// THE KEEP PASS IN A REAL ENGINE (review round 1 of the keep-with-next change, 2026-09-09): tab-row-keep.test.ts drives
// render.ts's painter over a flex-wrap model; this leg runs the SAME lifted code (makeRowBreak, paintTabRowLines,
// keepGroupsWithTabs, ensureTabRowObserver, sliced verbatim at run time) in headless Chromium under the real sheet,
// with a live ResizeObserver, and proves what the model cannot:
//   - the observer's own loop notice: Chromium raises "ResizeObserver loop completed with undelivered notifications"
//     as a WINDOW ERROR EVENT (not a console message; Playwright's console and pageerror never see it) when an
//     observed element's size changes inside the callback. Observing #tabs did that on every row the pass added or
//     dropped. The observer now watches a zero-height width sentinel, and a narrowing sweep that adds and drops rows
//     through the live observer raises none;
//   - the scrollbar's loop notice (review round 2): under classic scrollbars (the sheet's ::-webkit-scrollbar rule
//     makes every Chromium scrollbar a 10px classic one) a row change that crosses #tabbar's scroll cap toggled its
//     scrollbar, which changed #tabs' width, the sentinel's input, from inside the callback: one notice. #tabbar's
//     scrollbar-gutter: stable holds the width across the crossing. Playwright launches with --hide-scrollbars, so
//     this leg launches without it (ignoreDefaultArgs, file-view-scrollbar-browser.test.ts's idiom) and sweeps a
//     strip tall enough to cross the cap at a keep flip;
//   - the drag's live insert (review round 2): render.ts's dragover handler moves the dragged tab through the DOM
//     (tabs.insertBefore inside flipTabs) and the rows re-pack at an unchanged width, which no observer sees; the
//     handler's own insert block, sliced verbatim, runs the painter after the move, so the hairlines follow the rows
//     and the frozen keep breaks stay;
//   - the drag freeze: a width change while a tab is dragged runs the painter through the observer, and the keep
//     breaks stand exactly where the drag found them (the same elements, the same places); the paint after dragend
//     re-places them as a fresh paint would;
//   - the committed drop's rebuild (review round 3): the strip is rebuilt while the drag is still open (in Chromium
//     pointercancel at dragstart released the press-hold, so the drop's render is not deferred, and dragend then
//     renders nothing); the wipe disconnects the dragged element, the painter's gate, so the pass runs in that paint;
//   - the hairlines' right edge (review round 3): under classic scrollbars the bar reserves a 10px gutter, and each
//     hairline's bleed crosses it: the line's rect ends at the bar's border edge at every width, and where no
//     scrollbar is painted the line paints there (a hit test at the edge lands on the line); a painted scrollbar clips
//     the line at its inner edge (review round 4), so the hit test is read on the non-scrolling widths only; at the
//     round-2 head every line stopped 10px short while the bar's border ran on;
//   - the invariant across widths: no header or divider ends a row above its first tab unless no row can hold the
//     pair, and the hairlines sit under every row but the last.
// Skips, never fails, where playwright or Chromium is missing (CI installs none). The notes-api demo world.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

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

/** The probe: render.ts's own break, painter, pass and observer over a stand-in strip. */
function probeSource(): string {
  const BREAK = slice("function makeRowBreak(", "function makeTrailSep(");
  const PAINT = slice("function paintTabRowLines(", "function tabEmojiNode(");
  // the dragover handler's insert block: what render.ts runs once the virtual layout has picked the slot (the `if`
  // guard, the insert inside flipTabs, and whatever follows the insert), up to the handler's closing `});`
  const INSERT = slice("if (ref !== dragged && dragged.nextElementSibling !== ref)", "// Drop commits the LIVE DOM position").replace(/\}\);\s*$/, "");
  return `
function el(tag: string, cls?: string): HTMLElement { const e = document.createElement(tag); if (cls) e.className = cls; return e; }
let draggedId: string | null = null;   // render.ts's drag state: the id, and the very element, whose presence in the strip is the painter's gate
let draggedEl: HTMLElement | null = null;
${BREAK}
${PAINT}
const errs: string[] = [];
window.addEventListener("error", (e) => { errs.push(String((e as ErrorEvent).message)); });
const bar = document.getElementById("tabs")!;
const barbox = document.getElementById("tabbar")!;
type Spec = ["head", string] | ["tab", string, string] | ["sep"] | ["add"];
(window as any).__probe = {
  /** the rebuild: replaceChildren, the plan appended, the painter, the observer armed */
  build(spec: Spec[]) {
    bar.replaceChildren();
    for (const it of spec) {
      if (it[0] === "head") { const h = el("div", "tab-group-head"); h.dataset.group = it[1]; h.textContent = it[1] + " 3"; bar.appendChild(h); }
      else if (it[0] === "tab") { const t = el("div", "tab"); t.dataset.id = it[1]; t.textContent = it[2]; bar.appendChild(t); }
      else if (it[0] === "sep") bar.appendChild(el("div", "tab-group-sep"));
      else { const a = el("div", "tab tab-add"); a.textContent = "+"; bar.appendChild(a); }
    }
    paintTabRowLines(bar);
    ensureTabRowObserver(bar);
  },
  width(w: number) { barbox.style.width = w + "px"; },
  /** the bar's own size (its width is the probe's dial; its height the cap's) and the tab's, for the fixed-width legs */
  size(sel: string, w: number, h?: number) { for (const e of Array.from(document.querySelectorAll<HTMLElement>(sel))) { e.style.width = w + "px"; if (h !== undefined) e.style.height = h + "px"; } },
  drag(id: string | null) { draggedId = id; draggedEl = id ? bar.querySelector('.tab[data-id="' + id + '"]') as HTMLElement | null : null; },
  paint() { paintTabRowLines(bar); },
  /** the dragover handler's insert of the dragged tab ahead of ref, as render.ts runs it (the sliced block above) */
  insert(id: string, beforeId: string | null) {
    const tabs = bar;
    const dragged = bar.querySelector('.tab[data-id="' + id + '"]') as HTMLElement;
    const ref: Element | null = beforeId ? bar.querySelector('.tab[data-id="' + beforeId + '"]') : null;
    const flipTabs = (mutate: () => void) => { mutate(); };   // render.ts's FLIP animation, inert: the insert is the part under test
    ${INSERT}
  },
  mark() { Array.from(bar.querySelectorAll(".tab-keep-break")).forEach((k, i) => { (k as HTMLElement).dataset.probe = "k" + i; }); Array.from(bar.querySelectorAll(".tab-row-line")).forEach((l, i) => { (l as HTMLElement).dataset.probe = "l" + i; }); },
  frames() { return new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))); },
  survey() {
    const kids = Array.from(bar.children) as HTMLElement[];
    const opener = (k: HTMLElement) => k.classList.contains("tab-group-head") || (k.classList.contains("tab-group-sep") && !k.classList.contains("tab-group-break"));
    const bad: string[] = [];
    for (let i = 0; i < kids.length - 1; i++) {
      const k = kids[i], n = kids[i + 1];
      if (!opener(k) || !n.classList.contains("tab") || !n.dataset.id || n.offsetTop === k.offsetTop) continue;
      if (k.offsetWidth + n.offsetWidth > bar.clientWidth) continue;   // a pair no row can hold: accepted
      bad.push(k.textContent + "@" + k.offsetTop + " over " + n.dataset.id + "@" + n.offsetTop);
    }
    const rows = new Map<number, number>();
    for (const k of kids) {
      if (!(k.classList.contains("tab") || k.classList.contains("tab-group-head") || (k.classList.contains("tab-group-sep") && !k.classList.contains("tab-group-break")))) continue;
      rows.set(k.offsetTop, Math.max(rows.get(k.offsetTop) ?? 0, k.offsetTop + k.offsetHeight));
    }
    const bottoms = [...rows.values()].sort((x, y) => x - y); bottoms.pop();
    const lines = Array.from(bar.querySelectorAll(".tab-row-line")).map((l) => parseFloat((l as HTMLElement).style.top));
    const keeps = Array.from(bar.querySelectorAll(".tab-keep-break")) as HTMLElement[];
    // the first hairline's right edge against the bar's border edge, and whether the line PAINTS there: a hit test at
    // the bar's last pixel on the line's row (its pointer-events lifted for the read), which a clip at the padding edge
    // would hand to #tabbar; under a shown scrollbar the point is the scrollbar's, so the leg reads it only when the bar
    // does not scroll
    const barRight = barbox.getBoundingClientRect().right;
    const first = bar.querySelector(".tab-row-line") as HTMLElement | null;
    let lineRight = -1, edgePaints = false;
    if (first) {
      const lr = first.getBoundingClientRect(); lineRight = lr.right;
      first.style.pointerEvents = "auto";
      edgePaints = document.elementFromPoint(barRight - 1, lr.top + 0.5) === first;
      first.style.pointerEvents = "";
    }
    // the strip in DOM order, lines and the sentinel left out: what the drag's virtual layout reads
    const order = kids.filter((k) => !k.classList.contains("tab-row-line") && !k.classList.contains("tab-row-sentinel"))
      .map((k) => k.dataset.id || k.dataset.group || (k.classList.contains("tab-keep-break") ? "keep:" + (k.dataset.probe || "?") : k.className));
    return { bad, lines, bottoms, keeps: keeps.length, probes: keeps.map((k) => k.dataset.probe || null), order,
             height: bar.offsetHeight, width: bar.clientWidth, rows: rows.size, errs: errs.slice(),
             barRight, lineRight, edgePaints, draggedConnected: !!(draggedEl && draggedEl.isConnected),
             // #tabbar: its content width (the gutter and any scrollbar excluded), its border-box width, and whether it scrolls
             boxClientW: barbox.clientWidth, boxW: barbox.offsetWidth, scrolls: barbox.scrollHeight > barbox.clientHeight,
             lineEls: Array.from(bar.querySelectorAll(".tab-row-line")).map((l) => (l as HTMLElement).dataset.probe || null),
             sentinels: bar.querySelectorAll(".tab-row-sentinel").length,
             sentinelW: (bar.querySelector(".tab-row-sentinel") as HTMLElement | null)?.getBoundingClientRect().width ?? -1,
             sentinelH: (bar.querySelector(".tab-row-sentinel") as HTMLElement | null)?.getBoundingClientRect().height ?? -1 };
  },
};
`;
}

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: probeSource(), resolveDir: UI, loader: "ts", sourcefile: "tab-row-keep-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the strip under the real sheet (its @import and font urls 404 here, harmlessly); #tabbar's width is the probe's dial
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><link rel=stylesheet href=/styles.css>
<style>body{margin:0}</style></head>
<body><div id=tabbar style="width:900px"><div id=tabs></div></div><script src=/probe.js></script></body></html>`;

// the demo world: web with three tabs, api with two, tests folded (no tab follows), the trail with one
const SPEC = [["head", "web"], ["tab", "a1", "web-frontend"], ["tab", "a2", "web-backend"], ["tab", "a3", "web-gateway"],
              ["head", "api"], ["tab", "b1", "api-billing"], ["tab", "b2", "api-search"],
              ["head", "tests"], ["sep"], ["tab", "t1", "scratch"], ["add"]];

type Survey = { bad: string[]; lines: number[]; bottoms: number[]; keeps: number; probes: (string | null)[]; order: string[];
  height: number; width: number; rows: number; errs: string[]; boxClientW: number; boxW: number; scrolls: boolean; lineEls: (string | null)[];
  barRight: number; lineRight: number; edgePaints: boolean; draggedConnected: boolean;
  sentinels: number; sentinelW: number; sentinelH: number };

/** launch: Playwright launch options (the scrollbar leg drops --hide-scrollbars); spec: the strip built after load. */
async function withPage(t: any, body: (page: any, probe: { survey: () => Promise<Survey>; frames: () => Promise<void> }) => Promise<void>,
                        opts: { launch?: Record<string, unknown>; spec?: unknown[] } = {}): Promise<void> {
  let pw: any = null;
  try { pw = requireCjs("playwright"); } catch { pw = null; }
  if (!pw) { t.skip("playwright is not installed under vscode-extension (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(opts.launch ?? {}); }
  catch (e) { t.skip("no playwright chromium on this box (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try {
    const page = await browser.newPage({ viewport: { width: 1000, height: 400 } });
    const pageErrors: string[] = [];
    page.on("pageerror", (e: Error) => { pageErrors.push(e.message); });
    const js = bundle();
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname === "/styles.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: CSS });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.evaluate(() => document.fonts.ready);   // the fonts' once-paint has run before the test's own paints
    await page.evaluate((spec: unknown) => (window as any).__probe.build(spec), opts.spec ?? SPEC);
    assert.deepEqual(pageErrors, [], "the slices ran against the stand-in (a ReferenceError here means render.ts grew a dependency the probe lacks)");
    const survey = (): Promise<Survey> => page.evaluate(() => (window as any).__probe.survey());
    const frames = (): Promise<void> => page.evaluate(() => (window as any).__probe.frames());
    await body(page, { survey, frames });
  } finally {
    await browser.close();
  }
}

const loopNotice = (errs: string[]) => errs.filter((m) => /ResizeObserver loop/.test(m));

test("in Chromium, through the live observer: a narrowing that adds and drops rows raises no loop notice for the strip's own height changes (the observer watches the width sentinel, whose height the pass cannot change; the scrollbar's case is the classic-scrollbar leg below), and the invariant and the hairlines hold at every width", async (t) => {
  await withPage(t, async (page, { survey, frames }) => {
    let s = await survey();
    let flips = 0, heightFlips = 0, withKeeps = 0, steps = 0, sentinelFollows = true;
    let prev = s;
    for (let w = 880; w >= 200; w -= 4) {
      await page.evaluate((w: number) => (window as any).__probe.width(w), w);
      await frames();
      s = await survey();
      steps++;
      assert.ok(s.width < prev.width, "the strip took the width at " + w);
      sentinelFollows = sentinelFollows && s.sentinelW === s.width && s.sentinelH === 0;
      assert.deepEqual(s.bad, [], "no opener ends a row above its first tab at " + w + ": " + JSON.stringify(s.bad));
      assert.deepEqual(s.lines, s.bottoms, "a hairline under every row but the last at " + w);
      if (s.keeps) withKeeps++;
      if (s.keeps !== prev.keeps) { flips++; if (s.height !== prev.height) heightFlips++; }
      prev = s;
    }
    assert.ok(withKeeps > 0 && flips > 0 && heightFlips > 0, `the sweep exercised the pass through the observer: ${steps} widths, ${withKeeps} with a keep break, ${flips} flips, ${heightFlips} changing the strip's height`);
    assert.deepEqual(loopNotice(s.errs), [], "no 'ResizeObserver loop completed with undelivered notifications' window error across the sweep (scrollbars hidden by the default launch: the strip's own height changes are the only trigger here)");
    assert.deepEqual(s.errs, [], "no window error at all");
    // the sentinel: one, a child of the strip, as wide as it and zero tall at every width
    assert.equal(s.sentinels, 1, "one sentinel in the strip");
    assert.ok(sentinelFollows, "the sentinel followed the strip's width at zero height through the sweep");
  });
});

test("in Chromium, mid-drag: a width change runs the painter through the observer and the keep breaks stand where the drag found them, the same elements in the same places; the paint after dragend re-places them as a fresh paint would", async (t) => {
  await withPage(t, async (page, { survey, frames }) => {
    const setWidth = async (w: number) => { await page.evaluate((w: number) => (window as any).__probe.width(w), w); await frames(); return survey(); };
    const norm = (order: string[]) => order.map((x) => x.replace(/^keep:.*/, "keep"));
    // w0: the first width from wide to narrow where the pass placed a break; w1: a narrower width where a fresh paint
    // lays the breaks elsewhere (else the freeze would prove nothing). Both found with no drag in progress
    let w0 = 0, s = await survey();
    for (let w = 880; w >= 200 && !s.keeps; w -= 4) { s = await setWidth(w); w0 = w; }
    assert.ok(s.keeps > 0, "a width with a keep break exists in the demo world");
    const at0 = norm(s.order);
    let w1 = 0, fresh1: Survey | null = null;
    for (let w = w0 - 4; w >= 200 && !fresh1; w -= 4) { const f = await setWidth(w); if (JSON.stringify(norm(f.order)) !== JSON.stringify(at0)) { w1 = w; fresh1 = f; } }
    assert.ok(fresh1, "a narrower width lays the breaks elsewhere");
    s = await setWidth(w0);
    assert.deepEqual(norm(s.order), at0, "back at w0 the observer's paint gives the w0 layout again: the pass is a pure function of the width");
    await page.evaluate(() => (window as any).__probe.mark());
    const before = await survey();
    assert.deepEqual(before.probes, before.probes.map((_, i) => "k" + i), "the breaks at dragstart, marked");
    // the drag: a real width change (a scrollbar, a pane resize) while a1 is dragged
    await page.evaluate(() => (window as any).__probe.drag("a1"));
    const during = await setWidth(w1);
    assert.equal(during.width, fresh1!.width, "the strip took the width");
    assert.deepEqual(during.probes, before.probes, "the same break elements: none removed, none added");
    assert.deepEqual(during.order, before.order, "the strip's order, breaks included, as the drag found it");
    assert.deepEqual(during.lines, during.bottoms, "the hairlines still follow the rows as they now stand");
    assert.notDeepEqual(norm(during.order), norm(fresh1!.order), "which is not the layout a paint at this width gives: the pass did not run");
    // dragend: the rebuild re-places the breaks from the layout as it stands
    await page.evaluate(() => (window as any).__probe.drag(null));
    await page.evaluate(() => (window as any).__probe.paint());
    const after = await survey();
    assert.deepEqual(norm(after.order), norm(fresh1!.order), "the paint after dragend equals a fresh paint at this width");
    assert.deepEqual(after.bad, [], "and the invariant holds again");
    assert.deepEqual(loopNotice(after.errs), [], "no loop notice through the drag either");
  });
});

// the drag's live insert (review round 2): five tabs of fixed width in a 330px bar. a b fill row 0 (300 of 314: the bar's
// 8px paddings leave 314 for the strip), c d e row 1; the drag moves c ahead of b: a c (250) then b d (250) then e, three
// rows at the same width. No observer sees a row change at an unchanged width; the handler's insert block runs the painter
const DRAG_SPEC = [["tab", "a", "a"], ["tab", "b", "b"], ["tab", "c", "c"], ["tab", "d", "d"], ["tab", "e", "e"]];

test("in Chromium, mid-drag: the dragover handler's own insert (sliced from render.ts) re-packs the rows at an unchanged width and repaints the hairlines under the rows as they then stand, both directions; the frozen keep breaks do not move", async (t) => {
  await withPage(t, async (page, { survey, frames }) => {
    const size = (sel: string, w: number, h?: number) => page.evaluate(([sel, w, h]: [string, number, number | undefined]) => (window as any).__probe.size(sel, w, h), [sel, w, h]);
    await page.evaluate(() => (window as any).__probe.width(330));
    await size('.tab[data-id="a"], .tab[data-id="b"]', 150, 32); await size('.tab[data-id="c"], .tab[data-id="d"], .tab[data-id="e"]', 100, 32);
    await page.evaluate(() => (window as any).__probe.paint());   // the rebuild's paint, at the fixed sizes
    await frames();
    let s = await survey();
    assert.equal(s.rows, 2, "the premise: two rows before the drag: " + JSON.stringify(s.order));
    assert.deepEqual(s.lines, s.bottoms, "and the hairline under row 0");
    await page.evaluate(() => (window as any).__probe.drag("c"));
    await page.evaluate(() => (window as any).__probe.insert("c", "b"));   // the pointer crossed b's midpoint: c moves ahead of b
    await frames();
    s = await survey();
    assert.equal(s.rows, 3, "the insert re-packed the strip into three rows at the same width: " + JSON.stringify(s.order));
    assert.deepEqual(s.lines, s.bottoms, "a hairline under each of the two rows above the last, laid by the insert's own paint (at the round-1 head: [32] against [32, 64])");
    assert.deepEqual(loopNotice(s.errs), [], "no loop notice: the paint ran from the insert, not from inside an observer callback");
    // the other direction: c back after b drops row 2; a hairline must not stay lying at the strip's bottom edge
    await page.evaluate(() => (window as any).__probe.insert("c", "d"));
    await frames();
    s = await survey();
    assert.equal(s.rows, 2, "back to two rows");
    assert.deepEqual(s.lines, s.bottoms, "one hairline again: the dropped row's line went with it");
    await page.evaluate(() => (window as any).__probe.drag(null));
  }, { spec: DRAG_SPEC });
  // the keep breaks stand frozen through the insert's paint: the demo world at a width where a break stands
  await withPage(t, async (page, { survey, frames }) => {
    let s = await survey(), w0 = 0;
    for (let w = 880; w >= 200 && !s.keeps; w -= 4) { await page.evaluate((w: number) => (window as any).__probe.width(w), w); await frames(); s = await survey(); w0 = w; }
    assert.ok(s.keeps > 0 && w0 > 0, "a width with a keep break exists in the demo world");
    await page.evaluate(() => (window as any).__probe.mark());
    const before = await survey();
    await page.evaluate(() => (window as any).__probe.drag("a1"));
    await page.evaluate(() => (window as any).__probe.insert("a1", "b1"));   // a1 moves into the api group, ahead of b1
    await frames();
    s = await survey();
    assert.deepEqual(s.probes, before.probes, "the same break elements after the insert's paint: the pass stood down");
    assert.notDeepEqual(s.lineEls, before.lineEls, "the lines were re-laid by that paint (new elements)");
    assert.deepEqual(s.lines, s.bottoms, "under the rows as the insert left them");
    assert.deepEqual(s.order.filter((x) => x.startsWith("keep:")), before.order.filter((x) => x.startsWith("keep:")), "the breaks in the same order");
    await page.evaluate(() => (window as any).__probe.drag(null));
  });
});

test("in Chromium, the committed drop's rebuild (review round 3): the strip is rebuilt while the drag is still open, the wipe disconnects the dragged element, and the pass runs in that paint, so a header that would end a row above its first tab has its break before dragend, which renders nothing", async (t) => {
  await withPage(t, async (page, { survey, frames }) => {
    let s = await survey(), w0 = 0;
    for (let w = 880; w >= 200 && !s.keeps; w -= 4) { await page.evaluate((w: number) => (window as any).__probe.width(w), w); await frames(); s = await survey(); w0 = w; }
    assert.ok(s.keeps > 0 && w0 > 0, "a width with a keep break exists in the demo world");
    const before = s;
    await page.evaluate(() => (window as any).__probe.drag("a1"));
    assert.equal((await survey()).draggedConnected, true, "dragstart: the dragged element is in the strip");
    // the drop: reorderTo's renderTabs rebuilds at once (pointercancel released the press-hold at dragstart): every child
    // out, the plan in, the painter; the same strip, so the header that had its break needs it again
    await page.evaluate((spec: unknown) => (window as any).__probe.build(spec), SPEC);
    await frames();
    s = await survey();
    assert.equal(s.draggedConnected, false, "the wipe took the dragged element out of the strip");
    assert.deepEqual(s.bad, [], "no opener ends a row above its first tab right after the drop's rebuild, before dragend: " + JSON.stringify(s.bad));
    assert.equal(s.keeps, before.keeps, "the breaks are back as before the drag (at the round-2 head 0: the pass stood down under the still-set draggedId)");
    assert.deepEqual(s.lines, s.bottoms, "the hairlines under the rebuilt rows");
    await page.evaluate(() => (window as any).__probe.drag(null));   // dragend on the committed path renders nothing
    const after = await survey();
    assert.deepEqual(after.order, s.order, "dragend changed nothing: the breaks were placed at the drop");
    assert.deepEqual(loopNotice(after.errs), [], "no loop notice through the drop");
  });
});

// a strip tall enough to cross #tabbar's 150px scroll cap (styles.css --tabbar-cap) while the pass is placing and removing
// breaks: five groups, eleven tabs, the folded tests group, the trail's divider and its tab, and the +. Under classic
// scrollbars (this leg's launch) the cap's scrollbar takes 10px of the bar's width when it appears. Without the gutter rule
// this sweep raised exactly one notice on this strip: a re-wrap put the strip over the cap, the pass took a break out from
// inside the callback and the scrollbar went with the row, widening the strip under the observer
const TALL_SPEC = [["head", "web"], ["tab", "a1", "web-frontend"], ["tab", "a2", "web-backend"], ["tab", "a3", "web-gateway"],
                   ["head", "api"], ["tab", "b1", "api-billing"], ["tab", "b2", "api-search"],
                   ["head", "docs"], ["tab", "c1", "docs-site"], ["tab", "c2", "docs-guide"],
                   ["head", "infra"], ["tab", "d1", "infra-ci"], ["tab", "d2", "infra-deploy"], ["tab", "d3", "infra-alerts"],
                   ["head", "tests"], ["sep"], ["tab", "t1", "scratch"], ["add"]];

test("in Chromium with classic scrollbars (launched without --hide-scrollbars): a sweep whose keep flips cross #tabbar's scroll cap raises no loop notice, because #tabbar's scrollbar gutter is stable and the strip's width holds when the scrollbar comes and goes", { timeout: 120000 }, async (t) => {
  await withPage(t, async (page, { survey, frames }) => {
    let s = await survey(), prev = s;
    let scrollSteps = 0, capCrossings = 0, flipsScrolling = 0, flipsNot = 0, steps = 0, edgeReads = 0, edgeReadsScrolling = 0;
    const gutters = new Set<number>();
    for (let w = 880; w >= 200; w -= 4) {
      await page.evaluate((w: number) => (window as any).__probe.width(w), w);
      await frames();
      s = await survey();
      steps++;
      gutters.add(s.boxW - s.boxClientW);
      assert.equal(s.width, s.boxClientW - 16, "the strip is the bar's content width less its two 8px paddings at " + w + ", scrollbar or not");
      assert.deepEqual(s.bad, [], "no opener ends a row above its first tab at " + w + ": " + JSON.stringify(s.bad));
      assert.deepEqual(s.lines, s.bottoms, "a hairline under every row but the last at " + w);
      // the hairline meets the bar's edge like the border-bottom (T134), across the gutter: its right edge is the bar's
      // border edge, and where no scrollbar covers the gutter the line paints there
      if (s.lines.length) {
        assert.equal(s.lineRight, s.barRight, "the first hairline's right edge is the bar's border edge at " + w + " (at the round-2 head: 10px short, at the gutter)");
        if (s.scrolls) edgeReadsScrolling++;
        else { assert.ok(s.edgePaints, "the hairline paints to the bar's edge across the gutter at " + w + " (a clip at the padding edge hands the point to #tabbar)"); edgeReads++; }
      }
      if (s.scrolls) scrollSteps++;
      if (s.scrolls !== prev.scrolls) capCrossings++;
      if (s.keeps !== prev.keeps) { if (s.scrolls || prev.scrolls) flipsScrolling++; else flipsNot++; }
      prev = s;
    }
    assert.ok(scrollSteps > 0 && capCrossings > 0, `the sweep crossed the scroll cap: ${steps} widths, ${scrollSteps} scrolling, ${capCrossings} crossings`);
    assert.ok(flipsScrolling > 0 && flipsNot > 0, `the pass placed and removed breaks on both sides of the cap: ${flipsScrolling} flips at or into the scrolling strip, ${flipsNot} in the short one`);
    assert.equal(gutters.size, 1, "one gutter width at every step, scrollbar shown or not: " + JSON.stringify([...gutters]));
    assert.ok([...gutters][0] > 0, "the gutter is the classic scrollbar's width (the sheet's 10px): this launch shows scrollbars");
    assert.ok(edgeReads > 0 && edgeReadsScrolling > 0, `the right edge was read on both sides of the cap: ${edgeReads} painted reads on the short bar, ${edgeReadsScrolling} rect reads on the scrolling one`);
    assert.deepEqual(loopNotice(s.errs), [], "no 'ResizeObserver loop completed with undelivered notifications' window error across the sweep (without the gutter rule the cap crossing at a keep flip raised one)");
    assert.deepEqual(s.errs, [], "no window error at all");
  }, { launch: { ignoreDefaultArgs: ["--hide-scrollbars"] }, spec: TALL_SPEC });
});

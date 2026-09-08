// The pinned-notes strip under a REAL layout engine (review round 1 of the strip, 2026-09-08): headless
// Chromium lays the chat page's column out (tab bar, strip, transcript, composer) with the worktree's
// styles for the strip and drives the worktree's pinned-notes.ts and actions.ts, bundled the way the
// webview is built. Two things no stand-in can decide: (1) the CAP: a session's worst case (eight notes at
// the text and detail bounds, every fold open) must leave the transcript and the composer on screen, on a
// desktop and on a phone, with the strip scrolling past its cap and every row one line ending in an
// ellipsis; (2) the ARM on touch: the browser turns a tap into pointerdown and click, and the armed Unpin
// must stand down on the next tap elsewhere (before this, a tap left behind on a phone latched until the
// next pin, and a stray tap minutes later unpinned in one step); (3) the CUT (review round 2, 2026-09-08):
// which rows the one-line layout cuts is measured on the painted row, so a 60-character note that fits a
// desktop and is cut on a phone offers its full text there (the hint, the fold, the title), and the offer
// follows a width change of the strip through the ResizeObserver, no timer. The page carries the chat
// page's viewport meta (kernel.py), so the phone context lays out at the device width: without it a
// phone lays out at 980px and scales, and the phone leg measured a desktop (review round 2). (4) The MEASURE
// itself (review round 3, 2026-09-08): the cut is read in fractions of a pixel from the box the text has with
// the hint hidden, so the verdict flips exactly where Chrome paints the ellipsis (an overflow under a pixel
// included, where the integer scrollWidth and clientWidth read equal) and reads the same from a row already
// wearing the hint (a widen that gives the room back withdraws the offer); and the re-measure runs on the
// settings event and the fonts' loadingdone, which re-width a row and move no box. Skips LOUDLY without a
// playwright browser (CI installs none), as file-comments-regions-browser.test.ts does. Synthetic values only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { PINNED_CUT_CLASS } from "./pinned-notes";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

/** The builder, the arm and the delegate, bundled as the webview build bundles them, handed to the page as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { buildPinnedNotes, armUnpin, pinnedMeasureCut, pinnedWatchWidth, PINNED_ACT, PINNED_CUT_CLASS } from "./pinned-notes";\nimport { delegate } from "./actions";\n(window as any).__romp = { buildPinnedNotes, armUnpin, pinnedMeasureCut, pinnedWatchWidth, PINNED_ACT, PINNED_CUT_CLASS, delegate };\n',
      resolveDir: UI, loader: "ts", sourcefile: "pinned-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The strip's own rules, sliced from the sheet (the whole pinned-notes block), under the chat page's column. */
function sheet(): string {
  const a = CSS.indexOf("/* ---------- pinned notes (the user 2026-09-08)");
  const b = CSS.indexOf("/* the Reply modal: the need being answered");
  assert.ok(a >= 0 && b > a, "the pinned-notes block's markers in styles.css");
  return CSS.slice(a, b);
}
// the chat page's own head (kernel.py): the viewport meta is what makes a phone lay the page out at its width
const VIEWPORT_META = '<meta name="viewport" content="width=device-width, initial-scale=1">';
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8>${VIEWPORT_META}<style>
:root { --fs: 13px; --chat-col: 100%; --box-bg: #202020; --box-border: #444; --dim: #b8b8b8; --fg: #e8e8e8; --accent: #4aa3ff; --err: #ff6a6a; --sans: sans-serif; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; height: 100%; font-family: var(--sans); font-size: var(--fs); line-height: 1.6; background: #1e1e1e; color: var(--fg); }
body { display: flex; flex-direction: column; overflow-x: hidden; }
#tabbar { flex: 0 0 auto; padding: 5px 8px 0; border-bottom: 1px solid var(--box-border); height: 30px; }
#content { flex: 1 1 auto; overflow-y: scroll; overflow-x: hidden; padding: 8px 0 12px; }
#composer { flex: 0 0 auto; padding: 8px 24px 6px; }
#composer-input { width: 100%; height: 34px; }
${sheet()}</style></head><body>
<div id="tabbar"></div>
<div id="pinned-notes" style="display:none"></div>
<div id="content"><div style="height:3000px">the transcript</div></div>
<div id="composer"><textarea id="composer-input"></textarea></div>
<script src="/dist/pinned.js"></script></body></html>`;

const SID = "11111111-2222-3333-4444-555555555555";
const LONG = ("The staging deploy waits on the schema migration in docs/migrate.md; run step 3 before the api suite. ").repeat(4).slice(0, 300);
const NOTE60 = "staging deploy waits on the schema migration in docs/migrate";   // 60 characters: fits a desktop, cut on a phone
const DETAIL = ("Detail line: the auth step flakes when the cache is warm; see the run log.\n").repeat(60).slice(0, 4000);

type Box = { left: number; top: number; width: number; height: number; right: number; bottom: number };
type Row = { cut: boolean; over: boolean; whiteSpace: string; textOverflow: string; title: string; act: string | undefined;
  hintVisible: boolean; hintBeforeUnpin: boolean; foldStartsWithText: boolean; fullShown: boolean; fullText: string };
type Scene = {
  strip: Box; content: Box; composer: Box; viewport: number; pageWidth: number; fontPx: number;
  scrollHeight: number; clientHeight: number; overflowY: string; maxHeight: string;
  rows: Row[];
  mark: string;
};

type MountOpts = { openAll: boolean; long: boolean; text?: string };
/** Mount `n` notes (at the bounds, or one given text) with every fold open or closed, measure the cut the way
 *  render.ts does after its paint, wire the delegate and the width watch once, and report the layout. The
 *  report is window.__scene, so a later read (after a width change or a tap) re-measures without a rebuild. */
function mount(page: any, n: number, opts: MountOpts): Promise<Scene> {
  return page.evaluate(([n, opts, SID, LONG, DETAIL]: [number, MountOpts, string, string, string]) => {
    const w = window as any;
    const host = document.getElementById("pinned-notes")!;
    const notes = Array.from({ length: n }, (_, i) => ({ id: "pn-0000000" + i, text: opts.text ?? (opts.long ? LONG : "note " + i), detail: opts.long ? DETAIL : undefined, createdT: 1781200000 + i }));
    const state = { openDetails: new Set(opts.openAll ? notes.map((x) => x.id) : []), moreOpen: new Set(opts.openAll ? [SID] : []) };
    const strip = w.__romp.buildPinnedNotes(document, SID, notes, state, { line: () => {}, detail: () => {} });
    host.replaceChildren(strip); host.style.display = "";
    w.__romp.pinnedMeasureCut(host); w.__romp.pinnedWatchWidth(host);   // renderPinnedNotes' two calls after its paint
    if (!w.__wired) {
      w.__posts = []; w.__disarm = null;
      w.__romp.delegate(host, {
        [w.__romp.PINNED_ACT.unpin]: (el: HTMLElement) => {
          if (!el.classList.contains("armed")) { if (w.__disarm) w.__disarm(); w.__disarm = w.__romp.armUnpin(el, document, matchMedia("(pointer: coarse)").matches); return; }
          if (w.__disarm) w.__disarm();
          w.__posts.push(el.dataset.nid); el.closest(".pn-item")!.remove();
        },
      });
      w.__scene = (): Scene => {
        const r = (el: Element): Box => { const b = el.getBoundingClientRect(); return { left: b.left, top: b.top, width: b.width, height: b.height, right: b.right, bottom: b.bottom }; };
        const cs = getComputedStyle(host);
        const rows: Row[] = Array.from(host.querySelectorAll(".pn-item")).map((item) => {
          const t = item.querySelector(".pn-text") as HTMLElement;
          const hint = item.querySelector(".ut-more") as HTMLElement | null;
          const unpin = item.querySelector(".pn-unpin") as HTMLElement;
          const fold = item.querySelector(".pn-detail");
          const full = item.querySelector(".pn-full") as HTMLElement | null;
          const ts = getComputedStyle(t);
          return {
            cut: t.scrollWidth > t.clientWidth, over: item.classList.contains(w.__romp.PINNED_CUT_CLASS),
            whiteSpace: ts.whiteSpace, textOverflow: ts.textOverflow, title: t.title, act: t.dataset.act,
            hintVisible: !!hint && hint.getBoundingClientRect().width > 0 && hint.getBoundingClientRect().right <= host.getBoundingClientRect().right,
            hintBeforeUnpin: !!hint && hint.getBoundingClientRect().right <= unpin.getBoundingClientRect().left,
            foldStartsWithText: !!fold && (fold.textContent || "").startsWith(t.textContent || ""),
            fullShown: !!full && full.getBoundingClientRect().height > 0, fullText: full ? full.textContent || "" : "",
          };
        });
        const mark = getComputedStyle(host.querySelector(".pn-line")!, "::before").content;
        return {
          strip: r(host), content: r(document.getElementById("content")!), composer: r(document.getElementById("composer")!),
          viewport: window.innerHeight, pageWidth: document.documentElement.clientWidth, fontPx: parseFloat(getComputedStyle(document.body).fontSize),
          scrollHeight: host.scrollHeight, clientHeight: host.clientHeight, overflowY: cs.overflowY, maxHeight: cs.maxHeight, rows, mark,
        };
      };
      w.__wired = true;
    }
    return w.__scene();
  }, [n, opts, SID, LONG, DETAIL]);
}
const armed = (page: any, nid: string): Promise<{ armed: boolean; text: string; present: boolean }> =>
  page.evaluate((nid: string) => {
    const b = document.querySelector('.pn-item[data-nid="' + nid + '"] .pn-unpin') as HTMLElement | null;
    return { armed: !!b && b.classList.contains("armed"), text: b ? b.textContent || "" : "", present: !!b };
  }, nid);
const posts = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__posts.splice(0));

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, ctx: Record<string, unknown>, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension: the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box: the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    const context = await browser.newContext(ctx);
    const page = await context.newPage();
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/pinned.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

/** The strip's rows as they stand now, re-read without a rebuild (after a width change or a tap). */
function scene(page: any): Promise<Scene> {
  return page.evaluate(() => (window as any).__scene());
}

/** The first row's widths, fractional, read the way pinnedRowGeom reads them (a Range for the text's natural
 *  width; the hint's right edge past the text's for its take), plus the integer pair and the strip's box. */
type Geom = { host: number; height: number; text: number; box: number; hint: number; sw: number; cw: number; over: boolean };
function geom(page: any): Promise<Geom> {
  return page.evaluate((cls: string) => {
    const host = document.getElementById("pinned-notes")!, item = host.querySelector(".pn-item")!;
    const t = item.querySelector(".pn-text") as HTMLElement, h = item.querySelector(".ut-more") as HTMLElement;
    const r = document.createRange(); r.selectNodeContents(t);
    const tb = t.getBoundingClientRect(), hb = h.getBoundingClientRect(), hostB = host.getBoundingClientRect();
    return { host: hostB.width, height: hostB.height, text: r.getBoundingClientRect().width, box: tb.width, hint: hb.width > 0 ? hb.right - tb.right : 0,
      sw: t.scrollWidth, cw: t.clientWidth, over: item.classList.contains(cls) };
  }, PINNED_CUT_CLASS);
}
/** Whether Chrome paints the ellipsis on the first row's text as the row lays out on a fresh paint (the hint
 *  hidden): the row's pixels under text-overflow: ellipsis differ from the same row's under clip. */
async function ellipsisPainted(page: any): Promise<boolean> {
  const clip = await page.evaluate(() => {
    const st = document.createElement("style"); st.id = "pn-probe"; st.textContent = ".pn-line .ut-more { display: none !important; }"; document.head.appendChild(st);
    const b = document.querySelector(".pn-line")!.getBoundingClientRect();
    return { x: Math.floor(b.left), y: Math.floor(b.top), width: Math.ceil(b.width) + 1, height: Math.ceil(b.height) + 1 };
  });
  const withEllipsis = await page.screenshot({ clip });
  await page.evaluate(() => { (document.querySelector(".pn-text") as HTMLElement).style.textOverflow = "clip"; });
  const withClip = await page.screenshot({ clip });
  await page.evaluate(() => { (document.querySelector(".pn-text") as HTMLElement).style.textOverflow = ""; document.getElementById("pn-probe")!.remove(); });
  return !withEllipsis.equals(withClip);
}
/** Two frames: a ResizeObserver's callbacks run after layout and before the paint of the frame that follows a change. */
const settle = (page: any): Promise<void> => page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));

function checkCap(s: Scene, where: string, pageWidth: number): void {
  assert.equal(s.pageWidth, pageWidth, where + ": the page lays out at the context's width (the viewport meta), not a scaled 980px desktop");
  const cap = 11 * s.fontPx;                                      // min(11em, 30vh): 30vh is larger on both viewports here
  assert.ok(s.strip.height > 0 && s.strip.height <= cap + 2, where + ": the strip is capped (" + s.strip.height + " <= " + cap + ")");
  assert.equal(s.overflowY, "auto", where + ": the strip scrolls past the cap");
  assert.ok(s.scrollHeight > s.clientHeight + 40, where + ": there is more inside than the cap shows (" + s.scrollHeight + " > " + s.clientHeight + ")");
  assert.ok(s.content.height >= s.viewport * 0.5, where + ": the transcript keeps at least half the pane (" + s.content.height + " of " + s.viewport + ")");
  assert.ok(s.composer.bottom <= s.viewport + 0.5, where + ": the composer is on screen (" + s.composer.bottom + " <= " + s.viewport + ")");
  assert.ok(Math.abs(s.content.top - s.strip.bottom) < 0.5, where + ": the transcript starts where the strip ends");
  assert.equal(s.rows.length, 8, where + ": eight rows (the fold is open)");
  for (const [i, row] of s.rows.entries()) {
    assert.equal(row.whiteSpace, "nowrap", where + " row " + i + ": one line");
    assert.equal(row.textOverflow, "ellipsis", where + " row " + i + ": cut with an ellipsis");
    assert.ok(row.cut, where + " row " + i + ": a 300-character text is cut on this width");
    assert.ok(row.over, where + " row " + i + ": the measure marked the cut row");
    assert.ok(row.hintVisible, where + " row " + i + ": the details hint is visible beside the cut text");
    assert.equal(row.title, LONG, where + " row " + i + ": the full text is the row's title");
    assert.ok(row.fullShown && row.fullText === LONG, where + " row " + i + ": the open fold shows the full text");
    assert.ok(row.hintBeforeUnpin, where + " row " + i + ": text, hint, Unpin");
    assert.ok(row.foldStartsWithText, where + " row " + i + ": the fold carries the full text before the detail");
  }
  assert.equal(s.mark, '"▪"', where + ": the row mark is the neutral square, not the flag");
}

test("in a browser: eight notes at the bounds with every fold open stay within the cap, scroll inside it, and leave the transcript and the composer on screen (desktop and phone)", async (t) => {
  await inBrowser(t, { viewport: { width: 1200, height: 800 } }, async (page) => {
    checkCap(await mount(page, 8, { openAll: true, long: true }), "desktop", 1200);
    const few = await mount(page, 2, { openAll: false, long: false });
    assert.ok(few.strip.height < 4 * few.fontPx, "two short notes take two rows, well under the cap (" + few.strip.height + ")");
    assert.ok(few.scrollHeight <= few.clientHeight + 1, "nothing to scroll");
    assert.ok(!few.rows[0].cut, "a short text is not cut");
  });
  await inBrowser(t, { viewport: { width: 380, height: 700 }, hasTouch: true, isMobile: true }, async (page) => {
    checkCap(await mount(page, 8, { openAll: true, long: true }), "phone", 380);
  });
});

test("in a browser: a 60-character note fits a desktop and offers nothing; on a phone it is cut and offers its full text (title, hint, fold); a width change moves the offer with it, no rebuild", async (t) => {
  assert.equal(NOTE60.length, 60);
  const fits = (s: Scene, where: string): void => {
    const [row] = s.rows;
    assert.ok(!row.cut, where + ": the row shows the whole text");
    assert.ok(!row.over, where + ": not marked cut");
    assert.equal(row.title, NOTE60, where + ": the title still carries the text");
    assert.equal(row.act, undefined, where + ": the text is no click target: nothing to open");
    assert.ok(!row.hintVisible, where + ": no hint on a row that fits");
  };
  const offers = (s: Scene, where: string): void => {
    const [row] = s.rows;
    assert.ok(row.cut, where + ": the layout cuts the row (scrollWidth > clientWidth)");
    assert.ok(row.over, where + ": the measure marked it");
    assert.equal(row.title, NOTE60, where + ": the full text is the row's title");
    assert.equal(row.act, "pntoggle", where + ": the text opens the fold");
    assert.ok(row.hintVisible && row.hintBeforeUnpin, where + ": the details hint stands between the text and Unpin");
    assert.equal(row.fullText, NOTE60, where + ": the fold holds the full text");
  };
  await inBrowser(t, { viewport: { width: 380, height: 700 }, hasTouch: true, isMobile: true }, async (page) => {
    const s = await mount(page, 1, { openAll: false, long: false, text: NOTE60 });
    assert.equal(s.pageWidth, 380);
    offers(s, "phone");
    assert.ok(!s.rows[0].fullShown, "phone: folded until asked");
    await page.tap(".pn-item .ut-more");                          // the hint is visible and tappable on this width (playwright refuses a hidden target)
    await page.evaluate(() => { document.querySelector(".pn-item .pn-detail")!.classList.add("open"); });   // the toggle delegate's step, by hand: the test page carries the builder, not render.ts (pinned-notes.test.ts pins the delegate)
    const open = await scene(page);
    assert.ok(open.rows[0].fullShown, "phone: the open fold shows the full text");
    assert.equal(open.rows[0].fullText, NOTE60);
  });
  await inBrowser(t, { viewport: { width: 1200, height: 800 } }, async (page) => {
    fits(await mount(page, 1, { openAll: false, long: false, text: NOTE60 }), "desktop");
    // the pane narrows (a side panel, a window resize): the ResizeObserver re-measures and the offer appears
    await page.setViewportSize({ width: 380, height: 800 });
    await page.waitForFunction((c: string) => !!document.querySelector(".pn-item." + c), (await page.evaluate(() => (window as any).__romp.PINNED_CUT_CLASS)));
    offers(await scene(page), "narrowed");
    // and widens again: the offer is withdrawn
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.waitForFunction((c: string) => !document.querySelector(".pn-item." + c), (await page.evaluate(() => (window as any).__romp.PINNED_CUT_CLASS)));
    fits(await scene(page), "widened");
  });
});

test("in a browser, on touch: an armed Unpin stands down on the next tap elsewhere, and two taps in a row unpin", async (t) => {
  await inBrowser(t, { viewport: { width: 380, height: 700 }, hasTouch: true, isMobile: true }, async (page) => {
    assert.ok(await page.evaluate(() => matchMedia("(pointer: coarse)").matches), "the touch context reads as a coarse pointer");
    await mount(page, 2, { openAll: false, long: false });
    const btn = '.pn-item[data-nid="pn-00000001"] .pn-unpin';
    await page.tap(btn);
    assert.deepEqual(await armed(page, "pn-00000001"), { armed: true, text: "Unpin?", present: true }, "the first tap arms");
    await page.tap("#content");                                   // the user changes their mind and taps the transcript
    assert.deepEqual(await armed(page, "pn-00000001"), { armed: false, text: "Unpin", present: true }, "the tap elsewhere disarms; nothing was posted");
    assert.deepEqual(await posts(page), []);
    await page.tap(btn);
    assert.deepEqual(await armed(page, "pn-00000001"), { armed: true, text: "Unpin?", present: true }, "a stray later tap only re-arms; it cannot unpin in one step");
    await page.tap(btn);
    assert.deepEqual(await posts(page), ["pn-00000001"], "the second tap in a row confirms");
    assert.equal((await armed(page, "pn-00000001")).present, false, "the row is gone");
    assert.deepEqual(await armed(page, "pn-00000000"), { armed: false, text: "Unpin", present: true }, "the other row is untouched");
  });
});

test("in a browser, with a mouse: the armed Unpin stands down when the pointer leaves it, and when it loses focus", async (t) => {
  await inBrowser(t, { viewport: { width: 1200, height: 800 } }, async (page) => {
    await mount(page, 2, { openAll: false, long: false });
    const btn = '.pn-item[data-nid="pn-00000000"] .pn-unpin';
    await page.click(btn);
    assert.equal((await armed(page, "pn-00000000")).armed, true);
    await page.mouse.move(600, 600);                              // leaves the control
    assert.deepEqual(await armed(page, "pn-00000000"), { armed: false, text: "Unpin", present: true }, "pointerleave disarms");
    await page.focus(btn);
    await page.keyboard.press("Enter");                           // the keyboard arms it
    assert.equal((await armed(page, "pn-00000000")).armed, true);
    await page.keyboard.press("Tab");                             // and moves on: blur disarms
    assert.deepEqual(await armed(page, "pn-00000000"), { armed: false, text: "Unpin", present: true });
    assert.deepEqual(await posts(page), []);
    await page.focus(btn);
    await page.keyboard.press("Enter");
    await page.keyboard.press("Enter");                           // Enter, Enter: the keyboard confirms
    assert.deepEqual(await posts(page), ["pn-00000000"]);
  });
});

test("in a browser: the cut is read in fractions of a pixel from the box the text has with the hint hidden: a sweep of the strip's width around a note's natural width flips the verdict exactly where Chrome paints the ellipsis, through the band where the integer widths read equal, and reads the same from a row already wearing the hint", async (t) => {
  await inBrowser(t, { viewport: { width: 1200, height: 800 } }, async (page) => {
    await mount(page, 1, { openAll: false, long: false, text: NOTE60 });
    const g0 = await geom(page);
    assert.ok(g0.text > 100 && g0.box > g0.text && g0.hint === 0, "the row fits at 1200 with the hint hidden");
    const chrome = g0.host - g0.box;   // the mark, the gaps, Unpin and the strip's padding beside the text
    const seen: Array<{ room: number; overflow: number; ellipsis: boolean; integer: boolean; fromOff: boolean; fromOn: boolean }> = [];
    for (const room of [1.5, 0.5, 0.05, 0, -0.05, -0.1, -0.3, -0.5, -0.9, -0.95, -1.5, -40]) {   // the box past the text's natural width; negative is an overflow
      await page.evaluate(([w, cls]: [number, string]) => {
        const host = document.getElementById("pinned-notes")!;
        host.style.maxWidth = "none"; host.style.width = w + "px";
        host.querySelector(".pn-item")!.classList.remove(cls);
      }, [g0.text + chrome + room, PINNED_CUT_CLASS]);
      const ellipsis = await ellipsisPainted(page);
      const r = await page.evaluate((cls: string) => {
        const w = window as any, host = document.getElementById("pinned-notes")!, item = host.querySelector(".pn-item")!;
        item.classList.remove(cls);   // a fresh paint: no offer, the hint hidden
        const t = item.querySelector(".pn-text") as HTMLElement;
        const integer = t.scrollWidth > t.clientWidth;   // the round-2 read
        const range = document.createRange(); range.selectNodeContents(t);
        const overflow = range.getBoundingClientRect().width - t.getBoundingClientRect().width;
        w.__romp.pinnedMeasureCut(host); const fromOff = item.classList.contains(cls);
        item.classList.add(cls); w.__romp.pinnedMeasureCut(host); const fromOn = item.classList.contains(cls);   // from a row already offered the hint
        return { overflow, integer, fromOff, fromOn };
      }, PINNED_CUT_CLASS);
      seen.push({ room, ellipsis, ...r });
    }
    for (const s of seen) {
      const at = "at " + s.room + " (overflow " + s.overflow.toFixed(4) + "px)";
      assert.equal(s.ellipsis, s.overflow > 0, at + ": Chrome paints the ellipsis exactly when the text is wider than its box");
      assert.equal(s.fromOff, s.ellipsis, at + ": the verdict from a bare row is the ellipsis");
      assert.equal(s.fromOn, s.ellipsis, at + ": and the same from a row already wearing the hint");
    }
    assert.ok(seen.some((s) => s.ellipsis && !s.integer), "the sweep crossed the band the integer pair misses: an overflow under a pixel with the ellipsis painted");
    assert.ok(seen.some((s) => !s.ellipsis) && seen.some((s) => s.integer), "and the room where the text fits, and an overflow the integers see");
  });
});

test("in a browser: a row that has its room back after a widen drops its offer, hint and all, although the hint it was offered took that room while it showed (the ResizeObserver's re-measure reads the box the text has with the hint hidden)", async (t) => {
  await inBrowser(t, { viewport: { width: 1200, height: 800 } }, async (page) => {
    await mount(page, 1, { openAll: false, long: false, text: NOTE60 });
    const g0 = await geom(page);
    const snug = Math.ceil(g0.text + (g0.host - g0.box)) + 6;   // the text fits by about 6px with the hint hidden; the hint's 47px would not
    await page.setViewportSize({ width: snug, height: 800 });
    await settle(page);
    let g = await geom(page);
    assert.ok(!g.over && g.hint === 0 && g.box >= g.text + 5, "snug: the row fits with the hint hidden (" + g.box + " for " + g.text + ")");
    await page.setViewportSize({ width: 380, height: 800 });
    await page.waitForFunction((c: string) => !!document.querySelector(".pn-item." + c), PINNED_CUT_CLASS);
    g = await geom(page);
    assert.ok(g.over && g.hint > 30, "narrow: cut, the hint showing and taking its room (" + g.hint + "px)");
    await page.setViewportSize({ width: snug, height: 800 });
    // before round 3 this never came: the box beside the hint stayed short of the text, so the row kept the hint that kept it cut
    await page.waitForFunction((c: string) => !document.querySelector(".pn-item." + c), PINNED_CUT_CLASS);
    g = await geom(page);
    assert.ok(!g.over && g.hint === 0 && g.box >= g.text, "snug again: the same width paints the same strip, whatever showed before");
    const s = await scene(page);
    assert.ok(!s.rows[0].hintVisible && s.rows[0].act === undefined, "no hint, no click target");
  });
});

test("in a browser: a settings change that re-widths the rows and moves no box (a theme's font) re-measures on the romp:settings event, and a font finishing loading on the fonts' loadingdone; no repaint, no width change, no timer", async (t) => {
  await inBrowser(t, { viewport: { width: 1200, height: 800 } }, async (page) => {
    await mount(page, 1, { openAll: false, long: false, text: NOTE60 });
    const g0 = await geom(page);
    const roomy = Math.ceil(g0.text + (g0.host - g0.box)) + 20;   // the text fits by about 20px
    await page.setViewportSize({ width: roomy, height: 800 });
    await settle(page);
    const before = await geom(page);
    assert.ok(!before.over && before.box >= before.text + 19, "fits by 20px (" + before.box + " for " + before.text + ")");
    // the theme's font is wider: letter-spacing stands in for the swap (the same on every box: every row re-widths
    // by 60px and the strip's height does not move, so the ResizeObserver has nothing to say)
    await page.evaluate(() => { document.body.style.letterSpacing = "1px"; });
    await settle(page);
    const mid = await geom(page);
    assert.equal(mid.height, before.height, "the strip's box did not move");
    assert.ok(mid.text > mid.box, "the text is now wider than its box: the ellipsis is painted");
    assert.ok(!mid.over, "and unmarked: no event has said so yet (what round 3 found after a theme switch)");
    await page.evaluate(() => { window.dispatchEvent(new Event("romp:settings")); });   // what the gear dispatches after it writes the settings
    const after = await geom(page);
    assert.ok(after.over && after.hint > 30, "the settings event re-measured: cut, the hint offered");
    // a font load completing: the FontFaceSet's loadingdone (a failed load fires it too, so this needs no font file)
    await page.evaluate(() => { document.body.style.letterSpacing = ""; });
    await settle(page);
    assert.ok((await geom(page)).over, "the row fits again and is still marked: no event yet");
    await page.evaluate(() => new Promise<void>((resolve) => {
      document.fonts.addEventListener("loadingdone", () => resolve(), { once: true });   // registered after the strip's listener, so it runs after the measure
      const f = new FontFace("PnProbe", "url(data:font/woff,AAAA)");
      document.fonts.add(f);
      f.load().catch(() => {});
    }));
    const done = await geom(page);
    assert.ok(!done.over && done.hint === 0, "loadingdone re-measured: the offer withdrawn");
  });
});

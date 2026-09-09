// The margin layout's footer when it outgrows the panel (plans/file-review.md, "The margin-layout follow-on
// (2026-09-07)"; ui/CLAUDE.md: never dead-end a view). Beside the body the aside is `overflow: hidden` — a panel that
// scrolled would carry the track away from the body and every card off its mark — and the cards track was the one
// section that could shrink, so an open Send confirm (fifteen comments listed, the message preview under them) or an
// open Log (up to the host's 200 rows) collapsed the track to nothing and pushed its own Send, Cancel and Log controls
// past the panel's bottom edge, where no scroller reached them (found 2026-09-07). The sheet's rule now: the track
// keeps a floor, and every section but the track shrinks and scrolls inside itself, the one holding the content that
// grew first (the review's second round: the first cut let only the confirm's and the Log's sections yield, and the
// composer or a confirm row still pushed Send off the bottom — styles-fc-margin-fit.test.ts holds those). Pinned twice:
// the declarations in styles.css, and the geometry in a real engine — the worktree's file-comments.ts bundled as the
// webview is built, mounted under the chat page's own file-comments block, in Chromium and Firefox (skips LOUDLY
// without a playwright browser; CI installs none). Synthetic values only: invented prose, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const CHAT = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

function block(css: string): string {
  const a = css.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = css.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in styles.css");
  return css.slice(a, b);
}

// ── the declarations ───────────────────────────────────────────────────────────────────────────────
test("styles.css: the margin layout's track has a floor, the expanded footer sections yield and scroll, the panel never scrolls", () => {
  const css = block(CHAT);
  // the panel clips: a scroll of the panel would move the track's top against the body's, which placeCards measures once per pass
  assert.match(css, /\n\.fc-panel\.fc-margin \{ overflow: hidden; padding: 0; gap: 0; \}/, "the panel itself stays overflow: hidden");
  // the track: basis 0 (it never joins the shrink, so a tall footer costs it nothing past the floor) with a floor of the panel's height
  assert.match(css, /\n\.fc-margin > \.fc-sec-cards \{ flex: 1 1 0; min-height: 30%; position: relative; overflow: auto; scrollbar-width: none; \}/, "the track's basis is 0 with a 30% floor");
  // the footer sections are their content's height with a shrink, and scroll inside themselves when they give — never
  // flex 0 0 auto, which is what ran them past the aside's bottom
  assert.match(css, /\n\.fc-margin > \.fc-sec-send, \.fc-margin > \.fc-sec-log \{ flex: 0 1 auto; min-height: 0; overflow: auto; padding: 0 12px; \}/, "the footer sections shrink and scroll inside themselves");
  // expanded — the confirm up, rows in the Log, a row moved into the footer — a section gives first, a million times as
  // readily as a collapsed one, so Accept all · Reject all, Send and the Log toggle are squeezed only once everything
  // grown has reached its floor
  assert.match(css, /\n\.fc-margin > \.fc-sec-send:has\([^{]*\n\.fc-margin > \.fc-sec-log:has\(\.fc-log > :nth-child\(n\+2\)\) \{ flex-shrink: 1000000; min-height: min\(15%, 2\.4em\); \}/, "the grown sections give first, down to a floor");
  // the Log's fold stays in reach while its rows scroll under it
  assert.match(css, /\n\.fc-margin \.fc-log > \.fc-sec \{ position: sticky; top: 0; background: var\(--bg\); \}/, "the Log toggle is sticky in its scroller");
});

// ── the engine leg ─────────────────────────────────────────────────────────────────────────────────
/** The panel's registry entry and marked, bundled as the webview build bundles them (in memory), as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "margin-footer-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The chat page's rules the layout lives under: the viewer's card and body, the rendered prose, the buttons, and the
 *  whole file-comments block (the row, the aside and its fold, the panel, the cards, the margin layout). */
function sheet(): string {
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(CHAT);
    assert.ok(m, "a rule for " + sel + " in styles.css");
    return m![1];
  };
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4, .fileview-md h5, .fileview-md h6"), rule(".fileview-btn"), block(CHAT)].join("\n");
}
// the viewer's own ancestry: `.fileview` (the card) > `.fileview-main` (the row) > `.fileview-body` + the aside the panel mounts.
// 1000 × 600: the finding's geometry (a 700px window's viewer), well under what the confirm or the Log wants
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; }
${sheet()}
#wrap { width: 1000px; height: 600px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/margin-footer.js"></script></body></html>`;

// ── the document, its comments and its log (synthetic) ─────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
const SRC = "# Report\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const comment = (i: number, n: number): Record<string, unknown> => ({
  id: (T0 + n) + "-" + i, author: "you", ts: T0 + n, body: "Note on paragraph " + i + ": say what the cache does here.",
  anchor: { quote: "Paragraph " + i + " of the report", prefix: "", suffix: " says something about the cache" }, replies: [], resolved: false,
});
const N_COMMENTS = 15;                                            // an ordinary review, every one unsent
const COMMENTS = Array.from({ length: N_COMMENTS }, (_, k) => comment(2 * k + 2, k + 1));
const N_LOG = 30;                                                 // rows alternate a send (a fold underneath) and a tracking toggle (the line is the entry); the oldest, shown last, is a send
const LOG = Array.from({ length: N_LOG }, (_, k) => k % 2 === 0
  ? { kind: "send", ts: T0 - 100000 + k * 1000, sid: SID, comments: [{ desc: "on paragraph " + k, body: "Earlier note " + k + "." }], accepted: 0, rejected: 0 }
  : { kind: "set-tracked", ts: T0 - 100000 + k * 1000, on: true, entry: "docs/report.md" });
const STATUS = {
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: COMMENTS },
  hunks: [], log: LOG,
  unsent: { comments: COMMENTS.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
};

type Box = { top: number; bottom: number; height: number };
type Scroller = Box & { scrollTop: number; scrollHeight: number; clientHeight: number; overflowY: string };
type Hit = { box: Box; inside: boolean; hit: boolean } | null;    // a control: its box, whether the panel's box holds it, whether a click at its center lands on it
type Scene = {
  margin: boolean; panel: Scroller; track: Scroller; send: Scroller; log: Scroller;
  sendBtn: Hit; sendGo: Hit; cancel: Hit; logBtn: Hit; lastRow: Hit; rows: number; details: number;
};

/** Mount the panel over the rendered document, answer its status asks, open it, and let the paint and the pass run. */
function mount(page: any): Promise<void> {
  return page.evaluate(async ([src, status, abs, sid]: [string, Record<string, unknown>, string, string]) => {
    const w = window as any;
    const body = document.getElementById("body")!, md = document.getElementById("md")!;
    md.innerHTML = w.__romp.marked.parse(src);
    const posted: any[] = []; w.__posted = posted;
    const rendered: Array<() => void> = []; w.__rendered = rendered;
    const ctx = {
      path: abs, sid, todoId: null,
      body: () => body, mode: () => "rendered", text: () => src, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null,
      renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
      onRendered: (cb: () => void) => { rendered.push(cb); }, onSelection: () => { /* inert */ }, onSaved: () => { /* inert */ }, onClose: () => { /* inert */ },
      post: (m: any) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
      aside: (node: HTMLElement | null) => { const main = document.getElementById("main")!; main.querySelector(".fileview-aside")?.remove(); if (node) { node.classList.add("fileview-aside"); main.appendChild(node); } },
      setMode: () => { /* inert */ }, scrollToOffset: () => { /* inert */ }, reload: () => { /* inert */ },
    };
    const unit = w.__romp.fileCommentsAction.mount(ctx) as HTMLElement;
    document.body.appendChild(unit);
    const settle = () => new Promise<void>((r) => setTimeout(r, 0));
    const reply = async () => { const last = posted[posted.length - 1]; window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: last.reqId, ...status } })); await settle(); await settle(); };
    await reply();                                                // the probe
    (unit.querySelector("button") as HTMLButtonElement).click();  // open
    await reply();
    for (const cb of rendered) cb();                              // the viewer's onRendered: the paint pass over the body
    await settle();
    await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));   // the observers' frame
  }, [SRC, STATUS, ABS, SID]);
}
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const q = (sel: string): HTMLElement | null => aside.querySelector(sel);
  const box = (el: Element): Box => { const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height }; };
  const scroller = (el: HTMLElement): Scroller => ({ ...box(el), scrollTop: el.scrollTop, scrollHeight: el.scrollHeight, clientHeight: el.clientHeight, overflowY: getComputedStyle(el).overflowY });
  const panelBox = aside.getBoundingClientRect();
  const hit = (el: HTMLElement | null): Hit => {
    if (!el) return null;
    const r = el.getBoundingClientRect();
    const inside = r.top >= panelBox.top - 0.5 && r.bottom <= panelBox.bottom + 0.5;
    const at = document.elementFromPoint((r.left + r.right) / 2, (r.top + r.bottom) / 2);
    return { box: box(el), inside, hit: !!at && (at === el || el.contains(at)) };
  };
  const rows = Array.from(aside.querySelectorAll(".fc-log-row")) as HTMLElement[];
  return {
    margin: aside.classList.contains("fc-margin"),
    panel: scroller(aside), track: scroller(q(".fc-sec-cards")!), send: scroller(q(".fc-sec-send")!), log: scroller(q(".fc-sec-log")!),
    sendBtn: hit(q('[data-act="fcsend"]')), sendGo: hit(q('[data-act="fcsendgo"]')), cancel: hit(q('[data-act="fcsendcancel"]')),
    logBtn: hit(q('[data-act="fclog"]')), lastRow: hit(rows.length ? rows[rows.length - 1] : null), rows: rows.length, details: aside.querySelectorAll(".fc-log-detail").length,
  };
});
const click = (page: any, sel: string): Promise<void> => page.evaluate((sel: string) => { (document.querySelector(".fileview-aside " + sel) as HTMLElement).click(); }, sel);
const frames = (page: any, n = 2): Promise<void> => page.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
/** A mouse wheel over a section: the scroller under the pointer takes it, or nothing does (the finding's dead end). */
async function wheelOver(page: any, sel: string): Promise<number> {
  const at: { x: number; y: number } = await page.evaluate((sel: string) => { const r = (document.querySelector(".fileview-aside " + sel) as HTMLElement).getBoundingClientRect(); return { x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2 }; }, sel);
  await page.mouse.move(at.x, at.y);
  await page.mouse.wheel(0, 4000);
  try { await page.waitForFunction((sel: string) => (document.querySelector(".fileview-aside " + sel) as HTMLElement).scrollTop > 0, sel, { timeout: 3000 }); } catch { /* the caller reads the position */ }
  return page.evaluate((sel: string) => (document.querySelector(".fileview-aside " + sel) as HTMLElement).scrollTop, sel);
}
const FLOOR = 0.3;
const floorHeld = (s: Scene, when: string): void => {
  assert.ok(s.track.height >= FLOOR * s.panel.height - 1, when + ": the track keeps its floor (" + s.track.height + " of a " + s.panel.height + " panel)");
  assert.equal(s.panel.overflowY, "hidden", when + ": the panel itself does not scroll");
  assert.equal(s.panel.scrollTop, 0, when + ": the panel has not scrolled");
};

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, name: string, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    const page = await browser.newPage({ viewport: { width: 1100, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/margin-footer.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: the Send confirm with fifteen comments and the preview open scrolls within its section, Send and Cancel are in reach, the track keeps its floor, and closing it gives the room back`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      let s = await scene(page);
      assert.equal(s.margin, true, "the margin layout is on");
      assert.equal(s.rows, 0, "the Log is closed");
      assert.ok(s.track.height > FLOOR * s.panel.height + 40, "with the footer collapsed the track has the room: " + s.track.height + " of " + s.panel.height);
      assert.ok(s.send.scrollHeight <= s.send.clientHeight + 1, "the collapsed Send section has nothing to scroll");
      const trackBefore = s.track.height;
      assert.ok(s.sendBtn && s.sendBtn.inside && s.sendBtn.hit, "Send to session is in the panel and clickable");
      // Send to session, tick nothing, open The message: the confirm lists fifteen comments with the preview under them
      await click(page, '[data-act="fcsend"]');
      await frames(page);
      await click(page, '[data-act="fcpreview"]');
      await frames(page);
      s = await scene(page);
      assert.ok(s.sendGo && s.cancel, "the confirm is up with Send and Cancel");
      floorHeld(s, "confirm open");
      assert.ok(s.track.height < trackBefore, "the confirm took its room from the track: " + s.track.height + " < " + trackBefore);
      assert.ok(s.send.bottom <= s.panel.bottom + 0.5, "the Send section ends inside the panel: " + s.send.bottom + " vs " + s.panel.bottom);
      assert.ok(s.send.scrollHeight > s.send.clientHeight + 40, "the confirm is taller than its section, which scrolls it: " + s.send.scrollHeight + " in " + s.send.clientHeight);
      assert.equal(s.send.overflowY, "auto");
      assert.ok(s.logBtn && s.logBtn.inside && s.logBtn.hit, "the Log toggle under the confirm is still in the panel and clickable");
      // the wheel over the confirm scrolls the section (the finding: a wheel over the panel scrolled nothing)
      const wheeled = await wheelOver(page, ".fc-sec-send");
      assert.ok(wheeled > 0, "a wheel over the confirm scrolls its section: " + wheeled);
      // scrolled to its end, Send and Cancel are in the panel's box and a click at their centers lands on them
      await page.evaluate(() => { const el = document.querySelector(".fileview-aside .fc-sec-send") as HTMLElement; el.scrollTop = el.scrollHeight; });
      await frames(page);
      s = await scene(page);
      assert.ok(s.sendGo!.inside, "Send is inside the panel after the scroll: " + JSON.stringify(s.sendGo!.box) + " in " + JSON.stringify([s.panel.top, s.panel.bottom]));
      assert.ok(s.sendGo!.hit, "a click at Send's center lands on Send");
      assert.ok(s.cancel!.inside && s.cancel!.hit, "Cancel too");
      floorHeld(s, "confirm scrolled");
      // Cancel: the section collapses, nothing scrolls, the track has its room back
      await click(page, '[data-act="fcsendcancel"]');
      await frames(page);
      s = await scene(page);
      assert.equal(s.sendGo, null, "the confirm is gone");
      assert.ok(s.send.scrollHeight <= s.send.clientHeight + 1, "the collapsed Send section has nothing to scroll again");
      assert.ok(Math.abs(s.track.height - trackBefore) <= 1, "the track has its room back: " + s.track.height + " vs " + trackBefore);
      assert.ok(s.sendBtn && s.sendBtn.inside && s.sendBtn.hit, "Send to session is back in reach");
    });
  });

  test(`in ${name}: the Log with thirty rows scrolls within its section under a sticky toggle, every row is in reach and folds open, and the track keeps its floor`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      let s = await scene(page);
      const trackBefore = s.track.height;
      assert.ok(s.logBtn && s.logBtn.inside && s.logBtn.hit, "the Log toggle is in the panel and clickable");
      await click(page, '[data-act="fclog"]');
      await frames(page);
      s = await scene(page);
      assert.equal(s.rows, N_LOG, "every row is rendered");
      floorHeld(s, "Log open");
      assert.ok(s.track.height < trackBefore, "the Log took its room from the track: " + s.track.height + " < " + trackBefore);
      assert.ok(s.log.bottom <= s.panel.bottom + 0.5, "the Log section ends inside the panel: " + s.log.bottom + " vs " + s.panel.bottom);
      assert.ok(s.log.scrollHeight > s.log.clientHeight + 40, "thirty rows are taller than the section, which scrolls them: " + s.log.scrollHeight + " in " + s.log.clientHeight);
      assert.equal(s.log.overflowY, "auto");
      assert.ok(s.logBtn!.inside && s.logBtn!.hit, "the toggle is at the top of the open Log");
      assert.ok(!s.lastRow!.inside, "the last row starts out past the section's box (there is something to scroll to)");
      // the wheel over the rows scrolls the section
      const wheeled = await wheelOver(page, ".fc-sec-log");
      assert.ok(wheeled > 0, "a wheel over the Log scrolls its section: " + wheeled);
      // at the end: the last row is in the panel's box and clickable; the toggle is still in view (sticky)
      await page.evaluate(() => { const el = document.querySelector(".fileview-aside .fc-sec-log") as HTMLElement; el.scrollTop = el.scrollHeight; });
      await frames(page);
      s = await scene(page);
      assert.ok(s.lastRow!.inside && s.lastRow!.hit, "the last row is in the panel and a click at its center lands on it: " + JSON.stringify(s.lastRow!.box) + " in " + JSON.stringify([s.panel.top, s.panel.bottom]));
      assert.ok(s.logBtn!.inside && s.logBtn!.hit, "the toggle stayed in view over the scrolled rows: " + JSON.stringify(s.logBtn!.box));
      floorHeld(s, "Log scrolled");
      // the last row is a send entry: its fold opens where it stands
      assert.equal(s.details, 0);
      await page.evaluate(() => { const rows = document.querySelectorAll(".fileview-aside .fc-log-row"); (rows[rows.length - 1] as HTMLElement).click(); });
      await frames(page);
      s = await scene(page);
      assert.equal(s.details, 1, "the row's fold opened");
      assert.equal(s.rows, N_LOG);
      floorHeld(s, "a row open");
      // the toggle closes the Log from where it sticks, and the track has its room back
      await click(page, '[data-act="fclog"]');
      await frames(page);
      s = await scene(page);
      assert.equal(s.rows, 0, "the Log is closed");
      assert.ok(s.log.scrollHeight <= s.log.clientHeight + 1, "the collapsed Log section has nothing to scroll");
      assert.ok(Math.abs(s.track.height - trackBefore) <= 1, "the track has its room back: " + s.track.height + " vs " + trackBefore);
    });
  });
}

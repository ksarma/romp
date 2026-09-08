// The margin layout's footer in feed.css (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"): Send and
// the Log stay put at the bottom of the aside while the cards track is the scroller locked to the body — and, under
// `.fc-panel.fc-margin { overflow: hidden }`, the aside itself no longer scrolls as a whole the way the list layout's
// does. So the footer has to bound itself: the Send confirm (its list, its options, its 40vh preview, Send · Cancel) and
// the open Log (up to the host's tail of 200 rows) each grow past a pane's height, and a footer that can neither shrink
// nor scroll first starves the track to nothing (every card gone) and then runs past the aside's bottom, where no
// pointer reaches Send or the oldest rows (the 2026-09-07 review of the follow-on; ui/CLAUDE.md: never dead-end a view).
// This file holds the BEHAVIOUR, not the sheet's mechanism: the static leg asks only that the margin block makes the two
// sections scrollers of their own; the browser legs mount the worktree's panel under feed.css's own rules in Chromium and
// Firefox, open the confirm with its preview, then the Log, and measure — the grown section stays inside the aside,
// scrolls under a real wheel, its far end is hit-testable once scrolled there, and the track keeps room for cards.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only:
// invented prose, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** The one rule whose head is `sel` in feed.css. */
function rule(sel: string): string {
  const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
  assert.ok(m, "a rule for " + sel + " in feed.css");
  return m![1];
}
const BLOCK_A = "/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)";
const BLOCK_B = "/* ── end file comments panel ── */";

// ── the static leg: the margin block makes the footer's two sections scrollers of their own ─────────

test("feed.css: the margin layout gives the Send and Log sections an overflow of their own, inside the panel block", () => {
  const a = FEED.indexOf(BLOCK_A), b = FEED.indexOf(BLOCK_B);
  assert.ok(a >= 0 && b > a, "the file-comments block's markers");
  const margin = FEED.slice(FEED.indexOf("\n.fc-panel.fc-margin {", a), b);
  assert.ok(margin.length > 0, "the margin rules follow the root rule inside the block (the block both sheets hold byte-equal)");
  // every rule of the margin layout that names a footer section, with its declarations
  const footer = Array.from(margin.matchAll(/\n((?:\.fc-margin > \.fc-sec-(?:send|log)[^{,]*(?:, )?)+)\{([^}]*)\}/g));
  assert.ok(footer.length >= 1, "rules for the footer's sections under .fc-margin");
  for (const sec of ["send", "log"]) {
    const own = footer.filter((m) => m[1].includes(".fc-sec-" + sec));
    assert.ok(own.some((m) => /overflow(?:-y)?: auto;/.test(m[2])), "the " + sec + " section scrolls inside itself when it outgrows its room: " + own.map((m) => m[0].trim()).join(" | "));
  }
  // the aside's own overflow stays hidden: the track is the scroller the body is locked to, and a panel that scrolled as a
  // whole would carry the track away from the body (the plan's follow-on note)
  assert.equal(rule(".fc-panel.fc-margin"), ".fc-panel.fc-margin { overflow: hidden; padding: 0; gap: 0; }");
});

// ── the browser legs ─────────────────────────────────────────────────────────────────────────────

/** The panel's registry entry and marked, bundled as the webview build bundles them (in memory), as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "margin-footers-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under: the viewer's card, body and prose, the buttons, and the whole file-comments block. */
function sheet(): string {
  const a = FEED.indexOf(BLOCK_A), b = FEED.indexOf(BLOCK_B);
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4"), rule(".fileview-btn"), FEED.slice(a, b)].join("\n");
}
// the viewer's own ancestry: `.fileview` (the card) > `.fileview-main` (the row) > `.fileview-body` + the aside the panel mounts.
// The card is 500px tall in a 700px viewport: whatever the aside clips lies inside the viewport, so a hit test there
// says whether the footer reaches past the aside's box.
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; }
${sheet()}
#wrap { width: 1000px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/margin-footers.js"></script></body></html>`;

// ── the document, its comments, one change, and a long Log (synthetic) ──────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
const SRC = "# Report\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const comment = (i: number, n: number): Record<string, unknown> => ({
  id: (T0 + n) + "-" + i, author: "you", ts: T0 + n, body: "Note on paragraph " + i + ".",
  anchor: { quote: "Paragraph " + i + " of the report", prefix: "", suffix: " says something about the cache" }, replies: [], resolved: false,
});
const WHOLE = { id: (T0 - 5000) + "-0", author: "you", ts: T0 - 5000, body: "Add a summary at the top.", replies: [], resolved: false };
const COMMENTS = [WHOLE, comment(3, 1), comment(4, 2), comment(30, 3)];
const INS_AT = SRC.indexOf("Paragraph 6 of the report");
const HUNK = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: INS_AT, curTo: INS_AT + 9, baseFrom: INS_AT, baseTo: INS_AT, oldText: "", newText: "Paragraph", anchor: null };
// forty tracking toggles, the plainest entry the host writes (one row each, nothing underneath), oldest first as the host replies
const LOG_ROWS = 40;
const LOG = Array.from({ length: LOG_ROWS }, (_, i) => ({ ts: new Date(T0 - (LOG_ROWS - i) * 60000).toISOString(), kind: "set-tracked", author: "you", on: i % 2 === 0, scope: "file", entry: "docs/report.md" }));
const STATUS = {
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: COMMENTS },
  hunks: [HUNK], log: LOG,
  unsent: { comments: COMMENTS.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
};

type Box = { top: number; bottom: number; height: number; left: number; right: number };
/** One footer section as laid out: its box against the aside's, its overflow, its scroll range, and the track's room. */
type Foot = {
  margin: boolean; overflowY: string; box: Box; aside: Box; scrollHeight: number; clientHeight: number; scrollTop: number;
  trackHeight: number; cardsInTrack: number; posted: number;
};

/** Mount the panel over the rendered document, answer its status asks, open it, and let the paint and the pass run. */
function mount(page: any): Promise<void> {
  return page.evaluate(async ([src, status, abs, sid]: [string, Record<string, unknown>, string, string]) => {
    const w = window as any;
    const body = document.getElementById("body")!, md = document.getElementById("md")!;
    md.innerHTML = w.__romp.marked.parse(src);
    const posted: any[] = []; w.__posted = posted;
    const rendered: Array<() => void> = [];
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
const frames = (page: any, n = 2): Promise<void> => page.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
const click = (page: any, act: string): Promise<void> => page.evaluate((act: string) => { (document.querySelector('.fileview-aside [data-act="' + act + '"]') as HTMLElement).click(); }, act);
const foot = (page: any, sec: string): Promise<Foot> => page.evaluate((sec: string) => {
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const box = (el: Element): Box => { const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height, left: r.left, right: r.right }; };
  const s = aside.querySelector(sec) as HTMLElement;
  const track = aside.querySelector(".fc-sec-cards") as HTMLElement;
  const t = box(track);
  const cards = Array.from(aside.querySelectorAll(".fc-card")).filter((c) => { const b = box(c); return b.top >= t.top - 0.5 && b.bottom <= t.bottom + 0.5 && b.height > 0; });
  return {
    margin: aside.classList.contains("fc-margin"), overflowY: getComputedStyle(s).overflowY, box: box(s), aside: box(aside),
    scrollHeight: s.scrollHeight, clientHeight: s.clientHeight, scrollTop: s.scrollTop,
    trackHeight: track.clientHeight, cardsInTrack: cards.length, posted: (window as any).__posted.length,
  };
}, sec);
/** Whether the element under (x, y) is, or is inside, a match for `sel`. */
const hit = (page: any, x: number, y: number, sel: string): Promise<boolean> => page.evaluate(([x, y, sel]: [number, number, string]) => {
  const e = document.elementFromPoint(x, y);
  return !!(e && e.closest(sel));
}, [x, y, sel]);
/** A real wheel over (x, y), then the section's scrollTop once the engine has moved it (smooth scrolling included). */
async function wheel(page: any, sec: string, x: number, y: number): Promise<number> {
  await page.mouse.move(x, y);
  await page.mouse.wheel(0, 240);
  await page.waitForFunction((sec: string) => (document.querySelector(".fileview-aside " + sec) as HTMLElement).scrollTop > 0, sec, { timeout: 5000 });
  return page.evaluate((sec: string) => (document.querySelector(".fileview-aside " + sec) as HTMLElement).scrollTop, sec);
}
const toEnd = (page: any, sec: string): Promise<void> => page.evaluate((sec: string) => { const s = document.querySelector(".fileview-aside " + sec) as HTMLElement; s.scrollTop = s.scrollHeight; }, sec);
const boxOf = (page: any, sel: string): Promise<Box> => page.evaluate((sel: string) => { const r = (document.querySelector(".fileview-aside " + sel) as HTMLElement).getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height, left: r.left, right: r.right }; }, sel);
const lastRowBox = (page: any): Promise<Box> => page.evaluate(() => { const rows = document.querySelectorAll(".fileview-aside .fc-log-row"); const r = rows[rows.length - 1].getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height, left: r.left, right: r.right }; });
const inside = (b: Box, of: Box, what: string): void => assert.ok(b.top >= of.top - 0.5 && b.bottom <= of.bottom + 0.5, what + " is inside the aside's box: " + b.top + ".." + b.bottom + " vs " + of.top + ".." + of.bottom);
// the room the track must keep once a footer section has grown: a quarter of the aside (the sheet's share for the
// footer, whatever it is, leaves at least that), and a card in view in it
const ROOM = 0.25;

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
      if (u.pathname === "/dist/margin-footers.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: the Send confirm with its preview open stays inside the aside, scrolls under the wheel to Send · Cancel, and leaves the track its cards`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      let f = await foot(page, ".fc-sec-send");
      assert.equal(f.margin, true, "the margin layout is on at 1000px");
      // closed, the section is its content — the Accept all · Reject all row and the Send button — with nothing to scroll
      assert.ok(f.scrollHeight <= f.clientHeight + 1, "nothing to scroll with the confirm closed: " + f.scrollHeight + " in " + f.clientHeight);
      assert.ok(f.box.height < ROOM * f.aside.height, "the closed section is small: " + f.box.height + " of " + f.aside.height);
      const roomBefore = f.trackHeight;
      await click(page, "fcsend");
      await click(page, "fcpreview");
      await frames(page);
      f = await foot(page, ".fc-sec-send");
      // the finding's state: the confirm lists four comments, an option, a 40vh preview and Send · Cancel — more than fits
      assert.equal(f.overflowY, "auto", "the grown section is a scroll container of its own");
      assert.ok(f.scrollHeight > f.clientHeight + 40, "the confirm outgrows the section, so the section scrolls: " + f.scrollHeight + " in " + f.clientHeight);
      inside(f.box, f.aside, "the Send section");
      assert.ok(f.trackHeight >= ROOM * f.aside.height && f.trackHeight < roomBefore, "the track kept room for cards: " + f.trackHeight + " of " + f.aside.height + " (was " + roomBefore + ")");
      assert.ok(f.cardsInTrack >= 1, "a card is in view in the track: " + f.cardsInTrack);
      // a real wheel over the section's top (Accept all · Reject all, then the Send button) scrolls the section, not nothing
      const moved = await wheel(page, ".fc-sec-send", (f.box.left + f.box.right) / 2, f.box.top + 12);
      assert.ok(moved > 0, "the wheel moved the section: " + moved);
      // scrolled to its end, the confirm's own Send button is inside the aside and under the pointer
      await toEnd(page, ".fc-sec-send");
      await frames(page);
      const go = await boxOf(page, '[data-act="fcsendgo"]');
      inside(go, f.aside, "the confirm's Send button");
      const cx = (go.left + go.right) / 2, cy = (go.top + go.bottom) / 2;
      assert.equal(await hit(page, cx, cy, '[data-act="fcsendgo"]'), true, "the pointer reaches the confirm's Send button at " + cx + "," + cy);
      const before = f.posted;
      await page.mouse.click(cx, cy);
      await frames(page);
      f = await foot(page, ".fc-sec-send");
      assert.ok(f.posted > before, "the click landed: the send began with a request to the kernel (" + before + " → " + f.posted + ")");
    });
  });

  test(`in ${name}: the open Log stays inside the aside, scrolls under the wheel to its oldest row, and leaves the track its cards`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      let f = await foot(page, ".fc-sec-log");
      assert.equal(f.margin, true);
      assert.ok(f.scrollHeight <= f.clientHeight + 1, "the closed Log is one line, nothing to scroll");
      assert.ok(f.box.height < ROOM * f.aside.height, "the closed Log is small: " + f.box.height + " of " + f.aside.height);
      const roomBefore = f.trackHeight;
      await click(page, "fclog");
      await frames(page);
      f = await foot(page, ".fc-sec-log");
      const rows: number = await page.evaluate(() => document.querySelectorAll(".fileview-aside .fc-log-row").length);
      assert.equal(rows, LOG_ROWS, "every row of the host's tail is rendered");
      assert.equal(f.overflowY, "auto", "the open Log is a scroll container of its own");
      assert.ok(f.scrollHeight > f.clientHeight + 100, "forty rows outgrow the section, so the section scrolls: " + f.scrollHeight + " in " + f.clientHeight);
      inside(f.box, f.aside, "the Log section");
      assert.ok(f.trackHeight >= ROOM * f.aside.height && f.trackHeight < roomBefore, "the track kept room for cards: " + f.trackHeight + " of " + f.aside.height + " (was " + roomBefore + ")");
      assert.ok(f.cardsInTrack >= 1, "a card is in view in the track: " + f.cardsInTrack);
      const moved = await wheel(page, ".fc-sec-log", (f.box.left + f.box.right) / 2, f.box.top + 10);
      assert.ok(moved > 0, "the wheel moved the Log: " + moved);
      // scrolled to its end, the oldest row (the last one rendered: newest first) is inside the aside and under the pointer
      await toEnd(page, ".fc-sec-log");
      await frames(page);
      const last = await lastRowBox(page);
      inside(last, f.aside, "the oldest Log row");
      const cx = (last.left + last.right) / 2, cy = (last.top + last.bottom) / 2;
      assert.equal(await hit(page, cx, cy, ".fc-log-row"), true, "the pointer reaches the oldest row at " + cx + "," + cy);
    });
  });
}

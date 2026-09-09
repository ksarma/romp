// The margin layout in a REAL engine (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"): the
// worktree's file-comments.ts, bundled the way the webview is built, mounted over a rendered markdown body laid
// out under feed.css's own rules, with the kernel's replies arriving as window messages. This is the leg no
// stand-in can stand in for: whether a card's box lands where its mark's box is once the browser has laid out the
// paragraphs, the cards and the header the track begins under; whether two cards whose marks are a line apart
// stack instead of overlapping; whether the two scrollers move together, to the far end included — the fixed footer
// (Accept all · Reject all, Send, Log) makes the track's box shorter than the body's, and unless the track's content
// is shorter by the same amount the track scrolls on past the body's end and every card floats above its mark
// (found 2026-09-07); and whether the sheet's container query (the narrow fold) reaches the panel as the list
// layout. Runs in Chromium and Firefox; skips LOUDLY without a playwright browser (CI installs none), as the other
// browser legs do. Synthetic values only: invented prose, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** The panel's registry entry and marked, bundled as the webview build bundles them (in memory), as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "margin-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under: the body, the rendered prose, the buttons, and the whole file-comments block
 *  (the row, the aside and its fold, the panel, the cards, the highlights, the margin layout). */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  // `.fileview` is the viewer's card, the ancestor the fold's container query resolves against (its container-type)
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4, .fileview-md h5, .fileview-md h6"), rule(".fileview-btn"), FEED.slice(a, b)].join("\n");
}
// the viewer's own ancestry: `.fileview` (the card) > `.fileview-main` (the row) > `.fileview-body` + the aside the panel mounts
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; }
${sheet()}
#wrap { width: 1000px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/margin.js"></script></body></html>`;

// ── the document and its comments (synthetic prose) ────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
const SRC = "# Report\n\n" + Array.from({ length: 40 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const quoteOf = (i: number): string => "Paragraph " + i + " of the report";
const comment = (i: number, n: number): Record<string, unknown> => ({
  id: (T0 + n) + "-" + i, author: "you", ts: T0 + n, body: "Note on paragraph " + i + ".",
  anchor: { quote: quoteOf(i), prefix: "", suffix: " says something about the cache" }, replies: [], resolved: false,
});
const WHOLE = { id: (T0 - 5000) + "-0", author: "you", ts: T0 - 5000, body: "Add a summary at the top.", replies: [], resolved: false };
// marks on paragraphs 3 and 4 (a line apart: the second card cannot fit beside its paragraph), on paragraph 30 (far
// down) and on paragraph 40 (the last one: its mark is in the body's last lines, where the footer covers the track)
const COMMENTS = [WHOLE, comment(3, 1), comment(4, 2), comment(30, 3), comment(40, 4)];
const KEYS = { c3: COMMENTS[1].id as string, c4: COMMENTS[2].id as string, c30: COMMENTS[3].id as string, c40: COMMENTS[4].id as string, whole: WHOLE.id };
// one change: a word the session inserted in paragraph 6, painted in Rendered as a tint (the foot goes to the footer)
const INS_AT = SRC.indexOf("Paragraph 6 of the report");
const HUNK = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: INS_AT, curTo: INS_AT + 9, baseFrom: INS_AT, baseTo: INS_AT, oldText: "", newText: "Paragraph", anchor: null };
const STATUS = {
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: COMMENTS },
  hunks: [HUNK], log: [],
  unsent: { comments: COMMENTS.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
};

type Box = { top: number; bottom: number; height: number };
type Scene = {
  margin: boolean; footIn: string | null; listHeight: number; bodyScrollHeight: number; offset: number;
  cards: Record<string, Box & { pushed: string | null; leader: string }>; marks: Record<string, Box | null>;
  bodyScroll: number; trackScroll: number; flex: string;
  bodyRange: number; trackRange: number;                          // each scroller's farthest scrollTop (scrollHeight - clientHeight)
  bodyBox: Box; trackBox: Box;                                    // the two scrollers' boxes in the viewport (the track's ends above the footer)
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
const scene = (page: any, keys: Record<string, string>): Promise<Scene> => page.evaluate((keys: Record<string, string>) => {
  const body = document.getElementById("body")!;
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const track = aside.querySelector(".fc-sec-cards") as HTMLElement;
  const list = track.querySelector(".fc-cards") as HTMLElement;
  const box = (el: Element): { top: number; bottom: number; height: number } => { const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height }; };
  const cards: Record<string, any> = {}, marks: Record<string, any> = {};
  for (const [name, key] of Object.entries(keys)) {
    const card = aside.querySelector('.fc-card[data-id="' + key + '"]') as HTMLElement | null;
    cards[name] = card ? { ...box(card), pushed: card.dataset.pushed ?? null, leader: card.style.getPropertyValue("--fc-push") } : null;
    const act = key.startsWith("chg:") ? "fcchange" : "fcopen", id = key.startsWith("chg:") ? key.slice(4) : key;
    const m = body.querySelector('[data-act="' + act + '"][data-id="' + id + '"]');
    marks[name] = m ? box(m) : null;
  }
  const foot = aside.querySelector(".fc-foot");
  return {
    margin: aside.classList.contains("fc-margin"), footIn: foot ? (foot.parentElement as HTMLElement).className : null,
    listHeight: parseFloat(list.style.height || "0"), bodyScrollHeight: body.scrollHeight, offset: track.getBoundingClientRect().top - body.getBoundingClientRect().top,
    cards, marks, bodyScroll: body.scrollTop, trackScroll: track.scrollTop, flex: getComputedStyle(document.getElementById("main")!).flexDirection,
    bodyRange: body.scrollHeight - body.clientHeight, trackRange: track.scrollHeight - track.clientHeight, bodyBox: box(body), trackBox: box(track),
  };
}, keys);
const frames = (page: any, n = 2): Promise<void> => page.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
const near = (a: number, b: number, msg: string, tol = 1) => assert.ok(Math.abs(a - b) <= tol, msg + ": " + a + " vs " + b);

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
      if (u.pathname === "/dist/margin.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: cards land level with their marks, a colliding card stacks under the one above, the whole-file card is loose at the top, the foot is in the footer, and the scrollers move together over one range, the far end included`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      const keys = { ...KEYS, chg: "chg:h1" };
      let s = await scene(page, keys);
      assert.equal(s.flex, "row", "the row is two columns at 1000px");
      assert.equal(s.margin, true, "the margin layout is on");
      assert.equal(s.footIn, "fc-sec-send", "Accept all · Reject all stand in the footer, above Send");
      assert.ok(s.offset > 40, "the track begins under the header: " + s.offset);
      // one range: the track's box is the body's less the header above it AND the footer below it (Accept all · Reject
      // all, Send, Log), so its content must be shorter than the body's by both for the two farthest positions to
      // agree — the plan's "share one range". Content shorter by the header alone leaves the track a footer's height
      // of range the body does not have (the 2026-09-07 finding). scrollHeight and clientHeight are integers, so a
      // fractional footer can round the two ranges a pixel apart.
      assert.ok(s.bodyBox.bottom - s.trackBox.bottom > 40, "the footer stands under the track's box: " + (s.bodyBox.bottom - s.trackBox.bottom));
      near(s.trackRange, s.bodyRange, "the track's scroll range is the body's (list " + s.listHeight + ", body content " + s.bodyScrollHeight + ", header " + s.offset + ")", 2);
      for (const k of ["c3", "c4", "c30", "c40", "chg"]) assert.ok(s.marks[k], k + "'s mark is painted");
      // level: the card's top is its mark's top, in the viewport, for every card nothing pushes
      near(s.cards.c3.top, s.marks.c3!.top, "paragraph 3's card is level with its highlight");
      near(s.cards.chg.top, s.marks.chg!.top, "the change card is level with its tint");
      assert.equal(s.cards.c3.pushed, null); assert.equal(s.cards.chg.pushed, null);
      // colliding: paragraph 4's highlight is one paragraph under 3's, closer than a card is tall
      assert.ok(s.marks.c4!.top - s.marks.c3!.top < s.cards.c3.height, "the two marks are closer than a card is tall: " + (s.marks.c4!.top - s.marks.c3!.top) + " vs " + s.cards.c3.height);
      near(s.cards.c4.top, s.cards.c3.bottom + 8, "paragraph 4's card sits under paragraph 3's, a gap apart");
      assert.equal(s.cards.c4.pushed, "1");
      near(parseFloat(s.cards.c4.leader), s.cards.c4.top - s.marks.c4!.top, "the leader runs from the card up to the mark's height");
      // the whole-file comment has no mark: loose, at the top of the track's content, above every marked card
      assert.equal(s.marks.whole, null);
      assert.ok(s.cards.whole.top < s.cards.c3.top, "the loose card is above the marked ones");
      // paragraph 30 is far down: its card is below the box, level with a mark that is also below the box
      near(s.cards.c30.top, s.marks.c30!.top, "the far card is level with its far mark");
      // the lock: scrolling the body moves the track; the cards stay level with their marks
      await page.evaluate(() => { document.getElementById("body")!.scrollTop = 300; });
      await frames(page);
      s = await scene(page, keys);
      assert.equal(s.bodyScroll, 300);
      assert.equal(s.trackScroll, 300, "the track followed the body");
      near(s.cards.c3.top, s.marks.c3!.top, "still level after the scroll");
      near(s.cards.c4.top, s.cards.c3.bottom + 8, "still stacked after the scroll");
      // the reverse: a scroll of the track moves the body
      await page.evaluate(() => { (document.querySelector(".fileview-aside .fc-sec-cards") as HTMLElement).scrollTop = 120; });
      await frames(page);
      s = await scene(page, keys);
      assert.equal(s.trackScroll, 120);
      assert.equal(s.bodyScroll, 120, "the body followed the track");
      // the far end, from the cards' side: a wheel over the cards column runs the track to ITS end. That end must be
      // the body's — the body clamps at its own farthest position, and a track that can go on past it leaves every
      // card floating a footer's height above its mark, with nothing to bring the two back but a scroll of the body
      // (the poll re-renders nothing for an unchanged file). Chromium and Firefox both showed -109px here before the fix.
      await page.evaluate(() => { (document.querySelector(".fileview-aside .fc-sec-cards") as HTMLElement).scrollTop = 1e6; });
      await frames(page);
      s = await scene(page, keys);
      near(s.bodyScroll, s.bodyRange, "the body is at its end", 1);
      near(s.trackScroll, s.bodyScroll, "the track stopped where the body did, not a footer's height past it", 1);
      near(s.cards.c30.top, s.marks.c30!.top, "paragraph 30's card is level with its mark at the far end");
      near(s.cards.c40.top, s.marks.c40!.top, "the last paragraph's card is level with its mark at the far end");
      near(s.cards.c3.top, s.marks.c3!.top, "and so is paragraph 3's, far above the box");
      // the last passage's card is not a dead end: at the body's end its mark is in the body's last lines, and the
      // footer covers that height of the track — so the body's content must run on past its last passage by at least
      // the footer's height, or the card that is level with the mark sits under Send and Log where no scroll reaches it
      assert.ok(s.marks.c40!.top >= s.bodyBox.top && s.marks.c40!.bottom <= s.bodyBox.bottom + 1, "the last paragraph's mark is in the body's box: " + JSON.stringify(s.marks.c40) + " in " + JSON.stringify(s.bodyBox));
      assert.ok(s.cards.c40.top >= s.trackBox.top - 1 && s.cards.c40.bottom <= s.trackBox.bottom + 1, "its card is in the track's box, above the footer: " + JSON.stringify(s.cards.c40) + " in " + JSON.stringify(s.trackBox));
      // the far end from the body's side agrees
      await page.evaluate(() => { document.getElementById("body")!.scrollTop = 0; });
      await frames(page);
      await page.evaluate(() => { document.getElementById("body")!.scrollTop = 1e6; });
      await frames(page);
      s = await scene(page, keys);
      near(s.bodyScroll, s.bodyRange, "the body is at its end again", 1);
      near(s.trackScroll, s.bodyScroll, "the track came to the same end", 1);
      near(s.cards.c40.top, s.marks.c40!.top, "the last paragraph's card is level from this side too");
      // a click on the last card's reference: the centering clamps at the body's end, and the card is still in view
      await page.evaluate(() => { document.getElementById("body")!.scrollTop = 0; });
      await frames(page);
      await page.evaluate((key: string) => { (document.querySelector('.fc-card[data-id="' + key + '"] [data-act="fcgoto"]') as HTMLElement).click(); }, KEYS.c40);
      await frames(page);
      s = await scene(page, keys);
      assert.ok(s.marks.c40!.top >= s.bodyBox.top && s.marks.c40!.bottom <= s.bodyBox.bottom + 1, "the last mark is in the body's box after its reference was clicked");
      assert.ok(s.cards.c40.top >= s.trackBox.top - 1 && s.cards.c40.bottom <= s.trackBox.bottom + 1, "and its card is in the track's box: " + JSON.stringify(s.cards.c40) + " in " + JSON.stringify(s.trackBox));
      near(s.cards.c40.top, s.marks.c40!.top, "level with it");
      near(s.trackScroll, s.bodyScroll, "the track came along", 1);
      // a click on the far card's reference centers its mark in the body and brings the card with it
      await page.evaluate((key: string) => { (document.querySelector('.fc-card[data-id="' + key + '"] [data-act="fcgoto"]') as HTMLElement).click(); }, KEYS.c30);
      await frames(page);
      s = await scene(page, keys);
      const bodyBox = await page.evaluate(() => { const r = document.getElementById("body")!.getBoundingClientRect(); return { top: r.top, bottom: r.bottom }; });
      assert.ok(s.marks.c30!.top > bodyBox.top && s.marks.c30!.bottom < bodyBox.bottom, "the mark is in the body's box");
      assert.ok(s.cards.c30.top >= bodyBox.top && s.cards.c30.bottom <= bodyBox.bottom + 1, "the card is in view beside it");
      near(s.cards.c30.top, s.marks.c30!.top, "and level with it");
      assert.equal(s.trackScroll, s.bodyScroll, "the track came along");
    });
  });

  test(`in ${name}: the narrow fold (the sheet's container query) reaches the panel as the list layout, and the columns bring the margin back`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      let s = await scene(page, KEYS);
      assert.equal(s.margin, true);
      // the card is the query container: a container query styles a container's descendants, never the container itself,
      // so the row's own stacking rule needs the card above it to be one (the viewer's `.fileview` rule; found here 2026-09-07)
      const container: string = await page.evaluate(() => getComputedStyle(document.getElementById("wrap")!).containerType);
      assert.equal(container, "inline-size", "the viewer's card declares the container the fold resolves against");
      await page.evaluate(() => { document.getElementById("wrap")!.style.width = "600px"; });   // under the 680px container query: the aside folds below the body
      await frames(page, 3);
      s = await scene(page, KEYS);
      assert.equal(s.flex, "column", "the sheet stacked the row");
      assert.equal(s.margin, false, "the list layout");
      assert.equal(s.footIn, "fc-cards", "the foot is back in the list");
      const tops: string[] = await page.evaluate(() => Array.from(document.querySelectorAll(".fileview-aside .fc-card")).map((c) => (c as HTMLElement).style.top));
      assert.ok(tops.length >= 4 && tops.every((t: string) => t === ""), "no placed tops in the list: " + JSON.stringify(tops));
      await page.evaluate(() => { document.getElementById("wrap")!.style.width = "1000px"; });
      await frames(page, 3);
      s = await scene(page, KEYS);
      assert.equal(s.flex, "row");
      assert.equal(s.margin, true, "the margin layout is back");
      near(s.cards.c3.top, s.marks.c3!.top, "level again");
    });
  });
}

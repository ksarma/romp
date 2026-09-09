// A comment whose passage lies inside a CLOSED <details> (plans/markdown-viewer.md, Slice 4: the front matter renders as a
// closed details, `> [!type]-` as a folded callout, both reached from plain markdown; before this slice only an author's
// own <details> HTML made one). The panel's highlight paints inside the fold: Chromium lays the hidden content out on a
// forced read, so the mark HAS a box (the margin pass placed its card level with a phantom) but checkVisibility() is false
// and the person sees nothing. Every control that scrolls to a card's mark then scrolled to a shut fold with no highlight
// anywhere: the card's head (fccard, whose opening centers the mark in the margin layout), the card's quote button (fcgoto,
// goTo), the mark's own activation (fcopen, showCard's scrollCard). scrollIntoView reveals nothing (the browser's fragment
// navigation runs the HTML spec's ancestor revealing steps first; scrollIntoView does not), and neither did centerOn. The
// panel now runs those steps on its own marks (md-sanitize.ts revealFragmentTarget, what the viewer's `#` landing runs)
// before it scrolls, and in the margin layout re-runs the pass first, since the fold's opening moves everything below it.
// Over the REAL file-comments.ts bundle in headless Chromium, mounted as file-comments-margin-browser.test.ts mounts it,
// the markdown parsed by the one configuration (md-config.ts applyMdConfig) so the folds are the viewer's own. Two
// layouts: the margin (1000px) and the list (600px, under the sheet's 680px container query). Controls: a comment in an
// OPEN callout and one on a plain paragraph, which the same clicks reached before the fix, so the click path itself is
// never in question. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do.
// Synthetic values only: an invented note, a placeholder sid, TESTHOST paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { CARD_GAP } from "./card-layout";                          // the margin layout's pure half: the earliest a card may begin is one gap under the track's top

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** The panel's registry entry and marked, with the viewer's grammar applied, bundled as the webview build bundles them. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\nimport { applyMdConfig } from "./md-config";\napplyMdConfig();\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "goto-details-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the scene lives under: the viewer's body and prose, the constructs (callouts, front matter) and the whole
 *  file-comments block (the row, the aside and its fold, the cards, the highlights, the margin layout). */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  const constructs = FEED.split("\n").filter((l) => l.startsWith(".md ") && /md-callout|md-frontmatter/.test(l)).join("\n");
  assert.ok(constructs.includes("md-frontmatter") && constructs.includes("md-callout"), "the constructs' rules in feed.css");
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4, .fileview-md h5, .fileview-md h6"), rule(".fileview-btn"), constructs, FEED.slice(a, b)].join("\n");
}
// the viewer's own ancestry: `.fileview` (the card) > `.fileview-main` (the row) > `.fileview-body` + the aside the panel mounts
const PAGE = (width: number): string => `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; --box-border: #444; --err: #f66; --st-awaitbg-bg: #7c7; --st-compacting-bg: #6cc; }
${sheet()}
#wrap { width: ${width}px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/probe.js"></script></body></html>`;

// ── the note and its comments (synthetic prose) ────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/tmp/TESTHOST/notes-api/docs/report.md";
const T0 = 1757145600000;
const filler = (n: number, tag: string): string => Array.from({ length: n }, (_, i) => `Filler paragraph ${tag} ${i + 1} with enough words to take a line of its own on the page.`).join("\n\n");
// front matter (a closed details), a folded callout, a folded callout holding a second folded callout (two closed ancestors),
// an OPEN callout (a control) and a plain paragraph (a control), fillers between so every passage is below the fold at 500px
const SRC = [
  "---", "title: Test Note", "tags: [a, b]", "---", "",
  "# Report", "",
  "Intro paragraph of the report.", "",
  filler(12, "A"), "",
  "> [!tip]- Folded tip",
  "> Hidden body.", "",
  filler(12, "B"), "",
  "> [!note]- Outer fold",
  "> Outer body line.",
  ">",
  "> > [!note]- Inner fold",
  "> > Inner hidden body.", "",
  filler(12, "C"), "",
  "> [!important]+ Open note",
  "> Shown body.", "",
  filler(12, "D"), "",
  "Control paragraph near the end with the control phrase.", "",
].join("\n");
const comment = (i: number, quote: string, prefix: string, suffix: string): Record<string, unknown> => ({
  id: (T0 + i) + "-" + i, author: "you", ts: T0 + i, body: "Note " + i + ".", anchor: { quote, prefix, suffix }, replies: [], resolved: false,
});
const C = {
  fm: comment(1, "title: Test Note", "---\n", "\ntags"),
  hidden: comment(2, "Hidden body.", "> ", ""),
  nested: comment(3, "Inner hidden body.", "> > ", ""),
  open: comment(4, "Shown body.", "> ", ""),
  ctl: comment(5, "Control paragraph near the end", "", " with the control phrase"),
};
const KEY = Object.fromEntries(Object.entries(C).map(([k, c]) => [k, c.id as string])) as Record<keyof typeof C, string>;
const FOLDED: Array<keyof typeof C> = ["fm", "hidden", "nested"];
const CONTROLS: Array<keyof typeof C> = ["open", "ctl"];
const COMMENTS = Object.values(C);
const STATUS = {
  verb: "status", root: "/tmp/TESTHOST/notes-api", storePath: "/tmp/TESTHOST/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: COMMENTS }, hunks: [], log: [],
  unsent: { comments: COMMENTS.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
};

type Read = {
  margin: boolean; painted: boolean; text: string | null;
  closedAbove: number;                                            // closed <details> ancestors whose CONTENT holds the mark (the summary is in view already)
  visible: boolean | null;                                        // checkVisibility(): false inside a closed details, whatever its box says
  markTop: number | null; markBottom: number | null; cardTop: number | null;
  trackTop: number;                                               // the track's top in the viewport: the highest a card can stand (a mark above it, in the header's band, has its card clamped there)
  bodyBox: { top: number; bottom: number }; bodyScroll: number; trackScroll: number; modeCalls: string[];
};

/** Mount the panel over the rendered note, answer its status asks, open it, and let the paint and the pass run. */
function mount(page: any): Promise<void> {
  return page.evaluate(async ([src, status, abs, sid]: [string, Record<string, unknown>, string, string]) => {
    const w = window as any;
    const body = document.getElementById("body")!, md = document.getElementById("md")!;
    md.innerHTML = w.__romp.marked.parse(src);
    w.__initialOpen = Array.from(md.querySelectorAll("details")).map((d) => d.hasAttribute("open"));   // the folds as the note wrote them
    const posted: any[] = [];
    const rendered: Array<() => void> = [];
    w.__modeCalls = [];
    const ctx = {
      path: abs, sid, todoId: null,
      body: () => body, mode: () => "rendered", text: () => src, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null,
      renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
      onRendered: (cb: () => void) => { rendered.push(cb); }, onSelection: () => { /* inert */ }, onSaved: () => { /* inert */ }, onClose: () => { /* inert */ },
      post: (m: any) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ }, guardClose: () => { /* inert */ },
      aside: (node: HTMLElement | null) => { const main = document.getElementById("main")!; main.querySelector(".fileview-aside")?.remove(); if (node) { node.classList.add("fileview-aside"); main.appendChild(node); } },
      setMode: (m: string) => { w.__modeCalls.push(m); }, scrollToOffset: () => { /* inert */ }, reload: () => { /* inert */ },
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
const read = (page: any, id: string): Promise<Read> => page.evaluate((id: string) => {
  const body = document.getElementById("body")!, aside = document.querySelector(".fileview-aside") as HTMLElement;
  const track = aside.querySelector(".fc-sec-cards") as HTMLElement;
  const b = body.getBoundingClientRect();
  const m = body.querySelector('.fc-hl[data-id="' + id + '"]') as HTMLElement | null;
  let closedAbove = 0;
  for (let n: Element | null = m; n; n = n.parentElement) {
    const p = n.parentElement;
    if (p && p.localName === "details" && n.localName !== "summary" && !p.hasAttribute("open")) closedAbove++;
  }
  const r = m ? m.getBoundingClientRect() : null;
  const card = aside.querySelector('.fc-card[data-id="' + id + '"]');
  return {
    margin: aside.classList.contains("fc-margin"), painted: !!m, text: m ? m.textContent : null, closedAbove,
    visible: m ? (m as any).checkVisibility() : null,
    markTop: r ? r.top : null, markBottom: r ? r.bottom : null, cardTop: card ? card.getBoundingClientRect().top : null,
    trackTop: track.getBoundingClientRect().top,
    bodyBox: { top: b.top, bottom: b.bottom }, bodyScroll: body.scrollTop, trackScroll: track.scrollTop, modeCalls: (window as any).__modeCalls,
  };
}, id);
/** The scene as the note opened: the body at its top, every fold as the note wrote it. */
const reset = (page: any): Promise<void> => page.evaluate(() => {
  document.getElementById("body")!.scrollTop = 0;
  const initial: boolean[] = (window as any).__initialOpen;
  Array.from(document.querySelectorAll("#md details")).forEach((d, i) => { if (initial[i]) d.setAttribute("open", ""); else d.removeAttribute("open"); });
});
const frames = (page: any, n = 3): Promise<void> => page.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
const near = (a: number, b: number, msg: string, tol = 1) => assert.ok(Math.abs(a - b) <= tol, msg + ": " + a + " vs " + b);
/** The three controls that scroll to a card's mark, activated as the delegate hears them (a click event on the node). */
const ROUTES = {
  head: (id: string) => '.fc-card[data-id="' + id + '"] .fc-card-head',              // fccard: the card opens and its mark is centered (afterRender)
  goto: (id: string) => '.fc-card[data-id="' + id + '"] [data-act="fcgoto"]',         // fcgoto: goTo
  mark: (id: string) => '#body .fc-hl[data-id="' + id + '"]',                         // fcopen: showCard, then scrollCard (a saved reply's scroll shares it)
};
const click = (page: any, sel: string): Promise<void> => page.evaluate((sel: string) => { const n = document.querySelector(sel) as HTMLElement | null; if (!n) throw new Error("no node for " + sel); n.click(); }, sel);

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, width: number, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright chromium on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    const page = await browser.newPage({ viewport: { width: 1100, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE(width) });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await mount(page);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

/** The scene every leg starts from: five marks painted, the three in folds hidden (the case is real), the two controls shown. */
async function expectFoldedScene(page: any): Promise<void> {
  const folds: Array<[string, boolean, string]> = await page.evaluate(() => Array.from(document.querySelectorAll("#md details")).map((d) => [d.className, d.hasAttribute("open"), (d.querySelector("summary")?.textContent || "").trim()]));
  assert.deepEqual(folds, [["md-frontmatter", false, "Front matter"], ["md-callout md-callout-tip", false, "Folded tip"], ["md-callout md-callout-note", false, "Outer fold"], ["md-callout md-callout-note", false, "Inner fold"], ["md-callout md-callout-important", true, "Open note"]], "the note's folds, as the one grammar renders them");
  for (const k of [...FOLDED, ...CONTROLS]) {
    const r = await read(page, KEY[k]);
    assert.equal(r.painted, true, k + "'s mark is painted");
    assert.equal(r.text, (C[k].anchor as { quote: string }).quote, k + "'s mark is the passage");
  }
  for (const k of FOLDED) {
    const r = await read(page, KEY[k]);
    assert.ok(r.closedAbove >= (k === "nested" ? 2 : 1), k + "'s mark is inside a closed fold: " + r.closedAbove);
    assert.equal(r.visible, false, k + "'s mark is not visible while its fold is shut");
  }
  for (const k of CONTROLS) {
    const r = await read(page, KEY[k]);
    assert.equal(r.closedAbove, 0, k + "'s mark is in no fold");
    assert.equal(r.visible, true, k + "'s mark is visible");
  }
}
/** After a control scrolled to the mark: the fold open, the mark visible and inside the body's box, no switch to Raw. */
function expectRevealed(r: Read, what: string): void {
  assert.equal(r.closedAbove, 0, what + ": every closed fold above the mark was opened");
  assert.equal(r.visible, true, what + ": the mark is visible");
  assert.ok(r.markTop !== null && r.markTop >= r.bodyBox.top - 1 && r.markBottom! <= r.bodyBox.bottom + 1, what + ": the mark is in the body's box: " + JSON.stringify([r.markTop, r.markBottom, r.bodyBox]));
  assert.deepEqual(r.modeCalls, [], what + ": no fall back to Raw (the panel's own mark is in the view)");
}

test("margin layout: the card's head, its quote button and the mark's activation open the fold(s) around a comment's passage, scroll it into view and place the card level with it", async (t) => {
  await inBrowser(t, 1000, async (page) => {
    let r = await read(page, KEY.fm);
    assert.equal(r.margin, true, "the margin layout is on at 1000px");
    await expectFoldedScene(page);
    for (const k of FOLDED) {
      for (const [route, sel] of Object.entries(ROUTES)) {
        await reset(page); await frames(page);
        r = await read(page, KEY[k]);
        assert.ok(r.closedAbove >= 1 && r.visible === false, k + " before the " + route + " click: folded again");
        await click(page, sel(KEY[k])); await frames(page);
        r = await read(page, KEY[k]);
        const what = k + " after the " + route + " click";
        expectRevealed(r, what);
        // the fold's opening moved everything below it: the pass ran again before the centering, so the card is level with
        // the mark where it stands now, not with the phantom the shut fold laid out, and the track came along with the body.
        // The front matter is the note's first block: its mark stands in the header's band, above the track's top, where
        // the layout clamps the card at its floor, one gap under the track's top (the body cannot scroll above its own top
        // to bring the two level)
        near(r.cardTop!, Math.max(r.markTop!, r.trackTop + CARD_GAP), what + ": the card is level with its mark (or at the layout's floor for a mark in the header's band)");
        near(r.trackScroll, r.bodyScroll, what + ": the track is at the body's position");
      }
    }
    // the controls: the same clicks reach a passage in an open callout and a plain paragraph as before
    for (const k of CONTROLS) {
      await reset(page); await frames(page);
      await click(page, ROUTES.goto(KEY[k])); await frames(page);
      r = await read(page, KEY[k]);
      expectRevealed(r, k + " after the goto click");
      near(r.cardTop!, r.markTop!, k + ": the card is level with its mark");
    }
    // the open callout is still open: no fold the person left open was touched by a reveal elsewhere
    const openNote: boolean = await page.evaluate(() => document.querySelector("#md details.md-callout-important")!.hasAttribute("open"));
    assert.equal(openNote, true, "the open callout stays open");
  });
});

test("list layout (the narrow fold): the quote button opens the fold(s) around the passage and scrolls it into view", async (t) => {
  await inBrowser(t, 600, async (page) => {
    let r = await read(page, KEY.fm);
    assert.equal(r.margin, false, "the list layout at 600px");
    await expectFoldedScene(page);
    for (const k of FOLDED) {
      await reset(page); await frames(page);
      await click(page, ROUTES.goto(KEY[k])); await frames(page);
      r = await read(page, KEY[k]);
      expectRevealed(r, k + " after the goto click (list layout)");
    }
    for (const k of CONTROLS) {
      await reset(page); await frames(page);
      await click(page, ROUTES.goto(KEY[k])); await frames(page);
      r = await read(page, KEY[k]);
      expectRevealed(r, k + " after the goto click (list layout)");
    }
  });
});

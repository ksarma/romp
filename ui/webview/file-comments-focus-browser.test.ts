// The focus follow-on (plans/file-review.md, "The focus follow-on (2026-09-08)" under the margin-layout note) in a REAL
// engine: the worktree's file-comments.ts, bundled the way the webview is built, mounted over a rendered markdown body
// laid out under feed.css's own rules. The defect the user hit: a change card for a whole replaced paragraph, open,
// stood several hundred pixels tall above a comment's card in the track; the placement pass only ever pushed cards
// DOWN, so the comment's card sat a viewport below its highlight, and a click on the highlight scrolled the body as
// far as kept the highlight's top in view — the highlight at the top edge of the body, the card still out of sight.
// This leg builds that document (a short paragraph replaced by a long one, a comment on a phrase a few lines into the
// new text), opens the change card, clicks the comment's highlight, and measures: the comment's card level with its
// highlight and both in view; the tall change card above it moved UP out of the way and folded to its collapsed height
// with Show more at its foot; Show more opening it whole and making it the focus; Show less folding it again; and the
// narrow fold (the list layout) clipping nothing. The Show more row is measured as RENDERED — its box and its computed
// display — never read from the `hidden` property the panel writes itself (the verification review, 2026-09-09): the
// sheet's `.fc-clip-row { display: flex; }` beats the UA's rule for [hidden], and only its own `[hidden] { display: none; }`
// keeps a hidden row from rendering a Show more on every card with nothing cut, so the leg reads no box where the pass
// hides the row (the comment's short card in the margin layout, every card in the list layout) and a box where it shows
// it. Runs in Chromium and Firefox; skips LOUDLY without a playwright browser (CI installs none), as the other browser
// legs do. Synthetic values only: invented prose, placeholder ids.
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
      resolveDir: UI, loader: "ts", sourcefile: "focus-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under: the body, the rendered prose (the headings as the document type scale writes them), the buttons, and the whole file-comments block
 *  (the row, the aside and its fold, the panel, the cards, the highlights, the margin layout and the fold of a tall card). */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4, .fileview-md h5, .fileview-md h6"), rule(".fileview-md h1"), rule(".fileview-md h1, .fileview-md h2"), rule(".fileview-btn"), FEED.slice(a, b)].join("\n");
}
// the viewer's own ancestry: `.fileview` (the card) > `.fileview-main` (the row) > `.fileview-body` + the aside the panel mounts
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --text-muted: #888; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --overlay-10: rgba(255,255,255,0.1); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; }
${sheet()}
#wrap { width: 1000px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/focus.js"></script></body></html>`;

// ── the document and its comments (synthetic prose) ────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
// the replaced paragraph: the session rewrote a one-line paragraph 5 as a long one — long enough that its card, open,
// stands taller than the track when its old and new text show whole
const OLD = "Paragraph 5 of the report was one line about the cache.";
const SENTENCE = (i: number): string => "Sentence " + i + " of the new paragraph 5 says more about the cache, the latency budget, the plan for the next release and the reasons the team settled on it.";
const NEW = Array.from({ length: 10 }, (_, i) => SENTENCE(i + 1)).join(" ");
const SRC = "# Report\n\n" + Array.from({ length: 30 }, (_, i) => (i === 4 ? NEW : PARA(i + 1))).join("\n\n") + "\n";
// the comment: on a phrase a few lines into the new paragraph, so its highlight stands where the open change card's box
// covers it, the collapsed card included
const QUOTE = "Sentence 4 of the new paragraph 5";
const COMMENT = { id: (T0 + 1) + "-6", author: "you", ts: T0 + 1, body: "Say which cache.", anchor: { quote: QUOTE, prefix: "settled on it. ", suffix: " says more" }, replies: [], resolved: false };
const NEW_AT = SRC.indexOf(NEW);
const HUNK = { id: "h1", author: "api", ts: T0 - 30000, kind: "sub", curFrom: NEW_AT, curTo: NEW_AT + NEW.length, baseFrom: NEW_AT, baseTo: NEW_AT + OLD.length, oldText: OLD, newText: NEW, anchor: null };
const STATUS = {
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: [COMMENT] },
  hunks: [HUNK], log: [],
  unsent: { comments: [COMMENT.id], replies: [], accepted: 0, rejected: 0, watermark: null },
};
const KEYS = { chg: "chg:h1", c: COMMENT.id };

type Box = { top: number; bottom: number; height: number };
type Scene = {
  margin: boolean; flex: string; offset: number;
  cards: Record<string, (Box & { open: boolean; pushed: string | null; pulled: string | null }) | null>; marks: Record<string, Box | null>;
  bodyScroll: number; trackScroll: number; bodyBox: Box; trackBox: Box; trackHeight: number;
};
type Fold = {
  clipped: string | null; scrollH: number; clientH: number; maxH: string; lineH: string;
  rowHidden: boolean | null; rowDisplay: string | null; rowH: number; label: string | null; buttonH: number; cardH: number; more: boolean;
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
  const box = (el: Element): { top: number; bottom: number; height: number } => { const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height }; };
  const cards: Record<string, any> = {}, marks: Record<string, any> = {};
  for (const [name, key] of Object.entries(keys)) {
    const card = aside.querySelector('.fc-card[data-id="' + key + '"]') as HTMLElement | null;
    cards[name] = card ? { ...box(card), open: card.classList.contains("open"), pushed: card.dataset.pushed ?? null, pulled: card.dataset.pulled ?? null } : null;
    const act = key.startsWith("chg:") ? "fcchange" : "fcopen", id = key.startsWith("chg:") ? key.slice(4) : key;
    // a change's marks are several (the struck old text's point, the new text's tint): the highest is the card's mark
    const ms = Array.from(body.querySelectorAll('[data-act="' + act + '"][data-id="' + id + '"]')).map(box).filter((b) => b.height > 0);
    marks[name] = ms.length ? ms.reduce((a, b) => (b.top < a.top ? b : a)) : null;
  }
  return {
    margin: aside.classList.contains("fc-margin"), flex: getComputedStyle(document.getElementById("main")!).flexDirection,
    offset: track.getBoundingClientRect().top - body.getBoundingClientRect().top,
    cards, marks, bodyScroll: body.scrollTop, trackScroll: track.scrollTop, bodyBox: box(body), trackBox: box(track), trackHeight: track.clientHeight,
  };
}, keys);
/** The fold of one card: its clipped part (a change's old and new text, a comment's body), the toggle's row — the
 *  property, the computed display and the rendered box — its label and box, and the card's own height. */
const fold = (page: any, key: string): Promise<Fold> => page.evaluate((key: string) => {
  const card = document.querySelector('.fileview-aside .fc-card[data-id="' + key + '"]') as HTMLElement;
  const part = card.querySelector(".fc-clip") as HTMLElement;
  const row = card.querySelector(".fc-clip-row") as HTMLElement | null;
  const button = row ? (row.querySelector("button") as HTMLElement | null) : null;
  const cs = getComputedStyle(part);
  return {
    clipped: part.dataset.clipped ?? null, scrollH: part.scrollHeight, clientH: part.clientHeight, maxH: cs.maxHeight, lineH: cs.lineHeight,
    rowHidden: row ? row.hidden : null, rowDisplay: row ? getComputedStyle(row).display : null, rowH: row ? row.getBoundingClientRect().height : 0,
    label: button ? button.textContent : null, buttonH: button ? button.getBoundingClientRect().height : 0,
    cardH: card.getBoundingClientRect().height, more: card.classList.contains("fc-more"),
  };
}, key);
const frames = (page: any, n = 2): Promise<void> => page.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
const near = (a: number, b: number, msg: string, tol = 1) => assert.ok(Math.abs(a - b) <= tol, msg + ": " + a + " vs " + b);
/** The Show more row as rendered. A hidden row must take NO room: the `hidden` property alone is what the panel wrote
 *  (clipCards, clipRow), and a later or more specific `display` rule on `.fc-clip-row` would render a Show more on every
 *  card with nothing cut while the property still read true — so the row's box and computed display are what the leg
 *  holds, where the row is hidden and where it shows. */
const noRow = (f: Fold, msg: string): void => {
  assert.equal(f.rowHidden, true, msg + ": the row is hidden");
  assert.equal(f.rowDisplay, "none", msg + ": the hidden row's computed display");
  assert.equal(f.rowH, 0, msg + ": the hidden row takes no room");
  assert.equal(f.buttonH, 0, msg + ": the toggle has no box");
};
const rowShows = (f: Fold, msg: string): void => {
  assert.equal(f.rowHidden, false, msg + ": the row is shown");
  assert.equal(f.rowDisplay, "flex", msg + ": the row's computed display is the sheet's");
  assert.ok(f.rowH > 10, msg + ": the row has a box: " + f.rowH);
  assert.ok(f.buttonH > 10, msg + ": the toggle has a box: " + f.buttonH);
};
const wholeIn = (c: Box, of: Box): boolean => c.top >= of.top - 1 && c.bottom <= of.bottom + 1;
const click = (page: any, sel: string): Promise<void> => page.evaluate((sel: string) => { (document.querySelector(sel) as HTMLElement).click(); }, sel);
const markSel = (key: string): string => key.startsWith("chg:") ? '#body [data-act="fcchange"][data-id="' + key.slice(4) + '"]' : '#body [data-act="fcopen"][data-id="' + key + '"]';

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
      if (u.pathname === "/dist/focus.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: with a tall open change card above it, the comment whose highlight is clicked lands level with the highlight and in view, the change card moved up and folded to a few lines with Show more; Show more opens it whole as the focus, Show less folds it; the narrow fold clips nothing`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      let s = await scene(page, KEYS);
      assert.equal(s.flex, "row", "the row is two columns at 1000px");
      assert.equal(s.margin, true, "the margin layout is on");
      assert.ok(s.marks.chg && s.marks.c, "both marks are painted: " + JSON.stringify(s.marks));
      // the fixture: the comment's highlight is a few lines into the new paragraph — under the change card's box once
      // that card is open, so the two cards contend for the same height
      const apart = s.marks.c!.top - s.marks.chg!.top;
      assert.ok(apart > 20 && apart < 200, "the highlight stands a few lines under the change's mark: " + apart);
      near(s.cards.chg!.top, s.marks.chg!.top, "the closed change card is level with its mark");
      // the change card opens from its mark: tall, with its old and new text
      await click(page, markSel(KEYS.chg));
      await frames(page);
      s = await scene(page, KEYS);
      assert.equal(s.cards.chg!.open, true, "the change card is open");
      const openChange = s.cards.chg!.height;
      assert.ok(openChange > s.marks.c!.top - s.marks.chg!.top + 40, "the fixture: the open change card covers the comment's highlight and more: " + openChange);
      // the defect's click: the comment's highlight
      await click(page, markSel(KEYS.c));
      await frames(page);
      s = await scene(page, KEYS);
      assert.equal(s.cards.c!.open, true, "the comment's card is open");
      near(s.cards.c!.top, s.marks.c!.top, "the comment's card is level with its highlight (the defect: it sat a viewport below)");
      assert.ok(wholeIn(s.marks.c!, s.bodyBox), "the highlight is in the body's box: " + JSON.stringify(s.marks.c) + " in " + JSON.stringify(s.bodyBox));
      assert.ok(wholeIn(s.cards.c!, s.trackBox), "the comment's card is in the track's box: " + JSON.stringify(s.cards.c) + " in " + JSON.stringify(s.trackBox));
      assert.equal(s.cards.c!.pushed, null, "the focused card is not pushed");
      // the comment's card: a short body, nothing cut, so the pass leaves its Show more row hidden — and the row takes no
      // room as rendered (the property is the panel's own word; the box is the engine's)
      const fc = await fold(page, KEYS.c);
      assert.equal(fc.clipped, null, "the comment's short body is not cut");
      noRow(fc, "no Show more on a card with nothing cut, in the margin layout");
      // the change card above moved UP out of the way — its end a gap above the comment's card — instead of pushing the
      // comment's card down; its mark is inside its box, so it draws no leader
      near(s.cards.chg!.bottom + 8, s.cards.c!.top, "the change card's end sits a gap above the focused card");
      assert.ok(s.cards.chg!.top < s.marks.chg!.top - 1, "the change card moved up from its mark: " + s.cards.chg!.top + " vs " + s.marks.chg!.top);
      assert.equal(s.cards.chg!.pulled, null, "no leader: its mark's top is inside the card's box");
      // ...and folded: the change's old and new text clipped to eight lines with a fade, Show more at the foot, the card
      // far shorter than the whole text would make it
      let f = await fold(page, KEYS.chg);
      assert.equal(f.clipped, "1", "the change's old and new text is clipped");
      assert.ok(f.scrollH > f.clientH + 20, "the old and new text overflows its clipped box: " + f.scrollH + " vs " + f.clientH);
      const lh = parseFloat(f.lineH);
      assert.ok(lh > 0, "the part's computed line-height is a length: " + f.lineH);
      near(parseFloat(f.maxH), 8 * lh, "the cap is eight lines (8lh)", 1);
      rowShows(f, "the Show more row shows");
      assert.equal(f.label, "Show more");
      assert.ok(f.cardH < f.scrollH, "the card is shorter than its old and new text whole: " + f.cardH + " vs " + f.scrollH);
      assert.equal(s.cards.chg!.height, f.cardH);
      // Show more: the old and new text shows whole, the card is the focus — level with its mark — and the comment's card
      // is pushed below it as the push-down rule always had it
      await click(page, '.fileview-aside .fc-card[data-id="' + KEYS.chg + '"] [data-act="fcclip"]');
      await frames(page);
      f = await fold(page, KEYS.chg);
      assert.equal(f.more, true, "the card wears the open-bodies class");
      assert.equal(f.clipped, null, "no fade on an open body");
      near(f.scrollH, f.clientH, "the old and new text is shown whole", 1);
      assert.equal(f.maxH, "none", "no cap on an open body");
      assert.equal(f.label, "Show less");
      rowShows(f, "the row shows with Show less");
      s = await scene(page, KEYS);
      near(s.cards.chg!.top, s.marks.chg!.top, "the change card is the focus now: level with its mark");
      near(s.cards.c!.top, s.cards.chg!.bottom + 8, "the comment's card is pushed under it");
      assert.equal(s.cards.c!.pushed, "1");
      assert.ok(s.cards.chg!.height > f.cardH - 1 && s.cards.chg!.height > 300, "the whole card is tall: " + s.cards.chg!.height);
      // Show less: folded again
      await click(page, '.fileview-aside .fc-card[data-id="' + KEYS.chg + '"] [data-act="fcclip"]');
      await frames(page);
      f = await fold(page, KEYS.chg);
      assert.equal(f.more, false);
      assert.equal(f.clipped, "1", "clipped again");
      assert.equal(f.label, "Show more");
      // the narrow fold: the list layout keeps full bodies and offers no toggle
      await page.evaluate(() => { document.getElementById("wrap")!.style.width = "600px"; });
      await frames(page, 3);
      s = await scene(page, KEYS);
      assert.equal(s.flex, "column", "the sheet stacked the row");
      assert.equal(s.margin, false, "the list layout");
      f = await fold(page, KEYS.chg);
      assert.equal(f.maxH, "none", "no cap in the list");
      near(f.scrollH, f.clientH, "the old and new text is whole in the list", 1);
      noRow(f, "no Show more in the list");
      noRow(await fold(page, KEYS.c), "no Show more on the comment's card in the list");
      // ...and the columns bring the fold back
      await page.evaluate(() => { document.getElementById("wrap")!.style.width = "1000px"; });
      await frames(page, 3);
      s = await scene(page, KEYS);
      assert.equal(s.margin, true, "the margin layout is back");
      f = await fold(page, KEYS.chg);
      assert.equal(f.clipped, "1", "clipped again in the margin");
      rowShows(f, "the row is back with the fold");
    });
  });
}

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside — the short word for a change's text (Change: Avoid) and the one for a forked side session (File comment: Avoid) — appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  // the sibling focus modules scan themselves the same way: a test module is new prose too, and its assertion messages
  // print to the person on failure (the verification review, 2026-09-09: this leg was the slice's one module that named
  // the folded part of a change card by the short word the plan, the sheets and the panel avoid). The scan sets its own
  // guard lines aside; the module has no identifier in the short word, so a bare-word scan holds.
  const SELF = fs.readFileSync(path.join(UI, "file-comments-focus-browser.test.ts"), "utf8").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
  assert.doesNotMatch(SELF, /\bdiffs?\b/i, "the folded part of a change card is the change's old and new text (CONTEXT.md, Change: Avoid)");
  assert.doesNotMatch(SELF, /\bthreads?\b/i, "a comment with replies is a file comment with a run of turns (CONTEXT.md, File comment: Avoid)");
  assert.doesNotMatch(SELF, /fleet/i, "no new identifiers or prose in the old word for the sessions pane");
  assert.doesNotMatch(SELF, /\/home\/[a-z]/, "no absolute home paths");
});

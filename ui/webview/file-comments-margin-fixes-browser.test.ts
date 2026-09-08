// The margin layout's second review round in a REAL engine (plans/file-review.md, "The margin-layout follow-on
// (2026-09-07)"): the worktree's file-comments.ts bundled the way the webview is built, mounted over a rendered
// markdown body under feed.css's own rules, as file-comments-margin-browser.test.ts mounts it. What only an engine
// can show: that an opened card whose height the browser laid out — a few replies' turns — lands WHOLE in the track's
// box when its head or its reference link is clicked (the scroll that shows the card's end is track content, with no
// header term; one added on top put the card's head under the panel's header for every card taller than the track
// less the header), that a card taller than the track is clipped at its head by the excess alone, and that a comment
// saved with the text scrolled far down brings its card into view: a whole-file comment's card loose at the top of the
// track (the track to it, the body with it through the lock), a reply's card to its mark. Runs in Chromium and Firefox;
// skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only:
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

/** The panel's registry entry and marked, bundled as the webview build bundles them (in memory), as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "margin-fixes-probe.ts",
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
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4"), rule(".fileview-btn"), FEED.slice(a, b)].join("\n");
}
// the viewer's own ancestry: `.fileview` (the card) > `.fileview-main` (the row) > `.fileview-body` + the aside the panel mounts.
// 530px: the review's 500px plus the filter's row (All · Comments · Changes, under the toggles), so the track holds what it did
// then — the reply case below centers paragraph 3's card while the reply's box still stands in it, and a card taller than the
// track is clipped at its head by the excess (file-comments-margin-fixes.test.ts), which the box's leaving does not undo
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; }
${sheet()}
#wrap { width: 1000px; height: 530px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/margin-fixes.js"></script></body></html>`;

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
// replies of one line and of two (the second wraps in the 340px card), so the open cards' heights step through the band a
// header-term scroll clipped — (track − header − gap, track − gap], the header's height wide — whatever the engine's font
// metrics: at least one candidate lands in it (the leg asserts so), and the tallest does not fit the track at all
const REPLY = (i: number, long: boolean): Record<string, unknown> => ({ author: "api", ts: T0 + 100 + i, body: long ? "Reply " + (i + 1) + ": the cache is the one the api session added for the notes list, and the latency figure is from the staging run last week." : "Reply " + (i + 1) + " about the cache." });
const replies = (n: number, longAt: number | null): Record<string, unknown>[] => Array.from({ length: n }, (_, i) => REPLY(i, i === longAt));
const CANDIDATES: Array<{ para: number; n: number; longAt: number | null }> = [{ para: 12, n: 3, longAt: null }, { para: 16, n: 3, longAt: 0 }, { para: 20, n: 4, longAt: null }, { para: 24, n: 4, longAt: 0 }, { para: 28, n: 5, longAt: null }, { para: 32, n: 6, longAt: null }];
const CANDS: Array<Record<string, unknown>> = CANDIDATES.map((c, k) => ({ ...comment(c.para, 10 + k), replies: replies(c.n, c.longAt) }));
// marks on paragraphs 3 and 4 (a line apart: the second card cannot fit beside its paragraph), the candidates four paragraphs
// apart (closed, none reaches the next), and on paragraph 40 (the last one)
const COMMENTS: Array<Record<string, unknown>> = [WHOLE, comment(3, 1), comment(4, 2), ...CANDS, comment(40, 4)];
const KEYS: Record<string, string> = { c3: COMMENTS[1].id as string, c4: COMMENTS[2].id as string, c40: COMMENTS[COMMENTS.length - 1].id as string, whole: WHOLE.id };
CANDIDATES.forEach((c, k) => { KEYS["p" + c.para] = CANDS[k].id as string; });
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
  trackHeight: number; composerHidden: boolean;                   // the track's box height; whether the composer is closed
};

/** Mount the panel over the rendered document, answer its status asks, open it, and let the paint and the pass run. */
function mount(page: any, status: Record<string, unknown> = STATUS): Promise<void> {
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
  }, [SRC, status, ABS, SID]);
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
    trackHeight: track.clientHeight, composerHidden: (aside.querySelector(".fc-composer") as HTMLElement).hidden,
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
      if (u.pathname === "/dist/margin-fixes.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

/** The last request the panel posted, answered with `status` (the kernel's reply as a window message). */
const answer = (page: any, status: Record<string, unknown>): Promise<void> => page.evaluate((status: Record<string, unknown>) => {
  const p = (window as any).__posted; const last = p[p.length - 1];
  window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: last.reqId, ...status } }));
}, status);
const lastVerb = (page: any): Promise<string> => page.evaluate(() => { const p = (window as any).__posted; return p.length ? p[p.length - 1].verb : ""; });
const awaitVerb = (page: any, verb: string): Promise<void> => page.waitForFunction((verb: string) => { const p = (window as any).__posted; return p.length > 0 && p[p.length - 1].verb === verb; }, verb, { timeout: 5000 });
const click = (page: any, sel: string): Promise<void> => page.evaluate((sel: string) => { (document.querySelector(sel) as HTMLElement).click(); }, sel);
const cardSel = (key: string, inner: string): string => '.fileview-aside .fc-card[data-id="' + key + '"] ' + inner;
const wholeIn = (c: Box, of: Box): boolean => c.top >= of.top - 1 && c.bottom <= of.bottom + 1;
const NS9 = "1757145600000000009", NS10 = "1757145600000000010";
const FRESH = { id: (T0 + 5000) + "-0", author: "you", ts: T0 + 5000, body: "Add a summary at the top.", replies: [], resolved: false };

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: an opened card that fits the track lands whole in the track's box — its head under the header no more — after its head is clicked and after its reference link; a card taller than the track is clipped at its head by the excess alone`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      let s = await scene(page, KEYS);
      assert.equal(s.margin, true, "the margin layout is on");
      const T = s.trackHeight, offset = s.offset;
      assert.ok(offset > 40, "the header the track begins under: " + offset);
      const band = { lo: T - offset - 8, hi: T - 8 };       // open heights a header-term scroll clipped, that fit the track
      let inBand: string | null = null, tall: string | null = null;
      for (const c of CANDIDATES) {
        const k = "p" + c.para;
        await click(page, cardSel(KEYS[k], ".fc-card-head"));   // opens the card; the click centers it
        await frames(page, 3);
        s = await scene(page, KEYS);
        const card = s.cards[k], mark = s.marks[k]!;
        assert.ok(mark, k + "'s mark is painted");
        assert.ok(mark.top >= s.bodyBox.top - 1 && mark.bottom <= s.bodyBox.bottom + 1, k + "'s mark is in the body's box: " + JSON.stringify(mark) + " in " + JSON.stringify(s.bodyBox));
        near(s.trackScroll, s.bodyScroll, k + ": the track came along", 1);
        if (card.height + 8 <= T) {
          assert.ok(wholeIn(card, s.trackBox), k + " (" + card.height + "px, fits the " + T + "px track) is WHOLE in the track's box, head included: " + JSON.stringify(card) + " in " + JSON.stringify(s.trackBox));
          near(card.top, mark.top, k + " is level with its mark");
          if (inBand === null && card.height > band.lo) inBand = k;
        } else {
          // brought in as far as its end, the clipping at its head the excess over the track's box — or, where that would
          // take the mark's top out of the body's box, the header less the gap, the mark's top kept a gap under the body's top
          const excess = card.height + 8 - T;
          near(s.trackBox.top - card.top, Math.min(excess, offset - 8), k + " (" + card.height + "px, taller than the track) is clipped at its head by the excess alone, or by the header less the gap", 1.5);
          if (excess <= offset - 8) assert.ok(card.bottom <= s.trackBox.bottom + 1, k + ": its end is in the track's box: " + card.bottom + " vs " + s.trackBox.bottom);
          else near(mark.top, s.bodyBox.top + 8, k + ": the mark's top stays in view, a gap under the body's top", 1.5);
          if (tall === null) tall = k;
        }
        await click(page, cardSel(KEYS[k], ".fc-card-head"));   // fold: nothing moves, and the next candidate stands alone
        await frames(page, 2);
      }
      assert.ok(inBand, "the fixture: some candidate's open height is in the band a header-term scroll clipped (" + band.lo.toFixed(1) + ", " + band.hi + "]");
      assert.ok(tall, "the fixture: some candidate is taller than the track");
      // the reference link on an open card in the band, from the top of the text: the same whole card
      const k = inBand as string;
      await click(page, cardSel(KEYS[k], ".fc-card-head"));
      await frames(page, 3);
      await page.evaluate(() => { document.getElementById("body")!.scrollTop = 0; });
      await frames(page, 2);
      await click(page, cardSel(KEYS[k], '[data-act="fcgoto"]'));
      await frames(page, 3);
      s = await scene(page, KEYS);
      assert.ok(wholeIn(s.cards[k], s.trackBox), k + " is whole in the track's box after its reference link: " + JSON.stringify(s.cards[k]) + " in " + JSON.stringify(s.trackBox));
      near(s.cards[k].top, s.marks[k]!.top, "and level with its mark");
      near(s.trackScroll, s.bodyScroll, "the track came along", 1);
    });
  });

  test(`in ${name}: a whole-file comment saved with the text scrolled far down brings its card into view (the track to the loose card at its top, the body with it); a reply saved brings the card to its mark; the composer closes after`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      await page.evaluate(() => { document.getElementById("body")!.scrollTop = 1400; });
      await frames(page, 2);
      let s = await scene(page, KEYS);
      assert.equal(s.bodyScroll, 1400); near(s.trackScroll, 1400, "the track follows", 1);
      assert.ok(s.cards.whole.bottom < s.trackBox.top, "the loose card is above the track's box, out of view");
      await click(page, '.fileview-aside [data-act="fcfile"]');
      await page.focus(".fileview-aside .fc-composer .fc-input");
      await page.keyboard.type(FRESH.body);
      await page.keyboard.press("Control+Enter");   // the save chord (the composer follow-on: Enter alone adds a line)
      await awaitVerb(page, "comment");
      const req = await page.evaluate(() => (window as any).__posted.slice(-1)[0]);
      assert.equal(req.args.anchor, undefined, "a whole-file comment: no anchor");
      const withFresh = [...COMMENTS, FRESH];
      await answer(page, { ...STATUS, verb: "comment", storeMtimeNs: NS9, store: { ...STATUS.store, comments: withFresh } });
      await frames(page, 4);
      const keys = { ...KEYS, fresh: FRESH.id };
      s = await scene(page, keys);
      assert.ok(s.cards.fresh, "the new card is rendered");
      assert.equal(s.composerHidden, true, "the composer closed");
      assert.ok(wholeIn(s.cards.fresh, s.trackBox), "the new card is in the track's box: " + JSON.stringify(s.cards.fresh) + " in " + JSON.stringify(s.trackBox));
      near(s.trackScroll, s.bodyScroll, "the lock: the body came along with the track", 1);
      assert.ok(s.bodyScroll < 400, "the text is near its top, where the loose card is: " + s.bodyScroll);
      // a reply on paragraph 3's card: the card opened (its head; Reply stands in the open card), Reply, the text scrolled far
      // down meanwhile, the reply saved — the card comes back to its mark, whole in the track's box
      await click(page, cardSel(KEYS.c3, ".fc-card-head"));
      await frames(page, 3);
      await click(page, cardSel(KEYS.c3, '[data-act="fcreply"]'));
      await frames(page, 2);
      await page.evaluate(() => { document.getElementById("body")!.scrollTop = 1400; });
      await frames(page, 2);
      s = await scene(page, keys);
      assert.equal(s.bodyScroll, 1400);
      assert.equal(s.composerHidden, false, "the composer is up for the reply");
      await page.focus(".fileview-aside .fc-composer .fc-input");
      await page.keyboard.type("Which cache do you mean?");
      await page.keyboard.press("Control+Enter");   // the save chord
      await awaitVerb(page, "reply");
      assert.equal(await lastVerb(page), "reply");
      const c3r = { ...COMMENTS[1], replies: [{ author: "you", ts: T0 + 9000, body: "Which cache do you mean?" }] };
      await answer(page, { ...STATUS, verb: "reply", storeMtimeNs: NS10, store: { ...STATUS.store, comments: withFresh.map((c) => (c.id === KEYS.c3 ? c3r : c)) } });
      await frames(page, 4);
      s = await scene(page, keys);
      assert.equal(s.composerHidden, true, "the composer closed");
      assert.ok(s.cards.c3.height + 8 <= s.trackHeight, "the fixture: the card with its reply fits the track: " + s.cards.c3.height);
      assert.ok(s.marks.c3!.top >= s.bodyBox.top - 1 && s.marks.c3!.bottom <= s.bodyBox.bottom + 1, "the mark is in the body's box: " + JSON.stringify(s.marks.c3) + " in " + JSON.stringify(s.bodyBox));
      assert.ok(wholeIn(s.cards.c3, s.trackBox), "the card is whole in the track's box: " + JSON.stringify(s.cards.c3) + " in " + JSON.stringify(s.trackBox));
      // level with its mark — or, where the loose group above it (the whole-file cards, at the top of the track) reaches past
      // the mark, pushed down to the group's end and wearing the leader (card-layout.ts). Paragraph 3's mark is one line under
      // that reach: the head is a row taller since Show changes inline joined its button row (the file has a change, and three
      // buttons wrap at 340px), so the track begins that much lower and the card's desired top falls inside the group
      const floor = s.cards.fresh.bottom + 8;
      near(s.cards.c3.top, Math.max(s.marks.c3!.top, floor), "and level with its mark, or pushed to the loose group's end");
      if (floor > s.marks.c3!.top) { assert.equal(s.cards.c3.pushed, "1", "pushed by the loose group"); near(parseFloat(s.cards.c3.leader), floor - s.marks.c3!.top, "the leader spans the push", 1); }
      near(s.trackScroll, s.bodyScroll, "the track came along", 1);
    });
  });
}

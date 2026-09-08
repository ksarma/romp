// The margin layout's review findings in a REAL engine (plans/file-review.md, "The margin-layout follow-on
// (2026-09-07)"): the worktree's file-comments.ts bundled the way the webview is built, mounted over a rendered
// markdown body under feed.css's own rules, as file-comments-margin-browser.test.ts mounts it. What only an engine
// can show: the focus-fixup rule (a focused node the pass moves from the list to the footer loses the keyboard to
// the body unless it is given back), a content reflow the body's own ResizeObserver never reports (a <details>
// block opened moves every mark below it while the body's box stands), the Tab order reading down the margin (a
// head's focus scrolls the track, and the body with it), and the list's rows standing in the footer. Runs in
// Chromium and Firefox; skips LOUDLY without a playwright browser (CI installs none), as the other browser legs
// do. Synthetic values only: invented prose, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "margin-review-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under (the same slice the margin leg takes). */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4, .fileview-md h5, .fileview-md h6"), rule(".fileview-btn"), FEED.slice(a, b)].join("\n");
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; }
${sheet()}
#wrap { width: 1000px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/margin-review.js"></script></body></html>`;

// ── the document and its comments (synthetic prose) ────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
// a <details> block stands before paragraph 3 (DOMPurify's html profile keeps details and summary, so a rendered file may hold one)
const DETAILS = '<details id="more"><summary>Method</summary>' + Array.from({ length: 6 }, (_, i) => "<p>Method note " + (i + 1) + " about the measurement, in enough words to fill a line of the block.</p>").join("") + "</details>";
const SRC = "# Report\n\n" + PARA(1) + "\n\n" + PARA(2) + "\n\n" + DETAILS + "\n\n" + Array.from({ length: 38 }, (_, i) => PARA(i + 3)).join("\n\n") + "\n";
const quoteOf = (i: number): string => "Paragraph " + i + " of the report";
const comment = (i: number, n: number): Record<string, unknown> => ({
  id: (T0 + n) + "-" + i, author: "you", ts: T0 + n, body: "Note on paragraph " + i + ".",
  anchor: { quote: quoteOf(i), prefix: "", suffix: " says something about the cache" }, replies: [], resolved: false,
});
// comments in an order by time that is not the order of the text: 30, then 3, then 12
const COMMENTS = [comment(30, 1), comment(3, 2), comment(12, 3)];
const KEYS = { c30: COMMENTS[0].id as string, c3: COMMENTS[1].id as string, c12: COMMENTS[2].id as string };
// one change: a word the session inserted in paragraph 6 (the foot goes to the footer)
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
type Scene = { margin: boolean; cards: Record<string, Box | null>; marks: Record<string, Box | null>; bodyScroll: number; trackScroll: number; order: string[]; active: string };

/** Mount the panel over the rendered document, answer its status asks with `status`, open it, and let the paint and the pass run. */
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
    await reply();
    (unit.querySelector("button") as HTMLButtonElement).click();
    await reply();
    for (const cb of rendered) cb();
    await settle();
    await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
  }, [SRC, status, ABS, SID]);
}
const scene = (page: any, keys: Record<string, string>): Promise<Scene> => page.evaluate((keys: Record<string, string>) => {
  const body = document.getElementById("body")!;
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const track = aside.querySelector(".fc-sec-cards") as HTMLElement;
  const box = (el: Element): Box => { const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height }; };
  const cards: Record<string, Box | null> = {}, marks: Record<string, Box | null> = {};
  for (const [name, key] of Object.entries(keys)) {
    const card = aside.querySelector('.fc-card[data-id="' + key + '"]');
    cards[name] = card ? box(card) : null;
    const act = key.startsWith("chg:") ? "fcchange" : "fcopen", id = key.startsWith("chg:") ? key.slice(4) : key;
    const m = body.querySelector('[data-act="' + act + '"][data-id="' + id + '"]');
    marks[name] = m ? box(m) : null;
  }
  const a = document.activeElement as HTMLElement | null;
  const active = !a || a === document.body ? "BODY" : (a.dataset.act || a.tagName) + (a.dataset.id ? ":" + a.dataset.id : "") + "@" + ((a.closest(".fc-sec-send, .fc-sec-cards, .fc-sec-head") as HTMLElement | null)?.className || "?");
  return {
    margin: aside.classList.contains("fc-margin"), cards, marks, bodyScroll: body.scrollTop, trackScroll: track.scrollTop,
    order: Array.from(aside.querySelectorAll(".fc-cards .fc-card")).map((c) => (c as HTMLElement).dataset.id || ""), active,
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
      if (u.pathname === "/dist/margin-review.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: Reject all keeps the keyboard through its confirm's render and Accept all through a card's toggle — the moved foot gives the focus back; the confirm's buttons are the next Tab stops`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      let s = await scene(page, KEYS);
      assert.equal(s.margin, true, "the margin layout is on");
      await page.focus('.fileview-aside .fc-sec-send [data-act="fcrejectall"]');
      s = await scene(page, KEYS);
      assert.equal(s.active, "fcrejectall@fc-sec-send", "Tab reached Reject all, in the footer");
      await page.keyboard.press("Enter");
      await frames(page);
      s = await scene(page, KEYS);
      const confirm: boolean = await page.evaluate(() => !!document.querySelector('.fileview-aside .fc-sec-send [data-act="fcrejectallgo"]'));
      assert.equal(confirm, true, "the confirm row is up, in the footer");
      assert.equal(s.active, "fcrejectall@fc-sec-send", "the keyboard is on the new Reject all in the footer, not on the body");
      await page.keyboard.press("Tab");
      s = await scene(page, KEYS);
      assert.equal(s.active, "fcrejectallgo@fc-sec-send", "the next Tab stop is the confirm's Reject all");
      // Accept all through an unrelated render: a card head toggled by a click elsewhere
      await page.focus('.fileview-aside .fc-sec-send [data-act="fcacceptall"]');
      await page.evaluate((key: string) => { (document.querySelector('.fc-card[data-id="' + key + '"] .fc-card-head') as HTMLElement).click(); }, KEYS.c3);
      await frames(page);
      s = await scene(page, KEYS);
      assert.equal(s.active, "fcacceptall@fc-sec-send", "Accept all still holds the keyboard after the render moved the foot again");
    });
  });

  test(`in ${name}: a <details> block opened above the marks re-runs the pass (the body's content is observed, not only its box), and the cards stay level; the cards' DOM order is the placement's, so Tabbing down the heads scrolls the text one way`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      const keys = { ...KEYS, chg: "chg:h1" };
      let s = await scene(page, keys);
      for (const k of ["c3", "c12", "c30", "chg"]) { assert.ok(s.marks[k] && s.cards[k], k + " is painted and has a card"); near(s.cards[k]!.top, s.marks[k]!.top, k + "'s card is level before the block opens"); }
      // the block opens: the marks below it move down; the body's box is unchanged, its content's is not
      const grew: number = await page.evaluate(() => { const d = document.getElementById("more") as HTMLDetailsElement; const h0 = d.getBoundingClientRect().height; d.open = true; return d.getBoundingClientRect().height - h0; });
      assert.ok(grew > 100, "the block grew: " + grew);
      await frames(page, 3);
      s = await scene(page, keys);
      for (const k of ["c3", "c12", "c30", "chg"]) near(s.cards[k]!.top, s.marks[k]!.top, k + "'s card followed its mark after the reflow");
      // the order the eye reads: by placement (3, 6, 12, 30), not by time (30, 3, 12)
      assert.deepEqual(s.order, [KEYS.c3, "chg:h1", KEYS.c12, KEYS.c30], "the DOM order is the placement's");
      // Tab down the heads: the text scrolls one way
      const scrolls: number[] = [];
      for (const key of s.order) {
        await page.focus('.fileview-aside .fc-card[data-id="' + key + '"] .fc-card-head');
        await frames(page);
        scrolls.push((await scene(page, keys)).bodyScroll);
      }
      for (let i = 1; i < scrolls.length; i++) assert.ok(scrolls[i] >= scrolls[i - 1], "the text never scrolled back while Tabbing down: " + JSON.stringify(scrolls));
      assert.ok(scrolls[scrolls.length - 1] > scrolls[0], "and it did move down to the far card: " + JSON.stringify(scrolls));
    });
  });

  test(`in ${name}: the list's rows stand in the footer — the '… N more changes' fold is in view while the text is scrolled far down`, async (t) => {
    await inBrowser(t, name, async (page) => {
      // five insertions in five paragraphs: two groups fold behind the row
      const hunks = [2, 8, 14, 20, 26].map((p, n) => { const at = SRC.indexOf("Paragraph " + p + " of the report"); return { id: "h" + (n + 1), author: "api", ts: T0 - 30000 + n, kind: "ins", curFrom: at, curTo: at + 9, baseFrom: at, baseTo: at, oldText: "", newText: "Paragraph", anchor: null }; });
      await mount(page, { ...STATUS, hunks, store: { ...STATUS.store, comments: [] }, unsent: { comments: [], replies: [], accepted: 0, rejected: 0, watermark: null } });
      const where = (): Promise<{ inSend: boolean; inList: boolean; visible: boolean; text: string; cards: string[]; marks: number }> => page.evaluate(() => {
        const aside = document.querySelector(".fileview-aside")!;
        const more = aside.querySelector('[data-act="fcmore"]') as HTMLElement | null;
        const r = more ? more.getBoundingClientRect() : null;
        const a = aside.getBoundingClientRect();
        return {
          inSend: !!more && !!more.closest(".fc-sec-send"), inList: !!more && !!more.closest(".fc-cards"),
          visible: !!r && r.top >= a.top && r.bottom <= a.bottom && r.height > 0, text: more ? more.textContent || "" : "",
          cards: Array.from(aside.querySelectorAll(".fc-card")).map((c) => (c as HTMLElement).dataset.id || ""),
          marks: document.querySelectorAll('#body [data-act="fcchange"]').length,
        };
      });
      let at = await where();
      assert.deepEqual(at.cards, ["chg:h1", "chg:h2", "chg:h3"], "three groups' cards");
      assert.equal(at.marks, 5, "every change's mark is painted");
      assert.equal(at.inSend, true, "the fold row stands in the footer"); assert.equal(at.inList, false);
      assert.equal(at.text, "… 2 more changes");
      // the text scrolled to the fifth change: the row is still in view
      await page.evaluate(() => { (document.querySelector('#body [data-act="fcchange"][data-id="h5"]') as HTMLElement).scrollIntoView({ block: "center" }); });
      await frames(page, 2);
      at = await where();
      assert.equal(at.visible, true, "the row saying why the mark has no card is in view, in the footer");
      await page.evaluate(() => { (document.querySelector('.fileview-aside [data-act="fcmore"]') as HTMLElement).click(); });
      await frames(page, 2);
      at = await where();
      assert.equal(at.cards.length, 5, "the fold opened from the footer: every change has its card");
      assert.equal(at.text, "▾ Fewer changes");
    });
  });
}

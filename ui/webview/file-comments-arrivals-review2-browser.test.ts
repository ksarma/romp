// The arrivals follow-on's second review round (plans/file-review.md, "The arrivals follow-on (2026-09-09)" under Slice 2;
// the review of 2026-09-09, round 2) in a REAL engine: the worktree's file-comments.ts, bundled the way the webview is built,
// mounted over a rendered markdown body under feed.css's own rules, in Chromium and Firefox (the harness is
// file-comments-arrivals-fixes-browser.test.ts's, copied). THE NOTE BOX'S SCROLL: fifteen lines typed into the Send confirm's
// note box scroll it to its end; a status landing rebuilds the confirm and moves the box into it, and a moved textarea
// scrolls back to its first line — render reads the box's scrollTop before the rebuild and writes it back after, so the box
// shows the same lines and the caret's line stays in view, the keyboard still in the box. The stand-ins cannot see this (a
// textarea there keeps its offset when moved), so the restore was pinned by its source text alone; this leg measures it.
// Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only:
// invented prose, placeholder ids, the session name "api".
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
      resolveDir: UI, loader: "ts", sourcefile: "arrivals-review2-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under: the body, the rendered prose, the buttons, and the whole file-comments block. */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-btn"), FEED.slice(a, b)].join("\n");
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --text-muted: #888; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --err: #e55; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --overlay-10: rgba(255,255,255,0.1); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; --box-border: #555; --input-bg: #111; }
${sheet()}
#wrap { width: 1000px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/arrivals-review2.js"></script></body></html>`;

// ── the document and its comments (synthetic prose) ────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
const SRC = "# Report\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const QUOTE = "Paragraph 2 of the report";
const COMMENT = { id: (T0 + 1) + "-6", author: "you", ts: T0 + 1, body: "Say which cache.", anchor: { quote: QUOTE, prefix: "", suffix: " says something" }, replies: [], resolved: false };
const base = {
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: [COMMENT] },
  hunks: [], log: [],
  unsent: { comments: [COMMENT.id], replies: [], accepted: 0, rejected: 0, watermark: null },
};

/** Mount the panel over the rendered document, answer its status asks, open it, and let the paint and the pass run. The
 *  viewer's onSaved hooks are kept (w.__saved) so a test can make the panel re-ask status the way the viewer's save does. */
function mount(page: any): Promise<void> {
  return page.evaluate(async ([src, status, abs, sid]: [string, Record<string, unknown>, string, string]) => {
    const w = window as any;
    const body = document.getElementById("body")!, md = document.getElementById("md")!;
    md.innerHTML = w.__romp.marked.parse(src);
    const posted: any[] = []; w.__posted = posted;
    const rendered: Array<() => void> = []; w.__rendered = rendered;
    const saved: Array<(info: unknown) => void> = []; w.__saved = saved;
    const ctx = {
      path: abs, sid, todoId: null,
      body: () => body, mode: () => "rendered", text: () => src, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null,
      renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
      onRendered: (cb: () => void) => { rendered.push(cb); }, onSelection: () => { /* inert */ }, onSaved: (cb: (info: unknown) => void) => { saved.push(cb); }, onClose: () => { /* inert */ },
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
  }, [SRC, base, ABS, SID]);
}
/** Answer the panel's LAST posted request with `status` (a fileCommentsResult), and let the render and the pass run. */
const answer = (page: any, status: Record<string, unknown>): Promise<void> => page.evaluate(async (status: Record<string, unknown>) => {
  const w = window as any;
  const last = w.__posted[w.__posted.length - 1];
  window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: last.reqId, ...status } }));
  const settle = () => new Promise<void>((r) => setTimeout(r, 0));
  await settle(); await settle();
  await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
}, status);
/** A status landing as the viewer's own save makes one land: the onSaved hooks make the panel re-ask, and `status` answers. */
const land = async (page: any, status: Record<string, unknown>): Promise<void> => {
  await page.evaluate(() => { for (const cb of (window as any).__saved) cb({ mtimeNs: "1757145600000000001", logged: true }); });
  await answer(page, status);
};
const frames = (page: any, n = 2): Promise<void> => page.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
const click = (page: any, sel: string): Promise<void> => page.evaluate((sel: string) => { (document.querySelector(sel) as HTMLElement).click(); }, sel);
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
      if (u.pathname === "/dist/arrivals-review2.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

const BOX = ".fileview-aside .fc-confirm .fc-send-note";
type Box = { scrollTop: number; max: number; value: string; focused: boolean; caret: number; confirmMark: string | null } | null;
const box = (page: any): Promise<Box> => page.evaluate((sel: string) => {
  const b = document.querySelector(sel) as HTMLTextAreaElement | null;
  if (!b) return null;
  const cf = b.closest(".fc-confirm") as HTMLElement;
  return { scrollTop: b.scrollTop, max: b.scrollHeight - b.clientHeight, value: b.value, focused: document.activeElement === b, caret: b.selectionStart, confirmMark: cf.dataset.probe || null };
}, BOX);

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: the note box keeps its scroll offset through a status landing — fifteen lines scrolled to their end, the render moves the box into the rebuilt confirm, and the box shows the same lines after, the keyboard still in it`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      await click(page, '[data-act="fcsend"]'); await frames(page);
      await page.focus(BOX);
      for (let i = 0; i < 15; i++) { await page.keyboard.type("line " + i); if (i < 14) await page.keyboard.press("Enter"); }
      await frames(page);
      const before = (await box(page))!;
      assert.ok(before.max > 0, "the fixture: fifteen lines overflow the box's eight rows: " + before.max);
      assert.ok(before.scrollTop > 0, "and typing at the end scrolled it: " + before.scrollTop);
      assert.equal(before.focused, true);
      await page.evaluate((sel: string) => { (document.querySelector(sel)!.closest(".fc-confirm") as HTMLElement).dataset.probe = "old"; }, BOX);   // the confirm node before the landing
      await land(page, { ...base, storeMtimeNs: "1757145600000000005" });   // a poll's status while the person reads their note
      const after = (await box(page))!;
      assert.equal(after.confirmMark, null, "the fixture: the landing rebuilt the confirm around the box");
      assert.equal(after.value, before.value, "the words stand");
      assert.equal(after.focused, true, "the keyboard is back in the box");
      assert.equal(after.caret, before.caret, "the caret where it was");
      assert.equal(after.scrollTop, before.scrollTop, "the box shows the same lines (without the restore: scrolled back to its first line, " + before.scrollTop + " to 0, the caret's line out of the box)");
    });
  });
}

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const SELF = fs.readFileSync(path.join(UI, "file-comments-arrivals-review2-browser.test.ts"), "utf8").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
  assert.doesNotMatch(SELF, /\bdiffs?\b/i, "the folded part of a change card is the change's old and new text (CONTEXT.md, Change: Avoid)");
  assert.doesNotMatch(SELF, /\bthreads?\b/i, "a comment with replies is a file comment with a run of turns (CONTEXT.md, File comment: Avoid)");
  assert.doesNotMatch(SELF, /fleet/i, "no new identifiers or prose in the old word for the sessions pane");
  assert.doesNotMatch(SELF, /\/home\/[a-z]/, "no absolute home paths");
});

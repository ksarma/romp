// The seen-only accept (plans/file-review.md, decision 41 and "The seen follow-on (2026-09-09)" under Slice 2) in a REAL
// engine: the worktree's file-comments.ts, bundled the way the webview is built, mounted over a rendered markdown body laid
// out under feed.css's own rules, in Chromium and Firefox. One scene: two pending changes the panel's first status held
// (seen) and a third the session adds while the person reads, its card below the track's box (unseen). The Send confirm's
// accept option names the two it accepts and the one it leaves, checked; the send's accept goes by id for the two, never an
// accept-all; the message counts what the reply accepted; the third change's card is still in the list after the send.
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
      resolveDir: UI, loader: "ts", sourcefile: "arrivals-probe.ts",
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
#wrap { width: 1000px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/arrivals.js"></script></body></html>`;

// ── the document and its comments (synthetic prose) ────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
const SRC = "# Report\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const QUOTE = "Paragraph 2 of the report";
const COMMENT = { id: (T0 + 1) + "-6", author: "you", ts: T0 + 1, body: "Say which cache.", anchor: { quote: QUOTE, prefix: "", suffix: " says something" }, replies: [], resolved: false };
const WORD = "Paragraph 25 of the report";
const WORD_AT = SRC.indexOf(WORD);
// the session's answer: a reply on the comment (its card near the top of the track) and a change far down the text (its card
// below the track's box while the text is at its top)
const HUNK2 = { id: "h2", author: "api", ts: T0 + 21000, kind: "ins", curFrom: WORD_AT, curTo: WORD_AT + WORD.length, baseFrom: WORD_AT, baseTo: WORD_AT, oldText: "", newText: WORD, anchor: null };
const base = {
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: [COMMENT] },
  hunks: [], log: [],
  unsent: { comments: [COMMENT.id], replies: [], accepted: 0, rejected: 0, watermark: null },
};

/** Mount the panel over the rendered document, answer its status asks with `status` (the scene's first status), open it, and
 *  let the paint and the pass run. The viewer's onSaved hooks are kept (w.__saved) so a test can make the panel re-ask status
 *  the way the viewer's save does. */
function mount(page: any, status: Record<string, unknown> = base): Promise<void> {
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
  }, [SRC, status, ABS, SID]);
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
type Scene = {
  line: { text: string; color: string; dot: string; inHead: boolean } | null;
  cards: Record<string, { top: number; isNew: boolean; dot: string } | null>;
  marks: Record<string, { isNew: boolean; image: string } | null>;
  bodyScroll: number; trackScroll: number; trackBox: { top: number; bottom: number }; posted: number; lastVerb: string | null;
  composerHidden: boolean;
};
const scene = (page: any, keys: Record<string, string>): Promise<Scene> => page.evaluate((keys: Record<string, string>) => {
  const w = window as any;
  const body = document.getElementById("body")!;
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const track = aside.querySelector(".fc-sec-cards") as HTMLElement;
  const line = aside.querySelector('[data-act="fcarrivals"]') as HTMLElement | null;
  const cards: Record<string, any> = {}, marks: Record<string, any> = {};
  for (const [name, key] of Object.entries(keys)) {
    const card = aside.querySelector('.fc-card[data-id="' + key + '"]') as HTMLElement | null;
    const head = card ? (card.querySelector(".fc-card-head") as HTMLElement) : null;
    cards[name] = card ? { top: card.getBoundingClientRect().top, isNew: card.dataset.new === "1", dot: head ? getComputedStyle(head, "::before").width : "" } : null;
    const act = key.startsWith("chg:") ? "fcchange" : "fcopen", id = key.startsWith("chg:") ? key.slice(4) : key;
    const m = body.querySelector('[data-act="' + act + '"][data-id="' + id + '"]') as HTMLElement | null;
    marks[name] = m ? { isNew: m.dataset.new === "1", image: getComputedStyle(m).backgroundImage } : null;
  }
  const tb = track.getBoundingClientRect();
  const composer = aside.querySelector(".fc-composer") as HTMLElement | null;
  const last = w.__posted[w.__posted.length - 1];
  return {
    line: line ? { text: line.textContent || "", color: getComputedStyle(line).color, dot: getComputedStyle(line, "::before").width, inHead: !!line.closest(".fc-head") } : null,
    cards, marks, bodyScroll: body.scrollTop, trackScroll: track.scrollTop, trackBox: { top: tb.top, bottom: tb.bottom },
    posted: w.__posted.length, lastVerb: last ? last.verb || null : null, composerHidden: composer ? composer.hidden : true,
  };
}, keys);
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
      if (u.pathname === "/dist/arrivals.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}


// ── the scene ────────────────────────────────────────────────────────────────────────────────────
const W3 = "Paragraph 3 of the report", W3_AT = SRC.indexOf(W3);
const W4 = "Paragraph 4 of the report", W4_AT = SRC.indexOf(W4);
const H1 = { id: "h1", author: "api", ts: T0 + 100, kind: "ins", curFrom: W3_AT, curTo: W3_AT + W3.length, baseFrom: W3_AT, baseTo: W3_AT, oldText: "", newText: W3, anchor: null };
const H3 = { id: "h3", author: "api", ts: T0 + 200, kind: "ins", curFrom: W4_AT, curTo: W4_AT + W4.length, baseFrom: W4_AT, baseTo: W4_AT, oldText: "", newText: W4, anchor: null };
const sug = (...ids: string[]) => ids.map((id) => ({ id, authorId: SID }));
/** The first status: two pending changes, seen with it. */
const TWO_SEEN = { ...base, store: { v: 3, path: "docs/report.md", suggestions: sug("h1", "h3"), comments: [COMMENT] }, hunks: [H1, H3] };
/** The session's third change landing: an arrival far down the text. */
const THIRD = { ...TWO_SEEN, store: { v: 3, path: "docs/report.md", suggestions: sug("h1", "h3", "h2"), comments: [COMMENT] }, hunks: [H1, H3, HUNK2], storeMtimeNs: "1757145600000000004" };
/** After the accept of the two: the third still pending, the decisions unsent. */
const AFTER = { ...base, store: { v: 3, path: "docs/report.md", suggestions: sug("h2"), comments: [COMMENT] }, hunks: [HUNK2], storeMtimeNs: "1757145600000000005", unsent: { comments: [COMMENT.id], replies: [], accepted: 2, rejected: 0, watermark: null } };
type Option = { words: string; checked: boolean; disabled: boolean; rows: string[] } | null;
const option = (page: any): Promise<Option> => page.evaluate(() => {
  const cb = document.querySelector('.fileview-aside input[data-opt="accept"]') as HTMLInputElement | null;
  if (!cb) return null;
  return { words: cb.parentElement!.textContent || "", checked: cb.checked, disabled: cb.disabled, rows: Array.from(document.querySelectorAll(".fileview-aside .fc-confirm li")).map((li) => li.textContent || "") };
});
const lastPosted = (page: any): Promise<any> => page.evaluate(() => { const p = (window as any).__posted; return p[p.length - 1]; });
const postedVerbs = (page: any): Promise<string[]> => page.evaluate(() => (window as any).__posted.filter((m: any) => m.type === "fileComments").map((m: any) => m.verb));
const sentOk = (page: any): Promise<void> => page.evaluate(async () => {
  const p = (window as any).__posted, last = p[p.length - 1];
  window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId: last.reqId, queued: false } }));
  await new Promise<void>((r) => setTimeout(r, 0)); await new Promise<void>((r) => setTimeout(r, 0));
});
const cardsShown = (page: any): Promise<string[]> => page.evaluate(() => Array.from(document.querySelectorAll(".fileview-aside .fc-card")).map((c) => (c as HTMLElement).dataset.id || ""));

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: two seen and one unseen — the confirm's option names the two it accepts and the one it leaves, checked; the send accepts the two by id and never all; the message counts the reply's two; the third change's card is still in the list after`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page, TWO_SEEN);
      let s = await scene(page, { c: COMMENT.id, h1: "chg:h1", h3: "chg:h3", h2: "chg:h2" });
      assert.equal(s.line, null, "the first status: no arrival");
      assert.ok(s.cards.h1 && s.cards.h3, "both changes' cards are rendered");
      await land(page, THIRD);
      s = await scene(page, { c: COMMENT.id, h1: "chg:h1", h3: "chg:h3", h2: "chg:h2" });
      assert.ok(s.line && s.line.text === "api made 1 change since you last looked", "the third change is an arrival: " + JSON.stringify(s.line));
      assert.ok(s.cards.h2, "its card is rendered");
      assert.ok(s.cards.h2!.top >= s.trackBox.bottom, "below the track's box (unseen): " + s.cards.h2!.top + " vs " + JSON.stringify(s.trackBox));
      assert.equal(s.cards.h2!.isNew, true);
      assert.equal(s.cards.h1!.isNew, false);
      await click(page, '.fileview-aside [data-act="fcsend"]');
      await frames(page);
      const opt = await option(page);
      assert.ok(opt, "the confirm's accept option is up");
      assert.equal(opt!.words, "accept the 2 pending changes you have seen (1 unseen stays pending)");
      assert.equal(opt!.checked, true, "checked by default");
      assert.equal(opt!.disabled, false);
      assert.ok(opt!.rows.includes("2 accepted, 0 rejected"), "the list counts the two: " + JSON.stringify(opt!.rows));
      await click(page, '.fileview-aside [data-act="fcsendgo"]');
      await frames(page);
      let m = await lastPosted(page);
      assert.equal(m.type, "fileComments");
      assert.equal(m.verb, "accept", "by id (before: accept-all)");
      assert.deepEqual(m.args, { ids: ["h1", "h3"] });
      assert.ok(!(await postedVerbs(page)).includes("accept-all"), "no accept-all");
      await answer(page, { ...AFTER, verb: "accept", accepted: ["h1", "h3"] });
      m = await lastPosted(page);
      assert.equal(m.type, "fileCommentsSend", "then the send");
      assert.equal(m.accepted, 2, "the reply's count");
      assert.equal(m.rejected, 0);
      await sentOk(page);
      await frames(page);
      await answer(page, AFTER);
      const cards = await cardsShown(page);
      assert.ok(cards.includes("chg:h2"), "the unseen change is still pending, its card in the list: " + JSON.stringify(cards));
      assert.ok(!cards.includes("chg:h1") && !cards.includes("chg:h3"), "the two seen ones are gone");
    });
  });
}

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const own = fs.readFileSync(path.join(UI, "file-comments-send-seen-browser.test.ts"), "utf8");
  const prose = own.split("\n").filter((l) => l.trim().startsWith("//") || /^\s*test\(/.test(l)).join("\n");
  assert.doesNotMatch(prose, /\bfleet\b/i);
  assert.doesNotMatch(prose, /\b(suggestion|diff|annotation)\b/i);
  assert.doesNotMatch(own, /\/home\/[a-z]/, "no home path");
});

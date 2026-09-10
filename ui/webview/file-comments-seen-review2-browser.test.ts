// The seen follow-on's second review round (plans/file-review.md, decision 43 and "The seen follow-on (2026-09-09)" under Slice
// 2; the review of 2026-09-09, round 2) in a REAL engine: the worktree's file-comments.ts, bundled the way the webview is built,
// mounted over a rendered markdown body laid out under feed.css's own rules, in Chromium and Firefox, at the 1000x500 viewer the
// send-seen leg uses. Two scenes in the margin layout. One: the Send confirm up, the text scrolled to its end, a whole-file comment
// saved — the line at the panel's foot is inside the Send section's box, stuck to its bottom edge while the section scrolls
// inside itself (before: past the box, and every scroll that would show it was a gesture that ended it). Two: the keyboard's way
// to the line — a Shift alone and the Tab from Send to session leave it standing, Enter on it shows the card, and the keyboard
// lands on the card's head (before: any key ended the line, and the removed node took the keyboard to the body). Skips LOUDLY
// without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only: invented prose,
// placeholder ids, the session name "api".
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

// ── the scenes ───────────────────────────────────────────────────────────────────────────────────
const W3 = "Paragraph 3 of the report", W3_AT = SRC.indexOf(W3);
const W4 = "Paragraph 4 of the report", W4_AT = SRC.indexOf(W4);
const H1 = { id: "h1", author: "api", ts: T0 + 100, kind: "ins", curFrom: W3_AT, curTo: W3_AT + W3.length, baseFrom: W3_AT, baseTo: W3_AT, oldText: "", newText: W3, anchor: null };
const H3 = { id: "h3", author: "api", ts: T0 + 200, kind: "ins", curFrom: W4_AT, curTo: W4_AT + W4.length, baseFrom: W4_AT, baseTo: W4_AT, oldText: "", newText: W4, anchor: null };
const sug = (...ids: string[]) => ids.map((id) => ({ id, authorId: SID }));
/** The first status: two pending changes, seen with it, and the one unsent comment. */
const TWO_SEEN = { ...base, store: { v: 3, path: "docs/report.md", suggestions: sug("h1", "h3"), comments: [COMMENT] }, hunks: [H1, H3] };
const NOTE = "Add the run's date.";
/** The reply to the save of a whole-file comment: the store with the fresh comment (its card loose at the top of the track). */
const withSaved = (from: Record<string, unknown>, id: string, storeMtimeNs: string): Record<string, unknown> => {
  const store = (from as any).store;
  return { ...from, verb: "comment", storeMtimeNs, store: { ...store, comments: [...store.comments, { id, author: "you", ts: T0 + 50000, body: NOTE, replies: [], resolved: false }] } };
};
/** The text scrolled to `top` by the viewer (a write to the scroller, no gesture), and the scroll's frame. */
const scrollTo = async (page: any, top: number): Promise<void> => { await page.evaluate((top: number) => { document.getElementById("body")!.scrollTop = top; }, top); await frames(page, 2); };
const lastPosted = (page: any): Promise<any> => page.evaluate(() => { const p = (window as any).__posted; return p[p.length - 1]; });
/** Comment on this file, the words typed, Save: the panel's `comment` request goes. */
async function saveFileComment(page: any): Promise<void> {
  await click(page, '[data-act="fcfile"]');
  await frames(page);
  await page.focus(".fileview-aside .fc-composer .fc-input");
  await page.keyboard.type(NOTE);
  await click(page, '[data-act="fcsave"]');
  await frames(page);
  const m = await lastPosted(page);
  assert.equal(m.verb, "comment", "the save's request went");
}
type Saved = {
  line: { text: string; position: string; background: string; top: number; bottom: number; inSend: boolean } | null;
  send: { top: number; bottom: number; scrollHeight: number; clientHeight: number; scrollTop: number } | null;
  confirm: boolean; viewport: number; bodyScroll: number; trackBox: { top: number; bottom: number };
  card: { top: number; bottom: number } | null; active: string;
};
const saved = (page: any, cardKey: string | null): Promise<Saved> => page.evaluate((cardKey: string | null) => {
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const line = aside.querySelector('[data-act="fcsavedgo"]') as HTMLElement | null;
  const send = aside.querySelector(".fc-sec-send") as HTMLElement | null;
  const track = aside.querySelector(".fc-sec-cards") as HTMLElement;
  const tb = track.getBoundingClientRect();
  const lr = line ? line.getBoundingClientRect() : null;
  const sr = send ? send.getBoundingClientRect() : null;
  const card = cardKey ? (aside.querySelector('.fc-card[data-id="' + cardKey + '"]') as HTMLElement | null) : null;
  const cr = card ? card.getBoundingClientRect() : null;
  const a = document.activeElement as HTMLElement | null;
  const active = !a || a === document.body ? "body" : (a.dataset.act ? "act:" + a.dataset.act : a.className);
  return {
    line: line && lr ? { text: line.textContent || "", position: getComputedStyle(line).position, background: getComputedStyle(line).backgroundColor, top: lr.top, bottom: lr.bottom, inSend: !!line.closest(".fc-sec-send") } : null,
    send: send && sr ? { top: sr.top, bottom: sr.bottom, scrollHeight: send.scrollHeight, clientHeight: send.clientHeight, scrollTop: send.scrollTop } : null,
    confirm: !!aside.querySelector(".fc-confirm"), viewport: window.innerHeight, bodyScroll: document.getElementById("body")!.scrollTop,
    trackBox: { top: tb.top, bottom: tb.bottom }, card: cr ? { top: cr.top, bottom: cr.bottom } : null, active,
  };
}, cardKey);

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: with the Send confirm up, a whole-file comment saved with the text scrolled down leaves a line the person can see — stuck to the Send section's bottom edge, inside the section's box while the section scrolls inside itself (before: after the confirm, below the box, and every scroll that would show it ended it)`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page, TWO_SEEN);
      await click(page, '.fileview-aside [data-act="fcsend"]');
      await frames(page);
      let s = await saved(page, null);
      assert.equal(s.confirm, true, "the fixture: the confirm is up");
      assert.ok(s.send && s.send.scrollHeight > s.send.clientHeight, "the fixture: the Send section scrolls inside itself with the confirm up: " + JSON.stringify(s.send));
      await scrollTo(page, 100000);
      s = await saved(page, null);
      assert.ok(s.bodyScroll > 400, "the fixture: the text is at its end: " + s.bodyScroll);
      await saveFileComment(page);
      const id = (T0 + 50000) + "-1";
      await answer(page, withSaved(TWO_SEEN, id, "1757145600000000005"));
      s = await saved(page, id);
      assert.equal(s.confirm, true, "the confirm stays up through the save");
      assert.ok(s.card && s.card.bottom <= s.trackBox.top, "the fixture: the loose card is above the track's box: " + JSON.stringify(s.card) + " over " + JSON.stringify(s.trackBox));
      assert.ok(s.line, "the line is in the panel");
      assert.equal(s.line!.text, "Saved · the card is above");
      assert.equal(s.line!.inSend, true, "in the Send section");
      assert.equal(s.line!.position, "sticky");
      assert.equal(s.line!.background, "rgb(30, 30, 30)", "the panel's background, over the rows behind it");
      assert.ok(s.send!.scrollHeight > s.send!.clientHeight && s.send!.scrollTop === 0, "the section still scrolls inside itself, unscrolled: " + JSON.stringify(s.send));
      assert.ok(s.line!.top >= s.send!.top - 0.5 && s.line!.bottom <= s.send!.bottom + 0.5, "the line stands inside the section's box (before: below it): " + JSON.stringify(s.line) + " in " + JSON.stringify(s.send));
      assert.ok(s.line!.bottom <= s.viewport, "and on screen");
    });
  });

  test(`in ${name}: the keyboard reaches the line — a Shift alone and the Tab from Send to session leave it standing (before: each ended it before the focus arrived), Enter on it brings the card into view, and the keyboard lands on that card's head, not on the body`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      await scrollTo(page, 1200);
      let s = await saved(page, null);
      assert.ok(s.bodyScroll > 400, "the fixture: the text is scrolled well down: " + s.bodyScroll);
      await saveFileComment(page);
      const id = (T0 + 50000) + "-1";
      await answer(page, withSaved(base, id, "1757145600000000005"));
      s = await saved(page, id);
      assert.ok(s.line && s.line.text === "Saved · the card is above", "the fixture: the line stands: " + JSON.stringify(s.line));
      assert.ok(s.card && s.card.bottom <= s.trackBox.top, "the fixture: the card is above the box");
      await page.focus('.fileview-aside [data-act="fcsend"]');
      await page.keyboard.down("Shift"); await page.keyboard.up("Shift");
      await frames(page);
      s = await saved(page, id);
      assert.ok(s.line, "a Shift alone leaves the line (before: gone)");
      assert.equal(s.active, "act:fcsend", "the keyboard is still on Send to session");
      await page.keyboard.press("Tab");
      await frames(page);
      s = await saved(page, id);
      assert.ok(s.line, "the Tab leaves the line (before: gone before the focus arrived)");
      assert.equal(s.active, "act:fcsavedgo", "and the keyboard is on it: the next stop after Send to session");
      await page.keyboard.press("Enter");
      await frames(page, 3);
      s = await saved(page, id);
      assert.equal(s.line, null, "Enter pressed the line: it is over");
      assert.ok(s.card && s.card.top >= s.trackBox.top && s.card.bottom <= s.trackBox.bottom, "and the card is in the track's box: " + JSON.stringify(s.card) + " in " + JSON.stringify(s.trackBox));
      assert.equal(s.active, "act:fccard", "the keyboard is on the card's head, which carries the card's act (before: the removed node took it to the body)");
    });
  });
}

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const own = fs.readFileSync(path.join(UI, "file-comments-seen-review2-browser.test.ts"), "utf8");
  const prose = own.split("\n").filter((l) => l.trim().startsWith("//") || /^\s*test\(/.test(l)).join("\n");
  assert.doesNotMatch(prose, /\bfleet\b/i);
  assert.doesNotMatch(prose, /\b(suggestion|diff|annotation)\b/i);
  assert.doesNotMatch(own, /\/home\/[a-z]/, "no home path");
});

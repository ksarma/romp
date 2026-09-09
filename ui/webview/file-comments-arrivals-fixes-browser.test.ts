// The arrivals follow-on's review fixes (plans/file-review.md, "The arrivals follow-on (2026-09-09)" under Slice 2; the
// review of 2026-09-09) in a REAL engine: the worktree's file-comments.ts, bundled the way the webview is built, mounted over
// a rendered markdown body under feed.css's own rules, in Chromium and Firefox (the harness is
// file-comments-arrivals-browser.test.ts's, copied). THE PRESS: a real mouse press on an arrival's card head marks it seen —
// the dot comes off in place — but the line under the header keeps its words and the head keeps its place until the release,
// and the click lands on the card, which opens; with the last arrival's card pressed the line stands through the press and
// goes after (before the fix the row's hold was installed after the gesture listeners, so it never held for the press's own
// pointerdown: the line came off inside the press and the card moved up by the line's height under the pointer). THE NOTE
// BOX: fifteen lines grow it to SEND_NOTE_ROWS rows of its line-height plus its padding and border, then it scrolls; Cancel
// and a send that took the words bring the next confirm's box back at its three rows with no inline height; a height the
// person dragged it to stands through a keystroke. Skips LOUDLY without a playwright browser (CI installs none), as the
// other browser legs do. Synthetic values only: invented prose, placeholder ids, the session name "api".
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
      resolveDir: UI, loader: "ts", sourcefile: "arrivals-fixes-probe.ts",
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
#wrap { width: 1000px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/arrivals-fixes.js"></script></body></html>`;

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
const REPLIED = { ...COMMENT, replies: [{ author: "api", authorId: SID, ts: T0 + 20000, body: "The query cache; the sentence says so now." }] };
const HUNK2 = { id: "h2", author: "api", ts: T0 + 21000, kind: "ins", curFrom: WORD_AT, curTo: WORD_AT + WORD.length, baseFrom: WORD_AT, baseTo: WORD_AT, oldText: "", newText: WORD, anchor: null };
const base = {
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: [COMMENT] },
  hunks: [], log: [],
  unsent: { comments: [COMMENT.id], replies: [], accepted: 0, rejected: 0, watermark: null },
};
const ARRIVED = { ...base, store: { v: 3, path: "docs/report.md", suggestions: [{ id: "h2", authorId: SID }], comments: [REPLIED] }, hunks: [HUNK2], storeMtimeNs: "1757145600000000004" };
const NOTE = "Add a summary at the top.";
const withSaved = (id: string, storeMtimeNs: string): Record<string, unknown> => ({ ...base, verb: "comment", storeMtimeNs, store: { v: 3, path: "docs/report.md", suggestions: [], comments: [COMMENT, { id, author: "you", ts: T0 + 50000, body: NOTE, replies: [], resolved: false }] } });

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
/** A real wheel over the body's middle: the person's scroll. */
async function wheel(page: any, dy: number): Promise<void> {
  const box = await page.evaluate(() => { const r = document.getElementById("body")!.getBoundingClientRect(); return { x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2 }; });
  await page.mouse.move(box.x, box.y);
  await page.mouse.wheel(0, dy);
  await frames(page, 3);
}
const KEYS = { c: COMMENT.id, chg: "chg:h2" };
const ACCENT = "rgb(156, 210, 255)";

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
      if (u.pathname === "/dist/arrivals-fixes.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

// the session's reply alone: one arrival, its card in the track's box
const REPLY_ONLY = { ...base, store: { v: 3, path: "docs/report.md", suggestions: [], comments: [REPLIED] }, storeMtimeNs: "1757145600000000004" };
const HEAD = '.fileview-aside .fc-card[data-id="' + COMMENT.id + '"] .fc-card-head';
type Press = { line: string | null; headTop: number | null; isNew: boolean; open: boolean; accept: string | null; acceptOff: boolean | null };
type Click = { act: string | null; card: string | null; inHead: boolean };
const press = (page: any): Promise<Press> => page.evaluate((sel: string) => {
  const aside = document.querySelector(".fileview-aside")!;
  const line = aside.querySelector('[data-act="fcarrivals"]');
  const head = document.querySelector(sel);
  const card = head ? head.closest(".fc-card") as HTMLElement : null;
  const cb = aside.querySelector('input[data-opt="accept"]') as HTMLInputElement | null;
  return { line: line ? line.textContent : null, headTop: head ? head.getBoundingClientRect().top : null, isNew: !!card && card.dataset.new === "1", open: !!card && card.classList.contains("open"), accept: cb && cb.parentElement ? cb.parentElement.textContent : null, acceptOff: cb ? cb.disabled && !cb.checked : null };
}, HEAD);
/** The release's aftermath: the click (synchronous with the pointerup), then the hold's zero timer, then a frame. */
const settled = (page: any): Promise<void> => page.evaluate(() => new Promise<void>((r) => setTimeout(() => setTimeout(() => requestAnimationFrame(() => r()), 0), 0)));
/** A real press on the card's head, near its lower left corner — the card's own toggle (the passage link further along the
 *  head is a control of its own), and near the lower edge, where a shift of the line's height would move the head out from
 *  under the pointer — read before, during and after; and the clicks the document saw, by what they resolved to. */
async function pressHead(page: any): Promise<{ before: Press; during: Press; after: Press; clicks: Click[] }> {
  await page.evaluate((sel: string) => { const w = window as any; w.__clicks = []; document.addEventListener("click", (e) => { const t = e.target as HTMLElement; const a = t.closest("[data-act]") as HTMLElement | null; const c = t.closest(".fc-card") as HTMLElement | null; w.__clicks.push({ act: a ? a.dataset.act : null, card: c ? c.dataset.id : null, inHead: !!t.closest(sel) }); }, true); }, HEAD);
  const before = await press(page);
  const box = await page.evaluate((sel: string) => { const r = document.querySelector(sel)!.getBoundingClientRect(); return { x: r.left + 8, y: r.bottom - 3 }; }, HEAD);
  await page.mouse.move(box.x, box.y);
  await page.mouse.down();
  await frames(page, 2);
  const during = await press(page);
  await page.mouse.up();
  await settled(page);
  const after = await press(page);
  const clicks: Click[] = await page.evaluate(() => (window as any).__clicks);
  return { before, during, after, clicks };
}
const CARD_CLICK: Click[] = [{ act: "fccard", card: COMMENT.id, inHead: true }];

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: a real press on an arrival's card head marks it seen — the dot off in place — but the line under the header keeps its words and the head its place until the release; the click lands on the card, which opens; released, the words follow`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      await land(page, ARRIVED);
      await click(page, '[data-act="fcsend"]');                   // the confirm up: its accept option counts the arrived change as unseen
      await frames(page);
      const { before, during, after, clicks } = await pressHead(page);
      assert.equal(before.line, "api made 1 change and 1 reply since you last looked");
      assert.equal(before.open, false);
      assert.equal(before.accept, "accept the pending changes you have seen (the 1 pending change is unseen; nothing is accepted until you look)");
      assert.equal(before.acceptOff, true, "nothing seen: the box is unchecked and disabled");
      assert.equal(before.isNew, true);
      assert.equal(during.isNew, false, "seen at the press: the dot came off in place");
      assert.equal(during.line, before.line, "the line keeps its words through the press (before: rewritten at the pointerdown)");
      assert.equal(during.accept, before.accept, "the accept option waits with it");
      assert.equal(during.headTop, before.headTop, "the pressed head has not moved under the pointer");
      assert.deepEqual(clicks, CARD_CLICK, "one click, on the pressed head, resolved to the card's toggle");
      assert.equal(after.open, true, "the click landed on the card: it opened");
      assert.equal(after.line, "api made 1 change since you last looked", "released: the words follow");
      assert.equal(after.accept, "accept the pending changes you have seen (the 1 pending change is unseen; nothing is accepted until you look)", "the change below is still unseen: nothing to accept");
      assert.equal(after.acceptOff, true, "the box stays unchecked and disabled");
    });
  });

  test(`in ${name}: the last arrival's card pressed — the line stands through the press, the head does not move, and the line goes after the release, the card opened by the click`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      await land(page, REPLY_ONLY);
      const { before, during, after, clicks } = await pressHead(page);
      assert.equal(before.line, "api made 1 reply since you last looked");
      assert.equal(before.open, false);
      assert.equal(during.isNew, false, "seen at the press");
      assert.equal(during.line, before.line, "the line stands through the press (before: removed at the pointerdown, the track and its cards moved up by its height)");
      assert.equal(during.headTop, before.headTop, "the pressed head kept its place");
      assert.equal(after.line, null, "released: every arrival seen, the line is gone");
      assert.deepEqual(clicks, CARD_CLICK, "one click, on the pressed head");
      assert.equal(after.open, true, "and the click opened the card");
    });
  });

  test(`in ${name}: the note box grows to SEND_NOTE_ROWS rows then scrolls; after Cancel, and after a send that took the words, the next confirm's box is empty at its three rows with no inline height; a dragged height stands through a keystroke`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      const BOX = ".fileview-aside .fc-confirm .fc-send-note";
      type Box = { height: number; inline: string; rows: number; value: string; lh: number; extra: number; scrolls: boolean } | null;
      const box = (): Promise<Box> => page.evaluate((sel: string) => {
        const b = document.querySelector(sel) as HTMLTextAreaElement | null;
        if (!b) return null;
        const cs = getComputedStyle(b);
        const extra = ["paddingTop", "paddingBottom", "borderTopWidth", "borderBottomWidth"].reduce((n, k) => n + parseFloat((cs as any)[k]), 0);
        return { height: b.getBoundingClientRect().height, inline: b.style.height, rows: b.rows, value: b.value, lh: parseFloat(cs.lineHeight), extra, scrolls: b.scrollHeight > b.clientHeight + 1 };
      }, BOX);
      const near = (a: number, b: number, what: string) => assert.ok(Math.abs(a - b) < 1, what + ": " + a + " vs " + b);
      const lines = async (n: number) => { await page.focus(BOX); for (let i = 0; i < n; i++) { await page.keyboard.type("line " + i); if (i < n - 1) await page.keyboard.press("Enter"); } await frames(page); };
      await click(page, '[data-act="fcsend"]'); await frames(page);
      const fresh = (await box())!;
      assert.equal(fresh.inline, "", "fresh: no inline height");
      assert.equal(fresh.rows, 3);
      const three = fresh.height;
      near(three, 3 * fresh.lh + fresh.extra, "three rows of the line-height plus padding and border");
      await lines(15);
      let b = (await box())!;
      near(b.height, 8 * b.lh + b.extra, "fifteen lines: SEND_NOTE_ROWS rows (before: the composer's twelve)");
      assert.equal(b.scrolls, true, "then the box scrolls");
      const grown = b.height;
      await click(page, '[data-act="fcsendcancel"]'); await frames(page);
      assert.equal(await box(), null, "the confirm closed");
      await click(page, '[data-act="fcsend"]'); await frames(page);
      b = (await box())!;
      assert.equal(b.value, "", "Cancel took the words");
      assert.equal(b.inline, "", "and the inline height (before: kept)");
      near(b.height, three, "the box is back at three rows (before: " + grown + ")");
      // a send that goes: the note travels and the box comes back empty at three rows
      await lines(9);
      b = (await box())!;
      assert.ok(b.height > three + 4 * b.lh, "nine lines grew it: " + b.height);
      await click(page, '[data-act="fcsendgo"]'); await frames(page);
      const sent = await page.evaluate(() => { const last = (window as any).__posted.slice().reverse().find((m: any) => m.type === "fileCommentsSend"); return last ? { reqId: last.reqId, note: last.note } : null; });
      assert.ok(sent, "the send went out");
      assert.match(sent!.note, /^line 0\nline 1\n/, "with the note");
      await page.evaluate(async (reqId: number) => { window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsSent", reqId, queued: false } })); await new Promise((r) => setTimeout(r, 0)); await new Promise((r) => setTimeout(r, 0)); }, sent!.reqId);
      await answer(page, { ...base, storeMtimeNs: "1757145600000000005" });   // the send's refresh
      assert.equal(await box(), null, "the confirm is down after the send");
      await click(page, '[data-act="fcsend"]'); await frames(page);
      b = (await box())!;
      assert.equal(b.value, "", "sent: the words went with the message");
      assert.equal(b.inline, "", "and the inline height with them");
      near(b.height, three, "three rows again");
      // the person drags the box taller (the sheet's resize handle writes an inline height), then types: the drag stands
      await page.evaluate((sel: string) => { (document.querySelector(sel) as HTMLElement).style.height = "300px"; }, BOX);
      await lines(1);
      b = (await box())!;
      assert.equal(b.inline, "300px", "dragged before the first keystroke: the drag stands (before: snapped back to three rows)");
      near(b.height, 300, "as rendered");
      await lines(2);
      b = (await box())!;
      assert.equal(b.inline, "300px", "and through the next keystrokes");
    });
  });
}

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const SELF = fs.readFileSync(path.join(UI, "file-comments-arrivals-fixes-browser.test.ts"), "utf8").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
  assert.doesNotMatch(SELF, /\bdiffs?\b/i, "the folded part of a change card is the change's old and new text (CONTEXT.md, Change: Avoid)");
  assert.doesNotMatch(SELF, /\bthreads?\b/i, "a comment with replies is a file comment with a run of turns (CONTEXT.md, File comment: Avoid)");
  assert.doesNotMatch(SELF, /fleet/i, "no new identifiers or prose in the old word for the sessions pane");
  assert.doesNotMatch(SELF, /\/home\/[a-z]/, "no absolute home paths");
});

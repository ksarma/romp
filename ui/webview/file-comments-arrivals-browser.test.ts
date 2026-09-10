// The arrivals follow-on (plans/file-review.md, "The arrivals follow-on (2026-09-09)" under Slice 2) in a REAL engine: the
// worktree's file-comments.ts, bundled the way the webview is built, mounted over a rendered markdown body laid out under
// feed.css's own rules, in Chromium and Firefox. Two scenes. THE NOTICE: a status landing with a reply and a change of the
// session's shows one line under the header in the accent with a dot before it, and a dot on the arrival cards' heads and
// on their marks in the text; a real wheel over the body marks the arrival whose card is in the track's box seen — its dot
// off, the line's count down — and leaves the one below the box. THE SAVE: a whole-file comment saved while the text is
// scrolled down moves nothing (decision 43; before it, the text was brought to the card, and then not after a wheel), and
// the line at the panel's foot says the card is above, a button in the acknowledgment's green; a real wheel ends the line, and
// its click brings the text to the card. Skips LOUDLY without a playwright browser (CI installs none), as the other browser
// legs do. Synthetic values only: invented prose, placeholder ids, the session name "api".
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
  cards: Record<string, { top: number; bottom: number; isNew: boolean; dot: string } | null>;
  marks: Record<string, { isNew: boolean; image: string } | null>;
  bodyScroll: number; trackScroll: number; trackBox: { top: number; bottom: number }; posted: number; lastVerb: string | null;
  composerHidden: boolean;
  saved: { text: string; tag: string; inSend: boolean; color: string; display: string } | null;   // the line at the foot for a saved card out of view (decision 43)
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
    cards[name] = card ? { top: card.getBoundingClientRect().top, bottom: card.getBoundingClientRect().bottom, isNew: card.dataset.new === "1", dot: head ? getComputedStyle(head, "::before").width : "" } : null;
    const act = key.startsWith("chg:") ? "fcchange" : "fcopen", id = key.startsWith("chg:") ? key.slice(4) : key;
    const m = body.querySelector('[data-act="' + act + '"][data-id="' + id + '"]') as HTMLElement | null;
    marks[name] = m ? { isNew: m.dataset.new === "1", image: getComputedStyle(m).backgroundImage } : null;
  }
  const tb = track.getBoundingClientRect();
  const composer = aside.querySelector(".fc-composer") as HTMLElement | null;
  const last = w.__posted[w.__posted.length - 1];
  const savedEl = aside.querySelector('[data-act="fcsavedgo"]') as HTMLElement | null;
  return {
    line: line ? { text: line.textContent || "", color: getComputedStyle(line).color, dot: getComputedStyle(line, "::before").width, inHead: !!line.closest(".fc-head") } : null,
    cards, marks, bodyScroll: body.scrollTop, trackScroll: track.scrollTop, trackBox: { top: tb.top, bottom: tb.bottom },
    posted: w.__posted.length, lastVerb: last ? last.verb || null : null, composerHidden: composer ? composer.hidden : true,
    saved: savedEl ? { text: savedEl.textContent || "", tag: savedEl.tagName, inSend: !!savedEl.closest(".fc-sec-send"), color: getComputedStyle(savedEl).color, display: getComputedStyle(savedEl).display } : null,
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
const GREEN = "rgb(119, 204, 119)";                              // the page's --green (#7c7), the acknowledgment's colour

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

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: a status landing with the session's reply and change shows the line under the header, in the accent with its dot, and dots on the arrival cards and marks; a real wheel marks the arrival in the track's box seen and leaves the one below it`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      let s = await scene(page, KEYS);
      assert.equal(s.line, null, "the first status: no line");
      assert.equal(s.cards.c!.isNew, false, "no dot on the person's own comment");
      await land(page, ARRIVED);
      s = await scene(page, KEYS);
      assert.ok(s.line, "the line is under the header");
      assert.equal(s.line!.text, "api made 1 change and 1 reply since you last looked");
      assert.equal(s.line!.inHead, true);
      assert.equal(s.line!.color, ACCENT, "in the accent");
      assert.equal(s.line!.dot, "7px", "with a dot before it");
      assert.ok(s.cards.c && s.cards.chg, "both arrival cards are rendered");
      assert.equal(s.cards.c!.isNew, true, "the replied-to comment's card wears the dot");
      assert.equal(s.cards.c!.dot, "6px", "the head's dot has a box");
      assert.equal(s.cards.chg!.isNew, true, "and the change's");
      assert.equal(s.marks.c!.isNew, true, "the highlight too");
      assert.match(s.marks.c!.image, /radial-gradient/, "as a background layer");
      assert.match(s.marks.chg!.image, /radial-gradient/, "and the change's mark");
      // the fixture: the comment's card is in the track's box, the change's card far below it
      assert.ok(s.cards.c!.top >= s.trackBox.top && s.cards.c!.top < s.trackBox.bottom, "the comment's card is in the box: " + s.cards.c!.top + " in " + JSON.stringify(s.trackBox));
      assert.ok(s.cards.chg!.top >= s.trackBox.bottom, "the change's card is below it: " + s.cards.chg!.top);
      await wheel(page, 40);
      s = await scene(page, KEYS);
      assert.ok(s.bodyScroll > 0, "the wheel scrolled the text: " + s.bodyScroll);
      assert.ok(s.line, "the line stays while an arrival stands");
      assert.equal(s.line!.text, "api made 1 change since you last looked", "the reply on the card in the box is seen");
      assert.equal(s.cards.c!.isNew, false, "its dot came off");
      assert.equal(s.cards.c!.dot, "auto", "and the head's pseudo-element with it");
      assert.equal(s.marks.c!.isNew, false);
      assert.doesNotMatch(s.marks.c!.image, /radial-gradient/, "the highlight's layer is gone");
      assert.equal(s.cards.chg!.isNew, true, "the change below the box keeps its dot");
      assert.match(s.marks.chg!.image, /radial-gradient/);
    });
  });

  test(`in ${name}: a whole-file comment saved while the text is scrolled down moves nothing, and the line at the panel's foot says the card is above — a button in the Send section, in the acknowledgment's green; a real wheel ends the line; saved again, the line's click brings the text to the card and the line is over`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      // scrolled down: the loose card at the top of the track is out of view, the 2026-09-07 case
      await wheel(page, 1200);
      let s = await scene(page, KEYS);
      const down = s.bodyScroll;
      assert.ok(down > 400, "the fixture: the text is scrolled well down: " + down);
      await click(page, '[data-act="fcfile"]');
      await frames(page);
      await page.focus(".fileview-aside .fc-composer .fc-input");
      await page.keyboard.type(NOTE);
      await click(page, '[data-act="fcsave"]');
      await frames(page);
      s = await scene(page, KEYS);
      assert.equal(s.lastVerb, "comment", "the save's request went");
      assert.equal(s.saved, null, "no line before the save's status lands");
      const id1 = (T0 + 50000) + "-1";
      await answer(page, withSaved(id1, "1757145600000000005"));
      s = await scene(page, { saved: id1 });
      assert.ok(s.cards.saved, "the saved card is in the list");
      assert.equal(s.bodyScroll, down, "nothing moved: the text stays where it was (before decision 43: brought to the card)");
      assert.equal(s.trackScroll, down, "the track neither");
      assert.ok(s.cards.saved!.bottom <= s.trackBox.top, "the fixture: the loose card is above the track's box: " + JSON.stringify(s.cards.saved) + " over " + JSON.stringify(s.trackBox));
      assert.equal(s.composerHidden, true, "the composer closed");
      assert.ok(s.saved, "the line is in the panel");
      assert.equal(s.saved!.text, "Saved · the card is above");
      assert.equal(s.saved!.tag, "BUTTON", "a button");
      assert.equal(s.saved!.inSend, true, "in the Send section, at the acknowledgment's place");
      assert.equal(s.saved!.color, GREEN, "in the acknowledgment's green");
      assert.equal(s.saved!.display, "block", "a line of its own");
      // the person's next gesture: a real wheel ends the line, in place
      await wheel(page, -60);
      s = await scene(page, { saved: id1 });
      assert.equal(s.saved, null, "the wheel ended the line");
      assert.ok(s.bodyScroll < down && s.bodyScroll > 300, "the wheel moved the text a little, and nothing else did: " + down + " → " + s.bodyScroll);
      const moved = s.bodyScroll;
      // again: the line's click brings the text to the card
      await click(page, '[data-act="fcfile"]');
      await frames(page);
      await page.focus(".fileview-aside .fc-composer .fc-input");
      await page.keyboard.type(NOTE + " Twice.");
      await click(page, '[data-act="fcsave"]');
      await frames(page);
      const id2 = (T0 + 60000) + "-2";
      const twice = withSaved(id2, "1757145600000000006") as any;
      twice.store.comments[twice.store.comments.length - 1].body = NOTE + " Twice.";
      await answer(page, twice);
      s = await scene(page, { saved: id2 });
      assert.ok(s.cards.saved, "the second saved card is in the list");
      assert.equal(s.bodyScroll, moved, "the save scrolled nothing: the text stays where the wheel left it");
      assert.equal(s.saved!.text, "Saved · the card is above");
      await click(page, '[data-act="fcsavedgo"]');
      await frames(page, 3);
      s = await scene(page, { saved: id2 });
      assert.equal(s.saved, null, "the click ended the line");
      assert.ok(s.cards.saved!.top >= s.trackBox.top && s.cards.saved!.bottom <= s.trackBox.bottom, "and brought the card into the track's box: " + JSON.stringify(s.cards.saved) + " in " + JSON.stringify(s.trackBox));
      assert.ok(s.bodyScroll < 400, "the text near its top, where the loose card is: " + s.bodyScroll);
      assert.ok(Math.abs(s.trackScroll - s.bodyScroll) <= 1, "the lock: the body came along with the track");
      assert.equal(s.composerHidden, true, "the composer closed as before");
    });
  });
}

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const SELF = fs.readFileSync(path.join(UI, "file-comments-arrivals-browser.test.ts"), "utf8").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
  assert.doesNotMatch(SELF, /\bdiffs?\b/i, "the folded part of a change card is the change's old and new text (CONTEXT.md, Change: Avoid)");
  assert.doesNotMatch(SELF, /\bthreads?\b/i, "a comment with replies is a file comment with a run of turns (CONTEXT.md, File comment: Avoid)");
  assert.doesNotMatch(SELF, /fleet/i, "no new identifiers or prose in the old word for the sessions pane");
  assert.doesNotMatch(SELF, /\/home\/[a-z]/, "no absolute home paths");
});

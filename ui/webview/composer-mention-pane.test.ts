// The @-mention card's DOM half, run for real (the round-1 review of the mention branch, 2026-09-07). The
// mention block of setupComposer and the transcript's chip functions are sliced from render.ts by their
// markers, bundled with composer-mention.ts the way the webview is built, and driven in headless Chromium
// against a real textarea, so the browser decides what Ctrl+A, PageUp, Home, Ctrl+Z and a synthetic IME
// keystroke do to the caret, the selection and the undo stack. Skips by name without playwright's chromium
// (the pdf-chunk-browser idiom; CI installs none). Source pins hold the wiring the slices cannot carry: the
// one clear helper every clear site calls, the roster hook at the top of renderTabs, the retired keyup
// allowlist. Synthetic names only (web, api, TESTHOST, placeholder ids).
import { test, after } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const PKG = process.cwd();                                   // vscode-extension, where npm test runs
const UI = path.resolve(PKG, "..", "ui", "webview");
const RENDER = fs.readFileSync(path.join(UI, "render.ts"), "utf8");
const CSS = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const req = createRequire(path.join(PKG, "package.json"));   // runtime requires: esbuild must not bundle playwright

let chromium: any = null;
let SKIP: string | false = false;
try {
  chromium = req("playwright").chromium;
  const exe: string = chromium.executablePath();
  if (!exe || !fs.existsSync(exe)) SKIP = "playwright's chromium is not installed here (`npx playwright install chromium` in vscode-extension); the mention card browser test did not run";
} catch {
  SKIP = "playwright is not installed under vscode-extension/node_modules (run `npm ci` there); the mention card browser test did not run";
}

// ── the slices ──────────────────────────────────────────────────────────────────────────────────────────

/** The composer's mention block: from its banner to the prompt history's, inside setupComposer. */
function mentionBlock(): string {
  const a = RENDER.indexOf("  // ── @-mention autocomplete (the user 2026-09-07)");
  const b = RENDER.indexOf("  // ── PROMPT HISTORY");
  assert.ok(a > 0 && b > a, "the mention block sits between the slash menu and the prompt history");
  return RENDER.slice(a, b);
}
/** The transcript side: the roster signature, the chip dress and markMentions, up to setupComposer's banner. */
function chipBlock(): string {
  const a = RENDER.indexOf('let mentionRosterSig = "";');
  const b = RENDER.indexOf("// Composer: Enter sends the message");
  assert.ok(a > 0 && b > a, "the chip functions sit just before setupComposer");
  return RENDER.slice(a, b);
}

/** Both slices, bundled as the webview is built (in memory), each wrapped with the closure it lives in:
 *  the block's free names are the composer's (ta, sessions, tabMeta, activeId, the stubs the card paints
 *  with), the chips' are the module's (sessions, views, CHIP_LABEL). Handed to the page as window.__mention. */
function bundle(): string {
  const esbuild = req("esbuild");
  const contents = `
import { MENTION_MAX_ROWS, mentionQuery, rankMentions, mentionMoreNote, mentionToken, insertMention, mentionKeyAction, mentionSegments } from "./composer-mention";
const CHIP_LABEL: any = { working: "Working", ready: "Ready", idle: "Idle", closed: "Closed", needsInput: "Blocked" };
const el = (tag: string, cls?: string) => { const e = document.createElement(tag); if (cls) e.className = cls; return e; };
const hostNameNodes = (name: string, _id: string) => [document.createTextNode(name)];
const isProvisionalId = (id: string) => id.startsWith("prov:");
(window as any).__mention = {
  mount(ta: HTMLTextAreaElement, env: any) {
    const sessions: Map<string, any> = env.sessions, tabMeta: Map<string, any> = env.tabMeta;
    let activeId: string | null = env.activeId ?? null;
    let composerManualH: number | null = 7;
    let refreshMentionCard: any = null, clearComposerBox: any = null;
    const updateSlash = () => { env.slashUpdates = (env.slashUpdates || 0) + 1; };
${mentionBlock()}
    return { updateMention, mentionKey, pickMention, closeMention, clearBox,
      refresh: () => refreshMentionCard(), clearViaHook: () => clearComposerBox(),
      setActive: (id: string | null) => { activeId = id; },
      state: () => ({ open: !!mPop, items: mItems.map((c) => c.name), sel: mSel, at: mAt, dismissedAt: mDismissedAt, more: mMore, manualH: composerManualH,
                      rows: mPop ? Array.from(mPop.children).map((r) => (r.classList.contains("sel") ? "*" : "") + (r.classList.contains("mention-more") ? "+" : "") + (r.querySelector(".mention-name")?.textContent ?? r.textContent)) : [] }) };
  },
  chips(env: any) {
    const sessions: Map<string, any> = env.sessions, tabMeta: Map<string, any> = env.tabMeta, views: Map<string, any> = env.views;
    let refreshMentionCard: any = env.refreshMentionCard || null;
${chipBlock()}
    return { markMentions, refreshMentionChips, remarkMentions, mentionRosterChanged, dressMentionChip };
  },
};
`;
  const r = esbuild.buildSync({
    stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "mention-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(PKG, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}

// The page: the composer's textarea and a transcript root. The harness wires the composer's keydown order
// (the card's keys first, then an IME's Enter is left alone, then Cmd/Ctrl+Enter stages, then Enter sends; each
// clear goes through clearBox) and the input listener, as render.ts does; the source pins below and in
// composer-mention.test.ts hold that order.
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 200px 20px 20px; } textarea { width: 400px; height: 80px; font: 14px monospace; }
.mention-pop { position: fixed; }
</style></head><body><div id="content"></div><textarea id="composer-input" rows="4"></textarea>
<script src="/dist/mention.js"></script>
<script>
window.__setup = (roster, activeId) => {
  const w = window;
  if (w.__api) w.__api.closeMention();
  document.getElementById("mention-pop")?.remove();
  const old = document.getElementById("composer-input");
  const ta = document.createElement("textarea"); ta.id = "composer-input"; ta.rows = 4; old.replaceWith(ta);
  const env = { sessions: new Map(roster.map((r) => [r.id, { id: r.id, name: r.name, color: r.color || null, emoji: r.emoji, status: { state: r.state || "ready" } }])),
                tabMeta: new Map(), activeId: activeId || null, sent: [], staged: [] };
  const api = w.__mention.mount(ta, env);
  ta.addEventListener("keydown", (e) => {
    if (api.mentionKey(e)) return;
    if (e.key === "Enter" && (e.isComposing || e.keyCode === 229)) return;
    if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !e.shiftKey) { e.preventDefault(); if (ta.value.trim()) { env.staged.push(ta.value); api.clearBox(); } return; }
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (ta.value.trim()) { env.sent.push(ta.value); api.clearBox(); } }
  });
  ta.addEventListener("input", () => api.updateMention());
  w.__api = api; w.__env = env; w.__ta = ta;
  ta.focus();
};
</script></body></html>`;

const SID = (n: number) => "1111111" + n + "-2222-4333-8444-555555555555";
const ROSTER = [
  { id: SID(1), name: "romp", color: { bg: "#3a7bd5", fg: "#ffffff" }, state: "working" },
  { id: SID(2), name: "rompdocs", emoji: "\u{1F4D6}" },
  { id: SID(3), name: "web" },
  { id: "TESTHOST:" + SID(4), name: "TESTHOST:web" },
];

let browserP: Promise<any> | null = null;
const browser = () => (browserP ||= chromium.launch());
after(async () => { if (browserP) await (await browserP).close(); });

/** A fresh page on the harness, its composer mounted over `roster`, writing to `activeId`. */
async function open(roster: unknown[] = ROSTER, activeId: string | null = null) {
  const js = bundle();
  const page = await (await browser()).newPage({ viewport: { width: 800, height: 600 } });
  const errors: string[] = [];
  page.on("pageerror", (e: Error) => errors.push(e.message));
  await page.route("http://romp.test/**", (route: any) => {
    const u = new URL(route.request().url());
    if (u.pathname === "/page") return route.fulfill({ contentType: "text/html", body: PAGE });
    if (u.pathname === "/dist/mention.js") return route.fulfill({ contentType: "application/javascript", body: js });
    return route.fulfill({ status: 404, body: "" });
  });
  await page.goto("http://romp.test/page");
  await page.evaluate(([r, a]: [unknown[], string | null]) => (window as any).__setup(r, a), [roster, activeId]);
  const state = () => page.evaluate(() => (window as any).__api.state());
  const value = () => page.evaluate(() => (window as any).__ta.value as string);
  const env = () => page.evaluate(() => { const e = (window as any).__env; return { sent: e.sent, staged: e.staged, slashUpdates: e.slashUpdates || 0 }; });
  // selectionchange is queued as a task after the selection moves: let it run before reading the card
  const settle = () => page.evaluate(() => new Promise((r) => setTimeout(r, 30)));
  return { page, state, value, env, settle, errors };
}

// ── the card, executed ──────────────────────────────────────────────────────────────────────────────────

test("in Chromium: @ plus letters opens the card, Enter inserts the token through the undo stack, and Ctrl+Z puts the typed query back", { skip: SKIP }, async () => {
  const h = await open();
  await h.page.keyboard.type("ask @ro");
  let s = await h.state();
  assert.equal(s.open, true);
  assert.deepEqual(s.rows, ["*romp", "rompdocs"], "prefix matches, the best highlighted, in the card's rows");
  await h.page.keyboard.press("Enter");
  assert.equal(await h.value(), "ask @romp ", "the pick replaced the typed query with the plain token");
  assert.deepEqual((await h.env()).sent, [], "Enter with the card open picks; it never sends");
  s = await h.state();
  assert.equal(s.open, false);
  await h.page.keyboard.press("Control+z");
  assert.equal(await h.value(), "ask @ro", "the pick sits on the textarea's undo stack (the review's finding: a value assignment dropped it)");
  // (the undo restores the pre-command selection, "@ro" selected: a selection is not a caret, so the card stays closed)
  assert.deepEqual(h.errors, []);
  await h.page.close();
});

test("in Chromium: Ctrl+A with the card open closes it (a selection is not a caret), and Enter then sends the draft as typed, never a duplicate", { skip: SKIP }, async () => {
  const h = await open();
  await h.page.keyboard.type("ask @ro");
  assert.equal((await h.state()).open, true);
  await h.page.keyboard.press("Control+a");
  await h.settle();
  assert.equal((await h.state()).open, false, "selectionchange closed the card");
  await h.page.keyboard.press("Enter");
  assert.deepEqual((await h.env()).sent, ["ask @ro"], "the review's failure was 'ask @romp ask @ro' in the box");
  assert.equal(await h.value(), "");
  // and the pick itself refuses a caret the card has not followed yet (selectionchange is asynchronous, so a
  // pick can land first): the token the caret ends must be the one the card is about
  await h.page.keyboard.type("ask @ro");
  const r = await h.page.evaluate(() => {
    const w = window as any; const ta = w.__ta as HTMLTextAreaElement;
    ta.setSelectionRange(0, 0);
    w.__api.pickMention({ id: "x", name: "romp" });   // the same task: mAt is still the stale token
    return { value: ta.value, open: w.__api.state().open };
  });
  assert.deepEqual(r, { value: "ask @ro", open: false }, "nothing inserted, the card closed");
  assert.deepEqual(h.errors, []);
  await h.page.close();
});

test("in Chromium: PageUp on a two-line draft closes the card, and Enter sends the two lines unchanged", { skip: SKIP }, async () => {
  const h = await open();
  await h.page.keyboard.type("line one that is long enough");
  await h.page.keyboard.press("Shift+Enter");
  await h.page.keyboard.type("ask @ro");
  assert.equal((await h.state()).open, true);
  await h.page.keyboard.press("PageUp");
  await h.settle();
  assert.equal((await h.state()).open, false);
  await h.page.keyboard.press("Enter");
  assert.deepEqual((await h.env()).sent, ["line one that is long enough\nask @ro"]);
  assert.deepEqual(h.errors, []);
  await h.page.close();
});

test("in Chromium: a clear (Cmd/Ctrl+Enter stages, the Send button, any programmatic empty) closes the card; Enter then sends nothing and inserts nothing", { skip: SKIP }, async () => {
  const h = await open();
  await h.page.keyboard.type("ask @ro");
  assert.equal((await h.state()).open, true);
  await h.page.keyboard.press("Control+Enter");
  let s = await h.state();
  assert.equal(s.open, false, "the stage's clear went through clearBox, which the card sees");
  assert.equal(s.manualH, null, "the drag height snapped back with it");
  assert.deepEqual((await h.env()).staged, ["ask @ro"]);
  await h.page.keyboard.press("Enter");
  assert.equal(await h.value(), "", "the review's failure: the box read '@romp ' here");
  assert.deepEqual((await h.env()).sent, []);
  // the module-level hook (cancelComposerEdit's path) is the same helper, and the slash menu is refreshed too
  await h.page.keyboard.type("ask @ro");
  assert.equal((await h.state()).open, true);
  const before = (await h.env()).slashUpdates;
  await h.page.evaluate(() => (window as any).__api.clearViaHook());
  s = await h.state();
  assert.equal(s.open, false);
  assert.equal(await h.value(), "");
  assert.equal((await h.env()).slashUpdates, before + 1);
  assert.deepEqual(h.errors, []);
  await h.page.close();
});

test("in Chromium: an IME composition's keys are not the card's, and the card waits for compositionend to re-read the box", { skip: SKIP }, async () => {
  const h = await open();
  await h.page.keyboard.type("@ro");
  assert.equal((await h.state()).open, true);
  const r = await h.page.evaluate(() => {
    const w = window as any; const ta = w.__ta as HTMLTextAreaElement;
    // the card's handler alone: the harness's own Enter-to-send is not what this test is about
    const fire = (key: string) => { const e = new KeyboardEvent("keydown", { key, isComposing: true, cancelable: true, bubbles: true }); return w.__api.mentionKey(e) || e.defaultPrevented; };
    const enter = fire("Enter"), down = fire("ArrowDown");
    const afterKeys = { ...w.__api.state(), value: ta.value };
    // and through the composer's whole keydown order: the commit Enter, bare or with Ctrl, neither sends nor stages
    // (round 2's find: the card passed it on, and the send branch took it with the half-composed text)
    const commits = [new KeyboardEvent("keydown", { key: "Enter", isComposing: true, cancelable: true, bubbles: true }),
                     new KeyboardEvent("keydown", { key: "Enter", isComposing: true, ctrlKey: true, cancelable: true, bubbles: true })];
    for (const k of commits) ta.dispatchEvent(k);
    const afterCommit = { prevented: commits.some((k) => k.defaultPrevented), value: ta.value, sent: w.__env.sent.slice(), staged: w.__env.staged.slice(), open: w.__api.state().open };
    ta.dispatchEvent(new CompositionEvent("compositionstart", { bubbles: true }));
    ta.value = "@rom"; ta.setSelectionRange(4, 4); ta.dispatchEvent(new Event("input", { bubbles: true }));
    const composing = w.__api.state();
    ta.dispatchEvent(new CompositionEvent("compositionend", { bubbles: true }));
    const ended = w.__api.state();
    return { enter, down, afterKeys, afterCommit, composing, ended };
  });
  assert.equal(r.enter, false, "Enter mid-composition commits the IME's text, not a pick");
  assert.equal(r.down, false, "ArrowDown mid-composition walks the IME's candidates");
  assert.equal(r.afterKeys.open, true); assert.equal(r.afterKeys.sel, 0); assert.equal(r.afterKeys.value, "@ro");
  assert.deepEqual(r.afterCommit, { prevented: false, value: "@ro", sent: [], staged: [], open: true }, "the commit Enter is the IME's: nothing sent, nothing staged, the browser's default kept");
  assert.equal(r.composing.at.query, "ro", "the interim text is the IME's: the card did not re-read it");
  assert.equal(r.ended.at.query, "rom", "compositionend re-reads the box");
  assert.deepEqual(h.errors, []);
  await h.page.close();
});

test("in Chromium: a roster re-rank under the open card keeps the highlight on the SESSION, and a rename reaches the card's rows", { skip: SKIP }, async () => {
  const h = await open();
  await h.page.keyboard.type("@ro");
  await h.page.keyboard.press("ArrowDown");
  assert.deepEqual((await h.state()).rows, ["romp", "*rompdocs"]);
  // a peer renames romp to zromp: the rows re-rank, the highlight stays on rompdocs (the review's failure: it
  // sat on the row index and landed on zromp)
  await h.page.evaluate((sid: string) => { const w = window as any; w.__env.sessions.get(sid).name = "zromp"; w.__api.refresh(); }, SID(1));
  assert.deepEqual((await h.state()).rows, ["*rompdocs", "zromp"]);
  await h.page.keyboard.press("Enter");
  assert.equal(await h.value(), "@rompdocs ");
  // the highlighted session itself renamed: the highlight follows it, and the pick inserts the NEW name
  await h.page.keyboard.press("Control+a"); await h.page.keyboard.press("Backspace");
  await h.page.evaluate((sid: string) => { (window as any).__env.sessions.get(sid).name = "romp"; }, SID(1));
  await h.page.keyboard.type("@ro");
  assert.deepEqual((await h.state()).rows, ["*romp", "rompdocs"]);
  await h.page.evaluate((sid: string) => { const w = window as any; w.__env.sessions.get(sid).name = "zromp"; w.__api.refresh(); }, SID(1));
  assert.deepEqual((await h.state()).rows, ["rompdocs", "*zromp"]);
  await h.page.keyboard.press("Enter");
  assert.equal(await h.value(), "@zromp ", "never the stale name postal would no longer resolve");
  // the highlighted session left the roster: the first row is highlighted
  await h.page.keyboard.press("Control+a"); await h.page.keyboard.press("Backspace");
  await h.page.keyboard.type("@ro");
  await h.page.keyboard.press("ArrowDown");
  assert.deepEqual((await h.state()).rows, ["rompdocs", "*zromp"]);
  await h.page.evaluate((sid: string) => { const w = window as any; w.__env.sessions.delete(sid); w.__api.refresh(); }, SID(1));
  assert.deepEqual((await h.state()).rows, ["*rompdocs"]);
  assert.deepEqual(h.errors, []);
  await h.page.close();
});

test("in Chromium: Escape latches the card closed for that @ until it is deleted; a caret move away and back, or more letters, do not reopen it", { skip: SKIP }, async () => {
  const h = await open();
  await h.page.keyboard.type("ask @we");
  assert.equal((await h.state()).open, true);
  await h.page.keyboard.press("Escape");
  let s = await h.state();
  assert.equal(s.open, false); assert.equal(s.dismissedAt, 4);
  await h.page.keyboard.press("Home"); await h.settle();
  s = await h.state();
  assert.equal(s.dismissedAt, 4, "the caret left the token; the latch holds while its @ does (the review's failure: it cleared here)");
  await h.page.keyboard.press("End"); await h.settle();
  s = await h.state();
  assert.equal(s.open, false, "back at the token's end the card the user dismissed stays dismissed");
  await h.page.keyboard.type("b");
  assert.equal((await h.state()).open, false, "more letters of the same token do not re-pop it");
  // the query backspaced away to the bare "@", then retyped: the same "@", still dismissed (round 2's find: the
  // latch dropped on the bare "@" and the next letter reopened the card)
  for (let i = 0; i < 3; i++) await h.page.keyboard.press("Backspace");   // "ask @"
  assert.equal(await h.value(), "ask @");
  assert.equal((await h.state()).dismissedAt, 4, "the latch holds on the bare @");
  await h.page.keyboard.type("w");
  s = await h.state();
  assert.equal(s.open, false, "the query typed again does not reopen the card");
  assert.equal(s.dismissedAt, 4);
  // an edit BEFORE the "@" moves it, and the latch follows (round 2's find: keyed on the old offset, the latch
  // cleared, and End reopened the card over the same unchanged token)
  await h.page.keyboard.press("Home"); await h.settle();
  await h.page.keyboard.type("so ");
  assert.equal(await h.value(), "so ask @w");
  assert.equal((await h.state()).dismissedAt, 7, "the latch moved with its @");
  await h.page.keyboard.press("End"); await h.settle();
  assert.equal((await h.state()).open, false, "back at the token's end, still dismissed");
  await h.page.keyboard.press("Home"); await h.settle();
  for (let i = 0; i < 3; i++) await h.page.keyboard.press("Delete");   // "ask @w"
  assert.equal(await h.value(), "ask @w");
  assert.equal((await h.state()).dismissedAt, 4, "a deletion before the @ moves it back");
  await h.page.keyboard.press("End"); await h.settle();
  assert.equal((await h.state()).open, false);
  for (let i = 0; i < 2; i++) await h.page.keyboard.press("Backspace");   // "ask "
  assert.equal(await h.value(), "ask ");
  assert.equal((await h.state()).dismissedAt, -1, "the @ is gone: the latch re-arms");
  await h.page.keyboard.type("@we");
  assert.equal((await h.state()).open, true, "a fresh @ opens again");
  assert.deepEqual(h.errors, []);
  await h.page.close();
});

test("in Chromium: past twelve matches the last row counts the rest and takes no pick; the token follows the recipient's kernel", { skip: SKIP }, async () => {
  const many = Array.from({ length: 14 }, (_, i) => ({ id: SID(i + 1) + i, name: "romp-" + String(i + 1).padStart(2, "0") }));
  const h = await open([...many, ROSTER[3]], SID(9));
  await h.page.keyboard.type("@romp");
  let s = await h.state();
  assert.equal(s.items.length, 12);
  assert.equal(s.rows[12], "+2 more, keep typing", "the cap is visible, as the guide says");
  assert.equal(s.rows.length, 13);
  await h.page.keyboard.press("ArrowUp");
  assert.equal((await h.state()).sel, 11, "the arrows wrap over the rows only, never onto the count");
  const picked = await h.page.evaluate(() => {
    const more = document.querySelector(".mention-more") as HTMLElement;
    more.dispatchEvent(new MouseEvent("mousedown", { bubbles: true, cancelable: true }));
    return (window as any).__ta.value;
  });
  assert.equal(picked, "@romp", "a mousedown on the count inserts nothing");
  // writing to a LOCAL session, a remote peer goes in as the display name this kernel knows it by
  await h.page.keyboard.press("Control+a"); await h.page.keyboard.press("Backspace");
  await h.page.keyboard.type("@TESTHOST:w");
  await h.page.keyboard.press("Enter");
  assert.equal(await h.value(), "@TESTHOST:web ");
  // writing to a REMOTE session, every name goes in bare (B's rationale in composer-mention.ts)
  await h.page.evaluate(() => (window as any).__api.setActive("TESTHOST:" + "99999999-2222-4333-8444-555555555555"));
  await h.page.keyboard.press("Control+a"); await h.page.keyboard.press("Backspace");
  await h.page.keyboard.type("@TESTHOST:w");
  await h.page.keyboard.press("Enter");
  assert.equal(await h.value(), "@web ");
  assert.deepEqual(h.errors, []);
  await h.page.close();
});

// ── the transcript's chips, executed ────────────────────────────────────────────────────────────────────

test("in Chromium: chips are exact-name only, keyed by session id, re-dressed on a state, color or name change, and a name that joins the roster later gets its chip without nesting", { skip: SKIP }, async () => {
  const h = await open();
  const r = await h.page.evaluate(([api, webId]: [string, string]) => {
    const w = window as any;
    const sessions = new Map<string, any>([[api, { id: api, name: "api", color: { bg: "#d5643a", fg: "#ffffff" }, status: { state: "working" } }]]);
    const root = document.getElementById("content")!;
    const thread = document.createElement("div"); root.appendChild(thread);
    const views = new Map([["v1", { el: thread }]]);
    let refreshed = 0;
    const chips = w.__mention.chips({ sessions, tabMeta: new Map(), views, refreshMentionCard: () => { refreshed++; } });
    const bubble = document.createElement("div"); bubble.className = "user-bubble md";
    bubble.innerHTML = "<p>ask @web and @api and @API, not <code>@api</code></p>";
    thread.appendChild(bubble);
    chips.markMentions(bubble);
    const snap = () => Array.from(bubble.querySelectorAll(".mention-chip")).map((c) => {
      const e = c as HTMLElement;
      return { text: e.textContent, sid: e.dataset.sid, title: e.title, bg: e.style.getPropertyValue("--chip-bg") };
    });
    const out: any = {};
    out.first = snap(); out.marked = bubble.dataset.mentions;
    chips.mentionRosterChanged();                                   // the roster as it is: the signature is taken
    const taken = refreshed;
    // web's frame lands after the bubble rendered: a NEW name re-marks the bubble
    sessions.set(webId, { id: webId, name: "web", color: null, status: { state: "ready" } });
    chips.mentionRosterChanged();
    out.afterWeb = snap(); out.nested = bubble.querySelectorAll(".mention-chip .mention-chip").length; out.refreshed1 = refreshed - taken;
    out.text = bubble.textContent;
    // api changes state and color: the chip follows without a re-render
    const a = sessions.get(api); a.status = { state: "ready" }; a.color = { bg: "#112233", fg: "#ffffff" };
    chips.mentionRosterChanged();
    out.afterState = snap();
    // a rename: the chip's text stays as typed, its title names the session as it is now
    a.name = "api2"; chips.mentionRosterChanged();
    out.afterRename = snap();
    // an unchanged roster does nothing (no refresh of the card)
    const before = refreshed; chips.mentionRosterChanged(); out.idle = refreshed - before;
    // the session closes; its struck tab keeps it in the map: the chip reads Closed in its color
    a.status = { state: "closed" }; chips.mentionRosterChanged();
    out.afterClosed = snap();
    // a live session takes the name the text carries while the closed one is still in the map: the chip is
    // re-keyed to it now (round 2's find: it waited for the closed tab's dismissal, which says nothing about
    // the mention, and flipped then)
    sessions.set("new-1", { id: "new-1", name: "api", color: { bg: "#445566", fg: "#000000" }, status: { state: "working" } });
    chips.mentionRosterChanged();
    out.afterNamesake = snap(); out.closedStillHeld = sessions.has(api);
    // the closed tab is dismissed: nothing about the mention changed, so nothing moves
    sessions.delete(api); chips.mentionRosterChanged();
    out.afterDismiss = snap();
    // the session is gone from the map: the chip reads Closed and keeps its color
    sessions.delete("new-1"); chips.mentionRosterChanged();
    out.afterGone = snap();
    // a new session takes the name the text carries: the chip is re-keyed to it
    sessions.set("new-2", { id: "new-2", name: "api", color: { bg: "#667788", fg: "#000000" }, status: { state: "ready" } });
    chips.mentionRosterChanged();
    out.afterNew = snap();
    return out;
  }, [SID(2), SID(3)]);
  assert.deepEqual(r.first, [{ text: "@api", sid: SID(2), title: "api · Working", bg: "#d5643a" }],
    "the exact name only: @API is not a name postal takes, @web names nothing yet, the code span is left alone");
  assert.equal(r.marked, "1", "the bubble is marked for a later re-mark");
  assert.deepEqual(r.afterWeb.map((c: any) => c.text), ["@web", "@api"], "web's chip arrived with its frame");
  assert.equal(r.nested, 0, "the existing chip was not wrapped again");
  assert.equal(r.text, "ask @web and @api and @API, not @api", "the text reads as typed");
  assert.equal(r.refreshed1, 1, "the open card was re-ranked for the roster change");
  assert.equal(r.afterState[1].title, "api · Ready"); assert.equal(r.afterState[1].bg, "#112233");
  assert.equal(r.afterRename[1].title, "api2 · Ready"); assert.equal(r.afterRename[1].text, "@api");
  assert.equal(r.idle, 0, "the same roster twice: nothing re-ranked");
  assert.deepEqual(r.afterClosed[1], { text: "@api", sid: SID(2), title: "api2 · Closed", bg: "#112233" }, "closed, no namesake: the chip stays keyed to it");
  assert.equal(r.closedStillHeld, true, "the closed session was still in the map when the namesake arrived");
  assert.deepEqual(r.afterNamesake[1], { text: "@api", sid: "new-1", title: "api · Working", bg: "#445566" }, "re-keyed on the namesake going live, not on the closed tab's dismissal");
  assert.deepEqual(r.afterDismiss, r.afterNamesake, "the dismissal moved nothing");
  assert.equal(r.afterGone[1].title, "api · Closed"); assert.equal(r.afterGone[1].bg, "#445566"); assert.equal(r.afterGone[1].sid, "new-1");
  assert.equal(r.afterNew[1].sid, "new-2"); assert.equal(r.afterNew[1].title, "api · Ready"); assert.equal(r.afterNew[1].bg, "#667788");
  assert.deepEqual(h.errors, []);
  await h.page.close();
});

// ── source pins: the wiring the slices cannot carry ─────────────────────────────────────────────────────

test("every clear of the box goes through clearBox, which refreshes both menus; cancelComposerEdit clears through the module-level hook", () => {
  const stmts = RENDER.match(/^\s*ta\.value = "";/gm) || [];
  assert.equal(stmts.length, 1, "one bare clear statement in the file: clearBox's own");
  assert.match(RENDER, /const clearBox = \(\) => \{\s*\n\s*ta\.value = ""; composerManualH = null; ta\.style\.height = "";\s*\n\s*updateSlash\(\); updateMention\(\);\s*\n\s*\};\s*\n\s*clearComposerBox = clearBox;/);
  const composer = RENDER.slice(RENDER.indexOf("function setupComposer()"), RENDER.indexOf("  // ── PROMPT HISTORY"));
  assert.equal((composer.match(/\bclearBox\(\);/g) || []).length, 6, "the stage, the picker answer, the edit, the provisional queue, the send and /mcp");
  assert.match(RENDER, /function cancelComposerEdit\(sid: string\): void \{\s*\n[^\n]*\n[^\n]*\n\s*clearComposerBox\?\.\(\);/);
  assert.match(RENDER, /let clearComposerBox: \(\(\) => void\) \| null = null;/);
});

test("the pick re-derives the token from the live caret and inserts through execCommand, with the value assignment as the fallback", () => {
  const block = mentionBlock();
  assert.match(block, /const at = caretMention\(\);\s*\n\s*if \(!at \|\| !mAt \|\| at\.start !== mAt\.start \|\| at\.query !== mAt\.query\) \{ closeMention\(\); return; \}/);
  assert.match(block, /ta\.selectionStart === ta\.selectionEnd \? mentionQuery\(ta\.value, ta\.selectionStart\) : null/, "a selection is not a caret");
  assert.match(block, /const token = mentionToken\(c, activeId\);/, "relative to the recipient's kernel");
  assert.match(block, /document\.execCommand\("insertText", false, token\)/);
  assert.match(block, /if \(!done\) \{\s*\n\s*const next = insertMention\(ta\.value, at, caret, token\);\s*\n\s*ta\.value = next\.text;\s*\n\s*ta\.setSelectionRange\(next\.caret, next\.caret\);\s*\n\s*ta\.dispatchEvent\(new Event\("input", \{ bubbles: true \}\)\);/);
});

test("the caret is followed by selectionchange on the text control; the keyup allowlist and the click listener are gone; IME keys pass", () => {
  const block = mentionBlock();
  assert.match(block, /ta\.addEventListener\("selectionchange", updateMention\);/);
  assert.doesNotMatch(block, /addEventListener\("keyup"/);
  assert.doesNotMatch(block, /addEventListener\("click"/);
  assert.match(block, /const mentionKey = \(e: KeyboardEvent\): boolean => \{\s*\n\s*if \(e\.isComposing \|\| e\.keyCode === 229\) return false;/);
  assert.match(block, /if \(mComposing\) return;/);
  assert.match(block, /ta\.addEventListener\("compositionend", \(\) => \{ mComposing = false; updateMention\(\); \}\);/);
});

test("the highlight is kept by session id across a re-rank; the Escape latch keys on the @'s offset, follows it through edits before it and clears only when that @ is gone", () => {
  const block = mentionBlock();
  assert.match(block, /const keep = same \? mItems\[mSel\]\?\.id : undefined;\s*\n\s*const idx = keep \? items\.findIndex\(\(c\) => c\.id === keep\) : -1;\s*\n\s*mSel = idx >= 0 \? idx : 0;/);
  assert.match(block, /if \(mComposing\) return;[^\n]*\n\s*followLatch\(ta\.value, ta\.selectionStart\);[^\n]*\n\s*const at = caretMention\(\);\s*\n\s*if \(!at\) \{ closeMention\(\); return; \}/, "the latch is followed on every read, before the caret is consulted");
  assert.match(block, /const mentionAtOpens = \(text: string, start: number\): boolean =>\s*\n\s*start >= 0 && start < text\.length && text\[start\] === "@" && \(start === 0 \|\| \/\\s\/\.test\(text\[start - 1\]\)\);/, "a bare @ holds the latch: no next-character requirement");
  assert.match(block, /if \(caretEnd >= 0 && prev\.slice\(caretEnd\) === text\.slice\(caret\)\) \{ oldEnd = caretEnd; start = Math\.min\(p, caret, oldEnd\); \}\s*\n\s*if \(oldEnd <= mDismissedAt\) mDismissedAt \+= text\.length - prev\.length;\s*\n\s*else if \(start <= mDismissedAt\) mDismissedAt = -1;\s*\n\s*if \(!mentionAtOpens\(text, mDismissedAt\)\) mDismissedAt = -1;/, "an edit before the @ moves the latch; one over it clears it; the caret places an edit the text alone reads two ways");
  assert.doesNotMatch(block, /mentionTokenAt/, "the next-character test is gone");
  assert.match(block, /if \(mDismissedAt === at\.start\) return;/);
  assert.match(block, /const all = rankMentions\(at\.query, mentionRoster\(\), activeId\);\s*\n\s*const items = all\.slice\(0, MENTION_MAX_ROWS\);/);
  assert.match(block, /mMore = mentionMoreNote\(all\.length\)/);
  assert.match(block, /if \(mMore\) \{ const more = el\("div", "mention-more"\); more\.textContent = mMore; mPop\.appendChild\(more\); \}/, "no data-idx: the card's listener finds no row under it");
});

test("the composer's keydown declines an IME's commit Enter after the card has and before the stage and the send, with the type-from-anywhere handler's guard", () => {
  const start = RENDER.indexOf('  ta.addEventListener("keydown", (e) => {\n    if (slashKey(e)) return;');
  const end = RENDER.indexOf('  ta.addEventListener("input", () => {', start);
  assert.ok(start > 0 && end > start, "the composer's keydown listener, up to its input listener");
  const keys = RENDER.slice(start, end);
  const card = keys.indexOf("if (mentionKey(e)) return;");
  const guard = keys.indexOf('if (e.key === "Enter" && (e.isComposing || e.keyCode === 229)) return;');
  const stage = keys.indexOf('if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && !e.shiftKey) {');
  const send = keys.indexOf('if (e.key === "Enter" && !e.shiftKey && !isCoarsePointer()) {');
  assert.ok(card > 0 && guard > card && stage > guard && send > stage, "the card, then the IME guard, then the stage, then the send");
  assert.equal((keys.match(/sendComposer\(\)/g) || []).length, 1, "one send in the listener, behind the guard");
  assert.match(RENDER, /if \(e\.isComposing \|\| e\.keyCode === 229\) return;   \/\/ IME mid-composition/, "the type-from-anywhere handler's guard, the same test");
});

test("renderTabs opens with the whole-roster hook, ahead of its guards; the hook re-ranks the card, re-dresses the chips and re-marks on a new name", () => {
  assert.match(RENDER, /function renderTabs\(\) \{\n  mentionRosterChanged\(\);/);
  assert.doesNotMatch(RENDER, /tabStripSig = stripSig;\n  refreshMentionCard\?\.\(\);/, "the visible-strip hook is retired");
  const fn = chipBlock();
  assert.match(fn, /for \(const \[id, s\] of sessions\) \{\s*\n\s*rows\.push\(\[id, s\.name, s\.color\?\.bg, s\.color\?\.fg, s\.emoji \?\? tabMeta\.get\(id\)\?\.emoji, s\.status\.state\]\);/);
  assert.match(fn, /if \(sig === mentionRosterSig\) return;\s*\n\s*mentionRosterSig = sig;\s*\n\s*refreshMentionCard\?\.\(\);\s*\n\s*refreshMentionChips\(\);/);
  assert.match(fn, /if \(fresh\) remarkMentions\(\);/);
  assert.match(fn, /closest\("code, pre, a, \.mention-chip"\)/, "a chip already made is never wrapped again");
  assert.match(fn, /root\.dataset\.mentions = "1";/);
  assert.match(fn, /chip\.dataset\.sid = sg\.hit\.id;\s*\n\s*dressMentionChip\(chip, sg\.hit\);/);
  assert.doesNotMatch(fn, /toLowerCase\(\)/, "no case-folded lookup: postal's match is exact");
});

test("the CSS: the count row wears the menu's sub-line dress, no hex", () => {
  assert.match(CSS, /\.mention-more \{ padding: 4px 10px; font-size: 0\.82em; opacity: 0\.6; cursor: default; white-space: nowrap; \}/);
  assert.doesNotMatch(CSS.slice(CSS.indexOf(".mention-pop {"), CSS.indexOf(".mention-chip {")), /#[0-9a-fA-F]{3,6}\b/);
});

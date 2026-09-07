// The user-todos demo capture on the real stack (README.md; the lab boots through todos-lab.sh).
// One recorded browser context with three pages (the chat, the feed, and a second chat view for the
// tab strip); a real session on the lab model files a todo through the postal add_user_todo tool
// (POST /usertodo is the recorded fallback), the loop answers and dismisses from the card, restarts
// the kernel, reads the resumed session's context block, revives the session with a reply, and then
// cuts the GIFs from the recordings by the marks it took. Synthetic content only (the notes-api
// world: sessions api, web and tests). Exits non-zero naming the first missing phase.
import { createRequire } from "node:module";
import { spawn, execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const require2 = createRequire(path.join(ROOT, "vscode-extension", "package.json"));
const { chromium } = require2("playwright");

const PORT = process.env.PORT, TOKEN = process.env.TOKEN, LAB = process.env.LAB_DIR, PROJ = process.env.PROJECT_DIR;
const OUT = process.env.OUT_DIR || "";
const HOOK = process.env.HOOK || path.join(ROOT, "hooks", "romp-usertodo-context.sh");
const KERNEL_BIN = process.env.KERNEL_BIN || path.join(ROOT, "bin", "romp-kernel");
let KPID = Number(process.env.KPID || 0);
const MODEL = process.env.LAB_MODEL || "Haiku";
const FFMPEG = process.env.FFMPEG || "ffmpeg", FFPROBE = process.env.FFPROBE || "ffprobe";   // on PATH, or named in env
const shots = path.join(LAB, "shots"), assets = path.join(LAB, "assets"), video = path.join(LAB, "video");
for (const d of [shots, assets, video]) fs.mkdirSync(d, { recursive: true });

// ── the synthetic notes-api script ──
const T1_TEXT = "Need the auth-scheme decision to wire login; building the unauthenticated routes meanwhile";
const T1_DETAIL = "Two options: OAuth (Google and GitHub) or session cookies. Either unblocks /login. The routes in routes/notes.py work without it.";
const PROMPT = `You work on notes-api. First call the add_user_todo tool with text "${T1_TEXT}" and detail "${T1_DETAIL}". `
  + "Then, without waiting for me, reply with a three-line plan for the unauthenticated routes (list, get, create) and stop. "
  // the tool split is spelled out: one run filed the three routes through add_user_todo as well, and the
  // card read "Waiting on you · 5" where the script expected 2, so every count assertion after it failed
  + "Track the three routes with your own to-do list (TodoWrite), not with add_user_todo, which is only for things you need from me. "
  + "Do not read or change any files.";
const T2_TEXT = "Need a test API key for the notes-api staging server";
const T3_TEXT = "Need your pick between notes and entries as the resource name in the API paths";
const T4_TEXT = "Need the plural form confirmed for the collection route (/notes or /entries)";
const REPLY1 = "Session cookies. Keep OAuth for a later milestone. One line back is enough.";
const REPLY3 = "entries. Also list every note you still have open with me, by id, then withdraw any that this answers or that you no longer need.";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const fails = [];
const record = { filedBy: {}, todos: {}, notes: [], sessions: {} };
let phaseN = 0;
const log = (...a) => console.log(new Date().toISOString().slice(11, 19), ...a);
const check = (name, ok, detail = "") => {
  log(`${ok ? "PASS" : "FAIL"} ${name}${detail ? ": " + detail : ""}`);
  if (!ok) fails.push(name);
  return ok;
};
const note = (s) => { record.notes.push(s); log("NOTE", s); };
const api = async (method, p, body) => {
  const r = await fetch(`http://127.0.0.1:${PORT}${p}`, {
    method, headers: { "X-Romp-Token": TOKEN, "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined });
  const text = await r.text();
  try { return { status: r.status, json: JSON.parse(text) }; } catch { return { status: r.status, json: null, text }; }
};
const sessions = async () => {
  const r = await api("GET", "/sessions");
  const j = r.json;
  return Array.isArray(j) ? j : (j && Array.isArray(j.sessions) ? j.sessions : []);
};
const healthy = async () => { try { const r = await fetch(`http://127.0.0.1:${PORT}/healthz`); return r.ok; } catch { return false; } };
const postTodo = async (sid, text, detail = "") => {
  const r = await api("POST", "/usertodo", { id: sid, text, detail });
  return r.json && r.json.ok ? r.json.todoId : null;
};

// ── the browser: ONE context, recorded at the viewport's own size (the default fits into 800x800) ──
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1280, height: 850 },
                                 recordVideo: { dir: video, size: { width: 1280, height: 850 } } });
const t0 = {}, marks = {}, pages = {};
const newPage = async (key) => {
  const p = await ctx.newPage();
  t0[key] = Date.now(); marks[key] = {}; pages[key] = p;   // the video clock starts per page
  p.on("pageerror", (e) => log("PAGEERR", key, String(e)));
  return p;
};
const mark = (key, name) => { marks[key][name] = Date.now() - t0[key]; log(`MARK ${key}:${name} @${(marks[key][name] / 1000).toFixed(1)}s`); };
const shot = (page, name) => page.screenshot({ path: path.join(shots, `td${String(++phaseN).padStart(2, "0")}-${name}.png`) });
const asset = (name) => path.join(assets, `user-todos-${name}`);

// ── page drivers (the picker and statusline drivers the other loops use) ──
const createSession = async (page, name) => {
  const before = await page.evaluate(() => document.querySelectorAll("#tabs .tab:not(.tab-add)").length);
  await page.click(".tab.tab-add", { timeout: 8000 });
  await page.waitForSelector("#picker-search", { timeout: 8000 });
  await page.fill("#picker-search", name);
  await page.fill("#picker-dir", PROJ);
  await page.click("#picker-new-btn");
  await page.waitForFunction((n) => document.querySelectorAll("#tabs .tab:not(.tab-add)").length > n, before, { timeout: 30000 });
  await page.waitForSelector("#statusline .chip, #statusline .compacting-line", { timeout: 90000 });
  await settleTabTip(page);
};
const pickMeta = (page, kind, want) => page.evaluate(async ([kind, want]) => {
  const btn = document.querySelector(`#statusline .meta-btn[data-kind="${kind}"]`);
  if (!btn) return "no-" + kind + "-badge";
  btn.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  await new Promise((r) => setTimeout(r, 250));
  const item = Array.from(document.querySelectorAll(".meta-menu .meta-item"))
    .find((i) => i.textContent.toLowerCase().includes(want.toLowerCase()));
  if (!item) return "no-menu-item";
  item.dispatchEvent(new MouseEvent("click", { bubbles: true }));
  return "ok";
}, [kind, want]);
// The tab strip's rich hover card (.tab-tip: mode, model, the full project path) is one shared
// element hidden on the hovered tab's mouseleave. A click rebuilds the tab under the pointer, so the
// element that got mouseenter is gone before any mouseleave can fire and the card sticks. Re-enter the
// rebuilt tab, leave it, and park the pointer over the transcript; if the card still shows (a rebuild
// raced the hover again), hide the stale element directly, since it is a pointer artifact and not state.
const settleTabTip = async (page) => {
  const active = page.locator("#tabs .tab.active").first();
  await active.hover({ timeout: 5000 }).catch(() => null);
  await sleep(250);
  await page.mouse.move(700, 600);
  await sleep(250);
  const shown = await page.evaluate(() => { const t = document.querySelector(".tab-tip"); return !!t && t.style.display !== "none" && !!t.offsetParent; });
  if (shown) {
    await page.evaluate(() => { const t = document.querySelector(".tab-tip"); if (t) t.style.display = "none"; });
    note("the tab hover card stuck after a tab rebuild and was hidden directly");
  }
};
const activateTab = async (page, name) => {
  await page.locator("#tabs .tab:not(.tab-add)", { hasText: name }).first().click({ timeout: 8000 });
  await page.waitForFunction((n) => {
    const a = document.querySelector("#tabs .tab.active");
    return !!a && (a.textContent || "").trim().startsWith(n);
  }, name, { timeout: 10000 });
  await page.waitForSelector("#statusline .chip, #statusline .compacting-line", { timeout: 30000 });
  await settleTabTip(page);
};
// how many open asks the split card's "Waiting on you · N" head shows (0 when the section is absent)
const waitUt = (page, n, ms) => page.waitForFunction((n) => {
  const h = document.querySelector(".turn-todo .ut-head");
  if (!h) return n === 0;
  const m = /·\s*(\d+)/.exec(h.textContent || "");
  return !!m && Number(m[1]) === n;
}, n, { timeout: ms });
const utRows = (page) => page.evaluate(() => Array.from(document.querySelectorAll(".turn-todo .ut-item")).map((r) => ({
  tid: r.querySelector(".ut-reply")?.dataset.tid || "",
  text: (r.querySelector(".ut-text")?.textContent || "").replace(/[▸▾]\s*details/g, "").trim() })));
const working = (page) => page.evaluate(() => !!document.querySelector("#statusline .chip-working"));
const assistantCount = (page) => page.evaluate(() => document.querySelectorAll("#content .turn-assistant").length);
const lastAssistantText = (page) => page.evaluate(() => {
  const t = Array.from(document.querySelectorAll("#content .turn-assistant")).pop();
  return t ? (t.textContent || "").trim() : "";
});
const userBubble = (page, needle, ms) => page.waitForFunction((s) => Array.from(document.querySelectorAll("#content .turn-user"))
  .some((e) => (e.textContent || "").includes(s)), needle, { timeout: ms });
// Reply from the card: the modal on the confirm chrome, typed at a human pace, Enter sends
const replyFromCard = async (page, tid, text, delay = 40) => {
  await page.click(`.turn-todo .ut-reply[data-tid="${tid}"]`, { timeout: 8000 });
  await page.waitForSelector("#ut-reply-prompt .ut-reply-input", { timeout: 8000 });
  await page.type("#ut-reply-prompt .ut-reply-input", text, { delay });
  await sleep(400);
  await page.keyboard.press("Enter");
};
// Dismiss is a two-step control: arm, then confirm on the same button (a pointerleave disarms it,
// and a push rebuilds the card, which would drop the arm between two separate pointer clicks). Both
// clicks go to the delegate (actions.ts listens for click on the document) inside ONE evaluate, so
// no rebuild and no pointer movement can come between them; a pause between the two shows the
// armed "Really dismiss?" state on film.
const dismissFromCard = async (page, tid) => {
  for (let i = 0; i < 3; i++) {
    await page.locator(`.turn-todo .ut-dismiss[data-tid="${tid}"]`).scrollIntoViewIfNeeded({ timeout: 5000 }).catch(() => null);
    const armed = await page.evaluate((t) => {
      const b = document.querySelector(`.turn-todo .ut-dismiss[data-tid="${t}"]`);
      if (!b) return "missing";
      b.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
      return b.classList.contains("armed") ? (b.textContent || "") : "not-armed";
    }, tid);
    if (armed === "missing") return false;
    await sleep(700);
    const done = await page.evaluate((t) => {
      const b = document.querySelector(`.turn-todo .ut-dismiss[data-tid="${t}"]`);
      if (!b) return "missing";
      if (!b.classList.contains("armed")) return "disarmed";
      b.dispatchEvent(new MouseEvent("click", { bubbles: true, cancelable: true }));
      return "confirmed";
    }, tid);
    if (done === "confirmed") {
      const gone = await page.waitForFunction((t) => !document.querySelector(`.turn-todo .ut-dismiss[data-tid="${t}"]`), tid, { timeout: 6000 })
        .then(() => true).catch(() => false);
      if (gone) return true;
    }
    log("dismiss attempt", i + 1, armed, done);
    await sleep(800);
  }
  return false;
};

// ─────────────────────────────── 1. the chat, three sessions ───────────────────────────────
const pageChat = await newPage("chat");
await pageChat.goto(`http://127.0.0.1:${PORT}/chat?token=${TOKEN}`);
await pageChat.waitForSelector("#composer-input", { timeout: 20000 });

await createSession(pageChat, "api");
await pageChat.waitForSelector('#statusline .meta-btn[data-kind="model"]', { timeout: 60000 });
log("model pick:", await pickMeta(pageChat, "model", MODEL));
await sleep(500);
log("mode pick:", await pickMeta(pageChat, "mode", "bypass"));   // the tool call must not park on an ask
await sleep(500);
await shot(pageChat, "api-open");
// two quiet siblings, no prompt (no model spend): the tab strip needs tabs without the flag
await createSession(pageChat, "web");
await createSession(pageChat, "tests");
await activateTab(pageChat, "api");
await shot(pageChat, "three-tabs");
const rows0 = await sessions();
const apiRow = rows0.find((r) => r.name === "api");
check("1-api-session-exists", !!apiRow, JSON.stringify(rows0.map((r) => r.name)));
if (!apiRow) { await b.close(); process.exit(1); }
const SID = apiRow.id;
record.sessions.start = rows0.map((r) => ({ name: r.name, state: r.state, backend: r.backend }));

// the feed and the tab-strip view open BEFORE the prompt, so the marker is on film from the first push
const pageFeed = await newPage("feed");
await pageFeed.goto(`http://127.0.0.1:${PORT}/feed?token=${TOKEN}`);
await pageFeed.waitForSelector("#feed-foot", { timeout: 20000, state: "attached" });
const pageTabs = await newPage("tabs");
await pageTabs.goto(`http://127.0.0.1:${PORT}/chat?token=${TOKEN}`);
await pageTabs.waitForSelector("#composer-input", { timeout: 20000 });
await activateTab(pageTabs, "api").catch(() => null);

// ─────────────────────────────── 2. the session files a todo mid-turn ───────────────────────────────
await settleTabTip(pageChat);
await sleep(800);                 // the settle's own hover must be off film before the GIF's lead-in
await pageChat.fill("#composer-input", PROMPT);
mark("chat", "prompt-sent");
await pageChat.keyboard.press("Enter");
let filedByTool = await waitUt(pageChat, 1, 90000).then(() => true).catch(() => false);
let tid1 = "";
if (filedByTool) {
  mark("chat", "filed");
  record.filedBy.first = "tool";
  note("the first todo was filed by the session's own add_user_todo call");
  const w = await working(pageChat);
  check("2-filed-while-working", w, w ? "" : "the turn had already ended when the section appeared");
  await shot(pageChat, "filed-live");
} else {
  record.filedBy.first = "post";
  note("the session did not call add_user_todo within 90 s; the first todo was filed by POST /usertodo (the fallback), so the filed GIF shows no tool-call fold");
  tid1 = await postTodo(SID, T1_TEXT, T1_DETAIL);
  check("2-fallback-post-filed", !!tid1);
  await waitUt(pageChat, 1, 20000).catch(() => null);
  mark("chat", "filed");
}
check("2-section-appeared", (await utRows(pageChat)).length === 1);
const rows1 = await utRows(pageChat);
tid1 = rows1[0]?.tid || tid1;
record.todos.t1 = { id: tid1, text: rows1[0]?.text };

// a second, bare todo by POST (deterministic): one row with the details hint, one without. It waits a
// few seconds so the filed GIF's tail shows the one row the session filed, not this one arriving.
await sleep(4000);
const tid2 = await postTodo(SID, T2_TEXT);
check("3-second-todo-posted", !!tid2);
record.filedBy.second = "post";
record.todos.t2 = { id: tid2, text: T2_TEXT };
await waitUt(pageChat, 2, 20000).then(() => check("3-card-shows-two", true)).catch(() => check("3-card-shows-two", false));
// the card shot waits for the turn to end: the session's own checklist (its to-do list) sits above
// the Waiting-on-you section once it has written one, and the settled card is the guide's picture
await pageChat.waitForFunction(() => !document.querySelector("#statusline .chip-working"), undefined, { timeout: 150000 }).catch(() => null);
await sleep(1500);
mark("chat", "card");
await pageChat.locator(".turn-todo").scrollIntoViewIfNeeded({ timeout: 5000 }).catch(() => null);
await sleep(400);
await pageChat.locator(".turn-todo").screenshot({ path: asset("card.png") });
// the fold: one click opens the detail under the line, the hint flips to ▾
await pageChat.click(".turn-todo .ut-text.ut-has-detail", { timeout: 8000 });
await pageChat.waitForSelector(".turn-todo .ut-detail.open", { timeout: 5000 })
  .then(() => check("4-detail-opens", true)).catch(() => check("4-detail-opens", false));
await sleep(300);
await pageChat.locator(".turn-todo").screenshot({ path: asset("detail-open.png") });
await pageChat.click(".turn-todo .ut-text.ut-has-detail", { timeout: 8000 });
await sleep(300);

// the tab strip on the second chat view: api carries the glyph, web and tests do not
await pageTabs.waitForSelector("#tabs .tab-usertodo", { timeout: 20000 })
  .then(() => check("5-tab-glyph", true)).catch(() => check("5-tab-glyph", false));
mark("tabs", "tab-flag");
{
  // the tab's text runs the name, the glyph and the close mark together (api⚑×), so read the name
  // as its leading word characters only
  const flagged = await pageTabs.evaluate(() => Array.from(document.querySelectorAll("#tabs .tab:not(.tab-add)"))
    .map((t) => ({ name: ((t.textContent || "").trim().match(/^[\w-]+/) || [""])[0], flag: !!t.querySelector(".tab-usertodo") })));
  check("5-only-api-flagged", flagged.every((t) => t.flag === (t.name === "api")), JSON.stringify(flagged));
  const boxes = await pageTabs.evaluate(() => Array.from(document.querySelectorAll("#tabs .tab")).map((t) => {
    const r = t.getBoundingClientRect(); return { x: r.left, y: r.top, w: r.width, h: r.height }; }));
  const x0 = Math.max(0, Math.min(...boxes.map((b) => b.x)) - 8), x1 = Math.max(...boxes.map((b) => b.x + b.w)) + 8;
  const y0 = Math.max(0, Math.min(...boxes.map((b) => b.y)) - 6), y1 = Math.max(...boxes.map((b) => b.y + b.h)) + 6;
  await pageTabs.screenshot({ path: asset("tab.png"), clip: { x: x0, y: y0, width: Math.min(1280 - x0, x1 - x0), height: y1 - y0 } });
}

// ─────────────────────────────── 3. the feed: the quiet marker, then the floor ───────────────────────────────
const markerOk = await pageFeed.waitForFunction(() => Array.from(document.querySelectorAll(".fask-usertodo"))
  .some((e) => e.offsetParent !== null && /waiting on you/.test(e.textContent || "")), undefined, { timeout: 120000 })
  .then(() => true).catch(() => false);
check("6-feed-marker", markerOk, "no visible .fask-usertodo marker on the feed");
mark("feed", "feed-marker");
await sleep(700);
await pageFeed.screenshot({ path: asset("feed.png") });
// the turn ends, the triage judge places the segment, and the idle session's card floors to Needs input
const escalated = await pageFeed.waitForFunction(() => Array.from(document.querySelectorAll(".fask-blocked"))
  .some((e) => e.offsetParent !== null && /waiting on you/.test(e.textContent || "")), undefined, { timeout: 300000 })
  .then(() => true).catch(() => false);
mark("feed", "escalated");
{
  const badges = await pageFeed.evaluate(() => Array.from(document.querySelectorAll(".fask-blocked, .fask-usertodo, .fask-judgeauth"))
    .filter((e) => e.offsetParent !== null).map((e) => e.className + ": " + (e.textContent || "").trim()));
  check("7-feed-escalated", escalated, "no '⚑ waiting on you' blocked badge within the bound; visible badges: " + JSON.stringify(badges));
  const cnt = await pageFeed.evaluate(() => (document.getElementById("col-needsInput-count") || {}).textContent || "");
  note("needs-input column count at escalation: " + JSON.stringify(cnt));
}
await sleep(1200);
await pageFeed.screenshot({ path: asset("feed-escalated.png") });

// the gear: the per-install switch, checked
{
  await pageFeed.evaluate(() => window.postMessage({ romp: "openSettings" }, "*"));
  const ok = await pageFeed.waitForFunction(() => { const c = document.getElementById("rs-usertodos"); return !!c && !!c.offsetParent; }, undefined, { timeout: 15000 })
    .then(() => true).catch(() => false);
  check("8-gear-row", ok);
  if (ok) {
    // the row renders before the /version answer that fills it: wait for the kernel's value
    const checked = await pageFeed.waitForFunction(() => document.getElementById("rs-usertodos").checked === true, undefined, { timeout: 15000 })
      .then(() => true).catch(() => false);
    check("8-gear-switch-checked", checked, "the User todos checkbox never read checked");
    mark("feed", "gear");
    await pageFeed.locator("label.rs-row:has(#rs-usertodos)").screenshot({ path: asset("gear.png") });
    await pageFeed.screenshot({ path: path.join(shots, "gear-full.png") });
  }
  await pageFeed.keyboard.press("Escape");
  await sleep(500);
  const still = await pageFeed.evaluate(() => { const c = document.getElementById("rs-usertodos"); return !!c && !!c.offsetParent; });
  if (still) { await pageFeed.reload(); await pageFeed.waitForSelector("#feed-foot", { timeout: 20000, state: "attached" }); }
}

// ─────────────────────────────── 4. Reply lands as the person's own message ───────────────────────────────
const asstBefore = await assistantCount(pageChat);
await settleTabTip(pageChat);
await sleep(800);
mark("chat", "reply-open");
await pageChat.click(`.turn-todo .ut-reply[data-tid="${tid1}"]`, { timeout: 8000 });
await pageChat.waitForSelector("#ut-reply-prompt .ut-reply-input", { timeout: 8000 })
  .then(() => check("9-reply-modal", true)).catch(() => check("9-reply-modal", false));
{
  const q = await pageChat.evaluate(() => ({
    quote: document.querySelector("#ut-reply-prompt .ut-reply-quote")?.textContent || "",
    detail: document.querySelector("#ut-reply-prompt .ut-detail.open")?.textContent || "" }));
  check("9-modal-quotes-the-ask", q.quote.includes("auth-scheme") && q.detail.includes("OAuth"), JSON.stringify(q));
}
mark("chat", "modal");
await sleep(500);
await pageChat.screenshot({ path: asset("reply-modal.png") });
await pageChat.type("#ut-reply-prompt .ut-reply-input", REPLY1, { delay: 40 });
await sleep(400);
await pageChat.keyboard.press("Enter");
await userBubble(pageChat, "Re: Need the auth-scheme decision", 60000)
  .then(() => check("10-answer-lands-as-user-bubble", true)).catch(() => check("10-answer-lands-as-user-bubble", false));
await waitUt(pageChat, 1, 30000).then(() => check("10-row-leaves-card", true)).catch(() => check("10-row-leaves-card", false));
mark("chat", "answered");
await pageChat.waitForFunction((n) => document.querySelectorAll("#content .turn-assistant").length > n, asstBefore, { timeout: 150000 })
  .then(() => check("10-session-answers", true)).catch(() => check("10-session-answers", false));
await pageChat.waitForFunction(() => !document.querySelector("#statusline .chip-working"), undefined, { timeout: 120000 }).catch(() => null);
mark("chat", "reply-landed");
await shot(pageChat, "reply-landed");

// ─────────────────────────────── 5. Dismiss clears the bare ask ───────────────────────────────
check("11-dismiss-two-step", await dismissFromCard(pageChat, tid2));
await waitUt(pageChat, 0, 20000).then(() => check("11-section-gone", true)).catch(() => check("11-section-gone", false));
await pageChat.waitForFunction(() => !document.querySelector("#tabs .tab-usertodo"), undefined, { timeout: 20000 })
  .then(() => check("11-tab-glyph-gone", true)).catch(() => check("11-tab-glyph-gone", false));
await pageFeed.waitForFunction(() => !Array.from(document.querySelectorAll(".fask-usertodo, .fask-blocked"))
  .some((e) => e.offsetParent !== null && /waiting on you/.test(e.textContent || "")), undefined, { timeout: 30000 })
  .then(() => check("11-feed-marker-gone", true)).catch(() => check("11-feed-marker-gone", false));
mark("chat", "dismissed");
check("11-api-still-listed", (await sessions()).some((r) => r.name === "api"));
await shot(pageChat, "dismissed");

// ─────────────────────────────── 6. memory across a restart ───────────────────────────────
const tid3 = await postTodo(SID, T3_TEXT);
const tid4 = await postTodo(SID, T4_TEXT);
check("12-two-more-posted", !!tid3 && !!tid4);
record.todos.t3 = { id: tid3, text: T3_TEXT }; record.todos.t4 = { id: tid4, text: T4_TEXT };
record.filedBy.third = "post"; record.filedBy.fourth = "post";
await waitUt(pageChat, 2, 20000).catch(() => null);
mark("chat", "restart-begin");
process.kill(KPID, "SIGTERM");
{
  const t = Date.now();
  while ((await healthy()) && Date.now() - t < 20000) await sleep(300);
  await sleep(1500);
  const logfd = fs.openSync(path.join(LAB, "kernel.log"), "a");
  const k2 = spawn(KERNEL_BIN, [], { env: process.env, stdio: ["ignore", logfd, logfd], detached: true });
  k2.unref();
  KPID = k2.pid;
  fs.writeFileSync(path.join(LAB, "kernel.pid"), String(KPID));
  const t1 = Date.now();
  while (!(await healthy()) && Date.now() - t1 < 60000) await sleep(500);
  check("12-kernel-relaunched", await healthy());
}
mark("chat", "restarted");
await sleep(4000);
record.sessions.afterRestart = (await sessions()).map((r) => ({ name: r.name, state: r.state, backend: r.backend }));
note("session states after the restart: " + JSON.stringify(record.sessions.afterRestart));
// the hook, run the way the CLI runs it: the worktree's copy, the sid in env, the token on stdin via curl --config
{
  let out = "";
  try {
    out = execFileSync("bash", [HOOK], {
      env: { ...process.env, ROMP_SID: SID, ROMP_SERVE_PORT: String(PORT), ROMP_KERNEL_PORT: String(PORT), ROMP_SERVE_TOKEN: TOKEN },
      input: JSON.stringify({ source: "resume", session_id: SID }), encoding: "utf8", timeout: 20000 });
  } catch (e) { note("hook run failed: " + String(e)); }
  let block = "";
  try { block = JSON.parse(out).hookSpecificOutput.additionalContext || ""; } catch { /* no output */ }
  check("13-context-block", block.includes("Notes you still have open") && block.includes(tid4), out.slice(0, 200));
  fs.writeFileSync(asset("context-block.txt"), block + (block.endsWith("\n") ? "" : "\n"));
  const direct = await api("POST", "/usertodo/context", { id: SID });
  check("13-route-agrees", !!direct.json && direct.json.enabled === true && (direct.json.block || "").trim() === block.trim());
}
// the chat page reconnects on its own; the card must show the open asks again (two, plus any the
// dismiss phase left standing) with the new kernel's push
const openNow = (await api("POST", "/usertodo/context", { id: SID })).json?.block?.split("\n").filter((l) => l.startsWith("- ")).length || 2;
const back = await waitUt(pageChat, openNow, 60000).then(() => true).catch(() => false);
if (!back) {
  note("the chat page did not resync within 60 s of the restart; reloading it");
  await pageChat.reload(); await pageChat.waitForSelector("#composer-input", { timeout: 20000 });
  await activateTab(pageChat, "api").catch(() => null);
  await waitUt(pageChat, openNow, 30000).then(() => check("14-card-back-after-restart", true)).catch(() => check("14-card-back-after-restart", false));
} else check("14-card-back-after-restart", true);
await sleep(1000);
// Reply from the card revives the dormant session: SessionStart (source=resume) hands it the block
const asstBefore2 = await assistantCount(pageChat);
await settleTabTip(pageChat);
await sleep(800);
mark("chat", "resume-reply");
await replyFromCard(pageChat, tid3, REPLY3, 25);
await userBubble(pageChat, "Re: Need your pick", 120000)
  .then(() => check("15-resume-answer-lands", true)).catch(() => check("15-resume-answer-lands", false));
mark("chat", "resume-answered");
await pageChat.waitForFunction((n) => document.querySelectorAll("#content .turn-assistant").length > n, asstBefore2, { timeout: 240000 })
  .then(() => check("15-revived-session-answers", true)).catch(() => check("15-revived-session-answers", false));
const emptied = await waitUt(pageChat, 0, 150000).then(() => true).catch(() => false);
await pageChat.waitForFunction(() => !document.querySelector("#statusline .chip-working"), undefined, { timeout: 120000 }).catch(() => null);
mark("chat", "resume-done");
{
  const txt = await lastAssistantText(pageChat);
  record.resumeReply = txt.slice(0, 1500);
  // SessionStart evidence, two sources: the revived session's own transcript carries the block the
  // hook injected (the CLI keeps its project transcripts under ~/.claude/projects/<encoded cwd>/),
  // and its reply names an open note by id or says none stands
  let blockInTranscript = 0;
  try {
    const pdir = path.join(process.env.HOME || "", ".claude", "projects", PROJ.replace(/[/.]/g, "-"));
    for (const f of fs.readdirSync(pdir).filter((f) => f.endsWith(".jsonl")))
      blockInTranscript += (fs.readFileSync(path.join(pdir, f), "utf8").match(/Notes you still have open with the person you work for/g) || []).length;
  } catch (e) { note("transcript check skipped: " + String(e)); }
  record.sessionStartBlockInTranscript = blockInTranscript;
  const listed = /ut-[0-9a-f]{8}/.test(txt) || /no (open )?notes|none (still )?stand|nothing (still )?open/i.test(txt);
  check("15-session-start-block-delivered", blockInTranscript > 0, "the revived session's transcript carries no context block");
  check("15-reply-lists-open-notes", listed, "the revived session's reply names no open note");
  check("15-section-emptied", emptied, "the open asks were not all withdrawn within the bound");
  record.sessions.afterRevive = (await sessions()).map((r) => ({ name: r.name, state: r.state, backend: r.backend }));
}
await sleep(800);
await pageChat.screenshot({ path: asset("resumed.png") });

// ─────────────────────────────── 7. finalize: videos, marks, GIF cuts ───────────────────────────────
const vids = Object.fromEntries(Object.entries(pages).map(([k, p]) => [k, p.video()]));
await ctx.close();
await b.close();
const vpath = {};
for (const [k, v] of Object.entries(vids)) { try { vpath[k] = await v.path(); } catch (e) { note(`no video for ${k}: ${e}`); } }
fs.writeFileSync(path.join(LAB, "marks.json"), JSON.stringify({ t0, marks, videos: vpath }, null, 2));

const dur = (f) => {
  try {
    const s = execFileSync(FFPROBE, ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f], { encoding: "utf8" }).trim();
    const n = Number(s); return Number.isFinite(n) ? n : null;
  } catch { return null; }
};
const m = (key, name) => (marks[key][name] ?? NaN) / 1000;
const gif = (name, key, segs, width = 1100, fps = 10) => {
  const input = vpath[key];
  if (!input) { note(`${name}: no recording for ${key}`); return null; }
  const d = dur(input);
  const sorted = segs.filter(([a, b]) => Number.isFinite(a) && Number.isFinite(b))
    .map(([a, b]) => [Math.max(0, a), d ? Math.min(d, b) : b]).filter(([a, b]) => b - a > 0.3)
    .sort((p, q) => p[0] - q[0]);
  // segments that overlap or nearly touch (a fast judge, a quick reply) play as ONE stretch: a
  // replayed second would read as the UI moving twice
  const clean = [];
  for (const s of sorted) {
    const last = clean[clean.length - 1];
    if (last && s[0] <= last[1] + 1.0) last[1] = Math.max(last[1], s[1]); else clean.push([s[0], s[1]]);
  }
  if (!clean.length) { note(`${name}: no usable segments`); return null; }
  const trims = clean.map(([a, b], i) => `[0:v]trim=start=${a.toFixed(2)}:end=${b.toFixed(2)},setpts=PTS-STARTPTS[v${i}]`).join(";");
  const cat = clean.map((_, i) => `[v${i}]`).join("") + `concat=n=${clean.length}:v=1:a=0`;
  const fc = `${trims};${cat},fps=${fps},scale=${width}:-1:flags=lanczos,split[s0][s1];[s0]palettegen=stats_mode=diff[p];[s1][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle`;
  const out = asset(name);
  try {
    execFileSync(FFMPEG, ["-y", "-loglevel", "error", "-i", input, "-filter_complex", fc, "-loop", "0", out], { stdio: ["ignore", "inherit", "inherit"] });
  } catch (e) { note(`${name}: ffmpeg failed: ${e}`); return null; }
  const size = fs.statSync(out).size;
  // about 3 MB at most: step down the ladder 1100/10 -> 1000/8 -> 900/8 -> 900/6 -> 800/6
  const ladder = [[1100, 10], [1000, 8], [900, 8], [900, 6], [800, 6]];
  const at = ladder.findIndex(([w, f]) => w === width && f === fps);
  if (size > 3 * 1024 * 1024 && at >= 0 && at < ladder.length - 1) return gif(name, key, segs, ...ladder[at + 1]);
  const r = { name, key, segs: clean, width, fps, size, seconds: clean.reduce((s, [a, b]) => s + (b - a), 0) };
  log("GIF", JSON.stringify(r));
  return r;
};
const two = (key, aStart, aEnd, bStart, bEnd, maxOne = 14) =>
  (bEnd - aStart <= maxOne) ? [[aStart, bEnd]] : [[aStart, aEnd], [bStart, bEnd]];
record.gifs = {};
record.gifs.filed = gif("filed.gif", "chat", two("chat", m("chat", "prompt-sent") - 0.5, m("chat", "prompt-sent") + 3.5, m("chat", "filed") - 6, m("chat", "filed") + 2.5));
// the reply GIF ends once the answer has landed and the session has started on it (the working chip);
// the session's own reply text is the transcript's business, not the card's, and a fast model has
// already answered within a few seconds
record.gifs.reply = gif("reply.gif", "chat", [[m("chat", "reply-open") - 0.5, m("chat", "answered") + 1.8]]);
record.gifs.escalates = gif("escalates.gif", "feed", [[m("feed", "feed-marker") - 1.5, m("feed", "feed-marker") + 2.5], [m("feed", "escalated") - 3, m("feed", "escalated") + 2.5]]);
record.gifs.resume = gif("resume.gif", "chat", two("chat", m("chat", "resume-reply") - 0.5, m("chat", "resume-answered") + 2.5, m("chat", "resume-done") - 4, m("chat", "resume-done") + 2));
fs.writeFileSync(path.join(LAB, "record.json"), JSON.stringify(record, null, 2));

if (OUT) {
  fs.mkdirSync(OUT, { recursive: true });
  for (const f of fs.readdirSync(assets)) fs.copyFileSync(path.join(assets, f), path.join(OUT, f));
  for (const f of ["marks.json", "record.json", "kernel.log"]) if (fs.existsSync(path.join(LAB, f))) fs.copyFileSync(path.join(LAB, f), path.join(OUT, f));
  for (const [k, v] of Object.entries(vpath)) fs.copyFileSync(v, path.join(OUT, `${k}.webm`));
  log("assets copied to", OUT);
}
if (fails.length) { console.log("DIVERGED at:", fails[0], "| all:", fails.join(", ")); process.exit(1); }
console.log("ALL PHASES GREEN");

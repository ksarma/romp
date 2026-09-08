// The reply's box under a REAL renderer, after the second review of the change (plans/file-review.md, "The composer
// follow-on (2026-09-07)", its closing sentence): headless Chromium and Firefox mount the worktree's panel for the two
// things only a browser can say. (1) Save inside the card of a comment whose id holds a quote: the click puts the
// keyboard on the Save button, the busy render's refocus builds a selector from the card's id, and querySelector throws on
// a raw quote — the review found the reply never posted and Save stuck at "Saving…"; here nothing throws, the reply posts,
// and the second Save is not swallowed. (2) The textarea's scroll offset across the box's MOVE — its comment gone from the
// list, the box to the slot and back — which the stand-in cannot measure: a detached textarea scrolls back to its first
// line, and render puts the offset back. Skips LOUDLY without a playwright browser (CI installs none), as the composer's
// browser leg does. Synthetic fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** The panel's registry entry, bundled as the webview build bundles it (in memory), handed to the page as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\n(window as any).__romp = { fileCommentsAction };\n',
      resolveDir: UI, loader: "ts", sourcefile: "reply-review2-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The whole file-comments block of the sheet, as the feed page loads it (styles.css is pinned byte-equal to it). */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  return FEED.slice(a, b);
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
:root { --box-border: #555; --input-bg: #222; --fg: #ccc; --dim: #999; --accent: #9cd2ff; --accent-wash: rgba(156,210,255,0.14); --card-border: #444; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --warn: #e0a030; }
body { margin: 0; padding: 20px; font: 13px sans-serif; color: var(--fg); background: #1e1e1e; }
.fileview-main { display: flex; height: 600px; }
.fileview-body { flex: 1; }
.fileview-aside { flex: 0 0 340px; overflow: auto; }
${sheet()}</style></head><body><div class="fileview-main"><div class="fileview-body"></div><div class="fileview-aside"></div></div><script src="/dist/probe.js"></script></body></html>`;

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const passage = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." },
  replies: [{ author: "api", authorId: SID, ts: T0 + 1000, body: "The response cache." }, { author: "you", ts: T0 + 2000, body: "Say so in the text." }],
  resolved: false,
};
const whole = { id: T0 + "-119", author: "you", ts: T0 + 4000, body: "Lead with the numbers.", replies: [], resolved: false };
const odd = { id: T0 + '-7"x', author: "you", ts: T0 + 5000, body: "Quote the p99.", replies: [] as Array<Record<string, unknown>>, resolved: false };   // an id a hand wrote
type St = Record<string, unknown>;
function status(comments: Array<Record<string, unknown>>, storeMtimeNs = "1757145600000000002"): St {
  return {
    verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs, configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: [], comments },
    hunks: [], log: [], unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
  };
}

// ── the page side: a viewer context whose posts the test answers ──────────────────────────────────
const SETUP = `window.__setup = () => {
  const posted = []; window.__posted = posted;
  let savedCb = null; window.__saved = (info) => { if (savedCb) savedCb(info); };
  const body = document.querySelector(".fileview-body"), aside = document.querySelector(".fileview-aside");
  const noop = () => {};
  const ctx = {
    path: ${JSON.stringify(ABS)}, sid: ${JSON.stringify(SID)}, todoId: null,
    body: () => body, mode: () => "rendered", text: () => null, mtimeNs: () => "1757145600000000001",
    media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: (cb) => { savedCb = cb; }, onClose: noop,
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: noop, guardClose: noop,
    aside: (el) => { if (el) aside.appendChild(el); else aside.replaceChildren(); },
    setMode: noop, scrollToOffset: noop, reload: noop,
  };
  const unit = window.__romp.fileCommentsAction.mount(ctx);
  body.parentElement.insertBefore(unit, body);
};
window.__reply = (st) => { const m = window.__posted[window.__posted.length - 1]; window.dispatchEvent(new MessageEvent("message", { data: Object.assign({ type: "fileCommentsResult", reqId: m.reqId }, st) })); };
window.__ta = () => document.querySelector("textarea.fc-input");
window.__cardOf = (id) => Array.from(document.querySelectorAll(".fc-card")).find((c) => c.dataset.id === id) || null;
window.__active = () => { const a = document.activeElement; return a === document.body || !a ? { tag: "BODY" } : { tag: a.tagName, act: a.dataset.act || null, id: a.dataset.id || null, cls: a.className }; };
window.__box = () => { const ta = window.__ta(); const card = ta && ta.closest(".fc-card"); return { connected: !!ta && ta.isConnected, focused: document.activeElement === ta, value: ta ? ta.value : null, caret: ta ? ta.selectionStart : null, scrollTop: ta ? ta.scrollTop : null, scrollHeight: ta ? ta.scrollHeight : null, clientHeight: ta ? ta.clientHeight : null, readOnly: ta ? ta.readOnly : null, card: card ? card.dataset.id : null, inSlot: !!ta && ta.closest(".fc-panel") !== null && card === null, hidden: !!ta && ta.closest(".fc-composer").hidden }; };
window.__save = () => { const s = document.querySelector('.fc-composer [data-act="fcsave"]'); return s ? { label: s.textContent, disabled: s.disabled } : null; };
window.__row = () => Array.from(document.querySelectorAll(".fc-composer-ref .fc-note")).map((n) => n.textContent);`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, name: "chromium" | "firefox", body: (page: any, errors: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  let current: St = status([passage, whole, odd]);
  try {
    const js = bundle() + "\n" + SETUP;
    const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const req = route.request(), u = new URL(req.url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (req.method() === "HEAD") {                     // the poll's targets answer the mtimes the last status carried: nothing moves on its own
        const p = u.searchParams.get("path") || "";
        const ns = p.endsWith(".trackchanges/config.json") ? current.configMtimeNs : p.includes(".trackchanges") ? current.storeMtimeNs : current.fileMtimeNs;
        return route.fulfill({ status: 200, headers: { "X-Romp-Mtime-Ns": String(ns) }, body: "" });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp && !!(window as any).__setup);
    (page as any).__reply = async (st: St) => { current = st; await page.evaluate((s: St) => (window as any).__reply(s), st); };
    await body(page, errors);
  } finally { await browser.close(); }
}
const untilPosted = (page: any, n: number, verb: string) => page.waitForFunction(([k, v]: [number, string]) => { const p = (window as any).__posted; return p.length >= k && p[p.length - 1].verb === v; }, [n, verb]);
const postedCount = (page: any): Promise<number> => page.evaluate(() => (window as any).__posted.length);
/** Mount the panel, answer its probe, open it, answer its status: the cards are up. */
async function openPanel(page: any): Promise<void> {
  await page.evaluate(() => (window as any).__setup());
  await untilPosted(page, 1, "status");
  await page.__reply(status([passage, whole, odd]));
  await page.waitForFunction(() => { const u = document.querySelector(".fileview-fc") as HTMLElement | null; return !!u && !u.hidden; });
  await page.click(".fileview-fc button");
  await untilPosted(page, 2, "status");
  await page.__reply(status([passage, whole, odd]));
  await page.waitForSelector(".fc-card");
}
/** Open a card by its id (as data, so an id holding a quote works) and press its Reply: the box takes the keyboard. */
async function replyOn(page: any, id: string): Promise<void> {
  const card = await page.evaluateHandle((k: string) => (window as any).__cardOf(k), id);
  if (!(await card.evaluate((c: HTMLElement) => c.classList.contains("open")))) await (await card.$(".fc-card-head")).click();
  const btn = await page.evaluateHandle((k: string) => Array.from(document.querySelectorAll('[data-act="fcreply"]')).find((b) => (b as HTMLElement).dataset.id === k), id);
  await btn.click();
  await page.waitForFunction(() => { const ta = (window as any).__ta(); return !!ta && document.activeElement === ta; });
}

for (const name of ["chromium", "firefox"] as const) {
  test("in " + name + ": Save inside the card of a comment whose id holds a quote posts the reply — by the mouse and by Tab, Enter — with Save waiting disabled and no script error", async (t) => {
    await inBrowser(t, name, async (page, errors) => {
      await openPanel(page);
      await replyOn(page, odd.id);
      assert.equal((await page.evaluate(() => (window as any).__box())).card, odd.id, "the box stands in the quoted id's card");
      await page.keyboard.type("Yes.");
      // the mouse: the click puts the keyboard on Save, inside the card, and the busy render refocuses by the card's id
      let n = await postedCount(page);
      await page.click('.fc-composer [data-act="fcsave"]');
      await untilPosted(page, n + 1, "reply");
      let last = await page.evaluate(() => { const p = (window as any).__posted; return p[p.length - 1]; });
      assert.deepEqual(last.args, { commentId: odd.id, note: "Yes." });
      const busy = await page.evaluate(() => ({ save: (window as any).__save(), box: (window as any).__box(), active: (window as any).__active() }));
      assert.deepEqual(busy.save, { label: "Saving…", disabled: true }, "Save waits, disabled and relabeled, for the round trip");
      assert.equal(busy.box.readOnly, true, "the box is read-only meanwhile");
      assert.notEqual(busy.active.tag, "BODY", "the keyboard is on a control of the panel, not the body: " + JSON.stringify(busy.active));
      assert.deepEqual(errors, [], "no script error: the selector took the id escaped");
      // the reply lands: the box closes and frees, the turn is on the card
      const answered = { ...odd, replies: [{ author: "you", ts: T0 + 9000, body: "Yes." }] };
      await page.__reply(status([passage, whole, answered], "1757145600000000006"));
      await page.waitForFunction(() => (window as any).__box().hidden);
      const after = await page.evaluate((id: string) => ({ save: (window as any).__save(), box: (window as any).__box(), turns: (window as any).__cardOf(id).querySelectorAll(".fc-reply").length, active: (window as any).__active() }), odd.id);
      assert.equal(after.box.readOnly, false); assert.equal(after.box.value, "");
      assert.equal(after.turns, 1, "the new turn is on the card");
      assert.notEqual(after.active.tag, "BODY", "the keyboard stays in the panel: " + JSON.stringify(after.active));
      // the keyboard: Reply again, Tab from the box to Save, Enter — the same path, the busy gate not stuck from the first
      await replyOn(page, odd.id);
      await page.keyboard.type("And the p95.");
      await page.keyboard.press("Tab");
      assert.deepEqual(await page.evaluate(() => (window as any).__active()), { tag: "BUTTON", act: "fcsave", id: null, cls: "fileview-btn" }, "Tab lands on Save");
      n = await postedCount(page);
      await page.keyboard.press("Enter");
      await untilPosted(page, n + 1, "reply");
      last = await page.evaluate(() => { const p = (window as any).__posted; return p[p.length - 1]; });
      assert.deepEqual(last.args, { commentId: odd.id, note: "And the p95." });
      assert.deepEqual(await page.evaluate(() => (window as any).__save()), { label: "Saving…", disabled: true });
      await page.__reply(status([passage, whole, { ...answered, replies: [...answered.replies, { author: "you", ts: T0 + 9500, body: "And the p95." }] }], "1757145600000000007"));
      await page.waitForFunction(() => (window as any).__box().hidden);
      assert.deepEqual(errors, [], "no script error in the page");
    });
  });

  test("in " + name + ": the textarea's scroll offset survives the box's move to the slot (its comment gone from the list) and back into the card", async (t) => {
    await inBrowser(t, name, async (page, errors) => {
      await openPanel(page);
      await replyOn(page, passage.id);
      await page.keyboard.type(Array.from({ length: 16 }, (_, i) => "line " + (i + 1)).join("\n"));
      const before = await page.evaluate(() => (window as any).__box());
      assert.equal(before.card, passage.id);
      assert.ok(before.scrollHeight > before.clientHeight, "the box scrolls: " + before.scrollHeight + " over " + before.clientHeight);
      assert.ok(before.scrollTop > 0, "…and is scrolled to the caret: " + before.scrollTop);
      // the poll: the passage comment is gone from the sidecar, so the list shows no card for it and the box moves to the slot
      await page.evaluate(() => (window as any).__saved({ mtimeNs: "9", logged: true }));
      await untilPosted(page, 3, "status");
      await page.__reply(status([whole, odd], "1757145600000000004"));
      await page.waitForFunction((id: string) => !(window as any).__cardOf(id), passage.id);
      await page.waitForTimeout(50);                    // the refresh's last render (its finally) follows the status's
      const away = await page.evaluate(() => ({ box: (window as any).__box(), row: (window as any).__row() }));
      assert.equal(away.box.connected, true); assert.equal(away.box.card, null); assert.equal(away.box.inSlot, true, "the box stands in the slot");
      assert.equal(away.box.focused, true, "the keyboard was put back");
      assert.equal(away.box.value, before.value, "the words"); assert.equal(away.box.caret, before.caret, "the caret");
      assert.equal(away.box.scrollTop, before.scrollTop, "the scroll offset: a moved textarea scrolls back to its first line, and render puts the offset back");
      assert.deepEqual(away.row, ["Reply on shipping the cache in v1.2", "The comment is gone from the file's comments."], "the row says why");
      // the comment is back (the sidecar was restored): the box returns to the card with the offset
      await page.evaluate(() => (window as any).__saved({ mtimeNs: "10", logged: true }));
      await untilPosted(page, 4, "status");
      await page.__reply(status([passage, whole, odd], "1757145600000000005"));
      await page.waitForFunction((id: string) => { const c = (window as any).__cardOf(id); return !!c && !!c.querySelector(".fc-composer"); }, passage.id);
      await page.waitForTimeout(50);
      const back = await page.evaluate(() => (window as any).__box());
      assert.equal(back.card, passage.id, "the box returned to the card");
      assert.equal(back.focused, true); assert.equal(back.value, before.value);
      assert.equal(back.scrollTop, before.scrollTop, "the offset survived the return too");
      assert.deepEqual(errors, [], "no script error in the page");
    });
  });
}

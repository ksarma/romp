// The reply's box under a REAL renderer (plans/file-review.md, "The composer follow-on (2026-09-07)", its closing sentence;
// the review of that change): headless Chromium and Firefox mount the worktree's panel, open a reply in a card, type past
// the twelve-row cap, and then take the poll's re-render (a status with a new comment, through the onSaved path). The
// stand-in leg (file-comments-reply-keep.test.ts) can say the node was never detached; only a browser can say what a
// detach would have cost — the undo history, the scroll offset, a blur — and that none of it was: the textarea's undo
// still works, it is still scrolled to the caret, no blur or focusout fired, and the keyboard never left it. A second
// leg opens a reply on a comment whose id holds a quote: the panel's selectors take the id escaped, so nothing throws.
// Skips LOUDLY without a playwright browser (CI installs none), as the composer's browser leg does. Synthetic fixtures
// only: the notes-api world, placeholder ids.
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
      resolveDir: UI, loader: "ts", sourcefile: "reply-keep-probe.ts",
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
// the tokens the block reads, resolved to plain values here (a file:// harness loads no theme), the viewer's row with
// its body and a scrolling aside of the dashboard's width
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
const odd = { id: T0 + '-7"x', author: "you", ts: T0 + 5000, body: "Quote the p99.", replies: [], resolved: false };   // an id a hand wrote
const third = { id: T0 + "-120", author: "you", ts: T0 + 8000, body: "Cite the p99 too.", replies: [], resolved: false };
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

// ── the page side: a viewer context whose posts the test answers, as the stand-in harness does ─────────────────────
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
window.__last = () => { const m = window.__posted[window.__posted.length - 1]; return m ? { reqId: m.reqId, verb: m.verb } : null; };
window.__reply = (st) => { const m = window.__posted[window.__posted.length - 1]; window.dispatchEvent(new MessageEvent("message", { data: Object.assign({ type: "fileCommentsResult", reqId: m.reqId }, st) })); };
window.__ta = () => document.querySelector("textarea.fc-input");
window.__cardOf = (id) => Array.from(document.querySelectorAll(".fc-card")).find((c) => c.dataset.id === id) || null;
window.__watch = () => { const ta = window.__ta(); const n = { blur: 0, focusout: 0 }; window.__events = n; ta.addEventListener("blur", () => { n.blur++; }); ta.addEventListener("focusout", () => { n.focusout++; }); };
window.__box = () => { const ta = window.__ta(); const card = ta && ta.closest(".fc-card"); return { connected: !!ta && ta.isConnected, focused: document.activeElement === ta, value: ta ? ta.value : null, caret: ta ? ta.selectionStart : null, scrollTop: ta ? ta.scrollTop : null, scrollHeight: ta ? ta.scrollHeight : null, clientHeight: ta ? ta.clientHeight : null, card: card ? card.dataset.id : null, same: card === window.__card, events: window.__events || null }; };`;

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

for (const name of ["chromium", "firefox"] as const) {
  test("in " + name + ": the poll's re-render leaves the reply's textarea in place — no blur, the keyboard, the scroll offset and the undo history all kept — and a comment id holding a quote is escaped in the panel's selectors", async (t) => {
    await inBrowser(t, name, async (page, errors) => {
      await openPanel(page);
      // Reply on the passage card: the box opens in it and takes the keyboard
      await page.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');
      await page.click('[data-act="fcreply"][data-id="' + passage.id + '"]');
      await page.waitForFunction(() => { const ta = (window as any).__ta(); return !!ta && document.activeElement === ta; });
      let box = await page.evaluate(() => (window as any).__box());
      assert.equal(box.card, passage.id, "the box stands in the card");
      // past the twelve-row cap: the sheet caps the height and the box scrolls to the caret
      await page.keyboard.type(Array.from({ length: 16 }, (_, i) => "line " + (i + 1)).join("\n"));
      await page.evaluate(() => { (window as any).__card = (window as any).__cardOf((window as any).__ta().closest(".fc-card").dataset.id); (window as any).__watch(); });
      const before = await page.evaluate(() => (window as any).__box());
      assert.ok(before.scrollHeight > before.clientHeight, "the box scrolls: " + before.scrollHeight + " over " + before.clientHeight);
      assert.ok(before.scrollTop > 0, "…and is scrolled to the caret: " + before.scrollTop);
      assert.equal(before.value.split("\n").length, 16);
      // the poll's path: a save elsewhere re-asks status, and the reply carries a new comment — every section is rebuilt
      await page.evaluate(() => (window as any).__saved({ mtimeNs: "9", logged: true }));
      await untilPosted(page, 3, "status");
      await page.__reply(status([passage, whole, odd, third], "1757145600000000004"));
      await page.waitForFunction((id: string) => !!(window as any).__cardOf(id), third.id);
      await page.waitForTimeout(50);                    // the refresh's last render (its finally) follows the status's
      box = await page.evaluate(() => (window as any).__box());
      assert.equal(box.connected, true, "the textarea is in the document");
      assert.equal(box.card, passage.id, "…in the same comment's card");
      assert.equal(box.same, true, "…which is the same card node, kept around it");
      assert.equal(box.focused, true, "the keyboard never left it");
      assert.deepEqual(box.events, { blur: 0, focusout: 0 }, "no blur, no focusout: the node was never detached");
      assert.equal(box.value, before.value, "the words");
      assert.equal(box.caret, before.caret, "the caret");
      assert.equal(box.scrollTop, before.scrollTop, "the scroll offset: still at the caret, not back at the first line");
      // the undo history survived the re-render: one undo takes typing back
      await page.keyboard.press("Control+z");
      const undone = await page.evaluate(() => (window as any).__box());
      assert.ok(undone.value.length < before.value.length, "Ctrl+Z undid typing: " + undone.value.length + " < " + before.value.length);
      assert.deepEqual(errors, [], "no script error so far");
      // a comment whose id holds a quote: Reply on it throws nothing (the selectors take the id escaped), the box moves into its card
      await page.keyboard.press("Escape");
      const oddCard = await page.evaluateHandle((id: string) => (window as any).__cardOf(id), odd.id);
      await (await oddCard.$(".fc-card-head")).click();
      const replyBtn = await page.evaluateHandle((id: string) => Array.from(document.querySelectorAll('[data-act="fcreply"]')).find((b) => (b as HTMLElement).dataset.id === id), odd.id);
      await replyBtn.click();
      await page.waitForFunction(() => { const ta = (window as any).__ta(); return !!ta && document.activeElement === ta; });
      box = await page.evaluate(() => (window as any).__box());
      assert.equal(box.card, odd.id, "the box stands in the quoted id's card");
      await page.keyboard.type("Yes.");
      await page.evaluate(() => (window as any).__saved({ mtimeNs: "10", logged: true }));
      await untilPosted(page, 4, "status");
      await page.__reply(status([passage, whole, odd, third], "1757145600000000005"));
      await page.waitForTimeout(50);
      box = await page.evaluate(() => (window as any).__box());
      assert.equal(box.card, odd.id, "kept there across the re-render");
      assert.equal(box.value, "Yes.");
      assert.ok((await page.evaluate(() => document.querySelector(".fc-sec-send")!.childNodes.length)) > 0, "the sections after the cards rendered too");
      await page.keyboard.press("Escape");
      assert.equal(await page.evaluate((id: string) => (document.activeElement as HTMLElement | null)?.dataset.act === "fcreply" && (document.activeElement as HTMLElement).dataset.id === id, odd.id), true, "Escape hands the keyboard to the card's Reply, found by the escaped id");
      assert.deepEqual(errors, [], "no script error in the page");
    });
  });
}

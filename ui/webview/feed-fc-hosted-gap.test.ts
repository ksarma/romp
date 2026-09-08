// The spacing inside a comment on a change card (.fc-hosted; renderHosted in file-comments.ts) — the review of the
// reply-place follow-on (plans/file-review.md, "The composer follow-on (2026-09-07)", its closing sentence). The
// follow-on stands a reply's box inside the card it answers, "so the reply being written reads as the next turn"
// (.fc-composer-in's comment). In a comment's own card it does: .fc-card is a flex column with a gap, so the box stands
// off the turns above and the buttons below. A hosted comment had no rule of its own (the plan's Slice 2 note: the new
// elements need none to be usable), so it was a plain block, and the box touched the turn above and the buttons below at
// 0px; when the last turn was yours, the turn and the box — the same wash, the same accent edge — merged into one block.
// .fc-hosted is a column at the turns' own gap now (.fc-replies), so its row, its turns, the box and its buttons are
// spaced as turns are. The static leg pins the rule in feed.css (the feed page loads feed.css alone) and holds it
// byte-equal to styles.css's; the browser legs mount the real bundle under the sheet's panel block and measure the gaps
// around the box in both hosted variants (turns under the comment; a comment of yours with none) against the gap between
// two turns. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic
// fixtures only: the notes-api world, placeholder ids.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");
const CHAT = fs.readFileSync(path.join(UI, "styles.css"), "utf8");

function ruleOf(css: string, head: string): string {
  const at = css.indexOf("\n" + head);
  assert.ok(at >= 0, head + " present");
  return css.slice(at + 1, css.indexOf("}", at) + 1);
}
const gapOf = (rule: string): string => { const m = /(?:^|[\s;{])gap: ([^;]+);/.exec(rule); assert.ok(m, "a gap in " + rule); return m![1]; };

// ── the static leg ─────────────────────────────────────────────────────────────────────────────────

test("feed.css: .fc-hosted is a flex column at the turns' own gap, inside the panel block beside the reply rules, layout only", () => {
  assert.equal(FEED.split("\n.fc-hosted {").length - 1, 1, "one .fc-hosted rule in feed.css");
  const hosted = ruleOf(FEED, ".fc-hosted {");
  assert.match(hosted, /display: flex;/, "a flex column: a plain block gave its children no gap");
  assert.match(hosted, /flex-direction: column;/);
  assert.equal(gapOf(hosted), gapOf(ruleOf(FEED, ".fc-replies {")), "the gap between the box and its neighbours is the gap between two turns");
  assert.doesNotMatch(hosted, /#[0-9a-fA-F]{3,8}\b|rgba?\(|font-size|margin|padding/, "layout only: no colour, no size, no box of its own");
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  const at = FEED.indexOf("\n.fc-hosted {");
  assert.ok(a >= 0 && a < at && at < b, "inside the panel block");
  assert.ok(FEED.indexOf("\n.fc-replies {") < at && at < FEED.indexOf("\n.fc-composer-in {"), "beside the reply rules, before the box's own dress");
  assert.match(FEED.slice(FEED.lastIndexOf("*/", at) - 400, at), /0px/, "the comment above it says what the plain block cost");
});

test("styles.css: the same .fc-hosted rule, byte for byte, in the same place — the panel block is one block in both sheets", () => {
  // the panel block is held byte-equal across the two sheets (file-comments.test.ts); this names the rule that drifted,
  // and where it goes: with its comment, between .fc-reply-you and the .fc-composer-in comment, as in feed.css
  const at = FEED.indexOf("\n.fc-hosted {");
  const lines = FEED.slice(FEED.lastIndexOf("\n.fc-reply-you {", at) + 1, FEED.indexOf("\n", at) + 1);
  assert.ok(CHAT.includes("\n.fc-hosted {"), "styles.css has no .fc-hosted rule; it needs feed.css's, after .fc-reply-you:\n" + lines);
  assert.equal(ruleOf(CHAT, ".fc-hosted {"), ruleOf(FEED, ".fc-hosted {"), "the rule mirrors byte for byte");
  assert.ok(CHAT.includes(lines), "the rule stands where feed.css's does, with the same comment above it:\n" + lines);
});

// ── the browser legs ───────────────────────────────────────────────────────────────────────────────

/** The panel's registry entry, bundled as the webview build bundles it (in memory), handed to the page as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\n(window as any).__romp = { fileCommentsAction };\n',
      resolveDir: UI, loader: "ts", sourcefile: "hosted-gap-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The whole file-comments block of the sheet, as the feed page loads it. */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  return FEED.slice(a, b);
}
// the tokens the block reads, resolved to plain values here (a file:// harness loads no theme), the viewer's row with
// its body and a scrolling aside of the dashboard's width
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
:root { --box-border: #555; --input-bg: #222; --fg: #ccc; --dim: #999; --accent: #9cd2ff; --accent-wash: rgba(156,210,255,0.14); --card-border: #444; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --warn: #e0a030; --green: #7cc37c; --text-faint: #777; --radius-pill: 999px; }
body { margin: 0; padding: 20px; font: 13px sans-serif; color: var(--fg); background: #1e1e1e; }
.fileview-main { display: flex; height: 600px; }
.fileview-body { flex: 1; }
.fileview-aside { flex: 0 0 340px; overflow: auto; }
${sheet()}</style></head><body><div class="fileview-main"><div class="fileview-body"></div><div class="fileview-aside"></div></div><script src="/dist/probe.js"></script></body></html>`;

// ── fixtures: the notes-api world ──────────────────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const ROOT = "/repo/notes-api";
const T0 = 1757145600000;
type Hunk = Record<string, unknown>;
const H = (id: string, kind: string, from: number, oldText: string, newText: string, ts: number): Hunk =>
  ({ id, author: "api", ts, kind, curFrom: from, curTo: from + newText.length, baseFrom: from, baseTo: from + oldText.length, oldText, newText, anchor: null });
const h1 = H("h1", "sub", 30, "reduced", "cut", T0 - 90000);
const h2 = H("h2", "sub", 80, "persist", "remain", T0 - 60000);
const SUGG = [
  { id: "h1", author: "api", authorId: SID, ts: T0 - 90000, kind: "sub", from: 30, oldText: "reduced", newText: "cut" },
  { id: "h2", author: "api", authorId: SID, ts: T0 - 60000, kind: "sub", from: 80, oldText: "persist", newText: "remain" },
];
// on h1: a comment with two turns under it, the last one yours; on h2: a comment of yours with no turns yet
const withTurns = { id: T0 + 1000 + "-5", author: "you", ts: T0 + 1000, body: "Say cut, not reduced.", suggestionId: "h1", replies: [
  { author: "api", authorId: SID, ts: T0 + 2000, body: "Done." },
  { author: "you", ts: T0 + 3000, body: "Thanks; keep it short." },
], resolved: false };
const bare = { id: T0 + 4000 + "-6", author: "you", ts: T0 + 4000, body: "Remain is right.", suggestionId: "h2", replies: [], resolved: false };
const passage = {
  id: T0 + "-118", author: "you", ts: T0, body: "Which cache? Say which.",
  anchor: { quote: "shipping the cache in v1.2", prefix: "We recommend ", suffix: "." },
  replies: [{ author: "api", authorId: SID, ts: T0 + 5000, body: "The response cache." }, { author: "you", ts: T0 + 6000, body: "Say so in the text." }],
  resolved: false,
};
type St = Record<string, unknown>;
function status(): St {
  const comments = [withTurns, bare, passage];
  return {
    verb: "status", root: ROOT, storePath: ROOT + "/.trackchanges/docs%2Freport.md.json",
    trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
    fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
    store: { v: 3, path: "docs/report.md", suggestions: SUGG, comments },
    hunks: [h1, h2], log: [], unsent: { comments: comments.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
  };
}

// ── the page side: a viewer context whose posts the test answers, as the stand-in harness does ─────────────────────
const SETUP = `window.__setup = () => {
  const posted = []; window.__posted = posted;
  const body = document.querySelector(".fileview-body"), aside = document.querySelector(".fileview-aside");
  const noop = () => {};
  const ctx = {
    path: ${JSON.stringify(ABS)}, sid: ${JSON.stringify(SID)}, todoId: null,
    body: () => body, mode: () => "rendered", text: () => null, mtimeNs: () => "1757145600000000001",
    media: () => null, mediaElement: () => null, renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
    onRendered: noop, onSelection: noop, onSaved: noop, onClose: noop,
    post: (m) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: noop, editing: () => false, setTrackedEdit: noop, guardClose: noop,
    // the panel root becomes the aside, as file-view.ts aside() makes it (the margin layout lays the panel's sections out
    // over the row's height, so the panel must be the row's flex item, not a child of one)
    aside: (el) => { const old = document.querySelector(".fileview-aside"); if (el) { el.classList.add("fileview-aside"); old.replaceWith(el); } else { const d = document.createElement("div"); d.className = "fileview-aside"; old.replaceWith(d); } },
    setMode: noop, scrollToOffset: noop, reload: noop,
  };
  const unit = window.__romp.fileCommentsAction.mount(ctx);
  body.parentElement.insertBefore(unit, body);
};
window.__reply = (st) => { const m = window.__posted[window.__posted.length - 1]; window.dispatchEvent(new MessageEvent("message", { data: Object.assign({ type: "fileCommentsResult", reqId: m.reqId }, st) })); };
window.__ta = () => document.querySelector("textarea.fc-input");
// the box and its neighbours: what stands around it, and the space above and below it, in CSS px (rounded: subpixel layout)
window.__around = () => {
  const box = document.querySelector(".fc-composer.fc-composer-in"); if (!box) return null;
  const host = box.parentElement, prev = box.previousElementSibling, next = box.nextElementSibling;
  const r = box.getBoundingClientRect(), cs = getComputedStyle(host);
  return { host: host.className, hostId: host.dataset.id || null, prev: prev ? prev.className : null, next: next ? next.className : null,
    above: prev ? Math.round(r.top - prev.getBoundingClientRect().bottom) : null,
    below: next ? Math.round(next.getBoundingClientRect().top - r.bottom) : null,
    display: cs.display, direction: cs.flexDirection, rowGap: cs.rowGap,
    boxBg: getComputedStyle(box).backgroundColor, prevBg: prev ? getComputedStyle(prev).backgroundColor : null };
};
// the space between the first two turns under a comment: what "the next turn" is spaced at
window.__turnGap = (sel) => { const rows = document.querySelectorAll(sel + " .fc-replies > .fc-reply"); return rows.length > 1 ? Math.round(rows[1].getBoundingClientRect().top - rows[0].getBoundingClientRect().bottom) : null; };
// the space between a hosted comment's own row and the turns under it (the same column)
window.__rowGap = (sel) => { const host = document.querySelector(sel); const row = host.querySelector(":scope > .fc-reply"), turns = host.querySelector(":scope > .fc-replies"); return Math.round(turns.getBoundingClientRect().top - row.getBoundingClientRect().bottom); };`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, name: "chromium" | "firefox", body: (page: any, errors: string[]) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  const current = status();
  try {
    const js = bundle() + "\n" + SETUP;
    const page = await browser.newPage({ viewport: { width: 1000, height: 700 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const req = route.request(), u = new URL(req.url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (req.method() === "HEAD") {                     // the poll's targets answer the mtimes the status carried: nothing moves on its own
        const p = u.searchParams.get("path") || "";
        const ns = p.endsWith(".trackchanges/config.json") ? current.configMtimeNs : p.includes(".trackchanges") ? current.storeMtimeNs : current.fileMtimeNs;
        return route.fulfill({ status: 200, headers: { "X-Romp-Mtime-Ns": String(ns) }, body: "" });
      }
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp && !!(window as any).__setup);
    await body(page, errors);
  } finally { await browser.close(); }
}
const untilPosted = (page: any, n: number, verb: string) => page.waitForFunction(([k, v]: [number, string]) => { const p = (window as any).__posted; return p.length >= k && p[p.length - 1].verb === v; }, [n, verb]);
/** Mount the panel, answer its probe, open it, answer its status: the cards are up. */
async function openPanel(page: any): Promise<void> {
  await page.evaluate(() => (window as any).__setup());
  await untilPosted(page, 1, "status");
  await page.evaluate((s: St) => (window as any).__reply(s), status());
  await page.waitForFunction(() => { const u = document.querySelector(".fileview-fc") as HTMLElement | null; return !!u && !u.hidden; });
  await page.click(".fileview-fc button");
  await untilPosted(page, 2, "status");
  await page.evaluate((s: St) => (window as any).__reply(s), status());
  await page.waitForSelector(".fc-card");
}
/** Open the change card and press the hosted comment's Reply: the box stands in the hosted comment and has the keyboard. */
async function replyOnHosted(page: any, changeKey: string, commentId: string): Promise<void> {
  await page.click('.fc-card[data-id="' + changeKey + '"] .fc-card-head');
  await page.waitForSelector('.fc-hosted[data-id="' + commentId + '"] [data-act="fcreply"]');
  await page.click('.fc-hosted[data-id="' + commentId + '"] [data-act="fcreply"]');
  await page.waitForFunction((id: string) => { const ta = (window as any).__ta(); return !!ta && document.activeElement === ta && !!ta.closest('.fc-hosted[data-id="' + id + '"]'); }, commentId);
}

for (const name of ["chromium", "firefox"] as const) {
  test("in " + name + ": a reply's box in a hosted comment stands off the turn above and the buttons below at the turns' own gap — no 0px seam, and a turn of yours and the box never merge", async (t) => {
    await inBrowser(t, name, async (page, errors) => {
      await openPanel(page);
      // the reference: how far apart two turns stand, and how far the box stands from its neighbours in a comment's own card
      await page.click('.fc-card[data-id="' + passage.id + '"] .fc-card-head');
      await page.click('.fc-card[data-id="' + passage.id + '"] [data-act="fcreply"]');
      await page.waitForFunction(() => { const ta = (window as any).__ta(); return !!ta && document.activeElement === ta; });
      const own = await page.evaluate(() => (window as any).__around());
      assert.ok(own && own.host.includes("fc-card") && own.above > 0 && own.below > 0, "in the comment's own card the box stands off its neighbours: " + JSON.stringify(own));
      const turnGap = await page.evaluate((id: string) => (window as any).__turnGap('.fc-card[data-id="' + id + '"]'), passage.id);
      assert.ok(turnGap > 0, "two turns stand apart: " + turnGap);
      await page.keyboard.press("Escape");
      // a hosted comment with turns under it, the last one yours: the box after the turns, before the buttons, spaced as a turn
      await replyOnHosted(page, "chg:h1", withTurns.id);
      const hosted = await page.evaluate(() => (window as any).__around());
      assert.equal(hosted.host, "fc-hosted", "the box stands in the hosted comment");
      assert.equal(hosted.hostId, withTurns.id);
      assert.equal(hosted.prev, "fc-replies", "after the turns");
      assert.equal(hosted.next, "fc-actions", "before the buttons");
      assert.equal(hosted.above, turnGap, "the box stands off the turn above by one turn gap (it was 0)");
      assert.equal(hosted.below, turnGap, "and off the buttons below by the same (it was 0)");
      assert.equal(hosted.display, "flex", "the mechanism: the hosted comment is a flex column…");
      assert.equal(hosted.direction, "column");
      assert.equal(hosted.rowGap, turnGap + "px", "…at the turns' own gap");
      const hostedTurnGap = await page.evaluate((id: string) => (window as any).__turnGap('.fc-hosted[data-id="' + id + '"]'), withTurns.id);
      assert.equal(hostedTurnGap, turnGap, "the turns under a hosted comment keep the same gap as anywhere");
      assert.equal(await page.evaluate((id: string) => (window as any).__rowGap('.fc-hosted[data-id="' + id + '"]'), withTurns.id), turnGap, "the comment's own row stands off its turns by the same gap (the same column)");
      await page.keyboard.press("Escape");
      // a comment of yours with no turns yet: the box follows the comment's own row — the same wash, the same edge — and does not merge with it
      await replyOnHosted(page, "chg:h2", bare.id);
      const after = await page.evaluate(() => (window as any).__around());
      assert.equal(after.hostId, bare.id);
      assert.equal(after.prev, "fc-reply fc-reply-you", "the box follows the comment's own row, dressed as a reply of yours");
      assert.equal(after.next, "fc-actions");
      assert.equal(after.boxBg, after.prevBg, "the two wear the same wash (the box's dress is the reply-of-yours dress)…");
      assert.equal(after.above, turnGap, "…so a seam of one turn gap is what keeps them two blocks (it was 0: one continuous wash)");
      assert.equal(after.below, turnGap);
      assert.deepEqual(errors, [], "no script error in the page");
    });
  });
}

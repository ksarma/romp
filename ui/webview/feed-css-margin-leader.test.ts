// The pushed card's leader in feed.css (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"): a card the one
// above pushes down from its mark draws a dashed leader up the gutter to its mark's height, so the reader can tell which
// passage a displaced card is about. The panel sets only the cue's data — `data-pushed` on the card and the card's inline
// `--fc-push` (file-comments.ts placeCards) — and the sheet's `.fc-margin .fc-card[data-pushed]::before` rule is the one
// painter. Nothing asserted the painter: with the rule deleted from BOTH sheets the panel's tests (which read the attribute
// and the variable), the sheets' byte-equal check and the guide's cross-check all stayed green (the 2026-09-07 review of the
// follow-on). The static leg pins the rule's declarations in feed.css, inside the file-comments block, keyed on the attribute
// and the variable the panel writes (a rename on either side fails here), and holds styles.css to the same rule. The browser
// legs mount the worktree's panel under feed.css's own rules in Chromium and Firefox and read the pseudo-element's computed
// box off a card the one above pushed: dashed, as tall as the push, its top at the mark's height, inside the track's box; and
// no leader on a card nothing pushed. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs
// do. Synthetic values only: invented prose, placeholder ids.
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
const PANEL = fs.readFileSync(path.join(UI, "file-comments.ts"), "utf8");

const BLOCK_A = "/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)";
const BLOCK_B = "/* ── end file comments panel ── */";
const SEL = ".fc-margin .fc-card[data-pushed]::before";

/** The one rule whose head is `sel` in `css`, whole. */
function rule(css: string, sel: string, where: string): string {
  const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(css);
  assert.ok(m, "a rule for " + sel + " in " + where);
  return m![1];
}
/** The rule's declarations, one string each, whitespace collapsed. */
function decls(r: string): string[] {
  return r.slice(r.indexOf("{") + 1, r.lastIndexOf("}")).split(";").map((d) => d.replace(/\s+/g, " ").trim()).filter(Boolean);
}

// ── the static leg: the sheet paints the leader off the attribute and the variable the panel writes ─────

test("feed.css: a pushed card's leader is the sheet's ::before, dashed, as tall as the push, running up from the card, inside the panel block", () => {
  const a = FEED.indexOf(BLOCK_A), b = FEED.indexOf(BLOCK_B);
  assert.ok(a >= 0 && b > a, "the file-comments block's markers");
  const r = rule(FEED, SEL, "feed.css");
  const at = FEED.indexOf(r);
  assert.ok(at > a && at < b, "the leader rule sits in the file-comments block (the block both sheets hold byte-equal)");
  const d = decls(r);
  assert.ok(d.includes('content: ""'), "a generated box, empty: " + d.join("; "));
  assert.ok(d.includes("position: absolute"), "placed against the card (the card is itself absolute in the track): " + d.join("; "));
  assert.ok(d.includes("height: var(--fc-push, 0px)"), "as tall as the push: " + d.join("; "));
  assert.ok(d.includes("top: calc(-1 * var(--fc-push, 0px))"), "running UP from the card's top, so its far end is at the mark's height: " + d.join("; "));
  assert.ok(d.some((x) => /^border-left: 1px dashed var\(--text-faint\)$/.test(x)), "a dashed hairline in the faint ink, a token: " + d.join("; "));
  const left = d.find((x) => x.startsWith("left: "));
  assert.ok(left && parseFloat(left.slice(6)) < 0, "in the gutter, left of the card's box: " + left);
  // the seam: the attribute the selector keys on and the variable the rule reads are the ones placeCards writes — the
  // byte-equal check holds the two sheets to each other, never the sheet to the panel
  assert.match(PANEL, /node\.dataset\.pushed = "1"; node\.style\.setProperty\("--fc-push", Math\.min\(p\.pushed, p\.top\) \+ "px"\);/, "placeCards marks a pushed card and writes its push");
  assert.match(PANEL, /delete node\.dataset\.pushed; node\.style\.removeProperty\("--fc-push"\);/, "and clears both on a card nothing pushes");
});

test("styles.css: the chat page's sheet holds the same leader rule", () => {
  assert.equal(rule(CHAT, SEL, "styles.css"), rule(FEED, SEL, "feed.css"));
});

// ── the browser legs ─────────────────────────────────────────────────────────────────────────────

/** The panel's registry entry and marked, bundled as the webview build bundles them (in memory), as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "margin-leader-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under: the viewer's card, body and prose, the buttons, and the whole file-comments block. */
function sheet(): string {
  const a = FEED.indexOf(BLOCK_A), b = FEED.indexOf(BLOCK_B);
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const r = (sel: string): string => rule(FEED, sel, "feed.css");
  return [r(".fileview"), r(".fileview-body"), r(".fileview-md"), r(".fileview-md p"), r(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4"), r(".fileview-btn"), FEED.slice(a, b)].join("\n");
}
// the viewer's own ancestry: `.fileview` (the card) > `.fileview-main` (the row) > `.fileview-body` + the aside the panel mounts
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; }
${sheet()}
#wrap { width: 1000px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/margin-leader.js"></script></body></html>`;

// ── the document and its comments (synthetic prose) ────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
const SRC = "# Report\n\n" + Array.from({ length: 12 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const comment = (i: number, n: number): Record<string, unknown> => ({
  id: (T0 + n) + "-" + i, author: "you", ts: T0 + n, body: "Note on paragraph " + i + ".",
  anchor: { quote: "Paragraph " + i + " of the report", prefix: "", suffix: " says something about the cache" }, replies: [], resolved: false,
});
// marks on paragraphs 3 and 4, a line apart: the second card cannot fit beside its paragraph and is pushed under the first;
// paragraph 9's mark is far enough down that nothing pushes its card
const COMMENTS = [comment(3, 1), comment(4, 2), comment(9, 3)];
const KEYS = { c3: COMMENTS[0].id as string, c4: COMMENTS[1].id as string, c9: COMMENTS[2].id as string };
const STATUS = {
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: COMMENTS },
  hunks: [], log: [],
  unsent: { comments: COMMENTS.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
};

type Box = { top: number; bottom: number; left: number; right: number; height: number };
type Leader = { content: string; position: string; borderLeftStyle: string; borderLeftWidth: string; top: string; height: string; left: string };
type Scene = {
  margin: boolean; trackBox: Box;
  cards: Record<string, Box & { pushed: string | null; push: string; leader: Leader }>; marks: Record<string, Box | null>;
};

/** Mount the panel over the rendered document, answer its status asks, open it, and let the paint and the pass run. */
function mount(page: any): Promise<void> {
  return page.evaluate(async ([src, status, abs, sid]: [string, Record<string, unknown>, string, string]) => {
    const w = window as any;
    const body = document.getElementById("body")!, md = document.getElementById("md")!;
    md.innerHTML = w.__romp.marked.parse(src);
    const posted: any[] = []; w.__posted = posted;
    const rendered: Array<() => void> = []; w.__rendered = rendered;
    const ctx = {
      path: abs, sid, todoId: null,
      body: () => body, mode: () => "rendered", text: () => src, mtimeNs: () => "1757145600000000001", media: () => null, mediaElement: () => null,
      renderedImages: () => [], pdfPages: () => [], identity: () => ({ name: "api", color: null }),
      onRendered: (cb: () => void) => { rendered.push(cb); }, onSelection: () => { /* inert */ }, onSaved: () => { /* inert */ }, onClose: () => { /* inert */ },
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
  }, [SRC, STATUS, ABS, SID]);
}
/** Each card's box, its push data and its ::before's computed style; each mark's box; the track's box. */
const scene = (page: any, keys: Record<string, string>): Promise<Scene> => page.evaluate((keys: Record<string, string>) => {
  const body = document.getElementById("body")!;
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const track = aside.querySelector(".fc-sec-cards") as HTMLElement;
  const box = (el: Element) => { const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, left: r.left, right: r.right, height: r.height }; };
  const cards: Record<string, any> = {}, marks: Record<string, any> = {};
  for (const [name, key] of Object.entries(keys)) {
    const card = aside.querySelector('.fc-card[data-id="' + key + '"]') as HTMLElement | null;
    if (card) {
      const cs = getComputedStyle(card, "::before");
      cards[name] = {
        ...box(card), pushed: card.dataset.pushed ?? null, push: card.style.getPropertyValue("--fc-push"),
        leader: { content: cs.content, position: cs.position, borderLeftStyle: cs.borderLeftStyle, borderLeftWidth: cs.borderLeftWidth, top: cs.top, height: cs.height, left: cs.left },
      };
    } else cards[name] = null;
    const m = body.querySelector('[data-act="fcopen"][data-id="' + key + '"]');
    marks[name] = m ? box(m) : null;
  }
  return { margin: aside.classList.contains("fc-margin"), trackBox: box(track), cards, marks };
}, keys);
const near = (a: number, b: number, msg: string, tol = 1) => assert.ok(Math.abs(a - b) <= tol, msg + ": " + a + " vs " + b);

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
      if (u.pathname === "/dist/margin-leader.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: the card the one above pushed wears a dashed leader up the gutter to its mark's height, inside the track; a card nothing pushed wears none`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page);
      const s = await scene(page, KEYS);
      assert.equal(s.margin, true, "the margin layout is on");
      for (const k of ["c3", "c4", "c9"]) { assert.ok(s.cards[k], k + "'s card is in the aside"); assert.ok(s.marks[k], k + "'s mark is painted"); }
      // the setup the cue is for: paragraph 4's mark is closer under paragraph 3's than a card is tall, so its card sits
      // under paragraph 3's, pushed down from its own mark
      assert.ok(s.marks.c4!.top - s.marks.c3!.top < s.cards.c3.height, "the two marks are closer than a card is tall: " + (s.marks.c4!.top - s.marks.c3!.top) + " vs " + s.cards.c3.height);
      assert.equal(s.cards.c4.pushed, "1", "paragraph 4's card is marked pushed");
      const push = s.cards.c4.top - s.marks.c4!.top;
      assert.ok(push > 4, "and stands well below its mark: " + push);
      near(parseFloat(s.cards.c4.push), push, "the inline variable is the push");
      // the leader itself — the sheet's generated box, not the data: a dashed hairline as tall as the push, running up
      // from the card's top so its far end is level with the mark
      const L = s.cards.c4.leader;
      assert.equal(L.content, '""', "the pushed card has a generated box");
      assert.equal(L.position, "absolute");
      assert.equal(L.borderLeftStyle, "dashed", "the leader is dashed");
      assert.equal(L.borderLeftWidth, "1px", "a hairline");
      near(parseFloat(L.height), push, "the leader is as tall as the push");
      near(s.cards.c4.top + parseFloat(L.top), s.marks.c4!.top, "the leader's top is at the mark's height (card top " + s.cards.c4.top + ", leader top " + L.top + ")");
      // in the gutter, left of the card's box, and still inside the track's box (the track clips what leaves it)
      const leaderX = s.cards.c4.left + parseFloat(L.left);
      assert.ok(leaderX < s.cards.c4.left, "the leader stands left of the card: " + leaderX + " vs " + s.cards.c4.left);
      assert.ok(leaderX >= s.trackBox.left, "and inside the track, where the track's overflow does not clip it: " + leaderX + " vs " + s.trackBox.left);
      // a card nothing pushed: level with its mark, no leader
      for (const k of ["c3", "c9"]) {
        assert.equal(s.cards[k].pushed, null, k + " is not pushed");
        near(s.cards[k].top, s.marks[k]!.top, k + "'s card is level with its mark");
        assert.equal(s.cards[k].leader.content, "none", k + " wears no leader");
      }
    });
  });
}

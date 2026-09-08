// The footer's rule in the margin layout (plans/file-review.md, "The margin-layout follow-on (2026-09-07)"): the track
// clips its cards at its bottom edge, and the footer — the foot (Accept all · Reject all), the rows the list held (a
// fold, the empty note, a loader), then the Send box — begins right under it. The first review put the footer's rule on
// the foot alone (`.fc-sec-send > .fc-foot { border-top }`), the Send box carrying its own since Slice 1; a footer with
// rows and no pending change — a comments-only file with a resolved comment, the common state after one loop — began
// with a fold flush under the clipped cards and drew its one rule under the fold, above Send (the 2026-09-07 review,
// noted as a leftover; fixed in the review's consolidation). The rule now stands on the Send section's own top edge in
// both sheets, and the Send box drops its own when nothing stands before it, so the footer begins under one hairline
// whichever row comes first and never under two. The static leg pins both rules in each sheet, inside the file-comments
// block, after the shared section rule they override, and the old rule gone; the browser legs mount the worktree's panel
// under feed.css's own rules in Chromium and Firefox in three worlds — comments alone, a resolved comment (the Resolved
// fold first), a pending change (the foot first) — and read the computed borders: one hairline at the section's top,
// level with the track's bottom edge, none on the first row, the Send box's own only when a row stands before it, and
// nothing past the aside's edge. Skips LOUDLY without a playwright browser (CI installs none), as the other browser
// legs do. Synthetic values only: invented prose, placeholder ids.
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
const EDGE = "\n.fc-margin > .fc-sec-send { padding-top: 8px; border-top: 1px solid var(--card-border); }";
const FIRST = "\n.fc-margin .fc-sec-send > .fc-send:first-child { padding-top: 0; border-top: 0; }";
const SHARED = "\n.fc-margin > .fc-sec-send, .fc-margin > .fc-sec-log { flex: 0 1 auto; min-height: 0; overflow: auto; padding: 0 12px; }";

function fcBlock(css: string, name: string): string {
  const a = css.indexOf(BLOCK_A), b = css.indexOf(BLOCK_B);
  assert.ok(a >= 0 && b > a, name + ": the file-comments block's markers");
  return css.slice(a, b);
}

/** The one rule whose head is `sel` in `css`, whole. */
function rule(css: string, sel: string, where: string): string {
  const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(css);
  assert.ok(m, "a rule for " + sel + " in " + where);
  return m![1];
}

// ── the static leg ───────────────────────────────────────────────────────────────────────────────

test("both sheets: the footer's rule stands on the Send section's top edge, after the shared rule it overrides; the Send box drops its own when first; the foot's rule is gone", () => {
  for (const [name, css] of [["feed.css", FEED], ["styles.css", CHAT]] as const) {
    const block = fcBlock(css, name);
    const shared = block.indexOf(SHARED);
    assert.ok(shared >= 0, name + ": the shared section rule (flex, overflow, padding: 0 12px) the edge rule overrides");
    const edge = block.indexOf(EDGE);
    assert.ok(edge > shared, name + ": the edge rule follows the shared rule — same specificity, so source order is what makes its padding-top win");
    assert.ok(block.includes(FIRST), name + ": the Send box drops its own padding and rule when nothing stands before it, so the footer never begins under two hairlines");
    assert.ok(!/\.fc-sec-send > \.fc-foot \{/.test(block), name + ": the first review's rule on the foot alone is gone");
    assert.match(rule(block, ".fc-send", name), /padding-top: 8px; border-top: 1px solid var\(--card-border\);/, name + ": the Send box's own rule stands, for the list layout and for a footer whose rows come before Send");
  }
  assert.equal(fcBlock(FEED, "feed.css"), fcBlock(CHAT, "styles.css"), "the two sheets' blocks are one");
  // the seam: the panel moves every row before the Send box, so the box is first only when the footer holds no row
  assert.match(PANEL, /for \(const r of rows\) if \(r !== foot\) send\.insertBefore\(r, box\);/, "moveRows puts every row before the Send box");
  assert.match(PANEL, /if \(foot\) this\.sections\.send\.insertBefore\(foot, this\.sections\.send\.firstChild\);/, "and the foot first of all");
});

// ── the browser legs ─────────────────────────────────────────────────────────────────────────────

/** The panel's registry entry and marked, bundled as the webview build bundles them (in memory), as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "margin-footer-rule-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under: the viewer's card, body and prose, the buttons, and the whole file-comments block. */
function sheet(): string {
  const r = (sel: string): string => rule(FEED, sel, "feed.css");
  return [r(".fileview"), r(".fileview-body"), r(".fileview-md"), r(".fileview-md p"), r(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4"), r(".fileview-btn"), fcBlock(FEED, "feed.css")].join("\n");
}
// the viewer's own ancestry: `.fileview` (the card) > `.fileview-main` (the row) > `.fileview-body` + the aside the panel mounts
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; }
${sheet()}
#wrap { width: 1000px; height: 500px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/margin-footer-rule.js"></script></body></html>`;

// ── the document and its three worlds (synthetic prose) ──────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
const SRC = "# Report\n\n" + Array.from({ length: 12 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const comment = (i: number, n: number, resolved = false): Record<string, unknown> => ({
  id: (T0 + n) + "-" + i, author: "you", ts: T0 + n, body: "Note on paragraph " + i + ".",
  anchor: { quote: "Paragraph " + i + " of the report", prefix: "", suffix: " says something about the cache" }, replies: [], resolved,
});
// one change: a word the session inserted in paragraph 6 (its foot goes to the footer)
const INS_AT = SRC.indexOf("Paragraph 6 of the report");
const HUNK = { id: "h1", author: "api", ts: T0 - 30000, kind: "ins", curFrom: INS_AT, curTo: INS_AT + 9, baseFrom: INS_AT, baseTo: INS_AT, oldText: "", newText: "Paragraph", anchor: null };
const status = (comments: Array<Record<string, unknown>>, hunks: Array<Record<string, unknown>>): Record<string, unknown> => ({
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments },
  hunks, log: [],
  unsent: { comments: comments.filter((c) => !c.resolved).map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
});
/** Comments alone: the footer is the Send box. */
const ALONE = status([comment(3, 1), comment(9, 2)], []);
/** One comment resolved: the Resolved fold is the footer's first row, the Send box after it. */
const RESOLVED = status([comment(3, 1), comment(9, 2, true)], []);
/** A pending change: the foot (Accept all · Reject all) is first, the Send box after it. */
const CHANGE = status([comment(3, 1)], [HUNK]);

type Edge = { border: string; pad: string; cls: string; top: number };
type Scene = { margin: boolean; section: Edge; kids: Edge[]; trackBottom: number; asideScroll: number; asideClient: number };

/** Mount the panel over the rendered document, answer its status asks with `status`, open it, and let the paint and the pass run. */
function mount(page: any, status: Record<string, unknown>): Promise<void> {
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
      post: (m: any) => { posted.push(m); }, ensureEditingAllowed: async () => true, setEditBlocked: () => { /* inert */ }, editing: () => false, setTrackedEdit: () => { /* inert */ },
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
/** The Send section's computed top edge and its element children's, in order; the track's bottom; the aside's scroll range. */
const scene = (page: any): Promise<Scene> => page.evaluate(() => {
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const send = aside.querySelector(".fc-sec-send") as HTMLElement;
  const track = aside.querySelector(".fc-sec-cards") as HTMLElement;
  const edge = (el: Element) => { const s = getComputedStyle(el); return { border: s.borderTopWidth, pad: s.paddingTop, cls: (el as HTMLElement).className, top: el.getBoundingClientRect().top }; };
  const kids = Array.from(send.children).filter((k) => !(k as HTMLElement).hidden);
  return { margin: aside.classList.contains("fc-margin"), section: edge(send), kids: kids.map(edge), trackBottom: track.getBoundingClientRect().bottom, asideScroll: aside.scrollHeight, asideClient: aside.clientHeight };
});
const near = (a: number, b: number, msg: string, tol = 1) => assert.ok(Math.abs(a - b) <= tol, msg + ": " + a + " vs " + b);
/** What every world shares: the margin layout on; one hairline on the section's top edge, level with the track's bottom;
 *  none on the first row; the Send box last, wearing its own only when a row stands before it; nothing past the aside. */
function holds(s: Scene, world: string, first: string): void {
  assert.equal(s.margin, true, world + ": the margin layout is on");
  assert.equal(s.section.border, "1px", world + ": the footer's rule is on the Send section's top edge");
  assert.equal(s.section.pad, "8px", world + ": with the foot's old padding");
  near(s.section.top, s.trackBottom, world + ": the rule sits where the track's clipped cards end");
  assert.ok(s.kids.length >= 1, world + ": the section has children");
  assert.ok(s.kids[0].cls.split(" ").includes(first), world + ": the first row is the " + first + ": " + s.kids[0].cls);
  assert.equal(s.kids[0].border, "0px", world + ": the first row wears no rule of its own — one hairline, not two: " + s.kids[0].cls);
  const last = s.kids[s.kids.length - 1];
  assert.ok(last.cls.split(" ").includes("fc-send"), world + ": the Send box is last: " + last.cls);
  assert.equal(last.border, s.kids.length > 1 ? "1px" : "0px", world + ": the Send box wears its own rule only when a row stands before it");
  assert.equal(last.pad, s.kids.length > 1 ? "8px" : "0px", world + ": and its own padding only then");
  assert.ok(s.asideScroll <= s.asideClient + 1, world + ": nothing past the aside's edge: " + s.asideScroll + " in " + s.asideClient);
}

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
      if (u.pathname === "/dist/margin-footer-rule.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  test(`in ${name}: the footer begins under one hairline whichever row comes first — the Send box alone, the Resolved fold, the foot — and the Send box wears its own only behind a row`, async (t) => {
    await inBrowser(t, name, async (page) => {
      await mount(page, ALONE);
      holds(await scene(page), "comments alone", "fc-send");
    });
    await inBrowser(t, name, async (page) => {
      await mount(page, RESOLVED);
      const s = await scene(page);
      holds(s, "a resolved comment", "fc-sec");
      assert.equal(s.kids.length, 2, "the Resolved fold, then the Send box: " + s.kids.map((k) => k.cls).join(", "));
      assert.ok(s.kids[0].top >= s.section.top + 8, "the fold stands under the rule, in the padding's room: " + s.kids[0].top + " vs " + s.section.top);
    });
    await inBrowser(t, name, async (page) => {
      await mount(page, CHANGE);
      const s = await scene(page);
      holds(s, "a pending change", "fc-foot");
      assert.equal(s.kids[0].pad, "0px", "the foot carries no padding of its own now: the section's is the footer's");
      assert.equal(s.kids.length, 2, "the foot, then the Send box: " + s.kids.map((k) => k.cls).join(", "));
    });
  });
}

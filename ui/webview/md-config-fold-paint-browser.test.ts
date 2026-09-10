// A comment whose passage spans two blocks inside a folded callout (plans/markdown-viewer.md, Slice 4: `> [!type]+` and
// `> [!type]-` render a <details> whose body is marked's block output), or runs from a fold's last block into the block
// after the fold. marked leaves a "\n" text node after each block inside the details, the node it leaves between blocks
// everywhere; the painter skipped such a node by its PARENT's tag from a list of block containers, DETAILS not among them,
// so the panel wrapped each such node as a mark of its own: an empty ringed box on a line between the blocks (the sheet's
// 2px side padding and inset ring on an inline box), the details taller per mark and everything below moved down, on every
// paint pass; a closed fold showed the box the moment a card's quote button opened it. The figures follow the prose's font.
// In this leg's scene (a 14px/1.5 sans-serif body that sets neither --fs nor --font-doc, so .fileview-md's font-size and
// font-family are invalid at computed-value time and the prose stays 14px on 21px lines) the box is 4 x 16 px and a fold
// grows 21 to 28 px per mark: the fail-before actual is `DETAILS.md-callout "\n" 4x16`, and with the mark assertions
// stripped the fold 'Two paragraphs' is 95.19 px unpainted against 123.19 painted. The 4 x 18 px and 22 px per mark that
// anchor-map.ts skipBlockWs quotes are the viewer's own prose (13px x 1.15 in its sans), a different font. On main the same
// markdown is a plain blockquote and painted clean (the Slice 4 review, round 8). Now a whitespace-only text node with a
// block-level box on both sides, or at the edge of a block-level parent, is skipped whatever its parent is (anchor-map.ts
// skipBlockWs, the block set derived from the sanitizer's allowlist, md-config-paint-whitespace-browser.test.ts), and every
// other blank is painted and measured in the browser's layout, its mark unwrapped at zero width (trimCollapsedMarks, round 12).
// Over the REAL file-comments.ts bundle in headless Chromium, mounted as md-config-goto-closed-details-browser.test.ts
// mounts it, the markdown parsed by the one configuration (md-config.ts applyMdConfig) so the folds are the viewer's own.
// The measure: the layout of the note with every fold open, read before the panel paints and after, must be the same box
// for box (each details' height, each top-level block's top); no mark under any comment's id is whitespace-only or stands
// directly under a details; the comment's marks are its blocks' text. A control comment on a single paragraph inside a
// fold (the shape the fold legs elsewhere paint) shows the paint path itself is never in question. Skips LOUDLY without a
// playwright browser (CI installs none), as the other browser legs do. Synthetic values only: an invented note, a
// placeholder sid, TESTHOST paths.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const FEED = fs.readFileSync(path.join(UI, "feed.css"), "utf8");

/** The panel's registry entry and marked, with the viewer's grammar applied, bundled as the webview build bundles them. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\nimport { applyMdConfig } from "./md-config";\napplyMdConfig();\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "fold-paint-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the scene lives under: the viewer's body and prose, the constructs (callouts, front matter) and the whole
 *  file-comments block (the row, the aside and its fold, the cards, the highlights, the margin layout). */
function sheet(): string {
  const a = FEED.indexOf("/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)");
  const b = FEED.indexOf("/* ── end file comments panel ── */");
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in feed.css");
  const rule = (sel: string): string => {
    const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(FEED);
    assert.ok(m, "a rule for " + sel + " in feed.css");
    return m![1];
  };
  const constructs = FEED.split("\n").filter((l) => l.startsWith(".md ") && /md-callout|md-frontmatter/.test(l)).join("\n");
  assert.ok(constructs.includes("md-frontmatter") && constructs.includes("md-callout"), "the constructs' rules in feed.css");
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-md h1, .fileview-md h2, .fileview-md h3, .fileview-md h4, .fileview-md h5, .fileview-md h6"), rule(".fileview-btn"), constructs, FEED.slice(a, b)].join("\n");
}
// the viewer's own ancestry: `.fileview` (the card) > `.fileview-main` (the row) > `.fileview-body` + the aside the panel mounts
const PAGE = (width: number): string => `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; --box-border: #444; --err: #f66; --st-awaitbg-bg: #7c7; --st-compacting-bg: #6cc; }
${sheet()}
#wrap { width: ${width}px; height: 2000px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/probe.js"></script></body></html>`;

// ── the note and its comments (synthetic prose) ────────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/tmp/TESTHOST/notes-api/docs/report.md";
const T0 = 1757145600000;
// an open fold of two paragraphs, a closed fold of two, an open fold whose body is a paragraph, a list and a paragraph, a fold
// nested in a fold, and a one-paragraph fold followed by a paragraph; plain paragraphs between every two constructs
const SRC = [
  "# Report", "",
  "Intro paragraph of the report.", "",
  "> [!note]+ Two paragraphs", "> First body para.", ">", "> Second body para.", "",
  "Para after the open fold.", "",
  "> [!note]- Closed two", "> Closed first para.", ">", "> Closed second para.", "",
  "Para after the closed fold.", "",
  "> [!tip]+ Three blocks", "> Lead para.", ">", "> - alpha item", "> - beta item", ">", "> Tail para.", "",
  "Para after the three blocks.", "",
  "> [!note]+ Outer", "> Outer body.", ">", "> > [!note]+ Inner", "> > Inner first.", "> >", "> > Inner second.", ">", "> Outer after.", "",
  "Para after the nested fold.", "",
  "> [!important]+ Tail fold", "> Tail body para.", "",
  "Para after the tail fold.", "",
  "> [!warning]+ Single", "> Single body para.", "",
  "Last paragraph of the report.", "",
].join("\n");
const slice = (a: string, b: string): string => { const s = SRC.indexOf(a), e = SRC.indexOf(b, s); assert.ok(s >= 0 && e >= 0, a + " .. " + b); return SRC.slice(s, e + b.length); };
const comment = (i: number, quote: string, prefix: string, suffix: string): Record<string, unknown> => ({
  id: (T0 + i) + "-" + i, author: "you", ts: T0 + i, body: "Note " + i + ".", anchor: { quote, prefix, suffix }, replies: [], resolved: false,
});
/** Each comment and the text its marks must read, block by block (a nested fold's title is painted with the range that covers it,
 *  the standing rule for a hole inside a range, and is left out of this list). */
const C: Record<string, { c: Record<string, unknown>; texts: string[] }> = {
  twoOpen: { c: comment(1, slice("First body para.", "Second body para."), "> ", "\n\nPara after the open"), texts: ["First body para.", "Second body para."] },
  twoClosed: { c: comment(2, slice("Closed first para.", "Closed second para."), "> ", "\n\nPara after the closed"), texts: ["Closed first para.", "Closed second para."] },
  three: { c: comment(3, slice("Lead para.", "Para after the three blocks."), "> ", "\n\n> [!note]+ Outer"), texts: ["Lead para.", "alpha item", "beta item", "Tail para.", "Para after the three blocks."] },
  nested: { c: comment(4, slice("Outer body.", "Outer after."), "> ", "\n\nPara after the nested"), texts: ["Outer body.", "Inner first.", "Inner second.", "Outer after."] },
  bodyToAfter: { c: comment(5, slice("Tail body para.", "Para after the tail fold."), "> ", "\n\n> [!warning]"), texts: ["Tail body para.", "Para after the tail fold."] },
  single: { c: comment(6, "Single body para.", "> ", "\n\nLast paragraph"), texts: ["Single body para."] },
};
const KEY = Object.fromEntries(Object.entries(C).map(([k, v]) => [k, v.c.id as string])) as Record<keyof typeof C, string>;
const COMMENTS = Object.values(C).map((v) => v.c);
const STATUS = {
  verb: "status", root: "/tmp/TESTHOST/notes-api", storePath: "/tmp/TESTHOST/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy: { kind: "file", entry: "docs/report.md" }, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: COMMENTS }, hunks: [], log: [],
  unsent: { comments: COMMENTS.map((c) => c.id), replies: [], accepted: 0, rejected: 0, watermark: null },
};

type Layout = { details: Array<{ title: string; open: boolean; height: number }>; tops: Array<[string, number]>; mdHeight: number; wsUnderDetails: number };
type Mark = { parent: string; text: string; wsOnly: boolean; width: number; height: number; visible: boolean };

/** Render the note into the body (as mount does before the panel paints) and read its layout. */
function render(page: any): Promise<Layout> {
  return page.evaluate((src: string) => {
    const w = window as any;
    const md = document.getElementById("md")!;
    md.innerHTML = w.__romp.marked.parse(src);
    return w.__readLayout();
  }, SRC);
}
/** The layout with every fold OPEN (a shut fold's body has no box to compare; the folds' own states are put back after):
 *  each details' height, each top-level block's top, the body's height, and the count of whitespace-only text nodes standing
 *  directly under a details (the fixture must hold the nodes the rule is about). */
const READ_LAYOUT = `window.__readLayout = () => {
  const md = document.getElementById("md");
  const all = Array.from(md.querySelectorAll("details"));
  const was = all.map((d) => d.hasAttribute("open"));
  for (const d of all) d.setAttribute("open", "");
  const details = all.map((d, i) => ({ title: (d.querySelector("summary") || {}).textContent || "", open: was[i], height: d.getBoundingClientRect().height }));
  const tops = Array.from(md.children).map((c) => [c.tagName + "." + (c.className || "").split(" ")[0] + " " + (c.textContent || "").trim().slice(0, 24), c.getBoundingClientRect().top]);
  const mdHeight = md.getBoundingClientRect().height;
  let wsUnderDetails = 0;
  for (const d of all) for (const n of Array.from(d.childNodes)) if (n.nodeType === 3 && !(n.textContent || "").trim()) wsUnderDetails++;
  all.forEach((d, i) => { if (!was[i]) d.removeAttribute("open"); });
  return { details, tops, mdHeight, wsUnderDetails };
};`;

/** Mount the panel over the rendered note, answer its status asks, open it, and let the paint and the pass run. */
function mount(page: any): Promise<void> {
  return page.evaluate(async ([src, status, abs, sid]: [string, Record<string, unknown>, string, string]) => {
    const w = window as any;
    const body = document.getElementById("body")!;
    const posted: any[] = [];
    const rendered: Array<() => void> = [];
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
const layout = (page: any): Promise<Layout> => page.evaluate(() => (window as any).__readLayout());
const marksOf = (page: any, id: string): Promise<Mark[]> => page.evaluate((id: string) => Array.from(document.querySelectorAll('#body .fc-hl[data-id="' + id + '"]')).map((m) => {
  const p = m.parentElement!, r = m.getBoundingClientRect();
  return { parent: p.tagName + "." + (p.className || "").split(" ")[0], text: m.textContent || "", wsOnly: !(m.textContent || "").trim(), width: r.width, height: r.height, visible: (m as any).checkVisibility() };
}), id);
const frames = (page: any, n = 3): Promise<void> => page.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
const click = (page: any, sel: string): Promise<void> => page.evaluate((sel: string) => { const n = document.querySelector(sel) as HTMLElement | null; if (!n) throw new Error("no node for " + sel); n.click(); }, sel);
const isTitle = (m: Mark): boolean => m.parent.endsWith(".md-callout-title");

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, width: number, body: (page: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright chromium on this box; this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle() + "\n" + READ_LAYOUT;
    const page = await browser.newPage({ viewport: { width: 1100, height: 900 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE(width) });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    await page.waitForFunction(() => !!(window as any).__romp && !!(window as any).__readLayout);
    await body(page);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

/** The painted layout against the unpainted one: the same folds at the same heights, every top-level block where it stood. */
function expectSameLayout(before: Layout, after: Layout, what: string): void {
  assert.equal(after.details.length, before.details.length, what + ": as many folds as before");
  for (let i = 0; i < before.details.length; i++) {
    assert.equal(after.details[i].title, before.details[i].title, what + ": fold " + i + " is the same fold");
    assert.ok(Math.abs(after.details[i].height - before.details[i].height) < 0.5, what + ": fold " + JSON.stringify(before.details[i].title) + " keeps its height: " + before.details[i].height + " unpainted, " + after.details[i].height + " painted");
  }
  assert.deepEqual(after.tops.map((t) => t[0]), before.tops.map((t) => t[0]), what + ": the same top-level blocks");
  const moved = before.tops.map((t, i) => [t[0], after.tops[i][1] - t[1]] as [string, number]).filter((m) => Math.abs(m[1]) >= 0.5);
  assert.deepEqual(moved, [], what + ": no top-level block moved (block, px moved)");
  assert.ok(Math.abs(after.mdHeight - before.mdHeight) < 0.5, what + ": the body keeps its height: " + before.mdHeight + " to " + after.mdHeight);
}

test("a comment across two blocks of a folded callout, or from a fold's body into the block after it, paints its blocks' text and no whitespace-only mark, and moves nothing: the folds keep their heights and every block its place", async (t) => {
  await inBrowser(t, 1000, async (page) => {
    const before = await render(page);
    assert.ok(before.wsUnderDetails >= 8, "the fixture holds whitespace-only text nodes directly under its details (the nodes the rule is about): " + before.wsUnderDetails);
    assert.deepEqual(before.details.map((d) => [d.title, d.open]), [["Two paragraphs", true], ["Closed two", false], ["Three blocks", true], ["Outer", true], ["Inner", true], ["Tail fold", true], ["Single", true]], "the note's folds, as the one grammar renders them");
    await mount(page);
    await frames(page);
    for (const k of Object.keys(C) as Array<keyof typeof C>) {
      const marks = await marksOf(page, KEY[k]);
      assert.ok(marks.length >= C[k].texts.length, k + ": every block of the passage painted: " + JSON.stringify(marks.map((m) => [m.parent, m.text])));
      assert.deepEqual(marks.filter((m) => m.wsOnly).map((m) => [m.parent, JSON.stringify(m.text), Math.round(m.width) + "x" + Math.round(m.height), m.visible]), [], k + ": no whitespace-only mark (parent, text, box, visible)");
      assert.deepEqual(marks.filter((m) => m.parent.startsWith("DETAILS.")), [], k + ": no mark stands directly under a details");
      assert.deepEqual(marks.filter((m) => !isTitle(m)).map((m) => m.text), C[k].texts, k + ": the marks read the blocks' text");
    }
    const painted = await layout(page);
    expectSameLayout(before, painted, "painted");
    // the closed fold, opened by its card's quote button (goTo runs the reveal): its two marks show, no third box appears with
    // them, and the layout with every fold open is still the unpainted one
    await click(page, '.fc-card[data-id="' + KEY.twoClosed + '"] [data-act="fcgoto"]'); await frames(page);
    const opened: boolean = await page.evaluate(() => document.querySelector("#md details.md-callout-note:nth-of-type(1)") !== null && Array.from(document.querySelectorAll("#md details")).some((d) => (d.querySelector("summary")?.textContent || "") === "Closed two" && d.hasAttribute("open")));
    assert.equal(opened, true, "the quote button opened the closed fold");
    const shown = await marksOf(page, KEY.twoClosed);
    assert.deepEqual(shown.map((m) => [m.text, m.visible]), [["Closed first para.", true], ["Closed second para.", true]], "the closed fold's comment: its two paragraphs, visible, and nothing else");
    expectSameLayout(before, await layout(page), "after the fold opened");
  });
});

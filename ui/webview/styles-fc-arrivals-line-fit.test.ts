// The arrivals line under the panel's header (plans/file-review.md, "The arrivals follow-on (2026-09-09)" under Slice 2)
// against the margin layout's fit rules in styles.css (styles-fc-margin-fit.test.ts holds those). The head section gives
// first, down to a floor, while it holds anything beyond its control rows — and the line, the head's LAST child, counted
// as that growth: with the Send confirm up, a 600px viewer cut the line at the section's bottom edge and a 500px one
// scrolled it out of the section's box whole, with no cue left of the notice the follow-on exists to show (the arrivals
// review, 2026-09-09). The sheet now keeps a head whose only children past the toggles' row and the filter's are the
// line in the collapsed tier; a head grown by a real row (a refusal, the Track choice, the tooling warning) that also
// holds the line has a floor of the control row and the line's row together, and the line sticks to the section's
// bottom edge over the rows that scroll, as the Log toggle sticks to the top of its own scroller. The static leg holds
// the sheet to that shape (CI installs no browser); the browser legs mount the worktree's panel under styles.css's own
// rules in Chromium and Firefox, land a status with a session's reply and change, and measure the line's box against
// the section's at the review's heights: whole with the confirm up and with the composer open, the head scrolling
// nothing; whole and stuck to the bottom edge over a Track choice row, the head scrolling the rest. The same review
// found the marks' dot drawn on every line box of a wrapped mark; the last static test pins the sheet's account of that
// to the mechanism behind it. Skips LOUDLY without a playwright browser. Synthetic values only: invented prose,
// placeholder ids, the session name "api".
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8");
const BLOCK_A = "/* ── file comments panel (plans/file-review.md Slice 1; file-comments.ts)";
const BLOCK_B = "/* ── end file comments panel ── */";

/** The one rule whose head is `sel` in styles.css. */
function rule(sel: string): string {
  const m = new RegExp("\\n(" + sel.replace(/[.*+?^${}()|[\]\\]/g, "\\$&") + " \\{[^}]*\\})").exec(STYLES);
  assert.ok(m, "a rule for " + sel + " in styles.css");
  return m![1];
}
/** A selector list split at its top-level commas: the ones inside :has() and :not() belong to the selector. */
function splitSelectors(list: string): string[] {
  const out: string[] = []; let depth = 0, cur = "";
  for (const ch of list) {
    if (ch === "(") depth++; else if (ch === ")") depth--;
    if (ch === "," && depth === 0) { out.push(cur); cur = ""; } else cur += ch;
  }
  out.push(cur);
  return out.map((s) => s.replace(/\s+/g, " ").trim()).filter(Boolean);
}
/** The margin block's rules in source order, comments stripped: each as its selector list and its declarations. */
function marginRules(): Array<{ selectors: string[]; decls: Map<string, string> }> {
  const a = STYLES.indexOf(BLOCK_A), b = STYLES.indexOf(BLOCK_B);
  assert.ok(a >= 0 && b > a, "the file-comments block's markers");
  const start = STYLES.indexOf("\n.fc-panel.fc-margin {", a);
  assert.ok(start > a && start < b, "the margin rules follow the root rule inside the block");
  const text = STYLES.slice(start, b).replace(/\/\*[\s\S]*?\*\//g, "");
  const out: Array<{ selectors: string[]; decls: Map<string, string> }> = [];
  for (const m of text.matchAll(/([^{}]+?)\s*\{([^}]*)\}/g)) {
    const selectors = splitSelectors(m[1]);
    const decls = new Map<string, string>();
    for (const d of m[2].split(";")) { const i = d.indexOf(":"); if (i > 0) decls.set(d.slice(0, i).trim(), d.slice(i + 1).trim()); }
    out.push({ selectors, decls });
  }
  return out;
}
const GROWN_HEAD = ".fc-margin > .fc-sec-head:has(.fc-head > :nth-child(n+2):not(.fc-filter))";
const LINE_ONLY = ".fc-margin > .fc-sec-head:not(:has(.fc-head > :nth-child(n+2):not(.fc-filter, .fc-arrivals)))";
const GROWN_WITH_LINE = ".fc-margin > .fc-sec-head:has(.fc-head > :nth-child(n+2):not(.fc-filter, .fc-arrivals)):has(.fc-arrivals)";
const STICKY_LINE = ".fc-margin .fc-head > .fc-arrivals";

// ── the static leg ─────────────────────────────────────────────────────────────────────────────────

test("styles.css: a head whose only children past its control rows are the arrivals line stays in the collapsed tier — a rule after the grown tier's, at its specificity, with the grown tier's own selector left as the fit suite pins it", () => {
  const rules = marginRules();
  const grownAt = rules.findIndex((r) => r.selectors.includes(GROWN_HEAD) && r.decls.has("flex-shrink"));
  assert.ok(grownAt >= 0, "the grown tier's rule still keys on any head child past the toggles' row that is not the filter's (styles-fc-margin-fit.test.ts pins the text)");
  assert.ok(parseFloat(rules[grownAt].decls.get("flex-shrink")!) >= 1000, "and still shrinks first");
  const lineOnlyAt = rules.findIndex((r) => r.selectors.includes(LINE_ONLY));
  assert.ok(lineOnlyAt >= 0, "a rule for the head whose growth is the line alone: " + LINE_ONLY);
  assert.ok(lineOnlyAt > grownAt, "it follows the grown tier's rule: the two match the same section at the same specificity, and source order decides");
  const d = rules[lineOnlyAt].decls;
  assert.equal(d.get("flex-shrink"), "1", "back to the collapsed tier's shrink (flex 0 1 auto)");
  assert.equal(d.get("min-height"), "0", "and its floor");
  assert.deepEqual(rules[lineOnlyAt].selectors, [LINE_ONLY], "the rule stands alone: it is the head's exemption, not another section's");
});

test("styles.css: a head grown by a real row that also holds the line keeps a floor of the control row and the line's row together, and the line sticks to the bottom of the head's scroller, as the Log toggle sticks to the top of its", () => {
  const rules = marginRules();
  const floor = rules.find((r) => r.selectors.includes(GROWN_WITH_LINE));
  assert.ok(floor, "a floor rule for the grown head holding the line: " + GROWN_WITH_LINE);
  assert.equal(floor!.decls.get("min-height"), "min(15%, 4.4em)", "one control row (2.4em, the grown tier's floor) and the line's row (its 0.82em text and padding, and the head's gap): 15% caps it as the tier's floor is capped, so four grown sections and the track's 30% still fit");
  assert.ok(!floor!.decls.has("flex-shrink"), "the shrink is the grown tier's; this rule raises the floor only");
  assert.equal(rule(STICKY_LINE), STICKY_LINE + " { position: sticky; bottom: 0; background: var(--bg); }", "the line sticks to the section's bottom edge with the panel's background, over the rows that scroll under it");
  assert.equal(rule(".fc-margin .fc-log > .fc-sec"), ".fc-margin .fc-log > .fc-sec { position: sticky; top: 0; background: var(--bg); }", "the twin it mirrors: the Log toggle stuck to the top of the Log's scroller");
  assert.ok(STYLES.indexOf(STICKY_LINE + " {") < STYLES.indexOf(".fc-margin .fc-log > .fc-sec {"), "the line's rule stands with the head's fit rules, before the Log's");
});

test("styles.css: the marks' dot is one per LINE BOX of a wrapped mark, and the sheet says so — the marks paint each line box whole (box-decoration-break: clone, the ring per wrapped line), and the dot is a layer of that paint", () => {
  const a = STYLES.indexOf(BLOCK_A), b = STYLES.indexOf(BLOCK_B);
  const block = STYLES.slice(a, b);
  for (const sel of [".fc-hl", ".fc-ins"]) {
    const m = new RegExp("\\n" + sel.replace(".", "\\.") + " \\{([^}]*)\\}").exec(block);
    assert.ok(m, "the rule for " + sel);
    assert.match(m![1], /box-decoration-break: clone/, sel + " paints each of its line boxes whole — the ring around every wrapped line is the design, and the dot rides on the same paint");
  }
  const dot = /\n\.fc-hl\[data-new\], \.fc-ins\[data-new\], \.fc-del\[data-new\]::before \{([^}]*)\}/.exec(block);
  assert.ok(dot, "the data-new rule over the three marks");
  assert.match(dot![1], /background-image: radial-gradient/, "a background layer, so a dot coming off moves no layout under a pointer");
  assert.match(dot![1], /background-repeat: no-repeat;\s*background-position: top right/, "once per box it paints, at the top right");
  const comment = block.slice(block.indexOf("/* the arrivals notice"), block.indexOf("*/", block.indexOf("/* the arrivals notice")));
  assert.match(comment, /in the top right corner of each line box of a highlight/, "the comment says each line box, not one per mark: a mark that wraps wears a dot on every line, the Raw view's row slices one each");
  assert.doesNotMatch(comment, /and one in the top right corner of a highlight/, "the sentence that promised one dot per highlight was not true of a wrapped mark (the arrivals review, 2026-09-09)");
});

// ── the browser legs ─────────────────────────────────────────────────────────────────────────────

/** The panel's registry entry and marked, bundled as the webview build bundles them (in memory), as window.__romp. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { fileCommentsAction } from "./file-comments";\nimport { marked } from "marked";\n(window as any).__romp = { fileCommentsAction, marked };\n',
      resolveDir: UI, loader: "ts", sourcefile: "arrivals-line-fit-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
/** The sheet's rules the layout lives under: the viewer's card, body and prose, the buttons, and the whole file-comments block. */
function sheet(): string {
  const a = STYLES.indexOf(BLOCK_A), b = STYLES.indexOf(BLOCK_B);
  assert.ok(a >= 0 && b > a, "the file-comments block's markers in styles.css");
  return [rule(".fileview"), rule(".fileview-body"), rule(".fileview-md"), rule(".fileview-md p"), rule(".fileview-btn"), STYLES.slice(a, b)].join("\n");
}
const page = (height: number): string => `<!DOCTYPE html><html><head><meta charset=utf-8><style>
body { margin: 0; padding: 0; font: 14px/1.5 sans-serif; background: #1e1e1e; color: #ccc; --card-border: #444; --fg: #ccc; --dim: #999; --text-faint: #777; --text-muted: #888; --accent: #9cd2ff; --accent-fg: #0c1a2e; --accent-wash: rgba(156,210,255,0.15); --warn: #e0a030; --green: #7c7; --err: #e55; --bg: #1e1e1e; --overlay-05: rgba(255,255,255,0.05); --overlay-10: rgba(255,255,255,0.1); --radius-pill: 999px; --surface-raised: #252526; --shadow-menu: none; --box-border: #555; --input-bg: #111; }
${sheet()}
#wrap { width: 1000px; height: ${height}px; }</style></head><body><div class="fileview" id="wrap"><div class="fileview-main" id="main"><div class="fileview-body" id="body"><div class="fileview-md" id="md"></div></div></div></div><script src="/dist/arrivals-line-fit.js"></script></body></html>`;

// ── the document and its comments (synthetic prose) ────────────────────────────────────────────────
const SID = "11111111-2222-3333-4444-555555555555";
const ABS = "/repo/notes-api/docs/report.md";
const T0 = 1757145600000;
const PARA = (i: number): string => "Paragraph " + i + " of the report says something about the cache, the latency and the plan for the next release, in enough words to wrap onto a second line.";
const SRC = "# Report\n\n" + Array.from({ length: 30 }, (_, i) => PARA(i + 1)).join("\n\n") + "\n";
const COMMENT = { id: (T0 + 1) + "-6", author: "you", ts: T0 + 1, body: "Say which cache.", anchor: { quote: "Paragraph 2 of the report", prefix: "", suffix: " says something" }, replies: [], resolved: false };
const WORD = "Paragraph 25 of the report";
const WORD_AT = SRC.indexOf(WORD);
const REPLIED = { ...COMMENT, replies: [{ author: "api", authorId: SID, ts: T0 + 20000, body: "The query cache; the sentence says so now." }] };
const HUNK2 = { id: "h2", author: "api", ts: T0 + 21000, kind: "ins", curFrom: WORD_AT, curTo: WORD_AT + WORD.length, baseFrom: WORD_AT, baseTo: WORD_AT, oldText: "", newText: WORD, anchor: null };
type TrackedBy = { kind: string; entry: string } | null;
/** The first status: a tracked file with the person's one comment; `trackedBy` null for a file not tracked yet (the Track
 *  click then offers the file/folder choice, a real row of head growth). */
const first = (trackedBy: TrackedBy): Record<string, unknown> => ({
  verb: "status", root: "/repo/notes-api", storePath: "/repo/notes-api/.trackchanges/docs%2Freport.md.json",
  trackedBy, agentTooling: "present",
  fileMtimeNs: "1757145600000000001", storeMtimeNs: "1757145600000000002", configMtimeNs: "1757145600000000003",
  store: { v: 3, path: "docs/report.md", suggestions: [], comments: [COMMENT] },
  hunks: [], log: [],
  unsent: { comments: [COMMENT.id], replies: [], accepted: 0, rejected: 0, watermark: null },
});
/** The session's answer landing: a reply on the comment and a change far down the text. */
const arrived = (base: Record<string, unknown>): Record<string, unknown> => ({ ...base, store: { v: 3, path: "docs/report.md", suggestions: [{ id: "h2", authorId: SID }], comments: [REPLIED] }, hunks: [HUNK2], storeMtimeNs: "1757145600000000004" });

/** Mount the panel over the rendered document, answer its status asks with `status`, open it, and let the paint and the pass run. */
function mount(pg: any, status: Record<string, unknown>): Promise<void> {
  return pg.evaluate(async ([src, status, abs, sid]: [string, Record<string, unknown>, string, string]) => {
    const w = window as any;
    const body = document.getElementById("body")!, md = document.getElementById("md")!;
    md.innerHTML = w.__romp.marked.parse(src);
    const posted: any[] = []; w.__posted = posted;
    const rendered: Array<() => void> = [];
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
  }, [SRC, status, ABS, SID]);
}
/** A status landing as the viewer's own save makes one land: the onSaved hooks make the panel re-ask, and `status` answers. */
const land = (pg: any, status: Record<string, unknown>): Promise<void> => pg.evaluate(async (status: Record<string, unknown>) => {
  const w = window as any;
  for (const cb of w.__saved) cb({ mtimeNs: "1757145600000000001", logged: true });
  const last = w.__posted[w.__posted.length - 1];
  window.dispatchEvent(new MessageEvent("message", { data: { type: "fileCommentsResult", reqId: last.reqId, ...status } }));
  const settle = () => new Promise<void>((r) => setTimeout(r, 0));
  await settle(); await settle();
  await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
}, status);
const frames = (pg: any, n = 3): Promise<void> => pg.evaluate((n: number) => new Promise<void>((r) => { const step = (k: number) => (k ? requestAnimationFrame(() => step(k - 1)) : r()); step(n); }), n);
/** A click through the delegate (element.click(): no pointer press, so no gesture of the person's — the arrivals stand). */
const click = (pg: any, sel: string): Promise<void> => pg.evaluate((sel: string) => { (document.querySelector(sel) as HTMLElement).click(); }, sel);
type Box = { top: number; bottom: number; height: number };
type Scene = {
  margin: boolean; aside: Box; sec: Box; secScroll: number; secClient: number; shrink: number;
  line: (Box & { text: string }) | null; row: Box; log: Box; send: Box;
  confirm: boolean; choice: boolean; composerHidden: boolean; headKids: string[];
};
const scene = (pg: any): Promise<Scene> => pg.evaluate(() => {
  const aside = document.querySelector(".fileview-aside") as HTMLElement;
  const sec = aside.querySelector(".fc-sec-head") as HTMLElement;
  const line = aside.querySelector(".fc-head > .fc-arrivals") as HTMLElement | null;
  const box = (e: Element): { top: number; bottom: number; height: number } => { const r = e.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, height: r.height }; };
  const composer = aside.querySelector(".fc-composer") as HTMLElement | null;
  return {
    margin: aside.classList.contains("fc-margin"), aside: box(aside), sec: box(sec), secScroll: sec.scrollHeight, secClient: sec.clientHeight, shrink: parseFloat(getComputedStyle(sec).flexShrink),
    line: line ? { ...box(line), text: line.textContent || "" } : null, row: box(aside.querySelector(".fc-head > .fc-row")!), log: box(aside.querySelector('[data-act="fclog"]')!), send: box(aside.querySelector('[data-act="fcsend"], [data-act="fcsendgo"]')!),
    confirm: !!aside.querySelector(".fc-sec-send .fc-confirm"), choice: !!aside.querySelector(".fc-head > .fc-choice"), composerHidden: composer ? composer.hidden : true,
    headKids: Array.from((aside.querySelector(".fc-head") as HTMLElement).children).map((c) => c.className),
  };
});
const LINE = "api made 1 change and 1 reply since you last looked";
/** The line is whole inside the head section's box, and the footer's controls inside the aside's (nothing past its edge). */
function wholeAndInReach(s: Scene, where: string): void {
  assert.ok(s.margin, where + ": the margin layout is on");
  assert.ok(s.line, where + ": the line is under the header");
  assert.equal(s.line!.text, LINE, where);
  assert.ok(s.line!.top >= s.sec.top - 0.5 && s.line!.bottom <= s.sec.bottom + 0.5, where + ": the line is whole inside the head section's box: line " + JSON.stringify(s.line) + " in " + JSON.stringify(s.sec));
  assert.ok(s.log.bottom <= s.aside.bottom + 0.5 && s.send.bottom <= s.aside.bottom + 0.5, where + ": Send and the Log toggle are inside the aside");
}

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, name: string, height: number, body: (pg: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[name].launch(); }
  catch (e) { t.skip("no playwright " + name + " on this box — this leg needs it (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const js = bundle();
    const pg = await browser.newPage({ viewport: { width: 1100, height: 900 } });
    pg.on("pageerror", (e: Error) => { errors.push(e.message); });
    await pg.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: page(height) });
      if (u.pathname === "/dist/arrivals-line-fit.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      return route.fulfill({ status: 404, body: "" });
    });
    await pg.goto("http://romp.test/page");
    await pg.waitForFunction(() => !!(window as any).__romp);
    await body(pg);
    assert.deepEqual(errors, [], "no script error in the page");
  } finally { await browser.close(); }
}

for (const name of ["chromium", "firefox"]) {
  for (const height of [600, 500]) {
    test(`in ${name}, a ${height}px viewer: the line under the header with the Send confirm up — the head keeps the collapsed tier, scrolls nothing, and shows the line whole (before: cut at 600px, scrolled out whole at 500px)`, async (t) => {
      await inBrowser(t, name, height, async (pg) => {
        const base = first({ kind: "file", entry: "docs/report.md" });
        await mount(pg, base);
        let s = await scene(pg);
        assert.equal(s.line, null, "the first status: no line");
        assert.deepEqual(s.headKids, ["fc-row", "fc-row fc-filter"], "the head's two control rows");
        await land(pg, arrived(base));
        await click(pg, '[data-act="fcsend"]');
        await frames(pg);
        s = await scene(pg);
        assert.ok(s.confirm, "the Send confirm is up: the Send section is grown, and it gives");
        assert.deepEqual(s.headKids, ["fc-row", "fc-row fc-filter", "fc-sec fc-arrivals"], "the line is the head's third child, after the filter's row");
        assert.equal(s.shrink, 1, "the head is in the collapsed tier: the line is a control row, not growth (before: 1000000)");
        assert.ok(s.secScroll <= s.secClient + 1, "the head scrolls nothing inside itself: " + s.secScroll + " in " + s.secClient);
        wholeAndInReach(s, "confirm up");
      });
    });
  }

  test(`in ${name}, a 500px viewer: the line with the composer open — the composer gives, the head keeps its rows whole`, async (t) => {
    await inBrowser(t, name, 500, async (pg) => {
      const base = first({ kind: "file", entry: "docs/report.md" });
      await mount(pg, base);
      await land(pg, arrived(base));
      await click(pg, '[data-act="fcfile"]');
      await frames(pg);
      const s = await scene(pg);
      assert.equal(s.composerHidden, false, "the composer is showing");
      assert.equal(s.shrink, 1, "the head is in the collapsed tier");
      assert.ok(s.secScroll <= s.secClient + 1, "the head scrolls nothing inside itself: " + s.secScroll + " in " + s.secClient);
      wholeAndInReach(s, "composer open");
    });
  });

  for (const height of [600, 400]) {
    test(`in ${name}, a ${height}px viewer: a head grown by the Track choice row that also holds the line — the head gives to a floor of the control row and the line, scrolls the rest, and the line sticks whole to its bottom edge`, async (t) => {
      await inBrowser(t, name, height, async (pg) => {
        const base = first(null);                                  // not tracked yet: the Track click offers the file/folder choice
        await mount(pg, base);
        await land(pg, arrived(base));
        await click(pg, '[data-act="fctrack"]');
        await click(pg, '[data-act="fcsend"]');
        await frames(pg);
        const s = await scene(pg);
        assert.ok(s.choice && s.confirm, "the choice row stands in the head and the confirm in the Send section");
        assert.deepEqual(s.headKids, ["fc-row", "fc-row fc-choice", "fc-row fc-filter", "fc-sec fc-arrivals"], "the choice row under the toggles' row is real growth");
        assert.ok(s.shrink >= 1000, "the head is in the grown tier: " + s.shrink);
        assert.ok(s.secScroll > s.secClient + 1, "and scrolls inside itself: " + s.secScroll + " in " + s.secClient);
        wholeAndInReach(s, "grown head");
        assert.ok(Math.abs(s.line!.bottom - s.sec.bottom) <= 1, "the line is stuck to the section's bottom edge (before: at its natural place, below the box): " + s.line!.bottom + " vs " + s.sec.bottom);
        const floor = Math.min(0.15 * s.aside.height, 4.4 * 14);
        assert.ok(s.sec.height >= floor - 1, "the section is at least the raised floor: " + s.sec.height + " >= " + floor);
        assert.ok(s.row.top >= s.sec.top - 0.5 && s.row.top + 20 <= s.line!.top, "the toggles' row begins in view above the line: row " + JSON.stringify(s.row) + ", line " + JSON.stringify(s.line));
      });
    });
  }
}

test("vocabulary: this module's own prose says a change's old and new text, file comment and run of turns; the words CONTEXT.md sets aside appear nowhere in it, nor the banned sessions-pane word, nor a home path", () => {
  const SELF = fs.readFileSync(path.join(UI, "styles-fc-arrivals-line-fit.test.ts"), "utf8").split("\n").filter((l) => !l.includes("assert.doesNotMatch(SELF")).join("\n");
  assert.doesNotMatch(SELF, /\bdiffs?\b/i, "the folded part of a change card is the change's old and new text (CONTEXT.md, Change: Avoid)");
  assert.doesNotMatch(SELF, /\bthreads?\b/i, "a comment with replies is a file comment with a run of turns (CONTEXT.md, File comment: Avoid)");
  assert.doesNotMatch(SELF, /fleet/i, "no new identifiers or prose in the old word for the sessions pane");
  assert.doesNotMatch(SELF, /\/home\/[a-z]/, "no absolute home paths");
});

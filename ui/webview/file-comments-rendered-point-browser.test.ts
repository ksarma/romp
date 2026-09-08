// The Rendered view's struck deletion, under the real sheets in a real engine (the inline-display follow-on to
// plans/file-review.md, 2026-09-07). anchor-map.test.ts proves the DOM the painter builds; this leg proves what the
// sheets make of it, which no stand-in can: headless Chromium (and Firefox, when the box has it) loads styles.css
// and then feed.css — the chat page dresses the viewer with the one, the feed page with the other — over marked's
// rendering of a synthetic report, runs the worktree's own paintChangesRendered, and reads the layout:
//   • a point with a short label adds no line to its paragraph, and its label sits on the line of the word after it;
//   • the label is the sheet's generated content, struck, with the point's width being the label's — the point
//     itself holds no text, so the browser's selection never carries the struck words and mapRenderedSelection over
//     a selection that spans the point maps to the same source range as with no point;
//   • a long label wraps with the prose (an inline span, not an inline-block) — the paragraph grows, the box never
//     scrolls sideways;
//   • unpaint gives the markup back byte for byte.
// Skips, never fails, where playwright or an engine is missing (CI installs none). Synthetic fixtures only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { marked } from "marked";

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const SHEETS: Record<string, string> = { "styles.css": fs.readFileSync(path.join(UI, "styles.css"), "utf8"), "feed.css": fs.readFileSync(path.join(UI, "feed.css"), "utf8") };

marked.setOptions({ gfm: true, breaks: false });   // the viewer's configuration (pinned by anchor-map.test.ts)

// the notes-api report: three paragraphs after a heading, the changes a session made to it
const SOURCE = "# Report\n\nThe api session cut p95 latency by 40% and the p99 by 10%.\n\n"
  + "We recommend shipping the cache in v1.2.\n\nRisks remain in the fallback path, and the runbook covers them.\n";
const at = (s: string): number => { const i = SOURCE.indexOf(s); assert.ok(i >= 0, s); return i; };
const LONG_OLD = "the p50 and the p75 and the p90 and the p95 and the p99 and every other percentile we once reported here";
const CHANGES = [
  { id: "s1", kind: "sub", curFrom: at("cut"), curTo: at("cut") + 3, oldText: "reduced", newText: "cut", author: "api" },
  { id: "d1", kind: "del", curFrom: at("shipping"), curTo: at("shipping"), oldText: "quickly ", author: "api" },
  { id: "d2", kind: "del", curFrom: at("Risks remain") + "Risks remain".length, curTo: at("Risks remain") + "Risks remain".length, oldText: LONG_OLD, author: "web" },
];

/** The painter and the mapper, bundled as the webview build bundles them (in memory), handed to the page as window.__fc. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { paintChangesRendered, unpaintChanges, mapRenderedSelection, deletionLabel } from "./anchor-map";\n(window as any).__fc = { paintChangesRendered, unpaintChanges, mapRenderedSelection, deletionLabel };\n',
      resolveDir: UI, loader: "ts", sourcefile: "point-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the viewer's body at a narrow width, so a long label has to wrap (the sheet's @import and font urls 404 here, harmlessly).
// 420px: the column inside is the 384px the scenes were written against (420 less the root's 36px inset). The body reserves
// no scrollbar gutter (review round 2 of Slice 3 of plans/markdown-viewer.md took round 1's `scrollbar-gutter: stable` back
// out: it was a blank strip on every body that never scrolls, this one included, and the host stood at 435 to pay for it)
const PAGE = (html: string) => `<!DOCTYPE html><html><head><meta charset=utf-8><link rel=stylesheet href=/sheet.css>
<style>body{margin:0} #host{width:420px;margin:16px}</style></head>
<body><div id=host class=fileview-body><div id=box class=fileview-md>${html}</div></div><script src=/dist/probe.js></script></body></html>`;

type Probe = {
  errors: string[];
  heightsBefore: number[]; heightsAfter: number[]; heightsRestored: number[];
  painted: string[]; unpainted: string[];
  point: { display: string; width: number; height: number; top: number; text: string; content: string; strike: string; author: string } | null;
  wordTop: number | null; lineHeight: number;
  subOrder: string[] | null;
  longLabel: string | null; scrollWidth: number; clientWidth: number;
  selected: string | null; mapped: unknown; mappedClean: unknown;
  htmlBefore: string; htmlAfter: string;
};

async function probe(t: any, engine: "chromium" | "firefox", sheetName: string): Promise<void> {
  let pw: any = null;
  try { pw = requireCjs("playwright"); } catch { pw = null; }
  if (!pw) { t.skip("playwright is not installed under vscode-extension — the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw[engine].launch(); }
  catch (e) { t.skip(`no playwright ${engine} on this box — this leg needs it (CI installs none): ` + String((e as Error).message).split("\n")[0]); return; }
  try {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    const js = bundle();
    const html = marked.parse(SOURCE) as string;
    await page.route("http://romp.test/**", (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/page") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE(html) });
      if (u.pathname === "/dist/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: js });
      if (u.pathname === "/sheet.css") return route.fulfill({ status: 200, contentType: "text/css; charset=utf-8", body: SHEETS[sheetName] });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/page");
    const r: Probe = await page.evaluate(([source, changes]: [string, unknown[]]) => {
      const w = window as any;
      const box = document.getElementById("box")!;
      const paras = () => Array.from(box.children) as HTMLElement[];
      const heights = () => paras().map((p) => Math.round(p.getBoundingClientRect().height * 10) / 10);
      const htmlBefore = box.innerHTML;
      const heightsBefore = heights();
      // the selection over "We recommend shipping the cache", mapped with no point in the way
      const p1 = paras()[2];
      const selectSpan = (): Selection => {
        const range = document.createRange();
        const nodes: Text[] = [];
        const walk = (n: Node) => { if (n.nodeType === 3) nodes.push(n as Text); else n.childNodes.forEach(walk); };
        walk(p1);
        const first = nodes[0], last = nodes[nodes.length - 1];
        range.setStart(first, first.data.indexOf("We"));
        const endIn = last.data.indexOf("cache") + "cache".length;
        range.setEnd(last, endIn);
        const sel = window.getSelection()!;
        sel.removeAllRanges(); sel.addRange(range);
        return sel;
      };
      const mappedClean = w.__fc.mapRenderedSelection(selectSpan(), box, source);
      window.getSelection()!.removeAllRanges();
      const res = w.__fc.paintChangesRendered(box, source, changes, (c: { author: string }) => ({ "--fc-author": c.author === "api" ? "rgb(10, 20, 30)" : "rgb(40, 50, 60)" }));
      const heightsAfter = heights();
      const pt = box.querySelector('.fc-del[data-id="d1"]') as HTMLElement | null;
      let point: Probe["point"] = null, wordTop: number | null = null;
      if (pt) {
        const cs = getComputedStyle(pt), ps = getComputedStyle(pt, "::before");
        const b = pt.getBoundingClientRect();
        point = { display: cs.display, width: b.width, height: b.height, top: b.top, text: pt.textContent || "", content: ps.content, strike: ps.textDecorationLine, author: cs.borderBottomColor };
        // the word after the point: the first character of the text node that follows it
        const next = pt.nextSibling as Text | null;
        if (next && next.nodeType === 3) { const rg = document.createRange(); rg.setStart(next, 0); rg.setEnd(next, 1); wordTop = rg.getBoundingClientRect().top; }
      }
      const lineHeight = parseFloat(getComputedStyle(p1).lineHeight) || 0;
      const subPoint = box.querySelector('.fc-del[data-id="s1"]');
      const subOrder = subPoint ? [subPoint.className, (subPoint.nextSibling as Element | null)?.className || "?"] : null;
      const long = box.querySelector('.fc-del[data-id="d2"]') as HTMLElement | null;
      const longLabel = long ? getComputedStyle(long, "::before").content : null;
      // the selection spans the point now: the browser's own string of it, and the mapping
      const sel = selectSpan();
      const selected = sel.toString();
      const mapped = w.__fc.mapRenderedSelection(sel, box, source);
      sel.removeAllRanges();
      const scrollWidth = box.scrollWidth, clientWidth = box.clientWidth;
      w.__fc.unpaintChanges(box);
      return { errors: [], heightsBefore, heightsAfter, heightsRestored: heights(), painted: res.painted, unpainted: res.unpainted, point, wordTop, lineHeight, subOrder,
        longLabel, scrollWidth, clientWidth, selected, mapped, mappedClean, htmlBefore, htmlAfter: box.innerHTML };
    }, [SOURCE, CHANGES] as [string, unknown[]]);
    assert.deepEqual(errors, [], "no page errors");
    assert.deepEqual({ painted: r.painted, unpainted: r.unpainted }, { painted: ["s1", "d1", "d2"], unpainted: [] });
    assert.ok(r.point, "the deletion's point is in the body");
    const pt = r.point!;
    assert.equal(pt.display, "inline", "an inline span: the label flows with the words around it");
    assert.equal(pt.text, "", "the point holds no text of its own");
    if (engine === "chromium") assert.equal(pt.content, '"quickly "', "the label is the sheet's generated content from data-fc-text");
    assert.equal(pt.strike, "line-through", "struck");
    assert.ok(pt.width > 20, "the point's width is its label's: " + pt.width);
    assert.ok(pt.height <= r.lineHeight + 0.5, `the point sits within one line (${pt.height} of ${r.lineHeight})`);
    assert.ok(r.wordTop !== null && Math.abs(r.wordTop - pt.top) < 1, `the label shares its line with the word after it (${pt.top} vs ${r.wordTop})`);
    assert.equal(pt.author, "rgb(10, 20, 30)", "the author's colour rides --fc-author into the underline");
    // heights: the heading, the substitution's paragraph and the short deletion's keep their lines; the long label's grows
    assert.equal(r.heightsAfter[0], r.heightsBefore[0], "the heading is untouched");
    assert.equal(r.heightsAfter[1], r.heightsBefore[1], "a substitution's point and tint add no line");
    assert.equal(r.heightsAfter[2], r.heightsBefore[2], "a short struck label adds no line");
    assert.ok(r.heightsAfter[3] > r.heightsBefore[3], `a long label wraps with the prose, so its paragraph grows (${r.heightsBefore[3]} → ${r.heightsAfter[3]})`);
    assert.ok(r.scrollWidth <= r.clientWidth, `…and never widens the body sideways (${r.scrollWidth} in ${r.clientWidth})`);
    assert.deepEqual(r.subOrder, ["fc-del", "fc-ins"], "the substitution's point is the node right before its tint");
    if (engine === "chromium") assert.equal(r.longLabel, JSON.stringify(LONG_OLD.slice(0, 79) + "…"), "capped like Raw's, with the ellipsis");
    // the browser's selection across the point carries none of the struck words, and maps as it did before the paint
    assert.equal(r.selected, "We recommend shipping the cache", "the label is no text: the selection reads past it");
    assert.deepEqual(r.mapped, r.mappedClean, "the mapping over the painted body is the mapping over the clean one");
    assert.deepEqual(r.mapped, { ok: true, range: { start: at("We recommend"), end: at("cache") + 5 }, quote: "We recommend shipping the cache" });
    // unpaint: the lines and the markup are back
    assert.deepEqual(r.heightsRestored, r.heightsBefore);
    assert.equal(r.htmlAfter, r.htmlBefore, "the markup is what it was, byte for byte");
    await page.close();
  } finally { await browser.close(); }
}

for (const sheet of ["styles.css", "feed.css"]) {
  test(`in Chromium under ${sheet}: the struck deletion sits in its line, wraps with the prose, is no text to the selection, and unpaints clean`, async (t) => {
    await probe(t, "chromium", sheet);
  });
}
test("in Firefox under styles.css: the same — the layout is the spec's, not one engine's", async (t) => {
  await probe(t, "firefox", "styles.css");
});

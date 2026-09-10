// A Rendered deletion whose label has no visible character, under the real sheets in a real engine (the review of
// the inline-display follow-on, 2026-09-07). anchor-map-rendered-points.test.ts proves the DOM: the point carries
// `white-space: pre-wrap` when its label is spaces or tabs alone. This leg proves what the sheets make of it, which
// no stand-in can: headless Chromium (and Firefox, when the box has it) loads styles.css and then feed.css over
// marked's rendering of a synthetic report, runs the worktree's own paintChangesRendered, and reads the layout:
//   • a removed space beside a space that stayed (a doubled space a session collapsed) is a struck space with
//     width, under the author's underline, and the pointer finds it (elementFromPoint at its centre is the point);
//     the block's white-space alone collapsed it to a 0px point the card still called shown;
//   • a removed tab the same;
//   • a label with a visible character keeps the block's white-space (normal), the rule is that narrow;
//   • the paragraph keeps its lines, and unpaint gives the markup back byte for byte.
// Skips, never fails, where playwright or an engine is missing (CI installs none). Synthetic fixtures only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { marked } from "marked";
import { applyMdConfig } from "./md-config";   // the one markdown configuration, applied here as the viewer applies it

const requireCjs = createRequire(__filename);
const EXT = process.cwd();                                        // npm test runs in vscode-extension
const UI = path.resolve(EXT, "..", "ui", "webview");
const SHEETS: Record<string, string> = { "styles.css": fs.readFileSync(path.join(UI, "styles.css"), "utf8"), "feed.css": fs.readFileSync(path.join(UI, "feed.css"), "utf8") };

applyMdConfig();   // the viewer's configuration: the one every bundle applies (md-config.ts; pinned by anchor-map.test.ts)

// the notes-api report: a heading and one paragraph a copy-editing session tidied
// one line of prose with room beside it for the struck labels: the 80ch column of Slice 3 of plans/markdown-viewer.md holds
// about 95 characters of this prose at 15px, and a sentence that long wrapped onto a second line once the labels were added
const SOURCE = "# Report\n\nWe recommend shipping the cache. Risks remain in the fallback path.\n";
const at = (s: string): number => { const i = SOURCE.indexOf(s); assert.ok(i >= 0, s); return i; };
const CHANGES = [
  { id: "w-space", kind: "del", curFrom: at("Risks"), curTo: at("Risks"), oldText: " ", author: "api" },        // the second of a doubled space; the first stays
  { id: "w-tab", kind: "del", curFrom: at("fallback"), curTo: at("fallback"), oldText: "\t", author: "api" },
  { id: "v-word", kind: "del", curFrom: at("shipping"), curTo: at("shipping"), oldText: "quickly ", author: "web" },
];

/** The painter, bundled as the webview build bundles it (in memory), handed to the page as window.__fc. */
function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: {
      contents: 'import { paintChangesRendered, unpaintChanges } from "./anchor-map";\n(window as any).__fc = { paintChangesRendered, unpaintChanges };\n',
      resolveDir: UI, loader: "ts", sourcefile: "whitespace-probe.ts",
    },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
// the viewer's body, wide enough that the paragraph is one line: a struck space at a line's end would hang
// instead of sitting between its words, which is not the case under test (the sheet's @import and font urls 404 here, harmlessly)
const PAGE = (html: string) => `<!DOCTYPE html><html><head><meta charset=utf-8><link rel=stylesheet href=/sheet.css>
<style>body{margin:0} #host{width:840px;margin:16px}</style></head>
<body><div id=host class=fileview-body><div id=box class=fileview-md>${html}</div></div><script src=/dist/probe.js></script></body></html>`;

type PointProbe = { width: number; whiteSpace: string; content: string; strike: string; author: string; text: string; hit: "point" | "inside" | string };
type Probe = {
  painted: string[]; unpainted: string[];
  points: Record<string, PointProbe | null>;
  heightsBefore: number[]; heightsAfter: number[]; heightsRestored: number[];
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
      const heights = () => (Array.from(box.children) as HTMLElement[]).map((p) => Math.round(p.getBoundingClientRect().height * 10) / 10);
      const htmlBefore = box.innerHTML;
      const heightsBefore = heights();
      const res = w.__fc.paintChangesRendered(box, source, changes, (c: { author: string }) => ({ "--fc-author": c.author === "api" ? "rgb(10, 20, 30)" : "rgb(40, 50, 60)" }));
      const heightsAfter = heights();
      const points: Probe["points"] = {};
      for (const id of ["w-space", "w-tab", "v-word"]) {
        const pt = box.querySelector(`.fc-del[data-id="${id}"]`) as HTMLElement | null;
        if (!pt) { points[id] = null; continue; }
        const cs = getComputedStyle(pt), ps = getComputedStyle(pt, "::before");
        const b = pt.getBoundingClientRect();
        const hitEl = document.elementFromPoint(b.left + b.width / 2, b.top + b.height / 2);
        points[id] = {
          width: b.width, whiteSpace: cs.whiteSpace, content: ps.content, strike: ps.textDecorationLine, author: cs.borderBottomColor, text: pt.textContent || "",
          hit: hitEl === pt ? "point" : hitEl && pt.contains(hitEl) ? "inside" : hitEl ? hitEl.tagName + "." + hitEl.className : "nothing",
        };
      }
      w.__fc.unpaintChanges(box);
      return { painted: res.painted, unpainted: res.unpainted, points, heightsBefore, heightsAfter, heightsRestored: heights(), htmlBefore, htmlAfter: box.innerHTML };
    }, [SOURCE, CHANGES] as [string, unknown[]]);
    assert.deepEqual(errors, [], "no page errors");
    assert.deepEqual({ painted: r.painted, unpainted: r.unpainted }, { painted: ["w-space", "w-tab", "v-word"], unpainted: [] });
    const space = r.points["w-space"]!, tab = r.points["w-tab"]!, word = r.points["v-word"]!;
    assert.ok(space && tab && word, "the three points are in the body");
    // the removed space: the struck label has width beside the space that stayed, and the pointer lands on it (with
    // the block's white-space alone both were 0px: the layout claim first, its mechanism after)
    assert.ok(space.width > 1, "a struck space has width beside the space that stayed: " + space.width);
    assert.equal(space.hit, "point", "elementFromPoint at its centre is the point: it can be hovered and tapped");
    assert.equal(space.whiteSpace, "pre-wrap", "the point carries the rows' white-space");
    assert.equal(space.text, "", "the point holds no text of its own");
    if (engine === "chromium") assert.equal(space.content, '" "', "the label is the sheet's generated content: the space itself, no glyph");
    assert.equal(space.strike, "line-through", "struck");
    assert.equal(space.author, "rgb(10, 20, 30)", "the author's colour rides --fc-author into the underline");
    // the removed tab the same
    assert.ok(tab.width > 1, "a struck tab has width: " + tab.width);
    assert.equal(tab.hit, "point", "the tab's point is under the pointer too");
    assert.equal(tab.whiteSpace, "pre-wrap");
    // a visible label takes the block's white-space, as before: the rule is that narrow
    assert.equal(word.whiteSpace, "normal", "a label with a visible character inherits the block's white-space");
    assert.ok(word.width > 20, "…and is as wide as its words: " + word.width);
    // the paragraph keeps its lines, and the markup comes back
    assert.deepEqual(r.heightsAfter, r.heightsBefore, "no point adds a line");
    assert.deepEqual(r.heightsRestored, r.heightsBefore);
    assert.equal(r.htmlAfter, r.htmlBefore, "the markup is what it was, byte for byte");
    await page.close();
  } finally { await browser.close(); }
}

for (const sheet of ["styles.css", "feed.css"]) {
  test(`in Chromium under ${sheet}: a removed space or tab is a struck, underlined, hit-testable point in the Rendered view, not a 0px collapse`, async (t) => {
    await probe(t, "chromium", sheet);
  });
}
test("in Firefox under styles.css: the same — the layout is the spec's, not one engine's", async (t) => {
  await probe(t, "firefox", "styles.css");
});

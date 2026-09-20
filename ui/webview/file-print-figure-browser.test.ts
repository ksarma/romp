// The figure half of the printable rule over REAL elements in headless Chromium (file-print.ts figureHidden and
// figurePrintable; the print follow-on to plans/markdown-viewer.md's Slice 3, item 12), for what the round-3 review found
// (2026-09-20): the opacity read matched one spelling of zero by a pattern, so `-0`, `+0` and `0e0` counted a gated svg
// printable (its host named in the with-button's title and fetched by "Print with them" for a figure the browser paints
// nothing of) while `0.0.0`, which the browser refuses and paints at one, read as off the paper; and the placeholder's first
// element child alone was read, so `<picture><img hidden>` was counted and fetched. The flow now reads the COMPUTED
// visibility and opacity of each element that paints (the gate's sheet sets display none on the gated root and neither of
// those, so they compute on a gated figure as on the restored one), the author's own display through the browser's
// declaration parse (the sheet's display none is what makes the computed display unreadable), `hidden` and `popover` on HTML
// elements alone (the browser ignores both on an SVG element), and walks from each painting element up to the root. This
// leg builds every shape twice on one page: GATED, on a host the gear's list does not name, run through the real gate
// (figure-gate.ts gateRemoteFigures, on a parser document so no remote URL is ever live in the page) under the sheets' own
// gate rule, where the flow answers; and as an ungated TWIN at a local URL, where the browser answers for itself
// (checkVisibility with visibility and opacity read, and a client rect, over the twin's painting elements). It holds the
// flow's answer equal to the browser's for every shape, holds the named spellings of opacity, visibility and display to the
// answers the round named, and holds that no request reached a remote host. Two shapes the census of
// file-print-armed-browser.test.ts (D) turned up on the way (2026-09-20) are here too: an <audio> without `controls`, which the
// browser's own sheet hides, and a picture inside an <audio> or a <video>, fallback content a browser with the element never
// renders; before this both were counted, and the picture inside the audio fetched for a print that shows nothing of it.
// The round-4 review (2026-09-20) added two reads. (a) A second oracle keyed on the URL rather than the figure (extra8-2):
// after the reads above, every placeholder whose figure paints is restored the way "Print with them" restores it
// (loadGatedFigure, one placeholder at a time) and the remote URLs the page then asks for are held, per shape, equal to the
// table's `fetches`. The restore is the FIGURE's (figure-gate.ts), so a URL inside a non-painting element of a figure that
// paints is asked for too: the shapes with two painting elements on two hosts below measure that (an image at opacity zero
// beside one that paints, an image under <defs> beside one that paints, a group a sheet rule hides beside a painting
// image), and a figure that paints nothing has no URL asked for. What the browser fetches of a restored figure is its own
// (a <picture> fetches the <source> it picks and not the <img>'s src), so the column is measured, not derived. (b) Below the
// figure's root the flow reads the display the browser COMPUTES (extra8-3): a group hidden by a sheet rule on its class,
// which no attribute and no style declaration names, takes its image off the paper (FAILS BEFORE: the author's declaration
// read empty, and the figure was counted, its host named and fetched). Skips loudly without a browser. Synthetic values
// only: invented hosts under .test, a local /twin.svg and /twin2.svg.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { requireCjs, UI, inBrowser } from "./real-viewer-leg";
import { PAINTS_SEL } from "./file-print";

const ORIGIN = "http://figure.test";
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="black"/></svg>';
/** The one sheet rule the flow's display read depends on: it hides the gated root and sets neither visibility nor opacity. */
const GATE_RULE = '.fileview-md .fv-gate[data-act="fv-load"] > :not([data-fv-label]) { display: none; }';

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'export { figureHidden, figurePrintable, PAINTS_SEL } from "./file-print"; export { gateRemoteFigures, loadGatedFigure, GATE_ACT } from "./figure-gate";', resolveDir: UI, loader: "ts", sourcefile: "figure-leg.ts" },
    bundle: true, write: false, format: "iife", globalName: "FVF", platform: "browser", target: "es2020",
    nodePaths: [path.join(process.cwd(), "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}

/** `fetches`: which of the shape's URLs the browser asks for once the placeholder is restored as "Print with them" restores
 *  it ("a" the first, "b" the second), measured; absent, the first URL when the figure paints and none when it does not. */
type Shape = { name: string; html: (url: string, url2: string) => string; hidden?: boolean; paints: boolean; fetches?: string[] };
const svgOf = (attrs: string, inner: (url: string, url2: string) => string) => (url: string, url2: string): string => '<svg xmlns="http://www.w3.org/2000/svg" ' + attrs + ' width="8" height="8">' + inner(url, url2) + "</svg>";
const image = (attrs = "") => (url: string): string => '<image href="' + url + '" ' + attrs + ' width="8" height="8"/>';
/** The sheet rule of the leg's page that hides an author's class: what the computed display read below the root sees and
 *  the author's declaration does not. */
const HIDE_RULE = ".leg-hide { display: none; }";
/** Every shape: the spellings of opacity, visibility and display on a gated svg (`hidden`: the answer figureHidden must give
 *  for the root; `paints`: whether the browser paints the twin, which figurePrintable must match), the HTML attributes on
 *  HTML and SVG elements, the structures whose painting element is not the root, and the shapes with two painting elements
 *  on two hosts. */
function shapes(): Shape[] {
  const out: Shape[] = [];
  for (const [v, hidden] of [["0", true], ["-0", true], ["+0", true], ["0e0", true], ["0%", true], [" 0 ", true], ["-1", true], ["1e-100", true], ["calc(0)", true], [".0", true],
    ["0.0.0", false], ["0.", false], ["1e-9", false], ["50%", false], ["0.5", false], ["1", false], ["abc", false], ["", false]] as Array<[string, boolean]>) {
    out.push({ name: "opacity=" + JSON.stringify(v), html: svgOf('opacity="' + v + '"', image()), hidden, paints: !hidden });
  }
  for (const [v, hidden] of [["hidden", true], ["HIDDEN", true], [" collapse ", true], ["hidden /* c */", true], ["visible", false], ["bogus", false]] as Array<[string, boolean]>) {
    out.push({ name: "visibility=" + JSON.stringify(v), html: svgOf('visibility="' + v + '"', image()), hidden, paints: !hidden });
  }
  for (const [v, hidden] of [["none", true], ["NONE", true], [" none ", true], ["none /* c */", true], ["n\\6fne", true], ["contents", true], ["inline", false], ["bogus", false], ["block", false]] as Array<[string, boolean]>) {
    out.push({ name: "display=" + JSON.stringify(v), html: svgOf('display="' + v + '"', image()), hidden, paints: !hidden });
  }
  out.push({ name: "img", html: (u) => '<img src="' + u + '" width="8" height="8" alt="">', hidden: false, paints: true });
  out.push({ name: "img[hidden]", html: (u) => '<img hidden src="' + u + '" width="8" height="8" alt="">', hidden: true, paints: false });
  out.push({ name: "img[popover]", html: (u) => '<img popover src="' + u + '" width="8" height="8" alt="">', hidden: true, paints: false });
  out.push({ name: "svg[hidden]", html: svgOf("hidden", image()), hidden: false, paints: true });
  out.push({ name: "svg>image[hidden]", html: svgOf("", image("hidden")), hidden: false, paints: true });
  out.push({ name: "svg>image[popover]", html: svgOf("", image("popover")), hidden: false, paints: true });
  out.push({ name: "picture>img", html: (u) => '<picture><img src="' + u + '" width="8" height="8" alt=""></picture>', hidden: false, paints: true });
  out.push({ name: "picture>img[hidden]", html: (u) => '<picture><img hidden src="' + u + '" width="8" height="8" alt=""></picture>', hidden: false, paints: false });
  out.push({ name: "picture>source+img[hidden]", html: (u) => '<picture><source srcset="' + u + '" type="image/svg+xml"><img hidden src="' + u + '" width="8" height="8" alt=""></picture>', hidden: false, paints: false });
  out.push({ name: "picture[hidden]>img", html: (u) => '<picture hidden><img src="' + u + '" width="8" height="8" alt=""></picture>', hidden: true, paints: false });
  out.push({ name: "video[poster]", html: (u) => '<video poster="' + u + '" width="8" height="8"></video>', hidden: false, paints: true });
  out.push({ name: "video[hidden][poster]", html: (u) => '<video hidden poster="' + u + '" width="8" height="8"></video>', hidden: true, paints: false });
  out.push({ name: "video>img (fallback)", html: (u) => '<video width="8" height="8"><img src="' + u + '" width="8" height="8" alt=""></video>', hidden: false, paints: true });
  out.push({ name: "audio[controls][src]", html: (u) => '<audio controls src="' + u + '"></audio>', hidden: false, paints: true });
  out.push({ name: "audio[src]", html: (u) => '<audio src="' + u + '"></audio>', hidden: false, paints: false });
  out.push({ name: "audio>img (fallback)", html: (u) => '<audio><img src="' + u + '" width="8" height="8" alt=""></audio>', hidden: false, paints: false });
  out.push({ name: "img[hidden=until-found]", html: (u) => '<img hidden="until-found" src="' + u + '" width="8" height="8" alt="">', hidden: true, paints: false });
  // (an svg <title> or <desc> is an HTML integration point of the parser: an <image> inside becomes an HTML <img href>, which fetches nothing, so the gate wraps nothing there; neither is a shape)
  for (const c of ["defs", "symbol", "clipPath", "mask", "pattern", "marker", "metadata"]) out.push({ name: "svg>" + c + ">image", html: svgOf("", (u) => "<" + c + ">" + image()(u) + "</" + c + ">"), hidden: false, paints: false });
  for (const c of ["g", "a", "switch"]) out.push({ name: "svg>" + c + ">image", html: svgOf("", (u) => "<" + c + ">" + image()(u) + "</" + c + ">"), hidden: false, paints: true });
  out.push({ name: "svg>image[display=none]", html: svgOf("", image('display="none"')), hidden: false, paints: false });
  out.push({ name: "svg>image[display=contents]", html: svgOf("", image('display="contents"')), hidden: false, paints: false });
  out.push({ name: "svg>image[opacity=0]", html: svgOf("", image('opacity="0"')), hidden: false, paints: false });
  out.push({ name: "svg>image[visibility=hidden]", html: svgOf("", image('visibility="hidden"')), hidden: false, paints: false });
  out.push({ name: "svg[visibility=hidden]>image[visibility=visible]", html: svgOf('visibility="hidden"', image('visibility="visible"')), hidden: true, paints: true });
  out.push({ name: "svg[opacity=0]>image[opacity=1]", html: svgOf('opacity="0"', image('opacity="1"')), hidden: true, paints: false });
  out.push({ name: "svg[display=contents]>image", html: svgOf('display="contents"', image()), hidden: true, paints: false });
  out.push({ name: "svg>g[display=contents]>image", html: svgOf("", (u) => '<g display="contents">' + image()(u) + "</g>"), hidden: false, paints: true });
  for (const c of ["a", "switch"]) out.push({ name: "svg>" + c + "[display=contents]>image", html: svgOf("", (u) => "<" + c + ' display="contents">' + image()(u) + "</" + c + ">"), hidden: false, paints: false });
  out.push({ name: "svg>svg[display=contents]>image", html: svgOf("", (u) => '<svg display="contents" width="8" height="8">' + image()(u) + "</svg>"), hidden: false, paints: true });
  out.push({ name: "svg[fill=url]>rect", html: (u) => '<svg xmlns="http://www.w3.org/2000/svg" fill="url(' + u + '#p)" width="8" height="8"><rect width="8" height="8"/></svg>', hidden: false, paints: true });
  out.push({ name: "svg[fill=url]>defs>rect", html: (u) => '<svg xmlns="http://www.w3.org/2000/svg" fill="url(' + u + '#p)" width="8" height="8"><defs><rect width="8" height="8"/></defs></svg>', hidden: false, paints: false });
  out.push({ name: "svg[fill=url] empty", html: (u) => '<svg xmlns="http://www.w3.org/2000/svg" fill="url(' + u + '#p)" width="8" height="8"></svg>', hidden: false, paints: false });
  // the round-4 review's extra8-3: a group a sheet rule hides, which no attribute and no style names
  out.push({ name: "svg>g.leg-hide>image", html: svgOf("", (u) => '<g class="leg-hide">' + image()(u) + "</g>"), hidden: false, paints: false });
  // the round-4 review's extra8-2: two painting elements on two hosts; the restore is the figure's, so the URL of a
  // non-painting element beside a painting one is asked for too (the column below is what the browser does, measured)
  out.push({ name: "svg>image[a]+image[b]", html: svgOf("", (u, u2) => image()(u) + image()(u2)), hidden: false, paints: true, fetches: ["a", "b"] });
  out.push({ name: "svg>image[a]+image[b][opacity=0]", html: svgOf("", (u, u2) => image()(u) + image('opacity="0"')(u2)), hidden: false, paints: true, fetches: ["a", "b"] });
  out.push({ name: "svg>image[a]+defs>image[b]", html: svgOf("", (u, u2) => image()(u) + "<defs>" + image()(u2) + "</defs>"), hidden: false, paints: true, fetches: ["a", "b"] });
  out.push({ name: "svg>image[a][display=none]+image[b]", html: svgOf("", (u, u2) => image('display="none"')(u) + image()(u2)), hidden: false, paints: true, fetches: ["a", "b"] });
  out.push({ name: "svg>g.leg-hide>image[a]+image[b]", html: svgOf("", (u, u2) => '<g class="leg-hide">' + image()(u) + "</g>" + image()(u2)), hidden: false, paints: true, fetches: ["a", "b"] });
  out.push({ name: "svg[opacity=0]>image[a]+image[b]", html: svgOf('opacity="0"', (u, u2) => image()(u) + image()(u2)), hidden: true, paints: false, fetches: [] });
  out.push({ name: "picture>source[a]+img[b]", html: (u, u2) => '<picture><source srcset="' + u + '" type="image/svg+xml"><img src="' + u2 + '" width="8" height="8" alt=""></picture>', hidden: false, paints: true, fetches: ["a"] });
  out.push({ name: "video[poster=a]>img[b] (fallback)", html: (u, u2) => '<video poster="' + u + '" width="8" height="8"><img src="' + u2 + '" width="8" height="8" alt=""></video>', hidden: false, paints: true, fetches: ["a", "b"] });
  return out;
}
/** The URLs the restore is expected to have asked for, as the table says. */
const expectedFetches = (s: Shape): string[] => s.fetches ?? (s.paints ? ["a"] : []);

type Row = { name: string; gated: boolean; rootDisplay: string; rootOpacity: string; hidden: boolean | null; printable: boolean | null; twinPaints: boolean | null; remote: string };
type Read = { rows: Row[]; errors: string[] };
type Restored = { restored: boolean | null; printableAtRestore: boolean | null };

test("figureHidden and figurePrintable over real gated figures in Chromium: for every shape the flow's answer equals the browser's own answer for the shape's ungated twin (checkVisibility with visibility and opacity, and a client rect, over the twin's painting elements), a group hidden by a sheet rule on its class among them (FAILS BEFORE the round-4 review: the author's declaration read empty); the named spellings of opacity, visibility and display read as the round named (FAILS BEFORE: -0, +0, 0e0, -1 and calc(0) read on the paper, 0.0.0 off it; a hidden img inside a picture, an svg image inside defs, with display none or with opacity 0 counted; an <svg hidden> read as hidden where the browser paints it); the gate's sheet rule stands in both sheets and sets display none on the gated root alone; no remote host was asked", { timeout: 120000 }, async (t) => {
  for (const sheet of ["feed.css", "styles.css"]) assert.ok(fs.readFileSync(path.join(UI, sheet), "utf8").includes(GATE_RULE), sheet + " carries the gate rule the flow's display read depends on");
  await inBrowser(t, async (browser) => {
    const all = shapes();
    const hostOf = (i: number): string => "s" + i + ".remote.test";
    const hostOf2 = (i: number): string => "s" + i + "b.remote.test";
    const requests: string[] = [];
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("request", (r: any) => { requests.push(r.url()); });
    const js = bundle();
    const html = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>.fileview-md .fv-gate { display: inline-flex; min-width: 4em; min-height: 1em; }\n' + GATE_RULE + '\n' + HIDE_RULE + '\n.twin { display: inline-block; margin-left: 1em; }</style></head><body><div class="fileview-md" id="root"></div><script src="/leg.js"></script></body></html>';
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/leg.js") return route.fulfill({ status: 200, contentType: "text/javascript", body: js });
      if (u.pathname === "/twin.svg" || u.pathname === "/twin2.svg") return route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG });
      return route.fulfill({ status: 200, contentType: "text/html", body: html });
    });
    await page.route((u: URL) => u.hostname.endsWith(".remote.test"), (route: any) => route.fulfill({ status: 404, contentType: "text/plain", body: "never" }));
    await page.goto(ORIGIN + "/");
    const read: Read = await page.evaluate(async ([blocks, hosts, hosts2, paintsSel]: [string[], string[], string[], string]) => {
      const w = window as any;
      const errors: string[] = [];
      // the shapes on a parser document, so no remote URL is ever live in this page; the gate runs there, then the tree is adopted
      const src = new DOMParser().parseFromString("<!DOCTYPE html><html><body>" + blocks.map((b, i) => '<p data-shape="' + i + '">' + b.replace(/URL2/g, "https://" + hosts2[i] + "/q.svg").replace(/URL/g, "https://" + hosts[i] + "/p.svg") + '<span class="twin">' + b.replace(/URL2/g, "/twin2.svg").replace(/URL/g, "/twin.svg") + "</span></p>").join("") + "</body></html>", "text/html");
      w.FVF.gateRemoteFigures(src.body, location.href);
      const root = document.getElementById("root")!;
      for (const p of Array.from(src.body.children)) root.appendChild(document.adoptNode(p));
      // every twin picture loaded (or failed), so each has its box
      await Promise.all(Array.from(root.querySelectorAll(".twin img")).map((i) => (i as HTMLImageElement).complete ? null : new Promise<void>((r) => { i.addEventListener("load", () => r()); i.addEventListener("error", () => r()); })));
      await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
      const rows = blocks.map((_, i) => {
        const p = root.querySelector('p[data-shape="' + i + '"]')!;
        const g = p.querySelector('[data-act="' + w.FVF.GATE_ACT + '"]');
        const twin = p.querySelector(".twin")!;
        const twinRoot = twin.firstElementChild;
        const paints = [...(twinRoot && twinRoot.matches(paintsSel) ? [twinRoot] : []), ...Array.from(twin.querySelectorAll(paintsSel))];
        const shows = (e: Element): boolean => (e as any).checkVisibility({ visibilityProperty: true, opacityProperty: true }) && e.getClientRects().length > 0 && (getComputedStyle(e) as any).contentVisibility !== "hidden";   // content-visibility hidden (hidden=until-found) keeps the box and paints nothing of the element's content
        const fig = g ? g.firstElementChild : null;
        let hidden: boolean | null = null, printable: boolean | null = null;
        try { hidden = fig ? w.FVF.figureHidden(fig) : null; printable = g ? w.FVF.figurePrintable(g) : null; } catch (e) { errors.push(i + ": " + String(e)); }
        const cs = fig ? getComputedStyle(fig) : null;
        return { name: "", gated: !!g, rootDisplay: cs ? cs.display : "-", rootOpacity: cs ? cs.opacity : "-", hidden, printable, twinPaints: paints.length ? paints.some(shows) : false, remote: p.querySelector('[src^="https:"], [href^="https:"], [srcset*="https:"], [poster^="https:"], [fill*="https:"]') ? "live" : "moved" };
      });
      return { rows, errors };
    }, [all.map((s) => s.html("URL", "URL2")), all.map((_, i) => hostOf(i)), all.map((_, i) => hostOf2(i)), PAINTS_SEL]);
    assert.deepEqual(read.errors, [], "the flow's reads threw nothing");
    const rows = read.rows.map((r, i) => ({ ...r, name: all[i].name }));
    for (const r of rows) t.diagnostic("figure | " + r.name + " | gated=" + r.gated + " | root display=" + r.rootDisplay + " opacity=" + r.rootOpacity + " | figureHidden=" + r.hidden + " | figurePrintable=" + r.printable + " | twin paints=" + r.twinPaints);
    assert.deepEqual(rows.filter((r) => !r.gated).map((r) => r.name), [], "every shape was gated: its host is on no list, and the gate wraps the media root");
    assert.deepEqual(rows.filter((r) => r.remote !== "moved").map((r) => r.name), [], "every remote URL was moved aside by the gate before the tree entered the page");
    assert.deepEqual(rows.filter((r) => r.rootDisplay !== "none").map((r) => r.name), [], "the sheet's rule sets display none on every gated root");
    assert.deepEqual(rows.filter((r) => r.name.startsWith("opacity=") && r.hidden !== (Number(r.rootOpacity) === 0)).map((r) => r.name + " computed " + r.rootOpacity), [], "the sheet leaves opacity alone, and figureHidden reads the computed value: zero and only zero is hidden");
    // the flow's answer is the browser's answer for the twin, shape by shape
    const disagree = rows.filter((r) => r.printable !== r.twinPaints).map((r) => r.name + ": figurePrintable " + r.printable + ", the browser paints the twin " + r.twinPaints);
    assert.deepEqual(disagree, [], "FAILS BEFORE: figurePrintable disagreed with the browser on the zero spellings, on 0.0.0, on the hidden img inside a picture, on the svg image inside defs and on the hidden svg");
    // the named spellings and shapes, each to the answer the round named
    const wrong = rows.filter((r, i) => all[i].hidden !== undefined && r.hidden !== all[i].hidden).map((r, i) => r.name + ": figureHidden " + r.hidden);
    assert.deepEqual(wrong, [], "FAILS BEFORE: -0, +0, 0e0, -1 and calc(0) read as on the paper, 0.0.0 as off it, and <svg hidden> as hidden");
    const wrongPaper = rows.filter((r, i) => r.twinPaints !== all[i].paints).map((r, i) => r.name + ": the browser paints the twin " + r.twinPaints + ", the leg expected " + all[i].paints);
    assert.deepEqual(wrongPaper, [], "the browser's own answers are the ones this leg's table names (a change here is a change in the engine, and the flow follows it)");
    assert.deepEqual(requests.filter((u) => !u.startsWith(ORIGIN)), [], "no request left the origin before any restore: the gate moved every remote URL aside on the parser document");
    // the second oracle, keyed on the URL: every placeholder whose figure paints is restored as "Print with them" restores it,
    // and the remote URLs the page then asks for are read per shape against the table's `fetches`
    const before = requests.length;
    const restored: Restored[] = await page.evaluate((n: number) => {
      const w = window as any;
      const out: Restored[] = [];
      for (let i = 0; i < n; i++) {
        const g = document.querySelector('p[data-shape="' + i + '"] [data-act="' + w.FVF.GATE_ACT + '"]');
        const printable = g ? w.FVF.figurePrintable(g) as boolean : null;
        out.push({ printableAtRestore: printable, restored: printable === true && g ? w.FVF.loadGatedFigure(g) as boolean : null });
      }
      return out;
    }, all.length);
    for (let stable = 0; stable < 4; stable++) {   // the requests settle: four consecutive 250 ms windows with no new request (every .remote.test route answers at once)
      const n = requests.length;
      await new Promise((r) => setTimeout(r, 250));
      if (requests.length !== n) stable = -1;
    }
    const asked = requests.slice(before).filter((u) => !u.startsWith(ORIGIN));
    const fetchedOf = (i: number): string[] => { const a = asked.filter((u) => u === "https://" + hostOf(i) + "/p.svg").length, b = asked.filter((u) => u === "https://" + hostOf2(i) + "/q.svg").length; return [...(a ? ["a" + (a > 1 ? " x" + a : "")] : []), ...(b ? ["b" + (b > 1 ? " x" + b : "")] : [])]; };
    for (let i = 0; i < all.length; i++) t.diagnostic("fetch | " + all[i].name + " | printable=" + restored[i].printableAtRestore + " | restored=" + restored[i].restored + " | fetched=" + (fetchedOf(i).join(",") || "none") + " | expected=" + (expectedFetches(all[i]).join(",") || "none"));
    assert.deepEqual(restored.map((r, i) => [rows[i].name, r.printableAtRestore]).filter(([, p], i) => p !== rows[i].printable), [], "the restore read the same printable answer as the rows");
    assert.deepEqual(restored.filter((r) => r.printableAtRestore === true && r.restored !== true).map((_, i) => rows[i].name), [], "every placeholder whose figure paints was restored");
    const wrongFetch = all.map((s, i) => ({ name: s.name, got: fetchedOf(i), want: expectedFetches(s) })).filter((x) => x.got.join(",") !== x.want.join(",")).map((x) => x.name + ": asked for " + (x.got.join(",") || "none") + ", the table says " + (x.want.join(",") || "none"));
    assert.deepEqual(wrongFetch, [], "per URL: the restore of a figure that paints asks for every URL the browser fetches of the whole figure, a non-painting element's among them (the figure-level grant, stated in figure-gate.ts and file-print.ts), and a figure that paints nothing has no URL asked for");
    assert.deepEqual(asked.filter((u) => !/^https:\/\/s\d+b?\.remote\.test\/[pq]\.svg$/.test(u)), [], "no URL outside the shapes' own was asked for");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  });
});

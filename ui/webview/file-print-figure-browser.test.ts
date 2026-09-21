// The figure half of the printable rule over REAL elements in headless Chromium, Firefox and WebKit (file-print.ts
// figureHidden and figurePrintable; the print follow-on to plans/markdown-viewer.md's Slice 3, item 12), for what the round-3 review found
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
// read empty, and the figure was counted, its host named and fetched). The round-5 review (2026-09-20) ran the leg in the
// three engines (real-viewer-leg.ts inBrowser takes the engine; one case per engine below): the table's `paints` is one
// answer where the engines agree and each engine's own where they differ, because a row that pinned one engine's answer as
// every engine's would hold the flow to that engine's reading (the `svg>a[display=contents]>image` row: Firefox paints it,
// Chromium and WebKit do not). The round-7 fixes (2026-09-20, on the round-6 review's finding that the product's
// collectPictures read the divergent oracle) DEFINE the `paints` column as INK ON THE PAGE: a full-page screenshot of the
// leg's page, decoded in the page, with a pixel that is not white inside the twin's box, measured per row in each engine;
// never the twin oracle's reading (checkVisibility and a client rect) and never the flow's. Where the oracle reads other
// than the ink the row records that engine's reading (`twinReads`) and the oracle is held to it; where the FLOW answers
// other than the ink the row records that too (`flowReads`) with the reason, and the flow is held to the record, so the
// divergence stands at the row and a change in either direction reds it. A row whose ink cannot be measured says so on the
// row (`inkUnmeasured`, with the reason; the column is not asserted for it and its diagnostic line says so); today no row
// does. The oracle's divergences are pre-existing at the PR's base as platform readings (measured at the base, the fork's
// main the review reads this PR against, which has no file-print.ts, in the same three engines: Firefox and WebKit report a client rect for an element inside an SVG
// container that never renders its content, Firefox an empty one and WebKit a full one, with checkVisibility true, and
// every engine paints nothing there when nothing references the container; a pattern, mask or marker a printable element
// references by url(#id) paints through that element in every engine, the reference case per engine below) AND read by
// this PR's code: `rendered` is that oracle, and collectPictures read it
// alone for an svg <image> until the round-7 fixes, so in Firefox and WebKit the wait counted, awaited and probed the
// images inside such containers where Chromium skipped them; the collectPictures case per engine below pins the fix
// (FAILS BEFORE in Firefox and WebKit: eight pictures against Chromium's two). Figures with no remote URL have no row and
// nothing to label: the gate wraps a figure on an unlisted host alone (figure-gate.ts gateRemoteFigures), so an ungated
// figure never reaches figurePrintable in any engine. Skips loudly without a browser, engine by engine. Synthetic values
// only: invented hosts under .test, a local /twin.svg and /twin2.svg, and the collectPictures case's /pic-<container>.svg.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { requireCjs, UI, inBrowser, ENGINES, Engine } from "./real-viewer-leg";
import { PAINTS_SEL } from "./file-print";

const ORIGIN = "http://figure.test";
const SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="black"/></svg>';
/** The one sheet rule the flow's display read depends on: it hides the gated root and sets neither visibility nor opacity. */
const GATE_RULE = '.fileview-md .fv-gate[data-act="fv-load"] > :not([data-fv-label]) { display: none; }';

function bundle(): string {
  const esbuild = requireCjs("esbuild");
  const r = esbuild.buildSync({
    stdin: { contents: 'export { figureHidden, figurePrintable, collectPictures, rendered, printable, PAINTS_SEL } from "./file-print"; export { gateRemoteFigures, loadGatedFigure, GATE_ACT } from "./figure-gate"; export { sanitizeMd } from "./md-sanitize";', resolveDir: UI, loader: "ts", sourcefile: "figure-leg.ts" },
    bundle: true, write: false, format: "iife", globalName: "FVF", platform: "browser", target: "es2020",
    nodePaths: [path.join(process.cwd(), "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent",
  });
  return r.outputFiles[0].text as string;
}

/** `paints`: whether the shape's ungated twin puts INK on the page, one answer where the three engines agree, or each engine's
 *  own where they differ (a row naming one engine's answer as every engine's would pin that engine's reading as the truth,
 *  the round-5 review's correctness-2, 2026-09-20). Ink is measured (the round-7 fixes, 2026-09-20): a full-page screenshot
 *  decoded in the page, and a pixel inside the twin's box that is not white; the column is never the twin oracle's reading
 *  and never the flow's, each of which is recorded apart where it differs (twinReads, flowReads). `fetches`: which of the
 *  shape's URLs the browser asks for once the placeholder is restored as "Print with them" restores it ("a" the first, "b"
 *  the second), measured; absent, the first URL when the FLOW counts the figure (flowIn: the restore follows the flow's
 *  answer, not the ink) and none when it does not. */
type PerEngine = Record<Engine, boolean>;
/** `twinReads`: what the twin oracle (checkVisibility and a client rect over the twin's painting elements, `rendered` in the
 *  product) reads in an engine where that reading is NOT the ink: Firefox and WebKit report a client rect for an element
 *  inside an SVG container that never renders its content (Firefox an empty one, WebKit a full one) with checkVisibility
 *  true, and every engine paints nothing there when nothing references the container (the rows below carry no reference;
 *  a referenced pattern, mask or marker paints through its referrer, the reference case at the end of this file); every
 *  engine keeps opacity 1e-9 visible in checkVisibility and paints no
 *  visible pixel at it; and a rect whose paint server the page cannot resolve, and a video with no poster and no source,
 *  have a box and paint nothing. Pre-existing at the PR's base (the fork's main, which has no file-print.ts) as a platform
 *  reading in the same three engines, and read by this PR's code through `rendered` (the header). Where a row records it the oracle is
 *  held to the reading, so a change in the engine reds the row.
 *  `flowReads`: what the FLOW (figurePrintable) answers in an engine where that answer is NOT the ink, with the reason: the
 *  flow reads attributes and computed values and never the paint itself, so a figure whose painting element has a box and
 *  a nonzero computed opacity is counted whatever the page shows of it. Where a row records it the flow is held to the
 *  record, the divergence disclosed at the row; every other row holds the flow to the ink.
 *  `inkUnmeasured`: the reason a row's ink cannot be measured, stated on that row; the ink column is not asserted for it and
 *  its diagnostic line says so. No row carries it today: every twin is a box on one page, and the screenshot covers it. */
type Shape = { name: string; html: (url: string, url2: string) => string; hidden?: boolean | PerEngine; paints: boolean | PerEngine; fetches?: string[] | Record<Engine, string[]>; twinReads?: Partial<PerEngine>; flowReads?: { in: Partial<PerEngine>; why: string }; inkUnmeasured?: string };
/** The twin's ink the table names for `engine`. */
const paintsIn = (s: Shape, engine: Engine): boolean => typeof s.paints === "boolean" ? s.paints : s.paints[engine];
/** The root's figureHidden answer the table names for `engine`, or undefined where the row names none. */
const hiddenIn = (s: Shape, engine: Engine): boolean | undefined => typeof s.hidden === "object" ? s.hidden[engine] : s.hidden;
/** The twin oracle's reading the table expects in `engine`: the recorded one where the row carries it, the ink otherwise. */
const oracleReads = (s: Shape, engine: Engine): boolean => s.twinReads && s.twinReads[engine] !== undefined ? s.twinReads[engine]! : paintsIn(s, engine);
/** Whether the row records the oracle reading other than the ink in `engine`. */
const recorded = (s: Shape, engine: Engine): boolean => !!s.twinReads && s.twinReads[engine] !== undefined;
/** The flow's answer the table expects in `engine`: the recorded one where the row carries it (flowReads), the ink otherwise. */
const flowIn = (s: Shape, engine: Engine): boolean => s.flowReads && s.flowReads.in[engine] !== undefined ? s.flowReads.in[engine]! : paintsIn(s, engine);
/** Whether the row records the flow answering other than the ink in `engine`. */
const flowRecorded = (s: Shape, engine: Engine): boolean => !!s.flowReads && s.flowReads.in[engine] !== undefined;
const svgOf = (attrs: string, inner: (url: string, url2: string) => string) => (url: string, url2: string): string => '<svg xmlns="http://www.w3.org/2000/svg" ' + attrs + ' width="8" height="8">' + inner(url, url2) + "</svg>";
const image = (attrs = "") => (url: string): string => '<image href="' + url + '" ' + attrs + ' width="8" height="8"/>';
/** The sheet rule of the leg's page that hides an author's class: what the computed display read below the root sees and
 *  the author's declaration does not. */
const HIDE_RULE = ".leg-hide { display: none; }";
/** Every shape: the spellings of opacity, visibility and display on a gated svg (`hidden`: the answer figureHidden must give
 *  for the root; `paints`: the ink the twin puts on the page; both columns, and where the oracle or the flow is recorded as
 *  reading other than the ink, are documented at the Shape type above), the HTML attributes on
 *  HTML and SVG elements, the structures whose painting element is not the root, and the shapes with two painting elements
 *  on two hosts. */
function shapes(): Shape[] {
  const out: Shape[] = [];
  for (const [v, hidden] of [["0", true], ["-0", true], ["+0", true], ["0e0", true], ["0%", true], [" 0 ", true], ["-1", true], ["1e-100", true], ["calc(0)", true], [".0", true],
    ["0.0.0", false], ["0.", false], ["50%", false], ["0.5", false], ["1", false], ["abc", false], ["", false]] as Array<[string, boolean]>) {
    out.push({ name: "opacity=" + JSON.stringify(v), html: svgOf('opacity="' + v + '"', image()), hidden, paints: !hidden });
  }
  // opacity 1e-9 is the engine's own computed value, which the flow reads: Chromium and Firefox keep it (1e-09, 1e-9) and
  // WebKit computes it to 0, so the flow reads the figure off the paper in WebKit alone; no engine puts a pixel that is not
  // white on the page at that opacity (the ink column), and every engine's checkVisibility keeps it (twinReads)
  out.push({ name: 'opacity="1e-9"', html: svgOf('opacity="1e-9"', image()), hidden: { chromium: false, firefox: false, webkit: true }, paints: false, twinReads: { chromium: true, firefox: true, webkit: true }, flowReads: { in: { chromium: true, firefox: true }, why: "the flow reads the computed opacity and counts any nonzero value as on the paper; Chromium and Firefox compute 1e-9 as nonzero, and the page shows no pixel of it" } });
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
  // a video with no poster and no source inks nothing in any engine; the flow reads a video as painting of itself (PAINTING_ROOTS,
  // reading no source), so it counts the figure and the restore fetches the fallback image's URL (the fetches column)
  out.push({ name: "video>img (fallback)", html: (u) => '<video width="8" height="8"><img src="' + u + '" width="8" height="8" alt=""></video>', hidden: false, paints: false, twinReads: { chromium: true, firefox: true, webkit: true }, flowReads: { in: { chromium: true, firefox: true, webkit: true }, why: "the flow reads a video as painting of itself whatever it holds, and a video with no poster and no source inks nothing" } });
  out.push({ name: "audio[controls][src]", html: (u) => '<audio controls src="' + u + '"></audio>', hidden: false, paints: true, fetches: { chromium: ["a"], firefox: ["a"], webkit: ["a x2"] } });
  out.push({ name: "audio[src]", html: (u) => '<audio src="' + u + '"></audio>', hidden: false, paints: false });
  out.push({ name: "audio>img (fallback)", html: (u) => '<audio><img src="' + u + '" width="8" height="8" alt=""></audio>', hidden: false, paints: false });
  out.push({ name: "img[hidden=until-found]", html: (u) => '<img hidden="until-found" src="' + u + '" width="8" height="8" alt="">', hidden: true, paints: false });
  // (an svg <title> or <desc> is an HTML integration point of the parser: an <image> inside becomes an HTML <img href>, which fetches nothing, so the gate wraps nothing there; neither is a shape)
  // an image inside a container that never renders its content, referenced by nothing (these rows carry no reference; a
  // referenced pattern, mask or marker paints through its referrer, the reference case at the end of this file), paints
  // nothing in any engine; Firefox and WebKit report a client rect for it all the same (metadata excepted: its content is
  // not laid out there), the reading twinReads records
  for (const c of ["defs", "symbol", "clipPath", "mask", "pattern", "marker"]) out.push({ name: "svg>" + c + ">image", html: svgOf("", (u) => "<" + c + ">" + image()(u) + "</" + c + ">"), hidden: false, paints: false, twinReads: { firefox: true, webkit: true } });
  out.push({ name: "svg>metadata>image", html: svgOf("", (u) => "<metadata>" + image()(u) + "</metadata>"), hidden: false, paints: false });
  for (const c of ["g", "a", "switch"]) out.push({ name: "svg>" + c + ">image", html: svgOf("", (u) => "<" + c + ">" + image()(u) + "</" + c + ">"), hidden: false, paints: true });
  out.push({ name: "svg>image[display=none]", html: svgOf("", image('display="none"')), hidden: false, paints: false });
  out.push({ name: "svg>image[display=contents]", html: svgOf("", image('display="contents"')), hidden: false, paints: false });
  out.push({ name: "svg>image[opacity=0]", html: svgOf("", image('opacity="0"')), hidden: false, paints: false });
  out.push({ name: "svg>image[visibility=hidden]", html: svgOf("", image('visibility="hidden"')), hidden: false, paints: false });
  // a visible image inside an svg ROOT whose visibility is hidden: Chromium and Firefox paint it, WebKit paints nothing of it
  // (a visible image inside a hidden GROUP paints in all three); every engine computes the image's visibility as visible,
  // which the flow reads and the oracle's checkVisibility reads too
  out.push({ name: "svg[visibility=hidden]>image[visibility=visible]", html: svgOf('visibility="hidden"', image('visibility="visible"')), hidden: true, paints: { chromium: true, firefox: true, webkit: false }, twinReads: { webkit: true }, flowReads: { in: { webkit: true }, why: "the flow reads the image's computed visibility, visible in every engine; WebKit paints nothing of a visible child of an svg root whose visibility is hidden" } });
  out.push({ name: "svg[opacity=0]>image[opacity=1]", html: svgOf('opacity="0"', image('opacity="1"')), hidden: true, paints: false });
  out.push({ name: "svg[display=contents]>image", html: svgOf('display="contents"', image()), hidden: true, paints: false });
  out.push({ name: "svg>g[display=contents]>image", html: svgOf("", (u) => '<g display="contents">' + image()(u) + "</g>"), hidden: false, paints: true });
  // the round-5 review's correctness-2 (2026-09-20): on a link the engines differ. Chromium and WebKit compute the author's
  // `contents` to none and paint nothing; Firefox keeps it and paints the image inside (FAILS BEFORE in Firefox: the flow
  // read the link off the paper by the authored table, its placeholder not counted while the print showed the picture)
  out.push({ name: "svg>a[display=contents]>image", html: svgOf("", (u) => '<a display="contents">' + image()(u) + "</a>"), hidden: false, paints: { chromium: false, firefox: true, webkit: false } });
  out.push({ name: "svg>switch[display=contents]>image", html: svgOf("", (u) => '<switch display="contents">' + image()(u) + "</switch>"), hidden: false, paints: false });
  out.push({ name: "svg>svg[display=contents]>image", html: svgOf("", (u) => '<svg display="contents" width="8" height="8">' + image()(u) + "</svg>"), hidden: false, paints: true });
  // a paint server on another host: Chromium asks for it on the restore, Firefox and WebKit do not (what the browser fetches of
  // a restored figure is its own; the column is measured per engine). The twin's server is the local twin.svg, which has no
  // `p` fragment, so the rect inks nothing in any engine; the flow reads a rect as painting of itself and never resolves its
  // paint server, so it counts the figure (flowReads), and the twin oracle reads the rect's box (twinReads)
  out.push({ name: "svg[fill=url]>rect", html: (u) => '<svg xmlns="http://www.w3.org/2000/svg" fill="url(' + u + '#p)" width="8" height="8"><rect width="8" height="8"/></svg>', hidden: false, paints: false, twinReads: { chromium: true, firefox: true, webkit: true }, flowReads: { in: { chromium: true, firefox: true, webkit: true }, why: "the flow reads a rect as painting of itself and never resolves its paint server; a server the page cannot resolve fills nothing" }, fetches: { chromium: ["a"], firefox: [], webkit: [] } });
  out.push({ name: "svg[fill=url]>defs>rect", html: (u) => '<svg xmlns="http://www.w3.org/2000/svg" fill="url(' + u + '#p)" width="8" height="8"><defs><rect width="8" height="8"/></defs></svg>', hidden: false, paints: false, twinReads: { firefox: true, webkit: true } });
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
/** The URLs the restore is expected to have asked for in `engine`, as the table says: the row's list, one per engine where
 *  the engines differ in what they fetch of a restored figure (a paint server named by `fill="url(...)"`, which Firefox and
 *  WebKit do not ask for on the restore where Chromium does; an audio's src, which WebKit asks for twice), the first URL
 *  when the FLOW counts the figure (flowIn: the restore is keyed on figurePrintable, so a row the flow counts and the page
 *  inks nothing of is restored and fetched) and none when it does not otherwise. */
const expectedFetches = (s: Shape, engine: Engine): string[] => s.fetches === undefined ? (flowIn(s, engine) ? ["a"] : []) : Array.isArray(s.fetches) ? s.fetches : s.fetches[engine];
/** Whether a request URL is the page's own: the origin, or a blob URL the page minted (WebKit reports its own audio controls'
 *  glyphs as `blob:` requests of the page's origin, eleven per `<audio controls>`; a blob URL is the page's memory, no host). */
const ofOrigin = (u: string): boolean => u.startsWith(ORIGIN) || u.startsWith("blob:" + ORIGIN);

type Row = { name: string; gated: boolean; rootDisplay: string; rootOpacity: string; hidden: boolean | null; printable: boolean | null; twinPaints: boolean | null; remote: string; overlap: string };
/** The ink measured inside a twin's box: the count of pixels that are not white, and the box's size in the screenshot. */
type Ink = { pixels: number; width: number; height: number };
/** The shapes whose measured twin ORACLE reading disagrees with the table, each named with ITS OWN expected value: the expectation travels
 *  with its row through the filter. The round-4 review (2026-09-20): before this the leg filtered by the row's index and then
 *  mapped by the POST-FILTER index, so when it reddened the message named another shape's expected value, misleading exactly
 *  when it fired; the node case below executes both forms over three rows. */
function paperMismatches(rows: Array<{ name: string; twinPaints: boolean | null }>, expected: boolean[]): string[] {
  return rows.map((r, i) => ({ r, want: expected[i] })).filter((x) => x.r.twinPaints !== x.want).map((x) => x.r.name + ": the browser paints the twin " + x.r.twinPaints + ", the leg expected " + x.want);
}

test("paperMismatches names each disagreeing shape with its own expected value; the form before it (filter by the row's index, map by the post-filter index) named the third shape with the second's expected value, a message saying the leg expected what the browser painted", () => {
  const rows = [{ name: "first", twinPaints: true }, { name: "second", twinPaints: false }, { name: "third", twinPaints: true }];
  const expected = [true, true, false];
  assert.deepEqual(paperMismatches(rows, expected), ["second: the browser paints the twin false, the leg expected true", "third: the browser paints the twin true, the leg expected false"], "each row with its own expectation");
  assert.deepEqual(paperMismatches(rows, [true, false, true]), [], "no disagreement, no message");
  const before = rows.filter((r, i) => r.twinPaints !== expected[i]).map((r, i) => r.name + ": the browser paints the twin " + r.twinPaints + ", the leg expected " + expected[i]);
  assert.deepEqual(before, ["second: the browser paints the twin false, the leg expected true", "third: the browser paints the twin true, the leg expected true"], "FAILS BEFORE, kept as the record of the defect: the old form named the third shape with expected[1], the second's value, so its message claimed a disagreement between equal values");
});
/** The names of the rows `holds` picks, each with the row's own values beside it, so a red names the shape that failed and
 *  shows what it read: `names[i]` is `rows[i]`'s, and the row travels with its name through the filter. The round-5 review
 *  (2026-09-20, correctness-3): the restore assert below filtered the rows and then indexed the unfiltered table by the
 *  POST-FILTER index, so a red named another shape (row 0 never has a figure to restore, so every red named the first
 *  shape); the node case below executes the old form and this one over three rows, and the record test's census over the
 *  print test modules refuses every filter-then-map-by-index chain but the two fails-before records. */
function namesWhere<T>(rows: readonly T[], names: readonly string[], holds: (row: T) => boolean): string[] {
  return rows.map((r, i) => ({ r, name: names[i] })).filter((x) => holds(x.r)).map((x) => x.name + " " + JSON.stringify(x.r));
}

test("namesWhere names each row the predicate holds by its own name with the row's values; the form before it (filter, then map by the post-filter index into the unfiltered names) named the first shape whichever row failed", () => {
  const restored = [{ printableAtRestore: false, restored: null }, { printableAtRestore: true, restored: true }, { printableAtRestore: true, restored: false }];
  const names = ["first", "second", "third"];
  const holds = (r: { printableAtRestore: boolean | null; restored: boolean | null }): boolean => r.printableAtRestore === true && r.restored !== true;
  assert.deepEqual(namesWhere(restored, names, holds), ['third {"printableAtRestore":true,"restored":false}'], "the third row failed, and the message names the third with what it read");
  assert.deepEqual(namesWhere(restored, names, () => false), [], "nothing held, no message");
  const before = restored.filter(holds).map((_, i) => names[i]);
  assert.deepEqual(before, ["first"], "FAILS BEFORE, kept as the record of the defect: the old form named the first shape, which has no figure to restore, for the third's failure");
});
type Read = { rows: Row[]; errors: string[] };
type Restored = { restored: boolean | null; printableAtRestore: boolean | null };

for (const engine of ENGINES) test("figureHidden and figurePrintable over real gated figures in " + engine + ": for every shape the flow's answer equals the INK the shape's ungated twin puts on the page (a full-page screenshot decoded in the page, measured per row; the round-7 fixes) or the row's recorded flow reading where it differs, and the twin oracle (checkVisibility with visibility and opacity, and a client rect, over the twin's painting elements) equals the ink or the row's recorded oracle reading, a group hidden by a sheet rule on its class among them (FAILS BEFORE the round-4 review: the author's declaration read empty); the named spellings of opacity, visibility and display read as the round named (FAILS BEFORE: -0, +0, 0e0, -1 and calc(0) read on the paper, 0.0.0 off it; a hidden img inside a picture, an svg image inside defs, with display none or with opacity 0 counted; an <svg hidden> read as hidden where the browser paints it); the gate's sheet rule stands in both sheets and sets display none on the gated root alone; no remote host was asked", { timeout: 120000 }, async (t) => {
  for (const sheet of ["feed.css", "styles.css"]) assert.ok(fs.readFileSync(path.join(UI, sheet), "utf8").includes(GATE_RULE), sheet + " carries the gate rule the flow's display read depends on");
  await inBrowser(t, async (browser) => {
    const all = shapes();
    const hostOf = (i: number): string => "s" + i + ".remote.test";
    const hostOf2 = (i: number): string => "s" + i + "b.remote.test";
    const requests: string[] = [];
    const page = await browser.newPage({ viewport: { width: 1200, height: 700 } });   // wide enough for a twin at 40em plus an audio's controls, so the page never scrolls sideways and the shot is the viewport's width
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("request", (r: any) => { requests.push(r.url()); });
    const js = bundle();
    const html = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>.fileview-md .fv-gate { display: inline-flex; min-width: 4em; min-height: 1em; }\n' + GATE_RULE + '\n' + HIDE_RULE + '\n.fileview-md p { position: relative; }\n.twin { position: absolute; left: 40em; top: 0; }</style></head><body><div class="fileview-md" id="root"></div><script src="/leg.js"></script></body></html>';
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
        // the ink read's ground: no element of the row outside the twin lays out over the twin's box (the gated placeholder's
        // label runs past its 8px-wide inline-flex box in Firefox and WebKit, and under the twin when the twin sat 1em after it)
        const box = twin.getBoundingClientRect();
        const meets = (r: DOMRect): boolean => r.width > 0 && r.height > 0 && box.width > 0 && box.height > 0 && r.left < box.right && r.right > box.left && r.top < box.bottom && r.bottom > box.top;
        const overlap = Array.from(p.querySelectorAll("*")).filter((e) => e !== twin && !twin.contains(e) && meets(e.getBoundingClientRect())).map((e) => e.tagName.toLowerCase() + (e.className ? "." + String(e.className).split(" ")[0] : "")).join(",");
        return { name: "", gated: !!g, rootDisplay: cs ? cs.display : "-", rootOpacity: cs ? cs.opacity : "-", hidden, printable, twinPaints: paints.length ? paints.some(shows) : false, remote: p.querySelector('[src^="https:"], [href^="https:"], [srcset*="https:"], [poster^="https:"], [fill*="https:"]') ? "live" : "moved", overlap };
      });
      return { rows, errors };
    }, [all.map((s) => s.html("URL", "URL2")), all.map((_, i) => hostOf(i)), all.map((_, i) => hostOf2(i)), PAINTS_SEL]);
    assert.deepEqual(read.errors, [], "the flow's reads threw nothing");
    const rows = read.rows.map((r, i) => ({ ...r, name: all[i].name }));
    // the ink: one full-page screenshot, decoded in the page onto a canvas, and the pixels inside each twin's box that are
    // not white counted (the twin sits on the page's white background with nothing else in its box)
    const shot: Buffer = await page.screenshot({ fullPage: true });
    const inks: Ink[] = await page.evaluate(async ([png, n]: [string, number]) => {
      const img = new Image();
      img.src = "data:image/png;base64," + png;
      await img.decode();
      const canvas = document.createElement("canvas");
      canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
      const ctx = canvas.getContext("2d")!;
      ctx.drawImage(img, 0, 0);
      const scale = window.devicePixelRatio;   // device pixels per CSS pixel in the shot (the page's own ratio; the screenshot is viewport-wide, so its width over the document's clientWidth would be off by a scrollbar in Firefox and WebKit)
      const out: Ink[] = [{ pixels: -1, width: img.naturalWidth, height: img.naturalHeight }];   // the shot's own size first, for the diagnostic
      out.push({ pixels: -1, width: Math.round(window.innerWidth * scale), height: Math.round(document.documentElement.scrollHeight * scale) });
      for (let i = 0; i < n; i++) {
        const r = document.querySelector('p[data-shape="' + i + '"] .twin')!.getBoundingClientRect();
        const x = Math.floor((r.left + window.scrollX) * scale), y = Math.floor((r.top + window.scrollY) * scale);
        const width = Math.ceil(r.width * scale), height = Math.ceil(r.height * scale);
        let pixels = 0;
        if (width > 0 && height > 0) {
          const d = ctx.getImageData(x, y, width, height).data;
          for (let k = 0; k < d.length; k += 4) if (d[k] < 250 || d[k + 1] < 250 || d[k + 2] < 250) pixels++;
        }
        out.push({ pixels, width, height });
      }
      return out;
    }, [shot.toString("base64"), all.length]);
    const [shotSize, pageSize] = inks.splice(0, 2);
    t.diagnostic("ink | " + engine + " | shot " + shotSize.width + "x" + shotSize.height + " px | page " + pageSize.width + "x" + pageSize.height + " px at the page's pixel ratio");
    assert.equal(inks.length, all.length, "one ink reading per row");
    assert.deepEqual(rows.filter((r) => r.overlap).map((r) => r.name + ": " + r.overlap), [], "no element of a row outside its twin lays out over the twin's box, so the ink inside the box is the twin's alone (the placeholder's label overflowed under the twin in Firefox and WebKit when the twin followed it in flow; each twin now stands at a fixed offset from the row's left edge)");
    assert.ok(shotSize.width === pageSize.width && shotSize.height >= pageSize.height - 1, "the shot is the whole page at the page's pixel ratio, so a twin's box maps onto it without scaling beyond that ratio (shot " + shotSize.width + "x" + shotSize.height + ", page " + pageSize.width + "x" + pageSize.height + ")");
    const inkOf = (i: number): boolean | null => all[i].inkUnmeasured ? null : inks[i].pixels > 0;
    for (const [i, r] of rows.entries()) t.diagnostic("figure | " + engine + " | " + r.name + " | gated=" + r.gated + " | root display=" + r.rootDisplay + " opacity=" + r.rootOpacity + " | figureHidden=" + r.hidden + " | figurePrintable=" + r.printable + (flowRecorded(all[i], engine) ? " (recorded: " + all[i].flowReads!.why + ")" : "") + " | twin oracle=" + r.twinPaints + (recorded(all[i], engine) ? " (recorded)" : "") + " | ink=" + (all[i].inkUnmeasured ? "unmeasured: " + all[i].inkUnmeasured : inks[i].pixels + " of " + inks[i].width + "x" + inks[i].height + " px"));
    assert.ok(inks.some((k) => k.pixels > 0) && inks.some((k) => k.pixels === 0 && k.width > 0), "the ink read tells rows apart: some twin box inks and some sized box does not (a screenshot that missed the page would read every row alike)");
    // the paints column IS the ink: for every row whose ink is measurable, the table's paints is whether the twin's box holds a pixel that is not white
    const wrongInk = rows.map((r, i) => ({ r, s: all[i], ink: inkOf(i) })).filter((x) => x.ink !== null && x.ink !== paintsIn(x.s, engine)).map((x) => x.r.name + ": the twin inks " + x.ink + " (" + inks[all.indexOf(x.s)].pixels + " px), the table's paints " + paintsIn(x.s, engine));
    assert.deepEqual(wrongInk, [], "the paints column is the ink on the page, per row, in " + engine + " (FAILS BEFORE the round-7 fixes: the column carried the oracle's reading for svg[fill=url]>rect and for the rows below, which ink nothing)");
    assert.deepEqual(all.filter((s) => s.inkUnmeasured).map((s) => s.name + ": " + s.inkUnmeasured), [], "every row's ink is measured today; a row that cannot be says so here, on the row, and is listed in this message rather than passing silently");
    assert.deepEqual(rows.filter((r) => !r.gated).map((r) => r.name), [], "every shape was gated: its host is on no list, and the gate wraps the media root");
    assert.deepEqual(rows.filter((r) => r.remote !== "moved").map((r) => r.name), [], "every remote URL was moved aside by the gate before the tree entered the page");
    assert.deepEqual(rows.filter((r) => r.rootDisplay !== "none").map((r) => r.name), [], "the sheet's rule sets display none on every gated root");
    assert.deepEqual(rows.filter((r) => r.name.startsWith("opacity=") && r.hidden !== (Number(r.rootOpacity) === 0)).map((r) => r.name + " computed " + r.rootOpacity), [], "the sheet leaves opacity alone, and figureHidden reads the computed value: zero and only zero is hidden");
    // the flow's answer is the ink, shape by shape, but where the row records the flow reading other than the ink (flowReads,
    // with its reason), where it is held to the record
    const disagree = rows.map((r, i) => ({ r, s: all[i] })).filter((x) => !flowRecorded(x.s, engine) && x.r.printable !== paintsIn(x.s, engine)).map((x) => x.r.name + ": figurePrintable " + x.r.printable + ", the twin inks " + paintsIn(x.s, engine));
    assert.deepEqual(disagree, [], "FAILS BEFORE: figurePrintable disagreed with the paint on the zero spellings, on 0.0.0, on the hidden img inside a picture, on the svg image inside defs and on the hidden svg");
    const offRecord = rows.map((r, i) => ({ r, s: all[i] })).filter((x) => flowRecorded(x.s, engine) && x.r.printable !== flowIn(x.s, engine)).map((x) => x.r.name + ": figurePrintable " + x.r.printable + ", the row records " + flowIn(x.s, engine) + " in " + engine + " (" + x.s.flowReads!.why + ")");
    assert.deepEqual(offRecord, [], "where the row records the flow answering other than the ink, the flow answers as recorded; a flow that comes to read the paint reds the row, which then drops its record");
    // where the row records the twin oracle reading other than the ink (twinReads), the oracle is held to the reading (wrongPaper below); the two records are disjoint from the ink they depart from
    assert.deepEqual(all.filter((s) => (recorded(s, engine) && oracleReads(s, engine) === paintsIn(s, engine)) || (flowRecorded(s, engine) && flowIn(s, engine) === paintsIn(s, engine))).map((s) => s.name), [], "a record names a reading OTHER than the ink; one equal to the ink is a stale record");
    // the named spellings and shapes, each to the answer the round named
    const wrong = rows.filter((r, i) => hiddenIn(all[i], engine) !== undefined && r.hidden !== hiddenIn(all[i], engine)).map((r) => r.name + ": figureHidden " + r.hidden);
    assert.deepEqual(wrong, [], "FAILS BEFORE: -0, +0, 0e0, -1 and calc(0) read as on the paper, 0.0.0 as off it, and <svg hidden> as hidden");
    const wrongPaper = paperMismatches(rows, all.map((s) => oracleReads(s, engine)));
    assert.deepEqual(wrongPaper, [], "the twin oracle reads the ink, or the recorded per-engine reading where the row carries one (a change here is a change in the engine, and the record follows it)");
    assert.deepEqual(requests.filter((u) => !ofOrigin(u)), [], "no request left the origin before any restore: the gate moved every remote URL aside on the parser document");
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
    const asked = requests.slice(before).filter((u) => !ofOrigin(u));
    const fetchedOf = (i: number): string[] => { const a = asked.filter((u) => u === "https://" + hostOf(i) + "/p.svg").length, b = asked.filter((u) => u === "https://" + hostOf2(i) + "/q.svg").length; return [...(a ? ["a" + (a > 1 ? " x" + a : "")] : []), ...(b ? ["b" + (b > 1 ? " x" + b : "")] : [])]; };
    for (let i = 0; i < all.length; i++) t.diagnostic("fetch | " + engine + " | " + all[i].name + " | printable=" + restored[i].printableAtRestore + " | restored=" + restored[i].restored + " | fetched=" + (fetchedOf(i).join(",") || "none") + " | expected=" + (expectedFetches(all[i], engine).join(",") || "none"));
    assert.deepEqual(restored.map((r, i) => [rows[i].name, r.printableAtRestore]).filter(([, p], i) => p !== rows[i].printable), [], "the restore read the same printable answer as the rows");
    assert.deepEqual(namesWhere(restored, rows.map((r) => r.name), (r) => r.printableAtRestore === true && r.restored !== true), [], "every placeholder whose figure paints was restored (each named with what the restore read)");
    const wrongFetch = all.map((s, i) => ({ name: s.name, got: fetchedOf(i), want: expectedFetches(s, engine) })).filter((x) => x.got.join(",") !== x.want.join(",")).map((x) => x.name + ": asked for " + (x.got.join(",") || "none") + ", the table says " + (x.want.join(",") || "none"));
    assert.deepEqual(wrongFetch, [], "per URL: the restore of a figure that paints asks for every URL the browser fetches of the whole figure, a non-painting element's among them (the figure-level grant, stated in figure-gate.ts and file-print.ts), and a figure that paints nothing has no URL asked for");
    assert.deepEqual(asked.filter((u) => !/^https:\/\/s\d+b?\.remote\.test\/[pq]\.svg$/.test(u)), [], "no URL outside the shapes' own was asked for");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  }, engine);
});

/** The containers the collectPictures case builds one svg <image> in, each with its own local href: the six that never render
 *  their content (the rows above with `twinReads` in Firefox and WebKit; none is referenced here, so none paints through a
 *  referrer, the reference case below), <metadata> (not laid out in any engine) and <g>, the one that renders. */
const PICTURE_CONTAINERS: readonly string[] = ["defs", "symbol", "clipPath", "mask", "pattern", "marker", "metadata", "g"];
/** What the collectPictures case reads per engine: `rendered` for each container's image (the product's oracle, per engine),
 *  the URLs collectPictures probed, and how many pictures it returned (the <img> and the probes). */
type Collected = { rendered: Record<string, boolean | null>; probed: string[]; pictures: number; imgs: number };
/** The oracle's reading per engine for an svg <image> inside each container, as the docstrings of `rendered` and
 *  collectPictures state it: Chromium no rect for the six containers; Firefox an empty rect and WebKit a full one, both read as
 *  rendered; <metadata> not laid out anywhere; <g> rendered everywhere. */
const RENDERED_READS: Record<Engine, Record<string, boolean>> = {
  chromium: { defs: false, symbol: false, clipPath: false, mask: false, pattern: false, marker: false, metadata: false, g: true },
  firefox: { defs: true, symbol: true, clipPath: true, mask: true, pattern: true, marker: true, metadata: false, g: true },
  webkit: { defs: true, symbol: true, clipPath: true, mask: true, pattern: true, marker: true, metadata: false, g: true },
};

for (const engine of ENGINES) test("collectPictures in " + engine + " over a body of eight local svg images, one inside each SVG container (defs, symbol, clipPath, mask, pattern, marker, metadata, g), and one <img>: the pictures are the <img> and the image inside <g> alone, the one container that renders its content, and the seven other hrefs are not probed (FAILS BEFORE the round-7 fixes in Firefox and WebKit: the rect alone decided, those engines report one for an image inside a container that never renders, and collectPictures returned eight pictures and probed all seven against Chromium's two and one); the oracle `rendered` reads each container's image as the docstrings state per engine", { timeout: 120000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    const requests: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("request", (r: any) => { requests.push(r.url()); });
    const js = bundle();
    const body = PICTURE_CONTAINERS.map((c) => '<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><' + c + '><image href="/pic-' + c + '.svg" width="8" height="8"/></' + c + "></svg>").join("") + '<img src="/pic-img.svg" width="8" height="8" alt="">';
    const html = '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><div class="fileview-md" id="root">' + body + '</div><script src="/leg.js"></script></body></html>';
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/leg.js") return route.fulfill({ status: 200, contentType: "text/javascript", body: js });
      if (u.pathname.startsWith("/pic-") && u.pathname.endsWith(".svg")) return route.fulfill({ status: 200, contentType: "image/svg+xml", body: SVG });
      return route.fulfill({ status: 200, contentType: "text/html", body: html });
    });
    await page.goto(ORIGIN + "/");
    const got: Collected = await page.evaluate(async (containers: string[]) => {
      const w = window as any;
      const root = document.getElementById("root")!;
      await Promise.all(Array.from(root.querySelectorAll("img")).map((i) => i.complete ? null : new Promise<void>((r) => { i.addEventListener("load", () => r()); i.addEventListener("error", () => r()); })));
      await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
      const rendered: Record<string, boolean | null> = {};
      for (const c of containers) rendered[c] = w.FVF.rendered(root.querySelector(c + " > image"));
      const probed: string[] = [];
      const pics = w.FVF.collectPictures(root, location.href, (url: string) => { probed.push(url); return { complete: true, addEventListener() {}, removeEventListener() {} }; }) as unknown[];
      return { rendered, probed, pictures: pics.length, imgs: pics.filter((p) => p instanceof HTMLImageElement).length };
    }, PICTURE_CONTAINERS as string[]);
    for (const c of PICTURE_CONTAINERS) t.diagnostic("pictures | " + engine + " | svg>" + c + ">image | rendered=" + got.rendered[c] + " | probed=" + got.probed.includes(ORIGIN + "/pic-" + c + ".svg"));
    t.diagnostic("pictures | " + engine + " | collectPictures returned " + got.pictures + " (" + got.imgs + " img) | probed " + got.probed.join(",") + " | the render requested " + requests.filter((u) => u.includes("/pic-")).length + " picture URLs");
    assert.deepEqual(got.rendered, RENDERED_READS[engine], "the oracle reads each container's image as the docstrings state for " + engine);
    assert.deepEqual(got.probed, [ORIGIN + "/pic-g.svg"], "the image inside <g> is the one svg picture probed in " + engine + " (FAILS BEFORE in Firefox and WebKit: all seven laid-out containers' images were probed)");
    assert.deepEqual({ pictures: got.pictures, imgs: got.imgs }, { pictures: 2, imgs: 1 }, "two pictures, the <img> and one probe, in " + engine + " (FAILS BEFORE in Firefox and WebKit: eight)");
    assert.deepEqual(PICTURE_CONTAINERS.filter((c) => !requests.includes(ORIGIN + "/pic-" + c + ".svg")), [], "the render itself requested every container's image, <metadata>'s among them, in " + engine + ", so the fix changes what the wait counts and probes, never what the page fetches");
    assert.deepEqual(errors, [], "no script error");
    await page.close();
  }, engine);
});

// ── the reference case (the round-7 review's cluster E, 2026-09-21): an image inside a pattern, a mask or a marker paints through the element that references it ──

/** The image the reference case serves: a red square, so a mask's luminance is not zero (a black image masks everything out,
 *  and the masked rect would ink nothing whether the picture landed or not) and the picture's ink is told from the referrer's
 *  own paint (the mask's rect is black). */
const RED = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16"><rect width="16" height="16" fill="red"/></svg>';
const refImage = (href: string): string => '<image href="' + href + '" width="16" height="16"/>';
/** The three containers whose content paints through a reference, each inside <defs> with the element that references it: a
 *  rect filled by the pattern, a rect masked by the mask, a line carrying the marker at its start. `href` is the image's URL
 *  and `ref` the reference's spelling: `#<id>` as an author writes it, or `#user-content-<id>`, the sanitizer's own spelling
 *  of the id it mints (md-sanitize.ts prefixes every author id and leaves url() values as written, so after the sanitize the
 *  author's spelling names nothing and the prefixed one names the container). The id is `p`; the case suffixes it per cell. */
const REFERENCE_SHAPES: ReadonlyArray<{ container: string; html: (href: string, ref: string) => string }> = [
  { container: "pattern", html: (href, ref) => '<defs><pattern id="p" width="1" height="1">' + refImage(href) + '</pattern></defs><rect width="16" height="16" fill="url(' + ref + ')"/>' },
  { container: "mask", html: (href, ref) => '<defs><mask id="p" maskUnits="userSpaceOnUse" x="0" y="0" width="16" height="16">' + refImage(href) + '</mask></defs><rect width="16" height="16" fill="black" mask="url(' + ref + ')"/>' },
  { container: "marker", html: (href, ref) => '<defs><marker id="p" markerUnits="userSpaceOnUse" markerWidth="16" markerHeight="16" refX="0" refY="0" overflow="visible">' + refImage(href) + '</marker></defs><line x1="0" y1="0" x2="16" y2="16" stroke="none" marker-start="url(' + ref + ')"/>' },
];
/** One cell of the reference case: a container, the reference's spelling, whether the image's route serves it or answers 404
 *  (the twin), and the image's URL, unique per cell so the probes name their cell. */
type RefCell = { i: number; container: string; spelling: "author" | "prefixed"; served: boolean; url: string };
/** What the page reads of a cell: `rendered` on the image and on its referrer, `printable` on the image, whether collectPictures
 *  probed the cell's URL, and the sanitizer's survivors with the attributes the reference rides on. */
type RefRead = { rendered: boolean | null; renderedReferrer: boolean | null; printable: boolean | null; collected: boolean; survivors: string };
/** The ink inside a cell's box: the pixels that are not white, and the colour most of them share. */
type RefInk = { pixels: number; mode: string };

for (const engine of ENGINES) test("collectPictures in " + engine + " over sanitized bodies whose svg image stands inside a <pattern>, a <mask> or a <marker> that a rect or a line references by url(#id), each with the reference spelled as an author writes it (dead after the sanitize: the id is prefixed user-content- and the value is not) and as the sanitizer spells the id, each with the image served and with its route answering 404 (the twin): the picture reaches the paper, measured as ink inside the cell that differs from the twin's, exactly where the prefixed reference names the container, in every engine, screen and print alike; collectPictures collects exactly the images of the containers whose served cell paints, the twin of each among them (the rule reads the reference, not the load), the browser's answer read on the referrer, since `rendered` reads the image itself as the docstrings state per engine whether the container paints or not; the author-spelled cells are the control, collected in no engine; and the render requests every image URL either way (FAILS BEFORE the round-8 fixes in every engine: the walk alone decided and none of the six was collected; before the round-7 fixes the rect decided, and Firefox and WebKit collected them where Chromium never did)", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 600, height: 700 } });
    const errors: string[] = [];
    const requests: string[] = [];
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    page.on("request", (r: any) => { requests.push(r.url()); });
    const js = bundle();
    const cells: RefCell[] = [];
    for (const s of REFERENCE_SHAPES) for (const spelling of ["author", "prefixed"] as const) for (const served of [true, false]) {
      const i = cells.length;
      cells.push({ i, container: s.container, spelling, served, url: (served ? "/ref-" : "/ref-missing-") + i + ".svg" });
    }
    const markupOf = (c: RefCell): string => {
      const shape = REFERENCE_SHAPES.find((s) => s.container === c.container)!;
      return '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16">' + shape.html(c.url, "#" + (c.spelling === "prefixed" ? "user-content-" : "") + "p" + c.i).replace('id="p"', 'id="p' + c.i + '"') + "</svg>";
    };
    const html = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>body { margin: 0; background: #fff; } .cell { position: absolute; left: 20px; width: 16px; height: 16px; line-height: 0; }</style></head><body><div class="fileview-md" id="root"></div><script src="/leg.js"></script></body></html>';
    await page.route((u: URL) => u.href.startsWith(ORIGIN), (route: any) => {
      const u = new URL(route.request().url());
      if (u.pathname === "/leg.js") return route.fulfill({ status: 200, contentType: "text/javascript", body: js });
      if (u.pathname.startsWith("/ref-missing-")) return route.fulfill({ status: 404, contentType: "text/plain", body: "never" });
      if (u.pathname.startsWith("/ref-")) return route.fulfill({ status: 200, contentType: "image/svg+xml", body: RED });
      return route.fulfill({ status: 200, contentType: "text/html", body: html });
    });
    await page.goto(ORIGIN + "/");
    const reads: RefRead[] = await page.evaluate(async (specs: Array<{ i: number; markup: string; url: string }>) => {
      const w = window as any;
      const root = document.getElementById("root")!;
      for (const s of specs) {   // each body through the sanitizer, the road a note's markup takes to the page
        const cell = document.createElement("div");
        cell.className = "cell"; cell.setAttribute("data-cell", String(s.i)); cell.style.top = (20 + s.i * 30) + "px";
        const clean = w.FVF.sanitizeMd(s.markup) as HTMLElement;
        while (clean.firstChild) cell.appendChild(clean.firstChild);
        root.appendChild(cell);
      }
      await new Promise((r) => setTimeout(r, 1500));   // an svg <image> reports no completeness: time for every route to answer
      await new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r())));
      const probed: string[] = [];
      w.FVF.collectPictures(root, location.href, (url: string) => { probed.push(url); return { complete: true, addEventListener() {}, removeEventListener() {} }; });
      return specs.map((s) => {
        const cell = root.querySelector('[data-cell="' + s.i + '"]')!;
        const im = cell.querySelector("image");
        const referrer = cell.querySelector("rect, line");
        const survivors = Array.from(cell.querySelectorAll("*")).map((e) => e.localName + Array.from(e.attributes).filter((a) => /^(id|href|fill|mask|marker-start)$/.test(a.name)).map((a) => "[" + a.name + "=" + a.value + "]").join("")).join(" ");
        return { rendered: im ? w.FVF.rendered(im) : null, renderedReferrer: referrer ? w.FVF.rendered(referrer) : null, printable: im ? w.FVF.printable(im) : null, collected: probed.includes(location.origin + s.url), survivors };
      });
    }, cells.map((c) => ({ i: c.i, markup: markupOf(c), url: c.url })));
    // the ink, the figure case's read: one full-page screenshot decoded in the page, the pixels inside each cell's box that are
    // not white counted, with the colour most of them share; read on screen and again under print media
    const inkRead = async (): Promise<RefInk[]> => {
      const shot: Buffer = await page.screenshot({ fullPage: true });
      return page.evaluate(async ([png, n]: [string, number]) => {
        const img = new Image(); img.src = "data:image/png;base64," + png; await img.decode();
        const canvas = document.createElement("canvas"); canvas.width = img.naturalWidth; canvas.height = img.naturalHeight;
        const ctx = canvas.getContext("2d")!; ctx.drawImage(img, 0, 0);
        const scale = window.devicePixelRatio;
        const out: Array<{ pixels: number; mode: string }> = [];
        for (let i = 0; i < n; i++) {
          const r = document.querySelector('[data-cell="' + i + '"]')!.getBoundingClientRect();
          const d = ctx.getImageData(Math.floor((r.left + window.scrollX) * scale), Math.floor((r.top + window.scrollY) * scale), Math.ceil(r.width * scale), Math.ceil(r.height * scale)).data;
          let pixels = 0; const hist: Record<string, number> = {};
          for (let k = 0; k < d.length; k += 4) if (d[k] < 250 || d[k + 1] < 250 || d[k + 2] < 250) { pixels++; const c = "rgb(" + d[k] + "," + d[k + 1] + "," + d[k + 2] + ")"; hist[c] = (hist[c] || 0) + 1; }
          const mode = Object.entries(hist).sort((a, b) => b[1] - a[1])[0];
          out.push({ pixels, mode: mode ? mode[0] : "none" });
        }
        return out;
      }, [shot.toString("base64"), cells.length]);
    };
    const screen = await inkRead();
    await page.emulateMedia({ media: "print" });
    await page.evaluate(() => new Promise<void>((r) => requestAnimationFrame(() => requestAnimationFrame(() => r()))));
    const print = await inkRead();
    await page.emulateMedia({ media: null });
    const key = (k: RefInk): string => k.pixels + " " + k.mode;
    const twinOf = (c: RefCell): RefCell => cells.find((d) => d.container === c.container && d.spelling === c.spelling && !d.served)!;
    /** Whether the served cell `c`'s picture reaches the paper: its box inks, and other than its 404 twin's box (the image's
     *  load state is what the paper shows; a rect whose mask reference is dead renders unmasked, the same ink with or
     *  without the picture, so ink alone would read the picture where there is none). */
    const paints = (c: RefCell): boolean => screen[c.i].pixels > 0 && key(screen[c.i]) !== key(screen[twinOf(c).i]);
    for (const c of cells) t.diagnostic("reference | " + engine + " | " + c.container + " | " + c.spelling + " | " + (c.served ? "served" : "404") + " | ink=" + key(screen[c.i]) + " print=" + key(print[c.i]) + (c.served ? " | paints=" + paints(c) : "") + " | rendered(image)=" + reads[c.i].rendered + " rendered(referrer)=" + reads[c.i].renderedReferrer + " printable(image)=" + reads[c.i].printable + " | collected=" + reads[c.i].collected + " | " + reads[c.i].survivors);
    assert.deepEqual(errors, [], "no script error");
    assert.deepEqual(cells.filter((c) => !requests.includes(ORIGIN + c.url)).map((c) => c.url), [], "the render itself requested every cell's image, served or not, in " + engine + ": the rule changes what the wait counts and probes, never what the page fetches");
    assert.ok(screen.some((k) => k.pixels > 0) && screen.some((k) => k.pixels === 0), "the ink read tells cells apart in " + engine + " (a screenshot that missed the page would read every cell alike)");
    assert.deepEqual(cells.filter((c) => key(screen[c.i]) !== key(print[c.i])).map((c) => c.container + " " + c.spelling + (c.served ? "" : " 404") + ": screen " + key(screen[c.i]) + ", print " + key(print[c.i])), [], "every cell inks the same under print media as on screen in " + engine + ": what the screen shows of these is what the paper shows");
    const served = cells.filter((c) => c.served);
    assert.deepEqual(served.filter((c) => c.spelling === "prefixed" && !paints(c)).map((c) => c.container + ": " + key(screen[c.i]) + " against the twin's " + key(screen[twinOf(c).i])), [], "the picture inside every referenced container reaches the paper in " + engine + " when the reference names the container as the sanitizer spells the id: pattern, mask and marker");
    assert.deepEqual(served.filter((c) => c.spelling === "author" && paints(c)).map((c) => c.container + ": " + key(screen[c.i])), [], "the control: with the reference spelled as an author writes it the picture reaches the paper in no container in " + engine + " (the sanitizer prefixes the id and leaves the value as written, so the reference names nothing; a red here says the sanitizer now resolves it, the rule below then collects it, and this control's expectation is what to update)");
    // the rule: collected exactly where the reference paints, the 404 twin with its served sibling (the reference decides, not the load)
    const sibling = (c: RefCell): RefCell => served.find((s) => s.container === c.container && s.spelling === c.spelling)!;
    const expected = cells.filter((c) => paints(sibling(c))).map((c) => ORIGIN + c.url).sort();
    const got = cells.filter((c) => reads[c.i].collected).map((c) => ORIGIN + c.url).sort();
    assert.ok(expected.length > 0 && expected.length === served.filter(paints).length * 2, "the expectation is derived from the ink: " + expected.length + " URLs, two per painting container (the served image and its 404 twin), " + served.filter(paints).length + " painting containers");
    assert.deepEqual(got, expected, "collectPictures collects exactly the images of the containers whose picture reaches the paper in " + engine + ", the 404 twin of each among them, and none of the author-spelled controls (FAILS BEFORE the round-8 fixes in every engine: none of these was collected)");
    assert.deepEqual(cells.filter((c) => reads[c.i].rendered !== RENDERED_READS[engine][c.container]).map((c) => c.container + " " + c.spelling + (c.served ? "" : " 404") + ": rendered " + reads[c.i].rendered), [], "`rendered` reads the image inside each container as the docstrings state for " + engine + ", referenced or not, painting or not, so the browser's answer is not read on the image");
    assert.deepEqual(cells.filter((c) => reads[c.i].renderedReferrer !== true).map((c) => c.container + " " + c.spelling + (c.served ? "" : " 404") + ": rendered " + reads[c.i].renderedReferrer), [], "and reads every referrer, the rect or the line in rendering content, as rendered in " + engine + ": the answer the rule reads");
    await page.close();
  }, engine);
});

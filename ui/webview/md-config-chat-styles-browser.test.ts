// The Slice 4 constructs in the CHAT's markdown bodies under styles.css, in headless Chromium (plans/markdown-viewer.md,
// "one markdown configuration, Obsidian constructs included"): the grammar sits on the marked singleton, so a reply, a
// notice and the person's own bubble render callouts, ==mark==, front matter and footnotes too (the open ruling the
// build note records). The slice's review round 1 found every construct rule scoped `.fileview-md` alone: in a reply a
// <mark> wore the browser's yellow-on-black, a `> [!NOTE]` was a plain quote whose first line read "Note" in body weight
// and the quote's dim colour, front matter and a footnote definition were bare, in both themes and inside the bubble.
// The fixture goes through the chat's own path (marked under applyMdConfig then sanitizeMd, as render.ts md() does; the
// user instance of chat-md.ts for the bubble, as userMd() does) into `.assistant.md`, `.notice-md.md` and
// `.user-bubble.md`, and, for contrast, into `.fileview-md` on the same page. The computed styles are what the
// assertions read: the chat's dress equals the viewer's (the shared rules are doubled `.md X, .fileview-md X`), the
// comment highlight `mark.cmt-hl` keeps its own tint (its rule ties a `.md mark` rule on specificity and stands earlier
// in the sheet, so the construct rule keys on the renderer's own class, mark.md-mark, and never names it), a callout's
// title reads in the body's ink (round 3: the tint tokens are rails and fills, unreadable as text for the hairline and
// the caution red), and the bubble's mark and callout wear the white family the bubble's other rules use. Round 4: in
// the bubble a footnote definition and the front-matter fold kept the page's dim token on the saturated fill (1.66:1
// dark, 1.39:1 light, where the bubble's text reads at 4.67:1 and 5.13:1), and a folded callout (`> [!note]-`, a
// details) and an unfolded one (a blockquote) wore different rails and inks, since the bubble's blockquote rule outranked
// the callout rule's rail and ink for the blockquote form alone; the bubble leg types both shapes and both forms and reads
// the footnote and the fold in the bubble's own ink, the two forms equal. Round 5: every ink the slice sets in the bubble
// holds 4.5:1 on both fills, measured over the wash it sits on. A white wash under white ink lightens the fill and lowers
// the ratio, so round 4's callout ink (the quote's 0.88 white over the 7% white wash) read at 3.59:1 and 3.87:1 and the
// mark (white over the code span's 20% white wash) at 3.35:1 and 3.51:1; both washes darken the fill now (8% and 18%
// black) under the bubble's own ink. The fold's YAML, a pre in the bubble's page-coloured well with no code child,
// inherited round 4's white and read at 1.19:1 on the light theme's cream; it takes the page's --fg. A dead wikilink kept
// the shared rule's 0.7 opacity, tuned to --fg on --bg, and read at 3.10:1 and 3.38:1 on the fill; it is at full ink in
// the bubble. The bubble leg opens the fold and reads every one of these at the bar, both forms of the callout included.
// Round 6: the two forms still differed on the light theme in their FACE: the bubble's blockquote rule sets the prose face
// (`--font-prose`, mono in light) for the assistant's quoted words, and reached the blockquote-form callout alone, so
// `> [!note]` read in ui-monospace and `> [!note]-` one line below in the bubble's sans; a callout is the person's own
// construct, so both forms take the bubble's face now (font-family: inherit on the bubble's callout rule) and the quoted
// passage keeps the mono. And the folded form had no vertical margin on any surface: the blockquote form takes `margin:
// 0.5em 0` from the `.md blockquote` and `.fileview-md blockquote` rules, a details matched no margin rule, so a run of
// `> [!tip]-` folds stacked flush into one tinted box where the same run unfolded sat 0.5em apart; the details form has
// the blockquote's margin at the blockquote rule's own weight (a `:where()` head), so a fold that is the body's first
// child still loses its top margin to the `> :first-child` rule as a blockquote does (read here on two one-child roots).
// Both themes. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic text
// only.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");
const KATEX_CSS = fs.readFileSync(path.join(EXT, "node_modules", "katex", "dist", "katex.min.css"), "utf8");
const STYLES = fs.readFileSync(path.join(UI, "styles.css"), "utf8").replace('@import "katex/dist/katex.min.css";', KATEX_CSS);

const BUILD = { bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
  nodePaths: [path.join(EXT, "node_modules")], external: ["*.png", "*.svg", "*.woff", "*.ttf", "../media/*.woff2"], logLevel: "silent" };
/** The chat's two renderers, minus the PR-reference walk: the singleton under md-config.ts and the bubble's instance, each through sanitizeMd. */
function probeBundle(): string {
  const contents = [
    'import { marked } from "marked";',
    'import { applyMdConfig } from "./md-config";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { userMdHtml } from "./chat-md";',
    "applyMdConfig();",
    "(window as any).__md = (s: string) => sanitizeMd(marked.parse(s) as string).innerHTML;",
    "(window as any).__userMd = (s: string) => sanitizeMd(userMdHtml(s)).innerHTML;",
  ].join("\n");
  const r = requireCjs("esbuild").buildSync({ ...BUILD, stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "chat-styles-probe.ts" } });
  return r.outputFiles[0].text;
}

const REPLY = [
  "---", "title: Test Note", "tags: [a, b]", "---", "",
  "> [!NOTE]", "> This only affects the web dashboard.", "",
  "> [!WARNING]", "> Careful here.", "",
  "> plain quote for reference", "",
  "> [!NOTE]- A folded note", "> Folded body.", "",
  "The ==important== bit and a footnote[^1], see [[Note]].", "",
  "[^1]: The footnote definition text.", "",
].join("\n");
// what the person types: a note pasted whole (its YAML opener folds as front matter), a footnote, a callout and the same
// callout folded, the two forms of one construct one line apart
const TYPED = ["---", "title: Pasted note", "---", "", "==this== is what I typed[^1], see [[Note]]", "", "> [!NOTE]", "> pasted from an issue", "",
  "> [!NOTE]- the same, folded", "> its body", "", "> a passage I quoted from the reply", "", "[^1]: the source I pasted"].join("\n");
// a callout as the ONLY child of a body, in each form: the body's `> :first-child` and `> :last-child` rules take its margins
const FIRST_FOLD = "> [!NOTE]- A first fold\n> its body\n", FIRST_BLOCK = "> [!NOTE] A first block\n> its body\n";

const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}</style></head><body>
<div id=content>
  <div class="turn turn-assistant"><div class="assistant md" id=a></div></div>
  <div class="notice-md md" id=n></div>
  <div class="turn turn-user"><div class="user-bubble md" id=u></div></div>
  <div class="fileview-md" id=f></div>
  <div class="fileview-md" id=ff></div>
  <div class="fileview-md" id=fb></div>
  <p id=ref>A <mark class="cmt-hl">commented</mark> passage outside any markdown body</p>
</div>
<script>window.__pageErrors=[];window.addEventListener("error",function(e){window.__pageErrors.push(String(e.message));});</script>
<script>${probeBundle()}</script>
<script>
  var reply = ${JSON.stringify(REPLY)}, typed = ${JSON.stringify(TYPED)};
  document.getElementById("ff").innerHTML = window.__md(${JSON.stringify(FIRST_FOLD)});
  document.getElementById("fb").innerHTML = window.__md(${JSON.stringify(FIRST_BLOCK)});
  document.getElementById("a").innerHTML = window.__md(reply) + '<p>A <mark class="cmt-hl">commented</mark> passage in the reply</p>';
  document.getElementById("n").innerHTML = window.__md(reply);
  document.getElementById("u").innerHTML = window.__userMd(typed);
  document.getElementById("f").innerHTML = window.__md(reply);
</script></body></html>`;

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

async function inBrowser(t: any, body: (browser: any) => Promise<void>): Promise<void> {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  try { await body(browser); } finally { await browser.close(); }
}

const UA_MARK_BG = "rgb(255, 255, 0)";   // the browser's default <mark> (yellow on black), the state the review found

type Dress = Record<string, Record<string, string> | null>;
/** The computed properties of each construct under one root, keyed by selector; a missing element reads null. */
const READ_DRESS = `(function (rootId) {
  var root = document.getElementById(rootId);
  var want = {
    "mark:not(.cmt-hl)": ["backgroundColor", "color", "borderTopLeftRadius"],
    "blockquote.md-callout.md-callout-note": ["borderLeftColor", "borderLeftWidth", "backgroundColor", "borderTopRightRadius", "color", "fontFamily", "marginTop", "marginBottom"],
    "blockquote.md-callout.md-callout-warning": ["borderLeftColor"],
    ".md-callout-note > .md-callout-title": ["fontWeight", "color", "marginTop", "fontFamily"],
    ".md-callout-note > p:not(.md-callout-title)": ["fontWeight", "color", "fontFamily"],
    "blockquote:not(.md-callout)": ["borderLeftColor", "borderLeftWidth", "color", "fontFamily"],
    "details.md-callout.md-callout-note": ["borderLeftColor", "borderLeftWidth", "backgroundColor", "color", "fontFamily", "marginTop", "marginBottom"],
    "details.md-callout > summary.md-callout-title": ["fontWeight", "color", "fontFamily"],
    "details.md-callout > p": ["color", "fontFamily"],
    "details.md-frontmatter": ["borderTopWidth", "borderTopStyle", "borderTopColor", "borderTopLeftRadius", "color"],
    "details.md-frontmatter > summary": ["color"],
    "details.md-frontmatter > pre": ["color", "backgroundColor"],   // the YAML, laid out only while the fold is open (the bubble leg opens it)
    "span.fv-wikilink": ["color", "opacity", "textDecorationLine"],   // the dead wikilink span (no directory to resolve against in the chat)
    "div.md-footnote": ["borderLeftWidth", "borderLeftColor", "color"],
    "sup.md-fnref": ["lineHeight"],
    "mark.cmt-hl": ["backgroundColor"],
    ":scope > p": ["color"],   // a body paragraph of the root itself, never the callout's title
  };
  var out = {};
  for (var sel in want) {
    var el = root.querySelector(sel);
    if (!el) { out[sel] = null; continue; }
    var cs = getComputedStyle(el); var o = {};
    for (var i = 0; i < want[sel].length; i++) o[want[sel][i]] = cs[want[sel][i]];
    out[sel] = o;
  }
  out["__root"] = { color: getComputedStyle(root).color, backgroundColor: getComputedStyle(root).backgroundColor, fontFamily: getComputedStyle(root).fontFamily };
  return out;
})`;

function assertViewerDress(chat: Dress, viewer: Dress, where: string): void {
  const mark = chat["mark:not(.cmt-hl)"]!, vmark = viewer["mark:not(.cmt-hl)"]!;
  assert.ok(mark && vmark, where + ": the ==mark== rendered in both roots");
  assert.notEqual(mark.backgroundColor, UA_MARK_BG, where + ": the mark is not the browser's yellow");
  assert.equal(mark.backgroundColor, vmark.backgroundColor, where + ": the mark wears the viewer's amber wash");
  assert.equal(mark.color, chat[":scope > p"]!.color, where + ": the mark's ink is the body's (color: inherit), not the browser's black");
  assert.equal(mark.borderTopLeftRadius, vmark.borderTopLeftRadius, where + ": the mark's radius matches the viewer's (its em padding scales with each surface's size)");
  const note = chat["blockquote.md-callout.md-callout-note"]!, vnote = viewer["blockquote.md-callout.md-callout-note"]!;
  const plain = chat["blockquote:not(.md-callout)"]!;
  assert.equal(note.borderLeftWidth, "3px", where + ": the callout's rail is the viewer's 3px, not the plain quote's 2px");
  assert.equal(note.borderLeftColor, vnote.borderLeftColor, where + ": the note callout is tinted the accent, as in the viewer");
  assert.notEqual(note.borderLeftColor, plain.borderLeftColor, where + ": the callout's rail is not the plain quote's hairline");
  assert.equal(note.backgroundColor, vnote.backgroundColor, where + ": the callout's wash matches the viewer's");
  assert.equal(note.borderTopRightRadius, vnote.borderTopRightRadius, where + ": the callout's radius matches the viewer's");
  assert.equal(note.color, chat[":scope > p"]!.color, where + ": the callout's body reads in the body colour, not the quote's dim");
  assert.notEqual(chat["blockquote.md-callout.md-callout-warning"]!.borderLeftColor, note.borderLeftColor, where + ": a warning is tinted apart from a note");
  const title = chat[".md-callout-note > .md-callout-title"]!;
  assert.equal(title.fontWeight, "600", where + ": the callout's title is bold");
  assert.equal(title.color, chat[":scope > p"]!.color, where + ": the title reads in the body's ink; the callout's tint is its rail and wash (the tokens are not inks)");
  assert.notEqual(title.color, note.borderLeftColor, where + ": the title is not painted in the rail's token");
  assert.equal(title.marginTop, "0px", where + ": the title sits on the callout's top edge, not a paragraph's margin");
  assert.equal(chat[".md-callout-note > p:not(.md-callout-title)"]!.fontWeight, "400", where + ": the callout's body stays regular");
  // round 6: the folded form (a details) matched no margin rule, so consecutive folds stacked flush into one tinted box
  // where the blockquote form sits 0.5em apart through `.md blockquote` / `.fileview-md blockquote`; both forms one box now
  const fold = chat["details.md-callout.md-callout-note"]!, vfold = viewer["details.md-callout.md-callout-note"]!;
  assert.ok(fold && vfold, where + ": the folded callout rendered in both roots");
  assert.notEqual(note.marginTop, "0px", where + ": the callout is not the body's first child here, so it wears the quote's 0.5em margin");
  assert.equal(fold.marginTop, note.marginTop, where + ": the folded and the unfolded callout wear one top margin (before: the details form's UA 0px)");
  assert.equal(fold.marginBottom, note.marginBottom, where + ": ...and one bottom margin");
  assert.equal(vfold.marginTop, vnote.marginTop, where + ": ...and in the viewer's root too (its em is the viewer's own size, so no cross-root px)");
  assert.equal(fold.fontFamily, note.fontFamily, where + ": the two forms read in one face");
  const fm = chat["details.md-frontmatter"]!, vfm = viewer["details.md-frontmatter"]!;
  assert.equal(fm.borderTopWidth, vfm.borderTopWidth, where + ": the front matter is boxed as in the viewer");
  assert.equal(fm.borderTopStyle, "solid", where + ": the front matter's box is drawn");
  assert.equal(fm.borderTopLeftRadius, vfm.borderTopLeftRadius, where + ": the front matter's radius matches the viewer's");
  assert.equal(fm.color, plain.color, where + ": the front matter reads dim");
  const fn = chat["div.md-footnote"]!;
  assert.equal(fn.borderLeftWidth, "2px", where + ": the footnote definition wears its rail");
  assert.equal(fn.color, plain.color, where + ": the footnote definition reads dim");
  assert.equal(chat["sup.md-fnref"]!.lineHeight, "0px", where + ": the footnote reference does not open its line");
}

test("a reply's constructs wear the viewer's dress in the chat's markdown bodies, in both themes, and the comment highlight keeps its own tint", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    const errors: string[] = [];
    page.on("pageerror", (e: Error) => errors.push(e.message));
    await page.setContent(PAGE, { waitUntil: "load" });
    assert.deepEqual(errors, [], "the probe bundle ran clean");
    assert.deepEqual(await page.evaluate("window.__pageErrors"), [], "no script error on the page");
    const readAll = async () => ({
      a: await page.evaluate(READ_DRESS + '("a")') as Dress, n: await page.evaluate(READ_DRESS + '("n")') as Dress,
      f: await page.evaluate(READ_DRESS + '("f")') as Dress,
      ref: await page.evaluate("getComputedStyle(document.querySelector('#ref mark.cmt-hl')).backgroundColor") as string,
    });
    const dark = await readAll();
    assert.ok(dark.a["mark.cmt-hl"], "the fixture holds a comment highlight in the reply");
    // round 6: the fold's margin rule sits at the blockquote rule's weight, (0,1,1), so a fold that is the body's only child
    // loses both margins to the body's `> :first-child` and `> :last-child` rules, (0,2,0), as the blockquote form does
    const only = await page.evaluate(`(function () { var f = document.querySelector("#ff > details.md-callout"), b = document.querySelector("#fb > blockquote.md-callout");
      var r = function (el) { var cs = getComputedStyle(el); return { top: cs.marginTop, bottom: cs.marginBottom, tag: el.tagName }; }; return { fold: f && r(f), block: b && r(b) }; })()`) as { fold: { top: string; bottom: string; tag: string } | null; block: { top: string; bottom: string; tag: string } | null };
    assert.ok(only.fold && only.block, "the one-child roots rendered a details and a blockquote");
    assert.deepEqual([only.fold!.top, only.fold!.bottom], ["0px", "0px"], "a folded callout that is the body's only child keeps the body's edges (the first- and last-child rules outrank its margin rule)");
    assert.deepEqual([only.block!.top, only.block!.bottom], ["0px", "0px"], "...as the blockquote form does");
    assertViewerDress(dark.a, dark.f, "dark, a reply");
    assertViewerDress(dark.n, dark.f, "dark, a notice");
    // the comment highlight: its own rule (mark.cmt-hl) stands earlier in the sheet and ties a `.md mark` selector on
    // specificity, so a construct rule that matched it would repaint every comment in the amber wash
    assert.equal(dark.a["mark.cmt-hl"]!.backgroundColor, dark.ref, "dark: a comment highlight inside a reply is tinted as one outside any markdown body");
    assert.notEqual(dark.a["mark.cmt-hl"]!.backgroundColor, dark.a["mark:not(.cmt-hl)"]!.backgroundColor, "dark: the comment tint is not the ==mark== wash");
    await page.evaluate("document.body.classList.add('theme-light')");
    const light = await readAll();
    assertViewerDress(light.a, light.f, "light, a reply");
    assertViewerDress(light.n, light.f, "light, a notice");
    assert.equal(light.a["mark.cmt-hl"]!.backgroundColor, light.ref, "light: a comment highlight inside a reply is tinted as one outside any markdown body");
    assert.notEqual(light.a["mark:not(.cmt-hl)"]!.backgroundColor, dark.a["mark:not(.cmt-hl)"]!.backgroundColor, "the mark's wash follows the theme's token");
    assert.notEqual(light.a["blockquote.md-callout.md-callout-note"]!.borderLeftColor, dark.a["blockquote.md-callout.md-callout-note"]!.borderLeftColor, "the callout's tint follows the theme's token");
  });
});

// ── colour arithmetic: Chromium's computed colours as rgb() or rgba(), composited over the fill, then WCAG 2 contrast ──
type RGBA = [number, number, number, number];
function parse(s: string): RGBA {
  const m = /^rgba?\(\s*([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\s*\)$/.exec(s);
  if (!m) throw new Error("a colour this test cannot read: " + s);
  return [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]];
}
const over = (top: RGBA, under: RGBA): RGBA => [0, 1, 2].map((i) => top[i] * top[3] + under[i] * (1 - top[3])).concat([1]) as RGBA;
function luminance(c: RGBA): number {
  const lin = (v: number) => { const x = v / 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
  return 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
}
function contrast(a: RGBA, b: RGBA): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}
const BAR = 4.5;   // WCAG's minimum for reading text; the slice's own bar for KaTeX's flagged text and the callout titles
const QUOTE_INK = "rgba(255, 255, 255, 0.88)";   // the bubble's quote tint: a quoted passage, the math source fallback, a callout's rail
/** The ink's WCAG contrast over the ground it sits on (the fill, or a wash composited over the fill); `alpha` scales the ink (an opacity). */
const ratioOn = (ink: string, ground: RGBA, alpha = 1): number => { const c = parse(ink); return contrast(over([c[0], c[1], c[2], c[3] * alpha], ground), ground); };

test("the person's own bubble: a ==mark==, a callout in both forms, a footnote, a dead wikilink and the front matter they typed wear the bubble's white family at 4.5:1 over what they sit on, not the browser's yellow or the page's tints", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    await page.setContent(PAGE, { waitUntil: "load" });
    // the fold open, so its YAML is laid out and reads a colour (round 5: the pre's ink was never read, the fold shut)
    await page.evaluate("document.querySelector('#u details.md-frontmatter').open = true");
    for (const theme of ["dark", "light"]) {
      if (theme === "light") await page.evaluate("document.body.classList.add('theme-light')");
      const u = await page.evaluate(READ_DRESS + '("u")') as Dress;
      const a = await page.evaluate(READ_DRESS + '("a")') as Dress;
      const mark = u["mark:not(.cmt-hl)"]!;
      assert.ok(mark, theme + ": the typed ==mark== rendered in the bubble");
      assert.notEqual(mark.backgroundColor, UA_MARK_BG, theme + ": the bubble's mark is not the browser's yellow");
      assert.equal(mark.color, u["__root"]!.color, theme + ": the bubble's mark keeps the bubble's ink");
      assert.notEqual(mark.backgroundColor, a["mark:not(.cmt-hl)"]!.backgroundColor, theme + ": the bubble's mark is not the page's amber wash (a muddy tint on the saturated fill)");
      // round 5: a white wash under white ink lightens the fill and lowers the ratio (the code span's 20% white wash the mark
      // copied put it at 3.35:1 and 3.51:1, the lowest contrast in the message); the mark's wash darkens the fill instead
      assert.match(mark.backgroundColor, /^rgba\(0, 0, 0, /, theme + ": the bubble's mark is a wash that darkens the fill (before: the code span's 20% white)");
      const title = u[".md-callout-note > .md-callout-title"]!, quote = u["blockquote:not(.md-callout)"];
      assert.ok(title, theme + ": the typed callout rendered in the bubble");
      assert.equal(title.fontWeight, "600", theme + ": the bubble's callout title is bold");
      assert.notEqual(title.color, a[".md-callout-note > .md-callout-title"]!.color, theme + ": the bubble's callout title is not the page's body ink (the page's grey on the saturated fill)");
      assert.equal(title.color, u["__root"]!.color, theme + ": the bubble's callout title reads in the bubble's own ink (round 5; before: the quote's 0.88 tint, 3.59:1 and 3.87:1 over the wash)");
      const rail = u["blockquote.md-callout.md-callout-note"]!;
      assert.match(rail.borderLeftColor, /^rgba\(255, 255, 255, /, theme + ": the bubble's callout rail is in the white family");
      assert.match(rail.backgroundColor, /^rgba\(0, 0, 0, /, theme + ": the bubble's callout wash darkens the fill (round 5; before: 7% white through --callout, which lowered the ink's ratio)");
      assert.ok(quote, theme + ": the typed quoted passage rendered in the bubble");
      // round 4: the two forms of one callout. The bubble's blockquote rule (.user-bubble.md blockquote, a type selector deep)
      // outranked the shared callout rule's rail and ink for the blockquote form, so `> [!note]` wore the plain quote's 0.40
      // rail under a 0.88 ink while `> [!note]-` (a details) took the 0.88 rail --callout names and the bubble's plain white:
      // two rails and two inks one line apart. The bubble's callout rule sets the rail and the ink itself now, both forms alike.
      const fold = u["details.md-callout.md-callout-note"]!, foldTitle = u["details.md-callout > summary.md-callout-title"]!;
      assert.ok(fold && foldTitle, theme + ": the typed folded callout rendered in the bubble as a details");
      assert.equal(fold.borderLeftWidth, "3px", theme + ": the folded callout's rail is the callout's 3px");
      assert.equal(fold.borderLeftColor, rail.borderLeftColor, theme + ": the folded and the unfolded callout wear one rail (before: 0.88 against the plain quote's 0.40)");
      assert.equal(rail.borderLeftColor, QUOTE_INK, theme + ": ...the quote tint the rule's --callout names");
      assert.equal(fold.backgroundColor, rail.backgroundColor, theme + ": ...and one wash");
      assert.equal(fold.color, rail.color, theme + ": the two forms read in one ink (before: the bubble's white against the quote's 0.88)");
      assert.equal(rail.color, u["__root"]!.color, theme + ": ...the bubble's own ink (round 5; round 4 unified them downward to the quote's 0.88 tint)");
      assert.equal(foldTitle.color, title.color, theme + ": the two titles read in one ink");
      assert.equal(foldTitle.fontWeight, "600", theme + ": the folded callout's title is bold too");
      assert.equal(u["details.md-callout > p"]!.color, u[".md-callout-note > p:not(.md-callout-title)"]!.color, theme + ": the two bodies read in one ink");
      // round 6: the face. The bubble's blockquote rule sets the prose face (--font-prose, mono in the light theme) for the
      // assistant's quoted words, and reached the blockquote-form callout alone, so on light `> [!note]` read in ui-monospace
      // and `> [!note]-` in the bubble's sans; a callout is the person's own construct, so both forms take the bubble's face
      const face = u["__root"]!.fontFamily;
      assert.equal(rail.fontFamily, face, theme + ": the callout reads in the bubble's own face (before, on light: the quote rule's " + quote!.fontFamily + ")");
      assert.equal(fold.fontFamily, rail.fontFamily, theme + ": the folded and the unfolded callout wear one face");
      assert.equal(title.fontFamily, face, theme + ": ...its title too"); assert.equal(foldTitle.fontFamily, face, theme + ": ...and the folded one's");
      assert.equal(u[".md-callout-note > p:not(.md-callout-title)"]!.fontFamily, face, theme + ": ...and both bodies"); assert.equal(u["details.md-callout > p"]!.fontFamily, face);
      if (theme === "light") assert.notEqual(quote!.fontFamily, face, "light: the quoted passage keeps the prose face (mono in light, the 2026-08-31 ruling); only the callout is the person's own");
      // round 6: the box spacing. The details form matched no margin rule (UA 0px) where the blockquote form takes the quote's 0.5em
      assert.notEqual(rail.marginTop, "0px", theme + ": the typed callout is not the bubble's first child, so it wears the quote's margin");
      assert.equal(fold.marginTop, rail.marginTop, theme + ": the folded and the unfolded callout wear one top margin (before: 0px against " + rail.marginTop + ")");
      assert.equal(fold.marginBottom, rail.marginBottom, theme + ": ...and one bottom margin");
      // round 4: the footnote definition and the front-matter fold. Their shared rules colour them var(--dim), the page's grey,
      // which on the fill read at 1.66:1 (dark) and 1.39:1 (light) where the bubble's text reads at 4.67:1 and 5.13:1; the
      // sheet's own blockquote comment names that grey at ~2:1 on this fill as the reason the quote was re-inked. Both take the
      // bubble's own ink now (color: inherit), the 0.86em text clearing 4.5:1 on both fills, and the quote's 0.40 rail and box.
      const fill = parse(u["__root"]!.backgroundColor);
      const fn = u["div.md-footnote"]!, fm = u["details.md-frontmatter"]!, fmLabel = u["details.md-frontmatter > summary"]!;
      assert.ok(fn && fm && fmLabel, theme + ": the typed footnote and the pasted YAML rendered in the bubble");
      assert.equal(fn.color, u["__root"]!.color, theme + ": the footnote definition reads in the bubble's own ink (before: the page's " + a["div.md-footnote"]!.color + ")");
      assert.notEqual(fn.color, a["div.md-footnote"]!.color, theme + ": ...not the page's dim grey on the saturated fill");
      assert.equal(fm.color, u["__root"]!.color, theme + ": the front matter reads in the bubble's own ink (before: the page's " + a["details.md-frontmatter"]!.color + ")");
      assert.equal(fmLabel.color, u["__root"]!.color, theme + ": ...its fold label too");
      // round 5: the fold's YAML is a pre in the bubble's page-coloured well (the bubble's pre rule) with no code child, so
      // it inherited the fold's white and read at 1.19:1 on the light theme's cream; it takes the page's own reading ink
      const yaml = u["details.md-frontmatter > pre"]!;
      assert.ok(yaml, theme + ": the fold is open and its YAML laid out");
      assert.notEqual(yaml.backgroundColor, u["__root"]!.backgroundColor, theme + ": the YAML sits in the page-coloured well, not on the fill");
      assert.equal(parse(yaml.backgroundColor)[3], 1, theme + ": ...an opaque well (" + yaml.backgroundColor + ")");
      assert.notEqual(yaml.color, fm.color, theme + ": the YAML does not inherit the fold's ink (white on the well: 1.19:1 in light before round 5)");
      // round 5: a dead wikilink kept the shared rule's 0.7 opacity, tuned to --fg on --bg, and read at 3.10:1 and 3.38:1 on the fill
      const wiki = u["span.fv-wikilink"]!, replyWiki = a["span.fv-wikilink"]!;
      assert.ok(wiki && replyWiki, theme + ": the typed [[Note]] rendered as the dead span in the bubble and in the reply");
      assert.equal(wiki.opacity, "1", theme + ": the bubble's dead wikilink is at full ink (the reply's keeps the shared " + replyWiki.opacity + ")");
      assert.equal(replyWiki.opacity, "0.7", theme + ": ...the shared rule stands elsewhere");
      assert.match(wiki.textDecorationLine, /underline/, theme + ": ...and keeps the dead link's underline");
      assert.equal(wiki.color, u["__root"]!.color, theme + ": ...in the bubble's own ink");
      // every ink the slice sets in the bubble, at the bar, over the ground it sits on: the fill, a wash over the fill, the well
      const railGround = over(parse(rail.backgroundColor), fill), foldGround = over(parse(fold.backgroundColor), fill), markGround = over(parse(mark.backgroundColor), fill);
      const inks: [string, string, RGBA, number][] = [
        ["the footnote definition", fn.color, fill, 1], ["the front matter's label", fmLabel.color, fill, 1],
        ["the front matter's YAML", yaml.color, parse(yaml.backgroundColor), 1],
        ["the callout's body", u[".md-callout-note > p:not(.md-callout-title)"]!.color, railGround, 1], ["the callout's title", title.color, railGround, 1],
        ["the folded callout's body", u["details.md-callout > p"]!.color, foldGround, 1], ["the folded callout's title", foldTitle.color, foldGround, 1],
        ["the ==mark==", mark.color, markGround, 1], ["the dead wikilink", wiki.color, fill, parseFloat(wiki.opacity)],
      ];
      for (const [what, ink, ground, alpha] of inks) {
        const ratio = ratioOn(ink, ground, alpha);
        assert.ok(ratio >= BAR, theme + ": " + what + " reads at " + ratio.toFixed(2) + ":1 (" + ink + " on rgb(" + ground.slice(0, 3).map(Math.round).join(", ") + ")); the bar is " + BAR + ":1");
      }
      assert.match(fn.borderLeftColor, /^rgba\(255, 255, 255, /, theme + ": the footnote's rail is in the white family (the quote's tint), not the page's hairline");
      assert.match(fm.borderTopColor, /^rgba\(255, 255, 255, /, theme + ": the front matter's box is in the white family, not the page's hairline");
      assert.equal(fm.borderTopStyle, "solid", theme + ": ...and drawn");
    }
  });
});

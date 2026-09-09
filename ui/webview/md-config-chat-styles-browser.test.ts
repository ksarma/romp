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
// in the sheet, so the construct rule must skip it), and the bubble's mark and callout wear the white family the bubble's
// other rules use. Both themes. Skips LOUDLY without a playwright browser (CI installs none), as the other browser legs
// do. Synthetic text only.
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
  "The ==important== bit and a footnote[^1].", "",
  "[^1]: The footnote definition text.", "",
].join("\n");
const TYPED = ["==this== is what I typed", "", "> [!NOTE]", "> pasted from an issue"].join("\n");

const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8><style>${STYLES}</style></head><body>
<div id=content>
  <div class="turn turn-assistant"><div class="assistant md" id=a></div></div>
  <div class="notice-md md" id=n></div>
  <div class="turn turn-user"><div class="user-bubble md" id=u></div></div>
  <div class="fileview-md" id=f></div>
  <p id=ref>A <mark class="cmt-hl">commented</mark> passage outside any markdown body</p>
</div>
<script>window.__pageErrors=[];window.addEventListener("error",function(e){window.__pageErrors.push(String(e.message));});</script>
<script>${probeBundle()}</script>
<script>
  var reply = ${JSON.stringify(REPLY)}, typed = ${JSON.stringify(TYPED)};
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
    "blockquote.md-callout.md-callout-note": ["borderLeftColor", "borderLeftWidth", "backgroundColor", "borderTopRightRadius", "color"],
    "blockquote.md-callout.md-callout-warning": ["borderLeftColor"],
    ".md-callout-note > .md-callout-title": ["fontWeight", "color", "marginTop"],
    ".md-callout-note > p:not(.md-callout-title)": ["fontWeight", "color"],
    "blockquote:not(.md-callout)": ["borderLeftColor", "borderLeftWidth", "color"],
    "details.md-frontmatter": ["borderTopWidth", "borderTopStyle", "borderTopColor", "borderTopLeftRadius", "color"],
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
  out["__root"] = { color: getComputedStyle(root).color, backgroundColor: getComputedStyle(root).backgroundColor };
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
  assert.equal(title.color, note.borderLeftColor, where + ": the title takes the callout's tint");
  assert.equal(title.marginTop, "0px", where + ": the title sits on the callout's top edge, not a paragraph's margin");
  assert.equal(chat[".md-callout-note > p:not(.md-callout-title)"]!.fontWeight, "400", where + ": the callout's body stays regular");
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

test("the person's own bubble: a ==mark== and a callout they typed wear the bubble's white family, not the browser's yellow or the page's tints", { timeout: 180000 }, async (t) => {
  await inBrowser(t, async (browser) => {
    const page = await browser.newPage({ viewport: { width: 900, height: 700 } });
    await page.setContent(PAGE, { waitUntil: "load" });
    for (const theme of ["dark", "light"]) {
      if (theme === "light") await page.evaluate("document.body.classList.add('theme-light')");
      const u = await page.evaluate(READ_DRESS + '("u")') as Dress;
      const a = await page.evaluate(READ_DRESS + '("a")') as Dress;
      const mark = u["mark:not(.cmt-hl)"]!;
      assert.ok(mark, theme + ": the typed ==mark== rendered in the bubble");
      assert.notEqual(mark.backgroundColor, UA_MARK_BG, theme + ": the bubble's mark is not the browser's yellow");
      assert.equal(mark.color, u["__root"]!.color, theme + ": the bubble's mark keeps the bubble's ink");
      assert.notEqual(mark.backgroundColor, a["mark:not(.cmt-hl)"]!.backgroundColor, theme + ": the bubble's mark is not the page's amber wash (a muddy tint on the saturated fill)");
      assert.match(mark.backgroundColor, /^rgba\(255, 255, 255, /, theme + ": the bubble's mark is a white wash, as the bubble's code spans are");
      const title = u[".md-callout-note > .md-callout-title"]!, quote = u["blockquote:not(.md-callout)"];
      assert.ok(title, theme + ": the typed callout rendered in the bubble");
      assert.equal(title.fontWeight, "600", theme + ": the bubble's callout title is bold");
      assert.notEqual(title.color, a[".md-callout-note > .md-callout-title"]!.color, theme + ": the bubble's callout title is not the page's accent (the accent on the saturated fill)");
      assert.match(title.color, /^rgba\(255, 255, 255, /, theme + ": the bubble's callout title is in the white family");
      assert.equal(quote, null, theme + ": (the fixture types no plain quote)");
    }
  });
});

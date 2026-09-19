// The DOM's side of anchor-map-html-text.test.ts's rules, over the REAL pipeline in headless Chromium (the Slice 5 review,
// round 4's text rules; this leg from round 5). That file pins what the fallback reader shows for html the parser and the
// sanitizer shape (stripMarkupMapped, renderedQuote), and every one of its assertions compares the reader with itself; this
// leg renders each of its shapes as the viewer does (marked under applyMdConfig, then sanitizeMd, the sanitized body's
// children adopted as mdBlock adopts them, file-view.ts) and checks the reader against the DOM two ways. (1) The whole text:
// the box's textContent against the reader's text, whitespace-normalized, except where a recorded rule keeps them apart by
// design: the hay's blank between two adjacent table parts is no node (hayRuns), so a minified raw table is compared with
// its whitespace removed, and a markdown table's delimiter row is text to the reader alone (item 8's rule), so it is taken
// out of the reader's text first. (2) Each quote the text test reads: the real paint (paintRendered) over that DOM, which
// must wrap something, its marks reading the shown text the text test pins for the same slice (whitespace aside: the marks
// of two cells hold no blank between them), in the cells named where a table is involved; the reader's needle for the slice
// is that shown text normalized, so an entry's `shown` IS the text test's string (round 6: three round-5 entries carried a
// blank the rule removed, and passed under the marks' whitespace-blind compare). So a sanitizer profile that kept
// svg's foreignObject, or dropped a title, would go red here (the foreignObject and svg title shapes) while the text test,
// reading the reader alone, stayed green: that gap is what this leg closes. The plan's one recorded divergence is pinned both
// ways (RECORDED: the DOM's text and the reader's, so a change on either side is seen; since the closing check of PR 804, decision
// 52, an entry may also pin the DOM's top-level tags and the map's verdict per passage, `shape` and `verdicts`, whether or not the
// text agrees). The shapes of the findings round 5's
// review seeded against the reader are here as plain shapes and were red over a git archive of 701728eae, the tree that
// round reviewed: a named reference the browser decodes and the reader's HTML 4.01 table did not (`&check;`, `&ltimes;`,
// `&notni;`, and `&toString;` read with `in`), a quote from a cell across a table's end into trailing text (three shapes:
// lenientHtml's blank at every part's end where the hay puts one only between two adjacent parts), an inline svg title
// closed by the svg's end tag (no FOREIGN counter inline), and a `<title>` block the document begins with, which the reader
// read as its text. Round 6's three shapes (anchor-map-html-rules.test.ts tests 7 and 8) were red over a git archive of
// 8924fa17e the same way: a `<style>` or a `<br>` between two cells of a minified raw table, which the DOM leaves adjacent
// (the reader read the cells run together), and an HTML element left open inside a `<foreignObject>` at `</svg>`, which
// keeps the parser from closing the svg (the reader read the passage's tail as shown text where the DOM shows `Intro`
// alone). A body `<title>` anywhere is dropped content to the reader since round 5, and this leg holds the
// sanitizer to the same rule: its text is out of the DOM too (the profile drops the element with its content), so the three
// inline `<title>` shapes read `Lead tail` on both sides. Not a shape here: a wikilink inside an inline `<textarea>`, whose
// divergence (the reader rendered the singleton's dead span against a DOM showing the file kind's anchor) exists only under
// the file kind's token walk (file-view-links.ts viewerWalkTokens), which this pipeline, mdBlock over a render with no
// document, never runs; anchor-map-dom-rules-browser.test.ts pins it over the real viewer, where the walk does run. Skips
// LOUDLY without a playwright browser (CI installs none), as the other browser legs do. Synthetic values only; non-ASCII
// characters are written as escapes throughout.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as path from "node:path";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
// resolve playwright and esbuild from the extension, not from wherever this bundle was written (a single-file run lands it under TMPDIR)
const requireCjs = createRequire(path.join(EXT, "package.json"));
const UI = path.resolve(EXT, "..", "ui", "webview");

/** `s` with its whitespace runs folded to one blank and its edges trimmed (the text test's reading). */
const norm = (s: string): string => s.replace(/\s+/g, " ").trim();
/** `s` with its whitespace removed: how two marks apart in the DOM are read against a needle holding the hay's blank. */
const nows = (s: string): string => s.replace(/\s+/g, "");
// the glyphs the DOM shows, as escapes (the text test's constants)
const MDASH = "\u2014", NDASH = "\u2013", COPY = "\u00a9", REG = "\u00ae", HELLIP = "\u2026", REPL = "\ufffd", EURO = "\u20ac", NOT = "\u00ac";
const SMILE = "\u{1F600}", GRIN = "\u{1F601}";

/** A quote of the text test: the source slice from the first `from` to the end of the first `to` after it (`from` alone when
 *  `to` is absent), the shown text its marks must read (the string the text test pins for the reader's needle), and the table
 *  cells the marks must sit in, in order (`TD1` is the second cell of its row, null a mark outside any cell), where the shape is a table. */
type Quote = { from: string; to?: string; shown: string; cells?: (string | null)[] };
/** A shape whose DOM the reader must match: `whole` names the one recorded reason the whole-text comparison is not the plain
 *  normalized one ("blanks": a minified raw table, compared with whitespace removed; "rows": a markdown table, its delimiter
 *  rows taken out of the reader's text). */
type Shape = { name: string; src: string; quotes?: Quote[]; whole?: "blanks" | "rows" };
/** A divergence between the DOM and the reader, pinned on both sides (normalized), with why; since the closing check of PR 804 an
 *  entry may also pin the DOM's top-level tags (`shape`: an element's tag, its element children in brackets, the top-level elements
 *  joined by blanks) and each LATER passage's verdict from the map over a real Selection (`verdicts`, joined by blanks: `maps` at its
 *  own source offsets, `mismatch` refused with the mismatch sentence, `unmatched` refused with the could-not-be-matched sentence,
 *  `absent` not in the rendered text), whether or not the text agrees. */
type Divergence = { name: string; src: string; dom: string; reader: string; why: string; shape?: string; verdicts?: string };

const SHAPES: Shape[] = [
  // test 1: a raw html table's cell boundary
  { name: "a minified raw table: a quote across two cells, across two rows, a single cell", whole: "blanks",
    src: "Intro.\n\n<table><tr><td>cell *a*</td><td>b cell</td></tr><tr><td>c</td><td>d</td></tr></table>\n\npara\n",
    quotes: [{ from: "cell *a*</td><td>b cell", shown: "cell *a* b cell", cells: ["TD0", "TD1"] }, { from: "c</td><td>d", shown: "c d", cells: ["TD0", "TD1"] },
             { from: "b cell</td></tr><tr><td>c", shown: "b cell c", cells: ["TD1", "TD0"] }, { from: "cell *a*", shown: "cell *a*", cells: ["TD0"] }, { from: "b cell", shown: "b cell", cells: ["TD1"] }] },
  { name: "a raw table written with whitespace between its parts", src: "Intro.\n\n<table>\n<tr>\n<td>cell *a*</td>\n<td>b cell</td>\n</tr>\n</table>\n\npara\n",
    quotes: [{ from: "cell *a*</td>\n<td>b cell", shown: "cell *a* b cell", cells: ["TD0", "TD1"] }] },
  { name: "a table part inside a script adds nothing", src: "<div><script><table><tr><td>x</td></tr></table></script>y</div>\n", quotes: [{ from: "y", shown: "y" }] },
  // round 5: no blank at a part's end that no part follows (red at 701728eae: the needle `a2 tail` against a hay of `a1 a2tail`);
  // `shown` is the text test's string for each (`a2tail`, `inout`, `bc`), which the needle compare holds it to since round 6
  { name: "a quote from a cell across the table's end into trailing text", whole: "blanks", src: "<table><tr><td>a1</td><td>a2</td></tr></table>tail\n",
    quotes: [{ from: "a2</td></tr></table>tail", shown: "a2tail", cells: ["TD1", null] }] },
  { name: "a quote out of a nested minified table into its holding cell", whole: "blanks", src: "<table><tr><td><table><tr><td>in</td></tr></table>out</td><td>z</td></tr></table>\n",
    quotes: [{ from: "in</td></tr></table>out", shown: "inout" }] },
  { name: "a stray td in a div, whose tags the parser ignores", src: "<div>a<td>b</td>c</div>\n", quotes: [{ from: "b</td>c", shown: "bc" }] },
  // test 2: svg's foreignObject
  { name: "svg's foreignObject goes with its text in an html block; text and desc keep theirs",
    src: "Intro.\n\n<div><svg viewBox=\"0 0 10 10\"><text>svg text</text><desc>desc text</desc><foreignObject><p>fo text</p></foreignObject></svg></div>\n\npara.\n",
    quotes: [{ from: "<svg", to: "</svg>", shown: "svg textdesc text" }] },
  { name: "svg's foreignObject holding bare text goes with it in an html block (a profile that kept the element would show `fo text` here; one holding a <p> loses it to the namespace check either way)",
    src: "Intro.\n\n<div><svg><text>svg text</text><foreignObject>fo text</foreignObject></svg></div>\n\npara.\n", quotes: [{ from: "<svg>", to: "</svg>", shown: "svg text" }] },
  { name: "svg's foreignObject goes with its text inline", src: "Intro <svg><foreignObject>fo text</foreignObject><text>svg text</text></svg> end\n",
    quotes: [{ from: "<svg>", to: "</svg>", shown: "svg text" }] },
  // test 3: the named character references
  { name: "named references in a centred div", src: "Intro.\n\n<div align=\"center\">Cost &copy; w000 &mdash; done &amp; ok</div>\n\npara.\n",
    quotes: [{ from: "w000 &mdash; done &amp; ok", shown: "w000 " + MDASH + " done & ok" }, { from: "Cost &copy;", shown: "Cost " + COPY }] },
  { name: "a named reference in a heading", src: "# Title &mdash; sub\n\npara.\n", quotes: [{ from: "Title &mdash; sub", shown: "Title " + MDASH + " sub" }] },
  { name: "a named reference in a list item", src: "- item &copy; 2026\n- plain item\n", quotes: [{ from: "item &copy; 2026", shown: "item " + COPY + " 2026" }] },
  { name: "a named reference in a quote", src: "> quote &hellip; more\n", quotes: [{ from: "quote &hellip; more", shown: "quote " + HELLIP + " more" }] },
  { name: "named references in a link's text, strong and em", src: "See [a &mdash; b](http://x.test) and **bold &copy;** and *em &ndash; x* end\n",
    quotes: [{ from: "[a &mdash; b](http://x.test)", shown: "a " + MDASH + " b" }, { from: "**bold &copy;**", shown: "bold " + COPY }, { from: "*em &ndash; x*", shown: "em " + NDASH + " x" }] },
  { name: "named references in a markdown table's header and body cells", whole: "rows", src: "| h &mdash; 1 | h2 |\n|---|---|\n| c &hellip; 1 | c2 |\n",
    quotes: [{ from: "h &mdash; 1", shown: "h " + MDASH + " 1", cells: ["TH0"] }, { from: "c &hellip; 1", shown: "c " + HELLIP + " 1", cells: ["TD0"] }] },
  { name: "named references in a pre", src: "<pre>\nline &amp; one &copy;\n</pre>\n", quotes: [{ from: "line &amp; one &copy;", shown: "line & one " + COPY }] },
  { name: "the rest of the names, in a paragraph", src: "Fish &amp; chips &trade; a &euro; b &rarr; c &times; d &deg; e &frac12; f &laquo;g&raquo; h &middot; i &bull; j &reg; k &lang;l&rang; end\n" },
  { name: "the upper-case aliases and apos", src: "a &AMP; b &COPY; c &LT; d &GT; e &QUOT; f &REG; g &apos; h\n" },
  { name: "the parser's longest legacy match", src: "a &notit; b\n" },
  { name: "the table is case-sensitive", src: "a &Mdash; b &MDASH; c\n" },
  { name: "an unknown name with a legacy head decodes as the parser's legacy prefix and the tail", src: "a &notxyz; b\n", quotes: [{ from: "a &notxyz; b", shown: "a " + NOT + "xyz; b" }] },
  // the review's round 5: a named reference reads as the browser decodes it where a DOM is to hand (red at 701728eae, whose table
  // was HTML 4.01's read with `in`: `&check;` stayed as written, `&ltimes;` read `<imes;`, `&toString;` read Object.prototype's)
  { name: "an HTML5-only name decodes as the browser does", src: "a &check; b &star; c\n", quotes: [{ from: "a &check; b &star; c", shown: "a \u2713 b \u2606 c" }] },
  { name: "an HTML5 name whose head is a legacy name, ltimes and notni", src: "a &ltimes; b &notni; c\n", quotes: [{ from: "a &ltimes; b &notni; c", shown: "a \u22c9 b \u220c c" }] },
  { name: "a name of Object.prototype as a reference stays as written", src: "<div>Block &toString; here</div>\n", quotes: [{ from: "Block &toString; here", shown: "Block &toString; here" }] },
  // test 4: the legacy names with no semicolon
  { name: "legacy names with no semicolon in an html block", src: "Intro.\n\n<div>a &amp b &copy c &reg i &COPY; d &nbsp e &notit; f &amp;amp; g</div>\n\npara.\n",
    quotes: [{ from: "a &amp b &copy c &reg i &COPY; d &nbsp e &notit; f &amp;amp; g", shown: "a & b " + COPY + " c " + REG + " i " + COPY + " d e " + NOT + "it; f &amp; g" }, { from: "&copy c", shown: COPY + " c" }] },
  { name: "legacy names with no semicolon in a paragraph stay as written", src: "a &amp b &copy c &reg i end\n" },
  { name: "a numeric reference with no semicolon in an html block", src: "<div>&#65 u &#x42 v &#; w</div>\n", quotes: [{ from: "&#65 u &#x42 v &#; w", shown: "A u B v &#; w" }] },
  { name: "a numeric reference with no semicolon in a paragraph", src: "&#65 u end\n" },
  // test 5: the numeric reference end state
  { name: "the numeric end state in a paragraph", src: "Fish &amp; &#0; x &#xD800; y &#128; z &#150; w &#x110000; v &#65; u &#x1F600; end\n",
    quotes: [{ from: "&#0; x", shown: REPL + " x" }, { from: "&#xD800; y", shown: REPL + " y" }, { from: "&#128; z", shown: EURO + " z" }, { from: "&#150; w", shown: NDASH + " w" },
             { from: "&#x110000; v", shown: REPL + " v" }, { from: "&#65; u", shown: "A u" }, { from: "&#x1F600; end", shown: SMILE + " end" }] },
  { name: "the numeric end state in an html block", src: "<div>Fish &amp; &#0; x &#xD800; y &#128; z &#150; w &#x110000; v &#65; u &#x1F600; end</div>\n",
    quotes: [{ from: "&#128; z", shown: EURO + " z" }, { from: "&#xD800; y", shown: REPL + " y" }, { from: "&#x1F600; end", shown: SMILE + " end" }] },
  { name: "two astral characters in an html block", src: "<div>a &#x1F600; b &#x1F601; end</div>\n", quotes: [{ from: "a &#x1F600; b &#x1F601; end", shown: "a " + SMILE + " b " + GRIN + " end" }] },
  { name: "the windows-1252 holes", src: "&#129; &#141; &#159;\n" },
  // test 6: an RCDATA element inline
  { name: "a textarea inline in a paragraph shows marked's HTML for the tokens inside", src: "Fish &amp; <textarea>a <b>b</b> *c*</textarea> end\n",
    quotes: [{ from: "a <b>b</b> *c*", shown: "a <b>b</b> <em>c</em>" }, { from: "end", shown: "end" }] },
  { name: "a textarea inline in a cell", whole: "rows", src: "| h |\n|---|\n| x &amp; <textarea>a <b>b</b> *c*</textarea> y |\n",
    quotes: [{ from: "a <b>b</b> *c*", shown: "a <b>b</b> <em>c</em>", cells: ["TD0"] }, { from: "y", shown: "y", cells: ["TD0"] }] },
  { name: "a body title inline in a paragraph: dropped with its content on both sides (round 5), the text after it painting", src: "Lead <title>t &amp; *u*</title> tail\n", quotes: [{ from: "tail", shown: "tail" }] },
  { name: "a textarea in an html block takes no emphasis", src: "<div><textarea>d <i>e</i> *f*</textarea> tail</div>\n", quotes: [{ from: "d <i>e</i> *f*", shown: "d <i>e</i> *f*" }] },
  // test 7: svg's title
  { name: "an svg title closed by the svg's end tag", src: "Intro.\n\n<div><svg><title>inner title</svg> beside</div>\n\npara.\n",
    quotes: [{ from: "inner title</svg> beside", shown: "inner title beside" }] },
  { name: "an svg title closed by its own end tag", src: "Intro.\n\n<div><svg><title>inner title</title><text>t</text></svg> beside</div>\n\npara.\n" },
  { name: "a textarea in HTML content reads an svg end tag as text", src: "<div><textarea>x</svg> y</textarea> z</div>\n" },
  { name: "a style inside an svg goes with its text", src: "<div><svg><style>.a{}</style><text>t</text></svg> z</div>\n" },
  // round 5: inline too (red at 701728eae: the title's text ran to the svg's end tag, tags and all, `icon</svg> beside`); since decision 52
  // (md-literal-tags.ts) a `<title>` with no end tag of its own is literal text, svg text in the DOM, on both sides
  { name: "an svg title start tag inline with no end tag of its own before the svg's end tag: literal text on both sides", src: "Intro <svg><title>icon</svg> beside end\n", quotes: [{ from: "icon</svg> beside", shown: "icon beside" }] },
  // the round 5 finder's shapes, whole text alone
  { name: "a hex numeric reference with no semicolon in an html block", src: "<div>a &#x1F600 b</div>\n" },
  { name: "legacy names with digits, no semicolon", src: "<div>&frac12 x &sup2 y &AElig z</div>\n" },
  { name: "a legacy prefix with a semicolon tail", src: "<div>&ampx; y</div>\n" },
  { name: "notin against noti", src: "<div>&notin; a &noti; b</div>\n" },
  { name: "a textarea inside emphasis", src: "*em <textarea>a *b* c</textarea> end*\n" },
  { name: "a textarea holding a code span", src: "Lead <textarea>a `code` b</textarea> tail\n" },
  { name: "a title holding a link", src: "Lead <title>see [x](http://a.test) now</title> tail\n" },
  { name: "a reference in an attribute is no text", src: "<div title=\"&copy;\">a &copy; b</div>\n" },
  { name: "a textarea in a heading", src: "# Head <textarea>a *b*</textarea> tail\n" },
  { name: "an end tag in upper case", src: "Lead <textarea>a</TEXTAREA> tail\n" },
  { name: "a legacy name run into letters", src: "<div>&copyx y &ltz w</div>\n" },
  { name: "a semicolon-less legacy name at the block's end", src: "<div>a &copy</div>\n" },
  { name: "a list item and a quote", src: "- item &copy; 2026\n- plain\n\n> quote &hellip; more\n" },
  { name: "a tab and a newline by reference", src: "<div>a&#9;b&#10;c</div>\n" },
  { name: "a textarea holding a comment", src: "Lead <textarea>a <!-- c --> b</textarea> tail\n" },
  { name: "a title holding a reference alone", src: "Lead <title>&amp;</title> tail\n" },
  { name: "two textareas in one paragraph", src: "A <textarea>x *y*</textarea> B <textarea>z *w*</textarea> C\n" },
  // round 5: a title block the document begins with shows nothing (the parser puts it in the head), and the reader reads nothing
  // of it either (red at 701728eae, where it read `Doc title Para.`)
  { name: "a title block the document begins with", src: "<title>Doc title</title>\n\nPara.\n", quotes: [{ from: "Para.", shown: "Para." }] },
  // round 6 (the rules pinned in anchor-map-html-rules.test.ts tests 7 and 8, red over a git archive of 8924fa17e): a `<style>` between
  // two cells of a minified raw table goes with its text and leaves the cells adjacent, a `<br>` there is foster-parented before the
  // table, so the hay's blank stands between the cells in both (round 5 looked past whitespace and comments alone and read the cells
  // run together); and an HTML element left open inside a `<foreignObject>` at `</svg>` keeps the parser from closing the svg, so the
  // rest of the passage stays inside the dropped foreignObject and the paint shows `Intro` alone (round 5 read ` y` as shown text)
  { name: "a style between two cells of a minified raw table", whole: "blanks", src: "<div><table><tr><td>s1</td><style>td{}</style><td>s2</td></tr></table></div>\n",
    quotes: [{ from: "s1</td><style>td{}</style><td>s2", shown: "s1 s2", cells: ["TD0", "TD1"] }] },
  { name: "a br between two cells of a minified raw table, foster-parented before it", whole: "blanks", src: "<table><tr><td>a1</td><br><td>a2</td></tr></table>\n",
    quotes: [{ from: "a1</td><br><td>a2", shown: "a1 a2", cells: ["TD0", "TD1"] }] },
  // since decision 52 (md-literal-tags.ts) the foreignObject and the b, with no end tags of their own in the block, are literal text: svg
  // text in the DOM, the svg closed by its end tag, ` y` shown on both sides (before: `Intro` alone, the parser's element left open)
  { name: "a foreignObject and a b with no end tags of their own before the svg's end tag, inline: literal text on both sides", src: "Intro <svg><foreignObject><b>x</svg> y\n",
    quotes: [{ from: "Intro", to: " y", shown: "Intro <foreignObject><b>x y" }] },
  // round 7 (anchor-map-html-rules.test.ts tests 9 to 13, red over a git archive of 78c0806ce): a raw table written without its end tags,
  // whose implied ends leave the cells adjacent exactly as written end tags do (the blank was put at a part's END tag alone); a dropped
  // element WITH text between two cells, removed whole and leaving the cells adjacent (its text ended the look past it); a raw-text or
  // dropped element written `/>`, which the parser opens (read as a leaf); the parser's implied end tags inside a foreignObject, so a
  // `<p>` closed by the next `<p>` does not keep `</svg>` ignored (every start tag was kept open until its own end tag); and MathML's
  // integration points and an svg's title read as the foreignObject is (an element left open inside `<annotation-xml>` or `<mtext>`
  // kept `</math>` ignored in the parser and not in the reader)
  { name: "a raw table written without its end tags: a quote across two cells and across two rows", whole: "blanks",
    src: "Intro.\n\n<div><table><tr><td>ri1 a<td>ri2 b<tr><td>ri3 c<td>ri4 d</table></div>\n\npara ri5.\n",
    quotes: [{ from: "ri1 a<td>ri2 b", shown: "ri1 a ri2 b", cells: ["TD0", "TD1"] }, { from: "ri2 b<tr><td>ri3 c", shown: "ri2 b ri3 c", cells: ["TD1", "TD0"] }, { from: "ri4 d", shown: "ri4 d", cells: ["TD1"] }] },
  { name: "a README's raw table with the cells' end tags omitted", whole: "blanks", src: "Intro.\n\n<table><tr><td>Flag<td>Meaning</tr></table>\n\npara.\n",
    quotes: [{ from: "Flag<td>Meaning", shown: "Flag Meaning", cells: ["TD0", "TD1"] }] },
  { name: "header cells and a body opened without end tags", whole: "blanks", src: "<table><thead><tr><th>H1<th>H2<tbody><tr><td>x1<td>x2</table>\n",
    quotes: [{ from: "H1<th>H2", shown: "H1 H2", cells: ["TH0", "TH1"] }, { from: "H2<tbody><tr><td>x1", shown: "H2 x1", cells: ["TH1", "TD0"] }, { from: "x1<td>x2", shown: "x1 x2", cells: ["TD0", "TD1"] }] },
  { name: "a noscript with text between two cells of a minified raw table, removed whole", whole: "blanks", src: "<div><table><tr><td>bf1</td><noscript>js off</noscript><td>bf2</td></tr></table></div>\n",
    quotes: [{ from: "bf1</td><noscript>js off</noscript><td>bf2", shown: "bf1 bf2", cells: ["TD0", "TD1"] }] },
  { name: "a math with text between two cells, foster-parented before the table and removed whole", whole: "blanks", src: "<div><table><tr><td>bf1</td><math><mi>x</mi></math><td>bf2</td></tr></table></div>\n",
    quotes: [{ from: "bf1</td><math><mi>x</mi></math><td>bf2", shown: "bf1 bf2", cells: ["TD0", "TD1"] }] },
  { name: "an svg whose only content is a foreignObject with text between two cells", whole: "blanks", src: "<div><table><tr><td>bf1</td><svg><foreignObject>fo</foreignObject></svg><td>bf2</td></tr></table></div>\n",
    quotes: [{ from: "bf1</td><svg><foreignObject>fo</foreignObject></svg><td>bf2", shown: "bf1 bf2", cells: ["TD0", "TD1"] }] },
  { name: "a textarea written `/>` in an html block opens and shows the raw's rest as its text", src: "<div>lead <textarea/> in <b>bold</b> wrap</div>\n",
    quotes: [{ from: "in <b>bold</b> wrap", shown: "in <b>bold</b> wrap" }] },
  { name: "a noscript written `/>` in a paragraph opens and drops the paragraph's rest, closed by the paragraph's end tag", src: "Intro <noscript/> after\n\nPara.\n", quotes: [{ from: "Para.", shown: "Para." }] },
  { name: "a p closed by the next p inside a foreignObject: the svg closes and the text after it shows", src: "Intro <svg><foreignObject><p>a<p>b</p></foreignObject></svg> y\n",
    quotes: [{ from: "Intro", to: " y", shown: "Intro y" }, { from: " y", shown: "y" }] },
  { name: "an li closed by the next li inside a foreignObject", src: "Intro <svg><foreignObject><li>a<li>b</li></foreignObject></svg> y\n", quotes: [{ from: " y", shown: "y" }] },
  { name: "a p closed by a div inside a foreignObject in an html block", src: "Intro.\n\n<div><svg><foreignObject><p>a<div>b</div></foreignObject></svg> y</div>\n\npara\n", quotes: [{ from: " y", shown: "y" }] },
  // since decision 52 (md-literal-tags.ts) an integration point or a b with no end tag of its own is literal text, so the math closes at its
  // end tag and is dropped whole with the text inside it, and the tail shows on both sides (before: the parser's element left open kept
  // `</math>` ignored, `ma2` alone)
  { name: "an annotation-xml with the html encoding and a b, neither with an end tag of its own: literal text inside the dropped math, the tail shown", src: "ma2 <math><annotation-xml encoding=\"text/html\"><b>x</math> y2\n", quotes: [{ from: "ma2", to: "y2", shown: "ma2 y2" }] },
  { name: "an mtext and a b with no end tags of their own: the same", src: "ma5 <math><mtext><b>x</math> y5\n", quotes: [{ from: "ma5", to: "y5", shown: "ma5 y5" }] },
  { name: "a title and a b with no end tags of their own inside an svg: literal text, svg text in the DOM, the svg closed", src: "Intro <svg><title><b>x</svg> y\n", quotes: [{ from: "Intro", to: " y", shown: "Intro <title><b>x y" }] },
  // decision 52's two agreements that were the plan's recorded divergences before it (RECORDED below kept the `/>` forms): a `<textarea>` with
  // no end tag in its block is literal text and the tokens after it prose on both sides, where the parser used to read the block's rest as
  // the textarea's text; an `<annotation-xml>` whose encoding value carries a blank and a `<b>` with no end tags are literal text inside the
  // dropped math on both sides, where the parser used to break out of the math at the `<b>` and show `x`
  { name: "an inline textarea start tag with no end tag in its block: literal text on both sides", src: "Lead <textarea>open *x* tail\n", quotes: [{ from: "Lead", to: "tail", shown: "Lead <textarea>open x tail" }] },
  { name: "an annotation-xml whose encoding has a trailing blank and a b, neither closed: literal text inside the dropped math on both sides", src: "ma8 <math><annotation-xml encoding=\"text/html \"><b>x</math> y8\n", quotes: [{ from: "ma8", to: "y8", shown: "ma8 y8" }] },
  { name: "an HTML element closed inside an svg title is the sanitizer's to remove with its text; the svg closes", src: "Intro <svg><title>t<b>x</b>u</title></svg> y\n", quotes: [{ from: " y", shown: "y" }] },
  // round 8 (anchor-map-html-rules.test.ts tests 14 and 15, red over a git archive of 99e7e2d0c): a raw table marked splits into two html
  // blocks at a blank line, one table to the parser, whose second block continues the first's row and cells (the reader's table frames
  // were the block's own, so the second block's cells read run together and a quote across them painted nothing); and `<mglyph>` and
  // `<malignmark>` inside a MathML text element, which the parser keeps foreign, so the math closes (the reader recorded them as HTML
  // elements left open and dropped the block's rest)
  { name: "a raw table whose rows marked splits into two html blocks at a blank line", whole: "blanks", src: "Intro.\n\n<table>\n<tr><td>a1<td>a2\n\n<tr><td>b1<td>b2\n</table>\n\npara.\n",
    quotes: [{ from: "b1<td>b2", shown: "b1 b2", cells: ["TD0", "TD1"] }, { from: "a1<td>a2", shown: "a1 a2", cells: ["TD0", "TD1"] }] },
  { name: "an mglyph self-closed inside an mi: foreign content, so the math closes and the text after it shows", src: "ma9 <math><mi><mglyph/></mi></math> y9\n", quotes: [{ from: "ma9", to: "y9", shown: "ma9 y9" }] },
  { name: "a malignmark start tag inside an mtext", src: "ma9 <math><mtext><malignmark></mtext></math> y9\n", quotes: [{ from: "ma9", to: "y9", shown: "ma9 y9" }] },
  // decision 52's open-array sentence, executed, not pinned (the closing check of PR 804, 2026-09-19; the SHAPES loop asserts the text and
  // the paints, not the tags or the verdicts): an `image` start tag with no end tag is
  // the alias the rule leaves HTML (IMG_ALIAS), and inside an inline svg it is the svg's own element, closed by `</svg>` (the top-level
  // tags `P[svg[image]] H2 P P`), so the text agrees and every block maps, the tag's paragraph included; the same tags and the map's
  // verdict `maps` for each passage over the base tree c25a2b319
  { name: "an image inside an inline svg left open: the svg's own element, closed by the svg's end tag, and every block maps", src: "Lead <svg><image href=\"a.png\"></svg> tail t1.\n\n## Second heading t2\n\nPara after the heading t3.\n\nClosing words t4.\n",
    quotes: [{ from: "tail t1", shown: "tail t1" }, { from: "Second heading t2", shown: "Second heading t2" }, { from: "Para after the heading t3", shown: "Para after the heading t3" }, { from: "Closing words t4", shown: "Closing words t4" }] },
];

const MISMATCH = "This selection touches a block whose rendered text does not match the file; comment on it from the Raw view.";
const UNMATCHED = "The selection could not be matched to the file text.";
/** The passages of a recorded note (noteWith), in order: the tag's paragraph's tail, then a heading and two paragraphs after it. */
const LATER = ["tail t1", "Second heading t2", "Para after the heading t3", "Closing words t4"];
const noteWith = (tag: string): string => `Lead ${tag} tail t1.\n\n## Second heading t2\n\nPara after the heading t3.\n\nClosing words t4.\n`;
const NOTE_TEXT = "Lead tail t1. Second heading t2 Para after the heading t3. Closing words t4.";
const FO_TEXT = "Lead <foreignObject>x tail t1. Second heading t2 Para after the heading t3. Closing words t4.";
const DESC_TEXT = "Lead <desc>x tail t1. Second heading t2 Para after the heading t3. Closing words t4.";

/** The plan's recorded divergences (plans/markdown-viewer.md, the Slice 5 build note, item 4), pinned on both sides. The first of them, an
 *  inline `<textarea>` left open, is an agreement since decision 52 (SHAPES above): a start tag with no end tag in its block is literal text
 *  on both sides. The `/>` forms keep the divergence: the self-closing syntax stays HTML, which the parser opens. */
const RECORDED: Divergence[] = [
  // round 7: the `/>` forms, which open (both sides read the block's rest as the element's; the parser reads on)
  { name: "a title written `/>` in a paragraph drops the block's rest, and the parser every later block", src: "Intro.\n\nPara sc1 <title/> after sc2.\n\nPara sc3 more sc4.\n\nend sc5.\n", dom: "Intro. Para sc1", reader: "Intro. Para sc1 Para sc3 more sc4. end sc5.",
    why: "the parser's title runs to the document's end and the sanitizer drops it whole; the reader drops the block's rest alone" },
  { name: "a textarea written `/>` in a paragraph shows the block's rest as marked's HTML, and the parser every later block's too", src: "Para se1 <textarea/> after *em* se2.\n\nPara se3.\n", dom: "Para se1 after <em>em</em> se2.</p> <p>Para se3.</p>", reader: "Para se1 after <em>em</em> se2. Para se3.",
    why: "the parser's textarea runs to the document's end, which the DOM then shows as text; the reader reads the block's rest so" },
  // round 8's breakout divergence (an annotation-xml whose encoding value carries a blank, the `<b>` inside it breaking out of the math) is
  // an agreement since decision 52, in SHAPES above: with no end tags of their own, both tags are literal text inside the dropped math.
  // The breakout class itself stands, and decision 52 moves one shape into it: an `<annotation-xml>` with no end tag of its own is text
  // now, so the closed `<b>` after it stands in the math's foreign content with no integration point around it, and the parser breaks
  // out of the math at the `<b>` and shows its text, where the reader reads the b as the root's content and drops it with the math
  // (before decision 52 both sides read `ma6 y6`: the annotation-xml was the parser's integration point and the b HTML inside it)
  { name: "an HTML element closed inside an annotation-xml with the html encoding, the annotation-xml itself not closed: the b breaks out", src: "ma6 <math><annotation-xml encoding=\"text/html\"><b>x</b></math> y6\n", dom: "ma6 x y6", reader: "ma6 y6",
    why: "the parser breaks out of foreign content at the `<b>` and shows its text; the reader drops the math whole and reads on, the recorded class" },
  // the class that entry belongs to, since decision 52 (the review of PR 804, round 1; bounded again by its closing check, 2026-09-19):
  // an integration point of an INLINE `<math>` left open (`<mtext>`, `<mi>`, `<mo>`, `<mn>` or `<ms>`, or an `<annotation-xml>` with
  // the html or the xhtml encoding) is literal text now, so an HTML element after it whose start tag is on the parser's foreign-content
  // breakout list (the 44 names the HTML standard lists there, and `font` when it carries `color`, `face` or `size`) stands in the
  // math's foreign content with no integration point around it: the parser breaks out of the math at it, whether the tag is closed,
  // self-closed or void, and shows its text, and the reader drops the math whole (executed in Chromium for `<b>`, `<i>`, `<em>`,
  // `<strong>`, `<span>`, `<code>`, `<sub>`, `<sup>`, `<small>`, `<big>`, `<tt>`, `<u>`, `<s>`, `<strike>`, `<nobr>`, `<var>`,
  // `<ruby>`, `<div>`, `<p>`, `<h2>`, `<pre>`, `<blockquote>`, `<center>`, `<menu>`, `<listing>`, a `<ul>`, an `<ol>`, a `<dl>` and a
  // `<table>`, each with its end tag: the DOM `ma7 x y7`, the reader `ma7 y7`, no paint mark; for `<br>`, `<img>` and `<hr>` with no
  // end tag, for `<b/>` written with the flag, and for `<font color="red">x</font>`, by the DOM's top-level tags in the entries below).
  // Not in the class: a closed element whose start tag is not on that list (`<kbd>`, `<a>`, `<abbr>`, `<mark>`, `<q>`, `<cite>`,
  // `<dfn>`, `<samp>`, `<ins>`, `<del>`, `<label>`, `<time>`, `<button>`, `<section>` and their kind, and a `<font>` with none of the
  // three attributes) goes with the dropped math on both sides (the sanitized paragraph `ma7  y7`, two marks); and a `<math>` inside
  // an html block, whose tags the rule does not read (the `<mtext>` stays the parser's integration point and the `<b>` HTML inside it,
  // `ma7 y7` on both sides). Inside an inline `<svg>` the TEXT agrees for a member, since the sanitizer keeps svg text
  // (`sv1 <svg><title><b>x</b></svg> y1` reads `sv1 <title>x y1` on both sides, the `b` broken out into the paragraph, `P[svg,B]`, and
  // every block mapping), and the MAP does not for a block-level member: a closed `<div>` or `<p>` after a `<title>`, `<desc>` or
  // `<foreignObject>` left open splits the paragraph (`P[svg] DIV P`, `P[svg] P P`) and every later block is refused, where at the base
  // tree the element sat inside the integration point, a scope boundary, and every later block mapped; the same split after an
  // `<mtext>`; and an out-of-class element there (`<kbd>`) stays in the drawing and the sanitizer removes it with its text, which the
  // reader keeps, a text divergence. Those are the entries after the two text representatives, each with the DOM's top-level tags and
  // the map's verdicts over LATER, since this suite compares text and text alone would not see a split. The `<title>` half of the svg split
  // is prose here, executed and not pinned (`noteWith("<svg><title><div>x</div></svg>")` over 58bb100fc's code: `P[svg] DIV P H2 P P`, mismatch
  // unmatched unmatched unmatched): tools/markdown-viewer-plan-decision52-pointers.test.mjs refuses a `<textarea>`, `<plaintext>`, `<title>` or
  // `<noscript>` written without the self-closing syntax in a RECORDED src, since such a tag left open is literal text since decision 52 and
  // cannot itself be a recorded divergence, and the svg-title shape's divergence is the div's breakout, which the guard cannot tell from a
  // title left open, so the split is pinned through `<foreignObject>` and `<desc>`. Before decision 52 every member
  // agreed: the integration point was the parser's element and the closed element HTML inside it, `ma5 y5` and `ma7 y7` on both sides
  // with two paint marks over the PR's base tree (c25a2b319). A paragraph holding an inline `<math>` with text inside it is refused with
  // the mismatch sentence on both trees whatever follows the integration point (`<math><mi>x</mi></math>` too; `<math></math>` maps),
  // so an entry's verdicts differ from the base tree's in the later blocks, and in the tag's paragraph only where the math held no text
  // (`<br>`, `<img>`, `<hr>` and `<b/>`). anchor-map-html-rules.test.ts pins the reader's side of the first representative.
  { name: "an mtext and a first p left open inside an inline math, then `<p>b</p>` closed: the closed p breaks out of the math", src: "ma5 <math><mtext><p>a<p>b</p></math> y5\n", dom: "ma5 b y5", reader: "ma5 y5",
    why: "the mtext and the first p, with no end tags of their own, are literal text inside the math; the closed `<p>b</p>` stands in the math's foreign content with no integration point around it, so the parser breaks out at it and shows `b`, where the reader drops the math whole (before decision 52: `ma5 y5` on both sides)" },
  { name: "an mtext left open inside an inline math, then a closed b: the b breaks out of the math", src: "ma7 <math><mtext><b>x</b></math> y7\n", dom: "ma7 x y7", reader: "ma7 y7",
    why: "the same class: the closed `<b>` stands in the math's foreign content with no integration point around it, and the parser breaks out at it and shows `x`, where the reader drops the math whole (before decision 52: `ma7 y7` on both sides)" },
  // the closing check's entries (2026-09-19), each RECORDED by the DOM's top-level tags and the map's verdicts over LATER, the text pinned
  // too; the base tree's shape and verdicts in each `why` are from the same probe over a git archive of c25a2b319
  { name: "a br inside an mtext left open, a void member of the class: breaks out with no closing into the paragraph, whose passage is refused, a refusal new at decision 52", src: noteWith("<math><mtext><br></math>"), dom: NOTE_TEXT, reader: NOTE_TEXT, shape: "P[BR] H2 P P", verdicts: "mismatch maps maps maps",
    why: "the mtext is literal text, so the br stands in the math's foreign content with no integration point around it and the parser breaks out at it: a line break in the paragraph, the text unchanged, and the tag's paragraph refused with the mismatch sentence; at the base tree the br sat inside the mtext, `P H2 P P`, and every passage mapped" },
  { name: "an img inside an mtext left open, a void member: the same, a picture in the paragraph, a refusal new at decision 52", src: noteWith('<math><mtext><img src="a.png"></math>'), dom: NOTE_TEXT, reader: NOTE_TEXT, shape: "P[IMG] H2 P P", verdicts: "mismatch maps maps maps",
    why: "the img breaks out of the math into the paragraph, the text unchanged, and the tag's paragraph is refused with the mismatch sentence; at the base tree `P H2 P P`, every passage mapped" },
  { name: "an hr inside an mtext left open, a void member that closes the paragraph: every later block refused, a refusal new at decision 52", src: noteWith("<math><mtext><hr></math>"), dom: NOTE_TEXT, reader: NOTE_TEXT, shape: "P HR P H2 P P", verdicts: "mismatch unmatched unmatched unmatched",
    why: "the hr breaks out of the math and closes the open p, so the paragraph's tail stands in an extra top-level element: the tag's paragraph is refused with the mismatch sentence and every later block with the could-not-be-matched sentence; at the base tree `P H2 P P`, every passage mapped (the same after an mi or an xhtml annotation-xml in place of the mtext)" },
  { name: "a b written `/>` inside an mtext left open, a self-closed member: breaks out and opens, a wrapper around every later block, every passage refused, a refusal new at decision 52", src: noteWith("<math><mtext><b/></math>"), dom: NOTE_TEXT, reader: NOTE_TEXT, shape: "P[B] B[H2,P,P]", verdicts: "mismatch mismatch mismatch mismatch",
    why: "the parser ignores the flag on an HTML element, so the b breaks out of the math and stays open, reopened after the paragraph around every later block, and every passage is refused with the mismatch sentence; at the base tree the b stayed open inside the mtext and the page showed `Lead` alone, `P`, every passage absent" },
  { name: "a font with a color attribute inside an mtext left open, the member the list bounds by attribute: breaks out, its text shown, where a bare font goes with the math, a text divergence new at decision 52", src: noteWith('<math><mtext><font color="red">x</font></math>'), dom: "Lead x tail t1. Second heading t2 Para after the heading t3. Closing words t4.", reader: NOTE_TEXT, shape: "P[FONT] H2 P P", verdicts: "mismatch maps maps maps",
    why: "the breakout list holds `font` only when it carries `color`, `face` or `size`: with `color` the font breaks out of the math into the paragraph and shows `x`, where the reader drops the math whole; `<font>x</font>` with no attribute stays in the foreign content and goes with the math, `P H2 P P` and the text agreeing; at the base tree `P H2 P P`, the text agreeing, the tag's paragraph refused the same and every later block mapped" },
  { name: "a closed div inside an mtext left open, a block-level member: splits the paragraph, every later block refused, a refusal new at decision 52", src: noteWith("<math><mtext><div>x</div></math>"), dom: "Lead x tail t1. Second heading t2 Para after the heading t3. Closing words t4.", reader: NOTE_TEXT, shape: "P DIV P H2 P P", verdicts: "mismatch unmatched unmatched unmatched",
    why: "the closed div breaks out of the math and closes the open p, its text shown; the tag's paragraph is refused with the mismatch sentence and every later block with the could-not-be-matched sentence; at the base tree `P H2 P P`, the tag's paragraph refused the same and every later block mapped" },
  { name: "a closed div inside an svg foreignObject left open, a block-level member: splits the paragraph, the text agreeing, every later block refused, a refusal new at decision 52", src: noteWith("<svg><foreignObject><div>x</div></svg>"), dom: FO_TEXT, reader: FO_TEXT, shape: "P[svg] DIV P H2 P P", verdicts: "mismatch unmatched unmatched unmatched",
    why: "the foreignObject is literal svg text, so the closed div breaks out of the svg and closes the open p; the DOM and the reader read the same text, the tag's paragraph is refused with the mismatch sentence and every later block with the could-not-be-matched sentence; at the base tree the div sat inside the foreignObject, `P[svg] H2 P P`, the tag's paragraph refused the same and every later block mapped" },
  { name: "a closed p inside an svg foreignObject left open: the same split, a refusal new at decision 52", src: noteWith("<svg><foreignObject><p>x</p></svg>"), dom: FO_TEXT, reader: FO_TEXT, shape: "P[svg] P P H2 P P", verdicts: "mismatch unmatched unmatched unmatched",
    why: "the closed p breaks out of the svg and closes the open p, a paragraph of its own; at the base tree `P[svg] H2 P P`, the tag's paragraph refused the same and every later block mapped" },
  { name: "a closed div inside an svg desc left open: the same split, a refusal new at decision 52", src: noteWith("<svg><desc><div>x</div></svg>"), dom: DESC_TEXT, reader: DESC_TEXT, shape: "P[svg] DIV P H2 P P", verdicts: "mismatch unmatched unmatched unmatched",
    why: "the desc is literal svg text and the closed div breaks out of the svg; at the base tree the div sat inside the desc, `P[svg[desc]] H2 P P`, the tag's paragraph refused the same and every later block mapped" },
  { name: "a closed kbd inside an svg foreignObject left open, out of the class: stays in the drawing and the sanitizer removes it with its text, which the reader keeps, a text divergence new at decision 52 (the tag's paragraph's refusal is on both trees)", src: noteWith("<svg><foreignObject><kbd>x</kbd></svg>"), dom: "Lead <foreignObject> tail t1. Second heading t2 Para after the heading t3. Closing words t4.", reader: FO_TEXT, shape: "P[svg] H2 P P", verdicts: "mismatch maps maps maps",
    why: "no breakout: the kbd is an element of the svg's namespace, which the sanitizer's namespace check removes with its text, where the reader reads the text as the drawing's; the tag's paragraph is refused with the mismatch sentence (at the base tree too, `Lead tail t1.` on both sides there, `P[svg] H2 P P`) and every later block maps; an `<a>`, an svg name, is kept with its text and every passage maps" },
];

/** marked with the viewer's configuration, the real md-sanitize.ts and the real anchor-map.ts, bundled for a page: __probe
 *  renders `src` as mdBlock does and returns the box's text, the reader's, and each quote's real paint over a fresh box. */
function bundleProbe(): string {
  const esbuild = requireCjs("esbuild");
  const contents = [
    'import { applyMdConfig } from "./md-config";',
    'import { sanitizeMd } from "./md-sanitize";',
    'import { viewerHtml } from "./file-view";',
    'import { stripMarkupMapped, renderedQuote, paintRendered, mapRenderedSelection } from "./anchor-map";',
    'const MISMATCH = ' + JSON.stringify(MISMATCH) + ';',
    'const UNMATCHED = ' + JSON.stringify(UNMATCHED) + ';',
    "applyMdConfig();",
    // mdBlock's parse (file-view.ts viewerHtml: marked's lexer, the literal-tags rule of md-literal-tags.ts, marked's parser), then the sanitizer
    "(window as any).__probe = (src: string, quotes: Array<{ from: string; to?: string }>, needles: string[]) => {",
    "  const render = () => { const box = document.createElement('div'); box.className = 'fileview-md';",
    "    box.replaceChildren(...Array.from(sanitizeMd(viewerHtml(src)).childNodes)); document.body.append(box); return box; };",
    "  const box = render(); const dom = box.textContent || '';",
    // the DOM's top-level tags, and each needle's verdict from the map over a real Selection on the first text node holding it
    "  const shapeOf = (el: Element): string => { const kids = Array.from(el.children); return el.tagName + (kids.length ? '[' + kids.map(shapeOf).join(',') + ']' : ''); };",
    "  const shape = Array.from(box.children).map(shapeOf).join(' ');",
    "  const walker = document.createTreeWalker(box, NodeFilter.SHOW_TEXT); const texts: Text[] = [];",
    "  for (let n = walker.nextNode(); n; n = walker.nextNode()) texts.push(n as Text);",
    "  const verdicts = needles.map((needle) => {",
    "    const t = texts.find((x) => x.data.includes(needle));",
    "    if (!t) return 'absent';",
    "    const range = document.createRange(); const i = t.data.indexOf(needle); range.setStart(t, i); range.setEnd(t, i + needle.length);",
    "    const sel = window.getSelection() as Selection; sel.removeAllRanges(); sel.addRange(range);",
    "    const r = mapRenderedSelection(sel, box, src); sel.removeAllRanges();",
    "    if (r.ok) { const start = src.indexOf(needle); return r.range.start === start && r.range.end === start + needle.length ? 'maps' : 'maps elsewhere: ' + JSON.stringify(r.range); }",
    "    return r.reason === MISMATCH ? 'mismatch' : r.reason === UNMATCHED ? 'unmatched' : 'refused: ' + r.reason;",
    "  });",
    "  box.remove();",
    "  const reader = stripMarkupMapped(src);",
    "  const paints = quotes.map((q) => {",
    "    const t = q.to === undefined ? q.from : q.to; const a = src.indexOf(q.from); const b = a < 0 ? -1 : src.indexOf(t, a);",
    "    if (a < 0 || b < 0) return { error: 'not in the source: ' + q.from + ' .. ' + t };",
    "    const range = { start: a, end: b + t.length }; const bx = render();",
    "    const marks = (paintRendered(bx, src, range, 'fc-hl') || []) as Element[];",
    "    const text = marks.map((m) => m.textContent || '').join('');",
    "    const cells = marks.map((m) => { const td = m.closest('td,th'); return td ? td.tagName + Array.from((td.parentElement as Element).children).indexOf(td) : null; });",
    "    bx.remove(); return { needle: renderedQuote(src, range), marks: marks.length, text, cells };",
    "  });",
    "  return { dom, reader: reader.text, mapLen: reader.map.length, paints, shape, verdicts };",
    "};",
  ].join("\n");
  const r = esbuild.buildSync({
    stdin: { contents, resolveDir: UI, loader: "ts", sourcefile: "anchor-map-html-text-probe.ts" },
    bundle: true, write: false, format: "iife", platform: "browser", target: "es2020",
    nodePaths: [path.join(EXT, "node_modules")], logLevel: "silent",
  });
  return r.outputFiles[0].text;
}
const PAGE = `<!DOCTYPE html><html><head><meta charset=utf-8></head><body><script src=/probe.js></script></body></html>`;

/** A markdown table's delimiter row (`|---|---|`, `| :-- | --: |`), the row the reader keeps as its dashes and no rendered text holds. */
const DELIMITER_ROW = /^\s*\|?\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*$/;
/** The reader's text less each delimiter row of `src`, one occurrence per row, so a markdown table compares with the DOM. */
function lessDelimiterRows(reader: string, src: string): string {
  let out = reader;
  for (const line of src.split("\n")) if (DELIMITER_ROW.test(line) && line.includes("-")) out = out.replace(line.trim(), " ");
  return out;
}

type Paint = { error?: string; needle: string; marks: number; text: string; cells: (string | null)[] };
type Probe = { dom: string; reader: string; mapLen: number; paints: Paint[]; shape: string; verdicts: string[] };

let pw: any = null;
try { pw = requireCjs("playwright"); } catch { pw = null; }

test("in a browser, over the viewer's pipeline: the fallback reader's text for every html-text shape matches the DOM's, each quote paints over the real DOM reading the text the text test pins, and the recorded divergence stands as pinned", { timeout: 120000 }, async (t) => {
  if (!pw) { t.skip("playwright is not installed under vscode-extension; the browser leg needs it (CI installs no browsers)"); return; }
  let browser: any;
  try { browser = await pw.chromium.launch(); }
  catch (e) { t.skip("no playwright browser on this box; the browser leg needs one (CI installs none): " + String((e as Error).message).split("\n")[0]); return; }
  const errors: string[] = [];
  try {
    const probeJs = bundleProbe();
    const page = await browser.newPage({ viewport: { width: 900, height: 600 } });
    page.on("pageerror", (e: Error) => { errors.push(e.message); });
    await page.route("**/*", (route: any) => {
      const u = new URL(route.request().url());
      if (u.host !== "romp.test") return route.fulfill({ status: 404, body: "" });
      if (u.pathname === "/") return route.fulfill({ status: 200, contentType: "text/html; charset=utf-8", body: PAGE });
      if (u.pathname === "/probe.js") return route.fulfill({ status: 200, contentType: "application/javascript", body: probeJs });
      return route.fulfill({ status: 404, body: "" });
    });
    await page.goto("http://romp.test/");
    await page.waitForFunction(() => typeof (window as any).__probe === "function", null, { timeout: 10000 });
    const probe = (src: string, quotes: Array<{ from: string; to?: string }>, needles: string[] = []): Promise<Probe> =>
      page.evaluate(([s, q, n]: [string, Array<{ from: string; to?: string }>, string[]]) => (window as any).__probe(s, q, n), [src, quotes, needles] as [string, Array<{ from: string; to?: string }>, string[]]);

    for (const s of SHAPES) {
      await t.test(s.name, async () => {
        const r = await probe(s.src, (s.quotes || []).map((q) => ({ from: q.from, to: q.to })));
        assert.equal(r.mapLen, r.reader.length, "one map entry per code unit of the reader's text");
        if (s.whole === "blanks") assert.equal(nows(r.reader), nows(r.dom), "the whole text, whitespace aside (the hay's blank between two adjacent table parts is no node)");
        else if (s.whole === "rows") assert.equal(norm(lessDelimiterRows(r.reader, s.src)), norm(r.dom), "the whole text, the delimiter rows taken out of the reader's");
        else assert.equal(norm(r.reader), norm(r.dom), "the whole text, whitespace-normalized");
        (s.quotes || []).forEach((q, i) => {
          const p = r.paints[i], what = JSON.stringify(q.to === undefined ? q.from : q.from + " .. " + q.to);
          assert.equal(p.error, undefined, what + ": " + p.error);
          assert.equal(norm(p.needle), norm(q.shown), what + ": the reader's needle is the shown text (as the text test pins it, normalized)");
          assert.ok(p.marks > 0, what + ": the paint over the real DOM wraps something (needle " + JSON.stringify(p.needle) + ")");
          assert.equal(nows(p.text), nows(q.shown), what + ": the marks read the shown text");
          if (q.cells) assert.deepEqual(p.cells, q.cells, what + ": the marks sit in the cells named");
        });
      });
    }
    for (const d of RECORDED) {
      await t.test("recorded: " + d.name, async () => {
        const r = await probe(d.src, [], d.verdicts === undefined ? [] : LATER);
        assert.equal(norm(r.dom), d.dom, "the DOM's text (" + d.why + ")");
        assert.equal(norm(r.reader), d.reader, "the reader's text (" + d.why + ")");
        if (d.shape !== undefined) assert.equal(r.shape, d.shape, "the DOM's top-level tags (" + d.why + ")");
        if (d.verdicts !== undefined) assert.equal(r.verdicts.join(" "), d.verdicts, "each passage's verdict, in order: " + LATER.join(", ") + " (" + d.why + ")");
      });
    }
    assert.deepEqual(errors, [], "no page errors");
  } finally {
    await browser.close();
  }
});

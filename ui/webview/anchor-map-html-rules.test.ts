// The fallback reader's text rules for html, the Slice 5 review's round 5 (anchor-map.ts renderedBlocks: lenientHtml, lenientInline,
// the character reference decoders), pinned through the two exports that read a source as the Rendered view shows it
// (stripMarkupMapped, renderedQuote), beside anchor-map-html-text.test.ts's round-4 rules: the blank at a raw table's cell boundary
// put only BETWEEN two adjacent parts, where round 4 put one at every part's end; the character reference table read through an
// own-property test, so `&toString;` is no reference; the legacy-prefix rule kept off the HTML5 names it would misread where no
// DOM decodes them (the webview asks the browser: anchor-map-dom-rules-browser.test.ts); the foreign-content rule in the inline
// read, so an inline `<svg><title>` closes at `</svg>`; a body `<title>` dropped with its content, as the sanitizer now drops it
// (md-sanitize.ts dropBodyTitle); and the tokens inside an inline `<textarea>` rendered as the viewer rendered THIS document, a
// wikilink an anchor. Pure text, no DOM stand-in (`document` is undefined here, and the third test says so): the browser leg above
// checks the DOM's side of each rule over the real viewer. Every case here fails over a git archive of 701728eae's module, the
// tree the round reviewed, unless its comment says it is a control. Non-ASCII characters are written as escapes throughout.
import { test } from "node:test";
import assert from "node:assert/strict";
import { viewerHtml } from "./file-view";   // the viewer's parse (mdBlock's recipe: marked's lexer, the literal-tags rule of md-literal-tags.ts, the per-call walk, its parser), the stand-in's too
import { applyMdConfig } from "./md-config";
import { viewerWalkTokens } from "./file-view-links";
import { stripMarkupMapped, renderedQuote } from "./anchor-map";

applyMdConfig();
/** `s` with its whitespace runs folded to one blank and its edges trimmed: the fallback's match is tolerant of the amount of
 *  whitespace and not of its absence (anchor-map.ts occurrences), so the rules below are read the same way. */
const norm = (s: string): string => s.replace(/\s+/g, " ").trim();
/** The rendered text of the whole source, normalized. */
const shown = (src: string): string => norm(stripMarkupMapped(src).text);
/** The needle the fallback reads for the source slice from `from` to the end of `to` (the first occurrence of each), normalized. */
const quote = (src: string, from: string, to: string = from): string => {
  const a = src.indexOf(from); assert.ok(a >= 0, "in the source: " + from);
  const b = src.indexOf(to, a); assert.ok(b >= 0, "in the source: " + to);
  return norm(renderedQuote(src, { start: a, end: b + to.length }));
};
const COPY = "\u00a9", NOT = "\u00ac";

test("a raw html table's blank stands only BETWEEN two adjacent table parts, as the hay's does (hayRuns): a quote from a cell across the table's end into the text after it in the same html block reads the cell and the text run together, as the DOM lays them out, while a quote across `</td><td>` or `</tr><tr>` keeps its blank (before: a blank at EVERY part's end tag, so the needle carried one the hay lacked and a comment across the table's end, painted at 50b19bfdb, painted nothing)", () => {
  const TAIL = "Intro.\n\n<div><table><tr><td>cell *a*</td><td>b cell</td></tr></table>tail text here</div>\n\npara\n";
  assert.equal(quote(TAIL, "b cell</td></tr></table>tail text"), "b celltail text", "from the last cell across the table's end into the tail");
  assert.equal(quote(TAIL, "cell *a*</td><td>b cell"), "cell *a* b cell", "across two cells: round 4's blank stands (a control)");
  assert.equal(shown(TAIL), "Intro. cell *a* b celltail text here para");
  // the recheck's three shapes: text after a bare table, a nested minified table, a stray `<td>` the parser ignores
  const A2 = "Intro.\n\n<table><tr><td>a1</td><td>a2</td></tr></table>tail\n\npara\n";
  assert.equal(quote(A2, "a2</td></tr></table>tail"), "a2tail");
  assert.equal(shown(A2), "Intro. a1 a2tail para");
  const NEST = "Intro.\n\n<table><tr><td><table><tr><td>in</td></tr></table>out</td><td>z</td></tr></table>\n\npara\n";
  assert.equal(quote(NEST, "in</td></tr></table>out"), "inout", "the inner table's end into the outer cell's text");
  assert.equal(quote(NEST, "out</td><td>z"), "out z", "the outer cells apart (a control)");
  const STRAY = "Intro.\n\n<div>a<td>b</td>c</div>\n\npara\n";
  assert.equal(quote(STRAY, "b</td>c"), "bc", "a `<td>` outside a table: the parser ignores the tags, the DOM reads `abc`");
  // every part kind: a caption, a head, a body, each followed by the next part; the last part followed by text
  const CAP = "<table><caption>Cap</caption><thead><tr><th>H1</th></tr></thead><tbody><tr><td>x1</td></tr></tbody></table>trail\n";
  assert.equal(quote(CAP, "Cap</caption><thead><tr><th>H1"), "Cap H1");
  assert.equal(quote(CAP, "H1</th></tr></thead><tbody><tr><td>x1"), "H1 x1");
  assert.equal(quote(CAP, "x1</td></tr></tbody></table>trail"), "x1trail");
  // an html comment between two cells is looked past (the sanitizer drops it and the cells stay adjacent); two tables adjacent
  // are no two parts (TABLE is none), so their cells run together as the DOM's do; whitespace between parts folds with the blank
  assert.equal(quote("<table><tr><td>k1</td><!-- c --><td>k2</td></tr></table>\n", "k1</td><!-- c --><td>k2"), "k1 k2");
  assert.equal(quote("<table><tr><td>p</td></tr></table><table><tr><td>q</td></tr></table>\n", "p</td></tr></table><table><tr><td>q"), "pq");
  assert.equal(quote("<table>\n<tr>\n<td>cell *a*</td>\n<td>b cell</td>\n</tr>\n</table>\n", "cell *a*</td>\n<td>b cell"), "cell *a* b cell", "a spaced table (a control)");
});

test("the character reference table answers its own names alone: `&toString;`, `&constructor;`, `&valueOf;` and `&hasOwnProperty;` stay as written, as the DOM shows them, in a paragraph, an html block and a cell, and a real reference later in the same paragraph still decodes at its own place (before: the table was a plain object read with `in`, so those names answered Object.prototype's functions, whose source text took the reference's place and skewed every position after it in the paragraph, and the `&copy;` after one painted nothing)", () => {
  assert.equal(shown("a &toString; b &constructor; c &valueOf; d &hasOwnProperty; e\n"), "a &toString; b &constructor; c &valueOf; d &hasOwnProperty; e");
  const PARA = "Para &toString; here and &copy; sign.\n";
  assert.equal(quote(PARA, "Para &toString; here"), "Para &toString; here");
  assert.equal(quote(PARA, "and &copy; sign"), "and " + COPY + " sign", "the reference after it keeps its place");
  assert.equal(shown("<div>Block &toString; here</div>\n"), "Block &toString; here", "an html block (before: `Block  here`, the function's arity of characters)");
  assert.equal(quote("| x &toString; y | z |\n|---|---|\n| a | b |\n", "x &toString; y"), "x &toString; y", "a cell");
});

test("where no DOM is to hand (here: `document` is undefined) an HTML5 name that begins with a legacy name keeps its source form, the recorded class of an HTML5-only name, in a paragraph and an html block, while the legacy rule still decodes `&notit;` as the not sign and `it;` and a reference with no semicolon as the parser does (before: `&ltimes;` read `<imes;`, `&parallel;` the pilcrow and `llel;`, `&notni;` the not sign and `ni;`, neither the DOM's glyph nor the source form; in the webview the browser decodes these, anchor-map-dom-rules-browser.test.ts)", () => {
  assert.equal(typeof document, "undefined", "the node tests run with no DOM, so the table rule is what is pinned here");
  assert.equal(shown("a &ltimes; b &parallel; c &centerdot; d &notni; e &copysr; f\n"), "a &ltimes; b &parallel; c &centerdot; d &notni; e &copysr; f");
  assert.equal(quote("<div>use &ltimes; for it</div>\n", "use &ltimes; for it"), "use &ltimes; for it", "an html block");
  assert.equal(shown("a &notit; b\n"), "a " + NOT + "it; b", "a name the parser does not know: the legacy head and the rest (a control)");
  assert.equal(shown("a &check; b\n"), "a &check; b", "an HTML5-only name with no legacy head (a control)");
  assert.equal(shown("<div>a &ltimes b &notit c</div>\n"), "a <imes b " + NOT + "it c", "no semicolon: the legacy rule is the parser's whole rule (a control)");
});

test("inside an inline `<svg>` or `<math>` the raw-text rule is off, as in the html-block scanners (FOREIGN): an svg's `<title>` closed by its own end tag is an ordinary element of the drawing whose text stays, and a `<title>`, `<textarea>` or `<foreignObject>` start tag with no end tag of its own before `</svg>` is literal text since decision 52 (md-literal-tags.ts: the tag's characters are svg text in the DOM, in the textContent the reader matches and drawn nowhere), so `<svg><title>icon</svg> beside end` reads `<title>icon beside end` in a paragraph, a list item, a quote, a heading and a cell; a stray `</svg>` closes nothing (before decision 52 the title read as the parser's element, `icon beside end`; before round 5 the inline read had no foreign stack, so the title's text ran to the block's end, `icon</svg> beside end`, and a quote across the icon in a block the fallback serves painted nothing where 50b19bfdb painted it)", () => {
  for (const [what, src] of [["a paragraph", "Intro <svg><title>icon</svg> beside end\n"], ["a list item", "- Intro <svg><title>icon</svg> beside end\n"], ["a quote", "> Intro <svg><title>icon</svg> beside end\n"], ["a heading", "# Intro <svg><title>icon</svg> beside end\n"]]) {
    assert.equal(shown(src), "Intro <title>icon beside end", what);
  }
  const CELL = "| h |\n|---|\n| Intro <svg><title>icon</svg> beside end |\n";
  assert.equal(quote(CELL, "Intro <svg><title>icon</svg> beside end"), "Intro <title>icon beside end", "a cell");
  assert.equal(quote("Intro <svg><title>icon</svg> beside end\n", "icon</svg> beside"), "icon beside", "a quote across the svg's end");
  assert.equal(shown("Intro <svg><textarea>x</svg> beside end\n"), "Intro <textarea>x beside end", "a textarea start tag with no end tag: literal text, inside an svg as anywhere");
  assert.equal(shown("Intro *em <svg><title>icon</svg> beside* end\n"), "Intro em <title>icon beside end", "the stack is shared down into an emphasis");
  assert.equal(shown("Intro <svg><foreignObject>fo</svg> beside\n"), "Intro <foreignObject>fo beside", "a foreignObject start tag with no end tag of its own: literal text, so `fo` shows where the parser's element took it (before decision 52: `Intro beside`)");
  assert.equal(shown("a </svg> b\n"), "a b", "a stray `</svg>` (a control)");
  // the closed form read right before and reads right still; MathML goes with its text (a control)
  assert.equal(shown("Intro <svg><title>icon</title><text>t</text></svg> beside end\n"), "Intro icont beside end");
  assert.equal(shown("Intro <math><mi>x</mi></math> end\n"), "Intro end");
});

test("a body `<title>` shows nothing, so it reads as nothing: as a block, inside a `<div>`, inline in a paragraph and in a cell its content is dropped with it (the sanitizer drops the element, md-sanitize.ts dropBodyTitle: the browser never shows a title outside the page's head), a quote inside it reads as nothing and a quote across it reads the text beside it alone, where an svg's `<title>` keeps its text (an ordinary element of the drawing); the leading `<title>` block the parser puts in the head reads as nothing now too, where round 4 recorded it read as its text (before: the title's content was read as shown, so a comment inside it painted a mark with no box and the card offered Scroll to nothing)", () => {
  assert.equal(shown("Intro t0.\n\n<title>mid title t4c</title>\n\npara.\n"), "Intro t0. para.", "a title block");
  const DIV = "<div><title>div title t4d</title> beside t4e</div>\n";
  assert.equal(shown(DIV), "beside t4e");
  assert.equal(quote(DIV, "div title t4d</title> beside t4e"), "beside t4e", "across the title into the text beside it");
  assert.equal(quote(DIV, "div title t4d"), "", "inside the title: nothing");
  const PARA = "Para t4f <title>inline t4g</title> tail t4h.\n";
  assert.equal(shown(PARA), "Para t4f tail t4h.", "inline in a paragraph");
  assert.equal(quote(PARA, "inline t4g"), "");
  assert.equal(quote(PARA, "tail t4h."), "tail t4h.");
  assert.equal(quote("| <title>cell t4i</title> x | y |\n|---|---|\n| a | b |\n", "<title>cell t4i</title> x"), "x", "in a cell");
  assert.equal(shown("Lead <title>t &amp; *u*</title> tail\n"), "Lead tail", "the round-4 test's shape, re-aimed");
  assert.equal(shown("Lead <title>open tail\n"), "Lead <title>open tail", "no end tag in the block: the start tag is literal text since decision 52 (md-literal-tags.ts; before, the rest of the block was read as the title's and dropped)");
  assert.equal(shown("<title>lead t4a</title>\n\nafter\n"), "after", "the document-leading title, which the parser puts in the head");
  // an svg's title stays, inline and in a block (a control)
  assert.equal(shown("Intro <svg><title>svg t</title></svg> end\n"), "Intro svg t end");
  assert.equal(shown("<div><svg><title>inner</title></svg> z</div>\n"), "inner z");
});

test("the tokens inside an inline `<textarea>` render as the viewer rendered THIS document, the file kind's token walk (file-view-links.ts viewerWalkTokens: a wikilink an anchor to the note beside the file, a link's destination in the sanitizer's form), so the needle is the text the sanitizer's unwrap leaves in the DOM, marked's HTML for the file document (before: the reader's tokens carried no walk, so a `[[Wiki Note]]` rendered as the chat's dead span, class and title and all, and a comment on the passage painted nothing)", () => {
  const SRC = "Fish &amp; para15b <textarea>t15i [[Wiki Note]] ==hi== see[^1] [x](notes.md:7)</textarea> tail15h\n\n[^1]: A footnote.\n";
  const INNER = "t15i [[Wiki Note]] ==hi== see[^1] [x](notes.md:7)";
  const needle = quote(SRC, INNER);
  assert.ok(needle.startsWith("t15i <a href=\"Wiki%20Note.md\">Wiki Note</a> "), "the wikilink is the file kind's anchor: " + needle);
  assert.ok(!needle.includes("fv-dead") && !needle.includes("fv-wikilink"), "not the chat's dead span");
  assert.ok(needle.endsWith("<a href=\"./notes.md:7\">x</a>"), "a same-directory link target in the form the viewer gives it: " + needle);
  // the oracle: the viewer's own render of the document (file-view.ts's parse with the file kind's walk), the textarea's content
  // with its references decoded as the parser decodes RCDATA
  const html = viewerHtml(SRC, (t) => { viewerWalkTokens(t as { type: string; href?: string | null }); });
  const m = /<textarea>([\s\S]*?)<\/textarea>/.exec(html);
  assert.ok(m, "the render holds the textarea");
  assert.equal(needle, norm(m![1].replace(/&amp;/g, "&")), "the needle is the viewer's rendering of the tokens inside");
  assert.equal(quote(SRC, "tail15h"), "tail15h");
  // the round-4 shape stands (a control)
  assert.equal(quote("Fish &amp; <textarea>a <b>b</b> *c*</textarea> end\n", "a <b>b</b> *c*"), "a <b>b</b> <em>c</em>");
});

// ── the Slice 5 review, round 6 ──────────────────────────────────────────────────────────────────

test("the blank between two adjacent table parts stands past whatever leaves the DOM's parts adjacent (nextIsTablePart): a `<style>` or a `<script>` with its content, which the parser keeps in the row and the sanitizer removes whole; an empty `<form>`, inserted empty and unwrapped; a hidden `<input>`, kept in the row and removed; and a `<br>`, an `<img>`, an empty `<span>`, an empty `<b>` or an `<a name>` anchor, which the parser's in-table rules foster-parent before the table, between two cells and between two rows, so a quote across them reads the blank the hay has (before: round 5 looked past whitespace and comments alone, so `s1</td><style>td{}</style><td>s2` read `s1s2` against a hay `s1 s2` and the quote painted nothing where 701728eae painted it); a `<template>` is kept in the row as an element, so no blank there; text between two cells is moved before the table, an order no blank mirrors, so none there either; two tables stay two", () => {
  const cells = (between: string): string => `Intro.\n\n<div><table><tr><td>s1</td>${between}<td>s2</td></tr></table></div>\n\npara\n`;
  const BETWEEN: Array<[string, string]> = [
    ["a style", "<style>td{}</style>"], ["a script", "<script>var q = 1;</script>"], ["a style holding a `<td>` in its text", "<style>td > b {}</style>"],
    ["an empty form", "<form></form>"], ["a hidden input", '<input type="hidden" name="row">'],
    ["a br", "<br>"], ["a self-closing br", "<br/>"], ["an img", '<img src="x.png" alt="x">'], ["an empty span", "<span></span>"], ["an empty b", "<b></b>"],
    ["an a name anchor", '<a name="row"></a>'], ["a quoted `>` in an attribute", '<a title="a>b" name="row"></a>'], ["two of them", '<br><a name="row"></a>'],
    ["a style after a comment and whitespace", " <!-- c --> <style>td{}</style> "],
  ];
  for (const [what, between] of BETWEEN) {
    const src = cells(between);
    assert.equal(quote(src, `s1</td>${between}<td>s2`), "s1 s2", what);
    assert.equal(shown(src), "Intro. s1 s2 para", what + ": the whole");
  }
  const ROWS = "<table><tr><td>a1</td></tr><br><tr><td>a2</td></tr></table>\n";
  assert.equal(quote(ROWS, "a1</td></tr><br><tr><td>a2"), "a1 a2", "a br between two rows");
  assert.equal(quote("<table><tbody><tr><td>b1</td></tr></tbody><script>x()</script><tbody><tr><td>b2</td></tr></tbody></table>\n", "b1</td></tr></tbody><script>x()</script><tbody><tr><td>b2"), "b1 b2", "a script between two bodies");
  // the exceptions and the controls
  assert.equal(quote("<table><tr><td>m1</td><template>t</template><td>m2</td></tr></table>\n", "m1</td><template>t</template><td>m2"), "m1m2", "a template stands between the cells as an element: no blank (a control)");
  assert.equal(quote("<table><tr><td>g1</td><form>kept</form><td>g2</td></tr></table>\n", "g1</td><form>kept</form><td>g2"), "g1keptg2", "text between the cells, foster-parented before the table: no blank (recorded)");
  assert.equal(quote("<table><tr><td>p</td></tr></table><table><tr><td>q</td></tr></table>\n", "p</td></tr></table><table><tr><td>q"), "pq", "two tables (round 5's control stands)");
  assert.equal(quote("<div><table><tr><td>b cell</td></tr></table>tail text</div>\n", "b cell</td></tr></table>tail text"), "b celltail text", "the tail after the last part (round 5's control stands)");
  assert.equal(quote("<table><tr><td>k1</td><!-- c --><td>k2</td></tr></table>\n", "k1</td><!-- c --><td>k2"), "k1 k2", "a comment (round 5's control stands)");
  assert.equal(quote("<table><tr><td>u1</td><style>td{}<td>u2</td></tr></table>\n", "u1</td><style>td{}<td>u2"), "u1", "a style never closed: its text is the block's rest to the parser, no blank and no cell");
});

test("an HTML element left open inside a `<foreignObject>` when `</svg>` comes, INLINE: since decision 52 (md-literal-tags.ts) a start tag with no end tag of its own in the block is literal text, so no element is open when `</svg>` comes, the svg closes, and the tags' characters are svg text in the DOM (in the textContent the reader matches, drawn nowhere) with the text after the svg shown; a `</foreignObject>` closes the foreignObject the sanitizer drops with its content, whatever stands inside it as text; in an HTML BLOCK the parser's reading stands (the block's rest is the foreignObject's, which ignores `</svg>` while an element is open inside it); the closed forms round 5 pinned still show the text after the svg (the review's round 6, the round-5 recheck's residual, for the html block: the root's end tag cut the drop stack whatever stood open, so the block's tail read as shown against a DOM showing `Intro`, and a quote across the passage painted nothing)", () => {
  const OPEN = "Intro <svg><foreignObject><b>x</svg> y\n";
  assert.equal(shown(OPEN), "Intro <foreignObject><b>x y");
  assert.equal(quote(OPEN, "Intro <svg><foreignObject><b>x</svg> y"), "Intro <foreignObject><b>x y", "the quote across the passage reads what the DOM's text holds");
  assert.equal(quote(OPEN, "y"), "y", "the text after the svg: shown");
  assert.equal(shown("Intro <svg><foreignObject><p>x</svg> y\n"), "Intro <foreignObject><p>x y", "a block-level tag left open: text the same");
  assert.equal(shown("Intro <svg><foreignObject><b>x</i></svg> y\n"), "Intro <foreignObject><b>x y", "an end tag naming no open element closes nothing");
  assert.equal(shown("Intro <svg><foreignObject><b>x</foreignObject></svg> y\n"), "Intro y", "the foreignObject closed by its own end tag: HTML, dropped with the `<b>` text inside it");
  assert.equal(shown("Intro <svg><foreignObject><b>x</b><i>z</svg> w\n"), "Intro <foreignObject>x<i>z w", "the closed `<b>` stays HTML, the `<i>` left open is text");
  assert.equal(shown("Intro.\n\n<div><svg><foreignObject><b>x</svg> y</div>\n\npara\n"), "Intro. para", "an html block: the block's rest is the foreignObject's (the parser swallows the blocks after it too; recorded)");
  assert.equal(shown("- Intro <svg><foreignObject><b>x</svg> y\n"), "Intro <foreignObject><b>x y", "a list item");
  // the closed forms: the closed elements read as round 5 pinned them, and a `<foreignObject>` or `<g>` with no end tag of its own is
  // text (decision 52), so the text an open foreignObject used to take with it shows
  assert.equal(shown("Intro <svg><foreignObject><b>x</b></svg> y\n"), "Intro <foreignObject>x y", "the b closed: HTML, its text shown; the foreignObject text");
  assert.equal(shown("Intro <svg><foreignObject>fo</svg> beside\n"), "Intro <foreignObject>fo beside");
  assert.equal(shown("Intro <svg><foreignObject><br></svg> y\n"), "Intro <foreignObject> y", "a void element opens nothing and stays HTML");
  assert.equal(shown("Intro <svg><foreignObject><b>x</b><i>z</i></svg> w\n"), "Intro <foreignObject>xz w");
  assert.equal(shown("Intro <svg><foreignObject><b><svg><title>t</title></svg>x</b></svg> y\n"), "Intro <foreignObject>tx y", "a nested svg inside the closed b closes on its own end tag, and the outer on its; the title, closed, is the drawing's element");
  assert.equal(shown("Intro <svg><g>x</svg> y\n"), "Intro <g>x y", "an svg element with no end tag of its own: text too (the drawing's text was kept before as well)");
  assert.equal(shown("<div><svg><foreignObject><b>x</b></svg> z</div>\n"), "z", "an html block, the element closed (a control)");
});

// ── the Slice 5 review, round 7 ──────────────────────────────────────────────────────────────────

test("a raw table written without its end tags reads the hay's blank at each implied end (IMPLIED_TABLE_CLOSES): a `<td>` or `<th>` start tag while a cell is open, a `<tr>` while a cell or a row is, a section start tag while a cell, a row or a section is, and a `<caption>` closed by any of them, each leaving the two parts adjacent in the DOM exactly as written end tags do; one blank, never two, where the end-tag rule already put one; a nested table's cells apart inside their cell (the review's round 7: the blank was put at a part's END tag alone, so `<td>ri1 a<td>ri2 b` read `ri1 ari2 b` against a hay `ri1 a ri2 b` and a comment across the cells painted nothing, on every tree)", () => {
  const IMP = "Intro.\n\n<div><table><tr><td>ri1 a<td>ri2 b<tr><td>ri3 c<td>ri4 d</table></div>\n\npara ri5.\n";
  assert.equal(shown(IMP), "Intro. ri1 a ri2 b ri3 c ri4 d para ri5.");
  assert.equal(quote(IMP, "ri1 a<td>ri2 b"), "ri1 a ri2 b", "across two cells the second's start tag closes the first");
  assert.equal(quote(IMP, "ri2 b<tr><td>ri3 c"), "ri2 b ri3 c", "across two rows the second's start tag closes the first");
  assert.equal(quote(IMP, "ri4 d"), "ri4 d", "a single cell (a control)");
  const README = "Intro.\n\n<table><tr><td>Flag<td>Meaning</tr></table>\n\npara.\n";
  assert.equal(quote(README, "Flag<td>Meaning"), "Flag Meaning", "the README shape");
  const HEADS = "<table><thead><tr><th>H1<th>H2<tbody><tr><td>x1<td>x2</table>\n";
  assert.equal(shown(HEADS), "H1 H2 x1 x2");
  assert.equal(quote(HEADS, "H1<th>H2"), "H1 H2", "a header cell closed by the next");
  assert.equal(quote(HEADS, "H2<tbody><tr><td>x1"), "H2 x1", "a head closed by the body's start tag");
  assert.equal(quote("<table><caption>Cap<td>x</table>\n", "Cap<td>x"), "Cap x", "a caption closed by a cell's start tag");
  assert.equal(quote("<table><tr><td>a1<caption>c2</table>\n", "a1<caption>c2"), "a1 c2", "a cell closed by a caption's start tag");
  // one blank where the end-tag rule put one already, none where a part opens in an empty context
  const MIXED = stripMarkupMapped("<table><tr><td>a1</td><tr><td>a2</table>\n").text;
  assert.ok(MIXED.includes("a1 a2") && !MIXED.includes("a1  a2"), "a written `</td>` then an implied row end: one blank, " + JSON.stringify(MIXED));
  assert.equal(stripMarkupMapped("<table><tbody><tr><td>b1</td></tr><tr><td>b2</table>\n").text.includes("b1 b2"), true, "a `<tr>` after a written `</tr>`: the end-tag rule's blank alone");
  assert.equal(quote("<table><tr><td>o1<table><tr><td>i1<td>i2</table>o2<td>o3</table>\n", "o1<table><tr><td>i1<td>i2</table>o2<td>o3"), "o1i1 i2o2 o3", "a nested table's cells apart, its end no blank, the outer cells apart");
  // the written forms read as before (controls)
  assert.equal(quote("<table><tr><td>k1</td><td>k2</td></tr></table>\n", "k1</td><td>k2"), "k1 k2");
  assert.equal(quote("<div><table><tr><td>b cell</td></tr></table>tail text</div>\n", "b cell</td></tr></table>tail text"), "b celltail text", "the tail after the last part (round 5's control stands)");
});

test("the blank between two adjacent table parts stands past a dropped element's TEXT as well (nextIsTablePart reads a DROPPED_CONTENT element's content as no text): a `<noscript>`, a `<math>` with its parts, an svg's `<foreignObject>`, each removed whole by the sanitizer and leaving the cells adjacent, with a `<br>` before or after (the review's round 7: such an element was read to its `>` and its text ended the look, so `bf1</td><noscript>js off</noscript><td>bf2` read `bf1bf2` against a hay `bf1 bf2` and the quote painted nothing where 701728eae painted it); an svg's kept text between two cells is foster-parented before the table, an order no blank mirrors, so none there (recorded, as `<form>kept</form>`)", () => {
  const cells = (between: string): string => `Intro.\n\n<div><table><tr><td>bf1</td>${between}<td>bf2</td></tr></table></div>\n\npara bf3.\n`;
  const BETWEEN: Array<[string, string]> = [
    ["a noscript", "<noscript>js off</noscript>"], ["a noscript in upper case", "<NOSCRIPT>js off</NOSCRIPT>"],
    ["a math", "<math>x</math>"], ["a math with an mi", "<math><mi>x</mi></math>"], ["a math then a br", "<math>x</math><br>"], ["a br then a math", "<br><math>x</math>"],
    ["an svg whose only content is a foreignObject with text", "<svg><foreignObject>fo</foreignObject></svg>"],
    ["an empty noscript (round 6's rule stands)", "<noscript></noscript>"], ["an iframe with text (raw text, round 6's rule stands)", "<iframe>x</iframe>"],
  ];
  for (const [what, between] of BETWEEN) {
    const src = cells(between);
    assert.equal(quote(src, `bf1</td>${between}<td>bf2`), "bf1 bf2", what);
    assert.equal(shown(src), "Intro. bf1 bf2 para bf3.", what + ": the whole");
  }
  assert.equal(quote(cells("<svg><title>t</title></svg>"), "bf1</td><svg><title>t</title></svg><td>bf2"), "bf1tbf2", "an svg title's text is kept and stands between the cells in the raw: no blank (recorded; the DOM moves the svg before the table)");
});

test("a raw-text element or a dropped element written `/>` opens, as the parser reads it (the self-closing flag is ignored on an HTML element; leafTag): `<title/>` in a paragraph drops the block's rest with it, `<textarea/>` shows the block's rest as marked's HTML for its tokens, `<noscript/>` drops the rest, in a paragraph and in an html block, where a void element and a foreign `/>` still close at once (the review's round 7: the three scanners read `/>` as closing the element, so the text after a `<title/>` was read as shown where the DOM shows nothing from it on, and the tokens after a `<textarea/>` as prose where the DOM shows their HTML); the parser reads on past the block, which the reader does not mirror (recorded)", () => {
  const TITLE = "Intro.\n\nPara sc1 <title/> after sc2.\n\nPara sc3 more sc4.\n\nend sc5.\n";
  assert.equal(shown(TITLE), "Intro. Para sc1 Para sc3 more sc4. end sc5.", "the block's rest is the title's (the later blocks are read: the cross-block swallow is recorded)");
  assert.equal(quote(TITLE, "after sc2."), "", "inside the title: nothing");
  assert.equal(quote(TITLE, "Para sc1"), "Para sc1");
  const AREA = "Para se1 <textarea/> after *em* se2.\n\nPara se3.\n";
  assert.equal(shown(AREA), "Para se1 after <em>em</em> se2. Para se3.", "the block's rest is the textarea's text, marked's HTML for the tokens");
  assert.equal(quote(AREA, "after *em* se2."), "after <em>em</em> se2.");
  assert.equal(shown("Intro <noscript/> after\n\nPara.\n"), "Intro Para.", "a noscript: dropped with the block's rest");
  const BLOCK = "Intro.\n\n<div>lead <textarea/> in <b>bold</b> wrap</div>\n\nPara bw3.\n";
  assert.equal(quote(BLOCK, "in <b>bold</b> wrap"), "in <b>bold</b> wrap", "an html block: the raw's rest as written, tags and all");
  assert.equal(shown("Intro.\n\n<div>lead <title/> gone</div>\n\nPara bt3.\n"), "Intro. lead Para bt3.", "an html block's title");
  // a void element, a foreign `/>` and a closed raw-text element read as before (controls)
  assert.equal(shown("Intro <br/> after\n"), "Intro after");
  assert.equal(shown("Intro <svg><rect/><text>t</text></svg> y\n"), "Intro t y", "a foreign element's `/>` closes it at once");
  assert.equal(shown("Intro <svg/> y\n"), "Intro y", "a foreign root's `/>` closes it at once");
  assert.equal(shown("Intro <title>x</title> y\n"), "Intro y");
  assert.equal(shown("Intro <textarea>a *b*</textarea> y\n"), "Intro a <em>b</em> y");
});

test("inside a foreign root's integration point the parser's implied end tags are read (openInIntegrationPoint, startTagCloses), so an element it closes implicitly does not keep `</foreignObject>` and `</svg>` from closing: a `<p>` closed by a block-level start tag (a `<p>`, a `<div>`, a `<ul>`, an `<h2>`, through an open `<span>`), an `<li>` by the next `<li>`, a `<dt>` by a `<dd>`, an `<option>` by the next `<option>` or an `<optgroup>`, a heading by a heading, a `<button>` by a `<button>`, inline and in an html block, so the text after the svg reads as the DOM shows it; a `<p>` inside a `<button>` or before a `<table>` (no `<p>` closes at a table in the sanitizer's quirks-mode document) stays open and the end tags stay ignored, as does an `<li>` behind a `<blockquote>` (the review's round 7, round 6's residual: every start tag was pushed and popped by name alone, so `<p>a<p>b</p></foreignObject></svg> y` kept the first `<p>` open and dropped ` y`)", () => {
  const FO = (inner: string): string => `Intro <svg><foreignObject>${inner}</foreignObject></svg> y\n`;
  const CLOSES: Array<[string, string]> = [
    ["a p closed by a second p", "<p>a<p>b</p>"], ["a p closed by a div", "<p>a<div>b</div>"], ["a p closed by a ul", "<p>a<ul><li>b</li></ul>"], ["a p closed by an h2", "<p>a<h2>b</h2>"],
    ["a p closed through an open span", "<p>a<span>x<div>b</div>"], ["an li closed by the next li", "<li>a<li>b</li>"], ["an li closed through an open b", "<li>a<b>x<li>b</li>"],
    ["a dt closed by a dd", "<dt>a<dd>b</dd>"], ["an option closed by the next option", "<option>a<option>b</option>"], ["an option closed by an optgroup", "<optgroup><option>a<optgroup><option>b</option></optgroup></optgroup>"],
    ["an h1 closed by an h2", "<h1>a<h2>b</h2>"], ["a button closed by a button", "<button>a<button>b</button>"],
    ["two ps closed by name (round 6's control)", "<p>a</p><p>b</p>"],
  ];
  for (const [what, inner] of CLOSES) {
    const src = FO(inner);
    assert.equal(shown(src), "Intro y", what);
    assert.equal(quote(src, "Intro", " y"), "Intro y", what + ": the quote across the passage");
    assert.equal(quote(src, " y"), "y", what + ": the text after the svg");
  }
  assert.equal(shown("Intro <svg><foreignObject><p>a<p>b</p></svg> y\n"), "Intro <foreignObject><p>ab y", "`</svg>` alone after the closed ps: the foreignObject and the first p, with no end tag of their own, are text (decision 52), the second p HTML");
  assert.equal(shown("Intro.\n\n<div><svg><foreignObject><p>a<div>b</div></foreignObject></svg> y</div>\n\npara\n"), "Intro. y para", "an html block");
  // a start tag left open inside the foreignObject is literal text since decision 52 (md-literal-tags.ts), so nothing is open when
  // `</foreignObject>` comes: the foreignObject closes and the sanitizer drops it with the text inside, and ` y` shows (before
  // decision 52 the parser's element stayed open, the end tags were ignored and the block's rest was the foreignObject's, `Intro`)
  for (const [what, inner] of [["a p alone", "<p>a"], ["a p inside a button, which a div does not close", "<p>a<button><div>b</div></button>"], ["a p before a table (quirks mode)", "<p>a<table><tr><td>b</td></tr></table>"],
                               ["an li behind a blockquote", "<li>a<blockquote><li>b</li></blockquote>"], ["an option inside an open select", "<select><option>a</option>"], ["a b left open (round 6's pin)", "<b>x"]]) {
    assert.equal(shown(FO(inner)), "Intro y", what);
  }
});

test("every HTML integration point of a foreign root is read as the `<foreignObject>` is (ForeignRoot.ip, integrationPoint): MathML's `<mi>`, `<mo>`, `<mn>`, `<ms>` and `<mtext>`, an `<annotation-xml>` whose encoding is `text/html` or `application/xhtml+xml` (in any case, quoted or bare), and an svg's `<title>` and `<desc>`; since decision 52 (md-literal-tags.ts) a start tag with no end tag of its own in the block is literal text, so an integration point or an HTML element written without its end tag opens nothing, the root's end tag closes the root, and the text after it shows: inside a `<math>`, which the sanitizer drops whole, the tags' characters go with it; inside an `<svg>` they are svg text (in the textContent the reader matches, drawn nowhere); an HTML element CLOSED inside an svg's `<title>` or `<desc>` is removed WITH its text by the sanitizer's namespace check, so its text is dropped where the title's own text stays (the review's round 7, for the parser's elements: the foreignObject alone was modelled, so `<math><annotation-xml encoding=\"text/html\"><b>x</math> y2` read `ma2 y2` against a DOM showing `ma2`, and a comment made in Raw on the tail painted nothing; both sides read `ma2 y2` now)", () => {
  for (const [what, src] of [["an annotation-xml with the html encoding", "Intro before.\n\nma2 <math><annotation-xml encoding=\"text/html\"><b>x</math> y2\n"], ["the xhtml encoding", "Intro before.\n\nma2 <math><annotation-xml encoding=\"application/xhtml+xml\"><b>x</math> y2\n"],
                             ["the encoding in upper case", "Intro before.\n\nma2 <math><annotation-xml encoding=\"TEXT/HTML\"><b>x</math> y2\n"], ["the encoding bare", "Intro before.\n\nma2 <math><annotation-xml encoding=text/html><b>x</math> y2\n"],
                             ["an mtext", "Intro before.\n\nma2 <math><mtext><b>x</math> y2\n"], ["an mi", "Intro before.\n\nma2 <math><mi><b>x</math> y2\n"], ["an mo", "Intro before.\n\nma2 <math><mo><b>x</math> y2\n"]]) {
    assert.equal(shown(src), "Intro before. ma2 y2", what);
    assert.equal(quote(src, "ma2", "y2"), "ma2 y2", what + ": the quote across the passage reads what the DOM shows (the math dropped whole, the tail shown)");
    assert.equal(quote(src, "y2"), "y2", what + ": the tail shows");
  }
  assert.equal(shown("Intro.\n\n<div>ma4 <math><annotation-xml encoding=\"text/html\"><b>x</math> y4</div>\n\npara\n"), "Intro. ma4 para", "an html block: the block's rest is the annotation's (the parser swallows the later blocks too, which the reader does not mirror; recorded, as test 8's html block)");
  // the reader's side alone of a divergence RECORDED in anchor-map-html-text-browser.test.ts: the `<mtext>` and the first `<p>`, with no
  // end tags of their own, are literal text inside the math and the closed `<p>b</p>` goes with the dropped math, `ma5 y5`; the DOM shows
  // `ma5 b y5`, since the closed `<p>` stands in the math's foreign content with no integration point around it and the parser breaks out
  // of the math at it. The class, recorded there with two text representatives and, since the closing check of PR 804, entries by the
  // DOM's top-level tags and the map's verdicts: an integration point of an inline `<math>` left open
  // (`<mtext>`, `<mi>`, `<mo>`, `<mn>` or `<ms>`, or an `<annotation-xml>` with the html or the xhtml encoding), then an HTML
  // element whose start tag is on the parser's foreign-content breakout list (`<b>`, `<i>`, `<em>`, `<strong>`, `<span>`, `<code>`,
  // `<sub>`, `<sup>`, `<div>`, `<p>`, a heading, a list, a table and the rest of that list), closed, self-closed or void (`<br>`, `<img>`
  // and `<hr>` break out with no closing, and `<hr>` closes the paragraph too); a closed `<kbd>`, `<a>`, `<abbr>`, `<mark>`
  // or `<q>` is no breakout tag and both sides agree in text. Before decision 52 the mtext was the parser's element and the ps HTML inside it,
  // `ma5 y5` on both sides (the line's former message, about the implied ends inside a MathML text element, described that world)
  assert.equal(shown("ma5 <math><mtext><p>a<p>b</p></math> y5\n"), "ma5 y5", "the reader's text alone: the mtext and the first p literal text inside the dropped math, the closed `<p>b</p>` dropped with it (the DOM shows `ma5 b y5`, the closed p breaking out of the math: recorded in anchor-map-html-text-browser.test.ts, RECORDED)");
  // an svg's title and desc: a closed HTML element's text goes with it, the title's own stays; a start tag left open is text
  assert.equal(shown("Intro <svg><title><b>x</svg> y\n"), "Intro <title><b>x y", "a title and a b with no end tags: both literal text, svg text in the DOM, and the svg closes");
  assert.equal(shown("Intro <svg><desc><b>x</svg> y\n"), "Intro <desc><b>x y", "the same with a desc");
  assert.equal(shown("Intro <svg><title><b>x</b></svg> y\n"), "Intro <title>x y", "the title left open is text and the closed b an element of the drawing, whose text stays (no title element for the namespace check to remove it from)");
  assert.equal(shown("Intro <svg><title>t<b>x</b>u</title></svg> y\n"), "Intro tu y", "the title's own text stays around the dropped element");
  assert.equal(shown("Intro <svg><title>t<p>a</title></svg> y\n"), "Intro t<p>a y", "a p with no end tag inside a closed title: text of the title's");
  // the closed forms read as before (controls)
  assert.equal(shown("ma6 <math><annotation-xml encoding=\"text/html\"><b>x</b></math> y6\n"), "ma6 y6");
  assert.equal(shown("ma3 <math><mtext>x</math> y3\n"), "ma3 y3", "no HTML element open: the root's end tag closes it");
  assert.equal(shown("ma1 <math><mi>x</mi><mo>+</mo></math> y1\n"), "ma1 y1");
  assert.equal(shown("Intro <svg><title>icon</svg> beside end\n"), "Intro <title>icon beside end", "round 5's shape under decision 52 (test 6's reading)");
  assert.equal(shown("Intro <svg><foreignObject><b>x</svg> y\n"), "Intro <foreignObject><b>x y", "round 6's shape under decision 52 (test 8's reading)");
});

// ── the Slice 5 review, round 8 ──────────────────────────────────────────────────────────────────

test("a raw table marked splits into html blocks at a blank line is one table to the parser, so a block continuing it reads the implied end's blank against the parts the earlier block left open (lenientHtml's table frames, seeded from the wrapper chain the blocks before leave open, renderedBlocks): a quote across `<td>b1<td>b2` in the second block reads `b1 b2`, in a third block too, and a `<tbody>` block after a `<thead>` block the same; a `<tr><td>` block with no table open, or after the table's end tag, is the parser's stray and its cells run together, as the DOM shows (the review's round 8, round 7's residual: the frames were the block's own, pushed at a `<table>` start tag met in that block alone, so the second block read `b1b2` against a hay `b1 b2` and a comment across its cells painted nothing, where the first block's cells and a table with `</td>` written painted)", () => {
  const TB = "Intro.\n\n<table>\n<tr><td>a1<td>a2\n\n<tr><td>b1<td>b2\n</table>\n\npara.\n";
  assert.equal(shown(TB), "Intro. a1 a2 b1 b2 para.");
  assert.equal(quote(TB, "b1<td>b2"), "b1 b2", "across the second block's cells");
  assert.equal(quote(TB, "a1<td>a2"), "a1 a2", "across the first block's cells (round 7's rule stands, a control)");
  assert.equal(quote(TB, "a2\n\n<tr><td>b1"), "a2 b1", "across the two blocks");
  const TB3 = "Intro.\n\n<table>\n<tr><td>a1<td>a2\n\n<tr><td>b1<td>b2\n\n<tr><td>c1<td>c2\n</table>\n\npara.\n";
  assert.equal(shown(TB3), "Intro. a1 a2 b1 b2 c1 c2 para.");
  assert.equal(quote(TB3, "c1<td>c2"), "c1 c2", "the third block's cells");
  const HEADS = "<table><thead><tr><th>H1<th>H2\n\n<tbody><tr><td>x1<td>x2\n</table>\n";
  assert.equal(shown(HEADS), "H1 H2 x1 x2");
  assert.equal(quote(HEADS, "x1<td>x2"), "x1 x2", "the body's cells in the second block");
  assert.equal(quote("Intro.\n\n<table>\n<tr><td>a1</td><td>a2</td></tr>\n\n<tr><td>b1</td><td>b2</td></tr>\n</table>\n\npara.\n", "b1</td><td>b2"), "b1 b2", "the end tags written: the end-tag rule's blank alone, once (a control)");
  // no table open: the parser drops a top-level `<tr>` and `<td>` and their text runs together (topTags reads the block's own
  // strays; recorded as the top-level `<td>`/`<tr>` class)
  assert.equal(shown("Intro.\n\n<tr><td>s1<td>s2\n\npara.\n"), "Intro. s1s2 para.", "a stray row: no frame, no blank");
  assert.equal(shown("Intro.\n\n<table><tr><td>a1<td>a2</table>\n\n<tr><td>b1<td>b2\n\npara.\n"), "Intro. a1 a2 b1b2 para.", "the table closed in the block before: the second block's parts are strays");
});

test("`<mglyph>` and `<malignmark>` met inside a MathML text integration point (`<mi>`, `<mtext>`) stay foreign content, as the parser's dispatcher keeps them, so they open no HTML element and `</mi>`, `</mtext>` and `</math>` close as usual: `ma9 <math><mi><mglyph/></mi></math> y9` reads `ma9 y9` as the DOM shows, self-closed, as a start tag alone or between text, inline and in an html block; and an `<annotation-xml>`'s encoding is an exact match of the value, so a blank inside the quotes makes it no integration point and the reader reads on past the math as 78c0806ce did (the DOM showed `ma8 x y8` there before decision 52, the `<b>` breaking out of the math, the recorded class; since it the annotation-xml and the b, with no end tags of their own, are literal text inside the dropped math and the DOM shows `ma8 y8` too) (the review's round 8, round 7's recheck residuals: the two were sent to openInIntegrationPoint and recorded as HTML elements left open, so the root's end tag was ignored and the block's rest dropped; and `encoding=\"text/html \"` was read as an integration point through a `\\s*` in the pattern)", () => {
  for (const [what, src] of [["an mglyph self-closed inside an mi", "ma9 <math><mi><mglyph/></mi></math> y9\n"], ["a malignmark start tag inside an mtext", "ma9 <math><mtext><malignmark></mtext></math> y9\n"],
                             ["a malignmark between text inside an mi", "ma9 <math><mi>x<malignmark>z</mi></math> y9\n"], ["an mglyph with its own end tag (a control)", "ma9 <math><mi><mglyph></mglyph></mi></math> y9\n"]]) {
    assert.equal(shown(src), "ma9 y9", what);
    assert.equal(quote(src, "ma9", "y9"), "ma9 y9", what + ": the quote across the passage");
  }
  assert.equal(shown("Intro.\n\n<div>ma9 <math><mi><mglyph/></mi></math> y9</div>\n\npara.\n"), "Intro. ma9 y9 para.", "an html block");
  assert.equal(shown("ma9 <math><annotation-xml encoding=\"text/html\"><mglyph/></math> y9\n"), "ma9 y9", "an annotation-xml with no end tag of its own is literal text (decision 52), the `<mglyph/>` self-closing syntax HTML, both inside the dropped math (before decision 52: the parser's integration point stood open and the block's rest was the math's, `ma9`)");
  for (const [what, src] of [["a trailing blank", "ma8 <math><annotation-xml encoding=\"text/html \"><b>x</math> y8\n"], ["a leading blank", "ma8 <math><annotation-xml encoding=\" text/html\"><b>x</math> y8\n"],
                             ["blanks around the xhtml encoding, single-quoted", "ma8 <math><annotation-xml encoding=' application/xhtml+xml '><b>x</math> y8\n"]]) {
    assert.equal(shown(src), "ma8 y8", what + ": no integration point, the math closes at its end tag and the reader reads on (the DOM shows `ma8 y8` too since decision 52, the annotation-xml and the b literal text inside the dropped math; before it `ma8 x y8`, the breakout class, recorded)");
  }
  for (const src of ["ma8 <math><annotation-xml encoding=\"text/html\"><b>x</math> y8\n", "ma8 <math><annotation-xml encoding=\"TEXT/HTML\"><b>x</math> y8\n", "ma8 <math><annotation-xml encoding=text/html><b>x</math> y8\n"]) assert.equal(shown(src), "ma8 y8", "the exact forms: the annotation-xml and the b, with no end tags of their own, are literal text inside the dropped math (decision 52; before: `ma8`, the integration point's element left open): " + JSON.stringify(src));
});

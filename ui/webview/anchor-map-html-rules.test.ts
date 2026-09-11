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
import { marked } from "marked";
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

test("inside an inline `<svg>` or `<math>` the raw-text rule is off, as in the html-block scanners (FOREIGN): `<svg><title>icon</svg> beside end` reads `icon beside end` in a paragraph, a list item, a quote, a heading and a cell, the parser closing the title at `</svg>`; a `<textarea>` in an svg the same; the root's end tag closes a `<foreignObject>` opened inside it; a stray `</svg>` closes nothing (before: the inline read had no foreign stack, so the title's text ran to the block's end, `icon</svg> beside end`, and a quote across the icon in a block the fallback serves painted nothing where 50b19bfdb painted it)", () => {
  for (const [what, src] of [["a paragraph", "Intro <svg><title>icon</svg> beside end\n"], ["a list item", "- Intro <svg><title>icon</svg> beside end\n"], ["a quote", "> Intro <svg><title>icon</svg> beside end\n"], ["a heading", "# Intro <svg><title>icon</svg> beside end\n"]]) {
    assert.equal(shown(src), "Intro icon beside end", what);
  }
  const CELL = "| h |\n|---|\n| Intro <svg><title>icon</svg> beside end |\n";
  assert.equal(quote(CELL, "Intro <svg><title>icon</svg> beside end"), "Intro icon beside end", "a cell");
  assert.equal(quote("Intro <svg><title>icon</svg> beside end\n", "icon</svg> beside"), "icon beside", "a quote across the svg's end");
  assert.equal(shown("Intro <svg><textarea>x</svg> beside end\n"), "Intro x beside end", "a textarea inside an svg is an ordinary element too");
  assert.equal(shown("Intro *em <svg><title>icon</svg> beside* end\n"), "Intro em icon beside end", "the stack is shared down into an emphasis");
  assert.equal(shown("Intro <svg><foreignObject>fo</svg> beside\n"), "Intro beside", "`</svg>` closes the foreignObject the sanitizer drops, so the text after the svg shows");
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
  assert.equal(shown("Lead <title>open tail\n"), "Lead", "no end tag in the block: the rest is the title's (the parser reads on; recorded)");
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
  const html = marked.parse(SRC, { walkTokens: (t) => { viewerWalkTokens(t as { type: string; href?: string | null }); } }) as string;
  const m = /<textarea>([\s\S]*?)<\/textarea>/.exec(html);
  assert.ok(m, "the render holds the textarea");
  assert.equal(needle, norm(m![1].replace(/&amp;/g, "&")), "the needle is the viewer's rendering of the tokens inside");
  assert.equal(quote(SRC, "tail15h"), "tail15h");
  // the round-4 shape stands (a control)
  assert.equal(quote("Fish &amp; <textarea>a <b>b</b> *c*</textarea> end\n", "a <b>b</b> *c*"), "a <b>b</b> <em>c</em>");
});

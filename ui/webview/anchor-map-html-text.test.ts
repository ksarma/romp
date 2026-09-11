// The fallback reader's text rules for html the browser's parser and sanitizer shape (anchor-map.ts renderedBlocks: lenientHtml,
// lenientInline and the character reference decoders), pinned through the two exports that read a source as the Rendered view
// shows it (stripMarkupMapped, renderedQuote): the blank the hay puts at a raw table's cell boundary, an element the sanitizer
// drops with its text (svg's foreignObject), the character references (HTML 4.01's names, the legacy names with no semicolon in
// an html block, the numeric quirks), an RCDATA element inline, and svg's title as an ordinary element (the Slice 5 review,
// round 4). Pure text, no DOM stand-in: the browser legs over the real viewer (anchor-map-code-table-paint-browser.test.ts,
// md-sanitize-anchor-map-browser.test.ts) check the DOM's side of each rule. Every case here fails over a git archive of
// 50b19bfdb's module, the tree the round reviewed. Non-ASCII characters are written as escapes throughout.
import { test } from "node:test";
import assert from "node:assert/strict";
import { applyMdConfig } from "./md-config";
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
// the glyphs the DOM shows, as escapes
const MDASH = "\u2014", NDASH = "\u2013", COPY = "\u00a9", REG = "\u00ae", HELLIP = "\u2026", REPL = "\ufffd", EURO = "\u20ac", NOT = "\u00ac";
const SMILE = "\u{1F600}", GRIN = "\u{1F601}";

test("a raw html table's cell boundary reads as the blank the hay puts between two adjacent table parts: a quote across `</td><td>` or across `</tr><tr>` of a minified `<table>` finds the cells apart, a single cell reads as before (before: the end-tag branch put nothing there, the needle read `cell *a*b cell` against a DOM hay of `cell *a* b cell`, and the comment painted nothing)", () => {
  const MIN = "Intro.\n\n<table><tr><td>cell *a*</td><td>b cell</td></tr><tr><td>c</td><td>d</td></tr></table>\n\npara\n";
  assert.equal(quote(MIN, "cell *a*</td><td>b cell"), "cell *a* b cell", "across two cells");
  assert.equal(quote(MIN, "c</td><td>d"), "c d", "across two cells of the second row");
  assert.equal(quote(MIN, "b cell</td></tr><tr><td>c"), "b cell c", "across two rows");
  assert.equal(quote(MIN, "cell *a*"), "cell *a*", "a single cell, as written (an html block's text takes no emphasis)");
  assert.equal(quote(MIN, "b cell"), "b cell");
  assert.equal(shown(MIN), "Intro. cell *a* b cell c d para", "the whole block: a blank per part, whitespace-normalized");
  // a table written with whitespace between its parts reads the same, the blank joining the whitespace
  const SPACED = "Intro.\n\n<table>\n<tr>\n<td>cell *a*</td>\n<td>b cell</td>\n</tr>\n</table>\n\npara\n";
  assert.equal(quote(SPACED, "cell *a*</td>\n<td>b cell"), "cell *a* b cell");
  assert.equal(shown(SPACED), "Intro. cell *a* b cell para");
  // a table part inside an element the sanitizer drops adds nothing
  assert.equal(shown("<div><script><table><tr><td>x</td></tr></table></script>y</div>\n"), "y");
});

test("svg's `<foreignObject>` goes with its text, as the sanitizer drops it (DOMPurify's FORBID_CONTENTS, outside the svg profile), in an html block and inline in a paragraph; the svg's `<text>` and `<desc>` keep theirs (before: the reader kept `fo text` and a quote over the svg matched nothing)", () => {
  const BLOCK = "Intro.\n\n<div><svg viewBox=\"0 0 10 10\"><text>svg text</text><desc>desc text</desc><foreignObject><p>fo text</p></foreignObject></svg></div>\n\npara.\n";
  assert.equal(shown(BLOCK), "Intro. svg textdesc text para.", "the block: the foreignObject's text left out, the rest as the DOM runs it together");
  assert.equal(quote(BLOCK, "<svg", "</svg>"), "svg textdesc text");
  assert.equal(quote(BLOCK, "fo text"), "", "a quote inside the foreignObject reads as nothing");
  const INLINE = "Intro <svg><foreignObject>fo text</foreignObject><text>svg text</text></svg> end\n";
  assert.equal(shown(INLINE), "Intro svg text end", "inline: the drop stack holds the foreignObject");
  assert.equal(quote(INLINE, "<svg>", "</svg>"), "svg text");
});

test("the named character references decode as the parser decodes them, HTML 4.01's names with `apos` and the upper-case aliases, in every construct the fallback serves (an html block, a heading, a list item, a quote, a link's text, strong, a cell, a `<pre>`, a refused paragraph); an HTML5-only name keeps its source form, recorded (before: six names decoded, so `&mdash;`, `&copy;` and the rest never matched the DOM's glyph)", () => {
  const DIV = "Intro.\n\n<div align=\"center\">Cost &copy; w000 &mdash; done &amp; ok</div>\n\npara.\n";
  assert.equal(quote(DIV, "w000 &mdash; done &amp; ok"), "w000 " + MDASH + " done & ok", "an html block");
  assert.equal(quote(DIV, "Cost &copy;"), "Cost " + COPY);
  assert.equal(quote("# Title &mdash; sub\n\npara.\n", "Title &mdash; sub"), "Title " + MDASH + " sub", "a heading");
  assert.equal(quote("- item &copy; 2026\n- plain item\n", "item &copy; 2026"), "item " + COPY + " 2026", "a list item");
  assert.equal(quote("> quote &hellip; more\n", "quote &hellip; more"), "quote " + HELLIP + " more", "a quote");
  const INLINE = "See [a &mdash; b](http://x.test) and **bold &copy;** and *em &ndash; x* end\n";
  assert.equal(quote(INLINE, "[a &mdash; b](http://x.test)"), "a " + MDASH + " b", "a link's text");
  assert.equal(quote(INLINE, "**bold &copy;**"), "bold " + COPY, "strong");
  assert.equal(quote(INLINE, "*em &ndash; x*"), "em " + NDASH + " x", "em");
  const TABLE = "| h &mdash; 1 | h2 |\n|---|---|\n| c &hellip; 1 | c2 |\n";
  assert.equal(quote(TABLE, "h &mdash; 1"), "h " + MDASH + " 1", "a header cell");
  assert.equal(quote(TABLE, "c &hellip; 1"), "c " + HELLIP + " 1", "a body cell");
  assert.equal(quote("<pre>\nline &amp; one &copy;\n</pre>\n", "line &amp; one &copy;"), "line & one " + COPY, "a pre");
  // the rest of the finder's list, in a refused paragraph (marked passes a reference with a semicolon through, the browser decodes it)
  const MANY = "Fish &amp; chips &trade; a &euro; b &rarr; c &times; d &deg; e &frac12; f &laquo;g&raquo; h &middot; i &bull; j &reg; k &lang;l&rang; end\n";
  assert.equal(shown(MANY), "Fish & chips \u2122 a " + EURO + " b \u2192 c \u00d7 d \u00b0 e \u00bd f \u00abg\u00bb h \u00b7 i \u2022 j " + REG + " k \u27e8l\u27e9 end",
               "HTML5's code points (lang and rang moved from HTML 4's)");
  assert.equal(shown("a &AMP; b &COPY; c &LT; d &GT; e &QUOT; f &REG; g &apos; h\n"), "a & b " + COPY + " c < d > e \" f " + REG + " g ' h", "the upper-case aliases and apos");
  // a name the table lacks: an HTML5-only one keeps its form (recorded); one the parser reads as a legacy name and a tail decodes so
  assert.equal(shown("a &check; b &star; c\n"), "a &check; b &star; c", "an HTML5-only name stays as written");
  assert.equal(shown("a &notit; b\n"), "a " + NOT + "it; b", "the parser's longest legacy match: `&not` then `it;`");
  assert.equal(shown("a &Mdash; b &MDASH; c\n"), "a &Mdash; b &MDASH; c", "the table is case-sensitive, as the parser's");
});

test("in an html block the legacy names decode with no semicolon as the parser decodes them (`&copy c` shows the sign and `c`); in a paragraph such an `&` stays as written, since marked's escape turns it into `&amp;` and the DOM shows the source (before: neither form decoded in a block, the html block's needle keeping `&copy c` against the DOM's glyph)", () => {
  const BLOCK = "Intro.\n\n<div>a &amp b &copy c &reg i &COPY; d &nbsp e &notit; f &amp;amp; g</div>\n\npara.\n";
  assert.equal(quote(BLOCK, "a &amp b &copy c &reg i &COPY; d &nbsp e &notit; f &amp;amp; g"), "a & b " + COPY + " c " + REG + " i " + COPY + " d e " + NOT + "it; f &amp; g");
  assert.equal(quote(BLOCK, "&copy c"), COPY + " c", "a quote cut to the reference and a word");
  const PARA = "a &amp b &copy c &reg i end\n";
  assert.equal(shown(PARA), "a &amp b &copy c &reg i end", "a paragraph: marked escaped the ampersands, the DOM shows them");
  // a numeric reference with no semicolon decodes in a block and stays in a paragraph the same way
  assert.equal(quote("<div>&#65 u &#x42 v &#; w</div>\n", "&#65 u &#x42 v &#; w"), "A u B v &#; w");
  assert.equal(shown("&#65 u end\n"), "&#65 u end");
});

test("a numeric character reference shows what the parser's numeric reference end state gives: U+FFFD for zero, a surrogate and a code past U+10FFFF, the windows-1252 character for a C1 control, the code point otherwise, in a paragraph and in an html block; an astral character in an html block maps one entry per code unit (before: the source form, a lone surrogate or the raw control, and a map one entry short per astral entity)", () => {
  const LINE = "Fish &amp; &#0; x &#xD800; y &#128; z &#150; w &#x110000; v &#65; u &#x1F600; end";
  const WANT = "Fish & " + REPL + " x " + REPL + " y " + EURO + " z " + NDASH + " w " + REPL + " v A u " + SMILE + " end";
  const PARA = LINE + "\n";
  assert.equal(shown(PARA), WANT, "a refused paragraph");
  for (const [q, w] of [["&#0; x", REPL + " x"], ["&#xD800; y", REPL + " y"], ["&#128; z", EURO + " z"], ["&#150; w", NDASH + " w"], ["&#x110000; v", REPL + " v"], ["&#65; u", "A u"], ["&#x1F600; end", SMILE + " end"]] as const) {
    assert.equal(quote(PARA, q), w, q + " in a paragraph");
  }
  const DIV = "<div>" + LINE + "</div>\n";
  assert.equal(shown(DIV), WANT, "an html block");
  for (const [q, w] of [["&#128; z", EURO + " z"], ["&#xD800; y", REPL + " y"], ["&#x1F600; end", SMILE + " end"]] as const) assert.equal(quote(DIV, q), w, q + " in an html block");
  const TWO = "<div>a &#x1F600; b &#x1F601; end</div>\n";
  const m = stripMarkupMapped(TWO);
  assert.equal(m.map.length, m.text.length, "one map entry per code unit of the text");
  assert.equal(quote(TWO, "a &#x1F600; b &#x1F601; end"), "a " + SMILE + " b " + GRIN + " end", "the needle keeps its last character");
  // the five holes of the windows-1252 table keep their code point; the other C1 codes take the table's character
  assert.equal(shown("&#129; &#141; &#159;\n"), "\u0081 \u008d \u0178");
});

test("an RCDATA element inline (a `<textarea>`, a `<title>`) shows everything up to its end tag as text, marked's HTML for the tokens between included and character references decoded, as the parser reads it and the sanitizer's unwrap leaves it, in a paragraph and in a cell; the html-block form reads so already (before: the tokens inside were read as markup, the needle `a b c` for a DOM showing `a <b>b</b> <em>c</em>`)", () => {
  const PARA = "Fish &amp; <textarea>a <b>b</b> *c*</textarea> end\n";
  assert.equal(shown(PARA), "Fish & a <b>b</b> <em>c</em> end");
  assert.equal(quote(PARA, "a <b>b</b> *c*"), "a <b>b</b> <em>c</em>", "the textarea's content");
  assert.equal(quote(PARA, "end"), "end");
  const CELL = "| h |\n|---|\n| x &amp; <textarea>a <b>b</b> *c*</textarea> y |\n";
  assert.equal(quote(CELL, "a <b>b</b> *c*"), "a <b>b</b> <em>c</em>", "the same in a cell");
  assert.equal(quote(CELL, "y"), "y");
  assert.equal(shown("Lead <title>t &amp; *u*</title> tail\n"), "Lead t & <em>u</em> tail", "an inline title");
  const BLOCK = "<div><textarea>d <i>e</i> *f*</textarea> tail</div>\n";
  assert.equal(quote(BLOCK, "d <i>e</i> *f*"), "d <i>e</i> *f*", "the block form: an html block's raw takes no emphasis (as before)");
  // no end tag in the block: the block's rest is the text (recorded; the parser reads on past the block)
  assert.equal(shown("Lead <textarea>open *x* tail\n"), "Lead open <em>x</em> tail");
});

test("inside an `<svg>` a `<title>` is an ordinary element, closed by its own end tag or by `</svg>` (foreign content; the parser's raw-text rule holds in HTML content alone): `<svg><title>inner title</svg> beside` reads `inner title beside` (before: the title's text ran to the block's end, tags and all, the one regression against round 2's regex strip)", () => {
  const OPEN = "Intro.\n\n<div><svg><title>inner title</svg> beside</div>\n\npara.\n";
  assert.equal(shown(OPEN), "Intro. inner title beside para.");
  assert.equal(quote(OPEN, "inner title</svg> beside"), "inner title beside", "a quote across the svg's end");
  const CLOSED = "Intro.\n\n<div><svg><title>inner title</title><text>t</text></svg> beside</div>\n\npara.\n";
  assert.equal(shown(CLOSED), "Intro. inner titlet beside para.");
  // in HTML content the rule stands: a textarea's content is text to its own end tag, tags inside it and all
  assert.equal(shown("<div><textarea>x</svg> y</textarea> z</div>\n"), "x</svg> y z");
  // a style inside an svg goes with its text (the sanitizer's drop), as in HTML content
  assert.equal(shown("<div><svg><style>.a{}</style><text>t</text></svg> z</div>\n"), "t z");
});

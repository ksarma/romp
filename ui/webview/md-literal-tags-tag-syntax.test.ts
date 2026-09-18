// Three edges of the rule for an inline start tag with no end tag in its block (md-literal-tags.ts; plans/file-review.md,
// decision 52), each found in the slice's review and fixed with the case that was red before it. The self-closing flag is read
// as the HTML tokenizer reads a tag (isSelfClosingTag): the `/` that ends an unquoted attribute value is the value's own last
// character, so `<a href=http://a.test/>` is a start tag with no end tag and renders as text; a suffix test on the raw kept it
// HTML, and the browser opened the `a` and wrapped every later block in it, the shape the rule exists to stop. The `image`
// start tag the parser rewrites to `img` is left HTML as `<img>` is (IMG_ALIAS), so a note that wrote its picture with the
// obsolete alias keeps the picture; the void list itself stays HTML's fourteen, the map's VOID_TAGS. Matching runs in a stack
// per name, linear in the run's tags: one list scanned from its end on every end tag was quadratic when thousands of stray end
// tags followed thousands of open start tags of another name, seconds on the main thread twice per open (the viewer's parse
// and the map's lex); the stacks convert the same tokens the one list did, held here against that list as an oracle over a
// fixed sample and a seeded random one. The rule's own suite is md-literal-tags.test.ts. Synthetic text only.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked, type Token, type Tokens } from "marked";
import { applyMdConfig } from "./md-config";
import { literalizeUnclosedTags, isSelfClosingTag, escapeInlineText, VOID_ELEMENTS } from "./md-literal-tags";

applyMdConfig();

/** The viewer's parse (mdBlock's three steps): the lexer, the rule, the parser. */
function viewerHtml(src: string): string { const tokens = marked.lexer(src); literalizeUnclosedTags(tokens); return marked.parser(tokens); }
/** The inline tokens of block `at` after the rule, flattened in document order. */
function inlineOf(src: string, at = 0): Token[] {
  const tokens = marked.lexer(src);
  literalizeUnclosedTags(tokens);
  const out: Token[] = [];
  const walk = (list: Token[]) => { for (const x of list) { out.push(x); const kids = (x as { tokens?: Token[] }).tokens; if (kids) walk(kids); } };
  walk((tokens[at] as { tokens?: Token[] }).tokens || []);
  return out;
}
/** `type:raw` of every tag among block `at`'s inline tokens: the html tokens, and the text tokens the rule made of tags. */
const tags = (src: string, at = 0): string[] => inlineOf(src, at).filter((t) => (t.type === "html" || t.type === "text") && /^<[!?\/a-zA-Z]/.test(t.raw) && t.raw.endsWith(">")).map((t) => t.type + ":" + t.raw);
const firstLine = (html: string): string => html.split("\n")[0];

test("isSelfClosingTag reads the flag as the HTML tokenizer does: `/` right before the `>` outside every attribute value, after a bare attribute, a quoted value or a blank; a `/` that ends an unquoted value is the value's, and an end tag or a non-tag has no flag", () => {
  for (const raw of ["<x/>", "<x />", "<a href=\"http://a.test/\"/>", "<a href='http://a.test/'/>", "<a b/>", "<a b />", "<a b=c />", "<a  b  =  \"c\"  />", "<a\tb/>", "<a b=\"c\" d/>", "<A HREF=\"X\"/>"]) {
    assert.equal(isSelfClosingTag(raw), true, raw + ": the flag");
  }
  for (const raw of ["<a href=http://a.test/>", "<b class=x/>", "<a b=/>", "<A HREF=X/>", "<img src=a.png/>", "<a b=c/ d>", "<a title=\"x/>y\">", "<a href=\"x\">", "<a>", "<a b>", "<a b=c>", "</a>", "</a/>", "<!-- x -->", "<?php ?>", "<![CDATA[ x ]]>", "plain"]) {
    assert.equal(isSelfClosingTag(raw), false, raw + ": no flag");
  }
});

test("FAILS BEFORE: a start tag whose unquoted attribute value ends in `/` is an open start tag (`<a href=http://a.test/>`, `<b class=x/>`, `<a b=/>`): with no end tag in its block it is text, where the suffix test kept it HTML and marked.parse still passes it through; closed in its block, or written with the flag after a quoted value, it stays HTML", () => {
  const SRC = "Slash <a href=http://a.test/>unquoted here.\n\nNext para words.\n\nClosing words.\n";
  assert.deepEqual(tags(SRC), ["text:<a href=http://a.test/>"], "the tag is text");
  assert.equal(firstLine(viewerHtml(SRC)), "<p>Slash &lt;a href=http://a.test/&gt;unquoted here.</p>", "the paragraph renders whole as text");
  assert.equal(firstLine(marked.parse(SRC) as string), "<p>Slash <a href=http://a.test/>unquoted here.</p>", "marked.parse alone passes the tag through (the viewer's rendering before, in which the browser opened the a and wrapped the later paragraphs in it)");
  assert.equal(viewerHtml(SRC).split("\n").slice(1).join("\n"), "<p>Next para words.</p>\n<p>Closing words.</p>\n", "the later blocks render as their own paragraphs");
  assert.deepEqual(tags("Class <b class=x/>rest.\n"), ["text:<b class=x/>"], "`<b class=x/>`: the `/` is the value's");
  assert.equal(firstLine(viewerHtml("Class <b class=x/>rest.\n")), "<p>Class &lt;b class=x/&gt;rest.</p>");
  assert.deepEqual(tags("Bare <a b=/>rest.\n"), ["text:<a b=/>"], "`<a b=/>`: the value is the `/`");
  assert.deepEqual(tags("Quoted <a href=\"http://a.test/\">rest.\n"), ["text:<a href=\"http://a.test/\">"], "the quoted form, text as before");
  assert.deepEqual(tags("Blank <a href=http://a.test/ >rest.\n"), ["text:<a href=http://a.test/ >"], "a blank before the `>`: no flag, text");
  const CLOSED = "Closed <a href=http://a.test/>x</a> tail.\n";
  assert.deepEqual(tags(CLOSED), ["html:<a href=http://a.test/>", "html:</a>"], "closed in its block: HTML on both ends");
  assert.equal(viewerHtml(CLOSED), marked.parse(CLOSED), "closed: marked.parse's output");
  for (const src of ["Flag <a href=\"http://a.test/\"/> tail.\n", "Flag <x/> tail.\n", "Flag <x /> tail.\n", "Flag <a b/> tail.\n", "Flag <a b=c /> tail.\n"]) {
    assert.equal(inlineOf(src).filter((t) => t.type === "text" && t.raw.startsWith("<")).length, 0, src.trim() + ": the flag, nothing converted");
    assert.equal(viewerHtml(src), marked.parse(src), src.trim() + ": marked.parse's output");
  }
});

test("FAILS BEFORE: an `image` start tag with no end tag stays HTML like `<img>` (the parser rewrites it to `img`, a void element, so the picture renders as it did), in a paragraph, upper case, a heading, a list item and a table cell, closed, and inside an inline `<svg>`; the void list itself is still HTML's fourteen; `keygen`, `basefont` and `bgsound` left open are text, the record's preference for a tag the sanitizer would drop unseen", () => {
  const TAG = "<image src=\"a.png\" alt=\"p\">";
  const SRC = `See ${TAG} here.\n`;
  assert.deepEqual(tags(SRC), ["html:" + TAG], "the alias is HTML");
  assert.equal(viewerHtml(SRC), marked.parse(SRC), "marked.parse's output, the picture's tag passed through");
  assert.equal(firstLine(viewerHtml(SRC)), `<p>See ${TAG} here.</p>`);
  assert.deepEqual(tags("See <IMAGE SRC=\"a.png\"> here.\n"), ["html:<IMAGE SRC=\"a.png\">"], "upper case");
  assert.deepEqual(tags(`# Head ${TAG} tail\n`), ["html:" + TAG], "in a heading");
  assert.deepEqual(tags(`- item ${TAG} tail\n`, 0).filter((s) => s.includes("image")), [], "a list token owns no run of its own");
  const list = marked.lexer(`- item ${TAG} tail\n`);
  literalizeUnclosedTags(list);
  const itemText = ((list[0] as Tokens.List).items[0].tokens[0] as Tokens.Text).tokens!;
  assert.deepEqual(itemText.filter((t) => t.raw === TAG).map((t) => t.type), ["html"], "in a list item");
  const table = marked.lexer(`| a | b |\n|---|---|\n| ${TAG} | d |\n`);
  literalizeUnclosedTags(table);
  assert.deepEqual((table[0] as Tokens.Table).rows[0][0].tokens.filter((t) => t.raw === TAG).map((t) => t.type), ["html"], "in a table cell");
  const CLOSED = `See ${TAG}</image> here.\n`;
  assert.deepEqual(tags(CLOSED), ["html:" + TAG, "html:</image>"], "closed: HTML on both ends, the end tag a stray");
  assert.equal(viewerHtml(CLOSED), marked.parse(CLOSED));
  const SVG = "Icon <svg><image href=\"a.png\"></image></svg> tail.\n";
  assert.deepEqual(tags(SVG), ["html:<svg>", "html:<image href=\"a.png\">", "html:</image>", "html:</svg>"], "an svg's image with its own end tag: HTML throughout");
  assert.equal(viewerHtml(SVG), marked.parse(SVG));
  assert.equal(VOID_ELEMENTS.has("IMAGE"), false, "the void list, the map's VOID_TAGS, is HTML's own set");
  assert.equal(VOID_ELEMENTS.size, 14);
  for (const name of ["keygen", "basefont", "bgsound"]) {
    const src = `Lead <${name}> rest.\n`;
    assert.deepEqual(tags(src), [`text:<${name}>`], `<${name}> left open: text`);
    assert.equal(firstLine(viewerHtml(src)), `<p>Lead ${escapeInlineText(`<${name}>`)} rest.</p>`);
  }
});

/** The header's rule spelled as one list of the open start tags scanned from its end on every end tag: the shape the module had,
 *  the oracle for the stacks. Reads the sample's alphabet alone (non-void names, no attributes). */
function oneList(tokens: Token[]): void {
  for (const t of tokens) {
    const run = (t as { tokens?: Token[] }).tokens;
    if (!run) continue;
    const open: { name: string; token: Token }[] = [];
    const read = (list: Token[]): void => {
      for (const x of list) {
        if (x.type === "html") {
          const m = /^<(\/?)([a-zA-Z][\w:-]*)/.exec(x.raw)!;
          const name = m[2].toUpperCase();
          if (m[1]) { for (let i = open.length - 1; i >= 0; i--) if (open[i].name === name) { open.splice(i, 1); break; } }
          else open.push({ name, token: x });
          continue;
        }
        const kids = (x as { tokens?: Token[] }).tokens;
        if (kids) read(kids);
      }
    };
    read(run);
    for (const o of open) { const r = o.token as unknown as Record<string, unknown>; r.type = "text"; r.text = escapeInlineText(o.token.raw); delete r.pre; delete r.block; delete r.inLink; delete r.inRawBlock; }
  }
}
const withRule = (src: string): string => { const tokens = marked.lexer(src); literalizeUnclosedTags(tokens); return JSON.stringify(tokens); };
const withOracle = (src: string): string => { const tokens = marked.lexer(src); oneList(tokens); return JSON.stringify(tokens); };

test("the stacks per name convert the tokens the one list converted: the header's cases, interleaved and repeated names, a closer in the other case, a stray closer first, and 400 seeded random runs over b, i and u tags, text and emphasis", () => {
  const fixed = ["A <b>x<b>y</b> z.\n", "A <B>x</b> z.\n", "A <b>x *y</b>* z.\n", "A <b><i>x</b> z.\n", "A <b><i>x</b>y</i> z.\n", "A <i><b>x</i> z.\n", "A <b><b>x</b> z.\n", "A <b>x</b></b> z.\n", "A <B>x<b>y</B>z</b> w.\n", "A </b><b>x z.\n", "A <b>x</i><i>y</b> z.\n", "A <u><b><i>x</b></u> z.\n", "A <b>x<b>y<b>z</b></b> w.\n", "A <em>x<b>y</em> z.\n"];
  for (const src of fixed) assert.equal(withRule(src), withOracle(src), src.trim());
  let seed = 20260918;
  const rand = (n: number): number => { seed = (seed * 1103515245 + 12345) & 0x7fffffff; return seed % n; };
  const alphabet = ["<b>", "<i>", "<u>", "</b>", "</i>", "</u>", "<B>", "</I>", "x", "*y*", "*<b>y*", "[<i>z](http://a.test)", "`<b>`"];
  let converted = 0;
  for (let k = 0; k < 400; k++) {
    const parts: string[] = [];
    for (let j = 0, len = 1 + rand(12); j < len; j++) parts.push(alphabet[rand(alphabet.length)]);
    const src = "A " + parts.join(" ") + " z.\n";
    const rule = withRule(src);
    assert.equal(rule, withOracle(src), src.trim());
    converted += (rule.match(/"type":"text","raw":"<[a-zA-Z]/g) || []).length;
  }
  assert.ok(converted > 400, "the sample exercises the conversion: " + converted);
});

test("matching is linear in the run's tags: forty thousand open `<b>` followed by forty thousand stray `</i>` in one run convert in well under a second per pass (the one list took seconds, scanning every open tag on every stray)", () => {
  const N = 40000;
  const build = (): Token[] => {
    const run: Token[] = [];
    for (let i = 0; i < N; i++) run.push({ type: "html", raw: "<b>", text: "<b>", pre: false, block: false } as unknown as Token);
    for (let i = 0; i < N; i++) run.push({ type: "html", raw: "</i>", text: "</i>", pre: false, block: false } as unknown as Token);
    return [{ type: "paragraph", raw: "", text: "", tokens: run } as unknown as Token];
  };
  let best = Infinity;
  let last: Token[] = [];
  for (let k = 0; k < 3; k++) {   // the least of three passes: a starved pass on a loaded box does not fail the test alone
    const tokens = build();
    const t0 = performance.now();
    literalizeUnclosedTags(tokens);
    best = Math.min(best, performance.now() - t0);
    last = tokens;
  }
  const run = (last[0] as Tokens.Paragraph).tokens;
  assert.equal(run.filter((t) => t.type === "text").length, N, "every open `<b>` is text");
  assert.equal(run.filter((t) => t.type === "html").length, N, "every stray `</i>` is HTML still");
  assert.ok(best < 2500, `a pass over ${2 * N} tags took ${best.toFixed(0)} ms`);
});

// An inline start tag with no end tag in its block renders as literal text, and the anchor map places it (plans/file-review.md,
// decision 52). marked lexes a tag mid-line (`(<table>__widths.csv)` in a note's prose) as an inline `html` token and passes it
// through as HTML, and the browser's parser then does what an unclosed tag does. A `<table>` start tag inside a `<p>` in
// DOMPurify's quirks-mode document (md-sanitize.ts parses with no doctype) closes no `<p>`: it opened a table inside the
// paragraph's element and the next heading, paragraph and table were parsed into it, so the anchor map (anchor-map.ts), which
// predicted no text for an inline tag and pairs blocks with top-level elements one for one, refused that paragraph as not
// matching the file and every block after it met the element three places on (150 of 189 blocks of one note). An inline
// `<title>`, `<script>`, `<style>`, `<textarea>`, `<xmp>`, `<iframe>`, `<plaintext>` or `<template>` start tag took the rest
// of the note as its text, which the sanitizer then dropped or showed as raw text.
//
// The rule: an inline `html` token that is a START tag of a non-void element, with no matching end tag later in the SAME
// block's inline tokens, becomes a `text` token in place. Its raw is kept, so the map places it where the lexer found it; its
// text is the raw escaped as marked's inline text tokenizer escapes text (escapeInlineText), so marked's text renderer writes
// `&lt;table&gt;`, the reader sees `<table>` and the map's `text` case emits the raw's characters (anchor-map.ts walkInline,
// plainInline and lenientInline), with no case for the shape on either side. Everything else is left as lexed: a start tag
// closed within its block (`<b>x</b>`, `<span class="a">y</span>`, `<kbd>Ctrl</kbd>`), a void element (VOID_ELEMENTS),
// the self-closing syntax `<x/>`, an end tag (a stray one keeps anchor-map.ts blockEnds' reading), a comment, a processing
// instruction, a declaration and a CDATA section. Matching is by element name, ASCII case-insensitive, innermost first: one
// list of the open start tags over the block's inline tokens flattened in document order (a tag inside emphasis, a link's
// label or a highlight counts), an end tag closing the latest open tag of its name, so `<b>x<b>y</b>` keeps the inner pair
// as HTML and makes the first `<b>` text, `<B>x</b>` is closed and `<b>x *y</b>*` is closed through the emphasis. The block is
// the token that owns the inline run, each on its own: a paragraph, a heading, a tight list item's text, a footnote
// definition, a table cell; a list, a quote and a callout are walked into for the blocks they hold. Block-level `html` tokens
// are not read here: the tag scan (anchor-map.ts topTags) models what the parser makes of an html block.
//
// ONE rule, one code path. The viewer runs this on the tokens of each parse (file-view.ts mdBlock, between marked's lexer and
// its parser, on that parse's own token tree, so the chat's md(), which parses the same singleton, renders as before) and the
// map runs it on its own lex of the same source (anchor-map.ts placeTokens, right after Lexer.lex), before anything reads the
// tokens; both lex the same text under the one configuration (md-config.ts), so both convert the same tokens. Deliberately
// left, recorded in the plan: `<hr>` inline is void, stays HTML and still splits its paragraph in the parser; a start tag whose
// end tag stands in a LATER block renders as text now, where the parser used to wrap the blocks between in its element; a
// block-level element closed within its block mid-line (`<div>x</div>`) still splits the paragraph in the parser. marked's
// inline lexer state is not rewound: after an unclosed `<kbd>`, `<pre>`, `<code>` or `<script>` tag it lexes the block's
// remaining text unescaped (its inRawBlock flag), and after an unclosed `<a` tag it autolinks no bare URL (inLink), as before.
import type { Token, Tokens } from "marked";

/** HTML's void elements, upper case: a start tag of one opens nothing to close, so it stays HTML wherever it stands. The tag
 *  scans of anchor-map.ts (topTags, blockEnds, leafTag, nextIsTablePart) read this same set. */
export const VOID_ELEMENTS: ReadonlySet<string> = new Set(["AREA", "BASE", "BR", "COL", "EMBED", "HR", "IMG", "INPUT", "LINK", "META", "PARAM", "SOURCE", "TRACK", "WBR"]);

/** An inline `html` token's tag: `/` for an end tag, then the name (marked's inline tag rule: a letter, then letters, digits, `_`,
 *  `-` and, in an end tag, `:`). No match for a comment, a declaration, a processing instruction or a CDATA section. */
const TAG_RE = /^<(\/?)([a-zA-Z][\w:-]*)/;
/** The self-closing syntax, `<x/>` or `<x />`: left as HTML (the parser ignores the flag on an HTML element and closes the element
 *  at once in foreign content; anchor-map.ts leafTag reads it so). */
const SELF_CLOSING_RE = /\/>$/;

/** marked's escape of inline text (marked 12's escape$1 with `encode` false, the inline text tokenizer's call): `<`, `>`, `"`
 *  and `'` always, `&` unless it begins a character reference, which the browser decodes to one character (the map refuses
 *  such prose as it refuses it in any text token, anchor-map.ts ENTITY_RE). */
const ESCAPE_RE = /[<>"']|&(?!(?:#\d{1,7}|#[Xx][a-fA-F0-9]{1,6}|\w+);)/g;
const ESCAPES: Record<string, string> = { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" };
export const escapeInlineText = (s: string): string => s.replace(ESCAPE_RE, (c) => ESCAPES[c]);

/** The inline runs of `tokens`, a lexed block-token tree, converted in place: in each run every non-void start tag with no end
 *  tag of its name later in the run is now a `text` token (the header's rule). Idempotent: a converted token is text, which the
 *  walk does not read. */
export function literalizeUnclosedTags(tokens: Token[]): void {
  for (const t of tokens) {
    switch (t.type) {
      case "paragraph": case "heading": case "text": case "footnoteDef": {
        const run = (t as { tokens?: Token[] }).tokens;   // a block-level `text` token (a tight list item's line) owns a run; an inline one has none
        if (run) literalizeRun(run);
        break;
      }
      case "table": {
        const tt = t as Tokens.Table;
        for (const cell of tt.header) literalizeRun(cell.tokens);
        for (const row of tt.rows) for (const cell of row) literalizeRun(cell.tokens);
        break;
      }
      case "list": for (const item of (t as Tokens.List).items) literalizeUnclosedTags(item.tokens); break;
      default: {
        // a container of blocks (a blockquote, a callout): its blocks; a token with no children (an html block, code, a rule, a
        // display formula, the front matter) has nothing to read
        const kids = (t as { tokens?: Token[] }).tokens;
        if (kids) literalizeUnclosedTags(kids);
      }
    }
  }
}

/** One block's inline run: its html tokens in document order, a tag inside emphasis, a link's label or a highlight included,
 *  matched by name innermost first; the start tags left open at the run's end are converted. */
function literalizeRun(tokens: Token[]): void {
  const open: { name: string; token: Token }[] = [];
  const read = (list: Token[]): void => {
    for (const t of list) {
      if (t.type === "html") {
        const m = TAG_RE.exec(t.raw);
        if (!m) continue;   // a comment, a declaration, a processing instruction, a CDATA section
        const name = m[2].toUpperCase();
        if (m[1]) {
          // an end tag closes the latest open start tag of its name; naming none, it is a stray, blockEnds' to read
          for (let i = open.length - 1; i >= 0; i--) if (open[i].name === name) { open.splice(i, 1); break; }
        } else if (!VOID_ELEMENTS.has(name) && !SELF_CLOSING_RE.test(t.raw)) open.push({ name, token: t });
        continue;
      }
      const kids = (t as { tokens?: Token[] }).tokens;
      if (kids) read(kids);
    }
  };
  read(tokens);
  for (const o of open) toText(o.token);
}

/** The token as a `text` token: its raw kept, its text the raw escaped as marked's inline text tokenizer escapes text (marked's
 *  text renderer writes a text token's text as is), the html token's own fields gone (Tokens.HTML, Tokens.Tag). */
function toText(t: Token): void {
  const o = t as unknown as Record<string, unknown>;
  o.type = "text";
  o.text = escapeInlineText(t.raw);
  delete o.pre; delete o.block; delete o.inLink; delete o.inRawBlock;
}

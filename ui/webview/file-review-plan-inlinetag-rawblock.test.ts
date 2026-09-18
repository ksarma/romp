// The scope of marked's inline lexer state through the two lexes the viewer runs, as decision 52 of plans/file-review.md
// records it among the shapes it deliberately left: marked keeps `inRawBlock` and `inLink` on the one Lexer that lexes a
// document and resets neither between blocks, so after an inline `<kbd>`, `<pre>`, `<code>` or `<script>` start tag with no
// end tag the rest of that block AND every later block is lexed unescaped, until an end tag of any of those four names or the
// document's end, and after an unclosed `<a` no bare URL is autolinked in that block or any later one until an `</a>`. The
// literal-tags rule (md-literal-tags.ts) runs after the lex and changes no lexer state, so the scope is the same before and
// after decision 52, and it is the scope of both callers: mdBlock (file-view.ts) lexes with marked.lexer over a copy of the
// singleton's defaults, placeTokens (anchor-map.ts) with the static Lexer.lex over the module defaults, each once over the
// whole document, then the rule. This module runs both lexes as they run there, under the one configuration (md-config.ts),
// and reads the later blocks' text tokens and, for the viewer's path, the parser's output.
// Why this module beside tools/file-review-plan-inlinetag-rawblock.test.mjs, which holds the same sentence to the plan's
// text: that module lexes with marked's bare Lexer when vscode-extension/node_modules is installed and skips its lexer legs
// otherwise, and CI's shell job, the one runner of tools/*.test.mjs, runs no npm ci, so those legs skipped in every CI run
// (review find, 2026-09-18). This file is built and run by the extension job's `npm test` (esbuild.js's test build takes
// every .test.ts under ui/webview), so a marked release that resets the state between blocks goes red in CI here, and the
// tools module holds this file and its runner to the tree. Synthetic text only.
import { test } from "node:test";
import assert from "node:assert/strict";
import { marked, Lexer, type Token } from "marked";
import { applyMdConfig } from "./md-config";
import { literalizeUnclosedTags } from "./md-literal-tags";

applyMdConfig();

type Lex = (src: string) => Token[];
/** mdBlock's lex (file-view.ts): marked.lexer over a copy of the singleton's defaults, then the rule. */
const viewerLex: Lex = (src) => { const opts = { ...marked.defaults }; const tokens = marked.lexer(src, opts); literalizeUnclosedTags(tokens); return tokens; };
/** placeTokens' lex (anchor-map.ts): the static Lexer.lex over the module defaults, then the rule. */
const mapLex: Lex = (src) => { const tokens = Lexer.lex(src); literalizeUnclosedTags(tokens); return tokens; };
const LEXES: Array<[string, Lex]> = [["mdBlock's lex", viewerLex], ["placeTokens' lex", mapLex]];
/** The viewer's HTML: mdBlock's lexer, the rule and its parser, over one copy of the defaults (its walkTokens changes no text). */
function viewerHtml(src: string): string {
  const opts = { ...marked.defaults };
  const tokens = marked.lexer(src, opts);
  literalizeUnclosedTags(tokens);
  return marked.parser(tokens, opts);
}
/** Each paragraph's and heading's inline run as one string: a text token's text as it is (escaped or not, which is the
 *  point), any other token as `[type:raw]`. */
function inlineText(tokens: Token[]): string[] {
  return tokens
    .filter((t) => t.type === "paragraph" || t.type === "heading")
    .map((t) => ((t as { tokens?: Token[] }).tokens || []).map((x) => (x.type === "text" ? (x as { text: string }).text : `[${x.type}:${x.raw}]`)).join(""));
}
/** Each paragraph's inline token types, joined. */
function types(tokens: Token[]): string[] {
  return tokens.filter((t) => t.type === "paragraph").map((t) => ((t as { tokens?: Token[] }).tokens || []).map((x) => x.type).join(","));
}

const LATER = "Later a & b <y then d.\n\n# Head a & b <y\n\nClosing a & b <y then d.\n";
const ESCAPED = ["Later a &amp; b &lt;y then d.", "Head a &amp; b &lt;y", "Closing a &amp; b &lt;y then d."];
const RAW = ["Later a & b <y then d.", "Head a & b <y", "Closing a & b <y then d."];

test("after an unclosed <kbd>, <pre>, <code> or <script> both lexes leave the rest of its block and every later block unescaped, to the document's end, the tag itself literal text; the viewer's parser then writes the later text as is", () => {
  for (const [name, lex] of LEXES) {
    assert.deepEqual(inlineText(lex("Plain a & b.\n\n" + LATER)).slice(1), ESCAPED, `${name}: the control escapes every later block`);
    for (const tag of ["kbd", "pre", "code", "script"]) {
      const got = inlineText(lex(`Open <${tag}>here a & b.\n\n` + LATER));
      assert.equal(got[0], `Open &lt;${tag}&gt;here a & b.`, `${name}, ${tag}: the tag is literal text and the rest of its block is unescaped`);
      assert.deepEqual(got.slice(1), RAW, `${name}, ${tag}: every later block, a heading among them, is unescaped`);
    }
  }
  const control = viewerHtml("Plain a & b.\n\n" + LATER);
  assert.ok(control.includes("<p>Plain a &amp; b.</p>") && control.includes("<p>Later a &amp; b &lt;y then d.</p>"), "the control renders every block escaped: " + control);
  const raw = viewerHtml("Open <kbd>here a & b.\n\n" + LATER);
  assert.ok(raw.includes("<p>Open &lt;kbd&gt;here a & b.</p>"), "the opening block: the tag escaped by the rule, the rest of the block written as lexed: " + raw);
  assert.ok(raw.includes("<p>Later a & b <y then d.</p>"), "the later paragraph's text is written as is (the browser then reads `<y then d.</p>` as a tag, the loss the record names): " + raw);
});

test("an end tag of any of the four names clears the flag, whichever of them opened it, and escaping resumes; an end tag of another name does not", () => {
  for (const [name, lex] of LEXES) {
    assert.deepEqual(
      inlineText(lex("Open <kbd>here.\n\nStill raw a & b.\n\nStray </code> then a & b <y.\n\nAfter a & b <y then d.\n")),
      ["Open &lt;kbd&gt;here.", "Still raw a & b.", "Stray [html:</code>] then a &amp; b &lt;y.", "After a &amp; b &lt;y then d."],
      `${name}: a stray </code> closes an open <kbd>, and the end tag stays html`,
    );
    assert.deepEqual(inlineText(lex("Open <kbd>here.\n\nStray </b> then a & b <y.\n")), ["Open &lt;kbd&gt;here.", "Stray [html:</b>] then a & b <y."], `${name}: a </b> clears nothing`);
  }
});

test("after an unclosed <a both lexes autolink no bare URL in that block or any later one until an </a>, the tag itself literal text; the viewer renders the later URL as plain text", () => {
  const OPEN = 'Open <a href="x">here.\n\nSee https://example.test/a now.\n\nStray </a> here.\n\nSee https://example.test/b now.\n';
  for (const [name, lex] of LEXES) {
    assert.deepEqual(types(lex("See https://example.test/a now.\n")), ["text,link,text"], `${name}: the control autolinks`);
    assert.deepEqual(types(lex(OPEN)), ["text,text,text", "text", "text,html,text", "text,link,text"], `${name}: no link in the later block until the </a>; a link after it; the stray </a> stays html`);
  }
  const control = viewerHtml("See https://example.test/a now.\n");
  assert.ok(control.includes('<a href="https://example.test/a">'), "the control renders a link: " + control);
  const raw = viewerHtml(OPEN);
  assert.ok(raw.includes("<p>Open &lt;a href=&quot;x&quot;&gt;here.</p>"), "the opening block renders the tag as text: " + raw);
  assert.ok(raw.includes("<p>See https://example.test/a now.</p>") && raw.includes('<a href="https://example.test/b">'), "the later URL is plain text until the </a>, a link after it: " + raw);
});

test("both lexes see one token tree: the same paragraph and heading text for every document above", () => {
  const DOCS = ["Plain a & b.\n\n" + LATER, "Open <kbd>here a & b.\n\n" + LATER, "Open <script>here a & b.\n\n" + LATER, "Open <kbd>here.\n\nStray </code> then a & b <y.\n", 'Open <a href="x">here.\n\nSee https://example.test/a now.\n\nStray </a> here.\n\nSee https://example.test/b now.\n'];
  for (const src of DOCS) {
    assert.deepEqual(inlineText(viewerLex(src)), inlineText(mapLex(src)), JSON.stringify(src) + ": the same inline text");
    assert.deepEqual(types(viewerLex(src)), types(mapLex(src)), JSON.stringify(src) + ": the same token types");
  }
});

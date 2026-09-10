// The one markdown configuration (md-config.ts; plans/markdown-viewer.md Slice 4, "one markdown configuration,
// Obsidian constructs included"), executed over the REAL marked: applyMdConfig() on the singleton, the fixture every
// construct is written into (anchor-map-fixtures/obsidian.md), each construct's rendered element, the resolved and the
// unresolved wikilink, the user-text instance's parity, the function's idempotence, and the source pins for who calls
// it. No DOM and no sanitizer here (the browser leg, md-config-obsidian-browser.test.ts, opens the fixture in the real
// Files bundle through DOMPurify and reads the elements from the page); the shapes asserted are marked's own output,
// which is what the sanitizer is handed. Synthetic fixture only: an invented note.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { marked, Lexer } from "marked";
import { applyMdConfig, mdExtensions, resolveWikilink, calloutTitle, isYamlMapping, callout, markView, WIKILINK_DEAD_TITLE, FRONT_MATTER_LABEL, FOOTNOTE_ORPHAN_TITLE, MARK_CLASS } from "./md-config";
import { userMdHtml } from "./chat-md";

const UI = (f: string) => fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", f), "utf8");
const FIXTURE = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "anchor-map-fixtures", "obsidian.md"), "utf8");
applyMdConfig();
const html = (src: string): string => marked.parse(src) as string;
/** The file kind's parse: mdBlock's per-call walkTokens stamps every wikilink resolved (file-view-links.ts viewerWalkTokens). */
const fileHtml = (src: string): string => marked.parse(src, { walkTokens: (t) => { resolveWikilink(t); } }) as string;
/** One root element and nothing else: the shape every block construct must render as, for the anchor map's 1:1 pairing. */
const oneRoot = (out: string, tag: string): void => {
  assert.match(out, new RegExp("^<" + tag + "\\b[^>]*>[\\s\\S]*</" + tag + ">\\n?$"), "one " + tag + " and nothing beside it: " + out);
  assert.equal((out.match(new RegExp("<" + tag + "\\b", "g")) || []).length, 1, "one opening tag: " + out);
};

test("applyMdConfig is idempotent: a second call registers nothing twice, and the extensions reach the static lexer", () => {
  const ext = marked.defaults.extensions as { block?: unknown[]; inline?: unknown[] } | undefined;
  const before = { block: ext?.block?.length, inline: ext?.inline?.length };
  applyMdConfig(); applyMdConfig();
  const after = marked.defaults.extensions as { block?: unknown[]; inline?: unknown[] } | undefined;
  assert.deepEqual({ block: after?.block?.length, inline: after?.inline?.length }, before, "the tokenizer lists are unchanged by the repeat calls");
  assert.ok((before.block || 0) >= 4 && (before.inline || 0) >= 4, "the block and inline extensions are registered: " + JSON.stringify(before));
  // the static Lexer.lex reads the module defaults marked.use wrote, so the anchor map's lexer sees the same tokens the renderer renders
  const types = Lexer.lex(FIXTURE).map((t) => t.type);
  for (const want of ["frontMatter", "footnoteDef", "callout", "mathBlock", "paragraph", "heading"]) assert.ok(types.includes(want), want + " in " + types.join(","));
  const inline = (Lexer.lex("a [^1] ==b== [[c]] $d$ ~~e~~\n\n[^1]: d")[0] as { tokens: Array<{ type: string }> }).tokens.map((t) => t.type);   // the reference needs its definition (below)
  assert.deepEqual(inline.filter((t) => t !== "text"), ["footnoteRef", "mark", "wikilink", "mathInline", "del"]);
});

test("front matter: one folded element at the document's start, the YAML shown; never mid-document or inside a quote", () => {
  const out = html("---\ntitle: Test Note\ntags: [a, b]\n---\n\nPara.\n");
  assert.match(out, /^<details class="md-frontmatter"><summary class="md-frontmatter-head">Front matter<\/summary><pre>title: Test Note\ntags: \[a, b\]<\/pre><\/details><p>Para\.<\/p>\n$/);
  assert.equal(FRONT_MATTER_LABEL, "Front matter");
  oneRoot(html("---\na: 1\n---\n"), "details");
  assert.match(html("---\n---\nx"), /^<details class="md-frontmatter"><summary class="md-frontmatter-head">Front matter<\/summary><pre><\/pre><\/details><p>x<\/p>\n$/, "an empty block folds too");
  assert.doesNotMatch(html("Para.\n\n---\na: 1\n---\n"), /md-frontmatter/, "mid-document it is an hr and a setext heading, as it always was");
  assert.doesNotMatch(html("> ---\n> a: 1\n> ---\n"), /md-frontmatter/, "a quote's body is not the document's start");
  assert.match(html("---\ntitle: <b>x</b> & y\n---\n"), /<pre>title: &lt;b&gt;x&lt;\/b&gt; &amp; y<\/pre>/, "the YAML is text, never markup");
  assert.equal(Lexer.lex("---\na: 1\n---\n\nPara")[0].raw, "---\na: 1\n---\n\n", "the token's raw tiles the source from offset 0, trailing blank lines included");
});

test("footnotes: a reference is a numbered sup link, a definition renders IN PLACE as one div holding a paragraph that opens with the back link, numbered by order of first reference; a URL-only definition is a footnote, not a swallowed link definition", () => {
  const out = html("Ref[^b] and [^a] then [^b] again.\n\n[^a]: Def A\n    continued\n\n[^b]: https://example.test/def-only\n\nAfter.\n");
  assert.match(out, /<p>Ref<sup class="md-fnref"><a href="#fn-b" id="fnref-b">1<\/a><\/sup> and <sup class="md-fnref"><a href="#fn-a" id="fnref-a">2<\/a><\/sup> then <sup class="md-fnref"><a href="#fn-b" id="fnref-b-2">1<\/a><\/sup> again\.<\/p>/, "numbered by first reference; a second reference to the same note keeps its own id");
  assert.match(out, /<div class="md-footnote" id="fn-a"><p><a class="md-fnback" href="#fnref-a" title="Back to the text">2<\/a> Def A\ncontinued<\/p><\/div>/, "the definition in place, its body a paragraph inside the div (round 10: its spaces paint as a paragraph's), its continuation line de-indented");
  assert.match(out, /<div class="md-footnote" id="fn-b"><p><a class="md-fnback" href="#fnref-b" title="Back to the text">1<\/a> <a href="https:\/\/example\.test\/def-only">https:\/\/example\.test\/def-only<\/a><\/p><\/div>/, "the URL-only definition renders (marked's def rule used to swallow it)");
  assert.ok(out.indexOf("fn-a") < out.indexOf("<p>After."), "in place, before the paragraph that follows it");
  oneRoot(html("[^1]: only a definition\n"), "div");
  assert.match(html("[^x]: unreferenced\n"), /<span class="md-fnback" title="[^"]+">\[\^x\]:<\/span> unreferenced/, "a definition nothing refers to shows its marker as written, and has no back link to a reference that is not there (below)");
  assert.match(html("[^1]: <b>x</b> & \"y\"\n"), /id="fn-1"/);
  assert.match(html("[^a\"b]: x\n"), /id="fn-a&quot;b"/, "the id is escaped in the attribute");
});

test("callouts: GitHub's alerts and Obsidian's titled types render as one blockquote with a title line and a class per type; the fold markers give a details, closed for - and open for +", () => {
  const gh = html("> [!NOTE]\n> GitHub alert body.\n\nAfter.\n");
  assert.match(gh, /^<blockquote class="md-callout md-callout-note"><p class="md-callout-title">Note<\/p><p>GitHub alert body\.<\/p>\n<\/blockquote><p>After\.<\/p>\n$/);
  for (const [kind, title] of [["TIP", "Tip"], ["IMPORTANT", "Important"], ["WARNING", "Warning"], ["CAUTION", "Caution"]]) {
    assert.match(html(`> [!${kind}]\n> body\n`), new RegExp(`<blockquote class="md-callout md-callout-${kind.toLowerCase()}"><p class="md-callout-title">${title}</p>`), kind);
  }
  const titled = html("> [!note] Title here\n> Callout body line.\n> Second **bold** line.\n");
  assert.match(titled, /^<blockquote class="md-callout md-callout-note"><p class="md-callout-title">Title here<\/p><p>Callout body line\.\nSecond <strong>bold<\/strong> line\.<\/p>\n<\/blockquote>\n?$/, "the author's title, the body as blocks");
  oneRoot(html("> [!note] T\n> body\n"), "blockquote");
  assert.match(html("> [!tip]- Folded tip\n> Hidden body.\n"), /^<details class="md-callout md-callout-tip"><summary class="md-callout-title">Folded tip<\/summary><p>Hidden body\.<\/p>\n<\/details>\n?$/, "- folds closed");
  assert.match(html("> [!tip]+ Open tip\n> Shown body.\n"), /^<details class="md-callout md-callout-tip" open><summary class="md-callout-title">Open tip<\/summary>/, "+ folds open");
  oneRoot(html("> [!tip]- T\n> body\n"), "details");
  assert.match(html("> [!My-Type] x\n> y\n"), /class="md-callout md-callout-my-type"/, "any type is a class, lower-cased");
  assert.match(html("> [!note] <b>t</b>\n> y\n"), /<p class="md-callout-title">&lt;b&gt;t&lt;\/b&gt;<\/p>/, "the title is text, never markup");
  assert.equal(calloutTitle({ kind: "CAUTION", title: "" }), "Caution");
  assert.equal(calloutTitle({ kind: "note", title: "Given" }), "Given");
  assert.match(html("> plain quote\n"), /^<blockquote>\n<p>plain quote<\/p>\n<\/blockquote>\n$/, "an ordinary quote is untouched");
  assert.match(html("- item\n  > [!note]\n  > nested\n"), /<li>item\n?<blockquote class="md-callout md-callout-note">/, "inside a list item too, as any block (a tight list puts no newline before it)");
});

test("==mark== renders <mark class=\"md-mark\"> with inline content; the opener must touch its content, so a comparison in prose stays literal", () => {
  assert.equal(html("a ==b **c**== d"), "<p>a <mark class=\"md-mark\">b <strong>c</strong></mark> d</p>\n");
  assert.equal(html("x == y == z"), "<p>x == y == z</p>\n");
  assert.equal(html("`a ==b== c`"), "<p><code>a ==b== c</code></p>\n", "a code span is left alone");
});

test("wikilinks and embeds: anchors in a file document (the walkTokens stamp), the dead styled span showing the source as written everywhere else; an image embed is an <img>, any other embed a link-shaped chip", () => {
  const src = "Wiki [[Note]], [[Note|alias]], [[Note#Heading]], [[#Heading Two]], [[img.png]] and [[docs/Sub Note]].\n\nEmbed ![[image.png]], ![[Note]], ![[image.png|300]], ![[image.png|300x200]] and ![[paper.pdf]].\n";
  const dead = html(src);
  const span = (text: string) => `<span class="fv-wikilink fv-dead" title="${WIKILINK_DEAD_TITLE}">${text}</span>`;
  assert.equal(dead, `<p>Wiki ${span("[[Note]]")}, ${span("[[Note|alias]]")}, ${span("[[Note#Heading]]")}, ${span("[[#Heading Two]]")}, ${span("[[img.png]]")} and ${span("[[docs/Sub Note]]")}.</p>\n`
    + `<p>Embed ${span("![[image.png]]")}, ${span("![[Note]]")}, ${span("![[image.png|300]]")}, ${span("![[image.png|300x200]]")} and ${span("![[paper.pdf]]")}.</p>\n`,
    "unresolved (the chat, a URL document): no anchor, no img, the source as written with its brackets (the review: the alias alone read as plain text)");
  assert.doesNotMatch(WIKILINK_DEAD_TITLE, /—|fleet/i);
  const live = fileHtml(src);
  assert.equal(live, '<p>Wiki <a href="Note.md">Note</a>, <a href="Note.md">alias</a>, <a href="Note.md#Heading">Note#Heading</a>, <a href="#Heading%20Two">#Heading Two</a>, <a href="img.png">img.png</a> and <a href="docs/Sub%20Note.md">docs/Sub Note</a>.</p>\n'
    + '<p>Embed <img src="image.png" alt="image.png">, <a class="fv-embed" href="Note.md">Note</a>, <img src="image.png" alt="image.png" width="300">, <img src="image.png" alt="image.png" width="300" height="200"> and <a class="fv-embed" href="paper.pdf">paper.pdf</a>.</p>\n',
    "resolved: `.md` appended to a bare name, an extension kept, the fragment carried, marked's percent-encoding, the embed's size");
  assert.equal(html("[[a|b]] text"), `<p>${span("[[a|b]]")} text</p>\n`);
  assert.equal(html("not [[ a ]] wiki"), `<p>not ${span("[[ a ]]")} wiki</p>\n`, "the dead span shows the source text as written, spaces included");
  assert.equal(html("matrix[[0]] here"), `<p>matrix${span("[[0]]")} here</p>\n`, "an R-style index in a reply keeps its brackets");
  assert.equal(html("`[[code]]` and \\[[esc]]"), "<p><code>[[code]]</code> and [[esc]]</p>\n", "a code span and an escaped bracket are left alone");
  const tok = (Lexer.lex("x [[Note|alias]] y")[0] as { tokens: Array<Record<string, unknown>> }).tokens[1];
  assert.equal(tok.type, "wikilink"); assert.equal(tok.text, "alias"); assert.equal(tok.textOffset, 7, "the anchor map places the shown text at textOffset in the raw");
  assert.equal((tok.raw as string).slice(7, 12), "alias");
});

test("math: the placeholders KaTeX fills after the sanitize are the singleton's (the files and feed bundles carry the grammar through md-config.ts)", () => {
  assert.equal(html("Inline $x^2$ math."), '<p>Inline <span class="md-math-inline">x^2</span> math.</p>\n');
  assert.equal(html("$$\n\\sum_i i\n$$\n"), '<div class="md-math-display">\\sum_i i</div>');
  assert.equal(html("a ~~b~~ ~c~"), "<p>a <del>b</del> ~c~</p>\n", "the ~~-only del rule rides in the same list");
});

test("the fixture renders every construct's element, once each, in order; the user-text instance renders each single-line snippet identically", () => {
  const out = html(FIXTURE);
  const order = ['<details class="md-frontmatter">', "<h1>Heading One</h1>", '<sup class="md-fnref">', "<mark class=\"md-mark\">marked text</mark>", "<del>struck</del>", "~single~",
    '<div class="md-footnote" id="fn-1">', "<p>Para after footnote def.</p>", '<div class="md-footnote" id="fn-2">', '<blockquote class="md-callout md-callout-note"><p class="md-callout-title">Title</p>',
    '<blockquote class="md-callout md-callout-note"><p class="md-callout-title">Note</p>', '<details class="md-callout md-callout-tip"><summary class="md-callout-title">Folded tip</summary>',
    '<span class="fv-wikilink fv-dead"', '<span class="md-math-inline">x^2</span>', '<div class="md-math-display">\\sum_i i</div>', "<h2>Heading Two</h2>", "<p>Last para.</p>"];
  let at = -1;
  for (const s of order) { const i = out.indexOf(s, at + 1); assert.ok(i > at, "in order: " + s); at = i; }
  assert.equal((out.match(/md-frontmatter"/g) || []).length, 1);
  assert.equal((out.match(/class="md-footnote"/g) || []).length, 2);
  assert.equal((out.match(/class="md-callout /g) || []).length, 3);
  for (const snippet of ["==m== and ~~s~~", "a [[Note|alias]] b", "ref[^1] here", "$x^2$ math", "> [!note] T\n> body", "[^1]: def"]) {
    assert.equal(userMdHtml(snippet), html(snippet), snippet);
  }
  assert.equal(userMdHtml("line one\nline two"), "<p>line one<br>line two</p>\n", "…and keeps its one difference, hard breaks");
});

// ── the 2026-09-09 review of Slice 4: the grammar's edges ──────────────────────────────────────────
test("front matter is a YAML mapping between the rules: a reply or a note that opens with a horizontal rule and has another later keeps its blocks; a `---` inside a fence never closes it; YAML with an interior blank line, comments, a sequence under a key and a quoted key folds; a blank line right after the opener is an hr", () => {
  // the review's corpus: a report bounded by rules, a fence that opens with ---, a list between rules, a note with a decorative rule
  assert.equal(html("---\n\n## Summary\n\nTwo files changed, tests pass.\n\n---\n\nFooter note."), "<hr>\n<h2>Summary</h2>\n<p>Two files changed, tests pass.</p>\n<hr>\n<p>Footer note.</p>\n", "a report bounded by rules: hr, heading, paragraph, hr, paragraph, as the base rendered it");
  assert.equal(html("---\n\n```yaml\n---\nname: ci\n```\n\nAfter the fence."), '<hr>\n<pre><code class="language-yaml">---\nname: ci\n</code></pre>\n<p>After the fence.</p>\n', "a --- inside a fence is the fence's, and the fence closes where it did");
  assert.equal(html("---\n\n- one\n- two\n\n---\n\nTail."), "<hr>\n<ul>\n<li>one</li>\n<li>two</li>\n</ul>\n<hr>\n<p>Tail.</p>\n");
  assert.equal(html("---\n\n# Title\n\nFirst paragraph of a note that starts with a rule.\n\n---\n\nSecond part."), "<hr>\n<h1>Title</h1>\n<p>First paragraph of a note that starts with a rule.</p>\n<hr>\n<p>Second part.</p>\n");
  const reply = "---\n## Summary\n\nI changed three files and the tests pass.\n---\n\nDetails follow...";
  assert.doesNotMatch(html(reply), /md-frontmatter/, "prose between two rules is not a mapping: no fold, whatever marked makes of the rules");
  assert.match(html(reply), /^<hr>\n<h2>Summary<\/h2>/);
  assert.equal(userMdHtml(reply), html(reply), "the user's bubble agrees");
  assert.doesNotMatch(html("---\nmy note\n---\nhello"), /md-frontmatter/);
  assert.equal(Lexer.lex("---\n\n## Summary\n\n---\n")[0].type, "hr", "the anchor map's lexer sees the hr too");
  // what still folds: YAML as Obsidian, Jekyll and Hugo write it
  assert.match(html("---\ntitle: Test Note\n\ntags: [a, b]\n---\n\nPara.\n"), /^<details class="md-frontmatter"><summary class="md-frontmatter-head">Front matter<\/summary><pre>title: Test Note\n\ntags: \[a, b\]<\/pre><\/details><p>Para\.<\/p>\n$/, "a blank line inside the mapping is YAML's to have");
  assert.match(html("---\n# generated\ntitle: x\naliases:\n  - y\ntags:\n- a\n- b\n\"quoted key\": 1\nkey with spaces: v\nurl: https://example.test/a:b\n---\n"), /^<details class="md-frontmatter">/, "comments, nested lines, a sequence under a key, a quoted key, a key with spaces, a value with a colon");
  assert.match(html("---\n---\nx"), /^<details class="md-frontmatter">/, "an empty block still folds");
  // pandoc's rule: an opener followed by a blank line is a horizontal rule
  assert.equal(html("---\n\ntitle: x\n---\n"), "<hr>\n<h2>title: x</h2>\n", "a blank line right after the opener: a rule, as pandoc reads it");
  // a sequence, a fence, prose or a link as the first content line is not a mapping
  for (const body of ["- one\n- two", "```\ncode\n```", "Just a sentence.", "[link](x)"]) assert.doesNotMatch(html("---\n" + body + "\n---\n"), /md-frontmatter/, body);
});

test("footnotes: a reference with no definition stays as written; a definition's text may refer to a later note; a duplicate definition keeps its class and drops the id; a definition nothing refers to has a label and no back link; a lazy or two-space continuation line stays in the note, and another definition, a list or a heading ends it", () => {
  assert.equal(html("This was measured earlier[^1] and confirmed."), "<p>This was measured earlier[^1] and confirmed.</p>\n", "no definition: a literal citation, as GitHub leaves it, never a numbered link to nowhere");
  assert.equal(userMdHtml("This was measured earlier[^1] and confirmed."), "<p>This was measured earlier[^1] and confirmed.</p>\n");
  assert.deepEqual((Lexer.lex("a [^1] b")[0] as { tokens: Array<{ type: string }> }).tokens.map((t) => t.type), ["text"], "no token for the anchor map either");
  const cross = html("See [^b] then.\n\n[^b]: has [^a] inside\n\n[^a]: the other\n");
  assert.match(cross, /<p>See <sup class="md-fnref"><a href="#fn-b" id="fnref-b">1<\/a><\/sup> then\.<\/p>/);
  assert.match(cross, /<div class="md-footnote" id="fn-b"><p><a class="md-fnback" href="#fnref-b" title="Back to the text">1<\/a> has <sup class="md-fnref"><a href="#fn-a" id="fnref-a">2<\/a><\/sup> inside<\/p><\/div>/, "a reference inside a definition's text finds a definition written later: every definition is known before any inline text is lexed");
  assert.match(cross, /<div class="md-footnote" id="fn-a"><p><a class="md-fnback" href="#fnref-a" title="Back to the text">2<\/a> the other<\/p><\/div>/);
  const dup = html("Ref[^d].\n\n[^d]: First.\n\n[^d]: Second.\n");
  assert.equal((dup.match(/id="fn-d"/g) || []).length, 1, "one element carries the id, so #fn-d lands on the first definition");
  assert.match(dup, /<div class="md-footnote" id="fn-d"><p><a class="md-fnback" href="#fnref-d" title="Back to the text">1<\/a> First\.<\/p><\/div><div class="md-footnote"><p><a class="md-fnback" href="#fnref-d" title="Back to the text">1<\/a> Second\.<\/p><\/div>/, "the second keeps its class and its back link");
  assert.equal(html("[^x]: unreferenced\n"), `<div class="md-footnote" id="fn-x"><p><span class="md-fnback" title="${FOOTNOTE_ORPHAN_TITLE}">[^x]:</span> unreferenced</p></div>`, "nothing refers to it: the marker as written is the label, which says so, with no link to a reference that is not there");
  // round 2: an orphan definition's text is dressed, never changed. A regex character class an agent explains at a line start
  // is GFM's definition shape (GitHub drops the whole block); the marker stays in view, so the reply reads as written.
  const regex = "The pattern:\n\n[^a-z]: matches anything but a lowercase letter\n[^0-9]+: one or more non-digits";
  assert.match(html(regex), /<div class="md-footnote" id="fn-a-z"><p><span class="md-fnback" title="[^"]+">\[\^a-z\]:<\/span> matches anything but a lowercase letter\n\[\^0-9\]\+: one or more non-digits<\/p><\/div>$/);
  assert.equal(html(regex).replace(/<[^>]+>/g, ""), "The pattern:\n[^a-z]: matches anything but a lowercase letter\n[^0-9]+: one or more non-digits", "every character the author wrote is in the rendered text");
  assert.doesNotMatch(FOOTNOTE_ORPHAN_TITLE, /—|fleet/i);
  const lazy = "Ref[^1].\n\n[^1]: first\nlazy second line\n\nAfter.\n";
  assert.match(html(lazy), /<div class="md-footnote" id="fn-1"><p><a class="md-fnback" href="#fnref-1" title="Back to the text">1<\/a> first\nlazy second line<\/p><\/div><p>After\.<\/p>\n$/, "a lazy continuation line stays in the note, as GitHub keeps it");
  assert.equal(Lexer.lex(lazy).map((t) => t.raw).join(""), lazy, "the tokens tile the source");
  assert.match(html("Ref[^1].\n\n[^1]: first\n  two-space line\n"), /1<\/a> first\ntwo-space line<\/p><\/div>$/, "Obsidian's two-space continuation, de-indented");
  assert.match(html("Ref[^1].\n\n[^1]: first\n    four-space line\n"), /1<\/a> first\nfour-space line<\/p><\/div>$/, "GitHub's four-space continuation, as before");
  assert.match(html("Ref[^1] and [^2].\n\n[^1]: a\n[^2]: b\n"), /1<\/a> a<\/p><\/div><div class="md-footnote" id="fn-2"><p><a class="md-fnback" href="#fnref-2" title="Back to the text">2<\/a> b<\/p><\/div>$/, "another definition on the next line ends the first");
  assert.match(html("Ref[^1].\n\n[^1]: a\n- item\n"), /1<\/a> a<\/p><\/div><ul>\n<li>item<\/li>\n<\/ul>\n$/, "a list ends it");
  assert.match(html("Ref[^1].\n\n[^1]: a\n# Head\n"), /1<\/a> a<\/p><\/div><h1>Head<\/h1>\n$/, "a heading ends it");
});

test("a callout keeps a lazy continuation line, as the blockquote it displaces does and as GitHub keeps it; its start hint never fires inside a paragraph", () => {
  const lazy = "> [!WARNING]\n> Useful information that users should know,\neven when skimming content.\n";
  assert.equal(html(lazy), '<blockquote class="md-callout md-callout-warning"><p class="md-callout-title">Warning</p><p>Useful information that users should know,\neven when skimming content.</p>\n</blockquote>');
  assert.deepEqual(Lexer.lex(lazy).map((t) => [t.type, t.raw]), [["callout", lazy]], "one token whose raw tiles the source");
  assert.equal(html("> [!CAUTION]\n> careful\nnext line lazy\n"), '<blockquote class="md-callout md-callout-caution"><p class="md-callout-title">Caution</p><p>careful\nnext line lazy</p>\n</blockquote>');
  assert.equal(html("> [!NOTE]\n> body\n\nAfter.\n"), '<blockquote class="md-callout md-callout-note"><p class="md-callout-title">Note</p><p>body</p>\n</blockquote><p>After.</p>\n', "a blank line ends it, as before");
  assert.equal(html("a> [!note] b"), "<p>a&gt; [!note] b</p>\n", "a marker one character into a paragraph is text (the start hint used to fire at src.slice(1) through its ^ alternative)");
  assert.equal(html("> a> [!note] b"), "<blockquote>\n<p>a&gt; [!note] b</p>\n</blockquote>\n");
  assert.equal(html("text\n> [!note] b\n> body"), '<p>text</p>\n<blockquote class="md-callout md-callout-note"><p class="md-callout-title">b</p><p>body</p>\n</blockquote>', "a callout still interrupts a paragraph at a line start");
});

test("==mark== never opens inside a word or beside another =, so touching comparisons in prose and headings stay literal; a highlight after a space, punctuation or a line start renders", () => {
  assert.equal(html("It returns true when a==b and false when c==d."), "<p>It returns true when a==b and false when c==d.</p>\n");
  assert.equal(html("Use a===b for identity and c===d for the other case."), "<p>Use a===b for identity and c===d for the other case.</p>\n");
  assert.equal(html("## Compare a==b vs c==d"), "<h2>Compare a==b vs c==d</h2>\n");
  assert.equal(html("Set flag==true, then ==read== it."), "<p>Set flag==true, then <mark class=\"md-mark\">read</mark> it.</p>\n");
  assert.equal(html("This is ==important== text."), "<p>This is <mark class=\"md-mark\">important</mark> text.</p>\n");
  assert.equal(html("(==x==) and ==y==\n\n==z== at the start"), "<p>(<mark class=\"md-mark\">x</mark>) and <mark class=\"md-mark\">y</mark></p>\n<p><mark class=\"md-mark\">z</mark> at the start</p>\n");
  assert.equal(html("**bold ==in== bold**"), "<p><strong>bold <mark class=\"md-mark\">in</mark> bold</strong></p>\n");
  assert.equal(userMdHtml("a==b and c==d"), "<p>a==b and c==d</p>\n");
});

test("a wikilink target with a dotted title gets `.md` unless it names a file type Obsidian opens; the dead span's hover text names no surface", () => {
  const live = fileHtml("[[Note.v2]] [[Release v1.0]] [[2026.09.09]] [[Node.js]] [[Note.v2#Sec]] [[Archive.2024|old]] ![[Note.v2]] [[paper.pdf]] [[clip.mp4]] [[board.canvas]] [[song.mp3]] [[img.PNG]]");
  assert.equal(live, '<p><a href="Note.v2.md">Note.v2</a> <a href="Release%20v1.0.md">Release v1.0</a> <a href="2026.09.09.md">2026.09.09</a> <a href="Node.js.md">Node.js</a> <a href="Note.v2.md#Sec">Note.v2#Sec</a> <a href="Archive.2024.md">old</a> <a class="fv-embed" href="Note.v2.md">Note.v2</a> <a href="paper.pdf">paper.pdf</a> <a href="clip.mp4">clip.mp4</a> <a href="board.canvas">board.canvas</a> <a href="song.mp3">song.mp3</a> <a href="img.PNG">img.PNG</a></p>\n',
    "a dotted note title is a note (Obsidian resolves the title to <title>.md); a target that names a type Obsidian opens keeps its extension");
  assert.doesNotMatch(WIKILINK_DEAD_TITLE, /viewer/, "the span stands in a chat reply and in a URL document, where there is no viewer to speak of");
});

// ── the 2026-09-09 review of Slice 4, round 2: the grammar's edges, continued ─────────────────────
const escText = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");   // marked's escape of a text token
test("==mark== refuses an opener after a closing bracket, a quote or an underscore, and a closer that touches a word, so a comparison whose operand ends in ) ] ' \" or _ stays literal; a highlight still renders at a line start, after a space or an opening bracket, before punctuation, and in CJK prose", () => {
  for (const s of [
    "when len(a)==0 or len(b)==0 the loop exits",
    "if x[i]==y[j] and a[0]==b[0] then merge",
    "'a'==b and 'c'==d",
    "\"a\"==b and \"c\"==d",
    "f()==1 and g()==2",
    "count(*)==0 and sum(x)==0",
    "a_==b and c_==d",
    "if arr.indexOf(x)==-1 or s.indexOf(y)==-1 then skip",
  ]) {
    assert.equal(html(s), "<p>" + escText(s) + "</p>\n", s);
    assert.equal(userMdHtml(s), html(s), "the user's bubble agrees: " + s);
  }
  assert.equal(html("## Check len(a)==0 or len(b)==0"), "<h2>Check len(a)==0 or len(b)==0</h2>\n");
  assert.equal(html("(==x==) and [==y==] ==z==."), "<p>(<mark class=\"md-mark\">x</mark>) and [<mark class=\"md-mark\">y</mark>] <mark class=\"md-mark\">z</mark>.</p>\n", "an opening bracket before the opener, punctuation after the closer");
  assert.equal(html("これは==重要==です"), "<p>これは<mark class=\"md-mark\">重要</mark>です</p>\n", "CJK prose puts no space around a highlight: neither guard is a letter rule");
  assert.equal(html("==high==lighted"), "<p>==high==lighted</p>\n", "a closer touching a word is a comparison's, not a highlight's");
  assert.equal(html("a ==b==c== d"), "<p>a ==b==c== d</p>\n", "the first `==` after the opener is the closer, and this one touches a word: literal, never a highlight run on to the next `==` (round 3, below)");
});

test("a CommonMark link whose text is bracketed, `[[docs]](url)`, is marked's link in every kind, not a wikilink followed by a stray URL; a wikilink followed by anything marked's link rule refuses stays a wikilink", () => {
  const src = "See [[docs]](https://example.test/docs) and [[1]](https://example.test/ref1).";
  const want = '<p>See <a href="https://example.test/docs">[docs]</a> and <a href="https://example.test/ref1">[1]</a>.</p>\n';
  assert.equal(html(src), want, "the chat");
  assert.equal(userMdHtml(src), want, "the user's bubble");
  assert.equal(fileHtml(src), want, "a file document: no path link to a docs.md that does not exist");
  assert.equal(html("![[img.png]](https://example.test/i.png)"), '<p><img src="https://example.test/i.png" alt="[img.png]"></p>\n', "CommonMark's image with bracketed alt text, as GitHub reads it");
  assert.equal(fileHtml("[[Note]](see also) and [[A]][[B]] and [[C]] (x)"), '<p><a href="Note.md">Note</a>(see also) and <a href="A.md">A</a><a href="B.md">B</a> and <a href="C.md">C</a> (x)</p>\n',
    "a parenthetical marked's link rule refuses (a space in the destination), adjacent wikilinks and a space before a parenthesis keep the wikilinks");
  assert.deepEqual((Lexer.lex(src)[0] as { tokens: Array<{ type: string }> }).tokens.map((t) => t.type).filter((t) => t !== "text"), ["link", "link"], "the anchor map's lexer sees links, not wikilinks");
});

test("a callout's body drops a tab after the marker as marked's blockquote does, so `>\\tbody` is a paragraph, not indented code; a lazy setext underline after a callout stays paragraph text, as marked's blockquote keeps it", () => {
  const tab = "> [!note]\n>\tindented by a tab\n\nAfter.\n";
  assert.equal(html(tab), '<blockquote class="md-callout md-callout-note"><p class="md-callout-title">Note</p><p>indented by a tab</p>\n</blockquote><p>After.</p>\n');
  assert.equal(userMdHtml(tab), html(tab));
  const tok = Lexer.lex(tab)[0] as { raw: string; text: string };
  tok.text.split("\n").forEach((line, i) => assert.ok(tok.raw.split("\n")[i].endsWith(line), "line " + i + " of the text is a suffix of the raw line, the shape the anchor map reads: " + JSON.stringify(line)));
  for (const [underline, tag] of [["===", "h1"], ["--", "h2"]]) {
    const out = html(`> [!note]\n> text\n${underline}\n\nAfter.\n`);
    assert.equal(out, `<blockquote class="md-callout md-callout-note"><p class="md-callout-title">Note</p><p>text\n    ${underline}</p>\n</blockquote><p>After.</p>\n`, underline + ": marked's blockquote prefixes the lazy line with four spaces so it is not a setext underline");
    assert.doesNotMatch(out, new RegExp("<" + tag + ">"));
  }
  assert.match(html("> [!note]\n> text\n> ===\n"), /<h1>text<\/h1>/, "a prefixed underline is the quote's own setext heading, in both");
  assert.deepEqual(Lexer.lex("> [!note]\n> text\n===\n\nAfter.").map((t) => t.type), ["callout", "paragraph"], "one token to the blank line");
});

test("a footnote definition ends where the lexer's own paragraph would: a display formula on the next line is a block after the note, as a fence, a callout, a table or a heading already was; a line the math tokenizer rejects stays in the note", () => {
  for (const [name, math] of [["$$", "$$\nx\n$$"], ["\\[", "\\[\nx\n\\]"], ["one-line", "$$x$$"]]) {
    const src = `ref[^1]\n\n[^1]: text\n${math}\n\nAfter.\n`;
    const toks = Lexer.lex(src).map((t) => [t.type, t.raw]);
    assert.deepEqual(toks, [["paragraph", "ref[^1]"], ["space", "\n\n"], ["footnoteDef", "[^1]: text\n"], ["mathBlock", math + "\n\n"], ["paragraph", "After.\n"]], name);
    assert.equal(toks.map((t) => t[1]).join(""), src, name + ": the tokens tile the source");
    assert.match(html(src), /1<\/a> text<\/p><\/div><div class="md-math-display">x<\/div><p>After\.<\/p>\n$/, name + ": the formula is a display block after the note, not a span inside it");
  }
  const rejected = "ref[^1]\n\n[^1]: text\n$$x$$ is inline here.\n\nAfter.\n";
  assert.deepEqual(Lexer.lex(rejected).map((t) => t.type), ["paragraph", "space", "footnoteDef", "paragraph"], "a line the block tokenizer refuses is a continuation line, as in a paragraph");
  assert.match(html(rejected), /text\n<span class="md-math-display">x<\/span> is inline here\.<\/p><\/div>/);
  assert.equal(Lexer.lex(rejected).map((t) => t.raw).join(""), rejected);
});

// ── the 2026-09-09 review of Slice 4, round 3: the grammar's edges, continued ─────────────────────
const MARK = `<mark class="${MARK_CLASS}">`;
test("the ==mark== element carries the class the sheets key on, so the viewer's rule names the ==mark== alone and the comment and change marks (mark.fc-hl, .fc-presel, .fc-ins, .fc-del) keep their own dress", () => {
  assert.equal(MARK_CLASS, "md-mark");
  assert.equal(html("a ==b== c"), `<p>a ${MARK}b</mark> c</p>\n`);
  assert.equal(userMdHtml("a ==b== c"), html("a ==b== c"));
  assert.equal((Lexer.lex("a ==b== c")[0] as { tokens: Array<{ type: string }> }).tokens[1].type, "mark", "the token is unchanged: the anchor map maps it by its delimiters as before");
});

test("front matter: a bare key may begin with a letter or digit of any script, as YAML allows and as Obsidian writes property names in the vault's language; what is not a mapping still lexes as blocks", () => {
  for (const body of ["Über: x", "日本語: x", "title: x\nÜber: y", "étiquettes: [a, b]", "Заголовок: x", "título: x", "١: one"]) {
    const src = "---\n" + body + "\n---\n\nProse\n";
    assert.equal(html(src), `<details class="md-frontmatter"><summary class="md-frontmatter-head">Front matter</summary><pre>${body}</pre></details><p>Prose</p>\n`, body + ": folded (round 1's key check took an ASCII letter, digit or underscore alone, so this rendered as an hr and a setext heading of the keys, the slice's original defect)");
    assert.deepEqual(Lexer.lex(src).map((t) => t.type), ["frontMatter", "paragraph"], body + ": the anchor map's lexer folds it too");
    assert.ok(isYamlMapping(body), body);
    assert.equal(userMdHtml(src), html(src), body + ": the user's bubble agrees");
  }
  // the negatives round 1 pinned hold: a line that opens with a YAML indicator, markup or punctuation is no key
  for (const body of ["* item: x", "> quote: x", "+ item: x", "<div>: x", "$$: x", ": x", "@k: x", "%k: x", "- one\n- two", "Just a sentence.", "[link](x)"]) {
    assert.doesNotMatch(html("---\n" + body + "\n---\n"), /md-frontmatter/, body);
    assert.equal(isYamlMapping(body), false, body);
  }
  assert.equal(html("---\n\nÜber: x\n---\n"), "<hr>\n<h2>Über: x</h2>\n", "pandoc's rule stands: a blank line right after the opener makes it a rule");
});

test("==mark== holds no `==`: the first `==` after the opener is the closer, and a closer that touches a word makes the text literal instead of running the highlight on to a later `==`", () => {
  const cases: Array<[string, string, string]> = [
    ["==high==lighted and ==more== end", `<p>==high==lighted and ${MARK}more</mark> end</p>\n`, "a refused closer never extends to the next highlight (round 2 rendered one mark from `high` to `more`, eating the second opener)"],
    ["x ==a==b ==c== d", `<p>x ==a==b ${MARK}c</mark> d</p>\n`, "the same with an operator between"],
    ["if x ==0 or y ==1 then ==done==", `<p>if x ==0 or y ==1 then ${MARK}done</mark></p>\n`, "two comparisons and a highlight: the operators stay operators"],
    ["Set a ==b and c ==d then ==read== it.", `<p>Set a ==b and c ==d then ${MARK}read</mark> it.</p>\n`, "the shape the rule's guards exist for: two comparisons never pair into one highlight"],
    ["a ==b==c== d", "<p>a ==b==c== d</p>\n", "round 2's pin, re-aimed: the closer touches a word, so the text is literal"],
    ["==a == b==", "<p>==a == b==</p>\n", "a spaced equality inside a highlight is not a highlight: a highlight holds no `==`, the operator reading winning as everywhere in this rule"],
    ["==a ==b==", `<p>==a ${MARK}b</mark></p>\n`, "an opener-shaped `==` inside is a `==` too: the first candidate is literal, the second a highlight"],
    ["==a=b== and ==x=y=z==", `<p>${MARK}a=b</mark> and ${MARK}x=y=z</mark></p>\n`, "a single `=` inside is text"],
    ["==b **c**== d", `<p>${MARK}b <strong>c</strong></mark> d</p>\n`, "inline content inside"],
    ["==重要==です and ==x==) then", `<p>${MARK}重要</mark>です and ${MARK}x</mark>) then</p>\n`, "CJK after the closer and punctuation after it are not words"],
    ["==high==lighted", "<p>==high==lighted</p>\n", "round 2's recorded consequence holds"],
  ];
  for (const [src, want, why] of cases) {
    assert.equal(html(src), want, why + ": " + src);
    assert.equal(userMdHtml(src), want, "the user's bubble agrees: " + src);
  }
  const toks = (Lexer.lex("==high==lighted and ==more== end")[0] as { tokens: Array<{ type: string; raw: string }> }).tokens;
  assert.deepEqual(toks.map((t) => [t.type, t.raw]), [["text", "==high==lighted and "], ["mark", "==more=="], ["text", " end"]], "the anchor map's lexer sees one mark, its raw the delimiters and the text between, and the raws tile the paragraph");
});

test("==mark== skips a code span whole: a `==` inside one is neither the closer nor a forbidden run, so a highlight holding a comparison in code renders as Obsidian renders it; an unmatched or escaped backtick masks nothing, and only a code span is skipped", () => {
  const cases: Array<[string, string, string]> = [
    ["==see `a==b` here==", `<p>${MARK}see <code>a==b</code> here</mark></p>\n`, "the comparison in code, the highlight around it (round 3 rendered the whole line literal, the delimiters showing)"],
    ["==note: `x==y` compares==", `<p>${MARK}note: <code>x==y</code> compares</mark></p>\n`, "the shape an agent writes"],
    ["==see ``a==b`` here==", `<p>${MARK}see <code>a==b</code> here</mark></p>\n`, "a double-backtick span too"],
    ["==x `y== z` w==", `<p>${MARK}x <code>y== z</code> w</mark></p>\n`, "a `==` a space follows inside the span is no closer (rounds 2 and 3 closed the highlight at `y` and broke the span)"],
    ["==a `b== c`", "<p>==a <code>b== c</code></p>\n", "no closer outside the span: literal, the span intact"],
    ["==`a==b`==", `<p>${MARK}<code>a==b</code></mark></p>\n`, "the span is the whole content"],
    ["==`x==y`== and ==`z`==", `<p>${MARK}<code>x==y</code></mark> and ${MARK}<code>z</code></mark></p>\n`, "two of them"],
    ["==a==`b`", `<p>${MARK}a</mark><code>b</code></p>\n`, "a span right after the closer is not a word: the closer stands"],
    ["==see `a==b here==", "<p>==see `a==b here==</p>\n", "an unmatched backtick is text and masks nothing: the `==` touches a word, literal"],
    ["``a`==b==", `<p>\`\`a\`${MARK}b</mark></p>\n`, "a run its length never closes is text too, as marked reads it"],
    ["==see \\`a==b\\` here==", "<p>==see `a==b` here==</p>\n", "an escaped backtick opens no span (marked's escape reads it first): the `==` touches a word, literal"],
    ["==a \\`b\\` c==", `<p>${MARK}a \`b\` c</mark></p>\n`, "escaped backticks inside a highlight are its text"],
    ["==**a==b**==", "<p>==<strong>a==b</strong>==</p>\n", "only a code span is skipped: a `==` inside strong is a `==` in prose, literal (recorded in the header and the plan)"],
    ["see `a ==b` and ==x==", `<p>see <code>a ==b</code> and ${MARK}x</mark></p>\n`, "an opener-shaped `==` inside a span before the highlight is the span's"],
  ];
  for (const [src, want, why] of cases) {
    assert.equal(html(src), want, why + ": " + src);
    assert.equal(userMdHtml(src), want, "the user's bubble agrees: " + src);
  }
  assert.equal(html("==a\n`b==c`\nd=="), `<p>${MARK}a\n<code>b==c</code>\nd</mark></p>\n`, "across the lines of one paragraph");
  const toks = (Lexer.lex("==see `a==b` here==")[0] as { tokens: Array<{ type: string; raw: string; tokens?: Array<{ type: string; raw: string }> }> }).tokens;
  assert.deepEqual(toks.map((t) => [t.type, t.raw]), [["mark", "==see `a==b` here=="]], "the anchor map's lexer sees one mark whose raw is the source text: the delimiters place it as before");
  assert.deepEqual(toks[0].tokens!.map((t) => [t.type, t.raw]), [["text", "see "], ["codespan", "`a==b`"], ["text", " here"]], "the span is a code span inside it, its raw tiling the content");
});

test("the mark rule's view of the source stops at the first `==` outside a code span and masks the spans before it in place, so a candidate's work is the distance to its closer whatever follows; no `==` at all is no view", () => {
  const lexer = new Lexer();
  const tail = " and ==more== `x==y` " + "z".repeat(100000) + " ==end==";
  assert.equal(markView(lexer, "==a `x==y` b==c" + tail), "==a [aaaa] b==c", "cut after the first `==` outside a span and the character after it; the span before it masked to marked's filler, same length");
  assert.equal(markView(lexer, "==a ``x==y`` b==" + tail), "==a [aaaaaa] b== ", "a double-backtick span too; the character after the closer is the lookahead's");
  assert.equal(markView(lexer, "==a `x==y b==c and ==more== " + "z".repeat(100000)), "==a `x==y", "an unmatched backtick is text: the `==` after it is the first outside a span (the tail has no backtick: with one, the lone run would pair with it, as CommonMark reads it)");
  assert.equal(markView(lexer, "==a `x==y b==c" + tail), "==a [" + "a".repeat(tail.indexOf("`") + 9) + "]" + tail.slice(tail.indexOf("`") + 1, tail.indexOf("`") + 5), "the same lone backtick with a single-backtick span in the tail: the run closes at that span's opener, the whole stretch one code span, and the first `==` outside it is the tail's next");
  assert.equal(markView(lexer, "==a \\`x==y\\` b==" + tail), "==a \\`x==y", "an escaped backtick opens no span");
  assert.equal(markView(lexer, "==a `b` c ==d" + tail), "==a [a] c ==d", "a span with no `==` inside is masked all the same");
  assert.equal(markView(lexer, "==no closer here `x` " + "z".repeat(100000)), null, "no `==` follows: nothing to match, no view");
  assert.equal(markView(lexer, "==plain=="), "==plain==", "no backtick: the source itself, to the closer");
  assert.equal(markView(lexer, "==a==`b`"), "==a==`", "the cut keeps the character after the closer, a backtick here, which the closer's guard reads as not a word");
});

test("a lazy underline right under a callout's marker line is the body's first line: a paragraph's text, never indented code or a heading; the setext guard holds from the body's second line on", () => {
  const head = '<blockquote class="md-callout md-callout-note"><p class="md-callout-title">';
  for (const u of ["===", "--", "="]) {
    const src = `> [!note] Title\n${u}\n\nAfter.\n`;
    assert.equal(html(src), `${head}Title</p><p>${u}</p>\n</blockquote><p>After.</p>\n`, u + ": round 2 guarded it with four spaces as marked's blockquote does, but the blockquote keeps its first line, so there the guarded line is a paragraph's continuation; the callout takes the marker line as the title and the guard alone made the body indented code");
    assert.equal(userMdHtml(src), html(src), u + ": the user's bubble agrees");
    assert.equal(html(`> [!note]\n${u}\n`), `${head}Note</p><p>${u}</p>\n</blockquote>`, u + " with no title");
  }
  assert.doesNotMatch(html("> [!note]\n-\n"), /<pre>|<h\d>/, "a lone `-` is a body of `-`, which marked lexes as it lexes that line at any body's start (an empty list item), never code");
  assert.equal(html("> [!tip]- Folded\n===\n"), '<details class="md-callout md-callout-tip"><summary class="md-callout-title">Folded</summary><p>===</p>\n</details>', "a folded callout");
  assert.match(html("- > [!note]\n  ===\n"), /<li><blockquote class="md-callout md-callout-note"><p class="md-callout-title">Note<\/p><p>===<\/p>/, "inside a list item");
  assert.match(html("> > [!note]\n> ===\n"), /<blockquote>\n<blockquote class="md-callout md-callout-note"><p class="md-callout-title">Note<\/p><p>===<\/p>/, "inside a quote");
  assert.equal(html("> [!note]\n===\n--\n"), `${head}Note</p><p>===\n    --</p>\n</blockquote>`, "the body's second lazy line takes the guard: without it the first would be its setext heading");
  assert.equal(html("> [!note] T\n> body\n===\n"), `${head}T</p><p>body\n    ===</p>\n</blockquote>`, "round 2's shape is unchanged: a body line before the underline");
  assert.match(html("> [!note]\n> text\n> ===\n"), /<h1>text<\/h1>/, "a prefixed underline is the quote's own setext heading, as before");
  // the anchor map's suffix view: line i of the text is a suffix of raw line i (no four spaces the source does not hold)
  const tok = Lexer.lex("> [!note] Title\n===\n\nAfter.\n")[0] as { type: string; raw: string; text: string };
  assert.equal(tok.type, "callout");
  assert.equal(tok.text.split("\n")[1], "===");
  tok.text.split("\n").forEach((line, i) => assert.ok(tok.raw.split("\n")[i].endsWith(line), "line " + i + " of the text is a suffix of the raw line: " + JSON.stringify(line)));
});

test("a callout's marker line takes marked's own marker spelling: `>`, an optional space or tab, then up to three spaces of indentation, as GitHub reads an alert; a tab or a fourth space past that is indented code inside the quote", () => {
  const want = '<blockquote class="md-callout md-callout-note"><p class="md-callout-title">T</p><p>body</p>\n</blockquote>';
  for (const src of [">\t[!note] T\n>\tbody\n", ">  [!note] T\n> body\n", ">   [!note] T\n> body\n", ">    [!note] T\n> body\n", ">[!note] T\n> body\n", "> [!note] T\n> body\n"]) {
    assert.equal(html(src), want, JSON.stringify(src) + " (round 2 let the body's marker take a tab, the recognition a space alone, so a note typed with tabs rendered a plain quote reading `[!note] T`)");
    assert.equal(userMdHtml(src), html(src), "the user's bubble agrees: " + JSON.stringify(src));
    const tok = Lexer.lex(src)[0] as { type: string; raw: string; text: string };
    assert.equal(tok.type, "callout", JSON.stringify(src));
    tok.text.split("\n").forEach((line, i) => assert.ok(tok.raw.split("\n")[i].endsWith(line), JSON.stringify(src) + ": line " + i + " of the text is a suffix of the raw line, the shape the anchor map reads"));
  }
  assert.equal(html(">\t[!NOTE]\n>\tThe body.\n"), '<blockquote class="md-callout md-callout-note"><p class="md-callout-title">Note</p><p>The body.</p>\n</blockquote>', "GitHub's alert, typed with tabs");
  assert.equal(html("text\n>\t[!note] b\n> body"), '<p>text</p>\n<blockquote class="md-callout md-callout-note"><p class="md-callout-title">b</p><p>body</p>\n</blockquote>', "interrupts a paragraph as the space-marked one does");
  for (const src of [">\t\t[!note] T\n", "> \t[!note] T\n", ">     [!note] T\n"]) assert.doesNotMatch(html(src), /md-callout/, JSON.stringify(src) + ": four columns of indentation after the marker is indented code, as marked reads it");
});

test("a callout has no start hint: its line is a blockquote, a built-in paragraph interrupt, so a hint could change nothing but marked's clip flag, which joined a paragraph and its interrupt-rejected successor into one <p> whenever a `> [!` stood anywhere later", () => {
  assert.equal((callout as { start?: unknown }).start, undefined, "no hint: marked sets lastParagraphClipped for a hit anywhere in the remaining source and then joins the next paragraph onto the last with a newline the source does not hold");
  const tail = '<blockquote class="md-callout md-callout-note"><p class="md-callout-title">later</p></blockquote>';
  const a = "Intro line\nColumn A\n|---|---|\n\nAfter.\n\n> [!note] later";
  assert.equal(html(a), "<p>Intro line</p>\n<p>Column A\n|---|---|</p>\n<p>After.</p>\n" + tail, "a table header line over a delimiter row of another width: the table interrupt cuts the paragraph, the table tokenizer declines, and the two paragraphs are two, as on the base");
  assert.equal(userMdHtml(a), "<p>Intro line</p>\n<p>Column A<br>|---|---|</p>\n<p>After.</p>\n" + tail, "the user's bubble too");
  assert.equal(html("Para\n| a | b |\n|---|\n\nAfter\n\n> [!note] T"), '<p>Para</p>\n<p>| a | b |\n|---|</p>\n<p>After</p>\n<blockquote class="md-callout md-callout-note"><p class="md-callout-title">T</p></blockquote>');
  const far = "Intro line\nColumn A\n|---|---|\n\nAfter.\n\nMore.\n\nStill more.\n\n> [!tip] far";
  assert.equal(html(far), '<p>Intro line</p>\n<p>Column A\n|---|---|</p>\n<p>After.</p>\n<p>More.</p>\n<p>Still more.</p>\n<blockquote class="md-callout md-callout-tip"><p class="md-callout-title">far</p></blockquote>', "a callout several paragraphs later");
  for (const src of [a, far]) {
    const toks = Lexer.lex(src);
    assert.equal(toks.map((t) => t.raw).join(""), src, "the raws tile the source (a joined paragraph carried a doubled newline, and the anchor map lost every block after it)");
    assert.deepEqual(toks.filter((t) => t.type !== "space").map((t) => t.type).slice(0, 2), ["paragraph", "paragraph"]);
  }
  assert.equal(html("text\n> [!note] b\n> body"), '<p>text</p>\n<blockquote class="md-callout md-callout-note"><p class="md-callout-title">b</p><p>body</p>\n</blockquote>', "the callout still interrupts a paragraph at a line start, through the paragraph rule's own blockquote interrupt");
  // every four-line note of the shapes: the raws tile the source
  const lines = ["Intro line", "Column A", "|---|---|", "| a | b |", "|---|", "", "> [!note] T", "> body", "> quote", "- item", "# H", "After."];
  let n = 0;
  for (const a1 of lines) for (const b of lines) for (const c of lines) for (const d of lines) {
    const src = [a1, b, c, d].join("\n") + "\n";
    const toks = Lexer.lex(src);
    assert.equal(toks.map((t) => t.raw).join(""), src, "the raws tile " + JSON.stringify(src));
    n++;
  }
  assert.equal(n, lines.length ** 4);
});

test("a wikilink names a file or a section: `[[ ]]`, `[[#]]`, `![[ ]]`, `[[a/]]` and `[[ | ]]` name neither and stay literal, as `[[]]` does, in a file document and in a reply", () => {
  for (const s of ["[[ ]]", "[[#]]", "![[ ]]", "[[a/]]", "![[a/]]", "[[ | ]]", "[[ #]]", "[[  #  ]]", "[[/]]", "[[a/#Sec]]", "[[]]"]) {
    assert.equal(fileHtml("x " + s + " y"), "<p>x " + s + " y</p>\n", s + " in a file document (it rendered <a href=\"\">, which the link pass dressed as an external link that opened the page itself, or a path link to a `.md` with no name)");
    assert.equal(html("x " + s + " y"), "<p>x " + s + " y</p>\n", s + " in a reply");
    assert.deepEqual((Lexer.lex("x " + s + " y")[0] as { tokens: Array<{ type: string }> }).tokens.map((t) => t.type), ["text"], s + ": no token for the anchor map either");
  }
  assert.equal(fileHtml("[[#Heading]] [[Note#]] [[a/b]] [[ Note ]] ![[a/img.png]]"), '<p><a href="#Heading">#Heading</a> <a href="Note.md">Note#</a> <a href="a/b.md">a/b</a> <a href="Note.md"> Note </a> <img src="a/img.png" alt="a/img.png"></p>\n',
    "a section link, a target with an empty fragment, a path, a padded title and a path embed still resolve");
});

// ── the 2026-09-09 review of Slice 4, round 5 ─────────────────────────────────────────────────────
test("==mark== reads a backslash-escaped `=` as its text, as marked's escape rule reads it everywhere else in the paragraph: `==a \\== b==` highlights `a == b`, an even run of backslashes escapes itself so the closer after it stands, and an escaped `=` alone closes nothing", () => {
  const cases: Array<[string, string, string]> = [
    ["==a \\== b== end", `<p>${MARK}a == b</mark> end</p>\n`, "the escaped operator inside the highlight (round 4 took the `==` of `\\==` as the closer, highlighted `a \\` and left ` b== end` literal)"],
    ["==\\=a==", `<p>${MARK}=a</mark></p>\n`, "an escaped `=` right after the opener"],
    ["==a \\=b== end", `<p>${MARK}a =b</mark> end</p>\n`, "an escaped `=` a word follows, as before"],
    ["==a \\===", `<p>${MARK}a =</mark></p>\n`, "the content ends in an escaped `=` and the closer follows it (round 4 cut the view at the escaped pair, and the closer's lookahead failed on the third `=`)"],
    ["==a \\=== b==", `<p>${MARK}a =</mark> b==</p>\n`, "the first `==` after the escaped pair is the closer; the operator reading wins after it, as everywhere in the rule"],
    ["==x \\\\== y", `<p>${MARK}x \\</mark> y</p>\n`, "two backslashes escape each other: the closer stands and the content is one backslash, as before"],
    ["==a \\\\\\== b== end", `<p>${MARK}a \\== b</mark> end</p>\n`, "three: an escaped backslash, then an escaped `=` (round 4 highlighted `a \\\\` and left the rest literal)"],
    ["==a\\== end", "<p>==a== end</p>\n", "an escaped `=` leaves one `=`, which closes nothing: literal, the escape shown as its `=`, as `*a\\*` is literal to marked (round 4 highlighted `a\\`)"],
    ["==a \\b==", `<p>${MARK}a \\b</mark></p>\n`, "a backslash before a letter is text, as CommonMark reads it; neither character is a delimiter"],
    ["a \\== b and ==c==", `<p>a == b and ${MARK}c</mark></p>\n`, "outside a highlight the escape reads as before"],
    ["\\==a== b", "<p>==a== b</p>\n", "an escaped opener opens nothing, as before"],
    ["==see \\== in `a==b`==", `<p>${MARK}see == in <code>a==b</code></mark></p>\n`, "an escaped `==` before a code span whose `==` is masked: the closer is the one after the span"],
  ];
  for (const [src, want, why] of cases) {
    assert.equal(html(src), want, why + ": " + src);
    assert.equal(userMdHtml(src), want, "the user's bubble agrees: " + src);
  }
  const toks = (Lexer.lex("==a \\== b== end")[0] as { tokens: Array<{ type: string; raw: string; tokens?: Array<{ type: string; raw: string }> }> }).tokens;
  assert.deepEqual(toks.map((t) => [t.type, t.raw]), [["mark", "==a \\== b=="], ["text", " end"]], "the anchor map's lexer sees one mark whose raw is the source text, the delimiters placing it as before");
  assert.deepEqual(toks[0].tokens!.map((t) => [t.type, t.raw]), [["text", "a "], ["escape", "\\="], ["text", "= b"]], "the escape is marked's own token inside it, the raws tiling the content");
  const lexer = new Lexer();
  const tail = " and ==more== `x==y` " + "z".repeat(100000) + " ==end==";
  assert.equal(markView(lexer, "==a \\== b==" + tail), "==a \\== b== ", "the view runs past an escaped `==` to the first unescaped one outside a code span");
  assert.equal(markView(lexer, "==x \\\\== y" + tail), "==x \\\\== ", "an even run of backslashes escapes no `=`: the cut is at that `==`");
  assert.equal(markView(lexer, "==a \\===" + tail), "==a \\=== ", "the `==` after an escaped `=` is the cut, the tail's first character its lookahead");
  assert.equal(markView(lexer, "==a\\==" + tail), "==a\\== and ==m", "no unescaped closer of its own: the view runs on to the tail's first `==`");
  assert.equal(markView(lexer, "==no closer \\== here " + "z".repeat(100000)), null, "an escaped `==` alone is no closer: no view");
  assert.equal(html("~~a \\~~ b~~ end"), "<p><del>a \\</del> b~~ end</p>\n", "the double-tilde rule keeps the blind spot marked's own gfm del has (`~~a \\~~ b~~` closes at the escaped pair): no change of this slice's, recorded in the header");
});

// ── the 2026-09-09 review of Slice 4, round 6 ─────────────────────────────────────────────────────
test("==mark==: the escape atom is a backslash and one ASCII punctuation character, marked's escape (CommonMark 2.4), so a backslash before whitespace is text and a closer after `\\ ` is preceded by whitespace and refused, while `==a \\== b==` and `==a\\\\== b` render as round 5 renders them", () => {
  const cases: Array<[string, string, string]> = [
    ["==a \\ == z", "<p>==a \\ == z</p>\n", "a backslash and a space before the closer: the space is the content's last character, so the closer is refused as in `==a ==` (round 5's atom of a backslash and any character paired `\\ ` and highlighted `a \\ `)"],
    ["==a\\ ==", "<p>==a\\ ==</p>\n", "the same with nothing after the closer"],
    ["==a \\\t== z", "<p>==a \\\t== z</p>\n", "a backslash and a tab"],
    ["==a \\\n== z", "<p>==a <br>== z</p>\n", "a backslash at the end of a line is marked's hard break, kept, and the `==` on the next line closes nothing (round 5 highlighted `a \\` with the newline and lost the break)"],
    ["==\\ ==", "<p>==\\ ==</p>\n", "a backslash and a space alone"],
    ["==see \\ == in `a==b`==", "<p>==see \\ == in <code>a==b</code>==</p>\n", "the view still cuts at the first unescaped `==` outside a code span, and the rule refuses that closer: literal, marked rendering the code span"],
    ["==a \\== b== end", `<p>${MARK}a == b</mark> end</p>\n`, "an escaped `=` is the highlight's text, as round 5 renders it"],
    ["==a\\\\== b", `<p>${MARK}a\\</mark> b</p>\n`, "an escaped backslash, then the closer: two backslashes are one escape pair and the highlight closes at that `==`"],
    ["==a \\b==", `<p>${MARK}a \\b</mark></p>\n`, "a backslash before a letter is one character of text and the letter another; neither is a delimiter, as round 5 renders it"],
    ["==C:\\Users\\me==", `<p>${MARK}C:\\Users\\me</mark></p>\n`, "backslashes before letters inside a path"],
    ["*a \\ * z", "<p>*a \\ * z</p>\n", "marked's own em refuses the same shape"],
    ["~~a \\ ~~ z", "<p>~~a \\ ~~ z</p>\n", "and the double-tilde rule too"],
  ];
  for (const [src, want, why] of cases) {
    assert.equal(html(src), want, why + ": " + JSON.stringify(src));
    assert.equal(userMdHtml(src), want, "the user's bubble agrees: " + JSON.stringify(src));
  }
  const lexer = new Lexer();
  const tail = " and ==more== `x==y` " + "z".repeat(100000) + " ==end==";
  assert.equal(markView(lexer, "==a \\ == z" + tail), "==a \\ == ", "the view is unchanged: it cuts at the first unescaped `==` outside a code span, whitespace before it or not; the rule, not the view, refuses this closer");
  assert.deepEqual((Lexer.lex("==a \\ == z")[0] as { tokens: Array<{ type: string; raw: string }> }).tokens.map((t) => [t.type, t.raw]), [["text", "==a \\ == z"]], "one text token for the anchor map: no mark");
});

test("a callout's body drops a quote marker indented up to three spaces, CommonMark's marker: a lazy line indented four or more that begins with `>` keeps its `>` as text, as commonmark.js and GitHub render it; marked's blockquote strips it under any indentation, a deviation of marked's the callout does not copy", () => {
  const head = '<blockquote class="md-callout md-callout-note"><p class="md-callout-title">T</p>';
  const four = "> [!note] T\n> body\n    > more\n\nAfter.\n";
  const tab = "> [!note] T\n> body\n\t> more\n\nAfter.\n";
  const three = "> [!note] T\n> body\n   > more\n\nAfter.\n";
  assert.equal(html(four), `${head}<p>body\n    &gt; more</p>\n</blockquote><p>After.</p>\n`, "four spaces: a lazy continuation line, its `>` paragraph text (a browser collapses the spaces to one)");
  assert.equal(html(tab), `${head}<p>body\n    &gt; more</p>\n</blockquote><p>After.</p>\n`, "a tab: the lexer expands it to four spaces first");
  assert.equal(html(three), `${head}<p>body\nmore</p>\n</blockquote><p>After.</p>\n`, "three spaces: a marker, stripped as marked strips it");
  assert.equal(html("> body\n    > more\n\nAfter.\n"), "<blockquote>\n<p>body\nmore</p>\n</blockquote>\n<p>After.</p>\n", "marked's own blockquote strips the four-space `>` (its ` *>`): the recorded divergence is marked's from CommonMark, not the callout's from GitHub");
  for (const src of [four, tab, three]) {
    assert.equal(userMdHtml(src), html(src).replace("<p>body\n", "<p>body<br>"), "the user's bubble agrees, its soft newline a <br> (breaks: true): " + JSON.stringify(src));
    const tok = Lexer.lex(src)[0] as { type: string; raw: string; text: string };
    assert.equal(tok.type, "callout", JSON.stringify(src));
    assert.equal(tok.raw, "> [!note] T\n> body\n" + src.split("\n")[2].replace("\t", "    ") + "\n\n", "one token to the blank line, the trailing newlines marked's blockquote rule takes included, a leading tab expanded by the lexer");
    tok.text.split("\n").forEach((line, i) => assert.ok(tok.raw.split("\n")[i].endsWith(line), JSON.stringify(src) + ": line " + i + " of the text is a suffix of the raw line, the shape the anchor map reads, whichever way the `>` goes"));
  }
});

test("source: who applies the one configuration, and what it holds", () => {
  const config = UI("md-config.ts");
  assert.match(config, /export const mdExtensions: MarkedExtension\[\] = \[\n\s*delDoubleTilde,\n\s*\{ extensions: \[mathBlock, mathInline, frontMatter, footnoteDef, footnoteRef, callout, mark, wikilink\] \},\n\];/);
  assert.equal(mdExtensions.length, 2);
  assert.match(config, /registerMdPostPass\(renderMathPlaceholders\);/, "the fill travels with the grammar");
  for (const f of ["render.ts", "file-view.ts", "anchor-map.ts"]) assert.match(UI(f), /^applyMdConfig\(\);/m, f + " applies it at load");
  assert.match(UI("chat-md.ts"), /new Marked\(\{ gfm: true, breaks: true \}, \.\.\.mdExtensions\)/, "the user-text instance is built from the same list");
  assert.match(UI("file-view-links.ts"), /export function viewerWalkTokens\(token: \{ type: string; href\?: string \| null \}\): void \{\n\s*if \(token\.type === "link" && typeof token\.href === "string"\) token\.href = viewerLinkTarget\(token\.href\);\n\s*resolveWikilink\(token\);/,
    "the file kind's walkTokens stamps a wikilink resolved, beside the link-target rewrite");
  assert.doesNotMatch(config, /from "\.\/render"|from "\.\/file-view"|from "\.\/chat-md"/, "the configuration imports no bundle-specific module");
  assert.doesNotMatch(config, /innerHTML|document\./, "pure: it builds strings for marked and touches no DOM");
});

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
import { applyMdConfig, mdExtensions, resolveWikilink, calloutTitle, WIKILINK_DEAD_TITLE, FRONT_MATTER_LABEL, FOOTNOTE_ORPHAN_TITLE } from "./md-config";
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

test("footnotes: a reference is a numbered sup link, a definition renders IN PLACE as one div with a back link, numbered by order of first reference; a URL-only definition is a footnote, not a swallowed link definition", () => {
  const out = html("Ref[^b] and [^a] then [^b] again.\n\n[^a]: Def A\n    continued\n\n[^b]: https://example.test/def-only\n\nAfter.\n");
  assert.match(out, /<p>Ref<sup class="md-fnref"><a href="#fn-b" id="fnref-b">1<\/a><\/sup> and <sup class="md-fnref"><a href="#fn-a" id="fnref-a">2<\/a><\/sup> then <sup class="md-fnref"><a href="#fn-b" id="fnref-b-2">1<\/a><\/sup> again\.<\/p>/, "numbered by first reference; a second reference to the same note keeps its own id");
  assert.match(out, /<div class="md-footnote" id="fn-a"><a class="md-fnback" href="#fnref-a" title="Back to the text">2<\/a> Def A\ncontinued<\/div>/, "the definition in place, its continuation line de-indented");
  assert.match(out, /<div class="md-footnote" id="fn-b"><a class="md-fnback" href="#fnref-b" title="Back to the text">1<\/a> <a href="https:\/\/example\.test\/def-only">https:\/\/example\.test\/def-only<\/a><\/div>/, "the URL-only definition renders (marked's def rule used to swallow it)");
  assert.ok(out.indexOf("fn-a") < out.indexOf("<p>After."), "in place, before the paragraph that follows it");
  oneRoot(html("[^1]: only a definition\n"), "div");
  assert.match(html("[^x]: unreferenced\n"), /<span class="md-fnback" title="[^"]+">x<\/span> unreferenced/, "a definition nothing refers to shows its id, and has no back link to a reference that is not there (below)");
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

test("==mark== renders <mark> with inline content; the opener must touch its content, so a comparison in prose stays literal", () => {
  assert.equal(html("a ==b **c**== d"), "<p>a <mark>b <strong>c</strong></mark> d</p>\n");
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
  const order = ['<details class="md-frontmatter">', "<h1>Heading One</h1>", '<sup class="md-fnref">', "<mark>marked text</mark>", "<del>struck</del>", "~single~",
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
  assert.match(cross, /<div class="md-footnote" id="fn-b"><a class="md-fnback" href="#fnref-b" title="Back to the text">1<\/a> has <sup class="md-fnref"><a href="#fn-a" id="fnref-a">2<\/a><\/sup> inside<\/div>/, "a reference inside a definition's text finds a definition written later: every definition is known before any inline text is lexed");
  assert.match(cross, /<div class="md-footnote" id="fn-a"><a class="md-fnback" href="#fnref-a" title="Back to the text">2<\/a> the other<\/div>/);
  const dup = html("Ref[^d].\n\n[^d]: First.\n\n[^d]: Second.\n");
  assert.equal((dup.match(/id="fn-d"/g) || []).length, 1, "one element carries the id, so #fn-d lands on the first definition");
  assert.match(dup, /<div class="md-footnote" id="fn-d"><a class="md-fnback" href="#fnref-d" title="Back to the text">1<\/a> First\.<\/div><div class="md-footnote"><a class="md-fnback" href="#fnref-d" title="Back to the text">1<\/a> Second\.<\/div>/, "the second keeps its class and its back link");
  assert.equal(html("[^x]: unreferenced\n"), `<div class="md-footnote" id="fn-x"><span class="md-fnback" title="${FOOTNOTE_ORPHAN_TITLE}">x</span> unreferenced</div>`, "nothing refers to it: the label says so, with no link to a reference that is not there");
  assert.doesNotMatch(FOOTNOTE_ORPHAN_TITLE, /—|fleet/i);
  const lazy = "Ref[^1].\n\n[^1]: first\nlazy second line\n\nAfter.\n";
  assert.match(html(lazy), /<div class="md-footnote" id="fn-1"><a class="md-fnback" href="#fnref-1" title="Back to the text">1<\/a> first\nlazy second line<\/div><p>After\.<\/p>\n$/, "a lazy continuation line stays in the note, as GitHub keeps it");
  assert.equal(Lexer.lex(lazy).map((t) => t.raw).join(""), lazy, "the tokens tile the source");
  assert.match(html("Ref[^1].\n\n[^1]: first\n  two-space line\n"), /1<\/a> first\ntwo-space line<\/div>$/, "Obsidian's two-space continuation, de-indented");
  assert.match(html("Ref[^1].\n\n[^1]: first\n    four-space line\n"), /1<\/a> first\nfour-space line<\/div>$/, "GitHub's four-space continuation, as before");
  assert.match(html("Ref[^1] and [^2].\n\n[^1]: a\n[^2]: b\n"), /1<\/a> a<\/div><div class="md-footnote" id="fn-2"><a class="md-fnback" href="#fnref-2" title="Back to the text">2<\/a> b<\/div>$/, "another definition on the next line ends the first");
  assert.match(html("Ref[^1].\n\n[^1]: a\n- item\n"), /1<\/a> a<\/div><ul>\n<li>item<\/li>\n<\/ul>\n$/, "a list ends it");
  assert.match(html("Ref[^1].\n\n[^1]: a\n# Head\n"), /1<\/a> a<\/div><h1>Head<\/h1>\n$/, "a heading ends it");
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
  assert.equal(html("Set flag==true, then ==read== it."), "<p>Set flag==true, then <mark>read</mark> it.</p>\n");
  assert.equal(html("This is ==important== text."), "<p>This is <mark>important</mark> text.</p>\n");
  assert.equal(html("(==x==) and ==y==\n\n==z== at the start"), "<p>(<mark>x</mark>) and <mark>y</mark></p>\n<p><mark>z</mark> at the start</p>\n");
  assert.equal(html("**bold ==in== bold**"), "<p><strong>bold <mark>in</mark> bold</strong></p>\n");
  assert.equal(userMdHtml("a==b and c==d"), "<p>a==b and c==d</p>\n");
});

test("a wikilink target with a dotted title gets `.md` unless it names a file type Obsidian opens; the dead span's hover text names no surface", () => {
  const live = fileHtml("[[Note.v2]] [[Release v1.0]] [[2026.09.09]] [[Node.js]] [[Note.v2#Sec]] [[Archive.2024|old]] ![[Note.v2]] [[paper.pdf]] [[clip.mp4]] [[board.canvas]] [[song.mp3]] [[img.PNG]]");
  assert.equal(live, '<p><a href="Note.v2.md">Note.v2</a> <a href="Release%20v1.0.md">Release v1.0</a> <a href="2026.09.09.md">2026.09.09</a> <a href="Node.js.md">Node.js</a> <a href="Note.v2.md#Sec">Note.v2#Sec</a> <a href="Archive.2024.md">old</a> <a class="fv-embed" href="Note.v2.md">Note.v2</a> <a href="paper.pdf">paper.pdf</a> <a href="clip.mp4">clip.mp4</a> <a href="board.canvas">board.canvas</a> <a href="song.mp3">song.mp3</a> <a href="img.PNG">img.PNG</a></p>\n',
    "a dotted note title is a note (Obsidian resolves the title to <title>.md); a target that names a type Obsidian opens keeps its extension");
  assert.doesNotMatch(WIKILINK_DEAD_TITLE, /viewer/, "the span stands in a chat reply and in a URL document, where there is no viewer to speak of");
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

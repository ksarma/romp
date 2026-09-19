// Decision 52's account of the slice's first review round, held to the code (2026-09-18; plans/file-review.md, decision 52
// and the Tests bullet "The inline tag and the cells"). The first round changed three things in md-literal-tags.ts and
// recorded none of them in the decision: the matcher became a stack per element name where the first build kept one list
// of every open start tag, the `image` start tag (the alias the HTML parser rewrites to `img`) is left HTML outside the
// fourteen-element void list, and the self-closing flag is read as the HTML tokenizer reads a tag, so `<a href=http://a.test/>`
// is an open start tag. The round also added three test modules and named one of them in the plan. The second round found
// the record describing the replaced matcher, predicting text for the alias, calling the map's `open` array "always empty"
// (an unclosed `<image>` lands in it) and naming none of the three modules; this module holds each corrected sentence to the
// source that makes it true (the module's code with its comments stripped, the map's scan and its one call, the installed
// marked run through the rule for the two tags the record names) and holds the Tests bullet's inventory both ways, as the
// sidecar-records pin does for decisions 49 and 50: every module the bullet names is in the tree, and every test module
// under tools/, ui/webview/ or tests/ that cites decision 52 or 53 and this plan is named in the bullet or in one of the two
// records. The review of the slice's PR (round 1, 2026-09-19) corrected the record again and this module follows: the `open`
// array's occupants (an unclosed `<image>` in HTML content, a start tag inside an html comment) and the SELF-CLOSING spelling,
// which the rule leaves HTML and the parser opens (`<b/>`, `<div/>`, `<table/>`, `<title/>`), so the Block.leaves fix shape is
// not moot; the fragment target a converted tag's own id or name loses, left beside the heading slug for the user's call; the
// math breakout class widened from one shape to the class the browser suite records; the loss before the rule told apart for
// `<template>` and `<textarea>`; and the twin `ui/webview/guide-own-html-block-tag.test.ts` named in the bullet and the record.
// Synthetic: the repo's own text only. Run: node --test tools/file-review-plan-inlinetag-records.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const REPO = path.resolve(HERE, '..');
const SELF = 'tools/file-review-plan-inlinetag-records.test.mjs';
const read = (...parts) => fs.readFileSync(path.join(REPO, ...parts), 'utf8');
const flat = (s) => s.replace(/\s+/g, ' ');
/** A TypeScript module with its `//` lines and `/* *\/` blocks removed, so a pin reads the code and not its comments. */
const codeOnly = (ts) => ts.replace(/\/\*[\s\S]*?\*\//g, '').split('\n').filter((l) => !l.trimStart().startsWith('//')).join('\n');

const plan = read('plans', 'file-review.md');
function section(from, to) {
  const a = plan.indexOf(from);
  assert.ok(a >= 0, `heading ${JSON.stringify(from)} not found in the plan`);
  const b = plan.indexOf(to, a + from.length);
  assert.ok(b > a, `heading ${JSON.stringify(to)} not found after ${JSON.stringify(from)}`);
  return flat(plan.slice(a, b));
}
const decisions = section('## Decisions (the user, 2026-09-05 and 2026-09-06)', '## Open questions for the user');
const d52 = decisions.slice(decisions.indexOf('52. **'), decisions.indexOf('53. **'));
const d53 = decisions.slice(decisions.indexOf('53. **'));
const tests = section('## Tests', '## Docs');
const bullet = tests.slice(tests.indexOf('- The inline tag and the cells (2026-09-18, decisions 52 and 53):'));

const modSrc = read('ui', 'webview', 'md-literal-tags.ts');
const mod = codeOnly(modSrc);
const map = codeOnly(read('ui', 'webview', 'anchor-map.ts'));

// The installed marked and esbuild, for the leg that runs the rule itself; the record legs need neither.
const NM = path.join(REPO, 'vscode-extension', 'node_modules');
const MARKED = path.join(NM, 'marked', 'lib', 'marked.esm.js');
const ESBUILD = path.join(NM, 'esbuild', 'package.json');
const SKIP = fs.existsSync(MARKED) && fs.existsSync(ESBUILD)
  ? false
  : 'marked and esbuild are not installed under vscode-extension/node_modules (run `npm ci` in vscode-extension); the rule was not run';

/** The module, compiled to JavaScript and imported: its one import is of marked's types, which the compile removes. */
async function loadRule() {
  const esbuild = createRequire(import.meta.url)(path.join(NM, 'esbuild'));
  const { code } = esbuild.transformSync(modSrc, { loader: 'ts', format: 'esm' });
  assert.ok(!/^\s*import /m.test(code), 'the compiled module imports nothing');
  return import('data:text/javascript;base64,' + Buffer.from(code, 'utf8').toString('base64'));
}

// ── the matcher ─────────────────────────────────────────────────────

test('decision 52 says the matcher is a stack per name, popping the latest open tag of its name, and the code keeps a Map of stacks', () => {
  assert.ok(d52.includes('Matching is by element name, ASCII case-insensitive, innermost first: a stack per name of the open start tags over the block\'s inline tokens flattened in document order'));
  assert.ok(d52.includes('an end tag popping the latest open tag of its name and no other'));
  assert.ok(d52.includes('The stacks date from the review\'s first round (2026-09-18): the first build kept one list of every open start tag and scanned it from its end on each end tag, quadratic'), 'the one list is history, dated');
  assert.ok(d52.includes('the stacks are linear in the run\'s tags and convert the same tokens, held against that list as an oracle over a fixed sample and a seeded random one'));
  const run = mod.slice(mod.indexOf('function literalizeRun('), mod.indexOf('function toText('));
  assert.ok(run.includes('const open = new Map<string, Token[]>();'), 'a stack per name');
  assert.ok(run.includes('if (m[1]) open.get(name)?.pop();'), 'an end tag pops its own name\'s stack and no other');
  assert.ok(run.includes('for (const stack of open.values()) for (const t of stack) toText(t);'), 'the tags left open at the run\'s end are converted');
  assert.ok(!/lastIndexOf|open\.length = /.test(run), 'no list scanned from its end');
  const oracle = read('ui', 'webview', 'md-literal-tags-tag-syntax.test.ts');
  assert.ok(/oneList|one list/.test(oracle) && /seed/i.test(oracle), 'the oracle module holds the stacks against the one list over a seeded sample');
});

// ── the image alias and the self-closing flag ───────────────────────

test('decision 52 lists the `image` start tag among what is left as lexed, records IMG_ALIAS outside the void set with its reason, and the code does the same', () => {
  assert.ok(d52.includes('a void element, the `image` start tag (below), the self-closing syntax `<x/>`'), 'the left-as-lexed list names the alias');
  assert.ok(d52.includes('One start tag outside that list is left HTML too (the review\'s first round, 2026-09-18): `image`, the obsolete alias the HTML parser\'s in-body insertion mode rewrites to `img` as it inserts it'));
  assert.ok(d52.includes('`IMG_ALIAS` in the module, a constant of its own and not a fifteenth void element, because inside an inline `<svg>` an `<image>` is an element with an end tag of its own and the map\'s tag scans, which read `VOID_TAGS`, read it so'));
  assert.ok(d52.includes('(`keygen`, `basefont`, `bgsound`) fall to the rule and render as text'));
  assert.match(mod, /^const IMG_ALIAS = "IMAGE";$/m, 'the alias constant');
  const voidLine = mod.match(/^export const VOID_ELEMENTS: ReadonlySet<string> = new Set\(\[(.*)\]\);$/m);
  assert.ok(voidLine, 'the void list');
  const voids = Array.from(voidLine[1].matchAll(/"([A-Z]+)"/g), (m) => m[1]);
  assert.equal(voids.length, 14, 'fourteen void elements, the alias not among them');
  for (const name of ['IMAGE', 'KEYGEN', 'BASEFONT', 'BGSOUND']) assert.ok(!voids.includes(name), `${name} is not void`);
  assert.ok(mod.includes('else if (!VOID_ELEMENTS.has(name) && name !== IMG_ALIAS && !isSelfClosingTag(t.raw)) {'), 'the rule skips the void set, the alias and a self-closing tag, and nothing else');
  assert.match(map, /^const VOID_TAGS = VOID_ELEMENTS;$/m, 'the map\'s scans read the same fourteen, so an unclosed <image> is a start tag to them');
});

test('decision 52 records the self-closing flag read as the HTML tokenizer reads a tag, and the code reads it so with no suffix test', () => {
  assert.ok(d52.includes('The self-closing flag is read as the HTML tokenizer reads a tag (`isSelfClosingTag`, the same round), attribute by attribute: a quoted value runs to its closing quote, an unquoted value to the next blank or `>`, and the flag is a `/` right before the `>` outside them all.'));
  assert.ok(d52.includes('So `<a href=http://a.test/>` is an open start tag, the `/` the unquoted value\'s own last character, and with no end tag in its block it is text'));
  assert.ok(d52.includes('the first build\'s suffix test on the raw (`/>` at its end) read that tag as self-closing and left it HTML'));
  assert.ok(mod.includes('export function isSelfClosingTag(raw: string): boolean {'), 'the tokenizer-style reader is the module\'s');
  assert.ok(!/\/\\\/>\$\/|endsWith\("\/>"\)/.test(mod), 'no suffix test on the raw');
  const syntax = read('ui', 'webview', 'md-literal-tags-tag-syntax.test.ts');
  assert.ok(syntax.includes('<a href=http://a.test/>'), 'the tag-syntax module carries the record\'s example');
  assert.ok(/FAILS BEFORE/.test(syntax), 'with a case that was red before the fix');
});

test('the installed marked, run through the rule, does what the record says for the two tags it names: <image> stays HTML, <a href=http://a.test/> is text, <keygen> is text', { skip: SKIP }, async () => {
  const { Lexer, Parser } = await import(pathToFileURL(MARKED).href);
  const { literalizeUnclosedTags, VOID_ELEMENTS } = await loadRule();
  assert.ok(!VOID_ELEMENTS.has('IMAGE') && VOID_ELEMENTS.size === 14, 'the loaded module\'s void set');
  const render = (src) => { const tokens = Lexer.lex(src); literalizeUnclosedTags(tokens); return { tokens, html: Parser.parse(tokens) }; };
  const inline = (tokens) => tokens[0].tokens.map((t) => `${t.type}:${t.raw}`);
  const image = render('Pic <image src="a.png"> here.\n');
  assert.deepEqual(inline(image.tokens), ['text:Pic ', 'html:<image src="a.png">', 'text: here.'], 'the alias stays an html token');
  assert.equal(image.html, '<p>Pic <image src="a.png"> here.</p>\n', 'and renders as the tag');
  assert.deepEqual(inline(render('Pic <IMAGE src="a.png"> here.\n').tokens)[1], 'html:<IMAGE src="a.png">', 'upper case too');
  const anchor = render('See <a href=http://a.test/> now.\n');
  assert.deepEqual(inline(anchor.tokens), ['text:See ', 'text:<a href=http://a.test/>', 'text: now.'], 'the unquoted value\'s `/` is not the flag: an open start tag with no end tag, so text');
  assert.equal(anchor.html, '<p>See &lt;a href=http://a.test/&gt; now.</p>\n');
  assert.deepEqual(inline(render('See <a href="http://a.test/"/> now.\n').tokens)[1], 'html:<a href="http://a.test/"/>', 'the flag after a quoted value is read, and the tag stays HTML');
  for (const tag of ['keygen', 'basefont', 'bgsound', 'table']) {
    assert.equal(render(`Pic <${tag}> here.\n`).html, `<p>Pic &lt;${tag}&gt; here.</p>\n`, `<${tag}> falls to the rule`);
  }
});

// ── the map's open array ────────────────────────────────────────────

test('decision 52 no longer calls blockEnds\' open array always empty or the Block.leaves shape moot: its occupants are an unclosed <image> in HTML content and a start tag inside an html comment, the self-closing spelling still opens the wrapper, and the map passes a fresh array and reads it nowhere', () => {
  assert.ok(!d52.includes('is therefore always empty'), 'the overstatement is gone');
  assert.ok(!d52.includes('so that shape is moot'), 'the moot verdict is gone (the PR review\'s round 1)');
  assert.ok(d52.includes('can therefore hold nothing but an unclosed `image` start tag, the one start tag the rule leaves HTML that the scan\'s void set lacks, which opens no element in HTML content (the parser rewrites it to the void `img`; inside an inline `<svg>` the `image` element is closed by `</svg>` and every block still maps), or a start tag written inside an html comment (`<!-- an aside <b> -->`: the scan\'s `TAG_RE` reads the comment\'s raw, the rule\'s scan does not), which the parser reads as part of the comment; neither opens an element around the later blocks.'));
  assert.ok(d52.includes('The SELF-CLOSING spelling of such a tag still does: the rule leaves it HTML (`isSelfClosingTag`) and the scan reads it as a leaf, but the parser ignores the flag on an HTML element and opens it, so `<b/>` in prose is a wrapper around every later block (the tag\'s paragraph maps and every later block is refused with the mismatch sentence), `<div/>` a div holding them, `<table/>` one paragraph holding them, and `<title/>` takes the rest of the note as its text, which the sanitizer drops'));
  assert.ok(d52.includes('the pairing does not model that wrapper, so the fix shape recorded for it, `Block.leaves`, is NOT moot: before this decision the bare `<b>` with no closer made the same wrapper, and the rule removed it for that spelling alone'));
  assert.ok(d52.includes('The map passes the scan a fresh array and reads it nowhere.'));
  const scan = map.slice(map.indexOf('function blockEnds('), map.indexOf('\n}\n', map.indexOf('function blockEnds(')));
  assert.ok(scan.includes('else if (!VOID_TAGS.has(name) && !m[3]) open.push(name);'), 'the scan pushes every non-void start tag without the flag, the alias among them, and reads one with the flag as a leaf');
  assert.ok(map.includes('const TAG_RE = /<(\\/?)([a-zA-Z][a-zA-Z0-9:_-]*)'), 'TAG_RE reads any tag in an html token\'s raw, a comment\'s included');
  const calls = Array.from(map.matchAll(/blockEnds\(([^;]*)\);/g), (m) => m[1]).filter((args) => !args.includes(', open, '));
  assert.deepEqual(calls, ['[t], t.type === "text", [], ends'], 'the one call outside the scan\'s own recursion passes a fresh array, which nothing holds a name for');
  // the comment at that call says the same, and the two suites the record names carry the shapes it describes
  const comment = flat(read('ui', 'webview', 'anchor-map.ts').split('// the `open` array (the start tags the block\'s inline html leaves open) is discarded')[1].split('if (!isHtml) blockEnds(')[0].replace(/^\s*\/\/ ?/gm, ''));
  assert.ok(comment.includes('The SELF-CLOSING spelling of such a tag still does') && comment.includes('Block.leaves, is NOT moot'), 'the walkedBlocks comment mirrors the record');
  const browser = read('ui', 'webview', 'anchor-map-literal-tags-browser.test.ts');
  for (const shape of ['{ tag: "<b/>", shape: "H1 P[B] B[H2,P,P]"', '{ tag: "<div/>", shape: "H1 P DIV[P,H2,P,P]"', '{ tag: "(<table/>__widths.csv)", shape: "H1 P[P,H2,P,P,TABLE]"', '{ tag: "<title/>", shape: "H1 P"', '{ tag: "<x/>", shape: "H1 P H2 P P"']) assert.ok(browser.includes(shape), 'the browser leg records ' + shape);
  const standIn = read('ui', 'webview', 'anchor-map-literal-tags.test.ts');
  for (const shape of ['["Lead <div/> rest of the line t1.", "P DIV[P,H2,P,P]", mismatches]', '["Lead (<table/>__widths.csv) rest of the line t1.", "P[P,H2,P,P,TABLE]", mismatches]', '["Lead <title/> rest of the line t1.", "P", absent]']) assert.ok(standIn.includes(shape), 'the stand-in suite records ' + shape);
  assert.ok(standIn.includes('`<b/>` is recorded in the browser leg alone'), 'and says the stand-in does not model the `<b/>` wrapper');
});

test('the self-closing spelling and the html comment, run through the installed marked and the rule: the token stays html with the flag read, the comment stays one html token whose raw TAG_RE reads a start tag from, the bare spelling is text', { skip: SKIP }, async () => {
  const { Lexer } = await import(pathToFileURL(MARKED).href);
  const { literalizeUnclosedTags, isSelfClosingTag } = await loadRule();
  const inline = (src) => { const tokens = Lexer.lex(src); literalizeUnclosedTags(tokens); return tokens[0].tokens.map((t) => `${t.type}:${t.raw}`); };
  for (const tag of ['<b/>', '<div/>', '<table/>', '<title/>']) {
    assert.deepEqual(inline(`Intro ${tag} tail.\n`), ['text:Intro ', `html:${tag}`, 'text: tail.'], `${tag} stays an html token`);
    assert.equal(isSelfClosingTag(tag), true, `${tag} carries the flag`);
  }
  assert.deepEqual(inline('Intro <b> tail.\n'), ['text:Intro ', 'text:<b>', 'text: tail.'], 'the bare spelling is text');
  assert.deepEqual(inline('Note <!-- an aside <b> --> here.\n'), ['text:Note ', 'html:<!-- an aside <b> -->', 'text: here.'], 'the comment is one html token the rule leaves');
  const tagRe = map.match(/^const TAG_RE = \/(.*)\/g;$/m);
  assert.ok(tagRe, 'TAG_RE is one regex literal with the g flag');
  assert.deepEqual(Array.from('<!-- an aside <b> -->'.matchAll(new RegExp(tagRe[1], 'g')), (m) => [m[1], m[2], m[3]]), [['', 'b', '']], 'the scan\'s regex reads a start tag inside the comment\'s raw, which is how a `<b>` lands in `open` there');
});

// ── the PR review's round 1: the fragment target, the breakout class, the loss before the rule ──

test('decision 52 records the fragment target a converted tag loses as left, beside the heading slug and phrased for the user\'s call, with the untouched shapes; file-view-links.ts dresses a fragment link with no target dead with the title the record quotes', () => {
  assert.ok(d52.includes('holds the shape and the slug). Left too, found in the review of the slice\'s PR (round 1, 2026-09-19): a converted tag\'s own id or name is no longer a fragment target, since the tag is text and no element.'), 'the entry stands right after the heading-slug entry');
  assert.ok(d52.includes('An unclosed `<a name="spot">` or `<span id="sid">` written mid-prose reached the DOM before as an element under the sanitizer\'s `user-content-` prefix, so the note\'s own `[jump](#spot)` landed on it (the link\'s title `Go to spot`); it is characters now, so that link is dead, with the title `No heading or anchor named \u201cspot\u201d in this document` (`linkMarkdownAnchors` in file-view-links.ts finds no target)'));
  assert.ok(d52.includes('Untouched, landing before and after: a closed tag (`<a name="x"></a>`, the README idiom, mid-prose or on its own line) and a tag alone on its line (`<a name="line">`), which is an HTML block the rule does not read.'));
  assert.ok(d52.includes('the user decides whether it is worth one, as for the slug'));
  const links = read('ui', 'webview', 'file-view-links.ts');
  assert.ok(links.includes('export const noSectionTitle = (id: string): string => "No heading or anchor named \\u201c" + id + "\\u201d in this document";'), 'the dead title');
  assert.ok(links.includes('if (hit) { a.dataset.frag = id; a.setAttribute("title", "Go to " + id); }') && links.includes('else { withClass(a, DEAD_LINK_CLASS); a.setAttribute("title", noSectionTitle(id)); }'), 'a fragment link lands on a target or is dressed dead with that title');
  assert.ok(read('ui', 'webview', 'md-sanitize.ts').includes('export const USER_CONTENT_PREFIX = "user-content-";'), 'the prefix an author\'s id or name reaches the DOM under');
});

test('the rule over the installed marked makes the mid-prose id or name tag text, so no element carries the id or the name, and leaves the closed tag and the tag alone on its line html', { skip: SKIP }, async () => {
  const { Lexer, Parser } = await import(pathToFileURL(MARKED).href);
  const { literalizeUnclosedTags } = await loadRule();
  const run = (src) => { const tokens = Lexer.lex(src); literalizeUnclosedTags(tokens); return tokens; };
  const prose = run('See <a name="spot"> here in prose.\n');
  assert.deepEqual(prose[0].tokens.map((t) => `${t.type}:${t.raw}`), ['text:See ', 'text:<a name="spot">', 'text: here in prose.'], 'the unclosed `<a name>` is text');
  assert.equal(Parser.parse(prose), '<p>See &lt;a name=&quot;spot&quot;&gt; here in prose.</p>\n', 'and renders as its characters (the quotes escaped too, as the record says), no element');
  const span = run('Mark <span id="sid"> mid prose.\n');
  assert.deepEqual(span[0].tokens.map((t) => `${t.type}:${t.raw}`)[1], 'text:<span id="sid">', 'the unclosed `<span id>` the same');
  const closed = run('Closed <a name="closed"></a> here.\n');
  assert.deepEqual(closed[0].tokens.filter((t) => t.type === 'html').map((t) => t.raw), ['<a name="closed">', '</a>'], 'the closed tag stays html');
  const line = run('<a name="line">\n\nJump [jump](#line).\n');
  assert.equal(line[0].type, 'html', 'the tag alone on its line is a block html token');
  assert.ok(line[0].raw.startsWith('<a name="line">'), 'left as lexed');
});

test('decision 52 records the math breakout class the rule opened, bounded to an inline math and a closed element on the parser\'s breakout list, RECORDED and not modelled; the browser suite carries the class sentence and the two representatives, the rules suite the reader\'s side of ma5, and the Slice 5 note the record cites says not modelled', () => {
  assert.ok(!d52.includes('one shape moved into the breakout class'), 'the one-shape wording is gone');
  assert.ok(d52.includes('an integration point of an INLINE `<math>` left open (`<mtext>`, `<mi>`, `<mo>`, `<mn>` or `<ms>`, or an `<annotation-xml>` with the html or the xhtml encoding) is literal text now, so a CLOSED HTML element after it whose start tag is on the parser\'s foreign-content breakout list stands in the math\'s foreign content with no integration point around it: the parser breaks out of the math at it and shows its text, and the reader drops the math whole.'));
  assert.ok(d52.includes('In Chromium `ma7 <math><mtext><b>x</b></math> y7` shows `ma7 x y7` where the reader reads `ma7 y7`'));
  assert.ok(d52.includes('`ma5 <math><mtext><p>a<p>b</p></math> y5` shows `ma5 b y5` against `ma5 y5`, no paint mark on either; before this decision both sides read `ma7 y7` and `ma5 y5`.'));
  assert.ok(d52.includes('Not in the class, agreeing on both sides: a closed element whose start tag is not on that list (`<kbd>`, `<a>`), which goes with the dropped math; the same shape inside an inline `<svg>`, which the sanitizer keeps, so both sides read `sv1 <title>x y1`; and a `<math>` inside an html block, whose tags the rule does not read.'));
  assert.ok(d52.includes('records it as not modelled and pre-existing), so the class is RECORDED in that suite with two representatives, `ma5` and `ma7`, and not modelled; `ui/webview/anchor-map-html-rules.test.ts` pins the reader\'s side of `ma5`.'));
  const browser = read('ui', 'webview', 'anchor-map-html-text-browser.test.ts');
  assert.ok(browser.includes('an integration point of an INLINE `<math>` left'), 'the class sentence in the browser suite');
  assert.ok(browser.includes('src: "ma5 <math><mtext><p>a<p>b</p></math> y5\\n", dom: "ma5 b y5", reader: "ma5 y5"'), 'the ma5 representative recorded');
  assert.ok(browser.includes('src: "ma7 <math><mtext><b>x</b></math> y7\\n", dom: "ma7 x y7", reader: "ma7 y7"'), 'the ma7 representative recorded');
  const rules = read('ui', 'webview', 'anchor-map-html-rules.test.ts');
  assert.ok(rules.includes('assert.equal(shown("ma5 <math><mtext><p>a<p>b</p></math> y5\\n"), "ma5 y5", "the reader\'s text alone'), 'the rules suite pins the reader\'s side');
  assert.ok(flat(read('plans', 'markdown-viewer.md')).includes('a start tag that breaks out of foreign content, a `<b>` inside `<math><mrow>` or an annotation-xml with no HTML encoding, is not modelled, pre-existing and identical on main, recorded'), 'the Slice 5 note the record cites');
});

test('decision 52\'s account of the loss before the rule names the six names the sanitizer dropped whole and tells the template and the textarea apart; the sanitizer forbids textarea and not template', () => {
  assert.ok(d52.includes('after an inline `<title>`, `<script>`, `<style>`, `<xmp>`, `<iframe>` or `<plaintext>` start tag in prose, the parser took the rest of the note as the element\'s text and the sanitizer dropped it; after a `<template>` the parser put the rest into the template\'s content, which the browser renders nowhere (the sanitizer keeps the element); after a `<textarea>` the rest showed as unformatted characters, the element dropped and its text kept'));
  assert.ok(!d52.includes('`<style>`, `<textarea>`, `<xmp>`'), 'the textarea is no longer listed among the names dropped whole');
  const forbid = read('ui', 'webview', 'md-sanitize.ts').match(/^export const MD_FORBID_TAGS: readonly string\[\] = \[([\s\S]*?)\];$/m);
  assert.ok(forbid, 'the forbidden tags');
  assert.ok(forbid[1].includes('"textarea"'), 'textarea is forbidden (its text kept, KEEP_CONTENT)');
  assert.ok(!forbid[1].includes('"template"'), 'template is not');
});

test('decision 52\'s Tests paragraph and the Docs sentence follow the guide fixer\'s sentences: the twin, the loss sentence and the python pin named', () => {
  assert.ok(d52.includes('since the review of the slice\'s PR (round 1, 2026-09-19) it holds the guide\'s sentence on the tags that take the rest of the file when they stay HTML too, `<title>`, `<script>`, `<style>` and `<iframe>` first on their line (block `html` tokens) or written with the slash mid-sentence (inline `html` tokens the rule leaves), `<textarea>` beside them.'));
  assert.ok(d52.includes('so `ui/webview/guide-own-html-block-tag.test.ts` (the same round) runs them through both callers\' lexes under the viewer\'s configuration inside the extension job\'s `npm test`'));
  const twin = read('ui', 'webview', 'guide-own-html-block-tag.test.ts');
  assert.ok(twin.includes('const LEXES: Array<[string, Lex]> = [["mdBlock\'s lex", viewerLex], ["placeTokens\' lex", mapLex]];'), 'the twin lexes both ways');
  const tools = read('tools', 'guide-own-html-block-tag.test.mjs');
  assert.ok(tools.includes('const LOSS = \'A `<title>`, `<script>`, `<style>` or `<iframe>` that stays HTML takes everything after it out of the Rendered view'), 'the tools module pins the loss sentence');
  assert.ok(tools.includes('for (const name of [\'title\', \'script\', \'style\', \'iframe\', \'textarea\'])'), 'and lexes the five names');
});

// ── the comments and messages the consolidation pass brought in line with the record (2026-09-18) ──

test('the module header says the lexer state persists past the block as decision 52 does, the map\'s comment at the fresh array names its one occupant, and the html-rules message for the blank-encoding forms names the DOM the browser leg records', () => {
  const header = flat(modSrc.slice(0, modSrc.indexOf('\nimport ')).replace(/^\/\/ ?/gm, ''));
  assert.ok(header.includes('marked\'s inline lexer state is not rewound between blocks: after an unclosed `<kbd>`, `<pre>`, `<code>` or `<script>` tag it lexes the remaining text of that block and of every later block unescaped (its inRawBlock flag) until an end tag of any of those four names or the document\'s end'), 'the header\'s scope is the document\'s rest, as the record\'s');
  assert.ok(header.includes('after an unclosed `<a` tag it autolinks no bare URL in that block or any later one (inLink) until an `</a>`'));
  assert.ok(!header.includes('lexes the block\'s remaining text unescaped'), 'the block-scoped wording is gone');
  assert.ok(d52.includes('of that block and of every later block unescaped (`inRawBlock`)'), 'the record the header follows');
  const mapSrc = read('ui', 'webview', 'anchor-map.ts');
  const at = mapSrc.indexOf('// the `open` array (the start tags the block\'s inline html leaves open) is discarded');
  assert.ok(at >= 0, 'the comment at the fresh array');
  const comment = flat(mapSrc.slice(at, mapSrc.indexOf('if (!isHtml) blockEnds(', at)).replace(/^\s*\/\/ ?/gm, ''));
  assert.ok(comment.includes('so the scan meets none but an unclosed `<image>`, the alias the rule leaves HTML as it leaves `<img>` and VOID_TAGS lacks, which opens no element'), 'the comment names the one occupant, as the record does');
  assert.ok(!comment.includes('so the scan meets none and'), 'the overstatement is gone');
  const rules = read('ui', 'webview', 'anchor-map-html-rules.test.ts');
  const browser = read('ui', 'webview', 'anchor-map-html-text-browser.test.ts');
  assert.ok(browser.includes('src: "ma8 <math><annotation-xml encoding=\\"text/html \\"><b>x</math> y8\\n", quotes: [{ from: "ma8", to: "y8", shown: "ma8 y8" }]'), 'the browser leg records the blank-encoding form as an agreement: the DOM and the reader both `ma8 y8`');
  assert.ok(!rules.includes('the DOM shows `ma8 x y8`, the breakout class, recorded'), 'the html-rules message no longer says the DOM shows the breakout for those forms');
  assert.ok(rules.includes('the DOM shows `ma8 y8` too since decision 52, the annotation-xml and the b literal text inside the dropped math'));
  assert.ok(rules.includes('the DOM showed `ma8 x y8` there before decision 52, the `<b>` breaking out of the math, the recorded class; since it the annotation-xml and the b, with no end tags of their own, are literal text inside the dropped math and the DOM shows `ma8 y8` too'), 'the test\'s title says the same');
});

test('decision 52 records the heading id a converted tag changes as left, with the mechanism, the user\'s call and the module that holds it; file-view.ts says so at both comments that call the id GitHub\'s slug', () => {
  assert.ok(d52.includes('Left too, found in the review\'s consolidation pass (2026-09-18): a heading holding such a tag (`## Results <b>`) takes its id from its rendered text, the tag\'s characters included'));
  assert.ok(d52.includes('`md-results-b`, where GitHub\'s slug of that heading, which reads the tag as HTML, is `results`'));
  assert.ok(d52.includes('A fix would slug the heading\'s inline tokens with the converted ones skipped'));
  assert.ok(d52.includes('the user decides whether it is worth one (`ui/webview/md-literal-tags.test.ts` holds the shape and the slug)'));
  const view = read('ui', 'webview', 'file-view.ts');
  assert.ok(view.includes('One heading diverges from GitHub\'s slug, recorded as left in decision 52'), 'the mdBlock comment');
  assert.ok(view.includes('(`## Results <b>` mints md-results-b, GitHub\'s slug being results): decision 52 of plans/file-review.md records that'), 'the minting\'s comment');
  const pin = read('ui', 'webview', 'md-literal-tags.test.ts');
  assert.ok(pin.includes('viewerHtml("## Results <b>\\n"), "<h2>Results &lt;b&gt;</h2>\\n"') && pin.includes('assert.equal(headingSlug(shown), "results-b");'), 'the test module holds the shape and the slug');
});

test('the anchor-map stand-in suites render through the viewer\'s recipe: each imports viewerHtml from file-view.ts, the export mdBlock parses through, holds no copy of it, and no buildRendered parses with marked.parse alone; the cells suite holds a converted tag against the recipe', () => {
  const view = read('ui', 'webview', 'file-view.ts');
  assert.ok(view.includes('export function viewerHtml(text: string, walk?: (token: Token) => void): string {') && view.includes('\n  const dirty = viewerHtml(text, (t) => {\n'), 'file-view.ts exports the recipe and mdBlock parses through it');
  for (const f of ['anchor-map.test.ts', 'anchor-map-cells.test.ts', 'anchor-map-cells-formulas.test.ts', 'anchor-map-code-lines.test.ts', 'anchor-map-wrappers.test.ts', 'anchor-map-obsidian.test.ts']) {
    const src = read('ui', 'webview', f);
    assert.match(src, /^import \{ viewerHtml \} from "\.\/file-view";/m, `${f} imports the viewer's recipe`);
    assert.ok(!/\nfunction viewerHtml\(/.test(src) && !src.includes('marked.parser('), `${f}: no copy of the recipe`);
    const at = src.indexOf('\nfunction buildRendered(');
    assert.ok(at >= 0, `${f} builds the rendered stand-in`);
    const body = src.slice(at, src.indexOf('\n}\n', at));
    assert.ok(body.includes('viewerHtml(text') && !body.includes('marked.parse('), `${f}: buildRendered parses through the recipe`);
  }
  const am = read('ui', 'webview', 'anchor-map.test.ts');
  assert.ok(am.includes('parseHTML(box.ownerDocument, viewerHtml(B))') && !am.includes('marked.parse(B)'), 'the re-filled box in anchor-map.test.ts too');
  const cells = read('ui', 'webview', 'anchor-map-cells.test.ts');
  assert.ok(cells.includes('| <b>open | z1 |') && cells.includes('[["#text(<b>open)"], ["#text(z1)"]]'), 'the cells suite holds a converted tag in a cell against the recipe');
});

// ── the inventory, both ways ────────────────────────────────────────

/** The test modules a record names in backticks, as repo-relative paths. */
const testFiles = (s) => Array.from(s.matchAll(/`([^`\s]+\.(?:test\.ts|test\.mjs|py))`/g), (m) => m[1])
  .map((n) => (n.includes('/') ? n : path.posix.join('ui', 'webview', n)));
// A record of this plan's decision 52 or 53: the number, and the plan's name somewhere in the file, so a module citing another
// document's fifty-second decision is not swept in.
const CITES = /\bdecisions? (?:52|53)\b/;
const citing = (dir, re) => fs.readdirSync(path.join(REPO, ...dir)).filter((f) => re.test(f))
  .filter((f) => { const t = read(...dir, f); return CITES.test(t) && t.includes('file-review.md'); })
  .map((f) => path.posix.join(...dir, f));
// The three modules the first round added and named nowhere; the scan below reaches each (their headers cite the decision).
const UNRECORDED = ['ui/webview/md-literal-tags-tag-syntax.test.ts', 'tests/test_guide_files_own_html_foreign_tag.py', 'tools/markdown-viewer-plan-decision52-pointers.test.mjs'];
// The twin the PR review's round 1 added (the lexer legs of tools/guide-own-html-block-tag.test.mjs under the viewer's configuration).
const ROUND1 = ['ui/webview/guide-own-html-block-tag.test.ts'];

test('every module the Tests bullet, decision 52 or decision 53 names is in the tree, and every test module citing decision 52 or 53 is named in one of them', () => {
  const inBullet = new Set(testFiles(bullet));
  const named = new Set([...inBullet, ...testFiles(d52), ...testFiles(d53)]);
  assert.ok(inBullet.size >= 12, 'the bullet names the slice\'s modules: ' + inBullet.size);
  for (const f of named) assert.ok(fs.existsSync(path.join(REPO, f)), `${f} is named but not in the tree`);
  const all = [...citing(['tools'], /\.test\.mjs$/), ...citing(['ui', 'webview'], /\.test\.ts$/), ...citing(['tests'], /^test_\w+\.py$/)];
  for (const m of UNRECORDED) assert.ok(all.includes(m), `the scan reaches ${m}`);
  assert.ok(all.includes(SELF), 'and this module');
  assert.ok(all.length >= 15, 'the scan reaches the family: ' + all.length);
  for (const f of all) assert.ok(named.has(f), `${f} cites decision 52 or 53 but neither the Tests bullet nor the two records name it`);
  for (const m of ROUND1) assert.ok(all.includes(m), `the scan reaches ${m}`);
  for (const m of [...UNRECORDED, ...ROUND1, SELF]) {
    assert.ok(inBullet.has(m), `the bullet names ${m}`);
    assert.ok(d52.includes(`\`${m}\``), `decision 52 names ${m}`);
  }
  assert.ok(bullet.includes('so a later round\'s module cannot land unrecorded'), 'the bullet says this pin holds the inventory both ways');
  assert.ok(bullet.includes(`\`${SELF}\` holds decision 52's account of the first round to the code`));
});

test('the sentences added for the first round carry no em dash and no quoted utterance', () => {
  for (const [name, text] of [['decision 52', d52], ['the Tests bullet', bullet]]) {
    assert.ok(!text.includes(String.fromCharCode(0x2014)), `${name} has no em dash`);
    assert.ok(!/"[^"]*\b(I|my|me)\b[^"]*"/.test(text.replace(/"This selection spans more than one cell of a table; select within one cell, or comment on it from the Raw view\."/g, '')), `${name}: no quoted utterance of the user's`);
  }
});

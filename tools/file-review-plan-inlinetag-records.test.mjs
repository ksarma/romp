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
// records. Synthetic: the repo's own text only. Run: node --test tools/file-review-plan-inlinetag-records.test.mjs
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

test('decision 52 no longer calls blockEnds\' open array always empty: an unclosed <image> can land in it, the map passes a fresh array and reads it nowhere', () => {
  assert.ok(!d52.includes('is therefore always empty'), 'the overstatement is gone');
  assert.ok(d52.includes('can therefore hold nothing but an unclosed `image` start tag, the one start tag the rule leaves HTML that the scan\'s void set lacks, and that tag opens no element (the parser rewrites it to the void `img`), so that shape is moot; the map passes the scan a fresh array and reads it nowhere.'));
  const scan = map.slice(map.indexOf('function blockEnds('), map.indexOf('\n}\n', map.indexOf('function blockEnds(')));
  assert.ok(scan.includes('else if (!VOID_TAGS.has(name) && !m[3]) open.push(name);'), 'the scan pushes every non-void start tag without the flag, the alias among them');
  const calls = Array.from(map.matchAll(/blockEnds\(([^;]*)\);/g), (m) => m[1]).filter((args) => !args.includes(', open, '));
  assert.deepEqual(calls, ['[t], t.type === "text", [], ends'], 'the one call outside the scan\'s own recursion passes a fresh array, which nothing holds a name for');
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
  for (const m of [...UNRECORDED, SELF]) {
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

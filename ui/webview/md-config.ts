// ONE markdown configuration for every bundle (plans/markdown-viewer.md, Slice 4: "one markdown configuration,
// Obsidian constructs included"). Before this module the chat (render.ts) and the viewer (file-view.ts) each
// configured the shared `marked` singleton, the chat with a grammar the viewer's bundles never saw (the math
// extensions came in through chat-md.ts, imported by render.ts alone), so a note's `$x^2$` rendered in the chat
// page's viewer and stayed literal in the Files pane and the feed, and the anchor map (anchor-map.ts), which lexes
// the same source with the static `Lexer.lex`, saw whatever grammar its bundle happened to carry. Now render.ts,
// file-view.ts and anchor-map.ts each call applyMdConfig() at load, chat-md.ts builds its two instances
// from the same `mdExtensions` list, and the eight test copies of the viewer's configuration call the function.
//
// Registered on the SINGLETON on purpose, never on a private `Marked` instance: `marked.use` writes the module
// defaults the static `Lexer.lex` reads, so anchor-map.ts's lexer sees every extension here and pairs the same
// tokens the renderer rendered; an instance's extensions never reach the static lexer (measured 2026-09-08). The
// one consequence, recorded in the plan's Slice 4 build note: the Obsidian constructs render in chat replies too.
// A wikilink there is the dead styled span (no directory to resolve against), a reply that opens with YAML folds.
// The one extension NOT in the list is pathAwareEmphasis (below): the chat's two instances (chat-md.ts) take it and
// the singleton does not, on purpose; its comment says why.
//
// Extensions, not string preprocessing: every construct is a marked token whose `raw` tiles the source, so the
// anchor map can place it (anchor-map.ts walkBlocks and walkInline have a case per token type below). Every block
// construct renders as ONE element in place, so the map's 1:1 block-to-element pairing holds, and none of them
// emits author HTML: the markup here is the viewer's own and the sanitizer (md-sanitize.ts) keeps it, classes
// included; an author's `id` gains the `user-content-` prefix there, so the footnote ids below land through
// userContentTarget / fragmentTarget as any author id does.
import { marked, Tokenizer, type MarkedExtension, type Token, type Tokens, type TokenizerAndRendererExtension } from "marked";
import { mathBlock, mathInline, renderMathPlaceholders } from "./math";
import { registerMdPostPass } from "./md-sanitize";
import { isFileUri, looksLikeBareFileName, looksLikeFilePath, PathTokenScanner, trailingPunct } from "./path-links";

// ── helpers ─────────────────────────────────────────────────────────────────────────────────────────
function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
/** marked's own cleaning of a link destination (cleanUrl): percent-encode what needs it, keep an author's escapes. */
function cleanUrl(href: string): string | null {
  try { return encodeURI(href).replace(/%25/g, "%"); } catch { return null; }
}
type LexerThis = { lexer: { tokens: Token[]; state: { top: boolean }; blockTokens(src: string, tokens: Token[]): Token[]; inlineTokens(src: string): Token[]; inline(src: string, tokens?: Token[]): Token[] } };
type ParserThis = { parser: { parse(tokens: Token[]): string; parseInline(tokens: Token[]): string } };
/** marked's own block rules as the lexer's tokenizer holds them (gfm's, under applyMdConfig): the extents two constructs
 *  below borrow, so a callout ends where the blockquote it displaces would and a footnote definition where a paragraph
 *  would. The tokenizer is a private field in marked's types and a plain property at run time. */
function blockRules(lexer: object): { blockquote: RegExp; paragraph: RegExp } {
  return (lexer as { tokenizer: { rules: { block: { blockquote: RegExp; paragraph: RegExp } } } }).tokenizer.rules.block;
}
/** marked's own inline rules, the same way: the link rule the wikilink tokenizer yields to, the code rule the mark
 *  tokenizer masks by. */
function inlineRules(lexer: object): { link: RegExp; code: RegExp } {
  return (lexer as { tokenizer: { rules: { inline: { link: RegExp; code: RegExp } } } }).tokenizer.rules.inline;
}
/** The mark rule's view of `src` (which starts at the opener): a copy cut after the first `==` past the opener that
 *  lies outside a code span and is not escaped, plus the character after it (the closer's lookahead), with every code
 *  span before that point masked to a filler of the same length, `[`, `a`s and `]`, the filler marked's own inlineTokens
 *  masks links and code spans to before it runs em and strong (its blockSkip), a masked copy an extension's tokenizer
 *  is not handed. A `==` whose first `=` an odd count of backslashes precedes is marked's escape of that `=` and a lone
 *  `=` after it (round 5 of the review; the count is the source's, as for a backtick), so the view runs past it to the
 *  next candidate. A match over the copy neither opens nor closes inside a code span or at an escaped `=` and reads the
 *  source's offsets unchanged, the filler being neither `=`, a space, nor a word character at either end. Under the
 *  rule's no-`==` content a match ends at that first `==` or not at all, so nothing past it is read, and null when no
 *  `==` follows at all: the work per candidate stays the distance to its closer, as the bare regex's was (masking the
 *  whole remaining paragraph per candidate instead made a 490,000-character paragraph of 8,000 highlights with code
 *  spans take 64 s against 11 s; and the tokenizer checks the opener before building the view, since marked tries every
 *  inline extension at every token's start, where the view built for each start took a 410,000-character paragraph of
 *  comparisons from 5.5 s to 21 s). marked's code rule is tried at each backtick run before that point in turn, left to right as the lexer meets
 *  them, as a sticky match so no substring is cut per run: a run the rule refuses (unclosed, or a run its length never
 *  closes, `` ``a` ``) is text and masks nothing, and a backtick an odd count of backslashes precedes is marked's escape,
 *  not a run. Exported for md-config.test.ts, which pins the cut. */
const stickyCodeRules = new WeakMap<RegExp, RegExp>();
/** Whether an odd count of backslashes precedes `src[at]`: marked's escape of that character (its escape rule reads
 *  a backslash followed by ASCII punctuation, a backtick, an `=` and a backslash included, so an even run escapes itself). */
function escapedAt(src: string, at: number): boolean {
  let slashes = 0;
  for (let j = at - 1; j >= 0 && src.charCodeAt(j) === 92; j--) slashes++;
  return slashes % 2 === 1;
}
export function markView(lexer: object, src: string): string | null {
  let i = 2, out = "", done = 0;
  let re: RegExp | undefined;
  for (;;) {
    const eq = src.indexOf("==", i);
    if (eq < 0) return null;
    const bt = src.indexOf("`", i);
    if (bt < 0 || eq < bt) {
      if (escapedAt(src, eq)) { i = eq + 1; continue; }   // `\==`: marked's escape of the first `=`, then a lone `=`; neither a closer nor a run
      return out + src.slice(done, eq + 3);
    }
    if (escapedAt(src, bt)) { i = bt + 1; continue; }   // an escaped backtick: marked's escape token, no run
    if (!re) {
      const code = inlineRules(lexer).code;
      re = stickyCodeRules.get(code);
      if (!re) { re = new RegExp(code.source.replace(/^\^/, ""), code.flags.replace(/[gy]/g, "") + "y"); stickyCodeRules.set(code, re); }
    }
    re.lastIndex = bt;
    const m = re.exec(src);
    if (m) {
      out += src.slice(done, bt) + "[" + "a".repeat(m[0].length - 2) + "]";
      done = i = bt + m[0].length;
    } else {
      i = bt;
      while (src.charCodeAt(i) === 96) i++;   // the run is text: skip it whole, as marked's text rule reads it
    }
  }
}
/** `src` cut where marked cuts it before reading a paragraph: at the first line a block extension's start hint names
 *  (marked runs every registered hint on `src.slice(1)` and clips at the index plus one, so an extension's block
 *  interrupts the paragraph although the paragraph rule knows only the built-in interrupts). marked applies the clip
 *  only inside its own paragraph branch, so a tokenizer that borrows the paragraph rule for its extent must apply it
 *  too, or its block runs over the display formula, the one registered block whose start the paragraph rule cannot see
 *  (the 2026-09-09 review, round 2: a `$$` block on the line after a footnote definition was lexed as the note's text). */
function clipAtBlockStarts(lexer: object, src: string): string {
  const hints = (lexer as { options?: { extensions?: { startBlock?: Array<(this: { lexer: object }, s: string) => number | undefined> } } }).options?.extensions?.startBlock;
  if (!hints || hints.length === 0) return src;
  const tail = src.slice(1);
  let at = Infinity;
  for (const hint of hints) {
    const i = hint.call({ lexer }, tail);
    if (typeof i === "number" && i >= 0 && i < at) at = i;
  }
  return at < Infinity ? src.slice(0, at + 1) : src;
}

// ── strikethrough on DOUBLE tildes only ─────────────────────────────────────────────────────────────
// (the user 2026-06-26). marked's built-in GFM `del` tokenizer also fires on a SINGLE tilde, so prose like "near
// the ~21 Wh/day budget … gives ~1.5 to 2 days" rendered as one big <del> struck through from the first ~ to the
// second. GitHub itself only strikes ~~double~~, so match that: a lone ~ (commonly "approximately") stays literal.
// Returning undefined lets marked treat the ~ as text. Moved here from chat-md.ts and file-view.ts, which each
// held a copy.
export const delDoubleTilde = {
  tokenizer: {
    del(src: string) {
      const m = /^~~(?=\S)([\s\S]*?\S)~~/.exec(src);
      if (!m) return undefined;
      return { type: "del", raw: m[0], text: m[1], tokens: (this as { lexer: { inlineTokens(s: string): unknown[] } }).lexer.inlineTokens(m[1]) };
    },
  },
} as MarkedExtension;

// ── emphasis never cuts a file path (the chat's instances, not the singleton) ─────────────────────────
// The chat renders a reply with marked and then links the file paths it finds in the rendered text, one text node at a
// time (path-links.ts linkifyPathTokens, through render.ts linkifyFileUris). A path's own punctuation makes its
// underscores legal emphasis delimiters under CommonMark's flanking rules: a `_` run after `/`, `-`, `.`, `~` or at
// the token's start can open, one before them or at the token's end can close, so `/a-_b/c_/d.md` rendered
// `/a-<em>b/c</em>/d.md` and `__init__.py` rendered strong, the walk read the pieces and never saw the token, and the
// kernel's key for it (kernel.py _path_links, over the raw markdown) matched no text node, so the link never rendered
// (the 2026-09-19 browser census, Entry 5: a temp directory whose random name began with `_`; the population note,
// md-emphasis-population.md, measured 55 rows and 20 adversarial ones). marked agrees with the CommonMark reference on
// every row, so the renderer is not what is wrong: the road hands path-shaped text to the emphasis rule. This override
// makes a linkable token one word to the emphasis rule. "Linkable" is the walk's own scanner, its trailing-punctuation
// trim and its shape gates, imported from path-links.ts and never restated, so a change to the linking grammar changes
// the protection with it. Two rules decide it, named apart because the second is wider than the walk's own linking:
// (1) a token the walk would link where it stands (the file gate, or the URI arm); (2) a bare filename with a known
// extension (`__init__.py`, `_final_.pdf`), which the walk links only inside a code span but which reads as its name
// here, so `__init__.py` in prose stays literal, at the cost of `the _final_.pdf file` losing its emphasis. Both are
// shape rules over the masked paragraph with no view of the rendered DOM: a path in a link's label is protected too,
// though the walk never links under an <a> (the label shows the path as written), and the kernel's map is not consulted.
// The rule, in the spec's own terms. A `_` run lying STRICTLY inside a linkable token neither opens, nor closes, nor
// counts as a nested delimiter: an opener there is refused, and the run is hidden from the built-in's closer scan (a
// letter in its place in the masked string the built-in scans, as marked itself hides a link or a code span), so a
// prose opener pairs with the next closer OUTSIDE the token, as it would were the path one word: `_see /tmp/_build/out.md
// now_` is one emphasis around the literal, linked path. A run at a token's EDGE (`_posts/x.md`, `/tmp/x_`) is the
// prose's while the token holds no run the spec could pair it with: it opens or closes as the spec says, so `_see /tmp/x_`
// and `_x/y.md and more_` keep their emphasis, at the cost that the DOM token (`/tmp/x`) is not the kernel's key
// (`/tmp/x_`), the C42/C43 parity follow-up, identical on the base. Once the token also holds a run beside punctuation
// inside it (`__init__.py`, `_drafts/a_.md`, `/a/_b_`, `_final_.pdf`), the spec pairs the edge run with THAT run, and the
// protection has taken that run away; an edge run left visible then pairs across the hidden middle with a partner
// outside the token instead, cutting the token from its edge and misplacing the writer's emphasis (`_see __init__.py
// now_` lost its emphasis, `see __init__.py and stop__` bolded half the sentence, `_see _drafts/a_.md now_` cut the path
// and lost the link: the 2026-09-20 review, round 2), so such a token is one word WHOLE, its edge runs hidden and refused
// with the rest: `_see __init__.py now_` is one emphasis around the literal name, `see _build/x.py and /out/_run_ now` is
// literal with both paths linked. A run with a word character on both sides (`my_proj`) is no delimiter to marked and
// counts for nothing here either. Refusing the built-in's own first choice of pair instead left the opener as text and
// the emphasis lost, since marked never retries an opener (round 1). `*` is not a path character on the path arms, so
// `*docs/a.md*` keeps its emphasis; intraword underscores never pair (marked's own rule), and escaped delimiters, code
// spans and fences never reach here.
// The shape is delDoubleTilde's, a `tokenizer` override: `false` hands a `*` run to the built-in untouched, `undefined`
// makes marked read the run as text. The built-in decides the pair on a stand-in `this` whose lexer lexes nothing (it
// lexes the pair's body before it returns, and a body lexed twice numbers a footnote reference twice, since footnoteRef
// counts on the lexer), so the body is lexed here, once, when the pair stands. The built-in is reached through
// Tokenizer.prototype (marked's use() gives an override no handle to the tokenizer it replaced), which is right while
// no other extension the chat's instances take overrides emStrong: none in mdExtensions does, and
// md-emphasis-override.test.ts pins it by execution, with the stand-in's contract (see DRY_LEXER).
// Cost. The paragraph is scanned for tokens once per masked string (marked hands every delimiter of a paragraph the
// same string), and the runs and the hidden string are remembered in a short most-recently-used list, so the nested
// lexes marked runs on strings of their own (a link's label, a `*` pair's or a `~~` pair's body, and the standing pair's
// body lexed here) never evict the paragraph's entry (a one-slot memo did: a paragraph of links with an underscore in
// their labels rescanned itself once per link, eight to twelve times the base grammar at 20 KB, round 2). A run inside a
// token is refused before the built-in scans, so a delimiter costs a lookup and a binary search, and the built-in's own
// scan for a closer runs for the prose's delimiters as it does on the base grammar. Measured as a ratio to the base
// grammar on the same string in the same process, and as a count of scans: md-emphasis-atomic.test.ts.
// Registered on the chat's two instances (chat-md.ts chatMarked and userMarked) and NOT on the singleton, on purpose:
// the viewer's aim is GitHub's rendering of a note, which makes `foo/__pycache__/bar.pyc` strong, and the anchor
// map's static lexer pairs the viewer's tokens; whether the viewer should follow is a separate decision (its own
// walk, file-view-links.ts, has the same gap over a note's prose). md-emphasis-paths.test.ts runs both tables.
// Boundaries, measured in the 2026-09-20 review and recorded. The first four render differently from the base grammar,
// by this rule; in the fifth the run in question pairs as it does on the base grammar; the rest render as the base
// renders them:
//   - the accepted loss, A08: `_foo_-bar/baz.md`, emphasis glued to a path with no space between, renders literal,
//     since the closer lies inside the token the walk then links whole. The same when the glue is a strikethrough,
//     `__note/a.md__~~x.py~~`: `~` IS a path character, so the scanner's token runs on into the struck text and the
//     strong is lost (the walk links nothing there on either grammar); a space between restores the base's rendering;
//   - its face at a plain token's end edge: a closer run there longer than the pair spends (`_see /tmp/x__`, one `_` of
//     the two) leaves the spent `_` inside the token, so the pair is refused and the text is literal, the token
//     (`/tmp/x__`, the kernel's key) linked whole, where the base emphasised `see /tmp/x` and left a stray `_`;
//   - the URI arm's class (path-links.ts CLICKABLE_PATH_RE, the walk's and the kernel's parity contract) admits `[`,
//     `]`, `+`, sentence punctuation and `*`, so a file URI glued to a masked link, code span or tag
//     (`file:///x/y.md[link](u)_bar_`) or to punctuation and a pair (`file:///x/y.md._draft_`) is one token to the
//     scanner, the `_bar_` after it is refused where the base emphasised it, and the walk's target is the whole glued
//     token, ungated (a URI is never in the kernel's map); a space between restores the base's rendering. A `*` inside a
//     URI (`file:///tmp/*.log`) is the built-in's as it stands, so two globbed URIs in one sentence pair their stars as on
//     the base;
//   - a linkable token that is also a GFM autolink (`www.x.co/a_/b.md`: the file gate passes on its extension) is
//     protected though the walk never links under an <a>: `_see www.x.co/a_/b.md now_` keeps its emphasis around the
//     whole URL where the base cut the URL at its underscore;
//   - a run at a plain token's edge (above) closes or opens a prose pair also when another, protected token stands in
//     the same pair (`_see /tmp/_x/y.md and /tmp/z_ now_` ends its emphasis at `z`, where the base nests a second
//     emphasis inside the first path), and when the walk's ASCII word class (path-links.ts isWordCh, the third parity
//     follow-up) splits an accented path in two the second piece begins with a run at its edge (`_see /a-_b/cé_/d.md
//     now_` ends its emphasis at `cé`): the edge rule;
//   - an underscore-wrapped path with a run beside punctuation inside it (`_docs/x_/notes.md_`) fails the file gate on
//     its trailing `_`, is no token, and pairs its wrapping opener with the run inside, as the base does;
//   - the scan reads marked's masked string, where an escaped character is `++` and a link, a code span or a tag is
//     `[aaa]`. An escape inside a path (`/a\-_b/c.md`) splits the scanner's token there, as the kernel's tokeniser
//     splits it at the backslash (the C41 follow-up), and a relative path escaped in its last segment (`a-_b/c_/d\.md`)
//     loses the extension its gate needs;
//   - the mask keeps the length for every BMP character; a backslash before an astral symbol (an emoji) masks three
//     UTF-16 units as two. A run's position is measured here on the unmasked tail with those escapes counted, so a run
//     inside a token is refused whatever follows it (`see /_build/out_ \😀 \👉` is literal, as on the base); the
//     built-in clips the masked string by the unmasked length, marked's own arithmetic, so a pair whose body holds two
//     such escapes ends its emphasis a character early (`_see \😀 \👉 now_`), on this grammar as on the base.
/** The built-in emStrong's lexer for the dry run: lexes nothing, so a refused pair's body is never lexed. The stand-in
 *  the built-in runs on is `{ rules, lexer }` and nothing else, the contract with the installed marked (12.0.2 reads
 *  this.rules.inline and this.lexer.inlineTokens in emStrong, measured by a recording proxy); md-emphasis-override.test.ts
 *  pins it by execution on the installed marked, so an upgrade whose emStrong reads more from `this` goes red there by
 *  name. Unpinned, the throw would land in render.ts md()'s catch, which shows the whole reply as escaped text. */
const DRY_LEXER = { inlineTokens: (): Token[] => [] };
/** marked's own mask letter (a link, a code span or a tag is `[aaa]` in maskedSrc): a word character, so a run hidden
 *  behind it is no delimiter run to the built-in's closer scan, and the flanking of its neighbours reads as intraword. */
const HIDDEN = "a";
/** How many masked strings stay remembered (linkableRuns): the nested lexes marked runs between two delimiters of one
 *  paragraph nest a few levels at most (a `*` pair's body holding a link whose label holds a pair), so the paragraph's
 *  entry is found again after them and moved to the front, whatever the number of such constructs in the paragraph. */
const MEMO_SLOTS = 8;
/** One masked string's linkable tokens, scanned once. `masked` is the string marked handed emStrong; `runs` the tokens the
 *  path walk would link in it, as [start, end) in `masked`, in order (the walk's scanner, its trailing-punctuation trim
 *  and its shape gates, path-links.ts linkifyPathTokens); `whole`, per run, whether the token is one word whole (a `_`
 *  run beside punctuation lies strictly inside it, so its edge runs are hidden and refused with the rest) or keeps the
 *  edge rule; `hidden` is `masked` with every hidden `_` run replaced by HIDDEN, the string the built-in scans for a
 *  closer; `escaped` whether the string holds a masked escape (`++`), when a run's position must count the escapes. */
type LinkableRuns = { masked: string; runs: Array<[number, number]>; whole: boolean[]; hidden: string; escaped: boolean };
const linkableMemo: LinkableRuns[] = [];   // most recent first, at most MEMO_SLOTS
function linkableRuns(masked: string, punctuation: RegExp): LinkableRuns {
  for (let k = 0; k < linkableMemo.length; k++) {
    if (linkableMemo[k].masked !== masked) continue;
    if (k > 0) { const [hit] = linkableMemo.splice(k, 1); linkableMemo.unshift(hit); }
    return linkableMemo[0];
  }
  const runs: Array<[number, number]> = [], whole: boolean[] = [];
  let hidden = "", copied = 0;
  const scan = new PathTokenScanner(masked);
  let from = 0, m: [number, number] | null;
  while ((m = scan.next(from))) {
    const [start, end] = m;
    from = end;                                       // a token that stays prose: the scan resumes after all of it, as the walk's does
    let tok = masked.slice(start, end);
    const trail = trailingPunct(tok);
    if (trail) tok = tok.slice(0, tok.length - trail[0].length);
    if (!tok || !(isFileUri(tok) || looksLikeFilePath(tok) || looksLikeBareFileName(tok))) continue;
    const e = start + tok.length;
    runs.push([start, e]);
    from = e;                                         // a linked token: right after it, its trimmed tail prose
    // its `_` runs: one strictly inside the token (began after the token did, ends before it does) and beside
    // punctuation (marked's own rule for a flanking delimiter) makes the token one word whole
    const inner: Array<[number, number]> = [];
    let atomic = false;
    for (let i = start; i < e; i++) {
      if (masked.charCodeAt(i) !== 95) continue;
      let j = i + 1;
      while (j < e && masked.charCodeAt(j) === 95) j++;
      inner.push([i, j]);
      if (i > start && j < e && (punctuation.test(masked[i - 1]) || punctuation.test(masked[j]))) atomic = true;
      i = j - 1;
    }
    whole.push(atomic);
    for (const [i, j] of inner) {                     // hidden: every run of a whole token, else the runs strictly inside
      if (atomic || (i > start && j < e)) { hidden += masked.slice(copied, i) + HIDDEN.repeat(j - i); copied = j; }
    }
  }
  const entry: LinkableRuns = { masked, runs, whole, hidden: copied ? hidden + masked.slice(copied) : masked, escaped: masked.includes("++") };
  linkableMemo.unshift(entry);
  if (linkableMemo.length > MEMO_SLOTS) linkableMemo.length = MEMO_SLOTS;
  return entry;
}
/** The index in `runs` (in order, disjoint) of the token holding position d, s <= d < e, or -1: a binary search for the
 *  last token that began at or before d. */
function tokenAt(runs: Array<[number, number]>, d: number): number {
  let a = 0, b = runs.length;
  while (a < b) { const mid = (a + b) >> 1; if (runs[mid][0] <= d) a = mid + 1; else b = mid; }
  return a > 0 && d < runs[a - 1][1] ? a - 1 : -1;
}
/** Whether the delimiter run [d0, d1) is the prose's to pair: it lies outside every token, or at the edge of a token that
 *  keeps the edge rule (it begins at the token's start or ends at its end, and the token is not one word whole). */
function proseRun(tokens: LinkableRuns, d0: number, d1: number): boolean {
  const k = tokenAt(tokens.runs, d0);
  if (k < 0) return true;
  const [s, e] = tokens.runs[k];
  return !tokens.whole[k] && (d0 === s || d1 === e);
}
export const pathAwareEmphasis = {
  tokenizer: {
    emStrong(this: Tokenizer, src: string, maskedSrc: string, prevChar = "") {
      if (src.charCodeAt(0) !== 95) return false;                       // a `*` run: not a path character, the built-in's as it stands
      const tokens = linkableRuns(maskedSrc, this.rules.inline.punctuation);
      let at = maskedSrc.length - src.length;                            // where `src` starts in the paragraph: the mask keeps the length ...
      let shifts: number[] | null = null;                                // ... save for an escaped astral symbol, three units masked as two: their offsets in `src`
      if (tokens.escaped && src.includes("\\")) {
        shifts = [];
        const escapes = this.rules.inline.anyPunctuation;               // marked's own escape rule, the one that built the mask
        escapes.lastIndex = 0;
        for (let esc: RegExpExecArray | null; (esc = escapes.exec(src));) if (esc[0].length === 3) shifts.push(esc.index);
        at += shifts.length;
      }
      let run = 1;
      while (src.charCodeAt(run) === 95) run++;
      if (!proseRun(tokens, at, at + run)) return undefined;             // the run is a path's: text, before any scan
      const dry = { rules: this.rules, lexer: DRY_LEXER } as unknown as Tokenizer;
      const pair = Tokenizer.prototype.emStrong.call(dry, src, tokens.hidden, prevChar);   // the closer scan sees no run inside a token
      if (!pair) return undefined;
      const width = pair.type === "strong" ? 2 : 1;                      // the delimiters the pair spends at each end; a longer run's rest is body
      let end = at + pair.raw.length;
      if (shifts) for (const i of shifts) if (i < pair.raw.length) end--;
      if (!proseRun(tokens, end - width, end)) return undefined;         // the spent closer run is a path's: inside a token longer than the pair spends, or at a whole token's edge
      pair.tokens = this.lexer.inlineTokens(pair.text);                 // the body: its own masked string, its own entry in the memo
      return pair;
    },
  },
} as MarkedExtension;

// ── front matter ────────────────────────────────────────────────────────────────────────────────────
// A `---` block at the very start of the document, closed by the next `---` line (Obsidian's and Jekyll's rule),
// whose body reads as a YAML mapping, as ONE token whose raw tiles the source at offset 0, rendered folded: a <details>
// with a summary and the YAML in a <pre>. Before this the lexer read the opener as an <hr> and the keys plus the closer
// as a setext h2, so every Obsidian note opened with a rule and a heading of its own keys (the plan's High defect). Only
// at the top of the DOCUMENT: `tokens === this.lexer.tokens` is true for the top-level token list alone (a blockquote's
// or a list item's body is lexed into a fresh array), so `> ---` inside a quote stays an hr; `state.top` is not that
// test, since the blockquote tokenizer sets it for its body. No `start`: the block is never mid-paragraph.
// Two checks on the body keep a document that merely OPENS with a horizontal rule out of the fold (the 2026-09-09
// review: a reply bounded by rules, `---`, a heading and prose, `---`, folded its first section into a closed "Front
// matter" block, and a `---` inside a fence closed the block early, so the fence's closer became an opener that
// swallowed the rest of the reply). First, pandoc's rule: an opener followed by a blank line is a rule, not a metadata
// block. Second, the body must read as a YAML block mapping (isYamlMapping): every line at the left margin is a `key:`
// line, a `- ` item under a key, a `#` comment or blank, and an indented line belongs to the key above. Prose, a list or
// a fence between two rules fails that and lexes as it always did; YAML as Obsidian, Jekyll and Hugo write it (comments,
// nested values, a sequence under a key, a blank line between keys, a quoted key) passes. Not a YAML parser: a prose line
// with a colon ("See: the notes") reads as a key, and GitHub, which does parse the block, folds that too. A bare key begins
// with a letter or digit of any script, or an underscore (round 3 of the review: the first cut took ASCII alone, so a vault
// whose property names are in its own language, `Über:`, `日本語:`, rendered the original defect again, an hr and a setext
// heading of the keys); a line opening with anything else, YAML's indicators (`-`, `*`, `>`, `$`, `:`) or markup among
// them, is no key.
export const FRONT_MATTER_CLASS = "md-frontmatter";
export const FRONT_MATTER_HEAD_CLASS = "md-frontmatter-head";
export const FRONT_MATTER_LABEL = "Front matter";
export type FrontMatterToken = Tokens.Generic & { text: string };
const FRONT_MATTER_RE = /^---[ \t]*\n(?:([\s\S]*?)\n)?---[ \t]*(?:\n+|$)/;
const YAML_KEY_RE = /^(?:"[^"\n]*"|'[^'\n]*'|[\p{L}\p{N}_][^:\n]*?)[ \t]*:(?:[ \t]|$)/u;
/** Whether `body` reads as a YAML block mapping, the shape front matter takes (the section comment above). */
export function isYamlMapping(body: string): boolean {
  let underKey = false;
  for (const line of body.split("\n")) {
    if (/^[ \t]*(?:#|$)/.test(line)) continue;                            // blank, or a comment
    if (/^[ \t]/.test(line)) { if (!underKey) return false; continue; }      // a nested line: the key above's
    if (/^-(?:[ \t]|$)/.test(line)) { if (!underKey) return false; continue; }   // a sequence item under the key above
    if (!YAML_KEY_RE.test(line)) return false;
    underKey = true;
  }
  return true;
}
export const frontMatter: TokenizerAndRendererExtension = {
  name: "frontMatter",
  level: "block",
  tokenizer(this: LexerThis, src: string, tokens: Token[]) {
    if (tokens !== this.lexer.tokens || tokens.length !== 0) return undefined;
    const m = FRONT_MATTER_RE.exec(src);
    if (!m) return undefined;
    if (m[1] !== undefined && /^[ \t]*(?:\n|$)/.test(m[1])) return undefined;   // pandoc's rule: a blank line after the opener makes it a rule
    if (!isYamlMapping(m[1] || "")) return undefined;
    return { type: "frontMatter", raw: m[0], text: m[1] || "" } as FrontMatterToken;
  },
  renderer(token) {
    const t = token as FrontMatterToken;
    return `<details class="${FRONT_MATTER_CLASS}"><summary class="${FRONT_MATTER_HEAD_CLASS}">${FRONT_MATTER_LABEL}</summary><pre>${escapeHtml(t.text)}</pre></details>`;
  },
};

// ── footnotes ───────────────────────────────────────────────────────────────────────────────────────
// Our own small extension. marked-footnote (not installed) and GitHub render the definitions at the END of the
// document, in a section no block of the source stands for, which breaks the anchor map's pairing of blocks to
// elements (every block after a definition would pair one element early). Here a definition renders IN PLACE, one
// <div> per definition, with a back link; a reference renders as <sup><a href="#fn-id">n</a></sup>. Numbered by
// order of first reference: the reference tokenizer assigns the next number on first sight and keeps the order on
// the LEXER INSTANCE (one per parse, the static Lexer.lex included, so the anchor map's lex numbers the same
// document the same way), and a definition renders the number its id was given, or its id when nothing refers to
// it. The ids arrive in the DOM prefixed `user-content-` (md-sanitize.ts) and the `#fn-id` hrefs land through
// userContentTarget / fragmentTarget in the viewer and the chat's `#` delegate alike. A `[^n]: URL` line used to
// be swallowed as a link reference definition (marked's `def` rule accepts a one-word destination); block
// extensions run before every built-in rule, so it is a footnote now.
// A reference renders ONLY when the document defines its id (GitHub's rule; the 2026-09-09 review: `[^1]` with no
// `[^1]:` line rendered a live-looking numbered link whose click set the page hash and landed nowhere, and lost the
// citation as written). The lexer lexes every block before any inline text (Lexer.lex queues the inline passes), so
// when a reference is lexed the book holds every definition of the document, one inside a quote or a list item
// included; a definition's own text is queued the same way (`lexer.inline`, as marked's paragraph queues its text), so
// a reference in it finds a definition written later. A duplicate definition keeps its class and its back link and
// drops the id, so `#fn-id` lands on the first; a definition nothing refers to shows its marker as written (`[^id]:`)
// as a label with no back link, since the reference it would lead to is not there: the label is a control the anchor
// map and the reader's place skip, so its text is free, and the marker keeps every character the author wrote in view
// where the bare id ran into the text as a word (the 2026-09-09 review, round 2: a regex character class explained at a
// line start, `[^a-z]: matches anything but a lowercase letter`, is GFM's definition shape, which GitHub drops whole;
// here it reads as written, dressed as the orphan note it is). A definition's text runs as far as marked's paragraph rule
// reads a paragraph: to a blank line or a line that starts another block, a lazy continuation line (GitHub's documented
// form) or a two-space indented one (Obsidian's) included, each de-indented by up to four spaces; another definition
// ends it, and so does a line a registered block extension's start hint names (clipAtBlockStarts, the cut marked makes
// before its own paragraph), so a display formula on the line after a definition is a block after the note, as a fence
// or a heading there already was. The regex before this took only four-space continuations, so a wrapped definition
// lost its second line to a paragraph of its own.
// The body renders as a PARAGRAPH inside the div, the back link first in it (GitHub's own shape, `li > p` with the back
// link in the paragraph), never as inline content directly under the div, so the spaces between the body's inline
// elements are a paragraph's to the Rendered paint whatever anchor-map.ts skipBlockWs reads under a DIV. With the body
// directly under the div, the paint's container rule of the time (a whitespace-only text node under a DIV read as the
// white space between blocks and skipped, main's rule through the review round 9) never painted the spaces of
// `[^1]: **a** *b*` or between two links in a definition, and a highlight across the note broke at each (a 4 px gap
// between two ring ends), where main, which rendered the line as a plain paragraph, painted it whole (the 2026-09-09
// review, round 10, which also retired that container rule in anchor-map.ts, so a rendered space between two inline
// children of a div paints too; the paragraph stands on GitHub's shape; md-config-footnote-paint.test.ts and its browser
// leg). The div keeps the footnote's own spacing and rail, so the sheets give the inner paragraph no margin of its own
// (`.md .md-footnote p, .fileview-md .md-footnote p`, both sheets): the box is the one the div had, measured equal to the
// pixel. The literal space between the back link and the body stands in for the author's space after the colon, which
// FOOTNOTE_DEF_HEAD_RE consumes, as marked's task item puts one between its checkbox and the item's text (`checkbox + ' ' +
// text`); it stays: the note's copied and accessible text reads `1 alpha`, not `1alpha` (an inline-block adds no separator of
// its own to a selection's text, measured in headless Chromium), and the sheets' margin-right alone halves the label's gap
// (7.45 px to 3.86 at 15px). When a highlight crosses the note, that space is a rendered space at the head of the body and
// paints as a mark of its own beside the back link, which no mark holds, as the task item's after its checkbox does (the
// 2026-09-09 review, round 11: a ruling, not a slip; md-config-footnote-paint.test.ts and its browser leg pin the mark).
export const FOOTNOTE_CLASS = "md-footnote";
export const FOOTNOTE_REF_CLASS = "md-fnref";
export const FOOTNOTE_BACK_CLASS = "md-fnback";
export const FOOTNOTE_ORPHAN_TITLE = "Nothing in the text refers to this footnote";
export type FootnoteRefToken = Tokens.Generic & { id: string; n: number; k: number };
export type FootnoteDefToken = Tokens.Generic & { id: string; k: number; text: string; tokens: Token[]; order: Map<string, number> };
type FootnoteBook = { order: Map<string, number>; refs: Map<string, number>; defs: Map<string, number> };
function footnoteBook(lexer: object): FootnoteBook {
  const lx = lexer as { __mdFootnotes?: FootnoteBook };
  if (!lx.__mdFootnotes) lx.__mdFootnotes = { order: new Map(), refs: new Map(), defs: new Map() };
  return lx.__mdFootnotes;
}
const FOOTNOTE_REF_RE = /^\[\^([^\]\s]+)\]/;
const FOOTNOTE_DEF_HEAD_RE = /^ {0,3}\[\^([^\]\s]+)\]:[ \t]*/;
export const footnoteRef: TokenizerAndRendererExtension = {
  name: "footnoteRef",
  level: "inline",
  start(src: string) { const m = /\[\^/.exec(src); return m ? m.index : undefined; },
  tokenizer(this: LexerThis, src: string) {
    const m = FOOTNOTE_REF_RE.exec(src);
    if (!m) return undefined;
    const book = footnoteBook(this.lexer);
    if (!book.defs.has(m[1])) return undefined;   // no definition: the citation stays as written
    let n = book.order.get(m[1]);
    if (n === undefined) { n = book.order.size + 1; book.order.set(m[1], n); }
    const k = (book.refs.get(m[1]) || 0) + 1;
    book.refs.set(m[1], k);
    return { type: "footnoteRef", raw: m[0], id: m[1], n, k } as FootnoteRefToken;
  },
  renderer(token) {
    const t = token as FootnoteRefToken;
    const id = escapeHtml(t.id);
    return `<sup class="${FOOTNOTE_REF_CLASS}"><a href="#fn-${id}" id="fnref-${id}${t.k > 1 ? "-" + t.k : ""}">${t.n}</a></sup>`;
  },
};
export const footnoteDef: TokenizerAndRendererExtension = {
  name: "footnoteDef",
  level: "block",
  childTokens: ["tokens"],
  tokenizer(this: LexerThis, src: string) {
    const head = FOOTNOTE_DEF_HEAD_RE.exec(src);
    if (!head) return undefined;
    const para = blockRules(this.lexer).paragraph.exec(clipAtBlockStarts(this.lexer, src));   // the paragraph's extent from this line: lazy and indented continuation lines, to a blank line or another block, an extension's included
    if (!para) return undefined;
    const lines = para[0].split("\n");
    const next = lines.findIndex((l, i) => i > 0 && FOOTNOTE_DEF_HEAD_RE.test(l));   // another definition ends this one
    const kept = next > 0 ? lines.slice(0, next) : lines;
    const body = kept.join("\n");
    const raw = body + (src.charAt(body.length) === "\n" ? "\n" : "");
    // line i of `text` is a suffix of line i of `raw` (the marker, or a continuation line's indent, removed): the shape the anchor map reads
    const text = kept.map((l, i) => (i === 0 ? l.slice(head[0].length) : l.replace(/^(?: {1,4}|\t)/, ""))).join("\n");
    const book = footnoteBook(this.lexer);
    const k = (book.defs.get(head[1]) || 0) + 1;
    book.defs.set(head[1], k);
    const tokens: Token[] = [];
    this.lexer.inline(text, tokens);   // queued: lexed after every block of the document, so a reference in this text finds a definition written later
    return { type: "footnoteDef", raw, id: head[1], k, text, tokens, order: book.order } as FootnoteDefToken;
  },
  renderer(this: ParserThis, token) {
    const t = token as FootnoteDefToken;
    const id = escapeHtml(t.id);
    const label = t.order.get(t.id);
    const idAttr = t.k === 1 ? ` id="fn-${id}"` : "";   // a duplicate definition drops the id, so #fn-id lands on the first
    const back = label === undefined
      ? `<span class="${FOOTNOTE_BACK_CLASS}" title="${FOOTNOTE_ORPHAN_TITLE}">[^${id}]:</span>`   // nothing refers to it: the marker as written, no link to a reference that is not there
      : `<a class="${FOOTNOTE_BACK_CLASS}" href="#fnref-${id}" title="Back to the text">${label}</a>`;
    return `<div class="${FOOTNOTE_CLASS}"${idAttr}><p>${back} ${this.parser.parseInline(t.tokens)}</p></div>`;   // the body a paragraph inside the div (the header)
  },
};

// ── callouts ────────────────────────────────────────────────────────────────────────────────────────
// `> [!NOTE]` and its body, GitHub's five alerts (NOTE, TIP, IMPORTANT, WARNING, CAUTION) and Obsidian's `[!type]
// Title` with any type, plus Obsidian's fold markers: `[!type]-` renders closed and `[!type]+` open, as a
// <details> with the title in its <summary>. A block extension tried before the built-in blockquote (extensions run
// first), so `> [!note]` lexes as a callout wherever a blockquote would, and every other quote is untouched. Its
// extent is the blockquote's own (marked's rule, borrowed): the `>`-prefixed lines that follow, and a paragraph's lazy
// continuation lines with no `>`, to a blank line or another block, so a callout ends exactly where the quote it
// displaces would have (the 2026-09-09 review: a regex that took `>` lines alone cut a wrapped alert at its first
// unprefixed line and rendered the rest as a paragraph outside the tinted block, where GitHub keeps it inside). The
// marker line is spelled as marked spells a quote's: `>`, an optional space or tab, then up to three spaces of
// indentation before `[!` (a tab or a fourth space past that is indented code inside the quote), which is how GitHub
// reads an alert typed with tabs or two spaces (round 3 of the review: the recognition took one space alone, so
// `>\t[!NOTE]` rendered a plain quote reading `[!NOTE]`). The body is de-prefixed with CommonMark's marker, a `>` after
// at most three spaces (QUOTE_PREFIX_RE), and lexed as blocks the way marked's blockquote lexes its own, its two
// preparations included. The marker's indentation is a deliberate difference from marked's blockquote (round 5
// of the review): marked strips a `>` under any indentation (` *>`), so a lazy continuation line indented four or more
// spaces that begins with `>` loses its `>` there, where CommonMark reads such a line as paragraph text (a marker
// takes at most three spaces of indentation) and commonmark.js and GitHub show the `>`; the callout keeps it, GitHub
// being what the callout follows, and the anchor map's suffix view holds either way (each line of the text is a suffix
// of its raw line whether the `>` is stripped or kept). The two preparations: the marker's optional space may be a tab
// (round 2 of the review: `>\tbody` kept its tab, which the nested lex expanded into indented code), and a lazy `===` or
// `--` line is prefixed with four spaces first, so it is a paragraph's text and not a setext underline of the body line
// before it (round 2: a lazy `===` made the line before it an h1 inside the callout, where the blockquote kept both as text; a
// `>`-prefixed one stays the quote's own heading; a `---` line is an hr, which ends the quote before it). The guard
// skips the body's FIRST line: marked's blockquote keeps its first line, so there a guarded line continues that
// paragraph, but the callout takes the marker line as the title, and a lazy underline right under it has no paragraph
// before it to underline; guarded, it was the body's whole first block, four spaces in, which is indented code (round
// 3: `> [!note] Title` over `===` rendered a code block reading `===`). No start hint: the marker line begins with
// `>`, a paragraph interrupt marked's own paragraph rule knows, so the paragraph before a callout already ends at its
// line and a hint could shorten nothing (round 1's hint fired after a newline only, since marked calls a hint on
// `src.slice(1)`; round 2 memoised its answer per frame, md-block-start.ts). What a hint did do (round 3) was set
// marked's `lastParagraphClipped` for a hit ANYWHERE in the remaining source, and that flag joins the next paragraph
// onto the last one, with a newline the source does not hold, whenever a built-in interrupt cut a paragraph and its
// tokenizer then declined (a table header line over a delimiter row of another width): two paragraphs rendered as one
// <p> in a reply, and their joined raw no longer tiled the source for the anchor map. The math hint stays: `$$` is no
// built-in interrupt, so a paragraph would run over a display formula without it. Rendered as a <blockquote> so the
// sheets' blockquote rules and the anchor map's BLOCKQUOTE tag hold; the type rides in a class (`md-callout-note`),
// never a data attribute, since the sanitizer drops every data-* attribute (ALLOW_DATA_ATTR: false, for the reason in
// md-sanitize.ts). The title is the author's, or the type with its first letter capitalised, as plain text.
export const CALLOUT_CLASS = "md-callout";
export const CALLOUT_TITLE_CLASS = "md-callout-title";
export type CalloutToken = Tokens.Generic & { kind: string; fold: "" | "+" | "-"; title: string; text: string; tokens: Token[] };
const CALLOUT_HEAD_RE = /^ {0,3}>[ \t]? {0,3}\[!([A-Za-z][\w-]*)\]([+-]?)(?:[ \t]+([^\n]*?))?[ \t]*$/;
const CALLOUT_GATE_RE = /^ {0,3}>[ \t]? {0,3}\[!/;   // the head's opening: the tokenizer's cheap first test
const QUOTE_PREFIX_RE = /^ {0,3}>[ \t]?/gm;
const SETEXT_GUARD_RE = /\n {0,3}((?:=+|-+) *)(?=\n|$)/g;   // marked's blockquote: "precede setext continuation with 4 spaces so it isn't a setext"
/** The title a callout shows: the author's, else its type capitalised (`note` reads "Note", `CAUTION` "Caution"). */
export function calloutTitle(t: { kind: string; title: string }): string {
  if (t.title) return t.title;
  const k = t.kind.toLowerCase();
  return k.charAt(0).toUpperCase() + k.slice(1);
}
export const callout: TokenizerAndRendererExtension = {
  name: "callout",
  level: "block",
  childTokens: ["tokens"],
  tokenizer(this: LexerThis, src: string) {
    if (!CALLOUT_GATE_RE.test(src)) return undefined;
    const q = blockRules(this.lexer).blockquote.exec(src);
    if (!q) return undefined;
    const raw = q[0];
    const nl = raw.indexOf("\n");
    const m = CALLOUT_HEAD_RE.exec(nl < 0 ? raw : raw.slice(0, nl));
    if (!m) return undefined;
    // the setext guard from the body's SECOND line on (the section comment): the marker line is never lazy, and the body's
    // first line has no paragraph line before it to underline. Line i of text is line i of raw de-prefixed.
    const nl2 = nl < 0 ? -1 : raw.indexOf("\n", nl + 1);
    const guarded = nl2 < 0 ? raw : raw.slice(0, nl2) + raw.slice(nl2).replace(SETEXT_GUARD_RE, "\n    $1");
    const text = guarded.replace(QUOTE_PREFIX_RE, "");
    const tnl = text.indexOf("\n");
    const body = tnl < 0 ? "" : text.slice(tnl + 1);
    const top = this.lexer.state.top;
    this.lexer.state.top = true;
    const tokens = this.lexer.blockTokens(body, []);
    this.lexer.state.top = top;
    return { type: "callout", raw, kind: m[1], fold: (m[2] || "") as "" | "+" | "-", title: m[3] || "", text, tokens } as CalloutToken;
  },
  renderer(this: ParserThis, token) {
    const t = token as CalloutToken;
    const cls = `${CALLOUT_CLASS} ${CALLOUT_CLASS}-${t.kind.toLowerCase().replace(/[^a-z0-9-]/g, "-")}`;
    const title = escapeHtml(calloutTitle(t));
    const body = this.parser.parse(t.tokens);
    if (t.fold) return `<details class="${cls}"${t.fold === "+" ? " open" : ""}><summary class="${CALLOUT_TITLE_CLASS}">${title}</summary>${body}</details>`;
    return `<blockquote class="${cls}"><p class="${CALLOUT_TITLE_CLASS}">${title}</p>${body}</blockquote>`;
  },
};

// ── ==mark== ────────────────────────────────────────────────────────────────────────────────────────
// Obsidian's highlight, rendered as <mark>. The same shape as the double-tilde rule: the opener must touch its
// content (`a == b` in prose stays literal), so the anchor map places it by delimiter width like em and strong. And
// neither delimiter may touch a word on its OUTSIDE: `==` is also the equality operator, which agents write unquoted
// in prose (`a==b and c==d`, `a===b`, `len(a)==0 or len(b)==0`), and the plain delimiter rule paired two comparisons in
// one sentence or heading into a highlight that swallowed the text between and ate the operators (the 2026-09-09
// review). So, as CommonMark's `_` may neither open nor close inside a word, the run of `=` is exactly two; the opener
// is refused when the character before it (the last of the token lexed just before, when there is one) is an ASCII
// letter, digit or underscore, a closing bracket or quote, or another `=`, the characters an operand ends in; and the
// closer is refused when the character after it is an ASCII letter, digit or underscore, or another `=`, since the
// right operand of a comparison begins with one (round 2 of the review: the opener's guard alone knew letters and
// digits, so `len(a)==0 or len(b)==0`, `x[i]==y[j] and a[0]==b[0]`, `'a'==b and 'c'==d` and `f()==1 and g()==2` still
// paired). The closer's guard makes a highlight that runs into a word, `==high==lighted`, literal; a comparison is the
// far commoner shape in a reply. ASCII on purpose, both guards: CJK prose puts no space around a highlight, and a
// letter rule there would refuse it. And the content holds no `==` (round 3 of the review): the first `==` after the
// opener is the closer, and when that one touches a word the text is literal up to it and the lexer moves on, where
// the lazy match ran on to the next `==` that touched no word, so `==high==lighted and ==more== end` rendered one
// highlight from `high` to `more`, eating the second opener, and `if x ==0 or y ==1 then ==done==` one from `0` to
// `done`, the operators inside it. A spaced equality inside a highlight, `==a == b==`, is literal for the same reason,
// the operator reading winning as everywhere in this rule. A code span inside the highlight is skipped whole (round 4
// of the review): the match runs over a copy of the source with marked's code spans masked (markView above, the
// masking marked's own inlineTokens does before em and strong), so a `==` inside one is neither the closer nor a
// forbidden run, and `==see `a==b` here==` highlights `see a==b here` with the comparison in code, as Obsidian renders
// it, CommonMark reading a code span before any delimiter run; before, a `==` inside a code span made the highlight
// literal when a word followed it (round 3) and closed it inside the span when a space did (`==x `y== z` w==`
// highlighted `y` and broke the span, rounds 2 and 3). Only a code span is skipped: `==**a==b**==` stays literal, a
// `==` inside strong being a `==` in prose; and the double-tilde rule above keeps the blind spot its two copies had
// (`~~see `a~~b` here~~` closes at the first `~~`), no change of this slice's. A backslash-escaped `=` is the highlight's
// text (round 5 of the review): marked masks every escaped punctuation character before its em and strong run and hands
// an extension the unmasked source, so the `==` of `\==` closed the highlight when a space followed it, and `==a \== b==
// end` highlighted `a \` and left ` b== end` literal, where `\=` is marked's escape everywhere else in the paragraph
// (`a \== b` renders `a == b`). Now a backslash and one ASCII punctuation character after it are one atom of the content
// (MARK_RE; the pair marked's escape rule reads, CommonMark 2.4) and the view skips a `==` an odd count of backslashes
// precedes (markView), so `==a \== b==` highlights `a == b`, `==x \\== y` closes at its `==` (two backslashes escape
// each other) and `==a\==` is literal, one `=` escaped and one left, as `*a\*` is literal to marked. A backslash before
// any other character (a letter, a space, a newline) is one character of text and that character another (round 6 of
// the review): `==a \b==` highlights `a \b`, and `==a \ == z` is literal, its closer preceded by a space as in `==a ==`,
// where round 5's atom of a backslash and any character paired `\ ` and highlighted `a \ `, and took a line-ending
// backslash with its newline, marked's hard break, into the highlight. The double-tilde rule keeps the escaped-pair
// blind spot, as marked's own gfm del has it (`~~a \~~ b~~` closes at the escaped pair). The element carries a class, `md-mark`,
// so the sheets' rule names the highlight alone and the comment and change marks the panel paints as <mark> elements
// (mark.fc-hl, .fc-presel, .fc-ins, .fc-del; anchor-map.ts makeMark) keep their own dress (round 3: `.fileview-md mark`
// outranked their single-class rules, so every comment highlight in the Rendered view wore the amber wash).
export const MARK_CLASS = "md-mark";
export type MarkToken = Tokens.Generic & { text: string; tokens: Token[] };
/** The content: an escape pair (a backslash and one ASCII punctuation character, marked's escape rule, CommonMark 2.4) or
 *  one character that starts neither `==` nor an escape pair, so every position reads one way and a run of backslashes
 *  costs one pass; the last atom is an escape pair or a character that is neither whitespace, `=` nor a backslash, so a
 *  closer preceded by whitespace is refused whatever precedes the whitespace. */
const MARK_RE = /^==(?=[^\s=])((?:\\[!-\/:-@\[-`{-~]|(?!==|\\[!-\/:-@\[-`{-~])[\s\S])*?(?:\\[!-\/:-@\[-`{-~]|[^\s=\\]))==(?![A-Za-z0-9_=])/;
const OPERAND_END_RE = /[A-Za-z0-9_=)\]'"]$/;
export const mark: TokenizerAndRendererExtension = {
  name: "mark",
  level: "inline",
  start(src: string) { const m = /(?<![A-Za-z0-9_=)\]'"])==(?=[^\s=])/.exec(src); return m ? m.index : undefined; },
  tokenizer(this: LexerThis, src: string, tokens: Token[]) {
    if (src.charCodeAt(0) !== 61 || src.charCodeAt(1) !== 61) return undefined;   // no opener here (marked tries every inline extension at every token's start, so this is the common call)
    if (tokens.length && OPERAND_END_RE.test(tokens[tokens.length - 1].raw)) return undefined;   // after an operand: inside a word, after a closing bracket or quote, or after another =
    const view = markView(this.lexer, src);   // cut at the first `==` outside a code span, the spans before it masked: same offsets, so the match's extent reads the source
    const m = view === null ? null : MARK_RE.exec(view);
    if (!m) return undefined;
    const raw = src.slice(0, m[0].length);
    const text = raw.slice(2, -2);
    return { type: "mark", raw, text, tokens: this.lexer.inlineTokens(text) } as MarkToken;
  },
  renderer(this: ParserThis, token) {
    return `<mark class="${MARK_CLASS}">${this.parser.parseInline((token as MarkToken).tokens)}</mark>`;
  },
};

// ── wikilinks and embeds (decision 2) ───────────────────────────────────────────────────────────────
// `[[Note]]`, `[[Note|alias]]`, `[[Note#Heading]]`, `[[#Heading]]`, and the embeds `![[image.png]]` and `![[Note]]`.
// Resolution needs a directory, and only a FILE document has one, so the renderer emits an anchor ONLY when the
// per-parse walkTokens of the file kind stamped the token `resolved` (file-view-links.ts viewerWalkTokens, run by
// mdBlock for the file kind alone): `[[Note]]` becomes <a href="Note.md">Note</a> (a target that names a file type
// Obsidian opens keeps its extension, KNOWN_EXT_RE; a `#Heading` rides as the fragment), which the file kind's link pass (linkMarkdownAnchors)
// turns into a path link to <dir>/Note.md with the fragment in data-frag, no existence check, exactly as a
// `[text](Note.md#Heading)` link; `[[#Heading]]` is a section link within the same note. Everywhere else (the chat's
// replies, a URL document) the same text renders as an unclickable styled span that says why on hover (the
// ruling's "unclickable styled span"; the hover text names no surface, since the span stands in a reply as well as in
// a document, and "the viewer" is not what a reply's reader is looking at). An image embed (`![[image.png]]`, by extension) renders an <img> when
// resolved, so rewriteFigureSrcs loads it from the file's folder like `![](image.png)` and the comments panel's
// embed grammar (file-comments.ts imageEmbeds) pairs it; `![[image.png|300]]` sets its width as Obsidian does.
// Any other embed (`![[Note]]`, `![[paper.pdf]]`) renders as a link-shaped chip to the file, which opens in the
// viewer. Unresolved, an embed is the dead span too: an <img src="image.png"> in a chat reply would fetch
// `/image.png` from the page's own origin, a request nothing meant to make. An anchor's shown text is the source text
// as written (the alias, or the target with its fragment), so the anchor map places it at `textOffset` in the raw. The
// dead span shows the whole source, brackets included (`[[Note]]`, `![[img.png]]`, an R-style `matrix[[0]]` too): its
// reader is looking at a reply or a URL document, where the alias alone read as plain text and the brackets the author
// typed were gone (the 2026-09-09 review); the anchor map never places a dead span (a chat reply is not mapped, and
// the URL kind keeps its place by blocks alone). Inline extensions run before every built-in inline rule, so the
// tokenizer yields when `]]` is followed by `(` and marked's link rule reads the whole span: `[[docs]](url)` is
// CommonMark's link with the bracketed text `[docs]` (GitHub renders it so), `![[img.png]](url)` its image, and both
// rendered as before this module (round 2 of the review: the wikilink took `[[docs]]` and left `(url)` as prose, a dead
// span plus an autolinked URL in a reply, and in a note a path link to a `docs.md` that does not exist). A span the link
// rule refuses, `[[Note]](see also)`, and adjacent wikilinks, `[[A]][[B]]`, stay wikilinks. A span that names neither a
// file nor a section, `[[ ]]`, `[[#]]`, `![[ ]]`, a folder alone (`[[a/]]`) or an alias of nothing (`[[ | ]]`), is no
// wikilink and stays literal as `[[]]` does (round 3 of the review: in a file document it rendered `<a href="">`, which
// the link pass dressed as an external link that opened the page itself, and `[[a/]]` a path link to a nameless `a/.md`).
export const WIKILINK_CLASS = "fv-wikilink";
export const WIKILINK_EMBED_CLASS = "fv-embed";
export const WIKILINK_DEAD_TITLE = "Not a link that opens here: a wikilink names a file beside the one it is written in, and this text is not a file";
export type WikilinkToken = Tokens.Generic & {
  embed: boolean; image: boolean; target: string; frag: string; alias: string | null;
  text: string; textOffset: number; width: string | null; height: string | null; resolved?: boolean;
};
const WIKILINK_RE = /^(!?)\[\[([^\[\]|\n]+?)(?:\|([^\[\]\n]*))?\]\]/;
const IMAGE_EXT_RE = /\.(png|jpe?g|gif|svg|webp|bmp|avif|apng|ico)$/i;
/** The file types Obsidian opens (its accepted formats: notes, canvases, bases, PDFs, images, audio, video). A target that
 *  names one keeps its extension; any other target is a note's title and gets `.md`, a dotted title (`Note.v2`,
 *  `Release v1.0`, `2026.09.09`) included, since Obsidian resolves such a title to `<title>.md`. `\.[A-Za-z0-9]{1,8}$`
 *  read every dotted title as a file with an extension and linked a file that does not exist (the 2026-09-09 review). */
const KNOWN_EXT_RE = /\.(md|canvas|base|pdf|png|jpe?g|gif|svg|webp|bmp|avif|apng|ico|flac|m4a|mp3|ogg|wav|webm|3gp|mkv|mov|mp4|ogv)$/i;
export const wikilink: TokenizerAndRendererExtension = {
  name: "wikilink",
  level: "inline",
  start(src: string) { const m = /!?\[\[/.exec(src); return m ? m.index : undefined; },
  tokenizer(this: LexerThis, src: string) {
    const m = WIKILINK_RE.exec(src);
    if (!m) return undefined;
    if (src.charAt(m[0].length) === "(" && inlineRules(this.lexer).link.test(src)) return undefined;   // CommonMark's `[[text]](url)`: marked's link rule reads it
    const embed = m[1] === "!";
    const inner = m[2];
    const alias = m[3] !== undefined && m[3] !== "" ? m[3] : null;
    const hash = inner.indexOf("#");
    const target = (hash >= 0 ? inner.slice(0, hash) : inner).trim();
    const frag = hash >= 0 ? inner.slice(hash + 1).trim() : "";
    if (target ? !target.slice(target.lastIndexOf("/") + 1) : !frag) return undefined;   // names neither a file nor a section: literal (the section comment)
    let width: string | null = null, height: string | null = null;
    let text = alias === null ? inner : alias;
    if (embed && alias !== null && /^\d+(?:x\d+)?$/.test(alias)) {
      const [w, h] = alias.split("x");
      width = w; height = h || null;
      text = inner;
    }
    const textOffset = text === inner ? m[1].length + 2 : m[0].indexOf("|") + 1;
    return { type: "wikilink", raw: m[0], embed, image: embed && IMAGE_EXT_RE.test(target), target, frag, alias, text, textOffset, width, height } as WikilinkToken;
  },
  renderer(token) {
    const t = token as WikilinkToken;
    const text = escapeHtml(t.text);
    const dead = `<span class="${WIKILINK_CLASS} fv-dead" title="${escapeHtml(WIKILINK_DEAD_TITLE)}">${escapeHtml(t.raw)}</span>`;   // the source as written
    if (!t.resolved) return dead;
    const file = t.target && !KNOWN_EXT_RE.test(t.target.slice(t.target.lastIndexOf("/") + 1)) ? t.target + ".md" : t.target;
    const path = cleanUrl(file);
    const frag = t.frag ? cleanUrl(t.frag) : "";
    if (path === null || frag === null) return dead;
    if (t.embed && t.image) {
      const size = (t.width ? ` width="${escapeHtml(t.width)}"` : "") + (t.height ? ` height="${escapeHtml(t.height)}"` : "");
      return `<img src="${escapeHtml(path)}" alt="${text}"${size}>`;
    }
    const href = escapeHtml(path + (frag ? "#" + frag : ""));
    if (t.embed) return `<a class="${WIKILINK_EMBED_CLASS}" href="${href}">${text}</a>`;
    return `<a href="${href}">${text}</a>`;
  },
};
/** The stamp the file kind's walkTokens puts on a wikilink token, so the renderer emits an anchor (above). */
export function resolveWikilink(token: { type: string }): void {
  if (token.type === "wikilink") (token as WikilinkToken).resolved = true;
}

// ── the one list, and the one call ─────────────────────────────────────────────────────────────────
/** Every extension the singleton takes, in one list, so chat-md.ts's breaks:true instance for the user's own
 *  words takes exactly the same grammar (a user message with math or strikethrough renders as before; only its
 *  newlines differ). */
export const mdExtensions: MarkedExtension[] = [
  delDoubleTilde,
  { extensions: [mathBlock, mathInline, frontMatter, footnoteDef, footnoteRef, callout, mark, wikilink] },
];
// The math fill rides every sanitizeMd call in a bundle that carries this module (md-sanitize.ts
// registerMdPostPass: idempotent), so the grammar and its fill travel together and no renderer calls it by
// hand. Registered at load, beside the list, because chat-md.ts's user-text instance takes the list without
// calling applyMdConfig().
registerMdPostPass(renderMathPlaceholders);

let applied = false;
/** Configure the shared `marked` singleton: GFM without hard breaks (assistant output and a note are real markdown,
 *  where a lone newline is a soft wrap), and every extension above. Idempotent: the first call configures, every
 *  later one (render.ts, file-view.ts and anchor-map.ts all call it at load, and a bundle may carry all three) is a
 *  no-op, so no tokenizer is registered twice. */
export function applyMdConfig(): void {
  if (applied) return;
  applied = true;
  marked.setOptions({ gfm: true, breaks: false });
  marked.use(...mdExtensions);
}

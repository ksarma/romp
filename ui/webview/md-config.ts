// ONE markdown configuration for every bundle (plans/markdown-viewer.md, Slice 4: "one markdown configuration,
// Obsidian constructs included"). Before this module the chat (render.ts) and the viewer (file-view.ts) each
// configured the shared `marked` singleton, the chat with a grammar the viewer's bundles never saw (the math
// extensions came in through chat-md.ts, imported by render.ts alone), so a note's `$x^2$` rendered in the chat
// page's viewer and stayed literal in the Files pane and the feed, and the anchor map (anchor-map.ts), which lexes
// the same source with the static `Lexer.lex`, saw whatever grammar its bundle happened to carry. Now render.ts,
// file-view.ts and anchor-map.ts each call applyMdConfig() at load, chat-md.ts builds its breaks:true instance
// from the same `mdExtensions` list, and the eight test copies of the viewer's configuration call the function.
//
// Registered on the SINGLETON on purpose, never on a private `Marked` instance: `marked.use` writes the module
// defaults the static `Lexer.lex` reads, so anchor-map.ts's lexer sees every extension here and pairs the same
// tokens the renderer rendered; an instance's extensions never reach the static lexer (measured 2026-09-08). The
// one consequence, recorded in the plan's Slice 4 build note: the Obsidian constructs render in chat replies too.
// A wikilink there is the dead styled span (no directory to resolve against), a reply that opens with YAML folds.
//
// Extensions, not string preprocessing: every construct is a marked token whose `raw` tiles the source, so the
// anchor map can place it (anchor-map.ts walkBlocks and walkInline have a case per token type below). Every block
// construct renders as ONE element in place, so the map's 1:1 block-to-element pairing holds, and none of them
// emits author HTML: the markup here is the viewer's own and the sanitizer (md-sanitize.ts) keeps it, classes
// included; an author's `id` gains the `user-content-` prefix there, so the footnote ids below land through
// userContentTarget / fragmentTarget as any author id does.
import { marked, type MarkedExtension, type Token, type Tokens, type TokenizerAndRendererExtension } from "marked";
import { mathBlock, mathInline, renderMathPlaceholders } from "./math";
import { registerMdPostPass } from "./md-sanitize";

// ── helpers ─────────────────────────────────────────────────────────────────────────────────────────
function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
/** marked's own cleaning of a link destination (cleanUrl): percent-encode what needs it, keep an author's escapes. */
function cleanUrl(href: string): string | null {
  try { return encodeURI(href).replace(/%25/g, "%"); } catch { return null; }
}
type LexerThis = { lexer: { tokens: Token[]; state: { top: boolean }; blockTokens(src: string, tokens: Token[]): Token[]; inlineTokens(src: string): Token[] } };
type ParserThis = { parser: { parse(tokens: Token[]): string; parseInline(tokens: Token[]): string } };

// ── strikethrough on DOUBLE tildes only ─────────────────────────────────────────────────────────────
// (the user 2026-06-26). marked's built-in GFM `del` tokenizer also fires on a SINGLE tilde, so prose like "near
// the ~21 Wh/day budget … gives ~1.5–2 days" rendered as one big <del> struck through from the first ~ to the
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

// ── front matter ────────────────────────────────────────────────────────────────────────────────────
// A `---` block at the very start of the document, closed by the next `---` line (Obsidian's and Jekyll's rule),
// as ONE token whose raw tiles the source at offset 0, rendered folded: a <details> with a summary and the YAML in
// a <pre>. Before this the lexer read the opener as an <hr> and the keys plus the closer as a setext h2, so every
// Obsidian note opened with a rule and a heading of its own keys (the plan's High defect). Only at the top of the
// DOCUMENT: `tokens === this.lexer.tokens` is true for the top-level token list alone (a blockquote's or a list
// item's body is lexed into a fresh array), so `> ---` inside a quote stays an hr; `state.top` is not that test,
// since the blockquote tokenizer sets it for its body. No `start`: the block is never mid-paragraph.
export const FRONT_MATTER_CLASS = "md-frontmatter";
export const FRONT_MATTER_HEAD_CLASS = "md-frontmatter-head";
export const FRONT_MATTER_LABEL = "Front matter";
export type FrontMatterToken = Tokens.Generic & { text: string };
const FRONT_MATTER_RE = /^---[ \t]*\n(?:([\s\S]*?)\n)?---[ \t]*(?:\n+|$)/;
export const frontMatter: TokenizerAndRendererExtension = {
  name: "frontMatter",
  level: "block",
  tokenizer(this: LexerThis, src: string, tokens: Token[]) {
    if (tokens !== this.lexer.tokens || tokens.length !== 0) return undefined;
    const m = FRONT_MATTER_RE.exec(src);
    if (!m) return undefined;
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
export const FOOTNOTE_CLASS = "md-footnote";
export const FOOTNOTE_REF_CLASS = "md-fnref";
export const FOOTNOTE_BACK_CLASS = "md-fnback";
export type FootnoteRefToken = Tokens.Generic & { id: string; n: number; k: number };
export type FootnoteDefToken = Tokens.Generic & { id: string; text: string; tokens: Token[]; order: Map<string, number> };
type FootnoteBook = { order: Map<string, number>; refs: Map<string, number> };
function footnoteBook(lexer: object): FootnoteBook {
  const lx = lexer as { __mdFootnotes?: FootnoteBook };
  if (!lx.__mdFootnotes) lx.__mdFootnotes = { order: new Map(), refs: new Map() };
  return lx.__mdFootnotes;
}
const FOOTNOTE_REF_RE = /^\[\^([^\]\s]+)\]/;
const FOOTNOTE_DEF_RE = /^ {0,3}\[\^([^\]\s]+)\]:[ \t]*([^\n]*(?:\n(?: {4}|\t)[^\n]*)*)(?:\n|$)/;
export const footnoteRef: TokenizerAndRendererExtension = {
  name: "footnoteRef",
  level: "inline",
  start(src: string) { const m = /\[\^/.exec(src); return m ? m.index : undefined; },
  tokenizer(this: LexerThis, src: string) {
    const m = FOOTNOTE_REF_RE.exec(src);
    if (!m) return undefined;
    const book = footnoteBook(this.lexer);
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
    const m = FOOTNOTE_DEF_RE.exec(src);
    if (!m) return undefined;
    const text = m[2].replace(/\n(?: {4}|\t)/g, "\n");
    return { type: "footnoteDef", raw: m[0], id: m[1], text, tokens: this.lexer.inlineTokens(text), order: footnoteBook(this.lexer).order } as FootnoteDefToken;
  },
  renderer(this: ParserThis, token) {
    const t = token as FootnoteDefToken;
    const id = escapeHtml(t.id);
    const label = t.order.get(t.id);
    return `<div class="${FOOTNOTE_CLASS}" id="fn-${id}"><a class="${FOOTNOTE_BACK_CLASS}" href="#fnref-${id}" title="Back to the text">${label === undefined ? id : label}</a> ${this.parser.parseInline(t.tokens)}</div>`;
  },
};

// ── callouts ────────────────────────────────────────────────────────────────────────────────────────
// `> [!NOTE]` and its body, GitHub's five alerts (NOTE, TIP, IMPORTANT, WARNING, CAUTION) and Obsidian's `[!type]
// Title` with any type, plus Obsidian's fold markers: `[!type]-` renders closed and `[!type]+` open, as a
// <details> with the title in its <summary>. A block extension tried before the built-in blockquote (extensions run
// first), so `> [!note]` lexes as a callout wherever a blockquote would, and every other quote is untouched. The
// body is the `>`-prefixed lines that follow, de-prefixed and lexed as blocks the way marked's blockquote lexes its
// own (a lazy continuation line with no `>` ends the callout). Rendered as a <blockquote> so the sheets'
// blockquote rules and the anchor map's BLOCKQUOTE tag hold; the type rides in a class (`md-callout-note`), never
// a data attribute, since the sanitizer drops every data-* attribute (ALLOW_DATA_ATTR: false, for the reason in
// md-sanitize.ts). The title is the author's, or the type with its first letter capitalised, as plain text.
export const CALLOUT_CLASS = "md-callout";
export const CALLOUT_TITLE_CLASS = "md-callout-title";
export type CalloutToken = Tokens.Generic & { kind: string; fold: "" | "+" | "-"; title: string; text: string; tokens: Token[] };
const CALLOUT_RE = /^ {0,3}> ?\[!([A-Za-z][\w-]*)\]([+-]?)(?:[ \t]+([^\n]*?))?[ \t]*(?:\n|$)((?: {0,3}>[^\n]*(?:\n|$))*)/;
const QUOTE_PREFIX_RE = /^ {0,3}> ?/gm;
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
  start(src: string) { const m = /(?:^|\n) {0,3}> ?\[!/.exec(src); return m ? m.index : undefined; },
  tokenizer(this: LexerThis, src: string) {
    const m = CALLOUT_RE.exec(src);
    if (!m) return undefined;
    const body = m[4].replace(QUOTE_PREFIX_RE, "");
    const top = this.lexer.state.top;
    this.lexer.state.top = true;
    const tokens = this.lexer.blockTokens(body, []);
    this.lexer.state.top = top;
    return { type: "callout", raw: m[0], kind: m[1], fold: (m[2] || "") as "" | "+" | "-", title: m[3] || "", text: m[0].replace(QUOTE_PREFIX_RE, ""), tokens } as CalloutToken;
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
// content (`a == b` in prose stays literal), so the anchor map places it by delimiter width like em and strong.
export type MarkToken = Tokens.Generic & { text: string; tokens: Token[] };
export const mark: TokenizerAndRendererExtension = {
  name: "mark",
  level: "inline",
  start(src: string) { const m = /==(?=\S)/.exec(src); return m ? m.index : undefined; },
  tokenizer(this: LexerThis, src: string) {
    const m = /^==(?=\S)([\s\S]*?\S)==/.exec(src);
    if (!m) return undefined;
    return { type: "mark", raw: m[0], text: m[1], tokens: this.lexer.inlineTokens(m[1]) } as MarkToken;
  },
  renderer(this: ParserThis, token) {
    return `<mark>${this.parser.parseInline((token as MarkToken).tokens)}</mark>`;
  },
};

// ── wikilinks and embeds (decision 2) ───────────────────────────────────────────────────────────────
// `[[Note]]`, `[[Note|alias]]`, `[[Note#Heading]]`, `[[#Heading]]`, and the embeds `![[image.png]]` and `![[Note]]`.
// Resolution needs a directory, and only a FILE document has one, so the renderer emits an anchor ONLY when the
// per-parse walkTokens of the file kind stamped the token `resolved` (file-view-links.ts viewerWalkTokens, run by
// mdBlock for the file kind alone): `[[Note]]` becomes <a href="Note.md">Note</a> (a target that already names an
// extension keeps it; a `#Heading` rides as the fragment), which the file kind's link pass (linkMarkdownAnchors)
// turns into a path link to <dir>/Note.md with the fragment in data-frag, no existence check, exactly as a
// `[text](Note.md#Heading)` link; `[[#Heading]]` is a section link within the same note. Everywhere else (the chat's
// replies, a URL document) the same text renders as an unclickable styled span that says why on hover (the
// ruling's "unclickable styled span"). An image embed (`![[image.png]]`, by extension) renders an <img> when
// resolved, so rewriteFigureSrcs loads it from the file's folder like `![](image.png)` and the comments panel's
// embed grammar (file-comments.ts imageEmbeds) pairs it; `![[image.png|300]]` sets its width as Obsidian does.
// Any other embed (`![[Note]]`, `![[paper.pdf]]`) renders as a link-shaped chip to the file, which opens in the
// viewer. Unresolved, an embed is the dead span too: an <img src="image.png"> in a chat reply would fetch
// `/image.png` from the page's own origin, a request nothing meant to make. The shown text is the source text as
// written (the alias, or the target with its fragment), so the anchor map places it at `textOffset` in the raw.
export const WIKILINK_CLASS = "fv-wikilink";
export const WIKILINK_EMBED_CLASS = "fv-embed";
export const WIKILINK_DEAD_TITLE = "Not a link the viewer can follow here: a wikilink names a file beside the one it is written in, and there is no file here";
export type WikilinkToken = Tokens.Generic & {
  embed: boolean; image: boolean; target: string; frag: string; alias: string | null;
  text: string; textOffset: number; width: string | null; height: string | null; resolved?: boolean;
};
const WIKILINK_RE = /^(!?)\[\[([^\[\]|\n]+?)(?:\|([^\[\]\n]*))?\]\]/;
const IMAGE_EXT_RE = /\.(png|jpe?g|gif|svg|webp|bmp|avif|apng|ico)$/i;
const HAS_EXT_RE = /\.[A-Za-z0-9]{1,8}$/;
export const wikilink: TokenizerAndRendererExtension = {
  name: "wikilink",
  level: "inline",
  start(src: string) { const m = /!?\[\[/.exec(src); return m ? m.index : undefined; },
  tokenizer(src: string) {
    const m = WIKILINK_RE.exec(src);
    if (!m) return undefined;
    const embed = m[1] === "!";
    const inner = m[2];
    const alias = m[3] !== undefined && m[3] !== "" ? m[3] : null;
    const hash = inner.indexOf("#");
    const target = (hash >= 0 ? inner.slice(0, hash) : inner).trim();
    const frag = hash >= 0 ? inner.slice(hash + 1).trim() : "";
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
    if (!t.resolved) return `<span class="${WIKILINK_CLASS} fv-dead" title="${escapeHtml(WIKILINK_DEAD_TITLE)}">${text}</span>`;
    const file = t.target && !HAS_EXT_RE.test(t.target.slice(t.target.lastIndexOf("/") + 1)) ? t.target + ".md" : t.target;
    const path = cleanUrl(file);
    const frag = t.frag ? cleanUrl(t.frag) : "";
    if (path === null || frag === null) return `<span class="${WIKILINK_CLASS} fv-dead" title="${escapeHtml(WIKILINK_DEAD_TITLE)}">${text}</span>`;
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

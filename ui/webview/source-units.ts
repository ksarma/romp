/** A source read as its language reads it, for the pins of the link-navigation follow-on (plans/markdown-viewer.md,
 *  "Follow-on: Link navigation (2026-09-19)"). The file review's round 4 ruled one rule over three guards (regression-2 with
 *  extra6-1, tests-2, and the review-name pin under rules-1): a guard against a FORM is keyed on the property or it parses;
 *  each of the three had been keyed on one spelling and claimed more than it checked (the refused-state pins on the
 *  double-quoted literal, blind to a single-quoted comparison; the attribution pin on one apostrophe, blind to the escaped one
 *  inside a JS string). So the TypeScript compiler's parser reads a TS or JS module here: a STRING the program sees as one
 *  value is one unit with that value (either quote, every escape resolved; a `+` chain of string, template and numeric
 *  literals as the value JS computes, left to right, so `1 + 2 + "a"` is `3a`, the chain's all-literal prefix up to its first
 *  non-literal operand folded and the rest read operand by operand; a substitution template as its spans joined with each
 *  hole kept as its source text between `${` and `}`, so a phrase split by a hole is judged whole with the hole named), its
 *  regular expression literals, and its COMMENTS as text with the markers stripped and a run of line comments joined, so a
 *  sentence wrapped over two comment lines is one unit (the file review's round 5, correctness-2 with extra6-1 and tests-2:
 *  each literal TOKEN had been a unit of its own, so a phrase split across a `+` or a hole sat in no unit), and in a .tsx or
 *  .jsx module the TEXT between JSX tags as written (kind "jsxtext"; the author's closing pass after the file review's round 5,
 *  reader-1: the attribute's literal had been read and the text child skipped, so a phrase planted as JSX text sat in no unit).
 *  What is still NOT read as the program's value, and is outside every guard built on this reader: the value a hole takes at
 *  run time, the part of a chain at and after a non-literal operand (each literal there its own unit, so a round or an id split
 *  at its hyphen or its digits across those operands, `who + "round N (records-" + "M)"`, sits in no unit and no message names it;
 *  the same closing pass, reader-7), a join or a concat call (each literal its own unit), a tagged template
 *  (String.raw among them: read as its cooked spans whatever the tag returns, except that a span the template grammar rejects
 *  and the compiler reads raw, `String.raw`(a)\1``, is read as its raw body, the value String.raw sees; the same closing pass,
 *  reader-3: the throw below had reached it, one such literal in any candidate file aborting the read of the whole tree),
 *  a BigInt (`9n`) and a unary minus (`-9`) in a chain (not leaves: the chain is read operand by operand from there). An
 *  UNTAGGED literal the compiler read with an error (unterminated, an invalid escape) makes the walk and the compiler disagree
 *  on the value, and the read THROWS naming the file, the kind and the line rather than charge lines it cannot vouch for;
 *  before this the erroneous token was read silently. Markdown, which
 *  the compiler does not read, is read as paragraphs as it stands (unitsOf routes on the suffix: the compiler for .ts, .mts,
 *  .cts, .tsx, .js, .mjs, .cjs and .jsx, each with its script kind; prose for the suffixes it lists and for a file with none;
 *  any other suffix refused by name rather than read as prose, the file review's round 5, correctness-7 with tests-4 and
 *  extra7-2); Python as paragraphs with its string literals cooked as
 *  Python cooks them (`\n`, `\t`, `\r` and the other control escapes to a space, `\'`, `\"` and `\\` to the character, `\xNN`,
 *  `\uNNNN`, `\UNNNNNNNN` and an octal escape to the code point, an unknown escape and `\N{...}` kept as written, a backslash
 *  before the line end a continuation), adjacent literals (`'a' 'b'`, across a continuation or a wrapped line too) glued with
 *  nothing between them as the program glues them, an f-string's field kept as written between its braces, a raw literal as
 *  written, and a `#` comment as written (the file review's round 5, extra6-3: every backslash had been dropped, so `\n` read as
 *  the letter n and glued the words the escape separated, missing a real phrase and able to manufacture one). Not read there: a
 *  literal's own quote inside an f-string field (Python 3.12 syntax) ends the read of the literal early. Every unit maps an
 *  offset of its text back to the source line it came from (lineAt) through a starts map built from SOURCE positions (each
 *  cooked character knows the offset of the source that produced it, so an escaped newline is a character of the value and no
 *  line, a continuation is a line and no character; the file review's round 5, correctness-1 with tests-3 and extra7-1: the map
 *  had counted the newlines of the COOKED text, charging a one-line literal's fault to lines past the literal, and an added-line
 *  filter then dropped the fault), so a reader can judge a phrase with its whole unit as context and still charge it to the
 *  line that carries it. The two readers: file-view-figure-shapes.test.ts (the refused states' literals) and
 *  linknav-records-attribution.test.ts (the rounds the records name).
 *  Node-only: the tests import it; the webview bundle never does. */
import * as ts from "typescript";

export type UnitKind = "comment" | "string" | "template" | "regex" | "jsxtext" | "prose";
/** One readable unit of a source: `text` is the value (a literal's cooked text, a comment's words, a paragraph), `line` and
 *  `endLine` its 1-based lines, `pos` and `end` its offsets in the source, and `starts` the offset in `text` at which each
 *  source line's contribution begins, in line order (lineAt reads it). */
export type Unit = { kind: UnitKind; text: string; line: number; endLine: number; pos: number; end: number; starts: { line: number; at: number }[] };

/** The source line a text offset of the unit came from: the last line whose contribution starts at or before it. */
export function lineAt(u: Unit, offset: number): number {
  let line = u.line;
  for (const s of u.starts) { if (s.at <= offset) line = s.line; else break; }
  return line;
}

/** The compiler's script kind for a suffix: JS for .js, .mjs and .cjs; JSX for .jsx; TSX for .tsx (a JSX body parsed as TS
 *  misreads a closing tag as a regular expression); TS for .ts, .mts and .cts. */
const scriptKind = (file: string): ts.ScriptKind => (/\.(?:m?js|cjs)$/.test(file) ? ts.ScriptKind.JS : /\.jsx$/.test(file) ? ts.ScriptKind.JSX : /\.tsx$/.test(file) ? ts.ScriptKind.TSX : ts.ScriptKind.TS);

/** A unit built line by line: each piece is trimmed, its inner whitespace collapsed, and appended after one space; a piece
 *  that is empty adds nothing and no start. A piece added with `glue` continues the piece before it with nothing between
 *  (Python's adjacent literals, a continuation inside a literal), keeping one space only where the source had whitespace at
 *  the join. */
class Builder {
  text = "";
  starts: { line: number; at: number }[] = [];
  private trailingSpace = false;
  add(line: number, piece: string, glue = false): void {
    const collapsed = piece.replace(/\s+/g, " ");
    const t = collapsed.trim();
    if (!t) { this.trailingSpace = this.trailingSpace || collapsed.length > 0; return; }
    if (this.text) this.text += glue ? (this.trailingSpace || /^\s/.test(collapsed) ? " " : "") : " ";
    this.starts.push({ line, at: this.text.length });
    this.text += t;
    this.trailingSpace = /\s$/.test(collapsed);
  }
}

// ── TS and JS: the compiler's read ─────────────────────────────────────────────────────────────────

/** A run of cooked text with, for each of its characters, the offset of the source that produced it. */
type Piece = { text: string; src: number[] };
const join = (a: Piece, b: Piece): Piece => ({ text: a.text + b.text, src: a.src.concat(b.src) });
/** Source text as it stands (a regular expression, a template's hole), each character its own offset. */
const verbatim = (source: string, pos: number, end: number): Piece => ({ text: source.slice(pos, end), src: Array.from({ length: end - pos }, (_, i) => pos + i) });
/** A text every character of which came from one source offset (a number's digits, from its token). */
const fromOne = (text: string, pos: number): Piece => ({ text, src: Array.from({ length: text.length }, () => pos) });

const isHex = (c: string | undefined): boolean => c !== undefined && /^[0-9a-fA-F]$/.test(c);
const isOct = (c: string | undefined): boolean => c !== undefined && c >= "0" && c <= "7";
/** A literal's raw body (the source between its delimiters, starting at source offset `at`) cooked with the scanner's escape
 *  rules, each cooked character charged to the offset of the source that produced it: an escape is one character (or two
 *  UTF-16 units) at the backslash's offset and no source line; a backslash before a line terminator is a continuation with no
 *  character; inside a template a line terminator is one cooked newline (a CRLF one). */
function cookBody(body: string, at: number, template: boolean): Piece {
  let text = "";
  const src: number[] = [];
  const put = (s: string, from: number): void => { text += s; for (let k = 0; k < s.length; k++) src.push(from); };
  for (let i = 0; i < body.length; ) {
    const ch = body[i];
    const here = at + i;
    if (ch === "\\") {
      const nx = body[i + 1];
      if (nx === "\r" && body[i + 2] === "\n") { i += 3; continue; }
      if (nx === "\n" || nx === "\r" || nx === "\u2028" || nx === "\u2029") { i += 2; continue; }
      if (nx === "x") {
        if (isHex(body[i + 2]) && isHex(body[i + 3])) put(String.fromCharCode(parseInt(body.slice(i + 2, i + 4), 16)), here);
        i += 4; continue;
      }
      if (nx === "u") {
        if (body[i + 2] === "{") {
          const close = body.indexOf("}", i + 3);
          const digits = close < 0 ? "" : body.slice(i + 3, close);
          if (close >= 0 && /^[0-9a-fA-F]+$/.test(digits) && parseInt(digits, 16) <= 0x10ffff) put(String.fromCodePoint(parseInt(digits, 16)), here);
          i = close < 0 ? body.length : close + 1; continue;
        }
        if (isHex(body[i + 2]) && isHex(body[i + 3]) && isHex(body[i + 4]) && isHex(body[i + 5])) put(String.fromCharCode(parseInt(body.slice(i + 2, i + 6), 16)), here);
        i += 6; continue;
      }
      if (nx === "0" && !(body[i + 2] !== undefined && body[i + 2] >= "0" && body[i + 2] <= "9")) { put("\0", here); i += 2; continue; }
      if (isOct(nx)) {
        let j = i + 2;
        const max = nx <= "3" ? i + 4 : i + 3;
        while (j < max && isOct(body[j])) j++;
        put(String.fromCharCode(parseInt(body.slice(i + 1, j), 8)), here); i = j; continue;
      }
      const simple: Record<string, string> = { b: "\b", f: "\f", n: "\n", r: "\r", t: "\t", v: "\v" };
      if (nx !== undefined && simple[nx] !== undefined) { put(simple[nx], here); i += 2; continue; }
      if (nx === undefined) { i += 1; continue; }
      const cp = body.codePointAt(i + 1)!;
      const w = cp > 0xffff ? 2 : 1;
      put(body.slice(i + 1, i + 1 + w), here); i += 1 + w; continue;
    }
    if (template && ch === "\r") { put("\n", here); i += body[i + 1] === "\n" ? 2 : 1; continue; }
    put(ch, here); i += 1;
  }
  return { text, src };
}

type Token = ts.StringLiteral | ts.NoSubstitutionTemplateLiteral | ts.TemplateHead | ts.TemplateMiddle | ts.TemplateTail;
const isToken = (n: ts.Node): n is Token => ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n) || ts.isTemplateTail(n);
/** Whether a template token stands in a tagged template (`tag`...``): the literal itself, or the substitution template its
 *  span belongs to, is the tag's template. */
function isTagged(n: Token): boolean {
  let t: ts.Node = n;
  while (t.parent !== undefined && (ts.isTemplateSpan(t.parent) || ts.isTemplateExpression(t.parent))) t = t.parent;
  return t.parent !== undefined && ts.isTaggedTemplateExpression(t.parent) && t.parent.template === t;
}
/** A literal token cooked from its raw body, checked against the value the compiler gave it. A span of a TAGGED template
 *  whose escape the template grammar rejects (`String.raw`(a)\1``, a backreference; `\xq`) is valid code the compiler reads
 *  raw, and is read here as its raw body, the value String.raw sees (the author's closing pass after the file review's round
 *  5, reader-3: the throw had reached it, and one such literal in any candidate file aborted a tree-wide read). */
function cookToken(n: Token, sf: ts.SourceFile, file: string): Piece {
  const start = n.getStart(sf);
  const raw = sf.text.slice(start, n.end);
  const tail = ts.isTemplateHead(n) || ts.isTemplateMiddle(n) ? 2 : 1;
  const body = raw.slice(1, Math.max(1, raw.length - tail));
  // a JSX attribute's quoted value has no escapes: the program sees its characters as written (the compiler reads it so)
  const piece = ts.isStringLiteral(n) && n.parent !== undefined && ts.isJsxAttribute(n.parent) ? verbatim(sf.text, start + 1, start + 1 + body.length) : cookBody(body, start + 1, !ts.isStringLiteral(n));
  if (piece.text !== n.text) {
    const rawBody = verbatim(sf.text, start + 1, start + 1 + body.length);
    if (!ts.isStringLiteral(n) && isTagged(n) && rawBody.text === n.text) return rawBody;
    const line = sf.getLineAndCharacterOfPosition(start).line + 1;
    throw new Error("source-units: " + file + ":" + line + " " + (ts.isStringLiteral(n) ? "string" : "template") + " literal " + JSON.stringify(raw.slice(0, 40)) + " cooks to " + JSON.stringify(piece.text.slice(0, 40)) + " where the compiler read " + JSON.stringify(n.text.slice(0, 40)) + " (an unterminated literal or an invalid escape); the reader cannot charge its lines and stops");
  }
  return piece;
}

/** A value the program sees as one string or number, from an all-literal expression: a string or template literal, a numeric
 *  literal, a substitution template (its holes as their source text), or a `+` chain of these, through parentheses; null where
 *  any leaf is something else. `holes` are the substitution expressions, read for literals of their own. */
type Folded = { value: string | number; piece: Piece | null; from: number; holes: ts.Expression[] };
function fold(n: ts.Node, sf: ts.SourceFile, file: string): Folded | null {
  while (ts.isParenthesizedExpression(n)) n = n.expression;
  if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)) return { value: n.text, piece: cookToken(n, sf, file), from: n.getStart(sf), holes: [] };
  if (ts.isNumericLiteral(n)) return { value: Number(n.text.replace(/_/g, "")), piece: null, from: n.getStart(sf), holes: [] };
  if (ts.isTemplateExpression(n)) {
    let piece = cookToken(n.head, sf, file);
    const holes: ts.Expression[] = [];
    let holeFrom = n.head.end - 2;
    for (const span of n.templateSpans) {
      const holeEnd = span.literal.getStart(sf) + 1;
      piece = join(piece, verbatim(sf.text, holeFrom, holeEnd));
      piece = join(piece, cookToken(span.literal, sf, file));
      holes.push(span.expression);
      holeFrom = span.literal.end - 2;
    }
    return { value: piece.text, piece, from: n.getStart(sf), holes };
  }
  if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.PlusToken) {
    const l = fold(n.left, sf, file), r = fold(n.right, sf, file);
    if (!l || !r) return null;
    if (typeof l.value === "number" && typeof r.value === "number") return { value: l.value + r.value, piece: null, from: l.from, holes: [] };
    const asPiece = (f: Folded): Piece => f.piece ?? fromOne(String(f.value), f.from);
    return { value: String(l.value) + String(r.value), piece: join(asPiece(l), asPiece(r)), from: l.from, holes: [...l.holes, ...r.holes] };
  }
  return null;
}

/** The literal tokens of a module, for blanking before the comment scan. */
function tokenSpans(sf: ts.SourceFile): { pos: number; end: number }[] {
  const out: { pos: number; end: number }[] = [];
  const visit = (n: ts.Node): void => {
    if (isToken(n) || ts.isRegularExpressionLiteral(n)) out.push({ pos: n.getStart(sf), end: n.end });
    else if (ts.isJsxText(n)) out.push({ pos: n.pos, end: n.end });   // its quotes and slashes open no literal and no comment
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out.sort((a, b) => a.pos - b.pos);
}

/** Every string-like value of a TS or JS module, in source order, each ONE unit with the value the program sees: a string
 *  literal in either quote or a template without substitutions (kind "string" or "template"); a template with substitutions
 *  as its spans joined with each hole's source text between `${` and `}` kept in place (kind "template"); a `+` chain of
 *  string, template and numeric literals as the value JS computes (kind "string"; a chain's all-literal prefix up to its
 *  first non-literal operand folds, the rest is read operand by operand; an all-numeric chain is a number and no unit); and a
 *  regular expression literal (its source text, slashes and flags included). `'a\'b'`, `"a'b"`, `` `a'b` `` and `"a" + "'b"`
 *  are one value. A literal inside a hole is a unit of its own too. A JSX attribute's quoted value (`<a title="x\n">`) has no
 *  escapes and is read as written, as the compiler reads it; the text between JSX tags (`<p>the words</p>`) is one unit as
 *  written (kind "jsxtext"), a whitespace-only text no unit. */
export function literals(source: string, file = "source.ts"): Unit[] {
  return literalsIn(ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, scriptKind(file)), file);
}

function literalsIn(sf: ts.SourceFile, file: string): Unit[] {
  const out: Unit[] = [];
  const lineOf = (pos: number): number => sf.getLineAndCharacterOfPosition(pos).line + 1;
  const lineStarts = sf.getLineStarts();
  /** The starts map off the source offsets: a start wherever the offsets cross into a later source line (they never go back:
   *  the operands, the spans and the holes come in source order). */
  const push = (kind: UnitKind, piece: Piece, pos: number, end: number): void => {
    const line = lineOf(pos);
    const starts = [{ line, at: 0 }];
    let j = line - 1;   // the 0-based line of the last offset seen
    for (let i = 0; i < piece.src.length; i++) {
      const o = piece.src[i];
      let moved = false;
      while (j + 1 < lineStarts.length && lineStarts[j + 1] <= o) { j++; moved = true; }
      if (moved) starts.push({ line: j + 1, at: i });
    }
    out.push({ kind, text: piece.text, pos, end, line, endLine: lineOf(end), starts });
  };
  const visit = (n: ts.Node): void => {
    if (ts.isRegularExpressionLiteral(n)) { push("regex", verbatim(sf.text, n.getStart(sf), n.end), n.getStart(sf), n.end); return; }
    if (ts.isJsxText(n)) { if (!/^\s*$/.test(n.text)) push("jsxtext", verbatim(sf.text, n.pos, n.end), n.pos, n.end); return; }
    if (isToken(n) || ts.isTemplateExpression(n) || (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.PlusToken)) {
      const f = fold(n, sf, file);
      if (f) {
        if (typeof f.value === "string") push(ts.isTemplateExpression(n) || ts.isNoSubstitutionTemplateLiteral(n) ? "template" : "string", f.piece!, n.getStart(sf), n.end);
        for (const h of f.holes) visit(h);
        return;
      }
    }
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out;
}

/** Every comment of a TS or JS module as text: a `//` comment with its marker stripped, consecutive line comments (nothing
 *  but whitespace between them, and no blank line, which ends a run as it ends a paragraph) joined into one unit with single
 *  spaces, and a block comment with its opening and closing
 *  markers and each line's leading `*` stripped and its lines joined the same way. The literal TOKENS are blanked before the
 *  scan (a quote or a slash inside a string is not a comment's start), from the parser's own spans, in one pass; a comment
 *  between two operands of a chain is not blanked and is a unit of its own. */
export function comments(source: string, file = "source.ts"): Unit[] {
  return commentsIn(ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, scriptKind(file)), file);
}

function commentsIn(sf: ts.SourceFile, _file: string): Unit[] {
  const source = sf.text;
  const parts: string[] = [];
  let at = 0;
  for (const t of tokenSpans(sf)) {
    if (t.pos < at) continue;
    parts.push(source.slice(at, t.pos), source.slice(t.pos, t.end).replace(/[^\n\r\u2028\u2029]/g, " "));
    at = t.end;
  }
  parts.push(source.slice(at));
  const blanked = parts.join("");
  const lineOf = (pos: number): number => sf.getLineAndCharacterOfPosition(pos).line + 1;
  const sc = ts.createScanner(ts.ScriptTarget.Latest, false, ts.LanguageVariant.Standard, blanked);
  const out: Unit[] = [];
  let run: { b: Builder; pos: number; end: number; line: number; endLine: number } | null = null;   // the open run of line comments
  let sinceRun = "";   // the source between the run's last comment and the token being read
  const closeRun = (): void => {
    if (run) out.push({ kind: "comment", text: run.b.text, pos: run.pos, end: run.end, line: run.line, endLine: run.endLine, starts: run.b.starts });
    run = null; sinceRun = "";
  };
  for (let k = sc.scan(); k !== ts.SyntaxKind.EndOfFileToken; k = sc.scan()) {
    const pos = sc.getTokenStart();
    const end = sc.getTokenEnd();
    const raw = source.slice(pos, end);
    if (k === ts.SyntaxKind.SingleLineCommentTrivia) {
      const piece = raw.replace(/^\/\/ ?/, "");
      if (run && /^\s*$/.test(sinceRun) && (sinceRun.match(/\n/g) || []).length <= 1) { run.b.add(lineOf(pos), piece); run.end = end; run.endLine = lineOf(pos); sinceRun = ""; }
      else { closeRun(); const b = new Builder(); b.add(lineOf(pos), piece); run = { b, pos, end, line: lineOf(pos), endLine: lineOf(pos) }; }
      continue;
    }
    if (k === ts.SyntaxKind.MultiLineCommentTrivia) {
      closeRun();
      const b = new Builder();
      const line = lineOf(pos);
      raw.replace(/^\/\*+/, "").replace(/\*+\/$/, "").split("\n").forEach((l, i) => { b.add(line + i, l.replace(/^\s*\*+ ?/, "")); });
      out.push({ kind: "comment", text: b.text, pos, end, line, endLine: lineOf(end), starts: b.starts });
      continue;
    }
    if (run) sinceRun += raw;
  }
  closeRun();
  return out;
}

/** The comments and the literals of a TS or JS module, in source order, from one parse. */
export function scriptUnits(source: string, file = "source.ts"): Unit[] {
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, scriptKind(file));
  return [...commentsIn(sf, file), ...literalsIn(sf, file)].sort((a, b) => a.pos - b.pos);
}

// ── Python and prose ───────────────────────────────────────────────────────────────────────────────

/** A Python source line by line with its string literals cooked as Python cooks them (the header lists the escapes), adjacent
 *  literals glued with nothing between them, an f-string's fields kept as written, a raw literal as written and a `#` comment
 *  as written; the second element of a line says the line continues the line before it with nothing between (a continuation
 *  inside a literal, or a literal adjacent to one that closed on the line before). */
export function pythonLines(source: string): { text: string; glue: boolean }[] {
  const lines = source.split("\n");
  const out: { text: string; glue: boolean }[] = lines.map(() => ({ text: "", glue: false }));
  type Lit = { quote: string; raw: boolean; f: boolean };
  let lit: Lit | null = null;
  // a literal that closed with nothing but whitespace (or a continuation) since: its closing quote and that whitespace are held
  // back until the next token says whether another literal follows (glued: neither quote is written) or not (written as they were)
  let pending: { line: number; text: string } | null = null;
  const ident = (c: string | undefined): boolean => c !== undefined && /[A-Za-z0-9_]/.test(c);
  const cooked = (s: string): string => (s.length === 1 && s.charCodeAt(0) < 0x20 ? " " : s);
  for (let li = 0; li < lines.length; li++) {
    const l = lines[li];
    let i = 0;
    const emit = (s: string): void => { out[li].text += s; };
    const flushPending = (): void => {
      if (!pending) return;
      out[pending.line].text += pending.text;
      if (pending.line !== li) out[li].glue = false;
      pending = null;
    };
    while (i < l.length) {
      const c = l[i];
      if (lit) {
        if (l.startsWith(lit.quote, i)) { pending = { line: li, text: lit.quote }; i += lit.quote.length; lit = null; continue; }
        if (c === "\\" && lit.raw) { emit("\\" + (l[i + 1] ?? "")); i += l[i + 1] === undefined ? 1 : 2; continue; }
        if (c === "\\") {
          const nx = l[i + 1];
          if (nx === undefined || (nx === "\r" && i + 2 === l.length)) { i = l.length; if (li + 1 < lines.length) out[li + 1].glue = true; continue; }
          if (nx === "x" && isHex(l[i + 2]) && isHex(l[i + 3])) { emit(cooked(String.fromCharCode(parseInt(l.slice(i + 2, i + 4), 16)))); i += 4; continue; }
          if (nx === "u" && /^[0-9a-fA-F]{4}$/.test(l.slice(i + 2, i + 6))) { emit(cooked(String.fromCharCode(parseInt(l.slice(i + 2, i + 6), 16)))); i += 6; continue; }
          if (nx === "U" && /^[0-9a-fA-F]{8}$/.test(l.slice(i + 2, i + 10)) && parseInt(l.slice(i + 2, i + 10), 16) <= 0x10ffff) { emit(cooked(String.fromCodePoint(parseInt(l.slice(i + 2, i + 10), 16)))); i += 10; continue; }
          if (isOct(nx)) { let j = i + 2; while (j < i + 4 && isOct(l[j])) j++; emit(cooked(String.fromCharCode(parseInt(l.slice(i + 1, j), 8) & 0xff))); i = j; continue; }
          const simple: Record<string, string> = { n: " ", t: " ", r: " ", a: " ", b: " ", f: " ", v: " ", "'": "'", '"': '"', "\\": "\\" };
          if (simple[nx] !== undefined) { emit(simple[nx]); i += 2; continue; }
          emit("\\" + nx); i += 2; continue;   // an unknown escape (\N{...} among them) is kept as written
        }
        if (lit.f && (c === "{" || c === "}") && l[i + 1] === c) { emit(c); i += 2; continue; }
        emit(cooked(c)); i += 1; continue;
      }
      // outside a literal
      if (c === "#") { flushPending(); emit(l.slice(i)); i = l.length; continue; }
      const m = /^([rRbBuUfF]{0,2})('''|"""|'|")/.exec(l.slice(i));
      if (m && (m[1] === "" || !ident(l[i - 1]))) {
        const prefix = m[1].toLowerCase();
        if (pending) pending = null;   // glued: neither the held quote nor this opening is written
        else emit(l.slice(i, i + m[0].length));
        lit = { quote: m[2], raw: prefix.includes("r"), f: prefix.includes("f") };
        i += m[0].length; continue;
      }
      if (/\s/.test(c) || (c === "\\" && i + 1 === l.length)) { if (pending) pending.text += c; else emit(c); i += 1; continue; }
      flushPending();
      emit(c); i += 1;
    }
    if (pending && li + 1 < lines.length) out[li + 1].glue = true;   // a literal may follow on the next line
    if (lit && lit.quote.length === 1 && li + 1 < lines.length && !out[li + 1].glue) lit = null;   // a one-quote literal ends with its line (recovery)
  }
  if (pending) out[pending.line].text += pending.text;
  return out;
}

/** A prose file's paragraphs (runs of lines separated by a blank line), each one unit with its hard wraps collapsed. With
 *  `python` the lines are read through pythonLines first (the string literals cooked as Python cooks them, adjacent literals
 *  glued); Markdown is read as it stands. */
export function proseUnits(source: string, python = false): Unit[] {
  const out: Unit[] = [];
  const raw = source.split("\n");
  const lines = python ? pythonLines(source) : raw.map((text) => ({ text, glue: false }));
  let b: Builder | null = null;
  let start = -1;
  let pos = 0;
  let startPos = 0;
  const flush = (endIdx: number, endPos: number): void => {
    if (!b) return;
    out.push({ kind: "prose", text: b.text, pos: startPos, end: endPos, line: start + 1, endLine: endIdx, starts: b.starts });
    b = null; start = -1;
  };
  lines.forEach((l, i) => {
    if (l.text.trim() === "") flush(i, pos);
    else { if (!b) { b = new Builder(); start = i; startPos = pos; } b.add(i + 1, l.text, l.glue); }
    pos += raw[i].length + 1;
  });
  flush(lines.length, source.length);
  return out;
}

/** The suffixes the compiler reads (each with its script kind) and the suffixes read as prose, paragraphs as they stand; a
 *  file with no suffix (a Makefile, a LICENSE, a bare dotfile such as .gitignore) is text of no language and is read as
 *  prose too. Any other suffix is REFUSED by name (the file review's round 5, correctness-7 with tests-4 and extra7-2: .tsx,
 *  .jsx and .cts had fallen through to the prose arm with no word to the caller, the spelling-blind read the round-4 reader
 *  replaced; a guard refuses what it cannot read rather than read it as something else). */
export const SCRIPT_SUFFIXES = [".ts", ".mts", ".cts", ".tsx", ".js", ".mjs", ".cjs", ".jsx"];
export const PROSE_SUFFIXES = [".md", ".css", ".yml", ".yaml", ".json", ".html", ".sh", ".bash", ".bats", ".txt", ".toml", ".csv", ".tsv", ".svg", ".xml", ".patch", ".mmd", ".ini", ".cfg"];
/** The suffix `unitsOf` routes on: the text from the basename's last dot, or "" for a basename with no dot after its first
 *  character (a bare dotfile is a name, not a suffix). */
export function suffixOf(file: string): string {
  const base = file.slice(file.lastIndexOf("/") + 1);
  const dot = base.lastIndexOf(".");
  return dot > 0 ? base.slice(dot) : "";
}
/** The units of a file by its suffix: the compiler's for a script suffix (SCRIPT_SUFFIXES, each with its script kind);
 *  paragraphs with Python's string rules for .py; paragraphs as they stand for a prose suffix (PROSE_SUFFIXES) or no suffix;
 *  a throw naming the file for any other suffix, the caller's to add to the reader with its reading rule. */
export function unitsOf(file: string, source: string): Unit[] {
  const suffix = suffixOf(file);
  if (SCRIPT_SUFFIXES.includes(suffix)) return scriptUnits(source, file);
  if (suffix === ".py") return proseUnits(source, true);
  if (suffix === "" || PROSE_SUFFIXES.includes(suffix)) return proseUnits(source);
  throw new Error("source-units: " + file + " has the suffix " + JSON.stringify(suffix) + ", which the reader has no rule for (scripts: " + SCRIPT_SUFFIXES.join(" ") + "; Python: .py; prose: " + PROSE_SUFFIXES.join(" ") + ", or no suffix); it refuses rather than read the file as prose, so add the suffix to the reader with its rule (a guard that reads the whole tree reaches every file that names its vocabulary, so a new fixture of an unlisted suffix that does so blocks that guard's job until its suffix is added here)");
}
/** Whether `unitsOf` has a rule for the file's suffix (the same three arms), for a tree-wide caller to count the population's
 *  files of no known suffix before one of them names the vocabulary and trips the refusal. */
export function readable(file: string): boolean {
  const suffix = suffixOf(file);
  return suffix === "" || suffix === ".py" || SCRIPT_SUFFIXES.includes(suffix) || PROSE_SUFFIXES.includes(suffix);
}

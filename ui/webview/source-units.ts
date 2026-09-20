/** A source read as its language reads it, for the pins of the link-navigation follow-on (plans/markdown-viewer.md,
 *  "Follow-on: Link navigation (2026-09-19)"). The file review's round 4 ruled one rule over three guards (regression-2 with
 *  extra6-1, tests-2, and the review-name pin under rules-1): a guard against a FORM is keyed on the property or it parses;
 *  each of the three had been keyed on one spelling and claimed more than it checked (the refused-state pins on the
 *  double-quoted literal, blind to a single-quoted comparison; the attribution pin on one apostrophe, blind to the escaped one
 *  inside a JS string). So the TypeScript compiler's parser reads a TS or JS module here: its STRING LITERALS with the value the
 *  program sees (either quote, a template span, every escape resolved), its regular expression literals, and its COMMENTS as
 *  text with the markers stripped and a run of line comments joined, so a sentence wrapped over two comment lines is one
 *  unit. Markdown and Python, which the compiler does not read, are read as paragraphs with backslash escapes folded, and a
 *  caller's message says so. Every unit maps an offset of its text back to the source line it came from (lineAt), so a
 *  reader can judge a phrase with its whole unit as context and still charge it to the line that carries it (the attribution
 *  pin's second road reads the lines the branch added, inside the units they sit in). The two readers:
 *  file-view-figure-shapes.test.ts (the refused states' literals) and linknav-records-attribution.test.ts (the rounds the
 *  records name).
 *  Node-only: the tests import it; the webview bundle never does. */
import * as ts from "typescript";

export type UnitKind = "comment" | "string" | "template" | "regex" | "prose";
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

const scriptKind = (file: string): ts.ScriptKind => (/\.(?:m?js|cjs)$/.test(file) ? ts.ScriptKind.JS : ts.ScriptKind.TS);

/** A unit built line by line: each piece is trimmed, its inner whitespace collapsed, and appended after one space; a piece
 *  that is empty adds nothing and no start. */
class Builder {
  text = "";
  starts: { line: number; at: number }[] = [];
  add(line: number, piece: string): void {
    const t = piece.replace(/\s+/g, " ").trim();
    if (!t) return;
    if (this.text) this.text += " ";
    this.starts.push({ line, at: this.text.length });
    this.text += t;
  }
}

/** Every string-like literal of a TS or JS module, in source order: a string literal in either quote, a template literal
 *  (a substituting one as its head, middle and tail spans, each the cooked text of that span) and a regular expression
 *  literal (its source text, slashes and flags included). The value is the program's: `'a\'b'`, `"a'b"` and `` `a'b` `` are
 *  one value. */
export function literals(source: string, file = "source.ts"): Unit[] {
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, true, scriptKind(file));
  const out: Unit[] = [];
  const add = (n: ts.Node, kind: UnitKind, text: string): void => {
    const pos = n.getStart(sf);
    const line = sf.getLineAndCharacterOfPosition(pos).line + 1;
    const starts = [{ line, at: 0 }];
    for (let i = text.indexOf("\n"); i >= 0; i = text.indexOf("\n", i + 1)) starts.push({ line: line + starts.length, at: i + 1 });
    out.push({ kind, text, pos, end: n.end, line, endLine: sf.getLineAndCharacterOfPosition(n.end).line + 1, starts });
  };
  const visit = (n: ts.Node): void => {
    if (ts.isStringLiteral(n)) add(n, "string", n.text);
    else if (ts.isNoSubstitutionTemplateLiteral(n) || ts.isTemplateHead(n) || ts.isTemplateMiddle(n) || ts.isTemplateTail(n)) add(n, "template", n.text);
    else if (ts.isRegularExpressionLiteral(n)) add(n, "regex", n.text);
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out;
}

/** Every comment of a TS or JS module as text: a `//` comment with its marker stripped, consecutive line comments (nothing
 *  but whitespace between them, and no blank line, which ends a run as it ends a paragraph) joined into one unit with single
 *  spaces, and a block comment with its opening and closing
 *  markers and each line's leading `*` stripped and its lines joined the same way. The literals are blanked before the scan (a
 *  quote or a slash inside a string is not a comment's start), from the parser's own spans. */
export function comments(source: string, file = "source.ts"): Unit[] {
  let blanked = source;
  for (const l of literals(source, file)) blanked = blanked.slice(0, l.pos) + blanked.slice(l.pos, l.end).replace(/[^\n]/g, " ") + blanked.slice(l.end);
  const sf = ts.createSourceFile(file, source, ts.ScriptTarget.Latest, false, scriptKind(file));
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

/** The comments and the literals of a TS or JS module, in source order. */
export function scriptUnits(source: string, file = "source.ts"): Unit[] {
  return [...comments(source, file), ...literals(source, file)].sort((a, b) => a.pos - b.pos);
}

/** A prose file's paragraphs (runs of lines separated by a blank line), each one unit with its hard wraps collapsed. With
 *  `foldEscapes` a backslash before any character is dropped, for a Python module, whose string escapes the compiler here
 *  does not read (`\'` is `'`); Markdown is read as it stands. */
export function proseUnits(source: string, foldEscapes = false): Unit[] {
  const out: Unit[] = [];
  const lines = source.split("\n");
  let b: Builder | null = null;
  let start = -1;
  let pos = 0;
  let startPos = 0;
  const flush = (endIdx: number, endPos: number): void => {
    if (!b) return;
    const text = foldEscapes ? b.text.replace(/\\(.)/g, "$1") : b.text;
    // folding shortens the text before an offset by the escapes before it, so the starts are re-read off the folded text
    const starts = foldEscapes ? b.starts.map((s) => ({ line: s.line, at: b!.text.slice(0, s.at).replace(/\\(.)/g, "$1").length })) : b.starts;
    out.push({ kind: "prose", text, pos: startPos, end: endPos, line: start + 1, endLine: endIdx, starts });
    b = null; start = -1;
  };
  lines.forEach((l, i) => {
    if (l.trim() === "") flush(i, pos);
    else { if (!b) { b = new Builder(); start = i; startPos = pos; } b.add(i + 1, l); }
    pos += l.length + 1;
  });
  flush(lines.length, source.length);
  return out;
}

/** The units of a file by its suffix: the compiler's for .ts, .mts, .js, .mjs and .cjs; paragraphs with escapes folded for
 *  .py; paragraphs as they stand for anything else (.md, .css). */
export function unitsOf(file: string, source: string): Unit[] {
  if (/\.(?:m?ts|m?js|cjs)$/.test(file)) return scriptUnits(source, file);
  return proseUnits(source, /\.py$/.test(file));
}

// The comment stripper the source pins read through (file-view-seam.test.ts's inertness premise guard and its re-parse
// population, md-url-view.test.ts's and md-sanitize-viewer-links.test.ts's order pins over mdBlock), so a pin reads code
// and a comment quoting the pinned lines cannot satisfy it. The comments are the TypeScript compiler's own comment
// ranges: the source is parsed (ts.createSourceFile), every token of the tree is visited, and the comment ranges the
// scanner reports before each token (ts.getLeadingCommentRanges at the token's full start) and after it on the same line
// (ts.getTrailingCommentRanges at its end) are the ranges removed, and nothing else is. A string, a template and a regex
// literal are single tokens to the parser, so a `//` inside a string (the HTML namespace URL), a `/*` inside a template,
// a regex literal ending in backslash-slash, and a comment opener inside any of them are code and stay; a regex inside a
// block comment is comment and goes. The scanner alone cannot do this: whether a `/` opens a regex or divides is decided
// by the parser's context, which is why the tree is walked and not the token stream.
// Why a parser and not a pattern (the fork PR review's round 1, finding fresh-1, and the ruling's amendment, 2026-09-20): the
// hand scanner these tests carried before read a string's quotes and the two comment openers and nothing else, and on
// ui/webview/settings.ts's `new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(s) ? s : "http://" + s).hostname.toLowerCase()` it
// took the regex literal's closing `\//` as a line comment and deleted the rest of the line, `hostname.toLowerCase()`
// included (measured 2026-09-20 by running that scanner over the module at the head the round's ruling was answered from: the
// call present in the source, absent after the strip; the minimal case `const x = /a:\/\//i.test(s) ? s : "http://" + s; const y = keep();` stripped to
// `const x = /a:\/\`). A sibling PR's regex stripper the same night opened a block comment on the string "image/*" and
// swallowed 149 lines. A pattern mis-parses whichever construct nobody thought of next; the compiler knows where every
// comment is. The self-check in file-view-seam.test.ts ("codeOnly reads the compiler's comment ranges") runs this over an
// affected module (settings.ts keeps hostname.toLowerCase()), over md-sanitize.ts (a string holding `//` kept, the doc
// comments' word gone) and over a synthetic module holding each construct above.
// Node-only: the tests import it (the test build keeps `typescript` a runtime require, esbuild.js testBuild); no bundle does.
// Synthetic values only.
import * as ts from "typescript";

/** The kind of source: TypeScript (the dashboard's modules) or JavaScript (an installed library's dist). */
export type CodeKind = "ts" | "js";

/** `src` with every comment removed, by the compiler's comment ranges, and nothing else changed: the newlines a comment
 *  spanned are kept, so line numbers survive and a multi-line block comment leaves blank lines where it stood; every
 *  string, template and regex literal is intact. */
export function stripComments(src: string, kind: CodeKind = "ts"): string {
  const sf = ts.createSourceFile("code-only." + kind, src, ts.ScriptTarget.Latest, true, kind === "js" ? ts.ScriptKind.JS : ts.ScriptKind.TS);
  const ranges: Array<[number, number]> = [];
  const add = (found: ts.CommentRange[] | undefined): void => { if (found) for (const r of found) ranges.push([r.pos, r.end]); };
  // every token of the tree, through the syntax-list children the compiler synthesizes between a node's named children: a
  // comment sits before some token (leading, at that token's full start) or after one on its line (trailing, at its end).
  // A JSDoc node's children are positions INSIDE a comment, so the walk does not descend into one: a scan started inside
  // `/** see http://x */ code` would read `//x */ code` as a line comment and take the code with it.
  const walk = (node: ts.Node): void => {
    for (const child of node.getChildren(sf)) {
      add(ts.getLeadingCommentRanges(src, child.getFullStart()));
      add(ts.getTrailingCommentRanges(src, child.getEnd()));
      if (child.kind >= ts.SyntaxKind.FirstJSDocNode && child.kind <= ts.SyntaxKind.LastJSDocNode) continue;
      if (child.kind >= ts.SyntaxKind.FirstNode) walk(child);
    }
  };
  add(ts.getLeadingCommentRanges(src, 0));
  walk(sf);
  ranges.sort((a, b) => a[0] - b[0]);
  let out = "", at = 0;
  for (const [pos, end] of ranges) {
    if (end <= at) continue;                       // a range already covered (the same comment reached from two tokens)
    const from = Math.max(pos, at);
    out += src.slice(at, from) + src.slice(from, end).replace(/[^\n]/g, "");
    at = end;
  }
  return out + src.slice(at);
}

/** One parse per distinct source: the seam test strips file-view.ts several times in one run. */
const cache = new Map<string, string>();
/** The form the source pins read: stripComments, then each line's trailing whitespace trimmed and blank lines dropped (a
 *  stripped comment's line goes, so a pin's `\n`-anchored match and its line lists read statements alone). */
export function codeOnly(src: string, kind: CodeKind = "ts"): string {
  const key = kind + "\u0000" + src;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;
  const out = stripComments(src, kind).split("\n").map((l) => l.trimEnd()).filter((l) => l !== "").join("\n");
  cache.set(key, out);
  return out;
}

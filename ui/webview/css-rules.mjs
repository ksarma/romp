// A sheet's rules read as RULES, not as lines: each style rule's selector list, its declarations and the chain of at-rules
// enclosing it, found by matching braces over the sheet's text with its comments stripped. One reader for the two homes of
// the figure control's screen-only guard, ui/webview/file-figure-open.test.ts and tools/markdown-viewer-plan-linknav.test.mjs
// (the file review's round 10, correctness-1 with tests-1 and ui-1: both homes had keyed the closed set over the control's
// rules on LINES at column zero carrying the class and a brace, so a rule written the way the sheets already write them, an
// indented rule inside an at-rule block or a grouped selector wrapped across lines, was outside the population the set
// closed). A plain module with no dependency, so CI's Shell job, which runs tools/*.test.mjs with no npm ci, loads it as the
// webview test bundle does (esbuild bundles it into the .ts test; ui/webview/css-rules.d.mts types it for the typecheck). It
// lives under ui/, the tree the bundles read, since a ui test may not import from tools/, hooks/ or tests/: the kernel's
// bundle-staleness inputs read ui/, vendor/ and vscode-extension/ alone, and tests/test_lab_dist.py derives the trees the
// bundles' imports reach, the test bundles' among them, from the exported esbuild configs and holds them to those three (the
// author's closing pass after the file review's round 10, which moved the reader from tools/, where that pin had been red).
//
// What the reader refuses, loudly, rather than classifies, in eight refusals, each armed by an assert.throws in the tools home
// (tools/markdown-viewer-plan-linknav.test.mjs, the reader's test, which holds this count to the source's refusal sites and
// holds each site to one pin by the phrase its message opens with; the ui home holds no refusal pin, by design): a comment
// left open, a string left open, a block left open at the end of the sheet, a close brace with no block open, a close brace
// inside a prelude (a lost `{`), a prelude the sheet ends inside, a
// block opened inside a style rule's declarations (CSS nesting, which the sheets do not use; a reader with no rule for a
// form names it) and a style rule left open (the file review's round 11, extra7-1: three of the eight had no pin, the open
// string among them, so neutralising any one left both homes green). A statement at-rule (`@import ...;`, `@charset ...;`)
// declares no rule and is passed over. A block at-rule whose body holds declarations and no rules (`@font-face` and the
// others DECLARATION_AT_RULE names) yields no rule, its last declaration with or without a semicolon (the file review's
// round 11, correctness-2 with extra7-2: the reader had refused the no-semicolon spelling, valid CSS one edit away in the
// tree's own `@font-face` blocks, as a close brace inside a prelude, an unbalanced-brace message on a balanced sheet). The
// one read that acceptance leaves silent: inside a declaration-only at-rule a selector-shaped prelude ended by `}`
// (`@font-face { .a top: 0 }`) is read as a declaration and yields no rule, with no refusal. `@keyframes` steps (`from`,
// `to`, `50%`) are rules under their at-rule, as the text has them. Whitespace inside a selector, a body or an at-rule
// prelude is collapsed to one space and trimmed, so a rule renders the same however the sheet wrapped it.
//
// The reader returns every rule; each home chooses its population by the SELECTOR, the rules naming the control's class,
// over every sheet a page of either host loads (ui/webview/host-sheets.mjs derives that set from the page assembly; the file
// review's round 11, correctness-1 with regression-5). A rule whose selector would match the control's element without naming
// the class (`.fileview-md img + button`, an attribute selector, a universal) is outside what the homes close, a bound they
// state rather than read, since reading it means matching selectors against the element (the author's closing pass after the
// file review's round 10, mechanism-2), as are katex's vendored sheet and the style a template or a script writes into a page,
// the sheet bounds host-sheets.mjs names.

/** The sheet with every block comment removed. A comment opener inside a string is read as a comment: the sheets carry
 *  none, and a reader that honoured quotes at this level would have to parse every string in the sheet to find it. */
export function stripCssComments(css) {
  let out = '';
  for (let i = 0; i < css.length;) {
    if (css.startsWith('/*', i)) {
      const end = css.indexOf('*/', i + 2);
      if (end < 0) throw new Error('css-rules: a comment opened at offset ' + i + ' never closes');
      i = end + 2;
    } else out += css[i++];
  }
  return out;
}

const squeeze = (s) => s.replace(/\s+/g, ' ').trim();
/** The block at-rules whose body holds declarations and no rules, so their last declaration may end at the block's `}` with no
 *  semicolon (valid CSS, and the spelling every minifier writes): `@font-face`, `@page` and its sixteen margin at-rules,
 *  `@property`, `@counter-style`, `@font-palette-values`. Keyed by NAME, never by depth alone: a `}` ending a prelude under any
 *  other at-rule, or at the top level, is a lost `{` and stays refused (a break on any `}` at depth zero would read
 *  `@media screen { .a top: 0 }` as a declaration and return no rule, silently, where the reader refuses it). */
const DECLARATION_AT_RULE = /^@(?:font-face|page|(?:top|bottom)-(?:center|(?:left|right)(?:-corner)?)|(?:left|right)-(?:top|middle|bottom)|property|counter-style|font-palette-values)(?![\w-])/;

/** Every style rule of the sheet, in sheet order: `{ selector, body, chain }`, the selector list and the body squeezed to
 *  single spaces, `chain` the preludes of the at-rules enclosing the rule from the outermost in (`[]` at the top level). */
export function cssRules(css) {
  const text = stripCssComments(css);
  const rules = [];
  let i = 0;
  const fail = (why) => { throw new Error('css-rules: ' + why + ' (offset ' + i + ' of the comment-stripped sheet)'); };
  /** Advance past a quoted string opened at `i`. */
  const skipString = () => {
    const q = text[i];
    for (i++; i < text.length; i++) {
      if (text[i] === '\\') { i++; continue; }
      if (text[i] === q) { i++; return; }
    }
    fail('a string opened with ' + q + ' never closes');
  };
  /** A block's contents until its closing brace (consumed), the chain of at-rules around it. */
  const block = (chain) => {
    for (;;) {
      while (i < text.length && /\s/.test(text[i])) i++;
      if (i >= text.length) { if (chain.length) fail('a block under ' + chain.join(' > ') + ' never closes'); return; }
      if (text[i] === '}') { if (!chain.length) fail('a close brace with no block open'); i++; return; }
      // the prelude: up to `{` (a block) or a `;` outside parentheses (a statement)
      const start = i;
      let depth = 0;
      for (; i < text.length; i++) {
        const c = text[i];
        if (c === '"' || c === "'") { skipString(); i--; continue; }
        if (c === '(') depth++;
        else if (c === ')') depth--;
        else if (c === '{') break;
        else if (c === ';' && depth === 0) break;
        else if (c === '}') {
          // the last declaration of a declaration-only at-rule, ended by the block's own brace: left for the block to close on
          if (depth === 0 && chain.length && DECLARATION_AT_RULE.test(chain[chain.length - 1])) break;
          fail('a close brace inside a prelude: ' + JSON.stringify(text.slice(start, i + 1)));
        }
      }
      if (i >= text.length) fail('a prelude never reaches a brace or a semicolon: ' + JSON.stringify(text.slice(start, start + 80)));
      const prelude = squeeze(text.slice(start, i));
      if (text[i] === ';') { i++; continue; }                 // a statement at-rule (or a stray declaration): no rule
      if (text[i] === '}') continue;                          // the block's own brace after a final declaration: the loop closes on it
      i++;                                                    // past `{`
      if (prelude.startsWith('@')) { block([...chain, prelude]); continue; }
      // a style rule: its declarations to the matching `}`; a nested block is a form this reader has no rule for
      const bodyStart = i;
      for (; i < text.length; i++) {
        const c = text[i];
        if (c === '"' || c === "'") { skipString(); i--; continue; }
        if (c === '{') fail('a block opened inside the declarations of ' + JSON.stringify(prelude) + ' (CSS nesting), which this reader does not read');
        if (c === '}') break;
      }
      if (i >= text.length) fail('the rule ' + JSON.stringify(prelude) + ' never closes');
      rules.push({ selector: prelude, body: squeeze(text.slice(bodyStart, i)), chain: [...chain] });
      i++;                                                    // past `}`
    }
  };
  block([]);
  return rules;
}

/** A rule on one line, the way the sheets write a one-line rule: `@media screen { .a, .b { opacity: 1; } }`. */
export function renderRule(rule) {
  return rule.chain.map((c) => c + ' { ').join('') + rule.selector + ' { ' + rule.body + ' }' + ' }'.repeat(rule.chain.length);
}

/** The media queries of an `@media` prelude, split at the commas outside parentheses. */
const mediaQueries = (prelude) => {
  const out = []; let depth = 0, from = 0;
  const list = prelude.replace(/^@media\s*/, '');
  for (let k = 0; k < list.length; k++) {
    if (list[k] === '(') depth++;
    else if (list[k] === ')') depth--;
    else if (list[k] === ',' && depth === 0) { out.push(list.slice(from, k).trim()); from = k + 1; }
  }
  out.push(list.slice(from).trim());
  return out;
};
const SCREEN_QUERY = /^(?:only\s+)?screen(?:\s+and\s+\((?:[^()]|\([^()]*\))*\))*$/;

/** Does a chain of at-rule preludes confine a rule to screens: some `@media` among them whose every query is `screen`, or
 *  `screen and (...)` with any number of features (`only screen` too)? A query list with any other member (`print`, a bare
 *  feature such as `(min-width: 1px)`, `not screen`, `all`) confines nothing to screens, and a chain with no `@media` is
 *  every medium. */
export function underScreen(chain) {
  return chain.some((p) => /^@media\b/.test(p) && mediaQueries(p).every((q) => SCREEN_QUERY.test(q)));
}

// Every stylesheet a page of either host loads, DERIVED from the page assembly rather than typed as a pair or listed off a
// directory: the population of the closed set over the figure control's sheet rules (ui/webview/file-figure-open.test.ts and
// tools/markdown-viewer-plan-linknav.test.mjs) and of the Outline button's census (ui/webview/fileview-parity.test.ts,
// ui/webview/file-view-outline.test.ts). The file review's round 10, correctness-1 with regression-5 and correctness-5: the set
// was closed over styles.css and feed.css while the Files page loads ui/webview/files-pane.css third, after styles.css, so a
// reveal planted there left every home green and the control painting in print; and a flat listing of ui/webview is a wider
// typed bound, not the population, since the kernel inlines three blocks of its own that no listing of the directory reads: two
// constants the pages name (THEME_CSS, into every page that takes no arguments, and the chat's _CHAT_MOBILE_CSS, string constants
// of kernel/kernel.py) and the style block the pane spinner helper writes into the served HTML of the chat, feed, sessions and
// waiting pages (_pane_spin, carrying _LOADER_CSS; the file review's round 11, kernel-1 with extra6-1, extra7-1 and tests-1:
// the block had stood outside the read with every pin green, excused by this header as one a helper adds after the page is
// served, which is false, since the kernel writes it into the response body).
//
// The derivation, each part read off the tree's own source so a change to the assembly moves the population:
//   * the kernel's served pages are the `def _<name>_page(...)` functions of kernel/kernel.py whose `)` closes on `:` at the end
//     of the def's line, whatever their parameters (a signature wrapped across lines included: the chat, the feed, the sessions
//     pane, the waiting pane, the Files pane, the settings page and the timeline, and the chat's history page and the too-large
//     notice, which take arguments and load no sheet today; a read keyed on an empty signature had left those two outside the
//     derivation with no failure to name it), and a page def at column zero in any other shape (a return annotation, a `)`
//     inside a default, a trailing comment after the colon, an async def) fails by name, since a page the read drops would take
//     its sheets out of the population silently (the file review's round 11, correctness-1 with regression-1 and extra7-2: the
//     annotated and the `)`-in-default shapes had left the read with no failure, and the header had said every page was read
//     whatever its parameters); each with the function's own text, the lines up to the first statement at column zero outside a
//     triple-quoted literal (a column-zero line inside one is the template's own text, so a constant the page names after it is
//     read; the body had ended at that line whether or not a literal was open), its comment lines dropped so a sheet a comment
//     mentions is not read as one the page loads; from each: every `/dist/<name>.css` it
//     links, a bundle vscode-extension/esbuild.js builds from ui/webview/<name>.css (the entry list is read and a link with no
//     entry fails); every `(UI / "webview" / "<name>.css").read_text()` it writes into a `<style>`; and every module-level
//     `<NAME>_CSS` constant it names, whose text is read from kernel.py by its assignment (a triple-quoted literal, or a
//     parenthesised run of double-quoted literals with comment lines between them, decoded as Python decodes them);
//   * the helpers a page body calls are followed one level: for each `_<name>(` in the body whose `def _<name>(...)` writes a
//     `<style>`, the run of literals from `"<style>` to `</style>"` and every `<NAME>_CSS` constant it concatenates are read into
//     the page's sheets under `kernel/kernel.py _<name>`, in served order, and a run this reader cannot decode fails by name
//     (the pane spinner's block, `_pane_spin` with _LOADER_CSS folded in, on the chat, feed, sessions and waiting pages; the
//     file review's round 11, extra6-1 with extra7-1, kernel-1 and tests-1: the block was served with the page and outside the
//     read, so a reveal planted in _LOADER_CSS or in the helper's own literal left every home green);
//   * the VS Code host's webviews are built in vscode-extension/src/extension.ts, and every `Uri.joinPath(extUri, "dist",
//     "<name>.css")` there is a link to the same bundle;
//   * every other `.css` a page body or the extension names must be one of those (a link from anywhere else fails loudly rather
//     than falling outside the read), and every `.css` under ui/webview must be loaded by some page (a sheet no page loads by a
//     form this reader knows fails naming the sheet, so the listing, the wider bound, is covered and never silently exceeded).
// Outside the read, a bound the homes state and do not read: katex's vendored sheet (`@import "katex/dist/katex.min.css"` in
// styles.css and feed.css, inlined into the bundles by esbuild; third-party, under node_modules, outside the tree), the rules a
// template writes into its own HTML (the settings page's transparent background, the too-large notice's body rule, the
// extension's zoom rule), the style element a script creates after the page is served (palette.ts's and shortcuts-modal.ts's
// elements, the shim's notices set through style.cssText), and the landing shell (`_landing`, not a page function: its boot
// splash and notice blocks inline _LOADER_CSS, _STALE_CSS, _UPD_CSS and _RDRIFT_CSS, and the panes it frames are documents of
// their own).
// A plain module with no dependency beyond node's fs and path, imported by the .ts tests through the webview test bundle
// (ui/webview/host-sheets.d.mts types it) and by tools/*.test.mjs directly; it lives under ui/ for the reason
// ui/webview/css-rules.mjs states in its header.
import * as fs from 'node:fs';
import * as path from 'node:path';

const fail = (why) => { throw new Error('host-sheets: ' + why); };

/** A module-level string constant of kernel.py by name, as Python reads it: `NAME = """..."""` (taken raw, and a backslash in
 *  it fails, since this reader decodes no escape in that form) or `NAME = (` followed by lines each holding one double-quoted
 *  literal with an optional trailing comment, blank and comment lines between, closed by a `)` at column zero or by a `)` at the
 *  end of the last literal's line (kernel.py writes five of its six parenthesised runs the second way, _LOADER_CSS among them,
 *  and the reader had failed on every one of them; the file review's round 11, extra6-1 with extra7-1), any other line failing
 *  by name and a run that never closes failing too. */
export function pyStringConstant(src, name) {
  const at = src.indexOf('\n' + name + ' = ');
  if (at < 0) fail(name + ' is not assigned at column zero of kernel.py');
  const start = at + 1 + name.length + 3;
  if (src.startsWith('"""', start)) {
    const end = src.indexOf('"""', start + 3);
    if (end < 0) fail(name + "'s triple-quoted literal never closes");
    const text = src.slice(start + 3, end);
    if (text.includes('\\')) fail(name + "'s triple-quoted literal carries a backslash escape this reader does not decode");
    return text;
  }
  if (src[start] === '(') {
    let out = '';
    for (const line of src.slice(start + 1).split('\n')) {
      const t = line.trim();
      if (t === '' || t.startsWith('#')) continue;
      if (/^\)\s*(?:#.*)?$/.test(line)) return out;                                   // a lone `)` at column zero
      const lit = /^("(?:[^"\\]|\\.)*")\s*(\))?\s*(?:#.*)?$/.exec(t);
      if (!lit) fail(name + ' holds a line this reader has no rule for: ' + JSON.stringify(t.slice(0, 60)));
      out += JSON.parse(lit[1].replace(/\\'/g, "'"));
      if (lit[2]) return out;                                                          // `)` on the last literal's line
    }
    fail(name + "'s parenthesised run never closes");
  }
  fail(name + ' is assigned in a form this reader has no rule for (a triple-quoted literal or a parenthesised run)');
}

/** The lines of a function's body after its def head, `from` the index of the first line after it: indented, blank and
 *  column-zero comment lines, and any line while a triple-quoted literal is open (an odd count of `"""` or of `'''` so far, each
 *  delimiter counted on its own over the lines that are not comments, so a `"""` inside a `'''` literal or inside a one-line
 *  string would miscount, shapes no page body has), up to the first column-zero non-comment line outside a literal. Comment lines
 *  are dropped, except inside a literal, where a line opening with `#` is the template's own text (the file review's round 11,
 *  correctness-1: the body had ended at the first column-zero line whether or not a literal was open, so a constant a page named
 *  after a column-zero template line was not read, with no failure). */
function defBody(lines, from) {
  const body = [];
  let dq = 0, sq = 0;
  for (let i = from; i < lines.length; i++) {
    const l = lines[i], inside = dq % 2 === 1 || sq % 2 === 1;
    if (!inside && l !== '' && !/^[ \t#]/.test(l)) break;
    if (inside || !/^\s*#/.test(l)) {
      body.push(l);
      dq += (l.match(/"""/g) ?? []).length; sq += (l.match(/'''/g) ?? []).length;
    }
  }
  return body.join('\n') + '\n';
}

/** The kernel's served pages: each `def _<name>_page(...)` whose `)` closes on `:` at the end of its line, whatever its
 *  parameters (a signature wrapped across lines included, and the pages that take arguments, the chat's history page and the
 *  too-large notice: a page read only when its signature is empty would leave a sheet inlined by a page with parameters outside
 *  the population, silently), with the function's own text (defBody: the indented, blank and comment lines after the def, and
 *  every line while a triple-quoted literal is open, up to the next statement at column zero outside one), its comment lines
 *  dropped. After the read, every `def _<name>_page` at column zero, `async def` included, is counted against the pages read, and
 *  a page def in any other shape (a return annotation, a `)` inside a default, a trailing comment after the colon, an async def)
 *  fails by name, since a page the read drops would take its sheets out of the population silently (the file review's round 11,
 *  correctness-1 with regression-1 and extra7-2). */
export function kernelPages(kernel) {
  const out = [];
  const lines = kernel.split('\n');
  const head = /^def (_\w+_page)\([^)]*\):\n/gm;
  let m;
  while ((m = head.exec(kernel))) {
    const from = kernel.slice(0, m.index + m[0].length).split('\n').length - 1;
    out.push({ name: m[1], body: defBody(lines, from) });
  }
  const loose = kernel.match(/^(?:async )?def (_\w+_page)\b[^\n]*/gm) ?? [];
  const seen = new Set(out.map((p) => p.name));
  const missed = loose.filter((l) => !seen.has(/^(?:async )?def (_\w+_page)\b/.exec(l)[1]));
  if (missed.length || loose.length !== out.length) fail('a page function this reader has no rule for (its `)` does not close on `:` at the end of the def line, or it is an async def), so a sheet it loads would be outside the population: ' + (missed.length ? missed : loose).map((l) => JSON.stringify(l)).join(', '));
  if (!out.length) fail('kernel.py declares no `def _<name>_page(...)` function');
  return out;
}

const LINK = /\/dist\/([\w-]+)\.css\b/g;                                   // a linked bundle
const LIVE = /\(UI \/ "webview" \/ "([\w-]+\.css)"\)\.read_text\(\)/g;    // a sheet read live into a <style>
const INLINE = /\b(_?[A-Z][A-Z0-9_]*_CSS)\b/g;                            // a module-level constant inlined into a <style>
const HELPER = /(?<![.\w])(_[a-z]\w*)\(/g;                                 // a module-level helper a page body calls
const JOIN = /Uri\.joinPath\(extUri, "dist", "([\w-]+)\.css"\)/g;         // the extension's link to a bundle
const ANY_CSS = /([\w-]+)\.css\b/g;                                        // every sheet a text names, by base name
const all = (re, text) => { const out = []; let m; re.lastIndex = 0; while ((m = re.exec(text))) out.push(m[1]); return out; };

/** The `<style>` block a helper writes into the HTML it returns, or null when its text writes none: the run from the literal
 *  opening `"<style>` to the literal closing `</style>"`, each double-quoted literal decoded and each `<NAME>_CSS` constant it
 *  concatenates read by pyStringConstant, in the order the served HTML has them; a helper with no def in the strict shape, a
 *  `<style` outside such a run, any other token in the run and a run that does not decode to one block fail by name (the file
 *  review's round 11, extra6-1 with extra7-1, kernel-1 and tests-1: the pane spinner's block, `_pane_spin`'s with _LOADER_CSS
 *  folded in, served with the chat, feed, sessions and waiting pages, had been outside the read with every pin green). */
function helperStyle(kernel, lines, name) {
  const head = new RegExp('^def ' + name + '\\([^)]*\\):\\n', 'm').exec(kernel);
  if (!head) fail(name + ' is called by a page body and is no module-level def this reader has a rule for');
  const text = defBody(lines, kernel.slice(0, head.index + head[0].length).split('\n').length - 1);
  if (!text.includes('<style')) return null;
  const open = text.indexOf('"<style>'), close = text.indexOf('</style>"');
  if (open < 0 || close < 0 || close < open) fail(name + ' writes a <style> in a form this reader has no rule for (not a run of literals from "<style> to </style>")');
  const run = text.slice(open, close + '</style>"'.length);
  let out = '';
  const tok = /\s+|("(?:[^"\\]|\\.)*")|\+|\b(_?[A-Z][A-Z0-9_]*_CSS)\b|#[^\n]*/y;
  for (let i = 0; i < run.length;) {
    tok.lastIndex = i;
    const m = tok.exec(run);
    if (!m) fail(name + "'s <style> run holds a token this reader has no rule for: " + JSON.stringify(run.slice(i, i + 40)));
    if (m[1]) out += JSON.parse(m[1].replace(/\\'/g, "'"));
    else if (m[2]) out += pyStringConstant(kernel, m[2]);
    i = tok.lastIndex;
  }
  if (!out.startsWith('<style>') || !out.endsWith('</style>')) fail(name + "'s <style> run did not decode to one <style> block");
  return out.slice('<style>'.length, -'</style>'.length);
}

/** Every sheet a page of either host loads, sorted by name: `{ name, css, loadedBy }`, `name` the sheet's path in the tree
 *  (`ui/webview/<file>.css`), `kernel/kernel.py <NAME>` for a kernel constant, or `kernel/kernel.py _<helper>` for the block a
 *  helper the page calls writes into its HTML; `loadedBy` the pages that load it. */
export function hostSheets(root) {
  const read = (...p) => fs.readFileSync(path.join(root, ...p), 'utf8');
  const kernel = read('kernel', 'kernel.py');
  const lines = kernel.split('\n');
  const esbuild = read('vscode-extension', 'esbuild.js');
  const extension = read('vscode-extension', 'src', 'extension.ts').split('\n').filter((l) => !/^\s*\/\//.test(l)).join('\n');
  const sheets = new Map();
  const add = (name, css, page) => {
    const s = sheets.get(name) ?? { name, css, loadedBy: [] };
    s.loadedBy.push(page);
    sheets.set(name, s);
  };
  const bundle = (name, page) => {
    if (!esbuild.includes('"../ui/webview/' + name + '.css"')) fail(page + ' links /dist/' + name + '.css, which vscode-extension/esbuild.js builds from no sheet under ui/webview');
    add('ui/webview/' + name + '.css', read('ui', 'webview', name + '.css'), page);
  };
  /** Every `.css` the text names is one the derivation read for that page, or the read has a hole to name. */
  const complete = (text, page, names) => {
    for (const base of new Set(all(ANY_CSS, text))) {
      if (!names.has(base + '.css')) fail(page + ' names ' + base + '.css in a form this derivation does not read (a link outside /dist, a read outside ui/webview)');
    }
  };
  const helperCss = new Map();
  for (const { name: page, body } of kernelPages(kernel)) {
    const names = new Set();
    for (const n of all(LINK, body)) { bundle(n, page); names.add(n + '.css'); }
    for (const f of all(LIVE, body)) { add('ui/webview/' + f, read('ui', 'webview', f), page); names.add(f); }
    for (const c of all(INLINE, body)) add('kernel/kernel.py ' + c, pyStringConstant(kernel, c), page);
    // the helpers the body calls, followed one level: a helper whose def writes a <style> is a sheet of every page that calls it
    for (const h of new Set(all(HELPER, body))) {
      if (/_page$/.test(h)) continue;
      if (!helperCss.has(h)) helperCss.set(h, helperStyle(kernel, lines, h));
      if (helperCss.get(h) !== null) add('kernel/kernel.py ' + h, helperCss.get(h), page);
    }
    complete(body, 'kernel/kernel.py ' + page, names);
  }
  const ext = 'vscode-extension/src/extension.ts';
  const extNames = new Set();
  for (const n of all(JOIN, extension)) { bundle(n, ext); extNames.add(n + '.css'); }
  complete(extension, ext, extNames);
  for (const f of fs.readdirSync(path.join(root, 'ui', 'webview')).filter((f) => f.endsWith('.css')).sort()) {
    if (!sheets.has('ui/webview/' + f)) fail('ui/webview/' + f + ' is a sheet no page of either host loads by a form this derivation reads: a new host or a new way of loading a sheet, to be added here, or a sheet nothing loads');
  }
  return [...sheets.values()].sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0)).map((s) => ({ ...s, loadedBy: [...new Set(s.loadedBy)].sort() }));
}

// Every stylesheet a page of either host loads, DERIVED from the page assembly rather than typed as a pair or listed off a
// directory: the population of the closed set over the figure control's sheet rules (ui/webview/file-figure-open.test.ts and
// tools/markdown-viewer-plan-linknav.test.mjs) and of the Outline button's census (ui/webview/fileview-parity.test.ts,
// ui/webview/file-view-outline.test.ts). The file review's round 10, correctness-1 with regression-5 and correctness-5: the set
// was closed over styles.css and feed.css while the Files page loads ui/webview/files-pane.css third, after styles.css, so a
// reveal planted there left every home green and the control painting in print; and a flat listing of ui/webview is a wider
// typed bound, not the population, since the kernel inlines two sheets of its own into every page (THEME_CSS and the chat's
// _CHAT_MOBILE_CSS, string constants of kernel/kernel.py) that no listing of the directory reads.
//
// The derivation, each part read off the tree's own source so a change to the assembly moves the population:
//   * the kernel's served pages are the `def _<name>_page():` functions of kernel/kernel.py (the chat, the feed, the sessions
//     pane, the waiting pane, the Files pane, the settings page, the timeline), each with the function's own text, its comment
//     lines dropped so a sheet a comment mentions is not read as one the page loads; from each: every `/dist/<name>.css` it
//     links, a bundle vscode-extension/esbuild.js builds from ui/webview/<name>.css (the entry list is read and a link with no
//     entry fails); every `(UI / "webview" / "<name>.css").read_text()` it writes into a `<style>`; and every module-level
//     `<NAME>_CSS` constant it names, whose text is read from kernel.py by its assignment (a triple-quoted literal, or a
//     parenthesised run of double-quoted literals with comment lines between them, decoded as Python decodes them);
//   * the VS Code host's webviews are built in vscode-extension/src/extension.ts, and every `Uri.joinPath(extUri, "dist",
//     "<name>.css")` there is a link to the same bundle;
//   * every other `.css` a page body or the extension names must be one of those (a link from anywhere else fails loudly rather
//     than falling outside the read), and every `.css` under ui/webview must be loaded by some page (a sheet no page loads by a
//     form this reader knows fails naming the sheet, so the listing, the wider bound, is covered and never silently exceeded).
// Outside the read, a bound the homes state and do not read: katex's vendored sheet (`@import "katex/dist/katex.min.css"` in
// styles.css and feed.css, inlined into the bundles by esbuild; third-party, under node_modules, outside the tree), the style
// a template writes into its own HTML (the settings page's transparent background, the extension's zoom rule) or a helper or
// a script adds after the page is served (the pane spinner's block, the shim's notices), and the landing shell (`_landing`,
// not a page function: it links no sheet, and the panes it frames are documents of their own).
// A plain module with no dependency beyond node's fs and path, imported by the .ts tests through the webview test bundle
// (ui/webview/host-sheets.d.mts types it) and by tools/*.test.mjs directly; it lives under ui/ for the reason
// ui/webview/css-rules.mjs states in its header.
import * as fs from 'node:fs';
import * as path from 'node:path';

const fail = (why) => { throw new Error('host-sheets: ' + why); };

/** A module-level string constant of kernel.py by name, as Python reads it: `NAME = """..."""` (taken raw, and a backslash in
 *  it fails, since this reader decodes no escape in that form) or `NAME = (` followed by lines each holding one double-quoted
 *  literal with an optional trailing comment, blank and comment lines between, up to a `)` at column zero. */
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
    const end = src.indexOf('\n)', start);
    if (end < 0) fail(name + "'s parenthesised run never closes");
    let out = '';
    for (const line of src.slice(start + 1, end).split('\n')) {
      const t = line.trim();
      if (t === '' || t.startsWith('#')) continue;
      const lit = /^("(?:[^"\\]|\\.)*")\s*(?:#.*)?$/.exec(t);
      if (!lit) fail(name + ' holds a line this reader has no rule for: ' + JSON.stringify(t.slice(0, 60)));
      out += JSON.parse(lit[1].replace(/\\'/g, "'"));
    }
    return out;
  }
  fail(name + ' is assigned in a form this reader has no rule for (a triple-quoted literal or a parenthesised run)');
}

/** The kernel's served pages: each `def _<name>_page():` with the function's own text (the indented, blank and comment lines
 *  after the def, up to the next statement at column zero), its comment lines dropped. */
export function kernelPages(kernel) {
  const out = [];
  const re = /^def (_\w+_page)\(\):\n((?:(?:[ \t]+[^\n]*|#[^\n]*)?\n)*)/gm;
  let m;
  while ((m = re.exec(kernel))) out.push({ name: m[1], body: m[2].split('\n').filter((l) => !/^\s*#/.test(l)).join('\n') });
  if (!out.length) fail('kernel.py declares no `def _<name>_page():` function');
  return out;
}

const LINK = /\/dist\/([\w-]+)\.css\b/g;                                   // a linked bundle
const LIVE = /\(UI \/ "webview" \/ "([\w-]+\.css)"\)\.read_text\(\)/g;    // a sheet read live into a <style>
const INLINE = /\b(_?[A-Z][A-Z0-9_]*_CSS)\b/g;                            // a module-level constant inlined into a <style>
const JOIN = /Uri\.joinPath\(extUri, "dist", "([\w-]+)\.css"\)/g;         // the extension's link to a bundle
const ANY_CSS = /([\w-]+)\.css\b/g;                                        // every sheet a text names, by base name
const all = (re, text) => { const out = []; let m; re.lastIndex = 0; while ((m = re.exec(text))) out.push(m[1]); return out; };

/** Every sheet a page of either host loads, sorted by name: `{ name, css, loadedBy }`, `name` the sheet's path in the tree
 *  (`ui/webview/<file>.css`) or, for a kernel constant, `kernel/kernel.py <NAME>`, `loadedBy` the pages that load it. */
export function hostSheets(root) {
  const read = (...p) => fs.readFileSync(path.join(root, ...p), 'utf8');
  const kernel = read('kernel', 'kernel.py');
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
  for (const { name: page, body } of kernelPages(kernel)) {
    const names = new Set();
    for (const n of all(LINK, body)) { bundle(n, page); names.add(n + '.css'); }
    for (const f of all(LIVE, body)) { add('ui/webview/' + f, read('ui', 'webview', f), page); names.add(f); }
    for (const c of all(INLINE, body)) add('kernel/kernel.py ' + c, pyStringConstant(kernel, c), page);
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

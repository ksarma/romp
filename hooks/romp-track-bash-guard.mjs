#!/usr/bin/env node
// romp-track-bash-guard.mjs, a PreToolUse hook on the Bash tool: refuse a shell command that would
// write a TRACKED file (plans/file-review.md, decision 47).
//
// The vendored guard (vendor/track-changents/hooks/track-guard.mjs) denies a raw Write / Edit /
// MultiEdit on a tracked file and points the session at track-edit. It never sees a write made
// through the Bash tool, and a session in auto mode is told to make its file changes that way: cp
// and mv over the file, tee, a heredoc redirected into it, sed -i, a python or node one-liner. A
// dry run (2026-09-09) saw a session run track-config and cp in one compound command on a tracked
// file; the flag printed on and the cp landed raw, with no change recorded for the person to accept
// or reject. This hook closes that path.
//
// It reads the command, extracts the paths the command would write (extractWriteTargets below
// states the grammar), resolves them against the session's working directory (the payload's cwd;
// a `cd` earlier in the command moves it, and a `cd` inside a subshell moves it only up to the
// closing parenthesis, as in the shell), and refuses (exit 2, the reason on stderr) when one of
// them is a tracked text file of its project, per that project's .trackchanges/config.json, read
// through the same store-io the CLIs and the vendored guard use. A path is judged under its own
// name and under the name the kernel would open (symlinks resolved), so a link to a tracked file
// does not carry a write past it. A read-only command (cat, grep, diff, git) names no write target
// and passes. A command the extraction cannot see through (paths built from variables, eval,
// xargs) passes too: never a silent block of ordinary work. Like the vendored guard it lets a
// non-text file through (an image or a PDF cannot take a tracked edit, so the raw write is the
// only way to regenerate a figure), and it exits 0 at once, before stdin is read, when ROMP_SID is
// absent from its environment (decision 24: registered machine-wide, inert in every session romp
// did not launch).
//
// Cost: a couple of small reads of config.json per target and, when the project's tracked list is
// non-empty and a target is not on it by name, ONE walk of the project's markdown tree per call
// (store-io's link closure, the same walk the vendored guard pays once per Write), however many
// files the command lands: a directory copy of hundreds of files must not pay the walk once per
// file, or the call outruns the installer's 10 s hook timeout and the harness runs the command
// unjudged. A glob operand costs a listing of the directories it names; a directory source costs a
// listing of the source tree (less than the copy itself pays), skipped when the landing directory
// does not exist yet under any project that tracks anything.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { findVaultRoot, isTrackedFile, isNonTextPath, hasNulBytes } from '../vendor/track-changents/store-io.mjs';
import { relPathFor, trackedPaths as readTrackedPaths, untrackedPaths as readUntrackedPaths, trackedClosure } from '../vendor/track-changents/store-io.mjs';
import engine from '../vendor/track-changents/engine.js';

// ── lexer ───────────────────────────────────────────────────────────
//
// A command is cut into simple commands ("segments") at |, ||, &&, ;, &, newline, ( and ). Each
// segment is a list of words and a list of redirections, and `op` names the operator that ended
// it, so a later pass can tell a pipeline from a list. A `(` or `)` is also emitted as a marker
// segment (`paren`) so the scope of a subshell is known: a `cd` inside one moves nothing after the
// `)`. A word keeps the text the shell would see after quote removal, `marks` ('u' at each
// character that was unquoted, 'q' otherwise) so a later pass can tell a glob character from a
// quoted one, and two flags: `literal`, false once the word carries anything the shell would
// expand that the hook cannot ($VAR, ${...}, $(...), backticks, ~user, a process substitution), and
// `glob`, true for a word whose only expansion is an unquoted `*`, `?` or `[...]`, which
// extractWriteTargets expands against the filesystem the way the shell would. Brace expansion
// happens here, as in the shell before every other expansion: an unquoted `{a,b}` or `{1..3}`
// makes one word per alternative (`mv report.md{.new,}` names two operands), and a redirection
// target that expands to several words is the shell's ambiguous redirect, which writes nothing.
// A leading ~/ is expanded to the home directory, as the shell would. A heredoc body
// (<<EOF ... EOF) and a here-string (<<< word) are data, not commands: kept on the segment whose
// command opened them (not the one current when the line ends, which after
// `python3 - <<EOF && echo done` is the echo) for the python, node and shell stdin scans, and
// never lexed as shell. `>(cmd)` and `<(cmd)` are process substitutions: cmd is read like a
// `$(...)`, and the word stands for a /dev/fd path the hook cannot resolve. Inside `[[ ... ]]`
// (the unquoted keyword, in command position) a `>` or `<` compares and redirects nothing, and
// `&&`, `||`, `(` and `)` are the test's own operators; `(( ... ))` is arithmetic. `opaque` is set
// when the command is more than the lexer can follow: an unterminated quote, or eval, xargs or a
// shell -c with a script it cannot read.

const WRITE_REDIRECTS = new Set(['>', '>>', '>|', '&>', '&>>', '>&', '<>']);
const SHELLS = new Set(['sh', 'bash', 'zsh', 'dash', 'ksh']);
const PREFIXES = new Set(['sudo', 'command', 'builtin', 'exec', 'nice', 'nohup', 'time', 'env', 'timeout', 'ionice', 'stdbuf']);
const RESERVED = new Set(['do', 'then', 'else', 'elif', 'if', 'while', 'until', '!', '{', '}']);

function word(text, literal, raw, extra) {
  return { text, literal, raw, glob: !!(extra && extra.glob), marks: extra && extra.marks != null ? extra.marks : null };
}

// Whether `text` has an unquoted glob character, per `marks`.
function hasGlobChar(text, marks) {
  for (let i = 0; i < text.length; i++) if (marks[i] === 'u' && (text[i] === '*' || text[i] === '?' || text[i] === '[')) return true;
  return false;
}

// Brace expansion on a word's text with its marks: the first unquoted `{...}` holding an unquoted
// top-level comma, or a `..` sequence of integers or single letters, makes one alternative per
// member, each carried through the rest of the word (so `a{b,c}{d,e}` gives four), nested braces
// included; a `{` with no `}`, or `{x}` with neither, is text. Returns [text, marks] pairs, or
// null past BRACE_CAP alternatives (a word the hook then cannot resolve).
const BRACE_CAP = 512;
function braceSequence(inner) {
  let m = inner.match(/^(-?\d+)\.\.(-?\d+)(?:\.\.(-?\d+))?$/);
  if (m) {
    const a = parseInt(m[1], 10);
    const b = parseInt(m[2], 10);
    const step = (m[3] != null && Math.abs(parseInt(m[3], 10))) || 1;
    if (Math.abs(b - a) / step + 1 > BRACE_CAP) return null;
    const pad = /^-?0\d/.test(m[1]) || /^-?0\d/.test(m[2]) ? Math.max(m[1].replace('-', '').length, m[2].replace('-', '').length) : 0;
    const out = [];
    for (let v = a; a <= b ? v <= b : v >= b; v += a <= b ? step : -step) out.push((v < 0 ? '-' : '') + String(Math.abs(v)).padStart(pad, '0'));
    return out;
  }
  m = inner.match(/^([A-Za-z])\.\.([A-Za-z])(?:\.\.(-?\d+))?$/);
  if (m) {
    const a = m[1].charCodeAt(0);
    const b = m[2].charCodeAt(0);
    const step = (m[3] != null && Math.abs(parseInt(m[3], 10))) || 1;
    const out = [];
    for (let v = a; a <= b ? v <= b : v >= b; v += a <= b ? step : -step) out.push(String.fromCharCode(v));
    return out;
  }
  return undefined;
}
function braceExpand(text, marks) {
  for (let i = 0; i < text.length; i++) {
    if (text[i] !== '{' || marks[i] !== 'u') continue;
    let depth = 0;
    let close = -1;
    const commas = [];
    for (let j = i; j < text.length; j++) {
      if (marks[j] !== 'u') continue;
      if (text[j] === '{') depth++;
      else if (text[j] === '}') { if (--depth === 0) { close = j; break; } }
      else if (text[j] === ',' && depth === 1) commas.push(j);
    }
    if (close < 0) break;   // no closing brace: the text stands
    let alts;
    if (commas.length) {
      alts = [];
      let from = i + 1;
      for (const c of [...commas, close]) { alts.push([text.slice(from, c), marks.slice(from, c)]); from = c + 1; }
    } else {
      const seq = braceSequence(text.slice(i + 1, close));
      if (seq === undefined) continue;   // {x}: text; a later brace may still expand
      if (seq === null) return null;
      alts = seq.map((s) => [s, 'u'.repeat(s.length)]);
    }
    const out = [];
    for (const [t, m] of alts) {
      const rest = braceExpand(t + text.slice(close + 1), m + marks.slice(close + 1));
      if (!rest) return null;
      for (const [rt, rm] of rest) {
        out.push([text.slice(0, i) + rt, marks.slice(0, i) + rm]);
        if (out.length > BRACE_CAP) return null;
      }
    }
    return out;
  }
  return [[text, marks]];
}

const newSegment = () => ({ words: [], redirects: [], heredocs: [], subs: [], op: '' });

export function lex(command) {
  const src = String(command);
  const segments = [];
  let seg = newSegment();
  let buf = '';
  let raw = '';
  let marks = '';
  let sawExpansion = false;   // the word carries an expansion the hook cannot resolve
  let inWord = false;
  let opaque = false;
  let inTest = false;   // inside [[ ... ]], where > and < compare strings
  // what the next word is: a redirect target, a heredoc delimiter, a here-string, or data (<)
  let expect = null;
  const pendingHeredocs = [];
  let i = 0;

  const mk = (t, m) => {
    const g = !sawExpansion && hasGlobChar(t, m);
    return word(t, !sawExpansion && !g, raw, { glob: g, marks: m });
  };
  const endWord = () => {
    if (!inWord) return;
    if (expect) {
      if (expect.kind === 'target') {
        // a target that brace-expands to several words is an ambiguous redirect: the shell writes nothing
        const alts = braceExpand(buf, marks);
        seg.redirects.push({ op: expect.op, target: alts && alts.length === 1 ? mk(alts[0][0], alts[0][1]) : word(buf, false, raw) });
      } else if (expect.kind === 'heredoc') pendingHeredocs.push({ delim: buf, stripTabs: expect.stripTabs, owner: seg });
      else if (expect.kind === 'herestring') seg.heredocs.push(buf);
      expect = null;
    } else {
      // the keyword: unquoted, in command position (first in its segment, or after a reserved word)
      if (raw === '[[' && (!seg.words.length || RESERVED.has(seg.words[seg.words.length - 1].text))) inTest = true;
      else if (raw === ']]') inTest = false;
      const alts = braceExpand(buf, marks);
      if (!alts) seg.words.push(word(buf, false, raw));
      else for (const [t, m] of alts) seg.words.push(mk(t, m));
    }
    buf = ''; raw = ''; marks = ''; sawExpansion = false; inWord = false;
  };
  // A word of the test's own grammar (`>` or `&&` inside [[ ... ]]): ends any word under way, stands alone.
  const bareWord = (t) => { endWord(); inWord = true; buf = t; raw = t; marks = 'u'.repeat(t.length); endWord(); };
  const endSegment = (op) => {
    endWord();
    if (expect) expect = null;   // a redirect with no target: leave it
    inTest = false;
    seg.op = op;
    if (seg.words.length || seg.redirects.length || seg.heredocs.length || seg.subs.length) segments.push(seg);
    seg = newSegment();
  };
  // After a newline, the bodies of every heredoc opened on the line just ended, each on the
  // segment that opened it (already pushed by reference when an operator ended it on that line).
  const readHeredocBodies = () => {
    while (pendingHeredocs.length) {
      const { delim, stripTabs, owner } = pendingHeredocs.shift();
      const lines = [];
      for (;;) {
        if (i >= src.length) break;
        let j = src.indexOf('\n', i);
        if (j < 0) j = src.length;
        const line = src.slice(i, j);
        i = Math.min(j + 1, src.length);
        const cmp = stripTabs ? line.replace(/^\t+/, '') : line;
        if (cmp === delim) break;
        lines.push(line);
      }
      owner.heredocs.push(lines.join('\n'));
    }
  };
  // (( ... )): arithmetic, no command and no redirection in it; skip to the matching )).
  const skipArithmetic = () => {
    let depth = 2;
    while (i < src.length && depth > 0) {
      if (src[i] === '(') depth++;
      else if (src[i] === ')') depth--;
      i++;
    }
    if (depth > 0) opaque = true;
  };
  // Skip a $( ... ) or ${ ... } from just after its opener to its closer, quotes honoured;
  // returns the inner text. The word carrying it is not literal.
  const skipNested = (open, close) => {
    let depth = 1;
    const start = i;
    while (i < src.length && depth > 0) {
      const c = src[i];
      if (c === '\\') { i += 2; continue; }
      if (c === "'") { const e = src.indexOf("'", i + 1); i = e < 0 ? src.length : e + 1; continue; }
      if (c === '"') {
        i++;
        while (i < src.length && src[i] !== '"') { if (src[i] === '\\') i++; i++; }
        i++;
        continue;
      }
      if (c === open) depth++;
      else if (c === close) depth--;
      i++;
    }
    if (depth > 0) opaque = true;
    return src.slice(start, Math.max(start, i - 1));
  };
  // Quoted text, or text from an expansion: never a glob character, never a brace to expand.
  const quoted = (t) => { buf += t; marks += 'q'.repeat(t.length); };

  while (i < src.length) {
    const c = src[i];
    if (c === ' ' || c === '\t') { endWord(); i++; continue; }
    if (c === '\n') {
      endWord();
      i++;
      readHeredocBodies();   // the bodies belong to the line just ended
      endSegment('\n');
      continue;
    }
    if (c === '#' && !inWord) {   // comment to the end of the line
      while (i < src.length && src[i] !== '\n') i++;
      continue;
    }
    if (c === '\\') {
      if (src[i + 1] === '\n') { i += 2; continue; }   // line continuation
      inWord = true; quoted(src[i + 1] == null ? '' : src[i + 1]); raw += src.slice(i, i + 2); i += 2;
      continue;
    }
    if (c === "'") {
      const e = src.indexOf("'", i + 1);
      if (e < 0) { opaque = true; quoted(src.slice(i + 1)); raw += src.slice(i); inWord = true; i = src.length; break; }
      inWord = true; quoted(src.slice(i + 1, e)); raw += src.slice(i, e + 1); i = e + 1;
      continue;
    }
    if (c === '"') {
      inWord = true;
      raw += '"';
      i++;
      let closed = false;
      while (i < src.length) {
        const d = src[i];
        if (d === '"') { closed = true; raw += '"'; i++; break; }
        if (d === '\\' && i + 1 < src.length && '"\\$`\n'.includes(src[i + 1])) {
          if (src[i + 1] !== '\n') quoted(src[i + 1]);
          raw += src.slice(i, i + 2); i += 2; continue;
        }
        if (d === '$' && src[i + 1] === '(') { sawExpansion = true; raw += '$('; i += 2; const inner = skipNested('(', ')'); raw += inner + ')'; seg.subs.push(inner); continue; }
        if (d === '$' || d === '`') sawExpansion = true;
        quoted(d); raw += d; i++;
      }
      if (!closed) opaque = true;
      continue;
    }
    if (c === '`') {
      const e = src.indexOf('`', i + 1);
      inWord = true; sawExpansion = true;
      if (e < 0) { opaque = true; raw += src.slice(i); i = src.length; break; }
      seg.subs.push(src.slice(i + 1, e));
      raw += src.slice(i, e + 1); i = e + 1;
      continue;
    }
    if (c === '$') {
      inWord = true; sawExpansion = true;
      if (src[i + 1] === '(') { raw += '$('; i += 2; const inner = skipNested('(', ')'); raw += inner + ')'; seg.subs.push(inner); continue; }
      if (src[i + 1] === '{') { raw += '${'; i += 2; const inner = skipNested('{', '}'); raw += inner + '}'; quoted('${' + inner + '}'); continue; }
      quoted(c); raw += c; i++;
      continue;
    }
    if (c === '~' && !inWord) {
      const rest = src.slice(i + 1);
      if (rest === '' || /^[\s/;&|)]/.test(rest)) { inWord = true; quoted(os.homedir()); raw += '~'; i++; continue; }
      inWord = true; sawExpansion = true; quoted(c); raw += c; i++;   // ~user: not resolved here
      continue;
    }
    // operators
    if (c === '<' || c === '>' || c === '&' || c === '|' || c === ';' || c === '(' || c === ')') {
      // inside [[ ... ]] a > or < is a string comparison, not a redirection, and &&, ||, ( and ) are the
      // test's own operators: each a word of its own, the segment going on
      if (inTest && (c === '<' || c === '>')) { bareWord(c); i++; continue; }
      if (inTest && ((c === '&' && src[i + 1] === '&') || (c === '|' && src[i + 1] === '|'))) { bareWord(c + c); i += 2; continue; }
      if (inTest && (c === '(' || c === ')')) { bareWord(c); i++; continue; }
      // >(cmd) or <(cmd): a process substitution. cmd runs and is read like a $(...); the word stands
      // for a /dev/fd path the hook cannot resolve, so `tee >(cat) file` still names file.
      if ((c === '>' || c === '<') && src[i + 1] === '(') {
        endWord();
        i += 2;
        const inner = skipNested('(', ')');
        seg.subs.push(inner);
        inWord = true; sawExpansion = true;
        const t = c + '(' + inner + ')';
        quoted(t); raw += t;
        endWord();
        continue;
      }
      // a digits-only word glued to < or > is the descriptor (2>file still writes file): drop it
      if (inWord && /^[0-9]+$/.test(buf) && (c === '<' || c === '>')) { buf = ''; raw = ''; marks = ''; inWord = false; }
      else endWord();
      if (c === '(' && src[i + 1] === '(') { i += 2; skipArithmetic(); continue; }   // (( ... )) compares or counts
      if (c === '>') {
        if (src[i + 1] === '>') { i += 2; expect = { kind: 'target', op: '>>' }; continue; }
        if (src[i + 1] === '|') { i += 2; expect = { kind: 'target', op: '>|' }; continue; }
        if (src[i + 1] === '&') {
          i += 2;
          if (/[0-9-]/.test(src[i] || '')) { while (i < src.length && /[0-9-]/.test(src[i])) i++; continue; }   // dup: 2>&1, >&-
          expect = { kind: 'target', op: '>&' };
          continue;
        }
        i++; expect = { kind: 'target', op: '>' }; continue;
      }
      if (c === '<') {
        if (src[i + 1] === '<' && src[i + 2] === '<') { i += 3; expect = { kind: 'herestring' }; continue; }
        if (src[i + 1] === '<') { const strip = src[i + 2] === '-'; i += strip ? 3 : 2; expect = { kind: 'heredoc', stripTabs: strip }; continue; }
        if (src[i + 1] === '>') { i += 2; expect = { kind: 'target', op: '<>' }; continue; }
        if (src[i + 1] === '&') { i += 2; while (i < src.length && /[0-9-]/.test(src[i])) i++; continue; }
        i++; expect = { kind: 'data' }; continue;
      }
      if (c === '&') {
        if (src[i + 1] === '>') { const app = src[i + 2] === '>'; i += app ? 3 : 2; expect = { kind: 'target', op: app ? '&>>' : '&>' }; continue; }
        if (src[i + 1] === '&') { i += 2; endSegment('&&'); continue; }
        i++; endSegment('&'); continue;
      }
      if (c === '|') { const or = src[i + 1] === '|'; i += or ? 2 : 1; endSegment(or ? '||' : '|'); continue; }
      if (c === ';') { i += src[i + 1] === ';' ? 2 : 1; endSegment(';'); continue; }
      // ( or ): a segment break and a scope marker
      i++; endSegment(c);
      segments.push({ ...newSegment(), paren: c });
      continue;
    }
    inWord = true; buf += c; marks += 'u'; raw += c; i++;
  }
  endSegment('');
  readHeredocBodies();
  if (pendingHeredocs.length) opaque = true;
  return { segments, opaque };
}

// ── pathname expansion ─────────────────────────────────────────────

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&');
const POSIX_CLASSES = {
  alpha: 'a-zA-Z', digit: '0-9', alnum: 'a-zA-Z0-9', upper: 'A-Z', lower: 'a-z', space: '\\s', blank: ' \\t',
  punct: '!-\\/:-@\\[-`{-~', xdigit: '0-9A-Fa-f', cntrl: '\\x00-\\x1f', graph: '!-~', print: ' -~',
};
// A path segment's unquoted glob characters as a RegExp over one name (`*` any run, `?` one
// character, `[...]` a class, `[!...]` or `[^...]` its complement, a `[` with no `]` text), or null
// when the segment has none. As in the shell, a name starting with `.` is matched only by a pattern
// starting with a `.`.
function globRegex(text, marks) {
  let re = '';
  let any = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (marks[i] !== 'u') { re += escapeRe(c); continue; }
    if (c === '*') { any = true; re += '[^/]*'; continue; }
    if (c === '?') { any = true; re += '[^/]'; continue; }
    if (c === '[') {
      let j = i + 1;
      if (text[j] === '!' || text[j] === '^') j++;
      if (text[j] === ']') j++;   // a ] first is a member
      while (j < text.length && text[j] !== ']') j++;
      if (j >= text.length) { re += '\\['; continue; }   // unmatched: text
      any = true;
      let body = text.slice(i + 1, j);
      let neg = false;
      if (body[0] === '!' || body[0] === '^') { neg = true; body = body.slice(1); }
      let cls = '';
      for (let k = 0; k < body.length; k++) {
        const m = body.slice(k).match(/^\[:([a-z]+):\]/);
        if (m && POSIX_CLASSES[m[1]]) { cls += POSIX_CLASSES[m[1]]; k += m[0].length - 1; continue; }
        cls += '\\]^['.includes(body[k]) ? '\\' + body[k] : body[k];
      }
      re += '[' + (neg ? '^' : '') + cls + ']';
      i = j;
      continue;
    }
    re += escapeRe(c);
  }
  if (!any) return null;
  if (text[0] !== '.') re = '(?!\\.)' + re;
  try { return new RegExp('^' + re + '$'); } catch { return null; }
}

// The paths an unquoted glob names, read off the filesystem as the shell would expand it (one
// literal word per match, absolute, in name order; a literal tail after a glob segment must
// exist; a trailing slash keeps only directories). [] when nothing matches (zsh then runs nothing,
// and bash passes the pattern text through as a name, one no session means as a path). null when
// the hook cannot expand it: a relative pattern with the cwd unknown, or more directory entries or
// matches than the caps, a word the caller keeps as unresolvable.
const GLOB_MATCH_CAP = 2000;
const GLOB_READ_CAP = 50000;
function expandGlob(w, cwd) {
  const text = w.text;
  const marks = w.marks || 'u'.repeat(text.length);
  const absolute = path.isAbsolute(text);
  if (!absolute && !cwd) return null;
  let paths = [absolute ? path.parse(text).root : cwd];
  const parts = [];
  for (let s = 0, i = 0; i <= text.length; i++) {
    if (i === text.length || text[i] === '/') { if (i > s) parts.push([text.slice(s, i), marks.slice(s, i)]); s = i + 1; }
  }
  const trailingDir = text.endsWith('/');
  let read = 0;
  let globbed = false;
  for (const [t, m] of parts) {
    const re = globRegex(t, m);
    if (!re) { paths = paths.map((p) => path.join(p, t)); continue; }
    globbed = true;
    const next = [];
    for (const p of paths) {
      let names;
      try { names = fs.readdirSync(p); } catch { continue; }
      read += names.length;
      if (read > GLOB_READ_CAP) return null;
      names.sort();
      for (const n of names) {
        if (!re.test(n)) continue;
        next.push(path.join(p, n));
        if (next.length > GLOB_MATCH_CAP) return null;
      }
    }
    paths = next;
    if (!paths.length) return [];
  }
  if (!globbed) return [word(resolveAgainst(text, cwd), true, w.raw)];
  const out = [];
  for (const p of paths) {
    let isDir = false;
    let exists = true;
    try { isDir = fs.statSync(p).isDirectory(); } catch { try { fs.lstatSync(p); } catch { exists = false; } }   // a dangling link exists
    if (!exists || (trailingDir && !isDir)) continue;
    out.push(word(trailingDir ? p + '/' : p, true, w.raw));
  }
  return out;
}

// ── the grammar: which words a segment would write ─────────────────

// The options of each prefix that take the next word as their operand (`sudo -u USER`, `env -u
// VAR`, `timeout -s KILL 5`, `exec -a NAME`); every other -option is skipped on its own.
const PREFIX_OPERANDS = {
  sudo: new Set(['-u', '--user', '-g', '--group', '-h', '--host', '-p', '--prompt', '-C', '--close-from', '-D', '--chdir', '-r', '--role', '-t', '--type', '-T', '--command-timeout', '-U', '--other-user']),
  env: new Set(['-u', '--unset', '-S', '--split-string']),
  exec: new Set(['-a']),
  timeout: new Set(['-s', '--signal', '-k', '--kill-after']),
  nice: new Set(['-n', '--adjustment']),
  ionice: new Set(['-c', '--class', '-n', '--classdata', '-p', '--pid', '-P', '--pgid', '-u', '--uid']),
  stdbuf: new Set(['-i', '--input', '-o', '--output', '-e', '--error']),
};
const NO_OPERANDS = new Set();

// Words of a segment after the command's prefixes (sudo and its options, env with its options and
// K=V arguments, nice, ...), leading assignments and reserved words. Returns { name, args }, or
// null for an empty segment or one the prefix runs somewhere the hook cannot follow (`env -C DIR`,
// `sudo -D DIR`: the command's relative paths resolve against that directory, not the cwd).
function commandOf(words) {
  let k = 0;
  for (;;) {
    while (k < words.length && RESERVED.has(words[k].text)) k++;
    while (k < words.length && /^[A-Za-z_][A-Za-z0-9_]*=/.test(words[k].raw)) k++;
    if (k >= words.length) return null;
    const name = path.basename(words[k].text);
    if (!PREFIXES.has(name)) return { name, args: words.slice(k + 1) };
    k++;
    const operands = PREFIX_OPERANDS[name] || NO_OPERANDS;
    while (k < words.length) {
      const t = words[k].text;
      if (t === '--') { k++; break; }
      if ((name === 'env' && (t === '-C' || t === '--chdir' || t.startsWith('--chdir=')))
        || (name === 'sudo' && (t === '-D' || t === '--chdir' || t.startsWith('--chdir=')))) return null;
      if (operands.has(t)) { k += 2; continue; }
      if (t.startsWith('-') && t.length > 1) { k++; continue; }
      if (name === 'timeout' && /^[0-9.]+[smhd]?$/.test(t)) { k++; continue; }   // the duration
      break;
    }
  }
}

// Whether a file landing under `dir` (absolute; it need not exist yet) could be tracked. False
// only when the directory does not exist and its nearest existing ancestor sits under no project
// with a non-empty tracked list: nothing can be nested under a directory that is not there, and a
// project whose list is empty tracks nothing. An existing directory may hold a project of its own
// below it, so a copy into one is walked. With TRACKCHANGES_ROOT set every path is judged against
// that root, so nothing is skipped.
function mayHoldTracked(dir) {
  if (process.env.TRACKCHANGES_ROOT) return true;
  let p = dir;
  for (;;) {
    let exists = false;
    try { exists = fs.existsSync(p); } catch { /* unreadable: treat as absent */ }
    if (exists) break;
    const parent = path.dirname(p);
    if (parent === p) return false;
    p = parent;
  }
  if (p === dir) return true;
  const root = findVaultRoot(path.join(p, 'x'));   // findVaultRoot starts at the parent of the path given
  return !!root && trackedPaths(root).length > 0;
}

// The files a copy of `src` lands as when its destination is `dst`: `dst` itself for a file, and
// for a directory source (cp -r, mv of a folder) each file under it at dst/<its path>, never the
// directory itself. The whole source tree is walked (the copy itself reads every file, so the walk
// costs less than the command), except when nothing under the landing directory could be tracked
// (mayHoldTracked). A source the hook cannot read (absent, not literal) is taken as one file.
function landing(src, dst, cwd) {
  if (!src.literal) return [dst];
  const abs = resolveAgainst(src.text, cwd);
  let isDir = false;
  try { isDir = abs != null && fs.statSync(abs).isDirectory(); } catch { /* absent or unreadable: one file */ }
  if (!isDir) return [dst];
  const dstAbs = dst.literal ? resolveAgainst(dst.text, cwd) : null;
  if (!dstAbs) return [dst];   // an unresolvable destination: the caller drops it
  if (!mayHoldTracked(dstAbs)) return [];
  const out = [];
  const stack = [''];
  while (stack.length) {
    const rel = stack.pop();
    let entries;
    try { entries = fs.readdirSync(path.join(abs, rel), { withFileTypes: true }); } catch { continue; }
    for (const e of entries) {
      const r = rel ? path.join(rel, e.name) : e.name;
      if (e.isDirectory()) stack.push(r);   // a symlinked directory is copied as a link: one entry, not descended
      else out.push(word(path.join(dst.text, r), true, dst.raw));
    }
  }
  return out;
}

// cp / mv / install / ln: the last operand is the destination, unless -t DIR names the directory;
// a destination that is an existing directory receives each source under its own name. A glob
// operand is expanded first, as the shell expands it before the command sees its operands.
function copyTargets(args, cwd) {
  const operands = [];
  let targetDir = null;
  let noTargetDir = false;
  for (let k = 0; k < args.length; k++) {
    const a = args[k];
    if (a.text === '--') { operands.push(...args.slice(k + 1)); break; }
    if (a.text === '-t' || a.text === '--target-directory') { targetDir = args[k + 1]; k++; continue; }
    if (a.text.startsWith('--target-directory=')) { targetDir = word(a.text.slice(19), a.literal, a.raw, { glob: a.glob, marks: a.marks && a.marks.slice(19) }); continue; }
    if (a.text === '-T' || a.text === '--no-target-directory') { noTargetDir = true; continue; }
    if (a.text === '-S' || a.text === '--suffix' || a.text === '-m' || a.text === '--mode' || a.text === '-o' || a.text === '--owner'
      || a.text === '-g' || a.text === '--group' || a.text === '-Z' || a.text === '--context') { k++; continue; }
    if (a.text.startsWith('-') && a.text.length > 1) continue;
    operands.push(a);
  }
  const expanded = [];
  for (const o of operands) {
    if (!o.glob) { expanded.push(o); continue; }
    const m = expandGlob(o, cwd);
    if (m) expanded.push(...m);   // no match: no operand (zsh runs nothing; bash names a file the session did not mean)
    else expanded.push(word(o.text, false, o.raw));   // unresolvable: one operand the hook cannot read
  }
  const out = [];
  if (targetDir) {
    if (targetDir.glob) { const m = expandGlob(targetDir, cwd); targetDir = m && m.length === 1 ? m[0] : word(targetDir.text, false, targetDir.raw); }
    if (!targetDir.literal) return out;
    for (const s of expanded) out.push(...landing(s, word(path.join(targetDir.text, path.basename(s.text)), s.literal, s.raw), cwd));
    return out;
  }
  if (expanded.length < 2) return out;
  const dst = expanded[expanded.length - 1];
  if (!dst.literal) return out;
  const resolved = resolveAgainst(dst.text, cwd);
  let isDir = false;
  if (!noTargetDir && resolved) { try { isDir = fs.statSync(resolved).isDirectory(); } catch { isDir = /\/$/.test(dst.text); } }
  if (isDir) {
    for (const s of expanded.slice(0, -1)) out.push(...landing(s, word(path.join(dst.text, path.basename(s.text)), s.literal, s.raw), cwd));
    return out;
  }
  if (expanded.length === 2) return landing(expanded[0], dst, cwd);
  // three or more operands and a destination that is no directory: cp, mv, install and ln each stop
  // with "target is not a directory" and write nothing
  return out;
}

// sed: every file operand when -i / --in-place is given (the script is the first operand unless
// -e or -f supplied it).
function sedTargets(args) {
  let inPlace = false;
  let scriptGiven = false;
  const operands = [];
  for (let k = 0; k < args.length; k++) {
    const a = args[k];
    if (a.text === '--') { operands.push(...args.slice(k + 1)); break; }
    if (a.text === '-e' || a.text === '--expression' || a.text === '-f' || a.text === '--file') { scriptGiven = true; k++; continue; }
    if (a.text === '-l' || a.text === '--line-length') { k++; continue; }
    if (a.text.startsWith('--expression=') || a.text.startsWith('--file=')) { scriptGiven = true; continue; }
    if (a.text === '--in-place' || a.text.startsWith('--in-place=')) { inPlace = true; continue; }
    if (a.text.startsWith('--')) continue;
    if (a.text.startsWith('-') && a.text.length > 1) {
      // a cluster: -ni, -Ei, -i.bak, -ne 's/x/y/' (e and f take the next word as the script)
      const letters = a.text.slice(1);
      let m = letters.match(/^([nrEszu]*)([ief])(.*)$/);
      if (m) {
        if (m[2] === 'i') inPlace = true;
        else { scriptGiven = true; if (m[3] === '') k++; }
      } else if (/i/.test(letters)) inPlace = true;
      continue;
    }
    operands.push(a);
  }
  if (!inPlace) return [];
  return scriptGiven ? operands : operands.slice(1);
}

// perl: every file operand when -i is among its switches (the program is the first operand unless
// -e / -E supplied it).
function perlTargets(args) {
  let inPlace = false;
  let scriptGiven = false;
  const operands = [];
  for (let k = 0; k < args.length; k++) {
    const a = args[k];
    if (a.text === '--') { operands.push(...args.slice(k + 1)); break; }
    if (a.text.startsWith('-') && a.text.length > 1) {
      const letters = a.text.slice(1);
      for (let j = 0; j < letters.length; j++) {
        const ch = letters[j];
        if (ch === 'i') { inPlace = true; break; }              // -i, -i.bak, -pi.bak: the rest is the suffix
        if (ch === 'e' || ch === 'E') { scriptGiven = true; if (j === letters.length - 1) k++; break; }
        if (ch === 'l' || ch === '0') { while (j + 1 < letters.length && /[0-7]/.test(letters[j + 1])) j++; continue; }   // optional octal, the cluster goes on (-lpe)
        if ('MmIxFCdDV'.includes(ch)) break;                     // switches that eat the rest of the word
      }
      continue;
    }
    operands.push(a);
  }
  if (!inPlace) return [];
  return scriptGiven ? operands : operands.slice(1);
}

// Paths a python or node script opens for writing, read off its text. Only a literal path with a
// write mode counts: open('x', 'w'), open('x', mode='a'), open('x', encoding='utf8', mode='w'),
// open(mode='w', file='x'), Path('x').open('w'), Path('x').write_text(...), shutil.copy(src, 'x');
// fs.writeFileSync('x', ...), appendFile, createWriteStream, openSync('x', 'w'), copyFile(src, 'x'),
// rename(src, 'x'). A call's arguments may span lines, as a formatter wraps them in a heredoc
// script. A path that is a template or an f-string with an expression is not literal and is
// skipped, as is a call whose arguments the scan cannot read (a nested call).
const PY_OPEN = /\b(?:io\.)?open\(([^()]*)\)/g;
const PY_PATH_OPEN = /\bPath\(\s*(['"])([^'"\n]+)\1\s*\)\s*\.open\(([^()]*)\)/g;
const PY_PATH_WRITE = /\bPath\(\s*(['"])([^'"\n]+)\1\s*\)\s*\.write_(?:text|bytes)\(/g;
const PY_SHUTIL = /\bshutil\.(?:copy|copyfile|copy2|move)\(\s*[^,()\n]+,\s*(['"])([^'"\n]+)\1/g;
const NODE_WRITE = /\b(?:writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream|truncate|truncateSync)\(\s*(['"`])([^'"`\n$]+)\1/g;
const NODE_OPEN = /\b(?:open|openSync)\(\s*(['"`])([^'"`\n$]+)\1\s*,\s*(['"`])([rwaxs+]*)\3/g;
const NODE_COPY = /\b(?:copyFile|copyFileSync|rename|renameSync|cp|cpSync)\(\s*(['"`])[^'"`\n]*\1\s*,\s*(['"`])([^'"`\n$]+)\2/g;

// A python call's argument list, as { positional: [...], keyword: { name: text } }, each value
// the source text; commas inside quotes do not split.
function pyArgs(list) {
  const parts = [];
  let cur = '';
  let q = null;
  for (const ch of list) {
    if (q) { cur += ch; if (ch === q) q = null; continue; }
    if (ch === "'" || ch === '"') { q = ch; cur += ch; continue; }
    if (ch === ',') { parts.push(cur); cur = ''; continue; }
    cur += ch;
  }
  if (cur.trim()) parts.push(cur);
  const positional = [];
  const keyword = {};
  for (const p of parts) {
    const m = p.match(/^\s*([A-Za-z_]\w*)\s*=(?!=)\s*([\s\S]*)$/);
    if (m) keyword[m[1]] = m[2];
    else positional.push(p);
  }
  return { positional, keyword };
}
// The text of a plain string literal ('x' or "x"), or null for anything else (an f-string, a name).
function pyString(text) {
  const m = String(text == null ? '' : text).match(/^\s*(['"])([^'"\n]*)\1\s*$/);
  return m ? m[2] : null;
}
const PY_WRITE_MODE = /[wax+]/;

export function scriptWriteTargets(kind, text) {
  const out = [];
  const t = String(text);
  if (kind === 'python') {
    for (const m of t.matchAll(PY_OPEN)) {
      const { positional, keyword } = pyArgs(m[1]);
      const file = pyString(keyword.file != null ? keyword.file : positional[0]);
      const mode = pyString(keyword.mode != null ? keyword.mode : (keyword.file != null ? positional[0] : positional[1]));
      if (file && mode != null && PY_WRITE_MODE.test(mode)) out.push(file);
    }
    for (const m of t.matchAll(PY_PATH_OPEN)) {
      const { positional, keyword } = pyArgs(m[3]);
      const mode = pyString(keyword.mode != null ? keyword.mode : positional[0]);
      if (mode != null && PY_WRITE_MODE.test(mode)) out.push(m[2]);
    }
    for (const m of t.matchAll(PY_PATH_WRITE)) out.push(m[2]);
    for (const m of t.matchAll(PY_SHUTIL)) out.push(m[2]);
  } else if (kind === 'node') {
    for (const m of t.matchAll(NODE_WRITE)) out.push(m[2]);
    for (const m of t.matchAll(NODE_OPEN)) if (/[wa+]/.test(m[4])) out.push(m[2]);
    for (const m of t.matchAll(NODE_COPY)) out.push(m[3]);
  }
  return out.filter((p) => !/[{}$]/.test(p));
}

function resolveAgainst(text, cwd) {
  if (path.isAbsolute(text)) return path.normalize(text);
  if (!cwd) return null;
  return path.resolve(cwd, text);
}

// Interpreter options that take the next word as their operand; anything else starting with - is
// an option on its own, and the first other word is the script file.
const INTERPRETER_OPERANDS = {
  python: new Set(['-W', '-X', '--check-hash-based-pycs']),
  node: new Set(['-r', '--require', '--import', '--input-type', '-C', '--conditions', '--loader', '--experimental-loader', '--env-file', '--title']),
};

// What a shell (sh, bash, ...) runs, from its arguments: { script } for -c, alone or in a cluster
// (-lc, -ec; null when no operand follows), { stdin: true } when no -c and no script file is
// given (bash <<EOF, bash -s <<EOF, bash - <<EOF, a pipe), and {} for a script file, whose
// contents are not in the command.
function shellScript(args) {
  let c = false;
  let s = false;
  let operand;
  for (let k = 0; k < args.length; k++) {
    const t = args[k].text;
    if (t === '--' || t === '-') { operand = args[k + 1]; break; }
    if (t === '-o' || t === '+o' || t === '--rcfile' || t === '--init-file') { k++; continue; }
    if (/^[-+][A-Za-z]+$/.test(t)) {
      if (t[0] === '-' && t.includes('c')) c = true;
      if (t[0] === '-' && t.includes('s')) s = true;
      if (t.endsWith('o')) k++;   // -euo pipefail: the cluster's o takes the next word
      continue;
    }
    if (t.startsWith('--')) continue;
    operand = args[k];
    break;
  }
  if (c) return { script: operand || null };
  if (s || !operand) return { stdin: true };
  return {};
}

// The paths a command would write, each as { path, how }, resolved against `cwd` (the session's
// working directory; a `cd` earlier in the command moves it, a `cd` inside `( ... )` only up to
// the `)`, a `cd` inside an if, loop or case body leaves it unknown once the body closes, since
// the body may not run, and one the lexer cannot read makes every later relative path
// unresolvable). A glob is expanded against the filesystem, as the shell would expand it before
// the command runs, so `sed -i ... docs/*.md` names each file. `how` names the writing construct
// for the refusal. Returns { targets, opaque }.
export function extractWriteTargets(command, cwd) {
  const { segments, opaque } = lex(command);
  const targets = [];
  let dir = cwd || null;
  let unknownDir = false;
  const add = (w, how) => {
    if (!w || !w.text) return;
    if (w.glob) {
      const m = expandGlob(w, unknownDir ? null : dir);
      if (m) for (const x of m) add(x, how);
      return;
    }
    if (!w.literal) return;
    const p = resolveAgainst(w.text, unknownDir ? null : dir);
    if (p) targets.push({ path: p, how });
  };
  let sawOpaqueCommand = false;
  const recurse = (text) => {
    const sub = extractWriteTargets(text, unknownDir ? null : dir);
    targets.push(...sub.targets);
    if (sub.opaque) sawOpaqueCommand = true;
  };
  // What a command at segment `idx` reads on stdin, as text the hook holds: its own heredocs and
  // here-strings, and those of the commands piped into it (cat <<EOF | python3 -).
  const stdinBodies = (idx) => {
    const out = [...segments[idx].heredocs];
    for (let j = idx - 1; j >= 0 && segments[j].op === '|'; j--) out.push(...segments[j].heredocs);
    return out;
  };
  // Open scopes, innermost last: a subshell frame holds the dir to restore at its `)`; a function
  // frame (`f() { ... }`, a body defined, not run) holds the dir to restore at its closing brace;
  // a compound frame (if, while, until, for, case) records whether a cd ran in its body.
  const frames = [];
  const CLOSERS = { fi: ['if'], done: ['while', 'until', 'for'], esac: ['case'] };
  const isScope = (f) => f.kind === 'subshell' || f.kind === 'function';
  const closeSubshell = () => {
    for (let j = frames.length - 1; j >= 0; j--) {
      if (frames[j].kind === 'case' || frames[j].kind === 'function') return;   // in a case body a ) ends a pattern
      if (frames[j].kind === 'subshell') { ({ dir, unknownDir } = frames[j]); frames.length = j; return; }
    }
  };
  const closeCompound = (kinds) => {
    for (let j = frames.length - 1; j >= 0 && !isScope(frames[j]); j--) {
      if (!kinds.includes(frames[j].kind)) continue;
      if (frames.slice(j).some((f) => f.moved)) unknownDir = true;
      frames.length = j;
      return;
    }
  };
  const movedHere = () => {
    for (let j = frames.length - 1; j >= 0 && !isScope(frames[j]); j--) frames[j].moved = true;
  };
  // The braces of a function body: the frame closes, restoring the dir, when its depth returns to 0.
  const braces = (seg) => {
    const f = frames[frames.length - 1];
    if (!f || f.kind !== 'function') return;
    if (f.depth === 0 && !(seg.words.length && seg.words[0].text === '{')) { frames.pop(); return; }   // a body without braces: not followed
    for (const w of seg.words) {
      if (w.text === '{') f.depth++;
      else if (w.text === '}') f.depth--;
    }
    if (f.depth <= 0) { ({ dir, unknownDir } = f); frames.pop(); }
  };
  for (let idx = 0; idx < segments.length; idx++) {
    const seg = segments[idx];
    if (seg.paren === '(') {
      const next = segments[idx + 1];
      const prev = segments[idx - 1];
      const named = prev && prev.op === '(' && (prev.words.length === 1 || (prev.words.length === 2 && prev.words[0].text === 'function'));
      if (next && next.paren === ')' && named) {
        frames.push({ kind: 'function', dir, unknownDir, depth: 0 });   // name() ... : a definition, not a run
        idx++;
        continue;
      }
      frames.push({ kind: 'subshell', dir, unknownDir });
      continue;
    }
    if (seg.paren === ')') { closeSubshell(); continue; }
    braces(seg);
    for (const r of seg.redirects) {
      if (!WRITE_REDIRECTS.has(r.op)) continue;
      if (r.target.glob) {   // a glob target writes its one match; several, or none, is an ambiguous redirect
        const m = expandGlob(r.target, unknownDir ? null : dir);
        if (m && m.length === 1) add(m[0], `${r.op} redirection`);
      } else add(r.target, `${r.op} redirection`);
    }
    for (const inner of seg.subs) recurse(inner);
    const head = seg.words.length ? seg.words[0].text : '';
    if (head in CLOSERS) closeCompound(CLOSERS[head]);
    else if (head === 'if' || head === 'while' || head === 'until' || head === 'for' || head === 'case') frames.push({ kind: head, moved: false });
    const cmd = commandOf(seg.words);
    if (!cmd) continue;
    const { args } = cmd;
    let { name } = cmd;
    if (/^(python[0-9.]*|pypy[0-9]*)$/.test(name)) name = 'python';
    else if (name === 'nodejs') name = 'node';
    switch (name) {
      case 'cd': case 'pushd': {
        let a = args.find((w) => !w.text.startsWith('-') || w.text === '-');
        if (a && a.glob) {   // cd docs/*: one match is the directory; several, or none, leave it unknown
          const m = expandGlob(a, unknownDir ? null : dir);
          a = m && m.length === 1 ? m[0] : word(a.text, false, a.raw);
        }
        if (!a) { dir = os.homedir(); unknownDir = false; }
        else if (a.text === '-' || !a.literal) { unknownDir = true; }
        else { dir = resolveAgainst(a.text, unknownDir ? null : dir); unknownDir = dir == null; }
        movedHere();
        break;
      }
      case 'popd': unknownDir = true; movedHere(); break;
      case 'cp': case 'mv': case 'install': case 'ln':
        for (const w of copyTargets(args, unknownDir ? null : dir)) add(w, name);
        break;
      case 'tee':
        for (const a of args) if (!(a.text.startsWith('-') && a.text.length > 1)) add(a, 'tee');
        break;
      case 'dd':
        for (const a of args) if (a.text.startsWith('of=')) add(word(a.text.slice(3), a.literal, a.raw, { glob: a.glob, marks: a.marks && a.marks.slice(3) }), 'dd');
        break;
      case 'sponge': case 'truncate':
        for (let k = 0; k < args.length; k++) {
          const a = args[k];
          if (name === 'truncate' && (a.text === '-s' || a.text === '--size' || a.text === '-r' || a.text === '--reference')) { k++; continue; }
          if (a.text.startsWith('-') && a.text.length > 1) continue;
          add(a, name);
        }
        break;
      case 'sort':
        for (let k = 0; k < args.length; k++) {
          if (args[k].text === '-o' || args[k].text === '--output') add(args[k + 1], 'sort -o');
          else if (args[k].text.startsWith('--output=')) add(word(args[k].text.slice(9), args[k].literal, args[k].raw, { glob: args[k].glob, marks: args[k].marks && args[k].marks.slice(9) }), 'sort -o');
        }
        break;
      case 'sed':
        for (const w of sedTargets(args)) add(w, 'sed -i');
        break;
      case 'perl':
        for (const w of perlTargets(args)) add(w, 'perl -i');
        break;
      case 'python': case 'node': {
        const kind = name;
        let inline = null;
        let stdin = true;   // no script operand: the script is on stdin (python3 <<EOF, python3 -u <<EOF)
        for (let k = 0; k < args.length; k++) {
          const a = args[k];
          if (kind === 'python' && /^-[WX]./.test(a.text)) continue;   // -Xutf8, -Wignore: an option with its value glued on
          if (kind === 'python' && /^-[A-Za-z]*c$/.test(a.text)) { inline = args[k + 1] || null; stdin = false; break; }
          if (kind === 'node' && (a.text === '-e' || a.text === '--eval' || a.text === '-p' || a.text === '--print')) { inline = args[k + 1] || null; stdin = false; break; }
          if (a.text === '-') break;   // stdin, said so
          if (kind === 'python' && a.text === '-m') { stdin = false; break; }   // a module
          if (INTERPRETER_OPERANDS[kind].has(a.text)) { k++; continue; }
          if (a.text.startsWith('-')) continue;
          stdin = false;   // a script file: its contents are not in the command
          break;
        }
        if (inline) {
          if (inline.literal) for (const p of scriptWriteTargets(kind, inline.text)) add(word(p, true, p), `${kind} script`);
          else sawOpaqueCommand = true;
        } else if (stdin) {
          for (const body of stdinBodies(idx)) for (const p of scriptWriteTargets(kind, body)) add(word(p, true, p), `${kind} script`);
        }
        break;
      }
      case 'eval': case 'xargs': sawOpaqueCommand = true; break;
      default:
        if (SHELLS.has(name)) {
          const sh = shellScript(args);
          if ('script' in sh) {
            if (sh.script && sh.script.literal) recurse(sh.script.text);
            else if (sh.script) sawOpaqueCommand = true;
          } else if (sh.stdin) {
            for (const body of stdinBodies(idx)) recurse(body);   // bash <<'EOF' ... EOF: the body is the script
          }
        }
    }
  }
  return { targets, opaque: opaque || sawOpaqueCommand };
}

// ── the verdict ─────────────────────────────────────────────────────

// One command's targets share one memo, keyed by the Map of link closures evaluate creates for
// the call (the Map is the call's identity; the tests hold one too): the project root per
// directory, the two config lists per root and the real path per directory, each read once per
// call however many landing files a directory copy names (twenty thousand landing files judged
// with a config read and a root search each took seconds; with the memo, a stat or two per file).
// `activeMemo` is the memo of the isGuardedPath call under way (synchronous, so never two at
// once); trackedPaths and untrackedPaths below are store-io's readers behind it, so trackedIn
// reads as isTrackedFile does.
const memos = new WeakMap();
let activeMemo = null;
const newMemo = (closures) => ({ closures, roots: new Map(), configs: new Map(), realDirs: new Map() });
function memoFor(closures) {
  if (!closures) return newMemo(new Map());
  let m = memos.get(closures);
  if (!m) { m = newMemo(closures); memos.set(closures, m); }
  return m;
}
function configOf(root) {
  const m = activeMemo;
  if (!m) return { tracked: readTrackedPaths(root), untracked: readUntrackedPaths(root) };
  let c = m.configs.get(root);
  if (!c) { c = { tracked: readTrackedPaths(root), untracked: readUntrackedPaths(root) }; m.configs.set(root, c); }
  return c;
}
function trackedPaths(root) { return configOf(root).tracked; }
function untrackedPaths(root) { return configOf(root).untracked; }
function rootOf(file) {
  if (process.env.TRACKCHANGES_ROOT) return process.env.TRACKCHANGES_ROOT;
  const m = activeMemo;
  const dir = path.dirname(file);
  if (m && m.roots.has(dir)) return m.roots.get(dir);
  const root = findVaultRoot(file);
  if (m) m.roots.set(dir, root);
  return root;
}

// store-io's isTrackedFile, with the link closure (its one costly step: a walk of every .md
// under the root and a read of every tracked note) built once per root per call and kept in
// `closures`, a Map the caller holds for the call. The three steps and their order are
// isTrackedFile's own: the veto list wins, then the explicit list by name (an exact entry or a
// `dir/` prefix, which also covers a file that does not exist yet), then the closure.
// tools/romp-track-bash-guard-shapes.test.mjs pins isTrackedFile's body to these steps, so a
// vendored bump that changes them fails there by name.
function trackedIn(root, file, closures) {
  const rel = relPathFor(root, file);
  if (engine.isTracked(untrackedPaths(root), rel)) return false;
  const list = trackedPaths(root);
  if (engine.isTracked(list, rel)) return true;
  if (!list.length) return false;
  let closure = closures.get(root);
  if (!closure) { closure = trackedClosure(root); closures.set(root, closure); }
  return closure.has(rel);
}

// The path the kernel opens for `file`: every symlink in it resolved (the native realpath, which
// also reports each name as the filesystem spells it), for a file that need not exist yet: its
// directory's real path (memoised per call) with the name appended, and a dangling link followed
// to where its target would be. null when nothing of the path exists. One lstat for an absent
// file, one more realpath for one that exists.
const lstatOrNull = (file) => fs.lstatSync(file, { throwIfNoEntry: false }) || null;   // no exception for an absent file
function realPathOf(file, depth = 0, st = lstatOrNull(file)) {
  if (st) {
    try { return fs.realpathSync.native(file); } catch { /* a dangling link */ }
    if (!st.isSymbolicLink() || depth >= 40) return null;
    let target;
    try { target = path.resolve(path.dirname(file), fs.readlinkSync(file)); } catch { return null; }
    return realPathOf(target, depth + 1);
  }
  const dir = path.dirname(file);
  if (dir === file) return null;
  const m = activeMemo;
  let realDir = m ? m.realDirs.get(dir) : undefined;
  if (realDir === undefined) { realDir = realPathOf(dir, depth); if (m) m.realDirs.set(dir, realDir); }
  return realDir == null ? null : path.join(realDir, path.basename(file));
}

// Whether `file`, an absolute path, is a tracked TEXT file of its project by that name: a
// directory, a non-text file by name, a file outside any project, an untracked file, and a
// tracked binary under a text-looking name all answer false; so does any error (the vendored
// guard's posture: a guard that cannot read the config denies nothing). `st` is the file's lstat,
// or null for a file that does not exist yet (which may still be tracked by folder).
function guardedByName(file, closures, st = lstatOrNull(file)) {
  if (isNonTextPath(file)) return false;
  if (st && (st.isDirectory() || (st.isSymbolicLink() && (fs.statSync(file, { throwIfNoEntry: false }) || st).isDirectory()))) return false;
  const root = rootOf(file);
  if (!root) return false;
  if (!(closures ? trackedIn(root, file, closures) : isTrackedFile(root, file))) return false;
  if (hasNulBytes(file)) return false;
  return true;
}

// Whether a write to `file` (an absolute path) lands on a tracked text file: under the name given,
// or under the name the kernel opens for it (realPathOf), so a symlink to a tracked file, inside
// or outside its project, does not carry a write past the guard. The name given is judged first,
// so a tracked file that is itself a link out of its project stays guarded. `closures` (optional)
// is the per-call Map evaluate passes so that one command's targets share one closure per root
// and one memo (above); without it the answer comes from store-io's isTrackedFile directly.
export function isGuardedPath(file, closures) {
  const prev = activeMemo;
  activeMemo = memoFor(closures);
  try {
    const st = lstatOrNull(file);
    if (guardedByName(file, closures, st)) return true;
    const real = realPathOf(file, 0, st);
    return real != null && real !== file && guardedByName(real, closures);
  } catch { return false; } finally { activeMemo = prev; }
}

// Returns a block reason string when the command must be denied, or null to allow.
export function evaluate(raw) {
  let payload;
  try { payload = JSON.parse(raw); } catch { return null; }
  if (!payload || payload.tool_name !== 'Bash') return null;
  const command = payload.tool_input && payload.tool_input.command;
  if (typeof command !== 'string' || !command) return null;
  const cwd = typeof payload.cwd === 'string' && payload.cwd ? payload.cwd : process.cwd();
  let targets;
  try { ({ targets } = extractWriteTargets(command, cwd)); } catch { return null; }
  const seen = new Set();
  const closures = new Map();
  for (const t of targets) {
    if (seen.has(t.path)) continue;
    seen.add(t.path);
    if (!isGuardedPath(t.path, closures)) continue;
    return `Track-changes is ON for ${t.path}, so this command is blocked here `
      + `(its ${t.how} would write the file silently, with no change for me to accept or reject). `
      + `Make the change with track-edit instead, which records it for me to accept or reject:\n`
      + `  node ~/.claude/hooks/track-edit.mjs --file "${t.path}" --old "<exact unique text>" --new "<replacement>"`;
  }
  return null;
}

const invokedDirectly = (() => {
  try { return process.argv[1] && fs.realpathSync(process.argv[1]) === fileURLToPath(import.meta.url); }
  catch { return false; }
})();

if (invokedDirectly) {
  // Registered machine-wide by install.sh, so it runs on every Bash call in every Claude Code
  // session on the machine; it acts only in sessions romp launched. Both romp backends put the
  // session's stable id in its environment as ROMP_SID and hook commands inherit that environment;
  // no ROMP_SID means not a romp session, so pass the call through before stdin is read (the
  // vendored guard does the same, vendor/track-changents/patches/0004).
  if (!process.env.ROMP_SID) process.exit(0);
  let raw = '';
  process.stdin.setEncoding('utf8');
  process.stdin.on('data', (c) => { raw += c; });
  process.stdin.on('end', () => {
    let reason = null;
    try { reason = evaluate(raw); } catch { reason = null; }
    if (reason) { process.stderr.write(reason + '\n'); process.exit(2); }
    process.exit(0);
  });
}

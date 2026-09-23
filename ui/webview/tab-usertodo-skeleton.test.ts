// THE FLAG ON A TAB WHOSE PAYLOAD THIS PAGE HAS NOT BEEN SERVED (the user 2026-09-22, whose flagged sessions wore no
// flag until their tab was clicked). A session's open user todos ride its session payload (build_session's userTodos
// rows, re-sent on every chatTail), and the tab's glyph (tab-usertodo.test.ts), the folded header's flag
// (tab-group-flags.test.ts) and the section snapshot's count (tab-snapshot.test.ts) read that payload. Two upstream
// mechanisms withhold it for a tab nobody has opened: the skeleton diet (a redial, a later chat column, the main pane's
// first dial after a reload) and the cold-tab gate. So the COUNT of a session's open todos now rides the tabOrder roster
// beside its name, colour and emoji (the kernel's _tab_meta; tab-meta.ts TabSessionMeta), the strip meta every chat
// client receives for every listed tab, and the skeleton and placeholder builders paint the flag from it. A todo's text
// stays session content and loads with the tab. Source pins in tab-usertodo.test.ts's style (the renderer has no jsdom
// harness); each names the executed test of the rule it guards. tab-strip-skip.test.ts's census is the RULE these
// instances follow: every glyph the loaded row paints from the session has a strip-meta counterpart in the two rows.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as path from "node:path";
import { createRequire } from "node:module";
import { openUserTodo } from "./tab-state";   // the ONE spelling of "open" over the count (correctness-1, review round 1): the builders run against the real one below
import { nodeFactory } from "../test-dom-shim";

const requireCjs = createRequire(__filename);
const RENDER = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "render.ts"), "utf8");
const SNAP = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "tab-snapshot.ts"), "utf8");
const META = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "tab-meta.ts"), "utf8");
const STATE = fs.readFileSync(path.resolve(process.cwd(), "..", "ui", "webview", "tab-state.ts"), "utf8");

const fn = (src: string, name: string): string => {
  const i = src.indexOf(`function ${name}(`);
  assert.ok(i >= 0, `${name} not found`);
  return src.slice(i, src.indexOf("\n}\n", i) + 3);
};
const skeleton = fn(RENDER, "makeSkeletonTab"), placeholder = fn(RENDER, "makePlaceholderTab");
const renderTabs = RENDER.slice(RENDER.indexOf("function renderTabs() {"), RENDER.indexOf("function stripAftermath("));
const sig = renderTabs.slice(renderTabs.indexOf("const stripSig = JSON.stringify(["), renderTabs.indexOf("const mslotEl = "));
// a row's CODE: comments out, as tab-strip-skip.test.ts's census reads the rows (a term spelled only in a comment is not a read,
// and the includes checks below must miss it), by the TypeScript lexer (the comment ranges of every token, leading and trailing),
// which reads strings, template literals and regex literals, so a comment marker inside one opens nothing. A regex stripper
// cannot: two passes, blocks first, opened a block at the `accept=image/*` in a line comment of render.ts's setupComposer and
// swallowed 150 lines to the next `*/` (about 9,500 characters of source, about 3,500 of them code on 98 lines); one alternation,
// left to right, recovered the 16 code lines to the string "image/*" the composer sets its picker to, 22 lines on, and opened a
// block THERE that swallowed the other 128 lines (about 2,800 characters of code on 83 lines, five module-level functions of the
// composer's file-drop code among them) from every census below (found and measured in review round 2). The walk below pins that
// no tabMeta.get( literal is lost to the strip. One lex per file, memoized: render.ts takes about a third of a second.
const ts = requireCjs("typescript");
const lexed = new Map<string, { code: string; blanked: string }>();
const lex = (t: string): { code: string; blanked: string } => {
  const hit = lexed.get(t);
  if (hit !== undefined) return hit;
  const sf = ts.createSourceFile("x.ts", t, ts.ScriptTarget.Latest, false, ts.ScriptKind.TS);
  const cut: Array<[number, number]> = [], seen = new Set<number>();
  const add = (rs: Array<{ pos: number; end: number }> | undefined): void => { for (const r of rs ?? []) if (!seen.has(r.pos)) { seen.add(r.pos); cut.push([r.pos, r.end]); } };
  const visit = (n: any): void => { add(ts.getLeadingCommentRanges(t, n.pos)); add(ts.getTrailingCommentRanges(t, n.end)); for (const c of n.getChildren(sf)) visit(c); };
  visit(sf);
  cut.sort((a, b) => a[0] - b[0]);
  let code = "", blanked = "", p = 0;   // code: the comments removed; blanked: the comments as same-length spaces, so a source index still points at its character
  for (const [a, b] of cut) { if (a < p) continue; code += t.slice(p, a); blanked += t.slice(p, a) + t.slice(a, b).replace(/[^\n]/g, " "); p = b; }
  const r = { code: code + t.slice(p), blanked: blanked + t.slice(p) };
  lexed.set(t, r);
  return r;
};
const stripComments = (t: string): string => lex(t).code;
const sigRow = (marker: string): string => {
  const a = sig.indexOf(marker);
  assert.ok(a >= 0, "the signature row " + marker + " is in renderTabs");
  return stripComments(sig.slice(a, sig.indexOf("];", a)));
};
/** The builder paints the flag: the tab's own mark and class (tab-usertodo.test.ts pins the style and the phone scrape),
 *  from the strip meta's count, and never a number on the strip (plans/user-todos.md governs the glyph, not the wire). */
function paintsFlagFromMeta(builder: string, name: string): void {
  assert.match(builder, /const meta = tabMeta\.get\(id\);/, name + " reads the strip meta");
  assert.match(builder, /if \(openUserTodo\(meta\?\.userTodos\)\) \{\s*\n\s*const ut = el\("span", "tab-usertodo"\);\s*\n\s*ut\.textContent = "⚑";/,
    name + " paints the tab's own mark when the ONE open predicate says so (tab-state.ts openUserTodo, the folded header's and the signature rows' spelling; executed below on 2, 1, 0, -1 and no count): the glyph a loaded tab wears (tab-usertodo.test.ts), the class the phone scrape and the header's flag share");
  assert.match(builder, /ut\.title = /, name + ": the flag explains itself on hover, as on a loaded tab");
  const block = builder.slice(builder.indexOf('el("span", "tab-usertodo")'), builder.indexOf('el("span", "tab-usertodo")') + 300);
  assert.doesNotMatch(block, /userTodos\s*\+|`\$\{[^}]*userTodos|String\(meta/, name + ": no count reaches the strip (the glyph is non-numeric on every tab kind)");
  assert.doesNotMatch(block, /tab-dot/, name + ": the flag is not a pip");
  const label = builder.indexOf("tab.appendChild(label);"), glyph = builder.indexOf('el("span", "tab-usertodo")');
  assert.ok(label >= 0 && label < glyph, name + ": the flag follows the label, as on a loaded tab");
}

test("the roster row's count lands on the strip meta: applyTabOrder parses it INLINE and the tabMeta entry type carries it", () => {
  const apply = fn(RENDER, "applyTabOrder");
  // inline, not a helper: chat-split-exec.test.ts lifts applyTabOrder by source into a stub world where a new import would
  // be undefined; a non-negative integer or nothing: an older kernel's row has no key, and a count that is not the kernel's
  // contract (text, a fraction, a negative; tests/test_user_todos_roster.py holds the kernel to a non-negative integer) reads
  // as no key too, as text did from the start, so every reader downstream holds a real count or nothing and the builders
  // paint nothing for it (correctness-1, review round 1)
  assert.match(apply, /tabMeta\.set\(t\.id, \{[^}]*userTodos: Number\.isInteger\(t\.userTodos\) && t\.userTodos >= 0 \? t\.userTodos : undefined/,
    "the parse is the set literal's own expression and admits the kernel's contract alone (executed: chat-split-exec.test.ts drives the lifted applyTabOrder with rows of 2, 0, no key, a string, -1 and a fraction, reads the entries' counts, and hands the -1 row's entry to snapshotRow for a count of 0)");
  assert.match(RENDER, /^const tabMeta = new Map<string, \{ name: string; color: Color \| null; emoji\?: string; userTodos\?: number \}>\(\);/m,
    "the entry type names the count (tab-close-optimistic.test.ts holds this declaration within 900 characters of closingTabs)");
  assert.match(META, /export interface TabSessionMeta \{ name: string; color: TabColor \| null; emoji\?: string; userTodos\?: number \| ReadonlyArray<unknown> \| null \}/,
    "tab-meta.ts's shape of a strip member carries it: a count on a roster row, the rows on a session (applyMetaToSession takes a Session through this type)");
  assert.doesNotMatch(fn(META, "applyMetaToSession"), /userTodos/, "the push syncs name, colour and emoji onto a loaded session; its todo rows are the session payload's own and stay so");
});

test("makeSkeletonTab paints the flag from the strip meta's count, never from the stale entry's rows", () => {
  paintsFlagFromMeta(skeleton, "makeSkeletonTab");
  assert.doesNotMatch(skeleton, /stale\??\.userTodos/,
    "the pre-outage session entry a redial keeps underneath is what liveSession exists to hide; its rows are stale, the roster count is the kernel's current");
  const glyph = skeleton.indexOf('el("span", "tab-usertodo")'), widgets = skeleton.indexOf("appendTabAfterWidgets(tab");
  assert.ok(glyph < widgets, "the flag before the after-the-name widgets, as on a loaded tab (skeleton-tabs-wiring.test.ts orders label, widgets, close)");
});

test("makePlaceholderTab paints it too: a tab whose session is still being built has the roster's count already", () => {
  paintsFlagFromMeta(placeholder, "makePlaceholderTab");
});

test("the strip signature's skeleton AND placeholder rows carry the count, so a change repaints; the loaded row still reads the session's rows", () => {
  // without the term a filed or resolved todo on a skeleton computes an EQUAL signature and the repaint is skipped
  // (tab-strip-skip.test.ts: the signature is the input list; its census is the rule, these two are the instances)
  assert.ok(sigRow('return ["k",').includes("m?.userTodos"), "the skeleton row's code reads the meta's count (comments stripped)");
  assert.ok(sigRow('return ["p",').includes("m?.userTodos"), "the placeholder row's code reads the meta's count (comments stripped)");
  assert.ok(sig.includes("!!(s.userTodos && s.userTodos.length)"), "the loaded row's input is unchanged (tab-usertodo.test.ts)");
  // the kernel's painter-key census (tests/test_cold_tab_gate.py) reads the skeleton row's kst?. keys: the count is meta, not status
  assert.ok(!sigRow('return ["k",').includes("kst?.userTodos"), "the count rides the roster row, never the status frame");
});

test("one spelling of open over the roster count: every read of a strip-meta row's userTodos that decides open goes through tab-state's openUserTodo, derived from the sources within a stated bound (two regexes over the names m and meta across render.ts, tab-snapshot.ts and tab-state.ts, the names the two builders and the signature bind the row to; every tabMeta.get( outside those three slices held to what it does with the row, and a literal the strip removed or the walk did not visit refused); the snapshot's count assignment is the one named exemption, the two hand-offs are named with their receivers, and a row reached without the literal is outside the walk", () => {
  // THE RULE (correctness-1, review round 1 of the roster change): a count from the kernel is a non-negative integer, and one
  // predicate over it, tab-state.ts openUserTodo (the folded header's since the count landed), keeps "open" one fact on the
  // strip: the two builders, the two signature rows, the header and the section snapshot's needs-you cannot disagree on a
  // value none of them expected. Executed: the builders below on -1, tab-strip-skip-exec.test.ts's signature on -1,
  // tab-snapshot.test.ts's row on -1, tab-group-flags.test.ts's header on 0 and a count.
  assert.match(STATE, /^export const openUserTodo = \(v: TabTodoLike\["userTodos"\]\): boolean =>\s*\n\s*typeof v === "number" \? v > 0 : Array\.isArray\(v\) && v\.length > 0;/m,
    "tab-state.ts exports the one predicate, spelled once: a positive count, or a non-empty list of rows");
  const importNames = (src: string, file: string): string[] => {
    const m = src.match(/^import \{([^}]*)\} from "\.\/tab-state";/m);
    assert.ok(m, file + " imports from tab-state");
    return m![1].split(",").map((s) => s.trim());
  };
  for (const [src, file] of [[RENDER, "render.ts"], [SNAP, "tab-snapshot.ts"]] as const) {
    assert.ok(importNames(src, file).includes("openUserTodo"), file + " imports the predicate from tab-state");
    assert.doesNotMatch(stripComments(src), /\b(?:const|let|var|function)\s+openUserTodo\b/, file + " defines no predicate of its own: one spelling, in tab-state.ts");
  }
  // THE RECEIVERS, derived: a strip-meta row is what tabMeta.get(id) returns. In the two builders and the signature it is
  // bound as `meta` (the builders) or `m` (the skeleton and placeholder rows), or read for its emoji alone (the loaded row's
  // fallback); the snapshot's is its `meta` parameter and tab-state's member is `m`. Every tabMeta.get(id) in those slices is
  // one of those, so a read of the count is spelled `m?.userTodos`, `meta?.userTodos` or `meta.userTodos`
  const bindings = [...stripComments(skeleton + placeholder + sig).matchAll(/(?:const (\w+) = )?tabMeta\.get\((?:[^()]|\([^()]*\))*\)(\?\.\w+)?/g)].map((m) => m[1] ?? m[2]);
  assert.deepEqual(bindings.sort(), ["?.emoji", "m", "m", "meta", "meta"], "the strip meta's bindings in the builders and the signature: the two builders' meta, the two rows' m, the loaded row's emoji fallback");
  assert.match(fn(SNAP, "snapshotRow"), /^function snapshotRow\([^)]*meta\?: SnapMetaLike \| null\)/, "the snapshot's row takes the strip meta as `meta`");
  assert.match(fn(STATE, "sectionTodoFlag"), /for \(const m of members\)/, "the header's members are `m`");
  // THE CENSUS: every such read in the code (comments stripped) is the predicate's argument, or is listed here with its line
  const others: string[] = [];
  for (const [src, file] of [[RENDER, "render.ts"], [SNAP, "tab-snapshot.ts"], [STATE, "tab-state.ts"]] as const) {
    const code = stripComments(src);
    for (const hit of code.matchAll(/\b(?:m|meta)\??\.userTodos\b/g)) {
      const i = hit.index!;
      if (code.slice(Math.max(0, i - "openUserTodo(".length), i) === "openUserTodo(") continue;
      const line = code.slice(code.lastIndexOf("\n", i) + 1, code.indexOf("\n", i)).trim();
      if (!others.includes(file + ": " + line)) others.push(file + ": " + line);
    }
  }
  assert.deepEqual(others, [
    'tab-snapshot.ts: const todos = typeof meta?.userTodos === "number" ? meta.userTodos : Array.isArray(s?.userTodos) ? s!.userTodos!.length : 0;',   // the COUNT the row shows and rowWords speaks, not an open check: needsYou asks the predicate over it (below), and the strip's parse admits a non-negative integer alone, so the number here is a real count or 0
  ], "a read of the roster count that is not the one predicate's argument: an open check spelled a second way (truthiness, > 0, a length), or a new exemption to name here with its reason");
  assert.match(fn(SNAP, "snapshotRow"), /needsYou: feedBlock \|\| st\.needsYou \|\| openUserTodo\(todos\),/,
    "the snapshot row's needs-you reads the count through the one predicate (executed: tab-snapshot.test.ts, a meta count of -1 flags nothing)");
  // THE BOUND (fresh-1, review round 2), stated as the kernel-side census states its own (tests/test_user_todos_roster.py): the two
  // regexes above key on the NAMES m and meta, which the three slices bind the row to, so a reader outside the slices that binds
  // tabMeta.get(...) under another name, or chains ?.userTodos off the call, was a pass. Every other `tabMeta.get(` in the three
  // files (comments stripped) is therefore held here to what it does with the row: a member chained off the call by `.`, `?.` or
  // `!.` is a read of that one field, the name, the emoji or the colour unless the field is userTodos; a bracket member is refused
  // (the walk does not read a computed key); a binding (`const X = ...tabMeta.get(...)...`) puts the row, or a session-or-row, under
  // X, whose reads of the count to the end of the enclosing function (by `.`, `?.`, `!.`, a bracket, a destructuring or a call on
  // X) are held to the predicate, and a binding whose own statement reads userTodos after the call (a paren-wrapped call, a fallback,
  // then .userTodos) is refused as the COUNT bound under a name; a row handed to a callee (an argument, a callback's return) leaves
  // for a parameter the walk does not follow and is listed below with the receiver that holds it; a use the walk cannot classify is
  // refused. The walk's regex parses an argument with parens nested one level (tabMeta.get(String(id))); every literal `tabMeta.get(`
  // in the SOURCE is counted against the stripped code and against the walk's visits, and one the strip removed (a comment spelling
  // it: reword it; or a stripper fault) or one the walk did not visit (a deeper nesting) is refused by file and line, so no call is
  // skipped (the closing check of round 2 found three shapes the first walk passed: a paren argument it never visited, a
  // paren-wrapped call read for its count on the binding's own line, a `!.userTodos` chained off the call). Outside the
  // walk, by construction: a row reached without the literal (an accessor built at run time; the map iterated for its rows, pinned
  // absent below: renderTabs walks tabMeta.keys() for ids alone), and a bound name handed on to a callee (upsert hands `tm` to
  // applyMetaToSession, pinned above to read no rows).
  const keywords = new Set(["if", "for", "while", "switch", "return", "typeof", "await", "catch"]);
  const closer = (code: string, from: number): number => { const k = code.slice(from).search(/\n\}[ \t]*(?:\n|$)/); return k >= 0 ? from + k : code.length; };   // the function's column-0 brace
  const fnStarts = (code: string) => [...code.matchAll(/^(?:export )?(?:async )?function (\w+)\(/gm)].map((m) => ({ name: m[1], at: m.index!, end: closer(code, m.index!) }));
  // a read of the count off the name X, spelled any way: X.userTodos, X?.userTodos, X!.userTodos, X["userTodos"], the same on a call X(...), or a destructuring from X
  const countReadOf = (name: string): RegExp => {
    const x = "\\b" + name.replace(/\./g, "\\.") + "(?![\\w$])(?:\\([^()]*\\))?!?";
    return new RegExp(x + "\\??\\.userTodos\\b|" + x + "\\??\\.?\\[\\s*[\"']userTodos[\"']\\s*\\]|\\{[^}]*\\buserTodos\\b[^}]*\\}\\s*=\\s*" + x, "g");
  };
  const countSpelled = /\??\.userTodos\b|\[\s*["']userTodos["']\s*\]/;   // the count read off an expression on the binding's own statement
  const outside: string[] = [], handed: string[] = [], unvisited: string[] = [], lost: string[] = [];
  for (const [src, file, slices] of [[RENDER, "render.ts", [skeleton, placeholder, sig]], [SNAP, "tab-snapshot.ts", []], [STATE, "tab-state.ts", []]] as const) {
    const code = stripComments(src);
    const cut = slices.map((s) => { const c = stripComments(s), at = code.indexOf(c); assert.ok(at >= 0, file + ": a slice is a substring of the stripped file"); return [at, at + c.length] as const; });
    const fns = fnStarts(code);
    const lineOf = (at: number): string => code.slice(code.lastIndexOf("\n", at) + 1, code.indexOf("\n", at)).trim();
    const whereOf = (at: number): string => file + ": " + (fns.filter((f) => f.at <= at && at <= f.end).pop()?.name ?? "<module>") + ": ";
    const visited = new Set<number>();
    for (const hit of code.matchAll(/tabMeta\.get\(((?:[^()]|\([^()]*\))*)\)(!*)(?:(\??\.)(\w+)|(\??\.?\[))?/g)) {
      const i = hit.index!;
      visited.add(i);
      if (cut.some(([a, b]) => a <= i && i < b)) continue;   // the three slices: the bindings above and the two regexes hold them
      const fnOf = fns.filter((f) => f.at <= i && i <= f.end).pop();
      const where = whereOf(i), line = lineOf(i), end = i + hit[0].length;
      if (hit[5] !== undefined) { outside.push(where + "a bracket member off the row: " + line); continue; }   // a computed key: the walk does not read it
      if (hit[4] !== undefined) {   // a chained read of one field (a `!` before the dot admitted)
        if (hit[4] !== "userTodos" || code.slice(Math.max(0, i - "openUserTodo(".length), i) === "openUserTodo(") continue;
        outside.push(where + line); continue;
      }
      const lineStart = code.lastIndexOf("\n", i) + 1;
      const prefix = code.slice(lineStart, i);
      const open: string[] = [];   // the calls still open at the occurrence: inside one, the row is an argument, handed on
      for (let k = 0; k < prefix.length; k++) {
        if (prefix[k] === "(") { const callee = (prefix.slice(0, k).match(/([\w.]+)\s*$/) || [, ""])[1]!; open.push(keywords.has(callee) ? "" : callee); }
        else if (prefix[k] === ")") open.pop();
      }
      const callee = open.find((c) => c !== "");   // the outermost open call
      if (callee !== undefined) { const h = where + callee; if (!handed.includes(h)) handed.push(h); continue; }
      const bound = prefix.match(/(?:^|[;{])\s*(?:(?:const|let|var)\s+)?([\w.]+)\s*=[^=]*$/);
      if (!bound) { outside.push(where + line); continue; }
      const semi = code.indexOf(";", end), rest = code.slice(end, semi >= 0 ? semi : code.length);   // the binding's own statement after the call
      if (countSpelled.test(rest)) { outside.push(where + bound[1] + " = ...tabMeta.get(...)...userTodos (the count bound under a name): " + line); continue; }
      const stmtEnd = code.slice(i).search(/\n(?=\S)/);   // a module-level statement ends at the next column-0 line
      const scope = code.slice(i, fnOf ? fnOf.end : stmtEnd >= 0 ? i + stmtEnd : code.length);
      for (const read of scope.matchAll(countReadOf(bound[1]))) {
        const at = i + read.index!;
        if (code.slice(Math.max(0, at - "openUserTodo(".length), at) === "openUserTodo(") continue;
        outside.push(where + bound[1] + " = tabMeta.get(...): " + lineOf(at));
      }
    }
    for (const lit of code.matchAll(/tabMeta\.get\(/g)) if (!visited.has(lit.index!)) unvisited.push(whereOf(lit.index!) + lineOf(lit.index!));
    const blanked = lex(src).blanked;   // a literal at a source index the strip blanked sat inside a comment
    for (const lit of src.matchAll(/tabMeta\.get\(/g)) if (!blanked.startsWith("tabMeta.get(", lit.index!)) lost.push(file + ": " + src.slice(src.lastIndexOf("\n", lit.index!) + 1, src.indexOf("\n", lit.index!)).trim());
  }
  assert.deepEqual(lost, [], "a tabMeta.get( the comment strip removed: a comment that spells the literal (reword it so the count of literals in the source equals the count in the code), or a stripper fault that would hide a reader from this walk");
  assert.deepEqual(unvisited, [], "a tabMeta.get( the walk's regex did not visit (an argument with parens nested deeper than one level): every literal is held to what it does with the row, so this one is refused where it stands until the walk can read it or it is named in the census above with its reason");
  assert.deepEqual(outside, [], "a strip-meta row read outside the three slices whose count is decided some way other than the one predicate (a chained ?.userTodos or !.userTodos, a binding under another name reading it, the count itself bound under a name, a bracket member, a use the walk cannot classify): route it through openUserTodo, or name it in the census above with its reason");
  assert.deepEqual(handed.sort(), [
    "render.ts: makeGroupHead: sectionTodoFlag",   // the header hands its hidden members' rows to sectionTodoFlag, whose member is `m` (tab-state.ts): the two regexes read it (executed: tab-snapshot-pane.test.ts)
    "render.ts: renderSnapshot: snapshotModel",    // the snapshot's meta accessor: snapshotRow's `meta` parameter (tab-snapshot.ts): the two regexes read it, and its count assignment is the exemption above
  ], "a strip-meta row handed whole to a callee the walk does not follow: the callee's parameter joins the census (its name to the two, its file to the three) or the hand-off is named here with the receiver that holds it");
  assert.doesNotMatch(stripComments(RENDER) + stripComments(SNAP) + stripComments(STATE), /tabMeta\.(?:values|entries|forEach)\(|of tabMeta\)|\[\.\.\.tabMeta\]/,
    "the map is not iterated for its rows (renderTabs walks tabMeta.keys() for ids): a row reached without tabMeta.get( is the walk's one remaining escape, an accessor built at run time");
});

test("executed: the builders paint the flag when the one predicate says open, and none for 0, -1 or no count (the folded header's rule, run over the real makeSkeletonTab and makePlaceholderTab)", () => {
  // the two builders lifted by source into a stub world (tab-strip-skip-exec.test.ts's way), with the REAL openUserTodo from
  // tab-state.ts and a fake element from the shared shim; everything else the builders touch is an inert stand-in. The
  // -1 case is correctness-1's: before the one predicate, the builders read the count by truthiness and -1 painted a flag
  // the header would not raise.
  const make = nodeFactory();
  const el = (tag: string, cls = ""): any => {
    const n = make(tag); n.className = cls;
    for (const c of cls.split(/\s+/)) if (c) n.classList.add(c);
    n.style.setProperty = (k: string, v: string) => { n.style[k] = v; };
    n.replaceChildren = (...cs: any[]) => { n.children.length = 0; for (const c of cs) n.appendChild(c); };
    return n;
  };
  const text = (t: string): any => { const n = make("#text"); n.textContent = t; return n; };
  const js = requireCjs("esbuild").transformSync(skeleton + placeholder, { loader: "ts" }).code;
  const prelude = `
    const H = HOOKS;
    const tabMeta = H.tabMeta, sessions = new Map(), skeletonTabs = { status: new Map() };
    let activeId = null, peekId = null;
    const settings = { tabsLocked: false }, fedMissing = false;
    const openUserTodo = H.openUserTodo;
    const el = H.el;
    const onTabKey = () => {}; const wireTabDrag = () => {}; const applyTabStatus = () => {}; const appendTabAfterWidgets = () => {};
    const showTabMenu = () => {}; const mediaSrc = (f) => f; const tabEmojiNode = () => null;
    const hostNameNodes = (name) => [H.text(name)];
  `;
  const lift = new Function("HOOKS", prelude + js + "\nreturn { makeSkeletonTab, makePlaceholderTab };") as
    (H: { tabMeta: Map<string, unknown>; openUserTodo: typeof openUserTodo; el: typeof el; text: typeof text }) => { makeSkeletonTab: (id: string) => any; makePlaceholderTab: (id: string) => any };
  const glyphs = (tab: any): any[] => tab.children.filter((c: any) => c.classList.contains("tab-usertodo"));
  const cases: Array<[number | undefined, number]> = [[2, 1], [1, 1], [0, 0], [-1, 0], [undefined, 0]];
  for (const [count, want] of cases) {
    const tabMeta = new Map<string, unknown>([["s1", { name: "web", color: null, userTodos: count }]]);
    const api = lift({ tabMeta, openUserTodo, el, text });
    for (const [name, build] of [["makeSkeletonTab", api.makeSkeletonTab], ["makePlaceholderTab", api.makePlaceholderTab]] as const) {
      const tab = build("s1");
      assert.equal(glyphs(tab).length, want, `${name} on a roster count of ${count}: ${want ? "the flag" : "no flag"} (the one predicate's answer; the header agrees, tab-group-flags.test.ts)`);
      if (want) assert.deepEqual([glyphs(tab)[0].textContent, glyphs(tab)[0].title.startsWith("waiting on you: ")], ["⚑", true], name + ": the loaded tab's mark, and it explains itself");
      assert.ok(tab.children.some((c: any) => c.classList.contains("tab-label")), name + " still paints the label");
    }
  }
  const bare = lift({ tabMeta: new Map(), openUserTodo, el, text });
  assert.deepEqual([glyphs(bare.makeSkeletonTab("s9")).length, glyphs(bare.makePlaceholderTab("s9")).length], [0, 0], "no roster row at all: nothing to read, nothing painted");
});

test("the folded header's flag reads the live session, else the strip meta (executed: tab-snapshot-pane.test.ts, the folded header over a member with no session entry, a skeleton's stale entry and a loaded member; the predicate's count cases in tab-group-flags.test.ts)", () => {
  // matched over makeGroupHead's slice, not the whole file: a red here prints the builder, not all of render.ts (the closing
  // verifiers of review round 1 measured a whole-file dump at about 23,000 lines against 232 for a red of a sliced pin). A pin
  // keyed on where the code lives: the executed proof of the composition is tab-snapshot-pane.test.ts's case over the real
  // makeGroupHead and liveSession; tab-group-flags.test.ts runs sectionTodoFlag over rows and counts and never this selection
  // (review round 2, after the pins pointed at it as the executed coverage)
  assert.match(fn(RENDER, "makeGroupHead"), /const flag = sectionTodoFlag\(hidden\.map\(\(id\) => liveSession\(id\) \?\? tabMeta\.get\(id\)\)\);/,
    "a loaded member's rows, a skeleton or placeholder member's roster count: liveSession is undefined for a skeleton (its stale entry never reads as current), and the roster row stands in (executed: tab-snapshot-pane.test.ts, the composition over the real makeGroupHead and liveSession; tab-group-flags.test.ts, the flag rule over rows and counts)");
});

test("snapshotRow reads the roster count FIRST and says why (executed: tab-snapshot.test.ts, the meta-only row and the stale entry)", () => {
  const row = fn(SNAP, "snapshotRow");
  assert.match(row, /const todos = typeof meta\?\.userTodos === "number" \? meta\.userTodos : Array\.isArray\(s\?\.userTodos\) \? s!\.userTodos!\.length : 0;/,
    "the roster count when the kernel sent one, else the session's rows (an older kernel), else nothing");
  const why = row.slice(0, row.indexOf("const todos = "));
  assert.match(why, /sessions\.get\(id\)/, "the comment names the seam: render.ts hands the snapshot sessions.get(id) for every member");
  assert.match(why, /liveSession/, "...which on a redial is the stale pre-outage entry for a skeleton member, the very thing liveSession exists to dodge");
  assert.ok(row.indexOf("meta?.userTodos") < row.indexOf("s?.userTodos"), "roster first: a later reader must not simplify it to rows-first");
  assert.match(SNAP, /export interface SnapMetaLike \{ name\?: string; color\?: SnapColor \| null; userTodos\?: number \}/);
});

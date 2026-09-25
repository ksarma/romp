// THE IMPORT GATE, HELD TO A TYPESCRIPT PARSE (the seventh round of the review of PR 878, ruling B). scripts/network-inventory.py
// gates every package the walked JavaScript and TypeScript files import or require, and it reads their specifiers with a line
// reader (_js_specifiers, driven by line_scan). A line reader of arbitrary source misses any layout it was not written for, so
// this case holds its reads to the TypeScript compiler's parse of the same files:
// - The census hands out its walked files and the gate's reads through python3, from its own code: `--js-reads` runs the walk and
//   line_scan over each file of the js kind, which records each specifier its forms loop reads (file, line, specifier) and each
//   line where its refusal of a require or import the gate cannot read fires. Nothing here replays a copy of that loop.
// - Each file is parsed with ts.createSourceFile (ScriptKind TS for .ts, JS otherwise), and the case collects the specifier of
//   every import declaration and export declaration, of `import X = require()`, of a call of `require` or `import()` whose first
//   argument is a quoted string literal, and of an import type (`typeof import("x")`).
// - The two are compared as multisets keyed on (file, the specifier's line, specifier), both ways. Any difference is red, naming
//   the file, the line, the specifier and the side that has it. Lines are numbered as the census numbers them (Python's
//   str.splitlines).
// - A require or import() call the parse finds on any other first argument (a template, a computed value) must stand on a line
//   where that refusal fires (an IMPORT line, or a place JS_ALLOW names); an import() on a computed argument that is not a
//   template must stand instead on a line the census lists as a browser-computed-url site (line_scan's import() tool).
// - A file the parse reports an error in is red: its specifiers are not known.
// No skip: a missing python3 or a missing typescript FAILS this case, on purpose. file-comments.test.ts and
// file-comments-model-note-trim.test.ts skip without python3; here there would be nothing to compare, and a skip reads as a pass.
// The case holds walked files only. The pages the kernel serves are fragments of Python string literals, not files, so they are
// not parsed here, and the census's docstring states the gate's residual in served text.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import * as fs from "node:fs";
import * as path from "node:path";
import type * as TS from "typescript";

const ROOT = path.resolve(process.cwd(), "..");
const SCRIPT = path.join(ROOT, "scripts", "network-inventory.py");

type Read = [string, number, string];   // file, line, specifier
type Census = { files: string[]; reads: Read[]; unread: Array<[string, number]>; computed: Array<[string, number]> };
type Call = { file: string; line: number; callee: string; arg: string; template: boolean };

/** The offset where each line of the text starts, the lines cut as Python's str.splitlines cuts them (the census's line numbers):
 *  at \n, \r, \r\n, \v, \f, \x1c, \x1d, \x1e, \x85, U+2028 and U+2029. */
function lineStarts(text: string): number[] {
  const out = [0];
  for (let i = 0; i < text.length; i++) {
    const c = text.charCodeAt(i);
    if (c === 13 && text.charCodeAt(i + 1) === 10) { out.push(i + 2); i++; continue; }
    if (c === 10 || c === 13 || c === 11 || c === 12 || (c >= 0x1c && c <= 0x1e) || c === 0x85 || c === 0x2028 || c === 0x2029) out.push(i + 1);
  }
  return out;
}

/** The 1-based line of an offset. */
function lineOf(starts: number[], pos: number): number {
  let lo = 0, hi = starts.length - 1;
  while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (starts[mid] <= pos) lo = mid; else hi = mid - 1; }
  return lo + 1;
}

/** The census's side, from its own code through python3: the walked JavaScript and TypeScript files, the gate's reads, the lines
 *  where its refusal of an unread require or import fires, and its browser-computed-url import() sites. */
function censusReads(): Census {
  const r = spawnSync("python3", [SCRIPT, "--js-reads", ROOT], { cwd: ROOT, encoding: "utf8", timeout: 300000, maxBuffer: 64 << 20 });
  if (r.error) assert.fail(`python3 could not run ${SCRIPT} --js-reads (${r.error.message}): this case needs python3 on PATH and fails without it`);
  assert.equal(r.status, 0, `python3 ${SCRIPT} --js-reads exited ${r.status}: ${r.stderr}`);
  return JSON.parse(r.stdout) as Census;
}

/** The parse's side of one file: every specifier the six declaration, call and type kinds carry, every require or import() call
 *  whose first argument is not a quoted literal, and the parse's own errors. */
function parseFile(ts: typeof TS, file: string, text: string, specs: Read[], calls: Call[], errors: string[]): void {
  const starts = lineStarts(text);
  const sf = ts.createSourceFile(file, text, ts.ScriptTarget.Latest, true, file.endsWith(".ts") ? ts.ScriptKind.TS : ts.ScriptKind.JS);
  for (const d of (sf as unknown as { parseDiagnostics?: readonly TS.Diagnostic[] }).parseDiagnostics ?? [])
    errors.push(`${file}:${lineOf(starts, d.start ?? 0)} ${ts.flattenDiagnosticMessageText(d.messageText, " ")}`);
  const spec = (lit: TS.StringLiteral) => specs.push([file, lineOf(starts, lit.getStart(sf)), lit.text]);
  const call = (node: TS.CallExpression, callee: string) => {
    const arg = node.arguments[0];
    if (arg && ts.isStringLiteral(arg)) { spec(arg); return; }
    calls.push({ file, line: lineOf(starts, node.getStart(sf)), callee, arg: arg ? arg.getText(sf).slice(0, 60) : "",
                 template: !!arg && (ts.isNoSubstitutionTemplateLiteral(arg) || ts.isTemplateExpression(arg)) });
  };
  const visit = (node: TS.Node): void => {
    if (ts.isImportDeclaration(node) && ts.isStringLiteral(node.moduleSpecifier)) spec(node.moduleSpecifier);   // import ... from "x", import "x"
    if (ts.isExportDeclaration(node) && node.moduleSpecifier && ts.isStringLiteral(node.moduleSpecifier)) spec(node.moduleSpecifier);   // export ... from "x"
    if (ts.isImportEqualsDeclaration(node) && ts.isExternalModuleReference(node.moduleReference)
        && ts.isStringLiteral(node.moduleReference.expression)) spec(node.moduleReference.expression);   // import X = require("x")
    if (ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === "require") call(node, "require");   // require(...)
    if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) call(node, "import");   // import(...)
    if (ts.isImportTypeNode(node) && ts.isLiteralTypeNode(node.argument) && ts.isStringLiteral(node.argument.literal)) spec(node.argument.literal);   // typeof import("x")
    ts.forEachChild(node, visit);
  };
  visit(sf);
}

/** A multiset of reads keyed `file:line "specifier"`. */
function tally(reads: Read[]): Map<string, number> {
  const out = new Map<string, number>();
  for (const [file, line, spec] of reads) { const k = `${file}:${line} ${JSON.stringify(spec)}`; out.set(k, (out.get(k) ?? 0) + 1); }
  return out;
}

test("the import gate's reads over the walked JavaScript and TypeScript files are a TypeScript parse's specifiers, both ways, and a require or import() on any other argument stands on a refused line", () => {
  let ts: typeof TS;
  try { ts = require("typescript") as typeof TS; }
  catch (e) { assert.fail(`the typescript package does not load (${(e as Error).message}): npm ci in vscode-extension installs it, and this case fails without it`); }
  const census = censusReads();
  assert.ok(census.files.length > 0, "the census hands out no walked JavaScript or TypeScript file: the comparison would hold over nothing");
  const specs: Read[] = [], calls: Call[] = [], errors: string[] = [];
  for (const file of census.files) parseFile(ts, file, fs.readFileSync(path.join(ROOT, file), "utf8"), specs, calls, errors);
  assert.ok(specs.length > 0, "the parse finds no specifier in the walked files: the comparison would hold over nothing");
  assert.deepEqual(errors, [], "the TypeScript parse reports an error in a walked file, so the pin cannot know that file's specifiers");
  const parsed = tally(specs), read = tally(census.reads), diffs: string[] = [];
  for (const [k, n] of parsed) if (n > (read.get(k) ?? 0)) diffs.push(`${k}: the TypeScript parse finds this specifier ${n} time(s) and the census's line reader reads it ${read.get(k) ?? 0}`);
  for (const [k, n] of read) if (n > (parsed.get(k) ?? 0)) diffs.push(`${k}: the census's line reader reads this specifier ${n} time(s) and the TypeScript parse finds it ${parsed.get(k) ?? 0}`);
  assert.ok(diffs.length === 0, "the import gate reads a specifier where the parse finds none, or misses one it finds (file:line \"specifier\"):\n" + diffs.sort().join("\n"));
  const unread = new Set(census.unread.map(([f, l]) => `${f}:${l}`)), computed = new Set(census.computed.map(([f, l]) => `${f}:${l}`));
  const loose = calls.filter((c) => !(c.callee === "import" && !c.template ? computed : unread).has(`${c.file}:${c.line}`))
    .map((c) => `${c.file}:${c.line} ${c.callee}(${c.arg}): ` + (c.callee === "import" && !c.template
      ? "an import() on a computed argument that is not a template, on a line the census lists as no browser-computed-url site"
      : "a require or import() on an argument that is not a quoted literal, on a line where the census's refusal of a require or import the gate cannot read does not fire"));
  assert.ok(loose.length === 0, "a require or import() call the census neither reads nor refuses:\n" + loose.join("\n"));
});

// No script the kernel serves holds a direct eval or a with statement. Those are the two ways code can add a binding at
// run time to a scope between a listener and the global scope: in sloppy code (every page the kernel writes is sloppy;
// only the timeline view's inlined function opens with 'use strict') a direct eval declares its vars in the calling
// function's scope, and a with statement puts an object's properties in scope for the code inside it. (Any script can
// add a global binding, but the global scope is the last one a name is looked up in.) The pane shim's two window
// message listeners and fromShell, the const they read, sit in one function (kernel.py _shim), so a binding made in
// that function could put a laxer check where the listeners read theirs, and no test that drives senders would see it
// unless it drove the sender the laxer check admits. This census reads the scripts' syntax trees, so no spelling hides
// one: parentheses around the name ((eval)(s)), an escaped name (e\u0076al), a comment or a line break before the
// parenthesis, an optional call (eval?.(s), which is not a direct eval and is refused anyway).
//
// The population is tests/test_shell_source_check.py's _served_scripts: every <script> without a src, every event
// handler attribute and every javascript: URL on each page SERVED_BUILDERS lists (the shell, the six pane pages, the
// timeline, the sign-in page, the too-large page), /sw.js whole, and each SVG under /media. ServedScriptPopulation there
// derives that page list from kernel.py's syntax tree. A script the parser cannot read is refused too.
//
// What the census does not read, and why none of it can shadow the shim's check:
//   - eval reached other than by its name as the callee ((0, eval)(s), window.eval(s), an alias, a computed name), the
//     Function constructor, and a string handed to a timer: each runs its string in the global scope or in a function
//     of its own. The witness below runs the first two kinds in node and shows a function scope's binding left alone; a
//     string timer is compiled as a script of its own in the global scope (the HTML standard's timer steps).
//   - markup a page builds at run time (a handler attribute, a script element): its code is a string until then, and
//     runs as a handler function or a script of its own.
//   - the /dist bundles a page loads by src: tests/test_shell_source_check.py's population leaves them out, the ui/
//     census (foreign-sender-listeners.test.ts) reads their sources, and each runs in its own scope.
// Synthetic only: the kernel's own pages, rendered under a throwaway state root, and invented rows.
import { test } from "node:test";
import * as assert from "node:assert/strict";
import * as fs from "node:fs";
import * as os from "node:os";
import * as path from "node:path";
import * as vm from "node:vm";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";

const EXT = process.cwd();                                        // npm test runs in vscode-extension
const REPO = path.resolve(EXT, "..");
const ts = createRequire(path.join(EXT, "package.json"))("typescript");

type Piece = { page: string; where: string; kind: "script" | "handler" | "url"; code: string };

/** Why the census refuses `code`, one entry per refusal: a with statement, a call whose callee is the name eval (through
 *  any parentheses; the name as the parser reads it, escapes resolved), or a parse error. A handler attribute's code is
 *  read as the body of a function, which is how a browser runs it. */
function scopeRefusals(code: string, kind: Piece["kind"] = "script"): string[] {
  const text = kind === "handler" ? "function handler(event) {\n" + code + "\n}" : code;
  const sf = ts.createSourceFile("served.js", text, ts.ScriptTarget.Latest, true, ts.ScriptKind.JS);
  const out: string[] = [];
  for (const d of sf.parseDiagnostics) out.push("a script the parser cannot read: " + ts.flattenDiagnosticMessageText(d.messageText, " "));
  const at = (n: { getStart(s: unknown): number }) => {
    const { line, character } = sf.getLineAndCharacterOfPosition(n.getStart(sf));
    return (line + 1) + ":" + (character + 1);
  };
  const visit = (n: any): void => {
    if (ts.isWithStatement(n)) out.push("a with statement at " + at(n));
    if (ts.isCallExpression(n) && calleeName(n.expression) === "eval") out.push("a call of eval by its name at " + at(n));
    ts.forEachChild(n, visit);
  };
  visit(sf);
  return out;
}

/** The name a call's callee is, through any parentheses ((eval)(s) is a direct eval too); undefined for anything else. The
 *  identifier's text is its name with escapes resolved (e\u0076al is eval). */
function calleeName(e: any): string | undefined {
  while (ts.isParenthesizedExpression(e)) e = e.expression;
  return ts.isIdentifier(e) ? e.text : undefined;
}

// Each spelling of a direct eval or a with statement, refused.
const REFUSED: Array<[string, string]> = [
  ["eval(s);", "the plain call"],
  ["(eval)(s);", "the name in parentheses, still a direct eval"],
  ["((eval))(s);", "in two pairs of parentheses"],
  ["e\\u0076al(s);", "an escaped name"],
  ["\\u{65}val(s);", "an escaped name in braces"],
  ["eval/**/(s);", "a comment before the parenthesis"],
  ["eval\n(s);", "a line break before the parenthesis"],
  ["eval?.(s);", "an optional call (not a direct eval; refused by the name)"],
  ["function g() { if (x) eval(s); }", "inside a function and a branch"],
  ["with(o){}", "a with statement"],
  ["with (o) { go(); }", "with a space"],
  ["with/**/(o){}", "a comment before the parenthesis"],
  ["with\n(o)\n{}", "line breaks"],
  ["function g() { with (o) go(); }", "inside a function, with no block"],
];
// Survivors: eval or code from a string reached other than as a call of the name. Each runs its string in the global
// scope or in a function of its own (the witness below), so none can put a binding in a scope around a listener.
const SURVIVORS: Array<[string, string]> = [
  ["(0, eval)(s);", "a comma expression as the callee: an indirect eval"],
  ["window.eval(s);", "eval as a member: indirect"],
  ["var run = eval; run(s);", "an alias: indirect"],
  ["window[\"ev\" + \"al\"](s);", "a computed name: indirect"],
  ["Function(s)();", "the Function constructor: a function of its own in the global scope"],
  ["new Function(s)();", "the same, with new"],
  ["setTimeout(s, 0);", "a string timer: a script of its own in the global scope"],
  ["document.body.insertAdjacentHTML(\"beforeend\", \"<b onclick=\\\"with (o) go()\\\">x</b>\");", "markup made at run time"],
  ["eval`s`;", "a tagged template: eval is handed the strings array and returns it"],
];
// Not an eval call or a with statement at all.
const CONTROLS: Array<[string, string]> = [
  ["var e = evaluate(s);", "another name"],
  ["// eval(s) and with (o) {}\nvar a = 1;", "a comment"],
  ["var a = \"eval(s); with (o) {}\";", "a string"],
  ["var b = list.with(0, 1);", "a method named with (Array.prototype.with)"],
  ["var o = { with: 1, eval: 2 }; o.eval(s);", "properties named with and eval"],
];

for (const [src, what] of REFUSED) {
  test("refused: " + what + ": " + JSON.stringify(src), () => assert.equal(scopeRefusals(src).length, 1, "refused once"));
}
for (const [src, what] of SURVIVORS) {
  test("left, a survivor the census names: " + what + ": " + JSON.stringify(src), () => assert.deepEqual(scopeRefusals(src), []));
}
for (const [src, what] of CONTROLS) {
  test("accepted: " + what + ": " + JSON.stringify(src), () => assert.deepEqual(scopeRefusals(src), []));
}
test("a handler attribute is read as a function body: its return is no parse error, and its with statement is refused", () => {
  assert.deepEqual(scopeRefusals("with (o) { return false; }", "handler"), ["a with statement at 2:1"]);
});
test("a script the parser cannot read is refused", () => {
  assert.equal(scopeRefusals("var = ;")[0].startsWith("a script the parser cannot read"), true);
});

// Runs `body` in sloppy node code inside a function `around`, itself inside `outer`, which holds the check a listener in
// `around` reads: check() answers "strict". A binding a form makes in `around`'s scope answers "lax" instead.
const LAX = "var check = function () { return 'lax'; };";
function checkSeenAfter(form: string): string {
  const src = "var seen; var s = " + JSON.stringify(LAX) + ";\n" +
    "(function outer() { const check = function () { return 'strict'; };\n" +
    "  (function around() { " + form + " })(); })();\nseen;";
  return vm.runInNewContext(src, {}, { timeout: 5000 });
}

// Executed: each refused form that makes a binding puts the laxer check where the listener reads it, and each survivor
// node can run leaves the check alone.
for (const form of ["eval(s); seen = check();", "(eval)(s); seen = check();", "e\\u0076al(s); seen = check();",
  "with ({ check: function () { return 'lax'; } }) { seen = check(); }"]) {
  test("executed, refused: it puts a laxer check around a listener: " + JSON.stringify(form), () => {
    assert.equal(checkSeenAfter(form), "lax", "it shadows the check");
    assert.equal(scopeRefusals(form).length, 1, "the census refuses it");
  });
}
for (const form of ["(0, eval)(s); seen = check();", "this.eval(s); seen = check();", "var run = eval; run(s); seen = check();",
  "this[\"ev\" + \"al\"](s); seen = check();", "Function(s)(); seen = check();", "new Function(s)(); seen = check();",
  "eval?.(s); seen = check();"]) {
  test("executed: the check around a listener stays: " + JSON.stringify(form), () => {
    assert.equal(checkSeenAfter(form), "strict", "the check it would shadow stays");
    // an optional call runs its string in the global scope, like the survivors, but the census refuses it by the name
    assert.equal(scopeRefusals(form).length, form.startsWith("eval?.") ? 1 : 0, "the census leaves a survivor and refuses eval?.");
  });
}

/** The kernel's served scripts (tests/test_shell_source_check.py _served_scripts), the pages SERVED_BUILDERS lists, the
 *  documents the scripts were read from, and the pieces of `plant`, a page of our own, as that module's reader finds them;
 *  python3 loads the kernel under a throwaway state root with the floors tests/conftest.py puts under a kernel load (the
 *  way file-comments.test.ts loads it). */
function servedScripts(plant: string): { pages: string[]; documents: string[]; scripts: Piece[]; plant: Array<[string, Piece["kind"], string]> } {
  const script = [
    "import json, os, sys",
    "sys.path.insert(0, os.path.join(sys.argv[1], 'tests'))",
    "os.chdir(sys.argv[1])",
    "import test_shell_source_check as t",
    "plant = sys.stdin.read()",
    "json.dump({'pages': list(t.SERVED_BUILDERS), 'documents': list(t._served_documents()), 'scripts': t._served_scripts(),",
    "           'plant': t._page_scripts(plant)}, sys.stdout)",
  ].join("\n");
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "romp-scopes-"));
  try {
    const env: NodeJS.ProcessEnv = {};
    for (const [k, v] of Object.entries(process.env)) if (!k.startsWith("ROMP_")) env[k] = v;
    Object.assign(env, { XDG_STATE_HOME: scratch, TMPDIR: scratch, ROMP_MANAGER_PORT: "1", ROMP_KERNEL_NO_OPEN: "1",
      ROMP_SERVE_TOKEN: "testtok", ROMP_CLAUDE_BIN: "/bin/false", ROMP_MODEL_CATALOG: "off", ROMP_CLI_SCOPE: "0" });
    const r = spawnSync("python3", ["-c", script, REPO], { input: plant, encoding: "utf8", env, timeout: 120000, maxBuffer: 64 << 20 });
    assert.equal(r.status, 0, "python3 loaded the kernel and read its pages: " + (r.stderr || r.error));
    return JSON.parse(r.stdout);
  } finally {
    fs.rmSync(scratch, { recursive: true, force: true });
  }
}

const PLANT = "<script>var a = 1; (eval)(s);</script><form onsubmit=\"with (o) { go(); } return false\"></form>" +
  "<a href=\"javascript:e\\u0076al(s)\">x</a>";

let served: ReturnType<typeof servedScripts> | undefined;
const got = () => (served ??= servedScripts(PLANT));
const byPage = () => {
  const m = new Map<string, Piece[]>();
  for (const p of got().scripts) m.set(p.page, [...(m.get(p.page) || []), p]);
  return m;
};

test("every script the kernel serves parses, and none holds a direct eval or a with statement", () => {
  const refusals = got().scripts.flatMap((p) => scopeRefusals(p.code, p.kind).map((why) => p.page + ", " + p.where + ": " + why));
  assert.deepEqual(refusals, [], "a direct eval, a with statement or an unreadable script on a page the kernel serves");
});

test("the census read every page SERVED_BUILDERS lists and every media SVG, and the scripts it exists for are among them", () => {
  const svgs = fs.readdirSync(path.join(EXT, "media")).filter((f) => f.endsWith(".svg")).map((f) => "/media/" + f);
  assert.ok(svgs.length > 0, "the media SVGs are listed");
  assert.deepEqual([...got().documents].sort(), [...got().pages, ...svgs].sort(), "the documents read: every listed page and media SVG");
  const pages = byPage();
  for (const page of got().pages) if (page !== "the too-large page") assert.ok((pages.get(page) || []).length > 0, page + " carries a script the census read");
  for (const page of ["/chat", "/feed", "/fleet", "/waiting", "/files", "/settings", "/timeline"])
    assert.ok((pages.get(page) || []).some((p) => p.code.includes("const fromShell=function(e){")), page + ": the shim's check is among the scripts read");
  assert.ok((pages.get("/") || []).some((p) => p.code.includes("window.__rompPaneSourceOk=function(e){")), "the shell's check is among them");
  assert.deepEqual((pages.get("the sign-in page") || []).map((p) => p.kind), ["handler"], "the sign-in form's onsubmit");
  assert.ok(got().pages.includes("/sw.js") && (pages.get("/sw.js") || []).length === 1, "/sw.js, read whole");
});

test("a page of our own, through the same reader and census: a direct eval in a script, a with statement in a handler and a direct eval in a javascript: URL are each refused", () => {
  assert.deepEqual(got().plant.map(([, kind]) => kind), ["script", "handler", "url"]);
  assert.deepEqual(got().plant.map(([, kind, code]) => scopeRefusals(code, kind).length), [1, 1, 1], "each planted script refused");
});

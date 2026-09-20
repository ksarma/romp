"""The link-drop driver's receiver walk and wait census over the compiler's PARSE of the driver (2026-09-20, round 5 of PR 857).

tests/test_federated_linkdrop_driver_bound.py requires every wait the driver places to draw on its budget and every call
on a playwright receiver to be one an allow-list names for that receiver's kind, because an auto-waiting read inherits
playwright's 30 s default that no budget caps. Its instruments there are regular expressions over the driver text, keyed
on a receiver written as a bare dotted name, and round 5's review measured that keying: fourteen spellings of the same
receiver (an object literal, an array, a ternary, `null || pages.feed`, an arrow's or a return's value, a page awaited
into a helper, optional chaining, bracket access, a space, a newline or a comment before the member, a second browser
from firefox) reached none of them, a member read followed by a call (`pages.feed.request.get(url)`) ended the walk's
chain silently, and a wait written `. waitFor`, `["goto"]` or `goto?.()` was no site to the wait census. The rule the
review gave: a census over a FORM is keyed on the property, or it parses, or its message says which spellings it checks.
This module parses.

THE PARSER. The typescript package under vscode-extension/node_modules (the extension's devDependency; 5.9.3 as written),
called from a small node helper (PARSE_HELPER) the census hands the sources to: `ts.createSourceFile(name, src, options,
setParentNodes, ScriptKind.JS)` on each, every source marked an ES module up front (the driver is one, with top-level
await; a synthetic cell without an import would otherwise parse `await (x)` as a call of a name), the
tree returned as JSON (each node its kind, its start and end offset into the source, its children in the compiler's
order, the text of an identifier or a literal, the operator of a binary or unary expression). Every position is the
compiler's and every line number is counted from it; no text is stripped or normalised, so a dot inside a string, a
comment, a template literal or a regular expression is not a member, and whitespace or a comment between a receiver
and its member is not a spelling. The alternative the pipeline already uses (ui/webview/writer-census.ts, the compiler's
parser in a node test; the compiler's comment ranges as a stripper in a sibling branch) is the same compiler; a node test
was not chosen because the census's tables and the arithmetic they serve live in the pytest module and the plants below
are pytest fixtures. esbuild exposes no tree (its API is build, transform and their sync forms).

WHY THIS FILE. CI's Python matrix installs no node deps, so the typescript package is absent there and a census that needs
it cannot run in tests/test_federated_linkdrop_driver_bound.py without a skip that CI never turns into a failure. The
vscode-extension job runs `npm ci` and then pytest over tests/test_*_browser.py and tests/test_*_served.py under
ROMP_SERVED_TESTS_REQUIRE=1, which turns a skip in those files into a failure carrying the skip's reason (tests/conftest.py).
This module takes the `_served` suffix for that job: on the matrix it skips with its reason, as every served lab does, and
in the served job it must run. It boots no kernel and drives no browser; it needs node and the extension's node_modules.
The regex census in the driver-bound module stays as the matrix's backstop, its docstring naming the spellings it checks
and this module as the instrument that reads the rest.

THE WALK. A receiver is known by its TYPE through the walk, never by its spelling. The roots: the destructuring of
`require("playwright")` names a browser type (chromium; firefox and webkit would be named the same way and refused by the
allow-list, which knows chromium alone), `chromium.launch(...)` is a browser, `browser.newContext(...)` a context,
`context.newPage(...)` a page, a page's or a locator's LOCATOR_MAKERS call a locator, `makeBudget(...)` the budget and
`budget.waitFor` read without a call the budget's poll. A type flows through `await`, parentheses, a ternary's or a
logical expression's branches, an array literal (a list of that type), an object literal's property (an object holding
it), a `const`, `let` or `var` declaration, an assignment, a destructuring from the playwright module, a helper's return
(its expression body or its `return` statements) and a helper's parameters (from the types of the arguments at each call
of it); a write of a receiver into a member of an object (`pages[app] = page`) makes that object a TABLE of the receiver's
type, whose every member read is one. Names resolve by function scope (a parameter or a declaration inside a helper shadows
the module's), and a name bound to two types in one scope is refused. Then every expression whose type is a receiver, a
table, a list or an object holding one must be CONSUMED by one of the shapes the walk follows: the object of a member
call (checked against the allow-list by kind, `evaluate` on a page only), a truth test (an if, a while, a for, a `!`, a
ternary's condition, a `&&` or `||`), a binding or an assignment, an argument to a helper the driver declares (its type
flows to the parameter) or to Object.keys (the table), an `await`, a return, a literal it is placed in, the iterable of a
for-of over a list. Anything else is refused by line and text: a member READ that is not itself called (`pages.feed.request`,
`pages.feed.keyboard`, `pages.feed.waitForFunction` bound to a name), a computed member (`locator(...)[mth]()`), a receiver
passed to a callee the walk does not follow (`Reflect.get`, `wf.call`, a member call on an untyped object), a receiver in
a template string, a comparison, a constructor, or any other parent. Enumerated on the safe side: the consumers are the
list, and a new shape the driver grows is a red here until it is read.

THE WAIT CENSUS reads the same tree: every call whose member name is a wait form (the WAIT_FORMS of the driver-bound
module: the navigations, the waitFor family, waitForTimeout) or whose callee is the budget's poll is a site, whatever
punctuation spells it (`. waitFor`, `["goto"]`, `goto?.()` are the same calls); a `timeout` option is read from the call's
object-literal argument by node, and must be exactly one budget.capped(...) call (CAPPED) as the whole value; a
waitForTimeout draws on the budget or is one of the two fixed dwells. A bare `waitFor(` is the poll only when the tree binds
that name to `budget.waitFor` in a scope the call sees; a bare wait-named call the tree binds to no poll is an unlisted
form. A wait outside playwright and the budget is refused by name: a timer (setTimeout, setInterval, setImmediate,
queueMicrotask, spelled bare or as a member, or bound to another name) or a `new Promise(...)` anywhere but the budget's own
`sleep`, and a `require` or an `import` of any module but the driver's own (playwright; node:module, node:fs). Disclosed,
the class the census cannot see: a wait spelled with none of those names, such as a busy loop inside a callback handed to
evaluate or waitForFunction, or Atomics.wait; the budget is a deadline and bounds none of it. The two fetches (ctl and
tunnelsStatus) stay the acknowledged driver_error road, pinned at two.

THE PLANTS. The review's thirty-six instances (the receiver shapes, the wait spellings, the timers, the second browser, the
controls) are a fixture here: each is one line inserted into the driver after `out.provBefore = await provText();`, run
through this census, and must be refused by the class the table names (a walk refusal, an unlisted call, an uncapped or
unlisted wait site, a third fetch), the two controls passing. Every one of them but the six the regex census already caught
passed the driver-bound module at the round-5 head; the review record outside the repo carries the before and after outcomes.

Synthetic: no kernel, no browser; node and the extension's node_modules only.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_federated_linkdrop_served as L               # noqa: E402  the driver: DRIVER (BUDGET_JS first)
import test_federated_linkdrop_driver_bound as B         # noqa: E402  the tables: WAIT_FORMS, CAPPED, FIXED_DWELLS, ALLOWED_CALLS, LOCATOR_MAKERS

# The helper node runs: argv[2] a JSON file of [{name, src}], argv[3] the directory whose node_modules holds the typescript
# package (resolved from there, so the helper can live anywhere). Prints {tsVersion, sources: [{name, diagnostics, tree}]}.
# A tree node is {k, s, e, c, t, op}: the kind's name (VariableStatement and the literal kinds spelled by their own names,
# where SyntaxKind's reverse map spells them by a range alias), start and end offsets into src, the children in forEachChild
# order (punctuation, keywords other than this/super/null/true/false, and the end-of-file marker as kind "Token"), the text
# of an identifier or a literal, the operator of a binary or unary expression.
PARSE_HELPER = r"""
const ts = require(require.resolve("typescript", { paths: [process.argv[3]] }));
const fs = require("fs");
const inputs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const kindName = (n) => {
  if (ts.isVariableStatement(n)) return "VariableStatement";
  if (ts.isNumericLiteral(n)) return "NumericLiteral";
  if (ts.isNoSubstitutionTemplateLiteral(n)) return "NoSubstitutionTemplateLiteral";
  if (ts.isTemplateTail(n)) return "TemplateTail";
  return ts.SyntaxKind[n.kind];
};
const EXPR_KW = new Set([ts.SyntaxKind.ThisKeyword, ts.SyntaxKind.SuperKeyword, ts.SyntaxKind.NullKeyword, ts.SyntaxKind.TrueKeyword, ts.SyntaxKind.FalseKeyword]);
const isTok = (n) => (n.kind >= ts.SyntaxKind.FirstPunctuation && n.kind <= ts.SyntaxKind.LastPunctuation)
  || (n.kind >= ts.SyntaxKind.FirstKeyword && n.kind <= ts.SyntaxKind.LastKeyword && !EXPR_KW.has(n.kind)) || n.kind === ts.SyntaxKind.EndOfFileToken;
function ser(n, sf) {
  if (isTok(n)) return { k: "Token", s: n.getStart(sf), e: n.getEnd(), t: ts.tokenToString(n.kind) || ts.SyntaxKind[n.kind] };
  const o = { k: kindName(n), s: n.getStart(sf), e: n.getEnd() };
  if (typeof n.text === "string" && (ts.isIdentifier(n) || ts.isPrivateIdentifier(n) || ts.isStringLiteralLike(n) || ts.isNumericLiteral(n) || ts.isTemplateLiteralToken(n))) o.t = n.text;
  if (ts.isBinaryExpression(n)) o.op = ts.tokenToString(n.operatorToken.kind);
  if (ts.isPrefixUnaryExpression(n) || ts.isPostfixUnaryExpression(n)) o.op = ts.tokenToString(n.operator);
  const c = [];
  ts.forEachChild(n, (ch) => { c.push(ser(ch, sf)); });
  if (c.length) o.c = c;
  return o;
}
// every source is an ES module (the driver is one, with top-level await): the indicator is set up front, so a top-level
// `await (x)` is the keyword and not a call of a name, which the parser's heuristic would make it in a script
const asModule = { languageVersion: ts.ScriptTarget.Latest, impliedNodeFormat: ts.ModuleKind.ESNext, setExternalModuleIndicator: (f) => { f.externalModuleIndicator = f; } };
const out = inputs.map(({ name, src }) => {
  const sf = ts.createSourceFile(name, src, asModule, true, ts.ScriptKind.JS);
  const diagnostics = (sf.parseDiagnostics || []).map((d) => ts.flattenDiagnosticMessageText(d.messageText, " "));
  return { name, diagnostics, tree: ser(sf, sf) };
});
process.stdout.write(JSON.stringify({ tsVersion: ts.version, sources: out }));
"""

# the calls that return a receiver of another kind; a page's or a locator's LOCATOR_MAKERS call returns a locator
MAKERS = {("chromium", "launch"): "browser", ("browser", "newContext"): "context", ("context", "newPage"): "page"}
WAIT_NAME = re.compile(r"goto|reload|goBack|goForward|waitFor\w*")
TIMERS = ("setTimeout", "setInterval", "setImmediate", "queueMicrotask")
BARE_CALLEES = ("Object.keys",)                    # the one callee a table may be passed to bare
IMPORTS_ALLOWED = ("node:module", "node:fs")       # the driver's own imports; any other module is a road the census does not know
REQUIRE_ALLOWED = ("playwright",)
FN_KINDS = ("ArrowFunction", "FunctionExpression", "FunctionDeclaration", "MethodDeclaration")
PASS_THROUGH = ("AwaitExpression", "ParenthesizedExpression", "NonNullExpression", "AsExpression", "SatisfiesExpression", "TypeAssertionExpression")
LOGICAL = ("||", "&&", "??")
AUX = ("budget", "poll")   # kinds the walk tracks that are no receiver
SHADOW = object()          # a declared name with no receiver type: it hides an outer binding of the same name


def parse_js(sources):
    """[(name, src)] through node and the typescript package under EXT: (tsVersion, {name: (diagnostics, tree)}). Skips, in
    the served labs' words, when node or the package is absent, so ROMP_SERVED_TESTS_REQUIRE=1 turns that into a failure."""
    if not shutil.which("node"):
        raise unittest.SkipTest("extension deps absent (npm ci not run here): the parsed census needs node")
    if not os.path.isdir(os.path.join(EXT, "node_modules", "typescript")):
        raise unittest.SkipTest("extension deps absent (npm ci not run here): the parsed census needs the typescript package under vscode-extension/node_modules")
    d = tempfile.mkdtemp(prefix="linkdrop-parse-")
    try:
        helper, inputs = os.path.join(d, "parse.cjs"), os.path.join(d, "in.json")
        with open(helper, "w", encoding="utf-8") as f:
            f.write(PARSE_HELPER)
        with open(inputs, "w", encoding="utf-8") as f:
            json.dump([{"name": n, "src": s} for n, s in sources], f)
        p = subprocess.run(["node", helper, inputs, EXT], capture_output=True, text=True, timeout=120)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    if p.returncode != 0:
        raise AssertionError("the parse helper failed under node: %s%s" % (p.stdout[-800:], p.stderr[-800:]))
    out = json.loads(p.stdout)
    return out["tsVersion"], {s["name"]: (s["diagnostics"], s["tree"]) for s in out["sources"]}


def receiverish(k):
    """Whether a kind must be consumed by a shape the walk follows: a receiver, a browser type, the playwright module, a
    table, a list of one, an object holding one. The budget, its poll and a helper are tracked but are no receiver."""
    if k is None or k is SHADOW or k in AUX:
        return False
    if isinstance(k, tuple):
        if k[0] == "fn":
            return False
        if k[0] == "table":
            return True
        if k[0] == "list":
            return receiverish(k[1])
        return any(receiverish(v) for _, v in k[1])   # record
    return True


def show(k):
    if isinstance(k, tuple):
        if k[0] == "fn":
            return "a helper"
        if k[0] == "record":
            return "an object holding {%s}" % ", ".join("%s: %s" % (p, show(v)) for p, v in sorted(k[1]))
        return "a %s of %s" % (k[0], show(k[1]))
    return "a %s" % k


class Walk:
    """The receiver walk by type and the wait census over one parsed source. After run(): `refusals` {(line, text, why)},
    `calls` [(kind, method, line)], `waits` [(form, timeouts, first_arg, line)], `fetches`, `imports` [(module, line)],
    `requires` [(module, line)], `poll_bindings` [(scope kind, line)]."""

    def __init__(self, src, tree):
        self.src, self.root = src, tree
        self.parent, self.nodes = {}, []
        self._link(tree, None)
        self.scopes = {}      # id(scope node) -> {name: kind or SHADOW}
        self.fn_params = {}   # id(fn node) -> [(name, fn node) or None per parameter]
        self.fn_ret = {}      # id(fn node) -> the kind its body returns, re-derived each round
        self.kinds = {}
        self.refusals = set()
        self.calls, self.waits, self.fetches, self.timers, self.imports, self.requires, self.poll_bindings = [], [], [], [], [], [], []

    # ---- the tree ----
    def _link(self, n, parent):
        self.parent[id(n)] = parent
        self.nodes.append(n)
        for c in n.get("c", []):
            self._link(c, n)

    @staticmethod
    def kids(n):
        return [c for c in n.get("c", []) if c["k"] != "Token"]

    def line(self, n):
        return self.src.count("\n", 0, n["s"]) + 1

    def text(self, n, width=100):
        t = self.src[n["s"]:n["e"]].strip()
        return t if len(t) <= width else t[:width - 3] + "..."

    def scope_of(self, n):
        p = self.parent[id(n)]
        while p is not None and p["k"] not in FN_KINDS and p["k"] != "SourceFile":
            p = self.parent[id(p)]
        return p if p is not None else self.root

    def lookup(self, name, n):
        s = self.scope_of(n)
        while s is not None:
            table = self.scopes.get(id(s), {})
            if name in table:
                return None if table[name] is SHADOW else table[name]
            s = None if s["k"] == "SourceFile" else self.scope_of(s)
        return None

    def refuse(self, n, why):
        self.refusals.add((self.line(n), self.text(n), why))

    def declare(self, scope, name):
        self.scopes.setdefault(id(scope), {}).setdefault(name, SHADOW)

    def bind(self, scope, name, k, at):
        if k is None:
            return
        table = self.scopes.setdefault(id(scope), {})
        old = table.get(name)
        if old is None or old is SHADOW:
            table[name] = k
            self.changed = True
        elif old != k:
            self.refuse(at, "%s is bound to %s and to %s in one scope: the walk follows a name by one type" % (name, show(old), show(k)))

    def is_reference(self, n):
        """An identifier that reads a binding, as against one that names a property, a declaration or an import."""
        p = self.parent[id(n)]
        if p is None:
            return False
        k, kids = p["k"], self.kids(p)
        if k == "PropertyAccessExpression" and kids[1] is n:
            return False
        if k in ("PropertyAssignment", "VariableDeclaration", "Parameter", "FunctionDeclaration", "FunctionExpression", "MethodDeclaration") and kids[0] is n:
            return False
        return k not in ("BindingElement", "ImportClause", "ImportSpecifier", "NamespaceImport", "LabeledStatement", "BreakStatement", "ContinueStatement")

    # ---- the kinds ----
    def union(self, n, *ks):
        s = []
        for k in ks:
            if k is not None and k not in s:
                s.append(k)
        if not s:
            return None
        if len(s) == 1:
            return s[0]
        self.refuse(n, "one expression yields %s: the walk follows an expression by one type" % " and ".join(show(k) for k in s))
        return None

    def kind_of(self, n):
        if id(n) not in self.kinds:
            self.kinds[id(n)] = self._kind(n)
        return self.kinds[id(n)]

    def _kind(self, n):
        k, kids = n["k"], self.kids(n)
        if k == "Identifier":
            return self.lookup(n["t"], n) if self.is_reference(n) else None
        if k in PASS_THROUGH:
            return self.kind_of(kids[0]) if kids else None
        if k == "CallExpression":
            return self._call(n, kids)
        if k == "PropertyAccessExpression":
            return self._member(self.kind_of(kids[0]), kids[1].get("t"))
        if k == "ElementAccessExpression":
            ko, arg = self.kind_of(kids[0]), kids[1]
            if isinstance(ko, tuple) and ko[0] in ("table", "list"):
                return ko[1]
            return self._member(ko, arg["t"]) if arg["k"] in ("StringLiteral", "NoSubstitutionTemplateLiteral") else None
        if k == "ConditionalExpression":
            return self.union(n, self.kind_of(kids[1]), self.kind_of(kids[2]))
        if k == "BinaryExpression":
            op = n.get("op")
            if op in LOGICAL:
                return self.union(n, self.kind_of(kids[0]), self.kind_of(kids[1]))
            if op == ",":
                return self.kind_of(kids[1])
            if op == "=":
                kr = self.kind_of(kids[1])
                self._assign(n, kids[0], kr)
                return kr
            return None
        if k == "ObjectLiteralExpression":
            props = []
            for c in kids:
                ck = self.kids(c)
                if c["k"] == "PropertyAssignment" and ck[0].get("t") is not None:
                    props.append((ck[0]["t"], self.kind_of(ck[1])))
                elif c["k"] == "ShorthandPropertyAssignment":
                    props.append((ck[0]["t"], self.lookup(ck[0]["t"], c)))
            props = [(name, v) for name, v in props if receiverish(v)]
            return ("record", frozenset(props)) if props else None
        if k == "ArrayLiteralExpression":
            u = self.union(n, *[self.kind_of(c) for c in kids])
            return ("list", u) if u is not None else None
        if k in FN_KINDS:
            return self._fn(n, kids)
        if k == "VariableDeclaration":
            self._declare(n, kids)
            return None
        if k == "Parameter":
            if kids and kids[0]["k"] == "Identifier":
                self.declare(self.scope_of(kids[0]), kids[0]["t"])
                if len(kids) > 1:
                    self.bind(self.scope_of(kids[0]), kids[0]["t"], self.kind_of(kids[1]), n)
            return None
        if k == "ForOfStatement":
            ki = self.kind_of(kids[1])
            if isinstance(ki, tuple) and ki[0] == "list" and kids[0]["k"] == "VariableDeclarationList":
                for d in self.kids(kids[0]):
                    dk = self.kids(d)
                    if dk and dk[0]["k"] == "Identifier":
                        self.bind(self.scope_of(dk[0]), dk[0]["t"], ki[1], d)
            return None
        if k == "ImportDeclaration":
            spec = next((c for c in kids if c["k"] == "StringLiteral"), None)
            if spec is not None:
                self.imports.append((spec["t"], self.line(n)))
            return None
        return None

    def _member(self, ko, name):
        if name is None:
            return None
        if isinstance(ko, tuple):
            if ko[0] == "table":
                return ko[1]
            if ko[0] == "record":
                return dict(ko[1]).get(name)
            return None
        if ko == "playwright":
            return name
        if ko == "budget":
            return "poll" if name == "waitFor" else None
        return None

    def _call(self, n, kids):
        callee, args = kids[0], kids[1:]
        line = self.line(n)
        if callee["k"] == "Identifier":
            name = callee["t"]
            if name == "require":
                mod = args[0]["t"] if args and args[0]["k"] == "StringLiteral" else None
                self.requires.append((mod, line))
                return "playwright" if mod == "playwright" else None
            if name == "makeBudget":
                return "budget"
            if name == "fetch":
                self.fetches.append(line)
            kc = self.lookup(name, callee)
            if kc == "poll":
                self.waits.append(self._site("waitFor", n, args))
                return None
            if isinstance(kc, tuple) and kc[0] == "fn":
                self._flow(kc[1], args, n)
                return self.fn_ret.get(kc[1])
            if WAIT_NAME.fullmatch(name):
                self.waits.append(self._site(name + " (a bare name the tree binds to no poll)", n, args))
            return None
        if callee["k"] in ("PropertyAccessExpression", "ElementAccessExpression"):
            ck = self.kids(callee)
            ko = self.kind_of(ck[0])
            method = ck[1].get("t") if callee["k"] == "PropertyAccessExpression" or ck[1]["k"] in ("StringLiteral", "NoSubstitutionTemplateLiteral") else None
            if method is None:
                if receiverish(ko):
                    self.refuse(n, "a computed member call on %s the walk cannot name" % show(ko))
                return None
            if isinstance(ko, str) and receiverish(ko):
                self.calls.append((ko, method, line))
                if WAIT_NAME.fullmatch(method):
                    self.waits.append(self._site(".waitFor" if method == "waitFor" else method, n, args))
                if method in B.LOCATOR_MAKERS and ko in ("page", "locator"):
                    return "locator"
                return MAKERS.get((ko, method))
            if ko == "budget":
                if method == "waitFor":
                    self.waits.append(self._site("waitFor", n, args))
                elif method not in ("capped", "left"):
                    self.refuse(n, "a call on the budget the census does not know: %s" % method)
                return None
            if receiverish(ko):
                self.refuse(n, "a call on %s, which is no receiver a method is called on" % show(ko))
                return None
            if WAIT_NAME.fullmatch(method):
                self.waits.append(self._site(".waitFor" if method == "waitFor" else method, n, args))
            return None
        return None

    def _site(self, form, call, args):
        """A wait site: (form, the texts of every `timeout` property in the call's object-literal arguments, the first
        argument's text, line). A shorthand `{ timeout }` is a property whose value is a variable, reported as its name."""
        timeouts = []
        for a in args:
            if a["k"] == "ObjectLiteralExpression":
                for prop in self.kids(a):
                    pk = self.kids(prop)
                    if prop["k"] == "PropertyAssignment" and pk[0].get("t") == "timeout":
                        timeouts.append(self.text(pk[1], 10 ** 6))
                    elif prop["k"] == "ShorthandPropertyAssignment" and pk[0].get("t") == "timeout":
                        timeouts.append("timeout (a shorthand property, its value a variable)")
        return (form, timeouts, self.text(args[0], 10 ** 6) if args else "", self.line(call))

    def _flow(self, fn_id, args, at):
        params = self.fn_params.get(fn_id)
        if params is None:
            return
        for i, a in enumerate(args):
            ka = self.kind_of(a)
            if ka is None:
                continue
            if i >= len(params) or params[i] is None:
                self.refuse(at, "%s passed to a helper parameter the walk cannot name (a rest or destructured parameter, or one past the list)" % show(ka))
                continue
            self.bind(params[i][1], params[i][0], ka, at)

    def _fn(self, n, kids):
        params, body = [], None
        for c in kids:
            if c["k"] == "Parameter":
                ck = self.kids(c)
                rest = any(t["k"] == "Token" and t.get("t") == "..." for t in c.get("c", []))
                params.append((ck[0]["t"], n) if ck and ck[0]["k"] == "Identifier" and not rest else None)
            elif c["k"] != "Identifier":
                body = c
        self.fn_params[id(n)] = params
        if body is None:
            ret = None
        elif body["k"] != "Block":
            ret = self.kind_of(body)
        else:
            ret = self.union(n, *[self.kind_of(self.kids(r)[0]) for r in self._returns(body) if self.kids(r)])
        self.fn_ret[id(n)] = ret
        if n["k"] == "FunctionDeclaration" and kids and kids[0]["k"] == "Identifier":
            self.bind(self.scope_of(n), kids[0]["t"], ("fn", id(n)), n)
        return ("fn", id(n))

    def _returns(self, body):
        out = []

        def walk(m):
            for c in self.kids(m):
                if c["k"] in FN_KINDS:
                    continue
                if c["k"] == "ReturnStatement":
                    out.append(c)
                walk(c)
        walk(body)
        return out

    def _declare(self, n, kids):
        scope, name = self.scope_of(n), kids[0]
        if name["k"] == "Identifier":
            self.declare(scope, name["t"])
        else:
            for el in self.kids(name):
                ek = self.kids(el)
                if ek and ek[-1]["k"] == "Identifier":
                    self.declare(scope, ek[-1]["t"])
        if len(kids) < 2:
            return
        k = self.kind_of(kids[1])
        if k is None:
            return
        if name["k"] == "Identifier":
            self.bind(scope, name["t"], k, n)
            if k == "poll":
                self.poll_bindings.append((self.scope_of(n)["k"], self.line(n)))
        elif name["k"] == "ObjectBindingPattern":
            for el in self.kids(name):
                ek = self.kids(el)
                prop, target = (ek[0]["t"], ek[-1]) if len(ek) > 1 else (ek[0].get("t"), ek[0])
                if target["k"] == "Identifier":
                    self.bind(scope, target["t"], self._member(k, prop), n)
        elif name["k"] == "ArrayBindingPattern" and isinstance(k, tuple) and k[0] == "list":
            for el in self.kids(name):
                ek = self.kids(el)
                if ek and ek[0]["k"] == "Identifier":
                    self.bind(scope, ek[0]["t"], k[1], n)

    def _assign(self, n, left, kr):
        if kr is None:
            return
        if left["k"] == "Identifier":
            self.bind(self.scope_of(left), left["t"], kr, n)
            return
        if left["k"] in ("PropertyAccessExpression", "ElementAccessExpression"):
            obj = self.kids(left)[0]
            if obj["k"] == "Identifier":
                ko = self.lookup(obj["t"], obj)
                if ko is None and receiverish(kr):
                    self.bind(self.scope_of(obj), obj["t"], ("table", kr), n)   # a receiver written into a member: the object is a table of them
                    return
                if isinstance(ko, tuple) and ko[0] == "table":
                    if ko[1] != kr:
                        self.refuse(n, "%s written into %s" % (show(kr), show(ko)))
                    return
        if receiverish(kr):
            self.refuse(n, "%s assigned to a target the walk does not follow" % show(kr))

    # ---- the passes ----
    def run(self, rounds=40):
        """Type the tree to a fixpoint (bindings grow until a round adds none), then classify every consumer."""
        for _ in range(rounds):
            self.changed = False
            self.kinds = {}
            self.calls, self.waits, self.fetches, self.imports, self.requires, self.poll_bindings = [], [], [], [], [], []
            self.refusals = set()
            for n in self.nodes:
                self.kind_of(n)
            if not self.changed:
                break
        else:
            self.refuse(self.root, "the walk did not converge in %d rounds" % rounds)
        for n in self.nodes:
            k = self.kind_of(n)
            if receiverish(k):
                self._consume(n, k)
        self._outside_playwright()
        return self

    def _consume(self, n, k):
        p = self.parent[id(n)]
        if p is None:
            return
        pk, pkids = p["k"], self.kids(p)
        gp = self.parent[id(p)]
        if pk in ("PropertyAccessExpression", "ElementAccessExpression") and pkids[0] is n:
            if isinstance(k, tuple) or k == "playwright":
                return   # a table's, a list's, a record's or the playwright module's member is typed by _member
            called = gp is not None and gp["k"] == "CallExpression" and self.kids(gp)[0] is p
            named = pk == "PropertyAccessExpression" or pkids[1]["k"] in ("StringLiteral", "NoSubstitutionTemplateLiteral")
            if called and named:
                return
            if named:
                return self.refuse(p, "a member read on %s that is not itself called (its value is of a type the walk does not know)" % show(k))
            return self.refuse(p, "a computed member on %s the walk cannot name" % show(k))
        if pk == "CallExpression":
            if pkids[0] is n:
                return self.refuse(p, "%s called as a function" % show(k))
            callee = pkids[0]
            ctext = self.src[callee["s"]:callee["e"]]
            if ctext in BARE_CALLEES and isinstance(k, tuple) and k[0] == "table":
                return
            kc = self.lookup(callee["t"], callee) if callee["k"] == "Identifier" else None
            if isinstance(kc, tuple) and kc[0] == "fn":
                return   # the argument's type flowed to the helper's parameter (_flow)
            return self.refuse(p, "%s passed to %s, a callee the walk does not follow" % (show(k), ctext))
        if pk == "VariableDeclaration" and pkids[-1] is n:
            target = pkids[0]
            if target["k"] == "Identifier":
                return
            if target["k"] == "ObjectBindingPattern" and (k == "playwright" or isinstance(k, tuple) and k[0] in ("table", "record")):
                return
            if target["k"] == "ArrayBindingPattern" and isinstance(k, tuple) and k[0] == "list":
                return
            return self.refuse(p, "%s destructured by a pattern the walk does not follow" % show(k))
        if pk == "BinaryExpression":
            if p.get("op") in LOGICAL or p.get("op") in ("=", ","):
                return   # a branch the expression inherits; an assignment's target or value (_assign judged the target)
            return self.refuse(p, "%s in a %s expression" % (show(k), p.get("op")))
        if pk == "ExpressionStatement" and n["k"] == "BinaryExpression" and n.get("op") == "=":
            return
        if pk in PASS_THROUGH or pk in ("ConditionalExpression", "ArrayLiteralExpression", "PropertyAssignment", "ShorthandPropertyAssignment", "ReturnStatement", "Parameter"):
            return
        if pk == "PrefixUnaryExpression" and p.get("op") == "!":
            return
        if pk in ("IfStatement", "WhileStatement", "DoStatement", "ForStatement") and n["k"] != "Block":
            return
        if pk in FN_KINDS and pkids[-1] is n:
            return
        if pk == "ForOfStatement" and pkids[1] is n:
            if isinstance(k, tuple) and k[0] == "list":
                return
            return self.refuse(p, "%s iterated" % show(k))
        return self.refuse(p, "%s reaches a %s the walk does not follow" % (show(k), pk))

    def _outside_playwright(self):
        """A timer name (bare, as a member, or bound to another name) or a promise constructor anywhere but the budget's own
        `sleep` property; a require or an import of a module the driver does not own."""
        def under_sleep(n):
            p = self.parent[id(n)]
            while p is not None:
                if p["k"] == "PropertyAssignment" and self.kids(p)[0].get("t") == "sleep":
                    q = self.parent[id(p)]
                    while q is not None:
                        if q["k"] == "CallExpression" and self.kids(q)[0].get("t") == "makeBudget":
                            return True
                        q = self.parent[id(q)]
                p = self.parent[id(p)]
            return False
        why = "a wait outside playwright and the budget (a timer or a promise constructor that is not the budget's sleep)"
        for n in self.nodes:
            if n["k"] == "Identifier" and n["t"] in TIMERS and not under_sleep(n):
                self.refuse(self.parent[id(n)] or n, why)
            elif n["k"] == "NewExpression" and self.kids(n) and self.kids(n)[0].get("t") == "Promise" and not under_sleep(n):
                self.refuse(n, why)
        for mod, line in self.imports:
            if mod not in IMPORTS_ALLOWED:
                self.refusals.add((line, "import ... from %r" % mod, "an import of a module the census does not know"))
        for mod, line in self.requires:
            if mod not in REQUIRE_ALLOWED:
                self.refusals.add((line, "require(%r)" % (mod,), "a require of a module the census does not know"))


def census(src, tree):
    """The walk's verdicts over one parsed driver: refusals, the unlisted receiver calls, the wait census's uncapped and
    unlisted sites and its fixed dwells, the fetch count, the calls and waits seen."""
    w = Walk(src, tree).run()
    unlisted = sorted({(kind, method, line) for kind, method, line in w.calls if method not in B.ALLOWED_CALLS.get(kind, ())})
    unlisted_waits = sorted({(form, line) for form, _, _, line in w.waits if form not in B.WAIT_FORMS})
    uncapped, dwells = [], set()
    for form, timeouts, first, line in w.waits:
        rule = B.WAIT_FORMS.get(form)
        if rule == "timeout":
            if len(timeouts) != 1 or not B.CAPPED.fullmatch(timeouts[0]):
                uncapped.append((line, form, timeouts or "no timeout key (playwright's 30 s default, which no budget caps)"))
        elif rule == "dwell":
            if B.CAPPED.fullmatch(first):
                continue
            dwells.add(first)
            if first not in B.FIXED_DWELLS:
                uncapped.append((line, form, first))
    return {"refusals": sorted(w.refusals), "unlisted": unlisted, "unlisted_waits": unlisted_waits, "uncapped": uncapped,
            "dwells": sorted(dwells), "fetches": len(w.fetches), "calls": w.calls, "waits": w.waits, "poll_bindings": w.poll_bindings, "walk": w}


def verdict(c):
    """One word for a census over a planted driver: 'refused' (the walk), 'unlisted' (a receiver call the allow-list does not
    name), 'wait' (an uncapped or unlisted wait site), 'fetch' (a third fetch), else 'passed'."""
    if c["refusals"]:
        return "refused"
    if c["unlisted"]:
        return "unlisted"
    if c["uncapped"] or c["unlisted_waits"]:
        return "wait"
    if c["fetches"] != 2:
        return "fetch"
    return "passed"


ANCHOR = "  out.provBefore = await provText();\n"   # the plants go one line after this, inside the driver's try block
# The review's plants (round 5 of PR 857, the owner's read-only prep over the round-4 head): one JS line each, and the
# class of red this census must give it. `passed` marks the two controls. Every row but the six the regex census caught
# (var-held-page, var-held-locator, template-string, paren-receiver, space-before-dot-wait, third-fetch, set-default-timeout,
# bracket-page-control) passed the driver-bound module at the round-5 head with the plant in place.
PLANTS = (
    ("var-held-page", "const p = pages.feed; await p.locator(cfg.provSel).textContent();", "unlisted"),
    ("var-held-locator", "const Lx = pages.feed.locator(cfg.provSel); await Lx.textContent();", "unlisted"),
    ("optional-chain", "await pages.feed?.locator(cfg.provSel)?.textContent();", "unlisted"),
    ("bracket-method", 'await pages.feed["locator"](cfg.provSel)["textContent"]();', "unlisted"),
    ("bracket-goto", 'await pages.feed["goto"](cfg.urls[APPS[0]]);', "wait"),
    ("computed-method", 'const mth = "textContent"; await pages.feed.locator(cfg.provSel)[mth]();', "refused"),
    ("space-before-member", "await pages .feed.locator(cfg.provSel).textContent();", "unlisted"),
    ("newline-chain", "await pages.feed\n    .locator(cfg.provSel)\n    .textContent();", "unlisted"),
    ("paren-receiver", "await (pages.feed).locator(cfg.provSel).textContent();", "unlisted"),
    ("block-comment", "await pages.feed/* x */.locator(cfg.provSel).textContent();", "unlisted"),
    ("member-then-call", "await pages.feed.request.get(cfg.tunnelsUrl);", "refused"),
    ("keyboard-member", 'await pages.feed.keyboard.insertText("x");', "refused"),
    ("object-literal", "const box = { p: pages.feed }; await box.p.locator(cfg.provSel).textContent();", "unlisted"),
    ("array-for-of", "for (const p of [pages.feed]) await p.locator(cfg.provSel).textContent();", "unlisted"),
    ("ternary", "const p = cfg.stripCaps ? pages.feed : pages.waiting; await p.locator(cfg.provSel).textContent();", "unlisted"),
    ("logical-or", "const p = null || pages.feed; await p.locator(cfg.provSel).textContent();", "unlisted"),
    ("arrow-return", "const getP = () => pages.feed; await getP().locator(cfg.provSel).textContent();", "unlisted"),
    ("return-stmt", "const getP2 = () => { return pages.feed; }; await getP2().locator(cfg.provSel).textContent();", "unlisted"),
    ("await-wrapped-pass", "const readT = async (p) => p.locator(cfg.provSel).textContent(); await readT(await pages.feed);", "unlisted"),
    ("param-default", "const readD = async (p = pages.feed) => p.locator(cfg.provSel).textContent(); await readD();", "unlisted"),
    ("space-after-dot-wait", "await pages.feed.locator(cfg.provSel). waitFor({});", "wait"),
    ("space-before-dot-wait", "await pages.feed.locator(cfg.provSel) .waitFor({});", "wait"),
    ("optional-call-goto", "await pages.feed.goto?.(cfg.urls[APPS[0]]);", "wait"),
    ("raw-settimeout", "await new Promise((r) => setTimeout(r, 100000));", "refused"),
    ("evaluate-promise", "await pages.feed.evaluate(() => new Promise((r) => setTimeout(r, 100000)));", "refused"),
    ("method-ref-binding", "const wf = pages.feed.waitForFunction; await wf.call(pages.feed, () => true, null, {});", "refused"),
    ("reflect-get", 'await Reflect.get(pages.feed, "locator").call(pages.feed, cfg.provSel).textContent();', "refused"),
    ("comma-operator", "await (0, pages.feed.locator)(cfg.provSel).textContent();", "refused"),
    ("third-fetch", "await fetch(cfg.tunnelsUrl);", "fetch"),
    ("set-default-timeout", "pages.feed.setDefaultTimeout(60000);", "unlisted"),
    ("bracket-page-control", 'await pages["feed"].locator(cfg.provSel).textContent();', "unlisted"),
    ("count-control", "const nProv = await pages.feed.locator(cfg.provSel).count();", "passed"),
    ("template-string", "const tpl = `${await pages.feed.locator(cfg.provSel).textContent()}`;", "unlisted"),
    ("paren-receiver-noawait", "const prn = (pages.feed).locator(cfg.provSel).textContent(); await prn;", "unlisted"),
    ("firefox-launch", 'const { firefox } = require("playwright"); const b2 = await firefox.launch({}); const c2 = await b2.newContext({}); const p2 = await c2.newPage(); await p2.locator(cfg.provSel).textContent();', "unlisted"),
    ("timer-as-member", "await new Promise((r) => globalThis.setTimeout(r, 100000));", "refused"),
    ("timer-import", 'import { setTimeout as delay } from "node:timers/promises"; await delay(100000);', "refused"),
    ("identity-control", "", "passed"),
)


def planted(js):
    """The driver with one plant line after ANCHOR (the unmodified driver for an empty plant)."""
    if not js:
        return L.DRIVER
    return L.DRIVER.replace(ANCHOR, ANCHOR + "  " + js + "\n")


class TheDriverParsed(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        if L.DRIVER.count(ANCHOR) != 1:
            raise AssertionError("the plants' anchor line is not exactly once in the driver: %d" % L.DRIVER.count(ANCHOR))
        sources = [("driver.mjs", L.DRIVER)] + [(name, planted(js)) for name, js, _ in PLANTS if js]
        cls.ts_version, cls.trees = parse_js(sources)

    def _census(self, name, src):
        diagnostics, tree = self.trees[name]
        self.assertEqual(diagnostics, [], "%s parses clean as a JS module under typescript %s: %r" % (name, self.ts_version, diagnostics))
        return census(src, tree)

    def test_the_driver_walks_clean_and_every_wait_draws_on_the_budget(self):
        """The census over the driver as written: every receiver-typed expression is consumed by a shape the walk follows
        (no refusal), every call on a receiver is one ALLOWED_CALLS names for its kind, the fourteen (kind, method) pairs the
        driver makes today are all seen (the walk is not vacuous), every wait site is a listed form whose timeout is one
        budget.capped(...) call or a fixed dwell the arithmetic counts, the five forms the driver uses are all seen, the
        bare `waitFor(` sites are the poll because the module scope binds that name to `budget.waitFor` exactly once, no
        timer or promise constructor sits outside the budget's sleep, the driver imports and requires its own modules only,
        and the two fetches stand."""
        c = self._census("driver.mjs", L.DRIVER)
        self.assertEqual(c["refusals"], [], "a receiver, or a table, list or object holding one, reaches a shape the walk does not follow (a member read that "
                                            "is not called, a computed member, a callee the driver does not declare, a template, a comparison, a constructor), "
                                            "so a call on it would be invisible to the allow-list; or a wait or a module outside playwright and the budget: %r" % (c["refusals"],))
        self.assertEqual(c["unlisted"], [], "a call on a playwright receiver that ALLOWED_CALLS does not name for its kind (an auto-waiting read inherits playwright's "
                                            "30 s default, which no budget caps; a call known not to wait is added there by receiver kind, a wait goes to WAIT_FORMS): %r" % (c["unlisted"],))
        self.assertEqual({(kind, name) for kind, name, _ in c["calls"]},
                         {("page", "locator"), ("page", "evaluate"), ("page", "goto"), ("page", "waitForFunction"), ("page", "waitForTimeout"), ("page", "on"),
                          ("page", "addInitScript"), ("locator", "first"), ("locator", "count"), ("locator", "waitFor"), ("context", "newPage"),
                          ("browser", "newContext"), ("browser", "close"), ("chromium", "launch")},
                         "the walk is not vacuous: every receiver call the driver makes today is seen, by kind, and nothing else (a new pair is added here with its allow-list entry)")
        self.assertEqual(c["unlisted_waits"], [], "a wait form WAIT_FORMS does not list, or a bare wait-named call the tree binds to no poll: %r" % (c["unlisted_waits"],))
        self.assertEqual(c["uncapped"], [], "every wait the driver places draws on the budget (its timeout, or its dwell, is exactly one budget.capped(...) call "
                                            "and nothing more) or is a fixed dwell driver_worst_case_s counts (%r); these do neither: %r" % (B.FIXED_DWELLS, c["uncapped"]))
        self.assertEqual(c["dwells"], sorted(B.FIXED_DWELLS), "the fixed dwells the driver places are exactly the two the arithmetic counts: %r" % (c["dwells"],))
        self.assertLessEqual({"goto", "waitForFunction", ".waitFor", "waitForTimeout", "waitFor"}, {form for form, _, _, _ in c["waits"]},
                             "the wait census is not vacuous: the forms the driver uses today are all seen: %r" % (sorted({form for form, _, _, _ in c["waits"]}),))
        self.assertEqual(c["poll_bindings"], [("SourceFile", L.DRIVER.count("\n", 0, L.DRIVER.index("const waitFor = budget.waitFor;")) + 1)],
                         "the module scope binds `waitFor` to the budget's poll exactly once, the alias the bare waitFor( sites read: %r" % (c["poll_bindings"],))
        self.assertEqual(c["fetches"], 2, "the driver's two fetches (ctl and tunnelsStatus) carry no timeout: the acknowledged driver_error road, DRIVER_TIMEOUT_S, "
                                          "which the arithmetic does not count; a third fetch is a new uncounted wait")
        self.assertGreaterEqual(len(c["waits"]), 16, "the census saw the driver's wait sites (16 at the round-5 head): %d" % len(c["waits"]))

    def test_the_walk_types_a_receiver_however_it_is_reached_and_refuses_what_it_cannot_follow(self):
        """The instrument by cell, over synthetic sources parsed the same way: the roots and the makers; a page through a
        binding, an object literal, an array and a for-of, a ternary, `null ||`, an arrow's and a return's value, an awaited
        argument to a helper (its parameter typed from the call), a default parameter; the page table by write, read by name
        and by bracket; a parameter shadows the module's binding of the same name; a name bound to two types is refused; a
        member read not called, a computed member, a pass to an unknown callee, a template, a comparison and a constructor
        are refused; a bare waitFor is the poll only where the tree binds it; a second browser type is seen by its name."""
        root = 'const { chromium } = require("playwright"); const context = await (await chromium.launch({})).newContext({}); const pages = {}; pages[app] = await context.newPage();\n'
        cells = {
            "roots": 'const { chromium } = require("playwright"); const b = await chromium.launch({}); const c = await b.newContext({}); const p = await c.newPage(); await p.locator(s).first().waitFor({ timeout: budget.capped(x) });',
            "table": root + "for (const app of APPS) { const page = await context.newPage(); pages[app] = page; } await pages.feed.locator(s).count(); await pages[app].goto(u, { timeout: budget.capped(x) }); for (const a of Object.keys(pages)) {}",
            "record-list-ternary": root + "const box = { p: pages.feed }; await box.p.locator(s).count(); for (const q of [pages.feed]) await q.locator(s).count(); const r = cfg.x ? pages.feed : pages.waiting; await r.locator(s).count(); const t = null || pages.feed; await t.locator(s).count();",
            "helpers": root + "const getP = () => pages.feed; await getP().locator(s).count(); const getQ = () => { return pages.feed; }; await getQ().locator(s).count(); const read = async (p) => p.locator(s).count(); await read(await pages.feed); const readD = async (p = pages.feed) => p.locator(s).count(); await readD();",
            "shadow": root + "const p = pages.feed; const outcome = (name, p) => p.then(() => true); await p.locator(s).count();",
            "poll": "const budget = makeBudget({}); const waitFor = budget.waitFor; await waitFor(async () => true, 1000, \"w\"); await budget.waitFor(fn, 1, \"w\"); const inner = () => { const waitFor = async () => true; return waitFor(); };",
        }
        trees = parse_js(list(cells.items()))[1]
        for name, src in cells.items():
            with self.subTest(cell=name):
                self.assertEqual(trees[name][0], [], "the cell parses clean: %r" % (trees[name][0],))
                c = census(src, trees[name][1])
                self.assertEqual(c["refusals"], [], "the cell's every receiver is consumed by a shape the walk follows: %r" % (c["refusals"],))
                self.assertEqual(c["unlisted"], [], "the cell's every receiver call is allowed: %r" % (c["unlisted"],))
                self.assertEqual(c["uncapped"], [], "the cell's every wait is capped: %r" % (c["uncapped"],))
        seen = census(cells["roots"], trees["roots"][1])["calls"]
        self.assertEqual([(k, m) for k, m, _ in seen], [("chromium", "launch"), ("browser", "newContext"), ("context", "newPage"), ("page", "locator"), ("locator", "first"), ("locator", "waitFor")],
                         "the roots and the makers type each call by the receiver it is chained on")
        seen = [(k, m) for k, m, ln in census(cells["table"], trees["table"][1])["calls"] if ln > 1]
        self.assertEqual(set(seen), {("context", "newPage"), ("page", "locator"), ("locator", "count"), ("page", "goto")}, "the table's members are pages, by name and by bracket")
        seen = [(k, m) for k, m, ln in census(cells["record-list-ternary"], trees["record-list-ternary"][1])["calls"] if ln > 1]
        self.assertEqual(seen.count(("page", "locator")), 4, "a page reached through an object literal, an array, a ternary and `null ||` is a page: %r" % (seen,))
        seen = [(k, m) for k, m, ln in census(cells["helpers"], trees["helpers"][1])["calls"] if ln > 1]
        self.assertEqual(seen.count(("page", "locator")), 4, "a page returned from a helper, awaited into one, or a helper's default parameter is a page: %r" % (seen,))
        seen = [(k, m) for k, m, ln in census(cells["shadow"], trees["shadow"][1])["calls"] if ln > 1]
        self.assertEqual(seen, [("page", "locator"), ("locator", "count")], "outcome's parameter p shadows the module's p: p.then is no page call: %r" % (seen,))
        w = census(cells["poll"], trees["poll"][1])
        self.assertEqual([(f, ln) for f, _, _, ln in w["waits"]], [("waitFor", 1), ("waitFor", 1)], "the bare call and the receiver call are the poll; inner's waitFor is its own function and no site")
        self.assertEqual(w["poll_bindings"], [("SourceFile", 1)])
        refused = {
            "member-read": ("await pages.feed.request.get(u);", "a member read on a page that is not itself called"),
            "member-bound": ("const wf = pages.feed.waitForFunction;", "a member read on a page that is not itself called"),
            "computed": ("await pages.feed.locator(s)[mth]();", "a computed member"),
            "unknown-callee": ("await read(pages.feed);", "a page passed to read, a callee the walk does not follow"),
            "member-callee": ("await Reflect.get(pages.feed, \"locator\");", "a page passed to Reflect.get"),
            "template": ("const t = `${pages.feed}`;", "a page reaches a TemplateSpan"),
            "comparison": ("if (pages.feed === x) {}", "a page in a === expression"),
            "constructor": ("const w = new Wrapper(pages.feed);", "a page reaches a NewExpression"),
            "two-types": ("let v = pages.feed; v = pages.feed.locator(s);", "v is bound to a page and to a locator"),
            "list-iterated": ("for (const k of pages) {}", "a table of a page iterated"),
            "table-call": ("await pages.locator(s);", "a call on a table of a page"),
            "bare-wait": ("await waitFor(fn, 1, \"w\");", None),
            "second-browser": ('const { firefox } = require("playwright"); await firefox.launch({});', None),
            "timer": ("await new Promise((r) => setTimeout(r, 5));", "a wait outside playwright and the budget"),
            "timer-member": ("globalThis.setTimeout(f, 5);", "a wait outside playwright and the budget"),
            "timer-bound": ("const st = setTimeout;", "a wait outside playwright and the budget"),
            "foreign-require": ('const cp = require("child_process");', "a require of a module the census does not know"),
            "foreign-import": ('import { setTimeout as delay } from "node:timers/promises";', "an import of a module the census does not know"),
        }
        trees = parse_js([(name, root + src) for name, (src, _) in refused.items()])[1]
        for name, (src, token) in refused.items():
            with self.subTest(refused=name):
                c = census(root + src, trees[name][1])
                if token is None:
                    if name == "bare-wait":
                        self.assertEqual(c["unlisted_waits"], [("waitFor (a bare name the tree binds to no poll)", 2)], c["waits"])
                    else:
                        self.assertEqual(c["unlisted"], [("firefox", "launch", 2)], "a browser type the allow-list does not know is refused by its name: %r" % (c["calls"],))
                    continue
                self.assertTrue(any(token in why and line == 2 for line, _, why in c["refusals"]), "%s: the walk refuses the shape by line and class: %r" % (name, c["refusals"]))

    def test_every_plant_of_the_review_is_refused_by_the_class_the_table_names(self):
        """The fixture: each PLANTS row inserted into the driver and run through this census gives the verdict the row
        names, with the two controls passing. A row whose verdict moves is a change to what the census sees, and its
        line in PLANTS is where to say why."""
        self.assertGreaterEqual(len(PLANTS), 36, "the review's plants are all in the table: %d" % len(PLANTS))
        for name, js, want in PLANTS:
            with self.subTest(plant=name):
                c = self._census(name if js else "driver.mjs", planted(js))
                got = verdict(c)
                self.assertEqual(got, want, "%s: %s (refusals %r, unlisted %r, uncapped %r, unlisted waits %r, fetches %d)"
                                 % (name, js or "the unmodified driver", c["refusals"], c["unlisted"], c["uncapped"], c["unlisted_waits"], c["fetches"]))
                if want != "passed":
                    line = L.DRIVER.count("\n", 0, L.DRIVER.index(ANCHOR)) + 2   # the plant's own line
                    where = [ln for ln, *_ in c["refusals"]] + [ln for _, _, ln in c["unlisted"]] + [ln for ln, *_ in c["uncapped"]] + [ln for _, ln in c["unlisted_waits"]]
                    if want != "fetch":
                        self.assertIn(line, where, "%s: the red names the plant's line %d: %r" % (name, line, where))


if __name__ == "__main__":
    unittest.main()

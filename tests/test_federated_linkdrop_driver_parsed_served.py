"""The link-drop driver's receiver walk and wait census over the compiler's PARSE of the driver (2026-09-20, the author's pass 9 of PR 857).

The `_served` suffix is a PLACEMENT, not a description: this module boots no kernel, drives no page and needs no browser; it
parses source. The suffix reaches the one CI job whose vscode-extension/node_modules holds the typescript package (the
browser-backed served-page step, which runs tests/test_*_served.py after `npm ci` under ROMP_SERVED_TESTS_REQUIRE=1); on the
Python matrix, which installs no node deps, it skips with a reason saying the same, and under REQUIRE that skip is a failure.

tests/test_federated_linkdrop_driver_bound.py requires every wait the driver places to draw on its budget and every call
on a playwright receiver to be one an allow-list names for that receiver's kind, because an auto-waiting read inherits
playwright's 30 s default that no budget caps. Its instruments there are regular expressions over the driver text, keyed
on a receiver written as a bare dotted name, and the maintainer's round 4 (its addendum's prep) measured that keying: spellings of the same receiver
reached none of them (among them an object literal, an array, a ternary, `null || pages.feed`, an arrow's or a return's
value, a page awaited into a helper, optional chaining, bracket access to the method, a comma operator, a receiver
parenthesised before the await, a space or a comment before the member, a second browser from firefox; PLANTS below is
the measured table, each row with the verdict this census must give it, and the review record outside the repo carries the
regex census's verdict on each), a member read followed by a call (`pages.feed.request.get(url)`) ended the walk's chain
silently, and a wait written `. waitFor`, `["goto"]` or `goto?.()` was no site to the wait census. The rule the review
gave: a census over a FORM is keyed on the property, or it parses, or its message says which spellings it checks. This
module parses.

THE PARSER. The typescript package under vscode-extension/node_modules (the extension's devDependency, at the version
vscode-extension/package-lock.json pins: setUpClass asserts the parser's own report of its version against the lock, so a
lock refresh or a drifted node_modules is a red here, and the parse-failure message names the version), called from a small
node helper (PARSE_HELPER) the census hands the sources to: `ts.createSourceFile(name, src, options,
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

THE WALK. A receiver is known by its TYPE through the walk, never by its spelling, and the walk's default is the REFUSAL of
three things: a NAME no scope of the tree binds, a MEMBER of a root the driver does not read, and a receiver (or a table, a
list or an object holding one) reaching a shape the walk does not follow, each refused by construction; what is done with an
untyped value (`cfg.fifo`, a literal, an arithmetic expression) is not read, and the soundness argument is the consumption
rule below (a receiver cannot enter an untyped local unrefused), not a per-node refusal. The shapes the walk follows are the
exceptions, each a list held equal to the driver (the maintainer's round 5: the earlier walk refused the shapes it recognised and let the rest
through, so each round of planting found more). The roots: the destructuring of
`require("playwright")` names a browser type (chromium; firefox and webkit would be named the same way and refused by the
allow-list, which knows chromium alone), `chromium.launch(...)` is a browser, `browser.newContext(...)` a context,
`context.newPage(...)` a page, a page's or a locator's LOCATOR_MAKERS call a locator, `makeBudget(...)` the budget and
`budget.waitFor` read without a call the budget's poll; an import binding (`fs`, `createRequire`) is a MODULE, a kind the
walk types and reads nothing of. A type flows through `await`, parentheses, a ternary's or a logical expression's branches,
an array literal (a list of that type), an object literal's property (an object holding it), a `const`, `let` or `var`
declaration, a destructuring pattern followed ELEMENT BY ELEMENT (each name bound to the member the walk can type on the
value: a record's or the playwright module's named member, a list's element, a module's member; nested to any depth, and an
element the walk cannot bind on a receiverish value, a rest element, a default, a computed property name, a member of a
receiver read by a pattern, an array pattern over anything but a list, is refused where it stands, since its names would
stay untyped with the receiver inside them), an assignment, which types the name in the scope that DECLARES it (a closure's
write to an outer name types the outer binding), a helper's return (its expression body, the last child of the function that
is not a parameter, so `(page) => page` returns its parameter; or its `return` statements), a helper's parameters (from the
types of the arguments at each call of it, or a default's), and a for-of's DECLARATION over a list (a pattern there is
followed the same way; a for-of whose target is no declaration, a bound name, a member, an object or array pattern written as
an assignment target, `for await` included, binds no element, so one over a receiverish iterable is refused at the statement:
the maintainer's round 6, correctness-1); a write of a receiver into a member of a declared object (`pages[app] = page`) makes that object a
TABLE of the receiver's type, whose every member read is one. Names resolve by function scope: every binding of the tree is
declared before the typing starts (a parameter, a declaration, a function's or a class's name, an import binding, a catch
variable, the names inside a destructuring pattern), a parameter or a declaration inside a helper shadows the module's, and
a name bound to two types in one scope is refused. A name no scope
binds is FREE, and a free name is refused wherever it is read (as the object of a member, a callee, an argument, a value)
unless it is one of KNOWN_GLOBALS, the free names the driver reads today, a tuple the driver cell holds EQUAL to the walk's
own list over the unplanted driver, so a global the driver starts or stops reading is a red until the tuple says so. A known
global and a module binding are ROOTS the walk resolves to no receiver: a member of one (`process.env`, `Date.now`,
`fs.readFileSync`, a name imported from the module, the same through an alias of the root) must be one the driver reads
today, KNOWN_MEMBERS, a second tuple the driver cell holds equal to the walk's list, so `process.binding`, `fs.promises` or
`fs.watchFile` is a red until it is read; a computed member on a root is refused, the walk cannot name it. What is done with
a known global or member is the disclosed class below, and TIMERS, PROMISE_ALLOWED, REFUSED_NAMES and the fetch count refuse
particular uses of particular names. Then every expression whose type is a receiver, a table, a list or an object holding
one must be CONSUMED by one of the shapes the walk follows: the object of a member call (checked against the allow-list by
kind, `evaluate` on a page only), a truth test (an if, a while, a for, a `!`, a ternary's condition, a `&&` or `||`), a
binding or an assignment (accepted because the BINDING was judged, never by the target's form: a declaration's or a
parameter's pattern has every element bound or refused by the pattern rule above, an assignment's target is a declared name
or a table's member or is refused), an argument to a helper the driver declares (its type flows to the parameter) or to Object.keys
(the table), an `await`, a literal it is placed in (under a property name the parse can read: a computed key is refused,
since the record would hold the receiver under a name no member read can be typed by), the iterable of a for-of over a list,
a record's or the playwright module's member under a name or a string literal (typed by _member; under a computed key
either is refused, the walk cannot name what the key reaches), and a return from a helper the walk FOLLOWS TO A CALL: a
helper is invoked where the walk reads a call of it (a bare name bound to it, a name reached through a list or a table, a
call where it stands: an IIFE, `outer()()`, `fns[0]()`), and a receiver returned from a helper no followed call invokes (a
callback handed to a member call, a helper held in a literal or read as a member, a getter, an object or class method, a
constructor, whose `this` the walk does not type) is refused where it is returned; a helper whose return is a receiver may
itself sit only in a name binding, an assignment to a name, a direct call, or an argument to a helper the walk follows
(pass 9's fixer pass: nine shapes returned a page from a getter, an object or a class method, `hf.call`, a callback, an
array-held or a returned arrow, and passed silently). Anything else is refused by line and text: a member READ that is not
itself called (`pages.feed.request`, `pages.feed.keyboard`, `pages.feed.waitForFunction` bound to a name), a computed member
(`locator(...)[mth]()`, `box[key]`, `pw["chrom" + "ium"]`), a receiver passed to a callee the walk does not follow
(`Reflect.get`, `wf.call`, a member call on an untyped object), a receiver in a template string, a comparison, a
constructor, or any other parent. Enumerated on the safe side: the consumers are the list, and a new shape the driver grows
is a red here until it is read.

THE WAIT CENSUS reads the same tree: every call whose member name is a wait form (the WAIT_FORMS of the driver-bound
module: the navigations, the waitFor family, waitForTimeout) or whose callee is the budget's poll is a site, whatever
punctuation spells it (`. waitFor`, `["goto"]`, `goto?.()` are the same calls); a `timeout` option is read from the call's
object-literal argument by node, and must be exactly one budget.capped(...) call (CAPPED) as the whole value; a
waitForTimeout draws on the budget or is one of the two fixed dwells. The budget is ONE: the driver's module-level `const
budget = makeBudget(...)`, held to exactly one by the driver cell; a second makeBudget, wherever it sits and whatever it is
bound to, is refused, since its sleep would be a timer this census exempts and its poll a wait it reads as the budget's, with
a deadline of its own. A bare `waitFor(` is the poll only when the tree binds that name to `budget.waitFor` in a scope the
call sees; a bare wait-named call the tree binds to no poll is an unlisted form. A page's `evaluate` (UNTIMED_READS in the driver-bound
module: a protocol read with no timeout option and no default bound, allow-listed at the pass-10 head as a call known not to
wait, which it is not: the maintainer's round 6, extra4-2) is allowed only as the FIRST ARGUMENT of `budget.bounded(...)`, the
budget's race of the read against what is left of it (BUDGET_JS), and is refused anywhere else, its promise awaited or bound
before the race included. A wait outside playwright and the budget is
refused by the ROAD to it, wherever the name appears as an identifier (a reference, a member name, a binding): a timer
(setTimeout, setInterval, setImmediate, queueMicrotask) anywhere but the budget's own `sleep`, and there only when its delay
is the sleep's own argument, resolved by scope to the sleep's first parameter (the poll hands it capped(250); a timer under
the sleep with any other delay, nested a function deeper or not, is a wait the budget does not bound and is refused);
`Promise` read anywhere but as that sleep's constructor, the object of a Promise.resolve or
Promise.all call, or the object of the Promise.race inside the budget's own maker (the function bound to `makeBudget`, whose
`bounded` races a page read against the budget's sleep; a race anywhere else, an alias or another combinator is a promise that
may never settle); `fetch` anywhere but as a callee, bare or as a member
(counted there; an alias is refused); `Atomics`, `eval`, `Function`, `globalThis` and `global` (REFUSED_NAMES: script text
or a name the census cannot read); a computed member call on a value the walk does not type (`x["set" + "Timeout"](...)`);
and a SCRIPT_METHODS call (evaluate, evaluateHandle, waitForFunction, addInitScript and the rest) whose first argument is
anything but a function literal or a name the tree binds to one, since a string handed to the page is script this census
does not parse (the driver's `hook` is an arrow). A module is loaded only the driver's way: an `import` of node:module or
node:fs, the one module-level `const require = createRequire(...)` (a second createRequire, or one bound to another name, is
refused) and `require("playwright")` (a require of any other module or of a built name, and `require` read as a value, are
refused); a dynamic `import()` is refused whatever its argument. A loop's exit is a bound this census reads only where the
header states it: a while, do or for statement whose header (the condition, a for's incrementor) holds a receiver, the budget
or its poll, or CALLS a helper the walk resolves to one that reads a receiver, the budget, its poll or fetch, in its own body
or through the helpers it calls over the calls the walk follows (the maintainer's round 6, tests-1: the same poll written one
call out of the header passed, since the rule keyed on a node in the header and not on what the header's callees resolve to),
is refused, since its exit depends on what it reads and no timeout caps it (the budget's waitFor is the driver's
one receiver-reading loop, its own `while` reading the budget's clock; the driver's counter loops call receivers in their
bodies and are followed, a for-of is bounded by its iterable), and a helper in a call cycle (it calls itself, directly or
through another helper, a call inside a callback of its body included, over the graph of the calls the walk follows) is
refused as a recursion whose exit the census cannot read. The object-literal arguments of every receiver call are read by
node: each property name is an option of that (kind, method) and must be one the driver passes today (KNOWN_OPTIONS, held
equal to the walk's list by the driver cell), since the walk reads nothing of what an option does and a `slowMo` on a launch,
a `timeout` on a launch or a context or a `waitUntil` on a navigation is a wait no budget caps; a computed key or a spread
there is an option the walk cannot name. Disclosed, the class the census cannot see, drawn as the rule over what the walk
resolves to no receiver and not as a list of shapes: (1) a wait spelled by CONTROL FLOW rather than by a call the census
reads: a loop whose exit is decided in its body (`for (;;) { if (await ...count()) break; }`, a flag a receiver read sets),
a loop whose header calls a helper the walk does NOT resolve to a function (one held in a literal's member, reached through a
road the walk does not follow), since the header rule follows the helpers the walk resolves and no other,
a loop whose header reads no receiver (a busy loop over Date.now in the driver; one inside a callback handed to evaluate is
raced by budget.bounded since pass 11, which bounds the DRIVER's wait on that read and not the renderer: the loop keeps the
renderer wedged, every later locator.count() (class (1) of the allow-list, a call that does not auto-wait but a protocol read
the renderer answers) waits for the wedge to end outside the budget, and the drive's bound there is DRIVER_TIMEOUT_S, the
kill, with the RESULT line held when the driver had printed one (pass 11's fixer pass measured it: the race lost at the
budget's remaining time and the next count() returned when the wedge ended); one handed to waitForFunction by its capped
timeout), CPU-bound work, and an awaited
object whose `then` never settles, since the census reads call sites and their timeouts and resolves no loop's exit beyond the
header rule and the cycle rule above; (2) a call of a known global (`String`,
`setTimeout` inside the sleep, `fetch`) or of a known member of a global or a module (`Date.now`, `JSON.parse`, the driver's
own `fs.readFileSync`), with ANY argument and however the member is reached (the root's name, an alias of the root, the
member bound to a name, a name imported from the module): the census keys on WHICH global is read, WHICH module is loaded
and WHICH member is read, all three held equal to the driver (KNOWN_GLOBALS, IMPORTS_ALLOWED, KNOWN_MEMBERS), and not on the
arguments, so the driver's `fs.readFileSync(process.env.CFG)` and a planted `fs.readFileSync("/dev/stdin")` are one call to
it, a blocking one included; a member the driver does not read (`process.binding`, `fs.promises`, `fs.watchFile`) is refused
by construction; (3) an option a receiver call is handed as a VALUE the walk does not type: the driver's
`chromium.launch(cfg.launch || {})` reads its launch options from the config, which the lab writes with no `launch` key (the
config cell reads the dict literal the lab's _drive writes and pins it), so the launch runs on playwright's defaults, its own
launch timeout among them; the launch is outside the budget and read by no census, and the arithmetic CARRIES it as a fixed
term at that default (the served module's LAUNCH_TIMEOUT_S inside DRIVER_FIXED_S, whose comment states the term and the
arithmetic pin that holds it; the maintainer's round 6, extra4-1: an earlier sentence here called it a wait the arithmetic
does not count). The budget is a deadline and bounds none of the three. DISCLOSED names the plant rows of that class, witness rows for each member (several spellings
of the second), which pass by disclosure and are pinned as passing, so a census that learns to see one says so. The two
fetches (ctl and tunnelsStatus) stay the acknowledged driver_error road, pinned at two.

THE PLANTS. PLANTS is a fixture: each row is one line inserted into the driver after `out.provBefore = await provText();`,
run through this census, and must give the verdict class its row names (a walk refusal, an unlisted call, an uncapped or
unlisted wait site, a third fetch; `passed` for the CONTROLS and the DISCLOSED rows, and for nothing else). The rows are the
prep note's tables for censuses 3, 4 and 5, the addendum's `null || pages.feed`, the builder's and the fixer's, as the
comment on PLANTS says; the before-outcomes through the pass-8 head's regex census are in the review record outside the
repo, which names the rows that were red there. No count is kept in this docstring: len(PLANTS) is the count.

Synthetic: no kernel, no browser; node and the extension's node_modules only.
"""
import ast
import inspect
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

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
# of an identifier or a literal, the operator of a binary or unary expression, and for a `for` statement the role of each child
# in order (initializer, condition, incrementor, statement; the absent ones omitted), since the header's `;` are no children.
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
  if (ts.isForStatement(n)) o.roles = [["initializer", n.initializer], ["condition", n.condition], ["incrementor", n.incrementor], ["statement", n.statement]].filter(([, v]) => v).map(([r]) => r);
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
LOOP_KINDS = ("WhileStatement", "DoStatement", "ForStatement")   # the loops whose exit a header decides (a for-of is bounded by its iterable)
# The options the driver passes to its receiver calls today, as (kind, method, key), read by node from each call's object-literal
# arguments: the ONE list of options the walk resolves, held EQUAL to the walk's list over the unplanted driver by the driver cell.
# The walk reads nothing of what an option does (a wait form's `timeout` is read by _site for its value), so an option outside
# the tuple (a `slowMo` on a launch, a `timeout` on a launch or a context, a `waitUntil` on a navigation: waits no budget caps) is
# refused until the tuple says so, and a computed key or a spread is an option the walk cannot name. An argument that is not an
# object literal is not read here; the driver's `chromium.launch(cfg.launch || {})` hands the launch its config's options, the
# disclosed class's third member (the module docstring), pinned by the config cell.
KNOWN_OPTIONS = (("browser", "newContext", "viewport"), ("locator", "waitFor", "state"), ("locator", "waitFor", "timeout"), ("page", "addInitScript", "stripCaps"),
                 ("page", "goto", "timeout"), ("page", "locator", "hasText"), ("page", "waitForFunction", "timeout"))
IMPORTS_ALLOWED = ("node:module", "node:fs")       # the driver's own imports; any other module is a road the census does not know
REQUIRE_ALLOWED = ("playwright",)
# names refused wherever they appear as an identifier (a reference, a member name, a binding), by the road each opens: script
# text this census does not parse (eval, the Function constructor), a wait spelled with no timer name (Atomics.wait), the global
# object (a member of it named by a string is a name the walk cannot read)
REFUSED_NAMES = {"eval": "eval runs script text this census does not parse", "Function": "the Function constructor runs script text this census does not parse",
                 "Atomics": "Atomics.wait is a wait spelled with no timer name", "globalThis": "a member of the global object named by a string is a name the walk cannot read",
                 "global": "a member of the global object named by a string is a name the walk cannot read"}
PROMISE_ALLOWED = ("resolve", "all")               # the Promise members the driver calls; every other read of `Promise` is refused (a promise that may never settle)
# the receiver methods that run SCRIPT in the page: their first argument must be a function literal, or a name the tree binds to
# one, since a string (or a value built into one) handed to them is script this census does not parse
SCRIPT_METHODS = ("evaluate", "evaluateHandle", "evaluateAll", "$eval", "$$eval", "waitForFunction", "addInitScript")
FN_KINDS = ("ArrowFunction", "FunctionExpression", "FunctionDeclaration", "MethodDeclaration")
ACCESSOR_KINDS = ("MethodDeclaration", "GetAccessor", "SetAccessor", "Constructor")   # a body the walk types no `this` for and follows to no call (a constructor's return reaches `new`)
SCOPE_KINDS = FN_KINDS + ("GetAccessor", "SetAccessor", "Constructor")   # the nodes that open a function scope
PASS_THROUGH = ("AwaitExpression", "ParenthesizedExpression", "NonNullExpression", "AsExpression", "SatisfiesExpression", "TypeAssertionExpression")
LOGICAL = ("||", "&&", "??")
AUX = ("budget", "poll")   # kinds the walk tracks that are no receiver
SHADOW = object()          # a declared name with no receiver type: it hides an outer binding of the same name
# The free names the driver reads (no scope of the tree binds them): the ONE list of globals the walk resolves. Every other
# free name is refused wherever it is read, and the driver cell holds this tuple EQUAL to the walk's own list over the
# unplanted driver, so a global the driver starts or stops reading is a red until the tuple says so. What is done with one is
# the disclosed class (the module docstring); TIMERS, PROMISE_ALLOWED, REFUSED_NAMES and the fetch count refuse particular uses.
KNOWN_GLOBALS = ("Array", "Date", "JSON", "Math", "Object", "Promise", "String", "console", "document", "fetch", "process", "setTimeout", "undefined", "window")
# The members the driver reads on those globals and on the modules it loads (by the module's specifier), the ONE list of such
# members the walk resolves; a member of a root outside it is refused wherever it is read (`process.binding`, `fs.promises`),
# a computed member on a root is refused (the walk cannot name it), and the driver cell holds this tuple EQUAL to the walk's
# list over the unplanted driver. A member reached through an alias of the root, bound to a name, or imported from the module
# by name is the same member; what the member is called with is not read (the disclosed class, the module docstring).
KNOWN_MEMBERS = (("Array", "isArray"), ("Date", "now"), ("JSON", "parse"), ("JSON", "stringify"), ("Math", "max"), ("Math", "min"),
                 ("Object", "assign"), ("Object", "keys"), ("Promise", "all"), ("Promise", "race"), ("Promise", "resolve"), ("console", "error"), ("console", "log"),
                 ("document", "querySelector"), ("node:fs", "readFileSync"), ("process", "env"), ("process", "exit"),
                 ("window", "WebSocket"), ("window", "__rompLocalUp"), ("window", "__sends"), ("window", "__socks"))
# the parents whose FIRST identifier child is a name being declared, not a reference read; and the parents under which an
# identifier is never a reference (a binding pattern's names, an import's names, a label, `import.meta`)
DECLARING_HEADS = ("PropertyAssignment", "VariableDeclaration", "Parameter", "FunctionDeclaration", "FunctionExpression", "MethodDeclaration",
                   "GetAccessor", "SetAccessor", "PropertyDeclaration", "ClassDeclaration", "ClassExpression")
NOT_REFERENCES = ("BindingElement", "ImportClause", "ImportSpecifier", "NamespaceImport", "LabeledStatement", "BreakStatement", "ContinueStatement", "MetaProperty")


def parse_js(sources):
    """[(name, src)] through node and the typescript package under EXT: (tsVersion, {name: (diagnostics, tree)}). Skips, in
    the served labs' words, when node or the package is absent, so ROMP_SERVED_TESTS_REQUIRE=1 turns that into a failure."""
    if not shutil.which("node"):
        raise unittest.SkipTest("extension deps absent (npm ci not run here): this is a source parse with no server and no browser, placed under the _served suffix to reach the CI job that has node; it needs node")
    if not os.path.isdir(os.path.join(EXT, "node_modules", "typescript")):
        raise unittest.SkipTest("extension deps absent (npm ci not run here): this is a source parse with no server and no browser, placed under the _served suffix to reach the CI job that has vscode-extension/node_modules; it needs the typescript package there")
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
        if k[0] in ("fn", "module", "global"):
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
        if k[0] == "module":
            return ("%s imported from %s" % (k[2], k[1])) if k[2] is not None else ("the module %s (an import binding)" % k[1])
        if k[0] == "global":
            return "the global %s" % k[1]
        if k[0] == "record":
            return "an object holding {%s}" % ", ".join("%s: %s" % (p, show(v)) for p, v in sorted(k[1]))
        return "a %s of %s" % (k[0], show(k[1]))
    if k == "playwright":
        return "the playwright module"
    return "a %s" % k


class Walk:
    """The receiver walk by type and the wait census over one parsed source. After run(): `refusals` {(line, text, why)},
    `calls` [(kind, method, line)], `waits` [(form, timeouts, first_arg, line)], `fetches` [line], `imports` [(module, line)],
    `requires` [(module, line)], `poll_bindings` [(scope kind, line)], `require_bindings` [line], `invoked` {id(fn node)},
    `globals` {KNOWN_GLOBALS name: [lines]} (the free names it resolved to a known global; every other free name is a refusal),
    `member_reads` {(root, member): [lines]} (the KNOWN_MEMBERS it read on a known global or a loaded module; any other is a refusal)."""

    def __init__(self, src, tree):
        self.src, self.root = src, tree
        self.parent, self.nodes = {}, []
        self._link(tree, None)
        self.scopes = {}      # id(scope node) -> {name: kind or SHADOW}
        self.fn_params = {}   # id(fn node) -> [(name, fn node) or None per parameter]
        self.fn_ret = {}      # id(fn node) -> the kind its body returns, re-derived each round
        self.kinds = {}
        self.refusals = set()
        self.invoked = set()  # id(fn node) of every helper some call the walk follows invokes: a receiver returned from any other is refused
        self.calls, self.waits, self.fetches, self.timers, self.imports, self.requires, self.poll_bindings, self.require_bindings = [], [], [], [], [], [], [], []
        self.globals, self.member_reads, self.options = {}, {}, {}
        self.budget_bindings = []   # the lines of the driver's one `const budget = makeBudget(...)` (a second makeBudget is a refusal)
        self.bounded_reads = []     # the lines of every budget.bounded(...) call: the untimed reads (UNTIMED_READS) must sit as its first argument
        self.call_edges = set()     # (id(enclosing fn), id(callee fn)) for every call the walk follows: a cycle is a helper that recurs
        self.fn_nodes = {}          # id(fn node) -> the node, for the refusal at a cycle's helper
        self._declare_all()

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
        while p is not None and p["k"] not in SCOPE_KINDS and p["k"] != "SourceFile":
            p = self.parent[id(p)]
        return p if p is not None else self.root

    def resolves(self, name, n):
        """Whether a scope the node sees binds the name, typed or not; a name none binds is FREE (_kind refuses it unless it
        is a KNOWN_GLOBALS name)."""
        s = self.scope_of(n)
        while s is not None:
            if name in self.scopes.get(id(s), {}):
                return True
            s = None if s["k"] == "SourceFile" else self.scope_of(s)
        return False

    def lookup(self, name, n):
        s = self.scope_of(n)
        while s is not None:
            table = self.scopes.get(id(s), {})
            if name in table:
                return None if table[name] is SHADOW else table[name]
            s = None if s["k"] == "SourceFile" else self.scope_of(s)
        return None

    def declaring_scope(self, name, n):
        """The scope that DECLARES `name` as seen from `n` (the nearest enclosing one that binds it, typed or not), else the
        node's own scope for a name no scope binds (which _kind refuses as free). An assignment types the name where it is
        declared, so a closure's write to an outer name types the outer binding (pass 10's fixer pass: `let cap; const set = ()
        => { cap = pages.feed; }` typed cap inside the arrow alone, and the read at module level saw an untyped name)."""
        s = self.scope_of(n)
        while s is not None:
            if name in self.scopes.get(id(s), {}):
                return s
            s = None if s["k"] == "SourceFile" else self.scope_of(s)
        return self.scope_of(n)

    def refuse(self, n, why):
        self.refusals.add((self.line(n), self.text(n), why))

    def refuse_at(self, line, text, why):
        """A refusal with no node to point at (an import or a require read from the lists)."""
        self.refusals.add((line, text, why))

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
        if k in DECLARING_HEADS and kids[0] is n:
            return False
        return k not in NOT_REFERENCES

    def binding_names(self, target):
        """The identifiers a binding target declares: the name itself, or every name inside a destructuring pattern (a
        BindingElement's name is its second child when a `:` separates a property name from it, else its first)."""
        if target["k"] == "Identifier":
            return [target]
        out = []
        if target["k"] in ("ObjectBindingPattern", "ArrayBindingPattern"):
            for el in self.kids(target):
                ek = self.kids(el)
                if el["k"] != "BindingElement" or not ek:
                    continue
                name = ek[1] if len(ek) > 1 and ":" in self.src[ek[0]["e"]:ek[1]["s"]] else ek[0]
                out += self.binding_names(name)
        return out

    def _declare_all(self):
        """Every binding of the tree, declared in its scope before the typing starts, so that a name no scope binds is FREE at
        every read (a typing round visits a reference before a later declaration otherwise): a parameter's and a variable
        declaration's names (a catch clause's and a for-of's included, the names inside a destructuring pattern), a function's
        or a class's name, and an import binding, which is bound to the module it comes from (a kind the walk reads nothing of)."""
        for n in self.nodes:
            k, kids = n["k"], self.kids(n)
            if k in ("VariableDeclaration", "Parameter") and kids:
                for ident in self.binding_names(kids[0]):
                    self.declare(self.scope_of(ident), ident["t"])
            elif k in ("FunctionDeclaration", "ClassDeclaration") and kids and kids[0]["k"] == "Identifier":
                self.declare(self.scope_of(n), kids[0]["t"])
            elif k == "ImportDeclaration":
                spec = next((c for c in kids if c["k"] == "StringLiteral"), None)
                for m in self.nodes:
                    p = self.parent[id(m)]
                    if m["k"] != "Identifier" or p is None or p["k"] not in ("ImportClause", "NamespaceImport", "ImportSpecifier"):
                        continue
                    if p["k"] == "ImportSpecifier" and self.kids(p)[-1] is not m:
                        continue   # `{ a as b }`: a is the module's name, b the binding
                    q = p
                    while q is not None and q is not n:
                        q = self.parent[id(q)]
                    if q is n:
                        # a default or namespace import is the module itself; a named import is one MEMBER of it (`{ a as b }` binds b to a)
                        member = self.kids(p)[0]["t"] if p["k"] == "ImportSpecifier" else None
                        self.bind(self.root, m["t"], ("module", spec["t"] if spec is not None else None, member), n)

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
            if not self.is_reference(n):
                return None
            if not self.resolves(n["t"], n):
                p = self.parent[id(n)]
                if n["t"] in KNOWN_GLOBALS:
                    self.globals.setdefault(n["t"], []).append(self.line(n))
                    return ("global", n["t"])
                self.refuse(p if p is not None else n, "%s, read in a %s: a free name no scope of the tree binds and no global the driver reads (KNOWN_GLOBALS); the walk "
                                                       "resolves it to nothing, and what it cannot resolve it refuses" % (n["t"], p["k"] if p is not None else k))
                return None
            return self.lookup(n["t"], n)
        if k in PASS_THROUGH:
            return self.kind_of(kids[0]) if kids else None
        if k == "CallExpression":
            return self._call(n, kids)
        if k == "PropertyAccessExpression":
            ko = self.kind_of(kids[0])
            if isinstance(ko, tuple) and ko[0] in ("module", "global"):
                return self._root_member(n, ko, kids[1].get("t"))
            return self._member(ko, kids[1].get("t"))
        if k == "ElementAccessExpression":
            ko, arg = self.kind_of(kids[0]), kids[1]
            if isinstance(ko, tuple) and ko[0] in ("table", "list"):
                return ko[1]
            named = arg["t"] if arg["k"] in ("StringLiteral", "NoSubstitutionTemplateLiteral") else None
            if isinstance(ko, tuple) and ko[0] in ("module", "global"):
                return self._root_member(n, ko, named)
            return self._member(ko, named) if named is not None else None
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
                if c["k"] == "PropertyAssignment":
                    if ck[0].get("t") is not None:
                        props.append((ck[0]["t"], self.kind_of(ck[1])))
                    elif receiverish(self.kind_of(ck[1])):
                        self.refuse(c, "%s placed under a property name the walk cannot read (a computed key): the record would hold it under a name no member read can be typed by" % show(self.kind_of(ck[1])))
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
            if len(kids) > 1:   # a default: its type flows into the parameter's name or pattern (a call's arguments flow in _flow)
                self._bind_pattern(self.scope_of(n), kids[0], self.kind_of(kids[-1]), n)
            return None
        if k == "ForOfStatement":
            ki = self.kind_of(kids[1])
            if kids[0]["k"] == "VariableDeclarationList":
                if isinstance(ki, tuple) and ki[0] == "list":
                    for d in self.kids(kids[0]):
                        dk = self.kids(d)
                        if dk:
                            self._bind_pattern(self.scope_of(d), dk[0], ki[1], d)   # the element's type into the name or the pattern
            elif receiverish(ki):
                # the target is no declaration (a bound name, a member, an object or array pattern as an assignment target, `for await`
                # over any of them): the walk bound no element, so the type would flow to a name or a member it cannot type
                self.refuse(n, "a for-of over %s whose element the walk did not bind: its target is a %s, not a declaration, so the element reaches a name or a member the walk does not type" % (show(ki), kids[0]["k"]))
            return None   # a table, a record or a receiver iterated is refused in _consume
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

    def _root_member(self, at, ko, member):
        """A member of a ROOT the walk resolves to no receiver (a KNOWN_GLOBALS name, a module binding, or a name imported from a
        module): the walk reads nothing of what the member does, so it is one the driver reads today (KNOWN_MEMBERS, held equal
        to the driver's list by the driver cell), recorded, or a refusal; a computed member, or a member of a module's member,
        is a name the walk cannot resolve. Returns None: the member's own value is not typed."""
        if ko[0] == "module" and ko[2] is not None:
            self.refuse(at, "a member of %s, a value the walk reads nothing of" % show(ko))
            return None
        root = ko[1]
        if member is None:
            self.refuse(at, "a computed member on %s: a name the walk cannot read" % show(ko))
            return None
        if (root, member) not in KNOWN_MEMBERS:
            self.refuse(at, "%s.%s: a member of %s the driver does not read (KNOWN_MEMBERS holds the members it reads today); the walk resolves it to nothing, and what it cannot resolve it refuses" % (root, member, show(ko)))
            return None
        self.member_reads.setdefault((root, member), []).append(self.line(at))
        return None

    def _call(self, n, kids):
        raw = n.get("c", [])
        if raw and raw[0]["k"] == "Token" and raw[0].get("t") == "import":
            self.refuse(n, "a dynamic import(): a module load this census does not follow, whatever its argument")
            return None
        callee, args = kids[0], kids[1:]
        line = self.line(n)
        if callee["k"] == "Identifier":
            name = callee["t"]
            if name == "require":
                mod = args[0]["t"] if args and args[0]["k"] == "StringLiteral" else None
                self.requires.append((mod, line))
                return "playwright" if mod == "playwright" else None
            if name == "createRequire":
                # the one loader the driver makes: `const require = createRequire(...)` at module level; a second loader, or one
                # bound to another name, loads modules the census does not follow
                p = self.parent[id(n)]
                if p is not None and p["k"] == "VariableDeclaration" and self.kids(p)[0].get("t") == "require" and self.scope_of(p)["k"] == "SourceFile":
                    self.require_bindings.append(line)
                else:
                    self.refuse(n, "a createRequire beyond the driver's one module-level `const require = createRequire(...)`: a loader the census does not follow")
                return None
            if name == "makeBudget":
                # the driver's ONE budget: `const budget = makeBudget(...)` at module level; a second budget's sleep would be a
                # timer this census exempts and its poll a wait it reads as the budget's, with a deadline of its own
                p = self.parent[id(n)]
                if p is not None and p["k"] == "VariableDeclaration" and self.kids(p)[0].get("t") == "budget" and self.scope_of(p)["k"] == "SourceFile":
                    self.budget_bindings.append(line)
                else:
                    self.refuse(n, "a makeBudget beyond the driver's one module-level `const budget = makeBudget(...)`: a second budget's sleep and poll are waits this census would read as the budget's")
                return "budget"
            kc = self.lookup(name, callee)
            if kc == "poll":
                self.waits.append(self._site("waitFor", n, args))
                return None
            if isinstance(kc, tuple) and kc[0] == "fn":
                return self._invoke(kc, args, n)
            if isinstance(kc, tuple) and kc[0] == "module":
                if kc[2] is None:
                    self.refuse(n, "%s called as a function" % show(kc))
                else:
                    self._root_member(n, ("module", kc[1], None), kc[2])   # a name imported from the module, called: that module's member
                return None
            if WAIT_NAME.fullmatch(name):
                self.waits.append(self._site(name + " (a bare name the tree binds to no poll)", n, args))
            return None
        if callee["k"] in ("PropertyAccessExpression", "ElementAccessExpression"):
            ck = self.kids(callee)
            ko = self.kind_of(ck[0])
            kc = self.kind_of(callee)
            if isinstance(kc, tuple) and kc[0] == "fn":
                return self._invoke(kc, args, n)   # a helper reached through a list or a table (`fns[0]()`)
            if callee["k"] == "ElementAccessExpression" and ko is None:
                self.refuse(n, "a computed member call on a value the walk does not type (a member spelled by a string or a built name)")
                return None
            method = ck[1].get("t") if callee["k"] == "PropertyAccessExpression" or ck[1]["k"] in ("StringLiteral", "NoSubstitutionTemplateLiteral") else None
            if method is None:
                if receiverish(ko):
                    self.refuse(n, "a computed member call on %s the walk cannot name" % show(ko))
                return None
            if isinstance(ko, str) and receiverish(ko):
                self.calls.append((ko, method, line))
                self._options(n, ko, method, args)
                if method in SCRIPT_METHODS:
                    self._script_arg(n, method, args)
                if method in B.UNTIMED_READS.get(ko, ()):
                    self._bounded_read(n, ko, method)
                if WAIT_NAME.fullmatch(method):
                    self.waits.append(self._site(".waitFor" if method == "waitFor" else method, n, args))
                if method in B.LOCATOR_MAKERS and ko in ("page", "locator"):
                    return "locator"
                return MAKERS.get((ko, method))
            if ko == "budget":
                if method == "waitFor":
                    self.waits.append(self._site("waitFor", n, args))
                elif method == "bounded":
                    self.bounded_reads.append(line)
                elif method not in ("capped", "left"):
                    self.refuse(n, "a call on the budget the census does not know: %s" % method)
                return None
            if receiverish(ko):
                self.refuse(n, "a call on %s, which is no receiver a method is called on" % show(ko))
                return None
            if WAIT_NAME.fullmatch(method):
                self.waits.append(self._site(".waitFor" if method == "waitFor" else method, n, args))
            return None
        kc = self.kind_of(callee)   # any other callee shape: a helper called where it stands (an IIFE, `outer()()`)
        if isinstance(kc, tuple) and kc[0] == "fn":
            return self._invoke(kc, args, n)
        return None

    def _invoke(self, kc, args, at):
        """A call of a helper the walk follows: the arguments' types flow to its parameters and its return type is the call's;
        the helper is marked invoked, so a receiver its body returns has somewhere to go; and the call is an edge from every
        function enclosing its site to the callee (a call inside a callback of a helper's body is the helper's too), the graph
        _cycles reads."""
        self.invoked.add(kc[1])
        self._flow(kc[1], args, at)
        f = self._enclosing_fn(at)
        while f is not None:
            self.call_edges.add((id(f), kc[1]))
            f = self._enclosing_fn(f)
        return self.fn_ret.get(kc[1])

    def _bounded_read(self, call, ko, method):
        """An untimed protocol read (UNTIMED_READS: a page's evaluate, no timeout option, no default bound) must be the FIRST
        argument of a `budget.bounded(...)` call, the budget's race against what is left of it; placed anywhere else (awaited or
        bound before the race, a later argument, a value) it is a wait no budget bounds and is refused (the maintainer's round 6,
        extra4-2: the pass-10 allow-list named evaluate a call known not to wait)."""
        p = self.parent[id(call)]
        if p is not None and p["k"] == "CallExpression":
            pk = self.kids(p)
            callee = pk[0]
            if len(pk) > 1 and pk[1] is call and callee["k"] == "PropertyAccessExpression":
                ck = self.kids(callee)
                if self.kind_of(ck[0]) == "budget" and ck[1].get("t") == "bounded":
                    return
        self.refuse(call, "%s.%s outside budget.bounded(...): an untimed protocol read (no timeout option, no default bound) that no budget bounds; race it as budget.bounded's first argument" % (ko, method))

    def _options(self, call, ko, method, args):
        """The object-literal arguments of a receiver call, read by node: every property name is an option of that (kind, method)
        and must be one the driver passes today (KNOWN_OPTIONS, held equal to the walk's list by the driver cell), since the walk
        reads nothing of what an option does (a `slowMo` on a launch, a `timeout` on a launch or a context, a `waitUntil` on a
        navigation are waits no budget caps); a computed key, a spread or a method is an option the walk cannot name. An
        argument that is not an object literal is not read here: a wait form's timeout value is _site's, a selector or a
        callback is the call's own, and the driver's `chromium.launch(cfg.launch || {})` hands the launch its config's options,
        a value the walk does not type (the disclosed class's third member; the config cell pins that the lab writes no `launch`
        key)."""
        for a in args:
            if a["k"] != "ObjectLiteralExpression":
                continue
            for prop in self.kids(a):
                pk = self.kids(prop)
                name = pk[0].get("t") if prop["k"] in ("PropertyAssignment", "ShorthandPropertyAssignment") and pk else None
                if name is None:
                    self.refuse(prop, "an option of %s.%s the walk cannot name (a computed key, a spread, a method)" % (ko, method))
                elif (ko, method, name) not in KNOWN_OPTIONS:
                    self.refuse(prop, "%s.%s({ %s }): an option the driver does not pass (KNOWN_OPTIONS holds the options it passes today); the walk reads nothing of what an option does, and a slowMo, a timeout or a waitUntil is a wait no budget caps" % (ko, method, name))
                else:
                    self.options.setdefault((ko, method, name), []).append(self.line(prop))

    def _script_arg(self, call, method, args):
        """A SCRIPT_METHODS call's first argument is a function literal or a name the tree binds to one; anything else (a string,
        a template, a value built or bound at run time, a Function) is script text this census does not parse."""
        a = args[0] if args else None
        ka = self.kind_of(a) if a is not None and a["k"] == "Identifier" else None
        if a is None or not (a["k"] in FN_KINDS or (isinstance(ka, tuple) and ka[0] == "fn")):
            self.refuse(call, "a script handed to %s as anything but a function literal or a name the tree binds to one (a string, a template, a bound or built value, a Function): its text is not this census's parse" % method)

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
            else:
                body = c   # the last child that is not a parameter: the Block, or the expression body, a bare identifier included (`(page) => page`)
        self.fn_params[id(n)] = params
        self.fn_nodes[id(n)] = n
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
        """A variable declaration: its initializer's type flows into the name or the pattern (_bind_pattern); the names
        themselves were declared by _declare_all before the typing started."""
        if len(kids) < 2:
            return
        k = self.kind_of(kids[1])
        if k is None:
            return
        if kids[0]["k"] == "Identifier" and k == "poll":
            self.poll_bindings.append((self.scope_of(n)["k"], self.line(n)))
        self._bind_pattern(self.scope_of(n), kids[0], k, n)

    @staticmethod
    def _element_has(el, token):
        return any(t["k"] == "Token" and t.get("t") == token for t in el.get("c", []))

    def _bind_pattern(self, scope, target, k, at):
        """A value of kind `k` flows into a binding target. A name is bound to it. A destructuring pattern is followed element
        by element, nested to any depth: each name is bound to the member the walk can type on the value (a record's named
        member, absent ones holding no receiver; the playwright module's member; a table's or a list's element; a module's or
        a global's member, read by _root_member and, for a module, bound as that member), and every element the walk CANNOT
        bind on a receiverish value is refused where it stands: a rest element, an element with a default, a computed property
        name, a member of a receiver or of a list read by an object pattern, a pattern over a root's member, an array pattern
        over anything but a list. Its names would otherwise stay untyped with the receiver inside them, and a read of one would
        be invisible (pass 10's fixer pass: a nested pattern, a rest element, a for-of pattern and a parameter pattern with a
        receiver default passed both censuses, since _consume accepted a pattern by its FORM and _declare bound one level of
        plain names). A value with no type flows nowhere: the names stay untyped, as _declare_all left them."""
        if target["k"] == "Identifier":
            self.bind(scope, target["t"], k, at)
            return
        root = isinstance(k, tuple) and k[0] in ("module", "global")
        if not receiverish(k) and not root:
            return
        if target["k"] == "ObjectBindingPattern":
            for el in self.kids(target):
                ek = self.kids(el)
                if el["k"] != "BindingElement" or not ek:
                    continue
                named = len(ek) > 1 and ":" in self.src[ek[0]["e"]:ek[1]["s"]]
                prop, sub = (ek[0].get("t"), ek[1]) if named else (ek[0].get("t"), ek[0])
                if self._element_has(el, "...") or len(ek) > (2 if named else 1) or prop is None:   # a rest element; a default (an initializer is one more child); a computed name
                    self.refuse(el, "%s destructured by an element the walk cannot bind (a rest element, a default, a computed property name): its names would hold the value untyped" % show(k))
                    continue
                if root:
                    self._root_member(el, k, prop)   # `const { readFileSync } = fs`: the module's member, read
                    if sub["k"] != "Identifier":
                        self.refuse(el, "a pattern over %s.%s, a member the walk reads nothing of" % (k[1], prop))
                    elif k[0] == "module" and k[2] is None:
                        self.bind(scope, sub["t"], ("module", k[1], prop), at)
                    continue
                if isinstance(k, tuple) and k[0] == "record":
                    member = dict(k[1]).get(prop)   # absent: the value under that name holds no receiver
                elif k == "playwright" or (isinstance(k, tuple) and k[0] == "table"):
                    member = self._member(k, prop)
                else:
                    self.refuse(el, "a member of %s read by a pattern: its value is of a type the walk does not know" % show(k))
                    continue
                self._bind_pattern(scope, sub, member, at)
        elif target["k"] == "ArrayBindingPattern":
            if not (isinstance(k, tuple) and k[0] == "list"):
                self.refuse(target, "%s destructured by an array pattern: the walk types no element of it" % show(k))
                return
            for el in self.kids(target):
                ek = self.kids(el)
                if el["k"] != "BindingElement" or not ek:
                    continue   # an omitted element (`[, b]`)
                if self._element_has(el, "...") or len(ek) > 1:   # a rest element; a default (the initializer is a second child)
                    self.refuse(el, "%s destructured by an element the walk cannot bind (a rest element, a default): its names would hold the value untyped" % show(k))
                    continue
                self._bind_pattern(scope, ek[0], k[1], at)

    def _assign(self, n, left, kr):
        if kr is None:
            return
        if left["k"] == "Identifier":
            self.bind(self.declaring_scope(left["t"], left), left["t"], kr, n)   # typed where the name is declared, not where it is written
            return
        if left["k"] in ("PropertyAccessExpression", "ElementAccessExpression"):
            obj = self.kids(left)[0]
            if obj["k"] == "Identifier":
                ko = self.lookup(obj["t"], obj)
                if ko is None and receiverish(kr) and self.resolves(obj["t"], obj):
                    self.bind(self.declaring_scope(obj["t"], obj), obj["t"], ("table", kr), n)   # a receiver written into a member of a declared object: the object is a table of them, where it is declared
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
            self.calls, self.waits, self.fetches, self.imports, self.requires, self.poll_bindings, self.require_bindings, self.budget_bindings, self.bounded_reads = [], [], [], [], [], [], [], [], []
            self.refusals, self.invoked, self.globals, self.member_reads, self.options, self.call_edges = set(), set(), {}, {}, {}, set()
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
            elif isinstance(k, tuple) and k[0] == "fn" and receiverish(self.fn_ret.get(k[1])):
                self._consume_fn(n, k)
        self._outside_playwright()
        self._loops()
        self._cycles()
        return self

    def _enclosing_fn(self, n):
        p = self.parent[id(n)]
        while p is not None and p["k"] not in FN_KINDS and p["k"] not in ACCESSOR_KINDS:
            p = self.parent[id(p)]
        return p

    def _returned(self, n, k, fn):
        """A receiver returned from `fn` (a return statement's value, an expression body) is followed only where the walk
        follows a call of `fn` (_invoke), so the type has a call to flow to; a method's, an accessor's or a constructor's body is
        followed to no call (the walk types no `this` and no object method), and a helper no followed call invokes (a callback handed to a
        member call, a helper held in a literal, one reached through a road the walk does not read) returns it to nowhere the
        walk can see."""
        if fn is None:
            return self.refuse(n, "%s returned outside a function" % show(k))
        if fn["k"] in ACCESSOR_KINDS:
            return self.refuse(fn, "%s returned from a method, an accessor or a constructor: the walk types no `this` and no object method, so the call that reads it is unseen" % show(k))
        if id(fn) not in self.invoked:
            return self.refuse(fn, "%s returned from a helper the walk follows to no call (a callback handed to a member call, a helper held in a literal or reached through a road the walk does not read)" % show(k))

    def _consume_fn(self, n, k):
        """A helper whose return is a receiver flows only through a name binding, an assignment to a name, a direct call where it
        stands, or an argument to a helper the walk follows (whose parameter's calls invoke it, _flow); placed anywhere else
        (a literal, a member read such as `hf.call`, a callback to a member call, a return) its calls are unseen."""
        p = self.parent[id(n)]
        while p is not None and p["k"] in PASS_THROUGH:
            n, p = p, self.parent[id(p)]
        if p is None or n["k"] == "FunctionDeclaration":
            return
        pk, pkids = p["k"], self.kids(p)
        if pk == "VariableDeclaration" and pkids[0]["k"] == "Identifier" and pkids[-1] is n:
            return
        if pk == "BinaryExpression" and p.get("op") == "=" and pkids[0]["k"] == "Identifier" and pkids[1] is n:
            return
        if pk == "CallExpression":
            if pkids[0] is n:
                return
            kc = self.kind_of(pkids[0])
            if isinstance(kc, tuple) and kc[0] == "fn":
                return
        self.refuse(p, "a helper that returns %s reaches a %s the walk does not follow (a helper's return flows only through a name binding, an assignment to a name, a direct call or an argument to a helper the walk follows)" % (show(self.fn_ret[k[1]]), pk))

    def _consume(self, n, k):
        p = self.parent[id(n)]
        if p is None:
            return
        pk, pkids = p["k"], self.kids(p)
        gp = self.parent[id(p)]
        if pk in ("PropertyAccessExpression", "ElementAccessExpression") and pkids[0] is n:
            named = pk == "PropertyAccessExpression" or pkids[1]["k"] in ("StringLiteral", "NoSubstitutionTemplateLiteral")
            if isinstance(k, tuple) and k[0] in ("table", "list"):
                return   # a table's or a list's member is one of its type whatever the key spells (`pages[app]`), typed by _kind
            if not named:
                # a record's, the playwright module's or a receiver's member under a key the parse cannot read: the walk cannot
                # name what the key reaches, so the member's type is unknown (pass 9: a record's and the module's returned here)
                return self.refuse(p, "a computed member on %s the walk cannot name" % show(k))
            if isinstance(k, tuple) or k == "playwright":
                return   # a record's or the playwright module's member under a name or a string literal is typed by _member
            if gp is not None and gp["k"] == "CallExpression" and self.kids(gp)[0] is p:
                return   # a receiver's member CALL, checked against the allow-list in _call
            return self.refuse(p, "a member read on %s that is not itself called (its value is of a type the walk does not know)" % show(k))
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
            return   # the BINDING was judged, not the target's form: _declare bound every name the target declares through _bind_pattern, or refused the element it could not bind
        if pk == "BinaryExpression":
            if p.get("op") in LOGICAL or p.get("op") in ("=", ","):
                return   # a branch the expression inherits; an assignment's target or value (_assign judged the target: a declared name, a table's member, or a refusal)
            return self.refuse(p, "%s in a %s expression" % (show(k), p.get("op")))
        if pk == "ExpressionStatement" and n["k"] == "BinaryExpression" and n.get("op") == "=":
            return
        if pk == "ReturnStatement":
            return self._returned(n, k, self._enclosing_fn(p))
        if pk == "Parameter" and pkids[-1] is n:
            return   # a default: _kind's Parameter arm bound the name or the pattern through _bind_pattern, or refused the element it could not bind
        if pk in PASS_THROUGH or pk in ("ConditionalExpression", "ArrayLiteralExpression", "PropertyAssignment", "ShorthandPropertyAssignment"):
            return   # typed by _kind: the expression inherits it, a list of it, a record holding it (a computed key is refused there)
        if pk == "PrefixUnaryExpression" and p.get("op") == "!":
            return
        if pk in ("IfStatement", "WhileStatement", "DoStatement", "ForStatement") and n["k"] != "Block":
            return
        if pk in FN_KINDS and pkids[-1] is n:
            return self._returned(n, k, p)   # an expression body
        if pk == "ForOfStatement" and pkids[1] is n:
            if isinstance(k, tuple) and k[0] == "list":
                return
            return self.refuse(p, "%s iterated" % show(k))
        return self.refuse(p, "%s reaches a %s the walk does not follow" % (show(k), pk))

    def _subtree(self, n):
        yield n
        for c in self.kids(n):
            yield from self._subtree(c)

    def _loop_header(self, n):
        """The nodes a loop's exit reads: a while's or a do's condition; a for's condition and incrementor (by the roles the
        serializer names, since the header's `;` are no children; the initializer binds, and is _declare's)."""
        if n["k"] == "WhileStatement":
            return self.kids(n)[:1]
        if n["k"] == "DoStatement":
            return self.kids(n)[-1:]
        return [c for role, c in zip(n.get("roles", []), self.kids(n)) if role in ("condition", "incrementor")]

    def _reads(self, fnid, seen):
        """Whether the helper (by id) reads a receiver, the budget, its poll or fetch: in its own body, or in a helper it calls,
        over the calls the walk follows (_invoke's edges), a seen set against cycles. A helper the walk did not resolve to a
        function is not here: a header calling one is the disclosed class."""
        if fnid in seen:
            return False
        seen.add(fnid)
        node = self.fn_nodes.get(fnid)
        if node is None:
            return False
        for m in self._subtree(node):
            k = self.kind_of(m)
            if receiverish(k) or k in AUX or (m["k"] == "Identifier" and m.get("t") == "fetch"):
                return True
        return any(self._reads(dst, seen) for src, dst in self.call_edges if src == fnid)

    def _loops(self):
        """A while, do or for statement whose HEADER holds a receiver, the budget or its poll, or calls a helper the walk
        RESOLVES to one that reads a receiver, the budget, its poll or fetch (in its body or through the helpers it calls,
        _reads), is refused: its exit depends on what it reads, a wait with no timeout this census can read. Keyed on what the
        header's callees resolve to and not on a node in the header (the maintainer's round 6, tests-1: `const c9 = async () =>
        pages.feed.locator(s).count(); while (!(await c9())) {}` passed with no refusal). The budget's waitFor is the driver's
        one receiver-reading loop, and its own `while` reads the budget's clock alone. A for-of is bounded by its iterable and
        followed (a list's elements are typed); a loop whose header reads no receiver and calls no such helper is followed
        whatever its body reads (the driver's counter loops call receivers inside); a loop whose exit is decided in its body, or
        whose header calls a helper the walk does not resolve, is the disclosed class's first member."""
        for n in self.nodes:
            if n["k"] not in LOOP_KINDS:
                continue
            for h in self._loop_header(n):
                hit = next((m for m in self._subtree(h) if receiverish(self.kind_of(m)) or self.kind_of(m) in AUX), None)
                if hit is not None:
                    self.refuse(n, "a %s whose header reads %s: a loop whose exit depends on what it reads, a wait with no timeout this census can read (the budget's poll is the driver's one such loop)" % (n["k"], show(self.kind_of(hit))))
                    break
                helper = next((m for m in self._subtree(h) if isinstance(self.kind_of(m), tuple) and self.kind_of(m)[0] == "fn" and self._reads(self.kind_of(m)[1], set())), None)
                if helper is not None:
                    self.refuse(n, "a %s whose header calls a helper that reads a receiver, the budget, its poll or fetch (resolved through the calls the walk follows): a loop whose exit depends on what it reads, a wait with no timeout this census can read" % n["k"])
                    break

    def _cycles(self):
        """A helper in a call cycle (it calls itself, directly or through other helpers, a call inside a callback of its body
        included) is refused: a recursion is a loop whose exit this census cannot read. The graph is the calls the walk follows
        (_invoke's edges, from every function enclosing the call site to the callee)."""
        graph = {}
        for src, dst in self.call_edges:
            graph.setdefault(src, set()).add(dst)
        for start in graph:
            seen, todo = set(), list(graph[start])
            while todo:
                f = todo.pop()
                if f == start:
                    self.refuse(self.fn_nodes[start], "a helper in a call cycle (it calls itself, directly or through another helper): a loop whose exit this census cannot read")
                    break
                if f not in seen:
                    seen.add(f)
                    todo += graph.get(f, ())

    def _outside_playwright(self):
        """The names refused by the road they open, wherever they appear as an identifier: a timer (bare, as a member, or bound
        to another name) or a promise constructor anywhere but the budget's own `sleep` property, and a timer there only when
        its delay is the sleep's own argument (the poll hands it capped(250); any other delay is a wait the budget does not
        bound); `Promise` read anywhere but as that constructor or as the object of a Promise.resolve or Promise.all call (an
        alias, a combinator that may never settle); `fetch` anywhere but as a callee (counted there, bare or as a member);
        `require` read as a value; `createRequire` read as a value; REFUSED_NAMES; and a require or an import of a module the
        driver does not own (a dynamic import() and a second createRequire are refused in _call)."""
        def sleep_of(n):
            """The budget's own sleep (the function under `sleep:` in a makeBudget call) that `n` sits inside, else None."""
            p = self.parent[id(n)]
            while p is not None:
                if p["k"] == "PropertyAssignment" and self.kids(p)[0].get("t") == "sleep":
                    q = self.parent[id(p)]
                    while q is not None:
                        if q["k"] == "CallExpression" and self.kids(q)[0].get("t") == "makeBudget":
                            return self.kids(p)[-1]
                        q = self.parent[id(q)]
                p = self.parent[id(p)]
            return None

        def delay_is_the_sleeps_own(n, fn):
            """A timer called under the sleep whose delay argument is the sleep's own first parameter (`(ms) => new Promise((r) =>
            setTimeout(r, ms))`), resolved by scope to that function; a timer bound or read there, or one handed any other
            delay, is not."""
            call = self.parent[id(n)]
            if call is None or call["k"] != "CallExpression" or self.kids(call)[0] is not n or fn["k"] not in FN_KINDS:
                return False
            args, params = self.kids(call)[1:], [c for c in self.kids(fn) if c["k"] == "Parameter"]
            if len(args) < 2 or args[1]["k"] != "Identifier" or not params or not self.kids(params[0]) or self.kids(params[0])[0].get("t") != args[1]["t"]:
                return False
            return self.declaring_scope(args[1]["t"], args[1]) is fn

        def callee_of(p):
            """The CallExpression `p` is the callee of, else None."""
            gp = self.parent[id(p)]
            return gp if gp is not None and gp["k"] == "CallExpression" and self.kids(gp)[0] is p else None

        def in_budget_maker(n):
            """Whether `n` sits inside the function bound to `makeBudget` (`const makeBudget = (...) => {...}`), the budget's
            own maker, whose `bounded` races a read against the budget's sleep."""
            p = self.parent[id(n)]
            while p is not None:
                if p["k"] in FN_KINDS:
                    q = self.parent[id(p)]
                    if q is not None and q["k"] == "VariableDeclaration" and self.kids(q)[0].get("t") == "makeBudget":
                        return True
                p = self.parent[id(p)]
            return False
        why = "a wait outside playwright and the budget (a timer or a promise constructor that is not the budget's sleep)"
        for n in self.nodes:
            if n["k"] == "NewExpression" and self.kids(n) and self.kids(n)[0].get("t") == "Promise" and sleep_of(n) is None:
                self.refuse(n, why)
            if n["k"] != "Identifier":
                continue
            t, p = n["t"], self.parent[id(n)]
            at = p or n
            if t in TIMERS:
                fn = sleep_of(n)
                if fn is None:
                    self.refuse(at, why)
                elif not delay_is_the_sleeps_own(n, fn):
                    self.refuse(at, "a timer under the budget's sleep whose delay is not the sleep's own argument: a wait the budget does not bound (the poll hands the sleep capped(250))")
            elif t in REFUSED_NAMES:
                self.refuse(at, "%s: %s" % (t, REFUSED_NAMES[t]))
            elif t == "Promise":
                as_ctor = p is not None and p["k"] == "NewExpression" and sleep_of(n) is not None
                member = self.kids(p)[1].get("t") if p is not None and p["k"] == "PropertyAccessExpression" and self.kids(p)[0] is n else None
                as_object = member is not None and callee_of(p) is not None and (member in PROMISE_ALLOWED or (member == "race" and in_budget_maker(n)))
                if not (as_ctor or as_object):
                    self.refuse(at, "Promise read anywhere but as the budget's sleep constructor, as the object of a Promise.%s call, or as the object of the Promise.race inside the budget's own maker: an alias or another combinator is a promise this census cannot see settle, a wait with no timer name" % "/Promise.".join(PROMISE_ALLOWED))
            elif t == "fetch":
                bare = p is not None and p["k"] == "CallExpression" and self.kids(p)[0] is n
                member = p is not None and p["k"] == "PropertyAccessExpression" and self.kids(p)[1] is n and callee_of(p) is not None
                if bare or member:
                    self.fetches.append(self.line(n))
                else:
                    self.refuse(at, "fetch read as a value or named where it is not called: an alias carries the uncounted wait under another name")
            elif t == "require" and self.is_reference(n) and not (p is not None and p["k"] == "CallExpression" and self.kids(p)[0] is n):
                self.refuse(at, "require read as a value (an alias or a member of it loads a module the census does not see)")
            elif t == "createRequire" and p is not None and p["k"] != "ImportSpecifier" and not (p["k"] == "CallExpression" and self.kids(p)[0] is n):
                self.refuse(at, "createRequire read as a value (an alias makes a loader the census does not follow)")
        for mod, line in self.imports:
            if mod not in IMPORTS_ALLOWED:
                self.refuse_at(line, "import ... from %r" % mod, "an import of a module the census does not know")
        for mod, line in self.requires:
            if mod not in REQUIRE_ALLOWED:
                self.refuse_at(line, "require(%r)" % (mod,), "a require of a module the census does not know" if mod is not None else "a require whose module is not a string literal: a name built at run time")


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
            "dwells": sorted(dwells), "fetches": len(w.fetches), "calls": w.calls, "waits": w.waits, "poll_bindings": w.poll_bindings,
            "require_bindings": w.require_bindings, "budget_bindings": w.budget_bindings, "bounded": w.bounded_reads, "globals": sorted(w.globals), "member_reads": sorted(w.member_reads),
            "options": sorted(w.options), "walk": w}


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
SEL = "cfg.provSel"
# The plants (the author's pass 9 of PR 857): one JS line each, and the class of red this census must give it; `passed` for the CONTROLS
# and the DISCLOSED rows alone. Provenance: the rows from var-held-page to firefox-launch are the prep note's tables for
# censuses 3, 4 and 5 (the owner's read-only prep over the pass-8 head) but for computed-method, newline-chain, return-stmt,
# param-default, method-ref-binding and reflect-get, the builder's from the maintainer's round 4 fixlist's shapes (a returned receiver, a
# computed member) and its own, and logical-or, the addendum's; timer-as-member, timer-import and identity-control are the
# builder's; every row from getter-return on is the fixer pass's (pass 9's verifiers' shapes and the fixer's own), and the
# rows from walked-param-identity on are pass 10's (the maintainer's round 5 shapes and the method ruling's). Through the
# pass-8 head's regex census these rows were red and the rest passed: of the builder's, var-held-page, var-held-locator,
# computed-method, newline-chain, paren-receiver, param-default, space-before-dot-wait, method-ref-binding, reflect-get,
# third-fetch, set-default-timeout, bracket-page-control and template-string (four of them by an accident of spelling), and of
# the fixer's, fetch-globalthis; the review record outside the repo carries that table, and no count is kept here.
CONTROLS = ("count-control", "identity-control", "hook-control", "evaluate-fn-control", "bracket-locator-count-control", "evaluate-busy-bounded-control")
# the disclosed class, passing by disclosure (the rule is the module docstring's Disclosed paragraph; these are its witness rows,
# by member): a wait with no timer, promise, script, module or playwright name as a node, and a call on a root the walk resolves
# to no receiver and reads nothing of (a known global or a known member of a global or a module, with any argument, however reached)
DISCLOSED = ("busy-loop", "thenable-await", "poll-break-loop", "poll-header-unresolved-helper", "cpu-bound-work", "array-sort-cpu", "date-now-bound-busy",
             "fs-blocking-read", "fs-blocking-fifo", "fs-alias-read", "fs-member-bound", "named-import-known-member", "fs-default-import-read", "fs-namespace-import-read")
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
    # a receiver returned from a helper the walk follows to no call, or a helper that returns one placed where its calls are unseen
    ("getter-return", "const gobj = { get p() { return pages.feed; } }; await gobj.p.locator(%s).textContent();" % SEL, "refused"),
    ("object-method-return", "const om = { m() { return pages.feed; } }; await om.m().locator(%s).textContent();" % SEL, "refused"),
    ("class-method-return", "class CM { m() { return pages.feed; } } await new CM().m().locator(%s).textContent();" % SEL, "refused"),
    ("fn-call-via-call", "function hf() { return pages.feed; } await hf.call(null).locator(%s).textContent();" % SEL, "refused"),
    ("callback-return", "const pf = [1].map(() => pages.feed)[0]; await pf.locator(%s).textContent();" % SEL, "refused"),
    ("reduce-callback", "const pr2 = [0].reduce(() => pages.feed, null); await pr2.locator(%s).textContent();" % SEL, "refused"),
    ("arrow-in-array-invoked", "const fns = [() => pages.feed]; await fns[0]().locator(%s).textContent();" % SEL, "refused"),
    ("fn-in-record-invoked", "const rec2 = { g: () => pages.feed }; await rec2.g().locator(%s).textContent();" % SEL, "refused"),
    ("fn-returned-fn", "const outer = () => () => pages.feed; await outer()().locator(%s).textContent();" % SEL, "refused"),
    # ...and the helpers the walk does follow to a call, whose returned page reaches the allow-list
    ("async-iife-return", "const pi = await (async () => pages.feed)(); await pi.locator(%s).textContent();" % SEL, "unlisted"),
    ("fn-passed-then-invoked", "const inv = (f) => f(); await inv(() => pages.feed).locator(%s).textContent();" % SEL, "unlisted"),
    ("function-decl", "function gp() { return pages.feed; } await gp().locator(%s).textContent();" % SEL, "unlisted"),
    ("async-fn-return-awaited", "async function ga() { return pages.feed; } await (await ga()).locator(%s).textContent();" % SEL, "unlisted"),
    # script text handed to the page (a string, a template, a bound value, a Function, eval): not this census's parse
    ("evaluate-string-timer", 'await pages.feed.evaluate("new Promise((r) => setTimeout(r, 100000))");', "refused"),
    ("evaluate-new-function", 'await pages.feed.evaluate(new Function("return new Promise((r) => setTimeout(r, 100000))"));', "refused"),
    ("evaluate-template", "await pages.feed.evaluate(`new Promise((r) => setTimeout(r, 100000))`);", "refused"),
    ("evaluate-bound-string", 'const es = "new Promise((r) => setTimeout(r, 100000))"; await pages.feed.evaluate(es);', "refused"),
    ("waitforfunction-string", 'await pages.feed.waitForFunction("false", null, { timeout: budget.capped(cfg.pageWaitMs) });', "refused"),
    ("addinitscript-string", 'await pages.feed.addInitScript("setTimeout(() => {}, 100000)");', "refused"),
    ("addinitscript-string-bound", 'const hs = "while (true) {}"; await pages.feed.addInitScript(hs);', "refused"),
    ("eval-timer", 'await eval("new Promise((r) => setTimeout(r, 100000))");', "refused"),
    ("indirect-eval", 'const ev = eval; await ev("new Promise((r) => setTimeout(r, 100000))");', "refused"),
    ("function-ctor-bare", 'await Function("return new Promise((r) => setTimeout(r, 100000))")();', "refused"),
    ("hook-control", "await pages.feed.addInitScript(hook, { stripCaps: false });", "passed"),
    ("evaluate-fn-control", 'await budget.bounded(pages.feed.evaluate(() => 1), "c", null);', "passed"),
    # pass 11 (the maintainer's round 6, extra4-2): a page's evaluate takes no timeout and waits on the page with no default bound, so it is
    # an untimed read allowed only as budget.bounded's first argument; unbounded, or awaited before the race, it is refused
    ("evaluate-unbounded", "await pages.feed.evaluate(() => 1);", "refused"),
    ("evaluate-awaited-before-race", 'await budget.bounded(await pages.feed.evaluate(() => 1), "c", null);', "refused"),
    ("evaluate-bound-then-raced", 'const ep = pages.feed.evaluate(() => 1); await budget.bounded(ep, "c", null);', "refused"),
    ("evaluate-busy", "await pages.feed.evaluate(() => { const t0 = Date.now(); while (Date.now() - t0 < 100000) {} });", "refused"),
    ("evaluate-busy-bounded-control", 'await budget.bounded(pages.feed.evaluate(() => { const t0 = Date.now(); while (Date.now() - t0 < 100000) {} }), "b", null);', "passed"),
    ("promise-race-outside-maker", 'const rp = await Promise.race([pages.feed.evaluate(() => 1), Promise.resolve(null)]);', "refused"),
    # a module loaded any way but the driver's
    ("dynamic-import-timers", 'const tp = await import("node:timers/promises"); await tp.scheduler.wait(100000);', "refused"),
    ("dynamic-import-bracket", 'await (await import("node:timers/promises"))["setTimeout"](100000);', "refused"),
    ("dynamic-import-built-name", 'const tp3 = await import("node:" + "timers/promises"); await tp3["set" + "Timeout"](100000);', "refused"),
    ("createrequire-child-process", 'const rq2 = createRequire(process.env.EXT_PKG); rq2("child_process").execSync("sleep 100");', "refused"),
    ("createrequire-import-meta", 'const req4 = createRequire(import.meta.url); req4("child_process").execSync("sleep 100");', "refused"),
    ("require-alias", 'const rq = require; const tp2 = rq("node:timers/promises"); await tp2.scheduler.wait(100000);', "refused"),
    ("require-built-name", 'const cp = require("child_" + "process"); cp.execSync("sleep 100");', "refused"),
    # Promise read as anything but the sleep's constructor or Promise.resolve/Promise.all; fetch as anything but a callee
    ("promise-alias", "const PC = Promise; await new PC(() => {});", "refused"),
    ("promise-reject-alias", "const PR = Promise.reject; await PR(1).catch(() => {});", "refused"),
    ("promise-any-empty", "await Promise.any([]).catch(() => {});", "refused"),
    ("promise-withresolvers", "const { promise: pw } = Promise.withResolvers(); await pw;", "refused"),
    ("promise-race-empty", "await Promise.race([]);", "refused"),
    ("fetch-alias", "const f2 = fetch; await f2(cfg.tunnelsUrl);", "refused"),
    ("fetch-globalthis", "await globalThis.fetch(cfg.tunnelsUrl);", "refused"),
    # a wait spelled without a timer name, and the global object's members by string
    ("atomics-wait", "Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100000);", "refused"),
    ("atomics-alias", "const AW = Atomics; AW.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 100000);", "refused"),
    ("globalthis-string-timer", 'globalThis["set" + "Timeout"](() => {}, 100000);', "refused"),
    # the disclosed class (DISCLOSED; the rule is the module docstring's Disclosed paragraph), its first member: no timer, promise,
    # script, module or playwright name as a node of the tree
    ("busy-loop", "for (const t0 = Date.now(); Date.now() - t0 < 100000;) {}", "passed"),
    ("thenable-await", "await { then() {} };", "passed"),
    # pass 10 (the maintainer's round 5, tests-1): an identity helper, an arrow whose expression body is a bare identifier, returns its parameter
    ('walked-param-identity', 'const asPage = (page) => page; await asPage(pages.feed).locator(cfg.provSel).textContent();', 'unlisted'),
    ('identity-bound-then-read', 'const asP3 = (page) => page; const p9 = asP3(pages.feed); await p9.locator(cfg.provSel).textContent();', 'unlisted'),
    ('async-identity', 'const asPA = async (page) => page; await (await asPA(pages.feed)).locator(cfg.provSel).textContent();', 'unlisted'),
    ('identity-unwalked-param', 'const asQ = (q) => q; await asQ(pages.feed).locator(cfg.provSel).textContent();', 'unlisted'),
    ('arrow-returns-table', 'const getT = () => pages; await getT().feed.locator(cfg.provSel).textContent();', 'unlisted'),
    # pass 10 (the maintainer's round 5, correctness-1): a record's or the playwright module's member under a key the parse cannot read is refused, a literal key typed
    ('record-computed', 'const kk = "p"; const box9 = { p: pages.feed }; await box9[kk].locator(cfg.provSel).textContent();', 'refused'),
    ('record-computed-key', 'const kk2 = "p"; const rec9 = { [kk2]: pages.feed }; await rec9.p.locator(cfg.provSel).textContent();', 'refused'),
    ('playwright-computed', 'const pw = require("playwright"); const b3 = await pw["chrom" + "ium"].launch({}); const c3 = await b3.newContext({}); const p3 = await c3.newPage(); await p3.locator(cfg.provSel).textContent();', 'refused'),
    ('nested-computed', 'const k8 = "p"; const outer2 = { in: { p: pages.feed } }; await outer2.in[k8].locator(cfg.provSel).textContent();', 'refused'),
    ('optional-computed', 'const k6 = "p"; const box6 = { p: pages.feed }; await box6?.[k6].locator(cfg.provSel).textContent();', 'refused'),
    ('template-key', 'const box7 = { p: pages.feed }; await box7[`${"p"}`].locator(cfg.provSel).textContent();', 'refused'),
    ('playwright-var-key', 'const bn = "chromium"; const pw5 = require("playwright"); const b5 = await pw5[bn].launch({}); const c5 = await b5.newContext({}); const p5 = await c5.newPage(); await p5.locator(cfg.provSel).textContent();', 'refused'),
    ('record-bracket-literal', 'const box4 = { p: pages.feed }; await box4["p"].locator(cfg.provSel).textContent();', 'unlisted'),
    # pass 10 (the METHOD, the maintainer's round 5): a FREE name, bound by no scope and no KNOWN_GLOBALS name, is refused wherever it is read
    ('free-name-call', 'fs2.readFileSync("/dev/stdin", "utf8");', 'refused'),
    ('unread-global', 'structuredClone({});', 'refused'),
    ('free-name-member-read', 'const Q9 = Reflect.ownKeys;', 'refused'),
    # pass 10: the maintainer's round 4 spellings that had no row of their own (bracket-spelled waits on a page and on the table, spaces around
    # every dot, an unbound root read by bracket, and a bracket-spelled locator count as a control)
    ("bracket-dwell", 'await pages.feed["waitForTimeout"](60000);', "wait"),
    ("bracket-table-dwell", 'await pages["feed"]["waitForTimeout"](60000);', "wait"),
    ("bracket-table-wait-uncapped", 'await pages[APPS[0]]["waitForFunction"](() => true);', "wait"),
    ("spaces-around-dots", "await pages . feed . locator(cfg.provSel) . textContent();", "unlisted"),
    ("unbound-root-bracket", 'await pages2["feed"].locator(cfg.provSel).textContent();', "refused"),
    ("bracket-locator-count-control", 'await pages.feed["locator"](cfg.provSel).count();', "passed"),
    # pass 10 (the METHOD, one level down): a member of a known global or of a loaded module is one the driver reads (KNOWN_MEMBERS) or a refusal
    ('process-binding-timers', 'const tm = process.binding("timers");', 'refused'),
    ('global-computed-member', 'process["bind" + "ing"]("timers");', 'refused'),
    ('global-alias-member', 'const P2 = process; P2.binding("timers");', 'refused'),
    ('fs-new-member', 'fs.watchFile(cfg.fifo, () => {});', 'refused'),
    ('fs-promises', 'await fs.promises.readFile(cfg.fifo, "utf8");', 'refused'),
    ('fs-opensync', 'const fd = fs.openSync("/dev/stdin", "r"); fs.readSync(fd, new Uint8Array(1));', 'refused'),
    ('fs-computed-member', 'fs["read" + "FileSync"]("/dev/stdin", "utf8");', 'refused'),
    ('named-import-new-member', 'import { watchFile } from "node:fs"; watchFile(cfg.fifo, () => {});', 'refused'),
    # pass 10 (the maintainer's round 5, extra5-3): the disclosed class's second member, the driver's own module member called with any argument, however reached
    ('fs-blocking-read', 'fs.readFileSync("/dev/stdin", "utf8");', 'passed'),
    ('fs-blocking-fifo', 'const raw = fs.readFileSync(cfg.fifo, "utf8"); out.raw = raw.length;', 'passed'),
    ('fs-alias-read', 'const F = fs; F.readFileSync("/dev/stdin", "utf8");', 'passed'),
    ('fs-member-bound', 'const rfs = fs.readFileSync; rfs("/dev/stdin", "utf8");', 'passed'),
    ('named-import-known-member', 'import { readFileSync as rfs2 } from "node:fs"; rfs2("/dev/stdin", "utf8");', 'passed'),
    # pass 10's fixer pass (the pattern binder and the declaring scope): a destructuring element the walk cannot bind is refused,
    # one it can is followed to any depth, and an assignment from inside a closure types the outer name
    ("nested-object-destructure", "const { a: { b: nb } } = { a: { b: pages.feed } }; await nb.locator(%s).textContent();" % SEL, "unlisted"),
    ("nested-array-destructure", "const [[nc]] = [[pages.feed]]; await nc.locator(%s).textContent();" % SEL, "unlisted"),
    ("object-rest-destructure", "const { ...rst } = { p: pages.feed }; await rst.p.locator(%s).textContent();" % SEL, "refused"),
    ("array-rest-destructure", "const [...restA] = [pages.feed]; await restA[0].locator(%s).textContent();" % SEL, "refused"),
    ("element-default-destructure", "const { p: pd = null } = { p: pages.feed }; await pd.locator(%s).textContent();" % SEL, "refused"),
    ("for-of-destructure", "for (const { p: fp } of [{ p: pages.feed }]) await fp.locator(%s).textContent();" % SEL, "unlisted"),
    ("param-destructure-default", "const rdd = ({ p } = { p: pages.feed }) => p.locator(%s).textContent(); await rdd();" % SEL, "unlisted"),
    ("closure-assigns-outer", "let cap; const setCap = () => { cap = pages.feed; }; setCap(); await cap.locator(%s).textContent();" % SEL, "unlisted"),
    ("iife-assigns-outer", "let ip; (() => { ip = pages.feed; })(); await ip.locator(%s).textContent();" % SEL, "unlisted"),
    ("callback-assigns-outer", "let onp; [1].forEach(() => { onp = pages.feed; }); await onp.locator(%s).textContent();" % SEL, "unlisted"),
    ("closure-fills-table", "const tbl2 = {}; const fill = () => { tbl2.p = pages.feed; }; fill(); await tbl2.p.locator(%s).textContent();" % SEL, "unlisted"),
    # pass 10's fixer pass: the budget is one and its sleep's timer takes the sleep's own delay; a loop whose header reads a
    # receiver, the budget or its poll, and a helper in a call cycle, are refused; a receiver call's options are the driver's
    ("second-budget-slow-sleep", 'const budget2 = makeBudget({ budgetMs: 1, now: Date.now, sleep: () => new Promise((r) => setTimeout(r, 100000)), out }); await budget2.waitFor(() => false, 1, "w");', "refused"),
    ("sleep-nested-timer", 'const budget3 = makeBudget({ budgetMs: 1, now: Date.now, sleep: () => { const q = () => new Promise((r) => setTimeout(r, 100000)); return q(); }, out }); await budget3.waitFor(() => false, 1, "w");', "refused"),
    ("sleep-delay-added", "const budget4 = makeBudget({ budgetMs: 1, now: Date.now, sleep: (ms) => new Promise((r) => setTimeout(r, ms + 100000)), out });", "refused"),
    ("receiver-header-loop", "while (!(await pages.feed.locator(%s).count())) {}" % SEL, "refused"),
    ("poll-header-loop", 'while (!(await waitFor(() => false, 1, "w"))) {}', "refused"),
    ("for-incrementor-receiver", "for (let i9 = 0; i9 < 2; i9 += await pages.feed.locator(%s).count()) {}" % SEL, "refused"),
    ("recursive-poll", "const pollC = async () => (await pages.feed.locator(%s).count()) || pollC(); await pollC();" % SEL, "refused"),
    ("mutual-recursion", "const pa = async () => (await pages.feed.locator(%s).count()) || pb(); const pb = async () => pa(); await pa();" % SEL, "refused"),
    ("callback-recursion", "const pr = async () => { [1].forEach(() => pr()); return pages.feed.locator(%s).count(); }; await pr();" % SEL, "refused"),
    ("launch-slowmo", "const b4 = await chromium.launch({ slowMo: 100000 }); const c4 = await b4.newContext({}); const p4 = await c4.newPage(); await p4.goto(cfg.urls[APPS[0]], { timeout: budget.capped(cfg.pageWaitMs) }); await b4.close();", "refused"),
    ("newcontext-unread-option", 'const c7 = await browser.newContext({ reducedMotion: "reduce" }); const p7 = await c7.newPage(); await p7.goto(cfg.urls[APPS[0]], { timeout: budget.capped(cfg.pageWaitMs) });', "refused"),
    ("goto-waituntil", 'await pages.feed.goto(cfg.urls[APPS[0]], { timeout: budget.capped(cfg.pageWaitMs), waitUntil: "networkidle" });', "refused"),
    ("options-spread", "await pages.feed.goto(cfg.urls[APPS[0]], { ...{ timeout: 60000 } });", "refused"),
    ("options-computed-key", 'await pages.feed.locator(%s).waitFor({ ["timeout"]: 60000 });' % SEL, "refused"),
    # the disclosed class's first member, redrawn as control flow: a loop whose exit is decided in its body
    ("poll-break-loop", "for (;;) { if (await pages.feed.locator(%s).count()) break; }" % SEL, "passed"),
    # pass 11 (the maintainer's round 6, tests-1): the same poll one call out of the header, two calls out, the budget one call out and a
    # fetch behind a helper are refused (the header's callees resolved over the calls the walk follows); a poll behind a helper the walk
    # does not resolve (one held in a literal's member) is the disclosed class's first member, pinned as passing
    ("poll-header-one-out", "const c9 = async () => pages.feed.locator(%s).count(); while (!(await c9())) {}" % SEL, "refused"),
    ("poll-header-two-hop", "const inner7 = async () => pages.feed.locator(%s).count(); const outer7 = async () => inner7(); while (!(await outer7())) {}" % SEL, "refused"),
    ("budget-header-one-out", "const lf = () => budget.left(); while (lf() > 0) {}", "refused"),
    ("fetch-header-helper", "const fh = async () => (await fetch(cfg.tunnelsUrl)).ok; while (!(await fh())) {}", "refused"),
    ("poll-header-unresolved-helper", "const o9 = { c: async () => pages.feed.locator(%s).count() }; while (!(await o9.c())) {}" % SEL, "passed"),
    # pass 11 (the maintainer's round 6, correctness-1): a for-of whose target is no declaration binds no element and is refused at the
    # statement, in every target spelling: a bound name, an object pattern, a member, an array pattern, and `for await` over a bound name
    ("for-of-bound-name", "let fo1; for (fo1 of [pages.feed]) await fo1.locator(%s).textContent();" % SEL, "refused"),
    ("for-of-object-target", "let fo2; for ({ p: fo2 } of [{ p: pages.feed }]) await fo2.locator(%s).textContent();" % SEL, "refused"),
    ("for-of-member-target", "for (out.fo3 of [pages.feed]) await out.fo3.locator(%s).textContent();" % SEL, "refused"),
    ("for-of-array-target", "let fo4; for ([fo4] of [[pages.feed]]) await fo4.locator(%s).textContent();" % SEL, "refused"),
    ("for-await-bound-name", "let fo5; for await (fo5 of [pages.feed]) await fo5.locator(%s).textContent();" % SEL, "refused"),
    ("cpu-bound-work", '"x".repeat(2 ** 30);', "passed"),
    ("array-sort-cpu", "new Array(2 ** 26).fill(0).sort();", "passed"),
    ("date-now-bound-busy", "const nowF = Date.now; for (const t0 = nowF(); nowF() - t0 < 100000;) {}", "passed"),
    # ...and the second member through another import binding of the same module
    ("fs-default-import-read", 'import nfs from "node:fs"; nfs.readFileSync("/dev/stdin", "utf8");', "passed"),
    ("fs-namespace-import-read", 'import * as nfs2 from "node:fs"; nfs2.readFileSync("/dev/stdin", "utf8");', "passed"),
)


# The synthetic cells' prelude: every name a cell reads is declared here (a free name is a refusal), so the cells exercise the
# shapes they name and not the free-name rule; `makeBudget` is a stub binding (_call types the callee by its name), `require`
# the driver's own loader spelling, and the rest untyped locals. ROOT_JS adds the driver's roots: the playwright destructuring,
# a context, and the page table written once.
PRELUDE_NAMES_JS = "let makeBudget, s, x, u, f, fn, app, cfg, APPS, mth, read, Wrapper, holder; "
PRELUDE_JS = 'import { createRequire } from "node:module"; const require = createRequire(process.env.EXT_PKG); ' + PRELUDE_NAMES_JS + "const budget = makeBudget({}); "
ROOT_JS = PRELUDE_JS + 'const { chromium } = require("playwright"); const context = await (await chromium.launch({})).newContext({}); const pages = {}; pages[app] = await context.newPage();\n'

REFUSED_CELLS = {
    "member-read": ("await pages.feed.request.get(u);", "a member read on a page that is not itself called"),
    "member-bound": ("const wf = pages.feed.waitForFunction;", "a member read on a page that is not itself called"),
    "computed": ("await pages.feed.locator(s)[mth]();", "a computed member call on a locator the walk cannot name"),
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
    # pass 9's fixer pass's roads
    "return-uninvoked": ("const cb = [1].map(() => pages.feed);", "returned from a helper the walk follows to no call"),
    "return-method": ("const om = { m() { return pages.feed; } };", "returned from a method, an accessor or a constructor"),
    "return-getter": ("const go = { get p() { return pages.feed; } };", "returned from a method, an accessor or a constructor"),
    "helper-in-literal": ("const fns = [() => pages.feed];", "a helper that returns a page reaches a ArrayLiteralExpression"),
    "helper-member": ("function hf() { return pages.feed; } await hf.call(null);", "a helper that returns a page reaches a PropertyAccessExpression"),
    "dynamic-import": ('const tp = await import("node:timers/promises");', "a dynamic import()"),
    "second-createrequire": ("const rq2 = createRequire(process.env.EXT_PKG);", "a createRequire beyond the driver's one"),
    "require-alias": ("const rq = require;", "require read as a value"),
    "require-built": ('const cp2 = require("child_" + "process");', "a require whose module is not a string literal"),
    "eval": ('await eval("1");', "eval"),
    "function-ctor": ('new Function("return 1");', "Function"),
    "script-string": ('await pages.feed.evaluate("1");', "a script handed to evaluate as anything but a function literal"),
    "script-bound-string": ('const es = "1"; await pages.feed.evaluate(es);', "a script handed to evaluate as anything but a function literal"),
    "script-init": ('await pages.feed.addInitScript("1");', "a script handed to addInitScript as anything but a function literal"),
    "promise-alias": ("const PC = Promise;", "Promise read anywhere but"),
    "promise-race": ("await Promise.race([]);", "Promise read anywhere but"),
    "fetch-alias": ("const f2 = fetch;", "fetch read as a value"),
    "atomics": ("Atomics.wait(x, 0, 0, 1);", "Atomics"),
    "globalthis": ("globalThis.x = 1;", "globalThis"),
    "computed-callee": ('x["a" + "b"]();', "a computed member call on a value the walk does not type"),
    # pass 11 (the maintainer's round 6, extra4-2): an untimed read outside the budget's race
    "evaluate-unbounded": ("await pages.feed.evaluate(() => 1);", "page.evaluate outside budget.bounded"),
    # pass 10 (the maintainer's round 5, tests-2): the branches no cell and no PLANTS row fired, each with its own cell now, so the
    # derived coverage assertion below is green (it is what closes the class; these cells are what it needs)
    "ternary-two-types": ("const p = cfg.x ? pages.feed : pages.feed.locator(s);", "yields a page and a locator"),
    "budget-unknown-call": ("const budget2 = makeBudget({}); budget2.spend(1);", "a call on the budget the census does not know"),
    "rest-parameter": ("const fr = (...rest) => 1; fr(pages.feed);", "a helper parameter the walk cannot name"),
    "table-write-mismatch": ("const tbl = {}; tbl.a = pages.feed; tbl.b = context;", "written into a table of"),
    "nested-assign-target": ("holder.inner.p = pages.feed;", "assigned to a target the walk does not follow"),
    "return-outside-function": ("return pages.feed;", "returned outside a function"),   # a return at module level: the parser accepts it (a grammar error the checker would report), the walk refuses it
    "destructure-table": ("const [q] = pages;", "destructured by an array pattern: the walk types no element of it"),
    "createrequire-as-value": ("const cr = createRequire;", "createRequire read as a value"),
    # pass 10 (the METHOD): the roots the walk resolves to no receiver
    "free-name": ("fs2.readFileSync(u);", "a free name no scope of the tree binds"),
    "unread-member": ("process.binding(u);", "a member of the global process the driver does not read"),
    "root-computed-member": ('process["bind" + "ing"](u);', "a computed member on the global process"),
    "module-called": ('import fs from "node:fs"; fs();', "the module node:fs (an import binding) called as a function"),
    "module-member-member": ("createRequire.call(null, u);", "a member of createRequire imported from node:module, a value the walk reads nothing of"),
    "computed-record-member": ("const box = { p: pages.feed }; await box[mth].locator(s).count();", "a computed member on an object holding {p: a page}"),
    "computed-key-property": ("const rec = { [mth]: pages.feed };", "a page placed under a property name the walk cannot read"),
    # pass 10's fixer pass: the pattern binder (_bind_pattern) refuses every element it cannot bind on a receiverish value, in a
    # declaration, a for-of and a parameter default alike, and an assignment types the name where it is declared
    "pattern-rest": ("const { ...rst } = { p: pages.feed };", "destructured by an element the walk cannot bind (a rest element, a default, a computed property name)"),
    "pattern-default": ("const { p = x } = { p: pages.feed };", "destructured by an element the walk cannot bind (a rest element, a default, a computed property name)"),
    "pattern-computed-key": ("const { [mth]: cq } = { p: pages.feed };", "destructured by an element the walk cannot bind (a rest element, a default, a computed property name)"),
    "pattern-member-of-receiver": ("const { keyboard } = pages.feed;", "a member of a page read by a pattern: its value is of a type the walk does not know"),
    "pattern-over-root-member": ('import fs from "node:fs"; const { readFileSync: { call: rc } } = fs;', "a pattern over node:fs.readFileSync, a member the walk reads nothing of"),
    "array-pattern-rest": ("const [...ra] = [pages.feed];", "destructured by an element the walk cannot bind (a rest element, a default)"),
    "for-of-pattern-rest": ("for (const { ...fr } of [{ p: pages.feed }]) {}", "destructured by an element the walk cannot bind"),
    "param-pattern-rest": ("const rp = ({ ...pr } = { p: pages.feed }) => 1;", "destructured by an element the walk cannot bind"),
    "closure-two-types": ("let cv; const set1 = () => { cv = pages.feed; }; const set2 = () => { cv = context; };", "cv is bound to a page and to a context"),
    # pass 10's fixer pass: one budget, the sleep's delay, a loop's header, a call cycle, a receiver call's options
    "second-budget": ("const budget2 = makeBudget({});", "a makeBudget beyond the driver's one module-level"),
    "sleep-delay": ("const budget3 = makeBudget({ sleep: (ms) => new Promise((r) => setTimeout(r, 1000)) });", "a timer under the budget's sleep whose delay is not the sleep's own argument"),
    # the delay's NAME is the parameter's but an inner declaration shadows it: resolved by scope, not by spelling
    "sleep-shadowed-delay": ("const budget5 = makeBudget({ sleep: (ms) => new Promise((r) => { const ms = 100000; setTimeout(r, ms); }) });", "a timer under the budget's sleep whose delay is not the sleep's own argument"),
    "receiver-loop": ("while (!(await pages.feed.locator(s).count())) {}", "a WhileStatement whose header reads a locator"),
    # pass 11 (the maintainer's round 6, tests-1 and correctness-1): a header's callee resolved to a reading helper; a for-of with no declaration
    "helper-header-loop": ("const c9 = async () => pages.feed.locator(s).count(); while (!(await c9())) {}", "a WhileStatement whose header calls a helper that reads"),
    "for-of-no-declaration": ("let fk; for (fk of [pages.feed]) {}", "a for-of over a list of a page whose element the walk did not bind"),
    "budget-loop": ("do {} while (budget.left() > 0);", "a DoStatement whose header reads a budget"),
    "call-cycle": ("const pc = async () => (await pages.feed.locator(s).count()) || pc(); await pc();", "a helper in a call cycle"),
    "unread-option": ('await pages.feed.goto(u, { timeout: budget.capped(x), waitUntil: "load" });', "page.goto({ waitUntil }): an option the driver does not pass"),
    "computed-option": ("await pages.feed.goto(u, { [mth]: 1 });", "an option of page.goto the walk cannot name"),
}
# the two-round convergence bound (pass 10, the maintainer's round 5 tests-2): a page reaches a binding through a helper's return, which the fixpoint types
# in its second round; under rounds=1 the walk refuses "did not converge", and under the default bound the same source is clean
CONVERGENCE_JS = ROOT_JS + "const gp = () => pages.feed; const p2 = gp(); await p2.locator(s).count();"


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
        with open(os.path.join(EXT, "package-lock.json"), encoding="utf-8") as f:
            pinned = json.load(f)["packages"]["node_modules/typescript"]["version"]
        if cls.ts_version != pinned:
            raise AssertionError("the parser is typescript %s but vscode-extension/package-lock.json pins %s: a refreshed lock or a drifted node_modules (the docstring "
                                 "names the lock's version as the parser's, so the two must agree)" % (cls.ts_version, pinned))

    def _census(self, name, src):
        diagnostics, tree = self.trees[name]
        self.assertEqual(diagnostics, [], "%s parses clean as a JS module under typescript %s: %r" % (name, self.ts_version, diagnostics))
        return census(src, tree)

    def test_the_driver_walks_clean_and_every_wait_draws_on_the_budget(self):
        """The census over the driver as written: every receiver-typed expression is consumed by a shape the walk follows
        (no refusal), every call on a receiver is one ALLOWED_CALLS names for its kind, the (kind, method) pairs the driver
        makes today, the set the assertion below holds, are all seen (the walk is not vacuous), every wait site is a listed form whose timeout is one
        budget.capped(...) call or a fixed dwell the arithmetic counts, the five forms the driver uses are all seen, the
        bare `waitFor(` sites are the poll because the module scope binds that name to `budget.waitFor` exactly once, no
        timer or promise constructor sits outside the budget's sleep, the driver imports and requires its own modules only,
        the free names the driver reads are exactly KNOWN_GLOBALS, the members it reads on them and on its loaded modules
        exactly KNOWN_MEMBERS, the modules it imports exactly IMPORTS_ALLOWED and the modules it requires exactly
        REQUIRE_ALLOWED, and the options it passes its receiver calls exactly KNOWN_OPTIONS (the walk's lists over the
        unplanted driver, held equal to the tuples, so a global, a member, a module or an option the driver starts or stops
        reading is a red until the tuple says so; pass 10's fixer pass: the docstring said all three tuples were held equal
        while only two were), the module scope makes the one budget exactly once, and the two fetches stand."""
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
        self.assertEqual(c["require_bindings"], [L.DRIVER.count("\n", 0, L.DRIVER.index("const require = createRequire(")) + 1],
                         "the module scope makes the driver's one loader, `const require = createRequire(...)`, exactly once (every other createRequire is a refusal above): %r" % (c["require_bindings"],))
        self.assertEqual(c["fetches"], 2, "the driver's two fetches (ctl and tunnelsStatus) carry no timeout: the acknowledged driver_error road, DRIVER_TIMEOUT_S, "
                                          "which the arithmetic does not count; a third fetch is a new uncounted wait")
        self.assertEqual(c["globals"], sorted(KNOWN_GLOBALS), "KNOWN_GLOBALS is exactly the free names the driver reads (the names the walk resolves to no binding of the tree; "
                                                              "every other free name is a refusal, so a global the driver starts or stops reading is a red until the tuple says so): %r" % (c["globals"],))
        self.assertEqual(c["member_reads"], sorted(KNOWN_MEMBERS), "KNOWN_MEMBERS is exactly the members the driver reads on its known globals and its loaded modules (the walk "
                                                                   "reads nothing of what a member does; any other member of a root is a refusal, so one the driver starts or stops reading is a red until the tuple says so): %r" % (c["member_reads"],))
        self.assertEqual(sorted({m for m, _ in c["walk"].imports}), sorted(IMPORTS_ALLOWED), "IMPORTS_ALLOWED is exactly the modules the driver imports (an import outside it is a refusal above; "
                                                                                             "a name here that nothing imports is a stale allowance): %r" % (c["walk"].imports,))
        self.assertEqual(sorted({m for m, _ in c["walk"].requires}), sorted(REQUIRE_ALLOWED), "REQUIRE_ALLOWED is exactly the modules the driver requires: %r" % (c["walk"].requires,))
        self.assertEqual(c["options"], sorted(KNOWN_OPTIONS), "KNOWN_OPTIONS is exactly the options the driver passes its receiver calls today, by (kind, method, key) (the walk reads "
                                                             "nothing of what an option does; any other option is a refusal above, so one the driver starts or stops passing is a red until the tuple says so): %r" % (c["options"],))
        self.assertEqual(c["budget_bindings"], [L.DRIVER.count("\n", 0, L.DRIVER.index("const budget = makeBudget(")) + 1],
                         "the module scope makes the driver's one budget, `const budget = makeBudget(...)`, exactly once (every other makeBudget is a refusal above): %r" % (c["budget_bindings"],))
        self.assertGreaterEqual(len(c["waits"]), 16, "the census saw the driver's wait sites (16 at the pass-9 head): %d" % len(c["waits"]))
        evaluates = [ln for k, m, ln in c["calls"] if (k, m) == ("page", "evaluate")]
        self.assertEqual(len(c["bounded"]), len(evaluates), "every page.evaluate of the driver (%r) sits inside a budget.bounded(...) call (%r), and the budget races nothing else" % (evaluates, c["bounded"]))
        self.assertGreaterEqual(len(evaluates), 2, "the walk saw the driver's untimed reads (the snapshot and the provisional-row read): %r" % (evaluates,))

    def test_the_config_the_lab_writes_hands_the_launch_no_options(self):
        """The disclosed class's third member, pinned: the driver's `chromium.launch(cfg.launch || {})` hands the launch its
        config's `launch` key, a value the walk does not type. The config is the dict literal the lab's _drive writes to cfg.json,
        read here from the served module's parse: every key is a string constant (so the check is total) and none is `launch`,
        so the launch runs on playwright's defaults (no slowMo, its own launch timeout, LAUNCH_TIMEOUT_S, which the arithmetic
        carries as a fixed term inside DRIVER_FIXED_S: the maintainer's round 6, extra4-1), and a `launch` key added to the config is
        a red here until this census reads what it carries."""
        with open(L.__file__, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        drive = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_drive")
        dicts = [n for n in ast.walk(drive) if isinstance(n, ast.Dict) and any(isinstance(k, ast.Constant) and k.value == "driverBudgetMs" for k in n.keys)]
        self.assertEqual(len(dicts), 1, "the lab's _drive writes one config dict carrying the driver's budget: %d" % len(dicts))
        keys = [k.value if isinstance(k, ast.Constant) else None for k in dicts[0].keys]
        self.assertTrue(keys and all(isinstance(k, str) for k in keys), "every config key is a string constant, so the check reads them all: %r" % (keys,))
        self.assertNotIn("launch", keys, "the config hands the launch its options (`cfg.launch`), a value this census does not type: read them here before adding the key")
        self.assertIn("cfg.launch || {}", L.DRIVER, "the driver's launch reads its options from the config (the disclosed class's third member names this spelling)")

    def test_the_walk_types_a_receiver_however_it_is_reached_and_refuses_what_it_cannot_follow(self):
        """The instrument by cell, over synthetic sources parsed the same way: the roots and the makers; a page through a
        binding, an object literal, an array and a for-of, a ternary, `null ||`, an arrow's and a return's value, an awaited
        argument to a helper (its parameter typed from the call), a default parameter; the page table by write, read by name
        and by bracket; a parameter shadows the module's binding of the same name; a name bound to two types is refused; a
        member read not called, a computed member, a pass to an unknown callee, a template, a comparison and a constructor
        are refused; a bare waitFor is the poll only where the tree binds it; a second browser type is seen by its name. The
        refused cells are REFUSED_CELLS, at module level so the coverage cell below runs the same table."""
        root = ROOT_JS
        cells = {
            "roots": PRELUDE_JS + 'const { chromium } = require("playwright"); const b = await chromium.launch({}); const c = await b.newContext({}); const p = await c.newPage(); await p.locator(s).first().waitFor({ timeout: budget.capped(x) });',
            "table": root + "for (const app of APPS) { const page = await context.newPage(); pages[app] = page; } await pages.feed.locator(s).count(); await pages[app].goto(u, { timeout: budget.capped(x) }); for (const a of Object.keys(pages)) {}",
            "record-list-ternary": root + "const box = { p: pages.feed }; await box.p.locator(s).count(); for (const q of [pages.feed]) await q.locator(s).count(); const r = cfg.x ? pages.feed : pages.waiting; await r.locator(s).count(); const t = null || pages.feed; await t.locator(s).count();",
            "helpers": root + "const getP = () => pages.feed; await getP().locator(s).count(); const getQ = () => { return pages.feed; }; await getQ().locator(s).count(); const read = async (p) => p.locator(s).count(); await read(await pages.feed); const readD = async (p = pages.feed) => p.locator(s).count(); await readD();",
            "shadow": root + "const p = pages.feed; const outcome = (name, p) => p.then(() => true); await p.locator(s).count();",
            "poll": PRELUDE_NAMES_JS + "const budget = makeBudget({}); const waitFor = budget.waitFor; await waitFor(async () => true, 1000, \"w\"); await budget.waitFor(fn, 1, \"w\"); const inner = () => { const waitFor = async () => true; return waitFor(); };",
            "invoked-helpers": root + "const inv = (f) => f(); await inv(() => pages.feed).locator(s).count(); const pi = await (async () => pages.feed)(); await pi.locator(s).count(); "
                                      "const gp = () => pages.feed; const alias = gp; await alias().locator(s).count(); const fns = [() => 1]; await fns[0]();",
            "scripts-and-names": root + "const hk = (o) => { window.__socks = o; }; await pages.feed.addInitScript(hk, { stripCaps: false }); await budget.bounded(pages.feed.evaluate(() => 1), \"e\", null); "
                                        "await pages.feed.waitForFunction(() => true, null, { timeout: budget.capped(x) }); await Promise.all([]); const q = Promise.resolve(null); await fetch(u); await fetch(u);",
            # the budget's own maker may race a read against its sleep (BUDGET_JS's bounded); the same race anywhere else is refused (REFUSED_CELLS promise-race)
            "budget-maker-race": 'import { createRequire } from "node:module"; const require = createRequire(process.env.EXT_PKG); let s, x, u, f, fn, app, cfg, APPS, mth, read, Wrapper, holder; '
                                 "const makeBudget = ({ sleep, out }) => { const gone = {}; const bounded = async (p, what) => { const v = await Promise.race([p, sleep(1).then(() => gone)]); return v === gone ? null : v; }; return { bounded }; }; "
                                 "const budget = makeBudget({});",
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
        seen = [(k, m) for k, m, ln in census(cells["invoked-helpers"], trees["invoked-helpers"][1])["calls"] if ln > 1]
        self.assertEqual(seen.count(("page", "locator")), 3, "a page returned from a helper the walk follows to a call (an argument to a helper, an IIFE, an alias) is a page: %r" % (seen,))
        c = census(cells["scripts-and-names"], trees["scripts-and-names"][1])
        self.assertEqual(c["fetches"], 2, "fetch is counted as a callee: %r" % (c["fetches"],))
        w = census(cells["poll"], trees["poll"][1])
        self.assertEqual([(f, ln) for f, _, _, ln in w["waits"]], [("waitFor", 1), ("waitFor", 1)], "the bare call and the receiver call are the poll; inner's waitFor is its own function and no site")
        self.assertEqual(w["poll_bindings"], [("SourceFile", 1)])
        trees = parse_js([(name, root + src) for name, (src, _) in REFUSED_CELLS.items()])[1]
        for name, (src, token) in REFUSED_CELLS.items():
            with self.subTest(refused=name):
                c = census(root + src, trees[name][1])
                if token is None:
                    if name == "bare-wait":
                        self.assertEqual(c["unlisted_waits"], [("waitFor (a bare name the tree binds to no poll)", 2)], c["waits"])
                    else:
                        self.assertEqual(c["unlisted"], [("firefox", "launch", 2)], "a browser type the allow-list does not know is refused by its name: %r" % (c["calls"],))
                    continue
                self.assertTrue(any(token in why and line == 2 for line, _, why in c["refusals"]), "%s: the walk refuses the shape by line and class: %r" % (name, c["refusals"]))

    def test_every_refusal_site_of_the_walk_fires_under_a_pinned_cell(self):
        """The derived coverage (pass 10, the maintainer's round 5 tests-2: nine of the walk's refusal branches were exercised by no
        cell and no row, each deletable with the module green, and four more fired under no pin of their own). The refusal
        sites are read from this module's own source by ast (every `self.refuse(` and `self.refuse_at(` call inside class
        Walk, by line), and every REFUSED_CELLS cell, every PLANTS row, the unplanted driver and the one-round convergence cell
        are run with `Walk.refuse` and `Walk.refuse_at` spied to record the line each call came from, PER EXERCISER. What the
        cell checks, and no more (the maintainer's round 6, correctness-3: the earlier docstring claimed a cell deleted from
        under a branch was a red too, which held for 14 of 70 cells): (a) the union of the lines every exerciser fired equals
        the sites read from the source, both ways, so a refusal branch added with no cell or row that fires it is a red until
        one does, and a recorded line the source names no site at is a red; (b) every REFUSED_CELLS cell with a token fires at
        least one refusal site of its own, recorded per cell, so a cell whose source stopped exercising the walk (edited to a
        no-op, its shape now accepted) is a red naming the cell where the union alone stayed green because a PLANTS row fires
        the same line; the two token-less cells (bare-wait, second-browser) fire no refusal by design and are held to their
        verdict class instead (an unlisted wait form, an unlisted receiver call); (c) the number of sites with ONE exerciser
        and the cells that are that sole exerciser are derived and printed, not claimed, as two counts with their nouns (the sites
        whose sole exerciser is a REFUSED_CELLS cell, and the distinct cells that are those exercisers: one cell can be the sole
        exerciser of two sites, so the two differ, and pass 11's fixer pass found one print that read as both): a cell deleted
        from under a branch is a red only when it was that branch's sole exerciser, and the printed figure says how many are. Per-cell uniqueness is
        not asserted because it is false by construction: there are more cells than sites, and PLANTS rows fire most sites
        too. The convergence cell: under rounds=1 the walk refuses that it did not converge (a page reaches a binding through
        a helper's return, typed in the fixpoint's second round), and under the default bound the same source is clean and
        its one call allowed, so the pin cannot pass because the source was refused for another reason."""
        with open(os.path.realpath(__file__), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        walk = next(n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "Walk")
        sites = {n.lineno for n in ast.walk(walk) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("refuse", "refuse_at")
                 and isinstance(n.func.value, ast.Name) and n.func.value.id == "self"}
        self.assertGreaterEqual(len(sites), 30, "the walk's refusal sites, read from the source: %r" % (sorted(sites),))
        fired_by, current = {}, [None]

        def spy(fn):
            def wrapped(self, *a, **k):
                fired_by.setdefault(current[0], set()).add(inspect.currentframe().f_back.f_lineno)
                return fn(self, *a, **k)
            return wrapped
        cells = parse_js([(name, ROOT_JS + src) for name, (src, _) in REFUSED_CELLS.items()] + [("convergence", CONVERGENCE_JS)])[1]
        verdicts = {}
        with mock.patch.object(Walk, "refuse", spy(Walk.refuse)), mock.patch.object(Walk, "refuse_at", spy(Walk.refuse_at)):
            for name, (src, _) in REFUSED_CELLS.items():
                current[0] = ("cell", name)
                verdicts[name] = census(ROOT_JS + src, cells[name][1])
            for name, js, _ in PLANTS:
                current[0] = ("row", name) if js else ("driver", "driver.mjs")
                census(planted(js), self.trees[name if js else "driver.mjs"][1])
            current[0] = ("convergence", "one round")
            one = Walk(CONVERGENCE_JS, cells["convergence"][1]).run(rounds=1)
        self.assertTrue(any("did not converge in 1 rounds" in why for _, _, why in one.refusals), "the one-round walk refuses that it did not converge: %r" % (sorted(one.refusals),))
        c = census(CONVERGENCE_JS, cells["convergence"][1])
        self.assertEqual((c["refusals"], c["unlisted"]), ([], []), "the same source under the default bound is clean, so the convergence pin is not another refusal: %r" % (c["refusals"],))
        fired = set().union(*fired_by.values()) if fired_by else set()
        self.assertEqual(sorted(sites - fired), [], "refusal sites of the walk (by line) that no cell of REFUSED_CELLS, no PLANTS row, the driver and the convergence cell fire: "
                                                  "each needs a cell that exercises it, or it is a branch nothing pins")
        self.assertEqual(sorted(fired - sites), [], "refusals recorded from lines the source read names no site at (the derivation and the run disagree)")
        # (b) per cell: every token cell fires a site of its own; the two token-less cells are held to their verdict class
        silent = sorted(name for name, (_, token) in REFUSED_CELLS.items() if token is not None and not fired_by.get(("cell", name)))
        self.assertEqual(silent, [], "a REFUSED_CELLS cell that fires no refusal site of the walk: its shape is accepted now, or its source is a no-op, and the union above "
                                     "stayed green because a PLANTS row fires the same line: %r" % (silent,))
        for name, (_, token) in REFUSED_CELLS.items():
            if token is None:
                got = verdicts[name]
                self.assertTrue(got["unlisted_waits"] if name == "bare-wait" else got["unlisted"], "%s fires no refusal by design and is held to its verdict class: %r" % (name, got))
        # (c) the sole exercisers, derived and printed, never claimed
        exercisers = {site: sorted(who for who, lines in fired_by.items() if site in lines) for site in sites}
        sole = {site: who[0] for site, who in exercisers.items() if len(who) == 1}
        sole_cells = sorted({name for kind, name in sole.values() if kind == "cell"})
        sole_sites_by_a_cell = sum(1 for kind, _ in sole.values() if kind == "cell")
        print("coverage: %d refusal sites, %d cells, %d rows; %d sites have one exerciser; %d of those sites have a REFUSED_CELLS cell as their sole exerciser, and %d distinct cells are those exercisers (%s); "
              "a cell deleted from under a branch is a red only when it is that branch's sole exerciser"
              % (len(sites), len(REFUSED_CELLS), len(PLANTS), len(sole), sole_sites_by_a_cell, len(sole_cells), ", ".join(sole_cells) or "none"))

    def test_the_driver_stores_each_read_under_the_key_the_driver_bound_module_names(self):
        """The record keys the driver-bound module's wiring pin reads (WAITED_READS, UNWAITED_READS), derived here from the
        tree rather than from a spelling: every property assignment or assignment whose value is `await waitVisible(...)`
        stores a waitVisible record, every one whose value is `await visible(...)` a visible() record (`v` inside waitVisible
        is the record it builds), and no call of either is stored any other way."""
        w = Walk(L.DRIVER, self.trees["driver.mjs"][1]).run()
        stored, calls = [], {"waitVisible": 0, "visible": 0}
        for n in w.nodes:
            if n["k"] == "CallExpression" and w.kids(n)[0].get("t") in calls:
                calls[w.kids(n)[0]["t"]] += 1
                p = w.parent[id(n)]
                p = w.parent[id(p)] if p["k"] == "AwaitExpression" else None
                if p is not None and p["k"] == "PropertyAssignment":
                    stored.append((w.kids(p)[0]["t"], w.kids(n)[0]["t"]))
                elif p is not None and p["k"] == "BinaryExpression" and p.get("op") == "=" and w.kids(p)[0]["k"] == "PropertyAccessExpression":
                    stored.append((w.kids(w.kids(p)[0])[1]["t"], w.kids(n)[0]["t"]))
                elif p is not None and p["k"] == "VariableDeclaration":
                    stored.append((w.kids(p)[0]["t"], w.kids(n)[0]["t"]))
        self.assertEqual({k for k, fn in stored if fn == "waitVisible"}, set(B.WAITED_READS), stored)
        self.assertEqual({k for k, fn in stored if fn == "visible"} - {"v"}, set(B.UNWAITED_READS), stored)
        self.assertEqual((calls["waitVisible"], calls["visible"]), (len([1 for _, fn in stored if fn == "waitVisible"]), len([1 for _, fn in stored if fn == "visible"])),
                         "every call of waitVisible and of visible is stored under a key: %r" % (stored,))

    def test_every_plant_of_the_review_is_refused_by_the_class_the_table_names(self):
        """The fixture: each PLANTS row inserted into the driver and run through this census gives the verdict the row
        names, `passed` for the CONTROLS and the DISCLOSED rows and for nothing else. A row whose verdict moves is a change
        to what the census sees, and its line in PLANTS is where to say why; a DISCLOSED row that reds says the census now
        sees that shape, and the docstring's disclosed class is re-drawn."""
        self.assertEqual(len({name for name, _, _ in PLANTS}), len(PLANTS), "every plant has its own name")
        self.assertEqual({name for name, _, want in PLANTS if want == "passed"}, set(CONTROLS) | set(DISCLOSED),
                         "the rows that pass are exactly the controls and the disclosed class: %r" % (sorted(name for name, _, want in PLANTS if want == "passed"),))
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

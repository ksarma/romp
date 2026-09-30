#!/usr/bin/env python3
"""Census of romp's outbound network activity: every site that opens a connection or starts a program that may open one,
over kernel/, cli/, postal/, bin/, hooks/, ui/, vscode-extension/src, the install scripts and the one program the kernel runs
from tools/, each with its road from the table below. Run from the repository root:

    python3 scripts/network-inventory.py [root]            the sites, one line each, then the summary and the gates
    python3 scripts/network-inventory.py --table [root]    the road table the ledger entry and SECURITY.md are written from
    python3 scripts/network-inventory.py --write-expected  rewrite scripts/network-inventory-expected.json from a clean run
    python3 scripts/network-inventory.py --js-reads [root] the walked JavaScript files and the import gate's reads, as JSON

Standard library only. The script exits 1, naming the reason, on: a site with no road (UNCLASSIFIED); a row naming no site
(STALE ROW); no sites at all (a broken scan or moved roots); a declared root that is missing (SCOPE); a Python file that does
not parse (PARSE); an import the census does not know, a family module's specifier that no counted binding and no arm reads,
or a require or import on a walked line that the import gate cannot read, each unless JS_ALLOW names it, and an entry there
that names nothing or covers a different number of places (IMPORT); a road with no table entry or a table entry with no road
(TABLE); a served route whose content type, receiver, container, callee or text the served pass cannot read, a reference to
`_send` other than a call the scan reads (a read of it that is not a call's function, a store or delete of an attribute so named,
or a string equal to `_send`), a
script-running type written outside `_send`, a function that answers outside `_send`
more often than it writes a Content-Type header, a `_send` definition that writes none and is not a named frame writer, a call of
a `_send` its file binds more than once outside function bodies, or other than by one def statement, of a decorated `_send` or,
bare, in a module that
holds a star import, each unless SERVED_ALLOW names it, a script-running route whose page body it does not read, and an allowlist
entry that names nothing or covers a different number of places (SERVED); and any figure that differs from the committed counts in
scripts/network-inventory-expected.json (COUNTS): the totals, the counts by kind, by class, by road and by row key. So a scan
that finds fewer sites than the committed count, a file the walk stopped opening, or a second site inside a function that
already has a row is a loud line, not a clean report.
tests/test_price_feed_census.py runs this script over the tree and over mutated copies of it, so the guarantee is the suite's.

The walk is recursive over every declared root (os.walk; __pycache__, node_modules, symlinks and files whose name carries
.test. are skipped) and the kind of a file is its extension (.py, .js, .mjs, .cjs, .sh) or its shebang (python, node, sh):
hooks/ takes every hook whatever its extension, and ui/ and vscode-extension/src are read for the browser and editor kinds
only (a fixture of another kind below them, such as a CRLF Python sample, is skipped by kind and counted as skipped).
scripts/ and the rest of tools/ are the maintainers' release, review and bench tooling that nothing under the runtime trees
runs; the one program the kernel starts from tools/ is named in NAMED, and a string constant naming those directories from
the runtime trees is a gate (PROGRAM), so a second such program takes a place here or fails the run.
vendor/track-changents is runtime code, reached by relative imports from walked files (the dashboard's ui sources, a session
hook and the file-comments host) and by install.sh's links into ~/.claude, and it is not walked. A load written there is no
site and no line, and the import gate does not read its imports.

A row is keyed on file plus enclosing function (a Python site) or file plus tool (a shell or JavaScript line); the committed
count per row key is the guard for a second site inside a function that already has a row, and the listing names the new
line. For the Python command sites alone the committed counts also carry the program head per row key (the heads map: row
key, primitive, argv[0] as the scan renders it, with an argv the code does not spell out as RUNTIME-SUPPLIED), so a same-count
swap of a local tool for a network tool inside a rowed function is a COUNTS line naming the key, the primitive and the new
head; the residual beside it: a shell or JavaScript site is a line keyed by tool with no head figure, so a swap inside a rowed
shell or JavaScript line is caught by the count per key when it changes the tool and not when it keeps it (a curl whose URL
changes). Four classes of outbound activity this scan cannot derive are named in the table and counted on every run:
  external-program: a program started whose far end is not derivable from the argv here: a shell or an interpreter as argv[0]
    (sh, bash, node, perl, python, sys.executable), shell=True or child_process's exec, git with a subcommand the code does not
    spell out, or an argv the code does not spell out (RUNTIME-SUPPLIED marks it), whether the kernel starts it (a Python
    command site), a shell script runs it inline (the interpreter arm below), or the manager or the editor extension starts it
    (a child_process site, classed by its argv the same way). Each such site takes an explicit row with its reason and is
    never set aside as local, whatever road its row names.
  runtime-program: the external programs whose text is supplied at run time (the watch predicate, the operator's helper).
  browser-computed-url: a fetch, or a dynamic import(), in the browser or editor code whose first argument is computed at run
    time. A fetch is local only when its argument is a relative literal or a kernel-URL helper call (ku, kernelUrl, fileUrl,
    sliceUrl); an absolute literal needs a row; a computed argument is counted here and listed, and so is, in a page the kernel
    serves, a literal whose URL carries a Python format slot (`%s`, `{}`), filled at serve time; a dynamic import() in the
    gate's literal form (below) is an import and goes through the package gate, not a site.
  browser-dom-loads: the browser DOM's own loads (img, iframe, script, link and anchor src, srcset and href writes, setAttribute
    of those, HTML templates carrying them), counted by pattern over the browser and editor code and the served pages, one count
    per line that carries one (a page template inlined as one string is one line, however many it carries); the viewer's and the chat's
    rendered-markdown insertions have no line of their own and are not counted, so the browser-figures road is named from the
    gate's host-list read and the retry probe, not from a request; and the chat-media road from the pipeline's post-pass on a
    message's pictures (`mdImgPostPass`), for the same reason; the paint references of the chat's file preview and a notice
    card are a road named and not counted (below); an anchor's href write loads nothing by itself (the click that opens it is
    the clicked-link road), and a `window.open` is a site keyed file plus tool, never a load counted here.
A fifth class is named in the table and not counted, since the scan cannot see it by construction: a socket primitive called
on a receiver the census cannot resolve (an attribute-held or parameter socket) is not a site here. The scan resolves a socket
receiver as a name bound to socket.socket() in the same function, or by a tuple-literal address argument; a rule on the method
name alone would tag the backends' and transports' own connect methods, which are not sockets. tests/test_price_feed_census.py
plants one such call and holds this sentence to the behaviour.
One road is named in the table and not counted, since its loads are rendered-markdown insertions with no attribute line: the
chat's file preview (render.ts previewMdClean) and a notice card's body (feed.ts noticeBodyNodes) render markdown through the
shared sanitizer and then stripRemoteLoads (ui/webview/file-preview.ts), which reads no paint attribute, so an inline svg's
paint references load from the hosts they name; tests/test_security_price_feed.py counts by grep every call in render.ts spelled
`md(` or `userMd(`, a gap before the paren allowed, on one line (`md (t)` and `x.md(t)` among them), and every reference to
stripRemoteLoads (a call, an import, an alias) in the .ts
and .js files directly under ui/webview and vscode-extension/src, skipping test files, each name's definition (`function md(`
and the like), a line that opens with `//`, `*` or `/*`, and the text from a `//` that starts the line or follows whitespace;
each match is counted under the nearest `function NAME(` line at or above it, so a new call or reference moves a count and is
red: under its caller's name when that line declares the caller, and otherwise under the function that line declares, or under
none above the first such line.
A second road is named in the table and not counted, since its loads are the opened document's own and have no line in this
tree: a Cmd, Ctrl or middle click on a path link to an .svg opens the kernel's /file URL, or its /remote/<host>/file relay, in the
browser's own tab through preview.ts's openFileTab, a site counted on the local-kernel road by the URL it opens, and that tab is
an svg document that loads what its markup names; tests/test_security_price_feed.py holds the road's population to the property
that image/svg+xml is the one document type /file serves a file's bytes under, so a second document type there is red.
The clicked-link road holds the openers of a URL the content carries, on both hosts: the editor extension's one
`vscode.env.openExternal` and the browser bundles' `window.open`, each a JavaScript site keyed file plus tool that takes a row (the
road's rows name the chat page's click delegate, the shared opener the feed, the outline and the Waiting-on-you panes install, and
the file viewer's URL anchors; the file preview's own-tab open of the kernel's own file URL takes a local row, and the loads an
.svg opened that way makes are the second road named and not counted, above). Its residual: three
anchors the chat page's click delegate leaves to the default action (one with no scheme that the page built; one with no scheme in
a message that does not resolve to an http or https address; a message's own download anchor, one with no scheme carrying a
`download` attribute whose href resolves to an http or https address on this page's origin, which the browser saves from this
origin), and a page-built anchor with a scheme in a document that installs no opener (the gear's sign-in link on the dashboard's
settings page and in the editor's feed panel is one), are gestures this tree does not route: on the dashboard the browser's own
open or download, and what the editor's own webview host does with them is outside this tree.

What each side matches. The Python side reads every call by ast, resolved through import aliases, module constants and names
bound to a primitive (a socket, an asyncio event loop, a primitive itself), and gates every import: a module outside
KNOWN_IMPORTS fails the run (IMPORT), and so does a module named in importlib.import_module or __import__ (a string literal, a
module constant, or a loop or comprehension variable over a module constant of strings; an argument the scan cannot resolve is
refused as a module named at run time). The shell side is a line scan: the tools in SH, and an interpreter arm that emits a
site keyed file plus tool for an interpreter head (python, python3, node, perl, sh, bash, path-prefixed or not) followed by -c
or -e, or by a bare `-` (the program on stdin, the heredoc shape); every such site is in the external-program class and takes
a row that says what the text does, and a head held in a shell variable ("$PY" -c) is not matched, since a bare -c or -e is a
flag of many tools; a shell text inside a Python string literal (the remote apply scripts, the port probe, the self-update
script) is outside the shell scan and travels as the argument of a rowed ssh or bash site, whose row's prose carries it. The
browser and editor side is a line scan too: the clients and the two URL openers in JS (`vscode.env.openExternal`,
`window.open`, each a site that takes a row); the child_process family qualified to
its binding (`child_process.<fn>(`, `require('child_process').<fn>(`, a name the file keeps the module under, or a bare name
the file binds from child_process by a brace list, in the binding shapes the connection family's clause below names; a bare
`exec(` with no such binding is not a site, since RegExp exec is spelled the same way), each program site classed by its argv as
the Python side classes its own; the
connection family the same way: a `get` or `request` of `http` or `https`, a `connect` or `createConnection` of `net` and a
`connect` of `tls` through an inline require, a name the file keeps the module under (a require or an `await import()` assigned
whole in the first declarator of its declaration, TypeScript's `import X = require()`, a namespace or default import, alone or the two in one
statement, a default beside a brace list, `import { default as X }`), or a bare name the file binds from the module by a brace
list, alone or beside a default, in an import, a destructured require or a destructured `await import()` (renamed or not), and
`ws` by its constructor shape (`new <binding>(`, `new <namespace>.WebSocket(`, `new (require('ws'))(`), each an added arm beside
the literal spellings (`http.get(`, `net.connect(`, the bare global `new WebSocket(`), a call the literal list already names on
a line counted once under the same tool; and an import gate over every package the scoped files import or require, read where its
line reader reads a specifier (a literal require() or import() spelled whole on one line, a side-effect import that begins its
line, and the first `from` string on a line that starts with import or export or that continues an import or export statement that
begins its own line, and, in a walked file, any line led by a closing brace; the sentences after the two refusals below state each
read, and over the walked files the webview leg's pin holds the reads equal to a TypeScript parse of the same files): a specifier
that does not start with `.`, `/` or `*` names a package (its first path segment, two for a scoped package, `node:` dropped), and
a package outside KNOWN_JS_IMPORTS fails the run (IMPORT). The shell and browser sides are matched by a named list with no
completeness gate: a tool or a client the lists do not name is no site and no line; the Python side's gate is module-granular: an
import outside the allow-list fails the run, and a primitive of a known module outside NET and SUB is not a site. Two refusals
cover what the JavaScript binding patterns and the import gate do not read, each an IMPORT line unless the JavaScript allowlist,
JS_ALLOW, names the place by its file and expression, with the number of places the entry covers and the reason; an entry that
names nothing in the run, or covers a different number of places, fails the run too. First, a literal specifier of a family module
(`http`, `https`, `net`, `tls`, `ws` or `child_process`) that the import gate reads is read only where a binding the patterns
read takes the module from it, whole or by names, or an arm reads a call through it (`require('http').request(`); a require or
an `await import()` taken whole does not count when `.`, `?`, `[` or `(` follows it past whitespace and comments, and a brace
list that takes `default` does not count unless the same statement binds that name whole (`import { default as X }`), so a
require in a later declarator, `require("http").get` read as a value, a destructured default, a require assigned after its
declaration, a `.then()` callback of `import()` and a re-export are each refused; and in a walked file a binding the patterns
match whose specifier stands on a line led by `//`, `/*` or `*`, where the gate reads no module, is refused as a binding on a line
led by `//`, `/*` or `*`, whose module the gate does not read; the webview leg's pin sees such a binding when the line is code (a
`*`-led continuation of an import) and none on a comment line or in a template literal's text.
Second, on a walked line the scan reads (not in served text), a require or import the gate cannot read is refused: a call of
`require` in any other shape (whitespace or a comment before the paren, a template or a computed specifier), `require` as a bare
value (followed by `;`, `,`, `)`, `}`, `]` or the end of the line, outside a string and a comment, where a quote opens a string to
the same quote's next occurrence on the line that no backslash escapes, `/*` outside a string opens a comment to the next `*/` on
the line or the line's end, and `//` outside a string opens a comment to the line's end), any `.require(` call, any member access
on `require`, a `createRequire(` call, and an `import(` with a template specifier or with whitespace or a comment before its
paren. So every literal specifier of a family module that the gate reads is read or refused, and on a walked line every require
the gate cannot read is refused when it is spelled in one of those shapes; one spelled another way (a computed member such as
`module["require"]`, `require` beside an operator, a createRequire under another name) is no site and no line. A client is
read through a call on the module or on a binding the patterns read: a dotted call on an inline require or on a name the file
keeps the module under, or a call of a bare name the file binds from it, each read only as spelled on one line with nothing
between the require or the name, the dot, the method and the paren (`http.get(`), or between the bare name and the paren (`get(`),
and `ws` by its constructor shape, read with whitespace before its paren too (`new WS (u)`, `new W.WebSocket (u)`). A client
reached from such a binding any other way is no site and no line, among them a member alias (`const g =
http.get`), a destructure from the binding (`const { get } = http`), a computed member, `.call`, an optional chain, a call
spelled with whitespace or a comment around the dot or before the paren (`http . get(`, `http.get (`, `get (`) and a call split
across lines before its paren (`http` at the end of one line and `.get(` at the start of the next); an inline require called
either of the last two ways is refused by the first refusal. The import gate reads a specifier in a literal require() or import()
spelled whole on one line (the name, its paren, the quoted specifier and the closing paren, with nothing between them but
whitespace inside the parens), wherever it stands, in a side-effect import that begins its line (`import`, whitespace alone, then
the quoted specifier), and in the first `from` string (`from`, whitespace alone, then a quoted specifier) on a line that starts
with import or export or that continues an import or export statement that begins its own line and has not yet ended, and, in a
walked file, any line led by a closing brace. In a walked file such a statement opens at `import` (not `import(` or
`import.meta`), `export {`, `export *`, `export type {` or
`export type *` and ends at the line where the gate reads its `from` string or at a line that ends with `;` outside a string and a
comment; any line of it is read whatever leads it but a line led by `//`, `/*` or `*`, which is skipped, a binding on one refused
by the first refusal. Over the walked files the webview leg's pin (ui/webview/import-gate-parse.test.ts) holds these reads equal
to a
TypeScript parse of the same files (the specifier of each import and export declaration, of `import X = require()`, of a require
or import() call on a quoted literal and of an import type), both ways, keyed on file, line and specifier, and holds each require
or import() call whose first argument is not a quoted literal to a line where the second refusal fires (an import() on a computed
argument that is not a template, to a browser-computed-url site), so a specifier in a layout the line reader does not read is red
there by file, line and specifier. Served text is not parsed, and the pin does not hold it: there such a statement opens at any
line that starts with import or export (not `import(` or `import.meta`), a line continues it only when led by `from` or a closing
brace, and no line is skipped as a comment. Through a binding whose specifier the gate reads, `https`, `net` and `tls` still fail
the run at the gate, so this residual reaches `http`, `ws` and `child_process`, the packages the list knows; in served text,
through a binding the patterns read from a specifier the gate does not read, among them one on the line after a trailing `from`,
one on a continuation line led by anything but `from` or a closing brace, one in a require() or `await import()` split across
lines and one in a statement that does not begin its line, it reaches `https`, `net` and `tls` as well. A comment between `from`
(or a side-effect `import`) and its specifier is read by neither the gate nor the binding patterns, so in served text a client
through it is no site and no line whatever the module, `https`, `net` and `tls` included, and a package outside KNOWN_JS_IMPORTS
passes the gate.
The first refusal also refuses a line that binds nothing to call, such as `import type http from
"http"` or `let a: typeof import("http")`; no such line is live. An echo- or print-led shell line
is skipped as a printed remedy only when nothing live follows the printed text: the text outside quotes and the body of every
`$(...)` and backtick substitution, wherever it stands, are scanned by the interpreter arm and the tool list, so `echo "$body" |
curl ...` and `echo "rate: $(curl ...)"` are sites and a remedy that names a tool inside quotes is not.
The pages the kernel serves and its service worker's script, from its own string constants (the dashboard shell, the seven pane
pages, the token login page, the too-large page and /sw.js, with the shim, the timeline boot and the shell scripts they inline),
are read from kernel.py's syntax tree and scanned as browser text keyed kernel/kernel.py plus tool, with the DOM loads counted.
The routes are derived from the calls of `_send` the scan reads (spelled `_send(...)` or `<x>._send(...)`; a call through a name
computed at run time is not read) and every Content-Type header written outside `_send`, in every scanned Python file. A `_send`
call's content type is read through the definition it reaches, the one def or async def statement that binds `_send` in its
file, direct in the call's own class body (a call through self: a call on a name that is self by binding, the first positional
parameter of the method the call stands in, however it is spelled, never the spelling self) or in the module (a bare call): the
kernel's Handler._send
writes its `ctype` parameter, so the call's third argument or its `ctype=` keyword; the postal bus's writes application/json;
the session host's and its transport's write a frame to a Unix socket and answer no HTTP request (FRAME_WRITERS), and any other
definition that writes no Content-Type fails the run. So does each `_send` call in a file that binds `_send` more than once
outside function bodies (the module and every class body counted together, a class body a function body defines included, since a
class body is no function body, in any binding form but a comprehension's target, which binds only in its comprehension) or other
than by one def statement direct in a class body or the module, or where a function or a class body binds it under a `global`
declaration, rebinding the module's name at run time, each bare call that reaches a `_send` bound inside a function, a lambda, a
comprehension or a class body around it, in any form (a
parameter, a nested def, a loop target, a lambda's parameter and a comprehension's target among them; the line names the scope and
the binding), each call that reaches no definition the census reads, the line saying why (a `_send` the call's own class body does
not bind, for a call through self: inherited or set at run time; a call on a name in a class body that is not self by binding, the
line naming the condition it fails (the call outside the body of a method defined directly in that class body, or in that method's
header, which runs in the class body; the name not the method's first positional parameter; a lambda or a comprehension around the
call binding the name; the method binding the name again in any form, or a scope nested in it rebinding it under a nonlocal
declaration; a decorator on the method other than a name, or a call of a name, that the module binds once by a def statement; the
class body binding the method's name other than by that one def statement, or declaring it global or nonlocal; the file storing,
deleting or naming to a setter an attribute of the method's name on any object); one reached in a class body through a receiver that
is no name (an object other than self), or through an attribute outside any class body; a
`_send` no scope the bare call looks it up in binds, the module included; and, in a file that names `_send` nowhere but as the
called name of those calls, so binds it nowhere at all, a definition the file does not hold), each call to a definition carrying
any decorator, whose parameters the census does not read,
and each bare call in a module that holds a star import. An override of `_send` in a subclass that another file defines is not
read: a call through self is typed through its own class body's definition (where that file binds the page's module by an import
statement, the page's file fails the run, below). Nor is what a decorator the census accepts on the method (a
name, or a call of a name, that the module binds once by a def statement) does with self, since that def may hand the method another
object in the instance's place (its witness: a method whose decorator, a def of the file, calls it with an object whose `_send`
serves the page as text/html), or a method replaced on its class at run time through a name no code spells, a setter whose name
argument does not fold among them (its witness: a method a setattr replaces, its name the return of a call). The type is read
through a module name no code writes after binding it (one plain single-name assignment binds it as a top-level statement, nothing
else at module level binds it, a walrus in a def's or a class's header included, the module holds no star import, and nothing in
the file writes that name,
in any scope: a subscript store or delete, a call `<name>.<method>(` of a method _MUTATORS or _DUNDER_MUTATORS lists, a call of
such a method on a type _CONTAINER_TYPES lists with the name as its first argument (`dict.update(<name>, ...)`), a binding in a
function that declares the name `global` (as the target of an assignment, an augmented assignment, a loop, a comprehension, a
with or a walrus, or by an import, a def or class statement or an except clause) or a module-level augmented assignment),
through a local whose every binding is read (a walrus in a nested def's, class's or lambda's header is a binding it does not
read) and through a dict literal's values (refused before its type is read, below: a call inside a lambda's body, a Content-Type
write inside one that is no `_send` definition's own write, and a call whose definition binds the parameter one of its own writes
names other than as that parameter); the part before any `;`, stripped and lower-cased, is compared with the types a
browser runs script from (SCRIPT_TYPES: text/html; the XML types text/xml, application/xml, text/xsl and any type with a `+xml`
suffix, image/svg+xml and application/xhtml+xml among them; and text/javascript under each name a browser takes for JavaScript,
application/javascript among them). A script-running route's page body is the call's second positional argument, read only when
the call passes it positionally, with no starred argument before it and no `**`, and the definition's one output is its one
`self.wfile.write(<its second positional parameter>)`, with nothing in its signature or body outside the node kinds, in their
roles, of the kernel's Handler._send: that write, the definition's last statement, directly after its one `self.end_headers()`,
and before them send_response with its one argument and send_header, called on self as statements; isinstance, str, len, and
getattr of self with a string-constant name and a None default, where neither the definition nor the module binds the name,
nothing rebinds it (no function binds it under a `global` declaration, no module-level statement writes it, and the file does none
of the writes listed below that rebind every builtin) and the module holds no star import; the one rebinding of the page parameter
to itself or to itself encoded by `.encode("utf-8")`, alone or as the branches of an `isinstance(<page>, str)` test (`body =
body.encode("utf-8") if isinstance(body, str) else body`); a loop over a parameter's items (`for k, v in (headers or
{}).items():`) and an if on a parameter or on that getattr, each into header calls; header values built from string constants
holding no CR or LF, parameters, the loop's targets, attributes read on self, str, len and a `%` format on a string constant; and
a signature of positional parameters, none positional-only, with None defaults and no annotation. Any other script-running call
fails the run by name,
its reason naming the road (a second write, a write through an alias, a print to a stream and, for any other statement or
expression, its node kind and line among the reasons), among them a keyword body, a starred or `**` call, a definition whose one
write is of another parameter, a local or an expression, or that writes nothing, a method's definition that binds self again, in
any form (a lambda's or a nested def's parameter among them), or declares it global, any other read of an attribute named `write`,
`writelines`, `send`, `sendall`, `sendfile` or `sendmsg`, called or not, a string constant equal to one of those names, a
reference to the write's receiver other than as its receiver, and in the definition a statement after the end_headers (which
writes the header buffer to the stream, so a header call after it would reach the body), a second end_headers or none, any other
rebinding of the page parameter, another codec name or a second argument to `.encode` (either can name a codec or an error handler
the file registers at run time), a store or delete of an attribute or a subscript, a read of a name the module binds, a call not
listed above, and a nested def, class or lambda. The reader governs the definition's own text, and code the definition runs from
outside that text is not read: a header value is not scanned, and a response that a Content-Type in its headers argument, passed
or defaulted, makes a page is outside the served pass, the call being typed by its content-type argument; nor is code the
definition runs through an object it is handed (a parameter's methods, its mapping's items, its __str__), code behind a name the
definition calls or reads on self (a header method, a property or `__getattr__`, however the class, a base or other code defines
or replaces it) and any stream that code writes, or a `_send` replaced at run time through a name no code spells (setattr or a
class `__dict__` with a computed name, a metaclass namespace key, a base's `__init_subclass__`). The census does not see a module
namespace rewritten at run time by code outside the forms listed below that rebind every name: a listed name reached any other way
or a name the list does not hold (through `__self__` of a builtin, a container or a copy of a namespace mapping other than the
file's own module's or the builtins' (one of those used other than in a key position the census reads is a run-time form, below), a
module's own
`__setattr__` or `__delattr__` method, a listed name, attrgetter or methodcaller imported from a module other than its own, a name
built at run time, gc or ctypes among them, and through a module reached by a tuple or list unpacking, an inline walrus,
`sys.modules.__getitem__`, a for-loop target, a parameter default or a starred argument)
is outside the list and not seen, and a module name or a builtin so rewritten is read as the file's text binds it; nor does it see
a scalar local or parameter a function rebinds at run time through its own frame (the frame's locals, which Python 3.13 and later
write through to the function, reached by `sys._getframe()`, `inspect.currentframe()` or `inspect.getargvalues()` among other
calls): a page's text, and a content type that is a string constant or a name bound once to one, so rebound the census reads as
the function's text binds it, a stated limit on Python 3.13 and later (its witnesses: a handler that binds its content type to
`application/json` and one that binds its page to `<p>ok</p>`, each rebinding that local through its frame, so that those versions
serve a fetch as a page). A container a function binds and reads whole, changed through that same frame's local mapping, reached
or run as code in the function's own body (one of the seven bare names `locals`, `vars`, `exec`, `eval`, `_getframe`,
`currentframe`, `getargvalues`, one of the four attributes `_getframe`, `currentframe`, `getargvalues` or `f_locals` spelled as an
attribute on any receiver, or a name that a statement of the module's or the function's own body, outside every def, class or
lambda statement it
nests (header and body alike), binds to one of those primitives, its bound value the primitive's own bare name or attribute, by a
plain or annotated assignment, a walrus, an unpacking of a list or tuple literal into a target list of as many elements (each
plain name there bound to the value at its place, beside a starred or nested target too), or a `from ...
import` of one of the seven names, and any name such a statement binds to a name so bound, resolved among those statements), is
refused by name
on every version, since the change reaches the real object; the check reads the spelling anywhere
in the function, called or not, so a name merely spelled like a primitive is refused too, its reason naming the spelling found,
not a frame reached; a change to those locals at run time through a frame object, exec or eval reached in any other spelling
(among them: the name `locals` or `vars` as an attribute on a receiver; exec or eval reached as an attribute; `f_locals` as a bare
name; one of the four attributes named by a string, as `getattr(frame, "f_locals")`; and any binding of a name to a primitive that
the resolution above does not read, a plain name among the targets of an unpacking whose targets are not as many as its values, a
name a nested unpacking target binds, an alias whose bound value is any other expression (an if-expression, a call), and a binding
in the header or the body of a def, class or lambda statement) is the stated precondition,
outside what the census reads, and passes silently (its witnesses, one for each road named: `locals`
reached as an attribute on a receiver; `builtins.exec`; `builtins.eval`; `f_locals` called as a bare name; `getattr` handed a
frame from `inspect.stack()` and the string `f_locals`; a plain name beside a starred target that takes two values, and a name in
a nested target; a module alias bound to an if-expression and one bound to a call's return; a walrus in a module-level def's
default, a `from ... import` in a def nested in the function, an assignment inside a module-level def's body, an assignment in a
module-level class's body, read as the class's attribute, and a walrus in a module-level lambda's default), while a name a
nested
scope binds to
a primitive by an assignment carries the spelling in the function's subtree and refuses; code the function runs that the census does
not read (a helper it calls as a
statement, a method on self, a context manager it enters), reaching the caller's frame to change such a container, is a stated limit instead,
the census reading no such code's body for its frame reach as the call limit reads none for what a callee does with a container it
is handed; a content type the census reads other than as a string constant or a name bound once to one is refused by name too, on
every version, so no frame can rewrite an intermediate the census had read. Beside that precondition stands the item limit, for
the local container proof below: what code does with an item of a container the proof reads, or with the object that a name bound
other than to a literal or a call of parse_qs holds, after the census has read it, in a spelling the proof does not refuse, is
outside what the census reads and passes silently, one witness for each road: a name an unpacking binds from a tuple or list
display that holds the item, which takes that display's level, so a change through it is read as a change of a new object holding
the item (its witnesses: a list read out of a local dict of lists, bound so and appended to, and bound so and extended by an
augmented assignment; and a queue bound through a boolean operation, bound so, its put read off that name unbound and called); a
subscript of a new object holding the item as an augmented assignment's target, read as a store into that object (its witness:
that list held in a new list and extended through a subscript of it); a match statement's capture of the item, or of the name
itself, for a name bound other than to a literal, a call of parse_qs or calls alone (its witnesses: a dict of lists bound through
a boolean operation, a list of it captured by a mapping pattern and appended to, and the dict captured whole and stored into); an
item of such a name stored into another object and changed there (its witness: a list of that dict stored as another object's
attribute and appended to there), and an item of a name bound only to calls held in a new object that is stored into another
object, called or matched (its witness: a list read out of a dict bound to a call of dict, held in a new list stored into another
object through which a fetch is stored into it); on a name bound other than only by plain assignments of calls (an expression, a
loop, with or unpacking target, or a second binding), a method outside the in-place changers with its return used, the name stored
into another object, or an item of it handed to another object's method by an operator (its witnesses: a queue bound through a
boolean operation that a fetch is put into, the put's return used; a dict of lists so bound, stored into another object through
which a fetch is stored into it; and one whose item is compared with an object whose `__eq__` appends a fetch to it); a name bound
to anything but a literal or a call of parse_qs, handed itself, or in a new object holding it, to another object's method by an
operator (its witnesses: an import's object compared with an object whose `__eq__` stores a fetch on it, read through str; and a
dict bound to a call of dict, held in a new list compared with an object whose `__eq__` stores a fetch into it through that list);
a change a function makes to its own parameter by a use outside those the proof lists, what a function does with a value it is
handed, the call limit (its witness: a queue a module function takes as its parameter and puts a fetch into, the put's return
used); and on the module side, a list of a module container bound to a name by an unpacking nested in another, or by a loop's or a
comprehension's unpacking (a generator expression's among them), in a function or at module level, which the module side reads at
a depth that does not reach the container, or held in a new list in either place and extended through a subscript of it by an
augmented assignment (its witnesses: a list of a module dict of lists so bound in a function by a nested unpacking and appended
to, so bound there by a loop's unpacking and appended to, and so held there and extended; the same three at module level; and the
list so bound by a list comprehension's unpacking and appended to in its element, in a function and at module level, and by a
generator expression's unpacking at module level). A default of a function or a lambda that holds the name, or a name the proof
follows from it (a name that a plain or annotated assignment, a walrus, or a loop's, a comprehension's or a with statement's
target, an unpacking's names among them, binds to it, to an item of it or to a new object holding one, outside every def or class
statement and lambda body the function nests), marks the name at any level of new objects (unless the str exemption the local
container's definition below states holds), so that road refuses; a default holds it where the default's value is that name, or
reaches it only through subscript loads on it, the returns of the read methods get, keys, values, items and copy (and of index or
count with a constant argument), boolean operations, if-expressions' branches, walruses' values, starred values, awaits and new
objects (a list, tuple, set or dict display, a comprehension holding it as its element, or a binary operation whose other operand
is a constant). A def's default is part of the def statement, so the name read there is an occurrence in a def nested in the
function, which refuses a container whatever the use, and the proof follows no name bound there (a walrus's or a comprehension's
target), so a change through such a name is the item limit (its witness: a dict of lists bound through a boolean operation, a list
of it bound by a walrus inside a call in a nested def's default and appended to through the walrus's name after the def); a
lambda's default runs where the lambda stands, in the function's own scope. Otherwise any other use of the name or of
an item of it in a default is read as that use is in the function's own body: handed to a call as an argument, it is
under the call limit, what the call does with it and what it returns not read (its witnesses: a dict of lists bound through a
boolean operation, a list of it bound to a name and handed to a module function that returns it, its return taken as the default
of a nested def that appends a fetch to it; the list handed so directly, in a nested def's default and in a lambda's; and the same
in a
lambda's default where the dict is a local literal); and handed to another object's method by an operator, it is read as that
operand is elsewhere, refused where the proof refuses such an operand and otherwise one of the item limit's operand roads above
(its witness: that list, through a name bound to it, added to an object whose `__radd__` appends a fetch to it, in a nested def's
default). A default that takes the item through a name the proof does not follow from it passes silently, part of the item limit
(its witnesses: a dict of lists bound through a boolean operation, a list of it captured by a match statement's mapping
pattern and taken as the default of a nested def, and of a lambda, that appends a fetch to it; a list of that dict stored as
another object's attribute and taken from that attribute as a nested def's default that appends a fetch to it; and a list of that
dict bound by a comprehension's target in a nested def's default, the comprehension's list that default, through which the nested
def appends a fetch to it). A `_send`
definition in a class that a function defines, a page function that a function encloses, a `_send` call inside a lambda's body, and
a Content-Type write inside one that is no `_send` definition's own write fail the run by name: the census does not read the
enclosing function's or lambda's scope, so it would take a name that scope binds (a builtin or a module name it shadows) for the
module's. A `_send` definition's own Content-Type writes (each write whose innermost def is the definition, or a def in it itself
named `_send`) are typed at each call. A call fails the run by name where one of them names a parameter whose argument the census
reads as the type and the definition binds that name other than as that parameter anywhere in its body (in its own scope or in a
lambda, a comprehension, a nested def or a class body in it) and in any form (an assignment, augmented or annotated, or an
annotation; a loop, with, walrus or match target; an except name; a del; an import; a def or class statement; a global or nonlocal
declaration; a parameter, a comprehension's target, a type statement or a type parameter): the census reads that write's type from
the call's argument, which such a binding may replace.
The page function of each script-running route
is followed to the text it returns or inlines, and a
parameter a followed call omits is read from its default value as that argument would be, in the scope the def statement runs in
(a default the pass cannot read is refused by name, one that holds a lambda among them). A name
the page function's scope binds, or for a function defined in it an enclosing function's scope, is decided by that scope and never
by the module's binding: a local container the census does not prove it reads whole (below) is refused wherever it is read, and any
other local (a parameter the body also assigns, a walrus in a nested def's, class's or lambda's header, and a comprehension's
target inside its comprehension among them, read from its generator's source in the scope Python evaluates that source in: the
first generator's in the scope around the comprehension, each later one's with the earlier generators' targets bound, a target of
that generator or of a later one being refused there as a name a comprehension binds) is read from its values as a bare name or a
receiver (refused where one holds a lambda, below), each value in the scope that binds the local, where Python evaluates it (a
comprehension, a lambda or a function defined in the page function reads a local of the scope around it there, so its own binding
of a name that value reads is never taken for it) and refused as a callee; a parameter or an except name is a value slot, refused
as a callee when it shares a
module function's name; a function defined in the page function is followed as a callee only as its name's one binding there and
where the census proves it a plain def (below), and is refused by name as a value, a function object whose text the census does not
read; a name the function declares `global`
is the module's binding, read as such; and any other binding refuses, a comprehension's target elsewhere in the function, a
function-level import, a nested class, a del, a name a nonlocal declaration rebinds and a name bound two ways (two different
binding forms in one scope, or a def or a class statement beside any other binding of it; every value form, an assignment,
augmented or annotated, a loop, with or unpacking target and a walrus, is one form, and a parameter the body also binds by one is
one local, read from its values) among them. In that text the served pass reads a
BoolOp's operands, a method call's receiver and a subscript's container when they name a module constant (a name one plain
single-name assignment binds as a top-level statement and nothing else binds at module level, in a module with no star import that
writes no name of its module namespace through a computed name and may not rewrite it at run time, as listed below) or a local, a
method call's receiver only for a method whose return is drawn from the receiver's text (strip, lstrip, rstrip, removeprefix,
removesuffix, split, rsplit, splitlines, partition, rpartition, a match's group, and the read methods get, keys, values, items,
index, count and copy), any other method on a receiver whose text the pass reads refused by name, the receiver of `.encode` or
`.format_map` whatever it is (but the name str, bytes or bytearray before `.format_map`, and either one in a shape the census does
not compute, each refused below), a loop, unpacking or with target from its source, and a local container's stored or appended
values where every occurrence of its name is one of the proven forms (below); it passes over a base whose own text
it does not read (in a module
that holds no star import, a top-level import statement that is its name's one module-level binding and is not rebound, or one of
the seven builtins a page may name, each for what its result is (str, its argument's text or a value's printed form, a call of it
with more than one positional argument, a starred argument or a keyword other than `object`, any of which may be an encoding or an
errors argument that decodes its first, refused by name, an honest decode of bytes failing closed with it; int and float, a
number, which carries no host, so a call of either that is the builtin is a leaf whose argument the pass does not read, save where
the call is the base of a receiver, a container or an attribute, where the argument is read as any call's is (the leaf rests on
the builtin's return, which the census does not read: an `__int__` or an `__index__` returning an int subclass, or a
`__float__` returning a float subclass, whose `__str__` or `__format__` is overridden is the escape shape that could put text
there, the stated limit, and the interpreters the census runs on copy such a return to an exact int or float, so its witness
serves digits), and a call of either bound any other way is refused by name;
dict, a mapping of its arguments' keys and values; max, one of its arguments (a call of it handed one iterable or a starred
argument, which returns an element its argument holds, whose join with the text beside the call the census does not compute, is
refused by name); getattr, an attribute of its first argument; and chr, the character a code point names: getattr and chr give
text their arguments do not hold, so each falls under the call limit below, as its witness) that
no module-level binding shadows and
that is not rebound, any other builtin refused by name, and a call of super() refused by name as well, its methods being a base
class's (the names the import system binds in every module, `__doc__`, `__name__`, `__package__`, `__spec__` and `__loader__`, are
no builtins here: a page that reads one the file does not bind is refused by name wherever the pass reads it, as a bare name, the
base of a receiver, a container or an attribute, a callee or a call's argument, but never inside the index of a subscript over a
container whose text the pass does not read: below); a parameter, an except name, or a name the function
binds from one of those, where no attribute is read on the path to it: `q.get(k)` passes, and `q.X` is refused, below), reading as
text the arguments a call of such a base or of a method on one is handed, never the text it computes from them (a method whose
return is not drawn from its receiver's text, called on such a base where it derives through a call handed arguments the pass
reads, `str(X).lower()`, `int(X).bit_length()` and `base64.b64decode(X).decode()` among them, or on the bare name of one of the
seven builtins, called unbound, `str.lower(X)`, is refused by name because the base's own text is not read, not because its return
is undrawn (a `.strip`, whose return is a piece of that unread text, is refused the same way): at the call the page expression
makes, save a `.replace`, `.join`, `.format`, `.format_map`, `.encode`, `.strip`, `.lstrip` or `.rstrip` there, which the
text-method arm reads as its own shape (below); and at every call on the path below it with no exception by shape, the text-method
arm's among them, under a method whose return is drawn from its receiver's text, a join or a subscript,
`str(X).lower().removeprefix(p)`, `str(X).lower().split()[0]` and `str(X).strip().removeprefix(p)` among them): text a call
computes from its arguments is not read,
a
stated limit (`dict(X).get(k)` and
`json.loads(json.dumps(X))[0]` read X; the limit's witnesses are `chr(n)`, whose character is not n's text, `getattr(o, name)`,
whose attribute is not its arguments' text, and a decoder, `base64.b64decode(X)` or zlib or gzip over an embedded bundle
(`zlib.decompress(base64.b64decode(X))`), whose bytes the page serves, each read only as its arguments' own text; an encoded asset
kept ASCII and
decoded where the page is built is such a shape, and can be honest; and so is a method called on a parameter whose name no route
class's body binds and
the file nowhere stores, deletes or names to a setter as an attribute (below), a method of a class that holds no route among them),
and over a bare module name that is such an import or one of the seven builtins a page may name; a top-level def or class statement
that is its name's one module-level binding, read as a value rather than called (a bare name or a call's argument among them), is
refused by name as a function or class object, whose text (a class's through its metaclass, a function's through its writable
`__qualname__`) the census does not read. Text such a base holds is not read: a constant that
a sibling module defines and the page
imports, and a class reached through an import's attribute (its witness: a class that a sibling module defines, read as an attribute
of that module, which the page imports by name) or through a call's return, under the call limit; code behind a name on self is
not followed: a method called on self by binding, or on a name the census resolves to it (a local bound to it, or a function the
page function defines returning it), is refused by name (below), and one called on any other parameter, or on a name bound to the
return of a function the census follows that returns its parameter, is refused where a route class's body binds its name or the
file stores it, and is otherwise under the call limit; an item of self, a parameter's, is text such a base holds. A local
container (a name a function the pass reads binds whole to a list, dict or set literal or comprehension or to a call of parse_qs,
or a name with one of these uses: a store or delete through it or an item of it; an append or extend; setattr or delattr, or a
method spelled on a class, handed it or an item of it; a binding of it, or of a new object holding it, to a name the function
declares global or nonlocal, or as a default of a function or a lambda (unless the name is no parameter and every binding of it is
a plain assignment of one name to a value the proof types as a str: a string constant; a walrus of one; a boolean operation or an
if-expression whose operands or branches all are; or an item read, by a subscript load without a slice or by a dict's get (its
default, where it has one, of the items' type too), out of a container every item of which is one, such a container being a list,
tuple or dict literal (with no starred element or `**` entry, a dict's items its values), a slice of a list or a tuple one, a copy
of a list or a dict one, an item so read out of a container every item of which is such a container of one kind, or a walrus, a
boolean operation or an if-expression over such containers of one kind; an item read out of a container that holds none, which
Python cannot read, has no type and is left out wherever types are met); an augmented assignment to a name
bound to
it or to an item of it, which runs that value's own in-place method (`e += [v]` extends a list, `e |= {...}` updates a dict); one
of the in-place changers of a list, dict, set, deque or OrderedDict called on it or read off it unbound (update, setdefault,
append,
extend, insert, pop, popitem, popleft, clear, add, discard, remove, sort, reverse, appendleft, extendleft, rotate, move_to_end,
difference_update, intersection_update and symmetric_difference_update, or a spelled-out `__init__`, `__setitem__`, `__delitem__`,
`__setattr__`, `__delattr__`, `__ior__`, `__iadd__`, `__isub__`, `__iand__`, `__ixor__` or `__imul__`), or a method whose return a
statement drops; an attribute read off it other than as a method's callee, whatever the name is bound to; or a method other than
get, keys, values, items, index, count or copy called on an item of it, or an attribute read off one; and, for a name that is no
parameter and every binding of which is a plain assignment of one name to a call (an
import's, a builtin's or a followed function's), any use outside a closed set: a read, a call's argument, a subscript load, a
binding to a name the walk follows, the name itself an operand, and a method the census reads a text through with its return used
(get, keys, values, items, index, count, copy, split, rsplit, splitlines, partition, rpartition, removeprefix, removesuffix,
group, join, format, format_map, replace, strip, lstrip, rstrip or encode), so any other method, it or a new object holding it
stored into another object, called, matched or held where the census does not read it, and an item of it so used or handed to
another object's method by an operator; each directly or through a name bound to it, to an item of it or to a new object holding
one, at the levels of new objects that name's binding holds it at) is read whole only where every occurrence of its name, resolved
by binding, is one of the proven forms:
its one binding (a plain single-name assignment to a list, dict, set or tuple literal or to a call whose return the census reads
as a value slot, an import's, one of the seven builtins a page may name, a parameter's or a method's on one of those); the base of
a subscript store by a str or int constant key as the one target of a plain assignment, whose stored value the census reads; the
receiver of an append or extend of one plain argument the census reads; and the fourth form, a read that hands the container to no
other code: the receiver of one of the read methods of the type its one binding gives it, or the base of a subscript load on a
type that has one, wherever it stands, tests included. The read methods are a closed set per type: a dict's get, keys, values,
items and copy and a subscript load; a list's index, count and copy and a subscript load; a tuple's index and count and a
subscript load; a set's copy; an index or a count only with a constant argument (with any other, Python hands each item to that
argument's method, and the container refuses). Only a list, dict, set or tuple literal, or a call of parse_qs (imported from
urllib.parse at the top level and bound once, a dict), gives the container a type; bound to any other call the census reads as a
value slot (`dict(...)` or an import's call among them), it has no type, and a read method or a subscript load on it refuses. A
read method's or a subscript load's result is an item the census follows by binding like any other value. The proof covers the
container, and an item of it (a read method's or a subscript load's result) it reads by the same principle where no new object
stands around the item: the item itself, a name bound to it (a binding whose value is the item with no display, operator or
comprehension around it, or a loop's or a comprehension's target over such a display), and a subscript load or a read method taken
from a new object holding it, through the closed read set of the item's own type, known as the container's
is: from the literal, from parse_qs (whose items are lists of str) and from each value stored or appended into the container, a
string constant being a str, and a copy of a dict, a list or a set, or a slice of a list or a tuple, being of its receiver's type
and a new object holding its receiver's items. Any other method called on the item, and a read method or a subscript load outside
its type's set (a
spelled-out dunder among them), whether the return is used or dropped, an attribute read off it other than as a method's callee, a
store into it, an augmented assignment to a name bound to it (which runs the item's own in-place method, and refuses for a str
item too, whose augmented assignment only rebinds the name), setattr or delattr handed it, and a method spelled on a class handed
it as its first argument (a builtin class, as in `list.append`, or a class of collections imported as the module or by name, as in
`deque.append`), each where no new object stands around the item, refuses the container; a str has no read set, nor has an item
whose type the census does not know (a call's return, a
name it does not follow), so any method or subscript load on one refuses; and so does the item's hand-off to another object's
method by an operator (an operand of a binary operation or a comparison whose other operand is no constant, a subscript's index, a
slice's bound, the value of an augmented assignment, or what an index or a count with an argument that is no constant compares) or
any use of it the census does not read (called, or stored into another object, an attribute or a name the function declares global
or nonlocal); compared or combined with a constant, an item is read, since only its own type's method and the constant's run; and
an item handed as an argument to any other call, a method spelled on any other value among them (a class the file defines or
another import names, a module's function), is under the call limit, as the container is (below). Any other occurrence refuses
the container by the rule, its reason naming the role it fails: the whole container bound to another name, to a name the function
declares global or nonlocal, or into an attribute or
another object; a read that hands it to another object's method (an operand of a binary operator, a comparison or `in`, a
subscript's index, a slice's bound, the value of an augmented assignment) or any other read (a test, an identity test, a boolean
operation's operand, held in a new object); a second binding (an augmented assignment, a walrus, or a for, with, except, match or
unpacking
target); a delete; a method other than append, extend or a read method of its type, a read method outside its type's set or a
spelled-out dunder among them, or an attribute of it read other than as a method's callee; setattr or delattr, or a method spelled
on a class (a builtin class, or a class of collections imported as the module or by name), handed it as its first argument; a
store by a key that is no constant; an append or extend of other than one plain argument; an augmented assignment to a name bound
to it or to an item of it; or any occurrence in a function or lambda nested in it (a def's header, its defaults among them,
included; a lambda's defaults, which run where it stands, excepted), or a class body it defines, whose code the census does not
read (a closure capture) or which makes a class attribute; a comprehension is read
where it stands, as the function's own body is: a read of the fourth form and an append of a read value there pass, the container
as a comprehension's source, in its condition or as its element refuses as any other read does, and a change the census cannot
fold, a comprehension target store among them, refuses. The first parameter of a method or a route
handler is not read so: every attribute read and method call on it is refused already. The container, or an item of it, handed as
an argument to any other call is under the call limit, what the callee does with it not read (its witnesses: a local dict a module
function it is handed stores a fetch into; a list read out of a local dict of lists by a subscript load, by `.get`, or through a
name bound to it, which a module function it is handed appends a fetch to; and such a list handed to append spelled on a class of
the file that derives from list). What the proof does not read of a name so marked, or of an item of a container it reads, is the
item limit, stated above beside the frame precondition. An
attribute
read in a page position, as a value or
anywhere on the path of a receiver or a container (but never inside the index of a subscript over a
container whose text the pass does not read: below), is refused by name unless the root its base reaches by
binding is a module constant, an import, one of the seven builtins a page may name, a value slot or a literal the pass reads (an
attribute read off a local, or off a module name bound to a call, being refused before that, as a container or a run-time memo, so
the walk below reaches a local's values only through a comprehension's target, or from a receiver with no attribute read on its
path; the census follows the base down that path, through a call's callee, a BoolOp's operands, an
if-expression's branches and a walrus's
value as well, and through a local's values, a loop, comprehension or with target's source, a list, tuple, set or dict literal's
elements, keys and values, and a module constant's value, but never through a call's argument or a parameter's default): an
attribute read on self
(`self.X` as a value, a receiver or a container, `self.X.get(k)`, `self.X[0]` and `self.__doc__` among them), on a comprehension's
target bound to it or on a method's first parameter however spelled, where the method's def carries no decorator and, for a route
handler, the
file binds neither staticmethod nor classmethod, is refused by name, whatever sets it; one read on any other parameter (a module
helper's parameter, any other method's first parameter, and a parameter that a class is passed to or has as its default among
them) is refused by name as that parameter, a container the proof refuses, and one read on a route handler's first parameter the
census does not classify, on a parameter's call or on an except name with a reason of its own; a base whose root is
one the pass refuses (a
function's or a method's return, a call it does not follow, a builtin other than the seven, a function object, `__file__` in a file
that binds it, a run-time memo) is refused with the reason the pass gives that root; and an attribute read on a class, a method
called on one among
them, is refused by name too, as a value, a receiver or a container, through the class's own name (a name a class statement binds,
in the innermost
function scope around the read that binds the name or, where none does, at the top level of the file, whatever else binds it at
module level) or through a name the census resolves to such a class (a local or a module constant bound to one, `h = Handler` and
then `h.render()`, the attribute read `h.X` refusing that local as a container first), or through a method call on, or a subscript
of, a name whose
value holds such a class (a local or a module constant bound to a list, tuple, set or dict literal with one among its elements, keys
or values, `_REG.get(k).X`, or to a call of the builtin dict with one among its arguments, a keyword's value among them, `_REG =
dict(a=Handler)` and then `_REG["a"].X`, or a local or a module constant bound to such a method call or subscript), or of such a
literal or call itself (`dict(a=Handler).get(k).X`), or through any other base whose root by binding is such a class (a loop,
comprehension or with target over classes, an if-expression or a walrus over classes, and a literal container holding one,
`_REG["a"].X` and `_REG["a"].render()` among them), and so is a text method called on such a class through any of those roads
(`Handler.format(...)`, `_REG.get(k).format(...)`, `(A or B).replace(...)`, `t.strip()` in a loop over classes), save one on a
subscript refused as a join's operand (below), and a replacement field in a `.format` or `.format_map`
that reaches an attribute of its argument (below):
no class attribute is read as page text. A call of a name the census resolves to such a class, the class's own name among them, is
refused by name as a call, so no attribute of the instance it makes is read either. A
name
is rebound when a function binds it under `global` or a statement at
module level writes it, in one of the forms listed above for a route's type; every name is rebound, as under a star import, in a
file that writes its module namespace through a computed name (globals() or vars() used any way but for a `.get` read, the
`__dict__` or vars() of a module the file may be, or a store, setattr or delattr on that module; globals, vars, setattr and
delattr each reached in the first three of the four ways below, and any of those four read other than as a call; a module the file
may be is `sys.modules[k]` or `sys.modules.get(k)`, on any name or attribute spelled `modules`, or a call of `__import__` or
import_module reached in those three ways with the first argument k, where k is no string constant, `__name__` among them, or is
"__main__" or a dotted name whose last part is the file's own module name; a name that an assignment (as a name target, alone or
in a chain), an annotated assignment or a walrus binds to one of these, read by that name; or an if-expression or a boolean
operation with one of these among its operands) or that may
rewrite it at run time by one of these forms,
each named with its line in the reason: an import from the file's own package (a relative import, an import under its top package,
the file itself among them, an import naming the file's own bare stem, its working absolute name when its directory runs as a
script, or `__main__`), which closes every write through the name by one arm; an attribute named `__globals__`, `__builtins__`,
f_globals,
f_builtins or f_locals, on any receiver; a listed callable (locals, exec, eval, compile, `__import__`, import_module or _getframe)
reached in the first three ways; or one of those callables or attributes, globals, vars, setattr, delattr or `__dict__` reached in
the fourth; or, in a position of the fourth, a key the POSITIVE ALLOWLIST does not prove by its binding; in a call of the getattr
family or of a namespace-key method, which take a key of the fourth by position, a starred argument among its first two or a `**`
mapping, which may put any value in the key's place;
getattr, setattr, delattr or hasattr read other than as a call's callee (an alias or a partial's argument among them), by its own
name, by a name an import binds to it or as an attribute of a builtins receiver, since a lookup through it hands the
census no key to read; or a namespace mapping the file's own module or the builtins may be (globals() or vars() with no argument,
`__builtins__`, or the `__dict__` or vars() of such a module) used other than in a key position whose key the allowlist reads (a
subscript's container, in any context, or the receiver of `.get`, `.pop`, `.setdefault`, `.__getitem__`, `.__setitem__` or
`.__delitem__`). The allowlist accepts only a constant string spelling no listed name; a parameter whose default, if any, holds
constants alone (a constant, constants the census folds to text, or a tuple or list of those), none spelling a listed name; a call's
return whose callee
reaches
neither text nor the str, bytes or bytearray type nor a method of one; a name that is a loop or comprehension target inside a
function over a literal of constants, a once-bound module tuple constant no code can mutate or the one attribute source the file
kernel/host_transport.py holds, sh.SPEC_FIELDS, keyed by binding on the file, the attribute name and the base bound once at module
level and declared global or nonlocal nowhere, whose base reaches no text and for which the file writes no attribute of that name
(it binds and declares no such name, uses an attribute so named only as such a source or an item read, never storing, deleting,
augmenting or calling a method on one, spells the name in no string constant, constants the census folds to it, or keyword, uses
setattr, delattr, `__setattr__` or
`__delattr__`, or an attribute so named, only as the callee of a call each of whose arguments that may name an attribute (the second
of a setattr or delattr called by its bare name, else the first two) folds to string constants other than that name and none of
whose first two arguments folds as constants to that name, imports none of the four under another name,
spells none of them in a string constant or constants the census folds, and names no globals,
vars, locals or
`__dict__` and holds no star import; an argument folds only as a string constant, as constants the census folds to one or as a name
bound in its scope only as the target of a loop in a function's own body or of a comprehension over a tuple, list or set literal
each of whose elements is a string constant or constants the census folds to one), so a new accepted source
enters only by an allowlist edit; a name that is such a target,
or an unpacking target, over a parameter or such a call's return, directly or through names an
assignment, such a target or an unpacking binds to one; a boolean operation or an if-expression each of whose values the allowlist
accepts where it stands; and a name an assignment binds to any of these but a constant string. Every other key refuses by name,
the reason naming what the
walk met: a join, format, format_map or replace call, a `%`, a `+` or an f-string a string constant does not fold; a parameter's
default that holds anything but those constants (a name, a call or a starred element among them); a method of the
name str, bytes or bytearray, however reached; any method called on, or attribute read on, constant text or anything not proven to
reach no text; a direct attribute key or a name bound to one, an attribute source other than that one binding, and that binding
where the file may write its attribute as above, a setter argument of any other shape counting as such a write (a mixed literal, a
dict, an unpacking target, a parameter, a call's return, a join the census does not fold, a starred argument or a keyword among
them), as does a setter's name or an attribute so named used other than as a call's callee (an alias or an argument among them), an
import of one under another name, or a string constant, or constants the census folds, that spells one (for that one binding, one
line under the class limit: a class replaced through type() with a key the census does not fold (one built with chr, say), a
namespace constructor or a store elsewhere on the
base chain, since the census reads no base's text; a setter reached reflectively other than by a string constant, or constants the
census folds, that spells its name, through `__getattribute__`, inspect.getattr_static, an index into a mapping of an object's
members or a getattr handed to another call among them; and a writer other than setattr, delattr, `__setattr__` and `__delattr__`
handed the name other than as a string constant or constants the census folds to it (a name built with chr, say),
functools.update_wrapper and its kin and an item store into a `__dict__` reached
reflectively among them);
a name bound to a constant string; a with target, or a name bound to one; a
walrus, or a name a walrus binds anywhere, a comprehension's
included; a subscript; an augmented assignment; a loop target bound at module level; a name a function or a class body declares
global or a scope declares nonlocal;
a name a class body binds; a name bound only in another form or by no statement; a list, set or dict module constant; and any other
node kind. A name read at module level or as a builtin refuses where the file may rewrite its namespace. The four ways, the whole of the
reach the census reads for each of these names (`__dict__` in the fourth alone, beside
the attribute the computed-name forms above name): by its own name, in any context; by a name an import anywhere in
the file binds to it from its module (locals, exec, eval, compile, `__import__`, globals, vars, setattr and delattr from builtins,
import_module and
`__import__` from importlib, _getframe from sys), in any context, read as the name itself; as an attribute of that name on a
builtins receiver (`__builtins__`, a name that `import builtins [as X]` or `from X import builtins [as Y]` binds, for any module
X, `sys.modules["builtins"]` or `sys.modules.get("builtins")`, or `__import__("builtins")` or `import_module("builtins")`, a call
of either reached in these ways), or on any receiver for exec, eval, locals, `__import__`, import_module and _getframe; or by its
name spelled as a string, or as a join of string constants that reads as one, of the kinds whose text the census reads whole
(listed below), where a run-time lookup by name takes it (the second
argument of getattr, setattr, delattr or hasattr, called by its name, by a name an import binds to it or as an attribute of a
builtins receiver; any argument of operator.attrgetter (any dotted part of the name) or operator.methodcaller, called as
`.attrgetter` or `.methodcaller` on a name that `import operator [as X]` or `from X import operator [as Y]` binds, for any module
X, or by a name that `from operator import attrgetter [as Y]` or `from operator import methodcaller [as Y]` binds; or a key on a
namespace expression: a subscript's slice, or the first argument of `.get`, `.pop`, `.setdefault` or a
`__getitem__`-family call, whose receiver is a `__dict__`, `__builtins__` or a call of vars, globals or locals reached in the
first three ways). Every builtin is rebound in such a file and in a file that names `__builtins__` as a name, imports the builtins
module (`import builtins`, a submodule or an alias among them; `from builtins import ...` at any level; or `from X import
builtins` or `from X import __builtins__`, aliased or not, for any module X at any level) or writes a module that may be the
builtins module: an attribute store or delete on it, a setattr or delattr on it, or its `__dict__` or vars() used any way but for
a `.get` read, where a module that may be the builtins module is `__builtins__`; `sys.modules[k]`, `sys.modules.get(k)` or a call
of `__import__` or import_module as above, whose k is the string "builtins" or no string constant; a name that an assignment, an
annotated assignment or a walrus binds to one of these; or an if-expression or a boolean operation with one of these among its
operands. A function's `X = []` of a local of the same name, or its `X.append(...)`, does not rebind it. A module list, dict or set
constant (a literal or a comprehension a top-level assignment binds) is a container the module writes at run time as well, a
run-time memo no type is read through, where the file changes it other than by the writes listed above for a route's type (a store
or delete through an item of it or on it as an attribute, a method called on it or on an item of it other than one the census
reads a text through (named above), a method called on it whose return is dropped, one of the in-place changers named above read
off it or an item of it unbound, an attribute read off it other than as a method's callee, a setattr or delattr on it, an
augmented assignment to it, which runs its own in-place method, or it or an item of it handed to another object's method by an
operator), changes it through a name bound to it, to an item of it or to a new object holding one (each name read by its spelling
in every scope, so a local of that spelling counts too; a name an unpacking nested in another, or a loop's or a comprehension's
unpacking, binds, and a subscript of a new object as an augmented assignment's target, being the item limit, above), or lets it or
such a
name leave the census's sight (stored into another object, returned, yielded, handed as a default or matched; an item of a literal
that holds only constants and tuples of them, which cannot change, excepted), though none of these rebinds the name; a module name
bound to a call whose object the file changes in one of those ways, directly or through a name bound to it, to an item of it or to
a new object holding one, or lets out of the census's sight, is refused so wherever the pass takes text through it but as a call's
argument, which is under the call limit (its witness: an import's object an attribute store changes, read as
getattr's
argument), as is what a function a module container is handed does with it (its witness: a module dict a function it is handed
stores a fetch into). The proofs by binding above, and the route typing's, read only the page's own file, and a file that imports
the page's module can rebind or change its names at run time. So a walked Python file holding a route candidate (a `_send` call, a
Content-Type write, a send_response call or a getattr naming `_send`) fails the run by name, one SERVED line at its first
candidate, when an import statement of another walked Python file may bind its module: an absolute import where the file's path
ends with the dotted module, a parent package it imports, or the module and a name it imports; a relative import where one of
those, taken from the importing file's directory, is the file's path; or a star import from the file's package. A module reached
any other way (through
sys.modules, a loader by path, a function's `__globals__`, or an object the module hands to other code) is not seen, a stated
limit (its witness: a sibling module whose function stores a fetch into a page module's constant through sys.modules). It follows
a call whose callee is a module function (a top-level def statement that is its name's one
module-level binding, not rebound, in a module with no star import, and bound by no function scope of the page) or a function
defined in the page function (its name's one binding there), each only where the census proves it a plain def: a def statement (not
an async def, whose call returns a coroutine) carrying no decorator (staticmethod and classmethod among them: Python calls a
decorator's return in the def's place), with no yield or yield from in its own body (its call would return a generator), whose name
the file reads nowhere but as a call's callee (an alias, an argument, and a store or delete of the function or of one of its
attributes, `f.__code__ = ...` among them, may run code the census does not read) and, for a module function, spells in no string
constant (which a lookup by name may reach). Any other callee of those two kinds is refused by name, the reason naming the
condition it fails; a module-level def of int or float is not followed but refused as a call of int or float bound other than to
the builtin (above). It also follows a text method or a file read, and any other method through its receiver, as above, and it
reads every call's arguments but those of a call of int or float that is the builtin, a leaf, save where the call is a base
(above). It follows no method called on the
calling method's own first parameter (self by binding, however it is spelled,
the first parameter of a method whose def carries no decorator, never rebound in the method, and read so in a closure, a lambda or a
comprehension of the method that does not bind the name; the first parameter of a route handler that carries a decorator, whatever
it is bound to, or that stands in a file binding staticmethod or classmethod in any scope and by any form, a star import among them,
is not classified, and a method called on it, or it called, is refused by name): every such call is refused by name, since the
server may instantiate a subclass another file defines, whose override of the method the census does not read, and the reason names
what the census found first in the route class's method resolution order, the route class read from its class statement: no def
statement of a class of the file that defines the name first in that order (the order reaching a base whose names the census does
not read, an imported one, before any class of the file that binds the name; the first class that binds it binding it any other way;
no class binding it; or a route class that is not its name's one top-level class statement, whose order the census does not read); a
def that is no plain def (above); a class statement of the file, in any scope, outside that order, that binds the name and derives
from the route class, directly or through classes of the file, or whose derivation the census cannot place (a class statement that
is not its name's one top-level class statement, or one with a base on its ancestor chain that is none of those classes, no
top-level import that is its name's one binding or an attribute of one, and no builtin); the file's replacing the method at run time
(below); and otherwise that subclass. Refused by name as well are a call of a route class's method (a name the body of a route
class, or of a class of the file it derives from, binds in any form outside its nested scopes, a def statement, an assignment and an
import among them, the route class read from its class statement and the names read once per file) on self through anything else
(a local, a loop, comprehension or with target, a container, an if-expression, a BoolOp or a walrus bound to it, or the return of
a function the census follows, read in that function's own scope, as a function the page function defines returning self), on any
other parameter (one a followed function returns among them, `r = _ident(self)` and then `r.get(k)` with `_ident` returning its
parameter), or on a name spelled self that is not the calling method's own first parameter; a call of any other name on self
through
anything else; and a call of any other name on any other parameter, or on a name spelled self that is not that first parameter,
where the file stores, deletes or names to a setter an attribute of that name on any object, which may bind it on a route class or
its instance; each before the file-read and text-call arms and wherever such a call stands on the path of a receiver or a container.
A call to any other callee passes when the callee is such an import, one of the seven builtins a page may name or a parameter other
than such an unclassified first parameter, and is refused by name for any other builtin, for str handed more than one positional
argument, a starred argument or a keyword other than `object`, for max handed one iterable or a starred argument, and for such a
first parameter. For that reason the file may replace
a method at run time where it stores or deletes an attribute of the method's name on any object (the target of an assignment of any
kind, a for, with or comprehension target, or a del), names the method by a string constant, or a join of them, as the second
argument of setattr or delattr (by that name or as an attribute so named) or of `__setattr__` or `__delattr__` called unbound (by
that name, or as an attribute of `object`, of `type`, of a class a top-level class statement of the file binds or of a call of
type()), or as the first argument of `__setattr__` or `__delattr__` called bound on any other receiver (`self.__setattr__("name",
f)`, `super().__setattr__(...)`), or holds a class in the route class's method resolution order that binds `__getattribute__`; and,
with a reason of its own, where it hands setattr, delattr, `__setattr__` or `__delattr__` an attribute name the census does not fold
to a constant string (a name, a parameter or a call's return, one standing after a starred argument, or none at all, among them) or
reaches one of them other than by a call (its name, or an attribute so named, anywhere but as a call's callee, an import of one
under another name, or a string constant, or constants the census folds, that spells one). It reads both operands
of a `/`, a path join. `__file__`, wherever a page reads it
(as a bare name, the base of a receiver, a container or an attribute, or a callee, but never inside the index of a subscript over a
container whose text the pass does not read: below), is refused by name in a file where a statement binds
it, in any scope and by any form, before any scope's or module-level binding of it is read, and there a file read whose path the
census builds from `Path(__file__)` or `open(__file__)` is refused as a file the walk does not scan; where no statement binds it,
the file neither writes a name of its module namespace through a computed name nor may rewrite it at run time, no module-level
statement writes it and the module holds no star import, it is the file's own path: a value slot as a bare name (the argument of
`Path(__file__)` among them) and the path of a file read the census builds from `Path(__file__)` or `open(__file__)`, where it
proves the callee by binding (below); in every other case it is refused by name as a bare name, with that file's reason in a file
that writes its namespace through a computed name or
may rewrite it at run time and with no reason otherwise, and such a file read is refused as a file the walk does not scan, as in a
file where a statement binds it. A file read's path is accepted only as the census proves it by binding: `Path(...)` only where Path
is the file's one top-level `from pathlib import Path`, never rebound, and `open(...)` only where open is the builtin, neither bound
by a function scope around the read, each handed one positional argument and no keyword; its steps a `/` with a string constant,
`.parent` and `.resolve()`; a module constant read in the module's own scope, and a local only where it is a plain local of the page
function bound once. A path whose callee fails those conditions, that reads a name a function scope around the read binds where the
module binds a constant of that name or a module constant the file writes at run time, or that is a relative path spelled as a
string constant, which Python resolves from the working directory, is refused by name as a path the census does not prove by
binding, the line naming the condition it fails; any other path the census does not read is a file the walk does not scan. It
reads a lambda's body, its parameters value slots, and its defaults where the lambda stands in
the page; a lambda reached through a name's value (a local's, a module constant's or a followed function's default, directly or
inside an if-expression, a boolean operation, a walrus, a starred value or a literal) is refused by name where the name is read, a
callee no def statement defines. It reads a subscript's container only under a constant index: a slice of any shape, or an index
that is no
constant (a name, a call, a parameter, a tuple, or a negative number, which parses as a unary expression), over a container whose
text it reads (a literal, an f-string, an operator or an if-expression, a module constant or a local, an attribute, a subscript
or a method call on one of those, or a boolean operation with one of those among its operands) is refused by name, since it reads
the container whole and does not compute what the index selects; honest forms fail closed with it (`_PAGE[1:]`, a template's
leading newline cut; `PAGES[key]` over a dict constant, the key no constant; `_P[-1]`); so is such a subscript over a base whose
own text it does not read that derives through a call handed arguments it reads, whose arguments it reads whole and does not slice
either, whether the subscript is the page expression or stands anywhere on the path of a receiver, a container or an attribute's
base (`str(X)[::-1]`, `dict(a=X)[k]`, `str(X)[::-1].removeprefix(p)`, `str(X)[k].split(s)[0]`); and any
other container that is a base whose own text it does not read, or a call of one or of a method on one, passes whatever its index,
save where the method allowlist refuses a call on its path (above). The index of such a subscript, over a
container whose text the pass does not read, is not read at all, whatever it holds (a name the import system binds, `__file__`, an
attribute read on self, on a parameter or on a class, a call): the item it selects is text such a base holds (above). A None, bool
or int constant, the empty bytes constant and a `*` or `<<` over int constants are value
slots the pass reads as no text; one that stands directly as the right operand of a `%` (bare, a tuple element or a dict literal's
value, an int modulo such as `n % 60` among them), as a `.format` argument (an element of a starred list or tuple literal and a
value of a
`**` dict literal among them) or as a value of the dict literal a `.format_map` is handed is refused by name, whether or not a
conversion takes it, since a conversion can turn it into characters (a `%c`, a `%x`, a `{:c}`, a `%.1s` over the empty bytes), and
one held deeper there (a name or a local bound to one, an if-expression's branch, a list's element, or a call's argument, one of
the seven builtins' among them) is read as a value slot and not refused. The run fails by name (SERVED) on any other reference to `_send` (a read of it that is not a call's function, a
store or delete of an attribute so named, or a string equal to `_send`), a content type the pass cannot read, a content type the
census reads other than as a string constant or a name bound once to one, a script-running type written outside `_send`, a
function that
answers outside `_send` more often than it writes a Content-Type header, a container the module writes at run time (a module name
bound to a call whose object the file changes, read other than as a call's argument, among them), a local container with an
occurrence of its name that is none of the proven forms, an attribute
read on self, on any other parameter or on an except name, each judged by the root its base reaches by binding (so one read on a
local bound to self, or on a method's first parameter however spelled under the conditions above, is one read on self), a class
attribute (an attribute read on
a class, a method called on one among them, through the class's own name, a name the census resolves to it, a method call on or a
subscript of a name whose value holds it or of such a value itself, or any other base whose root by binding is a class), a function
or class object read as a value, a lambda reached through a name's value, a module function or a function defined in the page
function that is no plain def (an async def, one carrying a decorator, one whose own body yields, one whose name the file reads
other than as a call's callee or, for a module function, spells in a string constant), a method called on self, whatever its def, a
route class's method called other than on the calling method's own first parameter, a method called on any other parameter, or on a
name spelled self that is not that parameter, whose name the file stores, deletes or names to a setter as an attribute, a call of,
or a method
called on, a route handler's first parameter the census does not classify, a replacement field reaching an attribute or an index
of its argument in a `.format` or `.format_map`, a
`.format` or `.format_map` whose format string the receiver reaches other than as a string constant, a join of them or a name bound
to one, a
name the import system binds in every module that the file does not bind, a subscript by a slice or an index other than a constant
over a container whose text the pass reads or over a base whose own text it does not read that derives through a call handed
arguments it reads, anywhere on a page expression's path, a subscript by a constant index over a container whose text the pass
reads that stands as an operand of a `+`,
a `%`, an f-string, a `.join`, a `.format`, a `.format_map` or a `.replace`, a value
slot that stands directly as the right operand of a `%`, a `.format` argument or a `.format_map` value, a builtin other than the
seven a page
may name, a call of str with more than one positional argument, a starred argument or a keyword other than `object`, a call of max
handed one iterable or a starred argument, a call of int or float bound other than to the builtin, a method whose return the
census does not compute, called on a receiver the pass reads whose text it is not drawn from, or on a base whose own text it does
not read (a `.strip` among the latter, whose return is a piece of that unread text) that derives through a call handed arguments
it reads (a call of int or float that is the builtin among them) or is one of the seven builtins' names called unbound, at any
call on a page expression's path, a join,
format, format_map or replace called on the name str, bytes or bytearray, a `.replace`, `.format`, `.join`, `.format_map` or
`.encode` in a shape the census does not compute, a `%`, `.format` or `.format_map` on a string constant that is not expanded, a
join whose folded
text may run past a million characters, `__file__` in a file where a statement binds it, any other receiver or container, any other
callee (a module constant, a local, a class, a
subscript, a call and a lambda among them), any
other bare module name (one bound other than by one assignment, one bound by an annotated, unpacking or chained assignment, one
annotated at module level beside its assignment, one no module-level statement binds that a function or a class body binds under a
`global` declaration, an
import, a function or a class beside another module-level
binding, an import, a def or a class bound once inside a module-level block and not by a top-level statement, a name bound once in
any other form inside such a block's body, a name a star import may rebind, a module name in a file that writes its module
namespace through a computed name or may rewrite it at run time (the reason naming the form and its line), a builtin in a file
that may rewrite the builtins, and a rebound import, builtin, function or
class among them), any other kind of expression in a page (a non-empty bytes, float, complex or Ellipsis constant, an f-string's
format spec, any other operator, a comparison and a unary expression among them, and a yield, a yield from or an await, whose
value is what the generator is sent, what the iterator it delegates to returns or what the awaited object returns, not its
operand), and a route whose body yields no piece and no file slot (each
refusal of page text applies where the pass reads that text, never inside the index of a subscript over a container whose text the
pass does not read: above), unless the served allowlist, SERVED_ALLOW, names the place by its function and expression, with the
number of places the entry
covers and the reason (the two answers with no body, the CORS preflight's 204 and the websocket upgrade's 101, are named there);
an entry that names nothing in the run, or covers a different number of places, fails the run too. A method call the method
allowlist refuses whose page is honest is named instead in the served listing, SERVED_LISTED, keyed the same way: its place is not
excused but listed, one line after the stylesheets the listing names, with the entry's reason, and the run does not fail on it; an
entry there that names nothing in the run, or covers a different number of places, fails the run too. One place is so listed:
`str(app or "").capitalize()` in the kernel's `_pane_label`, called from `_shim`, whose callers are the seven page routes, each
passing a constant lowercase pane key, and `_shim_core_js`, which passes its own parameter (default `"test"`). In served text
every `fetch(`
and `import(` on a line is read by its own argument, and no comment skip applies, since a joined constant is one line whatever
it starts with. Each string literal is read on its own, and so is the text of each of these joins of string constants, at its
first literal's line: a `+` of them (an f-string's literal text at its start or end among them), an f-string whose fields are
string constants, a `%` of them, and a `.join`, `.format`, `.format_map` or `.replace` called on a string constant or on one of
these joins: a `.join` over a list or tuple of them or over a dict literal whose keys they are (the keys in order, a repeated key
at its first place), and a `.format`, `.format_map` or `.replace` of them (implicitly concatenated literals are one constant
already). The same methods called on the name str, bytes or bytearray (`str.join("", [...])`, unbound) are no such join and refuse
by name. A `.replace` other than with two positional arguments, a `.format` or a `.join` with a starred argument or a `**`
keyword, a `.format_map` other than with one positional argument that is a dict literal whose keys are each a string constant, and
an `.encode` other than with no argument or with one string constant that is `utf-8`, `utf_8` or `utf8`, in any case, also refuse
by name, since the census does not compute their text; an errors argument to `.encode` is among those refused, since a handler
registered with codecs writes any text in place of a character UTF-8 cannot encode, and so is every other encoding: another
spelling, even one Python also encodes as UTF-8 (`utf 8`), on the safe side, one Python hands to the codec registry (`u-t-f-8`),
where a search function the file registers may answer it, and an encoding that is no string constant (a name bound to `"utf-8"`),
which the census does not fold. A `%`, `.format` or
`.format_map` on a string constant or on one of these joins is not expanded when a field
or precision is wider than a million characters (a `%` conversion's width or precision, or any run of digits in a format field's
own spec) or when a format spec holds a replacement field, whose width is computed at run time; each such call refuses by name,
whatever its arguments, and each conversion of a `%` is read as Python's `%` parses it (its mapping key to the parenthesis that
balances its first, `%%` the literal percent). No join of string constants is expanded past a million characters: one whose folded
text may run past that length (a `+`, an f-string, a `.join` or a `.replace` by its text's exact length, a `.format` or
`.format_map` by Python's own length for each field, a `%` by an upper bound) refuses by name, each literal still read on its own, a
string constant, which is source text, aside; the width test bounds one field and this cap the whole text. A tool's name, a tag, an
attribute, an import or a
fetch URL split
across such a join is therefore read whole, and a site both reads find is listed once; a fetch URL cut at the join is listed as
the joined text reads it, whole. A `.format` or `.format_map` whose format string holds a replacement field whose name reaches an
attribute or an index of its argument (`{0.CSS}`, `{h.CSS}`, `{self.body}`, `{0[k]}`) refuses by name, since the text such a field
reads is the argument's attribute or item, which the pass does not read: the census looks for such a field where the format string
is the receiver's text, a string constant or one of these joins, or the value of a module constant or a local bound to one, and a
`.format` or `.format_map` whose format string the receiver reaches any other way (a function's or a method's return, a parameter,
an attribute, an if-expression, a `+` over a name among them) is refused by
name too, since the pass does not read that format string's fields, unless the receiver is a class (above), refused as a class
attribute, a subscript whose join the pass does not compute, refused as that, or one the pass refuses by name, in whole or in part,
as it reads it (`self.X.format(...)`, `Handler.X.format(...)`), that line standing for the text the receiver holds. Text a page
joins through anything but a string constant (a name,
a call, an attribute, a
subscript of a container whose text the pass does not read, or a field or a `%` slot holding one) is read piece by piece: a tool's name, a tag or an attribute split there is not seen, and a fetch URL cut there is
classed by the part before the cut. A subscript by a constant index over a container whose text the pass reads (the containers
named above for a slice) that stands as an operand of one of these joins, a `+`, a `%` or an f-string, or the receiver or an
argument of a `.join`, `.format`, `.format_map` or `.replace` (an element of a list, tuple or set literal or a key of a dict
literal handed to `.join`, an element of a starred list or tuple literal handed to `.format`, and a value of a dict literal handed
to `.format` or `.format_map`, among them), is refused by name, since the pass reads its container whole and not the text the join
makes of the pieces the indexes select; the refusal is keyed on such a container, and a subscript of any other container is read
piece by piece, as above; a subscript read through a function falls under the call limit above. A `.join` whose one argument, or,
unbound as in `str.join("", {...})`, its second, is or holds a set literal or a set comprehension as the census reads it refuses
by name, its iteration order not fixed, so its join is no one text: the argument itself, a walrus's value, an if-expression's
branches, a boolean operation's operands, a list or tuple display's elements (a starred one's value among them), the sources of a
list or dict comprehension or a generator (one that names the comprehension's own target excepted, its items held by an earlier
source), and the values of a local of the page's scope or of a module constant that the census reads the name by (a local's
values, a loop's, an unpacking's or a with target's source and a local container's appended or stored values among them, or a
module constant's value), a name bound so in turn; a set the census reaches only through a call's return (a function's, or a read
method's, a set's copy or a dict's get among them) or through a parameter (the argument a call hands it, or its default) is read
piece by piece, under the join limit above (its witnesses: a set a module function returns, a set's copy and a set a dict's get
returns, and a set a module function's parameter takes as its argument and one it takes as its default, each joined, a fetch split
across its elements). A file the page
reads at run time is covered by the walk only where the walk scans it as browser text, its DOM loads counted as a page's are (a
JavaScript file under ui/ or vscode-extension/src), and only where the page reads it with an encoding the census reads as utf-8,
utf_8 or utf8, or with none: the walk scans each file once as UTF-8, so a page that reads such a file with any other encoding, or through a `**` keyword whose mapping the census cannot read, is refused by name, since that one scan may not be the text the page serves, and a read that names no encoding takes the locale's default, a stated limit the census cannot prove is UTF-8; one the walk scans as Python, as shell, or as JavaScript elsewhere, its
DOM loads not
counted, is refused by name, the kind named, since the walk reads none of its text as a page's; a stylesheet the walk does not scan
is named, not scanned; and any other file is refused by name, as a path the census does not prove (above) or as a file the walk does
not scan, each unless SERVED_ALLOW names the read. A site in served text is listed
at the first line of the string part that carries it. Text joined across implicitly concatenated literals is one part, listed at
its first line, and a site that only a join of string constants holds (the join's text, read beside its literals' own reads) is
listed at the join's first literal's line. On Python 3.10 and 3.11 an f-string part is
listed at the line where the expression before it ends, so a part
that starts on a later line (after a `}` on a line of its own, or in the next literal of a concatenation) is listed early. The
count is the same on every interpreter. The whole of kernel.py is not scanned as text, since a text scan misreads Python and JS
concatenations (a Python method spelled like a client, a `from` inside a script split across Python literals). Over served text
the import gate's statement form applies to a line that starts with import or export, and to a line led by `from` or a closing
brace only where it continues an import or export statement that begins its own line and has not yet ended (a line led by a
closing brace is a multi-line import's last line in a module and any block's in a page's script), while a literal require() or
import() spelled whole on one line (the name, its paren, the quoted specifier and the closing paren, with nothing between them but
whitespace inside the parens) is gated wherever it stands. The served pages' rows are keyed by tool (kernel/kernel.py plus
WebSocket, window.open or
clients.openWindow) and counted once per line; only fetch and import() are read per match. A second socket or opener in the
served text is therefore caught by the count per key when it changes the tool or stands on a line without its tool, and not when
it joins a line, a joined constant (literals joined implicitly) or a join of string constants that already carries its tool, as
any rowed shell
or JavaScript line is (the residual above). Named and not counted in the served text: a stylesheet's `url()` loads (THEME_CSS's
fonts, _LOADER_CSS's face,
_RDRIFT_CSS's and the dashboard shell's own rules, and the pane stylesheets under ui/webview read at run time), every one a
`/media` path on the kernel's own origin, and the same-origin
navigations no list names (`location.replace` on the token login page, `location.reload` in the shim and the shell,
`navigator.serviceWorker.register('/sw.js')`, `history.replaceState`).
A program the kernel starts (ssh, git, gh, npm, npx, the session CLIs, the operator's helper, a watch predicate) may open
connections this scan cannot see: such a site is listed by program, on a road that says so."""
import _string   # str.format's own field parser and field-name split (_Served._format_length)
import ast
import builtins
import collections
import json
import os
import re
import string
import sys
import weakref

EXPECTED = os.path.join("scripts", "network-inventory-expected.json")
PY_ROOTS = ("kernel", "cli", "postal", "bin", "hooks")     # every kind by extension or shebang, recursively
JS_ROOTS = ("ui", "vscode-extension/src")                   # the browser and editor kinds only, recursively
NAMED = ("bootstrap.sh", "install.sh", "vscode-extension/install.sh", "tools/file-comments-host.mjs")
SKIP_DIRS = ("__pycache__", "node_modules")

NET = {"urllib.request.urlopen": "urlopen", "urllib.request.Request": "Request", "urllib.request.urlretrieve": "urlretrieve",
       "urllib.request.build_opener": "build_opener", "http.client.HTTPConnection": "HTTPConnection",
       "http.client.HTTPSConnection": "HTTPSConnection", "socket.create_connection": "create_connection", "ssl.wrap_socket": "wrap_socket",
       "asyncio.open_connection": "open_connection", "asyncio.open_unix_connection": "open_unix_connection", "socket.sendto": "sendto",
       "asyncio.sock_connect": "loop.sock_connect", "asyncio.create_connection": "loop.create_connection",
       "asyncio.create_datagram_endpoint": "loop.create_datagram_endpoint",   # event-loop methods, on a loop the scan resolves
       "anyio.connect_tcp": "connect_tcp", "anyio.connect_unix": "connect_unix", "smtplib.SMTP": "smtplib",
       "ClaudeSDKClient": "sdk-client", "claude_agent_sdk.ClaudeSDKClient": "sdk-client", "sdk.ClaudeSDKClient": "sdk-client",
       "CodexClient": "sdk-client", "openai_codex.client.CodexClient": "sdk-client", "SubprocessCLITransport": "sdk-transport"}
SUB = {"subprocess." + n: n for n in ("run", "Popen", "check_output", "check_call", "call", "getoutput", "getstatusoutput")}
SUB.update({"os." + n: "os." + n for n in ("system", "popen", "execv", "execve", "execvp", "execvpe", "execl", "execlp", "spawnv", "spawnvp",
            "spawnl", "spawnlp", "posix_spawn", "posix_spawnp")})
SUB.update({"asyncio.create_subprocess_exec": "create_subprocess_exec", "asyncio.create_subprocess_shell": "create_subprocess_shell",
            "webbrowser.open": "webbrowser.open"})
# A socket method is a site on a receiver the scan resolves: a name bound to socket.socket() in the function, or a tuple-literal
# address argument. A loop method is a site on a loop the scan resolves: a name bound to one of the getters, or the getter's call.
SOCKET_METHODS = ("connect", "connect_ex", "sendto")
LOOP_GETTERS = {"asyncio.get_event_loop", "asyncio.get_running_loop", "asyncio.new_event_loop"}
LOOP_METHODS = ("sock_connect", "create_connection", "create_datagram_endpoint")
# A module named to these is an import and goes through KNOWN_IMPORTS; an argument the scan cannot resolve fails the run (IMPORT).
IMPORTERS = ("importlib.import_module", "__import__")
# The default rules place a row-less command site only when its program is a fixed literal with no network use of its own.
LOCAL_TOOLS = {"ps", "scutil", "systemctl", "journalctl", "systemd-run", "osascript", "notify-send", "xdg-open", "open", "zenity"}
LOCAL_GIT = {"rev-parse", "status", "log", "show", "diff", "symbolic-ref", "merge-base", "rev-list", "merge", "ls-files", "describe", "tag"}
# A shell or an interpreter runs a program text this scan does not read: never local by default, and the external-program class.
INTERPRETERS = {"sh", "bash", "dash", "zsh", "env", "node", "perl", "ruby", "python", "python3", "sys.executable"}
KERNEL_URL_HELPERS = ("ku", "kernelUrl", "fileUrl", "sliceUrl")
# Every top-level module the scoped Python files import. A module outside this set fails the run (IMPORT): a new HTTP or
# socket client is then itself the loud line, and takes its primitives into NET or SUB, or a note here that it opens nothing.
KNOWN_IMPORTS = set("""
__future__ abc anyio argparse array ast asyncio base64 bisect calendar claude_agent_sdk codecs collections concurrent contextlib copy
cryptography ctypes datetime difflib email errno fcntl functools gc glob gzip hashlib hmac http importlib inspect itertools json
math openai_codex os pathlib pickle platform pty queue random re resource secrets select selectors shlex shutil signal smtplib
socket socketserver ssl stat statistics struct subprocess sys tempfile termios threading time traceback tracemalloc unicodedata
urllib uuid warnings weakref webbrowser zlib zoneinfo
perf_export perf_public spend_repair
""".split())   # the last three are cli/ siblings imported by name; a relative import resolves inside the scanned tree
# Every package the scoped JavaScript and TypeScript files import or require: the specifier's first path segment (two for a
# scoped package, `node:` dropped); a specifier starting with `.`, `/` or `*` is the project's own module or a declaration
# file's ambient path pattern and is not gated. A package outside this set fails the run (IMPORT). The ones that open
# connections or start programs are child_process (the manager, the editor extension and the timeline view start programs
# through it, each a site of the family in line_scan), http (the manager, the extension, its attach helper and the timeline view
# reach the kernel on the loopback, each a site), ws (the extension's websocket to the kernel, a site) and vscode (the editor
# API: its `openExternal` hands a URL to the operating system's default browser, a site of the clicked-link road); every other
# one opens nothing: the node built-ins for files, paths, hashing and assertions; the TypeScript compiler; and the browser
# libraries the webview bundles (markdown, math, sanitising, highlighting, the editor widget, PDF rendering). `module` opens
# nothing itself, but its createRequire makes a require the import gate cannot read, so a `createRequire(` call is refused by
# name (_js_unread_requires), and the one at this head, a test helper's, is placed by JS_ALLOW with its reason.
KNOWN_JS_IMPORTS = set("""
child_process http ws
assert crypto fs module os path url util vscode typescript
marked katex dompurify highlight.js pdfjs-dist
@codemirror/autocomplete @codemirror/commands @codemirror/lang-css @codemirror/lang-html @codemirror/lang-javascript
@codemirror/lang-json @codemirror/lang-markdown @codemirror/lang-python @codemirror/language @codemirror/legacy-modes
@codemirror/search @codemirror/state @codemirror/view
""".split())
# The JavaScript allowlist, in SERVED_ALLOW's shape and keyed on the code, never a line: (file, the expression as the refusal
# spells it) -> (the number of places the entry covers, the reason). A family module's literal specifier that no counted binding
# takes and no arm reads a call through, and on a walked line a require or import the import gate cannot read, are each an
# IMPORT line unless named here (line_scan); an entry that names nothing in the run, or covers a different number of places
# (distinct line and column positions), is an IMPORT ALLOW line, so a new place under an entry's key is read or named, never
# excused by it. A named file stays walked, and every other line of it is read.
JS_ALLOW = {
 ("bin/romp-manager", "require.main"): (1,
  "the manager's entry guard, `if (require.main === module)`: it asks whether the file runs as the program and loads no module"),
 ("ui/romp-timeline-view.js", "require('http')"): (1,
  "`new (require('http').Agent)(...)`, the keep-alive agent the view's kernel proof and its post share (their two `require('http')"
  ".request` calls are sites on the local-kernel row): it constructs an agent and opens no connection"),
 ("ui/webview/real-viewer-leg.ts", "createRequire(path.join(EXT, \"package.json\"))"): (1,
  "a test-only helper: nothing at run time imports it, and its importers are the webview test files, ui/webview/shell-drag-leg.ts "
  "(itself imported only by tests and a bench tool) and that bench, tools/viewer-resize-bench.ts; the require it makes loads "
  "esbuild and playwright for the browser legs, and neither is in KNOWN_JS_IMPORTS"),
 ("ui/webview/real-viewer-leg.ts", "import (?!type\\b)"): (1,
  "a regex literal, `/^import (?!type\\b)...from \"[^\"]+\";/gm`, that reads render.ts's import statements as text: no import runs"),
}
CP_FAMILY = ("exec", "execSync", "execFile", "execFileSync", "spawn", "spawnSync", "fork")   # child_process's program starters
# The one program the kernel starts from a directory outside the runtime trees; a string constant naming tools/ or scripts/
# from the runtime trees that is not one of these fails the run (PROGRAM).
KNOWN_PROGRAM_REFS = {"file-comments-host.mjs"}   # kernel/kernel.py _FILE_COMMENTS_HOST = ROOT / "tools" / "file-comments-host.mjs"
_PROGRAM_PATH = re.compile(r"^(?:tools|scripts)/.*\.(?:py|mjs|cjs|js|sh)$")   # a program path spelled as one string constant

# The table: "file:function" (a Python site) or "file:tool" (a shell or JavaScript line) -> road. Every function with a site that
# reaches another machine is named here, and so is every loopback or local-program site the default rules cannot place, and every
# external-program site whatever its road. A site with no row fails the run.
T = {}
def _t(road, *keys):
    for k in keys: T[k] = road
K, S, J, P = "kernel/kernel.py:", "kernel/sdk_backend.py:", "kernel/judge.py:", "postal/postal_service.py:"
_t("price-feed", K + "_refresh_remote_prices.work"); _t("model-catalog", K + "_fetch_models_api"); _t("fast-org-probe", S + "_fetch_key_fast_org")
_t("web-push", K + "_push_post"); _t("release-check", K + "_latest_release_tag"); _t("drift-check", K + "_origin_main_sha")
_t("self-update", K + "_run_update"); _t("main-converge", K + "_run_main_update"); _t("pr-watch", K + "_pr_watch_read")
_t("file-viewer-ls-remote", K + "_git_net_out"); _t("predicate-watch", K + "_watch_run"); _t("npm-install-retry", K + "_ensure_bundles")
_t("ssh-tunnel", K + "_spawn_tunnel", K + "Handler._remote_ws", K + "_remote_kernel_call", K + "_checkin_handshake", K + "_checkin_stop_hub",
   K + "_poll_remote_sessions", K + "_remote_forward_answer", K + "_poll_remote_version", K + "_poll_remote_usage", K + "_poll_remote_api_health",
   K + "_poll_remote_views", K + "_peer_call", K + "_peer_spend_call", K + "Handler._remote_control", K + "Handler._remote_api_health",
   K + "Handler._remote_sessions", K + "Handler._remote_file", K + "Handler._relay_download")
_t("ssh-one-shot", K + "_host_reachable", K + "_fetch_remote_token", K + "_remote_kernel_up", K + "_start_remote_kernel", K + "_discover_remote_clone",
   K + "_update_remote", K + "_restart_remote_kernel", K + "_open_folder_remote")   # _update_remote: its git push and its guarded apply
_t("git-to-attached", K + "_pull_remote"); _t("api-key-helper", "kernel/credentials.py:run_helper"); _t("watch-pr-registration", "bin/romp:gh")
_t("session-cli", "kernel/session_host.py:PipeCliTransport.connect", "kernel/session_host.py:SessionHost._spawn", S + "SdkBackend._spawn_host", S + "SdkSession._amain",
   K + "_login_start", K + "_aprobe_commands", "kernel/codex_backend.py:CodexBackend._get_client")
_t("judge-cli", J + "_judge_run_impl", K + "_JudgeChild._start"); _t("bus-peers", P + "_peer_http")
_t("local-bus", K + "_bus_send_relay", K + "_bus_recall_relay", K + "_bus_restore_mail", K + "_notify_bus_peer", K + "_notify_bus_origin_trust",
   K + "_bus_peers_snap", K + "_bus_quarantine_act", K + "_ensure_postal_bus", K + "_bus_converge", P + "_http", P + "ensure", P + "_restart_self")
_t("local-manager", K + "_manager_kernels", K + "_restart_this_kernel", "bin/romp-manager:http.get", "bin/romp-manager:http.request", "bin/romp-manager:spawn",
   "vscode-extension/src/kernel-attach.ts:http.request")
_t("local-kernel", P + "_kernel_sessions_checked", P + "_kernel_post", P + "_kernel_get", P + "_kernel_up", P + "_seed_peers_from_kernel", "cli/perf_export.py:read_kernel.get",
   "cli/restart_metrics.py:kernel_live", "cli/update.py:_kernel", "cli/update.py:_get", "cli/update.py:_post", "cli/version.py:_probe_kernel", "bin/romp:curl",
   "bin/romp-service:curl", "hooks/romp-wake.sh:curl", "hooks/romp-usertodo-context.sh:curl", "vscode-extension/src/extension.ts:http.get",
   "vscode-extension/src/extension.ts:WebSocket", "ui/webview/federation.ts:WebSocket",
   "ui/webview/preview.ts:window.open",   # a browser open is placed by the URL it opens: preview.ts's `openFileTab` opens
                                          # `fileUrl(path, sid)`, the kernel's own /file route or its /remote/<host>/file relay,
                                          # in the browser's own tab, so the site is local; the document that tab opens can load
                                          # other hosts: an .svg is a document that loads what its markup names (SVG_TAB_ROW)
   "ui/romp-timeline-view.js:http.request",   # the timeline view's two `require('http').request` calls: the kernel proof (GET /healthz)
                                              # and the panel's post, both to 127.0.0.1 with the panel's own token; the editor host
                                              # reaching this machine's kernel, as the extension's http.get above
   K + "WebSocket", K + "window.open", K + "clients.openWindow")   # the served pages' own script (served_texts): the shim's pane socket
   # and the shell's socket dial location.host; the timeline boot's window.open is reached by no caller at this head (the view's one
   # caller passes a vscode: URL, which the boot posts to the host and returns); the service worker's clients.openWindow opens the
   # URL of the kernel's own push payload (_push_payload's data.url, a path on this origin), else /
# The shell scripts' inline interpreter texts (external-program by class: a program text this scan does not read), keyed file
# plus tool and rowed with what the text does, read once for the row: bin/romp's `python3 -c` and `python3 -` texts parse the
# JSON the kernel's curls returned and render it, quote a query string (urllib.parse, no request), and stamp the restart audit
# row; bin/romp-service's renders the down marker's time; the hooks' read the SDK registration file and render the hook's JSON
# output; bin/romp-uninstall's edit the settings files, the shell rc and the judge scratch. None opens a connection of its own.
_t("local-kernel", "bin/romp:python3 -c", "bin/romp:python3 -", "bin/romp-service:python3 -", "hooks/romp-postal-context.sh:python3 -c",
   "hooks/romp-postal-context.sh:python3 -", "hooks/romp-postal-ensure.sh:python3 -c", "hooks/romp-usertodo-context.sh:python3 -")
_t("local-program", "bin/romp-uninstall:python3 -")
_t("local-git", K + "_release_remote")   # a bare `git remote`: the list of remote names from .git/config, no subcommand that fetches
_t("local-program", K + "_port_open", K + "_primary_addr", K + "_rebuild_dist", K + "_open_folder", K + "_open_file", K + "_run_dialog", K + "_system_notify",
   K + "_run_bounded", K + "_git_out", S + "interpreter_tag", S + "cli_scope_supported", S + "proc_start", S + "SdkBackend._session_cli_pid", S + "SdkBackend._end_cli_tree",
   S + "SdkBackend._stop_leftover_scopes", S + "SdkBackend._boot_reconcile", S + "SdkBackend._oom_killed_scope", S + "SdkBackend._scope_journal",
   S + "SdkBackend._host_orphan_recover", J + "_serve_fault", K + "main", "vscode-extension/src/extension.ts:execFile", "ui/romp-timeline-view.js:execFile",
   "kernel/host_transport.py:HostTransport.connect")   # the SDK transport's connection to a session host's Unix socket
# _serve_fault: a test-only fault route runs `sh -c echo`, a fixed literal that prints and opens nothing (external-program by class)
_t("browser-figures", "ui/webview/figure-gate.ts:figureHosts", "ui/webview/preview.ts:Image")
_t("chat-media", "ui/webview/render.ts:mdImgPostPass")   # the chat pipeline's one line on a message's pictures before the browser fetches
                                                          # them (md and userMd): the road is named from it, as browser-figures is from the gate's read
# The openers of a URL the content carries, on both hosts: the extension's one `vscode.env.openExternal` (inside `openLink`, reached
# from the chat panel's handler and from `routeViewMessage`'s `openLinkLocally` for the feed panel, the outline panel and view and
# the timeline view) and the browser bundles' `window.open` in the chat page's click delegate, in the shared opener the feed, the
# outline and the Waiting-on-you panes install, and in the file viewer's URL-anchor open. Every one sits in a click or
# pointer-release handler; a fifth `window.open`, preview.ts's own-tab open of the kernel's file URL, is local by its URL
# (above), and what an .svg it opens then loads is SVG_TAB_ROW's.
_t("clicked-link", "vscode-extension/src/extension.ts:openExternal", "ui/webview/render.ts:window.open", "ui/webview/link-opener.ts:window.open",
   "ui/webview/file-view.ts:window.open")
_t("install-bootstrap", "bootstrap.sh:curl", "bootstrap.sh:git clone", "bootstrap.sh:git fetch", "bootstrap.sh:git pull")
_t("install-sdk-setup", "bin/romp-sdk-setup:curl", "bin/romp-sdk-setup:wget", "bin/romp-sdk-setup:pip install")
_t("install-ext", "vscode-extension/install.sh:npm install", "vscode-extension/src/extension.ts:install.sh",
   "vscode-extension/install.sh:node -e", "vscode-extension/install.sh:npx")   # the version stamp (local) and the vsce fetch, both behind the editor-CLI gate
_t("install-codex-setup", "bin/romp-codex-setup:pip install", "kernel/codex_runtime.py:install_runtime")
LOCAL_ROADS = {"local-bus", "local-manager", "local-kernel", "local-program", "local-git"}
RUNTIME_ROADS = {"predicate-watch", "api-key-helper"}   # the program text itself arrives at run time
CLASSES = ("external-program", "runtime-program", "browser-computed-url", "browser-dom-loads")
# The clicked-link road's residual, one text in three homes: the docstring above, the road's trigger cell below and SECURITY.md's
# Network access section (tests/test_security_price_feed.py holds the three equal).
CLICK_RESIDUAL = ("three anchors the chat page's click delegate leaves to the default action (one with no scheme that the page built; one with "
                  "no scheme in a message that does not resolve to an http or https address; a message's own download anchor, one with no scheme "
                  "carrying a `download` attribute whose href resolves to an http or https address on this page's origin, which the browser saves "
                  "from this origin), and a page-built anchor with a scheme in a document that installs no opener (the gear's sign-in link on the "
                  "dashboard's settings page and in the editor's feed panel is one), are gestures this tree does not route: on the dashboard the "
                  "browser's own open or download, and what the editor's own webview host does with them is outside this tree")
# The paint clause, one text in every home: the chat-media row's sent cell and the paint row's below, SECURITY.md's Network access
# section and the two test modules' constants (tests/test_price_feed_census.py, tests/test_security_price_feed.py): which of an inline
# svg's paint references load from another host in each engine, and what those requests carry. PAINT_LIST, its first half, is the
# .svg tab row's list of the paint references its document loads.
PAINT_LIST = ("in Chromium a `fill`, `stroke`, `clip-path`, `mask`, `marker-start`, `marker-mid` or `marker-end` whose `url()` names another "
              "host loads from that host, in Firefox and WebKit at least a `mask` does, and a `filter` does in no engine")
PAINT_CLAUSE = (PAINT_LIST + "; each such request carries no cookie and carries the page's origin (the dashboard's scheme, host and port, the "
                "port omitted when it is the scheme's default) in its Origin header; in Chromium a `mask` request can also carry that origin as its Referer, from any page, framed or bare; and "
                "a paint request can carry the full page address with the serve token in its Referer, but only when the page's own address "
                "carries `?token=` (a pane page opened bare, such as `/chat?token=`; the shell drops the token from its address before it "
                "frames its panes, and frames them without it); these paint requests are the one exception to the trust model's sentence on "
                "`Referrer-Policy: same-origin` (the response is blocked as cross-origin; the request, with those headers, has reached the host)")

# The table's prose columns, one entry per road in the order the ledger entry prints them; the where column is derived from the
# sites on every run, so a hand-written member cannot survive here. Text: the repository's privacy documentation.
ROADS = [
 ("price-feed", "price feed (kernel-request)",
  "through `_token_analytics` with refresh: a build of the Token usage view's payload (`/analytics`), on an open of the view or a period picked in it, when the last fetch attempt is older than `PRICE_TTL`, six hours, or there has been none this kernel life; never at boot; nothing re-arms it",
  "GET of the public LiteLLM price table on raw.githubusercontent.com, no credential", "`ROMP_PRICE_FEED=off`"),
 ("model-catalog", "model catalog refresh (kernel-request)",
  "through `_refresh_model_catalog`, from `_model_catalog_boot` and `_note_unknown_model`: the first boot with no catalog cache file; after that once per unknown `claude-*` model id per kernel life (a set path or a pick names an id the merged list lacks); single-flight, up to ten pages",
  "GET `/v1/models` on api.anthropic.com (`ROMP_MODELS_URL` overrides) with the apiKeyHelper's key, else the `ANTHROPIC_AUTH_TOKEN` bearer claimed at startup; a box with neither sends nothing",
  "`ROMP_MODEL_CATALOG=off`"),
 ("fast-org-probe", "fast-mode organisation probe (kernel-request)",
  "through `key_fast_org_env` and `helper_fast_org_env`, from `SdkSession._options` (every connect compose) and kernel/judge.py `_fast_org_env`: every key-billed connect of a session (a launch, a resume, a reconnect, the reconnect a fast toggle makes) when the operator's apiKeyHelper is configured and the project's own settings name no other helper: the fetch runs first and the memo spares only a failed one; the judges ask once per judge process (the kernel, or the `romp-judge --serve` child when `STATE/judges-process` reads on) for a key-billed call whose tier's Fast-mode box is on with a fast-capable (Opus family) model, and ask again after any CLI fast refusal drops the memo",
  "GET `/api/claude_code_penguin_mode` on api.anthropic.com (`ANTHROPIC_BASE_URL`) with the helper's key, three-second bound",
  "none of its own: no helper, no probe; a login-billed session, no probe"),
 ("web-push", "web push (kernel-request)",
  "through `_push_send_one` and `_push_notify` (a card needing you, a completion, a turn end, a relayed peer event) and the `/push/test` route: every notification event while `push-subscriptions.json` holds a row, one POST per subscription; a 404 or 410 removes the row",
  "an aes128gcm-encrypted payload (title, body, routing) to each subscription's endpoint, the push service of the subscribed phone or browser (Apple, Google, Mozilla), signed with the kernel's own VAPID key; the service sees ciphertext",
  "none in the environment; unsubscribe on the device (the bell), which removes the row"),
 ("release-check", "release check (kernel-runs-a-command)",
  "through `_update_check` and `_update_check_loop`: at boot and every six hours (`_UPDATE_CHECK_EVERY_S`) on a clone with a VERSION file, in update modes ask (the default) and auto; re-armed at every boot",
  "`git ls-remote --tags <release remote>`: `upstream` when the clone has one, else `origin`, GitHub for a bootstrap install; git's own credential if the remote needs one",
  "`ROMP_UPDATE_CHECK=off`, or the gear's update mode off"),
 ("drift-check", "main drift check (kernel-runs-a-command)",
  "through `_main_drift_check` and `_update_check_loop`, behind the audience gate `_main_channel_verdict`: every 300 s (`_MAIN_CHECK_EVERY_S`) when the clone is main-tracking: on branch main, or update mode auto, or with an attached or remembered machine; re-armed at boot",
  "`git ls-remote <release remote> refs/heads/main`", "`ROMP_UPDATE_CHECK=off`, or update mode off"),
 ("self-update", "self-update to a release (kernel-runs-a-command)",
  "a bash script: the update banner's Update click, or update mode auto when a newer release tag is found, once per tag",
  "`git fetch <release remote> refs/tags/<tag>`, then `./install.sh`, which runs bin/romp-sdk-setup (pip against PyPI or pip's configured index; get-pip.py from bootstrap.pypa.io when the python lacks ensurepip) and vscode-extension/install.sh (`npm install` against the npm registry on every run, and `npx --yes @vscode/vsce package`, a fetch of vsce from the same registry even when it is cached, only when an editor CLI is present or `ROMP_EXT_PACKAGE_ONLY` is set) unless `ROMP_NO_SDK` or `ROMP_NO_EXT` is set; then a restart request to the manager on the loopback",
  "update mode ask (the default) runs it only on a click; `ROMP_UPDATE_CHECK=off` stops the discovery"),
 ("main-converge", "main converge (kernel-runs-a-command)",
  "kind pull: the drift banner's Update click, or update mode auto, on a main-tracking clone whose main moved",
  "`git fetch <release remote> main`; the rest is local (status, merge-base, checkout, `node esbuild.js`, a restart request to the manager)",
  "update mode off, or ask (a click only); `ROMP_UPDATE_CHECK=off`"),
 ("pr-watch", "PR watch (kernel-runs-a-command)",
  "through `_pr_watch_tick` in the tunnel supervisor pass: per registered row (`romp watch-pr`, POST `/watch-pr`) every 60 s (`PR_WATCH_EVERY`; 90 s while checks run), re-armed at boot from `pr-watches.json`, retired on merge, close or three consecutive gh failures; a failed check holds the watch and keeps polling",
  "`gh pr view <n> --repo <owner/repo> --json state,statusCheckRollup` to GitHub's API on gh's own token",
  "none: no registration, no poll; a cancel retires the row"),
 ("watch-pr-registration", "watch-pr registration (a romp CLI verb a session or the user runs, not the kernel)",
  "the `watch-pr` verb: `romp watch-pr` given no `--repo`, once per registration",
  "`gh repo view --json nameWithOwner` to GitHub's API on gh's own token", "none; `--repo` skips the call"),
 ("file-viewer-ls-remote", "file viewer origin check (kernel-runs-a-command)",
  "through `_origin_has_branch` and `_file_github_link`: a viewer open of a file in a git checkout whose current branch has no local tracking ref under origin; a no is remembered while the clone's refspec tracks the branch, until the ref appears; anything else is asked again per open; three-second bound; every credential prompt closed",
  "`git ls-remote --heads origin refs/heads/<branch>` to the checkout's origin (GitHub for a GitHub-hosted file); a configured credential helper may answer, askpass is refused",
  "none"),
 ("predicate-watch", "predicate watch (kernel-runs-a-command)",
  "through `_watch_tick` in the supervisor pass: per registered row (`romp watch`, POST `/watch`) every `every` seconds (floor 15, default 60) until exit 0, the timeout (24 h by default; a longer caller bound stands, a shorter one re-arms through the default) or a cancel; re-armed at boot from `watches.json`; each run bounded to 45 s",
  "whatever the registered command sends: it runs as `/bin/sh <scratch file holding the text>`, so the program is RUNTIME-SUPPLIED and this scan sees the shell and nothing else",
  "none"),
 ("ssh-tunnel", "ssh tunnels and everything over them (kernel-runs-a-command, and kernel-request over the forward)",
  "`_spawn_tunnel` (`_tunnel_argv`) on an attach (the dashboard or `romp`), re-attach at boot from `remotes.json`, a redial of a dead ssh on a backoff ladder, every tunnel dropped and redialed on a route change; over the forward the supervisor polls each attached host's kernel every 15 s (`SUPERVISOR_PASS_S`; 0.25 s while a row is in transition), and the browser's `/remote/<host>/` requests and websocket are relayed over it on demand",
  "`ssh -N -T` (BatchMode, no multiplexing) with `-L` forwards to the remote kernel and bus, plus `-R` forwards for a check-in; over it HTTP to the remote kernel with that machine's own serve token, and the postal peering",
  "none in the environment; detach the host"),
 ("ssh-one-shot", "one-shot ssh commands on an attached host (kernel-runs-a-command)",
  "an attach and the boot re-attach (the serve-token read; the kernel-port probe and the remote start when that kernel is down), a dial's death (the reachability probe), the Update, Pull and Restart actions on a remote row (clone discovery, the push, the guarded apply, the guarded restart), an automatic push of this machine's build when the gear's auto-update remotes is on (off by default), and a remote session's folder click (a terminal running `ssh -t`)",
  "one ssh command per call on the attached host (a `cat` of its serve-token file, a `/dev/tcp` port probe, `nohup romp-serve`, `git rev-parse` and `git status` in its clone, a reset-and-restart script), and `git push --force` of the committed HEAD to a scratch ref in the remote clone over `GIT_SSH_COMMAND`",
  "none; the automatic push is a gear setting, off by default"),
 ("git-to-attached", "git fetch from an attached checkout (kernel-runs-a-command)",
  "the Pull action on a remote row (`/tunnels/pull`, the sync-pull action)",
  "`git fetch <host>:<remote clone dir> HEAD` over ssh, then a local fast-forward", "none"),
 ("npm-install-retry", "npm install retry at boot (kernel-runs-a-command)",
  "at boot when the served bundles are older than their sources, `node_modules` exists and the `node esbuild.js` build fails: one `npm install --no-audit --no-fund`, then one rebuild",
  "package downloads from npm's configured registry", "none (`ROMP_EXT_DEV_BUILD` changes the build profile only; no `node_modules`, no build)"),
 ("api-key-helper", "the operator's own commands: the apiKeyHelper and a stored login's token command (kernel-runs-a-command)",
  "through `helper_key` (callers kernel/kernel.py `_models_api_credential`, kernel/sdk_backend.py `helper_fast_org_env`, kernel/judge.py `_fast_org_env`) and through kernel/logins.py `token_value` (callers kernel/sdk_backend.py `SdkSession._options`, kernel/judge.py `_judge_env`): the helper, from Claude Code's managed or user settings (never a project's), runs through `/bin/sh` whenever the kernel needs the key and its memo is past the TTL (`CLAUDE_CODE_API_KEY_HELPER_TTL_MS`, five minutes by default): the catalog refresh and the fast-mode probe, so at key-billed connects and the judges' once-per-process ask; a stored login's token command runs with no memo at every launch, resume or reconnect of a session billed to that login and at every judge call billed to it, on the login-billed side",
  "whatever those programs send (a password manager's or a vault's read), on their own credentials, from a whitelisted environment, stdin closed, stderr discarded",
  "none of romp's: no helper configured and no stored login, nothing runs"),
 ("session-cli", "the session CLIs (session-or-judge-cli)",
  "`SessionHost._spawn` (the SDK's `SubprocessCLITransport`, a class outside this tree) and `PipeCliTransport.connect` (the SDK-less test transport); `SdkBackend._spawn_host` (bin/romp-session-host) and `SdkSession._amain` (`ClaudeSDKClient`; with hosts off the SDK spawns the CLI in the kernel process); `_aprobe_commands` (the slash-command probe) and `_login_start` (the login flow); `CodexBackend._get_client` (`CodexClient`, the `codex app-server`): a session's launch, resume and reconnect (hosts on by default: one host process per session starts the CLI); the composer's slash-command list for a cwd not probed in 300 s starts a CLI with no prompt; the Billing flyout's login action starts the CLI's OAuth flow; a Codex session's first use starts one app-server per backend",
  "the sessions' own model calls to Anthropic (or `ANTHROPIC_BASE_URL`) on the session's billing (the machine's login, a stored login's token, or the key the CLI resolves through the apiKeyHelper), plus whatever the CLI does on its own; a Codex session's calls to OpenAI on its login",
  "none: running them is what romp is for"),
 ("judge-cli", "the judges' CLI (session-or-judge-cli)",
  "`_judge_run_impl` (`perl` alarm around `claude -p`, or `codex exec`); `_JudgeChild._start` (`bin/romp-judge --serve`, the judges' process when `STATE/judges-process` reads on): every judge call (triage, index, distill and the rest) on session activity, one CLI run per call",
  "the judge prompt (session excerpts) to Anthropic on the call's billing (the machine's login tokens, a stored login's token, or the key the CLI resolves through the apiKeyHelper), or to OpenAI through `codex exec` when `STATE/judge-engine` reads codex",
  "none in the environment; the engine setting picks the CLI"),
 ("bus-peers", "the postal bus to peer buses (bus-request)",
  "through `_peer_exchange_once` and `_peer_loop`: one long-poll exchange per up peer, re-issued as each returns (backoff to 30 s on errors), while the kernel reports the peer's tunnel up",
  "POST `/peer-exchange` (mail relays, presence) to the peer's bus through the tunnel's local forward, with the peer machine's serve token",
  "`ROMP_POSTAL_PEERS=0` (the legacy singleton mode, where the bus is reached over an `-R` forward instead)"),
 ("browser-figures", "a viewed file's pictures from the web (browser)",
  "a viewed markdown file's pictures and clips whose host is on the gear's Pictures from the web in files list load when the file opens (the default list, ui/webview/settings.ts `FIGURE_HOSTS_DEFAULT`: github.com, raw.githubusercontent.com and the other GitHub image and asset hosts, localhost, 127.0.0.1); a figure from another host loads on one click; the viewer's retry (`probeMdImgUrl`) probes a failed figure's URL",
  "GET of the figure's URL from the browser showing the dashboard, with that browser's own cookies for the host; the loads themselves are DOM insertions this scan cannot see (the browser-dom-loads row), so this road is named from the gate's host-list read and the retry probe, not from a request",
  "the setting (remove the hosts)"),
 ("chat-media", "a rendered message's media (browser)",
  "the render of a message on the web dashboard, and nothing else: no click, no gate, no setting; every text the chat page renders as markdown through `md` or `userMd` (ui/webview/render.ts): a session's reply (`md`, from the assistant branch of `renderEventInner`), your own message (`userMd`, from its user branch and from `renderQueued`'s echo of a pending send), the other texts that branch and that echo show (a Continue press, a message romp or another program sent to the session on your behalf, a note the harness injected such as a command's output, a notice from romp: `md` in `renderEventInner` and `renderQueued`), a compaction summary (`renderCompact`), an injected notice and a background task's report (`renderInjected`, `renderAgentNotif`), a subagent's skill text, prompt and report (`renderTool`), a postal body (`md` in `renderPostalService`), a peer agent's message (`renderTeammate`) and an agent's reply in a file comment thread (`commentMsgEl`) go through marked and the shared sanitizer (ui/webview/md-sanitize.ts), whose html profile keeps `img` (src, srcset), `video` (src, poster), `audio`, `source` and `picture` (and an inline svg's `image`), and are written into the page with `innerHTML`, at which point the browser requests every one; `mdImgPostPass`, the row's site, is the pipeline's one line on a message's pictures before the browser fetches them (a URL that failed this page life is parked, and re-probed by the browser-figures row's `Image` site on a reconnect); the editor extension's webviews block these loads by their CSP (`img-src` the webview's own resource origin and `data:`, no `media-src` under `default-src 'none'`), so this road is the web dashboard's alone",
  "GET of each media URL as the message's author wrote it (a session, you or a peer, a class this scan cannot bound), from the browser showing the dashboard to the host the URL names, with whatever cookies that browser sends to that host and no Referer to any other origin (every page the kernel serves carries `Referrer-Policy: same-origin`); an inline svg's paint references load at render too, with no click: " + PAINT_CLAUSE,
  "none: no setting gates a message's media (the gear's Pictures from the web in files list gates a viewed file's figures, not the chat's)"),
 ("clicked-link", "a link you click (browser)",
  "your click, and nothing else: in the browser showing the dashboard, the chat page's click delegate (`window.open` in ui/webview/render.ts) opens every anchor with a scheme, a link in a session's reply or in your own message, a whole-backtick URL, a URL in a todo's text or a pinned note, the address a todo carries, a pull-request reference; the shared opener (ui/webview/link-opener.ts, installed by the feed, the outline and the Waiting-on-you panes) opens a pull-request or URL link on a pointer release or an Enter; the file viewer (`openUrlTab` in ui/webview/file-view.ts) opens a URL in a viewed file's text on a modified click (Ctrl, Cmd or the middle button; a plain click is left to the browser's own open of the anchor); the file viewer's GitHub button (`GitHub \u2197`, an anchor of class `fileview-btn` in the title bar's `fileview-gh` span, rowed once the owning kernel's `fileGitLink` reply carries a URL) opens as the document it stands in decides: on the chat page the click delegate takes it as it takes every anchor with a scheme (`window.open`, the anchor's default action cancelled); on the Files pane, the feed page and the Waiting-on-you page the anchor's own default open (target `_blank`, rel `noopener`: the browser's new tab), since no opener in those documents matches it (the viewer's own `linkOf` returns only `[data-act=\"openpath\"]`, `a.fv-url` and `a.fv-frag` inside the body, and the button stands in the title bar; the shared opener serves `a.pr-link` and `a.url-link`), so no modified-click path reaches it (`openUrlTab` runs only for a link `linkOf` returns) and a middle click is the browser's own on every page; the viewer mounts in no editor webview (a file click there opens the file in the editor), so the button has no editor leg; the gear's sign-in link, an anchor the gear builds to open in a new tab (`a.target = '_blank'` in ui/webview/gear.js), opens by document: on the dashboard's settings page (/settings), which installs no opener, the browser's own open in a new tab, no site of this tree running on the click; in the editor extension's chat panel, which mounts the gear, the chat delegate's `openLink` post; in the editor's feed panel, which mounts the gear too and installs only the pull-request opener, the webview host's own link handling, outside this tree; in the editor extension the chat delegate, the shared opener and the file viewer post the href to the host, whose `openLink` (vscode-extension/src/extension.ts, from the chat panel's handler and from `routeViewMessage`'s `openLinkLocally` for the feed panel, the outline panel and view and the timeline view) hands it to `vscode.env.openExternal`, the extension's own `vscode://romp.romp-chat-view` deep link handled in the extension instead and never reaching a browser; every opener sits in a click or pointer-release handler, no automatic step; " + CLICK_RESIDUAL,
  "the clicked URL, as the content carries it, to the host that URL names, requested by the browser showing the dashboard (a new tab, `noopener,noreferrer`) or, from the editor extension, by the operating system's default browser, with that browser's own cookies for the host: a pull-request link carries the session's repository name (from the checkout's origin remote, or the text's own owner/repo) and the number, to github.com; the file viewer's GitHub button carries an address romp composes (`_file_github_link` in kernel/kernel.py, run by the kernel that owns the file, once per viewer open): `https://github.com/<owner>/<repository>/blob/<branch or sha>/<path>`, the checkout's owner and repository name read from its origin remote, its current branch, or the commit sha when HEAD is detached, and the file's path inside the checkout, each segment percent-encoded and slashes kept, to github.com, with that browser's own cookies for github.com and no Referer (the chat page's opener passes `noreferrer`; every page the kernel serves carries `Referrer-Policy: same-origin`); the button is not rowed, and no address composed, for an untracked, staged-only or uncommitted file, a path outside a git checkout, a checkout with no origin remote or with one not on github.com, or a relative path with no session directory to place it; no query string is ever added; a link in a message, a todo, a pinned note or a viewed file is whatever its author wrote, a session, you or a peer, a class this scan cannot bound; the gear's sign-in link is the CLI's own OAuth request to claude.com or claude.ai; romp adds no serve token, key or login token to a link's URL (a link is built from content or the checkout, never from the page's address; a paint request's Referer, in the chat-media row and the row for the chat's file preview and a notice card, can carry the full page address with the serve token, but only when the page's own address carries `?token=`)",
  "none; nothing sends until you click"),
 ("install-bootstrap", "bootstrap.sh (install-time-by-hand)",
  "by hand: the documented one-liner, and re-runs",
  "`curl` of bootstrap.sh from raw.githubusercontent.com (the one-liner itself), `git clone` of the repository (`ROMP_REPO`; github.com by default), on an existing clone `git fetch --tags origin` then `git pull --ff-only`, then `./install.sh`",
  "none"),
 ("install-sdk-setup", "bin/romp-sdk-setup (install-time-by-hand; also run by the kernel's self-update through install.sh)",
  "the `fetch` helper and the pip lines; install.sh runs it unless `ROMP_NO_SDK=1`: by hand at install, and at the kernel's self-update",
  "get-pip.py from bootstrap.pypa.io only when the python lacks ensurepip (`ROMP_GET_PIP_URL` overrides); `pip install --upgrade pip`, `pip install claude-agent-sdk==<pin>`, `pip install --upgrade cryptography` from pip's configured index, PyPI by default",
  "`ROMP_NO_SDK=1` skips the script; `ROMP_NO_GET_PIP=1` skips the bootstrap fetch"),
 ("install-ext", "vscode-extension/install.sh (install-time-by-hand; also run by the kernel's self-update and by the editor extension's update prompt)",
  "`npm install` on every run; `node -e` and `npx` only when an editor CLI is present (`code`, `code-insiders`, `cursor` or `codium` on PATH, or an editor bundle under `ROMP_EDITOR_APPS`) or `ROMP_EXT_PACKAGE_ONLY` is set, the script exiting after the build otherwise; install.sh runs it unless `ROMP_NO_EXT=1`; the editor extension's `runInstall` (`execFile bash`): by hand at install; the kernel's self-update; the editor extension's update prompt, on the user's click",
  "`npm install` against npm's configured registry, then a local `node esbuild.js`; behind the editor-CLI gate, a local `node -e` that stamps package.json's version, `npx --yes @vscode/vsce package`, which asks npm's configured registry for vsce even when it is cached, and a local `code --install-extension`; with no editor CLI and `ROMP_EXT_PACKAGE_ONLY` unset nothing after `npm install` is sent",
  "`ROMP_NO_EXT=1` for install.sh"),
 ("install-codex-setup", "bin/romp-codex-setup (install-time-by-hand)",
  "the setup script, and kernel/codex_runtime.py `install_runtime`, which the setup runs as a script (the kernel only looks the runtime up: kernel/codex_backend.py `runtime_path`; `ensure_codex_sdk` installs nothing): by hand",
  "`pip --isolated install openai-codex==<pin>` from PyPI (no get-pip fetch: the script refuses an unverified bootstrap); the pinned Codex CLI wheel from github.com's release downloads, hash-checked, with `--no-index`",
  "none"),
]
LOCAL_ROW = ("local, set aside and counted (local)",
  "each a connection to this machine or a fixed program with no network use of its own: the kernel to the manager, the postal bus and itself; the bus, bin/romp's curls, cli/*, the installed hooks, the VS Code extension and the manager to the kernel on 127.0.0.1; the browser's fetch and websocket to the kernel's own origin (a relative URL or a kernel-URL helper), the served pages' own scripts included (the shim's and the shell's sockets to location.host, the shell's fetches of its own routes, the service worker's open of the kernel's own push URL, and the timeline boot's window.open, which no caller reaches at this head), and its own-tab open of a file the kernel serves (`fileUrl`; the loads an .svg opened that way makes are the .svg tab row's); the SDK transport's connection to a session host's Unix socket; git read-only queries, ps, scutil and the systemd tools spelled out in the argv; and `_primary_addr`'s UDP connect to TEST-NET-1, which sends no packet. A program on a local road whose far end this scan cannot derive is counted in the external-program row, never here",
  "as the kernel, the CLIs and the browser run", "nothing is sent to another host", "not applicable")
# Each class label ends with the kind suffix; the external-program label is SECURITY.md's phrase for the class (a program
# romp's code starts whose far end its arguments do not show, whichever of the kernel, a shell script, the manager or the
# editor extension starts it), and tests/test_security_price_feed.py holds the two equal by reading this binding.
CLASS_ROWS = {
 "external-program": ("an external program started whose far end its arguments do not show (not derivable by this scan)",
  "as the roads above run: every site of this class sits on a road by an explicit row with its reason, and is never set aside as local",
  "whatever the program sends: a shell, node, perl or python runs a program text this scan does not read, started by the kernel, by a shell script inline (`python3 -c`, `python3 -` with the text on stdin, `node -e`) or by the manager or the editor extension (child_process); `shell=True` and child_process's exec run the configured command; git with a subcommand the code does not spell out and an argv the code does not spell out (RUNTIME-SUPPLIED) name their program at run time",
  "the road's own switch; none for the class"),
 "runtime-program": ("a program supplied at run time (not derivable by this scan)",
  "as the predicate watch and the operator's own commands rows run",
  "whatever the registered text sends: the predicate as `/bin/sh <scratch file holding the text>`, the helper or token command through the shell",
  "none"),
 "browser-computed-url": ("a browser request whose URL is computed at run time (not derivable by this scan)",
  "as the dashboard runs: a fetch whose first argument is a variable, or a dynamic import of a computed module URL; at this head each reads a kernel URL by its binding (a `same-origin` mode, a `fileUrl` or `kernelUrl` result, the PDF worker's URL derived from its own chunk's script src), and in the dashboard shell's scripts a route literal its caller passes (fetchDoc, vact, readSwitch and post in kernel/kernel.py) and the drift banner's per-host route (`route[h]` in _RDRIFT_JS, '/tunnels/askpull' or '/tunnels/update' by the host's row), which the scan cannot derive from the line",
  "to the URL the variable holds at run time; the kernel's own origin at this head by reading the bindings (the editor's webview reaches the same served bundles by its resource URL)",
  "not applicable"),
 "browser-dom-loads": ("the browser DOM's own loads (not derivable by this scan)",
  "as the dashboard and the editor views render: an element that loads (an image, a frame, a script, a stylesheet) loads its URL when the attribute lands, and an anchor's href waits for a click; the viewer's and the chat's rendered-markdown insertions load their figures with no attribute line at all and are not counted",
  "to the URL written: kernel URLs (`fileUrl`, `mediaSrc`, `/media`), object URLs and editor webview URIs, and for a viewed file's figures the hosts the browser-figures road names, and for a rendered message's media the host its URL names (the chat-media road), and for an inline svg's paint references in the chat's file preview and a notice card the hosts they name (that row, named and not counted); an anchor's href write loads nothing by itself, the click that opens it is the clicked-link road, and a `window.open` is a site of its own (that road, or a local row), not a load counted here",
  "the figure-host setting for figures; not applicable otherwise"),
}
# Named and not counted: the scan cannot see this class by construction, so its row states the mechanism and the test module
# plants one call and holds the row to it (the sentence in the where cell is the docstring's).
UNSEEN_ROW = ("a socket primitive on a receiver this scan cannot resolve (not derivable by this scan)",
  "not counted: a socket primitive called on a receiver the census cannot resolve (an attribute-held or parameter socket) is not a site here; the scan resolves a socket receiver as a name bound to `socket.socket()` in the same function or by a tuple-literal address, and a rule on the method name alone would tag the backends' and transports' own connect methods, which are not sockets",
  "wherever such a call would run; no site of this class can be listed by this scan",
  "to the address the socket is given at run time",
  "not applicable")
# The paint references of two surfaces that strip media, a road named and not counted: their loads are rendered-markdown insertions
# with no attribute line, and tests/test_security_price_feed.py counts by grep every call in render.ts spelled `md(` or `userMd(`,
# a gap before the paren allowed, on one line (`md (t)` and `x.md(t)` among them), and every reference to stripRemoteLoads (a call,
# an import, an alias) in the .ts and .js files directly under ui/webview and vscode-extension/src, skipping test files, each name's definition (`function md(` and the like), a line that
# opens with `//`, `*` or `/*`, and the text from a `//` that starts the line or follows whitespace; each match is counted under the
# nearest `function NAME(` line at or above it, so a new call or reference moves a count and is red: under its caller's name when
# that line declares the caller, and otherwise under the function that line declares, or under none above the first such line.
# render_table prints it beside the browser-dom-loads row.
PAINT_ROW = ("an inline svg's paint references in the chat's file preview and a notice card (browser)",
  "not counted: two surfaces render markdown through the shared sanitizer (ui/webview/md-sanitize.ts) and then `stripRemoteLoads` (ui/webview/file-preview.ts), which removes an element whose src, srcset, poster or data, or an svg image's, use's or feimage's href, names another origin, and reads no paint attribute: the chat's file preview (`previewMdClean` in ui/webview/render.ts) and a notice card's body (`noticeBodyNodes` in ui/webview/feed.ts); their loads are rendered-markdown insertions with no attribute line, so this scan cannot count them; tests/test_security_price_feed.py holds the calls of `stripRemoteLoads`, one in each of these two and one in the provider slot in `renderFilePreview`, which no producer fills at this head, and counts by grep every call in render.ts spelled `md(` or `userMd(`, a gap before the paren allowed, on one line (`md (t)` and `x.md(t)` among them), and every reference to stripRemoteLoads (a call, an import, an alias) in the .ts and .js files directly under ui/webview and vscode-extension/src, skipping test files, each name's definition (`function md(` and the like), a line that opens with `//`, `*` or `/*`, and the text from a `//` that starts the line or follows whitespace; each match is counted under the nearest `function NAME(` line at or above it, so a new call or reference moves a count and is red: under its caller's name when that line declares the caller, and otherwise under the function that line declares, or under none above the first such line",
  "the chat's file preview of a markdown file: a pointer dwell of 350 ms (`PREVIEW_DWELL_MS`) or a keyboard focus on a link in the chat to a markdown file the kernel allows to preview (one in the session's folder or your home; a glossary term links to its section the same way); a notice card's body: the feed page painting the card, its body written by a session through POST `/notice` (`romp card`), a session on an attached machine included; no click, no gate, no setting; the editor extension's webviews block these loads by their CSP (`img-src` the webview's own resource origin and `data:`), so this road is the web dashboard's alone",
  "GET of each paint reference's URL as the file or the notice carries it (a file in the session's folder or your home, whoever wrote it; a notice a session posted), a class this scan cannot bound, from the browser showing the dashboard to the host the URL names; only an inline svg's paint references load there (an image, video, audio, a poster and an svg image are stripped before the nodes join the page): " + PAINT_CLAUSE,
  "none: no setting gates them")
# The .svg tab road, named and not counted: its loads are the opened document's own, named by the file's markup, with no line in this
# tree, and the one site on its way, preview.ts's `openFileTab`, opens the kernel's own URL and is counted local-kernel (above).
# tests/test_security_price_feed.py holds the row to SECURITY.md's sentence and bounds its population: image/svg+xml is the one
# document type /file serves a file's bytes under. render_table prints it after the roads.
SVG_TAB_ROW = ("an .svg opened in its own tab (browser)",
  "not counted: the loads are the opened document's own, named by the file's markup, and have no line in this tree; the tab is opened by `openFileTab` in ui/webview/preview.ts (a `window.open` of `fileUrl(path, sid)`), a site counted on the local-kernel road because the URL it opens is the kernel's own; image/svg+xml is the one type /file serves a file's bytes under that a browser tab opens as a document (the `_media_policy_headers` docstring in kernel/kernel.py), so an .svg is the whole population",
  "on the web dashboard only: a Cmd, Ctrl or middle click on a path link to an .svg in a viewed file (`data-act=\"openpath\"` in ui/webview/file-view.ts: a markdown link such as `[diagram](diagram.svg)`, or a bare path in a viewed text file), or Cmd or Ctrl with Enter or Space on a focused one (`pathLinkKey` in ui/webview/path-links.ts), reaches `openFileTab`, which opens the kernel's `/file` URL in the browser's own tab with no check of the file's kind; for a file of a session on an attached machine the URL is the `/remote/<host>/file` relay, which sends the same headers (read on the wire from a second kernel on this machine standing in for the attached one; the ssh tunnel itself was not exercised); a plain click shows the svg in an image at an object URL, which loads nothing from another host, and the editor extension has no such tab (`canPreview` is false in its webviews)",
  "the tab is an svg document, sandboxed by the kernel's `Content-Security-Policy: sandbox` so no script runs in it, that loads each resource its markup names from that resource's host (whether or not the host is on the gear's Pictures from the web in files list), among them an `image` element's `href` or `xlink:href`, a CSS `@import`, an `xml-stylesheet` instruction, an `feImage`, HTML inside a `foreignObject` (an `img`, a stylesheet, a frame, a video, audio, an object or an embed), a cursor image, a web font, and paint references: " + PAINT_LIST + "; a `use` that names another host loads in no engine; a frame the markup embeds is a page from that host, which loads what that page names in turn; a load the browser makes without CORS (an image, a stylesheet, a frame, a media element, an embedded object, or in WebKit a web font), or a load the markup marks `crossorigin=\"use-credentials\"` on an `img`, `image`, `link rel=\"stylesheet\"`, `video` or `audio` element, carries whatever cookies that browser sends cross-site to that host; a paint reference, a web font in Chromium and Firefox, or a load the markup marks `crossorigin=\"anonymous\"` on one of those elements (a video's poster aside), carries none; for a load to another site: in Chromium none of the tab's own loads carries a Referer, the sandbox withholding it; in Firefox and WebKit the page's `Referrer-Policy` withholds it, and markup that relaxes that policy (a referrer `meta` or a `referrerpolicy` attribute) makes such a load carry at most the dashboard's origin; a framed page's loads to another site carry at most that frame's origin, and those a stylesheet names in turn at most that stylesheet's own address in Chromium and Firefox and what the tab's own loads carry in WebKit; and the tab's address (`/file?path=...` or `/file?path=...&sid=...`, or its `/remote/<host>/file` form) carries no serve token (the cookies a load carries cross-site are `SameSite=None` ones, not Lax or Strict ones; the sandbox gives the document an opaque origin; with the sandbox removed, a `mask` request to another site in Chromium carried the page's origin, and with the page's `Referrer-Policy` removed and the sandbox kept, the tab's loads to another site in Firefox and WebKit carried the dashboard's origin)",
  "none: no setting gates it (the gear's Pictures from the web in files list gates a viewed markdown file's figures in the viewer, not an opened tab)")

SH = [("curl", r"\bcurl\s"), ("wget", r"\bwget\s"), ("git clone", r"\bgit (?:-C \S+ )?clone\b"), ("git fetch", r"\bgit (?:-C \S+ )?fetch\b"),
      ("git pull", r"\bgit (?:-C \S+ )?pull\b"), ("git push", r"\bgit (?:-C \S+ )?push\b"), ("git ls-remote", r"\bgit (?:-C \S+ )?ls-remote\b"),
      ("npm install", r"\bnpm (?:install|ci)\b"), ("pip install", r"\bpip\S*\"? (?:--isolated )?install\b"),
      ("gh", r"\bgh (?:pr|repo|api|release|run|issue|auth)\b"), ("ssh", r"\bssh\s+\S"),
      ("npx", r"(?:^|[\s;&|(`{])npx\s"), ("scp", r"(?:^|[\s;&|(`{])scp\s"), ("rsync", r"(?:^|[\s;&|(`{])rsync\s"),
      ("sftp", r"(?:^|[\s;&|(`{])sftp\s"), ("nc", r"(?:^|[\s;&|(`{])nc\s")]
# The interpreter arm: a head (path-prefixed or not) followed by -c or -e, or by a bare `-` (the program on stdin, the heredoc
# shape); the tool the site is keyed on is the head with its flag (`python3 -c`, `python3 -`, `node -e`), and the class is
# external-program. Keyed on the head, never on the flag alone: `[ -e file ]` and `grep -c` carry those flags too.
SH_INTERPRETER = re.compile(r"(?:^|[\s;&|(`])(?P<head>(?:\S*/)?(?:python3?|node|perl|sh|bash))\s+(?P<flag>-c|-e|-)(?=\s|$)")
JS = [("fetch", r"\bfetch\("), ("WebSocket", r"new WebSocket\("), ("EventSource", r"new EventSource\("), ("Image", r"new Image\("), ("http.get", r"\bhttps?\.get\("),
      ("http.request", r"\bhttps?\.request\("), ("net.connect", r"\bnet\.connect\("), ("net.createConnection", r"\bnet\.createConnection\("),
      ("tls.connect", r"\btls\.connect\("), ("XMLHttpRequest", r"\bXMLHttpRequest\b"), ("sendBeacon", r"\bsendBeacon\("),
      ("import()", r"(?<![\w.$])import\("), ("figureHosts", r"loadSettings\(\)\.figureHosts"),
      ("openExternal", r"vscode\.env\.openExternal\("), ("window.open", r"window\.open\("),   # the URL openers: sites that take a row
      ("clients.openWindow", r"\bclients\.openWindow\("),   # the service worker's opener of a notification's URL: a site that takes a row
      ("mdImgPostPass", r"(?<!function )\bmdImgPostPass\(")]   # the chat-media road's row; the definition in preview.ts is not a site
# The child_process family is matched through its binding (see _cp_bindings), never as a bare name: `exec(` is RegExp exec too.
DOM = [("attribute write", r"\.(?:src|srcset|href)\s*=[^=]"), ("setAttribute", r"setAttribute\(\s*[\"'](?:src|srcset|href)[\"']"),
       ("template", r"<(?:img|script|iframe|link|source|video|audio|a|embed|object)\b[^>]*\b(?:src|srcset|href)=")]   # window.open is a JS site, not a load


def _compiled(tools):
    """A pattern list compiled once, with one alternation of the whole list: line_scan hands a line to the list's per-tool loop
    only when the alternation matches it, and the alternation matches exactly when some pattern of the list does, so a line
    that names no tool costs one search instead of one per pattern. Which lines are sites, and under which tool, is unchanged."""
    return [(name, re.compile(rx)) for name, rx in tools], re.compile("|".join("(?:%s)" % rx for _name, rx in tools))


SH_RX, SH_ANY = _compiled(SH); JS_RX, JS_ANY = _compiled(JS); DOM_RX, DOM_ANY = _compiled(DOM)


class Site(object):
    __slots__ = ("file", "line", "prim", "head", "fn", "road", "cls", "kind")
    def __init__(self, file, line, prim, head, fn, road, cls, kind):
        self.file, self.line, self.prim, self.head, self.fn, self.road, self.cls, self.kind = file, line, prim, head, fn, road, cls, kind
    def key(self):
        return "%s:%s" % (self.file, self.fn if self.fn != "-" else self.prim)
    def tuple(self):
        return (self.file, self.line, self.prim, self.head, self.fn, self.road or "", self.cls or "")


class Result(object):
    def __init__(self):
        self.sites, self.dom, self.problems, self.files, self.skipped = [], [], [], [], 0
        self.served, self.served_files = [], []   # the Python files whose served pages were scanned; the stylesheets a page reads at run time
        # SERVED_ALLOW's, SERVED_LISTED's, FRAME_WRITERS's and JS_ALLOW's matches this run (key -> the source positions it covered; a JS_ALLOW key is
        # (file, expression), a file with no colon, so no key of one list is a key of another), and per Python file the module
        # names some code writes after binding them (a subscript store or delete, a mutating call, a binding under `global`): the
        # run-time memos; and per Python file the rebinds, the names a function binds under `global` or a statement at module level
        # writes, each of which costs an import, a function, a class or a builtin its exemption in the served pass (_Served._sole); and
        # per Python file every `global` declaration in a function or class body, (the enclosing defs, the names it declares), which
        # _global_binder reads to name the body that binds a declared name (routes_of's file-wide refusal of a `_send` so bound, and
        # _Served._module_why's reason for a module name only such a body binds)
        self.allow_hits, self.writes, self.rebinds, self.global_decls = {}, {}, {}, {}
        # line_scan's import gate: each specifier its forms loop reads, (file, line, specifier), and each walked line where the
        # refusal of a require or import the gate cannot read fires, excused by JS_ALLOW or not, (file, line); js_reads hands both out
        self.reads, self.unread = [], []
        # per Python file, whether it may write its own module namespace through a computed name or its builtins, whether a
        # statement binds `__file__`, and the first run-time form by which it may rewrite either (_namespace_flags over Scan's
        # facts): the served pass and the `_send` gate read it
        self.ns = {}
        # per Python file, what the served pass's follow proof reads of the names its top-level def statements bind (_Served._plain_def):
        # each such name read other than as a call's callee, name -> [(its position, the scopes around it as Scan.kscopes holds them)],
        # and the set of those names a string constant of the file spells (Scan.visit_Name, Scan.visit_Constant)
        self.fn_refs = {}
        # per Python file, the names layer iv's module side finds changed other than by the forms Result.writes records (Scan.cwrites):
        # the served pass reads a module name bound to a call that is one of them as a run-time memo (_Served.cmemos)
        self.changed = {}
        # each walked file's kind as the walk scanned it (walk, kind_of), rel -> "py", "js" or "sh": a file a served page reads at run
        # time is covered by the walk only where the walk scanned it as browser text (served_texts, _browser_text; layer v of the eleventh round's rulings)
        self.kinds = {}
        # per Python file, each import statement in any scope, (its line, its level, its module or None, the names a from-import
        # imports or None for a plain import, one entry per module a plain import names), and per Python file holding a route
        # candidate (a `_send` call, a Content-Type write, a send_response call or a getattr naming `_send`: Scan) the line of its
        # first: scan's refusal of a page module another walked file imports reads both (_page_importers)
        self.imports_of, self.candidates = {}, {}
    def emit(self, *a):
        self.sites.append(Site(*a))


def _call_arg(line, opener, at=None):
    """The first argument of an `opener` (`fetch(`, `import(`) on the line, up to its top-level comma or the closing paren: the
    first opener on the line, or the one that starts at index `at` (served text reads every match, each by its own argument)."""
    text = line[(line.index(opener) if at is None else at) + len(opener):]; depth, out = 0, []
    for ch in text:
        if ch in "([{": depth += 1
        elif ch in ")]}":
            if depth == 0: break
            depth -= 1
        elif ch == "," and depth == 0: break
        out.append(ch)
    return "".join(out).strip()


def _runs_off(line, start, comma=True):
    """Whether the argument text after an open paren at `start` runs to the end of the line with no closing paren (and, where
    `comma`, no top-level comma), as _call_arg counts brackets: a call whose argument a string literal joined after this one
    carries on (line_scan's `cut`)."""
    depth = 0
    for ch in line[start:]:
        if ch in "([{": depth += 1
        elif ch in ")]}":
            if depth == 0: return False
            depth -= 1
        elif ch == "," and depth == 0 and comma: return False
    return True


_HELPER_CALL =re.compile(r"^(?:%s)\(" % "|".join(KERNEL_URL_HELPERS))   # a kernel-URL helper call as the fetch argument
# The content types a browser runs script from, compared with a route's type cut at its first `;`, stripped and lower-cased
# (_script_type): HTML; the XML types, whose XHTML-namespaced script runs (text/xml, application/xml, text/xsl and, by rule
# in _script_type, any type with a `+xml` suffix, image/svg+xml and application/xhtml+xml among them); and JavaScript under
# every name a browser takes for it. A route candidate of one of these types has its text read by the served pass.
SCRIPT_TYPES = ("text/html", "text/xml", "application/xml", "text/xsl", "application/xhtml+xml", "image/svg+xml",
                "text/javascript", "application/javascript", "application/ecmascript", "application/x-ecmascript", "application/x-javascript",
                "text/ecmascript", "text/javascript1.0", "text/javascript1.1", "text/javascript1.2", "text/javascript1.3", "text/javascript1.4",
                "text/javascript1.5", "text/jscript", "text/livescript", "text/x-ecmascript", "text/x-javascript")
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")                        # a URL scheme at the head of a literal
_PY_SLOT = re.compile(r"%[sdr(]|\{[A-Za-z_0-9]*\}")                         # a Python format slot inside a served page's literal


def _fetch_class(arg, served=False):
    """'local' (a relative literal, or a kernel-URL helper call), 'absolute' (a literal with a scheme or a host), or 'computed'
    (a variable, a template with an expression, or in a page the kernel serves a literal carrying a Python format slot, filled
    at serve time)."""
    if _HELPER_CALL.match(arg): return "local"
    if arg[:1] in ("'", '"', "`"):
        body = arg[1:arg.find(arg[0], 1)] if arg.find(arg[0], 1) > 0 else arg[1:]
        if body.startswith("//") or _SCHEME.match(body): return "absolute"
        if body.startswith("${") or (served and _PY_SLOT.search(body)): return "computed"
        return "local"
    return "computed"


_BODY_FIELDS = dict((t, f) for t, f in ((ast.FunctionDef, ("body",)), (ast.AsyncFunctionDef, ("body",)), (ast.ClassDef, ("body",)),
                                          (ast.If, ("body", "orelse")), (ast.For, ("body", "orelse")), (ast.AsyncFor, ("body", "orelse")),
                                          (ast.While, ("body", "orelse")), (ast.With, ("body",)), (ast.AsyncWith, ("body",)),
                                          (ast.Try, ("body", "handlers", "orelse", "finalbody")),
                                          (getattr(ast, "TryStar", None), ("body", "handlers", "orelse", "finalbody")),
                                          (ast.ExceptHandler, ("body",)), (ast.Match, ("cases",)), (ast.match_case, ("body",))) if t is not None)


def _statements(nodes):
    """The import statements of a body and of every body nested in it (a def's, a class's, a block's, an except clause's, a match
    case's), in order: an import is a statement, so this finds each one without walking an expression (_BODY_FIELDS, the fields
    that hold a body, by the statement's type)."""
    out, stack = [], list(reversed(nodes))
    while stack:
        s = stack.pop()
        if isinstance(s, (ast.Import, ast.ImportFrom)): out.append(s)
        for field in reversed(_BODY_FIELDS.get(type(s), ())): stack.extend(reversed(getattr(s, field)))
    return out


class Scan(ast.NodeVisitor):
    def __init__(self, rel, res):
        self.rel, self.res, self.stack, self.alias, self.consts, self.binds, self.imports = rel, res, [], {}, {}, [], []
        self.defs, self.routes = [], []   # the enclosing def nodes; the routes of a served page or script (routes_of, for served_texts)
        # the route candidates, each (call, its enclosing defs, "Class.function"): every `_send` call, every Content-Type header
        # written with send_header, every send_response; every other reference to `_send` (a read of it that is not a call's
        # function, a store or delete of an attribute so named, or a string equal to `_send`), each refused in routes_of; and the
        # module names written after their binding (Result.writes)
        self.sends, self.ctype_writes, self.responds, self.send_refs, self.send_funcs = [], [], [], [], set()
        self.globals, self.writes, self.rebinds = [set()], res.writes.setdefault(rel, {}), res.rebinds.setdefault(rel, {})
        self.global_decls = res.global_decls.setdefault(rel, [])
        self.inner_classes = []   # the class statements whose nearest enclosing def is a function, which _send_bindings counts (Scan.enter)
        # the route candidates (a `_send` call, a Content-Type write) standing in a lambda's body, the walk's depth of lambda bodies
        # counting them (visit_Lambda); routes_of refuses each, since a lambda's parameters are no scope the census reads
        self.in_lambda, self.lambdas = set(), 0
        self.setter_calls = []   # every call of setattr, delattr, `__setattr__` or `__delattr__`, by that name or as an attribute so named (routes_of's receiver proof: _stored_attrs)
        # what _namespace_flags reads, collected by the walk: the calls of globals or vars ns_listed reads with no argument, and
        # globals, vars, setattr or delattr as ns_listed reaches it read other than as a call's callee (ns_calls), the `__dict__`
        # attributes and the one-argument calls of vars (maps), the receivers of `.get(...)` calls (gets), the attribute stores and
        # deletes (stores), the calls of setattr and delattr ns_listed reads (setattrs), the assignments whose value may be a module,
        # whether the file names `__builtins__` as a name or imports the builtins module (`import builtins[.x]`, `from builtins[.x]
        # import ...` at any level, or `from X import builtins` or `from X import __builtins__`, any X at any level: visit_Import,
        # visit_ImportFrom),
        # whether a statement binds `__file__`, whether one binds staticmethod or classmethod (deco: in any scope and by any form, a star
        # import among them, which _Served._ctx reads for a route handler), each run-time form (runtime, each (line, column, the form): an import from the
        # file's own package (ns_own), a listed callable or attribute ns_listed reads or a call of one (arm ii), and a listed name
        # spelled as a string where a run-time lookup by name takes it (ns_string, arm iii)), the calls ns_listed reads as
        # __import__ or import_module (importers, which _namespace_flags's module() reads) and every call's callee node (callees),
        # and beside each run-time form the listed name behind it, None for any other form (rkinds, which _key_settle reads)
        self.ns_facts = {"ns_calls": [], "maps": [], "gets": set(), "stores": [], "setattrs": [], "assigns": [], "builtins": False, "file": False,
                         "deco": False, "runtime": [], "rkinds": [], "importers": set(), "callees": set(), "keyed": set(), "bnames": [], "bmaps": set()}
        parts = rel.split("/")   # the file's top package directory (none for a file at the root) and its own module name
        self.ns_top, self.ns_stem = parts[0] if len(parts) > 1 else None, os.path.basename(rel).rsplit(".", 1)[0]
        # the names an import anywhere in the file binds: to a listed name from its module (ns_from, name -> the listed name), to the
        # builtins module (ns_bmods: `import builtins [as X]`, `from X import builtins [as Y]`), and, for ns_string, to getattr,
        # setattr, delattr or hasattr (ns_getattrs), to operator's attrgetter or methodcaller (ns_ops: `from operator import
        # attrgetter [as Y]`) and to the operator module (ns_opmods: `import operator [as X]`, `from X import operator [as Y]`)
        self.ns_from, self.ns_bmods, self.ns_getattrs, self.ns_ops, self.ns_opmods = {}, set(), set(), {}, set()
        # arm iii's keys read by the allowlist (_key_form): the scopes around the walk's position, innermost last (a def's or a
        # class's whole statement, a lambda's body, a comprehension), the module's tree, each scope's bindings as _Served._locals and
        # _key_binds read them, computed once per scope a key's walk reads (id -> (the scope, its forms, its values), the node held
        # so its id is not reused), the keys held for the allowlist until the walk is done, each with its scopes (kdefer: _unfolded,
        # _key_settle), the names a key's acceptance read at module level or as a builtin (kheld), and the file's facts _key_const
        # and _key_attr read, gathered once (kindex: _key_index)
        self.kscopes, self.ktree, self.klocals, self.kdefer, self.kheld, self.kindex = [], None, {}, [], [], None
        # the served pass's follow proof (Result.fn_refs): the names the module's top-level def statements bind, each read of one other
        # than as a call's callee with the scopes around it (kscopes), and those a string constant spells
        self.fn_names, self.fn_uses, self.fn_strs = frozenset(), {}, set()
        # layer iv's module side (cflows): each change's depth below the name it reaches (cdepth, name -> depths: a store or delete
        # through it, a call that changes it in place or drops a method's return, a bound changer read off it, a setattr or delattr on
        # it), each name another name is bound to (cedges, root -> [(the bound name, the steps from the root's value to the bound
        # value)]), and the names whose value, or an item of it, is stored into another object, returned, yielded, handed as a default
        # or matched (cescapes); read at the walk's end (cflows) for the module containers the served pass and the route typing read
        self.cdepth, self.cedges, self.cescapes, self.cdropped = {}, {}, {}, set()   # cdropped: the calls a statement drops the return of
        self.cwrites = {}   # name -> the lines of the changes cwrite reads that reach it, besides the ones write records
    def visit_Module(self, n):   # the walk, then the routes read from its candidates
        self.ktree = n
        self.fn_names = frozenset(s.name for s in n.body if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)))
        for x in _statements(n.body):   # the imports ns_listed and ns_string read, in every scope, gathered before the walk reads any use of their names
            if isinstance(x, ast.ImportFrom):   # `from X import builtins [as Y]` or `from X import operator [as Y]`, any X at any level,
                # binds that module, as visit_ImportFrom counts the first as importing the builtins module
                self.ns_bmods.update(a.asname or a.name for a in x.names if a.name == "builtins")
                self.ns_opmods.update(a.asname or a.name for a in x.names if a.name == "operator")
            if isinstance(x, ast.ImportFrom) and not x.level:   # `from builtins import exec as e`: the name is the listed name itself
                self.ns_from.update((a.asname or a.name, a.name) for a in x.names if a.name in _LISTED_FROM.get(x.module or "", ()))
                self.ns_getattrs.update(a.asname or a.name for a in x.names if a.name in _GETATTRS)
                self.ns_ops.update((a.asname or a.name, a.name) for a in x.names if x.module == "operator" and a.name in ("attrgetter", "methodcaller"))
            elif isinstance(x, ast.Import):
                self.ns_bmods.update(a.asname or a.name for a in x.names if a.name == "builtins")
                self.ns_opmods.update(a.asname or a.name for a in x.names if a.name == "operator")
        self.generic_visit(n)
        self.cflows()   # layer iv's module side: a module container changed through a name bound to it, or escaping, is written
        self.res.changed[self.rel] = frozenset(self.cwrites)
        flags = _namespace_flags(self.ns_facts, self.ns_stem)   # read once: the forms below and _key_settle's add run-time forms alone
        for m in flags["nsuses"]: self.ns_runtime(m, _NS_USE, "nsmap")   # choice 13
        self._key_settle(flags)   # arm iii's held keys, read by the allowlist once every binding, declaration and write of the file is seen
        flags["runtime"] = min(self.ns_facts["runtime"])[2] if self.ns_facts["runtime"] else None   # the first form, as _namespace_flags reads it
        self.res.ns[self.rel] = flags
        self.res.fn_refs[self.rel] = (self.fn_uses, self.fn_strs)
        self.routes = routes_of(self.rel, n, self, self.res)
        cands = self.sends + self.ctype_writes + self.responds + self.send_refs   # the route candidates: _page_importers reads the first
        if cands: self.res.candidates[self.rel] = min(c[0].lineno for c in cands)
    def ns_bind(self, name):   # a binding of `__file__`, or of staticmethod or classmethod, in any scope and by any form (_namespace_flags)
        if name == "__file__": self.ns_facts["file"] = True
        elif name in ("staticmethod", "classmethod", "*"): self.ns_facts["deco"] = True   # a star import may bind either
    def ns_runtime(self, n, form, listed=None):   # a run-time form of _namespace_flags, with its line, and the listed name behind it
        self.ns_facts["runtime"].append((n.lineno, n.col_offset, "%s at line %d" % (form, n.lineno)))
        self.ns_facts["rkinds"].append(listed)
    def ns_own(self, node, module):   # arm i: an import from the file's own package: a relative import, an absolute one under its top
        # package directory (the file itself by that name among them), the file's own bare stem (its working absolute name when its
        # directory runs as a script, as kernel/ does), or __main__ (the file itself when it runs as a script). The import itself
        # may rewrite the file's module namespace at run time, whatever the code does with the name, so it is a run-time form: one
        # arm closes every write through such a name
        if module == "." or (self.ns_top and module.split(".")[0] == self.ns_top) or module.split(".")[0] == self.ns_stem or module == "__main__":
            self.ns_runtime(node, "imports from its own package")
    def ns_assign(self, targets, value):   # an assignment whose value may be a module, for _namespace_flags's aliases
        if isinstance(value, (ast.Subscript, ast.Call, ast.IfExp, ast.BoolOp, ast.Name)): self.ns_facts["assigns"].append((targets, value))
    def _builtins_recv(self, e):   # whether e is the builtins module, as ns_listed's third way reads a receiver: `__builtins__`, the
        # name `builtins` where no import binds it to another module, a name that `import builtins [as X]` or `from X import builtins
        # [as Y]` binds for any module X at any level (ns_bmods), `sys.modules["builtins"]` (or `.get("builtins")`, on any name or
        # attribute spelled `modules`), or a call ns_listed reads as __import__ or import_module whose first argument is "builtins"
        if self.dotted(e) in ("builtins", "__builtins__") or (isinstance(e, ast.Name) and e.id in self.ns_bmods): return True
        k = None
        if isinstance(e, ast.Subscript) and getattr(e.value, "attr", getattr(e.value, "id", None)) == "modules": k = e.slice
        elif isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "get" and getattr(e.func.value, "attr", getattr(e.func.value, "id", None)) == "modules": k = e.args[0] if e.args else None
        elif isinstance(e, ast.Call) and self.ns_listed(e.func) in ("__import__", "import_module"): k = e.args[0] if e.args else None
        return isinstance(k, ast.Constant) and k.value == "builtins"
    def ns_listed(self, e):   # arm ii, the one resolver: the listed callable (_RUNTIME_NAMES), computed-name writer (_NS_WRITERS) or
        # setter (_NS_SETTERS) e reaches (1) by its own name, in any context; (2) by a name an import binds to it (_LISTED_FROM:
        # `from builtins import exec as e`), in any context, the name read exactly as the listed name; (3) as an attribute of that
        # name on a builtins receiver (_builtins_recv), or on any receiver for exec, eval, locals, __import__, import_module and
        # _getframe (re.compile is live); else None. The fourth way, the name as a string where a run-time lookup takes it, is
        # ns_string's
        if isinstance(e, ast.Name): return e.id if e.id in _LISTED_NAMES else self.ns_from.get(e.id)
        if isinstance(e, ast.Attribute) and (e.attr in _RUNTIME_ATTR_CALLS or (e.attr in _BUILTINS_ATTRS and self._builtins_recv(e.value))): return e.attr
        return None
    def _const_str(self, e):   # the string a str constant or a constant join _Served._const_text folds to, else None (arm iii)
        c = _Served._const_text(e)
        return c[0] if c is not None and type(c[0]) is str else None
    def _unfolded(self, e):   # arm iii: why a lookup key is refused at once, else None. A join, format, format_map or replace called
        # on the name str, bytes or bytearray (_unbound_text_call), and a `%`, `.format` or `.format_map` of string constants
        # _const_text does not expand (a field wider than a million characters, _wide, or a format spec holding a replacement field,
        # _nested), each the direct key with its own form; a string constant key is left to ns_string's own listed-name test; any
        # other key is held for the allowlist (_key_form), which reads it once the file's walk is done (_key_settle), so a binding,
        # a declaration or a write later in the file counts as one earlier does
        if _unbound_text_call(e): return "spells a name by an unbound %s.%s" % (e.func.value.id, e.func.attr)
        if _Served._wide(e) or _Served._nested(e): return "spells a name by a format the census does not expand"
        if not isinstance(e, ast.Constant): self.kdefer.append((e, tuple(self.kscopes)))
        return None
    @staticmethod
    def _key_kind(x):   # the form a key may be that _const_text may not fold, named as a reason names it, else None (_key_form)
        if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and x.func.attr in ("join", "format", "format_map", "replace"): return "a " + x.func.attr
        if isinstance(x, ast.BinOp) and isinstance(x.op, (ast.Mod, ast.Add)): return "a %" if isinstance(x.op, ast.Mod) else "a +"
        return "an f-string" if isinstance(x, ast.JoinedStr) else None
    @staticmethod
    def _key_words(x):   # a node kind the allowlist does not accept where it stands, in words for its reason, never the syntax tree's name for it
        ops = {ast.Sub: "-", ast.Mult: "*", ast.Div: "/", ast.FloorDiv: "//", ast.Pow: "**", ast.LShift: "<<", ast.RShift: ">>",
               ast.BitOr: "|", ast.BitXor: "^", ast.BitAnd: "&", ast.MatMult: "@"}
        if isinstance(x, ast.BinOp): return "a " + ops.get(type(x.op), "binary operation")
        if isinstance(x, ast.UnaryOp): return {ast.Not: "a not", ast.USub: "a unary -", ast.UAdd: "a unary +", ast.Invert: "a ~"}.get(type(x.op), "a unary operation")
        kinds = ((ast.Lambda, "a lambda"), (ast.ListComp, "a list comprehension"), (ast.SetComp, "a set comprehension"),
                 (ast.DictComp, "a dict comprehension"), (ast.GeneratorExp, "a generator expression"), (ast.Await, "an await"),
                 (ast.Yield, "a yield"), (ast.YieldFrom, "a yield from"), (ast.Compare, "a comparison"), (ast.Slice, "a slice"),
                 (ast.FormattedValue, "an f-string's field"), (ast.Starred, "a starred value"), (ast.Tuple, "a tuple"),
                 (ast.List, "a list"), (ast.Set, "a set"), (ast.Dict, "a dict"), (ast.Call, "a call"), (ast.Name, "a name"),
                 (ast.NamedExpr, "a walrus"),
                 (ast.Attribute, "an attribute"), (ast.Subscript, "a subscript"), (getattr(ast, "TemplateStr", ()), "a template string"),
                 (getattr(ast, "Interpolation", ()), "a template string's field"))
        return next((w for k, w in kinds if k and isinstance(x, k)), "an expression")
    def _key_form(self, key, chain):
        """Why a lookup key is refused, or None where it is accepted: a POSITIVE ALLOWLIST. A key is accepted only in a shape
        proven by construction, and every other shape refuses, the reason naming in words what the walk met. Accepted:
        (1) constant text (a string constant, or constants _const_text folds to one) that spells no listed name (_STRING_NAMES),
        as the key itself or as a leaf of a loop's literal source (3); a direct key that spells one is left to ns_string's own
        test ("spells <name> as a string"), and constant text reached any other way refuses;
        (2) the stated remainders, each keyed by binding: a parameter whose default, if any, holds constants alone spelling no listed
        name, a tuple or list of them among them (read with the loop literal's leaf test: extra9-3 of the eleventh round's review, so a
        default spelling a listed name refuses as the literal's leaf does, and any other default refuses by name); a call's return whose
        callee reaches by binding neither text
        nor the str, bytes or bytearray type nor any of their methods (the callee a name bound by a def statement, an import, a
        parameter or no statement at all as a builtin other than those three, or an attribute, other than one so named, of a value
        that reaches no text; a name bound to one of those by an assignment is read through); and a name bound to a parameter or
        such a call's return by an assignment or an annotated assignment, or as an unpacking target over one;
        (3) a name that is a loop or comprehension target, inside a function, over a literal (a tuple, list or set literal, nested
        tuple and list literals among its elements, or a dict literal's keys) whose every leaf is constant text as in (1) or another
        constant, over a module constant bound once to a tuple literal of such constants, nested tuple literals among them, which no
        code can mutate (_key_const decides it: the file never binds, declares, names or writes that constant any other way), over the
        one attribute source kernel/host_transport.py holds (the live key at kernel/host_transport.py:1116, sh.SPEC_FIELDS): keyed by
        binding on the file, the attribute name and the base bound once at module level (_spec_source; any other attribute source
        refuses by name, so a new one enters only by an allowlist edit), whose base reaches no text and for which the file writes no
        attribute of that name (_key_attr decides that by the facts _key_const reads, keyed on the attribute's name on any receiver:
        the file binds and declares no such name, uses an attribute so named only as such a source or an item read, spells the name in
        no string constant, constants _const_text folds to it, or keyword, reaches a setter only by a call each of whose arguments
        that may name an attribute folds to string constants other than that name, directly or as a loop or comprehension target
        over a literal of them, the setter read
        failing closed on any other shape (_setter_sites, _setter_args, _setter_fold), and names no globals, vars, locals or
        `__dict__` and holds no star import), or over a parameter or such a
        call's return, directly or through a name an assignment, such a target or an unpacking binds to one; a module-level loop
        target refuses;
        a boolean operation or an if-expression is accepted where each of its values is, and a name an assignment binds to any
        accepted shape but constant text is read through. A name read at module level
        or as a builtin assumes the file may not rewrite its module namespace (_key_settle checks it). Refused, each by name: a
        join, format, format_map or replace call, a `%`, a `+` or an f-string _const_text does not fold ("... the census does
        not fold", _key_kind); a method of the name str, bytes or bytearray, however reached; any method called on, or attribute
        read on, constant text, a literal container or anything else that is not proven to reach no text; a direct attribute key or a
        name bound to one, any attribute source but that one binding (_spec_source), and that binding where the file may write its
        attribute (_key_attr), a setter whose name the census cannot fold, or one the file reaches other than by a call of its name,
        counting as such a write; a name bound to a constant string; a with
        target, or a name bound to one (its `__enter__` call's return is no shape the allowlist proves); a walrus, and a name a
        walrus binds, in any scope, a comprehension's included (a walrus in a comprehension binds the enclosing scope's name to a
        value the comprehension's own scope computes, so no binding of a walrus target is read in an enclosing scope); a loop
        target bound at module level; a subscript; a call of a
        class the file defines, a lambda, a call's return or anything but a name or an attribute; an augmented assignment; a
        name any function or class body declares global, or a scope of the file declares nonlocal; a name a class body binds; a
        name bound by a del, a match pattern or any other store; a list, set or dict module constant; and any other node kind,
        named in words ("a lambda the census does not evaluate"). From the key, read in the scopes `chain` (Scan.kscopes where
        the key stands). Walked iteratively: an explicit worklist and one visited set per query, keyed on the binding's scope, the
        name and the context (the key itself, a loop's source, an opaque value's items, a literal source's leaf, a receiver or a
        callee), so each name expands once per context, in _key_step; there is no depth bound."""
        if self._const_str(key) is not None: return None   # a direct key that is constant text: ns_string's own test reads its listed name

        def why(node, tail):   # the reason for a form the walk refuses, the entry key named where the form is not the key itself
            if node is key: return "spells a name by %s" % tail
            return "spells a name by %s, %s %s" % (ast.unparse(key)[:40], "bound to" if isinstance(key, ast.Name) else "which holds", tail)
        seen, todo = set(), [(key, tuple(chain), "key")]
        while todo:   # the context: "key" the key itself, "src" a loop's source, "rem" a value whose items are opaque, "lit" and
            # "tlit" a literal source's leaves (tlit a module constant's, tuples alone nested), "callee", ("nt", the tail for constant
            # text there, the attribute read on it) a receiver
            x, chain, ctx = todo.pop()
            nt = type(ctx) is tuple
            text = self._const_str(x)
            if ctx in ("lit", "tlit", "dflt"):   # a literal source's leaves (dflt a parameter's default): constants, and tuple (and for lit and dflt list) literals of them
                if text is not None or isinstance(x, ast.Constant):
                    if text in _STRING_NAMES: return "spells %s as a string" % text
                    continue
                where = "a parameter's default" if ctx == "dflt" else "a loop's literal source"
                if isinstance(x, ast.Tuple) or ctx in ("lit", "dflt") and isinstance(x, ast.List):
                    for v in reversed(x.elts):
                        if isinstance(v, ast.Starred): return why(v, "a starred element in %s the census does not evaluate" % where)
                        todo.append((v, chain, ctx))
                    continue
                kind = self._key_kind(x)
                if kind is not None: return why(x, "%s the census does not fold" % kind)
                return why(x, "%s in %s the census does not evaluate" % (self._key_words(x), where))
            if text is not None or isinstance(x, ast.Constant):
                if nt: return why(x, ctx[1])
                if text in _STRING_NAMES: return "spells %s as a string" % text
                return why(x, "constant text outside a loop's literal source")
            if _unbound_text_call(x): return why(x, "an unbound %s.%s the census does not fold" % (x.func.value.id, x.func.attr))
            if _Served._wide(x) or _Served._nested(x): return why(x, "a format the census does not expand")
            kind = self._key_kind(x)
            if kind is not None: return why(x, "%s the census does not fold" % kind)
            if isinstance(x, ast.IfExp): todo += [(x.orelse, chain, ctx), (x.body, chain, ctx)]; continue
            if isinstance(x, ast.BoolOp): todo += [(v, chain, ctx) for v in reversed(x.values)]; continue
            if isinstance(x, ast.Subscript): return why(x, "a subscript the census does not evaluate")
            if isinstance(x, ast.Call):   # a call's return: the stated remainder where its callee is proven
                if ctx == "callee": return why(x, "a call of a call's return the census does not evaluate")
                f = x.func
                if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in _TEXT_TYPES:   # `str.lower(v)`, by its spelling
                    return why(x, "an unbound %s.%s the census does not fold" % (f.value.id, f.attr))
                todo.append((f, chain, "callee")); continue
            if isinstance(x, ast.Attribute):
                if ctx == "callee" or nt:
                    if x.attr in _TEXT_TYPES: return why(x, "the %s type reached as an attribute, which the census does not fold" % x.attr)
                    tail = "a .%s() call on constant text the census does not fold" % x.attr if ctx == "callee" else ctx[1]
                    todo.append((x.value, chain, ("nt", tail, x.attr) if not nt else ctx)); continue
                if ctx == "src":   # an attribute as a loop or comprehension source: the live key at kernel/host_transport.py:1116, sh.SPEC_FIELDS
                    shut = self._key_attr(x.attr)   # for that one binding the honest writes stay refused (the facts _key_const reads for a module constant)
                    if shut: return why(x, _KEY_ATTR % (x.attr, shut))
                    if not self._spec_source(x, chain):   # NARROWED to the one live binding: any other attribute source refuses by name, so a new one enters only by an allowlist edit
                        return why(x, _KEY_SRC % x.attr)
                    todo.append((x.value, chain, ("nt", "an attribute .%s of constant text the census does not evaluate" % x.attr, x.attr))); continue
                return why(x, "an attribute .%s the census does not evaluate, accepted only as a loop or comprehension source" % x.attr)
            if isinstance(x, (ast.Tuple, ast.List, ast.Set, ast.Dict)) and ctx == "src":   # a loop's literal source
                if isinstance(x, ast.Dict):
                    if any(k is None for k in x.keys): return why(x, "a ** mapping in a loop's literal source the census does not evaluate")
                    todo += [(k, chain, "lit") for k in reversed(x.keys)]; continue
                for v in reversed(x.elts):
                    if isinstance(v, ast.Starred): return why(v, "a starred element in a loop's literal source the census does not evaluate")
                    todo.append((v, chain, "lit"))
                continue
            if isinstance(x, ast.Name):
                got = self._key_binding(x, chain, ctx)
                if got[0] == "refuse": return "spells a name by %s, %s" % (x.id, got[1])
                if (got[0], x.id, ctx) in seen: continue
                seen.add((got[0], x.id, ctx))
                for item in self._key_step(got[1]):
                    how = item[0]
                    if how == "param":   # a parameter: the stated remainder, in every context, its default, if any, read with the loop
                        # literal's leaf test (extra9-3 of the eleventh round's review: a default spelling a listed name refuses)
                        if item[1] is not None: todo.append((item[1], chain, "dflt"))
                        continue
                    if how in ("import", "def", "builtin"):
                        if item[1] in _TEXT_TYPES and (nt or ctx == "callee"):   # the str, bytes or bytearray type itself, by binding
                            return why(x, "an unbound %s.%s the census does not fold" % (item[1], ctx[2]) if nt else "a call of %s the census does not fold" % item[1])
                        if not (ctx == "callee" or nt and how == "import"): return "spells a name by %s, %s" % (x.id, _KEY_BOUND[how])
                        if got[2]: self.kheld.append((x.id, how))
                        continue
                    if how in ("class", "except", "with", "walrus"): return "spells a name by %s, %s" % (x.id, _KEY_BOUND[how])
                    if how == "const":   # a module constant bound once to a tuple literal, read as a loop's source
                        shut = self._key_const(x.id)
                        if shut: return "spells a name by %s, %s" % (x.id, shut)
                        self.kheld.append((x.id, "module"))
                        todo.append((item[1], (), "tlit")); continue
                    if how == "mutable": return "spells a name by %s, %s" % (x.id, _KEY_BOUND[how])
                    v, vch, d = item[1], item[2], item[3]
                    if got[2]: self.kheld.append((x.id, "module"))
                    if how in ("for", "comp"):
                        if got[2]: return "spells a name by %s, %s" % (x.id, "a loop target bound at module level, which the census does not evaluate")
                        todo.append((v, vch, "src" if ctx == "key" else "rem"))
                    elif d: todo.append((v, vch, "rem"))   # an unpacking target: an element of an opaque value
                    else: todo.append((v, vch, "rem" if ctx == "src" else ctx))
                continue
            return why(x, "%s the census does not evaluate" % self._key_words(x))   # any other node kind, or a literal where the allowlist takes none
        return None
    def _key_step(self, vals):   # _key_form's expansion of one name, which it calls once for each name it expands in a context,
        # given the items of the name's binding (_key_binding): the items to read, in their order
        return list(vals)
    @staticmethod
    def _key_targets(t):   # (name, the subscripts that take a target's source to it) for each name a target binds: one for each
        # tuple or list level it stands in, a starred name the level of the tuple or list that holds it (_key_binds, _key_binding);
        # a name inside an attribute's base or a subscript's container or index is read, not bound, and is not here. The one reader
        # of a target's names: _Served._locals, resolve's comprehension arm and _binding_forms take them here too
        out, todo = [], [(t, 0)]
        while todo:
            n, k = todo.pop()
            if isinstance(n, ast.Name): out.append((n.id, k))
            elif isinstance(n, (ast.Tuple, ast.List)): todo += [(e.value, k) if isinstance(e, ast.Starred) else (e, k + 1) for e in n.elts]
            elif isinstance(n, ast.Starred): todo.append((n.value, k))
        return out
    @staticmethod
    def _key_binds(fn):
        """name -> [(the form, the value, the unpacking level)] for the values the scope fn's own body binds to each name, by form:
        "assign" for a single-name, chained or annotated assignment's value, and for an element an assignment's tuple or list
        literal of the target's own length (no starred element on either side) binds element by element; "unpack" for any other
        unpacking target's value (its level one or more); "for" for a loop target's source (its level one, and one more for each
        unpacking level); "with" for a with target's context expression; "walrus" for a walrus's value, a walrus inside a
        comprehension among them, which binds this scope's name (the allowlist refuses both of the last two forms: _key_form).
        Traversed as _Served._locals traverses: nested defs, classes and lambdas are not entered, their headers read as this
        body's statements (_header)."""
        out, stack = {}, list(fn.body) if isinstance(fn.body, list) else [fn.body]

        def bind(t, v, form, base, pair):
            todo = [(t, v)]
            while todo:
                t, v = todo.pop()
                if (pair and isinstance(t, (ast.Tuple, ast.List)) and isinstance(v, (ast.Tuple, ast.List)) and len(t.elts) == len(v.elts)
                        and not any(isinstance(e, ast.Starred) for e in t.elts + v.elts)):
                    todo += zip(t.elts, v.elts); continue
                for name, k in Scan._key_targets(t):
                    out.setdefault(name, []).append(("unpack" if form == "assign" and k else form, v, base + k))
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)): stack.extend(_header(n)); continue
            if isinstance(n, ast.Assign):
                for tg in n.targets: bind(tg, n.value, "assign", 0, True)
            elif isinstance(n, ast.AnnAssign) and n.value is not None: bind(n.target, n.value, "assign", 0, False)
            elif isinstance(n, (ast.For, ast.AsyncFor)): bind(n.target, n.iter, "for", 1, False)
            elif isinstance(n, (ast.With, ast.AsyncWith)):
                for it in n.items:
                    if it.optional_vars is not None: bind(it.optional_vars, it.context_expr, "with", 0, False)
            elif isinstance(n, ast.NamedExpr): bind(n.target, n.value, "walrus", 0, False)
            stack.extend(ast.iter_child_nodes(n))
        return out
    def _key_scope(self, s):   # (_Served._locals, _key_binds) over the scope s (a def, a class body or the module), computed once per scope
        got = self.klocals.get(id(s))
        if got is None: got = self.klocals[id(s)] = (s, _Served._locals(s), self._key_binds(s))
        return got[1][3], got[2]
    def _key_binding(self, x, chain, ctx):
        """How the allowlist reads the name `x` in the scopes `chain` (innermost last), in the context ctx: ("refuse", the tail of a
        reason); or (the binding's scope, its items, whether the scope is the module) where each item is ("param", its default or
        None), ("import",
        the type it binds from builtins or None), ("def", None), ("class",), ("except",), ("builtin", its name) for a builtin no
        statement binds, ("const", the tuple literal) for a module constant bound once to a tuple literal read as a loop's source
        (ctx "src"), ("mutable",) for one bound once to a list, set or dict literal so read, or (a form of _key_binds or "comp", the
        value, the scopes it is read in, its unpacking level). From the innermost scope out, as Python resolves the name: a
        comprehension whose target binds it (read anywhere in it but its first source, which runs in the enclosing scope) gives
        the sources of the generators whose targets bind it; a lambda's body gives ("param", its default) for its parameter and refuses a
        walrus's name; a class body refuses a name it binds (the class body is not a scope of the scopes nested in it); a def's
        body (the key in it, not in its header, which runs in the enclosing scope) refuses an augmented assignment, a nonlocal
        declaration of the name in the def or in a def or class nested in it and a del, match or other store, breaks to the module
        on the def's own `global` declaration, and gives its parameter and its other bindings; and past every scope, the module:
        a name any function or class body of the file declares global refuses, wherever the declaration stands; else the
        module's bindings, or, where no statement binds it, a builtin (not a name the import system binds in every module). A def's
        body or the module that binds the name in a form that gives no item refuses (_KEY_BOUND["novalue"]), so no key is accepted
        through a binding it read nothing of (correctness-1 of the eleventh round's review: a name only read in a loop or with
        target took a value form with no item, and the empty scope was accepted). That refusal is dominated: a name the scope
        binds as a parameter, by an import, a def, a class or an except clause takes one item for that form, and a name with the
        form "value" one item for each of its bindings, since _Served._locals and _key_binds take a target's names with the one
        reader, Scan._key_targets, and both read the same assignments, annotated assignments, loops, with statements and walruses;
        every other form refuses above (or, a `global` declaration in a def, hands the name to the module), and "comp" is no form
        of these scopes here. So it fires only where the two readers disagree; the census module pins it by handing it such a
        scope."""
        at, name, passed, i = (x.lineno, x.col_offset), x.id, False, len(chain) - 1

        def default(a):   # the default of the parameter `name` of the arguments a, or None (extra9-3: read with the loop literal's leaf test)
            pos = a.posonlyargs + a.args
            got = dict(zip([x.arg for x in pos[len(pos) - len(a.defaults):]], a.defaults))
            got.update((x.arg, d) for x, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None)
            return got.get(name)

        def items(f, binds, sch):
            out = [("param", default(chain[i].args))] if "param" in f else []
            for how in ("import", "def", "class", "except"):
                if how in f: out.append((how, self.alias.get(name, "").partition("builtins.")[2] or None) if how == "import" else (how, None) if how == "def" else (how,))
            return out + [(fm, v, sch, d) for fm, v, d in binds.get(name, ())]
        while i >= 0:
            s = chain[i]
            if isinstance(s, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)):
                first = s.generators[0].iter
                if not (first.lineno, first.col_offset) <= at < (first.end_lineno, first.end_col_offset):
                    srcs = [("comp", g.iter, chain[:i] if g is s.generators[0] else chain[:i + 1], 1 + k) for g in s.generators
                            for t, k in self._key_targets(g.target) if t == name]
                    if srcs: return id(s), srcs, False
                    passed = True
            elif isinstance(s, ast.Lambda):
                a = s.args
                if any(isinstance(n, ast.NamedExpr) and n.target.id == name for n in ast.walk(s.body)):
                    return "refuse", _KEY_BOUND["lambda"]
                if name in {p.arg for p in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if p is not None}: return id(s), [("param", default(a))], False
                passed = True
            elif isinstance(s, ast.ClassDef) and passed: pass
            elif at >= (s.body[0].lineno, s.body[0].col_offset):   # in the body of a def or a class, not in its header
                if isinstance(s, ast.ClassDef):
                    if name in self._key_scope(s)[0]: return "refuse", _KEY_BOUND["classbody"]
                else:
                    a = s.args
                    f = set(self._key_scope(s)[0].get(name, ())) - {"comp"}
                    if name in {p.arg for p in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if p is not None}: f.add("param")
                    if f:
                        if "global" in f: break
                        if "nonlocal" in f: return "refuse", _KEY_BOUND["nonlocal"]
                        if "aug" in f: return "refuse", _KEY_BOUND["aug"]
                        if f & {"del", "match", "store"}: return "refuse", _KEY_BOUND["store"]
                        got = items(f, self._key_scope(s)[1], chain[:i + 1])
                        if not got: return "refuse", _KEY_BOUND["novalue"]   # a binding scope that yields no item fails closed
                        return id(s), got, False
                passed = True
            i -= 1
        if any(name in names for _, names in self.global_decls): return "refuse", _KEY_BOUND["global"]
        f, binds = self._key_scope(self.ktree)
        f = set(f.get(name, ())) - {"comp"}
        if "aug" in f: return "refuse", _KEY_BOUND["aug"]
        if f & {"del", "match", "store", "nonlocal", "global"}: return "refuse", _KEY_BOUND["store"]
        if f:
            got = items(f, binds, ())
            if not got: return "refuse", _KEY_BOUND["novalue"]   # a binding scope that yields no item fails closed
            if ctx == "src" and len(got) == 1 and got[0][0] == "assign" and not got[0][3] and any(
                    isinstance(st, ast.Assign) and st.value is got[0][1] and len(st.targets) == 1 for st in self.ktree.body):
                v = got[0][1]
                if isinstance(v, ast.Tuple): return id(self.ktree), [("const", v)], True
                if isinstance(v, (ast.List, ast.Set, ast.Dict)): return id(self.ktree), [("mutable",)], True
            return id(self.ktree), got, True
        if name not in _IMPORT_NAMES and hasattr(builtins, name): return id(self.ktree), [("builtin", name)], True
        return "refuse", _KEY_BOUND["none"]
    @staticmethod
    def _setter_sites(tree):
        """The setter read's population, by one iterative walk of the file's tree: (each call of setattr, delattr, `__setattr__`
        or `__delattr__`, by that name or as an attribute so named, with the scopes around it as Scan.kscopes holds them where the
        walk stands, innermost last: a def's or a class's whole statement, a lambda's body, a comprehension; whether the file
        reaches one of the four in one of the three other ways the walk reads: the name, or an attribute so named, anywhere but as
        a call's callee (an alias, an argument, a rebinding), an import of one under another name, or a string constant, or
        constants _const_text folds, that spells one; a setter reached reflectively other than by such a string is none of these,
        named under the class limit). _key_index reads it (the fact sopen), and so does _Served._setters_open."""
        calls, loose, todo = [], False, [(tree, ())]
        scopes = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
        while todo:
            n, chain = todo.pop()
            if isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) in _SETTERS: calls.append((n, chain))
            if isinstance(n, ast.alias) and n.name.rsplit(".", 1)[-1] in _SETTERS and n.asname not in (None, n.name): loose = True
            if isinstance(n, (ast.Constant, ast.BinOp, ast.JoinedStr, ast.Call)):
                c = _Served._const_text(n)
                if c is not None and c[0] in _SETTERS: loose = True
            inner = chain + (n,) if isinstance(n, scopes) else chain
            for c in ast.iter_child_nodes(n):
                if ((isinstance(c, ast.Name) and c.id in _SETTERS or isinstance(c, ast.Attribute) and c.attr in _SETTERS)
                        and not (isinstance(n, ast.Call) and n.func is c)): loose = True
                todo.append((c, chain + (n,) if isinstance(n, ast.Lambda) and c is n.body else inner))
        return calls, loose
    @staticmethod
    def _setter_args(call):
        """The arguments of a setter call that may name the attribute it sets or deletes: a setattr's or delattr's second, called
        by its bare name; the first two of any other (a bound `x.__setattr__(name, v)` names it first, an unbound
        `object.__setattr__(x, name, v)` second, and the spelling does not say which). None where the call's shape does not say
        (a starred argument, a keyword, too few arguments): _key_index then counts the call's name as unprovable."""
        if call.keywords or any(isinstance(a, ast.Starred) for a in call.args): return None
        if isinstance(call.func, ast.Name) and call.func.id in ("setattr", "delattr"): return call.args[1:2] if len(call.args) > 1 else None
        return call.args[:2] or None
    def _setter_fold(self, a, chain):
        """The set of strings the setter argument `a`, read in the scopes `chain`, may be, or None where the census cannot prove
        it by construction: a string constant, or constants _const_text folds to one; or a name bound, in the scope Python
        resolves it in (_key_binding, keyed on the binding and never on the spelling), only as the target of a for loop in a
        function's own body or of a comprehension, never unpacked, over a tuple, list or set literal each of whose elements is a
        string constant or constants _const_text folds to one. Every other shape is None: a literal holding any other element (a mixed literal, a nested one, a starred one), a dict
        or a dict's comprehension, a name bound at module level or in a class body, or bound any other way besides (a parameter,
        an assignment, an unpacking target), a call's return, a join or format the census does not fold, and any other node."""
        c = _Served._const_text(a)
        if c is not None: return {c[0]} if type(c[0]) is str else None
        if not isinstance(a, ast.Name): return None
        got = self._key_binding(a, chain, "key")
        if got[0] == "refuse" or got[2]: return None
        out = set()
        for item in got[1]:
            if item[0] not in ("for", "comp") or item[3] != 1 or not isinstance(item[1], (ast.Tuple, ast.List, ast.Set)): return None
            for e in item[1].elts:
                c = _Served._const_text(e)
                if c is None or type(c[0]) is not str: return None
                out.add(c[0])
        return out
    def _key_index(self):
        """The file's facts _key_const and _key_attr read, gathered once per file by one walk of its whole tree: how many times each
        name is bound, in any scope and by any form (a store or delete, a parameter, a def or class statement, an import, an except
        name, a match capture, a type parameter), the names any function or class body declares global or nonlocal, each name's
        loads with the node holding them, every attribute name, and each attribute node, in any context, with the node holding it,
        every string the file spells, as a string constant or as constants _const_text folds to one (a `+`, a `%`, an f-string, a
        `.join`, `.format`, `.format_map` or `.replace` of them: the string fact, so a name handed as folded constants to any writer,
        functools.update_wrapper's assigned= or an item store into a `__dict__` among them, is read as that name; extra11-3 of the
        eleventh round's review, choice 6 of the eleventh round's rulings), every keyword argument's name, whether a call of setattr, delattr,
        `__setattr__` or `__delattr__` (by that name or as an attribute so named) names its attribute other than by a string constant,
        whether the file names globals, vars or locals (as a name or an attribute) or an attribute `__dict__`, and whether it holds a
        star import. And the setter read, which fails closed (_setter_sites, _setter_args, _setter_fold): whether any argument of a
        setter call that may name its attribute is one whose strings the fold cannot prove, or the file uses a setter's name, or an
        attribute so named, other than as a call's callee, imports one under another name or spells one in folded constants (sopen),
        which _key_attr refuses. A setter's name the read proves needs no set of its own: each string it proves is a constant or a
        fold of constants that stands in the tree (the argument itself, or an element of the literal a loop or comprehension target
        iterates), so the string fact holds it already."""
        if self.kindex is None:
            binds, decl, loads, attrs, strs, kws, auses = {}, set(), {}, set(), set(), set(), {}

            def bound(name): binds[name] = binds.get(name, 0) + 1
            setter = ns = star = False
            for n in ast.walk(self.ktree):
                for c in ast.iter_child_nodes(n):
                    if isinstance(c, ast.Name) and isinstance(c.ctx, ast.Load): loads.setdefault(c.id, []).append((c, n))
                    elif isinstance(c, ast.Attribute): auses.setdefault(c.attr, []).append((c, n))
                if isinstance(n, ast.Name) and not isinstance(n.ctx, ast.Load): bound(n.id)
                elif isinstance(n, ast.arg): bound(n.arg)
                elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): bound(n.name)
                elif isinstance(n, ast.alias):
                    bound((n.asname or n.name).split(".")[0])
                    star = star or n.name == "*"
                elif isinstance(n, ast.ExceptHandler) and n.name: bound(n.name)
                elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name: bound(n.name)
                elif isinstance(n, ast.MatchMapping) and n.rest: bound(n.rest)
                elif isinstance(n, (ast.Global, ast.Nonlocal)): decl.update(n.names)
                elif type(n).__name__ in ("TypeVar", "ParamSpec", "TypeVarTuple", "TypeAlias"):
                    nm = getattr(n, "name", None)
                    if isinstance(nm, str): bound(nm)
                if isinstance(n, ast.Attribute):
                    attrs.add(n.attr)
                    ns = ns or n.attr in ("globals", "vars", "locals", "__dict__")
                elif isinstance(n, ast.Name): ns = ns or n.id in ("globals", "vars", "locals")
                elif isinstance(n, ast.Constant) and type(n.value) is str: strs.add(n.value)
                elif isinstance(n, ast.keyword) and n.arg: kws.add(n.arg)
                elif isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) in _SETTERS:
                    setter = setter or not any(isinstance(a, ast.Constant) and type(a.value) is str for a in n.args[:2])
                if isinstance(n, (ast.BinOp, ast.JoinedStr, ast.Call)):   # the string fact over folded constants (`"SPEC" + "_FIELDS"`)
                    c = _Served._const_text(n)
                    if c is not None and type(c[0]) is str: strs.add(c[0])
            calls, sopen = self._setter_sites(self.ktree)   # the setter read: every setter's name folded by binding, or unprovable
            for call, chain in calls:
                for a in self._setter_args(call) or [None]:
                    if a is None or self._setter_fold(a, chain) is None: sopen = True
            self.kindex = {"binds": binds, "decl": decl, "loads": loads, "attrs": attrs, "strs": strs, "kws": kws, "setter": setter, "ns": ns,
                           "star": star, "auses": auses, "sopen": sopen}
        return self.kindex
    def _key_const(self, name):
        """Why the allowlist may not read the module constant `name` (bound once, at the module's top level, to a tuple literal)
        as a loop's literal source, else None: the file binds it more than once in any scope or by any form, declares it global or
        nonlocal anywhere, uses it other than as a loop or comprehension source or an item read's container, names it as an
        attribute on any receiver (a write through the module object), spells it as a string constant (through globals(), vars(),
        setattr or a namespace mapping) or as a keyword argument, calls setattr, delattr, `__setattr__` or `__delattr__` with an
        attribute name that is no string constant, names globals, vars, locals or `__dict__`, or holds a star import
        (_key_index). A tuple no code can mutate, so these are every way the file may change what the name holds; _key_settle
        then refuses it in a file that may rewrite its module namespace."""
        ix = self._key_index()
        if ix["binds"].get(name, 0) != 1: return _KEY_CONST % "the file binds more than once"
        if name in ix["decl"]: return _KEY_CONST % "a scope of the file declares global or nonlocal"
        for c, p in ix["loads"].get(name, ()):
            if not ((isinstance(p, (ast.For, ast.AsyncFor, ast.comprehension)) and p.iter is c) or (isinstance(p, ast.Subscript) and p.value is c)):
                return _KEY_CONST % "the file uses other than as a loop's source or an item read"
        if name in ix["attrs"]: return _KEY_CONST % "the file names as an attribute, which may write it through the module object"
        if name in ix["strs"] or name in ix["kws"]: return _KEY_CONST % "the file spells as a string or a keyword, which may write it through a namespace"
        if ix["setter"]: return _KEY_CONST % "in a file that calls setattr, delattr, __setattr__ or __delattr__ with a name no string constant spells"
        if ix["ns"]: return _KEY_CONST % "in a file that names globals, vars, locals or __dict__"
        if ix["star"]: return _KEY_CONST % "in a file that holds a star import"
        return None
    def _key_attr(self, name):
        """Why the allowlist may not read an attribute named `name` as a loop's or a comprehension's source, else None: the file
        facts _key_const reads for a module constant (_key_index), keyed on the attribute's name on any receiver, since the base may
        be reached through any binding. The file binds the name in any scope or by any form (a class body's or the module's binding
        sets it on a class or a module a base may reach), declares it global or nonlocal anywhere, uses an attribute so named other
        than as a loop or comprehension source or an item read's container (an attribute store or delete, an augmented assignment,
        a method called on it, an item or slice store, an alias and a callee handed it among them), spells the name as a string
        constant, as constants _const_text folds to it (a setter's name, a loop or comprehension target's literal,
        functools.update_wrapper's assigned= or an item store into a `__dict__`, each wherever it stands: the string fact) or as a
        keyword argument, names globals, vars, locals or `__dict__`, or holds a star import. The setter read fails closed (sopen): the
        attribute refuses in a file where any call of setattr, delattr, `__setattr__` or `__delattr__` has an argument that may name
        the attribute (_setter_args) whose strings _setter_fold cannot prove (a mixed literal, a dict, a parameter, a call's return
        and an unfolded join among them), or that uses one of the four's names, or an attribute so named, other than as a call's
        callee, imports one under another name, or spells one in a string constant or constants _const_text folds (_setter_sites).
        Not read for it: a write in another file, outside the check, since the served sentence scopes the check to this file; and,
        named under the class limit, a setter reached reflectively other than by such a string, and a writer other than the four
        handed the name other than as a string constant or constants _const_text folds to it (a name built by chr, say). The live
        setter at kernel/host_transport.py:287, `setattr(self, name, None)` with `name` a loop target over ("hosts", "dir"),
        folds to those names, not SPEC_FIELDS, so the one accepted source (Scan._spec_source) stays accepted."""
        ix = self._key_index()
        if ix["binds"].get(name, 0): return "whose name the file binds, which may set it on a class or a module a base reaches"
        if name in ix["decl"]: return "whose name a scope of the file declares global or nonlocal"
        for c, p in ix["auses"].get(name, ()):
            if not (isinstance(c.ctx, ast.Load) and ((isinstance(p, (ast.For, ast.AsyncFor, ast.comprehension)) and p.iter is c)
                                                     or (isinstance(p, ast.Subscript) and p.value is c and isinstance(p.ctx, ast.Load)))):
                return "that the file writes or uses other than as a loop's source or an item read"
        if name in ix["strs"] or name in ix["kws"]:
            return "whose name the file spells as a string or a keyword, which may write it through setattr or a namespace"
        if ix["sopen"]: return "in a file that reaches setattr, delattr, __setattr__ or __delattr__ other than by a call whose name the census folds to constant strings"
        if ix["ns"]: return "in a file that names globals, vars, locals or __dict__"
        if ix["star"]: return "in a file that holds a star import"
        return None
    def _spec_source(self, x, chain):
        """Whether the loop- or comprehension-source attribute `x` is the one the allowlist accepts: kernel/host_transport.py's
        sh.SPEC_FIELDS, matched literally on the file (_SPEC_FILE), the attribute name (_SPEC_ATTR) and the base's name spelling `sh`
        (_SPEC_BASE), and proven by binding on the base: that bare name `sh` resolves, from the scopes `chain` outward, to
        a module-level constant bound exactly once and declared global or nonlocal nowhere, so a local or a rebound `sh` of the same
        spelling is not it. Any other attribute source refuses by name (_KEY_SRC), so a new accepted source enters only by an
        allowlist edit made on purpose. The escapes a general write check could not close for a bare base (a class replaced
        through type() with a key the census does not fold, a namespace constructor, a store elsewhere on the base chain) are, for
        this one binding, one line under the class limit: the census does not read a base's text, so a run-time rebuild of sh's
        class or module that the walk cannot see is the class limit's residual, which the remainder sentence names. Five of the
        seven conjuncts each red on a plant of its own (R1.7 of the eleventh round's review, the census module's HT_SOURCE): the
        file, the attribute name, the base spelled sh, the base bound once and the base at module level (got[2]), each by a plant
        accepted, silent, with that conjunct dropped. The base resolving to no refusal (got[0]) reds by its loud crash, an IndexError
        on the refusal's two-tuple. The declared-nowhere conjunct is dominated, so no plant can red it: _key_binding refuses every shape that puts sh in ix["decl"]
        before this reads it (a function's global declaration of sh is its own refusal, a module-level one reaches it through got[0],
        and a nonlocal sh needs a second binding, which the bound-once conjunct refuses), so dropping it neither crashes nor accepts."""
        if self.rel != _SPEC_FILE or x.attr != _SPEC_ATTR or not (isinstance(x.value, ast.Name) and x.value.id == _SPEC_BASE):
            return False
        got = self._key_binding(x.value, chain, "src")
        ix = self._key_index()
        return got[0] != "refuse" and got[2] and ix["binds"].get(_SPEC_BASE, 0) == 1 and _SPEC_BASE not in ix["decl"]
    def _key_settle(self, flags):
        """The allowlist over every key _unfolded held (Scan.kdefer), once the file's walk is done, each refusal a run-time form;
        then a key accepted by reading a name at module level, a builtin or a module constant (Scan.kheld) is refused where the
        file may rewrite its module namespace: it writes a name of it through a computed name or holds a star import
        (_namespace_flags's "computed", Scan's star imports), holds any run-time form but a call or an attribute read of
        import_module or __import__ (whose module the computed test reads), or, for a builtin, may write the builtins."""
        held = []
        for e, chain in self.kdefer:
            self.kheld = []
            got = self._key_form(e, chain)
            if got: self.ns_runtime(e, got)
            elif self.kheld: held.append((e, self.kheld))
        if not held: return
        shut = (flags["computed"] or any(isinstance(x, ast.ImportFrom) and any(a.name == "*" for a in x.names) for x in _statements(self.ktree.body))
                or any(k not in ("import_module", "__import__") for k in self.ns_facts["rkinds"]))
        for e, names in held:
            hit = next(((nm, "its module namespace") for nm, how in names if shut), None) or next(
                ((nm, "the builtins") for nm, how in names if how == "builtin" and flags["builtins"]), None)
            if hit is not None: self.ns_runtime(e, _KEY_SHUT % (ast.unparse(e)[:40], hit[0], hit[1]))
    def _nskey(self, e):   # a namespace expression a run-time lookup by name reaches: `__dict__`, `__builtins__`, or a call ns_listed reads as vars, globals or locals (arm iii)
        return ((isinstance(e, ast.Attribute) and e.attr == "__dict__") or (isinstance(e, ast.Name) and e.id == "__builtins__")
                or (isinstance(e, ast.Call) and self.ns_listed(e.func) in ("vars", "globals", "locals")))
    @staticmethod
    def _starred_key(node):   # R1.5 of the eleventh round's review: a call handed a starred value in its first two positional arguments,
        # or a ** mapping, where the getattr family's and a namespace key's arms read the key by position: a key the census does not read
        return any(isinstance(a, ast.Starred) for a in node.args[:2]) or any(k.arg is None for k in node.keywords)
    def ns_string(self, node):   # arm iii: a listed name (_STRING_NAMES) spelled as a string, read only where a run-time lookup by name
        # takes it: the second argument of getattr/setattr/delattr/hasattr on any receiver; any argument of operator.attrgetter or
        # methodcaller (for attrgetter any dotted part); or a key on a namespace expression (a subscript's slice, or the first argument
        # of .get/.pop/.setdefault/.__getitem__/.__setitem__/.__delitem__); and in each of those positions a key the positive
        # allowlist (_unfolded, _key_form) does not PROVE by its binding, a run-time form of its own. The allowlist accepts only a
        # constant string spelling no listed name; a parameter; a call's return whose callee reaches neither text nor the str, bytes
        # or bytearray type nor a method of one; a name that is a loop or comprehension target inside a function over a literal of
        # constants, a once-bound module tuple constant no code can mutate or the one attribute source kernel/host_transport.py
        # holds, sh.SPEC_FIELDS, by binding (_spec_source), where the file may write no attribute of its name (_key_attr, its setter
        # read failing closed); a name that is such a target, or an unpacking target, over a parameter or such a call's
        # return, directly or through names an assignment, such a target or an unpacking binds to one; a boolean operation or an
        # if-expression each of whose values the allowlist accepts where it stands; and a name an assignment binds to any of these
        # but a constant string. Every other shape refuses by name (a direct attribute key or a name bound to one; any other
        # attribute source; that one where the file may write its attribute; a name bound to a constant string; a with
        # target, or a name bound to one; a walrus, or a name a walrus binds anywhere, a comprehension's included; a loop target
        # bound at module level, among them), the reason naming what the walk met
        if isinstance(node, ast.Subscript):
            if self._nskey(node.value): self.ns_facts["keyed"].add(id(node.value))   # choice 13: a key position, its key read here
            why = self._unfolded(node.slice) if self._nskey(node.value) else None
            if why: self.ns_runtime(node.slice, why)
            if self._nskey(node.value) and self._const_str(node.slice) in _STRING_NAMES: self.ns_runtime(node.slice, "spells %s as a string" % self._const_str(node.slice))
            return
        f = node.func   # the callee by its name, a name an import binds to it (in any scope), or as an attribute of a builtins (getattr) or operator (ns_opmods) receiver
        af = self.alias.get(f.id, f.id).split(".")[-1] if isinstance(f, ast.Name) else ""
        if (isinstance(f, ast.Name) and (af in _GETATTRS or f.id in self.ns_getattrs)) or (isinstance(f, ast.Attribute)
                and f.attr in _GETATTRS and self._builtins_recv(f.value)):
            if self._starred_key(node): return self.ns_runtime(node, _KEY_STARRED)   # R1.5: its key, starred or in a ** mapping, is unread
            why = self._unfolded(node.args[1]) if len(node.args) > 1 else None
            if why: self.ns_runtime(node.args[1], why)
            if len(node.args) > 1 and self._const_str(node.args[1]) in _STRING_NAMES: self.ns_runtime(node.args[1], "spells %s as a string" % self._const_str(node.args[1]))
        d = self.dotted(f)
        op = d if d in ("operator.attrgetter", "operator.methodcaller") else ("operator." + self.ns_ops[f.id]) if (
            isinstance(f, ast.Name) and f.id in self.ns_ops) else ("operator." + f.attr) if (isinstance(f, ast.Attribute) and f.attr in ("attrgetter", "methodcaller")
                                                                                              and isinstance(f.value, ast.Name) and f.value.id in self.ns_opmods) else None
        if op is not None:
            for a in list(node.args) + [k.value for k in node.keywords]:
                why = self._unfolded(a)
                if why: self.ns_runtime(a, why)
                s = self._const_str(a)
                if s is not None and (s in _STRING_NAMES or (op == "operator.attrgetter" and any(p in _STRING_NAMES for p in s.split(".")))):
                    self.ns_runtime(a, "spells %s as a string" % s)
        if isinstance(f, ast.Attribute) and f.attr in ("get", "pop", "setdefault", "__getitem__", "__setitem__", "__delitem__") and self._nskey(f.value):
            self.ns_facts["keyed"].add(id(f.value))   # choice 13: a key position, its key read here
            if self._starred_key(node): return self.ns_runtime(node, _KEY_STARRED)   # R1.5
            why = self._unfolded(node.args[0]) if node.args else None
            if why: self.ns_runtime(node.args[0], why)
            if node.args and self._const_str(node.args[0]) in _STRING_NAMES: self.ns_runtime(node.args[0], "spells %s as a string" % self._const_str(node.args[0]))
    def visit_Global(self, n):
        self.globals[-1].update(n.names)
        if self.defs: self.global_decls.append((tuple(self.defs), tuple(n.names)))   # Result.global_decls
    def write(self, name, line, rebind=False):
        """A write of a name (Result.writes); a binding under `global` (rebind) or a write by a statement at module level is also a
        rebind of the module's name (Result.rebinds), and any other write inside a function or a class body is a write only."""
        self.writes.setdefault(name, []).append(line); self.cdepth.setdefault(name, []).append(0)
        if rebind or not self.stack: self.rebinds.setdefault(name, []).append(line)
    def cwrite(self, e, line, extra=0):
        """Layer iv's module side: a change to the value of `e`, or to an item of it `extra` levels further down, which reaches the
        name at its root (_chain_root): a change of that name (cwrites, which cflows makes a write of a module container: never a
        rebind, the name keeps its binding) at the depth the change stands below it (cdepth)."""
        got = _chain_root(e)
        if got is not None: self.cwrites.setdefault(got[0], []).append(line); self.cdepth.setdefault(got[0], []).append(got[1] + extra)
    def cbind(self, targets, value, loop=False):
        """Layer iv's module side: the names `value` reads through (_flow_roots) bound to the targets' names (cedges; a loop's or a
        comprehension's target an item), and escaping where a target stores into another object (cescapes)."""
        if type(value) in _NO_ROOTS or type(value) is ast.Call and not (type(value.func) is ast.Attribute and value.func.attr in _READ_METHODS): return
        roots = _flow_roots(value)
        if not roots: return
        in_class = bool(self.defs) and isinstance(self.defs[-1], ast.ClassDef)   # layer iv: a name a class body binds is an attribute of that class, reachable through it, not a plain edge
        names, other = [], False
        for t in targets:
            got = _target_names(t); names += [(x, isinstance(t, (ast.Tuple, ast.List)) or loop) for x in got[0]]; other = other or got[1]
        if in_class and names: other = True   # a container a class body aliases into a class attribute escapes through the class (never linked back to the name the edge follows)
        for r, ops in roots:
            if other: self.cescapes.setdefault(r, []).append(ops)
            for x, item in names: self.cedges.setdefault(r, []).append((x, ops + ("item",) if item else ops))
    def cescape(self, value):   # layer iv's module side: the names `value` reads through leave the file's sight (cescapes, with the steps)
        for r, ops in (_flow_roots(value) if value is not None else ()): self.cescapes.setdefault(r, []).append(ops)
    def cflows(self):
        """Layer iv's module side, at the walk's end: each module container whose text the census reads (a module name one top-level
        assignment binds to a list, dict or set literal or comprehension) that is changed other than by the forms write records (a
        store or delete through an item of it or an attribute, a method called on it or an item of it outside the closed set
        _READ_THROUGH (the in-place changers among them), a method called on it whose return is dropped, a changer read off it or an
        item of it unbound, an attribute read off it other than as a method's callee, a setattr or delattr on it, an augmented
        assignment to it, which runs its own in-place method (visit_AugAssign), or it or an item of it an operand whose other operand
        is no constant, handed to that operand's method (coperands): cwrites), or that a
        name bound to it, to an item of it or to a new
        object holding one is changed through (at a depth reaching it: its levels of new objects taken off), or that such a name, or it,
        leaves the file's sight through (stored into another object, returned, yielded, handed as a default or matched: the container
        itself or a new object holding it, or an item of it where its literal holds any value but constants and tuples of them), is
        written (Result.writes), so the served pass reads it as a run-time memo, refused unless SERVED_ALLOW names the place, and the
        route typing reads no type through it. Read by the names' spellings in every scope, as Result.writes reads them, so a local of the
        same spelling counts too, on the refusing side. A module name one top-level assignment binds to a call is read the same way:
        changed by one of those forms (cwrites), or changed through or let out of the file's sight by a name so bound to it (this
        walk, its literal no literal of constants), it is changed (Result.changed), and the served pass reads it as a run-time memo
        wherever it takes text through it but as a call's argument (_Served.cmemos, the call limit). Each state the walk pops is
        expanded once, in _cflow_step. What this side does not read is the item limit (the 19:33Z ruling, _Served._containers): a name
        that an unpacking nested in another, or a loop's or a comprehension's unpacking (a generator expression's among them), binds
        in a function or at module level is read at a depth that does not reach the container (cbind gives each name of a tuple or
        list target, or of a loop's or a comprehension's target, one item step, whatever its nesting: mupn, mfl and mcf in a function,
        mtn, mtl, mcn and mcg at module level), and a subscript of a new object holding an item, as an
        augmented assignment's target, in either place, is a store into that object (masf in a function, mts at module level); each
        passes silently."""
        for x, v in self.consts.items():
            call = type(v) is ast.Call   # a module name bound to a call: read as the containers are, its hit a change of it (Result.changed)
            if not (call or isinstance(v, _DISPLAYS)) or call and x in self.cwrites: continue
            if x in self.cwrites: self.writes.setdefault(x, []).append(self.cwrites[x][0]); continue
            frozen = _frozen(v)   # a literal of constants alone: an item of it that leaves the file's sight is a constant
            # (a name, the levels of new objects around it, whether it stands inside the container); a name is read again only in a
            # state no state it was read in covers (fewer levels, or the same and not inside), which reaches it wherever the covered one
            # does, so a binding that holds itself ends the walk
            seen, todo, hit = {x: [(0, False)]}, [(x, 0, False)], None
            while todo and hit is None:
                y, fr, inside = todo.pop()
                edges = self._cflow_step(self.cedges.get(y, ()))   # the walk's step, once for each state it pops
                if y != x and any(d >= fr for d in self.cdepth.get(y, ())): hit = y; break
                for ops in self.cescapes.get(y, ()):
                    if not (_steps(ops, fr, inside)[1] and frozen): hit = y; break
                for z, ops in edges:
                    f, ins = _steps(ops, fr, inside)
                    if not any(f0 <= f and (not i0 or ins) for f0, i0 in seen.get(z, ())): seen.setdefault(z, []).append((f, ins)); todo.append((z, f, ins))
            if hit is not None and call: self.cwrites.setdefault(x, []).append(v.lineno)   # Result.changed: a run-time memo (_Served.cmemos)
            elif hit is not None: self.writes.setdefault(x, []).append(v.lineno)
    def _cflow_step(self, edges):
        """cflows' expansion of one (name, levels, inside) state its walk pops, which it calls once for each: the walk keeps one visited
        map per module container (`seen`, the states each name bound to it was read in, a state read again only where none read covers
        it), and the step, given the popped name's bindings to other names (cedges), hands them back to read, in their order (freeze
        ruling 2 of the eleventh round: its count pin reads this step from outside the script)."""
        return list(edges)
    def global_bind(self, name, line):   # a binding of a name the enclosing function declares `global`
        if self.stack and name in self.globals[-1]: self.write(name, line, True)
    def visit_Name(self, n):   # a module name a function binds under `global`; a bare `_send` read other than as a call's function
        if isinstance(n.ctx, ast.Store): self.global_bind(n.id, n.lineno)
        elif n.id == "_send" and isinstance(n.ctx, ast.Load) and id(n) not in self.send_funcs: self.send_ref(n)
        if n.id in self.fn_names and id(n) not in self.ns_facts["callees"]:   # a top-level def's name in any other role, in any context
            self.fn_uses.setdefault(n.id, []).append(((n.lineno, n.col_offset), tuple(self.kscopes)))
        listed = self.ns_listed(n)   # arm ii: the listed callable, computed-name writer or setter the name reaches, by its own name or an import's name for it
        if n.id == "__builtins__": self.ns_facts["builtins"] = True
        elif n.id == "__file__" and not isinstance(n.ctx, ast.Load): self.ns_facts["file"] = True
        elif n.id in ("staticmethod", "classmethod") and not isinstance(n.ctx, ast.Load): self.ns_facts["deco"] = True
        elif listed in _NS_READS and isinstance(n.ctx, ast.Load) and id(n) not in self.ns_facts["callees"]:
            self.ns_facts["ns_calls"].append(n)   # globals, vars, setattr or delattr itself read (`_g = globals`, `_s = setattr`), a use no `.get` read limits
        if listed in _RUNTIME_NAMES: self.ns_runtime(n, "names %s" % listed, listed)   # a listed callable, in any context
        g = self.alias.get(n.id, n.id).split(".")[-1] if n.id in self.ns_getattrs else n.id
        if g in _GETATTRS and isinstance(n.ctx, ast.Load) and id(n) not in self.ns_facts["callees"]:   # choice 3: getattr's family aliased
            self.ns_runtime(n, _GETATTR_ALIAS % g, g)
        if n.id == "__builtins__" and isinstance(n.ctx, ast.Load): self.ns_facts["bnames"].append(n)   # choice 13's population
    def visit_ExceptHandler(self, n):   # `except E as X` under `global X`
        if n.name: self.global_bind(n.name, n.lineno); self.ns_bind(n.name)
        self.generic_visit(n)
    def visit_MatchAs(self, n):   # a match capture under `global X`: `case X:`, `case [X]:`, `case ... as X:`
        if n.name: self.global_bind(n.name, n.lineno); self.ns_bind(n.name)
        self.generic_visit(n)
    visit_MatchStar = visit_MatchAs   # `case [*X]:`
    def visit_MatchMapping(self, n):   # a match mapping's rest under `global X`: `case {**X}:`
        if n.rest: self.global_bind(n.rest, n.lineno); self.ns_bind(n.rest)
        self.generic_visit(n)
    def visit_arg(self, n):   # a parameter of a def or a lambda named `__file__` (_namespace_flags)
        self.ns_bind(n.arg); self.generic_visit(n)
    def visit_TypeVar(self, n):   # a type parameter so named (3.12)
        self.ns_bind(n.name); self.generic_visit(n)
    visit_ParamSpec = visit_TypeVarTuple = visit_TypeVar
    def visit_AnnAssign(self, n):
        if n.value is not None: self.ns_assign([n.target], n.value); self.cbind([n.target], n.value)
        self.generic_visit(n)
    def visit_NamedExpr(self, n):
        self.ns_assign([n.target], n.value); self.cbind([n.target], n.value); self.generic_visit(n)
    def visit_Expr(self, n):   # layer iv: a call whose return the statement drops, called for what it does (visit_Call's cwrite)
        if isinstance(n.value, ast.Call): self.cdropped.add(id(n.value))
        self.generic_visit(n)
    def visit_Return(self, n):   # layer iv: a value returned leaves the file's sight
        self.cescape(n.value); self.generic_visit(n)
    visit_Yield = visit_YieldFrom = visit_Return
    def visit_Match(self, n):   # layer iv: a match subject's patterns bind its items
        self.cescape(n.subject); self.generic_visit(n)
    def visit_Attribute(self, n):   # an `<x>._send` read other than as a call's function (`reply = self._send`), stored (`Handler._send = f`) or deleted
        if n.attr == "_send" and id(n) not in self.send_funcs: self.send_ref(n)
        if n.attr == "__dict__": self.ns_facts["maps"].append(n)   # a namespace mapping, a module's among them (_namespace_flags)
        if not isinstance(n.ctx, ast.Load): self.ns_facts["stores"].append(n); self.cwrite(n.value, n.lineno)   # layer iv: a store on it
        elif (n.attr in _CHANGERS or type(n.value) is ast.Name) and id(n) not in self.ns_facts["callees"]:   # layer iv: a changer read
            self.cwrite(n.value, n.lineno)   # off it or an item of it unbound, and any attribute read off the name itself other than as a
            # method's callee, a change of it (a name bound only to calls is read so on the local side too: _Served._containers)
        if n.attr in _RUNTIME_ATTRS: self.ns_runtime(n, "names the attribute %s" % n.attr, n.attr)   # arm ii: a function's or a frame's namespace, on any receiver
        listed = self.ns_listed(n)   # arm ii: a listed name as an attribute: compile, globals, vars, setattr and delattr on a builtins receiver, the rest on any receiver
        if listed in _RUNTIME_NAMES: self.ns_runtime(n, "names the attribute %s" % listed, listed)
        elif listed in _NS_READS and isinstance(n.ctx, ast.Load) and id(n) not in self.ns_facts["callees"]: self.ns_facts["ns_calls"].append(n)   # `builtins.globals` or `builtins.setattr` read
        if n.attr in _GETATTRS and isinstance(n.ctx, ast.Load) and id(n) not in self.ns_facts["callees"] and self._builtins_recv(n.value):
            self.ns_runtime(n, _GETATTR_ALIAS % n.attr, n.attr)   # choice 3: `builtins.getattr` read other than as a call's callee
        if n.attr == "__dict__" and self._builtins_recv(n.value): self.ns_facts["bmaps"].add(id(n))   # choice 13: the builtins' own mapping
        self.visit(n.value)   # the one child that holds nodes (attr is a string; the ctx marker holds none and no visitor reads it)
    def send_ref(self, n):
        self.send_refs.append((n, tuple(self.defs), ".".join(self.stack) or "<module>"))
    def visit_Subscript(self, n):   # a subscript store or delete writes its container
        if isinstance(n.ctx, (ast.Store, ast.Del)) and isinstance(n.value, ast.Name): self.write(n.value.id, n.lineno)
        elif isinstance(n.ctx, (ast.Store, ast.Del)): self.cwrite(n.value, n.lineno)   # layer iv: through an item or an attribute
        self.ns_string(n)   # arm iii: a listed name as a namespace subscript's key
        self.generic_visit(n)
    def visit_AugAssign(self, n):   # a module-level `X += ...` rebinds X after its binding
        if isinstance(n.target, ast.Name) and not self.stack: self.write(n.target.id, n.lineno)
        self.cbind([n.target], n.value)
        # layer iv: an augmented assignment runs its target's in-place method (`e += [v]` is list.__iadd__), a change of the name it
        # binds, in any scope (cflows reads a module container changed through a name bound to it, or to an item of it, so)
        if isinstance(n.target, ast.Name): self.cwrite(n.target, n.lineno)
        self.generic_visit(n)
    def visit_Import(self, n):
        self.alias.update({a.asname or a.name: a.name for a in n.names}); self.imports.extend((a.name.split(".")[0], n.lineno) for a in n.names)
        self.res.imports_of.setdefault(self.rel, []).extend((n.lineno, 0, a.name, None) for a in n.names)   # _page_importers
        for a in n.names: self.global_bind((a.asname or a.name).split(".")[0], n.lineno); self.ns_bind((a.asname or a.name).split(".")[0])   # an import under `global`
        if any(a.name.split(".")[0] == "builtins" for a in n.names): self.ns_facts["builtins"] = True
        for a in n.names: self.ns_own(n, a.name)
    def visit_ImportFrom(self, n):
        self.alias.update({a.asname or a.name: (n.module or "") + "." + a.name for a in n.names})
        self.res.imports_of.setdefault(self.rel, []).append((n.lineno, n.level or 0, n.module, tuple(a.name for a in n.names)))   # _page_importers
        for a in n.names: self.global_bind(a.asname or a.name, n.lineno); self.ns_bind(a.asname or a.name)
        if (n.module or "").split(".")[0] == "builtins" or any(a.name in ("builtins", "__builtins__") for a in n.names): self.ns_facts["builtins"] = True
        self.ns_own(n, "." if n.level else n.module or "")
        if n.level == 0 and n.module: self.imports.append((n.module.split(".")[0], n.lineno))
    def dotted(self, n):
        if isinstance(n, ast.Name): return self.alias.get(n.id, n.id)
        if isinstance(n, ast.Attribute):
            b = self.dotted(n.value); return b + "." + n.attr if b else None
    def prim(self, n):
        if isinstance(n, ast.BoolOp): return next((p for p in map(self.prim, n.values) if p), None)
        d = self.dotted(n); return SUB.get(d) or NET.get(d)
    def bind(self, name, value):
        if isinstance(value, ast.Call) and self.dotted(value.func) == "socket.socket": self.binds[-1][name] = "SOCKET"
        elif isinstance(value, ast.Call) and self.dotted(value.func) in LOOP_GETTERS: self.binds[-1][name] = "LOOP"
        elif self.prim(value): self.binds[-1][name] = self.prim(value)
    def bind_loop(self, target, it):
        """A for or comprehension target over a module constant of strings, or of tuples of strings, binds each name to the
        strings at its position, so importlib.import_module(mod) over such a constant resolves to the modules it names."""
        if not self.stack or not (isinstance(it, ast.Name) and isinstance(self.consts.get(it.id), (ast.List, ast.Tuple))): return
        names = [target] if isinstance(target, ast.Name) else list(target.elts) if isinstance(target, (ast.Tuple, ast.List)) else []
        for pos, t in enumerate(names):
            if not isinstance(t, ast.Name): continue
            vals = set()
            for e in self.consts[it.id].elts:
                v = e if isinstance(target, ast.Name) else e.elts[pos] if isinstance(e, (ast.Tuple, ast.List)) and pos < len(e.elts) else None
                if isinstance(v, ast.Constant) and isinstance(v.value, str): vals.add(v.value)
            if vals: self.binds[-1][t.id] = ("MODULES", frozenset(vals))
    def visit_For(self, n):
        self.bind_loop(n.target, n.iter); self.cbind([n.target], n.iter, True); self.generic_visit(n)
    visit_AsyncFor = visit_For
    def visit_comprehension(self, n):
        self.bind_loop(n.target, n.iter); self.cbind([n.target], n.iter, True); self.generic_visit(n)
    def comp(self, n):   # the generators bind before the element that reads them is visited
        self.kscopes.append(n)
        try:
            for g in n.generators: self.visit(g)
            for f in ("key", "value", "elt"):
                if hasattr(n, f): self.visit(getattr(n, f))
        finally: self.kscopes.pop()
    visit_ListComp = visit_SetComp = visit_GeneratorExp = visit_DictComp = comp
    def modules_of(self, a):
        """The modules an import_module or __import__ argument names: a string literal, a module constant holding one, or a
        loop or comprehension variable bound over a module constant of strings; None when the scan cannot resolve it."""
        if isinstance(a, ast.Constant) and isinstance(a.value, str): return [a.value]
        if isinstance(a, ast.Name):
            c = self.consts.get(a.id)
            if isinstance(c, ast.Constant) and isinstance(c.value, str): return [c.value]
            b = self.binds[-1].get(a.id) if self.binds else None
            if isinstance(b, tuple) and b[0] == "MODULES": return sorted(b[1])
        return None
    def visit_Assign(self, n):
        self.ns_assign(n.targets, n.value); self.cbind(n.targets, n.value)
        if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if not self.stack: self.consts[n.targets[0].id] = n.value
            else: self.bind(n.targets[0].id, n.value)
        self.generic_visit(n)
    def visit_With(self, n):
        for it in n.items: self.cbind([it.optional_vars] if it.optional_vars is not None else [], it.context_expr)
        if self.stack:
            for it in n.items:
                if isinstance(it.optional_vars, ast.Name): self.bind(it.optional_vars.id, it.context_expr)
        self.generic_visit(n)
    visit_AsyncWith = visit_With
    def program_ref(self, n, value):
        if os.path.basename(value) not in KNOWN_PROGRAM_REFS:
            self.res.problems.append("PROGRAM %s:%d names %r: a program under that directory is outside the declared scope; add it to NAMED "
                                     "and KNOWN_PROGRAM_REFS, or state here why it is not a program the kernel runs" % (self.rel, n.lineno, value))
    def visit_Constant(self, n):   # a program path spelled as one string: "tools/x.mjs"; a string equal to `_send`
        if isinstance(n.value, str) and _PROGRAM_PATH.match(n.value): self.program_ref(n, n.value)
        if n.value == "_send" and id(n) not in self.send_funcs: self.send_ref(n)   # `builtins.getattr(self, "_send")`, attrgetter("_send")
        if isinstance(n.value, str) and n.value in self.fn_names: self.fn_strs.add(n.value)   # a top-level def's name spelled as a string
    def coperands(self, ops):   # layer iv's module side: an operand handed to another operand's method (whose other operand is no
        for o in ops:   # constant), a change of the name it reaches (the dunder hand-off; the 07:37Z ruling's condition 2 on an item)
            if any(type(q) is not ast.Constant for q in ops if q is not o): self.cwrite(o, getattr(o, "lineno", 0))
    def visit_Compare(self, n):   # layer iv: a comparison or `in`, save an identity test, hands each operand to another's method
        if not all(isinstance(o, (ast.Is, ast.IsNot)) for o in n.ops): self.coperands([n.left] + n.comparators)
        self.generic_visit(n)
    def visit_BinOp(self, n):   # a program path built with pathlib: ROOT / "tools" / "x.mjs"; and layer iv's operand hand-off
        self.coperands([n.left, n.right])
        if (isinstance(n.op, ast.Div) and isinstance(n.right, ast.Constant) and isinstance(n.right.value, str) and isinstance(n.left, ast.BinOp)
                and isinstance(n.left.right, ast.Constant) and n.left.right.value in ("tools", "scripts")):
            self.program_ref(n, n.left.right.value + "/" + n.right.value)
        self.generic_visit(n)
    def enter(self, n):
        b = {}
        if not isinstance(n, ast.ClassDef):
            a = n.args
            for d in a.defaults + a.kw_defaults: self.cescape(d)   # layer iv: a default holds the value past the call
            for x, d in list(zip(a.args[len(a.args) - len(a.defaults):], a.defaults)) + list(zip(a.kwonlyargs, a.kw_defaults)):
                if d is not None and self.prim(d): b[x.arg] = self.prim(d)
        self.global_bind(n.name, n.lineno); self.ns_bind(n.name)   # a def or class statement under `global`, bound in the enclosing scope
        if isinstance(n, ast.ClassDef) and self.defs and not isinstance(self.defs[-1], ast.ClassDef): self.inner_classes.append(n)
        self.stack.append(n.name); self.binds.append(b); self.defs.append(n); self.globals.append(set()); self.kscopes.append(n); self.generic_visit(n)
        self.kscopes.pop(); self.globals.pop(); self.defs.pop(); self.binds.pop(); self.stack.pop()
    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = enter
    def visit_Lambda(self, n):   # its parameters and defaults run where it stands; a candidate in its body is in_lambda's
        for d in n.args.defaults + n.args.kw_defaults: self.cescape(d)   # layer iv: a default holds the value past the call
        self.visit(n.args); self.lambdas += 1; self.kscopes.append(n)
        try: self.visit(n.body)
        finally: self.kscopes.pop(); self.lambdas -= 1
    def argv(self, c):
        """(argv[0] as text, git subcommand or '', the literal after argv[0] or '') for a command call: a literal, a module constant
        (a string, or a list whose first element is read), sys.executable, or RUNTIME-SUPPLIED(expr) when the code does not spell it out."""
        kw = {k.arg: k.value for k in c.keywords}; a = c.args[0] if c.args else kw.get("args"); sub, follow = "", ""
        while isinstance(a, ast.BinOp): a = a.left
        if isinstance(a, ast.Name) and a.id in self.consts: a = self.consts[a.id]
        if isinstance(a, (ast.List, ast.Tuple)) and a.elts:
            lits = [e.value for e in a.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if lits and lits[0] == "git": sub = next((v for v in lits[1:] if not v.startswith("-")), "")
            if len(a.elts) > 1 and isinstance(a.elts[1], ast.Constant) and isinstance(a.elts[1].value, str): follow = a.elts[1].value
            a = a.elts[0]
            if isinstance(a, ast.Name) and a.id in self.consts: a = self.consts[a.id]
        if isinstance(a, ast.Attribute) and isinstance(a.value, ast.Name) and a.value.id == "sys" and a.attr == "executable": return "sys.executable", sub, follow
        if isinstance(a, ast.Constant) and isinstance(a.value, str): return a.value, sub, follow
        if isinstance(a, ast.Call) and getattr(a.func, "attr", "") == "get" and a.args and isinstance(a.args[0], ast.Constant):
            return "%s or %s" % (a.args[0].value, ast.unparse(a.args[1]) if len(a.args) > 1 else "''"), sub, follow   # SSH_BIN = os.environ.get(..., "ssh")
        return "RUNTIME-SUPPLIED(%s)" % (ast.unparse(a)[:48] if a is not None else ""), sub, follow
    def visit_Call(self, n):
        d = self.dotted(n.func); p = SUB.get(d) or NET.get(d); attr = getattr(n.func, "attr", "")
        f = n.func; listed = self.ns_listed(f)   # the listed callable, computed-name writer or setter the callee reaches (ns_listed, arm ii)
        if (f.id if isinstance(f, ast.Name) else attr) in _SETTERS: self.setter_calls.append(n)   # _stored_attrs reads their names
        if attr == "get": self.ns_facts["gets"].add(id(n.func.value))   # a `.get(...)` read, the one use of a namespace mapping that writes nothing
        elif listed in _NS_SETTERS: self.ns_facts["setattrs"].append(n)   # a call of setattr or delattr, by its own name, an import's name for it or as an attribute of builtins (_namespace_flags)
        elif listed in _NS_WRITERS:   # a call of globals or vars, by its own name, an import's name for it or as an attribute of builtins
            if not n.args and not n.keywords: self.ns_facts["ns_calls"].append(n)
            elif listed == "vars" and len(n.args) == 1:
                self.ns_facts["maps"].append(n)
                if self._builtins_recv(n.args[0]): self.ns_facts["bmaps"].add(id(n))   # choice 13: the builtins' own mapping
        self.ns_facts["callees"].add(id(f))
        if listed in ("__import__", "import_module"): self.ns_facts["importers"].add(id(n))   # module()'s calls of either
        # a call of a listed callable, a run-time form whose reason names the call where the callee is a name, an attribute of a name
        # bound to builtins, or import_module or _getframe on any receiver (the callee's own node, visited next, is the form too)
        if listed == "_getframe": self.ns_runtime(n, "calls sys._getframe", listed)
        elif listed in _RUNTIME_NAMES and (isinstance(f, ast.Name) or listed == "import_module" or self.dotted(f.value) in ("builtins", "__builtins__")):
            self.ns_runtime(n, "calls %s" % listed, listed)
        self.ns_string(n)   # arm iii: a listed name as a string in a getattr-family second argument, an attrgetter/methodcaller argument, or a namespace-mapping key
        where = ".".join(self.stack) or "<module>"
        if attr == "_send" or (isinstance(n.func, ast.Name) and n.func.id == "_send"):   # route candidates, typed by routes_of
            self.sends.append((n, tuple(self.defs), where)); self.send_funcs.add(id(n.func))   # (the func is no reference of its own)
            if self.lambdas: self.in_lambda.add(id(n))
        if _is_ctype_write(n):
            self.ctype_writes.append((n, tuple(self.defs), where))
            if self.lambdas: self.in_lambda.add(id(n))
        if (isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) > 1 and isinstance(n.args[1], ast.Constant)
                and n.args[1].value == "_send"):   # `_send` named by a getattr: refused as the call (its string is no second reference)
            self.send_refs.append((n, tuple(self.defs), where)); self.send_funcs.add(id(n.args[1]))
        if attr == "send_response": self.responds.append((n, tuple(self.defs), where))
        if attr and (attr not in _READ_THROUGH or attr not in _READ_METHODS and id(n) in self.cdropped):   # layer iv: a method
            self.cwrite(n.func.value, n.lineno)   # outside the closed set _READ_THROUGH (a changer among them), or one whose return is
            # dropped, a change of its receiver, at the receiver's depth below the name it reaches
        if listed in _NS_SETTERS and n.args: self.cwrite(n.args[0], n.lineno)   # layer iv: setattr or delattr on it
        if attr in _MUTATORS + _DUNDER_MUTATORS:   # a mutating call writes its receiver, and a container type's writes its first argument
            if isinstance(n.func.value, ast.Name): self.write(n.func.value.id, n.lineno)
            if n.args and isinstance(n.args[0], ast.Name) and self.dotted(n.func.value) in _CONTAINER_TYPES:   # dict.update(X, ...)
                self.write(n.args[0].id, n.lineno)
        if not p and isinstance(n.func, ast.Name) and self.binds:
            b = self.binds[-1].get(n.func.id)
            if isinstance(b, str) and b not in ("SOCKET", "LOOP"): p = b + " via " + n.func.id
        if not p and attr in SOCKET_METHODS and n.args:   # a socket the scan resolves: bound in the function, or a tuple-literal address
            bound = isinstance(n.func.value, ast.Name) and self.binds and self.binds[-1].get(n.func.value.id) == "SOCKET"
            addr = n.args[1] if attr == "sendto" and len(n.args) > 1 else n.args[0]
            if bound or isinstance(addr, ast.Tuple): p = "socket." + attr
        if not p and attr in LOOP_METHODS:   # an event loop the scan resolves: bound in the function, or the getter's own call
            r = n.func.value
            if (isinstance(r, ast.Name) and self.binds and self.binds[-1].get(r.id) == "LOOP") or (isinstance(r, ast.Call) and self.dotted(r.func) in LOOP_GETTERS):
                p = NET["asyncio." + attr]
        if d in IMPORTERS and n.args:   # an import by name: through KNOWN_IMPORTS, or refused when the name is not spelled out
            mods = self.modules_of(n.args[0])
            if mods is None:
                self.res.problems.append("IMPORT %s:%d imports a module named at run time (%s): the census cannot gate it; spell the module as a "
                                         "string literal or a module constant" % (self.rel, n.lineno, ast.unparse(n)[:60]))
            else: self.imports.extend((m.split(".")[0], n.lineno) for m in mods)
        if p:
            fn = ".".join(self.stack) or "<module>"; road = T.get(self.rel + ":" + fn); head, sub, cls = "", "", None
            if p.split(" ")[0] in SUB.values():
                head, sub, follow = self.argv(n)
                shell = any(k.arg == "shell" and getattr(k.value, "value", None) is True for k in n.keywords)
                base = os.path.basename(head) if not head.startswith("RUNTIME-SUPPLIED") else head
                interp = base in INTERPRETERS or base.startswith("python")
                external = interp or shell or head.startswith("RUNTIME-SUPPLIED") or (head == "git" and not sub)
                if shell: head += " SHELL"
                if interp and follow.startswith("-"): head += " " + follow
                if external: cls = "runtime-program" if road in RUNTIME_ROADS else "external-program"
                elif road is None and ((head == "git" and sub in LOCAL_GIT) or head in LOCAL_TOOLS):
                    road = "local-git" if head == "git" else "local-program"
            elif n.args: head = ast.unparse(n.args[0])[:60]
            self.res.emit(self.rel, n.lineno, p, (head + " " + sub).strip(), fn, road, cls, "py")
        self.generic_visit(n)


def kind_of(path, name, under_js):
    if ".test." in name: return None
    if under_js: return "js" if name.endswith((".ts", ".js", ".mjs", ".cjs")) else None
    if name.endswith(".py"): return "py"
    if name.endswith((".js", ".mjs", ".cjs")): return "js"
    if name.endswith(".sh"): return "sh"
    with open(path, "rb") as fh: first = fh.readline()   # a dotted name outside those extensions (a .bash hook) is read for its shebang too
    if not first.startswith(b"#!"): return None
    return "py" if b"python" in first else "js" if b"node" in first else "sh" if b"sh" in first else None


def walk(root, res):
    """Every file of a scanned kind under the declared roots, recursively, and the named files; (relative path, kind)."""
    for base, under_js in [(d, False) for d in PY_ROOTS] + [(d, True) for d in JS_ROOTS]:
        top = os.path.join(root, base)
        if not os.path.isdir(top):
            res.problems.append("SCOPE the declared root %s/ is missing under %s" % (base, root)); continue
        for dp, dns, fns in os.walk(top):
            dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not os.path.islink(os.path.join(dp, d)))
            for n in sorted(fns):
                f = os.path.join(dp, n)
                if os.path.islink(f) or not os.path.isfile(f): continue
                k = kind_of(f, n, under_js)
                if k: yield os.path.relpath(f, root), k
                else: res.skipped += 1
    for rel in NAMED:
        if not os.path.isfile(os.path.join(root, rel)): res.problems.append("SCOPE the named file %s is missing under %s" % (rel, root)); continue
        yield rel, "js" if rel.endswith((".js", ".mjs", ".cjs")) else "sh"


def _binding_patterns(mod):
    """The binding shapes of one module, compiled once per module: the quoted specifier (`node:` or not), the shapes that bind
    the module's members to bare names (`names`: a brace list per match) and the shapes that bind the module itself to a name
    (`spaces`: a name per capturing group). Every alternative is one shape on its own line, so a shape's arm is one line and
    _module_bindings reads every group a match fills rather than a numbered one; the group map, for the record: names 1 a
    destructured require, 2 a named import, 3 the brace part of a mixed default-plus-named import, 4 a destructured
    `await import()`; spaces 1 a require assigned whole in its declaration, 2 a namespace import, 3 a default import alone,
    4 the default of a mixed default-plus-named import, 5 and 6 the default and the namespace of a default-plus-namespace
    import, 7 `import { default as X }` (X is the module), 8 TypeScript's `import X = require()`, 9 a bound `await import()`
    whole. A match binds only as _module_bindings counts it, and a family module's specifier no counted match reads is refused
    by line_scan (the module docstring's sentence on the two refusals)."""
    spec = r"['\"](?:node:)?%s['\"]" % re.escape(mod)
    req = r"require\(\s*%s\s*\)" % spec
    dyn = r"await\s+import\(\s*%s\s*\)" % spec
    names = re.compile("|".join((
        r"(?:const|let|var)\s*\{([^}]*)\}\s*=\s*" + req,                        # 1 a destructured require
        r"import\s*(?:type\s+)?\{([^}]*)\}\s*from\s*" + spec,                    # 2 a named import
        r"import\s+\w+\s*,\s*\{([^}]*)\}\s*from\s*" + spec,                      # 3 the brace part of a mixed default-plus-named import
        r"(?:const|let|var)\s*\{([^}]*)\}\s*=\s*" + dyn,                         # 4 a destructured await import()
    )))
    spaces = re.compile("|".join((
        r"(?:const|let|var)\s+(\w+)\s*=\s*" + req,                               # 1 a require assigned whole in its declaration
        r"import\s+\*\s+as\s+(\w+)\s+from\s*" + spec,                            # 2 a namespace import
        r"import\s+(\w+)\s+from\s*" + spec,                                      # 3 a default import alone
        r"import\s+(\w+)\s*,\s*\{[^}]*\}\s*from\s*" + spec,                      # 4 the default of a mixed default-plus-named import
        r"import\s+(\w+)\s*,\s*\*\s+as\s+(\w+)\s+from\s*" + spec,                # 5, 6 a default-plus-namespace import, both names
        r"import\s*\{[^}]*\bdefault\s+as\s+(\w+)\b[^}]*\}\s*from\s*" + spec,     # 7 `import { default as X }`
        r"import\s+(\w+)\s*=\s*" + req,                                          # 8 TypeScript's import-equals
        r"(?:const|let|var)\s+(\w+)\s*=\s*" + dyn,                               # 9 a bound await import() whole
    )))
    return re.compile(spec), names, spaces, mod


_CP_PATTERNS = _binding_patterns("child_process")
_CP_MODULE, _CP_NAMES, _CP_SPACES, _CP_NAME = _CP_PATTERNS
_CP_RENAME = re.compile(r"\s+as\s+|\s*:\s*")   # the `as` or `:` that renames a destructured member
# The connection family read through the same bindings (an added arm beside JS's literal spellings): module -> the members that
# open a connection; the tool a site is keyed on is the literal list's own name (`http.get` for http and https alike). ws is
# constructor-shaped (`new <binding>(`) and keyed `WebSocket`, the literal `new WebSocket(` entry's name.
NET_FAMILY = {"http": ("get", "request"), "https": ("get", "request"), "net": ("connect", "createConnection"), "tls": ("connect",)}
_NET_PATTERNS = {mod: _binding_patterns(mod) for mod in tuple(NET_FAMILY) + ("ws",)}
# The family modules, whose clients the binding arms read: a literal specifier of one that the import gate reads is read (a
# counted binding takes the module from it, or an arm reads a call through it) or refused by name (line_scan, JS_ALLOW)
FAMILY = ("child_process",) + tuple(NET_FAMILY) + ("ws",)
_GOES_ON = (".", "?", "[", "(")   # after a require or `await import()`, a member access, a conditional or a call: no whole binding


def _names_module(text, patterns):
    """Whether the file spells the module's quoted specifier at all (the four spellings _binding_patterns's specifier admits), a
    substring check before any regex runs over the file."""
    mod = patterns[3]
    return any(q + m + q in text for q in "'\"" for m in (mod, "node:" + mod))


def _next_code(text, i):
    """The first character of text at or after index i past whitespace, line breaks and comments ('' at the end)."""
    n = len(text)
    while i < n:
        if text[i].isspace(): i += 1
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2); i = n if j < 0 else j + 2
        elif text.startswith("//", i):
            j = text.find("\n", i); i = n if j < 0 else j + 1
        else: return text[i]
    return ""


def _module_bindings(text, patterns):
    """(names, spaces, read) a JavaScript or TypeScript file binds from one module, by its patterns (_binding_patterns): `names`
    maps a bare name the file destructures or imports to the member it stands for (renamed or not; a `type` import binds no
    value but is read for parity, and `default as X` in a brace list lands here under the member `default`, which no family
    names, beside X's place in `spaces`), `spaces` holds the names the file keeps the module under, and `read` holds the text
    offsets where a counted match ends, each the end of the specifier it reads. A names match fills one group, its brace list
    (the alternative that matched); a spaces match fills one group per bound name (two for a default-plus-namespace import), so
    every filled group is read and no group number is. A spaces match (the module taken whole) that ends at a require's or an
    `await import()`'s closing paren and is followed, past whitespace and comments, by `.`, `?`, `[` or `(` binds nothing and
    does not count (the value is a member, a conditional or a call, not the module: `const get = require("http").get`); a names
    match whose brace list takes `default` binds its names and does not count, unless a spaces match ending at the same place
    binds that name whole (the `import { default as X }` shape). Where a counted and an uncounted match end at one place, the
    place is not read."""
    spec, names_rx, spaces_rx, _mod = patterns
    names, spaces, read, unread, whole = {}, set(), set(), set(), {}
    if not _names_module(text, patterns): return names, spaces, read
    for m in spaces_rx.finditer(text):
        if text[m.end() - 1] == ")" and _next_code(text, m.end()) in _GOES_ON: unread.add(m.end()); continue
        got = {g for g in m.groups() if g}
        spaces.update(got); whole.setdefault(m.end(), set()).update(got); read.add(m.end())
    for m in names_rx.finditer(text):
        read.add(m.end())
        for part in next((g for g in m.groups() if g is not None), "").split(","):
            part = part.strip()
            if part.startswith("type "): part = part[5:].strip()
            if part:
                bits = [b.strip() for b in _CP_RENAME.split(part)]
                names[bits[-1]] = bits[0]
                if bits[0] == "default" and bits[-1] not in whole.get(m.end(), ()): unread.add(m.end())
    return names, spaces, read - unread


def _cp_bindings(text):
    """The names a JavaScript or TypeScript file binds from child_process, and the call patterns those bindings make, read once
    per file: `names` maps a bare name the file destructures or imports to the family member it stands for, `spaces` holds
    the names the file keeps the module under (the shapes _binding_patterns reads: a require or an `await import()` assigned
    whole, TypeScript's import-equals, a namespace or default import alone or together, `import { default as X }`), `qualified` matches
    a family call qualified to the module (`child_process.<fn>(`, `require('child_process').<fn>(`, a name in `spaces`), and
    `bare` matches a family call by a name in `names`, or is None when the file binds none. A file whose text never names
    child_process binds nothing and qualifies no call, so it is None here and no line of it is a site. A family member
    called by a bare name the file does not bind is not a site. `read` holds the offsets where a counted binding ends
    (_module_bindings), for the refusal of a specifier no binding reads (line_scan)."""
    if "child_process" not in text: return None
    names, spaces, read = _module_bindings(text, (_CP_MODULE, _CP_NAMES, _CP_SPACES, _CP_NAME))
    qual = [r"\bchild_process", r"require\(\s*%s\s*\)" % _CP_MODULE.pattern] + [r"\b" + re.escape(s) for s in sorted(spaces)]
    bare = sorted(n for n, fn in names.items() if fn in CP_FAMILY)
    return {"names": names, "spaces": spaces, "read": read, "qualified": re.compile(r"(?:%s)\.(%s)\(" % ("|".join(qual), "|".join(CP_FAMILY))),
            "bare": re.compile(r"(?<![\w.$])(%s)\(" % "|".join(map(re.escape, bare))) if bare else None}


def _cp_sites(ln, cp):
    """(family member, index after its open paren) for every child_process call on the line, through the file's bindings
    (_cp_bindings): qualified to the module, or a bare name the file binds; none in a file that never names the module."""
    if cp is None: return []
    out = [(m.group(1), m.end()) for m in cp["qualified"].finditer(ln)]
    if cp["bare"] is not None:
        out.extend((cp["names"][m.group(1)], m.end()) for m in cp["bare"].finditer(ln))
    return out


def _net_bindings(text):
    """The connection family through the file's bindings, read once per file with the shapes _cp_bindings reads for
    child_process, over the modules NET_FAMILY names and ws: a list of (pattern, tool of a match) arms. For http, https, net
    and tls a member call qualified to an inline require or to a space (a name the file keeps the module under, the shapes
    _binding_patterns reads), and a call by a bare name the file binds from the module (renamed or not); for ws the constructor shape
    (`new (require('ws'))(`, `new (require('ws').WebSocket)(`, `new <space>(`, `new <space>.WebSocket(`, `new <bound name>(`).
    Returned as {"arms": [(module, pattern, tool of a match)], "read": {module: the offsets where a counted binding ends}},
    the arms empty for a file that names none of the modules; the bare global `new WebSocket(` is the literal list's."""
    arms, read = [], {}
    for mod, members in NET_FAMILY.items():
        if not _names_module(text, _NET_PATTERNS[mod]): continue
        names, spaces, read[mod] = _module_bindings(text, _NET_PATTERNS[mod])
        tool = ("http" if mod == "https" else mod) + ".%s"
        qual = [r"require\(\s*%s\s*\)" % _NET_PATTERNS[mod][0].pattern] + [r"\b" + re.escape(s) for s in sorted(spaces)]
        arms.append((mod, re.compile(r"(?:%s)\.(%s)\(" % ("|".join(qual), "|".join(members))), lambda m, t=tool: t % m.group(1)))
        bare = {n: fn for n, fn in names.items() if fn in members}
        if bare:
            arms.append((mod, re.compile(r"(?<![\w.$])(%s)\(" % "|".join(map(re.escape, sorted(bare)))), lambda m, t=tool, b=bare: t % b[m.group(1)]))
    if _names_module(text, _NET_PATTERNS["ws"]):
        names, spaces, read["ws"] = _module_bindings(text, _NET_PATTERNS["ws"])
        heads = ([r"\(\s*require\(\s*%s\s*\)(?:\.WebSocket)?\s*\)" % _NET_PATTERNS["ws"][0].pattern]
                 + [re.escape(s) + r"(?:\.WebSocket)?" for s in sorted(spaces)] + [re.escape(n) for n, fn in sorted(names.items()) if fn == "WebSocket"])
        arms.append(("ws", re.compile(r"\bnew\s+(?:%s)\s*\(" % "|".join(heads)), lambda m: "WebSocket"))
    return {"arms": arms, "read": read}


def _net_sites(ln, nb):
    """The tools of the connection family's binding arm (_net_bindings) on the line, each once, in order of first match."""
    out = []
    for _mod, rx, tool_of in nb["arms"] if nb else ():
        for m in rx.finditer(ln):
            t = tool_of(m)
            if t not in out: out.append(t)
    return out


def _js_args(text):
    """The top-level arguments of a call, from the text after its open paren up to the closing paren."""
    args, depth, cur, quote = [], 0, [], None
    for ch in text:
        if quote:
            cur.append(ch)
            if ch == quote: quote = None
            continue
        if ch in "'\"`": quote = ch; cur.append(ch); continue
        if ch in "([{": depth += 1
        elif ch in ")]}":
            if depth == 0: break
            depth -= 1
        elif ch == "," and depth == 0: args.append("".join(cur).strip()); cur = []; continue
        cur.append(ch)
    if "".join(cur).strip(): args.append("".join(cur).strip())
    return args


_SHELL_TRUE = re.compile(r"\bshell\s*:\s*true\b")   # a `shell: true` option in a child_process call's arguments


def _js_argv(fn, text):
    """(head, git subcommand or '', the literal after the head or '', shell) for a child_process call, read from the text after
    its open paren the way Scan.argv reads a Python command call: a quoted literal is the head, anything else RUNTIME-SUPPLIED;
    the first array argument gives git its subcommand (the first literal not starting with -) and an interpreter its flag."""
    args = _js_args(text); a0 = args[0] if args else ""
    lit = lambda t: t[1:-1] if len(t) >= 2 and t[0] in "'\"`" and t[-1] == t[0] and "${" not in t else None
    head, sub, follow = lit(a0), "", ""
    if head is None: head = "RUNTIME-SUPPLIED(%s)" % a0[:48]
    if len(args) > 1 and args[1].startswith("["):
        elts = [lit(e) for e in _js_args(args[1][1:])]
        lits = [e for e in elts if e is not None]
        if head == "git": sub = next((v for v in lits if not v.startswith("-")), "")
        if elts and elts[0] is not None: follow = elts[0]
    shell = fn in ("exec", "execSync") or bool(_SHELL_TRUE.search(text))   # exec runs its text through a shell
    return head, sub, follow, shell


_JS_FROM = re.compile(r"\bfrom\s*(['\"])([^'\"]+)\1")
_JS_SIDE_EFFECT = re.compile(r"import\s*(['\"])([^'\"]+)\1")
_JS_REQUIRE = re.compile(r"(?<![\w.$])(?:require|import)\(\s*(['\"])([^'\"]+)\1\s*\)")
_JS_STATEMENT = re.compile(r"(?:import|export)\b(?!\s*[(.])")   # served text: the first line of an import or export statement (not `import(`, `import.meta`)
# A walked file: the first line of a statement that can take a `from` string, `import` (not `import(`, `import.meta`), `export {`,
# `export *`, `export type {` or `export type *`; `export function` and the like open none, so a `from` in a string after one is not
# read as a specifier
_JS_OPENS = re.compile(r"import\b(?!\s*[(.])|export\s*(?:type\s*)?[{*]")


def _js_specifiers(s, served=False, cont=False):
    """The module specifiers a JavaScript or TypeScript line imports or requires, as their matches over the line (group 2 the
    specifier, group 0 the form as spelled): every literal require() and import() spelled whole on the line (the name, its paren,
    the quoted specifier and the closing paren, with nothing between them but whitespace inside the parens), wherever it stands;
    a side-effect import that begins its line (`import`, whitespace alone, then the quoted specifier); and the first `from` string
    (`from`, whitespace alone, then a quoted specifier) on a line that starts with import or export or that continues an import or
    export statement that begins its own line and has no specifier yet (`cont`, line_scan's state), and, in a walked file, any
    line led by a closing brace. In a walked file a continuation line is read whatever leads it (`import {`, then `  get } from
    "https"`); in served text, where a `}` leads any block, only a continuation line led by `from` or `}`, so a specifier on a
    continuation line led by anything but `from` or a closing brace is not read there, one of the served residual's shapes
    (UNREAD_BINDINGS, among them a specifier after a trailing `from`, a require() or `await import()` split across lines and a
    statement that does not begin its line). A comment between `from` (or a side-effect `import`) and its specifier is read by
    neither this reader nor the binding patterns: in served text a client through it is no site and no line whatever the module,
    `https`, `net` and `tls` included, and a package outside KNOWN_JS_IMPORTS passes the gate. Over the walked files the webview
    leg's pin (ui/webview/import-gate-parse.test.ts) holds these reads, as line_scan records them (Result.reads), equal to a
    TypeScript parse of the same files, so there that comment, and any layout this reader does not read, is red by file, line and
    specifier; served text is not parsed."""
    if "import" not in s and "require" not in s and "from" not in s: return []   # every shape below spells one of the three
    out = []
    if s.startswith(("import", "export")) or (not served and (cont or s.startswith("}"))) or (cont and (s.startswith("}") or _JS_FROM.match(s))):
        m = _JS_FROM.search(s)
        if m: out.append(m)
        m = _JS_SIDE_EFFECT.match(s)
        if m: out.append(m)
    out.extend(_JS_REQUIRE.finditer(s))
    return out


def _call_end(text, i):
    """The index after the paren that closes the one at text[i] (quotes skipped; the line's end when none closes it)."""
    depth, quote, j, n = 0, None, i, len(text)
    while j < n:
        ch = text[j]
        if quote:
            if ch == "\\": j += 2; continue
            if ch == quote: quote = None
        elif ch in "'\"`": quote = ch
        elif ch in "([{": depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth <= 0: return j + 1
        j += 1
    return n


def _js_code(ln):
    """The line with every string's text blanked and a trailing comment cut, for the bare-value clause of _js_unread_requires: a
    quote (', " or a backtick) opens a string to the same quote's next unescaped occurrence on the line, `//` outside a string
    starts a trailing comment, and `/* ... */` outside a string is blanked. Columns are kept."""
    out, q, i, n = list(ln), None, 0, len(ln)
    while i < n:
        ch = ln[i]
        if q:
            if ch == "\\":
                out[i:i + 2] = " " * len(out[i:i + 2]); i += 2; continue
            if ch == q: q = None
            else: out[i] = " "
            i += 1; continue
        if ch in "'\"`": q = ch
        elif ln.startswith("//", i): return "".join(out[:i])
        elif ln.startswith("/*", i):
            j = ln.find("*/", i + 2); j = n if j < 0 else j + 2
            out[i:j] = " " * (j - i); i = j; continue
        i += 1
    return "".join(out)


_REQ_CALL = re.compile(r"(?<![\w$.])require\s*(?:/\*.*?\*/\s*)*\(")        # a call of require, whatever stands before its paren
_REQ_METHOD = re.compile(r"\.\s*require\s*(?:/\*.*?\*/\s*)*\(")            # any .require( call
_REQ_MEMBER = re.compile(r"(?<![\w$])require\s*(?:\?\.\s*[\w$]*|\.\s*[\w$]*|\[[^\]]*\]?)")   # any member access on require
_REQ_BARE = re.compile(r"(?<![\w$])require\s*(?=[;,)}\]]|$)")              # require as a bare value, over the line's code (_js_code)
_CREATE_REQUIRE = re.compile(r"(?<![\w$])createRequire\s*(?:/\*.*?\*/\s*)*\(")
_IMPORT_CALL = re.compile(r"(?<![\w$.])import(\s*(?:/\*.*?\*/\s*)*)\((\s*`)?")   # a dynamic import: the gap before its paren, a template


def _chain_start(ln, i):
    """Where the dotted name that ends just before index i starts (`process.mainModule` before `.require`)."""
    while i > 0 and (ln[i - 1].isalnum() or ln[i - 1] in "_$.?"): i -= 1
    return i


def _js_unread_requires(ln):
    """The requires and imports on a walked JavaScript or TypeScript line that the import gate cannot read, as (column, what,
    the expression as spelled): a call of `require` in any shape but the gate's literal one (whitespace or a comment before the
    paren, a template or a computed specifier), `require` as a bare value (followed by `;`, `,`, `)`, `}`, `]` or the end of the
    line, in the line's code: _js_code), any `.require(` call, any member access on `require`, a `createRequire(` call, and an
    `import(` with a template specifier or whitespace or a comment before its paren. line_scan refuses each unless JS_ALLOW names
    it; a line that spells neither `equire` (require, createRequire) nor `import` costs two substring tests."""
    out = []
    if "equire" in ln:
        for m in _REQ_CALL.finditer(ln):
            if not _JS_REQUIRE.match(ln, m.start()):
                out.append((m.start(), "a call of require in a shape the gate does not read", ln[m.start():_call_end(ln, m.end() - 1)]))
        for m in _REQ_METHOD.finditer(ln):
            at = _chain_start(ln, m.start())
            out.append((at, "a .require( call", ln[at:_call_end(ln, m.end() - 1)]))
        for m in _REQ_MEMBER.finditer(ln):
            out.append((m.start(), "a member access on require", m.group(0)))
        for m in _REQ_BARE.finditer(_js_code(ln)):
            at = _chain_start(ln, m.start())
            out.append((at, "require as a bare value", ln[at:m.start() + len("require")]))
        for m in _CREATE_REQUIRE.finditer(ln):
            out.append((m.start(), "a createRequire( call", ln[m.start():_call_end(ln, m.end() - 1)]))
    if "import" in ln:
        for m in _IMPORT_CALL.finditer(ln):
            if m.group(1) or m.group(2):
                out.append((m.start(), "an import( with a template specifier or a gap before its paren", ln[m.start():_call_end(ln, m.end() - 1 - len(m.group(2) or ""))]))
    return out


def _line_starts(text):
    """The offset in text where each of its lines starts, the lines as str.splitlines cuts them (line_scan's lines)."""
    out, at = [], 0
    for piece in text.splitlines(True):
        out.append(at); at += len(piece)
    return out


_LED = ("//", "*", "/*")   # line_scan's comment test for a JavaScript line: the stripped line starts with one of these
_BREAKS = re.compile("[\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029]")   # the line breaks str.splitlines cuts at besides \n


def _led_at(text, i):
    """Whether the line of text that holds index i, as str.splitlines cuts it, is led by `//`, `/*` or `*`, for an index where a
    specifier's opening quote stands: the line's text before i, from the last line break, with the quote and the character after
    it, stripped of its leading whitespace, starts with one of those (the test line_scan makes of the whole stripped line, since
    the quote is no whitespace and no token is longer than two characters)."""
    head = text[text.rfind("\n", 0, i) + 1:i]
    cut = None
    for cut in _BREAKS.finditer(head): pass
    return ((head[cut.end():] if cut else head) + text[i:i + 2]).lstrip().startswith(_LED)


def _specifier_starts(text, mod):
    """Every index of text where a quoted specifier of the module starts, as _binding_patterns's first pattern spells it (a quote,
    `node:` or not, the module's name, a quote), found by str.find: each index that pattern matches at, overlapping ones
    included."""
    for q in "'\"":
        for pre in ("", "node:"):
            needle = q + pre + mod
            i = text.find(needle)
            while i >= 0:
                if text[i + len(needle):i + len(needle) + 1] in ("'", '"'): yield i
                i = text.find(needle, i + 1)


def _comment_bindings(text, mods=None):
    """The binding matches of a walked JavaScript or TypeScript file whose specifier stands on a line led by `//`, `/*` or `*`
    (a comment's line, or a line of code so led, such as an import's `* as h` continuation): the patterns match over the whole
    text, so such a binding binds its name, while line_scan skips the line and the import gate reads no module there; the
    webview leg's pin sees such a binding when the line is code and none on a comment line or in a template literal's text.
    {line number: [(column, module, the match's text on that line)]}, one per module on a line, over every family module's
    patterns (_binding_patterns), counted or not; empty for a file that names no family module. line_scan refuses each.
    `mods`: the family modules the file names, as line_scan's binding reads found them (_names_module), or None to test each
    here. A token prefilter keeps the patterns off a file where they can find nothing: every pattern ends at the module's quoted
    specifier (_binding_patterns's first pattern) or at a paren that only whitespace separates from it, so a match whose end stands
    on a led line holds the specifier on that line, and the patterns run over a file for a module only when a specifier of that
    module stands on a led line (_specifier_starts, _led_at); the outcome on every line is the same."""
    out, starts, lines = {}, None, None
    for p in (_CP_PATTERNS,) + tuple(_NET_PATTERNS[m] for m in tuple(NET_FAMILY) + ("ws",)):
        if (p[3] not in mods) if mods is not None else not _names_module(text, p): continue
        if not any(_led_at(text, i) for i in _specifier_starts(text, p[3])): continue   # no specifier of the module on a led line
        if starts is None: starts, lines = _line_starts(text), text.splitlines()
        for rx in (p[1], p[2]):
            for m in rx.finditer(text):
                at = next(k for k in range(len(starts) - 1, -1, -1) if starts[k] <= m.end() - 1)   # the specifier's line
                if not lines[at].strip().startswith(("//", "*", "/*")): continue
                lo = max(m.start(), starts[at])
                if all(x[1] != p[3] for x in out.get(at + 1, ())): out.setdefault(at + 1, []).append((lo - starts[at], p[3], text[lo:m.end()].strip()))
    return out


def _specifier_read(mod, end, ln, lo, hi, cp, nb):
    """Whether a family module's literal specifier, spelled at ln[lo:hi] and ending at text offset `end`, is read: a counted
    binding of the module ends there (_module_bindings), or a match of the module's arm spans it, a call read through it
    (`require('http').request(`, `new (require('ws'))(`)."""
    if mod == "child_process":
        if cp is None: return False
        if end in cp["read"]: return True
        rxs = [cp["qualified"]]
    else:
        if end in nb["read"].get(mod, ()): return True
        rxs = [rx for m, rx, _tool in nb["arms"] if m == mod]
    return any(m.start() <= lo and hi <= m.end() for rx in rxs for m in rx.finditer(ln))


def _js_refuse(res, rel, line, col, expr, text):
    """A refusal on the JavaScript side (line_scan): excused when JS_ALLOW names the place by its file and expression (the place,
    its line and column, recorded in res.allow_hits, whose count problems() holds to the entry's), a problem line otherwise."""
    key = (rel, expr)
    if key in JS_ALLOW: res.allow_hits.setdefault(key, set()).add((line, col))
    else: res.problems.append(text)


def _js_package(spec):
    """The package a specifier names, or None for the project's own module (a relative or absolute path) and a declaration
    file's ambient path pattern (`*/...`): the first path segment, two for a scoped package, `node:` dropped."""
    if spec.startswith((".", "/", "*")): return None
    spec = spec[5:] if spec.startswith("node:") else spec
    parts = spec.split("/")
    return "/".join(parts[:2]) if spec.startswith("@") else parts[0]


def _live_remainder(text):
    """The live text of a shell line after its echo or print lead: the text outside quotes, and the whole body of every
    $(...) and backtick substitution wherever it stands (inside double quotes too); the printed text inside quotes is not
    live. A paren-depth walk with quote states, not a regex: a nested $(...) closes at its own paren, a quoted paren
    inside a body does not close it, an unterminated body runs to the end of the line, and a word-initial # ends the
    live text (a comment)."""
    n = len(text); live = []

    def body(i, close):
        """(index after the closer, body text) for a substitution whose opener ended at i."""
        j, depth, q = i, 0, None
        while j < n:
            ch = text[j]
            if q:
                if ch == "\\" and q == '"': j += 2; continue
                if ch == q: q = None; j += 1; continue
                if q == '"' and text.startswith("$(", j): j = body(j + 2, ")")[0]; continue
                if q == '"' and ch == "`": j = body(j + 1, "`")[0]; continue
                j += 1; continue
            if ch == "\\": j += 2; continue
            if ch in "'\"": q = ch; j += 1; continue
            if text.startswith("$(", j): j = body(j + 2, ")")[0]; continue
            if close == ")":
                if ch == "(": depth += 1
                elif ch == ")":
                    if depth == 0: return j + 1, text[i:j]
                    depth -= 1
                elif ch == "`": j = body(j + 1, "`")[0]; continue
            elif ch == "`":
                return j + 1, text[i:j]
            j += 1
        return n, text[i:n]

    i, q = 0, None
    while i < n:
        ch = text[i]
        if q == "'":
            if ch == "'": q = None
            i += 1; continue
        if q == '"':
            if ch == "\\": i += 2; continue
            if ch == '"': q = None; i += 1; continue
            if text.startswith("$(", i): i, b = body(i + 2, ")"); live.append(" " + b + " "); continue
            if ch == "`": i, b = body(i + 1, "`"); live.append(" " + b + " "); continue
            i += 1; continue
        if ch == "\\": live.append(text[i:i + 2]); i += 2; continue
        if ch in "'\"": q = ch; i += 1; continue
        if text.startswith("$(", i): i, b = body(i + 2, ")"); live.append(" " + b + " "); continue
        if ch == "`": i, b = body(i + 1, "`"); live.append(" " + b + " "); continue
        if ch == "#" and (i == 0 or text[i - 1] in " \t"): break
        live.append(ch); i += 1
    return "".join(live)


def _browser_text(rel, kind):
    """Whether the walk scans the walked file `rel`, of kind `kind`, as browser text: JavaScript (a .js, .mjs or .cjs file, a .ts one
    under the browser and editor roots, or a node shebang) under those roots, where line_scan's DOM arm is on for a walked file, as
    it is for a served page's own text. The one rule for both: line_scan's DOM arm, and served_texts' coverage of a file a page reads
    at run time (layer v of the eleventh round's rulings: a file the walk scans any other way, as Python, as shell, or as JavaScript outside those roots
    with the DOM arm off, is refused by name, never counted as covered)."""
    return kind == "js" and rel.startswith(tuple(d + "/" for d in JS_ROOTS))


def _read_codec(expr):
    """The encoding argument of a file read (_READ_CALLS), or None where the read names none (the locale's default): `.read_text`'s
    own first positional argument or its `encoding=` keyword, and for `.read` the `encoding=` (or fourth positional) of the
    `open(...)` its receiver is. Returns (whether an encoding is named, the encoding node or None): a read whose encoding is named
    and is not a string constant the census reads as one of _UTF8_NAMES is not covered by the walk's UTF-8 scan (served_texts refuses
    it, _READ_CODEC), while a read that names none is the stated limit. A `**` keyword to `.read_text` may name the encoding in a
    mapping the census does not read, so it counts as an encoding named and unread (True, None), refused on the safe side; a `**` to
    the `open(...)` of a `.read` is refused before this, by _path (open handed a keyword)."""
    if not (isinstance(expr, ast.Call) and isinstance(expr.func, ast.Attribute)): return False, None
    attr = expr.func.attr
    if attr == "read_text":
        if any(k.arg is None for k in expr.keywords): return True, None   # a ** keyword may name the encoding, in a mapping unread here
        kw = next((k.value for k in expr.keywords if k.arg == "encoding"), None)
        if kw is not None: return True, kw
        return (True, expr.args[0]) if expr.args else (False, None)
    o = expr.func.value   # `.read`: the encoding of the open(...) its receiver is
    if isinstance(o, ast.Call) and isinstance(o.func, ast.Name) and o.func.id == "open":
        kw = next((k.value for k in o.keywords if k.arg == "encoding"), None)
        if kw is not None: return True, kw
        return (True, o.args[3]) if len(o.args) > 3 else (False, None)
    return False, None


def line_scan(rel, kind, text, res, base=0, dom=None, served=False, cut=False):
    """The shell or JavaScript sites, the DOM loads and the package gate over one file's text (read once, by scan). For a page the
    kernel serves (served_texts), `base` offsets the line numbers to the constant's place in its Python file, `dom` forces the DOM
    arm on (None keeps the rule: the browser and editor roots), `served` keeps served text's statement form, and `cut` marks a
    string literal a join of string constants carries on past its end (served_texts): a fetch( or import( whose argument, or a
    program call whose arguments, run to the end of its last line with no closing paren are left to the joined text, which reads
    them whole, so the call is listed once and not also by the part before the join. The gate reads a
    specifier in a literal require() or import() spelled whole on one line, wherever it stands, in a side-effect import that
    begins its line (`import`, whitespace alone, then the quoted specifier), and in the first `from` string (`from`, whitespace
    alone, then a quoted specifier) on a line that starts with import or export or that continues an import or export statement
    that begins its own line and has not yet ended, and, in a walked file, any line led by a closing brace (_js_specifiers). In
    served text a statement opens at any line that starts with import or export (_JS_STATEMENT: not `import(` or `import.meta`),
    a line continues it only when led by `from` or `}`, and no line is skipped as a comment, so there a specifier on a continuation
    line led by anything but `from` or a closing brace is not read, one of the served residual's shapes (UNREAD_BINDINGS). In a
    walked file a statement opens only where _JS_OPENS matches, and any line of it is read for its `from` string but a line led
    by `//`, `/*` or `*`, which is skipped (a comment's line, or a line of code so led, such as an import's `* as h`
    continuation). Either way it ends at the line whose `from` string or side-effect specifier the gate reads, or at a line that
    ends with `;` outside a string and a comment (_js_code). A comment between `from` (or a side-effect `import`) and its specifier
    is read by neither the gate nor the binding patterns: in served text a client through it is no site and no line whatever the
    module, `https`, `net` and `tls` included, and a package outside KNOWN_JS_IMPORTS passes the gate; in a walked file the webview
    leg's pin reds it. Every specifier the forms loop reads is recorded as (file, line, specifier) in res.reads, and every walked
    line where the second refusal below fires, excused or not, as (file, line) in res.unread: the --js-reads mode (js_reads) hands
    both to the webview leg's pin, which holds them to a TypeScript parse of the walked files. Two refusals ride the JavaScript
    lines, each excused only by JS_ALLOW: first, a family module's specifier the gate reads that no counted binding and no arm
    reads (_specifier_read), wherever the gate reads, and in a walked file a binding the patterns match whose specifier stands
    on a line led by `//`, `/*` or `*`, which the line reader skips (_comment_bindings), refused as a binding on a line led by
    `//`, `/*` or `*`, whose module the gate does not read (the pin's parse sees such a binding when the line is code, an
    import's `*`-led continuation, and none on a comment line or in a template literal's text); second, in a walked file
    (not served text), a require or import the gate cannot read (_js_unread_requires)."""
    tools, any_tool, comment = (JS_RX, JS_ANY, ("//", "*", "/*")) if kind == "js" else (SH_RX, SH_ANY, ("#",))
    if dom is None: dom = _browser_text(rel, kind)
    cp = _cp_bindings(text) if kind == "js" else None
    nb = _net_bindings(text) if kind == "js" else None
    first, starts = base + 1, None   # the text's first line number; its line offsets (_line_starts), made at the first family specifier
    stmt = False   # an import or export statement that begins its own line has no specifier yet and has not ended (_js_specifiers's `cont`)
    held = (_comment_bindings(text, [m for m in FAMILY if m in nb["read"] or m == _CP_NAME and cp is not None and _names_module(text, _CP_PATTERNS)])
            if kind == "js" and not served else {})   # a walked file's bindings on lines led by //, /* or *, refused below
    tail = text.splitlines(True)[-1] if cut and text else ""
    last = base + len(text.splitlines()) if tail and tail.splitlines() == [tail] else None   # a last line the joined text carries on
    for i, ln in enumerate(text.splitlines(), base + 1):
        s = ln.strip(); live = ln; seen = set()
        if s.startswith(comment) and not served:   # served text: a joined constant is one line whatever it starts with, never a comment
            for col, mod, expr in held.get(i - first + 1, ()):   # a binding the patterns read where the gate reads no module: refused by name
                _js_refuse(res, rel, i, col, expr, "IMPORT %s:%d names %s in %s, a binding on a line led by //, /* or *, whose module the gate does not read: "
                           "bind the module on a line the gate reads, or name the place in JS_ALLOW with its reason" % (rel, i, mod, expr[:80]))
            continue
        if kind == "sh" and s.startswith(("echo ", "print(")):   # a printed remedy is not a request: only what follows the printed text
            live = _live_remainder(s[5:] if s.startswith("echo ") else s[6:])   # live (_live_remainder) is scanned, and a line with nothing live is skipped
            if not live.strip(): continue
        if kind == "js":
            forms = _js_specifiers(s, served, stmt)
            said = any(f.re is _JS_FROM or f.re is _JS_SIDE_EFFECT for f in forms)
            if (_JS_STATEMENT if served else _JS_OPENS).match(s): stmt = not said and not _js_code(s).rstrip().endswith(";")   # begun here, and not ended on its line
            elif stmt and (said or _js_code(s).rstrip().endswith(";")): stmt = False   # its specifier read, or a statement ended with no `from`
            for f in forms:
                res.reads.append((rel, i, f.group(2)))
                pkg = _js_package(f.group(2))
                if pkg and pkg not in KNOWN_JS_IMPORTS:
                    res.problems.append("IMPORT %s:%d imports %s, a package the census does not know: a client that opens connections or starts programs "
                                        "takes its primitives into JS or the child_process family; either way add it to KNOWN_JS_IMPORTS with the reason" % (rel, i, pkg))
            for f in forms:   # a family module's specifier: read by a counted binding or an arm, else refused by name
                mod = _js_package(f.group(2))
                if mod not in FAMILY: continue
                if starts is None: starts = _line_starts(text)
                off = len(ln) - len(ln.lstrip())
                if not _specifier_read(mod, starts[i - first] + off + f.end(), ln, off + f.start(), off + f.end(), cp, nb):
                    _js_refuse(res, rel, i, off + f.start(), f.group(0),
                               "IMPORT %s:%d names %s in %s, and no binding the patterns count takes the module there and no call the census reads "
                               "goes through it: bind the module whole or by names in a shape the patterns read, or name the place in JS_ALLOW "
                               "with its reason" % (rel, i, mod, f.group(0)))
            if not served:   # walked files only: a require or import the gate cannot read
                for col, what, expr in _js_unread_requires(ln):
                    res.unread.append((rel, i))
                    _js_refuse(res, rel, i, col, expr,
                               "IMPORT %s:%d spells a require or import the import gate cannot read (%s: %s): require a module as "
                               "require(\"<module>\") or import(\"<module>\"), the quote right after the paren, or name the place in JS_ALLOW "
                               "with its reason" % (rel, i, what, expr[:80]))
            for fn, at in _cp_sites(ln, cp):   # a program site, classed by its argv as Scan.visit_Call classes a Python command
                if i == last and _runs_off(ln, at, comma=False): continue   # its arguments carried on in the joined text, read there
                head, sub, follow, shell = _js_argv(fn, ln[at:])
                tool, road, cls = fn, T.get("%s:%s" % (rel, fn)), None
                base = os.path.basename(head) if not head.startswith("RUNTIME-SUPPLIED") else head
                interp = base in INTERPRETERS or base.startswith("python")
                external = interp or shell or head.startswith("RUNTIME-SUPPLIED") or (head == "git" and not sub)
                if shell: head += " SHELL"
                if interp and follow.startswith("-"): head += " " + follow
                if external: cls = "runtime-program" if road in RUNTIME_ROADS else "external-program"
                if fn == "execFile" and 'execFile("bash"' in ln: tool, road = "install.sh", T.get(rel + ":install.sh")
                res.emit(rel, i, tool, (head + " " + sub).strip(), "-", road, cls, kind)
        else:
            for m in SH_INTERPRETER.finditer(live):   # the interpreter arm: keyed file plus tool, external-program by class
                tool = "%s %s" % (os.path.basename(m.group("head")), m.group("flag"))
                res.emit(rel, i, tool, s[:70], "-", T.get("%s:%s" % (rel, tool)), "external-program", kind)
        if any_tool.search(live):   # the list's alternation (_compiled): a miss means no tool below matches, so the loop is skipped
            for tool, rx in tools:
                if served and tool in ("fetch", "import()"):   # served text: every match on the line, each placed by its own argument
                    opener = "import(" if tool == "import()" else "fetch("
                    for m in rx.finditer(live):
                        if i == last and _runs_off(live, m.end()): continue   # its argument carried on in the joined text, read there
                        arg = _call_arg(live, opener, m.end() - len(opener)); road, cls = T.get("%s:%s" % (rel, tool)), None
                        if tool == "fetch":
                            fc = _fetch_class(arg, served); head = "fetch(%s)" % arg[:60]
                            if fc == "local": road = "local-kernel"
                            elif fc == "computed": cls = "browser-computed-url"
                        elif arg[:1] in ("'", '"', "`") and "${" not in arg: continue   # a literal specifier is an import (gated above)
                        else: cls, head = "browser-computed-url", "import(%s)" % arg[:60]
                        seen.add(tool); res.emit(rel, i, tool, head, "-", road, cls, kind)
                    continue
                if rx.search(live):
                    road, cls, head = T.get("%s:%s" % (rel, tool)), None, s[:70]
                    if tool == "fetch":   # placed by its URL: the argument is what the listing shows
                        arg = _call_arg(live, "fetch("); fc = _fetch_class(arg, served); head = "fetch(%s)" % arg[:60]
                        if fc == "local": road = "local-kernel"
                        elif fc == "computed": cls = "browser-computed-url"
                    if tool == "import()":   # a literal specifier is an import (gated above), a computed one a site of the class
                        arg = _call_arg(live, "import(")
                        if arg[:1] in ("'", '"', "`") and "${" not in arg: continue
                        cls, head = "browser-computed-url", "import(%s)" % arg[:60]
                    seen.add(tool); res.emit(rel, i, tool, head, "-", road, cls, kind)
        for tool in _net_sites(live, nb):   # the connection family through the file's bindings: a tool the literal list named on this line is counted once
            if tool not in seen: res.emit(rel, i, tool, s[:70], "-", T.get("%s:%s" % (rel, tool)), None, kind)
        if dom and DOM_ANY.search(ln):
            for name, rx in DOM_RX:
                if rx.search(ln): res.dom.append((rel, i, name, s[:70])); break


_TEXT_CALLS = ("format", "join", "replace", "strip", "lstrip", "rstrip")   # a call on a text receiver: the receiver and the arguments are text
_FOLLOW_ANY = ("encode", "format_map")                                     # a receiver followed whatever it is: its text is the page's
_READ_CALLS = ("read_text", "read")                                        # a file read bound to a page's slot
# The calls that write their receiver: on a module name, a write after its binding (a run-time memo, Result.writes); on a local
# container, their arguments are the container's values too (_Served._locals)
_MUTATORS = ("update", "setdefault", "append", "extend", "insert", "pop", "popitem", "clear", "add", "discard", "remove")
# The dunder spellings of a write (`X.__setitem__(k, v)`), and the container types whose method called on the type writes its first
# argument (`dict.update(X, ...)`, `list.append(X, v)`, `collections.OrderedDict.__setitem__(X, k, v)`), as Scan.dotted spells them: a
# call of either kind is a write of that module name (Result.writes), as a mutating method call on it is
_DUNDER_MUTATORS = ("__setitem__", "__delitem__", "__ior__", "__iadd__", "__isub__", "__iand__", "__ixor__", "__imul__")
_CONTAINER_TYPES = frozenset(("dict", "list", "set") + tuple("collections." + t for t in (
    "OrderedDict", "defaultdict", "Counter", "deque", "ChainMap", "UserDict", "UserList")))
_FOLD_CAP = 10 ** 6   # the longest text _Served._const_text folds a join to, a million characters, as _too_wide bounds a field
_TOO_LONG = object()   # _Served._fold's answer for a join whose parts fold and whose own folded text may run past _FOLD_CAP


def _pct_fields(fmt):
    """The conversions of the `%` format string `fmt` as Python's str % parses it (unicode_format_arg_parse in
    Objects/unicodeobject.c), each (the width's digits, the precision's digits, the conversion character), which _const_text and
    _wide bound: a `%`, then a mapping key read to the close parenthesis that balances its open one, nested pairs counted (R3 of the
    eleventh round's review, extra9-4: a key read to the first close parenthesis hid the width of `%(a(b)c)2000000s`), then the
    flags `-+ #0` (a width's leading zeros among them), a width of digits or `*`, a `.` and a precision of digits or `*` (a `*`
    giving no digits: its value is an argument, which a fold of string constants cannot supply), a length modifier `h`, `l` or
    `L`, and the conversion character, `%%` being the conversion that writes a literal percent. ValueError where Python refuses
    the format itself: a key with no close parenthesis to balance it, or a conversion the format's end cuts off."""
    out, i, n = [], 0, len(fmt)
    while True:
        i = fmt.find("%", i) + 1
        if not i: return out
        if i < n and fmt[i] == "(":   # a mapping key, to the close parenthesis that balances it
            depth, i = 1, i + 1
            while depth and i < n:
                depth += (fmt[i] == "(") - (fmt[i] == ")"); i += 1
            if depth: raise ValueError("incomplete format key")
        while i < n and fmt[i] in "-+ #0": i += 1   # the flags
        spec = []
        for dot in (False, True):   # the width, then the precision after its dot
            if dot:
                if i >= n or fmt[i] != ".": spec.append(""); continue
                i += 1
            j = i
            if i < n and fmt[i] == "*": i += 1; j = i
            else:
                while i < n and "0" <= fmt[i] <= "9": i += 1
            spec.append(fmt[j:i])
        if i < n and fmt[i] in "hlL": i += 1   # a length modifier, which Python ignores
        if i >= n: raise ValueError("incomplete format")
        out.append((spec[0], spec[1], fmt[i])); i += 1


# The constants the served pass refuses in a page, by type, each with the reason its SERVED line gives: a str is text it reads,
# and None, a bool, an int and the empty bytes are value slots (_Served.resolve)
_CONSTANT_KINDS = {bytes: "a non-empty bytes Constant", float: "a float Constant", complex: "a complex Constant", type(...): "an Ellipsis Constant"}


def _int_arith(e):
    """Whether e is an int constant, or a Mult or LShift whose operands are each one or such a BinOp (`2 * 1024`, `1 << 20`): the
    only arithmetic the served pass takes as a value slot, the kinds and roles the kernel's pages use."""
    if isinstance(e, ast.Constant): return type(e.value) is int
    return isinstance(e, ast.BinOp) and isinstance(e.op, (ast.Mult, ast.LShift)) and _int_arith(e.left) and _int_arith(e.right)


def _value_slot(e):
    """Whether e is a kind resolve reads as a value slot of its own: a None, bool or int constant, the empty bytes constant, or a
    Mult or LShift over int constants (_int_arith). Read as no text; one that stands directly as the right operand of a `%` (bare,
    a tuple element or a dict literal's value), a `.format` argument or a value of the dict literal a `.format_map` is handed is
    refused by name whether or not a conversion takes it (_Served._format_slots), since a conversion can turn it into characters
    (`%c`, `%x`, `{:c}`, `%.1s` over the empty bytes), and one held deeper there is read as a value slot."""
    if isinstance(e, ast.Constant): return e.value is None or type(e.value) in (bool, int) or type(e.value) is bytes and e.value == b""
    return isinstance(e, ast.BinOp) and _int_arith(e)


def _unbound_text_call(e):
    """Whether e is a call of join, format, format_map or replace on the name str, bytes or bytearray (`str.join("", [...])`),
    keyed on that spelling whether or not a binding shadows the name. _Served._const_text folds such a method only when it is
    called on a string constant or on a join it folds, so this spelling is refused by name: in a page by the served pass
    (_UNBOUND, as a value, as a receiver's or a container's base, or through a text method called on it), and where a run-time
    lookup by name takes it as the key as a run-time form (Scan.ns_string), rather than read piece by piece in a page and not at
    all in a lookup position."""
    return (isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr in ("join", "format", "format_map", "replace")
            and isinstance(e.func.value, ast.Name) and e.func.value.id in ("str", "bytes", "bytearray"))
# The served pass's allowlist, keyed on the code and never a line number: ("file:function", the expression as ast.unparse spells
# it) -> (the number of places the entry covers, the reason). A route candidate whose content type the census cannot resolve, a
# call of a `_send` its file binds more than once outside function bodies, or other than by one def statement, or rebinds under a
# `global` declaration in a function or a class body, a call of a decorated `_send`, and a bare call of a `_send` a scope around
# the call binds or in a module that holds a star import (each keyed on the call's function, `self._send` or `_send`), a reference to
# `_send` other than a call the scan reads (a read of it that is not a call's function, a store or delete of an attribute so named,
# or a string equal to `_send`), a script-running type written outside `_send`, a response
# answered outside `_send` with no Content-Type header, a container the module writes at run time, a receiver or container the
# pass does not read, a callee the pass does not follow, a bare module name the pass does not read, a name the page function's
# scope binds in a form the pass refuses, and a file a page reads that the walk does not scan are each a SERVED line unless named
# here (a route whose body the census does not read is not
# excused here: it is passed as the call's second positional argument or refused); an entry that names nothing in the run, or
# covers a different number of places (distinct source positions), is a SERVED ALLOW line, so a new place under an entry's key
# is read or named, never excused by it.
SERVED_ALLOW = {
 ("kernel/kernel.py:Handler.do_GET", "ct + '; charset=utf-8'"): (2,
  "the /dist and /media branch, files from disk typed by their suffix: /dist serves the bundles esbuild builds from three sources, "
  "none of it read as served text: the scanned ui and vscode-extension/src sources; the vendor/track-changents files they import, "
  "directly or through each other, which the walk does not read (engine.js, display.js, obsidian/src/track-cm.js and "
  "obsidian/src/track-logic.js); and the node_modules packages KNOWN_JS_IMPORTS names, together with the packages those depend "
  "on (text/javascript). /media serves vscode-extension/media, which the walk does not read: the repository's own fonts, pictures "
  "and SVG icons (image/svg+xml); neither is read as served text"),
 ("kernel/kernel.py:Handler._file_preview", "mime"): (4,
  "the user-file arm of /file (the GET, its HEAD reply and its range reply): a file on this machine that a session or the user "
  "names, typed from _PREVIEW_MIME (pictures, image/svg+xml among them, and application/pdf) or as text/plain; an .svg opened in "
  "its own tab is a document under Content-Security-Policy: sandbox, and the loads its markup names are the .svg tab row's"),
 ("kernel/kernel.py:Handler._file_slice", "ctype"): (1,
  "the file preview's slice: every return of _slice_body types its answer application/json or text/plain"),
 ("kernel/kernel.py:Handler._remote_file", "ctype"): (3,
  "the /remote/<host>/file relay (the GET, its HEAD reply and its range reply): an attached machine's file, typed by this kernel "
  "for the requested path as the user-file arm types it (image/svg+xml among them), under the same sandbox"),
 ("kernel/kernel.py:Handler._remote_file", "resp.read(_MEDIA_MAX_BYTES + 1)"): (1,
  "the relay's reply from the attached kernel, a file's bytes or its refusal, which the too-large page reaches only as its message "
  "and escapes (_too_large_page's _html_esc): no markup of its own reaches the page"),
 ("kernel/kernel.py:Handler._remote_file", "_remotes.get(host)"): (1,
  "the attached-host registry, written as hosts attach and detach: the relay reads the tunnel's port and the attached kernel's "
  "token from it and stores that token in the query map it forwards (q['token']); the too-large page reads only the path and the "
  "session id from that map (_too_large_page), so no value of the registry reaches the page"),
 ("kernel/kernel.py:Handler.do_OPTIONS", "self.send_response(204)"): (1,
  "the CORS preflight's answer: a 204 with no body, so nothing for a browser to type"),
 ("kernel/kernel.py:Handler._ws", "self.send_response(101)"): (1,
  "the websocket upgrade: a 101 with no body; what follows is the socket's frames, not a page"),
 ("kernel/kernel.py:_gear_glyph", "_gear_glyph_memo['glyph']"): (1,
  "a run-time memo: the gear's character, read from ui/webview/icons.ts, a walked file"),
 ("kernel/kernel.py:_timeline_axis_js", "_TIMELINE_AXIS_MEMO[0]"): (1,
  "a run-time memo: the axis formatter lifted from ui/romp-timeline-view.js, a walked file"),
 ("kernel/kernel.py:_code_ident", "_CODE_IDENT[0]"): (1,
  "a run-time memo: the identity of the kernel code this process runs, a hash of the tree's files (a lab names one in "
  "ROMP_CODE_IDENT in its place); no page text"),
 ("kernel/kernel.py:_kernel_sha", "_SHA"): (1,
  "a run-time memo: the git short sha of the code the kernel runs, which /sw.js reaches through _sw_version, the function declaring "
  "the name `global` so the module's binding is read; the kernel's own build sha, not page data, and no page text"),
 ("kernel/kernel.py:_pin_dir", "_MENTION_PINS"): (1,
  "a run-time memo: the directory under the kernel's state root that holds the mention pins (jd.STATE / \"mention-pins\"), which "
  "the too-large page's message reaches through a pinned file's path (_file_preview's `_pin_dir() / pin`, a path join the pass "
  "reads through both operands) and escapes (_too_large_page's _html_esc); a path on this machine, no page text"),
 ("kernel/kernel.py:_names_parts", "(NAMES / str(sid)).read_text()"): (1,
  "the names registry, runtime session data (a session's working directory and tab fields), which the too-large page's message "
  "reaches through the path it names (_resolve_open_path, _cwd_of); it holds no page text"),
}
# The served pass's listed refusals (the reviewer's 16:33Z ruling, E2, on the precedent of his 04:52Z ruling for the relay's query
# map): a method call the method allowlist refuses (_Served._undrawn) whose page is honest, keyed as SERVED_ALLOW's entries are,
# ("file:function", the expression as ast.unparse spells it) -> (the number of places the entry covers, the reason). Such a place is
# not excused: it is listed, one line per place with its reason, after the stylesheets the listing names (render_sites), where
# SERVED_ALLOW's places are not listed; an entry that names nothing in the run, or covers a different number of places (distinct
# source positions), is a SERVED LISTED line, as a stale SERVED_ALLOW entry is.
SERVED_LISTED = {
 ("kernel/kernel.py:_pane_label", "str(app or '').capitalize()"): (1,
  "a .capitalize() method whose return is not drawn from its receiver's text, on str() of the pane label's parameter: the seven "
  "page routes that call _shim pass constant lowercase pane keys, _shim_core_js passes its own parameter (default \"test\"), and "
  "_pane_label capitalizes a key _PANE_ORDER does not name"),
}
# The `_send` definitions that answer no HTTP request: each writes a frame to a session host's Unix socket, so a call to one is no
# route and has no content type. A `_send` definition a call reaches that writes no Content-Type header and is not named here is
# a SERVED line; an entry no call reaches is a SERVED ALLOW line, as a stale allowlist entry is.
FRAME_WRITERS = {
 "kernel/session_host.py:SessionHost._send": "the session host's frame to the kernel on the host's Unix socket",
 "kernel/host_transport.py:HostTransport._send": "the kernel's frame to a session host on that host's Unix socket",
}


def _header(n):
    """The parts of a def's, a class's or a lambda's header that run in the scope that defines it, so a walrus there binds that
    scope's name: a def's decorators, its positional and keyword-only defaults, every argument's annotation (`*args` and `**kwargs`
    included) and the return annotation; a class's decorators, bases and keyword values; a lambda's defaults. Everything but the
    body."""
    if isinstance(n, ast.ClassDef): return n.decorator_list + n.bases + [k.value for k in n.keywords]
    a = n.args
    parts = list(a.defaults) + [x for x in a.kw_defaults if x is not None]
    if isinstance(n, ast.Lambda): return parts
    parts += [x.annotation for x in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if x is not None and x.annotation is not None]
    return n.decorator_list + parts + ([n.returns] if n.returns is not None else [])


def _scopes_of(defs):
    """(parameters, single-name bindings, names bound another way) per enclosing function, innermost first: the scopes a content
    type's names are resolved in. A nested def's, class's or lambda's header is read as the function's own statements (a walrus
    there binds the function's name another way), and its body is not. A name bound another way is any other binding form: a store
    or delete of the name, an except name, a match capture or a match mapping's rest, an import, a def or class statement, and a
    global or nonlocal declaration (layer i of the eleventh round's rulings: only a store binds, in every form)."""
    out = []
    for d in reversed(defs):
        if isinstance(d, ast.ClassDef): continue
        a = d.args
        params = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs} | ({a.vararg.arg} if a.vararg else set()) | ({a.kwarg.arg} if a.kwarg else set())
        single, other, stack = {}, set(), list(d.body)
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): other.add(n.name); stack.extend(_header(n)); continue
            if isinstance(n, ast.Lambda): stack.extend(_header(n)); continue
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                single.setdefault(n.targets[0].id, []).append(n.value); stack.append(n.value); continue
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None:
                single.setdefault(n.target.id, []).append(n.value); stack.append(n.value); continue
            if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)): other.add(n.id)
            elif isinstance(n, ast.ExceptHandler) and n.name: other.add(n.name)
            elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name: other.add(n.name)   # a match capture: `case X:`, `case ... as X:`, `case [*X]:`
            elif isinstance(n, ast.MatchMapping) and n.rest: other.add(n.rest)   # a match mapping's rest: `case {**X}:`
            elif isinstance(n, (ast.Import, ast.ImportFrom)): other.update((x.asname or x.name).split(".")[0] for x in n.names)
            elif isinstance(n, (ast.Global, ast.Nonlocal)): other.update(n.names)
            stack.extend(ast.iter_child_nodes(n))
        out.append((params, single, other))
    return out


_CONSTS = weakref.WeakKeyDictionary()   # a module's tree -> (its _module_consts, its _module_bound, its _module_info): routes_of and the served pass read them once per tree
_STAR = "a module name a star import may rebind"
_IN_BLOCK = "a module name bound once inside a module-level block, not by a top-level import, def or class statement"
_IN_BLOCK_BODY = "a module name bound once inside a module-level block, not by a top-level statement"
_ASSIGN_FORM = "a module name bound by an annotated, unpacking or chained assignment, which the census does not read as a constant"
_ANNOTATED = "a module name annotated at module level beside its assignment"
_GLOBAL_ONLY = "a module name no module-level statement binds, bound at run time under a global declaration"
_SUPER = "a call of super(), whose methods are a base class's, which the census does not follow"
_COMPUTED = "a module name in a file that writes its module namespace through a computed name"
_FILE_BOUND = "__file__, which a statement of the file binds"
_SHADOWED = "a builtin in a file that may rewrite the builtins"
_ENCLOSED = "a definition inside a function, whose scope the census does not read"
_LAMBDA = "a lambda around the call, whose scope the census does not read"   # routes_of: a `_send` call, or a Content-Type write outside `_send`, inside a lambda
_TYPE_REBOUND = ("a definition that binds %s, the parameter its own Content-Type write names, other than as that parameter (%s), so the "
                 "type it writes need not be the call's")   # routes_of: a `_send` call refused before any typing (_type_rebinding)
_NOT_SELF = "a receiver the census does not prove self by binding (%s)"   # routes_of: a `<name>._send(...)` call in a class body whose receiver fails the proof (_self_receiver; layer iii of the eleventh round's rulings)
_IMPORT_NAMES = frozenset(("__doc__", "__name__", "__package__", "__spec__", "__loader__"))   # the names the import system binds in every module: no builtins to the served pass
_IMPORT_WHY = "a name the import system binds in every module"
_SELF_ATTR = "an attribute read on self, which any code may set before the call"   # an attribute of self as a value, a receiver or a container
_CLASS_ATTR = "a class attribute, which the census does not read as page text"   # _Served._class_root's refusal
_PARAM_ATTR = "an attribute read on a parameter, which any code may set before the call"   # _Served._attr_root's, on any other parameter
_EXCEPT_ATTR = "an attribute read on an except name, which the code that raised it sets"   # _Served._attr_root's, on an except name
_METHOD_CALL = ("a route class's method called other than on the calling method's own first parameter, which the census does not "
                "follow")   # _Served._method_call's, on self through anything else, on any other parameter or on a name spelled self
_SELF_METHOD = ("a method called on self that no def statement of a class of the file defines first in the route class's method "
                "resolution order, which the census does not follow")   # _Served._method_call's, where _definer finds no def to follow
_DECORATED = ("a callee whose def statement carries a decorator, staticmethod and classmethod among them, whose return Python calls "
              "in its place, which the census does not follow")   # _Served._def_shape's, the follow proof's decorator conjunct (layer ii)
# The follow proof's other conjuncts (_Served._def_shape, _Served._def_uses; layer ii of the eleventh round's rulings): a callee the census follows is a
# plain def statement, bound once, with no decorator (_DECORATED), a def and not an async def, no yield in its own body, its name
# read nowhere in the file but as a call's callee and spelled by no string constant, never rebound; any other callee refuses by name
_DEF_ASYNC = "a callee an async def statement defines, whose call returns a coroutine, not its return, which the census does not follow"
_DEF_YIELD = "a callee whose def statement's body yields, whose call returns a generator, not its return, which the census does not follow"
_DEF_ALIAS = ("a callee whose name the file reads other than as a call's callee (an alias, an argument, a store or a delete of it or of "
              "one of its attributes among them), which the census does not follow")
_DEF_STRING = "a callee whose name a string constant of the file spells, which a lookup by name may reach, which the census does not follow"
_LAMBDA_VALUE = "a lambda reached through a name's value, a callee no def statement defines, which the census does not follow"   # resolve's and _defaults's
_FUNC_OBJECT = "a function or class object"   # _scoped's and _base's reason for such a name read as a value, refused wherever it stands
# resolve's reasons for a yield, a yield from and an await read as a page value: each evaluates to a value other than its operand (what
# the generator is sent, what the delegated iterator returns, what the awaited object returns), which the census does not read
_NOT_OPERAND = {ast.Yield: "a yield, whose value is what its generator is sent, not its operand",
                ast.YieldFrom: "a yield from, whose value is what the iterator it delegates to returns, not its operand",
                ast.Await: "an await, whose value is what the awaited object returns, not its operand"}
_METHOD_SUBCLASS = ("a method called on self, which a subclass another file defines may override with code the census does not "
                    "read")   # _Served._method_call's, the one outcome of the follow arm on self (choice 4 of the eleventh round's rulings)
_METHOD_UNPLACED = ("a method called on self that a class statement of the file defines whose bases the census cannot place, which may "
                    "derive from the route class and override it")   # _Served._file_override's, on a class statement it cannot place
_METHOD_STORED = ("a method called other than on the calling method's own first parameter whose name the file stores, deletes or names "
                  "to a setter as an attribute, which may bind it on a route class or its instance")   # _Served._method_call's
_UNCLASSIFIED = ("a call of, or a method called on, the first parameter of a route handler that carries a decorator or stands in a file "
                 "that binds staticmethod or classmethod, which the census does not take for self, the class or any other "
                 "parameter")   # _Served._method_call's and _scoped's, on the mark _ctx sets (_Unclassified)
_METHOD_OVERRIDE = ("a method called on self that a file class deriving from the route class overrides, whose override the server would "
                    "run, which the census does not follow")   # _Served._method_call's, where a file subclass defines the name
_REPLACED = ("a method called on self whose name the file stores or deletes as an attribute or names as a string to setattr, delattr, "
             "__setattr__ or __delattr__, or whose route class's method resolution order binds __getattribute__, so code may replace it "
             "at run time")   # _method_call's
_REPLACED_OPEN = ("a method called on self in a file that hands setattr, delattr, __setattr__ or __delattr__ an attribute name the census "
                  "does not fold to a constant string, or reaches one of them other than by a call, so code may replace it at run "
                  "time")   # _method_call's, the fail-closed setter read (_Served._setters_open; choice 12 of the eleventh round's rulings)
_SETTERS = ("setattr", "delattr", "__setattr__", "__delattr__")   # the calls _Served._replaced reads a method's name from as a string
# Layer v of the eleventh round's rulings, a file a served page reads at run time: read (a file the walk scanned as browser text, _browser_text), named (a
# stylesheet the walk does not scan), or refused by name. _path's refusal where it cannot prove the path it reads, the clause naming
# the conjunct that fails; and the refusal of a file the walk scanned other than as browser text, by the kind the walk scanned it as
_PATH_UNPROVEN = "a path the census does not prove by binding (%s)"
_FILE_KINDS = {"py": "a file the walk reads as Python, not as browser text", "sh": "a file the walk reads as shell, not as browser text",
               "js": "a file the walk reads as JavaScript outside the browser and editor roots, with the DOM arm off"}
# A page's read of a walked browser-text file counts as covered only because the walk scanned that file once as UTF-8 (scan, encoding
# "utf-8"), so a page that reads it with an encoding the census does not read as one of _UTF8_NAMES may reveal a fetch the UTF-8 scan
# did not: such a read is refused by name (served_texts, _read_codec). A `**` keyword to `.read_text` may name the encoding in a mapping
# the census cannot read, so it counts as an encoding named and unread and is refused too, on the safe side (the reason names the form:
# a codec the census does not read as utf-8). A read that names no encoding takes the locale's default, which
# the census cannot prove is UTF-8; refusing it is not 0 live (a live page reads a walked .js with no encoding), so it is the stated
# limit, its witness the (u7) plant u7c
_READ_CODEC = ("a walked browser-text file a page reads with an encoding the census does not read as utf-8, utf_8 or utf8, so the "
               "walk's one UTF-8 scan of it may not be the text the page serves")
_SLICED = "a subscript by a slice or an index other than a constant, whose result the census does not compute"   # _Served._carries_text's refusal
_SLOT_FORMAT = "a value slot a % or a format call takes, which a conversion can turn into characters"   # _Served._format_slots's refusal
_SUB_OPERAND = ("a subscript as an operand of +, %, an f-string, .join, .format, .format_map or .replace, whose joined text the census does "
                "not compute")   # _Served._sub_operand's
_BUILTIN_OTHER = "a builtin other than the seven a page may call (str, int, dict, max, float, getattr, chr)"   # _Served._base's refusal
_STR_DECODE = ("str with more than one positional argument, a starred argument or a keyword other than object, which may decode its "
               "first argument")   # _Served._base's refusal
_MAX_ONE = ("max handed one iterable or a starred argument, which returns an element its argument holds, whose join with the text "
            "beside the call the census does not compute")   # _Served._base's refusal (the 00:28Z default, one check at 0 live)
_UNBOUND = "a join, format, format_map or replace called on the name str, bytes or bytearray, which the census does not fold"   # _unbound_text_call's
_JOIN_SET = "a join over a set, or over a value the census reads from one, whose order is not fixed"   # resolve's, at _Served._set_value
_WIDE = "a format field wider than a million characters, which the census does not expand"   # _Served._wide's refusal
_NESTED = "a format spec holding a replacement field, which the census does not expand"   # _Served._nested's refusal
_LONG = "a join whose folded text may run past a million characters, which the census does not expand"   # _Served._long's refusal (R3)
_FIELD_REACH = ("a replacement field reaching an attribute or an index of its argument, which the census does not "
                "read")   # _Served._field_reach's refusal
_TEMPLATE = ("a format string reached other than as a string constant, a join of them or a name bound to one, whose fields the "
             "census does not read")   # _Served._field_reach's refusal where no field it reads reaches
# The seven builtins a page may name (_Served._base, as a callee, a receiver's base or a bare name), each for what its result is;
# any other builtin in a page is refused by name (_BUILTIN_OTHER). int and float give a number, and a call of either that is the
# builtin is a leaf whose argument resolve does not read, save where the call is a base (_NUMBER_LEAVES, below); dict gives its
# arguments' keys and values; str
# gives its argument's text or a value's printed form (handed more than one positional argument, a starred argument or a keyword
# other than object, any of which may be an encoding or an errors argument that decodes its first, it is refused by name:
# _STR_DECODE); max gives one of its arguments, and handed one iterable or a starred argument, when it returns an element its
# argument holds, whose join with the text beside the call the census does not compute, it is refused by name (_MAX_ONE: the
# 00:28Z default, one check at 0 live, since no live page reaches such a call, the kernel's one call of max, over a generator of
# file times in _dist_ver, standing inside int's argument, which resolve does not read). getattr and chr give text their arguments
# do not hold, each under the stated limit (text a call computes from its arguments is not read); each passes because the
# kernel's pages call it (a getattr of an attribute; chr in the replacement function of a re.sub), a witness of that stated limit.
_PAGE_BUILTINS = {"str": "its argument's text, or a value's printed form (with more than one positional argument, a starred "
                         "argument or a keyword other than object, refused: _STR_DECODE)",
                  "int": "a number: a leaf, its argument not read unless the call is a base",
                  "float": "a number: a leaf, its argument not read unless the call is a base",
                  "dict": "a mapping of its arguments' keys and values",
                  "max": "one of its arguments (handed one iterable or a starred argument, refused: _MAX_ONE)",
                  "getattr": "an attribute of its first argument, not its arguments' text: the stated limit",
                  "chr": "the character a code point names, not its argument's text: the stated limit"}
# A call of int or float that is the builtin is a number-valued leaf (the eleventh round's rulings, the reviewer's 14:42Z ruling):
# resolve's Call arm reads none of its argument where it reads the call as text (the page, a piece of it or a call's argument),
# since what it returns is an int or a float, whose text is digits or float's fixed
# texts (inf and nan among them) and carries no host. The leaf rests on the builtin's return, which the census does not read: an
# __int__ or an __index__ that returns an int subclass, or a __float__ that returns a float subclass, whose __str__ or __format__ is
# overridden is the stated limit's shape, reached only by such an escape (its witness lfw, an __int__), and on the interpreters the
# census runs on (3.10, 3.12 and 3.14t) the builtin copies such a return to an exact int or float, with a DeprecationWarning, so the
# witness serves its digits. A call
# of either name bound any other way (an assignment, an import, a parameter, a def, a class or a global declaration, in the file or
# a scope around the call, or a file that may rewrite the builtins) is refused by name (_NUMBER_REBOUND), its arguments read as the
# other arms read them. A method called on such a call is read as on any base whose own text the pass does not read (receiver):
# one drawn from its receiver's text keeps the call limit, its arguments read (_chain_args), and any other refuses by name.
_NUMBER_LEAVES = ("int", "float")
_NUMBER_REBOUND = "a call of int or float bound other than to the builtin, whose return may be any text, not a number"   # resolve's
# The text-method arm's shapes (the eleventh round's rulings: the reviewer's 14:42Z item 2, and his 16:33Z E1 and E3): a .replace,
# .format, .join, .format_map or .encode in a shape _const_text does not fold is refused by name (_text_shape gives the clause), never
# read as its receiver's text
_TEXT_SHAPE = "a .%s() call %s, whose text the census does not compute"   # resolve's, the clause from _text_shape
# the encodings an .encode may name (_text_shape): a string constant that, lower-cased, is one of these three, each of which CPython's
# str.encode encodes as UTF-8 itself, before any codec lookup; every other encoding refuses by name: another spelling Python also
# encodes as UTF-8 (utf 8, UTF--8) on the safe side, one it hands to the codec registry (u-t-f-8, U_T_F_8, utf-8-sig), where a search
# function the file registers may answer it (utf-8-sig the built-in search answers first, with a byte-order mark), and an encoding
# that is no string constant (a name bound to "utf-8" among them), which the census does not fold
_UTF8_NAMES = ("utf-8", "utf_8", "utf8")
_RUNTIME = "a module name in a file that %s, which may rewrite its namespace at run time"   # the form: _namespace_flags's "runtime"
_RUNTIME_BUILTIN = "a builtin in a file that %s, which may rewrite the builtins at run time"
_RUNTIME_ATTRS = ("__globals__", "__builtins__", "f_globals", "f_builtins", "f_locals")   # an attribute so named, on any receiver, reaches a namespace (arm ii)
_RUNTIME_NAMES = ("locals", "exec", "eval", "compile", "__import__", "import_module", "_getframe")   # the listed callables, a run-time form however ns_listed reaches one (arm ii)
_NS_WRITERS = ("globals", "vars")   # the computed-name writers, read by the computed-name rule however ns_listed reaches one
_NS_SETTERS = ("setattr", "delattr")   # the setters, a call of one ns_listed reaches read by the rule for a setattr or delattr on the module
_NS_READS = _NS_WRITERS + _NS_SETTERS   # the names whose read other than as a call's callee, as ns_listed reaches one, is a computed-name write
_LISTED_NAMES = frozenset(_RUNTIME_NAMES + _NS_READS)   # the names ns_listed reads by their own name (its first way)
_RUNTIME_ATTR_CALLS = ("exec", "eval", "locals", "__import__", "import_module", "_getframe")   # listed as an attribute on any receiver (ns_listed's third way)
_BUILTINS_ATTRS = ("compile",) + _NS_READS   # listed as an attribute on a builtins receiver alone (ns_listed's third way; re.compile is live)
_LISTED_FROM = {"builtins": ("locals", "exec", "eval", "compile", "__import__") + _NS_READS, "importlib": ("__import__", "import_module"),
                "sys": ("_getframe",)}   # the module an import binds each listed name from (ns_listed's second way)
_STRING_NAMES = _RUNTIME_NAMES + _NS_READS + _RUNTIME_ATTRS + ("__dict__",)   # a listed name spelled as a string, read only in a run-time lookup (arm iii)
_GETATTRS = ("getattr", "setattr", "delattr", "hasattr")   # arm iii's first position: the second argument of one of these
_TEXT_TYPES = ("str", "bytes", "bytearray")   # the text types, whose methods the lookup-key allowlist refuses however reached (Scan._key_form)
# The lookup-key allowlist's reasons for a name it refuses by its binding (Scan._key_binding, _key_form), each after the name
_KEY_BOUND = {"global": "which a function or a class body declares global, so the census does not evaluate it",
              "nonlocal": "which a scope of the file declares nonlocal, so the census does not evaluate it",
              "aug": "bound by an augmented assignment the census does not evaluate",
              "store": "which the file binds in a form the census reads no value through (a del, a match pattern or another store)",
              "novalue": "whose binding in its scope gives the census no value to read, so the census does not evaluate it",
              "classbody": "which a class body binds, so the census does not evaluate it",
              "lambda": "bound by a walrus in a lambda, which the census does not evaluate",
              "walrus": "bound by a walrus, which the census does not evaluate",
              "with": "bound as a with target, which the census does not evaluate",
              "none": "which no statement of the file binds, so the census does not evaluate it",
              "import": "bound by an import, which the census reads in a lookup key only as a receiver or a callee",
              "def": "bound by a def statement, which the census reads in a lookup key only as a callee",
              "builtin": "a builtin, which the census reads in a lookup key only as a callee",
              "class": "bound by a class statement, which the census does not read in a lookup key",
              "except": "bound by an except clause, which the census does not read in a lookup key",
              "mutable": "a list, set or dict module constant, which code may mutate, so the census does not evaluate it"}
_KEY_CONST = "a module constant %s, so the census does not evaluate it"   # Scan._key_const's reasons
_KEY_ATTR = "an attribute .%s as a loop's source %s, so the census does not evaluate it"   # Scan._key_attr's, in _key_form
# the one attribute the allowlist accepts as a loop or comprehension source, keyed by binding (Scan._spec_source, in _key_form):
# the file, the attribute name, and the base bound once at module level to the session-host module. Any other refuses (_KEY_SRC)
_SPEC_FILE, _SPEC_BASE, _SPEC_ATTR = "kernel/host_transport.py", "sh", "SPEC_FIELDS"
_KEY_SRC = ("an attribute .%s as a loop's source the census does not evaluate, accepted only as %s's %s.%s by binding"
            % ("%s", _SPEC_FILE, _SPEC_BASE, _SPEC_ATTR))
_KEY_SHUT = "spells a name by %s, which reads %s in a file that may rewrite %s, so the census does not evaluate it"   # _key_settle
# R1.5 (Scan.ns_string, _starred_key): a getattr-family or namespace-key call whose key position holds a starred value or whose
# arguments hold a ** mapping, the key read by position; and choice 3: a getattr-family name read other than as a call's callee (an
# alias, a partial's argument), by which a lookup's key is never seen; and choice 13: a namespace mapping used other than for a .get
# or an item read (Scan.visit_Module, _namespace_flags's nsuses): each a run-time form
_KEY_STARRED = "spells a name by a starred argument or a ** mapping in a lookup's key position, which the census does not evaluate"
_GETATTR_ALIAS = "names %s other than as a call's callee, so a lookup through it hands the census no key to read"
_NS_USE = "uses a namespace mapping other than in a key position the census reads"
_NS_NONE = {"computed": False, "builtins": False, "file": False, "deco": False, "runtime": None}   # _namespace_flags's answer for a file the walk did not read
def _namespace_flags(facts, stem):
    """{"computed": whether the file may write its own module namespace through a computed name, "builtins": whether it may write
    the builtins, "file": whether a statement of the file binds `__file__`, in any scope and by any form, "deco": whether one binds
    staticmethod or classmethod so, a star import among them (_Served._ctx), "runtime": the first form,
    with its line, by which the file may rewrite its module namespace or the builtins at run time, or None}, from what Scan's walk
    collected (Scan.ns_facts; Result.ns holds the answer per file). The file's namespace is written through globals() or vars()
    with no argument used any way but as the receiver of a `.get(...)` read (a subscript store, a mutating call, or an alias that
    could do either), through any use but a `.get(...)` read of the `__dict__` or the vars() of a module the file may be, through
    a store or delete of an attribute of such a module, or a setattr or a delattr on it, and through globals, vars, setattr or
    delattr read other than as a call's callee (`_g = globals`, `_s = setattr`), each of those four reached in the first three of
    Scan.ns_listed's ways below (`builtins.globals()`, `from builtins import vars as v`, `builtins.setattr(m, n, v)`). A module
    the file may be (module() below) is `sys.modules[k]` or `sys.modules.get(k)`, on any name or attribute spelled `modules`, or a
    call Scan.ns_listed reads as __import__ or import_module whose first argument is k (facts["importers"]), where k is no string
    constant, `__name__` among them, or is "__main__" or a dotted name whose last part is the file's own module name (`stem`); a
    name that an assignment (as a name target, alone or in a chain), an annotated assignment or a walrus binds to one of these,
    read by that name in any scope (Scan.ns_assign, facts["assigns"], through a chain of names); or an if-expression or a boolean
    operation with one of these among its operands. No other expression is read as a module: a tuple or list unpacking, an inline
    walrus, `sys.modules.__getitem__(k)`, a for-loop target, a parameter default and a starred argument among them. The builtins
    may be written where the file names `__builtins__` as a name (an ast.Name so spelled, in any context), imports the builtins
    module (`import builtins[.x] [as X]`; `from builtins[.x] import ...` at any level, `from .builtins import ...` among them; or
    `from X import builtins [as Y]` or `from X import __builtins__ [as Y]`, for any module X at any level), or writes as above a
    module that module() below reads as the builtins (`__builtins__`; `sys.modules[k]`, its `.get(k)`, or a call Scan.ns_listed
    reads as __import__ or import_module, k the string "builtins" or no string constant; a name an assignment, an annotated
    assignment or a walrus binds to one of these; or an if-expression or a boolean operation over one); and a file that writes its own namespace
    through a computed name may shadow a builtin (`globals()["getattr"] = ...`), which _Served._builtin and _send_gate read with it.
    The run-time forms, each of which may rewrite either namespace by code the census does not read:
    (i) an import from the file's own package (a relative import, an absolute import under the file's top package directory, the
    file itself by that name among them, an import naming the file's own bare stem, its working absolute name when its directory runs
    as a script, or `import __main__`), which flags the file whatever it does with the name, so every write through it, the
    module's `__dict__`, vars(), `.__setattr__` and object.__setattr__ among them, is closed by one arm;
    (ii) an attribute named __globals__, __builtins__, f_globals, f_builtins or f_locals, on any receiver, and a listed callable
    (locals, exec, eval, compile, __import__, import_module or _getframe) reached in one of the first three ways, the one resolver
    Scan.ns_listed applies to each listed callable and to globals, vars, setattr and delattr alike: by its own name, in any
    context; by a name an
    import anywhere in the file binds to it from its module (locals, exec, eval, compile, __import__, globals, vars, setattr and
    delattr from builtins, import_module and __import__ from importlib, _getframe from sys: _LISTED_FROM), in any context, read as
    the name
    itself; or as an attribute of that name on a builtins receiver (Scan._builtins_recv: `__builtins__`; the name `builtins` where
    no import binds it to another module; a name that `import builtins [as X]` or `from X import builtins [as Y]` binds, for any
    module X, at any level (Scan.ns_bmods); `sys.modules["builtins"]` or `sys.modules.get("builtins")`, on any name or attribute
    spelled `modules`; or `__import__("builtins")` or `import_module("builtins")`, a call ns_listed reads as either), and on
    any receiver for exec, eval, locals, __import__, import_module and
    _getframe (re.compile is live);
    (iii) the fourth way: a listed name (those seven callables, globals, vars, setattr, delattr, the five attributes and
    `__dict__`: _STRING_NAMES) spelled as a
    string, or a constant join _Served._const_text folds to one, only where a run-time lookup by name takes it: the second argument
    of getattr, setattr, delattr or hasattr on any receiver (called by its name, by a name an import binds to it, or as an
    attribute of a builtins receiver), any argument of operator.attrgetter or operator.methodcaller (for attrgetter any dotted
    part of the name; either called as `.attrgetter` or `.methodcaller` on the name `operator` where no import binds it to another
    module, or on a name that `import operator [as X]` or `from X import operator [as Y]` binds, for any module X, at any level
    (Scan.ns_opmods), or by a name that `from operator import attrgetter [as Y]` or `from operator import methodcaller [as Y]`
    binds (Scan.ns_ops)), or a key on a namespace expression (a subscript's slice, or the first argument of `.get`, `.pop`,
    `.setdefault`, `.__getitem__`, `.__setitem__` or `.__delitem__`, whose receiver is an attribute named `__dict__`, the name
    `__builtins__`, or a call of vars, globals or locals as ns_listed reaches it). In each of those positions the key is a
    run-time form unless the POSITIVE ALLOWLIST (Scan._unfolded, _key_form, _key_binding) PROVES its shape by the binding: the
    allowlist accepts only a constant string that spells no listed name; a parameter whose default, if any, holds constants alone
    spelling no listed name; a call's return whose callee reaches neither
    text nor the str, bytes or bytearray type nor a method of one; a name that is a loop or comprehension target inside a function
    over a literal of constants, a once-bound module tuple constant the file never writes, rebinds, aliases, names as a string or a
    keyword, or mutates, or the one attribute source kernel/host_transport.py holds, sh.SPEC_FIELDS, keyed by binding on the file, the
    attribute name and the base bound once at module level (_spec_source; any other attribute source refuses by name), whose base
    reaches no text and for which the file writes no attribute of that name (it binds and declares no such name, uses an attribute so
    named only as such a source or an item read, spells the name in no string constant, constants the census folds to it, or
    keyword, uses setattr, delattr, `__setattr__` or `__delattr__`, or an attribute so named, only as the callee of a call each of whose arguments that may name an
    attribute folds to string constants other than that name, directly or as a loop or comprehension target over a literal of them,
    imports none of the four under another name and spells none in folded constants (_setter_sites, _setter_args, _setter_fold),
    and names no globals, vars, locals or `__dict__` and holds no star import); a name that is
    such a target, or an unpacking target, over a parameter or such a call's return, directly or through names an assignment,
    such a target or an unpacking binds to one; a
    boolean operation or an if-expression each of whose values the allowlist accepts where it stands; and a name an assignment
    binds to any of these but a constant string. Every other shape refuses by name, the reason
    naming what the walk met: a join, format, format_map or replace call, a `%`, a `+` or an f-string a string constant does not fold
    (_key_kind); a method of the name str, bytes or bytearray, however reached (`str.lower(v)`, a name bound to str, `builtins.str`);
    any method called on, or attribute read on, constant text or anything the allowlist does not prove reaches no text; a direct
    attribute key or a name bound to one, any attribute source but that one binding, and that binding where the file may write its
    attribute as above (a class replaced through type() with a key the census does not fold, a namespace constructor or a store
    elsewhere on the base chain being, for that one binding, one line under the class limit, since the census reads no base's text), a setter argument of
    any other shape, or a setter reached any other way, counting as such a write; a name bound to a constant string;
    a with target, or a name bound to one; a walrus, or a name a walrus binds anywhere, a comprehension's included (no binding of a
    walrus target is read in an enclosing scope); a subscript; a loop target bound at module level;
    an augmented assignment; a name a function or a class body declares global, wherever the declaration stands, or a scope declares
    nonlocal; a name a class body binds; a name the file binds only in another form (a del, a match pattern, an import, a def, a class
    or another store) or by no statement; a list, set or dict module constant, which code may mutate; and any other node kind, named
    in words. A name read at module level or as a builtin assumes the file may not rewrite its module namespace, and refuses where it
    may (it writes its namespace through a computed name, holds a star import, or holds a run-time form other than a call of
    import_module or __import__; and, for a builtin, where it may write its builtins), so the acceptance is closed at the file's own
    level.
    (iv) since the eleventh round's review (its R1.5 and choices 3 and 13): a getattr-family or namespace-key call whose key
    position holds a starred value or whose arguments hold a ** mapping (Scan._starred_key, _KEY_STARRED), the key read by position; a
    getattr-family name (getattr, setattr, delattr or hasattr, by its own name, by a name an absolute from-import of any module binds
    to it, or as an attribute of a builtins receiver) read other than as a call's callee, an alias or a partial's argument among them
    (_GETATTR_ALIAS); and a namespace mapping the file's own module or the builtins may be (globals() or vars() with no argument,
    `__builtins__`, the `__dict__` or the vars() of a module module() reads as either or of a receiver Scan._builtins_recv reads as the
    builtins) used other than in a key position whose key the allowlist reads (a subscript's container or the receiver of the six
    namespace-key methods: nsuses below, _NS_USE).
    A listed name reached any other way or a name the list does not hold (through `__self__` of a builtin, a container or a copy
    of a namespace mapping other than the file's own module's or the builtins' ((iv) above), a module's own `__setattr__` or
    `__delattr__` method, a listed name, attrgetter or methodcaller
    imported from a module other than its own, a name built at run time, gc or ctypes among them, and through a module reached by
    a tuple or list unpacking, an inline walrus, `sys.modules.__getitem__`, a for-loop target, a parameter default or a starred
    argument) is outside the list and not seen: a module namespace rewritten at run time by code
    outside that list is not seen."""
    aliases, out = {}, {"computed": False, "builtins": facts["builtins"], "file": facts["file"], "deco": facts["deco"], "runtime": None}

    def named(f, *names):
        return isinstance(f, ast.Name) and f.id in names or isinstance(f, ast.Attribute) and f.attr in names

    def module(e):   # the modules an expression may be: "own" (the file's, or one it cannot tell) and "builtins"
        if isinstance(e, ast.IfExp): return module(e.body) | module(e.orelse)
        if isinstance(e, ast.BoolOp): return set().union(*(module(v) for v in e.values))
        if isinstance(e, ast.Name): return {"builtins"} if e.id == "__builtins__" else aliases.get(e.id, set())
        if isinstance(e, ast.Subscript) and named(e.value, "modules"): k = e.slice
        elif isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "get" and named(e.func.value, "modules"): k = e.args[0] if e.args else None
        elif isinstance(e, ast.Call) and id(e) in facts["importers"]: k = e.args[0] if e.args else None   # a call Scan.ns_listed reads as __import__ or import_module
        else: return set()
        k = k.value if isinstance(k, ast.Constant) and isinstance(k.value, str) else None
        if k is None: return {"own", "builtins"}
        return {"builtins"} if k == "builtins" else {"own"} if k == "__main__" or k.split(".")[-1] == stem else set()

    for _ in range(len(facts["assigns"]) + 1):   # a name bound to a module the file may be is that module too, through a chain of names
        before = dict(aliases)
        for targets, value in facts["assigns"]:
            got = module(value)
            for t in targets:
                if isinstance(t, ast.Name) and got: aliases[t.id] = aliases.get(t.id, set()) | got
        if aliases == before: break
    hits = [{"own"} for c in facts["ns_calls"] if id(c) not in facts["gets"]]   # the file's own namespace, used but by a `.get` read
    hits += [module(n.args[0] if isinstance(n, ast.Call) else n.value) for n in facts["maps"] if id(n) not in facts["gets"]]
    hits += [module(n.value) for n in facts["stores"]] + [module(c.args[0]) for c in facts["setattrs"] if c.args]
    for h in hits:
        if "own" in h: out["computed"] = True
        if "builtins" in h: out["builtins"] = True
    # choice 13 of the eleventh round's rulings: a namespace mapping the file's own module or the builtins may be (globals() or vars()
    # with no argument, `__builtins__`, the `__dict__` or the vars() of a module module() reads as the file's or the builtins, or of a
    # receiver Scan._builtins_recv reads as the builtins) used other than in a key position whose key the allowlist reads (a
    # subscript's container, in any context, or the receiver of .get, .pop, .setdefault, .__getitem__, .__setitem__ or .__delitem__:
    # Scan.ns_string, facts["keyed"]): a copy, an alias or an argument by which a listed name may be reached with no key the census
    # reads (Scan.visit_Module makes each a run-time form, _NS_USE)
    free = lambda n: id(n) not in facts["keyed"]
    out["nsuses"] = sorted((n for n in [c for c in facts["ns_calls"] if isinstance(c, ast.Call)] + list(facts["bnames"]) + [
        n for n in facts["maps"] if id(n) in facts["bmaps"] or module(n.args[0] if isinstance(n, ast.Call) else n.value) & {"own", "builtins"}]
        if free(n)), key=lambda n: (n.lineno, n.col_offset))
    # the first run-time form in the file's order, which the reasons name. An own-package import is one such form (arm i's one arm:
    # a file that imports from its own package is flagged whatever it does with the name, so every write through it, `__dict__`,
    # vars(), .__setattr__ and object.__setattr__ among them, is closed), collected in facts["runtime"] beside arm ii's and arm
    # iii's forms.
    out["runtime"] = min(facts["runtime"])[2] if facts["runtime"] else None
    return out


def _module_consts(tree):
    """The module names the served pass and the route typing read as constants, each with its value: a name bound by one top-level
    plain single-name assignment (not annotated, unpacking or chained) and by no other binding at module level. The count walks the module's statements outside def, class
    and import bodies and takes every Name stored or deleted there (a comprehension's target among them, which errs toward
    refusing), with the names a def, a class, an import, an except clause or a match pattern binds there, and it walks every part
    of a def's or a class's header but the body (decorators, defaults, annotations, the return annotation, bases and keywords:
    _header), so a walrus there binds the module's name; so a name bound twice (a default and then a rebind, or a header walrus
    beside the assignment), or bound once inside a try, if, for or with block, is no constant here. A module that holds a star
    import (`from x import *`) wherever the count walks has no constant at all, since that import may bind any name, and neither
    reader reads one in a file that writes its module namespace through a computed name or may rewrite it at run time
    (_namespace_flags), which may too. Computed
    once per tree (_CONSTS, keyed on the tree object and holding no tree alive); neither reader writes the map."""
    return _module_scope(tree)[0]


def _module_bound(tree):
    """The number of module-level bindings of each name the module binds there, by _module_consts's count (a name absent is
    bound nowhere at module level): the served pass exempts a top-level import (def, class) statement only as the name's one
    binding, and a builtin only where no module-level binding shadows it (the names the import system binds in every module,
    `__doc__` among them, no builtin there: _IMPORT_NAMES), and neither where Result.rebinds records the name (a binding under
    `global` in a function, a write by a statement at module level) or the module holds a star import, which may rebind any name
    (_Served._sole and _Served._builtin)."""
    return _module_scope(tree)[1]


def _module_info(tree):
    """What the count saw besides the numbers: whether the module holds a star import (star), the names whose one module-level
    binding is an import, a def or a class statement inside a module-level block rather than a top-level statement (block), the
    names bound in any other form inside a module-level block's body (inblock: an assignment inside a try, say), the names a
    def statement binds anywhere the count walks (defs), the names a top-level annotated, unpacking or chained assignment
    binds (assigned: `X: str = ...`, `X, Y = ...`, `X = Y = ...`), which are no constants, and the names one top-level plain
    single-name assignment binds beside a top-level annotation alone (annotated: `X: str` and `X = ...`, in either order), which
    the count takes as a second binding though it binds nothing at run time, and nothing else binds at module level."""
    return _module_scope(tree)[2]


def _module_scope(tree):
    got = _CONSTS.get(tree)
    if got is None: got = _CONSTS[tree] = _module_consts_of(tree)
    return got


def _module_consts_of(tree):
    count, stack, star, block, defs, inblock, assigned = {}, [(n, True) for n in tree.body], False, set(), set(), set(), set()
    alone = {}   # name -> the top-level annotations alone (`X: str`, no value) that name it, each a binding to the count
    while stack:
        n, top = stack.pop()
        if top is True and (isinstance(n, ast.AnnAssign) and n.value is not None
                            or isinstance(n, ast.Assign) and not (len(n.targets) == 1 and isinstance(n.targets[0], ast.Name))):
            # a top-level annotated, unpacking or chained assignment: its names are no constant (assigned)
            assigned.update(t.id for tg in (n.targets if isinstance(n, ast.Assign) else [n.target]) for t in ast.walk(tg)
                            if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store))
        if top is True and isinstance(n, ast.AnnAssign) and n.value is None and isinstance(n.target, ast.Name):
            alone[n.target.id] = alone.get(n.target.id, 0) + 1
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            count[n.name] = count.get(n.name, 0) + 1
            if not top: block.add(n.name)
            if not isinstance(n, ast.ClassDef): defs.add(n.name)
            stack.extend((h, False) for h in _header(n)); continue   # the header runs at module level; the body is the function's or the class's
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                if a.name == "*": star = True; continue
                k = (a.asname or a.name).split(".")[0]; count[k] = count.get(k, 0) + 1
                if not top: block.add(k)
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)): count[n.id] = count.get(n.id, 0) + 1; got = n.id
        elif isinstance(n, ast.ExceptHandler) and n.name: count[n.name] = count.get(n.name, 0) + 1; got = n.name
        elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name: count[n.name] = count.get(n.name, 0) + 1; got = n.name
        elif isinstance(n, ast.MatchMapping) and n.rest: count[n.rest] = count.get(n.rest, 0) + 1; got = n.rest
        else: got = None
        if got is not None and top is None: inblock.add(got)   # bound inside a module-level block's body, not by a top-level statement
        # a statement below the top level stands in a block's body: what it binds, and what its parts bind, is marked None (inblock)
        stack.extend((c, None if top is None or (top is False and isinstance(n, ast.stmt)) else False) for c in ast.iter_child_nodes(n))
    consts = {} if star else {n.targets[0].id: n.value for n in tree.body
                              if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name) and count.get(n.targets[0].id) == 1}
    # a name one top-level plain single-name assignment binds, beside top-level annotations alone and nothing else at module level
    plain = [n.targets[0].id for n in tree.body if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)]
    annotated = {k for k, v in alone.items() if plain.count(k) == 1 and count.get(k) == v + 1}
    return consts, count, {"star": star, "block": block, "defs": defs, "inblock": inblock, "assigned": assigned, "annotated": annotated}


def _dict_of(e, consts, scopes, written):
    """The dict literal an expression holds: the literal itself, or the value of a module name no code writes after binding it
    (_module_consts, and not in `written`) when that value is one (a name no enclosing scope binds)."""
    if isinstance(e, ast.Dict): return e
    if isinstance(e, ast.Name) and not any(e.id in p or e.id in s or e.id in o for p, s, o in scopes):
        c = consts.get(e.id) if e.id not in written else None
        return c if isinstance(c, ast.Dict) else None
    return None


def _ctype_simple(e, scopes, consts, written):
    """Whether a content-type expression is a string constant, or a name bound once to one: a local of the innermost scope that binds
    it with one string-constant value, or a module constant no code writes after binding it. These are the shapes the frame-local
    limit's content-type face keeps (the census reads such a content type as the function's text binds it, its witness the frame-limit
    plant frwt); every other resolvable shape (a `+`, a conditional, a dict read, a local bound more than once or to no constant) is
    refused by name, since a frame may rewrite an intermediate local and the census does not read it. One check at 0 live (every live content-type expression is a string constant, measured over the walked files), so under the 00:28Z rule the content-type face is refused where a check
    does it, and only what no check refuses stays the stated limit (routes_of, judge)."""
    if isinstance(e, ast.Constant): return type(e.value) is str
    if isinstance(e, ast.Name):
        for params, single, other in scopes:
            if e.id in params or e.id in other: return False
            if e.id in single:
                v = single[e.id]
                return len(v) == 1 and isinstance(v[0], ast.Constant) and type(v[0].value) is str
        c = consts.get(e.id)
        return isinstance(c, ast.Constant) and type(c.value) is str and e.id not in written
    return False


def _ctype_values(e, scopes, consts, written, depth=0):
    """The strings a content-type expression can hold, or None when the census cannot resolve it: a literal, a module name no code
    writes after binding it (one of _module_consts and not in `written`, the module names some code writes after their binding:
    Result.writes), a local whose every binding resolves, a `+` of two resolved sides, a conditional's branches, a dict literal's
    values (by subscript or `.get`, with `.get`'s default). A written module name resolves to None, as any name it does not read
    does."""
    if depth > 24: return None
    if isinstance(e, ast.Constant): return {e.value} if isinstance(e.value, str) else None
    if isinstance(e, ast.Name):
        for params, single, other in scopes:
            if e.id in params or e.id in other: return None
            if e.id in single:
                out = set()
                for v in single[e.id]:
                    r = _ctype_values(v, scopes, consts, written, depth + 1)
                    if r is None: return None
                    out |= r
                return out
        if e.id in consts and e.id not in written: return _ctype_values(consts[e.id], [], consts, written, depth + 1)
        return None
    if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add):
        left, right = _ctype_values(e.left, scopes, consts, written, depth + 1), _ctype_values(e.right, scopes, consts, written, depth + 1)
        return None if left is None or right is None else {a + b for a in left for b in right}
    if isinstance(e, ast.IfExp):
        a, b = _ctype_values(e.body, scopes, consts, written, depth + 1), _ctype_values(e.orelse, scopes, consts, written, depth + 1)
        return None if a is None or b is None else a | b
    if (isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "get" and e.args) or isinstance(e, ast.Subscript):
        d = _dict_of(e.func.value if isinstance(e, ast.Call) else e.value, consts, scopes, written)
        if d is None: return None
        out = set()
        for v in d.values:
            r = _ctype_values(v, scopes, consts, written, depth + 1)
            if r is None: return None
            out |= r
        if isinstance(e, ast.Call) and len(e.args) > 1:
            r = _ctype_values(e.args[1], scopes, consts, written, depth + 1)
            if r is None: return None
            out |= r
        return out
    return None


def _script_type(v):
    """Whether a content type runs script in a browser: its essence (cut at the first `;`, stripped, lower-cased) is one of
    SCRIPT_TYPES or an XML type by its `+xml` suffix."""
    essence = v.split(";")[0].strip().lower()
    return essence in SCRIPT_TYPES or essence.endswith("+xml")


def _is_ctype_write(c):
    """A `send_header("Content-Type", <value>)` call, the header's name in any case."""
    return (isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr == "send_header" and len(c.args) >= 2
            and isinstance(c.args[0], ast.Constant) and isinstance(c.args[0].value, str) and c.args[0].value.lower() == "content-type")


_WRITE_NAMES = ("write", "writelines", "send", "sendall", "sendfile", "sendmsg")   # the stream and socket methods that put text on the wire
_HEADER_ARITY = {"send_response": 1, "send_header": 2, "end_headers": 0}          # the header methods a `_send` calls on self, each with its arguments
_SEND_BUILTINS = ("isinstance", "str", "len", "getattr")                            # the builtins a `_send` may call, where nothing binds or rebinds the name
# The node kinds of the kernel's Handler._send (kernel/kernel.py), each read only in the roles it takes there (_send_gate). Derived from
# that definition by a walk of its syntax tree; the fix commit of the eighth round's review records the command.
_SEND_KINDS = ("Expr", "Assign", "For", "If", "Call", "Attribute", "Name", "Tuple", "Constant", "BinOp", "BoolOp", "Dict", "IfExp")


def _send_gate(d, me, page, write, local, bound, rebinds, star, shadow=False):
    """Why the census does not read a `_send` definition, or None when nothing in its signature or body lies outside the kinds and
    roles of the kernel's Handler._send (_SEND_KINDS), the one definition that types script-running routes. `me` is a method's self
    (None for a module function), `page` its second positional parameter, `write` its one write (`<me>.wfile.write(<page>)`), `local`
    the names the definition binds, `bound` the names the module binds, `rebinds` the names a function binds under a `global`
    declaration or a module-level statement writes (Result.rebinds), `star` whether the module holds a star import and `shadow`
    whether the file may write its builtins or its own module namespace through a computed name, or the run-time form by which it
    may rewrite either (_namespace_flags), which the builtin's refusal then names. The table, by kind and role, with the eighth
    round's review's widening of that table (its word), ruled in on the evidence of the plants tsa and tsw: the order, since the
    table as first ruled ordered no statement, so a header call after the end_headers, flushed by a second end_headers, wrote into
    the response body unscanned (tsa), as did a header call after the write (tsw), and a definition with no end_headers passed;
    and no positional-only parameter, a signature form the ruled signature does not list and the real definition does not use:
    - the order: the write is the definition's last statement, and directly before it stands its one `self.end_headers()`; every
      other statement of its own body stands before that end_headers (end_headers writes the header buffer to the stream, so a
      header call after it would reach the body);
    - the signature: positional parameters, none positional-only, whose defaults are None constants, with no annotation;
    - Expr: a statement whose value is a header call on self, or the write as a statement of the definition's own body;
    - Assign: one, a statement of the definition's own body, its one target the page parameter by name and its value the codec
      shape: the page parameter, `.encode("utf-8")` on it with exactly that one argument, or an IfExp whose test is
      `isinstance(<page>, str)` and whose branches are those (`body = body.encode("utf-8") if isinstance(body, str) else body`);
    - For: one, a statement of the definition's own body with no else, its target a name or a tuple of names that are no parameter
      and not self, its iterable `(<a parameter> or {}).items()`;
    - If: a statement of the definition's own body with no else, its test a parameter or the getattr call below;
    - Call: `send_response` with its one argument and `send_header` with two, called on self as statements, and `end_headers` with
      none, the one statement above; the write; `isinstance(<page>, str)` as the codec's test; `len(<page>)` and `str(<one value>)` as header values;
      `getattr(<self>, <a str constant>, None)` as an if's test; `.encode("utf-8")` in the codec; `.items()` as the loop's iterable;
      none with a keyword;
    - Attribute, loaded: on self, a header method as its call's callee, `wfile` as the write's receiver and nowhere else, and any
      other name but a write method's as a header value; `.write` on `self.wfile` as the write's callee; `.encode` on the page
      parameter and `.items` on the loop's iterable, each its call's callee;
    - Name: loaded, a parameter; self as an attribute's base or getattr's first argument; the loop's targets inside its body; a
      builtin above as its call's callee, and `str` as isinstance's second argument, each only where neither the definition nor the
      module binds the name, nothing rebinds it, the module holds no star import and the file writes no builtin and no name of its
      module namespace through a computed name and may rewrite neither at run time (`shadow`); stored, the page parameter as the
      codec's target and the loop's targets;
    - Tuple, stored: the loop's target; Constant: a str or None, a str in a header call's arguments holding no CR or LF;
    - BinOp: a `%` whose left operand is a str constant, as a header value; BoolOp: the `or` of a parameter and an empty dict in the
      loop's iterable; Dict: that empty dict; IfExp: the codec's value.
    A header value is an argument of a header call or of str(), or the right operand of that `%`. Every other statement or
    expression refuses by its kind and line ("a With statement at line N", "a Subscript expression at line N"), a listed kind in
    any other role by its kind and line too ("a Call expression outside its listed roles at line N"), a builtin whose allowance a
    run-time form of the file takes away by the builtin and that form ("getattr at line N, a builtin in a file that calls exec at
    line M, which may rewrite the builtins at run time"), a string constant holding a CR or LF in a header call's arguments by
    name, and the signature by what it holds, the first in the definition's order."""
    a = d.args
    sig = ([(x, "a positional-only parameter") for x in a.posonlyargs] + [(x, "a keyword-only parameter") for x in a.kwonlyargs]
           + [(x, w) for x, w in ((a.vararg, "a *args parameter"), (a.kwarg, "a **kwargs parameter")) if x is not None]
           + [(x.annotation, "a parameter's annotation") for x in a.args if x.annotation is not None]
           + [(v, "a default other than None, a %s," % type(v).__name__) for v in a.defaults if not (isinstance(v, ast.Constant) and v.value is None)]
           + ([(d.returns, "a return annotation")] if d.returns is not None else []) + [(t, "a type parameter") for t in getattr(d, "type_params", ())])
    if sig:
        n, what = min(sig, key=lambda s: (s[0].lineno, s[0].col_offset))
        return "%s at line %d" % (what, n.lineno)
    parent, order = {}, []
    for s in d.body:
        parent[id(s)] = d
        for n in ast.walk(s):
            order.append(n)
            for c in ast.iter_child_nodes(n): parent[id(c)] = n
    top = [s for s in d.body]
    at = parent.get(id(write))
    widx = next((i for i, s in enumerate(top) if s is at), None)
    # the one end_headers, the statement directly before the write: a header call after it would reach the body, since end_headers
    # writes the header buffer to the stream, so every other statement of the body stands before it (before the write without it)
    ends = (top[widx - 1] if widx and isinstance(top[widx - 1], ast.Expr) and isinstance(top[widx - 1].value, ast.Call)
            and isinstance(top[widx - 1].value.func, ast.Attribute) and top[widx - 1].value.func.attr == "end_headers"
            and me is not None and isinstance(top[widx - 1].value.func.value, ast.Name) and top[widx - 1].value.func.value.id == me else None)
    limit = widx - 1 if ends is not None else widx
    assigns, fors = [s for s in top if isinstance(s, ast.Assign)], [s for s in top if isinstance(s, ast.For)]
    loop = fors[0] if fors else None
    # every name under the loop's target: the loop is accepted only where that target is a name or a tuple of names (ok's For arm),
    # which binds each name here, and with any other target the loop is outside its role, so the gate refuses the definition: a name
    # the target only reads is never taken for a loop target of a definition the gate accepts
    targets = {t.id for t in ast.walk(loop.target) if isinstance(t, ast.Name)} if loop else set()
    in_loop ={id(n) for b in (loop.body if loop else ()) for n in ast.walk(b)}
    params = {x.arg for x in a.args} - {me}

    def named(e, i=None):
        return isinstance(e, ast.Name) and (i is None or e.id == i)

    def header(c):
        return (me is not None and isinstance(c, ast.Call) and isinstance(c.func, ast.Attribute) and c.func.attr in _HEADER_ARITY
                and named(c.func.value, me))

    def encode(e):
        return (isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "encode" and named(e.func.value, page)
                and len(e.args) == 1 and not e.keywords and isinstance(e.args[0], ast.Constant) and type(e.args[0].value) is str
                and e.args[0].value == "utf-8")

    def is_str(e):
        return (isinstance(e, ast.Call) and named(e.func, "isinstance") and len(e.args) == 2 and not e.keywords and named(e.args[0], page)
                and named(e.args[1], "str"))

    def gets(e):
        return (me is not None and isinstance(e, ast.Call) and named(e.func, "getattr") and len(e.args) == 3 and not e.keywords
                and named(e.args[0], me) and isinstance(e.args[1], ast.Constant) and type(e.args[1].value) is str
                and isinstance(e.args[2], ast.Constant) and e.args[2].value is None)

    def codec(e):
        leaf = lambda x: named(x, page) or encode(x)
        return leaf(e) or (isinstance(e, ast.IfExp) and is_str(e.test) and leaf(e.body) and leaf(e.orelse))

    def value(n, p):   # a header value: an argument of a header call or of str(), or the right operand of the `%`
        return ((isinstance(p, ast.Call) and any(x is n for x in p.args) and (header(p) or named(p.func, "str")))
                or (isinstance(p, ast.BinOp) and p.right is n))

    def early(n):   # a statement of the body before the end_headers (before the write where there is none)
        return limit is not None and top.index(n) < limit

    def ok(n):
        p = parent[id(n)]
        if isinstance(n, ast.Expr):
            if n is ends or (n.value is write and p is d): return ends is not None
            return header(n.value) and (p is not d or early(n))
        if isinstance(n, ast.Assign):
            return p is d and n is assigns[0] and early(n) and len(n.targets) == 1 and named(n.targets[0], page) and codec(n.value)
        if isinstance(n, ast.For):
            it = n.iter
            return (p is d and n is loop and early(n) and not n.orelse and not targets & (params | {me})
                    and (named(n.target) or (isinstance(n.target, ast.Tuple) and all(named(t) for t in n.target.elts)))
                    and isinstance(it, ast.Call) and not it.args and not it.keywords and isinstance(it.func, ast.Attribute)
                    and it.func.attr == "items" and isinstance(it.func.value, ast.BoolOp) and isinstance(it.func.value.op, ast.Or)
                    and len(it.func.value.values) == 2 and named(it.func.value.values[0]) and it.func.value.values[0].id in params
                    and isinstance(it.func.value.values[1], ast.Dict) and not it.func.value.values[1].keys)
        if isinstance(n, ast.If): return p is d and early(n) and not n.orelse and ((named(n.test) and n.test.id in params) or gets(n.test))
        if isinstance(n, ast.Call):
            f = n.func
            if n.keywords: return False
            if header(n): return len(n.args) == _HEADER_ARITY[f.attr] and isinstance(p, ast.Expr) and (f.attr != "end_headers" or p is ends)
            if n is write:
                return (isinstance(p, ast.Expr) and parent.get(id(p)) is d and me is not None and isinstance(f, ast.Attribute)
                        and isinstance(f.value, ast.Attribute) and f.value.attr == "wfile" and named(f.value.value, me)
                        and len(n.args) == 1 and named(n.args[0], page))
            if is_str(n): return isinstance(p, ast.IfExp) and p.test is n
            if named(f, "len"): return len(n.args) == 1 and named(n.args[0], page) and value(n, p)
            if named(f, "str"): return len(n.args) == 1 and value(n, p)
            if gets(n): return isinstance(p, ast.If) and p.test is n
            if encode(n): return (isinstance(p, ast.Assign) and p.value is n) or (isinstance(p, ast.IfExp) and (p.body is n or p.orelse is n))
            return (isinstance(f, ast.Attribute) and f.attr == "items" and isinstance(f.value, ast.BoolOp) and not n.args
                    and isinstance(p, ast.For) and p.iter is n)
        if isinstance(n, ast.Attribute):
            if not isinstance(n.ctx, ast.Load): return False
            if me is not None and named(n.value, me):
                if n.attr in _HEADER_ARITY: return isinstance(p, ast.Call) and p.func is n
                if n.attr == "wfile": return isinstance(p, ast.Attribute) and p.value is n and p.attr == "write" and write.func is p
                return n.attr not in _WRITE_NAMES and value(n, p)
            if n.attr == "write": return p is write and write.func is n
            if n.attr == "encode": return named(n.value, page) and isinstance(p, ast.Call) and p.func is n
            return n.attr == "items" and isinstance(n.value, ast.BoolOp) and isinstance(p, ast.Call) and p.func is n
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Store):
                return ((n.id == page and isinstance(p, ast.Assign) and p is (assigns[0] if assigns else None) and any(t is n for t in p.targets))
                        or (n.id in targets and (p is loop or (isinstance(p, ast.Tuple) and parent.get(id(p)) is loop))))
            if not isinstance(n.ctx, ast.Load): return False
            if (isinstance(p, ast.Call) and p.func is n) or (is_str(p) and p.args[1] is n):
                # the builtin allowance, decided here alone: the name is no binding of the definition's or the module's, nothing
                # rebinds it (a function under `global`, or a module-level statement), no star import may, and the file writes no
                # builtin and no name of its module namespace through a computed name, nor may rewrite either at run time (`shadow`,
                # the run-time form named in the reason)
                allowed = n.id in _SEND_BUILTINS and n.id not in local and n.id not in bound and n.id not in rebinds and not star
                if allowed and isinstance(shadow, str): run_why[id(n)] = "%s at line %d, %s" % (n.id, n.lineno, _RUNTIME_BUILTIN % shadow)
                return allowed and not shadow
            if me is not None and n.id == me: return (isinstance(p, ast.Attribute) and p.value is n) or (gets(p) and p.args[0] is n)
            return n.id in params or (n.id in targets and id(n) in in_loop)
        if isinstance(n, ast.Tuple): return isinstance(n.ctx, ast.Store) and p is loop and loop.target is n
        if isinstance(n, ast.Constant): return type(n.value) is str or n.value is None
        if isinstance(n, ast.BinOp):
            return isinstance(n.op, ast.Mod) and isinstance(n.left, ast.Constant) and type(n.left.value) is str and value(n, p)
        if isinstance(n, ast.BoolOp):
            return (isinstance(n.op, ast.Or) and len(n.values) == 2 and named(n.values[0]) and n.values[0].id in params
                    and isinstance(n.values[1], ast.Dict) and isinstance(p, ast.Attribute) and p.attr == "items" and p.value is n)
        if isinstance(n, ast.Dict): return not n.keys and isinstance(p, ast.BoolOp)
        if isinstance(n, ast.IfExp): return isinstance(p, ast.Assign) and p.value is n and codec(n)
        return False

    in_header = {id(x) for c in order if header(c) for arg in c.args for x in ast.walk(arg)}
    run_why = {}   # id(a builtin's Name) -> its reason, where only a run-time form of the file (`shadow`) takes its allowance away
    bad = []   # (line, column, the reason): a decorated statement starts at its first decorator
    for n in order:
        if not isinstance(n, (ast.stmt, ast.expr)): continue   # an operator, a context, an argument list: part of its node's kind
        kind, what = type(n).__name__, "statement" if isinstance(n, ast.stmt) else "expression"
        art, line = "an" if kind[0] in "AEIO" else "a", min([n.lineno] + [x.lineno for x in getattr(n, "decorator_list", ())])
        if kind not in _SEND_KINDS: bad.append((line, n.col_offset, "%s %s %s at line %d" % (art, kind, what, line)))
        elif not ok(n): bad.append((line, n.col_offset, run_why.get(id(n)) or "%s %s %s outside its listed roles at line %d" % (art, kind, what, line)))
        elif isinstance(n, ast.Constant) and type(n.value) is str and ("\r" in n.value or "\n" in n.value) and id(n) in in_header:
            bad.append((line, n.col_offset, "a Constant holding a CR or LF in a header call at line %d" % line))
    return min(bad, key=lambda b: b[:2])[2] if bad else None   # the first in the definition's order; min keeps the outer at a tie


def _body_param(d, pos, me, tree, rebinds=(), shadow=False):
    """(the parameter a `_send` definition writes as its page body, None), or (None, why the census does not read it). The body is
    its second positional parameter (`pos`, self dropped for a method; `me` a method's first parameter, and a module function has
    none), read only when the definition's one output is its one `self.wfile.write(<that parameter>)` and nothing in its signature
    or body lies outside the kinds and roles of the kernel's Handler._send (_send_gate, which names them): the one write of the
    page parameter, the definition's last statement, directly after its one `self.end_headers()`, and before them send_response
    with its one argument and send_header, called on self as statements; isinstance, str, len, and getattr of self with a
    string-constant name and a None default, each only where neither the definition nor the module binds the name, nothing rebinds
    it (no function binds it under a `global` declaration and no module-level statement writes it: Result.rebinds, `rebinds`; and
    the file names no `__builtins__` as a name, imports no builtins module (`import builtins[.x]`, `from builtins[.x] import ...`
    at any level, `from X import builtins` or `from X import __builtins__`, any X at any level), writes no module that may be the
    builtins module (by an attribute store or delete, a setattr or delattr, or its `__dict__` or vars() used any way but for a
    `.get` read, a module _namespace_flags's module() reads as the builtins), writes no name of its
    module namespace through globals() or vars(), or through a store, setattr, delattr, `__dict__` or vars() on a module the file
    may be (`sys.modules[k]` or its `.get(k)`, or `__import__(k)` or `import_module(k)`, k no string constant, "__main__" or the
    file's own module name; a name that an assignment (as a name target, alone or in a chain), an annotated assignment or a walrus
    binds to one of these; or an if-expression or a boolean operation over one), globals, vars, setattr and delattr each by its
    own name, a name an import from builtins binds to it or as an attribute of a builtins receiver (`__builtins__`, a name `import
    builtins [as X]` or `from X import builtins [as Y]` binds, `sys.modules["builtins"]` or its `.get`, `__import__("builtins")`
    or `import_module("builtins")`), a read of one other than as a call counting as such a write, and
    does none of the run-time forms: an import from its own package, its
    own bare stem among them; an attribute named __globals__, __builtins__, f_globals, f_builtins or f_locals; a listed callable
    (locals, exec, eval, compile, __import__, import_module or _getframe) by its own name, by a name an import from builtins,
    importlib or sys binds to it, or as an attribute on a builtins receiver or, for all but compile, on any receiver; or one of
    those names, globals, vars, setattr,
    delattr or `__dict__` spelled as a string in a getattr-family, attrgetter/methodcaller or namespace-key position
    (_namespace_flags lists these four ways exactly):
    `shadow`, _namespace_flags) and the
    module holds no star import; the one rebinding
    of the page parameter to itself or to itself encoded by `.encode("utf-8")`, alone or as the branches of an
    `isinstance(<page>, str)` test (`body = body.encode("utf-8") if isinstance(body, str) else body`); a loop over a parameter's items (`for k, v in (headers or {}).items():`) and an if on a
    parameter or on that getattr, each into header calls; header values built from string constants holding no CR or LF,
    parameters, the loop's targets, attributes read on self, str, len and a `%` format on a string constant; and a signature of
    positional parameters, none positional-only, with None defaults and no annotation. Any other statement or expression refuses
    by its kind and line ("a With statement at line N"; a listed kind in another role, "a Call expression outside its listed roles
    at line N"): among them a statement after the end_headers (end_headers writes the header buffer to the stream, so a header
    call after it would reach the body), a second end_headers, a definition with none, and any other rebinding of the page
    parameter (another assignment, an augmented or annotated assignment, a walrus, a loop or with target, an import, an except
    name, a del, a match capture, a def, class or nested parameter of its name), another codec name or a second argument to
    `.encode` (either can name a codec or an error handler the file registers at run time), any store or delete of an attribute or
    a subscript, any read of a name the module binds, any other call and any nested def, class or lambda. Before that gate the
    named reasons refuse, each with its road: a method's definition that binds self again in any form, as a type parameter
    included, anywhere inside it (an assignment to it, a lambda's or a nested def's parameter named self among them), or declares
    it global there ("a definition that rebinds self", "a definition that declares self global": a header call or a getattr on
    self could then reach an object other than the handler); a string constant equal to a write method's name (write, writelines,
    send, sendall, sendfile or sendmsg); any other read of an attribute so named, called or not (an alias of the write, a second
    write, a write through another of those methods); a print; a reference to the write's receiver other than as its receiver; no
    such write; and a write of anything but the second positional parameter. The census does not read what the definition's text
    does not hold: a header value is not scanned, and a response that a Content-Type in its headers argument, passed or defaulted,
    makes a page is outside the served pass (the call is typed by its content-type argument); code the definition runs through an
    object it is handed (a parameter's methods, its mapping's items, its __str__) is not read; nor is code behind a name the
    definition calls or reads on self (a header method, a property or `__getattr__`, however the class, a base or other code
    defines or replaces it) and any stream that code writes, an override of `_send` in a subclass another file defines, or a
    `_send` replaced at run time through a name no code spells (setattr or a class `__dict__` with a computed name, a metaclass
    namespace key, a base's `__init_subclass__`); nor is a module namespace rewritten at run time by code outside the forms
    _namespace_flags reads: a listed name reached any other way or a name the list does not hold (through `__self__` of a builtin,
    a container or a copy of a namespace mapping other than the file's own module's or the builtins' (one of those used other
    than in a key position the census reads is a run-time form: _namespace_flags (iv)), a module's own `__setattr__` or
    `__delattr__` method, a listed name, attrgetter or methodcaller imported from a module other than its own, a name built at run time, gc or ctypes among them, and through a
    module reached by a tuple or list unpacking, an inline walrus, `sys.modules.__getitem__`, a for-loop target, a parameter
    default or a starred argument) is outside the list and not seen, a builtin so rewritten
    read as the builtin."""
    a = d.args
    nodes = list(ast.walk(d))
    # the names the definition binds in the other forms _binding_forms names (a def or class statement, a parameter of a def or
    # lambda nested in it, an import, an except name, a match capture, a del), each a local here; the definition's own parameters
    # are `pos` and `me`
    own = {id(x) for x in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if x is not None}
    others = set()
    for n in nodes:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n is not d: got = (n.name,)
        elif isinstance(n, ast.arg) and id(n) not in own: got = (n.arg,)   # every kind: positional, keyword-only, `*args`, `**kwargs`
        elif isinstance(n, (ast.Import, ast.ImportFrom)): got = tuple((a.asname or a.name).split(".")[0] for a in n.names)
        elif isinstance(n, (ast.ExceptHandler, ast.MatchAs, ast.MatchStar)): got = (n.name,) if n.name else ()
        elif isinstance(n, ast.MatchMapping): got = (n.rest,) if n.rest else ()
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Del): got = (n.id,)
        else: continue
        others.update(got)
    params = set(pos) | {x.arg for x in a.kwonlyargs} | ({a.vararg.arg} if a.vararg else set()) | ({a.kwarg.arg} if a.kwarg else set())
    local = {t.id for t in nodes if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store)} | others | params | ({me} if me else set())
    # a method's self (`me`) bound again anywhere inside the definition, as a store, in any form above or as a type parameter (3.12,
    # binding its name in the scope it heads), or declared global there: a header call or a getattr on self could then reach an
    # object other than the handler, so the definition is refused whole
    if me and (me in others or any(isinstance(t, ast.Name) and t.id == me and isinstance(t.ctx, ast.Store) for t in nodes)
               or any(type(t).__name__ in ("TypeVar", "ParamSpec", "TypeVarTuple") and t.name == me for t in nodes)):
        return None, "a definition that rebinds %s" % me
    if me and any(isinstance(n, ast.Global) and me in n.names for n in nodes): return None, "a definition that declares %s global" % me
    if any(isinstance(n, ast.Constant) and n.value in _WRITE_NAMES for n in nodes): return None, "a write method named by a string"
    writes = [n for n in nodes if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _WRITE_NAMES]
    called = {id(w.func) for w in writes}
    if any(isinstance(n, ast.Attribute) and n.attr in _WRITE_NAMES and id(n) not in called for n in nodes): return None, "a write through an alias"
    if len(writes) > 1: return None, "a second write"
    if writes and writes[0].func.attr != "write": return None, "a write through %s" % writes[0].func.attr
    if any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "print" for n in nodes): return None, "a print to a stream"
    if not writes: return None, "no write the census reads"
    w = writes[0]; recv = w.func.value
    if sum(1 for n in nodes if type(n) is type(recv) and ast.unparse(n) == ast.unparse(recv)) > 1:
        return None, "a reference to the write's receiver other than as its receiver"
    if not (len(w.args) == 1 and not w.keywords and isinstance(w.args[0], ast.Name) and len(pos) > 1 and w.args[0].id == pos[1]):
        return None, "the definition's written body is not its second positional parameter"
    # the gate, after every named reason: the definition's every node of a kind, in a role, the kernel's Handler._send holds
    why = _send_gate(d, me, pos[1], w, local, _module_bound(tree), rebinds, _module_info(tree)["star"], shadow)
    return (None, why) if why else (pos[1], None)


def _unread_body(call, param, why=None):
    """Why the census does not read a route's page body from this `_send` call (None when it reads `call.args[1]`): the
    definition's body parameter (_body_param) is None, with the reason that gave, or the call does not pass that argument
    positionally with no starred argument before it, or it spreads a mapping with `**`."""
    if param is None: return why or "the definition's written body is not its second positional parameter"
    if any(k.arg is None for k in call.keywords): return "a ** argument"
    if any(isinstance(a, ast.Starred) for a in call.args[:2]): return "a starred argument"
    if len(call.args) < 2: return "a keyword body" if any(k.arg == param for k in call.keywords) else "no body argument"
    return None


_COMPS = (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _send_bindings(tree, inner):
    """Every binding of `_send` in one file outside function bodies, each (the node, whether it is a def or async def statement
    direct in the module's body or a class's body): the module and every class body counted together, a class body defined inside
    a function body included, since a class body is never a function body (its statements bind the class's names, not the
    function's), while a binding in a function body itself is not counted (the function's own; one under a `global` declaration,
    which binds the module's name, refuses the file by itself in routes_of: _global_binder); a def, an async def or a class
    statement, an assignment, a loop or with target, a walrus (in a header too: _header), an import, an except clause, a match
    capture or a del; a comprehension binds its targets alone (Python 3), as _binding_forms reads it, so its target is no binding
    here, and a walrus in its parts binds the scope around it. Inside a function body only a class statement's body is counted:
    `inner`, the class statements whose nearest enclosing def is a function, as Scan's own walk records them (Scan.inner_classes),
    each body walked here, so no second walk enters a function body."""
    out, stack = [], [(n, True) for n in tree.body] + [(b, True) for c in inner for b in c.body]
    while stack:
        n, direct = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if n.name == "_send": out.append((n, direct))
            stack.extend((h, False) for h in _header(n)); continue   # the body is the function's; a class statement in it is one of `inner`
        if isinstance(n, ast.ClassDef):
            if n.name == "_send": out.append((n, False))
            stack.extend((h, False) for h in _header(n)); stack.extend((b, True) for b in n.body); continue
        if isinstance(n, ast.Lambda): stack.extend((h, False) for h in _header(n)); continue
        if isinstance(n, _COMPS):   # its targets are its own; a walrus in its parts binds this scope's name
            stack.extend((c, False) for c in ast.iter_child_nodes(n) if not isinstance(c, ast.comprehension))
            stack.extend((c, False) for g in n.generators for c in [g.iter] + g.ifs); continue
        if isinstance(n, (ast.Import, ast.ImportFrom)): out.extend((n, False) for a in n.names if (a.asname or a.name).split(".")[0] == "_send")
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)) and n.id == "_send": out.append((n, False))
        elif isinstance(n, ast.ExceptHandler) and n.name == "_send": out.append((n, False))
        elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name == "_send": out.append((n, False))
        elif isinstance(n, ast.MatchMapping) and n.rest == "_send": out.append((n, False))
        stack.extend((c, False) for c in ast.iter_child_nodes(n))
    return out


def _names_send(tree, calls):
    """Whether the file names `_send` anywhere but as the called name of its `_send` calls (`calls`): any other node with a field
    equal to it, a name or an attribute in any role, a parameter, an import alias, a def, class or except name, a match capture, a
    keyword or a string among them (every binding of the name has such a field). A file that names it nowhere else binds it
    nowhere at all; one that does may bind it (this errs toward saying so)."""
    called = {id(c.func) for c in calls}
    return any(v == "_send" for n in ast.walk(tree) if id(n) not in called for _, v in ast.iter_fields(n))


def _binding_forms(scope, name):
    """(the forms by which one scope binds a name, each named for a SERVED line; the declaration the scope makes of the name, "global",
    "nonlocal" or None): a def's or a lambda's parameters, and the statements of a def's, a lambda's or a class's own body, where a
    nested def's or class's header and a lambda's defaults count and their bodies do not (a def or a class statement, an
    assignment, an augmented or annotated assignment, an annotation alone, a loop, with or except target, a walrus, a del, an
    import, a match capture, any other store); a comprehension binds its targets alone, the names each target stores (a name, or one
    inside a tuple, list or starred target: Scan._key_targets, never a name the target only reads, inside an attribute's base or a
    subscript's container or index), and a walrus inside it binds the name of the scope around it."""
    if isinstance(scope, _COMPS):
        return ["a comprehension's target" for g in scope.generators for t, _ in Scan._key_targets(g.target) if t == name], None
    forms, declared = [], None
    if not isinstance(scope, ast.ClassDef):
        a = scope.args
        if any(x.arg == name for x in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if x is not None): forms.append("a parameter")
    stack = [(n, None) for n in (scope.body if isinstance(scope.body, list) else [scope.body])]
    while stack:
        n, how = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if n.name == name: forms.append("a class statement" if isinstance(n, ast.ClassDef) else "a def statement")
            stack.extend((h, None) for h in _header(n)); continue
        if isinstance(n, ast.Lambda): stack.extend((h, None) for h in _header(n)); continue
        if isinstance(n, _COMPS):   # its targets are its own; a walrus in its parts binds this scope's name
            stack.extend((c, None) for c in ast.iter_child_nodes(n) if not isinstance(c, ast.comprehension))
            stack.extend((c, None) for g in n.generators for c in [g.iter] + g.ifs); continue
        if isinstance(n, ast.Name):
            if n.id == name and isinstance(n.ctx, (ast.Store, ast.Del)): forms.append(how or ("a del" if isinstance(n.ctx, ast.Del) else "a store"))
            continue
        if isinstance(n, (ast.Global, ast.Nonlocal)):
            if name in n.names: declared = "global" if isinstance(n, ast.Global) else "nonlocal"
            continue
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            forms.extend("an import" for a in n.names if (a.asname or a.name).split(".")[0] == name); continue
        if isinstance(n, ast.ExceptHandler) and n.name == name: forms.append("an except name")
        elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name == name or isinstance(n, ast.MatchMapping) and n.rest == name: forms.append("a match capture")
        labels = {}   # a target's subtree, named by the statement that binds it
        if isinstance(n, (ast.For, ast.AsyncFor)): labels[id(n.target)] = "a loop target"
        elif isinstance(n, ast.withitem) and n.optional_vars is not None: labels[id(n.optional_vars)] = "a with target"
        elif isinstance(n, ast.Assign): labels.update((id(t), "an assignment") for t in n.targets)
        elif isinstance(n, ast.AugAssign): labels[id(n.target)] = "an augmented assignment"
        elif isinstance(n, ast.AnnAssign): labels[id(n.target)] = "an annotated assignment" if n.value is not None else "an annotation"
        elif isinstance(n, ast.NamedExpr): labels[id(n.target)] = "a walrus"   # a del's target is named by its own context above
        stack.extend((c, labels.get(id(c), how)) for c in ast.iter_child_nodes(n))
    return forms, declared


def _body_names(scope):
    """Every name the scope (a def, a lambda or a class statement) binds in any form, as _binding_forms reads its bindings: each
    name that stands in its body where _binding_forms looks (outside the bodies of the defs, classes and lambdas nested in it and the
    targets of its comprehensions) and for which _binding_forms gives a form there, so the set is that reader's, name by name."""
    names, stack = set(), list(scope.body if isinstance(scope.body, list) else [scope.body])
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): names.add(n.name); stack.extend(_header(n)); continue
        if isinstance(n, ast.Lambda): stack.extend(_header(n)); continue
        if isinstance(n, _COMPS):
            stack.extend(c for c in ast.iter_child_nodes(n) if not isinstance(c, ast.comprehension))
            stack.extend(c for g in n.generators for c in [g.iter] + g.ifs); continue
        if isinstance(n, ast.Name): names.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)): names.update((a.asname or a.name).split(".")[0] for a in n.names)
        elif isinstance(n, ast.ExceptHandler) and n.name: names.add(n.name)
        elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name: names.add(n.name)
        elif isinstance(n, ast.MatchMapping) and n.rest: names.add(n.rest)
        stack.extend(ast.iter_child_nodes(n))
    return {x for x in names if _binding_forms(scope, x)[0]}


def _name_reads(fn, name):
    """Each read of the name `name` other than as a call's callee in the body of the def statement fn, in any context and in any
    scope nested in it: (its position, the scopes around it, innermost last, fn first), the scopes as Scan.kscopes holds them (a
    def's or a class's whole statement, a lambda's body, a comprehension), for _binding_scope."""
    out, callee, stack = [], set(), [(n, (fn,)) for n in reversed(fn.body)]
    while stack:
        n, chain = stack.pop()
        if isinstance(n, ast.Call): callee.add(id(n.func))   # a call is popped before its callee
        if isinstance(n, ast.Name):
            if n.id == name and id(n) not in callee: out.append(((n.lineno, n.col_offset), chain))
            continue
        if isinstance(n, ast.Lambda):   # its defaults run where it stands, its body in its own scope
            stack.extend((c, chain) for c in ast.iter_child_nodes(n.args)); stack.append((n.body, chain + (n,))); continue
        inner = chain + (n,) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef) + _COMPS) else chain
        stack.extend((c, inner) for c in reversed(list(ast.iter_child_nodes(n))))
    return out


def _binding_scope(name, at, chain):
    """The scope whose binding of `name` a read at the position `at` reaches, inside the scopes `chain` (innermost last, as
    Scan.kscopes holds them: a def's or a class's whole statement, a lambda's body, a comprehension), as Python resolves it; None for
    the module's. From the innermost scope out, each read by _binding_forms, the one reader of a scope's bindings: a comprehension
    whose target binds it (a read anywhere in it but its first source, which runs in the enclosing scope), a lambda that binds it (a
    parameter, a walrus in its body), and a def or a class that binds it in any form (the read in its body, not its header, which
    runs in the enclosing scope; a class only where the read stands in its own body, since a class body is no scope of the scopes
    nested in it) answer that scope; a nonlocal declaration answers the scope itself, the enclosing function's binding standing in
    for it; a global declaration answers the module."""
    passed = False   # a function scope stands between the read and the scopes further out: a class body there is none of its scopes
    for s in reversed(chain):
        if isinstance(s, _COMPS):
            first = s.generators[0].iter
            if (first.lineno, first.col_offset) <= at < (first.end_lineno, first.end_col_offset): continue   # its first source runs outside it
            if _binding_forms(s, name)[0]: return s
            passed = True
        elif isinstance(s, ast.Lambda):
            if _binding_forms(s, name)[0]: return s
            passed = True
        elif isinstance(s, ast.ClassDef) and passed: continue
        elif at >= (s.body[0].lineno, s.body[0].col_offset):   # in the body of a def or a class, not in its header
            forms, declared = _binding_forms(s, name)
            if declared == "global": return None
            if forms or declared == "nonlocal": return s
            if not isinstance(s, ast.ClassDef): passed = True
    return None


def _yields(fn):
    """Whether the def statement fn's own body yields (a yield or a yield from, outside the defs, classes and lambdas nested in it),
    so a call of it returns a generator, not the value of a return statement: a yield inside a comprehension or a generator
    expression is a syntax error, and each nested scope yields for itself."""
    stack = list(fn.body)
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)): continue
        if isinstance(n, (ast.Yield, ast.YieldFrom)): return True
        stack.extend(ast.iter_child_nodes(n))
    return False


# the node kinds _holds_lambda descends through: a caller tests a value's type against the set first, so a value of any other kind (a
# name, a constant, a call) costs no call and no stack frame, and resolve's recursion over a chain of aliases keeps its depth
_LAMBDA_HOLDERS = frozenset((ast.Lambda, ast.IfExp, ast.BoolOp, ast.NamedExpr, ast.Starred, ast.List, ast.Tuple, ast.Set, ast.Dict))


def _holds_lambda(v):
    """Whether the value `v` a name holds is, or carries as one of its values, a lambda: the value itself, an if-expression's
    branches, a boolean operation's operands, a walrus's or a starred value, and a list, tuple, set or dict literal's elements, keys
    and values, each as the name's value holds it; never a call's argument or return, a subscript or an attribute, which yield a value
    of their own (a lambda handed to re.sub stands in the page where it is read). Each kind is tested by its exact type (the parser
    makes no subclass of a node kind), which calls nothing, where isinstance over a tuple of kinds enters the interpreter's
    recursion count on 3.10 and 3.11."""
    stack = [v]
    while stack:
        x = stack.pop()
        t = type(x)
        if t is ast.Lambda: return True
        if t is ast.IfExp: stack += [x.body, x.orelse]
        elif t is ast.BoolOp: stack.extend(x.values)
        elif t is ast.NamedExpr or t is ast.Starred: stack.append(x.value)
        elif t is ast.List or t is ast.Tuple or t is ast.Set: stack.extend(x.elts)
        elif t is ast.Dict: stack.extend(y for y in x.keys + x.values if y is not None)
    return False


def _call_scopes(call, defs, tree):
    """The scopes a bare call looks its name up in, innermost first: the lambdas and comprehensions around the call inside its
    innermost def or class (the module when there is none), a lambda only when the call stands in its body and a comprehension
    not when the call stands in its first iterable; that def or class when the call stands in its body, not its header; then the
    enclosing defs and classes outward. The module's own binding is the caller's to read after."""
    root = defs[-1] if defs else tree
    body = {id(s) for s in root.body}
    stack, path, inbody = [(c, (), id(c) in body) for c in ast.iter_child_nodes(root)], None, True
    while stack:
        n, around, top = stack.pop()
        if n is call: path, inbody = around, top; break
        if isinstance(n, ast.Lambda):
            stack.extend((c, around + (n,) if c is n.body else around, top) for c in ast.iter_child_nodes(n)); continue
        if isinstance(n, _COMPS):
            first = n.generators[0].iter
            stack.extend((c, around + (n,), top) for c in ast.iter_child_nodes(n) if not isinstance(c, ast.comprehension))
            for g in n.generators:
                stack.extend((c, around if c is first else around + (n,), top) for c in [g.target, g.iter] + g.ifs)
            continue
        stack.extend((c, around, top) for c in ast.iter_child_nodes(n))
    inner = list(reversed(path or ()))
    return inner + ([root] if defs and inbody else []) + list(reversed(defs[:-1]))


def _bare_send_binding(call, defs, tree):
    """Why a bare `_send` call does not reach the module's binding, or None when it does: as Python looks the name up, the nearest
    scope around the call that binds `_send` in any form decides (_call_scopes, _binding_forms), a class body only as the call's
    own scope, and a `global` declaration on the way, with no binding beside it, hands the name to the module. The reason names
    the scope and each form that binds it there."""
    chain = _call_scopes(call, defs, tree)
    for k, sc in enumerate(chain):
        if isinstance(sc, ast.ClassDef) and k > 0: continue   # a class body's names are no scope of a function or comprehension in it
        forms, declared = _binding_forms(sc, "_send")
        if forms:
            if isinstance(sc, ast.Lambda): what = "a lambda around the call"
            elif isinstance(sc, _COMPS): what = "a comprehension around the call"
            else:
                name = ".".join(d.name for d in defs[:defs.index(sc) + 1])
                what = ("the class body of %s around the call" if isinstance(sc, ast.ClassDef) else "the enclosing function %s") % name
            return "a _send %s binds (%s%s)" % (what, _forms_said(forms), ", under a %s declaration" % declared if declared else "")
        if declared == "global": return None
    return None


def _forms_said(forms):
    """The binding forms _binding_forms names, each once, sorted and joined for a SERVED line (`a def statement and an import`)."""
    kinds = sorted(set(forms))
    return kinds[0] if len(kinds) == 1 else ", ".join(kinds[:-1]) + " and " + kinds[-1]


_NESTED_SCOPES = ((ast.Lambda, "a lambda"), (ast.ClassDef, "a nested class body"), (_COMPS, "a comprehension"),
                  ((ast.FunctionDef, ast.AsyncFunctionDef), "a nested def"))   # _type_rebinding's scopes inside a definition, as it names them


def _type_rebinding(d, writes, params):
    """(the name, its forms said) where one of a `_send` definition's own Content-Type writes (`writes`, every write under it) has
    as its value a name the typing reads from the call (`params`, routes_of's: the positional parameters after a method's first
    and the keyword-only ones) and the definition binds that name other than as that parameter anywhere in its body, in its own
    scope or a nested one; None otherwise. Its own writes are the ones routes_of's Content-Type loop skips: those whose innermost
    def or async def (a def's header counted as that def's, as Scan's walk counts it; a lambda, a comprehension and a class body
    are no def) is named `_send`, the definition itself or a def in it so named; a write in any other def inside it is that loop's.
    The bindings: every form _binding_forms names in the definition's body, the parameter itself dropped (an assignment,
    augmented or annotated, or an annotation alone; a loop, with, walrus or match target; an except name; a del; an import; a def
    or class statement; any other store, a type statement's name among them), the same forms and the parameters of every def,
    lambda, class body and comprehension in its body (_NESTED_SCOPES), a comprehension's target among them, a global or nonlocal
    declaration of the name in one, and a type parameter so named (3.12). The census types such a write from the call's argument,
    so a binding the write may read in its place is refused, never read past."""
    own, names, stack = {id(w) for w in writes}, set(), [(c, d.name) for c in ast.iter_child_nodes(d)]
    while stack:
        n, inner = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): inner = n.name
        if id(n) in own and inner == "_send" and isinstance(n.args[1], ast.Name) and n.args[1].id in params: names.add(n.args[1].id)
        stack.extend((c, inner) for c in ast.iter_child_nodes(n))
    for name in sorted(names):
        forms = list(_binding_forms(d, name)[0]); forms.remove("a parameter")
        for s in (n for top in d.body for n in ast.walk(top)):
            if type(s).__name__ in ("TypeVar", "ParamSpec", "TypeVarTuple") and s.name == name: forms.append("a type parameter")
            what = next((w for kinds, w in _NESTED_SCOPES if isinstance(s, kinds)), None)
            if what is None: continue
            got, declared = _binding_forms(s, name)
            forms.extend(("%s's parameter" % what if f == "a parameter" else f if f == "a comprehension's target" else "%s in %s" % (f, what))
                         for f in got)
            if declared: forms.append("a %s declaration in %s" % (declared, what))
        if forms: return name, _forms_said(forms)
    return None


def _method_self(fn, name):
    """What the route typing's receiver proof (_self_receiver) reads of the method `fn` and its first parameter `name`, by one
    iterative walk of fn's body: (the ids of the calls in the body that read `name` as fn's own binding, the ids of those that read it
    as the binding of a lambda or a comprehension around them, the forms by which `name` is bound again). A call in the body reads fn's
    binding outside a lambda's body and a comprehension that binds the name, as _binding_forms reads those scopes' own bindings (a
    comprehension's first iterable runs in fn's scope, and so do a lambda's defaults and a nested def's or class's header); a call in
    a nested def's or class's body is that scope's (routes_of's defs name it, so it never reaches here), and a call in fn's header
    is in neither set (a call in a nested def's or class's header is that scope's too, since Scan's walk enters the def before its
    header, so the header parts a nested def or class hands on hold no call that reaches here: marking them keeps the walk exact and
    no plant can red on it). The forms: every form _binding_forms names in fn's own scope besides the parameter itself (an assignment
    of any kind, a loop, with or except target, a walrus, a del, an import, a match capture, a def or class statement), a global or
    nonlocal declaration of the name there (which Python's compiler refuses for a parameter, so a file holding one never runs: kept
    so the reading of the tree is exact, and no plant can red on it), and each form by which a def or class statement nested in fn,
    at any depth, binds the name under a nonlocal declaration, which rebinds fn's parameter at run time. A lambda that binds the
    name puts a call in its body in `shadowed`, which keeps the proof exact, though routes_of refuses any `_send` call in a lambda's
    body first (_LAMBDA), so that refusal dominates the lambda arm."""
    forms, declared = _binding_forms(fn, name)
    again = [f for f in forms if f != "a parameter"] + (["a %s declaration" % declared] if declared else [])
    own, shadowed, stack = set(), set(), [(s, True) for s in fn.body]   # (node, whether the name there is fn's binding)
    while stack:
        n, mine = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            got, decl = _binding_forms(n, name)
            if decl == "nonlocal" and got: again.extend("%s in a scope nested in it under a nonlocal declaration" % f for f in got)
            stack.extend((h, mine) for h in _header(n)); stack.extend((b, None) for b in n.body); continue   # None: its own scope's
        if isinstance(n, ast.Lambda):
            binds = bool(_binding_forms(n, name)[0])
            stack.extend((h, mine) for h in _header(n)); stack.append((n.body, mine and not binds)); continue
        if isinstance(n, _COMPS):
            binds, first = bool(_binding_forms(n, name)[0]), n.generators[0].iter
            stack.extend((c, mine and not binds) for c in ast.iter_child_nodes(n) if not isinstance(c, ast.comprehension))
            for g in n.generators: stack.extend((c, mine if c is first else mine and not binds) for c in [g.target, g.iter] + g.ifs)
            continue
        if isinstance(n, ast.Call) and mine is not None: (own if mine else shadowed).add(id(n))
        stack.extend((c, mine) for c in ast.iter_child_nodes(n))
    return own, shadowed, again


def _decorator_def(dec, cls, defs, tree, facts):
    """Whether one decorator expression `dec` on a method defined directly in the body of the class statement `cls` (`defs`: the
    scopes around the method, innermost last) is a name, or a call of a name, that resolves by binding to a def statement the
    module binds once (the route typing's receiver proof, _self_receiver, the 04:52Z ruling on the eleventh round's layer iii): no scope Python
    may look the name up in before the module binds it in any form (_binding_forms), the class body that runs the decorator and
    each function around the class (a class body further out is no scope of it; a global declaration in one is not read, so a
    binding beside it refuses too, fail-closed); the module binds it exactly once, by a top-level def statement (not an async def),
    and nothing rebinds it (_module_bound, Result.rebinds: no function
    binds it under a global declaration and no module-level statement writes it); the module holds no star import and the file
    writes no name of its module namespace through a computed name and may not rewrite it at run time (_namespace_flags), each of
    which may bind the name. A call of such a name passes as the name does, the reviewer's reading of the ruling's "a name bound once
    to a module-level def", confirmed at 14:19Z (the kernel's four handlers carry `@_stage_marked(lambda self: ...)`, a call of a
    module-level def whose one argument is a lambda); any other expression (an attribute, a subscript, a lambda, a call of anything
    but a name) does not. What the def the name binds does with self is not read, and a decorator call's arguments are part of what
    it does (the stated limit the ruling names, its witness rtwit in the census module)."""
    node = dec.func if isinstance(dec, ast.Call) else dec
    if not isinstance(node, ast.Name): return False
    name = node.id
    if _binding_forms(cls, name)[0]: return False   # the class body that runs the decorator binds the name
    if any(_binding_forms(d, name)[0] for d in defs[:defs.index(cls)] if not isinstance(d, ast.ClassDef)): return False   # a function around the class does
    ns = facts["ns"]
    if ns["computed"] or ns["runtime"] or _module_info(tree)["star"] or name in facts["rebinds"]: return False
    return _module_bound(tree).get(name, 0) == 1 and any(isinstance(s, ast.FunctionDef) and s.name == name for s in tree.body)


def _stored_attrs(sc):
    """The attribute names one file stores or deletes on any object (the target of an assignment of any kind, a for, with or
    comprehension target, or a del: Scan's attribute stores), or names by a string constant, or constants _Served._const_text folds
    to one, as an argument that may name the attribute of a call of setattr, delattr, `__setattr__` or `__delattr__` (by that name
    or as an attribute so named: Scan.setter_calls, Scan._setter_args), for the route typing's receiver proof (_self_receiver): a
    method stored on its class from outside the class body. A setter whose name argument does not fold names no attribute here;
    a method replaced at run time through a name no code spells is outside the proof (routes_of's docstring)."""
    out = {n.attr for n in sc.ns_facts["stores"]}
    for call in sc.setter_calls:
        for a in Scan._setter_args(call) or ():
            c = _Served._const_text(a)
            if c is not None and type(c[0]) is str: out.add(c[0])
    return out


def _self_receiver(call, name, defs, tree, sc, facts):
    """Why the receiver `name` of the `<name>._send(...)` call is not self by binding, as a clause of _NOT_SELF, or None when it is
    (layer iii of the eleventh round's rulings: the route typing keys the receiver on its binding, never on the spelling self; `defs`: the scopes around
    the call, innermost last, a class among them). Self by binding is the first positional parameter of the method the call stands
    in, proven so by each of these, each refused by name where it fails:
    - the call stands in the body of a def or async def statement that is a statement of the body of the class around the call
      itself (not one inside a block of it, and not a def nested in a method), the method (a call in its header runs in the class
      body);
    - `name` is that method's first positional parameter;
    - the call reads that binding: no lambda or comprehension around the call inside the method binds the name (_method_self);
    - the method never binds the name again, in its own scope in any form or from a scope nested in it under a nonlocal declaration
      (_method_self);
    - each decorator on the method is a name, or a call of a name, the module binds once by a def statement (_decorator_def; the
      04:52Z ruling on the eleventh round's layer iii, in the reviewer's reading of 14:19Z); what that def, or the call's arguments, do with
      self is not read;
    - the class body binds the method's name by that one def statement and nothing else, and declares it neither global nor
      nonlocal (a class-body rebinding such as `do_GET = wrap(do_GET)` is a decorator in another spelling, and under a global
      declaration the def binds a module function, which any code may call with any first argument);
    - the file stores, deletes or names to a setter no attribute of the method's name (_stored_attrs: a method stored on its class
      from outside the class body, a decorator in another spelling again).
    `facts`: routes_of's per-file cache (the method walks, the decorator verdicts, the stored names)."""
    # the innermost scope around the call, a statement of the body of the innermost class around it itself: then a def or async def
    # statement (a class statement there would be the innermost class, and a class body never holds its own statement)
    cls, fn = next(x for x in reversed(defs) if isinstance(x, ast.ClassDef)), defs[-1]
    if not any(s is fn for s in cls.body): return "the call stands in no method defined directly in the class body of %s" % cls.name
    where = "%s.%s" % (cls.name, fn.name)
    first = (fn.args.posonlyargs + fn.args.args)[:1]
    if not first or first[0].arg != name: return "%s is not the first positional parameter of %s" % (name, where)
    key = ("self", id(fn))   # the method's facts, read once per method (the method held in the entry, so its id is never reused)
    if key not in facts: facts[key] = (fn,) + _method_self(fn, name) + (_method_why(fn, cls, defs, tree, sc, facts),)
    _, own, shadowed, again, why = facts[key]
    if id(call) in shadowed: return "a lambda or a comprehension around the call binds %s" % name
    if id(call) not in own: return "the call stands in the header of %s, which runs in the class body" % where
    if again: return "%s binds %s again (%s)" % (where, name, _forms_said(again))
    return why


def _method_why(fn, cls, defs, tree, sc, facts):
    """The per-method half of _self_receiver's proof, after the method's rebinding test: why the def fn, defined directly in the body
    of the class statement cls, may not be what the class holds under its name when the server calls it, or None: a decorator other
    than a name, or a call of a name, the module binds once by a def statement (_decorator_def); a binding of its name in the class
    body besides that one def statement, or a global declaration of it there (the def then binds a module function, which any code
    may call with any first argument); its name stored, deleted or named to a setter as an attribute anywhere in the file
    (_stored_attrs)."""
    where = "%s.%s" % (cls.name, fn.name)
    bad = next((d for d in fn.decorator_list if not _decorator_def(d, cls, defs, tree, facts)), None)
    if bad is not None:
        return ("%s carries a decorator other than a name, or a call of a name, that the module binds once by a def statement (%s)"
                % (where, ast.unparse(bad)[:40]))
    forms, declared = _binding_forms(cls, fn.name)
    if forms != ["a def statement"] or declared:
        return "the class body of %s binds %s other than by that one def statement (%s)" % (
            cls.name, fn.name, _forms_said(forms + (["a %s declaration" % declared] if declared else [])))
    if "stored" not in facts: facts["stored"] = _stored_attrs(sc)
    if fn.name in facts["stored"]: return "the file stores, deletes or names to a setter an attribute named %s, which may replace the method" % fn.name
    return None


def _global_binder(decls, name):
    """The first function or class body, in source order, that declares `name` global and binds it there in any form
    (_binding_forms), so rebinding the module's name at run time: (its enclosing defs, innermost last; the forms), from one file's
    declarations (Result.global_decls, Scan's record of every `global` declaration in a function or class body); None when none
    does (a declaration with no binding beside it only reads the module's name)."""
    for defs, names in decls:
        if name in names:
            forms, declared = _binding_forms(defs[-1], name)
            if forms and declared == "global": return defs, forms
    return None


def routes_of(rel, tree, sc, res):
    """The routes of one Python file's served pages and scripts, read from its candidates (Scan.sends, Scan.ctype_writes,
    Scan.responds and Scan.send_refs): every `_send` call the scan reads (spelled `_send(...)` or `<x>._send(...)`) is typed
    through the `_send` definition it reaches in this file, the one def or async def statement that binds `_send` there, direct
    in the call's own class body (a call through self: a call on a name that is self by binding, the first positional parameter of
    the method the call stands in, however it is spelled, never by the spelling self; _self_receiver names the proof and its
    conjuncts) or in the module (a bare call): the parameter that definition's
    Content-Type write names, by position or keyword, or the value it writes (the kernel's Handler._send its `ctype`, the postal
    bus's application/json). A file that binds `_send` more than once outside function bodies (the module and every class body
    counted together, a class body a function body defines included, in any binding form but a comprehension's target, which binds
    only in its comprehension: _send_bindings) or other than by one def statement direct in a class body or the module, or where a
    function or a class body binds it under a `global` declaration, rebinding the module's name at run time (_global_binder over
    Result.global_decls), is a SERVED line at each of its `_send` calls, and so is a bare call that
    reaches a `_send` bound inside a function, a lambda, a comprehension or a class body around it, in any form, the line naming the
    scope and the binding (_bare_send_binding: Python calls that binding, not the module's), a call that reaches no definition the
    census reads, the line saying why (a `_send` the call's own class body does not bind, for a call through self: inherited or set
    at run time; a call on a name in a class body that is not self by binding, the line naming the conjunct of the proof it fails
    (_NOT_SELF: the call outside the body of a method defined directly in that class body, the name not the method's first positional
    parameter, a lambda or a comprehension around the call binding it, the call in the method's header, the method binding it
    again in any form or a scope nested in it rebinding it under a nonlocal declaration, a decorator on the method other than a name,
    or a call of a name, that the module binds once by a def statement, a binding of the method's name in the class body besides
    its def statement or a declaration of it there, or the method's name stored, deleted or named to a setter as an attribute
    anywhere in the file); one reached
    in a class body through a receiver that is no name (an object other than self), or through an attribute outside any class body;
    a `_send` no
    scope the bare call looks it up in
    binds, the module included; and, in a file that names `_send` nowhere but as the called name of those calls, so binds it nowhere
    at all (_names_send), a definition this file does not hold), a call of a definition carrying any decorator, whose parameters the
    census does not read, and a bare call in a module
    that holds a star import
    (_module_info); an override of `_send` in a subclass another file defines is not read, a call through self typed through its
    own class body's definition, and neither is what a decorator the proof accepts does with self (a def of the file may hand the
    method another object in the instance's place) nor a method replaced on its class at run time through a name no code spells
    (a setter whose name does not fold, a class `__dict__`, a metaclass). A call to a definition that writes no Content-Type is a frame writer's (FRAME_WRITERS) or a SERVED line; the type is
    resolved (_ctype_values, through a module name no code writes after binding it: _module_consts less the names Result.writes
    records, and through a local whose every binding _scopes_of reads) and a script-running one (_script_type) makes the call a
    route whose text the served pass reads; an unresolved type is a SERVED line. A route's page body is the call's second
    positional argument, read only when the call passes it positionally with no starred argument before it and no `**` and the
    definition's one output is its one write of that parameter, nothing in a method's definition binding self again or declaring it
    global, and nothing in its signature or body outside the node kinds, in their roles, of the kernel's Handler._send (_body_param,
    _send_gate, which lists them by kind): the one write of the page parameter, the definition's last statement, directly after its
    one `self.end_headers()`; the header calls on self, send_response with its one argument and send_header; isinstance, str, len
    and getattr of self, each unbound and unrebound (the file's Result.rebinds decides with the module's bindings whether a builtin
    the definition calls is the builtin, and a file that names `__builtins__` as a name, imports the builtins module, writes a
    module that may be the builtins module, writes its module namespace through a computed name or may rewrite it or the builtins
    at run time has none, in the forms _namespace_flags lists); the one rebinding of the page parameter to itself or to itself
    encoded by `.encode("utf-8")`, alone or as the branches of an `isinstance(<page>, str)` test; a loop over a parameter's items; tests
    on a parameter or on getattr of self; header values built from string constants holding no CR or LF, parameters, the loop's
    targets, attributes read on self, str, len and a `%` format on a string constant; and a signature of positional parameters,
    none positional-only, with None defaults and no annotation. A page function a function encloses, a `_send` in a class a
    function defines, and a `_send` call in a lambda's body (the call in the body of a lambda among _call_scopes, which the walk
    records in Scan.in_lambda), each a SERVED line by name (_ENCLOSED, _LAMBDA: after the bare call's own binding reason and
    before any typing), since the enclosing function's or lambda's names (a builtin or a module name it shadows, the page's text
    or its type among them) are no scope the census reads; a call where one of the definition's own Content-Type writes (each write
    whose innermost def is the definition or a def in it itself named `_send`, the writes the Content-Type loop below skips) names a
    parameter the type is read from and the definition binds that name other than as that parameter anywhere in its body, in any
    form _type_rebinding names, a SERVED line by name before any typing (_TYPE_REBOUND), since the census reads that write's type
    from the call's argument;
    any other script-running call (a keyword body, a starred or `**` call, a definition with any other output, whose written body is
    another parameter, a local or an expression, or that writes nothing, and a definition holding any other statement or
    expression, among them a call, a store or a nested def the table does not list) is a SERVED line by name, its reason naming the
    road or the node kind and its line (_unread_body), and no route. What the definition's text does not hold is not read: a header
    value, and a response a Content-Type in the headers argument, passed or defaulted, makes a page (the call is typed by its
    content-type argument);
    code the definition runs through an object it is handed (a parameter's methods, its mapping's items, its __str__); code behind a
    name the definition calls or reads on self, a header method, a property or `__getattr__`, however the class, a base or other
    code defines or replaces it, and any stream that code writes (a module global holding the socket, written by a method the
    definition calls on self, among them); a `_send` replaced at run time through a name no code spells (setattr or a class
    `__dict__` with a computed name, a metaclass namespace key, a base's `__init_subclass__`); and a module namespace rewritten at
    run time by code outside the forms _namespace_flags reads: a listed name reached any other way or a name the list does not
    hold (through `__self__` of a builtin, a container or a copy of a namespace mapping other than the file's own module's or the
    builtins' (one of those used other than in a key position the census reads is a run-time form), a module's own `__setattr__` or
    `__delattr__` method, a listed name, attrgetter or methodcaller imported from a module other than its own, a name built at run
    time, gc or ctypes among them, and through a module reached by a tuple or list unpacking, an inline walrus,
    `sys.modules.__getitem__`, a for-loop target, a parameter default or a starred argument) is outside the list
    and not seen (another walked file's import statement that may bind the module refuses the file whole: scan, _page_importers; a
    module reached any other way, the stated limit), and so is a content type a handler rebinds at run time through its own frame
    (the frame's locals, which Python 3.13 and later write through to the function): the census reads a content type that is a string
    constant or a name bound once to one as the handler's text binds it (the stated limit on those versions, its witness the (x)
    case's frwt), and refuses by name a content type it reads any other way, so no frame can rewrite an intermediate it had read. Any
    other reference to `_send` (a read
    of it that is not a call's
    function, a store or delete of an attribute so named, or a string equal to `_send`) is a SERVED line; a call through a name
    computed at
    run time is not read. Every Content-Type header written outside a `_send` definition (each write whose innermost def is not
    named `_send`, one in a def nested in a `_send` under another name among them) is typed the same way (one in a lambda's body
    refused by name first, _LAMBDA, since a parameter of the lambda may shadow the type's name), and a script-running
    one is a SERVED line (the served pass follows a page's text through `_send` alone); a function outside `_send` that answers
    (send_response) more often than it writes a Content-Type header is a SERVED line, the browser typing that body by sniffing
    it. SERVED_ALLOW excuses a place by its function and expression (a `_send` call's place by the call's function, `self._send` or
    `_send`), save an unread body. Returns the routes, (call, the
    enclosing function, the class statement the call stands in (the served pass keys the route class on it, never on its name
    alone: _Served._top_class), the script-running type, the body expression), sorted by line."""
    ns = res.ns.get(rel) or _NS_NONE   # a file that writes its module namespace through a computed name, or may rewrite it at run
    consts = {} if ns["computed"] or ns["runtime"] else _module_consts(tree)   # time, reads no module constant
    written = {x for x in res.writes.get(rel, {}) if x in consts}   # the module names some code writes after binding them
    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    routes, cache, typed = [], {}, {}
    facts = {"ns": ns, "rebinds": res.rebinds.get(rel, {})}   # the receiver proof's per-file cache (_self_receiver)

    def scopes(defs):
        k = tuple(id(d) for d in defs)
        if k not in cache: cache[k] = _scopes_of(defs)
        return cache[k]

    def allowed(where, expr, call):
        key = ("%s:%s" % (rel, where), ast.unparse(expr) if expr is not None else "")
        if key not in SERVED_ALLOW: return False
        res.allow_hits.setdefault(key, set()).add((call.lineno, call.col_offset)); return True

    def judge(call, where, expr, defs, direct):
        """The script-running type of one candidate, or None: allowlisted, not script-running, or refused by name here."""
        if allowed(where, expr, call): return None
        vals = _ctype_values(expr, scopes(defs), consts, written) if expr is not None else None
        if vals is None:
            res.problems.append("SERVED %s:%d serves a response whose content type the census cannot resolve (%s in %s): spell it so the "
                                "scan reads it, or name the call in SERVED_ALLOW with its reason" % (rel, call.lineno, ast.unparse(expr)[:60] if expr is not None else "no value", where))
            return None
        if not _ctype_simple(expr, scopes(defs), consts, written):   # the content-type face of the frame-local limit refused where one
            # check does it at 0 live (the 00:28Z rule): a content type the census resolves through anything but a string constant or a
            # name bound once to one, which a frame may rewrite at run time, the census reading only what its text binds
            res.problems.append("SERVED %s:%d serves a response whose content type the census reads other than as a string constant or a "
                                "name bound once to one (%s in %s), which code may rewrite through the function's frame at run time: spell "
                                "it as a constant, or name the call in SERVED_ALLOW with its reason" % (rel, call.lineno, ast.unparse(expr)[:60], where))
            return None
        script = sorted(v for v in vals if _script_type(v))
        if script and direct:
            res.problems.append("SERVED %s:%d writes Content-Type %s outside _send (%s): the census follows a page's text only through _send; "
                                "serve it there, or name it in SERVED_ALLOW with its reason" % (rel, call.lineno, script[0], where))
            return None
        return script[0] if script else None

    rebound = None   # why every `_send` call of the file is refused when a function or class body binds `_send` under a `global` declaration
    one_def = None   # whether the file binds `_send` outside function bodies at most once, and that once by a def statement direct in a body (_send_bindings)
    anywhere = None   # whether the file names `_send` anywhere but as its calls' called name (_names_send), read for a call that reaches no definition
    for call, defs, where in sc.sends:
        fn = next((x for x in reversed(defs) if not isinstance(x, ast.ClassDef)), None)
        cls = next((x for x in reversed(defs) if isinstance(x, ast.ClassDef)), None)
        f, d, method = call.func, None, False
        if rebound is None:   # a body that binds `_send` under a `global` declaration rebinds the module's name at run time: every call refused
            got = _global_binder(res.global_decls.get(rel, ()), "_send")
            rebound = ("a _send %s binds under a global declaration (%s), rebinding the module's name at run time" % (
                ("the class body of %s" if isinstance(got[0][-1], ast.ClassDef) else "the function %s") % ".".join(x.name for x in got[0]),
                _forms_said(got[1])) if got else False)
        if rebound:
            if not allowed(where, f, call):
                res.problems.append("SERVED %s:%d calls _send on %s, %s: the census cannot read the response's content type"
                                    % (rel, call.lineno, ast.unparse(f)[:40], rebound))
            continue
        if one_def is None:
            binds = _send_bindings(tree, sc.inner_classes)
            one_def = len(binds) == 1 and isinstance(binds[0][0], (ast.FunctionDef, ast.AsyncFunctionDef)) and binds[0][1]
            if not binds: one_def = True   # no binding in that population: each call reaches no definition the census reads, refused below by its reach
        if not one_def and not allowed(where, f, call):
            res.problems.append("SERVED %s:%d calls _send on %s, a _send bound more than once, or other than by one def statement, in %s: the "
                                "census types a call only through the one def statement that binds _send in a class body or the module"
                                % (rel, call.lineno, ast.unparse(f)[:40], rel)); continue
        if not one_def: continue
        not_self = None   # why a name receiver in a class body is not self by binding (_self_receiver), read where the call reaches no definition
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and cls is not None:   # a call through a name: self by binding, never by its spelling
            not_self = _self_receiver(call, f.value.id, defs, tree, sc, facts)
            if not_self is None:   # the calling method's own first parameter, however spelled: its class is cls
                d = next((b for b in cls.body if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) and b.name == "_send"), None); method = True   # the file's one binding, when this class body holds it
        elif isinstance(f, ast.Name):
            why = _bare_send_binding(call, defs, tree) or (_STAR if _module_info(tree)["star"] else None)   # a scope around the call binds it, or a star import may
            if why is not None:
                if not allowed(where, f, call):
                    res.problems.append("SERVED %s:%d calls _send on %s, %s: the census cannot read the response's content type"
                                        % (rel, call.lineno, ast.unparse(f)[:40], why))
                continue
            d = funcs.get("_send")
        # a lambda around the call (the call in its body, a Lambda among _call_scopes; Scan.in_lambda records it in the walk): its
        # parameters are no scope the census reads, so it would take a name one binds (the page's text, its type, a builtin) for the
        # module's; after the bare call's own binding reason, which a lambda's parameter named `_send` keeps, and before any typing
        if id(call) in sc.in_lambda:
            if not allowed(where, f, call):
                res.problems.append("SERVED %s:%d calls _send on %s, %s: the census cannot read the response's content type"
                                    % (rel, call.lineno, ast.unparse(f)[:40], _LAMBDA))
            continue
        if d is None:   # the call reaches no definition the census reads: why, by the reach
            if anywhere is None: anywhere = _names_send(tree, [c for c, _, _ in sc.sends])
            why = ("a definition this file does not hold" if not anywhere else
                   _NOT_SELF % not_self if not_self is not None else
                   "a _send the call's own class body does not bind (inherited or set at run time, which the census does not follow)" if method else
                   "a _send no scope the bare call looks it up in binds, the module included" if isinstance(f, ast.Name) else
                   "a _send reached through an object other than self, which the census does not follow" if cls is not None else
                   "a _send reached through an attribute outside any class body, which the census does not follow")
            res.problems.append("SERVED %s:%d calls _send on %s, %s: the census cannot read the response's content type"
                                % (rel, call.lineno, ast.unparse(f)[:40], why)); continue
        dkey = "%s:%s%s" % (rel, cls.name + "." if method else "", d.name)
        if d.decorator_list:   # a decorator may rewrite the signature: its parameters are not read, at either reach
            if not allowed(where, f, call):
                res.problems.append("SERVED %s:%d answers through %s, a decorated _send definition, whose parameters the census does not read (in %s)"
                                    % (rel, call.lineno, dkey.split(":", 1)[1], where))
            continue
        if id(d) not in typed: typed[id(d)] = [c for c in ast.walk(d) if _is_ctype_write(c)]
        writes = typed[id(d)]
        if not writes:
            if dkey in FRAME_WRITERS: res.allow_hits.setdefault(("frame", dkey), set()).add((call.lineno, call.col_offset)); continue
            res.problems.append("SERVED %s:%d answers through %s, which writes no Content-Type header: name it in FRAME_WRITERS if it answers "
                                "no HTTP request, or type its answer" % (rel, call.lineno, dkey.split(":", 1)[1])); continue
        a = d.args; pos = [x.arg for x in a.posonlyargs + a.args]; defaults = dict(zip(pos[len(pos) - len(a.defaults):], a.defaults))
        me = pos[0] if method and pos else None
        if method: pos = pos[1:]
        # a write of the definition's own (its innermost def the definition, or a def in it named `_send`: the writes the loop below
        # skips) that names a parameter the typing reads from the call, where the definition binds that name other than as that
        # parameter anywhere in its body (a lambda's parameter, a comprehension's or loop target, an assignment, in any form): the
        # write may carry that binding, not the call's argument, so the call is refused by name before any typing (_type_rebinding)
        if ("rebound", id(d)) not in typed: typed[("rebound", id(d))] = _type_rebinding(d, writes, pos + [x.arg for x in a.kwonlyargs])
        if typed[("rebound", id(d))]:
            if not allowed(where, f, call):
                res.problems.append("SERVED %s:%d calls _send on %s, %s: the census cannot read the response's content type"
                                    % (rel, call.lineno, ast.unparse(f)[:40], _TYPE_REBOUND % typed[("rebound", id(d))]))
            continue
        if ("body", id(d)) not in typed: typed[("body", id(d))] = _body_param(d, pos, me, tree, res.rebinds.get(rel, {}), ns["computed"] or ns["builtins"] or ns["runtime"])
        # the page function, or for a call through self the class whose body holds `_send`, inside a function: that function's names
        # (a builtin or a module name it shadows among them) are no scope the census reads, so neither the definition nor the page is read
        held = fn if fn is not None else cls if method else None
        enclosed = held is not None and any(isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) for x in defs[:defs.index(held)])
        unread = _ENCLOSED if enclosed else _unread_body(call, *typed[("body", id(d))])
        for w in writes:
            v = w.args[1]
            if isinstance(v, ast.Name) and v.id in pos + [x.arg for x in a.kwonlyargs]:   # the type is the call's argument for that parameter
                kw = {k.arg: k.value for k in call.keywords if k.arg}
                idx = pos.index(v.id) if v.id in pos else None
                if idx is not None and idx < len(call.args) and not any(isinstance(x, ast.Starred) for x in call.args[:idx + 1]): expr = call.args[idx]
                elif v.id in kw: expr = kw[v.id]
                else: expr = defaults.get(v.id)
                ctype = judge(call, where, expr, defs, False)
            else:   # the definition writes the type itself
                ctype = judge(call, dkey.split(":", 1)[1], v, [d], False)
            if ctype is None: continue
            if unread:   # a script-running call whose body the census does not read: refused by name, never read at a guessed position
                res.problems.append("SERVED %s:%d serves %s through %s, whose page body the census does not read (%s, in %s): the census reads "
                                    "a body as the call's second positional argument, the parameter the definition writes; pass it so"
                                    % (rel, call.lineno, ctype.split(";")[0], dkey.split(":", 1)[1], unread, where))
                continue
            routes.append((call, fn, cls, ctype, call.args[1]))   # the route class by its class statement (choice 1 of the eleventh round's rulings)
    for node, defs, where in sc.send_refs:   # a reference to `_send` that is no call the scan reads: its calls would be no routes
        if not allowed(where, node, node):
            res.problems.append("SERVED %s:%d refers to _send other than by a call the scan reads (%s in %s): the routes are the calls "
                                "spelled _send(...) or <x>._send(...); call it so, or name the place in SERVED_ALLOW with its reason"
                                % (rel, node.lineno, ast.unparse(node)[:60], where))
    counts = {}   # per function outside _send: [its Content-Type writes, its answers the allowlist does not name, the function's where]
    for call, defs, where in sc.ctype_writes:
        inner = next((x for x in reversed(defs) if not isinstance(x, ast.ClassDef)), None)
        if inner is not None and inner.name == "_send": continue   # a definition's own write, read at each call above
        counts.setdefault(id(inner), [0, 0, where])[0] += 1
        if id(call) in sc.in_lambda:   # a lambda around the write: its parameter may shadow the type's name, refused before typing
            if not allowed(where, call.args[1], call):
                res.problems.append("SERVED %s:%d writes a Content-Type header of %s in %s, %s: the census cannot read the type it writes"
                                    % (rel, call.lineno, ast.unparse(call.args[1])[:60], where, _LAMBDA))
            continue
        judge(call, where, call.args[1], defs, True)
    for call, defs, where in sc.responds:
        inner = next((x for x in reversed(defs) if not isinstance(x, ast.ClassDef)), None)
        if inner is not None and inner.name == "_send": continue
        entry = counts.setdefault(id(inner), [0, 0, where])
        if not allowed(where, call, call): entry[1] += 1
    for n_types, n_answers, where in counts.values():
        if n_answers > n_types:
            res.problems.append("SERVED %s:%s answers %d times outside _send and writes %d Content-Type headers: a body with no declared type is "
                                "typed by the browser's sniffing; write the header, or name a response with no body in SERVED_ALLOW with its "
                                "reason" % (rel, where, n_answers, n_types))
    return sorted(routes, key=lambda r: r[0].lineno)


# Layer iv of the eleventh round's rulings (the eleventh round's fail-closed census, with the 04:52Z ruling on its measurement and the
# 07:37Z ruling on its fourth form): a container the served pass reads is read whole only where EVERY occurrence of its name, resolved
# by binding, is one of the proven forms; any other occurrence refuses it by the rule. These are the methods the fourth form reads a
# container through without handing it to other code, the union of the closed sets per type in _TYPE_READS below (a dict's get, keys,
# values, items and copy; a list's index, count and copy; a tuple's index and count; a set's copy; index and count only with a constant
# argument, _COMPARED), each checked against the set of the type the one binding gives: a list, dict, set or tuple literal, or a call of
# parse_qs (a dict); a binding to any other value slot gives no type, and every read method and subscript load on it refuses
# (_CT_UNTYPED). An item a read method returns, or a subscript load returns, is a value the census follows by binding like any other
# (condition 2 of the 07:37Z ruling: _flow, _Served._containers), read only through the closed set of its own type (the item rule
# below). The append or extend of one plain argument, on the container itself, is the one growth it reads. _CHANGERS holds the in-place
# changers of a list, a dict, a set, a deque and an OrderedDict (every method of those five types that changes the object, `__init__` and
# popleft among them, with the spelled-out dunders that write), each of which, called on a name or read off it unbound, makes a name
# bound to anything but a literal a container whose every occurrence the proof reads (_Served._containers's changes: what marks a
# container, never what reads an item); a name every binding of which is a plain assignment of a call is marked by any use outside a
# closed set instead (any method outside _READ_THROUGH below, any attribute read), and a module name by any method outside
# _READ_THROUGH on it or an item of it, any attribute read off it and any operand hand-off (Scan.visit_Call, Scan.visit_Attribute,
# Scan.coperands: layer iv's module side)
_READ_METHODS = frozenset(("get", "keys", "values", "items", "index", "count", "copy"))
# The methods whose return is drawn from their receiver's text (the eleventh round's rulings, the reviewer's 14:42Z item 3 and 16:33Z
# E2: the allowlist _Served._undrawn reads for a method called on a receiver whose text the pass reads, or on a base whose own text it
# does not read that derives through a call handed arguments it reads or is one of the seven builtins' names called unbound): the
# substring family (removeprefix and removesuffix; strip, lstrip and rstrip
# are the text-method arm's), the pieces family (split, rsplit, splitlines, partition and rpartition, substrings whose later join is
# the stated join limit), the container reads above (an item, a view, a copy or an int) and a regular-expression match's group (a
# substring of the text searched); any other method on such a receiver is refused by name (_UNDRAWN on a receiver whose text the
# pass reads, _UNDRAWN_BASE on a base whose own text it does not read, each reason true where it is given)
_DRAWN = frozenset(("removeprefix", "removesuffix", "split", "rsplit", "splitlines", "partition", "rpartition", "group")) | _READ_METHODS
# The methods the census reads a text through, so a call of one changes nothing it reads (layer iv: the closed set a name bound only to
# calls may be read through, _Served._containers, and a module name, Scan.visit_Call): _DRAWN, and the text-method arm's join, format,
# format_map, replace, strip, lstrip, rstrip and encode, which resolve reads as their own shape
_READ_THROUGH = _DRAWN | frozenset(_TEXT_CALLS + _FOLLOW_ANY)
_UNDRAWN = "a .%s() method whose return is not drawn from its receiver's text, on a receiver the census reads"   # _Served._undrawn's
_UNDRAWN_BASE = ("a .%s() method called on a base whose own text the census does not read, so the census does not compute the text it "
                 "returns")   # _Served._exempt_undrawn's, at receiver's exempt point (true whether or not the method's return is drawn
# from its receiver's text: a drawn method's, strip among them, returns a piece of the base's own text, which the census does not read)
_GROWERS = ("append", "extend")
_CHANGERS = frozenset(_MUTATORS + _DUNDER_MUTATORS + ("sort", "reverse", "appendleft", "extendleft", "rotate", "move_to_end", "difference_update",
                                                      "intersection_update", "symmetric_difference_update", "popleft", "__init__", "__setattr__",
                                                      "__delattr__"))
_CONTAINER = "a container the census does not prove it reads whole (%s)"   # _Served._containers's refusal, the clause naming the conjunct
_TYPE_READS = {"dict": frozenset(("[]", "get", "keys", "values", "items", "copy")), "list": frozenset(("[]", "index", "count", "copy")),
               "tuple": frozenset(("[]", "index", "count")), "set": frozenset(("copy",))}
_COMPARED = ("index", "count")
_CT_HANDED = "an operand of a binary operation, a comparison or `in`, which Python hands to the other operand's method"
_CT_INDEX = "a subscript's index or a slice's bound, which Python hands to the subscripted object's method"
_CT_AUGV = "the value of an augmented assignment, which Python hands to its target's method"
_CT_BIND = "bound whole to another name (%s)"
_CT_READ = "read other than as a read method's receiver or a subscript load's base (%s)"
_CT_TYPE = "a method called on it other than append, extend or a read method of its type (%s)"
_CT_ITEM = "an item of it handed to another object's method (%s)"
_CT_SUB = "a subscript load on it, a set by its one binding"   # a typed container: a subscript load is a dict's, a list's or a tuple's read
_CT_UNTYPED = ("read through %s where its one binding, neither a literal nor a call of parse_qs, gives it no type whose read methods "
               "the census knows")   # a container bound to any other value slot (dict(...), an import's call): no read method or subscript load reads it
# An item of a container the proof reads (a read method's or a subscript load's result, directly or through a name bound to it or to a
# new object holding it) is read only through the closed read set of the item's own type, the type known as the container's is, from the
# one binding and the values stored or appended into the container (_Served._item_types, _value_type): condition 1 of the 07:37Z ruling
# applied to its items. Any other method called on it, a read method or a subscript load outside that set, a spelled-out dunder among
# them, whether the return is used or dropped, an attribute read off it other than as a method's callee, and a method spelled on a class
# (a builtin class, or a class of collections imported as the module or by name: _Served._class_callee) handed it as its first argument
# refuse the container; a str has no read set, nor has an item whose type the census does not know (a call's return, a name it does not
# follow), so any method or subscript load on one refuses (_Served._containers)
_CT_ITEM_USE = "%s on an item of it, not a read of the item's type (%s)"
_CT_ITEM_UNKNOWN = "%s on an item of it, whose type the census does not know"
_CT_ITEM_ATTR = "an attribute of an item of it read other than as a method's callee (%s)"
_CT_THROUGH = "through %s, a name the function binds to an item of it or to a new object holding one: %s"
_CT_CLASS = "handed to %s, a method spelled on a class, as the object it runs on"   # a builtin class or a class of collections: _Served._class_callee
_CT_ITEM_CLASS = "an item of it " + _CT_CLASS
_AS_DEFAULT = "a default of a function or a lambda"   # _flow's escape detail for a value a def's or a lambda's default holds
_CT_AUG = ("changed in place through %s, a name the function binds to it or to an item of it, by an augmented assignment, which runs "
           "the target's own method")   # _Served._containers's, at an augmented assignment to such a name ("aug")
# A function whose frame's local mapping is reached, or run as code, hands out or mutates the real container object on every CPython
# version (a mutation, not a rebind, so it needs no 3.13 write-through), so the container proof cannot prove a container it binds is read
# whole: a page function whose own subtree holds, anywhere and whether called or not, one of the SEVEN bare names in _FRAME_NAMES (locals,
# vars, exec, eval, _getframe, currentframe, getargvalues), one of the FOUR attributes in _FRAME_ATTRS (_getframe, currentframe,
# getargvalues, f_locals) spelled as an attribute on any receiver, or a name that a statement of the module's or the function's own body,
# outside every def, class or lambda statement it nests (header and body alike), binds to one of those primitives, its bound value the
# primitive's own bare name or attribute (a plain or annotated assignment, a walrus, an unpacking of a list or tuple literal into a
# target list of AS MANY elements, each plain name there bound to the value at its place, beside a starred or nested target too, or a
# `from ... import` of one of the seven names), and any name such a statement binds to a name so bound (a chained
# alias), resolved among those statements (_frame_alias_names), refuses every container it binds by name (_Served._containers,
# _reaches_frame). The check is syntactic: it reads the spelling, not a call, so a name merely spelled like a primitive refuses too (the
# safe side), and its reason names the spelling found (_FRAME_CONTAINER, `its function spells <the spelling>`), not a frame reached. One
# check at 0 live (no live route function reaches its frame). A change to the locals at run time through a frame object, exec or eval
# reached in ANY OTHER spelling is the stated precondition (the realm precondition's shape), outside what the census reads, each road
# passing silently; among them: locals or vars reached as an ATTRIBUTE on a receiver (`x.locals`, `sys.modules["builtins"].locals()`), and
# exec or eval reached as an attribute (`builtins.exec`), since none of locals, vars, exec, eval is in _FRAME_ATTRS (its witness fratr is
# `locals` reached as an attribute, frxr is exec so reached, frev eval); f_locals as a bare NAME (`f_locals(fr)`), since f_locals is in
# _FRAME_ATTRS alone, not _FRAME_NAMES (bfl2); one of the four attributes named by a STRING, `getattr(inspect.stack()[0].frame,
# "f_locals")`, since the check matches an attribute node and inspect.stack and frame are in neither set (fgs2); and any binding of a name
# to a primitive that _frame_alias_names does not read: a plain name among the targets of an unpacking whose targets are NOT AS MANY as
# its values (fsst `_PS, *_pr = locals, 1, 2`, two targets and three values) and a name a NESTED target binds (fsnt `(_PN, _pz), _py =
# (locals, 1), 2`), each of which the unpacking arm skips; an alias whose bound value is any other expression (tx4 a
# module alias bound to an if-expression, `_TX4 = locals if True else None`; txc one bound to a call's return, `_TXC = _ident(locals)`);
# and a binding in the header or the body of a def, class or lambda statement, which _own_stmts and _module_level_stmts skip whole: a
# walrus in a module-level def's default (tx2), a `from ... import` a def nested in the function makes (nstb), whose imported spelling
# sits in the alias node and whose alias name ast.walk does not match, an assignment inside a module-level def's body (tx3), an
# assignment in a module-level class's body, read as the class's attribute (frcl `class _FrK: fl = locals`, `_FrK.fl()`), or a walrus in
# a module-level lambda's default (flam `lambda z=(_LW := locals): z`). But a binding a
# nested def, class or lambda makes by an ASSIGNMENT carries the primitive's spelling in the function's subtree, which ast.walk(fn) reads,
# so it refuses (nsta), as does a name merely spelled like a primitive (lcsy binds `currentframe` to a string). Code the page function runs
# that the census does not read (a helper it calls as a statement, a method on self, a context manager it enters), reaching the caller's
# frame, is not read here (the census reads no such code's body for its frame reach): the frame-container stated limit, its witness fhlp. A
# scalar a frame rewrites, not mutated, is a rebind Python 3.13 and later serve: the frame-local stated limit, its witnesses frwt and frwb
_FRAME_NAMES = frozenset(("locals", "vars", "exec", "eval", "_getframe", "currentframe", "getargvalues"))   # a name that reaches or runs code in a frame's locals mapping
_FRAME_ATTRS = frozenset(("_getframe", "currentframe", "getargvalues", "f_locals"))          # an attribute that reaches a frame, on any receiver
_FRAME_CONTAINER = ("its function spells %s, which names a frame primitive or an alias of one, and a change through a frame's local mapping "
                    "is not read")   # _Served._containers's, at a frame reach, naming the spelling _reaches_frame found
_DISPLAYS = (ast.List, ast.Dict, ast.Set, ast.ListComp, ast.DictComp, ast.SetComp)   # a binding to one of these makes a name a container
_FLOWS = (ast.BinOp, ast.List, ast.Tuple, ast.Set, ast.Dict) + _COMPS   # a node that holds a value it is handed in a new object (_flow)
_NO_ROOTS = frozenset((ast.Constant, ast.JoinedStr, ast.Compare, ast.UnaryOp, ast.Lambda))   # a value that reads through no name (_flow_roots: none)
_READS = (ast.FormattedValue, ast.JoinedStr, ast.Compare, ast.UnaryOp, ast.Expr, ast.If, ast.While, ast.Assert, ast.Raise, ast.Slice, ast.Return,
          ast.Yield, ast.YieldFrom, ast.Lambda, ast.match_case)   # a node that consumes a value it holds


_UNSET = object()   # a name's type the container proof's fixpoint has not read yet (_Served._containers)


def _meet(a, b):
    """The type two values share, as the container proof reads an item's type: a pair (the kind, "dict", "list", "tuple", "set" or
    "str", and the type of the items it holds), None where it does not know it, _UNSET for no value read yet; the same kind with the item
    types met in turn, or None where the kinds differ or either is not known."""
    if a is _UNSET: return b
    if b is _UNSET: return a
    if a is None or b is None or a[0] != b[0]: return None
    return (a[0], _meet(a[1], b[1]))


def _settled(t):   # a type with any item type still unread (an empty literal's, which nothing fills) read as not known
    return None if t is _UNSET or t is None else (t[0], _settled(t[1]))


def _value_type(e, types):
    """The type (_meet's pair) of the value `e`, as the container proof reads an item's: a name's from `types` (the container's own,
    from its one binding, and those of the names bound to it, to an item of it or to a new object holding one; None for any other name); a
    string constant a str; a list, tuple or set display that kind, holding its elements' types met (a starred element's not known); a
    dict display a dict holding its values' (a ** entry's not known); a subscript load on a dict, a list or a tuple the type of the items
    it holds, and a slice of a list or a tuple its own type; a read method of the receiver's own type (_TYPE_READS) the type it returns: a
    copy the receiver's, a dict's get the type of its items met with the default's, and keys, values, items, index or count one it does
    not know (a view or a number); a boolean operation's operands and an if-expression's branches met; a walrus its value's. Any other
    value (a call, an attribute, a number, a subscript load or a read method its receiver's type does not read) is one it does not know."""
    t = type(e)
    if t is ast.Name: return types.get(e.id)
    if t is ast.Constant: return ("str", None) if type(e.value) is str else None
    if t is ast.List or t is ast.Tuple or t is ast.Set:
        held = _UNSET
        for v in e.elts: held = _meet(held, None if type(v) is ast.Starred else _value_type(v, types))
        return ("list" if t is ast.List else "tuple" if t is ast.Tuple else "set", held)
    if t is ast.Dict:
        held = _UNSET
        for k, v in zip(e.keys, e.values): held = _meet(held, None if k is None else _value_type(v, types))
        return ("dict", held)
    if t is ast.Subscript:
        base = _value_type(e.value, types)
        if base is _UNSET: return _UNSET
        if base is None or "[]" not in _TYPE_READS.get(base[0], ()): return None
        return base if type(e.slice) is ast.Slice and base[0] != "dict" else None if type(e.slice) is ast.Slice else base[1]
    if t is ast.Call and type(e.func) is ast.Attribute and e.func.attr in _READ_METHODS:
        base = _value_type(e.func.value, types)
        if base is _UNSET: return _UNSET
        if base is None or e.func.attr not in _TYPE_READS.get(base[0], ()): return None
        if e.func.attr == "copy": return base
        if e.func.attr == "get": return base[1] if len(e.args) < 2 else _meet(base[1], _value_type(e.args[1], types))
        return None
    if t is ast.BoolOp:
        held = _UNSET
        for v in e.values: held = _meet(held, _value_type(v, types))
        return held
    if t is ast.IfExp: return _meet(_value_type(e.body, types), _value_type(e.orelse, types))
    if t is ast.NamedExpr: return _value_type(e.value, types)
    return None


def _bind_type(p, types):
    """The type the binding node `p` gives the one name it binds from a value holding a container (_value_type): a plain assignment of
    one name, an annotated assignment or a walrus, its value's; a loop's or a comprehension's target that is one name, the type of the
    items its source holds (a list's, a tuple's or a set's; a dict's keys not known); any other binding (an unpacking, a with target) one
    it does not know."""
    if isinstance(p, ast.Assign):
        return _value_type(p.value, types) if len(p.targets) == 1 and isinstance(p.targets[0], ast.Name) else None
    if isinstance(p, (ast.AnnAssign, ast.NamedExpr)): return _value_type(p.value, types) if isinstance(p.target, ast.Name) else None
    if isinstance(p, (ast.For, ast.AsyncFor, ast.comprehension)) and isinstance(p.target, ast.Name):
        src = _value_type(p.iter, types)
        if src is _UNSET: return _UNSET
        return src[1] if src is not None and src[0] in ("list", "tuple", "set") else None
    return None


def _item_recv(e):
    """The receiver of an item use among _containers' events: a method called on, a read method's or a subscript load's step taken from,
    or an attribute read off a value at no level of new objects that stands inside the container (_flow's "method", "rstep", "sstep" and
    "attr" with `inside`: an item of it, directly or through a name bound to one or to a new object holding one); None for any other
    event, a use of the container itself (its own name, or a name bound to it whole, which its own occurrence refuses) among them."""
    kind, node, fresh, inside = e[6], e[7], e[9], e[11]
    if fresh or not inside or kind not in ("method", "rstep", "sstep", "attr"): return None
    return node.func.value if kind in ("method", "rstep") else node.value


def _scope_names(fn):
    """(name -> each Name node of that name in the body of the def statement fn and in every scope nested in it, with the scopes around
    it, innermost last, fn first, as Scan.kscopes holds them (a def's or a class's whole statement, a lambda's body, a comprehension:
    _name_reads builds the same); id(node) -> its parent node): the population the container proof reads (_Served._containers), by one
    walk of fn."""
    names, parents, stack = {}, {}, [(n, fn, (fn,)) for n in reversed(fn.body)]
    while stack:
        n, p, chain = stack.pop()
        parents[id(n)] = p
        if isinstance(n, ast.Name): names.setdefault(n.id, []).append((n, chain)); continue
        if isinstance(n, ast.Lambda):   # its defaults run where it stands, its body in its own scope
            stack.append((n.args, n, chain)); stack.append((n.body, n, chain + (n,))); continue
        inner = chain + (n,) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef) + _COMPS) else chain
        stack.extend((c, n, inner) for c in reversed(list(ast.iter_child_nodes(n))))
    return names, parents


def _target_names(t):
    """(the names a target stores, whether it stores anywhere else: into an item or an attribute of another object)."""
    names, other, todo = [], False, [t]
    while todo:
        x = todo.pop()
        if isinstance(x, ast.Name): names.append(x.id)
        elif isinstance(x, (ast.Tuple, ast.List)): todo.extend(x.elts)
        elif isinstance(x, ast.Starred): todo.append(x.value)
        else: other = True
    return names, other


def _steps(ops, fresh, inside):
    """(fresh, inside) after the steps `ops` (_flow_roots) from a value that holds a container `fresh` levels of new objects down, or
    that stands inside it (inside): an item step takes a level off, or with none left goes inside the container; a wrap adds one."""
    for op in ops:
        if op == "wrap": fresh += 1
        elif fresh: fresh -= 1
        else: inside = True
    return fresh, inside


def _frozen(v):
    """Whether the literal v holds constants alone, directly or in tuples of them (layer iv's module side: an item of such a
    container cannot be changed where it goes)."""
    todo = [v]
    while todo:
        x = todo.pop()
        if isinstance(x, ast.Constant): continue
        if isinstance(x, (ast.List, ast.Set, ast.Tuple)) and (x is v or isinstance(x, ast.Tuple)): todo.extend(x.elts)
        elif isinstance(x, ast.Dict) and x is v and None not in x.keys: todo.extend(x.keys + x.values)
        else: return False
    return True


def _chain_root(e):
    """(the name at the root of `e`, the number of item steps from it down to e: a subscript's container, an attribute's value or a
    read method's receiver, _READ_METHODS), or None where the root is no name: layer iv's module side (Scan.cwrite)."""
    d = 0
    while True:
        if isinstance(e, ast.Name): return e.id, d
        if isinstance(e, (ast.Subscript, ast.Attribute)): e = e.value
        elif isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr in _READ_METHODS: e = e.func.value
        else: return None
        d += 1


def _flow_roots(e):
    """Each name the value `e` reads through, with the steps from that name's value up to e's ("item": a subscript's container, an
    attribute's value or a read method's receiver, e an item of it; "wrap": a literal, a binary operation or a comprehension holding
    it, e a new object around it), through a boolean operation's operands, an if-expression's branches, a walrus's, a starred and an
    await's value as they are: layer iv's module side (Scan.cbind, cescape). A call's return is a value of its own (the call limit)."""
    out, todo = [], [(e, ())]
    while todo:   # each kind tested by its exact type, and a constant never pushed: a literal table of constants costs one pass over it
        x, path = todo.pop()
        t = type(x)
        if t is ast.Name: out.append((x.id, path[::-1]))
        elif t is ast.Subscript or t is ast.Attribute: todo.append((x.value, path + ("item",)))
        elif t is ast.Call:
            if type(x.func) is ast.Attribute and x.func.attr in _READ_METHODS: todo.append((x.func.value, path + ("item",)))
        elif t is ast.BoolOp: todo.extend((v, path) for v in x.values if type(v) is not ast.Constant)
        elif t is ast.IfExp: todo += [(x.body, path), (x.orelse, path)]
        elif t is ast.NamedExpr or t is ast.Starred or t is ast.Await: todo.append((x.value, path))
        elif t is ast.List or t is ast.Tuple or t is ast.Set:
            w = path + ("wrap",); todo.extend((v, w) for v in x.elts if type(v) is not ast.Constant)
        elif t is ast.Dict:
            w = path + ("wrap",); todo.extend((v, w) for v in x.keys + x.values if v is not None and type(v) is not ast.Constant)
        elif t is ast.BinOp: w = path + ("wrap",); todo += [(x.left, w), (x.right, w)]
        elif t is ast.ListComp or t is ast.SetComp or t is ast.GeneratorExp: todo.append((x.elt, path + ("wrap",)))
        elif t is ast.DictComp: w = path + ("wrap",); todo += [(x.key, w), (x.value, w)]
    return out


def _bound_value(st):
    """The value a binding statement or node binds its target to: an assignment's, augmented or annotated, and a walrus's value, a
    loop's or a comprehension's source, a with item's context expression; None for any other (layer iv, _Served._containers)."""
    if isinstance(st, (ast.Assign, ast.AugAssign, ast.AnnAssign, ast.NamedExpr)): return st.value
    if isinstance(st, (ast.For, ast.AsyncFor, ast.comprehension)): return st.iter
    return st.context_expr if isinstance(st, ast.withitem) else None


def _binds_whole(st, n):   # whether the binding statement st binds the name node n to its whole value (not an unpacking or a loop target)
    return isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)) and (
        n in st.targets if isinstance(st, ast.Assign) else st.target is n)


def _dotted(e):   # a name, or a dotted chain of attributes on one, spelled as Scan.dotted spells it; "" for anything else
    parts = []
    while type(e) is ast.Attribute: parts.append(e.attr); e = e.value
    return ".".join([e.id] + parts[::-1]) if type(e) is ast.Name else ""


def _module_level_stmts(tree):
    """Every node of the module's own body (_own_stmts of the module tree): its statements, the control flow it nests and the
    expressions inside them, never a def, class or lambda statement, header or body (_Served._reaches_frame's module frame aliases)."""
    return _own_stmts(tree)


def _own_stmts(node):
    """Every node of `node`'s own body (a module or a function), statements and expressions alike: its statements, the bodies of the
    control flow it nests (if, for, while, with, try, match) and every expression inside them, a comprehension's among them, never
    descending into a def, class or lambda statement, header or body. A body's names are not `node`'s; a header's may be (a walrus in a
    def's default binds a name of `node`), and that binding is not read here, the frame precondition's road (_Served._reaches_frame
    reads a function's own frame aliases from these nodes; _module_level_stmts reads the module's)."""
    out, stack = [], list(node.body)
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)): continue
        out.append(n); stack.extend(ast.iter_child_nodes(n))
    return out


def _flow(u, parents, fresh=0, inside=False):
    """Where the value the Name node u reads goes, walked up its parents (layer iv): a list of steps, each (kind, node, detail, fresh,
    inside), the last its sink. `fresh` counts the levels of a value that are new objects around the container's own: a literal, a
    binary operation or a comprehension that holds the value adds one, and an item step (a subscript load's, or a read method's return:
    _READ_METHODS) takes one off, or once none is left goes into the container: `inside`, the value an item of it (or an item of one) and
    no longer the container itself. A change reaches the container only where no level is left (0). Through a boolean operation's
    operand, an if-expression's branch, a starred value, an await and a walrus's value (a walrus also binds its name: "bind") the value
    goes on as it is. The steps that do not end the walk: "sstep" a subscript load on the value and "rstep" a read method called on it
    (detail its name), each read by _Served._containers against the type of the value it is taken from. The sinks: "store" a store or
    delete through it (the subscript or attribute); "handed" setattr or delattr handed it as the first argument (detail the callee);
    "tcall" a method spelled on another value (`list.append(x, v)`) handed it as the first argument (detail the callee as spelled),
    which _Served._containers reads as the method running on it where that value is a class it resolves (_class_callee) and as the
    call limit otherwise; "grow" an append or extend called on u itself; "method" any other method called on it (detail its name); "attr"
    an attribute read on it other than as a method's callee (detail its name); "bind" its value, or an item of it, bound to names, by an
    assignment, an augmented or annotated one, a loop, a comprehension, a with statement or a walrus (detail the names; a loop's or a
    comprehension's target an item of it); "escape" stored into another object, handed as a default, matched, called, or held anywhere
    else (detail the words); "operand" handed to another object's method by an operator, which Python invokes with the value as its
    argument (an operand of a binary operation or a comparison whose other operand is no constant, a subscript's index, a slice's
    bound, the value of an augmented assignment, or a .index()/.count() with an argument that is no constant): the 07:37Z ruling's
    condition 2, where the value is an item a read of the container returns; "call" a call's argument, the call limit; "read" consumed
    some other way (a test, a comprehension's condition, an identity comparison, an operand of a binary operation or a comparison whose
    other operands are constants, an f-string's field, a statement's value, a return or a yield, a lambda's body). For the container's
    OWN name, the fourth-form check (_own_use, _Served._containers) keeps only "read" as a read method's receiver or a subscript load's
    base; every other "read" or "operand" role of the container's own name refuses it."""
    steps, cur = [], u

    def item(fresh, inside):   # an item step: a level of new objects off, or with none left, into the container
        return (fresh - 1, inside) if fresh else (0, True)
    while True:
        p = parents.get(id(cur))
        if isinstance(p, ast.Subscript):
            if p.value is not cur: return steps + [("operand", p, "a subscript's index", fresh, inside)]   # an index
            if not isinstance(p.ctx, ast.Load): return steps + [("store", p, None, fresh, inside)]
            steps = steps + [("sstep", p, "[]", fresh, inside)]
            cur = p; fresh, inside = item(fresh, inside)
            if type(p.slice) is ast.Slice: fresh += 1   # a slice: a new object holding its receiver's items
            continue
        if isinstance(p, ast.Attribute):
            if not isinstance(p.ctx, ast.Load): return steps + [("store", p, None, fresh, inside)]
            gp = parents.get(id(p))
            if isinstance(gp, ast.Call) and gp.func is p:
                if p.attr in _READ_METHODS:
                    if p.attr in _COMPARED and not (gp.args and type(gp.args[0]) is ast.Constant):
                        return steps + [("operand", gp, "compared by .%s() with an argument that is no constant" % p.attr, fresh, inside)]
                    steps = steps + [("rstep", gp, p.attr, fresh, inside)]
                    cur = gp; fresh, inside = item(fresh, inside)
                    if p.attr == "copy": fresh += 1   # a copy: a new object holding its receiver's items
                    continue
                if p.attr in _GROWERS and cur is u: return steps + [("grow", gp, None, fresh, inside)]
                return steps + [("method", gp, p.attr, fresh, inside)]
            return steps + [("attr", p, p.attr, fresh, inside)]
        if isinstance(p, ast.IfExp):
            if cur is p.test: return steps + [("read", p, None, fresh, inside)]
            cur = p; continue
        if isinstance(p, (ast.BoolOp, ast.Starred, ast.Await)): cur = p; continue
        if type(p) is ast.BinOp and type(p.right if cur is p.left else p.left) is not ast.Constant:
            return steps + [("operand", p, "an operand of a binary operation whose other operand is no constant", fresh, inside)]
        if isinstance(p, _FLOWS): cur, fresh = p, fresh + 1; continue   # a literal, a binary operation or a comprehension's element holding it
        if isinstance(p, ast.NamedExpr):
            steps.append(("bind", p, [p.target.id], fresh, inside)); cur = p; continue
        if isinstance(p, ast.Call):
            if cur is p.func: return steps + [("escape", p, "called", fresh, inside)]
            if p.args and cur is p.args[0] and type(p.func) is ast.Name and p.func.id in _NS_SETTERS:
                return steps + [("handed", p, p.func.id, fresh, inside)]   # setattr(x, ...) or delattr(x, ...): a change of x
            if p.args and cur is p.args[0] and type(p.func) is ast.Attribute:   # `list.append(x, v)`: a method spelled on a class runs on
                return steps + [("tcall", p, _dotted(p.func) or p.func.attr, fresh, inside)]   # x where _containers reads its value as a class
            return steps + [("call", p, None, fresh, inside)]
        if isinstance(p, ast.keyword):
            gp = parents.get(id(p))
            return steps + [("call" if isinstance(gp, ast.Call) else "escape", gp if isinstance(gp, ast.Call) else p,
                             None if isinstance(gp, ast.Call) else "held in a position the census does not read", fresh, inside)]
        if isinstance(p, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.For, ast.AsyncFor, ast.comprehension, ast.withitem)):
            loop = isinstance(p, (ast.For, ast.AsyncFor, ast.comprehension))
            src = p.context_expr if isinstance(p, ast.withitem) else p.iter if loop else p.value
            if cur is not src: return steps + [("read", p, None, fresh, inside)]   # a comprehension's condition
            if isinstance(p, ast.AugAssign): return steps + [("operand", p, "the value of an augmented assignment", fresh, inside)]
            tgts = (p.targets if isinstance(p, ast.Assign) else [p.optional_vars] if isinstance(p, ast.withitem) else [p.target])
            names, other = [], False
            for t in tgts:
                if t is None: continue
                got = _target_names(t); names += got[0]; other = other or got[1]
            if other: return steps + [("escape", p, "stored into another object", fresh, inside)]
            return steps + [("bind", p, names) + (item(fresh, inside) if loop else (fresh, inside))]   # a loop's target: an item of its source
        if isinstance(p, ast.arguments): return steps + [("escape", p, _AS_DEFAULT, fresh, inside)]
        if isinstance(p, ast.Match): return steps + [("escape", p, "matched by a match statement", fresh, inside)]
        if type(p) is ast.Compare and not all(type(o) in (ast.Is, ast.IsNot) for o in p.ops) and any(
                type(o) is not ast.Constant for o in [p.left] + p.comparators if o is not cur):
            return steps + [("operand", p, "an operand of a comparison or `in` whose other operand is no constant", fresh, inside)]
        if type(p) is ast.Slice: return steps + [("operand", p, "a slice's bound", fresh, inside)]
        if isinstance(p, _READS): return steps + [("read", p, None, fresh, inside)]
        return steps + [("escape", p, "held in a position the census does not read", fresh, inside)]


def _role(n, p):
    if isinstance(p, (ast.If, ast.While, ast.Assert, ast.IfExp)) and p.test is n: return "a test"
    if isinstance(p, ast.comprehension): return "a test" if n in p.ifs else "a loop's or a comprehension's source"
    if isinstance(p, ast.match_case): return "a test"
    if isinstance(p, ast.Compare): return "an identity test"
    if isinstance(p, ast.BoolOp): return "a boolean operation's operand"
    if isinstance(p, ast.IfExp): return "an if-expression's branch"
    if isinstance(p, (ast.Return, ast.Yield, ast.YieldFrom)): return "returned or yielded"
    if isinstance(p, (ast.FormattedValue, ast.JoinedStr)): return "an f-string's field"
    if isinstance(p, ast.Expr): return "a statement's value"
    if isinstance(p, ast.UnaryOp): return "a unary operation's operand"
    if isinstance(p, (ast.List, ast.Tuple, ast.Set, ast.Dict) + _COMPS): return "held in a new object"
    if isinstance(p, (ast.For, ast.AsyncFor)): return "a loop's or a comprehension's source"
    if isinstance(p, ast.withitem): return "a with statement's context"
    if isinstance(p, ast.Starred): return "a starred value"
    if isinstance(p, ast.Await): return "awaited"
    if isinstance(p, ast.Raise): return "raised"
    return None


def _own_use(n, parents, own):
    p = parents.get(id(n))
    if isinstance(p, ast.Subscript):
        if p.value is not n: return "refuse", p, _CT_INDEX
        return ("read", p, "[]") if isinstance(p.ctx, ast.Load) else None
    if isinstance(p, ast.Attribute):
        gp = parents.get(id(p))
        if isinstance(p.ctx, ast.Load) and isinstance(gp, ast.Call) and gp.func is p and p.attr not in _GROWERS: return "read", gp, p.attr
        return None
    if isinstance(p, ast.Starred) and isinstance(parents.get(id(p)), ast.Call): return None
    if isinstance(p, ast.Slice): return "refuse", p, _CT_INDEX
    if isinstance(p, ast.BinOp) or isinstance(p, ast.Compare) and not all(isinstance(o, (ast.Is, ast.IsNot)) for o in p.ops):
        return "refuse", p, _CT_HANDED
    if isinstance(p, ast.AugAssign) and p.value is n: return "refuse", p, _CT_AUGV
    if isinstance(p, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and p.value is n:
        names, other = [], False
        for t in (p.targets if isinstance(p, ast.Assign) else [p.target]):
            got = _target_names(t); names += got[0]; other = other or got[1]
        if other or any("global" in own.get(z, ()) or "nonlocal" in own.get(z, ()) for z in names): return None
        return "refuse", p, _CT_BIND % ", ".join(names)
    r = _role(n, p)
    return None if r is None else ("refuse", p, _CT_READ % r)


class _Container(list):
    """The binding forms of a name the container proof refuses in its function's scope (_Served._ctx, _Served._containers), with the
    reason (why): a list like any other, and a mark for _Served._scoped, which refuses the name wherever the pass reads it (as a bare
    name, a receiver's base, a container, an attribute's root or a callee). A nested function or a lambda that binds no name so spelled
    reads the same list, so the mark holds in a closure; a scope inside the function that binds the name again gives it a plain list."""

    def __init__(self, forms, why):
        list.__init__(self, forms); self.why = why


class _Unclassified(list):
    """The binding forms of a route handler's first parameter that the census does not classify (_Served._ctx): the handler
    carries a decorator, whatever it is bound to, or a statement of the file binds the name staticmethod or classmethod, in any
    scope and by any form, a star import among them, so the parameter may be self, the class or any other value. A list like any
    other, so _Served._scoped reads the name as the parameter it is, and a mark for _Served._recv_roots, whose method call on it
    _method_call refuses as _UNCLASSIFIED, and for _scoped, which refuses it as a callee so; an attribute read on it is one on a
    parameter (_attr_root, _PARAM_ATTR). A nested function or a lambda that binds no name so spelled reads the same list, so the
    mark holds in a closure; a scope inside the handler that binds the name again gives it a plain list, and the mark ends there."""


class _SelfParam(list):
    """The binding forms of self by binding in its method's scope (_Served._ctx): the first parameter of a method defined in a class
    body (a def whose innermost enclosing scope is the class body: _method_defs) whose def carries no decorator, however it is
    spelled, other than a route handler's in a file that binds staticmethod or classmethod (_Unclassified). A list like any other,
    so _Served._scoped reads the name as the parameter it is, and a mark for _Served._attr_root, which takes an attribute read on
    the name for one read on self (_SELF_ATTR). A nested function or a lambda
    that binds no name so spelled reads the same list, so the mark holds in a closure; a scope inside the method that binds the
    name again gives it a plain list, and the mark ends there. The parameter never rebound in the method is the mark with forms
    ["param"] exactly."""


def _method_defs(tree):
    """The ids of the def and async def statements the module defines directly in a class body, a statement of the body itself
    (not one inside a block of it), in any class, one nested in a class, a function or a block among them: its methods. Statements
    only, never an expression, as _statements walks them (_BODY_FIELDS); a lambda holds no def statement."""
    out, stack = set(), list(tree.body)
    while stack:
        s = stack.pop()
        if isinstance(s, ast.ClassDef): out.update(id(n) for n in s.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
        for field in _BODY_FIELDS.get(type(s), ()): stack.extend(getattr(s, field))
    return out


class _Served(object):
    """The text a route's page is served from, followed through the module's syntax tree: the body expression of each route
    (routes_of: the call's second positional argument) resolved to its string constants (a literal, an f-string's parts, `+` and
    `%` operands and the argument tuple, a `/`'s operands (a path join), a conditional's branches, a BoolOp's operands, a starred
    value, a comprehension's element with its targets read from their source, a lambda's body with its parameters as value slots and
    its defaults read where it stands (one a name's value holds refused where the name is read: _LAMBDA_VALUE), a module constant by
    name (a name one plain single-name assignment binds as a top-level
    statement and nothing else binds at module level, a header walrus included, in a module with no star import that writes no
    name of its module namespace through a computed name and may not rewrite it at run time: _module_consts, _namespace_flags; each
    such proof reads the page's own file alone, so a file another walked file's import statement may bind is refused whole, one line
    at its first route candidate, scan's _page_importers, and a module reached another way is the stated limit), a local by every
    binding it has in the function (a container only where the container proof holds: _containers), a `.format`,
    `.join` (but one over a set, or over a local or a module constant the census reads by its binding from one: _set_value, _JOIN_SET;
    a set a call returns or a parameter takes, as its argument or its default, read piece by piece under the join limit), `.replace`
    or `.strip` receiver and its
    arguments (but a `.format`, `.join` or `.replace` called on the name str, bytes or bytearray; each refused below), and every `return`
    of a module function
    or a function defined in the page function that the census proves a plain def (_def_shape, _def_uses; a method called on self is
    refused by name: _method_call), each a piece (label, its own line, text, the
    part it came from) for line_scan, with each join of string constants _const_text reads recorded in `joins` (_note,
    _const_text), whose text served_texts scans beside each literal's own read; a local bound to a `.read_text()` or `.read()` is a
    file slot, its path proven by binding (_path), which served_texts covers where the walk scanned the file as browser text, names
    where it is a stylesheet the walk does not scan, and refuses otherwise. A route whose page function a function encloses, whose
    `_send` stands in a class a
    function defines, or whose `_send` call stands in a lambda's body, is refused before this pass (routes_of), since the enclosing
    function's or lambda's names are no scope it reads; and so is a call whose `_send` definition binds the parameter one of its own
    Content-Type writes names other than as that parameter, anywhere in its body (_type_rebinding), since that write's type is read
    from the call's argument.

    A name the page function's scope binds, or for a nested context an enclosing function's scope, is decided by that scope and
    never by the module's binding (_scoped over the binding forms _locals records, row (d) of the seventh round): a local (a
    parameter the body also assigns, a walrus in a nested def's, class's or lambda's header, a comprehension's target inside its
    comprehension, whose one value is its generator's source, read in the context Python evaluates that source in, comp_at: the
    first generator's in the scope around the comprehension, each later one's with the earlier generators' targets bound and its own
    target and the later ones' refused as a name a comprehension binds) is read from its values as a bare name or a receiver (refused
    where a value holds a lambda: _LAMBDA_VALUE), each value in the context of the scope that binds the local (_value_ctx: a
    comprehension, a lambda or a function defined in the page function reads a local of the scope around it there, local_at), and
    refused as "a call" as a callee, and before any of these a container of the scope the container proof refuses is refused
    wherever it is read (_Container, _containers, _CONTAINER); a parameter or an
    except name is a value slot, refused as a callee when it shares a module function's name; a function defined in the page
    function is followed only as its name's one binding there and a plain def (_def_shape, _def_uses), and refused as a value
    (_FUNC_OBJECT); a name the function declares `global` is the module's binding,
    read as such; and any other binding is refused by its form (a comprehension's target elsewhere in the function, a
    function-level import, a nested class, a del, a name a nonlocal declaration rebinds, any other store, and a name bound two
    ways, meaning two different binding forms in one scope, or a def or a class statement beside any other binding of the name;
    every value form, an assignment, augmented or annotated, a loop, with or unpacking target and a walrus, is one form, and a
    parameter the body also binds by one is one local, read from its values).

    A method call's receiver and a subscript's container are read when they name a module constant or a local, a method call's
    receiver only where the method's return is drawn from its receiver's text (_DRAWN: removeprefix, removesuffix, split, rsplit,
    splitlines, partition, rpartition, a match's group and the read methods get, keys, values, items, index, count and copy), any
    other method on a receiver whose text the pass reads (a local, a module constant that is no run-time memo, or an expression
    resolve reads) refused by name (_undrawn, _UNDRAWN), and so is the receiver of `.encode` or `.format_map` whatever it is (the
    name str, bytes or bytearray before `.format_map` excepted, refused below), but a `.replace` other than with two positional
    arguments, a `.format_map` other than with one positional argument or over a dict literal whose keys are not each a string
    constant, and an `.encode` other than with no argument or with one string constant that is utf-8, utf_8 or utf8 in any case
    (_UTF8_NAMES) are refused by name, their text uncomputed
    (_text_shape, _TEXT_SHAPE); a subscript's container is read only under a constant index: a slice
    of any shape, or an index that is no constant (a name, a call, a parameter, a tuple, a negative number, which parses as a
    UnaryOp), over a container whose text the pass reads (_carries_text: a literal or another expression resolve reads, a module
    constant or a local, an attribute, a subscript or a method call on one of those, or a BoolOp with such an operand) is refused
    by name (_SLICED), since the pass reads the container whole and does not compute what the index selects, and honest forms fail
    closed with it (`_PAGE[1:]`, a template's leading newline cut; `PAGES[key]` over a dict constant, the key no constant;
    `_P[-1]`), and so is such a subscript over a base whose own text the pass does not read (below) that derives through a call
    handed arguments it reads, which it reads whole and does not slice either, as the page expression or anywhere on the path of a
    receiver, a container or an attribute's base (_chain_text, _sliced, at resolve's Subscript arm and over _path_subs at receiver's
    point for such a base: `str(X)[::-1]`, `dict(a=X)[k]`, `str(X)[::-1].removeprefix(p)`), while any other container that is such a
    base, or a call of one or of a method on one, passes whatever its index, save where the method allowlist refuses a call on its
    path (_exempt_undrawn), and the index of
    such a subscript is not read at all, whatever it holds (a name the import
    system binds, `__file__`, an attribute read on self, on a parameter or on a class, a call: the Subscript arm hands receiver the
    container alone), the item it selects being text such a base holds; an attribute read on a class, a method called on one among
    them, as a value, a receiver or a container, through the class's
    own name (a class statement binds it, in the innermost function scope around the read that binds the name or, where none
    does, at the top level: _class_name) or through a name the census resolves to a class (a local or a module constant bound to
    one or to a method call on, or a subscript of, a name whose value holds one: _class_value), or through a method call on, or a
    subscript of, a name whose value holds one (a list, tuple, set or dict literal a local or a module constant is bound to, with
    a class among its elements, keys or values, or a call of the builtin dict with one
    among its arguments: _class_value, _class_step, _held, `_REG.get(k).X`, `_REG["a"].X`) or of such a literal or call itself
    (`dict(a=Cls).get(k).X`), is refused by name (_class_root, _CLASS_ATTR), and so is one read, or a method called, on any other
    base whose root by binding is a class (_attr_root: a loop, comprehension or with target over classes, an if-expression or a
    walrus over classes, a literal container holding one, `_REG["a"].X`; a method called with no attribute read on the way,
    `_REG["a"].render()`, at the call: _value_class), as is a text method called on such a class through any of those roads
    (_class_value, _value_class: `Cls.format(...)`, `_REG.get(k).format(...)`, `t.strip()` in a loop over classes), save one on a
    subscript refused as a join's operand (_SUB_OPERAND, below), and a format field that reaches an attribute of
    its argument (_FIELD_REACH, below), since no class attribute is read as page text; a call of a name the census resolves to a
    class is refused by name ("a call": _scoped, _base), so no attribute of the instance it makes is read; an attribute read in a
    page position, as a value or anywhere on the path of a receiver or a container (receiver, _path_attrs; never inside the index
    of a subscript over a container whose text the pass does not read, above), is refused by
    name unless the root its base reaches by binding is a module constant, an import, one of the seven builtins a page may name, a
    value slot or a literal the pass reads (an attribute read off a local, or off a module name bound to a call, being refused before
    that, as a container, _containers, xatr's check of the 19:33Z ruling, or a run-time memo, Scan.visit_Attribute; _attr_root, which
    reads the base
    down that path, a call's
    callee, a BoolOp's operands, an if-expression's branches and a walrus's value among it, and through a local's values, a loop,
    comprehension or with target's source, a list, tuple, set or dict literal's elements, keys and values, and a module constant's
    value, never a call's argument or a parameter's default): one read on self (`self.X` as a value, a receiver or a container,
    `self.X.get(k)`, `self.X[0]`), on a comprehension's target bound to it or on a method's first parameter however spelled where the
    method's def
    carries no decorator and, for a route handler, the file binds neither staticmethod nor classmethod (_SelfParam), as _SELF_ATTR,
    whatever sets it, one read on any other parameter as that parameter, a container the proof refuses (_CONTAINER, "a parameter"),
    one read on a route handler's first parameter the census does not classify (_Unclassified) or on a parameter's call as
    _PARAM_ATTR, and one read on an except name as _EXCEPT_ATTR, and a base whose root is one the pass refuses (a function's or a
    method's
    return, a call it does not follow, a builtin other than the seven, a function or class object, `__file__` in a file that binds
    it, a run-time memo) with the reason the pass gives that root, while a method called on self is no attribute read: it is
    refused by name below (_method_call); a name the function binds as a
    loop, unpacking or with
    target, or by a walrus, is read from that source, and a local container's appended or stored values are its values too where the
    container proof holds (_containers, a rule over occurrences: every occurrence of the container's name, resolved by binding, is
    one of the proven forms (its one binding in the function's own body, one plain single-name assignment of a list, dict, set or
    tuple literal or of a call _base reads as a value slot; the base of a constant-key subscript store of a value the census reads;
    the receiver of an append or extend of a value it reads; or the fourth form (07:37Z), a read that hands the container to no other
    code: the receiver of one of the read methods of the type its one binding gives it, or the base of a subscript load on a type that
    has one (_TYPE_READS: a dict's get, keys, values, items and copy and a subscript load; a list's index, count and copy and a
    subscript load; a tuple's index and count and a subscript load; a set's copy; index and count only with a constant argument; the
    type only from a list, dict, set or tuple literal or a call of parse_qs, a dict, so a container bound to any other value slot has
    none and any read method or subscript load on it refuses, _CT_UNTYPED)), and any other occurrence refuses it: a second binding, a
    del, a store or method the census cannot fold (setattr or delattr, or a method spelled on a class, handed it as its first
    argument, among them), a bind of the whole container to another name or to a global or nonlocal name, a
    read that hands it to another object's method (an operand of an operator, a comparison or `in`, or a subscript's index) or any
    other read, or a read or change in a def, class or lambda nested in it among them, a nested scope's own binding of the spelling
    being no occurrence of it; a read method's or a subscript load's result is an item the census follows by binding, read only
    through the closed read set of its own type (_item_types, _value_type: condition 1 applied to it), and of an item the proof reads
    this: any other method called on it, a read method or a subscript load outside that set (a str has none, nor has an item whose
    type the census does not know), an attribute read off it, a store into it, and setattr, delattr or a method spelled on a class
    handed it, its hand-off to another object's method by an operator whose other operand is no constant (a
    comparison, a binary operation, a subscript's index, a slice's bound, an augmented assignment's value, or what an index or a count with
    an argument that is no constant compares), and any use the census does not read (called,
    or stored into another object, an attribute or a global or nonlocal name) refuse the container, while an item compared or
    combined with a constant is read (only its own type's method and the constant's run), and one handed as an argument to any other
    call, a method spelled on a class the census does not resolve among them, is under the call limit; a comprehension is read where
    it stands, as the function's own body is: a read of the fourth form, an
    append of a read value and a call's argument pass there, and any other read refuses), any other container of the scope refused by name
    wherever it is read (_Container, _CONTAINER), save the first parameter of a method or a route handler, and the container or an item of
    it handed as an argument to any other
    call being under the call limit (its witnesses a local dict a module function it is handed stores a fetch into, ctwit, and a list read
    out of a local dict of lists by a subscript load, by `.get` or through a name bound to it, which a module function it is handed
    appends a fetch to, ihc, ihg and ihn, and such a list handed to append spelled on a class of the file that derives from list,
    itcw); a module container some code writes after binding it (a write
    Result.writes records, as the served sentence lists them, a module list, dict or set changed or let out of the census's sight
    among them: Scan.cflows) is a run-time memo, and so is a module name bound to a call whose object the file changes
    (Result.changed, self.cmemos), save as a call's argument (self.cargs: the call limit, its witness an import's object an
    attribute store changes, read as getattr's argument), and it and any other receiver or container are refused by name
    unless the base is one whose own text the pass does not read (a top-level import statement that is its name's one module-level
    binding, one of the seven builtins a page may name (str, int, dict, max, float, getattr, chr, each with its reason in
    _PAGE_BUILTINS: a call of int or float that is the builtin a number-valued leaf whose argument resolve does not read, save where
    the call is the base of a receiver, a container or an attribute, where receiver reads it with the path's other calls' arguments
    (_chain_args), and one bound
    any other way refused by name, _NUMBER_LEAVES, _NUMBER_REBOUND; getattr and chr give text their arguments do not hold, each
    under the call limit below and each its witness; max handed one iterable or a starred argument, which returns an element
    its argument holds, whose join with the text beside the call the census does not compute, is refused by name, _MAX_ONE;
    and str handed more than one positional argument, a starred argument or a keyword other than
    object, any of which may be an encoding or an errors argument that decodes its first, is refused by name, _STR_DECODE) that
    no module-level binding shadows, any other builtin refused by name (_BUILTIN_OTHER), and a call of
    super() refused by name as well (_SUPER), its methods being a base class's, and the
    names the import system binds in every module excepted (_IMPORT_NAMES, refused by name as a bare name, the base of a receiver, a
    container or an attribute, a callee or a call's argument, and not read inside the index of a subscript over a container whose
    text the pass does not read, above: _IMPORT_WHY), each in a module with no
    star import; a parameter or a name bound from one, a BoolOp over those, where no attribute is read on the path to it (`q.get(k)`
    passes, `q.X` is refused, above); a call of one of those or of a method on one, whose arguments are read as text:
    `dict(X).get(k)` reads X, _chain_args, a method on such a base derived through a call handed text, or on one of the seven
    builtins' names called unbound, read only where its return is drawn from the receiver's text, at every call on the path,
    _exempt_undrawn, a call of int or float that is the builtin among such calls, and a slice, or an index that is no constant,
    anywhere on the path refused, _path_subs) or SERVED_ALLOW names
    the place (or SERVED_LISTED lists it, refused with its reason), and a call base the reader does not resolve is refused
    by name; text such a base holds (a constant a sibling module defines and the page imports, and a class reached through an
    import's attribute, its witness a class a sibling module defines read as an attribute of that module, which the page imports by
    its name, or through a call's return, under the call limit) is not read as the base's, and text a call
    computes from its arguments is not read, the stated limit (its witnesses chr, getattr and a decoder whose bytes the page
    serves as they come, `base64.b64decode(X)` or zlib or gzip over an embedded bundle, `zlib.decompress(base64.b64decode(X))`, each
    read only as its arguments' own text, a decoder's text decoded, `base64.b64decode(X).decode()`, being refused by the method
    allowlist; an encoded asset kept ASCII and decoded where the page is built is such a shape, and can be honest; and so is a method called on a parameter whose name no route class's body binds (self.route_methods) and the file stores nowhere as an
    attribute (_stores), a method of a class that holds no route among them), and code behind a name on self is not followed: a method
    called on self by binding, or on a name the census resolves to it (a local bound to it, or a function the page function defines
    returning it), is refused by name, and one called on any other parameter, or on a name bound to the return of a followed function
    that returns its parameter, is refused where a route class binds its name or the file stores it, and is otherwise under the call
    limit (_method_call, _recv_roots, below). A call is followed only as listed here: a file read, a
    text method's receiver, and a module function that is a top-level def statement and its name's one module-level binding, bound
    by no function scope of the context, or a function defined in the page function, its name's one binding there (_scoped's
    ["def"]), each only where the census proves it a plain def (_def_shape: a def statement, not an async def, _DEF_ASYNC, carrying
    no decorator, _DECORATED, with no yield in its own body, _DEF_YIELD, _yields; _def_uses: its name read nowhere in the file but
    as a call's callee, _DEF_ALIAS, and, for a module function, spelled by no string constant of the file, _DEF_STRING), each such
    function read to its own returns (_returns) and the default of each of its parameters the call omits read as that argument would
    be, in the scope its def statement runs in (_defaults: a default that holds a lambda refused, _LAMBDA_VALUE); any other method
    call through its receiver as above (a lambda a name's value holds is refused where the name is read, _LAMBDA_VALUE,
    _holds_lambda: `_K.__call__(t)` on a constant holding one among them); and every call's arguments are read as text, save a call
    of int or float that is the builtin, a number-valued leaf, where the call is no base (_NUMBER_LEAVES). No method
    called on the calling method's own first parameter is followed (_own_self: self by binding, however it is spelled, the first
    parameter of a method whose def carries no decorator, never rebound in its scope, a closure, a lambda or a comprehension of the
    method that binds no name so spelled reading it too; the first parameter of a route handler that carries a decorator, whatever
    it is bound to, or that stands in a file where a statement binds staticmethod or classmethod, a star import among them, is not
    classified, _Unclassified, and a method called on it, or it called, is refused by name, _UNCLASSIFIED): the follow arm refuses
    each (_method_call, below), and it and the refusals below run before the file-read and text-call arms, and on every method call
    on the path of a receiver or a container (receiver, _path_calls); any other callee passes when _base finds it such an import,
    one of the seven builtins a page may name or a parameter other than a route handler's first parameter the census does not
    classify, and is refused by name for any other builtin and otherwise (a module constant, a local, a class, such an unclassified
    first parameter, a subscript, a call and a lambda literal among them) unless SERVED_ALLOW names the place. A method called on
    the calling method's own first parameter is refused by name, whatever its def, since a subclass another file defines may
    override it with code the census does not read (choice 4 of the eleventh round's rulings: _METHOD_SUBCLASS, the closing refusal), and before that
    with the reason that names what the census found first, the route class keyed on its class statement (_top_class: its name only
    where the node is its name's one top-level class statement): the route class's method resolution order (_mro, C3 over the
    classes of the file, any other base a class whose names the census does not read) resolving the name to no def statement of a
    class of the file first (the order reaching a base whose names the census does not read before any class of the file that binds
    the name; the first class that binds it binding it any other way, an assignment, a lambda, a def inside a block of the body, a
    second binding or a def under a global declaration among them; no class binding it; an order the census cannot compute; or a
    route class _top_class does not read: _definer, _SELF_METHOD); that def no plain def (_def_shape: _DEF_ASYNC, _DECORATED,
    _DEF_YIELD); a class statement of the file, in any scope, outside the route class's order, that binds the name and derives from
    the route class, directly or through classes _top_class reads (_METHOD_OVERRIDE), or that the census cannot place
    (_METHOD_UNPLACED: a class statement _top_class does not read, or one with a base on its ancestor chain that is none of those
    classes, no top-level import that is its name's one module-level binding or an attribute of one, and no builtin: _file_override
    over every class statement, _override_step); and the file's replacing the method at run time (_replaced: the file stores or
    deletes an attribute of its name on any object, as the target of an assignment of any kind, a for, with or comprehension target
    or a del, names it by a string constant, or a join of them, as the second argument of setattr or delattr, or of __setattr__ or
    __delattr__ called unbound (by that name, or on object, type, a class a top-level class statement binds or a call of type():
    _class_recv), or as the first argument of __setattr__ or __delattr__ called bound on any other receiver
    (self.__setattr__("name", f), super().__setattr__(...)), or holds a class in the route class's order that binds
    __getattribute__: _REPLACED; else a setter whose name the census does not fold to a constant string, one after a starred
    argument or none among them, or a setter reached other than by a call: _setters_open, _REPLACED_OPEN). So is a call of a route
    class's method (self.route_methods: every name the bodies of the route classes and of the classes of the file they derive from
    bind, in any form outside their nested scopes, _body_names, read from the route classes' class statements once per file in run,
    so a module helper's context has them) whose receiver resolves by binding (_recv_roots: through a local's values, a loop,
    comprehension or with target's source, a list, tuple, set or dict literal's elements, keys and values, a subscript's container,
    an if-expression's branches, a BoolOp's operands and a walrus's or a starred value, and a call of a function the census follows,
    through its returns in its own scope: _followed) to self through anything else or to any other parameter, or that is a name
    spelled self other than that first parameter (_METHOD_CALL); a call of any other name whose
    receiver resolves by binding to self through anything else (_SELF_METHOD); and a call of any other name whose receiver resolves
    to any other parameter, or is a name spelled self other than that first parameter, where the file stores, deletes or names to a
    setter an attribute of that name (_stores, read once per file in run: _METHOD_STORED). A receiver that is a class, or whose root
    by binding is one, is decided by receiver (_class_root,
    _value_class, _CLASS_ATTR), and one that is an except name passes as above. A bare module name that is no constant passes when
    it is such an import or one of the seven builtins a page may name, a top-level def or class statement that is its name's one
    module-level binding is refused by name as a function or class object (_FUNC_OBJECT), and any other (one bound other than by one
    assignment, one bound by an annotated,
    unpacking or chained assignment, one annotated at module level beside its assignment, an import, a function or a class beside
    another module-level binding, one bound once inside a module-level block and not by a top-level statement, a name a star
    import may rebind, and a rebound import, builtin, function or class among them) is refused by name, with the reason
    _module_why gives, unless SERVED_ALLOW names the place. The module's names are the count's own (_module_bound), so every
    module-level binding is classified here and none falls to the reasonless line, and a name no module-level statement binds that
    a function or a class body binds under a `global` declaration is refused with its own reason (_global_only). An import, a
    builtin, a function or a class passes in none of these places, and a module function is not followed, when its name is rebound
    (Result.rebinds: a function binds it under `global`, or a statement at module level writes it), the module holds a star import
    or the file writes its module namespace through a computed name (_namespace_flags: globals() or vars() used any way but for a
    `.get` read; the `__dict__` or vars() of a module the file may be (`sys.modules[k]` or its `.get(k)`, or `__import__(k)` or
    `import_module(k)`, k no string constant, "__main__" or the file's own module name; a name that an assignment (as a name
    target, alone or in a chain), an annotated assignment or a walrus binds to one of these; or an if-expression or a boolean
    operation over one); a store, setattr or delattr on that module; and globals, vars, setattr or delattr read other than as a
    call, each of those four by its own name, a name an import from builtins binds to it or as an attribute of a builtins receiver
    (`__builtins__`, a name `import builtins [as X]` or `from X import builtins [as Y]` binds, `sys.modules["builtins"]` or its
    `.get`, `__import__("builtins")` or `import_module("builtins")`)) or may
    rewrite it at run time (an import from the file's own package, its own bare stem among them, which closes every write through
    the name; an attribute named __globals__, __builtins__, f_globals, f_builtins or f_locals; a listed callable, locals, exec,
    eval, compile, __import__, import_module or _getframe, by its own name, by a name an import from builtins, importlib or sys
    binds to it, or as an attribute on
    a builtins receiver or, for all but compile, on any receiver; or one of those names, globals, vars, setattr, delattr or
    `__dict__` spelled as a string in a
    getattr-family, attrgetter/methodcaller or namespace-key position; _namespace_flags lists these four ways exactly; and, since
    the eleventh round's review, a starred argument or a ** mapping in a key position, _KEY_STARRED, a getattr-family name read other than as a call's
    callee, _GETATTR_ALIAS, and a namespace mapping the file's own module or the builtins may be used other than in a key position
    the allowlist reads, _NS_USE; the reason names the form and its line), and a builtin passes nowhere in a file that names
    `__builtins__` as a name, imports the builtins
    module (`import builtins[.x]`, `from builtins[.x] import ...` at any level, `from X import builtins` or `from X import
    __builtins__`, any X at any level) or writes a module that may be the builtins module (the forms _namespace_flags lists),
    each builtin there refused by name (_SHADOWED); a module namespace rewritten at run time by code outside those
    forms is not seen, a listed name reached any other way or a name the list does not hold (through `__self__` of a builtin, a
    container or a copy of a namespace mapping other than the file's own module's or the builtins' (_NS_USE above), a module's own
    `__setattr__` or `__delattr__` method, a listed name, attrgetter or
    methodcaller imported from a module other than its own, a name built at run time, gc or ctypes among them, and through a
    module reached by a tuple or list unpacking, an inline walrus, `sys.modules.__getitem__`, a for-loop target, a parameter
    default or a starred argument) being outside the list, and a function's write through a local
    of the same name does not count; a scalar local or parameter a function rebinds at run time through its own frame (the
    frame's locals, which Python 3.13 and later write through to the function) is not seen either, a page's text read as the
    function's text binds it (the stated limit on those versions, its witness the (x) case's frwb), while a container the function
    binds and reads whole, changed through that same frame's local mapping reached or run as code in its own body (one of the seven bare
    names in _FRAME_NAMES (locals, vars, exec, eval, _getframe, currentframe, getargvalues), one of the four attributes in _FRAME_ATTRS
    (_getframe, currentframe, getargvalues, f_locals) spelled as an attribute on any receiver, and a name a statement of the module's or
    the function's own body, outside every def, class or lambda statement it nests (header and body alike), binds to a frame primitive, its
    bound value the
    primitive's own bare name or attribute, by a plain or annotated assignment, a walrus, an unpacking of a list or tuple literal into
    a target list of as many elements (each plain name there bound to the value at its place, beside a starred or nested target too)
    or a `from ... import` of one of the seven names, and any name such a statement binds to a name so bound),
    is refused by name on every version, its reason naming the spelling found, not a frame reached (a mutation reaches the real object;
    _containers, _reaches_frame, _FRAME_CONTAINER); a change to those locals reached in any other spelling (among them locals or vars
    as an attribute on a receiver, exec or eval reached as an attribute, f_locals as a bare name, one of the four attributes named by a
    string, `getattr(frame, "f_locals")`, and any binding of a name to a primitive the resolution does not read, a plain name among
    the targets of an unpacking whose targets are not as many as its values and a name a nested unpacking target binds, an alias whose
    bound value is any other expression (an if-expression, a call) and a binding in the header or the body of a def, class or lambda
    statement) is the stated precondition, one witness for each road named (fratr, frxr and frev; bfl2; fgs2; fsst and fsnt; tx4 and
    txc; tx2, nstb, tx3, frcl and flam), while a binding a
    nested scope makes by an assignment carries the primitive's spelling in the function's subtree and refuses (nsta); code the
    function runs that the census does not read (a helper it calls as a statement, a method on self, a context manager it enters)
    reaching the caller's frame instead is a stated limit, its witness fhlp. Beside that precondition stands the item limit (the
    19:33Z ruling, _containers): what code does with an item of a container the proof reads, or with the object a name bound other
    than to a literal or a call of parse_qs holds, after the census has read it, in a spelling the proof does not refuse, passes
    silently, one witness for each road (iunp, iuag and iatr, a name an unpacking binds from a display that holds the item; isag, a
    subscript of a new object holding it as an augmented assignment's target; imat and xmat, a match capture; xies and cesw3, an item
    stored into another object or held in a new object that leaves the function; dmcap, dmcapl, dxies and dcmp, a default taking the
    item through a name the proof does not follow (a match capture, an attribute of another object, a comprehension's target in a
    def's default); dwal, a name a walrus in a def's default binds to the item, changed through after the def; xput, xesc and xiop, on
    a name bound
    other than only to calls, and dop, xiop's operand in a default; oeqw and cop1, an operand; pput, the call limit on a parameter,
    and dcall, dcall0, dcalll and dcallc, the call limit in a default, the item handed to a call whose return the default takes; mupn,
    mfl, mcf and masf, the module side's unpacking nested in another, a loop's or a comprehension's, and its subscript of a new
    object, in a function, and mtn, mtl, mcn, mcg and mts, the same at module level, mcg a generator expression's, Scan.cflows). A
    parameter in the body is
    a value slot whose text is its argument's, read at the call, or, where a followed call omits it, its default's (_defaults).
    The other value slots the pass reads as no text are the kinds and roles a full served pass over the kernel hands resolve: a
    None, bool or int constant, the empty bytes constant, a Mult or LShift whose operands are int constants or such BinOps
    (`2 * 1024`, `1 << 20`), each refused by name where it stands directly as the right operand of a `%` (bare, a tuple element or a
    dict literal's value), a `.format` argument or a value of a `.format_map` dict literal, whether or not a conversion takes it
    (_SLOT_FORMAT, _format_slots: a conversion can turn a value
    slot into characters; one held deeper there is read as a value slot), and `__file__` as a bare name where it is the file's own
    path, which the import system binds (_file_slot: no statement of the file binds it, in any scope and by any form, the file
    writes no name of its module namespace through a computed name and may not rewrite it at run time, no module-level statement
    writes it, and the module holds no star import). In a file where a statement binds it, `__file__` is refused by name wherever a
    page reads it (_FILE_BOUND: a bare name, the base of a receiver, a container or an attribute, and a callee, never inside the
    index of a subscript over a container whose text the pass does not read, which is not read at all), before any
    scope's or module-level binding of it is read; in the other cases where it is not the file's own path it is refused as another
    module name is; and wherever it is not, a file read whose path _path would build from `Path(__file__)` or `open(__file__)` has
    no path, a file the walk does not scan. Any other file read's path is accepted only as _path proves it by binding (Path the
    file's one top-level `from pathlib import Path`, never rebound, and open the builtin, neither bound by a function scope around
    the read, each handed one positional argument and no keyword; a module constant read in the module's scope and a plain local
    bound once; no relative path spelled as a string constant, no name a function scope binds where the module binds a constant of
    that name, and no module constant the file writes at run time), else refused by name (_PATH_UNPROVEN, the clause naming the
    condition it fails); and served_texts covers a file only where the walk scanned it as browser text (_browser_text), refusing one
    it scanned as Python, as shell or as JavaScript with the DOM arm off (_FILE_KINDS). Anything else resolve reaches (and it
    reaches no index of a subscript over a container
    whose text the pass does not read) is text the census did not read, a SERVED problem naming its kind (_unread): a non-empty
    bytes, float, complex or Ellipsis constant, a format spec (refused, not read:
    before 3.12 its parts carry the f-string's own position, which served_texts's read-once key would take for a part already
    read), a Mult or LShift over anything else, every other operator, a comparison, a unary expression, a subscript by a slice or
    an index other than a constant over a container whose text the pass reads (_SLICED: a slice never reaches resolve, the
    Subscript arm decides it), a subscript by a constant index over such a container that stands as an operand of a `+`, a `%`,
    an f-string or a `.join`, `.format`, `.format_map` or `.replace` (_SUB_OPERAND, _sub_operand, _join_operands: the pass reads
    its container whole and not the text the join makes of the pieces the indexes select; read no further, a subscript of any
    other container read piece by piece and a subscript read through a function under the call limit), a value slot that stands
    directly as the right operand of a `%`, a `.format` argument or a `.format_map` value (_SLOT_FORMAT), a builtin other than the
    seven a page
    may name (_BUILTIN_OTHER), a call of str with more than one positional argument, a starred argument or a keyword other than
    object (_STR_DECODE), a name the import system binds
    in every module other than `__file__` (`__doc__`, `__name__`,
    `__package__`, `__spec__` and `__loader__`, where the file does not bind it: _IMPORT_WHY), `__file__` in a file where a
    statement binds it (_FILE_BOUND), a join, format, format_map or replace called on the name str, bytes or bytearray (_UNBOUND,
    _unbound_text_call: _const_text folds none, so its pieces are not read apart), a `%`, `.format` or `.format_map` on a string
    constant with a field or precision wider than a million characters (_WIDE, _wide, each `%` read as Python parses it:
    _pct_fields) or a replacement field in a format spec (_NESTED, _nested), which _const_text does not expand, a join whose folded
    text may run past a million characters (_LONG, _long, _FOLD_CAP), a replacement field reaching an attribute or an index of its
    argument
    in a `.format` or `.format_map` whose format string the pass reads (_FIELD_REACH, _field_reach), a
    `.format` or `.format_map` whose format string the receiver reaches other than as a string constant, a join of them or a name
    bound to one (_TEMPLATE, taken only where the receiver is no class, stands as no subscript operand and is read with no refusal
    by name in whole or in part, a refusal of the receiver standing for the text it holds), an attribute read on self (_SELF_ATTR),
    on any other parameter (_PARAM_ATTR) or on an except name (_EXCEPT_ATTR), each by the root its base reaches by binding
    (_attr_root), a class attribute, read, or a method called, through the class's own name, a name the census resolves to it, a
    method call on or a subscript of a name whose value holds it or of such a value itself, or any other base whose root by binding
    is a class (_CLASS_ATTR), a container the container proof refuses (_CONTAINER), a function or class object read as a value
    (_FUNC_OBJECT), a lambda reached through a name's value (_LAMBDA_VALUE), a callee the census does not prove a plain def
    (_DEF_ASYNC, _DECORATED, _DEF_YIELD, _DEF_ALIAS, _DEF_STRING), every method called on self (_SELF_METHOD, _METHOD_OVERRIDE,
    _METHOD_UNPLACED, _REPLACED, _REPLACED_OPEN, _METHOD_SUBCLASS), a route class's method called other than on the calling method's
    own first parameter (_METHOD_CALL), a method called on any other parameter or a name spelled self whose name the file stores,
    deletes or names to a setter as an attribute (_METHOD_STORED), a
    `.join` whose one argument or, unbound as in `str.join("", {...})`, its second, is or holds a set literal or a set comprehension
    as the census reads it (_set_value, _JOIN_SET: a set's iteration order is not fixed, so its join is no one text) and a kind with no
    arm among them, as is a route whose body yields no piece and no file slot."""
    def __init__(self, rel, tree, res):
        self.rel, self.res, self.consts, self.funcs, self.methods = rel, res, {}, {}, {}
        # the builtins less the names the import system binds in every module (its docstring, name, package, spec and loader),
        # which a module holds as its own and resolve refuses by name (_IMPORT_NAMES)
        self.imports, self.builtins, self.classes = set(), set(dir(builtins)) - _IMPORT_NAMES, {}
        ns = res.ns.get(rel) or _NS_NONE   # a file that writes its module namespace through a computed name, or may rewrite it at run
        # time, reads no module name (a builtin among them), the reason naming the form, and one that may write its builtins takes no builtin
        runtime = bool(ns["runtime"])
        self.computed, self.shadowed, self.file_bound = ns["computed"] or runtime, ns["computed"] or ns["builtins"] or runtime, ns["file"]
        self.computed_why = _COMPUTED if ns["computed"] else _RUNTIME % ns["runtime"] if ns["runtime"] else None
        # a name bound by one top-level plain single-name assignment and nothing else at module level, in a file that writes no name
        # of its module namespace through a computed name
        self.consts = {} if self.computed else _module_consts(tree)
        self.bound = _module_bound(tree)     # every module-level binding's count: a top-level import, def or class is exempt as a name's one binding
        info = _module_info(tree)
        self.star, self.block, self.defs, self.inblock, self.assigned = info["star"], info["block"], info["defs"], info["inblock"], info["assigned"]
        self.annotated = info["annotated"]
        for node in tree.body:   # the top-level statements: the imports, functions and classes exempt or followed as a name's one binding
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): self.funcs[node.name] = node
            elif isinstance(node, ast.ClassDef):
                self.classes[node.name] = node
                self.methods[node.name] = {n.name: n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            if isinstance(node, (ast.Import, ast.ImportFrom)): self.imports.update((a.asname or a.name).split(".")[0] for a in node.names if a.name != "*")
        # whether a top-level `from pathlib import Path` binds the name Path to pathlib's Path (_path's proof of a Path(...) call, with
        # _sole: layer v of the eleventh round's rulings)
        self.parse_qs = {a.asname or a.name for node in tree.body if isinstance(node, ast.ImportFrom) and node.level == 0
                         and node.module == "urllib.parse" for a in node.names if a.name == "parse_qs"}
        # the names a top-level `import` binds, each to its module, and those a top-level `from collections import` binds, each to the
        # name it imports (_class_callee: a method spelled on a class of collections)
        self.import_mods = {a.asname or a.name.split(".")[0]: a.name if a.asname else a.name.split(".")[0]
                            for node in tree.body if isinstance(node, ast.Import) for a in node.names}
        self.from_collections = {a.asname or a.name: a.name for node in tree.body if isinstance(node, ast.ImportFrom) and node.level == 0
                                 and node.module == "collections" for a in node.names if a.name != "*"}
        self.pathlib_path = any(isinstance(node, ast.ImportFrom) and node.module == "pathlib"
                                and any(a.name == "Path" and (a.asname or a.name) == "Path" for a in node.names) for node in tree.body)
        # every module-level binding, from the count's own walk, and the builtins: a bare name of one not a constant is classified by
        # _base (resolve's Name arm): a top-level import, def or class statement that is the name's one module-level binding, or a
        # builtin no module-level binding shadows (the import system's names excepted: self.builtins), is a value slot when nothing
        # rebinds the name (self.rebound) and the module holds no star import, and any other is refused with the reason _module_why gives
        self.names = set(self.builtins) | set(self.bound)
        self.memos = {x for x in res.writes.get(rel, {}) if x in self.consts}   # the module containers some code writes (Scan's walk)
        # layer iv's module side: a module name bound to a call whose object the file changes other than by the forms Result.writes
        # records (a store through an item of it or on it as an attribute, a setattr or delattr on it, a method called on it or on an
        # item of it outside the closed set _READ_THROUGH, a method called on it whose return is dropped, a changer read off it or an
        # item of it unbound, an attribute read off it other than as a method's callee, it or an item of it handed to another
        # operand's method by an operator, or a name bound to it, to an item of it or to a new object holding one changed through or
        # let out of the file's sight: Scan.cwrites, Scan.cflows), read as a
        # run-time memo wherever the pass takes text through it (a receiver, a container, an attribute's root, a bare value, a local's
        # value), and only as a call's argument not (cargs: the call limit, what the callee does with it not read, and its text the
        # call's own arguments)
        self.cmemos = {x for x in res.changed.get(rel, ()) if isinstance(self.consts.get(x), ast.Call)} - self.memos
        self.cargs = set()   # ids of the names standing directly as a call's argument in a page (resolve's Call arm)
        self.rebound = set(res.rebinds.get(rel, {}))   # the names a function binds under `global` or a module-level statement writes
        self.pieces, self.files, self.problems = [], [], []
        self.op_refused = set()   # ids of subscripts refused by name as a +, %, f-string or join operand (_refuse_operands), read no further
        self.joins, self.noted = {}, set()   # the joins of string constants (_note), and the `+` nodes and f-strings a chain already recorded
        self.held = []   # every locals map a context built, held for the pass: a local read is keyed on its map's id, never reused
        self.comp_at = {}   # id(a comprehension's source) -> the context Python evaluates it in (resolve's comprehension arm, the reviewer's 14:42Z ruling)
        # id(a locals map a nested scope's context holds: a function defined in the page function, a comprehension, a lambda) -> name ->
        # the context of the scope that binds that name, for each name the map takes from the scope around it (_value_ctx)
        self.local_at = {}
        self.rctx = {}   # (id(a followed def), id(its def statement's context) or None) -> (the def, its context, that context): _followed
        self.undrawn = set()   # (id(a method call), its place) refused by _undrawn: one gap, one line
        self.scopes = {}   # id(function) -> (the function, its _locals): each function's body walked once per pass, each context given copies
        self.def_ctx = {}   # id(nested function) -> (the function, the context of the function its def statement stands in, that function):
        # its defaults' scope, and the scope its name binds in (_def_uses)
        self.tree, self.method_ids = tree, None   # the ids of the file's methods (_method_defs), read once, on the first context that asks
        self.deco_bound = ns["deco"]   # whether a statement of the file binds staticmethod or classmethod, in any scope and by any form (Scan's walk)
        # decision 2's reads, once per file: the route classes' method names (run: _route_methods), each class's method resolution
        # order (_mro) and the def statement a method called on self resolves to (_definer)
        self.route_methods, self.mros, self.definers = set(), {}, {}
        # the attribute names the file stores, deletes or names to a setter, read once per file before any route is read (run:
        # _stores), which _replaced and decision 2's refuse arm read; and every class statement of the file, in any scope, read once,
        # at the first override check (_file_override)
        self.stores, self.class_nodes = None, None
        self.sopen = None   # whether the file's setter read fails closed, read once per file at the first _replaced (_setters_open)
        self.cproofs = {}   # id(function) -> the container proof's refusals for the names it binds (_containers), read once per function
        self.frame_aliases = None   # the module's names bound to a frame primitive (_frame_alias_names over tree.body), read once (_reaches_frame)

    @staticmethod
    def _locals(fn):
        """(name -> every value bound to it in the function's own body: a single-name assignment, an augmented or annotated one, a
        loop, unpacking or with target's source, a walrus, and a local container's appended or stored values; the other names the
        body binds (a store's target, an except name); the functions defined inside it; name -> the forms that bind it in the
        function's scope, for row (d): "value" for a name with values here, "comp" for a comprehension's target, "except", "import",
        "def", "class", "del", "match", "store" for any other name a store binds, "global" and "nonlocal" for a declaration, and
        "nonlocal" too for a name a function or class nested in this one declares nonlocal). A loop, unpacking, with or
        comprehension target binds only the names it stores, as Python binds them: a name, or a name inside a tuple, list or
        starred target (Scan._key_targets, the reader _key_binds takes each target's names with); a name inside an attribute's
        base or a subscript's container or index, which the target only reads, takes no form and no value from it, so where the
        function binds it no other way the scope around the function or the module decides it (correctness-1 of the eleventh
        round's review: a name only read in a target took the target's source for its value). A walrus inside a target binds its
        own name to its own value, as every walrus does here. Nested defs, classes and lambdas are not entered, but a def's or a class's header
        and a lambda's defaults are read as this function's statements (_header), so a walrus there is a local with its value."""
        out, bound, nested, stack, src, mut, forms, stores, comp, augs = {}, set(), {}, list(fn.body), {}, {}, {}, set(), set(), set()

        def form(name, how): forms.setdefault(name, []).append(how)
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if isinstance(n, ast.ClassDef): form(n.name, "class")
                else: nested[n.name] = n; form(n.name, "def")
                for m in ast.walk(n):   # a nonlocal declaration inside it rebinds a name of this scope the reader does not see
                    if isinstance(m, ast.Nonlocal):
                        for x in m.names: form(x, "nonlocal")
                stack.extend(_header(n)); continue
            if isinstance(n, ast.Lambda): stack.extend(_header(n)); continue
            if isinstance(n, (ast.Import, ast.ImportFrom)):
                for a in n.names: form((a.asname or a.name).split(".")[0], "import")
            elif isinstance(n, (ast.Global, ast.Nonlocal)):
                for x in n.names: form(x, "global" if isinstance(n, ast.Global) else "nonlocal")
            elif isinstance(n, ast.comprehension):   # the names its target stores, never a name the target only reads
                comp.update(name for name, _ in Scan._key_targets(n.target))
            elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name: form(n.name, "match")
            elif isinstance(n, ast.MatchMapping) and n.rest: form(n.rest, "match")
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Del): form(n.id, "del")
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name): out.setdefault(n.targets[0].id, []).append(n.value)
            elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name): out.setdefault(n.target.id, []).append(n.value); augs.add(n.target.id)
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None: out.setdefault(n.target.id, []).append(n.value)
            elif isinstance(n, (ast.For, ast.AsyncFor)):   # each name the target stores reads the source (Scan._key_targets)
                for name, _ in Scan._key_targets(n.target): src.setdefault(name, []).append(n.iter)
            elif isinstance(n, ast.Assign):   # an unpacking (or a chained assignment): each name a target stores reads the value
                for tg in n.targets:
                    for name, _ in Scan._key_targets(tg): src.setdefault(name, []).append(n.value)
            elif isinstance(n, (ast.With, ast.AsyncWith)):
                for it in n.items:
                    for name, _ in (Scan._key_targets(it.optional_vars) if it.optional_vars is not None else ()):
                        src.setdefault(name, []).append(it.context_expr)
            elif isinstance(n, ast.NamedExpr): src.setdefault(n.target.id, []).append(n.value)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store): bound.add(n.id); stores.add(n.id)
            elif isinstance(n, ast.ExceptHandler) and n.name: bound.add(n.name); form(n.name, "except")
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in _MUTATORS and isinstance(n.func.value, ast.Name):
                mut.setdefault(n.func.value.id, []).extend(n.args + [k.value for k in n.keywords])
            if isinstance(n, ast.Assign):
                for tg in n.targets:
                    if isinstance(tg, ast.Subscript) and isinstance(tg.value, ast.Name): mut.setdefault(tg.value.id, []).append(n.value)
            stack.extend(ast.iter_child_nodes(n))
        for k, v in src.items(): out.setdefault(k, []).extend(v)
        bound -= set(src)
        for k, v in mut.items():
            if k in out: out[k] = out[k] + v
        for k in out: form(k, "value")
        for k in comp: form(k, "comp")
        for k in stores - set(out) - comp: form(k, "store")
        for k in augs: form(k, "aug")   # a name bound by an augmented assignment (the key walk cannot evaluate it: Scan._key_binding)
        return out, bound, nested, forms

    @staticmethod
    def _returns(fn):
        out, stack = [], list(fn.body)
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)): continue
            if isinstance(n, ast.Return) and n.value is not None: out.append(n.value)
            stack.extend(ast.iter_child_nodes(n))
        return out

    @staticmethod
    def _def_shape(fn):
        """The follow proof's conjuncts on the def statement itself (layer ii of the eleventh round's rulings, the census following a callee only where it
        proves a plain def): the reason the census does not follow a call of fn, or None where fn is a def statement, not an async
        def (_DEF_ASYNC: its call returns a coroutine), carrying no decorator (_DECORATED: Python calls the decorator's return in the
        def's place, staticmethod and classmethod among them) and with no yield in its own body (_DEF_YIELD, _yields: its call returns
        a generator, whose values its return statements do not hold). The two follows ask it (a module function and a function
        defined in the page function) before they read fn's returns (_returns) and its defaults (_defaults); with _def_uses (the
        name's reads) and the binding test each follow makes (bound once by that def statement, never rebound: _sole, _scoped's
        ["def"]), it is the whole proof, and every other callee refuses by name. The method arm, which follows nothing, asks it only
        for the reason it names first (_method_call, after _definer)."""
        if isinstance(fn, ast.AsyncFunctionDef): return _DEF_ASYNC
        if fn.decorator_list: return _DECORATED
        if _yields(fn): return _DEF_YIELD
        return None

    def _def_uses(self, fn, holder):
        """The follow proof's conjuncts on the name fn's def statement binds (layer ii of the eleventh round's rulings): the reason the census does not
        follow a call of it, or None where no statement of the file reads that binding other than as a call's callee and, for a
        module function, no string constant of the file spells its name. `holder` is None for a module function (a top-level def
        statement, its name's one module-level binding, never rebound: _sole), and for a function defined in the page function the
        def statement whose body holds it (its name's one binding there: _scoped's forms ["def"]). A read that reaches the binding
        (_binding_scope over the scopes around the read: a scope that binds the name itself holds a binding of its own) other than as
        a call's callee is an alias, an argument, a store or a delete of the function or of one of its attributes (`f.__code__ =
        ...`, `f.__defaults__ = ...`, setattr(f, ...), a decorator applied by hand among them), each of which may run code the census
        does not read as the callee (_DEF_ALIAS); a string constant that spells a module function's name is a key a lookup by name may
        reach it through (`globals().get("f")`: _DEF_STRING). A module function's reads come from the scan of its whole file
        (Result.fn_refs, from Scan's walk), where a file no scan read has none and refuses; a nested function's from a walk of the
        def that holds it (_name_reads), outside which its name binds nothing."""
        if holder is None:
            got = self.res.fn_refs.get(self.rel)
            if got is None: return _DEF_ALIAS   # no scan read the file's names: no proof
            if any(_binding_scope(fn.name, at, chain) is None for at, chain in got[0].get(fn.name, ())): return _DEF_ALIAS
            return _DEF_STRING if fn.name in got[1] else None
        return _DEF_ALIAS if any(_binding_scope(fn.name, at, chain) is holder for at, chain in _name_reads(holder, fn.name)) else None

    def _ctx(self, fn, cls, outer=None, where=None, route=False):
        """(the value-slot names: parameters and the other names the body binds, the locals, the class, the nested functions, the
        place's name for SERVED_ALLOW, name -> the forms that bind it in the innermost function scope that binds it: _locals's and
        "param"); a nested function's context (outer given) sees the enclosing function's names and locals under its own, and its
        own binding of a name decides over the enclosing one's; a local it takes from the enclosing function has its values read in
        the enclosing function's context, where Python evaluates them (local_at, _value_ctx). A name the function declares `global` names the module's binding:
        it is no local here, and the module's binding is read. The first parameter of a route handler (route, from run) that carries
        a decorator, whatever it is bound to, or that stands in a file where a statement binds the name staticmethod or classmethod
        (self.deco_bound, from Scan's walk: _namespace_flags's "deco") is not classified (_Unclassified); that of any other method (_method_defs) whose def carries no decorator is
        self by binding (_SelfParam)."""
        a = fn.args
        params = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs} | ({a.vararg.arg} if a.vararg else set()) | ({a.kwarg.arg} if a.kwarg else set())
        got = self.scopes.get(id(fn))
        if got is None: got = self.scopes[id(fn)] = (fn, self._locals(fn))   # the function held with its entry, so its id is never reused
        local, bound, nested, forms = got[1]
        local, bound, nested, forms = dict(local), set(bound), dict(nested), {k: list(v) for k, v in forms.items()}
        for p in params: forms.setdefault(p, []).append("param")
        first = (a.posonlyargs + a.args)[:1]
        if outer is None and first:
            if self.method_ids is None: self.method_ids = _method_defs(self.tree)
            if route and (fn.decorator_list or self.deco_bound):
                # a route handler's decorator, whatever it is bound to, may make the first parameter self, the class or anything else,
                # and a file that binds staticmethod or classmethod may rebind the decorator a def carries: not classified, so a method
                # called on it and it called are refused by name (_UNCLASSIFIED)
                forms[first[0].arg] = _Unclassified(forms[first[0].arg])
            elif id(fn) in self.method_ids and not fn.decorator_list:   # a method's first parameter, however spelled, with no
                # decorator on its def: self by binding (_attr_root); a decorated method's is a parameter like any other, and the
                # follow arm, which reads no method's body, refuses a call of a decorated def as no plain def (_DECORATED)
                forms[first[0].arg] = _SelfParam(forms[first[0].arg])
        gl = {k for k, v in forms.items() if "global" in v}
        if outer is not None:   # a name the enclosing function binds and this one does not: its values read where the enclosing binds it
            own_local = local
            params, local, nested, forms = params | outer[0], dict(outer[1], **local), dict(outer[3], **nested), dict(outer[5], **forms)
            self.local_at[id(local)] = {k: self._value_ctx(k, outer) for k in outer[1] if k not in own_local}
        for k in gl: local.pop(k, None); nested.pop(k, None)
        self.held.append(local)
        ctx = (params | bound) - gl, local, cls, nested, where or fn.name, forms
        for k, n in got[1][2].items():   # the defs this function holds run their defaults here (_defaults), and their names bind here (_def_uses)
            if k not in gl: self.def_ctx[id(n)] = (n, ctx, fn)
        for k, why in self._containers(fn, ctx).items():   # layer iv: a container of this scope the proof refuses, refused wherever it is read
            if k not in gl and not isinstance(forms.get(k), (_SelfParam, _Unclassified)): forms[k] = _Container(forms[k], why)
        return ctx

    def _containers(self, fn, ctx):
        """name -> the reason the container proof refuses fn's binding of it (layer iv, the eleventh round's 04:38Z ruling: a rule over
        occurrences; the 07:37Z ruling on its fourth form; the 04:52Z ruling's binding and change forms unchanged). A local container
        the census reads is read whole only when EVERY occurrence of its name in the function, resolved by binding, is one of the proven
        forms, keyed on the name's role in that occurrence: its one binding (a plain single-name assignment to a list, dict, set or tuple
        literal or a call whose return the census reads as a value slot, which _base reads as "exempt": an import's, one of the seven
        builtins a page may call, a parameter's, or a method's on one of those); the target base of a subscript store with a str or int constant
        key as the one target of a plain assignment, whose value the census reads with its values (_locals); the receiver of an append
        or extend of one plain argument the census reads; and the FOURTH FORM (07:37Z), a read that hands the container to no other code:
        the receiver of one of the read methods of the type its one binding gives it, or the base of a subscript load on a type that has
        one, wherever it stands, tests included. The read methods are a closed set per type (_TYPE_READS): a dict's get, keys, values,
        items and copy and a subscript load; a list's index, count and copy and a subscript load; a tuple's index and count and a
        subscript load; a set's copy; index and count only with a constant argument (with any other, _flow's operand check refuses:
        Python hands each item to the argument's method). The type comes only from the one binding: a dict, list, tuple or set literal,
        or a call of parse_qs (a top-level `from urllib.parse import parse_qs`, the name bound once), a dict; a container bound to any
        other value slot (dict(...), an import's call) has no type, and every read method and subscript load on it refuses
        (_CT_UNTYPED). Every other read of the container's own name refuses it, keyed on its role (_own_use, _CT_READ, _CT_BIND,
        _CT_HANDED, _CT_INDEX, _CT_AUGV, _CT_TYPE, _CT_SUB, _CT_UNTYPED): a read method outside the type's closed set or a spelled-out
        dunder (q.__getitem__, q.__contains__); a subscript load on a set; the container as an operand of a binary operator, a
        comparison or `in` (whatever the other operand), or as a subscript's index or a slice's bound, or the value of an augmented
        assignment (Python hands it to the other operand's or the subscripted object's method there: the dunder hand-off); the whole
        container bound to another name; and every other read (a test, an identity test, a boolean operation's operand, an
        if-expression's branch, held in a new object, a return, an f-string's field). A read method's or a subscript load's RESULT is
        an item the census follows by binding like any other value (07:37Z condition 2); the proof covers the container, and an item
        of it (a value standing inside it, where no new object stands around it: the item itself, a name bound to it, whose binding's
        value is the item with no display, operator or comprehension around it or which is a loop's or a comprehension's target over
        such a display, and a subscript load or a read method taken from a new object holding it: _flow's `inside`, no level left) it
        reads by condition 1's principle, through the closed read set of the item's own type (_item_types, _value_type: known from a
        dict, list, tuple or set literal's elements, a string constant a str, parse_qs's items lists of str, met with each value a
        constant-key store or an append puts in the container or an extend's argument holds; a copy of a dict, a list or a set, or a
        slice of a list or a tuple, of its receiver's type, and a new object holding the receiver's items, so a change to it reaches
        no item and a change
        through its items does). Any other method called on the item, a read method or a subscript load outside its type's set (a
        spelled-out dunder among them, whether the return is used or dropped: _CT_ITEM_USE; a str has no read set, nor has an item
        whose type the census does not know, a call's return or a name it does not follow: _CT_ITEM_UNKNOWN), an attribute read off it
        other than as a method's callee (_CT_ITEM_ATTR), a method spelled on a class handed it as its first argument (_CT_ITEM_CLASS:
        a builtin class, or a class of collections imported as the module or by name, _class_callee), a store into it ("changed
        through an item of it or an expression holding it"), an augmented assignment to a name bound to it (_CT_AUG: it runs the
        item's own in-place method, and it refuses for a str item too, whose augmented assignment only rebinds the name), and setattr
        or delattr handed it,
        refuses the container, each where no new object stands around the item (_CT_THROUGH through a name, or "changed through
        <name>, a name the function binds to it or to an item of it"); so
        does its hand-off to another object's method
        by an operator whose other operand is no constant (an operand of a binary operation or a comparison, a subscript's index, a
        slice's bound, an augmented assignment's value, or what a .index() or .count() with an argument that is no constant compares:
        _CT_ITEM), and any use of it the census does not read (called, or stored into another object, an attribute or a global or
        nonlocal name); an item compared or combined with a constant is read, only its own type's method and the constant's running
        there; and an item handed as an argument to any other call, a method spelled on any other value among them (a class the file
        defines or another import names, a module's function), is under the call limit, as the container is (its witnesses ihc, ihg
        and ihn, a list read out of a local dict of lists by a subscript load, by `.get` and through a name bound to it, which a
        module function it is handed appends a fetch to, and itcw, such a list handed to append spelled on a class of the file that
        derives from list), in a lambda's default too (dcallc), while in a def's default the occurrence refuses it as one in a def
        nested in the function. A container is a name an assignment, augmented or annotated, or a walrus binds whole to such a literal
        or comprehension or to a call of parse_qs (_parse_qs_call), or a name with one of these uses (changes()). At any level of new
        objects around it, since a new object that holds it hands it on: a binding to a name the function declares global or nonlocal;
        a default of a function or a lambda that holds it (_flow's escape _AS_DEFAULT, the value walked up to the default through
        subscript loads, read methods' returns, boolean operations, if-expressions' branches, walruses' values, starred values, awaits
        and new objects), unless the name is no parameter and
        every binding of it is a plain assignment of one name to a value _value_type types as a str (strs: a string constant; a walrus
        of one; a boolean operation or an if-expression whose
        operands or branches all are; or an item read, by a subscript load without a slice or by a dict's get (its default, where it
        has one, of the items' type too), out of a container every item of which is one, such a container being a list, tuple or dict
        literal (with no starred element or ** entry, a dict's items its values), a slice of a list or a tuple one, a copy of a list
        or a dict one, an item so read out of a container every item of which is such a container of one kind, or a walrus, a boolean
        operation or an if-expression over such containers of one kind; an item read out of a container that holds none, which Python
        cannot read, has no type, _UNSET, and is left out wherever types are met (_meet): a str, or None where a get finds no key,
        which no code changes in place; never a parameter, since its caller's value is bound as well); and, for a name bound only to
        calls (called, below), it itself leaving the function's sight (stored into another
        object, a default, matched, called or held where the census does not read it). At no level of new objects around it: an
        attribute read off it other than as a method's callee, whatever the name is bound to (the 19:33Z ruling's refusal of xatr's
        road, one check at 0 live: a local whose attribute a page reads is refused as a container, so the root walks read a local's
        values only for a comprehension's target and from a receiver with no attribute read on its path, _attr_root); a store or
        delete through it or through an item of it; an append or extend; setattr or delattr, or a method spelled on a class, handed
        it or an item of it; an augmented assignment to a name bound to it or to an item of it, which runs that value's own in-place
        method (`e += [v]` is list.__iadd__, `e |= {...}` dict.__ior__: "aug", an event the walk records at the target, a Store, where
        it reaches that name; the container's own name so assigned is a second binding); on the container itself (its own name, or a
        name bound to it whole), one of the in-place changers (_CHANGERS, `__init__` and popleft among them) called on it, or a method
        whose return a statement drops (a changer read off it unbound is an attribute read, above); on an item of it, any method (a
        read method is a step of the item's walk, never a "method" use) or an attribute read; and, for a name that is no parameter and
        every binding of which is a plain assignment of one name to a call (called: the census reads it as that call's value slot or a
        followed function's return), any use outside a closed set (a read, a call's argument, a subscript load, a binding to a name
        the walk follows, the name itself an operand, and a method of _READ_THROUGH with its return used): any other method, and an
        item of it leaving the function's sight or handed to another object's method by an operator (the 07:37Z ruling's condition 2);
        each directly or through a name it binds to it, to an item of it or to a new object holding one, at the levels of new objects
        its binding holds it at (an unpacking's names take the level of the display it reads). What these uses do not mark, and what
        the rule below does not refuse, is the item limit (the 19:33Z ruling), which SERVED_PAGES and _Served's docstring state beside
        the frame precondition: what code does with an item of a container the proof reads, or with the object a name bound other than
        to a literal or a call of parse_qs holds, after the census has read it, in a spelling the proof does not refuse, passes
        silently, one witness for each road: a name an unpacking binds from a display that holds the item, which takes that display's
        level, so a change through it is read as done to a new object holding the item (iunp, appended to; iuag, extended by an
        augmented assignment; iatr, a queue's put read off such a name unbound and called); a subscript of a new object holding the
        item as an augmented assignment's target, a store into that object (isag); a match statement's capture of the item, or of the
        name itself, for a name bound other than to a literal, a call of parse_qs or only calls (imat, xmat); an item of such a name
        stored into another object and changed there (xies), and an item of a name bound only to calls held in a new object that
        leaves the function (cesw3); a default of a function or a lambda that takes the item through a name the walk does not follow
        from the container, a match statement's capture (dmcap, a nested def's default; dmcapl, a lambda's), an attribute of another
        object the item is stored into (dxies) or a comprehension's target in a def's default (dcmp); a name a walrus in a def's
        default binds to the item, changed through after the def (dwal); on
        a name bound other than only by plain assignments of calls, a method outside the
        changers with its return used (xput), the name stored into another object (xesc) or an item of it handed to another object's
        method by an operator (xiop, and dop, in a nested def's default); a name bound to anything but a literal or a call of
        parse_qs, handed itself, or in a new object holding it, to another object's method by an operator (oeqw, cop1); and a change a
        function makes to its own parameter by a use outside those listed, the call limit (pput). A default of a function or a lambda
        that holds the name, or a name the walk follows from it (a "bind" step of _flow: a plain or annotated assignment, a walrus, or
        a loop's, a comprehension's or a with statement's target, an unpacking's names among them, outside every def or class
        statement and lambda body the function nests), marks the name at any level (unless strs holds), so that road refuses: _flow
        records the escape _AS_DEFAULT only where the value climbs to the default's ast.arguments through the steps that carry it on
        (a subscript load, a read method's return, a boolean operation, an if-expression's branch, a walrus's value, a starred value,
        an await, a new object). A def's default is part of the def statement (_scope_names chains the def over every name its header
        reads; a lambda's defaults run where it stands), so a name read there is an occurrence in a def nested in the function, which
        refuses a container whatever the use, and a bind step from it is not followed: a comprehension's target there holding the item
        (dcmp) and a walrus there inside a call, its name appended through after the def (dwal), are the item limit on a name the
        proof does not read as a container. Otherwise any other use in a default ends the walk as it does in the function's own body:
        a call's argument, the call limit, what the call returns not read (dcall, through a name bound to the item, a nested def's
        default; dcall0 and dcalll, the item directly, a nested def's and a lambda's; dcallc, a lambda's, on a container bound to a
        literal), and an operand, refused where the proof refuses such an operand and otherwise the item limit (dop, on a name bound
        through a boolean operation). The walk follows no match capture and no attribute of another object, so a default taking the
        item through one is the item limit (dmcap, dmcapl, dxies). The roads a check was measured for are the limit because that one
        check refuses
        pages of the live tree: the closed set on a parameter (pput's road); a method outside the closed set, an escape and an item's
        operand on a name bound to an expression (xput's, xesc's and xiop's); an item held in a new object that leaves the function,
        on a name bound to a call (cesw3's: an item of such a name that an unpacking binds, a str, stored in a new list into a dict);
        and the operand on a name bound to a call, itself or in a new object (oeqw's and cop1's: an int in a text concatenation); the
        unpacking's name, the subscript of a new object, the match capture, the item stored into another object and a default taking
        the item through a name the walk does not follow are the limit by the 19:33Z ruling. Any other
        occurrence refuses
        the container, by the rule and not by a list, the clause naming the role it fails (_CONTAINER): bound to another name, or to a
        name the function declares global or nonlocal (whose uses leave it), or into an attribute or another object; a second binding
        (an augmented assignment, a walrus, or a for, with, except, match or unpacking target); del; any method but append, extend or a
        read method of the type its binding gives it, or an attribute of it read other than as a method's callee; setattr or delattr,
        or a method spelled on a class, handed it as its first argument (_CT_CLASS); a store by a key that is no constant, or other
        than as the one target of a plain assignment; an append or extend of other than one plain argument; an augmented assignment to
        a name bound to it or to an item of it (_CT_AUG); and any occurrence in a function or lambda nested in it (a def's header, its
        defaults among them, included, as _scope_names chains it; a lambda's defaults, which run where it stands, excepted), or a
        class body it defines (a closure capture whose code the census does not read, or a class attribute; a nested scope's own
        binding of the spelling is not an occurrence of this container). A comprehension is read where it
        stands, as the function's own body is: a read of the fourth form and an append of a read value there pass, the container as a
        comprehension's source, in its condition or as its element refuses as any other read does (_own_use, _role), and a change the
        census cannot fold (a comprehension target store) refuses. Handed as an argument to any other call (not setattr or delattr,
        nor a method spelled on a class the census resolves, handed it as its first argument, which refuse above), it is under the
        call limit: what the callee does
        with it is not read (its witness ctwit, a container a function it is handed to changes), the census reading neither the callee nor
        the return. A container a
        function that reaches its frame binds refuses too (_reaches_frame, _FRAME_CONTAINER). The first parameter of a method (_SelfParam)
        or of a route handler (_Unclassified) is not read here: every attribute read on it and every method called on it refuses already,
        and code behind it is the stated limit. A name bound to an item of it is read by its spelling anywhere in the function, so a nested
        scope's own name of that spelling counts too, on the refusing side. A name is read again only at fewer levels than any it was
        read at standing the same way, inside it or not (a binding that holds itself ends the walk), each (name, levels, inside)
        popped expanded once, in _container_step. Computed once per
        function (self.cproofs)."""
        got = self.cproofs.get(id(fn))
        if got is not None: return got
        out = self.cproofs[id(fn)] = {}
        reaches = self._reaches_frame(fn)   # layer iv: a function that reaches its frame hands out the real container object (any version)
        names, parents = _scope_names(fn)
        local, _b, _n, own = self.scopes[id(fn)][1]
        a = fn.args
        params = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg] if x is not None}
        flows = {}

        def flow(n, fresh, inside):
            f = flows.get((id(n), fresh, inside))
            if f is None: f = flows[(id(n), fresh, inside)] = _flow(n, parents, fresh, inside)
            return f
        for x in sorted(set(own) | params):
            f = own.get(x, [])
            if "global" in f or "nonlocal" in f or not ("value" in f or x in params): continue
            xs = [(n, c) for n, c in names.get(x, ()) if c == (fn,) or _binding_scope(x, (n.lineno, n.col_offset), c[1:]) is None]
            # its uses, and those of every name bound to it, to an item of it or to a new object holding one (with the levels of new
            # objects around it, so a change reaches it only where none is left, and whether it stands inside it, an item: _flow). A
            # name is read again only at fewer levels than any it was read at standing the same way, which reach it wherever more do, so
            # a binding that holds itself (`x = x + [y]`) ends the walk; each binding of such a name is kept (binds) for the item types
            low, todo, events, binds = {(x, False): 0}, [(x, 0, False)], [], []
            while todo:
                y, fr, ins = todo.pop()
                for n, c in self._container_step(xs if y == x and fr == 0 and not ins else names.get(y, ())):
                    nested = any(isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)) for s in c[1:])   # in a
                    # function, lambda or class body nested in it: closure capture (code the census does not read) or a class attribute, so
                    # the container refuses; a comprehension is read where it stands (_own_use)
                    if not isinstance(n.ctx, ast.Load):   # a binding, but an augmented assignment to a name bound to it or to an item of
                        # it, or to a new object holding one, runs the target's in-place method (`e += [v]` is list.__iadd__, `e |= {...}`
                        # dict.__ior__): a change through that name ("aug"; its own name's is a second binding, refused below)
                        pa = parents.get(id(n))
                        if isinstance(pa, ast.AugAssign) and pa.target is n and (y != x or fr or ins):
                            events.append((n.lineno, n.col_offset, y, fr, n, c, "aug", pa, y, fr, nested, ins))
                        continue
                    use = _own_use(n, parents, own) if y == x and fr == 0 and not ins and not nested else None
                    if use is not None and (use[0] == "refuse" or use[2] is not None):
                        events.append((n.lineno, n.col_offset, y, fr, n, c, "own" if use[0] == "refuse" else "rmeth", use[1], use[2], 0, False, False))
                    for kind, node, detail, fresh, inside in flow(n, fr, ins):
                        if kind == "bind" and not nested:   # its value bound to a name of this scope, followed (a name only read stays read)
                            for z in detail:
                                if "global" in own.get(z, ()) or "nonlocal" in own.get(z, ()):   # a name whose uses leave the function
                                    events.append((n.lineno, n.col_offset, y, fr, n, c, "gescape", None, z, fresh, False, inside))
                                else:
                                    binds.append((z, node))
                                    if low.get((z, inside), fresh + 1) > fresh: low[(z, inside)] = fresh; todo.append((z, fresh, inside))
                        else: events.append((n.lineno, n.col_offset, y, fr, n, c, kind, node, detail, fresh, nested, inside))

            stores = [(n, c) for n, c in xs if isinstance(n.ctx, ast.Store)]
            # a name, no parameter, every binding of which is a plain assignment of one name to a call: the census reads it as that
            # call's value slot or a followed function's return, so a closed set of uses leaves it unmarked (changes)
            called = x not in params and bool(stores) and all(
                isinstance(parents.get(id(n)), ast.Assign) and parents.get(id(n)).targets == [n] and isinstance(parents.get(id(n)).value, ast.Call)
                for n, _c in stores)

            # a name, no parameter, every binding of which is a plain assignment of one name to a value _value_type reads as a str: a
            # default of a function or a lambda hands on a value no code can change in place (a str, or None where a dict literal's get
            # finds no key), so that hand-off marks no container of it (the page functions' own str locals a nested def takes as its
            # default, which _defaults reads). A parameter is never so read: its caller's value is bound too, which no assignment shows
            strs = x not in params and bool(stores) and all(
                isinstance(parents.get(id(n)), ast.Assign) and parents.get(id(n)).targets == [n]
                and _value_type(parents.get(id(n)).value, {}) == ("str", None) for n, _c in stores)

            def changes(e):   # a use that makes x a container, directly or through a name bound to it, to an item of it or to a new object
                # holding one. At any level of new objects around it, since a new object that holds it hands it on: a binding to a global or
                # nonlocal name; a default of a function or a lambda, unless x is no parameter and every binding of it is a str (strs); and
                # for a name bound only to calls (called), it itself (not an item of it) leaving the function's sight (stored into another
                # object, a default, matched, called or held anywhere else). At no level: an attribute read off it, other than as a method's
                # callee, which marks any name (the 19:33Z ruling's refusal of xatr's road, one check at 0 live; a changer read off it
                # unbound among them); a store or delete through it, an append or extend, setattr or delattr or a method spelled on a class
                # (_class_callee) handed it, or an augmented assignment to a name bound to it or to an item of it ("aug"); on its own name,
                # one of the in-place changers (_CHANGERS) called on it, or a method whose return a statement drops; on an item of it, any
                # method (a read method is a step, never a "method" event) or an attribute read; and for a name bound only to calls, any
                # use outside the closed set (a read, a call's argument, a binding to a name the walk follows, a subscript load, a method of
                # _READ_THROUGH with its return used, and the name itself an operand): any other method, and an item of it leaving the
                # function's sight or handed to another object's method by an operator (the 07:37Z ruling's condition 2)
                kind, node, detail = e[6], e[7], e[8]
                if kind == "gescape" or kind == "escape" and detail == _AS_DEFAULT and not strs or called and kind == "escape" and not e[11]:
                    return True
                if e[9]: return False
                if not e[11] and kind == "attr": return True   # an attribute read off it, or off a name bound to it whole: any name
                if kind == "aug": return True
                if called and e[11] and kind in ("operand", "escape"): return True
                if _item_recv(e) is not None: return kind in ("method", "attr")
                if called and not e[11] and kind == "method" and detail not in _READ_THROUGH: return True
                return kind in ("store", "grow", "handed") or kind == "tcall" and self._class_callee(node.func.value, ctx) or (
                    kind == "method" and (detail in _CHANGERS or isinstance(parents.get(id(node)), ast.Expr)))
            if not any(changes(e) for e in events) and not any(
                    (type(_bound_value(parents.get(id(n)))) in _DISPLAYS or self._parse_qs_call(_bound_value(parents.get(id(n))), ctx))
                    and _binds_whole(parents.get(id(n)), n) for n, _c in stores): continue   # no container: a literal or parse_qs's is one outright
            if reaches is not None: out[x] = _CONTAINER % (_FRAME_CONTAINER % reaches); continue   # a frame primitive spelled: refused
            if x in params: out[x] = _CONTAINER % "a parameter"; continue
            if f != ["value"] or len(stores) != 1 or stores[0][1] != (fn,):
                out[x] = _CONTAINER % ("deleted" if "del" in f else "bound by an augmented assignment" if "aug" in f
                                       else "bound other than once in its function's own body"); continue
            one = stores[0][0] if stores else None
            st = parents.get(id(one))
            if not (isinstance(st, ast.Assign) and len(st.targets) == 1 and st.targets[0] is one):
                out[x] = _CONTAINER % "bound other than by a plain assignment of one name"; continue
            v = _bound_value(st)
            if not (isinstance(v, (ast.List, ast.Dict, ast.Set, ast.Tuple)) or isinstance(v, ast.Call) and self._base(v, ctx)[0] == "exempt"):
                out[x] = _CONTAINER % "bound to neither a literal nor a call whose return the census reads as a value slot"; continue
            qs = self._parse_qs_call(v, ctx)
            ctype = ("dict" if isinstance(v, ast.Dict) or qs else "list" if isinstance(v, ast.List) else "tuple" if isinstance(v, ast.Tuple)
                     else "set" if isinstance(v, ast.Set) else None)
            types = None   # the item types, read at the first use of an item that needs them (_item_types)
            for e in sorted(events, key=lambda e: e[:2]):
                _l, _c, y, fr, n, c, kind, node, detail, fresh, nested, inside = e
                why, recv = None, _item_recv(e)
                if nested: why = "read or changed in a function, lambda or class body nested in it"   # closure capture (code unread) or a class attribute
                elif kind == "gescape": why = "bound to %s, a name the function declares global or nonlocal, whose uses leave it" % detail
                elif kind == "escape": why = detail   # it, or an object holding it, stored elsewhere, handed as a default, matched or called
                elif kind == "own": why = detail
                elif kind == "rmeth":
                    if detail not in _TYPE_READS.get(ctype, ()):
                        why = (_CT_UNTYPED % ("a subscript load" if detail == "[]" else ".%s()" % detail)
                               if ctype is None and (detail == "[]" or detail in _READ_METHODS) else _CT_SUB if detail == "[]" else _CT_TYPE % detail)
                elif kind == "operand": why = _CT_ITEM % detail
                elif kind in ("read", "call"): pass   # a value consumed without a change (_flow's "read": a test, a comprehension's
                # condition, an identity comparison, an operand whose other operands are constants, an f-string's field, a statement's
                # value, a return or a yield, a lambda's body) or handed as an argument to a call other than setattr, delattr or a method
                # spelled on a class (the call limit). For the container's own name every such read has refused above but a read method's
                # receiver or a subscript load's base, through the _own_use event recorded first at the same place; what passes here is the
                # container or an item of it handed to such a call, or an item of it, or a name bound to one, read
                elif fresh: pass   # a use of a new object around it, not of it
                elif kind == "aug": why = _CT_AUG % y   # an augmented assignment to a name bound to it or to an item of it
                elif kind == "tcall":   # a method spelled on a value handed it as its first argument: a class's runs on it; any other call
                    if self._class_callee(node.func.value, ctx):   # (a module's function, a class the census does not resolve) is the call limit
                        why = ((_CT_CLASS if node.args[0] is n else _CT_ITEM_CLASS) % detail if y == x and not fr
                               else _CT_THROUGH % (y, _CT_CLASS % detail))
                elif recv is not None:   # an item of it, or a name bound to one or to a new object holding one: its type's closed read set
                    if kind == "attr": got = _CT_ITEM_ATTR % detail
                    else:
                        if types is None: types = self._item_types(x, v, qs, events, binds, parents)
                        t = _settled(_value_type(recv, types))
                        what = "a subscript load" if detail == "[]" else ".%s()" % detail
                        got = (None if t is not None and detail in _TYPE_READS.get(t[0], ()) else
                               _CT_ITEM_UNKNOWN % what if t is None else _CT_ITEM_USE % (what, t[0]))
                    if got is not None: why = got if y == x and not fr else _CT_THROUGH % (y, got)
                elif y != x or fr:   # through a name bound to it or to an item of it: any use changes() counts (a name bound to it
                    # whole is refused where its own occurrence binds it)
                    if changes(e): why = "changed through %s, a name the function binds to it or to an item of it" % y
                elif kind == "store":
                    tgt = parents.get(id(node))
                    if node.value is not n: why = "changed through an item of it or an expression holding it"
                    elif not isinstance(node, ast.Subscript): why = "an attribute stored on it"
                    elif not (isinstance(node.ctx, ast.Store) and isinstance(tgt, ast.Assign) and tgt.targets == [node]):
                        why = "stored into other than by a plain assignment of its own"
                    elif not (type(getattr(node, "slice", None)) is ast.Constant and type(node.slice.value) in (str, int)):
                        why = "stored into by a key that is no constant"
                elif kind == "grow":
                    if len(node.args) != 1 or isinstance(node.args[0], ast.Starred) or node.keywords: why = "appended or extended by other than one plain argument"
                elif kind == "attr": why = "an attribute of it read other than as a method's callee (%s)" % detail   # on it, or a changer
                elif kind == "handed": why = "changed by a call handed it as the object to change (%s)" % detail
                # its own name's method call or read method's or subscript load's step: the fourth form's rmeth event decides it
                if why is not None: out[x] = _CONTAINER % why; break
        return out

    def _reaches_frame(self, fn):
        """The form by which the function `fn` reaches its own frame's local mapping in its own body, or runs code in it (through which
        code may change a container it binds on every CPython version), or None: one of the seven bare names in _FRAME_NAMES (locals,
        vars, exec, eval, _getframe, currentframe, getargvalues), one of the four attributes in _FRAME_ATTRS (_getframe, currentframe,
        getargvalues, f_locals) spelled as an attribute on any receiver, or a name that a statement of the MODULE's or of `fn`'s OWN body,
        outside every def, class or lambda statement it nests (header and body alike), binds to one of those frame primitives, its
        bound value the primitive's own bare name or attribute (a plain or annotated assignment, a walrus, an unpacking of a list or
        tuple literal into a target list of AS MANY elements, each plain name there bound to the value at its place, beside a starred
        or nested target too, or a `from ... import` of one of the seven names), and any name such a statement binds to a name so
        bound (a chained alias), resolved among those statements (_frame_alias_names over _module_level_stmts, seeded with the module
        aliases for `fn`'s own statements), anywhere in the function's own subtree. A name `fn` binds to a primitive by an assignment in
        its OWN body carries the primitive's own spelling there, so this walk sees it whether or not it is resolved; the resolution catches
        the module aliases, whose binding
        stands outside `fn`, and `fn`'s own `from ... import`, whose spelling sits in the alias node. The check is syntactic (the spelling,
        not a call), so a name merely spelled like a primitive is read too, on the safe side. One check at 0 live (no live route function
        reaches its frame): every container the function binds refuses (_containers, _FRAME_CONTAINER, whose reason names the form this
        returns, the spelling found, and does not say a frame was reached). The census reads a page function's
        locals as its text binds them; a change to them at run time through a frame object, exec or eval reached in any OTHER spelling is
        the stated precondition (the realm precondition's shape), outside what it reads, each road passing silently; among them: locals
        or vars reached as an ATTRIBUTE on a receiver (`sys.modules["builtins"].locals()`, `x.vars`), and exec or eval reached as an
        attribute (`builtins.exec`), since none of locals, vars, exec, eval is in _FRAME_ATTRS (its witness fratr is `locals` reached as
        an attribute, frxr exec so reached, frev eval); f_locals as a bare name, since f_locals is in _FRAME_ATTRS alone, not _FRAME_NAMES
        (bfl2); one of the four attributes named by a string, since only an attribute node is matched (fgs2,
        `getattr(inspect.stack()[0].frame, "f_locals")`); and any binding of a name to a primitive that _frame_alias_names does not
        read: a plain name among the targets of an unpacking whose targets are not as many as its values (fsst) and a name a nested
        target binds (fsnt), each of which the unpacking arm skips, an alias whose bound value is any other expression (tx4 an
        if-expression, txc a call's return), and a binding in the header or the body of a def, class or lambda statement, which
        _own_stmts and _module_level_stmts skip whole (tx2 a walrus in a module-level def's default; nstb a `from ... import` a def nested
        in `fn` makes, whose imported spelling sits in the alias node and whose alias name ast.walk does not match; tx3 an assignment
        inside a module-level def's body; frcl an assignment in a module-level class's body, read as the class's attribute; flam a
        walrus in a module-level lambda's default); a binding a nested scope makes by an ASSIGNMENT carries the primitive's spelling
        in `fn`'s subtree and refuses (nsta). Code the
        function runs that the census does not read (a helper it calls as a statement, a method on self, a context manager it enters),
        reaching the CALLER's frame, is the stated limit too: the census reads no such code's body for its frame reach, as the call limit
        reads none for what a callee does with a container it is handed."""
        if self.frame_aliases is None: self.frame_aliases = self._frame_alias_names(_module_level_stmts(self.tree))
        aliases = self._frame_alias_names(_own_stmts(fn), seed=self.frame_aliases)
        for n in ast.walk(fn):
            if isinstance(n, ast.Name) and (n.id in _FRAME_NAMES or n.id in aliases): return ast.unparse(n)[:40]
            if isinstance(n, ast.Attribute) and n.attr in _FRAME_ATTRS: return ast.unparse(n)[:40]
        return None

    def _item_types(self, x, v, qs, events, binds, parents):
        """name -> its type (_meet's pair, _value_type), for the container `x` bound by the one value `v` (a literal, or a call; `qs`
        whether a call of parse_qs, whose documented return is a dict of lists of str) and for every name its walk bound to it, to an item
        of it or to a new object holding one (binds, with the node of each binding): the container's the literal's type, or a dict of
        lists of str for parse_qs, or none known for any other call, its items met with every value a constant-key subscript store puts in
        it and every value an append puts in or an extend's argument holds; each other name's the meet of what each of its bindings gives
        it (_bind_type), read again whenever a name its bindings read moves, until none does. Types only fall from _UNSET toward not
        known, and every name's bindings reach the container's own fixed type, so the reading ends; were a type still moving after four
        readings per binding and sixteen more, every name would be read as not known (the safe side). Read once per container, at the
        first item use its verdict reaches."""
        tx = None
        if isinstance(v, (ast.List, ast.Dict, ast.Set, ast.Tuple)): tx = _value_type(v, {})
        elif qs: tx = ("dict", ("list", ("str", None)))
        if tx is not None:
            held = tx[1]
            for e in events:
                _l, _c, y, fr, n, _s, kind, node, _d, fresh, nested, inside = e
                if fresh or nested or inside or y != x or fr: continue
                if kind == "store" and isinstance(node, ast.Subscript) and node.value is n:
                    tgt = parents.get(id(node))
                    held = _meet(held, _value_type(tgt.value, {}) if isinstance(tgt, ast.Assign) else None)
                elif kind == "grow":
                    arg = node.args[0] if node.args and not node.keywords else None
                    got = None if arg is None or isinstance(arg, ast.Starred) else _value_type(arg, {})
                    if node.func.attr == "append": held = _meet(held, got)
                    else: held = _meet(held, got[1] if got is not None and got is not _UNSET and got[0] in ("list", "tuple", "set") else None)
            tx = (tx[0], held)
        types, by, uses = {x: tx}, {}, {}
        for z, p in binds:
            if z == x: continue
            by.setdefault(z, []).append(p); types[z] = _UNSET
            src = p.iter if isinstance(p, (ast.For, ast.AsyncFor, ast.comprehension)) else p.context_expr if isinstance(p, ast.withitem) else p.value
            for m in ast.walk(src):
                if type(m) is ast.Name: uses.setdefault(m.id, set()).add(z)   # z's type reads m's
        todo, budget = sorted(by), 4 * len(binds) + 16
        while todo and budget:   # each name read again only when a name its bindings read moves; types only fall from _UNSET
            z = todo.pop(); budget -= 1
            t = _UNSET
            for p in by[z]: t = _meet(t, _bind_type(p, types))
            if t != types[z]: types[z] = t; todo += sorted(uses.get(z, set()) - set(todo))
        if todo:   # a type still moving when the budget ends is read as not known
            for z in by: types[z] = None
        return {k: _settled(t) for k, t in types.items()}

    def _parse_qs_call(self, v, ctx):
        """Whether the value `v`, read in ctx, is a call of parse_qs: a top-level `from urllib.parse import parse_qs`, the name bound
        once (_sole) and no function scope of ctx binding it (_scoped). Its return is a dict of lists of str, the one value-slot call
        whose type the container proof knows (_containers: a name bound whole to one is a container outright, typed a dict)."""
        return (isinstance(v, ast.Call) and isinstance(v.func, ast.Name) and v.func.id in self.parse_qs
                and self._scoped(v.func.id, ctx, callee=True) is None and self._sole(v.func.id))

    def _class_callee(self, e, ctx):
        """Whether `e`, the value a called method is spelled on (`list` in `list.append(x, v)`), names a class by binding, so the method
        runs on the call's first argument (layer iv, _containers: a container or an item of it handed so refuses, _CT_CLASS): a builtin
        class (a builtin no binding of the file or the function shadows: _builtin, _scoped), a class of collections that a top-level `from
        collections import` binds the name to, the name bound once (_sole), or an attribute naming one on a name a top-level `import
        collections` binds once. Any other value (a class of the file, a class another import names, a module, a call's return) is not
        read as a class: a call of a method spelled on it, handed the container or an item of it, is under the call limit."""
        if type(e) is ast.Name:
            if self._scoped(e.id, ctx) is not None: return False
            if self._builtin(e.id): return isinstance(getattr(builtins, e.id, None), type)
            src = self.from_collections.get(e.id)
            return src is not None and self._sole(e.id) and isinstance(getattr(collections, src, None), type)
        if type(e) is ast.Attribute and type(e.value) is ast.Name:
            m = e.value.id
            return (self.import_mods.get(m) == "collections" and self._sole(m) and self._scoped(m, ctx) is None
                    and isinstance(getattr(collections, e.attr, None), type))
        return False

    def _container_step(self, uses):
        """_containers' expansion of one (name, levels, inside) its walk pops, which it calls once for each: the walk keeps one
        visited map per container (`low`, the fewest levels of new objects each name bound to it was read at, standing inside it or
        not, so a name is read again only at fewer standing the same way), and the step, given the popped name's uses (the Name nodes
        and the scopes around them), hands them back to
        read, in their order (freeze ruling 2 of the eleventh round: its count pin reads this step from outside the script)."""
        return list(uses)

    @staticmethod
    def _frame_alias_names(nodes, seed=()):
        """The names a plain or annotated assignment, a walrus, an unpacking of a list or tuple literal into a list or tuple target of
        as many elements (each plain name there, beside a starred or nested target too, bound to the value at its place), or a `from
        ... import` among `nodes` (the nodes of one scope's own body, statements and expressions alike, every def,
        class and lambda statement excluded, header and body: _own_stmts) binds to a frame primitive, its bound value the primitive itself
        (`_L = locals`, `_gf = sys._getframe`, `_LT, _z = locals, 1`, `from inspect import currentframe as _cf`), and every name bound in
        turn to one of those (a chained alias `_L2 = _L1`), resolved to a fixpoint among those statements. A primitive is a bare name in
        _FRAME_NAMES, an attribute in _FRAME_ATTRS, or the imported name of a `from ... import` in _FRAME_NAMES (whose spelling sits in the
        alias node, so the reader's subtree does not hold it). `seed` names that already alias a primitive (the module aliases, when this
        reads a function's own body). Layer iv, _Served._reaches_frame: a name so bound hands out a frame's locals mapping. Any other
        binding is not reached, the stated precondition and not a refusal: among them a binding in the header or the body of a def,
        class or lambda statement (tx2, nstb, tx3, frcl, flam), a name a nested target binds and a plain name among the targets of an
        unpacking whose targets are not as many as its values, or of anything but a list or tuple literal (fsst, fsnt), and an alias
        whose bound value is any other expression, an if-expression or a call (tx4, txc). The fixpoint is a worklist with
        one visited set (`out`) that expands each alias name once, in _frame_alias_step (freeze ruling 2 of the eleventh round: its count
        pin reads that step from outside the script; without the visited set a cycle of aliases loops)."""
        prim, edges = set(seed), []   # names bound directly to a primitive; (target, source-name) edges, a chained or unpacked name alias

        def take(name, val):
            if isinstance(val, ast.Name):
                if val.id in _FRAME_NAMES: prim.add(name)
                else: edges.append((name, val.id))
            elif isinstance(val, ast.Attribute) and val.attr in _FRAME_ATTRS:
                prim.add(name)
        for n in nodes:
            if isinstance(n, ast.ImportFrom):
                prim.update(a.asname or a.name for a in n.names if a.name in _FRAME_NAMES)
            elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
                v = n.value
                if v is None: continue
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    if isinstance(t, ast.Name):
                        take(t.id, v)
                    elif isinstance(t, (ast.Tuple, ast.List)) and isinstance(v, (ast.Tuple, ast.List)) and len(t.elts) == len(v.elts):
                        for te, ve in zip(t.elts, v.elts):
                            if isinstance(te, ast.Name): take(te.id, ve)
        out, todo = set(prim), list(prim)
        while todo:
            s = todo.pop()
            for t in _Served._frame_alias_step(s, edges):
                if t not in out: out.add(t); todo.append(t)
        return out

    @staticmethod
    def _frame_alias_step(name, edges):
        """_frame_alias_names' expansion of one alias name it pops (freeze ruling 2's count pin, WALKS): the names a chained or
        unpacked alias binds to it (the edges (target, source-name) whose source is `name`), which alias it in turn. Called once per
        name the fixpoint reaches, with its own visited set (`out`); a mutant that drops the set loops on a cycle of aliases."""
        return [t for t, s in edges if s == name]

    def _defaults(self, call, fn, dctx, label, done):
        """Read the default value of each parameter of a followed function (a plain def statement, _def_shape: no decorator, so
        Python binds the call's arguments to its own parameters) that the call may omit, as the call's argument would be read, since
        the omitted parameter takes that value: a positional parameter the call's plain positional arguments do not reach (none past
        a starred argument) and no keyword names, and a keyword-only one no keyword names, each read once per route in the context
        of the scope its def statement runs in (dctx: the module's for a module function, the enclosing function's for one defined in
        it). A default that holds a lambda, reached through the parameter's value, is refused by name (_LAMBDA_VALUE: _holds_lambda),
        and so is any default the reader cannot read, as resolve refuses it."""
        a = fn.args
        pos = a.posonlyargs + a.args
        kw = {k.arg for k in call.keywords if k.arg}
        plain = next((i for i, x in enumerate(call.args) if isinstance(x, ast.Starred)), len(call.args))
        pairs = list(zip(pos[len(pos) - len(a.defaults):], a.defaults)) + [(x, v) for x, v in zip(a.kwonlyargs, a.kw_defaults) if v is not None]
        for x, v in pairs:
            i = pos.index(x) if x in pos else None
            if i is not None and i < plain or x.arg in kw and x not in a.posonlyargs: continue   # the call passes it
            if ("default", id(v)) in done: continue
            done.add(("default", id(v)))
            for d in self._resolve_step((v,)):   # the default's one value, read once per route (resolve's walk: _resolve_step)
                if type(d) in _LAMBDA_HOLDERS and _holds_lambda(d): self._unread(d, _LAMBDA_VALUE, dctx[4])   # a lambda through the parameter's value
                else: self.resolve(d, dctx, label, done)

    def _file_slot(self):
        """Whether `__file__` is this file's own path, which the import system binds: no statement of the file binds it, in any
        scope and by any form (_FILE_BOUND), the file writes no name of its module namespace through a computed name and may not
        rewrite it at run time, no function binds it under a `global` declaration and no module-level statement writes it
        (Result.rebinds), and the module holds no star import. The one predicate for both of its reads: _path's `Path(__file__)`
        and `open(__file__)`, a file read that is this file only here, and the bare name as a value slot (resolve's Name arm, and
        _root_name's root for an attribute's base); in any other file each is refused."""
        return not (self.file_bound or self.computed or self.star or "__file__" in self.rebound)

    def _path(self, e, ctx=None, local=None, depth=0):
        """(the repository-relative path a pathlib expression spells, or None; why the census refuses it, or None): `ROOT / "ui" /
        "x.css"` through the module's constants (and, given the function's locals, a local's one binding), with Path(__file__) (or
        open(__file__)) as this file and .parent as its directory, each accepted only as proven by binding (layer v of the eleventh round's rulings,
        choice 14), `ctx` the context the read stands in (both callers hand it: resolve's local-slot arm with the function's locals,
        and its Call arm): the proof fails, and the read refuses by name, _PATH_UNPROVEN with the clause naming the conjunct that fails,
        where
        - a callee Path or open, or a name the path reads as a module constant, is a name a function scope around the read binds
          (_scoped: a local, a parameter, a comprehension's target, a lambda's parameter, a function-level import among them);
        - Path is not bound by one top-level `from pathlib import Path`, its name's one module-level binding, never rebound (_sole;
          a relative `from .pathlib import Path` is an import from the file's own package, a run-time form, where _sole holds for no
          name, so the import's level needs no test of its own);
        - open is not the builtin (_builtin: bound or rebound in the file, or a file that may rewrite the builtins);
        - Path or open is handed other than one positional argument, or a keyword (a second positional argument, pathlib's later
          absolute segment among them, replaces the first; an opener keyword opens what it likes);
        - the argument is a relative path spelled as a string constant, which Python resolves from the working directory, a
          directory no binding fixes;
        - a module constant the path reads is one the file writes at run time (a memo: rebound under a global declaration, or changed
          through its item or its attribute, _Served.memos and cmemos, as resolve reads them).
        A local is followed only where it is a plain local of the page function bound once (its forms exactly one value form, one
        value: never a parameter the body also assigns, whose incoming value the read may take), and only at the read itself, as
        before; a name inside a local's value, or inside the path past its first step, that a function scope binds refuses where it
        is a module constant's name the head would have read by spelling, and is None otherwise. A module constant's value is read
        in the module's own scope. None with no reason where the census cannot read the expression at all, and for Path(__file__)
        or open(__file__) wherever `__file__` may not be this file's own path (_file_slot: in a file where a statement binds it, in
        any scope and by any form, _FILE_BOUND, one that writes a name of its module namespace through a computed name or may
        rewrite it at run time, one where a function binds it under a `global` declaration or a module-level statement writes it,
        and a module that holds a star import), decided before the callee's proof, so a file read through it is a file the walk
        does not scan, as the tenth round's R1.2 has it."""
        if depth > 32: return None, None   # a constant bound through itself (`X = X.parent`) is not a path the census reads
        if isinstance(e, ast.Name):
            v = self._scoped(e.id, ctx) if ctx is not None else None
            if v is not None:   # a function scope around the read binds it: followed only as a plain local bound once, at the read
                oc = self._value_ctx(e.id, ctx)   # its one value read where the scope that binds it evaluates it
                if local is not None and ctx[5].get(e.id) == ["value"] and len(oc[1].get(e.id, ())) == 1:
                    return self._path(oc[1][e.id][0], self.comp_at.get(id(oc[1][e.id][0]), oc), None, depth + 1)
                return (None, _PATH_UNPROVEN % ("a function scope around the read binds %s" % e.id)) if e.id in self.consts else (None, None)
            if e.id not in self.consts: return None, None
            if e.id in self.memos or e.id in self.cmemos: return None, _PATH_UNPROVEN % ("%s, a module constant the file writes at run time" % e.id)
            return self._path(self.consts[e.id], None, None, depth + 1)   # its value is read in the module's scope
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Div) and isinstance(e.right, ast.Constant) and isinstance(e.right.value, str):
            left, why = self._path(e.left, ctx, None, depth + 1)
            return (None, why) if left is None else ((left + "/" if left else "") + e.right.value, None)
        if isinstance(e, ast.Attribute) and e.attr == "parent":
            base, why = self._path(e.value, ctx, None, depth + 1)
            return (None, why) if base is None else (os.path.dirname(base), None)
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "resolve": return self._path(e.func.value, ctx, None, depth + 1)
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id in ("Path", "open") and e.args:
            name, a = e.func.id, e.args[0]
            if isinstance(a, ast.Name) and a.id == "__file__" and not self._file_slot(): return None, None   # not this file's own path: first
            if ctx is not None and self._scoped(name, ctx) is not None:
                return None, _PATH_UNPROVEN % ("a function scope around the read binds %s" % name)
            if name == "Path" and not (self.pathlib_path and self._sole("Path")):
                return None, _PATH_UNPROVEN % "Path is not bound once, by a top-level from pathlib import Path, and never rebound"
            if name == "open" and not self._builtin("open"): return None, _PATH_UNPROVEN % "open is not the builtin"
            if len(e.args) != 1 or e.keywords: return None, _PATH_UNPROVEN % ("%s handed other than one positional argument and no keyword" % name)
            if isinstance(a, ast.Name) and a.id == "__file__": return self.rel, None   # this file's own path (_file_slot, above)
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                return (a.value, None) if os.path.isabs(a.value) else (None, _PATH_UNPROVEN % "a relative path, which Python resolves from the working directory")
            return self._path(a, ctx, None, depth + 1)
        return None, None

    def _allowed(self, where, whole):
        key = ("%s:%s" % (self.rel, where), ast.unparse(whole))
        if key not in SERVED_ALLOW: return False
        self.res.allow_hits.setdefault(key, set()).add((whole.lineno, whole.col_offset)); return True

    def _memo(self, name, whole, where):
        """A module container some code writes after binding it, read in a page: SERVED_ALLOW names the place, or a SERVED line."""
        if not self._allowed(where, whole):
            self.problems.append("SERVED %s:%d builds a served page from %s, a container the module writes at run time: name it in SERVED_ALLOW "
                                 "with the walked file its value comes from" % (self.rel, whole.lineno, ast.unparse(whole)[:60]))

    def _sole(self, name):
        """Whether the module binds the name exactly once at module level (_module_bound), never rebinds it (Result.rebinds: no
        function binds it under `global` and no statement at module level writes it), holds no star import, which may rebind
        any name, and writes no name of its module namespace through a computed name and may not rewrite it at run time
        (_namespace_flags), which may too: a top-level
        import, def or class statement is exempt as the name's one binding, never beside another (`from json import dumps as X` and
        then `X = ...`) or rebound (`global X` and then `X = ...` in a function); a write inside a function through a local of the
        same name (`quote = []`) does not count."""
        return not self.star and not self.computed and self.bound.get(name, 0) == 1 and name not in self.rebound

    def _builtin(self, name):
        """A builtin no module-level binding shadows and nothing rebinds (self.builtins, which holds no name the import system
        binds in every module, `__doc__` among them: _IMPORT_NAMES): a name the module binds (`format = lambda ...`, one
        bound in a try) is the module's, never the builtin, and so is one a function binds under `global` or a module-level
        statement writes (Result.rebinds), and every name in a module that holds a star import or in a file that may write its
        builtins or its own module namespace through a computed name (_namespace_flags: it names `__builtins__` as a name, imports
        the builtins module (`import builtins[.x]`, `from builtins[.x] import ...` at any level, `from X import builtins` or `from X
        import __builtins__`, any X at any level), writes a module that may be the builtins module (an attribute store or delete, a
        setattr or delattr, or its `__dict__` or vars() used any way but for a `.get` read, on a module module() reads as the
        builtins), or writes its own namespace through globals() or vars(), or through a store, setattr, delattr,
        `__dict__` or vars() on a module the file may be (`sys.modules[k]` or its `.get(k)`, or `__import__(k)` or
        `import_module(k)`, k no string constant, "__main__" or the file's own module name; a name that an assignment (as a name
        target, alone or in a chain), an annotated assignment or a walrus binds to one of these; or an if-expression or a boolean
        operation over one), globals, vars, setattr and delattr each by its own name, a name an import from builtins binds to it
        or as an attribute of a builtins receiver (`__builtins__`, a name `import builtins [as X]` or `from X import builtins [as
        Y]` binds, `sys.modules["builtins"]` or its `.get`, `__import__("builtins")` or `import_module("builtins")`), or read
        other than as a call) or may rewrite either at run time by one of
        _namespace_flags's run-time forms (an import from its own package, its own bare stem among them; an attribute named
        __globals__, __builtins__, f_globals, f_builtins or f_locals; a listed callable by its own name, by a name an import from
        builtins, importlib or sys binds to it, or as an attribute on a builtins receiver or, for all but compile, on any
        receiver; or one of those names, globals, vars, setattr, delattr or `__dict__` spelled as a string in a getattr-family,
        attrgetter/methodcaller or namespace-key position)."""
        return not self.star and not self.shadowed and name in self.builtins and name not in self.bound and name not in self.rebound

    def _module_why(self, name):
        """Why a module name the pass does not read is refused: a star import may rebind it; the file writes its module namespace
        through a computed name, or may rewrite it at run time by the form the reason names with its line (_namespace_flags), so no
        module name, a builtin among them, is read there (this branch runs first, so the reason for a computed-name or run-time file
        is that, not the builtin one below); it is a builtin in a file that may rewrite the
        builtins (it names `__builtins__` as a name, imports the builtins module or writes a module that may be the builtins module,
        in the forms _namespace_flags lists: an attribute store or delete, a setattr or delattr, or its `__dict__` or vars() used any
        way but for a `.get` read); its one
        module-level binding is an
        import, a def or a class statement inside a module-level block (if, try, with, for, while, match), not a top-level one; its
        one module-level binding is of any other form inside such a block's body (an assignment inside a try, say); its one
        module-level binding is a top-level annotated, unpacking or chained assignment (`X: str = ...`, `X, Y = ...`, `X = Y = ...`),
        which the count takes as a binding and _module_consts does not read; its module-level bindings are one top-level plain
        assignment and a top-level annotation alone beside it (`X: str` and `X = ...`, in either order: annotated), which the count
        takes as a second binding though an annotation alone binds nothing at run time; no module-level statement binds it and a
        function or class body binds it under a `global` declaration (_global_only), so it is bound only at run time; or it is bound
        other than by one assignment, a name an annotation alone names with no assignment among them."""
        if self.star: return _STAR
        if self.computed: return self.computed_why
        if self.shadowed and name in self.builtins and not self.bound.get(name): return _SHADOWED
        if self.bound.get(name, 0) == 1 and name in self.block: return _IN_BLOCK
        if self.bound.get(name, 0) == 1 and name in self.inblock: return _IN_BLOCK_BODY
        if self.bound.get(name, 0) == 1 and name in self.assigned: return _ASSIGN_FORM
        if name in self.annotated: return _ANNOTATED
        if self._global_only(name): return _GLOBAL_ONLY
        return "a module name bound other than by one assignment"

    def _global_only(self, name):
        """Whether no module-level statement binds the name, it is no builtin, and a function or class body binds it under a
        `global` declaration (Result.rebinds records the name; _global_binder finds the body), so it is bound only at run time."""
        return (not self.bound.get(name) and name not in self.builtins and name in self.rebound
                and _global_binder(self.res.global_decls.get(self.rel, ()), name) is not None)

    def _scoped(self, name, ctx, callee=False):
        """How the page function's own scope, or for a nested context an enclosing function's, decides a name it binds (row (d) of
        the seventh round): None when no function scope of the context binds it, or declares it `global` (the module's binding
        decides); otherwise ('local', None) for a local with values (a parameter the body also assigns among them), read from
        those values as a bare name or a receiver and refused as "a call" as a callee; ('exempt', why) for a parameter or an except
        name, a value slot, but refused as a callee when it shares a module function's name, and a route handler's first parameter
        the census does not classify (_Unclassified), refused as a callee as _UNCLASSIFIED; ('follow', None) for a callee that is a
        nested def, the name's one binding in the scope (followed only as a plain def: _def_shape, _def_uses), and ('unread',
        _FUNC_OBJECT) for that def as a bare name or a receiver, refused wherever it stands; and ('unread', why) for everything else: a comprehension's target, a function-level import, a nested class, a
        del, a match capture, a name a nonlocal declaration rebinds, any other store, and a name bound two ways (two different
        binding forms in one scope, or a nested def or class beside any other binding; every value form, an assignment, augmented
        or annotated, a loop, with or unpacking target and a walrus, is the one form "value", and a parameter the body also binds
        by one is one local). Before all of these, a container of the scope that the container proof refuses (layer iv of the eleventh round's rulings:
        _Container, _containers) is ('unread', its reason), wherever it is read: a bare name, a receiver's base, a container, an
        attribute's root or a callee."""
        forms = ctx[5].get(name)
        if not forms or "global" in forms: return None
        if isinstance(forms, _Container): return "unread", forms.why   # layer iv: a container the proof refuses (_containers)
        if callee and isinstance(forms, _Unclassified): return "unread", _UNCLASSIFIED   # a route handler's first parameter the census does not classify (_ctx)
        kinds = set(forms)
        if "nonlocal" in kinds: return "unread", "a name a nonlocal declaration rebinds"
        if "value" in kinds and kinds <= {"value", "param"}: return ("unread", "a call") if callee else ("local", None)
        if kinds in ({"param"}, {"except"}):
            if callee and name in self.defs:
                return "unread", "a parameter sharing a module function's name" if "param" in kinds else "an except name sharing a module function's name"
            return "exempt", "a parameter or a name the body binds"
        if forms == ["def"]: return ("follow", None) if callee else ("unread", _FUNC_OBJECT)
        if len(kinds) > 1 or len(forms) > 1 and kinds & {"def", "class"}: return "unread", "a name the function binds two ways"
        return "unread", {"comp": "a name a comprehension binds", "import": "a name the function binds by an import",
                          "class": "a name the function binds by a class statement", "del": "a name the function deletes"}.get(
                              forms[0], "a name the function binds another way")

    def _base(self, e, ctx):
        """What a receiver or a container derives from: ('exempt', why) for a base whose own text the pass does not read (a top-level
        import that is the name's one module-level binding, one of the seven builtins a page may name (_PAGE_BUILTINS: str, int,
        dict, max, float, getattr and chr) that no module-level binding shadows, any other builtin being refused by name as a bare
        name, a receiver's base or a callee (_BUILTIN_OTHER; a call of super() is refused with its own reason:
        its methods are a base class's; so is a call of str with more than one positional argument, a starred argument or a
        keyword other than object, any of which may be an encoding or an errors argument that decodes its first: _STR_DECODE;
        so is a call of max handed one iterable or a starred argument, which returns an element its argument holds: _MAX_ONE;
        and a name the import system binds in every module, `__doc__` among them, is no builtin,
        refused by name as a receiver's base or a callee where the file does not bind it: _IMPORT_WHY), each with nothing rebinding
        the name and no star import in the module: _sole and _builtin; a parameter or a name the body binds from one, a BoolOp over
        those; a call of one of those, or of a method on one, whose arguments receiver reads as text: _chain_args), ('readable',
        why) for one resolve reads, ('unread', why) otherwise, a call the reader does not resolve among them. A name the page
        function's scope binds is decided by that scope (_scoped) before the module's binding, as a bare name and as a callee;
        before that, `__file__` in a file where a statement binds it is unread (_FILE_BOUND), as a bare name and as a callee, and
        so is a join, format, format_map or replace called on the name str, bytes or bytearray (_UNBOUND, _unbound_text_call)."""
        params, local, cls, nested, where, scope = ctx
        if isinstance(e, (ast.Constant, ast.JoinedStr, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.BinOp, ast.IfExp)): return "readable", "an expression"
        if isinstance(e, ast.Name):
            if e.id == "__file__" and self.file_bound: return "unread", _FILE_BOUND   # before any binding is read, as resolve decides it
            v = self._scoped(e.id, ctx)
            if v is not None: return ("readable", "a name") if v[0] == "local" else v
            if e.id in self.consts: return "readable", "a name"
            if e.id in params: return "exempt", "a parameter or a name the body binds"
            if e.id in self.imports and self._sole(e.id): return "exempt", "an import"
            if self._builtin(e.id): return ("exempt", "a builtin") if e.id in _PAGE_BUILTINS else ("unread", _BUILTIN_OTHER)   # one of the seven
            if e.id in _IMPORT_NAMES and not self.bound.get(e.id): return "unread", _IMPORT_WHY   # the module's own docstring, name, ...: no builtin
            if (e.id in self.funcs or e.id in self.methods) and self._sole(e.id): return "unread", _FUNC_OBJECT
            return "unread", self._module_why(e.id)
        if isinstance(e, (ast.Attribute, ast.Subscript)): return self._base(e.value, ctx)
        if isinstance(e, ast.Call):
            f = e.func
            if _unbound_text_call(e): return "unread", _UNBOUND   # `str.join("", [...])` as a receiver's or a container's base
            if isinstance(f, ast.Name):
                if f.id == "__file__" and self.file_bound: return "unread", _FILE_BOUND
                v = self._scoped(f.id, ctx, callee=True)
                if v is not None: return ("unread", "a function's return") if v[0] == "follow" else v
                if f.id in self.funcs and self._sole(f.id): return "unread", "a function's return"
                if f.id in self.imports and self._sole(f.id): return "exempt", "an import"
                if f.id == "super" and self._builtin(f.id): return "unread", _SUPER   # its methods are a base class's, page text of their own
                if f.id == "str" and self._builtin(f.id) and (len(e.args) > 1 or any(isinstance(a, ast.Starred) for a in e.args)
                                                              or any(k.arg != "object" for k in e.keywords)):
                    return "unread", _STR_DECODE   # it may decode: a second positional argument, a starred one, a keyword but object
                if f.id == "max" and self._builtin(f.id) and (len(e.args) == 1 or any(isinstance(a, ast.Starred) for a in e.args)):
                    return "unread", _MAX_ONE   # an element its one iterable, or a starred argument, holds: the 16:33Z ruling, T8
                if self._builtin(f.id): return ("exempt", "a builtin") if f.id in _PAGE_BUILTINS else ("unread", _BUILTIN_OTHER)   # one of the seven
                if f.id in _IMPORT_NAMES and not self.bound.get(f.id): return "unread", _IMPORT_WHY
                if f.id in params: return "exempt", "a parameter or a name the body binds"
                if (self.star or self.computed or self.shadowed and f.id in self.builtins and not self.bound.get(f.id)
                        or f.id in self.bound and f.id in self.block and self.bound[f.id] == 1): return "unread", self._module_why(f.id)
                return "unread", "a call"
            if isinstance(f, ast.Attribute):
                if self._self_method(f, ctx): return "unread", "a method's return"
                return self._base(f.value, ctx)
            return "unread", "a call"
        if isinstance(e, ast.BoolOp):
            kinds = [self._base(v, ctx)[0] for v in e.values]
            return ("exempt", "a BoolOp looked through") if all(k == "exempt" for k in kinds) else ("unread", "a BoolOp")
        return "unread", type(e).__name__

    def _self_method(self, f, ctx):
        """Whether the callee `f`, an attribute, is a method called on the calling method's own first parameter (_own_self) that the
        route class's method resolution order resolves to a def statement of a class of the file (_definer): a call the follow arm
        refuses by name, however that def reads (_method_call, _METHOD_SUBCLASS at the last), whose return _base and _attr_root take for
        "a method's return"."""
        return self._own_self(f.value, ctx) and self._definer(ctx[2], f.attr) is not None

    @staticmethod
    def _own_self(r, ctx):
        """Whether the receiver `r`, read in ctx, is the calling method's own first parameter: a name whose binding is the first
        parameter of a method defined directly in a class body whose def carries no decorator, however it is spelled (_SelfParam; a
        route handler's in a file that binds staticmethod or classmethod is not classified, _Unclassified), never rebound in that
        scope (its forms exactly ["param"]); a closure or a lambda inside the method that binds no name so spelled reads the same
        binding. Since the eleventh round's follows every call it answers True for is refused (_method_call's closing refusal, _METHOD_SUBCLASS),
        so of its two tests the mark decides the outcome (a parameter it answers False for, a helper's among them, is refused by the
        refuse arm only for a route class's method or a name the file stores, and otherwise is a parameter's call, the call limit)
        and the forms test decides the reason alone: a first parameter the method rebinds is refused by the refuse arm as self
        through a binding (_recv_roots' "self" root), where it would otherwise be refused by the closing refusal."""
        forms = ctx[5].get(r.id) if isinstance(r, ast.Name) else None
        return isinstance(forms, _SelfParam) and list(forms) == ["param"]

    def _method_call(self, f, ctx):
        """Decision 2 at a method call in a page position whose callee is the attribute `f`, read in ctx (resolve's Call arm, before
        the file-read and text-call arms, and each method call on a receiver's or a container's path: receiver, _path_calls):
        ("refuse", why) or None. A method called on the calling method's own first parameter (_own_self) is refused by name however
        its def reads, since a subclass another file defines may override it with code the census does not read (choice 4 of the
        eleventh round's rulings: _METHOD_SUBCLASS); before that, with the reason that names what the census read, where the route class's method
        resolution order resolves it to no def statement of a class of the file (an imported base, a binding other than one def
        statement, no class, or a route class that is not its name's one top-level class statement: _definer, _SELF_METHOD), where
        that def is no plain def (an async def, a decorator, a yield in its own body: _def_shape), where a class statement of the
        file overrides it or may (_file_override: _METHOD_OVERRIDE, _METHOD_UNPLACED), and where the file may replace it at run time
        (_replaced: _REPLACED, and _REPLACED_OPEN where its setter read fails closed). The refusal that ends the arm dominates
        every reason before it, each of which names the shape the
        census found, and the follow proof's name conjuncts (_def_uses: the name read other than as a call's callee, or spelled by a
        string constant), which this arm does not read. For a call of any name on a receiver whose root by binding is a route
        handler's first parameter the census does not classify (_Unclassified: _UNCLASSIFIED); for a call of a route class's method
        (self.route_methods: any name a route class's body or a file base's binds, in any form) on self through anything else (an
        alias, a loop, comprehension or with target, a container, an if-expression, a BoolOp, a walrus, or a followed function's
        return: _recv_roots), on any other parameter (a followed function's returned parameter among them), or
        on a name spelled self that is not the calling method's own first parameter (_METHOD_CALL); for a call of any other name on
        self through anything else (_SELF_METHOD); and for a call of any other name on such a parameter or such a name spelled self
        where the file stores, deletes or names to a setter an attribute of that name (_stores: _METHOD_STORED), which may bind it on
        a route class or its instance. None for any other call, a method called on a parameter whose name no route class binds and
        the file stores nowhere among them (the call limit: its arguments read as text, not the text it computes)."""
        r = f.value
        if self._own_self(r, ctx):
            d = self._definer(ctx[2], f.attr)
            if d is None: return "refuse", _SELF_METHOD
            why = self._def_shape(self.methods[d][f.attr]) or self._file_override(ctx[2], f.attr)
            if why is not None: return "refuse", why
            why = self._replaced(ctx[2], f.attr)
            if why is not None: return "refuse", why
            return "refuse", _METHOD_SUBCLASS
        roots = self._recv_roots(r, ctx)
        if "unclassified" in roots: return "refuse", _UNCLASSIFIED
        if "self" in roots: return "refuse", _METHOD_CALL if f.attr in self.route_methods else _SELF_METHOD
        if "param" in roots or isinstance(r, ast.Name) and r.id == "self":
            if f.attr in self.route_methods: return "refuse", _METHOD_CALL
            if f.attr in self._stores(): return "refuse", _METHOD_STORED
        return None

    def _recv_roots(self, e, ctx):
        """The roots the receiver `e` of a method call, read in ctx, reaches by binding (decision 2's walk): "self" for self by binding
        (a method's first parameter however spelled, _SelfParam), "unclassified" for a route handler's first parameter the census
        does not classify (_Unclassified), "param" for any other parameter and "except" for an except name (_root_slot). The walk
        goes through a local's values (a loop, comprehension or with target's source, an unpacking's value and a walrus's among
        them: _binding, each read in the scope that binds the local), a list, tuple, set or dict literal's elements, keys and values, a
        subscript's container, an if-expression's branches, a BoolOp's operands and a walrus's or a starred value, and through a call of
        a name the census follows as a plain def (a module function or a function defined in the page function: _followed, resolve's two
        follows) to the returns resolve reads for it, in the callee's own scope, where a parameter is a "param" root and self a closure
        reads is "self" (`r = _ident(self)` then `r.get(k)`, with `_ident` returning its parameter, reaches a parameter, as `q.get(k)` on
        the parameter does); never through an attribute or any other call, whose value is no binding of a name the census reads, a module
        constant, whose value reads no function scope, or a class (receiver decides a receiver on one). Iterative: an explicit worklist
        and one visited set per query, keyed on the binding's scope and the name, and on the followed def, so each name and each def
        expands once, in _recv_step, and the walk is linear in the page's size; there is no depth bound."""
        roots, seen, todo = set(), set(), [(e, ctx)]
        while todo:
            x, c = todo.pop()
            if isinstance(x, (ast.Subscript, ast.NamedExpr, ast.Starred)): todo.append((x.value, c)); continue
            if isinstance(x, ast.IfExp): todo += [(x.orelse, c), (x.body, c)]; continue
            if isinstance(x, ast.BoolOp): todo.extend((v, c) for v in reversed(x.values)); continue
            if isinstance(x, (ast.List, ast.Tuple, ast.Set)): todo.extend((y, c) for y in reversed(x.elts)); continue
            if isinstance(x, ast.Dict): todo.extend((y, c) for y in reversed(x.keys + x.values) if y is not None); continue
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Name):   # a followed def: its returns, in its own scope
                got = self._followed(x.func, c)
                if got is not None and ("def", id(got[0])) not in seen:
                    seen.add(("def", id(got[0]))); todo += self._recv_step(self._returns(got[0]), got[1])
                continue
            if not isinstance(x, ast.Name): continue
            forms = c[5].get(x.id)
            if self._class_name(x, c): continue
            v = self._scoped(x.id, c)
            if v is not None and v[0] == "exempt": roots.add(self._root_slot(x.id, c)); continue
            if v is None or v[0] != "local": continue
            if "param" in forms: roots.add(self._root_slot(x.id, c))
            got = self._binding(x, c)
            if got is not None and (got[0], x.id) not in seen:
                seen.add((got[0], x.id)); todo += self._recv_step(got[1], got[2])
        return roots

    def _followed(self, f, ctx):
        """(the def statement a call of the name `f`, read in ctx, follows, the context resolve reads its returns in) where resolve's
        Call arm follows that call (layer ii): a function defined in the page function, the name's one binding there (_scoped's
        "follow"), or else a module function, the name's one module-level binding (_sole), in either case a plain def (_def_shape,
        _def_uses); None for any other callee. Each (def, context of its def statement) is given one context for the pass (rctx), so
        decision 2's walk (_recv_roots) reads a followed def's returns as resolve does and builds no context twice."""
        got = self._scoped(f.id, ctx, callee=True)
        if got is not None:
            fn = ctx[3].get(f.id) if got[0] == "follow" else None
            held = self.def_ctx.get(id(fn)) if fn is not None else None
            if held is None or self._def_shape(fn) or self._def_uses(fn, held[2]): return None
            key = (id(fn), id(held[1]))
            if key not in self.rctx: self.rctx[key] = (fn, self._ctx(fn, ctx[2], held[1], ctx[4] + "." + f.id), held[1])
            return self.rctx[key][:2]
        if f.id not in self.funcs or not self._sole(f.id): return None
        fn = self.funcs[f.id]
        if self._def_shape(fn) or self._def_uses(fn, None): return None
        if (id(fn), None) not in self.rctx: self.rctx[(id(fn), None)] = (fn, self._ctx(fn, None, None, f.id), None)
        return self.rctx[(id(fn), None)][:2]

    @staticmethod
    def _recv_step(vals, ctx):
        """_recv_roots's expansion of one name, which it calls once for each name it expands, given the values of the name's binding
        and the ctx they are read in (_binding): the values to read next."""
        return [(y, ctx) for y in reversed(vals)]

    def _top_class(self, node):
        """The name under which the census reads the class statement `node` as a class of the file: its name where node is the name's
        one top-level class statement (a statement of the module's own body, the class self.classes holds under that name, and the
        name's one module-level binding, never rebound: _sole); None for any other class statement (one nested in a function, a class
        body or a block, one a later statement rebinds, or a second class of that name), whose order and derivation the census does
        not read. The route class is keyed on its class statement through this (choice 1 of the eleventh round's rulings, R1.2: never on its name alone),
        in the follow arm (_definer) and in the refuse arm (_route_methods)."""
        return node.name if node is not None and self.classes.get(node.name) is node and self._sole(node.name) else None

    def _definer(self, cls, attr):
        """The class whose def statement a method `attr` called on self resolves to, where the route class is the class statement `cls`:
        the first class in its method resolution order (_mro, over the name _top_class reads) whose body binds the name, when that is
        a class of the file binding it by one def statement of its own body (self.methods) and by nothing else there; None when that
        class binds it any other way (an assignment, a lambda, a def inside a block, a second def, a global declaration among them),
        when the first class that may bind it is not a class of the file (an imported base, whose names the census does not read),
        when no class binds it, when the order cannot be read (_mro), and when the route class is no class _top_class reads (a class
        nested in a class or a block, one rebound, a second class of its name), whose order the census does not read. Read once per
        file for each class and name (self.definers)."""
        name = self._top_class(cls)
        if name is None: return None
        key = (name, attr)
        if key not in self.definers:
            got = None
            for kind, c in self._mro(name) or [("base", None)]:
                if kind != "file": break
                forms, declared = _binding_forms(self.classes[c], attr)
                if not forms: continue   # the class binds no such name (a global declaration alone binds none there)
                if forms == ["a def statement"] and declared is None and attr in self.methods.get(c, {}): got = c
                break
            self.definers[key] = got
        return self.definers[key]

    def _file_override(self, cls, attr):
        """Why the method `attr` that the route class `cls` (a class statement _top_class reads) resolves to a def of may run another
        class's code in its place, or None (R1.6 of the eleventh round's review): a class statement of the file, in any scope (every class statement of
        the tree, one a function, a class body, an if, a try or any other block holds among them), outside the route class's own
        method resolution order, that binds the name in its body in any form (_binding_forms), and either derives from the route
        class, directly or through classes _top_class reads (_METHOD_OVERRIDE: the server may instantiate that subclass, whose
        override Python runs in place of the def the order resolves the name to), or is one the census cannot place (_METHOD_UNPLACED):
        a class statement _top_class does not read, or one with a base on its ancestor chain that is none of those classes, no
        top-level import that is its name's one module-level binding (or an attribute of one) and no builtin (an alias of a class, an
        attribute of anything else, a call, a subscript, a starred base among them), whose derivation the census does not read. A
        class whose chain reaches imports and builtins alone derives from the route class only through another file, which the
        refusal that ends the follow arm answers (_METHOD_SUBCLASS); a class in the route class's own order stands after it there, so
        it is no override. The derivation is read from the classes' bases (_override_step), not the linearization, so it does not
        enter _mro. Iterative: an explicit worklist and one visited set per class statement, seeded with it, so each class expands
        once, in _override_step, and the walk is linear in the file's classes."""
        if self.class_nodes is None: self.class_nodes = [n for n in ast.walk(self.tree) if isinstance(n, ast.ClassDef)]
        name = self._top_class(cls)
        order = self.mros[name] if name in self.mros else self._mro(name)   # the order _definer read, once per file
        own = {id(self.classes[c]) for k, c in (order or ()) if k == "file"} | {id(cls)}
        for node in self.class_nodes:
            if id(node) in own or not _binding_forms(node, attr)[0]: continue
            if self._top_class(node) is None: return _METHOD_UNPLACED   # no top-level class statement the census places
            seen, todo = {node.name}, [node.name]
            while todo:
                for kind, b in self._override_step(todo.pop()):
                    if kind == "unplaced": return _METHOD_UNPLACED
                    if kind != "file": continue   # an import or a builtin: a class of another file
                    if self.classes[b] is cls: return _METHOD_OVERRIDE
                    if b not in seen: seen.add(b); todo.append(b)
        return None

    def _override_step(self, name):
        """_file_override's expansion of one class, which it calls once for each class it pops: the bases of the class a top-level
        class statement _top_class reads binds under `name`, in order, each ("file", its name) for a bare name of such a class,
        ("outside", its text) for a bare name a top-level import binds as the name's one module-level binding (_sole), an attribute
        whose root is such a name, or a builtin no binding shadows (_builtin), and ("unplaced", its text) for any other base."""
        out = []
        for b in self.classes[name].bases:
            root = b
            while isinstance(root, ast.Attribute): root = root.value
            if isinstance(b, ast.Name) and b.id in self.classes and self._top_class(self.classes[b.id]) is not None: out.append(("file", b.id))
            elif isinstance(root, ast.Name) and root.id in self.imports and self._sole(root.id): out.append(("outside", ast.unparse(b)))
            elif isinstance(b, ast.Name) and self._builtin(b.id): out.append(("outside", b.id))
            else: out.append(("unplaced", ast.unparse(b)))
        return out

    def _class_recv(self, e):
        """Whether the receiver of a `__setattr__` or `__delattr__` call is a class: `object`, `type`, a class a top-level class statement
        of the file binds, or a call of type(); so the call is the unbound three-argument form whose attribute name is its second
        argument, where the bound form on any other receiver (self, super()) names it in its first (_replaced)."""
        if isinstance(e, ast.Name): return e.id in ("object", "type") or e.id in self.classes
        return isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id == "type"

    def _stores(self):
        """The attribute names the file stores or deletes on any object (the target of an assignment, an augmented or annotated
        assignment, a for, with or comprehension target, or a del), or names by a string constant, or a join _const_text folds to
        one, as the second argument of a call of setattr or delattr (by that name or as an attribute so named) or of __setattr__ or
        __delattr__ called unbound (by that name, or as an attribute of a receiver _class_recv reads as a class), or as the first
        argument of __setattr__ or __delattr__ called as an attribute of any other receiver (the bound form, `self.__setattr__("name",
        f)`, `super().__setattr__(...)`: _setter_name). A setter whose name does not fold adds no name here (the refuse arm reads the
        set as it stands; _replaced's setter read fails closed on one: _setters_open). Read once per file, before any route is read
        (run), for _replaced and decision 2's refuse
        arm (_method_call, _METHOD_STORED; R1.4 of the eleventh round's review: a method bound onto a route class from outside its body, by a store on
        the class or a setattr, is one of these names)."""
        if self.stores is None:
            self.stores = set()
            for n in ast.walk(self.tree):
                if isinstance(n, ast.Attribute) and isinstance(n.ctx, (ast.Store, ast.Del)): self.stores.add(n.attr)
                elif isinstance(n, ast.Call) and (getattr(n.func, "id", None) or getattr(n.func, "attr", None)) in _SETTERS:
                    a = self._setter_name(n)[0]
                    if a is not None:
                        c = self._const_text(a)
                        if c is not None and type(c[0]) is str: self.stores.add(c[0])
        return self.stores

    def _setter_name(self, n):
        """(the argument of the setter call `n` that names the attribute it sets or deletes, or None where the call holds too few
        arguments; its position): a bound `x.__setattr__("name", f)` or `x.__delattr__("name")` on a receiver that is not a class
        (_class_recv) names the attribute in its first argument; every other setter (setattr, delattr, or the unbound
        `C.__setattr__(obj, "name", f)` on a class receiver) names it in its second. _stores and the setter read (_setters_open)."""
        idx = 0 if (isinstance(n.func, ast.Attribute) and n.func.attr in ("__setattr__", "__delattr__") and not self._class_recv(n.func.value)) else 1
        return (n.args[idx] if len(n.args) > idx else None), idx

    def _setters_open(self):
        """Whether the setter read fails closed for the file (choice 12 of the eleventh round's rulings: _replaced's fail-closed read, an unfoldable setter
        refuses): a call of setattr, delattr, `__setattr__` or `__delattr__` (by that name or as an attribute so named) whose argument
        naming the attribute (_setter_name) is missing, or is no string constant or constants _const_text folds to one (a name, a loop
        or comprehension target, a module constant, a parameter, a call's return, a starred argument among them), or stands after a
        starred argument, which may put any argument in its position; or the file reaches one of the four other than by such a call:
        its name, or an attribute so named, anywhere but as a call's callee (an alias, an argument), an import of one under another
        name, or a string constant, or constants _const_text folds, that spells one (Scan._setter_sites, the lookup key's setter read).
        A keyword is not read: the four take none, so a `**` mapping handed one is empty or raises, and no keyword moves a positional
        argument. A missing argument is unproven as one that does not fold is; the guard spells that out, and _const_text answers None
        for no node as well, so the guard decides nothing alone. Read once per file, at the first _replaced, which runs only for a
        method called on self that resolves to a def statement (0 live: the live tree makes no such call)."""
        if self.sopen is None:
            def unproven(call):
                a, idx = self._setter_name(call)
                if a is None or any(isinstance(x, ast.Starred) for x in call.args[:idx]): return True   # no argument there, or unplaced
                c = self._const_text(a)
                return c is None or type(c[0]) is not str
            calls, loose = Scan._setter_sites(self.tree)
            self.sopen = loose or any(unproven(call) for call, _chain in calls)
        return self.sopen

    def _replaced(self, cls, attr):
        """Why code of the file may replace at run time the method `attr` that the order of the route class `cls` (a class statement
        _top_class reads) resolves to a def of (_definer), or None, as far as one syntactic check reads it, one reason the follow arm
        refuses the call before its closing refusal (_method_call): _REPLACED where the file stores, deletes or names to a setter an
        attribute of that name (_stores), or a class of the file in cls's method resolution order binds __getattribute__, which runs
        on every lookup on self; else _REPLACED_OPEN where the file's setter read fails closed (_setters_open: a setter whose name
        the census does not fold may name the method)."""
        name = self._top_class(cls)
        order = self.mros[name] if name in self.mros else self._mro(name)   # the order _definer read, once per file
        if attr in self._stores() or any(k == "file" and _binding_forms(self.classes[c], "__getattribute__")[0] for k, c in order or ()):
            return _REPLACED
        return _REPLACED_OPEN if self._setters_open() else None

    def _class_bases(self, name):
        """The bases of the class a top-level class statement of the file binds under `name`, in order: ("file", its name) for a bare
        name a top-level class statement binds as the name's one module-level binding (_sole), a class of the file, and ("base", its
        text) for any other base (an import, an attribute, a call, a starred base), a class whose own bases the census does not read."""
        return [("file", b.id) if isinstance(b, ast.Name) and b.id in self.classes and self._sole(b.id) else ("base", ast.unparse(b))
                for b in self.classes[name].bases]

    def _mro(self, name):
        """The method resolution order of the class a top-level class statement of the file binds under `name`, as Python computes it
        (the C3 linearization) over its bases as _class_bases reads them, each other base a class of its own with no bases read; None
        when the name is no such class or the order cannot be computed (a base cycle, or bases C3 cannot order, which Python refuses
        at class creation). Iterative: an explicit worklist, each class's order computed once per file (self.mros), in _mro_step,
        which it calls once for each class it expands."""
        if name not in self.classes: return None
        todo, opened = [name], set()
        while todo:
            n = todo[-1]
            if n in self.mros: todo.pop(); continue
            need = [b for k, b in self._class_bases(n) if k == "file" and b not in self.mros]
            if need and n not in opened: opened.add(n); todo.extend(need); continue
            todo.pop(); opened.discard(n)
            self.mros[n] = None if need else self._mro_step(n)   # bases still unread on its second visit: a cycle
        return self.mros[name]

    def _mro_step(self, name):
        """_mro's expansion of one class, given its bases' orders (self.mros): its own order by C3's merge of those orders and the
        list of its bases, or None where a base's order is None or the merge finds no class to take next."""
        bases = self._class_bases(name)
        seqs = [(self.mros.get(b) if k == "file" else [(k, b)]) for k, b in bases] + [list(bases)]
        if any(s is None for s in seqs): return None
        out, at, tail = [("file", name)], [0] * len(seqs), {}   # tail: each class -> the lists that hold it past their head
        for s in seqs:
            for x in s[1:]: tail[x] = tail.get(x, 0) + 1
        while True:
            live = [i for i in range(len(seqs)) if at[i] < len(seqs[i])]
            if not live: return out
            head = next((seqs[i][at[i]] for i in live if not tail.get(seqs[i][at[i]])), None)
            if head is None: return None
            out.append(head)
            for i in live:
                if seqs[i][at[i]] == head:
                    at[i] += 1
                    if at[i] < len(seqs[i]): tail[seqs[i][at[i]]] -= 1

    def _route_methods(self, classes):
        """The method names decision 2's refuse arm keys on (the 21:39Z item 1; choices 1 and 2 of the eleventh round's rulings): every name the body of
        each route class binds, in any form outside its nested scopes (_body_names: a def statement, an assignment, a def inside a
        block of the body, an import among them; choice 2, a class's methods being its body's def statements, so a name bound there any
        other way refuses as a method, where the follow arm finds no def for it, _definer), read from the route class's class
        statement (choice 1: `classes` are class statements, never names), and every name the body of each class of the file it
        derives from binds (the file classes in its order, _mro, where _top_class reads the route class; for one it does not read, the
        file classes in the order of each base _top_class places); read once per file, so a module helper's context has them too."""
        out = set()
        for node in classes:
            name = self._top_class(node)
            if name is not None: scopes = [self.classes[c] for k, c in (self._mro(name) or [("file", name)]) if k == "file"]
            else:
                scopes = [node] + [self.classes[c] for b in node.bases if isinstance(b, ast.Name) and b.id in self.classes
                                   and self._top_class(self.classes[b.id]) is not None
                                   for k, c in (self._mro(b.id) or [("file", b.id)]) if k == "file"]
            for sc in scopes: out.update(_body_names(sc))
        return out

    def _carries_text(self, e, ctx):
        """Whether a subscript's container carries text the pass reads, so that a slice of it, or an index that is no constant,
        refuses (_SLICED): one _base reads as readable (a literal or another expression resolve reads, a module constant or a local,
        and an attribute, a subscript or a method call on one of those), or a BoolOp with such an operand, which _base takes as
        unread while receiver reads each operand. Any other container is not: a value slot passes whatever its index (a parameter,
        a name bound from one, an import, one of the seven builtins a page may call, or a call of one of those or of a method on
        one, its arguments read as text: _chain_args, save that a slice of such a call handed arguments, or an index that is no
        constant, refuses too, as the page expression or anywhere on a receiver's path: _chain_text, _sliced; and save where the
        method allowlist refuses a call on its path: _exempt_undrawn; _sub_operand, which reads this answer alone, keeps such a
        subscript under the call limit), and
        receiver refuses the rest whatever its index (a function's or a method's
        return, a class object, an attribute read on a class through its own name, refused as a class attribute, and an attribute
        read on self, on any other parameter or on an except name: _attr_root)."""
        if isinstance(e, ast.BoolOp): return any(self._carries_text(v, ctx) for v in e.values)
        return self._base(e, ctx)[0] == "readable"

    def _chain_text(self, e, ctx):
        """Whether a subscript's container `e` that is a base whose own text the pass does not read (_base: exempt) derives through a
        call handed arguments the pass reads as text (_chain_args: `str(X)`, `dict(a=X).get("a")`, `max(X, Y)`,
        `json.loads(json.dumps(X))`, `str.lower(X)`), so that a slice of it, or an index that is no constant, refuses (_SLICED) as
        over a container whose text the pass reads (_sliced: at resolve's Subscript arm, and at each subscript on the path of a
        receiver whose base is such a base, _path_subs): the pass reads those arguments whole and does not compute what the index
        selects of the text the call returns. A constant index still reads them (receiver), and a container
        whose calls are handed nothing, or none at all (a parameter, an import's bare name), passes whatever its index. The test that
        the container is such a base decides no outcome, only a reason (choice 5 of the eleventh round's rulings: a dominated
        conjunct argued): a container the pass reads refuses by _carries_text first, and receiver refuses any other whatever its
        index, with its own reason (a function's return, a call the reader does not resolve), which the test keeps; and at receiver's
        point for such a base every container on the path stands on that base, so is one."""
        return self._base(e, ctx)[0] == "exempt" and bool(self._chain_args(e))

    def _sliced(self, s, ctx):
        """Whether the subscript `s` is refused by name (_SLICED): its index a slice of any shape or no constant, over a container
        whose text the pass reads (_carries_text) or a base whose own text it does not read that derives through a call handed
        arguments it reads (_chain_text), since the pass reads that text whole and does not compute what the index selects. One
        rule at both places the pass reads through a subscript: resolve's Subscript arm, and receiver's point for a base whose own
        text the pass does not read, at each subscript on the path whose calls' arguments it reads there (_path_subs)."""
        return not isinstance(s.slice, ast.Constant) and (self._carries_text(s.value, ctx) or self._chain_text(s.value, ctx))

    def receiver(self, r, whole, ctx, label, done, read=False, call=False):
        """The receiver of a method call, or the container of a subscript or an attribute, `r` in the page expression `whole`: a
        name bound as a module constant or a local is read (a run-time memo is named in SERVED_ALLOW or refused); a BoolOp is looked
        through to each operand; one that stands on a class, through the class's own name or a name the census resolves to one or
        through a method call on, or a subscript of, a name whose value holds one (_class_root: `Handler.X`, `h.render()` after
        `h = Handler`, `_REG.get(k).X`), is refused by name (_CLASS_ATTR), since no class attribute is read
        as page text; then an attribute read is refused by the root its base reaches by binding (_attr_root: self, however it is
        spelled or aliased, as _SELF_ATTR, any other parameter as _PARAM_ATTR, an except name as _EXCEPT_ATTR, a class as
        _CLASS_ATTR, or a root the pass would read as a name's value with the reason the pass gives it), the attribute being
        `whole`'s own, on `r` itself, where `read` says `r` is the base of the attribute `whole` reads (resolve's Attribute arm,
        each operand of a BoolOp so), and otherwise each attribute read on `r`'s path (_path_attrs: `t.X.get(k)`, `t.X[0]` for a
        comprehension's target `t` over self; an attribute read off a local marks it a container the proof refuses first, xatr's check),
        so `q.get(k)` on a parameter passes and `q.X.get(k)` is refused, and where no attribute is read on the path, `r`
        whose root by binding is a class is refused as a class attribute (_value_class: a method called on a class reached as a
        value, `t.render()` in a loop over classes, `_REG["a"].render()`, or such a container); a base whose own text the pass does
        not read passes, and the arguments of every call it derives through are read as text (_chain_args: `dict(X).get(k)` reads
        X); anything else is a SERVED line by name unless SERVED_ALLOW names the place, a call the reader does not resolve among
        them. A name the page function's scope binds is decided by that scope (_scoped) before the module's binding. A subscript is
        read through resolve's Subscript arm, which refuses a slice or an index that is no constant over a container whose text
        the pass reads, or over a base whose own text it does not read that derives through a call handed arguments it reads
        (_SLICED, _sliced, _chain_text), before it hands the container here; at a base whose own text the pass does not read, the
        same rule applies to each subscript on `r`'s path, `r` among them, before the calls' arguments are read (_path_subs:
        `str(X)[::-1].removeprefix(p)`, `str(X)[k].split(s)[0]`), and a subscript on the path of any other value slot passes
        whatever its index, save where the method allowlist refuses a call on the path (below). A method call on `r`'s path, `r` itself among them (_path_calls: `h.m().get(k)` after `h = self`, `q.m()[0]` on a
        parameter), is read by decision 2 (_method_call) before the base: one it refuses is refused by name, a method called on
        self among them, whatever its def (the follow arm takes none), and any other passes to the base. Where `call` says `whole`
        is a method call resolve's last method arm hands here (the eleventh round's method allowlist), each point that would read the
        receiver's text as the page's (a local, a module constant that is no run-time memo, a base _base reads as readable) reads it
        only for a method whose return is drawn from that text, and refuses any other by name (_undrawn). At a base whose own text
        the pass does not read, whatever `call` says, each method call on the path whose receiver derives through a call handed
        arguments the pass reads (_chain_args: `str(X).lower()`, `dict(a=X).get("a").lower()`) or is the name of one of the seven
        builtins a page may name called unbound (`str.lower(X)`, whose argument is its receiver) is read only for such a method too,
        `whole` first where it is one, then each call on `r`'s path, outermost first, so `str(X).lower().removeprefix(p)` and
        `str(X).lower().split()[0]` refuse as `str(X).lower()` does (_exempt_undrawn; the reviewer's 16:33Z ruling, E2, with no
        exception by shape); any other base whose own text the pass does not read (an import's or a parameter's bare name) keeps
        the call limit, its calls' arguments read."""
        params, local, cls, nested, where, scope = ctx
        if isinstance(r, ast.BoolOp):
            for v in r.values: self.receiver(v, whole, ctx, label, done, read, call)
            return
        if self._class_root(r, ctx): return self._unread(whole, _CLASS_ATTR, where)   # on a class: never read as page text
        if read and self._attr_base(r, whole, ctx, where): return   # an operand of the attribute's base: refused by its root's binding
        if not read and self._value_class(r, ctx): return self._unread(whole, _CLASS_ATTR, where)   # a class reached as a value
        if isinstance(r, ast.Name):
            v = self._scoped(r.id, ctx)
            if v is not None and v[0] == "local":
                if call and self._undrawn(whole, where): return   # a method whose return is not drawn from the local's text
                self.resolve(r, ctx, label, done); return
            if v is None and r.id in self.consts and r.id not in params:
                if r.id in self.memos or r.id in self.cmemos: self._memo(r.id, whole, where); return
                if call and self._undrawn(whole, where): return   # the same on a module constant's
                self.resolve(r, ctx, label, done); return
        for a in () if read else self._path_attrs(r):   # an attribute read on the path: refused by its base's root (_attr_root)
            if self._attr_base(a.value, whole, ctx, where): return
        for c in self._path_calls(r):   # a method call on the path that decision 2 refuses (_method_call); one it follows is "a
            how = self._method_call(c.func, ctx)   # method's return" (_base)
            if how is not None and how[0] == "refuse": return self._unread(whole, how[1], where)
        kind, why = self._base(r, ctx)
        if kind == "exempt":   # its own text not read, but a call it derives through carries its arguments' (`dict(X).get(k)` reads X)
            # the method allowlist here too, at every method call on the base's path whose receiver derives through a call handed
            # arguments the pass reads or is the bare name of one of the seven builtins, called unbound (_exempt_undrawn): `whole`
            # first where resolve's last method arm hands it here, then each on r's path, outermost first (_path_calls), so an
            # undrawn method under a drawn one or a subscript's container is refused as one at the top is (the 16:33Z ruling, E2: no
            # exception by shape)
            for c in ([whole] if call else []) + self._path_calls(r):
                if self._exempt_undrawn(c, ctx, where): return
            # a slice, or an index that is no constant, anywhere on that path, under a method call, a subscript or an attribute read as
            # well as at the top: refused as resolve's Subscript arm refuses it (_sliced), since the arguments read next are read whole
            for s in self._path_subs(r):
                if self._sliced(s, ctx): return self._unread(s, _SLICED, where)
            for a in self._chain_args(r): self.resolve(a, ctx, label, done)
            return
        if kind == "readable":
            if call and self._undrawn(whole, where): return   # the same on an expression the pass reads
            self.resolve(r, ctx, label, done); return
        if not self._allowed(where, whole):
            self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                 % (self.rel, whole.lineno, ast.unparse(whole)[:60], why))

    def _undrawn(self, whole, where, why=_UNDRAWN):
        """The eleventh round's method allowlist (the reviewer's 14:42Z ruling, item 3, and his 16:33Z ruling, E2): whether the method
        call `whole`, whose receiver's text receiver is about to read as the page's (a local, a module constant that is no run-time
        memo, or a base _base reads as readable), or whose receiver is a base whose own text the pass does not read that derives
        through a call handed arguments the pass reads or is one of the seven builtins' names called unbound, is refused because its
        method is none of _DRAWN, whose return is drawn from the receiver's text: then a SERVED line by name (`why`: _UNDRAWN, or
        _UNDRAWN_BASE where _exempt_undrawn hands it for a base whose own text the pass does not read) unless
        SERVED_LISTED names the place, which lists it with its reason (_listed), or SERVED_ALLOW does, once per call and place (a
        BoolOp's operands reach it once each: one gap, one line), and the receiver is not read."""
        if whole.func.attr in _DRAWN: return False
        if (id(whole), where) not in self.undrawn:
            self.undrawn.add((id(whole), where))
            if not self._listed(where, whole): self._unread(whole, why % whole.func.attr, where)
        return True

    def _exempt_undrawn(self, c, ctx, where):
        """The method allowlist (_undrawn) at the method call `c` on the path of a base whose own text the pass does not read
        (receiver's exempt point, the 16:33Z ruling, E2): where c's receiver derives through a call handed arguments the pass reads
        (_chain_args: `str(X).lower()`, `dict(a=X).get("a").lower()`) or is the bare name of one of the seven builtins, called
        unbound (`str.lower(X)`, whose argument is its receiver: _base's own proof by binding, "a builtin"), a method none of _DRAWN
        is refused by name, its reason saying that the receiver is a base whose own text the census does not read (_UNDRAWN_BASE);
        whether it was. Any other such receiver, an import's or a parameter's bare name, keeps the call limit."""
        b = c.func.value
        return bool(self._chain_args(b) or isinstance(b, ast.Name) and self._base(b, ctx) == ("exempt", "a builtin")) and self._undrawn(c, where, _UNDRAWN_BASE)

    def _listed(self, where, whole):
        """Whether SERVED_LISTED names the place of the refused method call `whole` (its function and its expression, as a
        SERVED_ALLOW key does): then the place is recorded among the run's allowlist hits, and render_sites lists it with the
        entry's reason, one line per place; the run does not fail on it."""
        key = ("%s:%s" % (self.rel, where), ast.unparse(whole))
        if key not in SERVED_LISTED: return False
        self.res.allow_hits.setdefault(key, set()).add((whole.lineno, whole.col_offset)); return True

    @staticmethod
    def _path_attrs(e):
        """The attribute reads on the path of a receiver or a container `e` (an attribute's or a subscript's value, a method call's
        receiver, a BoolOp's operands), the outermost of each branch: the walk from its base (_attr_root) reads the rest of the path,
        so a read further down is one it reaches. A method called on a name is code behind that name, not a read of it."""
        out, todo = [], [e]
        while todo:
            x = todo.pop()
            if isinstance(x, ast.Attribute): out.append(x)
            elif isinstance(x, ast.Subscript): todo.append(x.value)
            elif isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute): todo.append(x.func.value)
            elif isinstance(x, ast.BoolOp): todo.extend(reversed(x.values))
        return out

    @staticmethod
    def _path_calls(e):
        """The method calls on the path of a receiver or a container `e` (an attribute's or a subscript's value, a method call's
        receiver, a BoolOp's operands), `e` itself among them when it is one, outermost first: each a call in a page position, which
        decision 2 reads (_method_call)."""
        out, todo = [], [e]
        while todo:
            x = todo.pop()
            if isinstance(x, (ast.Attribute, ast.Subscript)): todo.append(x.value)
            elif isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute): out.append(x); todo.append(x.func.value)
            elif isinstance(x, ast.BoolOp): todo.extend(reversed(x.values))
        return out

    @staticmethod
    def _path_subs(e):
        """The subscripts on the path of a receiver or a container `e`, `e` itself among them when it is one, outermost first: the
        path _chain_args reads the calls' arguments down (an attribute's or a subscript's value, a call's callee, a method call's
        receiver through it, a BoolOp's operands), each decided by _sliced."""
        out, todo = [], [e]
        while todo:
            x = todo.pop()
            if isinstance(x, ast.Subscript): out.append(x); todo.append(x.value)
            elif isinstance(x, ast.Attribute): todo.append(x.value)
            elif isinstance(x, ast.Call): todo.append(x.func)
            elif isinstance(x, ast.BoolOp): todo.extend(reversed(x.values))
        return out

    def _attr_base(self, b, whole, ctx, where):
        """Refuse by name the page expression `whole`, which reads an attribute of the base `b`, when b's root by binding refuses
        (_attr_root); whether it did."""
        why = self._attr_root(b, ctx)
        if why is None: return False
        self._unread(whole, why, where); return True

    def _value_class(self, r, ctx):
        """Whether the receiver or container `r`, read in ctx, on whose path no attribute is read (_path_attrs), has a class as its
        root by binding: R1.1's walk (_attr_root) from r answers a class attribute (_CLASS_ATTR), so r is a class reached as a
        value (`_REG["a"]`, a loop, comprehension or with target over classes, an if-expression or a walrus over them). An attribute
        read on the path is decided by its own base's root."""
        return not self._path_attrs(r) and self._attr_root(r, ctx) == _CLASS_ATTR

    def _attr_root(self, e, ctx):
        """Why an attribute read on the base `e`, read in ctx, is refused by name, or None: the base's root by binding. The walk goes
        down the path _base walks (an attribute's value, a subscript's container, a method call's receiver, a call's callee, a
        BoolOp's operands, an if-expression's branches, a walrus's or a starred value) and through a name's binding (_binding: a
        local through each of its values, a loop, comprehension or with target through its source among them, and a module constant
        through its value) and a list, tuple, set or dict literal's elements, keys and values; never a call's argument or a
        parameter's default. At the root it ends at: self by binding (a method's first parameter however spelled, _SelfParam)
        refuses as _SELF_ATTR; a class (its own name, _class_name) as _CLASS_ATTR, wherever the walk meets it, a module constant's
        value among them; any other parameter, a route handler's first parameter the census does not classify (_Unclassified) among
        them, as _PARAM_ATTR; an except name as _EXCEPT_ATTR; in that order. An import, one of the seven builtins a page may name, a value
        slot (`__file__` where it is one among them), a module constant (walked through for a class alone) and a literal the pass
        reads accept. Any other root is one _base refuses, and the walk stops there (a method's return on self, a method called on
        self whose def the route class's order resolves: _self_method; `__file__` in a file that binds it and a run-time memo among
        them, never walked past; a method called on self whose def the order does not resolve is walked through to self): reached
        down the path, where _base refuses it as the base
        it is, that refusal stands and receiver makes it (None here); reached as a name's value (through a comprehension's target, a
        literal container or an if-expression), the attribute read refuses with the reason _base names for it, save inside a module
        constant's value, the constant being read (a local whose attribute is read, directly or through a name bound to it, is a
        container the proof refuses before this walk reads it: xatr's check, _containers; so the walk reads a local's values only for a
        comprehension's target and from a receiver with no attribute read on its path, _value_class); a
        memo is refused as that container wherever the pass reads it (None here). Iterative: an explicit worklist and one visited
        set per query, keyed on the binding's scope and the name, so each name expands once, in _base_step, and the walk is linear
        in the page's size; there is no depth bound."""
        roots, seen, todo = [], set(), [(e, ctx, False, False)]   # (node, ctx, under a module constant, read as a name's value)
        while todo:
            x, c, const, value = todo.pop()
            if isinstance(x, (ast.Attribute, ast.Subscript)): todo.append((x.value, c, const, False)); continue
            if isinstance(x, (ast.BoolOp)): todo.extend((v, c, const, value) for v in reversed(x.values)); continue
            if isinstance(x, (ast.NamedExpr, ast.Starred)): todo.append((x.value, c, const, value)); continue
            if isinstance(x, ast.IfExp): todo += [(x.orelse, c, const, True), (x.body, c, const, True)]; continue
            if isinstance(x, (ast.List, ast.Tuple, ast.Set)): todo.extend((y, c, const, True) for y in reversed(x.elts)); continue
            if isinstance(x, ast.Dict): todo.extend((y, c, const, True) for y in reversed(x.keys + x.values) if y is not None); continue
            if isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and not _unbound_text_call(x):
                if not self._self_method(x.func, c): todo.append((x.func.value, c, const, False)); continue
                kind, why = "head", "a method's return"
            elif isinstance(x, ast.Name): kind, why, got = self._root_name(x, c)
            else: kind, why = self._root_kind(x, c)
            if isinstance(x, ast.Name) and got is not None:
                if (got[0], x.id) not in seen:
                    seen.add((got[0], x.id)); todo += self._base_step(got[1], got[2], const or got[0] is None)
                if kind is None: continue
            roots.append((kind, why, const, value))
        for k, why in (("self", _SELF_ATTR), ("class", _CLASS_ATTR), ("param", _PARAM_ATTR), ("unclassified", _PARAM_ATTR), ("except", _EXCEPT_ATTR)):
            if any(r[0] == k and (k == "class" or not r[2]) for r in roots): return why
        # any other root reached as a name's value, outside a module constant's: the reason _base names for it
        return next((why for kind, why, const, value in roots if kind == "head" and value and not const), None)

    def _base_step(self, vals, ctx, const):
        """_attr_root's expansion of one name, which it calls once for each name it expands, given the values of the name's binding
        and the ctx they are read in (_binding): the values to read next, each read as a name's value, under a module constant where
        the name is one or stands in one's value."""
        return [(y, ctx, const, True) for y in reversed(vals)]

    def _root_slot(self, name, ctx):
        """What a name the scope binds as a parameter or an except name is, as _attr_root's and _recv_roots's root: an except name,
        self by binding (_SelfParam), a route handler's first parameter the census does not classify (_Unclassified: "unclassified",
        refused as a parameter's where an attribute is read on it) or any other parameter."""
        forms = ctx[5].get(name) or ()
        return "except" if "except" in forms else "self" if isinstance(forms, _SelfParam) else "unclassified" if isinstance(forms, _Unclassified) else "param"

    def _root_name(self, x, ctx):
        """The name `x`, read in ctx, as _attr_root's root: (its kind, the reason _base names for it, the binding to walk through,
        _binding's, or None). A class, through its own name; a local, walked through its values,
        and a root itself where a parameter also binds it; a parameter or an except name; a module constant, accepted and walked
        through its value for a class; a run-time memo; `__file__` where it is a value slot; and any other as _base reads it. The
        parameter beside a local's values is dominated: a parameter whose attribute a page reads is a container the proof refuses
        before this walk runs (xatr's check), and from a receiver with no attribute on its path only a class root decides
        (_value_class), which outranks a parameter's; kept on the refusing side, its drop reds nothing."""
        forms = ctx[5].get(x.id)
        if x.id == "__file__" and self.file_bound: return "head", _FILE_BOUND, None
        if self._class_name(x, ctx): return "class", None, None
        v = self._scoped(x.id, ctx)
        if v is not None and v[0] == "local": return (self._root_slot(x.id, ctx) if "param" in forms else None), None, self._binding(x, ctx)
        if v is not None: return (self._root_slot(x.id, ctx), None, None) if v[0] == "exempt" else ("head", v[1], None)
        if x.id in self.consts and x.id not in ctx[0]:
            return ("memo", None, None) if x.id in self.memos else ("accept", None, self._binding(x, ctx))
        if x.id == "__file__" and self._file_slot(): return "accept", None, None
        return self._root_kind(x, ctx) + (None,)

    def _root_kind(self, x, ctx):
        """Any other node as _attr_root's root, as _base reads it: (the kind, the reason). A parameter or a name the body binds
        (a callee among them) is that slot; any other base _base exempts (an import, one of the seven builtins) and a literal it
        reads accept; any other is the reason _base names."""
        kind, why = self._base(x, ctx)
        if kind == "exempt" and why == "a parameter or a name the body binds": return self._root_slot((x.func if isinstance(x, ast.Call) else x).id, ctx), None
        return ("head", why) if kind == "unread" else ("accept", None)

    def _class_root(self, e, ctx):
        """Whether a receiver or a container stands on a class a class statement of the file binds, through the class's own name,
        a name the census resolves to one or a method call on, or a subscript of, a name whose value holds one or such a value itself
        (_class_value), on the path _base walks (an attribute's or a subscript's value, a method call's receiver, a BoolOp's
        operands): `Handler.PAGE`, `Handler.PAGE.get(k)`, `h.render()` after `h = Handler` (`h.PAGE` refusing h as a container
        first, xatr's check), `_H.PAGE` after
        a module-level `_H = Handler`, `_REG.get(k).PAGE` after `_REG = {"a": Handler}`, `_REGD["a"].PAGE` after `_REGD =
        dict(a=Handler)`. No class attribute is read as page text, so each is refused by name (_CLASS_ATTR), as an attribute read on
        self is, rather than read from a class body, passed over its base as a parameter or read as a name's value. A class the
        census reaches through any other base (a loop, comprehension or with target over classes, an if-expression or a walrus over
        classes, a literal container holding one) is refused by the root its base reaches by binding (_attr_root, _CLASS_ATTR; a
        class passed to a parameter or given as its default takes the parameter's reason, _PARAM_ATTR): for an attribute read by
        the attribute's base walk, and for a method called, or a container read, with no attribute read on the way by receiver's
        _value_class. A class reached through an import's attribute or a call's return the census does not resolve (a call of an
        import or of one of the seven builtins) is text such a base holds, the stated limit (its witness rsw: a class a sibling
        module defines, read as an attribute of that module, which the page imports by name)."""
        while True:
            if isinstance(e, ast.Subscript) and self._class_value(e, ctx): return True   # `_REGD["a"]`: an item of a value that holds classes
            if isinstance(e, (ast.Attribute, ast.Subscript)): e = e.value
            elif isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute):
                if self._class_value(e, ctx): return True   # `_REG.get(k)`: a method call on a name whose value holds classes
                e = e.func.value
            elif isinstance(e, ast.BoolOp): return any(self._class_root(v, ctx) for v in e.values)
            else: return isinstance(e, ast.Name) and self._class_value(e, ctx)

    def _class_name(self, x, ctx):
        """Whether the name `x`, read in ctx, is a class's own name: a class statement binds it in the innermost function scope
        of ctx that binds it (a class the page function defines), or, where no function scope of ctx binds it, as a top-level
        statement of the file, whatever else binds it at module level (a rebinding or a write through a computed name among
        them, each leaving a class whose attribute the census does not read as page text)."""
        forms = ctx[5].get(x.id)
        if forms and "global" not in forms: return "class" in forms
        return x.id in self.classes and x.id not in ctx[0]

    def _value_ctx(self, name, ctx):
        """The context the values of the local `name`, read in ctx, are read in: that of the scope that binds it, where Python
        evaluates them. A function defined in the page function, a comprehension and a lambda each read a local they take from the
        scope around them in that scope's context (local_at, set where each builds its context: _ctx, resolve's comprehension and
        Lambda arms), so a nested scope's own binding of a name one of those values reads (`[x for y in ...]` over `x = y`, `lambda y:
        x`, a nested def's `y` or its parameter `y`) is never taken for it; a local the scope binds itself is read in ctx."""
        return self.local_at.get(id(ctx[1]), {}).get(name, ctx)

    def _binding(self, x, ctx):
        """The binding the class walk (_class_value) and _format_texts read the name `x` through, read in ctx: (its scope, its
        values, the ctx the values are read in) for a local of the page's scope (the scope the locals map of the scope that binds it,
        _value_ctx, the values every value _locals holds for the name, read in that scope's context) and for a module constant (the
        scope the module, None, the value the constant's one value, read in the module's context); None for any other name, through
        which neither walk reads a value (a parameter, an except name, any other name the scope binds, a name no module constant
        binds). Each walk keys its visited set on the scope and the name."""
        v = self._scoped(x.id, ctx)
        if v is not None:
            if v[0] != "local": return None
            oc = self._value_ctx(x.id, ctx)
            vals = oc[1].get(x.id, ())   # a comprehension's target has one value, its source, read in that source's context
            return id(oc[1]), vals, (self.comp_at.get(id(vals[0]), oc) if len(vals) == 1 else oc)
        if x.id in ctx[0] or x.id not in self.consts: return None
        return None, [self.consts[x.id]], (set(), {}, None, {}, x.id, {})

    def _class_value(self, x, ctx):
        """Whether the value `x`, read in ctx, names a class a class statement of the file binds: the class's own name
        (_class_name), or a name that stands for such a class other than as its own name: a local of the page's scope any of whose
        values names such a class, and a module constant
        whose value does (`h = Handler`, `_H = Handler`, and a name bound so in turn); through an if-expression's branches, a
        boolean operation's operands and a walrus's value; and a method call on, or a subscript of, a name bound to a container literal
        that holds such a class, as an element of a list, tuple or set, a key or a value of a dict, or so inside a container it holds,
        or bound to a call of the builtin dict with one among its arguments (a local any of whose values does, or a module constant
        whose value does: `_REG.get(k)`, `_REGL.copy()`, `_REGD.get(k)` and `_REGD["a"]` after `_REGD = dict(a=Handler)`:
        _class_step), or on or of such a literal or call itself (`dict(a=Handler).get(k)`, `dict(a=Handler)["a"]`: _held, no name
        expanded).
        One query of the class walk, walked iteratively: an explicit worklist and one visited set per query, keyed on what the
        name is read as (a class reference, or a name whose value may hold a class), on the binding's scope (the locals map for a
        local, the module for a constant: _binding) and on the name, so each name expands once per query, in _class_step, and the
        walk is linear in the page's size. There is no depth bound: the visited set ends the walk. The answer is a disjunction, so
        a name met again drops nothing: its first expansion already carries whatever it reaches."""
        seen, todo = set(), [("value", x, ctx)]
        while todo:
            query, x, ctx = todo.pop()
            if query == "value":   # an expression: its branches, its operands, a walrus's value, or the name it reads
                if isinstance(x, ast.IfExp): todo += [("value", x.orelse, ctx), ("value", x.body, ctx)]
                elif isinstance(x, ast.BoolOp): todo += [("value", v, ctx) for v in reversed(x.values)]
                elif isinstance(x, ast.NamedExpr): todo.append(("value", x.value, ctx))
                elif isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute) and isinstance(x.func.value, ast.Name):
                    todo.append(("holds", x.func.value, ctx))   # `_REG.get(k)`, `_REGL.copy()`: a name whose value may hold classes
                elif (isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
                      and isinstance(x.func.value, (ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Call))):
                    todo += self._held([x.func.value], ctx)   # `dict(a=Handler).get(k)`: such a value itself, no name expanded
                elif isinstance(x, ast.Subscript) and isinstance(x.value, ast.Name):
                    todo.append(("holds", x.value, ctx))   # `_REGD["a"]` after `_REGD = dict(a=Handler)`: an item of a name's value
                elif isinstance(x, ast.Subscript) and isinstance(x.value, (ast.List, ast.Tuple, ast.Set, ast.Dict, ast.Call)):
                    todo += self._held([x.value], ctx)   # `dict(a=Handler)["a"]`: an item of such a value itself
                elif isinstance(x, ast.Name):
                    if self._class_name(x, ctx): return True
                    todo.append(("ref", x, ctx))   # a name that may stand for a class: its binding's values
                continue
            got = self._binding(x, ctx)
            if got is None or (query, got[0], x.id) in seen: continue
            seen.add((query, got[0], x.id))
            todo += self._class_step(query, got[1], got[2])
        return False

    def _class_step(self, query, vals, ctx):
        """The class walk's expansion of one name, which _class_value calls once for each name it expands, given the values of the
        name's binding and the ctx they are read in (_binding): the values to read next, each one that may name a class. For a
        class reference they are the values themselves; for a name whose value may hold a class they are the names standing in a
        list, tuple or set literal among the values, as a key or a value of a dict literal, or as an argument, positional or a
        keyword's value, of a call of the builtin dict, one of the seven a page may name (`dict(a=Handler)`: _base reads the
        callee as that builtin), or so inside a container literal or such a call it holds."""
        if query == "ref": return [("value", y, ctx) for y in reversed(vals)]
        return self._held(vals, ctx)

    def _held(self, vals, ctx):
        """The names the values `vals`, read in ctx, hold as the class walk reads a container: each standing in a list, tuple or set
        literal, as a key or a value of a dict literal, or as an argument, positional or a keyword's value, of a call of the builtin
        dict (_base reads the callee as that builtin), or so inside a container literal or such a call it holds; each a value item of
        the class walk (_class_value)."""
        out, todo = [], list(vals)
        while todo:
            y = todo.pop()
            if isinstance(y, (ast.List, ast.Tuple, ast.Set)): todo.extend(y.elts)
            elif isinstance(y, ast.Dict): todo.extend(k for k in y.keys + y.values if k is not None)
            elif (isinstance(y, ast.Call) and isinstance(y.func, ast.Name) and y.func.id == "dict"
                  and self._base(y, ctx) == ("exempt", "a builtin")):   # `dict(a=Cls)`, `dict({"a": Cls})`: a registry the builtin builds
                todo.extend(list(y.args) + [k.value for k in y.keywords])
            elif isinstance(y, ast.Name): out.append(("value", y, ctx))
        return out

    @staticmethod
    def _chain_args(e):
        """The arguments of every call a receiver or a container derives through, down the path _base reads (an attribute's or a
        subscript's value, a method call's receiver, a BoolOp's operands), innermost first: each is read as text, as a bare name
        is, since the arguments of one of the seven builtins a page may call, of an import, of a parameter or of a method on one
        are page text (`dict(X)` and `json.loads(json.dumps(X))` carry X's values; `list(X)` and `sorted(X)` are refused by name
        before this, list and sorted being no builtin a page may call: _BUILTIN_OTHER). The reader reads these arguments' own
        text, never the text the call computes from them: text a call computes from its arguments is not read (the stated limit,
        its witnesses chr, getattr and a decoder whose bytes the page serves as they come, `base64.b64decode(X)` or zlib or gzip
        over an embedded bundle, `zlib.decompress(base64.b64decode(X))`; an encoded asset kept ASCII and decoded where the page is
        built is such a shape, and can be honest; max handed one iterable
        or a starred argument, which returns an element its argument holds, is refused before this, _MAX_ONE, and so is str
        handed more than one positional argument, a starred argument or a keyword other than object, _STR_DECODE; a method
        whose return is not drawn from its receiver's text on a base these arguments reach is refused by name at every call on the
        path, _exempt_undrawn, and so is a slice, or an index that is no constant, over a container these arguments reach, as the
        page expression or anywhere on the path, _chain_text and _sliced over _path_subs; and a
        method called on a parameter whose name is no route class's method, a method of a
        class that holds no route among them, stays under this call limit too, its arguments read and the text it computes not)."""
        if isinstance(e, (ast.Attribute, ast.Subscript)): return _Served._chain_args(e.value)
        if isinstance(e, ast.Call): return _Served._chain_args(e.func) + list(e.args) + [k.value for k in e.keywords]
        if isinstance(e, ast.BoolOp): return [a for v in e.values for a in _Served._chain_args(v)]
        return []

    @staticmethod
    def _const_text(e):
        """(the text an expression evaluates to, the read-once keys of the string literals it holds, in their order in that text,
        whether the text is more than those literals side by side) when its every part is a string constant, else None: a str
        constant; a `+` of two such; an f-string whose fields are each such, with no format spec (a conversion applied); a `%`
        whose format is such and whose operand is such, or a tuple of such, or a dict of such under string keys; a `.join` called
        on such with one list or tuple of such, or one dict literal whose keys are such (its keys, in order, a repeated key at its
        first place); a `.format` called on such with such arguments; a `.format_map` called on such with a dict of such under
        string keys; and a `.replace` called on such, of such by such. Implicitly concatenated literals are one constant already.
        A method called on anything else is none, the name str, bytes or bytearray among them (`str.join("", [...])`, unbound),
        which resolve refuses by name in a page (_UNBOUND) and Scan.ns_string takes as a run-time form in a lookup position. A
        `%`, `.format` or `.format_map` with a field or precision wider than a million characters (a `%` conversion's width or
        precision, each conversion read as Python parses it, _pct_fields, or any run of digits in a format field's own spec:
        _too_wide) and a `.format` or `.format_map` whose format spec holds a replacement field are not expanded: each is none here,
        refused by name in a page (_wide, _nested) and a run-time form in a lookup position. So is a join whose own folded text may
        run past a million characters (_FOLD_CAP), its length bounded before the text is built (_fold): refused by name in a page
        (_long) and, in a lookup position, a key the allowlist takes for a join the census does not fold. A join Python would refuse
        is none."""
        got = _Served._fold(e)
        return None if got is _TOO_LONG else got

    @staticmethod
    def _long(e):
        """Whether `e` is a join each of whose parts _const_text folds and whose own folded text may run past a million characters
        (_FOLD_CAP, _fold): _const_text does not expand it, and resolve refuses it by name in a page (_LONG: _join for a `%`, a
        `.join`, `.format`, `.format_map` or `.replace`, and _note for a run of a `+` chain's operands or of an f-string's parts)."""
        return _Served._fold(e) is _TOO_LONG

    @staticmethod
    def _fold(e):
        """_const_text's reading of `e`, or _TOO_LONG where each part of e folds and e's own folded text may run past _FOLD_CAP, a
        million characters (R3 of the eleventh round's review, the width guard's second face: the width guard bounds one field, and a
        `.format` or a `%` that repeats a field, a `.join` whose separator is itself such a join or a `.replace` doubles the text per
        level from a line of source under a kilobyte, so the length is bounded before the text is built). A `+`, an f-string, a
        `.join` and a `.replace` by the exact length of their text; a `.format` and a `.format_map` by the exact length of each field,
        formatted by Python on its own (_format_length), and of the literal text between; a `%` by a bound no conversion's text can
        pass (_pct_bound). A part whose own text passes the cap is none to the join that holds it, so that join is none as well and
        resolve reads its parts down to the one that passes, refused there by name (one line, at the join whose own text passes). A
        string constant is source text and is never cut."""
        if isinstance(e, ast.Constant): return (e.value, [(e.lineno, e.col_offset, -1)], False) if type(e.value) is str else None
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add):
            l, r = _Served._const_text(e.left), _Served._const_text(e.right)
            # two texts of one type, a str or a tuple (the reviewer's 14:42Z ruling: Python raises TypeError on a str and a tuple and on
            # two dicts, so such a `+` folds to none, refused where the census reads it, never a crash)
            if not (l and r) or type(l[0]) is not type(r[0]) or type(l[0]) not in (str, tuple): return None
            if type(l[0]) is str and type(r[0]) is str and len(l[0]) + len(r[0]) > _FOLD_CAP: return _TOO_LONG   # R3: the cap
            return (l[0] + r[0], l[1] + r[1], l[2] or r[2])
        if isinstance(e, ast.JoinedStr):
            parts = _Served._fparts(e)
            if None in parts: return None
            if sum(len(p[0]) for p in parts) > _FOLD_CAP: return _TOO_LONG   # R3: the cap, before the parts are joined
            return ("".join(p[0] for p in parts), [k for p in parts for k in p[1]], any(p[2] for p in parts))
        if isinstance(e, ast.Dict):   # a `%` or `.format_map` operand: its values under string keys
            if not all(isinstance(k, ast.Constant) and type(k.value) is str for k in e.keys): return None
            vals = [_Served._const_text(v) for v in e.values]
            return None if None in vals else ({k.value: v[0] for k, v in zip(e.keys, vals)}, [x for v in vals for x in v[1]], True)
        if isinstance(e, ast.Tuple):   # a `%` operand
            vals = [_Served._const_text(v) for v in e.elts]
            return None if None in vals else (tuple(v[0] for v in vals), [x for v in vals for x in v[1]], True)
        got, wide = None, _Served._too_wide   # a width or precision over a million is not expanded
        try:
            if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mod):
                l, r = _Served._const_text(e.left), _Served._const_text(e.right)
                if l and r and type(l[0]) is str:
                    fields = _pct_fields(l[0])   # each conversion as Python parses it, a mapping key's nested parentheses counted
                    if not wide([w for f in fields for w in f[:2]]):
                        if _Served._pct_bound(l[0], fields, r[0]) > _FOLD_CAP: return _TOO_LONG   # R3: the cap
                        got = (l[0] % r[0], l[1] + r[1], True)
            elif isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr in ("join", "format", "format_map", "replace"):
                base, attr = _Served._const_text(e.func.value), e.func.attr
                if base is None or type(base[0]) is not str or any(isinstance(a, ast.Starred) for a in e.args): return None
                if attr == "join":   # one list or tuple of string constants, or a dict literal's keys, the base between each two
                    if len(e.args) != 1 or e.keywords or not isinstance(e.args[0], (ast.List, ast.Tuple, ast.Dict)): return None
                    arg = e.args[0]
                    elts = arg.elts if not isinstance(arg, ast.Dict) else [k for k in arg.keys if isinstance(k, ast.Constant)]
                    if isinstance(arg, ast.Dict):   # a dict iterates its keys in order, a repeated key at its first place
                        if len(elts) != len(arg.keys) or any(type(k.value) is not str for k in elts): return None
                        first = {}
                        for k in elts: first.setdefault(k.value, k)
                        elts = list(first.values())
                    items = [_Served._const_text(v) for v in elts]
                    if None in items or any(type(v[0]) is not str for v in items): return None
                    if sum(len(v[0]) for v in items) + max(len(items) - 1, 0) * len(base[0]) > _FOLD_CAP: return _TOO_LONG   # R3: the cap
                    keys = [k for i, v in enumerate(items) for k in (base[1] if i else []) + v[1]]
                    got = (base[0].join(v[0] for v in items), list(dict.fromkeys(keys)) or base[1], True)
                else:
                    args = [_Served._const_text(a) for a in e.args]
                    kw = [(k.arg, _Served._const_text(k.value)) for k in e.keywords]
                    if None in args or any(k is None or v is None for k, v in kw): return None
                    specs = [spec for _, _, spec, _ in string.Formatter().parse(base[0]) if spec] if attr in ("format", "format_map") else []
                    whole = not wide([w for spec in specs for w in re.findall(r"\d+", spec)]) and not any("{" in spec for spec in specs)
                    if attr == "format" and whole and all(type(a[0]) is str for a in args) and all(type(v[0]) is str for _, v in kw):
                        pos, named = [a[0] for a in args], {k: v[0] for k, v in kw}
                        if _Served._format_length(base[0], pos, named) > _FOLD_CAP: return _TOO_LONG   # R3: the cap
                        got = (base[0].format(*pos, **named), base[1] + [x for a in args for x in a[1]] + [x for _, v in kw for x in v[1]], True)
                    elif attr == "format_map" and whole and len(args) == 1 and not kw and isinstance(args[0][0], dict):
                        if _Served._format_length(base[0], (), args[0][0]) > _FOLD_CAP: return _TOO_LONG   # R3: the cap
                        got = (base[0].format_map(args[0][0]), base[1] + args[0][1], True)
                    elif attr == "replace" and len(args) == 2 and not kw and all(type(a[0]) is str for a in args) and args[0][0]:
                        old, new = args[0][0], args[1][0]
                        if len(base[0]) + base[0].count(old) * (len(new) - len(old)) > _FOLD_CAP: return _TOO_LONG   # R3: the cap
                        got = (base[0].replace(old, new), base[1] + args[1][1], True)
        except (TypeError, ValueError, KeyError, IndexError, AttributeError, OverflowError, MemoryError):
            return None
        return got if got is not None and type(got[0]) is str else None

    @staticmethod
    def _pct_bound(fmt, fields, operand):
        """A bound no text `fmt % operand` gives can pass (_fold's cap on a `%`; `fields` the format's conversions, _pct_fields): the
        format's own length, and for each conversion its width and the longest text the operand, whole, or any value it holds gives
        under that conversion: its own length for `%s` of a str (and a tuple's or a dict's repr for `%s` of one), and ten times that
        and two more for any other conversion (a repr or an ascii escapes a character to ten at most, and quotes it). A precision
        only cuts a str conversion, so it adds nothing; a conversion's markup counts in the format's length, which covers a literal
        percent and a one-character `%c`."""
        vals = [operand] + (list(operand.values()) if type(operand) is dict else list(operand) if type(operand) is tuple else [])
        plain = max(len(v) if type(v) is str else len(repr(v)) for v in vals)
        return len(fmt) + sum(int(w.lstrip("0") or "0") + (plain if c == "s" else 10 * plain + 2) for w, _, c in fields)

    @staticmethod
    def _format_length(fmt, args, kwargs):
        """The length of `fmt.format(*args, **kwargs)` (of `fmt.format_map(kwargs)` with no args), each replacement field formatted
        by Python on its own and the literal text between counted, so no text longer than one field is built (_fold's cap on a
        `.format` and a `.format_map`): the field's object read as str.format reads it (an argument by its number or its keyword, a
        field with no number or keyword taking the next argument, then each attribute or item the field's name reaches), its
        conversion applied, then formatted by its spec. A format Python refuses raises here or where _fold builds it."""
        n, auto = 0, 0
        for lit, name, spec, conv in _string.formatter_parser(fmt):
            n += len(lit)
            if name is None: continue
            first, rest = _string.formatter_field_name_split(name)
            if first == "": first, auto = auto, auto + 1   # numbered automatically, as str.format numbers it
            obj = args[first] if isinstance(first, int) else kwargs[first]
            for attr, key in rest: obj = getattr(obj, key) if attr else obj[key]
            n += len(format({None: str, "s": str, "r": repr, "a": ascii}[conv](obj), spec or ""))
        return n

    @staticmethod
    def _too_wide(ws):
        """Whether any of the digit strings `ws` (a `%` conversion's width and precision, or the digit runs of a format spec) names
        more than a million characters: one with more than seven digits after its leading zeros is, without converting it (int()
        refuses a digit string past 4300 digits on 3.11 and later, and on the 3.10 releases that carry that limit), and a
        zero-padded small value is not (`0000000000005` is 5)."""
        return any(w and (len(s := w.lstrip("0")) > 7 or int(s or "0") > 10 ** 6) for w in ws)

    @staticmethod
    def _wide(e):
        """Whether `e` is a `%`, a `.format` or a `.format_map` called on a string constant (or on a join _const_text folds) with a
        field or precision wider than a million characters: a `%` conversion's width or precision, or any run of digits in a format
        field's own spec, the arguments' text not read (_too_wide). _const_text does not expand it; resolve refuses it by name in a
        page (_WIDE) and Scan.ns_string takes it as a run-time form where a run-time lookup by name takes it as the key."""
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mod):
            l = _Served._const_text(e.left)
            try: ws = [w for f in _pct_fields(l[0]) for w in f[:2]] if l and type(l[0]) is str else []   # each conversion as Python parses it
            except ValueError: ws = []   # a format Python refuses: the page raises, no text served
        elif isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr in ("format", "format_map"):
            b = _Served._const_text(e.func.value)
            try: ws = [w for _, _, spec, _ in string.Formatter().parse(b[0]) if spec for w in re.findall(r"\d+", spec)] if b and type(b[0]) is str else []
            except ValueError: ws = []
        else: return False
        return _Served._too_wide(ws)

    @staticmethod
    def _nested(e):
        """Whether `e` is a `.format` or a `.format_map` called on a string constant (or on a join _const_text folds) whose format
        spec holds a replacement field (`"{:>{}}".format(t, w)`, `"{t:>{w}}".format_map(m)`), whatever its arguments: the spec,
        its width among it, is computed at run time from an argument, so _const_text does not expand it, resolve refuses it by
        name in a page (_NESTED) and Scan.ns_string takes it as a run-time form where a run-time lookup by name takes it as the
        key. A format string Python cannot parse is none (the call raises)."""
        if not (isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr in ("format", "format_map")): return False
        b = _Served._const_text(e.func.value)
        if not b or type(b[0]) is not str: return False
        try: return any(spec and "{" in spec for _, _, spec, _ in string.Formatter().parse(b[0]))
        except ValueError: return False

    def _field_reach(self, e, ctx):
        """The refusal the `.format` or `.format_map` call `e` takes for its format string, read through its receiver
        (_format_texts), or None: _FIELD_REACH where a format string the receiver holds has a replacement field whose name reaches
        an attribute or an index of its argument (`{0.CSS}`, `{h.CSS}`, `{self.body}`, `{0[k]}`), at its top level or nested in a
        field's format spec at any depth (`{0:{1.W}}`, `{a:{b[0]}}`: _reaches), since the text such a field reads is the
        argument's attribute or item, which the pass does not read, the argument being read as its own text, a class or self among
        them; else _TEMPLATE where the receiver reaches anything but a string constant, a join _const_text folds to one or a name
        bound to one (a function's or a method's return, a parameter, an attribute, an if-expression, a `+` over a name, a method
        called on a name among them), since the pass does not read that format string's fields; else None. resolve asks it only of
        a call _join did not refuse (_WIDE, _NESTED), so a node takes one of those reasons, never two, and takes _TEMPLATE only where
        the receiver is no class, stands as no subscript operand and is read with no refusal by name."""
        if not (isinstance(e.func, ast.Attribute) and e.func.attr in ("format", "format_map")): return None
        texts, other = self._format_texts(e.func.value, ctx)
        if any(self._reaches(text) for text in texts): return _FIELD_REACH
        return _TEMPLATE if other else None

    @staticmethod
    def _reaches(text):
        """Whether the format string `text` holds a replacement field whose name reaches an attribute or an index (a `.` or a `[`
        in the name), at its top level or nested in a field's format spec, at any depth, each spec parsed in turn with
        string.Formatter().parse from an explicit worklist. A format string Python refuses is read up to the fault: the call
        raises there, and no page is served."""
        todo = [text]
        while todo:
            try:
                for _, name, spec, _ in string.Formatter().parse(todo.pop()):
                    if name and ("." in name or "[" in name): return True
                    if spec: todo.append(spec)
            except ValueError: pass
        return False

    def _format_texts(self, x, ctx):
        """(the format strings the receiver `x` of a `.format` or `.format_map` holds, as the pass reads them; whether it reaches
        anything else): its text where it is a string constant or a join of them that _const_text folds to a str, and, where it is
        a name, the texts of the values a local of the page's scope or a module constant so named is bound to (_binding), a name
        bound to such a name in turn; any other value it reaches (a call, an attribute, a subscript, an if-expression, a boolean
        operation, a `+` or a `%` over a name, a parameter, an except name, a name no local or module constant binds, a join that
        folds to no str) is anything else, and gives no text. Walked iteratively, as the class walk is: an explicit worklist and
        one visited set per query, keyed on the binding's scope and the name, so each name expands once, in _format_step, and the
        walk is linear in the page's size. There is no depth bound: the visited set ends the walk. The texts are a union and the
        other answer a disjunction, so a name met again drops nothing: its first expansion already carries whatever it reaches."""
        texts, other, seen, todo = [], False, set(), [(x, ctx)]
        while todo:
            x, ctx = todo.pop()
            c = self._const_text(x)
            if c is not None and type(c[0]) is str:
                texts.append(c[0]); continue
            got = self._binding(x, ctx) if isinstance(x, ast.Name) else None
            if got is None: other = True; continue
            if (got[0], x.id) in seen: continue
            seen.add((got[0], x.id))
            todo += self._format_step(got[1], got[2])
        return texts, other

    def _set_value(self, x, ctx):
        """Whether `x`, the iterable a `.join` is handed, read in ctx, is or holds a set literal or a set comprehension as the census reads
        it, whose iteration order is not fixed, so the join's text is no one text (resolve refuses such a join by name, _JOIN_SET): `x`
        itself; a walrus's value; an if-expression's branches; a boolean operation's operands; the elements of a list or tuple display, a
        starred element's value among them; the sources of a list or dict comprehension or a generator expression, whose order is theirs
        (the first read in the scope around it; a later one that names a target of the comprehension reads an item of an earlier source,
        which this reads whole, and is not read itself); and the values of a name _binding reads: a local of the page's scope (its
        values as _locals holds them, a loop's, an unpacking's or a with target's source and a local container's appended or stored
        values among them) or a module constant (its one value), a name bound so in turn. A parameter, an except name and any other
        name _binding does not read are not followed, so a set a parameter takes, as the argument a call hands it or as its default,
        is read piece by piece under the join limit, as a call's return is (its witnesses jwp and jwq). A set a call returns, an
        attribute holds or a
        subscript selects is not reached here. Walked iteratively, as the format strings' walk is: an explicit worklist and one visited set
        per query, keyed on the binding's scope and the name, so each name expands once, in _set_step (freeze ruling 2 of the eleventh
        round: its count pin reads that step from outside the script; without the visited set a cycle of names loops)."""
        seen, todo = set(), [(x, ctx)]
        while todo:
            x, ctx = todo.pop()
            t = type(x)
            if t is ast.Set or t is ast.SetComp: return True
            if t is ast.NamedExpr or t is ast.Starred: todo.append((x.value, ctx))
            elif t is ast.IfExp: todo += [(x.body, ctx), (x.orelse, ctx)]
            elif t is ast.BoolOp: todo += [(v, ctx) for v in x.values]
            elif t is ast.List or t is ast.Tuple: todo += [(v, ctx) for v in x.elts]
            elif t is ast.ListComp or t is ast.DictComp or t is ast.GeneratorExp:   # the first source runs in the scope around it
                own = {n for g in x.generators for n, _ in Scan._key_targets(g.target)}
                todo += [(g.iter, ctx) for i, g in enumerate(x.generators)
                         if not i or not any(type(m) is ast.Name and m.id in own for m in ast.walk(g.iter))]
            elif t is ast.Name:
                got = self._binding(x, ctx)
                if got is None or (got[0], x.id) in seen: continue
                seen.add((got[0], x.id))
                todo += self._set_step(got[1], got[2])
        return False

    def _set_step(self, vals, ctx):
        """_set_value's expansion of one name, which it calls once for each name it expands, given the values of the name's binding
        and the ctx they are read in (_binding): the values to read next, in their order."""
        return [(y, ctx) for y in reversed(vals)]

    def _format_step(self, vals, ctx):
        """_format_texts's expansion of one name, which it calls once for each name it expands, given the values of the name's
        binding and the ctx they are read in (_binding): the values to read next, in their order."""
        return [(y, ctx) for y in reversed(vals)]

    def _join(self, e, where):
        """A `%`, `.join`, `.format`, `.format_map` or `.replace` of string constants recorded as a join (_note), or, too wide to
        expand (_wide), holding a replacement field in a format spec (_nested) or folding to a text that may run past a million
        characters (_long, R3 of the eleventh round's review), refused by name; whether it refused."""
        if self._wide(e): self._unread(e, _WIDE, where)
        elif self._nested(e): self._unread(e, _NESTED, where)
        elif self._long(e): self._unread(e, _LONG, where)
        else: self._note([self._const_text(e)]); return False
        return True

    @staticmethod
    def _format_slots(e):
        """The value slots (_value_slot: a None, bool or int constant, the empty bytes constant, a Mult or LShift over int constants)
        that stand directly as an operand of the `%` or the format call `e`, where a conversion can turn one into characters (`%c`,
        `%x`, `{:c}`, `%.1s` over the empty bytes), so resolve refuses each by name whether or not a conversion takes it and
        whatever the conversion (_SLOT_FORMAT): a `%`'s right operand, bare, an
        element of a tuple or a value of a dict literal; a `.format` call's positional or keyword argument, an element of a starred
        list or tuple literal and a value of a `**` dict literal among them; and a value of the dict literal a `.format_map` call is
        handed. One held deeper there (an if-expression's branch, a container's element, a call's argument, a name bound to one) is
        read as a value slot and not refused; an int modulo by a constant (`n % 60`) is refused as a `%`, failing closed."""
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mod):
            r = e.right
            ops = list(r.elts) if isinstance(r, ast.Tuple) else list(r.values) if isinstance(r, ast.Dict) else [r]
        elif isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "format":
            ops = [x for a in e.args for x in (a.value.elts if isinstance(a, ast.Starred) and isinstance(a.value, (ast.List, ast.Tuple)) else [a])]
            ops += [x for k in e.keywords for x in (k.value.values if k.arg is None and isinstance(k.value, ast.Dict) else [k.value])]
        elif isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "format_map":
            ops = [v for a in e.args if isinstance(a, ast.Dict) for v in a.values]
        else: return []
        return [x for x in ops if _value_slot(x)]

    @staticmethod
    def _join_operands(e):
        """The operands of the join `e` whose pieces the pass reads each on its own, in every join form the served paragraph names:
        a `+`'s two, a `%`'s format and its right operand (bare, an element of a tuple or a value of a dict literal), an
        f-string's fields, and the receiver and arguments of a `.join`, `.format`, `.format_map` or `.replace` call: a `.join`'s
        with the elements of a list, tuple or set literal argument and the keys of a dict literal one, a `.format`'s with the
        elements of a starred list or tuple literal and the values of a `**` dict literal, and a `.format_map`'s with the values of
        a dict literal argument."""
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add): return [e.left, e.right]
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mod):
            r = e.right
            return [e.left] + (list(r.elts) if isinstance(r, ast.Tuple) else list(r.values) if isinstance(r, ast.Dict) else [r])
        if isinstance(e, ast.JoinedStr): return [v.value for v in e.values if isinstance(v, ast.FormattedValue)]
        if not (isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr in ("join", "format", "format_map", "replace")): return []
        out, attr = [e.func.value], e.func.attr
        for a in e.args + [k.value for k in e.keywords]:
            out.append(a)
            if attr == "join" and isinstance(a, (ast.List, ast.Tuple, ast.Set)): out.extend(a.elts)
            elif attr == "join" and isinstance(a, ast.Dict): out.extend(k for k in a.keys if k is not None)
            elif attr == "format" and isinstance(a, ast.Starred) and isinstance(a.value, (ast.List, ast.Tuple)): out.extend(a.value.elts)
            elif attr in ("format", "format_map") and isinstance(a, ast.Dict): out.extend(a.values)
        return out

    def _sub_operand(self, x, ctx):
        """Whether `x`, an operand of a join (_join_operands), is a subscript by a constant index of a container whose text the pass
        reads (_carries_text), which resolve refuses by name (_SUB_OPERAND): the pass reads the container whole, each of its string
        constants on its own, and does not compute the text the join makes of the pieces the indexes select, so a tag split across
        `_P[0] + _P[1]` over a tuple constant is not seen. A subscript by a slice or another index is resolve's Subscript arm's
        (_SLICED), one whose container derives from a run-time memo is refused as that memo (receiver), and a subscript read through
        a function (a call's argument, or what a followed function returns) is read as that call's arguments' text: text a call
        computes from its arguments is not read."""
        if not (isinstance(x, ast.Subscript) and isinstance(x.slice, ast.Constant)): return False
        root = x.value
        while True:   # the path _base walks: an attribute's or a subscript's value, a method call's receiver
            if isinstance(root, (ast.Attribute, ast.Subscript)): root = root.value
            elif isinstance(root, ast.Call) and isinstance(root.func, ast.Attribute): root = root.func.value
            else: break
        if isinstance(root, ast.Name) and root.id in self.memos and root.id not in ctx[0] and self._scoped(root.id, ctx) is None: return False
        return self._carries_text(x.value, ctx)

    def _refuse_operands(self, e, ctx, where):
        """The refusals by name on the operands of a `+`, a `%`, an f-string or a `.join`, `.format`, `.format_map` or `.replace`
        call `e`, before resolve reads them: each value slot that stands directly as the right operand of a `%`, a `.format`
        argument or a `.format_map` value (_format_slots, _SLOT_FORMAT) and each subscript whose join the pass does not compute (_sub_operand,
        _SUB_OPERAND, over every operand _join_operands gives), each a SERVED line at its own line unless SERVED_ALLOW names the place. A
        refused subscript's id joins self.op_refused, so resolve's Subscript arm does not read its container: the pass names the gap
        and reads nothing the join selects, as a slice refused by name reads nothing (_SLICED)."""
        for x in self._format_slots(e): self._unread(x, _SLOT_FORMAT, where)
        for x in self._join_operands(e):
            if self._sub_operand(x, ctx): self._unread(x, _SUB_OPERAND, where); self.op_refused.add(id(x))

    @staticmethod
    def _fparts(e):
        """An f-string's parts in order, as _const_text gives each: a literal part (keyed as resolve keys it), and a field whose value
        is a join of string constants with no format spec, its conversion applied (`!r`, `!a`); None for any other field."""
        out = []
        for i, v in enumerate(e.values):
            if isinstance(v, ast.Constant): out.append((v.value, [(e.lineno, e.col_offset, i)], False)); continue
            c = _Served._const_text(v.value) if v.format_spec is None else None
            if c is None or type(c[0]) is not str: out.append(None); continue
            conv = {114: repr, 97: ascii}.get(v.conversion)
            out.append((conv(c[0]), c[1], True) if conv else c)
        return out

    def _chain(self, e):
        """A `+` chain's operands in order, each as _const_text gives it or None (an f-string's parts each on their own, so the literal
        text at its start or end joins the operand beside it); every `+` node inside is marked read (self.noted), and so is every
        f-string among its operands, whose parts the chain's runs hold (so the cap refuses such an f-string once, at the chain)."""
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add):
            self.noted.add(id(e)); return self._chain(e.left) + self._chain(e.right)
        if isinstance(e, ast.JoinedStr): self.noted.add(id(e)); return self._fparts(e)
        c = self._const_text(e)
        return [c if c is not None and type(c[0]) is str else None]

    def _note(self, ops, e=None, where=None):
        """Record each run of operands that are all string constants (_const_text), side by side in a `+` chain or an f-string or
        alone in a `%`, `.join`, `.format`, `.format_map` or `.replace`, as a join (self.joins: its keys -> (the keys in the text's
        order, the text)) when it holds two literals or more, or its text is more than its literal: served_texts scans its text
        beside each literal's own read. A run of a `+` chain's operands or of an f-string's parts whose text would run past a
        million characters in all (_FOLD_CAP; each operand folds within it on its own) is never recorded, and the chain or f-string
        `e`, where resolve hands it with its place, is refused by name, once (_LONG: R3 of the eleventh round's review; an f-string a
        chain holds is handed without it, the chain's own runs holding its parts)."""
        run, long = [], False
        for op in list(ops) + [None]:
            if op is not None: run.append(op); continue
            keys = [k for o in run for k in o[1]]
            if sum(len(o[0]) for o in run) > _FOLD_CAP: long = True   # never joined: past the cap
            elif len(keys) > 1 or any(o[2] for o in run): self.joins.setdefault(frozenset(keys), (keys, "".join(o[0] for o in run)))
            run = []
        if long and e is not None: self._unread(e, _LONG, where)

    # resolve's walk over the names it follows (choice 11 of the eleventh round's rulings, freeze ruling 2: a walk that expands names through a visited
    # set): `done`, one visited set per route, keyed on what each arm follows (a comprehension, a local of a function, a module
    # constant, a function defined in the page function, a module function and a followed function's default), and resolve expands
    # each key once, calling _resolve_step once for each key it adds, given the values that arm reads for it (a comprehension's
    # generators, a local's values, a constant's one value, a function's returns, a default), which the step hands back as a list.
    # _route_done is its entry, called once per route before resolve starts, which hands back the route's fresh visited set. Both
    # are builtins, so neither stands as a frame of its own under resolve's recursion, where a chain's depth is decided (decision
    # 11 of the tenth round's review: resolve completes a chain to the depth it did before the step); the census module counts
    # both from outside the script
    _route_done = staticmethod(set)
    _resolve_step = staticmethod(list)

    def resolve(self, e, ctx, label, done):
        """Add the text `e` evaluates to under ctx (the value-slot names, the locals, the class, the nested functions, the place's
        name, the scope's binding forms) as pieces and file slots; `done` holds the names already followed for this route, so a
        constant, a function or a local is read once per route and a cycle stops, each key expanded once through _resolve_step. A
        name, a receiver's base and a callee the page function's scope binds are decided by that scope (_scoped) before the
        module's binding."""
        params, local, cls, nested, where, scope = ctx
        if isinstance(e, ast.Constant):
            if isinstance(e.value, str): self.pieces.append((label, e.lineno, e.value, (e.lineno, e.col_offset, -1)))
            elif e.value is None or type(e.value) in (bool, int) or e.value == b"" and isinstance(e.value, bytes):
                # a value slot read as no text: None, a bool, an int or the empty bytes, refused by name where it stands
                # directly as the right operand of a `%`, a `.format` argument or a `.format_map` dict literal's value, whether
                # or not a conversion takes it (_format_slots)
                pass
            else: self._unread(e, _CONSTANT_KINDS.get(type(e.value), "a %s Constant" % type(e.value).__name__), where)
        elif isinstance(e, ast.JoinedStr):   # each part keyed at its own line: the part's on 3.12 and later, else where the expression before it ends
            # its literal parts and constant fields side by side, a join (served_texts); past the cap refused (_LONG), save an f-string a
            # `+` chain holds, whose parts the chain's runs held and refused (_chain)
            self._note(self._fparts(e), *((e, where) if id(e) not in self.noted else ()))
            self._refuse_operands(e, ctx, where)   # a field that is a subscript whose join the pass does not compute
            prev = e.lineno
            for idx, v in enumerate(e.values):
                if isinstance(v, ast.Constant): self.pieces.append((label, v.lineno if sys.version_info >= (3, 12) else prev, v.value, (e.lineno, e.col_offset, idx)))
                elif isinstance(v, ast.FormattedValue):
                    prev = v.value.end_lineno; self.resolve(v.value, ctx, label, done)
                    # a format spec is refused, not read: before 3.12 its parts carry the f-string's own position, which served_texts's
                    # read-once key would take for a part already read and drop; the line shows the field, which unparses alike everywhere
                    if v.format_spec is not None:
                        self._unread(e, "a format spec", where, v.value.lineno, "{%s:...}" % ast.unparse(v.value))
        elif isinstance(e, ast.BinOp) and isinstance(e.op, (ast.Add, ast.Mod, ast.Div)):   # a Div's operands too: a path join
            if isinstance(e.op, ast.Add) and id(e) not in self.noted: self._note(self._chain(e), e, where)   # its runs of string constants, joins (past the cap refused)
            elif isinstance(e.op, ast.Mod): self._join(e, where)   # a `%` of string constants, a join (served_texts)
            # a value slot standing directly as a `%`'s right operand, whether or not a conversion takes it, and a subscript as an
            # operand
            if not isinstance(e.op, ast.Div): self._refuse_operands(e, ctx, where)
            self.resolve(e.left, ctx, label, done); self.resolve(e.right, ctx, label, done)
        elif isinstance(e, ast.BinOp) and _int_arith(e): pass   # a value slot: a Mult or LShift over int constants (2 * 1024, 1 << 20)
        elif isinstance(e, ast.BinOp):
            self._unread(e, "a BinOp %s expression%s" % (type(e.op).__name__, " over an operand that is not an int constant"
                                                         if isinstance(e.op, (ast.Mult, ast.LShift)) else ""), where)
        elif isinstance(e, (ast.Tuple, ast.List)):
            for x in e.elts: self.resolve(x, ctx, label, done)
        elif isinstance(e, ast.IfExp):
            self.resolve(e.body, ctx, label, done); self.resolve(e.orelse, ctx, label, done)
        elif isinstance(e, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):   # the targets read from their source, once per route
            key = ("comprehension", id(e))   # a comprehension read once per route, as a function is: one whose source reads itself stops
            if key in done: return
            done.add(key)
            gens = self._resolve_step(e.generators)
            # the names each target stores (Scan._key_targets): a name it only reads, the base of an attribute or a subscript's container
            # or index there, is no target and is read in the scope around the comprehension
            stores = [[n for n, _ in Scan._key_targets(g.target)] for g in gens]
            cur, bound = ctx, set()
            for i, g in enumerate(gens):   # each generator's source in the context Python evaluates it in (comp_at, the reviewer's 14:42Z ruling)
                # the first in the scope around the comprehension; each later one with the earlier generators' targets bound, and the
                # targets of it and of the generators after it not yet bound, refused as a name a comprehension binds
                unset = {n for ns in stores[i:] for n in ns} - bound if i else set()
                self.comp_at[id(g.iter)] = (cur[0] - unset, cur[1], cls, nested, where, dict(cur[5], **{n: ["comp"] for n in unset})) if unset else cur
                loc = dict(cur[1]); loc.update((n, [g.iter]) for n in stores[i]); self.held.append(loc)
                self.local_at[id(loc)] = {k: self._value_ctx(k, cur) for k in cur[1] if k not in stores[i]}   # the scope around's locals, read there
                bound.update(stores[i])
                cur = (cur[0] - set(stores[i]), loc, cls, nested, where, dict(cur[5], **{n: ["value"] for n in stores[i]}))
            # a target is the comprehension's own local, read from its source in that source's context, and a callee so bound is refused
            # as "a call"
            self.resolve(e.elt, cur, label, done)
        elif isinstance(e, ast.Dict):
            for x in e.keys + e.values:
                if x is not None: self.resolve(x, ctx, label, done)
        elif isinstance(e, ast.Set):
            for x in e.elts: self.resolve(x, ctx, label, done)
        elif type(e) in _NOT_OPERAND: self._unread(e, _NOT_OPERAND[type(e)], where)   # its value is not its operand: refused by name
        elif isinstance(e, (ast.NamedExpr, ast.Starred)): self.resolve(e.value, ctx, label, done)
        elif isinstance(e, ast.BoolOp):
            for x in e.values: self.resolve(x, ctx, label, done)
        elif isinstance(e, ast.Name) and e.id == "__file__" and self.file_bound:   # a statement of the file binds it, in any scope and
            # by any form: refused by name before the scope's or the module's binding is read (_FILE_BOUND)
            self._unread(e, _FILE_BOUND, where)
        elif isinstance(e, ast.Name):
            v = self._scoped(e.id, ctx)
            if v is not None and v[0] == "local":
                oc = self._value_ctx(e.id, ctx)   # the context of the scope that binds it, where its values are read
                key = ("local", id(oc[1]), e.id)   # a local read once per binding scope per route: `x = x.replace(...)` reads itself
                if key in done: return
                done.add(key)
                vals = self._resolve_step(oc[1].get(e.id, ()))   # its values, read once per route
                for val in vals:   # a lambda a value holds is a callee no def statement defines (no call for a
                    # value of another kind, so a chain of aliases costs resolve no frame: _LAMBDA_HOLDERS)
                    if type(val) in _LAMBDA_HOLDERS and _holds_lambda(val): return self._unread(e, _LAMBDA_VALUE, where)
                for val in vals:
                    at = self.comp_at.get(id(val), oc)   # a comprehension's source, in the context Python evaluates it in
                    if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) and val.func.attr in _READ_CALLS:   # a file read bound to a slot
                        self.files.append((label, val.lineno, e.id) + self._path(val.func.value, at, at[1]) + (where, val))
                    else: self.resolve(val, at, label, done)
            elif v is not None:   # a value slot the scope binds (a parameter, an except name) passes; any other form is refused, a
                # function defined in the page function read as a value among them (_FUNC_OBJECT: its text the census does not read)
                if v[0] == "unread" and not self._allowed(where, e):
                    self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                         % (self.rel, e.lineno, ast.unparse(e)[:60], v[1]))
            elif e.id in self.consts:
                if (e.id in self.memos or e.id in self.cmemos and id(e) not in self.cargs) and e.id not in params: self._memo(e.id, e, where)
                elif e.id not in done:
                    done.add(e.id)
                    for val in self._resolve_step((self.consts[e.id],)):   # its one value, read once per route
                        if type(val) in _LAMBDA_HOLDERS and _holds_lambda(val): self._unread(e, _LAMBDA_VALUE, where)   # a callee no def statement defines
                        else: self.resolve(val, (set(), {}, None, {}, e.id, {}), e.id, done)
            elif e.id in params or e.id in nested: pass   # a value slot: a parameter or a name the body binds, a nested function
            elif e.id in self.names or self._global_only(e.id):   # a module-level binding that is no constant (an import or one of the
                # seven builtins a page may call passes; any other builtin, and a function or a class read as a value, _FUNC_OBJECT,
                # refused by name), or a name only a function or class body binds, under a global declaration
                kind, why = self._base(e, ctx)
                if kind == "unread" and not self._allowed(where, e):
                    self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                         % (self.rel, e.lineno, ast.unparse(e)[:60], why))
            elif e.id == "__file__" and not self.star and e.id not in self.rebound:   # the module's own path, which the import system binds
                # (no statement of the file binds it: the arm above): a value slot where it is this file's own path (_file_slot, the
                # predicate _path's `Path(__file__)` and `open(__file__)` read too), so here where the file writes no name of its module
                # namespace through a computed name and may not rewrite it at run time, and refused otherwise with that file's reason
                if not self._file_slot(): self._unread(e, self.computed_why, where)
            elif e.id in _IMPORT_NAMES:   # the module's own docstring, name, package, spec or loader, which the import system binds: no builtin
                self._unread(e, _IMPORT_WHY, where)
            else:   # a name bound nowhere the census reads
                self.problems.append("SERVED %s:%d builds a served page from %s, text the census did not read" % (self.rel, e.lineno, ast.unparse(e)[:60]))
        elif isinstance(e, ast.Call):
            f = e.func
            if isinstance(f, ast.Attribute) and f.attr == "join" and not e.keywords and (
                    (len(e.args) == 1 and self._set_value(e.args[0], ctx))   # `"".join({...})`, `"".join(d)` with `d = {...}`
                    or (len(e.args) == 2 and self._set_value(e.args[1], ctx))):   # unbound, `str.join("", {...})`
                return self._unread(e, _JOIN_SET, where)   # a set's iteration order is not fixed, so its join is no one text
            if _unbound_text_call(e): return self._unread(e, _UNBOUND, where)   # `str.join("", [...])`: not folded, so refused, not read apart
            if isinstance(f, ast.Name) and f.id == "__file__" and self.file_bound: return self._unread(e, _FILE_BOUND, where)   # a callee so bound
            if isinstance(f, ast.Name) and f.id in _NUMBER_LEAVES and self._scoped(f.id, ctx, callee=True) is None and self._builtin(f.id):
                return   # int or float, the builtin: a number-valued leaf, its argument not read here (the 14:42Z ruling)
            # decision 2, before the file-read and text-call arms: every call _method_call takes is refused by name (a method called
            # on the calling method's own first parameter, which a subclass another file defines may override, with the reason that
            # names what the census found first; a route class's method on self through anything else or on a parameter; a name the
            # file stores as an attribute on a parameter; any other method on self through anything else)
            how = self._method_call(f, ctx) if isinstance(f, ast.Attribute) else None
            if how is not None: self._unread(e, how[1], where)
            elif isinstance(f, ast.Name) and f.id in _NUMBER_LEAVES: self._unread(e, _NUMBER_REBOUND, where)   # bound other than to the builtin
            elif isinstance(f, ast.Attribute) and f.attr in _READ_CALLS:   # a file read: its path proven by binding in the read's context
                self.files.append((label, e.lineno, ast.unparse(f.value)[:40]) + self._path(f.value, ctx) + (where, e))
            elif isinstance(f, ast.Attribute) and f.attr in _TEXT_CALLS + _FOLLOW_ANY and _text_shape(e):   # a shape _const_text does not fold
                self._unread(e, _TEXT_SHAPE % (f.attr, _text_shape(e)), where)
            elif isinstance(f, ast.Attribute) and f.attr in _TEXT_CALLS + _FOLLOW_ANY:
                refused = self._join(e, where); self._refuse_operands(e, ctx, where)   # a join of string constants among them; the operands' refusals
                # the format string's fields, read through the receiver, asked only of a call _join did not refuse as _WIDE or _NESTED
                # (one reason a node): `"{0.CSS}".format(Handler)` and `_T.format(d, Other)` with `_T = "{0:{1.W}}"` reach the
                # argument's attribute (_FIELD_REACH); `_T.strip().format(Handler)` is a format string reached other than as a
                # string constant, a join of them or a name bound to one (_TEMPLATE, below)
                why = None if refused else self._field_reach(e, ctx)
                if why == _FIELD_REACH: self._unread(e, _FIELD_REACH, where)
                # `Cls.format(...)`, `_REG.get(k).format(...)`, `(A or B).replace(...)`, `t.strip()` in a loop over classes: a class
                # the class walk resolves the receiver to (_class_value: through its own name, a name the census resolves to it, a
                # method call on or a subscript of a name whose value holds one or of such a value itself, or an if-expression, a
                # boolean operation or a walrus over those), or a receiver on whose path no attribute is read whose root by binding is
                # a class (_value_class), whose method is a class attribute, not a text receiver, save a receiver refused already as a
                # subscript operand (op_refused); a receiver standing on such a class further down (an attribute of it, a method called
                # on that: `Handler.X.format(...)`) is refused where resolve reads that part (receiver, _class_root, _attr_root)
                if id(f.value) not in self.op_refused and (self._class_value(f.value, ctx) or self._value_class(f.value, ctx)):
                    self._unread(e, _CLASS_ATTR, where)
                else:   # _TEMPLATE, save where the receiver stands refused already: as a subscript operand (_SUB_OPERAND, op_refused),
                    # or by any refusal the pass makes as it reads the receiver (`self.X.format(...)`, `Handler.X.format(...)`), whose
                    # line stands for the text it holds: one gap, one line
                    n = len(self.problems)
                    self.resolve(f.value, ctx, label, done)
                    if why == _TEMPLATE and id(f.value) not in self.op_refused and len(self.problems) == n: self._unread(e, _TEMPLATE, where)
            elif isinstance(f, ast.Name) and self._scoped(f.id, ctx, callee=True) is not None:   # a callee the scope binds: never the module's
                kind, why = self._scoped(f.id, ctx, callee=True)
                if kind == "follow":   # a function defined inside the page function, the name's one binding there, over its names
                    key, fn = ("nested", id(nested[f.id])), nested[f.id]
                    held = self.def_ctx.get(id(fn))   # (the function, the context its def statement stands in, the def that holds it)
                    why = self._def_shape(fn) or (self._def_uses(fn, held[2]) if held is not None else _DEF_ALIAS)   # layer ii: a plain def
                    if why is not None: self._unread(e, why, where)
                    else:
                        if key not in done:
                            done.add(key)
                            for r in self._resolve_step(self._returns(fn)): self.resolve(r, self._ctx(fn, cls, held[1], where + "." + f.id), label + "." + f.id, done)
                        self._defaults(e, fn, held[1], label + "." + f.id, done)
                elif kind != "exempt" and not self._allowed(where, e):
                    self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                         % (self.rel, e.lineno, ast.unparse(e)[:60], why))
            elif isinstance(f, ast.Name) and f.id in self.funcs and self._sole(f.id):   # a module function, the name's one module-level binding
                fn = self.funcs[f.id]
                why = self._def_shape(fn) or self._def_uses(fn, None)   # layer ii: followed only as a plain def
                if why is not None: self._unread(e, why, where)
                else:
                    if f.id not in done:
                        done.add(f.id)
                        for r in self._resolve_step(self._returns(fn)): self.resolve(r, self._ctx(fn, None, None, f.id), f.id, done)
                    self._defaults(e, fn, (set(), {}, None, {}, f.id, {}), f.id, done)
            elif isinstance(f, ast.Attribute): self.receiver(f.value, e, ctx, label, done, call=True)   # any other method call: its receiver, for a method drawn from its text (_undrawn)
            else:   # any other callee: an import, one of the seven builtins a page may call or a parameter passes (_base), anything
                # else, any other builtin among them, is refused by name
                kind, why = self._base(e, ctx)
                if kind != "exempt" and not self._allowed(where, e):
                    self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                         % (self.rel, e.lineno, ast.unparse(e)[:60], why))
            self.cargs.update(id(a) for a in e.args + [k.value for k in e.keywords] if isinstance(a, ast.Name))   # layer iv: the call limit's names
            for a in e.args + [k.value for k in e.keywords]: self.resolve(a, ctx, label, done)   # a value slot's arguments are text too (json.dumps(x))
        elif isinstance(e, ast.Subscript):
            # already refused by name as an operand of a +, %, f-string or join whose joined text the pass does not compute
            # (_refuse_operands, _SUB_OPERAND): read nothing, so the container's pieces the join selects are not scanned apart
            if id(e) in self.op_refused: return
            # a slice of any shape, or an index that is no constant (a name, a call, a tuple, a negative number, which parses as a
            # UnaryOp), over a container whose text the pass reads (_carries_text) is refused by name: the pass reads the container
            # whole and does not compute what the index selects, so only a constant index reads it; a value slot passes (receiver)
            # and so over a container whose own text it does not read that derives through a call handed arguments it reads as text
            # (_chain_text: `str(X)[::-1]`, `dict(a=X)["a"][1:]`), which it reads whole and does not slice either (_sliced, the rule
            # receiver applies to each subscript on such a base's path too)
            if self._sliced(e, ctx): return self._unread(e, _SLICED, where)
            self.receiver(e.value, e, ctx, label, done)
        elif isinstance(e, ast.Attribute):
            base = e.value
            if isinstance(base, ast.Name) and base.id == "__file__" and self.file_bound:   # a statement binds it: refused before
                self._unread(e, _FILE_BOUND, where); return   # receiver takes a class so named (_FILE_BOUND)
            # any other base goes to receiver as the attribute's base (each operand of a BoolOp so), which refuses an attribute read
            # on a class, through the class's own name or a name the census resolves to one (_class_root, _CLASS_ATTR), and then by
            # the base's root, read by binding (_attr_root): self, a class, a parameter, an except name, or a root reached as a name's
            # value that _base refuses
            self.receiver(base, e, ctx, label, done, True)
        elif isinstance(e, ast.Lambda):   # one standing in the page (a lambda a name's value holds is refused where the name is read:
            # _LAMBDA_VALUE): its body is page text (a replacement function's return), its parameters value slots
            a = e.args
            for d in a.defaults + [d for d in a.kw_defaults if d is not None]: self.resolve(d, ctx, label, done)   # run where it stands
            lp = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs} | ({a.vararg.arg} if a.vararg else set()) | ({a.kwarg.arg} if a.kwarg else set())
            loc = {k: v for k, v in local.items() if k not in lp}; self.held.append(loc)
            self.local_at[id(loc)] = {k: self._value_ctx(k, ctx) for k in loc}   # each local the scope around binds, read there (_value_ctx)
            self.resolve(e.body, (params | lp, loc, cls, {k: v for k, v in nested.items() if k not in lp}, where,
                                  dict(scope, **{p: ["param"] for p in lp})), label, done)
        else:   # every other kind (a Compare, a UnaryOp and a kind with no arm above): no text the census reads; a subscript's index
            # never reaches resolve, the Subscript arm above deciding it (_SLICED)
            self._unread(e, "a%s %s expression" % ("n" if type(e).__name__[0] in "AEIO" else "", type(e).__name__), where)

    def _unread(self, e, why, where, line=None, shown=None):
        """A page position holding a kind resolve does not read (the kind named in `why`): a SERVED line at its line, or at `line`,
        showing the expression, or `shown`, unless SERVED_ALLOW names the place."""
        if not self._allowed(where, e):
            self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                 % (self.rel, e.lineno if line is None else line, (ast.unparse(e) if shown is None else shown)[:60], why))

    def run(self, routes):
        self._stores()   # once per file, before any route is read (_replaced, _method_call)
        # the route classes' method names, once per file (_method_call), from each route class's class statement (routes_of hands the
        # statement, never its name alone: choice 1 of the eleventh round's rulings)
        self.route_methods = self._route_methods(list({id(r[2]): r[2] for r in routes if r[2] is not None}.values()))
        for call, fn, cls, ctype, body in routes:   # the body routes_of read: the call's second positional argument
            before = len(self.pieces), len(self.files)
            where = ((cls.name + ".") if cls is not None else "") + fn.name if fn is not None else "<module>"   # the class's own spelling
            ctx = self._ctx(fn, cls, None, where, True) if fn is not None else (set(), {}, cls, {}, "<module>", {})
            self.resolve(body, ctx, fn.name if fn is not None else "<module>", self._route_done())   # the route's own visited set
            if (len(self.pieces), len(self.files)) == before:
                self.problems.append("SERVED %s:%d serves %s from %s, text the census did not read"
                                     % (self.rel, call.lineno, ctype.split(";")[0], ast.unparse(body)[:60]))


def _read_once(r, rel):
    """The records one line_scan call left in a scratch Result, each (its kind, its line-free identity, the record): a site by its
    tool, road and class, and a fetch's, an import()'s or a program's also by its head (the argument or argv read); a DOM load by
    its kind; a gate read by its specifier; a problem by its message with its line number dropped; a JS_ALLOW hit by its key."""
    sites = [("site", (s.prim, s.road, s.cls, s.kind) + ((s.head,) if s.prim in ("fetch", "import()", "install.sh") + CP_FAMILY else ()), s)
             for s in r.sites]
    probs = [("problem", re.sub(r"^(\S+ %s):\d+ " % re.escape(rel), r"\1: ", p), p) for p in r.problems]
    return (sites + [("dom", d[2], d) for d in r.dom] + [("read", x[2], x) for x in r.reads] + probs
            + [("allow", k, (k, pos)) for k in r.allow_hits for pos in sorted(r.allow_hits[k])])


def served_texts(rel, tree, routes, res):
    """The served pages' pass over one Python file: every piece the routes reach scanned as browser text with the DOM arm on,
    keyed file plus tool at the part's own line and read once per part (the part's position, never its line and text); and the
    text of each join _Served._note records (a `+` or f-string's run of string constants, a `%` of them, and a `.join` over a list,
    tuple or dict literal, a `.format`, `.format_map` or `.replace` of them, each called on a string constant or on such a join;
    the same methods called on the name str, bytes or bytearray are no such join, refused by name) scanned too, at its first
    literal's line, each record it finds
    beyond what its
    literals' own reads find added, so a load split across such a join is read and a site both reads find is listed once (a `.join`
    over a set, or over a local or a module constant the census reads by its binding from one (_Served._set_value), called on a string
    or unbound as in `str.join("", {...})`, whose order is not fixed, is no such join: resolve refuses it by name; one over a set a
    call returns or a parameter takes, as its argument or its default, is read piece by piece under the join limit; a fetch
    or import() argument, or a program call's arguments, that run past a joined literal's end are left to the join's text, which
    reads them whole: line_scan's `cut`); a file
    a page reads at run time is covered by the walk only where the walk scanned it as browser text (_browser_text: JavaScript under
    the browser and editor roots, the DOM arm on; not scanned again), named when it is a stylesheet the walk does not scan, excused
    when SERVED_ALLOW names the read, and a SERVED problem otherwise, its reason the kind the walk scanned the file as, Python, shell
    or JavaScript with the DOM arm off (_FILE_KINDS: layer v of the eleventh round's rulings, none counted as covered unread), or the conjunct of _path's
    proof by binding that fails (_PATH_UNPROVEN), or a file the walk does not scan."""
    sv = _Served(rel, tree, res); sv.run(routes)
    got = {}
    for label, lineno, text, part in sv.pieces: got.setdefault(part, (lineno, text))   # each part read once, at its position
    joins = [(keys, text) for ks, (keys, text) in sv.joins.items() if ks <= set(got) and not any(ks < other for other in sv.joins)]
    cut = {k for keys, _ in joins for k in keys}   # the literals a join carries on
    for part, (lineno, text) in sorted(got.items(), key=lambda p: (p[1][0], p[1][1], p[0])):
        line_scan(rel, "js", text, res, base=lineno - 1, dom=True, served=True, cut=part in cut)
    for keys, text in sorted(joins, key=lambda j: (got[j[0][0]][0], j[1], j[0])):   # each join's text, beside its literals' own reads
        whole, alone = Result(), Result()
        line_scan(rel, "js", text, whole, base=got[keys[0]][0] - 1, dom=True, served=True)
        for k in dict.fromkeys(keys): line_scan(rel, "js", got[k][1], alone, base=got[k][0] - 1, dom=True, served=True, cut=True)
        left = {}
        for kind, ident, _ in _read_once(alone, rel): left[(kind, ident)] = left.get((kind, ident), 0) + 1
        for kind, ident, rec in _read_once(whole, rel):
            if left.get((kind, ident)): left[(kind, ident)] -= 1; continue   # found by the literals' own reads too: listed once
            if kind == "site": res.sites.append(rec)
            elif kind == "dom": res.dom.append(rec)
            elif kind == "read": res.reads.append(rec)
            elif kind == "problem": res.problems.append(rec)
            else: res.allow_hits.setdefault(rec[0], set()).add(rec[1])
    for label, lineno, name, path, why, where, expr in sorted(sv.files, key=lambda f: (f[1], f[6].col_offset)):
        kind = res.kinds.get(path) if path is not None else None   # the kind the walk scanned it as, None for a file it did not walk
        if kind is not None:   # a walked file: covered where the walk scanned it as browser text, else refused by that kind
            if _browser_text(path, kind):
                named, enc = _read_codec(expr)   # the walk scanned it once as UTF-8: a read with an encoding the census does not read
                # as UTF-8 may serve text the scan did not (_READ_CODEC); a read that names no encoding is the stated limit (u7c)
                if not named or (isinstance(enc, ast.Constant) and type(enc.value) is str and enc.value.lower() in _UTF8_NAMES): continue
                why = _READ_CODEC
            else: why = _FILE_KINDS[kind]
        elif path is not None and path.endswith(".css"):   # a stylesheet the walk does not scan: named
            if (rel, lineno, path) not in res.served_files: res.served_files.append((rel, lineno, path))
            continue
        if not sv._allowed(where, expr):
            res.problems.append("SERVED %s:%d reads %s for a served page, %s" % (rel, lineno, path or name, why or "a file the walk does not scan"))
    res.problems.extend(sv.problems); res.served.append(rel)


def _text_shape(e):
    """Why the text-method arm refuses the call `e`, a .replace, .format, .join, .format_map or .encode (resolve's Call arm), by its
    shape, or None (the eleventh round's rulings: the reviewer's 14:42Z item 2, and his 16:33Z E1 and E3): a .replace other than with
    two positional arguments (a count, a keyword or a starred argument); a .format or a .join with a starred argument or a ** keyword;
    a .format_map other than with one positional argument that is a dict literal whose keys are each a string constant (a name, a
    call and a ** item among the refused); an .encode other than with no argument or with one string constant that, lower-cased, is
    one of _UTF8_NAMES, utf-8, utf_8 or utf8, and no other encoding (an errors argument among the others: a handler
    codecs.register_error names writes any text in place of a character UTF-8 cannot encode, the road the (t) plant tch holds in a
    _send definition; any other spelling, one CPython also encodes as UTF-8, `utf 8` or `UTF--8`, refused on the safe side, and one
    it hands to the codec registry, `u-t-f-8` or `U_T_F_8`, where a search function codecs.register adds may answer it; and an
    encoding that is no string constant, a name bound to "utf-8" among them, which the census does not fold). _const_text folds
    none of these shapes, so reading
    the receiver's text as the page's would take text the call does not return; a .replace of names stays the stated join limit."""
    a, kw, attr = e.args, e.keywords, e.func.attr
    starred = any(isinstance(x, ast.Starred) for x in a)
    if attr == "replace":
        if len(a) != 2 or kw or starred: return "with a count, a keyword or a starred argument"
    elif attr in ("format", "join"):
        if starred or any(k.arg is None for k in kw): return "with a starred argument or a ** keyword"
    elif attr == "format_map":
        if len(a) != 1 or kw or starred: return "other than with one positional argument"
        if not isinstance(a[0], ast.Dict): return "over anything but a dict literal"
        if isinstance(a[0], ast.Dict) and not all(isinstance(k, ast.Constant) and type(k.value) is str for k in a[0].keys):
            return "over a dict literal whose keys are not each a string constant"
    elif attr == "encode":
        enc = list(a) + [k.value for k in kw if k.arg == "encoding"]
        if len(enc) > 1 or starred or any(k.arg != "encoding" for k in kw): return "with an argument other than one encoding"
        if enc and not (isinstance(enc[0], ast.Constant) and type(enc[0].value) is str and enc[0].value.lower() in _UTF8_NAMES):
            return "with an encoding the census does not read as utf-8, utf_8 or utf8"
    return None


def _imports_page(importer, stmt, page):
    """Whether the import statement `stmt` (its line, its level, its module or None, the names it imports or None: Result.imports_of)
    of the walked Python file `importer` may bind the module of the walked Python file `page`, whose path less its suffix is its
    module's (a package's `__init__` the package): a relative import where that path, taken from the importing file's directory
    (up one directory for each level past the first), is the module, a package it imports on the way, or the module and a name it
    imports, or where it is a star import from the page's own package; an absolute import where the page's path ends with its dotted
    module, a package on the way, or the module and a name it imports (the root it is found from being unknown), or where it is a
    star import and the page's package path ends with its module."""
    _line, level, module, names = stmt
    mod = (page[:-3] if page.endswith(".py") else page).split("/")
    if mod[-1] == "__init__": mod = mod[:-1]
    parts, names = (module.split(".") if module else []), names or ()
    if level:
        base = importer.split("/")[:-1]
        if level - 1 > len(base): return False
        top = len(base) - level + 1
        full = base[:top] + parts
        paths = [full[:i] for i in range(top, len(full) + 1)] + [full + [x] for x in names if x != "*"]
        return any(p == mod for p in paths) or "*" in names and mod[:-1] == full
    paths = [parts[:i] for i in range(1, len(parts) + 1)] + [parts + [x] for x in names if x != "*"]
    return any(mod[-len(p):] == p for p in paths) or "*" in names and mod[:-1][-len(parts):] == parts


def _page_importers(res):
    """The refusal of a page module another walked file imports (an escape refused where one check does it at 0 live, the 00:28Z
    rule; the eleventh round's rulings order it by no name, their choice 4 being a page's reach through another file's
    definition the census does not read): a SERVED line for each walked Python
    file holding a route candidate (Result.candidates, at the line of its first) whose module an import statement of another walked
    Python file may bind (_imports_page over Result.imports_of, the first such file by path and its first such statement), since the
    served pass's and the route typing's proofs by binding read the page's own file alone (a module constant bound once, a container
    never changed, a function never rebound, a builtin never shadowed) and the importing file may rebind or change the module's names
    at run time. A module reached any other way (sys.modules, a loader by path, a function's `__globals__`, an object the module hands
    to other code) is not seen: the stated limit, its witness the (xi) plant xw."""
    out = []
    for page in sorted(res.candidates):
        hit = next(((b, s) for b in sorted(res.imports_of) if b != page for s in sorted(res.imports_of[b], key=lambda s: s[0])
                    if _imports_page(b, s, page)), None)
        if hit is None: continue
        b, (line, level, module, names) = hit
        shown = "import %s" % module if names is None else "from %s%s import %s" % ("." * level, module or "", ", ".join(names))
        out.append("SERVED %s:%d serves pages from a module that %s:%d imports (%s), whose code may rebind or change at run time the "
                   "module names the census reads the pages and their content types through" % (page, res.candidates[page], b, line, shown[:60]))
    return out


def scan(root):
    res = Result(); bootstrap = None; served = []
    for rel, kind in walk(root, res):   # each file's text is read once here: a Python file strictly, the others with replacement
        res.files.append(rel); res.kinds[rel] = kind   # the kind the walk scans it as, which the served pass reads (served_texts)
        with open(os.path.join(root, rel), encoding="utf-8", errors=None if kind == "py" else "replace") as fh: text = fh.read()
        if rel == "bootstrap.sh": bootstrap = text   # the one-liner pass below reads the text its line scan read
        if kind != "py": line_scan(rel, kind, text, res); continue
        try: tree = ast.parse(text)
        except SyntaxError as e:
            res.problems.append("PARSE %s:%s does not parse (%s)" % (rel, e.lineno, e.msg)); continue
        sc = Scan(rel, res); sc.visit(tree)
        for mod, line in sc.imports:
            if mod not in KNOWN_IMPORTS:
                res.problems.append("IMPORT %s:%d imports %s, a module the census does not know: a client that opens connections takes its "
                                    "primitives into NET or SUB; either way add it to KNOWN_IMPORTS with the reason" % (rel, line, mod))
        if sc.routes: served.append((rel, tree, sorted(sc.routes, key=lambda r: r[0].lineno)))   # the served pass runs after the walk: a file slot is checked against res.files
    res.problems.extend(_page_importers(res))   # a page module another walked file imports, once every file's imports are read
    for rel, tree, routes in served: served_texts(rel, tree, routes, res)
    if bootstrap is not None:
        for ln in bootstrap.split("\n"):   # the documented one-liner: the user's own curl of this script is a road too
            if ln.startswith("#") and "curl" in ln and "bootstrap.sh | bash" in ln:
                res.emit("bootstrap.sh", 3, "curl", "the documented one-liner: " + ln.strip("# \n")[:50], "-", T["bootstrap.sh:curl"], None, "sh")
    res.sites.sort(key=Site.tuple)
    return res


def js_reads(root):
    """The walked JavaScript and TypeScript files and what the import gate reads in them, for the webview leg's pin
    (ui/webview/import-gate-parse.test.ts), which holds the reads equal to a TypeScript parse of the same files: the walk, and
    line_scan over each file of the js kind as scan reads it, with no Python scan and no served pass (the --js-reads mode).
    Returns (the files in the walk's order, the Result line_scan filled)."""
    res = Result(); files = []
    for rel, kind in walk(root, res):
        if kind != "js": continue
        files.append(rel)
        with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh: text = fh.read()
        line_scan(rel, kind, text, res)
    return files, res


def figures(res):
    """The committed counts: every figure a run is compared against."""
    per_road, per_key, heads, classes, kinds = {}, {}, {}, dict.fromkeys(CLASSES, 0), {"py": 0, "js": 0, "sh": 0}
    for s in res.sites:
        kinds[s.kind] += 1; per_key[s.key()] = per_key.get(s.key(), 0) + 1
        if s.road: per_road[s.road] = per_road.get(s.road, 0) + 1
        if s.cls: classes[s.cls] += 1
        if s.kind == "py" and s.prim.split(" ")[0] in SUB.values():   # the program head per row key, Python command sites only
            h = "RUNTIME-SUPPLIED" + (" SHELL" if s.head.endswith(" SHELL") else "") if s.head.startswith("RUNTIME-SUPPLIED") else s.head
            k = "%s %s %s" % (s.key(), s.prim, h); heads[k] = heads.get(k, 0) + 1
    classes["browser-dom-loads"] = len(res.dom)
    roads = set(per_road)
    return {"sites": len(res.sites), "roads": len(roads), "local_roads": len(roads & LOCAL_ROADS),
            "local_sites": sum(1 for s in res.sites if s.road in LOCAL_ROADS and s.cls is None),
            "kinds": kinds, "classes": classes, "per_road": per_road, "per_key": per_key, "heads": heads}


def problems(root, res, fig, expected):
    out = list(res.problems)
    if not res.sites: out.append("NO SITES found: the scan is broken or the roots moved")
    bad = ["%s:%d" % (s.file, s.line) for s in res.sites if s.road is None and s.cls != "browser-computed-url"]
    if bad: out.append("UNCLASSIFIED " + " ".join(bad) + ": a site with no road; add a row to T with its reason (an external program is never local by "
                       "default), and a new road reaches SECURITY.md's Network access section and the ledger entry's table (--table) too")
    keys = {s.key() for s in res.sites}
    for k in sorted(set(T) - keys): out.append("STALE ROW %s names no site: drop it from T (a row for a site that is gone is never a pass)" % k)
    for k in sorted(set(SERVED_ALLOW) - set(res.allow_hits)):
        out.append("SERVED ALLOW %s %r names nothing this run reads: drop it from SERVED_ALLOW (an entry for code that is gone is never a pass)" % k)
    for k in sorted(set(SERVED_ALLOW) & set(res.allow_hits)):
        if len(res.allow_hits[k]) != SERVED_ALLOW[k][0]:
            out.append("SERVED ALLOW %s %r covers %d places, the entry says %d: a new place under an entry's key is read or named, never excused "
                       "by the key" % (k + (len(res.allow_hits[k]), SERVED_ALLOW[k][0])))
    for k in sorted(set(SERVED_LISTED) - set(res.allow_hits)):
        out.append("SERVED LISTED %s %r names nothing this run refuses: drop it from SERVED_LISTED (an entry for code that is gone is never "
                   "a pass)" % k)
    for k in sorted(set(SERVED_LISTED) & set(res.allow_hits)):
        if len(res.allow_hits[k]) != SERVED_LISTED[k][0]:
            out.append("SERVED LISTED %s %r covers %d places, the entry says %d: a new place under an entry's key is read or refused, never "
                       "listed by the key" % (k + (len(res.allow_hits[k]), SERVED_LISTED[k][0])))
    for k in sorted(set(FRAME_WRITERS) - {h[1] for h in res.allow_hits if h[0] == "frame"}):
        out.append("SERVED ALLOW %s is named in FRAME_WRITERS and no `_send` call reaches it: drop it (an entry for code that is gone is never "
                   "a pass)" % k)
    for k in sorted(set(JS_ALLOW) - set(res.allow_hits)):
        out.append("IMPORT ALLOW %s %r names nothing this run reads: drop it from JS_ALLOW (an entry for code that is gone is never a pass)" % k)
    for k in sorted(set(JS_ALLOW) & set(res.allow_hits)):
        if len(res.allow_hits[k]) != JS_ALLOW[k][0]:
            out.append("IMPORT ALLOW %s %r covers %d places, the entry says %d: a new place under an entry's key is read or named, never excused "
                       "by the key" % (k + (len(res.allow_hits[k]), JS_ALLOW[k][0])))
    table ={r[0] for r in ROADS}; roads = set(fig["per_road"])
    for r in sorted(roads - table - LOCAL_ROADS): out.append("TABLE the road %s has sites and no ROADS entry (its trigger, what it sends and its switch; "
                                                             "SECURITY.md's Network access section and the ledger's table follow from it)" % r)
    for r in sorted(table - roads): out.append("TABLE ROADS names %s, a road with no site" % r)
    for r in sorted(set(T.values()) - table - LOCAL_ROADS): out.append("TABLE the row road %s has no ROADS entry" % r)
    if expected is None:
        out.append("COUNTS %s is missing: run --write-expected on a clean tree and commit it" % EXPECTED)
    else:
        for name in ("sites", "roads", "local_roads", "local_sites"):
            if expected.get(name) != fig[name]: out.append("COUNTS %s: the committed count is %s, this run found %s" % (name, expected.get(name), fig[name]))
        for group in ("kinds", "classes", "per_road", "per_key", "heads"):
            e, f = expected.get(group) or {}, fig[group]
            for k in sorted(set(e) | set(f)):
                if e.get(k) != f.get(k): out.append("COUNTS %s %s: the committed count is %s, this run found %s" % (group, k, e.get(k), f.get(k)))
    return out


def render_sites(res, fig, out):
    for s in res.sites:
        tag = s.road or ("(%s)" % s.cls if s.cls == "browser-computed-url" else "UNCLASSIFIED")
        if s.cls and tag != "(%s)" % s.cls: tag += " [%s]" % s.cls
        out.write("%s:%d  %s  %s  in %s  -> %s\n" % (s.file, s.line, s.prim, s.head, s.fn, tag))
    for rel, i, name, s in res.dom: out.write("%s:%d  dom-load  %s  %s  -> (browser-dom-loads)\n" % (rel, i, name, s))
    for rel, i, path in res.served_files: out.write("%s:%d  served-file  %s  -> (a stylesheet a served page reads: named, not scanned)\n" % (rel, i, path))
    for k in sorted(k for k in SERVED_LISTED if k in res.allow_hits):   # refused, and listed with the entry's reason (SERVED_LISTED)
        rel, fn = k[0].split(":", 1)
        for i, _col in sorted(res.allow_hits[k]):
            out.write("%s:%d  served-refused  %s  in %s  -> (refused and listed: %s)\n" % (rel, i, k[1], fn, SERVED_LISTED[k][1]))
    c = fig["classes"]
    out.write("--- %d sites, %d roads (%d of them local), %d local sites set aside, %d unclassified; %d external-program, %d runtime-program, "
              "%d browser-computed-url, %d browser-dom-loads; %d files scanned, %d skipped by kind\n"
              % (fig["sites"], fig["roads"], fig["local_roads"], fig["local_sites"],
                 sum(1 for s in res.sites if s.road is None and s.cls != "browser-computed-url"), c["external-program"], c["runtime-program"],
                 c["browser-computed-url"], c["browser-dom-loads"], len(res.files), res.skipped))


def _where(sites):
    by = {}
    for s in sites: by.setdefault(s.file, set()).add(s.fn if s.fn != "-" else "(%s)" % s.prim)
    cells = []
    for f in sorted(by):
        fns = sorted(x for x in by[f] if not x.startswith("(")); tools = sorted(x[1:-1] for x in by[f] if x.startswith("("))
        cells.append(f + (" " + ", ".join("`%s`" % x for x in fns) if fns else "") + (" (" + ", ".join("`%s`" % x for x in tools) + ")" if tools else ""))
    return "; ".join(cells)


def _programs(sites):
    by = {}
    for s in sites:
        text = s.prim if s.kind == "sh" else s.head   # a shell site's program is its tool (`python3 -c`); its head is the line
        head = text.split(" SHELL")[0]
        label = ("an argv the code does not spell out" if head.startswith("RUNTIME-SUPPLIED") else "`git` with a subcommand the code does not spell out"
                 if head == "git" else "`%s` with `shell=True`" % head if " SHELL" in text else "`%s`" % head)
        by[label] = by.get(label, 0) + 1
    return ", ".join("%s %d" % (k, by[k]) for k in sorted(by, key=lambda k: (-by[k], k)))


def render_table(res, fig, out):
    out.write("| road | where | trigger and cadence | what is sent and to where | off switch |\n|---|---|---|---|---|\n")
    for road, label, trigger, sent, off in ROADS:
        out.write("| %s | %s | %s | %s | %s |\n" % (label, _where([s for s in res.sites if s.road == road]), trigger, sent, off))
    out.write("| %s | %s | %s | %s | %s |\n" % SVG_TAB_ROW)   # named and not counted: the opened document's own loads
    local = [s for s in res.sites if s.road in LOCAL_ROADS and s.cls is None]
    counts = ", ".join("%s %d" % (r, sum(1 for s in local if s.road == r)) for r in sorted(LOCAL_ROADS))
    out.write("| %s | %d sites on the %d local roads (%s), %s | %s | %s | %s |\n" % (LOCAL_ROW[0], len(local), fig["local_roads"], counts, LOCAL_ROW[1], LOCAL_ROW[2], LOCAL_ROW[3], LOCAL_ROW[4]))
    ext = [s for s in res.sites if s.cls == "external-program"]; rt = [s for s in res.sites if s.cls == "runtime-program"]
    comp = [s for s in res.sites if s.cls == "browser-computed-url"]
    files = sorted({rel for rel, _i, _n, _s in res.dom}); kinds = {}
    for _rel, _i, name, _s in res.dom: kinds[name] = kinds.get(name, 0) + 1
    where = {"external-program": "%d sites, by program: %s" % (len(ext), _programs(ext)),
             "runtime-program": _where(rt) + " (%d sites)" % len(rt),
             "browser-computed-url": "%d sites: %s" % (len(comp), "; ".join("%s `%s`" % (s.file, s.head) for s in comp)),
             "browser-dom-loads": "%d lines in %d files under %s%s (%s)" % (len(res.dom), len(files), " and ".join(JS_ROOTS),
                                   (" and in the pages %s serves" % " and ".join(sorted(res.served))) if res.served else "",
                                   ", ".join("%s %d" % (k, kinds[k]) for k in sorted(kinds)))}
    for cls in CLASSES:
        label, trigger, sent, off = CLASS_ROWS[cls]
        out.write("| %s | %s | %s | %s | %s |\n" % (label, where[cls], trigger, sent, off))
    out.write("| %s | %s | %s | %s | %s |\n" % PAINT_ROW)   # named and not counted, beside the browser-dom-loads row
    out.write("| %s | %s | %s | %s | %s |\n" % UNSEEN_ROW)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]; flags = {a for a in argv if a.startswith("--")}
    unknown = flags - {"--table", "--write-expected", "--js-reads"}
    if unknown or len(args) > 1 or ("--js-reads" in flags and len(flags) > 1):
        sys.stderr.write("usage: network-inventory.py [--table | --write-expected | --js-reads] [root]\n"); return 2
    root = os.path.abspath(args[0] if args else ".")
    if "--js-reads" in flags:   # the walk and the JavaScript line scan alone: no figure, no gate but a missing root
        files, res = js_reads(root)
        scope = [p for p in res.problems if p.startswith("SCOPE")]
        if scope:
            sys.stderr.write("\n".join(scope) + "\n"); return 1
        json.dump({"files": files, "reads": res.reads, "unread": res.unread,
                   "computed": [[s.file, s.line] for s in res.sites if s.prim == "import()" and s.cls == "browser-computed-url"]}, sys.stdout)
        sys.stdout.write("\n"); return 0
    res = scan(root); fig = figures(res)
    path = os.path.join(root, EXPECTED); expected = None
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as fh: expected = json.load(fh)
    probs = problems(root, res, fig, expected)
    if "--write-expected" in flags:
        hard = [p for p in probs if not p.startswith("COUNTS")]
        if hard:
            sys.stdout.write("\n".join(hard) + "\nnot written: %s (the run is not clean)\n" % EXPECTED); return 1
        with open(path, "w", encoding="utf-8") as fh: json.dump(fig, fh, indent=1, sort_keys=True); fh.write("\n")
        sys.stdout.write("wrote %s: %d sites, %d roads\n" % (EXPECTED, fig["sites"], fig["roads"])); return 0
    if "--table" in flags: render_table(res, fig, sys.stdout)
    else: render_sites(res, fig, sys.stdout)
    if probs:
        (sys.stderr if "--table" in flags else sys.stdout).write("\n".join(probs) + "\n"); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

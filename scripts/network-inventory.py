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
file, direct in the call's own class body (a call through self) or in the module (a bare call): the kernel's Handler._send
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
not bind, for a call through self: inherited or set at run time; one reached through an object other than self, or through an
attribute outside any class body; a
`_send` no scope the bare call looks it up in binds, the module included; and, in a file that names `_send` nowhere but as the
called name of those calls, so binds it nowhere at all, a definition the file does not hold), each call to a definition carrying
any decorator, whose parameters the census does not read,
and each bare call in a module that holds a star import. An
override of `_send` in a subclass that another file defines is not read: a call through self is typed through its own class body's
definition. The type is read
through a module name no code writes after binding it (one plain single-name assignment binds it as a top-level statement, nothing
else at module level binds it, a walrus in a def's or a class's header included, the module holds no star import, and nothing in
the file writes that name,
in any scope: a subscript store or delete, a call `<name>.<method>(` of a method _MUTATORS or _DUNDER_MUTATORS lists, a call of
such a method on a type _CONTAINER_TYPES lists with the name as its first argument (`dict.update(<name>, ...)`), a binding in a
function that declares the name `global` (as the target of an assignment, an augmented assignment, a loop, a comprehension, a
with or a walrus, or by an import, a def or class statement or an except clause) or a module-level augmented assignment),
through a local whose every binding is read (a walrus in a nested def's, class's or lambda's header is a binding it does not
read) and through a dict literal's values; the part before any `;`, stripped and lower-cased, is compared with the types a
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
to itself encoded, its one argument the string constant `"utf-8"`
(`body = body.encode("utf-8") if isinstance(body, str) else body`); a loop over a parameter's items (`for k, v in (headers or
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
or a name the list does not hold (through `__self__` of a builtin, a container or a copy of a namespace mapping, a module's own
`__setattr__` or `__delattr__` method, a listed name, attrgetter or methodcaller imported from a module other than its own, a name
built at run time, gc or ctypes among them, and through a module reached by a tuple or list unpacking, an inline walrus,
`sys.modules.__getitem__`, a for-loop target, a parameter default or a starred argument)
is outside the list and not seen, and a module name or a builtin so rewritten is read as the file's text binds it. A
`_send` definition in a class that a function defines, and a page function that a function encloses, fail the run by name: the
census does not read the
enclosing function's scope, so it would take a name that function binds (a builtin or a module name it shadows) for the module's.
The page function of each script-running route
is followed to the text it returns or inlines, and a
parameter a followed call omits is read from its default value as that argument would be, in the scope the def statement runs in
(a default the pass cannot read is refused by name, among them a method's default naming a name its class body binds). A name
the page function's scope binds, or for a function defined in it an enclosing function's scope, is decided by that scope and never
by the module's binding: a local (a parameter the body also assigns, a walrus in a nested def's, class's or lambda's header, and a
comprehension's target inside its comprehension among them) is read from its values as a bare name or a receiver and refused as
a callee; a parameter or an except name is a value slot, refused as a callee when it shares a module function's name; a function
defined in the page function is followed as a callee only as its name's one binding there; a name the function declares `global`
is the module's binding, read as such; and any other binding refuses, a comprehension's target elsewhere in the function, a
function-level import, a nested class, a del, a name a nonlocal declaration rebinds and a name bound two ways (two different
binding forms in one scope, or a def or a class statement beside any other binding of it; every value form, an assignment,
augmented or annotated, a loop, with or unpacking target and a walrus, is one form, and a parameter the body also binds by one is
one local, read from its values) among them. In that text the served pass reads a
BoolOp's operands, a method call's receiver and a subscript's container when they name a module constant (a name one plain
single-name assignment binds as a top-level statement and nothing else binds at module level, in a module with no star import that
writes no name of its module namespace through a computed name and may not rewrite it at run time, as listed below) or a local,
the receiver of
`.encode` or `.format_map` whatever it is, a class attribute the class body binds, a loop, unpacking or with target from its
source, and a local container's appended or stored values; it passes over a base whose own text it does not read (in a module
that holds no star import, a top-level import statement that is its name's one module-level binding and is not rebound, or a
builtin that no module-level binding shadows and that is not rebound, a call of super() excepted, whose methods are a base
class's; a parameter, an except name, or a name the function binds from one of those), reading as text the arguments of a call of
such a base or of a method on one (`dict(X).get(k)` and
`json.loads(json.dumps(X))[0]` read X), and over a bare module name that is such an import or such a builtin, or, in such a
module, a top-level def or class statement that is its name's one module-level binding and is not rebound. Text such a base holds
is not read, as with code behind a name on self: a constant that a sibling module defines and the page imports, or an attribute
set on self or another parameter before the call. A name is rebound when a function binds it under `global` or a statement at
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
the fourth. The four ways, the whole of the reach the census reads for each of these names (`__dict__` in the fourth alone, beside
the attribute the computed-name forms above name): by its own name, in any context; by a name an import anywhere in
the file binds to it from its module (locals, exec, eval, compile, `__import__`, globals, vars, setattr and delattr from builtins,
import_module and
`__import__` from importlib, _getframe from sys), in any context, read as the name itself; as an attribute of that name on a
builtins receiver (`__builtins__`, a name that `import builtins [as X]` or `from X import builtins [as Y]` binds, for any module
X, `sys.modules["builtins"]` or `sys.modules.get("builtins")`, or `__import__("builtins")` or `import_module("builtins")`, a call
of either reached in these ways), or on any receiver for exec, eval, locals, `__import__`, import_module and _getframe; or by its
name spelled as a string, or as a join of string constants that reads as one, where a run-time lookup by name takes it (the second
argument of getattr, setattr, delattr or hasattr, called by its name, by a name an import binds to it or as an attribute of a
builtins receiver; any argument of operator.attrgetter (any dotted part of the name) or operator.methodcaller, called as
`.attrgetter` or `.methodcaller` on a name that `import operator [as X]` or `from X import operator [as Y]` binds, for any module
X, or by a name that `from operator import attrgetter [as Y]` or `from operator import methodcaller [as Y]` binds; or a key on a
namespace expression: a subscript's slice, or the first argument of `.get`, `.pop`, `.setdefault` or a
`__getitem__`-family call, whose receiver is a `__dict__`, `__builtins__` or a call of vars, globals or locals reached in the
first three ways). Every builtin is rebound in such a file and in a file that names
`__builtins__`, imports the builtins module or writes a module spelled "builtins" (an attribute store, a setattr or delattr, or a
write through its `__dict__` or vars()). A function's `X = []` of a local of the same name, or its `X.append(...)`, does not
rebind it. It follows a call whose callee is a
module function (a top-level def statement that is its name's one module-level binding, not rebound, in a module with no star
import, and bound by no function scope of the page), a function defined in the page function or a method of the route's class
(to what it returns, any decorator on it not applied), a text method or a file read, or any other method (through its receiver,
as above, so `_K.__call__(t)` on a module constant `_K` that holds a lambda reads `_K` and the lambda's body, whose parameters are
value slots), and it reads every call's arguments; a call to any other callee passes when the callee is such an import, such a
builtin or a parameter. It reads both operands of a `/`, a path join, where `__file__` is a value slot when no statement of the
file binds it, in any scope and by any form, the file neither writes a name of its module namespace through a computed name nor
may rewrite it at run time and the module holds no star import, and is refused by name otherwise. It reads a lambda's body, its
parameters value slots, and its
defaults where
the lambda stands. A None, bool or int constant, the empty bytes constant and a `*` or `<<` over int constants are value slots
with no text. The run fails by name (SERVED) on any other reference to `_send` (a read of it that is not a call's function, a
store or delete of an attribute so named, or a string equal to `_send`), a content type the pass cannot read, a script-running
type written outside `_send`, a function that
answers outside `_send` more often than it writes a Content-Type header, a container the module writes at run time, any other
receiver or container, any other callee (a module constant, a local, a class, a subscript, a call and a lambda among them), any
other bare module name (one bound other than by one assignment, one bound by an annotated, unpacking or chained assignment, one
annotated at module level beside its assignment, one no module-level statement binds that a function or a class body binds under a
`global` declaration, an
import, a function or a class beside another module-level
binding, an import, a def or a class bound once inside a module-level block and not by a top-level statement, a name bound once in
any other form inside such a block's body, a name a star import may rebind, a module name in a file that writes its module
namespace through a computed name or may rewrite it at run time (the reason naming the form and its line), a builtin in a file
that may rewrite the builtins, and a rebound import, builtin, function or
class among them), any other kind of expression in a page (a non-empty bytes, float, complex or Ellipsis constant, an f-string's
format spec,
any other operator, a comparison and a unary expression among them), and a route whose text the pass cannot read,
unless the served allowlist, SERVED_ALLOW, names the place by its function and expression, with the number of places the entry
covers and the reason (the two answers with no body, the CORS preflight's 204 and the websocket upgrade's 101, are named there);
an entry that names nothing in the run, or covers a different number of places, fails the run too. In served text every `fetch(`
and `import(` on a line is read by its own argument, and no comment skip applies, since a joined constant is one line whatever
it starts with. Each string literal is read on its own, and so is the text of each of these joins of string constants, at its
first literal's line: a `+` of them (an f-string's literal text at its start or end among them), an f-string whose fields are
string constants, a `%`, `.format` or `.format_map` of them, a `.join` over a list or tuple of them or over a dict literal whose
keys they are (the keys in order, a repeated key at its first place) and a `.replace` of them (implicitly concatenated literals
are one constant already). A tool's name, a tag, an attribute, an import or a fetch URL split
across such a join is therefore read whole, and a site both reads find is listed once; a fetch URL cut at the join is listed as
the joined text reads it, whole. Text a page joins through anything but a string constant (a name, a call, an attribute, or a
field or a `%` slot holding one) is
read piece by piece: a tool's name, a tag or an attribute split there is not seen, and a fetch URL cut there is
classed by the part before the cut. A `.join` over a set literal or a set comprehension, its one argument or, unbound as in
`str.join("", {...})`, its second, refuses by name, its iteration order not fixed, so its join is no one text. A file the page
reads at run time is
covered by the walk when it is a scanned kind, and a stylesheet is named,
not scanned. A site in served text is listed
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
import ast
import builtins
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
__future__ abc anyio argparse array ast asyncio base64 bisect calendar claude_agent_sdk collections concurrent contextlib copy
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
        # SERVED_ALLOW's, FRAME_WRITERS's and JS_ALLOW's matches this run (key -> the source positions it covered; a JS_ALLOW key is
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
        # what _namespace_flags reads, collected by the walk: the calls of globals or vars ns_listed reads with no argument, and
        # globals, vars, setattr or delattr as ns_listed reaches it read other than as a call's callee (ns_calls), the `__dict__`
        # attributes and the one-argument calls of vars (maps), the receivers of `.get(...)` calls (gets), the attribute stores and
        # deletes (stores), the calls of setattr and delattr ns_listed reads (setattrs), the assignments whose value may be a module,
        # whether the file names `__builtins__` or imports the builtins module,
        # whether a statement binds `__file__`, each run-time form (runtime, each (line, column, the form): an import from the
        # file's own package (ns_own), a listed callable or attribute ns_listed reads or a call of one (arm ii), and a listed name
        # spelled as a string where a run-time lookup by name takes it (ns_string, arm iii)), the calls ns_listed reads as
        # __import__ or import_module (importers, which _namespace_flags's module() reads) and every call's callee node (callees)
        self.ns_facts = {"ns_calls": [], "maps": [], "gets": set(), "stores": [], "setattrs": [], "assigns": [], "builtins": False, "file": False,
                         "runtime": [], "importers": set(), "callees": set()}
        parts = rel.split("/")   # the file's top package directory (none for a file at the root) and its own module name
        self.ns_top, self.ns_stem = parts[0] if len(parts) > 1 else None, os.path.basename(rel).rsplit(".", 1)[0]
        # the names an import anywhere in the file binds: to a listed name from its module (ns_from, name -> the listed name), to the
        # builtins module (ns_bmods: `import builtins [as X]`, `from X import builtins [as Y]`), and, for ns_string, to getattr,
        # setattr, delattr or hasattr (ns_getattrs), to operator's attrgetter or methodcaller (ns_ops: `from operator import
        # attrgetter [as Y]`) and to the operator module (ns_opmods: `import operator [as X]`, `from X import operator [as Y]`)
        self.ns_from, self.ns_bmods, self.ns_getattrs, self.ns_ops, self.ns_opmods = {}, set(), set(), {}, set()
    def visit_Module(self, n):   # the walk, then the routes read from its candidates
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
        self.res.ns[self.rel] = _namespace_flags(self.ns_facts, self.ns_stem)
        self.routes = routes_of(self.rel, n, self, self.res)
    def ns_bind(self, name):   # a binding of `__file__`, in any scope and by any form (_namespace_flags)
        if name == "__file__": self.ns_facts["file"] = True
    def ns_runtime(self, n, form):   # a run-time form of _namespace_flags, with its line
        self.ns_facts["runtime"].append((n.lineno, n.col_offset, "%s at line %d" % (form, n.lineno)))
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
    def _nskey(self, e):   # a namespace expression a run-time lookup by name reaches: `__dict__`, `__builtins__`, or a call ns_listed reads as vars, globals or locals (arm iii)
        return ((isinstance(e, ast.Attribute) and e.attr == "__dict__") or (isinstance(e, ast.Name) and e.id == "__builtins__")
                or (isinstance(e, ast.Call) and self.ns_listed(e.func) in ("vars", "globals", "locals")))
    def ns_string(self, node):   # arm iii: a listed name (_STRING_NAMES) spelled as a string, read only where a run-time lookup by name
        # takes it: the second argument of getattr/setattr/delattr/hasattr on any receiver; any argument of operator.attrgetter or
        # methodcaller (for attrgetter any dotted part); or a key on a namespace expression (a subscript's slice, or the first argument
        # of .get/.pop/.setdefault/.__getitem__/.__setitem__/.__delitem__)
        if isinstance(node, ast.Subscript):
            if self._nskey(node.value) and self._const_str(node.slice) in _STRING_NAMES: self.ns_runtime(node.slice, "spells %s as a string" % self._const_str(node.slice))
            return
        f = node.func   # the callee by its name, a name an import binds to it (in any scope), or as an attribute of a builtins (getattr) or operator (ns_opmods) receiver
        af = self.alias.get(f.id, f.id).split(".")[-1] if isinstance(f, ast.Name) else ""
        if (isinstance(f, ast.Name) and (af in _GETATTRS or f.id in self.ns_getattrs)) or (isinstance(f, ast.Attribute)
                and f.attr in _GETATTRS and self._builtins_recv(f.value)):
            if len(node.args) > 1 and self._const_str(node.args[1]) in _STRING_NAMES: self.ns_runtime(node.args[1], "spells %s as a string" % self._const_str(node.args[1]))
        d = self.dotted(f)
        op = d if d in ("operator.attrgetter", "operator.methodcaller") else ("operator." + self.ns_ops[f.id]) if (
            isinstance(f, ast.Name) and f.id in self.ns_ops) else ("operator." + f.attr) if (isinstance(f, ast.Attribute) and f.attr in ("attrgetter", "methodcaller")
                                                                                              and isinstance(f.value, ast.Name) and f.value.id in self.ns_opmods) else None
        if op is not None:
            for a in list(node.args) + [k.value for k in node.keywords]:
                s = self._const_str(a)
                if s is not None and (s in _STRING_NAMES or (op == "operator.attrgetter" and any(p in _STRING_NAMES for p in s.split(".")))):
                    self.ns_runtime(a, "spells %s as a string" % s)
        if isinstance(f, ast.Attribute) and f.attr in ("get", "pop", "setdefault", "__getitem__", "__setitem__", "__delitem__") and self._nskey(f.value):
            if node.args and self._const_str(node.args[0]) in _STRING_NAMES: self.ns_runtime(node.args[0], "spells %s as a string" % self._const_str(node.args[0]))
    def visit_Global(self, n):
        self.globals[-1].update(n.names)
        if self.defs: self.global_decls.append((tuple(self.defs), tuple(n.names)))   # Result.global_decls
    def write(self, name, line, rebind=False):
        """A write of a name (Result.writes); a binding under `global` (rebind) or a write by a statement at module level is also a
        rebind of the module's name (Result.rebinds), and any other write inside a function or a class body is a write only."""
        self.writes.setdefault(name, []).append(line)
        if rebind or not self.stack: self.rebinds.setdefault(name, []).append(line)
    def global_bind(self, name, line):   # a binding of a name the enclosing function declares `global`
        if self.stack and name in self.globals[-1]: self.write(name, line, True)
    def visit_Name(self, n):   # a module name a function binds under `global`; a bare `_send` read other than as a call's function
        if isinstance(n.ctx, ast.Store): self.global_bind(n.id, n.lineno)
        elif n.id == "_send" and isinstance(n.ctx, ast.Load) and id(n) not in self.send_funcs: self.send_ref(n)
        listed = self.ns_listed(n)   # arm ii: the listed callable, computed-name writer or setter the name reaches, by its own name or an import's name for it
        if n.id == "__builtins__": self.ns_facts["builtins"] = True
        elif n.id == "__file__" and not isinstance(n.ctx, ast.Load): self.ns_facts["file"] = True
        elif listed in _NS_READS and isinstance(n.ctx, ast.Load) and id(n) not in self.ns_facts["callees"]:
            self.ns_facts["ns_calls"].append(n)   # globals, vars, setattr or delattr itself read (`_g = globals`, `_s = setattr`), a use no `.get` read limits
        if listed in _RUNTIME_NAMES: self.ns_runtime(n, "names %s" % listed)   # a listed callable, in any context
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
        if n.value is not None: self.ns_assign([n.target], n.value)
        self.generic_visit(n)
    def visit_NamedExpr(self, n):
        self.ns_assign([n.target], n.value); self.generic_visit(n)
    def visit_Attribute(self, n):   # an `<x>._send` read other than as a call's function (`reply = self._send`), stored (`Handler._send = f`) or deleted
        if n.attr == "_send" and id(n) not in self.send_funcs: self.send_ref(n)
        if n.attr == "__dict__": self.ns_facts["maps"].append(n)   # a namespace mapping, a module's among them (_namespace_flags)
        if not isinstance(n.ctx, ast.Load): self.ns_facts["stores"].append(n)
        if n.attr in _RUNTIME_ATTRS: self.ns_runtime(n, "names the attribute %s" % n.attr)   # arm ii: a function's or a frame's namespace, on any receiver
        listed = self.ns_listed(n)   # arm ii: a listed name as an attribute: compile, globals, vars, setattr and delattr on a builtins receiver, the rest on any receiver
        if listed in _RUNTIME_NAMES: self.ns_runtime(n, "names the attribute %s" % listed)
        elif listed in _NS_READS and isinstance(n.ctx, ast.Load) and id(n) not in self.ns_facts["callees"]: self.ns_facts["ns_calls"].append(n)   # `builtins.globals` or `builtins.setattr` read
        self.visit(n.value)   # the one child that holds nodes (attr is a string; the ctx marker holds none and no visitor reads it)
    def send_ref(self, n):
        self.send_refs.append((n, tuple(self.defs), ".".join(self.stack) or "<module>"))
    def visit_Subscript(self, n):   # a subscript store or delete writes its container
        if isinstance(n.ctx, (ast.Store, ast.Del)) and isinstance(n.value, ast.Name): self.write(n.value.id, n.lineno)
        self.ns_string(n)   # arm iii: a listed name as a namespace subscript's key
        self.generic_visit(n)
    def visit_AugAssign(self, n):   # a module-level `X += ...` rebinds X after its binding
        if isinstance(n.target, ast.Name) and not self.stack: self.write(n.target.id, n.lineno)
        self.generic_visit(n)
    def visit_Import(self, n):
        self.alias.update({a.asname or a.name: a.name for a in n.names}); self.imports.extend((a.name.split(".")[0], n.lineno) for a in n.names)
        for a in n.names: self.global_bind((a.asname or a.name).split(".")[0], n.lineno); self.ns_bind((a.asname or a.name).split(".")[0])   # an import under `global`
        if any(a.name.split(".")[0] == "builtins" for a in n.names): self.ns_facts["builtins"] = True
        for a in n.names: self.ns_own(n, a.name)
    def visit_ImportFrom(self, n):
        self.alias.update({a.asname or a.name: (n.module or "") + "." + a.name for a in n.names})
        for a in n.names: self.global_bind(a.asname or a.name, n.lineno); self.ns_bind(a.asname or a.name)
        if (n.module or "").split(".")[0] == "builtins" or any(a.name == "builtins" for a in n.names): self.ns_facts["builtins"] = True
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
        self.bind_loop(n.target, n.iter); self.generic_visit(n)
    visit_AsyncFor = visit_For
    def visit_comprehension(self, n):
        self.bind_loop(n.target, n.iter); self.generic_visit(n)
    def comp(self, n):   # the generators bind before the element that reads them is visited
        for g in n.generators: self.visit(g)
        for f in ("key", "value", "elt"):
            if hasattr(n, f): self.visit(getattr(n, f))
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
        self.ns_assign(n.targets, n.value)
        if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if not self.stack: self.consts[n.targets[0].id] = n.value
            else: self.bind(n.targets[0].id, n.value)
        self.generic_visit(n)
    def visit_With(self, n):
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
    def visit_BinOp(self, n):   # a program path built with pathlib: ROOT / "tools" / "x.mjs"
        if (isinstance(n.op, ast.Div) and isinstance(n.right, ast.Constant) and isinstance(n.right.value, str) and isinstance(n.left, ast.BinOp)
                and isinstance(n.left.right, ast.Constant) and n.left.right.value in ("tools", "scripts")):
            self.program_ref(n, n.left.right.value + "/" + n.right.value)
        self.generic_visit(n)
    def enter(self, n):
        b = {}
        if not isinstance(n, ast.ClassDef):
            a = n.args
            for x, d in list(zip(a.args[len(a.args) - len(a.defaults):], a.defaults)) + list(zip(a.kwonlyargs, a.kw_defaults)):
                if d is not None and self.prim(d): b[x.arg] = self.prim(d)
        self.global_bind(n.name, n.lineno); self.ns_bind(n.name)   # a def or class statement under `global`, bound in the enclosing scope
        if isinstance(n, ast.ClassDef) and self.defs and not isinstance(self.defs[-1], ast.ClassDef): self.inner_classes.append(n)
        self.stack.append(n.name); self.binds.append(b); self.defs.append(n); self.globals.append(set()); self.generic_visit(n)
        self.globals.pop(); self.defs.pop(); self.binds.pop(); self.stack.pop()
    visit_FunctionDef = visit_AsyncFunctionDef = visit_ClassDef = enter
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
        if attr == "get": self.ns_facts["gets"].add(id(n.func.value))   # a `.get(...)` read, the one use of a namespace mapping that writes nothing
        elif listed in _NS_SETTERS: self.ns_facts["setattrs"].append(n)   # a call of setattr or delattr, by its own name, an import's name for it or as an attribute of builtins (_namespace_flags)
        elif listed in _NS_WRITERS:   # a call of globals or vars, by its own name, an import's name for it or as an attribute of builtins
            if not n.args and not n.keywords: self.ns_facts["ns_calls"].append(n)
            elif listed == "vars" and len(n.args) == 1: self.ns_facts["maps"].append(n)
        self.ns_facts["callees"].add(id(f))
        if listed in ("__import__", "import_module"): self.ns_facts["importers"].add(id(n))   # module()'s calls of either
        # a call of a listed callable, a run-time form whose reason names the call where the callee is a name, an attribute of a name
        # bound to builtins, or import_module or _getframe on any receiver (the callee's own node, visited next, is the form too)
        if listed == "_getframe": self.ns_runtime(n, "calls sys._getframe")
        elif listed in _RUNTIME_NAMES and (isinstance(f, ast.Name) or listed == "import_module" or self.dotted(f.value) in ("builtins", "__builtins__")):
            self.ns_runtime(n, "calls %s" % listed)
        self.ns_string(n)   # arm iii: a listed name as a string in a getattr-family second argument, an attrgetter/methodcaller argument, or a namespace-mapping key
        where = ".".join(self.stack) or "<module>"
        if attr == "_send" or (isinstance(n.func, ast.Name) and n.func.id == "_send"):   # route candidates, typed by routes_of
            self.sends.append((n, tuple(self.defs), where)); self.send_funcs.add(id(n.func))   # (the func is no reference of its own)
        if _is_ctype_write(n): self.ctype_writes.append((n, tuple(self.defs), where))
        if (isinstance(n.func, ast.Name) and n.func.id == "getattr" and len(n.args) > 1 and isinstance(n.args[1], ast.Constant)
                and n.args[1].value == "_send"):   # `_send` named by a getattr: refused as the call (its string is no second reference)
            self.send_refs.append((n, tuple(self.defs), where)); self.send_funcs.add(id(n.args[1]))
        if attr == "send_response": self.responds.append((n, tuple(self.defs), where))
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
    if dom is None: dom = kind == "js" and rel.startswith(tuple(d + "/" for d in JS_ROOTS))
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
# The constants the served pass refuses in a page, by type, each with the reason its SERVED line gives: a str is text it reads,
# and None, a bool, an int and the empty bytes are value slots (_Served.resolve)
_PCT_SPEC = re.compile(r"%(?:\([^)]*\))?[-#0 +]*(\d*)(?:\.(\d*))?")   # a `%` conversion's width and precision, which _const_text bounds
_CONSTANT_KINDS = {bytes: "a non-empty bytes Constant", float: "a float Constant", complex: "a complex Constant", type(...): "an Ellipsis Constant"}


def _int_arith(e):
    """Whether e is an int constant, or a Mult or LShift whose operands are each one or such a BinOp (`2 * 1024`, `1 << 20`): the
    only arithmetic the served pass takes as a value slot, the kinds and roles the kernel's pages use."""
    if isinstance(e, ast.Constant): return type(e.value) is int
    return isinstance(e, ast.BinOp) and isinstance(e.op, (ast.Mult, ast.LShift)) and _int_arith(e.left) and _int_arith(e.right)
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
    there binds the function's name another way), and its body is not."""
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
_CLASS_DEFAULT = "a method's default naming a name the class body binds, which the census does not read as a scope"
_COMPUTED = "a module name in a file that writes its module namespace through a computed name"
_FILE_BOUND = "__file__, which a statement of the file binds"
_SHADOWED = "a builtin in a file that may rewrite the builtins"
_ENCLOSED = "a definition inside a function, whose scope the census does not read"
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
_NS_NONE = {"computed": False, "builtins": False, "file": False, "runtime": None}   # _namespace_flags's answer for a file the walk did not read
def _namespace_flags(facts, stem):
    """{"computed": whether the file may write its own module namespace through a computed name, "builtins": whether it may write
    the builtins, "file": whether a statement of the file binds `__file__`, in any scope and by any form, "runtime": the first form,
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
    may be written where the file names `__builtins__` as a name (so no alias of that name escapes),
    imports the builtins module, or writes as above a module spelled "builtins" there; and a file that writes its own namespace
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
    `__builtins__`, or a call of vars, globals or locals as ns_listed reaches it).
    A listed name reached any other way or a name the list does not hold (through `__self__` of a builtin, a container or a copy
    of a namespace mapping, a module's own `__setattr__` or `__delattr__` method, a listed name, attrgetter or methodcaller
    imported from a module other than its own, a name built at run time, gc or ctypes among them, and through a module reached by
    a tuple or list unpacking, an inline walrus, `sys.modules.__getitem__`, a for-loop target, a parameter default or a starred
    argument) is outside the list and not seen: a module namespace rewritten at run time by code
    outside that list is not seen."""
    aliases, out = {}, {"computed": False, "builtins": facts["builtins"], "file": facts["file"], "runtime": None}

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
    binding, and a builtin only where no module-level binding shadows it, and neither where Result.rebinds records the name (a
    binding under `global` in a function, a write by a statement at module level) or the module holds a star import, which may
    rebind any name (_Served._sole and _Served._builtin)."""
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
    targets = {t.id for t in ast.walk(loop.target) if isinstance(t, ast.Name)} if loop else set()
    in_loop = {id(n) for b in (loop.body if loop else ()) for n in ast.walk(b)}
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
    the file names no `__builtins__`, imports no builtins module, writes no module spelled "builtins", writes no name of its
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
    of the page parameter to itself encoded, its one argument the string constant "utf-8" (`body = body.encode("utf-8") if
    isinstance(body, str) else body`); a loop over a parameter's items (`for k, v in (headers or {}).items():`) and an if on a
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
    a container or a copy of a namespace mapping, a module's own `__setattr__` or `__delattr__` method, a listed name, attrgetter
    or methodcaller imported from a module other than its own, a name built at run time, gc or ctypes among them, and through a
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
    import, a match capture, any other store); a comprehension binds its targets alone, and a walrus inside it binds the name of the
    scope around it."""
    if isinstance(scope, _COMPS):
        return ["a comprehension's target" for g in scope.generators for t in ast.walk(g.target) if isinstance(t, ast.Name) and t.id == name], None
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
    in the call's own class body (a call through self) or in the module (a bare call): the parameter that definition's
    Content-Type write names, by position or keyword, or the value it writes (the kernel's Handler._send its `ctype`, the postal
    bus's application/json). A file that binds `_send` more than once outside function bodies (the module and every class body
    counted together, a class body a function body defines included, in any binding form but a comprehension's target, which binds
    only in its comprehension: _send_bindings) or other than by one def statement direct in a class body or the module, or where a
    function or a class body binds it under a `global` declaration, rebinding the module's name at run time (_global_binder over
    Result.global_decls), is a SERVED line at each of its `_send` calls, and so is a bare call that
    reaches a `_send` bound inside a function, a lambda, a comprehension or a class body around it, in any form, the line naming the
    scope and the binding (_bare_send_binding: Python calls that binding, not the module's), a call that reaches no definition the
    census reads, the line saying why (a `_send` the call's own class body does not bind, for a call through self: inherited or set
    at run time; one reached through an object other than self, or through an attribute outside any class body; a `_send` no
    scope the bare call looks it up in
    binds, the module included; and, in a file that names `_send` nowhere but as the called name of those calls, so binds it nowhere
    at all (_names_send), a definition this file does not hold), a call of a definition carrying any decorator, whose parameters the
    census does not read, and a bare call in a module
    that holds a star import
    (_module_info); an override of `_send` in a subclass another file defines is not read, a call through self typed through its
    own class body's definition. A call to a definition that writes no Content-Type is a frame writer's (FRAME_WRITERS) or a SERVED line; the type is
    resolved (_ctype_values, through a module name no code writes after binding it: _module_consts less the names Result.writes
    records, and through a local whose every binding _scopes_of reads) and a script-running one (_script_type) makes the call a
    route whose text the served pass reads; an unresolved type is a SERVED line. A route's page body is the call's second
    positional argument, read only when the call passes it positionally with no starred argument before it and no `**` and the
    definition's one output is its one write of that parameter, nothing in a method's definition binding self again or declaring it
    global, and nothing in its signature or body outside the node kinds, in their roles, of the kernel's Handler._send (_body_param,
    _send_gate, which lists them by kind): the one write of the page parameter, the definition's last statement, directly after its
    one `self.end_headers()`; the header calls on self, send_response with its one argument and send_header; isinstance, str, len
    and getattr of self, each unbound and unrebound (the file's Result.rebinds decides with the module's bindings whether a builtin
    the definition calls is the builtin, and a file that names `__builtins__`, imports the builtins module, writes a module spelled
    "builtins", writes its module namespace through a computed name or may rewrite it or the builtins at run time has none:
    _namespace_flags); the codec rebinding of the page parameter, its one argument "utf-8"; a loop over a parameter's items; tests
    on a parameter or on getattr of self; header values built from string constants holding no CR or LF, parameters, the loop's
    targets, attributes read on self, str, len and a `%` format on a string constant; and a signature of positional parameters,
    none positional-only, with None defaults and no annotation. A page function a function encloses, or a `_send` in a class a
    function defines, is a SERVED line by
    name, since the enclosing function's names (a builtin or a module name it shadows among them) are no scope the census reads;
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
    hold (through `__self__` of a builtin, a container or a copy of a namespace mapping, a module's own `__setattr__` or
    `__delattr__` method, a listed name, attrgetter or methodcaller imported from a module other than its own, a name built at run
    time, gc or ctypes among them, and through a module reached by a tuple or list unpacking, an inline walrus,
    `sys.modules.__getitem__`, a for-loop target, a parameter default or a starred argument) is outside the list
    and not seen. Any other reference to `_send` (a read of it that is not a call's
    function, a store or delete of an attribute so named, or a string equal to `_send`) is a SERVED line; a call through a name
    computed at
    run time is not read. Every Content-Type header written outside a `_send` definition is typed the same way, and a script-running
    one is a SERVED line (the served pass follows a page's text through `_send` alone); a function outside `_send` that answers
    (send_response) more often than it writes a Content-Type header is a SERVED line, the browser typing that body by sniffing
    it. SERVED_ALLOW excuses a place by its function and expression (a `_send` call's place by the call's function, `self._send` or
    `_send`), save an unread body. Returns the routes, (call, the
    enclosing function, the class name, the script-running type, the body expression), sorted by line."""
    ns = res.ns.get(rel) or _NS_NONE   # a file that writes its module namespace through a computed name, or may rewrite it at run
    consts = {} if ns["computed"] or ns["runtime"] else _module_consts(tree)   # time, reads no module constant
    written = {x for x in res.writes.get(rel, {}) if x in consts}   # the module names some code writes after binding them
    funcs = {n.name: n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    routes, cache, typed = [], {}, {}

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
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "self" and cls is not None:
            d = next((b for b in cls.body if isinstance(b, (ast.FunctionDef, ast.AsyncFunctionDef)) and b.name == "_send"), None); method = True   # the file's one binding, when this class body holds it
        elif isinstance(f, ast.Name):
            why = _bare_send_binding(call, defs, tree) or (_STAR if _module_info(tree)["star"] else None)   # a scope around the call binds it, or a star import may
            if why is not None:
                if not allowed(where, f, call):
                    res.problems.append("SERVED %s:%d calls _send on %s, %s: the census cannot read the response's content type"
                                        % (rel, call.lineno, ast.unparse(f)[:40], why))
                continue
            d = funcs.get("_send")
        if d is None:   # the call reaches no definition the census reads: why, by the reach
            if anywhere is None: anywhere = _names_send(tree, [c for c, _, _ in sc.sends])
            why = ("a definition this file does not hold" if not anywhere else
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
            routes.append((call, fn, cls.name if cls is not None else None, ctype, call.args[1]))
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


class _Served(object):
    """The text a route's page is served from, followed through the module's syntax tree: the body expression of each route
    (routes_of: the call's second positional argument) resolved to its string constants (a literal, an f-string's parts, `+` and
    `%` operands and the argument tuple, a `/`'s operands (a path join), a conditional's branches, a BoolOp's operands, a starred
    value, a comprehension's element with its targets read from their source, a lambda's body with its parameters as value slots
    and its defaults read where it stands, a module constant by name (a name one plain single-name assignment binds as a top-level
    statement and nothing else binds at module level, a header walrus included, in a module with no star import that writes no
    name of its module namespace through a computed name and may not rewrite it at run time: _module_consts, _namespace_flags), a
    local by every binding it has in
    the function, a `.format`, `.join` (but one over a set, refused below), `.replace` or `.strip` receiver and its arguments, and
    every `return` of a module function,
    a function defined in the page function or a `self.` method the page calls), each a piece (label, its own line, text, the
    part it came from) for line_scan, with each join of string constants _const_text reads recorded in `joins` (_note,
    _const_text), whose text served_texts scans beside each literal's own read; a local bound to a `.read_text()` or `.read()`
    is a file slot the walk covers or names. A route whose page function a function encloses, or whose `_send` stands in a class a
    function defines, is refused before this pass (routes_of), since the enclosing function's names are no scope it reads.

    A name the page function's scope binds, or for a nested context an enclosing function's scope, is decided by that scope and
    never by the module's binding (_scoped over the binding forms _locals records, row (d) of the seventh round): a local (a
    parameter the body also assigns, a walrus in a nested def's, class's or lambda's header, a comprehension's target inside its
    comprehension) is read from its values as a bare name or a receiver and refused as "a call" as a callee; a parameter or an
    except name is a value slot, refused as a callee when it shares a module function's name; a function defined in the page
    function is followed only as its name's one binding there; a name the function declares `global` is the module's binding,
    read as such; and any other binding is refused by its form (a comprehension's target elsewhere in the function, a
    function-level import, a nested class, a del, a name a nonlocal declaration rebinds, any other store, and a name bound two
    ways, meaning two different binding forms in one scope, or a def or a class statement beside any other binding of the name;
    every value form, an assignment, augmented or annotated, a loop, with or unpacking target and a walrus, is one form, and a
    parameter the body also binds by one is one local, read from its values).

    A method call's receiver and a subscript's container are read when they name a module constant or a local, and so are the
    receiver of `.encode` or `.format_map` whatever it is and a class attribute the class body binds (`self.X`, `Cls.X`); a name
    the function binds as a loop, unpacking or with target, or by a walrus, is read from that source, and a local container's
    appended or stored values are its values too; a module container some code writes after binding it (a write Result.writes
    records, as the served sentence lists them) is a run-time memo, and it and any other receiver or container are refused by name
    unless the base is one whose own text the pass does not read (a top-level import statement that is its name's one module-level
    binding, a builtin no module-level binding shadows, a call of super() excepted, whose methods are a base class's, each in a
    module with no star import; a parameter or a name bound from one, a BoolOp over those; a call of one of those or of a method
    on one, whose arguments are read as text: `dict(X).get(k)` reads X, _chain_args) or SERVED_ALLOW names the place, and a call
    base the reader does not resolve is refused by name; text such a base holds (a constant a sibling module defines and the page
    imports, an attribute set on self or another parameter before the call) is not read, as with code behind a name on self. A
    call is followed only as listed here (a file read, a text method's receiver, a module function that is a top-level def
    statement and its name's one module-level binding, bound by no function scope of the context, a function defined in the page
    function, a method of the route's class, and any other method call through its receiver as above, so `_K.__call__(t)` on a
    constant holding a lambda reads `_K` and the lambda's body, whose parameters are value slots), each followed function read to
    its own returns with any decorator on it not applied, and the default of each of its parameters the call omits read as that
    argument would be, in the scope its def statement runs in (_defaults), and every call's arguments are read as text; any other
    callee passes when _base finds it such an import, such a builtin or a parameter, and is refused by name otherwise (a module
    constant, a local, a class, a subscript, a call and a lambda literal among them) unless SERVED_ALLOW names the place. A bare
    module name that is no constant passes when it is such an import or such a builtin, or a top-level def or class statement that
    is its name's one module-level binding, and any other (one bound other than by one assignment, one bound by an annotated,
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
    getattr-family, attrgetter/methodcaller or namespace-key position; _namespace_flags lists these four ways exactly; the reason
    names the form and its line), and a builtin passes nowhere in a file that names `__builtins__`, imports the builtins module or
    writes a module spelled "builtins" (the reason names each); a module namespace rewritten at run time by code outside those
    forms is not seen, a listed name reached any other way or a name the list does not hold (through `__self__` of a builtin, a
    container or a copy of a namespace mapping, a module's own `__setattr__` or `__delattr__` method, a listed name, attrgetter or
    methodcaller imported from a module other than its own, a name built at run time, gc or ctypes among them, and through a
    module reached by a tuple or list unpacking, an inline walrus, `sys.modules.__getitem__`, a for-loop target, a parameter
    default or a starred argument) being outside the list, and a function's write through a local
    of the same name does not count. A parameter in the body is
    a value slot whose text is its argument's, read at the call, or, where a followed call omits it, its default's (_defaults).
    The other value slots, with no text, are the kinds and roles a full served pass over the kernel hands resolve: a None, bool or
    int constant, the empty bytes constant, a Mult or LShift whose operands are int constants or such BinOps (`2 * 1024`,
    `1 << 20`), and `__file__` where no statement of the file binds it, in any scope and by any form, the file writes no name of its
    module namespace through a computed name and may not rewrite it at run time, and the module holds no star import (the module's
    own path, which the import system binds; otherwise refused by name). Anything else is text the census did not read, a SERVED
    problem naming its kind (_unread): a non-empty bytes, float, complex or Ellipsis constant, a format spec (refused, not read:
    before 3.12 its parts carry the f-string's own position, which served_texts's read-once key would take for a part already
    read), a Mult or LShift over anything else, every other operator, a comparison, a unary expression, a slice, a `.join` over a
    set literal or a set comprehension (its one argument or, unbound as in `str.join("", {...})`, its second: a set's iteration
    order is not fixed, so its join is no one text) and a kind with no arm among them, as is a route whose body yields no piece
    and no file slot."""
    def __init__(self, rel, tree, res):
        self.rel, self.res, self.consts, self.funcs, self.methods = rel, res, {}, {}, {}
        self.imports, self.builtins, self.class_attrs, self.classes = set(), set(dir(builtins)), {}, {}
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
                self.class_attrs[node.name] = {n.targets[0].id: n.value for n in node.body
                                               if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)}
            if isinstance(node, (ast.Import, ast.ImportFrom)): self.imports.update((a.asname or a.name).split(".")[0] for a in node.names if a.name != "*")
        # every module-level binding, from the count's own walk, and the builtins: a bare name of one not a constant is classified by
        # _base (resolve's Name arm): a top-level import, def or class statement that is the name's one module-level binding, or a
        # builtin no module-level binding shadows, is a value slot when nothing rebinds the name (self.rebound) and the module holds no
        # star import, and any other is refused with the reason _module_why gives
        self.names = set(dir(builtins)) | set(self.bound)
        self.memos = {x for x in res.writes.get(rel, {}) if x in self.consts}   # the module containers some code writes (Scan's walk)
        self.rebound = set(res.rebinds.get(rel, {}))   # the names a function binds under `global` or a module-level statement writes
        self.pieces, self.files, self.problems = [], [], []
        self.joins, self.noted = {}, set()   # the joins of string constants (_note), and the `+` nodes a chain already recorded
        self.held = []   # every locals map a context built, held for the pass: a local read is keyed on its map's id, never reused
        self.scopes = {}   # id(function) -> (the function, its _locals): each function's body walked once per pass, each context given copies
        self.def_ctx = {}   # id(nested function) -> (the function, the context of the function its def statement stands in): its defaults' scope

    @staticmethod
    def _locals(fn):
        """(name -> every value bound to it in the function's own body: a single-name assignment, an augmented or annotated one, a
        loop, unpacking or with target's source, a walrus, and a local container's appended or stored values; the other names the
        body binds (an except name, a deleted name); the functions defined inside it; name -> the forms that bind it in the
        function's scope, for row (d): "value" for a name with values here, "comp" for a comprehension's target, "except", "import",
        "def", "class", "del", "match", "store" for any other name a store binds, "global" and "nonlocal" for a declaration, and
        "nonlocal" too for a name a function or class nested in this one declares nonlocal). Nested defs, classes and lambdas are
        not entered, but a def's or a class's header and a lambda's defaults are read as this function's statements (_header), so a
        walrus there is a local with its value."""
        out, bound, nested, stack, src, mut, forms, stores, comp = {}, set(), {}, list(fn.body), {}, {}, {}, set(), set()

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
            elif isinstance(n, ast.comprehension):
                comp.update(t.id for t in ast.walk(n.target) if isinstance(t, ast.Name))
            elif isinstance(n, (ast.MatchAs, ast.MatchStar)) and n.name: form(n.name, "match")
            elif isinstance(n, ast.MatchMapping) and n.rest: form(n.rest, "match")
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Del): form(n.id, "del")
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name): out.setdefault(n.targets[0].id, []).append(n.value)
            elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name): out.setdefault(n.target.id, []).append(n.value)
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None: out.setdefault(n.target.id, []).append(n.value)
            elif isinstance(n, (ast.For, ast.AsyncFor)):
                for t in ast.walk(n.target):
                    if isinstance(t, ast.Name): src.setdefault(t.id, []).append(n.iter)
            elif isinstance(n, ast.Assign):   # an unpacking (or a chained assignment): each target name reads the value
                for tg in n.targets:
                    for t in ast.walk(tg):
                        if isinstance(t, ast.Name) and isinstance(t.ctx, ast.Store): src.setdefault(t.id, []).append(n.value)
            elif isinstance(n, (ast.With, ast.AsyncWith)):
                for it in n.items:
                    for t in (ast.walk(it.optional_vars) if it.optional_vars is not None else ()):
                        if isinstance(t, ast.Name): src.setdefault(t.id, []).append(it.context_expr)
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

    def _ctx(self, fn, cls, outer=None, where=None):
        """(the value-slot names: parameters and the other names the body binds, the locals, the class, the nested functions, the
        place's name for SERVED_ALLOW, name -> the forms that bind it in the innermost function scope that binds it: _locals's and
        "param"); a nested function's context (outer given) sees the enclosing function's names and locals under its own, and its
        own binding of a name decides over the enclosing one's. A name the function declares `global` names the module's binding:
        it is no local here, and the module's binding is read."""
        a = fn.args
        params = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs} | ({a.vararg.arg} if a.vararg else set()) | ({a.kwarg.arg} if a.kwarg else set())
        got = self.scopes.get(id(fn))
        if got is None: got = self.scopes[id(fn)] = (fn, self._locals(fn))   # the function held with its entry, so its id is never reused
        local, bound, nested, forms = got[1]
        local, bound, nested, forms = dict(local), set(bound), dict(nested), {k: list(v) for k, v in forms.items()}
        for p in params: forms.setdefault(p, []).append("param")
        gl = {k for k, v in forms.items() if "global" in v}
        if outer is not None:
            params, local, nested, forms = params | outer[0], dict(outer[1], **local), dict(outer[3], **nested), dict(outer[5], **forms)
        for k in gl: local.pop(k, None); nested.pop(k, None)
        self.held.append(local)
        ctx = (params | bound) - gl, local, cls, nested, where or fn.name, forms
        for k, n in got[1][2].items():   # the defs this function holds run their defaults here (_defaults)
            if k not in gl: self.def_ctx[id(n)] = (n, ctx)
        return ctx

    def _defaults(self, call, fn, bound, dctx, label, done, cls_node=None):
        """Read the default value of each parameter of a followed function that the call may omit, as the call's argument would be
        read, since the omitted parameter takes that value: a positional parameter the call's plain positional arguments do not
        reach (the first `bound` bound already, self for a method; none past a starred argument) and no keyword names, and a
        keyword-only one no keyword names, each read once per route in the context of the scope its def statement runs in (dctx:
        the module's for a module function or a method, the enclosing function's for one defined in it). Every default of a function
        carrying a decorator is read, since a decorator may change which argument binds a parameter. A method's default that names
        a name the class body binds is refused by name (the census does not read a class body as a scope), and so is any default
        the reader cannot read, as resolve refuses it."""
        a = fn.args
        pos = a.posonlyargs + a.args
        kw = {k.arg for k in call.keywords if k.arg}
        plain = next((i for i, x in enumerate(call.args) if isinstance(x, ast.Starred)), len(call.args))
        pairs = list(zip(pos[len(pos) - len(a.defaults):], a.defaults)) + [(x, v) for x, v in zip(a.kwonlyargs, a.kw_defaults) if v is not None]
        for x, v in pairs:
            i = pos.index(x) if x in pos else None
            if not fn.decorator_list and (i is not None and i - bound < plain or x.arg in kw and x not in a.posonlyargs): continue   # the call passes it
            if ("default", id(v)) in done: continue
            done.add(("default", id(v)))
            if cls_node is not None and any(isinstance(n, ast.Name) and _binding_forms(cls_node, n.id)[0] for n in ast.walk(v)):
                if not self._allowed(dctx[4], v):
                    self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                         % (self.rel, v.lineno, ast.unparse(v)[:60], _CLASS_DEFAULT))
                continue
            self.resolve(v, dctx, label, done)

    def _path(self, e, local=None, depth=0):
        """The repository-relative path a pathlib expression spells: `ROOT / "ui" / "x.css"` through the module's constants (and a
        local's one binding, given the function's locals), with Path(__file__) as this file and .parent as its directory; None
        when the census cannot read it."""
        if depth > 32: return None   # a constant bound through itself (`X = X.parent`) is not a path the census reads
        if isinstance(e, ast.Name) and local and e.id in local and len(local[e.id]) == 1: return self._path(local[e.id][0], None, depth + 1)
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Div) and isinstance(e.right, ast.Constant) and isinstance(e.right.value, str):
            left = self._path(e.left, None, depth + 1)
            return None if left is None else (left + "/" if left else "") + e.right.value
        if isinstance(e, ast.Name):
            if e.id in self.consts: return self._path(self.consts[e.id], None, depth + 1)
            return None
        if isinstance(e, ast.Attribute) and e.attr == "parent":
            base = self._path(e.value, None, depth + 1)
            return None if base is None else os.path.dirname(base)
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "resolve": return self._path(e.func.value, None, depth + 1)
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id in ("Path", "open") and e.args:
            a = e.args[0]
            if isinstance(a, ast.Name) and a.id == "__file__": return self.rel
            if isinstance(a, ast.Constant) and isinstance(a.value, str): return a.value
            return self._path(a, None, depth + 1)
        return None

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
        """A builtin no module-level binding shadows and nothing rebinds: a name the module binds (`format = lambda ...`, one
        bound in a try) is the module's, never the builtin, and so is one a function binds under `global` or a module-level
        statement writes (Result.rebinds), and every name in a module that holds a star import or in a file that may write its
        builtins or its own module namespace through a computed name (_namespace_flags: it names `__builtins__`, imports the
        builtins module, writes a module spelled "builtins" (an attribute store, a setattr or delattr, or a write through its
        `__dict__` or vars()), or writes its own namespace through globals() or vars(), or through a store, setattr, delattr,
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
        builtins (it names `__builtins__`, imports the builtins module or writes a module spelled "builtins": an attribute store, a
        setattr or delattr, or a write through its `__dict__` or vars()); its one
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
        name, a value slot, but refused as a callee when it shares a module function's name; ('follow', None) for a callee that is a
        nested def, the name's one binding in the scope, and ('unread', "a function or class object") for that def as a bare name or
        a receiver; and ('unread', why) for everything else: a comprehension's target, a function-level import, a nested class, a
        del, a match capture, a name a nonlocal declaration rebinds, any other store, and a name bound two ways (two different
        binding forms in one scope, or a nested def or class beside any other binding; every value form, an assignment, augmented
        or annotated, a loop, with or unpacking target and a walrus, is the one form "value", and a parameter the body also binds
        by one is one local)."""
        forms = ctx[5].get(name)
        if not forms or "global" in forms: return None
        kinds = set(forms)
        if "nonlocal" in kinds: return "unread", "a name a nonlocal declaration rebinds"
        if "value" in kinds and kinds <= {"value", "param"}: return ("unread", "a call") if callee else ("local", None)
        if kinds in ({"param"}, {"except"}):
            if callee and name in self.defs:
                return "unread", "a parameter sharing a module function's name" if "param" in kinds else "an except name sharing a module function's name"
            return "exempt", "a parameter or a name the body binds"
        if forms == ["def"]: return ("follow", None) if callee else ("unread", "a function or class object")
        if len(kinds) > 1 or len(forms) > 1 and kinds & {"def", "class"}: return "unread", "a name the function binds two ways"
        return "unread", {"comp": "a name a comprehension binds", "import": "a name the function binds by an import",
                          "class": "a name the function binds by a class statement", "del": "a name the function deletes"}.get(
                              forms[0], "a name the function binds another way")

    def _base(self, e, ctx):
        """What a receiver or a container derives from: ('exempt', why) for a base whose own text the pass does not read (a top-level
        import that is the name's one module-level binding, a builtin no module-level binding shadows (a call of super() is refused:
        its methods are a base class's), each with nothing rebinding
        the name and no star import in the module: _sole and _builtin; a parameter or a name the body binds from one, a BoolOp over
        those; a call of one of those, or of a method on one, whose arguments receiver reads as text: _chain_args), ('readable',
        why) for one resolve reads, ('unread', why) otherwise, a call the reader does not resolve among them. A name the page
        function's scope binds is decided by that scope (_scoped) before the module's binding, as a bare name and as a callee."""
        params, local, cls, nested, where, scope = ctx
        if isinstance(e, (ast.Constant, ast.JoinedStr, ast.List, ast.Tuple, ast.Dict, ast.Set, ast.BinOp, ast.IfExp)): return "readable", "an expression"
        if isinstance(e, ast.Name):
            v = self._scoped(e.id, ctx)
            if v is not None: return ("readable", "a name") if v[0] == "local" else v
            if e.id in self.consts: return "readable", "a name"
            if e.id in params: return "exempt", "a parameter or a name the body binds"
            if e.id in self.imports and self._sole(e.id): return "exempt", "an import"
            if self._builtin(e.id): return "exempt", "a builtin"
            if (e.id in self.funcs or e.id in self.methods) and self._sole(e.id): return "unread", "a function or class object"
            return "unread", self._module_why(e.id)
        if isinstance(e, (ast.Attribute, ast.Subscript)): return self._base(e.value, ctx)
        if isinstance(e, ast.Call):
            f = e.func
            if isinstance(f, ast.Name):
                v = self._scoped(f.id, ctx, callee=True)
                if v is not None: return ("unread", "a function's return") if v[0] == "follow" else v
                if f.id in self.funcs and self._sole(f.id): return "unread", "a function's return"
                if f.id in self.imports and self._sole(f.id): return "exempt", "an import"
                if f.id == "super" and self._builtin(f.id): return "unread", _SUPER   # its methods are a base class's, page text of their own
                if self._builtin(f.id): return "exempt", "a builtin"
                if f.id in params: return "exempt", "a parameter or a name the body binds"
                if (self.star or self.computed or self.shadowed and f.id in self.builtins and not self.bound.get(f.id)
                        or f.id in self.bound and f.id in self.block and self.bound[f.id] == 1): return "unread", self._module_why(f.id)
                return "unread", "a call"
            if isinstance(f, ast.Attribute):
                if isinstance(f.value, ast.Name) and f.value.id == "self" and cls and f.attr in self.methods.get(cls, {}): return "unread", "a method's return"
                return self._base(f.value, ctx)
            return "unread", "a call"
        if isinstance(e, ast.BoolOp):
            kinds = [self._base(v, ctx)[0] for v in e.values]
            return ("exempt", "a BoolOp looked through") if all(k == "exempt" for k in kinds) else ("unread", "a BoolOp")
        return "unread", type(e).__name__

    def receiver(self, r, whole, ctx, label, done):
        """The receiver of a method call, or the container of a subscript or an attribute, `r` in the page expression `whole`: a
        name bound as a module constant or a local is read (a run-time memo is named in SERVED_ALLOW or refused); a BoolOp is
        looked through to each operand; a base whose own text the pass does not read passes, and the arguments of every call it
        derives through are read as text (_chain_args: `dict(X).get(k)` reads X); anything else is a SERVED line by name unless
        SERVED_ALLOW names the place, a call the reader does not resolve among them. A name the page function's scope binds is
        decided by that scope (_scoped) before the module's binding."""
        params, local, cls, nested, where, scope = ctx
        if isinstance(r, ast.BoolOp):
            for v in r.values: self.receiver(v, whole, ctx, label, done)
            return
        if isinstance(r, ast.Name):
            v = self._scoped(r.id, ctx)
            if v is not None and v[0] == "local": self.resolve(r, ctx, label, done); return
            if v is None and r.id in self.consts and r.id not in params:
                if r.id in self.memos: self._memo(r.id, whole, where); return
                self.resolve(r, ctx, label, done); return
        kind, why = self._base(r, ctx)
        if kind == "exempt":   # its own text not read, but a call it derives through carries its arguments' (`dict(X).get(k)` reads X)
            for a in self._chain_args(r): self.resolve(a, ctx, label, done)
            return
        if kind == "readable": self.resolve(r, ctx, label, done); return
        if not self._allowed(where, whole):
            self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                 % (self.rel, whole.lineno, ast.unparse(whole)[:60], why))

    @staticmethod
    def _chain_args(e):
        """The arguments of every call a receiver or a container derives through, down the path _base reads (an attribute's or a
        subscript's value, a method call's receiver, a BoolOp's operands), innermost first: each is read as text, as a bare name
        is, since a builtin's, an import's, a parameter's or a method's arguments are page text (`dict(X)`, `list(X)`, `sorted(X)`
        and `json.loads(json.dumps(X))` carry X's values)."""
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
        first place); a `.format` called on such with such arguments; a `.format_map` with a dict of
        such under string keys; and a `.replace` of such by such. Implicitly concatenated literals are one constant already. A
        field or width wider than a million characters is not expanded (resolve refuses it by name: _wide), and a join Python
        would refuse is none."""
        if isinstance(e, ast.Constant): return (e.value, [(e.lineno, e.col_offset, -1)], False) if type(e.value) is str else None
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add):
            l, r = _Served._const_text(e.left), _Served._const_text(e.right)
            return (l[0] + r[0], l[1] + r[1], l[2] or r[2]) if l and r else None
        if isinstance(e, ast.JoinedStr):
            parts = _Served._fparts(e)
            return None if None in parts else ("".join(p[0] for p in parts), [k for p in parts for k in p[1]], any(p[2] for p in parts))
        if isinstance(e, ast.Dict):   # a `%` or `.format_map` operand: its values under string keys
            if not all(isinstance(k, ast.Constant) and type(k.value) is str for k in e.keys): return None
            vals = [_Served._const_text(v) for v in e.values]
            return None if None in vals else ({k.value: v[0] for k, v in zip(e.keys, vals)}, [x for v in vals for x in v[1]], True)
        if isinstance(e, ast.Tuple):   # a `%` operand
            vals = [_Served._const_text(v) for v in e.elts]
            return None if None in vals else (tuple(v[0] for v in vals), [x for v in vals for x in v[1]], True)
        got, wide = None, lambda ws: any(w and int(w) > 10 ** 6 for w in ws)   # a width or precision over a million is not expanded
        try:
            if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mod):
                l, r = _Served._const_text(e.left), _Served._const_text(e.right)
                if l and r and type(l[0]) is str and not wide([w for m in _PCT_SPEC.finditer(l[0]) for w in m.groups()]):
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
                    keys = [k for i, v in enumerate(items) for k in (base[1] if i else []) + v[1]]
                    got = (base[0].join(v[0] for v in items), list(dict.fromkeys(keys)) or base[1], True)
                else:
                    args = [_Served._const_text(a) for a in e.args]
                    kw = [(k.arg, _Served._const_text(k.value)) for k in e.keywords]
                    if None in args or any(k is None or v is None for k, v in kw): return None
                    if attr == "format" and all(type(a[0]) is str for a in args) and all(type(v[0]) is str for _, v in kw):
                        if not wide([w for _, _, spec, _ in string.Formatter().parse(base[0]) if spec for w in re.findall(r"\d+", spec)]):
                            got = (base[0].format(*[a[0] for a in args], **{k: v[0] for k, v in kw}),
                                   base[1] + [x for a in args for x in a[1]] + [x for _, v in kw for x in v[1]], True)
                    elif attr == "format_map" and len(args) == 1 and not kw and isinstance(args[0][0], dict):
                        got = (base[0].format_map(args[0][0]), base[1] + args[0][1], True)
                    elif attr == "replace" and len(args) == 2 and not kw and all(type(a[0]) is str for a in args) and args[0][0]:
                        got = (base[0].replace(args[0][0], args[1][0]), base[1] + args[1][1], True)
        except (TypeError, ValueError, KeyError, IndexError, AttributeError, OverflowError, MemoryError):
            return None
        return got if got is not None and type(got[0]) is str else None

    @staticmethod
    def _wide(e):
        """Whether `e` is a `%` or a `.format` of string constants with a field or precision wider than a million characters, which
        _const_text does not expand and resolve refuses by name."""
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Mod):
            l = _Served._const_text(e.left)
            ws = [w for m in _PCT_SPEC.finditer(l[0]) for w in m.groups()] if l and type(l[0]) is str else []
        elif isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "format":
            b = _Served._const_text(e.func.value)
            try: ws = [w for _, _, spec, _ in string.Formatter().parse(b[0]) if spec for w in re.findall(r"\d+", spec)] if b and type(b[0]) is str else []
            except ValueError: ws = []
        else: return False
        return any(w and int(w) > 10 ** 6 for w in ws)

    def _join(self, e, where):
        """A `%`, `.join`, `.format`, `.format_map` or `.replace` of string constants recorded as a join (_note), or, too wide to
        expand (_wide), refused by name."""
        if self._wide(e): self._unread(e, "a format field wider than a million characters, which the census does not expand", where)
        else: self._note([self._const_text(e)])

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
        text at its start or end joins the operand beside it); every `+` node inside is marked read (self.noted)."""
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Add):
            self.noted.add(id(e)); return self._chain(e.left) + self._chain(e.right)
        if isinstance(e, ast.JoinedStr): return self._fparts(e)
        c = self._const_text(e)
        return [c if c is not None and type(c[0]) is str else None]

    def _note(self, ops):
        """Record each run of operands that are all string constants (_const_text), side by side in a `+` chain or an f-string or
        alone in a `%`, `.join`, `.format`, `.format_map` or `.replace`, as a join (self.joins: its keys -> (the keys in the text's
        order, the text)) when it holds two literals or more, or its text is more than its literal: served_texts scans its text
        beside each literal's own read."""
        run = []
        for op in list(ops) + [None]:
            if op is not None: run.append(op); continue
            keys = [k for o in run for k in o[1]]
            if len(keys) > 1 or any(o[2] for o in run): self.joins.setdefault(frozenset(keys), (keys, "".join(o[0] for o in run)))
            run = []

    def resolve(self, e, ctx, label, done):
        """Add the text `e` evaluates to under ctx (the value-slot names, the locals, the class, the nested functions, the place's
        name, the scope's binding forms) as pieces and file slots; `done` holds the names already followed for this route, so a
        constant, a function or a local is read once per route and a cycle stops. A name, a receiver's base and a callee the page
        function's scope binds are decided by that scope (_scoped) before the module's binding."""
        params, local, cls, nested, where, scope = ctx
        if isinstance(e, ast.Constant):
            if isinstance(e.value, str): self.pieces.append((label, e.lineno, e.value, (e.lineno, e.col_offset, -1)))
            elif e.value is None or type(e.value) in (bool, int) or e.value == b"" and isinstance(e.value, bytes):
                pass   # a value slot: None, a bool, an int or the empty bytes, no text of its own
            else: self._unread(e, _CONSTANT_KINDS.get(type(e.value), "a %s Constant" % type(e.value).__name__), where)
        elif isinstance(e, ast.JoinedStr):   # each part keyed at its own line: the part's on 3.12 and later, else where the expression before it ends
            self._note(self._fparts(e))   # its literal parts and constant fields side by side, a join (served_texts)
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
            if isinstance(e.op, ast.Add) and id(e) not in self.noted: self._note(self._chain(e))   # its runs of string constants, joins
            elif isinstance(e.op, ast.Mod): self._join(e, where)   # a `%` of string constants, a join (served_texts)
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
            done.add(key); names, loc = set(), dict(local)
            for g in e.generators:
                for n in ast.walk(g.target):
                    if isinstance(n, ast.Name): names.add(n.id); loc[n.id] = [g.iter]
            # a target is the comprehension's own local, read from its source, and a callee so bound is refused as "a call"
            self.held.append(loc); self.resolve(e.elt, (params - names, loc, cls, nested, where, dict(scope, **{n: ["value"] for n in names})), label, done)
        elif isinstance(e, ast.Dict):
            for x in e.keys + e.values:
                if x is not None: self.resolve(x, ctx, label, done)
        elif isinstance(e, ast.Set):
            for x in e.elts: self.resolve(x, ctx, label, done)
        elif isinstance(e, (ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr, ast.Starred)):
            if e.value is not None: self.resolve(e.value, ctx, label, done)
        elif isinstance(e, ast.BoolOp):
            for x in e.values: self.resolve(x, ctx, label, done)
        elif isinstance(e, ast.Name):
            v = self._scoped(e.id, ctx)
            if v is not None and v[0] == "local":
                key = ("local", id(local), e.id)   # a local read once per function per route: `x = x.replace(...)` reads itself
                if key in done: return
                done.add(key)
                for val in local.get(e.id, ()):
                    if isinstance(val, ast.Call) and isinstance(val.func, ast.Attribute) and val.func.attr in _READ_CALLS:   # a file read bound to a slot
                        self.files.append((label, val.lineno, e.id, self._path(val.func.value, local), where, val))
                    else: self.resolve(val, ctx, label, done)
            elif v is not None:   # a value slot the scope binds (a parameter, an except name) or a nested function passes; any other form is refused
                if v[0] == "unread" and v[1] != "a function or class object" and not self._allowed(where, e):
                    self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                         % (self.rel, e.lineno, ast.unparse(e)[:60], v[1]))
            elif e.id in self.consts:
                if e.id in self.memos and e.id not in params: self._memo(e.id, e, where)
                elif e.id not in done: done.add(e.id); self.resolve(self.consts[e.id], (set(), {}, None, {}, e.id, {}), e.id, done)
            elif e.id in params or e.id in nested: pass   # a value slot: a parameter or a name the body binds, a nested function
            elif e.id in self.names or self._global_only(e.id):   # a module-level binding that is no constant (an import, a builtin, a
                # function or a class passes), or a name only a function or class body binds, under a global declaration
                kind, why = self._base(e, ctx)
                if kind == "unread" and why != "a function or class object" and not self._allowed(where, e):
                    self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                         % (self.rel, e.lineno, ast.unparse(e)[:60], why))
            elif e.id == "__file__" and not self.star and e.id not in self.rebound:   # the module's own path, which the import system binds
                # a value slot only where no statement of the file binds it, in any scope and by any form, and the file writes no name
                # of its module namespace through a computed name; otherwise refused by name
                why = self.computed_why if self.computed else _FILE_BOUND if self.file_bound else None
                if why is not None: self._unread(e, why, where)
            else:   # a name bound nowhere the census reads
                self.problems.append("SERVED %s:%d builds a served page from %s, text the census did not read" % (self.rel, e.lineno, ast.unparse(e)[:60]))
        elif isinstance(e, ast.Call):
            f = e.func
            if isinstance(f, ast.Attribute) and f.attr == "join" and not e.keywords and (
                    (len(e.args) == 1 and isinstance(e.args[0], (ast.Set, ast.SetComp)))   # `"".join({...})`
                    or (len(e.args) == 2 and isinstance(e.args[1], (ast.Set, ast.SetComp)))):   # unbound, `str.join("", {...})`
                return self._unread(e, "a join over a set, whose order is not fixed", where)   # a set's iteration order is not fixed, so its join is no one text
            if isinstance(f, ast.Attribute) and f.attr in _READ_CALLS: self.files.append((label, e.lineno, ast.unparse(f.value)[:40], self._path(f.value), where, e))
            elif isinstance(f, ast.Attribute) and f.attr in _TEXT_CALLS + _FOLLOW_ANY:
                self._join(e, where); self.resolve(f.value, ctx, label, done)   # a join of string constants among them
            elif isinstance(f, ast.Name) and self._scoped(f.id, ctx, callee=True) is not None:   # a callee the scope binds: never the module's
                kind, why = self._scoped(f.id, ctx, callee=True)
                if kind == "follow":   # a function defined inside the page function, the name's one binding there, over its names
                    key, fn = ("nested", id(nested[f.id])), nested[f.id]
                    if key not in done:
                        done.add(key)
                        for r in self._returns(fn): self.resolve(r, self._ctx(fn, cls, self.def_ctx.get(id(fn), (None, ctx))[1], where + "." + f.id), label + "." + f.id, done)
                    self._defaults(e, fn, 0, self.def_ctx.get(id(fn), (None, ctx))[1], label + "." + f.id, done)
                elif kind != "exempt" and not self._allowed(where, e):
                    self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                         % (self.rel, e.lineno, ast.unparse(e)[:60], why))
            elif isinstance(f, ast.Name) and f.id in self.funcs and self._sole(f.id):   # a module function, the name's one module-level binding
                fn = self.funcs[f.id]
                if f.id not in done:
                    done.add(f.id)
                    for r in self._returns(fn): self.resolve(r, self._ctx(fn, None, None, f.id), f.id, done)
                self._defaults(e, fn, 0, (set(), {}, None, {}, f.id, {}), f.id, done)
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "self" and cls and f.attr in self.methods.get(cls, {}):
                key, fn = cls + "." + f.attr, self.methods[cls][f.attr]
                if key not in done:
                    done.add(key)
                    for r in self._returns(fn): self.resolve(r, self._ctx(fn, cls, None, key), key, done)
                self._defaults(e, fn, 1, (set(), {}, None, {}, key, {}), key, done, self.classes[cls])
            elif isinstance(f, ast.Attribute): self.receiver(f.value, e, ctx, label, done)   # any other method call: its receiver
            else:   # any other callee: an import, a builtin or a parameter passes (_base), anything else is refused by name
                kind, why = self._base(e, ctx)
                if kind != "exempt" and not self._allowed(where, e):
                    self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                         % (self.rel, e.lineno, ast.unparse(e)[:60], why))
            for a in e.args + [k.value for k in e.keywords]: self.resolve(a, ctx, label, done)   # a value slot's arguments are text too (json.dumps(x))
        elif isinstance(e, ast.Subscript):
            self.receiver(e.value, e, ctx, label, done)
        elif isinstance(e, ast.Attribute):
            base = e.value
            owner = cls if isinstance(base, ast.Name) and base.id == "self" else base.id if isinstance(base, ast.Name) and base.id in self.class_attrs else None
            if owner and e.attr in self.class_attrs.get(owner, {}):   # a class attribute the class body binds
                key = ("class attribute", owner, e.attr)
                if key not in done:
                    done.add(key); self.resolve(self.class_attrs[owner][e.attr], (set(), {}, owner, {}, owner + "." + e.attr, {}), owner + "." + e.attr, done)
            else: self.receiver(base, e, ctx, label, done)
        elif isinstance(e, ast.Lambda):   # read: its body is page text (a replacement function's return), its parameters value slots
            a = e.args
            for d in a.defaults + [d for d in a.kw_defaults if d is not None]: self.resolve(d, ctx, label, done)   # run where it stands
            lp = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs} | ({a.vararg.arg} if a.vararg else set()) | ({a.kwarg.arg} if a.kwarg else set())
            loc = local if not lp & set(local) else {k: v for k, v in local.items() if k not in lp}
            if loc is not local: self.held.append(loc)
            self.resolve(e.body, (params | lp, loc, cls, {k: v for k, v in nested.items() if k not in lp}, where,
                                  dict(scope, **{p: ["param"] for p in lp})), label, done)
        else:   # every other kind (a Compare, a UnaryOp, a Slice, and a kind with no arm above): no text the census reads
            self._unread(e, "a%s %s expression" % ("n" if type(e).__name__[0] in "AEIO" else "", type(e).__name__), where)

    def _unread(self, e, why, where, line=None, shown=None):
        """A page position holding a kind resolve does not read (the kind named in `why`): a SERVED line at its line, or at `line`,
        showing the expression, or `shown`, unless SERVED_ALLOW names the place."""
        if not self._allowed(where, e):
            self.problems.append("SERVED %s:%d builds a served page from %s (%s), text the census did not read"
                                 % (self.rel, e.lineno if line is None else line, (ast.unparse(e) if shown is None else shown)[:60], why))

    def run(self, routes):
        for call, fn, cls, ctype, body in routes:   # the body routes_of read: the call's second positional argument
            before = len(self.pieces), len(self.files)
            where = ((cls + ".") if cls is not None else "") + fn.name if fn is not None else "<module>"
            ctx = self._ctx(fn, cls, None, where) if fn is not None else (set(), {}, cls, {}, "<module>", {})
            self.resolve(body, ctx, fn.name if fn is not None else "<module>", set())
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
    text of each join _Served._note records (a `+` or f-string's run of string constants, a `%`, a `.join` over a list, tuple or
    dict literal, a `.format`, `.format_map` or `.replace` of them) scanned too, at its first literal's line, each record it finds
    beyond what its
    literals' own reads find added, so a load split across such a join is read and a site both reads find is listed once (a `.join`
    over a set, bound or unbound as in `str.join("", {...})`, whose order is not fixed, is no such join: resolve refuses it by
    name; a fetch
    or import() argument, or a program call's arguments, that run past a joined literal's end are left to the join's text, which
    reads them whole: line_scan's `cut`); a file
    a page reads at run time is covered by the walk when it is a scanned kind (not scanned again), named when it is a
    stylesheet, excused when SERVED_ALLOW names the read, and a SERVED problem otherwise."""
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
    for label, lineno, name, path, where, expr in sorted(sv.files, key=lambda f: (f[1], f[5].col_offset)):
        if path is not None and path in res.files: continue
        if path is not None and path.endswith(".css"):
            if (rel, lineno, path) not in res.served_files: res.served_files.append((rel, lineno, path))
        elif not sv._allowed(where, expr): res.problems.append("SERVED %s:%d reads %s for a served page, a file the walk does not scan" % (rel, lineno, path or name))
    res.problems.extend(sv.problems); res.served.append(rel)


def scan(root):
    res = Result(); bootstrap = None; served = []
    for rel, kind in walk(root, res):   # each file's text is read once here: a Python file strictly, the others with replacement
        res.files.append(rel)
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

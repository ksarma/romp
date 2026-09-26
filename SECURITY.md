# Security

romp runs a local kernel and a local message bus on your machine, and drives
Claude Code sessions on your behalf. This document states the trust model it
assumes, what that means on a shared machine, and how to report a vulnerability.

## Trust model: token-gated, same-user by file permission

Two local services run on your machine:

- the **kernel** (dashboard/API) on `127.0.0.1:29855`, and
- the **postal bus** (inter-session messaging) on `127.0.0.1` (a fixed local port).

Both bind **loopback only** (`127.0.0.1`); neither is exposed to your network by
default. On top of that, **every request requires the serve token — loopback
included** (the model Jupyter uses, for the same reason: loopback is one network
stack shared by every local UID, so it cannot be a trust boundary by itself).

The token (`~/.local/state/romp/serve-token`) is 144-bit random, stored at mode
`0600`, and compared with a constant-time check — **file permissions are the
same-user gate**. Same-user clients (the CLI, hooks, the bus, the VS Code
extension) read the file and send it as an `X-Romp-Token` header; the browser
presents it once as `?token=` (print the ready-made link with `romp url`, or
paste the token into the login page a bare open of the dashboard serves) and
rides an `HttpOnly` cookie afterwards. That cookie authorizes only when the
request's Origin is one the gate accepts: the dashboard's own origin (the
`Host` the request arrived at, or the kernel's own port on `127.0.0.1` or
`localhost`), any `vscode-webview://` origin (every VS Code webview, not
only romp's own), or no `Origin` header at all. The check protects the
browser surfaces, the WebSocket upgrade included, against cross-site
requests. It is needed because cookies are scoped by host and
**not by port** (RFC 6265 §8.5): every `http://127.0.0.1:<port>` page on your
machine is same-site with the dashboard, so anything else you run on loopback
(a dev server in a repo an agent cloned) would otherwise ride your cookie into
`/ws`, which streams every session and accepts text to send into any of them. A
request with no `Origin` header passes on its cookie because a same-origin
navigation and non-browser clients send none; a page on another loopback port
loading an `<img>` aimed at the kernel sends none either and still carries the
cookie, which is why the hold behind `/busy?drain=1` arms only for an
explicitly presented token (a request without one still gets the count and arms
nothing): while a `romp refresh --quiet` waits for the sessions to finish their
turns, that hold keeps every session from starting a new turn, a side effect no
subresource load may trigger. A token presented explicitly, as `?token=` or
`X-Romp-Token`, is accepted from any Origin: federated (cross-machine) calls
need it, and a cross-site page cannot obtain it: the dashboard drops `?token=`
from its address as it loads, and every page the kernel serves carries
`Referrer-Policy: same-origin`, so the token never reaches another origin in a
`Referer`, with one exception that Network access below states: an inline
svg's paint reference on a page whose own address carries `?token=`.
The token-exempt routes are the no-side-effect liveness probes (`/healthz`,
`/version` and `/busy` on the kernel, `/ping` on the bus) and the install files:
`/manifest.webmanifest` and the three home-screen icons under `/media/`
(`romp-touch-180.png`, `romp-app-192.png`, `romp-app-512.png`, a fixed allowlist
of names, not a path prefix). A browser fetches those with credentials omitted
when the dashboard is added to a home screen, so a token gate there would break
the install. They are static and read no session state: the manifest is a
fixed JSON literal (app name and short name, display mode, colors, start URL
and icon list) and the icons are three PNG files.

The practical consequence: another local user on a **shared machine** cannot
reach your kernel or bus — `/send` (which injects text into a live Claude
session that runs tools as you) and bus mail both require a token only your
UID can read.

## Residual cautions on shared machines

- The token gate protects against other **non-root users**. Root (or the host
  operator of a container/VM) can read any file and inspect any process — no
  userspace design changes that. Don't keep long-lived credentials on hosts
  whose root you don't trust.
- **Do not** set `ROMP_SERVE_HOST` to `0.0.0.0` or a LAN address on an untrusted
  network — the token still gates every request, but it widens the surface; use
  an ssh tunnel or `tailscale serve` instead, which keep the listener on
  loopback.
- For defense-in-depth on Linux you can still run romp inside a per-user
  **network namespace** (`unshare -n`) or rootless container, so its loopback is
  not even reachable by other users' processes.

## What is already hardened

- **Loopback-only binds** for the kernel and bus (above).
- **Serve token required on every request, loopback included**: 144-bit random,
  stored `0600`, constant-time compare; Origin gate on the dashboard and the
  WS upgrade. Federated (cross-machine) calls authorize with the remote
  machine's token, carried over ssh tunnels the local machine initiates.
- **Path-traversal guards** on every id/name/message-id that becomes a filesystem
  path component under the mail and outbox roots (`_safe_id`), so a crafted
  reference like `../../etc` is rejected before any path join.
- **No shell interpolation:** subprocess calls use argv lists (no `shell=True`);
  remote `ssh` targets are validated and argv-guarded with `--`.
- **Output sanitization:** model output and message content rendered in the
  dashboard/webview pass through DOMPurify; the VS Code webview runs under a
  strict nonce CSP with `localResourceRoots` limited to the extension's assets.
  The profile is modelled on the rules GitHub applies to a README
  (`ui/webview/md-sanitize.ts`, shared by the chat and the file viewer): no
  `<style>`, no form controls, no image map, ids and names prefixed
  `user-content-`, an inline `style` reduced to its color declarations, no
  `background` attribute; unlike GitHub it keeps that color-only inline `style`
  and inline SVG. One renderer writes into that sanitized DOM after DOMPurify
  has run: KaTeX. The sanitizer keeps only color in an inline `style`, and
  KaTeX's layout is inline style, so a formula's TeX passes through DOMPurify
  as the text of an inert placeholder and KaTeX renders it there afterwards,
  under `trust: false` (KaTeX's own safety model: no TeX command writes a link,
  an image, or an HTML attribute of the author's choosing), with a cap on the
  sizes a formula asks for, a per-formula cap on macro expansion, and length
  caps on one formula and on one message or note; a formula over a length or
  expansion cap is shown as its source, and a size over its cap is clamped.
  That boundary is checked against the code by
  `ui/webview/md-sanitize-postpass-browser.test.ts`; the profile, as the browser
  lays a file out, by `ui/webview/md-sanitize-browser.test.ts`. The bounds are
  stated under "Slice 1" in `plans/markdown-viewer.md` and checked against the
  code by `ui/webview/render-math.test.ts` and
  `ui/webview/md-sanitize-postpass-browser.test.ts`.
  While the **Comments** panel is open, pdf.js parses a PDF in a Worker on the
  dashboard's origin and paints each page onto a canvas, with pixels as its
  only sink: no text layer, annotation layer, form field, link, or script from
  the file reaches the DOM. That puts a PDF beside the untrusted files the
  viewer already renders on this origin (markdown through marked and
  DOMPurify, source through highlight.js); with the panel closed a PDF opens
  in the browser's own viewer, as before. The properties that limit this
  (pdf.js is handed bytes, never a URL, so it fetches nothing; the installed
  build has no eval path; only its core is bundled; a size cap and a page cap;
  the browser's viewer as the fallback) are stated under "Security posture" in
  `plans/file-review.md` and checked against the code by
  `ui/webview/file-review-posture.test.ts`.
- **No unsafe deserialization:** no `pickle`, `eval`, `exec`, or non-safe YAML on
  untrusted data.

## Federated messaging: per-host trust

romp can attach other machines so their sessions appear in one dashboard and can
exchange postal messages with yours. Because a message that lands in an agent's
context is a prompt-injection surface, **each attached host carries a trust
level** you set in the network popover (persisted per host):

- **trusted** — full two-way postal, no gating. For a machine you control (your
  laptop, your home server).
- **directed** (the **default** for a newly attached host) — you can send work
  *to* that host's sessions, but its mail to you is **held for approval**, never
  auto-injected. Each held message appears as a needs-you card ("incoming postal
  message from X to Y") with **Approve** (deliver), **Edit** (change the text
  first), and **Deny** (drop) — a human decides before any of that host's content
  reaches one of your agents. This is the safe posture for rented/shared compute
  (a cloud VM, a RunPod box): you can drive it, it cannot drive you.
- **isolated** — no postal at all in either direction; the host's sessions are
  visible in the dashboard but its bus never peers with yours.

The trust unit is the **machine**, not a session on it: any process on a remote
box can write to that box's bus, so trust is set per host. Identity is provided
by the ssh tunnel the message arrives on — no separate signing. The gate is
enforced at the receiving bus's delivery point, so it holds regardless of which
host originated the message.

A **forwarded** message is judged by the more restrictive of two tiers: the
origin's and the forwarding host's. The origin stamp is written by the forwarder
and nothing signs it, so trusting it alone would let any peer claim to speak for
a host you tiered `trusted` and have its mail auto-injected — a `directed` host
could promote itself simply by labelling its cargo. Capping at the forwarder's
own tier means a directed relay stays directed whatever name it stamps, at the
cost that mail from a trusted origin relayed through a directed hub is held for
approval rather than delivered.

The one thing romp can NOT firewall this way is same-machine peers: two sessions
running as the same user share a UID, so mailbox trust between them is policy,
not a security boundary (the enforceable lines are per-UID, from the serve token,
and per-machine, from this trust level).

## Network access

By default the kernel opens one connection of its own to a host other than the
model provider: it fetches a public model-pricing table
(`raw.githubusercontent.com/.../model_prices_and_context_window.json`) at a
build of the Token usage view's payload (`/analytics`), on an open of the view
or a period picked in it, when this kernel has made no fetch attempt yet, or
its last attempt is more than six hours old, with no credential. The kernel
stamps the attempt before the fetch runs, so a fetch that fails or lands
nothing holds the six hours like one that landed, and the first open of the
view after a start always fetches. The response is parsed strictly as numeric
pricing. The kernel's other connections, and the programs it runs that connect
on their own, are listed below. The list is derived from the code by
`python3 scripts/network-inventory.py`, run from the repository root: the
script walks kernel/, cli/, postal/, bin/, hooks/, ui/, vscode-extension/src
and the install scripts, and reads the pages the kernel serves from its own
text, for every site that opens a connection or starts a program, compares what
it finds with the counts committed beside it in
`scripts/network-inventory-expected.json`, and exits 1 naming any site it
cannot place, any count that differs, any HTTP or socket client it does not
know and any row of its table that names no site; the test suite runs it
(`tests/test_price_feed_census.py`). vendor/track-changents is runtime code,
reached by relative imports from walked files (the dashboard's ui sources, a
session hook and the file-comments host) and by install.sh's links into
~/.claude, and it is not walked. A load written there is no site and no line,
and the import gate does not read its imports. The pages the kernel serves and
its service worker's script, from its own string constants (the dashboard shell,
the seven pane pages, the token login page, the too-large page and /sw.js, with
the shim, the timeline boot and the shell scripts they inline), are read from
kernel.py's syntax tree and scanned as browser text keyed kernel/kernel.py plus
tool, with the DOM loads counted. The routes are derived from the calls of
`_send` the scan reads (spelled `_send(...)` or `<x>._send(...)`; a call through
a name computed at run time is not read) and every Content-Type header written
outside `_send`, in every scanned Python file. A `_send` call's content type is
read through the definition it reaches, the one def or async def statement that
binds `_send` in its file, direct in the call's own class body (a call through
self) or in the module (a bare call): the kernel's Handler._send writes its
`ctype` parameter, so the call's third argument or its `ctype=` keyword; the
postal bus's writes application/json; the session host's and its transport's
write a frame to a Unix socket and answer no HTTP request (FRAME_WRITERS), and
any other definition that writes no Content-Type fails the run. So does each
`_send` call in a file that binds `_send` more than once outside function bodies
(the module and every class body counted together, a class body a function body
defines included, since a class body is no function body, in any binding form
but a comprehension's target, which binds only in its comprehension) or other
than by one def statement direct in a class body or the module, or where a
function or a class body binds it under a `global` declaration, rebinding the
module's name at run time, each bare call that reaches a `_send` bound inside a
function, a lambda, a
comprehension or a class body around it, in any form (a parameter, a nested def,
a loop target, a lambda's parameter and a comprehension's target among them; the
line names the scope and the binding), each call that reaches no definition the
census reads, the line saying why (a `_send` the call's own class body does not
bind, for a call through self: inherited or set at run time; one reached through
an object other than self, or through an attribute outside any class body; a
`_send` no scope the bare call
looks it up in binds, the module included; and, in a file that names `_send`
nowhere but as the called name of those calls, so binds it nowhere at all, a
definition the file does not hold), each call to a definition
carrying any decorator, whose
parameters the census does not read, and each bare call in a module that holds a
star import. An override of `_send` in a subclass that another file defines is
not read: a call
through self is typed through its own class body's definition. The type is read
through a module name no code writes after binding it (one plain single-name
assignment binds it as a top-level statement, nothing else at module level binds
it, a walrus in a def's
or a class's header included, the module holds no star import, and nothing in
the file writes that name, in any scope: a subscript store or delete, a call
`<name>.<method>(` of a method _MUTATORS or _DUNDER_MUTATORS lists, a call of
such a method on a type _CONTAINER_TYPES lists with the name as its first
argument (`dict.update(<name>, ...)`), a binding in a function that declares the
name `global` (as the target of an assignment, an augmented assignment, a loop,
a comprehension, a with or a walrus, or by an import, a def or class statement
or an except clause) or a module-level augmented assignment), through a local
whose every binding is read (a walrus in a nested def's, class's or lambda's
header is a binding it does not read) and through a dict literal's values; the
part before any `;`, stripped and lower-cased, is compared with the types a
browser runs script from (SCRIPT_TYPES: text/html; the XML types text/xml,
application/xml, text/xsl and any type with a `+xml` suffix, image/svg+xml and
application/xhtml+xml among them; and text/javascript under each name a browser
takes for JavaScript, application/javascript among them). A script-running
route's page body is the call's second positional argument, read only when the
call passes it positionally, with no starred argument before it and no `**`, and
the definition's one output is its one `self.wfile.write(<its second positional
parameter>)`, with nothing in its signature or body outside the node kinds, in
their roles, of the kernel's Handler._send: that write, the definition's last
statement, directly after its one `self.end_headers()`, and before them
send_response with its one argument and send_header, called on self as
statements; isinstance, str, len, and getattr of self with a string-constant
name and a None default, where neither the definition nor the module binds the
name, nothing rebinds it (no function binds it under a `global` declaration, no
module-level statement writes it, and the file does none of the writes listed
below that rebind every builtin) and the module holds no star import; the
one rebinding of the page parameter to itself encoded, its one argument the
string constant `"utf-8"` (`body = body.encode("utf-8") if isinstance(body, str)
else body`); a loop over a parameter's items (`for k, v in (headers or
{}).items():`) and an if on a parameter or on that getattr, each into header
calls; header values built from string constants holding no CR or LF,
parameters, the loop's targets, attributes read on self, str, len and a `%`
format on a string constant; and a signature of positional parameters, none
positional-only, with None defaults and no annotation. Any other script-running
call fails the run by name,
its reason naming the road (a second write, a write through an alias, a print to
a stream and, for any other statement or expression, its node kind and line
among the reasons), among them a keyword body, a starred or `**` call, a
definition whose one write is of another parameter, a local or an expression, or
that writes nothing, a method's definition that binds self again, in any form (a
lambda's or a nested def's parameter among them), or declares it global, any
other read of an attribute named `write`, `writelines`, `send`, `sendall`,
`sendfile` or `sendmsg`, called or not, a string constant equal to one of those
names, a reference to the write's receiver other than as its receiver, and in
the definition a statement after the end_headers (which writes the header buffer
to the stream, so a header call after it would reach the body), a second
end_headers or none, any other rebinding of the page parameter, another codec
name or a second argument to `.encode` (either can name a codec or an error
handler the file registers at run time), a store or delete of an attribute or a
subscript, a read of a name the module binds, a call not listed above, and a
nested def, class or lambda. The reader governs the definition's own text, and
code the definition runs from outside that text is not read: a header value is
not scanned, and a response that a Content-Type in its headers argument, passed
or defaulted, makes a page is outside the served pass, the call being typed by
its content-type argument; nor is code the definition runs through an object it
is handed (a parameter's methods, its mapping's items, its __str__), code behind
a name the definition calls or reads on self (a header method, a property or
`__getattr__`, however the class, a base or other code defines or replaces it)
and any stream that code writes, or a `_send` replaced at run time through a
name no code spells (setattr or a class `__dict__` with a computed name, a
metaclass namespace key, a base's `__init_subclass__`). The census does not see
a module namespace rewritten at run time by code outside the forms listed below
that rebind every name: a listed name reached any other way or a name the list
does not hold (through `__self__` of a builtin, a container or a copy of a
namespace mapping, a module's own `__setattr__` or `__delattr__` method, a
listed name, attrgetter or methodcaller imported from a module other than its
own, a name built at run time, gc or ctypes among them, and through a module
reached by a tuple or list unpacking, an inline walrus,
`sys.modules.__getitem__`, a for-loop target, a parameter default or a starred
argument) is outside the list and not seen,
and a module
name or a builtin so rewritten is read as the file's text binds it. A `_send`
definition in a class that a function
defines, and a page function that a function encloses,
fail the run by name: the census does not read the enclosing function's scope,
so it would take a name that function binds (a builtin or a module name it
shadows) for the module's. The page
function of each script-running route is followed to the text it returns or
inlines, and a
parameter a followed call omits is read from its default value as that argument
would be, in the scope the def statement runs in (a default the pass cannot read
is refused by name, among them a method's default naming a name its class body
binds). A name the
page function's scope binds, or for a function defined in it an enclosing
function's scope, is decided by that scope and never by the module's binding: a
local (a parameter the body also assigns, a walrus in a nested def's, class's or
lambda's header, and a comprehension's target inside its comprehension among
them) is read from its values as a bare name or a receiver and refused as a
callee; a parameter or an except name is a value slot, refused as a callee when
it shares a module function's name; a function defined in the page function is
followed as a callee only as its name's one binding there; a name the function
declares `global` is the module's binding, read as such; and any other binding
refuses, a comprehension's target elsewhere in the function, a function-level
import, a nested class, a del, a name a nonlocal declaration rebinds and a name
bound two ways (two different binding forms in one scope, or a def or a class
statement beside any other binding of it; every value form, an assignment,
augmented or annotated, a loop, with or unpacking target and a walrus, is one
form, and a parameter the body also binds by one is one local, read from its
values) among them. In that text the served pass reads a
BoolOp's operands, a method call's receiver and a subscript's container when
they name a module constant (a name one plain single-name assignment binds as a
top-level statement and nothing else binds at module level, in a module with no
star import that writes no name of its module namespace through a computed name
and may not rewrite it at run time, as listed below) or a local, the
receiver of `.encode` or `.format_map` whatever it is, a class attribute the
class body binds, a loop, unpacking or with target from its source, and a local
container's appended or stored values; it passes over a base whose own text it
does not read (in a module that holds no star import, a top-level import
statement that is its name's one module-level binding and is not rebound, or a
builtin that no module-level binding shadows and that is not rebound, a call of
super() excepted, whose methods are a base class's; a parameter, an except name,
or a name the function binds from one of those),
reading as text the arguments of a call of such a base or of a method on one
(`dict(X).get(k)` and `json.loads(json.dumps(X))[0]` read X), and over a bare
module name that is such an import or such a builtin, or, in such a module, a
top-level def or class statement that is its name's one module-level binding and
is not rebound. Text such a base holds is not read, as with code behind a name
on self: a constant that a sibling module defines and the page imports, or an
attribute set on self or another parameter before the call. A name is rebound
when a function binds it under `global` or a statement at module level writes
it, in one of the forms listed above for a route's type; every name is rebound,
as under a star import, in a file that writes its module namespace through a
computed name (globals() or vars() used any way but for a `.get` read, the
`__dict__` or vars() of a module the file may be, or a store, setattr or delattr
on that module; globals, vars, setattr and delattr each reached in the first
three of the four ways below, and any of those four read other than as a call; a
module the file may be is `sys.modules[k]` or `sys.modules.get(k)`, on any name
or attribute spelled `modules`, or a call of `__import__` or import_module
reached in those three ways with the first argument k, where k is no string
constant, `__name__` among them, or is "__main__" or a dotted name whose last
part is the file's own module name; a name that an assignment (as a name target,
alone or in a chain), an annotated assignment or a walrus binds to one of these,
read by that name; or an if-expression or a boolean operation with one of these
among its operands) or that may rewrite it at run time by
one of these forms, each named with its line in the reason: an import from the
file's own package (a relative import, an import under its top package, the file
itself among them, an import naming the file's own bare stem, its working
absolute name when its directory runs as a script, or `__main__`), which closes
every
write through the name by one arm; an attribute named `__globals__`,
`__builtins__`, f_globals, f_builtins or f_locals, on any receiver; a listed
callable (locals, exec, eval, compile, `__import__`, import_module or _getframe)
reached in the first three ways; or one of those callables or attributes,
globals, vars, setattr, delattr or `__dict__` reached in the fourth. The four
ways, the whole of the reach the census reads for each of these names
(`__dict__` in the fourth alone, beside the attribute the computed-name forms
above name): by its own name, in any context; by a name
an import anywhere in the file binds to it from its module (locals, exec, eval,
compile, `__import__`, globals, vars, setattr and delattr from builtins,
import_module and
`__import__` from importlib, _getframe from sys), in any context, read as the
name itself; as an attribute of that name on a builtins receiver
(`__builtins__`, a name that `import builtins [as X]` or `from X import builtins
[as Y]` binds, for any module X, `sys.modules["builtins"]` or
`sys.modules.get("builtins")`, or `__import__("builtins")` or
`import_module("builtins")`, a call of either reached in these ways), or on any
receiver for exec, eval, locals, `__import__`,
import_module and _getframe; or by its name spelled as a string, or as a join of
string constants that reads as one, where a run-time lookup by name takes it
(the second argument of getattr, setattr, delattr or hasattr, called by its
name, by a name an import binds to it or as an attribute of a builtins receiver;
any argument of operator.attrgetter (any dotted part of the name) or
operator.methodcaller, called as `.attrgetter` or `.methodcaller` on a name that
`import operator [as X]` or `from X import operator [as Y]` binds, for any
module X, or by a name that `from operator import attrgetter [as Y]` or `from
operator import methodcaller [as Y]` binds; or a key
on a namespace
expression: a subscript's slice, or the first argument of `.get`, `.pop`,
`.setdefault` or a `__getitem__`-family call, whose receiver is a `__dict__`,
`__builtins__` or a call of vars, globals or locals reached in the first three
ways). Every builtin is rebound in such a file and in a
file that names `__builtins__`, imports the builtins module or writes a module
spelled "builtins" (an attribute store, a setattr or delattr, or a write through
its `__dict__` or vars()). A function's `X = []` of a local of the same name, or
its `X.append(...)`, does not rebind it. It follows a call whose callee
is a module function (a top-level def statement that is its name's one
module-level binding, not rebound, in a module with no star import, and bound by
no function scope of the page), a function defined in the page function or a
method of the route's class (to what it returns, any decorator on it not
applied), a text method or a file read, or any other method (through its
receiver, as above, so `_K.__call__(t)` on a module constant `_K` that holds a
lambda reads `_K` and the lambda's body, whose parameters are value slots), and
it reads every call's arguments; a call to any other callee passes when the
callee is such an import, such a builtin or a parameter. It reads both operands
of a `/`, a path join, where `__file__` is a value slot when no statement of the
file binds it, in any scope and by any form, the file neither writes a name of
its module namespace through a computed name nor may rewrite it at run time and
the module holds no star import, and is refused by name otherwise. It reads a
lambda's body, its
parameters value slots, and its defaults where the lambda stands. A None, bool
or int constant, the empty bytes constant and a `*` or `<<` over int constants
are value slots with no text. The run fails by name (SERVED) on
any other reference to `_send` (a read of it that is not a call's function, a
store or delete of an attribute so named, or a string equal to `_send`), a
content type the pass cannot read, a script-running
type written outside `_send`, a function that answers outside `_send` more often
than it writes a Content-Type header, a container the module writes at run time,
any other receiver or container, any other callee (a module constant, a local, a
class, a subscript, a call and a lambda among them), any other bare module name
(one bound other than by one assignment, one bound by an annotated, unpacking or
chained assignment, one annotated at module level beside its assignment, one no
module-level statement binds that a function or a
class body binds under a `global` declaration, an import, a function or a class
beside
another module-level binding, an import, a def or a class bound once inside a
module-level block and not by a top-level statement, a name bound once in any
other form inside such a block's body, a name a star import may rebind, a module
name in a file that writes its module namespace through a computed name or may
rewrite it at run time (the reason naming the form and its line), a builtin in a
file that may rewrite the builtins, and a rebound import, builtin,
function or class among them), any other kind of
expression in a page (a non-empty bytes, float, complex or Ellipsis constant, an
f-string's format spec, any other operator, a comparison and a unary expression
among them), and a route whose text the pass cannot read, unless the served
allowlist, SERVED_ALLOW, names the place
by its function and expression, with the number of places the entry covers and
the reason (the two answers with no body, the CORS preflight's 204 and the
websocket upgrade's 101, are named there); an entry that names nothing in the
run, or covers a different number of places, fails the run too. In served text
every `fetch(` and `import(` on a line is read by its own argument, and no
comment skip applies, since a joined constant is one line whatever it starts
with. Each string literal is read on its own, and so is the text of each of
these joins of string constants, at its first literal's line: a `+` of them
(an f-string's literal text at its start or end among them), an f-string whose
fields are string constants, a `%`, `.format` or `.format_map` of them, a
`.join` over a list or tuple of them or over a dict literal whose keys they are
(the keys in order, a repeated key at its first place) and a `.replace` of them
(implicitly concatenated literals are one constant already). A tool's name, a
tag, an
attribute, an import or a fetch URL split across such a join is therefore read
whole, and a site both reads find is listed once; a fetch URL cut at the join is
listed as the joined text reads it, whole. Text a page joins through anything
but a string constant (a name, a call, an attribute, or a field or a `%` slot
holding one) is read piece by piece: a tool's name, a tag or an
attribute split there is not seen, and a fetch
URL cut there is classed by the part before the cut. A `.join` over a set
literal or a set comprehension, its one argument or, unbound as in
`str.join("", {...})`, its second, refuses by name, its iteration order not
fixed, so its join is no one text. A file the page reads at
run time is covered
by the walk when it is a
scanned kind, and a stylesheet is named, not scanned. The shell and browser
sides are matched by a named list with no completeness gate: a tool or a client
the lists do not name is no site and no line; the Python side's gate is
module-granular: an import outside the allow-list fails the run, and a
primitive of a known module outside NET and SUB is not a site. Two refusals
cover what the JavaScript binding patterns and the import gate do not read,
each an IMPORT line unless the JavaScript allowlist, JS_ALLOW, names the place
by its file and expression, with the number of places the entry covers and the
reason; an entry that names nothing in the run, or covers a different number of
places, fails the run too. First, a literal specifier of a family module
(`http`, `https`, `net`, `tls`, `ws` or `child_process`) that the import gate
reads is read only where a binding the patterns read takes the module from it,
whole or by names, or an arm reads a call through it
(`require('http').request(`); a require or an `await import()` taken whole does
not count when `.`, `?`, `[` or `(` follows it past whitespace and comments,
and a brace list that takes `default` does not count unless the same statement
binds that name whole (`import { default as X }`), so a require in a later
declarator, `require("http").get` read as a value, a destructured default, a
require assigned after its declaration, a `.then()` callback of `import()` and a
re-export are each refused; and in a walked file a binding the patterns match
whose specifier stands on a line led by `//`, `/*` or `*`, where the gate reads
no module, is refused as a binding on a line led by `//`, `/*` or `*`, whose
module the gate does not read; the webview leg's pin sees such a binding when
the line
is code (a `*`-led continuation of an import) and none on a comment line or in a
template literal's text. Second, on a walked line the scan reads (not in
served text), a require or import the gate cannot read is refused: a call of
`require` in any other shape (whitespace or a comment before the paren, a
template or a computed specifier), `require` as a bare value (followed by `;`,
`,`, `)`, `}`, `]` or the end of the line, outside a string and a comment, where
a quote opens a string to the same quote's next occurrence on the line that no
backslash escapes, `/*` outside a string opens a comment to the next `*/` on the
line or the line's end, and `//` outside a string opens a comment to the line's
end), any `.require(` call, any member access on `require`, a
`createRequire(` call, and an `import(` with a template specifier
or with whitespace or a comment before its paren. So every
literal specifier of a family module that the gate reads is read or refused,
and on a walked line every require the gate cannot read is refused when it is
spelled in one of those shapes; one spelled another way (a computed member such
as `module["require"]`, `require` beside an operator, a createRequire under
another name) is no site and no line. A client is read through a call on the
module or on a binding the patterns read: a dotted call on an inline require or
on a name the file keeps the module under, or a call of a bare name the file
binds from it, each read only as spelled on one line with nothing between the
require or the name, the dot, the method and the paren (`http.get(`), or between
the bare name and the paren (`get(`), and `ws` by its constructor shape, read
with whitespace before its paren too (`new WS (u)`, `new W.WebSocket (u)`). A
client reached from such a binding any other way is no site and no line, among
them a member alias (`const g = http.get`), a destructure from the binding
(`const { get } = http`), a computed member, `.call`, an optional chain, a call
spelled with whitespace or a comment around the dot or before the paren
(`http . get(`, `http.get (`, `get (`) and a call split across lines before its
paren (`http` at the end of one line and `.get(` at the start of the next); an
inline require called either of the last two ways is refused by the first
refusal. The import gate reads a specifier in a literal require() or
import() spelled whole on one line (the name, its paren, the quoted specifier
and the closing paren, with nothing between them but whitespace inside the
parens), wherever it stands, in a side-effect import that begins its line
(`import`, whitespace alone, then the quoted specifier), and in the first `from`
string (`from`, whitespace alone, then a quoted specifier) on a line that starts
with import or export or that continues an import or export statement that
begins its own line and has not yet ended, and, in a walked file, any line led
by a closing brace. In a walked file such a statement
opens at `import` (not `import(` or `import.meta`), `export {`, `export *`,
`export type {` or `export type *` and ends at the line where the gate reads its
`from` string or at a line that ends with `;` outside a string and a comment;
any line of it is read whatever leads it but a line led by `//`, `/*` or `*`,
which is skipped, a binding on one refused by the first refusal. Over the walked
files the webview
leg's pin (ui/webview/import-gate-parse.test.ts) holds these reads equal to a
TypeScript parse of the same files (the specifier of each import and export
declaration, of `import X = require()`, of a require or import() call on a
quoted literal and of an import type), both ways, keyed on file, line and
specifier, and holds each require or import() call whose first argument is not a
quoted literal to a line where the second refusal fires (an import() on a
computed argument that is not a template, to a browser-computed-url site), so a
specifier in a layout the line reader does not read is red there by file, line
and specifier. Served text is not parsed, and the pin does not hold it: there
such a statement opens at any line that starts with import or export (not
`import(` or `import.meta`), a line continues it only when led by `from` or a
closing brace, and no line is skipped as a comment. Through a binding whose
specifier the gate reads, `https`, `net` and `tls` still fail the run at the
gate, so this residual reaches `http`, `ws` and `child_process`, the packages
the list knows; in served text, through a binding the patterns read from a
specifier the gate does not read, among them one on the line after a trailing
`from`, one on a continuation line led by anything but `from` or a closing
brace, one in a require() or `await import()` split across lines and one in a
statement that does not begin its line, it reaches `https`, `net` and `tls` as
well. A comment between `from` (or a side-effect `import`) and its specifier is
read by neither the gate nor the binding patterns, so in served text a client
through it is no site and no line whatever the module, `https`, `net` and `tls`
included, and a package outside KNOWN_JS_IMPORTS passes the gate.
The first refusal also refuses a line that binds nothing to call, such as
`import type http from "http"` or `let a: typeof import("http")`; no such line
is live. An echo- or print-led shell line is skipped as a printed remedy only
when nothing live follows the printed text: the text outside quotes and the
body of every `$(...)` and backtick substitution, wherever it stands, are
scanned by the interpreter arm and the tool list, so `echo "$body" | curl ...`
and `echo "rate: $(curl ...)"` are sites and a remedy that names a tool inside
quotes is not. On the browser and editor side a client the list names is a site
through a dotted call on an inline require or on a name the file keeps the
module under, a call of a bare name the file binds from it, or, for `ws`, its
constructor shape (a call through a computed member, `.call` or an optional
chain, one spelled with whitespace or a comment around the dot or with a comment
before its paren, one spelled with whitespace before its paren other than `ws`'s
constructor, which is read so too (`new WS (u)` and `new W.WebSocket (u)` are
sites), or one split across lines before its paren is no site), the connection
family read through its bindings as the child_process family is: a `get` or
`request` of `http` or `https`, a `connect` or `createConnection` of `net` and a
`connect` of `tls` through an inline require, a name the file keeps the module
under (a require or an `await import()` assigned whole in the first declarator
of its declaration, TypeScript's `import X = require()`, a namespace or default
import, alone or the two in one statement, a default beside a brace list,
`import { default as X }`), or a bare name the file binds from the module by a
brace list, alone or beside a default, in an import, a destructured require or a
destructured `await import()` (renamed or not), and `ws` by its constructor
shape (`new <binding>(`, `new <namespace>.WebSocket(`, `new (require('ws'))(`),
each an added arm beside the literal spellings (`http.get(`, `net.connect(`, the
bare global `new WebSocket(`), a call the literal list already names on a line
counted once under the same tool. NET and SUB are the script's lists of the
connection and command primitives it reads. Four classes of outbound activity
the scan cannot
derive are named and counted in its table rather than left out: an external
program started whose far end its arguments do not show (a shell, node, perl or
python as the program, whether the kernel starts it, a shell script of romp's
runs its text inline (`python3 -c`, a heredoc, `node -e`), or the manager or
the editor extension starts it; a command run through a shell; git with a
subcommand the code does not spell out; an argv the code does not spell out); a
program whose text is supplied at run time (a watch predicate, the apiKeyHelper
or a login's token command); a browser request whose URL is computed at run
time (a fetch, or a dynamic import of a module); and the loads the browser
makes on its own for what a page inserts (an image, a frame, a script, a link).
A fifth is named in the table and not counted, since the scan cannot see it: a
socket primitive called on a receiver the census cannot resolve (an
attribute-held or parameter socket) is not a site here. Two kinds of browser
request are also named in the table and not counted, since the content shown,
not a line of this tree, names what they load: an inline svg's paint references
in the chat's file preview and in a notice card, and the loads of an .svg
opened in its own tab.

`ROMP_PRICE_FEED=off` in the kernel's environment (`service.env` for the
installed service, then a manager restart) stops that fetch: the Token usage
modal then prices tokens from the built-in defaults and says so on the line
under its footnote, and `/version` says the same in its `priceFeed` block.
Only the value `off`, whitespace and case ignored, turns the feed off; any
other value leaves it on, and the kernel says so on its stderr, on that line
and in that block. The reference documents the switch under
[The price feed](docs/reference.md#the-price-feed).

The kernel's other connections of its own by default go to the model provider:
the Models API catalog refresh, on the apiKeyHelper's key or else the
`ANTHROPIC_AUTH_TOKEN` bearer from its environment (`ROMP_MODEL_CATALOG=off`
stops it; with neither credential it sends nothing), and, when an apiKeyHelper
is configured, the fast-mode probe on that key at every key-billed session
connect and, for the judges, once per judge process and again after a fast
refusal. By default the kernel also runs programs that connect on their own:
`git ls-remote` against the release remote, at boot and then every six hours
for the release check, on a clone whose VERSION file names a release, and
every five minutes for the drift check, on a checkout on branch main, in
update mode auto, or with a machine attached or remembered
(`ROMP_UPDATE_CHECK=off`, or the gear's update mode off, stops both);
`git ls-remote --heads origin` in a viewed file's checkout when its branch has
no local tracking ref; the session CLIs and the judge CLIs, which talk to
their providers on the session's or the call's billing; one `npm install`
when a bundle rebuild fails at boot; and, in the browser rather than the
kernel, the pictures a viewed markdown file loads from the hosts on the gear's
Pictures from the web in files list, which starts as github.com, its image and
asset hosts, localhost and 127.0.0.1 (a figure from any other host makes no
request until you click it; removing a host from the list stops its loads).
Also in the browser, with no click and no setting of yours: on the web
dashboard the chat's rendered markdown (a session's reply, your own message, a
postal body) loads an image, video, audio, srcset or picture media from the
host its URL names the moment it renders (a video's poster and an inline svg's
image load the same way), with whatever cookies that browser sends to that
host and no Referer to any other origin (every page the kernel serves
carries `Referrer-Policy: same-origin`). Every other text the chat page renders
as markdown loads its media the same way: the text a Continue press sends, a
message romp or another program sent to the session on your behalf, a note or
notice the harness injected (a command's output, a scheduled task's firing), a
notice from romp, a compaction summary, a background task's report, a
subagent's skill text, prompt and report, a peer agent's message and an agent's
reply in a file comment thread. An inline svg's paint references load with no
click on three surfaces of the web dashboard: the chat's rendered markdown,
when it renders; the chat's file preview, the card that opens on a pointer
dwell of 350 ms or a keyboard focus on a link in the chat to a markdown file
the kernel allows to preview (one in the session's folder or your home; a
glossary term links to its section the same way); and a notice card's body on
the feed page, which a session writes through POST `/notice` (`romp card`),
when the feed paints the card. The file preview and the notice card strip an
image, video, audio, a poster and an svg image before the nodes join the page,
so only the paint references load there. On all three, in Chromium a `fill`,
`stroke`, `clip-path`, `mask`, `marker-start`, `marker-mid` or `marker-end`
whose `url()` names another host loads from that host, in Firefox and WebKit at
least a `mask` does, and a `filter` does in no engine; each such request
carries no cookie and carries the page's origin (the dashboard's scheme, host
and port, the port omitted when it is the scheme's default) in its Origin
header; in Chromium a `mask` request can also carry that origin as its Referer,
from any page, framed or bare; and a paint request can carry the full page
address with the serve token in its Referer, but only when the page's own
address carries `?token=` (a pane page opened bare, such as `/chat?token=`; the
shell drops the token from its address before it frames its panes, and frames
them without it); these paint requests are the one exception to the trust
model's sentence on `Referrer-Policy: same-origin` (the response is blocked as
cross-origin; the request, with those headers, has reached the host); the
editor extension's webviews block these loads by their content security policy,
so this is the web dashboard's alone.

The other connections open when something sets them up, you or a session you
are running: an attached machine (ssh commands to it and tunnels to it, and
everything over them, a Pull of its checkout included); a PR watch
(`gh pr view` on a cadence, registered with `romp watch-pr`, which asks `gh`
for the repository's name when given no `--repo`); a watch predicate, which a
session registers on its own (`romp watch`, POST `/watch`; no setting of yours
gates it), after which the kernel runs the registered text through `/bin/sh`
on the cadence the registration names (no faster than every 15 seconds, every
60 by default) until it exits 0, its bound (24 hours by default) or a cancel,
re-armed at boot, and what the command itself sends is not romp's; a
subscribed phone (web push, encrypted end to end); the apiKeyHelper or
stored-login command you configured; and an update taken from the banner or
by the auto mode (`git fetch`, then for a release `install.sh` with pip and
npm, through `bin/romp-sdk-setup` and `vscode-extension/install.sh`; the
editor extension's update prompt runs `vscode-extension/install.sh`
(`npm install` and `npx`) on your click, not the root `install.sh`, so a click
reaches the npm registry and not PyPI). Whoever starts it,
`vscode-extension/install.sh` runs `npm install` against the npm registry on
every run; `npx --yes @vscode/vsce package`, a fetch of vsce from the same
registry even when it is cached, runs only when an editor CLI is present
(`code`, `code-insiders`, `cursor` or `codium` on PATH, or an editor bundle
under `ROMP_EDITOR_APPS`) or `ROMP_EXT_PACKAGE_ONLY` is set; with neither the
script exits after the build and sends nothing more. A link you click, in the
browser showing the dashboard or in one of the editor extension's views (a link
in a session's reply or in your own message, a pull-request reference in a
message, a card or an outline row, a URL in a todo's text or the address a todo
carries, a URL in a viewed file, the file viewer's GitHub button, the gear's
sign-in link), opens in a browser that requests the clicked URL from the host
it names with that browser's own cookies: on the web dashboard the browser
showing it, in a new tab; from the editor extension the operating system's
default browser, which `vscode.env.openExternal` hands the URL to. For a
pull-request reference that is the session's repository name and the number, on
github.com; for the file viewer's GitHub button, an address romp composes from
the file's checkout (the owner and repository name from its origin remote, the
current branch or the commit sha when HEAD is detached, and the file's path),
on github.com, offered only for a committed file in a checkout whose origin is
on GitHub; for a link in a message, a todo or a viewed file, whatever its
author wrote, a session, you or a peer; for the sign-in link, the CLI's own
sign-in request to claude.com or claude.ai. The sign-in link, an anchor the
gear builds to open in a new tab, opens by document: on the dashboard's
settings page, which installs no opener, the browser's own open in a new tab,
no site of this tree running; in the editor's chat panel the chat delegate's
`openLink` post to the extension; in the editor's feed panel the webview host's
own link handling, outside this tree. romp adds no serve token, key or login
token to a link's URL, and nothing sends until you click; three anchors the
chat page's click delegate leaves to the default action (one with no scheme
that the page built; one with no scheme in a message that does not resolve to
an http or https address; a message's own download anchor, one with no scheme
carrying a `download` attribute whose href resolves to an http or https address
on this page's origin, which the browser saves from this origin), and a
page-built anchor with a scheme in a document that installs no opener (the
gear's sign-in link on the dashboard's settings page and in the editor's feed
panel is one), are gestures this tree does not route: on the dashboard the
browser's own open or download, and what the editor's own webview host does
with them is outside this tree. Installing by hand (`bootstrap.sh`,
`install.sh`) fetches from GitHub, PyPI (and bootstrap.pypa.io for get-pip.py
when the python lacks ensurepip; `ROMP_NO_GET_PIP=1` skips that fetch) and the
npm registry, and `bin/romp-codex-setup`, run by hand for Codex sessions,
fetches the Codex SDK from PyPI and the pinned Codex CLI from GitHub.

On the web dashboard, a Cmd, Ctrl or middle click on a path link to an .svg in
a viewed file opens the file in the browser's own tab from the kernel's `/file`
route (Cmd or Ctrl with Enter or Space on a focused link does the same; for a
file of a session on an attached machine the tab opens from the
`/remote/<host>/file` relay, which sends the same headers), and the tab is an
svg document, sandboxed so no script runs in it, that loads each resource its
markup names from that resource's host (whether or not the host is on the
gear's Pictures from the web in files list), among them an `image` element's
`href` or `xlink:href`, a CSS `@import`, an `xml-stylesheet` instruction, an
`feImage`, HTML inside a `foreignObject` (an `img`, a stylesheet, a frame, a
video, audio, an object or an embed), a cursor image, a web font, and paint
references: in Chromium a `fill`, `stroke`, `clip-path`, `mask`,
`marker-start`, `marker-mid` or `marker-end` whose `url()` names another host
loads from that host, in Firefox and WebKit at least a `mask` does, and a
`filter` does in no engine; a `use` that names another host loads in no engine;
a frame the markup embeds is a page from that host, which loads what that page
names in turn; a load the browser makes without CORS (an image, a stylesheet, a
frame, a media element, an embedded object, or in WebKit a web font), or a load
the markup marks `crossorigin="use-credentials"` on an `img`, `image`,
`link rel="stylesheet"`, `video` or `audio` element, carries whatever cookies
that browser sends cross-site to that host; a paint reference, a web font in
Chromium and Firefox, or a load the markup marks `crossorigin="anonymous"` on
one of those elements (a video's poster aside), carries none; for a load to
another site: in Chromium none of the tab's own loads carries a Referer, the
sandbox withholding it; in Firefox and WebKit the page's `Referrer-Policy`
withholds it, and markup that relaxes that policy (a referrer `meta` or a
`referrerpolicy` attribute) makes such a load carry at most the dashboard's
origin; a framed page's loads to another site carry at most that frame's
origin, and those a stylesheet names in turn at most that stylesheet's own
address in Chromium and Firefox and what the tab's own loads carry in WebKit;
and the tab's address (`/file?path=...` or `/file?path=...&sid=...`, or its
`/remote/<host>/file` form) carries no serve token.

What those programs send is theirs, not the kernel's: a session's own CLI, the
judges' CLIs, a watch predicate, the API key helper, a login's token program,
`gh`, `git`, `ssh`, `npm` and the browser open connections of their own, and
the census lists such a site by the program it starts, never by where that
program connects. romp sends no telemetry: the kernel's own requests to hosts
other than the machines you attach are the four named above: the price table,
the catalog refresh, the fast-mode probe and web push. Session text goes to
the model provider the session or the judge call is billed to; over your own
ssh tunnels to a machine you attached (the text you send a session there, the
session listings, views and file bodies relayed back, and the postal mail
between the two machines' buses); and, encrypted end to end, to the push
service of a phone you subscribed.

## Reporting a vulnerability

Please report security issues privately via GitHub Security Advisories on the
repository rather than opening a public issue. Include a description, affected
version/commit, and a reproduction if you have one.

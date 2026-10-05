# Security

romp runs a local kernel and a local message bus on your machine, and drives
Claude Code sessions on your behalf. This document states the trust model it
assumes, what that means on a shared machine, and how to report a vulnerability.

## Trust model: token-gated, same-user by file permission

Two local services run on your machine:

- the **kernel** (dashboard/API) on `127.0.0.1:29855`, and
- the **postal bus** (inter-session messaging) on `127.0.0.1` (a fixed local port).

Both bind **loopback only** (`127.0.0.1`); neither is exposed to your network by
default. On top of that, **every request requires the serve token, loopback
included**, presented either directly or through a browser sign-in made with it
(below). This is the model Jupyter uses, for the same reason: loopback is one
network stack shared by every local UID, so it cannot be a trust boundary by
itself.

The token (`~/.local/state/romp/serve-token`) is 144-bit random, stored at mode
`0600`, and compared in constant time: **file permissions are the same-user
gate**. Same-user clients (the CLI, hooks, the bus, the manager, the VS Code
extension) read the file and send it as an `X-Romp-Token` header, or as
`?token=` in the URL (the extension's WebSocket and the requests its webview
makes); an attached machine presents the other machine's token the same way. A
token presented explicitly, as `?token=` or `X-Romp-Token`, is accepted from any
Origin: federated (cross-machine) calls need it, and a cross-site page cannot
obtain it: a browser sign-in stores no copy of it in the browser (below), the
dashboard drops `?token=` and the one-time code from its address as it signs
in, and every page the kernel serves carries `Referrer-Policy: same-origin`, so
the token never reaches another origin in a `Referer`, with one exception that
Network access below states: an inline svg's paint reference on a page whose
own address carries `?token=`.

The practical consequence: another local user on a **shared machine** cannot
reach your kernel or bus. `/send` (which injects text into a live Claude
session that runs tools as you) and bus mail both require the token only your
UID can read, or a browser sign-in made with it.

### Browser sign-in: a session cookie, a page key, per-file capabilities

A browser presents the token once, in one of three ways: the link `romp url`
prints, the sign-in page (`/login`, which a bare open of the dashboard also
shows) with the token pasted in, or a window `romp` opens, which carries a
one-time code in place of the token. That page load signs the browser in and
gives it three kinds of value, each derived from the serve token by HMAC under
a fixed label of its own:

- A **session cookie**. It holds a random session id and an HMAC tag over it,
  is `HttpOnly` and `SameSite=Lax`, lasts a year, and is named for this kernel,
  so two kernels on one host keep separate sessions. On its own it opens only
  the page documents (the dashboard shell and its pane pages) and the static
  files (`/dist/`, `/media/` and `/sw.js`), which hold code, one setting
  (whether task tracking is on), and no session data.
- A **page key**. The sign-in response writes it into this origin's local
  storage; that response is served with `Cache-Control: no-store`, and no other
  response carries the key. The pages send it as an `X-Romp-Key` header (a
  wrapper around `fetch` adds it to requests for the page's own origin only)
  and as `k=` when they open a WebSocket. Every request outside the page
  documents and static files (every JSON read, every POST, the WebSockets and
  every other route) needs the session cookie and the page key together, or,
  for a file, the cookie and that file's capability.
- A **file capability** in each `/file` or `/remote/<host>/file` URL a page
  builds: images, previews, PDF frames, a file opened in its own tab,
  downloads, and the `/file` pictures and links in rendered markdown. These
  loads cannot carry a header. A capability is an HMAC under the page key over
  one host, one path and one session id, as the kernel reads them from the URL
  (percent-decoded), so a spelling of the same file whose decoded path differs
  (a trailing slash, a dot segment, a symlink to it) needs its own. A
  capability is refused on a URL that names the path, the session id or the
  capability twice, and it is honoured for `GET` and `HEAD` only, and only with
  the session cookie of the sign-in that made it.

Because each kind has its own label, a value of one kind is refused wherever
another is required, the serve token included, and the kernel keeps no store of
sign-ins. The session cookie is honoured only when the request's Origin is one
the gate accepts: the dashboard's own origin (the `Host` the request arrived
at, or the kernel's own port on `127.0.0.1` or `localhost`), any
`vscode-webview://` origin (every VS Code webview, not only romp's own), or no
`Origin` header at all, which non-browser clients send and a browser sends on a
`GET` navigation (a frame's included) and on a load made without CORS (a
script, an image), whichever page made it. That is why the cookie alone opens
only the page documents and static files, which hold no session data. The
WebSocket upgrade is checked the same way. A page whose stored key
no longer matches its session (two sign-ins that overlapped, or storage cleared
while the tab was open) gets a refusal of its own and moves to the sign-in
page, as does a page whose origin holds no key. A browser that refuses site
storage cannot keep a page key at all, so its page stays where it is and says
why instead.

When the dashboard shows an attached machine through this kernel
(`/remote/<host>/...`), this kernel checks the browser's sign-in and calls the
other machine with that machine's own token. It forwards none of the browser's
cookie, page key or capabilities, and a relayed WebSocket handshake reaches the
browser with its handshake headers only.

The hold behind `/busy?drain=1` arms only for an explicitly presented token (a
request without one still gets the count and arms nothing): while a `romp
refresh --quiet` waits for the sessions to finish their turns, that hold keeps
every session from starting a new turn, a side effect no subresource load may
trigger.

The token-exempt routes are the no-side-effect liveness probes (`/healthz`,
`/version` and `/busy` on the kernel, `/ping` on the bus), the sign-in page
(`/login`, a static form that reads no state), the push worker's
acknowledgement (`POST /push/ack`, admitted only by the push's own unguessable
id: it records that push's delivery, marks the same device's older unanswered
notifications for that session as replaced, and fills in the device's origin
when it is missing) and the install files:
`/manifest.webmanifest` and the three home-screen icons under `/media/`
(`romp-touch-180.png`, `romp-app-192.png`, `romp-app-512.png`, a fixed allowlist
of names, not a path prefix). A browser fetches those with credentials omitted
when the dashboard is added to a home screen, so a token gate there would break
the install. They are static and read no session state: the manifest is a
fixed JSON literal (app name and short name, display mode, colors, start URL
and icon list) and the icons are three PNG files.

### What a browser sign-in costs, and how it ends

- **Losing the page key signs a browser out.** The key lives in the site's
  storage, which a browser can lose while it keeps the cookie: cleared site
  data, a private window, a browser that clears a site's storage after a week
  without a visit, or an app added to the Home Screen, which keeps storage of
  its own and so may ask for the token once after it is installed. That browser
  signs in again with the token: paste it on the sign-in page, open the link
  `romp url` prints, or run `romp` on the machine to open a signed-in window;
  an app on the Home Screen signs in by pasting the token. Earlier versions
  kept a browser signed in on the cookie alone for a year.
- **A sign-in lasts until the serve token is rotated.** Signing in again in a
  browser that still holds its cookie keeps its session, and with it the
  capabilities already in its URLs, and a new session ends no earlier one.
  Sessions, page keys and capabilities all end when the token is rotated, which
  signs every browser out at once. There is no per-browser sign-out.
- **An address with a capability reads that one file.** A file opened in its
  own tab, a download in the browser's history and a copied image address carry
  their capability; with the session cookie of the same sign-in, it reads that
  file until the token is rotated. It can also read a pinned copy of a picture
  that a message showed (`pin=`), which is named by the SHA-256 of its content,
  so only someone who already has that content can name it.
- **Whatever records a browser's request headers holds its sign-in.** A proxy
  you place between the browser and the kernel that logs headers records the
  session cookie and the page key together, which is a whole sign-in; trust it
  as you trust the browser.
- **Rendered markdown keeps its `/file` pictures and links.** The chat, notice
  cards, a preview provider's HTML, a markdown file's hover preview and the
  file viewer add a capability to each `/file` URL an author wrote, after
  sanitizing, and so do the places that turn typed text into links (a todo's
  or a note's text, a todo's link, a code span holding one address). A message
  can therefore show, or offer for download, any file the kernel's `/file`
  route serves this browser, as it could before; the bytes go only to this
  browser. Pictures that an SVG or a stylesheet names with `url()` get no
  capability, so a `/file` URL there draws nothing.

### Upgrading from a version whose cookie held the token

Before the session cookie, the dashboard kept the serve token itself in a
cookie named `romp_token`. The first dashboard page a browser loads after the
upgrade signs it in and clears `romp_token` in that same response. The kernel
clears `romp_token` only when its value is this kernel's token, so a
`romp_token` that belongs to another romp kernel on the same host is left
alone. Apart from the response that signs the browser in, a response to a
request without a valid session cookie never clears it, so a browser that has
not yet signed in with it keeps it until it does. Every browser that signs in
this way gets the same session, so tabs that reopen together after the upgrade
end signed in; each of those browsers held the serve token itself, and the
session ends, like every session, when the token is rotated. Rarely, and in
testing only in WebKit, one of two tabs that open at the same moment lands on
the sign-in page instead; opening the dashboard again in that tab signs it in
without the token. A dashboard left open across the upgrade keeps running the
page it loaded before, which has no page key: its requests are refused and its
sockets keep redialling until it is reloaded, so reload each open dashboard
once the kernel has restarted. A browser that never loads the dashboard again
keeps `romp_token`, whose value is the serve token and stays valid until the
token is rotated. Rotate the token after upgrading to retire every such
cookie. The steps, and what a rotation signs out, are under "Rotating the
token" in the guide's Security and trust section (`docs/guide.md`).

Going back to an earlier version signs browsers in with `romp_token` again,
and a browser keeps this version's session cookie beside it. When this version
comes back with the same token, that browser sends both, and the kernel clears
`romp_token` in the response to any request that carries it beside a valid
session cookie, so the first response after the return clears it. A browser
that does not come back keeps it, so pair a rollback with a rotation once this
version is back.

## Residual cautions on shared machines

- The token gate protects against other **non-root users**. Root (or the host
  operator of a container/VM) can read any file and inspect any process — no
  userspace design changes that. Don't keep long-lived credentials on hosts
  whose root you don't trust.
- **Do not** set `ROMP_SERVE_HOST` to `0.0.0.0` or a LAN address on an untrusted
  network. The token, or a browser sign-in made with it, still gates every
  request, but it widens the surface; use an ssh tunnel or `tailscale serve`
  instead, which keep the listener on loopback.
- For defense-in-depth on Linux you can still run romp inside a per-user
  **network namespace** (`unshare -n`) or rootless container, so its loopback is
  not even reachable by other users' processes.

## What is already hardened

- **Loopback-only binds** for the kernel and bus (above).
- **Serve token required on every request, loopback included**, directly or
  through a browser sign-in made with it: 144-bit random, stored `0600`,
  constant-time compare. A browser's session cookie opens only the page
  documents and static files; every other request needs its page key or a
  per-file capability as well, and the cookie is honoured only from an accepted
  Origin, the WS upgrade included. Federated (cross-machine) calls authorize
  with the remote machine's token, carried over ssh tunnels the local machine
  initiates.
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
  `<style>`, no form controls, no image map, no `<marquee>`, ids and names prefixed
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
tool, with the DOM loads counted. A string constant is scanned whole; a bytes
constant whose every byte is ASCII is scanned the same way, each byte its own
character, and one holding a byte past ASCII is refused by name (below); and a
name bound
once, by one top-level plain assignment, to a call of `compile` handed a string
or bytes constant (and at most a flags argument that is an int constant, an
attribute of that name, or their `|`) on a name the module binds to the standard
library's `re` by binding is read through its `.search`, `.match`, `.fullmatch`
and `.findall`, and through its `.sub` where the replacement is a string or
bytes constant holding no backslash and no argument is starred or a `**`, which
change nothing, so such a call's arguments are the page text and the compiled
name holds none of its own; any other `.sub` (one whose replacement holds a
backslash, which `re` may expand as a template escape or a group reference into
text the replacement does not spell, or is a name or a callable, and one handed
a starred argument or a `**`, whatever its replacement) is refused by name,
since the census does not model template expansion; `re`'s own `sub` and `subn`,
and a pattern's method called unbound on `re.Pattern`, are no such read but
calls under the call limit (below), their arguments read as spelled and the text
`re` makes of them not read; the proof by
binding is the digest leaf's (below), with its limit, so a module object stored
in sys.modules under that name before the import binds it, or a function of the
module replaced by an attribute store, is not seen. The census reads a page only
where the bytes a browser decodes are the text it scans, which it reads as
UTF-8, so it refuses by name, as a page it cannot read: a bytes constant holding
a byte past ASCII (a byte order mark, whole or split across constants, among
them); page text holding U+FEFF, refused on the safe side because a leading U+FEFF is a byte order mark the page's UTF-8 bytes carry; page text holding a NUL, by which a browser may read interleaved
NULs as UTF-16; page text declaring a charset other than utf-8 (a `charset=` in any
case, as a meta element's charset attribute and a content attribute's parameter
spell it, or an XML declaration's `encoding=`, followed by any label but utf-8,
read in the text as spelled and again with its character references decoded,
since a browser decodes them in an attribute's value before it reads the charset
there) in a string or bytes constant, an f-string's literal part or the joined
text of a join of string constants; a script-running content type whose
parameters name
a charset other than utf-8; and a page's read of a walked browser-text file
whose text, as the walk decoded it, holds U+FFFD, U+FEFF or a NUL, or declares such a
charset. A declaration split across texts the census reads apart (at any join
but the joins of string constants it folds, below: a part other than a string
constant among its pieces, between two literals or as one half, such as a name's
text, a call, a conditional expression or a bytes constant, which the census
reads each on its own, or a compiled pattern's `.sub`, whose replacement it
reads apart from the subject even where both are string constants) is read as
each text spells it. The routes are derived
from
the calls of
`_send` the scan reads (spelled `_send(...)` or `<x>._send(...)`; a call through
a name computed at run time is not read) and every Content-Type header written
outside `_send`, in every scanned Python file. A `_send` call's content type is
read through the definition it reaches, the one def or async def statement that
binds `_send` in its file, direct in the call's own class body (a call through
self: a call on a name that is self by binding, the first positional parameter
of the method the call stands in, however it is spelled, never the spelling
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
bind, for a call through self: inherited or set at run time; a call on a name in
a class body that is not self by binding, the line naming the condition it fails
(the call outside the body of a method defined directly in that class body, or
in that method's header, which runs in the class body; the name not the method's
first positional parameter; a lambda or a comprehension around the call binding
the name; the method binding the name again in any form, or a scope nested in it
rebinding it under a nonlocal declaration; a decorator on the method other than
a name, or a call of a name, that the module binds once by a def statement; the
class body binding the method's name other than by that one def statement, or
declaring it global or nonlocal; the file storing, deleting or naming to a
setter an attribute of the method's name on any object); one reached in a class
body through a receiver that is no name (an object other than self), or through
an attribute outside any class body; a
`_send` no scope the bare call
looks it up in binds, the module included; and, in a file that names `_send`
nowhere but as the called name of those calls, so binds it nowhere at all, a
definition the file does not hold), each call to a definition
carrying any decorator, whose
parameters the census does not read, and each bare call in a module that holds a
star import. An override of `_send` in a subclass that another file defines is
not read: a call through self is typed through its own class body's definition
(where that file binds the page's module by an import statement, the page's file
fails the run, below).
Nor is what a decorator the census accepts on the method (a name, or a call of a
name, that the module binds once by a def statement) does with self, since that
def may hand the method another object in the instance's place (its witness: a
method whose decorator, a def of the file, calls it with an object whose `_send`
serves the page as text/html), or a method replaced on its class at run time
through a name no code spells, a setter whose name argument does not fold among
them (its witness: a method a setattr replaces, its name the return of a call).
The type is read
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
header is a binding it does not read) and through a dict literal's values
(refused before its type is read, below: a call inside a lambda's body, a
Content-Type write inside one that is no `_send` definition's own write, and a
call whose definition binds the parameter one of its own writes names other than
as that parameter); a type holding a CR or LF is refused by name before it is
compared, even at a place SERVED_ALLOW names, where the census resolves the type
there (its header line ends there, and what follows is another header or the
body, which the census does not read); at a place no SERVED_ALLOW entry names,
so is a type that is not exactly one listed type, since a browser may run a page
under any other (a list of types by its last valid one, a type it sniffs where
no nosniff header stands, a multipart's HTML part): one holding a character past
ASCII or a comma, or whose part before any `;`, stripped of spaces and tabs
alone and lower-cased, is in neither SCRIPT_TYPES nor NO_SCRIPT_TYPES and has no
`+xml` suffix (NO_SCRIPT_TYPES: the types that run no script among those the
census types at such places in the live tree, application/json,
application/manifest+json, application/octet-stream, image/png and text/plain,
all but image/png only with a nosniff header); and so is one of those but
image/png (SNIFF_SCRIPT_TYPES) where no X-Content-Type-Options: nosniff header
is written beside its Content-Type (an expression statement calling send_header
on the write's own receiver with exactly two positional string constants and no
keyword, X-Content-Type-Options in any case and nosniff in any case once
stripped of spaces and tabs, in the write's block, before any statement there
that names end_headers or flush_headers (as an attribute, a name or a string
constant) or, after the write, calls a method of that receiver other than
send_header, send_response or send_response_only, or hands the receiver to a
call, and with no other X-Content-Type-Options header, nor a send_header whose
name is no string constant, before it there or in a statement that runs before
its block; not read: a compound statement before that block in an enclosing
block, a header written through a call the census does not follow, a helper
method of the handler among them, an earlier iteration of a loop around the
write that writes the header from a branch exclusive with the write's, a
callable bound outside the write's block under another name, a function that
reaches the handler through a global, a closure or a frame, and a name computed
before the write), at a `_send` call and at a write outside it alike, since
without
that header a browser runs such a response as a classic script when a page loads
it by <script src>, and the census reads no body of a type it types as running
none; the part before any `;`, stripped and lower-cased, is compared
with the types a browser runs script from
(SCRIPT_TYPES: text/html; the XML types text/xml,
application/xml, text/xsl and any type with a `+xml` suffix, image/svg+xml and
application/xhtml+xml among them; and text/javascript under each name a browser
takes for JavaScript, application/javascript among them). A script-running
route's page body is the call's second positional argument, read only when the
call passes it positionally, with no starred argument before it and no `**`, and
the definition's one output is its one `self.wfile.write(<its second positional
parameter>)`, with a signature of positional parameters, none positional-only,
with None defaults and no annotation, no node in its body of a kind the kernel's
Handler._send holds none of, and every statement of its own body one of that
definition's statement shapes, which the census lists from it (_SEND_SHAPES): a
statement's place in the order, its kind, each operator, each attribute's name,
the codec's name by its value, and each other operand by its class: self (the
method's first parameter); the page (its second positional parameter); another
parameter; a name a loop's target binds, read in that loop; a flag, a text name
and the header parameter, each a name a preamble role below binds, a flag also
where it is an if's whole test; any other name a statement stores that is no
parameter, a local (a loop's target among them); a constant by its type (a
string, a bool, an int, None); a builtin by its name (str, len, isinstance and
getattr in the shapes below), where neither the definition nor the module binds
the name, nothing rebinds it (no function binds it under a `global` declaration,
no module-level statement writes it, and the file does none of the writes listed
below that rebind every builtin) and the module holds no star import; a module
constant (a name one top-level plain assignment binds and nothing else at module
level, that nothing rebinds and no local or parameter of the definition names,
in a module with no star import that writes no name of its module namespace
through a computed name and may not rewrite it at run time) whose bound text
holds no CR or LF as the census reads it (below); an attribute on self other
than a header method or wfile, one class whatever its name; and page text, which
the served pass reads; any other name (a parameter a statement stores outside
those roles among them) stands in no listed shape. The shapes, each matched by
at most as many statements as the kernel's definition holds in it (a constant
header by four, every other shape by one), `<str>` a string constant and every
if and loop with no else: before the end_headers, the stamp `<page> = <page
text>`; a flag `<flag> = <a bool constant>`; the injection's if, `if
getattr(self, <str>, <a bool constant>) and isinstance(<page>, str) and
<parameter>.startswith(<str>) and <str> in <page>:` whose body is `<text name> =
<page text>`, then `if getattr(self, <str>, None):` holding `<text name> = <page
text>` and `<flag> = <a bool constant>`, then `<page> = <page>.replace(<str>,
<page text>, <an int constant>)`; the flag's if, `if <flag>: <header parameter>
= <str>`; the codec, `<page> = <page>.encode("utf-8") if isinstance(<page>, str)
else <page>`; the response line, `self.send_response(<parameter>)`; a header
from a parameter, `self.send_header(<str>, <parameter>)`; the length header,
`self.send_header(<str>, str(len(<page>)))`; a constant header,
`self.send_header(<str>, <str>)`; a constant header under a getattr test, `if
getattr(self, <str>, <a bool constant>): self.send_header(<str>, <str>)`; the
headers loop, `for <target>, <target> in (<parameter> or {}).items():
self.send_header(<target>, <target>)`, each `<target>` a name the loop's target
binds; a header under its parameter's test, `if <parameter>:
self.send_header(<str>, <parameter>)`; a formatted header under a getattr test,
`if getattr(self, <str>, None): self.send_header(<str>, <str> % (<module
constant>, <attribute on self>))`; and an attribute header under a getattr test,
`if getattr(self, <str>, None):` holding `self.send_header(<str>, <attribute on
self>)` then `self.send_header(<str>, <str>)`; directly before the write, the
end_headers, `self.end_headers()`; and last, the write,
`self.wfile.write(<page>)`. The page text is what the statements that build the
page put there before the codec, each read for the text it puts there: a stamp's
`F(<the definition's own parameters, positional, none starred and no keyword>)`,
F a bare name the served pass follows only where it proves a module function a
plain def and reads its returns; an injection's value; and the value of a text
name, a name no parameter, the page or self names, read where an injection's
value reads it. A flag is a name no parameter, the page or self names, assigned
a bool constant and read only as an if's test, any other assignment of it
refused; the header parameter, the parameter the flag's if assigns, is a
non-body header write, neither the page nor self, its string constant holding no
CR or LF. Any other script-running call fails the run by name, its reason naming
the road (a second write, a write through an alias, a print to a stream; a node
of a kind the shapes hold none of, by its kind and line; any other statement by
its kind and line and the shape it lacks, named among those the census lists for
its kind at its place, or by the order it stands outside; a statement in a
listed shape past its count, by that shape and its count; and in a statement of
a listed shape, a builtin or a module constant whose proof fails, by that
proof), among them a keyword body, a starred or `**` call, a definition whose
one write is of another parameter, a local or an expression, or that writes
nothing, a method's definition that binds self again, in any form (a lambda's or
a nested def's parameter among them), or declares it global, any other read of
an attribute named `write`, `writelines`, `send`, `sendall`, `sendfile` or
`sendmsg`, called or not, a string constant equal to one of those names, a
reference to the write's receiver other than as its receiver, and in the
definition a statement after the end_headers (which writes the header buffer to
the stream, so a header call after it would reach the body), a second
end_headers or none, any other rebinding of the page parameter, another codec
name or a second argument to `.encode` (either can name a codec or an error
handler the file registers at run time), a store or delete of an attribute or a
subscript, a read of a name the module binds other than a module constant in a
formatted header's tuple or in page text, a module constant there whose bound
text holds a CR or LF or reads a name the census does not follow by binding (by
name), a string constant holding a CR or LF in a header call (by name), a call
in no listed shape, and a nested def, class or lambda. The reader governs the
definition's own text, and code the definition runs from outside that text is
not read: a header value is not scanned (a module constant the definition uses
as one is read only for a CR or LF: each string or bytes constant in its value
and in the value of each module constant that value names, followed by binding
(a method call's receiver, as `T` in `T.lower()`, among the names followed), any
other name there refusing it, save a bare name a call calls (`f` in `f(...)`);
and so is each argument a `_send` call hands its definition but the page body
and the content type (read above), positional, starred or keyword, a `**` among
them: each string or bytes constant in it, a dict literal's keys and values
among them, and each name in it that no function scope around the call binds (a
name a function there declares `global` is the module's, not a binding of that
scope): a module constant (a name one top-level plain assignment binds, that
nothing rebinds and no code writes after binding it), read through the module
constants its value names, one holding
a CR or LF refusing the call by name before it is typed; a builtin's name (a
name the builtins module holds, the names the import system binds in every
module and the six site.py adds, copyright, credits, license, exit, quit and
help, not among them), a top-level import's name that nothing rebinds where it
is an attribute's base (the attribute limit below) and a bare name a call calls,
not read; and any other name, which the census cannot resolve to a
value it read, refusing the call by name as a name the census does not follow by
binding, in the argument or in a module constant's value there: a name the
module binds more than once or by an annotated assignment, one a function
rebinds under a `global` declaration or a module-level statement writes, one
some code writes after binding it, as a content type's module name is read (a
container a subscript store or an in-place method changes among them), a
top-level import's name anywhere but as an attribute's base, and one no
module-level statement binds, among them the names the import system and the
compiler bind (`__doc__` for a docstring, `__annotations__` for an annotation)
and site.py's six;
a CR or LF the value computes at run time, a call's return or a number formatted
as a character, is not read, nor is a header value held anywhere else, a local
or a parameter of a function around the call, an attribute, a call's return or
an item, a container a call binds that code changes through an alias, or a
container handed to a function that writes its parameter, its witnesses a CR LF
from chr and one from a `%c` of an int, a header value held in a local dict and
a CR LF a call of chr computes at the call, and a dict a call of dict binds that
a helper changes through an alias and a dict handed to a function that writes
it), and a response that a Content-Type in its headers argument, passed
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
namespace mapping other than the file's own module's or the builtins' (one of
those used other than in a key position the census reads is a run-time form,
below), a module's own `__setattr__` or `__delattr__` method, a
listed name, attrgetter or methodcaller imported from a module other than its
own, a name built at run time, gc or ctypes among them, and through a module
reached by a tuple or list unpacking, an inline walrus,
`sys.modules.__getitem__`, a for-loop target, a parameter default or a starred
argument) is outside the list and not seen, and a module name or a builtin so
rewritten is read as the file's text binds it; nor does it see a scalar local or
parameter a function rebinds at run time through its own frame (the frame's
locals, which Python 3.13 and later write through to the function, reached by
`sys._getframe()`, `inspect.currentframe()` or `inspect.getargvalues()` among
other calls): a page's text, and a content type that is a string constant or a
name bound once to one, so rebound the census reads as the function's text binds
it, a stated limit on Python 3.13 and later (its witnesses: a handler that binds
its content type to `application/json` and one that binds its page to
`<p>ok</p>`, each rebinding that local through its frame, so that those versions
serve a fetch as a page). A container a function binds and reads whole, changed through that same frame's
local mapping, reached or run as code in the function's own body (one of the
seven bare names `locals`, `vars`, `exec`, `eval`, `_getframe`, `currentframe`,
`getargvalues`, one of the four attributes `_getframe`, `currentframe`,
`getargvalues` or `f_locals` spelled as an attribute on any receiver, or a name
that a statement of the
module's or the function's own body, outside every def, class or lambda
statement it nests (header and body alike), binds to one of those primitives,
its bound value the primitive's own bare name or attribute, by a plain or
annotated assignment, a walrus, an unpacking of a list or tuple literal into a
target list of as many elements (each plain name there bound to the value at its
place, beside a starred or nested target too), or a `from ... import` of one of
the seven names, and
any name such a statement binds to a name so bound, resolved among those
statements), is refused by name on every version, since the change reaches the
real object; the check reads the spelling anywhere in the function, called or
not, so a name merely spelled like a primitive is refused too, its reason naming
the spelling found, not a frame reached; a change
to those locals at run time through a frame object, exec or eval reached in any
other spelling (among them: the name `locals` or `vars` as an attribute on a
receiver; exec or eval reached as an attribute; `f_locals` as a bare name; one
of the four attributes named by a string, as `getattr(frame, "f_locals")`; and
any binding of a name to a primitive that the resolution above does not read,
among them a plain name among the targets of an unpacking whose targets are not
as many as its values, a name a nested unpacking target binds, an alias whose
bound value is any other expression (an if-expression, a call), a module-level
for loop's target, a match statement's capture, a with statement's target (bound
to what `__enter__` returns), and a binding in the header or the body of a def,
class or lambda statement) is the stated precondition,
outside what
the census reads, and passes silently (its
witnesses, one for each road named: `locals` reached as an attribute on a
receiver; `builtins.exec`; `builtins.eval`; `f_locals` called as a bare name;
`getattr` handed a frame from `inspect.stack()` and the string `f_locals`; a
plain name beside a starred target that takes two values, and a name in a nested
target; a module alias bound to an if-expression and one bound to a call's
return; a walrus in a module-level def's default, a `from ... import` in a def
nested in the function, an assignment inside a module-level def's body, an
assignment in a module-level class's body, read as the class's attribute, a
walrus in a module-level lambda's default, a module-level for loop's target over
a tuple holding `locals`, a module-level match statement's capture of `locals`,
and a module-level with statement's target bound to `locals` through
`contextlib.nullcontext`), while a name a nested scope binds to
a primitive by an
assignment
carries the spelling in the function's subtree and refuses; code the function
runs that the census does not read (a helper it calls as a statement, a method
on self, a context manager it enters), reaching such a container to change it by
a road other than a hand-off, among them the caller's frame and the garbage
collector's heap (gc.get_objects or gc.get_referrers, with no frame, no hand-off
and no occurrence of the container's name), is a stated limit instead, the
census reading no such code's body for its reach as the call limit reads none
for what a callee does with a container it is handed (its witnesses, one for
each road named: a module helper the handler calls as a statement that appends a
fetch to the handler's container through its caller's frame, and one that finds
that container among gc.get_objects() by its content and appends a fetch to it);
a content type the census reads other than as a
string constant or a name bound once to one is refused by name too, on every
version, so no frame can rewrite an intermediate the census had read. Beside
that precondition stands a second one, for the functions the census follows: the
census reads a function as its text defines it, so a change at run time to a
function's code, its defaults, its keyword defaults, its closure cells or its
globals (`__code__`, `__defaults__`, `__kwdefaults__`, `__closure__` cell
contents, `__globals__`), by any reach, is outside what it reads and passes
silently, one witness for each road the reviews of this census found: a function
the page function defines, reached by `locals().get` with its literal name and
its `__code__` rewritten; a module function reached as an attribute of the
module object by its literal name; a module function found on the garbage
collector's heap by its name; and a module function found among
`inspect.getmembers` over the module object (a lookup by name on a namespace
mapping whose key is not constant text, which may spell any module function's
name at run time, is refused instead, where one check does it, as above). Beside
that precondition stands the item limit, for the local container proof below:
what code does with an item of a container the proof reads, or with the object
that a name bound other than to a literal or a call of parse_qs holds, after the
census has read it, in a spelling the proof does not refuse, is outside what the
census reads and passes silently, one witness for each road the reviews of this
census found, each named here: a name an unpacking binds from a new object that
holds the item, a tuple or list display, a comprehension, or a slice or a copy
of the container or of an item, which takes that object's level, so a change
through it is read as a change of a new object holding the item (its witnesses:
a list read out of a local dict of lists, bound so from a display and appended
to, bound so and extended by an augmented assignment, and bound so from a list
comprehension holding it and appended to; a list of a local list of lists, bound
so from a slice of it and from a copy of it, each appended to; and a queue bound
through a boolean operation, bound so, its put read off that name unbound and
called); a name bound to an item of a name bound other than to a literal or a
call of parse_qs, returned by a lambda or a def nested in the function, which
changes that return (its witnesses: a list of a dict of lists bound through a
boolean operation, bound to a name that a nested lambda returns and to one that
a nested def returns, each return appended to); a subscript of a new object
holding the item as an
augmented assignment's target, read as a store into that object (its witness:
that list held in a new list and extended through a subscript of it); a match
statement's capture of the item, or of the name itself, for a name bound other
than to a literal, a call of parse_qs or calls alone (its witnesses: a dict of
lists bound through a boolean operation, a list of it captured by a mapping
pattern and appended to, and the dict captured whole and stored into); an item
of such a name stored into another object and changed there (its witness: a list
of that dict stored as another object's attribute and appended to there), and an
item of a name bound only to calls held in a new object that is stored into
another object or matched by a match statement (its witnesses: a list read out
of a dict bound to a call of dict, held in a new list stored into another object
through which a fetch is stored into it, and held in a new list that a match
statement's sequence pattern captures it from, appended to through the capture),
a new object that is called being no road: a display, a comprehension, a slice
or a copy is no callable, so Python raises before any code runs, and a binary
operation's result is callable only through the item's own type, whose text the
census does not read as a page's (a class's call refused, a value slot's text
unread); on a name bound other than only by plain assignments
of calls (an expression, a loop, with or unpacking target, or a second binding),
a method outside the in-place changers with its return used, the name stored
into another object, or an item of it handed to another object's method by an
operator (its witnesses: a queue bound through a boolean operation that a fetch
is put into, the put's return used; a dict of lists so bound, stored into
another object through which a fetch is stored into it; and one whose item is
compared with an object whose `__eq__` appends a fetch to it); a name bound to
anything but a literal or a call of parse_qs, handed itself, or in a new object
holding it, to another object's method by an operator (its witnesses: an
import's object compared with an object whose `__eq__` stores a fetch on it,
read through str; and a dict bound to a call of dict, held in a new list
compared with an object whose `__eq__` stores a fetch into it through that
list); a change a function makes to its own parameter by a use outside those the
proof lists, what a function does with a value it is handed, the call limit (its
witness: a queue a module function takes as its parameter and puts a fetch into,
the put's return used); and on the module side, a list of a module container
bound to a name by an unpacking nested in another, or by a loop's or a
comprehension's unpacking (a generator expression's among them), in a function
or at module level, which the module side reads at a depth that does not reach
the container, or held in a new list in either place and extended through a
subscript of it by an augmented assignment (its witnesses: a list of a module
dict of lists so bound in a function by a nested unpacking and appended to, so
bound there by a loop's unpacking and appended to, and so held there and
extended; the same three at module level; and the list so bound by a list
comprehension's unpacking and appended to in its element, in a function and at
module level, and by a generator expression's unpacking at module level). A
default of a function or a lambda that holds the name, or a name the proof
follows from it (a name that a plain or annotated assignment, a walrus, or a
loop's, a comprehension's or a with statement's target, an unpacking's names
among them, binds to it, to an item of it or to a new object holding one,
outside every def or class statement and lambda body the function nests), marks
the name at any level of new objects (unless the str exemption the local
container's definition below states holds), so that road refuses; a default
holds it where the default's value is that name, or reaches it only through
subscript loads on it, the returns of the read methods get, keys, values, items
and copy (and of index or count with a constant argument), boolean operations,
if-expressions' branches, walruses' values, starred values, awaits and new
objects (a list, tuple, set or dict display, a comprehension holding it as its
element, or a binary operation whose other operand is a constant). A def's
default is part of the def statement, so the name read there is an occurrence in
a def nested in the function, which refuses a container whatever the use, and
the proof follows no name bound there (a walrus's or a comprehension's target),
so a change through such a name is the item limit (its witness: a dict of lists
bound through a boolean operation, a list of it bound by a walrus inside a call
in a nested def's default and appended to through the walrus's name after the
def); a lambda's default runs where the lambda stands, in the function's own
scope. Otherwise any other use of the name or of an item of it in a default is
read as that use is in the function's own body: handed to a call as an argument,
it is under the call limit, what the call does with it and what it returns not
read (its witnesses: a dict of lists bound through a boolean operation, a list
of it bound to a name and handed to a module function that returns it, its
return taken as the default of a nested def that appends a fetch to it; the list
handed so directly, in a nested def's default and in a lambda's; and the same in
a lambda's default where the dict is a local literal); and handed to another
object's method by an operator, it is read as that operand is elsewhere, refused
where the proof refuses such an operand and otherwise one of the item limit's
operand roads above (its witness: that list, through a name bound to it, added
to an object whose `__radd__` appends a fetch to it, in a nested def's default).
A default that takes the item through a name the proof does not follow from it
passes silently, part of the item limit (its witnesses: a dict of lists bound
through a boolean operation, a list of it captured by a match statement's
mapping pattern and taken as the default of a nested def, and of a lambda, that
appends a fetch to it; a list of that dict stored as another object's attribute
and taken from that attribute as a nested def's default that appends a fetch to
it; and a list of that dict bound by a comprehension's target in a nested def's
default, the comprehension's list that default, through which the nested def
appends a fetch to it). A
`_send`
definition in a class that a function defines, a page function that a function
encloses, a `_send` call inside a lambda's body, and a Content-Type write inside
one that is no `_send` definition's own write fail the run by name: the census
does not read the enclosing function's or lambda's scope, so it would take a
name that scope binds (a builtin or a module name it shadows) for the module's.
A `_send` definition's own Content-Type writes (each write whose innermost def
is the definition, or a def in it itself named `_send`) are typed at each call.
A call fails the run by name where one of them names a parameter whose argument
the census reads as the type and the definition binds that name other than as
that parameter anywhere in its body (in its own scope or in a lambda, a
comprehension, a nested def or a class body in it) and in any form (an
assignment, augmented or annotated, or an annotation; a loop, with, walrus or
match target; an except name; a del; an import; a def or class statement; a
global or nonlocal declaration; a parameter, a comprehension's target, a type
statement or a type parameter): the census reads that write's type from the
call's argument, which such a binding may replace. The
page
function of each script-running route is followed to the text it returns or
inlines, and a
parameter a followed call omits is read from its default value as that argument
would be, in the scope the def statement runs in (a default the pass cannot read
is refused by name, one that holds a lambda among them). A name the
page function's scope binds, or for a function defined in it an enclosing
function's scope, is decided by that scope and never by the module's binding: a
local container the census does not prove it reads whole (below) is refused
wherever it is read, and any other local (a parameter the body also assigns, a
walrus in a nested def's, class's or
lambda's header, and a comprehension's target inside its comprehension among
them, read from its generator's source in the scope Python evaluates that source
in: the first generator's in the scope around the comprehension, each later
one's with the earlier generators' targets bound, a target of that generator or
of a later one being refused there as a name a comprehension binds) is read from
its values as a bare name or a receiver (refused where one holds a lambda,
below), each value in the scope that binds the local, where Python evaluates it
(a comprehension, a lambda or a function defined in the page function reads a
local of the scope around it there, so its own binding of a name that value
reads is never taken for it) and refused as a callee; a parameter or an except
name is
a value slot, refused as a callee when
it shares a module function's name; a function defined in the page function is
followed as a callee only as its name's one binding there and where the census
proves it a plain def (below), and is refused by name as a value, a function
object whose text the census does not read; a name the function
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
and may not rewrite it at run time, as listed below) or a local, a method call's
receiver only for a method whose return is drawn from the receiver's text
(strip, lstrip, rstrip, removeprefix, removesuffix, split, rsplit, splitlines,
partition, rpartition, a match's group, and the read methods get, keys, values,
items, index, count and copy), any other method on a receiver whose text the
pass reads refused by name, the receiver of `.encode` or `.format_map` whatever
it is (but the name str, bytes or bytearray before `.format_map`, and either one
in a shape the census does not compute, each refused below), a loop, unpacking
or with target from its
source, and a local container's stored or appended values where every occurrence
of its name is one of the proven forms (below); it passes over a base whose own
text it
does not read (in a module that holds no star import, a top-level import
statement that is its name's one module-level binding and is not rebound, or one
of the seven builtins a page may name, each for what its result is (str, its
argument's text or a value's printed form, a call of it with more than one
positional argument, a starred argument or a keyword other than `object`, any of
which may be an encoding or an errors argument that decodes its first, refused
by name, an honest decode of bytes failing closed with it; int and float, a
number, which carries no host, so a call of either that is the builtin is a leaf
whose argument the pass does not read, save where the call is the base of a
receiver, a container or an attribute, where the argument is read as any call's
is (the leaf rests on the builtin's return,
which the census does not read: an `__int__` or an `__index__` returning an int
subclass, or a `__float__` returning a float subclass, whose `__str__` or
`__format__` is overridden is the escape shape that could put text there, the
stated limit, and the interpreters the census runs on copy such a return to an
exact int or float, so its witness serves digits), and a call of either
bound any other way is refused by name; dict, a mapping
of its arguments' keys and values; max, one of its arguments (a call of it
handed one iterable or a starred argument, which returns an element its argument
holds, whose join with the text beside the call the census does not compute, is
refused by name); getattr, an attribute of its first argument; and chr, the
character a code point names: getattr and chr give text their arguments do not
hold, so each falls under the call limit below, as its witness) that no
module-level binding shadows and that is not rebound, any
other builtin refused by name, and a call of super() refused by name as well,
its methods being a base class's (the names the import system
binds in every module, `__doc__`, `__name__`, `__package__`, `__spec__` and
`__loader__`, are no builtins here: a page that reads one the file does not bind
is refused by name wherever the pass reads it, as a bare name, the base of a
receiver, a container or an attribute, a callee or a call's argument, but never
inside the index of a subscript over a container whose text the pass does not
read: below); a digest, which carries no host either, a leaf as int's and
float's call is: a call, with no argument, of the `.digest()` or `.hexdigest()`
method of a call of one of `hashlib`'s constructors, or of `hmac`'s `new` handed
exactly one digestmod (its third positional argument or its digestmod keyword,
with no starred argument and no keyword but key, msg and digestmod) that is a
string constant naming one of `hashlib`'s named constructors (not the variable-length `shake_128` or `shake_256`) or such a constructor as an attribute of `hashlib`, each module name the standard
library's by binding, is a value the census reads none of what it is computed
from (`hmac`'s `new` hands its digest to the object its digestmod names, so one
handed any other digestmod is refused by name), and a base64 encoding of such a
leaf (one of
base64's encoders on the name base64 so bound, handed the leaf alone), a
`.decode()` of one with no argument, a slice of one, and a strip of one
(`.strip`, `.lstrip` or `.rstrip` with no argument or one string constant) stay
leaves, as do a name the census reads by binding whose every value is a leaf and
a call of a function the census follows as a plain def every return of which is
a leaf (whose arguments are then not read either); a base64 encoding alone is no
leaf and is read as before, as is a `.decode()`, a slice or a strip of anything
but a leaf, and a digest or base64 encoding through `hmac`, `hashlib` or
`base64` bound other than to the standard library's module is refused by name, a
module name a function rebinds under a `global` declaration or binds as its own
local among them; the proof by binding reads the file's import statements and no
more, so a digest or a constructor whose code is replaced at run time (by an
assignment to a method of the module's class, or by an attribute store on the
module object) and a module object stored in sys.modules under the standard
library's name before the import binds it are the escape-only limit, a witness
for each; a parameter, an except name, or a name the function binds
from one of those, where no attribute is read on the path to it: `q.get(k)`
passes, and `q.X` is refused, below), reading as text the arguments a call of
such a base or of a method on one is handed, never the text it computes from
them (a method whose return is not drawn from its receiver's text, called on
such a base where it derives through a call handed arguments the pass reads,
`str(X).lower()`, `int(X).bit_length()` and `base64.b64decode(X).decode()` among
them, or on the bare name of one of the seven builtins, called unbound,
`str.lower(X)`, is refused by name because the base's own text is not read, not
because its return is undrawn (a `.strip`, whose return is a piece of that
unread text, is refused the same way): at the call the page expression makes,
save a `.replace`, `.join`, `.format`, `.format_map`, `.encode`, `.strip`,
`.lstrip` or `.rstrip` there, which the text-method arm reads as its own shape
(below); and at every call on the path below it with no exception by shape, the
text-method arm's among them, under a method whose return is drawn from its
receiver's text, a join or a subscript, `str(X).lower().removeprefix(p)`,
`str(X).lower().split()[0]` and `str(X).strip().removeprefix(p)` among them):
text a call computes from its arguments
is
not
read, a stated limit (`dict(X).get(k)` and `json.loads(json.dumps(X))[0]` read
X; the limit's witnesses are `chr(n)`, whose character is not n's text,
`getattr(o, name)`, whose attribute is not its arguments' text, and a decoder,
`base64.b64decode(X)` or zlib or gzip over an embedded bundle
(`zlib.decompress(base64.b64decode(X))`), whose bytes the page serves, each read
only as its arguments' own text; an encoded asset kept ASCII and decoded where
the page is
built is such a shape, and can be honest; and so is a method called on a
parameter whose name no route class's body binds and the
file nowhere stores, deletes or names to a setter as an attribute (below), a
method of a class that holds no route among them), and over a bare module name
that is such an import or one of the seven builtins a page may name; a top-level
def or class statement that is its name's one module-level binding, read as a
value rather than called (a bare name or a call's argument among them), is
refused by name as a function or class object, whose text (a class's through its
metaclass, a function's through its writable `__qualname__`) the census does not
read. Text such a base holds is not read: a constant that a sibling module
defines and
the page imports, and a class reached through an import's attribute (its
witness: a class that a sibling module defines, read as an attribute of that
module, which the page imports by name) or through a call's return, under the
call limit; code behind a name on self is not followed: a method called on self
by binding, or on a name the census resolves to it (a local bound to it, or a
function the page function defines returning it), is refused by name (below),
and one called on any other parameter, or on a name bound to the return of a
function the census follows that returns its parameter, is refused where a route
class's body binds its name or the file stores it, and is otherwise under the
call limit; an item of self, a parameter's, is text such a base holds. A local
container (a name a function the pass reads binds whole to a list, dict or set
literal or comprehension or to a call of parse_qs, or a name with one of these
uses: a store or delete through it or an item of it; an append or extend;
setattr or delattr, or a method spelled on a class, handed it or an item of it;
a binding of it, or of a new object holding it, to a name the function declares
global or nonlocal, or as a default of a function or a lambda (unless the name
is no parameter and every binding of it is a plain assignment of one name to a
value the proof types as a str: a string constant; a walrus of one; a boolean
operation or an if-expression whose operands or branches all are; or an item
read, by a subscript load without a slice or by a dict's get (its default, where
it has one, of the items' type too), out of a container every item of which is
one, such a container being a list, tuple or dict literal (with no starred
element or `**` entry, a dict's items its values), a slice of a list or a tuple
one, a copy of a list or a dict one, an item so read out of a container every
item of which is such a container of one kind, or a walrus, a boolean operation
or an if-expression over such containers of one kind; an item read out of a
container that holds none, which Python cannot read, has no type and is left out
wherever types are met);
an augmented assignment
to a name bound to it or to an item of it, which runs that value's own in-place
method (`e += [v]` extends a list, `e |= {...}` updates a dict); one of the
in-place changers of a list, dict, set, deque or OrderedDict called on it or
read off it unbound (update, setdefault, append, extend, insert, pop, popitem,
popleft, clear, add, discard, remove, sort, reverse, appendleft, extendleft,
rotate, move_to_end, difference_update, intersection_update and
symmetric_difference_update, or a spelled-out `__init__`, `__setitem__`,
`__delitem__`, `__setattr__`, `__delattr__`, `__ior__`, `__iadd__`, `__isub__`,
`__iand__`, `__ixor__` or `__imul__`), or a method whose return a statement
drops; an attribute read off it other than as a method's callee, whatever the
name is bound to; or a method other than get, keys, values, items, index, count
or copy called on an item of it, or an attribute read off one; and, for a name
that is
no parameter and every binding of which is a plain assignment of one name to a
call (an import's, a builtin's or a followed function's), any use outside a
closed set: a read, a call's argument, a subscript load, a binding to a name the
walk follows, the name itself an operand, and a method the census reads a text
through with its return used (get, keys, values, items, index, count, copy,
split, rsplit, splitlines, partition, rpartition, removeprefix, removesuffix,
group, join, format, format_map, replace, strip, lstrip, rstrip or encode), so
any other method, it or a new object holding it stored into another object,
called, matched or held where the census does not read it, and an item of it so
used or handed to another object's method by an operator; each directly or
through a name bound to it, to an item of it or to a new object holding one, at
the levels of new objects that name's binding holds it at) is read whole only
where every occurrence of its name, resolved by binding, is one of the proven
forms: its one binding (a
plain single-name assignment to a list, dict, set or tuple literal or to a call
whose return the census reads as a value slot, an import's, one of the seven
builtins a page may name, a parameter's or a method's on one of those); the
base of a subscript store by a str or int constant key as the one target of a
plain assignment, whose stored value the census reads; the receiver of an append
or extend of one plain argument the census reads; a `.pop` on a dict of a
constant key, or of a key a for target over a tuple of string constants proves
constant by binding (the name no parameter and bound no other way in the
function), with at most a constant default and no keyword or starred argument,
which can only remove and hands the container's method no object of its own; and
the fourth form, a read that hands the container to no other code: the receiver
of one of the read
methods of the type its one binding gives it, or the base of a subscript load on
a type that has one, wherever it stands, tests included. The read methods are a
closed set per type: a dict's get, keys, values, items and copy and a subscript
load; a list's index, count and copy and a subscript load; a tuple's index and
count and a subscript load; a set's copy; an index or a count only with a
constant argument (with any other, Python hands each item to that argument's
method, and the container refuses). Only a list, dict, set or tuple
literal, or a call of parse_qs (imported from urllib.parse at the top level and
bound once, a dict), gives the container a type; bound to any other call the
census reads as a value slot (`dict(...)` or an import's call among them), it
has no type, and a read method or a subscript load on it refuses. A read
method's or a subscript load's result is an item the census follows by binding
like any other value. The proof covers the container, and an item of it (a read
method's or a subscript load's result) it reads by the same principle where no
new object stands around the item: the item itself, a name bound to it (a
binding whose value is the item with no display, operator or comprehension
around it, or a loop's or a comprehension's target over such a display), and a
subscript load or a read method taken from a new object holding it, through the
closed
read set of the item's own type, known as the container's is: from the literal,
from parse_qs (whose items are lists of str) and from each value stored or
appended into the container, a string constant being a str, and a copy of a
dict, a list or a set, or a slice of a list or a tuple, being of its receiver's
type and a new object holding its receiver's items. Any other method called on
the item, and a read
method or a subscript load outside its type's set (a spelled-out dunder among
them), whether the return is used or dropped, an attribute read off it other
than as a method's callee, a store into it, an augmented assignment to a name
bound to it (which runs the item's own in-place method, and refuses for a str
item too, whose augmented assignment only rebinds the name), setattr or delattr
handed it, and a method spelled on a class handed it as its first argument (a
builtin class, as in `list.append`, or a class of collections imported as the
module or by name, as in `deque.append`), each where no new object stands around
the item, refuses the container; a str has no read set, nor has an item whose
type the census does not
know (a call's return, a name it does not follow), so any method or subscript
load on one refuses; and so does the item's hand-off to another object's method
by an operator (an operand of a binary operation or a comparison whose other
operand is no constant, a subscript's index, a slice's bound, the value of an
augmented assignment, or what an index or a count with an argument that is no
constant compares) or
any use of it the census does not read (called, or stored into another object,
an attribute or a name the function declares global or nonlocal); compared or
combined with a constant, an item is read, since only its own type's method and
the constant's run; and an item handed as an argument to any other call, a
method spelled on any other value among them (a class the file defines or
another import names, a module's function), is under the call limit, as the
container is (below). Any other occurrence refuses the
container by the rule, its reason naming the role it fails: the whole
container bound to another name, to a name the function declares global or
nonlocal, or into an attribute or another object; a read that hands it to
another object's method (an operand of a binary operator, a comparison or `in`,
a subscript's index, a slice's bound, the value of an augmented assignment) or
any other read (a test, an identity test, a boolean operation's operand, held in
a new object); a
second binding (an augmented assignment, a walrus, or a for, with, except,
match or unpacking target); a delete; a method other than append, extend or a
read method of its type, a read method outside its type's set or a spelled-out
dunder among them, or an attribute of it read other than as a method's callee;
setattr or delattr, or a method spelled on a class (a builtin class, or a class
of collections imported as the module or by name), handed it as its first
argument; a store by a key that is no constant; an append or extend of other
than one plain argument; an augmented assignment to a name bound to it or to an
item of it; or any occurrence, whatever the use, in a def or class statement
nested in the function (its decorators; its header, a def's defaults and
annotations and a class's bases and keywords among them; and its body, where an
occurrence in a def's body is a closure capture whose code the census does not
read, and one in a class's body runs where the class statement stands, as an
expression of the class's own code or a class attribute it makes) or in the body
of a lambda nested in the function (a lambda's
defaults, which run where it stands, excepted); a comprehension is read where it
stands, as the function's own body is: a read of the fourth form and an append
of a read value there pass, the container as a comprehension's source, in its
condition or as its element refuses as any other read does, and a change the
census cannot fold, a comprehension target store among them, refuses. The first
parameter of a method or a route handler is not read so: every attribute read
and method call on it is refused already. Outside a nested def or class
statement and a lambda's body, the container, or an item of it, handed as an
argument to any other call is under the call limit, what the callee
does with it not read (its witnesses: a local dict a module function it is
handed stores a fetch into; a list read out of a local dict of lists by a
subscript load, by `.get`, or through a name bound to it, which a module
function it is handed appends a fetch to; and such a list handed to append
spelled on a class of the file that derives from list). What the proof does not
read of a name so marked, or of an item of a container it reads, is the item
limit, stated above beside the frame precondition.
An attribute read in a page position, as a value or anywhere on the
path of a receiver or a container (but never inside the index of a subscript
over a container whose text the pass does not read: below), is refused by name
unless the root its base reaches by
binding is a module constant, an import, one of the seven builtins a page may
name, a value slot or a literal the pass reads (an attribute read off a local,
or off a module name bound to a call, being refused before that, as a container
or a run-time memo, so the walk below reaches a local's values only through a
comprehension's target, or from a receiver with no attribute read on its path;
the census follows the base down that
path, through a call's callee, a BoolOp's operands, an if-expression's
branches and a walrus's value as well, and through a local's values, a loop,
comprehension or with target's source, a list, tuple, set or dict literal's
elements, keys and values, and a module constant's value, but never through a
call's argument or a parameter's default): an attribute read on self (`self.X`
as a value, a receiver or a
container, `self.X.get(k)`, `self.X[0]` and `self.__doc__` among them), on a
comprehension's target bound to it or on a method's first parameter however
spelled, where the
method's def carries no decorator and, for a route handler, the file binds
neither staticmethod nor classmethod, is refused by name, whatever sets it; one
read on any other parameter (a module helper's parameter, any other method's
first parameter, and a parameter that a class is passed to or has as its default
among them) is refused by name as that parameter, a container the proof refuses,
and one read on a route handler's first parameter the census does not classify,
on a parameter's call or on an except name with a reason of its own; a
base whose root is one the pass
refuses (a function's or a method's return, a call it does not follow, a builtin
other than the seven, a function object, `__file__` in a file that binds it, a
run-time memo) is refused with the reason the pass gives that root; and an
attribute read on a
class, a method called on one among them, is refused by name too, as a value, a
receiver or a container, through the class's own name (a name a class statement
binds, in the innermost function
scope around the read that binds the name or, where none does, at the top level
of the file, whatever else binds it at module level) or through a name the
census resolves to such a class (a local or a module constant bound to one, `h =
Handler` and then `h.render()`, the attribute read `h.X` refusing that local as
a container first), or through a method call on, or a subscript of, a name
whose value holds
such a class (a local or a module constant bound to a list, tuple, set or dict
literal with one among its elements, keys or values, `_REG.get(k).X`, or to a
call of the builtin dict with one among its arguments, a keyword's value among
them, `_REG = dict(a=Handler)` and then `_REG["a"].X`, or a local or a module
constant bound to such a method call or subscript), or of such a literal or call
itself (`dict(a=Handler).get(k).X`), or through any other base whose root by
binding is such a class (a loop, comprehension or with target over classes, an
if-expression or a walrus over classes, and a literal container holding one,
`_REG["a"].X` and `_REG["a"].render()` among them), and so is a text method
called on such a class through any of those roads (`Handler.format(...)`,
`_REG.get(k).format(...)`, `(A or B).replace(...)`, `t.strip()` in a loop over
classes), save one on a subscript refused as a join's operand (below), and a
replacement field in a `.format` or `.format_map`
that reaches an attribute of its argument (below): no class attribute is read as
page text. A call of a name the census resolves to such a class, the class's own
name among them, is refused by name as a call, so no attribute of the instance
it makes is read either. A name is
rebound
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
globals, vars, setattr, delattr or `__dict__` reached in the fourth; or, in a
position of the fourth, a key the POSITIVE ALLOWLIST does not prove by its
binding; in a call of the getattr family or of a namespace-key method, which
take a key of the fourth by position, a starred argument among its first two or
a `**` mapping, which may put any value in the key's place; getattr, setattr,
delattr or hasattr read other than as a call's callee (an alias or a partial's
argument among them), by its own name, by a name an import binds to it or as an
attribute of a builtins receiver,
since a lookup through it hands the census no key to read; or a namespace
mapping the file's own module or the builtins may be (globals() or vars() with
no argument, `__builtins__`, or the `__dict__` or vars() of such a module) used
other than in a key position whose key the allowlist reads (a subscript's
container, in any context, or the receiver of `.get`, `.pop`, `.setdefault`,
`.__getitem__`, `.__setitem__` or `.__delitem__`). The allowlist accepts only a
constant string spelling no listed name; a parameter whose default, if any,
holds constants alone (a constant, constants the census folds to text, or a
tuple or list of those), none spelling a listed name; a call's return whose
callee reaches neither text nor the str, bytes
or bytearray type nor a method of one; a name that is a loop or comprehension
target inside a function over a literal of constants, a once-bound module tuple
constant no code can mutate or the one attribute source the file
kernel/host_transport.py holds, sh.SPEC_FIELDS, keyed by binding on the file,
the attribute name and the base bound once at module level and declared global
or nonlocal nowhere, whose base reaches no text and for which the file writes no
attribute of that name (it binds and declares no such name, uses an attribute so
named only as such a source or an item read, never storing, deleting, augmenting
or calling a method on one, spells the name in no string constant, constants the
census folds to it, or keyword,
uses setattr, delattr, `__setattr__` or `__delattr__`, or an attribute so named,
only as the callee of a call each of whose arguments that may name an attribute
(the second of a setattr or delattr called by its bare name, else the first two)
folds to string constants other than that name and none of whose first two
arguments folds as constants to that name, imports none of the four under
another name, spells none of them in a string constant or constants the census
folds, and names no globals, vars, locals or `__dict__`
and holds no star import; an argument folds only as a string constant, as
constants the census folds to one or as a name bound in its scope only as the
target of a loop in a function's own body or of a comprehension over a tuple,
list or set literal each of whose elements is a string constant or constants
the census folds to one), so a new accepted source
enters only by an allowlist edit;
a name that is such a target, or an unpacking target, over
a parameter or such a call's
return, directly or through names an assignment, such a target or an unpacking
binds to one; a boolean operation or an if-expression each of whose values the
allowlist accepts where it stands; and a name an assignment binds to any of
these but a constant string. Every other key refuses by name, the reason naming
what the walk
met: a join, format, format_map or replace call, a `%`, a `+` or an f-string a
string constant does not fold; a parameter's default that holds anything but
those constants (a name, a call or a starred element among them); a method of
the name str, bytes or bytearray,
however reached; any method
called on, or attribute read on, constant text or anything not proven to reach no
text; a direct attribute key or a name bound to one, an attribute source other
than that one binding, and that binding where the file may write its attribute
as above, a setter argument of any other shape counting as such a write (a mixed
literal, a dict, an unpacking target, a parameter, a call's return, a join the
census does not fold, a starred argument or a keyword among them), as does a
setter's name or an attribute so named used other than as a call's callee (an
alias or an argument among them), an import of one under another name, or a
string constant, or constants the census folds, that spells one (for that one
binding, one line under the class limit: a class replaced through type() with a
key the census does not fold (one built with chr, say), a namespace constructor
or a store elsewhere on the base chain,
since the census reads no base's text; a setter reached reflectively other than
by a string constant, or constants the census folds, that spells its name,
through `__getattribute__`, inspect.getattr_static, an index into a mapping of
an object's members or a getattr handed to another call among them; and a writer
other than setattr, delattr, `__setattr__` and `__delattr__` handed the name
other than as a string constant or constants the census folds to it (a name
built with chr, say), functools.update_wrapper and its kin and an
item store into a `__dict__` reached reflectively among them);
a name bound to a constant string; a with
target, or a name bound to one; a walrus, or a name a walrus binds anywhere, a
comprehension's included; a subscript; an augmented assignment; a loop target
bound at module level; a name a function or a class body
declares global or a scope declares nonlocal; a name a class body binds; a name
bound only in another form or by no statement; a list, set or dict module
constant; and any other node kind. A name read at module level or as a builtin
refuses where the file may rewrite its namespace.
The
four
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
string constants that reads as one, of the kinds whose text the census reads
whole (listed below), where a run-time lookup by name takes it (the second argument of getattr, setattr, delattr or hasattr, called by its
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
ways). Every builtin is rebound in such a file and in a file that names
`__builtins__` as a name, imports the builtins module (`import builtins`, a
submodule or an alias among them; `from builtins import ...` at any level; or
`from X import builtins` or `from X import __builtins__`, aliased or not, for
any module X at any level) or writes a module that may be the builtins module:
an attribute store or delete on it, a setattr or delattr on it, or its
`__dict__` or vars() used any way but for a `.get` read, where a module that may
be the builtins module is `__builtins__`; `sys.modules[k]`, `sys.modules.get(k)`
or a call of `__import__` or import_module as above, whose k is the string
"builtins" or no string constant; a name that an assignment, an annotated
assignment or a walrus binds to one of these; or an if-expression or a boolean
operation with one of these among its operands. A function's `X = []` of a local
of the same name, or its `X.append(...)`, does not rebind it. A module list,
dict or set constant (a literal or a comprehension a top-level assignment binds)
is a container the module writes at run time as well, a run-time memo no type is
read through, where the file changes it other than by the writes listed above
for a route's type (a store or delete through an item of it or on it as an
attribute, a method called on it or on an item of it other than one the census
reads a text through (named above), a method called on it whose return is
dropped, one of the in-place changers named above read off it or an item of it
unbound, an attribute read off it other than as a method's callee, a setattr or
delattr on it, an augmented assignment to it, which runs its own in-place
method, or it or an item of it handed to another object's method by an
operator), changes it through a name bound to it, to an item of it or to a new
object holding one (each name read by its spelling in every scope, so a local of
that spelling counts too; a name an unpacking nested in another, or a loop's or
a comprehension's unpacking, binds, and a subscript of a new object as an
augmented assignment's target, being the item limit, above), or lets it or such
a name leave the
census's sight (stored into
another object, returned, yielded, handed as a default or matched; an item of a
literal that holds only constants and tuples of them, which cannot change,
excepted), though none of these rebinds the name; a module name bound to a call
whose object the file changes in one of those ways, directly or through a name
bound to it, to an item of it or to a new object holding one, or lets out of the
census's sight, is refused so wherever the pass takes text through it but as a
call's argument, which is under the
call
limit (its witness: an import's object an attribute store changes, read as
getattr's argument), as is what a function a module container is handed does
with it (its witness: a module dict a function it is handed stores a fetch
into). The proofs by binding above, and the route typing's, read only the page's
own file, and a file that imports the page's module can rebind or change its
names at run time. So a walked Python file holding a route candidate (a `_send`
call, a Content-Type write, a send_response call or a getattr naming `_send`)
fails the run by name, one SERVED line at its first candidate, when an import
statement of another walked Python file may bind its module: an absolute import
where the file's path ends with the dotted module, a parent package it imports,
or the module and a name it imports; a relative import where one of those, taken
from the importing file's directory, is the file's path; or a star import from
the file's package. A module reached any other way (through sys.modules, a
loader by path,
a function's `__globals__`, or an object the module hands to other code) is not
seen, a stated limit (its witness: a sibling module whose function stores a
fetch into a page module's constant through sys.modules). It follows a call
whose callee is a module function (a top-level def
statement that is its name's one module-level binding, not rebound, in a module
with no star import, and bound by no function scope of the page) or a function
defined in the page function (its name's one binding there), each only where the
census proves it a plain def: a def statement (not an async def, whose call
returns a coroutine) carrying no decorator (staticmethod and classmethod among
them: Python calls a decorator's return in the def's place), with no yield or
yield from in its own body (its call would return a generator), whose name the
file reads nowhere but as a call's callee (an alias, an argument, and a store or
delete of the function or of one of its attributes, `f.__code__ = ...` among
them, may run code the census does not read) and, for a module function, spells
in no string constant and in no constants the census folds to text, a `+`, an
f-string, a `%`, or a `.join`, `.format`, `.format_map` or `.replace` of string
constants, anywhere in the file (which a lookup by name may reach), in a file
where every key a lookup by name takes on a namespace mapping (a subscript of
globals(), vars() or locals(), `__builtins__` or an attribute named `__dict__`,
or the first argument of `.get`, `.pop`, `.setdefault`, `.__getitem__`,
`.__setitem__` or `.__delitem__` on one) is a string constant or constants the
census folds to text, since any other key, a parameter or a call's return among
them, may spell its name at run time. A module function that a lookup by name on
the module object itself reaches with such a key (getattr or attrgetter, the
module reached through sys.modules, import_module, a parameter or any other way)
is not seen, a stated limit, since the census does not read which object a
lookup's receiver is (its witness: a module function that getattr on
`sys.modules[__name__]` reaches by a module helper's return and whose `__code__`
the file rewrites). It follows a call whose callee reads a dispatch table, a
module name one top-level plain assignment binds once to a dict literal whose
keys are string constants and whose values are bare names of module functions
the module binds once, no code changing it after that binding and every other
occurrence of the name a `.get` callee's receiver, a subscript load's base, or a
membership test's right operand (a read, since such a dict's `__contains__` is
the builtin's, which hands the dict to no other code): the callee is a `.get` of
the table with one argument, a subscript load of it, or a name a function binds
once by a plain assignment to one of those whose every occurrence in the
function is that binding, a callee or an identity test against None, and each
value of the table is followed as a page renderer under the same proof. Any
other callee of those two kinds is refused by name, the reason naming the
condition it fails; a
module-level def of int or float is not followed but refused as a call of int or
float bound other than to the builtin (above). It
also follows a text method or a file read, and any other method through its
receiver, as above, and it reads every call's arguments but those of a call of
int or float that is the builtin, a leaf, save where the call is a base (above).
It follows no method
called on the calling method's own first parameter (self by binding, however it
is spelled, the first parameter of a method whose def carries no decorator,
never rebound in the method, and read so in a closure, a lambda or a
comprehension of the method that does not bind the name; the first parameter of
a route handler that carries a decorator, whatever it is bound to, or that
stands in a file binding staticmethod or classmethod in any scope and by any
form, a star import among them, is not classified, and a method called on it, or
it called, is refused by name): every such call is refused by name, since the
server may instantiate a subclass another file defines, whose override of the
method the census does not read, and the reason names what the census found
first in the route class's method resolution order, the route class read from
its class statement: no def statement of a class of the file that defines the
name first in that order (the order reaching a base whose names the census does
not read, an imported one, before any class of the file that binds the name; the
first class that binds it binding it any other way; no class binding it; or a
route class that is not its name's one top-level class statement, whose order
the census does not read); a def that is no plain def (above); a class statement
of the file, in any scope, outside that order, that binds the name and derives
from the route class, directly or through classes of the file, or whose
derivation the census cannot place (a class statement that is not its name's one
top-level class statement, or one with a base on its ancestor chain that is none
of those classes, no top-level import that is its name's one binding or an
attribute of one, and no builtin); the file's replacing the method at run time
(below); and otherwise that subclass. Refused by name as well are a call of a
route class's method (a name the body of a route class, or of a class of the
file it derives from, binds in any form outside its nested scopes, a def
statement, an assignment and an import among them, the route class read from its
class statement and the names read once per file) on self through anything else
(a local, a loop, comprehension or with target, a container, an if-expression, a
BoolOp or a walrus bound to it, or the return of a function the census follows,
read in that function's own scope, as a function the page function defines
returning self), on any other parameter (one a followed function returns among
them, `r = _ident(self)` and then `r.get(k)` with `_ident` returning its
parameter), or on a name spelled
self that is not the calling method's own first parameter; a call of any other
name on self through anything else; and a call of any other name on any other
parameter, or on a name spelled self that is not that first parameter, where the
file stores, deletes or names to a setter an attribute of that name on any
object, which may bind it on a route class or its instance; each before the
file-read and text-call arms and wherever such a call stands on the path of a
receiver or a container. A call to any other callee passes when the callee is
such an import, one of the seven builtins a page may name or a parameter other
than such an unclassified first parameter, and is refused by name for any other
builtin, for str handed more than one positional argument, a starred argument or
a keyword other than `object`, for max handed one iterable or a starred
argument, and for such a first parameter. For that reason
the file may replace a method at run time where it stores or deletes an
attribute of the method's name on any object (the target of an assignment of any
kind, a for, with or comprehension target, or a del), names the method by a
string constant, or a join of them, as the second argument of setattr or delattr
(by that name or as an attribute so named) or of `__setattr__` or `__delattr__`
called unbound (by that name, or as an attribute of `object`, of `type`, of a
class a top-level class statement of the file binds or of a call of type()), or
as the first argument of `__setattr__` or `__delattr__` called bound on any
other receiver (`self.__setattr__("name", f)`, `super().__setattr__(...)`), or
holds a class in the route class's method resolution order that binds
`__getattribute__`; and, with a reason of its own, where it hands setattr,
delattr, `__setattr__` or `__delattr__` an attribute name the census does not
fold to a constant string (a name, a parameter or a call's return, one standing
after a starred argument, or none at all, among them) or reaches one of them
other than by a call (its name, or an attribute so named, anywhere but as a
call's callee, an import of one under another name, or a string constant, or
constants the census folds, that spells one). It reads both operands
of a `/`, a path join. `__file__`, wherever a page reads it (as a bare name, the
base of a receiver, a container or an attribute, or a callee, but never inside
the index of a subscript over a container whose text the pass does not read:
below), is refused by name in a file where a statement binds it, in any
scope and by any form, before
any scope's or module-level binding of it is read, and there a file read whose
path the census builds from `Path(__file__)` or `open(__file__)` is refused as a
file the walk does not scan; where no statement binds it, the file neither
writes a name of its module namespace through a computed name nor may rewrite it
at run time, no module-level statement writes it and the module holds no star
import, it is the file's own path: a value slot as a bare name (the argument of
`Path(__file__)` among them) and the path of a file read the census builds from
`Path(__file__)` or `open(__file__)`, where it proves the callee by binding
(below); in every other case it is refused by name
as a bare name, with that file's reason in a file that writes its namespace
through a computed name or may rewrite it at run time and with no reason
otherwise, and such a file read is refused as a file the walk does not scan, as
in a file where a statement binds it. A file read's path is accepted only as the
census proves it by binding: `Path(...)` only where Path is the file's one
top-level `from pathlib import Path`, never rebound, and `open(...)` only where
open is the builtin, neither bound by a function scope around the read, each
handed one positional argument and no keyword; its steps a `/` with a string
constant, `.parent` and `.resolve()`; a module constant read in the module's own
scope, and a local only where it is a plain local of the page function bound
once that the container proof does not refuse. A path whose callee fails those
conditions, that reads a name a function
scope around the read binds where the module binds a constant of that name or a
module constant the file writes at run time, or that is a relative path spelled
as a string constant, which Python resolves from the working directory, is
refused by name as a path the census does not prove by binding, the line naming
the condition it fails; a local the container proof refuses is refused with that
proof's reason where no module constant shares its name; any other path the
census does not read is a file the walk does not scan. It reads a lambda's
body, its parameters
value slots, and its defaults where the lambda stands in the page; a lambda
reached through a name's value (a local's, a module constant's or a followed
function's default, directly or inside an if-expression, a boolean operation, a
walrus, a starred value or a literal) is refused by name where the name is read,
a callee no def statement defines. It reads a
subscript's container only under a constant index: a slice of any shape, or an
index that is no constant (a name, a call, a parameter, a tuple, or a negative
number, which parses as a unary expression), over a container whose text it
reads (a literal, an f-string, an operator or an if-expression, a module
constant or a local, an attribute, a subscript or a method call on one of those,
or a boolean operation with one of those among its operands) is refused by name,
since it reads the container whole and does not compute what the index selects;
honest forms fail closed with it (`_PAGE[1:]`, a template's leading newline cut;
`PAGES[key]` over a dict constant, the key no constant; `_P[-1]`); so is such a
subscript over a base whose own text it does not read that derives through a
call handed arguments it reads, whose arguments it reads whole and does not
slice either, whether the subscript is the page expression or stands anywhere on
the path of a receiver, a container or an attribute's base (`str(X)[::-1]`,
`dict(a=X)[k]`, `str(X)[::-1].removeprefix(p)`,
`str(X)[k].split(s)[0]`); and any other container that is a base whose own text
it does not read, or a call of one or of a method on one, passes whatever its
index, save where the method allowlist refuses a call on its path (above). The
index of such a subscript, over
a container whose text the pass does not read, is not read at all, whatever it
holds (a name the import system binds, `__file__`, an attribute read on self, on
a parameter or on a class, a call): the item it selects is text such a base
holds (above). A None, bool or int constant, the empty bytes constant and a `*`
or `<<` over int constants are value
slots the pass reads as no text; one that stands directly as the right operand
of a `%` (bare, a tuple element or a dict literal's value, an int modulo such as
`n % 60` among them), as a `.format` argument (an element of a starred list or
tuple
literal and a value of a `**` dict literal among them) or as a value of the dict
literal a `.format_map` is handed is refused by name, whether or not a
conversion takes it, since a conversion can turn it into characters (a `%c`, a
`%x`, a `{:c}`, a `%.1s` over the empty bytes), and one held deeper there (a
name or a local bound to one, an if-expression's branch, a list's element, or a
call's argument, one of the seven builtins' among them) is read as a value slot
and not refused. The run fails by name (SERVED) on any other reference to
`_send` (a read of it that is not a call's function, a store or delete of an
attribute so named, or a string equal to `_send`), which no allowlist entry
excuses, since none is keyed on `_send` itself, and on a content type the pass
cannot read, a content type the census reads other than as
a string constant or a name bound once to one, a script-running type written
outside `_send`, a function that answers outside `_send` more often
than it writes a Content-Type header, a container the module writes at run time
(a module name bound to a call whose object the file changes, read other than as
a call's argument, among them), a local container with an occurrence of its name
that is none of the proven forms,
an attribute read on self, on any other parameter or on an except name, each
judged by the root its base reaches by binding (so one read on a local bound to
self, or on a method's first parameter however spelled under the conditions
above, is one read on self), a
class attribute (an attribute read on a class, a method called on one among
them, through the class's own name, a name the census resolves to it, a method
call on or a subscript of a name whose value holds it or of such a value itself,
or any other base whose root by binding is a class), a function or class object
read as a value, a lambda reached through a name's value, a module function or a
function defined in the page function that is no plain def (an async def, one
carrying a decorator, one whose own body yields, one whose name the file reads
other than as a call's callee or, for a module function, spells in a string
constant or in constants the census folds to text, or stands in a file where a
lookup by name on a namespace mapping takes a key that is neither), a method
called on self,
whatever its def, a route class's method
called other than on the calling method's own first parameter, a method called
on any other parameter, or on a name spelled self that is not that parameter,
whose name the file stores, deletes or names to a setter as an attribute, a call
of, or a
method called on, a route handler's first parameter the census does not
classify, a replacement field
reaching an attribute or an index of its argument in a `.format` or
`.format_map`, a `.format` or `.format_map` whose format string the receiver
reaches other than as a string constant, a join of them or a name bound to one,
a name the
import system binds in every module
that the file does not bind, a subscript by a slice or an index other than a
constant over a container whose text the pass reads or over a base whose own
text it does not read that derives through a call handed arguments it reads,
anywhere on a page expression's path, a subscript by a constant index over a
container whose text the pass reads that
stands as an operand of a `+`, a `%`, an
f-string, a `.join`, a `.format`, a `.format_map` or a `.replace`, a value slot
that stands directly as the right operand of a `%`, a `.format` argument or a
`.format_map` value, a builtin other than the seven a page may name, a call of
str with more than one positional argument, a starred argument or a keyword
other than `object`, a call of max handed one iterable or a starred argument, a
call of int or float bound other than to the builtin, a method whose return the
census does not compute, called on a receiver the pass reads whose text it is
not drawn from, or on a base whose own text it does not read (a `.strip` among
the latter, whose return is a piece of that unread text) that derives through a
call handed arguments it reads (a call of int or float that is the builtin among
them) or is one of the seven builtins' names called unbound, at any call on a
page expression's path, a
join, format, format_map or replace called on the name str, bytes or bytearray,
a `.replace`, `.format`, `.join`, `.format_map` or `.encode` in a shape the
census does not compute,
a `%`, `.format` or `.format_map` on a string constant
that is not expanded, a join whose folded text may run past a million
characters, `__file__` in a file where a statement binds it, any other
receiver or container, any other callee (a module constant, a local, a class, a
subscript, a call and a lambda among them), any
other bare module name
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
function or class among them), any other kind of expression in a page (a float,
complex or Ellipsis constant, an f-string's format spec,
any other operator, a comparison and a unary expression among them, and a yield,
a yield from or an await, whose value is what the generator is sent, what the
iterator it delegates to returns or what the awaited object returns, not its
operand), and a route whose body yields no piece and no file slot (each
refusal of page text applies where the pass reads that text, never inside the
index of a subscript over a container whose text the pass does not read: above),
unless the served allowlist, SERVED_ALLOW, names the place
by its function and expression, with the number of places the entry covers and
the reason (the two answers with no body, the CORS preflight's 204 and the
websocket upgrade's 101, are named there); an entry that names nothing in the
run, or covers a different number of places, fails the run too. A method call
the method allowlist refuses, or a compiled pattern's `.sub` the replacement
rule above refuses, whose page is honest is named instead in the served listing,
SERVED_LISTED, keyed the same way (a compiled pattern's call by its exact call:
the call with its replacement's bytes, and its pattern's binding, the pattern's
text with its flags, so a change to either matches no entry): its place is not
excused but listed,
one line after the stylesheets the listing names, with the entry's reason, and
the run does not fail on it; its places are recorded apart from SERVED_ALLOW's,
and each list's checks read only its own; an entry there that names nothing in
the run, or covers a different number of places, fails the run too, and so does
a key both lists hold, since a place is excused or listed, never both. Three
places are so listed: `str(app or "").capitalize()` in the kernel's
`_pane_label`, called from `_shim`, whose callers are the seven page routes,
each passing a constant lowercase pane key, and `_shim_core_js`, which passes
its own parameter (default `"test"`); and the two `.sub` calls in the kernel's
page stamp, `_stamp_served_html`, one on a str page and one on a bytes page,
whose replacement's group reference re-inserts the matched `<html` tag, a
template expansion the census does not model. In served
text every
`fetch(` and `import(` on a line is read by its own argument, and no
comment skip applies, since a joined constant is one line whatever it starts
with. Each string literal is read on its own, and so is the text of each of
these joins of string constants, at its first literal's line: a `+` of them (an
f-string's literal text at its start or end among them), an f-string whose
fields are string constants, a `%` of them, and a `.join`, `.format`,
`.format_map` or `.replace` called on a string constant or on one of these
joins: a `.join` over a list or tuple of them or over a dict literal whose keys
they are (the keys in order, a repeated key at its first place), and a
`.format`, `.format_map` or `.replace` of them (implicitly concatenated literals
are one constant already). The same methods called on the name str, bytes or
bytearray (`str.join("", [...])`, unbound) are no such join and refuse by name.
A `.replace` other than with two positional arguments, a `.format` or a `.join`
with a starred argument or a `**` keyword, a `.format_map` other than with one
positional argument that is a dict literal whose keys are each a string
constant, and an `.encode` other than with no argument or with one string
constant that is `utf-8`, `utf_8` or `utf8`, in any case, also refuse by name,
since the census does not compute their text; an errors argument to `.encode` is
among those refused, since a handler registered with codecs writes any text in
place of a character UTF-8 cannot encode, and so is every other encoding:
another spelling, even one Python also encodes as UTF-8 (`utf 8`), on the safe
side, one Python hands to the codec registry (`u-t-f-8`), where a search
function the file registers may answer it, and an encoding that is no string
constant (a name bound to `"utf-8"`), which the census does not fold.
A `%`, `.format` or `.format_map` on a string constant or on one of these joins
is not expanded when a field or precision is wider than a million characters (a
`%` conversion's width or precision, or any run of digits in a format field's
own spec) or when a format spec holds a replacement field, whose width is
computed at run time; each such call refuses by name, whatever its arguments,
and each conversion of a `%` is read as Python's `%` parses it (its mapping key
to the parenthesis that balances its first, `%%` the literal percent). No join
of string constants is expanded past a million characters: one whose folded text
may run past that length (a `+`, an f-string, a `.join` or a `.replace` by its
text's exact length, a `.format` or `.format_map` by Python's own length for
each field, a `%` by an upper bound) refuses by name, each literal still read on
its own, a string constant, which is source text, aside; the width test bounds
one field and this cap the whole text. A
tool's name, a tag, an
attribute, an import or a fetch URL split across such a join is therefore read
whole, and a site both reads find is listed once; a fetch URL cut at the join is
listed as the joined text reads it, whole. A `.format` or `.format_map` whose
format string holds a replacement field whose name reaches an attribute or an
index of its argument (`{0.CSS}`, `{h.CSS}`, `{self.body}`, `{0[k]}`) refuses by
name, since the text such a field reads is the argument's attribute or item,
which the pass does not read: the census looks for such a field where the format
string is the receiver's text, a string constant or one of these joins, or the
value of a module constant or a local bound to one, and a `.format` or
`.format_map` whose format string the receiver reaches any other way (a
function's or a method's return, a
parameter, an attribute, an if-expression, a `+` over a name among them) is
refused by name too, since the pass does not read that format string's fields,
unless the receiver is a class (above), refused as a class attribute, a
subscript whose join the pass does not compute, refused as that, or one the pass
refuses by name, in whole or in part, as it reads it (`self.X.format(...)`,
`Handler.X.format(...)`), that line standing for the text the receiver holds.
Text a page joins through
anything but a
string constant (a
name, a call, an attribute, a subscript of a container whose text the pass does
not read, a field or a `%` slot holding one, or a bytes constant, which the census reads each on its own and folds only joins of string constants) is read piece by piece: a tool's
name, a tag or an attribute split there is not seen, and a fetch URL cut there
is classed by the part before the cut. An injection, which puts its value into
the page at its marker, and a compiled pattern's `.sub`, which puts its
replacement into its subject at each match, are such joins: the census reads the
page or the subject whole, the marker or the match in place, and the inserted
text apart, so a fetch URL the insertion completes is classed by what the page
or the subject holds around it, as a cut URL is. A subscript by a
constant index over a container whose text the pass reads (the containers named
above for a slice) that stands as an operand of one of these joins, a `+`, a `%`
or an f-string, or the receiver or an argument of a `.join`, `.format`,
`.format_map` or `.replace` (an element of a list, tuple or set literal or a key
of a dict literal handed to `.join`, an element of a starred list or tuple
literal handed to `.format`, and a value of a dict literal handed to `.format`
or `.format_map`, among them), is refused by name, since the pass reads its
container whole and not the text the join makes of the pieces the indexes
select; the refusal is keyed on such a container, and a subscript of any other
container is read piece by piece, as above; a subscript read through a function
falls under the call limit above. A `.join` whose one argument, or, unbound as
in `str.join("", {...})`, its second, is or holds a set literal or a set
comprehension as the census reads it refuses by name, its iteration order not
fixed, so its join is no one text: the argument itself, a walrus's value, an
if-expression's branches, a boolean operation's operands, a list or tuple
display's elements (a starred one's value among them), the sources of a list or
dict comprehension or a generator (one that names the comprehension's own target
excepted, its items held by an earlier source), and the values of a local of the
page's scope or of a module constant that the census reads the name by (a
local's values, a loop's, an unpacking's or a with target's source and a local
container's appended or stored values among them, or a module constant's value),
a name bound so in turn; a set the census reaches only through a call's return
(a function's, or a read method's, a set's copy or a dict's get among them) or
through a parameter (the argument a call hands it, or its default) is read piece
by piece, under the join limit above (its witnesses: a set a module function
returns, a set's copy and a set a dict's get returns, and a set a module
function's parameter takes as its argument and one it takes as its default, each
joined, a fetch split across its elements). A file the page reads
at run time is covered
by the walk only where the walk scans it as browser text, its DOM loads counted
as a page's are (a JavaScript file under ui/ or vscode-extension/src), and only
where the page reads it with an encoding the census reads as utf-8, utf_8 or
utf8, or with none, and hands the read no other argument: the walk scans each
file once as UTF-8, a byte it cannot decode replaced, so a page that reads such
a file with any other encoding, with an errors handler (in either spelling,
beside a UTF-8 name or with no encoding), or with any other argument besides the
one encoding, a `**` keyword whose mapping the census cannot read among them, is
refused by name, since that one scan may not be the text the page serves, and a
read that names no encoding and hands nothing else takes the locale's default, a
stated limit the census cannot prove is UTF-8; one the walk
scans as Python, as shell, or as JavaScript elsewhere, its DOM loads not
counted, is refused by name, the kind named, since the walk reads none of its
text as a page's; a stylesheet the walk does not scan is named, not scanned; and
any other file is refused by name, as a path the census does not prove (above)
or as a file the walk does not scan, each unless SERVED_ALLOW names the read.
The shell and browser
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
address carries `?token=` (a pane page loaded on such an address by a load the
kernel does not count as a navigation, one whose Sec-Fetch-Dest holds a value
that names neither a document nor an iframe or, with that header absent or
blank, whose Accept does not name text/html; the shell drops the token from its
address before it frames its
panes, and frames
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

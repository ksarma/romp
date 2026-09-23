#!/usr/bin/env python3
"""Census of romp's outbound network activity: every site that opens a connection or starts a program that may open one,
over kernel/, cli/, postal/, bin/, hooks/, ui/, vscode-extension/src, the install scripts and the one program the kernel runs
from tools/, each with its road from the table below. Run from the repository root:

    python3 scripts/network-inventory.py [root]            the sites, one line each, then the summary and the gates
    python3 scripts/network-inventory.py --table [root]    the road table the ledger entry and SECURITY.md are written from
    python3 scripts/network-inventory.py --write-expected  rewrite scripts/network-inventory-expected.json from a clean run

Standard library only. The script exits 1, naming the reason, on: a site with no road (UNCLASSIFIED); a row naming no site
(STALE ROW); no sites at all (a broken scan or moved roots); a declared root that is missing (SCOPE); a Python file that does
not parse (PARSE); an import the census does not know (IMPORT); a road with no table entry or a table entry with no road
(TABLE); a route that serves a page from text the extraction did not read (SERVED); and any figure that differs from the
committed counts in scripts/network-inventory-expected.json (COUNTS): the totals, the counts by kind, by class, by road and by
row key. So a scan that finds fewer sites than the committed count, a
file the walk stopped opening, or a second site inside a function that already has a row is a loud line, not a clean report.
tests/test_price_feed_census.py runs this script over the tree and over mutated copies of it, so the guarantee is the suite's.

The walk is recursive over every declared root (os.walk; __pycache__, node_modules, symlinks and files whose name carries
.test. are skipped) and the kind of a file is its extension (.py, .js, .mjs, .cjs, .sh) or its shebang (python, node, sh):
hooks/ takes every hook whatever its extension, and ui/ and vscode-extension/src are read for the browser and editor kinds
only (a fixture of another kind below them, such as a CRLF Python sample, is skipped by kind and counted as skipped).
scripts/ and the rest of tools/ are the maintainers' release, review and bench tooling that nothing under the runtime trees
runs; the one program the kernel starts from tools/ is named in NAMED, and a string constant naming those directories from
the runtime trees is a gate (PROGRAM), so a second such program takes a place here or fails the run.

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
    serves, a literal whose URL carries a Python format slot (`%s`, `{}`), filled at serve time; a dynamic import() with a
    literal specifier is an import and goes through the package gate below, not a site.
  browser-dom-loads: the browser DOM's own loads (img, iframe, script, link and anchor src, srcset and href writes, setAttribute
    of those, HTML templates carrying them), counted by pattern over the browser and editor code and the served pages, one count
    per line that carries one (a page template inlined as one string is one line, however many it carries); the viewer's and the chat's
    rendered-markdown insertions have no line of their own and are not counted, so the browser-figures road is named from the
    gate's host-list read and the retry probe, not from a request; and the chat-media road from the pipeline's post-pass on a
    message's pictures (`mdImgPostPass`), for the same reason; an anchor's href write loads nothing by itself (the click that
    opens it is the clicked-link road), and a `window.open` is a site keyed file plus tool, never a load counted here.
A fifth class is named in the table and not counted, since the scan cannot see it by construction: a socket primitive called
on a receiver the census cannot resolve (an attribute-held or parameter socket) is not a site here. The scan resolves a socket
receiver as a name bound to socket.socket() in the same function, or by a tuple-literal address argument; a rule on the method
name alone would tag the backends' and transports' own connect methods, which are not sockets. tests/test_price_feed_census.py
plants one such call and holds this sentence to the behaviour.
The clicked-link road holds the openers of a URL the content carries, on both hosts: the editor extension's one
`vscode.env.openExternal` and the browser bundles' `window.open`, each a JavaScript site keyed file plus tool that takes a row (the
road's rows name the chat page's click delegate, the shared opener the feed, the outline and the Waiting-on-you panes install, and
the file viewer's URL anchors; the file preview's own-tab open of the kernel's own file URL takes a local row). Its residual: three
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
its binding (`child_process.<fn>(`, `require('child_process').<fn>(`, a namespace the file imports the module as, or a bare
name the file binds from child_process by a destructured import or require; a bare `exec(` with no such binding is not a
site, since RegExp exec is spelled the same way), each program site classed by its argv as the Python side classes its own; the
connection family the same way: a `get` or `request` of `http` or `https`, a `connect` or `createConnection` of `net` and a
`connect` of `tls` through an inline require, a namespace or default import, or a bare name the file binds from the module
(renamed or not), and `ws` by its constructor shape (`new <binding>(`, `new <namespace>.WebSocket(`, `new (require('ws'))(`),
each an added arm beside the literal spellings (`http.get(`, `net.connect(`, the bare global `new WebSocket(`), a call the
literal list already names on a line counted once under the same tool; and an import gate over every package the scoped files
import or require: a specifier that does not start with `.`, `/` or
`*` names a package (its first path segment, two for a scoped package, `node:` dropped), and a package outside
KNOWN_JS_IMPORTS fails the run (IMPORT). The shell and browser sides are matched by a named list with no completeness gate: a
tool or a client the lists do not name is no site and no line; the Python side's gate is module-granular: an import outside the
allow-list fails the run, and a primitive of a known module outside NET and SUB is not a site. An echo- or print-led shell line
is skipped as a printed remedy only when nothing live follows the printed text: the text outside quotes and the body of every
`$(...)` and backtick substitution, wherever it stands, are scanned by the interpreter arm and the tool list, so `echo "$body" |
curl ...` and `echo "rate: $(curl ...)"` are sites and a remedy that names a tool inside quotes is not.
The pages the kernel serves and its service worker's script, from its own string constants (the dashboard shell, the seven pane
pages, the token login page, the too-large page and /sw.js, with the shim, the timeline boot and the shell scripts they inline),
are read from kernel.py's syntax tree, each route's page function followed to the constants it returns or inlines, and scanned as
browser text keyed kernel/kernel.py plus tool, with the DOM loads counted; a route that serves text/html or text/javascript from
text the extraction cannot read fails the run (SERVED); a file the page reads at run time is covered by the walk when it is a
scanned kind, and a stylesheet is named, not scanned. The whole of kernel.py is not scanned as text, since a text scan misreads
Python and JS concatenations (a Python method spelled like a client, a `from` inside a script split across Python literals).
Over served text the import gate's statement form applies only to a line that starts with import or export (a line led by a
closing brace is a multi-line import's last line in a module and any block's in a page's script), while a literal require() or
import() is gated wherever it stands. The served pages' rows are keyed by tool (kernel/kernel.py plus WebSocket, window.open or
clients.openWindow), so a second socket or opener in the served text is caught by the count per key when it changes the tool
and not when it keeps it, as any rowed shell or JavaScript line is (the residual above). Named and not counted in the served
text: a stylesheet's `url()` loads (THEME_CSS's fonts, _LOADER_CSS's face, _RDRIFT_CSS's and the dashboard shell's own rules, and
the pane stylesheets under ui/webview read at run time), every one a `/media` path on the kernel's own origin, and the same-origin
navigations no list names (`location.replace` on the token login page, `location.reload` in the shim and the shell,
`navigator.serviceWorker.register('/sw.js')`, `history.replaceState`).
A program the kernel starts (ssh, git, gh, npm, npx, the session CLIs, the operator's helper, a watch predicate) may open
connections this scan cannot see: such a site is listed by program, on a road that says so."""
import ast
import builtins
import json
import os
import re
import sys

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
# libraries the webview bundles (markdown, math, sanitising, highlighting, the editor widget, PDF rendering).
KNOWN_JS_IMPORTS = set("""
child_process http ws
assert crypto fs module os path url util vscode typescript
marked katex dompurify highlight.js pdfjs-dist
@codemirror/autocomplete @codemirror/commands @codemirror/lang-css @codemirror/lang-html @codemirror/lang-javascript
@codemirror/lang-json @codemirror/lang-markdown @codemirror/lang-python @codemirror/language @codemirror/legacy-modes
@codemirror/search @codemirror/state @codemirror/view
""".split())
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
   "ui/webview/preview.ts:window.open",   # a browser fetch is placed by its URL, never by a row; preview.ts's `openFileTab` opens
                                          # `fileUrl(path, sid)`, the kernel's own file route, in the browser's own tab
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
# pointer-release handler; a fifth `window.open`, preview.ts's own-tab open of the kernel's file URL, is local (above).
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

# The table's prose columns, one entry per road in the order the ledger entry prints them; the where column is derived from the
# sites on every run, so a hand-written member cannot survive here. Text: the repository's privacy documentation.
ROADS = [
 ("price-feed", "price feed (kernel-request)",
  "an open of the Token usage view (`_token_analytics` with refresh) when the last fetch attempt is older than `PRICE_TTL`, six hours, or there has been none this kernel life; never at boot; nothing re-arms it",
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
  "the render of a message on the web dashboard, and nothing else: no click, no gate, no setting; a session's reply (`md`, from the assistant branch of `renderEventInner`), your own message (`userMd`, from its user branch and from `renderQueued`'s echo of a pending send) and a postal body (`md` in `renderPostalService`; a peer agent's message in `renderTeammate`) go through marked and the shared sanitizer (ui/webview/md-sanitize.ts), whose html profile keeps `img` (src, srcset), `video` (src, poster), `audio`, `source` and `picture` (and an inline svg's `image`), and are written into the page with `innerHTML`, at which point the browser requests every one; `mdImgPostPass`, the row's site, is the pipeline's one line on a message's pictures before the browser fetches them (a URL that failed this page life is parked, and re-probed by the browser-figures row's `Image` site on a reconnect); the editor extension's webviews block these loads by their CSP (`img-src` the webview's own resource origin and `data:`, no `media-src` under `default-src 'none'`), so this road is the web dashboard's alone",
  "GET of each media URL as the message's author wrote it (a session, you or a peer, a class this scan cannot bound), from the browser showing the dashboard to the host the URL names, with the cross-site cookies that browser sends to that host (a `SameSite=None` cookie; not a Lax or Strict one, which only a top-level navigation carries) and no Referer (every page the kernel serves carries `Referrer-Policy: same-origin`); no serve token, key or login token rides in it (the kernel's cookie is scoped to the kernel's own host, and the page's URL is not sent)",
  "none: no setting gates a message's media (the gear's Pictures from the web in files list gates a viewed file's figures, not the chat's)"),
 ("clicked-link", "a link you click (browser)",
  "your click, and nothing else: in the browser showing the dashboard, the chat page's click delegate (`window.open` in ui/webview/render.ts) opens every anchor with a scheme, a link in a session's reply or in your own message, a whole-backtick URL, a URL in a todo's text or a pinned note, the address a todo carries, a pull-request reference; the shared opener (ui/webview/link-opener.ts, installed by the feed, the outline and the Waiting-on-you panes) opens a pull-request or URL link on a pointer release or an Enter; the file viewer (`openUrlTab` in ui/webview/file-view.ts) opens a URL in a viewed file's text on a modified click (Ctrl, Cmd or the middle button; a plain click is left to the browser's own open of the anchor); the file viewer's GitHub button (`GitHub \u2197`, an anchor of class `fileview-btn` in the title bar's `fileview-gh` span, rowed once the owning kernel's `fileGitLink` reply carries a URL) opens as the document it stands in decides: on the chat page the click delegate takes it as it takes every anchor with a scheme (`window.open`, the anchor's default action cancelled); on the Files pane, the feed page and the Waiting-on-you page the anchor's own default open (target `_blank`, rel `noopener`: the browser's new tab), since no opener in those documents matches it (the viewer's own `linkOf` returns only `[data-act=\"openpath\"]`, `a.fv-url` and `a.fv-frag` inside the body, and the button stands in the title bar; the shared opener serves `a.pr-link` and `a.url-link`), so no modified-click path reaches it (`openUrlTab` runs only for a link `linkOf` returns) and a middle click is the browser's own on every page; the viewer mounts in no editor webview (a file click there opens the file in the editor), so the button has no editor leg; the gear's sign-in link, an anchor the gear builds to open in a new tab (`a.target = '_blank'` in ui/webview/gear.js), opens by document: on the dashboard's settings page (/settings), which installs no opener, the browser's own open in a new tab, no site of this tree running on the click; in the editor extension's chat panel, which mounts the gear, the chat delegate's `openLink` post; in the editor's feed panel, which mounts the gear too and installs only the pull-request opener, the webview host's own link handling, outside this tree; in the editor extension the chat delegate, the shared opener and the file viewer post the href to the host, whose `openLink` (vscode-extension/src/extension.ts, from the chat panel's handler and from `routeViewMessage`'s `openLinkLocally` for the feed panel, the outline panel and view and the timeline view) hands it to `vscode.env.openExternal`, the extension's own `vscode://romp.romp-chat-view` deep link handled in the extension instead and never reaching a browser; every opener sits in a click or pointer-release handler, no automatic step; " + CLICK_RESIDUAL,
  "the clicked URL, as the content carries it, to the host that URL names, requested by the browser showing the dashboard (a new tab, `noopener,noreferrer`) or, from the editor extension, by the operating system's default browser, with that browser's own cookies for the host: a pull-request link carries the session's repository name (from the checkout's origin remote, or the text's own owner/repo) and the number, to github.com; the file viewer's GitHub button carries an address romp composes (`_file_github_link` in kernel/kernel.py, run by the kernel that owns the file, once per viewer open): `https://github.com/<owner>/<repository>/blob/<branch or sha>/<path>`, the checkout's owner and repository name read from its origin remote, its current branch, or the commit sha when HEAD is detached, and the file's path inside the checkout, each segment percent-encoded and slashes kept, to github.com, with that browser's own cookies for github.com and no Referer (the chat page's opener passes `noreferrer`; every page the kernel serves carries `Referrer-Policy: same-origin`); the button is not rowed, and no address composed, for an untracked, staged-only or uncommitted file, a path outside a git checkout, a checkout with no origin remote or with one not on github.com, or a relative path with no session directory to place it; no query string is ever added; a link in a message, a todo, a pinned note or a viewed file is whatever its author wrote, a session, you or a peer, a class this scan cannot bound; the gear's sign-in link is the CLI's own OAuth request to claude.com or claude.ai; no serve token, key or login token rides in any of them (the serve token travels only on the bundles' own fetch and media URLs, the extension's websocket URL and its request header, never into a link)",
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
  "each a connection to this machine or a fixed program with no network use of its own: the kernel to the manager, the postal bus and itself; the bus, bin/romp's curls, cli/*, the installed hooks, the VS Code extension and the manager to the kernel on 127.0.0.1; the browser's fetch and websocket to the kernel's own origin (a relative URL or a kernel-URL helper), the served pages' own scripts included (the shim's and the shell's sockets to location.host, the shell's fetches of its own routes, the service worker's open of the kernel's own push URL, and the timeline boot's window.open, which no caller reaches at this head), and its own-tab open of a file the kernel serves (`fileUrl`); the SDK transport's connection to a session host's Unix socket; git read-only queries, ps, scutil and the systemd tools spelled out in the argv; and `_primary_addr`'s UDP connect to TEST-NET-1, which sends no packet. A program on a local road whose far end this scan cannot derive is counted in the external-program row, never here",
  "as the kernel, the CLIs and the browser run", "nothing leaves the machine", "not applicable")
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
  "as the dashboard runs: a fetch whose first argument is a variable, or a dynamic import of a computed module URL; at this head each reads a kernel URL by its binding (a `same-origin` mode, a `fileUrl` or `kernelUrl` result, the PDF worker's URL derived from its own chunk's script src), and in the dashboard shell's scripts a route literal its caller passes (fetchDoc, vact, readSwitch and post in kernel/kernel.py), which the scan cannot derive from the line",
  "to the URL the variable holds at run time; the kernel's own origin at this head by reading the bindings (the editor's webview reaches the same served bundles by its resource URL)",
  "not applicable"),
 "browser-dom-loads": ("the browser DOM's own loads (not derivable by this scan)",
  "as the dashboard and the editor views render: an element that loads (an image, a frame, a script, a stylesheet) loads its URL when the attribute lands, and an anchor's href waits for a click; the viewer's and the chat's rendered-markdown insertions load their figures with no attribute line at all and are not counted",
  "to the URL written: kernel URLs (`fileUrl`, `mediaSrc`, `/media`), object URLs and editor webview URIs, and for a viewed file's figures the hosts the browser-figures road names, and for a rendered message's media the host its URL names (the chat-media road); an anchor's href write loads nothing by itself, the click that opens it is the clicked-link road, and a `window.open` is a site of its own (that road, or a local row), not a load counted here",
  "the figure-host setting for figures; not applicable otherwise"),
}
# Named and not counted: the scan cannot see this class by construction, so its row states the mechanism and the test module
# plants one call and holds the row to it (the sentence in the where cell is the docstring's).
UNSEEN_ROW = ("a socket primitive on a receiver this scan cannot resolve (not derivable by this scan)",
  "not counted: a socket primitive called on a receiver the census cannot resolve (an attribute-held or parameter socket) is not a site here; the scan resolves a socket receiver as a name bound to `socket.socket()` in the same function or by a tuple-literal address, and a rule on the method name alone would tag the backends' and transports' own connect methods, which are not sockets",
  "wherever such a call would run; no site of this class can be listed by this scan",
  "to the address the socket is given at run time",
  "not applicable")

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
    def emit(self, *a):
        self.sites.append(Site(*a))


def _call_arg(line, opener):
    """The first argument of the first `opener` (`fetch(`, `import(`) on the line, up to its top-level comma or the closing paren."""
    text = line[line.index(opener) + len(opener):]; depth, out = 0, []
    for ch in text:
        if ch in "([{": depth += 1
        elif ch in ")]}":
            if depth == 0: break
            depth -= 1
        elif ch == "," and depth == 0: break
        out.append(ch)
    return "".join(out).strip()


_HELPER_CALL = re.compile(r"^(?:%s)\(" % "|".join(KERNEL_URL_HELPERS))   # a kernel-URL helper call as the fetch argument
SERVED_CTYPES = ("text/html", "text/javascript")   # the pages, and the service worker's script: text the kernel serves and the browser runs
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


class Scan(ast.NodeVisitor):
    def __init__(self, rel, res):
        self.rel, self.res, self.stack, self.alias, self.consts, self.binds, self.imports = rel, res, [], {}, {}, [], []
        self.defs, self.routes = [], []   # the enclosing def nodes; the `_send` calls of a served page or script (served_texts)
    def visit_Import(self, n):
        self.alias.update({a.asname or a.name: a.name for a in n.names}); self.imports.extend((a.name.split(".")[0], n.lineno) for a in n.names)
    def visit_ImportFrom(self, n):
        self.alias.update({a.asname or a.name: (n.module or "") + "." + a.name for a in n.names})
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
    def visit_Constant(self, n):   # a program path spelled as one string: "tools/x.mjs"
        if isinstance(n.value, str) and _PROGRAM_PATH.match(n.value): self.program_ref(n, n.value)
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
        self.stack.append(n.name); self.binds.append(b); self.defs.append(n); self.generic_visit(n); self.defs.pop(); self.binds.pop(); self.stack.pop()
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
        if (attr == "_send" and len(n.args) >= 3 and isinstance(n.args[2], ast.Constant) and isinstance(n.args[2].value, str)
                and n.args[2].value.startswith(SERVED_CTYPES)):   # a route that serves a page or a script: its text is scanned after the walk
            fn = next((x for x in reversed(self.defs) if not isinstance(x, ast.ClassDef)), None)
            cls = next((x.name for x in reversed(self.defs) if isinstance(x, ast.ClassDef)), None)
            self.routes.append((n, fn, cls))
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
    """The binding shapes of one module, compiled once per module: the quoted specifier (`node:` or not), a destructured require
    or import (the names), and a require assigned whole or a namespace or default import (the spaces)."""
    spec = r"['\"](?:node:)?%s['\"]" % re.escape(mod)
    names = re.compile(r"(?:const|let|var)\s*\{([^}]*)\}\s*=\s*require\(\s*%s\s*\)|import\s*(?:type\s+)?\{([^}]*)\}\s*from\s*%s" % (spec, spec))
    spaces = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*require\(\s*%s\s*\)|import\s+\*\s+as\s+(\w+)\s+from\s*%s|import\s+(\w+)\s+from\s*%s" % (spec, spec, spec))
    return re.compile(spec), names, spaces, mod


_CP_MODULE, _CP_NAMES, _CP_SPACES, _CP_NAME = _binding_patterns("child_process")
_CP_RENAME = re.compile(r"\s+as\s+|\s*:\s*")   # the `as` or `:` that renames a destructured member
# The connection family read through the same bindings (an added arm beside JS's literal spellings): module -> the members that
# open a connection; the tool a site is keyed on is the literal list's own name (`http.get` for http and https alike). ws is
# constructor-shaped (`new <binding>(`) and keyed `WebSocket`, the literal `new WebSocket(` entry's name.
NET_FAMILY = {"http": ("get", "request"), "https": ("get", "request"), "net": ("connect", "createConnection"), "tls": ("connect",)}
_NET_PATTERNS = {mod: _binding_patterns(mod) for mod in tuple(NET_FAMILY) + ("ws",)}


def _names_module(text, patterns):
    """Whether the file spells the module's quoted specifier at all (the four spellings _binding_patterns's specifier admits), a
    substring check before any regex runs over the file."""
    mod = patterns[3]
    return any(q + m + q in text for q in "'\"" for m in (mod, "node:" + mod))


def _module_bindings(text, patterns):
    """(names, spaces) a JavaScript or TypeScript file binds from one module, by its patterns (_binding_patterns): `names` maps a
    bare name the file destructures or imports to the member it stands for (renamed or not; a `type` import binds no value
    but is read for parity), `spaces` holds the names the file keeps the module under."""
    spec, names_rx, spaces_rx, _mod = patterns
    names, spaces = {}, set()
    if not _names_module(text, patterns): return names, spaces
    for m in names_rx.finditer(text):
        for part in (m.group(1) or m.group(2) or "").split(","):
            part = part.strip()
            if part.startswith("type "): part = part[5:].strip()
            if part:
                bits = [b.strip() for b in _CP_RENAME.split(part)]
                names[bits[-1]] = bits[0]
    for m in spaces_rx.finditer(text):
        spaces.add(m.group(1) or m.group(2) or m.group(3))
    return names, spaces


def _cp_bindings(text):
    """The names a JavaScript or TypeScript file binds from child_process, and the call patterns those bindings make, read once
    per file: `names` maps a bare name the file destructures or imports to the family member it stands for, `spaces` holds
    the names the file keeps the module under (a namespace or default import, a require assigned whole), `qualified` matches
    a family call qualified to the module (`child_process.<fn>(`, `require('child_process').<fn>(`, a name in `spaces`), and
    `bare` matches a family call by a name in `names`, or is None when the file binds none. A file whose text never names
    child_process binds nothing and qualifies no call, so it is None here and no line of it is a site. A family member
    called by a bare name the file does not bind is not a site."""
    if "child_process" not in text: return None
    names, spaces = _module_bindings(text, (_CP_MODULE, _CP_NAMES, _CP_SPACES, _CP_NAME))
    qual = [r"\bchild_process", r"require\(\s*%s\s*\)" % _CP_MODULE.pattern] + [r"\b" + re.escape(s) for s in sorted(spaces)]
    bare = sorted(n for n, fn in names.items() if fn in CP_FAMILY)
    return {"names": names, "spaces": spaces, "qualified": re.compile(r"(?:%s)\.(%s)\(" % ("|".join(qual), "|".join(CP_FAMILY))),
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
    and tls a member call qualified to an inline require or to a space (a namespace or default import, a require assigned
    whole), and a call by a bare name the file binds from the module (renamed or not); for ws the constructor shape
    (`new (require('ws'))(`, `new (require('ws').WebSocket)(`, `new <space>(`, `new <space>.WebSocket(`, `new <bound name>(`).
    Empty for a file that names none of the modules; the bare global `new WebSocket(` is the literal list's."""
    arms = []
    for mod, members in NET_FAMILY.items():
        if not _names_module(text, _NET_PATTERNS[mod]): continue
        names, spaces = _module_bindings(text, _NET_PATTERNS[mod])
        tool = ("http" if mod == "https" else mod) + ".%s"
        qual = [r"require\(\s*%s\s*\)" % _NET_PATTERNS[mod][0].pattern] + [r"\b" + re.escape(s) for s in sorted(spaces)]
        arms.append((re.compile(r"(?:%s)\.(%s)\(" % ("|".join(qual), "|".join(members))), lambda m, t=tool: t % m.group(1)))
        bare = {n: fn for n, fn in names.items() if fn in members}
        if bare:
            arms.append((re.compile(r"(?<![\w.$])(%s)\(" % "|".join(map(re.escape, sorted(bare)))), lambda m, t=tool, b=bare: t % b[m.group(1)]))
    if _names_module(text, _NET_PATTERNS["ws"]):
        names, spaces = _module_bindings(text, _NET_PATTERNS["ws"])
        heads = ([r"\(\s*require\(\s*%s\s*\)(?:\.WebSocket)?\s*\)" % _NET_PATTERNS["ws"][0].pattern]
                 + [re.escape(s) + r"(?:\.WebSocket)?" for s in sorted(spaces)] + [re.escape(n) for n, fn in sorted(names.items()) if fn == "WebSocket"])
        arms.append((re.compile(r"\bnew\s+(?:%s)\s*\(" % "|".join(heads)), lambda m: "WebSocket"))
    return arms


def _net_sites(ln, nb):
    """The tools of the connection family's binding arm (_net_bindings) on the line, each once, in order of first match."""
    out = []
    for rx, tool_of in nb or ():
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


def _js_specifiers(s, served=False):
    """The module specifiers a JavaScript or TypeScript line imports or requires: an import or export statement's `from` string
    (the closing line of a multi-line import starts with `}`; in served text, where a `}` leads any block, the statement form
    applies only to a line that starts with import or export), a side-effect import, and every literal require() and import()."""
    if "import" not in s and "require" not in s and "from" not in s: return []   # every shape below spells one of the three
    out = []
    if s.startswith(("import", "export")) or (not served and s.startswith("}")):
        m = _JS_FROM.search(s)
        if m: out.append(m.group(2))
        m = _JS_SIDE_EFFECT.match(s)
        if m: out.append(m.group(2))
    out.extend(m.group(2) for m in _JS_REQUIRE.finditer(s))
    return out


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


def line_scan(rel, kind, text, res, base=0, dom=None, served=False):
    """The shell or JavaScript sites, the DOM loads and the package gate over one file's text (read once, by scan). For a page
    the kernel serves (served_texts), `base` offsets the line numbers to the constant's place in its Python file, `dom` forces
    the DOM arm on (None keeps the rule: the browser and editor roots), and `served` narrows the import gate's statement form
    to a line that starts with import or export."""
    tools, any_tool, comment = (JS_RX, JS_ANY, ("//", "*", "/*")) if kind == "js" else (SH_RX, SH_ANY, ("#",))
    if dom is None: dom = kind == "js" and rel.startswith(tuple(d + "/" for d in JS_ROOTS))
    cp = _cp_bindings(text) if kind == "js" else None
    nb = _net_bindings(text) if kind == "js" else None
    for i, ln in enumerate(text.splitlines(), base + 1):
        s = ln.strip(); live = ln; seen = set()
        if s.startswith(comment): continue
        if kind == "sh" and s.startswith(("echo ", "print(")):   # a printed remedy is not a request: only what follows the printed text
            live = _live_remainder(s[5:] if s.startswith("echo ") else s[6:])   # live (_live_remainder) is scanned, and a line with nothing live is skipped
            if not live.strip(): continue
        if kind == "js":
            for spec in _js_specifiers(s, served):
                pkg = _js_package(spec)
                if pkg and pkg not in KNOWN_JS_IMPORTS:
                    res.problems.append("IMPORT %s:%d imports %s, a package the census does not know: a client that opens connections or starts programs "
                                        "takes its primitives into JS or the child_process family; either way add it to KNOWN_JS_IMPORTS with the reason" % (rel, i, pkg))
            for fn, at in _cp_sites(ln, cp):   # a program site, classed by its argv as Scan.visit_Call classes a Python command
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
_READ_CALLS = ("read_text", "read")                                        # a file read bound to a page's slot


class _Served(object):
    """The text a route's page is served from, followed through the module's syntax tree: the body expression of each `_send`
    resolved to its string constants (a literal, an f-string's parts, `+` and `%` operands and the argument tuple, a
    conditional's branches, a comprehension's element, a module constant by name, a local by every binding it has in the
    function, a `.format`, `.join`, `.replace` or `.strip` receiver and its arguments, every `return` of a module function or
    a `self.` method the page calls, and the arguments of any other call), each a piece (label, first line, text) for
    line_scan; a local bound to a `.read_text()` or `.read()` is a file slot (label, line, path) the walk covers or names; a
    parameter, an attribute, a subscript, a comparison, a boolean or unary expression and a lambda are value slots (no text);
    anything else is text the census did not read, a SERVED problem by name, as is a route whose body yields no piece and no
    file slot."""
    def __init__(self, rel, tree):
        self.rel, self.consts, self.funcs, self.methods, self.names = rel, {}, {}, {}, set(dir(builtins))
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name): self.consts[node.targets[0].id] = node.value
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)): self.funcs[node.name] = node
            elif isinstance(node, ast.ClassDef): self.methods[node.name] = {n.name: n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
            if isinstance(node, (ast.Import, ast.ImportFrom)): self.names.update((a.asname or a.name).split(".")[0] for a in node.names)
            else: self.names.update(n.id for n in ast.walk(node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)) if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else None
        self.names.update(self.funcs); self.names.update(self.methods)   # every module-level binding: a bare name of one is a value slot
        self.pieces, self.files, self.problems = [], [], []

    @staticmethod
    def _locals(fn):
        """(name -> every value bound to it by a single-name assignment in the function's own body, the other names the body
        binds (a loop or with target, an except name, an unpacking, a walrus), the functions defined inside it), nested defs
        not entered."""
        out, bound, nested, stack = {}, set(), {}, list(fn.body)
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)): nested[n.name] = n; continue
            if isinstance(n, (ast.ClassDef, ast.Lambda)): continue
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name): out.setdefault(n.targets[0].id, []).append(n.value)
            elif isinstance(n, ast.AugAssign) and isinstance(n.target, ast.Name): out.setdefault(n.target.id, []).append(n.value)
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is not None: out.setdefault(n.target.id, []).append(n.value)
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store): bound.add(n.id)
            elif isinstance(n, ast.ExceptHandler) and n.name: bound.add(n.name)
            stack.extend(ast.iter_child_nodes(n))
        return out, bound, nested

    @staticmethod
    def _returns(fn):
        out, stack = [], list(fn.body)
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)): continue
            if isinstance(n, ast.Return) and n.value is not None: out.append(n.value)
            stack.extend(ast.iter_child_nodes(n))
        return out

    def _ctx(self, fn, cls, outer=None):
        """(the value-slot names: parameters and the other names the body binds, the locals, the class, the nested functions);
        a nested function's context (outer given) sees the enclosing function's names and locals under its own."""
        a = fn.args
        params = {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs} | ({a.vararg.arg} if a.vararg else set()) | ({a.kwarg.arg} if a.kwarg else set())
        local, bound, nested = self._locals(fn)
        if outer is not None:
            params, local, nested = params | outer[0], dict(outer[1], **local), dict(outer[3], **nested)
        return params | bound, local, cls, nested

    def _path(self, e):
        """The repository-relative path a pathlib expression spells: `ROOT / "ui" / "x.css"` through the module's constants, with
        Path(__file__) as this file and .parent as its directory; None when the census cannot read it."""
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Div) and isinstance(e.right, ast.Constant) and isinstance(e.right.value, str):
            left = self._path(e.left)
            return None if left is None else (left + "/" if left else "") + e.right.value
        if isinstance(e, ast.Name):
            if e.id in self.consts: return self._path(self.consts[e.id])
            return None
        if isinstance(e, ast.Attribute) and e.attr == "parent":
            base = self._path(e.value)
            return None if base is None else os.path.dirname(base)
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute) and e.func.attr == "resolve": return self._path(e.func.value)
        if isinstance(e, ast.Call) and isinstance(e.func, ast.Name) and e.func.id in ("Path", "open") and e.args:
            a = e.args[0]
            if isinstance(a, ast.Name) and a.id == "__file__": return self.rel
            if isinstance(a, ast.Constant) and isinstance(a.value, str): return a.value
            return self._path(a)
        return None

    def resolve(self, e, ctx, label, done):
        """Add the text `e` evaluates to under ctx (the value-slot names, the locals, the class, the nested functions) as pieces
        and file slots; `done` holds the names already followed for this route, so a constant, a function or a local is read
        once per route and a cycle stops."""
        params, local, cls, nested = ctx
        if isinstance(e, ast.Constant):
            if isinstance(e.value, str): self.pieces.append((label, e.lineno, e.value))
        elif isinstance(e, ast.JoinedStr):
            for v in e.values:
                if isinstance(v, ast.Constant): self.pieces.append((label, e.lineno, v.value))
                elif isinstance(v, ast.FormattedValue): self.resolve(v.value, ctx, label, done)
        elif isinstance(e, ast.BinOp) and isinstance(e.op, (ast.Add, ast.Mod)):
            self.resolve(e.left, ctx, label, done); self.resolve(e.right, ctx, label, done)
        elif isinstance(e, (ast.Tuple, ast.List)):
            for x in e.elts: self.resolve(x, ctx, label, done)
        elif isinstance(e, ast.IfExp):
            self.resolve(e.body, ctx, label, done); self.resolve(e.orelse, ctx, label, done)
        elif isinstance(e, (ast.GeneratorExp, ast.ListComp, ast.SetComp)):
            names = {n.id for g in e.generators for n in ast.walk(g.target) if isinstance(n, ast.Name)}
            self.resolve(e.elt, (params | names, local, cls, nested), label, done)
        elif isinstance(e, ast.Dict):
            for x in e.keys + e.values:
                if x is not None: self.resolve(x, ctx, label, done)
        elif isinstance(e, ast.Set):
            for x in e.elts: self.resolve(x, ctx, label, done)
        elif isinstance(e, (ast.Await, ast.Yield, ast.YieldFrom, ast.NamedExpr)):
            if e.value is not None: self.resolve(e.value, ctx, label, done)
        elif isinstance(e, ast.Name):
            if e.id in local:
                key = ("local", id(local), e.id)   # a local read once per function per route: `x = x.replace(...)` reads itself
                if key in done: return
                done.add(key)
                for v in local[e.id]:
                    if isinstance(v, ast.Call) and isinstance(v.func, ast.Attribute) and v.func.attr in _READ_CALLS:   # a file read bound to a slot
                        self.files.append((label, v.lineno, e.id, self._path(v.func.value)))
                    else: self.resolve(v, ctx, label, done)
            elif e.id in self.consts:
                if e.id not in done: done.add(e.id); self.resolve(self.consts[e.id], (set(), {}, None, {}), e.id, done)
            elif e.id not in params and e.id not in nested and e.id not in self.names:   # a name bound nowhere the census reads
                self.problems.append("SERVED %s:%d builds a served page from %s, text the census did not read" % (self.rel, e.lineno, ast.unparse(e)[:60]))
        elif isinstance(e, ast.Call):
            f = e.func
            if isinstance(f, ast.Attribute) and f.attr in _READ_CALLS: self.files.append((label, e.lineno, ast.unparse(f.value)[:40], self._path(f.value)))
            elif isinstance(f, ast.Attribute) and f.attr in _TEXT_CALLS: self.resolve(f.value, ctx, label, done)
            elif isinstance(f, ast.Name) and f.id in nested:   # a function defined inside the page function, over its names
                key = ("nested", id(nested[f.id]))
                if key not in done:
                    done.add(key); fn = nested[f.id]
                    for r in self._returns(fn): self.resolve(r, self._ctx(fn, cls, ctx), label + "." + f.id, done)
            elif isinstance(f, ast.Name) and f.id in self.funcs:
                if f.id not in done:
                    done.add(f.id); fn = self.funcs[f.id]
                    for r in self._returns(fn): self.resolve(r, self._ctx(fn, None), f.id, done)
            elif isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id == "self" and cls and f.attr in self.methods.get(cls, {}):
                key = cls + "." + f.attr
                if key not in done:
                    done.add(key); fn = self.methods[cls][f.attr]
                    for r in self._returns(fn): self.resolve(r, self._ctx(fn, cls), key, done)
            for a in e.args + [k.value for k in e.keywords]: self.resolve(a, ctx, label, done)   # a value slot's arguments are text too (json.dumps(x))
        elif isinstance(e, (ast.Attribute, ast.Subscript, ast.Compare, ast.BoolOp, ast.UnaryOp, ast.Lambda, ast.Starred, ast.BinOp, ast.Slice)):
            pass   # a value slot: no text of its own (a BinOp here is arithmetic or a pathlib join, not the `+` or `%` above)
        else:
            self.problems.append("SERVED %s:%d builds a served page from %s, text the census did not read" % (self.rel, e.lineno, ast.unparse(e)[:60]))

    def run(self, routes):
        for call, fn, cls in routes:
            before = len(self.pieces), len(self.files)
            ctx = self._ctx(fn, cls) if fn is not None else (set(), {}, cls, {})
            self.resolve(call.args[1], ctx, fn.name if fn is not None else "<module>", set())
            if (len(self.pieces), len(self.files)) == before:
                self.problems.append("SERVED %s:%d serves %s from %s, text the census did not read"
                                     % (self.rel, call.lineno, call.args[2].value.split(";")[0], ast.unparse(call.args[1])[:60]))


def served_texts(rel, tree, routes, res):
    """The served pages' pass over one Python file: every piece the routes reach scanned as browser text with the DOM arm on,
    keyed file plus tool at the constant's own lines; a file a page reads at run time is covered by the walk when it is a
    scanned kind (not scanned again), named when it is a stylesheet, and a SERVED problem otherwise."""
    sv = _Served(rel, tree); sv.run(routes)
    seen = set()
    for label, lineno, text in sorted(sv.pieces, key=lambda p: (p[1], p[2])):
        if (lineno, text) in seen: continue
        seen.add((lineno, text)); line_scan(rel, "js", text, res, base=lineno - 1, dom=True, served=True)
    for label, lineno, name, path in sorted(sv.files, key=lambda f: f[1]):
        if path is not None and path in res.files: continue
        if path is not None and path.endswith(".css"):
            if (rel, lineno, path) not in res.served_files: res.served_files.append((rel, lineno, path))
        else: res.problems.append("SERVED %s:%d reads %s for a served page, a file the walk does not scan" % (rel, lineno, path or name))
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
    table = {r[0] for r in ROADS}; roads = set(fig["per_road"])
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
    out.write("| %s | %s | %s | %s | %s |\n" % UNSEEN_ROW)


def main(argv):
    args = [a for a in argv if not a.startswith("--")]; flags = {a for a in argv if a.startswith("--")}
    unknown = flags - {"--table", "--write-expected"}
    if unknown or len(args) > 1:
        sys.stderr.write("usage: network-inventory.py [--table | --write-expected] [root]\n"); return 2
    root = os.path.abspath(args[0] if args else ".")
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

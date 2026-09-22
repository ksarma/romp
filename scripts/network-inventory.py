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
(TABLE); and any figure that differs from the committed counts in scripts/network-inventory-expected.json (COUNTS): the
totals, the counts by kind, by class, by road and by row key. So a scan that finds fewer sites than the committed count, a
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
    sliceUrl); an absolute literal needs a row; a computed argument is counted here and listed; a dynamic import() with a
    literal specifier is an import and goes through the package gate below, not a site.
  browser-dom-loads: the browser DOM's own loads (img, iframe, script, link and anchor src, srcset and href writes, setAttribute
    of those, HTML templates carrying them, window.open), counted by pattern over the browser and editor code; the viewer's
    and the chat's rendered-markdown insertions have no line of their own and are not counted, so the browser-figures road
    is named from the gate's host-list read and the retry probe, not from a request.
A fifth class is named in the table and not counted, since the scan cannot see it by construction: a socket primitive called
on a receiver the census cannot resolve (an attribute-held or parameter socket) is not a site here. The scan resolves a socket
receiver as a name bound to socket.socket() in the same function, or by a tuple-literal address argument; a rule on the method
name alone would tag the backends' and transports' own connect methods, which are not sockets. tests/test_price_feed_census.py
plants one such call and holds this sentence to the behaviour.

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
browser and editor side is a line scan too: the clients in JS; the child_process family qualified to
its binding (`child_process.<fn>(`, `require('child_process').<fn>(`, a namespace the file imports the module as, or a bare
name the file binds from child_process by a destructured import or require; a bare `exec(` with no such binding is not a
site, since RegExp exec is spelled the same way), each program site classed by its argv as the Python side classes its own;
and an import gate over every package the scoped files import or require: a specifier that does not start with `.`, `/` or
`*` names a package (its first path segment, two for a scoped package, `node:` dropped), and a package outside
KNOWN_JS_IMPORTS fails the run (IMPORT). The shell and browser sides are matched by a named list with no completeness gate: a
tool or a client the lists do not name is no site and no line; the Python side's gate is module-granular: an import outside the
allow-list fails the run, and a primitive of a known module outside NET and SUB is not a site.
A program the kernel starts (ssh, git, gh, npm, npx, the session CLIs, the operator's helper, a watch predicate) may open
connections this scan cannot see: such a site is listed by program, on a road that says so."""
import ast
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
# reach the kernel on the loopback, each a site) and ws (the extension's websocket to the kernel, a site); every other one
# opens nothing: the node built-ins for files, paths, hashing and assertions; the editor API vscode (its openExternal hands a
# URL to the OS browser, as `open` does); the TypeScript compiler; and the browser libraries the webview bundles (markdown,
# math, sanitising, highlighting, the editor widget, PDF rendering).
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
   "vscode-extension/src/extension.ts:WebSocket", "ui/webview/federation.ts:WebSocket")   # a browser fetch is placed by its URL, never by a row
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
_t("install-bootstrap", "bootstrap.sh:curl", "bootstrap.sh:git clone", "bootstrap.sh:git fetch", "bootstrap.sh:git pull")
_t("install-sdk-setup", "bin/romp-sdk-setup:curl", "bin/romp-sdk-setup:wget", "bin/romp-sdk-setup:pip install")
_t("install-ext", "vscode-extension/install.sh:npm install", "vscode-extension/src/extension.ts:install.sh",
   "vscode-extension/install.sh:node -e", "vscode-extension/install.sh:npx")   # the version stamp (local) and the vsce fetch, both behind the editor-CLI gate
_t("install-codex-setup", "bin/romp-codex-setup:pip install", "kernel/codex_runtime.py:install_runtime")
LOCAL_ROADS = {"local-bus", "local-manager", "local-kernel", "local-program", "local-git"}
RUNTIME_ROADS = {"predicate-watch", "api-key-helper"}   # the program text itself arrives at run time
CLASSES = ("external-program", "runtime-program", "browser-computed-url", "browser-dom-loads")

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
  "each a connection to this machine or a fixed program with no network use of its own: the kernel to the manager, the postal bus and itself; the bus, bin/romp's curls, cli/*, the installed hooks, the VS Code extension and the manager to the kernel on 127.0.0.1; the browser's fetch and websocket to the kernel's own origin (a relative URL or a kernel-URL helper); the SDK transport's connection to a session host's Unix socket; git read-only queries, ps, scutil and the systemd tools spelled out in the argv; and `_primary_addr`'s UDP connect to TEST-NET-1, which sends no packet. A program on a local road whose far end this scan cannot derive is counted in the external-program row, never here",
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
  "as the dashboard runs: a fetch whose first argument is a variable, or a dynamic import of a computed module URL; at this head each reads a kernel URL by its binding (a `same-origin` mode, a `fileUrl` or `kernelUrl` result, the PDF worker's URL derived from its own chunk's script src), which the scan cannot derive from the line",
  "to the URL the variable holds at run time; the kernel's own origin at this head by reading the bindings (the editor's webview reaches the same served bundles by its resource URL)",
  "not applicable"),
 "browser-dom-loads": ("the browser DOM's own loads (not derivable by this scan)",
  "as the dashboard and the editor views render: an element loads its URL when the attribute lands; the viewer's and the chat's rendered-markdown insertions load their figures with no attribute line at all and are not counted",
  "to the URL written: kernel URLs (`fileUrl`, `mediaSrc`, `/media`), object URLs and editor webview URIs, and for a viewed file's figures the hosts the browser-figures road names",
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
      ("import()", r"(?<![\w.$])import\("), ("figureHosts", r"loadSettings\(\)\.figureHosts")]
# The child_process family is matched through its binding (see _cp_bindings), never as a bare name: `exec(` is RegExp exec too.
DOM = [("attribute write", r"\.(?:src|srcset|href)\s*=[^=]"), ("setAttribute", r"setAttribute\(\s*[\"'](?:src|srcset|href)[\"']"),
       ("template", r"<(?:img|script|iframe|link|source|video|audio|a|embed|object)\b[^>]*\b(?:src|srcset|href)="), ("window.open", r"window\.open\(")]


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
_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")                        # a URL scheme at the head of a literal


def _fetch_class(arg):
    """'local' (a relative literal, or a kernel-URL helper call), 'absolute' (a literal with a scheme or a host), or 'computed'."""
    if _HELPER_CALL.match(arg): return "local"
    if arg[:1] in ("'", '"', "`"):
        body = arg[1:arg.find(arg[0], 1)] if arg.find(arg[0], 1) > 0 else arg[1:]
        if body.startswith("//") or _SCHEME.match(body): return "absolute"
        if body.startswith("${"): return "computed"
        return "local"
    return "computed"


class Scan(ast.NodeVisitor):
    def __init__(self, rel, res):
        self.rel, self.res, self.stack, self.alias, self.consts, self.binds, self.imports = rel, res, [], {}, {}, [], []
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
        self.stack.append(n.name); self.binds.append(b); self.generic_visit(n); self.binds.pop(); self.stack.pop()
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
    if "." in name: return None
    with open(path, "rb") as fh: first = fh.readline()
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


_CP_MODULE = r"['\"](?:node:)?child_process['\"]"
# The binding shapes, compiled once: a destructured require or import (the names), a require assigned whole or a namespace
# or default import (the spaces), and the `as` or `:` that renames a destructured member.
_CP_NAMES = re.compile(r"(?:const|let|var)\s*\{([^}]*)\}\s*=\s*require\(\s*%s\s*\)|import\s*(?:type\s+)?\{([^}]*)\}\s*from\s*%s" % (_CP_MODULE, _CP_MODULE))
_CP_SPACES = re.compile(r"(?:const|let|var)\s+(\w+)\s*=\s*require\(\s*%s\s*\)|import\s+\*\s+as\s+(\w+)\s+from\s*%s|import\s+(\w+)\s+from\s*%s" % (_CP_MODULE, _CP_MODULE, _CP_MODULE))
_CP_RENAME = re.compile(r"\s+as\s+|\s*:\s*")


def _cp_bindings(text):
    """The names a JavaScript or TypeScript file binds from child_process, and the call patterns those bindings make, read once
    per file: `names` maps a bare name the file destructures or imports to the family member it stands for, `spaces` holds
    the names the file keeps the module under (a namespace or default import, a require assigned whole), `qualified` matches
    a family call qualified to the module (`child_process.<fn>(`, `require('child_process').<fn>(`, a name in `spaces`), and
    `bare` matches a family call by a name in `names`, or is None when the file binds none. A file whose text never names
    child_process binds nothing and qualifies no call, so it is None here and no line of it is a site. A family member
    called by a bare name the file does not bind is not a site."""
    if "child_process" not in text: return None
    names, spaces = {}, set()
    for m in _CP_NAMES.finditer(text):
        for part in (m.group(1) or m.group(2) or "").split(","):
            part = part.strip()
            if part.startswith("type "): part = part[5:].strip()
            if part:
                bits = [b.strip() for b in _CP_RENAME.split(part)]
                names[bits[-1]] = bits[0]
    for m in _CP_SPACES.finditer(text):
        spaces.add(m.group(1) or m.group(2) or m.group(3))
    qual = [r"\bchild_process", r"require\(\s*%s\s*\)" % _CP_MODULE] + [r"\b" + re.escape(s) for s in sorted(spaces)]
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


def _js_specifiers(s):
    """The module specifiers a JavaScript or TypeScript line imports or requires: an import or export statement's `from` string
    (the closing line of a multi-line import starts with `}`), a side-effect import, and every literal require() and import()."""
    if "import" not in s and "require" not in s and "from" not in s: return []   # every shape below spells one of the three
    out = []
    if s.startswith(("import", "export", "}")):
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


def line_scan(rel, kind, text, res):
    """The shell or JavaScript sites, the DOM loads and the package gate over one file's text (read once, by scan)."""
    tools, any_tool, comment = (JS_RX, JS_ANY, ("//", "*", "/*")) if kind == "js" else (SH_RX, SH_ANY, ("#",))
    dom = kind == "js" and rel.startswith(tuple(d + "/" for d in JS_ROOTS))
    cp = _cp_bindings(text) if kind == "js" else None
    for i, ln in enumerate(text.splitlines(), 1):
        s = ln.strip()
        if s.startswith(comment) or s.startswith(("echo ", "print(")): continue   # a printed remedy is not a request
        if kind == "js":
            for spec in _js_specifiers(s):
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
            for m in SH_INTERPRETER.finditer(ln):   # the interpreter arm: keyed file plus tool, external-program by class
                tool = "%s %s" % (os.path.basename(m.group("head")), m.group("flag"))
                res.emit(rel, i, tool, s[:70], "-", T.get("%s:%s" % (rel, tool)), "external-program", kind)
        if any_tool.search(ln):   # the list's alternation (_compiled): a miss means no tool below matches, so the loop is skipped
            for tool, rx in tools:
                if rx.search(ln):
                    road, cls, head = T.get("%s:%s" % (rel, tool)), None, s[:70]
                    if tool == "fetch":   # placed by its URL: the argument is what the listing shows
                        arg = _call_arg(ln, "fetch("); fc = _fetch_class(arg); head = "fetch(%s)" % arg[:60]
                        if fc == "local": road = "local-kernel"
                        elif fc == "computed": cls = "browser-computed-url"
                    if tool == "import()":   # a literal specifier is an import (gated above), a computed one a site of the class
                        arg = _call_arg(ln, "import(")
                        if arg[:1] in ("'", '"', "`") and "${" not in arg: continue
                        cls, head = "browser-computed-url", "import(%s)" % arg[:60]
                    res.emit(rel, i, tool, head, "-", road, cls, kind)
        if dom and DOM_ANY.search(ln):
            for name, rx in DOM_RX:
                if rx.search(ln): res.dom.append((rel, i, name, s[:70])); break


def scan(root):
    res = Result(); bootstrap = None
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
             "browser-dom-loads": "%d lines in %d files under %s (%s)" % (len(res.dom), len(files), " and ".join(JS_ROOTS), ", ".join("%s %d" % (k, kinds[k]) for k in sorted(kinds)))}
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

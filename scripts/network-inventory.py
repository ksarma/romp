#!/usr/bin/env python3
"""Census of romp's outbound network activity: every site that opens a connection or starts a program that may open one, over
kernel/, cli/, postal/, bin/, ui/, vscode-extension/src, hooks/ and the install scripts, each with its road from the table below. Run from
the repository root: python3 scripts/network-inventory.py [root]. Exit 1 when a site has no road, so a new road is a loud line, never a
silent absence. Standard library only. A program the kernel starts (ssh, git, gh, npm, the session CLIs, the operator's helper, a watch
predicate) may open connections this scan cannot see: such sites are listed by program, and RUNTIME-SUPPLIED marks an argv the code does not spell out."""
import ast, os, re, sys
ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
NET = {"urllib.request.urlopen": "urlopen", "urllib.request.Request": "Request", "http.client.HTTPConnection": "HTTPConnection",
       "http.client.HTTPSConnection": "HTTPSConnection", "socket.create_connection": "create_connection", "ssl.wrap_socket": "wrap_socket",
       "smtplib.SMTP": "smtplib", "ClaudeSDKClient": "sdk-client", "claude_agent_sdk.ClaudeSDKClient": "sdk-client",
       "sdk.ClaudeSDKClient": "sdk-client", "CodexClient": "sdk-client", "openai_codex.client.CodexClient": "sdk-client", "SubprocessCLITransport": "sdk-transport"}
SUB = {"subprocess." + n: n for n in ("run", "Popen", "check_output", "check_call", "call", "getoutput", "getstatusoutput")}
SUB.update({"os." + n: "os." + n for n in ("system", "popen", "execv", "execve", "execvp", "execvpe", "execl", "execlp", "spawnv", "spawnvp",
            "spawnl", "spawnlp", "posix_spawn", "posix_spawnp")})
SUB.update({"asyncio.create_subprocess_exec": "create_subprocess_exec", "asyncio.create_subprocess_shell": "create_subprocess_shell", "webbrowser.open": "webbrowser.open"})
LOCAL_TOOLS = {"ps", "scutil", "systemctl", "journalctl", "systemd-run", "osascript", "notify-send", "xdg-open", "open", "zenity", "node", "perl", "sh"}
LOCAL_GIT = {"rev-parse", "status", "log", "show", "diff", "symbolic-ref", "merge-base", "rev-list", "checkout", "merge", "remote", "ls-files", "describe", "tag"}
# The table: "file:function" (a Python site) or "file:tool" (a shell or JS line) -> road. Every function with a site that reaches
# another machine is named here, and so is every loopback or local-program site the default rules (LOCAL_TOOLS, LOCAL_GIT, a
# python interpreter as argv[0]) cannot place. A site with no row fails the run.
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
   "vscode-extension/src/extension.ts:WebSocket", "ui/webview/federation.ts:WebSocket", "ui/webview:fetch")
_t("local-program", K + "_port_open", K + "_primary_addr", K + "_rebuild_dist", K + "_open_folder", K + "_open_file", K + "_run_dialog", K + "_system_notify",
   K + "_run_bounded", K + "_git_out", S + "interpreter_tag", S + "cli_scope_supported", S + "proc_start", S + "SdkBackend._session_cli_pid", S + "SdkBackend._end_cli_tree",
   S + "SdkBackend._stop_leftover_scopes", S + "SdkBackend._boot_reconcile", S + "SdkBackend._oom_killed_scope", S + "SdkBackend._scope_journal",
   S + "SdkBackend._host_orphan_recover", J + "_serve_fault", K + "main", "vscode-extension/src/extension.ts:execFile", "ui/romp-timeline-view.js:execFile")
_t("browser-figures", "ui/webview/figure-gate.ts:figureHosts", "ui/webview/preview.ts:Image")
_t("install-bootstrap", "bootstrap.sh:curl", "bootstrap.sh:git clone", "bootstrap.sh:git fetch", "bootstrap.sh:git pull")
_t("install-sdk-setup", "bin/romp-sdk-setup:curl", "bin/romp-sdk-setup:wget", "bin/romp-sdk-setup:pip install")
_t("install-ext", "vscode-extension/install.sh:npm install", "vscode-extension/src/extension.ts:install.sh")
_t("install-codex-setup", "bin/romp-codex-setup:pip install", "kernel/codex_runtime.py:install_runtime")
LOCAL_ROADS = {"local-bus", "local-manager", "local-kernel", "local-program", "local-git"}
sites, bad = [], []
def emit(f, line, prim, head, fn, road):
    sites.append((f, line, prim, head, fn, road or "UNCLASSIFIED")); bad.extend([] if road else ["%s:%d" % (f, line)])

class Scan(ast.NodeVisitor):
    def __init__(self, rel): self.rel, self.stack, self.alias, self.consts, self.binds = rel, [], {}, {}, []
    def visit_Import(self, n): self.alias.update({a.asname or a.name: a.name for a in n.names})
    def visit_ImportFrom(self, n): self.alias.update({a.asname or a.name: (n.module or "") + "." + a.name for a in n.names})
    def dotted(self, n):
        if isinstance(n, ast.Name): return self.alias.get(n.id, n.id)
        if isinstance(n, ast.Attribute):
            b = self.dotted(n.value); return b + "." + n.attr if b else None
    def prim(self, n):
        if isinstance(n, ast.BoolOp): return next((p for p in map(self.prim, n.values) if p), None)
        d = self.dotted(n); return SUB.get(d) or NET.get(d)
    def visit_Assign(self, n):
        if len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
            if not self.stack: self.consts[n.targets[0].id] = n.value
            elif self.prim(n.value): self.binds[-1][n.targets[0].id] = self.prim(n.value)
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
        """(argv[0] as text, git subcommand or '') for a command call: a literal, a module constant, or RUNTIME-SUPPLIED(expr)."""
        kw = {k.arg: k.value for k in c.keywords}; a = c.args[0] if c.args else kw.get("args"); sub = ""
        while isinstance(a, ast.BinOp): a = a.left
        if isinstance(a, (ast.List, ast.Tuple)) and a.elts:
            lits = [e.value for e in a.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)]
            if lits and lits[0] == "git": sub = next((v for v in lits[1:] if not v.startswith("-")), "")
            a = a.elts[0]
        if isinstance(a, ast.Name) and a.id in self.consts: a = self.consts[a.id]
        if isinstance(a, ast.Constant) and isinstance(a.value, str): return a.value, sub
        if isinstance(a, ast.Call) and getattr(a.func, "attr", "") == "get" and a.args and isinstance(a.args[0], ast.Constant):
            return "%s or %s" % (a.args[0].value, ast.unparse(a.args[1]) if len(a.args) > 1 else "''"), sub   # SSH_BIN = os.environ.get(..., "ssh")
        return "RUNTIME-SUPPLIED(%s)" % (ast.unparse(a)[:48] if a is not None else ""), sub
    def visit_Call(self, n):
        d = self.dotted(n.func); p = SUB.get(d) or NET.get(d)
        if not p and isinstance(n.func, ast.Name) and self.binds and n.func.id in self.binds[-1]: p = self.binds[-1][n.func.id] + " via " + n.func.id
        if not p and getattr(n.func, "attr", "") in ("connect", "connect_ex") and n.args and isinstance(n.args[0], ast.Tuple): p = "socket." + n.func.attr
        if p:
            fn = ".".join(self.stack) or "<module>"; road = T.get(self.rel + ":" + fn); head, sub = "", ""
            if p.split(" ")[0] in SUB.values():
                head, sub = self.argv(n)
                if any(k.arg == "shell" and getattr(k.value, "value", None) is True for k in n.keywords): head += " SHELL"
                if road is None and ((head == "git" and sub in LOCAL_GIT) or head in LOCAL_TOOLS or head.startswith("RUNTIME-SUPPLIED(sys.executable")):
                    road = "local-git" if head == "git" else "local-program"
            elif n.args: head = ast.unparse(n.args[0])[:60]
            emit(self.rel, n.lineno, p, (head + " " + sub).strip(), fn, road)
        self.generic_visit(n)

def py_files():
    for d in ("kernel", "cli", "postal", "bin"):
        for n in sorted(os.listdir(os.path.join(ROOT, d))):
            f = os.path.join(ROOT, d, n)
            if os.path.islink(f) or not os.path.isfile(f) or n.endswith((".md", ".pyc")): continue
            with open(f, "rb") as fh: first = fh.readline()
            if n.endswith(".py") or b"python" in first: yield f, "py"
            elif b"node" in first or b"sh" in first: yield f, "js" if b"node" in first else "sh"
SH = [("curl", r"\bcurl\s"), ("wget", r"\bwget\s"), ("git clone", r"\bgit (?:-C \S+ )?clone\b"), ("git fetch", r"\bgit (?:-C \S+ )?fetch\b"),
      ("git pull", r"\bgit (?:-C \S+ )?pull\b"), ("git push", r"\bgit (?:-C \S+ )?push\b"), ("git ls-remote", r"\bgit (?:-C \S+ )?ls-remote\b"),
      ("npm install", r"\bnpm (?:install|ci)\b"), ("pip install", r"\bpip\S*\"? (?:--isolated )?install\b"), ("gh", r"\bgh (?:pr|repo|api)\b"), ("ssh", r"\bssh\s+-")]
JS = [("fetch", r"\bfetch\("), ("WebSocket", r"new WebSocket\("), ("EventSource", r"new EventSource\("), ("Image", r"new Image\("), ("http.get", r"\bhttps?\.get\("),
      ("http.request", r"\bhttps?\.request\("), ("execFile", r"\bexecFile\("), ("spawn", r"\bspawn\("), ("figureHosts", r"loadSettings\(\)\.figureHosts")]
def line_scan(rel, tools, comment):
    for i, ln in enumerate(open(os.path.join(ROOT, rel), encoding="utf-8", errors="replace"), 1):
        s = ln.strip()
        if s.startswith(comment) or s.startswith(("echo ", "print(")): continue   # a printed remedy is not a request
        for tool, rx in tools:
            if re.search(rx, ln):
                road = T.get("%s:%s" % (rel, tool)) or (T.get("ui/webview:fetch") if rel.startswith("ui/") and tool == "fetch" else None)
                if tool == "execFile" and 'execFile("bash"' in ln: tool, road = "install.sh", T.get(rel + ":install.sh")
                emit(rel, i, tool, s[:70], "-", road)
for f, kind in py_files():
    rel = os.path.relpath(f, ROOT)
    Scan(rel).visit(ast.parse(open(f, encoding="utf-8").read())) if kind == "py" else line_scan(rel, JS if kind == "js" else SH, ("//",) if kind == "js" else ("#",))
for rel in ("bootstrap.sh", "install.sh", "vscode-extension/install.sh") + tuple("hooks/" + n for n in sorted(os.listdir(os.path.join(ROOT, "hooks"))) if n.endswith(".sh")):
    line_scan(rel, SH, ("#",))
for ln in open(os.path.join(ROOT, "bootstrap.sh")):   # the documented one-liner: the user's own curl of this script is a road too
    if ln.startswith("#") and "curl" in ln and "bootstrap.sh | bash" in ln: emit("bootstrap.sh", 3, "curl (the documented one-liner)", ln.strip("# \n")[:70], "-", T["bootstrap.sh:curl"])
for d in ("ui/webview", "ui", "vscode-extension/src"):
    for n in sorted(os.listdir(os.path.join(ROOT, d))):
        if n.endswith((".ts", ".js")) and not n.endswith(".test.ts") and os.path.isfile(os.path.join(ROOT, d, n)): line_scan(d + "/" + n, JS, ("//", "*", "/*"))
for f, line, prim, head, fn, road in sorted(sites): print("%s:%d  %s  %s  in %s  -> %s" % (f, line, prim, head, fn, road))
roads, local = {r for *_, r in sites}, sum(1 for *_, r in sites if r in LOCAL_ROADS)
print("--- %d sites, %d roads (%d of them local), %d local sites set aside, %d unclassified" % (len(sites), len(roads), len(roads & LOCAL_ROADS), local, len(bad)))
if bad: print("UNCLASSIFIED: " + " ".join(bad)); sys.exit(1)

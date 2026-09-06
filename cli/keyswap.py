#!/usr/bin/env python3
"""romp-keyswap — report which API key the sessions bill, switch it, and reconnect them after a rotation.

Two key sources, one command. Which one a box uses is decided by ONE non-secret setting, read the way
the kernel reads it (this shell's environment first, then the same line in the manager's env file):

  * FILE mode (ROMP_CREDENTIAL_COMMAND unset) is upstream's: the kernel reads the `ANTHROPIC_API_KEY=`
    line of `~/.config/romp/service.env` at every launch. Upstream's `romp keyswap <name>` rewrites
    that line from a sibling file (`service.env.<name>`); THIS FORK REFUSES THAT (the user 2026-09-05):
    the fork does not write API keys to files, so in file mode the named swap exits 2 and touches
    nothing. The bare report and the cycle are upstream's, unchanged.
  * COMMAND mode (ROMP_CREDENTIAL_COMMAND set; kernel/envsource.py): the kernel runs the command,
    with the selector file's one token as `$1`, and injects the `NAME=VALUE` set it prints into every
    launch. Here `romp keyswap <name>` writes that token (a name, never a key) — after checking it is
    declared in ROMP_CREDENTIAL_NAMES — re-runs the command in this shell, confirms the fingerprint
    moved, and asks the kernel to re-run too. Nothing here ever holds a key: the command's output is
    hashed inside envsource and only the fingerprint comes back.

Common to both modes:

  * the bare command reports the credential the kernel holds, by fingerprint, and whether it matches
    what this shell reads (a `/keycycle` read that names no session) — MISMATCH when they differ;
  * `--refresh` makes the kernel re-run the command now (a plain re-read in file mode) and prints the
    fingerprint before and after;
  * `--cycle <names>` / `--cycle-all` reconnect quiet running sessions so each resumes its own
    conversation, history intact, in a NEW CLI process — which is how a rotated credential reaches a
    session: a process keeps what it started with. In command mode the kernel re-runs the command
    first, then reconnects only the sessions whose launch fingerprint differs; a second run reads
    "current" for the ones already moved. The manager never restarts, so no session loses an open
    turn; a session with a turn, subagents or background tasks in flight is skipped and named.

No key value is ever printed, logged or passed over the wire. The only rendered form is the first
12 hex of its sha256 ("sha256:1a2b3c…"); a failure reason carries counts and exit codes only.

Usage:
    romp keyswap                            # which credential the kernel holds, and whether this shell agrees
    romp keyswap <name>                     # command mode: select a declared credential; file mode: refused
    romp keyswap --refresh                  # make the kernel re-run its command now
    romp keyswap --cycle-all                # after a rotation: reconnect every quiet session
    romp keyswap --cycle web,api            # …or only these
"""
import json
import os
import sys
import urllib.error
import urllib.request
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The SAME modules the kernel reads the credential with, not a second copy of the rules: writer and
# reader then cannot disagree about which file holds the key, which line wins, how it is parsed, how
# the mode is decided, where the selector lives or how a fingerprint is taken.
ks = SourceFileLoader("romp_keysource", str(ROOT / "kernel" / "keysource.py")).load_module()
es = SourceFileLoader("romp_envsource", str(ROOT / "kernel" / "envsource.py")).load_module()

KPORTS = ["http://127.0.0.1:29855", "http://127.0.0.1:7878", "http://127.0.0.1:7432"]

# The column every hint line stays within, indent included. One exception, deliberate: a path is never
# broken, so a service.env path too long for its sentence goes whole on a line of its own (_other_file).
WIDTH = 100

# `romp keyswap <name>` is refused in FILE mode on this fork (the user 2026-09-05). The exit code is 2,
# the class the other usage refusals use; the file is never opened for writing. One string, so a
# reword is a deliberate edit and the bats/python tests pin the same text the operator reads.
REFUSAL = (
    "romp keyswap: refused — this fork does not write API keys to files, so the named swap is disabled.\n"
    "             Keys reach the sessions through Claude Code's apiKeyHelper or through the manager's\n"
    "             environment; nothing here rewrites service.env, so there is nothing for a swap to do.\n"
    "             After rotating the manager's key, run\n"
    "                 romp keyswap --cycle-all\n"
    "             so quiet key-billed sessions reconnect and pick it up. In this file mode that cycle\n"
    "             skips sessions billed through the apiKeyHelper (they read as the login): a rotated\n"
    "             helper key reaches them through  romp refresh --quiet  (every process is new), or\n"
    "             through --cycle-all in command mode (set ROMP_CREDENTIAL_COMMAND; docs/reference.md).\n")


def _kernel_urls():
    """Where the local kernel may answer. ROMP_KERNEL_PORT / ROMP_SERVE_PORT when set — the port
    bin/romp and the installer resolve — and ONLY that one: a renumbered second-OS-user instance must
    never hand its serve token to whatever answers on the primary user's default port (review find,
    2026-09-04). Unset, the defaults `romp version` and `romp update` probe."""
    for var in ("ROMP_KERNEL_PORT", "ROMP_SERVE_PORT"):
        p = (os.environ.get(var) or "").strip()
        if not p:
            continue
        if not (p.isdigit() and 0 < int(p) < 65536):
            # an unusable override is refused, never silently replaced by the default ports — that
            # replacement is exactly the token-to-the-wrong-kernel path this function exists to close
            raise ValueError("%s=%r is not a port" % (var, p))
        return ["http://127.0.0.1:%s" % p]
    return list(KPORTS)


def _token():
    """The serve token — required on every kernel request, loopback included (Jupyter's model).
    Same resolution romp-update uses: env override, else the 0600 state file."""
    t = (os.environ.get("ROMP_SERVE_TOKEN") or "").strip()
    if t:
        return t
    try:
        root = Path(os.environ.get("ROMP_STATE_DIR")
                    or Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local/state")) / "romp")
        return (root / "serve-token").read_text().strip()
    except OSError:
        return ""


def _kernel():
    """The base URL of the running local kernel, or None."""
    try:
        urls = _kernel_urls()
    except ValueError:
        return None                                  # the callers report it (they check _kernel_urls first)
    for u in urls:
        try:
            with urllib.request.urlopen(u + "/version", timeout=1.5) as r:   # /version is auth-exempt
                if r.status == 200:
                    return u
        except Exception:
            continue
    return None


def _post(u, path, body):
    # the kernel may run its credential command (and the apiKeyHelper) before answering, each bounded
    # by ROMP_CREDENTIAL_TIMEOUT_S — so the wait here scales with it rather than cutting a slow but
    # working command off: 10 s plus twice the deadline (30 s in file mode, where the default holds)
    req = urllib.request.Request(u + path, data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json",
                                         "X-Romp-Token": _token()}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10 + 2 * es.timeout_s()) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode() or "{}")
        except Exception:
            return {"ok": False, "error": "HTTP %s" % e.code}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _fp(key):
    """A key as the only thing that may be shown of it."""
    f = ks.fingerprint(key)
    return ("sha256:" + f) if f else "(none)"


def _sha(fp):
    """A fingerprint already taken, rendered; "(none)" for an empty one."""
    return ("sha256:" + fp) if fp else "(none)"


def _ask(out, refresh=False):
    """The /keycycle read that names no session — the kernel's fingerprint and key-source facts, with
    `refresh` asking it to re-run its command first. Returns (body, rc): body None when nothing could
    be asked, rc the exit code that outcome deserves (0 for "no kernel is running" — the caller says
    what that means for it; 1 for an unusable port override, a kernel that predates the route, or a
    refused ask, each already said here)."""
    try:
        _kernel_urls()
    except ValueError as e:
        out("kernel      NOT ASKED — %s; fix the variable and re-run" % e)
        return None, 1
    u = _kernel()
    if not u:
        return None, 0
    body = _post(u, "/keycycle", {"sessions": [], "refresh": True} if refresh else {"sessions": []})
    if body.get("error") == "HTTP 404":
        out("kernel      predates `romp keyswap` (no /keycycle route): it is still on the key it booted")
        out("            with. Take the patch once with `romp refresh`; every swap after that is restart-free.")
        return None, 1
    if not body.get("ok"):
        out("kernel      could not be asked — %s" % (body.get("error") or body.get("detail") or "unknown"))
        return None, 1
    return body, 0


# ---------------------------------------------------------------------------
# FILE mode — upstream's report and cycle, unchanged but for the shared row printer and --refresh.
# ---------------------------------------------------------------------------

def _candidates(path, out):
    """List the sibling `service.env.<name>` files, each by fingerprint only — so `romp keyswap`
    with no argument answers both "which key is live" and "what can I swap to"."""
    d = os.path.dirname(path) or "."
    base = os.path.basename(path) + "."
    try:
        names = sorted(n[len(base):] for n in os.listdir(d) if n.startswith(base) and not n.endswith("~"))
    except OSError:
        names = []
    live = ks.read_key(path)
    if not names:
        # the fork writes no key files, so an empty list is the expected state — upstream's line here
        # told the operator to create one file per key
        out("candidates  none (this fork does not write API keys to files; the named swap is disabled)")
        return
    out("candidates")
    for n in names:
        k = ks.read_key(ks.sibling_path(n, path))
        mark = "  <- live" if (k and k == live) else ""
        out("  %-14s %s%s" % (n, _fp(k) if k else "(no %s line)" % ks.KEY_VAR, mark))


def _kernel_check(path, out, refresh=False):
    """Compare what the KERNEL reads with what the FILE says — the check the operator procedure used
    to ask for by eye (review find, 2026-09-04). The two can differ: the kernel and this shell resolve
    ROMP_SERVICE_ENV_FILE from their own environments, so they can read different service.env files
    (_other_file renders that cause, shared with the two mode MISMATCHes: the places the kernel's
    environment comes from and the remedy per place), the file is unreadable to the kernel, the kernel
    still holds its startup key because the file has no key line, or the kernel predates this feature.
    Reads the fingerprint through /keycycle with no sessions named — a read, nothing cycles. Returns 0
    when they agree (or no kernel is up to ask), 1 when they do not — or when the port override is
    unusable, which is a misconfiguration to fix, not "no kernel"."""
    body, rc = _ask(out, refresh)
    if body is None:
        if rc == 0:
            out("kernel      not running — sessions read the file when it is")
        return rc
    if (body.get("keySource") or "file") != "file":
        return _mode_mismatch(body, out)
    return _compare(body.get("keyFp") or "", path, out, body.get("refreshed"))


def _compare(kfp, path, out, refreshed=None):
    """Print the kernel's fingerprint and, when it is not the file's, say so and why it may be. The
    other-file cause is the one explanation the three MISMATCH hints share (_other_file): a kernel
    whose ROMP_SERVICE_ENV_FILE comes from a drop-in, a profile or the `romp up` shell is pointed at
    that place, one whose unit or plist lacks the line this shell's environment carries is pointed at
    the install that writes it, and the restart-and-reload block (_restart_block) follows once."""
    note = _refreshed_note(refreshed, kfp, "re-read")
    out("kernel      reads %s%s" % (_sha(kfp), (" (%s)" % note) if note else ""))
    if kfp == ks.fingerprint(ks.read_key(path)):
        return 0
    out("MISMATCH    the kernel is not reading this file's key. Usual causes: the file is unreadable to the")
    out("            kernel, the file has no %s line and the kernel still holds its startup" % ks.KEY_VAR)
    out("            key, or the kernel reads another service.env:")
    pad = " " * 12
    for line in _other_file(path, len(pad), _path_alias()) + _restart_block():
        out(pad + line)
    return 1


def _refreshed_note(refreshed, now_fp, verb="re-run"):
    """The clause a --refresh adds to the kernel line: "re-run now: was sha256:…" when the kernel's
    fingerprint moved, "re-run now: unchanged" when it did not, "" when no refresh was asked for.
    `verb` is "re-read" in file mode, where the refresh is a re-read of the env file."""
    if not isinstance(refreshed, dict):
        return ""
    if refreshed.get("error"):
        return "the refresh failed — %s" % refreshed["error"]
    frm = refreshed.get("from") or ""
    return "%s now: was %s" % (verb, _sha(frm)) if frm != now_fp else "%s now: unchanged" % verb


def _cycle(sessions, all_, out, path=None, refresh=False):
    """Reconnect the named sessions through the kernel, and report what it did per session. The
    kernel's fingerprint is READ and compared with the file's FIRST: cycling a session while the kernel
    reads another file would re-present the kernel's unchanged key, so a mismatch refuses to cycle.
    The failure lines for an unusable port and a refused read are upstream's, byte for byte; the
    no-kernel and no-route blocks keep the fork's main's second and third lines (upstream's say the
    file is already swapped, which is never true here). The fork adds the refresh body and the mode
    check on the success path."""
    try:
        _kernel_urls()
    except ValueError as e:
        out("cycle       NOT DONE — %s; fix the variable and re-run" % e)
        return 1
    u = _kernel()
    if not u:
        out("cycle       NOT DONE — no running kernel found (is romp on? `romp status`).")
        out("            Nothing was cycled. A session's next launch or revive runs a new process")
        out("            anyway; re-run `romp keyswap --cycle…` once romp is up for the running ones.")
        return 1
    body = _post(u, "/keycycle", {"sessions": [], "refresh": True} if refresh else {"sessions": []})   # the read
    if body.get("error") == "HTTP 404":
        # The one restart this feature genuinely needs: a kernel started before this code has no
        # /keycycle route AND no live key read, so it is still on the key it booted with.
        out("cycle       NOT DONE — the running kernel predates `romp keyswap` (no /keycycle route).")
        out("            Take the patch once with `romp refresh` — that restart also gives every")
        out("            session a new process — and every cycle after that is restart-free.")
        return 1
    if not body.get("ok"):
        out("cycle       FAILED — %s" % (body.get("error") or body.get("detail") or "unknown"))
        return 1
    if (body.get("keySource") or "file") != "file":
        _mode_mismatch(body, out)
        out("cycle       NOT DONE — fix the mismatch above first, then cycle.")
        return 1
    if _compare(body.get("keyFp") or "", path or ks.service_env_path(), out, body.get("refreshed")):
        out("cycle       NOT DONE — the kernel is not on this file's key, so a reconnect would re-present")
        out("            the key it already has. Fix the mismatch above first, then cycle.")
        return 1
    return _do_cycle(u, sessions, all_, out, file_mode=True)


def _not_done_unasked(rc, out):
    """The cycle could not even read the kernel: no kernel running (rc 0 from _ask — the report stands,
    the cycle does not), or an ask _ask already reported (an unusable port, a 404, a refusal)."""
    if rc == 0:
        out("cycle       NOT DONE — no running kernel found (is romp on? `romp status`).")
        out("            Nothing was cycled. A session's next launch or revive runs a new process")
        out("            anyway; re-run `romp keyswap --cycle…` once romp is up for the running ones.")
    else:
        out("cycle       NOT DONE — see above. Nothing was cycled.")


def _do_cycle(u, sessions, all_, out, file_mode=False):
    """The cycle itself, once the read agreed: one POST naming the sessions (or all), then the rows. In
    file mode a row skipped as the login may be a session billed through the apiKeyHelper (the kernel
    hands it no key, so it reads as the login there): one hint line says where such sessions cycle."""
    body = _post(u, "/keycycle", {"all": True} if all_ else {"sessions": sessions})
    if not body.get("ok"):
        out("cycle       FAILED — %s" % (body.get("error") or body.get("detail") or "unknown"))
        return 1
    rows = body.get("rows") or []
    if not rows:
        out("cycle       no sessions matched")
        return 0
    for r in rows:
        status = str(r.get("status") or "")
        frm = str(r.get("from") or "")
        tail = " (from sha256:%s)" % frm if (status == "cycling" and frm) else ""
        out("  %-14s %s%s" % (str(r.get("session"))[:14], _explain(status), tail))
    # The re-run hint speaks only of the rows that were skipped for in-flight work, and names them: a
    # session already moved reads "current" on the re-run, so naming only the skipped ones is exact.
    working = [str(r.get("session")) for r in rows if str(r.get("status")) == "working"]
    if working:
        out("            re-run --cycle %s once quiet; sessions already on this key read \"current\"" % ",".join(working))
    if file_mode and any(str(r.get("status")) == "login" for r in rows):
        out("            a session billed through the apiKeyHelper reads as the login here and is skipped: such")
        out("            sessions cycle in command mode (set ROMP_CREDENTIAL_COMMAND); romp refresh --quiet reaches them too")
    return 0


def _explain(status):
    return {
        "cycling": "reconnecting now — history kept",
        "current": "already on this key — nothing to do",
        "login":   "skipped: bills the machine login, not the key",
        "dormant": "not running — its next launch reads the new key",
        "working": "skipped: a turn, subagents or background tasks are in flight (a reconnect would kill "
                   "the work) — cycle it again when it is quiet; its next launch reads the new key anyway. "
                   "A standing background task (a dev server, a monitor) never goes quiet: end it, or "
                   "revive the session",
        "unknown": "no such session",
    }.get(status, status)


def _path_alias():
    """True when this shell's service.env path comes from ROMP_SERVICE_ENV, the alias kernel/keysource.py
    accepts after ROMP_SERVICE_ENV_FILE (service_env_path). The other-file hint then says so: its
    "unset the variable in this shell" otherwise names a variable such a shell never set, and its
    "install from this shell" remedy holds only because bin/romp-service resolves the alias the same way
    and writes the primary name into the unit or the plist (it read the primary alone, so the install
    wrote no override line and the kernel kept the default; review find, 2026-09-06)."""
    primary = (os.environ.get("ROMP_SERVICE_ENV_FILE") or "").strip()
    return not primary and bool((os.environ.get("ROMP_SERVICE_ENV") or "").strip())


def _other_file(path, indent=0, alias=False):
    """The one explanation the three MISMATCH hints share for a kernel that reads ANOTHER service.env
    (the file-mode fingerprint MISMATCH, the command-mode MISMATCH's other-file cause, and the file-mode
    MISMATCH under a shell whose file carries the line). The kernel resolves its path from
    ROMP_SERVICE_ENV_FILE as ITS environment sets it (kernel/keysource.py, service_env_path) and this
    shell from its own, so the two can read different files in either direction: the kernel's set to a
    file this shell's is not, or this shell's set where the kernel's is not (the install that predates
    the installer's line). The kernel's environment comes from the unit's Environment= and its drop-ins
    on Linux or the plist's EnvironmentVariables on macOS (bin/romp-service writes the variable there
    when the installing shell's path is not the default: _service_env_override), the profile a
    shell-wrapped ExecStart sources, or the shell that ran `romp up`. The lines name the variable, this
    shell's path and those places, under either name the kernel's resolver reads (ROMP_SERVICE_ENV_FILE
    or its alias ROMP_SERVICE_ENV: a drop-in, a profile or the `romp up` shell can carry either), then
    the remedy for each direction: if found, run this command with the same value, or change it there
    and restart the manager (`romp-service install` from a shell with the wanted path rewrites the
    unit's or the plist's line; a `romp up` shell starts again with the path); if not found, the kernel
    reads the default path, so unset the variable in this shell or install from this shell. The restart
    itself, the reload a unit, drop-in or plist line takes first and the install's cost are
    _restart_block's, which every hint renders once after its causes. Never
    a value. Unindented; the caller's lead-in ends with "another service.env:", and `indent` is the
    width of the pad the caller prints before each line. The path is the one part not written here,
    and it can be any length: when it would carry its sentence past WIDTH columns, pad included, the
    sentence stops at "reads" and the path follows whole on a line of its own, four columns deeper, so
    a path is never broken and every prose line stays within WIDTH (a long TMPDIR made the line 124
    columns in the tests, 2026-09-06). The words are the same either way. `alias` (_path_alias) adds
    two lines after the path under a shell whose path comes from the alias ROMP_SERVICE_ENV: which
    variable this shell set, and that the installer reads it too and writes the primary name."""
    reads = "in their own environment; this shell reads"
    inline = "%s %s." % (reads, path)
    if indent + len(inline) <= WIDTH:
        where = (inline,)
    else:
        where = (reads, "    %s." % path)
    if alias:
        where += (
            "This shell set it under the alias ROMP_SERVICE_ENV, which the installer reads too; the",
            "line it writes into the unit or the plist is ROMP_SERVICE_ENV_FILE.",
        )
    return (
        "the kernel and this shell each resolve the service.env path from ROMP_SERVICE_ENV_FILE",
    ) + where + (
        "Look for it where the kernel's environment comes from, under ROMP_SERVICE_ENV_FILE or",
        "its alias ROMP_SERVICE_ENV: the unit's Environment= and its drop-ins (Linux) or the",
        "plist's EnvironmentVariables (macOS), where `romp-service install` writes it when the",
        "installing shell's path is not the default (and rewrites it from a shell with the",
        "wanted path); the profile a shell-wrapped ExecStart sources; or the shell that ran",
        "`romp up` (start it again with the path). If found, run this command with the same",
        "value, or change it there and restart the manager (below). If not found, the kernel",
        "reads the default path: unset the variable in this shell, or point the kernel at this",
        "file with `romp-service install` from this shell.",
    )


def _restart_block():
    """The restart-and-reload mechanics every MISMATCH hint that names a manager restart renders ONCE,
    after its causes, so no hint gives them twice. The manager restart is `systemctl --user restart
    romp-manager` on Linux and `launchctl kickstart -k` on the launchd agent on macOS. A line in the
    unit or a drop-in is re-applied by a restart until `systemctl --user daemon-reload`, so that comes
    first. `launchctl kickstart -k` restarts the job as launchd loaded it and does not re-read the
    plist, so a plist edit takes `romp-service install` instead, and the hint names the install and
    never the bare bootout/bootstrap pair: bootout only starts the old job's teardown, a manager
    draining live sessions takes seconds to exit, and a bootstrap issued while it drains is refused
    (Input/output error) with the old job gone and no new one accepted, so the installer polls
    `launchctl print` until the job has left launchd before it bootstraps (bin/romp-service, install;
    twice the blind pair left no agent loaded, 2026-07-20). On Linux the install rewrites the unit and
    reloads systemd (daemon-reload, enable --now) and leaves a running manager as it is, so the restart
    follows. The cost the install has on BOTH platforms is stated because it is silent: write_unit and
    write_plist overwrite the file wholesale, so a line added to the unit or the plist by hand
    (ROMP_CREDENTIAL_COMMAND, say) is gone after the install and the next kernel pins file mode; a
    drop-in is not touched, so a line of one's own belongs in service.env or a drop-in (review find,
    2026-09-06). Unindented, like _other_file."""
    return (
        "The manager restart is `systemctl --user restart romp-manager` (Linux) or `launchctl",
        "kickstart -k gui/$(id -u)/com.romp.manager` (macOS); a unit or drop-in edit takes",
        "`systemctl --user daemon-reload` first. A plist edit takes `romp-service install`",
        "instead: the kickstart does not re-read the plist; the install rewrites it and reloads",
        "the job, waiting for the old job to leave launchd before it bootstraps the new one (a",
        "bootstrap issued sooner is refused, Input/output error, and no agent is left loaded).",
        "On Linux the install rewrites the unit and reloads systemd but restarts no running",
        "manager, so restart after it. Either rewrite drops a line added to the unit or the",
        "plist by hand; drop-ins survive, so put your own lines in service.env or a drop-in.",
    )


def _mode_mismatch(body, out, path=None):
    """The kernel and this shell resolve DIFFERENT modes: ROMP_CREDENTIAL_COMMAND is set for one and not
    the other. The caller established that; the kernel's mode is read from the answer (`keySource`) and
    this shell's is the other one, so nothing else is passed in. `path` is the service.env path the hints
    name for this shell: every caller in the command leaves it None, and it is resolved the way the
    kernel resolves it (ks.service_env_path); the tests pass one so the hints render around a path of a
    chosen length while the mode is still read from the temp file. The kernel decides its mode ONCE, when
    it starts (envsource.pin_mode), from its environment and then service.env; this shell reads its own
    environment and then service.env now. Under the installed service the kernel's environment is the
    manager's, which holds every service.env line as of the MANAGER's start (systemd's
    EnvironmentFile=; the macOS launcher's parse) plus the unit's own Environment= lines, and every
    kernel inherits it. So which restart makes the two agree depends on where the variable is: a line
    ADDED to service.env reaches the next kernel (`romp refresh`; the kernel reads the file itself); a
    value in this shell's environment alone reaches no kernel.

    A kernel in command mode under a shell that reads no line says only what is known (the kernel
    pinned the mode at its start) and lists the places the line can still be, with the remedy for
    each: the /keycycle answer cannot tell the manager's environment from a service.env line removed
    since the kernel started or from a `romp up` shell that exported it. The manager's environment is
    two places with two remedies: a service.env line the manager loaded is gone once the file is edited
    and the manager restarted (the restart re-reads the file), while a line in the unit's
    Environment=, a drop-in, or the profile a shell-wrapped ExecStart sources (Linux), or in the
    plist's EnvironmentVariables (macOS: the manager's environment there is the plist's pairs plus
    service.env as bin/romp-node-launch parses it at each start), is RE-APPLIED by a restart, so it is
    removed where it is first, the definition reloaded, and the manager restarted after. One more
    place is another file: the kernel resolves its service.env path from ROMP_SERVICE_ENV_FILE
    wherever its environment sets it, so the kernel and this shell can read different service.env
    files, and the answer carries no path; _other_file renders that cause, shared with the file-mode
    fingerprint MISMATCH, with this shell's path, the places per platform and the remedy per place.
    The restart commands, the reload a unit, drop-in or plist line takes first and the install's cost
    are _restart_block's, rendered once after the places, so the unit-or-plist bullet and the
    other-file bullet share one copy. The same other-file cause is named under a file-mode kernel when
    the file this shell reads carries the line: `romp refresh` reaches only the file the kernel reads.
    Under a shell whose environment alone carries the line the hint sends the line to service.env or
    a drop-in and says why not the unit or the plist: the next install rewrites both. Names the
    variable, the places and this shell's file path; never a value."""
    kmode = body.get("keySource") or "file"
    out("kernel      reads %s in %s mode" % (_sha(body.get("keyFp") or ""), kmode.upper()))
    path = path or ks.service_env_path()
    if kmode == "command":
        out("MISMATCH    the kernel is in command mode and this shell is not: the kernel pinned command mode")
        out("            when it started; this shell reads no ROMP_CREDENTIAL_COMMAND now. The kernel got the")
        out("            line from one of:")
        out("            - service.env as the manager loaded it at its start, which every kernel inherits: the")
        out("              line is gone from the file this shell reads, so restart the manager (the restart")
        out("              re-reads the file); `romp refresh` alone keeps the mode")
        out("            - the unit's Environment=, a drop-in, or the profile a shell-wrapped ExecStart sources")
        out("              (Linux), or the plist's EnvironmentVariables (macOS): a manager restart re-applies")
        out("              these, so remove the line there first, reload the definition, then restart (below)")
        out("            - another service.env:")
        pad = " " * 14
        for line in _other_file(path, len(pad), _path_alias()):
            out(pad + line)
        out("            - service.env, edited since the kernel read it at its start: `romp refresh`")
        out("            - the shell that ran `romp up`, which exported it: stop that `romp up`; start it again")
        out("              from a shell without the line")
        for line in _restart_block():
            out("            " + line)
        out("            To stay in command mode, put the line back in service.env instead.")
    elif es.command({}):
        # the file carries the line (an empty environ reads the file alone): the kernel reads the file
        # at its start, so the kernel restart is enough
        out("MISMATCH    the kernel is in file mode and this shell is not: ROMP_CREDENTIAL_COMMAND is set in")
        out("            service.env and was not when the kernel started. A running kernel keeps the mode it")
        out("            started in: `romp refresh` restarts the kernels into command mode (a kernel reads")
        out("            service.env at its start, so a line added there needs no manager restart). Until then")
        out("            the kernel injects no set.")
        out("            If the kernel is still in file mode after `romp refresh`, it reads another service.env:")
        pad = " " * 12
        for line in _other_file(path, len(pad), _path_alias()) + _restart_block():
            out(pad + line)
    else:
        out("MISMATCH    the kernel is in file mode and this shell is not: ROMP_CREDENTIAL_COMMAND is set in this")
        out("            shell's environment only, not in service.env, so a restarted kernel would not see it")
        out("            either. A running kernel keeps the mode it started in. Put the line in service.env, then")
        out("            `romp refresh` restarts the kernels into command mode; until then the kernel injects no")
        out("            set. A drop-in line reaches them at the manager restart after `systemctl --user")
        out("            daemon-reload` instead; not a line added to the unit or the plist by hand, which the")
        out("            next `romp-service install` rewrites away.")
    return 1


# ---------------------------------------------------------------------------
# COMMAND mode — the selector, this shell's run, the kernel's run, and the switch.
# ---------------------------------------------------------------------------

def _local():
    """This shell's own run of the command (and of the apiKeyHelper when the set carries no key),
    value-free: {"snap" (envsource's record), "fp", "kind" ("key"|"helper"|""), "err" (why there is
    no fingerprint and it is a failure), "noHelper" (no fingerprint because none is configured: a
    login-billed installation, not a failure), "selector", "selErr"}."""
    snap = es.status()
    sel, sel_err = es.read_selector()
    st = {"snap": snap, "fp": "", "kind": "", "err": "", "noHelper": "", "selector": sel, "selErr": sel_err}
    if snap.get("ok") is False:
        reason = snap.get("reason") or "failed"
        st["err"] = reason if reason.startswith("the selector") else "the credential command " + reason
    elif snap.get("hasKey"):
        st["fp"], st["kind"] = snap.get("keyFp") or "", "key"
    else:
        if not es.helper_command():
            st["kind"], st["noHelper"] = "login", es.helper_fingerprint()[1]      # nothing to run: the reason names the files
        else:
            hfp, hreason = es.helper_fingerprint()
            if hfp:
                st["fp"], st["kind"] = hfp, "helper"
            else:
                st["err"] = "the set carries no %s and the apiKeyHelper %s" % (es.KEY_VAR, hreason)
    return st


def _sel_word(token):
    """A selector token as the report may show it: by name when it is declared in ROMP_CREDENTIAL_NAMES,
    else by length only — an undeclared token could be anything, a pasted secret included."""
    if not token:
        return "(none)"
    return token if token in es.names() else "(undeclared, %d chars)" % len(token)


def _header(st, out):
    """The command-mode report's local half: source, selector, candidates, set, live key. Returns 1 when
    this shell could not fingerprint anything it should have (the command or the helper failed)."""
    snap = st["snap"]
    out("key source  command (%s is set): the kernel runs it and injects the set it prints" % es.COMMAND_VAR)
    sel_path = es.selector_path()
    if st["selErr"]:
        out("selector    UNREADABLE     %s — %s" % (sel_path, st["selErr"]))
    elif st["selector"]:
        out("selector    %-14s %s" % (_sel_word(st["selector"]), sel_path))
    else:
        out("selector    %-14s %s (absent: the command runs with an empty $1)" % ("(none)", sel_path))
    declared = es.names()
    if declared:
        out("candidates  " + ", ".join(n + (" <- selected" if n == st["selector"] else "") for n in declared))
    else:
        out("candidates  none declared (%s is unset; `romp keyswap <name>` needs it, and the selector is shown by "
            "length only)" % es.NAMES_VAR)
    if snap.get("timeoutProblem"):
        out("timeout     %s" % snap["timeoutProblem"])
    rc = 0
    if st["err"]:
        if snap.get("ok") and snap.get("setFp"):
            out("set         %s — %s" % (_sha(snap.get("setFp")), _names_phrase(snap)))
        out("live key    UNAVAILABLE — %s" % st["err"])
        rc = 1
    else:
        out("set         %s — %s" % (_sha(snap.get("setFp")), _names_phrase(snap)))
        if st["kind"] == "key":
            out("live key    %s   (this shell's run of the command: its %s line)" % (_sha(st["fp"]), es.KEY_VAR))
        elif st["kind"] == "helper":
            out("live key    %s   (this shell's run of the apiKeyHelper; the set carries no %s)"
                % (_sha(st["fp"]), es.KEY_VAR))
        else:
            out("live key    (none) — the set carries no %s and %s; sessions bill the machine login, and a"
                % (es.KEY_VAR, st["noHelper"]))
            out("            cycle covers the role variables in the set")
    return rc


def _names_phrase(snap):
    names = list(snap.get("names") or [])
    return "%d name%s: %s" % (len(names), "" if len(names) == 1 else "s", ", ".join(names)) if names else "no names"


def _kernel_lines(body, st, out):
    """The command-mode report's kernel half from a /keycycle read: what the kernel's own run yields,
    how many live sessions launched on which fingerprint, and MISMATCH when the kernel's run and this
    shell's disagree. Returns the exit code the comparison deserves. The fingerprint MISMATCH's hint
    names `romp-service install` as the reload a plist line takes, so it states the install's cost in
    the same breath, as every other hint that names the install does (_restart_block, _mode_mismatch):
    the rewrite drops a hand-added unit or plist line and the next kernel pins file mode, a drop-in
    survives (the one hint round 8 left without it, 2026-09-06)."""
    if (body.get("keySource") or "file") != "command":
        return _mode_mismatch(body, out)
    kfp = body.get("keyFp") or ""
    kerr = body.get("keyErr") or ""
    kkind = body.get("keyKind") or ""
    launched = body.get("launched") or {}
    note = _refreshed_note(body.get("refreshed"), kfp)
    rc = 0
    if kerr and not kfp:
        out("kernel      UNAVAILABLE — %s%s" % (kerr, (" (%s)" % note) if note else ""))
        rc = 1
    elif kerr:
        out("kernel      reads %s (its own run%s; the latest run failed — %s — so it stands on the previous set)"
            % (_sha(kfp), (", " + note) if note else "", kerr))
        rc = 1
    elif not kfp and kkind == "login":
        # no key in the set and no apiKeyHelper configured: the machine login bills, there is nothing
        # to fingerprint, and that is not a failure — the cycle still re-presents the role variables
        out("kernel      reads no key (its own run%s): sessions bill the machine login; a cycle covers the role"
            % ((", " + note) if note else ""))
        out("            variables (set %s); %d live session(s) launched with no key" % (_sha(body.get("setFp") or ""), launched.get("", 0)))
    else:
        out("kernel      reads %s (its own run%s); %d live session(s) on it"
            % (_sha(kfp), (", " + note) if note else "", launched.get(kfp, 0)))
    for fp2 in sorted(launched):
        if fp2 == kfp or (kkind == "login" and not fp2 and not kerr):
            continue
        if fp2:
            out("            %d live session(s) still on sha256:%s" % (launched[fp2], fp2))
        else:
            out("            %d live session(s) launched with no credential the kernel fingerprinted" % launched[fp2])
    if st["err"] or rc:
        return 1                              # one side has nothing to compare; already said
    diffs = []
    if kfp != st["fp"]:
        diffs.append("the credential fingerprint")
    if (body.get("setFp") or "") != (st["snap"].get("setFp") or ""):
        diffs.append("the set's fingerprint")
    if not diffs:
        return 0
    out("MISMATCH    the kernel's run of the command and this shell's disagree on %s." % " and ".join(diffs))
    ksel = body.get("selector") or ""                 # the kernel renders its selector the same way: a
    lsel = _sel_word(st["selector"]) if st["selector"] else ""   # declared name, or a length
    if ksel != lsel:
        out("            The kernel's last run used selector %s, this shell's %s: `romp keyswap --refresh`"
            % (ksel or "(none)", lsel or "(none)"))
        out("            makes the kernel re-run it now.")
    else:
        out("            Usual causes: the service environment (service.env, the unit or the plist) carries")
        out("            other ROMP_CREDENTIAL_* values than this shell (a line added to service.env reaches the")
        out("            kernel at its next start, `romp refresh`; a line changed or removed there, or one in the")
        out("            unit, at the next manager restart, whose environment holds the copy loaded at its start,")
        out("            and a unit or plist line reaches that restart only once the definition is reloaded:")
        out("            daemon-reload on Linux, `romp-service install` on macOS, which rewrites the plist as the")
        out("            Linux install rewrites the unit, so a line added to either by hand is gone and the next")
        out("            kernel pins file mode; drop-ins survive, so put your own lines in service.env or a")
        out("            drop-in), the two resolve different selector files, or CLAUDE_CONFIG_DIR differs (the")
        out("            apiKeyHelper the kernel fingerprints is the one its own settings name).")
    return 1


def _rotate_hint(out):
    declared = es.names()
    out("")
    out("rotate:     romp keyswap <name>  writes the selector%s and re-runs the command; then"
        % ((" (one of: %s)" % ", ".join(declared)) if declared else ""))
    out("            romp keyswap --cycle-all  so quiet sessions reconnect. A new value behind the same")
    out("            name: romp keyswap --cycle-all  alone (it re-runs the command first).")


def _report_command(out, refresh=False):
    """The bare report in command mode; --refresh makes the kernel re-run first."""
    st = _local()
    rc = _header(st, out)
    body, krc = _ask(out, refresh)
    if body is None:
        if krc == 0:
            out("kernel      not running — it runs the command itself when it is")
        rc = rc or krc
    else:
        rc = max(rc, _kernel_lines(body, st, out))
    _rotate_hint(out)
    return rc


def _cycle_command(sessions, all_, out, header=True):
    """The cycle in command mode: this shell's run, the kernel's re-run (refresh), the compare, then
    the reconnects. A local failure or a MISMATCH stops it before any reconnect."""
    st = _local()
    rc = _header(st, out) if header else (1 if st["err"] else 0)
    if rc:
        out("cycle       NOT DONE — this shell could not fingerprint the credential, so there is nothing to")
        out("            compare the kernel's run against. Fix the command (or the helper) first, then cycle.")
        return 1
    body, krc = _ask(out, True)
    if body is None:
        _not_done_unasked(krc, out)
        return 1
    if _kernel_lines(body, st, out):
        out("cycle       NOT DONE — the kernel is not on the credential this shell reads, so a reconnect would")
        out("            re-present what it already has. Fix the mismatch above first, then cycle.")
        return 1
    return _do_cycle(_kernel(), sessions, all_, out)


def _restore_selector(old, sel_err, target, name):
    """Put the selector back after a switch that switched nothing, and SAY what happened: the old
    token, or an empty file where there was none (the target, so a dotfiles link keeps pointing where
    it did). Returns the clause for the selector line — "put back to <old>" only when the write
    succeeded; an old selector that could not be read before the switch cannot be put back, and a
    failed write leaves the new name in place, and both say so rather than claim a restore."""
    if sel_err:
        return "NOT put back — the old selector could not be read before the switch (%s), so the file now holds %s" % (sel_err, name)
    try:
        if old:
            es.write_selector(old)
        else:
            with open(target, "w", encoding="utf-8"):
                pass
    except OSError as e:
        return "NOT put back (errno %s writing the selector file), so it still holds %s" % (getattr(e, "errno", None) or "?", name)
    return "put back to %s" % _sel_word(old)


def _switch(name, out):
    """`romp keyswap <name>` in command mode. The name is checked before anything runs: a token, and
    declared in ROMP_CREDENTIAL_NAMES when that is set — an undeclared name is refused and NEVER
    echoed (a key pasted where a name was expected must not reach a terminal). Then: this shell runs
    the command on the OLD selector, writes the new token, runs again, and confirms the fingerprint
    moved. A switch that moves nothing (the command ignores $1, both names resolve to one credential,
    or the command fails for the new name) is undone — the selector goes back — and exits 1: the
    world is as it was. A switch that moved asks the kernel to re-run too and reports its view."""
    if not es.valid_selector(name):
        sys.stderr.write("romp keyswap: a selector is one name — letters, digits, '.', '_' or '-', up to 64\n"
                         "             characters (%d characters given); nothing switched.\n" % len(name))
        return 2
    if not es.names():
        # nothing declared: no name can be checked, so none is written — and the argument is not echoed
        sys.stderr.write("romp keyswap: declare %s first (the comma list of names this command may select,\n"
                         "             in service.env or the service environment); nothing switched.\n" % es.NAMES_VAR)
        return 2
    if not es.selector_allowed(name):
        sys.stderr.write("romp keyswap: that name is not declared in %s (declared: %s);\n"
                         "             nothing switched. Declare it there first if it is meant to exist.\n"
                         % (es.NAMES_VAR, ", ".join(es.names())))
        return 2
    old, sel_err = es.read_selector()
    if old == name:
        out("selector    %s (already selected)" % name)
        out("            nothing to switch — `romp keyswap --refresh` re-runs the command; `romp keyswap --cycle-all`")
        out("            moves the sessions onto whatever it prints now")
        return 0
    before = _local()
    try:
        w = es.write_selector(name)
    except OSError as e:
        sys.stderr.write("romp keyswap: the selector file could not be written (errno %s): %s; nothing switched.\n"
                         % (getattr(e, "errno", None) or "?", es.selector_path()))
        return 1
    es.invalidate("switch")
    after = _local()
    was = _sel_word(old)
    if after["err"]:
        undo = _restore_selector(old, sel_err, w["target"], name)
        out("selector    %s -> %s, %s" % (was, name, undo))
        out("live key    UNAVAILABLE — %s" % after["err"])
        out("            nothing switched: the command failed for %s%s" % (
            name, ", so the selector is as it was." if undo.startswith("put back") else "."))
        return 1
    moved = after["fp"] != before["fp"] or (after["snap"].get("setFp") or "") != (before["snap"].get("setFp") or "")
    if not moved:
        undo = _restore_selector(old, sel_err, w["target"], name)
        out("selector    %s -> %s, %s" % (was, name, undo))
        out("live key    %s   (unchanged)" % _sha(after["fp"]))
        out("            nothing switched: the command printed the same set for %s as for %s. It must read the"
            % (name, was if old else "an empty $1"))
        out("            selector as $1 — `my-cmd \"$1\"`, not a bare `my-cmd` — and the two names must resolve to")
        out("            different credentials.")
        return 1
    out("selector    %s -> %s" % (was, name))
    out("live key    %s   (was %s)" % (_sha(after["fp"]), _sha(before["fp"])))
    if (after["snap"].get("setFp") or "") != (before["snap"].get("setFp") or ""):
        out("set         %s   (was %s)" % (_sha(after["snap"].get("setFp")), _sha(before["snap"].get("setFp"))))
    body, krc = _ask(out, True)
    if body is None:
        if krc == 0:
            out("kernel      not running — its next start runs the command with the new selector")
        return krc
    return _kernel_lines(body, after, out)


def parse_args(argv):
    """(source, cycle-list, cycle-all, error, refresh). Positional: at most one source name. The error
    for a second positional counts the arguments and never echoes them: a key value typed where a name
    was expected must not reach stderr (the rule every other surface here follows)."""
    src, cycle, cycle_all, err, refresh = "", [], False, "", False
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--cycle-all":
            cycle_all = True
        elif a == "--refresh":
            refresh = True
        elif a == "--cycle" or a.startswith("--cycle="):
            if a == "--cycle":
                i += 1
                val = argv[i] if i < len(argv) else ""
            else:
                val = a.split("=", 1)[1]
            cycle = [s.strip() for s in val.split(",") if s.strip()]
            if not cycle:
                err = err or "--cycle needs a session list, e.g. --cycle web,api"
        elif a.startswith("-"):
            err = err or ("unknown option %s" % a)
        else:
            positional.append(a)
        i += 1
    src = positional[0] if positional else ""
    if len(positional) > 1:
        err = err or "one source at a time (%d positional arguments given)" % len(positional)
    return src, cycle, cycle_all, err, refresh


def main(argv, out=None):
    out = out or (lambda line: sys.stdout.write(line + "\n"))
    src_arg, cycle, cycle_all, err, refresh = parse_args(list(argv))
    if err:
        sys.stderr.write("romp keyswap: %s\n" % err)
        return 2
    if es.configured():
        # COMMAND mode. The mode is read the way the kernel reads it (this environment, then the env
        # file), so the report and a launch cannot disagree about which source is in force.
        if src_arg:
            rc = _switch(src_arg, out)
            if rc or not (cycle or cycle_all):
                return rc
            return _cycle_command(cycle, cycle_all, out, header=False)
        if cycle or cycle_all:
            return _cycle_command(cycle, cycle_all, out)
        return _report_command(out, refresh)
    if src_arg:
        # FILE mode: the rewrite is refused here, whatever the name resolves to and whether or not the
        # file exists: the answer does not depend on the filesystem, so nothing is read or written
        # before it. --cycle riding the same command line is refused with it — the name made this a
        # swap request, and the message names the bare --cycle-all form that does the reconnect.
        sys.stderr.write(REFUSAL)
        return 2
    path = ks.service_env_path()
    # Read-only report: the key the kernel holds (fingerprint), the file it reads, and the sibling
    # files upstream's swap would have used (none expected here).
    out("service.env %s" % path)
    out("live key    %s" % _fp(ks.read_key(path)))
    _candidates(path, out)
    if cycle or cycle_all:
        return _cycle(cycle, cycle_all, out, path, refresh)
    rc = _kernel_check(path, out, refresh)
    out("")
    out("rotate:     this fork writes no key to a file — rotate the key at its source (the apiKeyHelper's")
    out("            store, or the manager's environment), then  romp keyswap --cycle-all  so quiet")
    out("            key-billed sessions reconnect and pick it up. Sessions billed through the apiKeyHelper")
    out("            read as the login in this mode and are skipped by that cycle: they cycle in command mode")
    out("            (set ROMP_CREDENTIAL_COMMAND), or  romp refresh --quiet  restarts every process")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

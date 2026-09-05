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

# `romp keyswap <name>` is refused in FILE mode on this fork (the user 2026-09-05). The exit code is 2,
# the class the other usage refusals use; the file is never opened for writing. One string, so a
# reword is a deliberate edit and the bats/python tests pin the same text the operator reads.
REFUSAL = (
    "romp keyswap: refused — this fork does not write API keys to files, so the named swap is disabled.\n"
    "             Keys reach the sessions through Claude Code's apiKeyHelper or through the manager's\n"
    "             environment; nothing here rewrites service.env, so there is nothing for a swap to do.\n"
    "             After rotating a key, run\n"
    "                 romp keyswap --cycle-all      (or: romp refresh --quiet)\n"
    "             so the running sessions reconnect and their new processes pick the new key up.\n")


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
    req = urllib.request.Request(u + path, data=json.dumps(body).encode(),
                                headers={"Content-Type": "application/json",
                                         "X-Romp-Token": _token()}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
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
    to ask for by eye (review find, 2026-09-04). The two can differ: the service was installed with
    another env-file path that never reached the kernel's environment, the file is unreadable to the
    kernel, the kernel still holds its startup key because the file has no key line, or the kernel
    predates this feature. Reads the fingerprint through /keycycle with no sessions named — a read,
    nothing cycles. Returns 0 when they agree (or no kernel is up to ask), 1 when they do not — or when
    the port override is unusable, which is a misconfiguration to fix, not "no kernel"."""
    body, rc = _ask(out, refresh)
    if body is None:
        if rc == 0:
            out("kernel      not running — sessions read the file when it is")
        return rc
    if (body.get("keySource") or "file") != "file":
        return _mode_mismatch(body, "file", out)
    return _compare(body.get("keyFp") or "", path, out, body.get("refreshed"))


def _compare(kfp, path, out, refreshed=None):
    """Print the kernel's fingerprint and, when it is not the file's, say so and why it may be."""
    note = _refreshed_note(refreshed, kfp, "re-read")
    out("kernel      reads %s%s" % (_sha(kfp), (" (%s)" % note) if note else ""))
    if kfp == ks.fingerprint(ks.read_key(path)):
        return 0
    out("MISMATCH    the kernel is not reading this file's key. Usual causes: the service was installed")
    out("            with another env-file path that the kernel's environment does not carry (re-run")
    out("            `romp service install`), the file is unreadable to the kernel, or the file has no")
    out("            %s line and the kernel still holds its startup key." % ks.KEY_VAR)
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
    reads another file would re-present the kernel's unchanged key, so a mismatch refuses to cycle."""
    body, rc = _ask(out, refresh)
    if body is None:
        _not_done_unasked(rc, out)
        return 1
    if (body.get("keySource") or "file") != "file":
        _mode_mismatch(body, "file", out)
        out("cycle       NOT DONE — fix the mismatch above first, then cycle.")
        return 1
    if _compare(body.get("keyFp") or "", path or ks.service_env_path(), out, body.get("refreshed")):
        out("cycle       NOT DONE — the kernel is not on this file's key, so a reconnect would re-present")
        out("            the key it already has. Fix the mismatch above first, then cycle.")
        return 1
    return _do_cycle(_kernel(), sessions, all_, out)


def _not_done_unasked(rc, out):
    """The cycle could not even read the kernel: no kernel running (rc 0 from _ask — the report stands,
    the cycle does not), or an ask _ask already reported (an unusable port, a 404, a refusal)."""
    if rc == 0:
        out("cycle       NOT DONE — no running kernel found (is romp on? `romp status`).")
        out("            Nothing was cycled. A session's next launch or revive runs a new process")
        out("            anyway; re-run `romp keyswap --cycle…` once romp is up for the running ones.")
    else:
        out("cycle       NOT DONE — see above. Nothing was cycled.")


def _do_cycle(u, sessions, all_, out):
    """The cycle itself, once the read agreed: one POST naming the sessions (or all), then the rows."""
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


def _mode_mismatch(body, local_mode, out):
    """The kernel and this shell resolve DIFFERENT modes: ROMP_CREDENTIAL_COMMAND is set for one and not
    the other. The kernel reads its environment (the unit's, plus service.env at manager start), this
    shell its own and then service.env — so the usual cause is an edit that the running manager has
    not seen, and the fix is the manager restart that reads it. Names the variable and the two places;
    never a value."""
    kmode = body.get("keySource") or "file"
    out("kernel      reads %s in %s mode" % (_sha(body.get("keyFp") or ""), kmode.upper()))
    if kmode == "command":
        out("MISMATCH    the kernel is in command mode and this shell is not: ROMP_CREDENTIAL_COMMAND is in the")
        out("            kernel's environment (the unit or service.env at its last start) but not in this shell's")
        out("            and not in service.env now. If the line was removed, restart the manager so it reads")
        out("            file mode; if it should be set, put it back in service.env (this shell reads it from there).")
    else:
        out("MISMATCH    the kernel is in file mode and this shell is not: ROMP_CREDENTIAL_COMMAND is set here (this")
        out("            shell's environment or service.env) but was not in the kernel's environment when the")
        out("            manager started. An edit to service.env or the unit reaches the kernel at the next manager")
        out("            restart (`systemctl --user restart romp-manager`, or `romp-service install`); until then")
        out("            the kernel injects no set.")
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
        hfp, hreason = es.helper_fingerprint()
        if hfp:
            st["fp"], st["kind"] = hfp, "helper"
        elif not es.helper_command():
            st["noHelper"] = hreason
        else:
            st["err"] = "the set carries no %s and the apiKeyHelper %s" % (es.KEY_VAR, hreason)
    return st


def _header(st, out):
    """The command-mode report's local half: source, selector, candidates, set, live key. Returns 1 when
    this shell could not fingerprint anything it should have (the command or the helper failed)."""
    snap = st["snap"]
    out("key source  command (%s is set): the kernel runs it and injects the set it prints" % es.COMMAND_VAR)
    sel_path = es.selector_path()
    if st["selErr"]:
        out("selector    UNREADABLE     %s — %s" % (sel_path, st["selErr"]))
    elif st["selector"]:
        out("selector    %-14s %s" % (st["selector"], sel_path))
    else:
        out("selector    %-14s %s (absent: the command runs with an empty $1)" % ("(none)", sel_path))
    declared = es.names()
    if declared:
        out("candidates  " + ", ".join(n + (" <- selected" if n == st["selector"] else "") for n in declared))
    else:
        out("candidates  none declared (%s is unset; any name is accepted)" % es.NAMES_VAR)
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
            out("live key    (none) — the set carries no %s and %s; sessions bill the login" % (es.KEY_VAR, st["noHelper"]))
    return rc


def _names_phrase(snap):
    names = list(snap.get("names") or [])
    return "%d name%s: %s" % (len(names), "" if len(names) == 1 else "s", ", ".join(names)) if names else "no names"


def _kernel_lines(body, st, out):
    """The command-mode report's kernel half from a /keycycle read: what the kernel's own run yields,
    how many live sessions launched on which fingerprint, and MISMATCH when the kernel's run and this
    shell's disagree. Returns the exit code the comparison deserves."""
    if (body.get("keySource") or "file") != "command":
        return _mode_mismatch(body, "command", out)
    kfp = body.get("keyFp") or ""
    kerr = body.get("keyErr") or ""
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
    else:
        out("kernel      reads %s (its own run%s); %d live session(s) on it"
            % (_sha(kfp), (", " + note) if note else "", launched.get(kfp, 0)))
    for fp2 in sorted(launched):
        if fp2 == kfp:
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
    ksel = body.get("selector") or ""
    if ksel != (st["selector"] or ""):
        out("            The kernel's last run used selector %s, this shell's %s: `romp keyswap --refresh`"
            % (ksel or "(none)", st["selector"] or "(none)"))
        out("            makes the kernel re-run it now.")
    else:
        out("            Usual causes: the service environment (service.env, or the unit) carries other")
        out("            ROMP_CREDENTIAL_* values than this shell — an edit there reaches the kernel at the next")
        out("            manager restart — the two resolve different selector files, or CLAUDE_CONFIG_DIR differs")
        out("            (the apiKeyHelper the kernel fingerprints is the one its settings.json names).")
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


def _restore_selector(old, target):
    """Put the selector back after a switch that switched nothing: the old token, or an empty file
    where there was none (the target, so a dotfiles link keeps pointing where it did)."""
    try:
        if old:
            es.write_selector(old)
        else:
            with open(target, "w", encoding="utf-8"):
                pass
    except OSError:
        pass


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
    if not es.selector_allowed(name):
        sys.stderr.write("romp keyswap: that name is not declared in %s (declared: %s);\n"
                         "             nothing switched. Declare it there first if it is meant to exist.\n"
                         % (es.NAMES_VAR, ", ".join(es.names())))
        return 2
    old, _sel_err = es.read_selector()
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
    was = old or "(none)"
    if after["err"]:
        _restore_selector(old, w["target"])
        out("selector    %s -> %s, put back to %s" % (was, name, was))
        out("live key    UNAVAILABLE — %s" % after["err"])
        out("            nothing switched: the command failed for %s, so the selector is as it was." % name)
        return 1
    moved = after["fp"] != before["fp"] or (after["snap"].get("setFp") or "") != (before["snap"].get("setFp") or "")
    if not moved:
        _restore_selector(old, w["target"])
        out("selector    %s -> %s, put back to %s" % (was, name, was))
        out("live key    %s   (unchanged)" % _sha(after["fp"]))
        out("            nothing switched: the command printed the same set for %s as for %s. It must read the"
            % (name, old or "an empty $1"))
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
    out("            sessions reconnect and pick it up")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

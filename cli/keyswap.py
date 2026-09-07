#!/usr/bin/env python3
"""romp-keyswap: report which API key the sessions bill, switch it, and reconnect them after a rotation.

The kernel selects its key source live (kernel/keysource.py, select_source), from the manager's env file
(`~/.config/romp/service.env`) and the manager's environment: a credential command
(`ROMP_CREDENTIAL_COMMAND=`), else a 1Password reference (`ROMP_API_KEY_REF=op://...`), else a key line
(`ANTHROPIC_API_KEY=`). This command reads the same file with the same module and decides its arm from
what it finds there and in this shell's environment:

  * Under a reference or a key line, `romp keyswap <name>` selects the source held by a sibling profile
    (`service.env.<name>`), which may carry any of the three lines, by rewriting the live file and removing
    the competing assignments. This command never resolves a reference.
  * Under a credential command (kernel/envsource.py), the kernel runs the command with the selector file's
    one token as `$1` and injects the NAME=VALUE set it prints into every launch. Here `romp keyswap <name>`
    writes that token (a name, never a key) after checking it against ROMP_CREDENTIAL_NAMES, runs the
    command in this shell, confirms the fingerprint moved, and asks the kernel to re-run too. The command's
    output is hashed inside envsource; only fingerprints come back.

Common to every kind:

  * the bare command reports what the kernel holds, by fingerprint, and whether it agrees with what this
    shell reads (a `/keycycle` read that names no session): MISMATCH, with the cause, when the two resolve
    different kinds, different sources, or different credentials;
  * `--refresh` makes the kernel re-run its command now (a plain re-read under the other kinds) and prints
    the fingerprint before and after;
  * `--cycle <names>` / `--cycle-all` reconnect quiet running sessions so each resumes its own conversation,
    history intact, in a NEW CLI process, which is how a rotated credential reaches a session: a process
    keeps what it started with. Under a command the kernel re-runs it first and reconnects only the
    sessions whose launch fingerprint differs, so a second run reads "current" for the ones already moved.
    The manager never restarts, so no session loses an open turn; a session with a turn, subagents or
    background tasks in flight is skipped and named.

No key value is ever printed, logged or passed over the wire. The only rendered form is the first 12 hex
of a sha256 ("sha256:1a2b3c..."); a failure reason carries counts and exit codes only, and an undeclared
selector name is never echoed.

Usage:
    romp keyswap                            # what is live now, and whether this shell agrees
    romp keyswap lowprio                    # a profile (service.env.lowprio), or a declared name under a command
    romp keyswap lowprio --cycle web,api    # ...and reconnect those two sessions onto it
    romp keyswap --cycle-all                # after a rotation: reconnect every quiet session
    romp keyswap --refresh                  # make the kernel re-run its command now
    romp keyswap /path/to/other.env         # an explicit profile file (a reference or a key line selected)
"""
import json
import os
import sys
import urllib.error
import urllib.request
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The SAME modules the kernel reads the credential with, not a second copy of the rules: writer and reader
# then cannot disagree about which file holds the source, which line wins, how it is parsed, where the
# selector lives or how a fingerprint is taken. envsource loads keysource under the same module name, so
# the two hold one keysource between them.
ks = sys.modules.get("romp_keysource") or SourceFileLoader(
    "romp_keysource", str(ROOT / "kernel" / "keysource.py")).load_module()
es = sys.modules.get("romp_envsource") or SourceFileLoader(
    "romp_envsource", str(ROOT / "kernel" / "envsource.py")).load_module()

KPORTS = ["http://127.0.0.1:29855", "http://127.0.0.1:7878", "http://127.0.0.1:7432"]

# The column every hint line stays within, indent included. One exception, deliberate: a path is never
# broken, so a service.env path too long for its sentence goes whole on a line of its own (_other_file).
WIDTH = 100

# The word each kind is named by when the kernel and this shell disagree; never a value.
_KIND_WORDS = {"command": "a credential command (%s)" % ks.CMD_VAR,
               "op": "a 1Password reference (%s)" % ks.REF_VAR,
               "file": "an API key line (%s)" % ks.KEY_VAR}


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
    # The kernel may run its credential command (and the apiKeyHelper) before answering, each bounded by
    # ROMP_CREDENTIAL_TIMEOUT_S, so the wait scales with that deadline rather than cutting a slow but
    # working command off: 10 s plus twice the deadline (40 s at the default of 15 s).
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


def _source_label(source):
    """Describe configuration without retrieving a provider's secret, running a command or exposing a
    literal key: the runtime kinds by their source fingerprint, a key by its own."""
    try:
        source.validate()
    except ks.KeySourceError:
        return "(invalid key source)"
    if source.kind == "op":
        return "1Password reference " + source.fingerprint()
    if source.kind == "command":
        return "credential command " + source.fingerprint()
    return _fp(source.value)


def _legacy_key_present(path):
    """Detect plaintext hidden by a higher-priority reference so selecting it also cleans up."""
    try:
        with open(path, encoding="utf-8") as fh:
            return bool(ks.parse_key(fh.read()))
    except (OSError, UnicodeError):
        # Attempt the write so its ordinary error path reports an unreadable live file.
        return True


def _shell_source(path):
    """(KeySource, where): the source THIS SHELL resolves, the way the kernel's select_source would for a
    foreground manager but with none of its memory: the marker file and the in-memory paths it writes are
    the kernel's, so they are not touched from here. The file's line wins when it has one (command >
    reference > key, keysource.parse_source); with no line, ROMP_CREDENTIAL_COMMAND in this shell's
    environment selects the command kind, as it does for a foreground manager (a supervised one reads the
    file only, which is one of the MISMATCH causes below). `where` is "file" or "environment"."""
    source = ks.read_source(path)
    if source.kind != "none":
        return source, "file"
    if ks.CMD_VAR in os.environ:
        return ks.KeySource("command", os.environ[ks.CMD_VAR].strip()), "environment"
    return source, "file"


def _shell_word(source):
    """The keySource word the kernel would answer for this shell's source: file | op | command; None for an
    invalid source, which _compare reports in its own words."""
    if source.kind == "error":
        return None
    return source.kind if source.kind in ("op", "command") else "file"


def _kind_differs(body, source):
    """True when the kernel answered a keySource and it is not this shell's kind. An answer without the
    field (a kernel that predates it) is compared by fingerprint alone, as before."""
    kmode = body.get("keySource")
    word = _shell_word(source)
    return kmode is not None and word is not None and kmode != word


def _ask(out, refresh=False):
    """The /keycycle read that names no session: the kernel's fingerprint and key-source facts, with
    `refresh` asking it to re-run its command first. Returns (body, rc, url): body None when nothing could
    be asked, rc the exit code that outcome deserves (0 for "no kernel is running", where the caller says
    what that means for it; 1 for an unusable port override, a kernel that predates the route, or a
    refused ask, each already said here), url the kernel that answered."""
    try:
        _kernel_urls()
    except ValueError as e:
        out("kernel      NOT ASKED — %s; fix the variable and re-run" % e)
        return None, 1, None
    u = _kernel()
    if not u:
        return None, 0, None
    body = _post(u, "/keycycle", {"sessions": [], "refresh": True} if refresh else {"sessions": []})
    if body.get("error") == "HTTP 404":
        out("kernel      predates `romp keyswap` (no /keycycle route): it is still on the key it booted")
        out("            with. Take the patch once with `romp refresh`; every swap after that is restart-free.")
        return None, 1, u
    if not body.get("ok"):
        out("kernel      could not be asked — %s" % (body.get("error") or body.get("detail") or "unknown"))
        return None, 1, u
    return body, 0, u


# ---------------------------------------------------------------------------
# A reference or a key line: the profile report, selection and cycle, plus --refresh and the kind check.
# ---------------------------------------------------------------------------

def _candidates(path, out):
    """List the sibling `service.env.<name>` files, each by fingerprint only — so `romp keyswap`
    with no argument answers both "which key is live" and "what can I swap to"."""
    d = os.path.dirname(path) or "."
    base = os.path.basename(path) + "."
    try:
        # `service.env.source` is the kernel's durable "the source was a runtime one" marker (keysource
        # .SOURCE_MARKER), not a candidate profile — it holds no key line and would list as "(no key source)"
        names = sorted(n[len(base):] for n in os.listdir(d)
                       if n.startswith(base) and not n.endswith("~") and n[len(base):] != ks.SOURCE_MARKER)
    except OSError:
        names = []
    live = ks.read_source(path)
    if not names:
        out("candidates  none — keep one file per key beside it, e.g. %s.lowprio (chmod 600)," % os.path.basename(path))
        out("            each a single ROMP_API_KEY_REF=op://…, ROMP_CREDENTIAL_COMMAND=… or %s=… line" % ks.KEY_VAR)
        return
    out("candidates")
    for n in names:
        source = ks.read_source(ks.sibling_path(n, path))
        mark = "  <- live" if (source.configured and source == live) else ""
        label = _source_label(source) if source.kind != "none" else "(no key source)"
        out("  %-14s %s%s" % (n, label, mark))


def _kernel_check(path, out, refresh=False):
    """Compare what the KERNEL reads with what the FILE says — the check the operator procedure used
    to ask for by eye (review find, 2026-09-04). The two can differ: the service was installed with
    another env-file path that never reached the kernel's environment, the file is unreadable to the
    kernel, the kernel still holds its startup key because the file has no key line, the kernel selects
    another kind from its own environment, or the kernel predates this feature. Reads the fingerprint
    through /keycycle with no sessions named — a read, nothing cycles. Returns 0 when they agree (or no
    kernel is up to ask), 1 when they do not — or when the port override is unusable, which is a
    misconfiguration to fix, not "no kernel"."""
    body, rc, _u = _ask(out, refresh)
    if body is None:
        if rc == 0:
            out("kernel      not running — sessions read the file when it is")
        return rc
    source = ks.read_source(path)
    if _kind_differs(body, source):
        return _mode_mismatch(body, out, source, "file", path)
    return _compare(body, path, out, body.get("refreshed"))


def _compare(body, path, out, refreshed=None):
    """Compare provider configuration, or conventional keys for compatibility with older kernels. A
    credential command is compared like a reference, by source identity (the hash of its text): the key
    it prints is the kernel's to fingerprint."""
    source = ks.read_source(path)
    try:
        source.validate()
    except ks.KeySourceError as exc:
        out("MISMATCH    this file has an invalid key source — %s" % exc)
        return 1
    if source.kind in ("op", "command"):
        if "sourceFp" not in body:
            out("kernel      predates runtime key sources; update it with `romp refresh` before cycling")
            return 1
        source_fp = body.get("sourceFp") or ""
        # a status read never runs op, so there is no credential fingerprint to say "was" about there
        note = (_reread_note(refreshed) if source.kind == "op"
                else _refreshed_note(refreshed, body.get("keyFp") or ""))
        out("kernel      source %s%s" % (source_fp or "(none)", (" (%s)" % note) if note else ""))
        if source_fp == source.fingerprint():
            if source.kind == "op":
                out("            1Password reference matches; credentials are retrieved at runtime")
            else:
                out("            the credential command matches; the kernel runs it and injects the set it prints")
            return 0
    else:
        kfp = body.get("keyFp") or ""
        note = _refreshed_note(refreshed, kfp, "re-read")
        out("kernel      reads %s%s" % (("sha256:" + kfp) if kfp else "(none)", (" (%s)" % note) if note else ""))
        if kfp == source.fingerprint():
            return 0
    out("MISMATCH    the kernel is not reading this file's key source. Usual causes: the service was installed")
    out("            with another env-file path that the kernel's environment does not carry (re-run")
    out("            `romp service install`), the file is unreadable to the kernel, or its credential")
    out("            configuration differs from the running manager's.")
    return 1


def _refreshed_note(refreshed, now_fp, verb="re-run"):
    """The clause a --refresh adds to the kernel line: "re-run now: was sha256:..." when the kernel's
    fingerprint moved, "re-run now: unchanged" when it did not, "" when no refresh was asked for. `verb` is
    "re-read" under a key line, where the refresh is a re-read of the env file. A failed re-run is the
    kernel line's own business (keyErr): the note says only what moved."""
    if not isinstance(refreshed, dict):
        return ""
    frm = refreshed.get("from") or ""
    return "%s now: was %s" % (verb, _sha(frm)) if frm != now_fp else "%s now: unchanged" % verb


def _reread_note(refreshed):
    """The note under a reference, where a status read fingerprints nothing: the kernel re-read, no more."""
    return "re-read now" if isinstance(refreshed, dict) else ""


def _cycle(sessions, all_, out, path=None, refresh=False):
    """Reconnect the named sessions through the kernel, and report what it did per session. The
    kernel's fingerprint is READ and compared with the file's FIRST: cycling a session while the kernel
    reads another file would re-present the kernel's unchanged key, so a mismatch refuses to cycle."""
    try:
        _kernel_urls()
    except ValueError as e:
        out("cycle       NOT DONE — %s; fix the variable and re-run" % e)
        return 1
    u = _kernel()
    if not u:
        out("cycle       NOT DONE — no running kernel found (is romp on? `romp status`).")
        out("            The file is already swapped: every session picks the new key up at its")
        out("            next launch or revive. Re-run `romp keyswap --cycle…` once romp is up.")
        return 1
    body = _post(u, "/keycycle", {"sessions": [], "refresh": True} if refresh else {"sessions": []})   # the read
    if body.get("error") == "HTTP 404":
        # The one restart this feature genuinely needs: a kernel started before this code has no
        # /keycycle route AND no live key read, so it is still on the key it booted with.
        out("cycle       NOT DONE — the running kernel predates `romp keyswap` (no /keycycle route).")
        out("            Take the patch once with `romp refresh`, and every swap after that is")
        out("            restart-free. The file is already swapped.")
        return 1
    if not body.get("ok"):
        out("cycle       FAILED — %s" % (body.get("error") or body.get("detail") or "unknown"))
        return 1
    path = path or ks.service_env_path()
    source = ks.read_source(path)
    if _kind_differs(body, source):
        _mode_mismatch(body, out, source, "file", path)
        out("cycle       NOT DONE — the kernel's key source could not be verified; fix the issue above first")
        return 1
    if _compare(body, path, out, body.get("refreshed")):
        out("cycle       NOT DONE — the kernel's key source could not be verified; fix the issue above first")
        return 1
    expected_fp = body.get("sourceFp", body.get("keyFp") or "") or ""
    return _do_cycle(u, sessions, all_, out, expected_fp)


def _do_cycle(u, sessions, all_, out, expected_fp):
    """The cycle itself, once the read agreed: one POST naming the sessions (or all) with the source
    fingerprint the read gave, so a source that changes mid-request is refused by the kernel (409) or
    caught here; then the rows, a cycling row with the fingerprint its CLI launched on."""
    request = {"all": True} if all_ else {"sessions": sessions}
    request["expectedSourceFp"] = expected_fp
    body = _post(u, "/keycycle", request)
    if not body.get("ok"):
        out("cycle       FAILED — %s" % (body.get("error") or body.get("detail") or "unknown"))
        return 1
    if (body.get("sourceFp", body.get("keyFp") or "") or "") != expected_fp:
        out("cycle       FAILED — the key source changed during the request; check it before cycling again")
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
    if any(str(r.get("status")) == "working" for r in rows):
        out("            re-run --cycle for the skipped sessions once those are quiet")
    return 1 if any(str(r.get("status")).startswith("error:") for r in rows) else 0


def _not_done_unasked(rc, out):
    """The cycle could not even read the kernel: no kernel running (rc 0 from _ask; the report stands,
    the cycle does not), or an ask _ask already reported (an unusable port, a 404, a refusal)."""
    if rc == 0:
        out("cycle       NOT DONE: no running kernel found (is romp on? `romp status`). Nothing was cycled; a")
        out("            session's next launch or revive runs a new process anyway. Re-run `romp keyswap --cycle...`")
        out("            once romp is up for the running ones.")
    else:
        out("cycle       NOT DONE: see above. Nothing was cycled.")


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
    accepts after ROMP_SERVICE_ENV_FILE (service_env_path). The other-file hint then says so: its "unset
    the variable in this shell" otherwise names a variable such a shell never set, and its "install from
    this shell" remedy does not hold as written, because bin/romp-service resolves its SERVICE_ENV_FILE
    from ROMP_SERVICE_ENV_FILE only and never reads the alias: an alias-only shell installs the DEFAULT
    path into the unit or the plist, and the mismatch stands. The hint names the export that makes the
    remedy work."""
    primary = (os.environ.get("ROMP_SERVICE_ENV_FILE") or "").strip()
    return not primary and bool((os.environ.get("ROMP_SERVICE_ENV") or "").strip())


def _other_file(path, indent=0, alias=False):
    """The one explanation every MISMATCH hint shares for a kernel that reads ANOTHER service.env. The
    kernel resolves its path from ROMP_SERVICE_ENV_FILE as ITS environment sets it (kernel/keysource.py,
    service_env_path) and this shell from its own, so the two can read different files in either
    direction. The kernel's environment comes from the unit's Environment= and its drop-ins on Linux or
    the plist's EnvironmentVariables on macOS (bin/romp-service writes the variable there when the
    installing shell's path is not the default), the profile a shell-wrapped ExecStart sources, or the
    shell that ran `romp up`. The lines name the variable, this shell's path and those places, under
    either name the kernel's resolver reads (ROMP_SERVICE_ENV_FILE or its alias ROMP_SERVICE_ENV), then
    the remedy for each direction. Never a value. Unindented; the caller's lead-in ends with "another
    service.env:", and `indent` is the width of the pad the caller prints before each line. The path can
    be any length: when it would carry its sentence past WIDTH columns, pad included, the sentence stops
    at "reads" and the path follows whole on a line of its own, four columns deeper, so a path is never
    broken. `alias` (_path_alias) adds three lines after the remedy under a shell whose path comes from
    the alias: which variable this shell set, that `romp-service install` does not read it (bin/romp-service
    resolves ROMP_SERVICE_ENV_FILE only, so an alias-only install bakes the default path into the unit or
    the plist), and the export of ROMP_SERVICE_ENV_FILE that makes the install remedy work."""
    reads = "in their own environment; this shell reads"
    inline = "%s %s." % (reads, path)
    if indent + len(inline) <= WIDTH:
        where = (inline,)
    else:
        where = (reads, "    %s." % path)
    tail = (
        "This shell set the path under the alias ROMP_SERVICE_ENV, which `romp-service install`",
        "does not read: export ROMP_SERVICE_ENV_FILE with this shell's path (or prefix the",
        "install command with it) before installing from this shell.",
    ) if alias else ()
    return (
        "the kernel and this shell each resolve the service.env path from ROMP_SERVICE_ENV_FILE",
    ) + where + (
        "Look for it where the kernel's environment comes from, under ROMP_SERVICE_ENV_FILE or",
        "its alias ROMP_SERVICE_ENV: the unit's Environment= and its drop-ins (Linux) or the",
        "plist's EnvironmentVariables (macOS), where `romp-service install` writes it when the",
        "installing shell's path is not the default (and rewrites it from a shell with the",
        "wanted path); the profile a shell-wrapped ExecStart sources; or the shell that ran",
        "`romp up` (start it again with the path). If found, run this command with the same",
        "value, or change it there and restart the manager. If not found, the kernel reads the",
        "default path: unset the variable in this shell, or point the kernel at this file with",
        "`romp-service install` from this shell.",
    ) + tail


def _kind_word(kind):
    return _KIND_WORDS.get(kind or "", "no key source" if kind in ("none", "environment", "") else str(kind))


def _mode_mismatch(body, out, shell, where="file", path=None):
    """The kernel and this shell resolve DIFFERENT kinds. The kernel selects its source live, at every
    launch, judge call and read, from its own service.env and environment (kernel/keysource.py,
    select_source); this shell read its own service.env and, with no line there, its environment
    (_shell_source). So the two disagree when they read different service.env files (_other_file), when
    the line rides one side's environment alone (a supervised manager reads the file only; a foreground
    one reads the shell that started it), when the kernel predates the credential command (its answer
    carries no keySource), or when the file changed between the two reads. `shell` is this shell's source
    and `where` says whether it came from the file or the environment; an environment bullet is offered
    only for a side whose line can be in an environment: this shell's when its line rides its environment,
    the kernel's only when this shell's file has no source line at all, since a line in service.env
    outranks any environment in select_source and a kernel reading this shell's file would select that
    line too (with a line here, the kernel's environment explains nothing without another service.env,
    which is always listed). `path` is this shell's service.env path, the
    kernel's resolution (ks.service_env_path) unless a caller has it. Names variables, kinds, places and
    this shell's file path; never a value."""
    kmode = body.get("keySource")
    kfp = body.get("keyFp") or ""
    out("kernel      key source: %s%s" % (_kind_word(kmode) if kmode else "not reported",
                                          ("; reads " + _sha(kfp)) if kfp else ""))
    path = path or ks.service_env_path()
    out("MISMATCH    the kernel's key source is %s;" % (_kind_word(kmode) if kmode else "not reported (an older kernel)"))
    out("            this shell's is %s." % _kind_word(shell.kind))
    out("            The kernel selects its source live, from its own service.env and environment, at every launch,")
    out("            judge call and read. Usual causes:")
    out("            - the kernel reads another service.env:")
    pad = " " * 14
    for line in _other_file(path, len(pad), _path_alias()):
        out(pad + line)
    if where == "environment":
        out("            - this shell's environment carries %s and the kernel does not read it:" % ks.CMD_VAR)
        out("              a supervised manager (the login service) reads service.env only, and a foreground one reads the")
        out("              shell that started it. Put the line in service.env so every reader selects it.")
    if kmode in ("op", "command") and (where == "environment" or shell.kind == "none"):
        var = ks.CMD_VAR if kmode == "command" else ks.REF_VAR
        out("            - the kernel's environment carries %s (a foreground manager started from a shell that" % var)
        out("              exported it) and this shell's does not. Put the line in service.env, or start the manager")
        out("              from a shell without it.")
    if not kmode:
        out("            - the kernel predates the credential command: `romp refresh` restarts it on this code.")
    out("            - the file changed between the kernel's read and this shell's (a swap in progress): run this again.")
    return 1


# ---------------------------------------------------------------------------
# A credential command: the selector, this shell's run, the kernel's run, and the switch.
# ---------------------------------------------------------------------------

def _local(source):
    """This shell's own run of `source`'s command (and of the apiKeyHelper when the set carries no key),
    value-free: {"source", "snap" (envsource's record), "fp", "kind" ("key"|"helper"|"login"|""), "err"
    (why there is no fingerprint and it is a failure), "noHelper" (no fingerprint because none is
    configured: a login-billed installation, not a failure), "selector", "selErr"}."""
    snap = es.status(source)
    sel, sel_err = es.read_selector()
    st = {"source": source, "snap": snap, "fp": "", "kind": "", "err": "", "noHelper": "",
          "selector": sel, "selErr": sel_err}
    if snap.get("ok") is False:
        reason = snap.get("reason") or "failed"
        # the selector and configuration reasons name their subject already; a run's reason is the command's
        st["err"] = (reason if (reason.startswith("the selector") or reason.startswith(es.COMMAND_VAR))
                     else "the credential command " + reason)
    elif snap.get("hasKey"):
        st["fp"], st["kind"] = snap.get("keyFp") or "", "key"
    else:
        if not es.helper_command():
            st["kind"], st["noHelper"] = "login", es.helper_fingerprint(source=source)[1]   # nothing to run: the reason names the files
        else:
            hfp, hreason = es.helper_fingerprint(source=source)
            if hfp:
                st["fp"], st["kind"] = hfp, "helper"
            else:
                st["err"] = "the set carries no %s and the apiKeyHelper %s" % (es.KEY_VAR, hreason)
    return st


def _sel_word(token):
    """A selector token as the report may show it: by name when it is declared in ROMP_CREDENTIAL_NAMES,
    else by length only. An undeclared token could be anything, a pasted secret included."""
    if not token:
        return "(none)"
    return token if token in es.names() else "(undeclared, %d chars)" % len(token)


def _header(st, where, out):
    """The command report's local half: source, selector, candidates, set, live key. Returns 1 when this
    shell could not fingerprint anything it should have (the command or the helper failed)."""
    snap = st["snap"]
    place = (ks.service_env_path() if where == "file"
             else "this shell's environment; a supervised manager reads service.env only")
    out("key source  command %s   (%s in %s)" % (_sha(st["source"].fingerprint()), es.COMMAND_VAR, place))
    out("            the kernel runs it and injects the NAME=VALUE set it prints into every launch")
    sel_path = es.selector_path()
    if st["selErr"]:
        out("selector    UNREADABLE     %s: %s" % (sel_path, st["selErr"]))
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
            out("set         %s (%s)" % (_sha(snap.get("setFp")), _names_phrase(snap)))
        out("live key    UNAVAILABLE: %s" % st["err"])
        rc = 1
    else:
        out("set         %s (%s)" % (_sha(snap.get("setFp")), _names_phrase(snap)))
        if st["kind"] == "key":
            out("live key    %s   (this shell's run of the command: its %s line)" % (_sha(st["fp"]), es.KEY_VAR))
        elif st["kind"] == "helper":
            out("live key    %s   (this shell's run of the apiKeyHelper; the set carries no %s)"
                % (_sha(st["fp"]), es.KEY_VAR))
        else:
            out("live key    (none): the set carries no %s and %s; sessions bill the machine login, and a"
                % (es.KEY_VAR, st["noHelper"]))
            out("            cycle covers the role variables in the set")
    return rc


def _names_phrase(snap):
    names = list(snap.get("names") or [])
    return "%d name%s: %s" % (len(names), "" if len(names) == 1 else "s", ", ".join(names)) if names else "no names"


def _kernel_lines(body, st, where, out):
    """The command report's kernel half from a /keycycle read: what the kernel's own run yields, how many
    live sessions launched on which fingerprint, and MISMATCH when the two sides disagree: on the kind
    (_mode_mismatch), on the source (the kernel runs another command text), or on the credential or set
    fingerprint the same command gave (a selector or environment difference). Returns the exit code the
    comparison deserves. Never a value; the kernel's command text is not known here and is not asked for."""
    # a kernel that answers no keySource at all predates the command kind (the field arrived with it)
    if body.get("keySource") is None or _kind_differs(body, st["source"]):
        return _mode_mismatch(body, out, st["source"], where)
    ksrc = body.get("sourceFp") or ""
    mine = st["source"].fingerprint()
    if ksrc and ksrc != mine:
        out("kernel      source %s (its own service.env and environment)" % _sha(ksrc))
        out("MISMATCH    the kernel runs another command: its source is %s, this shell's %s." % (_sha(ksrc), _sha(mine)))
        out("            Usual causes:")
        out("            - the kernel reads another service.env:")
        pad = " " * 14
        for line in _other_file(ks.service_env_path(), len(pad), _path_alias()):
            out(pad + line)
        if where == "environment":
            out("            - this shell's environment carries a %s that is not the line the kernel reads:" % es.COMMAND_VAR)
            out("              a supervised manager reads service.env only. Put the wanted line there.")
        else:
            out("            - the kernel's environment carries another %s (a foreground manager started from a" % es.COMMAND_VAR)
            out("              shell that exported it) and its service.env has no line, so that one governs.")
        return 1
    kfp = body.get("keyFp") or ""
    kerr = body.get("keyErr") or ""
    kkind = body.get("keyKind") or ""
    launched = body.get("launched") or {}
    note = _refreshed_note(body.get("refreshed"), kfp)
    rc = 0
    if kerr and not kfp:
        out("kernel      UNAVAILABLE: %s%s" % (kerr, (" (%s)" % note) if note else ""))
        rc = 1
    elif kerr:
        out("kernel      reads %s (its own run%s; the latest run failed (%s), so it stands on the previous set)"
            % (_sha(kfp), (", " + note) if note else "", kerr))
        rc = 1
    elif not kfp and kkind == "login":
        # no key in the set and no apiKeyHelper configured: the machine login bills, there is nothing
        # to fingerprint, and that is not a failure; the cycle still re-presents the role variables
        out("kernel      reads no key (its own run%s): sessions bill the machine login; a cycle covers the role"
            % ((", " + note) if note else ""))
        out("            variables (set %s); %d live session(s) launched with no key"
            % (_sha(body.get("setFp") or ""), launched.get("", 0)))
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
        out("            Usual causes: the command's output depends on its environment (a store session or token the manager")
        out("            has and this shell lacks, or the reverse); the kernel's environment carries other values of")
        out("            ROMP_CREDENTIAL_NAMES, ROMP_CREDENTIAL_SELECTOR_FILE or ROMP_CREDENTIAL_TIMEOUT_S than this shell (each")
        out("            is read from the process environment first, then service.env, and")
        out("            a manager's environment holds the copy loaded at its start, so a changed line reaches it at the next")
        out("            manager restart); the two resolve different selector files; or CLAUDE_CONFIG_DIR differs (the")
        out("            apiKeyHelper the kernel fingerprints is the one its own settings name).")
    return 1


def _rotate_hint(out):
    declared = es.names()
    out("")
    out("rotate:     romp keyswap <name>  writes the selector%s and re-runs the command; then"
        % ((" (one of: %s)" % ", ".join(declared)) if declared else ""))
    out("            romp keyswap --cycle-all  so quiet sessions reconnect. A new value behind the same")
    out("            name: romp keyswap --cycle-all  alone (it re-runs the command first).")


def _report_command(source, where, out, refresh=False):
    """The bare report under a command; --refresh makes the kernel re-run first."""
    st = _local(source)
    rc = _header(st, where, out)
    body, krc, _u = _ask(out, refresh)
    if body is None:
        if krc == 0:
            out("kernel      not running; it runs the command itself when it is")
        rc = rc or krc
    else:
        rc = max(rc, _kernel_lines(body, st, where, out))
    _rotate_hint(out)
    return rc


def _cycle_command(sessions, all_, source, where, out, header=True):
    """The cycle under a command: this shell's run, the kernel's re-run (refresh), the compare, then the
    reconnects, guarded by the source fingerprint the read gave. A local failure or a MISMATCH stops it
    before any reconnect."""
    st = _local(source)
    rc = _header(st, where, out) if header else (1 if st["err"] else 0)
    if rc:
        out("cycle       NOT DONE: this shell could not fingerprint the credential, so there is nothing to")
        out("            compare the kernel's run against. Fix the command (or the helper) first, then cycle.")
        return 1
    body, krc, u = _ask(out, True)
    if body is None:
        _not_done_unasked(krc, out)
        return 1
    if _kernel_lines(body, st, where, out):
        out("cycle       NOT DONE: the kernel is not on the credential this shell reads, so a reconnect would")
        out("            re-present what it already has. Fix the mismatch above first, then cycle.")
        return 1
    return _do_cycle(u, sessions, all_, out, body.get("sourceFp") or "")


def _restore_selector(old, sel_err, target, name):
    """Put the selector back after a switch that switched nothing, and SAY what happened: the old token,
    or an empty file where there was none (the target, so a dotfiles link keeps pointing where it did).
    Returns the clause for the selector line: "put back to <old>" only when the write succeeded; an old
    selector that could not be read before the switch cannot be put back, and a failed write leaves the
    new name in place, and both say so rather than claim a restore."""
    if sel_err:
        return ("NOT put back: the old selector could not be read before the switch (%s), so the file now holds %s"
                % (sel_err, name))
    try:
        if old:
            es.write_selector(old)
        else:
            with open(target, "w", encoding="utf-8"):
                pass
    except OSError as e:
        return "NOT put back (errno %s writing the selector file), so it still holds %s" % (getattr(e, "errno", None) or "?", name)
    return "put back to %s" % _sel_word(old)


def _switch(name, source, where, out):
    """`romp keyswap <name>` under a command. The name is checked before anything runs: a token, and
    declared in ROMP_CREDENTIAL_NAMES when that is set; an undeclared name is refused and NEVER echoed (a
    key pasted where a name was expected must not reach a terminal). Then: this shell runs the command on
    the OLD selector, writes the new token, runs again, and confirms the fingerprint moved. A switch that
    moves nothing (the command ignores $1, both names resolve to one credential, or the command fails for
    the new name) is undone, the selector goes back, and exits 1: the world is as it was. A switch that
    moved asks the kernel to re-run too and reports its view. The env file is never written here."""
    if not es.valid_selector(name):
        sys.stderr.write("romp keyswap: a selector is one name: letters, digits, '.', '_' or '-', up to 64\n"
                         "             characters (%d characters given); nothing switched. With a credential command\n"
                         "             selected, <name> is a selector for the command, not a profile.\n" % len(name))
        return 2
    if not es.names():
        # nothing declared: no name can be checked, so none is written, and the argument is not echoed
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
        out("            nothing to switch: `romp keyswap --refresh` re-runs the command; `romp keyswap --cycle-all`")
        out("            moves the sessions onto whatever it prints now")
        return 0
    before = _local(source)
    try:
        w = es.write_selector(name)
    except OSError as e:
        sys.stderr.write("romp keyswap: the selector file could not be written (errno %s): %s; nothing switched.\n"
                         % (getattr(e, "errno", None) or "?", es.selector_path()))
        return 1
    es.invalidate("switch")
    after = _local(source)
    was = _sel_word(old)
    if after["err"]:
        undo = _restore_selector(old, sel_err, w["target"], name)
        out("selector    %s -> %s, %s" % (was, name, undo))
        out("live key    UNAVAILABLE: %s" % after["err"])
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
        out("            selector as $1, `my-cmd \"$1\"` rather than a bare `my-cmd`, and the two names must resolve")
        out("            to different credentials.")
        return 1
    out("selector    %s -> %s" % (was, name))
    out("live key    %s   (was %s)" % (_sha(after["fp"]), _sha(before["fp"])))
    if (after["snap"].get("setFp") or "") != (before["snap"].get("setFp") or ""):
        out("set         %s   (was %s)" % (_sha(after["snap"].get("setFp")), _sha(before["snap"].get("setFp"))))
    body, krc, _u = _ask(out, True)
    if body is None:
        if krc == 0:
            out("kernel      not running; its first read runs the command with the new selector")
        return krc
    return _kernel_lines(body, after, where, out)


def parse_args(argv):
    """(source, cycle-list, cycle-all, error, refresh). Positional: at most one source name or path. The
    error for a second positional counts the arguments and never echoes them: a key value typed where a
    name was expected must not reach stderr (the rule every other surface here follows)."""
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
    path = ks.service_env_path()
    shell, where = _shell_source(path)
    if shell.kind == "command":
        # A credential command is selected (the file's line, or this shell's ROMP_CREDENTIAL_COMMAND with no
        # line in the file): <name> is a selector for the command, the report runs the command here, and
        # the cycle re-runs it in the kernel first. The env file is never written on this arm.
        if src_arg:
            rc = _switch(src_arg, shell, where, out)
            if rc or not (cycle or cycle_all):
                return rc
            return _cycle_command(cycle, cycle_all, shell, where, out, header=False)
        if cycle or cycle_all:
            return _cycle_command(cycle, cycle_all, shell, where, out)
        return _report_command(shell, where, out, refresh)
    args = [src_arg] if src_arg else []
    if not args:
        # Read-only report. Deliberately the no-argument behaviour: a swap is a real change and
        # should be asked for by name.
        out("service.env %s" % path)
        current = ks.read_source(path)
        out("live key    %s" % _source_label(current))
        _candidates(path, out)
        try:
            current.validate()
        except ks.KeySourceError as exc:
            out("configuration invalid — %s" % exc)
            return 1
        if cycle or cycle_all:
            return _cycle(cycle, cycle_all, out, path, refresh)
        rc = _kernel_check(path, out, refresh)
        out("")
        out("swap with:  romp keyswap <name> [--cycle <session,…> | --cycle-all]")
        return rc
    src = ks.sibling_path(args[0], path)
    if not os.path.exists(src):
        sys.stderr.write("romp keyswap: no such key file: %s\n" % src)
        sys.stderr.write("             keep one per key beside the env file (e.g. %s.lowprio, chmod 600)\n"
                         % os.path.basename(path))
        return 2
    new = ks.read_source(src)
    try:
        new.validate()
    except ks.KeySourceError as exc:
        sys.stderr.write("romp keyswap: %s has an invalid key source — %s (file untouched)\n"
                         % (src, exc))
        return 2
    if not new.configured or not new.value:
        # Refuse rather than write an empty key: the CLI reads an empty ANTHROPIC_API_KEY as
        # "API-key mode, no key" and every session would then fail to authenticate.
        sys.stderr.write("romp keyswap: %s has no usable ROMP_CREDENTIAL_COMMAND=, ROMP_API_KEY_REF= or %s= line — "
                         "nothing to swap to (file untouched)\n" % (src, ks.KEY_VAR))
        return 2
    cur = ks.read_source(path)
    # A pre-existing reference may still sit beside a legacy plaintext key. Selecting that same
    # reference also migrates the file: remove the leftover secret instead of treating it as done.
    if new == cur and not (new.kind == "op" and _legacy_key_present(path)):
        out("service.env %s" % path)
        out("live key    %s — already this key source, nothing rewritten" % _source_label(cur))
    else:
        try:
            res = ks.write_source(new, path)
        except OSError as e:
            sys.stderr.write("romp keyswap: could not rewrite %s: %s\n" % (path, e))
            return 1
        # Verify from the FILE, not from what we meant to write: re-read and fingerprint it.
        landed = ks.read_source(path)
        if landed != new:
            sys.stderr.write("romp keyswap: the rewrite did not land (file reads %s, expected %s) — "
                             "check %s by hand\n" % (_source_label(landed), _source_label(new), path))
            return 1
        out("service.env %s" % res["path"])
        if res.get("target") and res["target"] != res["path"]:
            out("            (a link: written through to %s)" % res["target"])
        out("key source  %s -> %s  (%d lines, mode %o%s)"
            % (_source_label(res["old"]), _source_label(new), res["lines"], res["mode"],
               ", tightened from a group/other-readable mode" if res["tightened"] else ""))
        out("source      %s" % src)
    out("effect      new and revived sessions use this key source; no manager restart needed")
    if new.kind == "op":
        out("            the kernel retrieves the key through op at runtime; no key was copied to disk")
    elif new.kind == "command":
        out("            the kernel runs the command at its next read and injects the set it prints; no key was copied to disk")
    if cycle or cycle_all:
        return _cycle(cycle, cycle_all, out, path, refresh)
    rc = _kernel_check(path, out, refresh)
    out("running     sessions keep the key they launched with — reconnect them with")
    out("            romp keyswap %s --cycle-all   (or --cycle <session,…>)" % args[0])
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

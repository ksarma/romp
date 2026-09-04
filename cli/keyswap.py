#!/usr/bin/env python3
"""romp-keyswap — point every romp session at another API key, without restarting anything.

`romp keyswap` rewrites ONE line of the manager's env file (`~/.config/romp/service.env`): the
`ANTHROPIC_API_KEY=` line, taken from a sibling file you keep beside it (`service.env.highprio`,
`service.env.lowprio`, …). The kernel reads that line live, per session launch, so:

  * a session started or revived from then on bills the new key with no further action;
  * a session already running keeps the key its CLI process started with, because the key rides
    the launch environment — `--cycle <names>` or `--cycle-all` reconnects those sessions so they
    re-present the new one, each resuming its own conversation with its history intact;
  * the manager itself never restarts, so no session loses an open turn and no subagent is killed.

No key value is ever printed, logged or passed over the wire. The only rendered form is the first
12 hex of its sha256 ("sha256:1a2b3c…"), which is enough to see that the swap landed and that the
kernel reads the same value this command wrote.

Usage:
    romp keyswap                            # what is live now, and which candidates exist
    romp keyswap lowprio                    # rewrite the key line from service.env.lowprio
    romp keyswap lowprio --cycle web,api    # …and reconnect those two sessions onto it
    romp keyswap lowprio --cycle-all        # …and reconnect every live key-billed session
    romp keyswap /path/to/other.env         # an explicit file instead of a sibling name
"""
import json
import os
import sys
import urllib.error
import urllib.request
from importlib.machinery import SourceFileLoader
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# The SAME module the kernel reads the key with, not a second copy of the rules: writer and reader
# then cannot disagree about which file holds the key, which line wins, or how it is parsed.
ks = SourceFileLoader("romp_keysource", str(ROOT / "kernel" / "keysource.py")).load_module()

KPORTS = ["http://127.0.0.1:29855", "http://127.0.0.1:7878", "http://127.0.0.1:7432"]


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
    for u in KPORTS:
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
        out("candidates  none — keep one file per key beside it, e.g. %s.lowprio (chmod 600),"
            % os.path.basename(path))
        out("            each a single %s=… line" % ks.KEY_VAR)
        return
    out("candidates")
    for n in names:
        k = ks.read_key(ks.sibling_path(n, path))
        mark = "  <- live" if (k and k == live) else ""
        out("  %-14s %s%s" % (n, _fp(k) if k else "(no %s line)" % ks.KEY_VAR, mark))


def _cycle(sessions, all_, out):
    """Reconnect the named sessions through the kernel, and report what it did per session."""
    u = _kernel()
    if not u:
        out("cycle       NOT DONE — no running kernel found (is romp on? `romp status`).")
        out("            The file is already swapped: every session picks the new key up at its")
        out("            next launch or revive. Re-run `romp keyswap --cycle…` once romp is up.")
        return 1
    body = _post(u, "/keycycle", {"all": True} if all_ else {"sessions": sessions})
    if not body.get("ok"):
        out("cycle       FAILED — %s" % (body.get("error") or body.get("detail") or "unknown"))
        return 1
    out("kernel      reads %s" % (("sha256:" + body["keyFp"]) if body.get("keyFp") else "(none)"))
    rows = body.get("rows") or []
    if not rows:
        out("cycle       no sessions matched")
        return 0
    for r in rows:
        out("  %-14s %s" % (str(r.get("session"))[:14], _explain(str(r.get("status") or ""))))
    return 0


def _explain(status):
    return {
        "cycling": "reconnecting now (idle) or at the end of its turn — history kept",
        "login":   "skipped: bills the machine login, not the key",
        "dormant": "not running — its next launch reads the new key",
        "unknown": "no such session",
    }.get(status, status)


def parse_args(argv):
    """(source, cycle-list, cycle-all, error). Positional: at most one source name or path."""
    src, cycle, cycle_all, err = "", [], False, ""
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--cycle-all":
            cycle_all = True
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
        elif not src:
            src = a
        else:
            err = err or "one source at a time (got %s and %s)" % (src, a)
        i += 1
    return src, cycle, cycle_all, err


def main(argv, out=None):
    out = out or (lambda line: sys.stdout.write(line + "\n"))
    src_arg, cycle, cycle_all, err = parse_args(list(argv))
    if err:
        sys.stderr.write("romp keyswap: %s\n" % err)
        return 2
    args = [src_arg] if src_arg else []
    path = ks.service_env_path()
    if not args:
        # Read-only report. Deliberately the no-argument behaviour: a swap is a real change and
        # should be asked for by name.
        out("service.env %s" % path)
        out("live key    %s" % _fp(ks.read_key(path)))
        _candidates(path, out)
        if cycle or cycle_all:
            return _cycle(cycle, cycle_all, out)
        out("")
        out("swap with:  romp keyswap <name> [--cycle <session,…> | --cycle-all]")
        return 0
    src = ks.sibling_path(args[0], path)
    if not os.path.exists(src):
        sys.stderr.write("romp keyswap: no such key file: %s\n" % src)
        sys.stderr.write("             keep one per key beside the env file (e.g. %s.lowprio, chmod 600)\n"
                         % os.path.basename(path))
        return 2
    new = ks.read_key(src)
    if not new:
        # Refuse rather than write an empty key: the CLI reads an empty ANTHROPIC_API_KEY as
        # "API-key mode, no key" and every session would then fail to authenticate.
        sys.stderr.write("romp keyswap: %s has no %s= line — nothing to swap to (file untouched)\n"
                         % (src, ks.KEY_VAR))
        return 2
    cur = ks.read_key(path)
    if new == cur:
        out("service.env %s" % path)
        out("live key    %s — already this key, nothing rewritten" % _fp(cur))
    else:
        try:
            res = ks.write_key(new, path)
        except OSError as e:
            sys.stderr.write("romp keyswap: could not rewrite %s: %s\n" % (path, e))
            return 1
        # Verify from the FILE, not from what we meant to write: re-read and fingerprint it.
        landed = ks.read_key(path)
        if landed != new:
            sys.stderr.write("romp keyswap: the rewrite did not land (file reads %s, expected %s) — "
                             "check %s by hand\n" % (_fp(landed), _fp(new), path))
            return 1
        out("service.env %s" % res["path"])
        out("key line    %s -> %s  (%d lines, mode %o%s)"
            % (_fp(res["old"]), _fp(new), res["lines"], res["mode"],
               ", tightened from a group/other-readable mode" if res["tightened"] else ""))
        out("source      %s" % src)
    out("effect      new and revived sessions bill this key immediately; no manager restart needed")
    if cycle or cycle_all:
        return _cycle(cycle, cycle_all, out)
    out("running      keep the key they launched with — reconnect them with")
    out("             romp keyswap %s --cycle-all   (or --cycle <session,…>)" % args[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

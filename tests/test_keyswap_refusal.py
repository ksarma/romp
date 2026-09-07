#!/usr/bin/env python3
"""The fork's keyswap contract (the user 2026-09-05): this fork does not write API keys to files.

Upstream's `romp keyswap <name>` rewrites the `ANTHROPIC_API_KEY=` line of the manager's env file
from a sibling file (`service.env.<name>`). tests/test_keyswap.py carries upstream's tests for the
parts the fork keeps — the live read, the bare report, `--cycle`. This file pins what the fork changes:

  NamedSwapRefused — in FILE mode `romp keyswap <name>` exits 2 with one fixed message, before the file
    is read or a kernel is dialed; no flag lets it through; the bare report's guidance names the cycle,
    never a file to create; the CLI carries no call that writes the key. (In COMMAND mode the same
    argument selects a declared credential by writing the selector file — a name, never a key — which
    tests/test_keyswap.py's KeyswapCliCommandMode pins.)
  HelperSessionsConverge — in COMMAND mode (ROMP_CREDENTIAL_COMMAND set; kernel/envsource.py) a
    session the kernel handed NO key but whose CLI reported one at init (apiKeySource: the
    apiKeyHelper) is stamped at connect with the fingerprint of the helper's output (envsource runs
    the configured helper and hashes inside), and `SdkBackend.cycle_key` converges on it: the same
    fingerprint reads "current", a rotation behind the helper reads "cycling" once and "current"
    after; a refusal on a session still stamped with the pre-rotation output re-runs neither the
    command nor the helper; a refresh landing between a connect's read of the set and its helper
    fingerprint leaves that fingerprint stored stale, not served as current. This replaces the fork's earlier always-reconnect "helper" outcome (2026-09-05, the same
    day): upstream reads such a session as login-billed and skips it, which made `--cycle-all` a
    no-op on a box whose every session bills through the helper; the always-reconnect answer fixed
    that but churned every quiet helper session on every run. In FILE mode the compare is upstream's
    (a non-keyed session reads "login"). The role variables the set injects converge the same way.
  EnvFileCredentialWarning — at backend construction, a credential-shaped line in the env file
    (`ANTHROPIC_API_KEY`, any `*_API_KEY`, any `*_TOKEN`, with a non-empty value) under a declared
    `ROMP_EXPECTED_AUTH` is said once, loudly (the problem ring), naming the file and the variable
    NAME — never the value. Undeclared, nothing is said.

Synthetic keys (`sk-ant-TEST-…`), synthetic sids, temp paths only; the command-mode values are
assembled at run time ("romp-test-fixture-" + a uuid) and the fake command and helper are scripts
written into a temp dir. The env-file path is pointed at a temp dir before the loads so nothing here
can read the machine's real one; conftest keeps ROMP_CREDENTIAL_* unset until a test sets them.
"""
import io
import json
import os
import re
import sys
import tempfile
import unittest
import uuid
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_SERVICE_ENV_FILE"] = os.path.join(os.environ["XDG_STATE_HOME"], "no-such-service.env")
os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]

sb = load_source("romp_sdk_backend_keyswap_refusal", os.path.join(BIN, "romp_sdk_backend.py"))
cli = load_source("romp_keyswap_cli_refusal", os.path.join(BIN, "romp-keyswap"))
ks = sb._keysrc
assert ks is cli.ks, "the CLI and the kernel must read the key through one module"
es = sb._envsrc


def fixture_value(tag=""):
    return "romp-test-fixture-%s%s" % (tag + "-" if tag else "", uuid.uuid4().hex)


OLD_KEY = "sk-ant-TEST-0000"
NEW_KEY = "sk-ant-TEST-1111"
SID = "11111111-2222-3333-4444-555555555501"


# The one explanation the three MISMATCH hints share for a kernel that reads ANOTHER service.env
# (cli/keyswap.py, _other_file): the file-mode fingerprint MISMATCH, the command-mode MISMATCH's other-file
# cause and the file-mode MISMATCH under a shell whose file carries the line render these lines word for
# word, each with its own indent. Pinned here so a rewording of one hint that leaves the others behind fails.
# The remedy is given in BOTH directions: the variable found where the kernel's environment comes from, and
# found nowhere (the kernel reads the default path; an install from before the installer wrote the line).
# The search names both spellings the kernel's resolver reads, ROMP_SERVICE_ENV_FILE and its alias
# ROMP_SERVICE_ENV (kernel/keysource.py, service_env_path), since a drop-in, a profile or the `romp up`
# shell can carry either; before, it named the primary alone, and a kernel whose path came from the alias
# was searched for under the wrong name (review find, 2026-09-06).
# The path line is the one line the CLI renders two ways: inline while its sentence fits WIDTH under the
# hint's indent, else the sentence stops at "reads" and the path follows whole on a line of its own
# (other_file_lines mirrors the rule, so a long temp directory changes nothing asserted here).
OTHER_FILE = (
    "the kernel and this shell each resolve the service.env path from ROMP_SERVICE_ENV_FILE",
    "in their own environment; this shell reads %s.",
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

# The restart-and-reload block (cli/keyswap.py, _restart_block) the same three hints render ONCE each, after
# their causes, so no report gives the mechanics twice: the restart per platform, the reload a unit or drop-in
# line takes first, `romp-service install` in place of `launchctl kickstart -k` for a plist line (the kickstart
# does not re-read the plist; the install waits for the old job to leave launchd, so never the bare pair), the
# Linux install's missing restart, and the cost of either install: it rewrites the unit or the plist wholesale
# (bin/romp-service, write_unit / write_plist), so a line added to either by hand is gone and the next kernel
# pins file mode, while a drop-in is not touched.
RESTART_BLOCK = (
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

# Under a shell whose path comes from the alias ROMP_SERVICE_ENV (kernel/keysource.py accepts it after
# ROMP_SERVICE_ENV_FILE) the path line is followed by these two, so "unset the variable in this shell" names a
# variable the shell has set and the install remedy holds: bin/romp-service resolves the alias the same way and
# writes ROMP_SERVICE_ENV_FILE into the unit or the plist (tests/romp-service.bats pins the installer's half).
# Before, the installer read the primary alone, so an install from such a shell wrote no override line and
# the kernel kept the default path with the remedy done (review find, 2026-09-06).
ALIAS_NOTE = (
    "This shell set it under the alias ROMP_SERVICE_ENV, which the installer reads too; the",
    "line it writes into the unit or the plist is ROMP_SERVICE_ENV_FILE.",
)

# compared against whitespace-flattened text: the rendered block wraps it across two lines
INSTALL_COST = "Either rewrite drops a line added to the unit or the plist by hand; drop-ins survive, so put your own lines in service.env or a drop-in."


# the column every hint line stays within, indent included; the CLI's own pin is held to it below
WIDTH = 100


def other_file_lines(path, indent, alias=False):
    """OTHER_FILE as the CLI lays it out under a pad `indent` wide, unindented: the path inline while its
    sentence fits WIDTH, else the sentence to "reads" and the path whole, four columns deeper, on its own
    line (cli._other_file's rule); ALIAS_NOTE after the path when this shell's path came from the alias."""
    lines = []
    for line in OTHER_FILE:
        if "%s" not in line:
            lines.append(line)
            continue
        if len(indent) + len(line % path) <= WIDTH:
            lines.append(line % path)
        else:
            lines.append(line.split(" %s.")[0])
            lines.append("    %s." % path)
        if alias:
            lines += list(ALIAS_NOTE)
    return lines


def other_file_block(path, indent, alias=False):
    """The shared lines as one hint renders them: this shell's path filled in, each line under `indent`."""
    return "\n".join(indent + line for line in other_file_lines(path, indent, alias))


def restart_block(indent):
    """The restart block as one hint renders it, each line under `indent`."""
    return "\n".join(indent + line for line in RESTART_BLOCK)


def render_shapes(env, path=None):
    """Every MISMATCH shape the CLI can print, rendered by CALLING its report functions with fabricated
    inputs (a temp env file, a made-up kernel answer), so the text asserted on is the text a reader sees,
    format arguments and concatenations included. `env` is an _Env with its temp file at `env.path`.
    `path`, when given, is the service.env path the hints NAME in place of the temp file's — fabricated,
    of a chosen length, never opened — so a width check does not depend on where the temp directory is;
    the mode is still read from the temp file (es.command), which is why the path is passed to the report
    functions rather than put in the environment. Returns {shape name: rendered text}; leaves the file
    and the environment as they were."""
    named = path or env.path
    shapes = {}
    said = []
    cli._compare(ks.fingerprint(NEW_KEY), named, said.append)
    shapes["file-mode fingerprint"] = "\n".join(said)
    said = []
    cli._mode_mismatch({"keySource": "command", "keyFp": ks.fingerprint(NEW_KEY)}, said.append, path)
    shapes["command-mode kernel"] = "\n".join(said)
    body = open(env.path).read()
    had = os.environ.pop("ROMP_CREDENTIAL_COMMAND", None)
    try:
        env.write_env("ROMP_PERF=1\nROMP_CREDENTIAL_COMMAND=romp-test-fixture-cmd \"$1\"\n")
        es._reset()
        said = []
        cli._mode_mismatch({"keySource": "file", "keyFp": ""}, said.append, path)
        shapes["file-mode kernel, the file carries the line"] = "\n".join(said)
        env.write_env("ROMP_PERF=1\n")
        os.environ["ROMP_CREDENTIAL_COMMAND"] = "romp-test-fixture-cmd \"$1\""
        es._reset()
        said = []
        cli._mode_mismatch({"keySource": "file", "keyFp": ""}, said.append, path)
        shapes["file-mode kernel, this shell's environment carries the line"] = "\n".join(said)
        # the command-mode fingerprint MISMATCH (_kernel_lines): the kernel's run and this shell's disagree
        # and the selectors agree, so the hint lists the two environments' differences
        said = []
        st = {"err": "", "fp": ks.fingerprint(OLD_KEY), "kind": "key", "snap": {"setFp": "a" * 12},
              "selector": "", "selErr": "", "noHelper": ""}
        cli._kernel_lines({"keySource": "command", "keyFp": ks.fingerprint(NEW_KEY), "setFp": "a" * 12,
                           "selector": "", "launched": {}}, st, said.append)
        shapes["command-mode fingerprint"] = "\n".join(said)
    finally:
        os.environ.pop("ROMP_CREDENTIAL_COMMAND", None)
        if had is not None:
            os.environ["ROMP_CREDENTIAL_COMMAND"] = had
        env.write_env(body)
        es._reset()
    return shapes


# The reload rule the reference and the CLI's hints are held to. A unit Environment= line or a plist
# EnvironmentVariables pair is part of the loaded service definition, which a manager restart re-applies, so
# advice that says "restart" about one and not the reload sends the reader to a restart that changes nothing.
# The unit of the check is the SENTENCE: a sentence that names both the concept and a restart must name the
# reload in that sentence (`reload`, `reloads`, `reloaded`, `daemon-reload`) or point at where it is given (the
# reference's restart section by its anchor; the CLI's "(below)", which every hint resolves with the restart
# block). A block whose concept and restart sit in different sentences must carry one of those somewhere in
# it. A block is a paragraph or one bullet of a list, so one bullet's reload covers no neighbour; a block is
# selected by the concept however worded (the ports paragraph says "unit" and "bakes in"; the install's cost
# says "a line added to the unit or the plist by hand", "added to either by hand", "a plist you edited by
# hand"), not by the literal `Environment=`. Presence anywhere in the block was the earlier rule, and it passed
# a bare restart for a unit line beside a mention of the install for another reason (round-7 verification);
# the "added to" and "by hand" forms were outside the regex while the docs used them, so a bare restart in
# those sentences passed (round-8 verification; the mutations are pinned below).
CONCEPT = re.compile(r"Environment=|EnvironmentVariables|unit'?s? (?:own )?environment|baked into the unit|"
                     r"unit bakes|(?:unit|plist) line|line in the (?:unit|plist)|in the unit\b|in the plist\b|"
                     r"plist's|added to (?:the )?(?:unit|plist|either)\b|(?:unit|plist)(?: or the plist)? by hand|"
                     r"(?:unit|plist) you (?:added|edited)", re.I)
RESTART_WORD = re.compile(r"\brestart")
POINTER = re.compile(r"#two-things-still-need-a-restart|\(below\)")
RELOAD_WORD = re.compile(r"reload|#two-things-still-need-a-restart|\(below\)")


def text_blocks(text):
    """Paragraphs, and within a paragraph one block per list bullet."""
    return [b for p in re.split(r"\n\s*\n", text) for b in re.split(r"\n(?=\s*[-*] )", p) if b.strip()]


def reload_violations(text):
    """The blocks of `text` the rule selects (concept + restart) that break it, as (block, offender) pairs:
    the sentence that names both and no reload; "" when no sentence names both and the block as a whole lacks
    the reload; "macOS" for the macOS half, which wants `romp-service install` named in a selected block that
    names macOS or the plist and points nowhere (`launchctl kickstart -k` restarts the job as launchd loaded it
    and does not re-read the plist, so the install IS the reload there)."""
    bad = []
    for b in text_blocks(text):
        flat = " ".join(b.split())
        if not (CONCEPT.search(flat) and RESTART_WORD.search(flat)):
            continue
        both = [s for s in re.split(r"(?<=[.!?])\s+", flat) if CONCEPT.search(s) and RESTART_WORD.search(s)]
        if both:
            bad += [(flat, s) for s in both if not RELOAD_WORD.search(s)]
        elif not RELOAD_WORD.search(flat):
            bad.append((flat, ""))
        if ("macOS" in flat or "plist" in flat.lower()) and not POINTER.search(flat) \
                and "romp-service install" not in flat:
            bad.append((flat, "macOS"))
    return bad


class _Env(unittest.TestCase):
    """A temp env file at the path every reader resolves, the declaration cleared, the one-shot reset."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.path = os.path.join(self.d, "service.env")
        self._before = {v: os.environ.get(v) for v in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV",
                                                       "ROMP_EXPECTED_AUTH", "ANTHROPIC_API_KEY")}
        os.environ["ROMP_SERVICE_ENV_FILE"] = self.path
        os.environ["ROMP_SERVICE_ENV"] = self.path
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        os.environ.pop("ANTHROPIC_API_KEY", None)
        self._said = sb._CREDENTIAL_LINE_SAID
        sb._CREDENTIAL_LINE_SAID = False
        ks._CACHE = ((), "")

    def tearDown(self):
        for v, was in self._before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        sb._CREDENTIAL_LINE_SAID = self._said
        ks._CACHE = ((), "")

    def write_env(self, body):
        with open(self.path, "w") as fh:
            fh.write(body)
        os.chmod(self.path, 0o600)
        ks._CACHE = ((), "")

    def sibling(self, name, body):
        with open(self.path + "." + name, "w") as fh:
            fh.write(body)
        os.chmod(self.path + "." + name, 0o600)


class NamedSwapRefused(_Env):
    def setUp(self):
        super().setUp()
        self.write_env("ROMP_PERF=1\n%s=%s\nROMP_EXPECTED_AUTH=key\n" % (ks.KEY_VAR, OLD_KEY))
        self.sibling("lowprio", "%s=%s\n" % (ks.KEY_VAR, NEW_KEY))
        self.posted, self.dialed = [], []
        self._saved = (cli._kernel, cli._post, ks.write_key)
        cli._kernel = lambda: self.dialed.append(1) or None
        cli._post = lambda u, p, b: self.posted.append((p, b)) or {"ok": True, "keyFp": "", "rows": []}

        def never(*a, **k):
            raise AssertionError("write_key must not be reached from the CLI")
        ks.write_key = never

    def tearDown(self):
        cli._kernel, cli._post, ks.write_key = self._saved
        super().tearDown()

    def run_cli(self, *argv):
        said, buf, was = [], io.StringIO(), sys.stderr
        sys.stderr = buf
        try:
            rc = cli.main(list(argv), out=said.append)
        finally:
            sys.stderr = was
        return rc, "\n".join(said), buf.getvalue()

    def test_a_named_source_exits_2_with_the_fixed_message_before_reading_anything(self):
        mtime = os.stat(self.path).st_mtime_ns
        rc, out, err = self.run_cli("lowprio")
        self.assertEqual(rc, 2)
        self.assertEqual(err, cli.REFUSAL, "one fixed message, so a reword is a deliberate edit")
        self.assertEqual(out, "", "nothing on stdout: the refusal is the whole answer")
        self.assertEqual(ks.read_key(self.path), OLD_KEY)
        self.assertEqual(os.stat(self.path).st_mtime_ns, mtime, "the file is not even rewritten in place")
        self.assertEqual(self.dialed, [], "no kernel is dialed for a refused request")
        self.assertEqual(self.posted, [])

    def test_the_message_says_where_keys_live_and_what_to_run_instead(self):
        m = cli.REFUSAL
        self.assertIn("does not write API keys to files", m, "a policy the code can stand behind, not a claim about one box")
        self.assertNotIn("this installation", m)
        self.assertIn("apiKeyHelper", m)
        self.assertIn("manager's\n             environment", m)
        self.assertIn("romp keyswap --cycle-all", m)
        self.assertIn("romp refresh", m)
        self.assertIn("skips sessions billed through the apiKeyHelper", m,
                      "honest about file mode: a non-keyed session reads as the login there and is not cycled")
        self.assertIn("--cycle-all in command mode (set ROMP_CREDENTIAL_COMMAND", m)
        self.assertNotIn("service.env.", m, "never a sibling-file recipe")
        for key in (OLD_KEY, NEW_KEY):
            self.assertNotIn(key, m)

    def test_a_missing_or_keyless_source_is_refused_the_same_way(self):
        # the refusal does not depend on the filesystem: an unknown name, a file with no key line and a
        # real candidate all get the same answer, and none of upstream's per-case messages
        self.sibling("empty", "ROMP_PERF=1\n")
        for name in ("nosuch", "empty", "lowprio"):
            rc, out, err = self.run_cli(name)
            self.assertEqual(rc, 2, name)
            self.assertEqual(err, cli.REFUSAL, name)
            self.assertNotIn("no such key file", err)
        self.assertEqual(ks.read_key(self.path), OLD_KEY)

    def test_a_name_with_a_cycle_is_refused_with_it_and_nothing_cycles(self):
        for argv in (["lowprio", "--cycle-all"], ["lowprio", "--cycle", "web"], ["--cycle-all", "lowprio"]):
            rc, _out, err = self.run_cli(*argv)
            self.assertEqual(rc, 2, argv)
            self.assertEqual(err, cli.REFUSAL, argv)
        self.assertEqual(self.posted, [], "the name made it a swap request; no reconnect rides along")

    def test_an_explicit_path_is_refused_too(self):
        rc, _out, err = self.run_cli(os.path.join(self.d, "other.env"))
        self.assertEqual(rc, 2)
        self.assertEqual(err, cli.REFUSAL)

    def test_the_bare_report_points_at_the_cycle_and_never_at_a_file_to_create(self):
        os.unlink(self.path + ".lowprio")
        rc, out, err = self.run_cli()
        self.assertEqual(rc, 0)
        self.assertEqual(err, "")
        self.assertIn("candidates  none (this fork does not write API keys to files; the named swap is disabled)", out)
        self.assertNotIn("this installation", out)
        self.assertIn("romp keyswap --cycle-all", out)
        self.assertIn("key-billed sessions reconnect", out, "the file-mode cycle reaches key-billed sessions")
        self.assertIn("they cycle in command mode", out, "…helper-billed ones are named as cycling in command mode")
        self.assertNotIn("swap with:", out)
        self.assertNotIn("chmod 600", out, "upstream's line told the operator to create one file per key")
        self.assertNotIn("keep one file per key", out)
        self.assertNotIn(OLD_KEY, out)

    def test_a_cycle_with_no_kernel_does_not_claim_a_swap_happened(self):
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("no running kernel", out)
        self.assertNotIn("already swapped", out, "nothing is ever swapped here")
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: {"ok": False, "error": "HTTP 404"}
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("romp refresh", out)
        self.assertNotIn("already swapped", out)

    def test_the_helper_status_word_is_gone_from_the_cli(self):
        # cycle_key's always-reconnect "helper" outcome was replaced by fingerprint convergence (kernel
        # side: HelperSessionsConverge below), so the CLI has no explanation for it: an unexplained
        # status prints its raw word, and no row text promises a reconnect on every run
        self.assertEqual(cli._explain("helper"), "helper")
        src = open(os.path.join(ROOT, "cli", "keyswap.py")).read()
        self.assertNotIn("reconnects on every run", src)
        self.assertNotIn("once per rotation", src)
        self.assertIn("apiKeyHelper", cli._explain("cycling") + cli.REFUSAL, "the helper is still named where it bills")

    def test_the_re_run_hint_names_the_skipped_rows_and_promises_current(self):
        # every status converges now (a session already moved reads "current" on the re-run), so the
        # hint names only the rows skipped for in-flight work and says exactly that
        cli._kernel = lambda: "http://127.0.0.1:29855"
        rows = [{"session": "web", "status": "working"}, {"session": "api", "status": "current"},
                {"session": "tests", "status": "working"}]
        cli._post = lambda u, p, b: {"ok": True, "keyFp": ks.fingerprint(OLD_KEY), "rows": rows}   # the compare step passes
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 0)
        self.assertIn("re-run --cycle web,tests once quiet; sessions already on this key read \"current\"", out)
        self.assertNotIn("helper-billed", out)
        self.assertNotIn("Name only those", out)
        rows[:] = [{"session": "api", "status": "current"}]
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertNotIn("re-run --cycle", out, "no skipped row, no hint")

    def test_a_cycling_row_carries_the_fingerprint_its_client_launched_on(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        fp = ks.fingerprint(NEW_KEY)                       # a fingerprint taken at run time, not a literal
        rows = [{"session": "web", "status": "cycling", "from": fp},
                {"session": "api", "status": "cycling", "from": ""}]
        cli._post = lambda u, p, b: {"ok": True, "keyFp": ks.fingerprint(OLD_KEY), "rows": rows}
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 0)
        self.assertIn("  web            reconnecting now — history kept (from sha256:%s)" % fp, out)
        self.assertIn("  api            reconnecting now — history kept\n", out + "\n")

    def test_refresh_in_file_mode_is_a_re_read_and_the_report_says_so(self):
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: self.posted.append((p, b)) or {
            "ok": True, "keyFp": ks.fingerprint(OLD_KEY), "keySource": "file", "rows": [],
            "refreshed": {"from": "deadbeefcafe", "to": ks.fingerprint(OLD_KEY), "err": ""}}
        rc, out, _err = self.run_cli("--refresh")
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.posted, [("/keycycle", {"sessions": [], "refresh": True})])
        self.assertIn("kernel      reads sha256:%s (re-read now: was sha256:deadbeefcafe)" % ks.fingerprint(OLD_KEY), out)
        self.assertNotIn("MISMATCH", out)

    def test_a_kernel_in_command_mode_under_a_file_mode_shell_is_a_mismatch(self):
        # the kernel's environment carries ROMP_CREDENTIAL_COMMAND and this shell's (and service.env) do
        # not: the report says which side is which and what makes them agree
        cli._kernel = lambda: "http://127.0.0.1:29855"
        fp = ks.fingerprint(NEW_KEY)
        cli._post = lambda u, p, b: {"ok": True, "keyFp": fp, "keySource": "command", "rows": []}
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("kernel      reads sha256:%s in COMMAND mode" % fp, out)
        self.assertIn("MISMATCH    the kernel is in command mode and this shell is not: the kernel pinned command mode\n"
                      "            when it started; this shell reads no ROMP_CREDENTIAL_COMMAND now. The kernel got the\n"
                      "            line from one of:", out)
        # the /keycycle answer cannot say WHERE the kernel got the line (the manager's environment, a
        # service.env line removed since the kernel started, another service.env, or the shell that ran
        # `romp up` all read the same), so the report asserts no cause: it lists the places, each with
        # its remedy
        self.assertNotIn("the kernel's environment carries", out, "a cause to check, not a fact")
        # the manager's environment is TWO causes with two remedies: a service.env line the manager loaded
        # goes at the restart, which re-reads the file; a line in the unit, a drop-in or the profile a
        # shell-wrapped ExecStart sources is re-applied by a restart, so it is removed where it is first,
        # the definition reloaded, and the manager restarted after, with the commands in the block below
        self.assertIn("            - service.env as the manager loaded it at its start, which every kernel inherits: the\n"
                      "              line is gone from the file this shell reads, so restart the manager (the restart\n"
                      "              re-reads the file); `romp refresh` alone keeps the mode", out)
        self.assertIn("            - the unit's Environment=, a drop-in, or the profile a shell-wrapped ExecStart sources\n"
                      "              (Linux), or the plist's EnvironmentVariables (macOS): a manager restart re-applies\n"
                      "              these, so remove the line there first, reload the definition, then restart (below)", out)
        self.assertNotIn("the unit's Environment=, or service.env as the manager loaded it", out,
                         "one cause with one remedy would send a unit line's owner to a restart that re-applies it")
        # the kernel may read ANOTHER service.env: kernel/keysource.py resolves the path from ROMP_SERVICE_ENV_FILE
        # wherever the kernel's environment sets it (the installer's unit or plist line is one source; a drop-in,
        # a profile or the shell that ran `romp up` are others), the answer carries no path, and this shell's is
        # named, with the places to look per platform and the remedy in both directions: the block the file-mode
        # fingerprint MISMATCH renders too (OTHER_FILE), under the bullet
        self.assertIn("            - another service.env:\n" + other_file_block(self.path, " " * 14), out)
        self.assertNotIn("the installer carries", out, "the installer is one source of the variable, not the cause")
        self.assertNotIn("check the unit for that variable", out, "the unit is the Linux place; the plist is the macOS one")
        self.assertEqual(ks.service_env_path(), self.path, "the CLI names the path the kernel's own resolver gives this environment")
        self.assertIn("            - service.env, edited since the kernel read it at its start: `romp refresh`", out)
        self.assertIn("            - the shell that ran `romp up`, which exported it: stop that `romp up`; start it again\n"
                      "              from a shell without the line", out)
        # the mechanics ONCE, after the places (RESTART_BLOCK): the unit-or-plist bullet and the other-file block
        # both say "(below)" and both resolve to this one copy, so the report gives the reload, the restart and
        # the install's cost a single time. Round 7's report gave them under the unit-or-plist bullet and again
        # inside the other-file block, 31 lines at up to 122 columns
        self.assertIn(restart_block(" " * 12) + "\n            To stay in command mode, put the line back in service.env instead.", out)
        flat = " ".join(out.split())
        self.assertEqual(flat.count("The manager restart is"), 1)
        self.assertEqual(flat.count("daemon-reload"), 1)
        self.assertEqual(flat.count("kickstart -k"), 1)
        self.assertEqual(flat.count("romp-service install"), 3,
                         "twice in the other-file block (the installer writes the variable; the install from this shell "
                         "points the kernel at this file) and once as the plist reload")
        self.assertLess(flat.rfind("(below)"), flat.index("The manager restart is"), "every pointer precedes the block")
        # the macOS half: the plist's EnvironmentVariables are part of the loaded job definition, which `launchctl
        # kickstart -k` restarts without re-reading the plist, so the job is booted out and bootstrapped again,
        # and the hint names `romp-service install` for that and never the bare pair: bootout only starts the old
        # job's teardown, and a bootstrap issued while a manager drains its sessions is refused (Input/output
        # error) with the old job gone and no agent loaded, so the installer polls `launchctl print` until the job
        # has left launchd before it bootstraps (bin/romp-service, install; the reader mid-keyswap is the one with
        # sessions to drain)
        self.assertIn("`systemctl --user daemon-reload` first. A plist edit takes `romp-service install`\n"
                      "            instead: the kickstart does not re-read the plist; the install rewrites it and reloads\n"
                      "            the job, waiting for the old job to leave launchd before it bootstraps the new one (a\n"
                      "            bootstrap issued sooner is refused, Input/output error, and no agent is left loaded).", out)
        self.assertNotIn("launchctl bootstrap", out, "the pair is never given: the install waits, a reader typing it would not")
        self.assertNotIn("launchctl bootout", out)
        svc = open(os.path.join(BIN, "romp-service"), encoding="utf-8").read()
        self.assertIn('LABEL="com.romp.manager"', svc)
        install = svc.split("case \"${1:-status}\" in")[1].split("uninstall)")[0]
        bootout = install.index('"$LAUNCHCTL" bootout "gui/$(id -u)/$LABEL"')
        bootstrap = install.index('"$LAUNCHCTL" bootstrap "gui/$(id -u)" "$PLIST"')
        self.assertLess(bootout, bootstrap)
        self.assertIn('"$LAUNCHCTL" print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || break', install[bootout:bootstrap],
                      "the install waits for the old job to leave launchd before it bootstraps")
        # `romp-service install` is named for what it does per platform: on macOS the plist rewrite and the
        # waited reload, on Linux a unit rewrite and a systemd reload with no restart of a running manager
        # (daemon-reload, enable --now)
        self.assertIn("On Linux the install rewrites the unit and reloads systemd but restarts no running\n"
                      "            manager, so restart after it.", out)
        self.assertIn("systemctl --user daemon-reload\n            systemctl --user enable --now romp-manager.service", svc)
        self.assertNotIn("systemctl --user restart", install, "install restarts no running manager on Linux")
        # and for what it costs on BOTH platforms: the rewrite drops a line added to the unit or the plist by
        # hand, so a Linux operator in command mode through a hand-added unit line who follows the install hint
        # is told what they lose and where the line survives (a drop-in, or service.env). Round 7 said it for
        # the plist alone, and the Linux operator's next kernel pinned file mode with nothing said
        self.assertIn(INSTALL_COST, flat)
        self.assertNotIn("which drops a line added by hand", out, "the cost was stated for the plist alone")
        self.assertNotIn("`romp refresh` restarts the kernels into file mode", out)
        self.assertIn("put the line back in service.env instead", out)
        rc, out, _err = self.run_cli("--cycle-all")
        self.assertEqual(rc, 1)
        self.assertIn("cycle       NOT DONE", out)

    def test_a_kernel_in_file_mode_under_a_file_that_carries_the_line_names_the_other_file_cause(self):
        # the file this shell reads carries ROMP_CREDENTIAL_COMMAND and the kernel is in file mode. The
        # first cause is a line added since the kernel started, and `romp refresh` is the whole fix; the
        # second is that the kernel reads ANOTHER service.env (its environment sets ROMP_SERVICE_ENV_FILE to
        # another path, through the installer's unit or plist line or any other source), which no kernel
        # restart mends, so the block names it with this shell's path and the places to look per platform.
        # Called at the block: the report's header would run the command
        self.write_env("ROMP_PERF=1\nROMP_CREDENTIAL_COMMAND=romp-test-fixture-cmd \"$1\"\n")
        cli.es._reset()
        said = []
        try:
            rc = cli._mode_mismatch({"keySource": "file", "keyFp": ""}, said.append)
        finally:
            cli.es._reset()
        out = "\n".join(said)
        self.assertEqual(rc, 1)
        self.assertIn("kernel      reads (none) in FILE mode", out)
        self.assertIn("MISMATCH    the kernel is in file mode and this shell is not: ROMP_CREDENTIAL_COMMAND is set in\n"
                      "            service.env and was not when the kernel started.", out)
        self.assertIn("so a line added there needs no manager restart). Until then\n            the kernel injects no set.", out)
        # the other-file block, then the restart block, each once
        self.assertIn("            If the kernel is still in file mode after `romp refresh`, it reads another service.env:\n"
                      + other_file_block(self.path, " " * 12) + "\n" + restart_block(" " * 12), out)
        self.assertEqual(out.count("The manager restart is"), 1)
        self.assertNotIn("the installer carries", out)
        self.assertNotIn("systemctl", out.split("reads another service.env:")[0], "adding the line is never a manager restart")
        self.assertNotIn("set in this shell's", out)

    def test_the_file_mode_fingerprint_mismatch_explains_the_other_file_cause_as_the_mode_mismatches_do(self):
        # a file-mode kernel on another fingerprint. The hint's other-file cause used to say the service was
        # installed with another env-file path the kernel's environment does not carry (re-run the install,
        # then restart): one direction, and a kernel whose ROMP_SERVICE_ENV_FILE comes from a drop-in, a
        # profile or the `romp up` shell was re-installed and restarted for nothing, with no pointer to the
        # place. The three hints render the one explanation (cli._other_file): the variable, this shell's
        # path, the places per platform, the remedy per place and the reload a unit or plist line takes
        cli._kernel = lambda: "http://127.0.0.1:29855"
        cli._post = lambda u, p, b: {"ok": True, "keyFp": ks.fingerprint(NEW_KEY), "keySource": "file", "rows": []}
        rc, out, _err = self.run_cli()
        self.assertEqual(rc, 1)
        self.assertIn("MISMATCH    the kernel is not reading this file's key. Usual causes: the file is unreadable to the\n"
                      "            kernel, the file has no %s line and the kernel still holds its startup\n"
                      "            key, or the kernel reads another service.env:\n" % ks.KEY_VAR
                      + other_file_block(self.path, " " * 12) + "\n" + restart_block(" " * 12), out)
        for gone in ("installed with", "does not carry", "re-run", "then restart the manager)", "wherever its"):
            self.assertNotIn(gone, out, gone)
        block = other_file_block(self.path, "")
        for fact in ("ROMP_SERVICE_ENV_FILE", self.path, "under ROMP_SERVICE_ENV_FILE or\nits alias ROMP_SERVICE_ENV:",
                     "the unit's Environment= and its", "drop-ins (Linux)", "plist's EnvironmentVariables (macOS)",
                     "where `romp-service install` writes it when the\ninstalling shell's path is not the default",
                     "(and rewrites it from a shell with the\nwanted path)", "the profile a shell-wrapped ExecStart sources",
                     "the shell that ran\n`romp up` (start it again with the path)",
                     "If found, run this command with the same\nvalue, or change it there and restart the manager (below).",
                     "If not found, the kernel\nreads the default path: unset the variable in this shell, or point the "
                     "kernel at this\nfile with `romp-service install` from this shell."):
            self.assertIn(fact, block, fact)
        self.assertEqual(block.count("ROMP_SERVICE_ENV_FILE"), 2, "the resolver's line and the search")
        self.assertEqual(block.count("alias ROMP_SERVICE_ENV"), 1, "the search names the alias the kernel also reads")
        mechanics = restart_block("")
        for fact in ("`systemctl --user restart romp-manager` (Linux)", "`launchctl\nkickstart -k gui/$(id -u)/com.romp.manager` (macOS)",
                     "a unit or drop-in edit takes\n`systemctl --user daemon-reload` first", "A plist edit takes `romp-service install`\ninstead",
                     "the kickstart does not re-read the plist", "waiting for the old job to leave launchd before it bootstraps",
                     "On Linux the install rewrites the unit and reloads systemd but restarts no running\nmanager, so restart after it"):
            self.assertIn(fact, mechanics, fact)
        self.assertIn(INSTALL_COST, " ".join(mechanics.split()))
        self.assertNotIn("launchctl boot", block + mechanics, "the macOS reload is the install; no bare pair")
        self.assertNotIn(OLD_KEY, out)
        self.assertNotIn(NEW_KEY, out)
        self.assertEqual(ks.service_env_path(), self.path, "the path named is the one the kernel's own resolver gives this environment")
        # the same lines, word for word, under the command-mode MISMATCH's bullet, and its restart block after
        # the places
        said = []
        cli._mode_mismatch({"keySource": "command", "keyFp": ks.fingerprint(NEW_KEY)}, said.append)
        self.assertIn("            - another service.env:\n" + other_file_block(self.path, " " * 14), "\n".join(said))
        self.assertIn(restart_block(" " * 12), "\n".join(said))
        self.assertEqual(cli._other_file(self.path), tuple(other_file_block(self.path, "").split("\n")))
        self.assertEqual(cli._restart_block(), RESTART_BLOCK)

    def test_a_second_positional_is_counted_never_echoed(self):
        # a key value typed where a name was expected must not reach stderr
        rc, out, err = self.run_cli("lowprio", "sk-ant-TEST-9999")
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")
        self.assertIn("one source at a time (2 positional arguments given)", err)
        self.assertNotIn("sk-ant-TEST-9999", err)
        self.assertNotIn("lowprio", err)
        self.assertEqual(cli.parse_args(["a", "b", "c"])[3], "one source at a time (3 positional arguments given)")

    def test_the_cli_carries_no_call_that_writes_the_key(self):
        # no escape hatch: not a flag, not a dead branch — the only writer of the key line is upstream's
        # module function, and nothing under bin/ or cli/ calls it
        for rel in ("cli/keyswap.py", "bin/romp-keyswap", "bin/romp"):
            src = open(os.path.join(ROOT, rel)).read()
            self.assertNotIn("write_key(", src, rel)


class HelpAndDocsAgree(unittest.TestCase):
    """`romp help`'s keyswap row, docs/reference.md's command table and the two READMEs spell the SAME
    invocation — one form, so an operator reading any of them types what the others describe."""

    FORM = "romp keyswap [<name>] [--refresh] [--cycle <session,…>|--cycle-all]"

    def _read(self, rel):
        return open(os.path.join(ROOT, rel), encoding="utf-8").read()

    def test_the_help_row_spells_the_whole_form(self):
        self.assertIn('_romp_cmd "%s" romp-keyswap' % self.FORM, self._read("bin/romp"))

    def test_the_reference_table_and_the_readmes_spell_the_same_form(self):
        escaped = self.FORM.replace("|", "\\|")                    # a table cell escapes the pipe
        for rel in ("docs/reference.md", "cli/README.md", "bin/README.md"):
            text = self._read(rel)
            if rel == "bin/README.md":
                continue                                           # its row names the binary, not the invocation
            self.assertIn("`%s`" % escaped, text, rel)
        self.assertIn("`romp keyswap <name>`", self._read("bin/README.md"))

    def test_every_restart_advice_about_a_unit_or_plist_line_names_the_reload(self):
        # a unit Environment= line or a plist EnvironmentVariables pair is part of the loaded service
        # definition, which a manager restart re-applies; advice that says "restart" about one and not the
        # reload sends the reader to a restart that changes nothing. Two paragraphs of the reference did
        # (the `romp refresh --quiet` paragraph and the keyswap section's list of places named a bare
        # restart), so the property (reload_violations: sentence-scoped, with the macOS half) is pinned over
        # the whole reference. The floor is today's count of selected blocks, so a rewrite that drops a block
        # out of selection fails here
        ref = self._read("docs/reference.md")
        hits = [b for b in text_blocks(ref) if CONCEPT.search(b) and RESTART_WORD.search(b)]
        self.assertGreaterEqual(len(hits), 6, "the blocks this covers:\n" + "\n---\n".join(h[:120] for h in hits))
        self.assertEqual(reload_violations(ref), [])
        self.assertTrue(any("#two-things-still-need-a-restart" in b for b in hits), "the by-reference form is exercised")
        # the section the others point at carries both reloads and the wait
        section = " ".join(ref.split("#### Two things still need a restart")[1].split("\n#")[0].split())
        self.assertIn("`systemctl --user daemon-reload` after editing a unit or a drop-in, then the restart", section)
        self.assertIn("the reload is `romp-service install`", section)
        # the same for the CLI's hints about such a line (rendered and checked in RenderedMismatches; the
        # phrases here pin the source): the mode MISMATCH under a command-mode kernel, the one under a shell
        # whose environment alone carries the line, the fingerprint MISMATCH's causes, the other-file block and
        # the restart block all three MISMATCHes share
        src = self._read("cli/keyswap.py")
        for phrase in ("the unit's Environment=, a drop-in, or the profile a shell-wrapped ExecStart sources",
                       "A drop-in line reaches them at the manager restart after `systemctl --user",
                       "a line changed or removed there, or one in the",
                       "the unit's Environment= and its"):
            self.assertIn(phrase, src, phrase)
        for phrase in ("these, so remove the line there first, reload the definition, then restart (below)",
                       "daemon-reload` instead; not a line added to the unit or the plist by hand, which the",
                       "and a unit or plist line reaches that restart only once the definition is reloaded:",
                       "daemon-reload on Linux, `romp-service install` on macOS, which rewrites the plist as the",
                       "`systemctl --user daemon-reload` first. A plist edit takes `romp-service install`",
                       "instead: the kickstart does not re-read the plist; the install rewrites it and reloads"):
            self.assertIn(phrase, src, phrase)
        self.assertNotIn("reaches them at the next manager restart (`systemctl --user restart romp-manager`)", src)
        self.assertNotIn("a line in the unit's own Environment= or the plist's EnvironmentVariables", src,
                         "a hand-added unit or plist line is not a place the hint sends the line to: the install rewrites both")

    def test_the_reload_rule_is_sentence_scoped(self):
        # the mutations the round-7 verification ran against the block-level rule, which passed them all: a
        # bare restart for a unit or plist line beside a reload named for another reason in the same block
        good = ("A line in the unit's own `Environment=` is re-applied by a restart, so remove it, run "
                "`systemctl --user daemon-reload`, then restart the manager.")
        by_ref = ("A line in the unit's own `Environment=` takes effect at the next manager restart (see [Two things "
                  "still need a restart](#two-things-still-need-a-restart)).")
        cli_form = "- a unit line: remove it, reload the definition, then restart (below)"
        for text in (good, by_ref, cli_form):
            self.assertEqual(reload_violations(text), [], text)
        m2 = ("A line in the unit's own `Environment=` takes effect at the next manager restart (`systemctl --user "
              "restart romp-manager`). The install runs `systemctl --user daemon-reload` for its own unit.")
        m2b = ("A line in the plist's `EnvironmentVariables` (as `romp-service install` wrote it) takes effect at the "
               "next manager restart: `launchctl kickstart -k gui/$(id -u)/com.romp.manager`.")
        m2c = ("A line in the unit's own `Environment=` takes effect at the next manager restart (`systemctl --user "
               "restart romp-manager`). The ports are under [Two things still need a "
               "restart](#two-things-still-need-a-restart).")
        kick = ("A line in the plist's `EnvironmentVariables` is reloaded by `launchctl kickstart -k` at the next "
                "manager restart.")                       # a reload named, and the wrong one
        neighbour = "- a plist line: `romp-service install`, which reloads the job\n- a unit line: restart the manager"
        for text in (m2, m2b, m2c, kick, neighbour):
            self.assertTrue(reload_violations(text), text)
        for text in (m2, m2b):
            flat = " ".join(text.split())
            self.assertTrue("romp-service install" in flat or "daemon-reload" in flat,
                            "the block-level rule these replace saw only presence, and passed this")
        # the wording the reference uses for the install's cost, each turned into a bare restart: none matched
        # the concept until round 8's verification (the regex knew "in the unit", not "added to the unit")
        by_hand = ("A line you added to the unit or the plist by hand takes effect at the next manager restart.",
                   "A line added to the unit by hand takes effect at the next manager restart (`systemctl --user "
                   "restart romp-manager`).",
                   "The install rewrites both; a line added to either by hand reaches the kernel at the next manager "
                   "restart.",
                   "A plist you edited by hand takes effect at the next manager restart.")
        for text in by_hand:
            self.assertTrue(reload_violations(text), text)
            self.assertTrue(CONCEPT.search(text), text)

    # the reference's four sentences on the install's cost, as written (the left side; a rewording lands here
    # too), and each turned into the bare restart a regression would write. The pristine reference passes and
    # every mutation fails, so the property covers the sentences round 8 added and not only the older wordings
    COST_SENTENCES = (
        ("Either rewrite drops a\nline you added to the unit or the plist by hand; a drop-in survives it (see\n"
         "[Two things still need a restart](#two-things-still-need-a-restart)).",
         "A line you added to the unit or the plist by hand takes effect at the next manager restart."),
        ("a line added to the unit or the plist by hand does not\nsurvive `romp-service install`, which rewrites both",
         "a line added to the unit or the plist by hand reaches the kernel at the next manager restart"),
        ("The rewrite drops a line added to the unit by hand, as the\nplist rewrite does; a drop-in survives it, so a "
         "line of your own belongs in\n`service.env` or a drop-in.",
         "A line added to the unit by hand takes effect at the next manager restart (`systemctl --user restart "
         "romp-manager`)."),
        ("rewrites the unit's or the plist's line and drops\n  a line added to either by hand; a drop-in survives it "
         "and takes the reload\n  under [Two things still need a restart](#two-things-still-need-a-restart))",
         "rewrites the unit's or the plist's line; a line added to either by hand takes effect at the next manager "
         "restart)"),
    )

    def test_a_bare_restart_in_any_cost_sentence_of_the_reference_fails_the_rule(self):
        ref = self._read("docs/reference.md")
        self.assertEqual(reload_violations(ref), [])
        for written, bare in self.COST_SENTENCES:
            self.assertEqual(ref.count(written), 1, "the reference's sentence moved or was reworded: " + written[:60])
            mutated = ref.replace(written, bare)
            self.assertTrue(reload_violations(mutated), "a bare restart passed: " + bare)

    def test_the_launchd_reload_is_romp_service_install_and_never_the_bare_pair(self):
        # bin/romp-service's install waits between bootout and bootstrap: bootout only starts the old job's
        # teardown, a manager draining live sessions takes seconds to exit, and a bootstrap issued while it
        # drains is refused (Input/output error) with the old job gone and no agent loaded, which is how two
        # installs ended before the wait (bin/romp-service, install). The reader mid-keyswap has sessions to
        # drain, so the CLI names `romp-service install` as the macOS reload and never the pair (the rendered
        # shapes are checked in RenderedMismatches; this is the source backstop, over every string literal in
        # the CLI that is not a docstring, so a formatted `out("… %s" % x)` line or a tuple line counts too),
        # and wherever the reference gives the pair by hand the `launchctl print` wait sits between the two
        # commands with the reason beside it
        import ast
        src = self._read("cli/keyswap.py")
        tree = ast.parse(src)
        docstrings = set()
        for node in ast.walk(tree):
            body = getattr(node, "body", None)
            if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
                docstrings.add(id(body[0].value))
        literals = [n.value for n in ast.walk(tree)
                    if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings]
        self.assertGreater(len(literals), 150, "the literals the reader can see")
        rendered = "\n".join(literals)
        for pair in ("launchctl bootstrap", "launchctl bootout", "bootout then bootstrap", "bootstrap gui/"):
            self.assertNotIn(pair, rendered, pair)
        self.assertIn("A plist edit takes `romp-service install`", rendered)
        self.assertIn("`romp-service install` on macOS, which rewrites the plist", rendered)
        self.assertIn("instead: the kickstart does not re-read the plist; the install rewrites it and reloads", rendered)
        ref = " ".join(self._read("docs/reference.md").split())          # the reference wraps a command across lines
        given = list(re.finditer(r"`launchctl bootstrap gui/", ref))
        self.assertEqual(len(given), 1, "the pair is given by hand in one place, the section the others point at")
        for m in given:
            bootout = ref.rfind("`launchctl bootout gui/", 0, m.start())
            self.assertGreater(bootout, -1, "a bootstrap given with no bootout before it")
            self.assertIn("`launchctl print gui/", ref[bootout:m.start()], "bootout then bootstrap with no wait between")
            self.assertIn("until it fails", ref[bootout:m.start()])
            self.assertIn("Input/output error", ref[bootout - 1500:m.start()], "the reason for the wait")
        self.assertNotIn("launchctl bootstrap gui/", " ".join(src.split()))

    def test_the_docs_show_the_command_mode_report_with_placeholder_fingerprints(self):
        ref = self._read("docs/reference.md")
        for line in ("key source  command (ROMP_CREDENTIAL_COMMAND is set)", "candidates  hp <- selected, lp",
                     "selector    hp -> lp", "re-run --cycle tests once quiet; sessions already on this key read \"current\""):
            self.assertIn(line, ref)
        import re
        for fp in re.findall(r"sha256:([0-9a-f]{12})", ref):
            # a placeholder fingerprint repeats a short pattern (low entropy): never something that reads
            # as a real digest, so the scanner that guards this repo has nothing to flag
            self.assertLessEqual(len(set(fp)), 6, fp)
        self.assertIn("#installing-without-keys-on-disk", self._read("docs/install.md"))


class RenderedMismatches(_Env):
    """Every MISMATCH shape the CLI prints, rendered by calling its report functions with fabricated inputs
    (render_shapes), held to what a reader depends on: at most 100 columns, the one exception a service.env
    path too long for its sentence, which goes whole on a line of its own; the two shared blocks once each,
    so no report gives the reload, the restart and the install twice; the install's cost beside every
    install remedy, on both platforms; the other-file cause in both directions; the reload rule the
    reference is held to; never the bare launchd pair; never a key value. Round 7's file-mode fingerprint
    MISMATCH gave the install and restart instructions inside the other-file block and, in the command-mode
    report, again under the unit-or-plist bullet, at up to 122 columns; its `never the bare pair` pin read
    `out("…")` literals from the source and so saw none of the formatted lines."""

    def setUp(self):
        super().setUp()
        self.write_env("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        self.shapes = render_shapes(self)
        of = " ".join(other_file_block(self.path, "").split())
        self.shared = {k: v for k, v in self.shapes.items() if of in " ".join(v.split())}

    def test_five_shapes_render_and_three_share_the_other_file_cause(self):
        self.assertEqual(sorted(self.shapes), ["command-mode fingerprint", "command-mode kernel", "file-mode fingerprint",
                                               "file-mode kernel, the file carries the line",
                                               "file-mode kernel, this shell's environment carries the line"])
        self.assertEqual(sorted(self.shared), ["command-mode kernel", "file-mode fingerprint",
                                               "file-mode kernel, the file carries the line"])
        for name, text in self.shapes.items():
            self.assertIn("MISMATCH", text, name)
        self.assertEqual(ks.read_key(self.path), OLD_KEY, "rendering leaves the file as it was")
        self.assertNotIn("ROMP_CREDENTIAL_COMMAND", os.environ)

    # the hints name this shell's service.env path, whose length is the environment's (the temp directory
    # under a long TMPDIR made the line 124 columns), so the width is held around a FABRICATED path of a
    # known length: short, and inline; long, and on a line of its own
    SHORT_PATH = "/srv/romp/service.env"
    LONG_PATH = "/srv/" + "/".join(["romp-" + "x" * 27] * 5) + "/" + "y" * 18 + "/service.env"

    def test_every_line_is_at_most_100_columns(self):
        self.assertEqual(len(self.SHORT_PATH), 21)
        self.assertEqual(cli.WIDTH, WIDTH, "the CLI's pin is the one this test holds it to")
        shapes = render_shapes(self, self.SHORT_PATH)
        self.assertEqual(sorted(shapes), sorted(self.shapes), "the same five shapes")
        for name, text in shapes.items():
            for line in text.split("\n"):
                self.assertLessEqual(len(line), 100, "%s: %r" % (name, line))
            self.assertLessEqual(len(text.split("\n")), 35, name)
        for name in sorted(self.shared):
            self.assertIn("in their own environment; this shell reads %s.\n" % self.SHORT_PATH, shapes[name] + "\n",
                          name + ": a path that fits stays in its sentence")

    def test_a_path_too_long_for_its_sentence_goes_whole_on_its_own_line(self):
        # only the line that IS the path may pass 100 columns; every prose line stays within, the sentence
        # keeps its words, and the path is never broken. Under a real temp directory the same shapes are
        # asserted word for word by the other tests through other_file_block, which mirrors the rule
        self.assertEqual(len(self.LONG_PATH), 200)
        shapes = render_shapes(self, self.LONG_PATH)
        short = render_shapes(self, self.SHORT_PATH)          # the inline layout, whatever the temp directory
        self.assertEqual(sorted(shapes), sorted(self.shapes))
        for name, text in shapes.items():
            lines = text.split("\n")
            wide = [line for line in lines if len(line) > 100]
            if name in self.shared:
                self.assertEqual([w.strip() for w in wide], [self.LONG_PATH + "."], "%s: %r" % (name, wide))
                at = lines.index(wide[0])
                self.assertTrue(lines[at - 1].endswith("in their own environment; this shell reads"), lines[at - 1])
                self.assertEqual(len(wide[0]) - len(wide[0].lstrip()), len(lines[at - 1]) - len(lines[at - 1].lstrip()) + 4,
                                 name + ": the path sits four columns deeper than its sentence")
                self.assertTrue(lines[at + 1].lstrip().startswith("Look for it where"), lines[at + 1])
                self.assertEqual(len(lines), len(short[name].split("\n")) + 1, name + ": one line more than inline")
                self.assertIn("this shell reads %s. Look for it" % self.LONG_PATH, " ".join(text.split()),
                              name + ": the sentence reads the same flattened")
            else:
                self.assertEqual(wide, [], name)
                self.assertNotIn(self.LONG_PATH, text, name)
                self.assertEqual(text, short[name], name + ": no path named, so the length changes nothing")
            self.assertEqual(reload_violations(text), [], name)
        for indent in (" " * 12, " " * 14):
            self.assertIn(other_file_block(self.LONG_PATH, indent), shapes["command-mode kernel" if len(indent) == 14
                                                                              else "file-mode fingerprint"])
        # the rule's edge: the longest path that still fits its sentence under the 12-column indent, and one
        # character more
        room = 100 - 12 - len("in their own environment; this shell reads .")
        fits = "/" + "p" * (room - 1)
        self.assertEqual(cli._other_file(fits, 12)[1], "in their own environment; this shell reads %s." % fits)
        self.assertEqual(cli._other_file(fits + "p", 12)[1:3],
                         ("in their own environment; this shell reads", "    %sp." % fits))
        self.assertEqual(cli._other_file(fits, 14)[1:3], ("in their own environment; this shell reads", "    %s." % fits),
                         "the same path under the deeper indent no longer fits")

    def test_the_boundary_paths_render_within_100_columns_in_every_shape(self):
        # the finding's arithmetic: under the 12-column indent the sentence holds a path of 44 characters and
        # not 45; under the 14-column one, 42 and not 43. Each edge is rendered from both sides in every shape
        # that names the path, within 100 columns throughout, and the layout is asserted per shape: inline
        # where the path fits its indent, on its own line where it does not (the two 12-column shapes and the
        # 14-column one disagree at 43 and 44). The table is the expectation, not a re-derivation of the rule
        sentence = len("in their own environment; this shell reads .")
        self.assertEqual((100 - 12 - sentence, 100 - 14 - sentence), (44, 42))
        indents = {"file-mode fingerprint": 12, "file-mode kernel, the file carries the line": 12, "command-mode kernel": 14}
        self.assertEqual(sorted(indents), sorted(self.shared))
        inline_at = {  # (path length, indent) -> the path stays in its sentence
            (42, 12): True, (43, 12): True, (44, 12): True, (45, 12): False,
            (42, 14): True, (43, 14): False, (44, 14): False, (45, 14): False,
        }
        inline = "in their own environment; this shell reads %s.\n"
        own_line = "in their own environment; this shell reads\n%s    %s.\n"
        for n in (42, 43, 44, 45):
            path = "/" + "p" * (n - 1)
            self.assertEqual(len(path), n)
            shapes = render_shapes(self, path)
            self.assertEqual(sorted(shapes), sorted(self.shapes))
            for name, text in shapes.items():
                for line in text.split("\n"):
                    self.assertLessEqual(len(line), 100, "%s: %r" % (name, line))
                self.assertEqual(reload_violations(text), [], name)
            for name, indent in indents.items():
                pad = " " * indent
                text = shapes[name] + "\n"
                self.assertIn(other_file_block(path, pad), shapes[name], name)
                want, other = (inline % path, own_line % (pad, path)) if inline_at[(n, indent)] else \
                              (own_line % (pad, path), inline % path)
                why = "%s: %d characters %s the %d-column indent" % (
                    name, n, "fit" if inline_at[(n, indent)] else "do not fit", indent)
                self.assertIn(want, text, why)
                self.assertNotIn(other, text, why)

    def test_the_shared_blocks_render_once_each_and_the_mechanics_never_twice(self):
        of = " ".join(other_file_block(self.path, "").split())
        rb = " ".join(restart_block("").split())
        for name, text in self.shared.items():
            flat = " ".join(text.split())
            self.assertEqual(flat.count(of), 1, name)
            self.assertEqual(flat.count(rb), 1, name)
            self.assertLess(flat.index(of), flat.index(rb), name + ": the cause, then the mechanics")
            for phrase in ("The manager restart is", "daemon-reload", "kickstart -k", "restart romp-manager", "re-read the plist"):
                self.assertEqual(flat.count(phrase), 1, "%s: %s" % (name, phrase))
            self.assertEqual(flat.count("romp-service install"), 3, name)
            self.assertLess(flat.rfind("(below)"), flat.index(rb), name + ": every pointer precedes the block it points at")
        for name in ("command-mode fingerprint", "file-mode kernel, this shell's environment carries the line"):
            flat = " ".join(self.shapes[name].split())
            self.assertNotIn(of, flat, name)
            self.assertNotIn(rb, flat, name)
            self.assertEqual(flat.count("romp-service install"), 1, name)
            self.assertEqual(flat.count("daemon-reload"), 1, name)
            self.assertNotIn("(below)", flat, name)

    def test_every_install_remedy_states_the_cost_on_both_platforms(self):
        # a Linux operator in command mode through a hand-added unit line reads `romp-service install` as the
        # remedy; write_unit overwrites the unit (PATH, ROMP_DIR, ROMP_SUPERVISED, the env-file override,
        # EnvironmentFile= and the instance variables, never ROMP_CREDENTIAL_COMMAND), so the next kernel pins
        # file mode and injects nothing. Every shape that names the install says what the rewrite drops and
        # where a line survives; round 7 said it for the plist alone
        for name, text in self.shared.items():
            self.assertIn(INSTALL_COST, " ".join(text.split()), name)
        env_only = self.shapes["file-mode kernel, this shell's environment carries the line"]
        self.assertIn("A drop-in line reaches them at the manager restart after `systemctl --user\n"
                      "            daemon-reload` instead; not a line added to the unit or the plist by hand, which the\n"
                      "            next `romp-service install` rewrites away.", env_only)
        # the command-mode fingerprint MISMATCH names the install as the reload a plist line takes; round 8 left
        # it as the one shape without the cost, and this test looped over self.shared alone (round-8
        # verification). The cost sits in the same sentence as the install it qualifies
        self.assertIn("`romp-service install` on macOS, which rewrites the plist as the Linux install rewrites the unit, "
                      "so a line added to either by hand is gone and the next kernel pins file mode; drop-ins survive, "
                      "so put your own lines in service.env or a drop-in)",
                      " ".join(self.shapes["command-mode fingerprint"].split()))
        # and the property over every shape, however worded: a shape that names the install anywhere carries the
        # words of its cost (a line added by hand is gone or rewritten away; a drop-in survives). Shape-wide, not
        # per sentence: the shared shapes name the install as what writes the path line and give the cost once,
        # in the restart block they render after their causes
        cost = re.compile(r"by hand.*?(?:gone|rewrit|drops|survive)|(?:drops|rewrit)[^.]*by hand", re.I)
        naming = [name for name, text in self.shapes.items() if "romp-service install" in text]
        self.assertEqual(sorted(naming), sorted(self.shapes), "every shape names the install today")
        for name in naming:
            flat = " ".join(self.shapes[name].split())
            self.assertTrue(cost.search(flat) and "drop-in" in flat, name + ": the install without its cost")
        for name, text in self.shapes.items():
            self.assertNotIn("which drops a line added by hand", text, name + ": the cost was stated for the plist alone")
            self.assertNotIn("so there the line goes in", text, name)
            self.assertNotIn("a line in the unit's own Environment=", text, name + ": not a place to send the line to")
        # the facts behind the cost, read from the installer: write_unit and write_plist write the whole file,
        # neither template carries a credential line, and the install leaves the unit's drop-ins alone
        svc = open(os.path.join(BIN, "romp-service"), encoding="utf-8").read()
        unit = svc.split("write_unit() {")[1].split("\n}\n")[0]
        self.assertIn('cat > "$UNIT" <<EOF', unit)
        self.assertNotIn("ROMP_CREDENTIAL", unit)
        plist = svc.split("write_plist() {")[1].split("\n}\n")[0]
        self.assertIn('cat > "$PLIST" <<EOF', plist)
        self.assertNotIn("ROMP_CREDENTIAL", plist)
        install = svc.split('case "${1:-status}" in')[1].split("uninstall)")[0]
        self.assertNotIn('"$UNIT.d"', install, "the install writes the unit and leaves its drop-ins alone")
        self.assertNotIn("rm -", install)

    def test_the_other_file_cause_is_given_in_both_directions(self):
        # the kernel's ROMP_SERVICE_ENV_FILE set to a file this shell's is not, or this shell's set where the
        # kernel's is not (an install from before the installer wrote the line): round 7 named the second
        # direction in the docstring and the docs, and the rendered lines presumed a line to find and change
        for name, text in self.shared.items():
            flat = " ".join(text.split())
            self.assertIn("this shell reads %s." % self.path, flat, name)
            self.assertIn("If found, run this command with the same value, or change it there and restart the manager "
                          "(below).", flat, name)
            self.assertIn("If not found, the kernel reads the default path: unset the variable in this shell, or point the "
                          "kernel at this file with `romp-service install` from this shell.", flat, name)
        # "the default path" is what the kernel's own resolver gives with the variable unset, and it is not this
        # shell's file (kernel/keysource.py, service_env_path)
        had = {v: os.environ.pop(v, None) for v in ("ROMP_SERVICE_ENV_FILE", "ROMP_SERVICE_ENV")}
        try:
            default = ks.service_env_path()
        finally:
            for v, was in had.items():
                if was is not None:
                    os.environ[v] = was
        self.assertNotEqual(default, self.path)
        self.assertTrue(default.endswith(os.path.join("romp", "service.env")), default)

    def test_a_shell_that_set_the_alias_is_told_so_in_the_shared_shapes_only(self):
        # kernel/keysource.py resolves the path from ROMP_SERVICE_ENV_FILE, else the alias ROMP_SERVICE_ENV; the
        # hint named the primary alone, so an alias-only shell read "unset the variable in this shell" about a
        # variable it never set and "install from this shell" about an installer that read the primary alone
        # (round-8 verification). With both set, or the primary alone, nothing is added
        for name, text in self.shapes.items():
            for line in ALIAS_NOTE:
                self.assertNotIn(line, text, name + ": both spellings set, the primary produced the path")
        os.environ.pop("ROMP_SERVICE_ENV_FILE")
        try:
            self.assertEqual(ks.service_env_path(), self.path, "the alias alone resolves the same file")
            self.assertTrue(cli._path_alias())
            shapes = render_shapes(self)                        # the real temp path: the word-for-word pins
            short = render_shapes(self, self.SHORT_PATH)        # a fabricated path: the width, whatever TMPDIR is
            for name in self.shared:
                indent = " " * (14 if name == "command-mode kernel" else 12)
                self.assertIn(other_file_block(self.path, indent, alias=True), shapes[name], name)
                flat = " ".join(shapes[name].split())
                self.assertIn("this shell reads %s. %s Look for it where" % (self.path, " ".join(ALIAS_NOTE)), flat, name)
                self.assertEqual(flat.count("ROMP_SERVICE_ENV,"), 1, name)
                for line in short[name].split("\n"):
                    self.assertLessEqual(len(line), 100, "%s: %r" % (name, line))
                self.assertIn(other_file_block(self.SHORT_PATH, indent, alias=True), short[name], name)
                self.assertEqual(reload_violations(shapes[name]), [], name)
            for name in set(shapes) - set(self.shared):
                self.assertEqual(shapes[name], self.shapes[name], name + ": no path named, so no alias named")
            long = render_shapes(self, self.LONG_PATH)["file-mode fingerprint"]
            self.assertIn(other_file_block(self.LONG_PATH, " " * 12, alias=True), long,
                          "the note follows the path on its own line too")
            os.environ.pop("ROMP_SERVICE_ENV")
            self.assertFalse(cli._path_alias(), "neither set: the default path, and no alias to name")
        finally:
            os.environ["ROMP_SERVICE_ENV_FILE"] = self.path
            os.environ["ROMP_SERVICE_ENV"] = self.path

    def test_no_rendered_shape_gives_the_bare_launchd_pair(self):
        for name, text in self.shapes.items():
            flat = " ".join(text.split())
            for pair in ("launchctl bootstrap", "launchctl bootout", "bootout then bootstrap", "bootstrap gui/"):
                self.assertNotIn(pair, flat, "%s: %s" % (name, pair))
        for name, text in self.shared.items():
            self.assertIn("A plist edit takes `romp-service install` instead: the kickstart does not re-read the plist",
                          " ".join(text.split()), name)
        self.assertIn("`romp-service install` on macOS, which rewrites the plist", self.shapes["command-mode fingerprint"])

    def test_every_shape_passes_the_reload_rule(self):
        selected = 0
        for name, text in self.shapes.items():
            self.assertEqual(reload_violations(text), [], name)
            selected += sum(1 for b in text_blocks(text) if CONCEPT.search(b) and RESTART_WORD.search(b))
        self.assertGreaterEqual(selected, 4, "the rule selects the hints it is meant for")

    def test_no_key_value_in_any_shape(self):
        for name, text in self.shapes.items():
            self.assertNotIn(OLD_KEY, text, name)
            self.assertNotIn(NEW_KEY, text, name)


class _Backend(_Env):
    """A backend on a keyless manager: the env file carries no key line, the startup claim is empty,
    so every unpicked session launches on the login and the CLI's apiKeyHelper supplies the key."""

    def setUp(self):
        super().setUp()
        self.write_env("ROMP_PERF=1\nROMP_EXPECTED_AUTH=key\n")
        self.state = tempfile.mkdtemp()
        self._stash, self._checked = sb._WORK_KEY, sb._KEY_FILE_CHECKED
        sb._WORK_KEY = ""
        sb._KEY_FILE_CHECKED = True
        self._fetch = sb._fetch_key_fast_org
        sb._fetch_key_fast_org = lambda key: None
        sb._FAST_ORG_VERDICTS.clear()
        self.logged = []
        self.be = self.construct()

    def construct(self):
        return sb.SdkBackend(self.state, "/bin/true", lambda *a, **k: None,
                             log=lambda m: self.logged.append(str(m)))

    def tearDown(self):
        sb._WORK_KEY, sb._KEY_FILE_CHECKED = self._stash, self._checked
        sb._fetch_key_fast_org = self._fetch
        sb._FAST_ORG_VERDICTS.clear()
        super().tearDown()

    def _live(self, auth_live, auth=""):
        # cycle_key answers "unknown" for a sid the backend does not own, so the registry entry comes
        # first (spawn), then the live session object the way upstream's CycleReconnects builds it
        self.be.sessions.pop(SID, None)
        if not self.be.owns(SID):
            self.be.spawn("web", "/tmp", sid=SID, auth=auth)
        reg = {"sid": SID, "name": "web", "cwd": "/tmp"}
        if auth:
            reg["auth"] = auth
        s = sb.SdkSession(self.be, reg)
        s.auth_live = auth_live
        self.reconnects, self.defers = [], []
        s.request_reconnect = lambda defer=True: (self.reconnects.append(SID), self.defers.append(defer))
        self.be.sessions[SID] = s
        return s


class _CommandMode(_Backend):
    """The backend of _Backend (a keyless manager, the login or the apiKeyHelper bills) in COMMAND
    mode: a fake command printing a synthetic set with no ANTHROPIC_API_KEY, and a fake apiKeyHelper
    in a temp CLAUDE_CONFIG_DIR — the helper-billed installation the convergence exists for."""

    def setUp(self):
        self.lab = tempfile.mkdtemp()
        self._cmd_before = {v: os.environ.get(v) for v in es.CONFIG_VARS + ("CLAUDE_CONFIG_DIR",)}
        os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(self.lab, "claude")
        os.environ["ROMP_CREDENTIAL_SELECTOR_FILE"] = os.path.join(self.lab, "selector")
        self.values = {"ANTHROPIC_LP_API_KEY": fixture_value("lp"), "A_TOKEN": fixture_value("role")}
        self.cmd = os.path.join(self.lab, "cmd.sh")
        self.print_set(self.values)
        os.environ["ROMP_CREDENTIAL_COMMAND"] = self.cmd + ' "$1"'
        self.helper_value = fixture_value("helper")
        self.helper(self.helper_value)
        es._reset()
        super().setUp()

    def tearDown(self):
        super().tearDown()
        for v, was in self._cmd_before.items():
            if was is None:
                os.environ.pop(v, None)
            else:
                os.environ[v] = was
        es._reset()

    def print_set(self, values):
        with open(self.cmd, "w") as fh:
            fh.write("#!/bin/sh\n" + "".join("echo '%s=%s'\n" % kv for kv in values.items()))
        os.chmod(self.cmd, 0o700)

    def helper(self, value):
        d = os.environ["CLAUDE_CONFIG_DIR"]
        os.makedirs(d, exist_ok=True)
        h = os.path.join(self.lab, "helper.sh")
        with open(h, "w") as fh:
            fh.write("#!/bin/sh\necho '%s'\n" % value)
        os.chmod(h, 0o700)
        with open(os.path.join(d, "settings.json"), "w") as fh:
            json.dump({"apiKeyHelper": h}, fh)

    def connect(self, s):
        """What a connect does for the stamps: _options on the live session object."""
        import sys
        import types
        fake = None
        if "claude_agent_sdk" not in sys.modules and not sb.sdk_importable():
            fake = types.ModuleType("claude_agent_sdk")
            fake.HookMatcher = lambda **kw: kw
            sys.modules["claude_agent_sdk"] = fake
        try:
            return self.be._options(s, dict)
        finally:
            if fake is not None:
                sys.modules.pop("claude_agent_sdk", None)


class HelperSessionsConverge(_CommandMode):
    def test_a_connect_stamps_the_helpers_fingerprint_when_nothing_is_injected(self):
        s = self._live("key")
        kw = self.connect(s)
        self.assertFalse("ANTHROPIC_API_KEY" in kw["env"], "the set carries no key: nothing injected")
        self.assertEqual(kw["env"]["A_TOKEN"], self.values["A_TOKEN"], "the role variables ride the launch")
        self.assertEqual(s._launched_key_fp, es.fingerprint(self.helper_value))
        self.assertEqual(s._launched_set_fp, es.set_fingerprint(self.values))
        self.assertFalse(s._launched_keyed)

    def test_a_session_on_the_current_helper_output_is_current_not_reconnected(self):
        s = self._live("key")
        self.connect(s)
        self.assertEqual(s.effective_auth(), "login", "the kernel injects nothing: no key anywhere it reads")
        self.assertEqual(self.be.cycle_key(SID), "current")
        self.assertEqual(self.be.cycle_key(SID), "current", "idempotent: a repeated --cycle-all leaves it alone")
        self.assertEqual(self.reconnects, [])

    def test_a_rotation_behind_the_helper_cycles_once_then_reads_current(self):
        s = self._live("key")
        self.connect(s)
        self.helper(fixture_value("rotated"))
        self.assertEqual(self.be.cycle_key(SID), "current", "cached: the kernel has not re-run the helper yet")
        self.be.refresh_key_source()                              # what --cycle does first
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        self.assertEqual(self.reconnects, [SID])
        self.assertEqual(self.defers, [False], "immediate-only, like every key cycle")
        line = [m for m in self.logged if m.startswith("keyswap (web)")]
        self.assertEqual(len(line), 1)
        self.assertIn("apiKeyHelper now prints sha256:", line[0])
        self.assertNotIn(self.helper_value, line[0])
        self.connect(s)                                           # the reconnect lands: new stamps
        self.assertEqual(self.be.cycle_key(SID), "current", "converged — the second run names nothing")
        self.assertEqual(self.reconnects, [SID])

    def test_a_rotation_of_a_role_variable_cycles_a_helper_session_too(self):
        s = self._live("key")
        self.connect(s)
        self.values["ANTHROPIC_LP_API_KEY"] = fixture_value("lp2")
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        line = [m for m in self.logged if m.startswith("keyswap (web)")][0]
        self.assertIn("role variables are now sha256:", line)
        self.connect(s)
        self.assertEqual(self.be.cycle_key(SID), "current")

    def test_a_login_billed_session_with_role_variables_cycles_on_their_rotation_only(self):
        s = self._live("login", auth="login")
        self.connect(s)
        self.assertEqual(self.be.cycle_key(SID), "current", "the set it launched with is the current one")
        self.helper(fixture_value("rotated"))
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "current", "a helper rotation is not its business: its CLI reported the login")
        self.values["A_TOKEN"] = fixture_value("role2")
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "cycling")

    def test_a_login_billed_session_with_no_role_variables_is_left_alone(self):
        self.print_set({})                    # the command prints nothing usable → an empty set
        es._reset()
        os.environ["ROMP_CREDENTIAL_COMMAND"] = "true"
        self._live("login", auth="login")
        self.assertEqual(self.be.cycle_key(SID), "login", "nothing to re-present: a reconnect would cost a turn")
        self._live("")
        self.assertEqual(self.be.cycle_key(SID), "login", "no init yet, nothing injected: nothing in play")
        self.assertEqual(self.reconnects, [])

    def test_a_helper_the_kernel_cannot_fingerprint_reconnects_on_every_run_with_the_reason(self):
        os.remove(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"))
        es._reset()
        s = self._live("key")
        self.connect(s)
        self.assertEqual(s._launched_key_fp, "", "no helper the kernel can see")
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        self.assertEqual(self.be.cycle_key(SID), "cycling", "nothing to converge on: the old behaviour, by its rule")
        self.assertEqual(self.reconnects, [SID, SID])
        line = [m for m in self.logged if m.startswith("keyswap (web)")][0]
        self.assertIn("could not fingerprint", line)
        self.assertIn("no apiKeyHelper in", line)

    def test_in_flight_work_still_skips_a_helper_session(self):
        s = self._live("key")
        self.connect(s)
        self.helper(fixture_value("rotated"))
        self.be.refresh_key_source()
        s._bg_tasks["t1"] = {"since": 1}
        self.assertEqual(self.be.cycle_key(SID), "working")
        s._bg_tasks.clear()
        s.inflight = 1
        self.assertEqual(self.be.cycle_key(SID), "working")
        self.assertEqual(self.reconnects, [], "a reconnect would kill the work — the same rule as upstream's")

    def test_an_explicit_login_pick_whose_cli_still_reports_a_key_converges_on_the_helper(self):
        # the pick says login, the CLI says a key (the helper found one anyway): the kernel injects
        # nothing either way, and the helper's fingerprint is what its new process would change
        s = self._live("key", auth="login")
        self.connect(s)
        self.assertEqual(self.be.cycle_key(SID), "current")
        self.helper(fixture_value("rotated"))
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "cycling")

    def test_a_login_pick_beside_a_set_that_carries_a_key_converges_on_the_helper_not_the_key(self):
        # the set has a key (other sessions inject it); THIS session picked login and its CLI still
        # reported a key — the helper's. Its compare is the helper's fingerprint, never the set's key
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key")
        self.print_set(self.values)
        es._reset()
        s = self._live("key", auth="login")
        kw = self.connect(s)
        self.assertFalse("ANTHROPIC_API_KEY" in kw["env"], "ANTHROPIC_API_KEY present")
        self.assertEqual(s._launched_key_fp, es.fingerprint(self.helper_value))
        self.assertEqual(self.be.cycle_key(SID), "current")
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key2")   # the set's key rotates: not this session's concern
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "current")
        self.helper(fixture_value("rotated"))                       # the helper rotates: it is
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        self.assertEqual(self.reconnects, [SID])

    def test_a_keyed_session_converges_on_the_sets_key(self):
        k = fixture_value("key")
        self.values["ANTHROPIC_API_KEY"] = k
        self.print_set(self.values)
        es._reset()
        s = self._live("key", auth="key")
        kw = self.connect(s)
        self.assertEqual(kw["env"]["ANTHROPIC_API_KEY"], k)
        self.assertEqual(s._launched_key_fp, es.fingerprint(k))
        self.assertEqual(self.be.cycle_key(SID), "current")
        self.values["ANTHROPIC_API_KEY"] = fixture_value("key2")
        self.print_set(self.values)
        self.be.refresh_key_source()
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        self.assertIn("the work key is now sha256:", [m for m in self.logged if m.startswith("keyswap (web)")][0])
        self.connect(s)
        self.assertEqual(self.be.cycle_key(SID), "current")

    def _sessions(self, *ns):
        return [sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-%012d" % n, "name": "s%d" % n, "cwd": "/tmp"})
                for n in ns]

    @staticmethod
    def _result(status):
        from types import SimpleNamespace
        return SimpleNamespace(is_error=status is not None, api_error_status=status, parent_tool_use_id=None)

    def test_a_refusal_on_a_session_still_on_the_pre_rotation_helper_output_runs_nothing(self):
        # the reproduction on the helper-billed box: a session stamped with the helper's output from
        # before a rotation behind the helper is refused on every turn, and a session on the current
        # output completes turns between. Before this every 401 was forwarded without the session's
        # stamp, so each refusal invalidated the current set (a command run AND a helper run at the
        # next connect, a log line) and each success re-armed the path (a second log line), for as
        # long as the old session was left uncycled.
        old, cur = self._sessions(1, 2)
        self.connect(old)
        self.assertEqual(old._launched_key_fp, es.fingerprint(self.helper_value))
        rotated = fixture_value("rotated")
        self.helper(rotated)
        self.be.refresh_key_source()                              # what --cycle does first
        self.connect(cur)
        self.assertEqual(cur._launched_key_fp, es.fingerprint(rotated))
        runs, hruns = es._runs, es.helper_runs()
        self.logged.clear()
        for n in range(5):
            old._ah_note_result(self._result(401))
            self.connect(self._sessions(10 + n)[0])               # a connect between: nothing to re-run
            cur._ah_note_result(self._result(None))
        self.assertEqual((es._runs, es.helper_runs()), (runs, hruns), "no command run and no helper run for the burst")
        self.assertEqual([m for m in self.logged if m.startswith("credential command:")], [],
                         "neither the refusal line nor the re-arm line, turn after turn")
        cur._ah_note_result(self._result(401))                    # the current output refused: fires once
        self.connect(self._sessions(20)[0])
        self.assertEqual((es._runs, es.helper_runs()), (runs + 1, hruns + 1))
        self.assertEqual(len([m for m in self.logged if "reported an authentication failure" in m]), 1, self.logged)
        self.assertFalse(any(self.helper_value in m or rotated in m for m in self.logged), "no line carries a value")

    def test_a_refresh_between_a_connects_read_and_its_helper_fingerprint_leaves_no_stale_entry_current(self):
        # a connect takes the set, then asks for the helper's fingerprint with it; an invalidate that
        # lands between the two (a --refresh, a refusal on another session) must not leave the
        # fingerprint of the connect's pre-refresh overlay stored as the current one. The helper here
        # reads a role variable, so the overlay decides what it prints.
        h = fixture_value("helper")
        hp = os.path.join(self.lab, "helper.sh")
        with open(hp, "w") as fh:
            fh.write('#!/bin/sh\necho "%s-${A_TOKEN:-none}"\n' % h)
        os.chmod(hp, 0o700)
        with open(os.path.join(os.environ["CLAUDE_CONFIG_DIR"], "settings.json"), "w") as fh:
            json.dump({"apiKeyHelper": hp}, fh)
        es.invalidate("the helper changed")
        role_a, role_b = self.values["A_TOKEN"], fixture_value("role-b")
        real_take = es.take

        def take_then_rotate(environ=None):
            out = real_take(environ)
            self.values["A_TOKEN"] = role_b
            self.print_set(self.values)
            es.invalidate("a refresh landed between the connect's read and its helper fingerprint")
            return out

        s = self._live("key")
        es.take = take_then_rotate
        try:
            self.connect(s)
        finally:
            es.take = real_take
        self.assertEqual(s._launched_key_fp, es.fingerprint("%s-%s" % (h, role_a)),
                         "stamped with what its CLI's helper prints in the environment it launched with")
        hruns = es.helper_runs()
        fp, kind = self.be.credential_fingerprint()
        self.assertEqual((fp, kind), (es.fingerprint("%s-%s" % (h, role_b)), "helper"),
                         "the current fingerprint is of the current set's overlay, not the connect's")
        self.assertEqual(es.helper_runs(), hruns + 1, "the connect's entry was stale: the helper ran again")

    def test_the_helper_status_word_is_gone(self):
        src = open(os.path.join(ROOT, "kernel", "sdk_backend.py")).read()
        self.assertNotIn('return "helper"', src, "the always-reconnect outcome was replaced by convergence")
        self.assertNotIn("helper = True", src)

    def test_the_file_mode_compare_is_upstreams(self):
        # FILE mode (the command unset): a non-keyed session reads "login" whatever its CLI reported;
        # a keyed one converges on the file key's fingerprint — upstream's arm, untouched
        os.environ.pop("ROMP_CREDENTIAL_COMMAND")
        es._reset()
        self._live("key")
        self.assertEqual(self.be.cycle_key(SID), "login")
        self.write_env("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        s = self._live("key", auth="key")
        s._launched_key_fp = ks.fingerprint(NEW_KEY)          # launched on a previous key
        self.assertEqual(self.be.cycle_key(SID), "cycling")
        s._launched_key_fp = ks.fingerprint(OLD_KEY)
        self.assertEqual(self.be.cycle_key(SID), "current")


class EnvFileCredentialWarning(_Backend):
    def _problems(self):
        return [p["text"] for p in self.be.problems()]

    def _warned(self):
        return [t for t in self._problems() if "credential line" in t]

    def test_login_declared_and_a_key_line_fires_once_naming_the_file_and_the_variable_not_the_value(self):
        self.write_env("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        sb._CREDENTIAL_LINE_SAID = False
        self.logged.clear()
        self.be = self.construct()
        lines = self._warned()
        self.assertEqual(len(lines), 1, self._problems())
        self.assertIn(self.path, lines[0])
        self.assertIn(ks.KEY_VAR, lines[0])
        self.assertIn("ROMP_EXPECTED_AUTH=login", lines[0])
        self.assertIn("does not write API keys to files", lines[0])
        self.assertNotIn("this installation", lines[0], "a fork policy, not a claim about one box")
        self.assertIn("would be injected at launch", lines[0], "ANTHROPIC_API_KEY is the variable the launch injects")
        self.assertIn("Billing pick", lines[0], "…so its line names the billing consequence")
        self.assertNotIn(OLD_KEY, lines[0])
        self.assertTrue(any(OLD_KEY not in m for m in self.logged))
        self.assertFalse(any(OLD_KEY in m for m in self.logged), "no log line carries the value")
        # once per process: a re-constructed backend (the WS handler's lazy build, tests) says nothing new
        be2 = self.construct()
        self.assertEqual([p["text"] for p in be2.problems() if "credential line" in p["text"]], [])

    def test_key_declared_fires_too_the_apikeyhelper_shape(self):
        self.write_env("ROMP_PERF=1\n%s=%s\nROMP_EXPECTED_AUTH=key\n" % (ks.KEY_VAR, OLD_KEY))
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        lines = self._warned()
        self.assertEqual(len(lines), 1, self._problems())
        self.assertIn("ROMP_EXPECTED_AUTH=key", lines[0])
        self.assertIn("apiKeyHelper", lines[0])
        self.assertNotIn(OLD_KEY, lines[0])

    def test_undeclared_is_quiet_upstreams_ordinary_file_key_box(self):
        self.write_env("ROMP_PERF=1\n%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        self.assertEqual(self._warned(), [])
        self.assertEqual(sb._warn_credential_lines_in_env_file(self.be._log), [])
        self.assertFalse(sb._CREDENTIAL_LINE_SAID, "a quiet pass does not spend the one shot")

    def test_a_declaration_over_a_file_with_no_credential_is_quiet(self):
        self.write_env("ROMP_PERF=1\nROMP_EXPECTED_AUTH=login\nROMP_DIR=/tmp/x\n")
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        self.assertEqual(self._warned(), [])
        self.assertFalse(sb._CREDENTIAL_LINE_SAID)

    def test_which_lines_count(self):
        # each empty-value line is followed by a comment line on purpose: compiled to bytecode, this
        # literal holds real newlines, and a secret scanner's generic rule would otherwise read
        # `EMPTY_TOKEN=` + newline + the next NAME= as a key and its value (the repo's own
        # gitleaks check scans the working tree, __pycache__ included)
        self.write_env("# a comment\n\nFOO_API_KEY=abc\nBAR_TOKEN='xyz'\nNOT_A_SECRET=1\n"
                       "BAR_TOKEN=again\nTOKEN_PREFIX_X=1\nQUOTED_API_KEY=\"\"\n# an empty value\n"
                       "EMPTY_TOKEN=\n# is not a credential\n")
        self.assertEqual(sb._credential_names_in_env_file(self.path), ["FOO_API_KEY", "BAR_TOKEN"])
        self.assertEqual(sb._credential_names_in_env_file(os.path.join(self.d, "absent.env")), [])
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        lines = self._warned()
        self.assertEqual(len(lines), 1)
        self.assertIn("FOO_API_KEY, BAR_TOKEN", lines[0])
        self.assertIn("credential lines", lines[0])
        for value in ("abc", "xyz", "again"):
            self.assertNotIn("=" + value, lines[0])
        # neither is the variable the launch injects, so the line makes no billing claim about them
        self.assertIn("FOO_API_KEY, BAR_TOKEN: a credential in a file contradicts the declared auth model", lines[0])
        self.assertNotIn("Billing pick", lines[0])
        self.assertNotIn("injected", lines[0])
        self.assertNotIn("apiKeyHelper", lines[0])

    def test_a_mixed_file_names_the_billing_consequence_for_the_key_and_the_plain_line_for_the_rest(self):
        self.write_env("%s=%s\nHF_TOKEN=abc\nROMP_SERVE_TOKEN=xyz\n" % (ks.KEY_VAR, OLD_KEY))
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        lines = self._warned()
        self.assertEqual(len(lines), 1)
        self.assertIn("ANTHROPIC_API_KEY would be injected at launch: the sessions' key reaches Claude Code through its apiKeyHelper", lines[0])
        self.assertIn("HF_TOKEN, ROMP_SERVE_TOKEN: a credential in a file contradicts the declared auth model", lines[0])
        self.assertIn("remove the lines and rotate the values, since they reached a file", lines[0])
        for value in (OLD_KEY, "abc", "xyz"):
            self.assertNotIn(value, lines[0])

    def test_the_check_reads_the_installers_variable_for_the_path(self):
        other = os.path.join(self.d, "elsewhere.env")
        with open(other, "w") as fh:
            fh.write("%s=%s\n" % (ks.KEY_VAR, OLD_KEY))
        os.environ["ROMP_SERVICE_ENV_FILE"] = other
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        sb._CREDENTIAL_LINE_SAID = False
        self.be = self.construct()
        lines = self._warned()
        self.assertEqual(len(lines), 1)
        self.assertIn(other, lines[0])


if __name__ == "__main__":
    unittest.main()

"""The boot line naming credential-shaped names in the kernel's own environment that reach every
session. All values here are synthetic; no backend construction dials a real kernel (the ports are
poisoned at import, matching conftest). romp holds no key of its own (kernel/credentials.py), so the
variables are staged straight into os.environ: nothing of romp's claims them but the login tokens. The
boot check (credentials.check_boot_environment, run by kernel.main() before a backend exists and pinned in
tests/test_credentials.py, BootCheck and KernelSide) never runs here, so a backend built directly sees
what is staged; no retired provider name is staged anywhere in this module."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import ModuleType
import types
import unittest
from unittest.mock import patch
from romp_load import load_source

ROOT = Path(__file__).resolve().parents[1]
_IMPORT_STATE = tempfile.mkdtemp(prefix="romp-envnames-")
os.environ["XDG_STATE_HOME"] = _IMPORT_STATE
os.environ.pop("ROMP_STATE_DIR", None)
os.environ["ROMP_MANAGER_PORT"] = "1"          # never dial the real manager (restart-all)
os.environ["ROMP_KERNEL_PORT"] = "1"           # never dial the real kernel
os.environ["ROMP_SERVICE_ENV_FILE"] = _IMPORT_STATE + "/absent.env"
os.environ["ROMP_SERVICE_ENV"] = os.environ["ROMP_SERVICE_ENV_FILE"]
sb = load_source("romp_sdk_envnames", str(ROOT / "kernel/sdk_backend.py"))


def _op_name(n):
    """The 1Password CLI's own names as credentials.py classifies them (is_op_env_name): the boot line's op
    shape is that classifier, the one the boot check refuses and the test floor pops. The delegation is
    deliberate, so over an op-shaped spelling the table below can only agree with the implementation; the
    INTENT for the op half's case handling is pinned on its own (PureNames.test_the_1password_half_folds_case_by_declared_intent,
    review round 1 of the env-pick door, 2026-09-18)."""
    return sb._cred.is_op_env_name(n)


def _shaped(n):
    # both halves fold case: the suffixes since review round 1 of the spawn-spec fix, the op names since review
    # round 1 of the env-pick door (2026-09-18), which hands the classifier the upper-cased name as the predicate does
    u = n.upper()
    return u.endswith("_API_KEY") or u.endswith("_TOKEN") or _op_name(u)


class PureNames(unittest.TestCase):
    def names(self, env):
        return sb.env_credential_names(env)

    def test_api_key_and_token_names_are_named(self):
        env = {"EXAMPLE_API_KEY": "x", "OPENAI_API_KEY": "y", "HF_TOKEN": "z", "MY_SECRET_TOKEN": "q"}
        self.assertEqual(self.names(env), ["EXAMPLE_API_KEY", "HF_TOKEN", "MY_SECRET_TOKEN", "OPENAI_API_KEY"])

    def test_the_control_token_is_the_one_exclusion(self):
        env = {"ROMP_SERVE_TOKEN": "control", "OPENROUTER_API_KEY": "r"}
        self.assertEqual(self.names(env), ["OPENROUTER_API_KEY"],
                         "romp's own control token is not a provider credential; nothing else is excluded by name")
        self.assertEqual(sb._cred.credential_env_names(env), ["OPENROUTER_API_KEY", "ROMP_SERVE_TOKEN"],
                         "the exclusion is this boot wrapper's, not the rule's (review round 1 of the env-pick door, "
                         "2026-09-18: carried in the rule, it let a per-session pick write the token to two files)")

    def test_a_login_token_still_present_is_named(self):
        """The helper excludes no name the boot claim removes: a login token still in the environment when it
        runs did reach sessions, so it is named, and the call's place after startup_auth_env (BootWiring
        below) is what keeps one off the line. The key name is named too: the boot check
        (credentials.check_boot_environment), not this helper, is what keeps a key out of the environment."""
        env = {n: "v" for n in sb.AUTH_ENV_NAMES}
        self.assertEqual(self.names(env), sorted(sb.AUTH_ENV_NAMES))

    def test_the_suffix_test_folds_case(self):
        """Review round 1 of the spawn-spec fix (2026-09-18): the suffixes were compared exactly, so a lowercase or
        mixed-case spelling was never named here, and the spawn spec's writer, which reuses this rule, would have
        written such a name to hosts/<sid>/spawn.json with its value. A name whose suffix only begins with the
        shape (editor_tokenizer) stays unnamed in any case."""
        self.assertEqual(self.names({"notes_api_token": "x", "Notes_Api_Key": "y", "editor_tokenizer": "z"}),
                         ["Notes_Api_Key", "notes_api_token"])

    def test_the_doors_predicate_and_this_helper_agree_over_every_spelling(self):
        """One shape rule, never two (2026-09-18): the per-session env door judges a pick by credentials.py's
        is_credential_env_name and credential_env_names, and this helper delegates to the same; so does the
        spawn.json writer (spawn_env_secret_names). The list of names is built at run time from stems, suffixes
        and casings, so the four readers are compared over spellings no one wrote out, and the expected verdict
        is this module's own _shaped (both halves fold case since review round 1 of the env-pick door,
        2026-09-18). The control token's exact name is excluded by the boot notice alone (that round moved the
        exclusion out of the rule); the rule, the writer and the door name it like any other."""
        names = []
        for stem in ("NOTES", "notes", "Notes", "HF", "my_secret", "ROMP_SERVE", "romp_serve", "OP_SESSION", "op_session"):
            for suffix in ("_API_KEY", "_TOKEN", "_api_key", "_token", "_Api_Key", "_Token", "_TOKENIZER", "_tokenizer",
                           "_KEY", "", "_ENDPOINT"):
                names.append(stem + suffix)
        names += ["OP_SESSION_testacct", "op_session_testacct", "Op_Session_TestAcct", "OP_ACCOUNT", "op_account",
                  "Op_Connect_Host", "OP_CONNECT_HOST", "OP_CONNECT_TOKEN", "op_service_account_token",
                  "OPTIONS_FOR_X", "options_for_x", "TOKEN_FIRST", "API_KEY_HOLDER", "_TOKEN", "_API_KEY", "_token"]
        self.assertGreater(len(set(names)), 80)
        for n in names:
            self.assertIs(sb._cred.is_credential_env_name(n), _shaped(n), "the door's predicate on %r" % (n,))
            expect = [n] if _shaped(n) else []
            self.assertEqual(sb._cred.credential_env_names({n: "v"}), expect, "credentials.py over %r" % (n,))
            self.assertEqual(self.names({n: "v"}), [] if n == "ROMP_SERVE_TOKEN" else expect,
                             "this helper over %r (the boot notice's one exclusion, the exact control token)" % (n,))
            self.assertEqual(sb.spawn_env_secret_names({n: "v"}), expect, "the spawn.json writer over %r" % (n,))
            self.assertEqual(bool(sb.env_request_error({n: "v"})), bool(expect), "the door over %r" % (n,))
        self.assertEqual(self.names({"romp_serve_token": "v"}), ["romp_serve_token"],
                         "the exclusion is the exact name romp reads; another spelling is not romp's token")

    def test_the_1password_half_folds_case_by_declared_intent(self):
        """Review round 1 of the env-pick door (2026-09-18): the table above delegates the op half of its oracle to
        is_op_env_name on purpose (the boot check reads the same classifier, and the table's job is four-site
        agreement), so over an op-shaped spelling it can only agree with the implementation; what it could not pin
        was the INTENT for that half's case handling, and the fold ordered for the suffixes had reached that half
        alone, so op_session_<account>, the most sensitive of these names, passed every reader. The intent is
        declared here, so a later change to the op half's case handling has to re-declare itself in a test: a
        lowercase or mixed-case 1Password name is credential-shaped, named by the rule, moved by the writer and
        refused at the door, exactly like its upper-case spelling. The boot check's own classifier
        (credentials.is_op_env_name, read direct) keeps 1Password's spelling: it refuses what `op` exports."""
        for n in ("op_session_testacct", "Op_Session_TestAcct", "op_account", "Op_Connect_Host",
                  "op_service_account_token", "OP_SESSION_testacct"):
            intent = ("INTENT (review round 1 of the env-pick door, 2026-09-18): the 1Password half of the shape rule "
                      "folds letter case, so %r is credential-shaped; a change to that case handling must re-declare "
                      "itself here" % (n,))
            self.assertTrue(sb._cred.is_credential_env_name(n), intent)
            self.assertEqual(sb._cred.credential_env_names({n: "v"}), [n], intent)
            self.assertEqual(self.names({n: "v"}), [n], intent)
            self.assertEqual(sb.spawn_env_secret_names({n: "v"}), [n], intent)
            self.assertIn(n, sb.env_request_error({n: "v"}), intent)
            self.assertEqual(sb._cred.credential_env_names({n: ""}), [], "an empty value is not a leak, in any case")
        for n in ("op_account", "op_session_testacct", "Op_Connect_Host"):
            self.assertFalse(sb._cred.is_op_env_name(n),
                             "the boot check's classifier itself stays as 1Password spells the names: %r" % (n,))
        self.assertTrue(sb._cred.is_op_env_name("OP_ACCOUNT") and sb._cred.is_op_env_name("OP_SESSION_testacct"))
        self.assertFalse(sb._cred.is_credential_env_name("options_for_x"), "a prefix that only begins like OP_ is not the shape")

    def test_empty_or_whitespace_values_are_not_named(self):
        self.assertEqual(self.names({"FOO_API_KEY": "", "BAR_TOKEN": "   ", "BAZ_API_KEY": "v"}), ["BAZ_API_KEY"])

    def test_non_credential_names_are_ignored(self):
        self.assertEqual(self.names({"ROMP_PERF": "1", "PATH": "/bin", "EDITOR_TOKENIZER": "x"}), [])

    def test_op_names_are_named_as_credentials_classifies_them(self):
        """OP_SESSION_<account> (what `op signin` exports) ends in neither suffix, yet credentials.py classifies
        it (is_op_env_name, beside the service-account and Connect names in OP_ENV_NAMES) as the 1Password
        CLI's own and refuses it at boot; the helper names what that classifier accepts on the upper-cased name
        (the fold, review round 1 of the env-pick door, 2026-09-18), so the boot line names every spelling the
        boot check refuses and the lowercase ones besides."""
        env = {"OP_SESSION_TESTACCT": "s", "OP_CONNECT_HOST": "h", "OP_ACCOUNT": "a",
               "OP_SERVICE_ACCOUNT_TOKEN": "t", "OPTIONS_FOR_X": "not an op name"}
        self.assertEqual(self.names(env), ["OP_ACCOUNT", "OP_CONNECT_HOST", "OP_SERVICE_ACCOUNT_TOKEN",
                                           "OP_SESSION_TESTACCT"])
        for n in self.names(env):
            self.assertTrue(_op_name(n), n)
        self.assertEqual(self.names({"OP_SESSION_TESTACCT": ""}), [], "an empty value is not a leak")

    def test_the_return_is_names_never_values(self):
        env = {"OPENAI_API_KEY": "plain-oai-must-not-appear"}
        out = self.names(env)
        self.assertEqual(out, ["OPENAI_API_KEY"])
        self.assertNotIn("plain-oai-must-not-appear", " ".join(out))


class ReferenceLister(unittest.TestCase):
    """docs/reference.md's names-only lister is a fourth spelling of the shape rule (review round 1 of the env-pick
    door, 2026-09-18): pinned by nothing, it listed ROMP_SERVE_TOKEN while the rule the doors judged by excluded it
    (the exclusion moved out of the rule and into the boot notice's wrapper that round, so the doors, the writer and
    this lister agree now), folded case on the suffixes alone, resolved a literal state root, and its markdown
    indent landed inside the quoted Python, so the command copied from the raw file was an IndentationError. Run
    here exactly as fenced, over a synthetic state root, and held to credential_env_names file by file and name by
    name. Since review round 2 (2026-09-19) it skips and REPORTS, on stderr, a file it cannot read or that is not a
    settings object, rather than aborting the listing at the first odd file (correctness-3), and the fixture plants
    every 1Password name from the rule's own list plus a lowercase OP_SESSION_ witness (correctness-4, kernel-5).
    Since review round 3 (2026-09-19, extra5-2) its globs take the temp files beside either launch file too
    (<sid>.json.<pid>.<hex>.tmp: a kernel killed between a writer's temp write and its rename leaves one holding what
    was being written, env included, and the *.json glob could not see it), so the fixture plants one in each
    directory and expects its names listed."""

    SID_A = "11111111-2222-3333-4444-555555555501"
    SID_B = "11111111-2222-3333-4444-555555555502"

    @classmethod
    def _snippet(cls):
        text = (ROOT / "docs" / "reference.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```bash\n(.*?)\n```", text, re.S)
        hits = [b for b in blocks if "sdk-flag-settings" in b]
        assert len(hits) == 1, "one fenced bash block lists the flag-settings files: %d found" % len(hits)
        return hits[0]

    def test_the_snippet_is_fenced_without_indent_and_lists_what_the_rule_names(self):
        snippet = self._snippet()
        self.assertTrue(snippet.startswith("python3 -c '"), "a shell command, fenced as bash")
        self.assertFalse(any(ln.startswith(" ") and ln.lstrip().startswith(("S =", "for p")) for ln in snippet.splitlines()),
                         "no markdown indent inside the quoted source (the indent was the IndentationError)")
        self.assertNotIn("ROMP_SERVE_TOKEN", snippet, "no exclusion the doors do not have")
        self.assertNotIn('expanduser("~/.local/state/romp")', snippet, "the state root is resolved as romp resolves it")
        root = tempfile.mkdtemp(prefix="romp-lister-")
        os.makedirs(os.path.join(root, "sdk-flag-settings"))
        os.makedirs(os.path.join(root, "sdk"))
        val = "synthetic-" + os.urandom(6).hex()
        env_a = {"NOTES_ENDPOINT": "http://notes.test", "notes_api_token": val, "EMPTY_TOKEN": "",
                 "ROMP_SERVE_TOKEN": "control", "OP_SESSION_testacct": val, "op_account": "acct", "SPACES_TOKEN": "  ",
                 # one lowercase witness per clause of the snippet's rule is deliberate (kernel-5, review round 2,
                 # 2026-09-19): op_account covers the fixed-names clause, this one the OP_SESSION_ prefix clause, and
                 # notes_api_token the suffix clause, so a clause that stops folding case goes red here
                 "op_session_testacct": val}
        # every 1Password name the rule itself lists (correctness-4, review round 2, 2026-09-19: the fixture planted
        # OP_ACCOUNT alone, so a doc edit narrowing the snippet's tuple left this pin green; OP_CONNECT_HOST, which no
        # suffix catches, is the one that escaped), and a name added to the rule later is planted by construction
        env_a.update({n: "synthetic-op-%d" % i for i, n in enumerate(sb._cred.OP_ENV_NAMES)})
        env_b = {"FEATURE_FLAG": "1", "Notes_Api_Key": val, "editor_tokenizer": "x", "options_for_x": "x"}
        pa = os.path.join(root, "sdk-flag-settings", self.SID_A + ".json")
        pb = os.path.join(root, "sdk", self.SID_B + ".json")
        Path(pa).write_text(json.dumps({"fastMode": True, "env": env_a}) + "\n")
        Path(pb).write_text(json.dumps({"sid": self.SID_B, "name": "api", "env": env_b}) + "\n")
        # the temps a kernel killed mid-write leaves (extra5-2, review round 3, 2026-09-19): write_reg's and the
        # flag-settings writer's, both <sid>.json.<pid>.<hex>.tmp, each holding an env block with a value
        ta = os.path.join(root, "sdk-flag-settings", self.SID_B + ".json.4242.0badc0de.tmp")
        tb = os.path.join(root, "sdk", self.SID_A + ".json.4242.0badc0de.tmp")
        Path(ta).write_text(json.dumps({"env": {"HF_TOKEN": val, "PLAIN": "x"}}) + "\n")
        Path(tb).write_text(json.dumps({"sid": self.SID_A, "env": {"Notes_Api_Key": val}}) + "\n")
        Path(root, "sdk", "unreadable.json").write_text("{not json")
        Path(root, "sdk", self.SID_A + ".json").write_text(json.dumps({"sid": self.SID_A, "name": "web"}) + "\n")
        # two shapes that parse as JSON but are not a settings object (correctness-3, review round 2, 2026-09-19: the
        # lister ABORTED on either, and an audit that stops at the first odd file under-reports in silence); each
        # is skipped and reported on stderr, and the listing of the other files is complete
        odd_null = os.path.join(root, "sdk", "odd-null.json")
        odd_list = os.path.join(root, "sdk-flag-settings", "odd-env-list.json")
        Path(odd_null).write_text("null\n")
        Path(odd_list).write_text(json.dumps({"env": ["NOTES_API_TOKEN=x"]}) + "\n")
        env = {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", ""),
               "ROMP_STATE_DIR": root, "HOME": root}
        for k in ("XDG_STATE_HOME",):
            env[k] = os.path.join(root, "unused-xdg")     # ROMP_STATE_DIR outranks it, as in the kernel
        r = subprocess.run(["/bin/sh", "-c", snippet], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, "the snippet runs as copied: %s" % r.stderr)
        got = sorted(r.stdout.splitlines())
        want = sorted(["%s %s" % (pa, n) for n in sb._cred.credential_env_names(env_a)]
                      + ["%s %s" % (pb, n) for n in sb._cred.credential_env_names(env_b)]
                      + ["%s HF_TOKEN" % ta, "%s Notes_Api_Key" % tb])
        self.assertEqual(got, want, "file by file and name by name, the rule's own verdict, the temps included")
        self.assertIn("%s ROMP_SERVE_TOKEN" % pa, got, "the control token is listed, as the doors refuse it")
        self.assertIn("%s op_account" % pa, got, "the 1Password half folds case here too")
        self.assertIn("%s op_session_testacct" % pa, got, "the OP_SESSION_ prefix clause folds case too")
        self.assertIn("%s OP_CONNECT_HOST" % pa, got, "the one 1Password name no suffix catches is listed")
        for n in sb._cred.OP_ENV_NAMES:
            self.assertIn("%s %s" % (pa, n), got, n)
        self.assertIn("%s notes_api_token" % pa, got)
        self.assertNotIn("%s EMPTY_TOKEN" % pa, got)
        self.assertNotIn(val, r.stdout, "names only, never a value")
        reported = sorted(ln for ln in r.stderr.splitlines() if "skipped" in ln)
        self.assertEqual(reported, sorted(["%s skipped: not a settings object" % odd_list,
                                           "%s skipped: not a settings object" % odd_null,
                                           "%s skipped: unreadable (JSONDecodeError)" % os.path.join(root, "sdk", "unreadable.json")]),
                         "each odd file is reported on stderr, by path, and the listing goes on: %r" % (r.stderr,))
        self.assertNotIn(val, r.stderr)

    def test_the_snippet_resolves_the_state_root_in_romps_order(self):
        # ROMP_STATE_DIR, else XDG_STATE_HOME/romp, else ~/.local/state/romp: the kernel's own resolution
        snippet = self._snippet()
        root = tempfile.mkdtemp(prefix="romp-lister-xdg-")
        os.makedirs(os.path.join(root, "romp", "sdk-flag-settings"))
        val = "synthetic-" + os.urandom(6).hex()
        p = os.path.join(root, "romp", "sdk-flag-settings", self.SID_A + ".json")
        Path(p).write_text(json.dumps({"env": {"HF_TOKEN": val}}) + "\n")
        env = {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", ""),
               "XDG_STATE_HOME": root, "HOME": os.path.join(root, "home-unused")}
        r = subprocess.run(["/bin/sh", "-c", snippet], env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), ["%s HF_TOKEN" % p])


class BootNoticeMethod(unittest.TestCase):
    """The method in isolation: __new__ skips __init__, so no thread, no state dir, no kernel."""

    def setUp(self):
        patch.object(sb, "_ENV_CRED_NAMES_SAID", False).start()
        self.addCleanup(patch.stopall)
        self.be = sb.SdkBackend.__new__(sb.SdkBackend)
        self.logs = []
        self.be._log = lambda m, problem=None: self.logs.append((m, problem))

    def test_says_once_naming_names_not_values(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "value-oai-synth", "HF_TOKEN": "value-hf-synth"}, clear=False):
            self.be._note_env_credential_names()
            self.be._note_env_credential_names()
        rows = [m for m, _ in self.logs if "reach every session" in m]
        self.assertEqual(len(rows), 1, "one line per process")
        self.assertIn("OPENAI_API_KEY", rows[0])
        self.assertIn("HF_TOKEN", rows[0])
        self.assertNotIn("value-oai-synth", rows[0])
        self.assertNotIn("value-hf-synth", rows[0])
        self.assertIs(self.logs[0][1], False, "filed as information explicitly, never left to _log's default")

    def test_the_line_names_lowercase_names_of_both_halves_and_its_clause_says_both_fold_case(self):
        """Review round 2 of the spawn-spec fix (2026-09-18): round 1 folded case in env_credential_names, and this
        line's own copy still described the exact-cased suffixes, so a lowercase variable was listed under a shape
        clause that excluded it. Review round 2 of the env-pick door (2026-09-19): round 1 of that PR made the
        1Password half fold too, and the copy still placed the fold on the suffixes alone and spelled the 1Password
        half OP_*, so a lowercase 1Password name was listed under a clause that read as excluding it, while this
        test pinned that placement and its docstring called the op names case-exact, certifying the misdescription.
        The intent now: BOTH halves fold, and the clause must SAY the fold covers both (where the words sit is not
        what is pinned; a rewording that says the same is fine). A lowercase name of each half is staged and listed."""
        with patch.dict(os.environ, {"notes_api_token": "value-lc-synth", "Notes_Api_Key": "value-mc-synth",
                                     "op_session_testacct": "value-op-synth"}, clear=False):
            self.be._note_env_credential_names()
        rows = [m for m, _ in self.logs if "reach every session" in m]
        self.assertEqual(len(rows), 1)
        self.assertIn("notes_api_token", rows[0])
        self.assertIn("Notes_Api_Key", rows[0])
        self.assertIn("op_session_testacct", rows[0], "a lowercase 1Password name is listed")
        for v in ("value-lc-synth", "value-mc-synth", "value-op-synth"):
            self.assertNotIn(v, rows[0])
        clause = re.search(r"\(([^()]*_API_KEY[^()]*1Password[^()]*)\)", rows[0])
        self.assertTrue(clause, "the line carries one parenthetical shape clause naming both halves: %r" % rows[0])
        clause = clause.group(1)
        self.assertTrue(clause.rstrip().endswith("in any letter case"),
                        "the clause must say the case fold covers BOTH halves, so the fold follows the 1Password half "
                        "too, not the suffixes alone: %r" % clause)
        self.assertNotIn("in any letter case, or", clause,
                         "a fold said before the 1Password clause scopes it to the suffixes and excludes op_session_<account>: %r" % clause)
        self.assertIn("names of another shape are not checked", rows[0], "and keeps its honesty about other shapes")

    def test_quiet_when_no_credential_names(self):
        with patch.dict(os.environ, {}, clear=False):       # restores every popped name on exit
            for n in list(os.environ):
                if _shaped(n):
                    os.environ.pop(n, None)
            self.be._note_env_credential_names()
        self.assertEqual([m for m, _ in self.logs if "reach every session" in m], [])


class BootWiring(unittest.TestCase):
    """A constructed backend runs the notice from __init__. Ports poisoned at import; state dir empty. The
    login-token claim (startup_auth_env) is once per process, so its memory is reset per test and every
    build runs inside patch.dict, which puts back what the claim popped."""

    def setUp(self):
        patch.object(sb, "_ENV_CRED_NAMES_SAID", False).start()
        patch.object(sb, "_STARTUP_AUTH_ENV", None).start()
        self.addCleanup(patch.stopall)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        fake = ModuleType("claude_agent_sdk")
        # an attribute-bearing stand-in, like the SDK's dataclass: with hosts on (the default since T348) the
        # options loop sets each matcher's `timeout` to the host's hook bound, which a plain dict refused
        fake.HookMatcher = lambda **kw: types.SimpleNamespace(**kw)
        fake.ClaudeAgentOptions = dict
        fake.ClaudeSDKClient = unittest.mock.Mock()
        for n in ("AssistantMessage", "ResultMessage", "SystemMessage"):
            setattr(fake, n, type(n, (), {}))
        patch.dict(sys.modules, {"claude_agent_sdk": fake}).start()

    def build(self):
        logs = []
        be = sb.SdkBackend(str(Path(self.tmp.name) / "state"), "/bin/true",
                           lambda *a, **k: None, log=logs.append)
        return be, logs

    def test_init_names_a_synthetic_provider_key_once(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "value-oai-init"}, clear=False):
            _, logs = self.build()
        rows = [m for m in logs if "reach every session" in m]
        self.assertEqual(len(rows), 1)
        self.assertIn("OPENAI_API_KEY", rows[0])
        self.assertNotIn("value-oai-init", rows[0])

    def test_boot_line_is_never_a_problem_row(self):
        """Informational on the wired path: the row reaches the log and NOT the problem ring the dashboard's
        error center reads. Built inside an except block on purpose: _log's default classification files
        any line logged while an exception is being handled, so an implicit problem=None would file this
        one whenever a boot happens on a handler's retry path. The explicit problem=False is what this
        pins; the synthetic exception below is never raised past the handler."""
        with patch.dict(os.environ, {"OPENAI_API_KEY": "value-oai-ring"}, clear=False):
            try:
                raise RuntimeError("synthetic: a boot inside an exception handler")
            except RuntimeError:
                be, logs = self.build()
        rows = [m for m in logs if "reach every session" in m]
        self.assertEqual(len(rows), 1)
        self.assertEqual([p["text"] for p in be.problems(50) if "reach every session" in p["text"]], [],
                         "the boot line is information, never a problem row")

    def test_op_names_are_named_on_the_wired_path(self):
        """The op shape on the wired path: a backend built with 1Password's names in the environment names
        them, the service-account token and the `op signin` session token both, beside a second provider's
        key, and the values never appear. romp runs no `op` of its own and claims none of these names
        (credentials.py); in production the boot check refuses them before kernel.main() builds a backend,
        so a backend that sees them was built outside it, and the line says what such a backend's sessions
        inherit."""
        env = {"OP_SERVICE_ACCOUNT_TOKEN": "synthetic-op-helper", "OP_SESSION_TESTACCT": "synthetic-op-session",
               "OPENAI_API_KEY": "value-oai-helper"}
        with patch.dict(os.environ, env, clear=False):
            _, logs = self.build()
            self.assertIn("OP_SERVICE_ACCOUNT_TOKEN", os.environ, "nothing of romp's claims op's names")
        rows = [m for m in logs if "reach every session" in m]
        self.assertEqual(len(rows), 1)
        for name in env:
            self.assertIn(name, rows[0])
        for value in env.values():
            self.assertNotIn(value, rows[0])

    def test_login_tokens_claimed_at_boot_are_not_named(self):
        """startup_auth_env pops the login tokens out of os.environ at the top of __init__, before the notice
        runs, so they are not named: sessions never inherit them (a login launch gets them back explicitly).
        The helper itself excludes neither name (PureNames above), so this is the call order in __init__
        and nothing else: moving the notice above startup_auth_env turns it red."""
        env = {"ANTHROPIC_AUTH_TOKEN": "synthetic-bearer", "CLAUDE_CODE_OAUTH_TOKEN": "synthetic-oauth",
               "OPENAI_API_KEY": "value-oai-login"}
        with patch.dict(os.environ, env, clear=False):
            _, logs = self.build()
            self.assertNotIn("ANTHROPIC_AUTH_TOKEN", os.environ, "claimed for login launches only")
            self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", os.environ, "claimed for login launches only")
        rows = [m for m in logs if "reach every session" in m]
        self.assertEqual(len(rows), 1)
        self.assertIn("OPENAI_API_KEY", rows[0])
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", rows[0])
        self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", rows[0])
        for value in env.values():
            self.assertNotIn(value, rows[0])


if __name__ == "__main__":
    unittest.main()

"""The boot line naming credential-shaped names in the kernel's own environment that reach every
session. All values here are synthetic; no backend construction dials a real kernel (the ports are
poisoned at import, matching conftest). romp holds no key of its own (kernel/credentials.py), so the
variables are staged straight into os.environ: nothing of romp's claims them but the login tokens. The
boot check (credentials.check_boot_environment, run by kernel.main() before a backend exists and pinned in
tests/test_credentials.py, BootCheck and KernelSide) never runs here, so a backend built directly sees
what is staged; no retired provider name is staged anywhere in this module."""
import ast
import inspect
import json
import os
from pathlib import Path
import re
import shutil
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

    def test_a_non_string_value_raises_in_the_predicate_and_the_writer_coerces_first(self):
        """credential_env_names takes str or None values; a value of another type that is truthy raises there (the
        strip is str's), and a falsy one (0, False, an empty list) reads as an empty value and is not named. The
        callers whose values may be of other types coerce first, for the NAME decision only (_overlay_text under
        spawn_env_secret_names), so a token-shaped name over an integer still moves out of the file. A coercion
        inside the predicate would hide a caller handing it what it does not take (the mutation pass of review round
        3, 2026-09-19: the docstring's precondition had no pin)."""
        for bad in (5, 1.5, True, ["x"], {"k": "v"}):
            with self.assertRaises(AttributeError, msg=repr(bad)):
                sb._cred.credential_env_names({"NOTES_API_TOKEN": bad})
        self.assertEqual(sb._cred.credential_env_names({"NOTES_API_TOKEN": None, "HF_TOKEN": "v"}), ["HF_TOKEN"],
                         "None is the unset it means")
        self.assertEqual(sb._cred.credential_env_names({"NOTES_API_TOKEN": 0, "OTHER_TOKEN": []}), [],
                         "a falsy value of another type reads as empty, as the strip's guard makes it")
        self.assertEqual(sb.spawn_env_secret_names({"NOTES_API_TOKEN": 5, "OTHER_TOKEN": 0}), ["NOTES_API_TOKEN", "OTHER_TOKEN"],
                         "the writer's coerced view names the same key without raising, the falsy one included")


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


class ReferenceEnvPassage(unittest.TestCase):
    """docs/reference.md's `--env` passage states what a re-declaration does to a stored value as a FACT and promises
    no removal (review round 3 of the env-pick door, 2026-09-19: the redaction road, a re-declaration that removes a
    stored value from every file, left this change for a design note, and every promise of it was reworded; the
    round's mutation pass found the reworded sentence pinned by nothing). The passage runs from the `--env` sentence
    to the lister's fenced block; its one "removes" is the fact's, and "clears" is `--no-env`'s set semantics."""

    FACT = "Nothing in this change removes a value already stored; that is a separate decision."
    AFTER = "Until it is made, a re-declaration (`romp new --env` with the rest of the set, or `--no-env`) does what it did before the door"

    @classmethod
    def _passage(cls):
        text = (ROOT / "docs" / "reference.md").read_text(encoding="utf-8")
        start = text.index("`--env` gives one session its own environment")
        return " ".join(text[start:text.index("```bash", start)].split())

    def test_the_passage_states_the_fact_and_the_sentence_after_it_says_what_a_redeclaration_does(self):
        flat = self._passage()
        self.assertIn(self.FACT, flat, "the fact, word for word")
        self.assertIn(self.FACT + " " + self.AFTER, flat, "and the next sentence states the base's behaviour, not a remedy")
        self.assertIn("a file nothing rewrites stays as it was", flat)

    def test_no_promise_of_removal_remains_outside_the_fact(self):
        rest = self._passage().replace(self.FACT, "").lower()
        for word in ("remov", "redact", "delet", "scrub", "wipe", "purge", "erase", "clears the file", "clears the flag",
                     "from both files", "from every file"):
            self.assertNotIn(word, rest, "a promise of removal is back in the passage: %r" % (word,))


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


class RuleStatementCount(unittest.TestCase):
    """extra8-1 (review round 5 of the env-pick door, 2026-09-19): the body's count of the credential-shape rule's
    statements was called non-behavioural and is not; it is pinned here by the definition the body states. A rule
    statement is a line matching `_API_KEY.{0,12}_TOKEN` that names 1Password on the same line or on the next (the
    two split statements: the boot notice's _log call and env_credential_names' docstring, each stating the suffix half
    with the 1Password half on the next line); a matching line with 1Password on neither is code (the suffix tuple,
    the reference lister's own test) and not a statement. Over kernel/, cli/, bin/, docs/ and ui/, with the
    bin/romp_sdk_backend.py symlink to kernel/sdk_backend.py excluded (it would count the module twice) and binary
    files skipped. Mutating one statement away (dropping 1Password from one) reds it."""
    DIRS = ("kernel", "cli", "bin", "docs", "ui")
    SKIP_DIRS = {"node_modules", "dist", "__pycache__", ".git"}
    PATTERN = re.compile(r"_API_KEY.{0,12}_TOKEN")

    def _statements(self):
        single, split, code = [], [], []
        for d in self.DIRS:
            for root, dirs, files in os.walk(ROOT / d):
                dirs[:] = sorted(x for x in dirs if x not in self.SKIP_DIRS and not os.path.islink(os.path.join(root, x)))
                for f in sorted(files):
                    path = os.path.join(root, f)
                    if os.path.islink(path):
                        continue
                    try:
                        data = Path(path).read_bytes()
                    except OSError:
                        continue
                    if b"\0" in data[:4096]:
                        continue
                    lines = data.decode("utf-8", errors="replace").splitlines()
                    for i, line in enumerate(lines):
                        if not self.PATTERN.search(line):
                            continue
                        rel = "%s:%d" % (os.path.relpath(path, ROOT), i + 1)
                        if "1Password" in line:
                            single.append(rel)
                        elif i + 1 < len(lines) and "1Password" in lines[i + 1]:
                            split.append(rel)
                        else:
                            code.append(rel)
        return single, split, code

    def test_the_rule_is_stated_fourteen_times_twelve_on_one_line_and_two_split(self):
        single, split, code = self._statements()
        self.assertTrue(os.path.islink(ROOT / "bin" / "romp_sdk_backend.py"), "the symlink the count excludes is a symlink")
        self.assertFalse([p for p in single + split + code if p.startswith("bin/romp_sdk_backend.py")])
        self.assertEqual((len(single), len(split)), (12, 2), "12 single-line statements and 2 split ones: %r / %r" % (single, split))
        self.assertEqual(sorted(p.split(":")[0] for p in split), ["kernel/sdk_backend.py", "kernel/sdk_backend.py"])
        self.assertEqual(sorted(p.split(":")[0] for p in code), ["docs/reference.md", "kernel/credentials.py"],
                         "the suffix tuple and the lister's own test are code, not statements: %r" % (code,))
        self.assertEqual(len(single) + len(split), 14)


# ── fork PR #781: the four readers of the credential-name population, held to ONE derived name set ────────────────
BIN = ROOT / "bin"


def _kernel_module():
    """The kernel under its standard module name, loaded once (the pattern of tests/test_session_env.py's
    ValidatorLockstep): its dependencies by the exact names it imports, a copy already in sys.modules reused rather
    than re-executed. The kernel's per-session env door (_env_error) lives there and cannot import sdk_backend at the
    door, so it is the reader most able to drift."""
    if "romp_kernel" in sys.modules:
        return sys.modules["romp_kernel"]
    os.environ.setdefault("ROMP_KERNEL_NO_OPEN", "1")
    for name, fn in (("romp_event_model", "romp-event-model"), ("romp_judge", "romp-judge")):
        if name not in sys.modules:
            load_source(name, str(BIN / fn))
    return load_source("romp_kernel", str(BIN / "romp-kernel"))


def _casings(name):
    """Five spellings of one name: as given, upper, lower, Title_Case and alternating. The rule folds case on both of
    its halves, so every spelling of a shaped name is shaped and every spelling of an unshaped one is not."""
    alternating = "".join(c.upper() if i % 2 else c.lower() for i, c in enumerate(name))
    return {name, name.upper(), name.lower(), name.title(), alternating}


def _fixture_name_census():
    """Every quoted identifier in tests/*.py that carries TOKEN or API_KEY, or begins OP_, in any letter case: the
    names the suite's fixtures use, shaped and near miss alike, read at run time so a fixture written later joins the
    population by itself. Names only; no value beside them is read."""
    out = set()
    for p in sorted((ROOT / "tests").glob("*.py")):
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"""["']([A-Za-z_][A-Za-z0-9_]*)["']""", text):
            n = m.group(1)
            u = n.upper()
            if "TOKEN" in u or "API_KEY" in u or u.startswith("OP_"):
                out.add(n)
    return out


def _population(cred):
    """ONE name population, derived from the GRAMMAR of the rule (kernel/credentials.py: CREDENTIAL_ENV_SUFFIXES,
    OP_ENV_NAMES, OP_ENV_PREFIX and CONTROL_TOKEN_VAR, read from the module and never retyped here): every suffix the
    rule names on a variety of stems, with the near misses of each (the suffix continued into a longer word, the
    suffix as an infix, the suffix bare, the suffix's word without its underscore, the word joined by a dash); every
    1Password spelling the rule names, continued, truncated and as the tail of another name; the session prefix with
    accounts, bare, without its underscore, as an infix, and a name that only begins like it; the control token; the
    three Claude credential names (AUTH_ENV_NAMES) and the two reserved identity names; names outside the shell
    alphabet (the empty name, a leading digit, a dash); all of it in every casing; and the fixture census. Every entry
    is a NAME: the values beside them are assembled at run time by the test."""
    suffixes = tuple(cred.CREDENTIAL_ENV_SUFFIXES)
    names = set()
    for stem in ("NOTES", "HF", "MY_SECRET", "SVC_00", "X9", "OPENROUTER", "ROMP_SERVE", "OP", "OP_SESSION", "A_B_C",
                 "ZZ_0000", "_"):
        for suf in suffixes:
            word = suf[1:]
            for n in (stem + suf, stem + suf + "IZER", stem + suf + "_BUDGET", word + "_" + stem, stem + word,
                      stem + "-" + word):
                names.update(_casings(n))
    for suf in suffixes:
        names.update(_casings(suf))
        names.update(_casings(suf[1:]))
        names.update(_casings(suf + "S"))
    for n in cred.OP_ENV_NAMES:
        names.update(_casings(n))
        names.update(_casings(n + "_2"))
        names.update(_casings(n[:-1]))
        names.update(_casings("X_" + n))
    prefix = cred.OP_ENV_PREFIX
    for account in ("TESTACCT", "notes", "a9"):
        names.update(_casings(prefix + account))
    names.update(_casings(prefix))
    names.update(_casings(prefix[:-1]))
    names.update(_casings("X_" + prefix + "acct"))
    names.update(_casings("OPTIONS_FOR_X"))
    names.update(_casings(cred.CONTROL_TOKEN_VAR))
    names.update(sb.AUTH_ENV_NAMES)
    names.update(sb.ENV_RESERVED_NAMES)
    names.update({"", "9LEADS" + suffixes[0], "MY-" + suffixes[0][1:], "X-Y" + suffixes[-1], "WITH-DASH", "DIGITS_123",
                  "PATH", "FEATURE_FLAG"})
    names.update(_fixture_name_census())
    return sorted(n for n in names if "=" not in n and "\0" not in n)


class FourReaders(unittest.TestCase):
    """The reviewer's ask on fork PR #781 (2026-09-21): the comment above CONTROL_TOKEN_VAR in kernel/credentials.py
    says the doors, the writer and the reference's lister agree on what a credential-shaped name is and only the boot
    line differs, and that is a four-reader agreement asserted in prose. This test reads all four over ONE population
    derived from the rule's grammar (_population) and asserts their agreement name by name, from the rule's verdict:

      the RULE         kernel/credentials.py is_credential_env_name and credential_env_names;
      the DOORS        kernel/kernel.py _env_error (POST /new, which `romp new --env` rides: the CLI has no shape test
                       of its own) and kernel/sdk_backend.py env_request_error (spawn, set_env), each driven directly
                       over a one-name pick; that the routes reach these functions is pinned by source, the weaker
                       guarantee, said in each message;
      the WRITER       kernel/sdk_backend.py split_spawn_secrets composed with kernel/host_transport.py
                       write_spawn_spec as _host_transport_for composes them, over a spec whose overlay carries the
                       whole population, the file read back;
      the LISTER       docs/reference.md: the fenced python3 -c listing, run as fenced over a flag-settings file
                       carrying the population (its predicate is a spelling of its own, since a copied command cannot
                       import credentials.py, so its literal tuples are also parsed and held to the rule's constants),
                       and the prose that spells the shape (the boot line's sentence, the `--env` passage, the
                       spawn.json sentence) and the 1Password spellings the boot check's paragraph lists, each parsed
                       into the suffixes and spellings it names and held to the rule's;
      the BOOT NOTICE  kernel/sdk_backend.py env_credential_names and _note_env_credential_names, the wrapper driven
                       over the population and the method over a staged environment, the line parsed back.

    The one permitted difference is the boot line leaving the control token unnamed, asserted positively: the rule
    shapes it, both doors refuse it, the writer moves it, the lister lists it, the notice drops it, its other spellings
    are named, and the exclusion is written down at both ends (the constant's comment and the wrapper's code). A door
    refuses a name outside the shell alphabet, or a reserved identity name, before the shape is consulted; those names
    are expected to hear that refusal, and every other reader still classifies them by the shape. Every value is
    assembled at run time (os.urandom), no message carries one, and a failure names the reader that drifted and the
    name it drifted on."""

    SID = "11111111-2222-3333-4444-555555555577"
    RULE = "the rule (kernel/credentials.py is_credential_env_name)"
    DOOR_KM = "the kernel door (kernel/kernel.py _env_error)"
    DOOR_SB = "the backend door (kernel/sdk_backend.py env_request_error)"
    WRITER = "the spawn.json writer (kernel/sdk_backend.py split_spawn_secrets + kernel/host_transport.py write_spawn_spec)"
    LISTER = "the reference lister (docs/reference.md)"
    NOTICE = "the boot notice (kernel/sdk_backend.py env_credential_names)"
    BEFORE_SHAPE_ALPHABET = "refused before the shape (outside the shell alphabet)"
    BEFORE_SHAPE_IDENTITY = "refused before the shape (a reserved identity name)"

    def setUp(self):
        patch.object(sb, "_ENV_CRED_NAMES_SAID", False).start()
        self.addCleanup(patch.stopall)
        self.root = tempfile.mkdtemp(prefix="romp-fourreaders-")
        self.addCleanup(shutil.rmtree, self.root, True)
        Path(self.root, "session-hosts").write_text("off\n")     # a state root minted here: hosts off, the suite's rule

    # ── one driver per reader ──
    def _door_verdict(self, door, name, value, cred):
        err = door({name: value})
        if not sb.ENV_NAME_RE.match(name):
            return self.BEFORE_SHAPE_ALPHABET if err.startswith("env: bad name") else "unexpected: " + err
        if name in sb.ENV_RESERVED_NAMES:
            return (self.BEFORE_SHAPE_IDENTITY if "is reserved" in err and "identity env" in err
                    else "unexpected: " + err)
        if name in sb.AUTH_ENV_NAMES:
            return (True if "is reserved: a session's credential is Claude Code's own" in err
                    else "unexpected: " + err)
        if err == "":
            return False
        if err == "env: " + cred.credential_env_refusal([name]):
            return True
        return "unexpected: " + err

    def _door_expected(self, name, shaped):
        if not sb.ENV_NAME_RE.match(name):
            return self.BEFORE_SHAPE_ALPHABET
        if name in sb.ENV_RESERVED_NAMES:
            return self.BEFORE_SHAPE_IDENTITY
        return shaped

    def _writer_verdicts(self, values):
        ht = sb._ht()
        spec = {"sid": self.SID, "name": "web", "cwd": self.root, "env": dict(values)}
        moved = sb.split_spawn_secrets(spec)
        path = ht.write_spawn_spec(self.root, self.SID, spec)
        text = path.read_text(encoding="utf-8")
        kept = json.loads(text).get("env") or {}
        out = {}
        for n, v in values.items():
            in_file, in_moved, value_in_text = (kept.get(n) == v), (moved.get(n) == v), (v in text)
            if in_moved and not in_file and not value_in_text:
                out[n] = True
            elif in_file and not in_moved and value_in_text:
                out[n] = False
            else:
                out[n] = ("inconsistent (kept in the file: %s, moved out: %s, value in the file's text: %s)"
                          % (in_file, in_moved, value_in_text))
        return out

    def _lister_verdicts(self, values):
        snippet = ReferenceLister._snippet()
        d = os.path.join(self.root, "sdk-flag-settings")
        os.makedirs(d)
        p = os.path.join(d, self.SID + ".json")
        Path(p).write_text(json.dumps({"env": values}) + "\n", encoding="utf-8")
        env = {"PATH": os.path.dirname(sys.executable) + os.pathsep + os.environ.get("PATH", ""),
               "ROMP_STATE_DIR": self.root, "HOME": self.root}
        r = subprocess.run(["/bin/sh", "-c", snippet], env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, "%s runs as fenced (exit %d)" % (self.LISTER, r.returncode))
        listed = set()
        for ln in r.stdout.splitlines():
            self.assertTrue(ln.startswith(p + " "), "%s prints the file, then the name" % self.LISTER)
            listed.add(ln[len(p) + 1:])
        return {n: (n in listed) for n in values}

    def _notice_verdicts(self, values, cred):
        named = set(sb.env_credential_names(values))                 # the wrapper over the population as an environ
        # the method reads os.environ: the population is staged on top of it for the call, the empty name left out
        # (putenv refuses it) and any name the process already carries left out too, so no live variable is touched
        stageable = {n: v for n, v in values.items() if n and n not in os.environ}
        be = sb.SdkBackend.__new__(sb.SdkBackend)
        rows = []
        be._log = lambda m, problem=None, **kw: rows.append((m, problem))
        with patch.dict(os.environ, stageable, clear=False):
            expect_line = set(sb.env_credential_names(os.environ))    # the wrapper over the very environment the method read
            be._note_env_credential_names()
        self.assertEqual(len(rows), 1, "%s: one line at boot" % self.NOTICE)
        line, problem = rows[0]
        self.assertIs(problem, False, "%s: information, never a problem row" % self.NOTICE)
        m = re.search(r"environment\): (.*)\. Values are never logged", line)
        self.assertTrue(m, "%s: the line lists its names between the shape clause and the values sentence" % self.NOTICE)
        on_line = set(m.group(1).split(", "))
        self.assertEqual(on_line, expect_line, "%s: the line names exactly what the wrapper names over the environment it read" % self.NOTICE)
        self.assertEqual(on_line & set(stageable), {n for n in named if n in stageable},
                         "%s: over the staged population the line is the wrapper's verdict, name for name" % self.NOTICE)
        self.assertGreater(len(on_line & set(stageable)), 100, "%s: the staged population reached the line" % self.NOTICE)
        clause = re.search(r"\(([^()]*1Password[^()]*)\)", line)
        self.assertTrue(clause, "%s: the line carries a shape clause naming the 1Password half" % self.NOTICE)
        self.assertEqual(set(re.findall(r"_[A-Z][A-Z_]*", clause.group(1))), set(cred.CREDENTIAL_ENV_SUFFIXES),
                         "%s: the suffixes its clause names are the rule's" % self.NOTICE)
        for v in values.values():
            self.assertNotIn(v, line, "%s: names only, never a value" % self.NOTICE)
        return {n: (n in named) for n in values}

    # ── the spellings in the reference, and the routes, by source ──
    def _shape_clause(self, clause, cred, where):
        tokens = re.findall(r"`([^`]+)`", clause)
        self.assertEqual({t for t in tokens if t.startswith("_")}, set(cred.CREDENTIAL_ENV_SUFFIXES),
                         "%s, %s: the suffixes it lists are the rule's" % (self.LISTER, where))
        for g in (t for t in tokens if t.endswith("*")):
            for n in cred.OP_ENV_NAMES + (cred.OP_ENV_PREFIX,):
                self.assertTrue(n.startswith(g[:-1]), "%s, %s: %s covers every 1Password spelling the rule names (%s)"
                                % (self.LISTER, where, g, n))
        self.assertIn("1Password", clause, "%s, %s: names the 1Password half" % (self.LISTER, where))
        self.assertIn("in any letter case", clause, "%s, %s: says the fold" % (self.LISTER, where))

    def _pin_lister_spellings(self, cred):
        snippet = ReferenceLister._snippet()
        ends = re.search(r"u\.endswith\(\((.*?)\)\)", snippet)
        starts = re.search(r'u\.startswith\("([^"]*)"\)', snippet)
        exact = re.search(r"u in \((.*?)\)", snippet)
        self.assertTrue(ends and starts and exact,
                        "%s: the fenced listing spells a suffix tuple, a prefix and a tuple of exact names" % self.LISTER)
        self.assertEqual(set(ast.literal_eval("(" + ends.group(1) + ",)")), set(cred.CREDENTIAL_ENV_SUFFIXES),
                         "%s: the suffix tuple the fenced listing spells is the rule's" % self.LISTER)
        self.assertEqual(starts.group(1), cred.OP_ENV_PREFIX,
                         "%s: the prefix the fenced listing spells is the rule's" % self.LISTER)
        self.assertEqual(set(ast.literal_eval("(" + exact.group(1) + ",)")), set(cred.OP_ENV_NAMES),
                         "%s: the 1Password names the fenced listing spells are the rule's" % self.LISTER)
        flat = " ".join((ROOT / "docs" / "reference.md").read_text(encoding="utf-8").split())
        for where, pattern in (("the boot line's sentence", r"shaped like credentials \(([^)]*)\)"),
                               ("the --env passage", r"credential-shaped variable with a non-empty value \((.*?);"),
                               ("the spawn.json sentence", r"carrying a value that ends (.*?) is left out of the file")):
            m = re.search(pattern, flat)
            self.assertTrue(m, "%s: %s is where this test reads the shape" % (self.LISTER, where))
            self._shape_clause(m.group(1), cred, where)
        op = re.search(r"1Password CLI's names \(([^:]*):", flat)
        self.assertTrue(op, "%s: the boot check's paragraph lists the 1Password spellings" % self.LISTER)
        self.assertEqual(set(re.findall(r"`([^`]+)`", op.group(1))), set(cred.OP_ENV_NAMES) | {cred.OP_ENV_PREFIX + "*"},
                         "%s: the 1Password spellings the reference lists are the rule's" % self.LISTER)
        self.assertIn("romp's own `%s` is refused like any other" % cred.CONTROL_TOKEN_VAR, flat,
                      "%s: the --env passage says the doors refuse the control token" % self.LISTER)

    def _pin_routes_by_source(self, km, cred):
        """The weaker guarantee, said as such: each route still reaches the function the executed checks drive."""
        ksrc = (ROOT / "kernel" / "kernel.py").read_text(encoding="utf-8")
        self.assertIn("eerr = _env_error(env_req", ksrc,
                      "POST /new reaches %s (a source pin; the executed check is on _env_error itself)" % self.DOOR_KM)
        self.assertIn("credential_env_names(env)", inspect.getsource(km._env_error),
                      "%s judges by the rule (a source pin; the executed check is the verdict table)" % self.DOOR_KM)
        for route in (sb.SdkBackend.spawn, sb.SdkBackend.set_env):
            self.assertIn("env_request_error(env", inspect.getsource(route),
                          "%s reaches %s (a source pin; the executed check is on env_request_error itself)"
                          % (route.__name__, self.DOOR_SB))
        self.assertIn("spawn_env_secret_names(env)", inspect.getsource(sb.env_request_error),
                      "%s judges by the writer's shape (a source pin; the executed check is the verdict table)" % self.DOOR_SB)
        self.assertIn("credential_env_names(", inspect.getsource(sb.spawn_env_secret_names),
                      "%s judges by the rule (a source pin; the executed check is the file read back)" % self.WRITER)
        launch = inspect.getsource(sb.SdkBackend._host_transport_for)
        self.assertLess(launch.index("split_spawn_secrets(spec)"), launch.index("write_spawn_spec(self.state_dir, sess.sid, spec)"),
                        "%s: the launch splits the overlay before it writes the file, as this test composes them (a source pin)"
                        % self.WRITER)
        romp = (ROOT / "bin" / "romp").read_text(encoding="utf-8")
        branch = re.search(r"--env\)\s+shift(.*?)--no-env\)", romp, re.S)
        self.assertTrue(branch, "romp new's --env branch is where this test reads the CLI")
        for probe in cred.CREDENTIAL_ENV_SUFFIXES + ("credential_env", "is_credential"):
            self.assertNotIn(probe, branch.group(1),
                             "romp new --env has no shape test of its own (%r): the pick rides POST /new and %s answers, "
                             "so a copy here would be a fifth reader" % (probe, self.DOOR_KM))

    # ── the one permitted difference, asserted positively ──
    def _pin_the_one_difference(self, cred, verdicts, values):
        ctl = cred.CONTROL_TOKEN_VAR
        self.assertTrue(cred.is_credential_env_name(ctl), "%s shapes the control token" % self.RULE)
        self.assertEqual(cred.credential_env_names({ctl: values[ctl]}), [ctl], "%s names it over an environ" % self.RULE)
        self.assertEqual(sb.env_credential_names({ctl: values[ctl]}), [], "%s leaves it unnamed" % self.NOTICE)
        for reader in (self.DOOR_KM, self.DOOR_SB, self.WRITER, self.LISTER):
            self.assertIs(verdicts[reader][ctl], True, "%s treats the control token as a credential, like any other" % reader)
        self.assertIs(verdicts[self.NOTICE][ctl], False, "%s: the one permitted difference" % self.NOTICE)
        for other in _casings(ctl) - {ctl}:
            self.assertIs(verdicts[self.NOTICE][other], True,
                          "%s: the exclusion is the exact name romp reads; %r is named" % (self.NOTICE, other))
        wsrc = inspect.getsource(sb.env_credential_names)
        self.assertIn("CONTROL_TOKEN_VAR", wsrc.rsplit('"""', 1)[1],
                      "%s: the exclusion is the wrapper's code, keyed on the constant" % self.NOTICE)
        self.assertIn(ctl, wsrc, "%s: its docstring names the token it leaves unnamed" % self.NOTICE)
        csrc = (ROOT / "kernel" / "credentials.py").read_text(encoding="utf-8")
        above = csrc[:csrc.index("\nCONTROL_TOKEN_VAR = ")].splitlines()[-6:]
        comment = " ".join(ln.lstrip("# ") for ln in above if ln.startswith("#"))
        self.assertIn("BOOT NOTICE", comment, "the constant's comment states the deliberate boot-line exclusion")
        self.assertIn("env_credential_names", comment, "and names the wrapper that carries it")

    def test_four_readers_agree_with_the_rule_on_one_derived_population_and_the_boot_line_alone_drops_the_control_token(self):
        cred = sb._cred
        km = _kernel_module()
        population = _population(cred)
        values = {n: "synthetic-" + os.urandom(8).hex() for n in population}
        rule = {n: cred.is_credential_env_name(n) for n in population}
        shaped = {n for n in population if rule[n]}
        # the population is what it claims: large, two-sided, and carrying its witnesses (a derived set must fail on empty)
        self.assertGreater(len(population), 500, "the derived population")
        self.assertGreater(len(shaped), 150, "shaped names in it")
        self.assertGreater(len(population) - len(shaped), 150, "unshaped names in it")
        for witness in (cred.CONTROL_TOKEN_VAR,) + tuple(sb.AUTH_ENV_NAMES) + tuple(cred.OP_ENV_NAMES) + tuple(sb.ENV_RESERVED_NAMES):
            self.assertIn(witness, population, witness)
        outside = [n for n in population if not sb.ENV_NAME_RE.match(n)]
        self.assertGreaterEqual(len(outside), 4, "names outside the shell alphabet: %r" % (outside,))
        self.assertTrue(any(rule[n] for n in outside) and any(not rule[n] for n in outside),
                        "the alphabet's outsiders are shaped and unshaped alike: %r" % (outside,))
        self.assertEqual(cred.credential_env_names(values), sorted(shaped), "%s over the population as an environ" % self.RULE)
        # the reference's spellings and the routes first: a suffix added to the rule, or dropped from the document, reds here
        self._pin_lister_spellings(cred)
        self._pin_routes_by_source(km, cred)
        # every reader over every name, then one comparison against the rule
        verdicts = {
            self.DOOR_KM: {n: self._door_verdict(km._env_error, n, values[n], cred) for n in population},
            self.DOOR_SB: {n: self._door_verdict(sb.env_request_error, n, values[n], cred) for n in population},
            self.WRITER: self._writer_verdicts(values),
            self.LISTER: self._lister_verdicts(values),
            self.NOTICE: self._notice_verdicts(values, cred),
        }
        expected = {
            self.DOOR_KM: {n: self._door_expected(n, rule[n]) for n in population},
            self.DOOR_SB: {n: self._door_expected(n, rule[n]) for n in population},
            self.WRITER: dict(rule),
            self.LISTER: dict(rule),
            self.NOTICE: {n: rule[n] and n != cred.CONTROL_TOKEN_VAR for n in population},
        }
        report = []
        for reader in verdicts:
            bad = [(n, verdicts[reader][n], expected[reader][n]) for n in population if verdicts[reader][n] != expected[reader][n]]
            if bad:
                report.append("%s drifted on %d of %d names, the first %d: %s"
                              % (reader, len(bad), len(population), min(len(bad), 8),
                                 "; ".join("%r is %r where the rule expects %r" % b for b in bad[:8])))
        if report:
            self.fail("readers drifting from the rule (every drifting reader named, with the names it drifted on):\n"
                      + "\n".join(report))
        self._pin_the_one_difference(cred, verdicts, values)

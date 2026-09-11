#!/usr/bin/env python3
"""ROMP_EXPECTED_AUTH — the box-wide intended-auth declaration (the user 2026-08-15).

On a machine whose sessions authenticate through Claude Code's apiKeyHelper the key never rides
service.env, so _launched_keyed reads "login" for every session while key auth IS the design — and
the per-init apiKeySource mismatch line was a permanent false alarm. The mechanics under test:

  * ROMP_EXPECTED_AUTH=key|login in the manager env declares the intended side; unset (or junk)
    preserves the launch-intent comparison exactly as it was. Under a declaration the landing that
    MATCHES is quiet and the landing that CONTRADICTS is the problem-ring entry, naming the
    declaration — the never-silent property inverts, it never disappears.
  * api_key_auth persists (reg apiKeyAuth) and restores on construction, with auth_live ("what the
    CLI actually reported") beside it: as a runtime-only default-False flag, a keyed session's
    rate-limit events landed in the login's usage.json between a kernel restart and its next init.
  * An all-keyed box fails loudly, not silently: refresh_usage says "no session can poll" once per
    episode (the rail timer calls it every 60s), as a problem only when no declaration explains it;
    the keyed no-window payload carries spend and nothing about rate limits (the notice was deleted 2026-08-24)
    the bars are absent.
  * The declaration also SEEDS the unpicked billing intent (the user 2026-09-09, whose every session
    read "login" on an apiKeyHelper box): with no key of romp's and no pick, effective_auth and
    default_auth read the declared side (unpicked_auth); a pick, explicit or remembered, still wins,
    and nothing is written to the reg (authPicked stays False). A remembered KEY pick on a box with no
    key source is one spawn sets aside, and under it the declaration speaks again (review round 1,
    2026-09-09). The kernel's picker default (_auth_avail) calls the backend's new_session_auth
    directly, one rule and one order with the backend (the box's key before the declaration), executed
    here on a REAL backend; _bills_login's fallback for a row that reports nothing reads the key's
    presence instead, not _auth_key_present() (the 2026-09-10 fold, ruling K2; pinned in
    tests/test_retry_pause_autoresume.py), and a row that reports outranks the declaration; and the
    live merge forwards authLive and authPicked, which it had dropped since the field was born. The
    defaults file behind the declaration read is parsed once per file identity, since the read is per
    row.
  * The three remedies a contradicting init files name the helper, Claude Code's apiKeyHelper or the
    login, and the manager's environment, and no longer a key in service.env (romp reads no key from a
    file since 2026-09-08; the 2026-09-09 fold's review found the parenthetical dropped with no test
    that failed before the drop). Each branch is driven and its sentence pinned exactly.

Synthetic sids/paths only; no real key material or session data.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = load_source("romp_sdk_backend_expected", os.path.join(BIN, "romp_sdk_backend.py"))
km = load_source("romp_kernel_expected", os.path.join(BIN, "romp-kernel"))


class _Declared(unittest.TestCase):
    """Base: a backend with captured logs and a clean ROMP_EXPECTED_AUTH slate (each test sets its
    own declaration; the world is restored after)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._exp_before = os.environ.pop("ROMP_EXPECTED_AUTH", None)
        self.logs = []
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=self.logs.append)

    def tearDown(self):
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        if self._exp_before is not None:
            os.environ["ROMP_EXPECTED_AUTH"] = self._exp_before

    def _sess(self, n=1, **reg):
        return sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-%012d" % n,
                                       "name": "s%d" % n, "cwd": "/tmp", **reg})

    def _problem_texts(self):
        return [p["text"] for p in self.be.problems(20)]


class DeclarationParsing(_Declared):
    def test_key_login_and_nothing_else(self):
        for raw, want in (("key", "key"), ("login", "login"), (" Key ", "key"),
                          ("LOGIN", "login"), ("both", ""), ("1", ""), ("", "")):
            os.environ["ROMP_EXPECTED_AUTH"] = raw
            self.assertEqual(sb._expected_auth(), want, "raw=%r" % raw)
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        self.assertEqual(sb._expected_auth(), "", "unset declares nothing")


class DeclarationInvertsTheMismatch(_Declared):
    """The apiKeyHelper box: launched WITHOUT a key in the env (_launched_keyed False), the CLI
    finds one through the helper. Undeclared that rings every init; declared =key it is the
    intended, quiet state — and the LOGIN landing becomes the flagged anomaly."""

    def test_declared_key_and_a_keyed_landing_is_quiet(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        s = self._sess(1)
        s._launched_keyed = False                       # no key rode service.env — the helper box
        self.be._note_auth_source(s, "apiKeyHelper")
        self.assertFalse([t for t in self._problem_texts() if "billing" in t],
                         "the intended landing must not ring")
        self.assertTrue(any("apiKeySource=" in m for m in self.logs),
                        "…but the state-change info line still self-documents the box")

    def test_declared_key_and_a_login_landing_rings_naming_the_declaration(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        s = self._sess(2)
        s._launched_keyed = False
        self.be._note_auth_source(s, "none")            # the helper failed — billing the login
        texts = self._problem_texts()
        self.assertTrue(any("ROMP_EXPECTED_AUTH=key" in t and "billing the login" in t
                            for t in texts),
                        "the inverted check flags the contradicting landing, naming the "
                        "declaration: %r" % texts)

    def test_declared_login_and_a_keyed_landing_rings(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        s = self._sess(3)
        s._launched_keyed = False
        self.be._note_auth_source(s, "apiKeyHelper")
        texts = self._problem_texts()
        self.assertTrue(any("ROMP_EXPECTED_AUTH=login" in t and "billing the API key" in t
                            for t in texts), texts)

    def test_the_declaration_beats_the_launch_intent(self):
        # launched keyed (the key WAS injected) but the box declares login: the login landing that
        # the old comparison would flag is now the intended one — quiet.
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        s = self._sess(4)
        s._launched_keyed = True
        self.be._note_auth_source(s, "none")
        self.assertFalse([t for t in self._problem_texts() if "billing" in t],
                         "the declared side is the expected side, whatever _options injected")

    def test_undeclared_keeps_todays_wording_exactly(self):
        s = self._sess(5)
        s._launched_keyed = False
        self.be._note_auth_source(s, "apiKeyHelper")
        texts = self._problem_texts()
        self.assertTrue(any("launched for the login but the CLI reports" in t
                            and "Check the login (claude /login) and the manager's environment" in t
                            for t in texts),
                        "no declaration → the launch-intent comparison, verbatim: %r" % texts)

    def test_every_remedy_names_the_helper_or_the_login_and_never_a_key_file(self):
        # The three remedies ended in "(or service.env, where your installation allows a key in a file)"
        # until the 2026-09-09 fold's round 5 (review finding F4): romp reads no key from a file since
        # 2026-09-08, so the parenthetical sent the reader to a source that no longer exists. Every branch
        # of the check is driven here and its remedy pinned exactly as the row's tail (the ring row's text
        # is the logged line verbatim, so nothing follows the remedy): a declaration contradicted, in both
        # its wordings (the env word and the remembered pick); an explicit key pick that launched with
        # nothing injected and landed on the login; and the launch-intent comparison, both directions.
        RETIRED = "service.env, where your installation allows a key in a file"
        HELPER = "Check the helper and the manager's environment."
        PICK = "Check Claude Code's apiKeyHelper (romp injected nothing) and the manager's environment."
        LOGIN = "Check the login (claude /login) and the manager's environment."

        def filed(sess, source):
            before = self._problem_texts()
            self.be._note_auth_source(sess, source)
            new = [t for t in self._problem_texts() if t not in before and "billing the" in t]
            self.assertEqual(len(new), 1, "one billing row per contradicting init: %r" % new)
            return new[0]

        rows = []
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        s = self._sess(31)
        s._launched_keyed = False
        rows.append((filed(s, "none"), "ROMP_EXPECTED_AUTH=key", HELPER))
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        s = self._sess(32)
        s._launched_keyed = False
        rows.append((filed(s, "apiKeyHelper"), "ROMP_EXPECTED_AUTH=login", HELPER))
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        s = self._sess(33, auth="key")                  # the pick meant Claude Code's own key
        s._launched_keyed = False
        s._launched_unkeyed_pick = True
        rows.append((filed(s, "none"), "launched for the API key", PICK))
        s = self._sess(34)
        s._launched_keyed = False
        rows.append((filed(s, "apiKeyHelper"), "launched for the login", LOGIN))
        s = self._sess(35)
        s._launched_keyed = True
        rows.append((filed(s, "none"), "launched for the API key", LOGIN))
        sb.write_sdk_default(Path(self.d), auth="login")   # written last: the env word is inert after it
        s = self._sess(36)
        s._launched_keyed = False
        rows.append((filed(s, "apiKeyHelper"), "the remembered Billing pick is login", HELPER))

        for text, lead, remedy in rows:
            self.assertIn(lead, text)
            self.assertTrue(text.endswith(" " + remedy),
                            "the remedy is the row's last sentence, exactly: %r" % text)
            self.assertNotIn(RETIRED, text)
            self.assertNotIn("service.env", text, "no remedy sends the reader to a key file: %r" % text)
        self.assertEqual({r for _, _, r in rows}, {HELPER, PICK, LOGIN}, "all three remedies were driven")


class AllKeyedUsageLineHonorsTheDeclaration(_Declared):
    """The refresh_usage all-keyed line rings as a PROBLEM exactly when the state contradicts (or
    lacks) a declaration: =key → the box working as designed, an info line; =login → all-keyed
    CONTRADICTS the declaration and must ring; undeclared → the surprising case, rings as before.
    `not _expected_auth()` muted the contradiction — the one state the declaration exists to flag."""

    def _all_keyed_box(self, n=7):
        s = self._sess(n)
        s.client, s.loop, s.ended, s.api_key_auth = object(), object(), False, True
        self.be.sessions[s.sid] = s
        return s

    def _usage_problems(self):
        return [p for p in self.be.problems(20) if "telemetry is unavailable" in p["text"]]

    def test_declared_key_is_an_info_line(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        self._all_keyed_box()
        self.be.refresh_usage()
        self.assertFalse(self._usage_problems(), "all-keyed under =key is the design, not a problem")

    def test_declared_login_rings_the_contradiction(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        self._all_keyed_box()
        self.be.refresh_usage()
        self.assertTrue(self._usage_problems(), "all-keyed CONTRADICTS =login — it must ring")

    def test_undeclared_still_rings(self):
        self._all_keyed_box()
        self.be.refresh_usage()
        self.assertTrue(self._usage_problems(), "undeclared all-keyed stays the surprising case")


class GearPickMakesTheDeclarationInert(_Declared):
    """Q3 (2026-08-26): ONE explicit gear Billing pick supersedes ROMP_EXPECTED_AUTH from then on —
    the env var described the box's UNPICKED design, and once billing is hand-managed its per-init
    alarms fought the user's own choice on every spawn re-seeded from the remembered default. The
    pick's durable trace is the remembered auth default (set_auth is its only writer), so inertness
    keys on the PICK EVENT — a spawn's seeded reg.auth never counts as explicit."""

    def test_the_pick_supersedes_the_env_declaration(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        sb.write_sdk_default(Path(self.d), auth="login")   # set_auth's durable trace — the gear pick
        s = self._sess(11)
        s._launched_keyed = True
        self.be._note_auth_source(s, "none")               # a login landing: contradicts the ENV, honors the PICK
        self.assertFalse([t for t in self._problem_texts() if "billing" in t],
                         "the env declaration is INERT after the pick — no false alarm")
        s2 = self._sess(12)
        s2._launched_keyed = False
        self.be._note_auth_source(s2, "apiKeyHelper")      # a keyed landing: contradicts the PICK
        texts = self._problem_texts()
        self.assertTrue(any("the remembered Billing pick is login" in t and "billing the API key" in t
                            for t in texts),
                        "a landing contradicting the pick rings, NAMING THE PICK not the env var: %r" % texts)
        self.assertFalse(any("ROMP_EXPECTED_AUTH" in t for t in texts),
                         "the env var no longer speaks anywhere once picked")

    def test_a_seeded_spawn_never_makes_the_declaration_inert(self):
        # the remembered default SEEDS reg.auth on a spawn — that seed must not count as explicit:
        # with no pick trace in the defaults, the env declaration still governs
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        s = self._sess(13, auth="key")                     # a spawn re-seeded from some remembered default
        s._launched_keyed = True
        self.be._note_auth_source(s, "none")               # lands on login — contradicts its own seed
        texts = self._problem_texts()
        self.assertTrue(any("billing the login" in t for t in texts),
                        "the seeded session is still judged (against its own pick side): %r" % texts)
        self.assertFalse(any("remembered Billing pick" in t for t in texts),
                         "…but nothing pretends a remembered default was an explicit box-wide pick")

    def test_all_keyed_gate_follows_the_pick(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        sb.write_sdk_default(Path(self.d), auth="key")     # the user picked key billing by hand
        be2 = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None, log=self.logs.append)
        s = sb.SdkSession(be2, {"sid": "11111111-2222-3333-4444-%012d" % 14, "name": "s14", "cwd": "/tmp"})
        s.connected = True
        s.api_key_auth = True
        be2.sessions[s.sid] = s
        be2.refresh_usage()
        probs = [p for p in be2.problems(20) if "telemetry is unavailable" in p["text"]]
        self.assertFalse(probs, "all-keyed under a KEY pick is the design — an info line, not a problem "
                                "(the env =login is inert)")

    def test_the_real_set_auth_leaves_the_trace(self):
        # end to end: the gear pick itself writes the durable trace _declared_auth keys on
        sb.write_reg(Path(self.d), "11111111-2222-3333-4444-%012d" % 15,
                     {"sid": "11111111-2222-3333-4444-%012d" % 15, "name": "s15", "cwd": "/tmp"})
        self.assertTrue(self.be.set_auth("11111111-2222-3333-4444-%012d" % 15, "login"))
        self.assertEqual(sb._declared_auth(Path(self.d)), ("login", "pick"))


class LoginPickNeedsALogin(_Declared):
    """T124 (2026-08-27): set_auth accepted 'login' UNCONDITIONALLY while gating 'key' on work_key —
    so on a box with no Claude login the pick sat in the UI as applied fact while the applying
    reconnect errored or landed keyed through an apiKeyHelper (the silent-degrade class). The pick
    now refuses at pick time via the kernel-wired credential probe; a bare backend stays
    permissive (tests, no kernel), and a REFUSED pick writes nothing — no reg flip, no remembered
    default, no pending window."""

    def _reg(self, n):
        sid = "11111111-2222-3333-4444-%012d" % n
        sb.write_reg(Path(self.d), sid, {"sid": sid, "name": "s%d" % n, "cwd": "/tmp"})
        return sid

    def test_refused_when_the_probe_says_no_login(self):
        self.be.login_ok = lambda: False
        sid = self._reg(21)
        self.assertFalse(self.be.set_auth(sid, "login"),
                         "refuse loudly at pick time — the box demonstrably lacks the credential")
        reg = sb.read_reg(Path(self.d), sid)
        self.assertNotIn("auth", reg or {}, "a refused pick flips nothing")
        self.assertFalse((reg or {}).get("authPending"), "…and opens no pending window")
        self.assertNotEqual(sb._declared_auth(Path(self.d))[1], "pick",
                            "…and leaves no remembered-default trace (the Q3 marker stays honest)")

    def test_accepted_when_the_probe_says_yes(self):
        self.be.login_ok = lambda: True
        sid = self._reg(22)
        self.assertTrue(self.be.set_auth(sid, "login"))
        self.assertEqual((sb.read_reg(Path(self.d), sid) or {}).get("auth"), "login")

    def test_unwired_backend_stays_permissive(self):
        sid = self._reg(23)
        self.assertTrue(self.be.set_auth(sid, "login"),
                        "no kernel probe wired → the pre-T124 behavior stands (bare backends, old tests)")


class PickOutranksTheDeclaration(_Declared):
    """An explicit per-session Billing pick (sess.auth) beats the box-wide declaration: the
    declaration describes the box's UNPICKED design, and set_auth's contract is that the next
    init confirms the PICK — judged, and worded, against what the pick launched."""

    def test_a_declared_box_with_an_honored_opposite_pick_is_quiet(self):
        # declared =key, but THIS session was explicitly picked to the login and landed there
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        s = self._sess(6, auth="login")
        s._launched_keyed = False
        self.be._note_auth_source(s, "none")
        self.assertFalse([t for t in self._problem_texts() if "billing" in t],
                         "a landing honoring the pick is intended, whatever the box declares")

    def test_a_landing_contradicting_the_pick_rings_even_when_it_matches_the_declaration(self):
        # declared =key AND the CLI landed keyed — but the user picked the login for THIS session:
        # billing against the pick must never pass silently, and the ring speaks the launch-intent
        # wording (the pick's side), never the declaration's
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        s = self._sess(7, auth="login")
        s._launched_keyed = False
        self.be._note_auth_source(s, "apiKeyHelper")
        texts = self._problem_texts()
        self.assertTrue(any("launched for the login but the CLI reports" in t
                            and "billing the API key" in t for t in texts), texts)
        self.assertFalse(any("ROMP_EXPECTED_AUTH" in t for t in texts),
                         "the pick's wording, not the declaration's: %r" % texts)


class SetAuthInvalidatesTheLiveReport(_Declared):
    """auth_live is DISPLAY truth from a live CLI report, and set_auth reconnects to apply — the
    process that made the report no longer exists once the switch lands. The report and its
    persisted reg twin clear with the pick, so the Billing row falls back to the plain intent
    until the next init re-confirms, and a kernel restart cannot resurrect the old side as a
    false "CLI reports" disagreement."""

    def test_the_pick_clears_the_report_live_persisted_and_dormant(self):
        sid = self.be.spawn("n", "/tmp")
        s = sb.SdkSession(self.be, sb.read_reg(self.be.state_dir, sid))
        self.be.sessions[sid] = s
        self.be._note_auth_source(s, "apiKeyHelper")     # an init landed: the CLI reported the key
        self.assertEqual(s.auth_live, "key")
        self.assertTrue(self.be.set_auth(sid, "login"))
        self.assertEqual(s.auth_live, "", "the report described the replaced process")
        self.assertEqual(s.snapshot()["authLive"], "", "…so no live-row disagreement")
        s2 = sb.SdkSession(self.be, sb.read_reg(self.be.state_dir, sid))
        self.assertEqual((s2.auth_live, s2.api_key_auth), ("", False),
                         "a restart restores 'no init yet', never the old side")
        self.assertEqual(self.be.live_sessions()[sid]["authLive"], "",
                         "the dormant row claims nothing either")


class ApiKeyAuthPersists(_Declared):
    """The flag is written to the reg on every flip and restored on construction — the post-restart
    window where a keyed session read False (and its rate-limit events contaminated the login's
    usage.json via the max-merge) is closed."""

    def _reg(self, sid):
        return sb.read_reg(self.be.state_dir, sid)

    def test_a_flip_writes_the_reg_and_construction_restores_it(self):
        sid = self.be.spawn("n", "/tmp")
        s = sb.SdkSession(self.be, self._reg(sid))
        self.assertEqual((s.api_key_auth, s.auth_live), (False, ""),
                         "a fresh session: no init has ever landed")
        self.be._note_auth_source(s, "apiKeyHelper")
        self.assertIs(self._reg(sid)["apiKeyAuth"], True)
        s2 = sb.SdkSession(self.be, self._reg(sid))
        self.assertTrue(s2.api_key_auth, "restored — not reset to False until the next init")
        self.assertEqual(s2.auth_live, "key", "the Billing row keeps the CLI's truth too")

    def test_the_flip_back_to_login_persists_the_same_way(self):
        sid = self.be.spawn("n", "/tmp")
        s = sb.SdkSession(self.be, self._reg(sid))
        self.be._note_auth_source(s, "ANTHROPIC_API_KEY")
        self.be._note_auth_source(s, "none")
        self.assertIs(self._reg(sid)["apiKeyAuth"], False)
        s2 = sb.SdkSession(self.be, self._reg(sid))
        self.assertFalse(s2.api_key_auth)
        self.assertEqual(s2.auth_live, "login")

    def test_the_first_login_report_persists_and_a_repeat_does_not(self):
        # a login session's FIRST init equals the flag's default, and until 2026-09-09 the early return
        # skipped the write: a restart then restored auth_live "" ("no init ever landed") for a session
        # whose CLI had spoken, and the Billing row fell back to the intent. The first report persists
        # whichever side it names; a repeat of the same side writes nothing more.
        sid = self.be.spawn("n", "/tmp")
        s = sb.SdkSession(self.be, self._reg(sid))
        self.be._note_auth_source(s, "none")
        self.assertEqual(s.auth_live, "login", "the runtime truth is set on every init")
        self.assertIs(self._reg(sid)["apiKeyAuth"], False, "the first report is on record")
        s2 = sb.SdkSession(self.be, self._reg(sid))
        self.assertEqual((s2.auth_live, s2.api_key_auth), ("login", False),
                         "a restart restores the CLI's report, not 'no init yet'")
        writes = []
        real = self.be._update_reg
        self.be._update_reg = lambda sid_, **f: writes.append(f) or real(sid_, **f)
        try:
            self.be._note_auth_source(s2, "none")
        finally:
            self.be._update_reg = real
        self.assertEqual([w for w in writes if "apiKeyAuth" in w], [], "the same side again: no write")


class AuthLiveOnTheWire(_Declared):
    def test_snapshot_reports_the_cli_truth_beside_the_intent(self):
        s = self._sess(1, auth="login")
        self.assertEqual(s.snapshot()["authLive"], "", "unknown until an init lands")
        self.be._note_auth_source(s, "apiKeyHelper")
        snap = s.snapshot()
        self.assertEqual(snap["auth"], "login", "the launch intent stays what it was")
        self.assertEqual(snap["authLive"], "key", "…and the live truth rides beside it")

    def test_dormant_rows_carry_the_persisted_truth(self):
        sid = self.be.spawn("n", "/tmp")
        self.be._update_reg(sid, apiKeyAuth=True)
        self.assertEqual(self.be.live_sessions()[sid]["authLive"], "key")
        sid2 = self.be.spawn("m", "/tmp")
        self.assertEqual(self.be.live_sessions()[sid2]["authLive"], "",
                         "no persisted report — a dormant row claims nothing")

    def test_the_kernel_payload_passes_it_through(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn('"authLive": tm.get("authLive", "")', src,
                      "the tab-hover Billing row reads the live truth off the session payload")
        self.assertIn('"authPicked": bool(tm.get("authPicked"))', src,
                      "…and whether the intent beside it is an explicit pick")
        # the merge that builds the map the payload reads: until 2026-09-09 it forwarded `auth` and
        # `authPending` from the SDK row and dropped `authLive`, so the payload's read above was always ""
        self.assertIn('"authLive": st.get("authLive", "")', src, "Sessions.live forwards the CLI's report")
        self.assertIn('"authPicked": bool(st.get("authPicked"))', src)


class DeclarationSeedsTheUnpickedDefault(_Declared):
    """The declaration decides what an UNPICKED session bills when romp holds no key (the user 2026-09-09:
    every session on an apiKeyHelper box read "login" as its intent, so the hover said Login for sessions
    whose CLI reported the key). The reg is not written: a seeded default is not a pick (authPicked False),
    and a pick, explicit or remembered, still wins, the declaration inert under it (_declared_auth)."""

    def test_declared_key_seeds_the_unpicked_intent_without_writing_a_pick(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        self.assertFalse(self.be.key_available, "no apiKeyHelper in the test's settings: the box reads as keyless")
        self.assertEqual(self._sess(1).effective_auth(), "key")
        sid = self.be.spawn("n", "/tmp")
        self.assertNotIn("auth", sb.read_reg(self.be.state_dir, sid), "a seeded default is not a pick")
        row = self.be.live_sessions()[sid]
        self.assertEqual((row["auth"], row["authPicked"]), ("key", False), "the dormant row reads the same")
        s = sb.SdkSession(self.be, sb.read_reg(self.be.state_dir, sid))
        snap = s.snapshot()
        self.assertEqual((snap["auth"], snap["authPicked"]), ("key", False))
        self.assertEqual(self.be.default_auth({}), self._sess(2).effective_auth(),
                         "the dormant twin and the live read share the one fallback")

    def test_a_pick_wins_over_the_declaration(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        s = self._sess(1, auth="login")
        self.assertEqual(s.effective_auth(), "login")
        self.assertIs(s.snapshot()["authPicked"], True)
        sid = self.be.spawn("n", "/tmp", auth="login")
        row = self.be.live_sessions()[sid]
        self.assertEqual((row["auth"], row["authPicked"]), ("login", True))

    def test_a_remembered_pick_makes_the_declaration_inert_here_too(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        sb.write_sdk_default(self.be.state_dir, auth="login")   # set_auth's durable trace
        self.assertEqual(self._sess(1).effective_auth(), "login",
                         "the remembered pick is the box's expectation now; the env word stops speaking")
        self.assertEqual(self.be.default_auth({}), "login")

    def test_declared_login_and_no_declaration_both_read_login_on_a_keyless_box(self):
        os.environ["ROMP_EXPECTED_AUTH"] = "login"
        self.assertEqual(self._sess(1).effective_auth(), "login")
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        self.assertEqual(self._sess(2).effective_auth(), "login", "the pre-declaration world, unchanged")
        self.assertEqual(sb.unpicked_auth(Path(self.d), True), "key", "a key romp holds still comes first")

    def test_a_set_aside_key_pick_lets_the_declaration_speak(self):
        # the user's own migration: a key pick made while the box held a key, the key since moved to Claude
        # Code's apiKeyHelper and the box declaring so. spawn sets the pick aside (no key source), so the
        # inertness a pick grants protects nothing here, and the declaration decides the unpicked default
        # (review round 1, 2026-09-09: before this the pick made the declaration inert AND seeded nothing,
        # so every new session read login against both the pick and the declaration)
        sb.write_sdk_default(self.be.state_dir, auth="key")
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        self.assertEqual(self._sess(1).effective_auth(), "key")
        self.assertEqual(self.be.default_auth({}), "key")
        self.assertEqual(self.be.new_session_auth(), "key", "the picker's written-out choice reads the key too")
        sid = self.be.spawn("n", "/tmp")
        self.assertNotIn("auth", sb.read_reg(self.be.state_dir, sid), "the pick is still set aside: nothing seeded")
        row = self.be.live_sessions()[sid]
        self.assertEqual((row["auth"], row["authPicked"]), ("key", False))
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        self.assertEqual(self._sess(2).effective_auth(), "login",
                         "undeclared, the set-aside rule stands: an unpicked session reads the login (dc3eabee)")
        self.assertEqual(self.be.new_session_auth(), "login")

    def test_the_defaults_file_is_parsed_once_per_identity(self):
        # the declaration read is per row (unpicked_auth under every dormant row of live_sessions): one parse
        # per file identity, a stat per read after it, and a write (the atomic writer's here) is seen on the
        # next read. Never a timer.
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        sb.write_sdk_default(self.be.state_dir, effort="high")   # the file exists and holds no pick
        for n in range(12):
            self.be.spawn("s%d" % n, "/tmp")
        reads = []
        real = Path.read_text

        def counting(p, *a, **k):
            if p.name == "sdk-defaults.json":
                reads.append(str(p))
            return real(p, *a, **k)

        with mock.patch.object(Path, "read_text", counting):
            rows = self.be.live_sessions()
            self.assertEqual(len(rows), 12)
            self.assertLessEqual(len(reads), 1, "one build, at most one parse")
            self.assertTrue(all(r["auth"] == "key" for r in rows.values()))
            reads.clear()
            self.be.live_sessions()
            self.assertEqual(reads, [], "a second build under the same identity parses nothing")
            sb.write_sdk_default(self.be.state_dir, auth="login")   # set_auth's writer: a new identity
            reads.clear()
            rows = self.be.live_sessions()
            self.assertEqual(len(reads), 1, "the write is seen: one parse, then cached again")
            self.assertTrue(all(r["auth"] == "login" for r in rows.values()), "and the new pick is what is read")


class _KeyToggleBackend(sb.SdkBackend):
    """A backend whose key_available reads a pinned bool. romp holds no key of its own (2026-09-08); the box's
    key is Claude Code's apiKeyHelper, which the real property reads from the settings files. The matrix below
    needs both worlds in one process, so it pins the answer instead of writing settings."""
    key_here = False

    @property
    def key_available(self) -> bool:
        return self.key_here


class KernelReadersShareTheBackendsRule(unittest.TestCase):
    """_auth_avail's picker default reads the backend's ONE rule (SdkBackend.new_session_auth, called
    directly) on a REAL backend; _bills_login's fallback for a row that reports nothing reads the key's
    presence, not _auth_key_present(), since the 2026-09-10 fold (ruling K2; its pin is LimitPauseLift's
    ..._this_machine_holds_no_key in tests/test_retry_pause_autoresume.py), and a row that reports
    outranks the declaration. Review round 1 (2026-09-09) found the kernel's two readers of the time
    consulting the declaration before the key while the backend consulted it after, so a keyed box
    declaring login seeded the picker on Login for sessions that launched keyed; and found no test
    executing the backend method the kernel reached through a getattr guard, so a rename restored the
    pre-fix readers with every test green. The matrix below runs every
    reader over a key available or not, declaration key/login/unset and pick none/login/key, and states the
    one answer for each of the two questions: what an UNPICKED reg bills (unpicked_auth: the key first) and
    what a session SPAWNED NOW bills (new_session_auth: the seed a spawn writes first). They differ in one
    cell only, a remembered login pick on a keyed box: the reg a spawn writes carries the pick, an older
    unpicked reg launches keyed. Since 2026-09-08 romp holds no key of its own: the key the rule reads is
    the box's apiKeyHelper (SdkBackend.key_available), toggled here without writing a settings file."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._exp_before = os.environ.pop("ROMP_EXPECTED_AUTH", None)
        self._saved = (km._sdk, km._claude_account, km._claude_account_label, km.jd.STATE)
        km.jd.STATE = Path(self.d)
        km._claude_account = lambda: "aaaaaaaaaaaa"
        km._claude_account_label = lambda: "user@example.com"
        self.be = _KeyToggleBackend(self.d, "/bin/true", lambda *a, **k: None, log=lambda m: None)
        km._sdk = lambda: self.be

    def tearDown(self):
        (km._sdk, km._claude_account, km._claude_account_label, km.jd.STATE) = self._saved
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        if self._exp_before is not None:
            os.environ["ROMP_EXPECTED_AUTH"] = self._exp_before

    def _world(self, declared="", pick="", key=False):
        if declared:
            os.environ["ROMP_EXPECTED_AUTH"] = declared
        else:
            os.environ.pop("ROMP_EXPECTED_AUTH", None)
        p = Path(self.d) / "sdk-defaults.json"
        if pick:
            p.write_text(json.dumps({"auth": pick}))
        else:
            p.unlink(missing_ok=True)
        self.be.key_here = key

    def test_every_reader_gives_one_answer_over_the_matrix(self):
        n = 0
        for key in (False, True):
            for declared in ("", "key", "login"):
                for pick in ("", "login", "key"):
                    self._world(declared, pick, key)
                    tag = "key=%s declared=%r pick=%r" % (key, declared, pick)
                    # an UNPICKED reg: the key romp holds; else a login pick's side; else the declaration (a
                    # key pick without a key is set aside and lets it speak); else the login
                    unpicked = "key" if key else ("login" if pick == "login" else (declared or "login"))
                    self.assertEqual(sb.unpicked_auth(Path(self.d), key), unpicked, tag)
                    self.assertEqual(self.be.default_auth({}), unpicked, tag)
                    n += 1
                    live = sb.SdkSession(self.be, {"sid": "11111111-2222-3333-4444-%012d" % n, "name": "u", "cwd": "/tmp"})
                    self.assertEqual(live.effective_auth(), unpicked, tag)
                    # a session SPAWNED NOW: the seed a spawn writes (a login pick; a key pick when the key is
                    # held), else the unpicked rule. The kernel's picker default takes this one.
                    fresh = "login" if pick == "login" else ("key" if key else (declared or "login"))
                    self.assertEqual(self.be.new_session_auth(), fresh, tag)
                    self.assertEqual(km._auth_avail()["default"], fresh, tag)
                    # _bills_login's fallback for a row that reports nothing left this rule at the 2026-09-10 fold
                    # (ruling K2): it reads `not _auth_key_present()`, pinned by LimitPauseLift's
                    # ..._this_machine_holds_no_key in tests/test_retry_pause_autoresume.py; the two pins retired
                    sid = self.be.spawn("n", "/tmp")
                    self.assertEqual(self.be.default_auth(sb.read_reg(self.be.state_dir, sid)), fresh,
                                     tag + ": the picker default IS what a spawn without a pick bills")

    def test_a_keyed_box_declaring_login_reads_the_key_everywhere(self):
        # the cell review round 1 found split: the declaration is a contradiction the init check rings about,
        # not a refusal, and every unpicked session launches on the box's key, so every reader must say key
        # (the base commit did; the fix's two kernel readers said login)
        self._world("login", "", key=True)
        self.assertEqual(sb.unpicked_auth(Path(self.d), True), "key")
        self.assertEqual(self.be.new_session_auth(), "key")
        self.assertEqual(km._auth_avail()["default"], "key")
        # _bills_login's fallback pin retired (the 2026-09-10 fold, ruling K2): its fallback is `not _auth_key_present()`

    def test_a_row_that_reports_still_wins(self):
        self._world("key")
        self.assertTrue(km._bills_login({"authLive": "login"}), "the CLI's own report outranks the declaration")
        self.assertTrue(km._bills_login({"auth": "login"}), "…and so does the intent on the row")

    def test_auth_avail_default_follows_the_rule(self):
        self._world("key")
        a = km._auth_avail()
        self.assertEqual((a["key"], a["default"]), (False, "key"),
                         "romp holds no key to offer, yet the one applying choice is the key")
        self._world("")
        self.assertEqual(km._auth_avail()["default"], "login")
        self._world("key", pick="login")
        self.assertEqual(km._auth_avail()["default"], "login", "a remembered login pick stays the default")
        self._world("key", pick="key")
        self.assertEqual(km._auth_avail()["default"], "key",
                         "a remembered KEY pick on a keyless box is set aside, and the declaration speaks for the default")
        self._world("", pick="key")
        self.assertEqual(km._auth_avail()["default"], "login", "undeclared, the set-aside pick reads as unpicked: the login")

    def test_the_kernel_calls_the_backend_method_directly_and_a_missing_one_is_loud(self):
        # the binding the fix depends on, executed on the real method (a getattr guard hid its loss before)
        self._world("key")
        self.assertEqual(self.be.new_session_auth(), "key")
        self.assertEqual(km._unpicked_default(), "key")
        # the _bills_login pin retired here too (the 2026-09-10 fold, ruling K2): its fallback is `not _auth_key_present()`,
        # True on this world's keyless backend, not the declaration's key; the binding under test is _unpicked_default's
        self.assertEqual(km._auth_avail()["default"], "key")
        km._sdk = lambda: type("B", (), {"key_available": False})()   # a backend without the method
        with self.assertRaises(AttributeError):
            km._unpicked_default()
        km._sdk = lambda: None
        self.assertEqual(km._unpicked_default(), "login", "no backend module at all: nothing of romp's is injected")


class LiveMergeCarriesTheCliReport(unittest.TestCase):
    """Sessions.live() forwards authLive and authPicked from the SDK row. It never had authLive: since the
    field was born (2026-08-15) the merge copied `auth` and `authPending` and dropped it, so build_session's
    `tm.get("authLive", "")` and every kernel reader of the map (_bills_login, _cap_switch_offer,
    _judge_limit_view) saw "" and fell to the seeded intent."""

    SID = "11111111-2222-3333-4444-000000000909"

    def setUp(self):
        self._saved = (km._sdk, km._codex)
        km._TMUX.live_sessions = lambda: {}
        km._codex = lambda: None
        row = {"state": "waiting", "since": "", "model": "", "effort": "", "auth": "login",
               "authLive": "key", "authPicked": False, "authPending": False, "mode": "", "fast": "",
               "fastReason": "", "color": None, "connected": False, "spawning": False, "retryCount": 0,
               "retryInfo": None, "ctx": None, "subagents": [], "bgTasks": []}
        km._sdk = lambda: type("B", (), {"live_sessions": lambda self: {LiveMergeCarriesTheCliReport.SID: row}})()

    def tearDown(self):
        (km._sdk, km._codex) = self._saved
        km._TMUX.__dict__.pop("live_sessions", None)   # the instance attr shadowed the class method

    def test_the_merged_row_carries_the_report_and_the_pick_flag(self):
        tm = km.Sessions.live()[self.SID]
        self.assertEqual((tm["auth"], tm["authLive"], tm["authPicked"]), ("login", "key", False))
        self.assertFalse(km._bills_login(tm), "the reader that records a cap's billing sees the CLI's side")


class RefreshUsageAllKeyed(_Declared):
    """Every live session keyed = nobody can poll the subscription windows. Said once per episode
    (the rail timer calls refresh_usage every 60s), as a problem only when undeclared."""

    LINE = "all billing API keys"

    def _live_keyed(self, n):
        s = self._sess(n)
        s.client, s.loop, s.ended = object(), object(), False
        s.api_key_auth = True
        s.refresh_usage = lambda: True
        return s

    def _lines(self):
        return [m for m in self.logs if self.LINE in m]

    def test_logged_once_per_episode_not_per_call(self):
        a, b = self._live_keyed(1), self._live_keyed(2)
        self.be.sessions = {a.sid: a, b.sid: b}
        for _ in range(3):
            self.be.refresh_usage()
        self.assertEqual(len(self._lines()), 1, "the 60s timer must not spam the log")
        self.assertIn("2 live session(s)", self._lines()[0])

    def test_undeclared_rings_and_a_key_declaration_does_not(self):
        a = self._live_keyed(1)
        self.be.sessions = {a.sid: a}
        self.be.refresh_usage()
        self.assertTrue(any(self.LINE in t for t in self._problem_texts()),
                        "undeclared all-keyed silence is the surprising case — it rings")
        os.environ["ROMP_EXPECTED_AUTH"] = "key"
        be2 = sb.SdkBackend(tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None,
                            log=self.logs.append)
        b = sb.SdkSession(be2, {"sid": "11111111-2222-3333-4444-%012d" % 9,
                                "name": "s9", "cwd": "/tmp"})
        b.client, b.loop, b.ended = object(), object(), False
        b.api_key_auth = True
        be2.sessions = {b.sid: b}
        be2.refresh_usage()
        self.assertEqual(len(self._lines()), 2, "declared, the condition still logs (info)…")
        self.assertFalse(any(self.LINE in p["text"] for p in be2.problems(10)),
                         "…but as the box working as designed, never a problem")

    def test_a_pollable_session_rearms_the_one_shot(self):
        keyed = self._live_keyed(1)
        self.be.sessions = {keyed.sid: keyed}
        self.be.refresh_usage()                          # episode 1: logged
        sub = self._sess(2)
        sub.client, sub.loop, sub.ended = object(), object(), False
        polled = []
        sub.refresh_usage = lambda: polled.append(True) or True
        self.be.sessions[sub.sid] = sub
        self.be._note_auth_source(sub, "none")           # its init CONFIRMED the login — only a
        #   confirmed login re-arms (a pre-init spawn is "unknown": the companion test below)
        self.be.refresh_usage()                          # a candidate exists: polls, re-arms
        self.assertTrue(polled)
        sub.api_key_auth = True                          # …and the box goes all-keyed again
        self.be.refresh_usage()
        self.assertEqual(len(self._lines()), 2, "a NEW episode logs again")

    def test_a_pre_init_spawn_does_not_rearm_or_re_ring(self):
        # a fresh spawn is connected before its first turn, and its init — the only event that can
        # set api_key_auth — arrives only WITH that turn: until then its default-False flag means
        # "unknown", not "login", and it must not open a new episode on the motivating all-keyed box
        keyed = self._live_keyed(1)
        self.be.sessions = {keyed.sid: keyed}
        self.be.refresh_usage()                          # episode 1: logged
        fresh = self._sess(2)                            # connected, no init yet: auth unknown
        fresh.client, fresh.loop, fresh.ended = object(), object(), False
        fresh.refresh_usage = lambda: True
        self.be.sessions[fresh.sid] = fresh
        self.be.refresh_usage()                          # a compose-window tick
        self.be._note_auth_source(fresh, "apiKeyHelper")  # its first init lands keyed
        self.be.refresh_usage()
        self.assertEqual(len(self._lines()), 1,
                         "an unknown was never a login — same episode, no repeat line")

    def test_no_connected_sessions_is_not_the_all_keyed_case(self):
        self.be.sessions = {}
        self.be.refresh_usage()
        dormant = self._sess(3)                          # keyed but not connected (client None)
        dormant.api_key_auth = True
        self.be.sessions = {dormant.sid: dormant}
        self.be.refresh_usage()
        self.assertEqual(self._lines(), [], "nothing connected — nothing to say")


class UsageTelemetryUnavailable(unittest.TestCase):
    """kernel _usage(): the keyed no-window payload says WHY the bars are absent — key auth means
    the windows are structurally absent (both usage.json writers skip keyed sessions), and the rail
    hover renders the reason. Key auth is the reason when the manager env carries a key OR the box
    declares ROMP_EXPECTED_AUTH=key (the apiKeyHelper box, where no key ever rides service.env)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.real_state = km.jd.STATE
        km.jd.STATE = Path(self.d)
        self.real_key = km._auth_key_present
        self.real_acct = km._claude_account
        self._exp_before = os.environ.pop("ROMP_EXPECTED_AUTH", None)

    def tearDown(self):
        km.jd.STATE = self.real_state
        km._auth_key_present = self.real_key
        km._claude_account = self.real_acct
        os.environ.pop("ROMP_EXPECTED_AUTH", None)
        if self._exp_before is not None:
            os.environ["ROMP_EXPECTED_AUTH"] = self._exp_before

    def test_no_payload_carries_the_retired_telemetry_flag(self):
        # the flag and its "rate-limit telemetry unavailable under API-key auth" hover line were
        # DELETED (the user 2026-08-24: they know which machines are key-only and want the spend
        # without a notice about rate limits that don't apply). A keyed host's payload carries
        # spend and NOTHING about rate limits; a login host's windows are untouched.
        (Path(self.d) / "usage.json").write_text(json.dumps({"t": 1000, "apiKey": True}))
        km._auth_key_present = lambda: True
        km._claude_account = lambda: ""
        u = km._usage()
        self.assertTrue(u.get("apiKey"))
        self.assertNotIn("telemetryUnavailable", u)
        os.environ["ROMP_EXPECTED_AUTH"] = "key"    # the apiKeyHelper declaration marks nothing either
        (Path(self.d) / "spend.json").write_text(json.dumps({"days": {}, "hours": {}}))
        self.assertNotIn("telemetryUnavailable", km._usage())

    def test_login_windows_stay_untouched_by_the_deletion(self):
        (Path(self.d) / "usage.json").write_text(json.dumps(
            {"t": 1000, "five_hour": {"pct": 40, "resets_at": None}}))   # unstamped legacy keeps bars
        km._auth_key_present = lambda: True
        km._claude_account = lambda: ""
        u = km._usage()
        self.assertTrue(u.get("fiveHour"), "rate-limit windows render exactly as before")
        self.assertNotIn("telemetryUnavailable", u)


if __name__ == "__main__":
    unittest.main()

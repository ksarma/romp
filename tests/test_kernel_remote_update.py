"""Remote version-drift detection + `romp update` (the user 2026-07-04): the local kernel polls each attached
remote's /version, flags one running an OLDER commit (outOfDate), and offers to pull+restart it behind the
scenes. `POST /tunnels/update` runs the ssh git-pull + restart; the rail popover + a top banner surface it.
SYNTHETIC hosts; subprocess/http are stubbed so nothing actually launches or connects."""
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel", os.path.join(BIN, "romp-kernel")).load_module()


class _R:
    def __init__(self, out="", err="", rc=0):
        self.stdout, self.stderr, self.returncode = out, err, rc


class VersionDrift(unittest.TestCase):
    def setUp(self):
        self._hc = dict(km._HEAD_CACHE)
        km._HEAD_CACHE.update(ts=9e18, full="abc12340000", short="abc1234")   # pin local HEAD, skip the subprocess

    def tearDown(self):
        km._HEAD_CACHE.clear(); km._HEAD_CACHE.update(self._hc)

    def test_sha_base_strips_dirty(self):
        self.assertEqual(km._sha_base("abc1234-dirty"), "abc1234")
        self.assertEqual(km._sha_base("abc1234"), "abc1234")
        self.assertIsNone(km._sha_base(""))
        self.assertIsNone(km._sha_base(None))

    def test_shas_agree_tolerates_different_short_lengths(self):
        self.assertTrue(km._shas_agree("abc1234", "abc1234567"), "one a prefix of the other → same commit")
        self.assertTrue(km._shas_agree("abc1234-dirty", "abc1234"), "'-dirty' ignored")
        self.assertFalse(km._shas_agree("abc1234", "def5678"))
        self.assertFalse(km._shas_agree("abc1234", ""))

    def test_drift_is_measured_against_live_HEAD_and_CLEARS_when_matched(self):
        # the fix (the user 2026-07-04): drift compares the remote to the LIVE HEAD — the SAME thing the push
        # sends — so once the remote is pushed to HEAD the flag goes away (it used to compare to the kernel's
        # cached startup sha while the push sent HEAD, so it never reconciled → banner stuck forever).
        self.assertTrue(km._remote_out_of_date({"kernel_sha": "def5678"}), "different commit → out of date")
        self.assertFalse(km._remote_out_of_date({"kernel_sha": "abc1234"}), "remote pushed to HEAD → CLEARS")
        self.assertFalse(km._remote_out_of_date({"kernel_sha": "abc12345"}), "same commit, longer short → clears")
        self.assertFalse(km._remote_out_of_date({}), "unknown remote sha → not flagged")
        self.assertFalse(km._remote_out_of_date({"kernel_sha": ""}), "blank remote sha → not flagged")

    def test_remote_public_exposes_version_fields(self):
        pub = km._remote_public({"host": "TESTHOST", "kernel_port": 29855, "local_port": 8801, "token": "t",
                                 "status": "up", "sids": [], "kernel_sha": "def5678"})
        self.assertEqual(pub["kernelSha"], "def5678")
        self.assertEqual(pub["localSha"], "abc1234", "localSha is the live HEAD short (what a push would send)")
        self.assertTrue(pub["outOfDate"])


class UpdateRemote(unittest.TestCase):
    """PEER-TO-PEER update (the user 2026-07-04): push local committed HEAD to the remote (no GitHub), refuse on
    a dirty/diverged remote, restart. Three subprocess calls — ssh-discover, git-push, ssh-apply — are dispatched
    by inspecting argv so each case can drive them independently."""
    LFULL = "1" * 40                        # local HEAD (full sha) the push sends
    RHEAD = "2" * 40                         # a remote at a DIFFERENT (older) commit

    def setUp(self):
        self._run, self._hc = km.subprocess.run, dict(km._HEAD_CACHE)
        km._HEAD_CACHE.update(ts=0.0, full=None, short=None)   # force _local_head to consult the mocked git

    def tearDown(self):
        km.subprocess.run = self._run
        km._HEAD_CACHE.clear(); km._HEAD_CACHE.update(self._hc)

    def _wire(self, rhead=None, dirty="", disc_out=None, push_rc=0, push_err="", apply_out="SYNCED:abcdef0"):
        """Install a dispatching subprocess mock; returns the list of argv it saw."""
        if disc_out is None:
            disc_out = "DIR:/home/u/romp\nHEAD:%s\nDIRTY:%s" % (rhead if rhead is not None else self.RHEAD, dirty)
        calls = []

        def fake(argv, **kw):
            calls.append(argv)
            if argv[0] == "git" and "push" in argv:
                return _R(err=push_err, rc=push_rc)
            if argv[0] == "git" and "rev-parse" in argv and "HEAD" in argv:   # _local_head
                return _R(out=self.LFULL)
            cmd = argv[-1]                                                     # ssh: dispatch on the remote command
            if "for d in" in cmd:
                return _R(out=disc_out)
            if "merge-base" in cmd or "reset --hard" in cmd:
                return _R(out=apply_out)
            return _R()
        km.subprocess.run = fake
        return calls

    def test_no_host_is_a_no_op(self):
        self.assertEqual(km._update_remote(""), (False, "no host"))

    def test_a_clean_ancestor_remote_is_pushed_reset_and_restarted(self):
        calls = self._wire(apply_out="SYNCED:abcdef0")
        ok, detail = km._update_remote("TESTHOST")
        self.assertTrue(ok)
        self.assertIn("synced to abcdef0", detail)
        # it force-pushed local HEAD to a scratch ref at host:remote-dir
        push = next(a for a in calls if a[0] == "git" and "push" in a)
        self.assertIn("--force", push)
        self.assertIn("TESTHOST:/home/u/romp", push)
        self.assertTrue(any(str(x).startswith("HEAD:refs/heads/") for x in push), "pushes HEAD to a scratch ref")

    def test_the_apply_restarts_through_the_manager_quiet_window_with_an_audit_row(self):
        # T238: the remote apply used to `pkill` the far kernel outright — an anonymous, immediate
        # SIGTERM (no restart-audit row, no quiet window: nine in-flight-turn cuts in three hours on a
        # merge day, each read by the dialing side as "unreachable"). The apply now writes the audit
        # row first and asks the far MANAGER for a quiet-window restart; pkill survives only as the
        # last-resort branch for a host with no manager.
        calls = self._wire(apply_out="SYNCED:abcdef0:QUIET")
        km._remotes["TESTHOST"] = {"host": "TESTHOST"}
        self.addCleanup(km._remotes.pop, "TESTHOST", None)
        ok, detail = km._update_remote("TESTHOST")
        self.assertTrue(ok, detail)
        self.assertIn("quiet window", detail)
        apply = next(a[-1] for a in calls if isinstance(a[-1], str) and "reset --hard" in a[-1])
        self.assertIn("restart-audit.jsonl", apply, "the restart is never anonymous")
        self.assertIn("p2p-update", apply)
        self.assertIn("restart-all --quiet", apply, "the manager's quiet-window gate, not a kill")
        self.assertLess(apply.index("restart-all --quiet"), apply.index('pkill -f "bin/romp-kern[e]l"'),
                        "pkill is the fallback AFTER the manager path, never the first move")
        exp = km._remotes["TESTHOST"].get("restartExpected")
        self.assertTrue(exp and exp.get("sha") == self.LFULL and exp.get("t") and exp.get("quiet") is True,
                        "the dialing side is told to expect the restart it just caused")

    def test_a_host_with_no_owning_manager_restarts_the_old_way_and_says_so(self):
        calls = self._wire(apply_out="SYNCED:abcdef0:FALLBACK")
        km._remotes["TESTHOST"] = {"host": "TESTHOST"}
        self.addCleanup(km._remotes.pop, "TESTHOST", None)
        ok, detail = km._update_remote("TESTHOST")
        self.assertTrue(ok, detail)
        self.assertIn("immediate", detail)
        self.assertNotIn("quiet window", detail)
        self.assertIs(km._remotes["TESTHOST"]["restartExpected"]["quiet"], False)

    def test_the_quiet_path_requires_the_manager_to_own_the_polled_kernel(self):
        # a manager owning nothing (or a bare kernel beside a crash-looping managed one) answers 202
        # and restarts nothing — trusting it turned the update into a silent never-restart (review)
        calls = self._wire(apply_out="SYNCED:abcdef0:QUIET")
        km._update_remote("TESTHOST")
        apply = next(a[-1] for a in calls if isinstance(a[-1], str) and "reset --hard" in a[-1])
        self.assertIn('romp-manager" status', apply, "ownership is read from the manager's own registry")
        self.assertLess(apply.index('romp-manager" status'), apply.index("restart-all --quiet"))
        self.assertIn('if [ "$OWNED" = 1 ]', apply)
        # per-branch audit rows: the quiet row precedes the quiet call; the fallback writes its own
        # row (no when=quiet) right before pkill, so the cut row joins the request that happened
        self.assertEqual(apply.count("restart-audit.jsonl"), 2)
        self.assertLess(apply.index("p2p-update"), apply.index("restart-all --quiet"),
                        "the quiet row lands before the quiet request")
        self.assertLess(apply.index("restart-all --quiet"), apply.index("immediate: no owning manager"),
                        "the fallback writes its own row after the quiet branch was skipped")
        self.assertLess(apply.index("immediate: no owning manager"), apply.index('pkill -f "bin/romp-kern[e]l"'))
        self.assertIn('SYNCED:$NEW:FALLBACK', apply)

    def test_both_generated_apply_scripts_parse_as_bash(self):
        import shlex, subprocess as sp
        calls = self._wire(apply_out="SYNCED:abcdef0:QUIET")
        km._update_remote("TESTHOST")
        wrapper = next(a[-1] for a in calls if isinstance(a[-1], str) and "reset --hard" in a[-1])
        inner = shlex.split(wrapper.split("; if command -v setsid")[0][len("APPLY="):])[0]
        r = sp.run(["bash", "-n"], input=inner, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_port": 29855}
        self.addCleanup(km._remotes.pop, "TESTHOST", None)
        calls2 = []
        real = km.subprocess.run
        def fake2(argv, **kw):
            calls2.append(argv)
            if argv[0] == "git":
                return _R(out=self.LFULL)
            cmd = argv[-1]
            if "for d in" in cmd:
                return _R(out="DIR:/home/u/romp\nHEAD:%s\nDIRTY:" % self.RHEAD)
            return _R(out="RESTARTED:1")
        km.subprocess.run = fake2
        try:
            ok, _ = km._restart_remote_kernel("TESTHOST")
        finally:
            km.subprocess.run = real
        self.assertTrue(ok)
        wrapper2 = next(a[-1] for a in calls2 if isinstance(a[-1], str) and "RESTARTED" in a[-1])
        inner2 = shlex.split(wrapper2.split("; if command -v setsid")[0][len("APPLY="):])[0]
        r2 = sp.run(["bash", "-n"], input=inner2, capture_output=True, text=True)
        self.assertEqual(r2.returncode, 0, r2.stderr)

    def test_the_expectation_is_stamped_before_the_apply_runs_and_popped_when_nothing_restarted(self):
        # an idle far kernel is SIGTERMed within milliseconds of the manager's 202, and the fallback
        # kills it mid-ssh: a stamp AFTER the ssh returned arrived after the gap it explains (review)
        km._remotes["TESTHOST"] = {"host": "TESTHOST"}
        self.addCleanup(km._remotes.pop, "TESTHOST", None)
        seen = []
        calls = self._wire(apply_out="SYNCED:abcdef0")
        real = km.subprocess.run
        def spy(argv, **kw):
            if isinstance(argv[-1], str) and "reset --hard" in argv[-1]:
                seen.append(dict(km._remotes["TESTHOST"].get("restartExpected") or {}))
            return real(argv, **kw)
        km.subprocess.run = spy
        km._update_remote("TESTHOST")
        km.subprocess.run = real
        self.assertTrue(seen and seen[0].get("sha") == self.LFULL, "expected BEFORE the apply ssh ran: %r" % seen)
        # a DIVERGED apply restarts nothing → the expectation is withdrawn
        self._wire(apply_out="DIVERGED")
        ok, _ = km._update_remote("TESTHOST")
        self.assertFalse(ok)
        self.assertNotIn("restartExpected", km._remotes["TESTHOST"])

    def test_already_up_to_date_re_arms_the_expectation_while_the_far_kernel_lags(self):
        # the checkout holds our build but the KERNEL still answers the old sha: a restart is pending
        # (a quiet window forgotten across our own restart) — expect its gap instead of reading death
        self._wire(rhead=self.LFULL)
        km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_sha": "2222222"}
        self.addCleanup(km._remotes.pop, "TESTHOST", None)
        ok, detail = km._update_remote("TESTHOST")
        self.assertTrue(ok)
        self.assertIn("has not restarted into it yet", detail)
        self.assertEqual(km._remotes["TESTHOST"]["restartExpected"]["sha"], self.LFULL)

    def test_an_explicit_restart_expects_a_gap_with_no_sha_and_withdraws_on_failure(self):
        km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_sha": "2" * 40, "kernel_port": 29855}
        self.addCleanup(km._remotes.pop, "TESTHOST", None)
        seen = []
        real = km.subprocess.run
        def fake(argv, **kw):
            if argv[0] == "git":
                return _R(out=self.LFULL)
            cmd = argv[-1]
            if "for d in" in cmd:
                return _R(out="DIR:/home/u/romp\nHEAD:%s\nDIRTY:" % self.RHEAD)
            seen.append(dict(km._remotes["TESTHOST"].get("restartExpected") or {}))
            return _R(out="NOLAUNCH")
        km.subprocess.run = fake
        try:
            ok, _ = km._restart_remote_kernel("TESTHOST")
        finally:
            km.subprocess.run = real
        self.assertFalse(ok)
        self.assertEqual(seen[0].get("sha"), "", "same build: no new sha to wait for — only the gap ends it")
        self.assertNotIn("restartExpected", km._remotes["TESTHOST"], "nothing restarted → withdrawn")

    def test_already_up_to_date_short_circuits(self):
        self._wire(rhead=self.LFULL)          # remote already at local HEAD
        ok, detail = km._update_remote("TESTHOST")
        self.assertTrue(ok)
        self.assertIn("already up to date", detail)

    def test_a_dirty_local_is_not_refused_it_pushes_committed_head(self):
        # "just take what is committed on local" (the user 2026-07-04): a dirty working tree is NOT a blocker —
        # _update_remote pushes the committed HEAD and never asks you to commit first.
        self._wire(apply_out="SYNCED:abcdef0")
        ok, detail = km._update_remote("TESTHOST")
        self.assertTrue(ok)
        self.assertNotIn("commit", detail.lower())

    def test_no_local_checkout_fails_cleanly(self):
        def fake(argv, **kw):
            if argv[0] == "git" and "rev-parse" in argv:
                return _R(rc=1)                            # not a git checkout
            return _R()
        km.subprocess.run = fake
        km._HEAD_CACHE.update(ts=0.0, full=None, short=None)
        ok, detail = km._update_remote("TESTHOST")
        self.assertFalse(ok)
        self.assertIn("git checkout", detail)

    def test_refuses_a_dirty_remote_without_clobbering(self):
        self._wire(dirty="M")
        ok, detail = km._update_remote("TESTHOST")
        self.assertFalse(ok)
        self.assertIn("uncommitted changes", detail)

    def test_refuses_a_diverged_remote(self):
        self._wire(apply_out="DIVERGED")
        ok, detail = km._update_remote("TESTHOST")
        self.assertFalse(ok)
        self.assertIn("diverged", detail)

    def test_no_romp_clone_fails_loudly(self):
        self._wire(disc_out="NOROMP")
        ok, detail = km._update_remote("TESTHOST")
        self.assertFalse(ok)
        self.assertIn("not installed", detail)

    def test_a_failed_push_surfaces_the_git_error(self):
        self._wire(push_rc=1, push_err="Permission denied (publickey)")
        ok, detail = km._update_remote("TESTHOST")
        self.assertFalse(ok)
        self.assertIn("git push", detail)
        self.assertIn("Permission denied", detail)

    def test_no_github_origin_in_the_remote_commands(self):
        # peer-to-peer: NOTHING should pull from origin / touch GitHub
        calls = self._wire()
        km._update_remote("TESTHOST")
        for a in calls:
            cmd = a[-1] if isinstance(a[-1], str) else ""
            self.assertNotIn("git pull", cmd, "no pull-from-origin anywhere")
            self.assertNotIn("origin", cmd)

    def test_restart_goes_through_the_manager_then_falls_back(self):
        # the user 2026-07-04: the restart should keep the remote MANAGER-owned (romp's durable supervisor, no
        # orphan) — kill the kernel, `romp-manager ensure` (respawns via a live manager, or STARTS one that spawns
        # a supervised kernel — upgrading an attach-bootstrapped bare host), then port-poll; bare romp-serve is a
        # LAST-RESORT fallback only when the port never returns. It must NOT rely on `romp --refresh` (the stuck bug).
        km._remotes = {"TESTHOST": {"host": "TESTHOST", "kernel_port": 29855}}
        calls = self._wire()
        km._update_remote("TESTHOST")
        apply = next(a[-1] for a in calls if isinstance(a[-1], str) and "merge-base" in a[-1])
        self.assertIn("pkill -f", apply, "kills the running kernel")
        self.assertIn('"$R/bin/romp-manager" ensure', apply, "prefers the manager (ensure = idempotent supervised start)")
        self.assertIn("/dev/tcp/127.0.0.1/29855", apply, "polls the remote's kernel port to confirm it came back")
        self.assertIn('if [ "$UP" = 0 ]; then nohup "$R/bin/romp-serve"', apply, "bare romp-serve only as a last resort")
        self.assertNotIn("--refresh", apply, "does NOT rely on `romp --refresh` (needs a manager) — the stuck bug")

    def test_a_host_stopped_by_romp_down_is_synced_but_not_restarted(self):
        # review find (2026-09-06): with the down-by-romp marker on the host, `romp-manager ensure`
        # refuses (that is the marker's job), the port poll fails and the bare fallback booted an
        # UNSUPERVISED kernel while `romp status` there kept saying down. The apply now checks the
        # marker after the owning-manager branch and before the immediate path touches anything
        km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_port": 29855}
        self.addCleanup(km._remotes.pop, "TESTHOST", None)
        calls = self._wire(apply_out="SYNCED:abcdef0:DOWN")
        ok, detail = km._update_remote("TESTHOST")
        self.assertTrue(ok, detail)
        self.assertIn("synced to abcdef0", detail)
        self.assertIn("stopped by romp down", detail)
        self.assertIn("nothing was restarted", detail)
        self.assertIn("romp up on it starts the new code", detail, "the way to start it is named for the user")
        self.assertNotIn("restartExpected", km._remotes["TESTHOST"], "no restart is coming: the gap is not expected")
        apply = next(a[-1] for a in calls if isinstance(a[-1], str) and "reset --hard" in a[-1])
        marker = 'if [ -f "$LOGDIR/down-by-romp" ]; then echo "SYNCED:$NEW:DOWN"; exit 0; fi'
        self.assertIn(marker, apply)
        self.assertLess(apply.index("restart-all --quiet"), apply.index(marker),
                        "a manager that owns the kernel still gets the quiet restart (its start cleared any marker)")
        self.assertLess(apply.index(marker), apply.index("immediate: no owning manager"),
                        "no audit row for a restart that does not happen")
        self.assertLess(apply.index(marker), apply.index('pkill -f "bin/romp-kern[e]l"'), "nothing killed")
        self.assertLess(apply.index(marker), apply.index('"$R/bin/romp-manager" ensure'), "nothing ensured")
        self.assertLess(apply.index(marker), apply.index('nohup "$R/bin/romp-serve"'), "no bare kernel")

    def test_a_same_build_restart_of_a_romp_down_host_says_not_restarting(self):
        km._remotes["TESTHOST"] = {"host": "TESTHOST", "kernel_port": 29855}
        self.addCleanup(km._remotes.pop, "TESTHOST", None)
        calls = []
        def fake(argv, **kw):
            calls.append(argv)
            if argv[0] == "git":
                return _R(out=self.LFULL)
            cmd = argv[-1]
            if "for d in" in cmd:
                return _R(out="DIR:/home/u/romp\nHEAD:%s\nDIRTY:" % self.RHEAD)
            return _R(out="DOWN")
        km.subprocess.run = fake
        ok, detail = km._restart_remote_kernel("TESTHOST")
        self.assertFalse(ok, "the restart asked for did not run")
        self.assertIn("TESTHOST is stopped by romp down; not restarting it", detail)
        self.assertIn("romp up there starts it", detail)
        self.assertNotIn("restartExpected", km._remotes["TESTHOST"])
        apply = next(a[-1] for a in calls if isinstance(a[-1], str) and "RESTARTED" in a[-1])
        marker = 'if [ -f "$LOGDIR/down-by-romp" ]; then echo DOWN; exit 0; fi'
        self.assertIn(marker, apply)
        self.assertLess(apply.index(marker), apply.index("restart-audit.jsonl"), "no audit row, no kill, no boot")
        self.assertLess(apply.index(marker), apply.index('pkill -f "bin/romp-kern[e]l"'))

    def test_apply_is_detached_from_the_ssh_session(self):
        # the user 2026-07-11 (TESTHOST): the apply kills the running kernel before booting its
        # replacement, so an ssh drop between the two halves left the host kernel-LESS — and every
        # banner Retry re-killed whatever a previous attempt had booted. The apply now runs in its
        # own session (setsid, plain-bash fallback where setsid is missing), so once started the
        # kill+boot pair always completes on the remote even if the connection dies.
        km._remotes = {"TESTHOST": {"host": "TESTHOST", "kernel_port": 29855}}
        calls = self._wire()
        km._update_remote("TESTHOST")
        wrapper = next(a[-1] for a in calls if isinstance(a[-1], str) and "merge-base" in a[-1])
        self.assertTrue(wrapper.startswith("APPLY="), "the apply script rides a variable, quoted once")
        self.assertIn('exec setsid bash -c "$APPLY"', wrapper)
        self.assertIn('else exec bash -c "$APPLY"', wrapper, "hosts without setsid still work")

    def test_apply_timeout_says_the_restart_keeps_running(self):
        # the local 60s confirmation window can expire while a slow host is still mid-restart; the
        # detached apply keeps going, so the message must say that instead of implying a dead host
        def fake(argv, **kw):
            if argv[0] == "git" and "rev-parse" in argv:
                return _R(out=self.LFULL)
            if argv[0] == "git" and "push" in argv:
                return _R()
            cmd = argv[-1]
            if "for d in" in cmd:
                return _R(out="DIR:/home/u/romp\nHEAD:%s\nDIRTY:" % self.RHEAD)
            raise km.subprocess.TimeoutExpired(argv, 60)
        km.subprocess.run = fake
        ok, detail = km._update_remote("TESTHOST")
        self.assertFalse(ok)
        self.assertIn("keeps", detail)
        self.assertIn("running", detail)


class UpdateEndpoint(unittest.TestCase):
    def test_post_tunnels_update_calls_update_remote_and_reports(self):
        import inspect
        src = inspect.getsource(km)
        self.assertIn('if u.path == "/tunnels/update":', src)
        self.assertIn("ok, detail = _update_remote(host)", src)
        self.assertIn('json.dumps({"ok": ok, "detail": detail})', src)
        # a failed update returns a non-2xx so the CLI/banner can tell (fail loudly)
        self.assertIn("200 if ok else 502", src)

    def test_supervisor_polls_the_remote_version(self):
        import inspect
        src = inspect.getsource(km._tunnel_supervisor)
        self.assertIn("_poll_remote_version(r)", src)
        self.assertIn('r["kernel_sha"] = rsha', src)


class UpdateUI(unittest.TestCase):
    def test_drift_banner_uses_the_update_framing(self):
        # mirrors the #rstale reload banner, but asks to bring the remote onto the local build (the user
        # 2026-07-04). ONE neutral word since 2026-07-28: the same button covers a push we run and an ask
        # a checked-in peer runs for itself, and what the user agrees to — that machine ends up on this
        # build — is identical either way.
        self.assertIn("id=rdrift", km._RDRIFT_HTML)
        self.assertIn(">Update<", km._RDRIFT_HTML, "the action button says Update")
        self.assertIn("Update it to this one?", km._RDRIFT_JS, "the prompt asks to bring the remote onto this build")
        self.assertIn("/tunnels/update", km._RDRIFT_JS)
        self.assertIn("outOfDate", km._RDRIFT_JS)
        self.assertIn("_rdrift_block()", inspect_src())

    def test_drift_banner_shows_live_progress_success_and_failure(self):
        # the user 2026-07-04: the banner must stay up through the work with a spinner + status, a success
        # confirmation, and a persistent actionable error — not silently flip back to the prompt.
        self.assertIn("rd-spin", km._RDRIFT_HTML)
        self.assertIn("romp-swirl-glyph.svg", km._RDRIFT_CSS)   # the spinner is the romp loader glyph
        self.assertIn("Updating ", km._RDRIFT_JS, "an 'updating…' progress message")
        self.assertIn("waiting for", km._RDRIFT_JS, "a 'waiting for it to restart' verify phase")
        self.assertIn("Up to date", km._RDRIFT_JS, "a success confirmation")
        self.assertIn("Update failed", km._RDRIFT_JS, "a persistent, specific failure message")
        self.assertIn("phase", km._RDRIFT_JS, "a state machine drives the flow")

    def test_popover_shows_behind_and_a_push_button(self):
        self.assertIn("behind", km._LANDING_REMOTES_JS)
        self.assertIn(">Push</button>", km._LANDING_REMOTES_JS)
        self.assertIn("/tunnels/update", km._LANDING_REMOTES_JS)
        self.assertIn("data-u=", km._LANDING_REMOTES_JS)


ru = SourceFileLoader("romp_update", os.path.join(BIN, "romp-update")).load_module()


class RompUpdateCLI(unittest.TestCase):
    def setUp(self):
        self._k, self._g, self._p = ru._kernel, ru._get, ru._post
        ru._kernel = lambda: "http://127.0.0.1:29855"
        self.posted = []
        ru._post = lambda u, path, body: (self.posted.append((path, body)) or {"ok": True, "detail": "updated"})

    def tearDown(self):
        ru._kernel, ru._get, ru._post = self._k, self._g, self._p

    def test_dispatch_routes_update_in_the_bash_cli(self):
        # Dash-only since 2026-07-25: bare `update` names a session (the retired-word
        src = open(os.path.join(BIN, "romp")).read()
        # Round 3 (2026-07-25): commands are bare words again — `update` is the
        # spelling, and the retired `--update` flag fails naming it.
        self.assertIn('"${1:-}" == "update"', src, "bare `update` routes to romp-update")
        self.assertIn('--update)', src, "the retired --update spelling gets a loud hint")
        self.assertIn("exec romp-update", src)

    def test_no_kernel_errors_cleanly(self):
        ru._kernel = lambda: None
        self.assertEqual(ru.main([]), 2)

    def test_named_host_updates_that_remote(self):
        self.assertEqual(ru.main(["TESTHOST"]), 0)
        self.assertEqual(self.posted, [("/tunnels/update", {"host": "TESTHOST"})])

    def test_no_arg_updates_only_out_of_date_remotes(self):
        ru._get = lambda u, path: {"tunnels": [{"host": "TESTHOST", "outOfDate": True},
                                               {"host": "gpu1", "outOfDate": False}]}
        self.assertEqual(ru.main([]), 0)
        self.assertEqual(self.posted, [("/tunnels/update", {"host": "TESTHOST"})], "only the stale remote is updated")

    def test_no_arg_all_current_updates_nothing(self):
        ru._get = lambda u, path: {"tunnels": [{"host": "gpu1", "outOfDate": False}]}
        self.assertEqual(ru.main([]), 0)
        self.assertEqual(self.posted, [], "nothing to do when every remote is current")

    def test_a_failed_update_returns_nonzero(self):
        ru._post = lambda u, path, body: {"ok": False, "detail": "git pull failed"}
        self.assertEqual(ru.main(["TESTHOST"]), 1)


def inspect_src():
    import inspect
    return inspect.getsource(km)


class BehindInfo(unittest.TestCase):
    """The popover's drift wording data (the user 2026-07-11: 'something more informative than just
    behind'): _behind_info measures HOW an out-of-date remote differs — commits behind, commits ahead
    (a push would clobber those, so 'behind' would be a lie), and the remote commit's date."""
    LOCAL_FULL = "abc1234000000000"
    REMOTE_FULL = "def5678000000000"

    def setUp(self):
        self._hc = dict(km._HEAD_CACHE)
        km._HEAD_CACHE.update(ts=9e18, full=self.LOCAL_FULL, short="abc1234")
        km._BEHIND_CACHE.clear()
        self._run = km.subprocess.run

    def tearDown(self):
        km._HEAD_CACHE.clear(); km._HEAD_CACHE.update(self._hc)
        km._BEHIND_CACHE.clear()
        km.subprocess.run = self._run

    def _mock_git(self, behind="12", ahead="0", date="2026-07-08", known=True, calls=None):
        loc, rem = self.LOCAL_FULL, self.REMOTE_FULL

        def run(argv, **kw):
            if calls is not None:
                calls.append(list(argv))
            j = " ".join(argv)
            if "rev-parse" in j and "^{commit}" in j:
                return _R(out=rem + "\n") if known else _R(rc=1)
            if "rev-list" in j and (rem + ".." + loc) in j:
                return _R(out=behind + "\n")
            if "rev-list" in j and (loc + ".." + rem) in j:
                return _R(out=ahead + "\n")
            if "log" in j:
                return _R(out=date + "\n")
            return _R(rc=1)
        km.subprocess.run = run

    def test_behind_counts_and_the_remote_commits_date(self):
        self._mock_git(behind="12", ahead="0", date="2026-07-08")
        self.assertEqual(km._behind_info("def5678"),
                         {"behind": 12, "ahead": 0, "date": "2026-07-08"})

    def test_ahead_is_distinguished_from_behind(self):
        # the remote has its own commits (updated from another machine, or local was rolled back):
        # a push would CLOBBER them, so the row must not claim 'behind'
        self._mock_git(behind="0", ahead="3")
        info = km._behind_info("def5678")
        self.assertEqual((info["behind"], info["ahead"]), (0, 3))

    def test_unknown_sha_reports_none_not_a_guess(self):
        self._mock_git(known=False)
        self.assertEqual(km._behind_info("def5678"), {"behind": None, "ahead": None, "date": ""})

    def test_memoized_per_sha_pair(self):
        calls = []
        self._mock_git(calls=calls)
        km._behind_info("def5678")
        n = len(calls)
        self.assertGreater(n, 0)
        km._behind_info("def5678")
        self.assertEqual(len(calls), n, "the second read is served from the memo — git never re-runs")

    def test_remote_public_carries_the_drift_fields(self):
        self._mock_git(behind="12", ahead="0", date="2026-07-08")
        pub = km._remote_public({"host": "TESTHOST", "kernel_port": 29855, "local_port": 8801,
                                 "status": "up", "kernel_sha": "def5678"})
        self.assertTrue(pub["outOfDate"])
        self.assertEqual((pub["behindBy"], pub["aheadBy"], pub["kernelDate"]), (12, 0, "2026-07-08"))

    def test_in_sync_remote_never_touches_git(self):
        def boom(argv, **kw):
            raise AssertionError("an in-sync row must not pay for drift measurement: %s" % argv)
        km.subprocess.run = boom
        pub = km._remote_public({"host": "TESTHOST", "kernel_port": 29855, "local_port": 8801,
                                 "status": "up", "kernel_sha": "abc1234"})
        self.assertFalse(pub["outOfDate"])
        self.assertEqual((pub["behindBy"], pub["aheadBy"], pub["kernelDate"]), (0, 0, ""))


class DriftWordingUI(unittest.TestCase):
    """The popover row names HOW the remote differs, not just 'behind' (the user 2026-07-11)."""

    def test_row_names_how_the_remote_differs(self):
        js = km._LANDING_REMOTES_JS
        self.assertIn("down=bb>0?('behind '+bb):''", js)   # said in words since 2026-07-30
        self.assertIn("up=ab>0?('ahead '+ab):''", js)
        self.assertIn("'diverged: '", js)
        self.assertIn("'different build'", js, "an unknown sha says so instead of guessing")

    def test_a_buildless_connected_host_reads_unversioned_not_blank(self):
        # A connected host that reports NO build at all (a plain file copy, no git checkout) used to
        # show a bare "connected" — indistinguishable from healthy-and-in-sync, while running
        # arbitrarily old code drift detection cannot see (the user 2026-08-11, whose devbox sat
        # months behind beside a blank). The row says "unversioned copy" where the build word sits,
        # and the tooltip says why and what restores updates. Fail loudly, never a blank that reads
        # as fine.
        js = km._LANDING_REMOTES_JS
        self.assertIn("else if(t.status==='up'){ver=' \\u00b7 <span class=\"rnet-old\"", js)
        self.assertIn("unversioned copy", js)
        self.assertIn("Reinstall it as a git clone to restore the build name and updates.", js)
        # the VS Code strip's popover row carries the same word — the two surfaces must not drift
        strip = (pathlib.Path(__file__).resolve().parents[1] / "ui" / "webview" / "strip.ts").read_text()
        self.assertIn('ver = " · unversioned copy";', strip)
        self.assertIn("!t.kernelSha && !t.kernelVer", strip)

    def test_tooltip_carries_the_shas_and_date(self):
        js = km._LANDING_REMOTES_JS
        # since 2026-07-30 each side is named by RELEASE and commit together (buildWord), not the sha
        # alone — the tag is the one number both machines already agree on
        self.assertIn("running '+(buildWord(t.kernelVer,t.kernelSha)||'?')", js)
        self.assertIn("this machine is at '+(buildWord(t.localVer,t.localSha)||'?')", js)
        self.assertIn("t.kernelDate", js)

    def test_popover_js_parses(self):
        # the inline JS ships unparsed inside the kernel's HTML — a stray brace only surfaces
        # when the popover breaks in the browser; parse it the way the browser will
        node = shutil.which("node")
        if not node:
            self.skipTest("node unavailable")
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(km._LANDING_REMOTES_JS)
            path = f.name
        try:
            r = subprocess.run([node, "--check", path], capture_output=True, text=True, timeout=15)
            self.assertEqual(r.returncode, 0, r.stderr)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()

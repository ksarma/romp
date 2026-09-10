#!/usr/bin/env python3
"""SDK-session lifecycle hardening (2026-07-05: a kernel death stranded every SDK session in
"purgatory" — cut turns never resumed, in-memory queues silently dropped, one orphaned CLI).

Covers the backend half:
  * queue persistence — SdkSession._pending mirrors to the registry on every mutation and is
    re-seeded from it, so a kernel death can DELAY queued turns but never lose them;
  * last_state_value — the cut-turn discriminator reads the last STATE record through the
    interleaved awaiting overlays (the boot heal itself appends one);
  * find_orphan_clis — matches only ORPHANED SDK-driven CLIs, i.e. whose parent is no live romp
    kernel (ppid 1 on macOS; the `systemd --user` subreaper on Linux, 2026-09-05) (--resume <ours> +
    stream-json), never a tmux session's interactive `claude --resume` and never a LIVE CLI still
    parented to a kernel (2026-07-06: a duplicate backend's reconcile reaped live sessions);
  * _boot_reconcile — resumes exactly the cut-turn / queued sessions (a user-interrupted or
    cleanly-finished session stays lazy), prepends the visible continuation nudge, reaps orphans;
  * drain — the SIGTERM path stops every running session, counts in-flight turns, and writes NO
    idle/waiting state (the trailing 'working' IS the next boot's resume marker).

All deterministic: no SDK import, no real claude processes (ps/os.kill are patched) — except PsArgv's
two real-ps tests, Linux-only, which run the machine's ps against a sleeper child they spawn and kill.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import signal
import threading
import time
import types
import unittest
import uuid
from pathlib import Path
from unittest import mock
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = load_source("romp_sdk_backend", os.path.join(BIN, "romp_sdk_backend.py"))


def _backend(d=None):
    return sb.SdkBackend(d or tempfile.mkdtemp(), "/bin/true", lambda *a, **k: None)


def _pid_max() -> int:
    """Fake pids above this can never be a live process on the box (T276c) — the reaper's liveness poll and
    os.getpgid then answer deterministically for them on every runner."""
    try:
        return int(open("/proc/sys/kernel/pid_max").read().strip())
    except (OSError, ValueError):
        return 4194304


_P = _pid_max()


def _reg(d, sid, **extra):
    r = {"sid": sid, "name": "s-" + sid[:4], "cwd": "/tmp", "alive": True, "lastSid": sid}
    r.update(extra)
    sb.write_reg(Path(d), sid, r)
    return r


class LastStateValue(unittest.TestCase):
    def test_reads_through_awaiting_overlays(self):
        d = tempfile.mkdtemp()
        sid = "11111111-2222-3333-4444-555555555555"
        sb.append_state(Path(d), sid, "working")
        sb.append_awaiting(Path(d), sid, False)      # the boot heal appends exactly this overlay
        self.assertEqual(sb.last_state_value(Path(d), sid), "working",
                         "an overlay after the state record must not hide the cut-turn marker")
        # last_state (the literal last line) would have returned the overlay — that's the trap
        self.assertNotIn("state", sb.last_state(Path(d), sid))

    def test_empty_and_missing(self):
        d = tempfile.mkdtemp()
        self.assertEqual(sb.last_state_value(Path(d), "nope"), "")


class FindOrphanClis(unittest.TestCase):
    SID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    OWN = 31337   # this kernel's pid in the fixtures; no fixture below uses it as a parent

    def test_matches_only_sdk_clis_resuming_ours(self):
        lines = [
            # ours, SDK-driven (stream-json), re-parented to launchd → a true orphan, matched
            " 4242 1 /x/claude --output-format stream-json --resume %s --input-format stream-json" % self.SID,
            # a TMUX session's interactive resume (no stream-json mark) → never touched
            " 4243 1 claude --resume %s --name termsess" % self.SID,
            # SDK-driven but a sid we don't own → not ours to reap
            " 4244 1 /x/claude --resume ffffffff-0000-1111-2222-333333333333 --input-format stream-json",
            # junk / short lines are skipped, not crashed on
            "garbage", " 99", " 99 100", "",
        ]
        self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [4242])

    def test_live_children_are_never_orphans(self):
        # Same command line as a true orphan, but still parented to a running kernel (the kernel's
        # own line is in the listing): a LIVE session's CLI. Reaping these was the 2026-07-06 kill
        # storm — a duplicate backend's reconcile SIGTERM'd freshly-resumed sessions mid-turn (exit 143).
        lines = [
            " 38438 901 /usr/bin/python3.12 /x/romp/bin/romp-kernel",
            " 4242 38438 /x/claude --output-format stream-json --resume %s --input-format stream-json" % self.SID,
            " 4245 1 /x/claude --output-format stream-json --resume %s --input-format stream-json" % self.SID,
        ]
        self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [4245])

    # Orphaned = the parent is not a live romp kernel (2026-09-05). Until then the check was ppid 1,
    # which is what an orphan gets under launchd — and never under `systemd --user`, whose
    # PR_SET_CHILD_SUBREAPER re-parents an orphan (from the service cgroup or from a transient scope
    # alike) to the user manager's pid, so the reap had matched nothing on Linux under the service.
    def _cli(self, pid, ppid):
        return " %d %d /x/claude --output-format stream-json --resume=%s --input-format stream-json" % (pid, ppid, self.SID)

    def test_orphan_reparented_to_launchd(self):
        # macOS: pid 1 is launchd, present in the listing and not a kernel
        lines = [" 1 0 /sbin/launchd", self._cli(700, 1)]
        self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [700])

    def test_orphan_reparented_to_the_systemd_user_manager(self):
        # Linux under the service: the orphan's ppid is the `systemd --user` pid, never 1
        lines = [" 1 0 /sbin/init", " 901 1 /usr/lib/systemd/systemd --user", self._cli(701, 901)]
        self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [701])

    def test_orphan_whose_parent_is_absent_from_the_listing(self):
        # the parent died between the CLI's line and its own (ps is not atomic) — an orphan
        lines = [self._cli(702, 65000)]
        self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [702])

    def test_a_live_cli_parented_to_a_romp_kernel_is_never_reaped(self):
        for kernel in (" 500 901 /usr/bin/python3.12 /x/romp/bin/romp-kernel",
                       " 500 901 python3 bin/romp-kernel",
                       " 500 901 python3 kernel/kernel.py",
                       " 500 901 /usr/bin/python3 /x/romp/kernel/kernel.py"):
            lines = [" 901 1 /usr/lib/systemd/systemd --user", kernel, self._cli(703, 500)]
            self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [], kernel)

    def test_a_cli_parented_to_a_different_live_kernel_is_that_kernels(self):
        # another kernel (an aux port, a second install) owns this CLI — not ours to reap, whatever
        # sid it carries; the orphan next to it, parented to the user manager, still is
        lines = [" 901 1 /usr/lib/systemd/systemd --user",
                 " 600 901 /usr/bin/python3.12 /elsewhere/romp/bin/romp-kernel",
                 self._cli(704, 600), self._cli(705, 901)]
        self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [705])

    # This kernel's own children are live by PID, not by how `ps` spells the kernel (the #941 review).
    # _is_kernel_cmd knows the spellings romp-serve and a hand run produce; under any other (a `-c`
    # runner, a renamed launcher, `python3 ./kernel.py`) it read the caller's own children as orphans —
    # the unconditional protection the old `ppid != 1` test gave them, lost. A foreign kernel is still
    # judged by its text: the pid shortcut is for the caller only.
    def test_this_kernels_own_children_are_live_whatever_ps_calls_it(self):
        for kernel in ("python3 ./kernel.py",
                       "/usr/bin/python3 -c import runpy; runpy.run_path('kernel/kernel.py')",
                       "/x/venv/bin/python /x/romp/bin/romp-kernel-dev"):
            self.assertFalse(sb._is_kernel_cmd(kernel), kernel)     # so the pid path is what protects them
            lines = [" 901 1 /usr/lib/systemd/systemd --user", " %d 901 %s" % (self.OWN, kernel),
                     self._cli(707, self.OWN), self._cli(708, 901)]
            self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [708], kernel)

    def test_own_children_stay_live_when_the_kernels_own_line_is_absent(self):
        # unlike test_orphan_whose_parent_is_absent_from_the_listing (ppid 65000 is not us, so that one
        # IS an orphan): a listing that missed our own line still protects our children, by pid
        self.assertEqual(sb.find_orphan_clis([self._cli(709, self.OWN)], [self.SID], self.OWN), [])

    def test_another_kernels_children_are_still_judged_by_its_text(self):
        # the boundary #941 drew, unchanged: a kernel spelled in a way _is_kernel_cmd does not know
        # shields nothing unless it is THIS kernel
        lines = [" 901 1 /usr/lib/systemd/systemd --user", " 600 901 python3 ./kernel.py", self._cli(710, 600)]
        self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [710])

    def test_kernel_match_is_on_argv_tokens_not_substrings(self):
        self.assertTrue(sb._is_kernel_cmd("/usr/bin/python3.12 /x/romp/bin/romp-kernel"))
        self.assertTrue(sb._is_kernel_cmd("python3 kernel/kernel.py"))
        self.assertTrue(sb._is_kernel_cmd("python3 kernel.py"))
        # a process merely mentioning the kernel is not one: its child would be an orphan
        self.assertFalse(sb._is_kernel_cmd("tail -f /x/state/romp/romp-kernel.log"))
        self.assertFalse(sb._is_kernel_cmd("node /x/romp/bin/romp-manager up"))
        self.assertFalse(sb._is_kernel_cmd("/usr/lib/systemd/systemd --user"))
        self.assertFalse(sb._is_kernel_cmd("python3 other/kernel.py"))
        lines = [" 800 1 tail -f /x/state/romp/romp-kernel.log", self._cli(706, 800)]
        self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [706])

    def test_empty_sids_match_nothing(self):
        lines = [" 1 1 claude --resume  --input-format stream-json"]
        self.assertEqual(sb.find_orphan_clis(lines, [""], self.OWN), [])

    def test_equals_flag_spelling_matches(self):
        # The Agent SDK moved to `--resume=<sid>` (equals form); the space-only match was blind to
        # it, so every boot reconcile "reaped 0" while a real orphan kept working the repo for over
        # an hour (2026-07-25, the twin incident). Both spellings, and --session-id for a CLI that
        # was spawned fresh and never resumed, must match.
        lines = [
            " 5001 1 /x/claude --output-format stream-json --resume=%s --input-format stream-json" % self.SID,
            " 5002 1 /x/claude --output-format stream-json --session-id=%s --input-format stream-json" % self.SID,
            " 5003 1 /x/claude --output-format stream-json --session-id %s --input-format stream-json" % self.SID,
            # equals form but a foreign sid → still not ours
            " 5004 1 /x/claude --resume=ffffffff-0000-1111-2222-333333333333 --input-format stream-json",
        ]
        self.assertEqual(sb.find_orphan_clis(lines, [self.SID], self.OWN), [5001, 5002, 5003])


class QueuePersistence(unittest.TestCase):
    def test_enqueue_and_unqueue_mirror_to_registry(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        sid = "11111111-2222-3333-4444-666666666666"
        reg = _reg(d, sid)
        s = sb.SdkSession(be, reg)                   # never started: pure kernel-thread surface
        s.enqueue("first")
        s.enqueue("second")
        self.assertEqual(sb.read_reg(Path(d), sid).get("queue"), ["first", "second"])
        self.assertEqual(s.unqueue(0), "first")
        self.assertEqual(sb.read_reg(Path(d), sid).get("queue"), ["second"],
                         "a canceled turn leaves the persisted queue too")

    def test_init_seeds_pending_from_persisted_queue(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        sid = "11111111-2222-3333-4444-777777777777"
        reg = _reg(d, sid, queue=["held over", "", 42, "and this"])
        s = sb.SdkSession(be, reg)
        self.assertEqual(s.pending(), ["held over", "and this"],
                         "restores strings only — junk entries never wedge delivery")


class TodoIdsRideTheQueue(unittest.TestCase):
    """Round-2 findings 1-3 (the restart-recall asymmetry), backend half: a user-todo ANSWER's id
    travels WITH the queued message — on the in-memory entry, through the reg mirror
    (_persist_queue), and back through the boot seed — so a recall after a kernel restart reads
    the id off the entry it removes, with no kernel-side table to lose. Entries without an id
    stay bare strings: the mirror is byte-identical to the pre-todo shape for every other send
    (an older kernel reads those untouched; only an id-carrying answer serializes as a dict), and
    every rewrite of reg['queue'] keeps a dict entry intact instead of erasing it with a
    strings-only filter (the thread wake's notice prepend was the one rewrite that still did,
    2026-09-07)."""

    ANSWER = "Re: need the staging port — 8443."

    def _session(self, queue=None):
        d = tempfile.mkdtemp()
        be = _backend(d)
        sid = "11111111-2222-3333-4444-888888888888"
        reg = _reg(d, sid, **({"queue": queue} if queue is not None else {}))
        return d, be, sid, sb.SdkSession(be, reg)

    def test_an_answer_entry_mirrors_with_its_id_and_bare_sends_stay_bare(self):
        d, be, sid, s = self._session()
        s.enqueue("plain message")
        s.enqueue(self.ANSWER, todo="ut-9f2c1a34")
        self.assertEqual(sb.read_reg(Path(d), sid).get("queue"),
                         ["plain message", {"text": self.ANSWER, "todo": "ut-9f2c1a34"}])

    def test_the_seed_restores_the_id_onto_the_entry(self):
        d, be, sid, s = self._session(queue=["held over",
                                             {"text": self.ANSWER, "todo": "ut-11112222"},
                                             {"bogus": 1}, "", 42])
        self.assertEqual(s.pending(), ["held over", self.ANSWER],
                         "both shapes seed; junk is filtered exactly as before")
        self.assertEqual([getattr(t, "todo", "") for t in s.pending()], ["", "ut-11112222"])

    def test_unqueue_returns_the_id_bearing_text_and_cleans_the_mirror(self):
        d, be, sid, s = self._session()
        s.enqueue(self.ANSWER, todo="ut-9f2c1a34")
        got = s.unqueue(0)
        self.assertEqual(got, self.ANSWER, "the text contract is unchanged")
        self.assertEqual(getattr(got, "todo", ""), "ut-9f2c1a34",
                         "the id rides the returned entry — the recall's reopen reads it here")
        self.assertEqual(sb.read_reg(Path(d), sid).get("queue"), [])

    def test_backend_unqueue_hands_the_id_through(self):
        d, be, sid, s = self._session()
        with be._lock:
            be.sessions[sid] = s
        s.enqueue(self.ANSWER, todo="ut-9f2c1a34")
        got = be.unqueue(sid, 0)
        self.assertEqual(got, self.ANSWER)
        self.assertEqual(getattr(got, "todo", ""), "ut-9f2c1a34")

    def test_boot_prepend_preserves_id_entries(self):
        # the cut-turn nudge prepend rewrites reg['queue'] — the dict entry must ride behind it
        # intact, not be dropped by a strings-only filter
        d = tempfile.mkdtemp()
        be = _backend(d)
        be._ensure = lambda sid, on_boot_settled=None: on_boot_settled and on_boot_settled()
        cut = "11111111-aaaa-0000-0000-0000000000f0"
        _reg(d, cut, queue=[{"text": self.ANSWER, "todo": "ut-33334444"}, "plain backlog"])
        sb.append_state(Path(d), cut, "working")
        with mock.patch.object(sb.subprocess, "run", return_value=mock.Mock(stdout="")):
            be._boot_reconcile([sb.read_reg(Path(d), cut)])
        self.assertEqual(sb.read_reg(Path(d), cut).get("queue"),
                         [sb.BOOT_RESUME_NUDGE,
                          {"text": self.ANSWER, "todo": "ut-33334444"}, "plain backlog"])

    def test_crash_heal_prepend_preserves_id_entries(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        be._ensure = lambda sid, on_boot_settled=None: None
        sid = "11111111-aaaa-0000-0000-0000000000f1"
        _reg(d, sid, queue=[{"text": self.ANSWER, "todo": "ut-55556666"}])
        s = sb.SdkSession(be, sb.read_reg(Path(d), sid))
        be._heal_cut_session(s)
        self.assertEqual(sb.read_reg(Path(d), sid).get("queue"),
                         [sb.CRASH_RESUME_NUDGE, {"text": self.ANSWER, "todo": "ut-55556666"}])

    def test_reconcile_strand_rehead_keeps_the_id(self):
        # the fed-turn twin (_inflight_texts) re-heads the queue when no conversation ever
        # materialized — the restored entry must still carry its id into the mirror
        d, be, sid, s = self._session()
        s.resume_sid = None                          # no init ever streamed: the re-head arm
        s.enqueue(self.ANSWER, todo="ut-77778888")
        with s._lock:
            fed = s._pending.pop(0)                  # the input generator feeds the entry…
        s.inflight = 1
        s._inflight_texts.append(fed)                # …and its twin carries it, id and all
        s._reconcile_stranded()
        self.assertEqual([getattr(t, "todo", "") for t in s.pending()], ["ut-77778888"])
        self.assertEqual(sb.read_reg(Path(d), sid).get("queue"),
                         [{"text": self.ANSWER, "todo": "ut-77778888"}])

    def test_a_plain_queue_serializes_exactly_as_before(self):
        # byte-stability: with no answer queued, the mirror's JSON is the pre-todo list of strings
        d, be, sid, s = self._session()
        s.enqueue("first")
        s.enqueue("second")
        raw = json.dumps(sb.read_reg(Path(d), sid).get("queue"), sort_keys=True)
        self.assertEqual(raw, json.dumps(["first", "second"], sort_keys=True))

    def test_pending_queued_decodes_the_persisted_shape_for_a_dormant_session(self):
        # the chat's queued bubbles for a NOT-running session come from the reg mirror: an
        # id-carrying entry renders as its text (and keeps its id), junk is filtered as before
        d = tempfile.mkdtemp()
        be = _backend(d)
        sid = "11111111-aaaa-0000-0000-0000000000e9"
        _reg(d, sid, queue=["plain", {"text": self.ANSWER, "todo": "ut-22223333"}, {"bogus": 1}, ""])
        got = be.pending_queued(sid)
        self.assertEqual(got, ["plain", self.ANSWER])
        self.assertEqual([getattr(t, "todo", "") for t in got], ["", "ut-22223333"])

    def test_thread_wake_notice_preserves_id_entries(self):
        # a dormant comment thread woken with a killed question: _ensure rewrites reg['queue'] to put
        # the notice first. The dict entry must ride behind it intact, in the reg AND in the dict the
        # SdkSession seed reads; before the fix the strings-only filter there erased it, and the
        # user's answer was gone with its ask already stamped answered.
        d = tempfile.mkdtemp()
        be = _backend(d)
        sid = "11111111-aaaa-0000-0000-0000000000f2"
        owner = "11111111-aaaa-0000-0000-0000000000f3"
        _reg(d, sid, threadOf=owner, pendingAsk=True,
             queue=[{"text": self.ANSWER, "todo": "ut-99990000"}, "plain reply"])
        seeded = []

        class _Fake:
            def __init__(self, backend, reg):
                seeded.append(reg)
                self.thread = types.SimpleNamespace(is_alive=lambda: True)

            def start(self):
                pass

        with mock.patch.object(sb, "SdkSession", _Fake):
            be._ensure(sid)
        want = [sb.ASK_DIED_NOTICE, {"text": self.ANSWER, "todo": "ut-99990000"}, "plain reply"]
        self.assertEqual(sb.read_reg(Path(d), sid).get("queue"), want)
        self.assertEqual(seeded[0].get("queue"), want, "the seed reads THIS dict")


def _procps() -> bool:
    """Whether this box's ps is procps (Linux; BSD ps has no --version). The truncation control below
    pins procps behaviour, so it runs only there."""
    try:
        return "procps" in subprocess.run(["ps", "--version"], capture_output=True, text=True, timeout=10).stdout
    except Exception:
        return False


class PsArgv(unittest.TestCase):
    """The `ps` both process scans run. `-ww` is the point: procps truncates every line to $COLUMNS
    when that variable is exported (BSD ps does by default), and an SDK CLI's sid sits ~2 KB into its
    argv behind --append-system-prompt, so a kernel started with COLUMNS exported reaped nothing and
    could not find its own child to signal, silently (2026-09-05; `COLUMNS=80 ps -axo` cut a 3200-char
    argv at 80 columns on procps-ng 4.0.4, `-axwwo` printed it whole). The first three tests pin the
    argv and its two call sites through mocks; the last two run this box's ps against a real long argv,
    on Linux only, so the width property itself has an executable check."""

    def test_the_argv_asks_for_unlimited_width(self):
        self.assertEqual(sb.PS_ARGV, ["ps", "-axwwo", "pid=,ppid=,command="])

    # GNU sleep rejects a non-numeric argument, so the sleeper with the >3000-character argv is this
    # interpreter, given the marker as an argument it ignores; it is killed on the way out. The marker is
    # minted per test so nothing else on the box (this process's own argv included) can carry it.
    def _sleeper_with_a_long_argv(self):
        marker = "romp-ps-ww-tail-" + uuid.uuid4().hex
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)", "x" * 3000 + marker],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(child.wait, timeout=10)
        self.addCleanup(child.kill)
        return child, marker

    def _ps_line_for(self, pid, argv):
        out = subprocess.run(argv, env={**os.environ, "COLUMNS": "80"}, capture_output=True, text=True,
                             timeout=10).stdout
        mine = [ln for ln in out.splitlines() if ln.split()[:1] == [str(pid)]]
        self.assertEqual(len(mine), 1, "one line for the sleeper's pid: %r" % (mine,))
        return mine[0]

    @unittest.skipUnless(sys.platform.startswith("linux") and shutil.which("ps"), "a real ps on Linux")
    def test_a_real_ps_under_columns_80_prints_a_3000_character_argv_whole(self):
        child, marker = self._sleeper_with_a_long_argv()
        line = self._ps_line_for(child.pid, sb.PS_ARGV)
        self.assertIn(marker, line, "the argv's tail survived COLUMNS=80 (line is %d chars)" % len(line))
        self.assertGreater(len(line), 3000)

    @unittest.skipUnless(sys.platform.startswith("linux") and _procps(), "procps ps on Linux")
    def test_without_ww_the_same_ps_cuts_the_argv_at_columns(self):
        # the control: the argv PS_ARGV replaced (-axo) loses the marker on procps, so the test above
        # passes because of -ww and not because this box's ps never truncates
        child, marker = self._sleeper_with_a_long_argv()
        line = self._ps_line_for(child.pid, ["ps", "-axo", "pid=,ppid=,command="])
        self.assertNotIn(marker, line)
        self.assertLessEqual(len(line), 80)

    def test_the_interrupt_escalation_reads_ps_with_it(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        sid = "11111111-aaaa-0000-0000-00000000000f"
        _reg(d, sid)
        # our own child (ppid = this process), its sid 2 KB into the argv — what -ww keeps intact
        ps = "  4242 %d /x/claude --append-system-prompt %s --resume %s --input-format stream-json\n" % (
            os.getpid(), "p" * 2100, sid)
        with mock.patch.object(sb.subprocess, "run", return_value=mock.Mock(stdout=ps)) as run:
            pid = be._session_cli_pid(types.SimpleNamespace(sid=sid, name="web"))
        self.assertEqual(pid, 4242)
        self.assertEqual(run.call_args_list[0][0][0], sb.PS_ARGV)

    def test_the_boot_reaper_reads_ps_with_it(self):
        # the reaper's own reap test (BootReconcile.test_reaps_orphans_but_never_tmux) pins the same
        # argv on its call; this one pins that the two sites share ONE constant, so neither can drift
        with open(sb.__file__) as f:
            src = f.read()
        self.assertNotIn('"-axo"', src, "every ps scan goes through PS_ARGV (-ww)")
        self.assertEqual(src.count("subprocess.run(PS_ARGV"), 2, "the reaper and the escalation")


class BootReconcile(unittest.TestCase):
    def _setup(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        be._ensured = []
        be._ensure = lambda sid, on_boot_settled=None: (be._ensured.append(sid), on_boot_settled and on_boot_settled())
        return d, be

    def test_resumes_exactly_cut_and_queued_sessions(self):
        d, be = self._setup()
        cut = "11111111-aaaa-0000-0000-000000000001"       # tail 'working' → cut by the kernel death
        queued = "11111111-aaaa-0000-0000-000000000002"    # finished, but has a persisted queue
        interrupted = "11111111-aaaa-0000-0000-000000000003"  # user interrupt wrote 'idle'
        finished = "11111111-aaaa-0000-0000-000000000004"  # clean turn end wrote 'waiting'
        dead = "11111111-aaaa-0000-0000-000000000005"
        regs = [_reg(d, cut), _reg(d, queued, queue=["waiting msg"]),
                _reg(d, interrupted), _reg(d, finished), _reg(d, dead, alive=False)]
        sb.append_state(Path(d), cut, "working")
        sb.append_state(Path(d), queued, "waiting")
        sb.append_state(Path(d), interrupted, "working")
        sb.append_state(Path(d), interrupted, "idle")      # the user-interrupt marker
        sb.append_state(Path(d), finished, "waiting")
        sb.append_state(Path(d), dead, "working")          # dead: even a 'working' tail stays dead
        with mock.patch.object(sb.subprocess, "run",
                               return_value=mock.Mock(stdout="")):
            be._boot_reconcile(regs)
        self.assertEqual(sorted(be._ensured), sorted([cut, queued]),
                         "user-interrupted / finished / dead sessions stay lazy")

    def test_cut_turn_gets_the_nudge_prepended_before_its_queue(self):
        d, be = self._setup()
        cut = "11111111-aaaa-0000-0000-00000000000a"
        _reg(d, cut, queue=["sent during the outage"])
        sb.append_state(Path(d), cut, "working")
        sb.append_awaiting(Path(d), cut, False)            # the boot heal's overlay must not mask the cut
        with mock.patch.object(sb.subprocess, "run", return_value=mock.Mock(stdout="")):
            be._boot_reconcile([sb.read_reg(Path(d), cut)])
        q = sb.read_reg(Path(d), cut).get("queue")
        self.assertEqual(q, [sb.BOOT_RESUME_NUDGE, "sent during the outage"],
                         "the visible continuation nudge is fed FIRST, then the restored backlog")
        self.assertEqual(be._ensured, [cut])

    def test_dead_bg_tasks_wake_the_session_with_a_named_notice(self):
        # bg tasks die with their CLI (the user 2026-07-11: nimbus's campaign watcher died with a
        # kernel restart and the session waited forever on a notification that could never arrive).
        # The reg's bgTasks mirror survives the death; the reconcile must tell the session what it
        # lost — by DESCRIPTION — and clear the mirror so the same deaths never re-notify.
        d, be = self._setup()
        sid = "11111111-aaaa-0000-0000-00000000000c"
        _reg(d, sid, bgTasks=[{"desc": "20-minute timer for campaign-start check", "type": "local_bash",
                               "since": 1, "toolUseId": "tu1", "lastTool": ""}])
        sb.append_state(Path(d), sid, "waiting")           # idle — NOT cut; the notice alone wakes it
        with mock.patch.object(sb.subprocess, "run", return_value=mock.Mock(stdout="")):
            be._boot_reconcile([sb.read_reg(Path(d), sid)])
        self.assertEqual(be._ensured, [sid], "an idle session with dead tasks is woken to hear it")
        reg = sb.read_reg(Path(d), sid)
        self.assertEqual(len(reg["queue"]), 1)
        self.assertIn("20-minute timer for campaign-start check", reg["queue"][0])
        self.assertIn("romp-system", reg["queue"][0], "a visible romp system notice, not silent")
        self.assertEqual(reg["bgTasks"], [], "reported — the same deaths never re-notify")

    def test_cut_turn_with_dead_tasks_orders_resume_nudge_then_notice(self):
        d, be = self._setup()
        sid = "11111111-aaaa-0000-0000-00000000000d"
        _reg(d, sid, queue=["backlog msg"], bgTasks=[{"desc": "power watcher", "since": 1}])
        sb.append_state(Path(d), sid, "working")           # cut by the kernel death
        with mock.patch.object(sb.subprocess, "run", return_value=mock.Mock(stdout="")):
            be._boot_reconcile([sb.read_reg(Path(d), sid)])
        q = sb.read_reg(Path(d), sid)["queue"]
        self.assertEqual(q[0], sb.BOOT_RESUME_NUDGE, "continuation context first")
        self.assertIn("power watcher", q[1])
        self.assertEqual(q[2], "backlog msg", "the restored backlog follows the notices")

    def test_stranded_pending_switch_flags_heal_at_boot_without_waking_the_session(self):
        # a /model or /effort switch mid-flight at the kernel's death strands its pending flags; the
        # dormant serving path shows them as switching-dots FOREVER (the user 2026-07-11, who reported the three
        # dots sitting there forever). The boot sweep heals the flags; an otherwise-idle session
        # stays lazy (no wake just for the heal).
        d, be = self._setup()
        sid = "11111111-aaaa-0000-0000-00000000000e"
        _reg(d, sid, effortPending=True, modelPending=True)
        sb.append_state(Path(d), sid, "waiting")
        with mock.patch.object(sb.subprocess, "run", return_value=mock.Mock(stdout="")):
            be._boot_reconcile([sb.read_reg(Path(d), sid)])
        reg = sb.read_reg(Path(d), sid)
        self.assertFalse(reg.get("effortPending"))
        self.assertFalse(reg.get("modelPending"))
        self.assertEqual(be._ensured, [], "the heal alone never wakes a session")

    def test_the_sweep_reads_each_registry_fresh_not_the_listing_it_was_handed(self):
        # __init__ lists the registries, then the echo reseed may re-queue a lost send into one of
        # them ON DISK, then the sweep walks that same listing: a row listed before the write still
        # showed an empty queue, so the session sat dormant with a message waiting in its registry.
        d, be = self._setup()
        sid = "11111111-aaaa-0000-0000-00000000000f"
        regs = [_reg(d, sid, queue=[])]                    # the listing: nothing queued yet
        sb.write_reg(Path(d), sid, {**regs[0], "queue": ["re-queued after the listing"]})   # the reseed's write
        sb.append_state(Path(d), sid, "waiting")
        with mock.patch.object(sb.subprocess, "run", return_value=mock.Mock(stdout="")):
            be._boot_reconcile(regs)
        self.assertEqual(be._ensured, [sid], "the sweep decides from the registry on disk, not the stale row")

    def test_reaps_orphans_but_never_tmux(self):
        d, be = self._setup()
        sid = "11111111-aaaa-0000-0000-00000000000b"
        _reg(d, sid)
        sb.append_state(Path(d), sid, "working")
        # the orphan's fake pid sits above pid_max (T276): the tree kill polls procfs after its SIGTERM, and a live
        # process wearing a small fake pid on the box would earn a SIGKILL the pin below does not expect
        ps = ("  9999555 1 /x/claude --output-format stream-json --resume %s --input-format stream-json\n"
              "  556 1 claude --resume %s --name termsess\n"
              "  90210 1 /usr/bin/python3 /x/romp/bin/romp-kernel\n"
              "  557 90210 /x/claude --output-format stream-json --resume %s --input-format stream-json\n"
              ) % (sid, sid, sid)
        killed = []
        with mock.patch.object(sb.subprocess, "run", return_value=mock.Mock(stdout=ps)) as run, \
             mock.patch.object(sb.os, "kill", side_effect=lambda p, s: killed.append((p, s))):
            be._boot_reconcile([sb.read_reg(Path(d), sid)])
        self.assertEqual(killed, [(9999555, sb.signal.SIGTERM)],
                         "the SDK orphan is reaped; the tmux CLI and the live (parented) CLI "
                         "on the same sid are untouched")
        self.assertEqual(run.call_args_list[0][0][0], sb.PS_ARGV, "the listing is read with PS_ARGV")

    def test_the_reaper_shields_this_kernels_own_children_by_pid(self):
        # The reconcile runs on a thread after the backend is up, concurrent with the kernel serving
        # requests, so a session started before the thread's `ps` is THIS kernel's child carrying one
        # of the lastsids. With the kernel spelled in a way _is_kernel_cmd does not know it was reaped
        # as an orphan (the #941 review); the caller hands its own pid down, and the child is live by it.
        d, be = self._setup()
        sid = "11111111-aaaa-0000-0000-00000000000d"
        _reg(d, sid)
        sb.append_state(Path(d), sid, "working")
        me = os.getpid()
        # fake pids above pid_max (T276c): a live runner process wearing a small fake pid made the tree kill
        # take a REAL process group (os.getpgid succeeded, killpg went unrecorded — an empty list on one
        # interpreter) or escalate to SIGKILL (the liveness poll saw it alive — an extra signal on another)
        MANAGER, OURS, ORPHAN = _P + 901, _P + 558, _P + 559
        ps = ("  %d 1 /usr/lib/systemd/systemd --user\n"
              "  %d %d python3 ./kernel.py\n"
              "  %d %d /x/claude --output-format stream-json --resume %s --input-format stream-json\n"
              "  %d %d /x/claude --output-format stream-json --resume %s --input-format stream-json\n"
              ) % (MANAGER, me, MANAGER, OURS, me, sid, ORPHAN, MANAGER, sid)
        killed = []
        with mock.patch.object(sb.subprocess, "run", return_value=mock.Mock(stdout=ps)), \
             mock.patch.object(sb.os, "kill", side_effect=lambda p, s: killed.append((p, s))), \
             mock.patch.object(sb.os, "killpg", side_effect=lambda g, s: killed.append(("pg", g, s))), \
             mock.patch.object(sb.SdkBackend, "_pid_alive", lambda self, p: False):   # nothing is alive after its SIGTERM: no grace, no SIGKILL
            be._boot_reconcile([sb.read_reg(Path(d), sid)])
        self.assertEqual(killed, [(ORPHAN, sb.signal.SIGTERM)],
                         "a child this kernel already spawned is left alone whatever ps calls the kernel; "
                         "the orphan under the user manager is reaped with exactly one SIGTERM — no group kill, no escalation")

    def test_reconcile_is_opt_in(self):
        # Constructing the backend plain (tests, ad-hoc) must NOT spawn a reconcile thread; the
        # kernel opts in with reconcile=True. Pinned by patching the method and constructing both ways.
        d = tempfile.mkdtemp()
        sid = "11111111-aaaa-0000-0000-00000000000c"
        _reg(d, sid)
        sb.append_state(Path(d), sid, "working")
        with mock.patch.object(sb.SdkBackend, "_boot_reconcile") as br:
            sb.SdkBackend(d, "/bin/true", lambda *a, **k: None)
            self.assertEqual(br.call_count, 0)
            sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, reconcile=True)
            deadline = time.time() + 5
            while br.call_count == 0 and time.time() < deadline:
                time.sleep(0.01)                     # the reconcile runs on its own thread
            self.assertEqual(br.call_count, 1)


class WriteRegConcurrency(unittest.TestCase):
    def test_temp_names_are_writer_unique(self):
        """During a kernel restart the OUTGOING kernel and the incoming boot reconcile write the
        SAME sid's registry concurrently; a shared '<sid>.tmp' let one os.replace steal the other's
        temp mid-write (FileNotFoundError, live 2026-07-06). Pin: concurrent writers never collide
        and the final registry is one of the written values, with no stray temps left behind."""
        d = tempfile.mkdtemp()
        sid = "11111111-2222-3333-4444-888888888888"
        errs = []

        def hammer(tag):
            try:
                for i in range(50):
                    sb.write_reg(Path(d), sid, {"sid": sid, "writer": tag, "i": i})
            except Exception as e:
                errs.append(e)

        ts = [threading.Thread(target=hammer, args=(t,)) for t in ("a", "b", "c")]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        self.assertEqual(errs, [], "no writer may crash on another's temp file")
        self.assertIn(sb.read_reg(Path(d), sid).get("writer"), ("a", "b", "c"))
        strays = [f for f in os.listdir(os.path.join(d, "sdk")) if f.endswith(".tmp")]
        self.assertEqual(strays, [], "failed/completed writes leave no temp litter")


class BootReconcileResilience(unittest.TestCase):
    def test_one_bad_session_does_not_strand_the_rest(self):
        """Live 2026-07-06: a write_reg race on the FIRST session aborted two whole reconcile
        passes, stranding every later session. One session's failure must log and continue."""
        d = tempfile.mkdtemp()
        be = _backend(d)
        be._ensured = []
        be._ensure = lambda sid, on_boot_settled=None: (be._ensured.append(sid), on_boot_settled and on_boot_settled())
        logs = []
        be._log_cb = logs.append
        bad = "11111111-aaaa-0000-0000-0000000000e1"
        good = "11111111-aaaa-0000-0000-0000000000e2"
        regs = [_reg(d, bad), _reg(d, good)]
        for s in (bad, good):
            sb.append_state(Path(d), s, "working")
        real_write = sb.write_reg

        def exploding_write(state_dir, sid, reg):
            if sid == bad:
                raise FileNotFoundError("simulated temp-steal race")
            real_write(state_dir, sid, reg)

        with mock.patch.object(sb.subprocess, "run", return_value=mock.Mock(stdout="")), \
             mock.patch.object(sb, "write_reg", side_effect=exploding_write):
            be._boot_reconcile(regs)
        self.assertEqual(be._ensured, [good], "the sweep continued past the failing session")
        self.assertTrue(any("sweep continues" in m for m in logs), "the failure is loud, not silent")


class CrashHeal(unittest.TestCase):
    """_on_session_gone on an ABNORMAL mid-turn death (CLI killed/crashed; not user-interrupted,
    not our shutdown) must NOT settle 'waiting' — that masked the cut and stranded the session
    until the next kernel restart (2026-07-06: reaped sessions wrote triple 'waiting' and stalled).
    Instead it keeps the trailing 'working' and resumes ONCE via _heal_cut_session; the budget
    re-arms only when a turn completes."""

    SID = "11111111-2222-3333-4444-777777777777"

    def _dead_session(self, be, d, inflight=1, interrupted=False, unit="default"):
        reg = sb.read_reg(Path(d), self.SID) or _reg(d, self.SID)   # keep a prior heal's queue intact
        s = sb.SdkSession(be, reg)          # never started: pure object surface
        sb.append_state(Path(d), self.SID, "working")
        s.inflight = inflight
        s._interrupted = interrupted
        s.cli_scope_unit = self.UNIT if unit == "default" else unit   # what _record_cli_scope left at connect
        return s

    def test_midturn_death_keeps_cut_marker_and_resumes(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        s = self._dead_session(be, d)
        with mock.patch.object(be, "_ensure") as ens:
            be._on_session_gone(s)
        self.assertEqual(sb.last_state_value(Path(d), self.SID), "working",
                         "no 'waiting' settle — the trailing 'working' IS the cut marker")
        q = sb.read_reg(Path(d), self.SID).get("queue")
        self.assertEqual(q, [sb.CRASH_RESUME_NUDGE],
                         "the visible crash nudge is queued so the resume is never silent")
        ens.assert_called_once_with(self.SID)

    def test_second_death_without_completed_turn_is_a_crash_loop(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        logs = []
        be._log_cb = logs.append
        with mock.patch.object(be, "_ensure") as ens:
            be._on_session_gone(self._dead_session(be, d))
            be._on_session_gone(self._dead_session(be, d))   # died again before any ResultMessage
        self.assertEqual(ens.call_count, 1, "one resume per cut — no respawn loop")
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE],
                         "the nudge is not stacked by the refused second heal")
        self.assertTrue(any("crash loop" in m for m in logs), "the give-up is loud")
        self.assertEqual(sb.last_state_value(Path(d), self.SID), "working",
                         "still cut — the next kernel restart's reconcile picks it up")

    def test_completed_turn_rearms_the_heal_budget(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        with mock.patch.object(be, "_ensure") as ens:
            be._on_session_gone(self._dead_session(be, d))
            be._turn_completed(self.SID)                     # a ResultMessage landed in between
            be._on_session_gone(self._dead_session(be, d))
        self.assertEqual(ens.call_count, 2, "a completed turn re-arms one resume for the next cut")

    # ── the cause, when the dead CLI's own scope still says (2026-09-10) ─────────────────────────────
    # Every session scope carries OOMPolicy=continue, under which systemd records NO Result on an OOM kill
    # (one process dies, the scope stands), so the heal reads the dead CLI's scope cgroup memory.events
    # `oom_kill` count first, and Result=oom-kill (a scope WITHOUT the property, which systemd stops whole)
    # second. It asks about the EXACT unit the CLI ran in (recorded from its /proc/<pid>/cgroup at connect,
    # SdkSession.cli_scope_unit), never a glob over the session's scopes: an older scope of the same session,
    # kept up by a tmux server and still draining an OOM kill of its own, would answer a glob. The fake
    # systemctl is table-driven (returncode, stdout, stderr) and records argv AND kwargs; it answers BYTES
    # when `text` is not asked for, as the real one would, so dropping text=True reproduces the real failure.
    UNIT = "romp-session-11111111-4242-1700000000000000000.scope"
    OLDER = "romp-session-11111111-4100-1600000000000000000.scope"   # an earlier CLI's scope, still up
    SHOW_ARGV = ["systemctl", "--user", "show", "--no-pager", "-p", "Id,LoadState,Result,ControlGroup", "--", UNIT]
    EVENTS = staticmethod(lambda n: "low 0\nhigh 0\nmax 37\noom %d\noom_kill %d\noom_group_kill 0\n" % (min(n, 1), n))

    @classmethod
    def _show(cls, unit=None, result="success", load="loaded", cgroup="default"):
        """A `systemctl show -p Id,LoadState,Result,ControlGroup -- <unit>` answer (the order systemd prints)."""
        unit = unit or cls.UNIT
        cg = "/fx.slice/%s" % unit if cgroup == "default" else cgroup
        return "Result=%s\nControlGroup=%s\nId=%s\nLoadState=%s\n" % (result, cg, unit, load)

    def _heal_with_show(self, d, be, stdout=None, raise_=None, returncode=0, stderr="", events=None, unit="default"):
        """Run the heal with the scopes on, a fake systemctl and a fake cgroup root: the fake records every
        (argv, kwargs) and answers (returncode, stdout, stderr), or raises; `events` maps a unit to the
        memory.events text under its /fx.slice/<unit> cgroup (no entry: no file). Returns (calls, log lines)."""
        be.cli_scope = True
        logs = []
        be._log_cb = logs.append
        calls = []
        root = tempfile.mkdtemp()
        for u, text in (events or {}).items():
            Path(root, "fx.slice", u).mkdir(parents=True)
            Path(root, "fx.slice", u, "memory.events").write_text(text)

        def fake_run(argv, **kw):
            calls.append((list(argv), dict(kw)))
            if raise_ is not None:
                raise raise_
            out, err = stdout or "", stderr or ""
            if "text" not in kw:
                out, err = out.encode(), err.encode()
            return mock.Mock(returncode=returncode, stdout=out, stderr=err)
        with mock.patch.object(sb.subprocess, "run", fake_run), mock.patch.object(sb, "CGROUP_ROOT", root), \
             mock.patch.object(be, "_ensure") as ens:
            be._on_session_gone(self._dead_session(be, d, unit=unit))
        ens.assert_called_once_with(self.SID)
        return calls, logs

    def _died_line(self, logs):
        line = [m for m in logs if "died mid-turn" in m]
        self.assertEqual(len(line), 1, logs)
        return line[0]

    def test_an_oom_kill_counted_in_the_scopes_cgroup_names_it_in_the_log_and_the_notice(self):
        # the primary signal: memory.events oom_kill > 0 with Result=success, which is what OOMPolicy=continue
        # leaves (verified on systemd 255: hog killed under MemoryMax=64M, oom_kill 1, Result=success)
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(1)})
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV], "one show, the dead CLI's exact unit, no glob")
        line = self._died_line(logs)
        self.assertIn("died mid-turn; the OOM killer took a process in its scope %s (memory.events oom_kill=1, Result=success)"
                      % self.UNIT, line)
        self.assertIn("resuming with history intact", line)
        q = sb.read_reg(Path(d), self.SID).get("queue")
        self.assertEqual(q, [sb.CRASH_RESUME_NUDGE_OOM], "the out-of-memory form of the notice, not the bare one")
        self.assertIn("out of memory", q[0])
        self.assertIn("OOM killer", q[0])
        self.assertTrue(sb.is_resume_nudge(q[0]), "readers that hide or re-head the resume nudge match this form too")
        self.assertTrue(sb.is_crash_resume_nudge(q[0]))
        self.assertEqual(sb.last_state_value(Path(d), self.SID), "working", "the cut marker stands as before")
        self.assertEqual(be.problems(), [], "naming a cause is no problem")
        self.assertFalse(any("session scope result" in m for m in logs), "both signals read: nothing to report")

    def test_the_show_asks_for_the_exact_unit_bounded_and_in_text_mode(self):
        # the argv literally (the constant and the unit), the 10 s bound, text mode and captured output: without
        # text=True the answer is bytes and the read raises out of the heal on the session thread (the fake
        # answers bytes then, as the real subprocess does)
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, _logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(0)})
        self.assertEqual(len(calls), 1)
        argv, kw = calls[0]
        self.assertEqual(argv, ["systemctl", "--user", "show", "--no-pager", "-p", "Id,LoadState,Result,ControlGroup", "--",
                                "romp-session-11111111-4242-1700000000000000000.scope"])
        self.assertEqual(argv, sb.SCOPE_SHOW_ARGV + [self.UNIT])
        self.assertEqual(kw.get("timeout"), sb.SCOPE_SHOW_TIMEOUT)
        self.assertEqual(sb.SCOPE_SHOW_TIMEOUT, 10.0)
        self.assertIs(kw.get("text"), True)
        self.assertIs(kw.get("capture_output"), True)
        self.assertNotIn("*", "".join(argv), "no pattern: the dead CLI's own scope and no other")

    def test_result_oom_kill_is_the_second_signal_for_a_scope_without_the_policy(self):
        # a scope systemd stopped whole (no OOMPolicy=continue on it: the marker, a dropped pre-flight, a
        # systemd before 253) reads Result=oom-kill in stop-sigterm while its processes go down; the counter
        # says so too, and is named first
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="oom-kill"), events={self.UNIT: self.EVENTS(1)})
        self.assertIn("(memory.events oom_kill=1, Result=oom-kill)", self._died_line(logs))
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        # with the counter unreadable, Result=oom-kill still names it, after a plain line about the counter
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="oom-kill"), events={})
        self.assertIn("took a process in its scope %s (Result=oom-kill)" % self.UNIT, self._died_line(logs))
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        self.assertTrue(any("session scope result" in m and "memory.events of %s could not be read" % self.UNIT in m for m in logs), logs)
        self.assertEqual(be.problems(), [])

    def test_a_scope_that_ended_otherwise_keeps_the_bare_notice(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="success"), events={self.UNIT: self.EVENTS(0)})
        self.assertEqual(len(calls), 1)
        line = self._died_line(logs)
        self.assertEqual(line, "session %s: claude process died mid-turn — resuming with history intact" % ("s-" + self.SID[:4]))
        self.assertNotIn("oom", line.lower())
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertFalse(any("session scope result" in m for m in logs), "both signals read and clear: nothing to report")

    def test_a_unit_no_longer_loaded_reads_as_no_verdict(self):
        # the scope already collected (every process gone): for an EXACT unit systemctl show still exits 0 and
        # prints a block, with LoadState=not-found, an empty ControlGroup and Result=success (verified on
        # systemd 255), so the read keys on LoadState and never mistakes that Result for a verdict
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""))
        self.assertEqual(len(calls), 1)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertFalse(any("oom" in m.lower() or "session scope result" in m for m in logs), logs)
        # an empty answer (nothing printed at all) is the same no verdict
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, "")
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertFalse(any("oom" in m.lower() for m in logs), logs)

    def test_no_unit_recorded_asks_nothing(self):
        # the CLI ran in no scope of its own (a fallback launch; a scope it inherited; the record failed): no
        # systemctl, the bare notice
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(1)}, unit=None)
        self.assertEqual(calls, [])
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertFalse(any("oom" in m.lower() for m in logs), logs)

    def test_an_older_scope_of_the_session_is_never_asked_about(self):
        # the older CLI's scope (kept up by a tmux server it started) is still draining an OOM kill of its own:
        # the dead CLI's scope reads clear, so the notice is bare, and the show never named the older unit
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.OLDER: self.EVENTS(1), self.UNIT: self.EVENTS(0)})
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV])
        self.assertNotIn(self.OLDER, str(calls))
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertFalse(any("oom" in m.lower() for m in logs), logs)
        # the other ordering: the dead CLI's own scope counts a kill, the older one is clear
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.OLDER: self.EVENTS(0), self.UNIT: self.EVENTS(1)})
        self.assertIn(self.UNIT, self._died_line(logs))
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        # and only the older one loaded (the dead CLI's collected): the exact unit reads not-found, no verdict
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), events={self.OLDER: self.EVENTS(1)})
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])

    def test_a_show_that_exits_non_zero_is_a_plain_line_and_the_bare_notice(self):
        # the user bus away: systemctl exits 1 with nothing on stdout and the reason on stderr; the heal runs,
        # the line says so (first stderr line only) and is no problem (it decides a wording, not the heal)
        d = tempfile.mkdtemp()
        be = _backend(d)
        seq = be.problem_seq()
        calls, logs = self._heal_with_show(d, be, "", returncode=1, stderr="Failed to connect to bus: No such file or directory\nmore\n",
                                           events={self.UNIT: self.EVENTS(1)})
        self.assertEqual(len(calls), 1)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE], "the heal ran all the same")
        line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(line), 1, logs)
        self.assertIn("exited 1", line[0])
        self.assertIn("Failed to connect to bus", line[0])
        self.assertIn(self.UNIT, line[0])
        self.assertNotIn("more", line[0])
        self.assertEqual(be.problems(), [])
        self.assertEqual(be.problem_seq(), seq)

    def test_a_show_that_raises_is_a_plain_line_too(self):
        for exc in (OSError("no systemctl"), subprocess.TimeoutExpired(["systemctl"], 10)):
            d = tempfile.mkdtemp()
            be = _backend(d)
            calls, logs = self._heal_with_show(d, be, raise_=exc, events={self.UNIT: self.EVENTS(1)})
            self.assertEqual(len(calls), 1)
            self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE], "the heal ran all the same")
            self.assertTrue(any("session scope result" in m and "did not answer" in m and str(exc) in m for m in logs), logs)
            self.assertEqual(be.problems(), [], "logged inside the except block, and still plain")

    def test_an_unreadable_memory_events_is_a_plain_line_and_the_bare_notice(self):
        # the unit is loaded but its memory.events cannot be read (no file under the cgroup root; a ControlGroup
        # the show did not fill in): the line says so, plain, and with Result=success nothing names an OOM kill
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={})
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(line), 1, logs)
        self.assertIn("memory.events of %s could not be read" % self.UNIT, line[0])
        self.assertIn("only systemd's Result can say", line[0])
        self.assertEqual(be.problems(), [])
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(cgroup=""), events={self.UNIT: self.EVENTS(1)})
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertTrue(any("shows no ControlGroup" in m for m in logs), logs)
        # a memory.events without the counter's line is unreadable too
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: "low 0\nhigh 0\n"})
        self.assertTrue(any("no oom_kill line" in m for m in logs), logs)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])

    def test_the_pure_readers(self):
        self.assertEqual(sb.scope_show_props(self._show(result="oom-kill")),
                         {"Result": "oom-kill", "ControlGroup": "/fx.slice/" + self.UNIT, "Id": self.UNIT, "LoadState": "loaded"})
        self.assertEqual(sb.scope_show_props(""), {})
        self.assertEqual(sb.scope_show_props("Id=x.scope\nnoequals\n"), {"Id": "x.scope"})
        self.assertEqual(sb.oom_kill_count(self.EVENTS(3)), 3)
        self.assertEqual(sb.oom_kill_count(self.EVENTS(0)), 0)
        self.assertIsNone(sb.oom_kill_count("low 0\noom 1\n"), "no oom_kill line: no count (oom is a different counter)")
        self.assertIsNone(sb.oom_kill_count(""))
        self.assertIsNone(sb.oom_kill_count("oom_kill x\n"))
        self.assertEqual(sb.oom_verdict({"Result": "success"}, 2), "memory.events oom_kill=2, Result=success")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, 1), "memory.events oom_kill=1, Result=oom-kill")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, None), "Result=oom-kill", "the second signal alone")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, 0), "Result=oom-kill")
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, 0))
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, None))
        self.assertIsNone(sb.oom_verdict({}, None))
        cg = "0::/user.slice/user-1000.slice/user@1000.service/app.slice/%s\n"
        self.assertEqual(sb.own_scope_unit(cg % self.UNIT, 4242, self.SID), self.UNIT)
        self.assertIsNone(sb.own_scope_unit(cg % self.OLDER, 4242, self.SID), "a scope the CLI merely inherited (another pid's)")
        self.assertIsNone(sb.own_scope_unit(cg % "romp-session-22222222-4242-1700000000000000000.scope", 4242, self.SID), "another sid's")
        self.assertIsNone(sb.own_scope_unit("0::/user.slice/user-1000.slice/user@1000.service/app.slice/romp-manager.service\n", 4242, self.SID))
        self.assertIsNone(sb.own_scope_unit("", 4242, self.SID))
        legacy = "12:memory:/user.slice/%s\n1:name=systemd:/user.slice/%s\n" % (self.UNIT, self.UNIT)
        self.assertEqual(sb.own_scope_unit(legacy, 4242, self.SID), self.UNIT, "the legacy hierarchy's per-controller lines")

    def test_the_cli_scope_is_recorded_at_connect_from_its_own_cgroup(self):
        # the record is made while the CLI is alive (its pid from the SDK transport), so the heal has the exact
        # unit after the pid is gone; only a scope this CLI started counts, and a transport without the pid is
        # a plain line, never a raise into the connect
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope = True
        logs = []
        be._log_cb = logs.append
        s = sb.SdkSession(be, _reg(d, self.SID))
        client = mock.Mock()
        client._transport._process.pid = 4242
        cg = "0::/user.slice/user-1000.slice/user@1000.service/app.slice/%s\n"
        reads = []

        def cgroup(pid):
            reads.append(pid)
            return cg % self.UNIT
        s._record_cli_scope(client, cgroup=cgroup)
        self.assertEqual((s.cli_scope_unit, reads), (self.UNIT, [4242]))
        s._record_cli_scope(client, cgroup=lambda pid: cg % self.OLDER)   # inherited: another pid's scope
        self.assertIsNone(s.cli_scope_unit)
        s._record_cli_scope(client, cgroup=lambda pid: "")                 # no scope at all (a fallback launch)
        self.assertIsNone(s.cli_scope_unit)
        s._record_cli_scope(client, cgroup=lambda pid: cg % self.UNIT)
        self.assertEqual(s.cli_scope_unit, self.UNIT)
        s._record_cli_scope(object(), cgroup=cgroup)                       # a transport without the attribute
        self.assertIsNone(s.cli_scope_unit, "a fresh connect never keeps the previous CLI's unit")
        self.assertTrue(any("scope could not be recorded at connect" in m for m in logs), logs)
        self.assertEqual(be.problems(), [])
        be.cli_scope = False
        reads.clear()
        s._record_cli_scope(client, cgroup=cgroup)
        self.assertEqual((s.cli_scope_unit, reads), (None, []), "the scopes off: nothing read, nothing recorded")
        self.assertIsNone(sb.SdkSession(be, _reg(d, self.SID)).cli_scope_unit, "None until a connect records one")

    def test_with_the_scopes_off_nothing_is_asked(self):
        # no scope was started for the CLI (the test floor, macOS, ROMP_CLI_SCOPE=0): no systemctl at all, even
        # with a unit on the session
        d = tempfile.mkdtemp()
        be = _backend(d)
        self.assertFalse(be.cli_scope)
        calls = []
        with mock.patch.object(sb.subprocess, "run", lambda argv, **kw: calls.append(list(argv))), \
             mock.patch.object(be, "_ensure"):
            be._on_session_gone(self._dead_session(be, d))
        self.assertEqual([c for c in calls if c[:1] == ["systemctl"]], [])
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])

    def test_the_oom_form_replaces_a_bare_notice_already_queued_and_is_not_stacked(self):
        # a crash loop's second heal is refused above; here a bare notice is in the queue from before (a
        # previous cut this kernel life, its turn completed since) and the new heal re-heads with one notice
        d = tempfile.mkdtemp()
        be = _backend(d)
        _reg(d, self.SID, queue=[sb.CRASH_RESUME_NUDGE, "a reply the person typed"])
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(1)})
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM, "a reply the person typed"])

    def test_the_two_forms_share_the_lead_and_the_bare_one_is_unchanged(self):
        # CRASH_RESUME_NUDGE is what every existing reader matched on: its text is the same to the byte
        self.assertEqual(sb.CRASH_RESUME_NUDGE,
                         "<!-- romp-injected --><!-- romp-system -->[romp] This session's claude process died mid-turn "
                         "(killed or crashed); the session has been resumed with its history intact. If the conversation "
                         "tail shows '[Request interrupted by user]', that record came from this cut, not from the user: "
                         "nobody asked you to stop. Re-read the tail of the conversation and pick the work back up where "
                         "it stopped, without asking whether to continue.")
        lead = "<!-- romp-injected --><!-- romp-system -->[romp] This session's claude process died mid-turn"
        for text in (sb.CRASH_RESUME_NUDGE, sb.CRASH_RESUME_NUDGE_OOM):
            self.assertTrue(text.startswith(lead))
            self.assertTrue(sb.is_crash_resume_nudge(text) and sb.is_resume_nudge(text))
            self.assertIn("nobody asked you to stop", text)
        self.assertFalse(sb.is_crash_resume_nudge(sb.BOOT_RESUME_NUDGE))
        self.assertFalse(sb.is_crash_resume_nudge(lead[:-5] + "different"))
        self.assertFalse(sb.is_crash_resume_nudge(None))
        # the OOM form speaks as the person: the cause in plain words, no tracking vocabulary
        for word in ("card", "board", "goal", "nudge", "scope", "cgroup", "systemd", "unit"):
            self.assertNotIn(word, sb.CRASH_RESUME_NUDGE_OOM.split("[romp]", 1)[1].lower(), word)

    def test_user_interrupted_death_still_settles_waiting(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        s = self._dead_session(be, d, inflight=1, interrupted=True)
        with mock.patch.object(be, "_ensure") as ens:
            be._on_session_gone(s)
        self.assertEqual(sb.last_state_value(Path(d), self.SID), "waiting",
                         "a user-interrupted turn's death is not a cut — settle as before")
        ens.assert_not_called()

    def test_idle_death_still_settles_waiting(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        s = self._dead_session(be, d, inflight=0)
        with mock.patch.object(be, "_ensure") as ens:
            be._on_session_gone(s)
        self.assertEqual(sb.last_state_value(Path(d), self.SID), "waiting")
        ens.assert_not_called()


class Drain(unittest.TestCase):
    def test_drain_stops_sessions_and_writes_no_state(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        sid = "11111111-aaaa-0000-0000-00000000000d"
        reg = _reg(d, sid)
        sb.append_state(Path(d), sid, "working")     # an in-flight turn's stamp
        s = sb.SdkSession(be, reg)
        s.inflight = 1
        s.thread = threading.Thread(target=lambda: time.sleep(0.01), daemon=True)
        s.thread.start()
        be.sessions[sid] = s
        r = be.drain(1.0)
        self.assertEqual((r["stopped"], r["inflight"]), (1, 1))
        self.assertEqual(r["cutTurns"], [{"sid": sid, "name": reg.get("name", sid)}],
                         "the drain names what it cuts — the restart-cut ledger's rows (T121)")
        self.assertTrue(s.ended, "shutdown was requested on the session")
        self.assertEqual(sb.last_state_value(Path(d), sid), "working",
                         "drain writes no idle/waiting — the trailing 'working' IS the boot "
                         "reconcile's resume marker")

    def test_drain_counts_mid_shutdown_cuts_and_survives_threadless_sessions(self):
        # T143's two ledger undercounts, executed: an `ended` session with a live in-flight turn IS
        # a cut (10 transcript-verified cuts vs 7 rows — the old filter dropped mid-shutdown ones),
        # and a constructed-but-never-started session (thread None) crashed the WHOLE drain
        # recordless on 2 of 18 restarts.
        d = tempfile.mkdtemp()
        be = _backend(d)
        s1 = sb.SdkSession(be, _reg(d, "11111111-aaaa-0000-0000-0000000000c1"))
        s1.inflight = 1
        s1.ended = True                                   # mid-shutdown, turn still live
        s1.thread = threading.Thread(target=lambda: None, daemon=True)
        s1.thread.start()
        s2 = sb.SdkSession(be, _reg(d, "11111111-aaaa-0000-0000-0000000000c2"))
        s2.inflight = 1                                   # constructed, never started: thread is None
        s2.thread = None
        be.sessions[s1.sid] = s1
        be.sessions[s2.sid] = s2
        r = be.drain(0.2)
        cut_sids = sorted(c["sid"] for c in r["cutTurns"])
        self.assertEqual(cut_sids, [s1.sid, s2.sid],
                         "both cuts recorded — ended included, threadless included, no crash")

    def test_drain_with_nothing_running_is_a_quiet_noop(self):
        be = _backend()
        self.assertEqual(be.drain(0.1), {"stopped": 0, "inflight": 0, "unjoined": 0, "reaped": 0,
                                         "cutTurns": []})

    def test_drain_reaps_the_cli_of_a_session_that_wont_close(self):
        # The 2026-07-25 twin incident: the drain's bound expired on a busy session ("still
        # closing: ..."), the kernel exited, and the orphaned CLI kept executing its turn for over
        # an hour while the next boot resumed the same conversation into a second process. The
        # drain must never exit leaving a live child: SIGTERM the unjoined session's CLI (then
        # SIGKILL if it lingers).
        d = tempfile.mkdtemp()
        be = _backend(d)
        sid = "11111111-aaaa-0000-0000-00000000000e"
        s = sb.SdkSession(be, _reg(d, sid))
        s.inflight = 1
        s.thread = threading.Thread(target=lambda: time.sleep(5), daemon=True)
        s.thread.start()                                  # outlives the drain bound → unjoined
        be.sessions[sid] = s
        be._session_cli_pid = lambda sess: 4242
        calls = []
        def fake_kill(pid, sig):
            calls.append((pid, sig))
            if sig == 0:
                raise ProcessLookupError                  # the TERM landed; existence poll sees it gone
        r = be.drain(0.1, kill=fake_kill)
        self.assertEqual((r["unjoined"], r["reaped"]), (1, 1))
        self.assertIn((4242, signal.SIGTERM), calls)
        self.assertNotIn((4242, signal.SIGKILL), calls, "a TERM that lands never escalates")

    def test_drain_sigkills_a_cli_that_ignores_term(self):
        d = tempfile.mkdtemp()
        be = _backend(d)
        sid = "11111111-aaaa-0000-0000-00000000000f"
        s = sb.SdkSession(be, _reg(d, sid))
        s.thread = threading.Thread(target=lambda: time.sleep(5), daemon=True)
        s.thread.start()
        be.sessions[sid] = s
        be._session_cli_pid = lambda sess: 4243
        calls = []
        def stubborn_kill(pid, sig):
            calls.append((pid, sig))                      # sig 0 never raises → still alive
        r = be.drain(0.1, kill=stubborn_kill)
        self.assertEqual(r["reaped"], 1)
        self.assertIn((4243, signal.SIGKILL), calls, "a wedged CLI still never outlives the kernel")


if __name__ == "__main__":
    unittest.main()

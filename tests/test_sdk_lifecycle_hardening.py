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
import asyncio
import contextlib
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

    def _dead_session(self, be, d, inflight=1, interrupted=False, unit="default", exit_code=None, baseline=None):
        reg = sb.read_reg(Path(d), self.SID) or _reg(d, self.SID)   # keep a prior heal's queue intact
        s = sb.SdkSession(be, reg)          # never started: pure object surface
        sb.append_state(Path(d), self.SID, "working")
        s.inflight = inflight
        s._interrupted = interrupted
        s.cli_scope_unit = self.UNIT if unit == "default" else unit   # what _record_cli_scope left at connect
        s._cli_exit_code = exit_code        # how the SDK reported the CLI ending (-9 is SIGKILL); the heal's primary signal
        s._oom_baseline = baseline          # the memory.events oom_kill count at the turn's start
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
        self.assertFalse(any("queued text(s) wait" in m for m in logs), "nothing but the nudge is queued: no parked-text clause (round 5)")
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

    # ── the cause, when the dead CLI's own scope still says (2026-09-10, rounds 2 and 3) ──────────────
    # Under OOMPolicy=continue systemd records NO Result on an OOM kill (one process dies, the scope
    # stands) and the whole-life memory.events `oom_kill` count cannot say WHICH death this was, so the
    # PRIMARY signal is the CLI's own exit (SdkSession._cli_exit_code): a SIGKILL (-9) is the OOM killer's
    # signature under `continue` (the cgroup killer and the kernel's global killer alike), and it survives
    # the scope's collection: a lone CLI IS the scope's last process, so the scope is gone the instant it
    # dies, taking the counter with it, but the exit is always read. The counter, when readable, is read
    # against the turn-start baseline (SdkSession._oom_baseline) and DECIDES what a SIGKILL was: risen,
    # the CLI's death out of memory; flat (on cgroup v2 the counter counts memcg and global kills alike),
    # a kill the kernel's killers did not make, named as a SIGKILL with no OOM kill counted (a kill by
    # hand, or earlyoom, which the counter cannot see) and never as out of memory (round 3); unreadable on
    # a LOADED unit, the SIGKILL stands alone. An increase WITHOUT a SIGKILL exit is a contained tool-child
    # kill the CLI outlived, named as a child and never as the CLI's cause, and only against a READ
    # baseline. Result=oom-kill is the second signal, for a scope WITHOUT the property, which systemd stops
    # whole; the Result leaves with the unit when every member dies on the SIGTERM, so for a collected unit
    # the heal reads the unit's journal tail, whatever the exit (rounds 3 and 4): the `Failed with result
    # 'oom-kill'` line names the whole-scope stop, and for a SIGKILL exit the manager's `A process of this
    # unit has been killed by the OOM killer` line, which survives the collection, tells the OOM killer
    # from a kill by hand (with it "oom", without it the hedged "sigkill"; an unreadable or empty journal
    # is "sigkill" too). The exit -1 is the SDK's own sentinel (a wait that failed, or SIGHUP) and reads as
    # unreported; 137 is a non-exec wrapper's report of a child's SIGKILL and reads as a plain exit.
    # The heal asks about the EXACT unit the CLI ran in (recorded from its /proc/<pid>/cgroup at connect,
    # SdkSession.cli_scope_unit), never a glob over the session's scopes: an older scope of the same
    # session, kept up by a tmux server and still draining an OOM kill of its own, would answer a glob.
    # Every read path logs one plain 'session scope result' line saying what was read and what was not,
    # and the reason a counter could not be read is the heal's to state (oom_verdict's counter_note).
    # The fake systemctl is table-driven (returncode, stdout, stderr) and records argv AND kwargs; it
    # answers BYTES when `text` is not asked for, as the real one would, so dropping text=True reproduces
    # the real failure. The fake journalctl answers `journal` (text, a returncode or a raise) the same way.
    UNIT = "romp-session-11111111-4242-1700000000000000000.scope"
    OLDER = "romp-session-11111111-4100-1600000000000000000.scope"   # an earlier CLI's scope, still up
    SHOW_ARGV = ["systemctl", "--user", "show", "--no-pager", "-p", "Id,LoadState,Result,ControlGroup", "--", UNIT]
    JOURNAL_ARGV = ["journalctl", "--user", "-n", "5", "-o", "cat", "-t", "systemd", "-u", UNIT]
    # the user manager's journal lines (systemd 255, verified on scratch scopes): for a scope systemd stopped
    # whole over an OOM kill (under OOMPolicy=stop) the Started line, the kill line and the stop line; for an
    # OOM kill under `continue` the Started line and the kill line only, whether the killed process was the
    # scope's last (the CLI, collected the same instant: the round-4 OOM cell) or a tool child the CLI outlived
    # (a contained kill, no verdict without a SIGKILL exit); for a kill by hand the Started line alone
    JOURNAL_OOM = ("Started %s - /usr/bin/claude.\n%s: A process of this unit has been killed by the OOM killer.\n"
                   "%s: Failed with result 'oom-kill'.\n" % (UNIT, UNIT, UNIT))
    JOURNAL_KILL = "Started %s - /usr/bin/claude.\n%s: A process of this unit has been killed by the OOM killer.\n" % (UNIT, UNIT)
    JOURNAL_STARTED = "Started %s - /usr/bin/claude.\n" % UNIT
    # round 5: systemd-oomd's kill leaves the manager's own line (verified on systemd 255 with the oomd xattrs set on a
    # scratch scope); and a user manager at LogLevel=warning keeps the stop line (LOG_WARNING) without the kill line
    # (LOG_NOTICE), so the stop line stands alone under `stop`
    JOURNAL_OOMD = "Started %s - /usr/bin/claude.\n%s: systemd-oomd killed 1 process(es) in this unit.\n" % (UNIT, UNIT)
    JOURNAL_STOP_ONLY = "Started %s - /usr/bin/claude.\n%s: Failed with result 'oom-kill'.\n" % (UNIT, UNIT)
    EVENTS = staticmethod(lambda n: "low 0\nhigh 0\nmax 37\noom %d\noom_kill %d\noom_group_kill 0\n" % (min(n, 1), n))
    KILL = -9   # SIGKILL_EXIT: the OOM killer's signature, the primary signal

    @classmethod
    def _show(cls, unit=None, result="success", load="loaded", cgroup="default"):
        """A `systemctl show -p Id,LoadState,Result,ControlGroup -- <unit>` answer (the order systemd prints)."""
        unit = unit or cls.UNIT
        cg = "/fx.slice/%s" % unit if cgroup == "default" else cgroup
        return "Result=%s\nControlGroup=%s\nId=%s\nLoadState=%s\n" % (result, cg, unit, load)

    def _heal_with_show(self, d, be, stdout=None, raise_=None, returncode=0, stderr="", events=None, unit="default",
                        exit_code=-9, baseline=None, journal=None, journal_raise=None, journal_returncode=0,
                        journal_stderr=""):
        """Run the heal with the scopes on, a fake systemctl, a fake journalctl and a fake cgroup root: the fake
        records every (argv, kwargs) and answers (returncode, stdout, stderr), or raises; `events` maps a unit
        to the memory.events text under its /fx.slice/<unit> cgroup (no entry: no file). `exit_code`/`baseline`
        are what the SDK reported and the turn-start counter (a SIGKILL exit -9 by default, since these
        cases are testing what the SCOPE read adds on top of the primary signal). A journalctl argv answers
        `journal` (its stdout; empty by default), or raises `journal_raise`, or exits `journal_returncode` with
        `journal_stderr`. Returns (calls, log)."""
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
            if list(argv[:1]) == ["journalctl"]:
                if journal_raise is not None:
                    raise journal_raise
                out, err = journal or "", journal_stderr or ""
                if "text" not in kw:
                    out, err = out.encode(), err.encode()
                return mock.Mock(returncode=journal_returncode, stdout=out, stderr=err)
            if raise_ is not None:
                raise raise_
            out, err = stdout or "", stderr or ""
            if "text" not in kw:
                out, err = out.encode(), err.encode()
            return mock.Mock(returncode=returncode, stdout=out, stderr=err)
        with mock.patch.object(sb.subprocess, "run", fake_run), mock.patch.object(sb, "CGROUP_ROOT", root), \
             mock.patch.object(be, "_ensure") as ens:
            be._on_session_gone(self._dead_session(be, d, unit=unit, exit_code=exit_code, baseline=baseline))
        ens.assert_called_once_with(self.SID)
        return calls, logs

    def _died_line(self, logs):
        line = [m for m in logs if "died mid-turn" in m]
        self.assertEqual(len(line), 1, logs)
        return line[0]

    def test_a_sigkill_exit_names_the_death_out_of_memory_the_counter_corroborating(self):
        # the primary signal: the CLI's own exit by SIGKILL (-9), the OOM killer's signature under
        # OOMPolicy=continue; the counter, read against the turn-start baseline, corroborates and is stated
        # (verified on systemd 255: a CLI over MemoryMax exited -9, oom_kill 1, Result=success)
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(1)}, exit_code=self.KILL, baseline=0)
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV], "one show, the dead CLI's exact unit, no glob")
        line = self._died_line(logs)
        self.assertIn("the OOM killer took a process in its scope %s (the CLI was killed by signal 9; "
                      "memory.events oom_kill=1 (was 0 at the turn's start), Result=success)" % self.UNIT, line)
        self.assertIn("resuming with history intact", line)
        q = sb.read_reg(Path(d), self.SID).get("queue")
        self.assertEqual(q, [sb.CRASH_RESUME_NUDGE_OOM], "the out-of-memory form of the notice, not the bare one")
        self.assertIn("out of memory", q[0])
        self.assertIn("OOM killer", q[0])
        self.assertTrue(sb.is_resume_nudge(q[0]), "readers that hide or re-head the resume nudge match this form too")
        self.assertTrue(sb.is_crash_resume_nudge(q[0]))
        self.assertEqual(sb.last_state_value(Path(d), self.SID), "working", "the cut marker stands as before")
        self.assertEqual(be.problems(), [], "naming a cause is no problem")
        # the always-log rule: one plain line saying what was read
        scope_line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(scope_line), 1, logs)
        self.assertIn("the CLI was killed by signal 9", scope_line[0])
        self.assertIn("oom_kill was 0 at the turn's start", scope_line[0])
        self.assertIn("memory.events oom_kill=1, Result=success", scope_line[0])

    def test_a_sigkill_exit_with_the_scope_already_collected_is_decided_by_the_journal(self):
        # the COMMON shape: a lone CLI IS the scope's last process, so the scope is collected the instant it
        # dies and the counter is gone (LoadState=not-found). The SIGKILL exit alone cannot tell the OOM
        # killer from a kill by hand, so the journal decides (round 4, regression-1): the user manager's
        # `<unit>: A process of this unit has been killed by the OOM killer.` line is written before the unit
        # is collected and survives it (verified on scratch scopes: every lone process OOM-killed under
        # `continue` left it; every kill -9 left the Started line alone), so with it the death is out of
        # memory and the OOM notice; without it a kill the counter and the journal cannot see, the hedged
        # notice. The read is bounded and in text mode like the show, and the plain line says what it found
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=self.KILL, baseline=0,
                                           journal=self.JOURNAL_KILL)
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV, self.JOURNAL_ARGV], "the show, then the journal")
        self.assertEqual(calls[1][1].get("timeout"), sb.SCOPE_SHOW_TIMEOUT)
        self.assertIs(calls[1][1].get("text"), True)
        line = self._died_line(logs)
        self.assertIn("the OOM killer took a process in its scope %s (the CLI was killed by signal 9; the scope was "
                      "already collected, so its counter could not be read (oom_kill was 0 at the turn's start); the journal "
                      "records an OOM kill in its scope (A process of this unit has been killed by the OOM killer))" % self.UNIT, line)
        self.assertNotIn("memory limit", line, "no limit is in force on this backend, so none is named (round 3: the "
                                              "'most likely the memory limit' guess is gone)")
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        scope_line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(scope_line), 1, logs)
        self.assertIn("the scope was already collected (LoadState=not-found), so the live counter could not be read; "
                      "the journal records an OOM kill in the scope (A process of this unit has been killed by the OOM killer)",
                      scope_line[0])
        self.assertEqual(be.problems(), [], "the read is no problem, and never silent")
        # the whole-scope stop line (a scope without the policy, stopped whole) names it too
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=self.KILL, baseline=0,
                                           journal=self.JOURNAL_OOM)
        self.assertIn("the journal records an OOM kill in its scope (Failed with result 'oom-kill'))", self._died_line(logs))
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        # round 5 (rules-2): the stop line ALONE files oom too (a user manager at LogLevel=warning drops the kill line)
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=self.KILL, baseline=0,
                                           journal=self.JOURNAL_STOP_ONLY)
        self.assertIn("the journal records an OOM kill in its scope (Failed with result 'oom-kill'))", self._died_line(logs))
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        # round 5 (correctness-4, D4): systemd-oomd's kill is the third kill line, a definite record: "oom", the evidence
        # naming systemd-oomd with the count the manager wrote, in the died line and in the plain line
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=self.KILL, baseline=0,
                                           journal=self.JOURNAL_OOMD)
        line = self._died_line(logs)
        self.assertIn("the OOM killer took a process in its scope %s (the CLI was killed by signal 9; the scope was already "
                      "collected, so its counter could not be read (oom_kill was 0 at the turn's start); the journal records an OOM "
                      "kill in its scope (systemd-oomd killed 1 process(es) in this unit))" % self.UNIT, line)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        scope_line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(scope_line), 1, logs)
        self.assertIn("; the journal records an OOM kill in the scope (systemd-oomd killed 1 process(es) in this unit)", scope_line[0])
        self.assertEqual(be.problems(), [])
        # the Started line alone (a kill -9 by hand, or earlyoom, which leaves no line), an empty journal, journalctl raising
        # and journalctl exiting non-zero: each is the hedged "sigkill" kind and the killed notice, never out of
        # memory (a definite verdict needs a definite record), with the journal's clause in both lines
        cases = (("Started only", dict(journal=self.JOURNAL_STARTED),
                  "its scope's journal records no OOM kill", "the journal's newest lines for the scope record no OOM kill"),
                 # round 5 (correctness-1): a journal with no line at all for the scope reads like a failed read, not like
                 # the Started-only silence: a manager that never logged the unit excludes nothing
                 ("empty", dict(journal=""), "no OOM kill is on record for its scope", "the journal has no line for the scope"),
                 ("raises", dict(journal_raise=subprocess.TimeoutExpired(["journalctl"], 10)),
                  "no OOM kill is on record for its scope", "journalctl did not answer ("),
                 ("exits 1", dict(journal_returncode=1, journal_stderr="No journal files were found.\nmore\n"),
                  "no OOM kill is on record for its scope",
                  "journalctl exited 1 (No journal files were found.)"))
        for label, kw, head, said in cases:
            with self.subTest(journal=label):
                d = tempfile.mkdtemp()
                be = _backend(d)
                calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=self.KILL, baseline=0, **kw)
                self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV, self.JOURNAL_ARGV])
                line = self._died_line(logs)
                self.assertIn("claude process died mid-turn; the CLI was killed by signal 9 and %s (a kill by hand, " % head, line)
                self.assertIn("; the scope was already collected, so its counter could not be read (oom_kill was 0 at the turn's "
                              "start); %s" % said, line)
                self.assertIn("(scope %s); resuming with history intact" % self.UNIT, line)
                self.assertNotIn("OOM killer took", line)
                self.assertNotIn("out of memory", line.lower())
                self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_KILLED])
                scope_line = [m for m in logs if "session scope result" in m]
                self.assertEqual(len(scope_line), 1, logs)
                self.assertIn("the scope was already collected (LoadState=not-found), so the live counter could not be read; " + said,
                              scope_line[0])
                self.assertEqual(be.problems(), [])
        # the newest life only: an earlier same-named unit's OOM death inside the -n window is cut off at the last
        # Started line, so this life's silence still reads as a kill the journal cannot see
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=self.KILL, baseline=0,
                                           journal=self.JOURNAL_KILL + self.JOURNAL_STARTED)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_KILLED])
        self.assertIn("records no OOM kill", self._died_line(logs))
        # with the memory controller known undelegated systemd records no OOM kill for any scope, so the
        # journal's silence excludes nothing: still the hedged kind, and the evidence says why the record is empty
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope_memory_delegated = False
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=self.KILL, baseline=0,
                                           journal=self.JOURNAL_STARTED)
        line = self._died_line(logs)
        self.assertIn("; the memory controller is not delegated to the user manager, so systemd records no OOM kill for a scope "
                      "and the journal's silence excludes none (scope %s)" % self.UNIT, line)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_KILLED])
        # and with it delegated (the stock verdict) the same silence carries no such clause
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope_memory_delegated = True
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=self.KILL, baseline=0,
                                           journal=self.JOURNAL_STARTED)
        self.assertNotIn("not delegated", self._died_line(logs))

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
        # systemd before 253) reads Result=oom-kill while its processes go down; the CLI exited on SIGTERM
        # (-15, systemd's stop signal), not SIGKILL, and Result=oom-kill stands alone
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="oom-kill"), events={self.UNIT: self.EVENTS(1)}, exit_code=-15)
        self.assertIn("systemd stopped the whole scope over an OOM kill (Result=oom-kill)", self._died_line(logs))
        self.assertIn("memory.events oom_kill=1", self._died_line(logs))
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        # with the counter unreadable, Result=oom-kill still names it, after a plain line about the counter
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="oom-kill"), events={}, exit_code=-15)
        self.assertIn("systemd stopped the whole scope over an OOM kill (Result=oom-kill)", self._died_line(logs))
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        self.assertTrue(any("session scope result" in m and "could not be read" in m for m in logs), logs)
        self.assertEqual(be.problems(), [])

    def test_a_contained_child_kill_the_cli_outlived_is_not_named_as_the_clis_death(self):
        # regression-2's defect: under continue a contained tool-child kill is the designed normal outcome,
        # so a NON-SIGKILL CLI exit with a counter increase over the baseline is a child, named as such and
        # NOT as the CLI's own out-of-memory death; the notice is bare
        for exit_code in (1, -6):   # exit 1 (the CLI's own), signal 6 (SIGABRT): neither is the killer
            d = tempfile.mkdtemp()
            be = _backend(d)
            calls, logs = self._heal_with_show(d, be, self._show(result="success"),
                                               events={self.UNIT: self.EVENTS(1)}, exit_code=exit_code, baseline=0)
            self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE],
                             "the bare notice: the CLI's own death was not out of memory")
            line = self._died_line(logs)
            self.assertIn("a tool child, not the CLI", line)
            self.assertNotIn("OOM killer took", line)
            self.assertEqual(be.problems(), [])

    def test_an_earlier_contained_kill_then_an_unrelated_crash_is_not_named_oom(self):
        # the baseline's job: a child OOM-killed in an EARLIER turn (baseline 1) that the session survived,
        # then an unrelated non-SIGKILL crash this turn with no NEW kill (count still 1) is no increase, so
        # nothing names it out of memory
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="success"), events={self.UNIT: self.EVENTS(1)},
                                           exit_code=1, baseline=1)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertNotIn("OOM killer took", self._died_line(logs))
        # a NEW kill this turn (count 2 over baseline 1) with a non-SIGKILL exit is a contained child, bare
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="success"), events={self.UNIT: self.EVENTS(2)},
                                           exit_code=1, baseline=1)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertIn("a tool child, not the CLI", self._died_line(logs))
        # but the SAME new kill with a SIGKILL exit IS the CLI's death out of memory
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="success"), events={self.UNIT: self.EVENTS(2)},
                                           exit_code=self.KILL, baseline=1)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        self.assertIn("(was 1 at the turn's start)", self._died_line(logs))

    def test_an_unreported_exit_leaves_the_count_as_context_not_a_verdict(self):
        # the SDK reported no exit code: the whole-life count is context in the plain line, never the cause,
        # and the notice is bare (correctness-2)
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="success"), events={self.UNIT: self.EVENTS(1)},
                                           exit_code=None, baseline=0)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertNotIn("OOM killer took", self._died_line(logs))
        scope_line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(scope_line), 1, logs)
        self.assertIn("the CLI's exit was not reported", scope_line[0])
        self.assertIn("memory.events oom_kill=1", scope_line[0])

    def test_a_scope_that_ended_otherwise_keeps_the_bare_notice(self):
        # a clean crash (exit 1, no counter increase, Result=success): no OOM verdict, the bare notice, and
        # one plain 'session scope result' line all the same (never silent)
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="success"), events={self.UNIT: self.EVENTS(0)},
                                           exit_code=1, baseline=0)
        self.assertEqual(len(calls), 1)
        line = self._died_line(logs)
        self.assertEqual(line, "session %s: claude process died mid-turn; resuming with history intact" % ("s-" + self.SID[:4]))
        self.assertNotIn("oom killer", line.lower())
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertTrue(any("session scope result" in m for m in logs), "the read is reported on every path")

    def test_a_unit_no_longer_loaded_with_a_clean_exit_reads_as_no_verdict(self):
        # the scope already collected AND the CLI exited cleanly (not by SIGKILL): for an EXACT unit systemctl
        # show still exits 0 and prints a block with LoadState=not-found and Result=success, which the read
        # drops; with no SIGKILL exit nothing names an OOM kill, and the plain line says the scope was collected
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=1)
        # round 3: the unit gone and the exit not SIGKILL, so the journal tail is read for a whole-scope stop the
        # unit no longer carries (bounded and in text mode like the show); empty here, so a plain clause
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV, self.JOURNAL_ARGV])
        self.assertEqual(calls[1][1].get("timeout"), sb.SCOPE_SHOW_TIMEOUT)
        self.assertIs(calls[1][1].get("text"), True)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertFalse(any("OOM killer took" in m for m in logs), logs)
        scope_line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(scope_line), 1, logs)
        self.assertIn("already collected", scope_line[0])
        self.assertIn("the journal has no line for the scope", scope_line[0])
        # an empty answer (nothing printed at all) is the same, with a clean exit: no verdict
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, "", exit_code=1)
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV, self.JOURNAL_ARGV])
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertFalse(any("OOM killer took" in m for m in logs), logs)

    def test_no_unit_recorded_asks_nothing(self):
        # the CLI ran in no scope of its own (a fallback launch; a scope it inherited; the record failed): no
        # systemctl, the bare notice, and no scope-result line (nothing to read)
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(1)}, unit=None, exit_code=self.KILL)
        self.assertEqual(calls, [])
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertFalse(any("OOM killer took" in m or "session scope result" in m for m in logs), logs)

    def test_an_older_scope_of_the_session_is_never_asked_about(self):
        # the older CLI's scope (kept up by a tmux server it started) is still draining an OOM kill of its own:
        # the dead CLI's scope is asked, never the older one, and a non-SIGKILL clean exit of the new CLI reads
        # bare whatever the older scope counted
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.OLDER: self.EVENTS(1), self.UNIT: self.EVENTS(0)},
                                           exit_code=1, baseline=0)
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV])
        self.assertNotIn(self.OLDER, str(calls))
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertFalse(any("OOM killer took" in m for m in logs), logs)
        # the dead CLI's own scope counts a NEW kill this turn and the CLI was SIGKILLed: its own death
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.OLDER: self.EVENTS(0), self.UNIT: self.EVENTS(1)},
                                           exit_code=self.KILL, baseline=0)
        self.assertIn(self.UNIT, self._died_line(logs))
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        # and only the older one loaded (the dead CLI's collected) with a clean exit: not-found, no verdict
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), events={self.OLDER: self.EVENTS(1)},
                                           exit_code=1)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])

    def test_a_show_that_exits_non_zero_is_a_plain_line(self):
        # the user bus away: systemctl exits 1 with the reason on stderr; the line says so (first stderr line
        # only) and is no problem. With a clean CLI exit the notice is bare; a SIGKILL exit would still name
        # it from the exit alone (tested above), so this uses a clean exit to reach the bare path
        d = tempfile.mkdtemp()
        be = _backend(d)
        seq = be.problem_seq()
        calls, logs = self._heal_with_show(d, be, "", returncode=1, stderr="Failed to connect to bus: No such file or directory\nmore\n",
                                           events={self.UNIT: self.EVENTS(1)}, exit_code=1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE], "the heal ran all the same")
        line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(line), 1, logs)
        self.assertIn("exited 1", line[0])
        self.assertIn("Failed to connect to bus", line[0])
        self.assertNotIn("more", line[0])
        self.assertEqual(be.problems(), [])
        self.assertEqual(be.problem_seq(), seq)

    def test_a_show_that_raises_is_a_plain_line_too(self):
        for exc in (OSError("no systemctl"), subprocess.TimeoutExpired(["systemctl"], 10)):
            d = tempfile.mkdtemp()
            be = _backend(d)
            calls, logs = self._heal_with_show(d, be, raise_=exc, events={self.UNIT: self.EVENTS(1)}, exit_code=1)
            self.assertEqual(len(calls), 1)
            self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE], "the heal ran all the same")
            self.assertTrue(any("session scope result" in m and "did not answer" in m and str(exc) in m for m in logs), logs)
            self.assertEqual(be.problems(), [], "logged inside the except block, and still plain")

    def test_an_unreadable_memory_events_is_a_plain_line(self):
        # the unit is loaded but its memory.events cannot be read (no file under the cgroup root; a ControlGroup
        # the show did not fill in): the line says so, plain, and with a clean exit and Result=success nothing
        # names an OOM kill
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={}, exit_code=1)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(line), 1, logs)
        self.assertIn("memory.events could not be read", line[0])
        self.assertIn("only systemd's Result can say", line[0])
        self.assertEqual(be.problems(), [])
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(cgroup=""), events={self.UNIT: self.EVENTS(1)}, exit_code=1)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertTrue(any("shows no ControlGroup" in m for m in logs), logs)
        # a memory.events without the counter's line is unreadable too
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: "low 0\nhigh 0\n"}, exit_code=1)
        self.assertTrue(any("no oom_kill line" in m for m in logs), logs)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        # round 3 (correctness-1, regression-2): with a SIGKILL exit the same three shapes still name the death
        # by the exit, but the died line says the counter could not be read on a LOADED unit, with the reason,
        # never that the scope was collected (that wording is the not-found show's alone); no journal read
        for shape, show, events, reason in (("no file", self._show(), {}, "No such file or directory"),
                                            ("no ControlGroup", self._show(cgroup=""), {self.UNIT: self.EVENTS(1)},
                                             "the unit shows no ControlGroup"),
                                            ("no oom_kill line", self._show(), {self.UNIT: "low 0\nhigh 0\n"}, "no oom_kill line in")):
            with self.subTest(shape=shape):
                d = tempfile.mkdtemp()
                be = _backend(d)
                calls, logs = self._heal_with_show(d, be, show, events=events, exit_code=self.KILL, baseline=0)
                self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV], "a loaded unit: no journal read")
                line = self._died_line(logs)
                self.assertIn("the OOM killer took a process in its scope %s (the CLI was killed by signal 9; its scope's "
                              "counter could not be read (" % self.UNIT, line)
                self.assertIn(reason, line)
                self.assertIn(") (oom_kill was 0 at the turn's start), Result=success)", line,
                              "the loaded unit's Result, which the show read, is stated (round 4, correctness-2)")
                self.assertNotIn("already collected", line)
                self.assertNotIn("memory limit", line)
                self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
                self.assertEqual(be.problems(), [])
        # round 4 (correctness-2): a SIGKILL exit on a loaded unit whose counter could not be read still states a
        # Result=oom-kill the show DID read, in the died line and in the plain line (no journal: the unit is loaded)
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(result="oom-kill"), events={}, exit_code=self.KILL, baseline=0)
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV])
        line = self._died_line(logs)
        self.assertIn("the OOM killer took a process in its scope %s (the CLI was killed by signal 9; its scope's counter could "
                      "not be read (" % self.UNIT, line)
        self.assertIn(") (oom_kill was 0 at the turn's start), Result=oom-kill)", line)
        scope_line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(scope_line), 1, logs)
        self.assertIn("memory.events could not be read (", scope_line[0])
        self.assertIn("; only systemd's Result can say (Result=oom-kill)", scope_line[0])
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])

    def test_a_show_that_fails_with_a_sigkill_exit_says_so_never_that_the_scope_was_collected(self):
        # round 3 (correctness-1, regression-2): systemctl exiting non-zero or raising leaves props {} exactly as
        # a not-found show does, and the died line used to say the scope was collected beside a scope line that
        # named the real failure; it now says the show did not answer, the SIGKILL still names the death, and
        # no journal is read (the show itself failed, so the unit's state is unknown)
        for label, kw in (("exits 1", dict(stdout="", returncode=1, stderr="Failed to connect to bus: No such file or directory\n")),
                          ("raises", dict(raise_=OSError("no systemctl")))):
            with self.subTest(show=label):
                d = tempfile.mkdtemp()
                be = _backend(d)
                calls, logs = self._heal_with_show(d, be, events={self.UNIT: self.EVENTS(1)}, exit_code=self.KILL, baseline=0, **kw)
                self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV])
                line = self._died_line(logs)
                self.assertIn("the OOM killer took a process in its scope %s (the CLI was killed by signal 9; systemctl show did "
                              "not answer (" % self.UNIT, line)
                self.assertNotIn("already collected", line)
                self.assertIn("Failed to connect to bus" if label == "exits 1" else "no systemctl", line)
                self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
                self.assertEqual(be.problems(), [])

    def test_the_crash_loop_refusal_reads_the_evidence_first_and_names_the_cause(self):
        # kernel-1: a session OOM-killed twice in a row must still have its cause named in the log, so the
        # scope read is hoisted above the crash-loop refusal; the refused second heal does not stack a nudge
        d = tempfile.mkdtemp()
        be = _backend(d)
        be._heal_attempts[self.SID] = 1     # a heal already ran this cut and its turn never completed
        logs = []
        be._log_cb = logs.append
        be.cli_scope = True
        root = tempfile.mkdtemp()
        Path(root, "fx.slice", self.UNIT).mkdir(parents=True)
        Path(root, "fx.slice", self.UNIT, "memory.events").write_text(self.EVENTS(1))
        calls = []

        def fake_run(argv, **kw):
            calls.append(list(argv))
            return mock.Mock(returncode=0, stdout=self._show(), stderr="")
        with mock.patch.object(sb.subprocess, "run", fake_run), mock.patch.object(sb, "CGROUP_ROOT", root), \
             mock.patch.object(be, "_ensure") as ens:
            be._on_session_gone(self._dead_session(be, d, exit_code=self.KILL, baseline=0))
        self.assertEqual(calls, [self.SHOW_ARGV], "the scope was read even though the heal is refused")
        self.assertEqual(ens.call_count, 0, "no resume: the crash loop stands")
        loop_line = [m for m in logs if "crash loop" in m]
        self.assertEqual(len(loop_line), 1, logs)
        self.assertIn("the OOM killer took a process in its scope %s (the CLI was killed by signal 9" % self.UNIT, loop_line[0])
        self.assertNotIn("\u2014", loop_line[0], "the crash-loop line has no em dash")

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
        # oom_verdict(props, oom_kill, exit_code, baseline) -> (kind, evidence) or None
        K = sb.SIGKILL_EXIT
        self.assertEqual(K, -9)
        kind, ev = sb.oom_verdict({"Result": "success"}, 2, K, 0)
        self.assertEqual(kind, "oom")
        self.assertIn("killed by signal 9", ev)
        self.assertIn("memory.events oom_kill=2 (was 0 at the turn's start), Result=success", ev)
        self.assertEqual(sb.oom_verdict({"Result": "success"}, None, K)[0], "oom", "SIGKILL alone: a loaded unit, no counter, no journal")
        self.assertEqual(sb.oom_verdict({"Result": "success"}, None, K)[1],
                         "the CLI was killed by signal 9; its counter could not be read, Result=success",
                         "pure and limits-blind (round 3): no guess about a memory limit, a plain note when the caller gave none; "
                         "the loaded unit's Result, read, is stated (round 4, correctness-2)")
        self.assertEqual(sb.oom_verdict({}, None, K, 0, counter_note="the scope was already collected, so its counter could not be read"),
                         ("oom", "the CLI was killed by signal 9; the scope was already collected, so its counter could not be read "
                                 "(oom_kill was 0 at the turn's start)"), "the caller's reason rides the evidence (no journal read: a failed show)")
        # round 4 (regression-1, kernel-1): the SIGKILL + collected cell is decided by the journal's newest life:
        # the manager's kill line or the stop line is "oom"; a read journal without either, an empty one, and a
        # read that failed (journal None with the caller's note) are "sigkill" with the journal named
        note = "the scope was already collected, so its counter could not be read"
        kind, ev = sb.oom_verdict({}, None, K, 0, counter_note=note, journal=self.JOURNAL_KILL, journal_note="the journal records an OOM kill")
        self.assertEqual((kind, ev), ("oom", "the CLI was killed by signal 9; %s (oom_kill was 0 at the turn's start); the journal "
                                             "records an OOM kill in its scope (A process of this unit has been killed by the OOM killer)" % note))
        self.assertEqual(sb.oom_verdict({}, None, K, 0, counter_note=note, journal=self.JOURNAL_OOM)[1],
                         "the CLI was killed by signal 9; %s (oom_kill was 0 at the turn's start); the journal records an OOM kill in its "
                         "scope (Failed with result 'oom-kill')" % note, "the stop line is named over the kill line when both are there")
        kind, ev = sb.oom_verdict({}, None, K, 0, counter_note=note, journal=self.JOURNAL_STARTED, journal_note="the journal says nothing")
        self.assertEqual(kind, "sigkill")
        self.assertEqual(ev, "the CLI was killed by signal 9 and its scope's journal records no OOM kill (a kill by hand, or a userspace "
                             "killer the cgroup counter and so the journal cannot see); %s (oom_kill was 0 at the turn's start); the journal "
                             "says nothing" % note)
        self.assertEqual(sb.oom_verdict({}, None, K, None, counter_note=note, journal="")[0], "sigkill", "an empty journal: no record")
        self.assertIn("; the journal's newest lines record no OOM kill", sb.oom_verdict({}, None, K, None, counter_note=note, journal="")[1],
                      "the plain fallback when the caller gave no note")
        kind, ev = sb.oom_verdict({}, None, K, 0, counter_note=note, journal=None, journal_note="journalctl exited 1 (no journal)")
        self.assertEqual(kind, "sigkill")
        self.assertEqual(ev, "the CLI was killed by signal 9 and no OOM kill is on record for its scope (a kill by hand, a userspace "
                             "killer, or the OOM killer with its record unread or missing); %s (oom_kill was 0 at the turn's start); "
                             "journalctl exited 1 (no journal)" % note)
        self.assertEqual(sb.oom_verdict({}, None, K, 0, counter_note=note)[0], "oom",
                         "no journal read and no note (a show that failed: the unit's state unknown): the exit stands alone")
        # journal_life cuts the window at the LAST Started line of the unit, so an earlier same-named unit's death
        # inside the window is not this life's; without a Started line every line counts; with a unit only lines
        # naming it count (the manager's `<unit>: ...` lines)
        self.assertTrue(sb.journal_oom_kill(self.JOURNAL_KILL))
        self.assertTrue(sb.journal_oom_kill(self.JOURNAL_KILL, self.UNIT))
        # round 5 (D4): systemd-oomd's line is a kill line too, and journal_oom_line names the deciding line for the evidence
        # (the stop line over the kill line, the oomd line as written past the unit's name, without its period)
        self.assertEqual(sb.SCOPE_JOURNAL_OOMD_LINE, "systemd-oomd killed")
        self.assertTrue(sb.journal_oom_kill(self.JOURNAL_OOMD))
        self.assertTrue(sb.journal_oom_kill(self.JOURNAL_OOMD, self.UNIT))
        self.assertFalse(sb.journal_oom_kill(self.JOURNAL_OOMD + self.JOURNAL_STARTED), "the oomd kill was the previous life's")
        self.assertEqual(sb.journal_oom_line(self.JOURNAL_OOMD, self.UNIT), "systemd-oomd killed 1 process(es) in this unit")
        self.assertEqual(sb.journal_oom_line(self.JOURNAL_OOMD), "systemd-oomd killed 1 process(es) in this unit")
        self.assertEqual(sb.journal_oom_line(self.JOURNAL_KILL, self.UNIT), sb.SCOPE_JOURNAL_KILL_LINE)
        self.assertEqual(sb.journal_oom_line(self.JOURNAL_OOM, self.UNIT), sb.SCOPE_JOURNAL_OOM_LINE, "the stop line over the kill line")
        self.assertEqual(sb.journal_oom_line(self.JOURNAL_STOP_ONLY, self.UNIT), sb.SCOPE_JOURNAL_OOM_LINE)
        self.assertIsNone(sb.journal_oom_line(self.JOURNAL_STARTED, self.UNIT))
        self.assertIsNone(sb.journal_oom_line("", None))
        self.assertIsNone(sb.journal_oom_line("%s: systemd-oomd killed some process(es) in this unit.\n" % self.OLDER, self.UNIT),
                          "another unit's oomd line, when the unit is given")
        kind, ev = sb.oom_verdict({}, None, K, 0, counter_note=note, journal=self.JOURNAL_OOMD, journal_note="the journal records an OOM kill")
        self.assertEqual((kind, ev), ("oom", "the CLI was killed by signal 9; %s (oom_kill was 0 at the turn's start); the journal "
                                             "records an OOM kill in its scope (systemd-oomd killed 1 process(es) in this unit)" % note))
        self.assertEqual(sb.oom_verdict({}, None, K, 0, counter_note=note, journal=self.JOURNAL_STOP_ONLY)[1],
                         "the CLI was killed by signal 9; %s (oom_kill was 0 at the turn's start); the journal records an OOM kill in its "
                         "scope (Failed with result 'oom-kill')" % note, "the stop line alone files oom (round 5, rules-2)")
        self.assertIsNone(sb.oom_verdict({}, None, 143, 0, journal=self.JOURNAL_OOMD),
                          "like the kernel killer's line, oomd's is whole-life: no verdict without a SIGKILL exit")
        self.assertFalse(sb.journal_oom_kill(self.JOURNAL_KILL + self.JOURNAL_STARTED), "the kill was the previous life's")
        self.assertFalse(sb.journal_oom_kill(self.JOURNAL_STARTED))
        self.assertFalse(sb.journal_oom_kill(""))
        self.assertTrue(sb.journal_oom_kill("%s: A process of this unit has been killed by the OOM killer.\n" % self.UNIT, self.UNIT),
                        "no Started line in the window: every line counts")
        self.assertFalse(sb.journal_oom_kill("%s: A process of this unit has been killed by the OOM killer.\n" % self.OLDER, self.UNIT),
                        "another unit's line, when the unit is given")
        self.assertFalse(sb.journal_oom_stop(self.JOURNAL_OOM + self.JOURNAL_STARTED), "the stop was the previous life's")
        self.assertEqual(sb.journal_life(self.JOURNAL_OOM, self.UNIT),
                         ["%s: A process of this unit has been killed by the OOM killer." % self.UNIT,
                          "%s: Failed with result 'oom-kill'." % self.UNIT])
        self.assertEqual(sb.journal_life(self.JOURNAL_STARTED, self.UNIT), [])
        self.assertEqual(sb.journal_life("", None), [])
        # round 5 (fresh-4, kernel-4): the cut is at ANY `Started ` line of the window, whatever the manager's
        # StatusUnitFormat= makes of the unit's name (`Started <unit>.` under name, `Started <description>.` under
        # description, upstream's compiled default), since -u <unit> -t systemd already restricts the window to the
        # manager's lines about this unit; a match on `Started <unit> ` was inert on both (verified on a scratch scope
        # whose description equalled its unit id)
        for started in ("Started %s.\n" % self.UNIT, "Started /usr/bin/claude.\n"):
            self.assertEqual(sb.journal_life("%s%s: A process of this unit has been killed by the OOM killer.\n%s"
                                             % (started, self.UNIT, started), self.UNIT), [],
                             "the kill was the previous life's: %r" % started)
            self.assertFalse(sb.journal_oom_kill(self.JOURNAL_KILL + started, self.UNIT), started)
        self.assertEqual(sb.SCOPE_JOURNAL_KILL_LINE, "A process of this unit has been killed by the OOM killer")
        self.assertEqual(sb.SCOPE_JOURNAL_STARTED, "Started ")
        # the loaded-unit cells the round-3 table names (round 4, rules-1): every cell has an assertion here
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, 2, K, 0)[0], "oom", "-9 rose under Result=oom-kill")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, None, K)[0], "oom", "-9 unreadable under Result=oom-kill")
        self.assertIn("Result=oom-kill", sb.oom_verdict({"Result": "oom-kill"}, None, K)[1],
                      "the Result the show DID read is stated (round 4, correctness-2)")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, 1, 1, 1)[0], "oom", "1 flat under Result=oom-kill")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, 2, 1, 1)[0], "oom", "1 rose under Result=oom-kill: the Result outranks the child")
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, 0, -1, 0), "-1 flat under Result=success")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, 0, -1, 0)[0], "oom", "-1 flat under Result=oom-kill")
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, None, -1), "-1 unreadable under Result=success")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, None, None)[0], "oom", "None unreadable under Result=oom-kill")
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, None, None), "None unreadable under Result=success")
        # a SIGKILL with a READABLE counter that did not rise over the baseline is a kill the kernel's killers did
        # not make (round 3): a kill by hand or a userspace killer, named as such and never as out of memory
        kind, ev = sb.oom_verdict({"Result": "success"}, 0, K, 0)
        self.assertEqual(kind, "sigkill")
        self.assertEqual(ev, "the CLI was killed by signal 9 with no OOM kill counted in its scope this turn (a kill by hand, or a "
                             "userspace killer the cgroup counter cannot see); memory.events oom_kill=0 (was 0 at the turn's start), "
                             "Result=success")
        self.assertEqual(sb.oom_verdict({"Result": "success"}, 0, K, None)[0], "sigkill", "a whole-life 0 with no baseline: nothing counted")
        self.assertIn("memory.events oom_kill=0, Result=success", sb.oom_verdict({"Result": "success"}, 0, K, None)[1])
        self.assertEqual(sb.oom_verdict({"Result": "success"}, 1, K, 1)[0], "sigkill", "an earlier turn's kill, none this turn")
        self.assertEqual(sb.oom_verdict({"Result": "success"}, 3, K, None)[0], "oom",
                         "a whole-life count above 0 with no baseline keeps oom: nothing says the counted kill was not this one")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, 0, K, 0)[0], "oom",
                         "systemd's own Result=oom-kill outranks a flat counter beside a SIGKILL")
        self.assertIn("(Result=oom-kill); the CLI was killed by signal 9; memory.events oom_kill=0 (was 0 at the turn's start)",
                      sb.oom_verdict({"Result": "oom-kill"}, 0, K, 0)[1])
        # Result=oom-kill, and the journal's record of the same whole-scope stop once the unit is gone (round 3)
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, 1, -15)[0], "oom", "Result=oom-kill stands alone")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, None, -15)[0], "oom")
        self.assertIn("(Result=oom-kill); the CLI was killed by signal 15", sb.oom_verdict({"Result": "oom-kill"}, None, -15)[1])
        self.assertEqual(sb.oom_verdict({}, None, 143, 0, journal=self.JOURNAL_OOM),
                         ("oom", "systemd stopped the whole scope over an OOM kill (journal: Failed with result 'oom-kill'); "
                                 "the CLI exited 143"))
        self.assertEqual(sb.oom_verdict({}, None, -15, 0, journal=self.JOURNAL_OOM)[0], "oom")
        self.assertEqual(sb.oom_verdict({}, None, None, None, journal=self.JOURNAL_OOM)[0], "oom", "the stop names it whatever the exit")
        self.assertIsNone(sb.oom_verdict({}, None, 143, 0, journal=self.JOURNAL_KILL),
                          "the whole-life 'killed by the OOM killer' line is no verdict without a SIGKILL exit (a contained kill logs it too)")
        self.assertIsNone(sb.oom_verdict({}, None, 143, 0, journal=""), "an empty journal")
        self.assertIsNone(sb.oom_verdict({}, None, 143, 0), "no journal read")
        self.assertTrue(sb.journal_oom_stop(self.JOURNAL_OOM))
        self.assertFalse(sb.journal_oom_stop(self.JOURNAL_KILL))
        self.assertFalse(sb.journal_oom_stop(""))
        self.assertEqual(sb.SCOPE_JOURNAL_OOM_LINE, "Failed with result 'oom-kill'")
        # a contained child kill: a counter increase over a READ baseline with a known non-SIGKILL exit
        self.assertEqual(sb.oom_verdict({"Result": "success"}, 2, 1, 1)[0], "contained", "a new kill, a non-SIGKILL exit: a child")
        self.assertIn("a tool child, not the CLI", sb.oom_verdict({"Result": "success"}, 2, 1, 1)[1])
        self.assertIn("while the CLI itself exited 1, so", sb.oom_verdict({"Result": "success"}, 2, 1, 1)[1])
        self.assertIn("while the CLI itself was killed by signal 6, so", sb.oom_verdict({"Result": "success"}, 2, -6, 1)[1])
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, 1, 1, 1), "no increase over the baseline")
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, 2, 1, None),
                          "no baseline: the whole-life count is context, not a child verdict (round 3)")
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, 1, None, 0), "no exit reported: the count is context")
        # -1 is the SDK's sentinel for an exit it could not read (or a SIGHUP): unreported, never a kill by
        # signal 1, and no child verdict from it, as for None (round 3)
        self.assertEqual(sb.SDK_EXIT_UNREPORTED, -1)
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, 1, -1, 0), "an unread exit files no child verdict")
        self.assertEqual(sb.oom_verdict({"Result": "oom-kill"}, 1, -1, 0)[0], "oom", "Result=oom-kill stands alone still")
        self.assertIn("(Result=oom-kill); the CLI ended on signal 1 (SIGHUP) or the SDK could not read its exit (it reports -1 for both)",
                      sb.oom_verdict({"Result": "oom-kill"}, 1, -1, 0)[1])
        self.assertEqual(sb.exit_said(-1), "the CLI ended on signal 1 (SIGHUP) or the SDK could not read its exit (it reports -1 for both)")
        self.assertEqual(sb.exit_said(-9), "the CLI was killed by signal 9")
        self.assertEqual(sb.exit_said(-15), "the CLI was killed by signal 15")
        self.assertEqual(sb.exit_said(137), "the CLI exited 137")
        self.assertEqual(sb.exit_said(0), "the CLI exited 0")
        self.assertEqual(sb.exit_said(None), "the CLI's exit was not reported")
        self.assertEqual(sb.exit_said(1, "the CLI itself"), "the CLI itself exited 1")
        self.assertEqual([sb.exit_known(c) for c in (None, -1, -9, 0, 1, 137)], [False, False, True, True, True, True])
        # 137 is a non-exec wrapper's report of a CHILD's SIGKILL, never the CLI's own (round 3): a plain exit,
        # a child kill with a counter increase, nothing with the scope collected
        self.assertEqual(sb.oom_verdict({"Result": "success"}, 1, 137, 0)[0], "contained")
        self.assertIn("while the CLI itself exited 137, so a tool child", sb.oom_verdict({"Result": "success"}, 1, 137, 0)[1])
        self.assertIsNone(sb.oom_verdict({}, None, 137, 0), "137 with the scope collected: no SIGKILL verdict")
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, 0, 137, 0))
        self.assertIsNone(sb.oom_verdict({"Result": "success"}, None, 1), "a clean exit, no counter")
        self.assertIsNone(sb.oom_verdict({}, None, None))
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
        self.assertEqual(s.cli_scope_cgroup, "/user.slice/user-1000.slice/user@1000.service/app.slice/" + self.UNIT,
                         "the v2 cgroup path is kept, so a turn-start baseline can read the live scope")
        # a fresh connect resets the recorded exit and baseline, so a heal keys on THIS CLI's life
        s._cli_exit_code = -9
        s._oom_baseline = 5
        s._record_cli_scope(client, cgroup=lambda pid: cg % self.OLDER)   # inherited: another pid's scope
        self.assertIsNone(s.cli_scope_unit)
        self.assertIsNone(s.cli_scope_cgroup)
        self.assertEqual((s._cli_exit_code, s._oom_baseline), (None, None), "a fresh connect clears the recorded status")
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

    def test_the_turn_start_baseline_reads_the_live_scopes_counter(self):
        # _snapshot_oom_baseline reads the LIVE scope's memory.events oom_kill from its v2 cgroup path (kept
        # at connect); an unreadable path leaves the baseline None and the heal uses the raw count
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope = True
        root = tempfile.mkdtemp()
        cgpath = "/user.slice/user@.service/app.slice/" + self.UNIT
        Path(root, cgpath.lstrip("/")).mkdir(parents=True)
        Path(root, cgpath.lstrip("/"), "memory.events").write_text(self.EVENTS(3))
        s = sb.SdkSession(be, _reg(d, self.SID))
        s.cli_scope_cgroup = cgpath
        with mock.patch.object(sb, "CGROUP_ROOT", root):
            s._snapshot_oom_baseline()
        self.assertEqual(s._oom_baseline, 3, "the counter at the turn's start")
        s.cli_scope_cgroup = "/user.slice/gone.scope"     # no such dir under the root
        with mock.patch.object(sb, "CGROUP_ROOT", root):
            s._snapshot_oom_baseline()
        self.assertIsNone(s._oom_baseline, "an unreadable scope leaves the baseline None")
        s.cli_scope_cgroup = None                          # no scope at all
        s._oom_baseline = 7
        s._snapshot_oom_baseline()
        self.assertIsNone(s._oom_baseline)

    def test_amain_records_the_cli_scope_at_connect(self):
        # the ONE line that wires the exact-unit record into the connect path (_record_cli_scope(client) in
        # _amain) has its own EXECUTING test: the REAL _amain runs against a stand-in SDK whose transport
        # carries a pid, and the record must land. Deleting the call, or reading the pid after the client is
        # torn down, leaves cli_scope_unit None. The record sits BEFORE `self.client = client` (the
        # opening-state pin keeps the handshake and the push adjacent), and needs only the client's pid.
        from types import SimpleNamespace
        from importlib.machinery import ModuleSpec
        UNIT = "romp-session-11111111-4242-1700000000000000000.scope"
        reads = []

        class _Client:
            def __init__(self, options=None, transport=None):
                self._transport = SimpleNamespace(_process=SimpleNamespace(pid=4242))
            async def __aenter__(self):
                return self
            async def __aexit__(self, *a):
                return False
            async def query(self, prompt, session_id="default"):
                async for _turn in prompt:
                    pass
            async def receive_messages(self):
                await asyncio.Event().wait()   # park: the connect is what this test observes, not a turn
                yield None
            async def get_context_usage(self):
                return {"percentage": 1, "model": "m"}
            async def get_server_info(self):
                return {}
            async def interrupt(self):
                pass

        class _Options:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)

        fake = types.ModuleType("claude_agent_sdk")
        fake.__spec__ = ModuleSpec("claude_agent_sdk", loader=None)
        fake.ClaudeSDKClient, fake.ClaudeAgentOptions, fake.HookMatcher = _Client, _Options, (lambda **kw: kw)
        fake.AssistantMessage = type("AssistantMessage", (), {})
        fake.ResultMessage = type("ResultMessage", (), {})
        fake.SystemMessage = type("SystemMessage", (), {})
        fake.TextBlock = type("TextBlock", (), {})
        saved = sys.modules.get("claude_agent_sdk")
        sys.modules["claude_agent_sdk"] = fake
        d = tempfile.mkdtemp()
        try:
            be = _backend(d)
            be.cli_scope = True     # set after construction, so the settle probe never spawns systemd-run
            reg = {"sid": self.SID, "name": "web", "mode": "acceptEdits", "alive": True, "cwd": d}
            sb.write_reg(Path(d), self.SID, reg)
            s = sb.SdkSession(be, dict(reg))

            def fake_cgroup(pid):
                reads.append(pid)
                return "0::/user.slice/user@.service/app.slice/%s\n" % UNIT
            with mock.patch.object(sb, "_read_cgroup", fake_cgroup):
                s.start()
                self.assertTrue(s._connected.wait(timeout=10), "the connect never landed")
                self.assertEqual(s.cli_scope_unit, UNIT, "the record ran at connect")
                self.assertEqual(reads, [4242], "the CLI's own pid, read from the transport")
            s.shutdown()
            if s.thread.ident is not None:
                s.thread.join(timeout=10)
        finally:
            if saved is None:
                sys.modules.pop("claude_agent_sdk", None)
            else:
                sys.modules["claude_agent_sdk"] = saved
            shutil.rmtree(d, ignore_errors=True)

    def test_a_sigkill_exit_with_a_flat_readable_counter_is_a_kill_the_counter_did_not_see(self):
        # round 3 (regression-1, tests-3, correctness-2): the counter was READ and did not rise over the turn's
        # baseline, which on cgroup v2 excludes the memcg killer and the kernel's global one alike, leaving a
        # kill by hand or a userspace killer (earlyoom) the counter cannot see. Naming that out of memory was
        # a quietly wrong notice: the kind is "sigkill", the log says what the evidence supports, and the
        # session reads a notice of its own that names the signal and asks for modest memory use, never the
        # out-of-memory form (verified on a scratch scope: kill -9 in a bystander-held scope left oom_kill 0,
        # Result=success; a memcg kill of the same shape left oom_kill 1)
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(0)}, exit_code=self.KILL, baseline=0)
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV])
        line = self._died_line(logs)
        self.assertIn("claude process died mid-turn; the CLI was killed by signal 9 with no OOM kill counted in its scope this "
                      "turn (a kill by hand, or a userspace killer the cgroup counter cannot see); memory.events oom_kill=0 "
                      "(was 0 at the turn's start), Result=success (scope %s); resuming with history intact" % self.UNIT, line)
        self.assertNotIn("OOM killer took", line)
        self.assertNotIn("out of memory", line.lower())
        q = sb.read_reg(Path(d), self.SID).get("queue")
        self.assertEqual(q, [sb.CRASH_RESUME_NUDGE_KILLED], "the third form of the notice: killed, no OOM kill counted")
        self.assertIn("killed by signal 9 partway through the last turn", q[0])
        self.assertIn("no out-of-memory kill is on record for it, which does not rule one out", q[0],
                      "round 5: the one text says what is on record and rules nothing out; the log line keeps the counter")
        self.assertIn("keep memory use modest for now", q[0])
        self.assertNotIn("out of memory:", q[0], "never the out-of-memory form's claim")
        self.assertTrue(sb.is_crash_resume_nudge(q[0]), "the readers that re-head or hide the crash notice match it")
        self.assertTrue(sb.is_resume_nudge(q[0]))
        self.assertEqual(sb.last_state_value(Path(d), self.SID), "working")
        self.assertEqual(be.problems(), [])
        scope_line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(scope_line), 1, logs)
        self.assertIn("the CLI was killed by signal 9; oom_kill was 0 at the turn's start; memory.events oom_kill=0, Result=success",
                      scope_line[0])
        # an earlier turn's kill the session survived (baseline 1, count still 1) is the same cell
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(1)}, exit_code=self.KILL, baseline=1)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_KILLED])
        self.assertIn("memory.events oom_kill=1 (was 1 at the turn's start)", self._died_line(logs))
        # and a whole-life 0 with no baseline (the connect-time read failed): still nothing counted
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(0)}, exit_code=self.KILL, baseline=None)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_KILLED])
        self.assertIn("no OOM kill counted in its scope this turn", self._died_line(logs))

    def test_the_crash_loop_refusal_names_a_kill_the_counter_did_not_see_too(self):
        # the refused second heal logs the same evidence for the "sigkill" kind (round 3), as it does for oom
        d = tempfile.mkdtemp()
        be = _backend(d)
        be._heal_attempts[self.SID] = 1
        logs = []
        be._log_cb = logs.append
        be.cli_scope = True
        root = tempfile.mkdtemp()
        Path(root, "fx.slice", self.UNIT).mkdir(parents=True)
        Path(root, "fx.slice", self.UNIT, "memory.events").write_text(self.EVENTS(0))
        with mock.patch.object(sb.subprocess, "run", lambda argv, **kw: mock.Mock(returncode=0, stdout=self._show(), stderr="")), \
             mock.patch.object(sb, "CGROUP_ROOT", root), mock.patch.object(be, "_ensure") as ens:
            be._on_session_gone(self._dead_session(be, d, exit_code=self.KILL, baseline=0))
        self.assertEqual(ens.call_count, 0, "no resume: the crash loop stands")
        loop_line = [m for m in logs if "crash loop" in m]
        self.assertEqual(len(loop_line), 1, logs)
        self.assertIn("; the CLI was killed by signal 9 with no OOM kill counted in its scope this turn (a kill by hand, or a "
                      "userspace killer the cgroup counter cannot see); memory.events oom_kill=0 (was 0 at the turn's start), "
                      "Result=success (scope %s)" % self.UNIT, loop_line[0])
        self.assertNotIn("OOM killer took", loop_line[0])
        self.assertNotIn("\u2014", loop_line[0])

    def test_a_collected_scope_with_a_non_sigkill_exit_reads_the_journal_for_the_whole_scope_stop(self):
        # round 3 (fresh-1): the incident's own shape. Under OOMPolicy=stop systemd SIGTERMs the whole scope;
        # when every member dies on it the unit is collected within milliseconds of the CLI's exit, before the
        # SDK reports that exit, so the show reads not-found and Result=oom-kill went with the unit. The
        # journal keeps it (`<unit>: Failed with result 'oom-kill'`), so it is read for a not-found unit
        # whenever the exit is not SIGKILL (143 from the CLI's SIGTERM handler, -15 raw, 1 and None alike),
        # bounded like the show, in text mode, and the whole-scope stop is named with the journal as its source
        for exit_code, said in ((143, "the CLI exited 143"), (-15, "the CLI was killed by signal 15"), (1, "the CLI exited 1"),
                                (None, "the CLI's exit was not reported")):
            with self.subTest(exit_code=exit_code):
                d = tempfile.mkdtemp()
                be = _backend(d)
                calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=exit_code, baseline=0,
                                                   journal=self.JOURNAL_OOM)
                self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV, self.JOURNAL_ARGV])
                jkw = calls[1][1]
                self.assertEqual(jkw.get("timeout"), sb.SCOPE_SHOW_TIMEOUT)
                self.assertIs(jkw.get("text"), True)
                self.assertIs(jkw.get("capture_output"), True)
                line = self._died_line(logs)
                self.assertIn("the OOM killer took a process in its scope %s (systemd stopped the whole scope over an OOM kill "
                              "(journal: Failed with result 'oom-kill'); %s)" % (self.UNIT, said), line)
                self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
                scope_line = [m for m in logs if "session scope result" in m]
                self.assertEqual(len(scope_line), 1, logs)
                self.assertIn("the scope was already collected (LoadState=not-found)", scope_line[0])
                self.assertIn("; the journal says systemd stopped the scope over an OOM kill (Failed with result 'oom-kill')",
                              scope_line[0])
                self.assertEqual(be.problems(), [])
        self.assertEqual(self.JOURNAL_ARGV, sb.SCOPE_JOURNAL_ARGV + [self.UNIT])
        self.assertEqual(sb.SCOPE_JOURNAL_ARGV, ["journalctl", "--user", "-n", "5", "-o", "cat", "-t", "systemd", "-u"],
                         "the manager's own lines only (-t systemd): a scope member's logger lines would push them out of the window")

    def test_a_journal_without_the_stop_line_is_a_plain_clause_never_silence(self):
        # the whole-life "killed by the OOM killer" line appears under `continue` for a contained kill too, so
        # it is no verdict; an empty journal, journalctl raising and journalctl exiting non-zero each become
        # a clause in the plain line (the first stderr line only), never silence and never a verdict
        cases = (("kill line only", dict(journal=self.JOURNAL_KILL),
                  "the journal records an OOM kill in the scope (A process of this unit has been killed by the OOM killer)"),
                 ("Started only", dict(journal=self.JOURNAL_STARTED), "the journal's newest lines for the scope record no OOM kill"),
                 ("empty", dict(journal=""), "the journal has no line for the scope"),
                 ("raises", dict(journal_raise=subprocess.TimeoutExpired(["journalctl"], 10)), "journalctl did not answer ("),
                 ("exits 1", dict(journal_returncode=1, journal_stderr="No journal files were found.\nmore\n"),
                  "journalctl exited 1 (No journal files were found.)"))
        for label, kw, said in cases:
            with self.subTest(journal=label):
                d = tempfile.mkdtemp()
                be = _backend(d)
                calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=143, baseline=0, **kw)
                self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV, self.JOURNAL_ARGV])
                self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
                self.assertFalse(any("OOM killer took" in m for m in logs), logs)
                scope_line = [m for m in logs if "session scope result" in m]
                self.assertEqual(len(scope_line), 1, logs)
                self.assertIn("the CLI exited 143; oom_kill was 0 at the turn's start; the scope was already collected "
                              "(LoadState=not-found), so the live counter could not be read; " + said, scope_line[0])
                if label == "exits 1":
                    self.assertNotIn("more", scope_line[0])
                self.assertEqual(be.problems(), [])
        # a LOADED unit never reads the journal, whatever the exit: its Result and counter are readable
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(0)}, exit_code=143, baseline=0,
                                           journal=self.JOURNAL_OOM)
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV])
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        # a collected unit with a SIGKILL exit reads it too (round 4: the exit alone cannot tell the OOM killer
        # from a kill by hand once the counter is gone), and the stop line names the death
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=self.KILL, baseline=0,
                                           journal=self.JOURNAL_OOM)
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV, self.JOURNAL_ARGV])
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])

    def test_an_exit_137_is_a_plain_exit_never_the_clis_own_sigkill(self):
        # round 3 (fresh-2): a claude_bin wrapper that runs the CLI as a child WITHOUT exec reports the child's
        # SIGKILL as its own exit 137; every layer romp launches through execs in place, so the CLI's own kill
        # is -9 and 137 is read as the plain exit it is (such a wrapper also defeats the interrupt escalation
        # and the orphan finder, so it is outside what romp supports). With a counter increase it is a child
        # kill the wrapper outlived; with the scope collected it is no verdict
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(1)}, exit_code=137, baseline=0)
        line = self._died_line(logs)
        self.assertNotIn("killed by signal 9", line)
        self.assertNotIn("OOM killer took", line)
        self.assertIn("while the CLI itself exited 137, so a tool child, not the CLI", line)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        scope_line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(scope_line), 1, logs)
        self.assertIn("the CLI exited 137;", scope_line[0])
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=137, baseline=0)
        self.assertFalse(any("OOM killer took" in m or "killed by signal 9" in m for m in logs), logs)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertTrue(any("session scope result" in m and "the CLI exited 137;" in m for m in logs), logs)
        self.assertEqual(sb.SIGKILL_EXIT, -9, "the match stays at -9")

    def test_the_sdks_minus_one_exit_reads_as_unreported_never_as_a_kill_by_signal_1(self):
        # round 3 (rules-3): the SDK's transport falls to -1 when its process wait raises (and anyio reports a
        # SIGHUP death the same), so -1 says the exit was not read: the plain line says so in those words, and
        # the contained shape (a counter increase, a non-SIGKILL exit) files no child verdict from it, as for None
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(1)}, exit_code=-1, baseline=0)
        scope_line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(scope_line), 1, logs)
        self.assertIn("the CLI ended on signal 1 (SIGHUP) or the SDK could not read its exit (it reports -1 for both); "
                      "oom_kill was 0 at the turn's start; memory.events oom_kill=1, Result=success", scope_line[0])
        self.assertNotIn("killed by signal 1", scope_line[0])
        line = self._died_line(logs)
        self.assertNotIn("a tool child", line)
        self.assertNotIn("OOM killer took", line)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        self.assertEqual(be.problems(), [])
        # with the scope collected the journal is read (not a SIGKILL) and an empty one leaves the bare notice
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(load="not-found", cgroup=""), exit_code=-1, baseline=0)
        self.assertEqual([argv for argv, _kw in calls], [self.SHOW_ARGV, self.JOURNAL_ARGV])
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])

    def test_a_memory_limit_is_named_only_when_one_is_in_force_and_applied(self):
        # round 3 (tests-4, rules-2): oom_verdict is pure and limits-blind, so the old "most likely the memory
        # limit" guess is gone (the collected-scope test above pins its absence on a limit-free backend); the
        # heal appends the limit as CONTEXT to an oom verdict by SIGKILL when a MemoryMax is set and the
        # controller is not known to leave it unapplied, never otherwise (MemoryHigh throttles, MemorySwapMax
        # alone kills nothing, an undelegated controller applies none), and never on the "sigkill" cell, whose
        # flat counter excludes the memcg killer. Round 4 (correctness-1): the clause is worded by the boot
        # probe's verdict, as the boot line is: "in force" only when the controller check settled True; when
        # it settled nothing (None) the clause says set for the scope but not settled and names the check
        # (memory-controller check, or the memory-limits probe when that is what settled nothing), never
        # "in force". The collected shape carries the journal's kill line here, so the verdict is oom.
        def heal(limits, delegated, events=None, unsettled=()):
            d = tempfile.mkdtemp()
            be = _backend(d)
            be.cli_scope_limits = dict(limits)
            be.cli_scope_memory_delegated = delegated
            be.cli_scope_unsettled = list(unsettled)
            show = self._show() if events else self._show(load="not-found", cgroup="")
            calls, logs = self._heal_with_show(d, be, show, events=events, exit_code=self.KILL, baseline=0, journal=self.JOURNAL_KILL)
            return self._died_line(logs), sb.read_reg(Path(d), self.SID).get("queue")
        line, q = heal({"memoryMax": "1G", "memorySwapMax": "0"}, True)
        self.assertIn("so its counter could not be read (oom_kill was 0 at the turn's start); the journal records an OOM kill in its "
                      "scope (A process of this unit has been killed by the OOM killer); a memory limit (MemoryMax=1G) is in force on "
                      "its scope); resuming", line)
        self.assertEqual(q, [sb.CRASH_RESUME_NUDGE_OOM])
        for unsettled, check in ((["memoryController"], "memory-controller check"), (["memoryLimits", "oomPolicy"], "memory-limits probe")):
            with self.subTest(unsettled=unsettled):
                line, q = heal({"memoryMax": "1G"}, None, unsettled=unsettled)   # the check settled nothing: set, not known unapplied
                self.assertIn("; a memory limit (MemoryMax=1G) is set for its scope but not settled (the %s settled nothing at start))"
                              % check, line)
                self.assertNotIn("is in force", line, "an unsettled value is never said to be in force (round 4)")
                self.assertEqual(q, [sb.CRASH_RESUME_NUDGE_OOM])
        line, q = heal({"memoryMax": "1G"}, True, events={self.UNIT: self.EVENTS(1)})   # the counter rose: the limit as context
        self.assertIn("(was 0 at the turn's start), Result=success; a memory limit (MemoryMax=1G) is in force on its scope)", line)
        for limits, delegated, why in (({}, True, "no limit set"),
                                       ({"memoryHigh": "1G", "memorySwapMax": "0"}, True, "no MemoryMax: nothing here kills"),
                                       ({"memoryMax": "1G"}, False, "the controller undelegated: systemd applies nothing")):
            with self.subTest(why=why):
                line, q = heal(limits, delegated)
                self.assertNotIn("memory limit", line, why)
                self.assertEqual(q, [sb.CRASH_RESUME_NUDGE_OOM])
        line, q = heal({"memoryMax": "1G"}, True, events={self.UNIT: self.EVENTS(0)})
        self.assertNotIn("memory limit", line, "a flat counter excludes the memcg killer: no limit named")
        self.assertEqual(q, [sb.CRASH_RESUME_NUDGE_KILLED])

    def test_a_whole_life_count_with_no_baseline_names_no_child_kill(self):
        # round 3 (tests-5): with no turn-start baseline (the connect-time read failed) a whole-life count above
        # zero and a non-SIGKILL exit is context in the plain line, not a "contained" verdict: nothing says the
        # counted kill was this turn's
        d = tempfile.mkdtemp()
        be = _backend(d)
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(2)}, exit_code=1, baseline=None)
        line = self._died_line(logs)
        self.assertNotIn("a tool child", line)
        self.assertNotIn("OOM killer took", line)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE])
        scope_line = [m for m in logs if "session scope result" in m]
        self.assertEqual(len(scope_line), 1, logs)
        self.assertIn("the CLI exited 1; no turn-start baseline; memory.events oom_kill=2, Result=success", scope_line[0])

    # ── the executing _amain tests' stand-in SDK ─────────────────────────────────────────────────────
    @contextlib.contextmanager
    def _fake_sdk(self, client_cls):
        """A stand-in claude_agent_sdk module for the executing _amain tests: `client_cls` stands in for
        ClaudeSDKClient; the options and message classes are bare. Restores sys.modules on exit, so the
        session thread must be joined INSIDE the block (the lazy import at _amain's start reads it)."""
        from importlib.machinery import ModuleSpec

        class _Options:
            def __init__(self, **kw):
                for k, v in kw.items():
                    setattr(self, k, v)
        fake = types.ModuleType("claude_agent_sdk")
        fake.__spec__ = ModuleSpec("claude_agent_sdk", loader=None)
        fake.ClaudeSDKClient, fake.ClaudeAgentOptions, fake.HookMatcher = client_cls, _Options, (lambda **kw: kw)
        for n in ("AssistantMessage", "ResultMessage", "SystemMessage", "TextBlock"):
            setattr(fake, n, type(n, (), {}))
        saved = sys.modules.get("claude_agent_sdk")
        sys.modules["claude_agent_sdk"] = fake
        try:
            yield fake
        finally:
            if saved is None:
                sys.modules.pop("claude_agent_sdk", None)
            else:
                sys.modules["claude_agent_sdk"] = saved

    def _session_for_amain(self, d, be):
        reg = {"sid": self.SID, "name": "web", "mode": "acceptEdits", "alive": True, "cwd": d}
        sb.write_reg(Path(d), self.SID, reg)
        return sb.SdkSession(be, dict(reg))

    @staticmethod
    def _until(pred, timeout=10.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end and not pred():
            time.sleep(0.01)
        return pred()

    def test_amain_records_the_clis_exit_at_teardown(self):
        # round 3 (tests-1): the exit-code capture at teardown (the exception's exit_code, else the transport's
        # returncode) has an EXECUTING test: the real _amain runs against a stand-in SDK whose stream dies
        # after the connect in each of the three shapes the SDK produces, and _cli_exit_code must read -9 once
        # the thread has ended. The thread is JOINED, never shut down (shutdown sets `ended`, the path the heal
        # skips), and the death waits for the connect, whose record clears the field, so the capture is what
        # the read sees. If this ever fails with the field None under load, that is an ordering hole, not a flake.
        from types import SimpleNamespace

        class _Err(Exception):
            def __init__(self, exit_code=None):
                super().__init__("the CLI ended")
                self.exit_code = exit_code
        for shape in ("an exception carrying exit_code", "the stream ending with the transport's returncode set",
                      "a codeless exception with the returncode set"):
            with self.subTest(shape=shape):
                death = threading.Event()

                class _Client:
                    def __init__(self, options=None, transport=None):
                        self._transport = SimpleNamespace(_process=SimpleNamespace(pid=4242, returncode=None))

                    async def __aenter__(self):
                        return self

                    async def __aexit__(self, *a):
                        return False

                    async def query(self, prompt, session_id="default"):
                        async for _turn in prompt:
                            pass

                    async def receive_messages(self):
                        while not death.is_set():
                            await asyncio.sleep(0.01)
                        if shape == "an exception carrying exit_code":
                            raise _Err(exit_code=-9)
                        self._transport._process.returncode = -9
                        if shape == "a codeless exception with the returncode set":
                            raise _Err()
                        return
                        yield None   # noqa: the generator shape

                    async def get_context_usage(self):
                        return {"percentage": 1, "model": "m"}

                    async def get_server_info(self):
                        return {}

                    async def interrupt(self):
                        pass
                d = tempfile.mkdtemp()
                with self._fake_sdk(_Client):
                    be = _backend(d)
                    be.cli_scope = True
                    s = self._session_for_amain(d, be)
                    try:
                        with mock.patch.object(sb, "_read_cgroup", lambda pid: "0::/user.slice/user@.service/app.slice/%s\n" % self.UNIT):
                            s.start()
                            self.assertTrue(s._connected.wait(timeout=10), "the connect never landed")
                            self.assertIsNone(s._cli_exit_code, "the connect-time reset")
                            death.set()
                            s.thread.join(timeout=10)
                        self.assertFalse(s.thread.is_alive(), "the stream's end ends the session thread (no reconnect armed)")
                        self.assertEqual(s._cli_exit_code, -9, shape)
                    finally:
                        if s.thread.is_alive():
                            s.shutdown()
                            s.thread.join(timeout=10)
                        shutil.rmtree(d, ignore_errors=True)

    def test_amain_heals_a_midturn_sigkill_from_the_recorded_exit(self):
        # the capture feeding the heal end to end (round 3, tests-1): the fake raises inflight to 1 before dying
        # by SIGKILL (a turn in flight, as the OOM killer finds it), the show says the scope is already
        # collected, the journal carries the manager's kill line, and the heal names the death by the recorded -9
        # and the journal and queues the out-of-memory notice. Only the show's and the journal's argv are
        # dispatched to the fakes; every other subprocess call is the real one.
        from types import SimpleNamespace
        death = threading.Event()
        holder = {}

        class _Err(Exception):
            exit_code = -9

        class _Client:
            def __init__(self, options=None, transport=None):
                self._transport = SimpleNamespace(_process=SimpleNamespace(pid=4242, returncode=None))

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def query(self, prompt, session_id="default"):
                async for _turn in prompt:
                    pass

            async def receive_messages(self):
                while not death.is_set():
                    await asyncio.sleep(0.01)
                s = holder["s"]
                with s._lock:
                    s.inflight = 1
                raise _Err("the CLI ended")
                yield None   # noqa: the generator shape

            async def get_context_usage(self):
                return {"percentage": 1, "model": "m"}

            async def get_server_info(self):
                return {}

            async def interrupt(self):
                pass
        real_run = sb.subprocess.run
        shows = []

        def fake_run(argv, **kw):
            if list(argv[:3]) == ["systemctl", "--user", "show"]:
                shows.append(list(argv))
                return mock.Mock(returncode=0, stdout=self._show(load="not-found", cgroup=""), stderr="")
            if list(argv[:1]) == ["journalctl"]:
                shows.append(list(argv))
                return mock.Mock(returncode=0, stdout=self.JOURNAL_KILL, stderr="")
            return real_run(argv, **kw)
        logs = []
        d = tempfile.mkdtemp()
        with self._fake_sdk(_Client):
            be = _backend(d)
            be.cli_scope = True
            be._log_cb = logs.append
            s = holder["s"] = self._session_for_amain(d, be)
            try:
                with mock.patch.object(sb, "_read_cgroup", lambda pid: "0::/user.slice/user@.service/app.slice/%s\n" % self.UNIT), \
                     mock.patch.object(sb.subprocess, "run", fake_run), mock.patch.object(be, "_ensure") as ens:
                    s.start()
                    self.assertTrue(s._connected.wait(timeout=10), "the connect never landed")
                    self.assertEqual(s.cli_scope_unit, self.UNIT)
                    death.set()
                    s.thread.join(timeout=10)
                    self.assertFalse(s.thread.is_alive())
                    self.assertEqual(s._cli_exit_code, -9)
                    self.assertEqual(shows, [sb.SCOPE_SHOW_ARGV + [self.UNIT], sb.SCOPE_JOURNAL_ARGV + [self.UNIT]],
                                     "one show and one journal read, the dead CLI's exact unit")
                    line = [m for m in logs if "died mid-turn" in m]
                    self.assertEqual(len(line), 1, logs)
                    self.assertIn("the OOM killer took a process in its scope %s (the CLI was killed by signal 9; the scope was "
                                  "already collected, so its counter could not be read" % self.UNIT, line[0])
                    self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
                    ens.assert_called_once_with(self.SID)
            finally:
                if s.thread.is_alive():
                    s.shutdown()
                    s.thread.join(timeout=10)
                shutil.rmtree(d, ignore_errors=True)

    def test_amain_rebaselines_the_counter_at_the_feeders_raise(self):
        # round 3 (tests-2): the per-turn baseline's wiring at the feeder's inflight 0->1 raise has an executing
        # test: the connect reads 0, the scope's counter then reads 2 before a turn is fed, and the snapshot at
        # the raise reads it, so the baselines go [0] -> [0, 2]. The wait is on the fake query having TAKEN the
        # item (it arrives as an SDK user-message dict), never on inflight, which the snapshot races.
        from types import SimpleNamespace
        cgpath = "/user.slice/user@.service/app.slice/" + self.UNIT
        root = tempfile.mkdtemp()
        Path(root, cgpath.lstrip("/")).mkdir(parents=True)
        events = Path(root, cgpath.lstrip("/"), "memory.events")
        events.write_text(self.EVENTS(0))
        fed = []

        class _Client:
            def __init__(self, options=None, transport=None):
                self._transport = SimpleNamespace(_process=SimpleNamespace(pid=4242))

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def query(self, prompt, session_id="default"):
                async for turn in prompt:
                    fed.append(turn)

            async def receive_messages(self):
                await asyncio.Event().wait()
                yield None

            async def get_context_usage(self):
                return {"percentage": 1, "model": "m"}

            async def get_server_info(self):
                return {}

            async def interrupt(self):
                pass
        d = tempfile.mkdtemp()
        with self._fake_sdk(_Client):
            be = _backend(d)
            be.cli_scope = True
            s = self._session_for_amain(d, be)
            baselines = []
            orig = s._snapshot_oom_baseline

            def counting():
                orig()
                baselines.append(s._oom_baseline)
            s._snapshot_oom_baseline = counting   # an instance attribute: every caller reads it through self
            try:
                with mock.patch.object(sb, "_read_cgroup", lambda pid: "0::%s\n" % cgpath), mock.patch.object(sb, "CGROUP_ROOT", root):
                    s.start()
                    self.assertTrue(s._connected.wait(timeout=10), "the connect never landed")
                    self.assertEqual(baselines, [0], "the connect-time baseline")
                    events.write_text(self.EVENTS(2))   # a kill between turns (a tool shell's child the session outlived)
                    s.enqueue("first turn")
                    self.assertTrue(self._until(lambda: bool(fed)), "the fake query never took the item")
                    self.assertEqual([f["message"]["content"][0]["text"] for f in fed], ["first turn"])
                    self.assertEqual(baselines, [0, 2], "the feeder's 0->1 raise re-read the live counter before the yield")
                    self.assertEqual(s._oom_baseline, 2)
            finally:
                s.shutdown()
                if s.thread.ident is not None:
                    s.thread.join(timeout=10)
                shutil.rmtree(d, ignore_errors=True)

    def test_a_reconnect_takes_no_baseline_from_the_old_scope(self):
        # round 3 (correctness-3, regression-3): the loop top used to snapshot the counter before the new client
        # existed, reading the OLD scope's memory.events, and the next connect's record discarded it. The connect
        # snapshot covers the idle interval and the re-headed turn takes its own baseline at the feeder's raise,
        # both on the NEW scope: after the first connect's read no snapshot reads the old scope's path, and the
        # final baseline is the new scope's count
        from types import SimpleNamespace
        UNIT2 = "romp-session-11111111-4343-1700000000000001000.scope"
        cg = "/user.slice/user@.service/app.slice/%s"
        pids = iter([4242, 4343])

        class _Client:
            instances = []

            def __init__(self, options=None, transport=None):
                self._transport = SimpleNamespace(_process=SimpleNamespace(pid=next(pids)))
                self.fed = []
                type(self).instances.append(self)

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def query(self, prompt, session_id="default"):
                async for turn in prompt:
                    self.fed.append(turn["message"]["content"][0]["text"])

            async def receive_messages(self):
                await asyncio.Event().wait()
                yield None

            async def get_context_usage(self):
                return {"percentage": 1, "model": "m"}

            async def get_server_info(self):
                return {}

            async def interrupt(self):
                pass
        root = tempfile.mkdtemp()
        for u, n in ((self.UNIT, 5), (UNIT2, 0)):
            Path(root, (cg % u).lstrip("/")).mkdir(parents=True)
            Path(root, (cg % u).lstrip("/"), "memory.events").write_text(self.EVENTS(n))

        def fake_cgroup(pid):
            return "0::%s\n" % (cg % (self.UNIT if pid == 4242 else UNIT2))
        d = tempfile.mkdtemp()
        with self._fake_sdk(_Client):
            be = _backend(d)
            be.cli_scope = True
            s = self._session_for_amain(d, be)
            reads = []
            orig = s._snapshot_oom_baseline

            def recording():
                orig()
                reads.append((s.cli_scope_cgroup, s._oom_baseline))
            s._snapshot_oom_baseline = recording
            try:
                with mock.patch.object(sb, "_read_cgroup", fake_cgroup), mock.patch.object(sb, "CGROUP_ROOT", root):
                    s.start()
                    self.assertTrue(s._connected.wait(timeout=10), "the first connect never landed")
                    self.assertEqual(reads, [(cg % self.UNIT, 5)], "the connect-time baseline, on the first scope")
                    # a settled hold (fed mid-turn, its turn ended, the CLI still held the text) meets a reconnect: the
                    # loop top puts it back and _reconcile_stranded re-heads it (no conversation ever materialized), so
                    # the new client feeds it as a fresh turn
                    s._untaken = {"text": "carry on", "item": "carry on", "fresh": True, "settled": True,
                                  "t": 0, "off": None, "fsid": None}
                    s.loop.call_soon_threadsafe(lambda: (setattr(s, "_reconnect", True), s._wake_set()))
                    self.assertTrue(self._until(lambda: len(_Client.instances) == 2 and _Client.instances[1].fed),
                                    "the second connect and its re-headed feed never came")
                    self.assertEqual(_Client.instances[1].fed, ["carry on"], "the re-headed text fed to the NEW client")
                    self.assertEqual(s.cli_scope_unit, UNIT2)
                    self.assertEqual(reads[0], (cg % self.UNIT, 5))
                    self.assertEqual([r for r in reads[1:] if r[0] == cg % self.UNIT], [],
                                     "no snapshot after the connect read the old scope's path (the loop-top read is gone)")
                    self.assertEqual(reads[1:], [(cg % UNIT2, 0), (cg % UNIT2, 0)],
                                     "the new connect's baseline, then the feeder's raise for the re-headed turn")
                    self.assertEqual(s._oom_baseline, 0, "the new scope's count")
            finally:
                s.shutdown()
                if s.thread.ident is not None:
                    s.thread.join(timeout=10)
                shutil.rmtree(d, ignore_errors=True)


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
        # round 4 (tests-1): the heal's own de-dup filter matches every form (is_crash_resume_nudge), not the bare
        # constant by equality: an OOM notice already queued is replaced by the killed form, and a killed one by
        # the bare form, each with the reply kept behind it and nothing stacked
        d = tempfile.mkdtemp()
        be = _backend(d)
        _reg(d, self.SID, queue=[sb.CRASH_RESUME_NUDGE_OOM, "a reply the person typed"])
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(0)}, exit_code=self.KILL, baseline=0)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_KILLED, "a reply the person typed"])
        d = tempfile.mkdtemp()
        be = _backend(d)
        _reg(d, self.SID, queue=[sb.CRASH_RESUME_NUDGE_KILLED, "a reply the person typed"])
        calls, logs = self._heal_with_show(d, be, self._show(), events={self.UNIT: self.EVENTS(0)}, exit_code=1, baseline=0)
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE, "a reply the person typed"])

    def test_a_send_during_the_heals_scope_read_lands_behind_the_nudge(self):
        # round 4 (kernel-3): the heal's two bounded reads (the show, the journal) used to run AFTER the dead
        # session was popped from be.sessions and BEFORE its nudge reached the reg, so a send landing in those
        # milliseconds spawned a replacement from a reg without the nudge, and the replacement's next persist
        # dropped it. The reads now run before the pop: the send lands in the dying session's own queue (its
        # thread alive in _run's finally, its loop already closed by asyncio.run, which enqueue must not raise
        # on), the heal re-heads the reg behind its nudge, and the replacement seeds both. The fake show blocks
        # until the test's send has returned.
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope = True
        s = self._dead_session(be, d, exit_code=self.KILL, baseline=0)
        loop = asyncio.new_event_loop()
        loop.close()
        s.loop, s._input_wake = loop, asyncio.Event()     # the session's loop, closed: the thread is in _run's finally
        be.sessions[self.SID] = s
        in_show, sent, parked = threading.Event(), threading.Event(), threading.Event()
        calls = []

        def fake_run(argv, **kw):
            calls.append(list(argv))
            if argv[:1] == ["systemctl"]:
                in_show.set()
                sent.wait(10)
                return mock.Mock(returncode=0, stdout=self._show(load="not-found", cgroup=""), stderr="")
            return mock.Mock(returncode=0, stdout=self.JOURNAL_KILL, stderr="")
        with mock.patch.object(sb.subprocess, "run", fake_run), \
             mock.patch.object(sb.SdkSession, "_run", lambda self_: parked.wait(10)):   # the replacement: alive, runs nothing
            s.thread = threading.Thread(target=lambda: be._on_session_gone(s), daemon=True)
            s.thread.start()
            try:
                self.assertTrue(in_show.wait(10), "the heal never read the scope")
                self.assertTrue(be.send(self.SID, "peer text"), "the send is accepted, and raises nothing on the closed loop")
                self.assertIs(be.sessions.get(self.SID), s, "no replacement was spawned during the read")
                self.assertEqual(s.pending(), ["peer text"], "the text went to the dying session's own queue")
                self.assertNotIn("peer text", sb.read_reg(Path(d), self.SID).get("queue") or [],
                                 "round 5 (D2): the mirror is sealed from the cut, so the send's own persist wrote nothing; the "
                                 "heal's write carries the text")
                sent.set()
                s.thread.join(10)
                self.assertFalse(s.thread.is_alive())
                rep = be.sessions.get(self.SID)
                self.assertIsNotNone(rep)
                self.assertIsNot(rep, s, "the heal spawned the replacement")
                self.assertEqual(rep.pending(), [sb.CRASH_RESUME_NUDGE_OOM, "peer text"], "the nudge heads the replacement's queue")
                rep._persist_queue()
                self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM, "peer text"],
                                 "the nudge survives the replacement's own persist")
                self.assertEqual([c[0] for c in calls], ["systemctl", "journalctl"])
                # round 5 (D2): the fold closed the dying session's queue: a late persist writes nothing over the heal's
                # reg, a late enqueue is refused (send re-resolves), a cancel is a miss
                s._persist_queue()
                self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM, "peer text"],
                                 "a late persist on the sealed session is a no-op")
                self.assertIs(s.enqueue("late"), False)
                self.assertFalse(s.enqueue_if_empty("late"))
                self.assertIsNone(s.unqueue(0, "peer text"))
                self.assertEqual(s.pending(), ["peer text"], "nothing appended, nothing popped")
                self.assertEqual(rep.pending(), [sb.CRASH_RESUME_NUDGE_OOM, "peer text"])
            finally:
                parked.set()
                for t in (s.thread, getattr(be.sessions.get(self.SID), "thread", None)):
                    if t is not None and t.is_alive():
                        t.join(10)

    @contextlib.contextmanager
    def _heal_blocked_in_the_show(self, d, be, journal=None):
        """The round-4 race scaffold as a context: a dying session (its loop closed by asyncio.run, its thread in
        _run's finally running _on_session_gone) whose heal is blocked inside the fake systemctl show until `sent` is
        set; the journal then answers `journal` (the kill line by default) and the replacement's _run parks. Yields
        (s, sent, calls) once the heal is inside the show; joins every thread on exit."""
        s = self._dead_session(be, d, exit_code=self.KILL, baseline=0)
        loop = asyncio.new_event_loop()
        loop.close()
        s.loop, s._input_wake = loop, asyncio.Event()
        be.sessions[self.SID] = s
        in_show, sent, parked = threading.Event(), threading.Event(), threading.Event()
        calls = []

        def fake_run(argv, **kw):
            calls.append(list(argv))
            if argv[:1] == ["systemctl"]:
                in_show.set()
                sent.wait(10)
                return mock.Mock(returncode=0, stdout=self._show(load="not-found", cgroup=""), stderr="")
            return mock.Mock(returncode=0, stdout=self.JOURNAL_KILL if journal is None else journal, stderr="")
        with mock.patch.object(sb.subprocess, "run", fake_run), \
             mock.patch.object(sb.SdkSession, "_run", lambda self_: parked.wait(10)):
            s.thread = threading.Thread(target=lambda: be._on_session_gone(s), daemon=True)
            s.thread.start()
            try:
                self.assertTrue(in_show.wait(10), "the heal never read the scope")
                yield s, sent, calls
            finally:
                sent.set()
                parked.set()
                for t in (s.thread, getattr(be.sessions.get(self.SID), "thread", None)):
                    if t is not None and t.is_alive():
                        t.join(10)

    def test_a_send_that_enqueues_after_the_heals_write_goes_to_the_replacement(self):
        # round 5 (D2: correctness-2, kernel-3): a send obtains the dying session from _ensure during the read and
        # reaches its enqueue only after the heal folded the queue into the reg and popped the session (the send's
        # own _ensure-to-persist gap, milliseconds under load). Before: the text was appended to the dead session's
        # pending and its persist put ['peer text'] over the reg's [nudge], so the nudge was lost, or the text at
        # the replacement's next persist. Now the fold CLOSES the queue: the enqueue is refused, send re-resolves
        # the sid, and the replacement takes the text behind the nudge. The send blocks in _transcript_mark (between
        # _ensure and enqueue) until the replacement exists.
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope = True
        logs = []
        be._log_cb = logs.append
        with self._heal_blocked_in_the_show(d, be) as (s, sent, calls):
            orig_mark, in_mark = be._transcript_mark, threading.Event()

            def slow_mark(sid):
                in_mark.set()
                deadline = time.time() + 10
                while time.time() < deadline and be.sessions.get(self.SID) in (s, None):
                    time.sleep(0.005)
                return orig_mark(sid)
            be._transcript_mark = slow_mark
            result = []
            sender = threading.Thread(target=lambda: result.append(be.send(self.SID, "peer text")), daemon=True)
            sender.start()
            self.assertTrue(in_mark.wait(10), "the send never reached the transcript mark")   # _ensure handed it the dying session
            sent.set()
            s.thread.join(10)
            sender.join(10)
            self.assertFalse(sender.is_alive(), "the send returned")
            self.assertEqual(result, [True], "the send is accepted")
            rep = be.sessions.get(self.SID)
            self.assertIsNotNone(rep)
            self.assertIsNot(rep, s, "the heal spawned the replacement")
            self.assertEqual(s.pending(), [], "the dying session's closed queue refused the text")
            self.assertEqual(rep.pending(), [sb.CRASH_RESUME_NUDGE_OOM, "peer text"], "the replacement took it, behind the nudge")
            self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM, "peer text"])
            self.assertTrue(any("queue closed under the send" in m for m in logs), logs)
            self.assertEqual(be.problems(), [], "the re-resolve is the designed path, not a problem")

    def test_a_send_in_the_heals_pop_to_write_gap_lands_behind_the_nudge(self):
        # round 6 (tests-1): a send whose _ensure ran between the heal's pop and its reg write found no session and
        # spawned the replacement from the pre-write reg; the replacement's persist then put a nudge-less list over
        # the heal's write, so the nudge and every text sealed during the reads were lost from every live queue
        # (the residual the round-5 body named, grown by the seal: the folded text no longer persisted itself).
        # Now the pop and the write share one hold of be._lock, the lock _ensure reads the reg under, so the send
        # blocks until the write has landed and spawns from the reg that carries the fold. The heal thread's
        # nudge-headed write_reg is slowed once to hold the gap open.
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope = True
        with self._heal_blocked_in_the_show(d, be) as (s, sent, calls):
            self.assertTrue(be.send(self.SID, "A"), "the send during the reads is accepted")
            self.assertEqual(s.pending(), ["A"])
            orig_write, slowed = sb.write_reg, []

            def slow_write(state_dir, sid, reg):
                if threading.current_thread() is s.thread and not slowed \
                        and any(sb.is_crash_resume_nudge(sb._queue_text(e)) for e in reg.get("queue") or []):
                    slowed.append(True)
                    time.sleep(0.5)
                return orig_write(state_dir, sid, reg)
            with mock.patch.object(sb, "write_reg", slow_write):
                sent.set()
                deadline = time.time() + 10
                while not s._queue_closed and time.time() < deadline:
                    time.sleep(0.001)
                self.assertTrue(s._queue_closed, "the heal folded the queue")
                self.assertTrue(be.send(self.SID, "B"), "the send in the gap is accepted")
                s.thread.join(10)
            self.assertFalse(s.thread.is_alive())
            self.assertEqual(slowed, [True], "the heal's write was held open once")
            rep = be.sessions.get(self.SID)
            self.assertIsNotNone(rep)
            self.assertIsNot(rep, s, "the heal spawned the replacement")
            self.assertEqual(rep.pending(), [sb.CRASH_RESUME_NUDGE_OOM, "A", "B"],
                             "the replacement was spawned from the written reg and took the second send behind the fold")
            rep._persist_queue()
            self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM, "A", "B"])

    def test_a_send_refused_by_the_close_re_resolves_to_a_reg_that_carries_the_fold(self):
        # round 6 (correctness-1): the fold closed the queue before its write landed, so a send that held the dying
        # session (its _ensure ran during the reads) and was refused by the close re-resolved through _ensure, which
        # spawned the replacement from the pre-fold reg; the replacement's first persist then overwrote the fold,
        # dropping the nudge and every text sealed during the reads. Now the write is inside the hold of the
        # session's _lock that closes the queue, so an enqueue can see the closed queue only once the fold is on
        # disk. The heal thread's nudge-headed write is held until a replacement appears or a bounded deadline
        # passes: with the fix in, the refused send is blocked on the session's _lock until the write lands, so no
        # replacement can appear during the hold and only the deadline releases it.
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope = True
        with self._heal_blocked_in_the_show(d, be) as (s, sent, calls):
            self.assertTrue(be.send(self.SID, "first"))
            orig_mark, in_mark = be._transcript_mark, threading.Event()

            def slow_mark(sid):
                in_mark.set()
                deadline = time.time() + 10
                while time.time() < deadline and not s._queue_closed:
                    time.sleep(0.001)
                return orig_mark(sid)
            be._transcript_mark = slow_mark
            orig_write, held = sb.write_reg, []

            def holding_write(state_dir, sid, reg):
                if threading.current_thread() is s.thread and not held \
                        and any(sb.is_crash_resume_nudge(sb._queue_text(e)) for e in reg.get("queue") or []):
                    held.append(True)
                    deadline = time.time() + 1.0
                    while time.time() < deadline and be.sessions.get(self.SID) in (s, None):
                        time.sleep(0.005)
                return orig_write(state_dir, sid, reg)
            result = []
            with mock.patch.object(sb, "write_reg", holding_write):
                sender = threading.Thread(target=lambda: result.append(be.send(self.SID, "second")), daemon=True)
                sender.start()
                self.assertTrue(in_mark.wait(10), "the second send holds the dying session")
                sent.set()
                s.thread.join(10)
                sender.join(10)
            self.assertFalse(sender.is_alive(), "the send returned")
            self.assertEqual(result, [True], "the send is accepted")
            self.assertEqual(held, [True], "the heal's write was held")
            rep = be.sessions.get(self.SID)
            self.assertIsNotNone(rep)
            self.assertIsNot(rep, s, "the heal spawned the replacement")
            self.assertEqual(s.pending(), ["first"], "the fold carried the first text; nothing was appended after the close")
            self.assertEqual(rep.pending(), [sb.CRASH_RESUME_NUDGE_OOM, "first", "second"],
                             "the refused send re-resolved to a replacement spawned from the written fold")
            rep._persist_queue()
            self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM, "first", "second"])

    def test_a_deliver_that_enqueues_after_the_heals_write_goes_to_the_replacement(self):
        # round 6 (regression-1): deliver (a peer's mail) ignored enqueue's False, so a text handed to the dying
        # session during the reads whose enqueue landed after the fold was dropped while the bus was told it was
        # delivered (the maildir copy consumed). deliver re-resolves like send now, through the one helper
        # (_enqueue_resolving): here the enqueue is released to run only after the heal has folded the queue, popped
        # the session and spawned the replacement.
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope = True
        logs = []
        be._log_cb = logs.append
        with self._heal_blocked_in_the_show(d, be) as (s, sent, calls):
            orig_enqueue, released = sb.SdkSession.enqueue, []

            def late_enqueue(self_, text, todo="", send_id=""):
                if self_ is s and not released:
                    released.append(True)
                    sent.set()             # the heal runs to its end before this enqueue reaches the queue
                    s.thread.join(10)
                return orig_enqueue(self_, text, todo=todo, send_id=send_id)
            with mock.patch.object(sb.SdkSession, "enqueue", late_enqueue):
                self.assertTrue(be.deliver(self.SID, "peer mail"), "the deliver is accepted")
            self.assertEqual(released, [True])
            self.assertFalse(s.thread.is_alive())
            rep = be.sessions.get(self.SID)
            self.assertIsNotNone(rep)
            self.assertIsNot(rep, s, "the heal spawned the replacement")
            self.assertEqual(s.pending(), [], "the dying session's closed queue refused the mail")
            self.assertEqual(rep.pending(), [sb.CRASH_RESUME_NUDGE_OOM, "peer mail"], "the replacement took it, behind the nudge")
            rep._persist_queue()
            self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM, "peer mail"])
            self.assertTrue(any("queue closed under the send" in m for m in logs), logs)
            self.assertEqual(be.problems(), [], "the re-resolve is the designed path, not a problem")

    def test_an_unreadable_reg_skips_the_sealed_queue_write_and_the_heal_says_so(self):
        # round 6 (correctness-2): _write_sealed_queue rebuilt the reg from `read_reg(...) or {"sid": ...}`, so a
        # transient read failure of an EXISTING reg wrote a gutted {sid, queue} reg with no alive, name, cwd or
        # lastSid (the 2026-08-31 blink class _update_reg guards against) and the heal went on to spawn the
        # replacement from it. Now the queue is still closed under the session's _lock, nothing is written, an
        # OSError worded as _update_reg's guard is raised and the heal's FAILED line names it; the reg keeps its
        # last good queue and no replacement is spawned (a silent resume with no nudge otherwise). The session's
        # pending texts do not reach the reg: the one-lost-update trade _update_reg makes, and the line says so.
        d = tempfile.mkdtemp()
        be = _backend(d)
        logs = []
        be._log_cb = logs.append
        _reg(d, self.SID, queue=["old text"])
        s = self._dead_session(be, d, exit_code=self.KILL, baseline=0)   # its pending is seeded from the reg's queue
        with s._lock:
            s._pending.append("peer text")        # a send during the reads: in the pending, not in the reg
        before = sb.read_reg(Path(d), self.SID)
        with mock.patch.object(sb, "read_reg", return_value=None), mock.patch.object(be, "_ensure") as ens:
            be._on_session_gone(s)
        after = sb.read_reg(Path(d), self.SID)
        self.assertEqual(after, before, "the reg is untouched: alive, name, cwd, lastSid and its prior queue")
        for key in ("alive", "name", "cwd", "lastSid"):
            self.assertIn(key, after)
        self.assertEqual(after.get("queue"), ["old text"], "the reg keeps its last good queue")
        ens.assert_not_called()
        self.assertTrue(s._queue_closed, "the queue is closed before the raise")
        failed = [m for m in logs if "crash-resume FAILED" in m]
        self.assertEqual(len(failed), 1, logs)
        self.assertIn("reg %s unreadable: skipping the sealed queue write rather than gutting the reg (2 pending text(s) "
                      "did not reach it)" % self.SID[:8], failed[0])

    def test_a_send_during_the_read_under_a_crash_loop_refusal_is_parked_in_the_reg(self):
        # round 5 (fresh-2): with the one resume spent (_heal_attempts 1), a send that reaches the dying session during
        # the read is accepted and its text folded into the reg by the refusal's own write (the mirror is sealed from
        # the cut, so nothing else writes it); no session runs it now (no replacement, no nudge, no re-head), the
        # crash-loop line says how many texts wait, and the next start (a later send, the boot reconcile) runs them
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope = True
        be._heal_attempts[self.SID] = 1
        logs = []
        be._log_cb = logs.append
        with self._heal_blocked_in_the_show(d, be) as (s, sent, calls):
            self.assertTrue(be.send(self.SID, "peer text"))
            self.assertEqual(s.pending(), ["peer text"])
            sent.set()
            s.thread.join(10)
        self.assertIsNone(be.sessions.get(self.SID), "the refusal spawns nothing")
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), ["peer text"], "parked in the reg, no nudge")
        line = [m for m in logs if "crash loop" in m]
        self.assertEqual(len(line), 1, logs)
        self.assertIn("; 1 queued text(s) wait until the next start (a later send or the boot reconcile runs them in order)", line[0])
        self.assertEqual(sb.last_state_value(Path(d), self.SID), "working", "still cut for the next kernel restart")
        self.assertTrue(s._queue_closed, "the refusal's write closes the queue like the resume's")

    def test_a_user_end_during_the_heals_scope_read_ends_the_session_without_a_raise(self):
        # round 5 (D3: correctness-3, regression-1, kernel-2): be.kill (the endSession op, the /kill route, end-on-idle)
        # reaches the dying session during the read; its shutdown scheduled on the closed loop and raised
        # RuntimeError('Event loop is closed') out of kill, so the end landed but the op's tail was skipped and a
        # traceback logged. Now every loop call is guarded (_call_on_loop): kill returns True, the session is ended,
        # the reg says alive False, no heal runs (the session ended during the read) and no replacement is spawned
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope = True
        logs = []
        be._log_cb = logs.append
        with self._heal_blocked_in_the_show(d, be) as (s, sent, calls):
            s.client = object()      # a connected session: shutdown schedules the interrupt too
            self.assertTrue(be.kill(self.SID), "the end lands, and raises nothing")
            self.assertTrue(s.ended)
            sent.set()
            s.thread.join(10)
        self.assertIsNone(be.sessions.get(self.SID), "no replacement: the session was ended, not cut")
        reg = sb.read_reg(Path(d), self.SID)
        self.assertIs(reg.get("alive"), False, "kill's flip survives the heal thread's own write")
        self.assertFalse(any(sb.is_crash_resume_nudge(sb._queue_text(e)) for e in reg.get("queue") or []), "no nudge: no heal ran")
        self.assertFalse(any("died mid-turn" in m for m in logs), logs)
        self.assertFalse(any("Event loop is closed" in m for m in logs), logs)

    def test_every_kernel_thread_entry_point_tolerates_a_closed_loop(self):
        # round 5 (D3): every call the kernel thread can make on a session whose loop asyncio.run has closed returns
        # instead of raising RuntimeError('Event loop is closed'), and the ones that report an outcome report False
        # (nothing ran on the closed loop). request_reconnect first: shutdown sets `ended`, which it returns on.
        d = tempfile.mkdtemp()
        be = _backend(d)
        s = sb.SdkSession(be, _reg(d, self.SID))
        loop = asyncio.new_event_loop()
        fut = loop.create_future()          # a live ask, waiting
        loop.close()
        s.loop, s._input_wake, s.client = loop, asyncio.Event(), object()
        s._cur_ask_fut = fut
        with s._sub_lock:
            s._bg_tasks["t1"] = {"toolUseId": "t1", "desc": "a watcher"}
        calls = (("request_reconnect", lambda: s.request_reconnect()),
                 ("interrupt (the control request)", lambda: s.interrupt()),
                 ("set_model_live", lambda: s.set_model_live("claude-x")),
                 ("set_mode_live", lambda: s.set_mode_live("plan")),
                 ("resolve_ask", lambda: self.assertFalse(s.resolve_ask("answer", 1), "a closed loop delivers nothing, and says so")),
                 ("refresh_usage", lambda: self.assertFalse(s.refresh_usage())),
                 ("request_stop_task", lambda: self.assertFalse(s.request_stop_task("t1"))),
                 ("request_rewind_files", lambda: self.assertFalse(s.request_rewind_files("11111111-2222-3333-4444-555555555555"))),
                 ("shutdown", lambda: s.shutdown()))
        for name, call in calls:
            with self.subTest(entry=name):
                call()          # raises nothing
        self.assertTrue(s.ended)
        self.assertFalse(sb._call_on_loop(None, lambda: None))
        self.assertFalse(sb._call_on_loop(loop, lambda: None))

    def test_a_death_that_is_not_a_cut_never_reads_the_scope(self):
        # round 5 (tests-1): the pre-pop scope read is gated on `cut` (a mid-turn death that is not a user interrupt and
        # not our own shutdown). A user interrupt's death, an idle exit and an ended (drained) session run neither
        # systemctl nor journalctl, log no scope-result line and seal nothing; an unconditional read left every module
        # green before this test
        for label, inflight, interrupted, ended in (("user interrupt", 1, True, False), ("idle exit", 0, False, False),
                                                    ("ended", 1, False, True)):
            with self.subTest(death=label):
                d = tempfile.mkdtemp()
                be = _backend(d)
                be.cli_scope = True
                logs = []
                be._log_cb = logs.append
                calls = []

                def fake_run(argv, **kw):
                    calls.append(list(argv))
                    return mock.Mock(returncode=0, stdout=self._show(load="not-found", cgroup=""), stderr="")
                s = self._dead_session(be, d, inflight=inflight, interrupted=interrupted, exit_code=self.KILL, baseline=0)
                s.ended = ended
                with mock.patch.object(sb.subprocess, "run", fake_run), mock.patch.object(be, "_ensure") as ens:
                    be._on_session_gone(s)
                self.assertEqual(calls, [], "a non-cut death ran the scope read: %r" % calls)
                self.assertFalse(any("session scope result" in m for m in logs), logs)
                ens.assert_not_called()
                if not ended:
                    self.assertEqual(sb.last_state_value(Path(d), self.SID), "waiting")
                self.assertFalse(getattr(s, "_queue_sealed", False), "the mirror is sealed on a cut only")

    def test_a_direct_heal_call_reads_the_scope_itself(self):
        # round 5 (tests-2): _heal_cut_session's _UNREAD default hands a caller that did not read the scope (the only
        # direct caller in the tree is a test) the read here, with the scopes on; the `oom = None` mutant left every
        # module green before this test
        d = tempfile.mkdtemp()
        be = _backend(d)
        be.cli_scope = True
        logs = []
        be._log_cb = logs.append
        root = tempfile.mkdtemp()
        Path(root, "fx.slice", self.UNIT).mkdir(parents=True)
        Path(root, "fx.slice", self.UNIT, "memory.events").write_text(self.EVENTS(1))
        calls = []

        def fake_run(argv, **kw):
            calls.append(list(argv))
            return mock.Mock(returncode=0, stdout=self._show(), stderr="")
        s = self._dead_session(be, d, exit_code=self.KILL, baseline=0)
        with mock.patch.object(sb.subprocess, "run", fake_run), mock.patch.object(sb, "CGROUP_ROOT", root), \
             mock.patch.object(be, "_ensure") as ens:
            be._heal_cut_session(s)
        self.assertEqual(calls, [self.SHOW_ARGV], "the direct caller's heal read the scope itself")
        self.assertEqual(sb.read_reg(Path(d), self.SID).get("queue"), [sb.CRASH_RESUME_NUDGE_OOM])
        self.assertIn("the OOM killer took a process in its scope", self._died_line(logs))
        ens.assert_called_once_with(self.SID)

    def test_the_three_forms_share_the_lead_and_the_bare_one_is_unchanged(self):
        # CRASH_RESUME_NUDGE is what every existing reader matched on: its text is the same to the byte
        self.assertEqual(sb.CRASH_RESUME_NUDGE,
                         "<!-- romp-injected --><!-- romp-system -->[romp] This session's claude process died mid-turn "
                         "(killed or crashed); the session has been resumed with its history intact. If the conversation "
                         "tail shows '[Request interrupted by user]', that record came from this cut, not from the user: "
                         "nobody asked you to stop. Re-read the tail of the conversation and pick the work back up where "
                         "it stopped, without asking whether to continue.")
        lead = "<!-- romp-injected --><!-- romp-system -->[romp] This session's claude process died mid-turn"
        for text in (sb.CRASH_RESUME_NUDGE, sb.CRASH_RESUME_NUDGE_OOM, sb.CRASH_RESUME_NUDGE_KILLED):
            self.assertTrue(text.startswith(lead))
            self.assertTrue(sb.is_crash_resume_nudge(text) and sb.is_resume_nudge(text))
            self.assertIn("nobody asked you to stop", text)
        self.assertFalse(sb.is_crash_resume_nudge(sb.BOOT_RESUME_NUDGE))
        self.assertFalse(sb.is_crash_resume_nudge(lead[:-5] + "different"))
        self.assertFalse(sb.is_crash_resume_nudge(None))
        # the two cause-bearing forms speak as the person: the cause in plain words, no tracking vocabulary and
        # none of the mechanics (round 4, tests-2: the killed form is checked too)
        for name, text in (("oom", sb.CRASH_RESUME_NUDGE_OOM), ("killed", sb.CRASH_RESUME_NUDGE_KILLED)):
            with self.subTest(form=name):
                for word in ("card", "board", "goal", "nudge", "scope", "cgroup", "systemd", "unit"):
                    self.assertNotIn(word, text.split("[romp]", 1)[1].lower(), word)

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

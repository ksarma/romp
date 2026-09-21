#!/usr/bin/env python3
"""The rename ping (the user 2026-08-24; settle-boundary form 2026-08-25 pm): a renamed session
hears its OWN new name — rename() stamps the reg (renameNote, restart-proof, ONLY when prior turns
exist under the old name), and the ping delivers at a turn's SETTLE as its own machine-dressed
turn. The enqueue-AHEAD form folded: the CLI batches every message that arrives before a turn
starts into ONE user record, so the user's own words rendered inside the ping's machine bubble
(the 2026-08-25 screenshot: one romp-badged bubble holding the ping + the user's reply-quote +
their whole message). Three gates make that fold unreachable: settle-only delivery (the user is
answered first), the empty-queue guard (a queued message would share the pre-turn window), and the
drain's feed-hold until the ping's turn streams its first message — an exact event — after which a
racing send lands mid-turn as its own record by the CLI's own design. Voice pinned in
test_injected_voice.py. Deterministic: reg-level + a stub session, no real claude processes."""
import contextlib
import io
import os
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from romp_load import load_source
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = load_source("romp_sdk_backend_renameping", os.path.join(BIN, "romp_sdk_backend.py"))
# the kernel, loaded as tests/test_session_emoji.py loads it (the event model and the judge first, no browser open, a
# serve token set), under a name private to this module: the pins that drive the kernel's rename door against this
# module's backend (fork PR #813, round 6 of the review, eighteenth commit) need Sessions.backend_for, _rename_claimed,
# _UNOWNED and _NAMES_LOCK, the kernel's own, and its singleton slot for the backend
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "test-token-DO-NOT-USE")
km = load_source("romp_kernel_renameping", os.path.join(BIN, "romp-kernel"))

SID = "aaaaaaaa-1111-2222-3333-444444444444"
SRC = open(os.path.join(BIN, "romp_sdk_backend.py")).read()


def _backend(d):
    return sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda *a, **k: None)


@contextlib.contextmanager
def _disk_full(nf):
    """ENOSPC beneath the REAL names writer: the publish (os.replace onto names/<sid>) fails, and an
    in-place write to that file does what ENOSPC does to one — truncates, then fails. Every other path
    proceeds, so only the writer under test, and any restore aimed at its file, feel the full disk."""
    want = os.path.realpath(str(nf))
    real_replace, real_wb = os.replace, Path.write_bytes

    def replace(src, dst, *a, **k):
        if os.path.realpath(str(dst)) == want:
            raise OSError(28, "No space left on device")
        return real_replace(src, dst, *a, **k)

    def write_bytes(self, data, *a, **k):
        if os.path.realpath(str(self)) == want:
            open(self, "w").close()
            raise OSError(28, "No space left on device")
        return real_wb(self, data, *a, **k)
    with mock.patch.object(os, "replace", replace), mock.patch.object(Path, "write_bytes", write_bytes):
        yield


class RenamePing(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.be = _backend(self.td.name)
        (Path(self.td.name) / "names").mkdir(parents=True, exist_ok=True)
        self.cwd = str(Path(self.td.name) / "proj")
        Path(self.cwd).mkdir()
        sb.write_reg(Path(self.td.name), SID, {"sid": SID, "name": "web", "cwd": self.cwd,
                                               "lastSid": SID})

    def tearDown(self):
        self.td.cleanup()

    def _write_history(self):
        # one prior turn under the old name — the transcript IS the record of prior turns
        tp = Path(sb.transcript_path(self.cwd, SID))
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_text('{"type": "user", "uuid": "u1"}\n')

    def test_rename_with_history_stamps_the_pending_note_beside_the_name(self):
        self._write_history()
        self.assertTrue(self.be.rename(SID, "tests"))
        reg = sb.read_reg(Path(self.td.name), SID)
        self.assertEqual(reg.get("name"), "tests")
        self.assertEqual(reg.get("renameNote"), "tests",
                         "reg-persisted, so the ping survives a kernel restart unspoken")

    def test_rename_before_the_first_turn_pings_nothing(self):
        # the 2026-08-25 sighting's second half: a brand-new session has no stale self-knowledge
        # to correct — it learns its name the normal way, and its user's first words stay first
        self.assertTrue(self.be.rename(SID, "tests"))
        reg = sb.read_reg(Path(self.td.name), SID)
        self.assertEqual(reg.get("name"), "tests", "the rename itself still lands")
        self.assertIsNone(reg.get("renameNote"), "…but no ping is owed")

    def test_rename_of_an_unknown_sid_stamps_nothing(self):
        self.assertFalse(self.be.rename("99999999-0000-1111-2222-333333333333", "tests"))

    class _StubSession:
        def __init__(self, sid, pending=()):
            import threading
            self.sid = sid
            self._lock = threading.Lock()
            self._pending = list(pending)
            self.sent = []

        def enqueue(self, text):
            self.sent.append(text)

        def enqueue_if_empty(self, text):
            # the real session's atomic gate: emptiness check + append under ONE lock hold
            with self._lock:
                if self._pending:
                    return False
                self.enqueue(text)
                return True

    def test_settle_delivery_ships_the_dressed_ping_alone_and_once(self):
        self._write_history()
        self.be.rename(SID, "tests")
        s = self._StubSession(SID)
        self.assertTrue(self.be._deliver_rename_ping(s))
        self.assertEqual(len(s.sent), 1, "one turn of its own")
        self.assertTrue(s.sent[0].startswith(sb.RENAME_PING_HEAD), "the machine dress leads the record")
        self.assertIn("'tests'", s.sent[0], "…and it names the new name")
        self.assertIsNone(sb.read_reg(Path(self.td.name), SID).get("renameNote"), "the note is spent")
        self.assertFalse(self.be._deliver_rename_ping(s), "…and a second settle delivers nothing")

    def test_a_queued_turn_holds_the_note_for_a_later_settle(self):
        # the empty-queue guard: a queued message would share the ping's pre-turn window, which is
        # exactly the fold that put the user's words in the machine bubble
        self._write_history()
        self.be.rename(SID, "tests")
        s = self._StubSession(SID, pending=["already queued"])
        self.assertFalse(self.be._deliver_rename_ping(s))
        self.assertEqual(s.sent, [], "nothing fed beside a queued turn")
        self.assertEqual(sb.read_reg(Path(self.td.name), SID).get("renameNote"), "tests",
                         "the note survives for a later, empty-queue settle")

    def test_a_rename_landing_inside_the_pings_spend_keeps_the_newer_note(self):
        # THE SPEND IS A COMPARE-AND-SWAP (fork PR #813, round 6 of the review, fourteenth commit): a rename to 'later' lands
        # between the ping's read of the note ('tests') and its spend. Until this commit the spend wrote None over 'later',
        # so the session never heard the name it now wears while the rename's caller was told True: the rename's name
        # stood, its ping alone was lost. Now the spend finds the record holding a note it did not deliver, leaves it,
        # logs once, and the next settle delivers 'later' and spends it. Red before: renameNote None after the first settle.
        self._write_history()
        logs = []
        self.be = sb.SdkBackend(self.td.name, "/bin/true", lambda *a, **k: None, log=logs.append)
        self.assertTrue(self.be.rename(SID, "tests"))
        be = self.be

        class _Racing(self._StubSession):
            def enqueue_if_empty(me, text):        # the rename lands after the note was read and before it is spent
                ok = super().enqueue_if_empty(text)
                assert be.rename(SID, "later")
                return ok
        s = _Racing(SID)
        self.assertTrue(self.be._deliver_rename_ping(s), "the ping for 'tests' was delivered")
        self.assertEqual(len(s.sent), 1, "one turn of its own")
        self.assertIn("'tests'", s.sent[0], "the ping names the note it read")
        self.assertEqual(sb.read_reg(Path(self.td.name), SID).get("renameNote"), "later",
                         "the newer note stands: the spend found the record no longer holding 'tests'")
        moved = [m for m in logs if "rename ping" in m and "stands for a later settle" in m]
        self.assertEqual(len(moved), 1, "one log line names the note that stands: %r" % (logs,))
        self.assertIn("'later'", moved[0])
        self.assertIn("'tests'", moved[0])
        s2 = self._StubSession(SID)
        self.assertTrue(self.be._deliver_rename_ping(s2), "the next settle delivers the newer note")
        self.assertIn("'later'", s2.sent[0])
        self.assertIsNone(sb.read_reg(Path(self.td.name), SID).get("renameNote"), "and spends it")
        self.assertEqual([m for m in logs if "rename ping" in m], moved, "the plain spend logs nothing: %r" % (logs,))

    def test_a_send_racing_the_gate_cannot_queue_ahead_of_the_ping(self):
        # the gate's TOCTOU (found 2026-08-26): the empty-queue check and the ping's enqueue held
        # the session lock SEPARATELY, with the renameNote reg write between them — a send landing
        # in that window queued AHEAD of the ping, and the CLI's pre-turn batching folded the
        # user's words into the ping's machine record (the exact 2026-08-25 fold the gate exists
        # to prevent). Deterministic interleave: the reg write IS the window, so a hook there
        # plays the racing send. A real (unstarted) session — the race is in its lock discipline.
        self._write_history()
        self.be.rename(SID, "tests")
        s = sb.SdkSession(self.be, {"sid": SID, "name": "web", "cwd": self.cwd,
                                    "mode": "acceptEdits"})
        orig, raced = self.be._update_reg_if_holds, []       # the spend's writer (the compare-and-swap since the fourteenth commit)

        def racing_update(sid, expect, fields):
            if "renameNote" in fields and not raced:
                raced.append(True)
                s.enqueue("the user's own racing words")   # a concurrent send() in the window
            return orig(sid, expect, fields)

        self.be._update_reg_if_holds = racing_update
        try:
            delivered = self.be._deliver_rename_ping(s)
        finally:
            self.be._update_reg_if_holds = orig
        pending = s.pending()
        if delivered:
            self.assertTrue(pending and pending[0].startswith(sb.RENAME_PING_HEAD),
                            "a racing send must never queue AHEAD of the ping — that is the fold")
            self.assertIn("the user's own racing words", pending,
                          "…and the racing send itself is queued behind it, not lost")
        else:
            self.assertEqual(sb.read_reg(Path(self.td.name), SID).get("renameNote"), "tests",
                             "an undelivered ping keeps its note for a later settle")

    def test_the_fold_gates_are_pinned_at_source(self):
        # the fold's mechanics live in async plumbing a unit test can't drive — pin the three gates
        self.assertNotIn("RENAME_NUDGE % _reg", SRC, "no send()-time delivery of any form remains")
        self.assertNotIn('text = "%s\\n\\n%s" % (RENAME_NUDGE', SRC, "the string-prepend form stays gone")
        self.assertIn("self.backend._deliver_rename_ping(self)", SRC, "delivery hooks the turn's settle")
        self.assertIn("blocked = blocked or self._ping_feeding", SRC,
                      "the drain holds every feed while the ping's turn has not started")
        self.assertIn("if item.startswith(RENAME_PING_HEAD):", SRC, "…armed exactly when a ping is fed")
        self.assertIn("self._ping_feeding = False   # a reconnect restarts the feed", SRC,
                      "…and a reconnect clears a stale hold instead of wedging the queue")
        self.assertNotIn("romp-injected", sb.RENAME_NUDGE,
                         "the constant stays bare prose; the dress is added only on the separate record")


class NamesWriteFailure(unittest.TestCase):
    """rename() moves the durable registry FIRST, then the shared names/<sid> identity file through
    write_name — tmp + os.replace, so a raise from it leaves names/<sid> exactly as it was. What a raise
    USED to leave: the registry holding the new name (and a renameNote the rename stamped), the writer's
    temp beside the file (the names scanners read the dir: a phantom session), and the exception
    escaping with no compensation. Now the temp is gone, the registry write is re-run with the old
    fields, the in-memory name never moves, and the exception still reaches the caller — with
    deliberately NO restore write: an in-place rewrite would be the one non-atomic write on the path,
    and under ENOSPC it truncates the very file it means to save, which is what _disk_full models
    (2026-09-08). Synthetic: placeholder sid, the demo names."""

    class _Live:
        name = "web"

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.be = _backend(self.td.name)
        self.cwd = str(self.root / "proj")
        Path(self.cwd).mkdir()
        (self.root / "names").mkdir()
        self.nf = self.root / "names" / SID
        self.line = "web\t%s\t#112233\t#ffffff\n" % self.cwd
        self.nf.write_text(self.line)
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "cwd": self.cwd, "lastSid": SID})
        tp = Path(sb.transcript_path(self.cwd, SID))          # prior turns: the rename also stamps
        tp.parent.mkdir(parents=True, exist_ok=True)         # renameNote, which must come back out
        tp.write_text('{"type": "user", "uuid": "u1"}\n')
        self.before = sb.read_reg(self.root, SID)
        self.live = self._Live()
        self.be.sessions[SID] = self.live

    def tearDown(self):
        self.td.cleanup()

    def test_a_failed_publish_leaves_every_store_as_it_was(self):
        # on origin/main: the writer's temp stayed beside the file and the registry moved to
        # {'name': 'tests', 'renameNote': 'tests'}
        with _disk_full(self.nf):
            with self.assertRaises(OSError):
                self.be.rename(SID, "tests")
        self.assertEqual(self.nf.read_text(), self.line,
                         "names/<sid> byte-identical: the writer is atomic and nothing rewrote it in place")
        self.assertEqual(sorted(p.name for p in self.nf.parent.iterdir()), [SID], "the writer's temp is gone")
        self.assertEqual(sb.read_reg(self.root, SID), self.before,
                         "the registry keeps its old fields — no new name, no renameNote")
        self.assertEqual(self.live.name, "web", "the in-memory name never moved")

    def test_a_failed_first_publish_leaves_nothing_behind(self):
        # on origin/main: the writer's temp stayed as the only thing in names/
        self.nf.unlink()                                      # a row predating the names write
        with _disk_full(self.nf):
            with self.assertRaises(OSError):
                self.be.rename(SID, "tests")
        self.assertEqual(sorted(p.name for p in self.nf.parent.iterdir()), [],
                         "neither names/<sid> nor its temp exists: a failed rename publishes nothing")
        self.assertEqual(sb.read_reg(self.root, SID), self.before)
        self.assertEqual(self.live.name, "web")

    def test_a_landing_write_still_moves_all_three_stores(self):
        # the control: with the write landing, the registry, the file and the live name all move
        self.assertTrue(self.be.rename(SID, "tests"))
        self.assertEqual(sb.read_reg(self.root, SID).get("name"), "tests")
        self.assertEqual(self.nf.read_text(), "tests\t%s\t#112233\t#ffffff\n" % self.cwd, "colours preserved")
        self.assertEqual(self.live.name, "tests")


class ConcurrentRenameInsideAFailingWindow(unittest.TestCase):
    """rename()'s compensation is a RESTORE SITE (fork PR #813, round 6 of the review, tenth commit, 2026-09-21): after
    the names write raises it puts the record's `name`, and the `renameNote` it stamped, back from the read it
    took at its door. The ninth commit's rule for every such site holds here too: a field goes back ONLY while it
    still holds what the step put there; a value another writer put there meanwhile stands. Driven with a
    real second thread: rename A (alpha) has written its record and is inside write_name when rename B (beta)
    lands whole (record, names file, live name) and answers True; A's names write then faults. Before the tenth
    commit A's compensation wrote the door-time name (web) over B's and dropped B's note, so B's caller was
    told applied while the record, which a restart applies, said web and the names file and the live object
    said beta: a write lost under a false success. Now the record keeps beta and B's note, A's caller still
    hears the raise, and the log names the newer name that stands. The control (nobody wrote meanwhile: the
    record goes back and the note is dropped) is NamesWriteFailure above. THE SAME NAME (the twelfth commit, the
    round's own verifiers' second pass): when B lands the SAME name alpha, a compare by value cannot tell B's
    alpha from A's, and the tenth commit's compensation put web back over B's landed rename with no log line.
    A never wrote names/<sid> (write_name is tmp + os.replace and raised), so a names file reading alpha at
    compensation time, which read web at A's door, was written by another caller: the compensation stands down
    and says so. THE DOOR'S READ ORDER (the thirteenth commit, the round's own verifiers' third pass): the twelfth
    commit read names/<sid> after the door's record read, so a same-name B landing whole between those two reads
    left the door's names read already saying alpha, no evidence, and the compare put web back over B's landed
    rename with no log line; the names read is the door's first read now. THE RECORD WRITE (the fourteenth commit, the
    round's own verifiers' fourth pass): a rename B to a DIFFERENT name landing whole between A's door read and A's record
    write was written over by A's record write and then, when A's names write faulted, "compensated" back to the door-time
    name: the record read web while the names file and the live name read beta, nothing logged, B's caller told True (the
    verifiers' drive; reachable through the rename door, which claims each name apart). The record write is a compare-and-
    swap on the door-time name now (_update_reg_if_holds): a record whose name moved refuses the rename (RenameRefused,
    the sentence naming the pick that landed, one log line, nothing written, no compensation), and what a failed publish
    puts back is what the write itself replaced, read in the same locked hold. THE HOLD (the fifteenth commit, the round's
    own verifiers' fourth pass on the fourteenth commit): the compare-and-swap left the names write and the live set outside the lock, so a rename B
    whose door read was A's LANDED record write passed its own compare while A was inside its names write, landed whole
    and answered True, and then A's names write and live set landed over B's: the record beta, the names file (the roster
    every listing reads) and the live name alpha, both callers told applied, nothing logged (the verifiers' drive). rename
    now holds _reg_lock from its compare-and-swap through its names write and live set, and through the compensation when
    the names write raises, so a rename arriving inside another's window WAITS on the hold: it lands after a rename that
    published, and is refused after one that put the record back (its door read was the unlanded write; the sentence
    names the name that stands). The tenth and twelfth commits' drives, B landing whole while A is inside its names write,
    are shapes this code no longer reaches; the two "waits" pins below replace them. Synthetic: placeholder sid, demo
    names, a one-line transcript."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.logs = []
        self.be = sb.SdkBackend(self.td.name, "/bin/true", lambda *a, **k: None, log=self.logs.append)
        self.cwd = str(self.root / "proj")
        Path(self.cwd).mkdir()
        (self.root / "names").mkdir()
        self.nf = self.root / "names" / SID
        self.nf.write_text("web\t%s\t#112233\t#ffffff\n" % self.cwd)
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "cwd": self.cwd, "lastSid": SID})
        tp = Path(sb.transcript_path(self.cwd, SID))          # prior turns: both renames stamp a note
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_text('{"type": "user", "uuid": "u1"}\n')
        self.live = NamesWriteFailure._Live()
        self.be.sessions[SID] = self.live

    def tearDown(self):
        self.td.cleanup()

    def _stores(self):
        reg = sb.read_reg(self.root, SID)
        return (reg.get("name"), reg.get("renameNote"), self.nf.read_text().split("\t")[0], self.live.name)

    def _held_after_door_read(self, name, inside, at_hold=("web", None, "web", "web")):
        """Rename A to `name` on a second thread, held right after its door's RECORD read returns (read_reg patched by thread
        identity, on A's first call); `inside` runs on this thread while A is held; then A resumes. Every write_reg and
        write_name call is recorded with the calling thread's name, so a pin can say which thread wrote what. `at_hold` is
        what the four stores must read while A is held (A has written nothing yet). Returns (A's outcome: its return
        value, or (exception type name, str(exception))), inside's return value, the record writes as (thread, name field)
        pairs, the names writes as (thread, name) pairs)."""
        real_read, real_write_reg, real_write_name = sb.read_reg, sb.write_reg, sb.write_name
        a_read_done, go, holder, a_reads, reg_writes, names_writes = threading.Event(), threading.Event(), {}, [], [], []

        def read_reg(state_dir, sid):
            reg = real_read(state_dir, sid)
            if threading.current_thread() is holder.get("a"):
                a_reads.append(sid)
                if len(a_reads) == 1:                              # A's door read: hold here until inside() has run
                    a_read_done.set()
                    go.wait(10)
            return reg

        def write_reg(state_dir, sid, reg):
            reg_writes.append((threading.current_thread().name, reg.get("name")))
            return real_write_reg(state_dir, sid, reg)

        def write_name(state_dir, sid, nm, *a, **k):
            names_writes.append((threading.current_thread().name, nm))
            return real_write_name(state_dir, sid, nm, *a, **k)

        outcome = {}

        def first():
            try:
                outcome["a"] = self.be.rename(SID, name)
            except BaseException as e:                            # noqa: BLE001 (the drive records whatever escapes)
                outcome["a"] = (type(e).__name__, str(e))

        t = holder["a"] = threading.Thread(target=first, name="rename-a")
        with mock.patch.object(sb, "read_reg", read_reg), mock.patch.object(sb, "write_reg", write_reg), \
                mock.patch.object(sb, "write_name", write_name):
            t.start()
            self.assertTrue(a_read_done.wait(10), "rename A returned from its door's record read")
            self.assertEqual(self._stores(), at_hold, "A has written nothing yet")
            got = inside()
            go.set()
            t.join(10)
        self.assertFalse(t.is_alive(), "rename A returned")
        return outcome.get("a"), got, reg_writes, names_writes

    def test_a_rename_to_another_name_landing_between_the_doors_reads_is_refused_at_the_record_write(self):
        # THE FOURTEENTH COMMIT'S DEFECT (the round's own verifiers' fourth pass). Rename A to alpha is held right after its
        # door's record read; rename B to beta lands whole (record, names file, live name) and answers True; A resumes. At the
        # thirteenth commit A's record write landed over B's, A's names write faulted, and the compensation, comparing by
        # value against alpha, put the door-time web back: the record read ('web', None) while the names file and the live
        # name read beta, with no log line, so B's rename was gone from the one store a restart applies, under a false
        # success. Now the record write is a compare-and-swap on the door-time name: the record holds beta, not web, so A
        # refuses before writing anything, its sentence names beta, one log line says so, and nothing is compensated. A's
        # names write is modelled to fault for parity with the thirteenth commit's drive; A never reaches it.
        def b_lands():
            return self.be.rename(SID, "beta")
        real = sb.write_name

        def faulting_for_a(state_dir, sid, nm, *a, **k):
            if threading.current_thread().name == "rename-a":
                raise OSError(28, "No space left on device")
            return real(state_dir, sid, nm, *a, **k)
        with mock.patch.object(sb, "write_name", faulting_for_a):
            a, b, reg_writes, names_writes = self._held_after_door_read("alpha", b_lands)
        self.assertTrue(b, "B was told applied")
        self.assertEqual(self._stores(), ("beta", "beta", "beta", "beta"),
                         "B's rename stands on the record, the names file and the live name (red before the fourteenth "
                         "commit: the record read ('web', None) under B's True, with no log line)")
        refused = [m for m in self.logs if "rename" in m and "refused" in m]
        self.assertEqual(len(refused), 1, "exactly one log line says the write was refused: %r" % (self.logs,))
        self.assertEqual(a[0] if isinstance(a, tuple) else a, "RenameRefused", "A hears the refusal: %r" % (a,))
        self.assertIn("'beta'", a[1], "the sentence names the pick another caller landed: %r" % (a[1],))
        self.assertIn("'alpha'", a[1], "and the rename it refused")
        self.assertEqual([w for w in reg_writes if w[0] == "rename-a"], [], "A wrote no record: %r" % (reg_writes,))
        self.assertEqual([w for w in names_writes if w[0] == "rename-a"], [], "A never reached its names write")
        for word in ("'web'", "'alpha'", "'beta'"):
            self.assertIn(word, refused[0], "the log line names the door's read, the refused pick and the landed one")
        self.assertEqual([m for m in self.logs if "compensation" in m or "stood down" in m or "is not put back" in m], [],
                         "no compensation ran, since nothing was written: %r" % (self.logs,))

    def test_a_note_spent_inside_a_failing_renames_window_is_not_re_armed_by_the_put_back(self):
        # THE PUT-BACK'S SOURCE (the fourteenth commit): what a failed publish puts back is what the record write itself
        # REPLACED, read in the same locked hold (_update_reg_if_holds's `replaced`), not the door-time read. The record
        # carries an older note ('old', a ping not yet delivered) at A's door; the ping is delivered and spent (renameNote
        # None) while A is held after its door read; A resumes, its compare-and-swap on the name passes (web is what it
        # read), it writes alpha and its own note, and its names write faults. The compensation drops A's note back to the
        # spent None. Put back from the door-time read it would re-arm 'old', and the next settle would ping a rename that
        # had already been announced: a spent write undone. The name goes back to web either way.
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "cwd": self.cwd, "lastSid": SID, "renameNote": "old"})
        real = sb.write_name

        def faulting_for_a(state_dir, sid, nm, *a, **k):
            if threading.current_thread().name == "rename-a":
                raise OSError(28, "No space left on device")
            return real(state_dir, sid, nm, *a, **k)

        def spend():
            return self.be._update_reg_if_holds(SID, {"renameNote": "old"}, {"renameNote": None})[0]
        with mock.patch.object(sb, "write_name", faulting_for_a):
            a, spent, reg_writes, _ = self._held_after_door_read("alpha", spend, at_hold=("web", "old", "web", "web"))
        self.assertEqual(spent, "written", "the ping's spend landed inside A's window")
        self.assertEqual(a, ("OSError", "[Errno 28] No space left on device"), "A hears its raise")
        reg = sb.read_reg(self.root, SID)
        self.assertEqual((reg.get("name"), "renameNote" in reg, reg.get("renameNote")), ("web", True, None),
                         "the name went back; the note went back to the spent None, not to the door-time 'old'")
        self.assertEqual([w for w in reg_writes if w[0] == "rename-a"], [("rename-a", "alpha"), ("rename-a", "web")],
                         "A's two record writes: the compare-and-swap and the put-back: %r" % (reg_writes,))
        self.assertEqual([m for m in self.logs if "rename" in m], [], "every key went back; nothing to log: %r" % (self.logs,))

    def test_a_names_file_already_reading_the_new_name_at_the_door_is_no_evidence_and_the_compare_runs(self):
        # THE DISTINGUISHER'S GUARD (the round's own verifiers' fourth pass, a non-red mutant at the thirteenth commit): the
        # stand-down fires only when the names file reads the new name NOW and did NOT at the door. Here the file already
        # reads alpha at A's door (the tenth commit's opposite-order residual: the record says web, the file alpha, a
        # disagreement that predates this rename), A renames to alpha with NOBODY else writing, and its names write faults.
        # The file reading alpha is no evidence of another caller, so the compare runs and the record goes back to the
        # door-time name with no stand-down line. Dropping the door-time clause from the stand-down's condition turns this
        # into a false stand-down: the record keeps alpha, a rename the caller was told FAILED applies at the next restart
        # (the 2026-09-08 shape), and the module stayed green until this pin.
        self.nf.write_text("alpha\t%s\t#112233\t#ffffff\n" % self.cwd)

        def write_name(*a, **k):
            raise OSError(28, "No space left on device")
        with mock.patch.object(sb, "write_name", write_name):
            with self.assertRaises(OSError):
                self.be.rename(SID, "alpha")
        self.assertEqual(self._stores(), ("web", None, "alpha", "web"),
                         "the compare ran and put the door-time name back; the names file is as it was; the live name never moved")
        self.assertEqual([m for m in self.logs if "stood down" in m], [], "no stand-down line: %r" % (self.logs,))
        self.assertEqual([m for m in self.logs if "rename" in m], [],
                         "every key went back, so the compensation logged nothing: %r" % (self.logs,))

    def test_a_same_name_rename_landing_between_the_names_read_and_the_record_read_is_stood_down_for(self):
        # THE READ ORDER'S PIN (the thirteenth commit's fix, re-pinned at the fourteenth): rename A is held right after its
        # door's NAMES read returns (Path.read_text patched by thread identity, on A's first call), rename B to the same name
        # alpha lands whole and answers True, then A resumes: its record read now says alpha, its compare-and-swap passes
        # (alpha is what it read), its record write replaces alpha with alpha, and its names write faults. The compensation
        # finds the names file reading alpha, which it did not at the door (web, the door's FIRST read), and stands down with
        # one log line. With the names read behind the record read the door would have read alpha, no evidence, and the
        # compare would have run silently: the record stays right either way since the fourteenth commit (the put-back is
        # the pre-image the write replaced, alpha), so this pin is what tells the two read orders apart.
        real_read_text, real_write_name = Path.read_text, sb.write_name
        a_names_read, b_done, holder, a_reads = threading.Event(), threading.Event(), {}, []

        def read_text(p, *a, **k):
            out = real_read_text(p, *a, **k)
            if threading.current_thread() is holder.get("a") and p.name == SID and p.parent.name == "names":
                a_reads.append(str(p))
                if len(a_reads) == 1:                              # A's door names read: hold until B has landed whole
                    a_names_read.set()
                    b_done.wait(10)
            return out

        def write_name(state_dir, sid, nm, *a, **k):
            if threading.current_thread() is holder.get("a"):
                raise OSError(28, "No space left on device")
            return real_write_name(state_dir, sid, nm, *a, **k)

        outcome = {}

        def first():
            try:
                outcome["a"] = self.be.rename(SID, "alpha")
            except BaseException as e:                            # noqa: BLE001
                outcome["a"] = (type(e).__name__, getattr(e, "errno", None))

        t = holder["a"] = threading.Thread(target=first, name="rename-a")
        with mock.patch.object(Path, "read_text", read_text), mock.patch.object(sb, "write_name", write_name):
            t.start()
            self.assertTrue(a_names_read.wait(10), "rename A returned from its door's names read")
            self.assertEqual(self._stores(), ("web", None, "web", "web"), "A has written nothing yet")
            answered = self.be.rename(SID, "alpha")
            b_done.set()
            t.join(10)
        self.assertFalse(t.is_alive(), "rename A returned")
        self.assertEqual((answered, outcome.get("a")), (True, ("OSError", 28)), "B was told applied; A still hears its raise")
        self.assertEqual(self._stores(), ("alpha", "alpha", "alpha", "alpha"), "B's rename stands on every store")
        stood = [m for m in self.logs if "rename" in m and "stood down" in m]
        self.assertEqual(len(stood), 1, "one log line says the compensation stood down: %r" % (self.logs,))
        self.assertIn("another caller landed the same name", stood[0])
        self.assertEqual([m for m in self.logs if "refused" in m or "compensation failed" in m or "is not put back" in m], [],
                         "no other verdict is logged: %r" % (self.logs,))

    def _b_arrives_while_a_holds(self, a_name, b_name, a_faults):
        """Rename A to `a_name` on a second thread, held INSIDE its names write (write_name patched by thread identity) with
        its record written and _reg_lock held; rename B to `b_name` starts on a third thread while A is held and is given
        0.3 s; then A resumes (its names write raises when `a_faults`, else lands) and both are joined. B's door reads run
        outside the lock and see A's record write; B's compare-and-swap then waits on the hold. Returns (A's outcome, B's
        outcome, whether B was still running when A resumed, the record writes as (thread, name field) pairs, the names
        writes as (thread, name) pairs, the four stores read while A was held). An outcome is the return value, or
        (exception type name, the sentence for a RenameRefused and the errno otherwise). The 0.3 s is a bound on a
        negative (B did not return), not the pin: the pin is the ORDER of the writes, A's before all of B's, which the
        hold decides and a bare lock-free window inverts."""
        real_write_name, real_write_reg = sb.write_name, sb.write_reg
        a_in, go, holder, reg_writes, names_writes = threading.Event(), threading.Event(), {}, [], []

        def write_name(state_dir, sid, nm, *a, **k):
            names_writes.append((threading.current_thread().name, nm))
            if threading.current_thread() is holder.get("a"):
                a_in.set()
                go.wait(10)
                if a_faults:
                    raise OSError(28, "No space left on device")
            return real_write_name(state_dir, sid, nm, *a, **k)

        def write_reg(state_dir, sid, reg):
            reg_writes.append((threading.current_thread().name, reg.get("name")))
            return real_write_reg(state_dir, sid, reg)

        outcome = {}

        def run(key, name):
            try:
                outcome[key] = self.be.rename(SID, name)
            except sb.RenameRefused as e:
                outcome[key] = ("RenameRefused", str(e))
            except BaseException as e:                            # noqa: BLE001 (the drive records whatever escapes)
                outcome[key] = (type(e).__name__, getattr(e, "errno", None))

        ta = holder["a"] = threading.Thread(target=run, args=("a", a_name), name="rename-a")
        tb = threading.Thread(target=run, args=("b", b_name), name="rename-b")
        with mock.patch.object(sb, "write_name", write_name), mock.patch.object(sb, "write_reg", write_reg):
            ta.start()
            self.assertTrue(a_in.wait(10), "rename A reached its names write with its record written")
            at_hold = self._stores()
            tb.start()
            tb.join(0.3)
            b_waiting = tb.is_alive()
            go.set()
            ta.join(10)
            tb.join(10)
        self.assertFalse(ta.is_alive() or tb.is_alive(), "both renames returned")
        return outcome.get("a"), outcome.get("b"), b_waiting, reg_writes, names_writes, at_hold

    def test_a_rename_arriving_while_a_landing_rename_holds_the_lock_waits_and_lands_after_it(self):
        # THE FIFTEENTH COMMIT'S DEFECT (the round's own verifiers' fourth pass on the fourteenth commit, F1): rename A to alpha has written its record
        # and is inside its names write; rename B to beta arrives. At the fourteenth commit B's door read was A's LANDED
        # record write, so B's compare-and-swap passed, B landed whole (record, names file, live name) and answered True,
        # and then A's names write and live set landed over B's: the record read beta while the names file and the live
        # name read alpha, both callers told applied, nothing logged. Now B waits on A's hold and lands after A has
        # published: every store reads beta, A's writes all precede B's, both callers told the truth in turn.
        a, b, b_waiting, reg_writes, names_writes, at_hold = self._b_arrives_while_a_holds("alpha", "beta", a_faults=False)
        self.assertEqual(at_hold, ("alpha", "alpha", "web", "web"), "A's record write is on disk; its names write has not landed")
        self.assertEqual((a, b), (True, True), "both told applied, in turn: %r" % ((a, b),))
        self.assertEqual(self._stores(), ("beta", "beta", "beta", "beta"),
                         "the later rename stands on every store (red before the fifteenth commit: the record beta, the names "
                         "file and the live name alpha, both callers told applied)")
        self.assertTrue(b_waiting, "B had not returned while A held the lock")
        self.assertEqual(reg_writes, [("rename-a", "alpha"), ("rename-b", "beta")], "A's record write, then B's: %r" % (reg_writes,))
        self.assertEqual(names_writes, [("rename-a", "alpha"), ("rename-b", "beta")],
                         "A's names write landed before B's began: %r" % (names_writes,))
        self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing to log: %r" % (self.logs,))

    def test_a_rename_arriving_while_a_failing_rename_holds_the_lock_waits_and_is_refused_after_the_put_back(self):
        # the tenth commit's drive, re-pinned under the hold: rename A to alpha is inside its names write, which will fault;
        # rename B to beta arrives. Until the fifteenth commit B landed whole inside A's window and A's compensation had to
        # yield to it (the tenth commit's per-field compare; before that, B's rename was put back over under a false
        # success). Now B's door read is A's record write, B waits on the hold, A's names write faults and A's compensation
        # puts the record back INSIDE the hold, and B's compare-and-swap then finds the record holding web, not the alpha
        # its door read: B is refused with a sentence naming its door read, the name that stands and its own pick, one log
        # line says so, every store reads the door-time name, and nothing applies at a restart. Nobody was told a rename
        # applied that did not.
        a, b, b_waiting, reg_writes, names_writes, at_hold = self._b_arrives_while_a_holds("alpha", "beta", a_faults=True)
        self.assertEqual(at_hold, ("alpha", "alpha", "web", "web"), "A's record write is on disk; its names write has not landed")
        self.assertEqual(a, ("OSError", 28), "A hears its raise: %r" % (a,))
        self.assertEqual(b[0] if isinstance(b, tuple) else b, "RenameRefused",
                         "B is refused after A's put-back (red before the fifteenth commit: B told True inside A's window): %r" % (b,))
        self.assertTrue(b_waiting, "B had not returned while A held the lock")
        for word in ("'alpha'", "'web'", "'beta'"):
            self.assertIn(word, b[1], "the sentence names B's door read, the name that stands and B's pick: %r" % (b[1],))
        self.assertEqual(self._stores(), ("web", None, "web", "web"), "every store reads the door-time name")
        self.assertEqual(reg_writes, [("rename-a", "alpha"), ("rename-a", "web")],
                         "A's compare-and-swap and its put-back; B wrote no record: %r" % (reg_writes,))
        self.assertEqual(names_writes, [("rename-a", "alpha")], "B never reached its names write: %r" % (names_writes,))
        refused = [m for m in self.logs if "rename" in m and "refused" in m]
        self.assertEqual(len(refused), 1, "one log line says B was refused: %r" % (self.logs,))
        self.assertIn("'alpha'", refused[0])
        self.assertIn("'web'", refused[0])
        self.assertEqual([m for m in self.logs if "compensation" in m or "stood down" in m or "is not put back" in m], [],
                         "A's compensation put every key back and logged nothing: %r" % (self.logs,))

    def test_a_same_name_rename_arriving_while_a_failing_rename_holds_the_lock_waits_and_is_refused_after_the_put_back(self):
        # the twelfth commit's drive, re-pinned under the hold: B wants the SAME name alpha. Until the fifteenth commit B
        # landed whole inside A's window and A's compensation stood down on the names file's evidence (the twelfth commit;
        # before it, web was put back over B's landed rename with no log line). Now B waits, and after A's put-back its
        # compare-and-swap finds web where its door read alpha: refused, with the sentence naming both, and every store
        # reads web. Through the rename door this shape needs a direct caller (the door answers a rename to the current
        # name as a no-op), as the helper's docstring says.
        a, b, b_waiting, reg_writes, names_writes, at_hold = self._b_arrives_while_a_holds("alpha", "alpha", a_faults=True)
        self.assertEqual(at_hold, ("alpha", "alpha", "web", "web"))
        self.assertEqual(a, ("OSError", 28), "A hears its raise: %r" % (a,))
        self.assertEqual(b[0] if isinstance(b, tuple) else b, "RenameRefused",
                         "B is refused after A's put-back (red before the fifteenth commit: B told True inside A's window): %r" % (b,))
        self.assertTrue(b_waiting, "B had not returned while A held the lock")
        self.assertIn("'alpha'", b[1])
        self.assertIn("'web'", b[1])
        self.assertEqual(self._stores(), ("web", None, "web", "web"), "every store reads the door-time name")
        self.assertEqual(reg_writes, [("rename-a", "alpha"), ("rename-a", "web")], "B wrote no record: %r" % (reg_writes,))
        self.assertEqual(names_writes, [("rename-a", "alpha")], "B never reached its names write: %r" % (names_writes,))
        self.assertEqual(len([m for m in self.logs if "rename" in m and "refused" in m]), 1, "one refused line: %r" % (self.logs,))
        self.assertEqual([m for m in self.logs if "stood down" in m or "compensation" in m], [],
                         "no stand-down: nothing landed inside the window for the compensation to yield to: %r" % (self.logs,))

    def test_the_record_write_the_names_write_and_the_live_set_are_made_under_one_hold_of_the_lock(self):
        # the property by execution: with no other writer, the three stores move in order with _reg_lock held at each write
        # (write_reg and write_name wrapped in the module, and a live object whose name setter reads the lock's state), and
        # the hold is released when rename returns. Red before the fifteenth commit: the names write and the live set with
        # the lock free.
        events, real_wr, real_wn, be = [], sb.write_reg, sb.write_name, self.be

        def write_reg(state_dir, sid, reg):
            events.append(("record", reg.get("name"), be._reg_lock.locked()))
            return real_wr(state_dir, sid, reg)

        def write_name(state_dir, sid, nm, *a, **k):
            events.append(("names", nm, be._reg_lock.locked()))
            return real_wn(state_dir, sid, nm, *a, **k)

        class _LiveRecording:
            def __init__(me):
                me._name = "web"

            @property
            def name(me):
                return me._name

            @name.setter
            def name(me, v):
                events.append(("live", v, be._reg_lock.locked()))
                me._name = v
        live = _LiveRecording()
        self.be.sessions[SID] = live
        with mock.patch.object(sb, "write_reg", write_reg), mock.patch.object(sb, "write_name", write_name):
            self.assertTrue(self.be.rename(SID, "alpha"))
        self.assertEqual(events, [("record", "alpha", True), ("names", "alpha", True), ("live", "alpha", True)],
                         "the three stores move in this order with _reg_lock held at each: %r" % (events,))
        self.assertFalse(self.be._reg_lock.locked(), "and the hold is released when rename returns")
        self.assertEqual((live.name, self.nf.read_text().split("\t")[0]), ("alpha", "alpha"))

    def test_a_same_name_rename_landing_between_the_doors_reads_is_refused_at_the_record_write(self):
        # the thirteenth commit's drive, re-pinned at the fourteenth: rename A is held right after its door's RECORD read
        # returns, rename B to the SAME name alpha lands whole and answers True, then A resumes. At the twelfth commit the
        # compare put web back over B's landed rename with no log line; at the thirteenth the compensation stood down on the
        # names file's evidence after A's record write had landed over B's and A's names write had faulted. Now the record
        # write is a compare-and-swap on the door-time name: the record holds alpha, not web, so A refuses before writing,
        # the sentence names alpha (the pick that landed, the very name A wanted), one log line says so, no compensation
        # runs and A's names write is never reached. Through the rename door this shape needs a direct caller (the door
        # answers a rename to the current name as a no-op), as the helper's docstring says.
        a, b, reg_writes, names_writes = self._held_after_door_read("alpha", lambda: self.be.rename(SID, "alpha"))
        self.assertTrue(b, "B was told applied")
        self.assertEqual(self._stores(), ("alpha", "alpha", "alpha", "alpha"),
                         "the record keeps the name and note B landed; the names file and the live name agree")
        self.assertEqual(a[0] if isinstance(a, tuple) else a, "RenameRefused", "A hears the refusal: %r" % (a,))
        self.assertIn("'alpha'", a[1], "the sentence names the pick another caller landed")
        self.assertEqual([w for w in reg_writes if w[0] == "rename-a"], [], "A wrote no record: %r" % (reg_writes,))
        self.assertEqual([w for w in names_writes if w[0] == "rename-a"], [], "A never reached its names write")
        refused = [m for m in self.logs if "rename" in m and "refused" in m]
        self.assertEqual(len(refused), 1, "one log line says the write was refused: %r" % (self.logs,))
        self.assertIn("'web'", refused[0])
        self.assertIn("'alpha'", refused[0])
        self.assertEqual([m for m in self.logs if "compensation" in m or "stood down" in m or "is not put back" in m], [],
                         "no compensation ran, since nothing was written: %r" % (self.logs,))


class RenameRecordWriteIsACompareAndSwap(unittest.TestCase):
    """rename()'s record write lands only while the record still holds the name its door read (fork PR #813, round 6 of the
    review, fourteenth commit, 2026-09-21; the round's own verifiers' fourth pass): _update_reg_if_holds compares and writes
    under _reg_lock in one hold, and rename refuses (RenameRefused carrying the sentence the caller hears, one log line,
    nothing written, nothing compensated) when the name moved, when the record is gone, and when it exists and would not
    read. The concurrent shapes are ConcurrentRenameInsideAFailingWindow's; here the plain write's property by execution
    (every record write of a rename is _update_reg_if_holds's, made with _reg_lock held, and it lands) and the two
    refusals that need no second writer. Until the fourteenth commit the write's False for the unreadable skip was never
    read: the rename moved the names file and the live name and answered True over a record that never moved. Synthetic:
    placeholder sid, demo names, a one-line transcript."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.logs = []
        self.be = sb.SdkBackend(self.td.name, "/bin/true", lambda *a, **k: None, log=self.logs.append)
        self.cwd = str(self.root / "proj")
        Path(self.cwd).mkdir()
        (self.root / "names").mkdir()
        self.nf = self.root / "names" / SID
        self.nf.write_text("web\t%s\t#112233\t#ffffff\n" % self.cwd)
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "cwd": self.cwd, "lastSid": SID})
        tp = Path(sb.transcript_path(self.cwd, SID))
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_text('{"type": "user", "uuid": "u1"}\n')
        self.regp = sb._reg_path(self.root, SID)
        self.live = NamesWriteFailure._Live()
        self.be.sessions[SID] = self.live

    def tearDown(self):
        self.td.cleanup()

    def _stores(self):
        reg = sb.read_reg(self.root, SID)
        return ((reg.get("name"), reg.get("renameNote")) if reg else None, self.nf.read_text().split("\t")[0], self.live.name)

    def _rename_with_the_record_changed_before_its_write(self, change):
        """Rename A to alpha on a second thread, held right after its door's record read returns (read_reg patched by thread
        identity, on A's first call); `change` runs on this thread against the record file; A resumes. Returns A's outcome:
        True, or (exception type name, str(exception))."""
        real_read = sb.read_reg
        a_read_done, go, holder, a_reads = threading.Event(), threading.Event(), {}, []

        def read_reg(state_dir, sid):
            reg = real_read(state_dir, sid)
            if threading.current_thread() is holder.get("a"):
                a_reads.append(sid)
                if len(a_reads) == 1:
                    a_read_done.set()
                    go.wait(10)
            return reg

        outcome = {}

        def first():
            try:
                outcome["a"] = self.be.rename(SID, "alpha")
            except BaseException as e:                            # noqa: BLE001
                outcome["a"] = (type(e).__name__, str(e))

        t = holder["a"] = threading.Thread(target=first, name="rename-a")
        with mock.patch.object(sb, "read_reg", read_reg):
            t.start()
            self.assertTrue(a_read_done.wait(10), "rename A returned from its door's record read")
            change()
            go.set()
            t.join(10)
        self.assertFalse(t.is_alive(), "rename A returned")
        return outcome.get("a")

    def test_a_plain_rename_writes_its_record_once_inside_the_locked_compare_and_swap_and_lands(self):
        # the control, by execution: with no other writer the rename lands on all three stores, and its one record write is
        # made from _update_reg_if_holds with _reg_lock held (write_reg wrapped in the module to record the calling frame's
        # name and the lock's state at the call; a bare write_reg on the road fails this however it is spelled). This is the
        # executed pin the spelling pin in tests/test_kernel_effort_reconnect.py names.
        real, writes = sb.write_reg, []

        def recording(state_dir, sid, reg):
            frame = sys._getframe(1)
            writes.append({"caller": frame.f_code.co_name, "locked": self.be._reg_lock.locked(), "name": reg.get("name")})
            return real(state_dir, sid, reg)
        with mock.patch.object(sb, "write_reg", recording):
            self.assertTrue(self.be.rename(SID, "alpha"))
        self.assertEqual(writes, [{"caller": "_update_reg_if_holds", "locked": True, "name": "alpha"}],
                         "one record write, the compare-and-swap's, under the lock, carrying the name: %r" % (writes,))
        self.assertEqual(self._stores(), (("alpha", "alpha"), "alpha", "alpha"), "the rename landed on every store")
        self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing to log: %r" % (self.logs,))

    def test_a_record_removed_between_the_door_read_and_the_write_refuses_and_builds_none(self):
        a = self._rename_with_the_record_changed_before_its_write(self.regp.unlink)
        self.assertEqual(a[0] if isinstance(a, tuple) else a, "RenameRefused", "A hears the refusal: %r" % (a,))
        self.assertIn("record is gone", a[1])
        self.assertEqual(self._stores(), (None, "web", "web"),
                         "no record was built from the door read; the names file and the live name never moved")
        refused = [m for m in self.logs if "rename" in m and "refused" in m]
        self.assertEqual(len(refused), 1, "one log line names the absent record: %r" % (self.logs,))
        self.assertIn("absent", refused[0])
        self.assertEqual([m for m in self.logs if "compensation" in m or "would not read" in m], [], "no other verdict: %r" % (self.logs,))

    def test_a_record_that_will_not_read_at_the_write_refuses_and_moves_no_other_store(self):
        # red before the fourteenth commit: the skipped write's False was never read, so the rename went on, the names file
        # and the live name read alpha, the caller heard True, and the record (which a restart applies) never moved
        with contextlib.redirect_stderr(io.StringIO()) as err:
            a = self._rename_with_the_record_changed_before_its_write(lambda: self.regp.write_text("[]\n"))
        self.assertEqual(a[0] if isinstance(a, tuple) else a, "RenameRefused", "A hears the refusal: %r" % (a,))
        self.assertIn("would not read", a[1])
        self.assertEqual(self.regp.read_text(), "[]\n", "nothing was written over the unreadable record")
        self.assertEqual((self.nf.read_text().split("\t")[0], self.live.name), ("web", "web"),
                         "the names file and the live name were not moved over a record that did not")
        self.assertIn("unreadable", err.getvalue(), "the writers' one rule: a stderr line and no write")
        refused = [m for m in self.logs if "rename" in m and "refused" in m]
        self.assertEqual(len(refused), 1, "one log line names the unreadable record: %r" % (self.logs,))
        self.assertIn("would not read", refused[0])
        self.assertEqual([m for m in self.logs if "compensation" in m or "is absent" in m], [], "no other verdict: %r" % (self.logs,))


class RecordGoneOrUnreadableAtCompensation(unittest.TestCase):
    """The two verdicts _revert_rename_record answers when the record does not read (the twelfth commit): ABSENT (the file
    is gone: this backend never unlinks a record and the kernel only reads it, so a hand outside the kernel dropped the
    session inside the rename's window) and UNREADABLE (the file exists and will not read: the writers' one rule skips
    the write rather than gut the row). Until the twelfth commit both answered None and rename's arm logged the unreadable
    sentence for both. Each is pinned by the log line it produces and the store it leaves alone. Synthetic: placeholder
    sid, demo names."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        self.logs = []
        self.be = sb.SdkBackend(self.td.name, "/bin/true", lambda *a, **k: None, log=self.logs.append)
        self.cwd = str(self.root / "proj")
        Path(self.cwd).mkdir()
        (self.root / "names").mkdir()
        self.nf = self.root / "names" / SID
        self.nf.write_text("web\t%s\t#112233\t#ffffff\n" % self.cwd)
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "cwd": self.cwd, "lastSid": SID})
        self.regp = sb._reg_path(self.root, SID)
        self.live = NamesWriteFailure._Live()
        self.be.sessions[SID] = self.live

    def tearDown(self):
        self.td.cleanup()

    def test_a_record_removed_inside_the_window_is_named_absent_and_none_is_built(self):
        def write_name(state_dir, sid, name, *a, **k):
            self.regp.unlink()                                    # a hand outside the kernel drops the session
            raise OSError(28, "No space left on device")
        with mock.patch.object(sb, "write_name", write_name):
            with self.assertRaises(OSError):
                self.be.rename(SID, "alpha")
        self.assertEqual(sb.read_reg(self.root, SID), None, "a compensation never builds a record")
        self.assertEqual((self.nf.read_text().split("\t")[0], self.live.name), ("web", "web"),
                         "the names file and the live name are as they were")
        absent = [m for m in self.logs if "rename" in m and "is absent" in m]
        self.assertEqual(len(absent), 1, "one log line names the absent record: %r" % (self.logs,))
        self.assertIn("alpha", absent[0])
        self.assertEqual([m for m in self.logs if "would not read" in m or "compensation failed" in m
                          or "stood down" in m or "is not put back" in m], [],
                         "the absent record is not reported as unreadable: %r" % (self.logs,))

    def test_a_record_that_will_not_read_is_named_unreadable_and_left_as_it_is(self):
        def write_name(state_dir, sid, name, *a, **k):
            self.regp.write_text("[]\n")                          # exists, reads as a non-object: not a record
            raise OSError(28, "No space left on device")
        with mock.patch.object(sb, "write_name", write_name), contextlib.redirect_stderr(io.StringIO()) as err:
            with self.assertRaises(OSError):
                self.be.rename(SID, "alpha")
        self.assertEqual(self.regp.read_text(), "[]\n", "nothing was written over the unreadable record")
        self.assertEqual((self.nf.read_text().split("\t")[0], self.live.name), ("web", "web"))
        unreadable = [m for m in self.logs if "rename" in m and "would not read" in m]
        self.assertEqual(len(unreadable), 1, "one log line names the unreadable record: %r" % (self.logs,))
        self.assertIn("alpha", unreadable[0])
        self.assertIn("unreadable", err.getvalue(), "the writers' one rule: a stderr line and no write")
        self.assertEqual([m for m in self.logs if "is absent" in m or "compensation failed" in m
                          or "stood down" in m or "is not put back" in m], [],
                         "the unreadable record is not reported as absent: %r" % (self.logs,))


class NamesFilePublicationsUnderTheLocks(unittest.TestCase):
    """Every write of names/<sid> the backend makes runs under the lock its record write holds and under the names lock
    (fork PR #813, round 6 of the review, sixteenth commit, 2026-09-21; the round's own verifiers' fifth pass), and
    publishes the record's name and cwd as read in that hold and the file's colours and emoji as read at the write.
    THE DEFECT (the F-A class on two sibling roads of rename's three stores; pre-existing): promote_thread's names write
    and live set ran after its record write's hold was released, and _finish_move's names rewrite ran outside any lock
    and published the name it had read before; a rename landing in either window (record, names file, live name; its
    caller told True) was written over on the names file, the roster every listing reads, by the late write, with no log
    line: the verifiers' drives read the record alpha while the names file and the live name read the promote's name,
    and the names file reading the move's stale name with the new cwd. THE FIX, fitted to the class, is the shape rename
    has had since the fifteenth commit: the names write moves inside the same hold of _reg_lock as the record write, with
    the record as the source of truth for the name and the cwd, so a rename whose door read the writer's record WAITS
    and lands after it, and nobody loses; a compare-and-swap on the file's content would have needed a retry loop for
    the writers whose fields are facts (a move's cwd, a promote's name), a separate condition on the live name, and a
    loser to log, where one hold has none. THE NAMES LOCK closes the other family: the kernel's colour, emoji, palette
    and dead-tab name writers hold _NAMES_LOCK across their read-edit-publish and the backend's writers took no lock of
    theirs, so a rename inside a colour writer's span was put back by its publish and a colour inside a rename's was
    carried stale; the kernel hands its lock to the backend at construction and every backend write of the file holds
    it (_publish_name). Driven with real threads: the writer held inside write_name by thread identity, the rename
    started on a third thread and given 0.3 s (a bound on a negative, not the pin: the pin is the ORDER of the writes,
    which the hold decides), then released. Synthetic: placeholder sid, demo names, a one-line transcript.
    THE SEVENTEENTH COMMIT (the round's own verifiers' sixth pass) brings fork under the same hold (its record write and
    its names publish were two holds, the publish after the first, and a rename of the new sid landing between them was
    undone on the roster under a True) and pins the source-of-truth rule as stated: the record's name and cwd where it
    holds them, else the file's (a rename over a cwd-less record cleared the file's cwd; a move over a nameless record
    published the sid), and the record's cwd over a names file that disagrees, the pin the non-red mutation (a rename
    carrying the file's cwd) needed.
    THE EIGHTEENTH COMMIT (the round's own verifiers' seventh pass) brings spawn under the same hold with the record
    FIRST: its names entry preceded its record, and the kernel's rename door, which owns a sid by its record's existence
    and routes a record-less sid to the dead-tab road, rewrote that entry in the window under a True while the record
    then landed with the spawn's name (the F17-1 drive); the dead-tab road itself re-checks ownership under the names
    lock before it writes, so a door that resolved the sid as nobody's before the record landed hands the rename to the
    backend instead of writing over its publish. Two non-red mutants are pinned: promote's cwd over a record with none
    (the file's, never a clear) and spawn's names write under the names lock, in its order after the record."""

    CHILD = "dddddddd-1111-2222-3333-444444444444"   # the sid a fork mints; a rename of it inside the fork's window

    class _Live:
        def __init__(self):
            self.name = "web"
            self.thread_of = "bbbbbbbb-1111-2222-3333-444444444444"

    @staticmethod
    def _names_locked(be):
        """The names lock's state at a write, or None on a tree whose backend has no names lock, so a red-before run
        on such a tree reaches the pins' assertions (the stores, the write order) instead of dying inside the writer."""
        lock = getattr(be, "_names_lock", None)
        return lock.locked() if lock is not None else None

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.root = Path(self.td.name)
        (self.root / "session-hosts").write_text("off\n")
        self.logs = []
        self.be = sb.SdkBackend(self.td.name, "/bin/true", lambda *a, **k: None, log=self.logs.append)
        self.cwd = str(self.root / "proj")
        Path(self.cwd).mkdir()
        self.new = str(self.root / "proj2")
        Path(self.new).mkdir()
        (self.root / "names").mkdir()
        self.nf = self.root / "names" / SID
        self.nf.write_text("web\t%s\t#112233\t#ffffff\n" % self.cwd)
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "cwd": self.cwd, "lastSid": SID})
        tp = Path(sb.transcript_path(self.cwd, SID))          # prior turns: a rename stamps its note
        tp.parent.mkdir(parents=True, exist_ok=True)
        tp.write_text('{"type": "user", "uuid": "u1"}\n')
        self.live = self._Live()
        self.be.sessions[SID] = self.live

    def tearDown(self):
        self.td.cleanup()

    def _names(self):
        return self.nf.read_text().rstrip("\n").split("\t")

    def _rename_arrives_while_a_writer_holds(self, writer):
        """`writer` runs on a thread named "writer" and is held INSIDE its names write (write_name patched by thread
        identity); a rename to alpha starts on a thread named "rename-b" while the writer is held and is given 0.3 s;
        the writer resumes; both are joined. Every write_reg and write_name is recorded as (thread, name, _reg_lock held,
        _names_lock held). Returns (the writer's outcome, the rename's outcome, whether the rename was still running when
        the writer resumed, the record writes, the names writes, the four stores read while the writer was held)."""
        real_wn, real_wr, be = sb.write_name, sb.write_reg, self.be
        w_in, go, holder, reg_writes, names_writes = threading.Event(), threading.Event(), {}, [], []

        def write_name(state_dir, sid, nm, *a, **k):
            names_writes.append((threading.current_thread().name, nm, be._reg_lock.locked(), self._names_locked(be)))
            if threading.current_thread() is holder.get("w"):
                w_in.set()
                go.wait(10)
            return real_wn(state_dir, sid, nm, *a, **k)

        def write_reg(state_dir, sid, reg):
            reg_writes.append((threading.current_thread().name, reg.get("name"), be._reg_lock.locked(), self._names_locked(be)))
            return real_wr(state_dir, sid, reg)

        outcome = {}

        def run(key, fn):
            try:
                outcome[key] = fn()
            except BaseException as e:                            # noqa: BLE001 (the drive records whatever escapes)
                outcome[key] = (type(e).__name__, str(e))

        tw = holder["w"] = threading.Thread(target=run, args=("w", writer), name="writer")
        tb = threading.Thread(target=run, args=("b", lambda: self.be.rename(SID, "alpha")), name="rename-b")
        with mock.patch.object(sb, "write_name", write_name), mock.patch.object(sb, "write_reg", write_reg):
            tw.start()
            self.assertTrue(w_in.wait(10), "the writer reached its names write")
            reg = sb.read_reg(self.root, SID)
            at_hold = (reg.get("name"), self._names()[0], self._names()[1], self.live.name)
            tb.start()
            tb.join(0.3)
            b_waiting = tb.is_alive()
            go.set()
            tw.join(10)
            tb.join(10)
        self.assertFalse(tw.is_alive() or tb.is_alive(), "both returned")
        return outcome.get("w"), outcome.get("b"), b_waiting, reg_writes, names_writes, at_hold

    def test_a_rename_arriving_while_a_promote_publishes_waits_and_lands_after_it(self):
        # THE VERIFIERS' DRIVE (PROMOTE_NAMES_WRITE_OVER_RENAME). The record is a comment thread's; promote_thread has
        # written its record (threadOf gone, name promoted) and is inside its names write; rename to alpha arrives. At the
        # fifteenth commit the promote's names write ran with the lock free, so the rename's door read the landed record,
        # its compare-and-swap passed on 'promoted', it wrote every store and answered True, and the promote's late names
        # write and live set then put 'promoted' back on the names file and the live name: the record ('alpha', 'alpha'),
        # the names file and the live name 'promoted', both callers told success, nothing logged. Now the rename waits on
        # the promote's hold and lands after it: every store alpha, the promote's writes before the rename's, no log line.
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "cwd": self.cwd, "lastSid": SID,
                                      "threadOf": self.live.thread_of})
        w, b, b_waiting, reg_writes, names_writes, at_hold = self._rename_arrives_while_a_writer_holds(
            lambda: self.be.promote_thread(SID, "promoted", "#112233", "#ffffff"))
        self.assertEqual(at_hold, ("promoted", "web", self.cwd, "web"), "the promote's record write is on disk; its names write has not landed")
        self.assertEqual((w, b), (True, True), "both told success, in turn: %r" % ((w, b),))
        reg = sb.read_reg(self.root, SID)
        self.assertEqual((reg.get("name"), reg.get("renameNote"), "threadOf" in reg, self._names()[0], self.live.name, self.live.thread_of),
                         ("alpha", "alpha", False, "alpha", "alpha", ""),
                         "the later rename stands on the record, the names file and the live name, and the promotion stands "
                         "(red before: the names file and the live name read 'promoted' under the rename's True)")
        self.assertTrue(b_waiting, "the rename had not returned while the promote held the lock (red before the sixteenth "
                                   "commit: it landed whole inside the promote's window)")
        self.assertEqual([(t, n) for t, n, _r, _n in reg_writes], [("writer", "promoted"), ("rename-b", "alpha")],
                         "the promote's record write, then the rename's: %r" % (reg_writes,))
        self.assertEqual([(t, n) for t, n, _r, _n in names_writes], [("writer", "promoted"), ("rename-b", "alpha")],
                         "the promote's names write landed before the rename's began: %r" % (names_writes,))
        self.assertEqual([(r, nl) for _t, _n, r, nl in names_writes], [(True, True), (True, True)],
                         "each names write made with _reg_lock and the names lock held: %r" % (names_writes,))
        self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing lost, nothing to log: %r" % (self.logs,))

    def test_a_rename_arriving_while_a_move_publishes_waits_and_both_facts_land(self):
        # THE VERIFIERS' DRIVE (MOVE_NAMES_REWRITE_STALE_NAME). _finish_move has written its record (cwd new) and is
        # inside its names write; rename to alpha arrives. At the fifteenth commit the move's names rewrite ran under no
        # lock and carried the name it had read before the rename: the rename landed whole (record, names file with the
        # OLD cwd it had read at its door, live name) and answered True, and the move's rewrite then published 'web' with
        # the new cwd over it: the names file 'web', the record and the live name 'alpha', one log line (the move's own).
        # Now the rename waits on the move's hold and lands after it, taking the cwd from the record under the lock: the
        # names file reads alpha WITH the new cwd, the move's write before the rename's, and the move's line is the only one.
        def move():
            with contextlib.redirect_stderr(io.StringIO()):
                self.be._finish_move(None, SID, self.cwd, self.new)
            return "finished"
        w, b, b_waiting, reg_writes, names_writes, at_hold = self._rename_arrives_while_a_writer_holds(move)
        self.assertEqual(at_hold, ("web", "web", self.cwd, "web"), "the move's record write is on disk; its names write has not landed")
        self.assertEqual((w, b), ("finished", True), "the move finished and the rename was told applied: %r" % ((w, b),))
        reg = sb.read_reg(self.root, SID)
        self.assertEqual((reg.get("name"), reg.get("cwd"), self._names()[:2], self.live.name),
                         ("alpha", self.new, ["alpha", self.new], "alpha"),
                         "both facts stand on the names file: the rename's name and the move's cwd (red before: the names "
                         "file read 'web' with the new cwd under the rename's True)")
        self.assertTrue(b_waiting, "the rename had not returned while the move held the lock (red before the sixteenth "
                                   "commit: it landed whole inside the move's window)")
        self.assertEqual(self._names()[2:4], ["#112233", "#ffffff"], "the colours ride along, read at each write")
        self.assertEqual([(t, n) for t, n, _r, _n in names_writes], [("writer", "web"), ("rename-b", "alpha")],
                         "the move's names write landed before the rename's began: %r" % (names_writes,))
        self.assertEqual([(r, nl) for _t, _n, r, nl in names_writes], [(True, True), (True, True)],
                         "each names write made with _reg_lock and the names lock held: %r" % (names_writes,))
        self.assertEqual(len([m for m in self.logs if "moved" in m]), 1, "the move's own line: %r" % (self.logs,))
        self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing lost, nothing to log: %r" % (self.logs,))

    def test_the_promotes_three_stores_and_the_moves_two_move_under_one_hold_of_each_lock(self):
        # the property by execution, the fifteenth commit's shape on the two sibling roads: with no other writer, each
        # store moves in order with _reg_lock held at every write and the names lock held at the names write, and both
        # locks are free when the road returns. Red before the sixteenth commit: the promote's names write and live set
        # and the move's names write with _reg_lock free, and no names lock at all.
        events, real_wr, real_wn, be = [], sb.write_reg, sb.write_name, self.be

        def write_reg(state_dir, sid, reg):
            events.append(("record", reg.get("name"), be._reg_lock.locked(), self._names_locked(be)))
            return real_wr(state_dir, sid, reg)

        def write_name(state_dir, sid, nm, *a, **k):
            events.append(("names", nm, be._reg_lock.locked(), self._names_locked(be)))
            return real_wn(state_dir, sid, nm, *a, **k)

        class _LiveRecording:
            def __init__(me):
                me._name, me.thread_of = "web", "bbbbbbbb-1111-2222-3333-444444444444"

            @property
            def name(me):
                return me._name

            @name.setter
            def name(me, v):
                events.append(("live", v, be._reg_lock.locked(), self._names_locked(be)))
                me._name = v
        live = _LiveRecording()
        self.be.sessions[SID] = live
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "cwd": self.cwd, "lastSid": SID, "threadOf": live.thread_of})
        with mock.patch.object(sb, "write_reg", write_reg), mock.patch.object(sb, "write_name", write_name):
            self.assertTrue(self.be.promote_thread(SID, "promoted", "#112233", "#ffffff"))
        self.assertEqual(events, [("record", "promoted", True, False), ("names", "promoted", True, True), ("live", "promoted", True, False)],
                         "the promote's three stores move in this order under the locks: %r" % (events,))
        self.assertEqual((self.be._reg_lock.locked(), self._names_locked(self.be)), (False, False), "both locks released when the promote returns")
        self.assertEqual((live.name, live.thread_of, self._names()[0]), ("promoted", "", "promoted"))
        del events[:]
        with mock.patch.object(sb, "write_reg", write_reg), mock.patch.object(sb, "write_name", write_name), \
                contextlib.redirect_stderr(io.StringIO()):
            self.be._finish_move(None, SID, self.cwd, self.new)
        self.assertEqual(events, [("record", "promoted", True, False), ("names", "promoted", True, True)],
                         "the move's record write and names write under the locks, the names file carrying the record's name: %r" % (events,))
        self.assertEqual((self.be._reg_lock.locked(), self._names_locked(self.be)), (False, False), "both locks released when the move returns")
        self.assertEqual(self._names()[:2], ["promoted", self.new])

    def test_a_names_publication_waits_for_a_writer_holding_the_names_lock_and_carries_what_it_landed(self):
        # THE OTHER FAMILY, by execution. A writer in the kernel's shape (_set_session_color: read the line, edit the
        # colour, publish tmp + os.replace, the whole span under the names lock) is held between its read and its publish;
        # a rename arrives, has its record written, and must WAIT at its names write; released, the colour writer publishes
        # web with the new colour, and the rename then publishes alpha carrying that colour, read from the file under the
        # lock. Red before the sixteenth commit (the backend took no names lock, so the attribute below was unread): the
        # rename landed inside the writer's span and the writer's publish put 'web' back over it while the record held
        # alpha, the roster disagreeing with the record under the rename's True and the writer's True. The lock is set on
        # the backend as an attribute here so that an older tree, which has no `names_lock` argument, still reaches the
        # assertions rather than failing at construction; the constructor's wiring is the next test's.
        lock = threading.Lock()
        self.be._names_lock = lock
        held, go, outcome = threading.Event(), threading.Event(), {}

        def colour_writer():
            with lock:                                             # the kernel's span: read, edit, publish, one hold
                parts = self._names()
                held.set()
                go.wait(10)
                parts[2], parts[3] = "#445566", "#000000"
                tmp = self.nf.with_suffix(".tmp")
                tmp.write_text("\t".join(parts) + "\n")
                os.replace(tmp, self.nf)
            return True

        def run(key, fn):
            outcome[key] = fn()
        tw = threading.Thread(target=run, args=("w", colour_writer), name="colour")
        tb = threading.Thread(target=run, args=("b", lambda: self.be.rename(SID, "alpha")), name="rename-b")
        tw.start()
        self.assertTrue(held.wait(10), "the colour writer holds the names lock after its read")
        tb.start()
        tb.join(0.3)
        b_waiting = tb.is_alive()
        record_while_held = (sb.read_reg(self.root, SID) or {}).get("name")
        go.set()
        tw.join(10)
        tb.join(10)
        self.assertFalse(tw.is_alive() or tb.is_alive(), "both returned")
        self.assertEqual((outcome.get("w"), outcome.get("b")), (True, True))
        self.assertEqual(self._names(), ["alpha", self.cwd, "#445566", "#000000"],
                         "the rename's name AND the writer's colour stand on the file (red before: 'web' with the new colour)")
        self.assertTrue(b_waiting, "the rename had not returned while the colour writer held the names lock")
        self.assertEqual(record_while_held, "alpha", "the rename's record write had landed; its names write was what waited")
        self.assertEqual(((sb.read_reg(self.root, SID) or {}).get("name"), self.live.name), ("alpha", "alpha"))
        self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing lost, nothing to log: %r" % (self.logs,))

    def test_a_move_landing_between_a_renames_door_read_and_its_record_write_keeps_its_cwd_on_the_names_file(self):
        # RESIDUAL 5, CLOSED (the fourteenth commit named it, the fifteenth narrowed it to this shape): rename A is held
        # right after its door's record read (read_reg patched by thread identity, on A's first call); a move finishes
        # whole (record cwd new, names file cwd new); A resumes, its compare-and-swap passes (the name never moved) and
        # its names write publishes alpha. At the fifteenth commit that write carried the cwd A's door had read, so the
        # names file went back to the OLD cwd while the record held the new one, under A's True and with no log line.
        # Now the cwd comes from the record as the compare-and-swap read it, under the lock: the names file reads alpha
        # with the new cwd, and the move's own line is the only one logged.
        real_read = sb.read_reg
        a_read_done, go, holder, a_reads, outcome = threading.Event(), threading.Event(), {}, [], {}

        def read_reg(state_dir, sid):
            reg = real_read(state_dir, sid)
            if threading.current_thread() is holder.get("a"):
                a_reads.append(sid)
                if len(a_reads) == 1:                              # A's door read: hold here until the move has finished
                    a_read_done.set()
                    go.wait(10)
            return reg

        def first():
            try:
                outcome["a"] = self.be.rename(SID, "alpha")
            except BaseException as e:                            # noqa: BLE001
                outcome["a"] = (type(e).__name__, str(e))
        t = holder["a"] = threading.Thread(target=first, name="rename-a")
        with mock.patch.object(sb, "read_reg", read_reg):
            t.start()
            self.assertTrue(a_read_done.wait(10), "rename A returned from its door's record read")
            with contextlib.redirect_stderr(io.StringIO()):
                self.be._finish_move(None, SID, self.cwd, self.new)
            self.assertEqual(self._names()[:2], ["web", self.new], "the move landed whole while A was held")
            go.set()
            t.join(10)
        self.assertFalse(t.is_alive(), "rename A returned")
        self.assertEqual(outcome.get("a"), True, "A was told applied: %r" % (outcome.get("a"),))
        reg = sb.read_reg(self.root, SID)
        self.assertEqual((reg.get("name"), reg.get("cwd"), self._names()[:2], self.live.name),
                         ("alpha", self.new, ["alpha", self.new], "alpha"),
                         "the names file carries the record's cwd as read at A's record write (red before the sixteenth commit: "
                         "the door-time OLD cwd, put back over the move's under A's True)")
        self.assertEqual(self._names()[2:4], ["#112233", "#ffffff"], "the colours ride along")
        self.assertEqual(len([m for m in self.logs if "moved" in m]), 1, "the move's own line: %r" % (self.logs,))
        self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing lost, nothing to log: %r" % (self.logs,))

    def test_a_move_publishes_the_records_name_over_a_names_file_that_disagrees(self):
        # THE SOURCE OF TRUTH FOR THE NAME, by execution (the mutation that carries a name read from the file before the
        # hold stays green under the two drives above, since the file and the record agree there; this pin tells the two
        # sources apart): the names file reads 'stale' while the record reads web (the F-B shape, a disagreement a faulted
        # rename left behind), and a move finishes. Until the sixteenth commit the move carried the file's name, so the
        # disagreement outlived it; now the names file reads the record's name with the new cwd, and the colours ride.
        # Every SDK sid's rename goes through the record (the kernel routes a sid with a record to this backend, alive or
        # dormant; its dead-tab _set_name is for sids no backend owns), so the record is what a restart applies and the
        # file is the copy.
        self.nf.write_text("stale\t%s\t#112233\t#ffffff\n" % self.cwd)
        with contextlib.redirect_stderr(io.StringIO()):
            self.be._finish_move(None, SID, self.cwd, self.new)
        self.assertEqual(self._names(), ["web", self.new, "#112233", "#ffffff"],
                         "the record's name and the new cwd (red before the sixteenth commit: 'stale' carried from the file)")
        self.assertEqual((sb.read_reg(self.root, SID) or {}).get("cwd"), self.new)

    def test_a_rename_arriving_at_a_forks_names_publish_waits_and_lands_after_it(self):
        # THE VERIFIERS' DRIVE (FORK_AT_PUBLISH_ENTRY_RENAME_ARRIVES, the sixth pass). fork has written the child's record
        # under _reg_lock and is at _publish_name's ENTRY, before the names lock; a rename of the child to alpha arrives
        # (the rename door takes a raw sid with no roster check, and the backend owns a sid by its record's existence, so
        # the sid is renameable the moment the record exists). At the sixteenth commit the publish ran after the record
        # write's hold was released: the rename landed whole in that window (its door read the child's record, its
        # compare-and-swap passed on 'child', it wrote the record and the names file and answered True) and the fork's
        # publish then wrote 'child' over the roster: the record ('alpha', 'alpha'), the names file 'child', both callers
        # told success, nothing logged. Now the fork's record write and its names publish are one hold, so the rename
        # waits and lands after: every store alpha with the fork's cwd and colours riding, the fork's names write before
        # the rename's, each under both locks. Held at the publish's ENTRY and not inside write_name: inside it the names
        # lock already made the rename's names write wait, which is why the sixteenth commit's harness saw no window here.
        real_wn, real_wr, real_pub, be = sb.write_name, sb.write_reg, self.be._publish_name, self.be
        w_in, go, holder, reg_writes, names_writes, outcome = threading.Event(), threading.Event(), {}, [], [], {}

        def publish(sid, *a, **k):
            if threading.current_thread() is holder.get("w"):
                w_in.set()
                go.wait(10)
            return real_pub(sid, *a, **k)

        def write_name(state_dir, sid, nm, *a, **k):
            names_writes.append((threading.current_thread().name, sid[:4], nm, be._reg_lock.locked(), self._names_locked(be)))
            return real_wn(state_dir, sid, nm, *a, **k)

        def write_reg(state_dir, sid, reg):
            reg_writes.append((threading.current_thread().name, sid[:4], reg.get("name")))
            return real_wr(state_dir, sid, reg)

        def run(key, fn):
            try:
                outcome[key] = fn()
            except BaseException as e:                            # noqa: BLE001 (the drive records whatever escapes)
                outcome[key] = (type(e).__name__, str(e))
        tw = holder["w"] = threading.Thread(target=run, name="writer",
                                            args=("w", lambda: self.be.fork("child", SID, "", "#112233", "#ffffff", sid=self.CHILD)))
        tb = threading.Thread(target=run, args=("b", lambda: self.be.rename(self.CHILD, "alpha")), name="rename-b")
        self.be._publish_name = publish
        child_nf = self.root / "names" / self.CHILD
        with mock.patch.object(sb, "write_name", write_name), mock.patch.object(sb, "write_reg", write_reg):
            tw.start()
            self.assertTrue(w_in.wait(10), "the fork reached its names publish")
            at_hold = ((sb.read_reg(self.root, self.CHILD) or {}).get("name"), child_nf.exists())
            tb.start()
            tb.join(0.3)
            b_waiting = tb.is_alive()
            go.set()
            tw.join(10)
            tb.join(10)
        self.assertFalse(tw.is_alive() or tb.is_alive(), "both returned")
        self.assertEqual(at_hold, ("child", False), "the fork's record is on disk; its names entry is not yet published")
        self.assertEqual((outcome.get("w"), outcome.get("b")), (self.CHILD, True),
                         "the fork returned its sid and the rename was told applied: %r" % (outcome,))
        reg = sb.read_reg(self.root, self.CHILD)
        names = child_nf.read_text().rstrip("\n").split("\t")
        self.assertEqual((reg.get("name"), reg.get("renameNote"), names), ("alpha", "alpha", ["alpha", self.cwd, "#112233", "#ffffff"]),
                         "the later rename stands on the record AND the roster, the fork's cwd and colours riding (red before the "
                         "seventeenth commit: the roster read 'child' under the rename's True)")
        self.assertTrue(b_waiting, "the rename had not returned while the fork held the lock (red before the seventeenth "
                                   "commit: it landed whole inside the fork's window)")
        self.assertEqual(reg_writes, [("writer", "dddd", "child"), ("rename-b", "dddd", "alpha")],
                         "the fork's record write, then the rename's: %r" % (reg_writes,))
        self.assertEqual([(t, n) for t, _s, n, _r, _nl in names_writes], [("writer", "child"), ("rename-b", "alpha")],
                         "the fork's names write landed before the rename's began: %r" % (names_writes,))
        self.assertEqual([(r, nl) for _t, _s, _n, r, nl in names_writes], [(True, True), (True, True)],
                         "each names write made with _reg_lock and the names lock held: %r" % (names_writes,))
        self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing lost, nothing to log: %r" % (self.logs,))

    def test_a_move_over_a_record_with_no_name_carries_the_files_name(self):
        # F16-2 (the sixth pass), a shape the sixteenth commit changed: _finish_move publishes the record's name, and over
        # a record that HAS none it put the sid in for it. Two records with no name: the file removed before the finish
        # (a hand outside the kernel between move()'s door, which refuses an absent record, and the finish;
        # _update_reg_dropping recreates the sid plus the cwd and movedFrom) and a record that reads with no name key (the
        # shape _update_reg's absent-record recreation mints). Until the seventeenth commit the roster read the sid over
        # the file's 'web' with the new cwd, the move's caller told success and nothing said. Now a record with no name
        # passes None and the file's own name is carried with the new cwd: the record is the source of truth where it
        # holds a value, never the source of a clear. The recreation itself stays silent, as every record RMW's is.
        for label, prepare in (("absent", lambda: sb._reg_path(self.root, SID).unlink()),
                               ("nameless", lambda: sb.write_reg(self.root, SID, {"sid": SID, "cwd": self.cwd, "lastSid": SID}))):
            with self.subTest(record=label):
                self.nf.write_text("web\t%s\t#112233\t#ffffff\n" % self.cwd)
                prepare()
                err = io.StringIO()
                with contextlib.redirect_stderr(err):
                    self.be._finish_move(None, SID, self.cwd, self.new)
                reg = sb.read_reg(self.root, SID) or {}
                self.assertEqual(self._names(), ["web", self.new, "#112233", "#ffffff"],
                                 "the file's own name with the new cwd (red before the seventeenth commit: the sid stood in for the name)")
                self.assertEqual((reg.get("cwd"), "name" in reg, (reg.get("movedFrom") or {}).get("cwd")), (self.new, False, self.cwd),
                                 "the record carries the move and no name: %r" % (reg,))
                self.assertEqual(err.getvalue(), "", "no unreadable line: the record was absent or nameless, not unreadable")
                self.assertEqual(len([m for m in self.logs if "moved" in m]), 1, "the move's own line: %r" % (self.logs,))
                del self.logs[:]

    def test_a_rename_over_a_record_without_a_cwd_carries_the_files_cwd(self):
        # F16-3 (the sixth pass), a shape the sixteenth commit changed: rename's names write takes the cwd from the record
        # as its compare-and-swap read it, and over a record with no `cwd` key (the absent-record recreations of
        # _update_reg and _update_reg_derived mint the sid plus the fields they write; spawn, fork and resume always set
        # one) it passed an empty string, write_name's explicit clear, so the names file lost the cwd it held under the
        # rename's True with nothing logged. Now a record with no cwd passes None and the file's cwd is carried.
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "lastSid": SID})
        self.assertTrue(self.be.rename(SID, "alpha"))
        self.assertEqual(self._names(), ["alpha", self.cwd, "#112233", "#ffffff"],
                         "the file's cwd carried (red before the seventeenth commit: cleared to an empty string)")
        self.assertEqual(((sb.read_reg(self.root, SID) or {}).get("name"), self.live.name), ("alpha", "alpha"))
        self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing lost, nothing to log: %r" % (self.logs,))

    def test_a_rename_and_a_promote_publish_the_records_cwd_over_the_files(self):
        # THE SOURCE OF TRUTH FOR THE CWD, by execution (F16-4, the sixth pass: the sixteenth commit's pins all had the
        # record and the file agreeing on the cwd, so a rename publishing the FILE's cwd, or a promote passing none,
        # stayed green under every one of them). The rule as stated and pinned: the record's cwd where the record holds
        # one (this test), else the file's (the test above). A rename over a names file whose cwd is stale against the
        # record's publishes the record's; a promote of a thread, which has no names file, publishes the record's cwd
        # (nothing on the file to carry: a publish passing None would leave the roster's cwd empty).
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "cwd": self.new, "lastSid": SID})   # the file still reads the old cwd
        self.assertTrue(self.be.rename(SID, "alpha"))
        self.assertEqual(self._names(), ["alpha", self.new, "#112233", "#ffffff"],
                         "the record's cwd over the file's stale one (a rename carrying the file's cwd leaves the old one here)")
        self.nf.unlink()                                          # a thread has no names file
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "cwd": self.cwd, "lastSid": SID, "threadOf": self.live.thread_of})
        self.assertTrue(self.be.promote_thread(SID, "promoted", "#445566", "#000000"))
        self.assertEqual(self._names(), ["promoted", self.cwd, "#445566", "#000000"],
                         "the record's cwd on the breakout's row (a promote passing no cwd leaves it empty)")
        self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing lost, nothing to log: %r" % (self.logs,))

    def _spawn_held_and_the_kernels_door_renames(self, be, hold):
        """spawn CHILD on a thread named "writer", held by thread identity at `hold`: "record write" (inside write_reg,
        before the record lands: the verifiers' hold point), "publish entry" (at _publish_name's entry) or "door resolved
        first" (inside write_reg too, but the door resolves the sid's backend while the spawn is held and writes only
        after the spawn has returned: the gap between the kernel door's two reads). The kernel's rename door
        (Sessions.backend_for, then _rename_claimed: the WS op's and the route's shape) renames CHILD to alpha on a
        thread named "rename-b", given 0.3 s where the spawn is still held. Every write_reg and write_name is recorded as
        (thread, sid, name, _reg_lock held); the kernel's stderr is captured. Returns a dict of what was read."""
        real_wn, real_wr, real_pub = sb.write_name, sb.write_reg, be._publish_name
        w_in, go, routed, spawn_done = threading.Event(), threading.Event(), threading.Event(), threading.Event()
        holder, reg_writes, names_writes, out = {}, [], [], {}

        def publish(sid, *a, **k):
            if hold == "publish entry" and threading.current_thread() is holder.get("w"):
                w_in.set()
                go.wait(10)
            return real_pub(sid, *a, **k)

        def write_name(state_dir, sid, nm, *a, **k):
            names_writes.append((threading.current_thread().name, sid[:4], nm, be._reg_lock.locked()))
            return real_wn(state_dir, sid, nm, *a, **k)

        def write_reg(state_dir, sid, reg):
            reg_writes.append((threading.current_thread().name, sid[:4], reg.get("name"), be._reg_lock.locked()))
            if hold != "publish entry" and threading.current_thread() is holder.get("w"):
                w_in.set()
                go.wait(10)
            return real_wr(state_dir, sid, reg)

        def door():
            be_for = km.Sessions.backend_for(self.CHILD)
            out["unowned"] = be_for is km._UNOWNED
            routed.set()
            if hold == "door resolved first":
                spawn_done.wait(10)
            return km._rename_claimed(be_for, self.CHILD, "alpha")

        def run(key, fn):
            try:
                out[key] = fn()
            except BaseException as e:                            # noqa: BLE001 (the drive records whatever escapes)
                out[key] = (type(e).__name__, str(e))
        tw = holder["w"] = threading.Thread(target=run, name="writer",
                                            args=("w", lambda: be.spawn("child", self.cwd, "#112233", "#ffffff", sid=self.CHILD)))
        tb = threading.Thread(target=run, args=("b", door), name="rename-b")
        child_nf, err = self.root / "names" / self.CHILD, io.StringIO()
        with mock.patch.object(sb, "write_name", write_name), mock.patch.object(sb, "write_reg", write_reg), \
                mock.patch.object(be, "_publish_name", publish), contextlib.redirect_stderr(err):
            tw.start()
            self.assertTrue(w_in.wait(10), "the spawn reached its hold point")
            out["at_hold"] = (sb._reg_path(self.root, self.CHILD).exists(), child_nf.exists())
            tb.start()
            if hold == "door resolved first":
                self.assertTrue(routed.wait(10), "the door resolved the sid's backend while the spawn was held")
                go.set()
                tw.join(10)
                spawn_done.set()
            else:
                tb.join(0.3)
                out["b_waiting"] = tb.is_alive()
                go.set()
                tw.join(10)
            tb.join(10)
        self.assertFalse(tw.is_alive() or tb.is_alive(), "both returned")
        out["reg"] = sb.read_reg(self.root, self.CHILD) or {}
        out["names"] = child_nf.read_text().rstrip("\n").split("\t") if child_nf.exists() else None
        out["reg_writes"], out["names_writes"], out["stderr"] = reg_writes, names_writes, err.getvalue()
        return out

    def test_a_spawns_record_lands_before_its_names_entry_so_the_kernels_rename_door_waits_or_refuses(self):
        # THE VERIFIERS' DRIVE (SPAWN_RECORD_WRITE_KERNEL_DOOR_RENAME, the seventh pass; F17-1, pre-existing at the pushed
        # head and at upstream main). spawn published names/<sid> at its top and wrote its record last; a rename of the new
        # sid arriving between the two through the KERNEL's door found no backend owning the sid (ownership is the
        # record's existence) and took the unowned route, whose rename is the dead-tab road: _set_name rewrote the entry
        # under the kernel's names lock alone and the door answered (True, ''); the record then landed with the spawn's
        # name. At the seventeenth commit: at the hold the record None and the entry 'child'; the door (True, ''); finally
        # the record 'child' and the entry 'alpha', the two stores disagreeing under the door's True, nothing logged. Now
        # the record lands first and the entry follows inside the same hold of _reg_lock, and the dead-tab road re-checks
        # ownership under the names lock before it writes. Held inside the record write, a rename finds neither store and
        # the door declines visibly ((False, ''), a stderr line naming the sid; the WS op says the rename did not take).
        # Held at the publish's entry, the door routes to this backend's rename, which waits on the hold and lands after
        # the publish on both stores. A door that resolved the sid as nobody's before the record landed and reaches its
        # write after the spawn returned finds the sid owned under the names lock and hands the rename to the backend,
        # which lands it on both stores (without the re-check the dead-tab write went over the spawn's publish under a
        # True). In every shape the record and the entry agree and the door's answer matches what stands. The kernel is
        # loaded as tests/test_session_emoji.py loads it; the backend is built with the kernel's names lock, as the kernel
        # builds it, and installed as its SDK singleton; the names registry is this test's.
        be = sb.SdkBackend(self.td.name, "/bin/true", lambda *a, **k: None, log=self.logs.append, names_lock=km._NAMES_LOCK)
        saved = (km.NAMES, km._sdk_backend, km._codex_backend)
        km.NAMES, km._sdk_backend, km._codex_backend = self.root / "names", be, False
        self.addCleanup(lambda: [setattr(km, k, v) for k, v in zip(("NAMES", "_sdk_backend", "_codex_backend"), saved)])
        for hold in ("record write", "publish entry", "door resolved first"):
            with self.subTest(held_at=hold):
                sb._reg_path(self.root, self.CHILD).unlink(missing_ok=True)
                (self.root / "names" / self.CHILD).unlink(missing_ok=True)
                del self.logs[:]
                out = self._spawn_held_and_the_kernels_door_renames(be, hold)
                reg, names = out["reg"], out["names"]
                self.assertEqual(out.get("w"), self.CHILD, "the spawn returned its sid: %r" % (out.get("w"),))
                self.assertIsNotNone(names, "the spawn published its entry")
                self.assertEqual(reg.get("name"), names[0],
                                 "the record and the names entry agree (red before the eighteenth commit, held inside the record "
                                 "write: the record 'child', the roster 'alpha' under the door's True)")
                self.assertEqual(out.get("b"), (names[0] == "alpha", ""), "the door's answer matches what stands: %r" % (out.get("b"),))
                self.assertEqual(names[1:], [self.cwd, "#112233", "#ffffff"], "the spawn's cwd and colours ride: %r" % (names,))
                self.assertEqual(out["reg_writes"][0], ("writer", "dddd", "child", True), "the spawn's record write first, under the lock: %r" % (out["reg_writes"],))
                self.assertEqual(out["names_writes"][0], ("writer", "dddd", "child", True),
                                 "the spawn's names write under the record lock, before any other (red before the eighteenth commit: "
                                 "the lock was free at the spawn's publish): %r" % (out["names_writes"],))
                if hold == "record write":
                    self.assertEqual(out["at_hold"], (False, False), "neither store exists while the record write is held (red before "
                                     "the eighteenth commit: the names entry was published first)")
                    self.assertTrue(out["unowned"], "no backend owns a sid with no record")
                    self.assertEqual((out.get("b"), reg.get("name")), ((False, ""), "child"), "the door declined and the spawn's name stands on both stores")
                    self.assertIn("no names/%s entry to rewrite" % self.CHILD, out["stderr"], "the refusal is said, naming the sid: %r" % (out["stderr"],))
                    self.assertEqual(len(out["names_writes"]), 1, "one names write, the spawn's: %r" % (out["names_writes"],))
                elif hold == "publish entry":
                    self.assertEqual(out["at_hold"], (True, False), "the record is on disk and the entry is not while the publish is held")
                    self.assertFalse(out["unowned"], "the record makes the sid this backend's, so the door routes to its rename")
                    self.assertTrue(out["b_waiting"], "the rename had not returned while the spawn held the lock")
                    self.assertEqual((out.get("b"), reg.get("name"), reg.get("renameNote")), ((True, ""), "alpha", None),
                                     "the rename landed after the publish, on the record too; no note: a fresh session has no history")
                    self.assertEqual([(t, n, r) for t, _s, n, r in out["names_writes"]], [("writer", "child", True), ("rename-b", "alpha", True)],
                                     "the spawn's names write landed before the rename's began, each under the record lock: %r" % (out["names_writes"],))
                    self.assertEqual(out["stderr"], "", "nothing refused, nothing said: %r" % (out["stderr"],))
                else:
                    self.assertTrue(out["unowned"], "the door resolved the sid as nobody's before the record landed")
                    self.assertEqual((out.get("b"), reg.get("name"), names[0]), ((True, ""), "alpha", "alpha"),
                                     "the dead-tab road found the sid owned under the names lock and handed the rename to the backend, "
                                     "which landed it on both stores (red without the re-check: the entry 'alpha' over the record 'child')")
                    self.assertEqual([(t, n, r) for t, _s, n, r in out["names_writes"]], [("writer", "child", True), ("rename-b", "alpha", True)],
                                     "the backend's names write, under its lock, not the dead-tab road's: %r" % (out["names_writes"],))
                    self.assertIn("the SDK backend owns %s now" % self.CHILD, out["stderr"], "the hand-over is said: %r" % (out["stderr"],))
                self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing lost, nothing to log: %r" % (self.logs,))

    def test_a_promote_over_a_record_without_a_cwd_carries_the_files_cwd(self):
        # F17-2 (the seventh pass), a non-red mutant of the seventeenth commit: promote_thread's `reg.get("cwd") or None`
        # mutated to `or ""` (write_name's explicit clear) left this module green, because every promote pin had a record
        # with a cwd or a thread with no names file (where "" and None publish the same empty cwd). The distinguishing
        # shape: a thread record with no `cwd` key (the absent-record recreations' shape) and a names entry present with
        # one. The rule as stated: the record's cwd where it holds one, else the file's, never a clear.
        sb.write_reg(self.root, SID, {"sid": SID, "name": "web", "lastSid": SID, "threadOf": self.live.thread_of})
        self.assertTrue(self.be.promote_thread(SID, "promoted", "#445566", "#000000"))
        self.assertEqual(self._names(), ["promoted", self.cwd, "#445566", "#000000"],
                         "the file's cwd carried onto the breakout's row (a promote passing an empty string clears it)")
        reg = sb.read_reg(self.root, SID) or {}
        self.assertEqual((reg.get("name"), "cwd" in reg, "threadOf" in reg, self.live.name), ("promoted", False, False, "promoted"),
                         "the record carries the breakout and still no cwd: %r" % (reg,))
        self.assertEqual([m for m in self.logs if "rename" in m], [], "nothing lost, nothing to log: %r" % (self.logs,))

    def test_a_spawns_record_write_and_names_publish_are_one_hold_of_the_lock_the_record_first(self):
        # the property by execution, the shape the one-hold pin above holds for promote and move (F17-3, the seventh pass:
        # spawn's `self._publish_name(...)` mutated to a bare write_name, no names lock, left this module green, its
        # publish unpinned). With no other writer, the record moves first with _reg_lock held and the names lock free,
        # then the names entry with both held; both locks are free when spawn returns; the two stores agree. Red before
        # the eighteenth commit: the names write first, with _reg_lock free.
        events, real_wr, real_wn, be = [], sb.write_reg, sb.write_name, self.be

        def write_reg(state_dir, sid, reg):
            events.append(("record", reg.get("name"), be._reg_lock.locked(), self._names_locked(be)))
            return real_wr(state_dir, sid, reg)

        def write_name(state_dir, sid, nm, *a, **k):
            events.append(("names", nm, be._reg_lock.locked(), self._names_locked(be)))
            return real_wn(state_dir, sid, nm, *a, **k)
        with mock.patch.object(sb, "write_reg", write_reg), mock.patch.object(sb, "write_name", write_name):
            self.assertEqual(self.be.spawn("child", self.cwd, "#112233", "#ffffff", sid=self.CHILD), self.CHILD)
        self.assertEqual(events, [("record", "child", True, False), ("names", "child", True, True)],
                         "the spawn's record write, then its names write, under the locks: %r" % (events,))
        self.assertEqual((self.be._reg_lock.locked(), self._names_locked(self.be)), (False, False), "both locks released when the spawn returns")
        reg = sb.read_reg(self.root, self.CHILD) or {}
        names = (self.root / "names" / self.CHILD).read_text().rstrip("\n").split("\t")
        self.assertEqual((reg.get("name"), reg.get("cwd"), names), ("child", self.cwd, ["child", self.cwd, "#112233", "#ffffff"]),
                         "the two stores agree on the name and the cwd, the colours riding")

    def test_the_constructor_wires_the_names_lock_the_kernel_hands_it(self):
        # the wiring, by execution: a backend built with names_lock=<lock> holds THAT lock at its names write
        lock, seen, real_wn = threading.Lock(), [], sb.write_name
        be = sb.SdkBackend(self.td.name, "/bin/true", lambda *a, **k: None, log=self.logs.append, names_lock=lock)
        be.sessions[SID] = self.live

        def write_name(state_dir, sid, nm, *a, **k):
            seen.append((nm, lock.locked()))
            return real_wn(state_dir, sid, nm, *a, **k)
        with mock.patch.object(sb, "write_name", write_name):
            self.assertTrue(be.rename(SID, "alpha"))
        self.assertEqual(seen, [("alpha", True)], "the names write ran with the handed lock held: %r" % (seen,))
        self.assertFalse(lock.locked(), "and released it")

    def test_write_name_carries_every_field_it_is_not_given_and_clears_on_an_empty_string(self):
        # the carry contract every publication relies on: a None field is the file's value at the write (the name falls
        # back to the sid when the file has none, the others to ""), "" clears; a writer passes only the fields it owns
        d = Path(self.td.name) / "carry"
        (d / "names").mkdir(parents=True)
        (d / "names" / SID).write_text("web\t%s\t#112233\t#ffffff\tE\n" % self.cwd)
        sb.write_name(d, SID, "api")
        self.assertEqual((d / "names" / SID).read_text(), "api\t%s\t#112233\t#ffffff\tE\n" % self.cwd, "a rename carries cwd, colours, emoji")
        sb.write_name(d, SID, None, self.new)
        self.assertEqual((d / "names" / SID).read_text(), "api\t%s\t#112233\t#ffffff\tE\n" % self.new, "a move carries the name, colours, emoji")
        sb.write_name(d, SID, bg="", fg="")
        self.assertEqual((d / "names" / SID).read_text(), "api\t%s\t\t\tE\n" % self.new, "an empty string clears a colour; the emoji rides")
        other = "cccccccc-1111-2222-3333-444444444444"
        sb.write_name(d, other)
        self.assertEqual((d / "names" / other).read_text(), other + "\t\t\t\n", "no file: the sid stands in for the name, the rest empty")
        self.assertEqual(sorted(p.name for p in (d / "names").iterdir()), sorted([SID, other]), "no staging file leaks")


if __name__ == "__main__":
    unittest.main()

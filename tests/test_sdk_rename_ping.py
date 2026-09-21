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


if __name__ == "__main__":
    unittest.main()

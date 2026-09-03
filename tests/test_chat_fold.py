#!/usr/bin/env python3
"""The chat-payload FOLD (issue 903): build_session reuses the rendered events of whole ENDED turns and
reshapes only the tail, and the result is byte-identical to a from-scratch build at every step.

Two builds make the comparison honest: the folding build keeps the module's `_chat_fold` cache warm
(the live path), the reference build runs right after with that cache cleared (always the full path;
the parse cache is shared, since the fold sits above it). Every scenario appends a record group at a
time and compares the WHOLE payload as sorted JSON at each step; the clean-append case also pins the
exact fold count, so the fast path can never rot into full builds while the equivalence stays green.
Each demote gate is then tripped on purpose: equivalence must hold BY DEMOTION, pinned via the counter.

Synthetic only: placeholder ids, invented text, the notes-api demo world (CLAUDE.md)."""
import inspect
import json
import os
import tempfile
import unittest
from datetime import datetime, timezone
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = SourceFileLoader("romp_kernel_chatfold", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd                                      # the kernel's OWN judge module (a second load would rebind nothing)
# a SECOND kernel instance for the deep replay: its fold cache is cleared before every build (always the
# full path) while the first keeps folding fold on fold — the assembly replay's emi/emr arrangement
kmr = SourceFileLoader("romp_kernel_chatfold_ref", os.path.join(BIN, "romp-kernel")).load_module()
MODS = (km, kmr)

SID = "11111111-2222-3333-4444-555555555555"


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def uline(t, text, uuid, parent=None, ps="typed"):
    return {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "promptSource": ps, "message": {"role": "user", "content": text},
            "cwd": "/tmp/notes-api", "version": "2.1.0", "gitBranch": "main"}


def aline(t, text, uuid, parent, tools=(), stop="end_turn", model="claude-sonnet-4"):
    content = [{"type": "text", "text": text}] if text else []
    for i, n in enumerate(tools):
        content.append({"type": "tool_use", "id": "tu_%s_%d" % (uuid, i), "name": n,
                        "input": {"file_path": "/tmp/notes-api/search.py", "old_string": "a", "new_string": "b"}
                        if n == "Edit" else {"command": "uv run pytest -q"}})
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "model": model, "content": content, "stop_reason": stop},
            "cwd": "/tmp/notes-api", "version": "2.1.0", "gitBranch": "main"}


def trline(t, tool_use_id, uuid, parent, content="ok"):
    return {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": tool_use_id,
                                                     "content": content}]}}


class Sess:
    """A synthetic session discovery can see: names/ + projects/<cdir>/<SID>.jsonl under a hermetic state
    root, with the kernel's judge module rebound to it (the ViewBuilder fixture's shape)."""

    def __init__(self, working=True):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.cdir = td / "launchdir"; self.cdir.mkdir()
        proj = td / "projects"
        pdir = proj / jd.re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(self.cdir)))
        pdir.mkdir(parents=True)
        self.tpath = pdir / (SID + ".jsonl")
        self.tpath.write_text("")
        names = td / "names"; names.mkdir()
        (names / SID).write_text("web\t%s\t#abcdef\n" % str(self.cdir))
        self.saved = [(m.jd.NAMES, m.jd.PROJECTS, m.jd.CAPDIR, m.jd.ARCHDIR, m.jd.GOALDIR, m.jd.STATE,
                       m.NAMES, m._tmux_sessions, m._GLOBAL_CLAUDE_MD, m._msg_summaries) for m in MODS]
        self.now = int(__import__("time").time())        # discovery keys on the real clock
        self.t = self.now - 3 * 86400
        state = "working" if working else "idle"
        self.tm = {SID: {"state": state, "since": self.now - 100, "model": "", "effort": "",
                         "context": None, "compactPct": None, "color": None}}
        for m in MODS:                                   # both kernel instances see the same synthetic world
            m.jd.NAMES, m.jd.PROJECTS = names, proj
            m.jd.CAPDIR, m.jd.ARCHDIR, m.jd.GOALDIR = td / "captions", td / "archive", td / "goals"
            m.jd.STATE = td
            m.NAMES = names
            m._GLOBAL_CLAUDE_MD = td / "no-global-claude.md"
            m._tmux_sessions = lambda: self.tm
            m._chat_fold.clear()
            m._parse_cache.clear()
            m._PATH_LINK_CACHE.clear()                  # keyed (sid, uuid): fixtures reuse both across tests
            m._SPACE_PATH_CACHE.clear()
            m._postal_index_memo[0] = None
            m.jd._discover_cache.clear() if isinstance(m.jd._discover_cache, dict) else None
        self.n = 0
        self.last = None

    def close(self):
        for m, sv in zip(MODS, self.saved):
            (m.jd.NAMES, m.jd.PROJECTS, m.jd.CAPDIR, m.jd.ARCHDIR, m.jd.GOALDIR, m.jd.STATE,
             m.NAMES, m._tmux_sessions, m._GLOBAL_CLAUDE_MD, m._msg_summaries) = sv
            m._chat_fold.clear()
        self.td.cleanup()

    def uid(self):
        self.n += 1
        return "aaaaaaaa-0000-0000-0000-%012d" % self.n

    def tick(self, dt=5):
        self.t += dt
        return self.t

    def turn(self, i, tools=("Edit",), close=True):
        """One complete turn: prompt, a tool round (use + result), a closing reply."""
        recs = []
        u = self.uid(); recs.append(uline(self.tick(), "step %d: tighten the notes-api search" % i, u, self.last))
        a = self.uid(); recs.append(aline(self.tick(), "Round %d: adjusting `search.py`." % i, a, u, tools=tools, stop="tool_use"))
        r = self.uid(); recs.append(trline(self.tick(), "tu_%s_0" % a, r, a, content="ok\n"))
        self.last = r
        if close:
            b = self.uid(); recs.append(aline(self.tick(), "Step %d done." % i, b, r))
            self.last = b
        return recs

    def append(self, recs):
        with open(self.tpath, "a") as f:
            for r in recs:
                f.write(json.dumps(r) + "\n")
        os.utime(self.tpath, None)

    def rewrite(self, recs):
        self.tpath.write_text("".join(json.dumps(r) + "\n" for r in recs))
        os.utime(self.tpath, None)

    def build(self, mod=None):
        return (mod or km).build_session(SID, self.now, self.tm)


def _dump(m):
    return json.dumps(m, sort_keys=True, default=str)


class _Fold(unittest.TestCase):
    def setUp(self):
        self.s = Sess()

    def tearDown(self):
        self.s.close()

    def equiv(self, label):
        """Folding build == full build (cache cleared), both at the same clock; re-warm afterwards.
        Returns the folding build."""
        inc = self.s.build()
        km._chat_fold.clear()
        ref = self.s.build()
        self.assertEqual(_dump(ref), _dump(inc), "fold diverged from full at %s" % label)
        self.s.build()                                  # the reference cleared the cache; warm it again
        return inc

    def grow(self, n_turns):
        for i in range(n_turns):
            self.s.append(self.s.turn(i))
            self.equiv("turn %d" % i)


class Replay(_Fold):
    def test_clean_append_stream_matches_full_and_actually_folds(self):
        # the red-first pin for the feature: equivalence alone would pass if every build were full
        f0 = km._CHAT_FOLD_STATS["fold"]
        n = 8
        self.grow(n)
        # per step from the 3rd turn on: the folding build and the re-warm build both fold; at 2 turns the
        # cache is still cold (nothing sealed while there was one turn) so only the re-warm folds
        self.assertEqual(km._CHAT_FOLD_STATS["fold"] - f0, 1 + 2 * (n - 2),
                         "fold count drifted — some record kind silently demotes to full")

    def test_the_last_turn_is_never_sealed(self):
        self.grow(3)
        e = km._chat_fold_get(SID)
        self.assertIsNotNone(e)
        self.assertEqual(e["n"], 2, "three turns → a prefix of the two ENDED ones; the last stays live")

    def test_prefix_dicts_are_handed_back_by_identity_and_never_written(self):
        self.grow(3)
        a = self.s.build()
        e = km._chat_fold_get(SID)
        before = _dump(e["events"])
        self.s.append(self.s.turn(3))
        b = self.s.build()
        self.assertGreater(len(e["events"]), 0)
        # the payload opens with the head system card, so the prefix sits at an offset: find it by identity
        off = next(i for i, ev in enumerate(b["events"]) if ev is e["events"][0])
        for i, ev in enumerate(e["events"]):
            self.assertIs(b["events"][off + i], ev, "prefix event %d must be the SAME dict (the diff's identity path)" % i)
        self.assertEqual(_dump(e["events"]), before, "a fold build wrote into a sealed prefix event")
        off_a = next(i for i, ev in enumerate(a["events"]) if ev is e["events"][0])
        self.assertIs(a["events"][off_a], b["events"][off])

    def test_an_open_turn_folds_too(self):
        self.grow(2)
        self.s.append(self.s.turn(2, close=False))     # the tail turn is OPEN (a tool round with no reply yet)
        self.equiv("open tail")
        self.assertEqual(km._chat_fold_get(SID)["n"], 2)

    def test_episode_render_bypasses_the_cache(self):
        self.grow(3)
        b0 = km._CHAT_FOLD_STATS["bypass"]
        e = km._chat_fold_get(SID)
        m = km.build_session(SID, self.s.now, self.s.tm, path_override=str(self.s.tpath))
        self.assertEqual(m.get("type"), "session")
        self.assertEqual(km._CHAT_FOLD_STATS["bypass"], b0 + 1)
        self.assertIs(km._chat_fold_get(SID), e, "an override render must not touch the live prefix")


class Gates(_Fold):
    def _demotes(self, reason, label):
        g = "g:" + reason
        n0 = km._CHAT_FOLD_STATS.get(g, 0)
        inc = self.equiv(label)
        self.assertGreater(km._CHAT_FOLD_STATS.get(g, 0), n0, "the %s gate must demote here" % reason)
        return inc

    def test_a_tool_result_landing_in_a_later_turn_demotes(self):
        # turn 1 ENDS with a tool call still unanswered (a typed prompt only opens a new turn after an
        # ended one — an unfinished turn absorbs it); the prompt opens turn 2; THEN the result lands, in
        # turn 2 (non-openers join the current turn) — it fills turn 1's card, which the prefix holds
        s = self.s
        u1 = s.uid(); s.append([uline(s.tick(), "start", u1, None)])
        a1 = s.uid(); s.append([aline(s.tick(), "Editing.", a1, u1, tools=("Edit",), stop="end_turn")])
        u2 = s.uid(); s.append([uline(s.tick(), "also check the tests", u2, a1)])
        a2 = s.uid(); s.append([aline(s.tick(), "Will do.", a2, u2)])
        self.equiv("two turns, tool open")
        self.assertIn("tu_%s_0" % a1, km._chat_fold_get(SID)["open_tools"])
        r = s.uid(); s.append([trline(s.tick(), "tu_%s_0" % a1, r, a2, content="edited late")])
        inc = self._demotes("tool-fill", "late tool result")
        card = next(ev for ev in inc["events"] if ev.get("kind") == "tool")
        self.assertEqual(card.get("output"), "edited late")

    def test_a_side_store_note_inside_the_prefix_demotes(self):
        self.grow(3)
        st = jd.STATE / "states"; st.mkdir(exist_ok=True)
        e = km._chat_fold_get(SID)
        t_in = e["last_t"] - 3                          # a recovery note timed INSIDE the sealed prefix
        with open(st / (SID + ".jsonl"), "a") as f:
            f.write(json.dumps({"t": t_in, "retriesRecovered": 2}) + "\n")
        n0 = km._CHAT_FOLD_STATS.get("g:note", 0) + km._CHAT_FOLD_STATS.get("g:turnfp", 0)
        inc = self.equiv("note in prefix")
        n1 = km._CHAT_FOLD_STATS.get("g:note", 0) + km._CHAT_FOLD_STATS.get("g:turnfp", 0)
        self.assertGreater(n1, n0, "a side-store row inside the prefix must demote")
        self.assertTrue(any(ev.get("kind") == "retried" for ev in inc["events"]))

    def test_a_seam_change_demotes(self):
        self.grow(3)
        jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        e = km._chat_fold_get(SID)
        (jd.GOALDIR / (SID + ".json")).write_text(json.dumps({
            "rompUuid": SID, "seq": 1, "nodes": {}, "placements": {}, "status": {},
            "seams": [{"segs": ["nowhere"], "t": e["last_t"] - 1, "top": SID + ":g1", "text": "Ship it"}]}))
        self._demotes("seam", "seam written")

    def test_a_path_token_that_resolves_later_demotes(self):
        s = self.s
        u1 = s.uid(); s.append([uline(s.tick(), "please write the summary to `docs/notes.md` when done", u1, None)])
        a1 = s.uid(); s.append([aline(s.tick(), "Noted.", a1, u1)])
        s.last = a1                                     # the next turn chains from this reply (one graph, one leaf)
        s.append(s.turn(1))
        inc = self.equiv("mention before the file exists")
        ev = next(ev for ev in inc["events"] if ev.get("kind") == "user" and "notes.md" in (ev.get("md") or ""))
        self.assertEqual(ev.get("pathLinks"), {}, "tokens exist but none resolved yet")
        self.assertTrue(km._chat_fold_get(SID)["pl_pending"], "the sealed prefix remembers the pending token")
        (s.cdir / "docs").mkdir()
        (s.cdir / "docs" / "notes.md").write_text("# summary\n")
        inc2 = self._demotes("path-link", "file appeared")
        ev2 = next(ev for ev in inc2["events"] if ev.get("kind") == "user" and "notes.md" in (ev.get("md") or ""))
        self.assertEqual(ev2.get("pathLinks"), {"docs/notes.md": "docs/notes.md"})

    def test_a_rewrite_that_shortens_the_transcript_demotes(self):
        self.grow(4)
        recs = [json.loads(l) for l in self.s.tpath.read_text().splitlines() if l.strip()]
        self.s.rewrite(recs[:-4])                       # the last turn is gone: a rewind, not an append
        n0 = km._CHAT_FOLD_STATS.get("g:parse", 0) + km._CHAT_FOLD_STATS.get("g:shrink", 0)
        self.equiv("shortened")
        self.assertGreater(km._CHAT_FOLD_STATS.get("g:parse", 0) + km._CHAT_FOLD_STATS.get("g:shrink", 0), n0)

    def test_a_new_complete_turn_extends_the_prefix(self):
        self.grow(2)
        self.assertEqual(km._chat_fold_get(SID)["n"], 1)
        self.s.append(self.s.turn(2) + self.s.turn(3))  # two turns land between builds
        self.equiv("two turns at once")
        self.assertEqual(km._chat_fold_get(SID)["n"], 3, "every ended turn before the last is sealed")


ROMP_AUTO = "<!-- romp-injected --><!-- romp-auto -->Where does this stand? If nothing is blocking you, keep going."
ROMP_RESTART = ("<!-- romp-injected --><!-- romp-system -->[romp] The romp kernel restarted and cut this "
                "session's in-flight turn; the session has been resumed with its history intact.")


class Seams(_Fold):
    def _cut_turn(self, i):
        """A turn cut by a kernel restart: prompt, a tool call in flight, the CLI's stop record, its
        synthetic settle reply — the shape every restart mints."""
        s = self.s
        u = s.uid(); recs = [uline(s.tick(), "step %d: reindex the notes" % i, u, s.last)]
        a = s.uid(); recs.append(aline(s.tick(), "Reindexing.", a, u, tools=("Bash",), stop="tool_use"))
        m = s.uid(); recs.append(uline(s.tick(), "[Request interrupted by user]", m, a))
        z = s.uid(); recs.append(aline(s.tick(), "No response requested.", z, m, model="<synthetic>"))
        s.last = z
        return recs

    def test_an_undecided_seam_is_never_sealed_and_its_cause_lands_later(self):
        # T0-T1 normal; T2 is cut; T3 opens with a romp auto-nudge (not a decider); the fold must hold the
        # boundary BEFORE T2 through every build — including the one where T2 stops being the first tail
        # turn — so that when the restart notice lands in T4 the marker is stamped and the settle dropped
        s = self.s
        self.grow(2)
        s.append(self._cut_turn(2))
        self.equiv("cut turn is last")
        def romp_turn(text, reply):                       # a romp-injected prompt and the agent's reply: one ended turn
            u_ = s.uid(); s.append([uline(s.tick(), text, u_, s.last)])
            a_ = s.uid(); s.append([aline(s.tick(), reply, a_, u_)]); s.last = a_
        romp_turn(ROMP_AUTO, "Still on the reindex.")
        self.equiv("nudge turn after the cut")
        self.assertLessEqual(km._chat_fold_get(SID)["n"], 2, "the undecided seam holds the boundary before its turn")
        romp_turn(ROMP_AUTO, "Nothing new yet.")          # a second non-deciding turn: the seam stays undecided
        self.equiv("a second nudge turn")
        self.assertLessEqual(km._chat_fold_get(SID)["n"], 2, "…and keeps holding it while more non-deciding turns land")
        romp_turn(ROMP_RESTART, "Resuming where I left off.")
        inc = self.equiv("restart notice landed")
        marker = next(ev for ev in inc["events"] if ev.get("interruptMarker"))
        self.assertEqual(marker.get("interruptCause"), "restart")
        self.assertTrue(marker.get("settleUuids"))
        self.assertFalse(any(ev.get("interruptSettle") for ev in inc["events"]), "the machine cut's settle line is dropped")
        s.append(s.turn(6))
        self.equiv("decided seam seals with the next turn")
        self.assertGreaterEqual(km._chat_fold_get(SID)["n"], 4, "once decided, the seam's turn seals like any other")


class PostalCards(_Fold):
    MID = "1788400000.100_1.TESTHOST"
    PEER = "22222222-3333-4444-5555-666666666666"

    def _log(self):
        d = jd.STATE / "timeline"; d.mkdir(exist_ok=True)
        (d / "messages.jsonl").write_text(json.dumps({"ev": "sent", "id": self.MID, "from": "api", "from_id": self.PEER,
                                                      "to_id": SID, "body": "the api tests are green now",
                                                      "kind": "coordinate", "t": self.s.t}) + "\n")

    def test_a_caption_rewritten_after_the_seal_refreshes_the_card(self):
        # the judge writes a LIVE caption under an id it later overwrites with the final one: a card
        # sealed complete between the two must not keep the live gloss forever
        s = self.s
        self._log()
        caps = {self.MID: "peer: tests green (live)"}
        for m in MODS:
            m._msg_summaries = lambda caps=caps: dict(caps)
        self.grow(1)
        u = s.uid(); s.append([uline(s.tick(), "<!-- romp-msg-id: %s -->\nthe api tests are green now" % self.MID, u, s.last)])
        a = s.uid(); s.append([aline(s.tick(), "Noted, thanks.", a, u)]); s.last = a
        s.append(s.turn(2))
        inc = self.equiv("card sealed with the live caption")
        card = next(ev for ev in inc["events"] if ev.get("kind") == "postal-service")
        self.assertEqual(card.get("summary"), "peer: tests green (live)")
        caps[self.MID] = "peer: api tests green"          # the FINAL caption lands
        for m in MODS:
            m._judge_gen[0] += 1
        n0 = km._CHAT_FOLD_STATS.get("g:postal", 0)
        inc2 = self.equiv("caption rewritten")
        self.assertGreater(km._CHAT_FOLD_STATS.get("g:postal", 0), n0)
        card2 = next(ev for ev in inc2["events"] if ev.get("kind") == "postal-service")
        self.assertEqual(card2.get("summary"), "peer: api tests green")


class TaskOutputs(_Fold):
    def test_a_notification_whose_output_file_grows_after_the_seal_demotes(self):
        s = self.s
        out = s.cdir / "nightly.out"
        out.write_text("line 1\n")
        note = ("<task-notification>\n<status>completed</status>\n<summary>nightly check</summary>\n"
                "<output-file>%s</output-file>\n<tool-use-id>toolu_bg_1</tool-use-id>\n</task-notification>" % out)
        self.grow(1)
        u = s.uid(); s.append([uline(s.tick(), note, u, s.last)])
        a = s.uid(); s.append([aline(s.tick(), "The nightly check passed.", a, u)]); s.last = a
        s.append(s.turn(2))
        inc = self.equiv("notification sealed")
        card = next(ev for ev in inc["events"] if ev.get("taskOutputs"))
        self.assertIn("line 1", card["taskOutputs"]["toolu_bg_1"]["output"])
        self.assertTrue(km._chat_fold_get(SID)["task_outs"], "the sealed card's output file is remembered")
        with open(out, "a") as f:
            f.write("line 2\n")
        os.utime(out, None)
        n0 = km._CHAT_FOLD_STATS.get("g:task-output", 0)
        inc2 = self.equiv("output grew")
        self.assertGreater(km._CHAT_FOLD_STATS.get("g:task-output", 0), n0)
        card2 = next(ev for ev in inc2["events"] if ev.get("taskOutputs"))
        self.assertIn("line 2", card2["taskOutputs"]["toolu_bg_1"]["output"])
        out.unlink()                                     # …and a vanished file renders differently too
        self.equiv("output vanished")


class DeepReplay(_Fold):
    def test_record_by_record_fold_on_fold_equals_a_full_build_at_every_step(self):
        # the folding kernel is never reset (fold on fold, deep chains); the reference kernel clears its
        # fold cache before every build — two module instances, one synthetic world
        s = self.s
        recs = []
        for i in range(6):
            recs += s.turn(i)
        s.last = None
        recs += self.__class__._interleave(self, recs)
        f0 = km._CHAT_FOLD_STATS["fold"]
        for i, r in enumerate(recs):
            s.append([r])
            inc = s.build(km)
            kmr._chat_fold.clear()
            ref = s.build(kmr)
            self.assertEqual(_dump(ref), _dump(inc), "fold-on-fold diverged from full at record %d" % (i + 1))
        self.assertGreater(km._CHAT_FOLD_STATS["fold"] - f0, len(recs) // 2, "the chain must actually fold")

    @staticmethod
    def _interleave(self, recs):
        # a nudge, a cut turn and its late restart notice, in the same stream
        s = self.s
        s.last = recs[-1]["uuid"]
        extra = []
        n_ = s.uid(); extra.append(uline(s.tick(), ROMP_AUTO, n_, s.last)); s.last = n_
        u = s.uid(); extra.append(uline(s.tick(), "step 6: reindex", u, s.last))
        a = s.uid(); extra.append(aline(s.tick(), "Reindexing.", a, u, tools=("Bash",), stop="tool_use"))
        m = s.uid(); extra.append(uline(s.tick(), "[Request interrupted by user]", m, a))
        z = s.uid(); extra.append(aline(s.tick(), "No response requested.", z, m, model="<synthetic>"))
        n2 = s.uid(); extra.append(uline(s.tick(), ROMP_AUTO, n2, z)); s.last = n2
        r_ = s.uid(); extra.append(uline(s.tick(), ROMP_RESTART, r_, s.last)); s.last = r_   # decides the seam
        extra += s.turn(7)
        extra += s.turn(8)
        return extra


class Fallback(_Fold):
    def test_a_gate_check_failure_counts_once_drops_the_entry_and_builds_in_full(self):
        self.grow(3)
        class Boom(dict):                             # read only by the gate check (the parse writes it)
            def get(self, *a, **k):
                raise RuntimeError("boom")
        saved = km._parse_mode
        km._parse_mode = Boom(saved)
        try:
            fb0, g0 = km._CHAT_FOLD_STATS["fallback"], km._CHAT_FOLD_STATS.get("g:fallback", 0)
            self.s.append(self.s.turn(3))
            inc = self.s.build()
        finally:
            km._parse_mode = saved
        self.assertEqual(km._CHAT_FOLD_STATS["fallback"], fb0 + 1)
        self.assertEqual(km._CHAT_FOLD_STATS.get("g:fallback", 0), g0, "a fallback is never also a demote")
        km._chat_fold.clear()
        self.assertEqual(_dump(self.s.build()), _dump(inc), "the fallback build is a correct full build")


class DeltaSend(_Fold):
    def test_a_fold_build_ships_as_a_tail_from_the_first_changed_index(self):
        self.grow(2)
        m1 = self.s.build()
        sent = []
        c = {"send": lambda body: sent.append(json.loads(body)), "sent": {}, "echat": {}}
        km._send_chat(c, m1, None, 0, False)
        self.assertEqual(sent[-1]["type"], "session")
        self.s.append(self.s.turn(2))
        m2 = self.s.build()                              # a fold: the prefix dicts are m1's
        change_from = km._chat_diff(m1["events"], m2["events"])
        self.assertGreater(change_from, 0)
        km._send_chat(c, m2, None, change_from, False)
        tail = sent[-1]
        self.assertEqual(tail["type"], "chatTail")
        self.assertEqual(tail["from"], change_from)
        self.assertEqual(len(tail["events"]), len(m2["events"]) - change_from)
        self.assertTrue(any(ev.get("md", "").startswith("step 2") for ev in tail["events"]))


class Diff(unittest.TestCase):
    def test_chat_diff_takes_the_identity_path_before_comparing(self):
        class Bomb(dict):
            def __eq__(self, other):
                raise AssertionError("value compare reached on an identical object")
            __hash__ = dict.__hash__
        b = Bomb(uuid="1")
        self.assertEqual(km._chat_diff([b], [b]), 1, "same object → equal without a value compare")
        a = {"uuid": "1", "x": 1}
        self.assertEqual(km._chat_diff([a, {"uuid": "2"}], [a, {"uuid": "2"}, {"uuid": "3"}]), 2)
        self.assertEqual(km._chat_diff([a, {"uuid": "2"}], [a, {"uuid": "2", "output": "x"}]), 1)


class SessionMetaFold(unittest.TestCase):
    def test_meta_folds_appends_and_refolds_on_rewrite(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "t.jsonl")
            recs = [uline(1000, "hi", "u1"), aline(1005, "yo", "a1", "u1", tools=("Edit",), stop="tool_use")]
            Path(p).write_text("".join(json.dumps(r) + "\n" for r in recs))
            km._session_meta_cache.pop(p, None)
            m1 = km._session_meta(p)
            self.assertEqual((m1["cwd"], m1["gitBranch"], m1["lastEditPath"]),
                             ("/tmp/notes-api", "main", "/tmp/notes-api/search.py"))
            r3 = uline(1010, "next", "u2", "a1"); r3["gitBranch"] = "feature"
            with open(p, "a") as f:
                f.write(json.dumps(r3) + "\n")
            m2 = km._session_meta(p)
            km._session_meta_cache.pop(p, None)
            fresh = km._session_meta(p)
            self.assertEqual(m2, fresh, "the folded meta must equal a from-scratch read")
            self.assertEqual(m2["gitBranch"], "feature")
            Path(p).write_text(json.dumps(recs[0]) + "\n")   # a rewrite: prefix identity is gone
            m3 = km._session_meta(p)
            self.assertEqual(m3["gitBranch"], "main")
            self.assertEqual(m3["lastEditPath"], "")


class Wiring(unittest.TestCase):
    def test_version_reports_the_fold_counters_beside_parse(self):
        src = inspect.getsource(km)
        self.assertIn('"chatfold": dict(_CHAT_FOLD_STATS)', src)
        self.assertIn('"parse": dict(em._ASM_STATS)', src)

    def test_a_tab_switch_wakes_the_pusher(self):
        src = inspect.getsource(km)
        i = src.index('msg.get("type") == "activeTab"')
        self.assertIn("_pusher_wake.set()", src[i:i + 400], "the tab switch IS the event; no 0.5 s backstop wait")

    def test_perf_line_carries_the_fold_fields(self):
        src = inspect.getsource(km)
        self.assertIn('fold=_chat_fold_last_info().get("fold", 0)', src)


if __name__ == "__main__":
    unittest.main()

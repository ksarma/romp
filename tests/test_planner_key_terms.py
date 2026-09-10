#!/usr/bin/env python3
"""The three fork terms of the planner's skip key (kernel/judge.py _plan_key; the upstream fold of 2026-09-09, slice 3,
ruling 2): cleared.jsonl by file identity, this session's death marker (STATE/gone/<sid>.json) by file identity, and
this session's stall slice (auto-nudge.json's records for its goals, read by value; _stall_term).

Upstream's #1173 and #1179 key the planner skip on the parse cache's pair, the store trio, the episode log, the leaf's
task store, the reg file, the captions file and the background launches' expiry crossing. The planner's decision path
also reads those three files: plan_units -> _live_anchor_gone -> _view_cleared reads cleared.jsonl, the settle's
_cli_epoch reads the death marker (a tmux session has no reg to move on a death), and rollup_status's stall-warn
retire reads stalled_facts. A key that omits an input the pass reads serves a skipped pass over a change: a clear, a
death or a stall would wait for an unrelated write to re-plan the session. One executed test per term: the key differs
before and after the input moves, and the planner is not skipped on the change; each fails when its term is dropped
from _plan_key (verified against a scratch copy of judge.py with the term removed). The third term's failure shape is
pinned too: a file that exists and does not read is a fresh sentinel per read (never equal), so the session is planned
every pass rather than skipped over a slice the pass could not see. An offer candidate
(upstream/2026-09-09-planner-key-blind-terms.md), the twin of the nudge gate's cleared-set term.

Private synthetic sids (a goal-minting fixture never uses the shared placeholder sid: its override journal is replayed
on every load), invented prompts, a temp state root and a temp Claude config root; the sids' journals are removed in
tearDown. The harness is upstream's tests/test_planner_skip.py's, with the planner's model calls stubbed."""
import json
import os
import re
import tempfile
import unittest
from datetime import datetime, timezone
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
jd = load_source("romp_judge_planner_key_terms", os.path.join(BIN, "romp-judge"))

A = "dddddddd-1111-2222-3333-4444444444a1"        # private synthetic sids, never the shared placeholder
B = "dddddddd-1111-2222-3333-4444444444a2"
C = "dddddddd-1111-2222-3333-4444444444a3"
OTHER = "dddddddd-1111-2222-3333-4444444444a9"    # a session outside the world: its rows must move no key by sid
NOW = 1781100000
T0 = NOW - 3600


def iso(t):
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def uline(t, text, uuid, parent=None):
    return {"type": "user", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "user", "content": text}, "promptSource": "typed"}


def aline(t, text, uuid, parent):
    return {"type": "assistant", "timestamp": iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}}


class _World(unittest.TestCase):
    SIDS = (A, B, C)
    PROMPTS = {A: "wire up the export button", B: "retire the request cap", C: "fix the mobile tab width"}

    def setUp(self):
        self.saved = (jd.STATE, jd.NAMES, jd.PROJECTS, jd.plan_llm, jd.opener_llm, jd.group_llm, jd._judge_run,
                      os.environ.get("CLAUDE_CONFIG_DIR"))
        jd.opener_llm = lambda text, menu, sibling_num=None, **kw: '{"ops":[{"why":"a new ask","do":"mint","text":"Ship: %s"}]}' % text.split("\n")[0][:40]
        jd.plan_llm = lambda *a, **kw: '{"ops":[{"why":"a new ask","do":"mint","text":"Ship: %s"}]}' % str(a[0] if a else "").split("\n")[0][:40]
        jd.group_llm = lambda menu, **kw: '{"ops":[]}'
        jd._judge_run = lambda *a, **kw: "{}"
        self._make_world()

    def tearDown(self):
        for sid in self.SIDS:
            try:
                (jd._overrides_dir() / (sid + ".jsonl")).unlink()   # a sid's journal never outlives its test
            except OSError:
                pass
        self._drop_world()
        (jd.STATE, jd.NAMES, jd.PROJECTS, jd.plan_llm, jd.opener_llm, jd.group_llm, jd._judge_run, cfg) = self.saved
        jd._rebind_state(jd.STATE)
        if cfg is None:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)
        else:
            os.environ["CLAUDE_CONFIG_DIR"] = cfg

    def _make_world(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        jd._rebind_state(td / "state")
        self.cfg = td / "claude"
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.cfg)
        cdir = td / "launchdir"; cdir.mkdir()
        proj = self.cfg / "projects"
        self.proj_dir = proj / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        self.proj_dir.mkdir(parents=True)
        names = td / "names"; names.mkdir()
        for i, sid in enumerate(self.SIDS):
            (names / sid).write_text("worker%d\t%s\t#abcdef\n" % (i, str(cdir)))
        jd.NAMES, jd.PROJECTS = names, proj
        jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        self.recs = {sid: [] for sid in self.SIDS}
        self._reset()
        for sid in self.SIDS:
            self.prompt(sid, T0 + 10 * self.SIDS.index(sid))

    def _drop_world(self):
        self._reset()
        self.td.cleanup()

    @staticmethod
    def _reset():
        jd._PARSE_CACHE.clear(); jd._CHAIN_MEMO.clear(); jd._episode_memo.clear(); jd._shared_clear()
        jd._PLANNER_SEEN.clear(); jd._lastsid_memo.clear(); jd._BG_SCAN_CACHE.clear(); jd._gone_memo.clear()
        for k in jd._PLANNER_STATS:
            jd._PLANNER_STATS[k] = 0
        jd._discover_cache.clear()

    def prompt(self, sid, t, text=None):
        """A human prompt and its reply land in `sid`'s transcript: one plan unit's worth."""
        n = len(self.recs[sid]) // 2 + 1
        parent = self.recs[sid][-1]["uuid"] if self.recs[sid] else None
        text = text or self.PROMPTS[sid]
        self.recs[sid] += [uline(t, text, "u%d" % n, parent), aline(t + 30, "Done: %s." % text, "a%d" % n, "u%d" % n)]
        p = self.proj_dir / (sid + ".jsonl")
        p.write_text("\n".join(json.dumps(r) for r in self.recs[sid]) + "\n")
        os.utime(p, (t + 60, t + 60))                       # a distinct mtime per write: the parse key moves
        jd._discover_cache.clear()

    def run_pass(self, now=NOW):
        """One planner pass; returns the gate counters' deltas (planned, skipped, recorded)."""
        before = jd.planner_skip_stats()
        jd._discover_cache.clear()
        jd.run_plan(now=now)
        after = jd.planner_skip_stats()
        return tuple(after[k] - before[k] for k in ("planned", "skipped", "recorded"))

    def settle(self):
        """Plan until every session has nothing to do and is recorded; then a pass skips all three."""
        for _ in range(4):
            p, s, r = self.run_pass()
            if p == 0:
                break
        self.assertEqual(self.run_pass(), (0, 3, 0), "settled: all three skipped")

    def key(self, sid):
        """The planner's skip key for `sid`, as _plan_session takes it: the cache's parse bound to the session object."""
        path = str(self.proj_dir / (sid + ".jsonl"))
        session = jd.parsed_session(sid, [path], NOW)
        k = jd._plan_key(sid, path, session, NOW)
        self.assertIsNotNone(k, "the parse is the cache's own")
        return k

    def top(self, sid):
        store = json.loads((jd.GOALDIR / (sid + ".json")).read_text())
        return next(nid for nid, n in store["nodes"].items() if n.get("parentId") is None)


class PlannerKeyTerms(_World):
    def test_a_cleared_row_moves_every_sessions_key_and_re_plans_them(self):
        # cleared.jsonl is one file for every session (plan_units -> _live_anchor_gone -> _view_cleared reads it whole), so
        # a row moves every key; the row names a node outside the world so nothing but the file's identity changes
        self.settle()
        before = {sid: self.key(sid) for sid in self.SIDS}
        with (jd.STATE / "cleared.jsonl").open("a") as f:
            f.write(json.dumps({"id": OTHER + ":g1", "op": "clear", "t": NOW}) + "\n")
        after = {sid: self.key(sid) for sid in self.SIDS}
        for sid in self.SIDS:
            self.assertNotEqual(after[sid], before[sid], "cleared.jsonl is a term of the key: a row moves it")
        self.assertEqual(self.run_pass(), (3, 0, 3), "every session planned on the row, none skipped; nothing to do, so recorded")
        self.assertEqual(self.run_pass(), (0, 3, 0), "then skipped under the new key")

    def test_a_death_marker_moves_that_sessions_key_and_re_plans_it(self):
        # the settle reads the marker through _cli_epoch (a dead tmux session has no reg to move), so the marker is A's
        # input alone: A's key moves, B's does not, and the pass plans A and skips B and C
        self.settle()
        ka, kb = self.key(A), self.key(B)
        jd._write_death_marker(A, {"t": NOW - 10, "by": "probe", "endedAt": NOW - 10})
        self.assertNotEqual(self.key(A), ka, "the death marker is a term of the key")
        self.assertEqual(self.key(B), kb, "another session's marker is not: the term is by sid")
        self.assertEqual(self.run_pass()[0:2], (1, 2), "A planned on its marker, B and C skipped")

    def test_a_stall_record_for_this_session_moves_its_key_and_re_plans_it_and_an_unreadable_file_never_skips(self):
        # rollup_status's stall-warn retire reads stalled_facts, this sid's records in auto-nudge.json by value, so a
        # record on A's goal moves A's key and not B's (the whole file moved for both); a file that exists and does not
        # read is a fresh sentinel per read (_stall_term, the listing-error rule of _task_store_key), so no recorded key
        # ever equals it and every session is planned until the file reads again
        self.settle()
        ka, kb = self.key(A), self.key(B)
        an = jd.STATE / "auto-nudge.json"
        an.write_text(json.dumps({"enabled": False, "deferred": {self.top(A): {"at": NOW, "why": "waiting on the closer", "sid": A}}}))
        self.assertNotEqual(self.key(A), ka, "this session's stall slice is a term of the key")
        self.assertEqual(self.key(B), kb, "another session's record leaves this key alone: the slice is read by sid, by value")
        self.assertEqual(self.run_pass()[0:2], (1, 2), "A planned on its stall record, B and C skipped")
        self.settle()
        an.write_text("{ not a document")                              # exists and does not parse: the strict read raises
        self.assertNotEqual(self.key(A), self.key(A), "a slice that cannot be read is a fresh sentinel per read: never equal")
        for i in range(2):
            self.assertEqual(self.run_pass()[0:2], (3, 0), "pass %d: every session planned, none skipped, while the file "
                                                            "cannot be read" % i)
        an.write_text(json.dumps({"enabled": False, "deferred": {}}))  # readable again: the world settles as before
        self.settle()


if __name__ == "__main__":
    unittest.main()

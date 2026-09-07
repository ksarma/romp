#!/usr/bin/env python3
"""The chat-build signature's input census (round-4 performance plan, item P4, 2026-09-07).

_built_chat serves a background tab's payload from its cache while _chat_build_sig(sess) is unchanged,
so the signature must contain every input build_session reads that can change the payload. This
module is the census that argument rests on: CENSUS classifies every module-level helper build_session
calls by name, DOTTED every attribute call on a module object or a backend local, and GLOBALS every
module global it reads without calling. Each entry is one of:

  sig    an input the signature folds, under the named label (_CHAT_SIG_LABELS);
  pure   a function of inputs already classified (the parse, the events, the args, a store the
         signature keys) and nothing else — the note says of what;
  memo   a cache whose own key is made of classified inputs, or that latches its first answer for
         the process's life (then constant, and an uncached build now would read the same entry);
  const  fixed for the life of the process (a module constant, an environment value, a path);
  out    a write or a counter, not an input.

The test derives the three sets from build_session's source by AST and requires each to EQUAL the
table's keys, so a helper added to build_session without a classification fails the suite, and so
does a stale entry for one removed. A second test requires every `sig` label to exist in the
signature's label tuple. Names, not lines: the tables say what each read is, the signature module
says how it is keyed. The census enforces ONE level: the helpers build_session calls directly. What
each helper reads in turn is the classification's claim (the note), verified by the differential
tests below that move one input at a time, not derived; a helper that gains a new read keeps its
entry and is caught only if a differential test covers the input.

Synthetic fixtures only.
"""
import ast
import inspect
import os
import tempfile
import unittest

from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()      # hermetic state BEFORE the load (import-time root)
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_chatsiginputs", os.path.join(BIN, "romp-kernel"))


# ── the read inventory ───────────────────────────────────────────────────────────────────────────
# Module-level functions build_session calls by name. Where a helper reads through several inputs the
# label names the one that identifies it and the note lists the rest; every listed input has a label.
CENSUS = {
    "_agent_open_set": ("pure", "over the goal store (store)"),
    "_api_error": ("pure", "the transcript's tail, memoized on its (mtime, size) (transcript)"),
    "_apply_rewind_hold": ("sig", "hold", "and the store; the kept-chain read is over the transcript, states and cut"),
    "_archive_roots": ("sig", "store", "the goals-archive identity is the store triple's third member"),
    "_ask_fill_answers": ("pure", "over a tool event and its result block"),
    "_ask_fill_chosen": ("pure", "over a tool event's output string"),
    "_atom_md": ("pure", "over an atom"),
    "_atom_user_texts": ("pure", "over an atom"),
    "_auth_both": ("sig", "acct", "the credential store's login and the manager's key presence"),
    "_awaiting_task_descs": ("sig", "bg", "the live task rows; the split reads the stamped tops (stamp), the store and the transcript"),
    "_awaiting_task_ids": ("sig", "bg", "as _awaiting_task_descs"),
    "_awaiting_items_payload": ("sig", "bg", "the wait's own rows (as _session_awaiting), else the rows in flight mid-turn: the row's agents (row), the live task rows and the watches (watch)"),
    "_bg_tasks": ("sig", "row", "the row's live task set gates the transcript's scan; each output tail is a taskout dep; the spawn epoch reads reg and gone"),
    "_chat_cleared_key": ("sig", "cleared"),
    "_chat_agent_open_at": ("pure", "over the events"),
    "_chat_agents_moved": ("pure", "the fold's sealed-agent gate: over the sidecar map (a taskout dep, recorded by _subagent_meta_map), the transcript's task scan (transcript), the row and the spawn epoch (row, reg, gone)"),
    "_chat_fold_count": ("out", "a fold counter"),
    "_chat_fold_demote": ("out", "a fold counter"),
    "_chat_fold_get": ("memo", "the sealed prefix: every gate it checks is an input classified here, and its output is the events an unfolded build produces"),
    "_chat_fold_put": ("out", "the fold entry's write"),
    "_chat_memo_bump": ("out", "a memo counter's increment"),
    "_chat_postal_key": ("sig", "postal", "the log's identity, folded when the payload carries postal traffic"),
    "_chat_postal_relevant": ("pure", "over a raw event"),
    "_chat_seam_open_at": ("pure", "over the events"),
    "_chat_stat_key": ("sig", "taskout", "the fold's per-output identity; the same stat the taskout dep re-takes"),
    "_chat_turn_fp": ("pure", "over a turn"),
    "_claude_account_label": ("sig", "acct"),
    "_claudemd_docs": ("sig", "claudemd", "the CLAUDE.md files on the chain from the cwd to its git root, plus the global one"),
    "_cleared_ids": ("sig", "cleared"),
    "_clearing_now": ("sig", "backend", "the backend's clearing bracket"),
    "_cmd_gestures": ("sig", "states"),
    "_colormap": ("sig", "colormap"),
    "_compacting": ("sig", "backend", "the backend's compacting bracket; else the row's state and since, the parse, and the optimistic stamp's clock boolean (clock)"),
    "_echo_overtaken": ("pure", "over an atom and the parse's human floor"),
    "_edit_diff": ("pure", "over a tool input"),
    "_effort_changes": ("sig", "states"),
    "_effort_color": ("pure", "over the effort string and the colormap name"),
    "_effort_tone": ("pure", "over the effort string"),
    "_feed_needs_input_of": ("sig", "needs"),
    "_fold_tasks": ("memo", "pure over the parse's turns (transcript, live)"),
    "_genuine_queued": ("pure", "over a queued text"),
    "_git_branch": ("sig", "cwd"),
    "_github_repo_of": ("sig", "cwd"),
    "_has_tmux": ("const", "whether a tmux binary is on PATH"),
    "_human_turn_floor": ("pure", "over the parse"),
    "_hydrate_postal": ("sig", "postal", "the index, the caption map and each card's peer identity (names)"),
    "_idle_faded": ("sig", "clock", "the faded boolean, from the row's since and now"),
    "_interrupt_settle": ("pure", "over the events and an atom"),
    "_launch_error": ("sig", "backend"),
    "_limit_hold": ("sig", "limit", "folded as its value while the tab can render a queued bubble (a queue, parked ops, or a tmux session's in-flight echo); None otherwise, when the build never reads it"),
    "_merge_live_atoms": ("sig", "live", "the backend's tail by revision; the transcript-side sets are pure over the parse"),
    "_model_color": ("pure", "over the model string and the colormap name"),
    "_model_pending_now": ("sig", "clock", "the row's flag, the kernel's stamp and its 20 s cap as one boolean"),
    "_model_tone": ("pure", "over the model string"),
    "_msg_summaries_scoped": ("sig", "postal", "the cycle's caption map (one fetch per pusher cycle; fresh on a handler thread), read only through the caption values each card embeds (the postal deps)"),
    "_name_color": ("sig", "names"),
    "_name_emoji": ("sig", "names"),
    "_name_of": ("sig", "names"),
    "_node_anchor_uuids": ("sig", "anchors", "the warm-anchor table by this sid's revision; else pure over the node and the parse's segment maps"),
    "_norm_branch": ("pure", "over a branch string"),
    "_notify_session_effective": ("sig", "ncards", "the master bell; the session's own override is in flags"),
    "_open_user_todos": ("sig", "todos", "the sid's rows and the feature switch, serialized"),
    "_orphan_replies": ("sig", "states"),
    "_parked_md": ("pure", "over a parked op"),
    "_parse": ("sig", "transcript", "memoized on the transcript's (mtime, size), the pending cut (cut) and the states file (states)"),
    "_parse_task_notification": ("pure", "over a reminder string"),
    "_patch_rows": ("pure", "over a structured patch"),
    "_path_links": ("sig", "pathlink", "a resolved token latches for the message's life; an unresolved one is retried, and the retry is the pathlink dep"),
    "_path_pins": ("sig", "pathlink", "the pins latched beside the links"),
    "_postal_card_deps": ("sig", "postal"),
    "_postal_index": ("sig", "postal", "memoized on the log's identity"),
    "_queue_recallable": ("sig", "backend"),
    "_queued_romp_flags": ("pure", "over a queued text"),
    "_read_task_store": ("sig", "tasks"),
    "_retry_gate_state": ("sig", "retry"),
    "_retry_gaveups": ("sig", "states"),
    "_retry_recoveries": ("sig", "states"),
    "_rewind_hold_get": ("sig", "hold"),
    "_sdk": ("const", "the SDK backend singleton, fixed once made"),
    "_sdk_sess": ("sig", "reg", "a transcript-less SDK session's row: its reg and names entry"),
    "_sdk_spawned_at": ("sig", "reg", "the reg's spawnedAt and the death marker (gone)"),
    "_seg_anchors": ("pure", "over a segment's atoms"),
    "_seg_jump": ("pure", "over a segment's atoms"),
    "_seg_key": ("pure", "over a segment id"),
    "_segs_seam": ("pure", "over a turn and the store's seams (store)"),
    "_self_host": ("sig", "host"),
    "_session_awaiting": ("sig", "bg", "the row's subagents and task set, the live task rows, the watches (watch), the states overlay (states), the durable stamp view with its delegation peers (stamp: the store, the journal and the postal log, since a peer's answer supersedes a peer wait), the blocked-yield read of the store (store, hold) and the peers' names (names)"),
    "_session_backend": ("sig", "row", "the row's backend field; else the reg's existence (reg)"),
    "_session_chip": ("pure", "over classified inputs: the parse and live tail, the row, the backend brackets, the clock booleans, the live task rows, the watches, the states overlay, the store and the downtime list"),
    "_session_cwd": ("sig", "cwd", "the names entry's cwd, else the transcript's stamp"),
    "_session_flag": ("sig", "flags"),
    "_session_meta": ("pure", "over the transcript's records, memoized by record identity (transcript)"),
    "_session_retry_suppressed": ("sig", "retry"),
    "_session_working": ("sig", "downtime", "over the turns, and the host suspensions recorded since boot"),
    "_sessions": ("sig", "names", "the cycle's discovery rows: the transcript path (transcript), the display name (names), and the 48 h discovery window (clock: a session that ages out leaves the roster and the tab list, so no signature is taken for it)"),
    "_space_paths": ("memo", "the first resolution of a message's spaced spans latches for the process's life"),
    "_split_followup": ("pure", "over a text"),
    "_split_reminders": ("pure", "over a text"),
    "_stamp_agents": ("sig", "taskout", "the sidecar directory and each agent transcript it reads are taskout deps (stat'd before the read, re-stat'd per cycle); the task scan is over the transcript, the liveness gate over the row and the spawn epoch (row, reg, gone)"),
    "_stamp_interrupt_causes": ("pure", "over the events"),
    "_strip_hook_notices": ("pure", "over a text"),
    "_task_outputs_for": ("sig", "taskout", "the launch record from the transcript's scan; each output file's tail is a taskout dep"),
    "_thread_reg": ("sig", "reg"),
    "_tilde": ("const", "the home directory"),
    "_tmux_sessions": ("sig", "row", "the liveness map when the caller passed none"),
    "_tree_of": ("sig", "cwd"),
    "_user_images": ("pure", "over a turn's blocks and text"),
    "_user_todo_session_ended": ("sig", "reg", "the reg's alive bit; else the death marker (gone) against the last states row (states)"),
    "iso": ("pure", "over a timestamp"),
}

# Attribute calls whose base is a module-level object or one of the backend locals build_session binds.
DOTTED = {
    "Sessions.backend_for": ("sig", "reg", "ownership: the SDK backend owns a sid whose reg exists"),
    "Sessions.working_note": ("sig", "note"),
    "jd.episode_rows": ("sig", "episodes"),
    "jd.episode_settles": ("sig", "episodes"),
    "jd.load_archive": ("sig", "archive"),
    "jd.load_goals_shared": ("sig", "store"),
    "em.MSG_TAG_RE.search": ("pure", "over a text"),
    "em.parse_teammate_message": ("pure", "over a text"),
    "sb.echo_text_key": ("pure", "over a text"),
    "cm.context_rgb": ("pure", "over a percentage"),
    "cm.ramp": ("pure", "over a fraction and the colormap's stops"),
    "cm.stops_for": ("pure", "over the colormap name"),
    "_SEND_TOOL_RE.search": ("const", "a module regex"),
    "_PATH_LINK_CACHE.get": ("sig", "pathlink", "which tokens are still unresolved"),
    "_chat_fold.pop": ("out", "the fold entry's eviction"),
    "_ledger_memo.get": ("memo", "keyed on the seams, cleared.jsonl and the anchor revision, held by parse and store identity"),
    "_node_anchor_rev.get": ("sig", "anchors"),
    "_parse_mode.get": ("memo", "the parse's own mode, written under the parse's key"),
    "_pending_ops.get": ("sig", "ops"),
    "be.owns": ("sig", "reg"),
    "be.pending_queued": ("sig", "backend", "the SDK queue by value; the tmux queue is folded from the transcript"),
    "be.live_atoms": ("sig", "live"),
    "_be_fk.fork_children": ("sig", "fork"),
    "os.path.exists": ("sig", "transcript", "whether the transcript exists yet"),
    "os.path.realpath": ("sig", "cwd", "the two tree tops compared through the filesystem"),
    "os.path.expanduser": ("const", "the home directory"),
    "os.path.basename": ("pure", "over a path string"),
    "os.path.dirname": ("pure", "over a path string"),
    "json.dumps": ("pure", "over a value"),
    "re.sub": ("pure", "over a text"),
    "bisect.bisect_right": ("pure", "over a list"),
    "sys.stderr.write": ("out", "a log line"),
    "traceback.format_exc": ("out", "a log line"),
}

# Module globals build_session reads without calling.
GLOBALS = {
    "Sessions": ("const", "the backend-agnostic session API class; its two calls are in DOTTED"),
    "_CHAT_FOLD_STATS": ("out", "counters"),
    "_LEDGER_TREE_ROWS": ("const", "a module constant"),
    "_PATH_LINK_CACHE": ("sig", "pathlink"),
    "_SEND_TOOL_RE": ("const", "a module regex"),
    "_chat_fold": ("memo", "see _chat_fold_get"),
    "_chat_fold_last": ("out", "the perf line's per-thread record"),
    "_chat_fold_lock": ("const", "a lock"),
    "_chat_fold_warned": ("out", "a once-flag"),
    "_chat_dep_scope": ("out", "the running build's dependency record, written for the pusher (see _chat_build_deps)"),
    "_chat_postal_stats": ("out", "counters"),
    "_ledger_memo": ("memo", "see _ledger_memo.get"),
    "_ledger_memo_stats": ("out", "counters"),
    "_live_scope": ("sig", "names", "the names snapshot the thread holds (the cycle's, or the push's own), digested"),
    "_node_anchor_rev": ("sig", "anchors"),
    "_parse_mode": ("memo", "see _parse_mode.get"),
    "_pending_ops": ("sig", "ops"),
    "bisect": ("const", "a module"), "cm": ("const", "a module"), "em": ("const", "a module"),
    "jd": ("const", "a module"), "json": ("const", "a module"), "os": ("const", "a module"),
    "re": ("const", "a module"), "sb": ("const", "a module"), "sys": ("const", "a module"),
    "traceback": ("const", "a module"),
}

# The local names build_session binds a backend to — derived from its source by AST (_backend_locals: every
# name assigned from a call to _sdk(), _codex() or Sessions.backend_for(), or from another such name,
# transitively) and pinned here, so a read through a backend bound to a new name, or a method called
# directly on _sdk()/_codex() (reported as `_sdk().<attr>`), reaches DOTTED instead of slipping past it.
BACKEND_LOCALS = ("_be_fk", "_cbe", "be")
BACKEND_FACTORIES = ("_sdk", "_codex")
KINDS = ("sig", "pure", "memo", "const", "out")


def _module_names():
    """Every name bound at kernel module level: functions, classes, assignments, imports."""
    tree = ast.parse(inspect.getsource(km))
    names = set()
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            names.add(n.name)
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                for x in ast.walk(t):
                    if isinstance(x, ast.Name):
                        names.add(x.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for a in n.names:
                names.add((a.asname or a.name).split(".")[0])
    return names


def _is_backend_factory(call):
    f = call.func
    return ((isinstance(f, ast.Name) and f.id in BACKEND_FACTORIES)
            or (isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name)
                and f.value.id == "Sessions" and f.attr == "backend_for"))


def _backend_locals(fn):
    """Every local name bound to a backend object, transitively: assigned from a backend factory call, or
    from a name already known to hold one."""
    names, changed = set(), True
    while changed:
        changed = False
        for x in ast.walk(fn):
            if not (isinstance(x, ast.Assign) and len(x.targets) == 1 and isinstance(x.targets[0], ast.Name)):
                continue
            v = x.value
            bound = (isinstance(v, ast.Call) and _is_backend_factory(v)) or (isinstance(v, ast.Name) and v.id in names)
            if bound and x.targets[0].id not in names:
                names.add(x.targets[0].id)
                changed = True
    return names


def _census_of(fn_src, module_names):
    """(calls, dotted, globals, backend_locals): the module-level functions called by name, the
    attribute-call chains on module objects or backend locals (a method called on a factory's result
    directly reads `_sdk().<attr>`), the module globals read without a call, and the backend locals the
    function binds (derived, see _backend_locals)."""
    fn = ast.parse(fn_src).body[0]
    backends = _backend_locals(fn)
    local = set()
    for x in ast.walk(fn):
        if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Store):
            local.add(x.id)
        elif isinstance(x, ast.FunctionDef) and x is not fn:
            local.add(x.name)
        elif isinstance(x, ast.arg):
            local.add(x.arg)
        elif isinstance(x, ast.ExceptHandler) and x.name:
            local.add(x.name)
    calls, dotted, reads = set(), set(), set()
    for x in ast.walk(fn):
        if isinstance(x, ast.Call):
            f = x.func
            if isinstance(f, ast.Name) and f.id in module_names and f.id not in local:
                calls.add(f.id)
            elif isinstance(f, ast.Attribute):
                base, chain = f.value, [f.attr]
                while isinstance(base, ast.Attribute):
                    chain.insert(0, base.attr)
                    base = base.value
                if isinstance(base, ast.Name) and ((base.id in module_names and base.id not in local)
                                                   or base.id in backends):
                    dotted.add(base.id + "." + ".".join(chain))
                elif isinstance(base, ast.Call) and _is_backend_factory(base) and isinstance(base.func, ast.Name):
                    dotted.add(base.func.id + "()." + ".".join(chain))   # a method called on the factory's result
        if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and x.id in module_names and x.id not in local:
            reads.add(x.id)
    return calls, dotted, reads - calls, backends


class Census(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = _module_names()
        cls.calls, cls.dotted, cls.reads, cls.backends = _census_of(inspect.getsource(km.build_session), cls.names)

    def test_every_helper_build_session_calls_is_classified_and_nothing_stale_remains(self):
        self.assertEqual(self.calls, set(CENSUS),
                         "a helper build_session calls by name is missing from CENSUS (an unclassified read), "
                         "or CENSUS names one build_session no longer calls: %r"
                         % sorted(self.calls ^ set(CENSUS)))

    def test_every_attribute_call_on_a_module_object_or_backend_is_classified(self):
        self.assertEqual(self.dotted, set(DOTTED), sorted(self.dotted ^ set(DOTTED)))

    def test_the_backend_locals_are_the_pinned_ones(self):
        self.assertEqual(self.backends, set(BACKEND_LOCALS),
                         "build_session binds a backend to a new name (or dropped one): pin it so its reads are censused")
        src = "def f():\n    be = _sdk()\n    x = be\n    y = Sessions.backend_for(sid)\n    z = other()\n    _codex().owns(sid)\n    y.pending_queued(sid)\n"
        calls, dotted, reads, backends = _census_of(src, {"_sdk", "Sessions", "other", "_codex"})
        self.assertEqual(backends, {"be", "x", "y"}, "transitive: a name assigned from a backend name is one too")
        self.assertEqual(dotted, {"_codex().owns", "y.pending_queued", "Sessions.backend_for"})

    def test_every_module_global_read_is_classified(self):
        self.assertEqual(self.reads, set(GLOBALS), sorted(self.reads ^ set(GLOBALS)))

    def test_every_entry_has_a_known_kind_and_a_sig_entry_names_a_label(self):
        for table in (CENSUS, DOTTED, GLOBALS):
            for name, ent in table.items():
                self.assertIn(ent[0], KINDS, name)
                if ent[0] == "sig":
                    self.assertGreaterEqual(len(ent), 2, "%s: a sig entry names its label" % name)
                else:
                    self.assertGreaterEqual(len(ent), 2, "%s: a note says of what" % name)

    def test_the_census_names_resolve_in_the_kernel(self):
        for name in CENSUS:
            self.assertTrue(callable(getattr(km, name, None)), name)
        for name in GLOBALS:
            self.assertTrue(hasattr(km, name), name)

    def test_every_sig_entry_is_a_component_of_the_signature(self):
        labels = set(km._CHAT_SIG_LABELS)
        for table in (CENSUS, DOTTED, GLOBALS):
            for name, ent in table.items():
                if ent[0] == "sig":
                    self.assertIn(ent[1], labels, "%s is keyed under %r, which the signature has no component for" % (name, ent[1]))
        folded = {ent[1] for table in (CENSUS, DOTTED, GLOBALS) for ent in table.values() if ent[0] == "sig"}
        self.assertLessEqual(folded, labels)
        self.assertNotIn("judge_gen", labels, "the global judge-pass counter is no longer a chat input")


if __name__ == "__main__":
    unittest.main()


# ── the differential tests ────────────────────────────────────────────────────────────────────────
# One hermetic world (a tmux-less session discovery finds, with a fixed liveness row); each test moves one
# input and requires the signature to miss under exactly that input's label, so a component that stopped
# covering its input fails here by name. The dependency components are exercised through a hand-made cache
# record, the way _chat_sig_deps evaluates one; the last test drives the REAL build_session through _push.
import json
import re
import time
from pathlib import Path

SID = "77777777-8888-9999-aaaa-ccccccccccc1"      # this module's private synthetic sids: goal stores are minted under SID
PEER = "77777777-8888-9999-aaaa-ccccccccccc2"
NOW = 1781100000
T0 = NOW - 3600


def _iso(t):
    from datetime import datetime, timezone
    return datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")


def _uline(t, text, uuid, parent=None):
    return {"type": "user", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent,
            "promptSource": "typed", "message": {"role": "user", "content": text}}


def _aline(t, text, uuid, parent=None):
    return {"type": "assistant", "timestamp": _iso(t), "uuid": uuid, "parentUuid": parent,
            "message": {"role": "assistant", "content": [{"type": "text", "text": text}], "stop_reason": "end_turn"}}


class _World(unittest.TestCase):
    def setUp(self):
        jd = km.jd
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        self.cdir = td / "launchdir"
        self.cdir.mkdir()
        proj = td / "projects"
        pdir = proj / re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(self.cdir)))
        pdir.mkdir(parents=True)
        self.tpath = pdir / (SID + ".jsonl")
        self.tpath.write_text("\n".join(json.dumps(r) for r in [
            _uline(T0, "start the notes-api spike", "u1"), _aline(T0 + 40, "Spike is up.", "a1", "u1"),
            _uline(T0 + 100, "now the tests", "u2", "a1"), _aline(T0 + 140, "Tests pass.", "a2", "u2")]) + "\n")
        state = td / "state"
        state.mkdir()
        self.saved = (jd.STATE, jd.PROJECTS, km.NAMES, km.WORKING_DIR, km._GLOBAL_CLAUDE_MD, km._tmux_sessions, km._sdk,
                      os.environ.get("CLAUDE_CONFIG_DIR"), os.environ.get("ROMP_HOST_NAME"), km._feed_needs_input[0],
                      len(km._downtime), km._claude_account_label)
        jd._rebind_state(state)                       # every STATE-derived dir (goals, states, episodes, gone, sdk, ...)
        jd.PROJECTS = proj
        jd.NAMES.mkdir()
        (jd.NAMES / SID).write_text("web\t%s\t#1EA1EB\twhite\n" % self.cdir)
        km.NAMES = jd.NAMES
        km.WORKING_DIR = state / "working"
        km._GLOBAL_CLAUDE_MD = td / "no-global-claude.md"
        os.environ["CLAUDE_CONFIG_DIR"] = str(td / "claude")   # the task-store root (_tasks_base)
        self.row = {"state": "idle", "since": NOW - 100, "model": "", "effort": "", "context": None,
                    "compactPct": None, "color": None, "backend": "tmux"}
        self.tmux = {SID: self.row}
        km._tmux_sessions = lambda: self.tmux
        km._sdk = lambda: None
        km._built_chat.clear()
        km._live_scope.chat_shared = None
        self.sess = {"sid": SID, "name": "web", "path": str(self.tpath), "anchor": SID}

    def tearDown(self):
        jd = km.jd
        (state, proj, names, wdir, gmd, tmux, sdk, cfg, host, needs, ndown, acct) = self.saved
        jd._rebind_state(state)
        jd.PROJECTS = proj
        km.NAMES, km.WORKING_DIR, km._GLOBAL_CLAUDE_MD, km._tmux_sessions, km._sdk = names, wdir, gmd, tmux, sdk
        km._claude_account_label = acct
        for k, v in (("CLAUDE_CONFIG_DIR", cfg), ("ROMP_HOST_NAME", host)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        km._feed_needs_input[0] = needs
        del km._downtime[ndown:]
        for d in (km._tmux_echo, km._tmux_echo_rev, km._node_anchor_rev, km._pending_ops, km._auto_retry_state,
                  km._interrupt_clicked, km._compact_clicked, km._model_switch_pending):
            d.pop(SID, None)
        with km._watch_lock:
            km._watches[:] = [w for w in km._watches if w.get("sid") != SID]
        km._rewind_hold_clear(SID)
        km._built_chat.clear()
        km._live_scope.names = None
        km._live_scope.snapshot = None
        km._live_scope.chat_shared = None
        for k in [k for k in km._PATH_LINK_CACHE if k[0] == SID]:
            km._PATH_LINK_CACHE.pop(k, None)
        self.td.cleanup()

    def sig(self, now=NOW, deps=None):
        return km._chat_build_sig(self.sess, self.tmux, now, deps=deps)

    def moved(self, before, after):
        return km._chat_sig_miss(before, after)

    def store(self, nodes=None, status=None):
        km.jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        (km.jd.GOALDIR / (SID + ".json")).write_text(json.dumps({"rompUuid": SID, "nodes": nodes or {}, "status": status or {}}))


class Differential(_World):
    def test_a_quiet_world_holds_and_has_one_value_per_label(self):
        a = self.sig()
        self.assertEqual(len(a), len(km._CHAT_SIG_LABELS))
        self.assertEqual(self.sig(), a)
        self.assertEqual(self.moved(a, self.sig()), ())

    def test_a_transcript_append_misses_under_transcript_alone(self):
        a = self.sig()
        with open(self.tpath, "a") as f:
            f.write(json.dumps(_uline(T0 + 200, "and the docs", "u3", "a2")) + "\n")
        self.assertEqual(self.moved(a, self.sig()), ("transcript",))

    def test_a_states_row_misses_under_states(self):
        a = self.sig()
        km.jd.STATESDIR.mkdir(parents=True, exist_ok=True)
        with open(km.jd.STATESDIR / (SID + ".jsonl"), "a") as f:
            f.write(json.dumps({"t": T0 + 150, "state": "idle"}) + "\n")
        self.assertEqual(self.moved(a, self.sig()), ("states",))

    def test_the_goal_store_its_journal_and_its_archive_each_miss_under_store(self):
        a = self.sig()
        self.store()
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("store",), "a publish busts the tab at once (the live identity)")
        jd = km.jd
        jd._overrides_dir().mkdir(parents=True, exist_ok=True)
        with open(jd._overrides_dir() / (SID + ".jsonl"), "a") as f:
            f.write(json.dumps({"t": T0, "op": "noop"}) + "\n")
        c = self.sig()
        self.assertEqual(self.moved(b, c), ("store",), "the override journal is the store triple's second member")
        jd.GOALARCHDIR.mkdir(parents=True, exist_ok=True)
        (jd.GOALARCHDIR / (SID + ".json")).write_text(json.dumps({"rompUuid": SID, "nodes": {}, "status": {}}))
        self.assertEqual(self.moved(c, self.sig()), ("store",), "…and the goals-archive the third")

    def test_a_rewind_hold_misses_under_hold_and_its_clear_restores_the_signature(self):
        a = self.sig()
        km._rewind_hold_set(SID, T0 + 10, "u1")
        self.assertEqual(self.moved(a, self.sig()), ("hold",))
        km._rewind_hold_clear(SID)
        self.assertEqual(self.sig(), a)

    def test_the_archive_headline_and_the_episode_log_each_miss_under_their_own_label(self):
        jd = km.jd
        a = self.sig()
        jd.ARCHDIR.mkdir(parents=True, exist_ok=True)
        (jd.ARCHDIR / (SID + ".json")).write_text(json.dumps({"headline": "the notes-api spike"}))
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("archive",))
        jd.EPIDIR.mkdir(parents=True, exist_ok=True)
        with open(jd.EPIDIR / (SID + ".jsonl"), "a") as f:
            f.write(json.dumps({"head": "u1", "fsid": SID, "t": T0}) + "\n")
        self.assertEqual(self.moved(b, self.sig()), ("episodes",))

    def test_the_sdk_registry_and_the_death_marker_each_miss_under_their_own_label(self):
        jd = km.jd
        a = self.sig()
        jd.SDKDIR.mkdir(parents=True, exist_ok=True)
        (jd.SDKDIR / (SID + ".json")).write_text(json.dumps({"sid": SID, "alive": True, "cwd": str(self.cdir)}))
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("reg",))
        jd.GONEDIR.mkdir(parents=True, exist_ok=True)
        (jd.GONEDIR / (SID + ".json")).write_text(json.dumps({"t": T0 + 300, "by": "probe"}))
        self.assertEqual(self.moved(b, self.sig()), ("gone",))

    def test_the_task_store_the_working_note_and_the_needs_bit(self):
        a = self.sig()
        tdir = Path(os.environ["CLAUDE_CONFIG_DIR"]) / "tasks" / SID
        tdir.mkdir(parents=True)
        (tdir / "1.json").write_text(json.dumps({"id": "1", "subject": "write the tests", "status": "pending"}))
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("tasks",))
        km._set_working_note(SID, "editing the notes-api tests")
        c = self.sig()
        self.assertEqual(self.moved(b, c), ("note",))
        km._feed_needs_input[0] = frozenset({SID})
        self.assertEqual(self.moved(c, self.sig()), ("needs",))

    def test_the_live_tail_misses_under_live_for_an_echo_and_for_its_dropped_mark(self):
        a = self.sig()
        km._tmux_echo_add(SID, "a send still in flight")
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("live",), "an echo added to the tail, no transcript write")
        t = km._tmux_echo_atoms(SID)[0]["t"]
        km._tmux_echo_settle(SID, human_floor=t + 5)          # the settle marks it dropped in place
        self.assertTrue(km._tmux_echo_atoms(SID)[0].get("dropped"))
        self.assertEqual(self.moved(b, self.sig()), ("live",), "a dropped mark on a background tab rebuilds it next cycle")

    def test_the_liveness_row_misses_under_row_and_its_snapshot_stamp_does_not(self):
        a = self.sig()
        self.row["snapT"] = 123456.0
        self.assertEqual(self.moved(a, self.sig()), (), "snapT moves every cycle and is not an input")
        self.row["model"] = "opus"
        self.assertEqual(self.moved(a, self.sig()), ("row",))

    def test_each_clock_boolean_misses_under_clock_exactly_at_its_crossing(self):
        a = self.sig()
        km._interrupt_clicked[SID] = NOW
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("clock",), "a stop dispatched: interrupting")
        self.assertEqual(self.sig(now=NOW + 121), a, "past the 120 s cap the stamp is popped and the signature is back")
        km._model_switch_pending[SID] = {"target": "opus", "until": time.time() + 20}
        self.assertEqual(self.moved(a, self.sig()), ("clock",), "a model switch pending")
        km._model_switch_pending.pop(SID, None)
        self.assertEqual(self.moved(a, self.sig(now=NOW + 4000)), ("clock",), "an hour idle: the faded look")
        km._compact_clicked[SID] = NOW
        self.assertEqual(self.moved(a, self.sig()), ("clock",), "a compact click: the optimistic compacting cue")
        km._compact_clicked.pop(SID, None)
        self.assertEqual(self.sig(), a)

    def test_parked_ops_miss_under_ops_and_the_limit_hold_is_read_only_while_something_is_queued(self):
        a = self.sig()
        self.assertIsNone(a[km._CHAT_SIG_LABELS.index("limit")], "nothing queued: the build never reads the hold")
        km._pending_ops[SID] = [("send", "hello there", False)]
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("ops",))
        (km.jd.STATE / "usage.json").write_text(json.dumps({"five_hour": {"pct": 100, "resets_at": time.time() + 3600}}))
        c = self.sig()
        self.assertEqual(self.moved(b, c), ("limit",), "the account hit its window: the queued bubble's hold")
        self.assertEqual(c[km._CHAT_SIG_LABELS.index("limit")]["reason"], "limit")

    def test_the_limit_hold_is_read_for_a_tmux_sessions_in_flight_echo_too(self):
        """Review nit (a): a busy tmux session folds a not-yet-landed echo into its queue, so the build
        reads the hold for it; the key folds the hold under the same condition."""
        a = self.sig()
        self.assertIsNone(a[km._CHAT_SIG_LABELS.index("limit")])
        (km.jd.STATE / "usage.json").write_text(json.dumps({"five_hour": {"pct": 100, "resets_at": time.time() + 3600}}))
        self.assertEqual(self.sig(), a, "no bubble can render: the hold is not an input yet")
        km._tmux_echo_add(SID, "a send still in flight")
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("limit", "live"), "the echo is a bubble the hold rides on")
        self.assertEqual(b[km._CHAT_SIG_LABELS.index("limit")]["reason"], "limit")

    def test_the_retry_state_misses_under_retry(self):
        a = self.sig()
        km._auto_retry_state[SID] = {"n": 2, "next": 123.0}
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("retry",))
        km._suppress_session_retry(SID)
        self.assertEqual(self.moved(b, self.sig()), ("retry",))
        km._clear_session_retry_suppress(SID)

    def test_the_live_task_rows_miss_under_bg_and_a_deadline_crossing_is_a_change(self):
        a = self.sig()
        self.row["bgTasks"] = [{"toolUseId": "t1", "desc": "the nightly batch", "since": NOW - 50, "type": "local_bash"}]
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("bg", "row"))
        jd = km.jd
        jd.SDKDIR.mkdir(parents=True, exist_ok=True)
        (jd.SDKDIR / (SID + ".json")).write_text(json.dumps(
            {"sid": SID, "alive": True, "bgLedger": [{"toolUseId": "t1", "deadlineEpoch": time.time() - 100}]}))
        c = self.sig()
        self.assertEqual(self.moved(b, c), ("bg", "reg"), "the ledger's deadline passed: the row is gone from the live set")
        self.assertEqual(c[km._CHAT_SIG_LABELS.index("bg")], ())

    def test_a_kernel_watch_misses_under_watch(self):
        a = self.sig()
        with km._watch_lock:
            km._watches.append({"id": "w1", "cmd": "true", "every": 60, "timeoutS": 600, "sid": SID,
                                "note": "the nightly job", "at": NOW})
        self.assertEqual(self.moved(a, self.sig()), ("watch",))

    def test_the_awaiting_stamp_view_misses_under_stamp_when_a_peers_answer_lands_in_the_postal_log(self):
        a = self.sig()
        self.store(nodes={"g1": {"id": "g1", "text": "ask the api session", "t": T0, "parentId": None,
                                 "awaitingWhy": "waiting on a peer", "awaitingAt": T0 + 5,
                                 "awaitingKind": "peer", "awaitingPeers": [PEER]}},
                   status={"g1": "working"})
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("stamp", "store"), "a stamp in a published store")
        jd = km.jd
        jd.MESSAGES.parent.mkdir(parents=True, exist_ok=True)
        with open(jd.MESSAGES, "a") as f:
            f.write(json.dumps({"ev": "sent", "id": "m1", "from_id": SID, "to_id": PEER, "t": T0, "kind": "question", "body": "?"}) + "\n")
            f.write(json.dumps({"ev": "sent", "id": "m2", "from_id": PEER, "to_id": SID, "t": T0 + 100, "kind": "coordinate", "body": "done"}) + "\n")
        c = self.sig()
        self.assertEqual(self.moved(b, c), ("stamp",),
                         "the peer's answer supersedes the wait: the chip changes with no card and no store write")

    def test_the_anchor_revision_the_suspension_list_and_the_names_digest(self):
        a = self.sig()
        km._node_anchor_rev[SID] = 1
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("anchors",))
        km._downtime.append((NOW, NOW + 10))
        c = self.sig()
        self.assertEqual(self.moved(b, c), ("downtime",))
        snap = km._names_snapshot()
        self.assertEqual(c[km._CHAT_SIG_LABELS.index("names")], km._names_digest(snap),
                         "with no snapshot on the thread the digest is of the registry read here")
        km._live_scope.names = snap                            # a handler-thread push's own snapshot
        self.assertEqual(self.sig(), c, "the same registry: the same component, whichever thread holds it")
        km._live_scope.snapshot = self.tmux                    # a pusher cycle's scope
        self.assertEqual(self.sig(), c, "…and a cycle scope changes nothing about it")
        renamed = dict(snap)
        renamed[SID] = ["web-2"] + list(snap[SID][1:])
        km._live_scope.names = renamed
        d = self.sig()
        self.assertEqual(self.moved(c, d), ("names",), "a rename moves it")
        km._live_scope.names = snap
        self.assertEqual(self.sig(), c, "and back")

    def test_the_shared_files_each_miss_under_their_own_label(self):
        jd = km.jd
        a = self.sig()
        km._set_session_flag(SID, "hideFromFeed", True)
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("flags",))
        km._set_notify_all(True)
        c = self.sig()
        self.assertEqual(self.moved(b, c), ("ncards",))
        other = next(n for n in km.cm.COLORMAPS if n != km.cm.DEFAULT)
        (jd.STATE / "colormap").write_text(other)
        d = self.sig()
        self.assertEqual(self.moved(c, d), ("colormap",))
        km._claude_account_label = lambda: "someone"
        e = self.sig()
        self.assertEqual(self.moved(d, e), ("acct",))
        with open(jd.STATE / "cleared.jsonl", "a") as f:
            f.write(json.dumps({"id": "g9", "t": T0}) + "\n")
        g = self.sig()
        self.assertEqual(self.moved(e, g), ("cleared",))
        os.environ["ROMP_HOST_NAME"] = "TESTHOST2"
        self.assertEqual(self.moved(g, self.sig()), ("host",))

    def test_the_cwd_rows_and_the_claudemd_chain(self):
        a = self.sig()
        (self.cdir / "CLAUDE.md").write_text("# project rules\n")
        b = self.sig()
        self.assertEqual(self.moved(a, b), ("claudemd",), "an instruction file appeared on the chain")
        other = Path(self.td.name) / "otherdir"
        other.mkdir()
        (km.jd.NAMES / SID).write_text("web\t%s\t#1EA1EB\twhite\n" % other)
        self.assertEqual(self.moved(b, self.sig()), ("claudemd", "cwd", "names"),
                         "a move: the cwd rows and the chain both follow, and the names entry that records the cwd moved too")

    def test_a_recorded_task_output_that_grows_misses_under_taskout(self):
        out = Path(self.td.name) / "task-out.log"
        out.write_text("hello\n")
        deps = {"task_outs": [(str(out), km._chat_stat_key(str(out)))], "pl_pending": [], "postal_any": False,
                "postal_cards": [], "at_build": None}
        a = self.sig(deps=deps)
        self.assertEqual(a[km._CHAT_SIG_LABELS.index("taskout")], ((str(out), km._chat_stat_key(str(out))),))
        self.assertEqual(self.sig(deps=deps), a)
        with open(out, "a") as f:
            f.write("more output\n")
        self.assertEqual(self.moved(a, self.sig(deps=deps)), ("taskout",))
        out.unlink()
        self.assertEqual(self.moved(a, self.sig(deps=deps)), ("taskout",), "…and one that vanished")

    def test_a_pending_path_token_whose_file_appears_misses_under_pathlink(self):
        md = "the numbers are in report.md now"
        self.assertEqual(km._path_links(md, SID, "u9", {}), {}, "tokens exist, none resolved: the retry is armed")
        deps = {"task_outs": [], "pl_pending": [("u9", md)], "postal_any": False, "postal_cards": [], "at_build": None}
        a = self.sig(deps=deps)
        self.assertEqual(a[km._CHAT_SIG_LABELS.index("pathlink")], (("u9", {}, None),))
        self.assertEqual(self.sig(deps=deps), a)
        (self.cdir / "report.md").write_text("42\n")
        b = self.sig(deps=deps)
        self.assertEqual(self.moved(a, b), ("pathlink",), "the mention preceded its file; the file landing is the change")
        self.assertIn("report.md", b[km._CHAT_SIG_LABELS.index("pathlink")][0][1])

    def test_a_postal_dependency_misses_under_postal_when_the_log_moves(self):
        deps = {"task_outs": [], "pl_pending": [], "postal_any": True, "postal_cards": [], "at_build": None}
        a = self.sig(deps=deps)
        self.assertEqual(a[km._CHAT_SIG_LABELS.index("postal")], (None, ()), "no log yet")
        jd = km.jd
        jd.MESSAGES.parent.mkdir(parents=True, exist_ok=True)
        with open(jd.MESSAGES, "a") as f:
            f.write(json.dumps({"ev": "sent", "id": "m1", "from_id": PEER, "to_id": SID, "t": T0, "kind": "coordinate", "body": "hi"}) + "\n")
        self.assertEqual(self.moved(a, self.sig(deps=deps)), ("postal",))
        nodeps = self.sig()
        self.assertIsNone(nodeps[km._CHAT_SIG_LABELS.index("postal")], "a tab with no postal traffic ignores the log")


class RealBuildIdleBoard(_World):
    """The real build_session through _push over a quiet world: the first push builds the tab, every later
    push serves it — judge passes included — and the post-build signature held (nothing moved)."""

    STUBS = ("_tab_list_tmux", "_chat_tab_sessions", "_cached_feed", "_cached_timeline", "build_timeline",
             "_fleet_view_sig", "_comments_frame", "_retry_parked_creates")

    def setUp(self):
        super().setUp()
        self.saved_stubs = {nm: getattr(km, nm) for nm in self.STUBS}
        self.saved_state2 = (dict(km._prev_chat_events), dict(km._prev_chat_ledger), list(km._last_tab_order), km._judge_gen[0])
        km._tab_list_tmux = lambda tmux: dict(tmux)
        km._chat_tab_sessions = lambda now, tmux: [dict(self.sess)]
        km._cached_feed = lambda now, tmux, sig, connect=False: {"working": [], "awaiting": [], "now": now}
        km._cached_timeline = lambda now, tmux, sig, connect=False: {"turns": {}, "judging": [], "messages": [], "now": now}
        km.build_timeline = lambda now, tmux, **kw: {"lanes": [], "now": now}
        km._fleet_view_sig = lambda now, tmux: {"probe": 1}
        km._comments_frame = lambda sid, tmux: None
        km._retry_parked_creates = lambda: None
        km._prev_chat_events.clear(); km._prev_chat_ledger.clear()
        self.client = {"app": "chat", "alive": True, "sent": {}, "active": PEER, "send": lambda s: None}

    def tearDown(self):
        for nm, v in self.saved_stubs.items():
            setattr(km, nm, v)
        pe, pl, lo, jg = self.saved_state2
        km._prev_chat_events.clear(); km._prev_chat_events.update(pe)
        km._prev_chat_ledger.clear(); km._prev_chat_ledger.update(pl)
        km._last_tab_order[:] = lo
        km._judge_gen[0] = jg
        super().tearDown()

    @staticmethod
    def _chat():
        c = km._PERF_STATS.snapshot()["builds"]["chat"]
        return dict(c, bg_miss=dict(c["bg_miss"]))

    def test_one_build_then_cache_hits_across_judge_passes_with_nothing_moved(self):
        c0 = self._chat()
        km._push([self.client])
        self.assertIn(SID, km._built_chat, "the real build cached")
        ent = km._built_chat[SID]
        self.assertEqual(len(ent), 4, "(sig, payload, serialized, deps)")
        self.assertEqual(ent[1]["id"], SID)
        self.assertEqual(ent[3]["task_outs"], [])
        self.assertEqual(ent[3]["pl_pending"], [])
        self.assertFalse(ent[3]["postal_any"])
        for _ in range(5):
            km._judge_gen[0] += 1                          # a producer pass that wrote nothing
            km._push([self.client])
        c1 = self._chat()
        d = {k: c1[k] - c0[k] for k in ("cached", "built", "bg_built", "moved")}
        self.assertEqual(d, {"cached": 5, "built": 1, "bg_built": 1, "moved": 0},
                         "one build, five served pushes, none left uncached by a moved signature")
        self.assertEqual({k: v - c0["bg_miss"].get(k, 0) for k, v in c1["bg_miss"].items() if v - c0["bg_miss"].get(k, 0)},
                         {"cold": 1})
        with open(self.tpath, "a") as f:
            f.write(json.dumps(_uline(T0 + 200, "and the docs", "u3", "a2")) + "\n")
        km._push([self.client])
        c2 = self._chat()
        self.assertEqual(c2["bg_built"] - c1["bg_built"], 1)
        self.assertEqual({k: v - c1["bg_miss"].get(k, 0) for k, v in c2["bg_miss"].items() if v - c1["bg_miss"].get(k, 0)},
                         {"transcript": 1})
        km._push([self.client])
        self.assertEqual(self._chat()["cached"] - c2["cached"], 1, "served again once nothing moves")

    def test_a_tab_built_during_a_liveness_collapse_caches_the_chip_of_the_handed_row(self):
        """The review's should-fix 2: _push hands the chat loop the GUARDED map (the previous rows carried
        through a tmux collapse) and the key reads that row, but the chip's sources read the raw snapshot;
        a tab built while the raw read had collapsed cached a 'ready' chip under a key the recovered read
        never busts. The chip now derives from the handed row, so the served payload equals a fresh build's."""
        self.row["bgTasks"] = [{"toolUseId": "t1", "desc": "the nightly batch", "since": NOW - 50, "type": "local_bash"}]
        saved = km._tmux_sessions
        km._tmux_sessions = lambda: {}                       # the raw read collapsed for this push…
        try:
            km._push([self.client], tmux=self.tmux)          # …while the handed map carries the row
        finally:
            km._tmux_sessions = saved
        served = km._built_chat[SID][1]["status"]
        fresh = km.build_session(SID, int(time.time()), self.tmux)["status"]
        self.assertEqual(served["state"], "awaitingBg", "the handed row's pending task decides the chip")
        self.assertEqual((served["state"], served["awaitingWhy"], served["awaitingTaskIds"]),
                         (fresh["state"], fresh["awaitingWhy"], fresh["awaitingTaskIds"]),
                         "what the collapse cycle cached is what a build after the read recovers produces")
        c0 = self._chat()
        km._push([self.client], tmux=self.tmux)
        self.assertEqual(self._chat()["cached"] - c0["cached"], 1, "the same key: served, and correct")

    def test_the_dependency_tail_is_evaluated_only_where_it_is_compared(self):
        """Review should-fix 3: the active tab never checks the cache and every post-build signature is
        compared on the static part, so neither evaluates the dependency tail (deps=False)."""
        calls = []
        real = km._chat_sig_deps
        km._chat_sig_deps = lambda sid, deps: calls.append(deps) or real(sid, deps)
        try:
            a = km._chat_build_sig(self.sess, self.tmux, NOW, deps=False)
            self.assertEqual(a[-3:], ((), (), None))
            self.assertEqual(calls, [], "deps=False evaluates nothing")
            self.assertEqual(km._chat_build_sig(self.sess, self.tmux, NOW)[:-3], a[:-3], "the static part is the same")
            del calls[:]
            watched = {"app": "chat", "alive": True, "sent": {}, "active": SID, "send": lambda s: None}
            km._push([watched], tmux=self.tmux)            # our tab is the watched one: built, never checked
            self.assertEqual(calls, [], "an active tab's pre-build and post-build signatures skip the tail")
            km._built_chat.clear()
            km._push([self.client], tmux=self.tmux)        # a cold background tab: one pre-build check, no tail after the build
            self.assertEqual(len(calls), 1)
            del calls[:]
            km._push([self.client], tmux=self.tmux)        # served: the one check
            self.assertEqual(len(calls), 1)
        finally:
            km._chat_sig_deps = real

    def test_a_build_whose_signature_moved_is_not_cached_and_counts_under_moved(self):
        """Review should-fix 4: the post-build gate. A build during which a keyed input moves (here the
        warm-anchor revision, bumped by a stub around the real build) is not cached, builds.chat.moved
        counts it, the tab's earlier entry stays as it was, and the next push rebuilds under that label
        and caches."""
        km._push([self.client], tmux=self.tmux)                   # the entry a quiet world caches
        e1 = km._built_chat[SID]
        with open(self.tpath, "a") as f:                          # something else moved, so the next push builds
            f.write(json.dumps(_uline(T0 + 200, "and the docs", "u3", "a2")) + "\n")
        real = km.build_session

        def moving(sid, now, tmux):
            m = real(sid, now, tmux)
            km._node_anchor_rev[SID] = km._node_anchor_rev.get(SID, 0) + 1   # a keyed input moves mid-build
            return m
        km.build_session = moving
        c0 = self._chat()
        try:
            km._push([self.client], tmux=self.tmux)
        finally:
            km.build_session = real
        c1 = self._chat()
        self.assertEqual(c1["moved"] - c0["moved"], 1)
        self.assertEqual(c1["bg_built"] - c0["bg_built"], 1)
        self.assertIs(km._built_chat[SID], e1, "the moved build was not stored; the earlier entry stands")
        km._push([self.client], tmux=self.tmux)
        c2 = self._chat()
        self.assertEqual(c2["moved"] - c1["moved"], 0)
        self.assertEqual({k: v - c1["bg_miss"].get(k, 0) for k, v in c2["bg_miss"].items() if v - c1["bg_miss"].get(k, 0)},
                         {"anchors": 1, "transcript": 1}, "the next push rebuilds under the labels that moved since the standing entry")
        self.assertIsNot(km._built_chat[SID], e1, "…and caches")
        km._push([self.client], tmux=self.tmux)
        self.assertEqual(self._chat()["cached"] - c2["cached"], 1)

    def _pusher_push(self, *clients):
        """A push as _pusher_cycle runs it: the cycle's scopes open on this thread."""
        km._live_scope.snapshot = self.tmux
        km._live_scope.names = km._names_snapshot()
        km._live_scope.msgsum = [km._MSGSUM_UNSET]
        km._live_scope.paths, km._live_scope.sessions = {}, {}
        try:
            km._push(list(clients or (self.client,)), tmux=self.tmux)
        finally:
            for k in ("snapshot", "names", "msgsum", "paths", "sessions"):
                setattr(km._live_scope, k, None)

    def _connect_push(self, client=None):
        """A page load as _push_one runs it: a handler thread with no cycle scope, connect=True."""
        self.assertIsNone(getattr(km._live_scope, "snapshot", None))
        km._push([client or self.client], connect=True, tmux=self.tmux)

    def test_a_connect_push_and_the_pusher_share_the_cache(self):
        c0 = self._chat()
        self._pusher_push()
        self._connect_push({"app": "chat", "alive": True, "sent": {}, "active": PEER, "send": lambda s: None})
        self._pusher_push()
        d = {k: self._chat()[k] - c0[k] for k in ("cached", "built", "bg_built")}
        self.assertEqual(d, {"cached": 2, "built": 1, "bg_built": 1},
                         "one build for three pushes: the handler thread's signature equals the pusher's (the review's should-fix 1)")
        self.assertIsNone(getattr(km._live_scope, "names", None), "the connect push closed the scopes it opened")

    def test_a_rename_between_two_connect_pushes_misses_once_under_names(self):
        self._connect_push()
        c1 = self._chat()
        self._connect_push()
        c2 = self._chat()
        self.assertEqual(c2["cached"] - c1["cached"], 1, "the same registry: served")
        (km.jd.NAMES / SID).write_text("web-renamed\t%s\t#1EA1EB\twhite\n" % self.cdir)
        self._connect_push()
        c3 = self._chat()
        self.assertEqual(c3["bg_built"] - c2["bg_built"], 1)
        self.assertEqual({k: v - c2["bg_miss"].get(k, 0) for k, v in c3["bg_miss"].items() if v - c2["bg_miss"].get(k, 0)},
                         {"names": 1}, "the rename busts the tab once, under names")
        self._connect_push()
        self.assertEqual(self._chat()["cached"] - c3["cached"], 1, "…and it is served again")


class KeyCost(_World):
    """The key's cost amendments: the pending-token pre-check vouches per directory, the row and the usage
    reading the key already holds are handed down, and a push outside a pusher cycle opens its own scopes."""

    def _record(self, uuids_md):
        for u, md in uuids_md:
            km._path_links(md, SID, u, {})
        deps = {"task_outs": [], "pl_pending": list(uuids_md), "postal_any": False, "postal_cards": [], "at_build": None,
                "pl_at": tuple((u, {}, None) for u, _ in uuids_md), "pl_check": None}
        return deps

    def test_the_precheck_vouches_and_a_quiet_cycle_re_resolves_nothing(self):
        sub = self.cdir / "notes"
        sub.mkdir()
        deps = self._record([("u1", "see report.md"), ("u2", "and notes/plan.md too")])
        calls = []
        real = km._path_links
        km._path_links = lambda md, sid, u, memo: calls.append(u) or real(md, sid, u, memo)
        try:
            a = self.sig(deps=deps)
            self.assertEqual(sorted(calls), ["u1", "u2"], "the first check after a build re-resolves once (pl_check starts None)")
            self.assertIsNotNone(deps["pl_check"], "…and vouches: every answer held")
            del calls[:]
            self.assertEqual(self.sig(deps=deps), a)
            self.assertEqual(calls, [], "nothing under a candidate directory moved: no token was re-probed")
            (sub / "unrelated.txt").write_text("x")            # notes/ moved: only the message naming notes/ is re-resolved
            self.assertEqual(self.sig(deps=deps), a)
            self.assertEqual(calls, ["u2"])
            del calls[:]
            (self.cdir / "report.md").write_text("42\n")        # the cwd moved: u1's file appeared
            b = self.sig(deps=deps)
            self.assertEqual(calls, ["u1"], "u2's directory did not move again")
            self.assertEqual(self.moved(a, b), ("pathlink",))
        finally:
            km._path_links = real

    def test_bg_live_norm_reads_the_row_it_is_handed(self):
        row = {"state": "idle", "bgTasks": [{"toolUseId": "t1", "desc": "batch", "since": NOW - 5, "type": "local_bash"}]}
        self.assertEqual([r["tid"] for r in km._bg_live_norm(SID, str(self.tpath), live=row)], ["t1"])
        self.assertEqual(km._bg_live_norm(SID, str(self.tpath), live=None), [], "None is a dormant session")
        self.assertEqual(km._bg_live_norm(SID, str(self.tpath)), [], "no row passed: the liveness map's (no task set here)")

    def test_limit_hold_reads_the_usage_it_is_handed(self):
        capped = {"limited": {"fiveHour": True}, "fiveHour": {"pct": 100, "resetsAt": NOW + 3600}}
        self.assertEqual(km._limit_hold(SID, usage=capped)["resetsAt"], NOW + 3600)
        self.assertIsNone(km._limit_hold(SID, usage={}), "no windows, no pause, no error: no hold")
        self.assertIsNone(km._limit_hold(SID, usage=None), "a failed reading: never invent a hold")

    def test_a_push_outside_a_cycle_opens_its_own_scopes_and_closes_them(self):
        self.assertIsNone(getattr(km._live_scope, "snapshot", None))
        km._live_scope.names = None
        km._live_scope.msgsum = None
        km._chat_push_scopes_open()
        self.assertIsNotNone(km._live_scope.chat_shared)
        self.assertIsNotNone(km._live_scope.names, "a names snapshot for the loop")
        self.assertEqual(km._live_scope.msgsum, [km._MSGSUM_UNSET])
        self.assertEqual(km._chat_sig_shared()["names"], km._names_digest(km._names_snapshot()),
                         "no cycle: the digest is of the snapshot this push opened, the same content the pusher's has")
        km._chat_push_scopes_close()
        self.assertIsNone(km._live_scope.chat_shared)
        self.assertIsNone(km._live_scope.names)
        self.assertIsNone(km._live_scope.msgsum)
        # a cycle's own scopes are the cycle's: opened by _pusher_cycle, left alone here
        km._live_scope.names = {"x": ["y"]}
        km._live_scope.msgsum = [km._MSGSUM_UNSET]
        km._chat_push_scopes_open()
        self.assertEqual(km._live_scope.chat_push_owned, ["chat_shared"])
        km._chat_push_scopes_close()
        self.assertEqual(km._live_scope.names, {"x": ["y"]})
        self.assertEqual(km._live_scope.msgsum, [km._MSGSUM_UNSET])
        km._live_scope.names = None
        km._live_scope.msgsum = None

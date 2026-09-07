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
says how it is keyed.

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
    "_awaiting_task_descs": ("sig", "bg", "the live task rows; the split reads the store and the transcript"),
    "_awaiting_task_ids": ("sig", "bg", "as _awaiting_task_descs"),
    "_bg_tasks": ("sig", "row", "the row's live task set gates the transcript's scan; each output tail is a taskout dep; the spawn epoch reads reg and gone"),
    "_chat_cleared_key": ("sig", "cleared"),
    "_chat_fold_count": ("out", "a fold counter"),
    "_chat_fold_demote": ("out", "a fold counter"),
    "_chat_fold_get": ("memo", "the sealed prefix: every gate it checks is an input classified here, and its output is the events an unfolded build produces"),
    "_chat_fold_put": ("out", "the fold entry's write"),
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
    "_limit_hold": ("sig", "limit", "folded as its value while the tab has a queue; None when nothing is queued and the build never reads it"),
    "_merge_live_atoms": ("sig", "live", "the backend's tail by revision; the transcript-side sets are pure over the parse"),
    "_model_color": ("pure", "over the model string and the colormap name"),
    "_model_pending_now": ("sig", "clock", "the row's flag, the kernel's stamp and its 20 s cap as one boolean"),
    "_model_tone": ("pure", "over the model string"),
    "_msg_summaries": ("sig", "postal", "read only through the caption values each card embeds (the postal deps)"),
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
    "_session_awaiting": ("sig", "bg", "the row's subagents and task set, the live task rows, the watches (watch), the states overlay (states), the store's stamps and delegation (store, hold) and the peers' names (names)"),
    "_session_backend": ("sig", "row", "the row's backend field; else the reg's existence (reg)"),
    "_session_chip": ("pure", "over classified inputs: the parse and live tail, the row, the backend brackets, the clock booleans, the live task rows, the watches, the states overlay, the store and the downtime list"),
    "_session_cwd": ("sig", "cwd", "the names entry's cwd, else the transcript's stamp"),
    "_session_flag": ("sig", "flags"),
    "_session_meta": ("pure", "over the transcript's records, memoized by record identity (transcript)"),
    "_session_retry_suppressed": ("sig", "retry"),
    "_session_working": ("sig", "downtime", "over the turns, and the host suspensions recorded since boot"),
    "_sessions": ("sig", "names", "the cycle's discovery rows: the transcript path (transcript) and the display name (names)"),
    "_space_paths": ("memo", "the first resolution of a message's spaced spans latches for the process's life"),
    "_split_followup": ("pure", "over a text"),
    "_split_reminders": ("pure", "over a text"),
    "_stamp_interrupt_causes": ("pure", "over the events"),
    "_strip_hook_notices": ("pure", "over a text"),
    "_task_outputs_for": ("sig", "taskout", "the launch record from the transcript's scan; each output file's tail is a taskout dep"),
    "_thread_reg": ("sig", "reg"),
    "_tilde": ("const", "the home directory"),
    "_tmux_sessions": ("sig", "row", "the liveness map when the caller passed none"),
    "_tree_of": ("sig", "cwd"),
    "_user_images": ("pure", "over a turn's blocks and text"),
    "_user_todo_session_ended": ("sig", "reg", "the reg's alive bit; else the death marker (gone) against the last states row (states)"),
    "_watch_awaiting": ("sig", "watch"),
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
    "_chat_postal_stats": ("out", "counters"),
    "_ledger_memo": ("memo", "see _ledger_memo.get"),
    "_ledger_memo_stats": ("out", "counters"),
    "_live_scope": ("sig", "names", "the pusher cycle's names scope: whether the build read names from the cycle's snapshot"),
    "_node_anchor_rev": ("sig", "anchors"),
    "_parse_mode": ("memo", "see _parse_mode.get"),
    "_pending_ops": ("sig", "ops"),
    "bisect": ("const", "a module"), "cm": ("const", "a module"), "em": ("const", "a module"),
    "jd": ("const", "a module"), "json": ("const", "a module"), "os": ("const", "a module"),
    "re": ("const", "a module"), "sb": ("const", "a module"), "sys": ("const", "a module"),
    "traceback": ("const", "a module"),
}

BACKEND_LOCALS = ("be", "_be_fk", "_cbe")   # the backend objects build_session binds and calls methods on
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


def _census_of(fn_src, module_names):
    """(calls, dotted, globals): the module-level functions called by name, the attribute-call chains
    on module objects or backend locals, and the module globals read without a call."""
    fn = ast.parse(fn_src).body[0]
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
                                                   or base.id in BACKEND_LOCALS):
                    dotted.add(base.id + "." + ".".join(chain))
        if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load) and x.id in module_names and x.id not in local:
            reads.add(x.id)
    return calls, dotted, reads - calls


class Census(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = _module_names()
        cls.calls, cls.dotted, cls.reads = _census_of(inspect.getsource(km.build_session), cls.names)

    def test_every_helper_build_session_calls_is_classified_and_nothing_stale_remains(self):
        self.assertEqual(self.calls, set(CENSUS),
                         "a helper build_session calls by name is missing from CENSUS (an unclassified read), "
                         "or CENSUS names one build_session no longer calls: %r"
                         % sorted(self.calls ^ set(CENSUS)))

    def test_every_attribute_call_on_a_module_object_or_backend_is_classified(self):
        self.assertEqual(self.dotted, set(DOTTED), sorted(self.dotted ^ set(DOTTED)))

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

    @unittest.skipUnless(hasattr(km, "_CHAT_SIG_LABELS"), "the labelled signature lands in the next commit")
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

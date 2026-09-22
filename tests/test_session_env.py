#!/usr/bin/env python3
"""Per-session env vars, spawn-time slice (the user 2026-08-17): two SDK sessions in the SAME
directory can run with different environments. Before this, env came only from directory-scoped
.claude/settings*.json — every session in the repo got it, and it outlived the session.

The mechanics under test:
  * `env_request_error` is the ONE validator both doors share (the /new handler mirrors it): a
    payload is a dict of NAME→string-value pairs, names matching [A-Za-z_][A-Za-z0-9_]*; anything
    else is named loudly, never skipped. A credential-shaped NAME of any spelling is refused by
    name, the value never quoted, and the advice says where the value belongs by the half of the
    rule it matched (2026-09-18; review round 2 of the env-pick door, 2026-09-19).
  * spawn() persists the dict in the session's reg (`env`) — the same home model/effort live in —
    and refuses a bad payload outright rather than writing a poisoned reg.
  * flag_settings_path folds a non-empty env into the per-sid settings payload beside ultracode /
    fastMode, and the return-""-when-no-keys contract stands (with no key riding nothing is
    touched, as before the door). It refuses a sid that is not a bare file name and a path that
    is a symbolic link (review round 2 of the env-pick door, 2026-09-19), and a directory whose real
    path is not under the state root's (round 9 of fork PR #781's review, fresh-2: a linked
    sdk-flag-settings/ was followed and the env block written outside the root), and writes on write_reg's
    temp-and-rename pattern, to a fresh inode and never through the existing one (review round 3,
    2026-09-19). Every row it logs has a ring text whose length is a function of its format. The
    link check and the write run under _flag_settings_lock, so two connects for one sid write in
    turn, and a no-keys call leaves a file an earlier connect left as it was (both pinned after the
    mutation pass of round 3, 2026-09-19, which found neither read by a test). The exclusive open
    and the finally that removes only the temp this call created are pinned by execution (review
    round 4, 2026-09-19: O_TRUNC in O_EXCL's place left every suite green, and the unconditional
    unlink removed a file the refused call had not created).
  * The problem rows about a per-session env or its file are a DERIVED population (review round 4,
    2026-09-19, after the round-3 comment claimed every row while two reserved-name rows carried no
    ring text), and since review round 6 (2026-09-19) the derivation is keyed on the problem RING, not
    on call-site names: tests/env_ring_census.py enumerates every door to the ring by resolution (the
    one appender, every call reaching it on any receiver or through a parameter, alias or conduit, the
    kernel's feeders) and derives the CONTENT rows as the door calls whose text carries a value of the
    pick or its file; the module's `# ENV ROWS:` line is that derivation (EnvRowsPopulation), every
    value-tainted door call declares problem= explicitly, every format on the line has a worst case
    computed here from the format with the repeat suffix on the KEYED rows (CredentialShapedNamesEndToEnd),
    each row is driven past its budgets through the real writer, and the lock-order sentence is pinned
    by a held-state probe inside the real _options and an AST census of the three sites
    (FlagSettingsLockOrder, EnvRowsPopulation).
  * _options threads the session's env into that file at EVERY connect — the file is rewritten on
    each use, so reconnects re-assert the reg's env by construction (pinned by tampering the file
    between two _options calls). Its stored-offender row states a fact and promises no remedy
    (review round 3: the redaction road left this change), with a short form for the error centre
    that is bounded by construction (one variable named, the rest counted through a bounded count,
    the session name and the named variable cut to a budget each), pinned as a property through
    the real ring for one, two and twenty variables and with the worst case computed from the
    format, the repeat suffix taken at a four-digit count.
  * set_env mirrors set_effort's shape (persist + reconnect to apply; env is connect-time), minus
    the badge/chip machinery that belongs to the not-yet-built UI slice; an UNCHANGED re-assert
    (the `romp new --env` re-brief on a standing session, or the fresh-spawn echo) skips the
    reconnect, since the asked-for env is already in force or already queued. A refused pick is a
    problem row whose ring text is bounded by construction, the session name cut to a budget and
    the refused names one named and the rest counted.
  * fork() inherits the parent's env like model/auth (it is that conversation, continued
    elsewhere), LESS any credential-shaped name (review round 1 of the env-pick door, 2026-09-18).

Values are assembled at run time, never a token-shaped literal (gitleaks reads this repo too); the
door tests deliberately plant credential-shaped NAMES, since refusing them is what they pin.
"""
import ast
import collections
import concurrent.futures
import contextlib
import copy
import errno
import glob
import inspect
import io
import json
import multiprocessing
import os
import pickle
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
import types
import unittest
import uuid
import warnings
from concurrent.futures.process import BrokenProcessPool
from pathlib import Path
from unittest import mock
from romp_load import load_source
import env_ring_census as erc
from env_ring_census import Census, CensusError, DEFAULT_SOURCES, census

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
sb = load_source("romp_sdk_backend_env", os.path.join(BIN, "romp_sdk_backend.py"))

PARENT = "11111111-2222-3333-4444-555555555555"
CHILD = "66666666-7777-8888-9999-aaaaaaaaaaaa"
CHILD2 = "77777777-8888-9999-aaaa-bbbbbbbbbbbb"
ENV = {"FEATURE_FLAG": "1", "UI_THEME": "dark"}
PLAIN = {"NOTES_ENDPOINT": "http://notes.test"}   # a plain name beside a credential-shaped one in the door tests


def _secret_value(tag):
    """A synthetic credential-shaped VALUE built at run time from short parts: gitleaks reads this repo, so no
    token-shaped literal ever sits in a test (the spawn.json fix's tests build theirs the same way)."""
    return "synthetic-" + tag + "-" + uuid.uuid4().hex


class _OsProxy:
    """The module's `os` with one function interposed and everything else forwarded: `replace` runs a hook in place
    of os.replace on the flag-settings writer's rename (a forced failure). Rebound as sb.os for a test's duration,
    since the module's functions read `os` from their globals; restored by addCleanup."""

    def __init__(self, real, replace=None):
        self._real, self._replace = real, replace

    def __getattr__(self, name):
        return getattr(self._real, name)

    def replace(self, src, dst):
        if self._replace is not None and sb.FLAG_SETTINGS_DIR in str(dst):   # the flag-settings writer's rename only:
            return self._replace(self._real, src, dst)                        #  write_reg's goes through this os too
        return self._real.replace(src, dst)


def _interpose(test, **kw):
    real = sb.os
    test.addCleanup(setattr, sb, "os", real)
    sb.os = _OsProxy(real, **kw)
    return real


def _temps(d):
    return sorted(os.path.basename(t) for t in glob.glob(os.path.join(str(d), sb.FLAG_SETTINGS_DIR, "*.tmp")))


SDK_BACKEND = os.path.join(os.path.dirname(HERE), "kernel", "sdk_backend.py")
# The fourth existence row's declaration (SdkSession._log_quietly's problem road) states that its callers' bound is
# currently unmet and names the tracked item; the same clause stands at the road's comment, in the census docstring and in
# the ENV ROWS paragraph, and test_each_existence_row_filed_as_a_problem_says_why_it_is_declared_and_not_bounded pins it
# on each (the post-merge census of the env-pick door, 2026-09-20, ruling 2's sharpening).
UNMET_CLAUSE = ("That responsibility is CURRENTLY UNMET: every caller formats self.name uncut (kernel.NAME_RE caps no length), the "
                "unreadable-list line joins up to twelve CLI key names uncut into its text and its key, and the five failure reports "
                "interpolate an exception's text uncut; tracked as ")
UNMET_ITEM = "ITEM: _log_quietly True callers unbounded (2026-09-20)"
KERNEL_PY = os.path.join(os.path.dirname(HERE), "kernel", "kernel.py")
CREDENTIALS_PY = os.path.join(os.path.dirname(HERE), "kernel", "credentials.py")
def _parsed(path):
    """A module's AST and its parent map (the walk needs the enclosing def and the enclosing handlers of a call)."""
    tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    return tree, parents


def _enclosing_def(node, parents):
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return node
    return None


def _lock_withs_above(node, parents):
    """The `with` (or `async with`) statements lexically enclosing `node` inside its def whose context names a lock (any
    context expression whose source spells "lock", in any letter case: self._lock, _reg_lock, a module-level LOCK)."""
    out = []
    while node in parents:
        node = parents[node]
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            break
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if "lock" in ast.unparse(item.context_expr).lower():
                    out.append((node.lineno, ast.unparse(item.context_expr)))
    return out


def _declaration_surfaces():
    """The two prose surfaces the census's declarations are pinned on, each read AS ITSELF (round 7 of the env-pick door's
    review, 2026-09-20, tests-3: read module-wide, a phrase could leave the surface an assertion names and the pin stayed
    green): the census module's docstring through ast.get_docstring, whitespace-normalised, and the ENV ROWS paragraph in
    kernel/sdk_backend.py as its list of comment lines (hash-stripped; join them with a space to read a phrase across a
    wrap), read from the one line starting `# ENV ROWS: ` to the first line that is not a comment."""
    tree, _parents = _parsed(os.path.join(HERE, "env_ring_census.py"))
    census_doc = " ".join((ast.get_docstring(tree) or "").split())
    lines = Path(SDK_BACKEND).read_text(encoding="utf-8").splitlines()
    starts = [i for i, ln in enumerate(lines) if ln.startswith("# ENV ROWS: ")]
    assert len(starts) == 1, "one ENV ROWS line to read the paragraph under: %r" % starts
    para, j = [], starts[0] + 1
    while j < len(lines) and lines[j].startswith("#"):
        para.append(lines[j].lstrip("#").strip())
        j += 1
    return census_doc, para


def _comment_block(path, marker):
    """A comment block read AS ITSELF (round 8 of the review, 2026-09-21, tests-3: a pin whose message named a docstring or a
    paragraph read the whole file, so a sentence leaving the surface the message names kept it green): the contiguous run
    of comment lines around the ONE line of `path` containing `marker`, at any indent, each stripped of its hash and
    whitespace, joined with single spaces so a phrase reads across a wrap."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    hits = [i for i, ln in enumerate(lines) if marker in ln]
    assert len(hits) == 1, "one line of %s carries the marker %r: %r" % (os.path.basename(path), marker, hits)
    is_comment = lambda i: 0 <= i < len(lines) and lines[i].lstrip().startswith("#")
    assert is_comment(hits[0]), "the marker line is a comment line: %r" % lines[hits[0]]
    lo = hi = hits[0]
    while is_comment(lo - 1):
        lo -= 1
    while is_comment(hi + 1):
        hi += 1
    return " ".join(lines[i].lstrip().lstrip("#").strip() for i in range(lo, hi + 1))


def _method_docstring(path, cls, name):
    """A method's docstring read AS ITSELF (ast.get_docstring on the def, whitespace-normalised), for a declaration pinned
    on the def's own prose rather than on the module's text (round 7's lenses, 2026-09-20: the conduit's routine-list
    clause was read by no test, so the round-6 wording that covered the five failure reports could return green)."""
    tree, _parents = _parsed(path)
    hits = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == cls]
    assert len(hits) == 1, "%d classes named %s in %s" % (len(hits), cls, path)
    defs = [n for n in hits[0].body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name]
    assert len(defs) == 1, "%d defs named %s in %s" % (len(defs), name, cls)
    return " ".join((ast.get_docstring(defs[0]) or "").split())


def _true_road(p):
    """The conduit's problem road a bound constant argument takes: any constant other than False or None (the round-7
    ruling's rule; a falsy constant such as 0 is filed here too, a false red rather than a silent miss)."""
    return isinstance(p, ast.Constant) and p.value is not False and p.value is not None


def _true_callers(rows):
    """[(caller name, carries a ring_text)] over Census.bound_site_args rows for the sites on the conduit's True road: the
    ring_text is carried unless the bound argument is the constant None (the default, or None written)."""
    return sorted((caller.name, not (isinstance(b.get("ring_text"), ast.Constant) and b["ring_text"].value is None))
                  for caller, _call, b in rows if _true_road(b.get("problem")))


CENSUS_FILES = (SDK_BACKEND, KERNEL_PY, CREDENTIALS_PY)
# The content rows by identity: the writing function, the module-level format the ring text starts from, and whether
# the call passes key= (the rows the launch files at every connect are keyed). Nine at review round 6; eleven since the
# merge of main (the post-merge census, 2026-09-20): main's fork PR #777 added two refused-launch rows in
# _host_transport_for, tainted through the host process, bounded by HOST_REFUSED_RING in the follow-up commit. Twelve
# since the round-8 merge of main (2026-09-21): main's fork PR #814 added the directory-refused row in
# _refused_directory_row, the same prose through problem_row's log= again (one explicit violation, one UNBOUNDED row),
# bounded by HOST_REFUSED_RING inside that merge, the way the two sibling roads were. Thirteen since round 9's closing
# commit (fresh-2, held to the landing): the writer's fourth row, the directory whose real path is not under the state
# root's (FLAG_DIR_LINK_RING), filed where a linked sdk-flag-settings/ had been followed with no row.
# Re-derived at round 9's closing commit: census content_identities() = [('flag_settings_path', 'FLAG_SID_RING', False),
# ('flag_settings_path', 'FLAG_LINK_RING', False), ('flag_settings_path', 'FLAG_DIR_LINK_RING', False),
# ('flag_settings_path', 'FLAG_UNWRITABLE_RING', False), ('_host_transport_for', 'HOST_REFUSED_RING', False),
# ('_host_transport_for', 'HOST_REFUSED_RING', False), ('_refused_directory_row', 'HOST_REFUSED_RING', False),
# ('_options', 'RESERVED_DROP_RING', True), ('_options', 'STORED_OFFENDER_RING', True), ('fork', 'FORK_RESERVED_RING',
# False), ('fork', 'FORK_DROP_RING', False), ('set_env', 'REFUSAL_RING_HEAD', False), ('set_env', 'REFUSAL_RING_HEAD',
# False)]
ROWS = [
    ("flag_settings_path", "FLAG_SID_RING", False), ("flag_settings_path", "FLAG_LINK_RING", False),
    ("flag_settings_path", "FLAG_DIR_LINK_RING", False), ("flag_settings_path", "FLAG_UNWRITABLE_RING", False),
    ("_host_transport_for", "HOST_REFUSED_RING", False), ("_host_transport_for", "HOST_REFUSED_RING", False),
    ("_refused_directory_row", "HOST_REFUSED_RING", False),
    ("_options", "RESERVED_DROP_RING", True), ("_options", "STORED_OFFENDER_RING", True),
    ("fork", "FORK_RESERVED_RING", False), ("fork", "FORK_DROP_RING", False),
    ("set_env", "REFUSAL_RING_HEAD", False), ("set_env", "REFUSAL_RING_HEAD", False),
]
# The tables: what the census finds at the head this block ships on, each entry an EXACT count asserted by EQUALITY
# (round 8 of the review, 2026-09-21; derived at the round-8 merge of main and pasted: that merge, of fork PR #814, grew
# the population over round 8's commit, doors 436 to 442, self calls 198 to 202, door-value sites 20 to 21, problem_row
# sites 13 to 14, content rows 11 to 12, functions 3233 to 3241, and this equality fired on the growth before the tables
# were re-derived there; re-derived again at the round's SECOND merge of main, which brought fork PR #884: functions
# 3241 to 3245, its two `skipped` lambdas, _row_owner and refused_in_replay, and no other entry moved; re-derived at round
# 9's closing commit, which added the writer's directory row through a new helper: doors 442 to 443, calls reaching the
# writer 358 to 359 (param 35 to 36), content rows 12 to 13, functions 3246 to 3247, and no other entry moved). Until round 8 these were FLOORS, and a floor
# is silent slack: twice a merge of main grew the population under floors that stayed green (38 doors of slack at round
# 6's head; three doors, a call, a door-value site, a problem_row site and a function at round 7's head), and at that
# head a walk blinded to one param-kind door call passed every floor. The rule as enforced now: any growth or shrinkage
# of the population reds this equality, and the author re-derives deliberately, stating the new head in this sentence.
# The expected value is NEVER read from the census at run time (a pin whose expected value comes from the artifact it
# guards cannot disagree with it). Re-derive, from the repository root:
#   python3 -c 'import json, os, sys; sys.path.insert(0, "tests"); import env_ring_census as e
#   c = e.Census([os.path.join("kernel", f) for f in ("sdk_backend.py", "kernel.py", "credentials.py")], e.DEFAULT_SOURCES)
#   print(json.dumps(c.counts, sort_keys=True)); print(json.dumps(c.by_kind, sort_keys=True))
#   print(len(c.existence_rows), len(c.mods["credentials.py"].fns))'
COUNTS = {
    "doors": 443,                  # 1 appender + 359 calls reaching it + 47 conduit and feeder call sites (_log_quietly 21,
    #                                problem_row 14, _sdk_problem 8, _spend_guard_row 2, _note_ws_drop 2) + 21 door-as-argument
    #                                sites + 10 parameter-bound functions + 2 feeder appends + 3 merge reads
    "calls_reaching_writer": 359,  # self._log in SdkBackend 202, another receiver 109, ApiHealth's bound self._log 7,
    #                                a log= parameter 36, a local alias 5
    "log_param_fns": 10,           # problem_row, ApiHealth.__init__, flag_settings_path, cli_scope_supported, cli_scope_limits and
    #                                its pass-through _cli_scope_settle, helper_fast_org_env and its pass-through key_fast_org_env,
    #                                relocate_transcripts, sweep_dead_test_roots
    "door_value_sites": 21,        # call sites passing a door as an argument: 14 problem_row (one in kernel.py, through getattr),
    #                                ApiHealth, cli_scope_supported, cli_scope_limits, sweep_dead_test_roots, flag_settings_path,
    #                                helper_fast_org_env, relocate_transcripts
    "problem_row_sites": 14,       # the problem_row calls that pass log= (13 in sdk_backend.py, 1 in kernel.py through getattr): the
    #                                same 14 the door_value_sites entry credits to problem_row. 17 problem_row calls in the three files;
    #                                the 3 that pass no log= (main's two refused-launch sites and the directory-refused row's) bind the
    #                                conduit's door to None and are sites of NEITHER count (env_ring_census's rule: such a site files
    #                                nothing through the conduit and is no site of it), so both entries read 14 = 17 - 3 (round 9)
    "sdk_problem_sites": 8,
    "feeder_appends": 2,           # _SDK_BOOT_PROBLEMS in _sdk_problem, _WS_DROPS in _note_ws_drop
    "merge_reads": 3,              # _sdk_problem_rows reads the two lists and be.problems()
    "content_rows": 13,            # the ENV ROWS line's rows; content_identities() == ROWS holds them exactly, so this entry
    #                                carries no tension of its own and is here so the block is truthful
    "functions": 3247,             # every def and lambda of the three files, nested ones included: 3245 at the second merge of main,
    #                                re-derived at round 9's commit as 3246 (_UnownedBackend.set_env, the one def the round added;
    #                                no other entry moved) and at round 9's closing commit as 3247 (_flag_settings_dir_link_rows, the
    #                                directory row's helper; the credentials.py count did not move)
}
CALLS_BY_KIND = {"self": 202, "typed": 109, "bound-self": 7, "param": 36, "alias": 5}   # the 359's derivation, an equality each
EXISTENCE_ROWS = 20      # the existence rows (tag "pick" alone, a fixed vocabulary plus names): derived at round 8's commit and
#                          re-derived unchanged at both round-8 merges of main; the vocabulary test holds the count exactly (a
#                          floor of 20 stood here until round 8)
CREDENTIALS_FNS = 28     # every def and lambda of kernel/credentials.py, the census's proof that it read a file with no door:
#                          derived at round 8's commit and unchanged at both round-8 merges of main (a floor of 20 stood here
#                          until round 8)


def _table_mismatches(counts, by_kind):
    """Every table entry the census's counts DIFFER from, as (name, found, committed): COUNTS over the counts, then
    CALLS_BY_KIND over the per-kind calls, in both directions (round 8: the floors this replaces named a shortfall alone,
    and growth passed in silence). All of them, so a per-kind difference is named even when the doors total moves with
    it (the round-6 mutation pass dropped `self` by one and saw only the doors floor fire, the assertions running in
    order)."""
    got = {"doors": counts["doors"], "calls_reaching_writer": counts["calls_reaching_writer"],
           "log_param_fns": counts["log_param_fns"], "door_value_sites": counts["door_value_sites"],
           "problem_row_sites": counts["conduit_sites"]["conduit:problem_row"],
           "sdk_problem_sites": counts["conduit_sites"]["conduit:_sdk_problem"],
           "feeder_appends": counts["feeder_appends"], "merge_reads": counts["merge_reads"],
           "content_rows": counts["content_rows"], "functions": counts["functions"]}
    out = [(k, got[k], n) for k, n in COUNTS.items() if got[k] != n]
    out += [(kind, by_kind.get(kind, 0), n) for kind, n in CALLS_BY_KIND.items() if by_kind.get(kind, 0) != n]
    return out


# ---- the small module: the input of the census's MECHANICS pins (round 8 of the review on fork PR #781, 2026-09-21) ----
# The reviewer's ruling: a test uses the SMALLEST input that can exhibit the property it asserts. A walker-mechanics
# property ("does the walker classify a bare-name loader planted here?") needs the planted module plus whatever the
# walker must resolve against, and nothing else; running it behind the 22k lines of kernel/sdk_backend.py does not
# test it harder and is LESS precise: an assertion over the whole tree can pass or fail for a reason unrelated to its
# plant (another door value escaping, a row moving, a merge of main growing the population under the plant, as the
# round-8 merge did to every count). A population property ("are there blind spots anywhere in the tree?") needs the
# population by definition and pays for it once per process, through env_ring_census's census() door. Until this
# commit every mechanics pin planted on a sabotaged copy of the real file beside kernel/credentials.py, about 180
# copies at about 1.3 s each, and was the module's cost. What a plant needs beside it, read off the walker's code
# (tests/env_ring_census.py), and what this module therefore carries:
#   the WRITER (Census._find_writer): one method appending to its own self._problems inside a class, its message the
#     second parameter, with problem, key and ring_text parameters (SdkBackend._log(self, m, problem, key, ring_text)),
#     __init__'s empty-list binding, and every other reference to the ring a read inside that class through self by a
#     copying or counting builtin, a loop or a comprehension, or the writer's own trim: the seven reference shapes the
#     real writer's class has, so a plant's second writer or foreign touch is judged against the same admitted set;
#   the RECEIVER CLASSES the plants type by (Census.receiver_classes, _annotation_classes, _class_object): the writer's
#     class under the exact header `class SdkBackend:` (the alias-resolution pin swaps a base in), a second class holding
#     the backend on an attribute bound in __init__ from a string-annotated parameter (SdkSession.backend, the
#     "typed by its __init__" arm), and a third class binding `_ring` in its __init__ and reading it in a method
#     (ApiHealth's deque: the twice-bound name the alias pins collide with, and the method the API_ANCHOR plants edit);
#   the CONDUIT the roster pins bind sites against (Census.bound_site_args, the conduit walk of _door_calls): a method
#     whose door call's message is its own parameter, with the real conduit's two roads and one site of its own
#     (SdkSession._log_quietly, called once from _serve), so a planted site is one more beside a roster of one;
#   the SOURCES the plants read or fold (DEFAULT_SOURCES, matched by (basename, name), which is why the module is
#     written to disk as sdk_backend.py): the attribute source env_vars, read on any receiver; the name source
#     AUTH_ENV_NAMES the conduit-fold pins fold, defined at module scope beside ENV_RESERVED_NAMES; one declared dict
#     source, SdkBackend._launch_shape, in the real one's shape (a dict literal with the env under its key, built from
#     sess.env_vars minus the reserved names), which gives the census a declared roots table for the pool transport pin
#     to carry across the process boundary; the function-keyed declarations a plant adds (_tenth_shape) match by the
#     same basename;
#   the ANCHORS the plants edit at, one each (asserted at the class's setUpClass): FMT_ANCHOR (a module-level ring
#     format, the plants' TENTH_RING goes before it), METHOD_ANCHOR (the writer's class body after _log, where the
#     plants' _tenth methods go), SESSION_ANCHOR (the conduit's def, the roster and second-writer plants go before it),
#     CRASH_ANCHOR (the crash line, an f-string whose leading text the reduction pin removes) and API_ANCHOR
#     (ApiHealth._push, the alias pins' ApiHealth arms go before it);
#   a door call of each shape the reduction reads (a self call with a literal head, a typed call through self.backend,
#     the conduit's two inner calls with a literal site), so the small census has heads to reduce and the crash line's
#     unreduced arm is one against none.
# NOT needed, by the same reading: kernel/kernel.py (its feeders are found by the def name _sdk_problem_rows, which the
# feeder pin plants in a synthetic module of its own) and kernel/credentials.py (the walker reaches it only through
# the calls the real sdk_backend.py makes into its functions; this module makes none, and a sources entry for a file
# the census was not handed matches nothing and fails nothing: _source_tag keys a name on the READING function's own
# basename). The census over the unplanted module is clean by construction and asserted so once per process
# (small_census: no content row, no failure, no explicit violation, nothing unreduced; the writer SdkBackend._log with
# message parameter m), so a plant's row is the only row and a plant's failure the only failure, and every count a
# mechanics pin reads is the plant's own. The module is never executed, only parsed; it is plausible Python so a reader
# can follow a plant against it. Not a repo file of its own: the anchors, the resolve-against derivation above and the
# plants that edit it live in one place.
SMALL_SDK_BACKEND = r'''"""The small module: a synthetic kernel/sdk_backend.py the census's mechanics pins plant on (the block comment above
SMALL_SDK_BACKEND in tests/test_session_env.py derives what it carries from the walker's code). Parsed, never run."""
import sys
import threading
import time
import traceback
from collections import deque
from typing import Any, Optional, Protocol

RESERVED_DROP_RING = ("env (%s): ignoring reserved %s from the stored session env: romp sets the identity env")
ENV_RESERVED_NAMES = ("ROMP_SID", "ROMP_SESSION_NAME")
AUTH_ENV_NAMES = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


class AhEvent(tuple):
    __slots__ = ()


class ApiHealth:
    def __init__(self, state_dir):
        self.state_dir = state_dir
        self._lock = threading.Lock()
        self._ring: deque = deque()

    def _push(self, ev: AhEvent):
        with self._lock:
            self._ring.append(ev)
            while self._ring and self._ring[0].t < ev.t - 3600:
                self._ring.popleft()

    def failures(self):
        with self._lock:
            return sum(1 for e in self._ring if e.kind != "ok")


class SdkSession:
    def __init__(self, backend: "SdkBackend", reg: dict):
        self.backend = backend
        self.sid = reg["sid"]
        self.name = reg.get("name", self.sid)

    def _log_quietly(self, line: str, problem=None, key=None, ring_text=None) -> None:
        try:
            if not problem:
                self.backend._log(line, problem=False)
            else:
                self.backend._log(line, problem=True, key=key, ring_text=ring_text)
        except Exception:
            pass

    def _run(self):
        try:
            self._serve()
        except Exception as e:
            self.backend._log(f"sdk session {self.name} crashed: {type(e).__name__}: {e}\n"
                              f"{traceback.format_exc()}")

    def _serve(self):
        self._log_quietly("reconnect (%s): serving" % self.name)


class SdkBackend:
    PROBLEM_RING = 100

    def __init__(self, state_dir, notify=None):
        self.state_dir = state_dir
        self._notify = notify
        self._log_cb = None
        self._problems: list[dict] = []
        self._problem_seq = 0
        self._problem_lock = threading.Lock()
        self.health = ApiHealth(state_dir)

    def _launch_shape(self, sess):
        reserved = ENV_RESERVED_NAMES + AUTH_ENV_NAMES
        return {"mode": sess.mode, "env": {k: v for k, v in sess.env_vars.items() if k not in reserved}}

    def _log(self, m, problem=None, key=None, ring_text=None):
        if problem is None:
            problem = sys.exc_info()[0] is not None
        rt = str(m if ring_text is None else ring_text)
        if problem:
            with self._problem_lock:
                hit = None
                if key is not None:
                    for entry in reversed(self._problems):
                        if entry.get("key") == key:
                            hit = entry
                            break
                if hit is not None:
                    hit["count"] = int(hit.get("count") or 1) + 1
                else:
                    self._problem_seq += 1
                    row = {"seq": self._problem_seq, "t": time.time(), "text": rt}
                    if key is not None:
                        row.update(key=key, first=rt, count=1)
                    self._problems.append(row)
                    if len(self._problems) > self.PROBLEM_RING:
                        del self._problems[:-self.PROBLEM_RING]
        if self._log_cb:
            self._log_cb(m)

    def problem_seq(self) -> int:
        with self._problem_lock:
            return self._problem_seq

    def problems(self, limit: int = 0) -> list[dict]:
        with self._problem_lock:
            rows = list(self._problems)
        return rows[-limit:] if limit else rows

    def problem_keyed(self, key) -> bool:
        with self._problem_lock:
            return any(row.get("key") == key for row in self._problems)

    def _note_launch(self, sess):
        self._log("launch (%s): starting" % sess.name, problem=False)
'''
_SMALL = {}


def small_module_files():
    """The small module written once per process to a scratch directory as sdk_backend.py (the basename the sources table
    keys on and the failure rows name), as the one-file tuple a census is built over; a plant goes beside it in the same
    tuple, a copy of it is edited through EnvRowsCensusBlindSpots._copy."""
    if "files" not in _SMALL:
        path = os.path.join(tempfile.mkdtemp(), "sdk_backend.py")
        Path(path).write_text(SMALL_SDK_BACKEND, encoding="utf-8")
        _SMALL["files"] = (path,)
    return _SMALL["files"]


def small_census():
    """The census over the unplanted small module, the mechanics pins' CONTROL: built once per process, here (the
    census() door keeps censuses over the canonical inputs alone, so a door read of it would build it again), frozen like
    the door's (env_ring_census.freeze) so no pin can change what the next reads, and asserted clean at its construction
    (the block comment above SMALL_SDK_BACKEND says why the pins rely on that): no content row, no failure, no explicit
    violation, nothing unreduced, the writer SdkBackend._log with message parameter m."""
    if "census" not in _SMALL:
        c = erc.freeze(Census(small_module_files(), DEFAULT_SOURCES))
        assert (c.writer.qual, c.door, c.msg_param) == ("SdkBackend._log", "_log", "m"), (c.writer, c.door, c.msg_param)
        assert (list(c.failures), list(c.content_rows), list(c.explicit_violations), list(c.unreduced)) == ([], [], [], []), c.summary()
        _SMALL["census"] = c
    return _SMALL["census"]


class _Backend(unittest.TestCase):
    """Base: a backend on a temp state dir, no real CLI, no real key claim."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self._fetch_before = sb._fetch_key_fast_org
        sb._fetch_key_fast_org = lambda key: None  # the fast-org probe is a real HTTPS GET — never from a test
        self.be = sb.SdkBackend(self.d, "/bin/true", lambda *a, **k: None)

    def tearDown(self):
        sb._fetch_key_fast_org = self._fetch_before

    def _reg(self, sid):
        return sb.read_reg(self.be.state_dir, sid)

    def _sess(self, sid):
        return sb.SdkSession(self.be, sb.read_reg(self.be.state_dir, sid))


class EnvRequestError(unittest.TestCase):
    """The shared validator: loud and specific, never a silent skip."""

    def test_valid_payloads_pass(self):
        self.assertEqual(sb.env_request_error({"FEATURE_FLAG": "1"}), "")
        self.assertEqual(sb.env_request_error({"_UNDER": "x", "A9": ""}), "",
                         "an empty VALUE is meaningful — explicitly setting empty")
        self.assertEqual(sb.env_request_error({}), "", "an empty dict is a valid (vacuous) payload")

    def test_a_non_dict_is_named(self):
        for bad in ("FEATURE_FLAG=1", ["FEATURE_FLAG"], 7, None):
            err = sb.env_request_error(bad)
            self.assertIn("env", err)
            self.assertTrue(err, "a non-object payload must be refused, not coerced")

    def test_a_bad_name_is_named(self):
        for bad in ("9BAD", "", "BAD-NAME", "BAD NAME", "über"):
            err = sb.env_request_error({bad: "1"})
            self.assertIn("[A-Za-z_][A-Za-z0-9_]*", err,
                          "the error must teach the alphabet, not just refuse: %r" % bad)

    def test_a_non_string_value_is_named(self):
        for bad in (1, None, True, {"nested": "no"}):
            err = sb.env_request_error({"FEATURE_FLAG": bad})
            self.assertIn("FEATURE_FLAG", err,
                          "the offending NAME must be in the error (fail loudly): %r" % (bad,))

    def test_a_nul_byte_in_a_value_is_named(self):
        # an execve envp entry is a NUL-terminated C string, so a NUL value is unfulfillable by
        # definition — accepted, it bakes an env the CLI can only truncate or throw on into the reg
        err = sb.env_request_error({"FEATURE_FLAG": "1\x00x"})
        self.assertIn("FEATURE_FLAG", err, "the offending NAME must be in the error")
        self.assertIn("NUL", err, "the error names the actual problem")

    def test_other_control_bytes_stay_legitimate(self):
        self.assertEqual(sb.env_request_error({"FEATURE_FLAG": "line1\nline2\ttabbed"}), "",
                         "NUL only — newlines and tabs are legitimate env content")

    def test_the_identity_names_are_refused(self):
        # options.env owns ROMP_SID / ROMP_SESSION_NAME (the identity overlay below): a user var of
        # either name would silently shadow or be shadowed by the identity, breaking `romp end self`
        # with nothing pointing at the cause — refused at the door instead, like every bad payload
        for name in ("ROMP_SID", "ROMP_SESSION_NAME"):
            err = sb.env_request_error({name: "x"})
            self.assertIn(name, err, "the reserved NAME must be in the error")
            self.assertIn("romp sets", err, "the error teaches WHO owns the name, not just 'no'")
        self.assertTrue(sb.env_request_error({"FEATURE_FLAG": "1", "ROMP_SID": "x"}),
                        "a reserved name refuses the WHOLE payload, never a silent skip")


class FlagSettingsEnv(unittest.TestCase):
    """flag_settings_path folds env in beside ultracode/fastMode; the ""-when-empty contract stands."""

    def setUp(self):
        self.d = tempfile.mkdtemp()

    def _read(self, p):
        return json.loads(Path(p).read_text())

    def test_env_alone_writes_the_file(self):
        p = sb.flag_settings_path(self.d, PARENT, env=ENV)
        self.assertTrue(p)
        self.assertEqual(self._read(p), {"env": ENV})

    def test_env_rides_beside_the_boolean_keys(self):
        p = sb.flag_settings_path(self.d, PARENT, ultracode=True, fast=True, env=ENV)
        got = self._read(p)
        self.assertEqual(got["env"], ENV)
        self.assertTrue(got["ultracode"] and got["fastMode"],
                        "env must merge INTO the payload, not replace the keys already riding it")

    def test_no_keys_still_returns_empty(self):
        self.assertEqual(sb.flag_settings_path(self.d, PARENT), "")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=None), "")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env={}), "",
                         "an empty env adds no key — the no-keys contract is the common case")

    def test_no_keys_leaves_a_file_an_earlier_connect_left_as_it_was(self):
        """With no key riding the writer returns "" and touches nothing, the base's behaviour: a file an earlier
        connect left stays, byte for byte and inode for inode, and no temp is minted. Review round 1 of the env-pick
        door had the no-keys call unlink such a file, and review round 3 (2026-09-19) sent that away with the
        redaction road, so the contract is pinned against the file too, not the return alone (the mutation pass of
        that round found no test reading the file after a no-keys call)."""
        p = sb.flag_settings_path(self.d, PARENT, env=ENV)
        before, ino = Path(p).read_bytes(), os.stat(p).st_ino
        for kw in ({}, {"env": None}, {"env": {}}):
            self.assertEqual(sb.flag_settings_path(self.d, PARENT, **kw), "", kw)
            self.assertEqual(Path(p).read_bytes(), before, "the file an earlier connect left stays as it was: %r" % (kw,))
            self.assertEqual(os.stat(p).st_ino, ino, "and is not rewritten either: %r" % (kw,))
        self.assertEqual(_temps(self.d), [], "no temp for a write that never happens")

    def test_an_unwritable_dir_degrades_loudly(self):
        # a plain FILE where the flag-settings dir goes forces the OSError (os.makedirs raises)
        Path(self.d, sb.FLAG_SETTINGS_DIR).write_text("not a directory")
        logged = []
        p = sb.flag_settings_path(self.d, PARENT, env=ENV,
                                  log=lambda msg, problem=False, **kw: logged.append((msg, problem)))
        self.assertEqual(p, "", "degrade to launch — a session without its env still beats none")
        self.assertEqual(len(logged), 1)
        msg, problem = logged[0]
        self.assertTrue(problem, "the drop is a problem row, not a quiet info line")
        self.assertIn("env", msg, "the log names the dropped keys")
        self.assertIn(PARENT, msg, "the log names whose launch went without them")

    def test_the_oserror_path_stays_quiet_without_a_logger(self):
        Path(self.d, sb.FLAG_SETTINGS_DIR).write_text("not a directory")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV), "",
                         "log=None (direct callers) must neither raise nor change the '' contract")

    def test_no_keys_asked_means_no_log_even_on_a_bad_dir(self):
        Path(self.d, sb.FLAG_SETTINGS_DIR).write_text("not a directory")
        logged = []
        self.assertEqual(
            sb.flag_settings_path(self.d, PARENT, log=lambda *a, **k: logged.append(a)), "")
        self.assertEqual(logged, [], "nothing requested, nothing dropped — nothing to report")



class FlagSettingsWriter(unittest.TestCase):
    """The one writer of the per-sid flag-settings file (flag_settings_path) since review round 3 of the env-pick
    door (2026-09-19) sent the env pick's own edit of the file away with the redaction road. Three refusals stand
    ahead of its write (review round 2, the first two): a sid that is not a bare file name (rules-2 / kernel-4: the path
    is built from the sid, and a crafted one would carry the env block outside the state root), a path that is a symbolic
    link (extra5-2: the write road put the env block into the link's target), and a directory whose real path is not
    under the state root's (round 9 of fork PR #781's review, fresh-2, held to the landing: the file check saw the file's
    path alone, so with sdk-flag-settings/ a link the writer made the directory through it, wrote the env block into the
    link's target outside the root, filed no row and returned the in-root path; refused by realpath containment, which
    passes a state root that is itself a link). The write itself is write_reg's
    temp-and-rename (round 3, correctness-4 and kernel-3: an in-place O_TRUNC write refreshed a hard link's other
    name with every connect's env and followed a symlink planted between the check and the open), and every row the
    writer logs has a ring text whose length is a function of its format (round 3, correctness-3 and kernel-2: the
    link row ran to 383 to 453 characters over a real state root, past both caps, and the sid rows were unbounded).
    Review round 4 (2026-09-19) pinned by execution what the round-3 text had only stated: the exclusive open (tests-1
    and extra6-1: O_TRUNC in its place left every suite green), the finally that removes only what this call created
    (kernel-2 and extra6-2: it removed a file the refused call had not created), the sid cut on the link and the
    unwritable rows and the class-name cut (tests-2: driven for the sid row alone), and FLAG_SETTINGS_KEYS against
    the keys the writer writes (extra5-1). Review round 5's mutation pass (2026-09-19) pinned the lock's re-entrancy by
    execution on the lock itself (RLock replaced by Lock had left every suite green)."""

    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.d = os.path.join(self.root, "state")
        os.makedirs(os.path.join(self.d, sb.FLAG_SETTINGS_DIR))

    def _log(self):
        logged = []
        return logged, (lambda msg, problem=False, **kw: logged.append((msg, problem, kw)))

    def _pin_temp_name(self, sid=PARENT):
        """The writer's temp name made predictable, TempIsExclusive's method (tests/test_kernel_serve_token_mode.py):
        the module's `uuid` stands in with a fixed hex for the test, so the path the exclusive open will ask for is
        known ahead and a file can be planted there. Returns that path."""
        fixed = "0123456789abcdef0123456789abcdef"
        stand_in = types.SimpleNamespace(uuid4=lambda: types.SimpleNamespace(hex=fixed))
        self.addCleanup(setattr, sb, "uuid", sb.uuid)
        sb.uuid = stand_in
        return Path(self.d, sb.FLAG_SETTINGS_DIR, "%s.json.%d.%s.tmp" % (sid, os.getpid(), fixed[:8]))

    def test_a_file_already_at_the_temp_path_is_never_written_through(self):
        """tests-1 / extra6-1 (review round 4 of the env-pick door, 2026-09-19): O_EXCL on the temp open was pinned by
        nothing (O_TRUNC in its place left every suite green), and it is what makes the writer's two promises true, a
        FRESH inode and 0600 with no chmod after. Behaviour, not source text: with the temp name pinned, a regular
        file already there, holding a hard link under another name, and then a symbolic link to a file outside the
        directory, each make the open fail EEXIST; the writer refuses with the unwritable row and mints nothing. The
        assertions read the OTHER name and the OUTSIDE target, so they hold whatever the finally does with the plant
        itself (the next test pins that). Under O_TRUNC the write goes through the plant: the other name or the
        outside file carries the env block and the call returns the path with no row."""
        tmp = self._pin_temp_name()
        p = Path(self.d, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        tmp.write_text("planted\n")
        other = Path(self.root, "other-name")
        os.link(str(tmp), str(other))
        self.assertEqual(os.stat(other).st_nlink, 2, "the state under test: the planted inode has two names")
        logged, log = self._log()
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, log=log), "", "the write road refuses")
        self.assertEqual(other.read_text(), "planted\n", "the bytes never went through the existing inode")
        self.assertFalse(p.exists(), "nothing is minted at the settings path")
        self.assertEqual(len(logged), 1, logged)
        m, problem, kw = logged[0]
        self.assertTrue(problem)
        self.assertIn("unwritable", m)
        self.assertIn(os.strerror(errno.EEXIST), m, "the exclusive open met the existing file and the log line says so")
        self.assertEqual(kw["ring_text"], sb.FLAG_UNWRITABLE_RING % (PARENT, "FileExistsError", "env"))
        if tmp.exists():
            os.unlink(tmp)
        os.unlink(other)
        target = Path(self.root, "outside.json")
        target.write_text(json.dumps({"env": {"OUTSIDE": "kept"}}) + "\n")
        os.chmod(target, 0o644)
        os.symlink(str(target), str(tmp))
        del logged[:]
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, log=log), "", "a link at the temp path is not followed")
        self.assertEqual(json.loads(target.read_text()), {"env": {"OUTSIDE": "kept"}}, "the outside file is untouched")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644, "and keeps its mode")
        self.assertFalse(p.exists())
        self.assertEqual(len(logged), 1, logged)
        self.assertEqual(logged[0][2]["ring_text"], sb.FLAG_UNWRITABLE_RING % (PARENT, "FileExistsError", "env"))
        if os.path.lexists(tmp):
            os.unlink(tmp)
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, log=log), str(p), "with the path free the same call writes")
        self.assertEqual(stat.S_IMODE(p.stat().st_mode), 0o600, "a fresh inode, created private")
        self.assertEqual(len(logged), 1, "and says nothing")
        self.assertEqual(_temps(self.d), [])

    def test_a_refused_write_removes_no_file_it_did_not_create(self):
        """kernel-2 / extra6-2 (review round 4 of the env-pick door, 2026-09-19): the finally unlinked the temp path
        unconditionally, so on the EEXIST road the file at the path, which is not this writer's, was deleted by the
        call that had refused to write through it. The guard is the descriptor the open returned: no descriptor,
        nothing of this call's to remove. A planted regular file survives byte for byte on its own inode and a planted
        symbolic link stays a link; the row still fires and nothing is minted. Red on 291268585, where the plant is
        gone after the call. The temps this call does create are still swept: the failed-rename test beside this one
        reads none left."""
        tmp = self._pin_temp_name()
        p = Path(self.d, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        tmp.write_text("planted\n")
        before = tmp.stat()
        logged, log = self._log()
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, log=log), "")
        self.assertTrue(tmp.exists(), "the plant survives the call that refused to write through it")
        self.assertEqual(tmp.read_text(), "planted\n", "byte for byte")
        self.assertEqual(tmp.stat().st_ino, before.st_ino, "on its own inode")
        self.assertEqual(tmp.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertFalse(p.exists())
        self.assertEqual(len(logged), 1, logged)
        self.assertIn("unwritable", logged[0][0])
        os.unlink(tmp)
        target = Path(self.root, "outside.json")
        target.write_text("kept\n")
        os.symlink(str(target), str(tmp))
        del logged[:]
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, log=log), "")
        self.assertTrue(os.path.islink(tmp), "the link is left in place: it is not this writer's")
        self.assertEqual(target.read_text(), "kept\n")
        self.assertEqual(len(logged), 1, logged)
        os.unlink(tmp)
        self.assertEqual(_temps(self.d), [])

    def test_flag_settings_keys_is_what_the_writer_writes(self):
        """extra5-1 (review round 4 of the env-pick door, 2026-09-19): the sid row's and the unwritable row's bounds rest
        on FLAG_SETTINGS_KEYS naming every key the writer writes, and nothing tied the constant to the writer: a fifth
        key left the worst-case pin green while the real sid row ran to 250 against 240. The writer is driven with
        every keyword-only knob its signature has, each at a value that writes (a bool True, a dict with one entry, a
        str), so a knob this test does not know by name is driven too, and the written file's keys must be the
        constant. Headroom under the cap is 7 characters, so the next key must shorten a format or spend it."""
        sig = inspect.signature(sb.flag_settings_path)
        knobs = {}
        for name, prm in sig.parameters.items():
            if prm.kind is not prm.KEYWORD_ONLY or name == "log":
                continue
            if isinstance(prm.default, bool):
                knobs[name] = True
            elif prm.default is None or isinstance(prm.default, dict):
                knobs[name] = {"A_FLAG": "1"}
            elif isinstance(prm.default, str):
                knobs[name] = "x"
            else:
                self.fail("a knob of a shape this pin cannot drive: %s=%r; extend the pin" % (name, prm.default))
        self.assertGreaterEqual(len(knobs), 4, "the four knobs the writer had at review round 4: %r" % (sorted(knobs),))
        written = sb.flag_settings_path(self.d, PARENT, **knobs)
        self.assertTrue(written)
        self.assertEqual(sorted(json.loads(Path(written).read_text())), list(sb.FLAG_SETTINGS_KEYS),
                         "FLAG_SETTINGS_KEYS is the set of keys the writer writes, sorted: the sid row's bound is computed "
                         "from it, so a key written and not named here moves the real row past the pin (7 characters of headroom)")
        self.assertEqual(sorted(sb.FLAG_SETTINGS_KEYS), list(sb.FLAG_SETTINGS_KEYS), "sorted, as the writer joins them")

    def test_a_traversal_sid_is_refused_before_anything_is_touched(self):
        victim = Path(self.root, "victim.json")
        victim.write_text(json.dumps({"env": {"KEEP": "me"}}) + "\n")
        st = victim.stat()
        sid = "../../victim"
        self.assertEqual(os.path.normpath(os.path.join(self.d, sb.FLAG_SETTINGS_DIR, sid + ".json")), str(victim),
                         "the sid would resolve to the victim outside the directory")
        logged, log = self._log()
        self.assertEqual(sb.flag_settings_path(self.d, sid, env=ENV, log=log), "", "the write road")
        self.assertEqual(json.loads(victim.read_text()), {"env": {"KEEP": "me"}}, "the victim's bytes are untouched")
        self.assertEqual(victim.stat().st_mtime_ns, st.st_mtime_ns, "and it was not rewritten in place either")
        self.assertEqual(len(logged), 1, logged)
        m, problem, kw = logged[0]
        self.assertTrue(problem)
        self.assertIn("not a bare file name", m, "the refusal names the specific reason")
        self.assertIn(repr(sid), m)
        self.assertIn("launching WITHOUT env", m, "the write road says what the launch goes without")
        self.assertEqual(kw["ring_text"], sb.FLAG_SID_RING % (sb.FLAG_SID_REASONS[2], repr(sid), "env"),
                         "the ring text: the reason, the sid's repr within its budget, the keys")
        self.assertLessEqual(len(kw["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)
        self.assertEqual(sb.flag_settings_path(self.d, sid, log=log), "", "with no key riding nothing is written and nothing said")
        self.assertEqual(len(logged), 1)
        for bad in ("..", ".", "", None, "a\0b", "x/y", 7):
            self.assertEqual(sb.flag_settings_path(self.d, bad, env=ENV), "", repr(bad))
        self.assertEqual(os.listdir(os.path.join(self.d, sb.FLAG_SETTINGS_DIR)), [], "nothing was written under the directory either")
        self.assertEqual(sb._flag_settings_sid_error(PARENT), "", "a kernel-minted uuid passes")
        self.assertTrue(sb.flag_settings_path(self.d, PARENT, env=ENV), "and writes as before")

    def test_a_symbolic_link_is_refused_and_nothing_is_written_through_it(self):
        import stat
        target = Path(self.root, "outside.json")
        target.write_text(json.dumps({"env": {"OUTSIDE": "kept"}}) + "\n")
        os.chmod(target, 0o644)
        p = Path(self.d, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        os.symlink(str(target), str(p))
        logged, log = self._log()
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, fast=True, log=log), "", "the write road")
        self.assertTrue(os.path.islink(p), "the link is left in place")
        self.assertEqual(json.loads(target.read_text()), {"env": {"OUTSIDE": "kept"}}, "the target's bytes are untouched")
        self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o644, "and its mode (the write road used to chmod through the link)")
        self.assertEqual(len(logged), 1, logged)
        m, problem, kw = logged[0]
        self.assertTrue(problem)
        self.assertIn(str(p), m, "the kernel log line names the path")
        self.assertIn("symbolic link", m)
        self.assertIn(str(target), m, "and where the link points")
        self.assertEqual(kw["ring_text"], sb.FLAG_LINK_RING % PARENT, "the ring text names no path and no target")
        self.assertNotIn(self.root, kw["ring_text"])
        self.assertLessEqual(len(kw["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)
        self.assertEqual(_temps(self.d), [])

    def test_a_symbolic_link_at_the_directory_is_refused_and_nothing_is_written_through_it(self):
        """fresh-2 (round 9 of fork PR #781's review, held to the landing): the link check above sees the FILE's path
        alone, and the directory it sits in was followed, so with <state>/sdk-flag-settings a symbolic link the writer made
        the directory through it, wrote the env block, value included, into the link's target outside the state root,
        filed no row and returned the in-root path (round 3's refuter had named the shape as a residual; no round ruled on
        it until this one). Now the file's real path must be under the state root's (realpath containment, inside the
        lock): the write is refused with its own row, the kernel log line naming the directory, where it resolves and the
        root, the ring text none of them, and the link is left in place. Red at the round-9 head: the target directory
        holds the sid's file with the value in it, the call returns the in-root path, and nothing is logged."""
        outside = Path(self.root, "elsewhere")
        outside.mkdir()
        d = Path(self.d, sb.FLAG_SETTINGS_DIR)
        shutil.rmtree(d)                                         # setUp made the real directory; the plant is a link in its place
        os.symlink(str(outside), str(d))
        val = _secret_value("notes-token")
        env = {**ENV, "NOTES_API_TOKEN": val}                     # the value the base wrote outside the root; assembled at run time
        p = Path(d, PARENT + ".json")
        logged, log = self._log()
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=env, fast=True, log=log), "", "the write road refuses")
        self.assertEqual(os.listdir(outside), [], "nothing landed in the link's target")
        self.assertTrue(os.path.islink(d), "the link is left in place: it is not this writer's")
        self.assertFalse(os.path.lexists(p), "and nothing was minted through it")
        for root, _dirs, files in os.walk(self.root):
            for f in files:
                self.assertNotIn(val, Path(root, f).read_text(errors="replace"), "the value is in no file under the test root: %s" % f)
        self.assertEqual(len(logged), 1, logged)
        m, problem, kw = logged[0]
        self.assertTrue(problem)
        self.assertIn(str(d), m, "the kernel log line names the directory")
        self.assertIn(os.path.realpath(str(outside)), m, "and where it resolves")
        self.assertIn(os.path.realpath(self.d), m, "and the state root it is outside of")
        self.assertIn("outside the state root", m, "the condition the check refuses, in words")
        self.assertIn("symbolic link", m)
        self.assertNotIn(val, m, "never a value")
        self.assertEqual(kw["ring_text"], sb.FLAG_DIR_LINK_RING % PARENT, "the ring text names no path")
        self.assertNotIn(self.root, kw["ring_text"])
        self.assertIn("resolves outside the state root", kw["ring_text"], "the ring text names the condition too")
        self.assertLessEqual(len(kw["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)
        self.assertEqual(_temps(self.d), [])
        # a directory link whose target is INSIDE the root passes containment: the file stays under the root, where the
        # reference's lister looks (its glob follows a directory link), so the refusal's reason does not apply
        inside = Path(self.d, "inside-dir")
        inside.mkdir()
        os.unlink(d)
        os.symlink(str(inside), str(d))
        del logged[:]
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, log=log), str(p), "a link into the root is written through")
        self.assertEqual(json.loads(Path(inside, PARENT + ".json").read_text())["env"], ENV)
        self.assertEqual(sorted(glob.glob(os.path.join(self.d, sb.FLAG_SETTINGS_DIR, "*.json"))), [str(p)], "and the lister's glob finds it")
        self.assertEqual(logged, [], "no row for a write that stayed under the root")

    def test_a_state_root_that_is_itself_a_symbolic_link_passes_containment(self):
        """The other side of fresh-2's check (round 9 of fork PR #781's review): realpath containment resolves BOTH sides,
        so a state root that is itself a symbolic link, or has one among its parents, passes: the whole root relocates and
        the file lands beside the registry, in the link's target, with no row. Refusing by os.path.islink on the state
        root's path would red this (the ruling named the linked root as the shape that must pass), and a string-prefix
        check in place of commonpath would pass a sibling whose name begins with the root's; both shapes are driven."""
        real = Path(self.root, "real-state")
        os.makedirs(Path(real, sb.FLAG_SETTINGS_DIR))
        linked = Path(self.root, "linked-state")
        os.symlink(str(real), str(linked))
        parent_link = Path(self.root, "linked-parent")
        os.symlink(self.root, str(parent_link))
        logged, log = self._log()
        for state in (linked, Path(parent_link, "real-state")):
            p = sb.flag_settings_path(state, PARENT, env=ENV, log=log)
            self.assertEqual(p, str(Path(state, sb.FLAG_SETTINGS_DIR, PARENT + ".json")), "written, and the in-root path returned: %s" % state)
            self.assertEqual(json.loads(Path(real, sb.FLAG_SETTINGS_DIR, PARENT + ".json").read_text())["env"], ENV, "the file is beside the registry")
            self.assertEqual(logged, [], "no row: the root relocated whole")
            os.unlink(Path(real, sb.FLAG_SETTINGS_DIR, PARENT + ".json"))
        # commonpath, not a prefix: a sibling directory whose name begins with the root's is outside it
        sibling = Path(str(real) + "-sibling")
        os.makedirs(sibling)
        d = Path(real, sb.FLAG_SETTINGS_DIR)
        shutil.rmtree(d)
        os.symlink(str(sibling), str(d))
        self.assertEqual(sb.flag_settings_path(real, PARENT, env=ENV, log=log), "", "the sibling is outside the root")
        self.assertEqual(os.listdir(sibling), [])
        self.assertEqual(len(logged), 1, logged)
        self.assertEqual(logged[0][2]["ring_text"], sb.FLAG_DIR_LINK_RING % PARENT)

    def test_the_write_goes_to_a_fresh_inode_so_a_hard_link_is_never_refreshed(self):
        """correctness-4 / extra8-3 (review round 3 of the env-pick door, 2026-09-19): the link guard sees symbolic
        links only, and the in-place O_CREAT|O_TRUNC write went through the existing inode, so a hard link at the
        path carried every connect's env block, credential value included, to a file under another name. The choice,
        stated in the writer: the bytes go to a FRESH inode renamed over the path, never through the existing one (a
        refusal on the link count was tried by the reviewers and rejected: it stops ordinary connects over a
        snapshot). The other name keeps the OLD bytes, as a copy would, and is never written again."""
        p = Path(self.d, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env={"OLD_FLAG": "x"}), str(p))
        other = Path(self.root, "other-name.json")
        os.link(str(p), str(other))
        self.assertEqual(os.stat(other).st_nlink, 2, "the state under test: one inode, two names")
        before = os.stat(p).st_ino
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV), str(p))
        self.assertNotEqual(os.stat(p).st_ino, before, "a fresh inode: the bytes never went through the existing one")
        self.assertEqual(json.loads(p.read_text())["env"], ENV)
        self.assertEqual(json.loads(other.read_text()), {"env": {"OLD_FLAG": "x"}},
                         "the other name keeps the old bytes and is never refreshed")
        self.assertEqual(os.stat(other).st_nlink, 1)
        self.assertEqual(_temps(self.d), [])

    def test_a_failed_rename_leaves_no_temp_and_the_old_file_whole(self):
        """write_reg's pattern (review round 3, 2026-09-19; kernel-4 and extra8-3): a writer-unique temp (pid and a
        random suffix) renamed into place and unlinked in a finally, so a launch reading at that moment sees the old
        file or the new one, never a torn one, and a rename that fails the way a full disk fails it leaves no temp.
        The row it logs names the path on the kernel log line and no path in the ring text."""
        sb.flag_settings_path(self.d, PARENT, env={"OLD_FLAG": "x"})
        p = Path(self.d, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        seen = []

        def boom(real, src, dst):
            seen.append(os.path.basename(src))
            raise OSError(errno.ENOSPC, "No space left on device")
        _interpose(self, replace=boom)
        logged, log = self._log()
        self.assertEqual(sb.flag_settings_path(self.d, PARENT, env=ENV, fast=True, log=log), "", "degrade to launch")
        self.assertEqual(json.loads(p.read_text()), {"env": {"OLD_FLAG": "x"}}, "the old file stands whole: never a torn one")
        self.assertEqual(_temps(self.d), [], "a failed rename leaves no temp behind")
        self.assertEqual(len(seen), 1)
        self.assertRegex(seen[0], r"^%s\.json\.%d\.[0-9a-f]{8}\.tmp$" % (re.escape(PARENT), os.getpid()),
                         "writer-unique: the pid and a random suffix, write_reg's name")
        self.assertEqual(len(logged), 1, logged)
        m, problem, kw = logged[0]
        self.assertTrue(problem)
        self.assertIn(str(p), m)
        self.assertIn("unwritable", m)
        self.assertIn("launching WITHOUT env, fastMode", m)
        self.assertEqual(kw["ring_text"], sb.FLAG_UNWRITABLE_RING % (PARENT, "OSError", "env, fastMode"))
        self.assertNotIn(self.root, kw["ring_text"], "no path in the short form: a path's length is the state root's")

    def test_the_link_check_and_the_write_run_under_the_flag_settings_lock(self):
        """regression-6 (review round 3 of the env-pick door, 2026-09-19): the module's two statements of its lock
        order say the link check and the write run under _flag_settings_lock, and the round's mutation pass found no
        test reading the lock (the `with` replaced by nothing stayed green). Probed, not named: a stand-in that counts
        its depth replaces the module's lock for the test, and the writer's three moments, the islink check, the
        realpath containment check (round 9 of fork PR #781's review, fresh-2) and the rename, record the depth they
        run at; a `with` that is not there, or one around the write alone, reads zero."""
        seen = {}

        class _Probe:
            depth = 0

            def __enter__(self):
                _Probe.depth += 1

            def __exit__(self, *exc):
                _Probe.depth -= 1

        class _Path:
            def __init__(self, real):
                self._real = real

            def __getattr__(self, name):
                return getattr(self._real, name)

            def islink(self, p):
                seen["islink"] = _Probe.depth
                return self._real.islink(p)

            def realpath(self, p):
                # the SHALLOWEST depth any realpath ran at: the check resolves two paths, and one of them moved out of
                # the lock must read zero here, where the last call's depth would hide it
                seen["realpath"] = min(seen.get("realpath", _Probe.depth), _Probe.depth)
                return self._real.realpath(p)

        class _Os(_OsProxy):
            @property
            def path(self):
                return _Path(self._real.path)

        def _replace(real_os, src, dst):
            seen["replace"] = _Probe.depth
            return real_os.replace(src, dst)

        self.addCleanup(setattr, sb, "_flag_settings_lock", sb._flag_settings_lock)
        sb._flag_settings_lock = _Probe()
        self.addCleanup(setattr, sb, "os", sb.os)
        sb.os = _Os(sb.os, replace=_replace)
        p = sb.flag_settings_path(self.d, PARENT, env=ENV)
        self.assertTrue(p)
        self.assertEqual(seen, {"islink": 1, "realpath": 1, "replace": 1}, "all three moments run inside the lock")
        self.assertEqual(_Probe.depth, 0, "and the lock is released on the way out")
        self.assertEqual(json.loads(Path(p).read_text())["env"], ENV)

    def test_two_connects_for_one_sid_write_in_turn(self):
        """The lock's stated job: a second writer for the same sid waits for the first. A stand-in signals when a
        writer asks for the lock, so the test waits on that signal and never on time; while the first holds it the
        second is alive and has written nothing, and once it is released the second writes."""
        asked = threading.Event()
        inner = threading.RLock()

        class _Gate:
            def __enter__(self):
                asked.set()
                inner.acquire()

            def __exit__(self, *exc):
                inner.release()

        self.addCleanup(setattr, sb, "_flag_settings_lock", sb._flag_settings_lock)
        sb._flag_settings_lock = _Gate()
        path = os.path.join(self.d, sb.FLAG_SETTINGS_DIR, "%s.json" % PARENT)
        out = []
        t = threading.Thread(target=lambda: out.append(sb.flag_settings_path(self.d, PARENT, env=ENV)), daemon=True)
        with inner:                                    # the first connect holds the lock through its write
            t.start()
            while not asked.is_set() and t.is_alive():
                t.join(0.01)
            self.assertTrue(asked.is_set(), "the second writer asks for the module's lock; one that never asked "
                                            "wrote without it: %r" % (out,))
            self.assertTrue(t.is_alive(), "and waits while the first holds it")
            self.assertFalse(os.path.exists(path), "nothing is written while another writer holds the lock")
        t.join(30)
        self.assertFalse(t.is_alive(), "released, the second writer runs")
        self.assertEqual(out, [path])
        self.assertEqual(json.loads(Path(path).read_text())["env"], ENV)

    def test_the_lock_is_re_entrant(self):
        """The lock's comment says it is re-entrant, as round 2 made it (review round 5's mutation pass, 2026-09-19: an
        RLock replaced by a Lock left every suite green; the population of statements is that one clause and the
        assignment, and nothing in tests/, docs/ or the ledger entry repeats it). No path nests the lock at this head,
        since the census (EnvRowsPopulation) holds one `with` and no bare acquire, so the property cannot be shown
        through the writer without a hang under the mutation; it is executed on the lock itself, non-blocking
        throughout: the thread holding it takes it again at once, another thread cannot take it while either hold
        stands, and it is free once both are released. The binding read is the module's, the one the writer's `with`
        resolves at call time."""
        lock = sb._flag_settings_lock
        tried = []

        def other_thread_tries():
            taken = lock.acquire(blocking=False)
            if taken:
                lock.release()
            tried.append(taken)

        def another_thread_can_take_it():
            t = threading.Thread(target=other_thread_tries, daemon=True)
            t.start()
            t.join(30)
            self.assertFalse(t.is_alive(), "the non-blocking try returned")
            return tried.pop()

        self.assertTrue(lock.acquire(blocking=False), "free at the start: the first hold")
        try:
            self.assertTrue(lock.acquire(blocking=False), "re-entrant: the holder takes it again without waiting")
            try:
                self.assertIs(another_thread_can_take_it(), False, "held twice by this thread: another thread cannot take it")
            finally:
                lock.release()
            self.assertIs(another_thread_can_take_it(), False, "one release of two: still held")
        finally:
            lock.release()
        self.assertIs(another_thread_can_take_it(), True, "both released: free for another thread")

    def test_every_writer_rows_worst_case_is_computed_from_its_format_and_fits_the_cap(self):
        """correctness-3 / kernel-2 (review round 3, 2026-09-19): the class, not the instance. Each row's worst case,
        the longest fixed text (the longest sid reason), the sid budget spent (a repr past it is cut with the marker),
        the class budget spent and every flag-settings key riding, is computed HERE from the module's constants and
        asserted under the error centre's cap and whole through the feed's cut; then the real writer is driven over a
        root longer than any home, with every key riding, a sid past the budget and a directory where the file goes,
        to show the constants are what it renders."""
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
        keys = ", ".join(sb.FLAG_SETTINGS_KEYS)
        self.assertEqual(sorted(sb.FLAG_SETTINGS_KEYS), list(sb.FLAG_SETTINGS_KEYS), "sorted, as the writer joins them")
        sid_worst = sb.FLAG_SID_RING % (max(sb.FLAG_SID_REASONS, key=len), "x" * sb.RING_SID_BUDGET, keys)
        link_worst = sb.FLAG_LINK_RING % ("x" * sb.RING_SID_BUDGET)
        dir_link_worst = sb.FLAG_DIR_LINK_RING % ("x" * sb.RING_SID_BUDGET)
        unw_worst = sb.FLAG_UNWRITABLE_RING % ("x" * sb.RING_SID_BUDGET, "x" * sb.RING_CLASS_BUDGET, keys)
        for name, worst in (("sid", sid_worst), ("link", link_worst), ("directory link", dir_link_worst), ("unwritable", unw_worst)):
            self.assertLessEqual(len(worst), sb.ERROR_CENTER_TEXT_CAP, (name, len(worst), worst))
            self.assertEqual(km._sdk_problem_text(worst), worst, "and whole in the feed")
        long_root = os.path.join(self.root, "a" * 120)
        os.makedirs(os.path.join(long_root, sb.FLAG_SETTINGS_DIR))
        p = Path(long_root, sb.FLAG_SETTINGS_DIR, PARENT + ".json")
        p.mkdir()                                                    # the rename over a directory fails
        logged, log = self._log()
        riding = dict(ultracode=True, fast=True, no_helper=True, env=ENV)
        self.assertEqual(sb.flag_settings_path(long_root, PARENT, log=log, **riding), "")
        long_sid = "x" * (sb.RING_SID_BUDGET + 30) + "/y"
        self.assertEqual(sb.flag_settings_path(long_root, long_sid, log=log, **riding), "")
        self.assertEqual(len(logged), 2, logged)
        self.assertIn(str(p), logged[0][0], "the kernel log line names the path")
        self.assertGreater(len(logged[0][0]), sb.ERROR_CENTER_TEXT_CAP, "the whole line would not fit the error centre over this root")
        self.assertEqual(logged[0][2]["ring_text"], sb.FLAG_UNWRITABLE_RING % (PARENT, "IsADirectoryError", keys))
        cut = sb._cred.cut_to(repr(long_sid), sb.RING_SID_BUDGET)
        self.assertTrue(cut.endswith(sb._cred.CUT_MARK) and len(cut) == sb.RING_SID_BUDGET, cut)
        self.assertEqual(logged[1][2]["ring_text"], sb.FLAG_SID_RING % (sb.FLAG_SID_REASONS[2], cut, keys))
        # tests-2 (review round 4, 2026-09-19): the sid cut on the link row and on the unwritable row was pinned by
        # nothing (every rendered assertion used the 36-character PARENT, under the 40 budget, where cut_to is the
        # identity), so both rows are driven with a BARE sid past the budget (a file name under NAME_MAX; the '/y' sid
        # above is refused by the sid gate first and never reaches either road), and the equality is what pins the cut:
        # at 70 characters the uncut unwritable row still fits the cap
        bare = "x" * (sb.RING_SID_BUDGET + 30)
        cut_bare = sb._cred.cut_to(bare, sb.RING_SID_BUDGET)
        self.assertTrue(cut_bare.endswith(sb._cred.CUT_MARK) and len(cut_bare) == sb.RING_SID_BUDGET, cut_bare)
        outside = Path(self.root, "outside.json")
        outside.write_text("{}\n")
        os.symlink(str(outside), os.path.join(long_root, sb.FLAG_SETTINGS_DIR, bare + ".json"))
        self.assertEqual(sb.flag_settings_path(long_root, bare, log=log, **riding), "")
        self.assertEqual(logged[-1][2]["ring_text"], sb.FLAG_LINK_RING % cut_bare, "the link row cuts the sid")
        self.assertIn(bare, logged[-1][0], "and the kernel log line carries it whole")
        bare2 = "y" * (sb.RING_SID_BUDGET + 30)
        Path(long_root, sb.FLAG_SETTINGS_DIR, bare2 + ".json").mkdir()
        self.assertEqual(sb.flag_settings_path(long_root, bare2, log=log, **riding), "")
        self.assertEqual(logged[-1][2]["ring_text"],
                         sb.FLAG_UNWRITABLE_RING % (sb._cred.cut_to(bare2, sb.RING_SID_BUDGET), "IsADirectoryError", keys),
                         "the unwritable row cuts the sid")
        self.assertIn(bare2, logged[-1][0])
        # the class-name cut on the same row: an OSError subclass named past RING_CLASS_BUDGET raised at the rename
        # (every other rendering uses IsADirectoryError or OSError, both under the budget)

        class AnOSErrorSubclassWhoseNameOutrunsTheBudget(OSError):
            pass
        klass = AnOSErrorSubclassWhoseNameOutrunsTheBudget.__name__
        self.assertGreater(len(klass), sb.RING_CLASS_BUDGET)

        def boom(real, src, dst):
            raise AnOSErrorSubclassWhoseNameOutrunsTheBudget(errno.EIO, "boom")
        _interpose(self, replace=boom)
        self.assertEqual(sb.flag_settings_path(long_root, CHILD, log=log, **riding), "")
        cut_class = sb._cred.cut_to(klass, sb.RING_CLASS_BUDGET)
        self.assertTrue(cut_class.endswith(sb._cred.CUT_MARK) and len(cut_class) == sb.RING_CLASS_BUDGET)
        self.assertEqual(logged[-1][2]["ring_text"], sb.FLAG_UNWRITABLE_RING % (CHILD, cut_class, keys), "the class name is cut")
        self.assertIn("boom", logged[-1][0], "the kernel log line carries the error's own text")
        self.assertNotIn(sb._cred.CUT_MARK, logged[-1][0], "and cuts nothing")
        self.assertEqual(len(logged), 5, logged)
        for m, problem, kw in logged:
            self.assertTrue(problem)
            self.assertNotIn(long_root, kw["ring_text"], "no path in the short form")
            self.assertLessEqual(len(kw["ring_text"]), sb.ERROR_CENTER_TEXT_CAP, kw["ring_text"])
            self.assertEqual(km._sdk_problem_text(kw["ring_text"]), kw["ring_text"])
        self.assertEqual(_temps(long_root), [])


class SpawnEnv(_Backend):
    def test_spawn_persists_the_env_in_the_reg(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.assertEqual(self._reg(sid).get("env"), ENV)

    def test_spawn_without_env_writes_no_key(self):
        sid = self.be.spawn("web", "/tmp")
        self.assertNotIn("env", self._reg(sid))

    def test_spawn_refuses_a_bad_payload_loudly(self):
        with self.assertRaises(ValueError):
            self.be.spawn("web", "/tmp", env={"9BAD": "1"})
        with self.assertRaises(ValueError):
            self.be.spawn("web", "/tmp", env={"FEATURE_FLAG": 1})

    def test_spawn_refuses_the_identity_names(self):
        # a reg born with ROMP_SID in its user env would shadow-race the identity at every connect
        with self.assertRaises(ValueError):
            self.be.spawn("web", "/tmp", env={"ROMP_SID": PARENT})
        with self.assertRaises(ValueError):
            self.be.spawn("web", "/tmp", env={"ROMP_SESSION_NAME": "impostor"})


class _OptionsBackend(_Backend):
    """_Backend plus the _options seam: ClaudeAgentOptions is a parameter (a dict stands in) and
    the in-function import only needs HookMatcher — stub the module when the real dependency is
    absent (CI without the venv)."""

    def setUp(self):
        super().setUp()
        import sys
        import types
        self._fake_sdk = "claude_agent_sdk" not in sys.modules and not sb.sdk_importable()
        if self._fake_sdk:
            fake = types.ModuleType("claude_agent_sdk")
            # an attribute-bearing stand-in, like the SDK's dataclass: with hosts on (the default since T348) the
            # options loop sets each matcher's `timeout` to the host's hook bound, which a plain dict refused
            fake.HookMatcher = lambda **kw: types.SimpleNamespace(**kw)
            sys.modules["claude_agent_sdk"] = fake

    def tearDown(self):
        import sys
        if self._fake_sdk:
            sys.modules.pop("claude_agent_sdk", None)
        super().tearDown()

    def _options_kw(self, sess):
        return self.be._options(sess, dict)


class OptionsThreadsEnv(_OptionsBackend):
    """_options → flag_settings_path(env=…): the file the CLI launches with carries the reg's env."""

    def test_the_settings_file_carries_the_regs_env(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        kw = self._options_kw(self._sess(sid))
        self.assertIn("settings", kw)
        self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], ENV)

    def test_no_env_and_no_flags_means_no_settings_file(self):
        sid = self.be.spawn("web", "/tmp")
        kw = self._options_kw(self._sess(sid))
        self.assertNotIn("settings", kw,
                         "the return-\"\"-when-no-keys contract: a plain session launches without "
                         "a flag-settings file at all")

    def test_every_connect_rewrites_the_file_so_reconnects_reassert(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        s = self._sess(sid)
        p = self._options_kw(s)["settings"]
        Path(p).write_text('{"env": {"TAMPERED": "yes"}}')   # drift the file behind romp's back
        p2 = self._options_kw(s)["settings"]
        self.assertEqual(p2, p)
        self.assertEqual(json.loads(Path(p2).read_text())["env"], ENV,
                         "the file is rewritten from the session on EVERY use — a reconnect "
                         "re-asserts the env by construction, never trusts what's on disk")

    def test_a_connect_with_no_keys_leaves_the_file_an_earlier_connect_left(self):
        """The seam's face of the no-keys contract: a session whose pick was cleared (`romp new --no-env`) connects
        with no key riding, so no settings file is handed to the CLI and the file the earlier connect wrote stays as
        it was (docs/reference.md: the registry follows a re-declaration at once, the file only at a connect that
        writes it, and a file nothing rewrites stays). A fact stated, not a promise kept, and pinned so the redaction
        road's removal of that file stays out of this change (review round 3 of the env-pick door, 2026-09-19)."""
        sid = self.be.spawn("web", "/tmp", env=ENV)
        p = self._options_kw(self._sess(sid))["settings"]
        before = Path(p).read_bytes()
        self.assertTrue(self.be.set_env(sid, {}), "the clear is accepted: the registry follows at once")
        self.assertEqual(self._reg(sid).get("env") or {}, {})
        kw = self._options_kw(self._sess(sid))
        self.assertNotIn("settings", kw, "no key rides: the no-keys contract")
        self.assertEqual(Path(p).read_bytes(), before, "the file the earlier connect left stays as it was")

    def test_a_failed_flag_write_degrades_loudly_through_options(self):
        # the connect-time seam: /new already echoed the env as applied, so a write failure here
        # must reach the Log as a problem — the session launching without its env is otherwise
        # invisible to every surface (no readback channel)
        sid = self.be.spawn("web", "/tmp", env=ENV)
        Path(self.be.state_dir, sb.FLAG_SETTINGS_DIR).write_text("not a directory")
        logged = []
        self.be._log = lambda msg, problem=False, **kw: logged.append((msg, problem))
        kw = self._options_kw(self._sess(sid))
        self.assertNotIn("settings", kw, "degrade to launch, never abort the connect")
        self.assertTrue(any(problem and "env" in msg for msg, problem in logged),
                        "the drop must land in the Log as a problem naming env: %r" % (logged,))


class EnvRowsPopulation(unittest.TestCase):
    """The problem rows about a per-session env or its flag-settings file are a DERIVED population (review round 4 of
    the env-pick door, 2026-09-19: the round-3 comment claimed every such row carried a bounded ring text while two rows
    carried none), and the derivation is keyed on the problem RING (review round 6, 2026-09-19: round 5 found the walk
    over calls NAMED _log or log with an env head narrower than the universal it enforced, four ways: problem_row was a
    third door it never read, kernel.py names no call _log so its negative half passed by construction, a message it
    could not reduce fell out of both assertions, and the head filter stood in for a rule). tests/env_ring_census.py
    enumerates every door by resolution and derives the content rows by taint; this class holds the module to it: the
    ENV ROWS line is the derivation, every value-tainted door call declares problem=, an unreduced message is named and
    never dropped, the negative half finds the kernel's doors before it asserts them clean, the counts equal their committed tables,
    and the parameter-indirection road is exercised on planted modules beside the small module (SMALL_SDK_BACKEND; since
    round 8 of the review, the mechanics pins' input, its block comment deriving what a plant needs beside it), one the
    walk follows and one it cannot, which must fail loudly. Fork PR #792's POOL SITES line and its pin in
    tests/test_perf_stats.py are the precedent."""

    @classmethod
    def setUpClass(cls):
        cls.c = census(CENSUS_FILES)

    def _assert_pin(self, c, expected=None):
        """The pin's first assertions, shared with the planted-module tests: a failure of the derivation itself refuses
        before anything is compared, and the content rows are `expected`'s, by identity: the tree's ROWS by default (eleven
        at round 7's head, nine at round 6, twelve since the round-8 merge of main, thirteen since round 9's closing
        commit), or what a plant arm expects, the control
        census's identities plus the planted row (round 9 of the review, tests-2: the arms had asserted that this pin REFUSES
        a planted census over the small module, which it did for any census there, plant or no plant, since no small-module
        census equals the tree's ROWS; now the ONE identity equality is executed by the population pin and by every arm,
        which takes the plant as the added row under the control's identities plus it and refuses it under the control's
        alone, so weakening the equality to a membership or subset test reds the arms)."""
        expected = ROWS if expected is None else list(expected)
        self.assertEqual(c.failures, [], "the derivation failed (a door value the walk could not follow, or a writer it "
                         "could not resolve): %r" % (c.failures,))
        self.assertEqual((c.writer.qual, c.door, c.msg_param), ("SdkBackend._log", "_log", "m"), "the one appender to self._problems")
        self.assertEqual(c.content_identities(), expected,
                         "the content rows (env-tainted, problem=True) by identity; the census found %d at lines %s. A new row "
                         "needs a module-level format for its ring_text, a worst case in CredentialShapedNamesEndToEnd's table, "
                         "and the ENV ROWS line re-derived" % (len(c.content_rows), c.sites(c.content_rows)))

    def test_the_census_keys_on_the_ring_and_the_env_rows_line_is_its_content_rows(self):
        c = self.c
        self._assert_pin(c)
        src = Path(SDK_BACKEND).read_text(encoding="utf-8")
        written = [ln for ln in src.splitlines() if ln.startswith("# ENV ROWS: ")]
        self.assertEqual(len(written), 1, "exactly one ENV ROWS line in kernel/sdk_backend.py: %r" % (written,))
        self.assertEqual(written[0], c.content_rows_line(), "kernel/sdk_backend.py's ENV ROWS line is the census's derivation")
        for dc in c.content_rows:
            self.assertEqual(dc.base, "sdk_backend.py")
            self.assertEqual(dc.problem_decl, ("const", True))
            self.assertIn("env", dc.taint)
            self.assertEqual(len(dc.ring_formats), 1, "one format per row, resolved from its ring_text: line %d in %s: %r" % (dc.lineno, dc.owner, dc.ring_formats))
            fmt = getattr(sb, dc.ring_formats[0])
            self.assertIsInstance(fmt, str, "%s names a module-level string format" % dc.ring_formats[0])
            self.assertNotIn("\u2014", fmt)
            self.assertTrue(dc.heads and all(fmt.startswith(h.split("%")[0]) for h in dc.heads),
                            "the ring text opens with the row's own head, the log line's literal text up to its first placeholder: "
                            "line %d, %r vs %r" % (dc.lineno, fmt, dc.heads))
        self.assertEqual(sorted({h.split(" (")[0].split(":")[0].split(" %")[0] for dc in c.content_rows for h in dc.heads}),
                         ["env", "flag settings", "the session host for"],
                         "the content rows' heads: the env pick's, the flag-settings file's, and since the merge of main the refused "
                         "launch's (the post-merge census: content heads first words = ['env', 'flag settings', 'the session host for'])")
        self.assertIn("SdkBackend._log, problem=True", Path(KERNEL_PY).read_text(encoding="utf-8"),
                      "the kernel names the backend ring as where its problem rows come from")

    def test_every_value_tainted_door_call_declares_problem_explicitly(self):
        """Rule (2) of the ring census (review round 6 of the env-pick door, 2026-09-19; the problem= class of round 5:
        correctness-1, tests-1, regression-4). _log classifies a line left without problem= by the LIVE exception,
        while the population decides lexically, so a line whose text carries a per-session env value or names a pending
        pick must declare its classification: False for a routine line, or True with a ring text that reduces to one
        module-level format (an existence-only row, tainted through the surface set alone, owes the constant and no
        format: a surface name adds a fixed word). Red on 5d5507ee3 at twelve lines: _log_quietly's conduit and its
        six pick-naming callers, the mode landing's two routine lines, set_mode's line, the thinking override note and
        set_env's success line; closed by problem=False inside _log_quietly and on the five lines. The round-6 addendum
        widened the taint (in-place adds, augmented assignment, attribute stores, module names, a re-keyed dict) and
        found three more: the host-start notice (its pid derives from a process spawned with the launch's
        credential-shaped names) and set_mode's two withdrawal lines, which name a pending pick; declared False. The
        post-merge census (2026-09-20): main's two refused-launch rows in _host_transport_for reached the ring through
        problem_row's log= with the whole reason as the ring text, tainted through the host process, and were four
        violations (each site through problem_row's plainer-callable fallback, which declares nothing, and problem_row's
        two inner calls); closed by the sites taking problem_row's ledger row and returned line without log= and filing
        their own row, problem=True with HOST_REFUSED_RING, and by the census judging a conduit's inner calls at their
        sites (rule 3). The Counter is unchanged by that: the two rows are 'self' calls declared True, and the
        re-derivation gives _host_transport_for: 2 (the host-start notice and the credential-names notice), as before. The
        round-8 merge of main (fork PR #814, 2026-09-21) brought a third row of the class, _refused_directory_row's
        directory-refused row through problem_row's log=, one violation (no explicit problem=) and one UNBOUNDED content
        row; closed the same way inside the merge, and the Counter is unchanged by it too."""
        c = self.c
        self.assertEqual([(dc.base, dc.lineno, dc.owner, why) for dc, why in c.explicit_violations], [],
                         "value-tainted door calls without an explicit constant problem= (or a content row with no single format)")
        declared_false = collections.Counter(dc.owner for dc in c.tainted if dc.problem_decl == ("const", False))
        self.assertEqual(declared_false, collections.Counter({
            "_log_quietly": 1, "_served_by_connect": 1, "_arm_reconnect_if_quiet": 3, "_note_work_ended": 1, "_settle_withdrawal": 1,
            "_reset_reconnect_state": 1, "_do_set_mode": 4, "set_mode": 3, "_options": 1, "set_env": 1,
            "_note_env_credential_names": 1, "_host_transport_for": 2, "_can_use_tool": 1}),
            "the routine lines declared problem=False by writing function: round 6's twelve (the conduit's own call, its six "
            "callers, two landing lines, set_mode, the thinking note, set_env's success line), the landing's two earlier "
            "declarations, the two boot-time notices, and the addendum's three (the host-start notice, set_mode's two "
            "withdrawal lines) plus the bypass-consult line the widened taint reaches through the conduit")

    def test_an_unreduced_door_call_is_named_never_dropped(self):
        """Rule (3): a door call whose message the walk cannot reduce to a literal head stays in the population (taint
        decides, not reduction) and is held here by identity, so a new one reds until it is reduced or named with its
        reason. One at this head: _lease_problem's problem_row call, whose prose is the host's own problem text, run-time
        data with no head to read. The four the round named reduce: problem_row's two inner calls through its
        door-passing sites (thirteen in sdk_backend.py since the round-8 merge of main, fourteen with kernel.py's one through
        getattr, as COUNTS's door-value entry counts them: the two refused-launch sites and the directory-refused row's
        pass no log= and are no sites of it),
        _log_quietly's through its callers, and the crash line, an f-string. The refused-launch rows' message is
        problem_row's RETURNED line, which the census reads as the caller's prose through the returned parameter (rule 7,
        the post-merge census): both rows reduce to their head and neither joins this set."""
        c = self.c
        self.assertEqual(sorted((dc.base, dc.owner, dc.kind) for dc in c.unreduced), [("sdk_backend.py", "_lease_problem", "conduit:problem_row")])
        host = [dc for dc in c.content_rows if dc.owner == "_host_transport_for"]
        self.assertEqual([(dc.kind, dc.heads, dc.unreduced) for dc in host], [("self", ["the session host for %s %s"], False)] * 2,
                         "the refused-launch rows' message is problem_row's returned line, read as the caller's prose")
        directory = [dc for dc in c.content_rows if dc.owner == "_refused_directory_row"]
        self.assertEqual([(dc.kind, dc.heads, dc.unreduced) for dc in directory], [("self", ["the session host for %s %s"], False)],
                         "the directory-refused row's message is problem_row's returned line too (the round-8 merge of main)")
        self.assertEqual([dc.lineno for dc in c.unreduced if dc.taint], [], "an unreduced call carries no env taint")
        inner = {(dc.owner, dc.kind): dc.heads for dc in c.door_calls if dc.owner in ("problem_row", "_log_quietly") and dc.kind in ("param", "typed")}
        self.assertEqual(sorted(inner), [("_log_quietly", "typed"), ("problem_row", "param")])
        for k, heads in inner.items():
            self.assertTrue(heads and all(heads), (k, heads))
        fstrings = [dc for dc in c.door_calls if isinstance(dc.message, ast.JoinedStr)]
        self.assertTrue(fstrings and all(dc.heads for dc in fstrings), "an f-string message reduces to its leading text: %r"
                        % [(dc.lineno, dc.heads) for dc in fstrings])
        self.assertIn("sdk session ", {h for dc in fstrings for h in dc.heads}, "the crash line is one of them")

    def test_existence_only_lines_declare_a_constant_and_are_outside_the_population(self):
        """The one sentence beside the content rows, pinned: lines tainted through the pending-pick surface set alone (the
        reconnect heading's, the mode landing's) name a pick's existence in a fixed vocabulary plus the session name,
        never a value; every one declares a constant, none is a content row, and the ones filed problem=True are the
        landing's three failure reports (the mode-truth tests own those) and, since the merge of main, the conduit's
        problem road. 18 at the round-6 addendum: round 6's 15, set_mode's two withdrawal lines and the bypass-consult
        line, reached once the taint followed attribute stores (the mode the landing stores is derived from the surface
        set); 20 at the merge (main's relaunch-slot line and the conduit's second call). The vocabulary gains "live work"
        at the merge, and this is why: main's live-work reconcile (its fork PR #787) sends its lines through the conduit, and
        the conduit's own two calls carry the UNION of every caller's heads (26 heads each at the merged head, first
        words {'live work', 'permission consult', 'reconnect'}), so "live work" is a head of the conduit's two rows even
        though no live-work site is itself pick-tainted (none is in the census's tainted set; the heads are read off the
        conduit's rows). Re-derived at the follow-up commit: existence vocabulary = ['live work', 'mode', 'permission
        consult', 'reconnect', 'set_permission_mode']; filed True = the three _do_set_mode reports and ('_log_quietly',
        'live work (%s): %d background task%s'), the conduit's problem road (ruling 2 of the post-merge census)."""
        c = self.c
        ex = c.existence_rows
        self.assertEqual(len(ex), EXISTENCE_ROWS, "the existence rows at round 8's commit, unchanged at the round-8 merge of main (%d): "
                         "fewer is a blind walk, more is growth "
                         "nobody re-derived; re-derive EXISTENCE_ROWS deliberately and name the head" % EXISTENCE_ROWS)
        for dc in ex:
            self.assertEqual(dc.taint, frozenset({"pick"}), (dc.lineno, dc.taint))
            self.assertEqual(dc.problem_decl[0], "const", (dc.lineno, dc.problem_decl))
        self.assertEqual(sorted({h.split(" (")[0] for dc in ex for h in dc.heads}),
                         ["live work", "mode", "permission consult", "reconnect", "set_permission_mode"])
        conduit_rows = [dc for dc in ex if dc.owner == "_log_quietly"]
        self.assertEqual(len(conduit_rows), 2, "the conduit's two calls, a road each")
        self.assertTrue(all("live work" in {h.split(" (")[0] for h in dc.heads} for dc in conduit_rows), "the live-work head rides the conduit's rows")
        self.assertEqual([dc.lineno for dc in ex if dc.owner not in ("_log_quietly",) and any(h.startswith("live work") for h in dc.heads)], [],
                         "no live-work site is itself pick-tainted: the head is the union's")
        self.assertFalse(set(ex) & set(c.content_rows))
        filed = sorted((dc.owner, dc.heads[0][:36]) for dc in ex if dc.problem_decl == ("const", True))
        self.assertEqual(filed, [("_do_set_mode", "mode (%s): the landed process runs %"), ("_do_set_mode", "mode (%s): the landed process runs %"),
                                 ("_do_set_mode", "set_permission_mode (%s -> %s) refus"), ("_log_quietly", "live work (%s): %d background task%s")])

    def test_the_negative_half_finds_the_kernels_doors_before_asserting_none_carries_env_taint(self):
        """Round 5's regression-1: the earlier negative half passed because kernel.py contains no call named _log. The
        census finds the kernel's real doors first (the eight _sdk_problem sites, the two _note_ws_drop sites, the
        problem_row call in _spend_guard_row with log=getattr(be, "_log", None) and its own two callers), and only then
        asserts that none carries env taint; credentials.py has no door, and the census shows it read the file by
        finding its twelve source definitions."""
        c = self.c
        kernel = [dc for dc in c.door_calls if dc.base == "kernel.py"]
        kinds = collections.Counter(dc.kind for dc in kernel)
        self.assertEqual(kinds, collections.Counter({"conduit:_sdk_problem": 8, "feeder:_note_ws_drop": 2, "conduit:problem_row": 1,
                                                     "conduit:_spend_guard_row": 2, "feeder-append:_SDK_BOOT_PROBLEMS": 1,
                                                     "feeder-append:_WS_DROPS": 1}), "the kernel's doors, found")
        self.assertEqual(sorted(fn.name for fn, _call, _lst in c.feeder_appends), ["_note_ws_drop", "_sdk_problem"])
        self.assertEqual(sorted(name for _k, name, _ln in c.merge_reads), ["_SDK_BOOT_PROBLEMS", "_WS_DROPS", "problems"])
        self.assertEqual([("kernel.py", 1, "parameter log of problem_row")[2]], [how for b, _ln, how, _f in c.door_value_sites if b == "kernel.py"])
        self.assertEqual([(dc.lineno, dc.owner, sorted(dc.taint)) for dc in kernel if dc.taint], [], "no kernel door carries env taint")
        cred = c.mods["credentials.py"]
        self.assertEqual([dc.lineno for dc in c.door_calls if dc.base == "credentials.py"], [])
        self.assertEqual([s for s in c.door_value_sites if s[0] == "credentials.py"], [])
        defined = sorted(n for (b, n) in list(DEFAULT_SOURCES["name"]) + list(DEFAULT_SOURCES["func"])
                         if b == "credentials.py" and (n in cred.top_defs or n in cred.top_assigns))
        self.assertEqual(len(defined), 12, defined)
        self.assertEqual(len(cred.fns), CREDENTIALS_FNS, "every def and lambda of credentials.py at round 8's commit and at the round-8 "
                         "merge of main; a different count "
                         "is a file the walk did not read whole, or growth to re-derive deliberately")

    def test_problem_rows_sites_are_its_log_passing_calls_and_the_three_without_log_are_sites_of_neither_count(self):
        """extra10-1 (round 9 of the review): the COUNTS block's derivation comment for problem_row_sites said the three
        problem_row calls that pass no log= were sites of it and not door-as-argument sites, when the census counts them in
        NEITHER entry (a log=None binding files nothing through the conduit and is no site of it); the round-8 re-derivation
        moved the number from 12 to 14 and carried the clause forward, widened from two sites to three, after round 7's
        refuter had named it wrong. The prose explaining a derived figure is part of the derivation, so it is held to the
        census here BY EXECUTION: every problem_row call in the three files by AST (a bare or attribute call by that name, or
        `getattr(x, "problem_row")(...)`), split by whether it passes log=; the conduit's sites are exactly the log=-passing
        calls, the door-value entry credits problem_row with exactly them (by the log= keyword's own line), the calls without
        log= are in neither table; then the comment's arithmetic (the total, the log=-passing count, the count without and
        its split by file, and the word neither) is read off the block and held to the figures derived here, never spelled."""
        c = self.c
        calls = []      # (base, the call's line, the log= keyword value's line or None)
        for path in CENSUS_FILES:
            mod = c.mods[os.path.realpath(path)]
            for node in ast.walk(mod.tree):
                if not isinstance(node, ast.Call):
                    continue
                f = node.func
                named = ((isinstance(f, ast.Name) and f.id == "problem_row") or (isinstance(f, ast.Attribute) and f.attr == "problem_row")
                         or (isinstance(f, ast.Call) and isinstance(f.func, ast.Name) and f.func.id == "getattr" and len(f.args) > 1
                             and isinstance(f.args[1], ast.Constant) and f.args[1].value == "problem_row"))
                if not named:
                    continue
                log = [kw for kw in node.keywords if kw.arg == "log" and not (isinstance(kw.value, ast.Constant) and kw.value.value is None)]
                calls.append((mod.base, node.lineno, log[0].value.lineno if log else None))
        with_log = [(b, ln, kl) for b, ln, kl in calls if kl is not None]
        without = [(b, ln) for b, ln, kl in calls if kl is None]
        per_file = collections.Counter(b for b, _ln, _kl in with_log)
        self.assertEqual((len(calls), len(with_log), len(without)), (17, 14, 3), "17 problem_row calls, 14 passing log=, 3 not: %r" % (calls,))
        self.assertEqual(per_file, {"sdk_backend.py": 13, "kernel.py": 1})
        self.assertEqual({b for b, _ln in without}, {"sdk_backend.py"}, "the three without log= are sdk_backend.py's: %r" % (without,))
        sites = sorted((dc.base, dc.lineno) for dc in c.conduit_calls if dc.kind == "conduit:problem_row")
        self.assertEqual(sites, sorted((b, ln) for b, ln, _kl in with_log), "the conduit's sites are exactly the log=-passing calls")
        self.assertEqual(len(sites), c.counts["conduit_sites"]["conduit:problem_row"])
        self.assertEqual(len(sites), COUNTS["problem_row_sites"])
        door_value = sorted((b, ln) for b, ln, how, _f in c.door_value_sites if how == "parameter log of problem_row")
        self.assertEqual(door_value, sorted((b, kl) for b, _ln, kl in with_log),
                         "the door-value entry credits problem_row with the same 14 calls, by the log= keyword's line")
        for b, ln in without:
            self.assertNotIn((b, ln), sites, "a call without log= is no site of the conduit")
            self.assertNotIn((b, ln), door_value, "and no door-as-argument site")
        src = Path(__file__).read_text(encoding="utf-8").splitlines()
        i = next(k for k, ln in enumerate(src) if ln.startswith('    "problem_row_sites": '))
        block = [src[i]]
        for ln in src[i + 1:]:
            if not ln.startswith("    #"):
                break
            block.append(ln)
        text = " ".join(ln.split("#", 1)[1].strip() for ln in block)
        numbers = {int(n) for n in re.findall(r"\b\d+\b", text)}
        self.assertLessEqual({len(calls), len(with_log), len(without)} | set(per_file.values()), numbers,
                             "the comment states the arithmetic the census derives: %r" % text)
        self.assertIn("neither", text.lower(), "the comment says the three are sites of NEITHER count: %r" % text)
        self.assertNotIn("sites of it and", text, "the round-7 clause (sites of it and not door-as-argument sites) is gone")

    def test_the_doors_handle_names_are_derived_from_the_writer_and_the_parameters_a_door_is_passed_under(self):
        """fresh-1 (round 9 of the review): the census's COMMON_METHODS filter (an attribute call on an untyped receiver whose
        name is a stdlib method's resolves to no callee) exempts the door's HANDLE names, derived per census from the trees
        (Census.door_names: the writer's bare name and every parameter name a door expression is passed under by keyword),
        where round 8 rescued one spelling by name (`COMMON_METHODS.discard("_log")`) and left `log`, the parameter road's
        own handle and a logging.Logger method too, filtered. At this head the handles are the writer's name and the one
        parameter name every door pass uses; both are stdlib method names, which is what the rescue is for; no conduit or
        feeder of the tree collides, so the loud failure (conduit-name-common, planted in EnvRowsCensusBlindSpots) has no
        row here. A third handle is growth to re-derive deliberately."""
        c = self.c
        self.assertEqual(sorted(c.door_names), ["_log", "log"], "the writer's name and the door-bound parameter name")
        self.assertEqual(sorted(erc.COMMON_METHODS & set(c.door_names)), ["_log", "log"],
                         "both handles are stdlib method names (logging.Logger's): without the exemption an untyped receiver's call resolves to nothing")
        self.assertEqual({how.split(" ")[1] for _b, _ln, how, _f in c.door_value_sites if how.startswith("parameter ")}, {"log"},
                         "every parameter a door is passed under at this head is spelled log")
        self.assertEqual([f for f in c.failures if f[0] == "conduit-name-common"], [], "no conduit or feeder of the tree collides")
        names = sorted({fn.name for fn in list(c.conduits) + list(c.feeders)})
        self.assertEqual([n for n in names if n in erc.COMMON_METHODS], [], "none of their bare names is a stdlib method name: %r" % (names,))

    def test_the_derivation_equals_its_committed_tables(self):
        """The census's counts EQUAL the tables committed at the round-8 merge of main (COUNTS, CALLS_BY_KIND). Fewer is a blind
        walk; more is growth nobody has re-derived; either reds, and the author re-derives the tables deliberately, naming
        the head. The floors this replaces were blind by construction: at round 7's head a walk with one param-kind door
        call removed passed every floor (the reviewer's round 7, extra8-1), and the same blinding reds this equality on
        three entries (param, calls_reaching_writer, doors), pasted in round 8's commit message."""
        c = self.c
        self.assertEqual(_table_mismatches(c.counts, c.by_kind), [],
                         "the census disagrees with the committed tables: (entry, found, committed at the round-8 merge of main); fewer is a blind "
                         "walk, more is growth nobody re-derived: re-derive COUNTS and CALLS_BY_KIND deliberately and name the head")
        self.assertEqual(sum(c.by_kind.values()), c.counts["calls_reaching_writer"])

    def test_a_table_entry_fires_alone_one_below_and_one_above_and_at_the_table_none_does(self):
        """The round-6 mutation pass left CALLS_BY_KIND's per-kind floors unshown: dropping one self._log call lowered
        `self` to 182 and the doors floor fired first. The mismatch list names every entry that differs, so a per-kind
        difference is named on its own, and since round 8 in BOTH directions; the boundary cases on a stand-in: at the
        table nothing fires, one below an entry the entry alone, one above it the entry alone (the growth a floor let
        pass), and the doors total one below or one above fires alone too."""
        c = self.c
        at_table = dict(c.by_kind)
        for kind, n in CALLS_BY_KIND.items():
            at_table[kind] = n
        counts = dict(c.counts)
        counts["calls_reaching_writer"] = sum(at_table.values())
        for k in ("doors", "log_param_fns", "door_value_sites", "feeder_appends", "merge_reads", "content_rows", "functions"):
            counts[k] = COUNTS[k]
        self.assertEqual(_table_mismatches(counts, at_table), [], "at the table exactly, nothing fires")
        for kind, n in CALLS_BY_KIND.items():
            for delta in (-1, 1):
                with self.subTest(kind=kind, delta=delta):
                    moved = dict(at_table)
                    moved[kind] = n + delta
                    self.assertEqual(_table_mismatches(counts, moved), [(kind, n + delta, n)], "the kind's entry fires alone, either way")
        for delta in (-1, 1):
            with self.subTest(entry="doors", delta=delta):
                moved = dict(counts)
                moved["doors"] = COUNTS["doors"] + delta
                self.assertEqual(_table_mismatches(moved, at_table), [("doors", COUNTS["doors"] + delta, COUNTS["doors"])])

    def test_the_kernel_adds_no_content_row_so_a_module_copy_is_read_with_credentials_alone(self):
        """The pair, kernel/sdk_backend.py with kernel/credentials.py, is the tree three population pins read through the
        door in place of the three files (a second under a second, against five with kernel.py): the conduit roster's
        own-roster read, the fixpoint pin's real-pair arm and the immutability pin; until round 8's small-input commit the
        planted-module and module-copy tests ran over it too. This holds that the shortcut loses no content row: the
        kernel taints set_env's parameter, and its rows are tainted by the door's own reads too."""
        self.assertEqual(census((SDK_BACKEND, CREDENTIALS_PY)).content_identities(), self.c.content_identities())

    PLANT = (
        "FMT = 'env (%s): planted %s'\n"
        "def planted(sess, log=None):\n"
        "    log('env (%s): planted %s' % (sess.name, ', '.join(sorted(sess.env_vars)))@DECL@)\n"
        "def caller(be, sess):\n"
        "    planted(sess, log=getattr(be, '_log', None))\n"
    )

    def _plant(self, name, src):
        path = os.path.join(tempfile.mkdtemp(), name)
        Path(path).write_text(src, encoding="utf-8")
        return path

    def test_a_door_planted_behind_a_parameter_indirection_is_found_and_reds_without_problem(self):
        """Rule (6): a synthetic module plants a door behind a parameter (a function taking log= and calling it with an
        env-tainted message, invoked with log=be._log through getattr), beside the small module. The walk finds it as a
        content row (the only one over the small module, and one ROWS does not name, so the identity pin reds), finds the
        door value at the call site, and reds rule (2) when the planted call lacks problem=; a planted message with no
        literal head lands in the unreduced set."""
        declared = ", problem=True, ring_text=FMT % (sess.name[:20], len(sess.env_vars))"
        small = small_module_files()
        c = Census(small + (self._plant("plant.py", self.PLANT.replace("@DECL@", declared)),), DEFAULT_SOURCES)
        self.assertEqual(c.failures, [])
        self.assertEqual(c.content_identities(), [("planted", "FMT", False)], "the plant's row is the only content row over the small module")
        found = [dc for dc in c.door_calls if dc.base == "plant.py"]
        self.assertEqual([(dc.lineno, dc.kind, dc.owner, sorted(dc.taint), dc.heads) for dc in found],
                         [(3, "param", "planted", ["env"], ["env (%s): planted %s"])])
        self.assertIn(("plant.py", 5, "parameter log of planted"), [(b, ln, how) for b, ln, how, _f in c.door_value_sites])
        self._assert_pin(c, expected=[("planted", "FMT", False)])       # the plant is the one content row, and the pin takes it as such
        with self.assertRaises(AssertionError) as cm:
            self._assert_pin(c, expected=[])                              # under the control's expectation (the small module: no row) it refuses the plant by name
        self.assertIn("planted", str(cm.exception))
        c2 = Census(small + (self._plant("plant.py", self.PLANT.replace("@DECL@", "")),), DEFAULT_SOURCES)
        self.assertEqual([(dc.base, dc.lineno, why) for dc, why in c2.explicit_violations if dc.base == "plant.py"],
                         [("plant.py", 3, "no explicit problem=")])
        self.assertNotIn("planted", [o for o, _f, _k in c2.content_identities()], "without problem=True it is no content row: rule (2) is what catches it")
        c3 = Census(small + (self._plant("plant.py", self.PLANT.replace("@DECL@", declared)
                                         + "def noisy(be, e):\n    be._log(str(e))\n"),), DEFAULT_SOURCES)
        self.assertIn(("plant.py", 7, "noisy", "typed"), [(dc.base, dc.lineno, dc.owner, dc.kind) for dc in c3.unreduced])

    CONDUIT_PLANT = (
        "FMT = 'env (%s): planted %s'\n"
        "def relay(prose, log=None, ring=True):\n"
        "    line = prose + ' ;; tail'\n"
        "    if log is not None:\n"
        "        try:\n"
        "            log(line, problem=bool(ring), ring_text=str(prose))\n"
        "        except TypeError:\n"
        "            log(line)\n"
        "    return line\n"
        "def through(be, sess):\n"
        "    relay('env (%s): planted %s' % (sess.name, ', '.join(sorted(sess.env_vars))), log=be._log)\n"
        "def beside(be, sess):\n"
        "    line = relay('env (%s): planted %s' % (sess.name, ', '.join(sorted(sess.env_vars))))\n"
        "    be._log(line, problem=True, ring_text=FMT % (sess.name[:20], len(sess.env_vars)))\n"
    )

    def test_a_conduit_that_keeps_an_undeclared_fallback_carries_no_tainted_row_and_a_site_binding_no_door_files_beside_it(self):
        """The post-merge census (2026-09-20), on a synthetic problem_row: `relay` is a conduit whose door is its log=
        parameter, forwarding problem=bool(ring) (the site's own ring=, True by default, the way problem_row forwards it)
        and keeping a plainer-callable fallback `log(line)` that declares nothing.
        `through` passes a door and a tainted prose: the site is a rule-(2) violation ("no explicit problem="; the
        fallback is one of the roads it files through) and its ring text is the prose, UNBOUNDED, whatever the site
        says. `beside` binds no door (log= left at its None default): it is NO site of the conduit, takes the returned
        line, and files its own row with a module-level format, which the census reads as a content row whose message
        reduces to the prose through the RETURNED parameter (rule 7), so it is not unreduced. The conduit's own inner
        calls are tainted (the prose reaches them from `through`) and are judged at that site, not on their own row
        (rule 3): the plant's violations are `through`'s one. Both planted rows are content rows (declared True and
        env-tainted; `through`'s identity names its UNBOUNDED format, the shape main's two rows had at the merged head),
        so the identity pin reds, naming both."""
        src = self.CONDUIT_PLANT
        c = Census(small_module_files() + (self._plant("plant3.py", src),), DEFAULT_SOURCES)
        self.assertEqual(c.failures, [])
        line_of = lambda needle: next(i + 1 for i, ln in enumerate(src.splitlines()) if needle in ln)
        planted = sorted(((dc.lineno, dc.owner, dc.kind) for dc in c.door_calls if dc.base == "plant3.py"))
        self.assertEqual(planted, [(line_of("log(line, problem=bool(ring)"), "relay", "param"), (line_of("            log(line)"), "relay", "param"),
                                   (line_of("log=be._log"), "through", "conduit:relay"), (line_of("be._log(line, problem=True"), "beside", "typed")],
                         "the two inner calls, the door-passing site, and beside's own call; beside's relay call is no site")
        self.assertEqual([(dc.lineno, why) for dc, why in c.explicit_violations if dc.base == "plant3.py"],
                         [(line_of("log=be._log"), "no explicit problem=")], "the door-passing tainted site, through the fallback; the inner calls are judged there")
        through = next(dc for dc in c.door_calls if dc.base == "plant3.py" and dc.owner == "through")
        self.assertEqual((sorted(through.taint), through.problem_decl, through.ring_formats), (["env"], ("const", True), ["UNBOUNDED:env (%s): planted %s"]))
        inner = [dc for dc in c.door_calls if dc.base == "plant3.py" and dc.owner == "relay"]
        self.assertEqual([sorted(dc.taint) for dc in inner], [["env"], ["env"]], "the inner calls carry the site's taint")
        beside = next(dc for dc in c.door_calls if dc.base == "plant3.py" and dc.owner == "beside")
        self.assertEqual((sorted(beside.taint), beside.problem_decl, beside.ring_formats, beside.heads, beside.unreduced),
                         (["env"], ("const", True), ["FMT"], ["env (%s): planted %s"], False))
        self.assertIn(("beside", "FMT", False), c.content_identities())
        self.assertIn(("through", "UNBOUNDED:env (%s): planted %s", False), c.content_identities(),
                      "the unbounded site is a content row too (declared True, env-tainted), its identity naming the UNBOUNDED format, "
                      "as main's two rows did at the merged head; the violation is what says it is not bounded")
        self.assertEqual(c.content_identities(), [("through", "UNBOUNDED:env (%s): planted %s", False), ("beside", "FMT", False)],
                         "the two planted rows, in line order, are the only content rows over the small module")
        self._assert_pin(c, expected=[("through", "UNBOUNDED:env (%s): planted %s", False), ("beside", "FMT", False)])   # taken as the two added rows
        with self.assertRaises(AssertionError) as cm:
            self._assert_pin(c, expected=[])
        self.assertIn("through", str(cm.exception), "the identity pin reds, naming the first differing row (unittest elides the rest)")

    def test_a_door_whose_binding_the_walk_cannot_follow_fails_loudly(self):
        """The second plant: the door reaches the planted function through a helper's RETURN (`log=pick(be)` with
        `pick` returning be._log), a binding the walk does not follow. The planted call is then NOT found, so a silent
        pass here would be the round-5 defect again; instead the door value's escape is a failure named by site, and
        the pin's first assertion refuses on it."""
        src = ("def pick(be):\n    return be._log\n"
               "def planted(sess, log=None):\n    log('env (%s): planted %s' % (sess.name, ', '.join(sess.env_vars)))\n"
               "def caller(be, sess):\n    planted(sess, log=pick(be))\n")
        c = Census(small_module_files() + (self._plant("plant2.py", src),), DEFAULT_SOURCES)
        self.assertEqual([(k, b, ln) for k, b, ln, _t in c.failures], [("door-escapes", "plant2.py", 2)])
        self.assertIn("through its return", c.failures[0][3])
        self.assertEqual([dc.lineno for dc in c.door_calls if dc.base == "plant2.py"], [], "the planted call is invisible to the walk, which is why the escape must be loud")
        self.assertEqual([dc for dc, _w in c.explicit_violations if dc.base == "plant2.py"], [])
        with self.assertRaises(AssertionError) as cm:
            self._assert_pin(c)
        self.assertIn("plant2.py", str(cm.exception))

    def test_the_writer_its_caller_and_the_locks_taker_sit_outside_every_lexical_with_over_a_lock(self):
        """The caller-side half of _flag_settings_lock's order sentence (correctness-3, tests-4, regression-2; review round 4,
        2026-09-19): the runtime probe (FlagSettingsLockOrder) reads the locks held when the writer takes its lock inside
        the real _options, and cannot see what _options' own caller holds, so that half is a census. Exactly one call
        site of flag_settings_path (in _options), one of _options (in _amain) and one `with _flag_settings_lock`
        (in flag_settings_path), and none of the three sits lexically inside a `with` over a lock (any context naming
        one: self._lock, _reg_lock, a session's _lock or _persist_lock, a module-level lock). A new caller, or one of
        these wrapped in a lock, reds here; wrapping the _options call in _amain is the mutation the refuter showed
        the runtime probe alone cannot catch."""
        tree, parents = _parsed(SDK_BACKEND)
        sites = {"flag_settings_path": [], "_options": [], "with _flag_settings_lock": []}
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                callee = f.attr if isinstance(f, ast.Attribute) else (f.id if isinstance(f, ast.Name) else None)
                if callee in ("flag_settings_path", "_options"):
                    sites[callee].append(node)
                if isinstance(f, ast.Attribute) and f.attr in ("acquire", "release") and "_flag_settings_lock" in ast.unparse(f.value):
                    self.fail("the lock is taken by a bare acquire at line %d; the census reads `with` only" % node.lineno)
            elif isinstance(node, (ast.With, ast.AsyncWith)):
                if any("_flag_settings_lock" in ast.unparse(item.context_expr) for item in node.items):
                    sites["with _flag_settings_lock"].append(node)
        self.assertEqual({k: len(v) for k, v in sites.items()}, {"flag_settings_path": 1, "_options": 1, "with _flag_settings_lock": 1},
                         "one production site each: %r" % ({k: [n.lineno for n in v] for k, v in sites.items()},))
        self.assertEqual({k: _enclosing_def(v[0], parents).name for k, v in sites.items()},
                         {"flag_settings_path": "_options", "_options": "_amain", "with _flag_settings_lock": "flag_settings_path"})
        for k, v in sites.items():
            self.assertEqual(_lock_withs_above(v[0], parents), [], "%s (line %d) sits inside a with over a lock" % (k, v[0].lineno))

    def test_each_existence_row_filed_as_a_problem_says_why_it_is_declared_and_not_bounded(self):
        """Ruling 1 of review round 6 (2026-09-19): the three pick-tainted rows filed problem=True, _do_set_mode's failure
        reports about the mode landing, are accepted as existence rows and the PR is not widened to bound them, on the
        condition that each says WHY it is unbounded where it is declared: it carries no ring_text, so the ring shows the
        whole line, unbounded by a module-level format, and it reports on the mode landing, a mechanism outside what the
        env-pick door bounds. A declared residual with no reason reads later as an oversight, so the comment block above
        each call is read here for the reason's parts, and the census docstring and the ENV ROWS paragraph for the reason
        class, stated once each. Red with any one comment removed, or the reason class dropped from either paragraph.
        Ruling 2 of the post-merge census (2026-09-20): a FOURTH row, SdkSession._log_quietly's problem road (main's fork PR
        #787 made the conduit forward problem=True, key= and ring_text=), is accepted on the same terms with its own
        reason: its text is the union of every caller's line, formatted inline by each caller, the conduit shapes nothing
        and forwards ring_text as given, so the bound is each CALLER's responsibility; the callers passing problem=True are
        named in the comment and pass no ring_text, so each rings its whole line. They are read off the module with each
        _log_quietly call's arguments BOUND against the conduit's signature (Census.bound_site_args: problem whether keyword
        or positional index 1, ring_text whether keyword or index 3; any constant other than False or None is the True
        road; a problem= that is not a constant is a failure row naming the site, never counted as False; round 7 of the
        review, 2026-09-20, tests-2 and extra7-1: read from n.keywords alone, a positional caller counted as saying
        nothing and the roster went stale green). Seven at round 7's head: the two live-work notes and the five failure
        reports the merge of main brought (regression-1, extra5-1: the merge's resolution had sent them down the
        problem=False road; each passes problem=True itself now). Owners by line: ['_log_quietly', '_do_set_mode',
        '_do_set_mode', '_do_set_mode']; the conduit's road forwards ring_text (a Name) where the three carry none.
        The sharpening of that ruling (2026-09-20): the declaration states that the callers' responsibility is CURRENTLY
        UNMET (every caller formats self.name uncut, the unreadable-list line joins up to twelve CLI key names uncut into
        text and key, the five failure reports interpolate an exception's text uncut) and names the tracked item, so a
        reader of the census sees a known unbounded row, tracked, never a false clean one. The clause and the item title
        are pinned on all three surfaces, each read AS ITSELF (round 7, tests-3): the road's comment block, the census
        module's docstring (ast.get_docstring, not the file) and the ENV ROWS paragraph (its own comment lines, not the
        module), so a phrase leaving any one of them is red on that surface's assertion. Round 7's lenses (2026-09-20) added
        the conduit's own docstring, read the same way: its routine-list clause covers the reconcile's report and hold
        lines and not its failure reports, and the sentence scoping round 6's ruling to its population stands there."""
        c = self.c
        lines = Path(SDK_BACKEND).read_text(encoding="utf-8").splitlines()
        filed = sorted((dc for dc in c.existence_rows if dc.problem_decl == ("const", True)), key=lambda d: d.lineno)
        self.assertEqual([dc.owner for dc in filed], ["_log_quietly", "_do_set_mode", "_do_set_mode", "_do_set_mode"])
        rows, refused = c.bound_site_args("SdkSession._log_quietly", constants=("problem",))
        self.assertEqual(refused, [], "a _log_quietly site whose problem= the census cannot read is refused, never counted as False")
        self.assertEqual(len(rows), c.counts["conduit_sites"]["conduit:SdkSession._log_quietly"], "every site of the conduit is bound")
        true_callers = _true_callers(rows)
        self.assertEqual(true_callers, [("_arm_after_relaunch_slot", False), ("_note_unknown_bg_type", False), ("_note_unreadable_bg_list", False),
                                        ("_reconcile_seeded_with_report", False), ("_reconcile_seeded_with_report", False),
                                        ("_reconcile_seeded_work", False), ("_served_by_connect", False)],
                         "the conduit's problem=True callers at round 7's head, none passing ring_text (the reason's 'each rings its whole line')")
        # The conduit's keyed sentence is a contract over its problem=True callers (round 8 of the review, 2026-09-21, kernel-2
        # and extra7-2: round 7 had weakened it to "should count" to fit five unkeyed sites; the sentence is restored and
        # the five sites keyed, by site label, session and exception class). Every True caller passes key= as its WHOLE
        # declared shape, read off the bound arguments as source text (round 9, extra10-2: round 8 read the label alone, so a
        # sid or an exception class dropped from a key changed what the ring does, two sessions' failures folding onto one
        # row, and reds nothing; and regression-1: a missing key read as None and sorted beside strings, so the defect the
        # pin guards failed with a TypeError inside sorted() instead of naming the site): the five failure reports (label,
        # self.sid, type(e).__name__), the two bounded-value rows (label, value). The label is TOTAL: a site with no key=
        # reads "<no key=>" and one whose key the census bound to nothing it can unparse reads "<key the census cannot
        # read>", strings both, so the diff names the drifted site. The execution half (twelve calls, one ring row keyed
        # by the triple) is LogQuietlyAtRuntime's.
        def _key_shape(b):
            v = b.get("key")
            if v is None or (isinstance(v, ast.Constant) and v.value is None):
                return "<no key=>"
            return ast.unparse(v) if isinstance(v, ast.AST) else "<key the census cannot read>"
        self.assertEqual(sorted((caller.name, _key_shape(b)) for caller, _call, b in rows if _true_road(b.get("problem"))),
                         [("_arm_after_relaunch_slot", "('relaunch-slot-wait-failed', self.sid, type(e).__name__)"),
                          ("_note_unknown_bg_type", "('bg-type-unknown', text)"),
                          ("_note_unreadable_bg_list", "('bg-list-unreadable', shape)"),
                          ("_reconcile_seeded_with_report", "('bg-mirror-write-failed', self.sid, type(e).__name__)"),
                          ("_reconcile_seeded_with_report", "('report-reconcile-failed', self.sid, type(e).__name__)"),
                          ("_reconcile_seeded_work", "('seeded-reconcile-failed', self.sid, type(e).__name__)"),
                          ("_served_by_connect", "('reconnect-reg-flag-clear-failed', self.sid, type(e).__name__)")],
                         "every problem=True caller of the conduit passes key= as its whole declared shape: the five failure reports "
                         "keyed (label, self.sid, type(e).__name__) so a recurring shape counts on one ring row PER SESSION and per "
                         "exception class, the two bounded-value rows (label, value)")
        for dc in filed:
            i, block = dc.lineno - 2, []
            while i >= 0 and lines[i].strip().startswith("#"):
                block.insert(0, lines[i].strip().lstrip("#").strip())
                i -= 1
            text = " ".join(block)
            if dc.owner == "_log_quietly":
                self.assertIsInstance(dc.ring_text, ast.Name, "line %d: the conduit forwards its callers' ring_text" % dc.lineno)
                self.assertEqual(dc.ring_text.id, "ring_text")
                parts = ("an EXISTENCE row", "the union of every caller's text", "formatted inline by its caller",
                         "CALLER's responsibility", "unbounded by a module-level format", "outside what the env-pick door bounds",
                         UNMET_CLAUSE + UNMET_ITEM)
                for name, _rt in true_callers:
                    self.assertIn(name, text, "line %d's comment does not name the problem=True caller %s" % (dc.lineno, name))
            else:
                self.assertIsNone(dc.ring_text, "line %d: the reason's first half is that the row carries no ring_text" % dc.lineno)
                parts = ("an EXISTENCE row", "carries no ring_text", "unbounded by a module-level format",
                         "a failure report about the mode landing", "outside what the env-pick door bounds")
            for part in parts:
                self.assertIn(part, text, "line %d's comment lacks the reason's part %r: %r" % (dc.lineno, part, text[:120]))
        census_doc, para = _declaration_surfaces()
        self.assertIn("a declared residual with no reason reads later as an oversight", census_doc, "ruling 1's condition, in the census docstring")
        self.assertIn("the bound of a row through it is its CALLER's responsibility", census_doc, "the fourth row's reason class, in the census docstring")
        self.assertIn(UNMET_CLAUSE + UNMET_ITEM, census_doc, "the fourth row's bound is stated unmet and tracked, in the census docstring")
        self.assertIn("the five failure reports the merge of main brought", census_doc,
                      "the census docstring's reason class covers the merged population's True callers (the road's comment names each)")
        self.assertIn("^ the CONTENT rows", para[0], "the paragraph under the ENV ROWS line")
        paragraph = " ".join(para)
        self.assertIn("each declared and not bounded for a stated reason", paragraph, "ruling 1's condition, in the ENV ROWS paragraph")
        self.assertIn("the bound is each caller's responsibility", paragraph, "the fourth row's reason class, in the ENV ROWS paragraph")
        self.assertIn(UNMET_CLAUSE + UNMET_ITEM, paragraph, "the fourth row's bound is stated unmet and tracked, in the ENV ROWS paragraph itself")
        # The conduit's own docstring (round 7's lenses, 2026-09-20: its routine-list clause was pinned by nothing, so the
        # round-6 wording "the live-work reconcile's lines", which covered the reconcile's three failure reports while the
        # merge sent them down the routine road, came back green under mutation). The clause names the two routine lines
        # of the reconcile and no more, and the sentence scoping round 6's ruling to its population stands beside it.
        conduit_doc = _method_docstring(SDK_BACKEND, "SdkSession", "_log_quietly")
        self.assertIn("the live-work reconcile's report and hold lines), so it is filed problem=False", conduit_doc,
                      "the routine list covers the reconcile's report and hold lines, not its failure reports")
        self.assertNotIn("the live-work reconcile's lines)", conduit_doc, "the round-6 clause that covered the failure reports")
        self.assertIn("passes problem=True through, keyed so a recurring shape counts on one ring row", conduit_doc,
                      "the keyed sentence is the contract (round 8: restored from the 'should count' round 7 had fitted to the code)")
        self.assertNotIn("should count on one ring row", conduit_doc, "a rule edited down to fit a violation is no rule")
        self.assertIn("That ruling was made over a population in which no caller was itself a failure report; the merge of main "
                      "brought five that are", conduit_doc, "the ruling's scope, stated where the road is")

    def test_the_ledger_entrys_where_line_names_the_fork_only_roads_and_no_ring_format_constant(self):
        """The upstream ledger entry for this change (upstream/2026-09-18-env-pick-refuses-credential-names.md) names on its
        where: line the roads an offer would carry or leave behind (round 6's regression-2, in the refuter's corrected shape:
        cut_to and utf16_units in credentials.py; the conduit's two roads with its declared problem=True road; the two
        refused-launch rows and host_refused_ring_text, each fork-only clause in the line's own form) and no ring FORMAT
        constant: none has ever been named there, "the ring budgets" covers the budgets, and a format's name on that line
        would go stale with every re-derivation of the ENV ROWS line. The formats are derived from the census, never
        listed here (tests/test_perf_stats.py's read of its own ledger entry is the precedent for reading an entry's
        load-bearing words). Round 7's lenses found the line pinned by nothing: the three clauses dropped stayed green."""
        entry = Path(HERE).parent.joinpath("upstream", "2026-09-18-env-pick-refuses-credential-names.md").read_text(encoding="utf-8")
        where = [ln for ln in entry.splitlines() if ln.startswith("where: ")]
        self.assertEqual(len(where), 1, "one where: line in the entry's front matter")
        where = where[0]
        for clause in ("cut_to and utf16_units",
                       "_log_quietly's two roads, problem=False for a line saying nothing and its declared problem=True road, and the four "
                       "routine lines declared so (fork-only: upstream has no _log_quietly)",
                       "host_refused_ring_text and the two refused-launch rows in _host_transport_for (fork-only: fork PR #777's rows, which "
                       "upstream does not carry)"):
            self.assertIn(clause, where, "the where: line names the road: %r" % clause)
        formats = sorted({fmt for _owner, fmt, _keyed in self.c.content_identities() if fmt != "UNBOUNDED"})
        self.assertGreaterEqual(len(formats), 2, "the census derives the formats the line must not name (an empty derivation pins nothing)")
        for fmt in formats:
            self.assertNotIn(fmt, where, "a ring format constant on the where: line: %s" % fmt)
        self.assertEqual(re.findall(r"\b[A-Z][A-Z0-9_]*_(?:RING|BUDGET)\b", where), [],
                         "no ring format or budget constant is named on the where: line (the ring budgets are covered by the phrase)")

    def test_the_pick_tags_dict_bound_is_stated_as_the_censuss_reach_and_not_as_the_kernels(self):
        """Ruling 3 of review round 6 (2026-09-19): that the pick tag does not cross a dict return is a bound on the
        CENSUS'S reach, not a property of the code. "The census found no violations" and "the census cannot see this
        class" are different claims, so the census docstring, the ENV ROWS paragraph and the PR body all state it in the
        second sense: the census does not follow the pick tag across a dict return, a pick that crosses one is OUTSIDE the
        census, and the existence population is the direct readers of the surface set by construction. The earlier
        wording, which stated it as a fact about the picks, is asserted gone from both files. Three surfaces state the
        bound and each is read AS ITSELF (round 8 of the review, 2026-09-21, tests-3: round 7 read both whole files
        behind messages naming the docstring and the paragraph, so the sentence could leave the surface named and stay
        anywhere in the file): the census module's docstring (ast.get_docstring), the taint pass's comment block in
        env_ring_census.py where the returns are classified, and kernel/sdk_backend.py's census-rule comment block above
        the ring budgets (not the ENV ROWS paragraph, which states the bound in other words), each joined across its
        wraps. The absence assertions stay over the whole files, the stronger check for an absence."""
        norm = lambda t: " ".join(t.split())
        census_doc, _para = _declaration_surfaces()
        taint_block = _comment_block(os.path.join(HERE, "env_ring_census.py"), "That bounds the census's reach and says nothing of")
        rule_block = _comment_block(SDK_BACKEND, "so a pick that crosses one is OUTSIDE the census")
        for text, where in ((census_doc, "the census docstring"), (taint_block, "the taint pass's comment block"),
                            (rule_block, "kernel/sdk_backend.py's census-rule comment block")):
            self.assertIn("a pick that crosses one is OUTSIDE the census", text, where)
            self.assertIn("direct readers of the surface set by construction", text, where)
        self.assertIn("a bound on the census's reach, not a property of the kernel", census_doc, "the census docstring")
        self.assertIn("That bounds the census's reach and says nothing of the kernel", taint_block,
                      "the taint pass's own comment states the bound in the same sense (the mutation pass reverted it green)")
        self.assertIn("a bound on the census's reach and not a property of this module", rule_block,
                      "the module's census-rule block, read across its wrap")
        for path, where in ((os.path.join(HERE, "env_ring_census.py"), "the census module"), (SDK_BACKEND, "kernel/sdk_backend.py")):
            self.assertNotIn("does not cross a dict at all", norm(Path(path).read_text(encoding="utf-8")),
                             "%s states it as a property of the kernel somewhere in the file" % where)



class _Raised:
    """A construction's own exception, carried out of EnvRowsCensusBlindSpots._censuses for `_take` to re-raise where the
    test asks for the result (a loud plant's CensusError, or anything else the construction raised)."""
    __slots__ = ("exc",)

    def __init__(self, exc):
        self.exc = exc


class _WorkerTraceback(Exception):
    """The worker's traceback text, chained as the cause of an exception a worker raised, for the failure report."""


class _Pending:
    """A batch result the test has not read yet: the worker's future and the spec it was built over. `_take` unpickles it
    when the test asks, so one unpickled Census is alive in the test process at a time, as in the serial class (a batch
    unpickled whole left millions of objects for the next full collection to walk, and the pause landed in whichever
    test came next)."""
    __slots__ = ("spec", "future")

    def __init__(self, spec, future):
        self.spec, self.future = spec, future


# The wedged-worker driver (round 8 of the review, 2026-09-21, extra6-1), run by EnvRowsCensusBlindSpots in a subprocess: a
# pool of the class's shape, a worker sleeping far past the bound, a read that gives up at the bound and drops the pool,
# and then the interpreter's EXIT, which is what the pin measures (with the drop a shutdown(wait=False) alone, the
# executor's manager thread kept waiting on the sleeper's work item and the exit joined that thread, so the process lived
# as long as the sleeper). The driver prints what it saw, one fact per line; the test reads the lines.
WEDGED_WORKER_DRIVER = r"""
import json, os, sys, time
sys.path.insert(0, %(here)r)
import test_session_env as m
cls = m.EnvRowsCensusBlindSpots
cls.POOL_READ_TIMEOUT = 0.5
pool = cls._new_pool()
cls._pool = pool
manager = pool._executor_manager_thread                   # read before shutdown() nulls it
wedged = pool.submit(time.sleep, %(sleep)r)
time.sleep(0.5)                                            # the executor spawns a worker for the submit; read the table settled
procs = list(pool._processes.values())                     # the workers, read before shutdown() nulls the table
case = cls("test_the_censuses_come_through_the_worker_pool_and_read_the_same_as_this_process_builds")
t0 = time.monotonic()
out = case._resolve(m._Pending((m.small_module_files(), m.DEFAULT_SOURCES), wedged))
for p in procs:
    p.join(%(join)r)
manager.join(%(join)r)
print("resolved", type(out).__name__, "in", round(time.monotonic() - t0, 1), "s;", cls._pool_reason)
print("workers", json.dumps([[p.pid, p.exitcode] for p in procs]))
print("manager alive", manager.is_alive())
try:
    exc = wedged.exception(timeout=%(join)r)
except BaseException as e:
    exc = e
print("wedged", type(exc).__name__)
"""

# The class-end driver (round 9 of the review, correctness-2 and extra10-3): a pool of the class's shape holding a worker
# that never returns and whose future NO test read (a test that failed mid-batch leaves its remaining futures unread), then
# tearDownClass as the class ships it. With `pool.shutdown(wait=True)` there the call never returned (the driver printed its
# "calling tearDownClass" line and nothing more until the test killed its process group at the wall-clock limit); with the
# drop it returns at once and the workers read back as killed.
WEDGED_TEARDOWN_DRIVER = r"""
import json, sys, time
sys.path.insert(0, %(here)r)
import test_session_env as m
cls = m.EnvRowsCensusBlindSpots
pool = cls._new_pool()
cls._pool = pool
manager = pool._executor_manager_thread                   # read before shutdown() nulls it
wedged = pool.submit(time.sleep, %(sleep)r)               # never read: the unread future a failed test leaves behind
time.sleep(0.5)                                            # the executor spawns a worker for the submit; read the table settled
procs = list(pool._processes.values())
print("calling tearDownClass", flush=True)
t0 = time.monotonic()
cls.tearDownClass()
print("teardown returned in", round(time.monotonic() - t0, 1), "s")
for p in procs:
    p.join(%(join)r)
manager.join(%(join)r)
print("workers", json.dumps([[p.pid, p.exitcode] for p in procs]))
print("manager alive", manager.is_alive())
try:
    exc = wedged.exception(timeout=%(join)r)
except BaseException as e:
    exc = e
print("wedged", type(exc).__name__)
"""


class EnvRowsCensusBlindSpots(unittest.TestCase):
    """The round-6 blind-pin lens planted a tenth env-carrying ring row 69 ways and the census passed 13 of them at its
    baseline (2026-09-19): aliases of the door bound at module or class scope (a module `_RING = SdkBackend._log` or
    `getattr(SdkBackend, "_log")`, a class-body `_ring = _log`, a method default `log=_log`), the door reached by
    reflection (`operator.attrgetter("_log")`), env names reaching a seen door through a re-keyed dict return, an
    in-place `append` in a loop, `+=`, an attribute stored in one method and read in another, and a module list's
    `extend`, and second writers of the ring (`be._problems.append` from kernel.py, `self.backend._problems.append`
    from a session, `self._problems.insert` in a second SdkBackend method). Each sabotage is replayed here on a copy of
    the SMALL MODULE (SMALL_SDK_BACKEND, since round 8 of the review; the block comment above it derives what the walker
    resolves a plant against, and why kernel/credentials.py is not needed beside it) or a synthetic module beside it,
    and must be LOUD: a tenth content row (the identity pin reds), a failure named by site, or a CensusError. The copies
    edit anchors asserted present once in the small module. The rulings' lenses (the addendum of 2026-09-19) added 45
    dict-source variants and 60 alias receivers, 35 and 13 of them quiet; the five tests at the end of this class replay
    every quiet one, loud now, beside the refusal-side pins the mutation pass found missing. Two kinds of pin share this
    class (the reviewer's ruling, 2026-09-21: a test uses the smallest input that can exhibit the property it asserts):
    a MECHANICS pin ("does the walker classify a form planted here?") plants on the small module, whose own census is
    clean, so "tenth" names the planted row and every count reads BASE, the small module's content rows (zero, from the
    control census at setUpClass), for a copy that adds no row and BASE + 1 for one that adds the plant; a POPULATION
    pin ("what does the tree have?") reads the tree through the census() door, once per process, and states its
    expectations in the tree's terms (ROWS, the committed tables). Until round 8's small-input commit every plant was a
    sabotaged copy of the real file, about 180 of them at about 1.3 s each, and BASE was the tree's row count."""

    FMT_ANCHOR = "RESERVED_DROP_RING = ("
    METHOD_ANCHOR = "    def problem_seq(self) -> int:"
    SESSION_ANCHOR = "    def _log_quietly(self, line: str, problem=None, key=None, ring_text=None) -> None:"
    CRASH_ANCHOR = '_log(f"sdk session {self.name} crashed: '
    API_ANCHOR = "    def _push(self, ev: AhEvent):"       # ApiHealth's method appending to its own self._ring deque
    TENTH = 'TENTH_RING = "env (%s): tenth %s"\n'
    MSG = '"env (%s): tenth %s" % (sess.name, ", ".join(sorted(sess.env_vars)))'
    RING = 'ring_text=TENTH_RING % (sess.name[:20], len(sess.env_vars))'
    TENTH_ID = ("_tenth", "TENTH_RING", False)

    @classmethod
    def setUpClass(cls):
        cls.src = SMALL_SDK_BACKEND                         # what _copy edits: the small module, never the tree file
        for needle in (cls.FMT_ANCHOR, cls.METHOD_ANCHOR, cls.SESSION_ANCHOR, cls.CRASH_ANCHOR, cls.API_ANCHOR, "class SdkBackend:\n"):
            assert cls.src.count(needle) == 1, "the copies' anchors are in the small module once each: %r" % needle
        cls.small_path, = small_module_files()              # the unchanged small module, for a plant beside it
        cls.small = small_census()                          # the control: the small module's own census, clean, frozen, once per process
        cls.BASE = len(cls.small.content_rows)              # the small module's content rows: none (small_census asserts it)
        cls._start_pool()

    @classmethod
    def tearDownClass(cls):
        pool, cls._pool = cls._pool, None
        if pool is not None:
            # the DROP, never a join (round 9 of the review, correctness-2 and extra10-3): round 7's rule that the drop must not
            # join reached _pool_lost and _new_pool's start arm and not this site, so a worker wedged on a batch result no test
            # read (a test that failed mid-batch leaves the rest of its futures unread) held the pytest process open at the
            # class's end; pytest-timeout's per-test timer is cancelled by the very failure that leaves the future unread, so
            # CI's 600 s bound never fired and the job ran to its 25-minute ceiling as cancelled, not red. Nothing is lost by
            # the kill: a construction is recorded in this process when its result is READ (_take absorbs the worker's records
            # at unpickle), so an unread future contributes no record on either road and the two checks below read the same.
            # Every join on this class's pool is bounded or a drop (WEDGED_TEARDOWN_DRIVER pins this one).
            cls._drop_pool(pool)
        problems = []
        for check in (cls._assert_each_unchanged_census_was_computed_once_and_reads_as_built,
                      cls._assert_constructions_equal_distinct_inputs_plus_declared_comparisons):
            try:
                check()
            except AssertionError as e:
                problems.append(str(e))
        if problems:
            raise AssertionError("\n".join(problems))

    @classmethod
    def _assert_each_unchanged_census_was_computed_once_and_reads_as_built(cls):
        """The shared-census rule, BY EXECUTION, once every test of the class has run (round 8 of the review on fork PR
        #781, 2026-09-21, the reviewer's ruling: one census per class shared by the pins, the sharing verified by counting
        computations and not by the presence of a cache, and the shared result immutable). Two facts, read off
        env_ring_census's recorder (its block comment says what a record is): (1) for each unchanged-tree input this
        module reads through the `census()` door (the three files, and the pair kernel/sdk_backend.py with
        kernel/credentials.py), the constructions by Census itself, on any road, this process's own or a pool worker's,
        number exactly ONE where anything in this process read the input and zero where nothing did; a subclass's
        construction (Sweeping's over the real pair) is a different computation and is counted under its own class, and
        every sabotaged copy and synthetic plant is a different input, counted under its own identity; (2) every census
        the door holds digests as it did when the door froze and handed it out, over what census_digest covers (summary(),
        the tables outside it and the structural rosters a population pin reads; its docstring lists them and names the
        slots outside), so no pin changed one of those, in whatever order the pins ran. Runs here, in tearDownClass, which unittest and pytest alike run after the class's last test in this
        process: under pytest serial the whole class; under pytest-xdist (-n 3, the sweep's shape), where a class may
        split across workers, once per worker for that worker's share, so the property there is at most one construction
        per worker per input and exactly one where that worker read it, which is what `reads` makes the expectation say.
        Red before the sharing, at the round-8 head with this pin bound in: the pair counted three constructions for two
        door reads in the module's process (the door's one, and two more through the pool, the conduit-roster pin's and
        the fixpoint pin's, each over the unchanged pair) against one construction for the three files; with the door's
        store dropped, twelve constructions for twelve reads of the three files over the class alone."""
        problems = []
        for label, files in (("the three files", CENSUS_FILES), ("the pair", (SDK_BACKEND, CREDENTIALS_PY))):
            recs, reads = erc.constructions_of(files), erc.reads_of(files)
            expected = 1 if reads else 0
            if len(recs) != expected:
                problems.append("%s (%s): %d constructions of the unchanged input for %d door reads in this process, expected %d: %s"
                                % (label, ", ".join(os.path.basename(f) for f in files), len(recs), reads, expected,
                                   [(r["cls"], r["road"], r["pid"]) for r in recs]))
        for key, c in erc._CENSUS.items():
            if erc.census_digest(c) != c.digest_at_birth:
                problems.append("the door's census over %s reads differently at the end of the class than when it was built: a pin changed it"
                                % ", ".join(os.path.basename(f) for f in key[0]))
        if problems:
            raise AssertionError("the shared census rule (one construction per unchanged input per process, read unchanged): " + "; ".join(problems))

    @classmethod
    def _assert_constructions_equal_distinct_inputs_plus_declared_comparisons(cls):
        """The count pin, a PROPERTY over every construction this process has recorded (round 8 of the review on fork PR
        #781, 2026-09-21, the reviewer's ruling: never `constructions == 1`; assert constructions == distinct (input,
        class), so a redundant construction reds and a legitimate new input does not, where a floor or a constant goes
        stale the moment the population moves). Read off env_ring_census's recorder: the records group by (input identity,
        class); a group's first construction is never a declared comparison and every later construction of the group is
        one (erc.comparing: a pool pin builds a pool result's own specs again in this process to compare what the two roads
        read, and declares it at the build), so constructions == distinct + declared comparisons holds with every
        comparison after a construction of its input. On failure the per-input list is printed: the files by basename, the
        class, and each construction's road with its declaration. Under pytest-xdist (-n 3, the sweep's shape) the recorder
        is the worker's and this runs once per worker over that worker's records; a pool pin runs whole in one worker, so a
        comparison and the construction it compares against sit in the same recorder. Red before the declaration existed,
        at the census commit with this pin bound in and the class run alone: constructions=210 distinct (input, class)=200
        declared comparisons=0, nine groups named (ten constructions past the first of their input), every one a pool pin's
        second build of its own specs (a pooled build then one or two here, or two builds here). Red with a redundant
        construction planted on this commit's tree (the same small input built
        twice in one test through the pool, undeclared): constructions=212 distinct (input, class)=201 declared
        comparisons=10, one group named, (('sdk_backend.py',), 'Census', [('pool', ''), ('pool', '')])."""
        recs = list(erc.CONSTRUCTIONS)
        distinct = {erc.construction_key(r) for r in recs}
        declared = [r for r in recs if r["comparison"]]
        repeated = erc.repeated_constructions(recs)
        if repeated or len(recs) != len(distinct) + len(declared):
            raise AssertionError("the count rule (constructions == distinct (input, class) + declared comparisons, each comparison after "
                                 "a construction of its input): constructions=%d distinct (input, class)=%d declared comparisons=%d; the "
                                 "inputs constructed against the rule, each with its constructions' roads in order: %s"
                                 % (len(recs), len(distinct), len(declared), repeated))

    def setUp(self):
        self._pool_reason_at_start = type(self)._pool_reason    # read back in tearDown: a loss during this test is its failure

    def tearDown(self):
        """A pool lost DURING this test fails this test, naming the reason, wherever the test sits in the class's order (round
        8 of the review on fork PR #781, extra6-2's second pass, by its mutation verifier: `_pool_or_fail` fails the pins that
        need the pool road, but only for a pool lost before them in unittest's alphabetical order; a loss planted inside a
        test sorted after them failed nothing, the run's only trace the RuntimeWarning). A reason recorded BEFORE the test
        (the start failure, set in setUpClass) is not this test's to report: it is every pool-road pin's, through
        `_pool_or_fail`, which alone knows the one environment limitation that may skip; a loss under a test is never a
        start failure, so no limitation applies here. The class's pool is not restored: the loss stands for the rest of
        the class and every later pool-road pin fails on it too."""
        cls = type(self)
        if cls._pool_reason != self._pool_reason_at_start:
            self.fail("the census pool was lost during this test, so the pool road did not run for its constructions from the "
                      "loss on (built in this process instead, the results unchanged; a failure of this test, not a skip, "
                      "wherever it sits in the class's order): %s" % cls._pool_reason)

    def _copy(self, edit, name="sdk_backend.py"):
        new = edit(self.src)
        self.assertNotEqual(new, self.src, "the copy's edit must apply")
        path = os.path.join(tempfile.mkdtemp(), name)
        Path(path).write_text(new, encoding="utf-8")
        return path

    def _plant(self, name, src):
        path = os.path.join(tempfile.mkdtemp(), name)
        Path(path).write_text(src, encoding="utf-8")
        return path

    def _with_format(self, s):
        return s.replace(self.FMT_ANCHOR, self.TENTH + self.FMT_ANCHOR)

    def _method(self, body, extra_methods=""):
        """A module copy with TENTH_RING and a new SdkBackend method `_tenth(self, sess)` whose body is `body`."""
        return self._copy(lambda s: self._with_format(s).replace(
            self.METHOD_ANCHOR, extra_methods + "    def _tenth(self, sess):\n" + body + "\n\n" + self.METHOD_ANCHOR))

    # ---- the census pool (fork PR #781, the reviewer's ruling of 2026-09-20 on the walk's cost on CI) ----
    # This class constructs about 180 censuses, each over a distinct sabotaged copy of the small module (SMALL_SDK_BACKEND;
    # about 7 ms each in one process since round 8's small-input commit, when the reviewer ruled that a mechanics pin's
    # input is the planted module plus what the walker resolves against). Until that commit each was a copy of
    # kernel/sdk_backend.py at about 1.3 s; CI runs pytest serially under a 25-minute job ceiling, and at the head before
    # the pool the Python 3.10 job was cancelled by it. The pool's ruling: build the class's censuses in worker processes
    # and assert on the same results (no cap raise before the cost is reduced and re-measured). The pool stays as the
    # class's construction road with the small input: its transport and its degradation roads are properties of the
    # pool, pinned below whatever the input, and a batch of plants still builds off the test process's thread. Every
    # plain Census this class reads comes through ONE entry point,
    # `_censuses(specs)`, a spec being (files, sources). It submits the batch to the class's ProcessPoolExecutor (the
    # spawn start method; min(os.cpu_count(), 4) workers; started once in setUpClass with a start probe bounded by
    # POOL_START_TIMEOUT; each worker imports tests.env_ring_census, the module's registered name, and runs its
    # `build_census` over the copy paths this process wrote) and returns the results in the batch's order: the Census
    # objects, unpickled (Census.__getstate__ re-keys the id(node) tables), or, for a construction that raised, its
    # exception carried back from the worker in a `_Raised`, which `_take` re-raises where the test asks for the result,
    # so a loud plant's CensusError still raises in this process with the worker's message. Each test plants first,
    # then builds its plants in one batch, then asserts in the order it always did; a batch's results are unpickled one
    # at a time as the test reads them (`_Pending`), never all at once, so the test process holds one Census at a time
    # and its full garbage collections walk the heap the serial class left them. A failure of the POOL degrades the
    # class, ANNOUNCED; a failure of the WORK is the test's own error and never a degradation (the reviewer's round 7
    # on fork PR #781: the repo's standing rule is to fail loudly rather than degrade silently, and a degradation whose
    # only trace was a captured stderr line read under CI's -q as "1 skipped"). By failure kind:
    #   the pool cannot START (the stdlib's NotImplementedError from concurrent.futures.process._check_system_limits
    #     on a Python built without multiprocessing.synchronize or with fewer than 256 semaphores, its ValueError on
    #     a bad worker count, a worker that cannot spawn raising ImportError or RuntimeError): `_start_pool` catches
    #     EVERY exception, since the start path touches pool plumbing alone (`_new_pool` builds the executor and runs
    #     `pool_probe`, which returns a pid) and so hides no census defect; with the narrow tuple the class errored in
    #     setUpClass on either stdlib message (fork PR #781's runs verifier). The class DEGRADES: every batch built here.
    #   the pool BREAKS AT A SUBMIT (BrokenProcessPool, or another of POOL_FAILURES): `_censuses` catches the tuple.
    #     The class DEGRADES: that batch and every later one built here.
    #   a worker WEDGES (a result not delivered within POOL_READ_TIMEOUT of being asked for, the wait's TimeoutError)
    #     or the pool FAILS UNDER A READ (BrokenProcessPool, CancelledError from the shutdown, OSError, the pickling
    #     errors, PoolTransportError from a worker whose census could not be pickled): `_resolve` catches the tuple.
    #     The class DEGRADES: that construction built here, a later undelivered one built here without a wait, a
    #     delivered one still read. The bound never yields an empty result: on the timeout `_resolve` builds the
    #     construction in this process, so what a read returns is a Census or the construction's own exception,
    #     whichever road built it, never nothing.
    #   the WORK RAISES (a CensusError over a loud plant, or an exception the census code should never raise, an
    #     AttributeError or a TypeError say): not a pool failure, and caught by none of the three; the start's
    #     catch-all never sees it either, since the start submits `pool_probe` alone. The worker's `build_census`
    #     carries it as DATA, a ("raised", exc) payload with the worker's traceback on it, so the read's catch never
    #     sees it; `_unpack` wraps it in a `_Raised` and `_take` re-raises it in this process, AS ITSELF, where the
    #     test asked for the result, the worker's traceback as its cause; `_serial` carries a serial construction's
    #     exception the same way. It is distinguishable from a clean empty result by construction: a `_Raised`, never
    #     a Census and never None, so a read that would have handed the test an empty census raises instead. The
    #     class does NOT degrade for it: the pool stays, no line, no warning, and the test that drove the work ERRORS
    #     with the exception itself. An exception at a read outside the tuple (pickle.loads raising over a class this
    #     process cannot import, say) is a transport defect and propagates as itself too.
    # The DROP does not join (round 8 of the review, 2026-09-21, extra6-1: a shutdown(wait=False) alone leaves the
    # executor's manager thread waiting on a running work item, and the interpreter's exit joins that thread, so a
    # worker that never returns held the pytest process open for as long as it ran, the wedged case the bound exists
    # for). `_drop_pool` reads the workers off the executor before shutdown() nulls its table, shuts down without
    # waiting, and sends each worker SIGKILL through multiprocessing.Process.kill; the manager thread wakes on a
    # killed worker's sentinel, marks the pool broken (a pending future ends with BrokenProcessPool, never a result),
    # joins every worker, which reaps it, and returns, so the exit joins a finished thread. Pinned by running a driver
    # in a subprocess with a wall-clock limit: a worker sleeping far past the bound, the read giving up, the process
    # exiting, every worker's exit code read back as SIGKILL's.
    # Every degradation is announced two ways from the one place, `_pool_lost`: a RuntimeWarning carrying the reason
    # (pytest records it, counts it on the -q summary line and prints it in the warnings section, so a degraded
    # class reads "N passed, M failed, 1 warning" and names its cause, M the tests the next sentence names) and one
    # stderr line naming the reason and that the results are unchanged.
    # A loss is then a FAILURE wherever in the class's order it happens (round 8,
    # extra6-2: a skip reports success, so a pool lost for a real reason left the run green and silent; and round 8's
    # mutation verifier: the pins that need the pool road fail only for a pool lost BEFORE them in unittest's
    # alphabetical order, so a loss planted inside a test sorted after them failed nothing): every pin that needs the
    # pool road fails naming the reason (`_pool_or_fail`), and the test during which the pool was lost fails in its
    # tearDown naming the reason (setUp records the reason at the start of each test, tearDown compares). The ONE
    # environment limitation the pool-road pins skip on instead, asserted as such, is the stdlib's refusal to build a
    # ProcessPoolExecutor at all (ENVIRONMENT_LIMITATION below), a start failure, recorded in setUpClass before any test
    # runs, which is why a start failure is theirs to report and never tearDown's.
    # The three test-local Census subclasses below (Tracing, Sweeping, _Capped) are not importable by a worker and
    # build in this process, each over an input of its own or, Sweeping's second construction, over the real pair by a
    # different algorithm, which is the comparison that pin makes. The UNCHANGED tree is never constructed by a test of
    # this class (round 8 of the review, 2026-09-21, the reviewer's ruling: one census per class, shared by the pins,
    # the sharing verified by execution and the result immutable): every read of it, the three files (CENSUS_FILES) or
    # the pair (kernel/sdk_backend.py with kernel/credentials.py), goes through env_ring_census's `census()` door, ONE
    # frozen census per input per process (the door's block comment says what the freeze is and why a read-only view
    # and not a copy per read; the recorder's block comment says how constructions are counted, the pool's shipped back
    # in build_census's payload). Until round 8 two pins of this class, the conduit roster's and the fixpoint's, built
    # the unchanged pair through the pool beside the door's census of it. tearDownClass asserts, off the recorder, that
    # each unchanged input was constructed at most once in this process and exactly once where anything read it, and
    # that each census the door holds still digests as it did when built; the immutability pin below holds the freeze.
    # `roads` records the road each batch took and `built` counts constructions by road; the pool's own pins hold that
    # the pool road is taken and that the fallback reads the same.
    POOL_WORKERS = min(os.cpu_count() or 1, 4)
    POOL_START_TIMEOUT = 120.0        # seconds the pool's first worker has to answer the start probe
    POOL_READ_TIMEOUT = 240.0         # seconds a batch result has to arrive once the test asks for it. Derived (the reviewer's
                                      # round 7 on fork PR #781): the largest batch, 29 constructions, built serially in 39.5 s
                                      # on the development box over copies of the real file (the class alone with the pool
                                      # off, 2026-09-21; across four workers the same batch took about a quarter of that), so
                                      # a result six times that late is a wedged worker, not a slow one: 6 x 40 s = 240 s.
                                      # The constraint is the module's per-test ceiling, 600 s (CI's --timeout): a test that
                                      # waits the bound once and then rebuilds its largest batch here took 240 + 40 = 280 s on
                                      # this box, leaving 320 s, an eightfold slower rebuild, before the ceiling ends the run.
                                      # No per-batch measurement exists from CI's runners; that eightfold is the margin for
                                      # them. Over the small module (round 8's small-input commit) the same 29-construction
                                      # batch builds serially in 0.20 s on this box (6.9 ms each), so the bound is kept and
                                      # not re-derived downward: it bounds a WEDGED worker, a slow CI worker must not read as
                                      # one, and the ceiling arithmetic only improves (240 s plus a rebuild under a second).
    POOL_FAILURES = (BrokenProcessPool, OSError, pickle.PicklingError, pickle.UnpicklingError, concurrent.futures.TimeoutError,
                     concurrent.futures.CancelledError, erc.PoolTransportError)
    _pool = None                      # the class's executor, or None while unavailable
    _pool_reason = None               # why it is unavailable, once known
    roads = []                        # per batch, in order, the road it was routed to: "pool" or "serial (<reason>)"
    built = collections.Counter()     # constructions by the road that built them (a pooled batch's stragglers may be serial)

    # The one environment limitation a pool-road pin may SKIP on (round 8, extra6-2): the stdlib refusing to build a
    # ProcessPoolExecutor at all, concurrent.futures.process._check_system_limits raising NotImplementedError on a Python
    # built without multiprocessing.synchronize or on a system with fewer than 256 semaphores (both of its messages name
    # semaphores). Any other reason the pool was lost is a FAILURE of the pin that needs the pool.
    ENVIRONMENT_LIMITATION = "the census pool could not start: NotImplementedError: "

    @classmethod
    def _drop_pool(cls, pool):
        """The executor dropped WITHOUT a join and its workers killed (the block comment above, the DROP). The workers are
        read off the executor first (`_processes`, the stdlib's private table, the one handle the executor gives; shutdown()
        nulls it), the executor is shut down without waiting and its pending futures cancelled, and each worker is sent
        SIGKILL through multiprocessing.Process.kill. Reaping is the manager thread's: a killed worker's sentinel wakes it,
        it marks the pool broken and joins every worker (concurrent.futures.process, _join_executor_internals), so the
        interpreter's exit joins a thread that is done. A worker already closed or never started has nothing to kill."""
        procs = list((getattr(pool, "_processes", None) or {}).values())
        pool.shutdown(wait=False, cancel_futures=True)
        for proc in procs:
            try:
                proc.kill()
            except (ValueError, AttributeError):
                pass

    @classmethod
    def _new_pool(cls):
        """A fresh executor whose first worker has answered the start probe; raises what the start raised, the executor
        dropped (a probe that never answers is a wedged worker, killed like any other)."""
        pool = concurrent.futures.ProcessPoolExecutor(max_workers=cls.POOL_WORKERS, mp_context=multiprocessing.get_context("spawn"))
        try:
            pool.submit(erc.pool_probe).result(timeout=cls.POOL_START_TIMEOUT)
        except BaseException:
            cls._drop_pool(pool)
            raise
        return pool

    @classmethod
    def _start_pool(cls):
        """The class's pool, or none: whatever the start raises (the block comment above says why every exception, not
        POOL_FAILURES alone) leaves the pool unavailable, ANNOUNCED. The catch-all's scope is the start path alone: the
        executor's construction and the probe; no pooled work runs here, so an AttributeError or TypeError raised inside
        the census's work is never caught by it and never degrades the class. Such an exception travels as data and is
        re-raised as itself by `_take` where the test asked for the result (the block comment above, the WORK RAISES)."""
        try:
            cls._pool = cls._new_pool()
        except Exception as e:
            cls._pool_lost("the census pool could not start: %s: %s" % (type(e).__name__, e))

    @classmethod
    def _pool_lost(cls, reason):
        """The pool is gone for the rest of the class, ANNOUNCED: a RuntimeWarning carrying the reason (the block comment above
        says why a warning: pytest counts it on the -q summary line and prints it, where a stderr line is captured) and the
        same text as one line on stderr; every construction from here builds in this process (a batch already submitted
        finishes serially as its results are read). The executor is dropped through `_drop_pool`: no join, its workers
        killed, so a wedged worker cannot hold the interpreter's exit. Every degradation of the class comes through here,
        whatever its kind."""
        pool, cls._pool, cls._pool_reason = cls._pool, None, reason
        if pool is not None:
            cls._drop_pool(pool)
        line = ("[%s] %s; building this class's censuses in the test process instead (the results are unchanged, the class is slower)"
                % (cls.__name__, reason))
        warnings.warn(line, RuntimeWarning, stacklevel=2)
        print(line, file=sys.stderr, flush=True)

    def _pool_or_fail(self):
        """The class's pool for a pin that needs the pool road. A pool lost for the ONE declared environment limitation
        (ENVIRONMENT_LIMITATION, asserted by its text) skips, naming it; a pool lost for any other reason FAILS the pin,
        naming the reason (round 8 of the review, 2026-09-21, extra6-2: the pin skipped on every reason, so a class that
        lost its pool to a real defect reported success)."""
        cls = type(self)
        if cls._pool is not None:
            return cls._pool
        reason = cls._pool_reason or ""
        if reason.startswith(cls.ENVIRONMENT_LIMITATION) and "semaphore" in reason:
            self.skipTest("the declared environment limitation, the stdlib's refusal to build a process pool: %s" % reason)
        self.fail("the census pool was lost for a reason that is no environment limitation, so the road this pin needs did "
                  "not run (a failure of the pin, not a skip): %s" % reason)

    def _censuses(self, specs):
        """The censuses over `specs`, one result per (files, sources) in the specs' order, each read through `_take`: on the
        pool road a `_Pending` (the worker builds now, the test process unpickles when asked), on the serial road a
        Census or a `_Raised` holding the construction's own exception."""
        specs = [(tuple(files), sources) for files, sources in specs]
        cls = type(self)
        if cls._pool is not None:
            try:
                futures = [cls._pool.submit(erc.build_census, files, sources) for files, sources in specs]
            except cls.POOL_FAILURES as e:
                cls._pool_lost("the census pool failed under a batch of %d: %s: %s" % (len(specs), type(e).__name__, e))
            else:
                cls.roads.append("pool")
                return [_Pending(spec, f) for spec, f in zip(specs, futures)]
        out = self._serial(specs)
        cls.roads.append("serial (%s)" % cls._pool_reason)
        cls.built["serial"] += len(out)
        return out

    def _resolve(self, result):
        """A batch result as a Census or a `_Raised`: a `_Pending` is unpickled from its worker here, waited for at most
        POOL_READ_TIMEOUT, and one whose pool failed under it (the worker gone, the future cancelled by the shutdown, the
        transport refused, the result not delivered within the bound) is built in this process after `_pool_lost` has
        spoken once. Once the pool is gone, a result it never delivered is built here without a wait (a worker that
        wedged is waited for once, for the bound, not once per result) and one it did deliver is read. A timeout never
        yields an empty result: the construction is built here, so the return is a Census or the construction's own
        exception in a `_Raised`, whichever road built it."""
        if not isinstance(result, _Pending):
            return result
        cls = type(self)
        if cls._pool is None and not result.future.done():
            out = self._serial([result.spec])[0]
            cls.built["serial"] += 1
            return out
        why = None
        try:
            out = self._unpack(pickle.loads(result.future.result(timeout=cls.POOL_READ_TIMEOUT)))
        except concurrent.futures.TimeoutError:
            why = "TimeoutError: no result within %g s" % cls.POOL_READ_TIMEOUT
        except cls.POOL_FAILURES as e:
            why = "%s: %s" % (type(e).__name__, e)
        if why is None:
            cls.built["pool"] += 1
            return out
        if cls._pool is not None:
            cls._pool_lost("the census pool failed under a batch: %s" % why)
        out = self._serial([result.spec])[0]
        cls.built["serial"] += 1
        return out

    @staticmethod
    def _serial(specs):
        """The same results built in this process."""
        out = []
        for files, sources in specs:
            try:
                out.append(Census(files, sources))
            except Exception as e:
                out.append(_Raised(e))
        return out

    def _comparison(self, specs):
        """The same specs built again in this process as the COMPARISON a pool pin makes against what the pool, or a
        degradation road, delivered over them, declared so to the recorder (env_ring_census.comparing): the count pin at the
        class's end admits a second construction of an input only under this declaration, and only after a construction of
        it, so a pool pin's comparison passes it and an undeclared second construction anywhere reds it."""
        with erc.comparing():
            return self._serial(specs)

    @staticmethod
    def _unpack(payload):
        kind, value, records = payload
        erc.absorb_constructions(records)       # the worker's constructions, held here under their inputs (erc's recorder comment)
        if kind == "raised":
            value.__cause__ = _WorkerTraceback(getattr(value, "worker_traceback", "(no traceback carried)"))
            return _Raised(value)
        return value

    def _take(self, result):
        """The Census of a batch result, or the construction's exception raised here."""
        result = self._resolve(result)
        if isinstance(result, _Raised):
            raise result.exc
        return result

    def _spec(self, *paths, sources=DEFAULT_SOURCES):
        """A construction's (files, sources): a copy of the small module, or the unchanged small module with a plant beside
        it, and nothing else (until round 8's small-input commit kernel/credentials.py rode beside every copy of the real
        file; the block comment above SMALL_SDK_BACKEND says why nothing needs to ride beside the small module)."""
        return (tuple(paths), sources)

    def _census(self, *paths):
        return self._take(self._censuses([self._spec(*paths)])[0])

    def _assert_tenth_found(self, c, kind):
        """The planted row is a CONTENT row (found, env-tainted, its head read) and the population pin's ONE identity
        equality is sensitive to it as an ADDED row (round 9 of the review, tests-2): the pin takes the census under the
        control's identities plus the planted row, and refuses it by name under the control's identities alone. Until round 9
        the closing arm asserted a refusal under the tree's ROWS, which every small-module census earns, plant or no plant, so
        the loudness proof the 22 plants share held for the wrong reason (round 8's small-input move). `expect_failures`
        went with it: no arm passed one, and the pin's own first assertion is that the derivation had none."""
        self.assertEqual(list(c.failures), [])
        self.assertIn(self.TENTH_ID, c.content_identities())
        self.assertEqual(len(c.content_rows), self.BASE + 1)
        found = [dc for dc in c.door_calls if dc.owner == "_tenth"]
        self.assertEqual([(dc.kind, sorted(dc.taint), dc.heads, dc.ring_formats) for dc in found],
                         [(kind, ["env"], ["env (%s): tenth %s"], ["TENTH_RING"])])
        self.assertEqual([w for dc, w in c.explicit_violations if dc.owner == "_tenth"], [])
        control = list(self.small.content_identities())                                  # the small module's own rows: none
        EnvRowsPopulation._assert_pin(self, c, expected=control + [self.TENTH_ID])        # the plant is the one ADDED row, and the pin takes it
        with self.assertRaises(AssertionError) as cm:
            EnvRowsPopulation._assert_pin(self, c, expected=control)                      # under the control's expectation it refuses the added row by name
        self.assertIn("_tenth", str(cm.exception))

    def test_a_door_aliased_at_module_scope_is_found_and_an_uncalled_one_is_a_failure(self):
        """Family A of the lens, the module scope: `_RING = SdkBackend._log` and `_RING3 = getattr(SdkBackend, "_log")`
        bound at import, called through the bare name with the message after an explicit self (the alias is the
        writer's function, unbound); both quiet at aa1037c8f (doors 395, content 9, failures none). Found as kind
        "alias" with the message read in the right position. A module alias nothing calls is a failure named by site."""
        bindings = (("attribute", "_RING = SdkBackend._log"), ("getattr", '_RING = getattr(SdkBackend, "_log")'))
        results = self._censuses([self._spec(self._copy(lambda s: self._with_format(s) + "\n%s\ndef _tenth(be, sess):\n    _RING(be, %s, problem=True, %s)\n"
                                                        % (binding, self.MSG, self.RING))) for _label, binding in bindings]
                                 + [self._spec(self._copy(lambda s: s + "\n_RING4 = SdkBackend._log\n"))])
        for (label, _binding), r in zip(bindings, results):
            with self.subTest(alias=label):
                c = self._take(r)
                self._assert_tenth_found(c, "alias")
                self.assertIn("module alias _RING", [how for _b, _ln, how, _f in c.door_value_sites])
        c = self._take(results[-1])
        self.assertEqual([(k, b, t) for k, b, _ln, t in c.failures], [("door-escapes", "sdk_backend.py", "module alias _RING4 is never called")])
        self.assertEqual(len(c.content_rows), self.BASE)

    def test_a_door_aliased_in_the_writers_class_body_is_found_and_an_ambiguous_name_is_a_failure(self):
        """Family A, the class scope: a class-body `_ring_door = _log` (the writer's bare name resolves in its own class
        body) called as `self._ring_door(...)`, and a method default `log=_log` called as `log(self, ...)`; both quiet
        at aa1037c8f. Found as kinds "alias" and "param", the message read after the explicit self. The lens's own
        spelling, `_ring`, is also ApiHealth's deque attribute: two bindings the census tells apart by the receiver's
        scope since ruling 4 of review round 6 (the next test walks every arm), so with the alias called through self in
        the writer's class the row is found, the collision is recorded and nothing fails; the failure is reserved for an
        untyped receiver of the twice-bound name."""
        class_body, method_default, lens_ring = self._censuses([self._spec(p) for p in (
            self._copy(lambda s: self._with_format(s).replace(self.METHOD_ANCHOR,
                "    _ring_door = _log\n\n    def _tenth(self, sess):\n        self._ring_door(%s, problem=True, %s)\n\n" % (self.MSG, self.RING) + self.METHOD_ANCHOR)),
            self._copy(lambda s: self._with_format(s).replace(self.METHOD_ANCHOR,
                "    def _tenth(self, sess, log=_log):\n        log(self, %s, problem=True, %s)\n\n" % (self.MSG, self.RING) + self.METHOD_ANCHOR)),
            self._copy(lambda s: self._with_format(s).replace(self.METHOD_ANCHOR,
                "    _ring = _log\n\n    def _tenth(self, sess):\n        self._ring(%s, problem=True, %s)\n\n" % (self.MSG, self.RING) + self.METHOD_ANCHOR)))])
        with self.subTest(alias="class-body _ring_door = _log"):
            c = self._take(class_body)
            self._assert_tenth_found(c, "alias")
            self.assertIn("class alias _ring_door of SdkBackend", [how for _b, _ln, how, _f in c.door_value_sites])
        with self.subTest(alias="method default log=_log"):
            c = self._take(method_default)
            self._assert_tenth_found(c, "param")
            self.assertIn("parameter log of SdkBackend._tenth (default)", [how for _b, _ln, how, _f in c.door_value_sites])
        with self.subTest(alias="the lens's _ring, ApiHealth's deque"):
            c = self._take(lens_ring)
            self._assert_tenth_found(c, "alias")
            self.assertEqual(c.alias_collisions, {"_ring": ["ApiHealth._ring (an attribute bound in __init__)"]}, "the collision is recorded, not failed")
            self.assertEqual([dc.lineno for dc in c.door_calls if dc.kind == "alias" and dc.fn.cls is not None and dc.fn.cls.name == "ApiHealth"], [],
                             "ApiHealth's own self._ring uses are not door calls")

    def test_an_unbound_call_through_the_class_reads_the_message_after_self(self):
        """`SdkBackend._log(self, <env message>, problem=True, ring_text=...)` was caught at aa1037c8f by the unreduced
        set alone: the walk took `self` as the message and never read the row's taint. The binding is read from the
        receiver (a class name: unbound), so the message is the second positional and the row is a content row."""
        c = self._census(self._method("        SdkBackend._log(self, %s, problem=True, %s)" % (self.MSG, self.RING)))
        self._assert_tenth_found(c, "typed")
        self.assertEqual([dc.lineno for dc in c.unreduced if dc.owner == "_tenth"], [])

    def test_env_names_reach_a_seen_door_through_the_five_roads_the_lens_named_and_a_sixth(self):
        """Family B: the door call was COUNTED (doors 396, calls 331) and classed untainted at aa1037c8f when the env
        names reached it through a helper's dict return under another key, a list built by append in a loop, a string
        built by +=, an attribute stored in one method and read in another, or a module-level list's extend; the
        sixth is the same re-keying through a dict built in place. Each is a content row now. The ring text of each
        plant derives from the road's own value (a count of it), never from a source read directly, so the taint that
        makes the row a content row is the road's: with `len(sess.env_vars)` in the ring text the row would be tainted
        through the ring text whatever the message carried (the addendum's first draft measured four of the six roads
        green on the old census for that reason)."""
        roads = {
            "dict return under names": (lambda s: self._with_format(s).replace(self.METHOD_ANCHOR,
                '    def _tenth(self, sess):\n        info = _tenth_info(sess)\n        self._log("env (%s): tenth %s" % (sess.name, ", ".join(info["names"])), '
                'problem=True, ring_text=TENTH_RING % (sess.name[:20], len(info["names"])))\n\n' + self.METHOD_ANCHOR)
                + '\ndef _tenth_info(sess):\n    return {"names": sorted(sess.env_vars)}\n'),
            "append in a loop": (lambda s: self._with_format(s).replace(self.METHOD_ANCHOR,
                '    def _tenth(self, sess):\n        parts = []\n        for k in sess.env_vars:\n            parts.append(k)\n'
                '        self._log("env (%s): tenth %s" % (sess.name, ", ".join(parts)), problem=True, ring_text=TENTH_RING % (sess.name[:20], len(parts)))\n\n' + self.METHOD_ANCHOR)),
            "augmented assignment": (lambda s: self._with_format(s).replace(self.METHOD_ANCHOR,
                '    def _tenth(self, sess):\n        names = ""\n        for k in sess.env_vars:\n            names += k\n'
                '        self._log("env (%s): tenth %s" % (sess.name, names), problem=True, ring_text=TENTH_RING % (sess.name[:20], len(names)))\n\n' + self.METHOD_ANCHOR)),
            "attribute store read in another method": (lambda s: self._with_format(s).replace(self.METHOD_ANCHOR,
                '    def _tenth_store(self, sess):\n        self._tenth_names = sorted(sess.env_vars)\n\n'
                '    def _tenth(self, sess):\n        self._log("env (%s): tenth %s" % (sess.name, ", ".join(self._tenth_names)), problem=True, ring_text=TENTH_RING % (sess.name[:20], len(self._tenth_names)))\n\n' + self.METHOD_ANCHOR)),
            "module list extend": (lambda s: s.replace(self.FMT_ANCHOR, self.TENTH + "_TENTH_SEEN = []\n" + self.FMT_ANCHOR).replace(self.METHOD_ANCHOR,
                '    def _tenth(self, sess):\n        _TENTH_SEEN.extend(sorted(sess.env_vars))\n'
                '        self._log("env (%s): tenth %s" % (sess.name, ", ".join(_TENTH_SEEN)), problem=True, ring_text=TENTH_RING % (sess.name[:20], len(_TENTH_SEEN)))\n\n' + self.METHOD_ANCHOR)),
            "dict built in place, re-keyed": (lambda s: self._with_format(s).replace(self.METHOD_ANCHOR,
                '    def _tenth(self, sess):\n        info = _tenth_info(sess)\n        self._log("env (%s): tenth %s" % (sess.name, ", ".join(info["names"])), '
                'problem=True, ring_text=TENTH_RING % (sess.name[:20], len(info["names"])))\n\n' + self.METHOD_ANCHOR)
                + '\ndef _tenth_info(sess):\n    d = {}\n    d["names"] = sorted(sess.env_vars)\n    return d\n'),
        }
        results = self._censuses([self._spec(self._copy(edit)) for edit in roads.values()])
        for road, r in zip(roads, results):
            with self.subTest(road=road):
                self._assert_tenth_found(self._take(r), "self")

    def test_the_env_key_of_a_dict_return_stays_a_source_at_the_read_and_does_not_taint_the_dicts_other_keys(self):
        """The other boundary of the dict rule: a helper returning {"env": sess.env_vars, "mode": sess.mode} taints
        no reader of its "mode" key (the env key is a source at its own read), so the count does not move; and the launch
        shape, a source function returning a dict, taints `shape["mode"]` no more (before this rule the attributes
        stored from it cascaded env taint to 96 content rows)."""
        c = self._census(self._copy(lambda s: self._with_format(s).replace(self.METHOD_ANCHOR,
            '    def _tenth(self, sess):\n        info = _tenth_info(sess)\n        self._log("env (%s): tenth %s" % (sess.name, info["mode"]), problem=True, '
            'ring_text=TENTH_RING % (sess.name[:20], info["mode"]))\n\n' + self.METHOD_ANCHOR)
            + '\ndef _tenth_info(sess):\n    return {"env": sess.env_vars, "mode": sess.mode}\n'))
        self.assertEqual(c.failures, [])
        self.assertEqual(len(c.content_rows), self.BASE)
        self.assertEqual([sorted(dc.taint) for dc in c.door_calls if dc.owner == "_tenth"], [[]])
        head = census(CENSUS_FILES)
        shape = [f for f in head.all_fns if f.qual == "SdkBackend._launch_shape"][0]
        self.assertTrue(head._returns_dicts(shape), "the launch shape returns a dict: a source at its env key, not whole")
        self.assertEqual(sorted(a for a, t in head.attr_taint.items() if "env" in t), ["_launched_env", "env_vars"],
                         "the env-tainted attributes at this head are the two env source attributes themselves")

    def test_the_doors_name_as_a_string_outside_getattr_is_a_failure(self):
        """Reflection: `log=operator.attrgetter("_log")(self)` bound a planted helper to the door with the walk seeing
        no door at all (doors 395, content 9, failures none at aa1037c8f). Every string constant spelling the door's
        name outside the one getattr form the walk follows is a failure named by site, as is one spelling the ring's;
        the module constant `LOG_ATTR = "_log"` handed to getattr is the same failure at the constant."""
        helper = '\ndef _tenth_helper(sess, log=None):\n    log(%s, problem=True, %s)\n' % (self.MSG, self.RING)
        attrgetter, constant, ring_name, followed = self._censuses([
            self._spec(self._copy(lambda s: "import operator\n" + self._with_format(s).replace(self.METHOD_ANCHOR,
                '    def _tenth(self, sess):\n        _tenth_helper(sess, log=operator.attrgetter("_log")(self))\n\n' + self.METHOD_ANCHOR) + helper)),
            self._spec(self._copy(lambda s: s.replace(self.FMT_ANCHOR, 'LOG_ATTR = "_log"\n' + self.TENTH + self.FMT_ANCHOR).replace(self.METHOD_ANCHOR,
                '    def _tenth(self, sess):\n        _tenth_helper(sess, log=getattr(self, LOG_ATTR, None))\n\n' + self.METHOD_ANCHOR) + helper)),
            self._spec(self._method('        getattr(self, "_problems").append({"text": "x"})')),
            self._spec(self._copy(lambda s: self._with_format(s).replace(self.METHOD_ANCHOR,
                '    def _tenth(self, sess):\n        _tenth_helper(sess, log=getattr(self, "_log", None))\n\n' + self.METHOD_ANCHOR) + helper))])
        with self.subTest(road="attrgetter"):
            c = self._take(attrgetter)
            self.assertEqual([(k, b, t.split(":")[0]) for k, b, _ln, t in c.failures], [("door-name-string", "sdk_backend.py", "the door's name '_log' is a string outside getattr(x, '_log')")])
            self.assertIn('attrgetter', c.failures[0][3])
            self.assertEqual([dc.owner for dc in c.door_calls if dc.owner in ("_tenth", "_tenth_helper")], [], "the door itself is invisible, which is why the string must be loud")
        with self.subTest(road="a module constant naming the attribute"):
            c = self._take(constant)
            self.assertEqual([(k, b) for k, b, _ln, _t in c.failures], [("door-name-string", "sdk_backend.py")])
        with self.subTest(road="the ring's name as a string"):
            c = self._take(ring_name)
            self.assertIn(("ring-name-string", "sdk_backend.py"), [(k, b) for k, b, _ln, _t in c.failures])
        with self.subTest(road="the followed form is no failure"):
            c = self._take(followed)
            self.assertEqual(c.failures, [])
            self.assertIn(("_tenth_helper", "TENTH_RING", False), c.content_identities())

    def test_a_second_writer_of_the_ring_is_a_census_error_and_the_heads_own_references_pass(self):
        """Family C: the ring the dashboard reads gained a row from kernel.py (`be._problems.append`), from a session
        (`self.backend._problems.append`) and from a second SdkBackend method (`self._problems.insert(0, ...)`) with
        the census at its baseline, because the writer was found by one shape and every other touch of the ring went
        unread. Every reference to `_problems` on any receiver in the files is classified now: a second appender, any
        other mutation, an alias, a return, a store outside __init__ or a touch outside the writer's class is a
        CensusError naming the site; the head's own seven references (the __init__ binding, the writer's repeat lookup,
        append and trim, problems()' copy, problem_keyed()'s scan) pass."""
        row = '{"seq": 0, "t": 0, "text": "env (%s): tenth %s" % (sess.name, ", ".join(sess.env_vars))}'
        cases = {
            "kernel-side be._problems.append": (lambda: self._spec(self.small_path, self._plant("plant.py", "def tenth(be, sess):\n    be._problems.append(%s)\n" % row)), "2 appenders"),
            "a session's self.backend._problems.append": (lambda: self._spec(self._copy(lambda s: s.replace(self.SESSION_ANCHOR,
                "    def _tenth(self, sess):\n        self.backend._problems.append(%s)\n\n" % row + self.SESSION_ANCHOR))), "2 appenders"),
            "a second method's self._problems.insert": (lambda: self._spec(self._method("        self._problems.insert(0, %s)" % row)), "mutated other than by the writer's append"),
            "an alias of the ring": (lambda: self._spec(self._method('        rows = self._problems\n        rows.append({"text": "x"})')), "read where the walk cannot follow"),
            "the ring returned": (lambda: self._spec(self._method("        return self._problems")), "read where the walk cannot follow"),
            "the ring rebound outside __init__": (lambda: self._spec(self._method("        self._problems = []")), "rebound outside __init__"),
            "a foreign class reading it": (lambda: self._spec(self._copy(lambda s: s.replace(self.SESSION_ANCHOR,
                "    def _tenth(self):\n        return len(self.backend._problems)\n\n" + self.SESSION_ANCHOR))), "touched outside its writer's class"),
        }
        results = self._censuses([spec() for spec, _words in cases.values()])
        for (label, (_spec, words)), r in zip(cases.items(), results):
            with self.subTest(case=label):
                with self.assertRaises(CensusError) as cm:
                    self._take(r)
                self.assertIn(words, str(cm.exception))
        head = census(CENSUS_FILES)
        refs = [(mod.base, node.lineno, fn.qual if fn else None) for mod, node, fn in head.ring_refs]
        self.assertEqual(len(refs), 7, refs)
        self.assertEqual({q for _b, _ln, q in refs}, {"SdkBackend.__init__", "SdkBackend._log", "SdkBackend.problems", "SdkBackend.problem_keyed"})
        self.assertEqual({b for b, _ln, _q in refs}, {"sdk_backend.py"})

    def test_a_feeder_list_adding_by_insert_extend_or_augmented_assignment_is_a_feeder_append(self):
        """The same family on the kernel's side: _sdk_problem_rows' lists took rows by `append` alone in the census's
        eyes. A synthetic module standing in for kernel.py (its own _sdk_problem_rows reading a module list) adds by
        insert, by extend and by +=, and each is a feeder append whose row text is read."""
        adds = (("insert", 'ROWS.insert(0, {"text": "env (%s): tenth %s" % (sess.name, ", ".join(sess.env_vars))})'),
                ("extend", 'ROWS.extend([{"text": "env (%s): tenth %s" % (sess.name, ", ".join(sess.env_vars))}])'),
                ("augmented assignment", 'ROWS += [{"text": "env (%s): tenth %s" % (sess.name, ", ".join(sess.env_vars))}]'))
        results = self._censuses([self._spec(self.small_path, self._plant("plant.py", "ROWS = []\ndef _sdk_problem_rows():\n    return list(ROWS)\ndef feed(sess):\n    %s\n" % stmt))
                                  for _how, stmt in adds])
        for (how, _stmt), r in zip(adds, results):
            with self.subTest(how=how):
                c = self._take(r)
                self.assertEqual([(fn.name, lst) for fn, _c, lst in c.feeder_appends if fn.base == "plant.py"], [("feed", "ROWS")])
                planted = [dc for dc in c.door_calls if dc.base == "plant.py"]
                self.assertEqual([(dc.kind, sorted(dc.taint), dc.problem_decl) for dc in planted], [("feeder-append:ROWS", ["env"], ("const", True))])
                self.assertEqual([w.split(" to ")[0] for dc, w in c.explicit_violations if dc.base == "plant.py"], ["problem=True with a ring text that reduces"])

    def test_reduction_follows_a_conduit_to_its_sites_and_an_fstring_to_its_leading_text(self):
        """The round-6 mutation pass applied no mutation that breaks reduction alone. A synthetic conduit `relay(be, m)`
        with one literal site and one run-time site: the inner call's heads are the literal site's, the run-time site
        is unreduced and the inner call is not; with every site run-time the inner call is unreduced too. And the
        small module's crash line (the head's shape, an f-string whose leading text the census reads; EnvRowsPopulation
        holds the head's own line to its head) with its leading text removed joins the unreduced set, so its reduction is
        shown to rest on that text."""
        plant = ("def relay(be, m):\n    be._log(m)\n"
                 "def a(be):\n    relay(be, 'x: literal')\n"
                 "def b(be, e):\n    relay(be, str(e))\n")
        path = self._copy(lambda s: s.replace(self.CRASH_ANCHOR, '_log(f"{self.name} crashed: '))
        c, c2, c3 = (self._take(r) for r in self._censuses([self._spec(self.small_path, self._plant("plant.py", plant)),
                                                             self._spec(self.small_path, self._plant("plant.py", plant.replace("'x: literal'", "repr(be)"))),
                                                             self._spec(path)]))
        inner = [dc for dc in c.door_calls if dc.base == "plant.py" and dc.kind == "typed"]
        self.assertEqual([(dc.owner, dc.heads, dc.unreduced) for dc in inner], [("relay", ["x: literal"], False)])
        sites = sorted((dc.owner, dc.heads, dc.unreduced) for dc in c.door_calls if dc.base == "plant.py" and dc.kind == "conduit:relay")
        self.assertEqual(sites, [("a", ["x: literal"], False), ("b", [], True)])
        self.assertEqual(sorted((dc.owner, dc.unreduced) for dc in c2.door_calls if dc.base == "plant.py"), [("a", True), ("b", True), ("relay", True)])
        line = [i + 1 for i, ln in enumerate(Path(path).read_text(encoding="utf-8").splitlines()) if '_log(f"{self.name} crashed: ' in ln]
        self.assertEqual(len(line), 1)
        self.assertIn(line[0], [dc.lineno for dc in c3.unreduced if dc.base == "sdk_backend.py"], "the crash line's reduction rests on its leading text")
        self.assertEqual(len([dc for dc in c3.unreduced if dc.base == "sdk_backend.py"]), len(self.small.unreduced) + 1,
                         "the small module's own unreduced calls (none, asserted at its construction) plus the crash line")

    # Ruling 2 of review round 6: a dict-returning SOURCE whose env value reaches a different key than the one it entered
    # at. Each variant is the body of `_tenth_shape(<param>)` after `e = <origin>` (`%(P)s` a second read of the
    # parameter), with the reader's expression over the returned `shape`; (f) and (j) below need a second function.
    REKEYS = {
        "a: a copy under a second key": ('    d = {"env": e}\n    d["opts"] = d["env"]\n    return d\n', 'shape["opts"]'),
        "b: a non-source key from the start": ('    return {"opts": e}\n', 'shape["opts"]'),
        "c: a pop into a new literal": ('    d = {"env": e, "mode": %(P)s}\n    return {"mode": d["mode"], "opts": d.pop("env")}\n', 'shape["opts"]'),
        "d: an update with a keyword": ('    d = {"env": e}\n    d.update(opts=d["env"])\n    return d\n', 'shape["opts"]'),
        "e: a splat beside a re-key": ('    d = {"env": e}\n    return {**d, "opts": d["env"]}\n', 'shape["opts"]'),
        "g: nested under another key": ('    return {"inner": {"env": e}}\n', 'shape["inner"]["env"]'),
        "h: a local alias of the key's read": ('    d = {"env": e}\n    x = d["env"]\n    return {"opts": x}\n', 'shape["opts"]'),
        "i: a comprehension renaming the keys": ('    d = {"env": e}\n    return {("opts" if k == "env" else k): v for k, v in d.items()}\n', 'shape["opts"]'),
    }
    CHAIN = "f: a chain, the re-key by pop in a helper"
    HELD = "j: the value held on an attribute, re-keyed by another method"
    # the two forms: the function DECLARED a source (DEFAULT_SOURCES' func entry) whose origin is a parameter's key, no
    # source read, so only the declaration can taint it; and an undeclared helper whose origin is a source read
    FORMS = {"declared": ("raw", 'raw["vars"]', 'raw["mode"]'), "helper": ("sess", "sess.env_vars", "sess.mode")}
    # quiet before this commit (the census at the round-6 addendum, run over these same plants): the declaration was
    # dropped for a dict returner, so an origin that was no source read reached another key clean, and a pop of the
    # key was no read of it
    QUIET_BEFORE = {("b: a non-source key from the start", "declared"), ("c: a pop into a new literal", "declared"),
                    ("i: a comprehension renaming the keys", "declared"), (CHAIN, "declared"), (CHAIN, "helper"), (HELD, "declared")}

    def _reader(self, arg, expr):
        """The SdkBackend method reading the moved key and writing the tenth row from it; its ring text derives from the
        moved value alone, so the taint that makes it a content row is the road's."""
        return ('    def _tenth(self, sess, raw):\n        shape = %s\n        self._log("env (%%s): tenth %%s" %% (sess.name, ", ".join(%s)), '
                'problem=True, ring_text=TENTH_RING %% (sess.name[:20], len(%s)))\n\n' % (arg, expr, expr))

    def _declared(self):
        declared = copy.deepcopy(DEFAULT_SOURCES)
        declared["func"][("sdk_backend.py", "_tenth_shape")] = "env"
        declared["func"][("sdk_backend.py", "SdkBackend._tenth_shape")] = "env"
        return declared

    def test_a_dict_returning_source_that_moves_the_env_to_another_key_is_caught_by_the_value_not_the_key(self):
        """Ruling 2 of review round 6 (2026-09-19): the source-function-dict rule (a source whose returns are dicts is a
        source at its env key, not whole) moves the census off the over-approximating side, so it is run against the
        case it admits: dict-returning sources where the env value reaches a DIFFERENT key than the one it entered at,
        by a copy or a re-key inside the function, with a reader taking the moved key and writing a ring row from it.
        Ten variants in two forms each (the function declared a source with a parameter for its origin, and an
        undeclared helper reading a source), twenty plants: every one is a tenth content row now (the identity pin
        reds), and the six QUIET_BEFORE names were quiet on the census before this commit. The rule as it now is: the
        value a declared dict source stores under the source key is the env BY DECLARATION, so the Name or attribute
        it is stored from and the dict holding it carry the tag whole while the dict's boundary still excludes the key;
        a return in which the census cannot locate the key (no source key in the literal, a comprehension, a local
        nothing stored the key into) is tainted whole; and `.pop("env")` reads the key like `.get`. The refusal side:
        the head's two dict-returning sources are located at their env key, their returns carry no env whole (so
        `shape["mode"]` stays clean and the 96 content rows and 267 violations of the addendum's first census stay
        gone), and the head reads BASE content rows, violations 0."""
        declared = self._declared()
        plants = []       # (variant, form, spec) in the order the subTests run
        for label, (body, expr) in self.REKEYS.items():
            for form, (param, origin, mode) in self.FORMS.items():
                fn = "\ndef _tenth_shape(%s):\n    e = %s\n%s" % (param, origin, body % {"P": mode})
                plants.append((label, form, ((self._copy(lambda s: self._with_format(s).replace(
                    self.METHOD_ANCHOR, self._reader("_tenth_shape(%s)" % param, expr) + self.METHOD_ANCHOR) + fn),),
                    declared if form == "declared" else DEFAULT_SOURCES)))
        chain = 'def _tenth_rekey(d):\n    x = d.pop("env")\n    return {"opts": x}\n'
        for form, (param, origin, _mode) in self.FORMS.items():
            sources = declared if form == "declared" else DEFAULT_SOURCES
            fn = '\ndef _tenth_shape(%s):\n    e = %s\n    d = {"env": e}\n    return d\n' % (param, origin) + chain
            plants.append((self.CHAIN, form, ((self._copy(lambda s: self._with_format(s).replace(
                self.METHOD_ANCHOR, self._reader("_tenth_rekey(_tenth_shape(%s))" % param, 'shape["opts"]') + self.METHOD_ANCHOR) + fn),), sources)))
            methods = ('    def _tenth_shape(self, %s):\n        self._tenth_held = %s\n        return {"env": self._tenth_held}\n\n'
                       '    def _tenth_other(self):\n        return {"opts": self._tenth_held}\n\n' % (param, origin))
            plants.append((self.HELD, form, ((self._copy(lambda s: self._with_format(s).replace(
                self.METHOD_ANCHOR, methods + self._reader("self._tenth_other()", 'shape["opts"]') + self.METHOD_ANCHOR)),), sources)))
        loud = set()
        for (label, form, _spec), r in zip(plants, self._censuses([spec for _label, _form, spec in plants])):
            with self.subTest(variant=label, form=form):
                self._assert_tenth_found(self._take(r), "self")
                loud.add((label, form))
        self.assertEqual(len(loud), 20)
        self.assertTrue(self.QUIET_BEFORE <= loud, "every variant quiet before this commit is loud now")
        head = census(CENSUS_FILES)
        for q in ("SdkBackend._launch_shape", "SdkSession._launched_shape"):
            f = [x for x in head.all_fns if x.qual == q][0]
            self.assertEqual(head._declared_dict_source(f), "env", q)
            self.assertTrue(f.returns and all(head._locates_source_key(r, f) for r in f.returns), "%s is located at its env key" % q)
            self.assertFalse(any("env" in v for v in head.ret_taint.get(f, {}).values()), "%s's return carries no env whole" % q)
        self.assertEqual(len(head.content_rows), len(ROWS))
        self.assertEqual(head.explicit_violations, [])

    def test_a_twice_bound_alias_name_is_resolved_by_the_receivers_scope_and_fails_only_untyped(self):
        """Ruling 4 of review round 6 (2026-09-19): a class alias of the door whose name another class also binds (the
        lens's `_ring = _log` in SdkBackend beside ApiHealth's `self._ring` deque) is two bindings the AST tells apart by
        scope, so the census disambiguates before any product rename. Every arm: `self.<name>` in the alias's class or a
        subclass through the MRO is the alias (a content row, kind alias; the identity pin reds); `self.<name>` in
        ApiHealth is its own deque (no door); a receiver typed by an annotation (`be: SdkBackend`, the string form), by a
        constructor call (`h = ApiHealth(...)`) or by a `self.<attr>` bound in __init__ from one (`self.backend` in a
        session) resolves by its class; an untyped receiver where both bindings could apply is the loud
        door-alias-ambiguous failure whose remedy names both bindings, and the call is not counted as a door. In every
        arm ApiHealth's own uses stay no door, and where the call resolves to the other binding the alias is called
        nowhere, which is its own failure. Which it is at this head: product code binds no alias of the door at class or
        module scope in the three files (the census's tables and a line scan agree), so no rename was needed, and the
        census can tell the two bindings apart by scope."""
        alias = "    _ring = _log\n\n"
        call = lambda recv, indent: "%s%s._ring(%s, problem=True, %s)\n" % (indent, recv, self.MSG, self.RING)

        def plant(backend="", session="", api="", tail=""):
            return self._copy(lambda s: self._with_format(s).replace(self.METHOD_ANCHOR, alias + backend + self.METHOD_ANCHOR)
                              .replace(self.SESSION_ANCHOR, session + self.SESSION_ANCHOR).replace(self.API_ANCHOR, api + self.API_ANCHOR) + tail)

        def api_doors(c):
            return [dc.lineno for dc in c.door_calls if dc.kind == "alias" and dc.fn.cls is not None and dc.fn.cls.name == "ApiHealth"]

        doors = {
            "self in the alias's class": dict(backend="    def _tenth(self, sess):\n" + call("self", " " * 8) + "\n"),
            "self in a subclass through the MRO": dict(tail="\nclass _TenthBackend(SdkBackend):\n    def _tenth(self, sess):\n" + call("self", " " * 8)),
            "a parameter annotated with the class": dict(tail="\ndef _tenth(be: SdkBackend, sess):\n" + call("be", " " * 4)),
            "a string annotation": dict(tail='\ndef _tenth(be: "SdkBackend", sess):\n' + call("be", " " * 4)),
            "self.backend in a session, typed by its __init__": dict(session="    def _tenth(self, sess):\n" + call("self.backend", " " * 8) + "\n"),
        }
        uncalled = ("door-escapes", "sdk_backend.py", "class alias _ring of SdkBackend is never called")
        others = {
            "self in ApiHealth, its own deque": dict(api="    def _tenth(self, sess):\n" + call("self", " " * 8) + "\n"),
            "a parameter annotated with ApiHealth": dict(tail="\ndef _tenth(h: ApiHealth, sess):\n" + call("h", " " * 4)),
            "a local assigned from ApiHealth's constructor": dict(tail="\ndef _tenth(state_dir, sess):\n    h = ApiHealth(state_dir)\n" + call("h", " " * 4)),
        }
        untyped = (("an untyped receiver calling the name", "\ndef _tenth(x, sess):\n" + call("x", " " * 4)),
                   ("an untyped receiver using the deque", "\ndef _tenth(x, ev):\n    x._ring.append(ev)\n"))
        built = iter(self._censuses([self._spec(plant(**kw)) for kw in doors.values()] + [self._spec(plant(**kw)) for kw in others.values()]
                                    + [self._spec(plant(tail=tail)) for _label, tail in untyped]
                                    + [self._spec(self._copy(lambda s: self._with_format(s).replace(self.METHOD_ANCHOR, "    _ring_door = _log\n\n" + self.METHOD_ANCHOR)
                                                             + "\ndef _tenth(x, sess):\n    x._ring_door(%s, problem=True, %s)\n" % (self.MSG, self.RING)))]))
        for label, kw in doors.items():
            with self.subTest(arm=label):
                c = self._take(next(built))
                self._assert_tenth_found(c, "alias")
                self.assertEqual(c.alias_collisions, {"_ring": ["ApiHealth._ring (an attribute bound in __init__)"]})
                self.assertEqual(api_doors(c), [], "ApiHealth's own self._ring uses are no door")
        for label, kw in others.items():
            with self.subTest(arm=label):
                c = self._take(next(built))
                self.assertEqual([(k, b, t) for k, b, _ln, t in c.failures], [uncalled], "the call is the other binding's, so the alias is called nowhere")
                self.assertEqual([dc.lineno for dc in c.door_calls if dc.owner == "_tenth"], [])
                self.assertEqual(api_doors(c), [])
                self.assertEqual(len(c.content_rows), self.BASE)
        for label, _tail in untyped:
            with self.subTest(arm=label):
                c = self._take(next(built))
                self.assertEqual([(k, b) for k, b, _ln, _t in c.failures], [("door-alias-ambiguous", "sdk_backend.py"), ("door-escapes", "sdk_backend.py")])
                text = c.failures[0][3]
                self.assertIn("x._ring in _tenth: the receiver is untyped", text)
                self.assertIn("SdkBackend._ring (a class-body alias of the door, line", text)
                self.assertIn("ApiHealth._ring (an attribute bound in __init__)", text)
                self.assertIn("type the receiver", text)
                self.assertEqual([dc.lineno for dc in c.door_calls if dc.owner == "_tenth"], [], "not counted as a door: named as a failure instead")
                self.assertEqual(len(c.content_rows), self.BASE)
        with self.subTest(arm="an untyped receiver of a name bound once resolves to the alias, as before"):
            c = self._take(next(built))
            self._assert_tenth_found(c, "alias")
        head = census(CENSUS_FILES)
        self.assertEqual((head.class_alias_doors, head.module_alias_doors, head.alias_collisions), ({}, {}, {}),
                         "product code binds no alias of the door at class or module scope: no rename is needed at this head")
        pat = re.compile(r"^\s*[A-Za-z_][A-Za-z0-9_]*\s*(:[^=]+)?=\s*(_log|SdkBackend\._log|getattr\(SdkBackend,\s*['\"]_log['\"]\))\s*(#.*)?$")
        for path in CENSUS_FILES:
            hits = [i + 1 for i, ln in enumerate(Path(path).read_text(encoding="utf-8").splitlines()) if pat.match(ln)]
            self.assertEqual(hits, [], "%s binds an alias of the door at line(s) %r" % (os.path.basename(path), hits))


    # ---- the addendum's replays (the round-6 rulings' lenses, 2026-09-19): a plant per quiet pass, each loud now ----

    def _shape_spec(self, form, body=None, expr='shape["opts"]', methods="", extra="", arg=None):
        """The spec of a module copy planted the way the ruling-2 test plants: TENTH_RING, a reader SdkBackend._tenth writing the tenth
        row from `expr` over `shape = <arg>`, and `_tenth_shape(<param>)` whose body follows `e = <origin>` (declared
        form: the parameter's key, declared a source; helper form: a source read under DEFAULT_SOURCES); `%(P)s` a second
        read of the parameter, `%(O)s` the origin, `%(PARAM)s` the parameter's name."""
        param, origin, mode = self.FORMS[form]
        sub = {"P": mode, "O": origin, "PARAM": param}
        fn = "" if body is None else "\ndef _tenth_shape(%s):\n    e = %s\n%s" % (param, origin, body % sub)
        arg = (arg or "_tenth_shape(%(PARAM)s)") % sub
        path = self._copy(lambda s: self._with_format(s).replace(
            self.METHOD_ANCHOR, (methods % sub) + self._reader(arg, expr % sub) + self.METHOD_ANCHOR) + fn + (extra % sub))
        return ((path,), self._declared() if form == "declared" else DEFAULT_SOURCES)

    def _shape_census(self, form, **kw):
        return self._take(self._censuses([self._shape_spec(form, **kw)])[0])

    def _assert_tenth_quiet(self, c):
        """The refusal side of a rule: the plant is read, nothing fails, and the tenth row carries no env (BASE rows)."""
        self.assertEqual(c.failures, [])
        self.assertEqual(len(c.content_rows), self.BASE)
        self.assertEqual([sorted(dc.taint) for dc in c.door_calls if dc.owner == "_tenth"], [[]])

    def test_the_env_under_the_source_key_is_followed_to_its_roots_so_a_second_road_to_the_value_carries_it(self):
        """Ruling 2's lens (2026-09-19): the declaration marked the value under the source key when it was a bare Name or
        attribute, so any other shape of the same value under another key crossed clean while the return was located:
        the origin read twice (ai), two locals from one origin (aj), `e or {}` (ak), `dict(e)` (al), a comprehension over
        it, the launch shape's own form (am), a tuple index (an), a walrus (ac), and a namedtuple or holder class built
        from it (r, s), seven of them quiet in the declared form. The taint follows the value to its ROOTS now (the Names,
        attribute chains and constant-keyed subscripts it derives from, a local followed to its assignments, a constructor's
        arguments), so each is a tenth content row. The store forms the declaration reads are pinned one by one, each the
        only road to the value (the return located by a literal holding an empty env): `dict(env=e)`, `d.update(env=e)`,
        `d.setdefault("env", e)`, `d.__setitem__("env", e)`, `operator.setitem(d, "env", e)`, `d["env"] = e`, and the bare
        Name store (a copy from the Name itself). Declared form: only the declaration can taint these."""
        plants = {
            "ai: the origin read twice, under env and under opts": ('    return {"env": %(O)s, "opts": %(O)s}\n', ""),
            "aj: two locals from the origin": ('    f = %(O)s\n    return {"env": e, "opts": f}\n', ""),
            "ak: e or {} under env, e under opts": ('    return {"env": e or {}, "opts": e}\n', ""),
            "al: dict(e) under env, e under opts": ('    return {"env": dict(e), "opts": e}\n', ""),
            "am: a comprehension over e under env, e under opts": ('    return {"env": {k: v for k, v in e.items() if k}, "opts": e}\n', ""),
            "an: a tuple index under both keys": ('    t = (e,)\n    return {"env": t[0], "opts": t[0]}\n', ""),
            "ac: a walrus under env, its target under opts": ('    return {"env": (x := e), "opts": x}\n', ""),
            "r: a namedtuple built from e, one field under each key": ('    p = _TenthPair(e, e)\n    return {"env": p.left, "opts": p.right}\n',
                                                                       '\nimport collections\n_TenthPair = collections.namedtuple("_TenthPair", "left right")\n'),
            "s: a holder class built from e, one attribute under each key": ('    b = _TenthBox(e, e)\n    return {"env": b.left, "opts": b.right}\n',
                                                                             '\nclass _TenthBox:\n    def __init__(self, left, right):\n        self.left = left\n        self.right = right\n'),
            "store: dict(env=e)": ('    return dict(env=e, opts=e)\n', ""),
            "store: d.update(env=e)": ('    d = {"env": {}, "mode": %(P)s}\n    d.update(env=e)\n    d["opts"] = e\n    return d\n', ""),
            "store: d.setdefault(env, e)": ('    d = {"env": {}, "mode": %(P)s}\n    d.setdefault("env", e)\n    d["opts"] = e\n    return d\n', ""),
            "store: d.__setitem__(env, e)": ('    d = {"env": {}, "mode": %(P)s}\n    d.__setitem__("env", e)\n    d["opts"] = e\n    return d\n', ""),
            "store: operator.setitem(d, env, e)": ('    d = {"env": {}, "mode": %(P)s}\n    operator.setitem(d, "env", e)\n    d["opts"] = e\n    return d\n', "\nimport operator\n"),
            "store: d[env] = e": ('    d = {"env": {}, "mode": %(P)s}\n    d["env"] = e\n    d["opts"] = e\n    return d\n', ""),
            "store: the Name itself copied": ('    d = {"env": e}\n    d["opts"] = e\n    return d\n', ""),
            # the holder's whole mark (m2e), the only road when the value under the key has no root the walk reaches (a
            # call into a function of the files) and the holder is used whole under another key
            "holder: a dict holding a value the roots cannot reach, used whole": ('    d = {"env": _tenth_make(e)}\n    return {"env": {}, "opts": list(d.values())}\n',
                                                                                    "\ndef _tenth_make(x):\n    return dict(x)\n"),
        }
        results = self._censuses([self._shape_spec("declared", body, extra=extra) for body, extra in plants.values()])
        for label, r in zip(plants, results):
            with self.subTest(variant=label):
                self._assert_tenth_found(self._take(r), "self")

    def test_nested_targets_lambdas_generators_and_reflected_stores_carry_the_env_with_the_value(self):
        """Ruling 2's lens, the mechanics the value crossed by: a nested tuple target (`(k, v), = d.items()`,
        `for i, (k, v) in enumerate(d.items())`, `*_rest, (k, v) = list(d.items())`), which a one-level flatten left
        unbound; a re-key through a for over items into a dict built in place; a lambda bound to a local and called by
        its name; a generator's yield fed to dict(); `operator.setitem`; a value held by `setattr(self, "n", e)` or
        `self.__dict__["n"] = e` and re-keyed by another method; the source called through `getattr(self, "name")(...)`;
        and the reader reading the attribute source by `getattr(sess, "env_vars")` or `vars(sess)["env_vars"]`. Each in
        the forms the lens ran it in, each a tenth content row: the target is flattened to its leaves, a yield is a
        return, a lambda is its local's callee, a spelled reflection is read as the attribute or the call it names."""
        both = {
            "k: (k, v), = d.items()": dict(body='    d = {"env": e}\n    (k, v), = d.items()\n    return {"env": e, "opts": v}\n'),
            "x: for i, (k, v) in enumerate(d.items())": dict(body='    d = {"env": e}\n    out = {"env": e}\n    for i, (k, v) in enumerate(d.items()):\n        out["opts"] = v\n    return out\n'),
            "bc: *_rest, (k, v) = list(d.items())": dict(body='    d = {"env": e}\n    *_rest, (k, v) = list(d.items())\n    return {"env": e, "opts": v}\n'),
            "w: a for over items re-keying into a dict built in place": dict(body='    d = {"env": e}\n    out = {}\n    for k, v in d.items():\n        out["opts" if k == "env" else k] = v\n    return out\n'),
            "u: a lambda bound to a local, called by its name": dict(body='    f = lambda: {"opts": e}\n    return {"env": e, **f()}\n'),
            "v: a generator yielding the pair, fed to dict()": dict(body='    def _gen():\n        yield ("opts", e)\n    return {"env": e, **dict(_gen())}\n'),
            "ao: operator.setitem re-keying": dict(body='    d = {"env": e}\n    operator.setitem(d, "opts", e)\n    return d\n', extra="\nimport operator\n"),
            "ap: setattr holding the value, re-keyed by another method": dict(
                methods='    def _tenth_shape(self, %(PARAM)s):\n        e = %(O)s\n        setattr(self, "_tenth_held", e)\n        return {"env": e}\n\n'
                        '    def _tenth_other(self):\n        return {"opts": self._tenth_held}\n\n', arg="self._tenth_other()"),
            "aq: self.__dict__ holding the value, re-keyed by another method": dict(
                methods='    def _tenth_shape(self, %(PARAM)s):\n        e = %(O)s\n        self.__dict__["_tenth_held"] = e\n        return {"env": e}\n\n'
                        '    def _tenth_other(self):\n        return {"opts": self._tenth_held}\n\n', arg="self._tenth_other()"),
            "ae: the source called through getattr by the reader": dict(
                methods='    def _tenth_shape(self, %(PARAM)s):\n        e = %(O)s\n        return {"env": e, "opts": e}\n\n',
                arg='getattr(self, "_tenth_shape")(%(PARAM)s)'),
        }
        reads = (("ax: the reader reads getattr(sess, 'env_vars')", 'getattr(sess, "env_vars")'),
                 ("ay: the reader reads vars(sess)['env_vars']", 'vars(sess)["env_vars"]'))
        built = iter(self._censuses([self._shape_spec(form, **kw) for kw in both.values() for form in self.FORMS]
                                    + [self._shape_spec("helper", arg=arg, expr="shape") for _label, arg in reads]))
        for label, kw in both.items():
            for form in self.FORMS:
                with self.subTest(variant=label, form=form):
                    self._assert_tenth_found(self._take(next(built)), "self")
        for label, _arg in reads:
            with self.subTest(variant=label, form="helper"):
                self._assert_tenth_found(self._take(next(built)), "self")

    def test_a_whole_value_use_of_a_dict_sources_return_reads_the_env_and_a_keyed_read_reads_its_own_key(self):
        """The bound the ruling-2 commit disclosed (a whole-value use of a dict source's return, `str(shape)` or
        `shape.values()`, outside the census) is inside it now: a value has a WHOLE set and a CARRIED set (what a read of one
        non-source key yields), for a local, a parameter, a return and an attribute alike, so `str(shape)`, `shape.values()`
        and a whole dict held on an attribute carry the env while `shape["mode"]`, `.get`, `.pop` and `.setdefault` of another
        key, `(shape or {}).get("mode")` and a scalar attribute stored from a keyed read stay clean, and the head stays at BASE
        (the first draft gave every attribute a whole set and read 95 content rows, since attributes are keyed by name across
        every receiver; an attribute takes a whole set only from a dict by shape). The refusal side of the ruling-2 rule is
        pinned beside it: the located local's boundary excludes the key (m2k); a holder found through a conditional is located
        (m2i); `os.environ` is nobody's per-session source (ah). And the three unpinned branches of the location test, each
        loud as the whole return: a local nothing stored the key into (m2g2), a conditional with one branch unlocated (m2g3),
        a dict(...) call without the key (m2g4)."""
        shape = '    return {"env": e, "mode": %(P)s}\n'
        loud = {
            "av: sorted(str(shape))": dict(body=shape, expr="sorted(str(shape))"),
            "aw: list(shape.values())": dict(body=shape, expr="list(shape.values())"),
            "the return held whole on an attribute, read whole by another method": dict(
                body=shape, methods='    def _tenth_hold(self, %(PARAM)s):\n        self._tenth_shape_held = _tenth_shape(%(PARAM)s)\n\n',
                arg="self._tenth_shape_held", expr="sorted(str(shape))"),
            "the return passed whole to a helper that stringifies it": dict(
                body=shape, extra="\ndef _tenth_text(d):\n    return str(d)\n", expr="sorted(_tenth_text(shape))"),
        }
        quiet = {
            "shape[mode]": dict(body=shape, expr='shape["mode"]'),
            "shape.get(mode)": dict(body=shape, expr='str(shape.get("mode"))'),
            "shape.setdefault(mode, None)": dict(body=shape, expr='str(shape.setdefault("mode", None))'),
            "shape.pop(mode, None)": dict(body=shape, expr='str(shape.pop("mode", None))'),
            "(shape or {}).get(mode)": dict(body=shape, expr='str((shape or {}).get("mode"))'),
            "a scalar attribute stored from a keyed read": dict(
                body=shape, methods='    def _tenth_hold(self, %(PARAM)s):\n        self._tenth_mode = _tenth_shape(%(PARAM)s)["mode"]\n\n',
                arg="self._tenth_mode", expr="str(shape)"),
            "m2k: the located local's boundary excludes the key": dict(body='    d = {"env": e, "mode": %(P)s}\n    return d\n', expr='shape["mode"]'),
            "m2i: a holder found through a conditional is located": dict(
                body='    d = {"env": {}, "mode": %(P)s} if %(P)s else {"env": {}}\n    d["opts"] = e\n    return d\n'),
            "ah: os.environ under another key is no per-session source": dict(body='    return {"env": e, "opts": os.environ.copy()}\n'),
        }
        unlocated = {
            "m2g2: a local nothing stored the key into": '    d = {"mode": %(P)s}\n    d["opts"] = e\n    return d\n',
            "m2g3: a conditional with one branch unlocated": '    return {"env": {}, "mode": %(P)s} if %(P)s else {"opts": e}\n',
            "m2g4: a dict(...) call without the key": '    return dict(mode=%(P)s, opts=e)\n',
        }
        built = iter(self._censuses([self._shape_spec(form, **kw) for kw in loud.values() for form in self.FORMS]
                                    + [self._shape_spec("declared", **kw) for kw in quiet.values()]
                                    + [self._shape_spec("declared", body) for body in unlocated.values()]))
        for label, kw in loud.items():
            for form in self.FORMS:
                with self.subTest(variant=label, form=form):
                    self._assert_tenth_found(self._take(next(built)), "self")
        for label, kw in quiet.items():
            with self.subTest(variant=label, form="declared"):
                self._assert_tenth_quiet(self._take(next(built)))
        for label, body in unlocated.items():
            with self.subTest(variant=label, form="declared"):
                self._assert_tenth_found(self._take(next(built)), "self")
        head = census(CENSUS_FILES)
        self.assertEqual(sorted(a for a, t in head.attr_whole.items() if "env" in t), ["_launched_env", "_launching", "env_vars"],
                         "at this head the shape held whole on _launching and the two env source attributes are the whole-env attributes")
        self.assertEqual(sorted(a for a, t in head.attr_taint.items() if "env" in t), ["_launched_env", "env_vars"],
                         "and no attribute's carried set gained env: the keyed readers of _launching stay clean")

    def test_a_source_name_spelled_as_a_string_outside_a_followed_reflection_is_a_failure(self):
        """The door had this rule (its name as a string outside `getattr(x, "_log")` fails) and no source did, so a source
        reached by reflection under a computed name went unread. Every string constant spelling a source's identifier (an
        attribute, a function, a module-level name; the 'env' key excepted, a key being spelled at every read) outside the
        reflected read or store the census follows (`getattr(x, "n"[, d])`, `setattr(x, "n", v)`, `vars(x)["n"]`,
        `x.__dict__["n"]` and its `.get`/`.setdefault`/`.pop`) is a failure named by site; a store by reflection under a name
        the census cannot place (`setattr(self, name, e)`, `self.__dict__[name] = e`) is a failure when the value is tainted.
        The followed forms are read as the attribute or the call they name (the previous test's ap, aq, ae, ax, ay)."""
        stores = (("setattr under a computed name", 'setattr(self, name, e)'),
                  ("self.__dict__ under a computed name", 'self.__dict__[name] = e'))
        built = iter(self._censuses([
            self._shape_spec("helper", arg="getattr(sess, _TENTH_ATTR)", expr="shape", extra='\n_TENTH_ATTR = "env_vars"\n'),
            self._shape_spec("declared", methods='    def _tenth_shape(self, raw):\n        e = raw["vars"]\n        return {"env": e, "opts": e}\n\n',
                             arg="getattr(self, _TENTH_FN)(raw)", extra='\n_TENTH_FN = "_tenth_shape"\n')]
            + [self._shape_spec("declared", methods='    def _tenth_shape(self, raw, name):\n        e = raw["vars"]\n        %s\n        return {"env": e}\n\n'
                                '    def _tenth_other(self):\n        return {"opts": self._tenth_held}\n\n' % store, arg="self._tenth_other()")
               for _label, store in stores]))
        with self.subTest(case="an attribute source's name in a module constant handed to getattr"):
            c = self._take(next(built))
            self.assertEqual([(k, b) for k, b, _ln, _t in c.failures], [("source-name-string", "sdk_backend.py")])
            self.assertIn("'env_vars' is a string outside a reflected read or store", c.failures[0][3])
            self.assertEqual(len(c.content_rows), self.BASE, "the row is read but untainted: the string is what is loud")
        with self.subTest(case="a declared source function's name in a constant handed to getattr"):
            c = self._take(next(built))
            self.assertEqual([(k, b) for k, b, _ln, _t in c.failures], [("source-name-string", "sdk_backend.py")])
        for label, _store in stores:
            with self.subTest(case=label):
                c = self._take(next(built))
                self.assertEqual([(k, b) for k, b, _ln, _t in c.failures], [("reflection-store", "sdk_backend.py")])
                self.assertIn("a name the census cannot place", c.failures[0][3])
        with self.subTest(case="the head spells no source's name as a string and stores nothing by a computed name"):
            head = census(CENSUS_FILES)
            self.assertEqual([f for f in head.failures if f[0] in ("source-name-string", "reflection-store")], [])
            idents = set(DEFAULT_SOURCES["attr"]) | {q.split(".")[-1] for _b, q in DEFAULT_SOURCES["func"]} | {n for _b, n in DEFAULT_SOURCES["name"]}
            self.assertEqual(head._source_idents, idents, "every attribute, function and name source by its identifier")
            self.assertGreaterEqual(len(idents), 30)
            self.assertNotIn("env", head._source_idents)

    def test_the_alias_resolution_walks_every_concrete_class_of_the_receiver_and_reads_reflection_and_the_class_object(self):
        """Ruling 4's lens (2026-09-19): thirteen receivers of the planted `_ring = _log` resolved silently to the other
        binding. The resolution walks every class an instance of the receiver's type can be (the class and each subclass,
        each by its own MRO: a mixin's self is an instance of the class it is mixed into), so a mixin into the writer's class
        is a door and a mixin into both classes is the loud ambiguity; a type every instance satisfies (`object`, `Any`, a
        Protocol, a class defining __getattr__) types nothing, so those receivers are untyped and fail; an annotated
        parameter reassigned in the body is what its assignments make it; a class object as receiver (a class name, `cls`,
        `type(self)`, `self.__class__`) reads the message after the explicit self; the alias's name spelled in
        `getattr(x, "_ring")` resolves like `x._ring`, and spelled anywhere else is the door-name-string failure. Beside
        the lens's arms, the unpinned typed forms (an attribute annotation, Optional, a union, a keyword-only parameter),
        the collision record's other two hows, and, with no alias at all, `cls._log(be or 'x', msg, problem=True)` in a
        classmethod, whose literal head hid the row from the unreduced pin while its message was read as `be or 'x'`."""
        alias = "    _ring = _log\n\n"
        call = lambda recv, indent, first=None: "%s%s._ring(%s%s, problem=True, %s)\n" % (indent, recv, (first + ", ") if first else "", self.MSG, self.RING)
        benign = '    def _tenth_plain(self):\n        self._ring("tenth: plain", problem=False)\n\n'

        def plant(backend="", session="", api="", tail="", head="", with_alias=True, with_benign=False):
            return self._copy(lambda s: (self._with_format(s).replace(self.METHOD_ANCHOR, (alias if with_alias else "") + (benign if with_benign else "") + backend + self.METHOD_ANCHOR)
                                         .replace(self.SESSION_ANCHOR, session + self.SESSION_ANCHOR).replace(self.API_ANCHOR, api + self.API_ANCHOR)
                                         .replace("class SdkBackend:\n", head + "class SdkBackend:\n" if not head.endswith("SdkBackend(_TenthBase):\n") else head)) + tail)

        def tenth(c):
            return [dc.lineno for dc in c.door_calls if dc.owner == "_tenth"]

        doors = {
            "03: self in a mixin mixed into the writer's class": dict(tail="\nclass _TenthMixin:\n    def _tenth(self, sess):\n" + call("self", " " * 8) + "\nclass _TenthBackend(_TenthMixin, SdkBackend):\n    pass\n"),
            "23a: getattr(self, '_ring')(...) in the writer's class": dict(backend="    def _tenth(self, sess):\n        getattr(self, '_ring')(%s, problem=True, %s)\n\n" % (self.MSG, self.RING)),
            "m4c: the class name as receiver, the message after the explicit self": dict(tail="\ndef _tenth(be, sess):\n" + call("SdkBackend", " " * 4, first="be")),
            "24a: type(self) as receiver": dict(backend="    def _tenth(self, sess):\n" + call("type(self)", " " * 8, first="self") + "\n"),
            "24b: self.__class__ as receiver": dict(backend="    def _tenth(self, sess):\n" + call("self.__class__", " " * 8, first="self") + "\n"),
            "m4d3: an attribute annotation": dict(tail="\ndef _tenth(be: kernel.SdkBackend, sess):\n" + call("be", " " * 4)),
            "m4d4: Optional[SdkBackend]": dict(tail="\ndef _tenth(be: Optional[SdkBackend], sess):\n" + call("be", " " * 4)),
            "m4d5: SdkBackend | None": dict(tail="\ndef _tenth(be: SdkBackend | None, sess):\n" + call("be", " " * 4)),
            "m4l: a keyword-only annotated parameter": dict(tail="\ndef _tenth(sess, *, be: SdkBackend):\n" + call("be", " " * 4)),
        }
        uncalled = ("door-escapes", "sdk_backend.py", "class alias _ring of SdkBackend is never called")
        others = {
            "m4g4: a subclass rebinding the name as a method, self in the subclass": dict(tail="\nclass _TenthSub(SdkBackend):\n    def _ring(self, line, **kw):\n        pass\n\n    def _tenth(self, sess):\n" + call("self", " " * 8)),
            "35: a mixin mixed only into ApiHealth, using the deque": dict(tail="\nclass _TenthMixin:\n    def _tenth(self, ev):\n        self._ring.append(ev)\n\nclass _TenthHealth(_TenthMixin, ApiHealth):\n    pass\n"),
            "Optional[ApiHealth]": dict(tail="\ndef _tenth(h: Optional[ApiHealth], sess):\n" + call("h", " " * 4)),
        }
        ambiguous = {
            "03b: a mixin mixed into both classes": dict(tail="\nclass _TenthMixin:\n    def _tenth(self, sess):\n" + call("self", " " * 8) + "\nclass _TenthBackend(_TenthMixin, SdkBackend):\n    pass\n\nclass _TenthHealth(_TenthMixin, ApiHealth):\n    pass\n", why="admits both bindings"),
            "19: a __getattr__ proxy typed by its constructor": dict(tail="\nclass _TenthProxy:\n    def __init__(self, be: SdkBackend):\n        self._be = be\n\n    def __getattr__(self, n):\n        return getattr(self._be, n)\n\n\ndef _tenth(be: SdkBackend, sess):\n    p = _TenthProxy(be)\n" + call("p", " " * 4), why="is untyped"),
            "20a: x: object": dict(tail="\ndef _tenth(x: object, sess):\n" + call("x", " " * 4), why="is untyped"),
            "20b: x: Any": dict(tail="\ndef _tenth(x: Any, sess):\n" + call("x", " " * 4), why="is untyped"),
            "20c: x: typing.Any": dict(tail="\ndef _tenth(x: typing.Any, sess):\n" + call("x", " " * 4), why="is untyped"),
            "20d: x: 'Any'": dict(tail="\ndef _tenth(x: 'Any', sess):\n" + call("x", " " * 4), why="is untyped"),
            "21a: a Protocol of the file declaring the name": dict(tail="\nclass _TenthRingLike(Protocol):\n    def _ring(self, line, **kw) -> None: ...\n\n\ndef _tenth(x: _TenthRingLike, sess):\n" + call("x", " " * 4), why="is untyped"),
            "21b: an abstract base binding the name, the writer's class a subclass owning the alias": dict(
                head="class _TenthBase:\n    def _ring(self, line, **kw):\n        raise NotImplementedError\n\n\nclass SdkBackend(_TenthBase):\n",
                tail="\ndef _tenth(x: _TenthBase, sess):\n" + call("x", " " * 4), why="admits both bindings"),
            "22: an annotated parameter reassigned in the body": dict(tail="\ndef _tenth(h: ApiHealth, be, sess):\n    h = be\n" + call("h", " " * 4), why="is untyped"),
            "37: self._be bound in __init__ from a parameter typed object": dict(tail="\nclass _TenthHolder:\n    def __init__(self, be: object):\n        self._be = be\n\n    def _tenth(self, sess):\n" + call("self._be", " " * 8), why="is untyped"),
            "m4e2: a local with one constructor assignment and one untyped": dict(tail="\ndef _tenth(state_dir, x, sess):\n    h = ApiHealth(state_dir)\n    if x:\n        h = x\n" + call("h", " " * 4), why="is untyped"),
        }
        classmethods = (("R05e: cls._log(be or 'tenth', msg, problem=True) in a classmethod", "    @classmethod\n    def _tenth(cls, be, sess):\n        cls._log(be or 'tenth', %s, problem=True, %s)\n\n"),
                            ("type(self)._log(self, msg, ...)", "    def _tenth(self, sess):\n        type(self)._log(self, %s, problem=True, %s)\n\n"),
                            ("getattr(self, '_log')(msg, ...)", "    def _tenth(self, sess):\n        getattr(self, '_log')(%s, problem=True, %s)\n\n"))
        built = iter(self._censuses(
            [self._spec(plant(**kw)) for kw in doors.values()] + [self._spec(plant(tail="\ndef _tenth_helper(sess, log):\n    log(%s, problem=True, %s)\n\n\ndef _tenth(be: SdkBackend, sess):\n    _tenth_helper(sess, log=getattr(be, '_ring', None))\n" % (self.MSG, self.RING)))]
            + [self._spec(plant(**kw)) for kw in others.values()]
            + [self._spec(plant(with_benign=True, **{k: v for k, v in kw.items() if k != "why"})) for kw in ambiguous.values()]
            + [self._spec(plant(with_benign=True, tail="\nclass _TenthByMethod:\n    def _ring(self, line, **kw):\n        pass\n\n\nclass _TenthByName:\n    _ring = None\n")), self._spec(plant(with_benign=True, tail="\n_TENTH_ATTR = '_ring'\n\n\ndef _tenth(be: SdkBackend, sess):\n    getattr(be, _TENTH_ATTR)(%s, problem=True, %s)\n" % (self.MSG, self.RING)))]
            + [self._spec(plant(backend=body % (self.MSG, self.RING), with_alias=False)) for _label, body in classmethods]))
        for label, kw in doors.items():
            with self.subTest(arm=label):
                c = self._take(next(built))
                self._assert_tenth_found(c, "alias")
                self.assertEqual([dc.lineno for dc in c.unreduced if dc.owner == "_tenth"], [])
        with self.subTest(arm="23b: getattr(be, '_ring', None) handed to a helper that calls it"):
            c = self._take(next(built))
            self.assertEqual(c.failures, [])
            self.assertIn(("_tenth_helper", "TENTH_RING", False), c.content_identities())
            self.assertEqual(len(c.content_rows), self.BASE + 1)
            self.assertEqual([dc.kind for dc in c.door_calls if dc.owner == "_tenth_helper"], ["param"])
        for label, kw in others.items():
            with self.subTest(arm=label):
                c = self._take(next(built))
                self.assertEqual([(k, b, t) for k, b, _ln, t in c.failures], [uncalled], "the call is the other binding's, so the alias is called nowhere")
                self.assertEqual(tenth(c), [])
                self.assertEqual(len(c.content_rows), self.BASE)
        for label, kw in ambiguous.items():
            why = kw["why"]
            with self.subTest(arm=label):
                c = self._take(next(built))
                kinds = [(k, b) for k, b, _ln, _t in c.failures]
                self.assertEqual(kinds, [("door-alias-ambiguous", "sdk_backend.py")], "the loud ambiguity, and no other failure (the benign call keeps the alias called)")
                text = c.failures[0][3]
                self.assertIn("the receiver is untyped" if why == "is untyped" else "the receiver's type admits both bindings", text)
                self.assertIn("SdkBackend._ring (a class-body alias of the door, line", text)
                self.assertIn("ApiHealth._ring (an attribute bound in __init__)", text)
                self.assertEqual(tenth(c), [], "not counted as a door: named as a failure instead")
                self.assertEqual(len(c.content_rows), self.BASE)
        with self.subTest(arm="m4j: the collision record's other hows, a method and a class-body name"):
            c = self._take(next(built))
            self.assertEqual(c.failures, [])
            self.assertEqual(c.alias_collisions, {"_ring": ["ApiHealth._ring (an attribute bound in __init__)", "_TenthByMethod._ring (a method)", "_TenthByName._ring (a class-body name)"]})
        with self.subTest(arm="the alias's name spelled as a string outside getattr"):
            c = self._take(next(built))
            self.assertEqual([(k, b) for k, b, _ln, _t in c.failures], [("door-name-string", "sdk_backend.py")])
            self.assertIn("a door alias's name '_ring' is a string outside getattr(x, '_ring')", c.failures[0][3])
        for label, _body in classmethods:
            with self.subTest(arm=label):
                c = self._take(next(built))
                self._assert_tenth_found(c, "typed")
                self.assertEqual([dc.lineno for dc in c.unreduced if dc.owner == "_tenth"], [])
        head = census(CENSUS_FILES)
        self.assertEqual((head.class_alias_doors, head.module_alias_doors, head.alias_collisions), ({}, {}, {}),
                         "product code binds no alias of the door at class or module scope: the census tells the bindings apart by scope, and no rename was needed")


    def test_the_conduits_true_callers_are_read_by_binding_each_call_against_its_signature_and_an_unreadable_road_is_refused(self):
        """Round 7 of the review (2026-09-20, tests-2 and extra7-1): the pin naming _log_quietly's problem=True callers read
        n.keywords alone, so a third caller passing problem positionally was counted as saying nothing (plant A stayed green
        at the round-6 head; the same caller as a keyword reded the pin), and the declaration's roster went stale with every
        test green. Census.bound_site_args binds each call against the conduit's signature (positional by index, keyword by
        name, the default for a parameter left unsaid), and the roster is read off the bound arguments: problem=True as a
        keyword and positionally are both the True road; ring_text positionally is a carrier and an explicit ring_text=None
        is not; a falsy constant other than False or None (0) is filed on the True road, the ruling's rule, a false red
        rather than a silent miss; and a problem= that is not a constant (a name, a call) or a call the signature cannot
        place (a starred argument) is a FAILURE ROW naming the site, never counted as False, the standing rule's restricted
        side. Each form is a plant on a module copy: a `_tenth_caller` method in the conduit's class."""
        plant = "    def _tenth_caller(self, flag, *rest):\n        self._log_quietly(%s)\n\n"
        counted = {
            "keyword True": '"live work (%s): planted" % self.name, problem=True',
            "positional True": '"live work (%s): planted" % self.name, True',
            "keyword True, ring_text=None written": '"live work (%s): planted" % self.name, problem=True, ring_text=None',
            "falsy constant 0 (the ruling's rule: any constant but False and None)": '"live work (%s): planted" % self.name, problem=0',
        }
        positional_ring = '"live work (%s): planted" % self.name, True, None, "planted ring text"'
        routine = ('"live work (%s): planted" % self.name, problem=False', '"live work (%s): planted" % self.name, problem=None')
        refused = {
            "positional non-constant": ('"live work (%s): planted" % self.name, flag', "site-argument-unread", "problem= at SdkSession._tenth_caller is"),
            "a name": ('"live work (%s): planted" % self.name, problem=flag', "site-argument-unread", "problem= at SdkSession._tenth_caller is"),
            "a call": ('"live work (%s): planted" % self.name, problem=bool(flag)', "site-argument-unread", "problem= at SdkSession._tenth_caller is"),
            "a starred argument": ('"live work (%s): planted" % self.name, *rest', "site-unbound", "SdkSession._log_quietly at SdkSession._"),
        }
        calls = list(counted.values()) + [positional_ring] + list(routine) + [call for call, _kind, _head in refused.values()]
        results = self._censuses([self._spec(self._copy(lambda s: s.replace(self.SESSION_ANCHOR, plant % call + self.SESSION_ANCHOR))) for call in calls])
        c0 = census((SDK_BACKEND, CREDENTIALS_PY))    # the unchanged pair: the door's one shared census, not a construction of this test's own
        built = dict(zip(calls, results))
        rows0, refused0 = c0.bound_site_args("SdkSession._log_quietly", constants=("problem",))
        base = _true_callers(rows0)
        self.assertEqual((len(base), refused0), (7, []), "the module's own roster at round 7's head: seven, none refused")
        rows_small, refused_small = self.small.bound_site_args("SdkSession._log_quietly", constants=("problem",))
        self.assertEqual((len(rows_small), refused_small), (1, []), "the small module's conduit has one site of its own, none refused")

        def roster(call):
            c = self._take(built[call])
            rows, refused_rows = c.bound_site_args("SdkSession._log_quietly", constants=("problem",))
            self.assertEqual(len(rows) + len([r for r in refused_rows if r[0] == "site-unbound"]), len(rows_small) + 1,
                             "the planted site is bound like the small module's own, or refused as unbound")
            return [t for t in _true_callers(rows) if t[0] == "_tenth_caller"], [(k, ln, text) for k, _b, ln, text in refused_rows]
        for label, call in counted.items():
            with self.subTest(form=label):
                self.assertEqual(roster(call), ([("_tenth_caller", False)], []), label)
        with self.subTest(form="positional True with a positional ring_text"):
            self.assertEqual(roster(positional_ring), ([("_tenth_caller", True)], []))
        with self.subTest(form="keyword False, and None written: the routine road"):
            self.assertEqual(roster(routine[0]), ([], []))
            self.assertEqual(roster(routine[1]), ([], []))
        line = self.src[:self.src.index(self.SESSION_ANCHOR)].count("\n") + 2      # the planted call's line in the copy
        for label, (call, kind, head) in refused.items():
            with self.subTest(form=label):
                hits, rows = roster(call)
                self.assertEqual((hits, [(k, ln) for k, ln, _t in rows]), ([], [(kind, line)]), "%s: a failure row naming the site, not a False" % label)
                self.assertTrue(rows[0][2].startswith(head), rows[0][2])

    def test_a_conduit_whose_inner_call_folds_a_source_of_its_own_is_refused_at_the_inner_call_and_the_no_fold_control_is_not(self):
        """Round 7 of the review (2026-09-20, kernel-1): the post-merge census took every conduit's inner door call out of
        the rule-(2) check on the premise that each site carries every inner road, which is true of the DECLARATION and
        false of the TAINT: a site carries the taint of the argument it passes, not what the conduit's own body folds into
        the message, the ring text or the key, so a fold of a declared env source inside the conduit was refused by nothing
        (the round-6 refuters' probe: byte-identical census output with AUTH_ENV_NAMES folded into problem_row's ring text).
        The skip is narrowed to inner calls whose RESIDUAL taint, recomputed with the conduit's parameters clean and
        re-propagated through its locals and its helpers' returns, is empty. Plants on a module copy: a conduit method
        `_tenth_relay(self, msg, ring=True)` whose inner call forwards problem=bool(ring) (problem_row's shape) and folds
        AUTH_ENV_NAMES into its message, its ring text or its key, called from `_tenth` with a clean prose; each fold is a
        violation AT THE INNER CALL ("problem= is the expression bool(ring)"), the census's residual names the env, and the
        content rows stay at BASE (no constant True, so no row). The site: clean for the message and ring-text folds, whose
        expressions _through collapses to the site's own argument (str(msg) + X reduces to msg), so nothing but the inner
        call's row refuses them; tainted for the key fold, which is no wrap of a parameter and so stays the site's own key
        expression, a second refusal at the site beside the inner call's and, the site being declared True through ring's
        default, a content row with an UNBOUNDED identity (BASE + 1). The no-fold control is silent (the inner call is
        not tainted at all). Under the blanket skip of the round-6 head the message and ring-text folds were silent, 0
        violations each, and the key fold was not tainted at all (rule 6 read the key since round 7; the round-7 build's
        probe, pasted in the PR body). Round 7's lenses added the residual's two propagation roads (a fold through a
        conduit local, a fold through a helper's return), their parameter-only control under a tainted site, and the
        depth bound's over-approximation, each of which a census with that road removed had left silent."""
        anchor = self.METHOD_ANCHOR
        relay = "    def _tenth_relay(self, msg, ring=True):\n        self._log(%s)\n\n"
        site = "    def _tenth(self, sess):\n        self._tenth_relay('env (%s): tenth' % sess.name)\n\n"

        def path_with(inner):
            return self._copy(lambda s: s.replace(anchor, relay % inner + site + anchor))

        def path_with_local(local, helpers="", where=site):
            return self._copy(lambda s: s.replace(anchor, helpers + relay2 % local + where + anchor))

        def census_with(c):
            self.assertEqual(c.failures, [])
            inner_calls = [dc for dc in c.door_calls if dc.owner == "_tenth_relay"]
            self.assertEqual([dc.kind for dc in inner_calls], ["self"], "the conduit's one inner call")
            self.assertEqual([dc.kind for dc in c.door_calls if dc.owner == "_tenth"], ["conduit:SdkBackend._tenth_relay"], "the planted site")
            return c, inner_calls[0]
        fold = "', '.join(sorted(AUTH_ENV_NAMES))"
        at_site = [("_tenth", "problem=True with a ring text that reduces to no format")]
        relay2 = "    def _tenth_relay(self, msg, ring=True):\n        line = %s\n        self._log(line, problem=bool(ring))\n\n"
        wrap = "    def _tenth_wrap(self, m):\n        return str(m) + %s\n\n"
        tainted_site = "    def _tenth(self, sess):\n        self._tenth_relay(%s)\n\n" % self.MSG
        chain = "".join("    def _tenth_w%d(self, m):\n        return str(m) + %s\n\n"
                        % (i, "self._tenth_w%d(m)" % (i + 1) if i < 8 else "' tail'") for i in range(1, 9))
        inner_row = ("_tenth_relay", "problem= is the expression bool(ring)")
        fold_roads = (("message", "msg + %s, problem=bool(ring)" % fold, []),
                      ("ring_text", "msg, problem=bool(ring), ring_text=str(msg) + %s" % fold, []),
                      ("key", "msg, problem=bool(ring), key=%s" % fold, at_site))
        local_roads = (("a fold through a conduit local", "msg + %s" % fold, ""),
                       ("a fold through a helper's return", "str(msg) + self._tenth_wrap(msg)", wrap % fold))
        # Round 8 of the review (2026-09-21, tests-1): each tainted road carries the NAME of the helper its local calls, and
        # census_with_local asserts the helper is defined in the copy and resolved at the local's call. Until round 8 the
        # name was sniffed off the road's LABEL ("wrap" in it), neither label had the word, so the control arm's local
        # called `_tenth_w1` while its helpers text defined `_tenth_wrap`: an undefined helper resolves to nothing and
        # reads as clean, so the "clean helper" half of the control was green by construction (a census reading a
        # helper's return from the main pass, the property the control controls for, left it green; it reds it now).
        tainted_roads = (("the parameter alone through a local and a clean helper, under a tainted site (the control)", wrap % "' tail'", "_tenth_wrap"),
                         ("a clean helper chain past RESIDUAL_DEPTH, under a tainted site (the over-approximating side)", chain, "_tenth_w1"))
        # Round 8 (correctness-2 and extra10-2): a fold reaching the inner call through SEVEN conduit locals assigned in
        # reverse order, each from the one the next statement fills and the last from the source, so the residual walk
        # gains one link per pass and needs eight; the round-7 walk stopped at six with no signal and read the residual
        # as empty (the inner call was skipped, the silence the residual exists to remove), while the main pass's identical
        # loop re-queued on its cap. The walk runs to a fixpoint now; its cap-hit signal is pinned two tests below.
        reverse_chain = "msg + g\n" + "".join("        %s = %s\n" % (a, b) for a, b in zip("gfedcb", "fedcba")) + "        a = %s" % fold
        local_roads = local_roads + (("a fold through a chain of seven conduit locals assigned in reverse order", reverse_chain, ""),)
        # Round 8 (extra9-2): a fold onto the conduit's OWN PARAMETER, by assignment and by augmented assignment. The
        # residual walk read every parameter as clean before it read the locals, so the store onto msg was invisible and
        # the inner call skipped, on a planted conduit and on the real problem_row alike. A parameter reads clean only
        # while nothing has been stored onto it; the control: a parameter reassigned from a CLEAN expression stays clean
        # (the store records a non-empty tag set alone), so under a tainted site the residual is empty, the inner call is
        # skipped and the site is judged, as for the local-and-helper control above.
        relay3 = "    def _tenth_relay(self, msg, ring=True):\n        %s\n        self._log(msg, problem=bool(ring))\n\n"
        param_roads = (("a fold onto the conduit's own parameter by assignment", "msg = msg + %s" % fold, site, True),
                       ("a fold onto the conduit's own parameter by augmented assignment", "msg += %s" % fold, site, True),
                       ("the parameter reassigned from a clean expression, under a tainted site (the control)", "msg = str(msg) + ' tail'", tainted_site, False))

        def path_with_param(stmt, where):
            return self._copy(lambda s: s.replace(anchor, relay3 % stmt + where + anchor))
        built = iter(self._censuses(
            [self._spec(path_with(inner)) for _road, inner, _rows in fold_roads]
            + [self._spec(path_with_local(local, helpers)) for _road, local, helpers in local_roads]
            + [self._spec(path_with_local("str(msg) + self.%s(msg)" % helper, helpers, tainted_site)) for _road, helpers, helper in tainted_roads]
            + [self._spec(path_with_local("str(msg) + self._tenth_w1(msg)", chain)), self._spec(path_with("msg, problem=bool(ring)"))]
            + [self._spec(path_with_param(stmt, where)) for _road, stmt, where, _folded in param_roads]))
        for road, inner, site_rows in fold_roads:
            with self.subTest(road=road):
                c, dc = census_with(self._take(next(built)))
                self.assertEqual(sorted(dc.taint), ["env"], "the inner call is tainted by the fold")
                self.assertEqual(sorted(dc.residual), ["env"], "the residual names what no site carries")
                self.assertEqual(sorted((d.owner, why) for d, why in c.explicit_violations),
                                 sorted([("_tenth_relay", "problem= is the expression bool(ring)")] + site_rows),
                                 "refused at the inner call, on its own declaration (and at the site where _through keeps the fold)")
                self.assertEqual([d.owner for d in c.tainted if d.owner == "_tenth"], ["_tenth"] if site_rows else [],
                                 "the site passed a clean prose; only a key the walk cannot collapse to a parameter taints it")
                self.assertEqual(len(c.content_rows), self.BASE + (1 if site_rows else 0),
                                 "no constant True at the inner call, so no row of its own; the key-tainted site, declared True through "
                                 "ring's default, is a content row with an UNBOUNDED identity the identity pin refuses")
                if site_rows:
                    self.assertIn(("_tenth", "UNBOUNDED", True), c.content_identities(), "keyed: the fold is its key")
        # Round 7's lenses (2026-09-20, the census lens): the three folds above sit in the inner call's own argument
        # expressions, which neither of the residual's propagation roads touches, so a census reading the conduit's
        # locals as clean (`names = {}` in residual_taint) or a helper's return as clean (_residual_return returning
        # set()) passed this class whole while a fold through a local or through a helper's return was silent, the
        # round-6 silence again. Each road on the refusal side: the fold reaches the inner call through a local of the
        # conduit, or through the return of a helper the local is assigned from, and is a violation at the inner call
        # with the residual naming the env. Their control: the same local and a clean helper carrying the parameter
        # alone under an env-TAINTED site, where the residual is empty (the taint is wholly the parameters'), the inner
        # call is skipped and the site is judged (refused, its ring text reducing to no format: a content row with an
        # UNBOUNDED identity, BASE + 1), which a mask reading the locals with the main pass's taint would red falsely.
        # The depth bound: an eight-deep clean helper chain past RESIDUAL_DEPTH reads its whole return from the main
        # pass, so under the tainted site the inner call is kept and refused (the over-approximating side, as
        # residual_taint's docstring says) and under a clean site it is silent. The local is `str(msg) + helper(msg)`,
        # never a bare `helper(msg)`: a local that is no wrap of a parameter makes the method no conduit at all, and the
        # inner call is then judged as a plain door (loud, but not through the residual).

        def census_with_local(c):
            self.assertEqual(c.failures, [])
            inner_calls = [dc for dc in c.door_calls if dc.owner == "_tenth_relay"]
            self.assertEqual([dc.kind for dc in inner_calls], ["self"], "the conduit's one inner call")
            self.assertEqual([dc.kind for dc in c.door_calls if dc.owner == "_tenth"], ["conduit:SdkBackend._tenth_relay"],
                             "the planted site is a conduit site: the local wraps the parameter")
            return c, inner_calls[0]
        for road, local, helpers in local_roads:
            with self.subTest(road=road):
                c, dc = census_with_local(self._take(next(built)))
                self.assertEqual((sorted(dc.taint), sorted(dc.residual)), (["env"], ["env"]),
                                 "the fold reaches the inner call through the local (and the helper's return, or the chain); the residual names it")
                self.assertEqual(sorted((d.owner, why) for d, why in c.explicit_violations), [inner_row], "refused at the inner call")
                self.assertEqual(([d.owner for d in c.tainted if d.owner == "_tenth"], len(c.content_rows)), ([], self.BASE),
                                 "the site passed a clean prose and is not judged; no constant True at the inner call, so no row")
                self.assertEqual(c.residual_cap_hits, 0, "the residual walk converged; a cap hit is a failure, never read as convergence")
        for road, helpers, helper in tainted_roads:
            with self.subTest(road=road):
                c, dc = census_with_local(self._take(next(built)))
                relay_fn = [f for f in c.all_fns if f.qual == "SdkBackend._tenth_relay"]
                self.assertEqual([f.qual for f in c.all_fns if f.qual == "SdkBackend.%s" % helper], ["SdkBackend.%s" % helper],
                                 "the helper the local calls is defined in the copy (round 8, tests-1: the control called one its helpers never defined)")
                self.assertIn("SdkBackend.%s" % helper, {callee.qual for call in relay_fn[0].calls for callee, _via in c.callees.get(id(call), [])},
                              "and resolved at the local's call, so the residual walk read the helper's return, not nothing")
                self.assertEqual(sorted(dc.taint), ["env"], "the main pass carries the site's env into the inner call through msg")
                deep = "RESIDUAL_DEPTH" in road
                self.assertEqual(sorted(dc.residual), ["env"] if deep else [],
                                 "past the bound the helper's whole return from the main pass is read (the env the site passed); "
                                 "within it the taint is wholly the parameters' and the residual is empty")
                self.assertEqual(sorted((d.owner, why) for d, why in c.explicit_violations),
                                 sorted(at_site + ([inner_row] if deep else [])),
                                 "the site is judged (a tainted site through a conduit is refused, its ring text reducing to no format); "
                                 "the inner call only past the bound")
                self.assertEqual(([d.owner for d in c.tainted if d.owner == "_tenth"], len(c.content_rows)), (["_tenth"], self.BASE + 1))
                self.assertIn(("_tenth", "UNBOUNDED", False), c.content_identities(), "the site, declared True through ring's default")
        with self.subTest(road="the same chain past RESIDUAL_DEPTH, under a clean site"):
            c, dc = census_with_local(self._take(next(built)))
            self.assertEqual((sorted(dc.taint), sorted(dc.residual), c.explicit_violations, len(c.content_rows)), ([], [], [], self.BASE),
                             "nothing folded, nothing passed: the bound's over-approximation reads a return that carries nothing")
        with self.subTest(road="no fold (the control)"):
            c, dc = census_with(self._take(next(built)))
            self.assertEqual((sorted(dc.taint), sorted(dc.residual), c.explicit_violations), ([], [], []))
            self.assertEqual(len(c.content_rows), self.BASE)
        for road, _stmt, _where, folded in param_roads:
            with self.subTest(road=road):
                c, dc = census_with_local(self._take(next(built)))
                self.assertEqual(sorted(dc.taint), ["env"], "the inner call is tainted, by the fold or by the site's env through msg")
                if folded:
                    self.assertEqual(sorted(dc.residual), ["env"], "a parameter something was stored onto reads its residual: the fold onto msg itself")
                    self.assertEqual(sorted((d.owner, why) for d, why in c.explicit_violations), [inner_row], "refused at the inner call")
                    self.assertEqual(([d.owner for d in c.tainted if d.owner == "_tenth"], len(c.content_rows)), ([], self.BASE),
                                     "the site passed a clean prose and is not judged; no constant True at the inner call, so no row")
                else:
                    self.assertEqual(sorted(dc.residual), [], "a parameter reassigned from a clean expression stays clean: the taint is wholly the parameters'")
                    self.assertEqual(sorted((d.owner, why) for d, why in c.explicit_violations), sorted(at_site), "the site is judged, the inner call skipped")
                    self.assertEqual(([d.owner for d in c.tainted if d.owner == "_tenth"], len(c.content_rows)), (["_tenth"], self.BASE + 1))
        with self.subTest(road="the head's own inner calls carry no residual"):
            self.assertEqual([(dc.owner, dc.lineno) for dc in census(CENSUS_FILES).tainted if dc.residual], [],
                             "problem_row's line, built from prose through a helper's returned row, and _log_quietly's forwarded parameters")

    def test_a_residual_walk_still_growing_at_its_cap_is_a_failure_naming_the_conduit_and_the_inner_call_is_judged(self):
        """The residual walk's cap-hit signal (round 8 of the review, 2026-09-21, correctness-2 and extra10-2): the walk over
        a conduit's locals runs to a fixpoint, and a walk STILL GROWING at RESIDUAL_PASS_CAP is filed as a "residual-cap"
        failure naming the conduit and the pass count, counted in residual_cap_hits, and the inner call is judged on the
        main pass's names (the restricted side), never skipped; so exhausting the cap is distinguishable from converging.
        Shown with the cap lowered to three on the seven-link reverse chain, which needs eight passes, built in this
        process on a Census subclass (the pool's workers would not see a patched class attribute); at the default cap the
        same plant converges with no failure and no hit (the fold test's chain subtest), and the head's own walk records
        no hit. Red before the signal: the walk stopped at six passes, filed nothing, and read the residual as empty."""
        class _Capped(Census):
            RESIDUAL_PASS_CAP = 3
        fold = "', '.join(sorted(AUTH_ENV_NAMES))"
        relay = ("    def _tenth_relay(self, msg, ring=True):\n        line = msg + g\n"
                 + "".join("        %s = %s\n" % (a, b) for a, b in zip("gfedcb", "fedcba"))
                 + "        a = %s\n        self._log(line, problem=bool(ring))\n\n" % fold)
        site = "    def _tenth(self, sess):\n        self._tenth_relay('env (%s): tenth' % sess.name)\n\n"
        path = self._copy(lambda s: s.replace(self.METHOD_ANCHOR, relay + site + self.METHOD_ANCHOR))
        c = _Capped((path,), DEFAULT_SOURCES)
        hits = [f for f in c.failures if f[0] == "residual-cap"]
        self.assertEqual(len(hits), 1, "one residual-cap failure, naming the conduit: %r" % (c.failures,))
        self.assertEqual((hits[0][1], hits[0][2] > 0), ("sdk_backend.py", True))
        self.assertIn("SdkBackend._tenth_relay", hits[0][3])
        self.assertIn("still growing after 3 passes", hits[0][3])
        self.assertEqual(c.residual_cap_hits, 1, "the hit is counted, distinguishable from convergence")
        inner = [dc for dc in c.door_calls if dc.owner == "_tenth_relay"]
        self.assertEqual([dc.kind for dc in inner], ["self"])
        self.assertEqual(sorted(inner[0].residual), ["env"], "on the restricted side: the main pass's names, so the inner call is judged")
        self.assertIn(("_tenth_relay", "problem= is the expression bool(ring)"), [(d.owner, why) for d, why in c.explicit_violations],
                      "the inner call is refused, not skipped")
        head = census(CENSUS_FILES)
        self.assertEqual((head.residual_cap_hits, [f for f in head.failures if f[0] == "residual-cap"]), (0, []), "the head's own walk converges")
        self.assertEqual(head.summary()["residual_cap_hits"], 0, "the signal is in the CLI's summary beside the main pass's rounds")


    def test_a_chain_the_inner_loop_needs_seven_passes_for_is_followed_to_the_door(self):
        """The taint visit's inner loop over a function's own stores runs at most six passes. A chain of seven names
        assigned in reverse order (each from the one the NEXT statement fills, the last from the env) gains one link
        per pass, so the sixth pass ends with the first name clean and the visit ends still growing. Before fork PR
        #781's readers index, the module-wide sweep on a grown module name happened to give the function another visit
        (a name grew after its first visit); the index removed the sweep, so the census re-visits a function whose loop
        ran out (Census.cap_requeues counts them), and the tenth row is found through the chain with the chain's taint
        alone: the ring text counts the last link and reads no source."""
        chain = "".join("        %s = %s\n" % (a, b) for a, b in zip("gfedcb", "fedcba")) + "        a = sess.env_vars\n"
        c = self._census(self._method(chain + '        self._log("env (%s): tenth %s" % (sess.name, ", ".join(g)), problem=True, '
                                              'ring_text=TENTH_RING % (sess.name[:20], len(g)))'))
        self._assert_tenth_found(c, "self")
        self.assertGreaterEqual(c.cap_requeues, 1, "the plant's function ran its inner loop out and was re-visited")
        self.assertEqual(sorted(c.tainted_names[[f for f in c.all_fns if f.qual == "SdkBackend._tenth"][0]]), list("abcdefg"))


    def test_an_attribute_read_by_reflection_and_stored_later_in_the_file_reaches_the_door(self):
        """A helper reads `getattr(self, "_tenth_names", None)`, the names are stored on the attribute by a method
        written AFTER it, and the row's function reads the helper's return. In file order the helper is visited with
        the attribute clean; the store then grows the attribute, and only a re-visit of the helper carries the names
        into its return and on to the row. Before fork PR #781 the module-wide sweep on a grown module name gave the
        helper that visit by accident: the attribute readers index knew `<x>._tenth_names` alone, not the reflected
        forms expr_taint reads through _reflected_attr, and the PR's differential over the real pair found
        _stamp_launch_login's `getattr(sess, "_launching", None)` losing its taint the moment the sweep went. The index
        holds the reflected forms now, so the row is found; the helper is no caller of the writer, so nothing else
        re-visits it (a plant whose row function reads the attribute itself is re-visited as the writer's caller and
        proves nothing)."""
        c = self._census(self._copy(lambda s: self._with_format(s).replace(
            self.METHOD_ANCHOR,
            '    def _tenth(self, sess):\n        names = self._tenth_names_of()\n'
            '        self._log("env (%s): tenth %s" % (sess.name, ", ".join(names)), problem=True, ring_text=TENTH_RING % (sess.name[:20], len(names)))\n\n'
            '    def _tenth_names_of(self):\n        return getattr(self, "_tenth_names", None) or []\n\n'
            '    def _tenth_store(self, sess):\n        self._tenth_names = sorted(sess.env_vars)\n\n' + self.METHOD_ANCHOR)))
        self._assert_tenth_found(c, "self")
        helper = [f for f in c.all_fns if f.qual == "SdkBackend._tenth_names_of"][0]
        self.assertIn(helper, c.attr_readers["_tenth_names"], "the reflected read indexes the helper as the attribute's reader")
        self.assertIn(("_tenth_names_of", "_tenth_store"), [(a.qual.split(".")[-1], b.qual.split(".")[-1]) for a in c.all_fns for b in c.all_fns
                                                              if a.qual.endswith("_tenth_names_of") and b.qual.endswith("_tenth_store")
                                                              and c.all_fns.index(a) < c.all_fns.index(b)],
                      "the helper is visited before the store in file order, so the row depends on the re-visit")


    def _module_list_plant(self):
        """A module list extended by a method written AFTER the method that joins it into a local for the tenth row: in
        file order the reader is visited with the list clean, the store then grows the module-level name, and only a
        re-visit of the reader carries the names to the row. The reader is a caller of the writer and nothing else, and
        the writer returns nothing, so no other event re-visits it: the row depends on the module name's readers index
        (fork PR #781), where before the PR the module-wide sweep on the grown name visited every function."""
        return self._copy(lambda s: s.replace(self.FMT_ANCHOR, self.TENTH + "_TENTH_SEEN = []\n" + self.FMT_ANCHOR).replace(
            self.METHOD_ANCHOR,
            '    def _tenth(self, sess):\n        names = ", ".join(_TENTH_SEEN)\n'
            '        self._log("env (%s): tenth %s" % (sess.name, names), problem=True, ring_text=TENTH_RING % (sess.name[:20], len(names)))\n\n'
            '    def _tenth_store(self, sess):\n        _TENTH_SEEN.extend(sorted(sess.env_vars))\n\n' + self.METHOD_ANCHOR))

    def test_every_function_whose_taint_visit_reads_a_module_name_is_in_the_readers_index_for_it(self):
        """Fork PR #781, before round 7: the census walk's cost on CI. The taint pass re-visited every function of a module
        whenever a module-level name's stored taint grew (three such events over 715 functions: 2101 visits of 743
        functions, 85 of them changing anything), and with this class constructing 175 censuses the module ran 337 s
        serial against 1.55 s at the PR's base, past CI's 25-minute job ceiling. The pass now re-visits the name's
        READERS by an index Census._index builds from the same test the reads make (a bare Name read that no scope of
        the function binds, then Census._global_read). The pin traces _global_read during _taint over the module-list
        plant, where a taint visit does read a grown name (over the real pair none does: one grown name is read in an
        `if` test alone, which no taint visit evaluates, the other only under a `global` declaration that binds it):
        every function whose visit read a name is indexed as its reader, the index is the predicate run over every
        function's reads, no reader is indexed without a Name read of the name under its def, and the index is
        narrower than the module."""
        class Tracing(Census):
            def _taint(self):
                self.traced, self._tracing = collections.defaultdict(set), True
                try:
                    super()._taint()
                finally:
                    self._tracing = False

            def _global_read(self, fn, name):
                if getattr(self, "_tracing", False):
                    self.traced[(self.mod_of(fn).path, name)].add(fn)
                return super()._global_read(fn, name)

        c = Tracing((self._module_list_plant(),), DEFAULT_SOURCES)
        self._assert_tenth_found(c, "self")
        key = (c.mods["sdk_backend.py"].path, "_TENTH_SEEN")
        self.assertIn(key, c.global_taint, "the module list gains the env: a growth event for the index to answer")
        self.assertEqual(sorted(f.qual for f in c.traced[key]), ["SdkBackend._tenth"], "the reader's taint visit reads the grown name")
        # soundness: every function whose taint visit read a module name is indexed as its reader
        missing = sorted((os.path.basename(k[0]), k[1], fn.qual) for k, fns in c.traced.items() for fn in fns
                         if fn not in c.global_readers.get(k, ()))
        self.assertEqual(missing, [], "a function whose taint visit read a module name is not indexed as its reader")
        # the index is the recognising predicate (a Name read no scope binds) run over every function's reads
        ident = lambda fn: (fn.base, fn.qual, fn.node.lineno)
        rebuilt = collections.defaultdict(set)
        for fn in c.all_fns:
            for name in fn.name_reads:
                if not c._binds(fn, name):
                    rebuilt[(fn.file, name)].add(ident(fn))
        self.assertEqual({k: sorted(ident(f) for f in v) for k, v in c.global_readers.items()},
                         {k: sorted(v) for k, v in rebuilt.items()})
        # and no reader is indexed without a Name read of the name under its def
        for (_path, name), fns in c.global_readers.items():
            for fn in fns:
                loads = {n.id for n in ast.walk(fn.node) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)}
                self.assertIn(name, loads, "%s is indexed as a reader of %s without a Name read of it" % (fn.qual, name))
        # the index is narrower than the module for every grown name: the saving is real
        module_fns = len(c.mods["sdk_backend.py"].fns)
        for k in c.global_taint:
            self.assertLess(len(c.global_readers.get(k, ())), module_fns, k[1])

    def test_the_readers_only_pass_reaches_the_module_wide_sweeps_fixpoint(self):
        """A census that restores the module-wide sweep (Census._global_growth_readers returning the module's every
        function, the enqueue before fork PR #781) reaches the same taint stores and the same rows as the readers-only
        pass while visiting more, over the real pair (the door's shared census of the unchanged pair, since round 8 of the
        review not a construction of this test's own) and over the module-list plant, where the readers index is
        load-bearing. Over the real pair no function runs its inner loop out, so the two passes differ in the enqueue
        alone."""
        class Sweeping(Census):
            def _global_growth_readers(self, key):
                return self.mods[key[0]].fns

        ident = lambda fn: (fn.base, fn.qual, fn.node.lineno)
        by_fn = lambda d: {ident(f): {str(k): sorted(v) for k, v in m.items() if v} for f, m in d.items() if any(m.values())}
        by_name = lambda d: {k: sorted(v) for k, v in d.items() if v}
        rows = lambda c: [(dc.base, dc.lineno, dc.kind, sorted(dc.taint), dc.heads, dc.ring_formats, dc.unreduced, sorted(dc.residual))
                          for dc in c.door_calls]
        plant = (self._module_list_plant(),)
        fast_plant = self._censuses([(plant, DEFAULT_SOURCES)])[0]
        pairs = (("the real pair", (SDK_BACKEND, CREDENTIALS_PY), census((SDK_BACKEND, CREDENTIALS_PY))), ("the module-list plant", plant, fast_plant))
        for label, files, fast_result in pairs:
            with self.subTest(over=label):
                fast, slow = self._take(fast_result), Sweeping(files, DEFAULT_SOURCES)
                self.assertTrue(fast.global_taint, "module names gain taint: the sweep had events to fire on")
                self.assertGreater(slow.taint_rounds, fast.taint_rounds, "the sweep visits more, else the pin compares a pass with itself")
                if label == "the real pair":
                    self.assertEqual(fast.cap_requeues, 0, "no function ran its inner loop out over the real pair")
                for attr, view in (("tainted_names", by_fn), ("carried_names", by_fn), ("ret_taint", by_fn), ("ret_whole", by_fn),
                                   ("attr_taint", by_name), ("attr_whole", by_name)):
                    self.assertEqual(view(getattr(fast, attr)), view(getattr(slow, attr)), attr)
                self.assertEqual({k[1]: sorted(v) for k, v in fast.global_taint.items()}, {k[1]: sorted(v) for k, v in slow.global_taint.items()})
                self.assertEqual(rows(fast), rows(slow))
                self.assertEqual((fast.content_identities(), fast.failures, [(dc.lineno, why) for dc, why in fast.explicit_violations]),
                                 (slow.content_identities(), slow.failures, [(dc.lineno, why) for dc, why in slow.explicit_violations]))

    def test_a_reader_inside_a_class_keyword_is_in_the_readers_index_and_its_variable_takes_the_grown_names_taint(self):
        """The index pass reaches a class statement's keywords and a def's or class's type parameters through
        stray_loops alone, which fed their loop nodes to Fn.loops without their reads: a comprehension in a class
        keyword reading a module list a LATER method extends was in no readers index, so the readers-only enqueue on
        the grown name (the pin above) never re-visited its function, and the comprehension's variable stayed clean
        where the module-wide sweep had tainted it. Found by fork PR #781's independent verifier on this copy: the
        index held the store alone and the variable no taint. The reads under those fields are indexed now: both
        methods are readers of the list, and the variable carries the env after the store's growth. The copy is
        parsed, never run, like every copy here. Class keywords alone: a type parameter is a syntax error before
        Python 3.12, and CI's matrix starts at 3.10."""
        c = self._census(self._copy(lambda s: s.replace(self.FMT_ANCHOR, "_TENTH_SEEN = []\n" + self.FMT_ANCHOR).replace(
            self.METHOD_ANCHOR,
            '    def _tenth(self, sess):\n        class _K(metaclass=type, names=[n for n in _TENTH_SEEN]):\n            pass\n\n'
            '    def _tenth_store(self, sess):\n        _TENTH_SEEN.extend(sorted(sess.env_vars))\n\n' + self.METHOD_ANCHOR)))
        self.assertEqual([f[:3] for f in c.failures], [])
        self.assertEqual(len(c.content_rows), self.BASE, "the plant adds no row: its reader feeds no door")
        key = (c.mods["sdk_backend.py"].path, "_TENTH_SEEN")
        self.assertIn(key, c.global_taint, "the module list gains the env: a growth event for the index to answer")
        self.assertEqual(sorted(f.qual for f in c.global_readers.get(key, ())), ["SdkBackend._tenth", "SdkBackend._tenth_store"],
                         "the comprehension in the class keyword indexes its method as the list's reader, beside the store")
        tenth = [f for f in c.all_fns if f.qual == "SdkBackend._tenth"][0]
        self.assertEqual({k: sorted(v) for k, v in c.tainted_names[tenth].items()}, {"n": ["env"]},
                         "the re-visit on the grown name carries the env to the comprehension's variable")

    def test_a_with_targets_taint_reaches_the_door(self):
        """The taint fold stores a with item's target from its context expression: in flag_settings_path,
        `with os.fdopen(fd, "w") as f:` with fd carrying the env gives f the env, in tainted_names and carried_names.
        No test held that road: with the fold's With arm skipped the module stayed green while the real pair's dump
        lost f's taint (fork PR #781's independent verifier). The plant copies the shape, a call on an env-carrying
        local as the context expression and its target joined into the tenth row's message, so the row is found
        through the with-target alone and the target's taint is in both of the function's stores."""
        c = self._census(self._method('        held = sorted(sess.env_vars)\n'
                                      '        with contextlib.nullcontext(held) as names:\n'
                                      '            self._log("env (%s): tenth %s" % (sess.name, ", ".join(names)), problem=True, '
                                      'ring_text=TENTH_RING % (sess.name[:20], len(names)))'))
        self._assert_tenth_found(c, "self")
        tenth = [f for f in c.all_fns if f.qual == "SdkBackend._tenth"][0]
        self.assertEqual(sorted(c.tainted_names[tenth].get("names", ())), ["env"], "the with-target carries the env")
        self.assertEqual(sorted(c.carried_names[tenth].get("names", ())), ["env"], "and carries it whole")

    # ---- the shared census (round 8 of the review, 2026-09-21: one frozen census per input per process) ----

    def test_the_shared_census_is_frozen_so_no_pin_can_change_what_the_next_reader_sees(self):
        """The immutability half of the shared-census rule (round 8 of the review on fork PR #781, 2026-09-21): the census
        the door hands out is ONE object per input per process, read by every pin of this class and by EnvRowsPopulation,
        the retention pins and the worst-case table, so a pin that changed it would change what every later reader sees
        and the run would pass or fail by order. The freeze (env_ring_census.freeze; the block comment above it says why a
        read-only view in place and not a copy per read) is held here by execution: every write a pin could make is
        REFUSED, at the census (an attribute rebound or deleted), at a table (an entry stored or removed, a nested table,
        the sources), at a record (a Fn's attribute, a DoorCall's taint, a Mod's roster and tree, the writer's calls) and
        at a set; a missed key inserts nothing (the defaultdicts were the one road a READ could write by); the audit of
        the rule finds nothing mutable reachable from the census's own structures (the syntax trees are the stdlib's
        nodes, outside the freeze and outside what any pin reads through the census); and after every attempt the door
        still answers with the same object, digesting as it did when built, so the next reader sees what the first saw.
        Red with the freeze removed (the door handing out the bare Census): every one of the thirteen writes succeeds
        and its subTest reports that neither TypeError nor AttributeError was raised; the deleted counts attribute then
        ends the test's own digest read, and the write into the sources reached DEFAULT_SOURCES itself, the module's
        table a bare Census holds by reference, so every later door key moved with it."""
        head = census(CENSUS_FILES)
        pair = census((SDK_BACKEND, CREDENTIALS_PY))
        self.assertIs(head, census(CENSUS_FILES), "one object per input per process")
        before = erc.census_digest(head)
        self.assertEqual(before, head.digest_at_birth, "the shared census reads as it did when the door froze it")
        a_fn, a_row = head.all_fns[0], head.content_rows[0]

        def store_an_entry():
            head.counts["doors"] = 0

        def store_a_nested_entry():
            head.counts["conduit_sites"]["conduit:problem_row"] = 0

        def remove_an_entry():
            del head.by_kind["self"]

        def store_a_source():
            head.sources["func"][("plant.py", "planted")] = "env"

        def rebind_an_attribute():
            head.failures = ()

        def delete_an_attribute():
            del head.counts

        def append_a_row():
            head.content_rows.append(a_row)

        def grow_a_set():
            head.attr_taint["env_vars"].add("planted")

        def rebind_a_records_attribute():
            a_fn.qual = "planted"

        def grow_a_records_list():
            head.writer.calls.append(None)

        def rebind_a_rows_taint():
            a_row.taint = frozenset()

        def grow_a_modules_roster():
            head.mods["sdk_backend.py"].fns.append(a_fn)

        def rebind_a_modules_tree():
            head.mods["sdk_backend.py"].tree = None

        writes = [store_an_entry, store_a_nested_entry, remove_an_entry, store_a_source, rebind_an_attribute, delete_an_attribute,
                  append_a_row, grow_a_set, rebind_a_records_attribute, grow_a_records_list, rebind_a_rows_taint,
                  grow_a_modules_roster, rebind_a_modules_tree]
        for write in writes:
            with self.subTest(write=write.__name__):
                with self.assertRaises((TypeError, AttributeError)):
                    write()
        with self.subTest(write="a missed key inserts nothing"):
            with self.assertRaises(KeyError):
                head.attr_readers["planted"]
            self.assertNotIn("planted", head.attr_readers)
        self.assertEqual(erc.unfrozen_parts(head), [], "nothing mutable is reachable from the census's own structures")
        self.assertEqual(erc.unfrozen_parts(pair), [])
        self.assertEqual([type(c).__name__ for c in erc._CENSUS.values()], ["FrozenCensus"] * len(erc._CENSUS), "every census the door holds is frozen")
        self.assertIs(census(CENSUS_FILES), head, "the door still answers with the same object")
        self.assertEqual(erc.census_digest(head), before, "and it digests as before: the next reader sees what the first saw")

    # ---- the pool's own pins (the block comment above _censuses says why the pool exists) ----

    def _pool_specs(self):
        """Two specs a pin builds both ways: a tenth-row plant on a copy of the small module, and a loud plant (a second
        appender in a synthetic module beside the small module) whose construction raises CensusError."""
        return [self._spec(self._method("        self._log(%s, problem=True, %s)" % (self.MSG, self.RING))),
                self._spec(self.small_path, self._plant("plant.py", "def tenth(be, sess):\n    be._problems.append({'text': 'x'})\n"))]

    def _reads_of(self, results):
        """What this class reads from a batch, in one comparable shape: for a Census its identities, failures, door calls
        with their taint, violations, summary, alias tables, functions and site binding; for a raised construction the
        exception's class and text."""
        out = []
        for r in results:
            r = self._resolve(r)
            if isinstance(r, _Raised):
                out.append(("raised", type(r.exc).__name__, str(r.exc)))
                continue
            rows, refused = r.bound_site_args("SdkSession._log_quietly", constants=("problem",))
            out.append(("census", r.content_identities(), r.failures,
                        [(dc.base, dc.lineno, dc.owner, dc.kind, sorted(dc.taint), dc.heads, dc.ring_formats, dc.unreduced, sorted(dc.residual),
                          dc.problem_decl) for dc in r.door_calls],
                        [(dc.lineno, why) for dc, why in r.explicit_violations], r.summary(), r.alias_collisions,
                        sorted((b, ln, how) for b, ln, how, _f in r.door_value_sites), [(f.qual, f.node.lineno) for f in r.all_fns],
                        r.cap_requeues, r.taint_rounds,
                        [(caller.qual, call.lineno, sorted((k, ast.unparse(v)) for k, v in b.items())) for caller, call, b in rows], refused))
        return out

    def test_the_censuses_come_through_the_worker_pool_and_read_the_same_as_this_process_builds(self):
        """The ruling's pin that the pool road is TAKEN: in this run, for this batch, the class's censuses came from the
        worker pool (a fallback that silently ran every batch passes every other test of the class and fails here), and
        what came through reads the same as this process builds over the same inputs, a loud plant's CensusError text
        included, so the tests above prove the same things they proved serially. Where the pool was lost the class has already
        said so (a RuntimeWarning and a stderr line) and ran serial; this pin then FAILS naming the reason, since the road
        it pins did not run, unless the reason is the one declared environment limitation, the only skip (round 8 of
        the review, 2026-09-21, extra6-2; until then it skipped on any reason, and condition (2) of the round-6 ruling,
        that the module never fails for want of a pool, holds for the limitation alone)."""
        cls = type(self)
        self._pool_or_fail()
        specs = self._pool_specs()
        pooled = self._censuses(specs)
        self.assertEqual(cls.roads[-1], "pool", "the batch was routed to the pool")
        self.assertEqual([type(r).__name__ for r in pooled], ["_Pending", "_Pending"], "unpickled when read, not before")
        pooled = [self._resolve(r) for r in pooled]
        self.assertGreaterEqual(cls.built["pool"], len(specs), "the batch's constructions came from the pool")
        self.assertEqual(cls.built["serial"], 0, "no construction of this class fell back to this process in this run")
        self.assertEqual([type(r).__name__ for r in pooled], ["Census", "_Raised"])
        self.assertIsInstance(pooled[1].exc, CensusError)
        self.assertIsInstance(pooled[1].exc.__cause__, _WorkerTraceback, "the worker's traceback travels as the cause")
        self.assertEqual(self._reads_of(pooled), self._reads_of(self._comparison(specs)))
        c = pooled[0]
        self.assertIn(self.TENTH_ID, c.content_identities())
        # the round trip's tables are keyed by the unpickled trees (Census.__getstate__): a table left keyed by the
        # worker's addresses would answer nothing here
        nodes = set(c._nodes_by_id())
        self.assertTrue(c.all_fns and all(c.fn_by_node.get(id(f.node)) is f for f in c.all_fns), "fn_by_node is keyed by the unpickled defs")
        self.assertTrue(c.door_calls and all(c.fn_of.get(id(dc.node)) is dc.fn for dc in c.door_calls if isinstance(dc.fn, erc.Fn)),
                        "fn_of is keyed by the unpickled call nodes")
        self.assertTrue(all(id(call) in c.callees for f in c.all_fns for call in f.calls), "callees is keyed by the unpickled call nodes")
        self.assertTrue(c.classes_by_name and all(c.cls_by_node.get(id(k.node)) is k for lst in c.classes_by_name.values() for k in lst),
                        "cls_by_node is keyed by the unpickled class nodes")
        self.assertTrue(c._decl_node_tags and set(c._decl_node_tags) <= nodes, "the declared roots name nodes of the unpickled trees")
        self.assertTrue(all(set(f.lexical) <= nodes for f in c.all_fns) and any(f.lexical for f in c.all_fns), "every lexical table does too")

    def test_a_pool_that_breaks_is_named_once_on_stderr_and_the_batch_is_built_here_with_the_same_results(self):
        """Condition (2) of the ruling: the class degrades, never errors, and (the reviewer's round 7 on fork PR #781) the
        degradation is ANNOUNCED. With the pool broken (an executor whose submit raises BrokenProcessPool, standing in for
        the class's for this test alone) a batch is built in this process, ONE RuntimeWarning and ONE stderr line name the
        kind (BrokenProcessPool) and say the results are unchanged, the class drops the pool so later batches go the same
        way without a second of either, and the results read the same as the pool's over the same inputs, the loud
        plant's CensusError text included. The class's own pool comes back after the test. Red with the warning removed
        from `_pool_lost`: no RuntimeWarning recorded."""
        cls = type(self)
        specs = self._pool_specs()
        pooled = [self._resolve(r) for r in self._censuses(specs)] if cls._pool is not None else None

        class _Broken:
            def submit(self, *a, **k):
                raise BrokenProcessPool("planted: every worker is gone")

            def shutdown(self, *a, **k):
                pass

        err = io.StringIO()
        with mock.patch.object(cls, "_pool", _Broken()), mock.patch.object(cls, "_pool_reason", None), \
                mock.patch.object(cls, "roads", []), mock.patch.object(cls, "built", collections.Counter()), contextlib.redirect_stderr(err), \
                warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with (erc.comparing() if pooled is not None else contextlib.nullcontext()):    # the serial batch is the comparison of the pooled one
                out = self._censuses(specs)
            self.assertIsNone(cls._pool, "the pool is dropped for the rest of the class")
            with erc.comparing():                                                          # specs[1] again, compared against out[1] below
                again = self._censuses(specs[1:])
            self.assertEqual(cls.roads, ["serial (the census pool failed under a batch of 2: BrokenProcessPool: planted: every worker is gone)"] * 2)
            self.assertEqual(cls.built, {"serial": 3})
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith("[EnvRowsCensusBlindSpots] the census pool failed under a batch of 2: BrokenProcessPool: planted: every worker is gone; "), lines[0])
        self.assertIn("the results are unchanged", lines[0])
        self._assert_announced(caught, lines[0])
        self.assertEqual([type(r).__name__ for r in out], ["Census", "_Raised"])
        self.assertEqual(self._reads_of(out[1:]), self._reads_of(again))
        if pooled is not None:
            self.assertEqual(self._reads_of(pooled), self._reads_of(out))
            self.assertIsNotNone(cls._pool, "the class's own pool is back")

    def test_a_pool_that_cannot_start_for_a_reason_the_pool_failures_do_not_name_is_named_once_and_the_class_builds_here(self):
        """Condition (2) of the ruling at the START: the stdlib refuses to build a ProcessPoolExecutor on a constrained
        platform with a NotImplementedError from concurrent.futures.process._check_system_limits (its two messages are
        planted verbatim: a Python built without multiprocessing.synchronize, and fewer than 256 semaphores), and a
        worker that cannot spawn can raise ImportError or RuntimeError; none is in POOL_FAILURES, and with the start
        catching that tuple alone the whole class ERRORED in setUpClass on either stdlib message (fork PR #781's runs
        verifier, `2 errors`). With `_new_pool` raising each, `_start_pool` leaves the pool unavailable, records the
        reason, ANNOUNCES it (the reviewer's round 7: ONE RuntimeWarning and ONE stderr line, each naming the kind by its
        class and saying the results are unchanged), and the batch built afterwards goes the serial road with no second
        of either and reads the same as the pool's over the same inputs. The stdlib's ValueError for a bad worker count
        is planted too, verbatim. Red with the start catching POOL_FAILURES: the NotImplementedError propagates out of
        `_start_pool`; red with the warning removed from `_pool_lost`: no RuntimeWarning recorded."""
        cls = type(self)
        specs = self._pool_specs()
        pooled = [self._resolve(r) for r in self._censuses(specs)] if cls._pool is not None else None
        starts = [NotImplementedError("This Python build lacks multiprocessing.synchronize, usually due to named semaphores "
                                      "being unavailable on this platform."),
                  NotImplementedError("system provides too few semaphores (32 available, 256 necessary)"),
                  ValueError("max_workers must be greater than 0"),
                  ImportError("This platform lacks a functioning sem_open implementation, therefore, the required "
                              "synchronization primitives needed will not function, see issue 3770."),
                  RuntimeError("planted: a start failure the pool's own failures do not name")]
        for exc in starts:
            with self.subTest(start="%s: %s" % (type(exc).__name__, str(exc)[:48])):
                self.assertNotIsInstance(exc, cls.POOL_FAILURES, "the planted start failure is outside the tuple, or the pin proves nothing")
                err = io.StringIO()
                with mock.patch.object(cls, "_new_pool", mock.Mock(side_effect=exc)), mock.patch.object(cls, "_pool", None), \
                        mock.patch.object(cls, "_pool_reason", None), mock.patch.object(cls, "roads", []), \
                        mock.patch.object(cls, "built", collections.Counter()), contextlib.redirect_stderr(err), \
                        warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    cls._start_pool()
                    self.assertIsNone(cls._pool, "the pool is unavailable")
                    reason = "the census pool could not start: %s: %s" % (type(exc).__name__, exc)
                    self.assertEqual(cls._pool_reason, reason)
                    lines = err.getvalue().splitlines()
                    self.assertEqual(len(lines), 1, lines)
                    self.assertTrue(lines[0].startswith("[EnvRowsCensusBlindSpots] %s; " % reason), lines[0])
                    self.assertIn("the results are unchanged", lines[0])
                    self._assert_announced(caught, lines[0])
                    if exc is starts[-1]:
                        with (erc.comparing() if pooled is not None else contextlib.nullcontext()):    # the serial batch compares against the pooled one
                            out = self._censuses(specs)
                        self.assertEqual(cls.roads, ["serial (%s)" % reason])
                        self.assertEqual(cls.built, {"serial": 2})
                        self.assertEqual(err.getvalue().splitlines(), lines, "no second line for the batch")
                        self._assert_announced(caught, lines[0])
                        self.assertEqual([type(r).__name__ for r in out], ["Census", "_Raised"])
                        if pooled is not None:
                            self.assertEqual(self._reads_of(pooled), self._reads_of(out))
        if pooled is not None:
            self.assertIsNotNone(cls._pool, "the class's own pool is back")

    def test_a_result_the_pool_never_delivers_is_waited_for_once_within_the_bound_and_the_rest_of_its_batch_is_built_here(self):
        """Condition (2) at a READ (fork PR #781's runs verifier: the read waited with no bound, so a worker wedged mid-batch
        held the test until the module's per-test timeout ended the whole run, which is not the degrade road). A read
        waits POOL_READ_TIMEOUT for its result; on the timeout the pool is dropped with the one stderr line naming the
        bound and that construction is built here; a later result of the batch the pool never delivered is built here
        WITHOUT a wait (its future's `result` is a failure of this test if called), and one the pool did deliver before
        it was dropped is still read from the future. Planted: a `_Pending` over a future nothing completes with the
        bound at 0.2 s for this test, a second over a future that refuses to be waited on, a third over a done future
        holding what a worker returns. The expiry is ANNOUNCED (the reviewer's round 7: ONE RuntimeWarning and ONE stderr
        line, TimeoutError and the bound named) and never an empty result: the first read is a Census built here that
        reads the same as a serial build over its spec. Red with the read unbounded (the first read never returns), with
        the no-wait rule removed (the second read's `result` raises) and with the warning removed (no RuntimeWarning)."""
        cls = type(self)
        pool_up = cls._pool is not None
        specs = self._pool_specs()
        never = concurrent.futures.Future()         # nothing completes it

        class _Unasked:
            def done(self):
                return False

            def result(self, timeout=None):
                raise AssertionError("waited on a result the dropped pool will never deliver")

        delivered = concurrent.futures.Future()
        delivered.set_result(erc.build_census(*specs[1]))       # what a worker returns for the loud plant, built here

        class _Stub:
            def shutdown(self, *a, **k):
                pass

        err = io.StringIO()
        with mock.patch.object(cls, "_pool", _Stub()), mock.patch.object(cls, "_pool_reason", None), mock.patch.object(cls, "roads", []), \
                mock.patch.object(cls, "built", collections.Counter()), mock.patch.object(cls, "POOL_READ_TIMEOUT", 0.2), \
                contextlib.redirect_stderr(err), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            first = self._resolve(_Pending(specs[0], never))
            self.assertIsNone(cls._pool, "the pool is dropped at the timeout")
            self.assertEqual(cls._pool_reason, "the census pool failed under a batch: TimeoutError: no result within 0.2 s")
            with erc.comparing():                              # specs[1] again, built here; `delivered` built it first, and the two are compared below
                second = self._resolve(_Pending(specs[1], _Unasked()))
            third = self._resolve(_Pending(specs[1], delivered))
            self.assertEqual(cls.built, {"serial": 2, "pool": 1}, "two built here, the delivered one read from its future")
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith("[EnvRowsCensusBlindSpots] the census pool failed under a batch: TimeoutError: no result within 0.2 s; "), lines[0])
        self.assertIn("the results are unchanged", lines[0])
        self._assert_announced(caught, lines[0])
        self.assertFalse(never.done(), "the planted future was left alone")
        out = [first, second]
        self.assertEqual([type(r).__name__ for r in out], ["Census", "_Raised"])
        self._assert_tenth_found(first, "self")
        self.assertEqual(self._reads_of([first]), self._reads_of(self._comparison([specs[0]])),
                         "the timed-out read is the census built here, the serial build's equal, never an empty result")
        self.assertIsInstance(third, _Raised)
        self.assertIsInstance(third.exc.__cause__, _WorkerTraceback, "the delivered result was unpacked as a worker's")
        self.assertEqual(self._reads_of([third]), self._reads_of([second]), "the delivered result reads as the one built here")
        if pool_up:
            self.assertIsNotNone(cls._pool, "the class's own pool is back")

    def _assert_announced(self, caught, line):
        """The degradation announced as ONE RuntimeWarning carrying the stderr line's text (the kind's class name is in it), and
        no other RuntimeWarning: what pytest counts on the -q summary line and prints in the warnings section."""
        runtime = [w for w in caught if w.category is RuntimeWarning]
        self.assertEqual([str(w.message) for w in runtime], [line],
                         "one RuntimeWarning, the degradation's own text; no RuntimeWarning means the degradation was silent under -q")

    def test_a_worker_that_sleeps_past_the_bound_is_a_timeout_announced_and_the_result_is_the_serial_one_never_empty(self):
        """(b2) of the reviewer's round 7 on fork PR #781: the bound's expiry is distinguishable from a clean empty result,
        shown end to end. A real pool of this class's shape (a fresh executor, the class's own set aside) is handed a worker
        that sleeps past a bound of 0.2 s; the read times out while the worker still sleeps, the class degrades ANNOUNCED
        (ONE RuntimeWarning and ONE stderr line naming TimeoutError and the bound), the construction is built here, and it
        reads the same as a serial build over the same spec: a Census carrying the planted tenth row and BASE + 1 content
        rows, so a timeout never yields an empty census silently. The drop KILLS the sleeper (round 8, extra6-1): its
        future ends broken, never with a result, and no worker of the dropped pool outlives the test. The class's own pool
        comes back after the test. Fails naming the reason where the pool was lost, as the pool-taken pin does (the road it
        pins did not run), the declared environment limitation the only skip."""
        cls = type(self)
        self._pool_or_fail()
        spec = self._pool_specs()[0]
        pool = cls._new_pool()
        self.addCleanup(type(self)._drop_pool, pool)       # the DROP (round 9): a join here waited out the sleeper if anything between the submit and the drop raised
        wedged = pool.submit(time.sleep, 900.0)             # past the bound by far; the drop kills it, nothing waits for it
        time.sleep(0.5)                                     # the executor spawns a worker for the submit; read the table settled
        workers = list(pool._processes.values())
        manager = pool._executor_manager_thread              # the reaper of the killed workers; read before shutdown() nulls it
        self.assertTrue(workers, "the pool has a worker for the sleeper")
        err = io.StringIO()
        with mock.patch.object(cls, "_pool", pool), mock.patch.object(cls, "_pool_reason", None), mock.patch.object(cls, "roads", []), \
                mock.patch.object(cls, "built", collections.Counter()), mock.patch.object(cls, "POOL_READ_TIMEOUT", 0.2), \
                contextlib.redirect_stderr(err), warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            first = self._resolve(_Pending(spec, wedged))
            self.assertIsNone(cls._pool, "the pool is dropped at the timeout")
            self.assertIsInstance(wedged.exception(timeout=30), BrokenProcessPool,
                                  "the sleeper's future ends broken: the drop killed its worker, and nothing waited for the sleep")
            # The exit codes are read after the manager thread's own join of the workers, the way the driver pin below reads
            # them (round 8's small-input commit): the manager marks the pool broken BEFORE it joins the workers, and with the
            # rebuild here down from 1.3 s to 7 ms this test reached the codes while the manager was still in that join, so
            # the two threads raced on waitpid for the same Process objects, and the one that loses reads ECHILD as no exit
            # code (None, not a survivor). Bounded, so a manager that never finishes fails here rather than hanging.
            manager.join(30)
            self.assertFalse(manager.is_alive(), "the executor's manager thread finished: the reaping is done")
            for w in workers:
                w.join(30)
            self.assertEqual({w.exitcode for w in workers}, {-signal.SIGKILL}, "every worker killed and reaped: %r" % [(w.pid, w.exitcode) for w in workers])
            reason = "the census pool failed under a batch: TimeoutError: no result within 0.2 s"
            self.assertEqual(cls._pool_reason, reason)
            self.assertEqual(cls.built, {"serial": 1}, "the timed-out construction was built here")
        lines = err.getvalue().splitlines()
        self.assertEqual(len(lines), 1, lines)
        self.assertTrue(lines[0].startswith("[EnvRowsCensusBlindSpots] %s; " % reason), lines[0])
        self._assert_announced(caught, lines[0])
        self.assertIsInstance(first, Census, "a timeout yields the census built here, never an empty result: %r" % (first,))
        self._assert_tenth_found(first, "self")
        self.assertEqual(self._reads_of([first]), self._reads_of(self._comparison([spec])), "the serial build's equal")
        self.assertIsNotNone(cls._pool, "the class's own pool is back")

    def test_a_construction_that_raises_inside_the_pooled_work_reaches_the_test_as_itself_and_never_degrades_the_class(self):
        """(v3) of the reviewer's round 7 on fork PR #781: a programming error inside the pooled work, an AttributeError the
        census code should never raise, is the test's own error and not a pool failure. The road, by reading: the worker's
        `build_census` catches the construction's exception and returns it as DATA, a ("raised", exc) payload with the
        worker's traceback on it, so `_resolve`'s catch of POOL_FAILURES never sees it; `_unpack` wraps it in a `_Raised`,
        and `_take` re-raises it here where the test asked for the result, the worker's traceback as its cause; `_serial`
        carries a serial construction's exception the same way. Planted: a spec whose sources carry a non-string qualifier,
        which Census.__init__ splits as its first use of the sources. Asserted: the exception reaches this test as the
        AttributeError it is, and the class did NOT degrade for it (the pool where it was, no reason recorded, no stderr
        line, no RuntimeWarning, the construction counted to the road that built it). Red with the read's catch widened to
        every exception and the worker's payload re-raised at the read: the class degraded and rebuilt here instead."""
        cls = type(self)
        pool_up, reason_before = cls._pool is not None, cls._pool_reason
        files = self._pool_specs()[0][0]                                          # the tenth-row copy's files
        plants = ((AttributeError, "split", dict(DEFAULT_SOURCES, func={("sdk_backend.py", 5): "env"})),   # a qualifier the census cannot split
                  (TypeError, "unpack", dict(DEFAULT_SOURCES, func={5: "env"})))                          # a key the census cannot unpack
        for exc_type, word, broken in plants:
            with self.subTest(raises=exc_type.__name__):
                err = io.StringIO()
                with mock.patch.object(cls, "roads", []), mock.patch.object(cls, "built", collections.Counter()), \
                        contextlib.redirect_stderr(err), warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    results = self._censuses([(files, broken)])
                    # distinguishable from a clean empty result by construction: the read returns a _Raised, never a Census
                    # and never None (round 8 of the review, 2026-09-21, extra6-2)
                    resolved = self._resolve(results[0])
                    self.assertIsInstance(resolved, _Raised, "the read hands back the exception as data, not an empty census: %r" % (resolved,))
                    self.assertIsInstance(resolved.exc, exc_type)
                    with self.assertRaises(exc_type) as cm:
                        self._take(resolved)
                    self.assertIs(cls._pool is not None, pool_up, "the pool is where it was: a failure of the work is not a pool failure")
                    self.assertEqual(cls._pool_reason, reason_before, "no degradation recorded for a failure of the work")
                    self.assertEqual(cls.roads, ["pool"] if pool_up else ["serial (%s)" % reason_before])
                    self.assertEqual(cls.built, {"pool": 1} if pool_up else {"serial": 1}, "counted to the road that built it")
                self.assertIn(word, str(cm.exception), "the census's own error, as itself: %r" % (cm.exception,))
                self.assertEqual(err.getvalue(), "", "no degradation line for a failure of the work")
                self.assertEqual([str(w.message) for w in caught if w.category is RuntimeWarning], [],
                                 "no degradation warning for a failure of the work: the class degraded instead of raising it as itself")
                if pool_up:
                    self.assertIsInstance(cm.exception.__cause__, _WorkerTraceback, "the worker's traceback travels as the cause")
                    self.assertIn(word, cm.exception.__cause__.args[0], "and names the line that raised")

    def test_the_pool_road_pin_fails_on_a_lost_pool_and_skips_on_the_declared_environment_limitation_alone(self):
        """Both arms of `_pool_or_fail` (round 8 of the review, 2026-09-21, extra6-2; a guard is run against what it refuses
        and what it admits): with the pool lost for a real reason (a planted start failure of the kind a defect raises, and
        a pool broken under a batch) the pin FAILS naming the reason; with the pool lost for the declared environment
        limitation, the stdlib's NotImplementedError from _check_system_limits in either of its two spellings, it skips
        naming that; a reason spelled like the limitation but not about semaphores is no limitation and fails. With the
        pool up, the pool is returned. The exception is CAPTURED inside the patch context and judged after it (round 9 of
        the review, tests-1): with `assertRaises(AssertionError)` a SkipTest raised by a `_pool_or_fail` that skipped on
        every reason escaped the assertRaises, the enclosing subTest recorded a SKIP, and the run exited 0, so the guard
        over the very decision it guards reported success; a skipping pin is worse than a missing one. Red with the skip put
        back on every reason (the condition in `_pool_or_fail` replaced by `if True:`): 4 failed, 1 passed, 2 subtests
        passed; with the limitation widened (the semaphore conjunct dropped): 1 failed, 1 passed, 5 subtests passed; the
        round-8 shape passed both (1 passed, 4 skipped; 1 passed, 1 skipped)."""
        cls = type(self)
        real = ["the census pool could not start: RuntimeError: planted: a start failure the pool's own failures do not name",
                "the census pool failed under a batch of 2: BrokenProcessPool: planted: every worker is gone",
                "the census pool failed under a batch: TimeoutError: no result within 0.2 s",
                "the census pool could not start: NotImplementedError: planted: a refusal that is not the stdlib's"]
        for reason in real:
            with self.subTest(fails=reason[:60]):
                raised = None
                with mock.patch.object(cls, "_pool", None), mock.patch.object(cls, "_pool_reason", reason):
                    try:
                        self._pool_or_fail()
                    except Exception as e:      # captured here: an escaping SkipTest marks the subtest SKIPPED, which reports as success
                        raised = e
                self.assertIsInstance(raised, AssertionError,
                                      "the pin FAILS on a pool lost for this reason (never skips, never returns): %r" % (raised,))
                self.assertNotIsInstance(raised, unittest.SkipTest)   # implied by the line above; the statement of what round 8's shape let through
                self.assertIn(reason, str(raised), "the failure names the reason")
        limitation = ["the census pool could not start: NotImplementedError: This Python build lacks multiprocessing.synchronize, "
                      "usually due to named semaphores being unavailable on this platform.",
                      "the census pool could not start: NotImplementedError: system provides too few semaphores (32 available, 256 necessary)"]
        for reason in limitation:
            with self.subTest(skips=reason[:60]):
                with mock.patch.object(cls, "_pool", None), mock.patch.object(cls, "_pool_reason", reason):
                    with self.assertRaises(unittest.SkipTest) as cm:
                        self._pool_or_fail()
                self.assertIn(reason, str(cm.exception), "the skip names the limitation")
        if cls._pool is not None:
            self.assertIs(self._pool_or_fail(), cls._pool, "with the pool up, the pool")

    def test_a_pool_lost_inside_any_test_fails_that_test_in_its_teardown_naming_the_reason(self):
        """The class's tearDown (round 8 of the review on fork PR #781, extra6-2's second pass, by its mutation verifier): a
        pool lost DURING a test fails that test, naming the reason, whatever the test's place in the class's order. The pins
        that need the pool road fail only for a loss before them (`_pool_or_fail`), and a loss planted inside a test sorted
        after them left the run green, the RuntimeWarning its only trace. Run through unittest's own machinery on a probe
        subclass with pool slots of its own (so the planted loss drops nothing of this class's): a test that loses the pool
        through `_pool_lost`, the one road every degradation takes, FAILS in tearDown and the failure names the reason; a
        test that loses nothing passes; and a test under a reason recorded BEFORE it (the start failure's shape, set in
        setUpClass) passes, since that loss is the pool-road pins' to report and not every test's (a tearDown failing on
        any recorded reason would fail the whole class at a start failure the pins already name). Red at round 8's
        commit: the losing test passed, no failure recorded."""
        cls = type(self)
        reason = "the census pool failed under a batch: TimeoutError: planted: no result within 0.2 s"
        start_failure = "the census pool could not start: RuntimeError: planted: a start failure recorded before the test"

        class Probe(cls):
            _pool = None                       # its own slots: the loss below is Probe's and drops nothing of the class's
            _pool_reason = None

            def test_loses_the_pool(self):
                type(self)._pool_lost(reason)

            def test_loses_nothing(self):
                pass

        def run_probe(name, reason_before=None):
            Probe._pool_reason = reason_before
            result = unittest.TestResult()
            with contextlib.redirect_stderr(io.StringIO()), warnings.catch_warnings(record=True):
                warnings.simplefilter("always")
                Probe(name).run(result)
            self.assertEqual(result.testsRun, 1)
            return result

        lost = run_probe("test_loses_the_pool")
        self.assertEqual(len(lost.failures), 1, "the test that lost the pool fails: failures %r, errors %r" % (lost.failures, lost.errors))
        self.assertEqual(lost.errors, [], "a failure (self.fail), never an error")
        self.assertIn("the census pool was lost during this test", lost.failures[0][1])
        self.assertIn(reason, lost.failures[0][1], "the failure names the reason")
        self.assertTrue(run_probe("test_loses_nothing").wasSuccessful(), "a test that loses nothing passes")
        before = run_probe("test_loses_nothing", reason_before=start_failure)
        self.assertTrue(before.wasSuccessful(),
                        "a reason recorded before the test is the pool-road pins' to report, not this test's: %r" % (before.failures,))

    WEDGED_EXIT_LIMIT = 150.0    # seconds the driver below has to EXIT. Its own work is a few seconds (the module's import,
                                 # one worker's start, a 0.5 s bound, one census built here, a 15 s join at most); the
                                 # planted sleep is 900 s, so an exit within the limit means the drop did not wait for it

    def test_the_class_end_digest_covers_the_structural_rosters_a_population_pin_reads(self):
        """extra7-1 (round 9 of the review): the freeze's class-end backstop claimed that a change by any pin, in any order,
        is red at the end of the class, while census_digest covered summary() and the tables outside it and NOT the
        structural rosters: Mod.fns (what the population pin reads for CREDENTIALS_FNS), Fn.calls, callees, callers and
        ident_consts, so a base-class `list.append` on one of them (the deliberate act FrozenList's docstring names) changed
        what the next pin read and the class-end check reported nothing. The digest covers the five by value now, and its
        docstring and the three claims name what is outside it. Executed on a frozen census over a fresh copy of the small
        module (a distinct input, read through the census() door so it is frozen and carries digest_at_birth, as the door's
        censuses do): each roster is a FrozenList whose own append refuses; a base-class append on it changes the digest,
        and the pop restores it. Red at the round-8 head: the digest was byte-identical across all five."""
        path = self._copy(lambda src: src + "\n# a copy for the digest pin\n")
        c = erc.census((path,))
        self.assertIsInstance(c, erc.FrozenCensus)
        d0 = c.digest_at_birth
        self.assertEqual(erc.census_digest(c), d0, "two reads of an unchanged census digest the same")
        mod = c.mods[os.path.realpath(path)]
        fn = c.writer
        some_call = next(call for f in c.all_fns for call in f.calls)
        self.assertIn(id(some_call), c.callees)
        self.assertIn(fn, c.callers, "the writer has callers in the small module")
        self.assertTrue(c.ident_consts, "the small module spells identifiers as strings")
        rosters = {"Mod.fns": (mod.fns, fn), "Fn.calls": (fn.calls, some_call), "callees": (c.callees[id(some_call)], (fn, "self")),
                   "callers": (c.callers[fn], (some_call, fn, "self")), "ident_consts": (c.ident_consts, c.ident_consts[0])}
        for label, (roster, item) in rosters.items():
            with self.subTest(roster=label):
                self.assertIsInstance(roster, erc.FrozenList, "%s is a frozen list: its own append refuses, so the base-class call is the deliberate act" % label)
                with self.assertRaises(TypeError):
                    roster.append(item)
                list.append(roster, item)
                try:
                    self.assertNotEqual(erc.census_digest(c), d0, "%s: a base-class append on the frozen roster changes the class-end digest" % label)
                finally:
                    list.pop(roster)
                self.assertEqual(erc.census_digest(c), d0, "%s: restored, the digest is the birth digest again" % label)

    RING_WRITER_NAMED_LOG = ("class Ring:\n"
                             "    def __init__(self):\n"
                             "        self._problems = []\n"
                             "    def log(self, m, problem=None, key=None, ring_text=None):\n"
                             "        self._problems.append({'text': m})\n"
                             "    def problems(self):\n"
                             "        return list(self._problems)\n"
                             "def relay(rec, sess):\n"
                             "    rec.log('env (%s): relayed %s' % (sess.name, ', '.join(sess.env_vars)), problem=True)\n")
    COLLIDING_CONDUIT = ("class Recorder:\n"
                         "    def %s(self, m, problem=None, ring_text=None):\n"
                         "        BACKEND._log(m, problem=problem, ring_text=ring_text)\n"
                         "def caller(rec, sess):\n"
                         "    rec.%s('env (%%s): planted %%s' %% (sess.name, ', '.join(sess.env_vars)), problem=True)\n")

    def test_a_door_spelled_like_a_stdlib_method_is_rescued_by_its_name_and_a_colliding_conduit_is_loud(self):
        """fresh-1 (round 9 of the review): the COMMON_METHODS filter drops the call edges of a CONDUIT whose bare name is a
        stdlib method's and which is called on a receiver the walk cannot type: the site files no door call, the inner
        call loses its taint, no failure row. Round 8 rescued the writer's spelling by name (`COMMON_METHODS.discard("_log")`)
        and left `log`, a logging.Logger method and the parameter road's own handle, filtered. Two pins on synthetic inputs:
        (1) the rescue is DERIVED from the door names the census knows, so a ring writer named `log` called on an untyped
        receiver resolves (the writer's own name is a handle); (2) a conduit whose bare name collides and is no handle is a
        census FAILURE naming it (conduit-name-common), where the same conduit under a plain name is followed with its
        taint. Red at the round-8 head: (1) the untyped call resolved to nothing (callers of the writer: none); (2) failures
        [] and the colliding conduit's site absent, silently."""
        c = Census((self._plant("ring_log.py", self.RING_WRITER_NAMED_LOG),), DEFAULT_SOURCES)
        self.assertEqual((c.door, sorted(c.door_names)), ("log", ["log"]), "the door's own name is its handle, derived")
        self.assertIn("log", erc.COMMON_METHODS, "and it is a stdlib method name, which is what the rescue is for")
        self.assertEqual(sorted(caller.qual for _call, caller, _via in c.callers.get(c.writer, [])), ["relay"],
                         "the untyped receiver's call resolves to the door: its name is a handle, so COMMON_METHODS does not filter it")
        self.assertEqual([(dc.owner, dc.kind) for dc in c.door_calls], [("relay", "typed")])
        self.assertEqual(list(c.failures), [])
        small = small_module_files()
        loud = Census(small + (self._plant("plant_common.py", self.COLLIDING_CONDUIT % ("log", "log")),), DEFAULT_SOURCES)
        self.assertEqual(sorted(loud.door_names), ["_log"], "the small module's handles: the writer's name alone (no parameter of it takes the door)")
        self.assertEqual([(k, b, ln) for k, b, ln, _t in loud.failures], [("conduit-name-common", "plant_common.py", 2)],
                         "the colliding conduit is named as a failure, by site")
        self.assertIn("Recorder.log is a conduit whose bare name 'log' is a stdlib method name", loud.failures[0][3])
        self.assertEqual([dc.lineno for dc in loud.door_calls if dc.base == "plant_common.py" and dc.owner == "caller"], [],
                         "the colliding conduit's site is unseen, which is why the failure must be loud")
        plain = Census(small + (self._plant("plant_plain.py", self.COLLIDING_CONDUIT % ("noted", "noted")),), DEFAULT_SOURCES)
        self.assertEqual(list(plain.failures), [])
        self.assertEqual([(dc.lineno, dc.owner, dc.kind, sorted(dc.taint)) for dc in plain.door_calls if dc.base == "plant_plain.py"],
                         [(3, "noted", "typed", ["env"]), (5, "caller", "conduit:Recorder.noted", ["env"])],
                         "the same conduit under a plain name: its inner door call and its site, both env-tainted")

    def test_a_worker_that_never_returns_does_not_hold_the_interpreters_exit_once_the_pool_is_dropped(self):
        """The bound BOUNDS (round 8 of the review, 2026-09-21, extra6-1): a worker that never returns within the run, a
        read that gives up at the bound, the pool dropped, and then the interpreter's EXIT, which is where the round-7
        drop still waited. Run as a driver in a subprocess with a wall-clock limit (WEDGED_WORKER_DRIVER: a pool of this
        class's shape, a worker sleeping 900 s, the bound at 0.5 s, `_resolve` over the sleeper's future), since the
        wait was the exit's own. Asserted: the driver exits within WEDGED_EXIT_LIMIT with status 0; the read returned a
        Census built here (never empty) naming TimeoutError and the bound; every worker's exit code reads back as
        SIGKILL's, so each was killed AND reaped (an exit code is read from a reaped process); the manager thread had
        finished; the sleeper's future ended broken, never with a result; and the degradation announced itself in the
        driver too. Red before the drop killed the workers: the driver printed its lines and then did not exit, the
        interpreter joining the manager thread that waited on the sleeper (150 s here, 900 s left alone); this test then
        kills the driver's process group (its pid, recorded here) and fails."""
        self._pool_or_fail()
        driver = WEDGED_WORKER_DRIVER % {"here": HERE, "sleep": 900.0, "join": 15.0}
        t0 = time.monotonic()
        proc = subprocess.Popen([sys.executable, "-c", driver], cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
        try:
            out, err = proc.communicate(timeout=self.WEDGED_EXIT_LIMIT)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)     # the driver's own session: it and the spawn workers it started, nothing else
            out, err = proc.communicate()
            self.fail("the driver did not exit within %g s: the drop still holds the interpreter's exit on the wedged worker\n"
                      "stdout: %s\nstderr: %s" % (self.WEDGED_EXIT_LIMIT, out[-2000:], err[-2000:]))
        elapsed = time.monotonic() - t0
        self.assertEqual(proc.returncode, 0, "the driver exited cleanly: %s" % err[-3000:])
        lines = out.splitlines()
        resolved = [ln for ln in lines if ln.startswith("resolved ")]
        self.assertEqual(len(resolved), 1, out)
        self.assertTrue(resolved[0].startswith("resolved Census in "), "the timed-out read is a census built here, never empty: %s" % resolved[0])
        self.assertIn("the census pool failed under a batch: TimeoutError: no result within 0.5 s", resolved[0])
        workers = json.loads([ln for ln in lines if ln.startswith("workers ")][0][len("workers "):])
        self.assertTrue(workers, "the pool had a worker for the sleeper")
        self.assertEqual({code for _pid, code in workers}, {-signal.SIGKILL},
                         "every worker was killed (SIGKILL) and reaped (its exit code read back): %r" % (workers,))
        self.assertIn("manager alive False", lines, "the executor's manager thread finished: the reaping is done, the exit has nothing to join")
        self.assertIn("wedged BrokenProcessPool", lines, "the sleeper's future ended broken, never with a result")
        self.assertIn("RuntimeWarning", err, "the degradation announced itself in the driver too")
        self.assertLess(elapsed, self.WEDGED_EXIT_LIMIT)

    def test_a_worker_wedged_on_a_result_no_test_read_does_not_hold_the_class_end(self):
        """The third join (round 9 of the review, correctness-2 and extra10-3): round 7's drop rule reached _pool_lost and
        _new_pool's start arm, and tearDownClass still joined the pool with wait=True, so a worker wedged on a batch result
        no test read (a test that failed mid-batch leaves the rest of its futures unread; batches are read lazily) held the
        pytest process open at the class's end, and pytest-timeout's per-test timer, cancelled by the failure that left the
        future unread, never bounded it. Run as a driver in a subprocess with a wall-clock limit (WEDGED_TEARDOWN_DRIVER:
        a pool of this class's shape, a worker sleeping 900 s never read, then tearDownClass as the class ships it).
        Asserted: the driver exits within WEDGED_EXIT_LIMIT with status 0; tearDownClass returned; every worker's exit
        code reads back as SIGKILL's; the manager thread finished; the sleeper's future ended broken. Red at the round-8
        head: the driver printed "calling tearDownClass" and did not exit; this test killed its process group and failed.
        The population of joins on this class's pool, every one bounded or a drop: _new_pool's probe read
        (POOL_START_TIMEOUT), _take's result read (POOL_READ_TIMEOUT), the sleeper pin's manager and worker joins and its
        future read (30 s each), both drivers' joins (their `join` parameter), _drop_pool's shutdown(wait=False) at
        _pool_lost, _new_pool's start arm, the sleeper pin's cleanup and here."""
        self._pool_or_fail()
        driver = WEDGED_TEARDOWN_DRIVER % {"here": HERE, "sleep": 900.0, "join": 15.0}
        t0 = time.monotonic()
        proc = subprocess.Popen([sys.executable, "-c", driver], cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
        try:
            out, err = proc.communicate(timeout=self.WEDGED_EXIT_LIMIT)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid, signal.SIGKILL)     # the driver's own session: it and the spawn workers it started, nothing else
            out, err = proc.communicate()
            self.fail("the driver did not exit within %g s: tearDownClass still joins the wedged worker\nstdout: %s\nstderr: %s"
                      % (self.WEDGED_EXIT_LIMIT, out[-2000:], err[-2000:]))
        elapsed = time.monotonic() - t0
        self.assertEqual(proc.returncode, 0, "the driver exited cleanly: %s" % err[-3000:])
        lines = out.splitlines()
        self.assertIn("calling tearDownClass", lines, out)
        returned = [ln for ln in lines if ln.startswith("teardown returned in ")]
        self.assertEqual(len(returned), 1, "tearDownClass returned: %s" % out)
        workers = json.loads([ln for ln in lines if ln.startswith("workers ")][0][len("workers "):])
        self.assertTrue(workers, "the pool had a worker for the sleeper")
        self.assertEqual({code for _pid, code in workers}, {-signal.SIGKILL},
                         "every worker was killed (SIGKILL) and reaped (its exit code read back): %r" % (workers,))
        self.assertIn("manager alive False", lines, "the executor's manager thread finished: the exit has nothing to join")
        self.assertIn("wedged BrokenProcessPool", lines, "the sleeper's future ended broken, never with a result")
        self.assertLess(elapsed, self.WEDGED_EXIT_LIMIT)


class CensusParseRetention(unittest.TestCase):
    """The parse cache's retention rule (fork PR #781, the reviewer's ruling of 2026-09-20): tests/env_ring_census.py
    keeps a parsed tree for the process's life for the census's canonical inputs alone (retained_paths, derived from
    DEFAULT_FILES), any other path is parsed for the construction that asked and dropped after it, and the `census()`
    door keeps a Census under the same rule. Until the rule every parsed path stayed: the blind-spot class above
    constructed (until round 8's small-input commit; its copies are of the small module SMALL_SDK_BACKEND since) about
    180 censuses over as many sabotaged copies of kernel/sdk_backend.py, each construction left about
    165k objects alive under a dead path, and late in the module every gen-2 collection walked tens of millions of
    objects (the finding at the pushed head, serial, a plugin timing every construction: 154 of 185 constructions in
    1.0 to 1.5 s, 14 at or above 2 s carrying 120.5 s, the slowest 21.8 s, each slow one holding exactly one gen-2
    collection). Over 30 plain copies in one process, serial, at the previous commit: the gen-2 pauses grew from 0.23 s
    at the second copy to 3.42 s at the 27th, 10 collections carrying 14.5 of 44.0 s, the cache at 31 entries; with the
    rule, the pauses stayed at 0.28 to 0.58 s, 15 collections carrying 7.0 of 33.8 s, the cache at 1 entry. The census
    result cannot depend on where a tree came from, and the differential over the real pair and 40 plants at both heads
    found 41 compared, 41 identical, 0 different. The pins here are rules, not figures: a foreign path is not retained
    and a canonical one is, the retained set is the canonical table's, the door keeps the sites' set alone, and the
    count of retained trees does not grow with the number of constructions. gc is neither disabled nor tuned: the
    heap that grew was the cache's, and the fix is at the cache. The foreign input here is a copy of the small module
    (round 8's small-input commit: the cache keys on the PATH, so any foreign path shows the rule, and the small module
    is the smallest input with a writer for the census to find) beside kernel/credentials.py, the smallest canonical
    input, which is what shows the retention; until that commit the copies were of kernel/sdk_backend.py itself."""

    def _copy(self):
        """A copy of the small module at a fresh path: the same bytes, a foreign path."""
        path = os.path.join(tempfile.mkdtemp(), "sdk_backend.py")
        shutil.copyfile(small_module_files()[0], path)
        return path

    def _plant(self, name, src):
        path = os.path.join(tempfile.mkdtemp(), name)
        Path(path).write_text(src, encoding="utf-8")
        return path

    def test_a_foreign_path_is_parsed_for_its_construction_and_not_retained(self):
        """A census over a copy walks the copy (the base rows come out of it) and the cache holds the copy's path
        afterwards no more than before; the canonical input the same construction parsed is held. Red before on the
        NotIn: the copy's realpath was a cache key for the process's life."""
        path = self._copy()
        c = Census((path, CREDENTIALS_PY), DEFAULT_SOURCES)
        self.assertEqual((c.writer.qual, c.writer.file), ("SdkBackend._log", os.path.realpath(path)), "the copy was the construction's input: its writer is found in it")
        self.assertIn(os.path.realpath(path), c.mods, "and its Mod, with the tree, is the Census's own")
        self.assertNotIn(os.path.realpath(path), erc.ASTS, "a foreign path is parsed for its construction, not retained")
        self.assertIn(os.path.realpath(CREDENTIALS_PY), erc.ASTS, "the canonical input the construction parsed is retained")
        parsed_canonical = [f for f in CENSUS_FILES if os.path.realpath(f) in erc.retained_paths()]
        self.assertTrue(parsed_canonical, "the sites' files include canonical inputs")
        census(CENSUS_FILES)
        for f in parsed_canonical:
            self.assertIn(os.path.realpath(f), erc.ASTS, "every canonical input parsed so far is retained: %s" % f)

    def test_the_retained_set_is_the_canonical_table(self):
        """retained_paths() is DEFAULT_FILES by realpath, read from the table (a scratch copy of the census module with
        the table cut to two files retains two, and this pin's expected value follows it), and after the sites' census
        the cache holds exactly that set: a synthetic path parsed through `parsed` itself is not in it. Red before on the
        set equality: the synthetic path was a key."""
        expected = frozenset(os.path.realpath(f) for f in erc.DEFAULT_FILES)
        self.assertTrue(expected, "the canonical table is not empty")
        self.assertEqual(erc.retained_paths(), expected)
        foreign = self._plant("synthetic.py", "X = 1\n")
        src, tree = erc.parsed(foreign)
        self.assertEqual((src, type(tree).__name__), ("X = 1\n", "Module"), "the foreign path was parsed")
        census(CENSUS_FILES)
        self.assertEqual(frozenset(erc.ASTS), expected, "the cache holds the canonical inputs and nothing else")

    def test_the_door_keeps_the_sites_census_and_not_a_foreign_set(self):
        """`census(CENSUS_FILES)` is one object per process (the sites share it; a canonical table that dropped one of
        this module's files would make every site construct anew, and this pin reds on it), while a set with a foreign
        path is computed for the call and leaves the door's cache the size it was. Red before on the size: the foreign
        set was kept, with its trees."""
        self.assertIs(census(CENSUS_FILES), census(CENSUS_FILES), "the sites' census is kept")
        held = len(erc._CENSUS)
        self.assertGreater(held, 0, "the door holds the sites' census")
        path = self._copy()
        c = census((path, CREDENTIALS_PY))
        self.assertEqual((c.writer.qual, c.writer.file), ("SdkBackend._log", os.path.realpath(path)), "the foreign set was computed")
        self.assertEqual(len(erc._CENSUS), held, "and not kept")
        self.assertNotIn(os.path.realpath(path), erc.ASTS, "nor its tree")

    def test_the_count_of_retained_trees_does_not_grow_with_the_constructions(self):
        """After N constructions over N copies the cache's size is the same for N = 3 and N = 6, and not zero (the
        canonical input each construction parsed is in it): the rule, not a figure. Red before: 3 and 6 more entries."""
        def construct(n):
            for _ in range(n):
                c = Census((self._copy(), CREDENTIALS_PY), DEFAULT_SOURCES)
                self.assertEqual(c.writer.qual, "SdkBackend._log", "each copy was walked")
            return len(erc.ASTS)
        after_three = construct(3)
        after_six = construct(3)
        self.assertGreater(after_three, 0, "the canonical input is retained")
        self.assertEqual(after_six, after_three, "the count of retained trees does not grow with the constructions")


class LogQuietlyAtRuntime(_Backend):
    """The runtime half of _log_quietly's problem=False (round 6; its lexical half is the census's rule (2)): a line
    through the conduit inside a live except handler, where _log's default would file it, lands on the kernel log
    and NOT on the ring, while a bare _log in the same handler does file, which shows the handler was live."""

    def test_a_line_through_the_conduit_inside_a_live_handler_is_no_ring_row(self):
        lines = []
        self.be._log_cb = lines.append
        sid = self.be.spawn("web", "/tmp", env=ENV)
        s = self._sess(sid)
        try:
            raise RuntimeError("probe")
        except RuntimeError:
            self.be._log("probe: a bare line in a live handler")
            s._log_quietly("reconnect (web): a routine line through the conduit")
        texts = [r["text"] for r in self.be.problems()]
        self.assertIn("probe: a bare line in a live handler", texts, "the handler was live: _log's default filed the bare line")
        self.assertEqual([t for t in texts if "through the conduit" in t], [], "the conduit's line is no ring row")
        self.assertIn("reconnect (web): a routine line through the conduit", lines, "the kernel log keeps it")

    def test_a_failure_report_through_the_conduit_from_its_own_handler_is_one_ring_row(self):
        """Round 7 of the review (2026-09-20, regression-1 and extra5-1): the merge of main resolved _log_quietly so that a
        caller saying nothing of problem= takes the problem=False road, which demoted the five failure reports main's fork PR #787
        files inside except handlers to kernel-log lines nobody reads. Each passes problem=True itself now. Driven on
        _reconcile_seeded_work's except road: a lock that refuses raises inside the reconcile, and the guard's one line is
        one ring row (be.problems()) and one kernel-log line. Red at the round-6 head: 0 ring rows, the line in the kernel
        log alone."""
        lines = []
        self.be._log_cb = lines.append
        sid = self.be.spawn("web", "/tmp", env=ENV)
        s = self._sess(sid)

        class _Refusing:
            def __enter__(self):
                raise RuntimeError("the lock refused")

            def __exit__(self, *a):
                return False
        s._sub_lock = _Refusing()
        s._reconcile_seeded_work()
        want = "live work (web): the seeded-work reconcile failed: RuntimeError: the lock refused"
        self.assertEqual([r["text"] for r in self.be.problems() if "the seeded-work reconcile failed" in r["text"]], [want],
                         "the caught exception's report is one ring row (as on main before the merge)")
        self.assertEqual([l for l in lines if "the seeded-work reconcile failed" in l], [want], "and one kernel-log line")

    def test_a_failure_report_that_repeats_counts_on_one_ring_row_keyed_by_site_session_and_exception_class(self):
        """The conduit's keyed sentence by execution (round 8 of the review, 2026-09-21, kernel-2 and extra7-2): the five
        failure reports the merge of main brought passed problem=True with no key, so a failure repeating at every settle
        appended a ring row per occurrence and bumped problem_seq, the feed's cache key, each time, and a hundred of them
        evicted the ring; the same five sites are unkeyed on main, so this tightens main's behaviour rather than repairing
        a regression of this change. Each of the five is keyed (site label, sid, exception class) now. Driven twelve times
        on _reconcile_seeded_work's except road with one failure: ONE ring row, its key the triple, its count 12, its text
        the first line with the repeat suffix, problem_seq up by ONE, twelve kernel-log lines (the log keeps each); then a
        second exception class at the same site is a second row, since the class is in the key and a distinct cause is not
        hidden behind the first. Red at round 7's head: twelve rows and problem_seq up by twelve."""
        lines = []
        self.be._log_cb = lines.append
        sid = self.be.spawn("web", "/tmp", env=ENV)
        s = self._sess(sid)

        class _Refusing:
            def __init__(self, exc):
                self.exc = exc

            def __enter__(self):
                raise self.exc

            def __exit__(self, *a):
                return False
        seq0 = self.be.problem_seq()
        s._sub_lock = _Refusing(RuntimeError("the lock refused"))
        for _ in range(12):
            s._reconcile_seeded_work()
        want = "live work (web): the seeded-work reconcile failed: RuntimeError: the lock refused"
        rows = [r for r in self.be.problems() if "the seeded-work reconcile failed" in r["text"]]
        self.assertEqual(len(rows), 1, "twelve occurrences, one ring row: %r" % ([r["text"][:70] for r in rows],))
        self.assertEqual(rows[0]["key"], ("seeded-reconcile-failed", sid, "RuntimeError"), "keyed by site label, session and exception class")
        self.assertEqual((rows[0]["count"], rows[0]["first"]), (12, want))
        self.assertTrue(rows[0]["text"].startswith(want + " (11 repeats this kernel life;"), rows[0]["text"])
        self.assertEqual(self.be.problem_seq(), seq0 + 1, "one cache bust for a recurring failure, not one per occurrence")
        self.assertEqual([l for l in lines if "the seeded-work reconcile failed" in l], [want] * 12, "the kernel log keeps every line")
        s._sub_lock = _Refusing(OSError("the lock's file is gone"))
        s._reconcile_seeded_work()
        rows = [r for r in self.be.problems() if "the seeded-work reconcile failed" in r["text"]]
        self.assertEqual([r["key"] for r in rows], [("seeded-reconcile-failed", sid, "RuntimeError"), ("seeded-reconcile-failed", sid, "OSError")],
                         "a second cause at the same site is its own row")
        self.assertEqual(self.be.problem_seq(), seq0 + 2)

class FlagSettingsLockOrder(_OptionsBackend):
    """The callee half of _flag_settings_lock's order sentence, pinned by execution (correctness-3, tests-4, regression-2;
    review round 4 of the env-pick door, 2026-09-19: the round-3 mutation pass had left it as prose, calling it a claim
    about every caller's stack, and the reviewer showed the population is one call site and the held state of a lock
    is readable). A stand-in for the module's lock records, at its acquisition inside the real _options, which of the
    module-level locks and of the four locks the two order statements name are held by this thread; the writer must
    find none. The caller-side half is EnvRowsPopulation's census."""

    def test_the_writer_takes_its_lock_with_no_other_lock_of_the_module_held(self):
        lock_types = (type(threading.Lock()), type(threading.RLock()))
        module_locks = {n: v for n, v in vars(sb).items() if isinstance(v, lock_types) and n != "_flag_settings_lock"}
        self.assertGreaterEqual(len(module_locks), 4, "the module-level locks the probe reads: %r" % (sorted(module_locks),))
        sid = self.be.spawn("web", "/tmp", env=ENV)
        sess = self._sess(sid)
        named = {"be._lock": self.be._lock, "be._reg_lock": self.be._reg_lock, "sess._lock": sess._lock,
                 "sess._persist_lock": sess._persist_lock}
        for n, lock in named.items():
            self.assertIsInstance(lock, lock_types, n)

        def held(lock):
            return lock._is_owned() if hasattr(lock, "_is_owned") else lock.locked()   # an RLock knows its owner; a Lock is held or not
        seen = {"entered": 0, "held": []}

        class _Probe:
            def __enter__(self):
                seen["entered"] += 1
                seen["held"].extend(sorted(n for n, lock in {**module_locks, **named}.items() if held(lock)))

            def __exit__(self, *exc):
                pass
        self.addCleanup(setattr, sb, "_flag_settings_lock", sb._flag_settings_lock)
        sb._flag_settings_lock = _Probe()
        kw = self.be._options(sess, dict)
        self.assertTrue(kw.get("settings"), "the writer ran (the env rides the settings file)")
        self.assertEqual(seen["entered"], 1, "the writer took the module's lock once")
        self.assertEqual(seen["held"], [], "no lock of the module is held when the writer takes its own")
        # the probe reads a held lock: the same walk under one of the named locks names it
        with self.be._reg_lock:
            self.assertEqual([n for n, lock in named.items() if held(lock)], ["be._reg_lock"])
        with sb._defaults_lock:
            self.assertEqual([n for n, lock in module_locks.items() if held(lock)], ["_defaults_lock"])


class SetEnv(_Backend):
    """set_env: set_effort's persist+reconnect shape, minus the UI slice's badge/chip machinery."""

    def _live(self, sid):
        s = self._sess(sid)
        s.request_reconnect = lambda *a, **k: self.reconnects.append(1)
        self.reconnects = []
        self.be.sessions[sid] = s
        return s

    def test_a_change_persists_and_reconnects(self):
        sid = self.be.spawn("web", "/tmp")
        s = self._live(sid)
        self.assertTrue(self.be.set_env(sid, ENV))
        self.assertEqual(self._reg(sid)["env"], ENV)
        self.assertEqual(s.env_vars, ENV)
        self.assertTrue(self.reconnects, "env is connect-time — the reconnect is what applies it")

    def test_an_unchanged_reassert_skips_the_reconnect(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self._live(sid)
        self.assertTrue(self.be.set_env(sid, dict(ENV)))
        self.assertFalse(self.reconnects,
                         "same env = nothing to apply: the fresh-spawn echo and the nightly "
                         "re-brief must not churn the CLI process")

    def test_replace_not_merge(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self._live(sid)
        self.assertTrue(self.be.set_env(sid, {"FEATURE_FLAG": "0"}))
        self.assertEqual(self._reg(sid)["env"], {"FEATURE_FLAG": "0"},
                         "the payload IS the session's per-session env — names not re-asserted drop")

    def test_refuses_junk_and_unknown_sids(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.assertFalse(self.be.set_env(sid, {"9BAD": "1"}))
        self.assertEqual(self._reg(sid)["env"], ENV, "a refused payload must not half-apply")
        self.assertFalse(self.be.set_env(CHILD, ENV), "no reg, no session — refuse, don't mint")

    def test_an_unreadable_registry_is_refused_with_one_row_saying_why(self):
        """Closing review of the env-pick door (2026-09-19): every False from set_env is answered by the kernel's
        _env_refusal, whose sentence tells the caller the backend's log line says why, and the registry road (no
        file for the sid, or a body read_reg returns None for) logged nothing, so on that road the sentence pointed
        at no line. One problem row per refusal: the whole sid and the reason on the kernel log line, the ring text
        bounded by construction (the sid cut to RING_SESSION_BUDGET ahead of fixed text), and nothing of the pick
        on either. Both unreadable registries take the same road."""
        logged = []
        self.be._log = lambda msg, problem=False, **kw: logged.append((msg, problem, kw))
        val = "synthetic-flag-" + uuid.uuid4().hex                          # built at run time; must appear nowhere
        sid = self.be.spawn("web", "/tmp", env=ENV)
        sb._reg_path(self.be.state_dir, sid).write_text("[]")               # a non-object body: read_reg answers None
        for case, target in (("no file", CHILD), ("non-object body", sid)):
            with self.subTest(case=case):
                logged.clear()
                self.assertFalse(self.be.set_env(target, {"FEATURE_FLAG": val}))
                rows = [(m, kw) for m, problem, kw in logged if problem]
                self.assertEqual(len(rows), 1, "one row says why: %r" % (logged,))
                line, kw = rows[0]
                self.assertEqual(line, "env (%s): pick refused: %s" % (target, sb.REFUSAL_NO_REG),
                                 "the whole sid and the reason on the kernel log line")
                self.assertIn("registry could not be read", line)
                self.assertEqual(kw.get("ring_text"),
                                 (sb.REFUSAL_RING_HEAD % sb._cred.cut_to(target, sb.RING_SESSION_BUDGET)) + sb.REFUSAL_NO_REG)
                self.assertTrue(kw["ring_text"].startswith("env (%s%s): pick refused: " % (target[:sb.RING_SESSION_BUDGET - 1], sb._cred.CUT_MARK)),
                                 "the 36-character sid is cut to the session budget in the ring: %s" % kw["ring_text"])
                self.assertLessEqual(len(kw["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)
                self.assertNotIn(val, line); self.assertNotIn(val, kw["ring_text"]); self.assertNotIn("FEATURE_FLAG", line)
        self.assertIsNone(sb.read_reg(self.be.state_dir, sid), "the registry stays as it was: the refusal writes nothing")
        worst = (sb.REFUSAL_RING_HEAD % ("x" * sb.RING_SESSION_BUDGET)) + sb.REFUSAL_NO_REG
        self.assertLessEqual(len(worst), sb.ERROR_CENTER_TEXT_CAP, "fixed text behind a budgeted head: the format's worst case fits")

    def test_refuses_a_nul_value(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.assertFalse(self.be.set_env(sid, {"FEATURE_FLAG": "1\x00x"}),
                         "a NUL value is unfulfillable — refuse, never persist it into the reg")
        self.assertEqual(self._reg(sid)["env"], ENV, "the poisoned payload must not half-apply")

    def test_refuses_the_identity_names(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.assertFalse(self.be.set_env(sid, {"ROMP_SESSION_NAME": "impostor"}),
                         "the identity env is romp's own — never a per-session override")
        self.assertEqual(self._reg(sid)["env"], ENV, "the refused payload must not half-apply")

    def test_an_explicit_empty_dict_clears_and_reconnects(self):
        # the replace-not-merge contract's limiting case: {} DECLARES "no per-session env" —
        # the only way to remove a spawn-time debugging var from a running session
        sid = self.be.spawn("web", "/tmp", env=ENV)
        s = self._live(sid)
        self.assertTrue(self.be.set_env(sid, {}))
        self.assertEqual(self._reg(sid)["env"], {}, "the empty declaration replaces the whole set")
        self.assertEqual(s.env_vars, {})
        self.assertTrue(self.reconnects, "clearing is a CHANGE — it applies by reconnecting")
        self.assertEqual(sb.flag_settings_path(self.be.state_dir, sid, env=s.env_vars), "",
                         "cleared env adds no key — the next connect launches without a flag file")
        self.reconnects.clear()
        self.assertTrue(self.be.set_env(sid, {}), "re-clearing is the unchanged re-assert")
        self.assertFalse(self.reconnects, "already clear = nothing to apply, no CLI churn")

    def test_a_dormant_session_persists_without_a_live_object(self):
        sid = self.be.spawn("web", "/tmp")
        self.assertTrue(self.be.set_env(sid, ENV))
        self.assertEqual(self._reg(sid)["env"], ENV,
                         "the next connect reads the reg — persistence alone is a full apply "
                         "for a session with no live client")


class ForkInheritsEnv(_Backend):
    def test_a_fork_carries_the_parents_env(self):
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()   # transcript_path resolves through this
        try:
            self.be.spawn("parent", self.d, sid=PARENT, env=ENV)
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertEqual(self._reg(CHILD).get("env"), ENV,
                             "it is that conversation, continued elsewhere — env inherits like "
                             "model/auth do")
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def test_a_fork_of_an_env_less_parent_stays_env_less(self):
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()
        try:
            self.be.spawn("parent", self.d, sid=PARENT)
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertNotIn("env", self._reg(CHILD))
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)


class LegacyReservedEnv(_OptionsBackend):
    """Regs written before ENV_RESERVED_NAMES existed can carry ROMP_SID / ROMP_SESSION_NAME in
    their stored env. Spawn and set_env refuse them at the door now — but a standing reg is
    replayed verbatim at every connect, and fork() copies the parent's. Three obligations at the
    apply seam: the session still LAUNCHES (a reconnect refusal would brick a long-running session
    over a var accepted under older rules), the reserved name never reaches the applied env (it
    would shadow-race the options.env identity — `romp end self` resolving to a forged sid), and
    the skip is LOUD, naming the session and the ignored var (never silently)."""

    def _poisoned(self, env):
        """A reg whose stored env predates the reserved-name rule — written behind the validator,
        the way those regs actually exist on disk."""
        sid = self.be.spawn("web", "/tmp")
        reg = self._reg(sid)
        reg["env"] = dict(env)
        sb.write_reg(self.be.state_dir, sid, reg)
        return sid

    def test_a_pre_rule_reg_launches_with_the_reserved_name_skipped(self):
        sid = self._poisoned({"FEATURE_FLAG": "1", "ROMP_SID": PARENT})
        logged = []
        self.be._log = lambda msg, problem=False, **kw: logged.append((msg, problem))
        kw = self._options_kw(self._sess(sid))
        applied = json.loads(Path(kw["settings"]).read_text())["env"]
        self.assertEqual(applied, {"FEATURE_FLAG": "1"},
                         "the rest of the stored env still applies — skip the var, not the session")
        self.assertEqual(kw["env"]["ROMP_SID"], sid,
                         "the identity overlay stands untouched — the forged sid never shadows it")
        self.assertTrue(any(problem and "ROMP_SID" in msg and "web" in msg
                            for msg, problem in logged),
                        "the skip must be loud, naming the session and the ignored var: %r"
                        % (logged,))

    def test_a_reg_carrying_only_reserved_names_still_launches(self):
        sid = self._poisoned({"ROMP_SESSION_NAME": "impostor"})
        logged = []
        self.be._log = lambda msg, problem=False, **kw: logged.append((msg, problem))
        kw = self._options_kw(self._sess(sid))
        self.assertNotIn("settings", kw,
                         "nothing left after the skip = the no-keys contract, not an empty env")
        self.assertEqual(kw["env"]["ROMP_SESSION_NAME"], "web")
        self.assertTrue(any(problem and "ROMP_SESSION_NAME" in msg for msg, problem in logged))

    def test_a_fork_drops_the_reserved_names_from_the_inherited_env(self):
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()   # transcript_path resolves through this
        try:
            self.be.spawn("parent", self.d, sid=PARENT)
            reg = self._reg(PARENT)
            reg["env"] = {"FEATURE_FLAG": "1", "ROMP_SID": PARENT}
            sb.write_reg(self.be.state_dir, PARENT, reg)
            logged = []
            self.be._log = lambda msg, problem=False, **kw: logged.append((msg, problem))
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertEqual(self._reg(CHILD).get("env"), {"FEATURE_FLAG": "1"},
                             "the copy is where a legacy reg's poison stops propagating")
            self.assertTrue(any(problem and "ROMP_SID" in msg and "child" in msg
                                for msg, problem in logged),
                            "the drop must be loud, naming the session and the var: %r" % (logged,))
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)


class ValidatorLockstep(unittest.TestCase):
    """_env_error (the /new door's kernel-side mirror) and env_request_error are hand-kept copies.
    Spawn backs the door with a loud ValueError, but set_env refuses with a silent False its callers
    discard — so drift between the copies on the existing:true path would be a 200 with an env echo
    and NOTHING applied. This pin is the backstop the door docstring cites: identical verdicts
    (messages included) across the whole good/bad payload table, so loosening one copy fails here
    instead of going silent."""

    PAYLOADS = (
        # valid: plain, underscore/empty-value, the vacuous empty declaration
        {"FEATURE_FLAG": "1"}, {"_UNDER": "x", "A9": ""}, {},
        # non-dicts, truthy and falsy alike (the door 400s all of them)
        "FEATURE_FLAG=1", ["FEATURE_FLAG"], 7, None, False, 0, "", [],
        # bad names
        {"9BAD": "1"}, {"": "1"}, {"BAD-NAME": "1"}, {"BAD NAME": "1"}, {"über": "1"},
        # the reserved identity names (options.env owns them), alone and riding a valid payload
        {"ROMP_SID": "x"}, {"ROMP_SESSION_NAME": "web"}, {"FEATURE_FLAG": "1", "ROMP_SID": "x"},
        # bad values, the NUL hole included
        {"FEATURE_FLAG": 1}, {"FEATURE_FLAG": None}, {"FEATURE_FLAG": True},
        {"FEATURE_FLAG": {"nested": "no"}}, {"FEATURE_FLAG": "1\x00x"},
        # credential-shaped names of other spellings (2026-09-18): refused by the rule credentials.py holds for
        # both copies; an empty or whitespace value holds no secret and passes; the control token is refused like
        # any other since review round 1 (its exclusion is the boot notice's alone); a bad value under such a
        # name is the value's refusal, whichever copy answers
        {"NOTES_API_TOKEN": _secret_value("notes-token")}, {"NOTES_API_KEY": _secret_value("notes-key")},
        {"OP_SESSION_notes": _secret_value("op-session")}, {"OP_CONNECT_TOKEN": _secret_value("op-connect")},
        {"NOTES_ENDPOINT": "http://notes.test", "NOTES_API_TOKEN": _secret_value("notes-token"),
         "NOTES_API_KEY": _secret_value("notes-key")},
        {"EMPTY_TOKEN": ""}, {"SPACES_TOKEN": "  "}, {"ROMP_SERVE_TOKEN": "control"},
        {"NOTES_API_TOKEN": 1}, {"NOTES_API_TOKEN": "a\x00b"},
        # the suffixes fold case (the spawn-spec fix's review round 1, 2026-09-18, carried into the door's
        # predicate): a lowercase or mixed-case spelling is the same shape; the control-token exclusion is
        # the exact name romp reads, so another spelling of it is refused like any other; a name whose suffix
        # only begins with the shape passes in any case
        {"notes_api_token": _secret_value("notes-token")}, {"Notes_Api_Key": _secret_value("notes-key")},
        {"romp_serve_token": _secret_value("control-lower")}, {"editor_tokenizer": "x"}, {"empty_token": ""},
        # the 1Password half folds too (review round 1 of the env-pick door, 2026-09-18): both copies, one verdict
        {"op_session_notes": _secret_value("op-session-lower")}, {"Op_Account": "acct"}, {"options_for_x": "x"},
    )

    @staticmethod
    def _kernel():
        import sys
        if "romp_kernel" in sys.modules:
            return sys.modules["romp_kernel"]
        # the kernel imports its deps by these exact module names (the test_new_route_prefs pattern)
        for name, fn in (("romp_event_model", "romp-event-model"), ("romp_judge", "romp-judge")):
            if name not in sys.modules:
                load_source(name, os.path.join(BIN, fn))
        return load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

    def test_the_two_validator_copies_agree_verdict_for_verdict(self):
        km = self._kernel()
        for payload in self.PAYLOADS:
            self.assertEqual(km._env_error(payload), sb.env_request_error(payload),
                             "the copies must stay in lockstep — payload %r" % (payload,))

    CREDENTIALS = ({"ANTHROPIC_API_KEY": "x"}, {"ANTHROPIC_AUTH_TOKEN": "x"}, {"CLAUDE_CODE_OAUTH_TOKEN": "x"})

    def test_the_copies_agree_that_a_credential_name_is_always_reserved(self):
        """romp holds no API key (2026-09-08): a session's credential is Claude Code's own resolution, so a
        per-session env payload naming any credential variable is refused for EVERY pick, in both copies,
        with the same words. Before this the key competed only while romp ran a provider, and a login
        session's own token override passed."""
        km = self._kernel()
        for auth in ("", "key", "login"):
            for p in self.CREDENTIALS:
                a, b = km._env_error(p, auth), sb.env_request_error(p, auth)
                self.assertEqual(a, b, "the copies must stay in lockstep (auth=%r, payload %r)" % (auth, p))
                self.assertIn("is reserved: a session's credential is Claude Code's own", a)
                self.assertIn(next(iter(p)), a, "the offender is named")

    def test_the_copies_agree_that_a_credential_shaped_name_is_refused(self):
        """The spawn.json fix's build found the doors refusing the three login names alone (2026-09-18): a pick
        naming NOTES_API_TOKEN or an OP_* variable landed in the registry and the flag-settings file. Both
        copies now refuse such a pick, for every billing pick, with credentials.py's one wording, naming the
        variable and never its value."""
        km = self._kernel()
        val = _secret_value("notes-token")
        for auth in ("", "key", "login"):
            for p in ({"NOTES_API_TOKEN": val}, {"OP_SESSION_notes": val}, {**PLAIN, "NOTES_API_KEY": val},
                      {"notes_api_token": val}, {**PLAIN, "Notes_Api_Key": val}):   # the fold, in both copies
                a, b = km._env_error(p, auth), sb.env_request_error(p, auth)
                self.assertEqual(a, b, "the copies must stay in lockstep (auth=%r, payload %r)" % (auth, sorted(p)))
                self.assertTrue(a, "refused (auth=%r, payload %r)" % (auth, sorted(p)))
                name = next(n for n in p if n not in PLAIN)
                self.assertIn(name, a, "the offender is named")
                self.assertNotIn(val, a, "the value is never in the message")
                self.assertIn("the pick was not saved", a)


class DrivePlumbing(unittest.TestCase):
    """The /new door rides the same park/drain path as the other per-session switches (source pins,
    the test_session_auth.DrivePlumbing pattern)."""

    def test_the_op_is_routed_parked_and_replayed(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        self.assertIn("def _set_env_or_park(be, sid, value):", src)
        self.assertIn('_gate_or_park(sid, ("env", value))', src)   # parks on the gate, or hands over (2026-09-05)
        self.assertIn('elif op[0] == "env":', src)
        self.assertIn('refused = (be.set_env(sid, op[1]) is False) if hasattr(be, "set_env") else True', src,
                      "the drain reads the verdict (review round 1 of the env-pick door, 2026-09-18) and a backend without "
                      "set_env is a refusal, never a raise (round 9, kernel-1 and extra9-1); a source pin on where the arm "
                      "lives: the refusal, the frame and the queue surviving behind the pick are pinned by execution in "
                      "tests/test_kernel_meta_command_gate.py (RefusalReachesTheClient's env pins)")
        self.assertIn("    def set_env(self, sid, value):\n", src.split("class _UnownedBackend(sb.SessionBackend):", 1)[1],
                      "_UnownedBackend answers set_env beside its other setters (round 9): the def's PRESENCE is this source pin's "
                      "(round 9's closing commit, extra10-1: at the round-9 head, with the method removed and the drain's guard kept, "
                      "the guard refused in its place and every behavioural test stayed green, so only this line and the census def "
                      "count went red; since that commit the gate test's direct call reds too, with AttributeError); its "
                      "VERDICT is pinned by execution in tests/test_kernel_meta_command_gate.py, RefusalReachesTheClient's unowned "
                      "drain test, which calls km._UNOWNED.set_env directly and asserts the False it answers")
        self.assertIn('("model", "effort", "fast", "env", "cwd")', src,
                       "a repeat env pick REPLACES the earlier parked one in place, like model/effort (and a move)")

    def test_the_create_path_passes_env_through(self):
        src = open(os.path.join(BIN, "romp-kernel")).read()
        # (parent + tags joined the signature with tab groups, 2026-09-04 — env's slot is unchanged)
        self.assertIn('def _create_sdk_session(nm, cwd, auth="", prefs=None, client=None, env=None, parent="", tags=()):', src)
        self.assertIn("sid = _sdk().spawn(nm, cwd, bg, fg, auth=auth, env=env)", src,
                      "env rides the SPAWN — the reg is born with it, ahead of the prefs pass")


# ── The session-identity environment surface (upstream; the user 2026-08-15 sid, 2026-08-16 name).
# Every SDK session's CLI process — and every Bash it runs — carries its romp identity in env:
# ROMP_SID (the stable uuid; what `romp end self` resolves through) and ROMP_SESSION_NAME (the
# human name at spawn). The name is a GENERIC capability for child processes that need to know
# which session they belong to (attribution, logging), deliberately coupled to no consumer.
# Env is spawn-frozen, so a post-spawn rename is not reflected — the sid is the address, the
# name a label. Source pins over _options' env line (the SDK merges options.env OVER the
# inherited environment, so both ride the same additive overlay as the bin PATH). Distinct layer
# from the per-session user env above: identity rides options.env (the transport), user env the
# per-sid flag-settings file — neither writes the other's layer.
SDK = Path(os.path.join(os.path.dirname(HERE), "kernel", "sdk_backend.py")).read_text()


class SessionIdentityEnv(unittest.TestCase):
    def test_sid_and_name_ride_the_spawn_env(self):
        self.assertIn('"ROMP_SID": str(sess.sid),', SDK,
                      "the stable identity — addressing (romp end self)")
        self.assertIn('"ROMP_SESSION_NAME": str(sess.name)', SDK,
                      "the human name at spawn — attribution/logging for child processes")

    def test_the_name_is_documented_as_spawn_frozen(self):
        # the caveat is the contract: a rename after spawn is NOT reflected in a live session's
        # env, so nothing may treat the name as an address — the comment must keep saying so
        self.assertIn("a rename after spawn is NOT reflected", SDK)

    def test_one_env_overlay_only(self):
        # both vars ride _options' single env= overlay (additive over os.environ via
        # _bin_on_path_env) — a second env assembly would fork the truth
        self.assertEqual(SDK.count('"ROMP_SESSION_NAME":'), 1)
        self.assertEqual(SDK.count('env={**_bin_on_path_env(os.environ)'), 1)


if __name__ == "__main__":
    unittest.main()


class EnvSecretsStayPrivate(unittest.TestCase):
    """Env values can be secrets (PR #889 review): the per-sid flag-settings file is created 0600
    like the serve token, and the parked chat chip renders NAMES only — never a value."""

    def test_the_flag_settings_file_is_private(self):
        import stat
        d = tempfile.mkdtemp()
        p = sb.flag_settings_path(d, "11111111-2222-3333-4444-555555555555", env={"TOKEN": "s3cret"})
        self.assertTrue(p, "an env writes the file")
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600, "0600, the serve-token treatment")
        self.assertIn("s3cret", open(p).read(), "…and the value is in it (the CLI reads it), private")
        p2 = sb.flag_settings_path(d, "11111111-2222-3333-4444-555555555555", env={"TOKEN": "other"})
        self.assertEqual(stat.S_IMODE(os.stat(p2).st_mode), 0o600, "a rewrite keeps it private")

    def test_the_published_path_ends_0600_over_a_pre_existing_looser_inode_with_the_mode_on_the_temps_descriptor_before_the_write(self):
        # Until 2026-09-18 the writer opened the published path O_CREAT|O_TRUNC at 0600 and chmod'd it AFTER the
        # write: a fresh file was born 0600, but a file created before the 0600 open (2026-09-03) kept its looser
        # mode through the truncating open, took the env block at that mode, and tightened only afterwards. Since the
        # merge of fork PR #789 with the env-pick door's temp-and-rename write the published path is never opened: the
        # writer creates a fresh O_EXCL 0600 temp, puts the mode onto the TEMP's descriptor before the first byte
        # (fork PR #789, review round 1: the same write-then-tighten window the reg and the parked-ops mirror lost; the
        # fchmod is what makes the mode exact under a umask that would strip bits from the create), writes the env
        # block, and os.replace carries the temp onto the path over the pre-existing looser inode, which is unlinked,
        # not tightened. os.chmod is interposed and recorded, so a chmod on the path would show; os.fchmod is
        # recorded with the descriptor's size at that moment, so "before the write" is executed (size 0), not read
        # off the source. Reworded in round 7 of the env-pick door's review (2026-09-20, extra5-2): the merge had
        # carried the prose of the in-place write the resolution discarded; the assertions are unchanged.
        import stat
        d = tempfile.mkdtemp()
        p = Path(d, sb.FLAG_SETTINGS_DIR, "%s.json" % PARENT)
        p.parent.mkdir(parents=True)
        p.write_text('{"ultracode": true}\n')
        os.chmod(p, 0o644)                                        # a file from before the 0600 open
        fchmods, chmods = [], []
        real_fchmod = os.fchmod

        def fchmod_probe(fd, mode):
            fchmods.append((mode, os.fstat(fd).st_size))
            return real_fchmod(fd, mode)

        def chmod_probe(path, mode, *a, **k):
            chmods.append((str(path), mode))
        with mock.patch.object(os, "fchmod", fchmod_probe), mock.patch.object(os, "chmod", chmod_probe):
            out = sb.flag_settings_path(d, PARENT, env={"FEATURE_FLAG": "1"})
        self.assertEqual(out, str(p))
        self.assertEqual(stat.S_IMODE(os.stat(p).st_mode), 0o600, "0600 on the published path: the temp's mode, carried over the looser inode by os.replace")
        self.assertEqual(fchmods, [(0o600, 0)], "one fchmod, on the temp's descriptor while it is still empty (size 0: before the write)")
        self.assertEqual(chmods, [], "no chmod on the path after the write")
        self.assertEqual(json.loads(p.read_text()), {"env": {"FEATURE_FLAG": "1"}}, "and the env block landed")

    def test_a_raising_fchmod_closes_the_descriptor_and_the_launch_goes_without_the_keys(self):
        # Review round 2 of PR 789 (2026-09-19): round 1 put the fchmod between os.open and os.fdopen with nothing closing
        # the descriptor when it raised. This writer catches the OSError, logs it and returns "" (the session launches
        # without the keys, said loudly), and it runs on every launch and reconnect, so the leak repeated for as long
        # as the failure lasted. The descriptor os.open returned reaches os.close (a real close, recorded), and the
        # log line stands.
        import errno
        d = tempfile.mkdtemp()
        opened, closed, logged = [], [], []
        real_open, real_close = os.open, os.close

        def open_probe(*a, **k):
            fd = real_open(*a, **k)
            opened.append(fd)
            return fd

        def fchmod_refused(fd, mode):
            raise PermissionError(errno.EPERM, "fchmod refused (interposed)")

        def close_probe(fd):
            closed.append(fd)
            return real_close(fd)
        with mock.patch.object(os, "open", open_probe), mock.patch.object(os, "fchmod", fchmod_refused), \
                mock.patch.object(os, "close", close_probe):
            out = sb.flag_settings_path(d, PARENT, env={"FEATURE_FLAG": "1"}, log=lambda m, **k: logged.append(m))
        self.assertEqual(out, "", "no settings file: the launch goes without the keys")
        self.assertEqual(len(opened), 1, "one descriptor, the temp's (the published path is never opened)")
        self.assertEqual(closed, opened, "closed on the failure road")
        self.assertEqual(len(logged), 1, logged)
        self.assertIn("unwritable", logged[0])

    def test_the_parked_chip_names_the_vars_but_never_their_values(self):
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
        md = km._parked_md(("env", {"B_TOKEN": "s3cret", "A_FLAG": "1"}))
        self.assertEqual(md, "/env A_FLAG B_TOKEN", "sorted names, no values")
        self.assertNotIn("s3cret", md)
        self.assertEqual(km._parked_md(("env", {})), "/env (cleared)")




class RefusedLaunchRowsRingBounded(unittest.TestCase):
    """Ruling 1 (a) of the post-merge census (2026-09-20), by execution: main's two refused-launch rows in
    _host_transport_for (fork PR #777) ring a text bounded by HOST_REFUSED_RING while the ledger row and the kernel log
    line keep the reason whole. The drivers are the host tests' (a fake _spawn_host that writes a host-crashed row and
    returns an exited process for the EXITED road; one whose process never exits and never serves its socket, with
    SOCKET_WAIT_S patched short, for the DEADLINE road, added in round 7 of the review, 2026-09-20, tests-1: until then
    only the exited row's ring text was driven, and the census identity is blind to which tainted value fills which
    placeholder, so a swapped argument at the deadline row rendered green), each with a 300-character host reason: until
    the post-merge commit problem_row's log= rang the whole prose, and the census read the row as an UNBOUNDED content row.
    Red before: the ring text held the whole reason and no marker."""

    SID = "11111111-2222-3333-4444-555555555555"

    def test_a_refused_launch_rings_the_bounded_text_and_the_ledger_and_the_log_keep_the_reason_whole(self):
        import asyncio
        d = tempfile.mkdtemp()
        logs = []
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda m, *a, **k: logs.append(m))
        Path(d, "session-hosts").write_text("on")
        sb.write_reg(Path(d), self.SID, {"sid": self.SID, "name": "web", "alive": True, "lastSid": self.SID})
        s = types.SimpleNamespace(sid=self.SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                  _options_login="", _seed_for_dead_cli=lambda cli: None)
        reason = "OSError: " + "B" * 291

        def fake_spawn(sess, spec_path, secret_env=None):
            with open(Path(spec_path).parent / "host.log", "a") as f:
                f.write(json.dumps({"t": 1, "kind": "host-started"}) + "\n" + json.dumps({"t": 2, "kind": "host-crashed", "error": reason}) + "\n")
            return types.SimpleNamespace(poll=lambda: 1, returncode=1, pid=4242, terminate=lambda: None)
        with mock.patch.object(be, "_spawn_host", fake_spawn):
            with self.assertRaises(sb.CLIConnectionErrorLike):
                asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        rows = [json.loads(l) for l in (Path(d) / sb.SESSION_EVENTS_FILE).read_text().splitlines()]
        self.assertEqual([r["kind"] for r in rows], ["host.exited-before-socket"])
        self.assertIn(reason, rows[0]["text"], "the ledger row keeps the reason whole (the card reads it)")
        line = [l for l in logs if sb.PROBLEM_ROW_MARK in l and "exited before serving its socket" in l]
        self.assertEqual(len(line), 1, logs)
        self.assertIn(reason, line[0], "the kernel log line keeps the reason whole, with its ;; problem-row tail")
        self.assertEqual(sb.parse_problem_row(line[0])["kind"], "host.exited-before-socket")
        ring = [p["text"] for p in be.problems() if p["text"].startswith("the session host for ")]
        self.assertEqual(len(ring), 1, be.problems())
        text = ring[0]
        self.assertLessEqual(len(text), sb.ERROR_CENTER_TEXT_CAP)
        self.assertEqual(text, sb.host_refused_ring_text("web", "exited before serving its socket (code 1); see hosts/%s/host.log: %s" % (self.SID, reason)))
        self.assertTrue(text.endswith(sb._cred.CUT_MARK), "the cut is visible: the marker is the last character")
        self.assertNotIn(reason, text, "the whole reason is not on the ring")
        self.assertTrue(text.startswith("the session host for web exited before serving its socket (code 1); see hosts/%s/host.log: OSError: B" % self.SID))
        self.assertEqual(len(rows[0]["text"]), len("the session host for web exited before serving its socket (code 1); see hosts/%s/host.log: " % self.SID) + len(reason))

    def test_a_host_that_never_serves_its_socket_rings_the_bounded_text_and_the_ledger_and_the_log_keep_the_reason_whole(self):
        """The deadline road (round 7, tests-1), driven the way the exited road is: a fake _spawn_host whose process never
        exits and never serves its socket, host.log carrying a host-crashed row with a 300-character reason (a wedged host
        that wrote a failing row and did not exit, the read host_exit_reason answers for), SOCKET_WAIT_S patched to 0.3 s.
        The row's kind is host.never-served-socket, the wedged host is ended, the ring text EQUALS
        host_refused_ring_text(sess.name, said) with the marker last (an equality, not a prefix: a prefix assertion is what
        an argument swap slips past on a short name), and the ledger row and the kernel log line keep the reason whole.
        Red under the swap host_refused_ring_text(said, sess.name) at the deadline site, which every other test leaves green."""
        import asyncio
        d = tempfile.mkdtemp()
        logs = []
        be = sb.SdkBackend(d, "/bin/true", lambda *a, **k: None, log=lambda m, *a, **k: logs.append(m))
        Path(d, "session-hosts").write_text("on")
        sb.write_reg(Path(d), self.SID, {"sid": self.SID, "name": "web", "alive": True, "lastSid": self.SID})
        s = types.SimpleNamespace(sid=self.SID, name="web", _host_intent=True, _host=None, _host_is_attach=False,
                                  _options_login="", _seed_for_dead_cli=lambda cli: None)
        reason = "OSError: " + "B" * 291
        ended = []

        def fake_spawn(sess, spec_path, secret_env=None):
            with open(Path(spec_path).parent / "host.log", "a") as f:
                f.write(json.dumps({"t": 1, "kind": "host-started"}) + "\n" + json.dumps({"t": 2, "kind": "host-crashed", "error": reason}) + "\n")
            return types.SimpleNamespace(poll=lambda: None, returncode=None, pid=4343, terminate=lambda: ended.append(1))
        with mock.patch.object(be, "_spawn_host", fake_spawn), mock.patch.object(sb._ht(), "SOCKET_WAIT_S", 0.3):
            with self.assertRaises(sb.CLIConnectionErrorLike) as cm:
                asyncio.run(be._host_transport_for(s, types.SimpleNamespace(), (None, None, None)))
        self.assertEqual(ended, [1], "the wedged host was ended")
        said = "did not serve its socket within 0 s; it was ended; see hosts/%s/host.log: %s" % (self.SID, reason)
        self.assertEqual(str(cm.exception), "the session host " + said)
        rows = [json.loads(l) for l in (Path(d) / sb.SESSION_EVENTS_FILE).read_text().splitlines()]
        self.assertEqual([r["kind"] for r in rows], ["host.never-served-socket"])
        self.assertEqual(rows[0]["text"], "the session host for web " + said, "the ledger row keeps the reason whole (the card reads it)")
        line = [l for l in logs if sb.PROBLEM_ROW_MARK in l and "did not serve its socket" in l]
        self.assertEqual(len(line), 1, logs)
        self.assertIn(reason, line[0], "the kernel log line keeps the reason whole, with its ;; problem-row tail")
        self.assertEqual(sb.parse_problem_row(line[0])["kind"], "host.never-served-socket")
        ring = [p["text"] for p in be.problems() if p["text"].startswith("the session host for ")]
        self.assertEqual(len(ring), 1, be.problems())
        text = ring[0]
        self.assertEqual(text, sb.host_refused_ring_text("web", said), "the ring text is the helper's over (name, said), in that order")
        self.assertLessEqual(len(text), sb.ERROR_CENTER_TEXT_CAP)
        self.assertLessEqual(len(text.encode("utf-16-le")) // 2, sb.ERROR_CENTER_TEXT_CAP, "in the error centre's unit too")
        self.assertTrue(text.endswith(sb._cred.CUT_MARK), "the cut is visible: the marker is the last character")
        self.assertNotIn(reason, text, "the whole reason is not on the ring")
        self.assertTrue(text.startswith("the session host for web did not serve its socket within 0 s; it was ended; see hosts/%s/host.log: OSError: B" % self.SID))


class CredentialShapedNamesAtTheDoor(unittest.TestCase):
    """The door refuses a pick naming a credential-shaped variable of ANY spelling (2026-09-18, found by the
    spawn.json fix's build; the box admin ruled the door the fix): until then env_request_error refused the
    three login names alone, so NOTES_API_TOKEN=... typed into the pick was written into the registry and
    the per-sid flag-settings file, against the fork's rule that no credential is ever written to a file.
    The rule is the spawn.json writer's (spawn_env_secret_names) over the pick itself, one rule, never a
    second list; the message names the variable(s), never a value, says where the value belongs, and that
    nothing was saved. Values are built at run time (never a token-shaped literal: gitleaks reads tests)."""

    def test_a_credential_shaped_name_is_refused_by_name_and_the_pick_without_it_passes(self):
        for name in ("NOTES_API_TOKEN", "NOTES_API_KEY", "OP_SESSION_notes", "OP_SERVICE_ACCOUNT_TOKEN"):
            val = _secret_value("value")
            for auth in ("", "key", "login"):
                err = sb.env_request_error({**PLAIN, name: val}, auth)
                self.assertTrue(err, "%s must be refused for auth=%r" % (name, auth))
                self.assertIn(name, err, "the offending NAME is in the message")
                self.assertNotIn(val, err, "the VALUE is never in the message")
                self.assertNotIn("NOTES_ENDPOINT", err, "the plain name is not blamed")
                self.assertIn("the pick was not saved", err)
                self.assertIn("process environment", err, "the message says where such a value belongs")
                self.assertTrue(err.startswith("env: "), "the env doors' prefix, like every other refusal")
                self.assertEqual(err, "env: " + sb._cred.credential_env_refusal([name]),
                                 "the door's head once, in front of the shared sentence (review round 1, 2026-09-18)")
        self.assertEqual(sb.env_request_error(dict(PLAIN)), "", "the same pick without the name passes")

    def test_the_shared_sentence_carries_no_head_of_its_own(self):
        """Review round 1 (2026-09-18): the sentence began "env: " and set_env's log line put its own head in front,
        so the row read "pick refused: env: ...". Each door adds the head once; the sentence leads with the names."""
        sentence = sb._cred.credential_env_refusal(["NOTES_API_TOKEN"])
        self.assertTrue(sentence.startswith("NOTES_API_TOKEN is credential-shaped"), sentence)
        self.assertNotIn("env: ", sentence)
        short = sb._cred.credential_env_ring_text(["NOTES_API_TOKEN"])
        self.assertTrue(short.startswith("NOTES_API_TOKEN is credential-shaped: the pick was not saved"), short)
        self.assertIn("process environment", short)
        self.assertNotIn("env: ", short)

    def test_the_control_token_is_refused_like_any_credential_shaped_name(self):
        """Review round 1 (2026-09-18): the door reused a rule that left ROMP_SERVE_TOKEN unnamed for the boot line's
        sake, so romp's own control token was the one credential-shaped name a pick could still write to the
        registry and the flag-settings file, while the reference's lister reported it as an offender. The
        exclusion is the boot notice's alone now; the rule, the writer and the doors name it."""
        pick = {"ROMP_SERVE_TOKEN": "control"}
        err = sb.env_request_error(pick)
        self.assertIn("ROMP_SERVE_TOKEN is credential-shaped", err)
        self.assertEqual(sb._cred.credential_env_names(pick), ["ROMP_SERVE_TOKEN"], "the rule names it")
        self.assertEqual(sb.spawn_env_secret_names(pick), ["ROMP_SERVE_TOKEN"], "the writer moves it")
        self.assertEqual(sb.env_credential_names(pick), [], "the boot line alone leaves it unnamed")
        self.assertEqual(sb.env_credential_names({"romp_serve_token": "c"}), ["romp_serve_token"],
                         "and that exclusion stays the exact name romp reads")

    def test_every_offending_name_is_said_sorted_and_no_value(self):
        tok, key = _secret_value("tok"), _secret_value("key")
        err = sb.env_request_error({"NOTES_API_TOKEN": tok, **PLAIN, "NOTES_API_KEY": key})
        self.assertIn("NOTES_API_KEY, NOTES_API_TOKEN are credential-shaped", err, "all of them, sorted")
        self.assertNotIn(tok, err)
        self.assertNotIn(key, err)

    def test_the_door_judges_by_the_writers_rule(self):
        """One rule with the spawn.json writer: a well-formed pick is refused exactly when spawn_env_secret_names
        flags a name in it, and the names the message says are the writer's."""
        val = _secret_value("value")
        picks = ({**PLAIN, "NOTES_API_TOKEN": val}, {"EMPTY_TOKEN": ""}, {"SPACES_TOKEN": "  "},
                 {"ROMP_SERVE_TOKEN": "control"}, dict(PLAIN), {"OP_ACCOUNT": "acct"}, {"MY_SECRET_TOKEN": val},
                 {"TOKEN_FIRST": val}, {"API_KEY_HOLDER": val}, {"op_session_notes": val}, {"Op_Connect_Host": "h"})
        for pick in picks:
            flagged = sb.spawn_env_secret_names(pick)
            err = sb.env_request_error(pick)
            self.assertEqual(bool(err), bool(flagged), "door and writer disagree on %r" % (sorted(pick),))
            for n in flagged:
                self.assertIn(n, err)
            self.assertNotIn(val, err)

    def test_an_empty_credential_shaped_value_passes_as_the_writer_keeps_it(self):
        # the writer leaves an empty value in its file (it holds no secret; there it is the unset it means), so
        # the door lets it through too: one rule
        self.assertEqual(sb.env_request_error({"EMPTY_TOKEN": ""}), "")
        self.assertEqual(sb.env_request_error({**PLAIN, "EMPTY_API_KEY": ""}), "")

    def test_a_lowercase_or_mixed_case_credential_shaped_name_is_refused_with_the_same_words(self):
        """The spawn-spec fix's review round 1 (2026-09-18) made the writer's suffix test fold case, since a
        notes_api_token was otherwise written to spawn.json with its value; the door's predicate compared the
        suffixes exactly, so the same name typed into the pick passed the door and landed in the registry and
        the flag-settings file. One shape rule, never two: the door refuses the lowercase and mixed-case
        spellings, under their own spelling, with the refusal an upper-case name gets, the value in no message;
        an empty value and a name whose suffix only begins with the shape pass in any case."""
        for name, upper in (("notes_api_token", "NOTES_API_TOKEN"), ("Notes_Api_Key", "NOTES_API_KEY"),
                            ("hf_token", "HF_TOKEN"),
                            # the 1Password half folds too (review round 1 of the env-pick door, 2026-09-18: the fold
                            # had reached the suffixes alone, so a lowercase session token passed every door)
                            ("op_session_notes", "OP_SESSION_NOTES"), ("Op_Account", "OP_ACCOUNT")):
            val = _secret_value("value")
            for auth in ("", "key", "login"):
                err = sb.env_request_error({**PLAIN, name: val}, auth)
                self.assertTrue(err, "%s must be refused for auth=%r" % (name, auth))
                self.assertEqual(err, "env: " + sb._cred.credential_env_refusal([name]), "the one wording, naming this spelling")
                self.assertEqual(err.replace(name, upper), sb.env_request_error({**PLAIN, upper: val}, auth),
                                 "the same refusal text as the upper-case spelling gets")
                self.assertNotIn(val, err, "the VALUE is never in the message")
                self.assertNotIn("NOTES_ENDPOINT", err, "the plain name is not blamed")
        self.assertEqual(sb.env_request_error({**PLAIN, "empty_token": "", "editor_tokenizer": "x"}), "",
                         "an empty value holds no secret and a prefix-only suffix is not the shape, in any case")

    def test_the_three_login_names_keep_their_own_words(self):
        # the loop's refusal of the three stands first, whatever the value, with the wording other tests pin
        for name in sb.AUTH_ENV_NAMES:
            err = sb.env_request_error({name: ""})
            self.assertIn("Claude Code's own", err)
            self.assertNotIn("credential-shaped", err)

    def test_the_advice_is_scoped_to_the_half_of_the_rule_the_name_matched(self):
        """fresh-2 (review round 2 of the env-pick door, 2026-09-19): the first wording sent every refused value to
        the process environment romp's service starts with, and for a 1Password name that is the road the boot check
        refuses (romp-manager exits 1 on it), so an operator following the printed advice for an OP_* name took the
        deployment down. The suffix half keeps that road; the 1Password half hears the boot check's own (a file of
        the helper's own, or the session's shells); a mixed pick hears both, each scoped. The boot check is executed
        here so the two sentences cannot drift apart from what it refuses."""
        suffix = sb._cred.credential_env_refusal(["NOTES_API_TOKEN"])
        op = sb._cred.credential_env_refusal(["OP_ACCOUNT"])
        mixed = sb._cred.credential_env_refusal(["NOTES_API_TOKEN", "op_session_notes"])
        self.assertIn("Put such a value in the process environment romp's service starts with", suffix)
        self.assertNotIn("Put such a value in the process environment", op,
                         "the road the boot check refuses is never advised for a 1Password name")
        self.assertIn("refuses a 1Password name in its process environment at boot", op)
        self.assertIn("its own file", op)
        self.assertIn("_API_KEY or _TOKEN value goes in romp's process environment", mixed)
        self.assertIn("1Password name is refused there at boot", mixed)
        # the closing review's fold clause (2026-09-19) landed with no test to fail without it (tests-5, review round
        # 4): the mixed road states the fold like every other statement of the rule, and AFTER both halves, so it
        # scopes both (the exact phrase: credential_env_refusal's own prefix already carries "any letter case")
        self.assertIn("in any letter case", mixed)
        after_suffix = mixed.index("goes in romp's process environment")
        self.assertGreater(mixed.index("in any letter case", after_suffix), mixed.index("1Password name is refused there at boot"),
                           "the fold clause follows both halves: %r" % mixed)
        self.assertEqual(sb._cred.credential_env_refusal(["op_account"]).replace("op_account", "OP_ACCOUNT"), op,
                         "the fold: a lowercase 1Password name hears the 1Password road")
        short_op = sb._cred.credential_env_ring_text(["OP_ACCOUNT"])
        self.assertIn("refused in the process environment at boot", short_op)
        self.assertNotIn("belongs in the process environment", short_op)
        # the ring text hears the road of the half matched too; its bound is the format's (CredentialShapedNamesEndToEnd
        # computes the worst case), and the full sentence is capped on no surface it reaches (the /new reply, romp
        # new's stderr, the kernel log), so every name rides it whole (review round 3, 2026-09-19: the pins here had
        # measured both against the caps with the three-character session name "web")
        for names, road in ((["NOTES_API_TOKEN"], "suffix"), (["OP_ACCOUNT"], "op"), (["OP_SERVICE_ACCOUNT_TOKEN"], "op"),
                            (["NOTES_API_TOKEN", "op_session_notes"], "mixed"), (["NOTES_API_TOKEN", "OP_SERVICE_ACCOUNT_TOKEN"], "mixed")):
            ring = sb._cred.credential_env_ring_text(names)
            self.assertTrue(ring.endswith(sb._cred.CREDENTIAL_RING_ROADS[road]), (names, ring))
            for n in names:
                self.assertIn(n, sb._cred.credential_env_refusal(names), "every name whole in the sentence")
        absent = os.path.join(tempfile.mkdtemp(), "absent.env")
        with self.assertRaises(RuntimeError, msg="the boot check refuses the road the first wording advised"):
            sb._cred.check_boot_environment(path=absent, environ={"OP_ACCOUNT": "acct"})
        sb._cred.check_boot_environment(path=absent, environ={"NOTES_API_TOKEN": "x"})   # a suffix name boots
        # The boot refusal each road names is for the spelling 1Password uses; this door folds case and the boot check does
        # not (is_op_env_name is exact), and every road that names the refusal says so (round 9 of the review,
        # correctness-1: the op road told a user whose pick spelled a 1Password name in lower case that romp refuses it at
        # boot, which for that spelling it does not). Executed: the folded spellings this door refuses BOOT.
        for road, where in ((op, "the op road"), (mixed, "the mixed road")):
            self.assertIn("as 1Password spells it", road, "%s names the spelling the boot check refuses" % where)
            self.assertIn("this door folds case, the boot check does not", road, "%s says where the two checks differ" % where)
        for k in ("op", "mixed"):
            self.assertIn("as op spells", sb._cred.CREDENTIAL_RING_ROADS[k], "the %s ring road names the spelling" % k)
            self.assertIn("door folds case", sb._cred.CREDENTIAL_RING_ROADS[k], "the %s ring road says the two checks differ" % k)
            # The other clauses each road owes are pinned by their own words too (round 9 of fork PR #781's review, the
            # closing commit's check: extra10-2 restored the mixed road's destination and only the roads' LENGTHS held it, so
            # a same-length reword that dropped the destination again stayed green): the boot refusal of the 1Password half
            # and where its value belongs, on both roads that name that half, and where a suffix value belongs, on both
            # roads that name that half
            self.assertIn("refused", sb._cred.CREDENTIAL_RING_ROADS[k], "the %s ring road names the boot refusal" % k)
            self.assertIn("at boot", sb._cred.CREDENTIAL_RING_ROADS[k], "the %s ring road says where the refusal happens" % k)
            self.assertIn("a helper's file", sb._cred.CREDENTIAL_RING_ROADS[k], "the %s ring road names where the 1Password value belongs" % k)
        self.assertIn("process env", sb._cred.CREDENTIAL_RING_ROADS["mixed"], "the mixed ring road names where a suffix value belongs")
        self.assertIn("process environment", sb._cred.CREDENTIAL_RING_ROADS["suffix"], "the suffix ring road names where such a value belongs")
        for folded in ("op_account", "Op_Session_Notes", "op_service_account_token"):
            sb._cred.check_boot_environment(path=absent, environ={folded: "x"})     # returns: not refused at boot
            self.assertTrue(sb.env_request_error({**PLAIN, folded: _secret_value("v")}), "%s is refused at this door" % folded)
            self.assertTrue(sb._cred.is_credential_env_name(folded))
            self.assertFalse(sb._cred.is_op_env_name(folded), "the boot check's classifier reads %s as spelled" % folded)


def _ring_road_budget():
    """The ring roads' budget and lengths, derived from the pieces the refusal row is built from (round 9 of fork PR #781's
    review, extra7-1): the error centre's cap less set_env's head at the session budget and CREDENTIAL_RING_FORMAT at the
    name budget with the widest count text and no road, and each road's length. Returns (budget, {road: length, ...,
    "budget": budget, "headroom": budget less the longest road}). The worst-case pin asserts against it; a report states
    these figures by running this function, never by typing them."""
    head = sb.REFUSAL_RING_HEAD % ("x" * sb.RING_SESSION_BUDGET)
    names_worst = "%s and %s more" % ("x" * sb.RING_NAME_BUDGET, sb._cred.count_text(sb._cred.COUNT_CAP + 1))
    fixed = len(head) + len(sb._cred.CREDENTIAL_RING_FORMAT % (names_worst, "are", ""))
    budget = sb.ERROR_CENTER_TEXT_CAP - fixed
    lengths = {k: len(v) for k, v in sb._cred.CREDENTIAL_RING_ROADS.items()}
    lengths["budget"] = budget
    lengths["headroom"] = budget - max(lengths[k] for k in sb._cred.CREDENTIAL_RING_ROADS)
    return budget, lengths


class CredentialShapedNamesEndToEnd(_OptionsBackend):
    """The backend end to end (2026-09-18): a refused pick writes nothing, the stored env stands and the value
    is in no file under the state root; a plain name still lands in the flag-settings file; a stored env from
    before the rule still launches, with its name said in the problem ring and never its value."""

    def setUp(self):
        super().setUp()
        Path(self.d, "session-hosts").write_text("off\n")   # this root mints no host (the runner floors only its own)
        self.logged = []
        self.be._log = lambda msg, problem=False, **kw: self.logged.append((msg, problem, kw))

    def _files_carrying(self, text):
        hits = []
        for root, _dirs, files in os.walk(self.d):
            for f in files:
                p = os.path.join(root, f)
                try:
                    if text in Path(p).read_text(errors="replace"):
                        hits.append(p)
                except OSError:
                    pass
        return hits

    def _live(self, sid):
        s = self._sess(sid)
        self.reconnects = []
        s.request_reconnect = lambda *a, **k: self.reconnects.append(1)
        self.be.sessions[sid] = s
        return s

    def _flag_file(self, sid):
        return Path(self.be.state_dir, sb.FLAG_SETTINGS_DIR, "%s.json" % sid)

    def test_a_refused_pick_writes_nothing_and_the_previous_env_stands(self):
        sid = self.be.spawn("web", "/tmp", env=ENV)
        s = self._live(sid)
        self.be._options(s, dict)                              # the session launched with ENV: the file carries it
        self.assertEqual(json.loads(self._flag_file(sid).read_text())["env"], ENV)
        val = _secret_value("notes-token")
        self.assertFalse(self.be.set_env(sid, {**PLAIN, "NOTES_API_TOKEN": val}), "the pick is refused")
        self.assertEqual(self._reg(sid)["env"], ENV, "the stored pick stays what it was")
        self.assertEqual(s.env_vars, ENV, "the live session's env stays what it was")
        self.assertFalse(self.reconnects, "nothing to apply, no reconnect")
        text = self._flag_file(sid).read_text()
        self.assertEqual(json.loads(text)["env"], ENV, "the flag-settings file is untouched")
        self.assertNotIn("NOTES_API_TOKEN", text)
        self.be._options(s, dict)                              # the next connect rewrites the file from the reg
        self.assertEqual(json.loads(self._flag_file(sid).read_text())["env"], ENV)
        self.assertEqual(self._files_carrying(val), [], "the value is in no file under the state root")
        rows = [m for m, problem, _kw in self.logged if problem and "NOTES_API_TOKEN" in m]
        self.assertTrue(rows, "the refusal is a problem row naming the variable: %r" % (self.logged,))
        self.assertFalse(any(val in m for m, _p, _kw in self.logged), "no log line carries the value")

    def test_spawn_refuses_and_mints_no_file_carrying_the_value(self):
        before = sum(len(f) for _r, _d, f in os.walk(self.d))
        val = _secret_value("notes-key")
        with self.assertRaises(ValueError) as cm:
            self.be.spawn("api", "/tmp", env={**PLAIN, "NOTES_API_KEY": val})
        self.assertIn("NOTES_API_KEY", str(cm.exception))
        self.assertNotIn(val, str(cm.exception))
        self.assertEqual(self._files_carrying(val), [])
        self.assertEqual(sum(len(f) for _r, _d, f in os.walk(self.d)), before, "a refused spawn writes no file")

    def test_a_plain_name_still_lands_in_the_flag_settings_file(self):
        sid = self.be.spawn("web", "/tmp", env=dict(PLAIN))
        kw = self.be._options(self._sess(sid), dict)
        self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], PLAIN,
                         "a name of no credential shape rides the file as before")
        self.assertTrue(self.be.set_env(sid, {**PLAIN, "FEATURE_FLAG": "1"}), "and a plain re-pick is accepted")

    def test_a_stored_credential_shaped_name_still_launches_and_is_said_once_per_session(self):
        """The launch path never ran the door, so a reg written before the rule (a pick accepted then) keeps
        launching: the variable is NOT stripped from what the CLI receives (a drop would change a running
        session's environment at its next reconnect with no gesture of the user's, and clean nothing: the
        registry holds the value). It is said instead, names only, keyed per session so the ring holds one row."""
        sid = self.be.spawn("web", "/tmp", env=ENV)
        val = _secret_value("notes-token")
        self.be._update_reg(sid, env={**ENV, "NOTES_API_TOKEN": val})   # a store from before the door refused it
        s = self._sess(sid)
        kw = self.be._options(s, dict)
        got = json.loads(Path(kw["settings"]).read_text())["env"]
        self.assertEqual(got, {**ENV, "NOTES_API_TOKEN": val}, "the stored env launches whole; nothing is dropped")
        rows = [(m, kw2) for m, problem, kw2 in self.logged if problem and "NOTES_API_TOKEN" in m]
        self.assertEqual(len(rows), 1, "one problem row names the stored variable: %r" % (self.logged,))
        self.assertNotIn(val, rows[0][0], "the value is never in the line")
        self.assertIn("the session launches with it", rows[0][0], "the fact")
        self.assertIn("flag-settings file", rows[0][0], "and where the value sits")
        ring = rows[0][1]["ring_text"]
        self.assertEqual(ring, sb.stored_offender_ring_text("web", ["NOTES_API_TOKEN"]))
        for promise in ("romp new", "re-declar", "redact", "remove", "clears", "until"):
            self.assertNotIn(promise, rows[0][0], "no remedy is promised (review round 3, 2026-09-19: the redaction road, a "
                                                  "re-declaration that removes the value from every file, left this change)")
            self.assertNotIn(promise, ring)
        self.assertEqual(rows[0][1].get("key"), ("env-stored-credential", sid), "keyed per session: the ring dedupes")
        self.assertFalse(any(val in m for m, _p, _k in self.logged))
        self.assertTrue(self.be.set_env(sid, dict(ENV)), "a re-declaration without the name is accepted by the door")
        self.assertEqual(self._reg(sid)["env"], ENV, "and the registry follows it, as before the door; the file is not this change's")

    def test_a_stored_lowercase_credential_shaped_name_is_said_too(self):
        """The stored-offender line judges by the writer's rule, which folds case since the spawn-spec fix's
        review round 1 (2026-09-18): a reg holding notes_api_token from before the door refused it launches
        whole, like the upper-case case above, and is said once under its own spelling, never its value."""
        sid = self.be.spawn("web", "/tmp", env=ENV)
        val = _secret_value("notes-token")
        self.be._update_reg(sid, env={**ENV, "notes_api_token": val})
        s = self._sess(sid)
        kw = self.be._options(s, dict)
        self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], {**ENV, "notes_api_token": val},
                         "the stored env launches whole; nothing is dropped")
        rows = [(m, kw2) for m, problem, kw2 in self.logged if problem and "notes_api_token" in m]
        self.assertEqual(len(rows), 1, "one problem row names the stored lowercase variable: %r" % (self.logged,))
        self.assertNotIn(val, rows[0][0], "the value is never in the line")
        self.assertEqual(rows[0][1].get("key"), ("env-stored-credential", sid))
        self.assertFalse(any(val in m for m, _p, _k in self.logged))

    def test_a_fork_copies_no_credential_shaped_name_into_its_own_files(self):
        """Review round 1 of the env-pick door (2026-09-18): the fork copied the parent's stored env verbatim except
        the reserved and login names, so a stored credential-shaped name was written into a fresh registry and,
        at the child's first connect, a fresh flag-settings file, by a user gesture (a cut turn, a comment thread)
        no door sees. The copy drops such a name, on its own names-only line (not the reserved drop's, whose words
        would misdescribe it, and with no key: the fork is one gesture, and stubs of _log take none), and the
        parent's registry keeps it (a fact the line states; review round 3, 2026-09-19, sent the remedy away). The
        line's ring text is bounded by construction (FORK_DROP_RING)."""
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()   # transcript_path resolves through this
        try:
            self.be.spawn("parent", self.d, sid=PARENT, env=ENV)
            val = _secret_value("notes-token")
            self.be._update_reg(PARENT, env={**ENV, "NOTES_API_TOKEN": val, "op_session_notes": val})
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertEqual(self._reg(CHILD).get("env"), ENV, "the env inherits less the credential-shaped names")
            kw = self.be._options(self._sess(CHILD), dict)
            self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], ENV, "the child's own file is clean")
            for path in self._files_carrying(val):
                self.assertIn(PARENT, path, "the value sits in the parent's files alone: %r" % (path,))
            self.assertTrue(self._files_carrying(val), "the parent's registry still holds it (nothing is cleaned there)")
            rows = [(m, kw2) for m, problem, kw2 in self.logged if problem and "child" in m and "NOTES_API_TOKEN" in m]
            self.assertEqual(len(rows), 1, "one names-only line for the fork: %r" % (self.logged,))
            self.assertIn("op_session_notes", rows[0][0])
            self.assertIn("not copying credential-shaped", rows[0][0])
            self.assertNotIn("reserved", rows[0][0], "not the reserved drop's words")
            self.assertNotIn("key", rows[0][1], "no dedupe key: a fork is one gesture")
            self.assertNotIn("re-declared", rows[0][0], "no remedy is promised")
            self.assertEqual(rows[0][1]["ring_text"], sb.FORK_DROP_RING % ("child", "NOTES_API_TOKEN and 1 more"),
                             "the ring text: the fork's name and the first variable, the rest counted")
            self.assertLessEqual(len(rows[0][1]["ring_text"]), sb.ERROR_CENTER_TEXT_CAP)
            self.assertFalse(any(val in m for m, _p, _k in self.logged), "no log line carries the value")
            self.assertFalse(any(kw2.get("key") == ("env-stored-credential", CHILD) for _m, _p, kw2 in self.logged),
                             "the child's own connect has no stored offender to report")
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def test_a_stored_login_name_takes_the_reserved_row_and_never_the_stored_offender_row(self):
        """The stored-offender row excludes the legacy names, the identity names and the three login names: those are
        stripped from the launch and have a row of their own (the reserved skip, LegacyReservedEnv), where a
        credential-shaped name of another spelling launches and is named as a fact. The exclusion holds by the
        launch shape (the row judges the stripped env) and is pinned on the rows themselves (the mutation pass of
        review round 3, 2026-09-19: a stored-offender row naming a login name had no test to fail)."""
        sid = self.be.spawn("web", "/tmp", env=ENV)
        val = _secret_value("login-token")
        self.be._update_reg(sid, env={**ENV, "ANTHROPIC_AUTH_TOKEN": val, "ROMP_SID": PARENT})
        kw = self.be._options(self._sess(sid), dict)
        self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], ENV, "the legacy names are stripped from the launch")
        reserved = [m for m, problem, _kw in self.logged if problem and "ignoring reserved" in m]
        self.assertEqual(len(reserved), 1, "the reserved skip's own row: %r" % (self.logged,))
        self.assertIn("ANTHROPIC_AUTH_TOKEN", reserved[0])
        self.assertIn("ROMP_SID", reserved[0])
        self.assertEqual([m for m, _p, kw2 in self.logged if kw2.get("key") == ("env-stored-credential", sid)], [],
                         "no stored-offender row: the legacy names have their own")
        self.assertFalse(any("credential-shaped" in m for m, _p, _k in self.logged), self.logged)
        # beside a name of another spelling, the stored row names that name alone
        val2 = _secret_value("notes-token")
        self.be._update_reg(sid, env={**ENV, "ANTHROPIC_AUTH_TOKEN": val, "NOTES_API_TOKEN": val2})
        del self.logged[:]
        self.be._options(self._sess(sid), dict)
        rows = [(m, kw2) for m, problem, kw2 in self.logged if problem and kw2.get("key") == ("env-stored-credential", sid)]
        self.assertEqual(len(rows), 1, self.logged)
        self.assertIn("NOTES_API_TOKEN", rows[0][0])
        self.assertNotIn("ANTHROPIC_AUTH_TOKEN", rows[0][0], "the login name is the reserved row's, never this one's")
        self.assertEqual(rows[0][1]["ring_text"], sb.stored_offender_ring_text("web", ["NOTES_API_TOKEN"]))
        self.assertFalse(any(val in m or val2 in m for m, _p, _k in self.logged), "no log line carries a value")

    def test_a_forks_two_drops_each_name_their_own_and_a_reserved_name_never_takes_the_fork_row(self):
        """The fork's shaped list excludes the reserved names: the identity and login names take the reserved drop's
        line, with its own words, so the fork row names a credential-shaped name of another spelling alone and its
        ring text counts none of the reserved; a parent whose stored env carries reserved names only gets the reserved
        line and no fork row (the mutation pass of review round 3, 2026-09-19: a fork row naming a login name had no
        test to fail)."""
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()   # transcript_path resolves through this
        try:
            self.be.spawn("parent", self.d, sid=PARENT, env=ENV)
            val = _secret_value("login-token")
            self.be._update_reg(PARENT, env={**ENV, "ANTHROPIC_API_KEY": val, "ROMP_SID": PARENT, "NOTES_API_TOKEN": val})
            self.be.fork("child", PARENT, "a1", sid=CHILD)
            self.assertEqual(self._reg(CHILD).get("env"), ENV, "neither kind of name crosses the copy")
            reserved = [m for m, problem, _kw in self.logged if problem and "dropping reserved" in m]
            shaped = [(m, kw2) for m, problem, kw2 in self.logged if problem and "not copying credential-shaped" in m]
            self.assertEqual(len(reserved), 1, self.logged)
            self.assertIn("ANTHROPIC_API_KEY", reserved[0])
            self.assertIn("ROMP_SID", reserved[0])
            self.assertNotIn("NOTES_API_TOKEN", reserved[0], "the other spelling is not the reserved drop's")
            self.assertEqual(len(shaped), 1, self.logged)
            self.assertIn("NOTES_API_TOKEN", shaped[0][0])
            for name in ("ANTHROPIC_API_KEY", "ROMP_SID"):
                self.assertNotIn(name, shaped[0][0], "a reserved name takes the reserved drop's line, never this one")
            self.assertEqual(shaped[0][1]["ring_text"], sb.FORK_DROP_RING % ("child", "NOTES_API_TOKEN"), "one name, none counted")
            # reserved names alone: the reserved line, and no fork row at all
            self.be._update_reg(PARENT, env={**ENV, "CLAUDE_CODE_OAUTH_TOKEN": val})
            del self.logged[:]
            self.be.fork("child2", PARENT, "a2", sid=CHILD2)
            self.assertEqual(self._reg(CHILD2).get("env"), ENV)
            self.assertTrue(any(problem and "dropping reserved" in m and "CLAUDE_CODE_OAUTH_TOKEN" in m
                                for m, problem, _k in self.logged), self.logged)
            self.assertFalse(any("not copying credential-shaped" in m for m, _p, _k in self.logged),
                             "no fork row for a reserved name: %r" % (self.logged,))
            self.assertFalse(any(val in m for m, _p, _k in self.logged), "no log line carries the value")
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)

    def test_the_fork_and_reserved_rows_two_cuts_are_driven_at_one_two_and_twenty_names(self):
        """tests-3 and correctness-1 (review round 4 of the env-pick door, 2026-09-19): the fork row's two budget cuts
        were never exercised and its one cap assertion was a measurement with the five-character name "child", the
        shape round 3 ruled out for every other row; the two reserved rows (the _options skip and the fork drop) had
        no ring text at all. Through the real fork and the real _options, with a fork or session name past
        RING_SESSION_BUDGET and a first variable past RING_NAME_BUDGET: the rendered ring text equals the format
        applied to the two cut pieces and the count, at one, two and twenty names for the fork row and at one, two and
        all five for the reserved rows (the reserved set is fixed and every name in it fits the name budget, so the
        session cut is the one that fires there and the count is at most four by construction); the kernel log line
        carries every name and the whole session name; no line carries a value. The fork rows are unkeyed, so no
        repeat suffix rides them and the format's worst case is the whole bound."""
        os.environ["CLAUDE_CONFIG_DIR"] = tempfile.mkdtemp()   # transcript_path resolves through this
        try:
            cap = sb.ERROR_CENTER_TEXT_CAP
            long_child = "notes-api-" + "c" * 30                                     # 40 characters, budget 20
            long_name = "NOTES_" + "X" * 40 + "_TOKEN"                               # 52 characters, budget 24; sorts first
            cut_child = sb._cred.cut_to(long_child, sb.RING_SESSION_BUDGET)
            cut_name = sb._cred.cut_to(long_name, sb.RING_NAME_BUDGET)
            for piece, budget in ((cut_child, sb.RING_SESSION_BUDGET), (cut_name, sb.RING_NAME_BUDGET)):
                self.assertTrue(piece.endswith(sb._cred.CUT_MARK) and len(piece) == budget, piece)
            self.be.spawn("notes-api-" + "p" * 30, self.d, sid=PARENT, env=ENV)
            for count in (1, 2, 20):
                with self.subTest(fork_names=count):
                    names = [long_name] + ["ZZ_%02d_TOKEN" % i for i in range(count - 1)]
                    vals = {n: _secret_value("f%d" % i) for i, n in enumerate(names)}
                    self.be._update_reg(PARENT, env={**ENV, **vals})
                    del self.logged[:]
                    child = self.be.fork(long_child, PARENT, "a%d" % count)
                    self.assertEqual(self._reg(child).get("env"), ENV)
                    rows = [(m, kw) for m, problem, kw in self.logged if problem and "not copying credential-shaped" in m]
                    self.assertEqual(len(rows), 1, self.logged)
                    expect = sb.FORK_DROP_RING % (cut_child, cut_name + (" and %d more" % (count - 1) if count > 1 else ""))
                    self.assertEqual(rows[0][1]["ring_text"], expect, "both cuts and the count, through the real fork")
                    self.assertLessEqual(len(expect), cap)
                    self.assertNotIn("key", rows[0][1], "unkeyed: no repeat suffix rides the fork rows")
                    self.assertIn(long_child, rows[0][0], "the kernel log line carries the whole fork name")
                    for n in names:
                        self.assertIn(n, rows[0][0], "and every name whole")
                    self.assertFalse(any(v in m for v in vals.values() for m, _p, _k in self.logged), "no line carries a value")
            reserved = sorted(sb.ENV_RESERVED_NAMES + sb.AUTH_ENV_NAMES)
            self.assertEqual(len(reserved), 5)
            self.assertLessEqual(max(len(n) for n in reserved), sb.RING_NAME_BUDGET, "every reserved name fits the name budget")
            for count in (1, 2, 5):
                with self.subTest(reserved_names=count):
                    names = reserved[:count]
                    val = _secret_value("r%d" % count)
                    self.be._update_reg(PARENT, env={**ENV, **{n: val for n in names}})
                    del self.logged[:]
                    child = self.be.fork(long_child, PARENT, "b%d" % count)
                    self.assertEqual(self._reg(child).get("env"), ENV)
                    rows = [(m, kw) for m, problem, kw in self.logged if problem and "dropping reserved" in m]
                    self.assertEqual(len(rows), 1, self.logged)
                    expect = sb.FORK_RESERVED_RING % (cut_child, sb._cred.first_and_count(names, sb.RING_NAME_BUDGET))
                    self.assertEqual(rows[0][1]["ring_text"], expect, "the fork's reserved drop, bounded")
                    self.assertNotIn("key", rows[0][1], "unkeyed: the fork fires once, so no repeat suffix rides its rows")
                    self.assertTrue(expect.startswith("env (%s): dropping reserved %s" % (cut_child, names[0])), expect)
                    if count > 1:
                        self.assertIn(" and %d more from the inherited env" % (count - 1), expect)
                    self.assertLessEqual(len(expect), cap)
                    self.assertFalse(any("not copying credential-shaped" in m for m, _p, _k in self.logged), "no fork row for a reserved name")
                    # the _options skip of the same names on a session with a long name, launched with them stored
                    sid = self.be.spawn(long_child + "-%d" % count, "/tmp", env=ENV)
                    self.be._update_reg(sid, env={**ENV, **{n: val for n in names}})
                    del self.logged[:]
                    kw = self.be._options(self._sess(sid), dict)
                    self.assertEqual(json.loads(Path(kw["settings"]).read_text())["env"], ENV, "the reserved names are stripped from the launch")
                    rows = [(m, kw2) for m, problem, kw2 in self.logged if problem and "ignoring reserved" in m]
                    self.assertEqual(len(rows), 1, self.logged)
                    cut_sess = sb._cred.cut_to(long_child + "-%d" % count, sb.RING_SESSION_BUDGET)
                    expect = sb.RESERVED_DROP_RING % (cut_sess, sb._cred.first_and_count(names, sb.RING_NAME_BUDGET))
                    self.assertEqual(rows[0][1]["ring_text"], expect, "the launch's reserved skip, bounded")
                    self.assertEqual(rows[0][1].get("key"), ("env-reserved-skip", sid), "keyed (round 6): a second connect counts on the row")
                    self.assertLessEqual(len(expect) + 59, cap, "with the repeat suffix at four digits")
                    self.assertIn(long_child + "-%d" % count, rows[0][0], "the whole session name on the log line")
                    for n in names:
                        self.assertIn(n, rows[0][0])
                    self.assertFalse(any(val in m for m, _p, _k in self.logged))
        finally:
            os.environ.pop("CLAUDE_CONFIG_DIR", None)

    TWO_PIECE = ("RESERVED_DROP_RING", "STORED_OFFENDER_RING", "FORK_RESERVED_RING", "FORK_DROP_RING")

    @staticmethod
    def _worst_cases(formats, keyed, suffix4, cap):
        """One worst case per format on the ENV ROWS line, computed from the format's own pieces with every budget spent
        and the count text at its widest; _log's repeat suffix at a four-digit count rides every KEYED row's (review
        round 6 of the env-pick door, 2026-09-19: round 5 hand-added it to the stored-offender row alone, so keying the
        launch's skip, the natural fix for its per-connect churn, would have crossed the cap under a green table).
        `formats` maps each name on the line to its text (the real module's, or a copy's), `keyed` is derived from
        the key= keyword at each call by the census."""
        S, N, D = "x" * sb.RING_SESSION_BUDGET, "x" * sb.RING_NAME_BUDGET, "x" * sb.RING_SID_BUDGET
        count_worst = " and %s more" % sb._cred.count_text(sb._cred.COUNT_CAP + 1)
        keys = ", ".join(sb.FLAG_SETTINGS_KEYS)
        road = max(sb._cred.CREDENTIAL_RING_ROADS.values(), key=len)
        head = formats["REFUSAL_RING_HEAD"] % S
        worst = {
            "FLAG_SID_RING": [formats["FLAG_SID_RING"] % (max(sb.FLAG_SID_REASONS, key=len), D, keys)],
            "FLAG_LINK_RING": [formats["FLAG_LINK_RING"] % D],
            "FLAG_DIR_LINK_RING": [formats["FLAG_DIR_LINK_RING"] % D],
            "FLAG_UNWRITABLE_RING": [formats["FLAG_UNWRITABLE_RING"] % (D, "x" * sb.RING_CLASS_BUDGET, keys)],
            "HOST_REFUSED_RING": [formats["HOST_REFUSED_RING"] % (S, "x" * sb.RING_REASON_BUDGET)],
            "RESERVED_DROP_RING": [formats["RESERVED_DROP_RING"] % (S, N + count_worst)],
            "STORED_OFFENDER_RING": [formats["STORED_OFFENDER_RING"] % (S, N + count_worst)],
            "FORK_RESERVED_RING": [formats["FORK_RESERVED_RING"] % (S, N + count_worst)],
            "FORK_DROP_RING": [formats["FORK_DROP_RING"] % (S, N + count_worst)],
            "REFUSAL_RING_HEAD": [head + sb._cred.CREDENTIAL_RING_FORMAT % (N + count_worst, "are", road),
                                  head + sb.REFUSAL_NO_REG,
                                  head + sb._cred.cut_to("B" * 1000, cap - len(head))],
        }
        return {name: [t + (suffix4 if name in keyed else "") for t in texts] for name, texts in worst.items()}

    def test_every_format_on_the_env_rows_line_has_its_worst_case_computed_from_the_format_and_fits_the_cap(self):
        """The tie between the derived population (EnvRowsPopulation) and the bounds (review round 4 of the env-pick door,
        2026-09-19; keyed rows derived since round 6): one worst case per format the census's content rows name, no more
        entries and no fewer, so a new row reds this test until its worst case is written down. Which rows are keyed is
        read from the census (the key= keyword at each call): the two rows _options files at every connect, the stored
        offender's and the reserved skip's, and _log's repeat suffix at a four-digit count, read from the real ring,
        rides both; the refusal head has three bodies (the credential ring text under the longest road, the registry-road
        sentence, and any other body cut to what the cap leaves). Each is under ERROR_CENTER_TEXT_CAP and whole through
        the feed's cut, and the two-piece formats' lengths are the identity fixed text + session budget + name budget +
        widest count (+ the suffix when keyed)."""
        km = self._real_ring()
        suffix4 = self._repeat_suffix(9999)
        cap = sb.ERROR_CENTER_TEXT_CAP
        count_worst = " and %s more" % sb._cred.count_text(sb._cred.COUNT_CAP + 1)
        self.assertEqual((count_worst, len(suffix4)), (" and 999+ more", 59))
        c = census(CENSUS_FILES)
        keyed = {fmt for _o, fmt, k in c.content_identities() if k}
        self.assertEqual(keyed, {"RESERVED_DROP_RING", "STORED_OFFENDER_RING"}, "the keyed rows at review round 6, derived from key= at each call")
        on_line = sorted({fmt for _o, fmt, _k in c.content_identities()})
        worst = self._worst_cases({n: getattr(sb, n) for n in on_line}, keyed, suffix4, cap)
        self.assertEqual(sorted(worst), on_line, "one worst case per format on the ENV ROWS line, no more and no fewer")
        lengths = {}
        for fmt_name in on_line:
            fmt = getattr(sb, fmt_name)
            for text in worst[fmt_name]:
                self.assertLessEqual(len(text), cap, (fmt_name, len(text), text))
                self.assertLessEqual(len(text.encode("utf-16-le")) // 2, cap, (fmt_name, "in the error centre's unit, UTF-16 code units (round 7)"))
                self.assertEqual(km._sdk_problem_text(text), text, (fmt_name, "whole in the feed"))
                self.assertTrue(text.startswith(fmt.split("%s")[0]), (fmt_name, text))
            lengths[fmt_name] = max(len(t) for t in worst[fmt_name])
            if fmt_name in self.TWO_PIECE:
                self.assertEqual(fmt.count("%s"), 2, fmt_name)
                self.assertEqual(len(worst[fmt_name][0]) - (len(suffix4) if fmt_name in keyed else 0),
                                 len(fmt % ("", "")) + sb.RING_SESSION_BUDGET + sb.RING_NAME_BUDGET + len(count_worst),
                                 "%s: the format's worst case is its fixed text plus both budgets and the widest count" % fmt_name)
        self.assertEqual(lengths["REFUSAL_RING_HEAD"], cap, "the refusal ring's worst case is the cap exactly (round 3's arithmetic)")
        self.assertEqual(lengths["STORED_OFFENDER_RING"], 178 + len(suffix4), "the stored row: 178 plus the suffix at four digits")
        self.assertEqual(lengths["RESERVED_DROP_RING"], self._two_piece_worst(sb.RESERVED_DROP_RING) + len(suffix4),
                         "the keyed skip (round 6): fixed text + session 20 + name 24 + count 14, plus the suffix at four digits")
        self.assertEqual((len(sb.RESERVED_DROP_RING % ("", "")), lengths["RESERVED_DROP_RING"]), (117, 234), "117 fixed; 234 of 240 with the suffix")
        self.assertEqual(lengths["FORK_RESERVED_RING"], 187, "the fork's reserved drop, unkeyed: it fires once per fork (round 4's 187)")
        self.assertEqual(lengths["FORK_DROP_RING"], 160)
        self.assertEqual((len(sb.HOST_REFUSED_RING % ("", "")), sb.RING_SESSION_BUDGET, sb.RING_REASON_BUDGET, lengths["HOST_REFUSED_RING"]), (22, 20, 198, cap),
                         "the refused-launch row (the post-merge census): 22 fixed + the session's 20 + the reason's 198, what the cap leaves, "
                         "so its worst case is the cap exactly, the refusal ring's arithmetic (HOST worst len = 240)")

    def test_the_refused_launch_rows_ring_text_is_cut_visibly_and_the_ledger_prose_is_not(self):
        """Ruling 1 (a) of the post-merge census (2026-09-20) with its condition (3): the two refused-launch rows'
        ring text is HOST_REFUSED_RING over the session name and the road's reason, each cut to its budget, and a cut
        is VISIBLE (credentials.CUT_MARK as the last character), never a cut that still reads as a whole sentence. The
        helper the sites call is driven at a short reason (whole, 123 characters at a synthetic sid), a 300-character
        reason (cut to the budget, the marker last; 223 with a three-letter name) and a long session name (cut to its
        20 with the marker). The prose the sites hand problem_row is untouched by the helper: the ledger row and the
        kernel log line keep the reason whole (the card reads the ledger), and the ring shows the bounded text."""
        cap, mark = sb.ERROR_CENTER_TEXT_CAP, sb._cred.CUT_MARK
        sid = "11111111-2222-3333-4444-555555555555"
        short = "exited before serving its socket (code 1); see hosts/%s/host.log" % sid
        whole = sb.host_refused_ring_text("web", short)
        self.assertEqual(whole, "the session host for web " + short)
        self.assertEqual(len(whole), 123)
        self.assertNotIn(mark, whole, "a reason inside its budget is whole")
        long_reason = short + ": " + "B" * 300
        cut = sb.host_refused_ring_text("web", long_reason)
        self.assertEqual(len(cut), 22 + 3 + sb.RING_REASON_BUDGET)
        self.assertEqual(len(cut), 223)
        self.assertLessEqual(len(cut), cap)
        self.assertTrue(cut.endswith(mark), "a cut reason ends with the feed's marker, so it never reads as a whole sentence")
        self.assertTrue(cut.startswith("the session host for web exited before serving its socket (code 1); see hosts/%s/host.log: BBB" % sid))
        named = sb.host_refused_ring_text("n" * 40, short)
        self.assertTrue(named.startswith("the session host for " + "n" * (sb.RING_SESSION_BUDGET - 1) + mark + " exited"), "the name is cut to its budget, marked")
        worst = sb.host_refused_ring_text("n" * 400, "r" * 4000)
        self.assertEqual(len(worst), cap, "both budgets spent: the cap exactly")
        self.assertEqual(worst.count(mark), 2)
        km = self._real_ring()
        for text in (whole, cut, named, worst):
            self.assertEqual(km._sdk_problem_text(text), text, "whole through the feed's own cut")

    @staticmethod
    def _centre_cut(text, n):
        """ui/webview/badge-mirror.ts's cap, `s.length > n ? s.slice(0, n - 1) + "…" : s`, over UTF-16 code units the way
        JavaScript counts them; the result is the unit sequence, so a slice inside a surrogate pair shows as a lone surrogate."""
        units = text.encode("utf-16-le")
        if len(units) // 2 <= n:
            return text
        return units[: (n - 1) * 2].decode("utf-16-le", errors="surrogatepass") + "\u2026"

    def test_the_reason_is_cut_in_the_error_centres_unit_so_an_astral_reason_neither_overruns_the_cap_nor_splits_a_pair(self):
        """Round 7 of the review (2026-09-20, extra6-1): RING_REASON_BUDGET is derived from ERROR_CENTER_TEXT_CAP, which is the
        error centre's cut in UTF-16 CODE UNITS (badge-mirror.ts, `s.length` and `s.slice`), while the cut charged it in
        Python code points, so a character above U+FFFF in a host's reason cost the budget one and the centre two. At the
        round-6 head a 300-emoji reason rendered 420 units against the cap of 240 (an overrun of 180; the budget-spending
        worst case 437), and the centre's own slice at 239 units landed on a lone high surrogate for a four-letter session
        name (the fixed prefix's parity decides which half). credentials.cut_to charges two units per code point above
        U+FFFF and takes whole code points, so the row fits the cap in the consumer's unit, the centre's cut has nothing left
        to do (it cannot split a pair it never reaches), and no lone surrogate exists in the text; the marker stays last.
        Headroom would not have closed it (an all-astral reason at the budget is 437 units), and mapping such characters out
        of `said` would have destroyed the traceback tail the reason exists to carry, which is why the cut is unit-aware
        instead. For text within the Basic Multilingual Plane the units agree and the cut is as before."""
        cap, mark = sb.ERROR_CENTER_TEXT_CAP, sb._cred.CUT_MARK
        units = lambda t: len(t.encode("utf-16-le")) // 2
        lone = lambda t: [hex(ord(ch)) for ch in t if 0xD800 <= ord(ch) <= 0xDFFF]
        astral = "\U0001F600" * 300
        for name in ("web", "webb"):
            with self.subTest(name=name):
                text = sb.host_refused_ring_text(name, astral)
                self.assertLessEqual(units(text), cap, (units(text), "the row fits the cap in the centre's unit"))
                self.assertLessEqual(len(text), cap)
                self.assertTrue(text.endswith(mark), "the cut is visible")
                self.assertEqual(self._centre_cut(text, cap), text, "the centre's cut has nothing to do")
                self.assertEqual(lone(text), [], "no lone surrogate: whole code points only")
                self.assertEqual(text.encode("utf-16-le").decode("utf-16-le"), text)
        one = sb.host_refused_ring_text("web", "OSError: " + "\U0001F600" + "B" * 300)
        self.assertLessEqual(units(one), cap, "one astral character in the tail costs the budget two, not one")
        self.assertEqual(self._centre_cut(one, cap), one)
        worst = sb.host_refused_ring_text("n" * 400, "\U0001F600" * 4000)
        self.assertLessEqual(units(worst), cap)
        self.assertEqual(worst.count(mark), 2, "both budgets spent, both cuts marked")
        self.assertEqual(self._centre_cut(worst, cap), worst)
        self.assertEqual(sb._cred.utf16_units("a\U0001F600"), 3, "one BMP code point and one pair")
        self.assertEqual(sb._cred.cut_to("\U0001F600" * 3, 4), "\U0001F600" + mark, "a budget of 4 units holds one pair and the marker, never half a pair")
        self.assertEqual(sb._cred.cut_to("\U0001F600" * 2, 4), "\U0001F600" * 2, "4 units: fits whole")
        self.assertEqual(sb._cred.cut_to("abcd", 3), "ab" + mark, "BMP text: as before")
        self.assertEqual(sb._cred.cut_to("abc", 3), "abc")
        # the centre's cut on a row built by the pre-fix rule, for the record: a code-point cut of the same reason lands the
        # centre's slice inside a pair for the four-letter name (the defect the unit-aware cut removes)
        old = sb.HOST_REFUSED_RING % ("webb", astral[:sb.RING_REASON_BUDGET - 1] + mark)
        self.assertGreater(units(old), cap)
        self.assertEqual(len(lone(self._centre_cut(old, cap))), 1, "the pre-fix row: the centre's slice left a lone surrogate")

    def test_set_envs_refusal_row_charges_its_head_in_the_centres_unit_so_an_astral_registry_name_leaves_the_row_under_the_cap(self):
        """Round 8 of the review (2026-09-21, extra7-3, the refuter's narrowed shape): credentials.cut_to has charged UTF-16
        code units since round 7, but set_env's refusal row computed the body's share of the cap as the cap less len(head),
        in code points, so the two halves of one cap arithmetic were in different units and a head carrying characters
        above U+FFFF left the COMPOSED row over the cap by one unit per such character (nine here). No product door
        reaches it (kernel.NAME_RE admits no such name and the sid is kernel-minted): the registry name is written
        directly, a test road. The composition is measured through the real set_env, not the helper: the row fits the
        cap in the centre's unit exactly (the body's share is the cap less the head's UNITS), the centre's cut has nothing
        to do, no lone surrogate, the marker last; the pre-fix arithmetic is stated beside it. The overrun predates this
        change's delta (nineteen units at round 6's head); the round-7 cut narrowed it and this closes it."""
        cap, mark = sb.ERROR_CENTER_TEXT_CAP, sb._cred.CUT_MARK
        units = lambda t: len(t.encode("utf-16-le")) // 2
        lone = lambda t: [hex(ord(ch)) for ch in t if 0xD800 <= ord(ch) <= 0xDFFF]
        name = "\U0001F600" * 19                     # 19 code points, 38 units: over the 20-unit session budget
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.be._update_reg(sid, name=name)
        head = sb.REFUSAL_RING_HEAD % sb._cred.cut_to(name, sb.RING_SESSION_BUDGET)
        self.assertEqual((len(head), units(head)), (32, 41), "the head: 22 fixed characters and a 20-unit budget spent on nine pairs and the marker")
        bad = "B" * 300 + "-"                          # outside the alphabet: the other-body road, whose body quotes the whole name
        self.assertFalse(self.be.set_env(sid, {bad: "x"}), "refused")
        rows = [kw.get("ring_text") for m, problem, kw in self.logged if problem and str(kw.get("ring_text", "")).startswith(head)]
        self.assertEqual(len(rows), 1, "one problem row with the astral head (this class records _log's calls in self.logged): %r" % (rows,))
        row = rows[0]
        self.assertEqual(units(row), cap, "the composed row spends the cap exactly in the centre's unit: the body's share is the cap less the head's units")
        self.assertLessEqual(len(row), cap)
        self.assertEqual(self._centre_cut(row, cap), row, "the centre's cut has nothing to do")
        self.assertEqual(lone(row), [], "no lone surrogate")
        self.assertTrue(row.endswith(mark), "the cut is visible")
        self.assertIn("bad name", row)
        self.assertNotIn(bad, row, "the name never fits whole: it is cut")
        self.assertEqual((cap - len(head)) - (cap - units(head)), 9,
                         "the pre-fix share, computed in code points, was nine units too large: nine pairs in the head, nine units over the cap")

    SKIP_FORMAT = ('RESERVED_DROP_RING = ("env (%s): ignoring reserved %s from the stored session env: romp sets the identity env; a credential is "\n'
                   '                      "Claude Code\'s own")')
    SKIP_FORMAT_ROUND_4 = ('RESERVED_DROP_RING = ("env (%s): ignoring reserved %s from the stored session env: romp sets the identity env itself, and a "\n'
                           '                      "session\'s credential is Claude Code\'s own")')
    SKIP_KEY = ' key=("env-reserved-skip", sess.sid),'
    FORK_RESERVED_CALL = '% (name, ", ".join(dropped)), problem=True,\n'

    def _module_copy(self, edit):
        src = Path(SDK_BACKEND).read_text(encoding="utf-8")
        new = edit(src)
        self.assertNotEqual(new, src, "the copy's edit must apply")
        path = os.path.join(tempfile.mkdtemp(), "sdk_backend.py")
        Path(path).write_text(new, encoding="utf-8")
        return path

    def _copy_table(self, path, suffix4, cap):
        """The census over a module copy (with credentials.py; EnvRowsPopulation holds that kernel.py adds no content row),
        the copy's own format texts, and the table's longest worst case per format; `self.copy_formats` keeps the copy's
        texts so an expected length is derived from the format rather than kept as a second copy of the arithmetic."""
        c = Census((path, CREDENTIALS_PY), DEFAULT_SOURCES)
        self.assertEqual(c.failures, [])
        keyed = {fmt for _o, fmt, k in c.content_identities() if k}
        on_line = sorted({fmt for _o, fmt, _k in c.content_identities()})
        tree = ast.parse(Path(path).read_text(encoding="utf-8"))
        consts = {t.id: ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                  for t in node.targets if isinstance(t, ast.Name) and t.id in on_line}
        self.assertEqual(sorted(consts), on_line)
        self.copy_formats = consts
        worst = self._worst_cases(consts, keyed, suffix4, cap)
        return keyed, {n: max(len(t) for t in texts) for n, texts in worst.items()}

    def _two_piece_worst(self, fmt):
        """A two-piece format's unkeyed worst case from its own text: fixed text + session budget + name budget + the
        widest count (the one arithmetic; the head's 175 for the skip is this over RESERVED_DROP_RING)."""
        return len(fmt % ("", "")) + sb.RING_SESSION_BUDGET + sb.RING_NAME_BUDGET + len(" and %s more" % sb._cred.count_text(sb._cred.COUNT_CAP + 1))

    def test_the_worst_case_table_reds_where_a_keyed_reserved_row_crosses_the_cap(self):
        """kernel-2 with extra6-1 (review round 5 of the env-pick door, 2026-09-19) and the round-6 roster item: the
        table is re-run against copies of the module with each reserved row keyed, and it reds where a keyed row's
        bound crosses the cap. Both boundary cases: the fork's reserved drop keyed (187 + 59 = 246, over the cap; it
        stays unkeyed, firing once per fork), the launch's skip keyed under round 4's longer format (196 + 59 = 255,
        the way the obvious fix for kernel-2 would have crossed it under round 5's table), and the skip with its key
        removed (175, no suffix, under the cap), so the derivation is shown to read the key= keyword both ways."""
        self._real_ring()
        suffix4 = self._repeat_suffix(9999)
        cap = sb.ERROR_CENTER_TEXT_CAP
        src = Path(SDK_BACKEND).read_text(encoding="utf-8")
        for needle in (self.SKIP_FORMAT, self.SKIP_KEY, self.FORK_RESERVED_CALL):
            self.assertEqual(src.count(needle), 1, "the copy's anchors are in the module once each: %r" % needle)
        with self.subTest(copy="the fork's reserved drop keyed"):
            keyed, lengths = self._copy_table(self._module_copy(lambda s: s.replace(
                self.FORK_RESERVED_CALL, '% (name, ", ".join(dropped)), problem=True, key=("env-fork-reserved", sid),\n')), suffix4, cap)
            self.assertEqual(keyed, {"RESERVED_DROP_RING", "STORED_OFFENDER_RING", "FORK_RESERVED_RING"})
            self.assertEqual(lengths["FORK_RESERVED_RING"], 187 + len(suffix4))
            self.assertEqual([n for n, ln in sorted(lengths.items()) if ln > cap], ["FORK_RESERVED_RING"], "the table reds on the keyed row alone")
        with self.subTest(copy="the skip keyed under round 4's format"):
            keyed, lengths = self._copy_table(self._module_copy(lambda s: s.replace(self.SKIP_FORMAT, self.SKIP_FORMAT_ROUND_4)), suffix4, cap)
            self.assertIn("RESERVED_DROP_RING", keyed)
            self.assertEqual(lengths["RESERVED_DROP_RING"], 196 + len(suffix4))
            self.assertEqual([n for n, ln in sorted(lengths.items()) if ln > cap], ["RESERVED_DROP_RING"])
        with self.subTest(copy="the skip with its key removed"):
            keyed, lengths = self._copy_table(self._module_copy(lambda s: s.replace(self.SKIP_KEY, "")), suffix4, cap)
            self.assertEqual(keyed, {"STORED_OFFENDER_RING"})
            self.assertEqual(lengths["RESERVED_DROP_RING"], self._two_piece_worst(self.copy_formats["RESERVED_DROP_RING"]), "unkeyed, no suffix rides it")
            self.assertEqual(lengths["RESERVED_DROP_RING"], self._two_piece_worst(sb.RESERVED_DROP_RING), "the copy's format is the head's")
            self.assertEqual([n for n, ln in sorted(lengths.items()) if ln > cap], [])

    def test_the_reserved_skip_row_is_keyed_so_a_second_connect_counts_on_it(self):
        """kernel-2 (review round 5 of the env-pick door, 2026-09-19): the launch's reserved skip runs at every connect of
        the same session, and unkeyed it appended a fresh ring entry each time while its sibling 21 lines below was keyed
        to avoid exactly that. Through the real ring: two connects of one session storing a reserved name leave ONE row,
        keyed on the session, counted twice, with _log's repeat suffix, and the short form is the format's."""
        self._real_ring()
        sid = self.be.spawn("web", "/tmp", env=ENV)
        self.be._update_reg(sid, env={**ENV, "ROMP_SID": PARENT})
        s = self._sess(sid)
        self.be._options(s, dict)
        self.be._options(s, dict)
        rows = [r for r in self.be.problems() if "ignoring reserved" in r["text"]]
        self.assertEqual(len(rows), 1, "one row for the session, not one per connect: %r" % (rows,))
        self.assertEqual((rows[0].get("key"), rows[0].get("count")), (("env-reserved-skip", sid), 2))
        self.assertTrue(rows[0]["text"].startswith(sb.RESERVED_DROP_RING % ("web", "ROMP_SID") + " (1 repeat"), rows[0]["text"])
        self.assertNotIn(PARENT, rows[0]["text"], "names, never a value")
        # the kernel log line keeps its words (round 6 shortened the ring FORMAT, not the line; pinned by the addendum)
        self.assertEqual([ln for ln in self.lines if "ignoring reserved" in ln],
                         ["env (web): ignoring reserved ROMP_SID from the stored session env: romp sets the identity env itself, and a "
                          "session's credential is Claude Code's own"] * 2, "one log line per connect, the sentence whole")

    def _real_ring(self):
        """The row as the dashboard reads it: the class stubs _log to capture lines, so the stub goes and the kernel
        log's lines are captured instead (every name whole is the LOG line's promise, the short form's is the cap)."""
        del self.be._log
        self.lines = []
        self.be._log_cb = self.lines.append
        return load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))

    def _repeat_suffix(self, repeats=1, text="probe"):
        """_log's count suffix as the REAL ring renders it after `repeats` repeats of a keyed row whose text is `text`,
        read from the ring rather than spelled here, so a change to that suffix moves the bound this class pins. The
        suffix grows with the count's digits (review round 3, 2026-09-19, extra7-7: the addendum's pin read it at one
        repeat and called the two spare characters a third digit's room, while a third digit in the repeat count costs
        three), so the worst-case pin reads it at a four-digit count."""
        key = ("probe", repeats, text)
        for _ in range(repeats + 1):
            self.be._log(text, problem=True, key=key)
        row = [r for r in self.be.problems() if r.get("key") == key][0]
        self.assertTrue(row["text"].startswith(text + " (%d repeat" % repeats), row["text"][:len(text) + 20])
        return row["text"][len(text):]     # the ring appends the suffix AFTER the whole first text (asserted just above)

    def _stored_row_after_a_repeat(self, session_name, names):
        """A session launched twice with `names` stored under credential-shaped spellings: the keyed row after the ring
        counted the repeat, and the values, which must appear nowhere."""
        sid = self.be.spawn(session_name, "/tmp", env=ENV)
        vals = {n: _secret_value("v%d" % i) for i, n in enumerate(names)}
        self.be._update_reg(sid, env={**ENV, **vals})
        s = self._sess(sid)
        self.be._options(s, dict)
        self.be._options(s, dict)                              # the repeat: the ring counts it on the row, with a suffix
        rows = [r for r in self.be.problems() if r.get("key") == ("env-stored-credential", sid)]
        self.assertEqual(len(rows), 1, "keyed: one row, counted")
        self.assertEqual(rows[0]["count"], 2)
        self.assertIn("repeat", rows[0]["text"], "rendered with the ring's count suffix")
        return rows[0], vals

    STORED_ROW_TAIL = ("launches with it", "value in registry and flag-settings file")   # the fact; no remedy (round 3)

    def test_the_stored_offender_row_fits_the_error_centre_for_one_two_and_twenty_variables(self):
        """regression-1 (review round 2 of the env-pick door, 2026-09-19) and its addendum. The reworded row ran to
        333 characters against the 240-character error-centre cap this PR introduced, so the dashboard clipped it
        mid-parenthesis and lost its tail. Round 2's short form was then pinned at a length two demo names happened to fit,
        and the reviewer showed that the bound was a measurement, not a property: a third stored name, or a longer
        one, clipped the same clause again. The form is bounded by construction now (stored_offender_ring_text: one
        variable named, the rest counted, the session name and the named variable cut to a budget each), and THIS
        test pins the property rather than a length: rendered through the REAL ring (no stub of _log) after a
        repeat, the form a second connect leaves, with the longest 1Password name as the one named, the row fits
        the cap and the feed's cut for one, two and twenty stored variables alike, the tail clause is present in
        every case, the count says how many more, and the kernel log line names every variable whole."""
        km = self._real_ring()
        for count in (1, 2, 20):
            with self.subTest(variables=count):
                names = ["OP_SERVICE_ACCOUNT_TOKEN"] + ["SVC_%02d_API_TOKEN" % i for i in range(count - 1)]   # sorts first
                row, vals = self._stored_row_after_a_repeat("notes-api-web-%02d" % count, names)
                text = row["text"]
                self.assertLessEqual(len(text), sb.ERROR_CENTER_TEXT_CAP, "whole in the error centre: %d characters: %s" % (len(text), text))
                self.assertEqual(km._sdk_problem_text(text), text, "and whole in the feed")
                self.assertIn("OP_SERVICE_ACCOUNT_TOKEN", text, "the first variable in sorted order is named")
                if count > 1:
                    self.assertIn(" and %d more stored" % (count - 1), text, "the rest are a count")
                else:
                    self.assertNotIn("more", text)
                for clause in self.STORED_ROW_TAIL:
                    self.assertIn(clause, text, "the tail is present whatever the count: %s" % text)
                self.assertFalse(any(v in text for v in vals.values()))
                self.assertLessEqual(len(row["first"]), sb.ERROR_CENTER_TEXT_CAP, "the first fire fits too")
                line = [ln for ln in self.lines if "credential-shaped" in ln and "notes-api-web-%02d" % count in ln]
                self.assertEqual(len(line), 2, "one kernel log line per connect: %r" % (self.lines,))
                for n in names:
                    self.assertIn(n, line[0], "the kernel log line names every variable whole")
                self.assertFalse(any(v in ln for v in vals.values() for ln in self.lines))

    def test_the_stored_offender_rows_worst_case_is_computed_from_the_format_and_fits_the_cap(self):
        """The bound as a property of the format (the round-2 addendum, recomputed in review round 3, 2026-09-19: tests-3,
        kernel-7 and extra7-7 found the addendum's pin taking _log's repeat suffix at ONE repeat though it grows with
        the count's digits, 241 against 240 from 100 repeats on, and its "third digit in the count of more" case
        rendering a two-digit count). The worst case the construction allows is computed HERE from the format's own
        pieces: the fixed text, the session budget and the name budget both spent, the count text at its widest
        (credentials.count_text renders "999+" past COUNT_CAP, so the count is bounded by construction too), and the
        suffix as the real ring renders it at a FOUR-digit repeat count. The budgets were set so that sum fits: 120
        + 20 + 24 + 14 + 59 = 237 of 240, and the fixed text is what gave up characters (round 2's read 127). The
        suffix grows a character per digit, so the row fits through a seven-digit repeat count, and past that the
        cut lands inside the suffix, since _log appends it after the whole first text (asserted through the real
        ring at five digits)."""
        km = self._real_ring()
        suffix1 = self._repeat_suffix(1)
        suffix4 = self._repeat_suffix(9999)
        self.assertEqual(len(suffix4), len(suffix1) + 4, "three more digits and the plural: the suffix's only growth")
        fixed = sb.STORED_OFFENDER_RING % ("", "")
        self.assertEqual(fixed.count("%"), 0, "two slots, the session name and the names, and nothing else")
        long_session = "s" * (sb.RING_SESSION_BUDGET + 20)
        long_name = "NOTES_" + "X" * 40 + "_TOKEN"
        count_worst = " and %s more" % sb._cred.count_text(sb._cred.COUNT_CAP + 1)
        self.assertEqual(count_worst, " and 999+ more", "the count text at its widest")
        names = [long_name] + ["ZZ_%04d_TOKEN" % i for i in range(sb._cred.COUNT_CAP + 1)]    # the long one sorts first
        worst = sb.stored_offender_ring_text(long_session, names)
        self.assertEqual(len(worst), len(fixed) + sb.RING_SESSION_BUDGET + sb.RING_NAME_BUDGET + len(count_worst),
                         "both budgets spent, plus the widest count: the format's worst case")
        self.assertIn(count_worst, worst)
        self.assertLessEqual(len(worst) + len(suffix4), sb.ERROR_CENTER_TEXT_CAP,
                             "the worst case fits with the ring's suffix at a four-digit count: %d + %d against %d"
                             % (len(worst), len(suffix4), sb.ERROR_CENTER_TEXT_CAP))
        self.assertEqual(km._sdk_problem_text(worst + suffix4), worst + suffix4, "and whole in the feed")
        for more, text in ((19, " and 19 more"), (119, " and 119 more"), (999, " and 999 more"), (1000, " and 999+ more")):
            row = sb.stored_offender_ring_text(long_session, [long_name] + ["ZZ_%04d_TOKEN" % i for i in range(more)])
            self.assertIn(text, row, "two digits, three digits, the cap and past it")
            self.assertLessEqual(len(row) + len(suffix4), sb.ERROR_CENTER_TEXT_CAP, (more, len(row)))
        for clause in self.STORED_ROW_TAIL:
            self.assertIn(clause, worst)
        # the suffix grows one character per digit of the repeat count (the plural aside), and the ring appends it
        # after the whole first text (_repeat_suffix asserts that through the real ring, here at five digits), so the
        # room left after the worst-case text and the one-repeat suffix is the number of digits the count may grow
        # by before the cut lands, and then it lands inside the suffix, never in the row's own text
        suffix5 = self._repeat_suffix(99999, text=worst)
        self.assertEqual(len(suffix5), len(suffix4) + 1)
        room = sb.ERROR_CENTER_TEXT_CAP - len(worst) - len(suffix1)
        self.assertGreaterEqual(room, 4, "at least a four-digit repeat count fits after the worst-case text; the pin above took exactly that")
        self.assertEqual(room, 7, "the arithmetic the docstring states: 240 - 178 - 55, so a count of up to seven digits fits")
        self.assertEqual(sb.RING_NAME_BUDGET, len("OP_SERVICE_ACCOUNT_TOKEN"),
                         "every 1Password name romp spells EXACTLY is whole under the budget; an OP_SESSION_<account> "
                         "longer than it is cut like any other name (extra7-8, review round 3)")
        self.assertIn("OP_SESSION_" + "a" * 13, sb.stored_offender_ring_text("web", ["OP_SESSION_" + "a" * 13]), "24 characters: whole")
        self.assertIn("OP_SESSION_" + "a" * 12 + sb._cred.CUT_MARK, sb.stored_offender_ring_text("web", ["OP_SESSION_" + "a" * 14]),
                      "25 characters: cut with the marker")
        self.assertEqual(sb.stored_offender_ring_text("web", ["NOTES_API_TOKEN"]),
                         fixed.replace("env ()", "env (web)").replace("credential-shaped  stored", "credential-shaped NOTES_API_TOKEN stored"))
        self.assertIn("credential-shaped NOTES_API_TOKEN and 1 more stored",
                      sb.stored_offender_ring_text("web", ["OP_SERVICE_ACCOUNT_TOKEN", "NOTES_API_TOKEN"]), "two: the first and a count")

    def test_a_variable_or_session_name_past_its_budget_is_cut_with_a_marker_and_the_tail_stays(self):
        """How a very long name is handled (the round-2 addendum, 2026-09-19, which asked for the decision to be
        stated and pinned): the named variable and the session name are each CUT to their budget, the cut marked
        with the feed's own one-character mark, rather than the row naming nothing or the tail going; the kernel
        log line carries both whole. Through the real ring after a repeat, like the rows above."""
        km = self._real_ring()
        long_session = "notes-api-" + "w" * 30                                          # 40 characters, budget 20
        long_name = "NOTES_" + "X" * 40 + "_TOKEN"                                       # 52 characters, budget 24
        row, vals = self._stored_row_after_a_repeat(long_session, [long_name, "ZZ_TOKEN"])
        text = row["text"]
        self.assertLessEqual(len(text), sb.ERROR_CENTER_TEXT_CAP, (len(text), text))
        self.assertEqual(km._sdk_problem_text(text), text)
        cut_name = long_name[:sb.RING_NAME_BUDGET - 1] + sb._cred.CUT_MARK
        cut_session = long_session[:sb.RING_SESSION_BUDGET - 1] + sb._cred.CUT_MARK
        self.assertEqual(len(cut_name), sb.RING_NAME_BUDGET)
        self.assertIn("env (%s): credential-shaped %s and 1 more stored" % (cut_session, cut_name), text)
        self.assertNotIn(long_name, text, "the whole name is the log line's")
        self.assertNotIn(long_session, text)
        for clause in self.STORED_ROW_TAIL:
            self.assertIn(clause, text, "the tail stays when the names are cut: %s" % text)
        self.assertFalse(any(v in text for v in vals.values()))
        line = [ln for ln in self.lines if long_name in ln]
        self.assertEqual(len(line), 2, "the kernel log line carries the whole name at each connect")
        self.assertIn(long_session, line[0])
        self.assertIn("ZZ_TOKEN", line[0])
        self.assertNotIn(sb._cred.CUT_MARK, line[0], "nothing is cut on the log line")
        self.assertEqual(sb._cred.cut_to("short", 24), "short", "a name within its budget is whole, unmarked")

    def test_the_refusal_row_is_headed_once_and_its_ring_text_is_the_bounded_form(self):
        """Review round 1 of the env-pick door (2026-09-18): the set_env line read "pick refused: env: ..." and its
        ring text, then the whole line, ran to 414 characters and was clipped mid-word. The line carries the door's
        head once and every name whole (nothing caps the kernel log line; review round 3, 2026-09-19, corrected the
        docstrings that claimed the feed's cap governed it), and the ring text is the bounded form: set_env's head
        with the session name cut to its budget, then credentials.credential_env_ring_text. Any other refusal's body
        quotes the offending name, which nothing bounds, so the ring cuts it to what the cap leaves after the head."""
        sid = self.be.spawn("web", "/tmp", env=ENV)
        val = _secret_value("notes-token")
        self.assertFalse(self.be.set_env(sid, {**PLAIN, "NOTES_API_TOKEN": val}))
        rows = [(m, kw) for m, problem, kw in self.logged if problem and "pick refused" in m]
        self.assertEqual(len(rows), 1, self.logged)
        line, kw = rows[0]
        self.assertTrue(line.startswith("env (web): pick refused: NOTES_API_TOKEN is credential-shaped"), line)
        self.assertNotIn("refused: env:", line, "the door's own head is not repeated")
        self.assertEqual(line.count("env ("), 1)
        self.assertNotIn("env: ", line, "the door's head appears nowhere in the line")
        self.assertEqual(line, "env (web): pick refused: " + sb._cred.credential_env_refusal(["NOTES_API_TOKEN"]),
                         "the whole sentence on the kernel log line")
        ring = kw.get("ring_text")
        self.assertEqual(ring, sb.REFUSAL_RING_HEAD % "web" + sb._cred.credential_env_ring_text(["NOTES_API_TOKEN"]))
        self.assertTrue(ring.startswith("env (web): pick refused: NOTES_API_TOKEN is credential-shaped: the pick was not saved"), ring)
        self.assertIn("process environment", ring)
        self.assertNotIn(val, line)
        self.assertNotIn(val, ring)
        # another refusal shape keeps its own words, headed once; short, it rides the ring whole
        self.assertFalse(self.be.set_env(sid, {"9BAD": "1"}))
        bad = [(m, kw) for m, problem, kw in self.logged if problem and "9BAD" in m]
        self.assertEqual(len(bad), 1)
        self.assertTrue(bad[0][0].startswith("env (web): pick refused: bad name"), bad[0][0])
        self.assertEqual(bad[0][1].get("ring_text"), bad[0][0])
        # a body that quotes a long offending name is cut to what the cap leaves after the head, marked
        huge = "9" + "B" * 400
        self.assertFalse(self.be.set_env(sid, {huge: "1"}))
        hb = [(m, kw) for m, problem, kw in self.logged if problem and huge in m]
        self.assertEqual(len(hb), 1, "the kernel log line carries the whole name")
        ring = hb[0][1]["ring_text"]
        self.assertEqual(len(ring), sb.ERROR_CENTER_TEXT_CAP)
        self.assertTrue(ring.endswith(sb._cred.CUT_MARK) and ring.startswith("env (web): pick refused: bad name"), ring)
        # the 1Password half hears its own road (review round 2, 2026-09-19): the process environment refuses such a
        # name at boot, so the advice that took the deployment down is not given
        self.assertFalse(self.be.set_env(sid, {"OP_SERVICE_ACCOUNT_TOKEN": _secret_value("op")}))
        op_rows = [(m, kw) for m, problem, kw in self.logged if problem and "OP_SERVICE_ACCOUNT_TOKEN" in m]
        self.assertEqual(len(op_rows), 1, self.logged)
        line, kw = op_rows[0]
        self.assertIn("refuses a 1Password name in its process environment at boot", line)
        self.assertIn("its own file", line)
        self.assertNotIn("Put such a value in the process environment", line)
        self.assertTrue(kw["ring_text"].endswith(sb._cred.CREDENTIAL_RING_ROADS["op"]), kw["ring_text"])

    def test_the_refusal_rings_worst_case_is_computed_from_the_format_and_fits_the_cap(self):
        """regression-2, extra6-3, extra7-3 and tests-2 (review round 3 of the env-pick door, 2026-09-19): the refusal
        row's two cap pins were measurements taken with the session name "web", and the form joined every refused
        name whole behind the whole session name, so an ordinary session name, six names, or one long name pushed the
        ring text past the error centre's cap and around eleven names the cut landed inside the name list. The
        construction: set_env's head cuts the session name (or the sid a nameless registry falls back to) to
        RING_SESSION_BUDGET; credential_env_ring_text names the first variable cut to RING_NAME_BUDGET, counts the rest
        through the bounded count text, and appends the road of the half matched. The worst case, both budgets and
        the widest count spent under the longest road (the mixed pick's), is computed here from those pieces and
        asserted under the cap; then the real set_env is driven to that worst case, and to one, two and twenty names,
        a session name past its budget, and the sid fallback, each rendered form under the cap with its tail present.
        The kernel log line carries every name and the whole session name."""
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
        cap = sb.ERROR_CENTER_TEXT_CAP
        road = max(sb._cred.CREDENTIAL_RING_ROADS.values(), key=len)
        self.assertEqual(road, sb._cred.CREDENTIAL_RING_ROADS["mixed"], "the mixed pick hears the longest road")
        count_worst = sb._cred.count_text(sb._cred.COUNT_CAP + 1)
        names_worst = "%s and %s more" % ("x" * sb.RING_NAME_BUDGET, count_worst)
        worst = (sb.REFUSAL_RING_HEAD % ("x" * sb.RING_SESSION_BUDGET)) + sb._cred.CREDENTIAL_RING_FORMAT % (names_worst, "are", road)
        self.assertLessEqual(len(worst), cap, "the format's worst case fits: %d against %d" % (len(worst), cap))
        self.assertEqual(km._sdk_problem_text(worst), worst, "and whole in the feed")
        # The roads' budget is DERIVED here and nowhere typed (round 9 of fork PR #781's review, extra7-1: the body and the
        # module's docstring typed "of 113" and "one character of headroom", both wrong by one against this pin's figures):
        # what the cap leaves after the head at its session budget and the format at its name budget and widest count.
        # _ring_road_budget is the statement of record; the commit message and the body paste its output, never a figure
        budget, lengths = _ring_road_budget()
        self.assertEqual(budget, cap - len(worst) + len(road), "the budget is what the cap leaves the road: %r" % (lengths,))
        self.assertEqual(lengths["mixed"], len(road))
        self.assertLessEqual(lengths["mixed"], budget, "the mixed road within the derived budget: %r" % (lengths,))
        self.assertEqual(cap - len(worst), budget - lengths["mixed"], "the headroom is the budget less the mixed road: %r" % (lengths,))
        for other in ("op", "suffix"):
            self.assertLess(len(sb._cred.CREDENTIAL_RING_ROADS[other]), len(road))
        # the real row at the worst case: a session name past its budget, a first name past its budget, a thousand
        # more names of both halves (the mixed road), every value built at run time and in no line
        long_session = "notes-api-" + "w" * 30                                      # 40 characters, budget 20
        long_name = "NOTES_" + "X" * 40 + "_TOKEN"                                   # 52 characters, budget 24; sorts first
        sid = self.be.spawn(long_session, "/tmp", env=ENV)
        val = _secret_value("notes-token")
        pick = {long_name: val, "op_session_notes": val, **{"ZZ_%04d_TOKEN" % i: val for i in range(sb._cred.COUNT_CAP)}}
        self.assertEqual(len(pick), sb._cred.COUNT_CAP + 2)
        self.assertFalse(self.be.set_env(sid, pick))
        rows = [(m, kw) for m, problem, kw in self.logged if problem and "pick refused" in m]
        self.assertEqual(len(rows), 1, len(self.logged))
        line, kw = rows[0]
        ring = kw["ring_text"]
        self.assertEqual(len(ring), len(worst), "both budgets and the widest count spent: the format's worst case, through the real row")
        self.assertTrue(ring.startswith(sb.REFUSAL_RING_HEAD % sb._cred.cut_to(long_session, sb.RING_SESSION_BUDGET)), ring)
        self.assertIn(sb._cred.cut_to(long_name, sb.RING_NAME_BUDGET) + " and %s more are credential-shaped: the pick was not saved. " % count_worst, ring)
        self.assertTrue(ring.endswith(road), "the mixed road, whole, at the tail")
        self.assertIn(long_session, line, "the kernel log line carries the whole session name")
        for n in (long_name, "op_session_notes", "ZZ_0000_TOKEN", "ZZ_%04d_TOKEN" % (sb._cred.COUNT_CAP - 1)):
            self.assertIn(n, line, "and every name whole")
        self.assertNotIn(val, line)
        self.assertNotIn(val, ring)
        self.logged.clear()
        # one, two and twenty names of one half, through the real row: the count, the tail, the cap
        sid2 = self.be.spawn("web", "/tmp", env=ENV)
        for count in (1, 2, 20):
            with self.subTest(names=count):
                self.logged.clear()
                self.assertFalse(self.be.set_env(sid2, {"SVC_%02d_API_TOKEN" % i: val for i in range(count)}))
                rows = [(m, kw) for m, problem, kw in self.logged if problem and "pick refused" in m]
                self.assertEqual(len(rows), 1)
                ring = rows[0][1]["ring_text"]
                self.assertLessEqual(len(ring), cap, (count, len(ring), ring))
                self.assertEqual(km._sdk_problem_text(ring), ring)
                self.assertTrue(ring.startswith("env (web): pick refused: SVC_00_API_TOKEN"), ring)
                if count > 1:
                    self.assertIn(" and %d more are credential-shaped" % (count - 1), ring)
                else:
                    self.assertIn("SVC_00_API_TOKEN is credential-shaped", ring)
                self.assertIn("the pick was not saved", ring)
                self.assertTrue(ring.endswith(sb._cred.CREDENTIAL_RING_ROADS["suffix"]), ring)
                for i in range(count):
                    self.assertIn("SVC_%02d_API_TOKEN" % i, rows[0][0], "every name on the log line")
                self.assertNotIn(val, rows[0][0])
        # the sid fallback of a nameless registry: the head cuts the 36-character sid to the session budget
        self.logged.clear()
        self.be._update_reg(sid2, name="")
        self.assertFalse(self.be.set_env(sid2, {"NOTES_API_TOKEN": val}))
        rows = [(m, kw) for m, problem, kw in self.logged if problem and "pick refused" in m]
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0][0].startswith("env (%s): pick refused: " % sid2), "the log line carries the whole sid")
        self.assertTrue(rows[0][1]["ring_text"].startswith(sb.REFUSAL_RING_HEAD % sb._cred.cut_to(sid2, sb.RING_SESSION_BUDGET)),
                        rows[0][1]["ring_text"])
        self.assertLessEqual(len(rows[0][1]["ring_text"]), cap)

    def test_the_error_centre_cap_is_the_badge_mirrors_literal(self):
        ts = Path(os.path.dirname(HERE), "ui", "webview", "badge-mirror.ts").read_text()
        # the SDK problem row's own function, sliced (review round 2, 2026-09-19: the same literal caps the unrelated
        # sync-notices row in this file, so a whole-file assertIn stayed green when the SDK row's cap alone changed);
        # str.index raises when a marker is gone, so a rename fails loudly instead of slicing nothing
        start = ts.index("export function sdkProblemNotices")
        end = ts.index("export function", start + 1)
        body = ts[start:end]
        self.assertIn("cap(r.text, %d)" % sb.ERROR_CENTER_TEXT_CAP, body,
                      "the constant mirrors the cut the dashboard's error centre applies to an SDK problem row")
        self.assertEqual(body.count("cap(r.text, "), 1, "one cut in that function, the one the constant mirrors")
        km = load_source("romp_kernel", os.path.join(BIN, "romp-kernel"))
        self.assertEqual(km._sdk_problem_text.__defaults__, (km.SDK_PROBLEM_TEXT_CAP,), "the feed's cut is the constant")

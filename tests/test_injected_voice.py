#!/usr/bin/env python3
"""Every message romp injects into a session is written as the USER asking, not as romp reporting
(the user rule, 2026-07-24 — CLAUDE.md "Messages we inject into a session").

The recipient is an agent with NO idea it is being tracked. It has never seen the feed, has no concept
of a card, a goal, a board or a column, and cannot act on any of it. A message that narrates that
machinery reads as a system notice rather than the person it works for asking for something. The
2026-07-24 sweep found five: the two feed status asks, the multi-goal bundle, the nudge quote header,
and the fork/stalled nudge. (The clear wrap-up retired 2026-08-23: clear is a silent discard.)

This test renders each injected body from SYNTHETIC fixtures and fails on romp vocabulary in the PROSE.
It is the guardrail behind the CLAUDE.md rule, so the rule holds without anyone remembering it.

Scope note — what is deliberately NOT checked:
- the MARKER TAIL (everything from the first "<!--"). It names romp on purpose in `romp-goal-id` /
  `romp-injected`, and its romp-note describes the comments as "an external tracking system" precisely
  so it does NOT have to name romp to the model. Prose only.
- the SessionStart instruction, which asks for ordinary self-reporting (what you finished, what you're
  blocked on) and names no machinery.
- the session prompt's housekeeping note (claude/romp-session-prompt.md), the ONE place romp is named
  to a session on purpose: it pre-explains the [romp] / <!-- romp-* --> artifacts as an external
  session manager's bookkeeping to ignore (the user 2026-07-25). Pinned by test_session_prompt.py.
- sdk_backend's "[romp] The kernel restarted…" notices, which are genuinely ABOUT romp: they tell a
  session why its turn was cut, so naming it is the point (and the housekeeping note gives the
  name meaning). The rename ping (RENAME_NUDGE, 2026-08-24) is the same family — it tells a session
  its own new name — and is pinned below to stay one marker-free line with no romp nouns beyond
  the sanctioned prefix.

SYNTHETIC fixtures only (placeholder ids, invented goal text).
"""
import json
import os
import re
import tempfile
import unittest
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_voice", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
TOP, SUB_OPEN, SUB_BLOCKED, TOP2 = (SID + ":g1", SID + ":g2", SID + ":g3", SID + ":g4")
T0 = 1781100000

# romp's OWN vocabulary — words that name a thing only romp knows about. A message using one of these
# is describing the tracking system to someone who has never heard of it.
ROMP_WORDS = [
    ("romp", "the product name — the recipient has never heard of it"),
    ("card", "a feed object; the agent sees no feed"),
    ("board", "a column layout the agent cannot see"),
    ("goal", "romp's unit of tracking, not a word the user would use to an agent"),
    ("cleared", "a board gesture"),
    ("dismissal", "a board gesture"),
    ("status check", "announces a form rather than asking a question"),
    ("nudge", "romp's name for this message"),
]


def _nodes():
    return {TOP: {"id": TOP, "text": "Ship the notes API", "parentId": None, "nodeComplete": False,
                  "blocked": False, "cleared": False, "why": "The client is waiting on it.",
                  "summary": "Endpoints are live and the client is wired up.", "t": T0, "mt": T0},
            SUB_OPEN: {"id": SUB_OPEN, "text": "Backfill the fixtures", "parentId": TOP,
                       "nodeComplete": False, "blocked": False,
                       "why": "Needed before the load test.", "t": T0, "mt": T0},
            SUB_BLOCKED: {"id": SUB_BLOCKED, "text": "Pick the rate-limit ceiling", "parentId": TOP,
                          "nodeComplete": False, "blocked": True,
                          "blockWhy": "Need you to choose a number.", "t": T0, "mt": T0},
            TOP2: {"id": TOP2, "text": "Write the migration guide", "parentId": None,
                   "nodeComplete": False, "blocked": False, "cleared": False, "t": T0, "mt": T0}}


def prose(body):
    """The part a model actually reads as instruction: everything before the marker tail."""
    return body.split("<!--")[0]


# ── the widened passage desc (the anchors follow-on, 2026-09-07) ─────────────────────────────────
# A passage comment whose anchor the host widened — the passage recurs, and the extra context is what tells
# the copies apart — names its copy by its surroundings: `on "<quote>", the one after "…" and before "…"`,
# each side JSON-quoted so a context holding a line break or a quotation mark keeps the message's
# `Comment <id> (…):` line one line (file-comments-model.ts passageDesc). The sides print whole, up to
# DESC_CTX_MAX characters each (five of the host's 24-character steps); past that on either side — at the
# host's cap, ANCHOR_CTX_CAP a side, where the anchor may still tie and the first form put a kilobyte of
# escaped text on the line (the review's round 2, 2026-09-07) — the desc keeps the plan's `on "<quote>"`
# and adds RECURS_CLAUSE, a short clause saying the text recurs. Two specimens are the composer's own
# test's literals, copied (file-comments-model-recurring.test.ts) and pinned to that file so a copy cannot
# outlive its original; the rest — the widest whole form, and the short form — are built with
# _widened_desc, a mirror of passageDesc's assembly (JSON.stringify and json.dumps(ensure_ascii=False)
# write the same escapes for the text a sidecar holds), itself pinned to those literals and to the
# composer's constants, which are read from the source so a moved or reworded one fails loudly.
_MODEL_SRC = Path(os.path.dirname(HERE), "ui", "webview", "file-comments-model.ts").read_text(encoding="utf-8")
_HOST_SRC = Path(os.path.dirname(HERE), "tools", "file-comments-host.mjs").read_text(encoding="utf-8")


def _source_const(src, where, pattern):
    """The one capture of `pattern` in a module's source: a constant the specimens must track."""
    m = re.search(pattern, src, re.M)
    assert m, ("%s no longer defines the constant %r at module level — re-pin the specimens here, do not drop them"
               % (where, pattern))
    return m.group(1)


ANCHOR_CTX_CAP = int(_source_const(_HOST_SRC, "tools/file-comments-host.mjs", r"^export const ANCHOR_CTX_CAP = (\d+);"))
ANCHOR_CTX = int(_source_const(_MODEL_SRC, "file-comments-model.ts", r"^export const ANCHOR_CTX = (\d+);"))
DESC_CTX_MAX = ANCHOR_CTX * int(_source_const(_MODEL_SRC, "file-comments-model.ts",
                                              r"^export const DESC_CTX_MAX = ANCHOR_CTX \* (\d+);"))
# the composer's clause for a recurring passage whose copies the message cannot tell apart, COPIED (pinned below)
RECURS_CLAUSE = ", which appears more than once with the same text around each copy"


def _widened_desc(quote, prefix, suffix):
    """passageDesc's assembly for a widened anchor: the quote's first 40 characters plain; then, with both sides
    within DESC_CTX_MAX, each non-empty side JSON-quoted and the sides joined with " and " — else RECURS_CLAUSE."""
    head = 'on "%s"' % quote[:40]
    if len(prefix) > DESC_CTX_MAX or len(suffix) > DESC_CTX_MAX:
        return head + RECURS_CLAUSE
    sides = []
    if prefix:
        sides.append("after " + json.dumps(prefix, ensure_ascii=False))
    if suffix:
        sides.append("before " + json.dumps(suffix, ensure_ascii=False))
    return head + ", the one " + " and ".join(sides)


RECURRING_COMMENTS = [
    # the second copy: its context holds a quotation mark, a tab and a line break, and the escapes carry them
    {"id": "1781100000010-612",
     "desc": r'on "Ship it.", the one after "He said \"ready\", then\ttyped: " and before "\nNo regressions were seen in the nightly run."',
     "body": "Not yet."},
    # the first copy, at the file's start: no prefix to name, so only the side the file has
    {"id": "1781100000011-0",
     "desc": r'on "Ship it.", the one before "\n\nThe tests pass on every supported platform."',
     "body": "Say it once."},
]
# the widest whole form: both sides at exactly DESC_CTX_MAX, each holding quotation marks and line breaks — the
# longest Comment line a send carries
_PARA = 'The nightly run said "ready" on every supported platform.\n'
_BOUND_TEXT = _PARA * (DESC_CTX_MAX // len(_PARA) + 1)
BOUND_PREFIX, BOUND_SUFFIX = _BOUND_TEXT[-DESC_CTX_MAX:], _BOUND_TEXT[:DESC_CTX_MAX]
WIDEST_COMMENT = {"id": "1781100000012-1740", "desc": _widened_desc("Ship it.", BOUND_PREFIX, BOUND_SUFFIX),
                  "body": "Which of these is the one you mean?"}
# past the bound: the host's anchor at its cap on copies of one paragraph the cap cannot tell apart, so the desc
# reads the same on every copy (the composer's cap test's specimen, file-comments-model-cap.test.ts) — the first
# through the mirror from a cap-width anchor, the second the literal a reader should expect
RECURS_COMMENTS = [
    {"id": "1781100002000-1213", "desc": _widened_desc("the marker phrase", "x" * ANCHOR_CTX_CAP, "y" * ANCHOR_CTX_CAP),
     "body": "Say it once."},
    {"id": "1781100003000-2423", "desc": 'on "the marker phrase"' + RECURS_CLAUSE, "body": "And here."},
]


# ── the desc composers' source scan ──────────────────────────────────────────────────────────────
# The Send to session message's parenthetical (`desc`) is composed in the webview and the kernel prints
# it verbatim, so its fixed phrases are scanned at the SOURCE (test_the_client_composed_desc_speaks_
# plainly_at_its_source). A composer's phrases are not all in its own body: regionDesc prints a
# coordinate that is not a number as UNREADABLE, a module constant it reaches through fmt2, and the
# first cut of the scan read only the function's span, so a romp noun in that constant would have
# reached a session unscanned (review finding, 2026-09-06). The scan therefore follows every identifier
# a composer's code references to its module-level definition — in the same file, or through a relative
# `import { … } from "./…"` / `import * as … from "./…"` — and reads those too, transitively, so "every
# fixed phrase a desc can carry" holds by construction rather than by a hand-kept list. Comments and
# types are not emitted and are skipped; a template literal's `${…}` is code, followed but not scanned
# as prose. A relative import that no longer resolves, or an imported name the module does not define,
# fails loudly rather than being skipped (a silent skip is the gap this exists to close). So does a DEFAULT
# import (`import x from "./…"`, alone or beside a `{ … }` list) that a composer's code references: the
# scan does not follow one — the webview's only default import today is the vendored track-changents engine,
# whose source is not a desc's — so a composer reaching a helper that way would otherwise be skipped
# silently; the names in the `{ … }` list beside it are followed like any named import.
_TOKEN = re.compile(r'"((?:[^"\\\n]|\\.)*)"|\'((?:[^\'\\\n]|\\.)*)\'|`((?:[^`\\]|\\.)*)`'
                    r'|//[^\n]*|/\*.*?\*/', re.S)
_INTERP = re.compile(r"\$\{([^{}]*)\}")
_IDENT = re.compile(r"\b[A-Za-z_$][\w$]*\b")
_MEMBER = re.compile(r"\b([A-Za-z_$][\w$]*)\s*\.\s*([A-Za-z_$][\w$]*)")
# where the next module-level statement (or a comment) starts at column 0: the end of the one before it
_TOP_START = re.compile(r"^(?:export|const|let|var|function|async|class|type|interface|enum|declare|import)\b"
                        r"|^//|^/\*", re.M)
_NAMED_IMPORT = re.compile(r"^import\s+(type\s+)?(?:[A-Za-z_$][\w$]*\s*,\s*)?\{([^}]*)\}\s*from\s*[\"']([^\"']+)[\"']",
                           re.M)
_NS_IMPORT = re.compile(r"^import\s+\*\s+as\s+([A-Za-z_$][\w$]*)\s+from\s*[\"']([^\"']+)[\"']", re.M)
_DEFAULT_IMPORT = re.compile(r"^import\s+(?!type\b)([A-Za-z_$][\w$]*)\s*(?:,\s*(?:\{[^}]*\}|\*\s+as\s+[A-Za-z_$][\w$]*))?"
                             r"\s*from\s*[\"']([^\"']+)[\"']", re.M)


def _value_def(src, name):
    """The module-level VALUE definition of `name` in `src` — const/let/var/function/class/enum at column 0 —
    as the text from its head to the next column-0 statement or comment. None when there is none."""
    m = re.search(r"^(?:export\s+(?:default\s+)?)?(?:const|let|var|(?:async\s+)?function\*?|class|(?:const\s+)?enum)"
                  r"\s+%s\b" % re.escape(name), src, re.M)
    if not m:
        return None
    line_end = src.find("\n", m.end())
    if line_end < 0:
        return src[m.start():]
    nxt = _TOP_START.search(src, line_end + 1)
    return src[m.start():nxt.start() if nxt else len(src)]


def _is_type_def(src, name):
    """A `type` or `interface` at column 0: imported without the `type` modifier it is still not a value."""
    return re.search(r"^(?:export\s+)?(?:type|interface)\s+%s\b" % re.escape(name), src, re.M) is not None


def _imports(src):
    """(local name → (module spec, exported name)) for the file's named imports, type-only ones dropped;
    (namespace → module spec) for its `import * as` ones; and (local name → module spec) for its default imports,
    which the scan refuses to follow rather than skip."""
    named, spaces, defaults = {}, {}, {}
    for type_only, names, spec in _NAMED_IMPORT.findall(src):
        if type_only:
            continue
        for part in names.split(","):
            part = part.strip()
            if not part or part.startswith("type "):
                continue
            exported, _, local = part.partition(" as ")
            named[(local or exported).strip()] = (spec, exported.strip())
    for ns, spec in _NS_IMPORT.findall(src):
        spaces[ns] = spec
    for local, spec in _DEFAULT_IMPORT.findall(src):
        defaults[local] = spec
    return named, spaces, defaults


def _resolve_module(from_file, spec):
    """The file a relative import spec names, or None: bare, with a TypeScript extension, an ESM `.js` spelling
    of a `.ts` file, or a directory's index."""
    base = os.path.normpath(os.path.join(os.path.dirname(from_file), spec))
    cands = [base + ext for ext in ("", ".ts", ".tsx", ".mts", ".js", ".mjs")] + [os.path.join(base, "index.ts")]
    stem, ext = os.path.splitext(base)
    if ext in (".js", ".mjs"):
        cands += [stem + ".ts", stem + ".mts"]
    for c in cands:
        if os.path.isfile(c):
            return c
    return None


def _code_of(span):
    """The span as CODE: comments and string literals blanked, a template literal's `${…}` kept."""
    return _TOKEN.sub(lambda m: " ".join(_INTERP.findall(m.group(3))) if m.group(3) is not None else " ", span)


def _literals_of(span):
    """The span's string literals as PROSE: comments dropped, a template literal's `${…}` blanked."""
    return [a or b or _INTERP.sub(" ", c) for a, b, c in _TOKEN.findall(span) if a or b or c]


def _desc_closure(path, name):
    """Every string literal the composer `name` defined in `path` can emit: its own, and those of every
    module-level value its code references, transitively, across relative imports. Returns (literals,
    reached): literals as [(file basename, def name, literal)], reached as the set of (basename, def name)
    read. Raises AssertionError when the composer has no column-0 definition in `path`, when a referenced
    name is imported from a relative module that does not resolve to a file, or when that module defines no
    such value (a re-export, or a rename): each is a case where the scan would otherwise read nothing and
    pass."""
    literals, reached, cache = [], set(), {}

    def read(p):
        if p not in cache:
            cache[p] = Path(p).read_text(encoding="utf-8")
        return cache[p]

    def imported(p, local, spec, exported):
        target = _resolve_module(p, spec)
        if target is None:
            raise AssertionError("%s imports %r from %r, which resolves to no file — the module moved or was "
                                 "renamed; re-pin the composer's helpers, do not drop the scan"
                                 % (os.path.basename(p), local, spec))
        tsrc = read(target)
        if _value_def(tsrc, exported) is None:
            if _is_type_def(tsrc, exported):
                return
            raise AssertionError("%s imports %r from %r, but %s defines no such value at column 0 (a re-export, "
                                 "or a rename) — re-pin it here, do not drop the scan"
                                 % (os.path.basename(p), exported, spec, os.path.basename(target)))
        visit(target, exported)

    def visit(p, n):
        if (p, n) in reached:
            return
        reached.add((p, n))
        src = read(p)
        span = _value_def(src, n)
        base = os.path.basename(p)
        literals.extend((base, n, lit) for lit in _literals_of(span))
        code = _code_of(span)
        named, spaces, defaults = _imports(src)
        for ns, member in _MEMBER.findall(code):
            if ns in spaces:
                imported(p, ns + "." + member, spaces[ns], member)
        for ident in sorted(set(_IDENT.findall(code))):
            if ident != n and _value_def(src, ident) is not None:
                visit(p, ident)
            elif ident in named:
                imported(p, ident, *named[ident])
            elif ident in defaults:
                raise AssertionError("%s.%s references %r, a default import from %r, which the scan does not follow — "
                                     "import the helper by name so its phrases are read, or extend the scan; do not "
                                     "leave it unread" % (base, n, ident, defaults[ident]))

    if _value_def(Path(path).read_text(encoding="utf-8"), name) is None:
        raise AssertionError("%s: no module-level definition of %s at column 0 — the desc composer moved or "
                             "was renamed; re-pin it here" % (os.path.basename(path), name))
    visit(path, name)
    return literals, {(os.path.basename(p), n) for p, n in reached}


def _romp_hits(literals):
    """The (basename, def name, literal, word, why) of every romp word a scanned literal carries."""
    return [(base, n, lit, word, why) for base, n, lit in literals for word, why in ROMP_WORDS if word in lit.lower()]


class InjectedBodiesSpeakAsTheUser(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved_goaldir, self.saved_state = jd.GOALDIR, jd.STATE
        jd.GOALDIR, jd.STATE = Path(self.td.name), Path(self.td.name)
        (jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 4, "nodes": _nodes(), "placements": {}, "status": {}}))
        # open user todos for the context block below — the same synthetic notes-api world
        km._user_todos_cache.clear()
        km._set_user_todos(True)                     # the feature switch is OFF by default (2026-09-03)
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login — building the open "
                               "routes meanwhile")
        km._add_user_todo(SID, "Need a staging API key before the load test can run")

    def tearDown(self):
        jd.GOALDIR, jd.STATE = self.saved_goaldir, self.saved_state
        km._user_todos_cache.clear()
        self.td.cleanup()

    def _file_warning(self):
        """The warning POST /usertodo answers for a `file` that cannot become absolute, rendered for a session
        with no recorded cwd (a PRIVATE synthetic sid no store knows, so nothing is minted under it)."""
        stored, warning = km._user_todo_file("docs/report.md", "7b7b7b7b-1111-4222-8333-944444444444")
        self.assertEqual(stored, "docs/report.md", "kept as given")
        self.assertIsInstance(warning, str)
        self.assertIn("did not resolve", warning)
        return warning

    def _bodies(self):
        """Every message romp injects, by name, rendered from the same synthetic store."""
        nodes = _nodes()
        bodies = {
            "auto-nudge": km.AUTO_NUDGE_TEXT,
            "fork nudge": km.AUTO_NUDGE_STALLED_TEXT,
            "nudge on a hierarchical goal":
                km._followup_body(TOP, None, km.AUTO_NUDGE_TEXT, injected=True, auto=True),
            "fork nudge on a hierarchical goal":
                km._followup_body(TOP, None, km.AUTO_NUDGE_STALLED_TEXT, injected=True, auto=True,
                                  stalled=True),
            "typed follow-up on a summary": km._followup_body(TOP, None, "ship it"),
            # the Continue button's canned reply (the user 2026-08-08) — rides the typed-reply path,
            # rendered exactly as the recipient session will see it
            "continue button": km._followup_body(TOP, None, km.CONTINUE_TEXT),
            "multi-goal bundle": km._nudge_bundle_body([TOP, TOP2], nodes, set()),
            "multi-goal bundle (fork)": km._nudge_bundle_body([TOP, TOP2], nodes, {TOP}),
            # the Merge handoff (the user 2026-08-23): a comment thread's discussion folded back into
            # the parent session — the reader has never heard of romp; it must read as the person's
            # own record of a side discussion
            "comment-thread merge": km._merge_body(
                "the caching layer should be write-through",
                [{"who": "user", "text": "should we make the cache write-through instead?"},
                 {"who": "assistant", "text": "Yes: write-through avoids the stale-read window and "
                                              "the extra invalidation pass; the cost is one write "
                                              "per update, which this workload absorbs."}]),
            "debt reminder (question)": km._debt_reminder_body(
                [("web", T0, "question", "Which port should the staging server use?")]),
            "debt reminder (handoff)": km._debt_reminder_body(
                [("api", T0, "delegate", "Take over the fixtures backfill and report when it lands.")]),
            "debt reminder (several)": km._debt_reminder_body(
                [("web", T0, "question", "Which port should the staging server use?"),
                 ("api", T0 + 5, "delegate", "Take over the fixtures backfill.")]),
            # the awaiting BACKSTOP (kernel AWAITING_BACKSTOP_TEXT): missed by the 2026-07-24 sweep's
            # index, so it shipped saying "goal" twice and announcing "(Automated re-check…)" until
            # 2026-08-11 — exactly the drift this index exists to catch
            "awaiting backstop": km.AWAITING_BACKSTOP_TEXT,
            # a comment thread's opening message (the user 2026-08-13): the highlight + comment are
            # the user's own words; the quoting frame around them is romp-authored and scanned here
            "comment thread opener": km._comment_first_message(
                "Cap the retry delay at two minutes.", "Why two minutes and not five?"),
            # the reply to a USER TODO (plans/user-todos.md): the todo's own short line anchors the
            # user's answer (`Re: <text> — <reply>`) — the frame is romp-authored and scanned here
            "user-todo answer": km._user_todo_answer_body(
                "Need the auth-scheme decision to wire login — building the open routes meanwhile",
                "Go with the session cookie for now."),
            # the SessionStart context block (plans/user-todos.md slice 3): a resumed/compacted
            # session's open todos as its OWN outstanding notes to the person it works for. Not an
            # injected MESSAGE (it rides additionalContext, costing no turn) but the same veil
            # applies — it must read as the agent's own notes, never a tracking system's; naming
            # withdraw_user_todo is correct (the agent holds that tool)
            "user-todo context block": km._user_todo_context_block(SID),
            # the filing reply's file WARNING (the todo-file follow-on, 2026-09-07): the kernel's words for a
            # `file` that did not resolve (a relative path, no working directory recorded for the session),
            # which the postal tool's add_user_todo relays verbatim into the agent's reply — so the same veil
            "user-todo file warning": self._file_warning(),
            # the dashboard-edit trace (the user 2026-08-22): the file viewer saved over a file in this
            # session's tree, and the session is told in the person's voice — never edited under silently
            "edit trace": km._edit_trace_body("/TESTDIR/notes-api/README.md"),
            # the reject trace (plans/file-review.md, Slice 2): the person rejected some of the session's
            # tracked changes in the viewer, which rewrote the file and its sidecar — told in the person's
            # voice like the edit trace, for one change and for several
            "reject trace": km._reject_trace_body("/TESTDIR/notes-api/docs/report.md", 2),
            "reject trace (one change)": km._reject_trace_body("/TESTDIR/notes-api/docs/report.md", 1),
            # the count-less form: the host wrote the file and died before saying which ids landed
            "reject trace (count unknown)": km._reject_trace_body("/TESTDIR/notes-api/docs/report.md", None),
            # the save trace (plans/file-review.md, Slice 5; the review round, 2026-09-06): the editor's
            # Save wrote the file AND its decisions rejected some of the session's tracked changes, so the
            # session hears the direct edit and the count in one body — told as the edit trace alone it
            # read as an overwrite. A save that rejected nothing sends the edit trace above. The same
            # voice, tail and neutralized path as its two siblings, rendered for several and for one
            "save trace": km._save_trace_body("/TESTDIR/notes-api/docs/report.md", 2),
            "save trace (one change)": km._save_trace_body("/TESTDIR/notes-api/docs/report.md", 1),
            # the compaction suggestion (the user 2026-08-30): idle + a lot of context → the person
            # suggests a /compact at a natural boundary; /compact is a CLI feature the session
            # already knows, and the thresholds behind the timing are never mentioned
            "compaction suggestion": km._compact_suggest_body("web"),
            # Send to session (plans/file-review.md): the person's comments on a file, handed to the
            # owning session as one message with the reply commands — the [obsidian-diff] shape the
            # vendored skill handles. The bodies are the person's own words; the frame around them is
            # romp-authored and scanned here. No marker tail, like a todo answer: this IS the person
            # writing. Rendered for one comment on a tracked text file, several on an untracked one,
            # and one on an image, since the second bullet differs.
            # The parenthetical after "Comment <id>" (`desc`) is composed in the webview
            # (file-comments-model.ts describeComment, region-geometry.ts regionDesc) and the kernel
            # prints it verbatim, so the descs below are COPIES of what the client emits, one body per
            # form: a passage, this file, a change with the decision sentence, a region of a standalone
            # image, a region of a figure embedded in a text file (Slice 3, which names the figure by
            # its src), a region of a PDF page (the plan's own specimen), a region with a coordinate
            # the sidecar holds as something other than a number, which prints as "?" in its slot (the
            # UNREADABLE form the source scan below reaches through fmt2), and a passage that RECURS,
            # named by its widened surroundings (the anchors follow-on, 2026-09-07; passageDesc) — with
            # the escapes a context needs, at the widest the sides print whole, and past that bound, where
            # a short clause says only that the text recurs. A copy catches a drift only
            # when the editor propagates it, so the composers' string literals — and those of every
            # helper they reach, such as the "?" a coordinate that is not a number prints as — are
            # scanned at the source as well (test_the_client_composed_desc_speaks_plainly_at_its_source).
            "file comments message": km._file_comments_message(
                "/TESTDIR/notes-api/docs/report.md",
                [{"id": "1781100000000-0", "desc": 'on "shipping the cache in v1.2"',
                  "body": "Which cache? Say which."}], 0, 0, True, True),
            "file comments message (untracked, several)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/report.md",
                [{"id": "1781100000000-0", "desc": 'on "shipping the cache in v1.2"',
                  "body": "Which cache? Say which."},
                 {"id": "1781100000003-0", "desc": "on this file", "body": "Add a summary table at the top."}],
                0, 0, False, True),
            "file comments message (image)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/latency.png",
                [{"id": "1781100000005-0", "desc": "on this file", "body": "The y axis needs units."}],
                0, 0, True, False),
            # the plan's specimen (plans/file-review.md, "The contract"): a change the session made,
            # named by its old and new text, and the accepted/rejected sentence — "change" is the
            # person's word for it (CONTEXT.md), never the storage format's
            "file comments message (decided changes)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/report.md",
                [{"id": "1781100000000-0", "desc": 'on "shipping the cache in v1.2"',
                  "body": "Which cache? Say which."},
                 {"id": "1781100000001-0", "desc": 'on your change "40%" to "35%"',
                  "body": "Keep the measured number."}],
                4, 1, True, True),
            # …and the DECISIONS-ONLY shape (Slice 2): a send carrying an Accept or Reject and no
            # comments wears its own prose (the file, the decisions line, that nothing needs a reply,
            # the same closing ask). A distinct body with its own words, so it is rendered here too —
            # a hand-copied noun list elsewhere would drift from ROMP_WORDS (the review, 2026-09-06)
            "file comments message (decisions only)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/report.md", [], 3, 1, True, True),
            # …and a send carrying a NOTE (the owner's ruling, 2026-09-09): the Send confirm's text box
            # replaced the message preview, and what the person types there is the first paragraph after
            # the header, unlabeled, in both shapes — or the whole middle of the message when nothing else
            # is unsent, where the line saying nothing needs a reply stands down. The note is the person's
            # own words and adds no vocabulary; the frame around it is what the scan reads, rendered here
            # in the note-only shape, the one whose text no other entry carries
            "file comments message (note only)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/report.md", [], 0, 0, True, True,
                note="Two things before the next pass: keep the numbers as measured, and add the run's date."),
            # Slice 3: a region of a standalone image — fractions of its natural size, two decimals —
            # beside a whole-file comment; the image bullet, since the file is not text
            "file comments message (image, region)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/latency.png",
                [{"id": "1781100000005-0", "desc": "on this file", "body": "Which run is this?"},
                 {"id": "1781100000006-0", "desc": "on the region at 0.50, 0.50, 0.25, 0.25",
                  "body": "This spike."}],
                0, 0, False, False),
            # Slice 3: a region of a figure embedded in a markdown file — the desc names the figure by
            # its src as the embed writes it, and the file is text, so the text bullets stay
            "file comments message (embedded figure)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/figures.md",
                [{"id": "1781100000007-0",
                  "desc": "on the region at 0.12, 0.40, 0.35, 0.20 of figs/latency.png",
                  "body": "Label the axes."}],
                0, 0, True, True),
            # a region of a PDF page: regionDesc composes the page form today and the plan's specimen
            # carries it (Slice 4 renders the pages)
            "file comments message (pdf page)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/report.pdf",
                [{"id": "1781100000008-0", "desc": "on the region at 0.12, 0.40, 0.35, 0.20 of page 2",
                  "body": "This table is cut off."}],
                0, 0, True, False),
            # a region whose sidecar holds a coordinate that is not a number (a hand edit, a foreign writer
            # of the `target` field): the comment still sends — deriveUnsent picks by author and time, not by
            # shape — and regionDesc prints the slot as UNREADABLE, so this is a message a session can receive
            "file comments message (image, unreadable coordinate)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/latency.png",
                [{"id": "1781100000009-0", "desc": "on the region at 0.10, ?, 0.30, 0.40",
                  "body": "Which run is this spike from?"}],
                0, 0, False, False),
            # the anchors follow-on (2026-09-07): a passage that RECURS is named by its widened
            # surroundings — `on "<quote>", the one after "…" and before "…"`, both sides JSON-quoted
            # (passageDesc) — so the session can build a `--old` that is unique; the quote alone is one the
            # CLI refuses. Rendered as the two copies of one passage: one whose context holds a quotation
            # mark, a tab and a line break (the escapes are what keep the Comment line one line), and one
            # at the file's start with no prefix to name. The descs are the composer's own test's literals.
            "file comments message (recurring passage)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/report.md", RECURRING_COMMENTS, 0, 0, True, True),
            # …the WIDEST whole form: both sides at the bound the composer prints whole (DESC_CTX_MAX), the
            # longest Comment line a send carries, rendered so the scan and a reader see the shape at its largest
            "file comments message (recurring passage, widest)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/report.md", [WIDEST_COMMENT], 0, 0, True, True),
            # …and PAST the bound (the review's round 2, 2026-09-07): an anchor at the host's cap may still tie,
            # so its sides would name a span that sits on every copy — a kilobyte of it — and the desc says
            # instead, in a short clause, that the text recurs (RECURS_CLAUSE); the same line on every copy
            "file comments message (recurring passage, past the bound)": km._file_comments_message(
                "/TESTDIR/notes-api/docs/repeat.md", RECURS_COMMENTS, 0, 0, True, True),
        }
        # every repeat-nudge variant wears the same voice as the first fire (the user 2026-08-11): the
        # rotation exists so a re-ask doesn't read canned, so a variant that broke the voice rule would
        # defeat its own purpose
        for i, v in enumerate(km.AUTO_NUDGE_VARIANTS, 1):
            bodies["auto-nudge variant %d" % i] = v
        for i, v in enumerate(km.AUTO_NUDGE_STALLED_VARIANTS, 1):
            bodies["fork nudge variant %d" % i] = v
        return bodies

    def test_no_romp_vocabulary_reaches_the_session(self):
        for name, body in self._bodies().items():
            # THE ONE ALLOWANCE, deliberate and ruling-backed (T212, the user 2026-09-01): a
            # backtick-quoted `romp compact …` COMMAND is practical information the recipient
            # must literally type — an SDK session cannot run /compact, and the session-prompt
            # housekeeping note already gives the name its meaning (the sanctioned precedent).
            # Scoped to the exact command span, never the word: "romp" in PROSE still fails.
            text = re.sub(r"`romp compact[^`]*`", "", prose(body)).lower()
            for word, why in ROMP_WORDS:
                with self.subTest(message=name, word=word):
                    self.assertNotIn(word, text,
                                     "%r speaks romp at the session (%r: %s). Write it as the person "
                                     "it works for asking — see CLAUDE.md, 'Messages we inject into a "
                                     "session'." % (name, word, why))

    def test_the_client_composed_desc_speaks_plainly_at_its_source(self):
        # The file-comments descs in _bodies are COPIES: the parenthetical is composed in the webview
        # (describeComment in file-comments-model.ts, regionDesc in region-geometry.ts) and the kernel
        # prints it verbatim, so a romp noun added to either composer would reach a session while the
        # copies here stayed clean. This reads the string literals of each composer AND of every
        # module-level value its code reaches (_desc_closure) — every fixed phrase a desc can carry —
        # and scans them the way the rendered bodies are scanned. The reach matters: regionDesc prints
        # a coordinate that is not a number as UNREADABLE ("the region at 0.10, ?, 0.30, 0.40"), a
        # constant it gets through fmt2, and describeComment names an embedded figure through decodeSrc
        # and the region through region-geometry's regionDesc, and names a recurring passage by its surroundings
        # or by the short RECURS_CLAUSE through passageDesc (the anchors follow-on, 2026-09-07) — none of them
        # in the composer's own span.
        # Comments in the source are skipped (they are not emitted); a composer that moved or was
        # renamed, a helper import that no longer resolves, or a helper reached through a default
        # import (which the scan does not follow) fails loudly here — re-pin it, do not drop the scan.
        # Each composer's known phrases must be among what was read, and its known helpers among what
        # was reached, so the scan can never pass by reading nothing.
        ui = os.path.join(os.path.dirname(HERE), "ui", "webview")
        composers = (
            ("file-comments-model.ts", "describeComment",
             ("on this file", 'on "', "on your change", "the region at ", ", the one ", "after ", "before ",
              ", which appears more than once"),
             (("region-geometry.ts", "regionDesc"), ("file-comments-model.ts", "decodeSrc"),
              ("file-comments-model.ts", "passageDesc"), ("file-comments-model.ts", "RECURS_CLAUSE"))),
            ("region-geometry.ts", "regionDesc",
             ("the region at ", " of page ", "?"),
             (("region-geometry.ts", "fmt2"), ("region-geometry.ts", "UNREADABLE"))),
        )
        for fname, fn, expect, helpers in composers:
            literals, reached = _desc_closure(os.path.join(ui, fname), fn)
            for helper in helpers:
                self.assertIn(helper, reached,
                              "%s.%s no longer reaches %s.%s — the helper moved, was renamed, or the composer "
                              "stopped using it; re-pin the reach here, do not drop the scan" % ((fname, fn) + helper))
            for phrase in expect:
                self.assertTrue(any(phrase in lit for _, _, lit in literals),
                                "%s.%s no longer carries %r — the scan read the wrong span, or the desc form "
                                "changed; fix the pin AND the copies in _bodies" % (fname, fn, phrase))
            for base, n, lit in literals:
                for word, why in ROMP_WORDS:
                    with self.subTest(composer=fn, source=base + "." + n, literal=lit, word=word):
                        self.assertNotIn(word, lit.lower(),
                                         "%s.%s would print %r into the Send to session message, through %s.%s "
                                         "(%r: %s). The desc reaches the session verbatim — write it as the "
                                         "person would name the spot." % (fname, fn, lit, base, n, word, why))

    @staticmethod
    def _sides(clause):
        """The surroundings a widened desc's clause names — the text after ", the one " — decoded the way a
        session would read them: {"after": prefix, "before": suffix} for the sides present. A side is one
        JSON string; the two are joined with " and "."""
        dec, out, rest = json.JSONDecoder(), {}, clause
        while rest:
            side, rest = rest.split(" ", 1)
            text, end = dec.raw_decode(rest)
            out[side] = text
            rest = rest[end:]
            if rest.startswith(" and "):
                rest = rest[len(" and "):]
        return out

    def test_the_widened_desc_rides_the_comment_line_whole(self):
        # the anchors follow-on (2026-09-07): a passage comment whose anchor the host widened names its copy
        # by its surroundings, or — past the bound the composer prints whole — says that the text recurs, and
        # the kernel prints that desc verbatim on the `Comment <id> (…):` line, so the session reads it exactly
        # as the client composed it. What a reader of the rendered bodies should be able to see, pinned: every
        # form is ONE line — a context's line break rides as the JSON escape, never raw — the body follows on
        # the next line; each quoted side decodes back to the context whole, the text a session puts beside the
        # quote in `track-edit --old`, and never wider than the bound; at the bound the line is the longest a
        # send carries; and past it the short clause stands alone, the same on every copy, carrying none of
        # the surroundings. Before this the widened form was rendered nowhere the voice scan reads; only its
        # fragments were scanned at the source (the review, 2026-09-07).
        bodies = self._bodies()
        whole = [("file comments message (recurring passage)", RECURRING_COMMENTS),
                 ("file comments message (recurring passage, widest)", [WIDEST_COMMENT])]
        short = ("file comments message (recurring passage, past the bound)", RECURS_COMMENTS)
        for name, comments in whole + [short]:
            lines = bodies[name].split("\n")
            self.assertEqual(len([l for l in lines if l.startswith("Comment ")]), len(comments),
                             "%r: one Comment line per comment — no desc broke its line" % name)
            for c in comments:
                with self.subTest(message=name, comment=c["id"]):
                    line = "Comment %s (%s):" % (c["id"], c["desc"])
                    self.assertNotIn("\n", line, "the escapes carry the context's line breaks")
                    self.assertIn(line, lines, "the kernel prints the desc verbatim, whole, on one line")
                    self.assertEqual(lines[lines.index(line) + 1], c["body"], "the body follows its own line")
        for name, comments in whole:
            for c in comments:
                with self.subTest(message=name, comment=c["id"]):
                    m = re.fullmatch(r'on "([^"]+)", the one (.+)', c["desc"])
                    self.assertTrue(m, "the whole form: the quote plain, then the surroundings clause")
                    self.assertEqual(m.group(1), "Ship it.")
                    sides = self._sides(m.group(2))
                    self.assertTrue(sides and set(sides) <= {"after", "before"}, sides)
                    for side, text in sides.items():
                        self.assertTrue(text, "an empty side is not named")
                        self.assertLessEqual(len(text), DESC_CTX_MAX, "a side printed is printed whole, within the bound")
                        self.assertNotEqual(json.dumps(text, ensure_ascii=False), '"%s"' % text,
                                            "each specimen's %s side holds something only an escape can carry" % side)
        widest = self._sides(re.fullmatch(r'on "[^"]+", the one (.+)', WIDEST_COMMENT["desc"]).group(1))
        self.assertEqual({k: len(v) for k, v in widest.items()}, {"after": DESC_CTX_MAX, "before": DESC_CTX_MAX},
                         "the bound's worth on both sides, whole")
        self.assertEqual((widest["after"], widest["before"]), (BOUND_PREFIX, BOUND_SUFFIX))
        self.assertGreater(len(WIDEST_COMMENT["desc"]), 2 * DESC_CTX_MAX, "the longest line a send carries is rendered")
        # past the bound: the plan's form plus the clause, alike on every copy, none of the context, no false "the one"
        self.assertGreater(ANCHOR_CTX_CAP, DESC_CTX_MAX,
                           "an anchor at the host's cap is past the bound, so the cap renders the short form")
        for c in RECURS_COMMENTS:
            self.assertEqual(c["desc"], 'on "the marker phrase"' + RECURS_CLAUSE)
            self.assertNotIn("the one ", c["desc"])
            self.assertLess(len("Comment %s (%s):" % (c["id"], c["desc"])), 160)
        self.assertNotIn("xxxx", bodies[short[0]], "none of the cap-width context reaches the message")

    def test_the_widened_desc_copies_are_the_composers_own_specimens(self):
        # the two RECURRING_COMMENTS descs are copied from the composer's own test (file-comments-model-
        # recurring.test.ts asserts passageDesc produces each), RECURS_CLAUSE from the composer's constant, and
        # _widened_desc, which builds the widest and the short specimens, must produce those same copies and
        # the composer's own bound cases (file-comments-model-cap.test.ts) — so a change to passageDesc's form
        # that the client's tests follow fails here until the copies and the mirror follow too, rather than
        # leaving this index rendering a shape no session receives
        ts = Path(os.path.dirname(HERE), "ui", "webview", "file-comments-model-recurring.test.ts").read_text(encoding="utf-8")
        for c in RECURRING_COMMENTS:
            with self.subTest(comment=c["id"]):
                # the TypeScript literal is single-quoted and doubles each backslash the desc carries
                self.assertIn("'" + c["desc"].replace("\\", "\\\\") + "'", ts,
                              "the copy is no longer the literal the composer's test asserts — re-copy it")
        self.assertIn('export const RECURS_CLAUSE = "%s";' % RECURS_CLAUSE, _MODEL_SRC,
                      "the copy is no longer the composer's constant — re-copy it")
        self.assertEqual(_widened_desc("Ship it.", 'He said "ready", then\ttyped: ',
                                       "\nNo regressions were seen in the nightly run."), RECURRING_COMMENTS[0]["desc"])
        self.assertEqual(_widened_desc("Ship it.", "", "\n\nThe tests pass on every supported platform."),
                         RECURRING_COMMENTS[1]["desc"])
        p, s = "p" * DESC_CTX_MAX, "s" * DESC_CTX_MAX
        self.assertEqual(_widened_desc("Ship it.", p, s), 'on "Ship it.", the one after "%s" and before "%s"' % (p, s),
                         "exactly the bound: whole")
        for over in ((p + "p", s), (p, s + "s"), ("", "s" * ANCHOR_CTX_CAP), ("x" * ANCHOR_CTX_CAP, "y" * ANCHOR_CTX_CAP)):
            self.assertEqual(_widened_desc("Ship it.", *over), 'on "Ship it."' + RECURS_CLAUSE,
                             "one over on either side, or at the cap: the short form, never a side cut short")
        self.assertEqual(_widened_desc("x" * 50, "p" * 30, ""), 'on "%s", the one after "%s"' % ("x" * 40, "p" * 30),
                         "the quote keeps the plan's 40 characters; a side the file left empty is not named")
        self.assertEqual(_widened_desc("q" * 50, p + "p", ""), 'on "%s"' % ("q" * 40) + RECURS_CLAUSE,
                         "…in both forms")

    def test_the_index_renders_both_shapes_of_the_file_comments_message(self):
        # the send message has TWO shapes with different prose (kernel _file_comments_message): the
        # comments shape and the decisions-only shape a send with no comments wears. The index must
        # render both, or one is scanned only by a copied noun list that ROMP_WORDS cannot update —
        # the gap the 2026-09-06 review found. Pinned on the shapes' own tell-tales, not their names.
        bodies = self._bodies()
        decisions = [n for n, b in bodies.items() if "No comments this time" in b]
        comments = [n for n, b in bodies.items() if "\nComment " in b and "To respond:" in b]
        self.assertTrue(decisions, "the decisions-only send is rendered and scanned")
        self.assertTrue(comments, "the comments send is rendered and scanned")
        for name in decisions:
            self.assertNotIn("Comment ", bodies[name], "%r is the decisions-only shape: no comment list" % name)
            self.assertIn("I accepted", bodies[name], "%r carries the decision it exists to report" % name)

    def test_the_command_allowance_is_the_span_not_the_word(self):
        # the T212 allowance must never become a whitelist: bare "romp" in prose, or any other
        # romp command, still speaks romp at the session and still fails the scan
        self.assertIn("romp", re.sub(r"`romp compact[^`]*`", "", "romp says hi").lower())
        self.assertIn("romp", re.sub(r"`romp compact[^`]*`", "", "`romp status`").lower())
        self.assertNotIn("romp", re.sub(r"`romp compact[^`]*`", "",
                                        "run `romp compact web` in your shell").lower())

    def test_the_rename_ping_stays_one_clean_mechanics_line(self):
        # the [romp] prefix is the sanctioned mechanics family (the restart notices' shape); past
        # it, the line must speak plainly — no markers (it joins an EXISTING message and would
        # re-author it), no romp nouns, one line
        import os as _os
        sb = load_source("romp_sdk_backend_voice", _os.path.join(BIN, "romp_sdk_backend.py"))
        line = sb.RENAME_NUDGE % "tests"
        self.assertTrue(line.startswith("[romp] "), "the sanctioned mechanics prefix")
        self.assertNotIn("\n", line, "one line")
        self.assertNotIn("<!--", line, "marker-free — it rides inside an existing message")
        body = line.split("]", 1)[1].lower()
        for word, why in ROMP_WORDS:
            self.assertNotIn(word, body, "the ping speaks plainly past its prefix (%r: %s)" % (word, why))
        self.assertIn("renamed", body)
        self.assertIn("'tests'", body, "…and it names the new name itself")

    def test_the_lost_tasks_notice_asks_for_a_check_in_the_persons_voice(self):
        # the lost-background-tasks notice (task_death_notice) is the same [romp]-prefixed mechanics
        # family; past the prefix it speaks plainly, to "you". Since 2026-09-05 it says the tasks were
        # CUT OFF, never that they died: under the per-session scopes a task's shell can outlive the
        # CLI, so the ask is to check whether each still runs before relaunching it. Since 2026-09-06
        # it names the session once (as "you") and says whose process ended (the one that started the
        # tasks) — the earlier wording said "session" twice in one clause and left "its" dangling.
        import os as _os
        sb = load_source("romp_sdk_backend_voice", _os.path.join(BIN, "romp_sdk_backend.py"))
        for tasks in ([{"desc": "watching the CI run"}],
                      [{"desc": "watching the CI run"}, {"desc": "tailing the deploy log"}, {}]):
            text = sb.task_death_notice(tasks)
            prose = text[text.index("[romp]"):]
            self.assertNotIn("<!--", prose, "markers lead, prose follows")
            self.assertNotIn("\n", prose, "one line")
            body = prose.split("]", 1)[1].lower()
            for word, why in ROMP_WORDS:
                self.assertNotIn(word, body, "the notice speaks plainly past its prefix (%r: %s)" % (word, why))
            self.assertIn("%d background task" % len(tasks), body)
            self.assertIn("cut off when the claude process that started", body)
            self.assertNotIn("session", body, "the recipient is \"you\"; the noun appears in neither clause")
            self.assertNotIn(" its claude process", body, "the antecedent-free wording is gone")
            self.assertIn("will never arrive", body)
            self.assertIn("still running before relaunching", body)
            self.assertNotIn("died", body)
            self.assertIn("watching the ci run", body, "the descriptions name what was lost")
        # singular and plural agree throughout; an empty description is skipped, not printed
        self.assertIn("1 background task you had running was cut off when the claude process that started it "
                      "ended (a restart or crash). Its completion notification will never arrive. Check whether it "
                      "is still running before relaunching it; if it isn't needed, carry on.",
                      sb.task_death_notice([{}]))
        three = sb.task_death_notice([{"desc": "a"}, {"desc": "b"}, {}])
        self.assertIn("3 background tasks you had running were cut off when the claude process that started them "
                      "ended (a restart or crash): a; b. Their completion notifications will never arrive. Check "
                      "whether each is still running before relaunching it; if they aren't needed, carry on.", three)
        # the reconnect cause reads as the parenthesis after "ended", with "it" the process that ended
        self.assertIn("ended (a settings switch or a rewind restarted it): a",
                      sb.task_death_notice([{"desc": "a"}], cause=sb.SdkSession._RECONNECT_CAUSE))

    def test_the_untitled_fallback_names_no_romp_object(self):
        # a node with no text still renders SOMETHING; that placeholder must not smuggle in "goal"
        nodes = _nodes()
        nodes[TOP]["text"] = ""
        for name, body in (("bundle", km._nudge_bundle_body([TOP], nodes, set())),):
            self.assertIn("(untitled)", prose(body), name)
            self.assertNotIn("goal", prose(body).lower(), name)

    def test_the_marker_tail_is_exempt_and_still_explains_itself(self):
        # the tail names romp in its markers ON PURPOSE, and its note describes them WITHOUT naming
        # romp — that split is the point, so the test must not have banned it by accident
        body = km._followup_body(TOP, None, "ship it")
        tail = body[body.index("<!--"):]
        self.assertIn("romp-goal-id", tail, "the judge's marker still rides")
        note = tail.split("romp-note:", 1)[1].split("-->", 1)[0]     # the human-readable sentence
        self.assertIn("external tracking system", note)
        self.assertNotIn("romp", note,
                         "the note DESCRIBES the markers without naming the product — naming it would "
                         "explain nothing to a model that has never heard of it")

    def test_the_index_renders_every_trace_body(self):
        # the trace family — one `_<verb>_trace_body` per verb that changes a file's bytes under a
        # session (edit, reject, save so far) — grows a builder per slice of plans/file-review.md,
        # and the save trace shipped (2026-09-06) with its voice check in its own module only, so this
        # index no longer rendered every injected body: the awaiting backstop's drift again, in
        # miniature. Pin the shape rather than the list: every trace builder the kernel defines is
        # rendered by _bodies(), so the next verb's trace cannot skip the index-wide checks, and every
        # rendered trace wears the ONE shared tail (_TRACE_MARKER_TAIL) that keeps them from drifting
        import inspect
        builders = sorted(n for n in dir(km)
                          if re.fullmatch(r"_[a-z]+_trace_body", n) and callable(getattr(km, n)))
        self.assertLessEqual({"_edit_trace_body", "_reject_trace_body", "_save_trace_body"}, set(builders),
                             "the enumeration finds the three known builders — otherwise the loop is vacuous")
        index = inspect.getsource(InjectedBodiesSpeakAsTheUser._bodies)
        for name in builders:
            with self.subTest(builder=name):
                self.assertTrue("km.%s(" % name in index,          # not assertIn: it would dump the source
                                "%s is a message romp injects into a session, but this index never renders "
                                "it — add a row to _bodies() (and, if it is an FYI, to the four-verdicts "
                                "exemption list) so the index-wide checks reach it" % name)
        traces = {n: b for n, b in self._bodies().items() if n.split(" (")[0].endswith(" trace")}
        self.assertEqual(sorted(traces), ["edit trace", "reject trace", "reject trace (count unknown)", "reject trace (one change)",
                                          "save trace", "save trace (one change)"])
        for name, body in traces.items():
            with self.subTest(message=name):
                self.assertTrue(body.endswith(km._TRACE_MARKER_TAIL), "%r wears the shared trace tail" % name)
                self.assertEqual(body.count("<!--"), 2, "%r carries the tail's two markers and no other" % name)

    def test_the_asks_still_elicit_the_planners_four_verdicts(self):
        # the rule is about VOCABULARY, not content: dropping the labeled reply slots must not drop the
        # question. Each nudge still asks for progress, for what is owed by the user, and permits "drop it".
        for name, body in self._bodies().items():
            # the wrap-up is a stop order, not a status ask; a TYPED follow-up carries the user's OWN
            # words as its body, so there is no romp-authored ask in it to check; the DEBT reminder
            # asks for a reply to a PEER, not a progress report to the user; a comment thread's
            # opener is the user's own comment on a quoted passage — a conversation, never a nudge;
            # a user-todo answer is the user's own reply to a need the agent flagged — same class;
            # the user-todo context block is the agent's OWN notes handed back after context loss —
            # a memory aid with a withdraw invitation, not a status ask
            # …and the edit trace is an FYI about something the user already DID (a file changed under
            # the session) — telling, not asking; a status question bolted on would be noise; the reject
            # trace is the same class (the person rejected the session's changes and the file changed),
            # and the save trace is both at once (the person edited the file AND rejected some changes)
            # …and the MERGE handoff is a record handed over with direction ("account for it"),
            # never a status ask — bolting a progress question onto it would be noise
            # …and the file-comments message is the person's own comments with instructions on how
            # to answer them — its ask is "address these and ask me for another look", not a status
            # …and the user-todo file warning is a tool reply's clause about a path that did not resolve —
            # it tells the agent what to pass next time, and asks for nothing
            if (name.startswith("file comments message")       # every form of the Send to session message
                    or name in ("typed follow-up on a summary",
                                "debt reminder (question)", "debt reminder (handoff)",
                                "debt reminder (several)", "comment thread opener", "user-todo answer",
                                "user-todo context block", "user-todo file warning", "edit trace", "reject trace",
                                "reject trace (one change)", "reject trace (count unknown)",
                                "save trace", "save trace (one change)",
                                "comment-thread merge", "compaction suggestion")):
                                # ^ a housekeeping suggestion, not a progress ask — it elicits nothing
                continue
            text = prose(body).lower()
            with self.subTest(message=name):
                self.assertTrue("stand" in text or "what's next" in text or "keep going" in text,
                                "%r no longer asks for progress" % name)
                self.assertIn("from me", text, "%r no longer asks what it needs from the user" % name)


class TheDescSourceScanReadsWhatTheComposerReaches(unittest.TestCase):
    """The source scan behind test_the_client_composed_desc_speaks_plainly_at_its_source, proven on SYNTHETIC
    modules (invented names in a temporary directory): a romp noun in a constant the composer reaches only
    through a helper — in its own module, through a named or aliased import, through a namespace import, or
    inside a template literal's `${…}` — is caught; what is not emitted (a comment, a type, a value the
    composer never references, the code inside `${…}`) is not scanned; and a helper that cannot be found, or
    is reached through a default import the scan does not follow, fails loudly. The first cut scanned the
    composer's span alone and let UNREADABLE through (review finding, 2026-09-06); this pins the reach so it
    cannot narrow back."""

    WORDS = '''// A coordinate that is not a number prints as SLOT. (This comment says card; comments are not emitted.)
export const SLOT = "?";
export const UNUSED = "card";     // no composer reaches this: its word must not be flagged
export type Slot = string;
export const fmt = (v: unknown): string => (typeof v === "number" ? v.toFixed(2) : SLOT);
export function tail(n: number): string {
  return " of page " + n;
}
'''
    COMPOSER = '''import { fmt as two, Slot, tail } from "./desc-words";
import * as words from "./desc-words";
const AT = "the region at ";
function join(parts: string[]): string {
  return parts.join(", ");
}
export function compose(r: Record<string, unknown>, page?: number): string {
  const at: Slot = AT + join(["x", "y"].map((k) => two(r[k])));
  return page ? `${at}${tail(page)}` : at + words.fmt(r.w);
}
'''

    def _modules(self, words=None, composer=None):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        Path(d.name, "desc-words.ts").write_text(words or self.WORDS, encoding="utf-8")
        Path(d.name, "desc-composer.ts").write_text(composer or self.COMPOSER, encoding="utf-8")
        return os.path.join(d.name, "desc-composer.ts")

    def test_the_scan_reaches_helpers_in_its_module_and_across_imports(self):
        literals, reached = _desc_closure(self._modules(), "compose")
        self.assertEqual(reached, {("desc-composer.ts", "compose"), ("desc-composer.ts", "AT"),
                                   ("desc-composer.ts", "join"), ("desc-words.ts", "fmt"),
                                   ("desc-words.ts", "SLOT"), ("desc-words.ts", "tail")},
                         "the composer's own constants and helpers, the aliased and the plain named import, the "
                         "namespace member, and the constant a helper reaches — nothing unreferenced, no type")
        phrases = {lit for _, _, lit in literals}
        for phrase in ("the region at ", ", ", "x", "y", "?", " of page "):
            self.assertIn(phrase, phrases, "every fixed phrase the desc can carry is read, wherever it is defined")
        self.assertEqual(_romp_hits(literals), [],
                         "the comment's word and the unreferenced constant's word are not emitted, so not scanned")

    def test_a_noun_in_a_constant_reached_through_a_helper_is_caught(self):
        # the gap the first cut had: the composer's own span is clean, the constant it reaches is not
        hits = _romp_hits(_desc_closure(self._modules(words=self.WORDS.replace('SLOT = "?"', 'SLOT = "card"')),
                                        "compose")[0])
        self.assertEqual([(h[0], h[1], h[2], h[3]) for h in hits], [("desc-words.ts", "SLOT", "card", "card")],
                         "a noun placed in the constant the helper prints reaches the session; the scan names "
                         "the module and the definition it came from")

    def test_a_noun_reached_through_each_import_form_is_caught(self):
        # a named import (tail), a namespace member (words.fmt), and the composer's own module
        for label, words, composer in (
                ("named import", self.WORDS.replace('" of page "', '" of board "'), None),
                ("namespace member", self.WORDS.replace('SLOT = "?"', 'SLOT = "goal"'),
                 self.COMPOSER.replace("import { fmt as two, Slot, tail }", "import { Slot, tail }")
                              .replace("two(r[k])", "words.fmt(r[k])")),
                ("own module", None, self.COMPOSER.replace('AT = "the region at "', 'AT = "the card at "'))):
            with self.subTest(form=label):
                hits = _romp_hits(_desc_closure(self._modules(words=words, composer=composer), "compose")[0])
                self.assertEqual(len(hits), 1, "exactly the planted noun, at its source: %r" % (hits,))

    def test_code_inside_a_template_literal_is_followed_but_not_scanned_as_prose(self):
        # `${cardinal(x)}` is code: the identifier is followed to its definition (its literals are read) and
        # the code text itself is not a phrase the session sees
        words = self.WORDS + 'export function cardinal(n: unknown): string {\n  return "no. " + String(n);\n}\n'
        composer = self.COMPOSER.replace("import { fmt as two, Slot, tail }", "import { fmt as two, Slot, tail, cardinal }") \
                                .replace("`${at}${tail(page)}`", "`${at}${cardinal(page)}`")
        literals, reached = _desc_closure(self._modules(words=words, composer=composer), "compose")
        self.assertIn(("desc-words.ts", "cardinal"), reached, "the identifier inside ${…} is followed")
        self.assertIn("no. ", {lit for _, _, lit in literals}, "…and what it prints is read")
        self.assertEqual(_romp_hits(literals), [], "the ${cardinal(page)} code is not a phrase; its name is not a hit")
        self.assertNotIn(("desc-words.ts", "tail"), reached, "a helper the composer stopped using is not read")

    def test_a_helper_that_cannot_be_found_fails_loudly(self):
        # each is a case where a silent skip would let the scan pass by reading nothing
        with self.assertRaisesRegex(AssertionError, "resolves to no file"):
            _desc_closure(self._modules(composer=self.COMPOSER.replace('"./desc-words"', '"./desc-word"')), "compose")
        with self.assertRaisesRegex(AssertionError, "defines no such value"):
            _desc_closure(self._modules(composer=self.COMPOSER.replace("fmt as two", "fmt2 as two")), "compose")
        with self.assertRaisesRegex(AssertionError, "no module-level definition of compose2"):
            _desc_closure(self._modules(), "compose2")
        # a type imported WITHOUT the `type` modifier (Slot above) is legal TypeScript and not a value: the clean
        # modules resolve, so that case did not trip the loud path
        _desc_closure(self._modules(), "compose")

    def test_a_default_import_the_composer_references_fails_loudly_and_its_named_list_is_still_read(self):
        # a default import is not followed (the scan cannot know what the target's `export default` is without
        # reading it, and the webview's one such import is vendored code), so a composer that reaches a helper
        # that way must fail rather than pass with the helper unread — alone, and beside a `{ … }` list whose
        # names are still followed. A default import the composer's code never references costs nothing.
        alone = self.COMPOSER.replace('import * as words from "./desc-words";', 'import words from "./desc-words";')
        with self.assertRaisesRegex(AssertionError, r"references 'words', a default import from '\./desc-words'"):
            _desc_closure(self._modules(composer=alone), "compose")
        beside = self.COMPOSER.replace("import { fmt as two, Slot, tail }", "import engine, { fmt as two, Slot, tail }") \
                              .replace("import * as words", "import * as words2") \
                              .replace("words.fmt(r.w)", "engine.fmt(r.w)")
        with self.assertRaisesRegex(AssertionError, "references 'engine', a default import"):
            _desc_closure(self._modules(composer=beside), "compose")
        unused = self.COMPOSER.replace("import { fmt as two, Slot, tail }", "import engine, { fmt as two, Slot, tail }")
        literals, reached = _desc_closure(self._modules(composer=unused), "compose")
        self.assertIn(("desc-words.ts", "fmt"), reached, "the named list beside an unreferenced default import is read")
        self.assertIn(("desc-words.ts", "tail"), reached)
        self.assertIn("?", {lit for _, _, lit in literals})
        # …and `import type X from` is a type, not a value: never a default import to refuse
        typed = self.COMPOSER.replace('import * as words from "./desc-words";',
                                      'import type Words from "./desc-words";\nimport * as words from "./desc-words";')
        _desc_closure(self._modules(composer=typed), "compose")


class UserTodoToolDescriptionsKeepTheVeil(unittest.TestCase):
    """The two user-todo postal tools (plans/user-todos.md) describe an obligation to the PERSON
    THE AGENT WORKS FOR, so their descriptions ride the same veil as injected bodies: no romp
    machinery named. (The OTHER postal tools name romp on purpose — the bus is visible tooling
    with the product's name on it; these two must not teach the model a tracking system.)"""

    def test_the_descriptions_carry_no_romp_vocabulary(self):
        pm = load_source("romp_postal_voice", os.path.join(BIN, "romp-postal-service"))
        tools = {t["name"]: t for t in pm.MCP_TOOLS}
        for name in ("add_user_todo", "withdraw_user_todo"):
            self.assertIn(name, tools, "the tool exists to be scanned")
            desc = tools[name]["description"]
            self.assertIn("person you work for", desc, "%s speaks as the person the agent works for" % name)
            for word, why in ROMP_WORDS:
                with self.subTest(tool=name, word=word):
                    self.assertNotIn(word, desc.lower(),
                                     "%s's description speaks romp at the session (%r: %s)" % (name, word, why))

    def test_the_result_texts_carry_no_romp_vocabulary(self):
        # The RESULT texts land in the agent's context exactly as the descriptions do — the
        # tool's answer is read verbatim by the same model the veil protects — so the sweep
        # covers them too: every user-todo branch of _mcp_call is rendered (success, each
        # refusal, an unreachable kernel) and scanned. The shared "Not inside a romp session."
        # identity refusal is out of scope on purpose: it is every postal tool's answer, and
        # the bus names romp deliberately (visible tooling); identity is stubbed so no branch
        # here can reach it.
        pm = load_source("romp_postal_voice_results",
                              os.path.join(BIN, "romp-postal-service"))
        saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        canned = {}
        pm._kernel_post = lambda path, body, timeout=4.0: canned.get("res")
        pm._self_identity = lambda: (SID, "api")     # the one resolver every tool call reads (2026-09-06)
        pm._heartbeat = lambda *a, **k: None
        # the per-install switch (2026-09-03) is OFF by default: turn it on for the live branches,
        # then off again for the two refusals a still-connected session hears
        pm.USER_TODOS_SWITCH.parent.mkdir(parents=True, exist_ok=True)
        pm.USER_TODOS_SWITCH.write_text(json.dumps({"enabled": True, "gt": 1}))
        try:
            results = {}
            canned["res"] = {"ok": True, "todoId": "ut-9f2c1a34"}
            results["add: noted"] = pm._mcp_call("add_user_todo", {"text": "Need the port"})[0]
            # the file the need is about (2026-09-07): the kernel's warning for an unresolved path
            # rides the reply behind the tool's own lead-in, which is what is scanned here
            canned["res"] = {"ok": True, "todoId": "ut-9f2c1a34", "warning": "that path did not resolve"}
            results["add: noted, path unresolved"] = pm._mcp_call(
                "add_user_todo", {"text": "Need a look at the report", "file": "docs/report.md"})[0]
            results["add: no text"] = pm._mcp_call("add_user_todo", {"text": "  "})[0]
            # the address the need is about (2026-09-08): a value that is not an http(s) address is refused
            # before any post, and a kernel that echoes no link to a body that sent one is named
            results["add: link refused"] = pm._mcp_call(
                "add_user_todo", {"text": "Need a review of the pull request", "link": "ftp://example.invalid/x"})[0]
            canned["res"] = {"ok": True, "todoId": "ut-9f2c1a34"}
            results["add: noted, link not recorded"] = pm._mcp_call(
                "add_user_todo", {"text": "Need a review of the pull request", "link": "https://example.invalid/pull/1"})[0]
            # the bounds on the line and the detail (the 2026-09-09 review): each refusal names the bound and the
            # length before any post
            results["add: text too long"] = pm._mcp_call("add_user_todo", {"text": "N" * (pm.TODO_TEXT_MAX + 1)})[0]
            results["add: detail too long"] = pm._mcp_call(
                "add_user_todo", {"text": "Need the port", "detail": "d" * (pm.TODO_DETAIL_MAX + 1)})[0]
            # the kernel's own account of a link lost on the way to an older remote kernel rides the reply verbatim
            # behind the tool's lead-in, so it is scanned here too: the sample is the kernel's wording (kernel.py, the
            # /usertodo forward's linkWarning; test_user_todos.py holds the real sentence to this veil as well)
            canned["res"] = {"ok": True, "todoId": "ut-9f2c1a34",
                             "linkWarning": ("the link https://example.invalid/pull/1 was not recorded. The session manager on "
                                             "TESTHOST runs an older version that does not keep a todo's link (an update and a "
                                             "restart there fix that), so the todo stands there without it. If the link "
                                             "matters, withdraw it and file it again with the address in its detail, where it "
                                             "becomes a link too.")}
            results["add: noted, link warning relayed"] = pm._mcp_call(
                "add_user_todo", {"text": "Need a review of the pull request", "link": "https://example.invalid/pull/1"})[0]
            canned["res"] = None                    # unreachable kernel / non-2xx
            results["add: couldn't save"] = pm._mcp_call("add_user_todo", {"text": "Need the port"})[0]
            results["withdraw: unreachable"] = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})[0]
            results["withdraw: no id"] = pm._mcp_call("withdraw_user_todo", {})[0]
            canned["res"] = {"ok": True}
            results["withdraw: withdrawn"] = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})[0]
            canned["res"] = {"ok": False}
            results["withdraw: no open note"] = pm._mcp_call("withdraw_user_todo", {"id": "ut-deadbeef"})[0]
            # the kernel's account (state / at / owner, 2026-09-07) words the ok:false four ways
            for state in ("answered", "dismissed", "withdrawn"):
                canned["res"] = {"ok": False, "state": state, "at": T0, "owner": True}
                results["withdraw: already " + state] = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})[0]
            canned["res"] = {"ok": False, "state": "unknown", "at": None, "owner": False}
            results["withdraw: not yours"] = pm._mcp_call("withdraw_user_todo", {"id": "ut-deadbeef"})[0]
            pm.USER_TODOS_SWITCH.write_text(json.dumps({"enabled": False, "gt": 2}))
            results["add: switch off"] = pm._mcp_call("add_user_todo", {"text": "Need the port"})[0]
            results["withdraw: switch off"] = pm._mcp_call("withdraw_user_todo", {"id": "ut-9f2c1a34"})[0]
        finally:
            pm._kernel_post, pm._self_identity, pm._heartbeat = saved
            pm.USER_TODOS_SWITCH.unlink()
        # the sweep rendered the real branches, not seven copies of one fallback
        self.assertIn("Noted", results["add: noted"])
        self.assertIn("About the file: that path did not resolve", results["add: noted, path unresolved"])
        self.assertIn("Refused: the link ftp://example.invalid/x is not an http or https address", results["add: link refused"])
        self.assertIn("About the link: https://example.invalid/pull/1 was not recorded", results["add: noted, link not recorded"])
        self.assertIn("Too long: the line takes at most %d characters" % pm.TODO_TEXT_MAX, results["add: text too long"])
        self.assertIn("Too long: 'detail' takes at most %d characters" % pm.TODO_DETAIL_MAX, results["add: detail too long"])
        self.assertIn("About the link: the link https://example.invalid/pull/1 was not recorded. The session manager on TESTHOST",
                      results["add: noted, link warning relayed"])
        self.assertIn("Withdrawn", results["withdraw: withdrawn"])
        self.assertIn("Nothing changed", results["withdraw: no open note"])
        self.assertIn("Already closed", results["withdraw: already answered"])
        self.assertIn("Already closed", results["withdraw: already dismissed"])
        self.assertIn("Already withdrawn", results["withdraw: already withdrawn"])
        self.assertIn("of yours", results["withdraw: not yours"])
        self.assertIn("turned off on this machine", results["add: switch off"])
        self.assertIn("turned off on this machine", results["withdraw: switch off"])
        for name, text in results.items():
            for word, why in ROMP_WORDS:
                with self.subTest(result=name, word=word):
                    self.assertNotIn(word, text.lower(),
                                     "%s's result speaks romp at the session (%r: %s)" % (name, word, why))


class PinnedNoteToolDescriptionsKeepTheVeil(unittest.TestCase):
    """The two pinned-note postal tools (the user 2026-09-08) speak to the PERSON THE AGENT WORKS FOR
    the way the user-todo pair does, so their descriptions and result texts ride the same veil: no romp
    machinery named. Every branch of _mcp_call is rendered from stubs and scanned."""

    NOTES = [{"id": "pn-9f2c1a34", "text": "Waiting on CI for the login fix", "createdT": T0},
             {"id": "pn-0badcafe", "text": "Read docs/plan.md before replying", "createdT": T0 + 60}]

    def test_the_descriptions_carry_no_romp_vocabulary(self):
        pm = load_source("romp_postal_voice_pn", os.path.join(BIN, "romp-postal-service"))
        tools = {t["name"]: t for t in pm.MCP_TOOLS}
        for name in ("pin_note", "unpin_note"):
            self.assertIn(name, tools, "the tool exists to be scanned")
            desc = tools[name]["description"]
            self.assertIn("person you work for", desc, "%s speaks as the person the agent works for" % name)
            for word, why in ROMP_WORDS:
                with self.subTest(tool=name, word=word):
                    self.assertNotIn(word, desc.lower(),
                                     "%s's description speaks romp at the session (%r: %s)" % (name, word, why))
            for prop in tools[name]["inputSchema"]["properties"].values():
                for word, why in ROMP_WORDS:
                    with self.subTest(tool=name, word=word, prop=prop["description"][:30]):
                        self.assertNotIn(word, prop["description"].lower())

    def test_the_result_texts_carry_no_romp_vocabulary(self):
        pm = load_source("romp_postal_voice_pn_results", os.path.join(BIN, "romp-postal-service"))
        saved = (pm._kernel_post, pm._self_identity, pm._heartbeat)
        canned = {}
        pm._kernel_post = lambda path, body, timeout=4.0: canned.get("res")
        pm._self_identity = lambda: (SID, "api")
        pm._heartbeat = lambda *a, **k: None
        try:
            results = {}
            canned["res"] = {"ok": True, "noteId": "pn-0badcafe", "notes": self.NOTES}
            results["pin: pinned"] = pm._mcp_call("pin_note", {"text": "Read docs/plan.md before replying"})[0]
            results["pin: no text"] = pm._mcp_call("pin_note", {"text": "  "})[0]
            results["pin: too long"] = pm._mcp_call("pin_note", {"text": "x" * 301})[0]
            results["pin: detail too long"] = pm._mcp_call("pin_note", {"text": "x", "detail": "y" * 4001})[0]
            canned["res"] = {"ok": True, "noteId": "pn-0badcafe", "notes": self.NOTES,
                             "dropped": [{"id": "pn-00000000", "text": "the first note"}]}
            results["pin: made room"] = pm._mcp_call("pin_note", {"text": "the ninth"})[0]
            canned["res"] = None                    # unreachable kernel / non-2xx
            results["pin: couldn't pin"] = pm._mcp_call("pin_note", {"text": "Waiting on CI"})[0]
            results["pin: not a string"] = pm._mcp_call("pin_note", {"text": ["a"]})[0]
            canned["res"] = {"ok": False, "state": "unreadable", "notes": [], "error": "the pinned-notes store (x) is not readable; nothing changed"}
            results["pin: unreadable"] = pm._mcp_call("pin_note", {"text": "Waiting on CI"})[0]
            results["unpin: unreachable"] = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})[0]
            results["unpin: no id"] = pm._mcp_call("unpin_note", {})[0]
            canned["res"] = {"ok": True, "state": "unpinned", "notes": []}
            results["unpin: unpinned"] = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})[0]
            canned["res"] = {"ok": False, "state": "unknown", "error": "no pinned note of yours with that id", "notes": self.NOTES[:1]}
            results["unpin: nothing changed"] = pm._mcp_call("unpin_note", {"id": "pn-deadbeef"})[0]
            canned["res"] = {"ok": False, "state": "already", "at": T0, "dropped": False, "error": "already unpinned", "notes": []}
            results["unpin: already"] = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})[0]
            canned["res"] = {"ok": False, "state": "already", "at": T0, "dropped": True, "error": "already unpinned", "notes": []}
            results["unpin: already, dropped"] = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})[0]
            canned["res"] = {"ok": False, "state": "unreadable", "notes": [], "error": "the pinned-notes store (x) is not readable; nothing changed"}
            results["unpin: unreadable"] = pm._mcp_call("unpin_note", {"id": "pn-9f2c1a34"})[0]
            canned["res"] = {"ok": False, "error": "no pinned note of yours with that id", "notes": []}
            results["unpin: older kernel"] = pm._mcp_call("unpin_note", {"id": "pn-deadbeef"})[0]
        finally:
            pm._kernel_post, pm._self_identity, pm._heartbeat = saved
        self.assertIn("Pinned (id pn-0badcafe)", results["pin: pinned"])
        self.assertIn("Unpinned", results["unpin: unpinned"])
        self.assertIn("Nothing changed", results["unpin: nothing changed"])
        self.assertIn("Already unpinned", results["unpin: already"])
        self.assertIn("came down", results["pin: made room"])
        self.assertIn("not readable", results["unpin: unreadable"])
        self.assertIn("NOT see it", results["pin: couldn't pin"])
        self.assertIn("not readable", results["pin: unreadable"])
        self.assertIn("Nothing was pinned", results["pin: not a string"])
        for name, text in results.items():
            for word, why in ROMP_WORDS:
                with self.subTest(result=name, word=word):
                    self.assertNotIn(word, text.lower(),
                                     "%s's result speaks romp at the session (%r: %s)" % (name, word, why))


class TheRuleIsWrittenDown(unittest.TestCase):
    def test_claude_md_carries_the_rule_and_its_exceptions(self):
        md = (Path(HERE).parent / "CLAUDE.md").read_text()
        self.assertIn("the agent does not know romp exists", md)
        self.assertIn("No romp nouns in the prose", md)
        self.assertIn("No taxonomy handed over as reply slots", md)
        self.assertIn("tests/test_injected_voice.py", md, "the rule points at its own guardrail")
        # the exceptions are part of the rule: without them someone "fixes" the marker note next
        self.assertIn("SessionStart instruction", md)
        self.assertIn("marker tail", md)
        self.assertIn("housekeeping note", md)


if __name__ == "__main__":
    unittest.main()

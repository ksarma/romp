#!/usr/bin/env python3
"""docs/install.md, docs/reference.md and docs/architecture.md state the kernel's interpreter rule in bin/romp-serve's order.

`pick_python` in bin/romp-serve chooses the Python the kernel runs: `ROMP_PYTHON` when set, else the
interpreter the SDK venv's `pyvenv.cfg` records, else another Python of the venv's version and build, else
the newest `python3.X` found. The venv-first rule replaced newest-first on 2026-09-06 (this fork's PR #272),
and the reference's section "The kernel's Python" was rewritten with it while install.md's section "Which
Python runs the kernel" kept the old rule: `ROMP_PYTHON`, then the newest of `python3.14` through
`python3.10`, plus a warning that installing another interpreter moves the kernel at its next restart, the
failure the venv-first pick exists to prevent, and docs/architecture.md's installer section kept it in one
clause: a venv "built against the newest Python 3.10+ on the machine and rebuilt when that Python changes".
Three docs, two rules, one script (found while porting the fork's PR upstream, 2026-09-10).

The pins are mechanical, on the tokens the script and the docs share for each candidate, not on the prose
around them: a source's order is the order it first names the tokens in, and the three sources must agree.
`ROMP_PYTHON` and `pyvenv.cfg` name the override and the venv's record in the script and in both docs; the
last resort is the script's newest-first loop (`for v in 3.14 ...`) and the word "newest" in the docs, which
neither install.md's nor the reference's section uses for anything else. A doc that drops a candidate, or
names them in another order, reddens here; so does a reorder of the script the docs do not follow.
architecture.md's clause is read from the interpreter sentence of its installer section alone, the sentence
naming `ROMP_PYTHON` or `pyvenv.cfg`, because that section says other things with the word (the installer
checks the clone out at the newest release); the sentence is held to the override and the venv's record, in
that order, and to naming no newest-first rule: it says what the kernel runs, not the last resort. Two more
pins hold install.md's version range to the loop's list, so the range grows with it, and its pointer at the
reference to the anchor of the reference heading it names.

The move procedure (the one paragraph of each section that names both `service.env` and
`bin/romp-sdk-setup`: a numbered list in install.md, prose in the reference) is pinned the same way, on the
tokens its steps share with the scripts: `service.env` first (the file bin/romp-service's unit and
bin/romp-node-launch read into the manager's environment at a manager start; bin/romp-sdk-setup never reads
it), then `bin/romp-sdk-setup`, then the Codex script by the name kernel/codex_backend.py's remedy line gives
it (a codexvenv built for another tag than the kernel runs is refused with "re-run bin/romp-codex-setup";
nothing on the restart path runs it), then "restart the manager" (only a manager start re-reads the file:
`romp refresh` restarts kernels inside the environment the manager started with, bin/romp-manager's
specEnv). The two docs' orders must agree. install.md's list is read item by item, so a paragraph that runs
into the list without a blank line lends it no order of its own (review round 3, which found that a
rebuild-first list would have passed with the section's pin-anyway paragraph joined to it). install.md's
procedure also names the suite command for the new interpreter, `-m pytest`, since the suite imports the
kernel in-process and `python3 -m pytest` would run the interpreter the move is leaving (review round 2,
which found install.md with the steps reversed, a bare "then restart", and no Codex step in either doc), and
a venv route for an interpreter that has no pytest, since a distro or uv-managed Python refuses installs
into itself (review round 3, which found the step pip-installing into the interpreter).

tests/romp-serve.bats executes the picker (which candidate wins in which state) and diffs its three copies
(bin/romp-serve, bin/romp-sdk-setup, bin/romp-codex-setup); this module holds the docs to the script and
does not run it.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)


def _read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
        return f.read()


def _section(doc, heading):
    """The body under the heading line `heading`, at any level, up to the next heading of any level."""
    m = re.search(r"^#{1,6} " + re.escape(heading) + r"[ \t]*\n(.*?)(?=^#{1,6} |\Z)", doc, re.S | re.M)
    assert m, "no section %r" % heading
    return m.group(1)


def _function(script, name):
    """The body of the bash function `name`: from its `name() {` line to the first `}` at column 0."""
    m = re.search(r"^" + re.escape(name) + r"\(\) \{\n(.*?)^\}", script, re.S | re.M)
    assert m, "no function %r" % name
    return m.group(1)


# Each candidate as the token the docs and the script share for it. A source states the order it first
# names the tokens in; a token it never names is left out of its order, so the mismatch reads as the
# missing name.
CANDIDATES = (
    ("ROMP_PYTHON", re.compile(r"ROMP_PYTHON"), re.compile(r"ROMP_PYTHON")),
    ("pyvenv.cfg", re.compile(r"pyvenv\.cfg"), re.compile(r"pyvenv\.cfg")),
    ("newest", re.compile(r"\bnewest\b"), re.compile(r"^\s*for v in 3\.\d+", re.M)),
)

# The tokens that mark the interpreter sentence: the override and the venv's record.
INTERPRETER_TOKENS = re.compile(r"ROMP_PYTHON|pyvenv\.cfg")


def _order(text, source):
    """The candidate names in the order `text` first names them; `source` is "doc" or "script"."""
    firsts = []
    for name, doc_pat, script_pat in CANDIDATES:
        m = (script_pat if source == "script" else doc_pat).search(text)
        if m:
            firsts.append((m.start(), name))
    return tuple(name for _, name in sorted(firsts))


def _interpreter_rule(section):
    """The sentences of `section` that name the override or the venv's record, in order, as one text.

    A sentence ends at a period, question mark or exclamation mark followed by whitespace. The installer
    section of docs/architecture.md describes the whole install, so a pin that read all of it would take any
    "newest" there (the clone checked out at the newest release) as the interpreter rule; the rule is the
    sentence that names the candidates. Empty when no sentence does.
    """
    return " ".join(s for s in re.split(r"(?<=[.!?])\s+", section) if INTERPRETER_TOKENS.search(s))


# The Codex setup script, by the name the kernel's own remedy gives it (kernel/codex_backend.py, the
# codexvenv-built-for-another-tag verdict: "re-run bin/romp-codex-setup ..."). The docs' move procedure must
# name the script the kernel tells an operator to run, whatever it is called.
CODEX_REMEDY = re.search(r're-run\s*"?\s*"?(bin/romp-[a-z-]+)', _read("kernel", "codex_backend.py"))
assert CODEX_REMEDY, "kernel/codex_backend.py names no bin/romp-* script to re-run"

# The move procedure's steps as the tokens the docs share with the scripts, in the order the steps go.
MOVE_STEPS = (
    ("service.env", re.compile(r"service\.env")),
    ("bin/romp-sdk-setup", re.compile(r"bin/romp-sdk-setup")),
    (CODEX_REMEDY.group(1), re.compile(re.escape(CODEX_REMEDY.group(1)))),
    ("restart the manager", re.compile(r"restart the manager", re.I)),   # a list item starts it in capitals
)
MOVE_MARKERS = (MOVE_STEPS[0][1], MOVE_STEPS[1][1])


def _move_block(section, doc):
    """The one paragraph of `section` that names both `service.env` and `bin/romp-sdk-setup`: the move procedure.

    A paragraph is a run of non-blank lines, so install.md's numbered list is one block with its items and
    the reference's prose paragraph is one block. A section with no such block, or two, has no single move
    procedure to hold to the steps, and the failure says which.
    """
    blocks = [b for b in re.split(r"\n[ \t]*\n", section) if b.strip()]
    hits = [b for b in blocks if all(m.search(b) for m in MOVE_MARKERS)]
    assert len(hits) == 1, "%s: %d paragraphs name both service.env and bin/romp-sdk-setup, not one: %r" % (
        doc, len(hits), hits)
    return hits[0]


def _step_order(block):
    """The move steps in the order `block` first names them; a step it never names is left out."""
    firsts = [(m.start(), name) for name, pat in MOVE_STEPS for m in [pat.search(block)] if m]
    return tuple(name for _, name in sorted(firsts))


# A numbered list's item: its first line and the indented lines that continue it.
ITEM = re.compile(r"^\d+\. .*(?:\n[ \t]+.*)*", re.M)


def _steps_text(block):
    """The text the step order is read from: a numbered list's items alone, a prose paragraph whole.

    A paragraph that runs into install.md's list without a blank line is part of the list's block, and read
    whole the block would take that paragraph's `service.env` as the first step, so a rebuild-first list would
    pass whenever the section's pin-anyway paragraph joined it (review round 3). The items are read in the
    list's order and nothing else in the block is; the reference's procedure is prose and is read whole.
    """
    items = ITEM.findall(block)
    return "\n".join(items) if items else block


PICK_PYTHON = _function(_read("bin", "romp-serve"), "pick_python")
INSTALL = _section(_read("docs", "install.md"), "Which Python runs the kernel")
REFERENCE_HEADING = "The kernel's Python"
REFERENCE = _section(_read("docs", "reference.md"), REFERENCE_HEADING)
ARCHITECTURE = _section(_read("docs", "architecture.md"), "What the installer sets up")
DOCS = (("docs/install.md", INSTALL), ("docs/reference.md", REFERENCE))


class TheScriptsOrder(unittest.TestCase):
    def test_the_picker_tries_the_override_then_the_venvs_record_then_newest_first(self):
        # The order the docs are held to is the script's, read from the script, so a reorder there is a
        # docs failure and not a silently agreeing pair of stale sections.
        self.assertEqual(_order(PICK_PYTHON, "script"), ("ROMP_PYTHON", "pyvenv.cfg", "newest"))


class TheDocsFollowTheScript(unittest.TestCase):
    def test_each_doc_names_every_candidate_in_the_scripts_order(self):
        want = _order(PICK_PYTHON, "script")
        for doc, text in DOCS:
            with self.subTest(doc=doc):
                self.assertEqual(_order(text, "doc"), want, doc + " states another rule than bin/romp-serve")

    def test_both_docs_name_the_same_override_and_the_same_first_candidate(self):
        # The override is ROMP_PYTHON and the first candidate after it is the venv's recorded interpreter,
        # in both docs: the pair install.md lost when reference.md alone was rewritten.
        first_two = {doc: _order(text, "doc")[:2] for doc, text in DOCS}
        self.assertEqual(first_two["docs/install.md"], first_two["docs/reference.md"], first_two)
        self.assertEqual(first_two["docs/install.md"], ("ROMP_PYTHON", "pyvenv.cfg"), first_two)

    def test_architecture_md_names_the_override_and_the_venvs_record_and_no_newest_first_rule(self):
        # The installer section of the architecture doc states the rule in one sentence: what the kernel runs
        # (the override, then the venv's recorded interpreter) and not the newest-first last resort, which
        # it used to give as the rule. The pin reads that sentence, not the section around it.
        want = _order(PICK_PYTHON, "script")
        rule = _interpreter_rule(ARCHITECTURE)
        self.assertTrue(rule, "docs/architecture.md's installer section has no sentence naming ROMP_PYTHON "
                              "or pyvenv.cfg: it does not say what the kernel runs")
        self.assertEqual(_order(rule, "doc"), want[:2],
                         "docs/architecture.md names the override and the venv's record, in the script's order, "
                         "and never the newest-first walk as the rule")

    def test_a_newest_outside_the_interpreter_sentence_is_not_read_as_the_rule(self):
        # The installer section says other things with the word: install.md's "checked out at the newest
        # release" is the phrase that would land there. Added to the section as its own sentence, it is in the
        # section's order and out of the rule's; put inside the interpreter sentence, it still reddens the pin.
        want = _order(PICK_PYTHON, "script")
        outside = ARCHITECTURE.rstrip("\n") + "\n\nThe clone is checked out at the newest release.\n"
        self.assertIn("newest", _order(outside, "doc"), "the phrase is in the section")
        self.assertEqual(_order(_interpreter_rule(outside), "doc"), want[:2])
        inside = ARCHITECTURE.replace("`ROMP_PYTHON`", "the newest Python, `ROMP_PYTHON`", 1)
        self.assertNotEqual(inside, ARCHITECTURE, "the section names `ROMP_PYTHON`")
        self.assertEqual(_order(_interpreter_rule(inside), "doc"), ("newest",) + want[:2])

    def test_install_md_names_the_newest_first_walks_ends(self):
        # install.md gives the walk's range; the list in the script grows with each release.
        m = re.search(r"^\s*for v in ((?:3\.\d+ ?)+); do", PICK_PYTHON, re.M)
        self.assertIsNotNone(m, "the newest-first loop lists its versions inline")
        versions = m.group(1).split()
        by_number = lambda v: tuple(int(x) for x in v.split("."))
        self.assertEqual(versions, sorted(versions, key=by_number, reverse=True), "the walk is newest first")
        for end in (versions[0], versions[-1]):
            self.assertIn("`python%s`" % end, INSTALL, "install.md names the walk's " + end)

    def test_install_md_points_at_the_references_section(self):
        # GitHub's anchor for a heading: lowercased, punctuation other than hyphens dropped, spaces to hyphens.
        slug = re.sub(r"[^a-z0-9 -]", "", REFERENCE_HEADING.lower()).replace(" ", "-")
        self.assertIn("](reference.md#%s)" % slug, INSTALL, "install.md links the reference's section")


class TheMoveProcedure(unittest.TestCase):
    def test_each_doc_gives_the_move_pin_first_then_both_venvs_then_the_manager_restart(self):
        # service.env first: the manager reads it for the kernel and the setup script never does, so a
        # rebuild-first order (install.md at the round-1 head) had the two agree only by the operator
        # remembering the second step. Then the SDK venv with the same value, then the Codex venv, which
        # follows the SDK venv's record and is not rebuilt by anything on the restart path, then the
        # manager restart. The reference's order is upstream's; install.md's must be the same one.
        want = tuple(name for name, _ in MOVE_STEPS)
        orders = {}
        for doc, text in DOCS:
            with self.subTest(doc=doc):
                block = _move_block(text, doc)
                orders[doc] = _step_order(_steps_text(block))
                self.assertEqual(orders[doc], want, doc + " gives the move in another order: " + block)
        self.assertEqual(orders.get("docs/install.md"), orders.get("docs/reference.md"), orders)

    def test_a_paragraph_joined_to_install_mds_list_lends_it_no_order(self):
        # install.md's list is one block with any paragraph that runs into it without a blank line. Read
        # whole, a swapped list with the section's pin-anyway paragraph (which names service.env) joined to it
        # gives the right order for the wrong list; read item by item, the swap shows.
        block = _move_block(INSTALL, "docs/install.md")
        items = ITEM.findall(block)
        self.assertGreaterEqual(len(items), 4, "install.md's move procedure is a numbered list")
        self.assertEqual(_steps_text(block), "\n".join(items), "the list's block is its items")
        swapped = block.replace(items[0] + "\n" + items[1], items[1] + "\n" + items[0], 1)
        self.assertNotEqual(swapped, block, "the first two items are adjacent")
        joined = "If romp runs as a service, pin the interpreter anyway, `ROMP_PYTHON=/usr/bin/python3.12` in " \
                 "`~/.config/romp/service.env`.\n" + swapped
        want = tuple(name for name, _ in MOVE_STEPS)
        self.assertEqual(_step_order(joined), want, "read whole, the joined paragraph hides the swap")
        self.assertNotEqual(_step_order(_steps_text(joined)), want, "read by item, the swap shows")
        self.assertEqual(_step_order(_steps_text(joined))[0], want[1], "the swapped list starts at the rebuild")

    def test_each_docs_move_procedure_names_the_codex_script_the_kernel_names(self):
        # The kernel refuses Codex sessions on a codexvenv built for another tag than it runs and names the
        # remedy; the move procedure must name that script as a step, before the restart, since nothing on
        # the restart path runs it. The reference's paragraph used to name it only in a closing sentence
        # after the restart, as a description of what the venv follows, not as something to run.
        restart = MOVE_STEPS[-1][1]
        for doc, text in DOCS:
            with self.subTest(doc=doc):
                block = _move_block(text, doc)
                m = restart.search(block)
                self.assertIn(CODEX_REMEDY.group(1), block[:m.start()] if m else block,
                              doc + " moves the kernel without re-running the Codex setup before the restart")

    def test_each_docs_move_procedure_restarts_the_manager_not_just_romp(self):
        # Only a manager start re-reads service.env (bin/romp-service's EnvironmentFile=, bin/romp-node-launch);
        # `romp refresh` restarts the kernels inside the manager's start-time environment, so a bare "then
        # restart" leaves a pinned service machine on the old interpreter with a venv rebuilt for the new one.
        for doc, text in DOCS:
            with self.subTest(doc=doc):
                self.assertRegex(_move_block(text, doc), MOVE_STEPS[-1][1], doc + " says only to restart")

    def test_install_md_gives_the_suite_command_for_the_new_interpreter(self):
        # The suite imports the kernel in-process, so the interpreter under pytest is the one exercised; the
        # only other documented recipe, `python3 -m pytest -q`, runs the interpreter the move is leaving. An
        # interpreter without pytest gets a venv built on it and the suite run from there: a distro Python
        # ships no pip module and refuses installs into itself (PEP 668), a uv-managed one refuses the same
        # way, so `<path> -m pip install pytest`, the round-2 text, failed on the doc's own example pin
        # (review round 3).
        steps = _steps_text(_move_block(INSTALL, "docs/install.md"))
        self.assertIn("-m pytest", steps,
                      "install.md's move says to run the suite without saying how, on which interpreter")
        for token in ("-m venv", "/bin/pip install pytest", "/bin/python -m pytest"):
            self.assertIn(token, steps, "install.md's move has no venv route for an interpreter without pytest")
        self.assertNotRegex(steps, r"<path> -m pip install",
                            "install.md's move pip-installs into the interpreter itself, which PEP 668 refuses")


if __name__ == "__main__":
    unittest.main()

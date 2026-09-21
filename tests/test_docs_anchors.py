#!/usr/bin/env python3
"""Every in-page link in the repository's markdown resolves to a heading of its own file (round 10 of fork PR #778, correctness-1),
and the slugger that decides it agrees with the renderer over every heading of the documentation (round 12, tests-2, extra8-1, extra8-2).

docs/reference.md's paragraph on the unit rewrite's identity refusal linked `#two-instances-on-one-machine`, an anchor no heading
in the repository produces, so the one pointer that sentence gave the reader was dead, and it stayed green through nine review
rounds because nothing read the anchors (CI renders no markdown). This module slugs every heading as GitHub does: the heading's
inline markdown rendered to its text (a code span's text without the ticks, a link's text, nothing for an image, a tag dropped,
an entity decoded, a backslash escape's character, and an emphasis delimiter, `*` or `_`, dropped only where CommonMark's
left- and right-flanking rules and its process-emphasis pairing make it one, an intraword underscore run never being one and
an unpaired run staying literal), then lowercased, everything but letters, digits, underscores, hyphens and spaces removed,
spaces to hyphens, a repeated slug numbered -1, -2, ...; it takes an explicit `<a id=...>` or `<a name=...>` as a target too,
skips fenced code on both sides, and resolves every `](#...)` reference in a file against that file's targets. The population
is the documentation a reader is sent to: every tracked markdown file under docs/, at the top level, and bin/README.md and
tests/README.md. Outside it, read once when this pin was written (2026-09-20) and left to their owners:
ui/webview/anchor-map-fixtures/obsidian.md carries two deliberately odd anchors (a fixture of the viewer's anchor map),
plans/file-review.md one to `#results` and the ledger entry upstream/2026-09-07-markdown-viewer-sanitizer.md one to `#top`,
none a document this pin guards.

The slugger is checked against the renderer by DERIVATION, not by a hand list (round 12 of fork PR #778): corpus_headings()
is every ATX heading of that population and of every tracked markdown file under plans/, battery() is every shape a small
grammar of emphasis runs generates (both delimiters, one to three on each side, seven contents, three surroundings) plus
the pairing and flanking shapes CommonMark's own examples name, and tests/fixtures/docs_anchor_slugs.json holds, for each,
the slug the renderer gives it: marked 12.0.2, the extension's, run by tests/docs-anchors-oracle.py, which renders the
heading, takes the h element's text content as GitHub's anchor filter does (the tags gone, then every character reference
decoded by html.unescape, the whole HTML5 named set as cmark-gfm decodes it; the first table's node program knew five names,
amp, lt, gt, quot and apos, and left any other's name in the slug, so the battery carries a `&copy;` and a `&nbsp;` since
the third round-12 fix-up) and slugs it by github-slugger's rule. The test below fails on a heading with no row, a row with
no heading, and any disagreement, naming each; CI's Python job has no node and no marked (the extension job alone installs
vscode-extension/node_modules), so the table is the oracle there, and the recipe refuses to run without them rather than
skipping; CI's extension job, which has both, runs its --check whether or not the test steps before it passed (a pin below
reads the step and its condition). Round 11 checked seventeen headings somebody chose and an underscore arm that stripped
unbalanced runs CommonMark leaves literal, admitted one intraword underscore inside a span and read no whitespace flanking;
over the derived corpus that arm agreed on every real heading (none carries such a shape, at the round-12 commit and at the
third fix-up's head) and disagreed on 123 of the battery's 457 shapes at the round-12 commit: 110 carrying an underscore,
10 an asterisk run with whitespace, or an end of the text, on both sides and 3 neither (a kbd tag, an ampersand entity, lt and
gt entities beside a numeric one), a class the round-12 sentence did not name, that arm dropping no tag and decoding no entity; the third fix-up's
two entity shapes fall in that class, 125 of 459, and RoundEleven below recomputes the split from the table and the round-11
slugger, kept here for it (the round-12 sentence had 111 and 12, remembered, not derived). The slugger below disagreed on
none of the 987 rows at the round-12 commit, before the merge of main, and on none of the 991 at the third fix-up (the
table's corpus field names the counts at this head). What GitHub does that the oracle does not: it renders with cmark-gfm,
which agrees with marked on everything the corpus and the battery hold; it replaces an emoji shortcode (`:name:`) before
it slugs, so one contributes nothing where this module keeps the name (no heading here carries one); and it prefixes the
id with user-content- and resolves the bare anchor by script, which the link never sees. Letters and digits here are
Python's \\w, so a combining mark, which github-slugger keeps, would be dropped; no heading carries one, and the table
would show it."""
import html
import itertools
import json
import os
import re
import subprocess
import unicodedata
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
TABLE = os.path.join(HERE, "fixtures", "docs_anchor_slugs.json")
REGENERATE = "python3 tests/docs-anchors-oracle.py"

_FENCE = re.compile(r"^\s*(```|~~~)")
_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_HTML_ANCHOR = re.compile(r"""<a\s+(?:id|name)=["']([^"']+)["']""")
_IN_PAGE = re.compile(r"\]\(#([^)\s]+)\)")
_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")                              # an image contributes nothing
_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")                              # a link: its text
_AUTOLINK = re.compile(r"<([A-Za-z][A-Za-z0-9+.-]{1,31}:[^\s<>]*)>")      # <scheme:...>: its text
_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s[^<>]*)?/?>")            # an inline tag: nothing (its text stays)
_KEEP = re.compile(r"[^\w\- ]", re.UNICODE)
_ASCII_PUNCT = set("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")


def _space(ch):
    """CommonMark's Unicode whitespace; the ends of the text ("") count as whitespace for flanking."""
    return ch == "" or ch in "\t\n\x0c\r" or unicodedata.category(ch) == "Zs"


def _punct(ch):
    """CommonMark's Unicode punctuation: the ASCII set and every P and S category."""
    return ch != "" and (ch in _ASCII_PUNCT or unicodedata.category(ch)[0] in "PS")


def _delimiter(ch, before, after):
    """(can open, can close) for a run of `ch` between `before` and `after` (CommonMark 0.31, section 6.2): left-flanking is
    not followed by whitespace and either not followed by punctuation or preceded by whitespace or punctuation, right-flanking
    the mirror; `*` opens where left-flanking and closes where right-flanking; `_` opens only where left-flanking and not
    right-flanking (or preceded by punctuation) and closes only where right-flanking and not left-flanking (or followed by
    punctuation), which is what keeps an intraword underscore run literal."""
    left = not _space(after) and (not _punct(after) or _space(before) or _punct(before))
    right = not _space(before) and (not _punct(before) or _space(after) or _punct(after))
    if ch == "*":
        return left, right
    return left and (not right or _punct(before)), right and (not left or _punct(after))


def _tokens(s):
    """The inline text as CommonMark reads it: text chunks and [char, length, can open, can close] delimiter runs. A code span
    (a backtick run closed by an equal run) is one text chunk, its ticks gone, one space stripped from each end when both are
    there and it is not all spaces; an unclosed run is literal; a backslash before ASCII punctuation escapes it."""
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n and s[i + 1] in _ASCII_PUNCT:
            out.append(s[i + 1])
            i += 2
            continue
        if c == "`":
            j = i
            while j < n and s[j] == "`":
                j += 1
            run = s[i:j]
            m = re.compile(r"(?<!`)" + re.escape(run) + r"(?!`)").search(s, j)
            if m:
                body = s[j:m.start()].replace("\n", " ")
                if len(body) >= 2 and body[0] == " " and body[-1] == " " and body.strip(" "):
                    body = body[1:-1]
                out.append(body)
                i = m.end()
            else:
                out.append(run)
                i = j
            continue
        if c in "*_":
            j = i
            while j < n and s[j] == c:
                j += 1
            can_open, can_close = _delimiter(c, s[i - 1] if i else "", s[j] if j < n else "")
            out.append([c, j - i, can_open, can_close])
            i = j
            continue
        j = i + 1
        while j < n and s[j] not in "\\`*_":
            j += 1
        out.append(s[i:j])
        i = j
    return out


def _emphasis(tokens):
    """CommonMark's process-emphasis over the delimiter runs: a closer takes the nearest earlier opener of its character that
    the rule of three allows (where either run could both open and close, their original lengths must not sum to a multiple
    of three unless both are), two delimiters from each for strong when both hold two or more, else one each; the runs between
    the pair are literal from then on, and every delimiter neither side consumed stays in the text."""
    runs = [t for t in tokens if isinstance(t, list)]
    orig = [t[1] for t in runs]
    dead = set()
    for ci, closer in enumerate(runs):
        while closer[1] and closer[3]:
            found = None
            for oi in range(ci - 1, -1, -1):
                opener = runs[oi]
                if oi in dead or not opener[1] or opener[0] != closer[0] or not opener[2]:
                    continue
                if (opener[3] or closer[2]) and (orig[oi] + orig[ci]) % 3 == 0 and not (orig[oi] % 3 == 0 and orig[ci] % 3 == 0):
                    continue
                found = oi
                break
            if found is None:
                break
            use = 2 if runs[found][1] >= 2 and closer[1] >= 2 else 1
            runs[found][1] -= use
            closer[1] -= use
            dead.update(range(found + 1, ci))
    return "".join(t if isinstance(t, str) else t[0] * t[1] for t in tokens)


def inline_text(heading):
    """The text GitHub's renderer gives a heading's inline markdown, which its anchor is slugged from (the module docstring)."""
    s = _IMAGE.sub("", heading)
    s = _LINK.sub(r"\1", s)
    s = _AUTOLINK.sub(r"\1", s)
    s = _TAG.sub("", s)
    return html.unescape(_emphasis(_tokens(s)))


def slug(heading):
    """GitHub's anchor for a heading's text (github-slugger's rule over the rendered text): the heading trimmed as the block parser
    trims it, its inline markdown rendered to text, lowercased, everything but letters, digits, underscores, hyphens and spaces
    removed, spaces to hyphens. Nothing is trimmed after the rendering: an image at an end leaves its space, and the hyphen."""
    return _KEEP.sub("", inline_text(heading.strip()).lower()).replace(" ", "-")


def _unfenced(text):
    """(line number, line) for every line outside fenced code."""
    fenced, fence = False, None
    for n, line in enumerate(text.split("\n"), 1):
        m = _FENCE.match(line)
        if m:
            if not fenced:
                fenced, fence = True, m.group(1)
            elif m.group(1) == fence:
                fenced, fence = False, None
            continue
        if fenced:
            continue
        yield n, line


def targets_and_links(text):
    """(set of anchors the file defines, [(line, anchor) for each in-page link]), fenced code skipped."""
    seen, anchors, links = {}, set(), []
    for n, line in _unfenced(text):
        h = _HEADING.match(line)
        if h:
            s = slug(h.group(2))
            k = seen.get(s, 0)
            seen[s] = k + 1
            anchors.add(s if k == 0 else "%s-%d" % (s, k))
        for a in _HTML_ANCHOR.findall(line):
            anchors.add(a)
        for a in _IN_PAGE.findall(line):
            links.append((n, a))
    return anchors, links


def _ls_files(*pathspecs):
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "-z", "--"] + list(pathspecs), capture_output=True, check=True).stdout
    return sorted({p.decode() for p in out.split(b"\0") if p})


def tracked_markdown():
    """The tracked markdown files the anchor pin guards (the module docstring names the population and what it leaves out)."""
    return _ls_files(":(glob)docs/**/*.md", ":(glob)*.md", "bin/README.md", "tests/README.md")


def corpus_files():
    """The files whose headings the slugger is checked against the renderer over: the anchor pin's population and every tracked
    markdown file under plans/, the repository's richest headings (round 12 of fork PR #778)."""
    return sorted(set(tracked_markdown()) | set(_ls_files(":(glob)plans/**/*.md")))


def corpus_headings():
    """{heading text: [(file, line), ...]} for every ATX heading outside fenced code in corpus_files(), the text as the heading
    regex reads it (the marks and the closing sequence gone)."""
    out = {}
    for rel in corpus_files():
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            for n, line in _unfenced(f.read()):
                h = _HEADING.match(line)
                if h:
                    out.setdefault(h.group(2), []).append((rel, n))
    return out


# the shapes CommonMark's emphasis section names, beside the generated grid: pairing across a foreign run, the rule of three,
# strong inside em and em inside strong, delimiters beside punctuation, intraword runs of each character, runs alone, escapes,
# code spans holding delimiters, a tag, entities, an autolink, strikethrough, non-Latin text; and, since the third round-12
# fix-up, a named character reference outside the five the first oracle decoded and a no-break space reference, which the
# renderer decodes to a sign and a space its slug then drops
_BATTERY_SHAPES = (
    "*a _b* c_", "_a *b_ c*", "**a *b** c*", "*a **b* c**", "***a** b*", "*a **b*** c", "**a *b*** c", 'a*"foo"*', "*(*foo*)*",
    "_(_foo_)_", "foo-_(bar)_", "_foo_bar_baz_", "*foo*bar", "_foo_bar", "__foo, __bar__, baz__", "*foo**bar**baz*", "***foo** bar*",
    "*foo **bar***", "foo***bar***baz", "foo******bar*********baz", "*foo _bar* baz_", "**foo*bar*baz**", "*[foo*](x.md)",
    "_a `b_ c` d_", "\\_not\\_ emphasis", "\\*lit\\*", "<kbd>Ctrl</kbd>+C", "A &amp; B", "&lt;tag&gt; and &#95;x&#95;",
    "<https://example.com/a_b>", "` a ` and `_a_` and ``co`de``", "~~strike~~ through", "a * b * c", "a ** b ** c", "*a*_b_",
    "_a_*b*", "__init__ and __main__", "*foo*_bar_", "_foo_*bar*", "foo _bar_ baz_", "_foo_ bar_", "a_*b*_c", "**Note:** the _thing_",
    "*Note*: `x_y` and _z_", "5*6*78", "пример _слова_ здесь", "日本語 *テスト* です", "**", "***", "****", "_", "__", "___", "____",
    "* *", "_ _", "*_*", "_*_", "*__*", "_**_", "**_a_**", "__*a*__", "***a***", "___a___", "**a**b", "__a__b", "a**b**", "a__b__",
    "*a **b** c*", "_a __b__ c_", "**bold** and __strong__ and *em* and _em_", "ROMP_STATE_DIR and ROMP_SERVICE_NO_LOAD",
    "x _y_z_ w", "`code_with_underscores` and `*stars*`", "[a _link_ text](x.md) and ![img](y.png)", "a_ _b", "foo_bar_ baz",
    "2*3*4", "2 * 3 * 4", "&copy; sign", "a&nbsp;b")


def battery():
    """Every input of a small grammar of emphasis runs, in a fixed order: for each delimiter character, each pair of run lengths
    one to three, each of seven contents (a word, two words, an intraword single and double run, the other character intraword,
    whitespace on both sides, a run then a space) and each of three surroundings (none, words with spaces, words abutting), then
    the shapes above. Derived, not chosen: a shape the grammar covers is in the table whether or not anyone thought of it."""
    out = []
    for ch in "_*":
        other = "*" if ch == "_" else "_"
        for o, c in itertools.product((1, 2, 3), repeat=2):
            for content in ("word", "two words", "a%sb" % ch, "a%s%sb" % (ch, ch), "a%sb" % other, " spaced ", "x%s y" % ch):
                for pre, post in (("", ""), ("lead ", " tail"), ("lead", "tail")):
                    out.append("%s%s%s%s%s" % (pre, ch * o, content, ch * c, post))
    out.extend(_BATTERY_SHAPES)
    return out


def _table():
    with open(TABLE, encoding="utf-8") as f:
        return json.load(f)


# the round-11 slugger of fork PR #778, its five substitutions and its rule verbatim, kept for RoundEleven below, which recomputes
# the figure the module docstring and the ledger state for it: it read a code span, an image, a link, an asterisk run pair and an
# underscore pair with no word character on either side, and nothing else (no tag, no entity, no flanking, no pairing)
_ROUND11_INLINE = [(re.compile(r"`([^`]*)`"), r"\1"),
                   (re.compile(r"!\[[^\]]*\]\([^)]*\)"), ""),
                   (re.compile(r"\[([^\]]*)\]\([^)]*\)"), r"\1"),
                   (re.compile(r"\*{1,3}([^*]+)\*{1,3}"), r"\1"),
                   (re.compile(r"(?<!\w)_{1,3}([^_](?:[^_]|(?<=[^\W_])_(?=[^\W_]))*)_{1,3}(?!\w)"), r"\1")]
_WS_ASTERISK = re.compile(r"(?:^|\s)\*+(?:\s|$)")


def _round11_slug(heading):
    text = heading
    for pat, rep in _ROUND11_INLINE:
        text = pat.sub(rep, text)
    return _KEEP.sub("", text.strip().lower()).replace(" ", "-")


class InPageAnchors(unittest.TestCase):
    def test_every_in_page_link_in_tracked_markdown_resolves_to_a_heading_of_its_file(self):
        dead, resolved = [], 0
        for rel in tracked_markdown():
            with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
                anchors, links = targets_and_links(f.read())
            for line, a in links:
                if a in anchors:
                    resolved += 1
                else:
                    dead.append("%s:%d: #%s" % (rel, line, a))
        self.assertGreater(resolved, 0, "the scan found no in-page link at all: the population or the pattern is wrong")
        self.assertEqual(dead, [], "an in-page link names an anchor no heading of its file produces (%d resolved):\n%s"
                         % (resolved, "\n".join(dead)))


class AgainstTheRenderer(unittest.TestCase):
    """The slugger against the renderer over the derived population (round 12 of fork PR #778; the module docstring). The table is
    the oracle: tests/docs-anchors-oracle.py wrote it from marked, and the test refuses a heading the table does not cover, a row no
    heading or battery shape owns, and any disagreement, each named with the file and line, the renderer's slug and the slugger's."""

    def test_every_heading_of_the_documentation_and_every_battery_shape_slugs_as_the_renderer_does(self):
        table = _table()
        want = dict(table["rows"])
        self.assertTrue(want, "the table is empty: run %s" % REGENERATE)
        corpus, files, shapes = corpus_headings(), corpus_files(), battery()
        # a derived expectation must fail on empty, and on a population no wider than the hand list it replaces
        self.assertGreater(len(files), len(tracked_markdown()), "plans/ contributed no file: the corpus is the anchor pin's alone")
        self.assertGreater(len(corpus), 17, "the derived corpus (%d headings in %d files) must exceed round 11's seventeen" % (len(corpus), len(files)))
        self.assertGreater(len(shapes), 100, "the battery is not the grammar's")
        missing = ["%s (%s)" % (h, ", ".join("%s:%d" % w for w in corpus[h])) for h in sorted(corpus) if h not in want]
        missing += ["%r (battery)" % b for b in shapes if b not in want]
        self.assertEqual(missing, [], "headings with no row in %s (regenerate it: %s; needs node and vscode-extension/node_modules):\n%s"
                         % (os.path.relpath(TABLE, ROOT), REGENERATE, "\n".join(missing)))
        held = set(shapes)
        stale = sorted(h for h in want if h not in corpus and h not in held)
        self.assertEqual(stale, [], "rows no heading of the corpus and no battery shape owns (regenerate: %s):\n%s" % (REGENERATE, "\n".join(stale)))
        disagree = [(h, want[h], slug(h)) for h in sorted(want) if slug(h) != want[h]]
        self.assertEqual(disagree, [], "the slugger disagrees with the renderer on %d of %d (heading, the renderer's slug, the slugger's):\n%s"
                         % (len(disagree), len(want), "\n".join("  %r: want %r, got %r" % d for d in disagree)))

    def test_the_table_names_the_renderer_the_extension_pins_and_its_own_recipe(self):
        table = _table()
        with open(os.path.join(ROOT, "vscode-extension", "package-lock.json"), encoding="utf-8") as f:
            pinned = json.load(f)["packages"]["node_modules/marked"]["version"]
        self.assertEqual(table["marked"], pinned, "the extension's marked moved (%s, the table's %s): re-run %s" % (pinned, table["marked"], REGENERATE))
        self.assertEqual(table["regenerate"], REGENERATE)

    def test_the_battery_is_the_grammar_and_holds_the_shapes_round_eleven_missed(self):
        shapes = battery()
        self.assertEqual(len(shapes), len(set(shapes)), "a shape is generated twice")
        self.assertEqual(len(shapes), 2 * 9 * 7 * 3 + len(_BATTERY_SHAPES))
        for s in ("__a_b_", "_ spaced _", "lead __word_ tail", "___a__b___", "**a *b** c*"):
            self.assertIn(s, shapes)

    def test_ci_runs_the_recipe_where_node_and_marked_are_installed(self):
        # round 12 fix-up of fork PR #778: on the Python matrix runners the table IS the oracle, so a table edited to agree with a
        # wrong slugger passes the test above there (executed: a slugger stripping every underscore, the table rewritten from it,
        # this class green, the recipe's --check red on 226 rows). The extension job has node and the extension's marked (npm ci),
        # so it runs `docs-anchors-oracle.py --check`; this pin reads that step off the workflow, in that job, after its npm ci
        with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as f:
            text = f.read()
        job = re.search(r"^  vscode-extension:\n(.*?)(?=^  [a-z-]+:$|\Z)", text, re.S | re.M)
        self.assertIsNotNone(job, "ci.yml has no vscode-extension job")
        steps = job.group(1)
        install = steps.find("run: npm ci")
        self.assertGreaterEqual(install, 0, "the extension job runs no npm ci")
        check = re.search(r"^\s+run: python3? tests/docs-anchors-oracle\.py --check\s*$", steps, re.M)
        self.assertIsNotNone(check, "the extension job runs no `python tests/docs-anchors-oracle.py --check` step: in CI the table is never "
                                    "held to the renderer, so a table edited to agree with a wrong slugger passes")
        self.assertGreater(check.start(), install, "the recipe needs the extension's marked: the --check step must follow npm ci")
        # third round-12 fix-up: the step checks a committed table against the renderer, a subject none of the test steps before it
        # (the served-page pytest is the job's long phase and goes red for reasons of its own) bears on, so it runs after a red one
        # too and one run reports both; its condition names only cancellation and the install's outcome (the id below), since
        # without marked the recipe can only say to run npm ci. A text pin over the workflow, the weaker guarantee: nothing here runs
        # Actions, so what it holds is that the step's condition reads no other step's result
        blocks = re.split(r"^      - ", steps, flags=re.M)
        step = [b for b in blocks if "tests/docs-anchors-oracle.py --check" in b]
        deps = [b for b in blocks if "run: npm ci" in b]
        self.assertEqual((len(step), len(deps)), (1, 1), "the --check step and the npm ci step must each be one step of the job")
        cond = re.search(r"^\s+if: (.*?)\s*$", step[0], re.M)
        self.assertIsNotNone(cond, "the --check step has no if: and so is skipped whenever a test step before it fails, though its "
                                   "subject, the committed table against the renderer, is independent of theirs")
        self.assertEqual(cond.group(1), "${{ !cancelled() && steps.deps.outcome == 'success' }}",
                         "the --check step's condition must name only cancellation and the install's outcome, no other step's result")
        self.assertRegex(deps[0], re.compile(r"^\s+id: deps\s*$", re.M), "the npm ci step carries no `id: deps` for the --check step's condition to read")


class RoundEleven(unittest.TestCase):
    """The figure the module docstring and the ledger's round-12 paragraph state for round 11's arm is derived, not remembered (third
    round-12 fix-up of fork PR #778): the round-12 commit wrote the split of its 123 battery disagreements as 111 underscore runs
    and 12 whitespace-flanked asterisk runs, where the derivation over the table gives 110, 10 and 3 with neither, a class the
    sentence did not name (a tag and entities, which that arm neither dropped nor decoded). The classes are predicates over the
    shape's text, in this order: it carries an underscore; else an asterisk run with whitespace or an end on both sides; else
    neither. The battery is the fixed grammar and list above, so the counts move only when it does, and this message says so."""

    def test_the_round_eleven_slugger_disagrees_with_the_table_on_the_derived_split(self):
        want = dict(_table()["rows"])
        shapes = battery()
        self.assertEqual([b for b in shapes if b not in want], [], "a battery shape has no row: regenerate the table (%s)" % REGENERATE)
        disagree = [h for h in shapes if _round11_slug(h) != want[h]]
        underscore = [h for h in disagree if "_" in h]
        asterisk = [h for h in disagree if "_" not in h and _WS_ASTERISK.search(h)]
        neither = [h for h in disagree if "_" not in h and not _WS_ASTERISK.search(h)]
        self.assertGreater(len(disagree), 0, "round 11's arm agrees with the renderer on every battery shape: the slugger kept here is not its")
        self.assertEqual([h for h in neither if "<" not in h and "&" not in h], [],
                         "the third class is what round 11 neither dropped nor decoded, a tag or an entity, and holds something else")
        self.assertEqual((len(disagree), len(underscore), len(asterisk), len(neither)), (125, 110, 10, 5),
                         "the round-11 figure (disagreements over the battery; with an underscore; with a whitespace-flanked asterisk run; "
                         "neither) moved: restate it in this module's docstring and the ledger's round-12 paragraph with its vintage. "
                         "The third class now: %r" % (neither,))


class Slugs(unittest.TestCase):
    def test_slugs_as_github_does(self):
        self.assertEqual(slug("The manager's control port"), "the-managers-control-port")
        self.assertEqual(slug("Per-session billing: login vs API key"), "per-session-billing-login-vs-api-key")
        self.assertEqual(slug("`romp up` and the **bold** [link](x.md)"), "romp-up-and-the-bold-link")
        self.assertEqual(slug("  Spaced   words  "), "spaced---words")
        # underscores: intraword ones are text and stay (GitHub keeps them in the anchor); a pair around a word or a
        # phrase is emphasis and goes, and the pair may hold an intraword underscore of its own (round 11, correctness-1)
        self.assertEqual(slug("The ROMP_STATE_DIR and ROMP_SERVICE_NO_LOAD switches"), "the-romp_state_dir-and-romp_service_no_load-switches")
        self.assertEqual(slug("_real emphasis_ here"), "real-emphasis-here")
        self.assertEqual(slug("x _y_z_ w and __strong__ text"), "x-y_z-w-and-strong-text")
        self.assertEqual(slug("snake_case_name and trailing_ and a_ _b"), "snake_case_name-and-trailing_-and-a_-_b")
        # round 12 (tests-2, extra8-1), each the renderer's answer: an unbalanced run keeps what no closer consumed, a
        # whitespace-flanked run is no delimiter, a span may hold a double intraword run, and a code span's delimiters are text
        self.assertEqual(slug("__a_b_"), "_a_b")
        self.assertEqual(slug("_ spaced _"), "_-spaced-_")
        self.assertEqual(slug("lead __word_ tail"), "lead-_word-tail")
        self.assertEqual(slug("_a__b_"), "a__b")
        self.assertEqual(slug("`_a_` and `*b*`"), "_a_-and-b")
        self.assertEqual(slug("[a _link_ text](x.md) and ![img](y.png)"), "a-link-text-and-")
        # third round-12 fix-up: a named reference outside amp, lt, gt, quot and apos decodes as cmark-gfm decodes it, to a sign
        # the slug drops (the space before the word stays, as a hyphen), and a no-break space reference to a space the slug drops
        self.assertEqual(slug("&copy; sign"), "-sign")
        self.assertEqual(slug("a&nbsp;b"), "ab")

    def test_a_correct_link_to_a_heading_with_two_underscores_resolves(self):
        # round 11 of fork PR #778 (correctness-1): the round-10 stripper read the heading's `_STATE_` and `_SERVICE_` as
        # emphasis and derived `the-rompstatedir-and-rompserviceno_load-switches`, so the link GitHub resolves was reported dead
        text = "## The ROMP_STATE_DIR and ROMP_SERVICE_NO_LOAD switches\n\nsee [x](#the-romp_state_dir-and-romp_service_no_load-switches)\n"
        anchors, links = targets_and_links(text)
        self.assertEqual([(n, a) for n, a in links if a not in anchors], [],
                         "the link GitHub resolves must not be reported dead (anchors: %s)" % sorted(anchors))

    def test_a_dead_link_to_a_heading_with_two_underscores_is_reported(self):
        # the other direction of the same defect: the module's own wrong slug is not an anchor GitHub produces, so a
        # link to it is dead and must be reported, where round 10 passed it
        text = "## The ROMP_STATE_DIR and ROMP_SERVICE_NO_LOAD switches\n\nsee [x](#the-rompstatedir-and-rompserviceno_load-switches)\n"
        anchors, links = targets_and_links(text)
        self.assertEqual([(n, a) for n, a in links if a not in anchors], [(3, "the-rompstatedir-and-rompserviceno_load-switches")],
                         "a dead link must be reported (anchors: %s)" % sorted(anchors))

    def test_a_repeated_heading_is_numbered_and_fenced_code_is_skipped(self):
        text = "# A\n\n```\n# not a heading\n](#nowhere)\n```\n\n# A\n\n<a id=\"hand\"></a>\n\nsee [x](#a) [y](#a-1) [z](#hand)\n"
        anchors, links = targets_and_links(text)
        self.assertEqual(anchors, {"a", "a-1", "hand"})
        self.assertEqual(links, [(12, "a"), (12, "a-1"), (12, "hand")])

    def test_a_dead_anchor_is_named_with_its_line(self):
        anchors, links = targets_and_links("# Ports\n\nsee [x](#two-instances-on-one-machine)\n")
        self.assertEqual([(n, a) for n, a in links if a not in anchors], [(3, "two-instances-on-one-machine")])


if __name__ == "__main__":
    unittest.main()

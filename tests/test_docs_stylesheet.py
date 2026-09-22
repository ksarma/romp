#!/usr/bin/env python3
"""docs/stylesheets/extra.css: every comment closes once, and the Mermaid variable rule its longest
comment explains is a rule a CSS parser keeps (2026-09-22).

The defect this pins (found by the reviewer's CSS rule reader in fork PR #862's round 10, run over
every sheet in the tree; the sheet was not in that PR's diff): the Mermaid-legibility comment closed
with ` */` at the end of its second paragraph, and the five lines of a third paragraph, added on
2026-07-24 to explain why the selector below it is `:root, :root > *` rather than `:root`, followed
that close and ended with a ` */` of their own. To a CSS parser the lines between the two closes are
not a comment: they are consumed, with the `:root, :root > *` after them, as one qualified rule's
prelude; that prelude is not a valid selector list, so the whole rule is dropped, its two
declarations with it (--md-mermaid-label-fg-color and --md-mermaid-label-bg-color, the fix for
near-white node labels on pale Mermaid boxes on the dark scheme). Nothing else in the sheet is lost:
the parser recovers at the rule's closing brace, so the loss was silent.

Two properties, keyed on the sheet's structure and never on a line's spelling:
  1. comment balance over the whole sheet: a `*/` met outside a comment is the defect, and a `/*`
     still open at end of file is its other face; each fault names its line, and a stray close also
     names the line the last comment closed on, since the lines between the two are the prose a
     parser reads as code;
  2. with comments stripped, a rule whose prelude is exactly `:root, :root > *` is present and
     declares both custom properties.
The scanner is a plain `/*` to `*/` state machine: no nesting (CSS has none) and no string state.
Strings are not modelled because this sheet has no quoted string carrying either delimiter (a url()
or a content string could, in general), and a test here asserts that on the comment-stripped text
rather than assuming it. The mechanics are exercised on the smallest inputs that exhibit each
property, then the checks run over the real sheet; the historical defect is replanted on every line
of the real comment in turn and each plant is reported at its own lines, so the pin is known to red
on the population's own shape.

The natural instrument for this is the CSS rule reader fork PR #862 adds, which was not landed when
this was written; this module is the narrower comment-balance check over the docs sheet alone (the
interface's sheets under ui/webview are that reader's population) and is to be folded into the
reader when it lands.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
SHEET = os.path.join(ROOT, "docs", "stylesheets", "extra.css")

MERMAID_PRELUDE = ":root, :root > *"
MERMAID_PROPERTIES = ("--md-mermaid-label-fg-color", "--md-mermaid-label-bg-color")

STRAY_CLOSE = "stray close"
UNCLOSED = "unclosed comment"


def comment_faults(text):
    """Every comment-balance fault in a sheet, as (kind, line, other): a `*/` outside any comment is
    (STRAY_CLOSE, its line, the line the last comment closed on, or None when none had); a `/*` still
    open at end of input is (UNCLOSED, the line it opened on, None). Lines are 1-based."""
    faults = []
    in_comment = False
    open_line = None
    last_close = None
    line = 1
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            line += 1
            i += 1
            continue
        pair = text[i:i + 2]
        if in_comment:
            if pair == "*/":
                in_comment = False
                last_close = line
                i += 2
            else:
                i += 1
            continue
        if pair == "/*":
            in_comment = True
            open_line = line
            i += 2
        elif pair == "*/":
            faults.append((STRAY_CLOSE, line, last_close))
            i += 2
        else:
            i += 1
    if in_comment:
        faults.append((UNCLOSED, open_line, None))
    return faults


def describe(faults):
    out = []
    for kind, line, other in faults:
        if kind == STRAY_CLOSE:
            tail = (" (the last comment closed at line %d; the lines between are code to a parser)" % other
                    if other is not None else "")
            out.append("line %d: '*/' outside any comment%s" % (line, tail))
        else:
            out.append("line %d: '/*' still open at end of file" % line)
    return "\n".join(out)


def strip_comments(text):
    """The sheet without its comments, the way a parser reads it: `/*` to the next `*/`, no nesting; a
    comment still open at the end swallows the rest (comment_faults reports that case)."""
    out = []
    i = 0
    while True:
        start = text.find("/*", i)
        if start < 0:
            out.append(text[i:])
            break
        out.append(text[i:start])
        end = text.find("*/", start + 2)
        if end < 0:
            break
        i = end + 2
    return "".join(out)


def rules(text):
    """[(prelude, body)] for every rule in comment-stripped text, at every nesting level: a prelude is
    the text before a `{` with its whitespace collapsed, a body the text to the matching `}`; a body
    that itself holds rules (an @media block) is walked too, so the list is flat and in source order."""
    out = []
    i = 0
    n = len(text)
    while True:
        brace = text.find("{", i)
        if brace < 0:
            break
        prelude = " ".join(text[i:brace].split())
        depth = 1
        j = brace + 1
        while j < n and depth:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
            j += 1
        body = text[brace + 1:j - 1] if depth == 0 else text[brace + 1:]
        out.append((prelude, body))
        if "{" in body:
            out.extend(rules(body))
        i = j
    return out


def declarations(body):
    """{name: value} for the `name: value;` declarations of a rule body that holds no nested rules."""
    out = {}
    for piece in body.split(";"):
        if ":" not in piece:
            continue
        name, value = piece.split(":", 1)
        out[name.strip()] = value.strip()
    return out


STRING_RE = re.compile(r'"[^"\n]*"|\'[^\'\n]*\'')


def _sheet():
    with open(SHEET, encoding="utf-8") as f:
        return f.read()


class ScannerMechanics(unittest.TestCase):
    """The smallest inputs that exhibit each property, so the checks below are known to be able to fail."""

    def test_a_stray_close_is_reported_at_its_line_with_the_last_close(self):
        sheet = "/* one */\na { color: red; } */\nb { color: blue; }\n"
        self.assertEqual(comment_faults(sheet), [(STRAY_CLOSE, 2, 1)])
        self.assertEqual(describe(comment_faults(sheet)),
                         "line 2: '*/' outside any comment (the last comment closed at line 1; "
                         "the lines between are code to a parser)")

    def test_a_stray_close_before_any_comment_names_no_last_close(self):
        self.assertEqual(comment_faults("a { } */\n"), [(STRAY_CLOSE, 1, None)])
        self.assertEqual(describe(comment_faults("a { } */\n")), "line 1: '*/' outside any comment")

    def test_a_comment_left_open_is_reported_at_the_line_it_opened_on(self):
        self.assertEqual(comment_faults("a { }\n/* open\nb { }\n"), [(UNCLOSED, 2, None)])

    def test_a_balanced_sheet_has_no_faults(self):
        self.assertEqual(comment_faults("/* a\n   b */\nc { d: e; }\n/* f */ g { }\n"), [])

    def test_a_close_inside_a_comment_ends_it_and_the_text_after_is_code(self):
        # the defect's shape in miniature: an early close turns the rest of the comment into a prelude
        sheet = "/* said */ more said */\nx { y: z; }\n"
        self.assertEqual(comment_faults(sheet), [(STRAY_CLOSE, 1, 1)])
        self.assertEqual([p for p, _ in rules(strip_comments(sheet))], ["more said */ x"])

    def test_the_tokenizer_reads_preludes_bodies_and_nested_rules(self):
        sheet = "/* c */ a, b { x: 1; y: 2 }\n@media (min-width: 1px) { c { z: 3; } }\nprose */ d { w: 4 }\n"
        found = rules(strip_comments(sheet))
        self.assertEqual([p for p, _ in found], ["a, b", "@media (min-width: 1px)", "c", "prose */ d"])
        self.assertEqual(declarations(found[0][1]), {"x": "1", "y": "2"})
        self.assertEqual(declarations(found[2][1]), {"z": "3"})

    def test_strip_comments_removes_each_comment_and_keeps_the_code_between(self):
        self.assertEqual(strip_comments("a/* one */b/* two\n*/c"), "abc")
        self.assertEqual(strip_comments("a/* open"), "a")


class DocsStylesheet(unittest.TestCase):
    """The real sheet."""

    def test_every_comment_closes_once(self):
        faults = comment_faults(_sheet())
        self.assertEqual(faults, [], "docs/stylesheets/extra.css: a comment does not balance; a '*/' outside a "
                                     "comment leaves the lines before it as code, and the rule they run into "
                                     "is dropped by the parser with every declaration in it\n%s" % describe(faults))

    def test_no_string_outside_a_comment_carries_a_comment_delimiter(self):
        # the scanner has no string state; this holds while the sheet gives it no reason to
        code = strip_comments(_sheet())
        carriers = [s for s in STRING_RE.findall(code) if "/*" in s or "*/" in s]
        self.assertEqual(carriers, [], "a quoted string carries a comment delimiter; comment_faults would misread "
                                       "it, so teach the scanner strings before relying on it here")

    def test_the_mermaid_variable_rule_is_parsed_with_both_declarations(self):
        found = rules(strip_comments(_sheet()))
        matches = [body for prelude, body in found if prelude == MERMAID_PRELUDE]
        self.assertEqual(len(matches), 1, "one rule with prelude %r; the preludes naming :root are %r" % (
            MERMAID_PRELUDE, [p for p, _ in found if ":root" in p]))
        decls = declarations(matches[0])
        for name in MERMAID_PROPERTIES:
            self.assertIn(name, decls, "the rule declares %s (declared: %r)" % (name, sorted(decls)))
            self.assertTrue(decls[name], "%s has a value" % name)

    def _mermaid_comment_lines(self, lines):
        """(first, last) 1-based line numbers of the comment that precedes the Mermaid variable rule,
        derived from the sheet: the rule's line, the `*/` on the line before it, and the `/*` that opened it."""
        rule = [i for i, ln in enumerate(lines, 1) if ln.startswith(MERMAID_PRELUDE + " {")]
        self.assertEqual(len(rule), 1, "the Mermaid variable rule opens on one line of its own")
        last = rule[0] - 1
        self.assertTrue(lines[last - 1].rstrip().endswith("*/"), "the line before the rule closes its comment")
        first = last
        while "/*" not in lines[first - 1]:
            first -= 1
            self.assertGreater(first, 0, "the comment before the rule has an opener")
        return first, last

    def test_the_historical_defect_replanted_on_any_line_of_the_comment_is_reported(self):
        """A ` */` appended to any line of the real comment, first to last, closes it there and turns the
        rest into code; the scanner reports the comment's own close as the stray one and names the plant
        line as the last close, so the failure points a reader at both ends of the run of prose."""
        text = _sheet()
        self.assertEqual(comment_faults(text), [], "the plants below start from a balanced sheet")
        lines = text.splitlines(keepends=True)
        first, last = self._mermaid_comment_lines(lines)
        self.assertGreater(last - first, 5, "the comment runs several lines: %d to %d" % (first, last))
        for plant in range(first, last + 1):
            planted = list(lines)
            planted[plant - 1] = planted[plant - 1].rstrip("\n") + " */\n"
            faults = comment_faults("".join(planted))
            self.assertEqual(faults, [(STRAY_CLOSE, last, plant)],
                             "planted on line %d: the close on line %d is the stray one and the plant is the last close" % (plant, last))
            preludes = [p for p, _ in rules(strip_comments("".join(planted)))]
            self.assertNotIn(MERMAID_PRELUDE, preludes,
                             "planted on line %d: the parser no longer sees the variable rule's prelude" % plant)


if __name__ == "__main__":
    unittest.main()

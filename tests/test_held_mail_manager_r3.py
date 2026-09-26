#!/usr/bin/env python3
"""The held-mail readers bundle, the manager's round 3 on the fork PR: the kernel-side pins that fit no earlier class. One
class today, the viewing panel's rendering of the PARTIAL marker (correctness-2, ruled up in emphasis): a holder whose bus
read some of its held records and could not read the rest used to gossip the rows of the records it read and nothing of
the rest, so a record left unread beside served ones was reported absent on every viewing machine, under a 200 and in the
summary rows, the round 2 defect surviving in the mixed case. The bus's summary appends one marker row after the message
rows now, in the fault row's key shape with `fault` (the count wording), `unread` (the count left unread) and `served` (the
count read), and the kernel's served panel (the Held for approval elsewhere block of _LANDING_REMOTES_JS) renders such a
row as a partial listing: the host's count line stands over its message rows, the marker is one line under it in the fault
line's dress with the fault text as its text and a hover saying the counted messages stand, the unread are not counted
here and the read is retried on the next refresh, one line per distinct marker text per host, never counted as a message,
nothing of the row but its fault text rendered; a `fault` row with no `unread` renders as the whole store refused, as
before. Each case fails over a git archive of the reviewed head f418f75e9, whose panel knows no `unread` and renders the
marker row as a whole-store fault line (its text prefixed `held mail could not be read: `, its hover saying whatever is
held there is not counted), at the assertion its docstring names.

The harness is the round 1 module's (tests/test_held_mail_reader_guards.py: its hermetic root, its private synthetic
sid), imported the way tests/test_held_mail_manager_r1b.py imports it, and its import is the state preamble (that module
makes its root hermetic before it loads the kernel); the panel stub and the row builders are the round 1 manager module's
(tests/test_held_mail_manager_r1.py), imported rather than copied. The real panel JS runs in node against the stub, the
idiom of tests/test_remotes_panel_render.py; no state root is touched by the cases. Synthetic only: TESTHOST and
invented host names, placeholder texts; every root the harness mints writes `off` into <root>/session-hosts (repo rule,
2026-09-11) and no goals are minted."""
import json
import subprocess
import unittest

from tests.test_held_mail_reader_guards import km   # noqa: E402  (the harness: the state preamble runs on this import)
from tests.test_held_mail_manager_r1 import PANEL_STUB, PANEL_TUNNELS, _hold_row, _fault_row, FAULT_TEXT, HOLD_GIST   # noqa: E402

MARKER_TEXT = "held mail: 1 of its 3 records cannot be read (errno 13: Permission denied); the rest is served"   # the bus's count wording
WHOLE_STORE_PREFIX = "held mail could not be read: "                    # the whole-store fault line's dress (round 1's contract)
WHOLE_STORE_HOVER = "could not read its own held-mail store"          # the whole-store fault line's hover, false of a marker


def _marker_row(at_host, fault=MARKER_TEXT, unread=1, served=2, **extra):
    """The contract's partial marker as the viewing kernel receives it: the fault row's key shape (_fault_row) with `fault`
    carrying the count wording and `unread` and `served` the counts beside it. `extra` plants markers in the other keys."""
    return _fault_row(at_host, fault=fault, unread=unread, served=served, **extra)


class APartialMarkerRowReachesTheViewingPanel(unittest.TestCase):
    """correctness-2, the kernel half (the manager's round 3 on the held-mail readers PR). The contract: a row carrying a
    numeric `unread` beside `fault` is the partial marker; the host's count line stands over the rows that are messages
    (the unread never counted), the marker renders as its own line under the host with the `fault` text as its text and a
    hover saying the counted messages stand, the unread ones are not counted here and the read is retried on the next
    refresh, one line per distinct marker text per host; a `fault` row with no `unread` renders as today, the whole
    store refused. Nothing of a marker row but its fault text is rendered, and a fault that is not text is named by its
    type. Fails before over the f418f75e9 archive: that panel reads `fault` alone, so the marker row renders as a
    whole-store fault line, with the whole-store prefix on its text and the whole-store hover (whatever is held there is
    not counted), beside the count line; each case reds at the marker line's own dress or hover words, named in its
    docstring."""

    def _render(self, remote_holds):
        tunnels = dict(PANEL_TUNNELS, remoteHolds=remote_holds)
        js = PANEL_STUB.replace("__PANEL_JS__", km._LANDING_REMOTES_JS).replace("__TUNNELS__", json.dumps(tunnels))
        p = subprocess.run(["node", "-e", js], capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, "the panel JS crashed:\n%s" % p.stderr[-2000:])
        out = json.loads(p.stdout or "{}")
        self.assertEqual(out.get("errors"), [], "the panel names a failed refresh in the console; there must be none")
        rows = out["rows"]
        heads = [i for i, r in enumerate(rows) if "Held for approval elsewhere" in r]
        section = rows[heads[0] + 1:] if heads else []
        return rows, heads, [r for r in section if "rnet-khead" not in r]

    def _host_rows(self, section, host):
        return [r for r in section if "<b>%s</b>" % host in r]

    def _assert_marker_line(self, line, text):
        """The marker line's dress: the fault text as the line's text, the partial hover, never the whole store's."""
        self.assertIn(">" + text + "</span>", line, "the fault text is the marker line's text")
        self.assertNotIn(WHOLE_STORE_PREFIX, line, "the marker is not dressed as the whole store refused")
        self.assertNotIn(WHOLE_STORE_HOVER, line, "the whole-store hover is false of a partial read")
        self.assertIn("it read are counted", line, "the hover says the counted messages stand...")
        self.assertIn("not counted here", line, "...the unread ones are not counted here...")
        self.assertIn("retried on the next refresh", line, "...and the read is retried")
        self.assertNotIn("held for your approval", line, "a marker row is not a held message and is never counted as one")

    def test_a_marker_renders_under_the_hosts_count_line_and_is_never_counted(self):
        """Two message rows and one marker row (unread 1, served 2) for one host: one count line saying 2 messages, the
        gist on hover, then one marker line carrying the fault text and the partial hover, nothing else for the host,
        and no key of the marker row but its fault rendered. Red over the f418f75e9 archive at the marker line's dress,
        `the fault text is the marker line's text` (that panel prefixes it with `held mail could not be read: `)."""
        rows, heads, section = self._render([
            _hold_row("HOLDER-A", "px-1"), _hold_row("HOLDER-A", "px-2"),
            _marker_row("HOLDER-A", frm="SECRET-FRM-MARKER", to="SECRET-TO-MARKER", gist="SECRET-MARKER-GIST", mid="SECRET-MID-MARKER",
                        origin="SECRET-ORIGIN-MARKER"),
        ])
        self.assertEqual(len(heads), 1, "the section renders once:\n%s" % "\n".join(rows))
        a = self._host_rows(section, "HOLDER-A")
        self.assertEqual(len(a), 2, "the count line and the marker line, nothing else for the host:\n%s" % "\n".join(section))
        self.assertIn("2 messages held for your approval", a[0], "the count line stands over the message rows...")
        self.assertIn(HOLD_GIST, a[0], "...with the gist on hover, as it always was")
        self.assertNotIn("3 messages", "\n".join(a), "the marker is never counted")
        self._assert_marker_line(a[1], MARKER_TEXT)
        joined = "\n".join(rows)
        for marker in ("SECRET-FRM-MARKER", "SECRET-TO-MARKER", "SECRET-MARKER-GIST", "SECRET-MID-MARKER", "SECRET-ORIGIN-MARKER"):
            self.assertNotIn(marker, joined, "nothing of a marker row but its fault text is rendered")
        self.assertEqual(len(section), 2, "one host, two lines:\n%s" % "\n".join(section))

    def test_a_marker_row_alone_renders_the_marker_line_and_no_count(self):
        """A marker row with no message row for its host (the twenty-row bound is over the message rows, so this is a
        degenerate payload, and the panel still says the truth of it): the marker line alone, no count claimed. Red over
        the f418f75e9 archive at `the fault text is the marker line's text` (the whole-store prefix on it there)."""
        rows, heads, section = self._render([_marker_row("HOLDER-B", unread=2, served=5)])
        self.assertEqual(len(heads), 1, "the section stands on a marker row alone:\n%s" % "\n".join(rows))
        self.assertEqual(len(section), 1, section)
        self.assertIn("<b>HOLDER-B</b>", section[0])
        self._assert_marker_line(section[0], MARKER_TEXT)
        self.assertNotRegex(section[0], r"\d+ messages? held for your approval", "no count is claimed for a host whose payload carried no message row")

    def test_a_marker_and_a_whole_store_fault_for_two_hosts_render_each_its_own_way(self):
        """HOLDER-B's store was refused whole (a `fault` row with no `unread`): the round 1 fault line, its prefix and its
        hover as before. HOLDER-C read two records and not a third (a marker row): the partial line. Red over the
        f418f75e9 archive at HOLDER-C's line, `the fault text is the marker line's text` (the whole-store prefix on it)."""
        rows, heads, section = self._render([
            _fault_row("HOLDER-B"),
            _hold_row("HOLDER-C", "px-1"), _hold_row("HOLDER-C", "px-2"), _marker_row("HOLDER-C"),
        ])
        self.assertEqual(len(heads), 1)
        b = self._host_rows(section, "HOLDER-B")
        self.assertEqual(len(b), 1, section)
        self.assertIn(WHOLE_STORE_PREFIX + FAULT_TEXT, b[0], "a fault row with no unread renders as the whole store refused, as before")
        self.assertIn("Whatever is held there is not counted here", b[0])
        self.assertNotIn("held for your approval", b[0])
        c = self._host_rows(section, "HOLDER-C")
        self.assertEqual(len(c), 2, "the count line and the marker line:\n%s" % "\n".join(section))
        self.assertIn("2 messages held for your approval", c[0])
        self._assert_marker_line(c[1], MARKER_TEXT)
        self.assertEqual(len(section), 3, section)

    def test_a_markers_text_is_escaped_and_a_fault_that_is_not_text_is_named_by_type(self):
        """The bus's wording is interpolated through esc, and a marker whose `fault` is not text (an object) is named by
        its type, never formatted; two markers with the same text for one host are one line. Red over the f418f75e9
        archive at HOLDER-B's marker line, `the fault text is the marker line's text` (the whole-store prefix on it)."""
        forged = '<b>forged</b> "quoted" & <img src=x onerror=alert(1)>'
        rows, heads, section = self._render([
            _hold_row("HOLDER-B", "px-1"), _marker_row("HOLDER-B", fault=forged),
            _hold_row("HOLDER-C", "px-1"), _marker_row("HOLDER-C", fault={"errno": 13}), _marker_row("HOLDER-C", fault={"errno": 13}),
        ])
        self.assertEqual(len(heads), 1)
        b = self._host_rows(section, "HOLDER-B")
        self.assertEqual(len(b), 2, section)
        self.assertIn("&lt;b&gt;forged&lt;/b&gt; &quot;quoted&quot; &amp; &lt;img", b[1], "esc on the interpolated marker text")
        self.assertNotIn("<img", b[1])
        self._assert_marker_line(b[1], "&lt;b&gt;forged&lt;/b&gt; &quot;quoted&quot; &amp; &lt;img src=x onerror=alert(1)&gt;")
        c = self._host_rows(section, "HOLDER-C")
        self.assertEqual(len(c), 2, "one count line and one marker line per distinct marker text per host:\n%s" % "\n".join(section))
        self.assertIn("1 message held for your approval", c[0])
        self._assert_marker_line(c[1], "a fault of type object")
        self.assertNotIn("[object Object]", c[1])
        self.assertNotIn("errno", c[1], "a value that is not text is named by its type, never formatted")


if __name__ == "__main__":
    unittest.main()

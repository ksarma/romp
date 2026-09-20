#!/usr/bin/env python3
"""Every in-page link in the repository's markdown resolves to a heading of its own file (round 10 of fork PR #778, correctness-1).

docs/reference.md's paragraph on the unit rewrite's identity refusal linked `#two-instances-on-one-machine`, an anchor no heading
in the repository produces, so the one pointer that sentence gave the reader was dead, and it stayed green through nine review
rounds because nothing read the anchors (CI renders no markdown). This module slugs every heading as GitHub does (lowercase, the
inline markup dropped, punctuation other than hyphens and underscores removed, spaces to hyphens, a repeated slug numbered -1, -2,
...), takes an explicit `<a id=...>` or `<a name=...>` as a target too, skips fenced code on both sides, and resolves every
`](#...)` reference in a file against that file's targets. The population is the documentation a reader is sent to: every
tracked markdown file under docs/, at the top level, and bin/README.md and tests/README.md. Outside it, read once when this
pin was written (2026-09-20) and left to their owners: ui/webview/anchor-map-fixtures/obsidian.md carries two deliberately odd
anchors (a fixture of the viewer's anchor map), plans/file-review.md one to `#results` and the ledger entry
upstream/2026-09-07-markdown-viewer-sanitizer.md one to `#top`, none a document this pin guards."""
import os
import re
import subprocess
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)

_FENCE = re.compile(r"^\s*(```|~~~)")
_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_HTML_ANCHOR = re.compile(r"""<a\s+(?:id|name)=["']([^"']+)["']""")
_IN_PAGE = re.compile(r"\]\(#([^)\s]+)\)")
_INLINE = [(re.compile(r"`([^`]*)`"), r"\1"),                 # code spans: the text stays, the ticks go
           (re.compile(r"!\[[^\]]*\]\([^)]*\)"), ""),          # an image contributes nothing
           (re.compile(r"\[([^\]]*)\]\([^)]*\)"), r"\1"),      # a link: its text
           (re.compile(r"[*_]{1,3}([^*_]+)[*_]{1,3}"), r"\1")]  # emphasis
_KEEP = re.compile(r"[^\w\- ]", re.UNICODE)


def slug(heading):
    """GitHub's anchor for a heading's text."""
    text = heading
    for pat, rep in _INLINE:
        text = pat.sub(rep, text)
    text = _KEEP.sub("", text.strip().lower()).replace(" ", "-")
    return text


def targets_and_links(text):
    """(set of anchors the file defines, [(line, anchor) for each in-page link]), fenced code skipped."""
    seen, anchors, links, fenced, fence = {}, set(), [], False, None
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


def tracked_markdown():
    """The tracked markdown files this pin guards (the module docstring names the population and what it leaves out)."""
    out = subprocess.run(["git", "-C", ROOT, "ls-files", "-z", "--", ":(glob)docs/**/*.md", ":(glob)*.md", "bin/README.md", "tests/README.md"],
                         capture_output=True, check=True).stdout
    return sorted({p.decode() for p in out.split(b"\0") if p})


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


class Slugs(unittest.TestCase):
    def test_slugs_as_github_does(self):
        self.assertEqual(slug("The manager's control port"), "the-managers-control-port")
        self.assertEqual(slug("Per-session billing: login vs API key"), "per-session-billing-login-vs-api-key")
        self.assertEqual(slug("`romp up` and the **bold** [link](x.md)"), "romp-up-and-the-bold-link")
        self.assertEqual(slug("  Spaced   words  "), "spaced---words")

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

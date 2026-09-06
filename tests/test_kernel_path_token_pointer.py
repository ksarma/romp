#!/usr/bin/env python3
"""The kernel's path-token comments name the client file that owns CLICKABLE_PATH_RE, and that file
must still define it.

_PATH_TOKEN_RE is a Python port of the client's CLICKABLE_PATH_RE, and its comments send a maintainer
to the client file for the other half of the parity contract. Slice 0 of plans/file-review.md moved
the regex out of render.ts into ui/webview/path-links.ts and left the kernel's pointer behind: the
parity fixture test reads only tests/fixtures/path_token_parity.json, so a pointer at a file that no
longer holds the regex went uncaught. This reads the kernel SOURCE (no import, no state), so it is
safe under any runner. Synthetic content only.
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
KERNEL = os.path.join(ROOT, "kernel", "kernel.py")
WEBVIEW = os.path.join(ROOT, "ui", "webview")

# Every "<file>.ts CLICKABLE_PATH_RE" pointer in the kernel, by the .ts basename it names.
POINTER_RE = re.compile(r"(?:[\w\-]+/)*([\w\-]+\.ts) CLICKABLE_PATH_RE")


class PathTokenPointer(unittest.TestCase):
    def test_kernel_pointers_name_the_file_that_defines_the_regex(self):
        with open(KERNEL, encoding="utf-8") as f:
            src = f.read()
        named = sorted(set(POINTER_RE.findall(src)))
        self.assertTrue(named, "the kernel names the client file that owns CLICKABLE_PATH_RE")
        for name in named:
            target = os.path.join(WEBVIEW, name)
            self.assertTrue(os.path.isfile(target), "%s names a file that does not exist" % name)
            with open(target, encoding="utf-8") as f:
                client = f.read()
            self.assertIn("export const CLICKABLE_PATH_RE", client,
                          "%s no longer defines CLICKABLE_PATH_RE; the kernel's pointer is stale" % name)

    def test_the_port_comment_sits_on_the_regex_it_ports(self):
        # The pointer is only useful next to _PATH_TOKEN_RE itself: the line that compiles the port
        # carries it, so a maintainer editing the regex sees where the other half lives.
        with open(KERNEL, encoding="utf-8") as f:
            lines = f.read().splitlines()
        defn = [ln for ln in lines if ln.startswith("_PATH_TOKEN_RE = re.compile(")]
        self.assertEqual(len(defn), 1, "one _PATH_TOKEN_RE definition")
        self.assertRegex(defn[0], POINTER_RE)


if __name__ == "__main__":
    unittest.main()

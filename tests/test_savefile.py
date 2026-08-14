#!/usr/bin/env python3
"""_save_file + the saveFile WS op — the viewer's raw-mode edit (plans/file-browser.md slice 2).

THE invariant is optimistic concurrency: agents edit the same trees a human has open in the viewer,
so a save whose baseMtime is older than the disk REFUSES loudly (reload-and-say-so) — never a merge,
never a silent last-writer-wins. Scope is exactly what raw mode shows: _is_text_path names within
the text cap, existing files only. Writes are temp-file + os.replace in the same directory with the
mode preserved, so a failure mid-write leaves the original intact.

Synthetic paths in a temp dir only (the notes-api demo world).
"""
import json
import os
import tempfile
import unittest
from importlib.machinery import SourceFileLoader

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_savefile", os.path.join(BIN, "romp-kernel")).load_module()


class _File(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.fp = os.path.join(self.tmp, "app.py")
        with open(self.fp, "w") as f:
            f.write("print('v1')\n")
        os.chmod(self.fp, 0o640)
        self.mt = int(os.stat(self.fp).st_mtime)


class SaveFile(_File):
    def test_a_clean_save_writes_and_returns_the_new_mtime(self):
        mt, err = km._save_file(self.fp, None, "print('v2')\n", self.mt)
        self.assertIsNone(err)
        self.assertEqual(open(self.fp).read(), "print('v2')\n")
        self.assertEqual(mt, int(os.stat(self.fp).st_mtime))

    def test_the_mode_survives_the_replace(self):
        km._save_file(self.fp, None, "print('v2')\n", self.mt)
        self.assertEqual(os.stat(self.fp).st_mode & 0o777, 0o640)

    def test_a_stale_base_mtime_refuses_and_names_the_conflict(self):
        # the concurrent-agent case: the disk moved after the viewer loaded — refuse, never merge
        os.utime(self.fp, (self.mt + 5, self.mt + 5))
        mt, err = km._save_file(self.fp, None, "print('mine')\n", self.mt)
        self.assertIsNone(mt)
        self.assertIn("changed on disk", err)
        self.assertEqual(open(self.fp).read(), "print('v1')\n", "the refusal wrote NOTHING")

    def test_a_failed_replace_leaves_the_original_intact(self):
        real = os.replace
        def boom(a, b):
            raise OSError(28, "No space left on device")
        os.replace = boom
        try:
            mt, err = km._save_file(self.fp, None, "print('v2')\n", self.mt)
        finally:
            os.replace = real
        self.assertIsNone(mt)
        self.assertIn("No space left", err)
        self.assertEqual(open(self.fp).read(), "print('v1')\n", "atomicity: no truncated file")
        self.assertEqual([f for f in os.listdir(self.tmp) if f.startswith(".romp-save-")], [],
                         "the temp file is cleaned up on failure")

    def test_binary_names_and_missing_files_and_creates_are_refused(self):
        self.assertIn("not a text file", km._save_file(os.path.join(self.tmp, "x.parquet"),
                                                       None, "data", 0)[1])
        self.assertIn("no such file", km._save_file(os.path.join(self.tmp, "new.py"),
                                                    None, "print()", 0)[1])

    def test_the_text_cap_is_enforced_and_named(self):
        mt, err = km._save_file(self.fp, None, "x" * (km._TEXT_MAX_BYTES + 1), self.mt)
        self.assertIsNone(mt)
        self.assertIn("text cap", err)

    def test_a_relative_path_resolves_against_the_sessions_cwd(self):
        real = km._cwd_of
        km._cwd_of = lambda sid: self.tmp if sid == "11111111-2222-3333-4444-000000000001" else None
        try:
            mt, err = km._save_file("app.py", "11111111-2222-3333-4444-000000000001",
                                    "print('v2')\n", self.mt)
            self.assertIsNone(err)
            self.assertEqual(open(self.fp).read(), "print('v2')\n")
        finally:
            km._cwd_of = real


class SaveFileWire(_File):
    """The WS op through the real dispatcher with a fake client (the listDir harness)."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"app": "feed", "alive": True,
                       "send": lambda s: self.sent.append(json.loads(s))}
        self.handler = object.__new__(km.Handler)

    def send(self, msg):
        km.Handler._dispatch_ws(self.handler, msg, self.client)
        return self.sent[-1] if self.sent else None

    def test_a_save_acks_with_the_request_id_and_new_mtime(self):
        r = self.send({"type": "saveFile", "path": self.fp, "content": "print('v2')\n",
                       "baseMtime": self.mt, "reqId": 3})
        self.assertEqual(r["type"], "fileSaved")
        self.assertEqual(r["reqId"], 3)
        self.assertEqual(r["mtime"], int(os.stat(self.fp).st_mtime))

    def test_a_refusal_nacks_with_the_kernels_words(self):
        r = self.send({"type": "saveFile", "path": self.fp, "content": "print('mine')\n",
                       "baseMtime": self.mt - 10, "reqId": 4})
        self.assertEqual(r["type"], "fileSaveFailed")
        self.assertEqual(r["reqId"], 4)
        self.assertIn("changed on disk", r["error"])


class LastModifiedHeader(unittest.TestCase):
    def test_the_file_route_stamps_last_modified_on_both_success_paths(self):
        # source pins (no live server here): the header is what the viewer's baseMtime anchors on
        import inspect
        src = inspect.getsource(km.Handler._file_preview)
        self.assertIn('lastmod = _httpdate(os.path.getmtime(fp))', src)
        self.assertIn('self.send_header("Last-Modified", lastmod)', src)
        self.assertEqual(src.count('headers={"Last-Modified": lastmod}'), 2,
                         "text AND media bodies both carry it")

    def test_the_remote_relay_mirrors_last_modified_unlike_content_type(self):
        import inspect
        src = inspect.getsource(km.Handler._remote_file)
        self.assertIn('lastmod = resp.getheader("Last-Modified")', src)
        self.assertIn('headers={"Last-Modified": lastmod} if lastmod else None', src)


if __name__ == "__main__":
    unittest.main()

#!/usr/bin/env python3
"""File comments (plans/file-review.md, Slice 1) — three kernel gates the review found open (2026-09-06).

- Send to session stands behind the file-editing consent BEFORE the message goes. The send's `send`
  entry is the comments log's only record of what went, and the unsent list is derived from it, so a
  send the log cannot record must not go: the first build delivered the message, stamped the todo,
  skipped the append, and the next click delivered the identical message again.
- A save on a file the comments log is owed an entry for, on a machine with no node, WARNS. The kernel
  mirrors the store layer's root, sidecar, log and config rules exactly where they are exact, and says
  "could not be checked" where only the host (link inheritance) can decide — never a quiet logged:false
  that reads as nothing owed.
- `status {baseline: true}` is refused `too-large` on a stat before node runs when the file is past the
  viewer's text cap, and the host's stdout is read through a bounded runner that kills the child past
  the reply cap instead of buffering a file-sized answer in the kernel.

The kernel's half against a STUB host script (tests/test_file_comments.py's pattern), plus the real
tools/file-comments-host.mjs where the point is agreement with it. Synthetic only: the notes-api demo
world, a placeholder sid, temp dirs.
"""
import inspect
import json
import os
import shutil
import subprocess
import tempfile
import threading
import time
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
BIN = os.path.join(REPO, "bin")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
km = SourceFileLoader("romp_kernel_filecomments_gates", os.path.join(BIN, "romp-kernel")).load_module()
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
NODE = shutil.which("node")
REAL_HOST = Path(os.path.join(REPO, "tools", "file-comments-host.mjs"))
TEXT = "# Findings\n\nThe api session cut p95 latency by 40%.\n"
EDITED = "# Findings\n\nThe api session cut p95 latency by 45%.\n"
ONE = [{"id": "1781100000000-0", "desc": "on this file", "body": "Which cache?"}]
NO_STORE = {"storeMtimeNs": "", "configMtimeNs": ""}

# The stub host: records the request it read from stdin, then answers as configured (canned JSON, or
# raw stdout, a non-zero exit, a stall). ESM like the real script.
_STUB = """import fs from 'node:fs';
const CFG = %s;
let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (d) => { raw += d; });
process.stdin.on('end', () => {
  let request = null;
  try { request = JSON.parse(raw); } catch (e) { request = { parseError: String(e) }; }
  fs.writeFileSync(CFG.seen, JSON.stringify({ request, pid: process.pid }));
  const finish = () => {
    if (CFG.stderr) process.stderr.write(CFG.stderr);
    if (CFG.stdout !== null) process.stdout.write(CFG.stdout);
    else process.stdout.write(JSON.stringify(CFG.reply));
    process.exit(CFG.exit);
  };
  if (CFG.sleep) setTimeout(finish, CFG.sleep * 1000); else finish();
});
"""

# A host whose answer never ends: 64 KB chunks for as long as the pipe takes them (it notes its pid
# first, so the test can check the kernel killed it).
_ENDLESS = """import fs from 'node:fs';
fs.writeFileSync(%s, JSON.stringify({ pid: process.pid }));
const chunk = '{"ok": true, "verb": "status", "pad": "' + 'x'.repeat(65500) + '"';
function pump() { let ok = true; while (ok) ok = process.stdout.write(chunk); process.stdout.once('drain', pump); }
pump();
"""

# A host that exits without reading its stdin at all.
_DEAF = "process.exit(3);\n"


@unittest.skipUnless(NODE, "node not installed on this machine")
class _World(unittest.TestCase):
    """A notes-api tree with a .trackchanges/ at its root and docs/report.md in it; the consent on; the
    kernel's state sandboxed with user todos ON, one known session (`web`, tmux-owned) and
    _send_or_park scripted; the kernel pointed at a stub host under the temp dir; the real dispatcher
    wired to a fake client whose send() flips an Event."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root = os.path.join(self.tmp, "notes-api")
        os.makedirs(os.path.join(self.root, ".trackchanges"))
        os.makedirs(os.path.join(self.root, "docs"))
        self.fp = os.path.join(self.root, "docs", "report.md")
        with open(self.fp, "w") as f:
            f.write(TEXT)
        self.ns = os.stat(self.fp).st_mtime_ns
        self.seen_path = os.path.join(self.tmp, "seen.json")
        self.stub_path = os.path.join(self.tmp, "stub-host.mjs")
        self._saved = (km._FILE_COMMENTS_HOST, km._FILE_COMMENTS_TIMEOUT, km._FILE_COMMENTS_REPLY_MAX)
        km._FILE_COMMENTS_HOST = Path(self.stub_path)
        # the state sandbox
        self.saved_state = jd.STATE
        jd.STATE = Path(self.tmp) / "state"
        jd.STATE.mkdir()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        km._set_file_editing(True)
        self._saved2 = (km._name_of, km._sdk, km._send_or_park)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected, self.send_result = [], True

        def fake_send_or_park(be, sid, text, echo=None, user_todo=None):
            self.injected.append({"sid": sid, "text": text, "echo": echo, "user_todo": user_todo})
            return self.send_result
        km._send_or_park = fake_send_or_park
        self.tid = km._add_user_todo(SID, "Need a look at the findings report", self.fp)
        # the wire
        self.sent, self.got = [], threading.Event()

        def _send(s):
            self.sent.append(json.loads(s))
            self.got.set()
        self.client = {"app": "feed", "alive": True, "send": _send}
        self.handler = object.__new__(km.Handler)
        self.stub()

    def tearDown(self):
        km._FILE_COMMENTS_HOST, km._FILE_COMMENTS_TIMEOUT, km._FILE_COMMENTS_REPLY_MAX = self._saved
        km._name_of, km._sdk, km._send_or_park = self._saved2
        km._set_file_editing(False)
        jd.STATE = self.saved_state
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)

    # -- the host ------------------------------------------------------------------------------------
    def stub(self, reply=None, exit=0, stderr="", stdout=None, sleep=0):
        if reply is None:
            reply = {"ok": True, "verb": "status", "root": self.root, "storePath": None, "trackedBy": None,
                     "agentTooling": "absent", "fileMtimeNs": str(self.ns), "storeMtimeNs": None,
                     "configMtimeNs": None, "store": None, "hunks": [],
                     "unsent": {"comments": [], "replies": [], "accepted": 0, "rejected": 0, "watermark": None},
                     "log": [], "logTruncated": False}
        cfg = {"seen": self.seen_path, "reply": reply, "exit": exit, "stderr": stderr, "stdout": stdout,
               "sleep": sleep}
        self.host_source(_STUB % json.dumps(cfg))

    def host_source(self, src):
        with open(self.stub_path, "w") as f:
            f.write(src)
        try:
            os.unlink(self.seen_path)
        except OSError:
            pass

    def real_host(self):
        km._FILE_COMMENTS_HOST = REAL_HOST

    def seen(self):
        try:
            with open(self.seen_path) as f:
                return json.load(f)
        except OSError:
            return None

    # -- the wire ------------------------------------------------------------------------------------
    def ws(self, msg, wait=True):
        self.got.clear()
        km.Handler._dispatch_ws(self.handler, msg, self.client)
        if wait:
            self.assertTrue(self.got.wait(20), "the op never answered")
        return self.sent[-1] if self.sent else None

    def op(self, verb, path=None, args=None, fence=None, rid=7):
        msg = {"type": "fileComments", "reqId": rid, "sid": SID, "path": path or self.fp, "verb": verb}
        if args is not None:
            msg["args"] = args
        if fence is not None:
            msg["fence"] = fence
        return self.ws(msg)

    def send(self, **kw):
        msg = {"type": "fileCommentsSend", "reqId": 9, "sid": SID, "path": self.fp, "tracked": True,
               "comments": ONE, "accepted": 0, "rejected": 0, "watermark": 1781100000000, "todoId": self.tid}
        msg.update(kw)
        return km._file_comments_send_op(msg)

    def save(self, path=None, content=EDITED, ns=None, rid=3):
        p = path or self.fp
        return self.ws({"type": "saveFile", "path": p, "content": content,
                        "baseMtimeNs": str(os.stat(p).st_mtime_ns if ns is None else ns), "reqId": rid}, wait=False)

    def todo(self):
        return km._user_todos()[SID][0]

    def config(self, **cfg):
        with open(os.path.join(self.root, ".trackchanges", "config.json"), "w") as f:
            f.write(json.dumps(dict({"v": 2}, **cfg)) + "\n")

    def log_lines(self, p=None):
        root = km._track_root(p or self.fp)
        _store, log, _cfg = km._track_paths(root, p or self.fp)
        return [json.loads(l) for l in open(log).read().splitlines() if l.strip()] if os.path.exists(log) else []


class _NoNode:
    """`with _NoNode():` — the kernel's node probe answers None (the stub itself still needs node to
    run, which is why the whole module skips without it)."""

    def __enter__(self):
        self.real = km.shutil.which
        km.shutil.which = lambda name, *a, **k: None

    def __exit__(self, *exc):
        km.shutil.which = self.real


# ═══════════════════════════════════════════════════════════════════════════════════════════════════
class TheSendStandsBehindTheConsent(_World):
    """fileCommentsSend with file editing off: refused before anything goes, so nothing is delivered,
    nothing is stamped, and the log is not left behind the session."""

    def setUp(self):
        super().setUp()
        self.stub(reply={"ok": True, "verb": "log-send", "logged": True})

    def test_editing_off_refuses_before_the_message_goes(self):
        km._set_file_editing(False)
        r = self.send()
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertEqual(r["reqId"], 9)
        self.assertEqual(r["code"], "editing-off")
        self.assertIn("file editing is off", r["error"], "the phrase the viewer's regex matches")
        self.assertIn("nothing was sent", r["error"])
        self.assertEqual(self.injected, [], "the message did not go")
        self.assertNotIn("resolved", self.todo(), "nothing was stamped")
        self.assertIsNone(self.seen(), "no host call: nothing to record")

    def test_the_gate_is_checked_once_ahead_of_delivery(self):
        src = inspect.getsource(km._file_comments_send_op)
        body = src[src.index('rid = msg.get("reqId")'):]          # past the docstring
        self.assertEqual(body.count("_file_editing_on()"), 1, "one gate per op, like _save_file")
        self.assertLess(body.index("_file_editing_on()"), body.index("_deliver_todo_reply("),
                        "the consent is checked before the message is delivered")
        self.assertLess(body.index("_file_editing_on()"), body.index("_file_comments_message("),
                        "before the message is even built")

    def test_with_consent_restored_the_same_send_goes_once_and_is_recorded(self):
        km._set_file_editing(False)
        self.assertEqual(self.send()["type"], "fileCommentsSendFailed")
        km._set_file_editing(True)
        r = self.send()
        self.assertEqual(r, {"type": "fileCommentsSent", "reqId": 9, "queued": False})
        self.assertEqual(len(self.injected), 1, "exactly one message, from the send that was allowed")
        self.assertEqual(self.todo()["resolved"]["kind"], "answered")
        s = self.seen()
        self.assertEqual(s["request"]["verb"], "log-send")
        self.assertEqual(s["request"]["args"]["comments"], ONE)

    def test_the_refusal_names_the_file_and_carries_no_todo_side_effect(self):
        km._set_file_editing(False)
        r = self.send(todoId=None)
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertIn("report.md", r["error"])
        self.assertEqual(self.injected, [])

    def test_end_to_end_through_the_real_host(self):
        """The review's scenario, through the real host script and the vendored store: comments written
        under consent; consent off; Send → refused and the comments stay unsent (nothing went); consent
        on; Send → one message, one `send` entry, the unsent list empty."""
        self.real_host()
        c = self.op("comment", args={"note": "Which cache?"}, fence=NO_STORE)
        self.assertEqual(c["type"], "fileCommentsResult", c)
        cid = c["store"]["comments"][0]["id"]
        s = self.op("status")
        self.assertEqual(s["unsent"]["comments"], [cid])
        comments = [{"id": cid, "desc": "on this file", "body": "Which cache?"}]
        wm = c["store"]["comments"][0]["ts"]           # epoch ms, as the host stamps a comment
        km._set_file_editing(False)
        r = self.send(comments=comments, watermark=wm)
        self.assertEqual(r["type"], "fileCommentsSendFailed")
        self.assertIn("file editing is off", r["error"])
        self.assertEqual(self.injected, [])
        self.assertEqual(self.log_lines(), [], "no send entry for a send that was refused")
        self.assertEqual(self.op("status")["unsent"]["comments"], [cid], "still unsent — nothing went")
        km._set_file_editing(True)
        r = self.send(comments=comments, watermark=wm)
        self.assertEqual(r["type"], "fileCommentsSent", r)
        self.assertNotIn("logWarning", r)
        self.assertEqual(len(self.injected), 1)
        self.assertTrue(self.injected[0]["text"].startswith("[obsidian-diff] I left 1 comment on %s.\n" % self.fp))
        sends = [e for e in self.log_lines() if e["kind"] == "send"]
        self.assertEqual(len(sends), 1)
        self.assertEqual(sends[0]["comments"][0]["id"], cid)
        self.assertEqual(self.op("status")["unsent"]["comments"], [], "the log's derivation: nothing left unsent")


# ═══════════════════════════════════════════════════════════════════════════════════════════════════
class TheNoNodeSaveWarns(_World):
    """saveFile on a machine with no node: a file the comments log is owed an entry for warns in the
    fileSaved reply (logged:false + logWarning); a file the host would not have logged either stays
    quiet; where only the host could decide, the warning says the log could not be checked."""

    def warned(self, path=None):
        with _NoNode():
            r = self.save(path=path)
        self.assertEqual(r["type"], "fileSaved", r)
        self.assertIs(r["logged"], False)
        self.assertIsNone(self.seen(), "no node: the host never ran")
        return r.get("logWarning")

    def test_a_config_tracked_file_saves_and_warns(self):
        self.config(tracked=["docs/report.md"])
        w = self.warned()
        self.assertIsNotNone(w, "the log is owed this edit and could not take it: say so")
        self.assertIn("comments log", w)
        self.assertIn("node is not installed", w)
        self.assertIn("report.md", w)
        self.assertNotIn("could not be checked", w, "a listed file is a certain miss, not a maybe")
        self.assertEqual(open(self.fp).read(), EDITED, "the save itself landed")

    def test_a_folder_entry_covers_the_file(self):
        self.config(tracked=["docs/"])
        w = self.warned()
        self.assertIn("node is not installed", w)
        self.assertNotIn("could not be checked", w)

    def test_a_sidecar_or_a_log_makes_the_file_the_logs_business_whatever_the_config_says(self):
        root = km._track_root(self.fp)
        store, log, _cfg = km._track_paths(root, self.fp)
        with open(store, "w") as f:
            f.write(json.dumps({"v": 3, "path": "docs/report.md", "suggestions": [], "comments": []}))
        w = self.warned()
        self.assertIn("node is not installed", w)
        self.assertNotIn("could not be checked", w)
        os.unlink(store)
        with open(log, "w") as f:
            f.write(json.dumps({"ts": "2026-09-06T00:00:00.000Z", "kind": "set-tracked", "author": "you"}) + "\n")
        w = self.warned()
        self.assertIn("node is not installed", w)
        self.assertNotIn("could not be checked", w)

    def test_an_unlisted_file_under_a_config_with_entries_says_the_log_could_not_be_checked(self):
        # tracking inherits through [[links]] from a tracked note; only the host resolves that closure
        self.config(tracked=["docs/other.md"])
        w = self.warned()
        self.assertIsNotNone(w)
        self.assertIn("could not be checked", w)
        self.assertIn("node is not installed", w)

    def test_a_corrupt_or_newer_config_says_the_log_could_not_be_checked(self):
        with open(os.path.join(self.root, ".trackchanges", "config.json"), "w") as f:
            f.write("{not json\n")
        self.assertIn("could not be checked", self.warned())
        self.config(v=3, tracked=["docs/report.md"])
        self.assertIn("could not be checked", self.warned())

    def test_nothing_owed_stays_quiet(self):
        # no config, no sidecar, no log: the host would answer logged:false, and so does the mirror
        self.assertIsNone(self.warned())
        # a config with an empty tracked list
        self.config(tracked=[])
        self.assertIsNone(self.warned())
        # the file vetoed by `untracked`, as store-io's isTrackedFile reads it
        self.config(tracked=["docs/"], untracked=["docs/report.md"])
        self.assertIsNone(self.warned())

    def test_a_nearer_root_without_its_own_trackchanges_is_the_hosts_root_too(self):
        # store-io's root is the NEAREST landmark: a sub-project with a .git and no .trackchanges/ of its
        # own is not covered by the parent's config, so the host logs nothing and the mirror agrees
        sub = os.path.join(self.root, "sub")
        os.makedirs(os.path.join(sub, ".git"))
        fp = os.path.join(sub, "x.md")
        with open(fp, "w") as f:
            f.write("a\n")
        self.config(tracked=["sub/x.md", "sub/"])
        self.assertTrue(km._trackchanges_above(fp))
        self.assertIsNone(self.warned(path=fp))

    def test_with_node_present_the_host_decides_as_before(self):
        self.stub(reply={"ok": True, "verb": "log-edit", "logged": True})
        self.config(tracked=["docs/report.md"])
        r = self.save()
        self.assertIs(r["logged"], True)
        self.assertNotIn("logWarning", r)
        self.assertEqual(self.seen()["request"]["verb"], "log-edit")

    def test_the_mirror_never_contradicts_the_real_host(self):
        """Where _edit_log_stake claims certainty ("logged" / None) the real host's log-edit answers the
        same `logged`; "maybe" is allowed either answer. Each world is read by the mirror BEFORE the
        host runs (a logged edit creates the log, which changes the world)."""
        self.real_host()
        summary = {"mtimeBeforeNs": "1", "mtimeAfterNs": "2", "bytesBefore": 1, "bytesAfter": 2,
                   "diff": "", "truncated": False}
        worlds = [
            ("no config", lambda: None),
            ("listed file", lambda: self.config(tracked=["docs/report.md"])),
            ("folder entry", lambda: self.config(tracked=["docs/"])),
            ("empty list", lambda: self.config(tracked=[])),
            ("vetoed", lambda: self.config(tracked=["docs/"], untracked=["docs/report.md"])),
            ("unlisted under entries", lambda: self.config(tracked=["docs/other.md"])),
            ("dot-slash spellings", lambda: self.config(tracked=["./docs/"])),
        ]
        for name, build in worlds:
            shutil.rmtree(os.path.join(self.root, ".trackchanges"))
            os.makedirs(os.path.join(self.root, ".trackchanges"))
            build()
            stake = km._edit_log_stake(self.fp)
            out, err = km._file_comments_call(self.fp, "log-edit", {"summary": summary})
            self.assertIsNone(err, (name, err))
            host = bool(out.get("logged"))
            if stake == "logged":
                self.assertTrue(host, "%s: the mirror said logged, the host did not" % name)
            elif stake is None:
                self.assertFalse(host, "%s: the mirror said nothing owed, the host logged" % name)
            else:
                self.assertEqual(stake, "maybe", name)

    def test_the_sidecar_path_mirror_is_encode_uri_component(self):
        names = ["docs/report.md", "docs/Meeting notes (v2).md", "docs/résumé.md", "a+b&c=d#e.md",
                 "it's!*()~.md", "sub dir/ünïcödé — dash.md"]
        for n in names:
            store, log, cfg = km._track_paths(self.root, os.path.join(self.root, n))
            r = subprocess.run([NODE, "-e", "console.log(encodeURIComponent(process.argv[1]))", "--", n],
                               capture_output=True, text=True, timeout=20)
            enc = r.stdout.strip()
            self.assertEqual(store, os.path.join(self.root, ".trackchanges", enc + ".json"), n)
            self.assertEqual(log, os.path.join(self.root, ".trackchanges", enc + ".comments-log.jsonl"), n)
        self.assertEqual(cfg, os.path.join(self.root, ".trackchanges", "config.json"))

    def test_the_listed_mirror_is_engine_is_tracked(self):
        self.assertTrue(km._track_listed(["docs/report.md"], "docs/report.md"))
        self.assertTrue(km._track_listed(["docs/"], "docs/report.md"))
        self.assertTrue(km._track_listed(["./docs/"], "/docs/report.md"))
        self.assertFalse(km._track_listed(["docs"], "docs/report.md"), "a file entry is exact, not a prefix")
        self.assertFalse(km._track_listed(["docs/report.md"], "docs/report.md.bak"))
        self.assertFalse(km._track_listed([1, None, ""], "docs/report.md"))
        self.assertFalse(km._track_listed("docs/", "docs/report.md"))


# ═══════════════════════════════════════════════════════════════════════════════════════════════════
class TheBaselineIsBounded(_World):
    """`baseline` is the whole file in the reply: refused on a stat above the text cap before node
    runs; and whatever the verb, the host's stdout is read through a bound that kills the child."""

    def big(self, size=km._TEXT_MAX_BYTES + 1):
        p = os.path.join(self.root, "docs", "huge.md")
        with open(p, "wb") as f:
            f.write(b"x" * size)
        return p

    def test_baseline_on_a_file_past_the_text_cap_is_refused_before_node_runs(self):
        p = self.big()
        r = self.op("status", path=p, args={"baseline": True})
        self.assertEqual(r["type"], "fileCommentsFailed")
        self.assertEqual(r["code"], "too-large")
        self.assertIn("2.0 MB", r["error"])
        self.assertIn("huge.md", r["error"])
        self.assertIsNone(self.seen(), "refused on the stat: node never ran")

    def test_the_stat_gate_applies_to_every_verb_that_asks_for_the_baseline(self):
        p = self.big()
        r = self.op("comment", path=p, args={"baseline": True, "note": "x"}, fence=NO_STORE)
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "too-large"))
        self.assertIsNone(self.seen())

    def test_baseline_on_a_small_file_reaches_the_host(self):
        r = self.op("status", args={"baseline": True})
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertIs(self.seen()["request"]["args"]["baseline"], True)

    def test_status_without_the_baseline_on_a_big_file_still_reaches_the_host(self):
        # the host stats instead of reading for a plain status; only the whole-file answer is refused
        p = self.big()
        r = self.op("status", path=p)
        self.assertEqual(r["type"], "fileCommentsResult")
        self.assertEqual(self.seen()["request"]["path"], p)

    def test_only_a_true_baseline_flag_counts(self):
        p = self.big()
        for v in (1, "true", "yes", None, False):
            r = self.op("status", path=p, args={"baseline": v})
            self.assertEqual(r["type"], "fileCommentsResult", v)

    def test_the_real_host_still_returns_the_baseline_of_a_small_file(self):
        self.real_host()
        r = self.op("status", args={"baseline": True})
        self.assertEqual(r["type"], "fileCommentsResult", r)
        self.assertEqual(r["baseline"], TEXT)

    def test_a_reply_past_the_cap_is_cut_off_and_the_host_killed(self):
        km._FILE_COMMENTS_REPLY_MAX = 256 * 1024
        km._FILE_COMMENTS_TIMEOUT = 8
        self.host_source(_ENDLESS % json.dumps(self.seen_path))
        t0 = time.monotonic()
        r = self.op("status")
        took = time.monotonic() - t0
        self.assertEqual(r["type"], "fileCommentsFailed")
        self.assertEqual(r["code"], "host-error")
        self.assertIn("256.0 KB", r["error"])
        self.assertIn("cut off", r["error"])
        self.assertLess(took, 4, "cut at the cap, not at the deadline (%.1fs)" % took)
        pid = self.seen()["pid"]
        for _ in range(50):                      # the kill is synchronous in the runner; the loop absorbs scheduling
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break
            time.sleep(0.05)
        else:
            self.fail("the host process %d outlived the cut-off reply" % pid)

    def test_a_host_that_exits_without_reading_its_stdin_cannot_hang_the_call(self):
        # a request larger than a pipe buffer, to a child that never drains it: EPIPE, not a deadlock
        self.host_source(_DEAF)
        km._FILE_COMMENTS_TIMEOUT = 8
        t0 = time.monotonic()
        r = self.op("comment", args={"note": "n" * (300 * 1024)}, fence=NO_STORE)
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "host-error"))
        self.assertIn("exit 3", r["error"])
        self.assertLess(time.monotonic() - t0, 4)

    def test_the_deadline_still_kills_and_reports(self):
        km._FILE_COMMENTS_TIMEOUT = 1
        self.stub(sleep=5, stderr="still loading")
        t0 = time.monotonic()
        r = self.op("status")
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "host-error"))
        self.assertIn("did not answer within 1 s", r["error"])
        self.assertLess(time.monotonic() - t0, 4)

    def test_stderr_and_a_non_zero_exit_still_ride_the_error(self):
        self.stub(exit=2, stderr="EACCES: permission denied")
        r = self.op("status")
        self.assertEqual((r["type"], r["code"]), ("fileCommentsFailed", "host-error"))
        self.assertIn("exit 2", r["error"])
        self.assertIn("EACCES", r["error"])

    def test_run_bounded_returns_what_run_did(self):
        rc, out, err, overflow = km._run_bounded(
            [NODE, "-e", "process.stdin.on('data', d => process.stdout.write(d)); process.stderr.write('e')"],
            "hello", 10, 1024)
        self.assertEqual((rc, out, err, overflow), (0, b"hello", b"e", False))
        rc, out, err, overflow = km._run_bounded([NODE, "-e", "process.stdout.write('x'.repeat(2048))"], "", 10, 1024)
        self.assertEqual((rc, out, overflow), (None, b"", True))


if __name__ == "__main__":
    unittest.main()

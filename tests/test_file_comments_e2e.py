#!/usr/bin/env python3
"""File comments (plans/file-review.md, Slices 1 and 2) — end to end, with nothing stubbed below the wire.

tests/test_file_comments.py proves the kernel's half against a STUB host script; the host's own node
tests prove its half against the vendored CLIs. This module joins the pieces the way the dashboard
does: the real `Handler._dispatch_ws` runs the real `tools/file-comments-host.mjs`, which loads the
real vendored `store-io` and engine, on a synthetic project under pytest's tmp_path; the vendored
`track-reply` CLI answers as the session would; the patched guard is spawned exactly as Claude Code
spawns a PreToolUse hook (its JSON on stdin, the session's environment); the vendored `track-edit`
records the session's changes the way the sent message tells it to. Only what needs a live session is
scripted: `_send_or_park` records the message instead of injecting it, the names registry is a lambda
that knows one session, `web`, whose recorded cwd is the project root (so the reject trace finds an
owner), and that session's backend `send` is a recorder.

Skipped when node is missing (the host script and the CLIs run under it). Synthetic only: the
notes-api demo world, a placeholder sid, a `.git/` directory as the project landmark (store-io reads
nothing from it).
"""
import json
import os
import shutil
import subprocess
import tempfile
import threading
from romp_load import load_source
from pathlib import Path

import pytest

HERE = os.path.dirname(os.path.realpath(__file__))
REPO = os.path.dirname(HERE)
BIN = os.path.join(REPO, "bin")
VENDOR = os.path.join(REPO, "vendor", "track-changents")
HOST = os.path.join(REPO, "tools", "file-comments-host.mjs")
GUARD = os.path.join(VENDOR, "hooks", "track-guard.mjs")
TRACK_REPLY = os.path.join(VENDOR, "cli", "track-reply.mjs")
TRACK_EDIT = os.path.join(VENDOR, "cli", "track-edit.mjs")
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
# Hermetic state BEFORE the load — the kernel resolves its state root at import time, and only pytest
# runs conftest's floor (a bare script run would otherwise write REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
km = load_source("romp_kernel_filecomments_e2e", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
NODE = shutil.which("node")
TEXT = "# Findings\n\nThe api session cut p95 latency by 40%.\n\nWe recommend shipping the cache in v1.2.\n"
EDITED = "# Findings\n\nThe api session cut p95 latency by 45%.\n\nWe recommend shipping the cache in v1.2.\n"
PNG = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, 0, 0, 0, 13, 0x49, 0x48, 0x44, 0x52])
EMPTY_UNSENT = {"comments": [], "replies": [], "accepted": 0, "rejected": 0, "watermark": None}
NO_STORE = {"storeMtimeNs": "", "configMtimeNs": ""}   # the fence a browser sends before any sidecar exists

pytestmark = pytest.mark.skipif(not NODE, reason="node not installed on this machine")


def _env(**extra):
    """The environment a child gets: this process's, minus the two variables that would change the
    outcome — TRACKCHANGES_ROOT (a stranger's root for every file) and ROMP_SID (the suite may itself
    run inside a romp session) — plus `extra`."""
    env = dict(os.environ)
    env.pop("TRACKCHANGES_ROOT", None)
    env.pop("ROMP_SID", None)
    env.update(extra)
    return env


def _node(argv, stdin=None, env=None, timeout=20):
    return subprocess.run([NODE] + list(argv), input=stdin, capture_output=True, text=True,
                          timeout=timeout, env=env or _env())


def store_io(file):
    """What the vendored store layer says about `file`: its root and its sidecar path — the
    authority the host's answers are compared against."""
    src = ("const s = await import(process.argv[1]); const f = process.argv[2]; const r = s.findVaultRoot(f);"
           " console.log(JSON.stringify({root: r, store: r ? s.storePathFor(r, f) : null,"
           " tracked: r ? s.isTrackedFile(r, f) : false}));")
    r = _node(["--input-type=module", "-e", src, "--", Path(os.path.join(VENDOR, "store-io.mjs")).as_uri(), file])
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def make_anchor(text, start, end):
    """The engine's own anchor for text[start:end] — what the browser's anchor-map builds."""
    src = ("const fs = (await import('fs')).default; const m = await import(process.argv[1]); const e = m.default || m;"
           " const [t, a, b] = JSON.parse(fs.readFileSync(0, 'utf8'));"
           " console.log(JSON.stringify(e.makeAnchor(t, a, b)));")
    r = _node(["--input-type=module", "-e", src, "--", Path(os.path.join(VENDOR, "engine.js")).as_uri()],
              stdin=json.dumps([text, start, end]))
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


class World:
    """A notes-api project (landmark: `.git/`) with docs/report.md, docs/other.md and docs/figure.png; a
    loose notes.md with no landmark above it; a scratch.md outside any project. The kernel's state
    lives under tmp_path, user todos and file editing are on, one todo names the report, and the
    dispatcher answers a fake client whose send() flips an Event. One live session, `web`, has the
    project root as its recorded cwd, so a trace (a save's, a reject's) resolves to it; its backend's
    send is recorded in `traced`, and `order` writes down whether a client reply or a trace came first."""

    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.root = tmp_path / "notes-api"
        (self.root / ".git").mkdir(parents=True)
        (self.root / "docs").mkdir()
        self.fp = self.root / "docs" / "report.md"
        self.fp.write_text(TEXT)
        self.other = self.root / "docs" / "other.md"
        self.other.write_text("# Other\n")
        self.png = self.root / "docs" / "figure.png"
        self.png.write_bytes(PNG)
        self.loose = tmp_path / "loose" / "notes.md"
        self.loose.parent.mkdir()
        self.loose.write_text("A loose note.\n")
        self.outside = tmp_path / "elsewhere" / "scratch.md"
        self.outside.parent.mkdir()
        self.outside.write_text("scratch\n")
        # the kernel's state, sandboxed under tmp_path
        self.saved_state = jd.STATE
        jd.STATE = tmp_path / "state"
        jd.STATE.mkdir()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)
        km._set_file_editing(True)
        self.saved = (km._name_of, km._sdk, km._send_or_park)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected = []

        def fake_send_or_park(be, sid, text, echo=None, user_todo=None):
            self.injected.append({"sid": sid, "text": text, "echo": echo, "user_todo": user_todo})
            return True
        km._send_or_park = fake_send_or_park
        # the one live session and its tree, and the door a trace goes through (Sessions.backend_for(...).send)
        self.saved_trace = (km._tmux_sessions, km._cwd_of, km.Sessions.__dict__["backend_for"])
        km._tmux_sessions = lambda: {SID: {}}
        km._cwd_of = lambda s: str(self.root) if s == SID else ""
        self.traced, self.order = [], []
        world = self

        class _FakeBackend:
            def send(self, sid, text, *a, **k):
                world.order.append("trace")
                world.traced.append((sid, text))
                return True
        km.Sessions.backend_for = staticmethod(lambda sid: _FakeBackend())
        self.tid = km._add_user_todo(SID, "Need a look at the findings report", str(self.fp))
        # the wire
        self.sent, self.got = [], threading.Event()

        def _send(s):
            self.order.append("reply")
            self.sent.append(json.loads(s))
            self.got.set()
        self.client = {"app": "feed", "alive": True, "send": _send}
        self.handler = object.__new__(km.Handler)
        self.rid = 0

    def close(self):
        km._name_of, km._sdk, km._send_or_park = self.saved
        km._tmux_sessions, km._cwd_of, backend_for = self.saved_trace
        km.Sessions.backend_for = backend_for
        km._set_file_editing(False)
        jd.STATE = self.saved_state
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()

    def ws(self, msg, wait=True):
        """One frame through the real dispatcher; the file-comments ops answer from their own thread, and
        that thread is joined before returning so what follows the reply (a reject's trace) has run."""
        self.rid += 1
        msg = dict(msg, reqId=self.rid)
        self.got.clear()
        before = set(threading.enumerate())
        km.Handler._dispatch_ws(self.handler, msg, self.client)
        if wait:
            assert self.got.wait(30), "the op never answered"
        for t in set(threading.enumerate()) - before:
            t.join(20)
        rep = self.sent[-1]
        assert rep["reqId"] == self.rid
        return rep

    def op(self, verb, path, args=None, fence=None):
        msg = {"type": "fileComments", "sid": SID, "path": str(path), "verb": verb}
        if args is not None:
            msg["args"] = args
        if fence is not None:
            msg["fence"] = fence
        return self.ws(msg)

    def ok(self, verb, path, args=None, fence=None):
        rep = self.op(verb, path, args, fence)
        assert rep["type"] == "fileCommentsResult", rep
        assert rep["verb"] == verb
        return rep

    def fence_of(self, status, file=False):
        """The fence the panel sends from its last status/result reply; `file` adds the file's mtime, which
        the verbs that write the file (reject, reject-all) require."""
        f = {"storeMtimeNs": status["storeMtimeNs"] or "", "configMtimeNs": status["configMtimeNs"] or ""}
        if file:
            f["fileMtimeNs"] = status["fileMtimeNs"]
        return f

    def track_edit(self, old, new, path=None):
        """The session revises the file with the vendored CLI, exactly as the sent message tells it to."""
        r = _node([TRACK_EDIT, "--file", str(path or self.fp), "--old", old, "--new", new],
                  env=_env(ROMP_SESSION_NAME="web", ROMP_SID=SID))
        assert r.returncode == 0, r.stderr
        return r

    def comment(self, path, note, fence=None, anchor=None, hint=None):
        args = {"note": note}
        if anchor is not None:
            args["anchor"], args["hintOffset"] = anchor, hint
        return self.ok("comment", path, args, fence or NO_STORE)

    def todo(self):
        return km._user_todos()[SID][0]

    def log_path(self, status):
        return Path(status["storePath"][:-len(".json")] + ".comments-log.jsonl")

    def log_lines(self, status):
        p = self.log_path(status)
        return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


@pytest.fixture
def world(tmp_path):
    w = World(tmp_path)
    try:
        yield w
    finally:
        w.close()


def test_the_kernel_runs_the_real_host_script_here():
    """The point of this module: nothing between the dispatcher and the vendored store layer is a stub."""
    assert Path(km._FILE_COMMENTS_HOST) == Path(HOST)
    assert os.path.isfile(HOST)
    assert os.path.isfile(TRACK_REPLY) and os.path.isfile(GUARD)


def test_status_on_a_clean_file_with_no_landmark(world):
    if store_io(str(world.loose))["root"] is not None:
        pytest.skip("a .git, .obsidian or .trackchanges directory sits above the temp dir on this machine")
    ns = world.loose.stat().st_mtime_ns
    s = world.ok("status", world.loose)
    assert (s["root"], s["storePath"], s["trackedBy"], s["store"]) == (None, None, None, None)
    assert s["hunks"] == [] and s["log"] == [] and s["logTruncated"] is False
    assert s["unsent"] == EMPTY_UNSENT
    assert (s["fileMtimeNs"], s["storeMtimeNs"], s["configMtimeNs"]) == (str(ns), None, None)
    assert s["agentTooling"] in ("present", "absent")
    assert not (world.loose.parent / ".trackchanges").exists(), "status writes nothing"


def test_a_whole_file_comment_on_a_loose_file_creates_the_project_beside_it(world):
    if store_io(str(world.loose))["root"] is not None:
        pytest.skip("a .git, .obsidian or .trackchanges directory sits above the temp dir on this machine")
    before = world.loose.read_bytes()
    r = world.comment(world.loose, "Which cache?")
    # decision 37: .trackchanges/ appears beside the file and is its project's root from now on
    assert Path(r["root"]) == world.loose.parent
    assert (world.loose.parent / ".trackchanges").is_dir()
    authority = store_io(str(world.loose))
    assert authority["root"] == r["root"]
    assert r["storePath"] == authority["store"], "the sidecar is exactly where storePathFor puts it"
    assert Path(r["storePath"]) == world.loose.parent / ".trackchanges" / "notes.md.json"
    assert r["storeMtimeNs"] == str(Path(r["storePath"]).stat().st_mtime_ns)
    disk = json.loads(Path(r["storePath"]).read_text())
    assert disk["v"] == 3 and disk["suggestions"] == []
    c = disk["comments"][0]
    assert set(c) == {"id", "author", "ts", "body", "replies", "resolved"}, "a whole-file comment: no anchor, no target"
    assert (c["author"], c["body"], c["replies"], c["resolved"]) == ("you", "Which cache?", [], False)
    assert isinstance(c["ts"], int) and c["id"] == "%d-0" % c["ts"]
    assert "authorId" not in c
    assert r["store"]["comments"] == disk["comments"], "the reply is what the next load sees"
    assert r["unsent"] == dict(EMPTY_UNSENT, comments=[c["id"]])
    assert world.loose.read_bytes() == before, "a comment never touches the file"


def test_a_passage_comment_in_a_project_lands_in_the_root_sidecar(world):
    start = TEXT.index("shipping the cache")
    end = start + len("shipping the cache")
    anchor = make_anchor(TEXT, start, end)
    assert anchor["quote"] == "shipping the cache"
    r = world.comment(world.fp, "Which cache? Say which.", anchor=anchor, hint=start)
    assert Path(r["root"]) == world.root, "the .git/ landmark, not the file's own directory"
    authority = store_io(str(world.fp))
    assert r["storePath"] == authority["store"]
    assert Path(r["storePath"]) == world.root / ".trackchanges" / "docs%2Freport.md.json"
    disk = json.loads(Path(r["storePath"]).read_text())
    c = disk["comments"][0]
    assert c["anchor"] == anchor, "stored at the located position with the engine's own context"
    assert c["id"] == "%d-%d" % (c["ts"], start)
    assert (c["author"], c["body"]) == ("you", "Which cache? Say which.")
    assert "target" not in c
    assert world.fp.read_text() == TEXT
    # the same passage again, with no hint: the quote occurs once, so it locates
    r2 = world.comment(world.fp, "And say when.", fence=world.fence_of(r), anchor=anchor)
    assert [x["body"] for x in r2["store"]["comments"]] == ["Which cache? Say which.", "And say when."]
    # a stale fence refuses and writes nothing
    bad = world.op("comment", world.fp, {"note": "late"}, NO_STORE)
    assert (bad["type"], bad["code"]) == ("fileCommentsFailed", "store-moved")
    assert "appeared on disk" in bad["error"] and "reload" in bad["error"]
    assert len(json.loads(Path(r["storePath"]).read_text())["comments"]) == 2


def test_track_reply_answers_into_the_comment_and_status_derives_unsent(world):
    r = world.comment(world.fp, "Which cache?")
    cid = r["store"]["comments"][0]["id"]
    # the session answers with the vendored CLI, exactly as the sent message tells it to
    rep = _node([TRACK_REPLY, "--file", str(world.fp), "--thread", cid, "--note", "The response cache."],
                env=_env(ROMP_SESSION_NAME="web", ROMP_SID=SID))
    assert rep.returncode == 0, rep.stderr
    s = world.ok("status", world.fp)
    replies = s["store"]["comments"][0]["replies"]
    assert len(replies) == 1
    assert (replies[0]["author"], replies[0]["authorId"], replies[0]["body"]) == ("web", SID, "The response cache.")
    assert isinstance(replies[0]["ts"], int)
    assert s["unsent"] == dict(EMPTY_UNSENT, comments=[cid]), "the session's reply is not the person's to send"
    # the person replies back through the host: that IS unsent
    r2 = world.ok("reply", world.fp, {"commentId": cid, "note": "Yes, that one."}, world.fence_of(s))
    mine = r2["store"]["comments"][0]["replies"][1]
    assert (mine["author"], mine["body"]) == ("you", "Yes, that one.") and "authorId" not in mine
    assert r2["unsent"] == dict(EMPTY_UNSENT, comments=[cid], replies=[{"commentId": cid, "ts": mine["ts"]}])
    # the CLI reads the host's comment unchanged: a second reply lands after the first two
    rep2 = _node([TRACK_REPLY, "--file", str(world.fp), "--thread", cid, "--note", "Noted."],
                 env=_env(ROMP_SESSION_NAME="web", ROMP_SID=SID))
    assert rep2.returncode == 0, rep2.stderr
    s2 = world.ok("status", world.fp)
    assert [x["author"] for x in s2["store"]["comments"][0]["replies"]] == ["web", "you", "web"]
    # an unknown comment refuses no-comment, never a revive
    bad = world.op("reply", world.fp, {"commentId": "1-1", "note": "x"}, world.fence_of(s2))
    assert (bad["type"], bad["code"]) == ("fileCommentsFailed", "no-comment")


def expected_message(path, comments, tracked):
    """Contract C3, spelled out independently of both builders."""
    n = len(comments)
    out = ["[obsidian-diff] I left %d comment%s on %s." % (n, "" if n == 1 else "s", path), ""]
    for c in comments:
        out += ["Comment %s (%s):" % (c["id"], c["desc"]), c["body"], ""]
    out += ["To respond:",
            "  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file %s --thread <id> --note \"<your reply>\"" % path]
    if tracked:
        out.append("  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file %s --thread <id> --old \"<exact text>\" --new \"<replacement>\"" % path)
    else:
        out.append("  • to revise the text: edit the file normally, then say what you changed with the reply command above")
    out += ["", "When you have addressed these, ask me for another look the same way you asked for this one,", "naming the file."]
    return "\n".join(out) + "\n"


def test_send_to_session_carries_the_contract_text_answers_the_todo_and_the_log_empties_unsent(world):
    start = TEXT.index("shipping the cache in v1.2")
    anchor = make_anchor(TEXT, start, start + len("shipping the cache in v1.2"))
    r1 = world.comment(world.fp, "Which cache?")
    r2 = world.comment(world.fp, "Say when, too.", fence=world.fence_of(r1), anchor=anchor, hint=start)
    s = world.ok("status", world.fp)
    cs = s["store"]["comments"]
    assert s["unsent"]["comments"] == [c["id"] for c in cs]
    # what the panel builds from the status (file-comments-model.ts sendParts / describeComment)
    comments = [{"id": cs[0]["id"], "desc": "on this file", "body": "Which cache?"},
                {"id": cs[1]["id"], "desc": 'on "%s"' % cs[1]["anchor"]["quote"][:40], "body": "Say when, too."}]
    watermark = max(c["ts"] for c in cs)
    rep = world.ws({"type": "fileCommentsSend", "sid": SID, "path": str(world.fp), "tracked": False,
                    "comments": comments, "accepted": 0, "rejected": 0, "watermark": watermark, "todoId": world.tid})
    assert rep == {"type": "fileCommentsSent", "reqId": rep["reqId"], "queued": False}, rep
    assert "logWarning" not in rep and "warning" not in rep
    assert len(world.injected) == 1
    inj = world.injected[0]
    assert inj["text"] == expected_message(str(world.fp), comments, tracked=False)
    assert inj["text"] == km._file_comments_message(str(world.fp), comments, 0, 0, False, True)
    assert inj["sid"] == SID and inj["user_todo"] == world.tid
    assert world.todo()["resolved"]["kind"] == "answered"
    # the log's send entry is the watermark; unsent is derived from it, not from the browser
    s2 = world.ok("status", world.fp)
    assert s2["unsent"] == dict(EMPTY_UNSENT, watermark=watermark)
    entries = world.log_lines(s2)
    assert [e["kind"] for e in entries] == ["send"]
    e = entries[0]
    assert (e["author"], e["sid"], e["sessionName"], e["queued"], e["watermark"]) == ("you", SID, "web", False, watermark)
    assert e["comments"] == comments and (e["accepted"], e["rejected"]) == (0, 0)
    assert e["ts"].endswith("Z")
    assert s2["log"] == entries, "the status carries the parsed log, oldest first"
    # a later reply from the person is unsent again; a second send with tracked on names track-edit
    r3 = world.ok("reply", world.fp, {"commentId": cs[0]["id"], "note": "Also the header."}, world.fence_of(s2))
    assert r3["unsent"]["replies"] == [{"commentId": cs[0]["id"], "ts": r3["store"]["comments"][0]["replies"][0]["ts"]}]
    assert r3["unsent"]["comments"] == []
    world.ok("set-tracked", world.fp, {"on": True, "scope": "file"}, world.fence_of(r3))
    again = [{"id": cs[0]["id"], "desc": "on this file", "body": "Also the header."}]
    rep2 = world.ws({"type": "fileCommentsSend", "sid": SID, "path": str(world.fp), "tracked": True,
                     "comments": again, "accepted": 0, "rejected": 0, "watermark": r3["unsent"]["replies"][0]["ts"]})
    assert rep2["type"] == "fileCommentsSent" and "logWarning" not in rep2
    assert world.injected[1]["text"] == expected_message(str(world.fp), again, tracked=True)
    assert world.injected[1]["user_todo"] is None, "no todoId: nothing to stamp"
    s3 = world.ok("status", world.fp)
    assert s3["unsent"] == dict(EMPTY_UNSENT, watermark=r3["unsent"]["replies"][0]["ts"])
    assert [e["kind"] for e in s3["log"]] == ["send", "set-tracked", "send"]
    # nothing to send refuses before anything runs
    none = world.ws({"type": "fileCommentsSend", "sid": SID, "path": str(world.fp), "tracked": True,
                     "comments": [], "accepted": 0, "rejected": 0, "watermark": None})
    assert none["type"] == "fileCommentsSendFailed" and "nothing to send" in none["error"]
    assert len(world.injected) == 2


def test_set_tracked_on_then_off_with_the_config_fence_and_a_stale_fence_refusal(world):
    s = world.ok("status", world.fp)
    assert s["trackedBy"] is None and s["configMtimeNs"] is None
    cfg = world.root / ".trackchanges" / "config.json"
    on = world.ok("set-tracked", world.fp, {"on": True, "scope": "file"}, world.fence_of(s))
    assert on["trackedBy"] == {"kind": "file", "entry": "docs/report.md"}
    assert json.loads(cfg.read_text()) == {"v": 2, "tracked": ["docs/report.md"]}
    assert on["configMtimeNs"] == str(cfg.stat().st_mtime_ns)
    assert store_io(str(world.fp))["tracked"] is True, "the guard's own verdict agrees"
    assert store_io(str(world.other))["tracked"] is False
    # the browser that still holds the pre-toggle fence is refused, and nothing changes
    stale = world.op("set-tracked", world.fp, {"on": False}, world.fence_of(s))
    assert (stale["type"], stale["code"]) == ("fileCommentsFailed", "config-moved")
    assert "appeared on disk" in stale["error"] and "reload" in stale["error"]
    assert json.loads(cfg.read_text())["tracked"] == ["docs/report.md"]
    off = world.ok("set-tracked", world.fp, {"on": False}, world.fence_of(on))
    assert off["trackedBy"] is None
    assert json.loads(cfg.read_text())["tracked"] == []
    assert store_io(str(world.fp))["tracked"] is False
    # folder scope covers the file through its directory entry, and off removes that entry
    fon = world.ok("set-tracked", world.fp, {"on": True, "scope": "folder"}, world.fence_of(off))
    assert fon["trackedBy"] == {"kind": "folder", "entry": "docs/"}
    assert store_io(str(world.other))["tracked"] is True, "a folder entry tracks its siblings too"
    foff = world.ok("set-tracked", world.fp, {"on": False}, world.fence_of(fon))
    assert foff["trackedBy"] is None and json.loads(cfg.read_text())["tracked"] == []
    # a second stale fence: the config vanished from under a browser that believes it exists
    gone = world.op("set-tracked", world.fp, {"on": True, "scope": "file"},
                    {"storeMtimeNs": "", "configMtimeNs": "1"})
    assert (gone["type"], gone["code"]) == ("fileCommentsFailed", "config-moved")
    assert [(e["kind"], e["on"], e["scope"], e["entry"]) for e in world.log_lines(foff)] == [
        ("set-tracked", True, "file", "docs/report.md"), ("set-tracked", False, "file", "docs/report.md"),
        ("set-tracked", True, "folder", "docs/"), ("set-tracked", False, "folder", "docs/")]
    # the panel does not learn the refused attempts from the log: only writes are logged
    assert len(foff["log"]) == 4


def test_a_direct_edit_on_the_commented_file_is_logged_and_unrelated_saves_are_not(world):
    r = world.comment(world.fp, "Which cache?")
    ns = world.fp.stat().st_mtime_ns
    saved = world.ws({"type": "saveFile", "path": str(world.fp), "content": EDITED, "baseMtimeNs": str(ns)}, wait=False)
    assert saved["type"] == "fileSaved", saved
    assert saved["logged"] is True and "logWarning" not in saved
    assert world.fp.read_text() == EDITED
    assert saved["mtimeNs"] == str(world.fp.stat().st_mtime_ns)
    entries = world.log_lines(r)
    assert [e["kind"] for e in entries] == ["edit"]
    e = entries[0]
    assert e["author"] == "you"
    assert (e["mtimeBeforeNs"], e["mtimeAfterNs"]) == (str(ns), saved["mtimeNs"])
    assert (e["bytesBefore"], e["bytesAfter"]) == (len(TEXT.encode()), len(EDITED.encode()))
    assert "-The api session cut p95 latency by 40%.\n" in e["diff"]
    assert "+The api session cut p95 latency by 45%.\n" in e["diff"]
    assert e["truncated"] is False
    s = world.ok("status", world.fp)
    assert s["log"] == entries, "the panel's Log is current when the viewer hears the save"
    assert s["store"]["comments"][0]["body"] == "Which cache?", "the sidecar survived the direct edit"
    # a sibling inside the same project with no sidecar, log or tracked flag: the host says logged:false
    ons = world.other.stat().st_mtime_ns
    o = world.ws({"type": "saveFile", "path": str(world.other), "content": "# Other\n\nmore\n",
                  "baseMtimeNs": str(ons)}, wait=False)
    assert o["type"] == "fileSaved" and o["logged"] is False and "logWarning" not in o
    assert not (world.root / ".trackchanges" / "docs%2Fother.md.comments-log.jsonl").exists()
    assert not (world.root / ".trackchanges" / "docs%2Fother.md.json").exists(), "log-edit never creates a sidecar"
    # a file with no .trackchanges/ anywhere above it: logged:false without asking the host
    xns = world.outside.stat().st_mtime_ns
    x = world.ws({"type": "saveFile", "path": str(world.outside), "content": "scratch 2\n",
                  "baseMtimeNs": str(xns)}, wait=False)
    assert x["type"] == "fileSaved" and x["logged"] is False and "logWarning" not in x
    assert not (world.outside.parent / ".trackchanges").exists()
    # a tracked-but-uncommented file IS logged: the flag alone makes the file the log's business
    s2 = world.ok("status", world.other)
    world.ok("set-tracked", world.other, {"on": True, "scope": "file"}, world.fence_of(s2))
    o2 = world.ws({"type": "saveFile", "path": str(world.other), "content": "# Other\n\nmore\n\nand more\n",
                   "baseMtimeNs": str(world.other.stat().st_mtime_ns)}, wait=False)
    assert o2["type"] == "fileSaved" and o2["logged"] is True
    kinds = [e["kind"] for e in world.log_lines(world.ok("status", world.other))]
    assert kinds == ["set-tracked", "edit"]


def _guard(tool, file, env):
    """The guard as Claude Code runs it: a PreToolUse hook with the tool call's JSON on stdin."""
    return subprocess.run([NODE, GUARD], input=json.dumps({"tool_name": tool, "tool_input": {"file_path": str(file)}}),
                          capture_output=True, text=True, timeout=20, env=env)


def test_the_guard_denies_a_tracked_write_in_a_romp_session_and_stands_aside_otherwise(world):
    s = world.ok("status", world.fp)
    world.ok("set-tracked", world.fp, {"on": True, "scope": "file"}, world.fence_of(s))
    ps = world.ok("status", world.png)
    world.ok("set-tracked", world.png, {"on": True, "scope": "file"}, world.fence_of(ps))
    assert json.loads((world.root / ".trackchanges" / "config.json").read_text())["tracked"] == [
        "docs/report.md", "docs/figure.png"]
    romp = _env(ROMP_SID=SID)
    denied = _guard("Write", world.fp, romp)
    assert denied.returncode == 2, (denied.returncode, denied.stderr)
    assert "Track-changes is ON" in denied.stderr and "track-edit" in denied.stderr and str(world.fp) in denied.stderr
    assert denied.stdout == ""
    assert _guard("Edit", world.fp, romp).returncode == 2, "the matcher's other tools are denied too"
    assert _guard("Write", world.other, romp).returncode == 0, "an untracked file passes"
    passed = _guard("Write", world.png, romp)
    assert passed.returncode == 0 and passed.stderr == "", "a tracked image passes: track-edit would destroy it"
    assert _guard("Read", world.fp, romp).returncode == 0, "a read is never a write"
    # a session romp did not launch: exit 0 at once, before stdin is read (the pipe stays open)
    child = subprocess.Popen([NODE, GUARD], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             env=_env())
    try:
        out, err = None, None
        try:
            child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            child.kill()
            pytest.fail("without ROMP_SID the guard waited on stdin instead of exiting")
        assert child.returncode == 0
    finally:
        child.stdin.close()
        out, err = child.stdout.read(), child.stderr.read()
        child.stdout.close()
        child.stderr.close()
    assert out == b"" and err == b""
    # the file is still what it was: the guard only ever says no
    assert world.fp.read_text() == TEXT


# ── Slice 2: the session's changes, decided from the panel ───────────────────────────────────────────

EDITED_TWICE = EDITED.replace("shipping the cache", "shipping the response cache")


def test_track_edit_records_a_change_a_change_comment_binds_to_it_and_accept_resolves_the_comment_without_dropping_it(world):
    s0 = world.ok("status", world.fp)
    on = world.ok("set-tracked", world.fp, {"on": True, "scope": "file"}, world.fence_of(s0))
    assert on["trackedBy"] == {"kind": "file", "entry": "docs/report.md"}
    world.track_edit("cut p95 latency by 40%", "cut p95 latency by 45%")
    assert world.fp.read_text() == EDITED, "the file on disk is the current text, the change applied"
    s = world.ok("status", world.fp)
    assert len(s["hunks"]) == 1
    h = s["hunks"][0]
    assert h["kind"] in ("ins", "del", "sub") and h["kind"] == "sub", "the engine's three kinds (D1)"
    assert (h["oldText"], h["newText"], h["author"]) == ("cut p95 latency by 40%", "cut p95 latency by 45%", "web")
    assert EDITED[h["curFrom"]:h["curTo"]] == h["newText"], "offsets index the current text"
    assert s["store"]["suggestions"][0]["authorId"] == SID
    assert s["store"]["suggestions"][0]["id"] == h["id"]
    assert s["unsent"] == EMPTY_UNSENT, "the session's change is not the person's to send"
    # a change comment: bound by suggestionId, no anchor, no target
    c = world.ok("comment", world.fp, {"suggestionId": h["id"], "note": "Good; say what moved it."}, world.fence_of(s))
    cm = c["store"]["comments"][0]
    assert set(cm) == {"id", "author", "ts", "suggestionId", "body", "replies", "resolved"}
    assert (cm["suggestionId"], cm["author"], cm["body"], cm["resolved"]) == (h["id"], "you", "Good; say what moved it.", False)
    assert c["unsent"] == dict(EMPTY_UNSENT, comments=[cm["id"]])
    assert world.fp.read_text() == EDITED
    # a change that is not pending refuses no-change and writes nothing
    bad = world.op("comment", world.fp, {"suggestionId": "1-1", "note": "late"}, world.fence_of(c))
    assert (bad["type"], bad["code"]) == ("fileCommentsFailed", "no-change")
    assert "reload" in bad["error"]
    assert len(json.loads(Path(c["storePath"]).read_text())["comments"]) == 1
    # the session answers into the change comment with the vendored CLI
    rep = _node([TRACK_REPLY, "--file", str(world.fp), "--thread", cm["id"], "--note", "The retry budget."],
                env=_env(ROMP_SESSION_NAME="web", ROMP_SID=SID))
    assert rep.returncode == 0, rep.stderr
    s2 = world.ok("status", world.fp)
    bound = s2["store"]["comments"][0]
    assert [(r["author"], r["authorId"], r["body"]) for r in bound["replies"]] == [("web", SID, "The retry budget.")]
    assert bound["suggestionId"] == h["id"] and "anchor" not in bound
    assert [x["id"] for x in s2["hunks"]] == [h["id"]], "a reply moves no change"
    # accept: the sidecar only, fenced on its mtime alone; the file's bytes and mtime do not move
    text_before, ns_before = world.fp.read_bytes(), world.fp.stat().st_mtime_ns
    a = world.ok("accept", world.fp, {"ids": [h["id"]]}, world.fence_of(s2))
    assert a["accepted"] == [h["id"]] and "rejected" not in a
    assert a["hunks"] == []
    kept = a["store"]["comments"][0]
    assert (kept["id"], kept["suggestionId"], kept["resolved"]) == (cm["id"], h["id"], True), "resolved and kept, never dropped"
    assert [r["body"] for r in kept["replies"]] == ["The retry budget."]
    disk = json.loads(Path(a["storePath"]).read_text())
    assert disk["suggestions"] == [] and disk["comments"][0]["resolved"] is True and disk["v"] == 3
    assert world.fp.read_bytes() == text_before and world.fp.stat().st_mtime_ns == ns_before
    assert a["fileMtimeNs"] == str(ns_before)
    assert a["storeMtimeNs"] == str(Path(a["storePath"]).stat().st_mtime_ns) and a["storeMtimeNs"] != s2["storeMtimeNs"]
    assert a["unsent"] == dict(EMPTY_UNSENT, comments=[cm["id"]], accepted=1)
    assert [e["kind"] for e in a["log"]] == ["set-tracked", "accept"]
    assert a["log"][1]["author"] == "you"
    assert a["log"][1]["changes"] == [{"id": h["id"], "oldText": h["oldText"], "newText": h["newText"]}]
    assert world.traced == [] and world.injected == [], "a sidecar-only verb tells the session nothing"
    # the same id again: no longer pending
    again = world.op("accept", world.fp, {"ids": [h["id"]]}, world.fence_of(a))
    assert (again["type"], again["code"]) == ("fileCommentsFailed", "no-change")
    # the CLI still answers the resolved, bound comment the sent message would name
    rep2 = _node([TRACK_REPLY, "--file", str(world.fp), "--thread", cm["id"], "--note", "Noted."],
                 env=_env(ROMP_SESSION_NAME="web", ROMP_SID=SID))
    assert rep2.returncode == 0, rep2.stderr
    s3 = world.ok("status", world.fp)
    assert [r["body"] for r in s3["store"]["comments"][0]["replies"]] == ["The retry budget.", "Noted."]
    assert s3["store"]["comments"][0]["resolved"] is True


def test_reject_reverts_the_file_tells_the_owning_session_once_and_a_stale_file_fence_writes_nothing(world):
    s0 = world.ok("status", world.fp)
    world.ok("set-tracked", world.fp, {"on": True, "scope": "file"}, world.fence_of(s0))
    world.track_edit("cut p95 latency by 40%", "cut p95 latency by 45%")
    world.track_edit("shipping the cache", "shipping the response cache")
    assert world.fp.read_text() == EDITED_TWICE
    s = world.ok("status", world.fp)
    assert [h["oldText"] for h in s["hunks"]] == ["cut p95 latency by 40%", "shipping the cache"], "two changes, in text order"
    first, second = s["hunks"]
    # a whole-file comment, so the sidecar outlives the decisions (pruneIfClean keeps a commented sidecar)
    c = world.comment(world.fp, "Which cache?", fence=world.fence_of(s))
    cid = c["store"]["comments"][0]["id"]
    a = world.ok("accept", world.fp, {"ids": [first["id"]]}, world.fence_of(c))
    assert a["accepted"] == [first["id"]] and [h["id"] for h in a["hunks"]] == [second["id"]]
    text_before, sidecar_before = world.fp.read_bytes(), Path(a["storePath"]).read_bytes()
    # a stale file fence refuses file-moved: nothing written, nothing logged, nothing told
    stale = world.op("reject", world.fp, {"ids": [second["id"]]}, dict(world.fence_of(a), fileMtimeNs="1"))
    assert (stale["type"], stale["code"]) == ("fileCommentsFailed", "file-moved")
    assert "reload" in stale["error"]
    assert world.fp.read_bytes() == text_before and Path(a["storePath"]).read_bytes() == sidecar_before
    assert [e["kind"] for e in world.log_lines(a)] == ["set-tracked", "accept"]
    assert world.traced == []
    # the sidecar fence answers first when both are stale
    moved = world.op("reject", world.fp, {"ids": [second["id"]]}, {"storeMtimeNs": "", "configMtimeNs": "", "fileMtimeNs": "1"})
    assert (moved["type"], moved["code"]) == ("fileCommentsFailed", "store-moved")
    assert world.traced == [] and world.fp.read_bytes() == text_before
    # the reject: the second change's old text comes back, the accepted first stays
    r = world.ok("reject", world.fp, {"ids": [second["id"]]}, world.fence_of(a, file=True))
    assert r["rejected"] == [second["id"]] and "accepted" not in r
    assert r["hunks"] == []
    assert world.fp.read_text() == EDITED
    assert r["fileMtimeNs"] == str(world.fp.stat().st_mtime_ns) and r["fileMtimeNs"] != a["fileMtimeNs"], "the file's mtime moved"
    assert r["storeMtimeNs"] == str(Path(r["storePath"]).stat().st_mtime_ns) and r["storeMtimeNs"] != a["storeMtimeNs"], "the sidecar's too"
    assert r["store"]["suggestions"] == [] and [x["body"] for x in r["store"]["comments"]] == ["Which cache?"]
    assert r["unsent"] == dict(EMPTY_UNSENT, comments=[cid], accepted=1, rejected=1)
    # exactly one trace, to the session whose tree holds the file, after the reply, in the contract's words (D3)
    real = os.path.realpath(str(world.fp))
    assert world.traced == [(SID, km._reject_trace_body(real, 1))]
    body = world.traced[0][1]
    assert body.startswith("I rejected 1 of your tracked changes in %s while reading it; the file and its sidecar both "
                           "changed, so re-read it before writing." % km._tilde(real))
    assert "romp-injected" in body
    assert world.injected == [], "a trace is a direct backend send: nothing parked, no todo stamped"
    assert world.order[-2:] == ["reply", "trace"], "the fileCommentsResult is on the wire before the trace goes"
    # the log holds both decisions with their texts, and unsent counts them until a send
    entries = world.log_lines(r)
    assert [e["kind"] for e in entries] == ["set-tracked", "accept", "reject"]
    assert entries[1]["changes"] == [{"id": first["id"], "oldText": first["oldText"], "newText": first["newText"]}]
    assert entries[2]["changes"] == [{"id": second["id"], "oldText": second["oldText"], "newText": second["newText"]}]
    assert all(e["author"] == "you" and e["ts"].endswith("Z") for e in entries[1:])
    comments = [{"id": cid, "desc": "on this file", "body": "Which cache?"}]
    watermark = c["store"]["comments"][0]["ts"]
    rep = world.ws({"type": "fileCommentsSend", "sid": SID, "path": str(world.fp), "tracked": True,
                    "comments": comments, "accepted": 1, "rejected": 1, "watermark": watermark})
    assert rep["type"] == "fileCommentsSent", rep
    msg = world.injected[-1]["text"]
    assert msg == km._file_comments_message(str(world.fp), comments, 1, 1, True, True)
    assert "\nI accepted 1 of your changes and rejected 1.\n\n" in msg
    s3 = world.ok("status", world.fp)
    assert s3["unsent"] == dict(EMPTY_UNSENT, watermark=watermark), "the send entry resets the counts"
    assert s3["log"][-1]["kind"] == "send" and (s3["log"][-1]["accepted"], s3["log"][-1]["rejected"]) == (1, 1)
    assert len(world.traced) == 1, "a send is not a trace"


def test_accept_all_on_a_sidecar_with_no_comments_prunes_it_and_the_log_keeps_the_decision(world):
    s0 = world.ok("status", world.fp)
    world.ok("set-tracked", world.fp, {"on": True, "scope": "file"}, world.fence_of(s0))
    world.track_edit("cut p95 latency by 40%", "cut p95 latency by 45%")
    s = world.ok("status", world.fp)
    store_path = Path(s["storePath"])
    assert store_path.exists() and s["store"]["comments"] == []
    h = s["hunks"][0]
    a = world.ok("accept-all", world.fp, {}, world.fence_of(s))
    assert a["accepted"] == [h["id"]]
    assert (a["store"], a["storeMtimeNs"], a["hunks"]) == (None, None, []), "the client's absent state"
    assert a["storePath"] == s["storePath"] and not store_path.exists(), "pruneIfClean removed the emptied sidecar"
    assert world.fp.read_text() == EDITED and a["fileMtimeNs"] == s["fileMtimeNs"]
    assert world.log_path(a).exists(), "the log outlives the sidecar"
    assert [e["kind"] for e in a["log"]] == ["set-tracked", "accept"]
    assert a["unsent"] == dict(EMPTY_UNSENT, accepted=1)
    assert world.traced == [] and world.injected == []
    s2 = world.ok("status", world.fp)
    assert (s2["store"], s2["storeMtimeNs"]) == (None, None) and s2["unsent"]["accepted"] == 1
    none = world.op("accept-all", world.fp, {}, world.fence_of(s2))
    assert (none["type"], none["code"]) == ("fileCommentsFailed", "no-change")
    assert not store_path.exists(), "a refused decision creates nothing"
    # the session's next edit starts a fresh sidecar; reject-all of it goes back to the absent state, with a trace
    world.track_edit("cut p95 latency by 45%", "cut p95 latency by 50%")
    s3 = world.ok("status", world.fp)
    assert len(s3["hunks"]) == 1 and store_path.exists()
    r = world.ok("reject-all", world.fp, {}, world.fence_of(s3, file=True))
    assert r["rejected"] == [s3["hunks"][0]["id"]]
    assert (r["store"], r["storeMtimeNs"], r["hunks"]) == (None, None, []) and not store_path.exists()
    assert world.fp.read_text() == EDITED
    assert world.traced == [(SID, km._reject_trace_body(os.path.realpath(str(world.fp)), 1))]
    assert [e["kind"] for e in world.log_lines(r)] == ["set-tracked", "accept", "reject"]
    assert r["unsent"] == dict(EMPTY_UNSENT, accepted=1, rejected=1)

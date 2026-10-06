"""The Python half of the served drivers' result protocol: one reader for every driver's record (2026-10-06).

WHY. A served driver used to print its whole record on stdout, and every module parsed it its own way. Loading playwright
leaves the driver's stdout non-blocking, so one fs.writeSync of a record to a pipe delivered what the pipe had room for
(8 KiB on a loaded machine) and the module read a cut line. Now the driver writes its record to a file this module
names and prints one short line naming it, through tests/lab_result.cjs (whose header states the protocol and the JS API),
and this module reads it back. Pinned by tests/test_lab_result.py (every refusal below, on synthetic streams and files) and
tests/test_lab_result_pipe_served.py (the two halves together, a 96 KiB record through an 8 KiB non-blocking pipe).

THE API.
  target(lab, name="result")
      The target of ONE drive: {"resultPath": <lab>/result-<name>.json, "resultNonce": a fresh random hex string,
      "resultLib": the absolute path of tests/lab_result.cjs}. Call it once per drive, right before the drive, and hand it
      to the driver in its cfg with cfg.update(tgt) (not ** inside the dict literal: a module whose cfg is read as a dict
      literal of string-constant keys stays readable). `name` keeps two drives of one lab apart (an engine, a tag); it is
      letters, digits, dot, dash and underscore.
  env(tgt)
      {"LAB_RESULT": <the target as JSON>}: the target for a driver that takes no cfg, merged into the driver's
      environment (env=dict(os.environ, ..., **lab_result.env(tgt))). The driver reads it with targetFromEnv().
  read(p, tgt)
      The record the drive wrote, from `p`, anything with .stdout and .stderr (a CompletedProcess from
      subprocess.run(..., capture_output=True), text or bytes; a Popen whose two attributes the caller set after
      communicate()). Raises ResultError, with both streams' tails, when stdout holds no RESULT: line or more than one,
      the line is not JSON, it reports a write error (with the died reason when the line carries one), it names another
      file, or it carries another nonce; when the file is missing (with the died reason), not JSON, or holds another
      drive's nonce (a stale file); or when the file holds no record. Leaves the exit status to the caller: check it
      first (exit 3, the skip, writes no line; a crash writes none either, and its streams say more than this reader
      would). Leaves the record's own fields to the caller too, `died` among them.
  ResultError
      An AssertionError, so a module that reads in a test body reports a failure, not an error; a module that keeps a
      setUpClass error string catches it: `except lab_result.ResultError as e: cls.driver_error = str(e)`.
  LIB, PREFIX
      The helper's absolute path, and "RESULT:".
"""
import json
import os
import re
import secrets

LIB = os.path.join(os.path.dirname(os.path.realpath(__file__)), "lab_result.cjs")
PREFIX = "RESULT:"
TAIL = 1500
_NAME = re.compile(r"[A-Za-z0-9_.-]+")


class ResultError(AssertionError):
    """The drive handed back no record this reader can trust; the message says why, with both streams' tails."""


def target(lab, name="result"):
    if not isinstance(name, str) or not _NAME.fullmatch(name) or name in (".", ".."):
        raise ValueError("a result name is letters, digits, dot, dash and underscore: %r" % (name,))
    return {"resultPath": os.path.join(lab, "result-%s.json" % name), "resultNonce": secrets.token_hex(8), "resultLib": LIB}


def env(tgt):
    return {"LAB_RESULT": json.dumps(tgt)}


def _text(v):
    if v is None:
        return ""
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return v


def read(p, tgt):
    out, err = _text(getattr(p, "stdout", None)), _text(getattr(p, "stderr", None))
    path, nonce = tgt["resultPath"], tgt["resultNonce"]

    def fail(why):
        raise ResultError("%s\n--- driver stdout tail:\n%s\n--- driver stderr tail:\n%s" % (why, out[-TAIL:], err[-TAIL:]))

    # split on line feeds only: str.splitlines also splits at U+2028 and friends, which JSON.stringify leaves raw
    lines = [ln.rstrip("\r") for ln in out.split("\n") if ln.startswith(PREFIX)]
    if len(lines) != 1:
        fail("the driver printed %d %s lines on stdout, not exactly one (tests/lab_result.cjs writeResult, once per drive)"
             % (len(lines), PREFIX))
    try:
        head = json.loads(lines[0][len(PREFIX):])
    except ValueError:
        head = None
    if not isinstance(head, dict):
        fail("the %s line is not a JSON object: %r" % (PREFIX, lines[0][:300]))
    if head.get("resultWriteError"):
        fail("the driver could not write its record to %r: %s (died: %r)" % (head.get("resultPath"), head["resultWriteError"], head.get("died")))
    if head.get("resultPath") != path:
        fail("the %s line names %r, not this drive's file %r" % (PREFIX, head.get("resultPath"), path))
    if head.get("nonce") != nonce:
        fail("the %s line carries nonce %r, not this drive's %r" % (PREFIX, head.get("nonce"), nonce))
    envelope, why = None, None   # the reasons are raised outside the handlers, so a ResultError carries no chained traceback
    try:
        with open(path, encoding="utf-8") as f:
            envelope = json.load(f)
    except FileNotFoundError:
        why = "the driver wrote no result file at %s (died: %r)" % (path, head.get("died"))
    except (OSError, ValueError) as e:
        why = "the result file %s is not readable JSON: %s" % (path, e)
    if why:
        fail(why)
    if not isinstance(envelope, dict) or envelope.get("nonce") != nonce:
        fail("the result file %s holds another drive's record (nonce %r, this drive's %r): a stale file"
             % (path, envelope.get("nonce") if isinstance(envelope, dict) else None, nonce))
    if "record" not in envelope:
        fail("the result file %s holds no record" % path)
    return envelope["record"]

#!/usr/bin/env python3
"""The request routes' HTTP answers, pinned across the refusal matrix (plans/user-todos.md).

POST /usertodo and POST /usertodo/withdraw answer through _user_todo_register_route and _user_todo_withdraw_route, the
one implementation for every road a request arrives by: the postal bus's add_user_todo and withdraw_user_todo (a POST
as the calling session) and the Codex postal tools (the kernel calling the same function as the thread's session). A
change to a check, its order, its status or its wording in either function reaches every road at once, so the HTTP
road's answers are pinned here as a table: one row per input the routes distinguish, the status and the exact body
(placeholders for what a run mints: `ut-<n>` for a minted id by first appearance, `<T>` for a ten-digit epoch), the
pusher wake (the ack-fast contract: a saved change wakes _push_soon once, a refusal never), whether the store was
written, the store's content after a write, and the body a remote forward carried. The ordering rows send an input
that fails two checks at once and pin which answer wins; the order is a contract the bus's wording relies on (the sid
check before the switch and the forward, the caps before the forward, the switch before the forward, the forward
before the store guard).

The table was first run as a differential when the two route bodies moved out of Handler.do_POST into the functions
(the same rows through the handler before and after, byte-identical answers), and stays as the golden the lift and
any later road are held to. Driven through the REAL do_POST dispatcher over test_user_todos' fake-socket harness, in a
fresh state root per row, with the remote forward's boundary (_host_for_sid, _remote_forward_status) mocked the way
that module mocks it. Synthetic fixtures only: this module's private placeholder sids, the notes-api demo world.
"""
import contextlib
import inspect
import io
import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
import test_user_todos as tut  # noqa: E402  the kernel under its harness name and the fake-socket driver

km, jd = tut.km, tut.jd
REG, WD = "/usertodo", "/usertodo/withdraw"
# this module's private synthetic sids (the fixture rule: never the shared placeholder)
SID = "5c5c5c5c-1111-4222-8333-944444444401"
PEER = "5c5c5c5c-1111-4222-8333-944444444402"
NOW = 1781200000
LINE = "Need the auth-scheme decision to wire login"
TEXT_CAP, DETAIL_CAP = km._USER_TODO_TEXT_CAP, km._USER_TODO_DETAIL_CAP
# fixed ids carry a letter outside the hex range, so the normalizer leaves them alone
SEEDED, UNKNOWN, REMOTE_ID = "ut-seed0001", "ut-nosuch01", "ut-remote01"
OFF = km._USER_TODOS_OFF_ERR
UNREADABLE = km._USER_TODOS_UNREADABLE_ERR
REMOTE_ROW = {"host": "TESTHOST", "local_port": 1, "token": "t"}
NAMELESS_ROW = {"local_port": 1}
FLAGGED = {"enabled": True, "gt": 1}                # a settings blob where the store should be: the shape guard flags it
CAP_TEXT = ("text is %d characters, over the %d-character cap: keep the request to one line and put the rest in your reply"
            % (TEXT_CAP + 1, TEXT_CAP))
CAP_DETAIL = ("detail is %d characters, over the %d-character cap: keep the request to one line and put the rest in your reply"
              % (DETAIL_CAP + 1, DETAIL_CAP))
MALFORMED = "malformed closing stamp on %s: resolved=%s (a stamp is {kind: answered | dismissed | withdrawn, t})"


def _row(text=LINE, tid="ut-<1>", **extra):
    """One stored row as the store serializes it (sort_keys): the fields in key order, the epoch a placeholder."""
    d = dict(extra, createdT="<T>", id=tid, text=text)
    return "{" + ", ".join('"%s": %s' % (k, v if k == "createdT" or k == "resolved" else json.dumps(v))
                           for k, v in sorted(d.items())) + "}"


WITHDRAWN = '{"kind": "withdrawn", "t": <T>}'


def _store(**by_sid):
    """The store file as the writer publishes it (sort_keys, default separators), sids in key order."""
    return "{" + ", ".join('"%s": [%s]' % (k, ", ".join(v)) for k, v in sorted(by_sid.items())) + "}"


# --------------------------------------------------------------------------------------------------- seeds
def seed_own_open(ctx):
    ctx["tid"] = km._add_user_todo(SID, LINE)


def seed_two_open(ctx):
    ctx["tid"] = km._add_user_todo(SID, LINE)
    km._add_user_todo(SID, "Need a staging API key")


def seed_peer_open(ctx):
    ctx["tid"] = km._add_user_todo(PEER, "api: need the auth decision")


def seed_stamped(kind):
    def _s(ctx):
        ctx["tid"] = km._add_user_todo(SID, LINE)
        assert km._resolve_user_todo(SID, ctx["tid"], kind)
    return _s


def seed_withdrawn_once(ctx):
    ctx["tid"] = km._add_user_todo(SID, LINE)
    assert tut._serve_post(WD, {"id": SID, "todoId": ctx["tid"]}, {"X-Romp-Token": km.TOKEN})[0] == 200


def seed_file(obj):
    """Write the store file by hand and drop the caches, as test_user_todos seeds rows."""
    def _s(ctx):
        (jd.STATE / "user-todos.json").write_text(obj if isinstance(obj, str) else json.dumps(obj))
        km._user_todos_cache.clear(); km._user_todos_bad.clear()
    return _s


def seed_resolved(resolved):
    return seed_file({SID: [{"id": SEEDED, "text": LINE, "createdT": NOW - 60, "resolved": resolved}]})


def seed_flagged_after_row(ctx):
    ctx["tid"] = km._add_user_todo(SID, LINE)
    seed_file(FLAGGED)(ctx)


def by_tid(c):
    return {"id": SID, "todoId": c["tid"]}


# --------------------------------------------------------------------------------------------------- the table
def case(name, path, body, status, answer, *, token=True, switch=True, seed=None, remote=None, row=None,
         patch=None, pushed=0, fwd=None, written=False, store=None):
    """One row: the request (a dict, raw bytes, or a callable of the seed's ctx), the expected status and body text,
    and the side effects expected of it. `remote` is the (status, parsed body) the mocked forward answers, `row`
    the remote row _host_for_sid names (the standard one unless given), `fwd` the exact forwarded calls expected
    (None: no forward may happen), `patch` a (name, replacement) on the kernel module."""
    return dict(name=name, path=path, body=body, status=status, answer=answer, token=token, switch=switch, seed=seed,
                remote=remote, row=row, patch=patch, pushed=pushed, fwd=fwd, written=written, store=store)


def _reg(name, body, status, answer, **kw):
    return case(name, REG, body, status, answer, **kw)


def _wd(name, body, status, answer, **kw):
    return case(name, WD, body, status, answer, **kw)


def _err(text):
    return '{"ok": false, "error": %s}' % json.dumps(text)


def _bad_remote(why, host="TESTHOST"):
    return '{"ok": false, "error": %s, "host": %s}' % (json.dumps(why % host if "%s" in why else why), json.dumps(host))


def _acct(state, at, owner, error="no open request with that id"):
    return '{"error": %s, "ok": false, "state": "%s", "at": %s, "owner": %s}' % (
        json.dumps(error), state, at, json.dumps(owner))


SAVED = '{"ok": true, "todoId": "ut-<1>"}'
FILED = _store(**{SID: [_row()]})
REMOTE_SAVED = '{"ok": true, "todoId": "%s"}' % REMOTE_ID
ONE_FWD = [[REG, {"id": SID, "text": LINE, "detail": "", "blocking": False}]]
WD_FWD = [[WD, {"id": SID, "todoId": REMOTE_ID}]]
WITHDREW = '{"ok": true, "state": "withdrawn", "at": <T>, "owner": true}'
AFTER_WITHDRAW = _store(**{SID: [_row(resolved=WITHDRAWN)]})

REGISTER = [
    # the handler's own gates, before the route
    _reg("no token", {"id": SID, "text": LINE}, 403, None, token=False),
    _reg("body not JSON", b"not json", 400, _err("body is not JSON")),
    _reg("body a JSON list", b"[1, 2]", 400, _err("body must be a JSON object, got [1, 2]")),
    _reg("body a JSON string", b'"a string"', 400, _err('body must be a JSON object, got "a string"')),
    _reg("body empty", b"", 400, _err("id and text required")),
    # shape
    _reg("no id", {"text": LINE}, 400, _err("id and text required")),
    _reg("no text", {"id": SID}, 400, _err("id and text required")),
    _reg("whitespace text", {"id": SID, "text": "   "}, 400, _err("id and text required")),
    _reg("numeric text is str()ed", {"id": SID, "text": 123}, 200, SAVED, pushed=1, written=True,
         store=_store(**{SID: [_row("123")]})),
    _reg("numeric id is str()ed and is a safe id", {"id": 123, "text": LINE}, 200, SAVED, pushed=1, written=True,
         store=_store(**{"123": [_row()]})),
    _reg("id with a slash", {"id": "web/" + SID, "text": LINE}, 400, _err("id must be a session id")),
    _reg("id with a leading dot", {"id": "." + SID, "text": LINE}, 400, _err("id must be a session id")),
    _reg("id of 129 chars", {"id": "a" * 129, "text": LINE}, 400, _err("id must be a session id")),
    _reg("id with a trailing newline", {"id": SID + "\n", "text": LINE}, 400, _err("id must be a session id")),
    _reg("blocking the string true", {"id": SID, "text": LINE, "blocking": "true"}, 400,
         _err("'blocking' must be true or false, got \"true\"")),
    _reg("blocking 1", {"id": SID, "text": LINE, "blocking": 1}, 400, _err("'blocking' must be true or false, got 1")),
    _reg("blocking a list", {"id": SID, "text": LINE, "blocking": [True]}, 400,
         _err("'blocking' must be true or false, got [true]")),
    _reg("blocking null is the absent case", {"id": SID, "text": LINE, "blocking": None}, 200, SAVED, pushed=1,
         written=True, store=FILED),
    _reg("blocking false stores no key", {"id": SID, "text": LINE, "blocking": False}, 200, SAVED, pushed=1,
         written=True, store=FILED),
    _reg("blocking true lands on the row", {"id": SID, "text": LINE, "blocking": True}, 200, SAVED, pushed=1,
         written=True, store=_store(**{SID: [_row(blocking=True)]})),
    # the switch
    _reg("switch off", {"id": SID, "text": LINE}, 409, _err(OFF), switch=False),
    # the caps
    _reg("text at the cap", {"id": SID, "text": "N" * TEXT_CAP}, 200, SAVED, pushed=1, written=True),
    _reg("text one over the cap", {"id": SID, "text": "n" * (TEXT_CAP + 1)}, 400, _err(CAP_TEXT)),
    _reg("text one over the cap after the strip", {"id": SID, "text": " " + "n" * (TEXT_CAP + 1) + " "}, 400, _err(CAP_TEXT)),
    _reg("detail at the cap", {"id": SID, "text": LINE, "detail": "d" * DETAIL_CAP}, 200, SAVED, pushed=1, written=True),
    _reg("detail one over the cap", {"id": SID, "text": LINE, "detail": "x" * (DETAIL_CAP + 1)}, 400, _err(CAP_DETAIL)),
    # the success shapes
    _reg("text only", {"id": SID, "text": LINE}, 200, SAVED, pushed=1, written=True, store=FILED),
    _reg("text and detail", {"id": SID, "text": LINE, "detail": "OAuth vs cookie"}, 200, SAVED, pushed=1, written=True,
         store=_store(**{SID: [_row(detail="OAuth vs cookie")]})),
    _reg("text, detail and blocking", {"id": SID, "text": LINE, "detail": "8443?", "blocking": True}, 200, SAVED, pushed=1,
         written=True, store=_store(**{SID: [_row(blocking=True, detail="8443?")]})),
    _reg("whitespace detail stores no key", {"id": SID, "text": LINE, "detail": "   "}, 200, SAVED, pushed=1, written=True,
         store=FILED),
    _reg("padded text is stored stripped", {"id": SID, "text": "  Need the port  "}, 200, SAVED, pushed=1, written=True,
         store=_store(**{SID: [_row("Need the port")]})),
    _reg("a second row in the session", {"id": SID, "text": "Need a staging API key"}, 200, '{"ok": true, "todoId": "ut-<2>"}',
         seed=seed_own_open, pushed=1, written=True,
         store=_store(**{SID: [_row(), _row("Need a staging API key", "ut-<2>")]})),
    _reg("extra keys are ignored", {"id": SID, "text": LINE, "extra": 1, "todoId": "x"}, 200, SAVED, pushed=1, written=True,
         store=FILED),
    # the remote forward: the answer's status says what happened over there
    _reg("remote answers 200 with an id", {"id": SID, "text": LINE, "detail": "8443?", "blocking": True}, 200, REMOTE_SAVED,
         remote=(200, {"ok": True, "todoId": REMOTE_ID}),
         fwd=[[REG, {"id": SID, "text": LINE, "detail": "8443?", "blocking": True}]]),
    _reg("remote: the forwarded body carries detail and blocking even when absent", {"id": SID, "text": LINE}, 200,
         REMOTE_SAVED, remote=(200, {"ok": True, "todoId": REMOTE_ID}), fwd=ONE_FWD),
    _reg("remote 200 with an id and no ok", {"id": SID, "text": LINE}, 200, REMOTE_SAVED,
         remote=(200, {"todoId": REMOTE_ID}), fwd=ONE_FWD),
    _reg("remote answers 409: that machine's switch", {"id": SID, "text": LINE}, 409,
         '{"ok": false, "host": "TESTHOST", "error": "requests from sessions are turned off on TESTHOST"}',
         remote=(409, None), fwd=ONE_FWD),
    _reg("remote tunnel dead", {"id": SID, "text": LINE}, 502, _bad_remote("the tunnel to %s is not answering (re-dialing)"),
         remote=(0, None), fwd=ONE_FWD),
    _reg("remote predates the route", {"id": SID, "text": LINE}, 502,
         _bad_remote("the kernel on %s predates /usertodo: update romp there and restart it"), remote=(404, None), fwd=ONE_FWD),
    _reg("remote answers HTTP 500", {"id": SID, "text": LINE}, 502, _bad_remote("the kernel on %s answered HTTP 500"),
         remote=(500, None), fwd=ONE_FWD),
    _reg("remote 200 without an id", {"id": SID, "text": LINE}, 502,
         _bad_remote("the kernel on %s answered without a request id"), remote=(200, {"ok": False}), fwd=ONE_FWD),
    _reg("remote 200 not JSON", {"id": SID, "text": LINE}, 502, _bad_remote("the kernel on %s answered without a request id"),
         remote=(200, None), fwd=ONE_FWD),
    _reg("remote 200 with an empty id", {"id": SID, "text": LINE}, 502,
         _bad_remote("the kernel on %s answered without a request id"), remote=(200, {"ok": True, "todoId": ""}), fwd=ONE_FWD),
    _reg("remote row without a host name", {"id": SID, "text": LINE}, 502,
         _bad_remote("the tunnel to %s is not answering (re-dialing)", "that host"), remote=(0, None), row=NAMELESS_ROW,
         fwd=ONE_FWD),
    # the store's shape guard and the writer's own refusals
    _reg("flagged store: a settings blob", {"id": SID, "text": LINE}, 503, _err(UNREADABLE), seed=seed_file(FLAGGED)),
    _reg("flagged store: unparsable", {"id": SID, "text": LINE}, 503, _err(UNREADABLE), seed=seed_file("not json")),
    _reg("the writer's own ValueError is the 400 body", {"id": SID, "text": LINE}, 400, _err("the writer's own refusal"),
         patch=("_add_user_todo", mock.Mock(side_effect=ValueError("the writer's own refusal")))),
    _reg("the store goes bad under the check", {"id": SID, "text": LINE}, 503, _err(UNREADABLE),
         patch=("_write_user_todos", mock.Mock(side_effect=RuntimeError("write refused")))),
]

REGISTER_ORDER = [
    _reg("sid before the switch and the forward", {"id": "web/" + SID, "text": LINE}, 400, _err("id must be a session id"),
         switch=False, remote=(200, {"ok": True, "todoId": REMOTE_ID})),
    _reg("switch before the caps", {"id": SID, "text": "n" * (TEXT_CAP + 1)}, 409, _err(OFF), switch=False),
    _reg("blocking before the switch", {"id": SID, "text": LINE, "blocking": "true"}, 400,
         _err("'blocking' must be true or false, got \"true\""), switch=False),
    _reg("caps before the forward", {"id": SID, "text": "n" * (TEXT_CAP + 1)}, 400, _err(CAP_TEXT),
         remote=(200, {"ok": True, "todoId": REMOTE_ID})),
    _reg("presence before the sid's shape", {"id": "web/" + SID}, 400, _err("id and text required")),
    _reg("the forward before the store guard", {"id": SID, "text": LINE}, 200, REMOTE_SAVED,
         remote=(200, {"ok": True, "todoId": REMOTE_ID}), seed=seed_file(FLAGGED), fwd=ONE_FWD),
    _reg("switch before the store guard", {"id": SID, "text": LINE}, 409, _err(OFF), switch=False, seed=seed_file(FLAGGED)),
    _reg("switch before the forward", {"id": SID, "text": LINE}, 409, _err(OFF), switch=False,
         remote=(200, {"ok": True, "todoId": REMOTE_ID})),
    _reg("blocking before the forward", {"id": SID, "text": LINE, "blocking": "true"}, 400,
         _err("'blocking' must be true or false, got \"true\""), remote=(200, {"ok": True, "todoId": REMOTE_ID})),
    _reg("auth before the body parse", b"not json", 403, None, token=False),
]

WITHDRAW = [
    # the handler's own gates, then shape
    _wd("no token", {"id": SID, "todoId": UNKNOWN}, 403, None, token=False),
    _wd("body not JSON", b"not json", 400, _err("body is not JSON")),
    _wd("body a JSON list", b"[1, 2]", 400, _err("body must be a JSON object, got [1, 2]")),
    _wd("body empty", b"", 400, _err("id and todoId required")),
    _wd("no id", {"todoId": UNKNOWN}, 400, _err("id and todoId required")),
    _wd("no todoId", {"id": SID}, 400, _err("id and todoId required")),
    _wd("empty todoId", {"id": SID, "todoId": ""}, 400, _err("id and todoId required")),
    # the switch: nothing stamped, the row stays open
    _wd("switch off with an own open row", by_tid, 409, _err(OFF), switch=False, seed=seed_own_open),
    # the account
    _wd("unknown id, empty store", {"id": SID, "todoId": UNKNOWN}, 200, _acct("unknown", "null", False)),
    _wd("own open row", by_tid, 200, WITHDREW, seed=seed_own_open, pushed=1, written=True, store=AFTER_WITHDRAW),
    _wd("own open row, a second row stays open", by_tid, 200, WITHDREW, seed=seed_two_open, pushed=1, written=True,
        store=_store(**{SID: [_row(resolved=WITHDRAWN), _row("Need a staging API key", "ut-<2>")]})),
    _wd("repeat withdraw accounts the first stamp", by_tid, 200, _acct("withdrawn", "<T>", True), seed=seed_withdrawn_once),
    _wd("answered row", by_tid, 200, _acct("answered", "<T>", True), seed=seed_stamped("answered")),
    _wd("dismissed row", by_tid, 200, _acct("dismissed", "<T>", True), seed=seed_stamped("dismissed")),
    _wd("a peer's row is unknown to the asker", by_tid, 200, _acct("unknown", "null", False), seed=seed_peer_open),
    _wd("unknown id beside an own row", {"id": SID, "todoId": UNKNOWN}, 200, _acct("unknown", "null", False), seed=seed_own_open),
    _wd("malformed stamp: true", {"id": SID, "todoId": SEEDED}, 200,
        _acct("unknown", "null", True, MALFORMED % (SEEDED, "True")), seed=seed_resolved(True)),
    _wd("malformed stamp: an unknown kind", {"id": SID, "todoId": SEEDED}, 200,
        _acct("unknown", "null", True, MALFORMED % (SEEDED, "{'kind': 'lost', 't': 1781200000}")),
        seed=seed_resolved({"kind": "lost", "t": NOW})),
    _wd("a seeded stamp's own epoch", {"id": SID, "todoId": SEEDED}, 200, _acct("answered", "<T>", True),
        seed=seed_resolved({"kind": "answered", "t": NOW})),
    _wd("a stamp whose t is a string: at null", {"id": SID, "todoId": SEEDED}, 200, _acct("answered", "null", True),
        seed=seed_resolved({"kind": "answered", "t": "1781200000"})),
    _wd("resolved {} reads as open and is stamped", {"id": SID, "todoId": SEEDED}, 200, WITHDREW, seed=seed_resolved({}),
        pushed=1, written=True, store=_store(**{SID: [_row(tid=SEEDED, resolved=WITHDRAWN)]})),
    _wd("flagged store: owner null, the cause named", {"id": SID, "todoId": SEEDED}, 200,
        _acct("unknown", "null", None, UNREADABLE), seed=seed_file(FLAGGED)),
    _wd("flagged store after an own row", by_tid, 200, _acct("unknown", "null", None, UNREADABLE), seed=seed_flagged_after_row),
    _wd("the store goes bad under the account", by_tid, 503, _err(UNREADABLE), seed=seed_own_open,
        patch=("_write_user_todos", mock.Mock(side_effect=RuntimeError("write refused")))),
    _wd("a malformed sid has no shape check here: unknown", {"id": "web/" + SID, "todoId": UNKNOWN}, 200,
        _acct("unknown", "null", False)),
    _wd("extra keys are ignored", lambda c: dict(by_tid(c), text="x", blocking="true"), 200, WITHDREW, seed=seed_own_open,
        pushed=1, written=True, store=AFTER_WITHDRAW),
    # the remote forward: the account rides through when the remote gives one
    _wd("remote 200 ok true", {"id": SID, "todoId": REMOTE_ID}, 200, '{"ok": true}', remote=(200, {"ok": True}), fwd=WD_FWD),
    _wd("remote 200 with the full account", {"id": SID, "todoId": REMOTE_ID}, 200,
        '{"ok": false, "state": "answered", "at": <T>, "owner": true}',
        remote=(200, {"ok": False, "state": "answered", "at": NOW, "owner": True}), fwd=WD_FWD),
    _wd("remote 200: an extra key is dropped", {"id": SID, "todoId": REMOTE_ID}, 200,
        '{"ok": true, "state": "withdrawn", "at": <T>, "owner": true}',
        remote=(200, {"ok": True, "state": "withdrawn", "at": NOW, "owner": True, "extra": 1}), fwd=WD_FWD),
    _wd("remote 200 with an error", {"id": SID, "todoId": REMOTE_ID}, 200,
        '{"ok": false, "state": "unknown", "at": null, "owner": true, "error": "malformed closing stamp on ut-remote01"}',
        remote=(200, {"ok": False, "state": "unknown", "at": None, "owner": True,
                      "error": "malformed closing stamp on ut-remote01"}), fwd=WD_FWD),
    _wd("remote 200 empty object: ok false, nothing invented", {"id": SID, "todoId": REMOTE_ID}, 200, '{"ok": false}',
        remote=(200, {}), fwd=WD_FWD),
    _wd("remote 200 ok as a string is bool()ed", {"id": SID, "todoId": REMOTE_ID}, 200, '{"ok": true}',
        remote=(200, {"ok": "yes"}), fwd=WD_FWD),
    _wd("remote 200 not JSON", {"id": SID, "todoId": REMOTE_ID}, 502,
        _bad_remote("the kernel on %s answered a body that is not JSON"), remote=(200, None), fwd=WD_FWD),
    _wd("remote 200 a list", {"id": SID, "todoId": REMOTE_ID}, 502,
        _bad_remote("the kernel on %s answered a body that is not JSON"), remote=(200, [1, 2]), fwd=WD_FWD),
    _wd("remote tunnel dead", {"id": SID, "todoId": REMOTE_ID}, 502, _bad_remote("the tunnel to %s is not answering (re-dialing)"),
        remote=(0, None), fwd=WD_FWD),
    _wd("remote predates the route", {"id": SID, "todoId": REMOTE_ID}, 502,
        _bad_remote("the kernel on %s predates /usertodo/withdraw: update romp there and restart it"), remote=(404, None),
        fwd=WD_FWD),
    _wd("remote answers HTTP 500", {"id": SID, "todoId": REMOTE_ID}, 502, _bad_remote("the kernel on %s answered HTTP 500"),
        remote=(500, None), fwd=WD_FWD),
    _wd("remote answers 409: no relay arm here, a 502 naming the status", {"id": SID, "todoId": REMOTE_ID}, 502,
        _bad_remote("the kernel on %s answered HTTP 409"), remote=(409, None), fwd=WD_FWD),
    _wd("remote row without a host name", {"id": SID, "todoId": REMOTE_ID}, 502,
        _bad_remote("the tunnel to %s is not answering (re-dialing)", "that host"), remote=(0, None), row=NAMELESS_ROW,
        fwd=WD_FWD),
]

WITHDRAW_ORDER = [
    _wd("presence before the switch", {"id": SID}, 400, _err("id and todoId required"), switch=False),
    _wd("switch before the forward", {"id": SID, "todoId": REMOTE_ID}, 409, _err(OFF), switch=False, remote=(200, {"ok": True})),
    _wd("the forward before the store guard", {"id": SID, "todoId": REMOTE_ID}, 200, '{"ok": true}', remote=(200, {"ok": True}),
        seed=seed_file(FLAGGED), fwd=WD_FWD),
    _wd("switch before the account", {"id": SID, "todoId": UNKNOWN}, 409, _err(OFF), switch=False),
    _wd("switch before the store guard", {"id": SID, "todoId": SEEDED}, 409, _err(OFF), switch=False, seed=seed_file(FLAGGED)),
    _wd("auth before the body parse", b"not json", 403, None, token=False),
]


# --------------------------------------------------------------------------------------------------- the runner
class _Norm:
    """Per-row normalizer: minted ids by first appearance (ut-<n>), ten-digit epochs on createdT / t / at (<T>)."""

    def __init__(self):
        self.ids = {}

    def __call__(self, s):
        if s is None:
            return None
        s = re.sub(r"ut-[0-9a-f]{8}", lambda m: self.ids.setdefault(m.group(0), "ut-<%d>" % (len(self.ids) + 1)), s)
        return re.sub(r'("(?:createdT|t|at)": )\d{10}\b', r"\1<T>", s)


def _store_text():
    p = jd.STATE / "user-todos.json"
    return p.read_text() if p.exists() else None


class RouteAnswers(unittest.TestCase):
    """Every row of the four tables, each in a fresh state root with the switch as the row says."""

    def _run(self, c):
        with contextlib.ExitStack() as row_scope:            # a fresh state root per row, restored when the row ends
            td = row_scope.enter_context(tempfile.TemporaryDirectory())
            row_scope.callback(setattr, jd, "STATE", jd.STATE)
            saved_push = (km._push_all, km._push_soon)
            row_scope.callback(lambda: (setattr(km, "_push_all", saved_push[0]), setattr(km, "_push_soon", saved_push[1])))
            for d in (km._user_todos_cache, km._user_todos_bad, km._user_todos_switch_cache):
                row_scope.callback(d.clear)
                d.clear()
            jd.STATE = Path(td)
            tut._hosts_off(td)
            km._set_user_todos(True)
            if not c["switch"]:
                km._set_user_todos(False)
            pushed = []
            km._push_all = lambda *a, **k: (_ for _ in ()).throw(AssertionError("synchronous _push_all on a postal-called route"))
            km._push_soon = lambda: pushed.append(True)
            ctx = {}
            if c["seed"] is not None:
                c["seed"](ctx)
                del pushed[:]                                # the row's own wake only, never the seed's
            body = c["body"](ctx) if callable(c["body"]) else c["body"]
            norm = _Norm()
            before = norm(_store_text())
            calls = []
            with contextlib.ExitStack() as stack:
                if c["remote"] is not None:
                    row = REMOTE_ROW if c["row"] is None else c["row"]
                    stack.enter_context(mock.patch.object(km, "_host_for_sid", lambda sid: row))
                    stack.enter_context(mock.patch.object(
                        km, "_remote_forward_status", lambda r, path, b: calls.append([path, b]) or c["remote"]))
                if c["patch"] is not None:
                    stack.enter_context(mock.patch.object(km, *c["patch"]))
                with contextlib.redirect_stderr(io.StringIO()):
                    status, out = tut._serve_post(c["path"], body, {"X-Romp-Token": km.TOKEN} if c["token"] else {})
            answer = norm(out.decode("utf-8"))
            after = norm(_store_text())
        self.assertEqual(status, c["status"])
        if c["answer"] is None:                          # the handler's own refusal: a text/plain body, not the route's
            self.assertTrue(answer.startswith("forbidden:"), answer)
        else:
            self.assertEqual(answer, c["answer"])
        self.assertEqual(len(pushed), c["pushed"], "the pusher wakes once per saved change, never for a refusal")
        self.assertEqual(json.loads(norm(json.dumps(calls))), c["fwd"] or [], "the forward and the body it carried")
        self.assertEqual(before != after, c["written"], "written: %r -> %r" % (before, after))
        if c["store"] is not None:
            self.assertEqual(after, c["store"])

    def _table(self, rows):
        names = [c["name"] for c in rows]
        self.assertEqual(len(names), len(set(names)), "row names are unique")
        for c in rows:
            with self.subTest(c["name"]):
                self._run(c)

    def test_register(self):
        self._table(REGISTER)

    def test_register_check_order(self):
        self._table(REGISTER_ORDER)

    def test_withdraw(self):
        self._table(WITHDRAW)

    def test_withdraw_check_order(self):
        self._table(WITHDRAW_ORDER)

    def test_the_table_reaches_every_answer_the_two_functions_can_give(self):
        # every `return` in the two route functions is a status the table pins on that path: a new arm in either
        # function reds here until the table has a row for it
        for fn, rows in ((km._user_todo_register_route, REGISTER + REGISTER_ORDER),
                         (km._user_todo_withdraw_route, WITHDRAW + WITHDRAW_ORDER)):
            src = inspect.getsource(fn)
            returned = {int(m) for m in re.findall(r"^\s+return (\d{3}),", src, re.M)}
            pinned = {c["status"] for c in rows}
            self.assertEqual(returned - pinned, set(), "%s answers a status the table never sees" % fn.__name__)


if __name__ == "__main__":
    unittest.main()

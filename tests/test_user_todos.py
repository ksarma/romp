#!/usr/bin/env python3
"""User todos (plans/user-todos.md; docs/adr/0001): a need an agent registers with the person it
works for — a decision, input, or action only they can provide — held open while the agent keeps
working. Exactly three events clear one: the user answers, the user dismisses, or the agent
withdraws. Nothing that reasons by inference may write the store (the authority tier).

Covered here, kernel-side:
- the store (user-todos.json under STATE): round-trip, stamps-not-deletes, sid-keying, id
  stability, the loud unknown-id refusal, the mtime-cache, the prune sweep;
- the store LOCK (_user_todos_lock, the _comments_lock doctrine): every read-modify-write holds
  it, concurrent registrations lose nothing, and a racing answer + withdraw cannot both succeed
  — first-stamp-wins is real, not single-threaded prose;
- the DELIVERY-KEYED answer stamp (docs/adr/0001's fatal class): sent now → stamped on a truthy
  backend send; parked → the op carries the todo id and stamps at the drain; recalled (parked ✕
  or backend unqueue) or dropped (dead-session queue) → the todo stays/returns OPEN;
- the POST routes (/usertodo, /usertodo/withdraw) incl. route auth, driven over the fake-socket
  harness (the auth-hardening idiom: ask the real dispatcher, don't pin source positions), and
  the ack-fast contract: the reply never waits behind a synchronous every-session build;
- build_session's `userTodos` field + the split-card `todo` event that carries the rows (the
  chatTail wire re-sends changed EVENTS only, so the rows must ride the event), clock-invariant
  per the serialized-payload dedup rule — and _send_chat's chatTail frame carrying the field;
- the ended gate for BOTH backends (SDK registry alive:false; a reg-less tmux sid's durable
  death record, superseded by newer states evidence — never a raw listing miss) — hidden, not
  cleared, and the answer op refuses loudly instead of sending into the void;
- the per-sid chat-build-sig fold (a todo write busts the owning session's cache only);
- the two drive ops (userTodoAnswer / userTodoDismiss), the injected answer body's shape, and
  its marker hygiene (a "<!-- romp-…" lookalike in either half is neutralized);
- the round-2 wave (2026-08-22): the recall reads the todo id off the QUEUE ENTRY itself (no
  kernel-side table to restart away or evict — RecallRidesTheEntry), a restart-lost answer's
  drop-marked echo reopens its ask through _user_todo_answer_lost unless the transcript proves
  it landed (LostAnswerReopens), the neutralizer breaks the whole "<!--\\s*romp-" class the
  downstream matchers accept (MarkerNeutralizerVariants, verbatim regex imports), and resolved
  rows are size-capped per sid while open rows never are (ResolvedRowsAreBounded);
- the round-3 wave (2026-08-22): a mark-then-die kernel death no longer strands the ask —
  every boot re-derives pending losses from the persisted regs and re-offers them to the same
  seam (LossBootPass); the landed check resolves its transcript through discover's cached WIDE
  walk, so a >48h-idle session no longer skips it silently, and a genuinely transcript-less
  check logs the skip before reopening (in LostAnswerReopens); and a loss-path reopen that
  finds no 'answered' row is loud, matching the recall path (in LostAnswerReopens);
- SLICE 2 (ambient visibility and the endgame): build_feed's sid-keyed open-count map behind
  the ended/muted gates + the feed-cache sig watch (FeedSeamUserTodos); the idle-escalation floor's
  arming predicate with the no-flap pin (EscalationFloorPredicate) and its perm_top-family
  wiring incl. the goal-less placeholder (EscalationFloorWiring); the widened app badge and its
  no-double-count rule (BadgeArithmetic); the auto-nudge stand-down (NudgeStandsDownForOpenTodos).
  The tab glyph / feed marker pins live in the node suites (tab-usertodo.test.ts,
  feed-user-todos.test.ts);
- the slice-2 review wave (2026-08-22): the nudge stand-down is scoped to the STATUS-NUDGE
  branch alone — the awaiting wake and the debt machinery flow past it
  (NudgeStandsDownForOpenTodos); the floor's predicate gains the peer-wait input (waiting on a
  live peer is deliberately not needs-you; in EscalationFloorPredicate); the floored card's OS
  push is deduplicated on the floored todo SET, never re-fired by the card's own designed
  Working dips (FloorNotificationDedup); one session shows ONE interrupt story — the goal-less
  placeholder yields to any floored/blocked card and the todo-floored card suppresses the
  provisional Working placeholder (OneInterruptStory); the badge counts per-ITEM decision
  classes (quarantine, parked handoffs) per card (in BadgeArithmetic); the focus-chain miss
  falls back to a still-working top (in OneInterruptStory); and the muted-session asymmetry —
  tab glyph shows, feed aggregates quiet — is pinned as designed (in BuildSessionSeam);
- the round-2 verification wave (2026-08-22), all in the classes above: the notification
  baseline SEEDS the floor-push latch from the already-floored world, so a restart's first
  dip+re-entry is not news; a LOST answer's reopen clears its id from the latch (the re-floor
  is the one signal the answer never arrived) while the user's own ✕ recall stays silent; the
  floored todo-set diff runs independent of the column transition, so an id joining with no
  observed dip still pushes (FloorNotificationDedup); the focus walk and the working-top
  fallback both skip done-CONFIRMING tops — the settle gate's cards, flooring them flaps
  (OneInterruptStory); and the peer-wait gate's local-host-only scope is pinned as a documented
  limitation shared with the waitingOn chip (PeerWaitScopeIsLocalOnly);
- SLICE 3 (memory across context loss): the rendered context block — nothing at zero todos,
  newest-first with the capped "…and N more" tail, marker hygiene, the deliberate absence of a
  liveness re-check (ContextBlock) — and its read-only, token-gated POST /usertodo/context leg
  (ContextRoute). The hook that carries it into a session is bats-covered
  (romp-usertodo-context.bats); the words themselves are voice-scanned in test_injected_voice.py;
- the todo-file follow-on (2026-09-07): a todo may name the FILE it is about — `file`, resolved at
  filing against the session's cwd and stored absolute, kept as given with a `warning` on the
  filing reply when it cannot resolve, never a refusal (FileNamedByATodo; the file tests in
  Routes, incl. the remote forward) — and it rides every serialization: the open rows, the feed's
  userTodoRows, the lifecycle log and its rebuild, the SessionStart block (in ContextBlock and
  FeedSeamUserTodos). The comments panel's side, the status reply's `todos`, is pinned in
  tests/test_file_comments.py.

SYNTHETIC fixtures only: placeholder UUIDs, the notes-api demo world.
"""
import contextlib
import inspect
import io
import json
import os
import re
import tempfile
import threading
import time
import unittest
from unittest import mock
from romp_load import load_source
from pathlib import Path

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")
# Hermetic state BEFORE the loads — they resolve their state root at import time, and only
# pytest runs conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
em = load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")  # setdefault like every other module: an unconditional set poisons a shared-name kernel loaded earlier in the worker
km = load_source("romp_kernel_ut", os.path.join(BIN, "romp-kernel"))
jd = km.jd

SID = "11111111-2222-3333-4444-555555555555"
SID2 = "22222222-3333-4444-5555-666666666666"
NOW = 1781200000


class _StoreSandbox(unittest.TestCase):
    """Per-test STATE sandbox + cache reset — the _session_flags test idiom."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.saved = jd.STATE
        jd.STATE = Path(self.td.name)
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()
        km._set_user_todos(True)                     # the feature switch is OFF by default (2026-09-03);
        #                                              these suites pin the ON behavior — the OFF side
        #                                              lives in test_user_todos_switch.py
        self.poisoned0 = jd.shared_store_stats()["poisoned"]

    def tearDown(self):
        # the shared-cache landing gate (round-4 plan P1): the feed builds in these suites read their
        # stores through the shared read-only cache and must never have written into one
        self.assertEqual(jd.shared_store_stats()["poisoned"] - self.poisoned0, 0,
                         "a feed build wrote into a shared goal store (see judge-errors frozen-store-write)")
        jd.STATE = self.saved
        self.td.cleanup()
        km._user_todos_cache.clear()
        km._user_todos_bad.clear()


class StoreRoundTrip(_StoreSandbox):
    def test_add_mints_a_ut_id_and_persists_the_record(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        self.assertRegex(tid, r"^ut-[0-9a-f]{8}$")
        rec = km._user_todos()[SID][0]
        self.assertEqual(rec["id"], tid)
        self.assertEqual(rec["text"], "Need the auth-scheme decision to wire login")
        self.assertEqual(rec["detail"], "OAuth vs cookie")
        self.assertIsInstance(rec["createdT"], int)
        self.assertNotIn("resolved", rec, "a fresh todo is open")

    def test_detail_is_optional_and_absent_when_empty(self):
        km._add_user_todo(SID, "Need a test credential for the api session")
        self.assertNotIn("detail", km._user_todos()[SID][0])

    def test_the_mtime_cache_sees_the_write(self):
        self.assertEqual(km._user_todos(), {})            # primes the (empty) read path
        km._add_user_todo(SID, "Need your pick of the two route layouts")
        self.assertTrue(km._user_todos().get(SID), "the (mtime_ns,size) cache key sees the write")

    def test_ids_never_collide_within_a_session(self):
        ids = {km._add_user_todo(SID, "todo %d" % i) for i in range(20)}
        self.assertEqual(len(ids), 20)

    def test_the_store_is_sid_keyed(self):
        km._add_user_todo(SID, "web: need the staging port")
        km._add_user_todo(SID2, "api: need the auth decision")
        self.assertEqual(len(km._open_user_todos(SID)), 1)
        self.assertEqual(len(km._open_user_todos(SID2)), 1)
        self.assertEqual(km._open_user_todos(SID)[0]["text"], "web: need the staging port")

    def test_open_list_sorts_by_createdT_oldest_first(self):
        # written newest-first on purpose: the sort must come from createdT, not file order
        (jd.STATE / "user-todos.json").write_text(json.dumps({SID: [
            {"id": "ut-bbbbbbbb", "text": "second", "createdT": NOW + 60},
            {"id": "ut-aaaaaaaa", "text": "first", "createdT": NOW}]}))
        self.assertEqual([t["id"] for t in km._open_user_todos(SID)], ["ut-aaaaaaaa", "ut-bbbbbbbb"])


# PRIVATE synthetic sids for the todo-file tests (the goal-store fixture rule, generalized: rows
# minted under the shared placeholder can be reached by another module's fixtures).
FSID = "7c7c7c7c-1111-4222-8333-944444444444"
FSID2 = "7d7d7d7d-1111-4222-8333-944444444444"


class FileNamedByATodo(_StoreSandbox):
    """The todo-file follow-on (2026-09-07): a user todo may name the FILE it is about — `file`, an
    absolute path on this kernel's disk, resolved at filing (_user_todo_file: ~ expanded, a relative
    path against the session's recorded cwd) and carried by every serialization of the todo (the
    store, the open rows every surface ships, the lifecycle log and its rebuild). A path that does
    not resolve is kept as given with a warning for the filing reply — never a refusal."""

    def setUp(self):
        super().setUp()
        self.root = os.path.join(self.td.name, "notes-api")
        os.makedirs(os.path.join(self.root, "docs"))
        self.fp = os.path.join(self.root, "docs", "report.md")
        with open(self.fp, "w") as f:
            f.write("# Findings\n")
        self._cwd = km._cwd_of
        km._cwd_of = lambda sid: self.root if sid == FSID else ""     # FSID2 has no recorded cwd

    def tearDown(self):
        km._cwd_of = self._cwd
        super().tearDown()

    def test_an_absolute_file_is_stored_and_rides_the_open_rows(self):
        tid = km._add_user_todo(FSID, "Need a look at the findings report", file=self.fp)
        rec = km._user_todos()[FSID][0]
        self.assertEqual(rec["file"], self.fp)
        rows = km._open_user_todos(FSID)
        self.assertEqual((rows[0]["id"], rows[0]["file"]), (tid, self.fp), "the rows every surface ships carry it")

    def test_a_todo_without_a_file_stores_no_file_key(self):
        km._add_user_todo(FSID, "Need the staging port")
        km._add_user_todo(FSID, "Need the fixture format pick", "either is fine", file="   ")
        for rec in km._user_todos()[FSID] + km._open_user_todos(FSID):
            self.assertNotIn("file", rec, "a file-less todo keeps the shape it had")

    def test_a_relative_file_resolves_against_the_sessions_cwd_and_is_normalized(self):
        km._add_user_todo(FSID, "Need a look at the findings report", file="docs/../docs/report.md")
        self.assertEqual(km._user_todos()[FSID][0]["file"], self.fp)
        self.assertEqual(km._user_todo_file("docs/report.md", FSID), (self.fp, None))

    def test_a_tilde_path_expands(self):
        with mock.patch.dict(os.environ, {"HOME": self.root}):
            self.assertEqual(km._user_todo_file("~/docs/report.md", FSID), (self.fp, None))

    def test_an_unresolvable_file_is_kept_as_given_with_a_warning_never_refused(self):
        tid = km._add_user_todo(FSID2, "Need a look at the findings report", file="docs/report.md")
        self.assertRegex(tid, r"^ut-[0-9a-f]{8}$", "filed all the same")
        self.assertEqual(km._user_todos()[FSID2][0]["file"], "docs/report.md")
        stored, warning = km._user_todo_file("docs/report.md", FSID2)
        self.assertEqual(stored, "docs/report.md")
        for words in ("docs/report.md", "did not resolve", "absolute path"):
            self.assertIn(words, warning)

    def test_no_file_means_no_warning(self):
        self.assertEqual(km._user_todo_file(None, FSID), (None, None))
        self.assertEqual(km._user_todo_file("", FSID), (None, None))

    def test_the_spelling_is_stored_not_the_realpath(self):
        # the store keeps the path as named (the chip shows what the agent said); matching by
        # realpath is the comments panel's job at status time (_user_todos_naming_file)
        alias = os.path.join(self.td.name, "alias.md")
        os.symlink(self.fp, alias)
        km._add_user_todo(FSID, "Need a look at the findings report", file=alias)
        self.assertEqual(km._user_todos()[FSID][0]["file"], alias)

    def test_the_lifecycle_log_carries_the_file_and_the_rebuild_restores_it(self):
        tid = km._add_user_todo(FSID, "Need a look at the findings report", file=self.fp)
        km._add_user_todo(FSID, "Need the staging port")
        km._resolve_user_todo(FSID, tid, "answered", reply="Re: … — looks good")
        lines = (jd.STATE / km.USER_TODOS_LOG_FILE).read_text().splitlines()
        recs = [json.loads(ln) for ln in lines]
        self.assertEqual([r.get("file") for r in recs], [self.fp, None, self.fp],
                         "every line of a todo that names a file carries it; a file-less line does not")
        self.assertNotIn("file", recs[1], "the documented shape for a file-less filing, nothing else")
        rebuilt = km._user_todos_from_log(lines)
        self.assertEqual(rebuilt[FSID][0]["file"], self.fp)
        self.assertEqual(rebuilt[FSID][0]["resolved"]["kind"], "answered")
        self.assertNotIn("file", rebuilt[FSID][1])
        # a resolution whose filing was rotated away still knows its file
        got = km._user_todos_from_log([{"t": 9, "sid": FSID, "id": "ut-9", "kind": "withdrawn",
                                        "text": "Need the port", "detail": "", "file": self.fp}])
        self.assertEqual(got[FSID][0]["file"], self.fp)


LSID = "7e7e7e7e-1111-4222-8333-944444444444"
LINK = "https://example.invalid/notes-api/pull/398"


class LinkCarriedByATodo(_StoreSandbox):
    """`link` (the user 2026-09-08, whose todo titles named pull requests by URL): a user todo may CARRY the web
    address it is about, an http or https URL, checked at filing (_user_todo_link) and carried by every
    serialization of the todo the way `file` is (the store, the open rows every surface ships, the lifecycle log
    and its rebuild, the resume hand-back). Unlike a `file` that does not resolve, a value that is not such an
    address is REFUSED and nothing is filed: there is no resolution step that could mend it, and the agent hears
    the reason in the reply it would have read the id from."""

    def test_a_web_address_is_stored_and_rides_the_open_rows(self):
        tid = km._add_user_todo(LSID, "Need a review of the pull request", link=LINK)
        rec = km._user_todos()[LSID][0]
        self.assertEqual(rec["link"], LINK)
        rows = km._open_user_todos(LSID)
        self.assertEqual((rows[0]["id"], rows[0]["link"]), (tid, LINK), "the rows every surface ships carry it")
        self.assertNotIn("file", rows[0], "a link is not a file")

    def test_http_and_https_both_pass_and_the_address_is_stripped(self):
        self.assertEqual(km._user_todo_link("  " + LINK + " \n"), (LINK, None), "stripped of surrounding whitespace")
        self.assertEqual(km._user_todo_link("http://example.invalid/x?y=1#z"), ("http://example.invalid/x?y=1#z", None))
        self.assertEqual(km._user_todo_link("HTTPS://Example.invalid/X"), ("HTTPS://Example.invalid/X", None), "the scheme case-insensitively; the rest as typed")
        # the kernel does not fetch it: a mistyped host is stored as typed, like a mistyped absolute file
        self.assertEqual(km._user_todo_link("https://exmaple.invalid/typo"), ("https://exmaple.invalid/typo", None))

    def test_a_todo_without_a_link_stores_no_link_key(self):
        km._add_user_todo(LSID, "Need the staging port")
        km._add_user_todo(LSID, "Need the fixture format pick", "either is fine", link="   ")
        km._add_user_todo(LSID, "Need the port", link=None)
        for rec in km._user_todos()[LSID] + km._open_user_todos(LSID):
            self.assertNotIn("link", rec, "a link-less todo keeps the shape it had")
        self.assertEqual(km._user_todo_link(None), (None, None))
        self.assertEqual(km._user_todo_link(""), (None, None))

    def test_a_value_that_is_not_a_web_address_is_refused_and_nothing_is_filed(self):
        bad = ["ftp://example.invalid/x", "example.invalid/x", "https://", "https:///nohost", "mailto:someone@example.invalid",
               "javascript:alert(1)", "file:///tmp/notes-api/a.md", "https://example.invalid/a b", "https://example.invalid/a\tb",
               "https://example.invalid/a\x00b", "https://example.invalid/" + "x" * km._TODO_LINK_MAX, ["https://example.invalid/x"],
               {"href": "https://example.invalid/x"}, 7, True]
        for value in bad:
            with self.subTest(link=value):
                stored, err = km._user_todo_link(value)
                self.assertIsNone(stored)
                self.assertIsInstance(err, str)
                self.assertIn("http or https address", err, "the reply says what would have been taken")
                with self.assertRaises(ValueError) as cm:
                    km._add_user_todo(LSID, "Need a review of the pull request", link=value)
                self.assertEqual(str(cm.exception), err, "the filer raises the same words the route answers")
        self.assertEqual(km._user_todos().get(LSID), None, "nothing filed: no row, no store")
        self.assertFalse((jd.STATE / km.USER_TODOS_LOG_FILE).exists(), "and no lifecycle line")

    def test_each_refusal_names_its_reason(self):
        self.assertIn("is not a string", km._user_todo_link(["x"])[1])
        self.assertIn("whitespace or a control character", km._user_todo_link("https://example.invalid/a b")[1])
        self.assertIn("\\x20", km._user_todo_link("https://example.invalid/a b")[1],
                      "the space is spelled out too: one predicate decides the refusal and the spelling (the round-3 review)")
        self.assertIn("\\0", km._user_todo_link("https://example.invalid/a\x00b")[1], "a NUL is spelled out: in a reply it is invisible")
        for value, ch, esc in (("https://example.invalid/a\x1bb", "\x1b", "\\x1b"), ("https://example.invalid/\x9bx", "\x9b", "\\x9b"),
                               ("https://example.invalid/a\x7fb", "\x7f", "\\x7f"),
                               # the format characters and separators the C0/C1 gate let through, spelled \uNNNN (the round-3 review)
                               ("https://example.invalid/a\u200bb", "\u200b", "\\u200b"), ("\ufeffhttps://example.invalid/x", "\ufeff", "\\ufeff"),
                               ("https://example.invalid/a\u2028b", "\u2028", "\\u2028"), ("https://example.invalid/a\u2060b", "\u2060", "\\u2060")):
            err = km._user_todo_link(value)[1]
            self.assertIn("whitespace or a control character", err, "a C1 control or a format character is refused with the controls (the 2026-09-09 review)")
            self.assertIn(esc, err, "spelled out, as the NUL is")
            self.assertNotIn(ch, err, "the character itself never rides the reason")
        self.assertIsNone(km._user_todo_link("https://example.invalid/caf\u00e9")[1], "a printable character outside ASCII passes")
        long = "https://example.invalid/" + "x" * km._TODO_LINK_MAX
        err = km._user_todo_link(long)[1]
        self.assertIn("longer than %d characters" % km._TODO_LINK_MAX, err)
        self.assertNotIn(long, err, "a spelling that long is shown by its head and its length, never whole")
        self.assertIn("(%d characters)" % len(long), err)
        self.assertIn("must start with http:// or https:// and name a host", km._user_todo_link("ftp://example.invalid/x")[1])
        self.assertIn("must start with http:// or https:// and name a host", km._user_todo_link("https://")[1])

    def test_the_lifecycle_log_carries_the_link_and_the_rebuild_restores_it(self):
        tid = km._add_user_todo(LSID, "Need a review of the pull request", link=LINK)
        km._add_user_todo(LSID, "Need the staging port")
        km._resolve_user_todo(LSID, tid, "answered", reply="Approved")
        lines = (jd.STATE / km.USER_TODOS_LOG_FILE).read_text().splitlines()
        recs = [json.loads(ln) for ln in lines]
        self.assertEqual([r.get("link") for r in recs], [LINK, None, LINK],
                         "every line of a todo that carries a link carries it; a link-less line does not")
        self.assertNotIn("link", recs[1])
        rebuilt = km._user_todos_from_log(lines)
        self.assertEqual(rebuilt[LSID][0]["link"], LINK)
        self.assertEqual(rebuilt[LSID][0]["resolved"]["kind"], "answered")
        self.assertNotIn("link", rebuilt[LSID][1])
        # a resolution whose filing was rotated away still knows its link
        got = km._user_todos_from_log([{"t": 9, "sid": LSID, "id": "ut-9", "kind": "withdrawn",
                                        "text": "Need the port", "detail": "", "link": LINK}])
        self.assertEqual(got[LSID][0]["link"], LINK)

    def test_the_lost_line_carries_the_link(self):
        tid = km._add_user_todo(LSID, "Need a review of the pull request", link=LINK)
        km._resolve_user_todo(LSID, tid, "answered", reply="Approved")
        self.assertTrue(km._reopen_user_todo(LSID, tid))
        lines = [json.loads(ln) for ln in (jd.STATE / km.USER_TODOS_LOG_FILE).read_text().splitlines()]
        self.assertEqual(lines[-1]["kind"], "lost")
        self.assertEqual(lines[-1]["link"], LINK)
        self.assertEqual(km._open_user_todos(LSID)[0]["link"], LINK, "open again, the link with it")

    def test_the_resume_list_shows_the_address_after_the_path(self):
        root = os.path.join(self.td.name, "notes-api")
        os.makedirs(os.path.join(root, "docs"))
        fp = os.path.join(root, "docs", "report.md")
        with mock.patch.object(km, "_cwd_of", lambda sid: root):
            km._add_user_todo(LSID, "Need a look at the findings report", file=fp, link=LINK)
            km._add_user_todo(LSID, "Need a review of the pull request", link=LINK)
            km._add_user_todo(LSID, "Need a look at the other note", file=fp)
        block = km._user_todo_context_block(LSID)
        self.assertRegex(block, r"- Need a look at the findings report \(ut-[0-9a-f]{8}, opened \d{4}-\d{2}-\d{2}\); file: "
                                + re.escape(fp) + "; link: " + re.escape(LINK) + "\n")
        self.assertRegex(block, r"- Need a review of the pull request \(ut-[0-9a-f]{8}, opened \d{4}-\d{2}-\d{2}\); link: " + re.escape(LINK) + "\n")
        self.assertRegex(block, r"- Need a look at the other note \(ut-[0-9a-f]{8}, opened \d{4}-\d{2}-\d{2}\); file: " + re.escape(fp) + "\n",
                         "a todo with a file alone reads the same way")
        self.assertEqual(len(re.findall(r"\); (?:file|link): ", block)), 3, "one tail per row, each after the row's parenthesis")
        for ln in block.splitlines():
            if ln.startswith("- "):
                self.assertNotIn("\u2014", ln, "a row's tail follows a semicolon, not an em dash (the round-3 review)")


class ResolutionStamps(_StoreSandbox):
    """Resolution STAMPS rather than deletes — the record carries its own history."""

    def test_each_clearing_event_stamps_its_own_kind(self):
        for kind in ("answered", "dismissed", "withdrawn"):
            tid = km._add_user_todo(SID, "need for %s" % kind)
            self.assertTrue(km._resolve_user_todo(SID, tid, kind))
            rec = next(t for t in km._user_todos()[SID] if t["id"] == tid)
            self.assertEqual(rec["resolved"]["kind"], kind)
            self.assertIsInstance(rec["resolved"]["t"], int)

    def test_a_resolved_todo_leaves_the_open_list_but_not_the_file(self):
        tid = km._add_user_todo(SID, "Need the rate-limit ceiling")
        km._resolve_user_todo(SID, tid, "answered")
        self.assertEqual(km._open_user_todos(SID), [])
        self.assertEqual(len(km._user_todos()[SID]), 1, "stamped, never deleted")

    def test_unknown_id_is_refused_never_a_silent_success(self):
        self.assertFalse(km._resolve_user_todo(SID, "ut-deadbeef", "withdrawn"))

    def test_a_second_stamp_is_refused_and_the_first_survives(self):
        tid = km._add_user_todo(SID, "Need the schema review")
        self.assertTrue(km._resolve_user_todo(SID, tid, "answered"))
        self.assertFalse(km._resolve_user_todo(SID, tid, "withdrawn"),
                         "already cleared — the withdraw must be told so, loudly")
        rec = km._user_todos()[SID][0]
        self.assertEqual(rec["resolved"]["kind"], "answered", "the first stamp is the history")


class StoreLock(_StoreSandbox):
    """The store lock (_user_todos_lock, the _comments_lock doctrine): the routes' HTTP threads,
    the WS dispatch threads and the pusher all read-modify-write this file, so without the lock
    two postal buses registering concurrently silently lost CONFIRMED rows, and a racing answer +
    withdraw both reported success with last-write-wins on the surviving stamp."""

    def test_every_store_mutation_runs_under_the_lock(self):
        # deterministic pin: the publish step of every mutation must hold the lock — the exact
        # interleaving the concurrent shapes below hammer probabilistically
        real_write = km._write_user_todos
        seen = []

        def guarded(cur):
            # the lock is re-entrant since the stamp stand-down (round 3, 2026-08-27), and an
            # RLock has no .locked() on 3.12 — _is_owned() is the sharper predicate anyway:
            # every mutation publishes on the thread that took the lock, so "the CALLING thread
            # holds it" is exactly the claim, where .locked() would settle for "someone does"
            seen.append(km._user_todos_lock._is_owned())
            real_write(cur)

        km._write_user_todos = guarded
        try:
            tid = km._add_user_todo(SID, "Need the auth-scheme decision")
            km._resolve_user_todo(SID, tid, "answered")
            km._reopen_user_todo(SID, tid)
            (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
            (jd.STATE / "gone" / (SID2 + ".json")).write_text(json.dumps({"t": NOW, "by": "gone"}))
            t2 = km._add_user_todo(SID2, "dead session's row")
            km._resolve_user_todo(SID2, t2, "dismissed")
            km._user_todos_cache.clear()
            km._prune_user_todos()
        finally:
            km._write_user_todos = real_write
        self.assertGreaterEqual(len(seen), 5)
        self.assertTrue(all(seen), "a store write outside the lock is the lost-update bug")

    def test_concurrent_registrations_lose_nothing(self):
        # the R1 shape, bounded: two threads (two postal buses' route threads) register in
        # parallel; every row postal confirmed must be in the file afterwards
        n = 60
        barrier = threading.Barrier(2)

        def writer(sid):
            barrier.wait()
            for i in range(n):
                km._add_user_todo(sid, "todo %d" % i)

        ts = [threading.Thread(target=writer, args=(s,)) for s in (SID, SID2)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        km._user_todos_cache.clear()
        d = json.loads((jd.STATE / "user-todos.json").read_text())
        self.assertEqual(len(d.get(SID) or []) + len(d.get(SID2) or []), 2 * n,
                         "registrations lost to an unlocked read-modify-write")

    def test_a_racing_answer_and_withdraw_cannot_both_succeed(self):
        # the R2 shape, bounded: whatever the schedule, exactly ONE clearing event wins and the
        # surviving stamp is the winner's — the loser is told loudly (False)
        for attempt in range(100):
            km._user_todos_cache.clear()
            (jd.STATE / "user-todos.json").write_text(json.dumps(
                {SID: [{"id": "ut-aaaaaaaa", "text": "need x", "createdT": 1}]}))
            barrier = threading.Barrier(2)
            out = [None, None]

            def r(i, kind):
                barrier.wait()
                out[i] = km._resolve_user_todo(SID, "ut-aaaaaaaa", kind)

            ts = [threading.Thread(target=r, args=(0, "answered")),
                  threading.Thread(target=r, args=(1, "withdrawn"))]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual([out[0], out[1]].count(True), 1,
                             "attempt %d: first-stamp-wins must be real under concurrency" % attempt)
            km._user_todos_cache.clear()
            kind = km._user_todos()[SID][0]["resolved"]["kind"]
            self.assertEqual(kind, "answered" if out[0] else "withdrawn",
                             "the surviving stamp must be the winner's, never last-write-wins")


class PruneSweep(_StoreSandbox):
    """The sweep keys on the rows' own corroborated evidence — resolved AND a durable death
    record — NEVER on a display/known-set: the tab-GC's set drops alive-but-idle tmux sessions
    during list-collapse cycles and 48h transcript ageouts, and the first cut deleted a LIVE
    session's open asks on exactly that evidence (the vanishing the ADR exists to stop)."""

    def _mark_dead(self, sid, t=NOW):
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (sid + ".json")).write_text(json.dumps({"t": t, "by": "gone"}))

    def test_open_todos_survive_regardless_of_any_display_set(self):
        km._add_user_todo(SID, "live but idle — a list collapse must not delete me")
        km._add_user_todo(SID2, "aged out of the discover window — still standing")
        km._prune_user_todos()
        self.assertEqual(set(km._user_todos()), {SID, SID2},
                         "open todos persist until user dismiss / agent withdraw — no set miss")

    def test_open_todos_of_a_dead_session_survive_too(self):
        km._add_user_todo(SID, "my session died — revive returns me")
        self._mark_dead(SID)
        km._prune_user_todos()
        self.assertEqual(len(km._open_user_todos(SID)), 1,
                         "hidden by the ended gate, never deleted — the ADR's whole point")

    def test_resolved_rows_of_a_dead_session_leave(self):
        tid = km._add_user_todo(SID, "answered, then the session died")
        km._resolve_user_todo(SID, tid, "answered")
        self._mark_dead(SID)
        km._prune_user_todos()
        self.assertNotIn(SID, km._user_todos(), "nothing open, session dead → the sid leaves")

    def test_resolved_rows_of_a_live_session_stay(self):
        tid = km._add_user_todo(SID, "answered but the session lives")
        km._resolve_user_todo(SID, tid, "answered")
        km._prune_user_todos()
        self.assertEqual(len(km._user_todos()[SID]), 1, "history rides until the session dies")

    def test_an_sdk_ended_registry_counts_as_the_death_record(self):
        tid = km._add_user_todo(SID, "answered on an ended SDK session")
        km._resolve_user_todo(SID, tid, "answered")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        km._prune_user_todos()
        self.assertNotIn(SID, km._user_todos())

    def test_a_revived_session_is_not_dead_and_keeps_its_rows(self):
        # the marker counts only while it is the NEWEST event (_death_stamp_due's time key):
        # a revival's fresh states row un-ends the session without deleting the marker
        tid = km._add_user_todo(SID, "answered, session died, then revived")
        km._resolve_user_todo(SID, tid, "answered")
        self._mark_dead(SID, t=NOW)
        (jd.STATE / "states").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "states" / (SID + ".jsonl")).write_text(
            json.dumps({"t": NOW + 60, "state": "idle"}) + "\n")
        km._prune_user_todos()
        self.assertEqual(len(km._user_todos()[SID]), 1, "revived → not ended → history stays")

    def test_a_noop_prune_never_writes(self):
        km._add_user_todo(SID, "still here")
        p = jd.STATE / "user-todos.json"
        before = p.stat().st_mtime_ns
        km._prune_user_todos()
        self.assertEqual(p.stat().st_mtime_ns, before, "nothing gone → no write (no hot-path churn)")

    def test_the_sweep_still_rides_the_tab_session_pass_but_not_its_known_set(self):
        # wired where the old sweep was — one call per pusher pass — but keyed on its own
        # corroborated evidence, never the display set the tab-GC prunes by
        src = inspect.getsource(km._chat_tab_sessions)
        self.assertIn("_prune_user_todos()", src)


def _serve_post(path, body=None, headers=None):
    """Drive the REAL do_POST dispatcher over a fake socket (the auth-hardening harness)."""
    raw = json.dumps(body).encode() if isinstance(body, (dict, list)) else (body or b"")
    h = km.Handler.__new__(km.Handler)
    h.client_address = ("127.0.0.1", 0)
    hdrs = dict(headers or {})
    hdrs.setdefault("Content-Length", str(len(raw)))
    h.headers = hdrs
    h.path = path
    h.command = "POST"
    h.request_version = "HTTP/1.1"
    h.wfile = io.BytesIO()
    h.rfile = io.BytesIO(raw)
    h.close_connection = True
    captured = {}
    h.send_response = lambda code, *a: captured.__setitem__("status", code)
    h.send_header = lambda k, v: None
    h.end_headers = lambda: None
    h.log_message = lambda *a: None
    h.do_POST()
    return captured.get("status"), h.wfile.getvalue()


class Routes(_StoreSandbox):
    """POST /usertodo and /usertodo/withdraw — the kernel legs the postal tools stand on."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        self.pushed_soon = []
        # the routes must never build views synchronously (the ack-fast contract below) — a stray
        # _push_all here is a bug, so it BLOWS UP instead of silently passing
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on a postal-called route"))
        km._push_soon = lambda: self.pushed_soon.append(True)

    def tearDown(self):
        km._push_all, km._push_soon = self._push
        super().tearDown()

    def _post(self, path, body, token=True):
        hdrs = {"X-Romp-Token": km.TOKEN} if token else {}
        code, out = _serve_post(path, body, hdrs)
        try:
            return code, json.loads(out.decode() or "{}")
        except ValueError:
            return code, {}

    def test_register_requires_the_serve_token(self):
        code, _ = self._post("/usertodo", {"id": SID, "text": "x"}, token=False)
        self.assertEqual(code, 403)

    def test_register_returns_the_minted_id_and_writes_the_store(self):
        code, res = self._post("/usertodo", {"id": SID, "text": "Need the auth-scheme decision",
                                             "detail": "OAuth vs cookie — either unblocks login"})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertRegex(res["todoId"], r"^ut-[0-9a-f]{8}$")
        rec = km._user_todos()[SID][0]
        self.assertEqual(rec["id"], res["todoId"])
        self.assertEqual(rec["detail"], "OAuth vs cookie — either unblocks login")

    def test_register_refuses_a_bodyless_or_textless_ask(self):
        self.assertEqual(self._post("/usertodo", {"id": SID})[0], 400)
        self.assertEqual(self._post("/usertodo", {"text": "no sid"})[0], 400)
        code, _ = _serve_post("/usertodo", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)

    def test_withdraw_requires_the_serve_token(self):
        code, _ = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-deadbeef"}, token=False)
        self.assertEqual(code, 403)

    def test_withdraw_stamps_withdrawn(self):
        _, res = self._post("/usertodo", {"id": SID, "text": "Need the fixture format pick"})
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "withdrawn")

    def test_withdraw_of_an_unknown_or_cleared_id_answers_ok_false(self):
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": "ut-deadbeef"})
        self.assertEqual(code, 200)
        self.assertFalse(out["ok"], "a loud, plain answer — never a silent success")
        self.assertTrue(out.get("error"))
        _, res = self._post("/usertodo", {"id": SID, "text": "once"})
        self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        _, again = self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertFalse(again["ok"])

    def test_the_routes_ack_fast_and_never_push_synchronously(self):
        # the postal bus times its POST out at 2s: an inline _push_all (a synchronous build of
        # every session's payload) outran it, so a SAVED todo came back as a loud false failure
        # ("will NOT see it — try again") and the agent's retry filed a duplicate. The setUp
        # _push_all stub raises, so this passing IS the proof; the woken pusher carries the row.
        code, res = self._post("/usertodo", {"id": SID, "text": "Need the auth-scheme decision"})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        code, out = self._post("/usertodo/withdraw", {"id": SID, "todoId": res["todoId"]})
        self.assertEqual(code, 200)
        self.assertTrue(out["ok"])
        self.assertEqual(len(self.pushed_soon), 2, "each route wakes the pusher instead")

    # ── the todo-file follow-on (2026-09-07): `file` in, resolved; `warning` out when it did not ──

    def test_register_takes_the_file_resolves_it_and_answers_no_warning(self):
        root = os.path.join(self.td.name, "notes-api")
        os.makedirs(os.path.join(root, "docs"))
        fp = os.path.join(root, "docs", "report.md")
        open(fp, "w").close()
        with mock.patch.object(km, "_cwd_of", lambda sid: root if sid == FSID else ""):
            code, res = self._post("/usertodo", {"id": FSID, "text": "Need a look at the findings report",
                                                 "file": "docs/report.md"})
            code2, res2 = self._post("/usertodo", {"id": FSID, "text": "Need a look at the other note", "file": fp})
        self.assertEqual((code, code2), (200, 200))
        self.assertTrue(res["ok"] and res2["ok"])
        self.assertNotIn("warning", res)
        self.assertNotIn("warning", res2)
        recs = km._user_todos()[FSID]
        self.assertEqual(recs[0]["file"], fp, "resolved against the session's cwd, stored absolute")
        self.assertEqual(recs[1]["file"], fp, "an absolute path passes through")
        self.assertEqual(len(self.pushed_soon), 2)

    def test_register_keeps_an_unresolvable_file_as_given_and_warns_without_refusing(self):
        with mock.patch.object(km, "_cwd_of", lambda sid: ""):
            code, res = self._post("/usertodo", {"id": FSID, "text": "Need a look at the findings report",
                                                 "file": "docs/report.md"})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"], "never refused for its file")
        self.assertRegex(res["todoId"], r"^ut-[0-9a-f]{8}$")
        self.assertIn("did not resolve", res["warning"])
        self.assertIn("docs/report.md", res["warning"])
        self.assertEqual(km._user_todos()[FSID][0]["file"], "docs/report.md", "kept as given")
        self.assertEqual(len(self.pushed_soon), 1)

    def test_register_without_a_file_answers_as_before(self):
        code, res = self._post("/usertodo", {"id": FSID, "text": "Need the staging port"})
        self.assertEqual(code, 200)
        self.assertEqual(set(res), {"ok", "todoId"})
        self.assertNotIn("file", km._user_todos()[FSID][0])

    def test_the_remote_forward_passes_the_file_and_the_warning_back(self):
        seen = []
        remote = {"host": "TESTHOST", "local_port": 1, "token": "t"}
        warn = "the file path docs/report.md did not resolve to an absolute path"

        def fwd(r, path, body):
            seen.append((path, body))
            return {"ok": True, "todoId": "ut-9f2c1a34", "warning": warn}
        with mock.patch.object(km, "_host_for_sid", lambda s: remote), mock.patch.object(km, "_remote_forward", fwd):
            code, res = self._post("/usertodo", {"id": FSID, "text": "Need a look at the findings report",
                                                 "detail": "the morning report", "file": "docs/report.md"})
        self.assertEqual(code, 200)
        self.assertEqual(seen, [("/usertodo", {"id": FSID, "text": "Need a look at the findings report",
                                               "detail": "the morning report", "file": "docs/report.md"})],
                         "the file crosses as given: the remote kernel resolves it against ITS disk")
        self.assertEqual(res, {"ok": True, "todoId": "ut-9f2c1a34", "warning": warn})
        self.assertEqual(km._user_todos(), {}, "nothing stored here: the remote owns that session's ledger")
        # no file: the forward carries none, and a remote answer without a warning adds none
        seen.clear()

        def fwd2(r, path, body):
            seen.append((path, body))
            return {"ok": True, "todoId": "ut-9f2c1a35"}
        with mock.patch.object(km, "_host_for_sid", lambda s: remote), mock.patch.object(km, "_remote_forward", fwd2):
            code, res = self._post("/usertodo", {"id": FSID, "text": "Need the staging port"})
        self.assertNotIn("file", seen[0][1])
        self.assertEqual(res, {"ok": True, "todoId": "ut-9f2c1a35"})

    # ── `link` (the user 2026-09-08): checked before any write, echoed as stored, refused as a 400 ──

    def test_register_takes_a_link_and_echoes_it(self):
        code, res = self._post("/usertodo", {"id": FSID, "text": "Need a review of the pull request",
                                             "link": "  " + LINK + " "})
        self.assertEqual(code, 200)
        self.assertEqual(set(res), {"ok", "todoId", "link"})
        self.assertEqual(res["link"], LINK, "echoed as the record keeps it: stripped")
        self.assertEqual(km._user_todos()[FSID][0]["link"], LINK)
        self.assertEqual(len(self.pushed_soon), 1)
        # with a file beside it: both echoed, each as stored
        root = os.path.join(self.td.name, "notes-api"); os.makedirs(root)
        fp = os.path.join(root, "report.md")
        with mock.patch.object(km, "_cwd_of", lambda sid: root if sid == FSID else ""):
            code, res = self._post("/usertodo", {"id": FSID, "text": "Need a look at the report and the pull request",
                                                 "file": "report.md", "link": LINK})
        self.assertEqual(code, 200)
        self.assertEqual((res["file"], res["link"]), (fp, LINK))
        # absent, null and blank all mean: no link, and the reply carries none
        for body in ({"id": FSID, "text": "Need the port"}, {"id": FSID, "text": "Need the port", "link": None},
                     {"id": FSID, "text": "Need the port", "link": "  "}):
            code, res = self._post("/usertodo", body)
            self.assertEqual(code, 200)
            self.assertNotIn("link", res)
        self.assertTrue(all("link" not in t for t in km._user_todos()[FSID][2:]))

    def test_register_refuses_a_link_that_is_not_a_web_address_with_400_and_files_nothing(self):
        for value in ("ftp://example.invalid/x", "example.invalid/x", "https://example.invalid/a b", ["https://example.invalid/x"], 7):
            with self.subTest(link=value):
                code, res = self._post("/usertodo", {"id": FSID, "text": "Need a review of the pull request", "link": value})
                self.assertEqual(code, 400)
                self.assertFalse(res["ok"])
                self.assertIn("http or https address", res["error"], "the reason, in the same words the filer raises")
                self.assertEqual(res["error"], km._user_todo_link(value)[1])
        self.assertEqual(km._user_todos(), {}, "nothing filed")
        self.assertEqual(self.pushed_soon, [], "and nothing to push")
        # a bad link is refused before the file is even looked at: no half-filed todo with a file and no link
        code, res = self._post("/usertodo", {"id": FSID, "text": "Need a look", "file": "/tmp/notes-api/a.md", "link": "ftp://x/y"})
        self.assertEqual(code, 400)
        self.assertEqual(km._user_todos(), {})

    def test_the_remote_forward_passes_the_link_and_echoes_the_remotes_back(self):
        seen = []
        remote = {"host": "TESTHOST", "local_port": 1, "token": "t"}

        def fwd(r, path, body):
            seen.append((path, body))
            return {"ok": True, "todoId": "ut-9f2c1a34", "link": body.get("link")}
        with mock.patch.object(km, "_host_for_sid", lambda s: remote), mock.patch.object(km, "_remote_forward", fwd):
            code, res = self._post("/usertodo", {"id": FSID, "text": "Need a review of the pull request", "link": " " + LINK})
        self.assertEqual(code, 200)
        self.assertEqual(seen, [("/usertodo", {"id": FSID, "text": "Need a review of the pull request", "detail": "", "link": LINK})],
                         "the link crosses stripped and checked; the remote checks it again")
        self.assertEqual(res, {"ok": True, "todoId": "ut-9f2c1a34", "link": LINK})
        self.assertEqual(km._user_todos(), {}, "nothing stored here: the remote owns that session's ledger")
        # a bad link never reaches the tunnel
        seen.clear()
        with mock.patch.object(km, "_host_for_sid", lambda s: remote), mock.patch.object(km, "_remote_forward", fwd):
            code, res = self._post("/usertodo", {"id": FSID, "text": "Need a review", "link": "ftp://example.invalid/x"})
        self.assertEqual(code, 400)
        self.assertEqual(seen, [])

    def test_a_remote_kernel_that_echoes_no_link_is_named_in_the_reply_under_its_own_key_and_on_stderr(self):
        # version skew, the file's own rule: a kernel that predates a todo's link files the todo without it and
        # echoes none; the reply says so under `linkWarning` (its own key: the tool labels `warning` as the file's)
        # and stderr keeps the record (the 2026-09-09 review: before, the reply was plain success)
        remote = {"host": "TESTHOST", "local_port": 1, "token": "t"}
        err = io.StringIO()
        with mock.patch.object(km, "_host_for_sid", lambda s: remote), \
             mock.patch.object(km, "_remote_forward", lambda r, p, b: {"ok": True, "todoId": "ut-9f2c1a34"}), \
             contextlib.redirect_stderr(err):
            code, res = self._post("/usertodo", {"id": FSID, "text": "Need a review of the pull request", "link": LINK})
        self.assertEqual(code, 200)
        self.assertEqual((res["ok"], res["todoId"]), (True, "ut-9f2c1a34"))
        self.assertNotIn("link", res, "no link echoed: the signal the tool reads")
        self.assertNotIn("warning", res, "the file's key is the file's alone")
        self.assertIn("the link " + LINK + " was not recorded", res["linkWarning"])
        self.assertIn("The session manager on TESTHOST runs an older version that does not keep a todo's link", res["linkWarning"])
        self.assertIn("an update and a restart there fix that", res["linkWarning"], "the remedy for the machine")
        self.assertIn("address in its detail", res["linkWarning"],
                      "and for this todo: the detail links too, and holds an address the 300-character text may not (the round-3 review)")
        for word in ("romp", "kernel", "card", "board", "goal", "nudge", "cleared", "dismissal", "status check"):
            self.assertNotIn(word, res["linkWarning"].lower(),
                             "%r: the tool relays this sentence to the agent verbatim (test_injected_voice.py's veil), so the kernel "
                             "is the session manager here, as in the tool's own skew sentence" % word)
        self.assertIn("link not recorded on TESTHOST", err.getvalue())
        self.assertIn("predates a todo's link", err.getvalue())
        # a file and a link both lost to the same older kernel: each named under its own key
        err = io.StringIO()
        with mock.patch.object(km, "_host_for_sid", lambda s: remote), \
             mock.patch.object(km, "_remote_forward", lambda r, p, b: {"ok": True, "todoId": "ut-9f2c1a34"}), \
             contextlib.redirect_stderr(err):
            code, res = self._post("/usertodo", {"id": FSID, "text": "Need a look", "file": "/tmp/notes-api/a.md", "link": LINK})
        self.assertEqual(code, 200)
        self.assertIn("the file path /tmp/notes-api/a.md was not recorded", res["warning"])
        self.assertNotIn(LINK, res["warning"], "the file's sentence names the file alone")
        self.assertIn("the link " + LINK + " was not recorded", res["linkWarning"])
        self.assertEqual(err.getvalue().count("not recorded on TESTHOST"), 2, "both losses on record")
        # a remote that echoes the link: no warning of either kind
        with mock.patch.object(km, "_host_for_sid", lambda s: remote), \
             mock.patch.object(km, "_remote_forward", lambda r, p, b: {"ok": True, "todoId": "ut-9f2c1a34", "link": b.get("link")}):
            code, res = self._post("/usertodo", {"id": FSID, "text": "Need a review", "link": LINK})
        self.assertEqual(res, {"ok": True, "todoId": "ut-9f2c1a34", "link": LINK})


# A PRIVATE synthetic sid for the account tests below (the goal-store fixture rule, generalized:
# rows minted under the shared placeholder can be reached by another module's fixtures).
WSID = "7a7a7a7a-1111-4222-8333-944444444444"
WSID2 = "7b7b7b7b-1111-4222-8333-944444444444"


class WithdrawAccount(_StoreSandbox):
    """POST /usertodo/withdraw ACCOUNTS for what it found (2026-09-07): `ok` keeps its meaning
    (this call stamped the row), and `state` / `at` / `owner` say which kind of nothing-to-do an
    ok:false was, so the postal tool can tell the agent "the person already answered it" apart from
    "not your id". Two sessions had read the one-size ok:false as a failure. The route describes
    the asker's own rows only: another session's id is `unknown`, never described."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        self.pushed_soon = []
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on a postal-called route"))
        km._push_soon = lambda: self.pushed_soon.append(True)

    def tearDown(self):
        km._push_all, km._push_soon = self._push
        super().tearDown()

    def _post(self, path, body):
        code, out = _serve_post(path, body, {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 200)
        return json.loads(out.decode() or "{}")

    def _file(self, text="Need the auth-scheme decision", sid=WSID):
        tid = self._post("/usertodo", {"id": sid, "text": text})["todoId"]
        self.pushed_soon.clear()                     # the register's own wake; the counts below are the withdraw's
        return tid

    def _withdraw(self, tid, sid=WSID):
        return self._post("/usertodo/withdraw", {"id": sid, "todoId": tid})

    def test_a_fresh_withdraw_is_ok_and_accounts_the_stamp_it_made(self):
        tid = self._file()
        out = self._withdraw(tid)
        row = km._user_todos()[WSID][0]
        self.assertEqual(row["resolved"]["kind"], "withdrawn")
        self.assertEqual(out, {"ok": True, "state": "withdrawn", "at": row["resolved"]["t"], "owner": True})
        self.assertIsInstance(out["at"], int)
        self.assertEqual(len(self.pushed_soon), 1, "the row leaves the split card")

    def test_a_row_the_person_answered_is_accounted_answered_and_left_alone(self):
        tid = self._file()
        self.assertTrue(km._resolve_user_todo(WSID, tid, "answered", reply="OAuth."))
        stamp = km._user_todos()[WSID][0]["resolved"]
        out = self._withdraw(tid)
        self.assertFalse(out["ok"])
        self.assertEqual((out["state"], out["at"], out["owner"]), ("answered", stamp["t"], True))
        self.assertTrue(out.get("error"), "the old contract's error text still rides along")
        self.assertEqual(km._user_todos()[WSID][0]["resolved"], stamp, "a withdraw never overwrites a stamp")
        self.assertEqual(self.pushed_soon, [], "nothing changed, nothing to push")

    def test_a_row_the_person_dismissed_is_accounted_dismissed(self):
        tid = self._file()
        self.assertTrue(km._resolve_user_todo(WSID, tid, "dismissed"))
        stamp = km._user_todos()[WSID][0]["resolved"]
        out = self._withdraw(tid)
        self.assertFalse(out["ok"])
        self.assertEqual((out["state"], out["at"], out["owner"]), ("dismissed", stamp["t"], True))

    def test_a_second_withdraw_accounts_the_first_ones_stamp(self):
        tid = self._file()
        first = self._withdraw(tid)
        again = self._withdraw(tid)
        self.assertFalse(again["ok"])
        self.assertEqual((again["state"], again["at"], again["owner"]), ("withdrawn", first["at"], True))
        self.assertEqual(len(self.pushed_soon), 1, "only the stamping call woke the pusher")

    def test_an_unknown_id_is_unknown_and_not_owned(self):
        out = self._withdraw("ut-deadbeef")
        self.assertFalse(out["ok"])
        self.assertEqual((out["state"], out["at"], out["owner"]), ("unknown", None, False))
        self.assertTrue(out.get("error"))

    def test_another_sessions_id_is_unknown_to_the_asker_and_stays_open(self):
        tid = self._file(sid=WSID2)
        out = self._withdraw(tid, sid=WSID)
        self.assertFalse(out["ok"])
        self.assertEqual((out["state"], out["owner"]), ("unknown", False), "never described, never stamped")
        self.assertNotIn("resolved", km._user_todos()[WSID2][0], "the other session's ask still stands")
        self.assertEqual(self.pushed_soon, [])

    def test_the_lookup_and_the_stamp_share_one_critical_section(self):
        # a racing answer must not land between "found open" and the stamp: the stamp is made
        # while the account's look-up still holds the store lock (re-entrant, so the nested
        # _resolve_user_todo takes it again instead of deadlocking)
        held = []
        real = km._resolve_user_todo
        km._resolve_user_todo = lambda *a, **k: (held.append(km._user_todos_lock._is_owned()) or real(*a, **k))
        try:
            tid = self._file()
            self.assertTrue(self._withdraw(tid)["ok"])
        finally:
            km._resolve_user_todo = real
        self.assertEqual(held, [True], "the stamp ran inside the look-up's lock")

    def _seed_row(self, resolved, sid=WSID):
        """A hand-edited store: one row of the asker's with the given closing stamp, as written."""
        row = {"id": "ut-11111111", "text": "Need the auth-scheme decision", "createdT": NOW - 60,
               "resolved": resolved}
        (jd.STATE / "user-todos.json").write_text(json.dumps({sid: [row]}))
        km._user_todos_cache.clear()
        return row

    def test_a_malformed_closing_stamp_is_unknown_and_named_never_open(self):
        # review round 1 (2026-09-07): `resolved` truthy but not a {kind, t} stamp with one of the
        # three kinds (no writer makes one: a hand-edited or damaged store) read as state 'open', a
        # fifth value the contract does not have, which the tool worded as already closed. The row
        # is not open (a truthy stamp blocks the stamp), so the account is unknown-shaped, names
        # the stamp it could not read, and says the row is the asker's own; nothing is rewritten.
        for stamp in (True, "withdrawn", 1781200000, {"t": 1781200000}, {"kind": "", "t": 1781200000},
                      {"kind": "lost", "t": 1781200000}, {"kind": ["withdrawn"], "t": 1781200000}):
            with self.subTest(stamp=stamp):
                row = self._seed_row(stamp)
                out = self._withdraw("ut-11111111")
                self.assertFalse(out["ok"])
                self.assertEqual((out["state"], out["at"], out["owner"]), ("unknown", None, True))
                self.assertIn("malformed closing stamp on ut-11111111", out["error"])
                self.assertIn(repr(stamp), out["error"], "names the stamp it could not read")
                self.assertIn("answered | dismissed | withdrawn", out["error"], "and the shape it expected")
                self.assertEqual(km._user_todos()[WSID][0], row, "the damage is reported, not papered over")
                self.assertEqual(self.pushed_soon, [], "nothing changed, nothing to push")

    def test_a_well_formed_stamp_of_each_kind_is_still_its_own_state(self):
        # the validation above must not narrow the three real states
        for kind in ("answered", "dismissed", "withdrawn"):
            with self.subTest(kind=kind):
                self._seed_row({"kind": kind, "t": 1781200000})
                out = self._withdraw("ut-11111111")
                self.assertEqual((out["ok"], out["state"], out["at"], out["owner"]),
                                 (False, kind, 1781200000, True))
                self.assertNotIn("malformed", out.get("error", ""))

    def _forward(self, st, res, sid=WSID):
        """Drive the route's remote branch: the sid maps to TESTHOST and its tunnel answers (st, res),
        the (status, parsed body) pair _remote_forward_status returns."""
        saved = (km._host_for_sid, km._remote_forward_status)
        km._host_for_sid = lambda s: {"host": "TESTHOST", "local_port": 1, "token": "t"}
        km._remote_forward_status = lambda r, path, body, method="POST": (st, res)
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                code, out = _serve_post("/usertodo/withdraw", {"id": sid, "todoId": "ut-9f2c1a34"},
                                        {"X-Romp-Token": km.TOKEN})
        finally:
            km._host_for_sid, km._remote_forward_status = saved
        return code, json.loads(out.decode() or "{}")

    def test_the_remote_forward_passes_the_account_through(self):
        acct = {"ok": False, "state": "answered", "at": 1781200000, "owner": True}
        self.assertEqual(self._forward(200, acct), (200, acct))
        # a remote kernel that predates the account answers ok alone: nothing is invented
        self.assertEqual(self._forward(200, {"ok": False}), (200, {"ok": False}))
        # the remote's error rides along too (its malformed-stamp account names the stamp there)
        bad = {"ok": False, "state": "unknown", "at": None, "owner": True,
               "error": "malformed closing stamp on ut-9f2c1a34: resolved=True (a stamp is {kind: answered | dismissed | withdrawn, t})"}
        self.assertEqual(self._forward(200, bad), (200, bad))
        self.assertEqual(self.pushed_soon, [], "a forwarded withdraw changes nothing here")

    def test_a_remote_that_gave_no_account_is_a_502_never_already_closed(self):
        # review round 1 (2026-09-07): a dead tunnel answered 200 {"ok": false}, which the tool
        # worded as "already answered, dismissed, or withdrawn" while the row still stood on the
        # remote. A non-2xx makes the tool say the withdraw did not happen (_kernel_post reads a
        # 502 as None), which is true; the body names the cause for a caller that reads it.
        # Through the tool this branch is out of reach (a session's tool posts to its own host's
        # kernel, whose GET /sessions lists local sessions only, so its sid maps to no remote
        # there); the route is API for any token holder, so it answers honestly regardless.
        for st, res, words in ((0, None, ("tunnel to TESTHOST", "not answering")),
                               (404, None, ("kernel on TESTHOST", "predates /usertodo/withdraw")),
                               (500, None, ("kernel on TESTHOST", "HTTP 500")),
                               (200, None, ("kernel on TESTHOST", "not JSON"))):
            with self.subTest(status=st):
                code, out = self._forward(st, res)
                self.assertEqual(code, 502)
                self.assertFalse(out["ok"])
                self.assertEqual(out["host"], "TESTHOST")
                self.assertNotIn("state", out, "no account is invented")
                for w in words:
                    self.assertIn(w, out["error"])
        self.assertEqual(self.pushed_soon, [])


class ContextBlock(_StoreSandbox):
    """SLICE 3 (memory across context loss, plans/user-todos.md): _user_todo_context_block renders
    a session's OPEN todos as the agent's OWN outstanding notes to the person it works for — the
    passive block the SessionStart hook (hooks/romp-usertodo-context.sh) injects on the resume and
    compact sources, so an agent whose working memory was wiped remembers what it asked for and
    can withdraw the moot ones. Voice-scanned by test_injected_voice.py."""

    def _seed(self, rows, sid=SID):
        (jd.STATE / "user-todos.json").write_text(json.dumps({sid: rows}))
        km._user_todos_cache.clear()

    def test_no_open_todos_mean_no_block_at_all(self):
        # a zero-todo session gets NOTHING — no noise (the spec's no-noise rule)
        self.assertEqual(km._user_todo_context_block(SID), "")
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "withdrawn")
        self.assertEqual(km._user_todo_context_block(SID), "", "resolved rows render nothing")

    def test_the_block_carries_text_id_and_opened_date(self):
        self._seed([{"id": "ut-11111111", "createdT": NOW - 86400,
                     "text": "Need the auth-scheme decision to wire login"}])
        block = km._user_todo_context_block(SID)
        day = km.time.strftime("%Y-%m-%d", km.time.localtime(NOW - 86400))
        self.assertIn("Notes you still have open with the person you work for", block)
        self.assertIn("- Need the auth-scheme decision to wire login (ut-11111111, opened %s)" % day,
                      block)
        self.assertIn("withdraw it (withdraw_user_todo)", block,
                      "the withdraw instruction names the tool by its real name — the agent holds it")

    def test_detail_stays_behind_the_short_line(self):
        # the block carries the one short line only; the longer context lives on the split card
        self._seed([{"id": "ut-11111111", "createdT": NOW, "text": "Need the auth-scheme decision",
                     "detail": "OAuth vs cookie — either unblocks login"}])
        self.assertNotIn("OAuth vs cookie", km._user_todo_context_block(SID))

    def test_the_file_a_todo_names_follows_the_text(self):
        # the todo-file follow-on (2026-09-07): the SessionStart listing shows the file after the
        # text, so an agent whose memory was wiped knows WHICH file it asked about; a file-less row
        # renders exactly as before
        self._seed([{"id": "ut-11111111", "createdT": NOW, "text": "Need a look at the findings report",
                     "file": "/srv/notes-api/docs/report.md"},
                    {"id": "ut-22222222", "createdT": NOW - 60, "text": "Need the staging port"}], sid=FSID)
        block = km._user_todo_context_block(FSID)
        day = km.time.strftime("%Y-%m-%d", km.time.localtime(NOW))
        bullets = [ln for ln in block.splitlines() if ln.startswith("- ")]
        self.assertEqual(bullets, [
            "- Need a look at the findings report (ut-11111111, opened %s); file: /srv/notes-api/docs/report.md" % day,
            "- Need the staging port (ut-22222222, opened %s)" % day])

    def test_a_marker_shaped_file_path_is_neutralized(self):
        # the path is agent-supplied, like the text: the same hygiene
        self._seed([{"id": "ut-11111111", "createdT": NOW, "text": "Need a look at the report",
                     "file": "/srv/notes-api/<!--romp-injected-->/report.md"}], sid=FSID)
        block = km._user_todo_context_block(FSID)
        self.assertIsNone(km._ROMP_MARKER_OPEN_RE.search(block))
        self.assertIn("romp-injected", block, "the words survive — only the comment form breaks")

    def test_newest_first_and_capped_with_a_more_tail(self):
        cap = km._USER_TODO_CONTEXT_CAP
        self._seed([{"id": "ut-%08d" % i, "createdT": NOW + i, "text": "Need decision %d" % i}
                    for i in range(cap + 3)])
        block = km._user_todo_context_block(SID)
        bullets = [ln for ln in block.splitlines() if ln.startswith("- ")]
        self.assertEqual(len(bullets), cap + 1, "cap bullets plus the tail")
        self.assertIn("Need decision %d" % (cap + 2), bullets[0], "the newest ask leads")
        self.assertEqual(bullets[-1], "- …and 3 more from earlier")
        self.assertNotIn("Need decision 0", block, "the oldest beyond the cap fold into the tail")

    def test_exactly_cap_todos_carry_no_tail(self):
        cap = km._USER_TODO_CONTEXT_CAP
        self._seed([{"id": "ut-%08d" % i, "createdT": NOW + i, "text": "Need decision %d" % i}
                    for i in range(cap)])
        self.assertNotIn("more from earlier", km._user_todo_context_block(SID))

    def test_marker_shaped_text_is_neutralized(self):
        # todo text is agent-supplied: a literal "<!--romp-…" in it would inject a lookalike
        # marker into the session's context — same hygiene as the answer body
        self._seed([{"id": "ut-11111111", "createdT": NOW,
                     "text": "Need a call on the note text <!--romp-injected--> in the fixture"}])
        block = km._user_todo_context_block(SID)
        self.assertIsNone(km._ROMP_MARKER_OPEN_RE.search(block),
                          "no marker-opening sequence may survive into the block")
        self.assertIn("romp-injected", block, "the words survive — only the comment form breaks")

    def test_no_liveness_gate_the_session_start_event_is_the_evidence(self):
        # DELIBERATE (slice 3): the block renders even when a death marker / alive:false reg
        # exists. The only caller is a SessionStart fired from INSIDE the session — an ended
        # session fires none — and re-checking the marker here would race the revival's own
        # states row (tmux-status.sh writes it from the SAME SessionStart) and eat the exact
        # block the revival came for. The event outranks the stale record.
        self._seed([{"id": "ut-11111111", "createdT": NOW, "text": "Need the auth-scheme decision"}])
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW - 50, "by": "gone"}))
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        self.assertIn("ut-11111111", km._user_todo_context_block(SID))


class ContextRoute(_StoreSandbox):
    """POST /usertodo/context — the read leg the SessionStart hook stands on. Token-gated like its
    siblings; READ-ONLY: it must neither write the store nor wake the pusher (nothing changed)."""

    def setUp(self):
        super().setUp()
        self._push = (km._push_all, km._push_soon)
        km._push_all = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("synchronous _push_all on the context read"))
        km._push_soon = lambda: (_ for _ in ()).throw(
            AssertionError("_push_soon on a read-only route — nothing changed"))

    def tearDown(self):
        km._push_all, km._push_soon = self._push
        super().tearDown()

    def _post(self, path, body, token=True):
        hdrs = {"X-Romp-Token": km.TOKEN} if token else {}
        code, out = _serve_post(path, body, hdrs)
        try:
            return code, json.loads(out.decode() or "{}")
        except ValueError:
            return code, {}

    def test_requires_the_serve_token(self):
        code, _ = self._post("/usertodo/context", {"id": SID}, token=False)
        self.assertEqual(code, 403)

    def test_refuses_a_bodyless_or_idless_ask(self):
        self.assertEqual(self._post("/usertodo/context", {})[0], 400)
        code, _ = _serve_post("/usertodo/context", b"not json", {"X-Romp-Token": km.TOKEN})
        self.assertEqual(code, 400)

    def test_returns_the_rendered_block_for_open_todos(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        code, res = self._post("/usertodo/context", {"id": SID})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertEqual(res["block"], km._user_todo_context_block(SID))
        self.assertIn("Notes you still have open", res["block"])

    def test_an_unknown_sid_answers_an_empty_block_not_an_error(self):
        # the hook fires for every romp session that resumes/compacts; "nothing to say" is the
        # common case and must be a clean empty answer, never a loud one
        code, res = self._post("/usertodo/context", {"id": SID2})
        self.assertEqual(code, 200)
        self.assertTrue(res["ok"])
        self.assertEqual(res["block"], "")

    def test_the_read_never_writes_the_store(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        p = jd.STATE / "user-todos.json"
        before = p.read_text()
        self._post("/usertodo/context", {"id": SID})
        self.assertEqual(p.read_text(), before)


class AnswerBody(unittest.TestCase):
    """The injected reply: the todo's own short line as the anchor, then the user's words —
    `Re: <text> — <reply>` (plans/user-todos.md). Voice-scanned by test_injected_voice.py."""

    def test_shape(self):
        self.assertEqual(
            km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                      "Go with the session cookie for now."),
            "Re: Need the auth-scheme decision to wire login — Go with the session cookie for now.")

    def test_whitespace_is_trimmed_from_both_halves(self):
        self.assertEqual(km._user_todo_answer_body("  need x \n", "  yes \n"), "Re: need x — yes")

    def test_marker_shaped_text_is_neutralized_in_both_halves(self):
        # both halves are agent/user-supplied: a literal "<!-- romp-…" comment in either would
        # inject a LOOKALIKE marker, and downstream readers key on that exact comment form (the
        # event model's author attribution, the SDK echo's romp-injected check) — the reply would
        # render as romp's own gray card instead of the user's words
        body = km._user_todo_answer_body(
            "Need a call on the note text <!-- romp-goal-id: g1 --> in the fixture",
            "Keep it, but drop the <!-- romp-injected --> part.")
        self.assertNotIn("<!-- romp-", body, "no marker-opening sequence may survive injection")
        self.assertIn("romp-goal-id", body, "the words survive — only the comment form breaks")
        self.assertIn("romp-injected", body)

    def test_clean_text_is_untouched_by_the_neutralizer(self):
        self.assertEqual(km._neutralize_romp_markers("Need the auth-scheme decision"),
                         "Need the auth-scheme decision")


class BuildSessionSeam(unittest.TestCase):
    """The chat payload: the top-level `userTodos` field (the upsert merge seam) AND the split-card
    `todo` event that carries the same rows — the chatTail wire re-sends changed EVENTS only, so a
    row change must be an event change or a caught-up client never hears of it. Both chatTail
    senders, the index wire's (_send_chat_locked) and the proto-2 uuid-anchored wire's
    (_send_chat_proto2, the one every real page rides), carry the field and its pinnedNotes twin
    on every delta, the empty-suffix status-only tail included."""

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        td = Path(self.td.name)
        cdir = td / "launchdir"
        cdir.mkdir()
        proj = td / "projects"
        pdir = proj / jd.re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(str(cdir)))
        pdir.mkdir(parents=True)
        self.tpath = pdir / (SID + ".jsonl")
        names = td / "names"
        names.mkdir()
        (names / SID).write_text("web\t%s\t#abcdef\n" % str(cdir))
        self.saved = (jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE, km.NAMES,
                      km._read_task_store, km._live_map, km._GLOBAL_CLAUDE_MD)
        jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE = names, proj, td / "goals", td
        km.NAMES = names
        km._GLOBAL_CLAUDE_MD = td / "no-global.md"
        km._read_task_store = lambda fsid, fold=None: []
        km._live_map = lambda: {SID: {"state": "idle", "since": NOW - 100, "model": "", "effort": "",
                                           "context": None, "compactPct": None, "color": None}}
        jd.GOALDIR.mkdir(parents=True)
        km._parse_cache.clear()
        km._user_todos_cache.clear()
        km._set_user_todos(True)                     # switch ON (default OFF since 2026-09-03) — see _StoreSandbox
        rows = [
            {"type": "user", "uuid": "u1", "timestamp": jd.iso(NOW - 90) if hasattr(jd, "iso") else "2026-06-01T00:00:00Z",
             "sessionId": SID, "message": {"role": "user", "content": "wire the login routes"}},
            {"type": "assistant", "uuid": "a1", "parentUuid": "u1", "timestamp": "2026-06-01T00:00:05Z",
             "sessionId": SID,
             "message": {"role": "assistant", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": "starting on the open routes"}]}},
        ]
        self.tpath.write_text("\n".join(json.dumps(r) for r in rows) + "\n")

    def tearDown(self):
        (jd.NAMES, jd.PROJECTS, jd.GOALDIR, jd.STATE, km.NAMES,
         km._read_task_store, km._live_map, km._GLOBAL_CLAUDE_MD) = self.saved
        km._parse_cache.clear()
        km._user_todos_cache.clear()
        self.td.cleanup()

    def _todo_events(self, payload):
        return [e for e in payload["events"] if e.get("kind") == "todo"]

    def test_no_todos_and_no_tasks_mean_no_event_and_an_empty_field(self):
        payload = km.build_session(SID, NOW)
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(self._todo_events(payload), [])

    def test_open_todos_ride_both_the_field_and_the_event(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login", "OAuth vs cookie")
        payload = km.build_session(SID, NOW)
        self.assertEqual([t["id"] for t in payload["userTodos"]], [tid])
        evs = self._todo_events(payload)
        self.assertEqual(len(evs), 1, "one split card, by the composer")
        self.assertEqual(evs[0]["tasks"], [])
        self.assertEqual(evs[0]["userTodos"], payload["userTodos"],
                         "the event carries the rows — the chatTail delta re-sends events only")
        self.assertIs(payload["events"][-1], evs[0], "appended last: the card sits by the composer")

    def test_agent_tasks_and_user_todos_share_one_card(self):
        km._read_task_store = lambda fsid, fold=None: [
            {"id": "1", "subject": "Build the fixtures", "activeForm": None, "status": "pending"}]
        km._add_user_todo(SID, "Need a test credential for the api session")
        payload = km.build_session(SID, NOW)
        evs = self._todo_events(payload)
        self.assertEqual(len(evs), 1)
        self.assertEqual(len(evs[0]["tasks"]), 1)
        self.assertEqual(len(evs[0]["userTodos"]), 1)

    def test_resolved_todos_ship_nowhere(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        payload = km.build_session(SID, NOW)
        self.assertEqual(payload["userTodos"], [])
        self.assertEqual(self._todo_events(payload), [])

    def test_the_field_is_clock_invariant(self):
        # _send_client dedups by the serialized payload (the firstSeen lesson): the field must
        # serialize identically across builds when nothing changed
        km._add_user_todo(SID, "Need the auth-scheme decision")
        a = km.build_session(SID, NOW)
        b = km.build_session(SID, NOW + 600)
        self.assertEqual(json.dumps(a["userTodos"]), json.dumps(b["userTodos"]))

    def test_an_ended_session_hides_its_todos_without_clearing_them(self):
        km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        payload = km.build_session(SID, NOW)
        self.assertEqual(payload["userTodos"], [], "ended (registry alive:false) → hidden everywhere")
        self.assertEqual(self._todo_events(payload), [])
        self.assertEqual(len(km._open_user_todos(SID)), 1, "hidden, not cleared — revive returns them")
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": True}))
        self.assertEqual(len(km.build_session(SID, NOW)["userTodos"]), 1,
                         "a dormant session (alive:true, no thread) still shows its todos")

    def test_a_muted_session_still_ships_its_todos_to_the_tab(self):
        # THE DESIGNED ASYMMETRY (review call, 2026-08-22 — do not "fix"): hideFromFeed quiets
        # the feed and every aggregate built from it — the card marker, the escalation floor,
        # the badge (FeedSeamUserTodos pins that side) — because mute means "stop interrupting
        # me about this session". The CHAT payload, the tab glyph's source, still carries the
        # open todos: the tab remains truthful about what its session holds.
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        (jd.STATE / "session-flags.json").write_text(json.dumps({SID: {"hideFromFeed": True}}))
        km._flags_cache.clear()
        payload = km.build_session(SID, NOW)
        self.assertEqual(len(payload["userTodos"]), 1, "muted ≠ hidden on the session's own tab")
        self.assertEqual(len(self._todo_events(payload)), 1, "the split card renders too")

    def test_a_row_carries_detail_iff_the_ask_has_one(self):
        # The row's "more behind this" hint (render.ts renderTodo → user-todo-hint.ts) keys on the
        # PRESENCE of `detail` on the payload row — that presence is the has-detail flag (no
        # separate boolean: the row already carries the text, and a second field could drift from
        # it). So it must track the store exactly: present, with the text, when the ask carries a
        # non-blank detail; ABSENT (not empty, not null) for a bare one-line ask — and a blank or
        # whitespace-only detail written straight into the store is no detail either, so the seam
        # (_open_user_todos), not just the register route, is what drops it.
        (jd.STATE / "user-todos.json").write_text(json.dumps({SID: [
            {"id": "ut-aaaaaaaa", "text": "Need the auth-scheme decision to wire login",
             "createdT": NOW - 40, "detail": "OAuth vs cookie — either unblocks login"},
            {"id": "ut-bbbbbbbb", "text": "Need a test credential for the api session", "createdT": NOW - 30},
            {"id": "ut-cccccccc", "text": "Need your pick of the two route layouts",
             "createdT": NOW - 20, "detail": "  \n\t "},
            {"id": "ut-dddddddd", "text": "Need the staging port", "createdT": NOW - 10, "detail": ""}]}))
        km._user_todos_cache.clear()
        payload = km.build_session(SID, NOW)
        rows = {t["id"]: t for t in payload["userTodos"]}
        self.assertEqual(set(rows), {"ut-aaaaaaaa", "ut-bbbbbbbb", "ut-cccccccc", "ut-dddddddd"})
        self.assertEqual(rows["ut-aaaaaaaa"]["detail"], "OAuth vs cookie — either unblocks login")
        self.assertNotIn("detail", rows["ut-bbbbbbbb"], "a bare ask ships no detail key at all")
        self.assertNotIn("detail", rows["ut-cccccccc"], "whitespace-only detail is no detail")
        self.assertNotIn("detail", rows["ut-dddddddd"], "an empty detail is no detail")
        ev_rows = {t["id"]: t for t in self._todo_events(payload)[0]["userTodos"]}
        self.assertEqual({k: ("detail" in v) for k, v in ev_rows.items()},
                         {k: ("detail" in v) for k, v in rows.items()},
                         "the split-card event rows carry the same has-detail truth as the field")

    def test_a_todo_write_busts_the_chat_build_cache(self):
        # _chat_build_sig is (transcript, states, …) — a todo write changes NEITHER, so without the
        # store in the signature a background tab's cached chat never showed the new row
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        saved_sdk = km._sdk
        km._sdk = lambda: None
        try:
            before = km._chat_build_sig(sess)
            km._add_user_todo(SID, "Need the auth-scheme decision")
            after = km._chat_build_sig(sess)
        finally:
            km._sdk = saved_sdk
        self.assertNotEqual(before, after)

    def test_another_sessions_todo_write_busts_no_one_elses_cache(self):
        # the fold is PER-SID (_user_todo_fp): a shared-file stat here made every session's write
        # rebuild every tab's chat once — extra load a hot route's caller then waited behind
        sess = {"path": str(self.tpath), "sid": SID, "anchor": ""}
        saved_sdk = km._sdk
        km._sdk = lambda: None
        try:
            before = km._chat_build_sig(sess)
            km._add_user_todo(SID2, "api: need the auth decision")
            after = km._chat_build_sig(sess)
        finally:
            km._sdk = saved_sdk
        self.assertEqual(before, after, "another session's row is not this tab's repaint")

    def test_the_chat_tail_delta_carries_the_user_todos_field(self):
        # the chat wire's steady state is chatTail deltas: a caught-up client that only merged
        # full session frames kept a stale top-level field (the tab glyph's read, next slice)
        rows = [{"id": "ut-aaaaaaaa", "text": "Need the auth-scheme decision", "createdT": NOW}]
        notes = [{"id": "pn-aaaaaaaa", "text": "the staging port is 8443", "createdT": NOW}]
        evs = [{"uuid": "u1", "kind": "user", "text": "wire the login routes"},
               {"uuid": "a1", "kind": "todo", "tasks": [], "userTodos": rows}]
        m = {"type": "session", "id": SID, "events": evs, "status": {"state": "idle"},
             "userTodos": rows, "pinnedNotes": notes}   # set on the message: a dropped seam cannot hide behind the [] default
        got = []
        c = {"send": lambda s: got.append(json.loads(s)), "sent": {},
             "echat": {SID: ("u1", 0)}}                # caught up from event 0 → the delta path
        km._send_chat(c, m, None, 1, False)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["type"], "chatTail", "the caught-up client got the delta")
        self.assertEqual(got[0]["userTodos"], rows,
                         "the field rides the delta — byte-stable store values, dedup-safe")
        self.assertEqual(got[0]["pinnedNotes"], notes, "the pinned-notes strip's field rides the same delta")

    def test_the_proto2_chat_tail_delta_carries_both_fields(self):
        # the proto-2 twin of the case above (review round 1 of the 2026-09-15 pull-in): every real page says
        # proto 2 in its ready (T323 stage 4b), so upstream's _send_chat_proto2 is the sender the seam serves
        # in production, and the index-wire case alone left it unexecuted. The client's base is the {first,
        # last} uuids of its tail run; a change inside or right after the run is a chatTail {afterUuid, events}
        # that must carry the two top-level fields, or a caught-up tab's glyph and strip go stale
        rows = [{"id": "ut-aaaaaaaa", "text": "Need the auth-scheme decision", "createdT": NOW}]
        notes = [{"id": "pn-aaaaaaaa", "text": "the staging port is 8443", "createdT": NOW}]
        evs = [{"uuid": "u1", "kind": "user", "text": "wire the login routes"},
               {"uuid": "a1", "kind": "todo", "tasks": [], "userTodos": rows}]
        m = {"type": "session", "id": SID, "events": evs, "status": {"state": "idle"},
             "userTodos": rows, "pinnedNotes": notes}
        got = []
        c = {"send": lambda s: got.append(json.loads(s)), "sent": {}, "proto": 2,
             "echat": {SID: {"first": "u1", "last": "u1"}}}   # the base ends on the last TRANSCRIPT event: the todo
        km._send_chat(c, m, None, 1, False)                  # card is an overlay that rides the suffix (_last_anchor)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["type"], "chatTail", "the caught-up proto-2 client got the uuid-anchored delta")
        self.assertEqual(got[0]["afterUuid"], "u1")
        self.assertEqual([e["uuid"] for e in got[0]["events"]], ["a1"], "the suffix after the held run")
        self.assertEqual(got[0]["userTodos"], rows, "the field rides the proto-2 delta")
        self.assertEqual(got[0]["pinnedNotes"], notes, "and so does the pinned-notes strip's")

    def test_the_status_only_tail_with_an_empty_suffix_carries_both_fields(self):
        # change_from at the total: no event changed, only the status, a view flag or a store did. Both wires
        # send a chatTail with an EMPTY suffix for that, and the two fields ride it the same way, so a todo or
        # a note written between two pushes with no transcript change still reaches a caught-up tab
        rows = [{"id": "ut-aaaaaaaa", "text": "Need the auth-scheme decision", "createdT": NOW}]
        notes = [{"id": "pn-aaaaaaaa", "text": "the staging port is 8443", "createdT": NOW}]
        evs = [{"uuid": "u1", "kind": "user", "text": "wire the login routes"},
               {"uuid": "a1", "kind": "assistant", "text": "starting on the open routes"}]
        m = {"type": "session", "id": SID, "events": evs, "status": {"state": "idle"},
             "userTodos": rows, "pinnedNotes": notes}
        for proto, base in ((2, {"first": "u1", "last": "a1"}), (1, ("u1", 0))):
            with self.subTest(proto=proto):
                got = []
                c = {"send": lambda s, got=got: got.append(json.loads(s)), "sent": {}, "echat": {SID: base}}
                if proto == 2:
                    c["proto"] = 2                       # an index client carries no proto key (the ready sets it)
                km._send_chat(c, m, None, len(evs), False)   # change_from == total: nothing after the held run
                self.assertEqual(len(got), 1)
                self.assertEqual(got[0]["type"], "chatTail")
                self.assertEqual(got[0]["events"], [], "the status-only tail carries no events")
                self.assertEqual(got[0]["status"], {"state": "idle"})
                self.assertEqual(got[0]["userTodos"], rows)
                self.assertEqual(got[0]["pinnedNotes"], notes)

    def test_both_chat_tail_senders_carry_the_two_fields_by_source(self):
        # the wire-seams pin over BOTH senders (tests/test_pinned_notes.py WireSeams reads both too since
        # 2026-09-16): the proto-2 sender is its own function since the 2026-09-15 pull-in, so a seam line dropped
        # from it would leave every index-wire case green while every real page went stale
        for fn in (km._send_chat_locked, km._send_chat_proto2):
            with self.subTest(fn=fn.__name__):
                src = inspect.getsource(fn)
                self.assertIn('"userTodos": m.get("userTodos") or []', src)
                self.assertIn('"pinnedNotes": m.get("pinnedNotes") or []', src)


class DriveOps(_StoreSandbox):
    """userTodoAnswer / userTodoDismiss — the user's two gestures on the split card. The answer
    stamp is DELIVERY-keyed: `self.send_result` scripts what _send_or_park reports (True parked,
    False handed over now, None refused: upstream's contract since the 2026-09-15 pull-in) so each
    outcome's contract pins separately."""

    def setUp(self):
        super().setUp()
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}
        self._saved = (km._name_of, km._sdk, km._send_or_park)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        self.injected = []
        self.send_result = False                     # default: the immediate path handed the answer over now

        def fake_send_or_park(be, sid, text, echo=None, qid=None, user=False, paths=None, user_todo=None):
            self.injected.append((sid, text, user_todo))
            return self.send_result

        km._send_or_park = fake_send_or_park

    def tearDown(self):
        km._name_of, km._sdk, km._send_or_park = self._saved
        super().tearDown()

    def test_both_ops_are_id_ops(self):
        src = inspect.getsource(km._drive)
        self.assertIn('"userTodoAnswer"', src)
        self.assertIn('"userTodoDismiss"', src)

    def test_dismiss_stamps_dismissed_and_injects_nothing(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        handled = km._drive({"type": "userTodoDismiss", "id": SID, "todoId": tid}, self.client)
        self.assertTrue(handled)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")
        self.assertEqual(self.injected, [], "dismiss sends nothing into the session")
        self.assertEqual(self.sent, [], "a clean dismiss raises no warning")

    def test_dismiss_of_a_cleared_id_warns_loudly(self):
        km._drive({"type": "userTodoDismiss", "id": SID, "todoId": "ut-deadbeef"}, self.client)
        self.assertEqual(len(self.sent), 1)
        self.assertEqual(self.sent[0]["type"], "warn")

    def test_answer_injects_the_anchored_reply_and_stamps_on_a_truthy_send(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Go with the session cookie for now."}, self.client)
        self.assertEqual(len(self.injected), 1)
        self.assertEqual(self.injected[0][0], SID)
        self.assertEqual(self.injected[0][1],
                         "Re: Need the auth-scheme decision to wire login — "
                         "Go with the session cookie for now.")
        self.assertEqual(self.injected[0][2], tid, "the todo id rides the send for the park path")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "delivered now → stamped now — the user's gesture, never a judgment")

    def test_a_parked_answer_does_not_stamp_yet(self):
        # the park is still recallable (the queued bubble's ✕) — the stamp waits for the drain
        self.send_result = True                      # parked
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Session cookie."}, self.client)
        self.assertEqual(len(self.injected), 1, "the answer went to the FIFO")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "parked ≠ delivered: stamping here loses the answer to a later recall")
        self.assertEqual(self.sent, [], "a park is normal flow, not an error")

    def test_a_refused_send_warns_and_leaves_the_todo_open(self):
        # the backend said no (an unrevivable SDK session): be loud, the ask still stands
        self.send_result = None                      # refused
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Session cookie."}, self.client)
        self.assertNotIn("resolved", km._user_todos()[SID][0])
        self.assertEqual(self.sent[0]["type"], "warn")

    def test_answer_to_an_ended_sdk_session_is_refused_loudly(self):
        # sending into a dead session loses the answer while the stamp reads 'answered' — refuse
        # BEFORE the send, keep the todo open, tell the user how to make it answerable (revive)
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": False}))
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Session cookie."}, self.client)
        self.assertEqual(self.injected, [], "nothing may be sent into the void")
        self.assertEqual(self.sent[0]["type"], "warn")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the ask still stands")

    def test_answer_to_a_dead_regless_session_is_refused_loudly(self):
        # _thread_reg is {} for a session with no SDK record: the gate must also read the durable death
        # record (STATE/gone), or a send "succeeds" into the void and the stamp fires (the tmux-backed
        # case until that backend's removal 2026-09-11; the reg-less arm stays)
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW, "by": "gone"}))
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Session cookie."}, self.client)
        self.assertEqual(self.injected, [], "nothing may be sent into the void")
        self.assertEqual(self.sent[0]["type"], "warn")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the ask still stands")

    def test_a_dormant_sdk_session_still_takes_the_answer(self):
        # dormant (alive:true, no thread) is addressable — the send path auto-revives it
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID + ".json")).write_text(json.dumps({"alive": True}))
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                   "text": "Session cookie."}, self.client)
        self.assertEqual(len(self.injected), 1)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_answer_to_a_cleared_id_sends_nothing_and_warns(self):
        km._drive({"type": "userTodoAnswer", "id": SID, "todoId": "ut-deadbeef",
                   "text": "too late"}, self.client)
        self.assertEqual(self.injected, [])
        self.assertEqual(self.sent[0]["type"], "warn")

    def test_an_empty_answer_is_not_a_drive_op(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        self.assertFalse(km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                                    "text": "   "}, self.client))
        self.assertEqual(km._open_user_todos(SID)[0]["id"], tid, "nothing was stamped")


class _TodoStr(str):
    """The queue-entry contract the kernel reads back: a plain str for every consumer, with the
    todo id it answers riding as a `todo` attribute (getattr(entry, "todo", "") — duck-typed, so
    this local double pins the CONTRACT, not the SDK's own class)."""

    def __new__(cls, text, todo):
        o = str.__new__(cls, text)
        o.todo = todo
        return o


class _FakeBackend:
    """A forwards_sends backend double for the park/drain/recall pipeline: send() records and
    reports what the test scripts; pending_queued/unqueue model the SDK's recallable queue —
    including the todo id riding ON the queue entry (its send NAMES user_todo, the signature read
    _send_with_id makes): the entry itself, not any kernel-side table, is what a recall reads the
    id back off."""

    def __init__(self, send_ok=True):
        self.sent = []
        self.send_ok = send_ok
        self.queue = []

    def forwards_sends(self):
        return True

    def send(self, sid, text, user_todo=None):
        if not self.send_ok:
            return False
        if user_todo:
            text = _TodoStr(text, user_todo)
        self.sent.append((sid, text))
        self.queue.append(text)
        return True

    def pending_queued(self, sid):
        return list(self.queue)

    def unqueue(self, sid, idx, expect=None):
        if 0 <= idx < len(self.queue) and (expect is None or self.queue[idx] == expect):
            return self.queue.pop(idx)
        return None


class DeliveryKeyedStamp(_StoreSandbox):
    """The answer stamp keys on DELIVERY (docs/adr/0001's fatal class), end to end through the
    real park machinery: a parked answer carries its todo id, stamps only when the park drains
    into a truthy send, and every recall/drop path leaves (or returns) the todo OPEN — the user
    changed their mind about the ANSWER; the ask still stands."""

    def setUp(self):
        super().setUp()
        self._saved = (km._name_of, km._sdk, km._compacting_now, dict(km._pending_ops), km.Sessions.backend_for)
        km._name_of = lambda sid: "web" if sid == SID else None
        km._sdk = lambda: None
        # a sid no backend owns routes to the unowned backend, whose send REFUSES (None) before anything parks
        # (upstream #1401): the fake owns the session, so a park is a park
        self.be = _FakeBackend()
        km.Sessions.backend_for = staticmethod(lambda sid: self.be)
        km._pending_ops.clear()                       # a hermetic FIFO: the drain walks EVERY sid
        self.sent = []
        self.client = {"send": lambda s: self.sent.append(json.loads(s))}

    def tearDown(self):
        km._name_of, km._sdk, km._compacting_now = self._saved[:3]
        km._pending_ops.clear()
        km._pending_ops.update(self._saved[3])
        km.Sessions.backend_for = self._saved[4]
        super().tearDown()

    def _park_an_answer(self):
        km._compacting_now = lambda sid: sid == SID
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        handled = km._drive({"type": "userTodoAnswer", "id": SID, "todoId": tid,
                             "text": "Go with the session cookie."}, self.client)
        self.assertTrue(handled)
        ops = km._pending_ops.get(SID) or []
        self.assertTrue(ops and ops[0][0] == "send", "the answer parked (compaction)")
        self.assertEqual(km._op_todo(ops[0]), tid, "the parked op carries the todo id for the drain stamp (its seventh slot)")
        self.assertNotIn("resolved", km._user_todos()[SID][0], "no stamp at park time")
        return tid, ops

    def test_cancelling_the_parked_answer_leaves_the_todo_open(self):
        # the R3 repro shape: park, then the user clicks ✕ on the queued bubble — the answer is
        # recalled before it ever reached the agent, so the ask must still stand
        tid, ops = self._park_an_answer()
        err = km._cancel_parked(SID, 0, km._parked_md(ops[0]))
        self.assertIsNone(err, "the cancel succeeds")
        self.assertFalse(km._pending_ops.get(SID), "the answer will never be delivered")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "recalled ≠ answered: the row returns, nothing is silently lost")

    def test_the_drain_delivers_and_stamps(self):
        tid, _ = self._park_an_answer()
        km._compacting_now = lambda sid, **k: False        # compaction ended — the FIFO may drain
        be = _FakeBackend()
        saved = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(lambda sid: be)
        try:
            km._apply_pending_ops()
        finally:
            km.Sessions.backend_for = saved
        self.assertEqual(len(be.sent), 1, "the parked answer drained into a real send")
        self.assertIn("Re: Need the auth-scheme decision", be.sent[0][1])
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "THE delivery event — the drain — is where the stamp fires")

    def test_a_dropped_dead_session_queue_leaves_the_todo_open(self):
        tid, _ = self._park_an_answer()
        km._compacting_now = lambda sid, **k: False
        saved = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(
            lambda sid: (_ for _ in ()).throw(RuntimeError("session is gone")))
        try:
            km._apply_pending_ops()
        finally:
            km.Sessions.backend_for = saved
        self.assertFalse(km._pending_ops.get(SID), "the dead session's queue was dropped")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "dropped ≠ delivered: the ask survives the session")

    def test_an_unqueued_answer_reopens_the_todo(self):
        # the immediate SDK path: send() enqueues backend-side (truthy → stamped), but the queued
        # bubble's ✕ can still recall it before it forwards — the recall must re-open the todo,
        # reading the id off the entry it removed (never a kernel-side table)
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                         "Go with the session cookie.")
        be = _FakeBackend()
        self.assertTrue(km._send_with_id(be, SID, body, user_todo=tid))   # the delivered-now path…
        km._stamp_user_todo_answered(SID, tid, body)                      # …stamps at the truthy send
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err, "the unqueue succeeds")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "recalled before it forwarded → the ask stands again")

    def test_reopen_never_lifts_a_dismiss_or_withdraw(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        self.assertFalse(km._reopen_user_todo(SID, tid),
                         "only an 'answered' stamp — a failed delivery — may be lifted")
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")


class RecallRidesTheEntry(_StoreSandbox):
    """Round-2 findings 1+3, one root: the old recall bookkeeping was an IN-MEMORY map while the
    SDK queue it tracked is PERSISTED (reg mirror, reseeded at boot) — so a post-restart recall
    reopened nothing, and the map's global FIFO cap could evict a live entry. The id now travels
    WITH the queued message (the entry itself carries it; the recall reads it back off the entry
    it removes), so there is nothing kernel-side to lose, restart away, or evict."""

    def _answered_via_backend(self, be=None):
        be = be or _FakeBackend()
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                         "Go with the session cookie.")
        self.assertTrue(km._send_with_id(be, SID, body, user_todo=tid))
        km._stamp_user_todo_answered(SID, tid, body)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")
        return be, tid, body

    def test_a_post_restart_recall_still_reopens(self):
        # the round-2 test_A shape: the queue survives a kernel restart (reg mirror), the old map
        # did not — so the recall must work with NO in-kernel memory of the send. The fresh
        # kernel's _cancel_backend_queued sees only the entry, and the entry knows its todo.
        be, tid, body = self._answered_via_backend()
        # "kernel restart": there is deliberately no kernel-side record left to clear — the
        # structural pin below proves the side table is gone, so this cancel IS the fresh kernel
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err, "the post-restart unqueue succeeds (the queue was persisted)")
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the recall reopens the ask — never a false permanent 'answered'")

    def test_the_recall_side_table_is_gone(self):
        # finding 3's entire class (a FIFO cap evicting a live entry) dies with the table
        for name in ("_user_todo_recalls", "_USER_TODO_RECALLS_CAP", "_record_user_todo_recall"):
            self.assertFalse(hasattr(km, name),
                             "%s must not come back — the id rides the queue entry" % name)

    def test_many_later_answers_cannot_evict_the_recall(self):
        # the round-2 test_D shape: 64+ later stamps used to evict the live map entry; the id
        # rides the entry now, so no volume of unrelated answers can disarm a recall
        be, tid, body = self._answered_via_backend()
        for i in range(65):
            t2 = km._add_user_todo("00000000-0000-4000-8000-%012d" % i, "todo %d" % i)
            km._stamp_user_todo_answered("00000000-0000-4000-8000-%012d" % i, t2, "body %d" % i)
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err)
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the recall survives any number of later answers")

    def test_a_lookalike_recall_reopens_nothing(self):
        # the round-2 test_C residual, closed by the same root: the answer was DELIVERED (its
        # entry consumed); a later byte-identical NORMAL send carries no todo id, so recalling
        # that one reopens nothing
        be, tid, body = self._answered_via_backend()
        be.queue.pop(0)                               # the input generator forwards it: delivered
        be.send(SID, body)                            # a plain send, byte-identical, no user_todo
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "the delivered answer stands — nothing rode the lookalike entry")

    def test_a_recalled_entry_never_lifts_a_dismiss(self):
        # the round-2 test_B shape, end to end: parked answer (no stamp), user dismisses, the
        # drain delivers anyway (the entry carries the id), then the user recalls the queued
        # message — the reopen's answered-only guard keeps the dismiss
        be = _FakeBackend()
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        self.assertTrue(km._resolve_user_todo(SID, tid, "dismissed"))
        km._deliver_send_batch(be, SID, [("send", body, None, None, True, None, tid)])   # the seventh slot (2c item 1)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed",
                         "the drain's stamp attempt must not overwrite the dismiss")
        err = km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1])
        self.assertIsNone(err)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed",
                         "reopen must never lift a dismiss — answered-only")

    def test_the_drain_hands_the_id_to_the_backend_entry(self):
        # the park path feeds the same root: a drained answer's queue entry carries the id
        # exactly like an immediate send's, so its recall reopens the same way
        be = _FakeBackend()
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        body = km._user_todo_answer_body("Need the auth-scheme decision", "Cookie.")
        km._deliver_send_batch(be, SID, [("send", body, None, None, True, None, tid)])   # the seventh slot (2c item 1)
        self.assertEqual(getattr(be.queue[0], "todo", ""), tid,
                         "the drained entry carries the todo id end to end")

    def test_a_backend_whose_send_names_no_todo_takes_the_plain_send(self):
        # a send that does not NAME user_todo in its signature (the _takes_kw read _send_with_id makes) is
        # handed the bare text; the fork's queue_carries_todos flag and _backend_send retired 2026-09-15
        class _Plain:
            def __init__(self):
                self.sent = []

            def send(self, sid, text):
                self.sent.append((sid, text))
                return True

        be = _Plain()
        self.assertTrue(km._send_with_id(be, SID, "hello", user_todo="ut-12345678"))
        self.assertEqual(be.sent, [(SID, "hello")])


class LostAnswerReopens(_StoreSandbox):
    """Round-2 finding 2: a kernel death in the fed-but-unlanded window strands a stamped answer —
    the dropped-echo machinery detects the loss but could not tie it back to the ask. The echo now
    carries the todo id, the backend hands it to _user_todo_answer_lost, and the ask visibly
    returns to \"Waiting on you\" — UNLESS the transcript proves the text actually landed (then the
    agent has the answer and the stamp is true; a landed-but-unpruned echo at kernel death is
    common, so reopening blindly would flap answered asks open on every restart)."""

    def setUp(self):
        super().setUp()
        self._saved = (km._sessions, km._parse)
        self.turns = []
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "path": "/dev/null"}]
        km._parse = lambda path, sid, now: {"turns": self.turns}

    def tearDown(self):
        km._sessions, km._parse = self._saved
        super().tearDown()

    def _stamped(self):
        tid = km._add_user_todo(SID, "Need the auth-scheme decision")
        body = km._user_todo_answer_body("Need the auth-scheme decision", "Cookie.")
        km._stamp_user_todo_answered(SID, tid, body)
        return tid, body

    def _land(self, text):
        self.turns = [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                                  "message": {"role": "user",
                                              "content": [{"type": "text", "text": text}]}}]}]

    def test_a_lost_answer_reopens_the_ask(self):
        tid, body = self._stamped()
        km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the answer died with its holder — the ask visibly returns")

    def test_a_landed_answer_keeps_its_stamp(self):
        tid, body = self._stamped()
        self._land(body)
        km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "the transcript has the answer — delivered, not lost")

    def test_a_landed_text_block_inside_a_bundle_counts(self):
        # romp bundles injected messages into one user record; per-block matching (the
        # _atom_user_texts contract) must recognize the landed answer inside it
        tid, body = self._stamped()
        self.turns = [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                                  "message": {"role": "user", "content": [
                                      {"type": "text", "text": "a restart notice"},
                                      {"type": "text", "text": body}]}}]}]
        km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_an_edge_whitespace_answer_reads_as_landed(self):
        # the CLI records user text verbatim, edge whitespace included, and _atom_user_texts keys it
        # under echo_text_key (strip). A match set built from the raw text never met such a key, so a
        # delivered answer whose send carried a trailing newline was reopened at every boot
        # (2026-09-06 review, round 4): the landed check's forms start from the same key
        tid, body = self._stamped()
        self._land(body + "\n")
        km._user_todo_answer_lost(SID, tid, body + "\n", wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "one key on both sides — delivered, the stamp stands")

    def test_the_loss_path_never_lifts_a_dismiss(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        km._resolve_user_todo(SID, tid, "dismissed")
        km._user_todo_answer_lost(SID, tid, "Re: Need the staging port — 8443.", wait=True)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "dismissed")

    def test_an_unparsable_transcript_fails_toward_the_visible_ask(self):
        # fail loudly, never degrade silently: a broken landed-check reopens (a wrongly-open ask
        # is visible and dismissable; a wrongly-'answered' one is the silent loss the ADR names)
        tid, body = self._stamped()

        def boom(path, sid, now):
            raise RuntimeError("corrupt transcript")

        km._parse = boom
        km._user_todo_answer_lost(SID, tid, body, wait=True)
        self.assertNotIn("resolved", km._user_todos()[SID][0])

    def test_the_backend_wire_is_connected(self):
        # the callback must ride CONSTRUCTION (the boot reseed fires drop marks from __init__,
        # before any post-construction attribute assignment could arm it)
        src = inspect.getsource(km._sdk_locked)
        # Re-pinned 2026-09-15 (the pull-in): the hand-off wears the thread's default stage mark, as push_session's does
        # (upstream's T401 (5a) census: _user_todo_answer_lost parses the transcript on the backend's own thread, so the
        # mark rides the hand-off, not a decorator on the def). What the text pins is unchanged: the wire is construction-time.
        self.assertIn('todo_lost=_stage_default("todo.lost")(_user_todo_answer_lost)', src)

    def test_a_sid_outside_the_48h_window_still_gets_the_landed_check(self):
        # round 3: the check resolved its session via _sessions(now) — discover's DEFAULT 48h
        # window — so a >48h-idle transcript skipped it silently and a genuinely-landed answer's
        # ask reopened (a card move with no new information). The check now falls back to
        # discover's cached wide walk (the _alive_sessions / DEATH_BACKFILL_WINDOW idiom): it
        # runs whenever the transcript exists at all.
        tid, body = self._stamped()
        self._land(body)
        km._sessions = self._saved[0]        # the REAL _sessions: the window miss must come from
        saved = km.jd.discover               # discover itself, not from the class stub
        try:
            km.jd.discover = (lambda now, window=None, forks=True:
                              [] if window is None else [(SID, "/dev/null", SID, "web")])
            km._user_todo_answer_lost(SID, tid, body, wait=True)
        finally:
            km.jd.discover = saved
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "the transcript exists (wide walk) and holds the answer — delivered, "
                         "the stamp stands")

    def test_no_transcript_anywhere_reopens_and_logs_the_skipped_check(self):
        # fail toward the VISIBLE ask, but never silently: when the landed check cannot run at
        # all (no transcript even in the wide walk), the skip itself is logged before reopening
        tid, body = self._stamped()
        km._sessions = self._saved[0]
        saved = km.jd.discover
        try:
            km.jd.discover = lambda now, window=None, forks=True: []
            err = io.StringIO()
            with contextlib.redirect_stderr(err):
                km._user_todo_answer_lost(SID, tid, body, wait=True)
        finally:
            km.jd.discover = saved
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "no transcript to check → reopen anyway (fail toward visible)")
        self.assertIn("cannot run", err.getvalue(), "…but the skipped check is SAID, not silent")
        self.assertIn(tid, err.getvalue())

    def test_a_reopen_that_finds_no_answered_row_is_loud(self):
        # round 3: the recall path already logged a no-op reopen; the loss path swallowed it. A
        # capped-out/cleared row means the answer never landed AND no row remains to show the
        # ask — this log line is the only record left.
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km._user_todo_answer_lost(SID, "ut-00000000", "Re: Need the staging port — 8443.",
                                      wait=True)
        self.assertIn("nothing reopened", err.getvalue())
        self.assertIn("ut-00000000", err.getvalue())


class LossBootPass(_StoreSandbox):
    """Round-3 finding 1 (2026-08-22): _mark_dropped_echoes persists an echo's drop mark
    IMMEDIATELY and fires the loss seam exactly once — for the not-yet-marked echo — while the
    reopen itself runs on a fire-and-forget daemon thread that at boot waits out _sdk_lock
    through the whole staggered reconcile. A kernel death in that window left the mark persisted
    with the reopen undone, and the next boot's one-shot marking skipped the already-marked
    echo: the ask stayed falsely 'answered' forever. _user_todo_loss_boot_pass is the durability
    backstop: every boot re-derives the pending set from the PERSISTED world alone (an echo
    drop-marked AND carrying a todo id AND whose store row still reads 'answered') and re-offers
    each to the same landed-check-then-reopen seam — idempotent by the seam's own checks, and
    covering every historical mark, including ones from before the pass existed."""

    def setUp(self):
        super().setUp()
        self._saved = (km._sessions, km._parse)
        self.turns = []
        km._sessions = lambda now, window=None, forks=True: [{"sid": SID, "path": "/dev/null"}]
        km._parse = lambda path, sid, now: {"turns": self.turns}

    def tearDown(self):
        km._sessions, km._parse = self._saved
        super().tearDown()

    def _reg(self, echoes, sid=SID):
        d = jd.STATE / "sdk"
        d.mkdir(parents=True, exist_ok=True)
        (d / (sid + ".json")).write_text(json.dumps({"sid": sid, "alive": True, "echoes": echoes}))

    def _stamped(self):
        tid = km._add_user_todo(SID, "Need the staging port")
        body = km._user_todo_answer_body("Need the staging port", "8443.")
        km._stamp_user_todo_answered(SID, tid, body)
        return tid, body

    def test_a_marked_then_died_loss_reopens_on_the_next_boot(self):
        # the two-boot shape: boot 1 marked the echo (persisted) and died before its reopen
        # thread ran; boot 2's pass must re-offer the loss or the ask is 'answered' forever
        tid, body = self._stamped()
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid}])
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 1)
        self.assertNotIn("resolved", km._user_todos()[SID][0],
                         "the mark survived the death; the boot pass re-offered it and the ask "
                         "visibly returned")

    def test_a_landed_answer_keeps_its_stamp_through_the_pass(self):
        # idempotence half 1: the seam's transcript check still guards the stamp, so the pass
        # can re-offer the same landed echo on every boot without flapping the ask open
        tid, body = self._stamped()
        self.turns = [{"atoms": [{"type": "user", "author": "human", "uuid": "u1",
                                  "message": {"role": "user",
                                              "content": [{"type": "text", "text": body}]}}]}]
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid}])
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 1)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered",
                         "landed = delivered; the stamp stands however many boots re-check it")

    def test_rows_not_reading_answered_are_not_offered(self):
        # idempotence half 2: an already-reopened row (open) and a dismissed row fail the
        # answered filter — the pass goes quiet once the reopen has landed
        tid, body = self._stamped()
        km._reopen_user_todo(SID, tid)                       # boot N-1's reopen already landed
        tid2 = km._add_user_todo(SID, "Need the auth-scheme decision")
        km._resolve_user_todo(SID, tid2, "dismissed")        # a dismiss has no delivery to fail
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": True, "todo": tid},
                   {"t": 2, "text": "Re: auth — cookie.", "author": "human", "dropped": True,
                    "todo": tid2}])
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0)
        self.assertNotIn("resolved", km._user_todos()[SID][0])
        self.assertEqual(km._user_todos()[SID][1]["resolved"]["kind"], "dismissed")

    def test_unmarked_or_idless_echoes_are_not_offered(self):
        # an echo still in flight (not drop-marked) belongs to the live path; a plain echo
        # (no id) has nothing to reopen
        tid, body = self._stamped()
        self._reg([{"t": 1, "text": body, "author": "human", "dropped": False, "todo": tid},
                   {"t": 2, "text": "an ordinary lost send", "author": "human", "dropped": True}])
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0)
        self.assertEqual(km._user_todos()[SID][0]["resolved"]["kind"], "answered")

    def test_a_missing_or_junk_reg_dir_is_a_quiet_zero(self):
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0, "no sdk/ dir at all")
        (jd.STATE / "sdk").mkdir(parents=True)
        (jd.STATE / "sdk" / "junk.json").write_text("not json{")
        self.assertEqual(km._user_todo_loss_boot_pass(wait=True), 0, "unreadable regs are skipped")

    def test_the_pass_is_wired_into_main_before_any_backend_construction(self):
        # the ordering IS the correctness: the pass must read the regs as the dead kernel left
        # them, before this boot's reseed re-persists new drop marks — that split (pre-existing
        # marks → the pass; new marks → the live path) is what keeps the two from double-firing
        src = inspect.getsource(km.main)
        i = src.index("_user_todo_loss_boot_pass")
        self.assertLess(i, src.index("_boot_warm()"),
                        "_boot_warm's _alive_sessions constructs the backend — the pass runs first")
        self.assertLess(i, src.index("target=_sdk"))


class MarkerNeutralizerVariants(unittest.TestCase):
    """Round-2 finding 4: every downstream matcher tolerates arbitrary whitespace after the
    comment opener (\"<!--\\s*romp-\"), so the neutralizer must break that same CLASS, not the one
    literal one-space spelling — a no-space \"<!--romp-injected-->\" in todo text sailed through
    and the user's own answer rendered as romp's system card. Verified against the VERBATIM
    downstream regexes, imported, never copied."""

    WS = ("", " ", "   ", "\n", "\t ", " \n ")

    def _cases(self):
        for ws in self.WS:
            yield "<!--%sromp-injected -->" % ws, em.ROMP_INJECT_RE, "romp-injected"
            yield "<!--%sromp-injected -->" % ws, km.jd.NUDGE_MARKER_RE, "romp-injected"
            yield "<!--%sromp-msg-id: m-3f2c -->" % ws, em.POSTAL_RE, "romp-msg-id"
            yield "<!--%sromp-tag: build-1 -->" % ws, em.MSG_TAG_RE, "romp-tag"

    def test_every_whitespace_variant_breaks_for_every_downstream_matcher(self):
        for raw, rex, words in self._cases():
            self.assertTrue(rex.search(raw),
                            "sanity: %r must be marker-shaped for /%s/" % (raw, rex.pattern))
            out = km._neutralize_romp_markers("note %s kept" % raw)
            self.assertFalse(rex.search(out),
                             "neutralized %r still matches /%s/" % (out, rex.pattern))
            self.assertIn(words, out, "the words survive — only the comment form breaks")

    def test_the_answer_body_gets_the_same_tolerance_on_both_halves(self):
        for raw, rex, _ in self._cases():
            body = km._user_todo_answer_body("Need a call on %s in the fixture" % raw,
                                             "Keep it, but drop the %s part." % raw)
            self.assertFalse(rex.search(body),
                             "an answer body carrying %r still matches /%s/" % (raw, rex.pattern))

    def test_the_edit_trace_path_gets_the_same_neutralization(self):
        # the edit trace embeds the request-supplied file PATH in an injected body — a marker-shaped
        # filename must not become a live marker downstream readers key on (same rule as the answer
        # body's two halves). The body's own designed tail IS a real marker, so only the prose half
        # before it is asserted marker-free.
        for raw, rex, _ in self._cases():
            body = km._edit_trace_body("/TESTDIR/notes-api/drafts/%s.md" % raw)
            head, sep, _tail = body.rpartition("<!-- romp-injected -->")
            self.assertTrue(sep, "the designed marker tail must still ride the body")
            self.assertFalse(rex.search(head),
                             "the path half carrying %r still matches /%s/" % (raw, rex.pattern))

    def test_the_escape_is_the_same_visible_one(self):
        self.assertEqual(km._neutralize_romp_markers("<!-- romp-injected -->"),
                         "<!- - romp-injected -->")
        self.assertEqual(km._neutralize_romp_markers("<!--romp-injected-->"),
                         "<!- -romp-injected-->")

    def test_the_bare_goal_id_form_breaks_in_both_todo_bodies(self):
        # The CANONICAL neutralizer (the one def these callers actually reach — see
        # tests/test_marker_neutralizer.py's single-def pin) also breaks the bare "romp-goal-id:"
        # form: it needs no comment opener, and per the follow-up contract it would REOPEN the
        # named goal — todo text and replies are agent/user-supplied, so a quoted id in either
        # half must not fire the judge's FOLLOWUP_RE or the kernel's twin.
        raw = "wrap up romp-goal-id: g-12 first"
        for rex in (km.jd.FOLLOWUP_RE, km._FOLLOWUP_GOAL_RE):
            self.assertTrue(rex.search(raw),
                            "sanity: %r must be marker-shaped for /%s/" % (raw, rex.pattern))
            body = km._user_todo_answer_body("Need a call on %s" % raw, "Do %s after." % raw)
            self.assertFalse(rex.search(body),
                             "an answer body carrying %r still matches /%s/" % (raw, rex.pattern))
            self.assertNotIn("romp-goal-id:", km._neutralize_romp_markers(raw))
        self.assertIn("romp-goal-id;", km._neutralize_romp_markers(raw),
                      "the visible escape: the colon becomes a semicolon")

    def test_a_non_romp_comment_is_untouched(self):
        self.assertEqual(km._neutralize_romp_markers("code sample: <!-- not ours -->"),
                         "code sample: <!-- not ours -->")


class ResolvedRowsAreBounded(_StoreSandbox):
    """Round-2 finding 5: a never-dying session's resolved rows accumulated without bound (the
    prune clears them only at session death — right for history, wrong as an invariant on a
    self-hosted box whose sessions live for weeks), and _user_todo_fp re-serializes every row on
    every chat build. A per-sid SIZE cap on RESOLVED rows only: the newest _USER_TODO_RESOLVED_KEEP
    stay, the oldest leave. OPEN rows are NEVER capped — the ADR's authority tier: an open ask
    leaves the store by answer/dismiss/withdraw alone, never by volume."""

    def test_resolved_rows_keep_only_the_newest_K(self):
        K = km._USER_TODO_RESOLVED_KEEP
        first = km._add_user_todo(SID, "the oldest resolved row")
        km._resolve_user_todo(SID, first, "dismissed")
        for i in range(K):
            t = km._add_user_todo(SID, "later todo %d" % i)
            km._resolve_user_todo(SID, t, "answered")
        resolved = [t for t in km._user_todos()[SID] if t.get("resolved")]
        self.assertEqual(len(resolved), K, "a size bound, not a time heuristic")
        self.assertNotIn(first, [t["id"] for t in resolved], "the OLDEST row is the one that left")

    def test_every_stamp_kind_is_capped_the_same_way(self):
        K = km._USER_TODO_RESOLVED_KEEP
        for i in range(K + 7):
            t = km._add_user_todo(SID, "todo %d" % i)
            km._resolve_user_todo(SID, t, ("answered", "dismissed", "withdrawn")[i % 3])
        self.assertEqual(len([t for t in km._user_todos()[SID] if t.get("resolved")]), K)

    def test_open_rows_are_never_capped(self):
        K = km._USER_TODO_RESOLVED_KEEP
        opens = [km._add_user_todo(SID, "open %d" % i) for i in range(K + 5)]
        for i in range(K + 5):
            t = km._add_user_todo(SID, "resolved %d" % i)
            km._resolve_user_todo(SID, t, "answered")
        got = km._user_todos()[SID]
        self.assertEqual([t["id"] for t in got if not t.get("resolved")], opens,
                         "every open ask survives — the cap reads resolved rows only")
        self.assertEqual(len([t for t in got if t.get("resolved")]), K)

    def test_the_fp_is_bounded_by_the_cap(self):
        K = km._USER_TODO_RESOLVED_KEEP
        for i in range(K * 2):
            t = km._add_user_todo(SID, "todo %d" % i)
            km._resolve_user_todo(SID, t, "answered")
        self.assertEqual(len(km._user_todos()[SID]), K,
                         "the per-sid fold hashes at most K resolved rows, forever")
        self.assertTrue(km._user_todo_fp(SID))


class NoJudgeWritesTheStore(unittest.TestCase):
    """The authority tier, grep-provable (docs/adr/0001): nothing in judge.py names the store or
    its helpers — every eraser in the three holes acts by inference, and this object exists to
    survive inference. The token list is DERIVED from the kernel source (every module-level def
    whose name says user_todo — writers and readers alike), so a helper added tomorrow is
    covered the day it is written; the literal floor below keeps the derivation honest against
    a pattern drift that would quietly match nothing."""

    # every store writer that exists today — the derivation must still see each of these,
    # or the regex broke and the pin is scanning an empty list
    _KNOWN_WRITERS = ("_add_user_todo", "_resolve_user_todo", "_reopen_user_todo",
                      "_stamp_user_todo_answered", "_user_todo_answer_lost",
                      "_user_todo_loss_boot_pass", "_write_user_todos")

    def test_judge_py_never_touches_user_todos(self):
        kdir = Path(HERE).parent / "kernel"
        src = (kdir / "judge.py").read_text()
        tokens = set(re.findall(r"^def (\w*user_todo\w*)\(",
                                (kdir / "kernel.py").read_text(), re.M))
        for w in self._KNOWN_WRITERS:
            self.assertIn(w, tokens, "the derivation no longer sees %s — fix the pattern, "
                                     "never the floor" % w)
        # the store file itself, plus the bare prefix that covers the reader/cache/lock names
        tokens |= {"user-todos.json", "_user_todos"}
        for token in sorted(tokens):
            self.assertNotIn(token, src)


# ────────────────────────────── slice 2: ambient visibility and the endgame ──────────────────────────


def _feed_env(test, sids):
    """Patch build_feed's session inputs to a synthetic alive set — the map/floor seams need no
    parse (ps None keeps every parse-derived path dark, exactly the cold-start shape)."""
    sessions = [{"sid": s, "name": n, "path": "/nonexistent/%s.jsonl" % s, "anchor": 0, "mtime": 0}
                for s, n in sids]
    ps = [
        mock.patch.object(km, "_alive_sessions", lambda now, tmux: list(sessions)),
        mock.patch.object(km, "_warm_fleet_bg", lambda now: None),
    ]
    for p in ps:
        p.start()
        test.addCleanup(p.stop)


class FeedSeamUserTodos(_StoreSandbox):
    """build_feed's return grows a top-level sid-keyed OPEN-COUNT map (plans/user-todos.md, data
    seams) — the feed-card marker's ride, the same way working[]/bgServices ride the payload. The
    ended gate is build_session's exact gate; a muted (hideFromFeed) session contributes nothing,
    like every other feed surface."""

    def test_the_map_carries_open_counts_per_sid(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._add_user_todo(SID, "Need a staging credential for the tests")
        tid = km._add_user_todo(SID2, "Need your pick of the two route layouts")
        km._resolve_user_todo(SID2, tid, "withdrawn")
        _feed_env(self, [(SID, "web"), (SID2, "api")])
        feed = km.build_feed(NOW, {})
        self.assertEqual(feed.get("userTodos"), {SID: 2}, "open rows only; a resolved-only sid is absent")

    def test_an_ended_sessions_todos_are_hidden_from_the_map(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        (jd.STATE / "gone").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "gone" / (SID + ".json")).write_text(json.dumps({"t": NOW, "by": "gone"}))
        _feed_env(self, [(SID, "web")])
        feed = km.build_feed(NOW, {})
        self.assertEqual(feed.get("userTodos"), {}, "hidden, not cleared — they return with a revive")
        self.assertTrue(km._open_user_todos(SID), "the store still holds the open ask")

    def test_a_muted_session_contributes_nothing(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        (jd.STATE / "session-flags.json").write_text(json.dumps({SID: {"hideFromFeed": True}}))
        km._flags_cache.clear()
        _feed_env(self, [(SID, "web")])
        feed = km.build_feed(NOW, {})
        self.assertEqual(feed.get("userTodos"), {}, "muted from the feed → no marker data either")

    def test_the_map_serializes_stably_across_builds(self):
        # the feed payload is dedup-compared serialized (_send_client) — same store, same bytes
        km._add_user_todo(SID2, "api: need the auth decision")
        km._add_user_todo(SID, "web: need the staging port")
        _feed_env(self, [(SID, "web"), (SID2, "api")])
        a = json.dumps(km.build_feed(NOW, {}).get("userTodos"))
        b = json.dumps(km.build_feed(NOW, {}).get("userTodos"))
        self.assertEqual(a, b)
        self.assertEqual(json.loads(a), {SID: 1, SID2: 1})

    def test_the_rows_carry_the_file_a_todo_names(self):
        # the todo-file follow-on (2026-09-07): the Waiting-on-you pane's file chip reads `file` off
        # the row (ui/webview/waiting.ts); a file-less todo's row is unchanged; store values only
        km._add_user_todo(FSID, "Need a look at the findings report", file="/srv/notes-api/docs/report.md")
        km._add_user_todo(FSID, "Need the staging port")
        _feed_env(self, [(FSID, "web")])
        feed = km.build_feed(NOW, {})
        rows = feed["userTodoRows"]
        self.assertEqual([r["sid"] for r in rows], [FSID])
        # two todos filed within one second sort by id (_open_user_todos: createdT, then id), so read
        # them by text, not by position
        by_text = {t["text"]: t for t in rows[0]["todos"]}
        self.assertEqual(set(by_text), {"Need a look at the findings report", "Need the staging port"})
        self.assertEqual(by_text["Need a look at the findings report"]["file"], "/srv/notes-api/docs/report.md")
        self.assertNotIn("file", by_text["Need the staging port"])
        self.assertEqual(json.dumps(rows), json.dumps(km.build_feed(NOW, {})["userTodoRows"]),
                         "byte-stable across builds when nothing changed")

    def test_the_view_sig_watches_the_store(self):
        # the marker/badge/floor all read this store from build_feed, so a todo write must bust
        # the FEED cache the way it already busts the owning session's chat cache — without this
        # the new row waited on an unrelated rebuild
        before = km._fleet_view_sig(NOW, {})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        after = km._fleet_view_sig(NOW, {})
        self.assertNotEqual(before, after)


class EscalationFloorPredicate(_StoreSandbox):
    """The idle-escalation floor's ARMING read (_user_todo_idle): true only when the session has
    SETTLED idle — no open turn, nothing dispatched, no queued intent, no live prompt — the exact
    idle the auto-nudge tick requires. Event-keyed both ways, and NEVER armed by a transient
    turn-boundary lull (the cards-move-on-new-information rule; WHY_UNBLOCK_UNSETTLED is the
    repo's own card-flap history)."""

    PS = {"turns": [{"id": "t1", "t": NOW - 60, "end": NOW - 30, "atoms": []}]}

    def _idle(self, sid=SID, ps=None, who_working=False, awaiting=None, perm_state=None, aerr=None,
              last_state=("waiting", NOW - 20), queued=False, rewind=False, compacting=False,
              interrupted=False, pending_ops=None, peer_wait=None):
        patches = [
            mock.patch.object(km, "_last_state", lambda s: last_state),
            mock.patch.object(km, "_backend_queued", lambda s: queued),
            mock.patch.object(km, "_backend_rewind_pending", lambda s: rewind),
            mock.patch.object(km, "_compacting_now", lambda s, **k: compacting),
            mock.patch.object(km, "_interrupt_suppresses_nudge", lambda turns, s="", **k: interrupted),
            mock.patch.dict(km._pending_ops, pending_ops or {}, clear=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        return km._user_todo_idle(sid, self.PS if ps is None else ps, who_working, awaiting,
                                  perm_state, aerr, peer_wait)

    def test_a_settled_idle_session_arms_the_floor(self):
        self.assertTrue(self._idle())

    def test_an_open_turn_never_arms_it(self):
        self.assertFalse(self._idle(who_working=True))

    def test_dispatched_background_work_never_arms_it(self):
        self.assertFalse(self._idle(awaiting="waiting on 2 agents"))

    def test_a_live_prompt_or_compaction_never_arms_it(self):
        self.assertFalse(self._idle(perm_state="permission"))
        self.assertFalse(self._idle(perm_state="picker"))
        self.assertFalse(self._idle(perm_state="compacting"))
        self.assertFalse(self._idle(compacting=True))

    def test_an_api_error_story_wins(self):
        self.assertFalse(self._idle(aerr={"status": 529, "text": "overloaded"}))

    def test_queued_intent_means_the_session_is_about_to_wake(self):
        # a message arrived — the de-escalation event; the floor must not claim idle over it
        self.assertFalse(self._idle(queued=True))
        self.assertFalse(self._idle(pending_ops={SID: [("send", "hi")]}))
        self.assertFalse(self._idle(rewind=True))

    def test_a_user_interrupt_means_the_user_acted(self):
        self.assertFalse(self._idle(interrupted=True))

    def test_waiting_on_a_live_peer_never_floors(self):
        # the notes-api shape (review 2026-08-22): api sent web a question and web is alive —
        # api's idle with an open todo is explained by the PEER it awaits (_wait_for_graph's
        # edge, the same event the waitingOn chip and the nudge tick's skip read), and waiting
        # on a peer is deliberately NOT needs-you (interrupt only when the human is the
        # bottleneck). The floor must not fire while a live peer owes this session a reply.
        edge = {"peerSid": SID2, "name": "web", "color": None, "inCycle": False,
                "since": NOW - 900, "kind": "question"}
        self.assertFalse(self._idle(peer_wait=edge))

    def test_the_peer_wait_lifts_with_the_edge(self):
        # the peer's reply (any message back) drops the edge — a real postal event, and the
        # floor may then claim the idle it explains
        self.assertTrue(self._idle(peer_wait=None))

    def test_no_parse_or_no_turns_reads_unknown_never_idle(self):
        self.assertFalse(self._idle(ps={}))
        self.assertFalse(self._idle(ps={"turns": []}))
        self.assertFalse(km._user_todo_idle(SID, None, False, None, None, None))

    def test_no_flap_a_mid_turn_lull_never_arms_the_floor(self):
        # THE PIN (the card-flap history): the event model reads "no open turn" during transient
        # mid-turn lulls, so keying the floor on that alone would strobe the card at every turn
        # boundary. The authoritative state log saying PROGRESSING at/after the parsed turn end
        # means the stop is not real — the same genuine-stop discriminator the auto-nudge uses,
        # two real-event timestamps, no time window.
        self.assertFalse(self._idle(last_state=("working", NOW - 10)),
                         "state log progressing AFTER the turn end → a lull, not a stop")
        self.assertFalse(self._idle(last_state=("working", NOW - 30)),
                         "progressing AT the turn end → still the open turn")

    def test_a_stale_progressing_record_from_before_the_turn_end_does_not_wedge(self):
        # the post-turn 'waiting' write can be LOST (kernel restart) — a progressing record OLDER
        # than the turn end must not pin the floor off forever (the bugsdk2 nudge lesson)
        self.assertTrue(self._idle(last_state=("working", NOW - 40)))

    def test_the_deciding_events_re_derive_it_cleanly(self):
        # escalate at the settle; stand down the build after a new turn opens — each a real event
        self.assertTrue(self._idle())
        self.assertFalse(self._idle(who_working=True), "a new turn opening stands the floor down")


class EscalationFloorWiring(_StoreSandbox):
    """The floor lives in the per-session derivation's perm_top family (_feed_session_entry, the body
    T368's card memo derives per session and build_feed folds; the ended gate is the KEY's,
    _feed_session_key) (source pins, the same convention as test_kernel_distill_state: a full feed
    build's inputs are heavy). A verdict-shaped write is exactly what the ADR forbids; the floor
    re-derives from the store read each derivation."""

    def test_the_floor_yields_to_every_live_interrupt(self):
        src = inspect.getsource(km._feed_session_entry)
        self.assertIn("_user_todo_idle(", src)
        self.assertIn("if _todo_idle and api_top is None and perm_top is None and jauth_top is None:",
                      src, "one interrupt at a time — the present event first")

    def test_the_floor_files_the_focus_card_under_needs_input(self):
        src = inspect.getsource(km._feed_session_entry)
        self.assertIn('_todo_block = bool(nid == todo_top and col == "working")', src,
                      "floors a plain-working focus card only — never displaces awaiting/blocked/"
                      "recheck moves, which are their own designed latches")
        self.assertIn("or _todo_block", src.split("column = (")[1].split(")\n")[0],
                      "the column expression carries the floor")

    def test_the_escalated_card_carries_the_story(self):
        src = inspect.getsource(km._feed_session_entry)
        self.assertIn('{"state": "userTodos"', src)
        self.assertIn("if _todo_block", src)

    def test_the_ended_gate_is_build_sessions_exact_gate(self):
        src = inspect.getsource(km._feed_session_key)   # the ended read is a KEY component (todos, by value)
        self.assertIn("_user_todo_session_ended(fsid)", src)

    def test_a_goal_less_session_gets_the_needs_input_placeholder(self):
        src = inspect.getsource(km._feed_session_entry)
        self.assertIn("elif _todo_idle and _ut_open and todo_top is None and not had_needs_input:",
                      src, "…and only when NOTHING else floored/blocked the session — one "
                           "interrupt story at a time (review 2026-08-22; OneInterruptStory "
                           "carries the behavioral repro)")
        self.assertIn("_user_todo_placeholder(", src)

    def test_the_floor_reads_the_peer_wait_edge(self):
        # review 2026-08-22: the predicate's peer-wait input comes from the SAME wait-for graph
        # the nudge tick and the waitingOn chip consult — never a second derivation
        src = inspect.getsource(km._feed_session_entry)
        self.assertIn("aerr, wmap.get(fsid),", src)   # the edge, then the badge read (P2 S2)

    def test_the_provisional_chain_treats_a_floored_card_as_working(self):
        # review 2026-08-22: a todo-floored focus card reports needs_input, so without this the
        # judge-latency window painted a provisional Working "Analyzing:" placeholder BESIDE the
        # floored card — the exact duplicate the perm floor's guard already prevents; mirror it
        src = inspect.getsource(km._feed_session_entry)
        self.assertIn("if not had_working and perm_top is None and todo_top is None and ps:", src)

    def test_the_placeholder_is_a_presentation_not_a_countable_card(self):
        # provisional, like the goal-less permission placeholder — the badge counts the TODOS
        # (the map), never this presentation of them (the no-double-count rule)
        ph = km._user_todo_placeholder(
            {"sid": SID, "path": "/nonexistent"}, "web", None, SID, True, NOW,
            [{"id": "ut-11111111", "text": "Need the auth-scheme decision", "createdT": NOW - 300},
             {"id": "ut-22222222", "text": "Need a staging credential", "createdT": NOW - 100}])
        self.assertTrue(ph["provisional"])
        self.assertEqual(ph["column"], "needs_input")
        self.assertEqual(ph["blocked"]["state"], "userTodos")
        self.assertEqual(ph["blocked"]["count"], 2)
        self.assertEqual(ph["itemId"], "usertodo:" + SID)
        self.assertIn("Need the auth-scheme decision", ph["text"], "the oldest open ask titles it")
        self.assertIn("+1 more", ph["text"])
        self.assertEqual(ph["t"], NOW - 100, "the newest ask is the card's current-state time")

    def test_the_floor_is_not_a_judge_verdict(self):
        # read-side only: neither the derivation nor build_feed writes the goal store or the diary for this move
        src = inspect.getsource(km._feed_session_entry) + inspect.getsource(km.build_feed)
        self.assertNotIn("save_goals", src)


class PeerWaitScopeIsLocalOnly(_StoreSandbox):
    """The peer-wait stand-down is LOCAL-HOST only — a DOCUMENTED limitation, pinned (round-2
    verification, 2026-08-22): _wait_for_graph keeps an edge only when the awaited peer is in
    THIS kernel's alive set, so an unanswered ask to a FEDERATED peer (a relay-addressed row)
    makes no edge and the idle floor still fires needs-you over an idle a remote peer actually
    explains. The scope is shared with the waitingOn chip and the nudge tick's skip — all three
    read the same graph, deliberately: cross-host wait tracking belongs in _wait_for_graph,
    where widening it lifts every surface at once; a floor-only special case would fork the
    wait derivation (plans/user-todos.md, escalation). If these tests start failing because the
    graph learned federated edges, flip the floor's expectation CONSCIOUSLY alongside the
    chip's."""

    def setUp(self):
        super().setUp()
        self.mfile = Path(self.td.name) / "timeline" / "messages.jsonl"
        self._saved_messages = jd.MESSAGES
        jd.MESSAGES = self.mfile
        self._saved_cache = list(km._POSTAL_WAIT_CACHE)
        km._POSTAL_WAIT_CACHE[:] = [None, None]

    def tearDown(self):
        jd.MESSAGES = self._saved_messages
        km._POSTAL_WAIT_CACHE[:] = self._saved_cache
        super().tearDown()

    def _write_rows(self, rows):
        self.mfile.parent.mkdir(parents=True, exist_ok=True)
        self.mfile.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        km._POSTAL_WAIT_CACHE[:] = [None, None]

    def test_a_local_alive_peer_makes_the_edge(self):
        # the control (keeps the negatives below non-vacuous): the same unanswered question to
        # a LOCAL alive peer builds the edge the floor stands down on
        self._write_rows([{"from_id": SID, "to_id": SID2, "t": NOW - 300,
                           "kind": "question", "body": "Which port does staging use?"}])
        wmap = km._wait_for_graph(NOW, {SID, SID2})
        self.assertIn(SID, wmap)
        self.assertEqual(wmap[SID]["peerSid"], SID2)

    def test_a_relay_addressed_ask_makes_no_edge_so_the_floor_still_fires(self):
        # the federated shape: the row is addressed to the relay and the remote never spoke, so
        # the alias cannot resolve and the pair keys on the named recipient — never in the local
        # alive set, so the graph drops the edge and the floor's peer_wait input (wmap.get(sid))
        # is None: a session idle on a cross-host reply still floors as needs-you. KNOWN
        # limitation, kept consciously — see the class docstring.
        self._write_rows([{"from_id": SID, "to_id": "peer:TESTHOST", "toName": "TESTHOST:api",
                           "t": NOW - 300, "kind": "question",
                           "body": "Which port does staging use?"}])
        wmap = km._wait_for_graph(NOW, {SID})
        self.assertNotIn(SID, wmap, "no edge to a federated peer — wmap is local-host scope")

    def test_even_a_resolved_remote_sid_makes_no_edge(self):
        # the stronger claim: the alias CAN resolve the remote's real sid (it sent a row once),
        # and the edge is still dropped — the gate is the local alive set, not addressability
        self._write_rows([
            {"from_id": SID2, "from": "api", "from_host": "TESTHOST", "to_id": SID,
             "t": NOW - 900, "kind": "coordinate", "body": "Staging is rebuilt nightly."},
            {"from_id": SID, "to_id": "peer:TESTHOST", "toName": "TESTHOST:api",
             "t": NOW - 300, "kind": "question", "body": "Which port does staging use?"},
        ])
        wmap = km._wait_for_graph(NOW, {SID})
        self.assertNotIn(SID, wmap, "a resolvable but non-local peer still makes no edge")


class OneInterruptStory(_StoreSandbox):
    """Review 2026-08-22, the guard-conflict roots: a session shows ONE interrupt presentation
    at a time. (a) The goal-less userTodos placeholder fired BESIDE a jauth-floored focus card
    (todo_top None conflated 'no live goal' with 'yielded to jauth_top'); (b) the provisional
    Working chain painted an 'Analyzing:' placeholder beside a todo-floored card during judge
    latency; and the focus-chain miss: a completed lastNode top with another top still working
    escalated NOTHING (the walk dead-ended, had_working suppressed the placeholder). Behavioral,
    over a real build_feed with the repro's own harness — SYNTHETIC data only."""

    TURNS = [{"id": "t1", "t": NOW - 60, "end": NOW - 30, "ended": True, "atoms": []}]

    def _env(self, store, jauth=False, extra=None):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        sessions = [{"sid": SID, "name": "web", "path": "/nonexistent/%s.jsonl" % SID,
                     "anchor": 0, "mtime": 0}]
        turns = list(self.TURNS)
        patches = [
            mock.patch.object(jd, "_auth_down_map",
                              lambda: ({SID: {"mode": "key", "since": NOW - 100}} if jauth else {})),
            mock.patch.object(km, "_alive_sessions", lambda now, tmux: list(sessions)),
            mock.patch.object(km, "_warm_fleet_bg", lambda now: None),
            mock.patch.object(km, "_parse_cached", lambda path: {"turns": list(turns)}),
            mock.patch.object(km, "_merge_live_atoms", lambda ps, sid: ps),
            # build_feed reads the store with its version key (_feed_goals_keyed, upstream #1789); a synthetic
            # store is a live read keyed None (no snapshot version), so the memo bypasses it
            mock.patch.object(km, "_feed_goals_keyed", lambda sid: (dict(store), None)),
            # the predicate is pinned separately (EscalationFloorPredicate); force-arm it here
            # so these shapes exercise the GUARDS, not the arming gates — arity-proof on purpose
            mock.patch.object(km, "_user_todo_idle", lambda *a, **k: True),
        ] + (extra or [])
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def _needs_input(self, feed):
        return [a for a in feed["asks"]
                if str(a.get("sid")) == SID and a.get("column") == "needs_input"]

    def test_the_jauth_floor_stands_alone(self):
        # the reviewer repro: jauth latched + open todos + a live goal → the jauth story is the
        # one interrupt; the goal-less todo placeholder must not fire beside it
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "working"}, "lastNode": "g1", "placements": {}}, jauth=True)
        ni = self._needs_input(km.build_feed(NOW, {}))
        self.assertEqual(len(ni), 1,
                         "ONE needs-input presentation, got %d (%s)"
                         % (len(ni), sorted(str((a.get("blocked") or {}).get("state")) for a in ni)))
        self.assertNotIn("usertodo:" + SID, [a["itemId"] for a in ni],
                         "the placeholder yielded — jauth won")

    def test_a_todo_floored_card_gets_no_working_placeholder(self):
        # (b): during judge latency _provisional_card can return a Working 'Analyzing:' card;
        # a todo-floored focus card already tells the session's one story, so the provisional
        # chain must treat it as had-working-equivalent (the perm floor's own handling)
        dummy = {"itemId": "provisional:" + SID, "sid": SID, "name": "web", "color": None,
                 "text": "Analyzing: wire the login flow", "t": NOW, "live": True,
                 "trgb": [0, 0, 0], "turnId": None, "origin": None, "followupPending": None,
                 "summary": None, "blockSummary": None, "background": None,
                 "blocked": None, "column": "working", "provisional": True, "tree": []}
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "working"}, "lastNode": "g1", "placements": {}},
                  extra=[mock.patch.object(km, "_provisional_card", lambda *a, **k: dict(dummy))])
        feed = km.build_feed(NOW, {})
        ni = self._needs_input(feed)
        self.assertEqual([str((a.get("blocked") or {}).get("state")) for a in ni], ["userTodos"],
                         "the floored focus card carries the story")
        self.assertNotIn("provisional:" + SID, [a["itemId"] for a in feed["asks"]],
                         "no Working placeholder beside the floored card")

    def test_a_completed_focus_falls_back_to_the_working_top(self):
        # the focus-chain miss: lastNode's top completed, another top still working → the todo
        # IS the frontier of this IDLE session regardless of which top holds focus
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 900, "text": "ship the fixtures"},
                             "g2": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "completed", "g2": "working"}, "lastNode": "g1",
                   "placements": {}})
        feed = km.build_feed(NOW, {})
        ni = self._needs_input(feed)
        self.assertEqual([a["itemId"] for a in ni], ["g2"],
                         "the still-working top takes the floor when the focus walk dead-ends")
        self.assertEqual((ni[0].get("blocked") or {}).get("state"), "userTodos")
        self.assertNotIn("usertodo:" + SID, [a["itemId"] for a in feed["asks"]],
                         "a floored card means no placeholder")

    def test_the_fallback_still_yields_to_jauth(self):
        # keep every yield rule: with the jauth floor latched on a live focus goal, the
        # fallback never floors a second card for the same session
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 900, "text": "ship the fixtures"},
                             "g2": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "working", "g2": "working"}, "lastNode": "g1",
                   "placements": {}}, jauth=True)
        ni = self._needs_input(km.build_feed(NOW, {}))
        self.assertEqual(len(ni), 1, "one interrupt story — jauth floors the focus, todos wait")
        self.assertNotEqual((ni[0].get("blocked") or {}).get("state"), "userTodos")

    def test_a_done_confirming_focus_is_never_floored(self):
        # round-2 verification: a top in the rollup's `confirming` export (done verdict filed,
        # settle pending) still reads col 'working' — flooring it fights the settle gate and
        # flaps working→needs-you→completed with no new information. The focus walk skips it;
        # the fallback floors the genuinely working top instead.
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 900, "text": "ship the fixtures"},
                             "g2": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "working", "g2": "working"}, "lastNode": "g1",
                   "confirming": ["g1"], "placements": {}})
        feed = km.build_feed(NOW, {})
        ni = self._needs_input(feed)
        self.assertEqual([a["itemId"] for a in ni], ["g2"],
                         "the confirming focus belongs to the settle gate, not the floor")
        g1 = next(a for a in feed["asks"] if a["itemId"] == "g1")
        self.assertTrue(g1.get("doneConfirming"), "the skipped focus keeps its steady cue")

    def test_the_fallback_skips_a_confirming_top_too(self):
        # …and the working-top fallback honors the same set: with the one candidate confirming,
        # nothing floors this build — its completion is moments away (the settle), and a floor
        # now would be un-floored by the very next verdict
        self._env({"nodes": {"g1": {"parentId": None, "t": NOW - 900, "text": "ship the fixtures"},
                             "g2": {"parentId": None, "t": NOW - 500, "text": "wire the login flow"}},
                   "status": {"g1": "completed", "g2": "working"}, "lastNode": "g1",
                   "confirming": ["g2"], "placements": {}})
        feed = km.build_feed(NOW, {})
        self.assertEqual(self._needs_input(feed), [],
                         "no floor while the only candidate is done-confirming")
        g2 = next(a for a in feed["asks"] if a["itemId"] == "g2")
        self.assertEqual(g2["column"], "working")
        self.assertTrue(g2.get("doneConfirming"))


class FloorNotificationDedup(_StoreSandbox):
    """Review 2026-08-22: the floor stands down for every turn the session takes and re-arms at
    the settle — the DESIGNED card move — but _feed_notifications read each re-entry as news,
    an OS push per exchange and per monitor wake-cycle for the SAME deferred todo. The interrupt
    is deduplicated at the notification layer, event-keyed on the FLOORED TODO SET: it fires on
    first arm or when a todo id joins the set; an identical set re-entering is not news. The
    latch is _NOTIFY_PREV's own in-memory idiom, kept beside it, so it survives the card's
    Working dips. The CARD move stays exactly as built — only the push is deduplicated."""

    def setUp(self):
        super().setUp()
        km._NOTIFY_PREV[0] = None
        km._NOTIFY_PREV_DISK[0] = None                       # the persisted snapshot's load latch: this world's own file
        getattr(km, "_NOTIFY_UT_FIRED", [{}])[0].clear()
        patches = [
            mock.patch.object(km, "_notify_card_effective", lambda cards, iid, sid: True),
            mock.patch.object(km, "_prune_notify_cards", lambda live: None),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        km._NOTIFY_PREV[0] = None
        km._NOTIFY_PREV_DISK[0] = None
        getattr(km, "_NOTIFY_UT_FIRED", [{}])[0].clear()
        super().tearDown()

    def _card(self, floored, state="userTodos"):
        blocked = ({"state": state, "count": len(km._open_user_todos(SID)),
                    "what": "waiting on you"} if floored else None)
        return {"asks": [{"itemId": SID + ":g1", "sid": SID, "name": "web",
                          "text": "wire the login flow",
                          "column": "needs_input" if floored else "working",
                          "blocked": blocked}]}

    def test_a_dip_and_re_entry_with_the_same_todo_set_is_not_news(self):
        # the monitor-cycle shape: settle→floor (push), check-in turn→working, settle→floor,
        # …repeated. Exactly ONE notification for the one deferred todo.
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))          # baseline build
        fired = len(km._feed_notifications(self._card(floored=True)))   # first arm → the one push
        self.assertEqual(fired, 1)
        for _cycle in range(3):                                    # three monitor wake-cycles
            self.assertEqual(km._feed_notifications(self._card(floored=False)), [])
            fired += len(km._feed_notifications(self._card(floored=True)))
        self.assertEqual(fired, 1, "re-entry with an identical todo set is not news")

    def test_a_new_todo_re_arms_the_push(self):
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1)
        km._feed_notifications(self._card(floored=False))          # the session took a turn
        km._add_user_todo(SID, "Need a staging credential for the tests")
        out = km._feed_notifications(self._card(floored=True))
        self.assertEqual(len(out), 1, "a todo id joining the floored set IS news")

    def test_the_dedup_is_scoped_to_the_floor(self):
        # a non-todo card follows the notification snapshot's own rule, not the floor's set diff: a permission
        # stop is announced once per (card, column) unless the user acted on the card since, or the other
        # column was announced since (the persisted snapshot; test_notify_bells.py's re-blocking pin is the
        # master for the answer-then-re-block case, which journals the user's act). A dip to working with
        # nothing from the user in between is not news for it, where the floored card above re-arms on a
        # new todo id alone.
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(True, state="permission"))), 1)
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(True, state="permission"))), 0,
                         "the same card under the same column, no user act since: announced once")

    def test_a_restart_baseline_seeds_the_latch_from_the_floored_world(self):
        # round-2 verification (repro test_A): the latch is in-memory and the baseline build
        # returned BEFORE seeding it, so the first dip+re-entry after every kernel restart
        # re-pushed the SAME already-notified todo — one spurious interrupt per floored session
        # per deploy on a self-hosting box. The floored set IS the already-notified state (the
        # card either fired before the restart or was status the baseline declined to push), so
        # the baseline seeds the latch from exactly the cards already floored — event-derived,
        # no persistence file.
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1)
        # KERNEL RESTART: both in-memory latches re-baseline together
        km._NOTIFY_PREV[0] = None
        km._NOTIFY_UT_FIRED[0].clear()
        self.assertEqual(km._feed_notifications(self._card(floored=True)), [],
                         "the boot baseline stays silent — existing state is status, not news")
        self.assertEqual(km._feed_notifications(self._card(floored=False)), [])
        self.assertEqual(km._feed_notifications(self._card(floored=True)), [],
                         "the routine dip+re-entry after a restart is NOT news — the baseline "
                         "seeded the latch from the already-floored card")

    def test_the_baseline_seed_suppresses_only_what_was_already_floored(self):
        # the seed must not oversuppress: a todo the baseline never saw is still news
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        self.assertEqual(km._feed_notifications(self._card(floored=True)), [],
                         "floored at boot — the baseline is silent and seeds the latch")
        km._add_user_todo(SID, "Need a staging credential for the tests")
        self.assertEqual(km._feed_notifications(self._card(floored=False)), [])
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1,
                         "the id that joined AFTER the baseline is news")

    def test_a_new_id_joining_while_floored_pushes_with_no_observed_dip(self):
        # round-2 verification (repro test_C): a second todo registers in a turn too quick for
        # any build to observe the dip — the card is floored in BOTH adjacent builds, so hanging
        # the latch off the column diff short-circuited it and the join never pushed. The
        # todo-set diff is the news test, independent of the column transition.
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1)
        km._add_user_todo(SID, "Need a staging credential for the tests")
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1,
                         "a joining id is news even when no build observed a dip")
        self.assertEqual(km._feed_notifications(self._card(floored=True)), [],
                         "…and exactly once: the steadily floored card stays quiet after it")

    def test_a_lost_answer_reopen_re_arms_the_push(self):
        # round-2 verification (repro test_B): the loss seam reopens the SAME id, so the set
        # dedup ate the re-floor's push forever — but that push is the ONE signal telling the
        # user their answer never arrived (the loss seam's never-quiet doctrine). The loss
        # EVENT clears the id from the latch, so the next floor treats it as news.
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1)
        # the user answers → stamp lands, the card unfloors
        self.assertTrue(km._resolve_user_todo(SID, tid, "answered"))
        self.assertEqual(km._feed_notifications(self._card(floored=False)), [])
        # the answer's holder dies; the loss seam reopens the same id (no transcript → reopen)
        with mock.patch.object(km, "_sessions",
                               lambda now, window=None, forks=True: [{"sid": SID,
                                                                      "path": "/dev/null"}]), \
             mock.patch.object(km, "_parse", lambda path, sid, now: {"turns": []}), \
             contextlib.redirect_stderr(io.StringIO()):
            km._user_todo_answer_lost(SID, tid, "Re: Need the auth-scheme decision — cookie.",
                                      wait=True)
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the loss reopened the ask")
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1,
                         "the re-floor after a LOST answer pushes — never quiet")

    def test_the_users_own_recall_stays_silent(self):
        # the ✕ recall (_cancel_backend_queued) reopens the same id too — but the user pulled
        # the answer back THEMSELVES; an interrupt telling them what they just did is noise.
        # The unlatch keys on the LOSS event alone, so the recall's re-floor stays deduplicated.
        be = _FakeBackend()
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._feed_notifications(self._card(floored=False))
        self.assertEqual(len(km._feed_notifications(self._card(floored=True))), 1)
        body = km._user_todo_answer_body("Need the auth-scheme decision to wire login",
                                         "Go with the session cookie.")
        self.assertTrue(km._send_with_id(be, SID, body, user_todo=tid))
        km._stamp_user_todo_answered(SID, tid, body)
        self.assertEqual(km._feed_notifications(self._card(floored=False)), [])
        self.assertIsNone(km._cancel_backend_queued(be, SID, 0, km._split_followup(body)[1]))
        self.assertNotIn("resolved", km._user_todos()[SID][0], "the recall reopened the ask")
        self.assertEqual(km._feed_notifications(self._card(floored=True)), [],
                         "the user's own ✕ needs no interrupt saying what they just did")

    def test_the_latch_writers_share_one_lock(self):
        # the loss seam's unlatch runs THREADED beside the build's read-modify-write; every
        # writer holds _NOTIFY_UT_LOCK, or a stale fire could overwrite a concurrent unlatch
        # (a lost update that re-arms or re-silences the wrong sid)
        for fn in (km._feed_notifications_diff, km._notify_ut_unlatch):   # the diff holds the build's read-modify-write
            self.assertIn("with _NOTIFY_UT_LOCK", inspect.getsource(fn),
                          "%s must hold the latch lock around its read-modify-write" % fn.__name__)


class BadgeArithmetic(unittest.TestCase):
    """_needs_you_count widens to 'things only the user can move' (plans/user-todos.md, (d)):
    open user todos of non-ended sessions PLUS hard-stopped needs-input sessions — counted per
    SESSION ('counts once as itself'), with the escalation floor adding nothing (a presentation
    of todos the count already includes). Ended sessions are excluded upstream: the map is built
    behind the ended gate (FeedSeamUserTodos)."""

    def test_todos_plus_hard_stopped_sessions(self):
        feed = {"asks": [{"itemId": "a", "sid": "S1", "column": "needs_input"}],
                "userTodos": {"S2": 2}}
        self.assertEqual(km._needs_you_count(feed), 3)

    def test_the_escalation_floor_adds_nothing_extra(self):
        # an idle session escalated BY its todos: the card is a presentation of the two todos
        # already in the count — never a third thing
        feed = {"asks": [{"itemId": "a", "sid": "S2", "column": "needs_input",
                          "blocked": {"state": "userTodos", "count": 2}}],
                "userTodos": {"S2": 2}}
        self.assertEqual(km._needs_you_count(feed), 2)

    def test_a_hard_stopped_session_with_todos_counts_once_as_itself(self):
        # the spec's dedup rule: the permission stop is its own thing (1) beside the session's
        # own todo (1) — the session's hard stop never counts twice
        feed = {"asks": [{"itemId": "a", "sid": "S1", "column": "needs_input",
                          "blocked": {"state": "permission", "what": "stopped"}}],
                "userTodos": {"S1": 1}}
        self.assertEqual(km._needs_you_count(feed), 2)

    def test_hard_stops_count_per_session_not_per_card(self):
        feed = {"asks": [{"itemId": "a", "sid": "S1", "column": "needs_input"},
                         {"itemId": "b", "sid": "S1", "column": "needs_input"}]}
        self.assertEqual(km._needs_you_count(feed), 1)

    def test_provisional_and_non_blocked_cards_stay_out(self):
        feed = {"asks": [
            {"itemId": "a", "sid": "S1", "column": "needs_input", "provisional": True},
            {"itemId": "b", "sid": "S2", "column": "working"},
            {"itemId": "c", "sid": "S3", "column": "completed"},
        ]}
        self.assertEqual(km._needs_you_count(feed), 0)

    def test_a_sid_less_card_still_counts(self):
        # nothing to dedup it against — dropping it would hide a real needs-you
        feed = {"asks": [{"itemId": "q1", "column": "needs_input"},
                         {"itemId": "q2", "column": "needs_input"}]}
        self.assertEqual(km._needs_you_count(feed), 2)

    def test_held_mail_counts_per_message_beside_a_session_stop(self):
        # review 2026-08-22: quarantine cards are independent user DECISIONS (approve/deny/edit
        # per message), not a state of their session — the per-session dedup absorbed them, so a
        # permission stop + 2 held mails for the same session read badge 1. Three decisions = 3.
        feed = {"asks": [
            {"itemId": "S1:g1", "sid": "S1", "column": "needs_input",
             "blocked": {"state": "permission", "what": "stopped"}},
            {"itemId": "quarantine:m-01", "sid": "S1", "column": "needs_input",
             "blocked": {"state": "quarantine", "mid": "m-01"}},
            {"itemId": "quarantine:m-02", "sid": "S1", "column": "needs_input",
             "blocked": {"state": "quarantine", "mid": "m-02"}},
        ]}
        self.assertEqual(km._needs_you_count(feed), 3)

    def test_parked_handoffs_count_per_send(self):
        # two handoffs parked for the same offline recipient are two deliver-or-dismiss calls
        feed = {"asks": [
            {"itemId": "parked:m-01", "sid": "S9", "column": "needs_input",
             "blocked": {"state": "parkedHandoff", "toSid": "S9"}},
            {"itemId": "parked:m-02", "sid": "S9", "column": "needs_input",
             "blocked": {"state": "parkedHandoff", "toSid": "S9"}},
        ]}
        self.assertEqual(km._needs_you_count(feed), 2)

    def test_the_per_item_classes_are_the_feeds_own(self):
        # the class list is enumerated from build_feed's needs-input constructors — goal cards
        # and the provisional placeholders are session-state; these two are the per-item ones.
        # A constructor whose state leaves this list dedups by sid, so drift shows up here.
        self.assertEqual(set(km._NEEDS_YOU_PER_ITEM), {"quarantine", "parkedHandoff"})
        src = inspect.getsource(km.build_feed) + inspect.getsource(km._quarantine_cards)
        for st in km._NEEDS_YOU_PER_ITEM:
            self.assertIn('"state": "%s"' % st, src, "the class must name a real constructor")

    def test_an_empty_feed_is_zero(self):
        self.assertEqual(km._needs_you_count({"asks": []}), 0)
        self.assertEqual(km._needs_you_count({}), 0)


class NudgeStandsDownForOpenTodos(_StoreSandbox):
    """The auto-nudge's open-todo gate is scoped to the STATUS NUDGE alone (plans/user-todos.md,
    escalation; review 2026-08-22): the todo says exactly what a status check would fish for, so
    none fires while one stands — but two unrelated ladders share this walk and must flow past
    it. The awaiting WAKE is the 6h LOST-WAKEUP backstop (suppressing it re-creates the
    2026-08-11 wedge: dispatched background work whose completion wakeup died, asleep in Awaiting
    for days), and the DEBT machinery is the ONE mechanism that unparks a PEER silently waiting
    on this session's answer — a todo names what THIS session needs from the user and says
    nothing about what a peer needs from it. The first cut returned at session level and
    silenced all three. SYNTHETIC fixtures (the notes-api world)."""

    S = {"sid": SID, "name": "web", "path": "/nonexistent/%s.jsonl" % SID, "anchor": 0, "mtime": 0}
    TURNS = [{"id": "t1", "trigger": None, "t": NOW - 600, "end": NOW - 500, "ended": True, "atoms": []}]   # upstream's gate reads `trigger` (em.segments)

    def setUp(self):
        super().setUp()
        self.saved_goaldir = jd.GOALDIR
        jd.GOALDIR = jd.STATE / "goals"
        jd.GOALDIR.mkdir(parents=True, exist_ok=True)
        km._autonudge_cache.clear()
        km._SESSION_STAMP_CACHE.clear()
        km._flags_cache.clear()
        self.sent = []
        rec = self

        class _Backend:
            def send(self, sid, body):
                rec.sent.append((sid, body))
                return True

        self.saved_backend = km.Sessions.backend_for
        km.Sessions.backend_for = staticmethod(lambda sid: _Backend())
        patches = [
            mock.patch.object(km, "_api_error", lambda path: None),
            mock.patch.object(jd, "parsed_session",
                              lambda sid, paths, now: {"turns": list(self.TURNS)}),
            mock.patch.object(km, "_session_working", lambda turns: False),
            mock.patch.object(km, "_interrupt_suppresses_nudge", lambda turns, s="", **k: False),
            mock.patch.object(km, "_backend_queued", lambda s: False),
            mock.patch.object(km, "_backend_rewind_pending", lambda s: False),
            mock.patch.object(km, "_last_state", lambda s: ("waiting", 0)),
            mock.patch.object(km, "_session_awaiting",
                              lambda sid, path, idle, stamp=False, live=None: None),
            mock.patch.object(km, "_closer_settled", lambda *a, **k: True),
            mock.patch.object(jd, "plan_units", lambda ps, store, **kw: []),   # upstream's gate passes lazy_text=True
            mock.patch.object(km, "_revivers_pending", lambda *a, **k: ""),
            mock.patch.object(km, "_peer_answered_at", lambda sid: 0),
            mock.patch.object(km, "_log_nudge_event", lambda *a, **k: None),
            mock.patch.dict(km._pending_ops, {}, clear=True),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        jd.GOALDIR = self.saved_goaldir
        km.Sessions.backend_for = self.saved_backend
        km._autonudge_cache.clear()
        km._SESSION_STAMP_CACHE.clear()
        super().tearDown()

    def _seed_goals(self, nodes, status=None):
        (jd.GOALDIR / (SID + ".json")).write_text(json.dumps(
            {"rompUuid": SID, "seq": 1, "placements": {}, "status": status or {},
             "nodes": nodes}))

    def _plain_top(self):
        return {"g1": {"id": "g1", "text": "wire the login flow", "parentId": None,
                       "t": NOW - 900, "mt": NOW - 900, "nodeComplete": False,
                       "blocked": False, "cleared": False, "trail": []}}

    def _stamped_top(self, at):
        nd = {"id": "g1", "text": "run the fixture sweep", "parentId": None,
              "t": NOW - 90000, "mt": NOW - 90000, "nodeComplete": False, "blocked": False,
              "cleared": False, "trail": [],
              "awaitingWhy": "the sweep it dispatched; reports when done", "awaitingAt": at,
              "log": [{"ev_t": at, "src": "closer", "kind": "awaiting",
                       "why": "the sweep it dispatched; reports when done", "at": at + 5}]}
        return {"g1": nd}

    def _run(self, alive_ids=None):
        km._autonudge_cache.clear()
        km._SESSION_STAMP_CACHE.clear()
        return km._auto_nudge_session(self.S, NOW, {SID: {"state": ""}}, {}, {},
                                      alive_ids=alive_ids)

    def test_the_status_nudge_stands_down_while_a_todo_is_open(self):
        self._seed_goals(self._plain_top(), status={"g1": "working"})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        self.assertFalse(self._run())
        self.assertEqual(self.sent, [], "the todo already names what a status check would ask")
        self.assertEqual(km._auto_nudge_data().get("nudged", {}), {}, "no record armed either")

    def test_the_gate_lifts_the_moment_the_last_todo_clears(self):
        self._seed_goals(self._plain_top(), status={"g1": "working"})
        tid = km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        km._resolve_user_todo(SID, tid, "dismissed")
        self.assertTrue(self._run(), "with no open todos the status nudge proceeds as before")
        self.assertEqual(len(self.sent), 1)

    def test_the_awaiting_wake_flows_past_an_open_todo(self):
        # the awaiting-wedge shape (2026-08-11): a stamped goal past the 6h backstop whose
        # completion wakeup died. The wake is a lost-wakeup CHECK, not a status ask — an open
        # todo must not put the session back to sleep for days.
        self._seed_goals(self._stamped_top(at=NOW - 7 * 3600), status={"g1": "working"})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        self.assertTrue(self._run(), "the wake fired despite the open todo")
        self.assertEqual(len(self.sent), 1)
        self.assertTrue(km._auto_nudge_data()["nudged"]["g1"].get("wake"),
                        "…and it is the WAKE's episode record, not a status nudge's")

    def test_the_debt_machinery_flows_past_an_open_todo(self):
        # the peer-parked-forever shape: this idle session owes a live peer a reply ("Awaiting
        # us" on their card). The debt reminder is the one mechanism that unparks them; a todo
        # about the USER must not silence it.
        self._seed_goals({}, status={})
        km._add_user_todo(SID, "Need the auth-scheme decision to wire login")
        t_ask = NOW - 1800
        # (last_any, last_ask, last_await): the wait maps carry a third map since upstream #1056 (the
        # latest reply-requiring send per pair); a question is one, so the pair sits there too
        maps = ({(SID2, SID): t_ask},
                {(SID2, SID): (t_ask, "question", "Which port should the staging server use?")},
                {(SID2, SID): t_ask})
        patches = [
            mock.patch.object(km, "_postal_wait_maps", lambda: maps),
            mock.patch.object(km, "_name_of", lambda sid: {SID2: "api", SID: "web"}.get(sid)),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        # upstream (T401 (2) follow-up) reads a KEYED asker's aliveness from its own registry row, the file the
        # debtor's memo key stats (_asker_row_alive): an absent row is a dead asker and the ask is not owed, whatever
        # the alive set says, so the live peer gets the row a revival would write (test_nudge_walk_parse_gate's idiom)
        (jd.STATE / "sdk").mkdir(parents=True, exist_ok=True)
        (jd.STATE / "sdk" / (SID2 + ".json")).write_text(json.dumps({"sid": SID2, "pid": 1, "alive": True}))
        self.assertTrue(self._run(alive_ids={SID, SID2}), "the reminder fired despite the todo")
        self.assertEqual(len(self.sent), 1)
        self.assertIn("api asked you", self.sent[0][1])


if __name__ == "__main__":
    unittest.main()

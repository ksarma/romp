"""A federated chat pane dials the remote with the PAGE'S OWN terms (the design in
plans/federated-pane-dial-terms.md; the code it decides). Two hermetic kernels on one box:
a hub that owns no session and a checked-in TESTHOST that owns two ("api" the watched tab, "worker" a cold
one). The hub's /chat page, in a skeleton posture (?skeleton=1) with the watched tab persisted as a REMOTE
session, dials TESTHOST's relay socket. Before this change the remote dial carried only app+wid, so the
remote built every tab whole, held no skeleton set, and filed an anonymous relay row: the cost the user's
long chat thread ran on. Now federation.ts reads the shim's __rompDialTerms and carries them to each remote
socket, so the remote is served the way the local pane is.

Red first at the base (the bare dial), green with the terms, on three observables:
  1. the relay dial URL (window.__dials) carries skeleton=1, delta=1, the watched tab's BARE sid as
     active=, and an iid namespaced by the hub's wid;
  2. the REMOTE kernel's /perf builds.chat.coldSkipped is >0 (it dieted the cold tab for the hub's
     skeleton client), 0 at the base;
  3. the REMOTE kernel's client-diag.jsonl carries a wsopen row of kind "relay" whose iid presence flag is
     true (the stored row records iid as present/absent, not the value: kernel.py _note_ws_open), where the
     bare dial left it the absent one that reads as an anonymous relay.

This lab boots subprocess kernels and drives Chromium; it loads no romp code in-process, so it carries no
in-process state-isolation preamble and is not scanned by tests/test_state_isolation_order.py (the same as
tests/test_chat_split_host_served.py, its two-kernel sibling). Synthetic only: placeholder uuids, hostname
TESTHOST, invented transcript text.
"""
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlsplit

import lab_dist

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
EXT = os.path.join(ROOT, "vscode-extension")
sys.path.insert(0, HERE)
import test_ship_reship_served as _lab   # noqa: E402  the lab kernel's environment (the module, not its classes)

SID_R0 = "11111111-2222-4333-8444-000000000701"   # "api" on TESTHOST: the tab the page is watching
SID_R1 = "11111111-2222-4333-8444-000000000702"   # "worker" on TESTHOST: a cold tab the skeleton client diets
HOST = "TESTHOST"
REMOTE0 = HOST + ":" + SID_R0                      # …as the hub's dashboard carries it (federation.ts prefixId)
WID = "hublab"                                     # the hub pane's wid: the iid it sends is namespaced by this


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ── the relay dial's caps term, derived from the drive (2026-09-19) ──
# federation.ts writes a relay dial's caps as its own decoder word (REMOTE_DIAL_CAPS) plus the held members it reads from the
# CONN's own bases after connect()'s gated reset: held:feed:<gen>.<rev> from the pair beside the raw feed base, held:bars from
# the receiver's bars base, each omitted when its base is absent or holds no gen. The page's caps string is never a source.
# A lab derives the expectation from the DRIVE, the frames the host's EARLIER relay sockets received as the driver's hook
# records them (type, slot and the stamp fields, never content), by the same rule; on a kernel whose frames carry no gen
# (every kernel in this repo today) that is "feedDelta" on every dial, a redial included, and the labs record exactly that.
REMOTE_DIAL_CAPS = "feedDelta"
STAMP_FIELDS = ("gen", "newGen", "base", "rev", "through")   # what a hook copies off a frame beside its type: the gens as the kernel's strings, the revs as numbers, no content
GEN_FIELDS = ("gen", "newGen")


def client_gen_max():
    """The client's cap on a gen's length, read from its one declaration (ui/webview/view-deltas.ts, `export const GEN_MAX =
    <n>;`), so the mirror below cannot drift from the rule the client applies (round 3, the fixer's pass, 2026-09-20: the
    cap was a second hand-kept literal). A declaration not found fails here, loudly, at import: a mirror that cannot read
    the client's cap must not derive a dial expectation from a cap of its own."""
    src = open(os.path.join(ROOT, "ui", "webview", "view-deltas.ts"), encoding="utf-8").read()
    m = re.search(r"^export const GEN_MAX = (\d+);", src, re.M)
    if not m:
        raise AssertionError("ui/webview/view-deltas.ts no longer declares `export const GEN_MAX = <n>;`: re-aim client_gen_max()")
    return int(m.group(1))


GEN_MAX = client_gen_max()   # the client's cap, derived: the longest gen it reads as a stamp (the relay refuses a request line over 65,536 bytes)


def _utf16_len(v):
    """A string's length as the client counts it (String.length): UTF-16 code units, so a character outside the Basic
    Multilingual Plane counts two where Python's len counts one code point; a lone surrogate passes through as one unit."""
    return len(v.encode("utf-16-le", "surrogatepass")) // 2


REV_MAX = 2 ** 53 - 1   # Number.isSafeInteger's bound: the client reads every rev field as a JavaScript number


def _safe_int(v):
    """A value as the client's Number.isSafeInteger reads it after JSON parsing: an int (never a bool) within plus or minus
    2^53 - 1; else None. The one caller that wants the sign-free form is the feed road's base test, which asks a safe integer at
    or below the held rev and nothing more of it (federation.ts applyRemoteFeedDelta), so a negative base passes there."""
    return v if isinstance(v, int) and not isinstance(v, bool) and -REV_MAX <= v <= REV_MAX else None


def _stamp_field(f, k):
    """A stamp field as the client reads it: a gen (view-deltas.ts genOf) is a non-empty string of at most GEN_MAX UTF-16
    code units (String.length, the client's count: _utf16_len) holding neither '.' (the held member's own separator) nor ','
    (the caps term's), the kernel's boot token and counter joined by '-'; a rev (base, rev, through) is a non-negative safe
    integer (_safe_int: at most 2^53 - 1, since the client's Number.isSafeInteger refuses a rev past it and this rule read one
    as a rev until the author's pass after round 4). Anything else is None, the answer for a value the client cannot read AND
    for a key the frame does not carry: a caller that must tell the two apart reads the key's presence with _stamp_present,
    as held_pair does where it matters (the author's pass 4, 2026-09-20: unparseable is not absent; a present gen the client
    cannot read is a refusal on both roads, never a gen-less frame)."""
    v = f.get(k)
    if k in GEN_FIELDS:
        return v if isinstance(v, str) and v and _utf16_len(v) <= GEN_MAX and "." not in v and "," not in v else None
    v = _safe_int(v)
    return v if v is not None and v >= 0 else None


def _stamp_present(f, k):
    """Whether a recorded frame carried the stamp field `k` at all, whatever its value: the key itself (a hook records a gen
    or newGen of any string or number form as posted) or the presence flag beside it (`<k>Key`), which EVERY frame recorder
    feeding held_pair sets for gen and newGen: the driver hooks of the dial-terms, relay-redial and capability-corners labs
    (both of the corners module's, since the author's pass after round 4: until then those two set neither flag, so a gen of
    null, a boolean, an object or a list, which the hooks copy no value for, read as a gen-less frame in those two labs) and
    the relay-redial consumer's _record (tests/test_relay_dial_declares_held_pair.py), which keeps the revs as the hooks do (any
    number, an integral float as its int: _rev_as_js) and the gens parsed (_stamp_field), so a gen the client cannot read is
    told from an absent one there by this flag alone. FrameRecorderCensus pins the population, the two lines, the type and slot
    rule (a string, else none) and the forms a recorder may take."""
    return k in f or bool(f.get(k + "Key"))


def held_pair(frames, slot):
    """The (gen, rev) pair the client holds for `slot` ("feed" or "bars") after `frames`, the recorded frames of one CONN's relay
    sockets in arrival order (the pair lives on the conn: connect()'s gated reset keeps it across the conn's redials, and
    closeRemote drops the conn, so a host detached and re-attached starts a fresh conn with no pair; the labs using this
    helper never detach a host, so a host's sockets are one conn's), by each road's OWN rule, mirrored test by test in the
    receiver's order (the author's pass after round 4, 2026-09-20, the maintainer's round 4 C: the arms had carried some of
    the receivers' tests and not others, so this declared a pair for frames the client refused; measured on one probe shape
    per refusal point of each receiver, the logs under the review note's section for that pass).

    Both roads: a full carrying a gen the client reads leaves (gen, 0); a full carrying none, or one genOf cannot read, clears
    the pair, and while no pair is held a delta moves nothing here (on the bars road the client applies it onto a gen-less
    base and holds no pair to declare; on the feed road a stamped delta onto a base holding no pair is the gate's "unpaired"
    and applies nothing, a gen-less one applies and writes no pair). A frame of another type or slot moves nothing HERE; on the
    client one such frame does move the feed pair, the acceptance named under THE BOUND below.

    The BARS road (ui/webview/view-deltas.ts receive, onto a base holding a gen), in the receiver's order: the frame's base is
    the held rev exactly (an absent or unreadable base included), else the base is dropped (needSlot: None here); a present
    gen the client cannot read, or a readable gen that is not the base's, drops it; a matched gen with a present newGen the
    client cannot read drops it; then the rev relation: rev a non-negative safe integer and, with a through key, through a
    safe integer with rev at or above the base and equal to through, without one rev equal to base plus one, else dropped.
    Applied, the pair is (the base's gen, the frame's rev), the frame's newGen adopted only when its gen matched and it
    carries through (a gen-less frame's newGen is never adopted: the gate never ran for it). So the bars road APPLIES a
    stamped delta carrying no through at base plus one, where the feed road refuses it, and a gen-less delta in sequence,
    moving the pair's rev under the held gen, where the feed road moves nothing (the two roads' pairs live in different
    places: the feed's in Conn.feedHeld, written under a gen alone, the bars' in the base itself, whose rev every applied
    frame moves).

    The FEED road (ui/webview/federation.ts applyRemoteFeedDelta, onto a held pair), in the gate's order, each refusal leaving
    the pair standing (needFullFeed with the held pair, nothing applied): a gen-less delta (no gen key) applies and moves no
    pair; a present gen the client cannot read, or a readable gen that is not the pair's ("gen"); a present newGen it cannot
    read ("newGen"); a base that is not a safe integer ("base", any sign: the gate asks no more of it) or above the held rev
    ("ahead"); a through absent or not a safe integer ("through") or below the held rev ("behind"); a rev that is not a safe
    integer ("rev") or not equal to the through ("disagree"). Applied, the pair is (newGen when carried, else gen; rev).

    THE BOUND, as a rule (the maintainer's round 5, G): this mirror models every MOVEMENT of the pair the client makes from what a
    frame recorder keeps of a frame (its type and slot when they are strings, since a non-string type or slot is recorded as none
    and moves nothing here, as on the client, which ignores such a frame; the stamp fields, a gen field of any string or number
    and a rev field as a number; and the gen and newGen keys' presence) on the frames each road writes its pair FROM: `feed` and
    `feedDelta` for the feed pair (Conn.feedHeld's two content writers, the feed arm and applyRemoteFeedDelta; its two clears,
    connect()'s gated reset and closeRemote, are the conn's life and not a frame's), `bars` and `delta slot:bars` for the bars pair
    (the receiver's two bases.set writes, the full's seed and the patch's advance). The authorities are the two receivers and the
    writers of Conn.feedHeld, never a list kept here (the maintainer's round 3, tests-3: a hand list here went stale twice in one
    day); test_the_pair_writers_are_counted_so_a_new_one_reds_until_classified derives them from the sources by the PROPERTY and
    not a spelling (the author's fixer pass after round 5, refusal-1: every `feedHeld` token in federation.ts's code, comments
    blanked, is the declaration, a member read or one of the four writes, whatever the receiver's name or the assignment's form,
    and any other form, an object key, a string, a destructuring, is unclassified), so a writer in any spelling or a frame type
    this rule does not read is a census failure; the refusal-site census reads every `throw` statement and every `return` of
    the roads the same way (refusal-2). Outside the rule, in two kinds, each measured and held in RECEIVER_BLIND
    with the client's reading:
    A REFUSAL the receiver makes on content a recorder does not keep, three classes, sharing one property: each leaves this rule
    AHEAD of the client, so expected_relay_caps over-demands a held term in every one; they differ in what the client does next.
    (1) the bars receiver's content checks on a patch, view-deltas.ts receive's throws inside its try (the collections, the
    remainder, a remainder that drops the frame type under restAll, a set, an order, and assemble's throw for a lane holding both
    a scalar and item entries, thrown from a helper inside the try) and a rev field of a type the hooks do not copy (a through of
    "1" at base plus one: the client reads the through and refuses, this reads through-less and applies): the client drops the
    base (needSlot, None), asks for the slot whole and re-seeds at the next whole frame that keys, where this rule advances;
    (2) the bars receiver's refusal of a WHOLE frame, outside its try (receive's full arm: a collection split() cannot key, a
    dictlist given a list, a byid given an object, a lane holding the separator, throws Unkeyable, and the arm deletes the base and
    returns the frame whole, calling neither recover nor throw): the client holds no pair after such a full, a held pair included,
    the delta after it finds no base and asks, and the next whole frame that keys seeds again; this rule reads (gen, 0) from the
    recorded full and advances on the delta;
    (3) the feed road's content refusals, which are applyFeedDelta's throws (ui/webview/feed-delta.ts: asks not a list, an ask
    or a ledger item null, removeAsks not iterable): caught in tryApplyFeedDelta and refused before Conn.feedHeld is written
    (the maintainer's round 5, refusals-2), so the client's pair STANDS while it asks once, bare, per stall and stops asking
    after the answering full, so its divergence from this rule persists across the refused frames where classes 1 and 2 recover
    at the next keyable whole frame; this rule advances it, the one class whose over-demand does not clear on its own. The gate
    itself refuses nothing on content.
    A MOVEMENT from a producer or field outside the set above, of which one exists, and it is an ACCEPTANCE, not a refusal (an
    unreachable acceptance is a different residual from an unreachable refusal, the 19:31Z ruling): the feed arm's store site is
    reached by the receiver's reassembly of a `delta slot:feed` patch as well as by the wire's full (view-deltas.ts slotOf admits
    feed, and every remote frame passes receive() before the arm), and it re-seeds the feed pair from the REASSEMBLED frame's gen:
    the receiver's feed base's gen (recorded on the full, so (gen, 0) with the rev reset: the feed-slotpatch-empty-rest row), or
    the patch's rest.gen (content no recorder keeps: feed-slotpatch-rest-gen, (rest.gen, 0)), or none under restAll (the pair
    CLEARED: feed-slotpatch-restall). This rule reads no `delta` frame on the feed slot and holds the pair the deltas before it
    left, so it reads (gen, 1) for all three. No kernel in this repo sends a delta slot:feed patch to a socket that announced
    caps=feedDelta, and none stamps a gen on that road, so the shape is unreachable against every kernel here; the client road is
    live (federation-remote-view-delta.test.ts drives the patch, and federation-remote-feed-delta.test.ts reads the three
    re-seeds). A base or rev of a type no recorder keeps reads as absent on both sides and is refused on both. The words the feed
    gate files are stale_why_words()'s derivation in tests/test_client_diag_allowlist.py. None when no pair is held."""
    full, delta = ("feed", "feedDelta") if slot == "feed" else ("bars", "delta")
    pair = None
    for f in frames:
        t = f.get("t")
        if t == full:
            g = _stamp_field(f, "gen")
            pair = (g, 0) if g is not None else None
            continue
        if t != delta or (slot == "bars" and f.get("slot") != "bars"):
            continue
        if pair is None:
            continue   # no pair held: a delta moves nothing here (a stamped one onto no pair is the feed road's "unpaired" refusal and applies nothing; the bars road applies it and seeds no gen)
        held_gen, held_rev = pair
        g, new_gen = _stamp_field(f, "gen"), _stamp_field(f, "newGen")
        gen_key, new_key, through_key = _stamp_present(f, "gen"), _stamp_present(f, "newGen"), "through" in f
        rev, through = _stamp_field(f, "rev"), _stamp_field(f, "through")
        if slot == "bars":
            # view-deltas.ts receive, in its order; every refusal drops the base (needSlot), so nothing is held after it
            base = _stamp_field(f, "base")
            if base != held_rev:
                pair = None   # the exact-base test (:211): an absent or unreadable base is not the held rev either
                continue
            if (gen_key and g is None) or (g is not None and g != held_gen):
                pair = None   # the gen gate (:229): a present gen the client cannot read, or another stream's gen
                continue
            if g is not None and new_key and new_gen is None:
                pair = None   # a matched gen with a newGen the client cannot read (:230)
                continue
            if rev is None or (through_key and (through is None or rev < base or rev != through)) or (not through_key and rev != base + 1):
                pair = None   # the rev relation (revOk): through present means rev at or above base and equal to it, absent means base plus one
                continue
            adopt = new_gen if through_key and g is not None else None   # a newGen rides only a matched, through-carrying frame
            pair = (adopt if adopt is not None else held_gen, rev)
        else:
            # applyRemoteFeedDelta's gate, in its order; every refusal leaves the pair standing (needFullFeed with the held pair)
            if not gen_key:
                continue   # a gen-less delta applies and moves no pair (the vintage guard: Conn.feedHeld is written under a gen alone)
            if g is None or g != held_gen:
                continue   # "gen": a present gen the client cannot read, or another stream's
            if new_key and new_gen is None:
                continue   # "newGen"
            base = _safe_int(f.get("base"))
            if base is None or base > held_rev:
                continue   # "base", "ahead"
            if through is None or through < held_rev:
                continue   # "through" (absent or unreadable), "behind"
            if rev is None or rev != through:
                continue   # "rev", "disagree"
            pair = (new_gen if new_gen is not None else g, rev)
    return pair


def drive_pair(tc, frames, slot):
    """held_pair over a lab's recorded drive, telling "no gen key" from "a gen key the client reads as none". A hook records
    `genKey` (a bool: the frame carried a `gen` key, whatever its value; no content) beside the parsed stamp fields, and
    _stamp_field drops a gen the client would refuse (view-deltas.ts genOf: a number, an empty string, a '.' or ',', one over
    GEN_MAX characters), so
    held_pair alone reads a kernel stamping an unreadable gen exactly as one stamping none. None only when NO recorded frame
    carried the key (a kernel before the stamp: the leg's skip-and-branch case); a frame carried the key but no pair parsed
    is a failure on `tc`: the kernel stamped a gen the client reads as none, a stamped full was followed by a gen-less one
    (the rollback shape), or the key rode a frame this rule reads no pair from (a delta while no full carried one, or a
    frame of another type) while the full carried none, none of which a leg may pass green as "undeclared"."""
    pair = held_pair(frames, slot)
    if pair is None and any(f.get("genKey") for f in frames):
        tc.fail("a frame carried a gen key but no pair parsed for %r: the kernel stamped a gen the client reads as none "
                "(view-deltas.ts genOf), a stamped full was followed by a gen-less one, or the key rode a frame this rule reads "
                "no pair from (a delta while no full carried one, or a frame of another type) while the full carried none: %r"
                % (slot, frames))
    return pair


def composed_frames(frames, slot):
    """The recorded deltas of `slot` whose `newGen` parsed (_stamp_field): the composed frame a declaring dial earns. A
    per-cycle K2 delta carries `through` (equal to its rev) and no `newGen`, so `through` never tells a composed frame; the
    labs count the composed frame by this and never by `through`."""
    delta = "feedDelta" if slot == "feed" else "delta"
    return [f for f in frames if f.get("t") == delta and (slot == "feed" or f.get("slot") == "bars")
            and _stamp_field(f, "newGen") is not None]


def expected_relay_caps(prev_frames):
    """The caps term a relay dial carries: REMOTE_DIAL_CAPS, then held:feed:<g>.<r> and held:bars:<g>.<r> for the pairs the
    CONN's EARLIER relay sockets left it (held_pair over their recorded frames in arrival order: the client keeps a base
    holding a gen across a redial, so a third dial declares what the whole stream left, not what one socket received),
    each omitted when none is held. `prev_frames` is None for a first dial (no socket before it). A redial none of whose
    earlier sockets recorded a frame is an empty drive and an AssertionError: the expectation never rests on nothing.
    Precondition (review round 1, 2026-09-20): assert_relay_dials keys the earlier sockets by HOST, which equals the conn
    only while no host detaches and re-attaches (closeRemote drops the conn and its pair; the re-attach is a first dial
    again, REMOTE_DIAL_CAPS alone). No lab using this helper detaches a host; a lab that does must restart the drive at the
    re-attach, recording the detach's position in the socket sequence, since this helper keeps no socket indices. The
    hook and the conn keying land with the first lab that detaches or the first kernel that stamps a gen, whichever comes
    first; no failing-before test exists for it here, since neither does yet."""
    if prev_frames is None:
        return REMOTE_DIAL_CAPS
    if not prev_frames:
        raise AssertionError("the host's earlier relay sockets recorded no frames: no drive to derive the redial's caps term from")
    words = [REMOTE_DIAL_CAPS]
    for slot in ("feed", "bars"):
        pair = held_pair(prev_frames, slot)
        if pair is not None:
            words.append("held:%s:%s.%d" % (slot, pair[0], pair[1]))
    return ",".join(words)


def relay_dials(dials):
    """[(index, host, url)] for every /remote/<host>/ws dial among `dials`, the page's dials in order (the index is the hook's
    socket index, the `sock` its frame records carry). Guarded non-empty."""
    out = []
    for i, u in enumerate(dials):
        m = re.search(r"/remote/([^/]+)/ws", u)
        if m:
            out.append((i, unquote(m.group(1)), u))
    if not out:
        raise AssertionError("the page dialed no relay socket: %r" % (dials,))
    return out


def assert_relay_dials(tc, app, dials, frames, caps=True):
    """Every relay dial the page made carries `app`, delta=1 and the caps term expected_relay_caps derives from the frames
    EVERY earlier relay socket of the host received, in arrival order (`frames`: the hook's records, each naming its socket
    index under `sock`; the recorded order is the page's, and a frame the page discarded after abandoning its socket is not
    modelled), or no caps term where the lab strips it (caps False). Returns the dials checked, [(index, host, url)]."""
    earlier = {}   # host -> the socket indices of its earlier relay dials
    checked = relay_dials(dials)
    for i, host, u in checked:
        qs = parse_qs(urlsplit(u).query)
        tc.assertEqual(qs.get("app"), [app], "the pane's app on the relay dial: %r" % (u,))
        tc.assertEqual(qs.get("delta"), ["1"], "the page's delta term rides the relay dial (since 2026-09-15): %r" % (u,))
        drive = [f for f in frames or [] if f.get("sock") in earlier[host]] if host in earlier else None
        expected = expected_relay_caps(drive) if caps else None
        tc.assertEqual(qs.get("caps"), ([expected] if expected else None),
                       "the relay dial's caps term: federation's decoder word and the held members its conn's bases give it, "
                       "derived from the frames the host's earlier sockets received (none on a first dial), or no term where the page strips it: %r" % (u,))
        earlier.setdefault(host, set()).add(i)
    return checked


SEED_PAIRS = 6         # closed pairs per seed transcript: one bar each on the timeline
SEED_PAIR_S = 720      # a stamped seed (t0 given): pair i's user row at t0 + SEED_PAIR_S * i, its assistant row SEED_REPLY_S later
SEED_REPLY_S = 30


def _stamp(t):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))


def seed_uuid(tag, i, role="a"):
    """The uuid _transcript mints for pair `i` of a seed with `tag` ("u" the user row, "a" the assistant row): a later
    append chains its parentUuid to the seed's last assistant row (the bars lab, the corners' transcript change)."""
    return "%s-%s%02d" % (tag, role, i)


def _transcript(sid, tag, cwd, pairs, t0=None):
    """`pairs` CLOSED user/assistant turns for `sid` (an OPEN turn would invite the boot reconcile to resume it).
    Stamped in 2024 by default; with `t0` (epoch seconds) pair i is stamped at t0 + SEED_PAIR_S * i and its reply
    SEED_REPLY_S later, so a lab's timeline page shows the seed as a board of the last hours in plain time. The
    kernel filters no bar by time, and the pane's default view collapses idle gaps, so it draws a 2024 seed too
    (the idle span since is squeezed to a gap); the stamps are for the record's readability and the plain-time
    view, not a condition of the bars being drawn (tests/test_federated_bars_delta_served.py, driven both ways)."""
    out, parent = [], None
    filler = ["The ranking pass reads its weights from the notes-api config now.",
              "Tokenizer edge cases (hyphens, quotes) are covered by the new fixture set.",
              "Index rebuild time is dominated by the stemmer; caching its table halves it."]
    for i in range(pairs):
        u, a = seed_uuid(tag, i, "u"), seed_uuid(tag, i, "a")
        if t0 is None:
            ts_u, ts_a = "2024-01-01T00:%02d:00Z" % (i % 60), "2024-01-01T00:%02d:30Z" % (i % 60)
        else:
            ts_u, ts_a = _stamp(t0 + SEED_PAIR_S * i), _stamp(t0 + SEED_PAIR_S * i + SEED_REPLY_S)
        out.append({"type": "user", "uuid": u, "parentUuid": parent, "sessionId": sid, "cwd": cwd,
                    "timestamp": ts_u, "promptSource": "typed",
                    "message": {"role": "user", "content": "turn %d: what changed in the notes-api search?" % i}})
        out.append({"type": "assistant", "uuid": a, "parentUuid": u, "sessionId": sid, "cwd": cwd,
                    "timestamp": ts_a,
                    "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                                "content": [{"type": "text", "text": filler[i % len(filler)]}]}})
        parent = a
    return "".join(json.dumps(r) + "\n" for r in out)


def _kernel(lab, name, port, token, sessions, bin_dir=BIN, t0=None):
    """Boot one hermetic kernel: its own state root and dist, and `sessions` [(sid, name, tag)] with closed-turn transcripts.
    `bin_dir` is the checkout whose bin/romp-kernel runs: this one by default; another vintage's for a mixed-build lab
    (tests/test_federated_capability_corners_served.py boots an older remote or hub against this checkout's pages).
    `t0` stamps the seed transcripts from that epoch (see _transcript); None keeps the 2024 stamps."""
    state = os.path.join(lab, name, "xdg", "romp")
    claude = os.path.join(lab, name, "claude")
    cwd = os.path.join(lab, name, "proj")
    for d in ("names", "sdk", "states"):
        os.makedirs(os.path.join(state, d), exist_ok=True)
    os.makedirs(cwd, exist_ok=True)
    Path(state, "session-hosts").write_text("off\n")   # a lab root writes its own hosts off (the conftest rule)
    Path(state, "usage.json").write_text(json.dumps({"five_hour": {"pct": 100}, "seven_day": {"pct": 10}}))   # park sends
    proj = os.path.join(claude, "projects", re.sub(r"[^A-Za-z0-9]", "-", os.path.realpath(cwd)))
    os.makedirs(proj, exist_ok=True)
    for sid, sname, tag in sessions:
        Path(state, "names", sid).write_text("%s\t%s\t\t\n" % (sname, cwd))
        Path(state, "sdk", sid + ".json").write_text(json.dumps(
            {"sid": sid, "name": sname, "cwd": cwd, "mode": "auto", "effort": "high", "lastSid": sid, "alive": True}))
        Path(proj, sid + ".jsonl").write_text(_transcript(sid, tag, cwd, SEED_PAIRS, t0=t0))
    env = _lab.kernel_env(os.path.join(lab, name), claude, os.path.join(lab, "dist"), port, token, ROMP_HOST_NAME=name.upper())
    log = os.path.join(lab, name + "-kernel.log")
    proc = subprocess.Popen([os.path.join(bin_dir, "romp-kernel")], stdout=open(log, "w"), stderr=subprocess.STDOUT, env=env)
    for _ in range(120):
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/healthz" % port, timeout=1)
            return proc, log
        except Exception:
            time.sleep(0.5)
    proc.kill(); proc.wait()
    raise unittest.SkipTest("hermetic kernel %s never served /healthz here" % name)


CHANGE_USER_AGO_S = 60    # an appended pair (change_pair): the user row this long before `now`, the reply CHANGE_REPLY_AGO_S before it
CHANGE_REPLY_AGO_S = 30


def change_pair(sid, tag, cwd, prompt, reply, now=None, pairs=SEED_PAIRS):
    """One CLOSED user/assistant pair to append to a seed transcript as a lab's change: fresh uuids, chained to the seed's
    last assistant row (seed_uuid), the user row CHANGE_USER_AGO_S before `now` and the reply CHANGE_REPLY_AGO_S before
    it. Closed, because an open turn on a registry-alive session invites the SDK backend's reconcile; staggered,
    because the timeline pane culls a bar whose start equals its end; both at or before now, because the pane clips a
    bar's end to the live edge. Returns the rows as jsonl text."""
    now = time.time() if now is None else now
    u, a = str(uuid.uuid4()), str(uuid.uuid4())
    rows = [{"type": "user", "uuid": u, "parentUuid": seed_uuid(tag, pairs - 1, "a"), "sessionId": sid, "cwd": cwd,
             "timestamp": _stamp(now - CHANGE_USER_AGO_S), "promptSource": "typed",
             "message": {"role": "user", "content": prompt}},
            {"type": "assistant", "uuid": a, "parentUuid": u, "sessionId": sid, "cwd": cwd,
             "timestamp": _stamp(now - CHANGE_REPLY_AGO_S),
             "message": {"role": "assistant", "model": "claude-opus-5", "stop_reason": "end_turn",
                         "content": [{"type": "text", "text": reply}]}}]
    return "".join(json.dumps(r) + "\n" for r in rows)


def checkin(hport, htoken, rport, rtoken, host=HOST):
    """Check the remote kernel in with the hub (POST /checkin) and wait until the hub reports the peer up with its token
    (the hub's supervisor probes the peer and reports it up; the browser dials only then). A refusal or a peer that
    never comes up skips the lab."""
    body = json.dumps({"host": host, "kernelPort": rport, "busPort": _free_port(), "token": rtoken}).encode()
    req = urllib.request.Request("http://127.0.0.1:%d/checkin?token=%s" % (hport, htoken), data=body,
                                 headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=5) as resp:
        ans = json.loads(resp.read().decode())
    if not ans.get("ok"):
        raise unittest.SkipTest("the hub refused the check-in: %r" % ans)
    rows = []
    for _ in range(60):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/tunnels?token=%s" % (hport, htoken), timeout=3) as r2:
                rows = json.loads(r2.read().decode()).get("tunnels") or []
        except Exception:
            rows = []
        row = next((t for t in rows if t.get("host") == host), None)
        if row and row.get("status") == "up" and row.get("hasToken"):
            return
        time.sleep(0.5)
    raise unittest.SkipTest("the hub never reported the checked-in peer up: %r" % (rows,))


# The Chromium driver: hook every socket URL the page dials (window.__dials) and, on a relay socket, every frame it
# receives by its socket index, type, slot and stamp fields (window.__frames: no content; the drive expected_relay_caps
# reads), persist the watched tab as a REMOTE session before the page's scripts run (the shim's ?active= and
# __rompDialTerms read it), open the hub's /chat page in a skeleton posture, and wait for the relay socket to the remote.
# The kernel-side observables (the remote's /perf and client-diag) are read from Python after this returns.
DRIVER = r"""
import { createRequire } from "node:module";
import fs from "node:fs";
const require = createRequire(process.env.EXT_PKG);
const { chromium } = require("playwright");
const cfg = JSON.parse(fs.readFileSync(process.env.CFG, "utf8"));
let browser;
try { browser = await chromium.launch(cfg.launch || {}); }
catch (e) { console.error("browser-launch-failed: " + e); process.exit(3); }
const context = await browser.newContext({ viewport: { width: 1200, height: 700 } });
const page = await context.newPage();
const out = { dials: [], frames: [], died: null, tabSeen: false };
page.on("pageerror", () => {});
await page.addInitScript(() => {
  window.__dials = []; window.__frames = []; const W = window.WebSocket;
  window.WebSocket = function (url, protos) {
    const u = String(url); const idx = window.__dials.length; window.__dials.push(u);
    const w = protos === undefined ? new W(u) : new W(u, protos);
    if (u.indexOf("/remote/") !== -1) {
      w.addEventListener("message", (ev) => {
        try {
          const m = JSON.parse(ev.data);
          if (m && m.type !== "ka") {
            const f = { sock: idx, t: typeof m.type === "string" ? m.type : "", slot: typeof m.slot === "string" ? m.slot : "" };   // type and slot as the client reads them: a string, else none (a String() here read an array ['bars'] as the word the client ignores; the author's fixer pass after round 4)
            for (const k of ["gen", "newGen", "base", "rev", "through"]) if (typeof m[k] === "number" || (typeof m[k] === "string" && (k === "gen" || k === "newGen"))) f[k] = m[k];   // the revs as numbers, the gens as the kernel's strings; no content
            if ("gen" in m) f.genKey = true;   // the key's presence, whatever its value: drive_pair tells an unreadable gen from none
            if ("newGen" in m) f.newGenKey = true;   // the same for newGen: held_pair reads a present newGen the client cannot read as the refusal it is (round 4)
            window.__frames.push(f);
          }
        } catch (e) {}
      });
    }
    return w;
  };
  window.WebSocket.prototype = W.prototype; window.WebSocket.CONNECTING = 0; window.WebSocket.OPEN = 1; window.WebSocket.CLOSING = 2; window.WebSocket.CLOSED = 3;
});
// the watched tab is a REMOTE session, host-prefixed as the dashboard carries it: __rompDialTerms carries it
// to the remote dial, where federation.ts strips the host to the bare sid the remote knows
await page.addInitScript((rid) => { try { localStorage.setItem("romp-vscode-state-chat", JSON.stringify({ activeId: rid })); } catch (e) {} }, cfg.remote0);
try {
  await page.goto(cfg.chat);
  // the FederationManager attaches every checked-in remote on load; wait for its relay socket to be dialed
  await page.waitForFunction(() => (window.__dials || []).some((u) => u.indexOf("/remote/TESTHOST/ws") !== -1), null, { timeout: 30000 });
  // the remote tab surfaces once the relay is open (best-effort confirmation; the assertions read __dials + the remote kernel)
  try { await page.locator("#tabs .tab", { hasText: "TESTHOST" }).first().waitFor({ timeout: 15000 }); out.tabSeen = true; } catch (e) {}
  // let the remote serve the skeleton client: the watched tab full, the cold tab skipped, the relay wsopen row filed
  await page.waitForTimeout(3000);
  Object.assign(out, await page.evaluate(() => ({ dials: (window.__dials || []).slice(), frames: (window.__frames || []).slice() })));
} catch (e) {
  out.died = String(e).slice(0, 400);
  try { Object.assign(out, await page.evaluate(() => ({ dials: (window.__dials || []).slice(), frames: (window.__frames || []).slice() }))); } catch (e2) {}
}
console.log("RESULT:" + JSON.stringify(out));
await browser.close();
"""


# gens in the kernel's form (the boot's 16-hex token, '-', a decimal counter), for the rule's own tests
GEN_STAMP = "0123456789abcdef"
GEN, GEN2, GEN3 = GEN_STAMP + "-7", GEN_STAMP + "-9", GEN_STAMP + "-3"

# ── the mirror against the client, one probe shape per refusal point of each receiver (the author's pass after round 4) ──
# Each row: the case, the slot, the frames as a driver hook RECORDS them (type, slot, the stamp fields the hook copies, the gen
# and newGen presence flags; no content), and the pair the CLIENT held after the same frames in the probe (view-deltas.ts
# ViewDeltas for the bars road, the real FederationManager over federation-remote-feed-delta.test.ts's rig for the feed road;
# the probe and its logs under the review note's section for that pass). held_pair must read every row as the client did. The
# rows are the receivers' refusal points in source order, one shape each, then the applying shapes, then the shapes the
# maintainer's round 4 measured. RECEIVER_BLIND rows are the recorder-blind class the docstring names (a refusal the receiver
# makes on content a hook does not keep): the fifth member is what this rule reads there, asserted so the divergence stays
# named and measured, never silent.
OVER = GEN_STAMP + "-" + "9" * 48   # 65 characters: one over GEN_MAX
GEN11 = GEN_STAMP + "-11"
RECEIVER_CASES = [
    ('bars-slot-other', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "lanes", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}], (GEN, 0), None),  # R1 unknown slot (:200): a delta for a slot this receiver has no table for
    ('bars-slot-nonstring', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "7", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}], (GEN, 0), None),  # R1 unknown slot (:200): a non-string slot, no ask
    ('bars-nobase-none', 'bars', [{"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, None),  # R2 no base (:201): a delta before any whole frame
    ('bars-nobase-nogen', 'bars', [{"t": "bars", "slot": ""}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, None),  # no refusal: a base seeded by a full without a gen applies and declares nothing
    ('bars-nobase-badgen', 'bars', [{"t": "bars", "slot": "", "gen": GEN + ".x", "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, None),  # no refusal: a base seeded by a full whose gen genOf cannot read holds no gen
    ('bars-base-genless-ahead', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 1, "rev": 2}], None, None),  # R3 exact base (:211): a gen-less delta whose base is above the held rev
    ('bars-base-genless-replay', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, None),  # R3 exact base (:211): a gen-less delta replaying an applied base
    ('bars-base-stamped-ahead', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "base": 2, "rev": 3, "through": 3, "genKey": True}], None, None),  # R3 exact base (:211): a stamped delta whose base is above the held rev
    ('bars-base-composed-same-rev', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "newGen": GEN2, "base": 0, "rev": 1, "through": 1, "genKey": True, "newGenKey": True}], None, None),  # R3 exact base (:211): a composed frame at the held rev's predecessor base (correctness-3's shape)
    ('bars-base-absent', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "rev": 1}], None, None),  # R3 exact base (:211): no base field
    ('bars-base-string', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "rev": 1}], None, None),  # R3 exact base (:211): a base of a type the hook does not copy
    ('bars-base-negative', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": -1, "rev": 0}], None, None),  # R3 exact base (:211) and :245 (base < 0): a negative base
    ('bars-gen-number', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": 8, "base": 0, "rev": 1, "through": 1, "genKey": True}], None, None),  # R4 gen gate (:229): a present gen genOf cannot read (a number) onto a gen-holding base
    ('bars-gen-empty', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": "", "base": 0, "rev": 1, "through": 1, "genKey": True}], None, None),  # R4 gen gate (:229): an empty-string gen
    ('bars-gen-separator', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN + ".7", "base": 0, "rev": 1, "through": 1, "genKey": True}], None, None),  # R4 gen gate (:229): a gen carrying the held member's separator
    ('bars-gen-overcap', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": OVER, "base": 0, "rev": 1, "through": 1, "genKey": True}], None, None),  # R4 gen gate (:229): a gen over GEN_MAX
    ('bars-gen-null', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1, "through": 1, "genKey": True}], None, None),  # R4 gen gate (:229): a gen of null (the corners hooks record neither value nor flag: the flag fix)
    ('bars-gen-foreign', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN2, "base": 0, "rev": 1, "through": 1, "genKey": True}], None, None),  # R4 gen gate (:229): a readable gen that is not the base's
    ('bars-newgen-unreadable', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "newGen": 9, "base": 0, "rev": 1, "through": 1, "genKey": True, "newGenKey": True}], None, None),  # R5 newGen (:230): a matched gen with a newGen genOf cannot read
    ('bars-newgen-null', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True, "newGenKey": True}], None, None),  # R5 newGen (:230): a newGen of null
    ('bars-rev-float', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1.5}], None, None),  # R6 revOk (:244-248): a rev that is not a safe integer
    ('bars-rev-huge', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 2 ** 53 + 1, "through": 2 ** 53 + 1}], None, None),  # R6 revOk (:244-248): a rev past 2^53
    ('bars-rev-string', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0}], None, None),  # R6 revOk (:244-248): a rev of a type the hook does not copy
    ('bars-through-disagree', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "base": 0, "rev": 1, "through": 2, "genKey": True}], None, None),  # R6 revOk (:244-248): through present and rev not equal to it
    ('bars-through-rev-below-base', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}, {"t": "delta", "slot": "bars", "base": 1, "rev": 2}, {"t": "delta", "slot": "bars", "base": 2, "rev": 1, "through": 1}], None, None),  # R6 revOk (:244-248): through present and rev below base
    ('bars-nothrough-skip', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 5}], None, None),  # R6 revOk (:244-248): no through and rev not base plus one
    ('bars-nothrough-same', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 0}], None, None),  # R6 revOk (:244-248): no through and rev equal to base
    ('bars-through-float', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1, "through": 1.5}], None, None),  # R6 revOk (:244-248): a through that is a number but not a safe integer
    ('bars-apply-genless', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], (GEN, 1), None),  # applies: a gen-less delta at base plus one
    ('bars-apply-genless-two', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}, {"t": "delta", "slot": "bars", "base": 1, "rev": 2}], (GEN, 2), None),  # applies: two gen-less deltas in sequence
    ('bars-apply-genless-newgen', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "newGen": GEN2, "base": 0, "rev": 1, "through": 1, "newGenKey": True}], (GEN, 1), None),  # applies: a gen-less delta carrying newGen and through (the newGen not adopted)
    ('bars-apply-genless-through', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1, "through": 1}], (GEN, 1), None),  # applies: a gen-less delta carrying through equal to rev at base plus one
    ('bars-apply-stamped-cycle', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}], (GEN, 1), None),  # applies: a stamped per-cycle delta
    ('bars-apply-composed', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "newGen": GEN2, "base": 0, "rev": 4, "through": 4, "genKey": True, "newGenKey": True}], (GEN2, 4), None),  # applies: a composed frame (newGen adopted)
    ('bars-apply-composed-caught-up', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "newGen": GEN2, "base": 0, "rev": 0, "through": 0, "genKey": True, "newGenKey": True}], (GEN2, 0), None),  # applies: a composed frame at the held rev (rev equal to base)
    ('bars-apply-stamped-nothrough', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "base": 0, "rev": 1, "genKey": True}], (GEN, 1), None),  # applies on THIS road: a stamped delta carrying no through at base plus one (the feed road refuses it)
    ('bars-apply-after-composed', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN, "newGen": GEN2, "base": 0, "rev": 4, "through": 4, "genKey": True, "newGenKey": True}, {"t": "delta", "slot": "bars", "gen": GEN2, "base": 4, "rev": 5, "through": 5, "genKey": True}], (GEN2, 5), None),  # applies: a per-cycle delta under the new generation after a composed frame
    ('bars-refuse-then-reseed', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "gen": GEN2, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "bars", "slot": "", "gen": GEN11, "genKey": True}], (GEN11, 0), None),  # after a refusal (a foreign gen) the next whole frame re-seeds
    ('bars-slot-array', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "", "base": 0, "rev": 1}], (GEN, 0), None),  # R1 (:200): a slot that is the array ['bars'], recorded as none (the hooks keep a string slot alone since the fixer pass; a String() read it as the word): the client returns null with no ask, the pair stands
    ('bars-type-array-delta', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "", "slot": "bars", "base": 0, "rev": 1}], (GEN, 0), None),  # a type that is the array ['delta'], recorded as none: the client passes the frame through, nothing applied
    ('bars-type-array-full', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "", "slot": "", "gen": GEN2, "genKey": True}], (GEN, 0), None),  # a type that is the array ['bars']: not a full to the client, the pair stands
    ('feed-type-array-delta', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "", "slot": "", "gen": GEN, "base": 1, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), None),  # a type that is the array ['feedDelta']: ignored by the client, the pair stands
    ('feed-type-array-full', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "", "slot": "", "gen": GEN2, "genKey": True}], (GEN, 0), None),  # a type that is the array ['feed']: not a full to the client
    ('feed-base-written-float', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "through": 2, "genKey": True}], (GEN, 2), None),  # the wire text base 1.0, rev 2.0 or through 2e0 is the number the client reads as a safe integer; every recorder keeps it as the int (the Python one since the fixer pass: _rev_as_js), so the recorded row is the applying row
    ('feed-nobase', 'feed', [{"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}], None, None),  # A nobase (:1518): a delta before any full frame on the conn
    ('feed-genless-applies', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "base": 1, "rev": 2}], (GEN, 1), None),  # no refusal: a gen-less delta applies and moves no pair (the vintage guard)
    ('feed-genless-newgen-through', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "newGen": GEN2, "base": 1, "rev": 2, "through": 2, "newGenKey": True}], (GEN, 1), None),  # no refusal: a gen-less delta carrying newGen and through moves no pair
    ('feed-unreadable-gen-nogen-base', 'feed', [{"t": "feed", "slot": ""}, {"t": "feedDelta", "slot": "", "gen": 8, "base": 0, "rev": 1, "through": 1, "genKey": True}], None, None),  # no refusal: an unreadable gen onto a base holding no pair applies as gen-less
    ('feed-unpaired', 'feed', [{"t": "feed", "slot": ""}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}], None, None),  # D unpaired: a stamped delta onto a base holding no pair
    ('feed-unpaired-badgen-full', 'feed', [{"t": "feed", "slot": "", "gen": GEN + ".x", "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}], None, None),  # D unpaired: the full's gen was unreadable, so no pair is held
    ('feed-gen-number', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": 8, "base": 1, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), None),  # D gen: a present gen genOf cannot read onto a held pair
    ('feed-gen-null', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "base": 1, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), None),  # D gen: a gen of null onto a held pair (the corners hooks' blind type)
    ('feed-gen-overcap', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": OVER, "base": 1, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), None),  # D gen: a gen over GEN_MAX
    ('feed-gen-foreign', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN2, "base": 1, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), None),  # D gen: a readable gen that is not the held pair's
    ('feed-newgen-unreadable', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "newGen": 9, "base": 1, "rev": 2, "through": 2, "genKey": True, "newGenKey": True}], (GEN, 1), None),  # D newGen: a matched gen with a newGen genOf cannot read
    ('feed-newgen-null', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "through": 2, "genKey": True, "newGenKey": True}], (GEN, 1), None),  # D newGen: a newGen of null
    ('feed-base-float', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1.5, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), None),  # D base: a base that is not a safe integer
    ('feed-base-string', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), None),  # D base: a base of a type the hook does not copy
    ('feed-base-absent', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), None),  # D base: no base field
    ('feed-base-negative-applies', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": -1, "rev": 2, "through": 2, "genKey": True}], (GEN, 2), None),  # no refusal: a negative base is a safe integer at or below the held rev (the gate asks no more of it)
    ('feed-ahead', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 5, "rev": 6, "through": 6, "genKey": True}], (GEN, 1), None),  # D ahead: a base above the held rev
    ('feed-through-absent', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "genKey": True}], (GEN, 1), None),  # D through: no through on a stamped delta
    ('feed-through-string', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "genKey": True}], (GEN, 1), None),  # D through: a through of a type the hook does not copy
    ('feed-through-huge', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2 ** 53 + 1, "through": 2 ** 53 + 1, "genKey": True}], (GEN, 1), None),  # D through: a through past 2^53
    ('feed-behind', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "through": 2, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 2, "rev": 3, "through": 3, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 2, "through": 2, "genKey": True}], (GEN, 3), None),  # D behind: a through below the held rev
    ('feed-rev-string', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "through": 2, "genKey": True}], (GEN, 1), None),  # D rev: a rev of a type the hook does not copy
    ('feed-rev-float', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2.5, "through": 2, "genKey": True}], (GEN, 1), None),  # D rev: a rev that is not a safe integer
    ('feed-rev-absent', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "through": 2, "genKey": True}], (GEN, 1), None),  # D rev: no rev field
    ('feed-disagree', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 3, "through": 2, "genKey": True}], (GEN, 1), None),  # D disagree: every field valid and rev not the through
    ('feed-apply-cycle', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}], (GEN, 1), None),  # applies: a stamped per-cycle delta
    ('feed-apply-composed', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "newGen": GEN2, "base": 1, "rev": 4, "through": 4, "genKey": True, "newGenKey": True}], (GEN2, 4), None),  # applies: a composed frame (newGen adopted, rev equal to through)
    ('feed-apply-composed-caught-up', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "newGen": GEN2, "base": 1, "rev": 1, "through": 1, "genKey": True, "newGenKey": True}], (GEN2, 1), None),  # applies: a composed frame at the held rev
    ('feed-apply-base-below', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "through": 2, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 3, "through": 3, "genKey": True}], (GEN, 3), None),  # applies: a stamped delta whose base is below the held rev with through at it
    ('feed-apply-after-composed', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "newGen": GEN2, "base": 1, "rev": 4, "through": 4, "genKey": True, "newGenKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN2, "base": 4, "rev": 5, "through": 5, "genKey": True}], (GEN2, 5), None),  # applies: a per-cycle delta under the new generation
]
RECEIVER_BLIND = [
    ('bars-through-string', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R6 revOk (:244-248): a through of a type the hook does not copy (recorder blindness: reads as through-less here)
    ('bars-coll-list', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R6 (:248) object(coll) false: the recorder cannot see collections
    ('bars-rest-list', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R7 (:251) rest not an object
    ('bars-rest-type', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R7 (:251) rest.type not the slot
    ('bars-rest-collection', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R8 (:256) a collection key in the remainder
    ('bars-coll-unknown', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R10 (:262) an unknown collection name
    ('bars-coll-change-scalar', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R10 (:262) a non-object change
    ('bars-set-scalar', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R11 (:268) change.set not an object
    ('bars-del-nonstrings', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R13 stringKeys (:137) del not a list of strings
    ('bars-order-incomplete', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R12 (:275-277) incomplete collection order
    ('bars-rest-restall-type-dropped', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # R9 (:260) a remainder under restAll that carries no type drops the frame type: "missing frame type" (the point the pass enumerated and never probed: text-1)
    # the full path (class 2 of the docstring): a bars FULL one of whose collections split() cannot key throws Unkeyable and the
    # full arm deletes the base (view-deltas.ts:178-190, neither a recover call nor a throw inside the try); every hook records
    # the frame as {t: bars, gen, genKey}, the same record a keyable full leaves
    ('bars-full-unkeyable-turns-list', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}], None, (GEN, 0)),  # turns a list where the kind is a dictlist: the client seeds no base
    ('bars-full-unkeyable-judging-list', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}], None, (GEN, 0)),  # judging a list
    ('bars-full-unkeyable-messages-object', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}], None, (GEN, 0)),  # messages an object where the kind is a byid list
    ('bars-full-unkeyable-lane-sep', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}], None, (GEN, 0)),  # a lane holding the separator (the kernel's twin refusal)
    ('bars-full-unkeyable-after-pair', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}, {"t": "bars", "slot": "", "gen": GEN2, "genKey": True}], None, (GEN2, 0)),  # an unkeyable full after a held pair drops the base; this rule reseeds
    ('bars-full-unkeyable-then-delta', 'bars', [{"t": "bars", "slot": "", "gen": GEN, "genKey": True}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], None, (GEN, 1)),  # the delta after an unkeyable full finds no base (R2, needSlot); this rule applies it
    # the feed road's content refusals (class 3): applyFeedDelta's throws, caught since the maintainer's round 5 (refusals-2) in
    # feed-delta.ts and refused before Conn.feedHeld is written, so the client's pair STANDS (this rule advances it, the direction
    # expected_relay_caps would over-demand); the client asks once, bare, per stall and stops after the answering full
    ('feed-apply-throw-asks-object', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), (GEN, 2)),  # asks an object: ups.map is not a function
    ('feed-apply-throw-asks-null-item', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), (GEN, 2)),  # an ask that is null: reading itemId of null
    ('feed-apply-throw-removeAsks-number', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), (GEN, 2)),  # removeAsks a number: not iterable (new Set)
    ('feed-apply-throw-ledgers-null-item', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "through": 2, "genKey": True}], (GEN, 1), (GEN, 2)),  # a ledger item that is null: reading sid of null
    # the fourth shape, an ACCEPTANCE and not a refusal (the maintainer's round 5, extra7-1, and the 19:31Z ruling): a {type: delta,
    # slot: feed} patch on a remote conn is reassembled by the conn's receiver into a feed frame that enters the feed arm, which
    # re-seeds Conn.feedHeld from the reassembled frame's gen; the recorder keeps the patch's t, slot, base and rev and no rest
    # content, and this rule reads no delta frame on the feed slot, so it holds (GEN, 1) while the client reads (rest.gen, 0),
    # (GEN, 0) or nothing. Measured in the node rig (federation-remote-feed-delta.test.ts); unreachable against every kernel here
    ('feed-slotpatch-rest-gen', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "delta", "slot": "feed", "base": 0, "rev": 1}], (GEN2, 0), (GEN, 1)),  # rest.gen: the pair re-seeded under the patch's own gen at rev 0
    ('feed-slotpatch-empty-rest', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "delta", "slot": "feed", "base": 0, "rev": 1}], (GEN, 0), (GEN, 1)),  # an empty rest: the receiver's feed base's gen, the rev reset to 0
    ('feed-slotpatch-restall', 'feed', [{"t": "feed", "slot": "", "gen": GEN, "genKey": True}, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}, {"t": "delta", "slot": "feed", "base": 0, "rev": 1}], None, (GEN, 1)),  # restAll with a rest carrying no gen: the reassembled frame carries none, the pair CLEARED
]


def _ts_code(src):
    """The TypeScript source with its comments blanked (spaces, so offsets and line numbers hold) and its string and template
    literals left as they are: a character walk that tracks the string state, so a `//` inside a string is not a comment. The
    censuses below count tokens (`feedHeld`, `throw`, `return`) in CODE, and a comment naming one is not a site."""
    out = list(src)
    i, n = 0, len(src)
    while i < n:
        ch = src[i]
        if ch in "\"'`":
            q = ch
            i += 1
            while i < n and src[i] != q:
                if src[i] == "\\":
                    i += 1
                i += 1
            i += 1
        elif src.startswith("//", i):
            j = src.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if src[k] != "\n":
                    out[k] = " "
            i = j
        else:
            i += 1
    return "".join(out)


def _feed_held_tokens(fed):
    """Every `feedHeld` token in federation.ts's code, classified by the PROPERTY of its site: the declaration (`feedHeld?:`),
    a member WRITE (`<receiver>.feedHeld` followed by an assignment operator, plain or compound, or preceded by `delete`), a
    member READ (any other `<receiver>.feedHeld`), else OTHER (an object key, a quoted name, a destructuring pattern). A write
    is (line, receiver, the assigned expression up to the semicolon)."""
    code = _ts_code(fed)
    out = {"declaration": [], "write": [], "read": [], "other": []}
    for m in re.finditer(r"feedHeld", code):
        line = code.count("\n", 0, m.start()) + 1
        before = code[m.start() - 1:m.start()]
        tail = code[m.end():]
        if before == ".":
            head = code[code.rfind("\n", 0, m.start()) + 1:m.start()]
            recv = re.search(r"([\w$]+)\.$", head)
            if re.search(r"\bdelete\s+[\w$.\[\]]+\.$", head):
                out["write"].append((line, recv.group(1) if recv else "?", "delete"))
            elif re.match(r"\s*(=(?!=)|\+=|-=|\|\|=|\?\?=|&&=)", tail):
                out["write"].append((line, recv.group(1) if recv else "?", code[m.end():code.find(";", m.end())].strip().lstrip("=").strip()))
            else:
                out["read"].append(line)
        elif re.match(r"\s*\?:", tail):
            out["declaration"].append(line)
        else:
            out["other"].append((line, before, tail[:24]))
    return out


def _throw_forms(code):
    """Every `throw` statement in a comment-stripped region, by form: `new Error(`, `new Unkeyable(`, the rethrow of a caught
    `e`, else OTHER (a TypeError, a thrown variable, anything a spelling-keyed count never saw)."""
    forms = []
    for t in re.finditer(r"\bthrow\b\s*([^;]*);", code):
        f = t.group(1).strip()
        forms.append("new Error(" if f.startswith("new Error(") else "new Unkeyable(" if f.startswith("new Unkeyable(") else "rethrow e" if f == "e" else "OTHER: " + f)
    return forms


class HeldPairRule(unittest.TestCase):
    """The drive-derived expectation's rule, pinned on synthetic frame records (no kernel): the labs above run against kernels
    whose frames carry no gen, so the stamped arms of held_pair, expected_relay_caps and assert_relay_dials are exercised
    here alone until a kernel stamps its frames."""

    def test_a_full_carrying_gen_leaves_gen_0_and_a_gen_less_full_clears_the_pair(self):
        self.assertEqual(held_pair([{"t": "feed", "gen": GEN}], "feed"), (GEN, 0))
        self.assertIsNone(held_pair([{"t": "feed"}], "feed"), "a kernel before the stamp: no pair")
        self.assertIsNone(held_pair([{"t": "feed", "gen": GEN}, {"t": "feed"}], "feed"), "a gen-less full after a stamped one clears the pair (a rollback)")
        self.assertIsNone(held_pair([], "feed"))

    def test_the_gens_form_is_the_kernels_string_and_anything_else_reads_as_no_stamp(self):
        # the client's genOf (view-deltas.ts): a non-empty string of at most GEN_MAX characters holding neither '.' nor ','; a
        # number, an empty string, a bool, a string carrying either separator or one over the cap is no stamp, so the full leaves
        # no pair (and the hook's record of it is dropped); a gen at the cap is a stamp (round 3, 2026-09-20)
        over_cap = GEN_STAMP + "-" + "9" * (GEN_MAX - len(GEN_STAMP))
        self.assertEqual(len(over_cap), GEN_MAX + 1)
        for bad in (7, 0, "", GEN_STAMP + ".7", GEN_STAMP + ",7", True, None, over_cap):
            self.assertIsNone(held_pair([{"t": "feed", "gen": bad}], "feed"), repr(bad))
            self.assertIsNone(_stamp_field({"gen": bad}, "gen"), repr(bad))
        self.assertEqual(held_pair([{"t": "feed", "gen": GEN}], "feed"), (GEN, 0))
        at_cap = over_cap[:-1]
        self.assertEqual(held_pair([{"t": "feed", "gen": at_cap}], "feed"), (at_cap, 0), "at the cap: a stamp")
        self.assertEqual(_stamp_field({"rev": 3}, "rev"), 3)
        for bad in ("3", -1, True, None):
            self.assertIsNone(_stamp_field({"rev": bad}, "rev"), "a rev is a non-negative int: %r" % (bad,))

    def test_the_length_cap_is_the_clients_own_declaration_and_counts_as_the_client_counts(self):
        # the mirror's cap is read from view-deltas.ts, never a second literal (round 3, the fixer's pass): the declaration is
        # found (an empty read fails, never passes) and the module's GEN_MAX is its value; and the count is String.length's,
        # UTF-16 code units, so a gen of GEN_MAX // 2 + 1 characters outside the Basic Multilingual Plane (GEN_MAX + 2 units)
        # is over the cap where Python's len would read it under, and GEN_MAX // 2 of them (GEN_MAX units) is at the cap
        src = open(os.path.join(ROOT, "ui", "webview", "view-deltas.ts"), encoding="utf-8").read()
        m = re.search(r"^export const GEN_MAX = (\d+);", src, re.M)
        self.assertIsNotNone(m, "the client's declaration was not found")
        self.assertEqual(GEN_MAX, int(m.group(1)))
        self.assertEqual(GEN_MAX, client_gen_max())
        wide = "\U0001F600"
        self.assertEqual((len(wide), _utf16_len(wide)), (1, 2))
        over = wide * (GEN_MAX // 2 + 1)
        self.assertLessEqual(len(over), GEN_MAX, "under the cap as len() counts")
        self.assertIsNone(_stamp_field({"gen": over}, "gen"), "over the cap as the client counts: no stamp")
        self.assertIsNone(held_pair([{"t": "feed", "gen": over}], "feed"))
        at = wide * (GEN_MAX // 2)
        self.assertEqual(_utf16_len(at), GEN_MAX)
        self.assertEqual(_stamp_field({"gen": at}, "gen"), at, "at the cap in the client's units: a stamp")

    def test_a_present_gen_or_newGen_the_client_cannot_read_is_a_refusal_and_never_reads_as_absent(self):
        # unparseable is not absent (round 4, 2026-09-20): a delta carrying a gen key whose value the client cannot read
        # (_stamp_field None, the key present: genOf refuses it) onto a held pair is REFUSED by both roads, never read as a
        # gen-less delta; on the feed road the pair stands (needFullFeed with the held pair, nothing applied), on the bars
        # road the base is dropped (needSlot), so nothing is held until the next whole frame. The same for a composed frame
        # whose gen matched but whose newGen the client cannot read: the pair never advances under the old gen.
        over_cap = GEN_STAMP + "-" + "9" * (GEN_MAX - len(GEN_STAMP))
        held = [{"t": "feed", "gen": GEN}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1}]
        for bad in (over_cap, GEN_STAMP + ".8", GEN_STAMP + ",8", 8, "", True):
            self.assertEqual(held_pair(held + [{"t": "feedDelta", "gen": bad, "base": 1, "rev": 2, "through": 2}], "feed"), (GEN, 1),
                             "feed: refused, the pair stands: %r" % (bad,))
            self.assertEqual(held_pair(held + [{"t": "feedDelta", "gen": GEN, "newGen": bad, "base": 1, "rev": 4, "through": 4}], "feed"), (GEN, 1),
                             "feed: an unreadable newGen on a matched frame is refused, the pair never (gen, 4): %r" % (bad,))
            bars = [{"t": "bars", "gen": GEN3}, {"t": "delta", "slot": "bars", "gen": GEN3, "base": 0, "rev": 1, "through": 1}]
            self.assertIsNone(held_pair(bars + [{"t": "delta", "slot": "bars", "gen": bad, "base": 1, "rev": 2, "through": 2}], "bars"),
                              "bars: recovered, the base dropped: %r" % (bad,))
            self.assertIsNone(held_pair(bars + [{"t": "delta", "slot": "bars", "gen": GEN3, "newGen": bad, "base": 1, "rev": 4, "through": 4}], "bars"),
                              "bars: an unreadable newGen on a matched frame recovers, the base dropped: %r" % (bad,))
            # a hook that dropped the unreadable value and noted the key (the relay-redial consumer's _record) reads the same
            self.assertEqual(held_pair(held + [{"t": "feedDelta", "genKey": True, "base": 1, "rev": 2, "through": 2}], "feed"), (GEN, 1))
            self.assertIsNone(held_pair(bars + [{"t": "delta", "slot": "bars", "genKey": True, "base": 1, "rev": 2, "through": 2}], "bars"))
            self.assertEqual(held_pair(held + [{"t": "feedDelta", "gen": GEN, "newGenKey": True, "base": 1, "rev": 4, "through": 4}], "feed"), (GEN, 1))
        # a whole frame carrying an unreadable gen seeds no pair on either road, as before (the full arm is not a gate)
        self.assertIsNone(held_pair([{"t": "feed", "gen": over_cap}], "feed"))
        self.assertIsNone(held_pair([{"t": "bars", "gen": over_cap}], "bars"))
        # and after the drop the next whole frame re-seeds
        bars = [{"t": "bars", "gen": GEN3}, {"t": "delta", "slot": "bars", "gen": over_cap, "base": 0, "rev": 1, "through": 1}, {"t": "bars", "gen": GEN2}]
        self.assertEqual(held_pair(bars, "bars"), (GEN2, 0))
        for k in ("gen", "newGen"):
            self.assertTrue(_stamp_present({k: over_cap}, k) and _stamp_present({k + "Key": True}, k), k)
            self.assertFalse(_stamp_present({"base": 1}, k), k)

    def test_a_stamped_delta_advances_the_pair_and_a_gen_less_one_moves_no_feed_pair(self):
        frames = [{"t": "feed", "gen": GEN}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1}]
        self.assertEqual(held_pair(frames, "feed"), (GEN, 1), "a per-cycle stamped delta: (gen, rev)")
        self.assertEqual(held_pair([{"t": "feed", "gen": GEN}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1}], "feed"), (GEN, 0),
                         "a stamped delta carrying no through is refused by the client and moves nothing: every stamped delta carries through")
        frames.append({"t": "feedDelta", "gen": GEN, "newGen": GEN2, "base": 1, "rev": 4, "through": 4})
        self.assertEqual(held_pair(frames, "feed"), (GEN2, 4), "a composed frame: (newGen, through)")
        frames.append({"t": "feedDelta", "base": 4, "rev": 5})
        self.assertEqual(held_pair(frames, "feed"), (GEN2, 4), "a gen-less delta moves no feed pair (the bars slot differs: the test below)")
        self.assertIsNone(held_pair([{"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1}], "feed"), "a delta before any full: nothing held")

    def test_a_gen_less_delta_moves_no_feed_pair_and_advances_the_bars_pairs_rev_under_the_held_gen(self):
        # the roads differ on a gen-less delta onto a held pair, and the difference was measured at both clients (round 4, the
        # mirror measured, 2026-09-20; held_pair's docstring carries the two probes' readings): the feed road writes its pair
        # under a gen alone (the vintage guard), the bars road's pair is its base, whose rev every applied frame moves, so
        # ViewDeltas.held reads (the held gen, the frame's rev) after one; a newGen on a gen-less frame is adopted on neither
        # road, since the gate never ran for it. Before the measurement this rule read "moves no pair" for both slots.
        feed = [{"t": "feed", "gen": GEN}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1}]
        self.assertEqual(held_pair(feed + [{"t": "feedDelta", "base": 1, "rev": 2}], "feed"), (GEN, 1), "feed: a gen-less delta moves no pair")
        self.assertEqual(held_pair(feed + [{"t": "feedDelta", "newGen": GEN2, "base": 1, "rev": 2, "through": 2}], "feed"), (GEN, 1), "feed: nor does one carrying newGen and through")
        bars = [{"t": "bars", "gen": GEN3}, {"t": "delta", "slot": "bars", "gen": GEN3, "base": 0, "rev": 1, "through": 1}]
        self.assertEqual(held_pair(bars + [{"t": "delta", "slot": "bars", "base": 1, "rev": 2}], "bars"), (GEN3, 2), "bars: the rev advances under the held gen")
        self.assertEqual(held_pair(bars + [{"t": "delta", "slot": "bars", "base": 1, "rev": 2, "through": 2}], "bars"), (GEN3, 2), "bars: the same with through")
        self.assertEqual(held_pair(bars + [{"t": "delta", "slot": "bars", "newGen": GEN2, "base": 1, "rev": 2, "through": 2}], "bars"), (GEN3, 2), "bars: a newGen on a gen-less frame is not adopted")
        self.assertEqual(held_pair([{"t": "bars", "gen": GEN3}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], "bars"), (GEN3, 1), "bars: straight after the full, the probe's shape")
        # onto a base seeded without a gen: no pair on either road, before and after (both probes read null and None)
        self.assertIsNone(held_pair([{"t": "bars"}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}], "bars"))
        self.assertIsNone(held_pair([{"t": "feed"}, {"t": "feedDelta", "base": 0, "rev": 1}], "feed"))
        # and the redial then declares the pair the bars base holds, rev 1 under the full's gen
        self.assertEqual(expected_relay_caps([{"t": "bars", "gen": GEN3}, {"t": "delta", "slot": "bars", "base": 0, "rev": 1}]), "feedDelta,held:bars:%s.1" % GEN3)

    def test_a_per_cycle_stamped_delta_carrying_through_equal_to_its_rev_leaves_gen_rev(self):
        # the stamping kernel's per-cycle shape: every delta carries gen, base, rev AND through, through equal to rev and no
        # newGen; through's presence does not make it a composed frame, and the pair is (gen, through), through equal to rev
        frames = [{"t": "feed", "gen": GEN}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1}]
        self.assertEqual(held_pair(frames, "feed"), (GEN, 1))
        frames.append({"t": "feedDelta", "gen": GEN, "base": 1, "rev": 2, "through": 2})
        self.assertEqual(held_pair(frames, "feed"), (GEN, 2))
        bars = [{"t": "bars", "gen": GEN3}, {"t": "delta", "slot": "bars", "gen": GEN3, "base": 0, "rev": 1, "through": 1}]
        self.assertEqual(held_pair(bars, "bars"), (GEN3, 1))

    def test_the_bars_slot_reads_bars_fulls_and_bars_patches_alone(self):
        frames = [{"t": "bars", "gen": GEN3}, {"t": "delta", "slot": "bars", "gen": GEN3, "base": 0, "rev": 1, "through": 1},
                  {"t": "delta", "slot": "lanes", "gen": GEN3, "base": 1, "rev": 2, "through": 2}, {"t": "feed", "gen": GEN}]
        self.assertEqual(held_pair(frames, "bars"), (GEN3, 1), "another slot's patch and the feed full do not move the bars pair")
        self.assertEqual(held_pair(frames, "feed"), (GEN, 0))
        # a slot the receiver DOES decode (the maintainer's round 5, extra7-1: the lanes sample above pins a slot no table has): a
        # delta slot:feed patch moves neither pair HERE, the mirror's reading; the client's feed arm re-seeds the feed pair from the
        # frame the receiver reassembles, the acceptance the docstring names and RECEIVER_BLIND's feed-slotpatch rows hold
        frames.append({"t": "delta", "slot": "feed", "gen": GEN3, "base": 0, "rev": 1, "through": 1})
        self.assertEqual(held_pair(frames, "bars"), (GEN3, 1), "a feed slot patch does not move the bars pair")
        self.assertEqual(held_pair(frames, "feed"), (GEN, 0), "nor the feed pair in this rule (the client re-seeds: the acceptance class)")

    def test_drive_pair_skips_on_no_gen_key_and_fails_on_an_unparsed_one(self):
        # the labs' skip-and-branch read: None only when no recorded frame carried a gen key (the leg skips or takes the undeclared
        # arm); a gen key present with a pair parsed is that pair; a gen key present and no pair parsed (a gen the client reads
        # as none, which a hook's record drops) fails, never "undeclared"
        self.assertIsNone(drive_pair(self, [{"t": "feed"}], "feed"), "no gen key on any frame: a kernel before the stamp")
        self.assertIsNone(drive_pair(self, [{"t": "feed"}, {"t": "caps"}, {"t": "feedDelta", "base": 0, "rev": 1}], "feed"))
        self.assertEqual(drive_pair(self, [{"t": "feed", "gen": GEN, "genKey": True}], "feed"), (GEN, 0))
        with self.assertRaises(AssertionError):
            drive_pair(self, [{"t": "feed", "gen": GEN_STAMP + ".7", "genKey": True}], "feed")   # the key with a gen genOf refuses
        with self.assertRaises(AssertionError):
            drive_pair(self, [{"t": "feed", "genKey": True}], "feed")   # the same frame as a hook records it: the value dropped, the key noted
        with self.assertRaises(AssertionError):
            drive_pair(self, [{"t": "feed", "gen": GEN, "genKey": True}, {"t": "feed"}], "feed")   # a stamped full then a gen-less one
        # the third failing shape (peer read, 2026-09-19): the key rode a frame the rule reads no pair from while the full carried
        # none, a stamped delta onto no held pair or a frame of another type; the verdict is the same fail, never "undeclared"
        with self.assertRaises(AssertionError):
            drive_pair(self, [{"t": "feed"}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1, "genKey": True}], "feed")
        with self.assertRaises(AssertionError):
            drive_pair(self, [{"t": "feed"}, {"t": "caps", "genKey": True}], "feed")

    def test_composed_frames_are_the_deltas_carrying_newGen(self):
        # a per-cycle K2 delta carries through and no newGen, so through never tells a composed frame; a newGen the client reads as
        # none (a '.' in it) is no composed frame either
        per_cycle = {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1}
        composed = {"t": "feedDelta", "gen": GEN, "newGen": GEN2, "base": 1, "rev": 4, "through": 4}
        bad = {"t": "feedDelta", "gen": GEN, "newGen": GEN_STAMP + ".9", "base": 4, "rev": 5, "through": 5}
        self.assertEqual(composed_frames([{"t": "feed", "gen": GEN}, per_cycle], "feed"), [], "through and no newGen: not composed")
        self.assertEqual(composed_frames([{"t": "feed", "gen": GEN}, per_cycle, composed, bad], "feed"), [composed])
        bars = {"t": "delta", "slot": "bars", "gen": GEN3, "newGen": GEN2, "base": 0, "rev": 2, "through": 2}
        self.assertEqual(composed_frames([{"t": "bars", "gen": GEN3}, bars, composed], "bars"), [bars], "the bars slot reads bars patches alone")
        self.assertEqual(composed_frames([], "feed"), [])

    def test_expected_relay_caps_is_the_decoder_word_plus_each_held_member_and_fails_on_an_empty_drive(self):
        self.assertEqual(expected_relay_caps(None), "feedDelta", "a first dial: no socket before it")
        self.assertEqual(expected_relay_caps([{"t": "feed"}, {"t": "caps"}]), "feedDelta", "a redial after gen-less frames: undeclared")
        self.assertEqual(expected_relay_caps([{"t": "feed", "gen": GEN}, {"t": "feedDelta", "gen": GEN, "base": 0, "rev": 2, "through": 2}]), "feedDelta,held:feed:%s.2" % GEN)
        self.assertEqual(expected_relay_caps([{"t": "bars", "gen": GEN3}]), "feedDelta,held:bars:%s.0" % GEN3)
        self.assertEqual(expected_relay_caps([{"t": "feed", "gen": GEN}, {"t": "bars", "gen": GEN3}]), "feedDelta,held:feed:%s.0,held:bars:%s.0" % (GEN, GEN3), "both, feed first")
        with self.assertRaises(AssertionError):
            expected_relay_caps([])   # a redial none of whose earlier sockets recorded a frame: no drive

    def test_assert_relay_dials_derives_a_later_redials_member_from_every_earlier_socket_of_the_host(self):
        # the client keeps a base holding a gen across a redial, so socket 2's composed frame applies onto what socket 1 left and
        # the THIRD dial declares (newGen, through), the pair the whole stream left; read from socket 2's frames alone it would
        # be nothing (a composed frame onto no full), a false red on a correct client
        relay = "ws://hub.local:1/remote/TESTHOST/ws?app=feed&delta=1&caps="
        dials = ["ws://hub.local:1/ws?app=feed&delta=1", relay + "feedDelta",
                 relay + quote("feedDelta,held:feed:%s.1" % GEN, safe=""), relay + quote("feedDelta,held:feed:%s.4" % GEN2, safe="")]
        frames = [{"sock": 1, "t": "feed", "gen": GEN}, {"sock": 1, "t": "feedDelta", "gen": GEN, "base": 0, "rev": 1, "through": 1},
                  {"sock": 2, "t": "caps"}, {"sock": 2, "t": "feedDelta", "gen": GEN, "newGen": GEN2, "base": 1, "rev": 4, "through": 4}]
        self.assertEqual([i for i, _h, _u in assert_relay_dials(self, "feed", dials, frames)], [1, 2, 3])
        # the middle socket recorded nothing (it dropped before a frame): the pair socket 1 left stands, the base kept across
        # the redial, so the third dial declares it and the drive is not empty
        assert_relay_dials(self, "feed", dials[:3] + [dials[2]], [f for f in frames if f["sock"] == 1])
        # a third dial declaring only what socket 1 left where socket 2 composed onward is the wrong term
        with self.assertRaises(AssertionError):
            assert_relay_dials(self, "feed", dials[:3] + [dials[2]], frames)
        # an empty drive: no frame on ANY earlier socket of the host
        with self.assertRaises(AssertionError):
            assert_relay_dials(self, "feed", dials[:3], [])

    def test_every_refusal_point_of_both_receivers_is_mirrored_one_probe_shape_each(self):
        # the shape instruction (the maintainer's round 4, ROUND 5): the client's FULL refusal set, not the shapes changed. One
        # row per refusal point of view-deltas.ts receive (the unknown slot, no base, the exact base, the gen gate, the newGen
        # test, the rev relation) and of applyRemoteFeedDelta (nobase, then the ladder's nine words in gate order), plus the
        # applying shapes on each road and the shapes the round measured; every row's expectation is the client's own reading
        # in the probe. Red at the head before the pass on 28 of these rows (the bars exact-base and rev-relation classes, a
        # foreign readable gen adopted on both roads, the feed gate's base, ahead, through, behind, rev and disagree words, a
        # rev past 2^53, the through-less stamped delta on the bars road).
        self.assertGreaterEqual(len(RECEIVER_CASES), 60, "the table is the probe's, not a sample")
        for cid, slot, frames, expected, _ in RECEIVER_CASES:
            self.assertEqual(held_pair(frames, slot), expected, "%s: the client held %r" % (cid, expected))
        self.assertEqual({slot for _, slot, _, _, _ in RECEIVER_CASES}, {"bars", "feed"}, "both roads")

    def test_the_recorder_blind_class_is_named_and_reads_as_the_docstring_says(self):
        # what the rule does not read, in two kinds (the docstring's bound). REFUSALS on content a recorder does not keep, three
        # classes sharing one property, that each leaves this rule AHEAD of the client (expected_relay_caps over-demands in every
        # one), and differing in what the client does next: the bars receiver's content checks on a patch and a rev field of a
        # type the hooks do not copy (the client drops the base and re-seeds at the next keyable whole frame); the bars receiver's
        # refusal of a whole frame it cannot key (the client holds no pair, re-seeds at the next keyable whole frame; this rule
        # reads the recorded full as a seed); the feed road's applyFeedDelta throws (the client's pair STANDS, it asks once, bare,
        # then stops after the answering full: round 5's bounded refusal; the divergence persists across the refused frames). And
        # one ACCEPTANCE (the maintainer's round 5, extra7-1): a delta slot:feed patch the receiver reassembles into a feed frame
        # that re-seeds the feed pair, from content or from the recorded full's gen at rev 0, where this rule reads no delta on
        # the feed slot. This pins each measured reading so no divergence is silent, and the class per row by its shape.
        self.assertGreaterEqual(len(RECEIVER_BLIND), 24)
        for cid, slot, frames, client, mirror in RECEIVER_BLIND:
            self.assertEqual(held_pair(frames, slot), mirror, "%s: the recorder-blind reading" % cid)
            self.assertNotEqual(client, mirror, "%s: a row here is a measured divergence" % cid)
            self.assertIsNotNone(mirror, cid)
            if slot == "bars":
                self.assertIsNone(client, "%s: on the bars road the client drops the base (or seeds none), and holds no pair" % cid)
            elif cid.startswith("feed-slotpatch-"):
                # the acceptance: the recorded patch is a delta on the feed slot, which this rule skips, so the mirror holds the
                # pair the deltas before it left; the client's reading is a re-seed at rev 0 under some gen, or nothing
                self.assertEqual(frames[-1]["t"], "delta"); self.assertEqual(frames[-1]["slot"], "feed")
                self.assertEqual(mirror, held_pair(frames[:-1], slot), "%s: this rule reads no delta frame on the feed slot" % cid)
                self.assertTrue(client is None or client[1] == 0, "%s: the client re-seeds the pair at rev 0 (or clears it) from the reassembled frame" % cid)
            else:
                self.assertEqual(client, held_pair(frames[:-1], slot), "%s: on the feed road the client's pair stands as it was before the frame (the throw is caught and refused before Conn.feedHeld is written)" % cid)
        ids = [r[0] for r in RECEIVER_BLIND]
        self.assertIn("bars-through-string", ids, "the one rev-field divergence, a through the hook does not copy")
        self.assertIn("bars-rest-restall-type-dropped", ids, "the frame-type throw (view-deltas.ts:260), enumerated and probed")
        self.assertEqual(len([i for i in ids if i.startswith("bars-full-unkeyable")]), 6, "the full path: the four Unkeyable shapes, the drop of a held pair, the delta after")
        self.assertEqual(len([i for i in ids if i.startswith("feed-apply-throw")]), 4, "the feed road's four measured throws")
        self.assertEqual(sorted((r[3] for r in RECEIVER_BLIND if r[0].startswith("feed-slotpatch-")), key=repr), sorted([(GEN2, 0), (GEN, 0), None], key=repr), "the acceptance's three measured re-seeds: rest.gen, the base's gen, cleared")

    def test_the_receivers_refusal_sites_are_counted_so_a_new_one_reds_until_classified(self):
        # the census form space: the refusal points the table above enumerates are read off the receivers' sources, so a
        # receiver that grows a refusal site fails here until a row classifies it (modelled, or recorder-blind)
        vd = open(os.path.join(ROOT, "ui", "webview", "view-deltas.ts"), encoding="utf-8").read()
        m = re.search(r"^  receive\(msg: any\): any \{\n(.*?)^  \}\n", vd, re.S | re.M)
        self.assertIsNotNone(m, "view-deltas.ts receive() was not found: re-aim this census")
        body = m.group(1)
        self.assertEqual(body.count("this.recover("), 6, "receive's recover sites: the unknown slot, no base, the exact base, the gen gate, the newGen test, the catch (each modelled above but the catch's content class)")
        self.assertEqual(body.count("throw new Error("), 7, "receive's throws inside the try: the rev relation and coll object test (modelled for the stamp fields), the remainder, a collection in it, the frame type, an unknown collection, a set, the order (recorder-blind)")
        # the refusal SITES over the whole module, by construction and never by message (the maintainer's round 5, extra8-1: the
        # census read receive's body and matched two helper throws by their text, so a throw added to split() or any helper was
        # invisible to it): every `throw new Error(` in view-deltas.ts is counted, and the per-region counts beside the total say
        # which function each is reached from (receive's own; split's unsupported kind, a programming error and no wire shape;
        # assemble's lane throw and stringKeys' key-list throw, both helpers called inside receive's try, so class 1); a throw
        # added anywhere in the module moves the total and reds here until a row classifies it
        def region(name):
            # a top-level function: from its `function <name>(` line to the first `}` at column 0 (the method bodies above close at two spaces)
            m_ = re.search(r"^function %s\(.*?\n(.*?)^\}\n" % re.escape(name), vd, re.S | re.M)
            self.assertIsNotNone(m_, "view-deltas.ts %s was not found: re-aim this census" % name)
            return m_.group(1)
        regions = {"receive": body, "split": region("split"), "assemble": region("assemble"), "stringKeys": region("stringKeys")}
        per_region = {k: v.count("throw new Error(") for k, v in regions.items()}
        self.assertEqual(per_region, {"receive": 7, "split": 1, "assemble": 1, "stringKeys": 1}, "the throw sites by function")
        self.assertEqual(vd.count("throw new Error("), sum(per_region.values()), "every `throw new Error(` in the module is in one of the four regions: a throw elsewhere reds here until classified")
        self.assertEqual(vd.count("throw new Unkeyable("), sum(v.count("throw new Unkeyable(") for v in regions.values()), "and every Unkeyable throw")
        self.assertEqual(regions["stringKeys"].count("throw new Error("), 1, "stringKeys' one throw (an invalid key list), reached from receive for del and order (recorder-blind, class 1)")
        self.assertEqual(regions["assemble"].count("throw new Error("), 1, "assemble's one throw (a lane holding both scalar and item entries), reached from receive inside its try (recorder-blind, class 1)")
        # the PROPERTY beside the spellings (the author's fixer pass after round 5, refusal-2: the counts above read two
        # constructor spellings, so a `throw new TypeError(` or a thrown variable planted in split() left them green): every
        # `throw` statement in the module's CODE (comments blanked: a comment naming a throw is not a site), per region and by
        # form, the rethrow of the full arm's caught `e` classified with the two constructors, any other form unclassified and
        # red; the module total is the regions' sum, so a throw outside the four regions reds too
        code_regions = {k: _ts_code(v) for k, v in regions.items()}
        forms = {k: _throw_forms(v) for k, v in code_regions.items()}
        self.assertEqual({k: [f for f in v if f.startswith("OTHER")] for k, v in forms.items()}, {k: [] for k in forms}, "a throw in a form this census does not classify (not new Error(, new Unkeyable( or the rethrow of e): classify it, then the row")
        self.assertEqual({k: len(v) for k, v in forms.items()}, {"receive": 8, "split": 3, "assemble": 1, "stringKeys": 1}, "every throw statement by region, whatever its form: receive's seven Errors and the full arm's rethrow; split's Error and two Unkeyables; assemble's and stringKeys' one each: %r" % (forms,))
        self.assertEqual(forms["receive"].count("rethrow e"), 1, "receive's one rethrow (the full arm passes every error but Unkeyable on)")
        self.assertEqual(len(re.findall(r"\bthrow\b", _ts_code(vd))), sum(len(v) for v in forms.values()), "every throw in view-deltas.ts's code is in one of the four regions")
        # the full path (the docstring's class 2): split()'s Unkeyable throws and the full arm's catch that deletes the base and
        # returns the frame whole, neither a recover call nor a throw inside the try, so the counts above cannot see it
        self.assertEqual(vd.count("throw new Unkeyable("), 2, "split's two Unkeyable sites: a container the kind cannot key, a lane holding the separator (the full arm refuses the whole frame as a base on either: recorder-blind, the bars-full-unkeyable rows)")
        self.assertEqual(body.count("if (!(e instanceof Unkeyable)) throw e;"), 1, "the full arm's catch tells Unkeyable from every other error")
        self.assertEqual(body.count("this.bases.delete(full);"), 1, "and drops the base for it: the one refusal of a WHOLE frame, outside the try (recorder-blind)")
        fed = open(os.path.join(ROOT, "ui", "webview", "federation.ts"), encoding="utf-8").read()
        m2 = re.search(r"^  private applyRemoteFeedDelta\(host: string, d: any\): void \{\n(.*?)^  \}\n", fed, re.S | re.M)
        self.assertIsNotNone(m2, "federation.ts applyRemoteFeedDelta was not found: re-aim this census")
        self.assertEqual(m2.group(1).count('"needFullFeed"'), 3, "the feed road's two stamp-and-base refusal sites: nobase (a bare ask) and the gate (the ask with the held pair, or bare when none is held)")
        self.assertEqual(m2.group(1).count("this.diag("), 2, "the two rows those refusals file: feedDelta-nobase and feedDelta-stale (its words are stale_why_words()'s derivation)")
        # the feed road's content refusals (class 3): applyFeedDelta's throws. Since the maintainer's round 5 (refusals-2) the throw
        # is CAUGHT, in feed-delta.ts's tryApplyFeedDelta (the one wrapper both roads call, so both are covered by construction),
        # and each road refuses it with its own recovery and bound (refuseRemoteApply, refuseLocalApply): the pair still stands
        # (nothing was written), one bare needFullFeed goes per stall, and the asking stops after the answering full. A bare
        # applyFeedDelta call anywhere in federation.ts, a second catch, or a throw of the gate's own moves the reading and reds here
        self.assertEqual(m2.group(1).count("const r = tryApplyFeedDelta(raw, d);"), 1, "the checked apply, once, before the pair write")
        self.assertEqual(m2.group(1).count("if (!r.ok) { this.refuseRemoteApply(c, host, d, r.error); return; }"), 1, "a throw is the remote road's refusal, before any write")
        self.assertEqual(len(re.findall(r"[^A-Za-z]applyFeedDelta\(", fed)), 0, "federation.ts calls the bare apply nowhere (the local arm and the remote road both go through tryApplyFeedDelta)")
        self.assertEqual(fed.count("tryApplyFeedDelta("), 2, "the two roads, one call each: the local feedDelta arm and applyRemoteFeedDelta")
        self.assertEqual(m2.group(1).count("try"), 1, "one try in applyRemoteFeedDelta, and it is the checked apply's name (the catch itself is feed-delta.ts's)")
        self.assertEqual(m2.group(1).count("throw "), 0, "and the gate itself throws nothing: its refusals are the asks and the rows above")
        # the roads' EXITS by the property (refusal-2): every `return` in the comment-stripped body of applyRemoteFeedDelta is one
        # of the three refusals (nobase, the gate, the checked apply), each pinned by its statement, so a refusal that neither
        # asks nor files (an early return) reds here until classified; the same over the local feedDelta arm's four exits (the
        # remote hand-off, nobase, the checked apply, the end) and the two refusal helpers' one early return each
        remote_code = _ts_code(m2.group(1))
        self.assertEqual(len(re.findall(r"\breturn\b", remote_code)), 3, "applyRemoteFeedDelta's exits: nobase, the gate, the checked apply (a fourth is a refusal this census has not classified)")
        self.assertEqual(len(re.findall(r"\bthrow\b", remote_code)), 0, "and no throw in its code")
        self.assertRegex(remote_code, r'this\.sendRemote\(host, \{ type: "needFullFeed" \}\);\n\s*return;', "the nobase exit follows its bare ask")
        self.assertRegex(remote_code, r'this\.sendRemote\(host, held \? \{ type: "needFullFeed", gen: held\.gen, rev: held\.rev \} : \{ type: "needFullFeed" \}\);\n\s*return;', "the gate's exit follows its ask with the held pair")
        arm_m = re.search(r'^    if \(m && m\.type === "feedDelta"\) \{\n(.*?)\n    \}\n', fed, re.S | re.M)
        self.assertIsNotNone(arm_m, "federation.ts's feedDelta arm was not found: re-aim this census")
        arm_code = _ts_code(arm_m.group(1))
        self.assertEqual(len(re.findall(r"\breturn\b", arm_code)), 4, "the feedDelta arm's exits: the remote hand-off, the local nobase ask, the local checked apply, the end")
        self.assertRegex(arm_code, r'if \(host !== LOCAL\) \{ this\.applyRemoteFeedDelta\(host, msg\); return; \}', "the remote hand-off")
        self.assertRegex(arm_code, r'if \(typeof s === "function"\) s\(\{ type: "needFullFeed" \}\);\n\s*return;', "the local nobase exit follows its ask")
        self.assertRegex(arm_code, r'if \(!r\.ok\) \{ this\.refuseLocalApply\(m, r\.error\); return; \}', "the local checked apply's exit")
        self.assertEqual(len(re.findall(r"\bthrow\b", arm_code)), 0, "and no throw in the arm's code")
        m4 = re.search(r"^  private refuseRemoteApply\(c: Conn, host: string, d: any, error: unknown\): void \{\n(.*?)^  \}\n", fed, re.S | re.M)
        self.assertIsNotNone(m4, "federation.ts refuseRemoteApply was not found: re-aim this census")
        self.assertEqual(m4.group(1).count('"needFullFeed"'), 1, "the apply-throw refusal's one bare ask (never the held pair: the base's own content is a suspect)")
        self.assertEqual(m4.group(1).count("this.diag("), 1, "and its one row, feedDelta-apply")
        self.assertEqual(m4.group(1).count("this.tellShell("), 1, "and the visible message once the answering full did not repair the stream")
        m5 = re.search(r"^  private refuseLocalApply\(m: any, error: unknown\): void \{\n(.*?)^  \}\n", fed, re.S | re.M)
        self.assertIsNotNone(m5, "federation.ts refuseLocalApply was not found: re-aim this census")
        self.assertEqual(m5.group(1).count('"needFullFeed"'), 1, "the local twin's one bare ask, through the local send hook")
        self.assertEqual(m5.group(1).count("this.diag("), 1); self.assertEqual(m5.group(1).count("this.tellShell("), 1)
        for name, mm in (("refuseRemoteApply", m4), ("refuseLocalApply", m5)):
            self.assertEqual(len(re.findall(r"\breturn\b", _ts_code(mm.group(1)))), 1, "%s's one early return: the latch's asked and stopped states, nothing further" % name)
        fd = open(os.path.join(ROOT, "ui", "webview", "feed-delta.ts"), encoding="utf-8").read()
        self.assertEqual(fd.count("try"), 2, "feed-delta.ts: the checked apply's one try and its name (tryApplyFeedDelta); applyFeedDelta itself catches nothing")
        self.assertRegex(fd, r"export function tryApplyFeedDelta\(base: any, d: FeedDelta\)[^\n]*\{\n  try \{\n    return \{ ok: true, next: applyFeedDelta\(base, d\) \};\n  \} catch \(e\) \{\n    return \{ ok: false, error: e \};", "the wrapper's shape: the throw caught and returned, the base untouched")
        self.assertEqual(fd.count("upsertById("), 3, "the two upserts (asks by itemId, ledgers by sid) and the function: the throw-capable sites are their reads of an item's id, a null item, and the Set over the removals (the four feed-apply-throw rows)")
        m3 = re.search(r"^    ws\.onmessage = \(ev: MessageEvent\) => \{\n(.*?)^    \};\n", fed, re.S | re.M)
        self.assertIsNotNone(m3, "federation.ts ws.onmessage was not found: re-aim this census")
        self.assertRegex(m3.group(1), r"try \{\n\s*msg = JSON\.parse\(ev\.data\);\n\s*\} catch", "onmessage's one try wraps the parse alone")
        self.assertEqual(m3.group(1).count("try"), 1, "nothing else in onmessage catches: the apply's throw is caught below it, in feed-delta.ts, never folded into the parse's catch")

    def test_the_pair_writers_are_counted_so_a_new_one_reds_until_classified(self):
        # the census over the WRITERS of the pair (the maintainer's round 5, tests-4 and extra7-1: the census read the receivers'
        # refusals and nothing read the feed arm, where Conn.feedHeld is written from a whole frame, the site the mirror's own full
        # branch models): every write of Conn.feedHeld in federation.ts and every bases.set in view-deltas.ts, each site's
        # expression pinned with a loud miss, and the frame types that reach the feed arm, so a fifth writer or a new producer of
        # the arm's frame reds here until the rule's docstring classifies it
        fed = open(os.path.join(ROOT, "ui", "webview", "federation.ts"), encoding="utf-8").read()
        # every `feedHeld` token in the module's CODE, classified by the property of its site (the author's fixer pass after
        # round 5, refusal-1: the census read `c.feedHeld =` and `conn.feedHeld =`, two receiver spellings, so a fifth writer
        # through another variable name or an Object.assign left it green): the declaration once; a member write whatever the
        # receiver's name and the assignment's form (plain, compound, delete); a member read; any other form (an object key, a
        # quoted name, a destructuring) is unclassified and reds until a row classifies it
        tokens = _feed_held_tokens(fed)
        self.assertEqual(tokens["other"], [], "a feedHeld token in a form this census does not classify (not the declaration, a member read or a member write): a writer in a new spelling, red until classified")
        self.assertEqual(len(tokens["declaration"]), 1, "Conn.feedHeld is declared once: %r" % (tokens["declaration"],))
        self.assertGreaterEqual(len(tokens["read"]), 1, "the pair is read (the redial's caps compose it)")
        writes = [w[2] for w in tokens["write"]]
        self.assertEqual(len(writes), 4, "Conn.feedHeld's writers, whatever the receiver is called: the feed arm, applyRemoteFeedDelta, connect()'s gated reset, closeRemote: %r" % (tokens["write"],))
        self.assertEqual(sorted(set(w[1] for w in tokens["write"])), ["c", "conn"], "the receivers today (informational: a new name is a fifth write above before it is a name here)")
        self.assertEqual(writes.count("undefined"), 2, "two are clears (connect()'s gated reset and closeRemote), the conn's life and not a frame's")
        content = [w for w in writes if w != "undefined"]
        self.assertEqual(len(content), 2, "two write the pair from a frame: %r" % (content,))
        self.assertIn("g !== undefined ? { gen: g, rev: 0 } : undefined", content, "the feed arm: the full's gen through genOf, rev 0, or cleared (the mirror's full branch)")
        self.assertIn("{ gen: newGen !== undefined ? newGen : gen, rev: d.rev }", content, "applyRemoteFeedDelta: newGen when carried else the gate's gen, at the frame's rev (the mirror's feedDelta branch)")
        arm = re.search(r'^    if \(m && m\.type === "feed"\) \{\n(.*?)^      return;\n    \}\n', fed, re.S | re.M)
        self.assertIsNotNone(arm, "federation.ts's feed arm was not found: re-aim this census")
        self.assertEqual(arm.group(1).count("c.feedHeld = "), 1, "the feed arm's one pair write, from genOf(msg.gen)")
        self.assertIn("const g = genOf(msg.gen);", arm.group(1))
        # the frame the arm stores may be the receiver's product: every remote frame passes receive() first, and the receiver's
        # slot table admits feed, so a delta slot:feed patch reassembles into a feed frame that enters this arm (the acceptance)
        self.assertEqual(fed.count("msg = vd.receive(msg);"), 1, "every remote frame passes the conn's receiver before the arms")
        self.assertLess(fed.index("msg = vd.receive(msg);"), fed.index('if (m && m.type === "feed") {'), "and before the feed arm reads it")
        vd = open(os.path.join(ROOT, "ui", "webview", "view-deltas.ts"), encoding="utf-8").read()
        self.assertRegex(vd, r'const slotOf = \(s: any\): Slot \| null => s === "feed" \|\| s === "bars" \? s : null;', "the receiver decodes the feed slot (a kernel too old to read the caps term serves the feed there)")
        sets = re.findall(r"this\.bases\.set\((\w+), \{ rev: (.*?), (gen(?:: [^,]+)?), msg", vd)   # the patch's write spells gen as a shorthand property
        self.assertEqual(sorted(sets), sorted([("full", "0", "gen: genOf(msg.gen)"), ("slot", "msg.rev", "gen")]), "the bars pair's two writers: the full's seed (the frame's gen through genOf) and the patch's advance (the gen the gate derived: newGen when carried under a matched gen, else the base's): %r" % (sets,))
        self.assertEqual(vd.count("this.bases.set("), 2, "and no other bases.set")


class FrameRecorderCensus(unittest.TestCase):
    """Every frame recorder that feeds held_pair sets both presence flags (the maintainer's round 4, tests-2 and regression-2:
    two of the five recorders set neither, so _stamp_present was False for every frame of two labs and a gen of null, a
    boolean, an object or a list, which the hooks copy no value for, read there as a gen-less frame). The population is
    DERIVED: every tests/*.py that reaches held_pair (calls one of its readers: held_pair, drive_pair, expected_relay_caps or
    assert_relay_dials; a module that only imports this one for its other helpers, as the bars-delta lab does, feeds nothing)
    and records frames (a JS hook pushing onto window.__frames, or a Python _record), each recorder found by its push or its
    def; a recorder found without the two lines fails, and an empty derivation fails (a census that found nothing checked
    nothing)."""

    JS_PUSH = re.compile(r"window\.__frames\.push\((\w+)\);")
    READER = re.compile(r"\b(?:held_pair|drive_pair|expected_relay_caps|assert_relay_dials)\(")

    def recorders(self):
        found = []
        for name in sorted(os.listdir(HERE)):
            if not (name.startswith("test_") and name.endswith(".py")):
                continue
            src = open(os.path.join(HERE, name), encoding="utf-8").read()
            if not self.READER.search(src):
                continue   # records frames for another purpose, or reaches no reader: not a recorder feeding held_pair
            for m in self.JS_PUSH.finditer(src):
                block = src[max(0, m.start() - 2500):m.start()]
                # the hook's frame object is built in the lines just above the push: the block from its `const <var> = {` on
                start = block.rfind("const %s = {" % m.group(1))
                self.assertGreaterEqual(start, 0, "%s: the frame object of the push at offset %d was not found" % (name, m.start()))
                found.append((name, "js", m.group(1), block[start:]))
            dm = re.search(r"^def _record\(m\):\n(.*?)^    return f\n", src, re.S | re.M)
            if dm:
                found.append((name, "py", "f", dm.group(1)))
        return found

    def test_every_frame_recorder_feeding_held_pair_sets_both_presence_flags(self):
        found = self.recorders()
        self.assertEqual(sorted((n, kind) for n, kind, _, _ in found), sorted([
            ("test_federated_capability_corners_served.py", "js"), ("test_federated_capability_corners_served.py", "js"),
            ("test_federated_dial_terms_served.py", "js"), ("test_federated_relay_redial_served.py", "js"),
            ("test_relay_dial_declares_held_pair.py", "py")]),
            "the five recorders feeding held_pair: three lab hooks plus the corners module's two, and the relay-redial consumer's _record; a sixth lands here until it carries the flags")
        for name, kind, var, block in found:
            if kind == "js":
                # the message variable differs per hook (m, j); the frame variable is the pushed one
                self.assertRegex(block, r'if \("gen" in \w+\) %s\.genKey = true;' % re.escape(var), "%s: the gen presence flag" % name)
                self.assertRegex(block, r'if \("newGen" in \w+\) %s\.newGenKey = true;' % re.escape(var), "%s: the newGen presence flag" % name)
                # type and slot as the client reads them, a string else none (the author's fixer pass after round 4: a String()
                # read an array ['bars'] as the word, and the mirror applied a delta or reseeded a pair the client ignored)
                self.assertRegex(block, r'const %s = \{ sock: idx, t: typeof (\w+)\.type === "string" \? \1\.type : "", slot: typeof \1\.slot === "string" \? \1\.slot : ""' % re.escape(var), "%s: type and slot recorded only when strings" % name)
                self.assertRegex(block, r'for \(const k of \["gen", "newGen", "base", "rev", "through"\]\) if \(typeof \w+\[k\] === "number" \|\| \(typeof \w+\[k\] === "string" && \(k === "gen" \|\| k === "newGen"\)\)\) %s\[k\] = \w+\[k\];' % re.escape(var), "%s: the stamp fields, the revs as numbers, the gens as strings or numbers" % name)
            else:
                self.assertIn('f["genKey"] = True', block, "%s: the gen presence flag" % name)
                self.assertIn('f["newGenKey"] = True', block, "%s: the newGen presence flag" % name)
                self.assertIn('"t": m.get("type") if isinstance(m.get("type"), str) else ""', block, "%s: the type recorded only when a string" % name)
                self.assertIn('"slot": m.get("slot") if isinstance(m.get("slot"), str) else ""', block, "%s: the slot recorded only when a string" % name)
                self.assertIn("_rev_as_js(m.get(k))", block, "%s: the revs kept as the JS hooks keep them" % name)
        # and the flag is read as the docstring says: a frame carrying the key alone reads as a present gen the client cannot read
        self.assertTrue(_stamp_present({"genKey": True}, "gen") and _stamp_present({"newGenKey": True}, "newGen"))
        self.assertFalse(_stamp_present({"base": 0}, "gen"))

    def test_the_census_form_space_is_pinned_so_a_recorder_in_another_form_reds(self):
        # the derivation above finds a JS recorder by a push of a NAMED frame onto window.__frames (JS_PUSH) with `const <name> = {`
        # above it, and a Python one by a module-level `def _record(m):` ending in `return f`; a sixth recorder pushing an inline
        # object, or naming its function otherwise, would fall outside the population and the docstring's "a sixth lands here"
        # would be false. So every reader module's every push onto __frames and every _record must match a form the derivation
        # reads. (The needle is assembled, so this test's own text is not a push.)
        needle = "__frames." + "push("
        readers = 0
        for name in sorted(os.listdir(HERE)):
            if not (name.startswith("test_") and name.endswith(".py")):
                continue
            src = open(os.path.join(HERE, name), encoding="utf-8").read()
            if not self.READER.search(src):
                continue
            readers += 1
            pushes = src.count(needle)
            self.assertEqual(len(self.JS_PUSH.findall(src)), pushes, "%s: every push onto __frames in a reader module names a variable declared as `const <name> = {` (a push in another form is a recorder the census cannot see)" % name)
            defs = len(re.findall(r"^def _record\b", src, re.M))
            self.assertEqual(len(re.findall(r"^def _record\(m\):\n(?:.*?\n)*?    return f\n", src, re.M)), defs, "%s: every module-level _record takes (m) and ends in `return f`" % name)
        self.assertGreaterEqual(readers, 4, "the reader modules (an empty derivation checked nothing)")

    def test_the_python_recorder_keeps_type_slot_and_revs_as_the_js_hooks_do(self):
        # the fifth recorder reads the wire itself (Python json), the four JS hooks the client's parse (JavaScript); the same wire
        # text must leave the same record, or held_pair reads one frame two ways by lab (the author's fixer pass after round 4,
        # refusals-3 and refusals-4). The JS side of each row is the hook line's semantics: `typeof m[k] === "number"` keeps
        # any number (a bool is not one), JSON.parse reads 1.0 and 2e0 as 1 and 2, -1 as -1, 1.5 as 1.5, and a string, null or
        # bool is not copied; type and slot are kept when strings.
        sys.path.insert(0, HERE)
        import test_relay_dial_declares_held_pair as decl   # noqa: E402  the module's _record (no kernel is booted by the import)
        rows = [('{"type": "delta", "slot": "bars", "base": -1, "rev": 0}', {"t": "delta", "slot": "bars", "base": -1, "rev": 0}),
                ('{"type": "feedDelta", "gen": "%s", "base": 1.0, "rev": 2.0, "through": 2e0}' % GEN, {"t": "feedDelta", "slot": "", "gen": GEN, "base": 1, "rev": 2, "through": 2, "genKey": True}),
                ('{"type": "delta", "slot": "bars", "base": 0, "rev": 1.5, "through": "1"}', {"t": "delta", "slot": "bars", "base": 0, "rev": 1.5}),
                ('{"type": "delta", "slot": "bars", "base": true, "rev": null}', {"t": "delta", "slot": "bars"}),
                ('{"type": ["delta"], "slot": ["bars"], "base": 0, "rev": 1}', {"t": "", "slot": "", "base": 0, "rev": 1}),
                ('{"type": "bars", "gen": 8, "newGen": null}', {"t": "bars", "slot": "", "genKey": True, "newGenKey": True}),
                ('{"type": "bars", "gen": "%s"}' % GEN, {"t": "bars", "slot": "", "gen": GEN, "genKey": True})]
        for text, want in rows:
            self.assertEqual(decl._record(json.loads(text)), want, text)
        # an int the double cannot hold: JSON.parse rounds 2^53 + 1 to 2^53 and the client refuses it (not a safe integer); the
        # exact int here is refused by the same rule, so the two records read alike
        big = decl._record(json.loads('{"type": "delta", "slot": "bars", "base": 0, "rev": 9007199254740993}'))
        self.assertEqual(big["rev"], 2 ** 53 + 1)
        self.assertIsNone(_stamp_field(big, "rev"))
        self.assertIsNone(_stamp_field({"rev": 2 ** 53}, "rev"), "the JS-rounded value is refused too")
        self.assertEqual(_stamp_field({"rev": 2 ** 53 - 1}, "rev"), 2 ** 53 - 1)
        # the same wire frames through held_pair on both recorders' records agree: a negative feed base applies, the float forms apply
        wire = ['{"type": "feed", "gen": "%s"}' % GEN, '{"type": "feedDelta", "gen": "%s", "base": 0, "rev": 1, "through": 1}' % GEN,
                '{"type": "feedDelta", "gen": "%s", "base": -1, "rev": 2, "through": 2}' % GEN, '{"type": "feedDelta", "gen": "%s", "base": 1.0, "rev": 3.0, "through": 3e0}' % GEN]
        self.assertEqual(held_pair([decl._record(json.loads(t)) for t in wire], "feed"), (GEN, 3))


class FederatedDialTerms(unittest.TestCase):
    """Two kernels (a hub and a checked-in TESTHOST), one page, one driver run in setUpClass; each method asserts one observable."""
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        cls.procs = []
        try:
            cls._boot()
        except BaseException:          # a skip OR a failure: never leave a kernel or a lab behind
            cls.tearDownClass()
            raise

    @classmethod
    def _boot(cls):
        if not os.path.isdir(os.path.join(EXT, "node_modules", "playwright")):
            raise unittest.SkipTest("extension deps absent (npm ci not run here), the served lab needs them")
        probe = subprocess.run(["node", "-e", "const p=require(process.argv[1]);process.stdout.write(p.chromium.executablePath())",
                                os.path.join(EXT, "node_modules", "playwright")], capture_output=True, text=True)
        if probe.returncode != 0 or not os.path.exists(probe.stdout.strip()):
            raise unittest.SkipTest("no playwright browser on this box, the served lab needs one (CI installs none)")
        cls.lab = tempfile.mkdtemp(prefix="federated-dial-terms-")
        lab_dist.copy_dist(os.path.join(cls.lab, "dist"))   # the checkout's ONE build of the bundles, copied under its lock (tests/lab_dist.py)
        # the REMOTE owns both sessions (the watched tab + a cold one); the HUB owns none and shows them through the relay
        cls.rport, cls.rtoken = _free_port(), "testtok-remote-fed"
        cls.hport, cls.htoken = _free_port(), "testtok-hub-fed"
        rp, cls.rlog = _kernel(cls.lab, "testhost", cls.rport, cls.rtoken, [(SID_R0, "api", 1), (SID_R1, "worker", 2)])
        cls.procs.append(rp)
        hp, cls.hlog = _kernel(cls.lab, "hub", cls.hport, cls.htoken, [])
        cls.procs.append(hp)
        body = json.dumps({"host": HOST, "kernelPort": cls.rport, "busPort": _free_port(), "token": cls.rtoken}).encode()
        req = urllib.request.Request("http://127.0.0.1:%d/checkin?token=%s" % (cls.hport, cls.htoken), data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5) as resp:
            ans = json.loads(resp.read().decode())
        if not ans.get("ok"):
            raise unittest.SkipTest("the hub refused the check-in: %r" % ans)
        rows = []
        for _ in range(60):   # the hub's supervisor probes the peer and reports it up; the browser dials only then
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/tunnels?token=%s" % (cls.hport, cls.htoken), timeout=3) as r2:
                    rows = json.loads(r2.read().decode()).get("tunnels") or []
            except Exception:
                rows = []
            row = next((t for t in rows if t.get("host") == HOST), None)
            if row and row.get("status") == "up" and row.get("hasToken"):
                break
            time.sleep(0.5)
        else:
            raise unittest.SkipTest("the hub never reported the checked-in peer up: %r" % (rows,))
        cls.result, cls.driver_error = None, None
        cls._drive()
        cls.remote_chat_perf = cls._poll_remote_chat_perf()
        cls.remote_relay_rows = cls._read_relay_wsopen_rows()

    @classmethod
    def _drive(cls):
        cfg = os.path.join(cls.lab, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"chat": "http://127.0.0.1:%d/chat?skeleton=1&wid=%s&token=%s" % (cls.hport, WID, cls.htoken),
                       "remote0": REMOTE0}, f)
        driver = os.path.join(cls.lab, "driver.mjs")
        with open(driver, "w") as f:
            f.write(DRIVER)
        try:
            p = subprocess.run(["node", driver], capture_output=True, text=True, timeout=240,
                               env=dict(os.environ, EXT_PKG=os.path.join(EXT, "package.json"), CFG=cfg))
        except subprocess.TimeoutExpired as e:
            so = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode()
            cls.driver_error = "driver timed out; partial output:\n%s" % so
            return
        if p.returncode == 3:
            raise unittest.SkipTest("no playwright browser on this box, the served leg needs one (CI installs none)")
        if p.returncode != 0:
            cls.driver_error = "driver failed:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        if line is None:
            cls.driver_error = "driver printed no result:\n" + p.stdout[-3000:] + p.stderr[-3000:]
            return
        cls.result = json.loads(line[len("RESULT:"):])

    @classmethod
    def _poll_remote_chat_perf(cls):
        """The remote's builds.chat counters, once its push cycle has served the hub's skeleton client (a bounded
        retry, as the /tunnels poll above: no busy loop). At the base the dial states no diet and coldSkipped stays 0."""
        chat = {}
        for _ in range(20):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/perf?token=%s" % (cls.rport, cls.rtoken), timeout=3) as r:
                    perf = json.loads(r.read().decode())
                chat = (perf.get("builds") or {}).get("chat") or {}
            except Exception:
                chat = {}
            if chat.get("coldSkipped"):
                break
            time.sleep(0.5)
        return chat

    @classmethod
    def _read_relay_wsopen_rows(cls):
        """The remote kernel's wsopen rows of kind 'relay' (the hub's spliced dial). data.iid is a PRESENCE flag,
        not the value (kernel.py _note_ws_open): true names a per-pane iid, false is the anonymous relay."""
        path = os.path.join(cls.lab, "testhost", "xdg", "romp", "client-diag.jsonl")
        rows = []
        for _ in range(20):
            rows = []
            try:
                with open(path) as fh:
                    for ln in fh:
                        try:
                            rec = json.loads(ln)
                        except ValueError:
                            continue
                        if rec.get("what") == "wsopen" and (rec.get("data") or {}).get("kind") == "relay":
                            rows.append(rec)
            except OSError:
                rows = []
            if rows:
                break
            time.sleep(0.3)
        return rows

    @classmethod
    def tearDownClass(cls):
        for p in getattr(cls, "procs", []):
            try:
                p.kill(); p.wait()
            except Exception:
                pass
        shutil.rmtree(getattr(cls, "lab", ""), ignore_errors=True)

    def _driver_ran(self):
        if getattr(type(self), "driver_error", None):
            self.fail(type(self).driver_error)
        if getattr(type(self), "result", None) is None:
            raise unittest.SkipTest("the driver produced no result")

    def _relay_dial(self):
        self._driver_ran()
        relay = [u for u in self.result["dials"] if "/remote/TESTHOST/ws" in u]
        self.assertTrue(relay, "the hub page dialed the remote's relay socket: %r" % self.result["dials"])
        return relay[0]

    def test_the_hub_dials_the_remote_relay_socket(self):
        self.assertTrue(self._relay_dial())

    def test_the_remote_dial_carries_the_pages_terms(self):
        qs = parse_qs(urlsplit(self._relay_dial()).query)
        self.assertEqual(qs.get("app"), ["chat"], "the pane's app")
        self.assertEqual(qs.get("delta"), ["1"], "delta rides every dial, as the local pane's does")
        self.assertEqual(qs.get("skeleton"), ["1"], "the page's skeleton posture rode the remote dial")
        self.assertEqual(qs.get("active"), [SID_R0], "the watched remote tab, stripped to its bare sid")

    def test_the_remote_dial_caps_term_is_the_decoder_word_and_the_members_its_conns_bases_hold(self):
        # derived from the drive (assert_relay_dials): a first dial has no socket before it and states the decoder word alone;
        # the frames the relay socket then received are what a redial's held member would be derived from, and on a kernel
        # whose frames carry no gen (this checkout's) that would be the decoder word alone too
        self._driver_ran()
        checked = assert_relay_dials(self, "chat", self.result["dials"], self.result.get("frames"))
        self.assertEqual([h for _i, h, _u in checked], [HOST], "one relay dial, to the checked-in host: %r" % (checked,))
        frames = [f for f in self.result.get("frames") or [] if f.get("sock") == checked[0][0]]
        self.assertTrue(frames, "the relay socket recorded the remote's frames (the drive a redial's member is derived from)")

    def test_the_remote_iid_is_namespaced_by_the_hub_wid(self):
        qs = parse_qs(urlsplit(self._relay_dial()).query)
        iid = (qs.get("iid") or [""])[0]
        self.assertTrue(iid.startswith(WID + ":"),
                        "the iid a hub pane sends is namespaced by its wid so it cannot collide with the remote's own page: %r" % iid)
        self.assertGreater(len(iid), len(WID) + 1, "…and carries the page's own instance id after the prefix")

    def test_the_remote_diets_its_cold_tab_for_the_skeleton_client(self):
        self._driver_ran()
        self.assertGreater(self.remote_chat_perf.get("coldSkipped") or 0, 0,
                           "the remote skipped its cold tab for the hub's skeleton client: %r" % self.remote_chat_perf)

    def test_the_remote_relay_wsopen_row_names_a_per_pane_iid(self):
        self._driver_ran()
        rows = self.remote_relay_rows
        self.assertTrue(rows, "the remote filed a relay wsopen row for the hub's spliced dial")
        self.assertTrue(any((r.get("data") or {}).get("iid") for r in rows),
                        "a relay row names a per-pane iid (present), not the absent one that reads as an anonymous relay: %r"
                        % [r.get("data") for r in rows])


if __name__ == "__main__":
    unittest.main()

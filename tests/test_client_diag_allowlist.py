#!/usr/bin/env python3
"""The clientDiag handler admits each surface's known top-level data keys and bounds the row (2026-09-18, the beacon
extension). The file used to take whatever a page posted, of any shape and size. Now: a key outside the surface's
allowlist (CLIENT_DIAG_KEYS) is dropped and said once on stderr per surface and key; a data that is not an object is
stored as null; every string value is cut at CLIENT_DIAG_STR_MAX characters at any depth, and a row a value of which was cut,
or nulled past CLIENT_DIAG_DEPTH_MAX, carries CLIENT_DIAG_CUT_KEY naming the admitted keys it happened under, said once per
surface and key (the maintainer's round 3 of wsBytesByHost, 2026-09-20: the one silent loss on this road); a row whose JSON runs past
CLIENT_DIAG_ROW_MAX bytes keeps its surface, what and app and carries {"capped": true, "bytes": N, "app": ...} as its
data, except a perf minute row, which sheds CLIENT_DIAG_MINUTE_SHED's keys in order (the uncapped wsBytesByHost map first
and whole, then its per-minute figures) until it fits and names them under `capped`, so the once-per-page nav, res, marks
and env survive; the bound is derived from the collector's own caps, so the row it builds at every cap at once is stored
whole while its wsBytesByHost map is under the crossing the ladder test derives, and past it the map alone is shed; the
surface and what strings are cut too, once; the
stderr latch is bounded at CLIENT_DIAG_SAID_MAX pairs and one row can have at most CLIENT_DIAG_ROW_SAY_MAX of its keys
said; and a page's row under the kernel's own surface is refused. Today's rows (the collector's minute and slowframe,
the shim's return, close and stale rows) pass whole, so the desktop readers keep every key they depend on, and one
fixture row per call site of every bundle and shell poster ties the table to what the posters send.

Drives the REAL Handler's WS dispatch (_dispatch_ws with a clientDiag message, the way the pane shim delivers one)
against a hermetic state directory. Synthetic fixtures only: a placeholder dashboard id, invented numbers."""
import contextlib
import io
import json
import os
import pathlib
import re
import tempfile
import unittest
from romp_load import load_source

HERE = os.path.dirname(os.path.realpath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin")

# Hermetic state BEFORE the loads: they resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor
load_source("romp_event_model", os.path.join(BIN, "romp-event-model"))
load_source("romp_judge", os.path.join(BIN, "romp-judge"))
os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
km = load_source("romp_kernel_cdiag_allow", os.path.join(BIN, "romp-kernel"))

WID = "11111111-2222-3333-4444-555555555555"
UI = os.path.join(os.path.dirname(HERE), "ui", "webview")

# a minute row as ui/webview/perf-telemetry.ts builds it today (perf-telemetry.test.ts pins the same keys)
MINUTE = {"app": "chat", "since": 1700000000000, "span_ms": 60000,
          "frames": {"session": {"n": 12, "ms_sum": 340.5, "ms_max": 88.1, "n16": 5, "n100": 0, "hist": [0] * 14}},
          "free": {"n": 3, "p50": 12.5, "p90": 40, "max": 41.2},
          "loaf": {"n": 1, "blocking_ms": 60, "worst_ms": 110, "top": [{"k": "render.js:paintAll@9000", "ms": 90, "n": 1, "inv": "WebSocket.onmessage"}], "src": "loaf"},
          "slow": {"sent": 1, "suppressed": 0, "suppressed_worst_ms": 0},
          "dom": 53306, "visible": True, "hidden_pane": False, "ua": "safari-ios", "heap_mb": 210.4}
# the shared fields the same row carries when the gear's share switch is on
SHARED = {"nav": {"type": "reload", "responseEnd": 210, "domContentLoaded": 656, "loadEventEnd": 0},
          "res": {"feed.js": {"transferSize": 120000, "encodedBodySize": 119700, "duration": 88}, "other": {"transferSize": 600, "encodedBodySize": 400, "duration": 45}},
          "marks": {"wsOpen": 121, "bundleReady": 300, "firstFrame": 455, "fp": 388, "fcp": 402},
          "env": {"standalone": True, "iosMajor": 17, "touch": True, "vw": 390, "vh": 664, "dpr": 3, "entryTypes": ["paint", "resource", "navigation"], "ric": False, "dv": 1757100000},
          "vis": {"hiddenN": 1, "visibleN": 1, "hiddenMs": 30000}, "wsBytes": 12345, "rafGap": {"n": 2, "worst": 120},
          # wsBytesByHost (2026-09-19, the user's approval: the bytes each attached host sent, one number per host, no content):
          # the same unit per REMOTE host by its position in the pane document, h1 the first remote host it attached; positions, never names
          "wsBytesByHost": {"h1": 40123, "h2": 991}}

# The content census (the maintainer's round 1 of the wsBytesByHost change, 2026-09-20; re-derived by producers in the author's pass 4). Every admitted
# key of every surface, classified by what its VALUE can carry as the first-party posters and the kernel's own writers build it.
# THE RULE (the author's pass 4, after a row was found classified from a sibling field): a field is a carrier if ANY producer chain can put a
# host name in it, however rare that road; classify by the producer's RANGE, never by the field's typical content, and follow the
# value to its WRITERS and their minters, never to the shape of the row it appears in (a sibling field is not evidence about a
# value). Each carrier's reason names its range, every row of the kind or the one road, and the disclosure copies read the
# range back. The four forms follow from the rule: BARE (a host name as the value), PREFIXED (a session id with its host in
# front, <host>:<uuid>, when the row concerns a remote session), KEYED (a map whose keys are host names), SUFFIX (a host name as
# the tail of a postal message id inside the value, <epoch>.<pid>_<hex>.<host>: postal_service.py _unique bakes self_host() in);
# a fifth would classify itself. NONE names the producer chain and answers whether any branch reaches a host name. A shorthand
# reason (_BOOL, _INT, _ENUM) is a claim about EVERY writer of the key, checked by the fixture rows in
# test_one_fixture_row_per_poster_call_site_passes_whole_and_the_table_names_nothing_else and, for the perf, pane-shim and
# reload-core surfaces, test_todays_rows_pass_whole_and_quietly: one row per call site with the values the writers post, and
# every value posted under a shorthand row asserted to the row's shape (assert_shorthand_shapes: a number, a boolean, a
# string), so a fixture value of another shape reds (the author's pass-4 fixer pass: the pass-whole loop compares the stored row to the
# posted one and reads no shape, and three chat values had contradicted their rows green). A census keyed on the NAME `host`
# had missed the chat surface, whose sid, id, ids and active are the tab ids
# the page holds, which federation.ts prefixes for every remote session (prefixInbound on SCALAR_ID and ARRAY_ID, the tab records
# through OBJ_ID); the cut at CLIENT_DIAG_STR_MAX keeps the head of a string, prefix included, and a suffix survives it by 64
# less the head's length. The kernel admits a surface's top-level keys and cuts nested string values; it inspects no nested key
# and no value's form, so every class here names the writer that holds the shape.
# test_every_admitted_key_is_classified_by_the_content_its_value_can_carry ties this table to CLIENT_DIAG_KEYS both ways, so a
# key added to the table without a row here fails, and the disclosure copies are read back against the host-carrying surfaces
# this table derives (test_the_disclosure_copies_state_the_content_rule_and_name_every_host_carrying_surface).
BARE, PREFIXED, KEYED, SUFFIX, NONE = "bare", "prefixed", "keyed", "suffix", "none"
_ENUM, _INT, _BOOL = "a fixed word", "a number", "a boolean"
CENSUS = {
    "perf": {   # perf-telemetry.ts: the minute and slowframe rows; every key's shape is the collector's
        "app": (NONE, "the pane word the collector is created with"), "since": (NONE, _INT), "span_ms": (NONE, _INT),
        "frames": (NONE, "keys: classifyFrame's type, an identifier of at most 32 characters or the fold word; values: counts"),
        "free": (NONE, "percentiles"), "loaf": (NONE, "top[].k is scriptKey's basename form, top[].inv is sanitizeInvoker's, which strips an element id and reduces a URL to its basename; src a fixed word"),
        "slow": (NONE, "counts"), "dom": (NONE, _INT), "visible": (NONE, _BOOL), "hidden_pane": (NONE, _BOOL),
        "ua": (NONE, "uaClass's fixed word"), "heap_mb": (NONE, _INT), "type": (NONE, "the slow frame's classified type"), "ms": (NONE, _INT),
        "nav": (NONE, "fixed keys, type from NAV_TYPES or other, whole ms"),
        "res": (NONE, "keys: resourceKey's same-origin /dist/ or /media/ basename, a root file name or other, so a cross-origin URL folds"),
        "marks": (NONE, "fixed keys, whole ms"), "env": (NONE, "fixed keys; entryTypes from a fixed list; dv a number"),
        "vis": (NONE, "counts"), "wsBytes": (NONE, _INT), "rafGap": (NONE, "counts"),
        "wsBytesByHost": (NONE, "keys h<ordinal>: the collector's bytesByHost keeps a key only on ^h[1-9][0-9]*$ and federation.ts mints them as 'h' plus the attach ordinal; values: characters; the kernel admits the key and does not inspect the map's keys"),
    },
    "pane-shim": {   # kernel.py's pane shim: staleDiag, returnDiag, the wsclose, wsconnfail and page-load rows
        "app": (NONE, "the pane word"), "why": (NONE, "a stale cause word"), "ready": (NONE, _INT), "quietMs": (NONE, _INT), "hidden": (NONE, _BOOL),
        "decision": (NONE, _ENUM), "resumed": (NONE, _BOOL), "hiddenMs": (NONE, _INT), "frozenMs": (NONE, _INT), "quietAtResumeMs": (NONE, _INT),
        "resent": (NONE, _BOOL), "ms": (NONE, _INT), "bytesSince": (NONE, _INT), "redialed": (NONE, _BOOL), "code": (NONE, "the close code"),
        "reason": (NONE, "the close frame's reason text: this kernel sends no close frame (a drop reads 1006), so empty, or an intermediary's text, cut"),
        "wasClean": (NONE, _BOOL), "sinceOpenMs": (NONE, _INT), "everConnected": (NONE, _BOOL), "bundleReady": (NONE, _BOOL),
        "attempts": (NONE, _INT), "firstFailMs": (NONE, _INT), "wasDiscarded": (NONE, _BOOL), "nav": (NONE, "the navigation type word"),
        "awaitLink": (NONE, _BOOL), "linkUpMs": (NONE, _INT), "parked": (NONE, _BOOL),
    },
    "reload-core": {   # kernel.py's _RELOAD_CORE_JS, the one writer heldLong (a hold that has stood for the bound files one breadcrumb, once per owed request)
        "reason": (NONE, "held: owed.reason, the literal build (accept, the Reload click: owed={reason:'build',...}) or required (demand: request('required', why) on a {type:'reloadRequired'} frame on the pane's or the shell's local socket, which no kernel sends today), the core's two writers of owed and no other; never a hold word: fresh is busy()'s, the row's sibling hold field's vocabulary, which no writer assigns to reason"),
        "detail": (NONE, "held: owed.detail: on build the offer's dist token, a decimal integer's text (_dist_ver, the max mtime of dist/*.js, through the shim's or the shell's ka frame or the page-origin /version), or its code identity (_code_ident's 12 hex characters, or ROMP_CODE_IDENT's string), both the SERVING kernel's and never a peer's (federation.ts never touches __rompReload); on required the frame's why, cut at 64 (no sender today); '' when that why is empty"),
        "hold": (NONE, "held: busy()'s word, the first clocked pane word behind any gesture (paneHere, busyHere: code literals of the gesture and hold tables) or fresh"),
        "ageMs": (NONE, "held: Date.now() less the hold's start, a number"),
    },
    "shell": {   # kernel.py's shell scripts: the push panel's rows, the tap ledger rows, the return probe
        "sidAttached": (NONE, _BOOL),
        "host": (BARE, "push-test: the active tab's host, read off the tab id's prefix (activeSession), empty for a local session"),
        "why": (NONE, "push-test: activeSession's cause word, one of six literals ('', no-frame, no-doc, no-tabs, none-active, threw)"), "tabs": (NONE, _INT),
        "status": (NONE, "reveal-post: the /reveal fetch's Response.status, a number, on land()'s then arm; the literal 0 on its catch arm (the fetch threw); no writer posts a word"),
        "via": (NONE, "the road word each caller passes, literals: reveal-post link, ack, vanish, sw; deeplink boot, pageshow, popstate; tap-pending boot, visible, pageshow, focus"), "boot": (NONE, _BOOL),
        "hasSid": (NONE, _BOOL), "hasCard": (NONE, _BOOL), "hasPid": (NONE, _BOOL), "controlled": (NONE, _BOOL), "dup": (NONE, _BOOL), "sub": (NONE, _BOOL),
        "rows": (NONE, _INT), "err": (NONE, "tap-pending: the literal true when GET /push/pending failed (fromLedger's catch arm; the kernel's body has no err key); absent otherwise"),
        "getNotifications": (NONE, "tap-pending: whether getNotifications answered (d !== null), a boolean"),
        "displayed": (NONE, _INT), "vanished": (NONE, _INT), "superseded": (NONE, "tap-pending: a count, written only when nonzero"),
        "sid8": (PREFIXED, "tap-pending-land and tap-vanish-land: the first 8 characters of the push ledger row's sid (r.sid.slice(0,8), v.sid.slice(0,8)), which the test push "
                           "files as the active tab's whole data-id (activeSession's sid, host:uuid on a federated tab, into _push_ledger_add) and which the relay prefixes with its "
                           "origin before its own ledger row (host:sid); the ledger's host field is a courtesy copy of that prefix (_push_payload) and the rows do not read it. So the "
                           "head is a host name's first 8 characters, or a short host name whole, on every row of both kinds that concerns a remote session"),
        "ageS": (NONE, "tap-pending-land and tap-vanish-land: _push_pending's bounded int"), "shape": (NONE, "sw-message: m.romp behind the gate m.romp === 'notificationClick', so that literal"),
        "kind": (NONE, "sw-message: the worker's copy of _push_payload's str(kind or 'card'): card, turn or test"),
        "sw": (NONE, "sw-message: the worker's diag block or null: road (open, focus or open-after-refused), vis (a visibilityState word), clients and tops (counts); sw.js's "
                     "notificationclick mints it beside the message's sid and host and copies neither in; the kernel stores its nested keys as posted"),
        "decision": (NONE, _ENUM),
        "hiddenMs": (NONE, _INT), "quietMs": (NONE, _INT), "attempts": (NONE, _INT), "firstFailMs": (NONE, _INT), "ms": (NONE, _INT),
    },
    "federation": {   # federation.ts diag(): hostconn, feedDelta-nobase, feedDelta-stale, feedDelta-apply, feedmerge, sendqueue, senddrop
        "host": (BARE, "the conn's host on every hostconn, feedDelta-nobase, feedDelta-stale, feedDelta-apply, sendqueue and senddrop row (federation_host_row_kinds, "
                       "derived from federation.ts); empty on the poll rows, local on the local nobase and local apply rows"),
        "ev": (NONE, "the hostconn event word"),
        "why": (NONE, "a cause word at each literal writer (watchdog-close's quiet or connecting, dial-deferred's local-down, senddrop's no-conn on its bookkeeping arm, the feedDelta-stale ladder's words, "
                      "feedDelta-apply's asked or stopped at refuseRemoteApply and refuseLocalApply); "
                      "on delta-unknown-slot the peer frame's own slot string as parsed off the remote socket, cut at 32 (UNKNOWN_SLOT_CUT: the remote kernel's choice, a fixed "
                      "word for every kernel in this repo), then the peer's sha as the hub's /version poll validated it (_peer_sha) or nothing; on delta-unkeyed-base this bundle's "
                      "slot, collection and shape words with the same tail; or the page's own /tunnels fetch failure text, cut at 200 by the poster and 64 here. NONE on the census's "
                      "first-party scope (this header): a peer kernel could put any 32 characters in its slot word"),
        "quietMs": (NONE, _INT), "foreground": (NONE, _BOOL), "msgType": (NONE, "hold, sendqueue and senddrop: msg.type of an outbound frame, a KERNEL_SETTING word (sendqueue), a BOOKKEEPING type (hold and the no-conn drop), or, on the default drop, the outbound gesture's own type, a page-minted literal"),
        "rs": (NONE, "a readyState"),
        "flushed": (NONE, "open and flush-halt: message type words (flushPending's list)"), "held": (NONE, "flush-halt: pendingTypes, message type words"),
        "unread": (NONE, _BOOL), "endedUnread": (NONE, _BOOL),
        "code": (NONE, "the close code"), "clean": (NONE, _BOOL), "detached": (NONE, _BOOL),
        "pendingDropped": (NONE, "detach: pendingTypes(c), each a KERNEL_SETTING word or a BOOKKEEPING type; moot: needFull alone (dropAsksTheReadyServes); type words on every writer this "
                                 "field ever had (no writer posted a count)"),
        "buildId": (NONE, "feedDelta-nobase, feedDelta-stale and feedDelta-apply: the feedDelta frame's buildId as its kernel sent it, posted raw: the LOCAL kernel's on the local nobase and "
                          "local apply rows, the remote's on the remote rows; _next_feed_build_id's integer counter on every kernel in this repo"),
        "road": (NONE, "feedDelta-apply: which road the throwing delta arrived on, one of two fixed words at the two writers, wire (refuseRemoteApply, a remote conn's socket) "
                       "or local (refuseLocalApply, the local socket); never host content (the host rides the host key)"),
        "counts": (KEYED, "feedmerge: the merged feed's ask count per host, keyed by the host name (local for the local kernel), every row"),
        "gt": (NONE, _INT), "superseded": (NONE, "sendqueue: the replaced queued pick's gt, the gesture-clock stamp it was posted with (a number at or above the wall clock in ms), or "
                                                 "true when that pick carried no numeric gt (an older emitter)"),
    },
    "chat": {   # render.ts's direct posts and scroll-write.ts's rows through scrollDiagRow
        "sid": (PREFIXED, "the active tab's id or the session's id: <host>:<uuid> for a remote session (send, cancel-miss, reconcile-optimistic-failed, every scroll row)"),
        "error": (NONE, "a caught exception's message, cut at 200 by the poster and 64 here"), "held": (NONE, _INT), "got": (NONE, _INT), "distVer": (NONE, _INT),
        "path": (NONE, "location.pathname, the page's own route"), "mdLen": (NONE, _INT), "queuedLeft": (NONE, _INT),
        "ids": (PREFIXED, "live-omitted-kept: tab ids the kernel still affirms live, prefixed for remote sessions"),
        "n": (NONE, _INT),
        "active": (PREFIXED, "skeleton: the active tab's id, prefixed for a remote session"),
        "ts": (NONE, _INT), "len": (NONE, _INT), "route": (NONE, "plain, quote or followup"),
        "id": (PREFIXED, "empty-session-frame: the frame's session id, prefixed by prefixInbound for a remote session"),
        "load": (NONE, "federation-missing: federationLoadEntry's four rounded numbers (frame-listener.ts) or null"),
        "first": (NONE, "federation-missing: the earlier pass's load figures, federationLoadEntry's four numbers read back from the sessionStorage retry marker ({load: entry}, its "
                        "only writer), or null; no build ever posted a boolean"),
        "recovered": (NONE, _BOOL), "hadRestore": (NONE, _BOOL), "perMinute": (NONE, _INT), "writer": (NONE, "the writing function's name"),
        "before": (NONE, _INT), "after": (NONE, _INT), "delta": (NONE, _INT), "stick": (NONE, _BOOL), "gesture": (NONE, _BOOL), "sh": (NONE, _INT), "ch": (NONE, _INT),
        "anchor": (SUFFIX, "landmiss: the last 12 characters of whatever scrollToAnchor was called with (uuid.slice(-12)): a rendered turn's data-uuid, a kept or restored row's "
                           "uuid, the chatWindow reply's echoed ask, a feed card's anchorUuid the kernel relays (showOnTimeline), a branch token, or a deep link URL's anchor query "
                           "forwarded verbatim by the kernel's deepLink road (the timeline bridge's __rompTimelineOpenExternal, timeline-boot.ts, the extension's URI handler), which "
                           "the timeline's message connector fills with a postal message id, <epoch>.<pid>_<hex>.<host> (postal_service.py _unique), so on that ONE road the tail is "
                           "the delivering kernel's short hostname, whole with its leading dot for a host of up to 11 characters, on a single-kernel page the page's own machine's; "
                           "filed on a landing miss, not gated by the share switch"),
        "proto": (NONE, _INT), "events": (NONE, _INT), "regions": (NONE, _BOOL),
        "headKnown": (NONE, _BOOL),
        "headFrom": (NONE, "landmiss: the resident tail's first global event index (Session.headFrom, a non-negative number from the kernel's full frame or the chatHead reply's from), "
                           "or null when the active tab has no live session"),
        "older": (NONE, _BOOL), "noframe": (NONE, _BOOL),
        "trail": (NONE, "landmiss and regionask: landTrail.slice(-4), the last up-to-four landing-trail words, code literals render.ts pushes (pointer-exact, time-nearest, "
                        "window-fault and the like), the longest 21 characters"),
        "dh": (NONE, _INT), "last": (NONE, "the tail element's class list or live-ask"),
        "cls": (NONE, "unitchange: an element's className, or '#' plus the id of one of #content's non-thread children (scroll-write.ts boxLabel), literal ids"), "fromTail": (NONE, _INT),
        "atBottom": (NONE, _BOOL), "where": (NONE, "view or live-ask"), "removed": (NONE, "tailmut: up to four element class names (scroll-write.ts)"), "added": (NONE, "tailmut: the same minter's class names"),
        "reAdded": (NONE, _BOOL), "shBefore": (NONE, _INT), "shAfter": (NONE, _INT), "st": (NONE, _INT),
        "top": (NONE, "scrollgesture: #content's scrollTop, a number; spacer: the top spacer's [before, after] heights (scroll-write.ts spacerRow)"),
        "bot": (NONE, "spacer: the bottom spacer's [before, after] heights, its only writer"),
        "dTop": (NONE, _INT), "dBot": (NONE, _INT), "lo": (NONE, _INT), "hi": (NONE, _INT), "edge": (NONE, "top or bottom"),
        "why": (NONE, "regionask: gap-scroll (requestTurns, a gap fill's region ask) or landing (the window ask at landing), the two writers' literals"),
        "notice": (NONE, _BOOL),
        "nav": (NONE, "regionask: whether the window ask is a fresh landing rather than keepPlaceAcrossWindow's re-land, nav = !relandAsk, a boolean"),
        "kind": (NONE, "regionask: the landing anchor's kind, the kernel's _focus_kind word (user) on the showOnTimeline road, or a deep link URL's anchorKind query forwarded as "
                       "posted by the kernel's deepLink road (a string any link can carry, cut at 64; first-party links send user or nothing); not a host by construction on any "
                       "first-party road, the standing error and strip's err have"),
        "keep": (NONE, "regionask: whether a keep-offset restore is armed, pendingAnchorKeepY != null, a boolean"), "reland": (NONE, _BOOL),
    },
    "strip": {   # strip.ts: the host popover's fetch and toggle rows
        "ok": (NONE, _BOOL), "tunnels": (NONE, _INT), "err": (NONE, "the page's own /tunnels fetch failure as String(err), cut"), "open": (NONE, _BOOL),
        "base": (NONE, "netToggle: the extension's kernel URL in the VS Code webview, http://127.0.0.1:<port> (extension.ts HOST is the loopback literal), a URL with no host name; the "
                       "served dashboard never posts a strip row (the strip renders only under the extension's window.__rompShowStrip), so the poster's '' default is unreachable"),
    },
    "feed": {   # feed.ts: colflip, itemset (auditShownColumns), feedDelta-unapplied
        "id": (SUFFIX, "colflip: the ask's itemId (a.itemId), by its minter in kernel.py: goal node ids <uuid>:g<n> and provisional:/awaiting:/blocked:/usertodo:<sid> carry a bare "
                       "sid; notice:<sid>:<key>:<rev> a caller-chosen key under NOTICE_KEY_RE (20 characters of it survive the cut); parked:<postal mid> ends in the card's own "
                       "kernel's postal host (deliver()'s row id, postal_service.py _unique and self_host: <epoch>.<pid>_<hex32>.<host>; 5 to 11 host characters survive the 64 "
                       "cut); quarantine:<px- mid> ends in the held mail's ORIGIN kernel's postal host (0 to 4 survive). prefixInbound rewrites the ask's sid and never its item "
                       "id; the road is not gated by the share switch and needs no remote session: on a single-kernel page the parked form names the page's own machine's postal "
                       "name. The parked and quarantine cards are fixed at needs_input, so this row's flip road is the pane's own prediction"),
        "from": (NONE, "a column word"), "to": (NONE, "a column word"),
        "ev": (NONE, "the input change word"), "buildId": (NONE, "the merged frame's buildId, _next_feed_build_id's integer counter"), "predicted": (NONE, _BOOL),
        "appeared": (SUFFIX, "itemset: item ids of feed.id's forms, every minter included, cut per element; filed on routine use (a card arriving after first render)"),
        "gone": (SUFFIX, "itemset: item ids of feed.id's forms, cut per element; filed on routine use (a card leaving)"), "total": (NONE, _INT),
    },
    "outline": {   # fleet.ts: a feedDelta or a delta frame that reached the pane unapplied (federation.js absent or older than the receiver), the frame's own stamps posted raw
        "buildId": (NONE, "feedDelta-unapplied: the frame's buildId as its kernel sent it, _next_feed_build_id's integer counter on every kernel in this repo"),
        "slot": (NONE, "delta-unapplied: the frame's slot word, bars or feed from a kernel in this repo (_send_slot's ftype, one of _DELTA_SLOTS's names); on the pre-receiver federation.js road (the handler's comment: a bundle older than the per-conn receiver handing the pane a remote kernel's raw delta) the remote's own string, cut at 64; at this head no bundle road hands the pane a delta frame (the shim and the receiver each recover instead), so the row is a mixed-build breadcrumb"),
        "rev": (NONE, "delta-unapplied: the frame's rev, the kernel's per-slot integer counter (_send_slot); on the pre-receiver federation.js road the remote's value as the wire carried it, slot's scope clause"),
    },
    "waiting": {"buildId": (NONE, "feedDelta-unapplied (waiting.ts): the frame's buildId as its kernel sent it, _next_feed_build_id's integer counter")},
    "kernel": {   # the kernel's four direct writers: _note_ws_open, _note_history_reply, _note_chat_withheld_at_close, _implicit_handshake
        "app": (NONE, "the dial's app word"), "kind": (NONE, "page, relay or hub"), "reconnect": (NONE, _BOOL), "iid": (NONE, "a boolean: whether the dial stated one"),
        "cid": (NONE, "a minted hex id"),
        "host": (BARE, "wsopen, kind hub: the host a spliced /remote/<host>/ws upgrade was relayed to (_note_ws_open, from the hub's splice)"),
        "sid": (NONE, "historyReply: str(msg['id']), the session id a history ask named, stored uncut (the kernel's rows never pass _client_diag_scrub): a page asks for its "
                      "local sessions bare, and the relay strips a remote id's host before forwarding (federation.ts stripHost)"),
        "type": (NONE, "the ask's type word, one of four guarded words or the literal loadOlder"),
        "span": (NONE, "historyReply: the turn pair [lo, hi) the kernel computed from its turn index (_chat_history_reply), or null on a loadAround with no placed turn; on a "
                       "chatTurns reply the kernel could not build (lo or hi not an int, no session or build, an exception) the ask's own lo and hi echoed as parsed and stored "
                       "UNCUT, since the kernel's rows never pass _client_diag_scrub; the first-party asks send numbers (render.ts requestTurns via pagesToAsk, "
                       "reaskOutstandingGaps via parseGapKey) and the relay forwards lo and hi untouched"),
        "events": (NONE, _INT), "bytes": (NONE, _INT), "head": (NONE, _BOOL),
        "missing": (NONE, _BOOL), "refused": (NONE, _BOOL),
        "reason": (NONE, "historyReply: the fault text the kernel minted for a refused history reply (_fault's two forms, the legacy arm's; no build to answer from, or an "
                         "exception's class and text), stored uncut; an exception's text may quote the ask"),
        "sent": (NONE, _BOOL), "frames": (NONE, _INT), "ageS": (NONE, _INT), "frame": (NONE, "a WS_OPS word or other"), "withheld": (NONE, _INT), "proto": (NONE, _INT),
    },
}

# The kernel-written marker keys (the author's pass 4, 2026-09-20), classified as the admitted keys are: written AFTER the admit by the
# kernel alone and admitted from no poster (test_the_constants_and_the_table pins that for every surface), so a page cannot
# forge either; neither can carry a host name, since both hold positions of keys in the row and a byte count.
MARKERS = {
    "capped": (NONE, "_client_diag_line: true (the whole-row marker, beside bytes) or {bytes, dropped}, the shed perf minute row's byte count and the "
                     "names of the keys it shed (CLIENT_DIAG_MINUTE_SHED's words), positions of keys and a number, no host"),
    "cut": (NONE, "_client_diag_admit: the admitted keys of the row under which _client_diag_scrub cut a string or nulled a nesting, in the "
                  "row's key order: positions of keys in the row, taken from the surface's own table, no host"),
}


def host_carrying_keys():
    """The census's host-carrying keys by surface, {surface: {key: class}}, derived from the rows whose class is not NONE."""
    out = {}
    for surface, table in CENSUS.items():
        keys = {k: c for k, (c, _why) in table.items() if c != NONE}
        if keys:
            out[surface] = keys
    return out


def federation_host_row_kinds():
    """The federation row kinds that carry the conn's host, derived from federation.ts: every `this.diag("<what>", ...)` call
    whose data literal names `host` on the call's line (the literal's first key at every site today). The disclosure copies
    name each kind (the author's pass-1 verify, 2026-09-20: the copies said "hostconn rows" where the census reason said every hostconn,
    feedDelta and send row); a new host-carrying row kind fails the pin until the copies name it."""
    src = open(os.path.join(os.path.dirname(HERE), "ui", "webview", "federation.ts"), encoding="utf-8").read()
    return set(re.findall(r'this\.diag\("([\w-]+)",[^\n{]*\{[^\n}]*\bhost\b', src))


STALE_WHY_WORDS = ("unpaired", "gen", "newGen", "base", "ahead", "through", "behind", "rev", "disagree")   # the feedDelta-stale row's why vocabulary in the ladder's test order (the author's pass 4, 2026-09-20): a word per field failure and a word per relation, held to the ladder by test_the_stale_rows_vocabulary_is_the_ladders


def stale_why_expr():
    """The `const why = ...` expression of applyRemoteFeedDelta's stale row, as federation.ts spells it, or None when the
    anchors are gone. The anchor is the statement AFTER it, which carries the minter's literal, `{ host, buildId: d.buildId,
    why }`, so the read also holds that the row carries host, buildId and why and nothing else: the word is the whole signal a
    reader of the file has (a stale row in the file carries no gen, base, rev or through), which is why a relation failure
    between two valid fields needs a word of its own and cannot ride a field's; and since the author's pass 4 the anchor
    holds the row's latch too (sayDeltaOnce keyed on the word and the remote's build, the ask beside it unlatched). The
    expression is cut at the `;` that ends its statement, found from the anchor backwards, so a `;` inside one of its
    literals stays inside the expression (an earlier reader stopped at the first `;`)."""
    src = open(os.path.join(os.path.dirname(HERE), "ui", "webview", "federation.ts"), encoding="utf-8").read()
    anchor = re.search(r';\s*\n\s*if \(this\.sayDeltaOnce\(c, "feedDelta-stale", why \+ this\.peerTag\(c\)\)\) '
                       r'this\.diag\("feedDelta-stale", \{ host, buildId: d\.buildId, why \}\);', src)
    if not anchor:
        return None
    start = src.rfind("const why = ", 0, anchor.start())
    return src[start + len("const why = "):anchor.start()] if start >= 0 else None


_JS_FORMS = {'"': "double-quoted string", "'": "single-quoted string", "`": "template literal"}
_JS_SIMPLE_ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "v": "\v", "0": "\0", "\\": "\\", "'": "'", '"': '"', "`": "`"}
_JS_PUNCT = ("===", "!==", "?.", "??", "==", "!=", "<=", ">=", "&&", "||", "=>", "**")


def _js_literal(src, i):
    """Read the string or template literal that opens at src[i] as JavaScript reads it: the value it denotes and the index
    after its closing quote. Every escape the language permits is decoded (the simple escapes, \\xHH, \\uHHHH, \\u{H...}, an
    escaped quote, a line continuation, and a non-escape character standing for itself); a template literal may hold a raw
    newline. A literal this cannot read, an unterminated one, a malformed escape or a template expression (a `${...}`
    substitution, no constant), raises an AssertionError naming the form: a refusal, never absence."""
    q = src[i]
    form = _JS_FORMS[q]
    j, out = i + 1, []
    while True:
        if j >= len(src):
            raise AssertionError("stale_why_words(): an unterminated %s at offset %d: %r" % (form, i, src[i:i + 40]))
        c = src[j]
        if c == q:
            return "".join(out), j + 1
        if q == "`" and src.startswith("${", j):
            raise AssertionError("stale_why_words(): a template expression (a `${...}` substitution) at offset %d is no constant this reader can read: %r" % (i, src[i:i + 40]))
        if c == "\\":
            e = src[j + 1:j + 2]
            if e == "":
                raise AssertionError("stale_why_words(): an unterminated %s at offset %d (it ends in a backslash): %r" % (form, i, src[i:i + 40]))
            if e == "\n":
                j += 2
                continue   # a line continuation: nothing
            if e == "\r":
                j += 3 if src.startswith("\r\n", j + 1) else 2
                continue
            if e in _JS_SIMPLE_ESCAPES:
                out.append(_JS_SIMPLE_ESCAPES[e])
                j += 2
                continue
            if e == "x":
                h = src[j + 2:j + 4]
                if not re.fullmatch(r"[0-9a-fA-F]{2}", h):
                    raise AssertionError("stale_why_words(): a malformed \\x escape in a %s at offset %d: %r" % (form, i, src[i:i + 40]))
                out.append(chr(int(h, 16)))
                j += 4
                continue
            if e == "u":
                if src.startswith("{", j + 2):
                    k = src.find("}", j + 3)
                    h = src[j + 3:k] if k > 0 else ""
                    # the language bounds the VALUE, never the digit count (leading zeros are allowed): a value above 0x10FFFF is the
                    # malformed escape, and it raises the promised AssertionError here rather than a ValueError out of chr() (the
                    # maintainer's round 5, correctness-6)
                    if not re.fullmatch(r"[0-9a-fA-F]+", h) or int(h, 16) > 0x10FFFF:
                        raise AssertionError("stale_why_words(): a malformed \\u{} escape in a %s at offset %d: %r" % (form, i, src[i:i + 40]))
                    out.append(chr(int(h, 16)))
                    j = k + 1
                    continue
                h = src[j + 2:j + 6]
                if not re.fullmatch(r"[0-9a-fA-F]{4}", h):
                    raise AssertionError("stale_why_words(): a malformed \\u escape in a %s at offset %d: %r" % (form, i, src[i:i + 40]))
                out.append(chr(int(h, 16)))
                j += 6
                continue
            out.append(e)   # a non-escape character stands for itself (JavaScript's rule for \\a, \\d, ...)
            j += 2
            continue
        if c == "\n" and q != "`":
            raise AssertionError("stale_why_words(): a newline inside a %s at offset %d (unterminated): %r" % (form, i, src[i:i + 40]))
        out.append(c)
        j += 1


def _js_tokens(expr):
    """The expression as tokens: ("literal", value, text) for every string or template literal (every form, decoded by
    _js_literal), ("identifier", ...), ("number", ...) and ("punct", ...) for the rest, the multi-character punctuators
    kept whole so `?.` and `??` are never read as the ternary's `?`."""
    toks, i, n = [], 0, len(expr)
    while i < n:
        c = expr[i]
        if c.isspace():
            i += 1
            continue
        if c in _JS_FORMS:
            v, j = _js_literal(expr, i)
            toks.append(("literal", v, expr[i:j]))
            i = j
            continue
        if c.isalpha() or c in "_$":
            j = i + 1
            while j < n and (expr[j].isalnum() or expr[j] in "_$"):
                j += 1
            toks.append(("identifier", expr[i:j], expr[i:j]))
            i = j
            continue
        if c.isdigit():
            j = i + 1
            while j < n and (expr[j].isalnum() or expr[j] in "._"):
                j += 1
            toks.append(("number", expr[i:j], expr[i:j]))
            i = j
            continue
        for punct in _JS_PUNCT:
            if expr.startswith(punct, i):
                toks.append(("punct", punct, punct))
                i += len(punct)
                break
        else:
            toks.append(("punct", c, c))
            i += 1
    return toks


def ladder_words(expr):
    """The words of a flat conditional ladder, `cond ? value : cond ? value : ... : value`, in source order: each VALUE must
    be one string literal, in any form the language permits (a double-quoted or single-quoted string, a template literal
    without a substitution, any escape), decoded as the language reads it; a condition may hold anything (a literal there is
    no word). A value that is not one literal (an identifier, a member or other expression, a concatenation, a call, a
    number, an empty value, a template expression, an unterminated literal, a malformed escape) or a shape that is not a
    flat ladder raises an AssertionError naming the form, so the vocabulary pin reds naming what it could not read instead
    of passing over a word it never saw (the maintainer's round 4, extra7-2: an earlier reader collected double-quoted
    `[\\w-]+` literals alone, and a tenth word in any other form vanished from the derived list)."""
    toks = _js_tokens(expr)
    runs, cur, depth = [], [], 0
    for t in toks:
        if t[0] == "punct" and t[1] in "([{":
            depth += 1
        elif t[0] == "punct" and t[1] in ")]}":
            depth -= 1
        if depth == 0 and t[0] == "punct" and t[1] in ("?", ":"):
            runs.append((t[1], cur))
            cur = []
        else:
            cur.append(t)
    runs.append(("end", cur))
    n = len(runs)
    v = (n - 1) // 2
    if n < 3 or [d for d, _ in runs] != ["?", ":"] * v + ["end"]:
        raise AssertionError("stale_why_words(): the expression is not a flat conditional ladder (condition ? value : condition ? value : ... : value): its top-level delimiters read %r" % ([d for d, _ in runs],))
    values = [runs[k][1] for k in range(1, n - 1, 2)] + [runs[n - 1][1]]
    words = []
    for pos, run in enumerate(values, 1):
        if len(run) == 1 and run[0][0] == "literal":
            words.append(run[0][1])
            continue
        text = " ".join(t[2] for t in run)
        if not run:
            form = "an empty value"
        elif len(run) == 1:
            form = ("an " if run[0][0][0] in "aeiou" else "a ") + run[0][0]
        elif run[0][1] == "(":
            form = "a parenthesized expression"   # a nested ternary in parentheses among them: refused, and named for what it is, not as a call (the author's fixer pass after the maintainer's round 4, refusals-5)
        elif any(t[0] == "identifier" for t in run) and any(t[1] == "(" for t in run):
            form = "a call"
        elif any(t[1] == "+" for t in run):
            form = "a concatenation"
        else:
            form = "an expression of %d tokens" % len(run)
        raise AssertionError("stale_why_words(): the ladder's value %d of %d is %s, not one string literal (a double-quoted or single-quoted string, or a template literal without a substitution): %r; a value this reader cannot read is a refusal, never absence"
                             % (pos, len(values), form, text))
    return words


def stale_why_words():
    """The feedDelta-stale row's `why` vocabulary as federation.ts mints it: the value literals of the `const why = ...`
    ladder in applyRemoteFeedDelta (stale_why_expr), in source order (the order the conditions are tested in), read by
    ladder_words in every literal form the language permits, or None when the anchors are gone; a value the reader cannot
    read raises, naming the form (the maintainer's round 4, extra7-2). test_the_stale_rows_vocabulary_is_the_ladders holds
    this list to STALE_WHY_WORDS, test_the_vocabulary_reader_reads_every_literal_form_and_refuses_what_it_cannot pins the
    forms, and tests/test_federated_dial_terms_served.py's held_pair points here for the words the feed gate files."""
    expr = stale_why_expr()
    return ladder_words(expr) if expr is not None else None


def disclosure_copies():
    """The three disclosure copies in the tree, each as its text or None when the anchors are gone: the wsBytesByHost entry's
    comment in kernel.py (from the entry to the next surface), the minute-row entry's wsBytesByHost passage in docs/reference.md
    (from the field's sentence to rafGap's) and the ledger entry's body (after its front matter)."""
    root = os.path.dirname(HERE)
    ksrc = open(os.path.join(root, "kernel", "kernel.py"), encoding="utf-8").read()
    k = re.search(r'"wsBytesByHost"\)\),(.*?)"pane-shim": frozenset\(', ksrc, re.S)
    dsrc = open(os.path.join(root, "docs", "reference.md"), encoding="utf-8").read()
    d = re.search(r"`wsBytesByHost` is the same\n(.*?)`rafGap` is\n", dsrc, re.S)
    lsrc = open(os.path.join(root, "upstream", "2026-09-19-relay-dial-page-caps-ws-bytes-by-host.md"), encoding="utf-8").read()
    l = re.search(r"^---\n.*?\n---\n(.*)", lsrc, re.S)
    def flat(m):
        # one line per copy: the comment markers and the doc's wrapping are not part of the claim
        return re.sub(r"\s+", " ", re.sub(r"\n\s*#", " ", m.group(1))).strip() if m else None
    return {"kernel": flat(k), "docs": flat(d), "ledger": flat(l)}


def federation_grain_texts():
    """Every federation.ts text that states the positions' grain, flattened, keyed by site: the two-maps comment
    (maps_comment), the wsBytesByHost() and attachedHostOrdinals() docstrings, and the __rompFed publication comment in
    start() (the maintainer's round 3, regression-1, 2026-09-20: the grain pass left "over this page's life" at two of them and "attached to this page"
    at the third, against the maps declaration 800 lines above). A site whose anchors are gone reads None, so the phrase
    loop fails on it rather than passing on nothing."""
    root = os.path.dirname(HERE)
    fsrc = open(os.path.join(root, "ui", "webview", "federation.ts"), encoding="utf-8").read()
    def flat(m):
        return re.sub(r"\s+", " ", re.sub(r"\n\s*(//|\*)", " ", m.group(1))).strip() if m else None
    return {
        "maps": maps_comment(),
        "wsBytesByHost": flat(re.search(r"(/\*\* The text-frame characters received on each remote host's sockets.*?\*/)\s*wsBytesByHost\(\)", fsrc, re.S)),
        "attachedHostOrdinals": flat(re.search(r"(/\*\* The positions of the hosts attached.*?\*/)\s*attachedHostOrdinals\(\)", fsrc, re.S)),
        "publication": flat(re.search(r"\n(\s*// the characters each remote host's sockets delivered.*?)attachedHostOrdinals: \(\) => this\.attachedHostOrdinals\(\),", fsrc, re.S)),
    }


def maps_comment():
    """The federation manager's two-maps comment in federation.ts (from the field's header line to the first map's
    declaration), flattened to one line, or None when its anchors are gone. Not a disclosure copy (it states the maps, not
    the rule), but the copy a reader of the code meets first, so its reload sentence carries the docs' three conditions
    (the author's pass 3; the revision 14 read found it carrying one)."""
    root = os.path.dirname(HERE)
    fsrc = open(os.path.join(root, "ui", "webview", "federation.ts"), encoding="utf-8").read()
    m = re.search(r"// wsBytesByHost \(2026-09-19;(.*?)\n\s*private hostOrdinal = ", fsrc, re.S)
    return re.sub(r"\s+", " ", re.sub(r"\n\s*//", " ", m.group(1))).strip() if m else None


def federation_fixture_rows(host):
    """One synthetic row per federation.ts diag() call site (hostconn's events, then the others), the shapes the WRITERS post:
    re-minted from the source in the author's pass after the maintainer's round 4 (its extra7-1 and extra9-1: the hold
    row carried a KERNEL_SETTING type where a hold can carry only a BOOKKEEPING one, and the senddrop row posted a `why` no
    writer sends, "closed", on a type the why-carrying arm never drops). test_the_federation_fixture_rows_are_shapes_the_writers_post
    holds these rows to the writers' literals and tables."""
    return [
        ("hostconn", {"host": host, "ev": "watchdog-close", "why": "quiet", "quietMs": 31000, "foreground": True}),
        ("hostconn", {"host": host, "ev": "dial-deferred", "why": "local-down"}),   # a relay dial put off while the pane's local socket is down (2026-09-18)
        ("hostconn", {"host": host, "ev": "hold", "msgType": "activeTab", "rs": 0}),   # a bookkeeping frame held for the open: its type is a BOOKKEEPING key (federation.ts, the hold arm)
        ("hostconn", {"host": host, "ev": "flush-halt", "flushed": ["setAutoNudge"], "held": ["setJudgeModel"]}),
        ("hostconn", {"host": host, "ev": "tunnels-poll-failing", "why": "http", "unread": True}),   # unread is !this.hostsRead, a boolean (federation.ts); the earlier fixture posted a count
        ("hostconn", {"host": host, "ev": "tunnels-poll-recovered", "unread": False, "endedUnread": True}),   # both booleans: !this.hostsRead and firstRead
        ("hostconn", {"host": host, "ev": "open", "flushed": ["setAutoNudge"]}),
        ("hostconn", {"host": host, "ev": "close", "code": 1006, "clean": False, "detached": False}),
        ("hostconn", {"host": host, "ev": "detach", "pendingDropped": ["setAutoNudge", "needFull"]}),
        ("hostconn", {"host": host, "ev": "moot", "pendingDropped": ["needFull", "needFull"]}),   # the held asks the ready's connect push answers, dropped before the flush, by type (2026-09-18)
        ("hostconn", {"host": host, "ev": "delta-unknown-slot", "why": "lanes"}),   # a remote patch for a slot the conn's receiver has no table for (2026-09-19)
        ("hostconn", {"host": host, "ev": "delta-unkeyed-base", "why": "bars judging dictlist:k is a list @a1b2c3d4e"}),   # a remote's patch that found no base because its whole frame was refused as one (a collection the receiver's table cannot key): the slot, the collection and shape, and the remote's build when the /tunnels row names one; once per distinct row (2026-09-19)
        ("feedDelta-nobase", {"host": host, "buildId": 7}),
        ("feedDelta-nobase", {"host": "local", "buildId": 7}),   # the local socket's frame with no base: the LOCAL kernel's counter (the census, federation.buildId)
        ("feedDelta-stale", {"host": host, "buildId": 7, "why": "gen"}),   # a stamped remote feedDelta refused by the gen gate: the ask carries the held pair (2026-09-19). The why is one of STALE_WHY_WORDS (a word per field failure, a word per relation between valid fields); each is driven in test_the_stale_rows_why_words_pass_whole_and_a_foreign_key_on_the_row_is_dropped
        ("feedDelta-apply", {"host": host, "buildId": 7, "why": "asked", "road": "wire"}),   # a remote feedDelta whose apply threw: refused with one bare needFullFeed (the maintainer's round 5, refusals-2; federation.ts refuseRemoteApply)
        ("feedDelta-apply", {"host": host, "buildId": 8, "why": "stopped", "road": "wire"}),   # a throw after the answering full landed: the asking stopped, the shell told once
        ("feedDelta-apply", {"host": "local", "buildId": 7, "why": "asked", "road": "local"}),   # the local road's twin (refuseLocalApply): the LOCAL kernel's counter, the word local under host
        ("feedDelta-apply", {"host": "local", "buildId": 8, "why": "stopped", "road": "local"}),
        ("feedmerge", {"counts": {host: 4}}),
        ("sendqueue", {"host": host, "msgType": "setAutoNudge", "gt": 1700000000002, "rs": 0, "superseded": True}),   # an older emitter's pick replaced: no numeric gt
        ("sendqueue", {"host": host, "msgType": "setJudgeModel", "gt": 1700000000002, "rs": 0, "superseded": 1700000000001}),   # a stamped pick replaced: its gesture-clock stamp
        ("senddrop", {"host": host, "msgType": "activeTab", "why": "no-conn"}),   # the bookkeeping arm: a host this page holds no conn for (federation.ts; federation-send-queue.test.ts pins the row)
        ("senddrop", {"host": host, "msgType": "prompt"}),   # the default drop: the outbound gesture's own type, no why (federation.ts, the last arm of sendRemote)
    ]


def fed_src():
    return open(os.path.join(os.path.dirname(HERE), "ui", "webview", "federation.ts"), encoding="utf-8").read()


def federation_writer_tables():
    """The tables and literals federation.ts's hold, sendqueue and senddrop writers draw their fields from, read off the source:
    the KERNEL_SETTING set, the BOOKKEEPING map's keys, and the literal object of every senddrop and hold call site (its
    keys, and the `why` literal where it carries one). Empty reads fail loudly in the test that calls this."""
    src = open(os.path.join(os.path.dirname(HERE), "ui", "webview", "federation.ts"), encoding="utf-8").read()
    ks = re.search(r"const KERNEL_SETTING = new Set\(\[(.*?)\]\);", src, re.S)
    kernel_setting = set(re.findall(r'"([A-Za-z]+)"', ks.group(1))) if ks else set()
    bk = re.search(r"export const BOOKKEEPING: ReadonlyMap.*?= new Map.*?\(\[\n(.*?)\n\]\);", src, re.S)
    bookkeeping = set(re.findall(r'^\s*\["([A-Za-z]+)",', bk.group(1), re.M)) if bk else set()
    sites = []
    for what, body in re.findall(r'this\.diag\("(senddrop|hostconn)", \{ (host[^}]*?) \}\)', src):
        keys = tuple(re.findall(r'(?:^|, )([A-Za-z]+)(?=:|,|$)', body))   # a shorthand key (host) or a keyed one (msgType: ...), the terminator left for the next
        why = re.search(r'why: "([^"]+)"', body)
        ev = re.search(r'ev: "([^"]+)"', body)
        sites.append((what, ev.group(1) if ev else None, keys, why.group(1) if why else None))
    return kernel_setting, bookkeeping, sites


class ClientDiagAllowlistTest(unittest.TestCase):
    def setUp(self):
        # A private state root (T282): km.jd is the judge module every test module shares, and its STATE is whatever
        # the last module left. A minted state root pins per-session hosts off (the repo rule of 2026-09-11).
        self._saved_state = km.jd.STATE
        self._td = tempfile.TemporaryDirectory()
        root = pathlib.Path(self._td.name)
        (root / "session-hosts").write_text("off\n", encoding="utf-8")
        km.jd._rebind_state(root)
        self.fp = km.jd.STATE / "client-diag.jsonl"
        km._client_diag_said.clear()    # the once-per-kernel stderr latch: each test is its own kernel

    def tearDown(self):
        km._client_diag_said.clear()
        km.jd._rebind_state(self._saved_state)
        self._td.cleanup()

    def post(self, surface, what, data):
        """One row through the real dispatch, the way a pane's shim delivers it; returns what the kernel said on stderr."""
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            km.Handler._dispatch_ws(None, {"type": "clientDiag", "surface": surface, "what": what, "data": data}, {"wid": WID})
        return err.getvalue()

    def rows(self):
        return [json.loads(line) for line in self.fp.read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_the_constants_and_the_table(self):
        self.assertEqual(km.CLIENT_DIAG_STR_MAX, 64)
        self.assertEqual(km.CLIENT_DIAG_ROW_MAX, 24 * 1024, "above the collector's worst case (test_the_collectors_worst_case_minute_row_is_stored_whole)")
        self.assertEqual(sorted(km.CLIENT_DIAG_KEYS), ["chat", "federation", "feed", "kernel", "outline", "pane-shim", "perf", "reload-core", "shell", "strip", "waiting"])
        for surface, keys in km.CLIENT_DIAG_KEYS.items():
            self.assertIsInstance(keys, frozenset, surface)
            self.assertTrue(all(isinstance(k, str) and k for k in keys), surface)
        self.assertTrue(set(MINUTE) <= km.CLIENT_DIAG_KEYS["perf"], "every key of today's minute row is admitted")
        self.assertTrue(set(SHARED) <= km.CLIENT_DIAG_KEYS["perf"], "and every shared field")
        self.assertTrue({"app", "type", "ms", "dom", "loaf"} <= km.CLIENT_DIAG_KEYS["perf"], "the slowframe row's keys")
        self.assertEqual(km.CLIENT_DIAG_MINUTE_SHED, ("wsBytesByHost", "frames", "loaf", "free", "slow"),
                         "the uncapped map first and whole, then the per-minute figures largest first (the ladder test)")
        self.assertTrue(set(km.CLIENT_DIAG_MINUTE_SHED) <= km.CLIENT_DIAG_KEYS["perf"])
        self.assertEqual(km.CLIENT_DIAG_SAID_MAX, 512)
        self.assertEqual(km.CLIENT_DIAG_ROW_SAY_MAX, 8, "the foreign keys of one row said by name; the rest are counted in one line")
        self.assertEqual(km.CLIENT_DIAG_CUT_KEY, "cut", "the value-loss marker's key (the author's pass 4)")
        for marker in (km.CLIENT_DIAG_CUT_KEY, "capped"):
            for surface, keys in km.CLIENT_DIAG_KEYS.items():
                self.assertNotIn(marker, keys, "%s: a kernel-written marker is admitted from no poster, or a page could forge one" % surface)

    def assert_shorthand_shapes(self, surface, what, data):
        """Every value a fixture posts under a census row whose reason is a shorthand (_INT, _BOOL, _ENUM) has that shape
        (the author's pass-4 fixer pass, 2026-09-20): the header's claim that the fixture rows check the shorthand reasons had been
        satisfied by no assertion (the pass-whole loop compares the stored row to the posted one and reads no shape), and
        three chat values contradicted their rows green. A bool is an int in Python, so a number must not be one."""
        for key, value in data.items():
            reason = CENSUS[surface][key][1]
            if reason == _INT:
                ok = isinstance(value, (int, float)) and not isinstance(value, bool)
            elif reason == _BOOL:
                ok = isinstance(value, bool)
            elif reason == _ENUM:
                ok = isinstance(value, str)
            else:
                continue
            self.assertTrue(ok, "%s %s: the census says %s is %s; the fixture posts %r" % (surface, what, key, reason, value))

    def test_todays_rows_pass_whole_and_quietly(self):
        todays = [
            ("perf", "minute", MINUTE),
            ("perf", "slowframe", {"app": "chat", "type": "session", "ms": 150.2, "dom": 53306, "loaf": {"ms": 160, "blocking_ms": 110, "top": []}}),
            ("pane-shim", "wsclose", {"app": "feed", "code": 1006, "reason": "", "wasClean": False, "sinceOpenMs": 5000, "quietMs": 31000, "everConnected": True, "bundleReady": True}),
            ("pane-shim", "return", {"decision": "redial-closed", "resumed": False, "hiddenMs": 29000, "frozenMs": 0, "quietMs": 29500, "quietAtResumeMs": -1, "ready": 3, "app": "chat", "resent": True}),
            ("pane-shim", "return-fresh", {"ms": 5600, "bytesSince": 40000, "redialed": True, "app": "chat"}),
            ("pane-shim", "wsconnfail", {"app": "chat", "attempts": 3, "firstFailMs": 30000}),
            ("pane-shim", "page-load", {"wasDiscarded": True, "nav": "reload", "app": "feed"}),
            ("pane-shim", "watchdog-close", {"app": "feed", "why": "quiet", "ready": 1, "quietMs": 31000, "hidden": False}),
            # the reload core's two writers of owed (the census, reload-core.reason): accept's row names the build with the
            # offer's dist token, demand's names required with the frame's why (empty here); the hold is busy()'s word, a
            # sibling field whose vocabulary the earlier fixture had posted as the reason, a value no writer sends
            ("reload-core", "held", {"reason": "build", "detail": "1757100000", "hold": "fresh", "ageMs": 61000}),
            ("reload-core", "held", {"reason": "required", "detail": "", "hold": "sends", "ageMs": 61000}),
        ]
        err = ""
        for surface, what, data in todays:
            err += self.post(surface, what, data)
            self.assert_shorthand_shapes(surface, what, data)
        self.assertEqual(err, "", "nothing dropped, nothing said")
        rows = self.rows()
        self.assertEqual(len(rows), 10)
        self.assertEqual(sorted(rows[0]), ["data", "reconnect", "surface", "t", "what", "wid"], "the row's own shape is unchanged")
        self.assertEqual(rows[0]["data"], MINUTE)
        self.assertEqual(rows[2]["data"]["reason"], "")
        self.assertEqual(rows[3]["data"]["resent"], True)

    def test_the_shell_led_return_keys_pass_whole(self):
        # D3 (2026-09-18): the pane's return awaits the shell's link (return.awaitLink) and its return-fresh carries
        # the path's own recovery (return-fresh.linkUpMs); the shell socket's return-probe is a fixed-shape row.
        err = self.post("pane-shim", "return", {"decision": "redial-closed", "resumed": False, "hiddenMs": 195000,
                                                 "frozenMs": 0, "quietMs": 195500, "quietAtResumeMs": -1, "ready": 3,
                                                 "app": "chat", "awaitLink": True})
        err += self.post("pane-shim", "return-fresh", {"ms": 1200, "bytesSince": 40000, "redialed": True,
                                                       "linkUpMs": 900, "app": "chat"})
        err += self.post("shell", "return-probe", {"decision": "redial-closed", "hiddenMs": 195000, "quietMs": 195500,
                                                   "attempts": 2, "firstFailMs": 12500, "ms": 33000})
        self.assertEqual(err, "", "the D3 keys are admitted whole (awaitLink, linkUpMs, and the shell return-probe)")
        rows = self.rows()
        self.assertIs(rows[-3]["data"]["awaitLink"], True)
        self.assertEqual(rows[-2]["data"]["linkUpMs"], 900)
        self.assertEqual(rows[-1]["data"]["decision"], "redial-closed")

    def test_the_parked_return_keys_pass_whole(self):
        # D2 (2026-09-18): a pane off screen on the phone parks its return redial (return.parked, true; false on a return
        # that did not park in a shell that told a word) and the return-fresh that answers its tap says so too
        # (return-fresh.parked, beside D3's linkUpMs). A bool, approved field by field; the one key this change adds.
        err = self.post("pane-shim", "return", {"decision": "redial-closed", "resumed": False, "hiddenMs": 181000,
                                                 "frozenMs": 0, "quietMs": 181500, "quietAtResumeMs": -1, "ready": 3,
                                                 "app": "files", "parked": True})
        err += self.post("pane-shim", "return-fresh", {"ms": 800, "bytesSince": 240000, "redialed": True,
                                                       "linkUpMs": 0, "parked": True, "app": "files"})
        err += self.post("pane-shim", "return", {"decision": "redial-closed", "resumed": False, "hiddenMs": 181000,
                                                 "frozenMs": 0, "quietMs": 181500, "quietAtResumeMs": -1, "ready": 3,
                                                 "app": "chat", "awaitLink": True, "parked": False})
        self.assertEqual(err, "", "the parked key is admitted whole on the return and return-fresh rows")
        rows = self.rows()
        self.assertIs(rows[-3]["data"]["parked"], True)
        self.assertIs(rows[-2]["data"]["parked"], True)
        self.assertEqual(rows[-2]["data"]["linkUpMs"], 0)
        self.assertIs(rows[-1]["data"]["parked"], False)
        self.assertIn("parked", km.CLIENT_DIAG_KEYS["pane-shim"])
        for surface in ("shell", "federation", "chat", "perf", "reload-core"):
            self.assertNotIn("parked", km.CLIENT_DIAG_KEYS[surface], "the key is the pane-shim surface's alone")

    def test_every_surface_in_the_table_admits_every_key_it_names(self):
        for surface, keys in sorted(km.CLIENT_DIAG_KEYS.items()):
            data = {k: i for i, k in enumerate(sorted(keys))}
            if surface == "kernel":
                # the kernel's own surface: the handler refuses a page's row under it (the test below), so the entry is
                # checked at the admit step alone; it names the keys the kernel's own writers use
                self.assertEqual(km._client_diag_admit(surface, data), data)
                continue
            err = self.post(surface, "probe", data)
            self.assertEqual(err, "", surface)
            self.assertEqual(self.rows()[-1]["data"], data, surface)

    def test_the_shared_fields_pass_and_an_unknown_key_is_dropped_and_said_once(self):
        data = dict(MINUTE, **SHARED)
        data["typed"] = "what the user wrote"
        data["sid"] = "11111111-2222-3333-4444-555555555555"
        err = self.post("perf", "minute", data)
        row = self.rows()[0]["data"]
        self.assertEqual(row, dict(MINUTE, **SHARED), "the admitted keys, the shared fields among them; the two foreign keys gone")
        lines = [l for l in err.splitlines() if l]
        self.assertEqual(len(lines), 2, err)
        self.assertTrue(any("'typed'" in l and "'perf'" in l for l in lines), err)
        self.assertTrue(any("'sid'" in l for l in lines), err)
        self.assertTrue(all(l.startswith("[client-diag] dropping a key the surface's allowlist does not admit") for l in lines), err)
        # the same keys again, from another minute: said already
        self.assertEqual(self.post("perf", "minute", data), "")
        # a different foreign key: its own line, once
        self.assertEqual(len(self.post("perf", "minute", dict(MINUTE, other_thing=1)).splitlines()), 1)
        self.assertEqual(self.post("perf", "minute", dict(MINUTE, other_thing=2)), "")
        self.assertEqual(len(self.rows()), 4)

    def test_strings_are_cut_at_the_cap_at_any_depth_and_the_row_carries_the_cut_marker_said_once(self):
        # the cut is the standing rule; since the author's pass 4 (2026-09-20) it is never silent: the row carries CLIENT_DIAG_CUT_KEY
        # naming the admitted keys a value was cut under, and the kernel says so once per surface and key, as it says a
        # dropped key, so a stored value can be told from a whole one (a cut string looked like a whole one to every reader)
        long = "x" * 200
        err = self.post("pane-shim", "wsclose", {"app": "feed", "code": 1006, "reason": long, "wasClean": False, "sinceOpenMs": 1, "quietMs": 1, "everConnected": True, "bundleReady": True})
        row = self.rows()[-1]["data"]
        self.assertEqual(row["reason"], "x" * 64)
        self.assertEqual(row["code"], 1006)
        self.assertIs(row["wasClean"], False)
        self.assertEqual(row[km.CLIENT_DIAG_CUT_KEY], ["reason"], "the marker names the key the cut happened under")
        lines = [l for l in err.splitlines() if l]
        self.assertEqual(len(lines), 1, err)
        self.assertIn("key 'reason', cut", lines[0])
        self.assertIn("a string over 64 characters is stored as its first 64", lines[0])
        self.assertIn("the row's cut key names it", lines[0])
        self.assertEqual(self.post("pane-shim", "wsclose", {"app": "feed", "code": 1006, "reason": long, "wasClean": False, "sinceOpenMs": 1, "quietMs": 1, "everConnected": True, "bundleReady": True}), "",
                         "said once per surface and key: the latch's budget, the one a dropped key spends")
        self.assertEqual(self.rows()[-1]["data"][km.CLIENT_DIAG_CUT_KEY], ["reason"], "the marker rides every such row, said or not")
        nested = dict(MINUTE, loaf={"n": 1, "blocking_ms": 1, "worst_ms": 1, "src": "loaf",
                                    "top": [{"k": "a" * 100, "ms": 1, "n": 1, "inv": "b" * 70}]})
        err = self.post("perf", "minute", nested)
        d = self.rows()[-1]["data"]
        top = d["loaf"]["top"][0]
        self.assertEqual(top["k"], "a" * 64)
        self.assertEqual(top["inv"], "b" * 64)
        self.assertEqual(top["ms"], 1)
        self.assertEqual(d[km.CLIENT_DIAG_CUT_KEY], ["loaf"], "a nested cut is attributed to the top-level admitted key (the scrub sees no key)")
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("'perf'", err); self.assertIn("key 'loaf', cut", err)
        # the dict's own keys are not values and stay whole (the row cap bounds them); null stays null; and a row nothing
        # was cut under carries no marker and says nothing
        self.assertEqual(self.post("perf", "minute", dict(MINUTE, frames={"k" * 70: {"n": 1}}, free=None)), "")
        d = self.rows()[-1]["data"]
        self.assertEqual(list(d["frames"]), ["k" * 70])
        self.assertIsNone(d["free"])
        self.assertNotIn(km.CLIENT_DIAG_CUT_KEY, d, "no value was cut: no marker")
        # a poster's own key of the marker's name is a foreign key: dropped and said as one, never stored as a marker, and the
        # kernel's marker wins the name on a row that was cut
        err = self.post("federation", "senddrop", {"host": "TESTHOST", "msgType": "activeTab", "why": "no-conn", km.CLIENT_DIAG_CUT_KEY: ["host"]})   # the writer's row (the bookkeeping arm) plus a forged marker
        self.assertNotIn(km.CLIENT_DIAG_CUT_KEY, self.rows()[-1]["data"], "the forged marker is dropped")
        self.assertIn("dropping a key the surface's allowlist does not admit", err); self.assertIn("'%s'" % km.CLIENT_DIAG_CUT_KEY, err)
        self.post("federation", "senddrop", {"host": "TESTHOST", "msgType": "activeTab", "why": "w" * 65, km.CLIENT_DIAG_CUT_KEY: ["host"]})   # the same row with a why over the cap (no writer sends one: the cut is the subject here)
        self.assertEqual(self.rows()[-1]["data"][km.CLIENT_DIAG_CUT_KEY], ["why"], "the kernel's list, not the poster's")

    def test_nesting_past_the_depth_cap_reads_null_and_the_row_carries_the_cut_marker(self):
        deep = 1
        for _ in range(20):
            deep = [deep]
        err = self.post("perf", "minute", dict(MINUTE, frames=deep))
        d = self.rows()[-1]["data"]
        v = d["frames"]
        depth = 0
        while isinstance(v, list):
            v = v[0]
            depth += 1
        self.assertIsNone(v)
        self.assertEqual(depth, km.CLIENT_DIAG_DEPTH_MAX, "lists at depths 0 to the cap less one, then null")
        self.assertEqual(d[km.CLIENT_DIAG_CUT_KEY], ["frames"], "a nulled nesting is a value loss too: the marker names the key (the maintainer's round 3, extra7-1)")
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("a value nested past depth 8 is stored as null", err)
        # a value of no JSON type is the third loss the scrub records; unreachable on the posted road (its data is json.loads
        # output), so driven at the admit step alone
        losses = []
        self.assertIsNone(km._client_diag_scrub(object(), losses))
        self.assertEqual(losses, ["type"])
        km._client_diag_said.clear()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = km._client_diag_admit("perf", {"app": "chat", "dom": object()})
        self.assertEqual(out, {"app": "chat", "dom": None, km.CLIENT_DIAG_CUT_KEY: ["dom"]})
        self.assertIn("a value of no JSON type is stored as null", err.getvalue())

    def test_a_row_over_the_cap_is_stored_capped_with_its_surface_and_what_and_said_once(self):
        # a slowframe row whose long-frame report grew past the cap, a shape the collector never builds (its top is five
        # entries): the marker is the backstop for a row no first-party poster sends (the minute row has its own rule, below)
        big = {"app": "chat", "type": "session", "ms": 150.2, "dom": 53306,
               "loaf": {"ms": 160, "blocking_ms": 110, "top": [{"k": "render.js:paint%03d@9000" % i, "ms": 1, "n": 1, "inv": "WebSocket.onmessage"} for i in range(400)]}}
        self.assertGreater(len(json.dumps(big)), km.CLIENT_DIAG_ROW_MAX)
        err = self.post("perf", "slowframe", big)
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("is stored capped", err)
        row = self.rows()[-1]
        self.assertEqual(row["surface"], "perf")
        self.assertEqual(row["what"], "slowframe")
        self.assertEqual(row["wid"], WID)
        self.assertIn("reconnect", row)
        self.assertEqual(sorted(row["data"]), ["app", "bytes", "capped"], "the marker keeps the pane, so the row still groups under it (review find, 2026-09-18)")
        self.assertEqual(row["data"]["app"], "chat")
        self.assertIs(row["data"]["capped"], True)
        self.assertGreater(row["data"]["bytes"], km.CLIENT_DIAG_ROW_MAX)
        self.assertLess(len(json.dumps(row)), 400, "the stored row is small")
        self.assertEqual(self.post("perf", "slowframe", big), "", "said once per surface and what")
        self.assertEqual(len(self.post("perf", "probe", big).splitlines()), 1, "another what: its own line")
        # a row with no string app takes the bare marker
        self.post("pane-shim", "probe", {"code": [1] * 20000, "app": 7})
        self.assertEqual(sorted(self.rows()[-1]["data"]), ["bytes", "capped"], "app is kept only where the poster sent a string")
        # a row just under the cap passes whole: frame types added until one more would not fit
        env = {"t": 1700000000, "wid": WID, "surface": "perf", "what": "minute", "reconnect": False}
        frames = {}
        while True:
            more = dict(frames, **{"type%03d" % len(frames): {"n": len(frames), "hist": [0] * 14}})
            if len(json.dumps(dict(env, data=dict(MINUTE, frames=more)))) > km.CLIENT_DIAG_ROW_MAX:
                break
            frames = more
        near = dict(MINUTE, frames=frames)
        line = json.dumps(dict(env, data=near))
        self.assertLess(len(line), km.CLIENT_DIAG_ROW_MAX)
        self.assertGreater(len(line), km.CLIENT_DIAG_ROW_MAX - 100, "within one frame entry of the bound")
        self.assertEqual(self.post("perf", "minute", near), "")
        self.assertEqual(self.rows()[-1]["data"], near)

    def test_a_minute_row_over_the_cap_sheds_its_frames_and_keeps_the_once_per_page_fields(self):
        # a first shared minute over the bound: the row the whole-row marker used to swallow, and with it nav, res, marks
        # and env for the page's life, since the collector sends them once (review find, 2026-09-18). The bound now sits
        # above the collector's own worst case (the test below), so this shape (260 frame types) is one no collector
        # builds; the shed is the backstop. Under pressure the ladder sheds the uncapped map first whatever the cause (the
        # ladder test), so this row's two-position map goes before its frames
        frames = {("fed:" if i % 2 else "") + "type%03d" % i: {"n": 12 + i, "ms_sum": 340.5 + i, "ms_max": 88.1, "n16": 5, "n100": 1, "hist": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]} for i in range(260)}
        res = {"bundle%02d.js" % i: {"transferSize": 120000 + i, "encodedBodySize": 119700 + i, "duration": 88 + i} for i in range(24)}
        res["other"] = {"transferSize": 600, "encodedBodySize": 400, "duration": 45}   # MAX_RES named entries and the fold, as the collector builds it
        shared = dict(SHARED, res=res)
        data = dict(MINUTE, frames=frames, **shared)
        line = json.dumps({"t": 1700000000, "wid": WID, "surface": "perf", "what": "minute", "reconnect": False, "data": data})
        self.assertGreater(len(line), km.CLIENT_DIAG_ROW_MAX, "the fixture is over the cap as posted")
        err = self.post("perf", "minute", data)
        row = self.rows()[-1]
        d = row["data"]
        self.assertNotIn("frames", d, "the largest per-minute figure is shed")
        self.assertNotIn("wsBytesByHost", d, "the uncapped map is shed first, whatever took the row over")
        self.assertEqual(d["capped"], {"bytes": len(line), "dropped": ["wsBytesByHost", "frames"]}, "the marker names what was shed, in ladder order, and the line's bytes before")
        for k in ("nav", "res", "marks", "env"):
            self.assertEqual(d[k], shared[k], k)
        for k in ("app", "since", "span_ms", "dom", "visible", "hidden_pane", "ua", "heap_mb", "vis", "wsBytes", "rafGap", "loaf", "free", "slow"):
            self.assertEqual(d[k], data[k], "%s stays: the shed stops once the line fits" % k)
        self.assertLessEqual(len(json.dumps(row)), km.CLIENT_DIAG_ROW_MAX)
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("stored without some of its keys (its capped key names them)", err, "worded for the ladder as a whole: the map alone may be what went (the maintainer's round 3, kernel-1)")
        self.assertNotIn("per-minute figures", err)
        self.assertEqual(self.post("perf", "minute", data), "", "said once per surface and what")
        # a minute whose long-frame report is big too: frames goes first, then loaf; free, slow and the shared fields stay
        loaf = {"n": 320, "blocking_ms": 900, "worst_ms": 200, "src": "loaf",
                "top": [{"k": "render.js:paint%03d@9000" % i, "ms": 90, "n": 1, "inv": "WebSocket.onmessage"} for i in range(320)]}
        self.post("perf", "minute", dict(MINUTE, frames=frames, loaf=loaf, **shared))
        d = self.rows()[-1]["data"]
        self.assertEqual(d["capped"]["dropped"], ["wsBytesByHost", "frames", "loaf"])
        self.assertNotIn("loaf", d)
        self.assertEqual(d["free"], MINUTE["free"])
        self.assertEqual(d["slow"], MINUTE["slow"])
        self.assertEqual(d["res"], res)
        self.assertLessEqual(len(json.dumps(self.rows()[-1])), km.CLIENT_DIAG_ROW_MAX)
        # a minute row that does not fit even without all four (a resource fold no collector builds) takes the whole-row marker
        wide = {"asset%03d.js" % i: {"transferSize": 100000 + i, "encodedBodySize": 99000 + i, "duration": 88} for i in range(400)}
        err = self.post("perf", "minute", dict(MINUTE, **dict(SHARED, res=wide)))
        d = self.rows()[-1]["data"]
        self.assertEqual(sorted(d), ["app", "bytes", "capped"])
        self.assertEqual(d["app"], "chat")
        self.assertIs(d["capped"], True)
        self.assertIn("is stored capped", err)
        # the shed is the minute row's alone: a slowframe row over the cap takes the marker whole (the test above)

    def test_a_long_surface_is_cut_once_for_the_row_the_lookup_and_the_stderr_line(self):
        # before the fix the allowlist lookup and the latch read the uncut string: a 200-character surface was printed whole
        # via %r, and every distinct spelling grew the latch (review find, 2026-09-18)
        err = self.post("s" * 200, "probe", {"a": 1})
        row = self.rows()[-1]
        self.assertEqual(row["surface"], "s" * 64)
        self.assertEqual(row["data"], {})
        lines = err.splitlines()
        self.assertEqual(len(lines), 1, err)
        self.assertIn("'%s'" % ("s" * 64), lines[0])
        self.assertNotIn("s" * 65, lines[0], "the stderr line carries the cut surface, never the 200 characters")
        self.assertIn(("s" * 64, "key 'a'"), km._client_diag_said, "the latch holds the cut surface")
        self.assertEqual(self.post("s" * 300, "probe", {"a": 2}), "", "another long spelling of the same 64 characters is the same latch entry")
        self.assertEqual(len(km._client_diag_said), 1)
        # a surface that is not a string reads as its str(), cut the same way
        err = self.post({"k": "v" * 200}, "probe", {"a": 1})
        self.assertEqual(self.rows()[-1]["surface"], str({"k": "v" * 200})[:64])
        self.assertLess(max(len(l) for l in err.splitlines()), 200)

    def test_one_row_with_many_foreign_keys_has_a_handful_said_and_the_rest_counted(self):
        # one row with 600 foreign keys used to print 513 lines and spend the whole latch, so every other surface was
        # silent for the kernel's life (review find, 2026-09-18); now a row has at most CLIENT_DIAG_ROW_SAY_MAX of its keys
        # said by name and one line counting the rest, every key still dropped
        n = km.CLIENT_DIAG_ROW_SAY_MAX
        foreign = {"zz%03d" % i: i for i in range(600)}
        err = self.post("perf", "minute", dict(MINUTE, **foreign))
        lines = err.splitlines()
        self.assertEqual(len(lines), n + 1, err)
        for i in range(n):
            self.assertIn("key 'zz%03d'" % i, lines[i], "the row's first keys, in its order")
            self.assertIn("dropping a key the surface's allowlist does not admit", lines[i])
        self.assertIn("and %d more keys dropped from one row, unnamed" % (600 - n), lines[-1])
        self.assertEqual(len(km._client_diag_said), n + 1, "the named keys and the counting line: a handful of the latch, not all of it")
        self.assertEqual(self.rows()[-1]["data"], MINUTE, "every foreign key is dropped regardless")
        # a second surface still says (the line the old pin held silent)
        self.assertEqual(len(self.post("mystery", "probe", {"q": 1}).splitlines()), 1, "one wide row did not spend the latch")
        # another wide row on the same surface: its first keys are new and are named; the counting line is said once per surface
        more = {"yy%03d" % i: i for i in range(100)}
        lines = self.post("perf", "minute", dict(MINUTE, **more)).splitlines()
        self.assertEqual(len(lines), n, lines)
        self.assertTrue(all("key 'yy" in l for l in lines), lines)
        # the same wide row again: every named key is latched, the counting line too
        self.assertEqual(self.post("perf", "minute", dict(MINUTE, **more)), "")
        # the same bound on a surface no allowlist names
        lines = self.post("nowhere", "probe", {"k%03d" % i: i for i in range(50)}).splitlines()
        self.assertEqual(len(lines), n + 1, lines)
        self.assertTrue(all("a surface no allowlist names" in l for l in lines[:-1]), lines)
        self.assertIn("and %d more keys" % (50 - n), lines[-1])

    def test_the_stderr_latch_is_bounded_and_says_so_once(self):
        # a flood of distinct pairs across rows: the latch holds CLIENT_DIAG_SAID_MAX, one closing line, then silence
        for i in range(600):
            err = self.post("perf", "minute", dict(MINUTE, **{"zz%03d" % i: i}))
            if i < km.CLIENT_DIAG_SAID_MAX:
                self.assertEqual(len(err.splitlines()), 1, (i, err))
                self.assertIn("dropping a key", err)
            elif i == km.CLIENT_DIAG_SAID_MAX:
                self.assertEqual(len(err.splitlines()), 1, (i, err))
                self.assertIn("nothing more is said", err)
            else:
                self.assertEqual(err, "", (i, err))
        self.assertEqual(len(km._client_diag_said), km.CLIENT_DIAG_SAID_MAX + 1, "the pairs and the latch's own entry")
        self.assertEqual(len(self.rows()), 600, "every row lands regardless")
        self.assertEqual(self.rows()[-1]["data"], MINUTE)
        # more foreign keys, another surface, a capped row: nothing more is said and the latch does not grow
        self.assertEqual(self.post("perf", "minute", dict(MINUTE, another=1)), "")
        self.assertEqual(self.post("mystery", "probe", {"q": 1}), "")
        big = {"app": "chat", "type": "x", "ms": 1, "loaf": {"top": [{"k": "render.js:paint%03d@9000" % i, "ms": 1, "n": 1, "inv": "WebSocket.onmessage"} for i in range(400)]}}
        self.assertGreater(len(json.dumps(big)), km.CLIENT_DIAG_ROW_MAX)
        self.assertEqual(self.post("perf", "slowframe", big), "")
        self.assertEqual(sorted(self.rows()[-1]["data"]), ["app", "bytes", "capped"], "the cap still applies, unsaid")
        self.assertEqual(len(km._client_diag_said), km.CLIENT_DIAG_SAID_MAX + 1)

    def test_a_page_row_under_the_kernels_surface_is_refused_and_said_once(self):
        # the table admitted surface kernel from a page, so a forged wsopen landed indistinguishable from the kernel's own
        # rows (_note_ws_open and its siblings write those directly, never through the handler); the handler now refuses
        # it, said once per what (review find, 2026-09-18). The table keeps the entry: it names the kernel's own keys.
        forged = {"app": "chat", "kind": "page", "iid": "forged", "reconnect": False}
        err = self.post("kernel", "wsopen", forged)
        self.assertFalse(self.fp.exists(), "no row: the file is not even created")
        lines = err.splitlines()
        self.assertEqual(len(lines), 1, err)
        self.assertIn("refusing a page's row under the kernel's own surface", lines[0])
        self.assertIn("surface 'kernel', what 'wsopen'", lines[0])
        self.assertEqual(self.post("kernel", "wsopen", forged), "", "said once per what")
        self.assertEqual(len(self.post("kernel", "historyReply", {"sid": "11111111-2222-3333-4444-555555555555"}).splitlines()), 1, "another what: its own line")
        self.assertFalse(self.fp.exists())
        self.assertIn("kernel", km.CLIENT_DIAG_KEYS, "the entry stays for the kernel's own rows")
        # a surface that merely begins with the word is another surface: unknown, so it keeps no key and lands
        self.post("kernel-ish", "wsopen", forged)
        self.assertEqual((self.rows()[-1]["surface"], self.rows()[-1]["data"]), ("kernel-ish", {}))

    def test_the_collectors_key_lists_are_admitted_by_the_perf_entry(self):
        # the collector's executed row is pinned against TODAY_KEYS and SHARED_KEYS in ui/webview/perf-telemetry.test.ts,
        # and the table here against hand-written fixtures; nothing tied the two, so a key the collector grows or renames
        # kept both suites green while the kernel dropped it from the file (review find, 2026-09-18). Parsed by regex, the way
        # tests/test_perf_stats.py reads perf-telemetry.ts; a subset, not equality: the perf entry is a union that also
        # carries the slowframe row's type and ms.
        ts = open(os.path.join(UI, "perf-telemetry.test.ts"), encoding="utf-8").read()
        lists = {}
        for name in ("TODAY_KEYS", "SHARED_KEYS"):
            m = re.search(r'^const %s = (\[[^\]]*\]);$' % name, ts, re.M)
            self.assertIsNotNone(m, "perf-telemetry.test.ts no longer declares %s on one line: re-aim this parse" % name)
            lists[name] = json.loads(m.group(1))
            self.assertTrue(lists[name] and all(isinstance(k, str) for k in lists[name]), name)
        table = km.CLIENT_DIAG_KEYS["perf"]
        for name, keys in lists.items():
            missing = sorted(set(keys) - table)
            self.assertEqual(missing, [], "%s in perf-telemetry.test.ts names %s, which CLIENT_DIAG_KEYS['perf'] does not admit: "
                                          "add the key to the table, or take it out of the collector and its list" % (name, missing))
        self.assertEqual(sorted(lists["TODAY_KEYS"]), sorted(MINUTE), "this module's MINUTE fixture is the same list")
        self.assertEqual(sorted(lists["SHARED_KEYS"]), sorted(SHARED), "and SHARED the same")

    def _worst_case_row(self):
        """The minute row the collector would send with every cap reached at once and eight attached hosts, built from the
        constants as perf-telemetry.ts declares them: (minute, shared, env, consts), `minute` the share-off row, `shared` the
        fields the share switch adds (wsBytesByHost among them at HOSTS positions of nine-digit counts), `env` the kernel's
        envelope and `consts` the collector's constants read. Shared by the worst-case row test and the ladder test."""
        src = open(os.path.join(UI, "perf-telemetry.ts"), encoding="utf-8").read()
        def const(name):
            m = re.search(r"^export const %s(?:: [^=]+)? = ([^;]+);" % name, src, re.M)
            self.assertIsNotNone(m, name)
            return m.group(1)
        max_types = int(const("MAX_FRAME_TYPES")); max_top = int(const("MAX_TOP")); free_ring = int(const("FREE_RING"))
        slow_rows = int(const("SLOW_ROWS_PER_MINUTE")); max_res = int(const("MAX_RES"))
        buckets = len(json.loads(const("HIST_EDGES"))) + 1
        ident_cap = int(re.search(r"\^\[A-Za-z0-9_\.:-\]\{1,(\d+)\}\$", src).group(1))    # ident(): a frame type at most this long
        self.assertEqual((max_types, max_top, free_ring, slow_rows, max_res, buckets, ident_cap), (32, 5, 64, 5, 24, 14, 32), "the constants this derivation was made with")
        entry_types = json.loads(re.search(r"^export const ENV_ENTRY_TYPES: readonly string\[\] = (\[[^\]]*\]);", src, re.M).group(1))
        big = 999999                                         # six-digit counts: more than a minute of frames at 60 Hz can hold
        ms = 60000.0                                         # one-decimal ms, a whole minute
        st = {"n": big, "ms_sum": ms, "ms_max": ms, "n16": big, "n100": big, "hist": [big] * buckets}
        frames = {}
        for i in range(max_types + 1):                       # the named types and the fold ("other" / "fed:other") are max_types + 1 keys each
            frames["delta:" + "w" * (ident_cap - 6) + "%06d" % i] = dict(st)      # the longest prefix (a raw delta by slot) and an identifier at the cap
            frames["fed:delta:" + "f" * (ident_cap - 6) + "%06d" % i] = dict(st)   # the federation layer's key for the same frame: fed: plus the classified type
        self.assertEqual(len(frames), 2 * (max_types + 1))
        self.assertEqual(max(len(k) for k in frames if not k.startswith("fed:")), 38, "a wire key is at most delta: plus the identifier cap")
        self.assertEqual(max(len(k) for k in frames), 42, "the longest key the collector emits is fed:delta: plus the identifier cap")
        top = [{"k": "k" * km.CLIENT_DIAG_STR_MAX, "ms": ms, "n": big, "inv": "i" * km.CLIENT_DIAG_STR_MAX} for _ in range(max_top)]
        minute = {"app": "timeline", "since": 1700000000000, "span_ms": 600000, "frames": frames,
                  "free": {"n": free_ring, "p50": ms, "p90": ms, "max": ms},
                  "loaf": {"n": big, "blocking_ms": 600000.0, "worst_ms": ms, "top": top, "src": "longtask"},
                  "slow": {"sent": slow_rows, "suppressed": big, "suppressed_worst_ms": ms},
                  "dom": 9999999, "visible": False, "hidden_pane": False, "ua": "chrome-desktop", "heap_mb": 99999.9}
        res = {"r" * 20 + "%03d.woff2" % i: {"transferSize": 99999999, "encodedBodySize": 99999999, "duration": ms} for i in range(max_res)}
        res["other"] = {"transferSize": 99999999, "encodedBodySize": 99999999, "duration": ms}
        # wsBytesByHost at its widest (2026-09-19): the field has no cap (one key per attached host, the owner's decision), so the
        # row states a count rather than reading one. Eight is twice the four an earlier cut capped at and more than any lab or
        # deployment attaches to one page (the labs' widest is two); each further host adds about 17 bytes to the row; a row
        # budget, if one is ever needed, is the owner's question through the design.
        HOSTS = 8
        by_host = {"h%d" % i: 999999999 for i in range(1, HOSTS + 1)}
        self.assertEqual(len(by_host), HOSTS, "one key per stated host, no fold key")
        shared = {"nav": {"type": "back_forward", "responseEnd": big, "domContentLoaded": big, "loadEventEnd": big}, "res": res,
                  "marks": {"wsOpen": big, "bundleReady": big, "firstFrame": big, "fp": big, "fcp": big},
                  "env": {"standalone": True, "iosMajor": 17, "touch": True, "vw": 99999, "vh": 99999, "dpr": 3.5, "entryTypes": entry_types, "ric": True, "dv": 1757100000000},
                  "vis": {"hiddenN": big, "visibleN": big, "hiddenMs": 99999999}, "wsBytes": 999999999, "rafGap": {"n": big, "worst": big},
                  "wsBytesByHost": by_host}
        env = {"t": 1700000000, "wid": WID, "surface": "perf", "what": "minute", "reconnect": False}
        return minute, shared, env, {"max_types": max_types, "hosts": HOSTS}

    def test_the_collectors_worst_case_minute_row_is_stored_whole(self):
        # CLIENT_DIAG_ROW_MAX sat at 8 KiB, below the collector's own worst case, so a share-off minute with 28 or more frame
        # types lost its frames where main stored it whole, and the shared row lost more (review find, 2026-09-18: 16481 B
        # share off, 19110 B share on, measured). The bound is now derived from the collector's caps; this builds the row
        # the collector would send with every cap reached at once, from the constants as perf-telemetry.ts declares them,
        # and asserts it lands whole, no shed, no marker, nothing said. A 16 KiB bound would still have shed it. The fed:
        # keys are spelled in their longest form, fed:delta: plus the 32-character identifier, 42 characters: federation.ts
        # times a frame as fed: plus classifyFrame(msg), which reads delta: plus the identifier for a delta frame. This test
        # first spelled them fed: plus the identifier, 36 characters, and the row it proved whole was 198 B under the row
        # the collector can build (a review find of the earlier cut's review, 2026-09-18). The one key with no cap, wsBytesByHost, is built at
        # the eight positions the derivation states; the ladder test below takes it past the bound.
        minute, shared, env, c = self._worst_case_row()
        max_types, HOSTS, by_host = c["max_types"], c["hosts"], shared["wsBytesByHost"]
        off, on = len(json.dumps(dict(env, data=minute))), len(json.dumps(dict(env, data=dict(minute, **shared))))
        self.assertGreater(off, 16 * 1024, "the share-off worst case is over 16 KiB, so the old 8 KiB bound shed its frames")
        self.assertLess(on, km.CLIENT_DIAG_ROW_MAX, "the share-on worst case fits under the bound (%d of %d bytes)" % (on, km.CLIENT_DIAG_ROW_MAX))
        # The row bound's derivation comment in kernel.py states this map's count, the bytes it adds to the row and the share-on
        # figure. Until the peer read of 2026-09-19 those were hand-kept copies of HOSTS with nothing tying them to the row built
        # here: a raised HOSTS left the comment claiming a margin this test no longer measured, and nothing went red. Read back
        # from the comment and compared to the row, so a change to HOSTS, or to any figure the row is made of, re-derives the
        # comment too. Derived reads: a comment the pattern no longer finds fails here rather than passing on nothing.
        ksrc = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py"), encoding="utf-8").read()
        stated = re.search(r"the worst-case row test states (\w+) at nine digits each, (\d+) bytes", ksrc)
        self.assertIsNotNone(stated, "kernel.py's CLIENT_DIAG_ROW_MAX derivation no longer states the widest wsBytesByHost map: re-aim this read")
        words = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")
        self.assertLess(HOSTS, len(words), "state HOSTS as a count word this read knows, or extend the tuple")
        self.assertEqual(stated.group(1), words[HOSTS], "the derivation's count word is the HOSTS this test states")
        without = len(json.dumps(dict(env, data=dict(minute, **{k: v for k, v in shared.items() if k != "wsBytesByHost"}))))
        self.assertEqual(int(stated.group(2)), on - without, "the derivation's byte figure is what the map adds to the row, its key and separator included")
        share_on = re.findall(r"\((\d+\.\d) KB(?: share on\)|; the derivation above\))", ksrc)
        self.assertEqual(len(share_on), 2, "the derivation and CLIENT_DIAG_ROW_MAX's own comment each state the share-on figure once")
        self.assertEqual(set(share_on), {"%.1f" % (on / 1000)}, "both share-on figures are this row's size in KB (%d bytes)" % on)
        # docs/reference.md states the same two figures for the same derivation, in its own phrasing: a third copy, which this
        # change moved in kernel.py and the body and left at the old figure in the docs (the maintainer's round 1, regression-3, 2026-09-20). Its own
        # pattern, whitespace-flattened (the doc wraps), and a not-None guard before the comparison, so a rephrased doc fails
        # here rather than passing on nothing; the assumed host count is read back too, since "every cap reached at once" is
        # not a bound on the one key that has no cap
        dsrc = re.sub(r"\s+", " ", open(os.path.join(os.path.dirname(HERE), "docs", "reference.md"), encoding="utf-8").read())
        doc = re.search(r"is about (\d+\.\d) KB with share off and (\d+\.\d) KB with share on\)", dsrc)
        self.assertIsNotNone(doc, "docs/reference.md no longer states the two worst-case figures: re-aim this read")
        self.assertEqual(doc.groups(), ("%.1f" % (off / 1000), "%.1f" % (on / 1000)), "the docs' figures are this row's (%d and %d bytes)" % (off, on))
        count = re.search(r"every cap reached at once and (\w+) attached hosts", dsrc)
        self.assertIsNotNone(count, "docs/reference.md no longer states the assumed host count beside the figures: re-aim this read")
        self.assertEqual(count.group(1), words[HOSTS], "the docs' host count word is the HOSTS this test states")
        for data in (minute, dict(minute, **shared)):
            self.assertEqual(self.post("perf", "minute", data), "", "nothing shed, nothing said")
            row = self.rows()[-1]
            self.assertEqual(row["data"], data, "stored whole")
            self.assertNotIn("capped", row["data"])
            self.assertEqual(len(row["data"]["frames"]), 2 * (max_types + 1), "every frame type intact")
        self.assertEqual(self.rows()[-1]["data"]["wsBytesByHost"], by_host, "the per-host map lands whole: the admit filters top-level keys only, the scrub walks it")

    def test_a_wide_wsBytesByHost_map_is_shed_whole_as_the_ladders_first_step_and_the_rest_of_the_row_is_stored_as_posted(self):
        # wsBytesByHost is the one key of the minute row the collector does not cap (one position per attached host, the owner's
        # decision), so it is the one key that can take a row the collector builds past CLIENT_DIAG_ROW_MAX. Before the maintainer's round 1 of
        # its review (2026-09-20) the ladder shed the frame histograms first and kept the map that caused the overflow, and past
        # a second crossing the whole row: a wide map lost exactly what the shed protects. Now the map is the ladder's first
        # step, shed WHOLE and named under capped (never truncated to the positions that fit, so a stored map is never read as a
        # host count), and shedding it returns the row to the derived worst case, which fits: the frames and the once-per-page
        # fields stay, however wide the map. The crossing and the per-position cost are DERIVED here from the row this test
        # builds and read back against the kernel's comment, so a moved figure or a reshaped row goes red rather than leaving
        # the comment claiming a crossing the row no longer has.
        minute, shared, env, c = self._worst_case_row()
        def with_hosts(n):
            return dict(minute, **dict(shared, wsBytesByHost={"h%d" % i: 999999999 for i in range(1, n + 1)}))
        def size(n):
            return len(json.dumps(dict(env, data=with_hosts(n))))
        n = c["hosts"]
        self.assertLessEqual(size(n), km.CLIENT_DIAG_ROW_MAX, "the stated worst case fits (the test above)")
        while size(n) <= km.CLIENT_DIAG_ROW_MAX:
            n += 1
            self.assertLess(n, 100000, "no crossing found: the map never takes the row over the bound?")
        crossing = n
        self.assertGreater(crossing, c["hosts"], "derived: the first position count whose row is over the bound")
        for count in (crossing, crossing + 1, 2000):
            data = with_hosts(count)
            line = json.dumps(dict(env, data=data))
            self.assertGreater(len(line), km.CLIENT_DIAG_ROW_MAX, count)
            km._client_diag_said.clear()
            err = self.post("perf", "minute", data)
            row = self.rows()[-1]
            d = row["data"]
            self.assertNotIn("wsBytesByHost", d, "%d positions: the map is shed whole, never stored truncated" % count)
            self.assertEqual(d["capped"], {"bytes": len(line), "dropped": ["wsBytesByHost"]}, "%d positions: the one step, recorded" % count)
            self.assertEqual(len(d["frames"]), 2 * (c["max_types"] + 1), "%d positions: every frame type intact" % count)
            for k, v in data.items():
                if k != "wsBytesByHost":
                    self.assertEqual(d[k], v, "%d positions: %s stored as posted" % (count, k))
            self.assertLessEqual(len(json.dumps(row)), km.CLIENT_DIAG_ROW_MAX)
            self.assertEqual(len(err.splitlines()), 1, err)
            self.assertIn("stored without some of its keys (its capped key names them)", err, "the shed's stderr line fires, once, worded for the ladder as a whole (this row lost the map and kept every per-minute figure)")
        data = with_hosts(crossing - 1)
        self.assertEqual(self.post("perf", "minute", data), "", "one position under the crossing: nothing shed, nothing said")
        self.assertEqual(self.rows()[-1]["data"], data, "stored whole, the map at %d positions included" % (crossing - 1))
        # the per-position cost by the ordinal's digit width (the separator, the quoted key and a nine-digit count), derived
        per = (size(9) - size(8), size(10) - size(9), size(100) - size(99))
        self.assertTrue(all(b > 0 for b in per), per)
        ksrc = open(os.path.join(os.path.dirname(HERE), "kernel", "kernel.py"), encoding="utf-8").read()
        ksrc = re.sub(r"\s+", " ", re.sub(r"\n\s*#", " ", ksrc))   # the comment's wrapping is not part of the claim
        rule = re.search(r"each further position adds (\d+) bytes at a one-digit ordinal, (\d+) at two and (\d+) at three", ksrc, re.I)
        self.assertIsNotNone(rule, "kernel.py's derivation no longer states the per-position rule: re-aim this read")
        self.assertEqual(tuple(int(x) for x in rule.groups()), per, "the derivation's per-position figures are this row's")
        cross = re.search(r"the map crosses the bound at (\d+) positions", ksrc)
        self.assertIsNotNone(cross, "kernel.py's derivation no longer states the crossing: re-aim this read")
        self.assertEqual(int(cross.group(1)), crossing, "the derivation's crossing is the one this row derives")
        margin = re.search(r"leaves (\d+) bytes under the bound", ksrc)
        self.assertIsNotNone(margin, "kernel.py's derivation no longer states the margin: re-aim this read")
        self.assertEqual(int(margin.group(1)), km.CLIENT_DIAG_ROW_MAX - size(c["hosts"]), "the stated margin is the bound less the stated worst case")
        # docs/reference.md carries a copy of the same derived figures (the maintainer's round 3, regression-2: a fourth, unpinned copy): its own
        # patterns, whitespace-flattened, each guarded, read back against the same row: the per-position range against the derived
        # tuple's least and most, the crossing against the derived crossing, the shed order against CLIENT_DIAG_MINUTE_SHED. Neither
        # copy states the crossing on "today's rows" any more: that figure was pinned by nothing in either and is dropped from both.
        dsrc = re.sub(r"\s+", " ", open(os.path.join(os.path.dirname(HERE), "docs", "reference.md"), encoding="utf-8").read())
        drange = re.search(r"each position adds (\d+) to (\d+) bytes", dsrc)
        self.assertIsNotNone(drange, "docs/reference.md no longer states the per-position range: re-aim this read")
        self.assertEqual(tuple(int(x) for x in drange.groups()), (min(per), max(per)), "the docs' range is the derived tuple's least and most")
        dcross = re.search(r"on that worst-case row the crossing is (\d+) positions", dsrc)
        self.assertIsNotNone(dcross, "docs/reference.md no longer states the crossing: re-aim this read")
        self.assertEqual(int(dcross.group(1)), crossing, "the docs' crossing is the one this row derives")
        dorder = re.search(r"sheds `(\w+)` whole, then `(\w+)`, `(\w+)`, `(\w+)` and `(\w+)`, in that order", dsrc)
        self.assertIsNotNone(dorder, "docs/reference.md no longer states the shed order: re-aim this read")
        self.assertEqual(dorder.groups(), km.CLIENT_DIAG_MINUTE_SHED, "the docs' shed order is the ladder's")
        for name, text in (("kernel.py", ksrc), ("docs/reference.md", dsrc)):
            self.assertIsNone(re.search(r"about 1200|today's rows (only )?(past )?about", text), "%s: the unpinnable today's-rows crossing is stated again" % name)

    def test_every_admitted_key_is_classified_by_the_content_its_value_can_carry(self):
        # The census (CENSUS, above) against the table, both ways per surface: a key the table admits with no row here fails, as
        # does a row here for a key the table no longer admits, so a surface cannot grow a key without a reader deciding what its
        # value can carry. The host-carrying surfaces are DERIVED from the rows' classes, never listed by hand, and the derivation
        # must not come out empty: the file carries host names today (the shell's and federation's `host`, the kernel's wsopen row,
        # federation's counts, the chat surface's prefixed session ids), and a census that found none would be reading nothing.
        self.assertEqual(sorted(CENSUS), sorted(km.CLIENT_DIAG_KEYS), "every surface of the table is classified and no other")
        for surface, table in sorted(CENSUS.items()):
            self.assertEqual(sorted(table), sorted(km.CLIENT_DIAG_KEYS[surface]),
                             "%s: every admitted key has a classification and every classified key is admitted" % surface)
            for key, (cls, why) in sorted(table.items()):
                self.assertIn(cls, (BARE, PREFIXED, KEYED, SUFFIX, NONE), (surface, key))
                self.assertTrue(isinstance(why, str) and why, "%s.%s: a class names its reason" % (surface, key))
        # the kernel-written markers: the two the kernel writes after the admit (CLIENT_DIAG_CUT_KEY and the row cap's), each
        # classified NONE with its writer named, and admitted from no poster (the constants test)
        self.assertEqual(sorted(MARKERS), sorted([km.CLIENT_DIAG_CUT_KEY, "capped"]))
        for key, (cls, why) in MARKERS.items():
            self.assertEqual(cls, NONE, key)
            self.assertIn("_client_diag_", why, "%s: the marker's reason names its kernel writer" % key)
            self.assertTrue(all(key not in keys for keys in km.CLIENT_DIAG_KEYS.values()), key)
        carrying = host_carrying_keys()
        self.assertTrue(carrying, "the derivation found no host-carrying key: the census is reading nothing")
        self.assertEqual(carrying, {"chat": {"active": PREFIXED, "anchor": SUFFIX, "id": PREFIXED, "ids": PREFIXED, "sid": PREFIXED},
                                    "feed": {"appeared": SUFFIX, "gone": SUFFIX, "id": SUFFIX},
                                    "federation": {"counts": KEYED, "host": BARE}, "kernel": {"host": BARE}, "shell": {"host": BARE, "sid8": PREFIXED}},
                         "the host-carrying keys and their forms, as derived (the author's pass 4 gained shell.sid8, feed's three and chat.anchor by following the values to their "
                         "producers); a change here is a change to the disclosure copies")
        # the prefixed form lands as posted: the head of a string survives the cut, host and all (a 64-character cut of
        # <host>:<uuid> keeps the whole id for a host name of up to 27 characters and the host for any longer one)
        sid = "TESTHOST:11111111-2222-3333-4444-555555555555"
        self.assertEqual(self.post("chat", "send", {"sid": sid, "ts": 1700000000000, "len": 3, "route": "plain"}), "")
        self.assertEqual(self.rows()[-1]["data"]["sid"], sid)
        long_host = "h" * 80
        self.post("chat", "skeleton", {"n": 1, "active": long_host + ":" + sid.split(":")[1]})
        self.assertEqual(self.rows()[-1]["data"]["active"], long_host[:km.CLIENT_DIAG_STR_MAX])
        # the suffix form: a parked card's id ends in a postal message id whose last component is the delivering kernel's short
        # hostname; the cut keeps the head, so what survives of the host is 64 less the head's length (a one-digit pid leaves the
        # whole 8-character fixture host; a five-digit pid leaves 7 of it, and the row then carries the cut marker)
        parked = "parked:1700000000.7_" + "a" * 32 + ".TESTHOST"
        self.assertEqual(len(parked), 61)
        self.assertEqual(self.post("feed", "colflip", {"id": parked, "from": "working", "to": "blocked", "ev": "feedDelta", "buildId": 7, "predicted": True}), "")
        self.assertEqual(self.rows()[-1]["data"]["id"], parked, "under the cut: the host lands whole")
        parked5 = "parked:1700000000.12345_" + "a" * 32 + ".TESTHOST"
        self.assertEqual(len(parked5), 65)
        self.post("feed", "itemset", {"appeared": [parked5], "gone": [], "total": 1, "ev": "feed", "buildId": 7})
        d = self.rows()[-1]["data"]
        self.assertEqual(d["appeared"], [parked5[:km.CLIENT_DIAG_STR_MAX]], "cut per element: 7 of the host's 8 characters survive")
        self.assertTrue(d["appeared"][0].endswith(".TESTHOS"))
        self.assertEqual(d[km.CLIENT_DIAG_CUT_KEY], ["appeared"])
        # the anchor's one host-carrying road: the tail of a postal message id, 12 characters, a host of up to 11 whole
        mid = "1700000000.7_" + "b" * 32 + ".TESTHOST"
        self.assertEqual(mid[-12:], "bbb.TESTHOST")
        self.post("chat", "landmiss", {"sid": sid, "anchor": mid[-12:], "proto": 2, "events": 3, "regions": True, "headKnown": True, "headFrom": 0, "older": False, "noframe": False, "trail": ["pre-jump"]})
        self.assertEqual(self.rows()[-1]["data"]["anchor"], "bbb.TESTHOST")

    def test_the_disclosure_copies_state_the_content_rule_and_name_every_host_carrying_surface(self):
        # The disclosure is stated three times in the tree (the wsBytesByHost entry's comment in kernel.py, the minute-row entry
        # in docs/reference.md, the ledger entry) and once in the PR body outside it. Its first version enumerated the surfaces
        # that name a `host` KEY and missed the chat surface, whose values carry a host inside a session id (the maintainer's round 1, correctness-1, 2026-09-20).
        # Each copy must now state the rule (a value can carry a host name bare under a host key, as a host-prefixed session id
        # when the row concerns a remote session, or as a host-keyed map), name the chat road's condition and its independence
        # from the share switch, and name every host-carrying surface the census derives; a copy that drops a clause fails here.
        # The tokens are the rule's terms and the clauses the author's pass-1 verify asked for (the chat road's age, its frequency and its use, the
        # map clause, the registries' stamp); a copy's other sentences are not read here.
        copies = disclosure_copies()
        self.assertEqual(sorted(copies), ["docs", "kernel", "ledger"])
        for name, text in sorted(copies.items()):
            self.assertIsNotNone(text, "%s: the disclosure copy was not found: re-aim disclosure_copies()" % name)
            self.assertGreater(len(text), 200, name)
            for token in (r"host-prefixed session id", r"host-keyed map", r"remote session", r"share switch", r"`?host`? key", r"positions and no host name",
                          r"several positions for one machine",   # the per-document grain's consequence (the maintainer's round 1 addendum, fresh-2)
                          r"GET /tunnels", r"in (its|their) own right",
                          r"remotes\.json", r"remotes-known\.json", r"lastAttachedAt", r"exact for", r"order inference",
                          r"no page-life correlation", r"attached-host order",   # the fourth road's whole statement (the maintainer's round 1 addendum, extra8-1)
                          r"older than", r"most frequent", r"routine use", r"not from chat or feed rows alone",
                          r"four forms", r"tail of a postal message id", r"postal host", r"sid8", r"first 8 characters", r"message connector",   # the author's pass 4: the suffix form, the shell's rows, the anchor's road
                          r"single-kernel page", r"every row of (the|both) kind", r"one road",   # each carrier's RANGE (the ruling's rule: classify by the producer's range)
                          r"\bmints\b", r"does not inspect the map's keys", r"nested key",
                          r"a value of which was cut carries",   # the cut marker: a stored value can be told from a whole one (the author's pass 4)
                          r"regular-expression test in the page bundle", r"the kernel has none"):   # the enforcement named (the maintainer's round 1 addendum, extra8-3)
                self.assertIsNotNone(re.search(token, text, re.I), "%s: the disclosure no longer states %r" % (name, token))
            # one grain per copy (the author's pass-3 fixer pass): the copies state the per-document grain and its consequence, so no
            # sentence of theirs may keep the page grain the first cut wrote (h1 "the first remote host the page saw", a position
            # "on the page"), which on a page with several panes is false and contradicts the sentence beside it
            for phrase in (r"position on the page", r"the page saw", r"this page attached", r"page-lifetime", r"the page attaches", r"appeared to the page"):
                self.assertIsNone(re.search(phrase, text, re.I), "%s: the disclosure states the page grain again: %r" % (name, phrase))
        # the bare-name example is derived, not hand-kept: every federation row kind that carries the conn's host, read from
        # federation.ts's diag call sites, is named by every copy (the author's pass-1 verify, 2026-09-20: the copies named hostconn alone)
        kinds = federation_host_row_kinds()
        self.assertEqual(kinds, {"hostconn", "feedDelta-nobase", "feedDelta-stale", "feedDelta-apply", "sendqueue", "senddrop"},
                         "the federation row kinds carrying a host, as derived (feedDelta-apply since the maintainer's round 5, refusals-2); a change here is a change to the disclosure copies")
        for name, text in sorted(copies.items()):
            for kind in sorted(kinds):
                self.assertIsNotNone(re.search(r"\b%s\b" % re.escape(kind), text), "%s: the disclosure does not name federation's %s rows" % (name, kind))
        # the stability caveat lives where the position rule is stated for readers, the docs and the ledger (and the PR body outside
        # the tree): a reload re-derives the assignment from the same /tunnels order, so the caveat must carry its condition, never
        # read as a de-linking property (the maintainer's round 1, correctness-2; the ledger's copy since the author's pass-1 verify)
        for name in ("docs", "ledger"):
            for token in (r"names the same one again", r"dialable rows", r"first poll", r"attach and detach history", r"rotation"):
                self.assertIsNotNone(re.search(token, copies[name], re.I), "%s: the reload sentence no longer states %r" % (name, token))
        # federation.ts's two-maps comment carries the same three conditions (it carried one until the author's pass 3)
        maps = maps_comment()
        self.assertIsNotNone(maps, "federation.ts: the two-maps comment's anchors are gone: re-aim maps_comment()")
        for token in (r"names the same one again", r"dialable rows", r"first poll", r"attach and detach history"):
            self.assertIsNotNone(re.search(token, maps, re.I), "maps: the reload sentence no longer states %r" % token)
        # and no federation.ts site that states the grain keeps the page grain (the maintainer's round 3, regression-1: the grain pass left
        # "over this page's life" at the wsBytesByHost() docstring and the publication comment and "attached to this page" at
        # attachedHostOrdinals(), against the maps declaration). The phrases are federation.ts's alone: kernel.py says "for the
        # page's life" of the once-per-page fields, another grain, and is not read here.
        grain = federation_grain_texts()
        for site, text in sorted(grain.items()):
            self.assertIsNotNone(text, "federation.ts: the %s text's anchors are gone: re-aim federation_grain_texts()" % site)
            self.assertGreater(len(text), 80, site)
            for phrase in (r"position on the page", r"the page saw", r"this page attached", r"page-lifetime", r"the page attaches", r"appeared to the page",
                           r"page's life", r"attached to this page", r"this page NOW"):
                self.assertIsNone(re.search(phrase, text, re.I), "federation.ts %s: the page grain again: %r" % (site, phrase))
            self.assertIsNotNone(re.search(r"manager|pane document", text), "federation.ts %s: the grain is stated (the manager, the pane document)" % site)
        named = {"chat": r"\bchat\b", "federation": r"\bfederation\b", "shell": r"\bshell\b", "kernel": r"\bwsopen\b",
                 "feed": r"feed surface's `?id`?, `?appeared`? and `?gone`?"}   # the fourth form's surface (the author's pass 4), named with its three keys
        carrying = host_carrying_keys()
        self.assertTrue(carrying)
        for surface in sorted(carrying):
            self.assertIn(surface, named, "a new host-carrying surface: say how each disclosure copy names it")
            for name, text in sorted(copies.items()):
                self.assertIsNotNone(re.search(named[surface], text), "%s: the disclosure does not name the %s surface" % (name, surface))

    def test_one_fixture_row_per_poster_call_site_passes_whole_and_the_table_names_nothing_else(self):
        """The table against the posters: one synthetic row per clientDiag call site in the bundles (render.ts and
        scroll-write.ts, federation.ts, feed.ts, fleet.ts, waiting.ts, strip.ts) and the shell scripts in kernel.py, with the
        keys each posts and, since the author's pass 4 (2026-09-20), values of the shapes the writers post (the rows had been written
        from the key names: eleven shell values across five call sites, and counts, strings and booleans where the writers
        post lists, ints and objects, matched no producer, so the census's shorthand reasons were checked by nothing). Every
        row passes whole with no stderr line, and per surface the fixtures' keys are exactly the table's, so a poster that
        grows a key without the table, or a table key no poster sends, fails here. The perf, pane-shim and reload-core rows
        are test_todays_rows_pass_whole_and_quietly's."""
        sid = "TESTHOST:11111111-2222-3333-4444-555555555555"   # a REMOTE session's tab id as the page holds it, host-prefixed (the census, CENSUS)
        host = "TESTHOST"
        parked = "parked:1700000000.7_" + "a" * 32 + ".TESTHOST"   # a parked hand-off's item id: a postal message id, the delivering kernel's postal host at its tail (the census, feed.id)
        load = {"duration": 88, "transferSize": 120000, "encodedBodySize": 119700, "responseStatus": 200}   # federationLoadEntry's four figures (frame-listener.ts)
        posters = {
            "chat": [   # render.ts's direct posts, then scrollDiagRow's kinds (scroll-write.ts builds the rows)
                ("reconcile-optimistic-failed", {"sid": sid, "error": "gone"}),
                ("views-stale-blob", {"held": 3, "got": 1}),
                ("pageload", {"distVer": 1757100000, "path": "/chat"}),
                ("cancel-provisional", {"mdLen": 12, "queuedLeft": 0}),
                ("live-omitted-kept", {"ids": [sid, "TESTHOST:11111111-2222-3333-4444-666666666666"]}),
                ("skeleton", {"n": 4, "active": sid}),
                ("send", {"sid": sid, "ts": 1700000000000, "len": 42, "route": "plain"}),   # render.ts: followup on a goal cite, quote on a quote cite, else plain
                ("empty-session-frame", {"id": sid, "held": 12}),   # render.ts: held is prev.events.length, the events the pane holds for the id; the earlier fixture posted a boolean
                ("federation-missing", {"load": load, "first": None}),
                ("federation-missing", {"recovered": True, "first": load}),
                ("cancel-miss", {"sid": sid, "mdLen": 12, "hadRestore": False}),
                ("scrollwrite", {"sid": sid, "writer": "paintAll", "before": 100, "after": 120, "delta": 20, "stick": True, "gesture": False, "sh": 5000, "ch": 800}),
                ("landmiss", {"sid": sid, "anchor": "bbb.TESTHOST", "proto": 2, "events": 3, "regions": True, "headKnown": True, "headFrom": 0, "older": False, "noframe": False, "trail": ["pointer-fetch-older", "pointer-not-rendered"]}),   # the anchor as the message connector's road leaves it: the tail of a postal message id (the census, chat.anchor)
                ("tailchange", {"sid": sid, "dh": 12, "last": "turn turn-user", "stick": True, "sh": 5000, "ch": 800}),   # tailLabel: the tail element's className (scroll-write.ts), or the literal live-ask
                ("unitchange", {"sid": sid, "dh": 4, "cls": "turn", "fromTail": 1, "stick": False, "atBottom": True, "sh": 5000, "ch": 800}),   # fromTail counts units above the tail (unitChangeRow), 1 the unit just above it
                ("tailmut", {"sid": sid, "where": "tail", "removed": ["turn"], "added": ["turn", "live-ask"], "reAdded": False, "shBefore": 5000, "shAfter": 5010, "st": 4200, "ch": 800}),
                ("spacer", {"sid": sid, "top": [40, 48], "bot": [0, 0], "dTop": 8, "dBot": 0, "sh": 5000, "ch": 800}),
                ("scrollgesture", {"sid": sid, "top": 4100, "gesture": True, "sh": 5000, "ch": 800}),
                ("regionask", {"sid": sid, "lo": 10, "hi": 20, "edge": "top", "why": "gap-scroll", "notice": False}),
                ("regionask", {"sid": sid, "why": "landing", "nav": True, "kind": "user", "keep": True, "reland": False, "trail": ["pre-jump"], "notice": True, "atBottom": False}),
                ("scrollwrite-capped", {"sid": sid, "perMinute": 200}),
            ],
            "federation": federation_fixture_rows(host),
            "feed": [
                ("colflip", {"id": parked, "from": "working", "to": "blocked", "ev": "feedDelta", "buildId": 7, "predicted": True}),
                ("itemset", {"appeared": [parked], "gone": ["11111111-2222-3333-4444-555555555555:g1"], "total": 12, "ev": "feed", "buildId": 7}),
                ("feedDelta-unapplied", {"buildId": 7}),
            ],
            "outline": [("feedDelta-unapplied", {"buildId": 7}), ("delta-unapplied", {"slot": "bars", "rev": 7})],
            "waiting": [("feedDelta-unapplied", {"buildId": 7})],
            "strip": [("netFetch", {"ok": True, "tunnels": 2}), ("netFetch", {"ok": False, "err": "TypeError"}), ("netToggle", {"open": True, "base": "http://127.0.0.1:1"})],
            "shell": [   # the shell scripts' shellDiag rows (kernel.py)
                ("push-test", {"sidAttached": True, "host": host, "why": "", "tabs": 2}),
                ("push-test", {"sidAttached": False, "host": "", "why": "none-active", "tabs": 2}),
                ("reveal-post", {"status": 200, "via": "link", "boot": False}),
                ("reveal-post", {"status": 0, "via": "ack", "boot": True}),   # the fetch threw
                ("deeplink", {"via": "boot", "hasSid": True, "hasCard": False, "hasPid": True, "dup": False, "controlled": True}),
                ("tap-pending", {"via": "boot", "sub": True, "rows": 0, "err": True}),   # GET /push/pending failed: err is the literal true and the row ends before displayed() runs
                ("tap-pending", {"via": "visible", "sub": True, "rows": 2, "getNotifications": True, "displayed": 1, "vanished": 0, "superseded": 1}),   # superseded is written only when nonzero
                ("tap-pending-land", {"sid8": sid[:8], "ageS": 4, "dup": False}),   # the head of the ledger row's sid, the page's whole prefixed data-id: for this fixture the host name itself (the census, shell.sid8)
                ("tap-vanish-land", {"sid8": sid[:8], "ageS": 4}),
                ("sw-message", {"shape": "notificationClick", "hasSid": True, "kind": "card", "dup": False, "sw": {"road": "focus", "vis": "visible", "clients": 2, "tops": 1}}),
                ("return-probe", {"decision": "redial-closed", "hiddenMs": 30000, "quietMs": 31000, "attempts": 3, "firstFailMs": 12500, "ms": 30500}),   # D3 (2026-09-18): the shell socket's return probe, one row per return; decision is an enum, the rest ints
            ],
        }
        for surface, rows in posters.items():
            sent = set()
            for what, data in rows:
                err = self.post(surface, what, data)
                self.assertEqual(err, "", "%s %s: %s" % (surface, what, err))
                row = self.rows()[-1]
                self.assertEqual((row["surface"], row["what"], row["data"]), (surface, what, data), "%s %s passes whole" % (surface, what))
                self.assert_shorthand_shapes(surface, what, data)
                sent |= set(data)
            self.assertEqual(sent, set(km.CLIENT_DIAG_KEYS[surface]), "%s: the fixtures' keys are the table's, both ways" % surface)

    def test_the_federation_fixture_rows_are_shapes_the_writers_post_and_the_reasons_name_every_writer_literal(self):
        """The census against the writers (the maintainer's round 4, extra7-1, extra9-1, extra9-2): a census asserting a shape the
        product cannot produce tests its own fixture. The hold row carried a KERNEL_SETTING type, where federation.ts's hold arm
        holds only a BOOKKEEPING frame; the senddrop row posted `why: "closed"`, a word no writer sends, on a KERNEL_SETTING type,
        where the one why-carrying senddrop writer (the bookkeeping arm, a host this page holds no conn for) posts "no-conn" on a
        BOOKKEEPING type and the other (the default drop) posts the gesture's own type and no why. Derived from the source, never
        a list kept here: every senddrop and hold fixture row's key set is one a call site posts, its why is that site's literal,
        its msgType is in the table that arm draws from (BOOKKEEPING for hold and the why-carrying drop, KERNEL_SETTING for
        sendqueue, a gesture type outside both for the default drop); both senddrop call sites have a row; and the census's
        `why` and `msgType` reasons name every writer literal and all three msgType classes."""
        kernel_setting, bookkeeping, sites = federation_writer_tables()
        self.assertGreaterEqual(len(kernel_setting), 10, "KERNEL_SETTING read off federation.ts")
        self.assertGreaterEqual(len(bookkeeping), 4, "BOOKKEEPING's keys read off federation.ts")
        self.assertIn("activeTab", bookkeeping); self.assertIn("setAutoNudge", kernel_setting)
        senddrop_sites = [(keys, why) for what, ev, keys, why in sites if what == "senddrop"]
        self.assertEqual(sorted(senddrop_sites), sorted([(("host", "msgType", "why"), "no-conn"), (("host", "msgType"), None)]),
                         "the two senddrop writers: the bookkeeping arm with why no-conn, the default drop with none")
        hold_sites = [keys for what, ev, keys, why in sites if what == "hostconn" and ev == "hold"]
        self.assertEqual(hold_sites, [("host", "ev", "msgType", "rs")], "the one hold writer")
        rows = federation_fixture_rows("TESTHOST")
        senddrops = [d for what, d in rows if what == "senddrop"]
        self.assertEqual(sorted((tuple(d), d.get("why")) for d in senddrops), sorted(senddrop_sites), "one fixture row per senddrop call site, its keys and why the site's")
        for d in senddrops:
            if "why" in d:
                self.assertIn(d["msgType"], bookkeeping, "the why-carrying drop is the bookkeeping arm's: %r" % (d,))
            else:
                self.assertNotIn(d["msgType"], bookkeeping | kernel_setting, "the default drop carries a gesture's own type, outside both tables: %r" % (d,))
        holds = [d for what, d in rows if what == "hostconn" and d.get("ev") == "hold"]
        self.assertEqual(len(holds), 1)
        self.assertEqual(tuple(holds[0]), hold_sites[0]); self.assertIn(holds[0]["msgType"], bookkeeping, "a hold carries a BOOKKEEPING type: %r" % (holds[0],))
        for d in (d for what, d in rows if what == "sendqueue"):
            self.assertIn(d["msgType"], kernel_setting, "sendqueue queues KERNEL_SETTING frames alone: %r" % (d,))
        why_reason, msg_reason = CENSUS["federation"]["why"][1], CENSUS["federation"]["msgType"][1]
        for lit in ("quiet", "connecting", "local-down", "no-conn", "asked", "stopped"):
            self.assertIn(lit, why_reason, "the why reason names the writer literal %r" % lit)
        # the apply-throw row's road word (the maintainer's round 5, refusals-2): two fixed words at two writers, derived from federation.ts and named by the reason
        roads = sorted(set(re.findall(r'this\.diag\("feedDelta-apply", \{[^}]*\broad: "(\w+)"', fed_src())))
        self.assertEqual(roads, ["local", "wire"], "the two writers of feedDelta-apply post the two road words")
        road_reason = CENSUS["federation"]["road"][1]
        for lit in roads:
            self.assertIn(lit, road_reason, "the road reason names the writer literal %r" % lit)
        apply_rows = [d for what, d in rows if what == "feedDelta-apply"]
        self.assertEqual(sorted(set(d["road"] for d in apply_rows)), roads, "the fixture rows post both roads")
        self.assertEqual(sorted(set(d["why"] for d in apply_rows)), ["asked", "stopped"], "and both words")
        for d in apply_rows:
            self.assertEqual(d["host"] == "local", d["road"] == "local", "the local road's rows carry the word local under host, the wire road's a host name: %r" % (d,))
        self.assertNotIn("closed", why_reason, "no writer sends closed")
        for phrase in ("KERNEL_SETTING", "BOOKKEEPING", "gesture's own type"):
            self.assertIn(phrase, msg_reason, "the msgType reason names the class: %s" % phrase)

    def test_the_stale_rows_why_words_pass_whole_and_a_foreign_key_on_the_row_is_dropped(self):
        """The author's pass 3 (2026-09-20), the fifth word; the author's pass 4, the rule applied to every test of the gate (the maintainer's round 3, extra6-1; nine words: a word per
        field failure, a word per relation). The feedDelta-stale row carries host, buildId and why and nothing else, so
        its word is the whole signal a reader of the file has. Every word of STALE_WHY_WORDS is driven through the real
        dispatch, the road the fixture test posts through, and stored whole: the admit filters a row's top-level KEYS against
        the surface's table and tests no value for admission (an admitted key's value is stored through _client_diag_scrub,
        a string cut at CLIENT_DIAG_STR_MAX, 64 characters, which no word approaches: the 65-character word below is stored
        cut to 64, the row marked and the cut said once (the author's pass 4), so the value is read and never gated), so a new WORD under the admitted `why` key needs
        no table change where a new KEY does (PR 861: a pane-side marker under a key the table did not name was dropped).
        Green at the head before the word existed in federation.ts, by that mechanism; the failing-before is the control: the
        same row carrying `rev` and `through`, keys the minter does not send and the table does not admit, is stored without
        them and each is said once, so a minter that grew a field to explain its word would lose the field here, and a kernel
        that stopped dropping would fail this test."""
        for i, word in enumerate(STALE_WHY_WORDS):
            row = {"host": "TESTHOST", "buildId": "b%d" % i, "why": word}
            self.assertEqual(self.post("federation", "feedDelta-stale", row), "", "%s: admitted with no stderr line" % word)
            self.assertEqual(self.rows()[-1]["data"], row, "%s: the row is stored whole, the word whole among it" % word)
        self.assertEqual(len(self.rows()), len(STALE_WHY_WORDS))
        long_word = "d" * (km.CLIENT_DIAG_STR_MAX + 1)
        err = self.post("federation", "feedDelta-stale", {"host": "TESTHOST", "buildId": "b8", "why": long_word})
        self.assertEqual(self.rows()[-1]["data"], {"host": "TESTHOST", "buildId": "b8", "why": long_word[:km.CLIENT_DIAG_STR_MAX], km.CLIENT_DIAG_CUT_KEY: ["why"]},
                         "an over-long word under the admitted key is admitted (the admit gates on no value) and stored cut at CLIENT_DIAG_STR_MAX, "
                         "the row carrying the cut marker naming the key (the maintainer's round 3, kernel-2: a cut must not look like a whole value), so the ladder's words are whole because they are short")
        lines = [l for l in err.splitlines() if l]
        self.assertEqual(len(lines), 1, err)
        self.assertIn("key 'why', cut", lines[0]); self.assertIn("'federation'", lines[0]); self.assertIn("stored as its first 64", lines[0])
        self.assertEqual(self.post("federation", "feedDelta-stale", {"host": "TESTHOST", "buildId": "b8", "why": long_word}), "", "the one say per surface and key")
        err = self.post("federation", "feedDelta-stale", {"host": "TESTHOST", "buildId": "b9", "why": "disagree", "rev": 2, "through": 7})
        self.assertEqual(self.rows()[-1]["data"], {"host": "TESTHOST", "buildId": "b9", "why": "disagree"},
                         "the control: the two foreign keys dropped, the word kept; the file never learns which two revs disagreed")
        lines = [l for l in err.splitlines() if l]
        self.assertEqual(len(lines), 2, err)
        self.assertTrue(all(l.startswith("[client-diag] dropping a key the surface's allowlist does not admit") for l in lines), err)
        self.assertTrue(any("'rev'" in l and "'federation'" in l for l in lines) and any("'through'" in l for l in lines), err)

    def test_the_stale_rows_vocabulary_is_the_ladders(self):
        """The words the drive above posts are the words federation.ts mints, in the ladder's order (gen, base, through and
        rev for a failure of that field; disagree for the relation between a rev and a through that are each valid): a word
        added to the ladder fails here until STALE_WHY_WORDS carries it, so it is driven too. Red at the head before the
        fifth word (the ladder minted four, the relation failure riding rev's), and again at the author's pass-3 head before the
        pass-4 words (three relations riding a field's word: unpaired under gen, ahead under base, behind under through)."""
        words = stale_why_words()   # raises, naming the form, on a value the reader cannot read: never a shorter list
        self.assertIsNotNone(words, "federation.ts: the ladder's anchors are gone (the `const why` expression, or the minter's literal {host, buildId, why}): re-aim stale_why_words()")
        self.assertEqual(tuple(words), STALE_WHY_WORDS, "the ladder's words, in test order, are the driven vocabulary")

    def test_the_vocabulary_reader_reads_every_literal_form_and_refuses_what_it_cannot(self):
        """The maintainer's round 4 (extra7-2): stale_why_words() read only double-quoted `[\\w-]+` literals, so a tenth word
        in any other form vanished from the derived list, the vocabulary pin passed nine against nine, and the word was never
        driven through the admit road. The reader now parses the expression as a flat conditional ladder and reads one string
        literal per value in every form the language permits (double quotes, single quotes, a template literal without a
        substitution; every escape: the simple ones, \\x, \\u, \\u{}, an escaped quote, a line continuation, a non-escape
        character standing for itself; a raw newline in a template), and REFUSES, naming the form, a value it cannot read (a
        template expression, an identifier, a member expression, a concatenation, a call, a number, an empty value, an
        unterminated literal, a malformed escape) and a shape that is not a flat ladder. This plants a tenth word in EACH form
        into the real expression before its last value: a readable form yields ten words with the tenth decoded, so the
        vocabulary pin reds (ten against nine: the word not driven); an unreadable form raises with the form named. The two
        form sets are the census form space, asserted so a form added to one list is counted. Red at the head before the
        pass: the reader returned nine words for the single-quoted and dotted plants (the module stayed green under both)."""
        expr = stale_why_expr()
        self.assertIsNotNone(expr, "the anchors are gone")
        self.assertTrue(expr.rstrip().endswith(': "disagree"'), "the rig: the ladder's last value is the relation word: %r" % (expr[-40:],))
        self.assertEqual(tuple(ladder_words(expr)), STALE_WHY_WORDS, "the real expression reads as the pinned vocabulary")
        plant = lambda lit: expr[:expr.rstrip().rfind(': "disagree"')] + ": d.rev < 0 ? " + lit + ' : "disagree"'
        readable = [("double", '"negative"', "negative"), ("single", "'negative'", "negative"), ("template", "`negative`", "negative"),
                    ("double-with-dot", '"rev.negative"', "rev.negative"), ("unicode-escape", '"neg\\u0061tive"', "negative"),
                    ("unicode-brace-escape", '"neg\\u{61}tive"', "negative"), ("unicode-brace-leading-zeros", '"neg\\u{0000061}tive"', "negative"),   # seven digits: the language bounds the value, not the count (the maintainer's round 5, correctness-6)
                    ("hex-escape", '"neg\\x61tive"', "negative"),
                    ("quote-escape", "'neg\\'ative'", "neg'ative"), ("double-quote-escape", '"neg\\"ative"', 'neg"ative'),
                    ("line-continuation", '"nega\\\ntive"', "negative"), ("template-newline", "`nega\ntive`", "nega\ntive"),
                    ("non-escape", '"neg\\ative"', "negative"), ("simple-escape", '"neg\\tative"', "neg\tative")]
        for name, lit, decoded in readable:
            words = ladder_words(plant(lit))
            self.assertEqual(len(words), 10, name)
            self.assertEqual(words[8], decoded, "%s: the tenth word decoded as the language reads it" % name)
            self.assertNotEqual(tuple(words), STALE_WHY_WORDS, "%s: the vocabulary pin would red (a word not driven)" % name)
        unreadable = [("template-expression", "`neg${x}ative`", "template expression"), ("identifier", "NEGATIVE", "an identifier"),
                      ("member", "d.why", "an expression"), ("concatenation", '"neg" + "ative"', "a concatenation"),
                      ("call", 'word("negative")', "a call"), ("number", "42", "a number"), ("empty", "", "an empty value"),
                      ("unterminated", '"negative', "unterminated"), ("newline-in-string", '"nega\ntive"', "unterminated"),
                      ("bad-hex-escape", '"neg\\xZZtive"', "malformed"), ("unicode-brace-out-of-range", '"neg\\u{110000}ative"', "malformed"),   # above 0x10FFFF: the promised AssertionError, never chr()'s ValueError (the maintainer's round 5, correctness-6)
                      ("parenthesized-nested-ternary", '(d.x ? "a" : "b")', "a parenthesized expression")]
        for name, lit, named in unreadable:
            with self.assertRaises(AssertionError, msg=name) as cm:
                ladder_words(plant(lit))
            self.assertIn(named, str(cm.exception), "%s: the refusal names the form" % name)
        # the census form space: the literal forms the language permits, each read; the non-literal shapes, each refused
        self.assertEqual({n for n, _, _ in readable}, {"double", "single", "template", "double-with-dot", "unicode-escape", "unicode-brace-escape", "unicode-brace-leading-zeros", "hex-escape",
                                                       "quote-escape", "double-quote-escape", "line-continuation", "template-newline", "non-escape", "simple-escape"})
        self.assertEqual({n for n, _, _ in unreadable}, {"template-expression", "identifier", "member", "concatenation", "call", "number", "empty",
                                                         "unterminated", "newline-in-string", "bad-hex-escape", "unicode-brace-out-of-range", "parenthesized-nested-ternary"})
        # a string literal inside a CONDITION is not a value and is no word (the conditions are free; only the values are read)
        self.assertEqual(tuple(ladder_words(expr.replace("!held ?", '(d.kind === "x" || !held) ?', 1))), STALE_WHY_WORDS)
        # a ladder that is not flat (a nested ternary in a value) is refused, named
        with self.assertRaises(AssertionError) as cm:
            ladder_words(plant('d.x ? "a" : "b"'))
        self.assertIn("not a flat conditional ladder", str(cm.exception))
        # the anchor's cut: a `;` inside a literal stays inside the expression (the earlier reader stopped at the first `;`)
        self.assertEqual(ladder_words(plant('"semi;colon"'))[8], "semi;colon")

    def test_data_that_is_not_an_object_reads_null_and_an_unknown_surface_keeps_no_key(self):
        err = self.post("perf", "minute", "a string where an object goes")
        self.assertIsNone(self.rows()[-1]["data"])
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertIn("not an object", err)
        self.assertEqual(self.post("perf", "minute", ["a", "list"]), "", "said once per surface")
        self.assertIsNone(self.rows()[-1]["data"])
        self.assertEqual(self.post("perf", "minute", None), "", "a missing data is stored as null and is nothing to say")
        self.assertIsNone(self.rows()[-1]["data"])
        err = self.post("mystery", "probe", {"a": 1, "b": "two"})
        self.assertEqual(self.rows()[-1]["data"], {})
        lines = err.splitlines()
        self.assertEqual(len(lines), 2, err)
        self.assertTrue(all("a surface no allowlist names" in l and "'mystery'" in l for l in lines), err)
        self.assertEqual(self.post("mystery", "probe", {"a": 3}), "", "said once per surface and key")

    def test_the_surface_and_what_strings_are_cut_too(self):
        self.post("s" * 100, "w" * 100, {"a": 1})
        row = self.rows()[-1]
        self.assertEqual(row["surface"], "s" * 64)
        self.assertEqual(row["what"], "w" * 64)
        self.assertEqual(row["data"], {})


if __name__ == "__main__":
    unittest.main()

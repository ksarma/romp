#!/usr/bin/env python3
"""The Log writes "Kernel connection lost" when a reconnect FAILS, never at the drop (iOS item 4b, 2026-10-03).

Every return to the app logged the entry for the chat and the Feed, with an unread digit on the Log control, although the
sockets came back at once: the shell's Log wrote it at each pane's up-to-down transition, and a return always makes one (the
shim puts a stale socket down before it redials; a thawed page receives the FIN of a socket the OS dropped). The entry now
waits in the Log's `lost` until the event that says the reconnect failed, a dial that closed without ever opening, and a
socket that reopens first drops it unwritten. A close the connect cut made (a timer) fails nothing while another socket of the
page is open (the review of item 4b, 2026-10-03: on a slow network the dials a return makes together wait in line for their
handshakes, and the last of them reached the cut while every handshake was succeeding), and a close the page's own unload made
fails nothing (review round 1, 2026-10-04: Firefox delivers those closes to the unloading page). Six pieces, each executed
here under node against the code as served:

  ShimFailureWord        kernel/kernel.py _shim: a dial that never opened posts {romp:'wsFail',app,cut} to the shell after
                         its down word, cut true when the watchdog's CONNECTING arm closed it and false for a refusal (at
                         the bound's edge: a close at 15000 ms is a refusal, at 15001 ms a cut); an opened socket's close,
                         the return's abandon() and a park post none. The pane's frames reach no door of the shell's
                         (the Log's leaving latch, below, clears on the shell link's frames, not a pane's): they call no
                         window.__rompNotLeaving and post nothing to the shell but a return's wsFresh. Through
                         tests/test_pane_shim_return.py's harness.
  ShellLinkFailure       _LANDING_MOBILE_JS: the shell socket's close of a dial that never opened (refused, or its own
                         connect cut) calls window.__rompLinkFailed once, with true when its own cut timer or the tick's
                         backstop made the close (a close the browser made reads the clock: at 14999 ms a refusal, at
                         15000 ms a cut); an opened socket's close, the return's abandon and a superseded socket's late
                         close call nothing. Each dial, each open and each frame on the link calls
                         window.__rompNotLeaving (the Log's leaving latch, below), a frame whatever it carries. Through
                         tests/test_kernel_mobile.py's probe harness.
  LogWaitsForTheFailure  _LANDING_ERRS_JS: a drop alone writes nothing (the live red cue shows it); a failure word, or the
                         link's failure for every waiting pane, writes one entry per drop, and one pane's word that pane's
                         entry alone; an up drops the waiting entry; a pane not shown keeps waiting and is written once
                         shown; a parked pane, or a closed column, is dropped; a split column waits under its own key.
                         Through tests/test_error_center.py's DOM stub.
  ACutFailsNothingWhileASocketStands
                         _LANDING_ERRS_JS: a cut word, or the link's failure with true, writes nothing while the shell's link,
                         another pane's socket (a pane not shown included) or a column's stands; a refusal writes whatever
                         stands; with nothing open (a parked pane holds no socket) the cut writes. The same DOM stub.
  AnUnloadsClosesFailNothing
                         _LANDING_ERRS_JS: from a beforeunload, neither the link's failure nor a failure word writes, and
                         a pane's down word, which the shim posts just before its failure word, clears nothing (a real
                         Firefox unload's order); the shell's next dial, open or frame on its link
                         (window.__rompNotLeaving), a pane's or a column's open (its up word), and pageshow each clear the
                         latch, so a navigation that did not unload hides no later outage; a pane's wsFresh clears
                         nothing. The same DOM stub.
  ThePaneSourceCheckComesFirst
                         _LANDING_BOOT_JS's window.__rompPaneSourceOk with _LANDING_ERRS_JS (the landing merge with fork
                         main, batch 970): a wsFail or wsState word whose source is not a protocol pane of the page is
                         refused before any of the Log's own handling, so it writes, drops, clears and starts nothing; the
                         panes' own words write as before. The same DOM stub, with the boot script's real check.

One census besides, read from the source and not executed: NotLeavingCallSites holds window.__rompNotLeaving to one
definition, the Log's, and three callers, the shell link's dial, open and frame, and finds no caller under ui/ or
vscode-extension/src (the light closing check at ed1feaa79, 2026-10-05), so a second caller turns it red.

The composition in real engines (phone and desktop, healthy, slow and failing returns; reloads while a dial is connecting, and a
204 followed by an outage) is tests/test_conn_lost_log_served.py.
Synthetic only: no network, no real DOM, no real session data.
"""
import ast
import bisect
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import tokenize
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
KERNEL_PY = os.path.join(ROOT, "kernel", "kernel.py")
sys.path.insert(0, HERE)
# Hermetic state before the imports below, each of which loads the kernel source at import: the state floor here, and the
# kernel's own switches (ROMP_KERNEL_NO_OPEN, ROMP_SERVE_TOKEN) are those modules' own writes, made before their loads.
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)
import test_error_center as _errc          # noqa: E402  the modules, not their classes: an imported TestCase would be collected twice
import test_kernel_mobile as _mob          # noqa: E402
import test_pane_shim_return as _shimret   # noqa: E402


# ---- the shim's failure word ----
WORDS = r"""function words(){return parentPosts.filter(function(p){return p.romp==="wsState"||p.romp==="wsFail";}).map(function(p){return p.romp==="wsFail"?(p.cut===true?"fail-cut":p.cut===false?"fail":"fail-unmarked"):p.state;});}
"""


class ShimFailureWord(unittest.TestCase):
    def test_a_refused_dial_posts_its_down_word_then_the_failure_word(self):
        r = _shimret._run(WORDS + r"""
sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});   // the boot dial never opened: refused
out({words:words(),app:parentPosts.filter(function(p){return p.romp==="wsFail";}).map(function(p){return p.app;})});""", app="feed")
        self.assertEqual(r["words"], ["down", "fail"], "the down word first (the shell's state), then the failure the Log waits for, "
                         "marked not cut: a refusal inside the connect bound")
        self.assertEqual(r["app"], ["feed"], "the word names the pane")

    def test_an_opened_socket_closing_and_the_returns_abandon_post_no_failure_word(self):
        r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});var afterClose=words();
var t=timers.filter(function(x){return x.live&&x.fn.name==="connect";});t.forEach(function(x){x.live=false;x.fn();});open();recv({type:"ka"});
hide();NOW+=46000;show();var afterReturn=words();   // the return's fast path puts the quiet socket down (abandon) and dials at once
open();var afterReopen=words();
out({afterClose:afterClose,afterReturn:afterReturn,afterReopen:afterReopen,dials:sockets.length});""")
        self.assertEqual(r["afterClose"], ["up", "down"], "an opened socket's close is a drop, not a failed reconnect")
        self.assertEqual(r["afterReturn"], ["up", "down", "up", "down"], "the return's put-down is a drop, not a failed reconnect")
        self.assertEqual(r["afterReopen"], ["up", "down", "up", "down", "up"], "the redial opened: no failure word anywhere")
        self.assertEqual(r["dials"], 3)

    def test_a_dial_cut_by_the_watchdog_posts_the_failure_word_when_its_close_lands(self):
        r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});
var t=timers.filter(function(x){return x.live&&x.fn.name==="connect";});t.forEach(function(x){x.live=false;x.fn();});   // the redial: CONNECTING, and the path hangs
var hung=sock();NOW+=16000;tick();var cut=hung.readyState;var beforeClose=words();   // past 15 s the watchdog closes it
hung.onclose({code:1006,reason:"",wasClean:false});   // the browser's close event for the cut dial
out({cut:cut,beforeClose:beforeClose,afterClose:words()});""")
        self.assertEqual(r["cut"], 3, "the watchdog's CONNECTING arm closed the hung dial")
        self.assertEqual(r["beforeClose"], ["up", "down"])
        self.assertEqual(r["afterClose"], ["up", "down", "down", "fail-cut"],
                         "the cut dial never opened: its close is the failure, marked cut (the Log does not count it while another socket stands)")

    def test_a_refusal_after_a_long_quiet_is_not_marked_cut(self):
        # the mark reads the dial's own age at its close, not the page's: a dial made long after the last open and refused at once
        r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});NOW+=60000;sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});   // an opened socket's close, a minute in
var t=timers.filter(function(x){return x.live&&x.fn.name==="connect";});t.forEach(function(x){x.live=false;x.fn();});
NOW+=40;sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});   // the redial refused 40 ms after it was made
out({words:words()});""")
        self.assertEqual(r["words"], ["up", "down", "down", "fail"], "a refused redial is a failure the Log counts whatever stands")

    def test_the_cut_mark_at_the_bounds_edge(self):
        # review round 1 of item 4b (2026-10-04, tests-3): the mark is the watchdog arm's own test, a strict > 15000 on the dial's
        # age; a browser's close of the redial at exactly 15000 ms is a refusal and at 15001 ms a cut (no tick runs here)
        got = {}
        for ms in (15000, 15001):
            r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});
var t=timers.filter(function(x){return x.live&&x.fn.name==="connect";});t.forEach(function(x){x.live=false;x.fn();});   // the redial, made now
NOW+=%d;sock().readyState=3;sock().onclose({code:1006,reason:"",wasClean:false});   // the browser closes it, never opened
out({words:words()});""" % ms)
            got[ms] = r["words"]
        self.assertEqual(got[15000], ["up", "down", "down", "fail"], "at exactly 15 s the close is a refusal")
        self.assertEqual(got[15001], ["up", "down", "down", "fail-cut"], "past 15 s it is a cut")

    def test_a_park_posts_no_failure_word(self):
        r = _shimret._run(WORDS + r"""
open();recv({type:"ka"});park();out({words:words()});""")
        self.assertEqual(r["words"], ["up", "parked"], "a park is its own state, never a failure")

    def test_a_panes_frames_reach_no_door_of_the_shells(self):
        # review round 1 of item 4b (2026-10-04, call 1): the Log's leaving latch clears on the shell link's next frame, and a
        # pane's frames are not that event. Each pane's socket carries the link's keepalive and its own data besides, so a clear
        # on them would widen the race the call accepted (a frame between an unload's beforeunload and its closes) by every
        # pane's frames. The pane's open, its up word, is the one clear a pane makes. After it, frames call no
        # window.__rompNotLeaving, and they post nothing at all to the shell, so no listener there can take them for the clear,
        # whatever word it would read (the review of call 1's build: a new word posted on each frame, with a Log listener
        # clearing the latch on it, passed a check of the wsState and wsFail words alone). The one exception is a return's
        # first frame of data, which posts wsFresh once, the end of the reconnecting cue; the Log does not clear the latch on
        # it (AnUnloadsClosesFailNothing, below), and no other listener of the shell's calls the door on it or on anything
        # else (NotLeavingCallSites, below, holds the door's callers to the shell link's three)
        frames = r"""recv({type:"ka"});recv({type:"caps",caps:["tagEdit"],viewsSeq:null});recv({type:"ka"});sock().onmessage({data:"not json"});"""
        r = _shimret._run(WORDS + r"""
open();var afterOpen=words(),n=parentPosts.length;
""" + frames + r"""
var bootFrames=parentPosts.slice(n);
hide();NOW+=46000;show();NOW+=300;open();n=parentPosts.length;   // a return: the quiet socket put down, the redial opened
""" + frames + r"""
out({nl:NL,afterOpen:afterOpen,bootFrames:bootFrames,returnFrames:parentPosts.slice(n)});""", app="feed",
                          before="var NL=0;window.parent.__rompNotLeaving=function(){NL++;};")
        self.assertEqual(r["afterOpen"], ["up"], "the open's up word, which clears the latch in the Log")
        self.assertEqual(r["nl"], 0, "no frame of the pane's called the shell's door")
        self.assertEqual(r["bootFrames"], [], "after the boot's open the pane's frames posted nothing to the shell")
        self.assertEqual(r["returnFrames"], [{"romp": "wsFresh"}],
                         "after a return's open they posted wsFresh once, at the first frame of data, and nothing else")


# ---- the latch door's callers (the light closing check at ed1feaa79, new-A-1, 2026-10-05) ----
DOOR = "__rompNotLeaving"
_JS_PUNCT = re.compile(r">>>=|\.\.\.|===|!==|\*\*=|<<=|>>=|>>>|&&=|\|\|=|\?\?=|=>|==|!=|<=|>=|&&|\|\||\?\?|\?\.(?!\d)|\+\+|--"
                       r"|[-+*/%&|^]=|\*\*|<<|>>|.", re.S)
_JS_REGEX_AFTER = {"return", "typeof", "instanceof", "in", "of", "new", "delete", "void", "throw", "case", "do", "else", "yield",
                   "await"}
_JS_BLOCK_WORDS = {"if", "for", "while", "switch", "catch", "with"}


def _js_lex(src):
    """A script's tokens as [kind, text, start, end], kind word, num, str (a quoted string's or a template's text, between its
    delimiters), regex or punct; its comments as (start, end); and the number of delimiters left open (0 for a script read
    whole): the templates, substitutions and block comments still open at the end, plus each quoted string or regex literal
    that met an unescaped line feed, or the script's end, before its closing delimiter, which valid JavaScript never does.
    It keeps the comment, string, template and substitution states (a substitution's own braces counted; its closing brace
    is the punct `}$`) and tells a regex literal from a division by the token before the `/`. The only line break it reads
    is a line feed: a line comment runs to the next one, and a quoted string or regex literal left open ends at the first
    one no backslash escapes, and is counted. So a stray quote or slash misreads one line at most, unless a backslash ends
    that line, or a line break this lexer does not read (a carriage return, U+2028 or U+2029) breaks it, which carries it
    on to the next."""
    toks, comments, stack, loose = [], [], [], 0   # stack: "t" inside a template's text, or a substitution's brace depth
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if stack and stack[-1] == "t":
            j = i
            while j < n and src[j] != "`" and not src.startswith("${", j):
                j += 2 if src[j] == "\\" else 1
            toks.append(["str", src[i:j], i, j])
            if j >= n:
                break
            if src[j] == "`":
                stack.pop()
                i = j + 1
            else:
                stack.append(0)
                toks.append(["punct", "${", j, j + 2])
                i = j + 2
            continue
        if c.isspace():
            i += 1
            continue
        if src.startswith("//", i) or src.startswith("/*", i):
            j = src.find("\n", i) if src[i + 1] == "/" else src.find("*/", i + 2)
            loose += j < 0 and src[i + 1] == "*"   # a block comment the script's end left open
            j = n if j < 0 else j if src[i + 1] == "/" else j + 2
            comments.append((i, j))
            i = j
            continue
        if c in "'\"":
            j = i + 1
            while j < n and src[j] not in (c, "\n"):
                j += 2 if src[j] == "\\" else 1
            loose += j >= n or src[j] == "\n"
            toks.append(["str", src[i + 1:j], i, min(j + 1, n)])
            i = j + 1
            continue
        if c == "`":
            stack.append("t")
            i += 1
            continue
        p = toks[-1] if toks else None
        if c == "/" and (p is None or (p[0] == "punct" and p[1] not in (")", "]")) or (p[0] == "word" and p[1] in _JS_REGEX_AFTER)):
            j, cls = i + 1, False
            while j < n and src[j] != "\n" and (cls or src[j] != "/"):
                if src[j] == "\\":
                    j += 1
                elif src[j] == "[":
                    cls = True
                elif src[j] == "]":
                    cls = False
                j += 1
            loose += j >= n or src[j] == "\n"
            j += 1
            while j < n and (src[j].isalnum() or src[j] in "_$"):
                j += 1
            toks.append(["regex", src[i:j], i, j])
            i = j
            continue
        if c.isalpha() or c in "_$" or ord(c) > 127:
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] in "_$" or ord(src[j]) > 127):
                j += 1
            toks.append(["word", src[i:j], i, j])
            i = j
            continue
        if c.isdigit():
            j = i + 1
            while j < n and (src[j].isalnum() or src[j] in "._"):
                j += 1
            toks.append(["num", src[i:j], i, j])
            i = j
            continue
        t = _JS_PUNCT.match(src, i).group(0)
        if stack and t in ("{", "}"):
            if t == "{":
                stack[-1] += 1
            elif stack[-1]:
                stack[-1] -= 1
            else:
                stack.pop()                     # back in the template's text
                toks.append(["punct", "}$", i, i + 1])
                i += 1
                continue
        toks.append(["punct", t, i, i + len(t)])
        i += len(t)
    return toks, comments, len(stack) + loose


def _js_brackets(toks):
    """(each bracket's partner, both ways, by token index; whether every bracket closed its own kind and none was left open)."""
    pair, stack, whole = {}, [], True
    for i, t in enumerate(toks):
        if t[0] == "punct" and t[1] in ("(", "[", "{"):
            stack.append(i)
        elif t[0] == "punct" and t[1] in (")", "]", "}"):
            if not stack or "([{"[")]}".index(t[1])] != toks[stack[-1]][1]:
                whole = False
                continue
            o = stack.pop()
            pair[o], pair[i] = i, o
    return pair, whole and not stack


def _js_assigned(toks, k):
    """The member chain assigned at the `=` at index k (`ws.onopen` in `ws.onopen=function`), or ''."""
    parts, j = [], k - 1
    while j >= 0 and toks[j][0] == "word":
        parts.insert(0, toks[j][1])
        if j >= 2 and toks[j - 1][1] == ".":
            j -= 2
        else:
            break
    return ".".join(parts)


def _js_owner(toks, pair, i):
    """What the `{` at index i opens: 'function NAME', 'assigned to X.Y' (a function expression or an arrow assigned there),
    'method NAME', 'a function' (any other function) or 'block'."""
    p = toks[i - 1][1] if i else ""
    if p == "=>":
        k = (pair.get(i - 2, i - 2) if toks[i - 2][1] == ")" else i - 2) - 1   # before the arrow's parameters
        return "assigned to " + _js_assigned(toks, k) if k >= 0 and toks[k][1] == "=" and _js_assigned(toks, k) else "a function"
    if p != ")" or i - 1 not in pair:
        return "block"
    o = pair[i - 1]
    f = toks[o - 1] if o else None
    if not f or f[0] != "word" or f[1] in _JS_BLOCK_WORDS:
        return "block"
    if f[1] == "function":
        k = o - 2
        return "assigned to " + _js_assigned(toks, k) if k >= 0 and toks[k][1] == "=" and _js_assigned(toks, k) else "a function"
    return ("function " if o >= 2 and toks[o - 2][1] == "function" else "method ") + f[1]


def _js_enclosing(toks, pair, idx):
    """The functions enclosing the token at idx, outermost first, as [(owner, open brace index)]; blocks are left out."""
    opens = sorted(k for k in pair if k < idx < pair[k] and toks[k][1] == "{")
    return [(own, o) for o, own in ((o, _js_owner(toks, pair, o)) for o in opens) if own != "block"]


def _js_path(toks, pair, idx):
    return [own for own, _ in _js_enclosing(toks, pair, idx)]


def _js_ref_kind(toks, ti):
    """(kind, chain start) for the door's reference at token ti (its name, or the string key of a bracket): 'definition' (the
    name assigned, declared or given as an object key), 'call' (the reference called, plainly or as `?.(`), 'guard' (`X&&X(`
    or `typeof X==='function'&&X(`, the call that follows being its own site), 'alias' (bound to a local name, as `var nl=X;`)
    or 'unknown' (any other use: an argument, a ternary, a fallback)."""
    bracket = toks[ti][0] == "str"
    a = ti - 1 if bracket else ti
    e = ti + 2 if bracket else ti + 1          # the token after the reference
    s = a - 1 if bracket else a
    while s >= 2 and toks[s - 1][1] in (".", "?.") and toks[s - 2][0] == "word":
        s -= 2
    at = lambda k: toks[k][1] if 0 <= k < len(toks) else ""   # noqa: E731
    called = lambda k: at(k) == "(" or (at(k) == "?." and at(k + 1) == "(")   # noqa: E731
    if (at(s - 1) == "function" or at(e) in ("=", "||=", "&&=", "??=")
            or (s == a and not bracket and at(e) == ":" and at(s - 1) in ("{", ","))):
        return "definition", s
    if called(e):
        return "call", s
    chain = [t[1] for t in toks[s:e]]
    if at(e) == "&&":
        nxt = e + 1
    elif at(s - 1) == "typeof" and at(e) in ("===", "==") and at(e + 1) == "function" and at(e + 2) == "&&":
        nxt = e + 3
    else:
        nxt = None
    if nxt is not None and [t[1] for t in toks[nxt:nxt + len(chain)]] == chain and called(nxt + len(chain)):
        return "guard", s
    if (at(s - 1) == "=" and s >= 2 and toks[s - 2][0] == "word" and at(s - 3) not in (".", "?.")
            and at(e) in (";", ",", ")", "}", "")):
        return "alias", s
    return "unknown", s


def _js_alias_sites(toks, pair, bind):
    """The uses of the local alias bound at token index bind, inside the function that binds it, as [(kind, index)]: 'alias
    call' for a call (a guard `nl&&nl(` folded into its call), 'unknown' for any other use, and one 'unknown' at the binding
    when nothing uses it."""
    name = toks[bind][1]
    encl = _js_enclosing(toks, pair, bind)
    lo, hi = (encl[-1][1], pair[encl[-1][1]]) if encl else (0, len(toks))
    out = []
    for k in range(lo, hi):
        if k == bind or toks[k][0] != "word" or toks[k][1] != name or (k and toks[k - 1][1] in (".", "?.")):
            continue
        nx = [t[1] for t in toks[k + 1:k + 4]]
        if nx[:1] == ["("] or nx[:2] == ["?.", "("]:
            out.append(("alias call", k))
        elif not (nx[:2] == ["&&", name] and nx[2:3] in (["("], ["?."])):
            out.append(("unknown", k))
    return out or [("unknown", bind)]


def _door_census(src):
    """(definitions, sites, prose, whole) for the door in one script's text, read by the code (_js_lex), never by its spelling. A
    definition is the name assigned, declared or given as an object key. A site is each call, through a member (`.`, `?.`, or
    a bracket's string key) or the bare global name, plain or optional, a guard `X&&X(` or `typeof X==='function'&&X(` being
    part of its call; a local alias's calls are sites where they stand; and any other reference (an argument, a key held as a
    string, an alias the census cannot follow) is a site of its own, so it fails the role check loudly instead of passing
    unseen. Each is (kind, offset, enclosing functions). prose holds the mentions in comments, strings, regex literals and
    longer names, none of them a reference. whole says the reading balanced: every bracket closed its own kind, and no
    template, quoted string, regex literal or block comment was left open (_js_lex). That catches a misread whose stray
    delimiter is left open. A misread the reading still balances around is not caught, as when a later delimiter closes the
    stray one again, and it reaches as far as _js_lex's rule for what the stray delimiter opened: a quoted string or regex
    literal to the first line feed no backslash escapes (the lexer reads no other line break, a carriage return included), a
    line comment to the next line feed, a template or block comment to its closing delimiter, on its line or any later one,
    so the call it hides may sit on another line (the stated limit in NotLeavingCallSites). A census of a script read otherwise proves nothing, and the tests below require it."""
    toks, comments, unclosed = _js_lex(src)
    pair, whole = _js_brackets(toks)
    starts = [t[2] for t in toks]
    defs, sites, prose = [], [], []
    for m in re.finditer(re.escape(DOOR), src):
        k = m.start()
        if any(a <= k < b for a, b in comments):
            prose.append(("comment", k))
            continue
        ti = bisect.bisect_right(starts, k) - 1
        t = toks[ti] if ti >= 0 and k < toks[ti][3] else None
        if t is None:
            sites.append(("unknown", k, []))   # outside every token: a slip of the lexer, never a pass
            continue
        if t[0] == "regex" or (t[0] in ("word", "str") and t[1] != DOOR):
            prose.append((t[0], k))
            continue
        if t[0] == "str" and not (ti >= 2 and toks[ti - 1][1] == "[" and ti + 1 < len(toks) and toks[ti + 1][1] == "]"
                                  and (toks[ti - 2][0] == "word" or toks[ti - 2][1] in (")", "]"))):
            # the name as a whole string that is not a member's key: a key held for later
            sites.append(("unknown", k, _js_path(toks, pair, ti)))
            continue
        kind, s = _js_ref_kind(toks, ti)
        if kind == "definition":
            defs.append((kind, k, _js_path(toks, pair, ti)))
        elif kind == "alias":
            sites += [(ak, toks[ai][2], _js_path(toks, pair, ai)) for ak, ai in _js_alias_sites(toks, pair, s - 2)]
        elif kind != "guard":
            sites.append((kind, k, _js_path(toks, pair, ti)))
    return defs, sites, prose, whole and not unclosed


def _py_leaves(node):
    """The operands of a `+` chain, left to right."""
    out, stack = [], [node]
    while stack:
        x = stack.pop()
        if isinstance(x, ast.BinOp) and isinstance(x.op, ast.Add):
            stack += [x.right, x.left]
        else:
            out.append(x)
    return out


def _py_text(x):
    """A string literal's text (an f-string's holes as `0`), or None for any other expression."""
    if isinstance(x, ast.Constant) and isinstance(x.value, str):
        return x.value
    if isinstance(x, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "0" for v in x.values)
    return None


def _kernel_door_census():
    """The door in kernel.py. Each script unit is a string literal, or a `+` chain holding one (read with the ast module, so
    escapes are decoded and the served text is what is read; any other operand stands in as `0`), named by the variable it
    is assigned to; docstrings are not script. Returns definitions and sites as (unit's variable, line, kind, enclosing
    functions), and the mentions counted twice: in the source, and where the census read them (the units, the docstrings
    and the Python comments), so a mention outside all three fails loudly."""
    with open(KERNEL_PY, encoding="utf-8") as f:
        src = f.read()
    tree = ast.parse(src)
    docs, units, read = set(), [], [0]
    lines = sorted({src.count("\n", 0, m.start()) + 1 for m in re.finditer(re.escape(DOOR), src)})

    def visit(node, owner):
        if hasattr(node, "end_lineno"):   # a node whose lines hold no mention holds no unit naming the door: skipped
            k = bisect.bisect_left(lines, node.lineno)
            if k == len(lines) or lines[k] > node.end_lineno:
                return
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and node.body:
            first = node.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                docs.add(id(first.value))
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            owner = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            owner = node.target.id
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            chain = _py_leaves(node)
        elif isinstance(node, (ast.Constant, ast.JoinedStr)):
            chain = [node]
        else:
            chain = []
        texts = [_py_text(x) for x in chain]
        if any(t is not None for t in texts):
            if id(node) in docs:
                read[0] += node.value.count(DOOR)
                return
            text, pieces = "", []
            for x, t in zip(chain, texts):
                pieces.append((len(text), getattr(x, "lineno", 0)))
                text += "0" if t is None else t
            units.append((owner, text, pieces))
            for x, t in zip(chain, texts):   # the operands that are not literals, and an f-string's holes, may hold units too
                subs = [x] if t is None else [v for v in x.values if not isinstance(v, ast.Constant)] if isinstance(x, ast.JoinedStr) else []
                for sub in subs:
                    visit(sub, owner)
            return
        for ch in ast.iter_child_nodes(node):
            visit(ch, owner)

    visit(tree, "")
    # the Python comments naming the door, tokenized by the top-level statement that holds the mention's line (or the line
    # alone, between statements), so the whole file is not tokenized for a handful of lines
    src_lines, spans = io.StringIO(src).readlines(), []   # split at "\n" alone, as the line numbers above count
    for st in tree.body:
        spans.append((min([st.lineno] + [d.lineno for d in getattr(st, "decorator_list", [])]), st.end_lineno))
    segs = set()
    for ln in lines:
        k = bisect.bisect_right(spans, (ln, float("inf"))) - 1
        segs.add(spans[k] if k >= 0 and spans[k][0] <= ln <= spans[k][1] else (ln, ln))
    for a, b in sorted(segs):
        toks = tokenize.generate_tokens(io.StringIO("".join(src_lines[a - 1:b])).readline)
        read[0] += sum(tok.string.count(DOOR) for tok in toks if tok.type == tokenize.COMMENT)
    out = {"mentions": src.count(DOOR), "defs": [], "sites": [], "misread": []}
    for owner, text, pieces in units:
        if DOOR not in text:
            continue
        read[0] += text.count(DOOR)
        d, s, _, whole = _door_census(text)

        def line(k):
            start, lineno = max(p for p in pieces if p[0] <= k)
            return lineno + text.count("\n", start, k)
        out["defs"] += [(owner, line(k), kind, path) for kind, k, path in d]
        out["sites"] += [(owner, line(k), kind, path) for kind, k, path in s]
        if not whole:
            out["misread"].append((owner, pieces[0][1]))
    out["read"] = read[0]
    return out


_SCRIPT_EXTS = (".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs")
_MARKUP_EXTS = (".html", ".htm", ".xhtml", ".svg")


def _tree_door_census(rel):
    """(script files read, definitions, sites) under ROOT/rel, every file but node_modules and the tests (`*.test.*`), each a
    (path, kind). A script is read by _door_census, and one it misread (not whole) is a site of its own; markup that names
    the door is a site of its own too, since the census does not read the scripts inside it; any other file (styles, docs,
    data) carries no script."""
    files, defs, sites = 0, [], []
    for dirpath, dirnames, filenames in os.walk(os.path.join(ROOT, rel)):
        dirnames[:] = sorted(d for d in dirnames if d != "node_modules")
        for name in sorted(filenames):
            if ".test." in name:
                continue
            path, low = os.path.join(dirpath, name), name.lower()
            files += low.endswith(_SCRIPT_EXTS)
            with open(path, "rb") as f:
                data = f.read()
            if DOOR.encode() not in data:
                continue
            where = os.path.relpath(path, ROOT)
            if low.endswith(_SCRIPT_EXTS):
                d, s, _, whole = _door_census(data.decode("utf-8"))
                defs += [(where, kind) for kind, _, _ in d]
                sites += [(where, kind) for kind, _, _ in s] + ([] if whole else [(where, "a script the census misread")])
            elif low.endswith(_MARKUP_EXTS):
                sites.append((where, "named in markup, whose scripts this census does not read"))
    return files, defs, sites


# the three callers, by the functions that enclose them in the shell link's script (_LANDING_MOBILE_JS)
_DOOR_ROLES = {("function shellWS",): "the shell link's dial",
               ("function shellWS", "assigned to ws.onopen"): "the shell link's open",
               ("function shellWS", "assigned to ws.onmessage"): "the shell link's frame"}


def _door_role(owner, path):
    if owner != "_LANDING_MOBILE_JS":
        return None
    return _DOOR_ROLES.get(tuple(path[-2:])) or _DOOR_ROLES.get(tuple(path[-1:]))


class NotLeavingCallSites(unittest.TestCase):
    """The light closing check at ed1feaa79 (new-A-1, 2026-10-05): the Log's leaving latch clears at each call of
    window.__rompNotLeaving. ShellLinkFailure, below, executes its three callers (the shell link's dial, its open and each
    frame on it), and the pin above holds a pane's frames to calling no door. A caller anywhere else went unseen: the
    check's mutant M7, the reload banner's wsFresh listener (_STALE_JS) calling the door, kept this module green, and a call
    from a pane's wsFresh, or from any other listener, would widen the unload race call 1 accepted. So the callers are
    counted here, by the code: kernel.py's script literals, and every script under ui/ and vscode-extension/src but the
    tests (`*.test.*`). A call spelled with optional chaining, through a bracket's string key, or through a local alias
    counts; the definition, comments and strings that name the door do not; any other reference is a site of its own and
    fails the role check; and a script the lexer did not read whole (a bracket unbalanced, or a template, quoted string,
    regex literal or block comment left open) fails too. Stated limits. On the precondition that the sources are written in
    good faith, a name assembled at run time (`w["__romp" + "NotLeaving"]`), or a call held in a string and run as code, is
    not read. And the census reads a script as _js_lex reads it, which is not always as JavaScript does: a call in text the
    lexer reads otherwise is not read either, when the reading still balances. The cases pinned in
    test_the_census_reads_a_call_by_the_code come from two of the lexer's rules. It reads no line break but a line feed, so
    a line comment runs on past a carriage return ('a line comment past a carriage return'). And it tells a regex literal
    from a division by the token before the slash, so it can take either for the other: the stray delimiter opens a quoted
    string, a regex literal, a template or a comment, and the reading can balance again when a later delimiter closes it.
    How far that reaches follows the lexer's rule for what it opened: a quoted string or regex literal runs to the first
    line feed no backslash escapes, a line comment to the next line feed, a template or block comment to its closing
    delimiter, on its line or any later one. The witnesses: 'a quote closed again' (a regex read as a division, whose quote
    an apostrophe in a later comment on its line closes), 'a slash closed again' (a division read as a regex, which a later
    division on its line closes), 'a quote closed again past an escaped line feed' and 'a quote closed again past a carriage
    return' (the same quote, the call on the next line, after a line that ends in a backslash or after a carriage return),
    'a slash closed again past an escaped line feed' (the same slash, a string's line continuation before the call), 'a
    backtick closed again, lines later' (a regex read as a division, whose backtick opens a template that a backtick in a
    comment two lines down closes, the call on the line between) and 'a block comment closed again, lines later' (the same
    with a regex holding `/*`, which a `*/` in a comment two lines down closes)."""

    @classmethod
    def setUpClass(cls):
        cls.kernel = _kernel_door_census()
        cls.trees = {rel: _tree_door_census(rel) for rel in ("ui", os.path.join("vscode-extension", "src"))}

    def test_every_mention_in_kernel_py_is_read(self):
        self.assertGreater(self.kernel["mentions"], 0, "kernel.py names the door")
        self.assertEqual(self.kernel["read"], self.kernel["mentions"],
                         "every mention of the door in kernel.py is in a string literal the census read, a docstring or a "
                         "Python comment: a mention outside them is one the census cannot classify")
        self.assertEqual(self.kernel["misread"], [], "each script naming the door was read whole (every bracket closed its own "
                         "kind; no template, quoted string, regex literal or block comment left open): a script read "
                         "otherwise may hide a call behind a misread delimiter")

    def test_the_door_has_one_definition_the_logs(self):
        self.assertEqual([(o, kind) for o, _, kind, _ in self.kernel["defs"]], [("_LANDING_ERRS_JS", "definition")],
                         "window.__rompNotLeaving is defined once, by the Log (_LANDING_ERRS_JS); with no definition found "
                         "the census below counts nothing it can trust")

    def test_the_door_has_three_callers_the_shell_links_dial_open_and_frame(self):
        sites = self.kernel["sites"]
        words = {"call": "a call", "alias call": "a call through a local alias", "unknown": "a reference the census cannot follow"}
        detail = "; ".join("kernel.py about line %d, %s in %s inside %s: %s" % (
            ln, words.get(kind, kind), o or "an unnamed literal", " > ".join(p) or "the top level",
            _door_role(o, p) or "not one of the three") for o, ln, kind, p in sites)
        roles = sorted(_door_role(o, p) or "not one of the three" for o, _, _, p in sites)
        self.assertEqual(roles, sorted(_DOOR_ROLES.values()),
                         "window.__rompNotLeaving has exactly three callers, the shell link's dial, open and frame: a call "
                         "from a pane's wsFresh, or from any other listener, would widen the unload race call 1 accepted. "
                         "Found: " + detail)

    def test_no_script_under_ui_or_the_extension_calls_the_door(self):
        for rel, (files, _, _) in sorted(self.trees.items()):
            self.assertGreater(files, 0, "the census read scripts under %s" % rel)
        self.assertEqual({rel: defs + sites for rel, (_, defs, sites) in self.trees.items()}, {rel: [] for rel in self.trees},
                         "nothing under ui/ or vscode-extension/src defines or calls window.__rompNotLeaving: its callers are "
                         "the shell link's three, in kernel.py")

    def test_the_census_reads_a_call_by_the_code(self):
        x = "window." + DOOR
        cases = [
            ("the definition", x + "=function(){leaving=false;};", ["definition"], []),
            ("comments and strings", "// " + x + "()\n/* " + x + "() */var s='" + x + "()',t=`" + x + "()`;", [], []),
            ("a longer name", x + "Soon();", [], []),
            ("the guarded call", "try{" + x + "&&" + x + "();}catch(e){}", [], ["call"]),
            ("a typeof guard", "typeof " + x + "==='function'&&" + x + "();", [], ["call"]),
            ("optional chaining", x + "?.();", [], ["call"]),
            ("a bracket", "window['" + DOOR + "']();window[\"" + DOOR + "\"]?.();", [], ["call", "call"]),
            ("the bare global", DOOR + "();", [], ["call"]),
            ("a local alias", "var nl=" + x + ";nl&&nl();nl?.();", [], ["alias call", "alias call"]),
            ("an alias never called", "var nl=" + x + ";", [], ["unknown"]),
            ("an argument", "setTimeout(" + x + ",0);", [], ["unknown"]),
            ("a key held as a string", "var k='" + DOOR + "';window[k]();", [], ["unknown"]),
            ("a regex literal holding a quote", "var r=/'/g;" + x + "();", [], ["call"]),
            ("a template's substitution", "var t=`a${" + x + "()}b`;" + x + "();", [], ["call", "call"]),
        ]
        for label, js, want_defs, want_sites in cases:
            d, s, _, whole = _door_census(js)
            self.assertEqual(([kind for kind, _, _ in d], [kind for kind, _, _ in s], whole), (want_defs, want_sites, True), label)
        # a reading that does not balance is reported, never trusted. The lexer reads a regex literal after `if(a)` as a
        # division, so the regex's backtick opens a template, its quote a string, or its `/*` a block comment, that swallows
        # the call after it; and it reads the division after `i++` as a regex literal that swallows the call. A quoted string
        # or regex literal still open at an unescaped line feed or at the script's end, and a template or block comment still
        # open at the script's end, are never valid JavaScript, so each is counted as left open.
        for label, js in [("a backtick left open", "if(a)/`/.test(b);" + x + "();"),
                          ("a quote left open at the script's end", "if(a)/'/.test(b)&&" + x + "();"),
                          ("a quote left open at its line's end", "if(a)/'/.test(b)&&" + x + "();\nvar k=1;"),
                          ("a slash left open at the script's end", "i++/n;" + x + "();"),
                          ("a slash left open at its line's end", "i++/n;" + x + "();\nvar k=1;"),
                          ("a block comment left open", "if(a)/\\/*/.test(b);" + x + "();")]:
            misread = _door_census(js)
            self.assertEqual((misread[1], misread[3]), ([], False),
                             label + ": the call is hidden, and the script is reported as not read whole")
        # the stated limit's witnesses (the class docstring): each script holds text the lexer reads otherwise than
        # JavaScript does, and the call in it goes unseen in a reading that balances. A misread that a later delimiter closes
        # again reaches as far as the lexer's rule for what it opened (a quoted string or regex literal to the first line
        # feed no backslash escapes, a template or block comment to its closing delimiter, on its line or any later one), and
        # a line comment runs on past a carriage return; a lexer that reads one of these scripts right turns its witness red
        for label, js in [("a quote closed again", "if(a)/'/.test(b);" + x + "();// it's"),
                          ("a slash closed again", "i++/n;" + x + "();y=z/2;"),
                          ("a quote closed again past an escaped line feed", "if(a)/'/.test(b);//\\\n" + x + "();// it's"),
                          ("a quote closed again past a carriage return", "if(a)/'/.test(b);\r" + x + "();// it's"),
                          ("a slash closed again past an escaped line feed", "i++/n;s='a\\\nb';" + x + "();y=z/2;"),
                          ("a line comment past a carriage return", "// a note\r" + x + "();"),
                          ("a backtick closed again, lines later", "if(a)/`/.test(b);\n" + x + "();\n// a ` mark\n"),
                          ("a block comment closed again, lines later", "if(a)/\\/*/.test(b);\n" + x + "();\n// a */ mark\n")]:
            limit = _door_census(js)
            self.assertEqual((limit[1], limit[3]), ([], True),
                             label + ": the stated limit, a call hidden in a reading that balances")

    def test_the_census_names_a_sites_role_by_the_functions_enclosing_it(self):
        call = "window." + DOOR + "&&window." + DOOR + "();"
        js = ("(function(){function shellWS(){var ws=new WebSocket('u');" + call + "ws.onopen=function(){" + call + "};"
              "ws.onmessage=(ev)=>{" + call + "};}window.addEventListener('message',function(e){" + call + "});"
              "function other(){" + call + "}})();")
        sites = _door_census(js)[1]
        dial, opened, frame = _DOOR_ROLES.values()
        self.assertEqual([_door_role("_LANDING_MOBILE_JS", p) for _, _, p in sites], [dial, opened, frame, None, None],
                         "the dial in shellWS, the open and the frame in its socket's handlers; a listener and another "
                         "function are none")
        self.assertEqual([_door_role("_STALE_JS", p) for _, _, p in sites], [None] * 5,
                         "a role holds in the shell link's script alone")


# ---- the shell link's failure ----
LINKFAIL = r"""var LF=0,LFC=[];window.__rompLinkFailed=function(c){LF++;LFC.push(c===true?"cut":c===false?"refused":"unmarked");};
"""


class ShellLinkFailure(unittest.TestCase):
    def test_a_refused_dial_calls_the_link_failure_and_an_opened_sockets_close_does_not(self):
        r = _mob._run_probe(LINKFAIL + r"""
shRefuseNow();var afterRefusal=LF;           // the boot dial refused
shFireDials();shOpen();shRecv({type:'ka'});var s=shSock();s.readyState=3;s.onclose({code:1006});var afterOpenedClose=LF;
shOut({afterRefusal:afterRefusal,afterOpenedClose:afterOpenedClose,how:LFC});""")
        self.assertEqual(r["afterRefusal"], 1, "a dial that never opened: the link failed to come back")
        self.assertEqual(r["how"], ["refused"], "a refusal is marked as one: the Log counts it whatever stands")
        self.assertEqual(r["afterOpenedClose"], 1, "an opened socket's close is a drop, not a failure")

    def test_the_returns_abandon_calls_nothing_and_its_redials_connect_cut_does(self):
        r = _mob._run_probe(LINKFAIL + r"""
shOpen();shRecv({type:'ka'});shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();var afterReturn=LF;   // abandon the dead socket, dial at once
var hung=shSock();shRunDue(SHNOW+15000);var cut=hung.readyState;var beforeClose=LF;   // the path hangs: the dial's own cut closes it at SH_CONNECT_MS
hung.onclose({code:1006});
shOut({afterReturn:afterReturn,cut:cut,beforeClose:beforeClose,afterClose:LF,how:LFC});""")
        self.assertEqual(r["afterReturn"], 0, "the return's put-down of a stale socket is no failure")
        self.assertEqual(r["cut"], 3, "the dial's own cut closed it")
        self.assertEqual(r["beforeClose"], 0)
        self.assertEqual(r["afterClose"], 1, "the cut dial never opened: its close is the failure")
        self.assertEqual(r["how"], ["cut"], "marked cut (shCutHere): the Log does not count it while a pane's socket stands")

    def test_a_cut_timer_that_fires_a_ms_short_of_the_bound_is_marked_cut_by_its_own_flag(self):
        # a timer can fire while the wall clock still reads a ms short of SH_CONNECT_MS (iOS item 1a's shCutHere): the mark reads
        # the cut's own flag, not the clock alone, or this close would count as a refusal whatever stands
        r = _mob._run_probe(LINKFAIL + r"""
shOpen();shRecv({type:'ka'});shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();
var hung=shSock();var own=SHTIMERS.filter(function(t){return t.live&&t.fn.name==='shCut';});
SHNOW+=14999;own.forEach(function(t){t.live=false;t.fn();});var cut=hung.readyState;   // the dial's own cut, early by the clock
hung.onclose({code:1006});
shOut({own:own.length,cut:cut,how:LFC});""")
        self.assertEqual(r["own"], 1)
        self.assertEqual(r["cut"], 3, "the dial's own cut timer closed it")
        self.assertEqual(r["how"], ["cut"], "marked cut by shCutHere although the clock reads 14999 ms")

    def test_the_links_cut_mark_at_the_bounds_edge(self):
        # review round 1 of item 4b (2026-10-04, tests-3): a browser's close of a dial the cut timer has not closed reads the clock,
        # the ladder's complement of a refusal: at SH_CONNECT_MS - 1 a refusal, at SH_CONNECT_MS a cut
        got = {}
        for ms in (14999, 15000):
            r = _mob._run_probe(LINKFAIL + r"""
shOpen();shRecv({type:'ka'});shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();   // the return dials at once
var d=shSock();SHNOW+=%d;d.readyState=3;d.onclose({code:1006});   // the browser's close; the dial's own cut timer has not run
shOut({how:LFC});""" % ms)
            got[ms] = r["how"]
        self.assertEqual(got[14999], ["refused"], "a ms under the bound the close is a refusal")
        self.assertEqual(got[15000], ["cut"], "at the bound it is a cut")

    def test_the_watchdogs_backstop_cut_is_marked_cut_too(self):
        r = _mob._run_probe(LINKFAIL + r"""
shOpen();shRecv({type:'ka'});shHide();SHSOCKS[0].readyState=3;SHNOW+=100;shShow();   // the return dials at once
var hung=shSock();var own=SHTIMERS.filter(function(t){return t.live&&t.fn.name==='shCut';});own.forEach(function(t){t.live=false;});   // the dial's own cut timer is lost
SHNOW+=15001;shTick();var cut=hung.readyState;   // the tick's CONNECTING arm closes it past SH_CONNECT_MS
hung.onclose({code:1006});
shOut({own:own.length,cut:cut,how:LFC});""")
        self.assertEqual(r["own"], 1, "the dial armed its own cut, which this case loses")
        self.assertEqual(r["cut"], 3, "the backstop closed the hung dial")
        self.assertEqual(r["how"], ["cut"], "a close the backstop made past SH_CONNECT_MS is a cut, the ladder's complement of a refusal")

    def test_each_dial_and_each_open_of_the_link_clears_the_logs_leaving_latch(self):
        # review round 1 of item 4b (2026-10-04): the shell's next dial and its open are two of the events that clear the Log's
        # leaving latch (a beforeunload that did not unload): the shell calls window.__rompNotLeaving at both
        r = _mob._run_probe(r"""
var NL=[];window.__rompNotLeaving=function(){var s=shSock();NL.push(SHSOCKS.length+':'+(s?s.readyState:-1));};
shOpen();var afterOpen=NL.slice();          // the boot dial opens
var s=shSock();s.readyState=3;s.onclose({code:1006});var afterClose=NL.slice();   // no frame between: a frame calls it too (below)
shFireDials();                               // its redial
shOut({afterOpen:afterOpen,afterClose:afterClose,afterRedial:NL});""")
        self.assertEqual(r["afterOpen"], ["1:1"], "the open of the boot dial calls it, its socket OPEN")
        self.assertEqual(r["afterClose"], ["1:1"], "a close calls nothing")
        self.assertEqual(r["afterRedial"], ["1:1", "2:0"], "the redial calls it, its new socket CONNECTING")

    def test_each_frame_on_the_link_clears_the_logs_leaving_latch(self):
        # review round 1 of item 4b (2026-10-04, call 1): in Chromium and WebKit a beforeunload that did not unload (a 204, a
        # download) closes no socket, so the link may neither dial nor open again for a whole outage of the panes alone; a frame
        # on it shows the page is still here. Every frame calls window.__rompNotLeaving, before its type is read: the keepalive,
        # any other frame, the announced restart, one that is not JSON
        r = _mob._run_probe(r"""
var NL=[];window.__rompNotLeaving=function(){NL.push(shSock().readyState);};
shOpen();var atOpen=NL.length;
shRecv({type:'ka'});var afterKa=NL.length;
shRecv({type:'apiHealth'});var afterOther=NL.length;
shSock().onmessage({data:'not json'});var afterRaw=NL.length;
shRecv({type:'restarting'});var afterRestarting=NL.length;
shOut({atOpen:atOpen,afterKa:afterKa,afterOther:afterOther,afterRaw:afterRaw,afterRestarting:afterRestarting,states:NL});""")
        self.assertEqual(r["atOpen"], 1, "the open called it once")
        self.assertEqual((r["afterKa"], r["afterOther"], r["afterRaw"], r["afterRestarting"]), (2, 3, 4, 5),
                         "each frame on the link called it once, whatever it carried")
        self.assertEqual(r["states"], [1, 1, 1, 1, 1], "on the OPEN socket")

    def test_a_superseded_sockets_late_close_calls_nothing(self):
        r = _mob._run_probe(LINKFAIL + r"""
var a=shSock();a.readyState=3;              // the boot dial closed; its close event is still queued
SHNOW+=9000;shTick();var dialed=SHSOCKS.length;   // the watchdog's CLOSED arm dials past SH_REDIAL_MS
a.onclose({code:1006});                     // the old socket's close lands after the newer dial
shOut({dialed:dialed,lf:LF});""")
        self.assertEqual(r["dialed"], 2, "the CLOSED arm dialed a newer socket")
        self.assertEqual(r["lf"], 0, "a close delivered after a newer dial fails nothing (the superseded-close return comes first)")


# ---- the Log waits for the failure ----
LOG_DRIVER = r"""
const out = {};
const realNotify = window.__rompNotify, CONN = [];
window.__rompNotify = function (kind, text) { if (kind === 'conn') CONN.push(String(text)); return realNotify.apply(this, arguments); };
window.__rompColOf = (src) => (src && src.col) || '';   // the shell's column lookup by the sender frame, stubbed
function postFrom(src, data) { (WL['message'] || []).forEach((f) => f({ data: data, source: src })); }
// the shell socket's call, read through a guard so a Log without the hook (the fork's main before this change) still runs every step
// and is read by the steps' own assertions; out.hook says whether the hook was there
function linkFailed() { out.hook = typeof window.__rompLinkFailed === 'function'; if (out.hook) window.__rompLinkFailed(); }
const snap = () => ({ texts: notes().map((n) => n.text), unread: notes().filter((n) => !n.seen).length, ns: notes().map((n) => n.n),
  conn: CONN.length, red: EL['merr']._cls.has('has'), num: EL['merr']._num.textContent });
post({ romp: 'wsState', app: 'chat', state: 'down' });
out.drop = snap();                                         // a drop alone
post({ romp: 'wsState', app: 'chat', state: 'up' });
out.back = snap();                                         // it reopened: nothing to write
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsFail', app: 'chat' });
out.failed = snap();                                       // its reconnect failed
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsFail', app: 'chat' });
out.failedAgain = snap();                                  // the same outage fails again: one entry
post({ romp: 'wsState', app: 'chat', state: 'up' });
out.recovered = snap();
EL['rerr-clear'].fire('click');
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
post({ romp: 'wsState', app: 'waiting', state: 'down' }); // not shown (no po-waiting class)
linkFailed();
out.link = snap();                                         // the shell's link failed: every waiting shown pane
BODY.add('po-waiting');
linkFailed();
out.shownLater = snap();                                   // the Waiting pane is shown now and still down: written at the next failure
post({ romp: 'wsState', app: 'timeline', state: 'down' });
post({ romp: 'wsState', app: 'timeline', state: 'parked' });
linkFailed();
out.parked = snap();                                       // a drop that became a park is dropped
post({ romp: 'wsState', app: 'timeline', state: 'down' });
post({ romp: 'wsFail', app: 'timeline' });
out.afterPark = snap();                                    // its later drop is a drop like any other
post({ romp: 'wsFail', app: 'files' });
out.noDrop = snap();                                       // a failure word for a pane that never dropped
post({ romp: 'wsState', app: 'feed', state: 'up' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
post({ romp: 'wsState', app: 'feed', state: 'up' });
post({ romp: 'wsFail', app: 'feed' });
out.lateWord = snap();                                     // a failure word after the socket reopened
EL['rerr-clear'].fire('click');
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'down' });
out.colDrop = snap();
postFrom({ col: '2' }, { romp: 'wsFail', app: 'chat' });
out.colFailed = snap();                                    // a split column waits and is written under its own key
postFrom({ col: '3' }, { romp: 'wsState', app: 'chat', state: 'down' });
postFrom({ col: '3' }, { romp: 'wsState', app: 'chat', state: 'up' });
linkFailed();
out.colBack = snap();                                      // a column that reopened has nothing waiting
// review round 1 of item 4b (2026-10-04), keyed by pane: one pane's failure word writes that pane's waiting entry alone. Both
// panes are put up first (the chat is still down from the link step, and a down over a down records nothing), and the steps
// read the new writes, since the store coalesces an entry by its text.
post({ romp: 'wsState', app: 'chat', state: 'up' });
post({ romp: 'wsState', app: 'feed', state: 'up' });
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
const k0 = CONN.length;
post({ romp: 'wsFail', app: 'chat', cut: false });
out.oneWord = CONN.slice(k0);                              // the chat's word, the Feed's drop waiting too
post({ romp: 'wsState', app: 'feed', state: 'up' });
linkFailed();
out.oneWordThenLink = CONN.slice(k0);                      // the Feed reopened before any failure of its own
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'up' });
post({ romp: 'wsState', app: 'timeline', state: 'up' });
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsState', app: 'timeline', state: 'down' });
const k1 = CONN.length;
postFrom({ col: '2' }, { romp: 'wsFail', app: 'chat', cut: false });
out.oneColumnsWord = CONN.slice(k1);                       // a column's word, the Sessions pane's drop waiting too
// a column closed while its drop waits takes the drop with it (window.__rompColGone): a later failure writes nothing for it
post({ romp: 'wsState', app: 'timeline', state: 'up' });  // the Sessions pane reopens first, so nothing else is waiting
postFrom({ col: '4' }, { romp: 'wsState', app: 'chat', state: 'down' });
window.__rompColGone('4');
const k2 = CONN.length;
linkFailed();
out.colGone = CONN.slice(k2);
console.log(JSON.stringify(out));
"""


class LogWaitsForTheFailure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        script = _errc.HARNESS + _errc.km._LANDING_ERRS_JS + LOG_DRIVER
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        assert r.returncode == 0, "the Log's JS threw: " + r.stderr[:800]
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    CHAT = "Kernel connection lost: Chat pane (reconnecting)"

    def test_the_shell_has_a_door_for_its_links_failure(self):
        self.assertIs(self.out["hook"], True, "window.__rompLinkFailed is the Log's: the shell socket's close calls it")

    def test_a_drop_alone_writes_nothing_and_the_live_cue_shows_it(self):
        self.assertEqual(self.out["drop"], {"texts": [], "unread": 0, "ns": [], "conn": 0, "red": True, "num": "!"},
                         "nothing written, no digit; the red cue rides the live state")
        self.assertEqual(self.out["back"], {"texts": [], "unread": 0, "ns": [], "conn": 0, "red": False, "num": "!"},
                         "the socket reopened before any failure: nothing was lost, nothing is written")

    def test_a_failed_reconnect_writes_one_unread_entry_per_drop(self):
        self.assertEqual(self.out["failed"], {"texts": [self.CHAT], "unread": 1, "ns": [1], "conn": 1, "red": True, "num": "1"})
        self.assertEqual(self.out["failedAgain"], {"texts": [self.CHAT], "unread": 1, "ns": [1], "conn": 1, "red": True, "num": "1"},
                         "further failures of the same outage write nothing more")
        self.assertEqual(self.out["recovered"], {"texts": [self.CHAT], "unread": 1, "ns": [1], "conn": 1, "red": True, "num": "1"},
                         "the entry stays unread once the socket is back")

    def test_the_links_failure_writes_every_waiting_shown_pane_and_a_pane_shown_later_once_it_fails_again(self):
        self.assertEqual(self.out["link"]["texts"], [self.CHAT, "Kernel connection lost: Feed pane (reconnecting)"],
                         "the chat and the Feed, both shown; the Waiting pane is not shown")
        self.assertEqual(self.out["link"]["conn"], 3)
        self.assertEqual(self.out["shownLater"]["texts"][-1], "Kernel connection lost: Waiting pane (reconnecting)",
                         "a drop on a pane not shown keeps waiting and is written at a failure once the pane is shown")
        self.assertEqual(self.out["shownLater"]["conn"], 4, "and the chat and the Feed, already written, are not written again")

    def test_a_parked_pane_is_dropped_and_its_later_drop_counts(self):
        self.assertEqual(self.out["parked"]["conn"], 4, "a drop that became a park is not written at the link's failure")
        self.assertEqual(self.out["afterPark"]["texts"][-1], "Kernel connection lost: Sessions pane (reconnecting)")
        self.assertEqual(self.out["afterPark"]["conn"], 5)

    def test_a_failure_word_with_nothing_waiting_writes_nothing(self):
        self.assertEqual(self.out["noDrop"]["conn"], 5, "a pane that never dropped")
        self.assertEqual(self.out["lateWord"]["conn"], 5, "a failure word after the socket reopened")

    def test_one_panes_failure_word_writes_that_panes_entry_alone(self):
        # review round 1 of item 4b (2026-10-04, tests-1): with two panes down, the chat's word writes the chat's entry and leaves
        # the Feed's waiting, which its own reopening then drops; a column's word likewise leaves the Sessions pane's waiting
        self.assertEqual(self.out["oneWord"], [self.CHAT], "the chat's failure word writes the chat's entry, not the Feed's")
        self.assertEqual(self.out["oneWordThenLink"], [self.CHAT], "the Feed reopened before a failure of its own: never written")
        self.assertEqual(self.out["oneColumnsWord"], ["Kernel connection lost: chat split 2 (reconnecting)"],
                         "a column's failure word writes the column's entry, not the Sessions pane's")

    def test_a_column_closed_while_its_drop_waits_takes_the_drop_with_it(self):
        # review round 1 of item 4b (2026-10-04, tests-2): the column is shown (po-chat), so only the discard keeps it unwritten
        self.assertEqual(self.out["colGone"], [], "a closed column's waiting drop is discarded, never written at a later failure")

    def test_a_split_column_waits_under_its_own_key(self):
        self.assertEqual(self.out["colDrop"]["conn"], 5, "the column's drop alone writes nothing")
        self.assertEqual(self.out["colFailed"]["texts"], ["Kernel connection lost: chat split 2 (reconnecting)"])
        self.assertEqual(self.out["colBack"]["texts"], ["Kernel connection lost: chat split 2 (reconnecting)"],
                         "a column that reopened before the link failed has nothing waiting")


# ---- a connect cut fails nothing while another socket of the page stands ----
CUT_DRIVER = r"""
const out = {};
const realNotify = window.__rompNotify, CONN = [];
window.__rompNotify = function (kind, text) { if (kind === 'conn') CONN.push(String(text)); return realNotify.apply(this, arguments); };
window.__rompColOf = (src) => (src && src.col) || '';
let LINK = false;
window.__rompLink = () => ({ up: LINK, connT: 0 });   // the shell's publication (_LANDING_MOBILE_JS), stubbed
function postFrom(src, data) { (WL['message'] || []).forEach((f) => f({ data: data, source: src })); }
const snap = () => ({ conn: CONN.slice() });
post({ romp: 'wsState', app: 'chat', state: 'up' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
post({ romp: 'wsFail', app: 'feed', cut: true });
out.cutWhileAPaneStands = snap();                          // the Feed's dial waited in line behind the chat's and was cut
post({ romp: 'wsFail', app: 'feed', cut: false });
out.refusedWhileAPaneStands = snap();                      // a refusal fails whatever stands
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsFail', app: 'chat', cut: true });
out.cutWithNothingOpen = snap();                           // nothing open: a hung outage's cut writes
post({ romp: 'wsState', app: 'waiting', state: 'up' });   // the one socket open is a pane's the page does not show (no po-waiting)
post({ romp: 'wsState', app: 'timeline', state: 'down' });
post({ romp: 'wsFail', app: 'timeline', cut: true });
window.__rompLinkFailed(true);
out.cutWhileOnlyAHiddenPaneStands = snap();                // the kernel is answering that socket: neither cut writes
post({ romp: 'wsState', app: 'waiting', state: 'parked' }); // and it goes, so the steps below read the page as before
post({ romp: 'wsState', app: 'timeline', state: 'down' });
LINK = true;
post({ romp: 'wsFail', app: 'timeline', cut: true });
out.cutWhileTheLinkStands = snap();                        // the shell's link is open: the kernel answers
LINK = false;
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'up' });
window.__rompLinkFailed(true);
out.linkCutWhileAColumnStands = snap();                    // the shell's own dial waited behind a column's and was cut
window.__rompLinkFailed(false);
out.linkRefusedWhileAColumnStands = snap();                // the shell's dial refused: every waiting shown drop is written
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsState', app: 'files', state: 'up' });
post({ romp: 'wsState', app: 'files', state: 'parked' });
post({ romp: 'wsState', app: 'feed', state: 'up' });
post({ romp: 'wsState', app: 'feed', state: 'down' });
window.__rompLinkFailed(true);
out.linkCutWithOnlyAParkedPane = snap();                   // a parked pane holds no socket: nothing stands, the cut writes
console.log(JSON.stringify(out));
"""


class ACutFailsNothingWhileASocketStands(unittest.TestCase):
    """The review of item 4b (2026-10-03): on a slow network the dials a return makes together wait in line, since Chromium and
    Firefox hold each WebSocket handshake to a host until the one ahead of it is done, and the page's own 15 s connect cut closed
    the last of them while every handshake was succeeding. A close that cut made (the shim's word marked cut, the shell's call
    with true) now fails nothing while a socket of the page is open: the shell's link, a pane's or a column's. A refusal fails
    whatever stands, and with nothing open the cut writes as before. Through tests/test_error_center.py's DOM stub."""

    @classmethod
    def setUpClass(cls):
        script = _errc.HARNESS + _errc.km._LANDING_ERRS_JS + CUT_DRIVER
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        assert r.returncode == 0, "the Log's JS threw: " + r.stderr[:800]
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    FEED = "Kernel connection lost: Feed pane (reconnecting)"
    CHAT = "Kernel connection lost: Chat pane (reconnecting)"
    SESSIONS = "Kernel connection lost: Sessions pane (reconnecting)"
    SPLIT = "Kernel connection lost: chat split 2 (reconnecting)"

    def test_a_panes_cut_while_another_pane_stands_writes_nothing_and_a_refusal_writes(self):
        self.assertEqual(self.out["cutWhileAPaneStands"]["conn"], [], "the chat's socket is open: the Feed's cut dial was waiting its turn")
        self.assertEqual(self.out["refusedWhileAPaneStands"]["conn"], [self.FEED], "the same drop's refused dial is a failure")

    def test_a_cut_with_nothing_open_writes(self):
        self.assertEqual(self.out["cutWithNothingOpen"]["conn"], [self.FEED, self.CHAT], "no socket of the page is open: the cut is the failure")

    def test_a_socket_of_a_pane_not_shown_stands_too(self):
        # review round 1 of item 4b (2026-10-04, tests-4): on the desktop the Outline, Waiting and Files panes are hidden by
        # default and their sockets open at boot; the kernel answering one of them is what stands() asks
        self.assertEqual(self.out["cutWhileOnlyAHiddenPaneStands"]["conn"], [self.FEED, self.CHAT],
                         "the Sessions pane's cut word and the link's cut write nothing while a hidden pane's socket is open")

    def test_the_shells_link_counts_as_a_socket_that_stands(self):
        self.assertEqual(self.out["cutWhileTheLinkStands"]["conn"], [self.FEED, self.CHAT], "the Sessions pane's cut while the link stands writes nothing")

    def test_the_shells_own_cut_fails_nothing_while_a_column_stands_and_its_refusal_fails_every_waiting_drop(self):
        self.assertEqual(self.out["linkCutWhileAColumnStands"]["conn"], [self.FEED, self.CHAT], "a split column's open socket stands too")
        self.assertEqual(self.out["linkRefusedWhileAColumnStands"]["conn"], [self.FEED, self.CHAT, self.SESSIONS],
                         "the refusal writes the drop still waiting (the Sessions pane's), and nothing twice")

    def test_a_parked_pane_is_not_a_socket_that_stands(self):
        self.assertEqual(self.out["linkCutWithOnlyAParkedPane"]["conn"], [self.FEED, self.CHAT, self.SESSIONS, self.SPLIT, self.FEED],
                         "the column's and the Feed's new drops are written at the shell's cut: the parked Files pane holds no socket")


# ---- a close the page's own unload makes fails nothing (review round 1 of item 4b, 2026-10-04) ----
LEAVE_DRIVER = r"""
const out = {};
const realNotify = window.__rompNotify, CONN = [];
window.__rompNotify = function (kind, text) { if (kind === 'conn') CONN.push(String(text)); return realNotify.apply(this, arguments); };
window.__rompColOf = (src) => (src && src.col) || '';
function postFrom(src, data) { (WL['message'] || []).forEach((f) => f({ data: data, source: src })); }
function fire(k) { (WL[k] || []).forEach((f) => f({})); }
const snap = () => CONN.slice();
// the shell's door, read through a guard so a Log without it (d8a1df87e, before the latch) still runs every step and is read by
// the steps' own assertions; out.door says whether the door was there
out.door = typeof window.__rompNotLeaving === 'function';
function notLeaving() { if (out.door) window.__rompNotLeaving(); }
// the unload, in a real Firefox reload's order (review round 2 of item 4b, 2026-10-05): beforeunload first, then the closes
// Firefox delivers to the page before its pagehide. At a reload during the boot dials no pane has said a word yet, and each
// pane's or column's dial that never opened posts its down word and then its failure word (the shim's onclose: netState("down"),
// then netFail), so its down word lands while the page is leaving too, and only an up word may clear the latch
fire('beforeunload');
post({ romp: 'wsFresh' });                                 // a pane's first frame of data after a return, the one word its frames post: no clear
post({ romp: 'wsState', app: 'chat', state: 'down' });
post({ romp: 'wsFail', app: 'chat', cut: false });
post({ romp: 'wsState', app: 'feed', state: 'down' });
post({ romp: 'wsFail', app: 'feed', cut: false });
post({ romp: 'wsState', app: 'timeline', state: 'down' });
post({ romp: 'wsFail', app: 'timeline', cut: false });
postFrom({ col: '2' }, { romp: 'wsState', app: 'chat', state: 'down' });
postFrom({ col: '2' }, { romp: 'wsFail', app: 'chat', cut: false });
out.wordWhileLeaving = snap();                             // the three shown panes' and a column's down word and failure word
window.__rompLinkFailed(false);
out.linkWhileLeaving = snap();                             // the shell's dial that never opened, closed by the unload: four drops waiting
// clear 1: the shell's next dial (window.__rompNotLeaving, which the shell calls at each dial, at its open and at each frame on its link)
notLeaving();
post({ romp: 'wsFail', app: 'feed', cut: false });
out.afterTheShellsDial = snap();                           // the page stayed: the Feed's refused dial is a failure
// clear 2: a pane's socket open (its up word)
fire('beforeunload');
window.__rompLinkFailed(false);
out.leavingAgain = snap();
post({ romp: 'wsState', app: 'timeline', state: 'up' });
window.__rompLinkFailed(false);
out.afterAPanesOpen = snap();                              // the chat and the split column, still waiting, are written
// clear 3: a column's socket open
postFrom({ col: '3' }, { romp: 'wsState', app: 'chat', state: 'down' });
fire('beforeunload');
window.__rompLinkFailed(false);
out.leavingThird = snap();
postFrom({ col: '4' }, { romp: 'wsState', app: 'chat', state: 'up' });
window.__rompLinkFailed(false);
out.afterAColumnsOpen = snap();
// clear 4: pageshow (the Sessions pane's down word and failure word after the beforeunload, in the shim's order)
fire('beforeunload');
post({ romp: 'wsState', app: 'timeline', state: 'down' });
post({ romp: 'wsFail', app: 'timeline', cut: false });
out.leavingFourth = snap();
fire('pageshow');
post({ romp: 'wsFail', app: 'timeline', cut: false });
out.afterPageshow = snap();
console.log(JSON.stringify(out));
"""


class AnUnloadsClosesFailNothing(unittest.TestCase):
    """Review round 1 of item 4b (2026-10-04): Firefox closes the page's dials that never opened after beforeunload and before
    pagehide and delivers their close events while the page still runs, so a reload during a return's redial or the boot dials
    wrote one unread entry per shown pane. The Log now holds a latch, `leaving`, set on beforeunload, read by both failure
    doors before any handling of their own (window.__rompLinkFailed first; the wsFail listener right after the pane
    protocol's source check, which ThePaneSourceCheckComesFirst executes), and cleared by the page's next real event, since
    beforeunload also fires for a navigation that does not unload (a 204, a download): the shell's next dial, its open or the
    next frame on its link (window.__rompNotLeaving), a pane's or a column's open, or pageshow. Each door and each clear is executed here; the real
    engines are tests/test_conn_lost_log_served.py's unload legs. The unload posts its words in a real Firefox reload's order
    (review round 2, 2026-10-05): beforeunload first, then each pane's down word followed by its wsFail, as the shim's onclose
    posts them, so a Log that clears the latch on a down word, or on any wsState word, writes an entry for each of those panes
    and the column here. Through tests/test_error_center.py's DOM stub."""

    @classmethod
    def setUpClass(cls):
        script = _errc.HARNESS + _errc.km._LANDING_ERRS_JS + LEAVE_DRIVER
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        assert r.returncode == 0, "the Log's JS threw: " + r.stderr[:800]
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    CHAT = "Kernel connection lost: Chat pane (reconnecting)"
    FEED = "Kernel connection lost: Feed pane (reconnecting)"
    SESSIONS = "Kernel connection lost: Sessions pane (reconnecting)"
    SPLIT2 = "Kernel connection lost: chat split 2 (reconnecting)"
    SPLIT3 = "Kernel connection lost: chat split 3 (reconnecting)"

    def test_the_shell_has_a_door_to_clear_the_latch(self):
        self.assertIs(self.out["door"], True, "window.__rompNotLeaving is the Log's: the shell calls it at each dial and at its open")

    def test_the_links_failure_while_leaving_writes_nothing(self):
        self.assertEqual(self.out["linkWhileLeaving"], [], "the shell's close made by the unload: four drops waiting, none written")

    def test_a_panes_failure_word_while_leaving_writes_nothing(self):
        self.assertEqual(self.out["wordWhileLeaving"], [], "each pane's and the column's close made by the unload posts its down "
                         "word and then its failure word: the down word leaves the latch set, so the failure word writes "
                         "nothing, and a pane's wsFresh before them cleared nothing")

    def test_the_shells_next_dial_clears_the_latch(self):
        self.assertEqual(self.out["afterTheShellsDial"], [self.FEED], "the page stayed: the next failure is written")

    def test_a_panes_open_clears_the_latch(self):
        self.assertEqual(self.out["leavingAgain"], [self.FEED], "a second beforeunload sets it again")
        self.assertEqual(self.out["afterAPanesOpen"], [self.FEED, self.CHAT, self.SPLIT2],
                         "a pane's socket opened: the link's refusal writes the drops still waiting")

    def test_a_columns_open_clears_the_latch(self):
        self.assertEqual(self.out["leavingThird"], [self.FEED, self.CHAT, self.SPLIT2])
        self.assertEqual(self.out["afterAColumnsOpen"], [self.FEED, self.CHAT, self.SPLIT2, self.SPLIT3],
                         "a column's socket opened: the column still waiting is written")

    def test_pageshow_clears_the_latch(self):
        self.assertEqual(self.out["leavingFourth"], [self.FEED, self.CHAT, self.SPLIT2, self.SPLIT3])
        self.assertEqual(self.out["afterPageshow"], [self.FEED, self.CHAT, self.SPLIT2, self.SPLIT3, self.SESSIONS],
                         "the page is shown again (a back-forward restore): the Sessions pane's failure is written")


# ---- the pane protocol's source check runs before the Log's own handling (the landing merge with fork main, batch 970) ----
# the boot script's real check needs the page's origin and its iframes; the frames are this page's panes, one a split column,
# and a URL pane (data-protocol=none), a plain iframe that cannot speak the protocol
SOURCE_PAGE = r"""
global.location = { origin: 'https://TESTHOST' };
function mkWin(name, col) { return { name: name, col: col || '' }; }
const CHAT_WIN = mkWin('chat'), FEED_WIN = mkWin('feed'), TIMELINE_WIN = mkWin('timeline'), COL2_WIN = mkWin('col2', '2');
const URL_WIN = mkWin('urlPane'), STRANGER = mkWin('stranger'), NESTED = mkWin('nested');
const FRAMES = [CHAT_WIN, FEED_WIN, TIMELINE_WIN, COL2_WIN].map((w) => ({ contentWindow: w, getAttribute: () => null }))
  .concat([{ contentWindow: URL_WIN, getAttribute: (a) => (a === 'data-protocol' ? 'none' : null) }]);
document.querySelectorAll = (s) => (s === 'iframe' ? FRAMES : []);
"""

SOURCE_DRIVER = r"""
const out = {};
const realNotify = window.__rompNotify, CONN = [];
window.__rompNotify = function (kind, text) { if (kind === 'conn') CONN.push(String(text)); return realNotify.apply(this, arguments); };
const COLOF = [];   // each source a listener asked the column map about: a word refused at the check reaches no line after it
window.__rompColOf = (src) => { COLOF.push(src === window ? 'shell' : (src && src.name) || String(src)); return (src && src.col) || ''; };
const ORIGIN = location.origin;
function from(src, data, origin) { (WL['message'] || []).forEach((f) => f({ data: data, source: src, origin: origin === undefined ? ORIGIN : origin })); }
function fire(k) { (WL[k] || []).forEach((f) => f({})); }
const snap = () => CONN.slice();
// the forgers, each failing the check on one ground
const FOREIGN = [
  ['stranger', STRANGER, ORIGIN],                          // a window this page holds no iframe for
  ['urlPane', URL_WIN, ORIGIN],                            // a URL pane's iframe
  ['shell', window, ORIGIN],                               // the shell's own window
  ['nested', NESTED, ORIGIN],                              // a frame nested inside a pane, not an iframe of this page
  ['otherOrigin', CHAT_WIN, 'https://elsewhere.invalid'],  // a protocol pane's window, from another origin
  ['noSource', undefined, ORIGIN],                         // a message with no source
];
out.checkIsTheBootScripts = String(window.__rompPaneSourceOk).indexOf("querySelectorAll('iframe')") >= 0;
out.ok = { chatPane: window.__rompPaneSourceOk({ source: CHAT_WIN, origin: ORIGIN }) };
FOREIGN.forEach(([k, s, o]) => { out.ok[k] = window.__rompPaneSourceOk({ source: s, origin: o }); });
// A. a forged failure word: the chat pane's own drop waits, and each forger's wsFail for it is refused at the check
from(CHAT_WIN, { romp: 'wsState', app: 'chat', state: 'down' });
COLOF.length = 0;
FOREIGN.forEach(([k, s, o]) => from(s, { romp: 'wsFail', app: 'chat', cut: false }, o));
out.forgedFail = { conn: snap(), colOf: COLOF.slice() };
from(CHAT_WIN, { romp: 'wsFail', app: 'chat', cut: false });   // the chat pane's own failure word writes the entry that waited
out.ownFail = { conn: snap(), colOf: COLOF.slice() };
// B. a forged up word while the page is leaving: it clears neither the latch nor the Feed's waiting drop
from(FEED_WIN, { romp: 'wsState', app: 'feed', state: 'down' });
fire('beforeunload');
FOREIGN.forEach(([k, s, o]) => from(s, { romp: 'wsState', app: 'feed', state: 'up' }, o));
from(FEED_WIN, { romp: 'wsFail', app: 'feed', cut: false });   // the unload's close of the Feed's dial
out.forgedUpWhileLeaving = snap();
fire('pageshow');                                             // the page stayed
from(FEED_WIN, { romp: 'wsFail', app: 'feed', cut: false });   // the Feed's drop still waits: no forged up dropped it
out.afterPageshow = snap();
// C. a forged down word starts no drop: the shell's refused dial fails every waiting entry, and none waits
FOREIGN.forEach(([k, s, o]) => from(s, { romp: 'wsState', app: 'timeline', state: 'down' }, o));
window.__rompLinkFailed(false);
out.forgedDown = snap();
// D. a split column's own words, through the column map, still write under the column's key
COLOF.length = 0;
from(COL2_WIN, { romp: 'wsState', app: 'chat', state: 'down' });
from(COL2_WIN, { romp: 'wsFail', app: 'chat', cut: false });
out.column = { conn: snap(), colOf: COLOF.slice() };
console.log(JSON.stringify(out));
"""


class ThePaneSourceCheckComesFirst(unittest.TestCase):
    """The landing merge with fork main (batch 970, which brought upstream's pane registry in the fold 965): every message
    listener of the shell reads the boot script's fail-closed check, window.__rompPaneSourceOk(e), as its first statement, so
    a {romp:...} word acts only when its immediate source is a same-origin iframe of the page that speaks the protocol. The
    merge put that check first in the Log's wsFail listener, ahead of the leaving latch and the rest of the Log's handling, and
    took upstream's opening line for the wsState listener, ahead of the latch clear on an up word. Executed here with the
    boot script's real check in place of the DOM stub's: a word from a window the page holds no iframe for, a URL pane, the
    shell itself, a frame nested in a pane, another origin or no source writes no entry, drops no waiting entry, clears no
    latch and starts no drop, and reaches no line after the check (the column map is never asked about it); the panes' own
    words, a split column's included, write as before. The check's position as the FIRST statement is held by
    tests/test_pane_registry.py's listener census: the latch read and the check are both early returns with no effect, so
    their order between themselves has no behaviour to execute."""

    @classmethod
    def setUpClass(cls):
        script = _errc.HARNESS + SOURCE_PAGE + _errc.km._LANDING_BOOT_JS + _errc.km._LANDING_ERRS_JS + SOURCE_DRIVER
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
            f.write(script)
            path = f.name
        try:
            r = subprocess.run(["node", path], capture_output=True, text=True, timeout=30)
        finally:
            os.unlink(path)
        assert r.returncode == 0, "the Log's JS threw: " + r.stderr[:800]
        cls.out = json.loads(r.stdout.strip().splitlines()[-1])

    CHAT = "Kernel connection lost: Chat pane (reconnecting)"
    FEED = "Kernel connection lost: Feed pane (reconnecting)"
    SPLIT2 = "Kernel connection lost: chat split 2 (reconnecting)"

    def test_the_check_is_the_boot_scripts_and_rules_on_each_forger(self):
        self.assertIs(self.out["checkIsTheBootScripts"], True, "the boot script's definition replaced the DOM stub's")
        self.assertEqual(self.out["ok"], {"chatPane": True, "stranger": False, "urlPane": False, "shell": False, "nested": False,
                                          "otherOrigin": False, "noSource": False},
                         "a protocol pane passes and each forger fails, so the steps below read the check, not a stub")

    def test_a_forged_failure_word_is_refused_before_the_logs_handling(self):
        self.assertEqual(self.out["forgedFail"], {"conn": [], "colOf": []},
                         "no forger's wsFail writes the chat pane's waiting entry, and none reaches the column map, the first "
                         "line after the latch and the word's own checks: the source check ran before them")
        self.assertEqual(self.out["ownFail"], {"conn": [self.CHAT], "colOf": ["chat"]},
                         "the chat pane's own failure word writes the entry, which waited through the forgeries")

    def test_a_forged_up_word_clears_neither_the_latch_nor_a_waiting_drop(self):
        self.assertEqual(self.out["forgedUpWhileLeaving"], [self.CHAT],
                         "after beforeunload a forged up word is refused before the latch clear: the unload's close of the "
                         "Feed's dial writes nothing")
        self.assertEqual(self.out["afterPageshow"], [self.CHAT, self.FEED],
                         "the Feed's drop still waited (no forged up marked it up), so its failure after pageshow is written")

    def test_a_forged_down_word_starts_no_drop(self):
        self.assertEqual(self.out["forgedDown"], [self.CHAT, self.FEED],
                         "the shell's refused dial fails every waiting entry, and no forged down word left one for the "
                         "Sessions pane")

    def test_a_split_columns_own_words_still_write_under_its_key(self):
        self.assertEqual(self.out["column"], {"conn": [self.CHAT, self.FEED, self.SPLIT2], "colOf": ["col2", "col2"]},
                         "the column's down word and failure word each pass the check and ask the column map, and the "
                         "failure writes the column's entry")


if __name__ == "__main__":
    unittest.main()

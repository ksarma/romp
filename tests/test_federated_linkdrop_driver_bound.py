"""The link-drop lab's driver ends before CI ends the served process (2026-09-19).

CI's served job runs every served lab in ONE pytest process under pytest-timeout's per-test cap (600 s, thread method:
the process ends with a thread dump and no summary), and tests/test_federated_linkdrop_served.py drives its two kernels
and the browser in setUpClass. Round 2's review found the node driver's subprocess timeout at 900 s, above the cap, with
waits that alone summed past it: a drive degraded by one unmet precondition (a supervisor that never re-read the row up)
would have been ended by pytest-timeout inside setUpClass, taking every served lab collected after the module with it
and leaving no summary for the labs already run. The module now bounds the drive in three layers, pinned here without a
kernel or a browser:
- the arithmetic: the driver's worst case (its shared wait budget plus the bounded work between the waits) is under the
  subprocess timeout, which is under CI's cap with room for the rest of setUpClass, and the cap the constant is chosen
  against is the one the workflow's served step states; and the down dwell holds DOWN_WINDOW_MARGIN times wait_ms, the
  cap waitVisible puts on the delivery the gate legs measure it against, plus DOWN_READ_ROOM_MS (a phase's delivery is
  stamped after the reads that follow its wait, so a wait that resolved at the cap's edge is stamped past it by their
  duration; a wait that ran to its cap is refused by the margin leg itself, seen.expired, beside the visibility legs),
  so that pin holds for every drive whose link-up waits all resolved and showed, the reads inside the room;
- the bytes sent: _drive hands subprocess.run the timeout and writes the budget, the wait caps and the settle values
  into the driver's cfg from the class that drives (a stub class, the driver replaced by a spy), and the driver it writes
  opens with the budget and reads every one of those keys;
- the budget under node: BUDGET_JS, the driver's opening lines, run with a clock of its own: a wait that never comes
  spends the budget once and is recorded, every later wait returns at once, no timeout handed on is ever 0 (playwright
  reads 0 as no timeout), and a wait that comes spends only what it took;
- the premise of the arithmetic (round 2, fresh-1): every wait the driver places is one the sum counts. A census of the
  driver's wait call sites against a table of the forms it may use requires each playwright wait to carry
  timeout: budget.capped(...) as the WHOLE value (round 3: `budget.capped(x) + N`, `* N` or a second argument left the
  value uncapped and the census green; a wait with no timeout key inherits playwright's 30 s default, which no budget
  caps: the driver never calls setDefaultTimeout) and each waitForTimeout to draw on the budget or be one of the two fixed
  dwells driver_worst_case_s counts; the navigations (goto, reload, goBack, goForward) are wait forms too; and an unlisted
  wait form or an auto-waiting action fails by name. Round 4 added the other half of that premise as an ALLOW-list: every
  method the driver calls on a playwright receiver (a page, a locator made from one, the context, the browser, chromium)
  must be one ALLOWED_CALLS names for that receiver kind, because a deny-list's gap passes (the round-3 head listed the
  auto-waiting ACTIONS and not the auto-waiting locator READS, so `locator(...).textContent()`, which inherits playwright's
  30 s default that no budget caps, kept the census green while the pinned headroom under the subprocess timeout is 7.5 s
  and 27.5 s); `evaluate` is allowed on a page receiver only, since a locator's evaluate auto-waits. The fixer pass of that
  round closed the walk's own gap: the walk follows chains on the names it knows (page, pages, context, browser, chromium),
  so a receiver or a locator reachable under any other name was invisible to it and a bound locator's read left the census
  green; the three ways a receiver leaves the walk (a binding or assignment to a name outside WALKED_NAMES, a locator-making
  call whose chain ends on it, a receiver passed bare to anything but Object.keys or a driver helper whose one parameter is a
  walked name) are refused by name.

Three more pins ride here because the module they pin has no kernel-free test of its own: LinkDropBothNew gates on no
knob, wherever such a gate could sit (a class-level skip, setUpClass, _knobs), and LinkDropOldLocal skips as optional
(round 1's high, closed by a value; round 2 asked for the pin, round 3 for the property over every site); a hub a knob
asked for whose bundle cannot be made ready, or whose root holds no kernel, is an error through _boot, while this
checkout's own bundle failing to build stays a skip (round 1's tests-3, ruled twice); the old-hub storm's allowance
for an empty phase is keyed on a notice post that found the Outline without an open, served relay socket and then on a
whole keyed feed frame after the bundle's last notice, over a synthetic record, and the floor it guards reds on a planted
miss with the frame present (round 4: the frame alone excused 47 of 75 recorded windows); and the
gate's control in time takes a phase's waitedMs as a delivery only when every wait behind it resolved and its visibles
showed, over a synthetic record for each class (round 5: a wait that ran to its cap measured as a delivery at the cap).

Synthetic: no kernel, no browser; stub classes over scratch directories.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import test_federated_linkdrop_served as L   # noqa: E402  the lab module: the constants, BUDGET_JS, _drive

CFG_KEYS = ("driverBudgetMs", "pageWaitMs", "phaseSettleMs", "quietTries", "quietStepMs")   # plus waitsMs.<mark>, below
KNOBS = ("ROMP_LINKDROP_LAB", "ROMP_CORNER_OLD_HUB_ROOT", "ROMP_LINKDROP_OLD_HUB_BUILD", "ROMP_LINKDROP_HUB_ROOT")   # the lab's four

# Every wait form the driver may place, and what caps it (the premise of driver_worst_case_s). "timeout": a playwright wait
# (the waitFor* family and the navigations goto, reload, goBack and goForward, which wait under the same 30 s default) whose
# options must carry exactly one timeout key whose WHOLE value is one budget.capped(...) call (CAPPED); "dwell":
# waitForTimeout, whose argument is one such call or one of FIXED_DWELLS, the two fixed waits the arithmetic counts by name;
# "budget": the budget's own poll (const waitFor = budget.waitFor), whose positional timeout makeBudget caps inside (the node
# test below). The two fetches (ctl and tunnelsStatus) carry no timeout and are the acknowledged driver_error road: a hang
# there ends the node process at DRIVER_TIMEOUT_S, which the arithmetic does not count and _drive reports as "driver timed out".
WAIT_FORMS = {"goto": "timeout", "reload": "timeout", "goBack": "timeout", "goForward": "timeout",
              "waitForFunction": "timeout", "waitForSelector": "timeout", "waitForEvent": "timeout",
              "waitForURL": "timeout", "waitForLoadState": "timeout", ".waitFor": "timeout", "waitForTimeout": "dwell", "waitFor": "budget"}
FIXED_DWELLS = ("cfg.phaseSettleMs", "cfg.downDwellMs")
# exactly one capped call and nothing around it: `budget.capped(x) + 600000`, `budget.capped(x) * 30` and `budget.capped(x, 99999)`
# all begin with the call and none is bounded by the budget (round 3)
CAPPED = re.compile(r"budget\.capped\(\s*[\w.]+\s*\)")
AUTO_WAITING_ACTIONS = ("click", "dblclick", "fill", "press", "type", "check", "uncheck", "hover", "tap", "selectOption", "setInputFiles", "dragTo", "focus")
# The calls the driver may make on a playwright receiver, by the receiver's kind (round 4, regression-2): an ALLOW-list, so a
# call it does not name fails by name whatever it is, where a deny-list's gap passes. Measured at this head (the refuter's
# probe against the lab's playwright): locator.textContent, innerText, ariaSnapshot and locator.evaluate auto-wait under the
# 30 s default; count, first, isVisible, isHidden, allTextContents and allInnerTexts do not. Only what the driver calls today
# is listed: `evaluate` on a PAGE receiver (snap, provText) and not on a locator; the wait forms here (goto, waitForFunction,
# waitForTimeout, waitFor) are the census's above, which requires their timeouts capped. A new call is added here with its
# receiver kind once it is known not to wait, or added to WAIT_FORMS as a wait the budget caps.
ALLOWED_CALLS = {"page": ("locator", "evaluate", "goto", "waitForFunction", "waitForTimeout", "on", "addInitScript"),
                 "locator": ("first", "count", "waitFor"),
                 "context": ("newPage",), "browser": ("newContext", "close"), "chromium": ("launch",)}
LOCATOR_MAKERS = ("locator", "first", "last", "nth", "filter", "and", "or", "getByText", "getByRole", "getByTestId", "getByLabel", "getByPlaceholder", "getByAltText", "getByTitle")
RECEIVERS = re.compile(r"\b(?P<recv>pages\.\w+|pages\[(?:[^\[\]]|\[[^\[\]]*\])*\]|page|context|browser|chromium)(?=\s*\.)")
MEMBER = re.compile(r"\s*\.\s*(?P<name>[\w$]+)\s*")
# The names the walk follows: a playwright receiver, or a locator made from one, reachable under any OTHER name is invisible to
# it, so the census refuses the three ways a receiver leaves the walk (round 4's fixer pass: `const row = pages.feed.locator(sel);
# await row.textContent();` and `const fp = pages.feed; await fp.locator(sel).textContent();` left the allow-list green): a binding
# or assignment whose target is not a walked name (BINDING against WALKED_TARGET), a locator-making call whose chain ends on it
# (stored, returned or passed on; _receiver_calls reports it), and a receiver passed bare as an argument (PASSED_BARE), allowed
# only to BARE_CALLEES or to a driver helper whose one parameter is itself a walked name (HELPER_PARAM: snap's is `page`).
WALKED_NAMES = ("page", "pages", "context", "browser", "chromium")
RECV_EXPR = r"pages(?:\.\w+|\[[^\[\]]*\])?|page|context|browser|chromium"
BINDING = re.compile(r"(?:\b(?:const|let|var)\s+)?(?P<target>[\w$]+(?:\s*(?:\.\s*[\w$]+|\[[^\[\]]*\]))*|[\[{][^=;]*[\]}])\s*(?<![=!<>])=(?![=>])\s*(?:await\s+)?(?P<recv>%s)(?![\w$])" % RECV_EXPR)
WALKED_TARGET = re.compile(r"page|context|browser|chromium|pages(?:\.\w+|\[[^\[\]]*\])?")
PASSED_BARE = re.compile(r"(?:(?P<callee>[\w$]+(?:\.[\w$]+)*)\s*\(|,)\s*(?P<recv>%s)\s*(?=[,)])(?!\s*\)\s*=>)" % RECV_EXPR)   # not an arrow's parameter list
PARAM_LIST_HEADS = ("async", "function")   # `async (page) =>` and `function (page)` declare a parameter, they pass nothing
HELPER_PARAM = re.compile(r"\bconst\s+(?P<name>[\w$]+)\s*=\s*(?:async\s*)?\(\s*(?P<param>[\w$]+)\s*\)\s*=>")
BARE_CALLEES = ("Object.keys",)
RECEIVER_MAKERS = ("launch", "newContext", "newPage")   # the calls that return a receiver (chromium, browser, context); with LOCATOR_MAKERS, a chain ending on one binds a receiver


def _strip_js_comments(text):
    """The driver's // comments removed (a full-line comment, or one after ; { or }), so a `timeout:` in BUDGET_JS's own
    comment is not a site. The driver carries no // in a string or a regex; the census asserts none is left."""
    text = re.sub(r"(?m)^\s*//.*$", "", text)
    return re.sub(r"(?m)(?<=[;{}])\s*//.*$", "", text)


def _call_args(text, i):
    """The text between the parenthesis at `i` and its match, string literals skipped."""
    depth, j, quote = 0, i, None
    while j < len(text):
        ch = text[j]
        if quote:
            if ch == "\\":
                j += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"`":
            quote = ch
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
        j += 1
    raise AssertionError("no closing parenthesis from %d" % i)


# a wait-shaped call with the receiver before its dot captured whole, every dotted segment of it (round 4): `budget.waitFor(` is
# the poll; `mybudget.waitFor(`, `obj.budget.waitFor(` and `this.budget.waitFor(` are a locator's or a member's. The round-3
# lookback read the seven characters BEFORE the dot and compared them to "budget.", which could never match, so the receiver
# form of the poll classified as an uncapped locator wait, green only because the driver uses the alias; round 4's first capture
# took one segment, so a receiver whose LAST segment was budget read as the poll (the fixer pass)
WAIT_SITE = re.compile(r"(?:(?P<recv>(?:[\w$]+\.)*[\w$]*)(?P<dot>\.))?\b(?P<name>goto|reload|goBack|goForward|waitFor\w*)\s*\(")


def _wait_sites(text):
    """Every call site of a wait-shaped name in the (comment-stripped) driver: (form, args, line), the navigations included
    (round 3: `page.reload()` waited under playwright's default and was neither listed nor flagged). `.waitFor(` on a locator
    is the form ".waitFor"; a bare `waitFor(` or `budget.waitFor(` is the budget's poll, the receiver compared whole across its
    dots (WAIT_SITE), so a receiver merely ending in budget, or whose last segment is budget (`obj.budget`), is a locator's."""
    out = []
    for m in WAIT_SITE.finditer(text):
        name = m.group("name")
        if name == "waitFor" and m.group("dot") and m.group("recv") != "budget":
            name = ".waitFor"
        out.append((name, _call_args(text, m.end() - 1), text.count("\n", 0, m.start()) + 1))
    return out


def _receiver_calls(text, escapes=None):
    """Every method call chained on a playwright receiver expression in the (comment-stripped) driver: (kind, method, line).
    The receivers are the driver's names for them (`page`, `pages.<app>`, `pages[...]`: a page; `context`; `browser`;
    `chromium`), the chain is walked call by call with _call_args skipping each call's arguments, and the kind becomes
    `locator` after a locator-making call (LOCATOR_MAKERS), so `pages.feed.locator(sel).first().waitFor({...})` yields
    (page, locator), (locator, first), (locator, waitFor). A member read without a call ends the chain. A chain that ends
    ON a locator-making call left that locator unconsumed (stored, returned or passed on, to be read under a name the walk
    does not follow) and is appended to `escapes` as (line, what) when a list is given (round 4's fixer pass)."""
    out = []
    for m in RECEIVERS.finditer(text):
        kind = "page" if m.group("recv").startswith("page") else m.group("recv")
        j, last = m.end(), None
        while True:
            c = MEMBER.match(text, j)
            if not c or text[c.end():c.end() + 1] != "(":
                break
            name = c.group("name")
            out.append((kind, name, text.count("\n", 0, m.start()) + 1))
            last = name
            if name in LOCATOR_MAKERS:
                kind = "locator"
            j = c.end() + 1 + len(_call_args(text, c.end())) + 1   # past the call's closing parenthesis
        if escapes is not None and last in LOCATOR_MAKERS:
            escapes.append((text.count("\n", 0, m.start()) + 1, "%s(...) left its chain unconsumed" % last))
    return out


def _escaped_receivers(text):
    """The bindings and bare passes of a playwright receiver in the (comment-stripped) driver, as (line, what, allowed): a
    binding or assignment whose right side begins with a receiver name and YIELDS a receiver (no call after it, a member read
    without a call, or a chain ending on a receiver-making or locator-making call: RECEIVER_MAKERS, LOCATOR_MAKERS) is allowed
    only when its target is a walked name (WALKED_TARGET: `const context = await browser.newContext(...)`, `pages[app] = page`),
    while a chain ending on any other call binds a value, not a receiver (`const c = await pages.feed.locator(s).count()`), and
    is not a binding here; a receiver passed bare as an argument is allowed only to BARE_CALLEES or to a driver helper whose one
    parameter is a walked name (HELPER_PARAM), since the walk follows the parameter by its name. Everything else here is a
    receiver reaching a name the walk does not follow."""
    out = []
    for m in BINDING.finditer(text):
        j, last = m.end("recv"), None
        while True:
            c = MEMBER.match(text, j)
            if not c or text[c.end():c.end() + 1] != "(":
                break
            last = c.group("name")
            j = c.end() + 1 + len(_call_args(text, c.end())) + 1
        if last is not None and last not in RECEIVER_MAKERS and last not in LOCATOR_MAKERS:
            continue   # the chain ends on a call that returns a value: nothing playwright is bound
        target = re.sub(r"\s+", "", m.group("target"))
        out.append((text.count("\n", 0, m.start()) + 1, "%s = %s" % (target, m.group("recv")), bool(WALKED_TARGET.fullmatch(target))))
    helpers = {h.group("name"): h.group("param") for h in HELPER_PARAM.finditer(text)}
    for m in PASSED_BARE.finditer(text):
        callee = m.group("callee")
        if callee in PARAM_LIST_HEADS:
            continue
        out.append((text.count("\n", 0, m.start()) + 1, "%s(%s)" % (callee or "<a later argument>", m.group("recv")),
                    callee in BARE_CALLEES or helpers.get(callee) in WALKED_NAMES))
    return out


def _without_knobs():
    """The environment with the lab's four knobs unset, the rest kept (a bare clear=True would take PATH and HOME too)."""
    return mock.patch.dict(os.environ, {k: v for k, v in os.environ.items() if k not in KNOBS}, clear=True)

BUDGET_HARNESS = r"""
const out = { timeouts: [] };
let clock = 0; const now = () => clock; const sleep = async (ms) => { clock += ms; };
const res = {};
const b = makeBudget({ budgetMs: 1000, now, sleep, out });
res.capBig = b.capped(5000);
res.capSmall = b.capped(300);
let polls = 0;
res.r1 = await b.waitFor(async () => { polls++; return false; }, 5000, "w1");
res.clock1 = clock; res.polls1 = polls; res.timeouts1 = out.timeouts.slice(); res.left1 = b.left();
const c = clock;
res.r2 = await b.waitFor(async () => false, 5000, "w2");
res.spent2 = clock - c; res.timeouts2 = out.timeouts.slice(); res.capSpent = b.capped(5000);
const out2 = { timeouts: [] }; clock = 0; let n = 0;
const b2 = makeBudget({ budgetMs: 1000, now, sleep, out: out2 });
res.r3 = await b2.waitFor(async () => ++n >= 3, 5000, "w3");
res.clock3 = clock; res.left3 = b2.left(); res.timeouts3 = out2.timeouts;
console.log("RESULT:" + JSON.stringify(res));
"""


class TheDriverEndsBeforeCI(unittest.TestCase):
    maxDiff = None

    def _served_step_line(self):
        with open(os.path.join(ROOT, ".github", "workflows", "ci.yml"), encoding="utf-8") as f:
            ci = f.read()
        served = [ln for ln in ci.splitlines() if "tests/test_*_served.py" in ln and "pytest" in ln]
        self.assertEqual(len(served), 1, "the served step's one pytest line: %r" % (served,))
        return served[0]

    def test_the_arithmetic_and_the_cap_it_is_chosen_against(self):
        for cls in (L.LinkDropBothNew, L.LinkDropOldLocal):
            worst = L.driver_worst_case_s(cls)
            self.assertGreater(worst, cls.driver_budget_ms / 1000.0 + L.hub_restart_bound_s(),
                               "the worst case counts more than the budget and the restart (the bundles, the dwell, the settles): %r" % (worst,))
            self.assertLess(worst, L.DRIVER_TIMEOUT_S, "%s's driver at its worst (%.1f s) ends before its subprocess timeout (%d s)" % (cls.__name__, worst, L.DRIVER_TIMEOUT_S))
            self.assertGreaterEqual(cls.down_dwell_ms, L.DOWN_WINDOW_MARGIN * cls.wait_ms + L.DOWN_READ_ROOM_MS,
                                    "%s's down dwell (%d ms) holds DOWN_WINDOW_MARGIN (%g) times wait_ms (%d ms), the cap waitVisible puts on the delivery the "
                                    "gate legs measure the dwell against, plus DOWN_READ_ROOM_MS (%d ms) for the reads after the wait (seen.waitedMs is stamped "
                                    "after visible()'s reads, so a wait that resolved at the cap's edge is stamped past it by their duration; a wait that ran "
                                    "to its cap is refused by the margin leg itself, seen.expired, never measured); with the room the per-drive margin pin "
                                    "holds for every drive whose link-up waits all resolved and showed, the reads inside the room (DOWN_READ_ROOM_MS over "
                                    "DOWN_WINDOW_MARGIN, %d ms), and reds only for a window shorter than that"
                                    % (cls.__name__, cls.down_dwell_ms, L.DOWN_WINDOW_MARGIN, cls.wait_ms, L.DOWN_READ_ROOM_MS, int(L.DOWN_READ_ROOM_MS / L.DOWN_WINDOW_MARGIN)))
        self.assertGreaterEqual(L.DOWN_WINDOW_MARGIN, 2.0, "round 2's ruling: the while-down read comes at least twice this drive's slowest link-up delivery after phase D's "
                                                          "post; widen down_dwell_ms, never the margin. The floor is pinned here because the margin pin's cells are derived from "
                                                          "the constant and shrink with it (a lowered margin passes them all); the relation pin above ceilings it at 2.0 for the "
                                                          "dwell and the cap as they stand, so the constant is bracketed from both sides")
        self.assertLessEqual(L.DRIVER_TIMEOUT_S + L.BOOT_ROOM_S, L.CI_TEST_TIMEOUT_S,
                             "the subprocess timeout leaves BOOT_ROOM_S of CI's per-test cap for the rest of setUpClass")
        served = self._served_step_line()
        self.assertIn("--timeout=%d --timeout-method=thread" % L.CI_TEST_TIMEOUT_S, served,
                      "CI_TEST_TIMEOUT_S is the cap the served step runs under: %r" % (served,))
        # The premise (round 2, fresh-1): the sum is an upper bound only if every wait the driver places is one it counts.
        driver = _strip_js_comments(L.DRIVER)
        self.assertNotIn("//", driver, "a // the comment stripper cannot see past (a new comment shape, or // inside a string): teach _strip_js_comments")
        sites = _wait_sites(driver)
        self.assertTrue(sites, "the census saw the driver's wait sites")
        unlisted = sorted({(name, ln) for name, _, ln in sites if name not in WAIT_FORMS})
        self.assertEqual(unlisted, [], "a wait form WAIT_FORMS does not list (name it there with what caps it, and count it in driver_worst_case_s if fixed): %r" % (unlisted,))
        uncapped, dwells = [], set()
        for name, args, ln in sites:
            rule = WAIT_FORMS[name]
            if rule == "timeout":
                keys = [k.strip() for k in re.findall(r"\btimeout\s*:\s*([^,}]+)", args)]
                if len(keys) != 1 or not CAPPED.fullmatch(keys[0]):
                    uncapped.append((ln, name, keys or "no timeout key (playwright's 30 s default, which no budget caps)"))
            elif rule == "dwell":
                a = args.strip()
                if CAPPED.fullmatch(a):
                    continue
                dwells.add(a)
                if a not in FIXED_DWELLS:
                    uncapped.append((ln, name, a))
        self.assertEqual(uncapped, [], "every wait the driver places draws on the budget (its timeout, or its dwell, is exactly one budget.capped(...) "
                                       "call and nothing more) or is a fixed dwell driver_worst_case_s counts (%r); these do neither, so the arithmetic is not "
                                       "a bound: %r" % (FIXED_DWELLS, uncapped))
        self.assertEqual(sorted(dwells), sorted(FIXED_DWELLS), "the fixed dwells the driver places are exactly the two the arithmetic counts "
                                                                "(down_dwell_ms and phases x PHASE_SETTLE_MS): %r" % (sorted(dwells),))
        self.assertLessEqual({"goto", "waitForFunction", ".waitFor", "waitForTimeout", "waitFor"}, {name for name, _, _ in sites},
                             "the census is not vacuous: the forms the driver uses today are all seen: %r" % (sorted({name for name, _, _ in sites}),))
        actions = re.findall(r"\.(%s)\s*\(" % "|".join(AUTO_WAITING_ACTIONS), driver)
        self.assertEqual(actions, [], "an auto-waiting playwright action in the driver (it waits under playwright's 30 s default, which no budget caps; the driver reads pages, it does not act on them): %r" % (actions,))
        # the allow-list (round 4): every call on a playwright receiver is one ALLOWED_CALLS names for that receiver's kind; the
        # deny-list above is the backstop it was, and its gap (the auto-waiting locator READS: textContent, innerText, ariaSnapshot,
        # a locator's evaluate, each under the 30 s default) is what this refuses
        escapes = []
        calls = _receiver_calls(driver, escapes)
        self.assertTrue(calls, "the walk saw the driver's calls on its playwright receivers")
        unlisted = sorted({(kind, name, ln) for kind, name, ln in calls if name not in ALLOWED_CALLS.get(kind, ())})
        self.assertEqual(unlisted, [], "a call on a playwright receiver that ALLOWED_CALLS does not name for its kind (an auto-waiting read such as a locator's "
                                       "textContent, innerText, ariaSnapshot or evaluate inherits playwright's 30 s default, which no budget caps, and one such read "
                                       "outruns the headroom under the subprocess timeout; a call known not to wait is added there by receiver kind, a wait goes "
                                       "to WAIT_FORMS): %r" % (unlisted,))
        self.assertLessEqual({("page", "locator"), ("page", "evaluate"), ("page", "goto"), ("page", "waitForFunction"), ("page", "waitForTimeout"), ("page", "on"),
                              ("page", "addInitScript"), ("locator", "first"), ("locator", "count"), ("locator", "waitFor"), ("context", "newPage"),
                              ("browser", "newContext"), ("browser", "close"), ("chromium", "launch")}, {(kind, name) for kind, name, _ in calls},
                             "the walk is not vacuous: every receiver call the driver makes today is seen, by kind: %r" % (sorted({(kind, name) for kind, name, _ in calls}),))
        # the walk's own gap (round 4's fixer pass): a receiver or a locator reaching a name the walk does not follow is refused
        self.assertEqual(escapes, [], "a locator made on a playwright receiver and not consumed by a call in its own chain (stored, returned or passed on) is read "
                                      "under a name the walk does not follow, so its reads never reach the allow-list: %r" % (escapes,))
        leaves = _escaped_receivers(driver)
        self.assertEqual([(ln, what) for ln, what, ok in leaves if not ok], [],
                         "a playwright receiver, or a locator made from one, reaching a name the walk does not follow (bound or assigned to a name outside "
                         "WALKED_NAMES, or passed bare to anything but Object.keys or a driver helper whose one parameter is a walked name); a call on that name "
                         "is invisible to the allow-list: %r" % ([(ln, what) for ln, what, ok in leaves if not ok],))
        self.assertLessEqual({"context = browser", "page = context", "pages[app] = page", "snap(pages[app])"}, {what for _, what, ok in leaves if ok},
                             "the census is not vacuous: the driver's bindings of the context and the page, the page table's assignment and snap's argument "
                             "are seen: %r" % (sorted({what for _, what, ok in leaves if ok}),))
        self.assertEqual(len(re.findall(r"\bfetch\s*\(", driver)), 2, "the driver's two fetches (ctl and tunnelsStatus) carry no timeout: the acknowledged driver_error road, DRIVER_TIMEOUT_S, "
                                                                        "which the arithmetic does not count; a third fetch is a new uncounted wait")

    def test_a_wait_site_is_classified_by_the_receiver_before_its_dot(self):
        """The census's classifier (_wait_sites), by cell: the budget's poll through the alias and through its receiver (`waitFor(`,
        `budget.waitFor(`) is the budget form, whose positional timeout makeBudget caps; a locator's `.waitFor(` (a bare receiver,
        a chain) is the timeout form the census requires capped; a receiver merely ending in budget (`mybudget`, `xbudget`) or
        whose last dotted segment is budget (`obj.budget`, `this.budget`) is a locator's or a member's, never the poll; a
        navigation and a waitFor* keep their names; the alias assignment is no site. Round 4: the round-3 head's lookback
        compared the seven characters before the dot to "budget." and could never match, so `budget.waitFor(` classified as an
        uncapped locator wait (a driver with the alias deleted and every poll written through the receiver redded the census
        with seven false "no timeout key" entries); the six-character compare the findings offered would have taken `mybudget`
        for the poll, which is why the receiver is captured whole; and round 4's first capture took one segment, so
        `obj.budget.waitFor(` read as the poll (the fixer pass), which is why the capture spans every dotted segment."""
        self.assertEqual(_wait_sites('await budget.waitFor(fn, 1, "w");'), [("waitFor", 'fn, 1, "w"', 1)])
        self.assertEqual(_wait_sites('await waitFor(fn, cfg.waitsMs.held, "w");'), [("waitFor", 'fn, cfg.waitsMs.held, "w"', 1)])
        self.assertEqual(_wait_sites('await row.waitFor({ timeout: budget.capped(x) })'), [(".waitFor", "{ timeout: budget.capped(x) }", 1)])
        self.assertEqual(_wait_sites('\nawait pages.feed.locator(s).first().waitFor({ state: "attached", timeout: budget.capped(ms) });'),
                         [(".waitFor", '{ state: "attached", timeout: budget.capped(ms) }', 2)])
        for recv in ("mybudget", "xbudget", "budget2", "the_budget", "$budget", "obj.budget", "this.budget", "a.b.budget"):
            self.assertEqual([n for n, _, _ in _wait_sites('await %s.waitFor(fn, 1, "w")' % recv)], [".waitFor"], "%s is not the budget" % recv)
        self.assertEqual([n for n, _, _ in _wait_sites('await page.goto(u, { timeout: budget.capped(x) }); await page.waitForFunction(f, null, { timeout: budget.capped(x) });')],
                         ["goto", "waitForFunction"])
        self.assertEqual(_wait_sites("const waitFor = budget.waitFor;"), [], "an assignment is no site")

    def test_the_receiver_walk_classifies_a_call_by_the_receiver_it_is_chained_on(self):
        """The allow-list's instrument (_receiver_calls), by cell: a page's locator chain yields the page call and the locator calls
        after it; a bracketed page expression is a page; a member read without a call ends the chain; a locator's textContent,
        innerText, ariaSnapshot and evaluate are locator calls the allow-list refuses while a page's evaluate is allowed (the
        refuter measured a locator's evaluate auto-waiting and a page's returning at once); text that names no receiver yields
        nothing. The failing-before is a driver mutation, not a cell: provText rewritten as a locator's `textContent()`
        passed the round-3 head's census and reds this one by name."""
        self.assertEqual(_receiver_calls('await pages.feed.locator(cardSel(ch, n)).first().waitFor({ state: "attached", timeout: budget.capped(ms) });'),
                         [("page", "locator", 1), ("locator", "first", 1), ("locator", "waitFor", 1)])
        self.assertEqual(_receiver_calls('x = (await pages.waiting.locator(".ut-text", { hasText: ch.todoText }).count()) > 0;'),
                         [("page", "locator", 1), ("locator", "count", 1)])
        self.assertEqual(_receiver_calls('await pages[APPS[0]].waitForTimeout(budget.capped(cfg.quietStepMs));'), [("page", "waitForTimeout", 1)])
        self.assertEqual(_receiver_calls('await pages[app].waitForFunction(() => true, null, { timeout: budget.capped(x) });'), [("page", "waitForFunction", 1)])
        self.assertEqual(_receiver_calls('const u = page.url; const c = await context.newPage();'), [("context", "newPage", 1)])
        self.assertEqual(_receiver_calls('\nconst t = await pages.feed.locator(cfg.provSel).textContent();'), [("page", "locator", 2), ("locator", "textContent", 2)])
        for read in ("textContent", "innerText", "ariaSnapshot", "evaluate"):
            calls = _receiver_calls("await pages.feed.locator(sel).%s();" % read)
            self.assertEqual([(k, n) for k, n, _ in calls if n not in ALLOWED_CALLS.get(k, ())], [("locator", read)], "a locator's %s is refused by the allow-list" % read)
        calls = _receiver_calls("await pages.feed.evaluate((sel) => document.querySelector(sel), cfg.provSel);")
        self.assertEqual([(k, n) for k, n, _ in calls if n not in ALLOWED_CALLS.get(k, ())], [], "a page's evaluate is allowed")
        self.assertEqual(_receiver_calls("const webpage = 1; out.pages[app] = await snap(pages[app]); w.send(d);"), [], "no receiver, no call")

    def test_a_receiver_or_a_locator_that_leaves_the_walk_is_refused(self):
        """The walk's own gap (round 4's fixer pass): the allow-list reads chains on the names it knows, so a receiver or a locator
        reaching any other name was invisible to it and a bound locator's `textContent()` left the census green. By cell: a
        locator bound to a name (refused twice: the binding, and the chain that ended on the maker), a page bound to a name, a
        destructured page table, a locator passed on or returned unconsumed, a page passed bare to a helper whose parameter is
        not a walked name and to a helper the text does not define (all refused); the driver's own shapes (the browser, context
        and page bindings, the page table's assignment, a page passed to snap whose parameter is `page`, Object.keys over the
        table) and chains consumed by a count or tested for truth (all allowed)."""
        def refused(text):
            escapes = []
            _receiver_calls(text, escapes)
            return sorted([what for _, what, ok in _escaped_receivers(text) if not ok] + [what for _, what in escapes])
        self.assertEqual(refused("const row = pages.feed.locator(cfg.provSel); await row.textContent();"), ["locator(...) left its chain unconsumed", "row = pages.feed"])
        self.assertEqual(refused("const fp = pages.feed; await fp.locator(cfg.provSel).textContent();"), ["fp = pages.feed"])
        self.assertEqual(refused("const snap = async (page) => 1; const g = function (page, x) {}; const h = async (a, page) => 1;"), [], "a parameter list declares a name, it passes nothing")
        self.assertEqual(refused("let p2 = page; const { feed } = pages;"), ["p2 = page", "{feed} = pages"])
        self.assertEqual(refused("const p = await context.newPage(); const b = await chromium.launch({}); const u = page.url;"), ["b = chromium", "p = context", "u = page"],
                         "a receiver-making call binds a receiver; a member read without a call is refused on the safe side")
        self.assertEqual(refused("await read(pages.feed.locator(sel)); return pages[app].locator(sel).first();"), ["first(...) left its chain unconsumed", "locator(...) left its chain unconsumed"])
        self.assertEqual(refused("const read = async (p) => p.locator(sel).textContent(); await read(pages.feed);"), ["read(pages.feed)"])
        self.assertEqual(refused("await read(pages[app]); await f(1, page);"), ["<a later argument>(page)", "read(pages[app])"])
        self.assertEqual(refused("let browser; browser = await chromium.launch({}); const context = await browser.newContext({}); const page = await context.newPage(); pages[app] = page;"), [])
        self.assertEqual(refused("const snap = async (page) => page.evaluate(() => 1); const s = await snap(pages[app]); for (const app of Object.keys(pages)) {}"), [])
        self.assertEqual(refused("const c = await pages.feed.locator(sel).count(); if (pages.fleet && x) y = 1; x = (await pages.waiting.locator(s).count()) > 0;"), [])
        allowed = {what for _, what, ok in _escaped_receivers("const context = await browser.newContext({}); const page = await context.newPage(); pages[app] = page; const snap = async (page) => 1; await snap(pages[app]);") if ok}
        self.assertEqual(allowed, {"context = browser", "page = context", "pages[app] = page", "snap(pages[app])"}, "the allowed shapes are reported as allowed, so the driver's non-vacuity check reads them")

    def test_the_new_bundle_class_gates_on_no_knob_and_the_old_hub_class_skips_as_optional(self):
        """Round 1's high (this lab was the one served lab of 94 with no executing test in CI: its base class gated on a knob)
        was closed by a value, _LinkDrop._knobs returning None. The property, pinned (round 2, extra6-1; round 3 widened it
        from the one call site to every site a gate could sit at, since the same optional gate re-planted as a class
        decorator or in setUpClass re-created the high with the pin green): with the four knobs unset, LinkDropBothNew
        carries no class-level skip (what unittest.skip* sets, __unittest_skip__), its _knobs returns, and its setUpClass runs
        to the boot (with _boot stubbed) without a SkipTest; LinkDropOldLocal's _knobs raises a SkipTest whose reason starts
        with "optional:" and names its knob. The new class's calls are wrapped so a regression fails the pin instead of
        skipping it; throwaway subclasses, so nothing _knobs or setUpClass assigns reaches the real classes. And the served
        step runs with -rs, so an optional skip prints its reason in CI's log rather than folding into a count."""
        class New(L.LinkDropBothNew):
            pass

        class Old(L.LinkDropOldLocal):
            pass
        self.assertFalse(getattr(New, "__unittest_skip__", False),
                         "LinkDropBothNew carries a class-level skip (unittest.skip*), so the lab would collect in CI's served job with no executing test: %r"
                         % (getattr(New, "__unittest_skip_why__", ""),))
        with _without_knobs():
            try:
                New._knobs()
            except unittest.SkipTest as e:
                self.fail("LinkDropBothNew._knobs raised SkipTest with the four knobs unset, so the lab would collect in CI's served job with no executing test: %s" % e)
            try:
                with mock.patch.object(New, "_boot", classmethod(lambda cls: None)):
                    New.setUpClass()
            except unittest.SkipTest as e:
                self.fail("LinkDropBothNew.setUpClass raised SkipTest before its boot with the four knobs unset (a gate outside _knobs), so the lab would "
                          "collect in CI's served job with no executing test: %s" % e)
            with self.assertRaises(unittest.SkipTest) as cm:
                Old._knobs()
        reason = str(cm.exception)
        self.assertTrue(reason.startswith("optional:"), "the old-hub class's skip is optional (the CI census reads the prefix): %r" % (reason,))
        self.assertIn("ROMP_LINKDROP_LAB", reason, "…and names the knob that runs it")
        self.assertIn(" -rs ", self._served_step_line(), "CI's served step prints skip reasons (-rs), so the optional skip is visible there")

    def _boot_stub(self, base, **attrs):
        """A class over a scratch lab that _boot runs to its build statement without node deps or a browser: L.EXT repointed
        at a scratch with a playwright package directory, the node probe answered by the spy with a path that exists, every
        other subprocess a failure of the test (the kernels are never reached), the remote's routes read from this checkout's
        kernel. Returns the class; the caller cleans its lab."""
        scratch = tempfile.mkdtemp(prefix="linkdrop-boot-")
        self.addCleanup(shutil.rmtree, scratch, True)
        os.makedirs(os.path.join(scratch, "node_modules", "playwright"))
        self.addCleanup(setattr, L, "EXT", L.EXT)
        L.EXT = scratch

        class Boot(base):
            pass
        Boot.procs, Boot.proxy, Boot.ctl = [], None, None
        for k, v in attrs.items():
            setattr(Boot, k, v)
        test = self

        def probe_only(cmd, *a, **kw):
            if cmd[:2] == ["node", "-e"]:
                return subprocess.CompletedProcess(cmd, 0, stdout=scratch + "\n", stderr="")
            test.fail("_boot ran a subprocess past the build statement: %r" % (cmd,))
        p = mock.patch.object(L.subprocess, "run", probe_only)
        p.start()
        self.addCleanup(p.stop)
        return Boot

    def _boot_expecting_error(self, Boot):
        """_boot's outcome as one of three: a RuntimeError (returned), a SkipTest (a failure of the pin, never a skip), a return."""
        try:
            Boot._boot()
        except RuntimeError as e:
            return e
        except unittest.SkipTest as e:
            self.fail("a build the runner asked for skipped instead of erring (the class would skip and the run report green): %s" % e)
        finally:
            shutil.rmtree(getattr(Boot, "lab", "") or "", ignore_errors=True)
        self.fail("_boot returned without building")

    def test_a_hub_a_knob_asked_for_errs_when_its_bundle_cannot_be_made_ready_and_this_checkouts_stays_a_skip(self):
        """Round 1's tests-3, through _boot with a stub build: the mint knob with a build that skips (lab_dist's esbuild
        failure) is a RuntimeError carrying the knob and the build's words; a knob-named root with no prebuilt dist is the
        same, under the old-hub class's own knob and under the base-hub lever; a knob-named root with no kernel file at all (a
        mistyped root) is the same through the kernel check one statement earlier (round 3: it skipped, whatever the knob
        said); and with no knob this checkout's own bundle failing to build stays a SkipTest, as in every other served lab."""
        words = "esbuild failed here: the stub build"

        class StubBuild:
            def __init__(self, ext, root):
                self.ext, self.root = ext, root

            def copy_to(self, dest):
                raise unittest.SkipTest(words)
        # the mint knob: a mint that succeeds (stubbed: the checkout's kernel and extension directory appear) and a build that skips
        def mint(cls):
            wt = os.path.join(cls.lab, "oldhub")
            os.makedirs(os.path.dirname(os.path.join(wt, L.KERNEL_BIN)))   # the kernel entry point _boot requires, by the module's own name for it
            os.makedirs(os.path.join(wt, "vscode-extension"))
            with open(os.path.join(wt, L.KERNEL_BIN), "w") as f:
                f.write("#!/bin/sh\n")
            cls.old_hub_wt = wt
            return wt
        with _without_knobs(), mock.patch.dict(os.environ, {"ROMP_LINKDROP_LAB": "1", "ROMP_LINKDROP_OLD_HUB_BUILD": "1"}), mock.patch.object(L.lab_dist, "DistBuild", StubBuild):
            Boot = self._boot_stub(L.LinkDropOldLocal, _mint_old_hub=classmethod(mint))
            e = self._boot_expecting_error(Boot)
        self.assertIn("ROMP_LINKDROP_OLD_HUB_BUILD=1", str(e), "the error names the knob that asked: %s" % e)
        self.assertIn(words, str(e), "…and carries the build's words: %s" % e)
        self.assertTrue(Boot.old_hub_wt and Boot.old_hub_wt in str(e), "…and the minted checkout: %s" % e)
        # a knob-named root with a kernel and no prebuilt dist, under the old-hub class's knob and under the base-hub lever
        for base, knob, env in ((L.LinkDropOldLocal, "ROMP_CORNER_OLD_HUB_ROOT", {"ROMP_LINKDROP_LAB": "1"}), (L.LinkDropBothNew, "ROMP_LINKDROP_HUB_ROOT", {})):
            root = tempfile.mkdtemp(prefix="linkdrop-hubroot-")
            self.addCleanup(shutil.rmtree, root, True)
            os.makedirs(os.path.dirname(os.path.join(root, L.KERNEL_BIN)))
            with open(os.path.join(root, L.KERNEL_BIN), "w") as f:
                f.write("#!/bin/sh\n")
            with _without_knobs(), mock.patch.dict(os.environ, dict(env, **{knob: root})):
                Boot = self._boot_stub(base)
                e = self._boot_expecting_error(Boot)
            self.assertEqual(Boot.hub_knob, knob, "the knob that named the hub is recorded")
            self.assertIn(knob, str(e), "the error names the knob that asked: %s" % e)
            self.assertIn("no prebuilt dist under %s" % root, str(e), "…and says what was missing: %s" % e)
        # a knob-named root with NO kernel file (a mistyped root), under both knobs: the kernel check follows the same rule
        for base, knob, env in ((L.LinkDropOldLocal, "ROMP_CORNER_OLD_HUB_ROOT", {"ROMP_LINKDROP_LAB": "1"}), (L.LinkDropBothNew, "ROMP_LINKDROP_HUB_ROOT", {})):
            root = tempfile.mkdtemp(prefix="linkdrop-hubroot-empty-")
            self.addCleanup(shutil.rmtree, root, True)
            with _without_knobs(), mock.patch.dict(os.environ, dict(env, **{knob: root})):
                Boot = self._boot_stub(base)
                e = self._boot_expecting_error(Boot)
            self.assertIn(knob, str(e), "the error names the knob that asked: %s" % e)
            self.assertIn("no %s" % L.KERNEL_BIN, str(e), "…and the kernel file the root lacks: %s" % e)
            self.assertIn(root, str(e), "…and the root: %s" % e)
        # no knob: this checkout's own bundle, whose failed build stays a skip
        def skip_dist(dest):
            raise unittest.SkipTest(words)
        with _without_knobs(), mock.patch.object(L.lab_dist, "copy_dist", skip_dist):
            Boot = self._boot_stub(L.LinkDropBothNew)
            try:
                with self.assertRaises(unittest.SkipTest) as cm:
                    Boot._boot()
            finally:
                shutil.rmtree(getattr(Boot, "lab", "") or "", ignore_errors=True)
        self.assertEqual(str(cm.exception), words, "the unknobbed arm's skip is lab_dist's own, unwrapped")
        self.assertIsNone(Boot.hub_knob)

    def test_an_empty_phase_is_excused_only_by_a_whole_frame_after_the_bundles_last_notice(self):
        """The old-hub storm's allowance (_outline_caught_up_whole, both floors) excuses a phase with no patch and no row only
        when one of the bundle's notice posts happened while the Outline held no open relay socket that had already received
        its first feed-family frame (the gap that could have swallowed a notice), and then only for a whole keyed feed frame
        the Outline received after the earliest the bundle's LAST notice could have been posted (the change record's t0 plus
        the gaps between the notices) and before the window's padded end. Round 3 found the key was the window: a frame at
        A0 + 5 ms or between notice 1 and notice 2 excused a stripped phase, though it could not have carried the notices
        posted after it. Round 4 found the frame alone was no key either: on the old bundle a routine redial produces a whole
        frame after the notices were already delivered as patches, so the excuse was available in 47 of the 75 recorded phase
        windows and a planted miss stayed green, and the cells below could not tell the keys apart, since a synthetic socket
        with no openAt reads as never open and the gap held in every cell. Over a synthetic record, by cell: with the socket
        recording no open, a frame before the window, before the first post, between the notices, one millisecond before the
        last notice's earliest post (all no excuse), at it, after the bundle, at the right pad's edge (all an excuse), past
        the pad and unkeyed (no excuse); a frame on the feed page's socket counts for nothing; a phase with no change record
        fails rather than widening. Then the socket's state at the posts: open and served across all three posts with a
        later frame in the window (no excuse: the 42 recorded windows the frame alone excused with their patches delivered),
        the same socket closing after the last post with the redial's frame (no excuse), closed before the posts (an excuse:
        the tightening kept the recorded churn's excuse), closing between notice 1 and notice 2 (an excuse), open across the
        posts but served only after notice 2 (an excuse). And the floor the excuse guards, with the excuse frame PRESENT in
        the record: a phase with no patch and no row whose socket was open and served across the posts reds
        _assert_one_row_per_outline_feed_patch (the planted miss), the same with the socket closed across the posts passes
        (the churn), and a patch with its row passes (the storm)."""
        A0 = 1_000_000
        made = {"phase": "A", "t0": A0 / 1000.0 + 0.010, "t1": A0 / 1000.0 + 2.015, "noticeKeys": ["k1", "k2", "k3"], "noticeRevs": [1, 2, 3], "notices": []}
        last_post = (made["t0"] + (L.NOTICES_PER_PHASE - 1) * L.NOTICE_GAP_S) * 1000   # the earliest the last notice's post could start
        A1 = int(made["t1"] * 1000) + L.PHASE_SETTLE_MS
        self.assertGreater(last_post, A0 + 1000, "the cells straddle the key: the last notice comes after the between-notices cell")
        self.assertLess(last_post, A1, "…and before the phase's end")

        def frame(at, asks=11):
            return {"t": "feed", "slot": "", "len": 1, "at": at, "asks": asks, "buildId": None}
        cells = [(A0 - 500, 11, False, "before the window (the ready-time frame)"),
                 (A0 + 5, 11, False, "inside the window, before the bundle's first post"),
                 (A0 + 1000, 11, False, "after notice 1, before notices 2 and 3"),
                 (int(last_post) - 1, 11, False, "one millisecond before the last notice's earliest post"),
                 (int(last_post) + 1, 11, True, "just after the last notice's earliest post"),
                 (A0 + 3000, 11, True, "after the bundle (the recorded churn frames came 2.8 to 2.9 s in)"),
                 (A1 + 1500, 11, True, "at the right pad's edge"),
                 (A1 + 1501, 11, False, "past the right pad"),
                 (A0 + 3000, None, False, "unkeyed (no asks list)")]

        class Rec(L.LinkDropOldLocal):
            driver_error = None

        def record(outline_frames, feed_frames=(), socks=None, rows=()):
            outline = list(socks) if socks is not None else [{"relay": True, "frames": list(outline_frames)}]   # no openAt: never open
            Rec.result = {"marks": {"A0": A0, "A1": A1, "end": A1 + 1}, "died": None,
                          "pages": {"fleet": {"socks": outline}, "feed": {"socks": [{"relay": True, "frames": list(feed_frames)}]}}}
            Rec.changes_made = [dict(made)]
            Rec.hub_diag_rows = list(rows)
            return Rec("test_nothing_was_asked_of_the_remote")   # an instance for the helper; the test method is never run
        for at, asks, want, why in cells:
            got = record([frame(at, asks)])._outline_caught_up_whole("A0", "A1")
            self.assertEqual(bool(got), want, "a whole frame %s (at A0 %+d ms; the last notice's earliest post at A0 %+d ms) %s excuse an empty phase A: %r"
                             % (why, at - A0, int(last_post) - A0, "should" if want else "must not", got))
        self.assertEqual(record([], [frame(A0 + 3000)])._outline_caught_up_whole("A0", "A1"), [], "a frame on the feed page's socket is not the Outline's")
        t = record([frame(A0 + 3000)])
        Rec.changes_made = []
        with self.assertRaises(AssertionError):
            t._outline_caught_up_whole("A0", "A1")
        # the socket's state at the three posts (A0 + 10, + 1010, + 2010 ms): the gap the excuse is keyed on
        posts = [int((made["t0"] + i * L.NOTICE_GAP_S) * 1000) for i in range(L.NOTICES_PER_PHASE)]
        self.assertEqual(posts, [A0 + 10, A0 + 1010, A0 + 2010], "the derived post times the cells are placed against")

        def sock(i, open_at, close_at, frames):
            return {"i": i, "relay": True, "dialedAt": open_at - 100, "openAt": open_at, "closeAt": close_at, "frames": list(frames)}
        held = sock(0, A0 - 5000, None, [frame(A0 - 4000)])                       # open and served since before the window
        redial = sock(1, A0 + 2500, None, [frame(A0 + 3000)])                      # the retry's socket, its whole frame after the last post
        state_cells = [([sock(0, A0 - 5000, None, [frame(A0 - 4000), frame(A0 + 3000)])], False,
                        "open and served across all three posts, with a later whole frame in the window (the redial after the notices were delivered)"),
                       ([sock(0, A0 - 5000, A0 + 2500, [frame(A0 - 4000)]), sock(1, A0 + 2900, None, [frame(A0 + 3000)])], False,
                        "open and served across all three posts, closing after the last post, the redial's frame in the window"),
                       ([sock(0, A0 - 5000, A0 - 100, [frame(A0 - 4000)]), redial], True,
                        "closed before the first post (every post found no open socket), the redial's frame after the last post"),
                       ([sock(0, A0 - 5000, A0 + 500, [frame(A0 - 4000)]), redial], True,
                        "closing between notice 1 and notice 2 (posts 2 and 3 found no open socket)"),
                       ([sock(0, A0 - 5000, None, [frame(A0 + 1500), frame(A0 + 3000)])], True,
                        "open across the posts but served its first frame only after notice 2 (posts 1 and 2 found it unserved)")]
        for socks, want, why in state_cells:
            with self.subTest(socket=why):
                got = record([], socks=socks)._outline_caught_up_whole("A0", "A1")
                self.assertEqual(bool(got), want, "the Outline's socket %s: a whole frame after the last post %s excuse an empty phase A: %r"
                                 % (why, "should" if want else "must not", got))
        # the floor the excuse guards, with the excuse frame present in the record (a whole keyed frame at A0 + 3 s, after the
        # last post, inside the window): the planted miss reds it, the churn passes it, the storm passes it
        with self.assertRaises(AssertionError) as cm:
            record([], socks=[sock(0, A0 - 5000, None, [frame(A0 - 4000), frame(A0 + 3000)])])._assert_one_row_per_outline_feed_patch("A0", "A1", patches_due=True)
        self.assertIn("neither happened", str(cm.exception), "a phase with no patch and no row whose socket was open and served across the posts is a change that "
                                                              "reached the Outline as nothing; the later whole frame excuses nothing: %s" % cm.exception)
        self.assertEqual(record([], socks=[held.copy() | {"closeAt": A0 - 100}, redial])._assert_one_row_per_outline_feed_patch("A0", "A1", patches_due=True), 0,
                         "the churn: no patch and no row, the socket closed across the posts, the redial's whole frame after the last post")
        patch = {"t": "delta", "slot": "feed", "at": A0 + 1200, "coll": ["asks"], "rev": 1, "len": 300, "restAll": False}
        row = {"surface": "outline", "what": "delta-unapplied", "t": (A0 + 1200) // 1000, "wid": "w1", "reconnect": False, "data": {"rev": 1, "slot": "feed"}}
        self.assertEqual(record([], socks=[sock(0, A0 - 5000, None, [frame(A0 - 4000), patch, frame(A0 + 3000)])], rows=[row])._assert_one_row_per_outline_feed_patch("A0", "A1", patches_due=True), 1,
                         "the storm: one patch, its row, the socket open and served throughout")

    def test_the_down_windows_attach_exemption_takes_one_feed_row_per_attach_stamped_at_or_after_it(self):
        """The down window's exemption for the connect push's ledgers attach (round 2's regression-3 fix: a card-less feed slot
        patch at or after the resume, and the row the old bundle files for it, are the return's, not the down window's) landed
        keyed on the row's REV as a set over the drive's attaches, with no test, and the Outline's feed patch revs restart at 1
        on every relay socket, so the gate leg's exact zero was weaker than its message (round 4: the row is matched to the
        attach, at most one row per attach, naming the feed slot, stamped at or after the attach's floored second with a
        second of slack for the kernel's clock against the browser's). Over a synthetic record (one Outline relay socket
        opened after the resume, one card-less feed slot patch 50 ms after it, rows at chosen stamps), the storm test's
        down-window call returns 0 for the attach's row floored a second below the attach, at its floored second and a second
        above it; a second row of the attach's rev, also stamped at or after it, is the down window's and reds (the round-3
        head's set exempted both); a row of the attach's rev stamped two seconds below is not the attach's and reds (the set
        exempted it); a row of the attach's rev naming another slot is not the attach's and reds (the set exempted it before
        the slot check ran); a second row with no attach behind it reds (narrowness: a widened exemption passes the first
        cell alone); the same patch carrying cards is no attach and its row reds (a control on the card conditioning, red at
        both trees, so not a discriminator of the match). The gate leg
        reads attaches from 1.5 s before the resume and the storm test from the resume: an attach 1 s before the resume is in
        the first set and not the second, through the helpers at both since values and through the gate leg's own read
        (_rows_down_minus_attaches, which carries its since; round 4's fixer pass: the leg's inline since was reached by no
        test, and a mutation moving it to the resume stayed green). And the return window's read (_return_window_stray, the
        third reader of the attaches, which kept a set of revs until the fixer pass): one row of an attach's rev in the window
        is the attach's, a second row of the same rev is stray (the set passed both), a row of a rev no attach carries is
        stray, and a row of the attach's rev two seconds before its floored second is stray. Nothing here reaches the test
        methods' own lines; the replays over recorded drives do (0 rows and 0 attaches in every recorded down window and
        return window, so neither exemption fires on any recorded drive: the census is in the served module's
        _minus_attach_rows docstring)."""
        DROP, RESUME = 1_000_000, 1_030_000
        B0, END = RESUME + 20_000, RESUME + 60_000

        class Rec(L.LinkDropOldLocal):
            driver_error = None

        def row(rev, t_ms, slot="feed"):
            return {"surface": "outline", "what": "delta-unapplied", "t": t_ms // 1000, "wid": "w1", "reconnect": False, "data": {"rev": rev, "slot": slot}}

        def patch(at, coll, rev=7):
            return {"t": "delta", "slot": "feed", "at": at, "coll": list(coll), "rev": rev, "len": 300, "restAll": False}

        def record(rows, frames):
            Rec.result = {"marks": {"drop": DROP, "resume": RESUME, "B0": B0, "end": END}, "died": None, "timeouts": [],
                          "pages": {"fleet": {"socks": [{"i": 1, "relay": True, "dialedAt": RESUME + 10, "openAt": RESUME + 20, "closeAt": None, "url": "", "frames": list(frames)}], "sends": []}}}
            Rec.changes_made = []
            Rec.hub_diag_rows = list(rows)
            return Rec("test_nothing_was_asked_of_the_remote")   # an instance for the helpers; the test method is never run

        def down(rows, frames):
            return record(rows, frames)._assert_one_row_per_outline_feed_patch("drop", "resume", patches_due=False, attach_after="resume")
        attach = patch(RESUME + 50, ["ledgers"])   # the connect push's ledgers attach: card-less, 50 ms after the resume, floored second RESUME // 1000
        floor = (RESUME + 50) // 1000
        for t_ms, why in ((RESUME - 900, "floored a second below the attach (the kernel's clock behind the browser's)"),
                          (RESUME + 50, "at the attach's floored second"), (RESUME + 1050, "a second above it")):
            with self.subTest(row=why):
                self.assertEqual(down([row(7, t_ms)], [attach]), 0, "the attach's row %s (t %d against the attach's floored second %d) is the return's, not the down window's" % (why, t_ms // 1000, floor))
        with self.subTest(rows="two rows of the attach's rev, both stamped at or after it"):
            with self.assertRaises(AssertionError, msg="a second row of the attach's rev is the down window's (one row per attach; the set of revs exempted both)") as cm:
                down([row(7, RESUME - 900), row(7, RESUME + 1050)], [attach])
            self.assertIn("one outline/delta-unapplied row per feed slot patch", str(cm.exception), cm.exception)
        with self.subTest(rows="a row of the attach's rev two seconds below its floored second"):
            with self.assertRaises(AssertionError, msg="a row of the attach's rev two seconds below its floored second is not the attach's (the slack is one second)"):
                down([row(7, RESUME - 2000)], [attach])
        with self.subTest(rows="a row of the attach's rev naming another slot"):
            with self.assertRaises(AssertionError, msg="a row of the attach's rev naming another slot is not the attach's (the set exempted it before the slot check)"):
                down([row(7, RESUME - 900, slot="ledgers")], [attach])
        with self.assertRaises(AssertionError, msg="a second row with no attach behind it reds (narrowness)"):
            down([row(7, RESUME - 900), row(99, RESUME - 900)], [attach])
        with self.assertRaises(AssertionError, msg="the same patch carrying cards is no attach (a control on the card conditioning, red at both trees)"):
            down([row(7, RESUME - 900)], [patch(RESUME + 50, ["asks"])])
        # the gate leg's separate copy reads attaches from resume - 1500 ms, the storm test's from resume
        early = patch(RESUME - 1000, ["ledgers"], rev=5)
        t = record([row(5, RESUME - 1000)], [early])
        stamped = t._outline_unapplied_stamped(t._rows_in("drop", "resume"))
        self.assertEqual((t._attaches_since(RESUME - 1500), t._attaches_since(RESUME)), ([(5, (RESUME - 1000) // 1000)], []),
                         "an attach 1 s before the resume is in the gate leg's set of attaches and not the storm test's")
        self.assertEqual((t._minus_attach_rows(stamped, RESUME - 1500), t._minus_attach_rows(stamped, RESUME)), ([], [{"rev": 5, "slot": "feed"}]),
                         "…so the gate leg's since exempts its row and the storm test's does not")
        self.assertEqual(t._rows_down_minus_attaches(), [], "…and the gate leg's own read, which carries its since of 1.5 s before the resume, exempts the row (at the resume it would not)")
        # the return window's read (the third reader of the attaches): one row per attach the Outline received there, matched to it
        late = patch(RESUME + 1540, ["ledgers"], rev=1)   # the connect push's ledgers attach 1.54 s after the resume, past the down window's patch pad
        f = (RESUME + 1540) // 1000   # the attach's floored second; row() takes milliseconds and floors them the same way
        self.assertEqual(record([row(1, f * 1000)], [late])._return_window_stray(), ([], [(1, f)]), "one row of the attach's rev at its floored second is the attach's, not stray")
        self.assertEqual(record([row(1, f * 1000), row(1, (f + 1) * 1000)], [late])._return_window_stray()[0], [{"rev": 1, "slot": "feed"}], "a second row of the attach's rev is stray (the set of revs passed both)")
        self.assertEqual(record([row(1, f * 1000), row(2, (f + 2) * 1000)], [late])._return_window_stray()[0], [{"rev": 2, "slot": "feed"}], "a row of a rev no attach carries is stray")
        self.assertEqual(record([row(1, (f - 2) * 1000)], [late])._return_window_stray()[0], [{"rev": 1, "slot": "feed"}], "a row of the attach's rev two seconds before its floored second is not the attach's")

    def test_the_margin_leg_takes_no_expired_or_unshown_wait_as_a_delivery(self):
        """The gate's control in time (_assert_the_down_window_outlasts_the_drives_slowest_delivery) reads a phase's
        seen.waitedMs as this drive's delivery. Round 5 found that a waitVisible wait that TIMED OUT left waitedMs at about
        wait_ms with no other trace (the driver swallowed the TimeoutError; out.timeouts held only budget.waitFor's
        expiries), so the yardstick became the cap and the leg passed at 42 >= 2 x 20.0x by the relation pin's arithmetic
        with the true delivery unknown; on the old-hub class phase A's visibles were asserted nowhere, so an old-hub drive
        whose phase-A churn came past 20 s was green. Over a synthetic record for each class with a 42.005 s down window
        (the recorded span): every wait resolved and the slowest delivery 19,900 ms passes and is measured; then in each
        link-up phase in turn, a wait that expired with the visibles absent (waitedMs 20,012), the same with the visibles
        present (the card attached inside the read gap: an honest 20.0x s, refused all the same, since the leg keys on the
        wait's outcome and not on a read that happened to catch it), an older driver's record with no expired list and the
        visibles shown (the outcome cannot be established, so the read alone does not make it a delivery) and a resolved
        wait whose read found nothing (the belt: the DOM changed between the wait and the read) each fail naming the phase and in
        the words of the check that refused it (the expired check's own clause, not a token the record's repr carries: the seen
        record embeds 'expired' as a key, so that word alone would let a visibles failure pass for an expired one); a resolved wait
        at 20,012 ms with the visibles present passes, since a resolved wait ended by its cap and the excess is the reads
        (DOWN_READ_ROOM_MS). Then the inequality itself, which every cell above exercises the guards of and none the bound (round
        4: the bound deleted, the margin lowered to 0.001, and that with the dwell reverted to round 2's 12 s left every
        kernel-free test green): with every wait resolved and shown and the slowest delivery 19,900 ms, a window one millisecond
        under DOWN_WINDOW_MARGIN times it reds in the inequality's own words. Two halves pin the margin and both are needed: this
        cell is derived from the constant, so it moves with it and catches a deleted or inverted bound but not a lowered constant,
        and the floor on DOWN_WINDOW_MARGIN in test_the_arithmetic_and_the_cap_it_is_chosen_against catches the lowered constant but
        not a deleted bound. No passing sibling at the bound itself: int() truncation of the product would make such a cell red for
        arithmetic reasons rather than for the property."""
        span_ms = 42005                     # settled less phase D's t1: 42.004 to 42.010 s over the recorded head drives
        d_t1 = 2_000_000.0                  # phase D's post end, in the control door's seconds
        settled = int(d_t1 * 1000) + span_ms
        for cls in (L.LinkDropBothNew, L.LinkDropOldLocal):
            self.assertTrue(cls.local_drop, "both classes drive the local drop, so A, B and C are the phases the yardstick reads")

            class Rec(cls):
                driver_error = None

            def change(p):
                return {"phase": p, "prompt": "synthetic prompt %s" % p, "noticeKeys": ["k1", "k2", "k3"], "noticeRevs": [1, 2, 3]}

            def seen(waited, p, shown=True, expired=(), key=True):
                v = {"cards": [shown] * 3, "waitedMs": waited}
                if "todo" in cls.changes:
                    v["todo"] = shown
                if "append" in cls.changes:
                    v["prov"] = change(p)["prompt"] if shown else "the row before the change"
                if key:
                    v["expired"] = list(expired)
                return v

            def record(settled=settled, **over):
                Rec.result = {"marks": {"settled": settled, "resume": settled + 20, "end": settled + 60000}, "died": None, "timeouts": [],
                              "phases": {p: {"change": change(p), "seen": over.get(p) or seen(1000 * (i + 1), p)} for i, p in enumerate("ABC")}}
                Rec.changes_made = [change(p) for p in "ABC"] + [{"phase": "D", "t0": d_t1 - 2.0, "t1": d_t1, "noticeKeys": ["k1", "k2", "k3"]}]
                return Rec("test_every_wait_the_driver_placed_was_met")   # an instance for the helper; the test method is never run
            span_s, deliveries = record(C=seen(19900, "C"))._assert_the_down_window_outlasts_the_drives_slowest_delivery()
            self.assertAlmostEqual(span_s, span_ms / 1000.0, places=3, msg="%s: the leg read the window from phase D's post end to settled" % cls.__name__)
            self.assertEqual(deliveries, {"A": 1000, "B": 2000, "C": 19900}, "%s: every wait resolved and shown, so every phase's waitedMs is a delivery and the slowest is C's" % cls.__name__)
            for X in "ABC":
                cells = [("a wait that expired with the visibles absent", seen(20012, X, shown=False, expired=["card"]), "resolved before their cap"),
                         ("a wait that expired though the read caught the card", seen(20012, X, shown=True, expired=["card"]), "resolved before their cap"),
                         ("an older driver's record with no expired list, visibles shown", seen(20012, X, shown=True, key=False), "resolved before their cap"),
                         ("a resolved wait whose read found nothing", seen(20012, X, shown=False, expired=[]), "phase %s's changes" % X)]
                for why, v, token in cells:
                    with self.assertRaises(AssertionError, msg="%s: %s in phase %s must fail the margin leg instead of measuring the cap" % (cls.__name__, why, X)) as cm:
                        record(**{X: v})._assert_the_down_window_outlasts_the_drives_slowest_delivery()
                    self.assertIn("phase %s" % X, str(cm.exception), "%s: %s: the failure names the phase: %s" % (cls.__name__, why, cm.exception))
                    self.assertIn(token, str(cm.exception), "%s: %s: the failure says why: %s" % (cls.__name__, why, cm.exception))
                span_s, deliveries = record(**{X: seen(20012, X, shown=True, expired=[])})._assert_the_down_window_outlasts_the_drives_slowest_delivery()
                self.assertEqual(deliveries[X], 20012, "%s: a resolved wait at the cap's edge with the visibles shown is a delivery in phase %s (the reads after the wait)" % (cls.__name__, X))
            # the bound: every wait resolved and shown, the slowest delivery 19,900 ms, the window one millisecond under the margin times it
            under = int(d_t1 * 1000) + int(L.DOWN_WINDOW_MARGIN * 19900) - 1
            with self.assertRaises(AssertionError, msg="%s: a window under DOWN_WINDOW_MARGIN times the slowest delivery must fail the inequality" % cls.__name__) as cm:
                record(settled=under, C=seen(19900, "C"))._assert_the_down_window_outlasts_the_drives_slowest_delivery()
            self.assertIn("widen down_dwell_ms, never the margin", str(cm.exception), "%s: the inequality's own words: %s" % (cls.__name__, cm.exception))
            self.assertIn("phase C", str(cm.exception), "%s: the failure names the slowest phase: %s" % (cls.__name__, cm.exception))

    def test_a_waited_read_requires_an_empty_expired_list_and_an_unwaited_read_none(self):
        """_assert_seen's `waited` (round 4, tests-1): a record waitVisible produced (a phase's seen, D's seenAfterReturn) must carry
        an empty expired list, so a wait that expired with the read catching the cards, or an older driver's record with no list,
        reds in the expired check's own words; a visible() record carries no list and is read without one. The gate leg's D read
        after the return is the waited read that had no reader (the record replay of that event is the round's failing-before)."""
        class Rec(L.LinkDropOldLocal):
            driver_error = None
        t = Rec("test_nothing_was_asked_of_the_remote")
        shown = {"cards": [True, True, True], "waitedMs": 20012}
        t._assert_seen(dict(shown, expired=[]), True, what="a resolved wait", waited=True)
        t._assert_seen(dict(shown), True, what="an unwaited read")
        for why, rec in (("a wait that expired though the read caught the cards", dict(shown, expired=["card"])), ("an older driver's record with no expired list", dict(shown))):
            with self.assertRaises(AssertionError, msg=why) as cm:
                t._assert_seen(rec, True, what="phase D after the link's return", waited=True)
            self.assertIn("resolved before their cap", str(cm.exception), "%s: the failure says why: %s" % (why, cm.exception))
            self.assertIn("phase D after the link's return", str(cm.exception), "%s: the failure names the read: %s" % (why, cm.exception))

    def test_drive_sends_the_timeout_the_budget_and_the_caps(self):
        lab = tempfile.mkdtemp(prefix="linkdrop-bound-")
        self.addCleanup(shutil.rmtree, lab, True)

        class Drive(L._LinkDrop):
            # values of the stub's own, so the cfg is read from the class that drives and not from the base's defaults
            driver_budget_ms = 123456
            page_wait_ms = 7777
            waits_ms = {k: v + 1000 for k, v in L._LinkDrop.waits_ms.items()}
        Drive.lab, Drive.hport, Drive.htoken, Drive.ctl = lab, 1, "testtok-bound", types.SimpleNamespace(port=2)
        Drive.result, Drive.driver_error = None, None
        seen = {}

        def spy(cmd, *a, **kw):
            seen["cmd"], seen["kw"] = list(cmd), kw
            return subprocess.CompletedProcess(cmd, 0, stdout='RESULT:{"marks": {}}\n', stderr="")
        with mock.patch.object(L.subprocess, "run", spy):
            Drive._drive()
        self.assertEqual(seen["cmd"][:1], ["node"], seen)
        self.assertEqual(seen["kw"].get("timeout"), L.DRIVER_TIMEOUT_S, "the driver's subprocess timeout is DRIVER_TIMEOUT_S")
        self.assertEqual(Drive.result, {"marks": {}}, "the spy's result was read")
        with open(os.path.join(lab, "cfg.json"), encoding="utf-8") as f:
            cfg = json.load(f)
        self.assertEqual(cfg["driverBudgetMs"], Drive.driver_budget_ms)
        self.assertEqual(cfg["waitsMs"], Drive.waits_ms)
        self.assertEqual(cfg["pageWaitMs"], Drive.page_wait_ms)
        self.assertEqual((cfg["phaseSettleMs"], cfg["quietTries"], cfg["quietStepMs"]), (L.PHASE_SETTLE_MS, L.QUIET_TRIES, L.QUIET_STEP_MS))
        with open(seen["cmd"][1], encoding="utf-8") as f:
            driver = f.read()
        self.assertTrue(driver.startswith(L.BUDGET_JS), "the driver the class writes opens with BUDGET_JS")
        unread = [k for k in CFG_KEYS if "cfg.%s" % k not in driver] + ["waitsMs.%s" % k for k in Drive.waits_ms if "cfg.waitsMs.%s" % k not in driver]
        self.assertEqual(unread, [], "every value the cfg carries is read by the driver by name: %r" % (unread,))
        self.assertEqual(set(Drive.waits_ms), set(re.findall(r"cfg\.waitsMs\.(\w+)", driver)), "…and the driver reads no cap the class does not send")

    def test_the_budget_binds_every_wait_under_node(self):
        if not shutil.which("node"):
            raise unittest.SkipTest("node absent: the budget's node run needs it")
        d = tempfile.mkdtemp(prefix="linkdrop-budget-")
        self.addCleanup(shutil.rmtree, d, True)
        path = os.path.join(d, "budget.mjs")
        with open(path, "w", encoding="utf-8") as f:
            f.write(L.BUDGET_JS + BUDGET_HARNESS)
        p = subprocess.run(["node", path], capture_output=True, text=True, timeout=60)
        self.assertEqual(p.returncode, 0, "the budget ran under node: %s%s" % (p.stdout[-800:], p.stderr[-800:]))
        line = next((ln for ln in p.stdout.splitlines() if ln.startswith("RESULT:")), None)
        self.assertIsNotNone(line, p.stdout)
        res = json.loads(line[len("RESULT:"):])
        spent = " (the driver's wait budget was spent)"
        self.assertEqual((res["capBig"], res["capSmall"]), (1000, 300), "the budget caps a larger timeout and leaves a smaller one: %r" % (res,))
        self.assertEqual((res["r1"], res["clock1"], res["polls1"], res["left1"]), (False, 1000, 4, 0),
                         "a wait that never comes polls every 250 ms, spends the budget once and no more: %r" % (res,))
        self.assertEqual(res["timeouts1"], ["w1" + spent], "…and is recorded as expired with the budget spent: %r" % (res,))
        self.assertEqual((res["r2"], res["spent2"], res["capSpent"]), (False, 1, 1),
                         "with the budget spent the next wait returns at once and no timeout handed on is 0: %r" % (res,))
        self.assertEqual(res["timeouts2"], ["w1" + spent, "w2" + spent])
        self.assertEqual((res["r3"], res["clock3"], res["left3"], res["timeouts3"]), (True, 500, 500, []),
                         "a wait that comes on its third poll spends only what it took and records nothing: %r" % (res,))


if __name__ == "__main__":
    unittest.main()

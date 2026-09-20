#!/usr/bin/env python3
"""The suite's backend-singleton ratchet (tests/conftest.py: _sdk_singleton_restored and the class- and module-scoped
_sdk_singleton_class_boundary and _sdk_singleton_module_boundary), tested by running pytest in a child over scratch
modules that load the real kernel under this checkout's conftest, the way tests/test_tempdir_hygiene.py's
RunLeavesNothing tests the temp-root floors: each scratch case takes one of the roads the suite takes to
km._sdk_backend, and the outer test reads what the ratchet said about it.

The defect the ratchet guards (2026-09-19): kernel.py builds its SdkBackend lazily, the first km._sdk() call
constructing it over jd.STATE as it stands and caching it in km._sdk_backend for the life of the process.
tests/test_kernel.py::ViewBuilder pointed jd.STATE at a sandbox, its card builds reached km._sdk() and built the
singleton over the sandbox, and its tearDown restored jd.STATE and removed the directory without touching the
singleton; a later module's chat signature consulted that backend, whose fork_children statted the removed
registry, answered {} on the OSError and scanned no registry, so a derivation counting registry stats read 0
against 39 in a test that did nothing wrong, and only under an order that ran ViewBuilder first.

The population, measured at this branch's base: six classes in five modules leaked the singleton (ViewBuilder,
CostWeighting, BuildSessionDiffRows, FeedWarmResolveBumpsTheLedgerRevision, SharedViewInBuilds and
PushSurvivesOneFailedChatBuild), each fixed in a commit of its own with ViewBuilder's shape: ViewBuilder's before the
ratchet, the other four after it, one per module, found by the review round that ran the modules alone. The count
comes from running every module ALONE with the ratchet on, on the missing road, which is CI's: the test venv's
interpreter has no claude_agent_sdk, and a module run alone does not import tests/test_host_transport.py (that module is
the one exception in the union, since it puts the venv on sys.path itself). The population is a union, every set saved
beside the list with the script that derives it: the 237 modules a census plugin (a scratch pytest plugin over two full
-n 4 runs, on the SDK-importable road: tests/test_host_transport.py puts the box's SDK venv on sys.path at import, and
every xdist worker imports every collected module, so a full run here takes that road, which CI never does) saw
take a road to a root change (a jd.STATE assignment, a jd._rebind_state call, a singleton construction, or a singleton
that changed), the 94 that load the kernel under its shared name, the 272 whose text assigns jd.STATE or calls
_rebind_state in process (the private-kernel modules among them included: a private name isolates the kernel's
globals and not jd's, so they move the shared jd.STATE, and their own singletons are outside this fixture by the
stated limit; unprotected is a private-name kernel's dangling backend over a removed directory that a sibling file
reads and gets the silent empty-registry answer this fixture exists to stop, live today on romp_kernel_mc, which
tests/test_kernel_interrupt_machine_cut.py leaves dangling and two of the three files that load it read, that one and
tests/test_kernel_msgcaption.py; the loop cannot land here because the private-kernel harnesses carry 90 or more
pre-existing teardown leaks (the 90 measured over the three romp_kernel_mc files in one run, on the missing road; the
round-1 refuters' 574 over the 18 files, their count, its road not recorded, and a teardown count does not depend on the
road, since SdkBackend constructs on both), so their save-and-restore product code lands first, then the ratchet's
private-kernel
arm; Y pins the limit as behaviour, a private-name leak over a removed root with the ratchet silent and the run green,
red the day that arm lands), and the 316 the first sweep ran, module alone on the missing road; 364 modules in all. The
first sweep, over its 316 at the base, module alone on the missing road, found the 4 red on these leaks and 1 red for an
unrelated pre-existing reason (tests/test_sdk_rate_limit_usage.py, an unrestored ROMP_SERVE_TOKEN setdefault the judge
fixture's environment check names; identical with the ratchet off);
at this head every one of the 364 is green alone (the missing road, CI's) except that one. The full-suite census, on
the importable road, saw none of the five, because an earlier first builder in every worker made their builds cache
hits: a green suite run is no evidence a module is clean, and the module-alone sweep is the measurement; the green CI
run at the round-3 head is the missing-road full-suite datum.

The residual that leaves, a stated limit: a green run under the ratchet proves no leak occurred in that run and not that no
test would leak alone, because a first builder that leaves its build masks a later sandboxed test's reach as a cache hit
(no build, no transition, the ratchet silent). Measured at this head, as a pair and module alone on the missing road,
which is CI's (the test venv's interpreter has no claude_agent_sdk and neither run collects
tests/test_host_transport.py), tests/test_kernel_fleet_cache.py then
tests/test_token_usage.py with CostWeighting's fix reverted gave 77 passed and 0 verdicts, while the module alone gave 65
passed and 1 error. An arm keyed on the build event inherits the masking, since a cache hit is no build, so the
order-independent instrument is the module-alone sweep; a reach-under-moved-root arm with two signals (a leak keyed on
what is LEFT at teardown, and a wrong-root read keyed on the root the RETURNED backend was built over) is a follow-up
item, its own PR after this one. TheResidualIsWorded holds this wording here and in the ledger entry.

The ratchet judges TRANSITIONS, at three windows. The test: the singleton read before the test and after its own
teardown, and the test whose own transition made the bad state fails (a different object left, the directory
removed under the object it found, or that object's state_dir repointed, both sides rendered from the reads'
recorded text since the live attribute shows the after path on both). The class and module boundaries: a read at the
scope's start and at its end, after tearDownClass or tearDownModule, and the scope whose setup or teardown made the bad
state fails, the error
landing on the scope's last test with the boundary named. The setup before a test: a singleton found over a gone
directory that no verdict has named yet was made by something outside every window (import-time code, or a fixture
of a scope wider than the function) and is reported once per worker, at the first test that meets it, worded as
inherited, raised after that test's own teardown so its body runs and its own transition is judged beside it; every
later test that inherits the same object is quiet.
At the worker's first test window the same report covers a real backend over a directory that stands but is not
jd.STATE as the module boundary's START READ recorded it, when that backend is the object that read found: at the start
read only import-time code and any fixture of a scope wider than the function has run, so the identity term and the
start read's reference make the report a statement about that read; a module or class setup's install after it is left
to its boundary, which names the scope and prints the sandbox remedy, and a jd.STATE a scope setup moved for its tests
after that read is no leak and never the reference (K2: compared against the window's jd.STATE, the kernel's own
import-time build over the run root got the report). The first window spends the flag whether or not it takes the
report, and never defers it: a report deferred to a later window would fire where a test body has run, with its premise
sentence (before any test in this worker has run) false, a wrong attribution in place of a silence. When the slot at
the worker's first window does not hold the object the start read found, and that read's object is a real backend over
a directory that stands and is not the jd.STATE it recorded (an import-time build over a kept root met first by a class
that swapped the singleton out around its tests, S7), the window REFUSES instead, at the moment the flag is spent: it
names the leak from the start read's fields (the object, its root, and jd.STATE at that read), says a module or class
setup swapped the slot between the two reads, accuses no test and names no scope, and the run exits 1; the later test
that meets the object is quiet, and the refusal is the first window's alone (S7B). A start read's object over the run
root is no leak and gets no refusal (S8). One over a gone directory is refused too, under the gone wording, whatever its
root: the swapping scope may never put the object back, and then no window starts under it, the gone report never fires,
and the scope's boundary verdict names the swap and not the object's origin (S10, the refusal beside that verdict in
One.a's one teardown, the only line naming the leak's origin; and that verdict, the start-to-end judgment on the object
the class found, says the object it found is the one the first window refused to attribute, a clause of its own with
the same key, the object); when the scope does put it back, the later test that
starts under the object carries the gone report as well, two lines on two items each saying what the other does not
(S9), and that report names the object as the one the first window refused to attribute, the link keyed on the object
and not on the rendered path, which a repoint between the two lines changes (S9B; S10B for the boundary's pair, a
setUpModule repointing the object between the module start read and the class's reads, so the refusal renders the
recorded root and the verdict the live one, and the clause is still there); a second gone object a later class
builds and removes after the refusal carries its gone report without that clause, the link being membership by identity
and not any refusal's having been taken in the worker (S14), and the boundary's clause is keyed the same way, on the
object its start-to-end verdict renders as before, so a verdict rendering another object carries none: the scope found
the refused object and its teardown repointed the build its test left (S10C's One), the scope found an object no
refusal named while a refusal stands in the worker (S10C's Two), or the run took no refusal (M). The outer tests read
the refusal as
they read every report, by the test it lands on (inherited with the SWAPPED
or SWAPPED_GONE head) and as the set of tests carrying each head (carriers, a set of size one), never by a phrase
count. The class and module boundaries yield to the
tests' own windows: when the changing windows inside the scope run from the value the scope found to the value it ends
on, each judged where it happened against the scope's own reference root, the boundary says nothing, so a test's
accused reset or allowed rebuild is never re-attributed to a tearDownClass or tearDownModule that did nothing; a class
that drops the object it found before a test rebuilds, or moves jd.STATE for a test's build, stays the author. Its
allowances are derived from the transition, never from a list of test names:
None before and, after, the kernel's own class (module romp_sdk_backend, qualname SdkBackend; a look-alike is
refused) over jd.STATE AS THE TEST FOUND IT, that directory present, is a worker's lazy first build under the root
the test inherited, the kernel's own design; None before and False after is the kernel's own unavailable outcome.
WHICH test builds first depends on the run (the xdist scheduler, the subset, the module order), so a name list
could never be right: the census that found ViewBuilder saw a different first builder on each of three workers.
The remedy is one per road: the sandbox sentence when the value left is the kernel's class over a root that is
not the reference or not a directory; put the state_dir back where it was found when the same object was repointed;
put back the object you found otherwise. A kernel re-execution inside a test replaces the marker
function and resets the singleton, so the before value is stale and only what the test LEFT is judged, against
jd.STATE as the reload re-bound it: None or False pass, the lazy build over the loader's root passes, and a build
anywhere else is named with the re-execution wording; the kernel's FIRST load inside a test (no marker before) is
the same road, never an exemption.

The SDK road is forced in every scratch head, never inherited from the interpreter: claude_agent_sdk is absent from
CI's install and from the test venv's interpreter here, present on a box that installed it, AND a run here that
collects tests/test_host_transport.py takes the importable road (that module puts the box's SDK venv on sys.path at
import, and every xdist worker imports every collected module), so a full run here is the importable road while a
module-alone run is CI's; SdkBackend constructs either way (the probe at construction, importlib.util.find_spec, only
sets _sdk_missing and prints the not-found notices on the missing road), so the transition the ratchet judges is the
same on both roads, and the figures from this module's own runs carry no inherited road. SCRATCH_HEAD sets None in
sys.modules
for the name, which makes find_spec answer None and the import fail, so every run over it takes the missing road
wherever it runs (A's outer test reads the notices); Q takes the importable road over a head without that line and a
stub package importable by the child alone (nested_run's sdk_stub), asserts inside the child that the stub is what
imported and that _sdk_missing is False, and the same lazy first build passes there with neither notice in the output.

The scratch modules, one nested run each, the cases in method order (unittest runs a class's methods
alphabetically, and each case's `before` is what the previous case left):
  A, the singleton built under the run root first:
    a. the worker's lazy first build (None before; after, a backend over jd.STATE, present) passes;
    b. ViewBuilder's fixed shape (save km._sdk_backend, sandbox jd.STATE, build, put both back, remove the
       sandbox) passes;
    c. a kernel re-execution inside the test, the singleton reset and rebuilt over jd.STATE, is not judged;
    d. a rebuild over the SAME root left in place fails: another object under an equal state_dir, said as such
       (the readers hold the object, not the path), with the object road's remedy;
    e. ViewBuilder's original leak with the sandbox kept fails, naming the change and no gone directory;
    f. removing the directory under the singleton e left (the same object, present before and gone after) fails
       as this test's own transition, with the gone clause;
    g. ViewBuilder's original leak with the sandbox removed and a regular FILE written at the path fails, naming
       the change, the gone clause (a file is not a directory) and the sandbox remedy (its before value, f's gone
       object, was already named, so g starts quietly);
    h. a test that does nothing under g's gone object passes: inherited, already named, not accused;
    i. resetting the singleton to None and leaving it fails with the object road's remedy and no sandbox sentence.
  B, the leak as the worker's first build, and the re-execution road:
    a. None before and, after, a backend over a removed sandbox: the allowance does not cover it;
    b. a kernel re-execution that then builds over a removed sandbox fails with the re-execution wording and the
       gone clause;
    c. a kernel re-execution that then builds over a KEPT sandbox, jd.STATE restored, fails with the re-execution
       wording and no gone clause (the road the first form of the fixture exempted);
    d. XDG_STATE_HOME moved to a fresh root (hosts off), a re-execution so the judge re-binds jd.STATE there, then
       the lazy build over that root passes: the reference on this road is jd.STATE after the test (last in B,
       since it moves the child's environment).
  C, the first build over a sandbox that stands:
    a. None before and, after, a backend over a kept sandbox, jd.STATE elsewhere: the allowance does not
       cover it either (it asks for jd.STATE, not for any directory that exists).
    C is run a second time with a module-level DeprecationWarning planted in the scratch, so the child's summary
    line carries a warnings segment between passed and errors ("1 passed, 1 warning, 1 error in" today): the outer
    tests read the error count past that segment (summary_mismatch, which tolerates any other count between passed
    and errors and refuses a wrong count by name) and pin the segment's presence and position, not its count.
    C is run a third time from a parent that exports PY_COLORS=1 and FORCE_COLOR=1 for the child's start (the colour
    is switched off at the nested_run boundary): every read of C runs again over that output, and one more test reads
    that no escape sequence is in it.
  D, a class teardown that removes the directory under the singleton its tests left:
    One.a builds over a kept sandbox stored on the class and fails as its own; One.b does nothing and passes at
    its own window; tearDownClass removes the sandbox and writes a regular FILE at the path, and the class
    boundary fails at One.b's teardown with the gone clause (a file is not a directory); Two.a and Two.b do
    nothing under the named object and pass.
  E, an import-time leak (the module builds over a sandbox after loading the kernel, restores jd.STATE and
    removes the sandbox, before any test runs):
    a. does nothing and is the first test to meet the state: PASSED, then an ERROR at its teardown worded as
       inherited, with no remedy addressed to it; b. does nothing and passes; c. makes a kept-sandbox leak of its own
       and fails as its own.
  K, a class that moves jd.STATE for its tests:
    One: setUpClass moves jd.STATE to a class sandbox; a's lazy build lands over it and passes at its own window
    (it inherited that root); b passes; tearDownClass restores jd.STATE and keeps the sandbox, and the class
    boundary fails at One.b's teardown as the author. Two: setUpClass saves the singleton and jd.STATE, resets
    the singleton and moves jd.STATE to its sandbox; a builds and passes; tearDownClass puts both back and
    removes its sandbox: quiet.
  K2, the kernel's own import-time build over the run root, then setUpModule and One's setUpClass move jd.STATE for
    their tests without building and put it back: nothing leaked. One.a and Two.a find the singleton over the run root
    and jd.STATE elsewhere; no window reports it, since the first-window report's reference is the module start read's
    jd.STATE and not the window's, every boundary is quiet, and the run exits 0.
  L, a module teardown that removes the directory under the singleton its tests left:
    a builds over a kept sandbox stored on the module and fails as its own; b passes; tearDownModule removes it
    and the module boundary fails at b's teardown with the module named; the class end is quiet on the named
    object.
  H and H2, over a head that loads NO kernel at import (the worker's first load happens inside the test):
    H.a loads the kernel, then builds over a kept sandbox and fails with the first-load wording; H2.a loads the
    kernel, then makes the lazy build over the loader's root and passes (the run exits 0).
  F, the values the slot can be handed that are not the kernel's build over the inherited root:
    a. a class named SdkBackend defined in the scratch module, over jd.STATE, as the worker's first value: refused
       by the class check, rendered module-qualified (test_scratch.SdkBackend over ...), the object remedy;
    b. None left in place of it fails (object remedy); c. the kernel's own unavailable outcome (km._sdk_import_notice
       made to raise, so _sdk_locked's except branch sets False) passes; d. None left in place of False fails;
    e. the real lazy build over the run root passes; f. False left in place of the backend fails; g. a
    SimpleNamespace left fails, rendered as types.SimpleNamespace over no state_dir; h. a MagicMock left fails,
    rendered unittest.mock.MagicMock over its attribute's repr and WITHOUT the gone clause, which says a state_dir is
    no longer a directory and is true of the kernel's own class alone. Every failing case carries the object remedy
    and no sandbox sentence.
  J, the first build over a sandbox with jd.STATE LEFT at the sandbox: the singleton agrees with jd.STATE as left,
    and the ratchet still fails it, on the root the test inherited; the judge fixture names the STATE leak in the
    same teardown (two failures on one item render as an exception group in pytest 9), and the outer test reads
    both texts.
  N, with a follower module (the pair is one nested run; the follower takes the loaded kernel from sys.modules):
    One.a builds first; Sandboxed moves jd.STATE for its one test and never builds (quiet: the singleton over the run
    root is unnamed and not jd.STATE, the picture the first-window report names at the worker's first window only);
    Two.a leaves None (accused) and Two.b makes the allowed rebuild (passes alone); Three.a leaves None as the last
    test of a class that started on a real backend; Four.a rebuilds and Four.b leaves False; Five.a leaves None in
    place of False and Five.b rebuilds; Six's setUpClass drops the object it found and Six.a rebuilds (the class is
    named at its boundary with the rebuild text, the one boundary verdict in the run); the follower's one test leaves
    None as the last test of its module. Six accused tests, no boundary accused of what its tests did, no exception
    group.
  S6, an import-time build over a sandbox that STANDS (jd.STATE restored): a is the first test to meet it and also
    leaks on its own; its one teardown failure carries the inherited report (the kept-root wording, both roots named,
    no remedy) and its own verdict; b is quiet under a's named object.
  S7, S6's import-time build over a kept root met first by a class that swaps the singleton (One's setUpClass saves the
    singleton and jd.STATE, resets the slot and moves jd.STATE; a builds over the class root; tearDownClass puts both
    back): One.a's before object (None) is not the one the start read found, so the first window refuses in place of
    the kept-root report: the refusal on One.a's teardown names the leak from the start read's fields (SdkBackend over
    the kept root, jd.STATE the run root at that read), says the slot holds None at this window because a module or
    class setup swapped it between the two reads, accuses no test and names no scope; Two.a meets the import-time
    object at a later window and is quiet; every boundary is quiet; the run exits 1 (S6 is the control, the same leak
    with no swapping class, reported as inherited).
  S7B, S7 with a third class of One's shape after Two: a later window where the identity term fails, and the refusal is
    still the first window's alone (one carrier, Three.a quiet, Three's boundary quiet, one error).
  S8, the refusal's refused input on the run-root shape: K2's import-time build over the RUN root, then S7's swapping
    class; the identity term fails at One.a but the start read's object is over jd.STATE as that read recorded it, so
    no refusal, no report, and the run exits 0.
  S9, the gone shape, the object put back: E's import-time leak (the sandbox removed), then S7's swapping class; One.a's
    first window refuses under the gone head (the start read's object over a directory that no longer exists, the slot
    holding None, the cause family narrowed to import-time code or a wider-scoped fixture), and Two.a, which starts
    under the gone object put back, carries the inherited gone report, which names the object as the one the first window
    refused to attribute: two errors on two items, each line saying what the other does not; every boundary quiet.
  S9B, S9's two lines with the object repointed between them: setUpModule, after the module start read, repoints the gone
    object's state_dir to a second removed path and clears the slot; One.a's lazy build over the run root is allowed and
    its first window refuses under the gone head, naming the root the start read recorded; Two's setUpClass puts the
    repointed object in the slot and Two.a carries the gone report over the moved path, still naming the object as the
    one the first window refused (the link is the object, not the path); tearDownModule puts both back; two errors,
    every boundary quiet.
  S10, the gone shape, the object never put back: E's import-time leak, then a class whose setUpClass resets the slot
    and leaves it (jd.STATE untouched; a lazy-builds over the run root, Two.a meets that build); One.a's teardown
    carries the refusal under the gone head beside One's boundary verdict on the swap (before the gone object, after
    the class's build, the object remedy, and the verdict saying the object it found is the one the first window
    refused to attribute, the two lines linked at the object, the clause ending one period before the remedy), one
    exception group, one error; no test starts under the gone object, so no gone report; Two.a quiet. Without the gone
    arm the boundary verdict was the only line and named neither the gone directory nor import-time code.
  S10B, S10's two lines with the object repointed between the reads that render them: setUpModule, after the module
    start read, repoints the gone object's state_dir to a second removed path and leaves it in the slot; One's class
    start read finds the object over the moved path; One's setUpClass resets the slot and never puts the object back
    (jd.STATE untouched); One.a's lazy build over the run root is allowed and its first window refuses under the gone
    head, naming the root the module start read recorded; One's boundary verdict on the swap renders the object it
    found from the live attribute, the moved path, so the two lines render two paths for one object, and the verdict
    still says it found the one the first window refused (the link is the object, not the path); one exception group,
    one error; Two.a meets the build and is quiet; the module end is quiet on the named build.
  S10C, the refused object found by a class whose verdicts render other objects, the boundary clause's negatives with a
    refusal in the run: E's import-time gone leak, the object kept as _obj and put back by tearDownModule (the module's
    start and end reads agree on it, so the module end is quiet); One's setUpClass resets the slot (S10's swap), One.a
    lazy-builds over the run root, and One's tearDownClass repoints that build's state_dir to a kept sandbox (X.Two's
    shape), so One's verdict is the last-object repoint (before the build over the run root, after it over the sandbox,
    the state_dir remedy), rendering the build alone while the object One FOUND is the refused one, and carries no
    clause; Two does nothing under the build and its tearDownClass resets the slot to None (M.Three's shape), so Two's
    verdict is the start-to-end judgment on a found object no refusal named (before the build over the sandbox, after
    None, the object remedy), no clause while the refused list holds the first object; the refusal on One.a under the
    gone head beside One's verdict, one exception group; Two.a passes and errors at its teardown; two errors.
  S11, S7 with the start read's object repointed before the swap: One's setUpClass moves the import-time object's
    state_dir to a second sandbox, then saves, resets and moves jd.STATE; the refusal names the root the start read
    RECORDED (the kept one) and not the live attribute's (the repointed one); tearDownClass puts the object, jd.STATE and
    the state_dir back, so every boundary is quiet; Two.a is quiet; one error.
  S12, S7's swapping class BUILDING over its class root in place of resetting the slot: a real object of the class's own
    is in the slot at the first window, the identity term fails, and the refusal's window value says the slot holds
    SdkBackend over the class root, the one run that executes that branch of the render; One.a's window is a cache hit,
    Two.a meets the import-time object, every boundary is quiet, one error.
  S13, the refusal's named-object guard, a pair: module 1's One builds over a kept sandbox in setUpClass, restores
    jd.STATE, leaves the build in the slot and raises SkipTest, so no function window opens there and the first-window
    flag stays armed while One's class boundary names the object (an ERROR on the skipped One.a with the sandbox
    remedy; the module end quiet); the follower's Two is S7's swapping class over that object, so its Two.a opens the
    worker's first window with the identity term failing, and the refusal is silent because a verdict has named the
    object; Three.a meets the object put back and is quiet; two passed, one skipped, one error, no carrier of any head.
  S14, a second gone object after the refusal, the link clause's negative control: S9's import-time gone leak and swapping
    class (One.a's first window refuses under the gone head; One's tearDownClass puts the object back), then a class whose
    setUpClass builds over a sandbox of its own and removes it, leaving that second gone object in the slot for its one
    test and putting the first back after it; Two.a carries the gone report on the second object with no link clause (no
    refusal named that object; the two lines render two roots), every boundary is quiet, two errors.
  W, a session-scoped autouse fixture in the case directory's own conftest.py (nested_run's conftest) that builds over
    a kept root and restores jd.STATE before the module boundary's start read: a is the first test to meet it and
    carries the kept-root inherited report, its cause clause naming import-time code or a session- or package-scoped
    fixture; b is quiet, and both ends are quiet (no read brackets a session fixture).
  T, a setUpClass that makes the worker's first build over a kept sandbox and restores jd.STATE: the module's start
    read saw None, so One.a is not told import-time code made the object (no inherited report) and One's class
    boundary names the change from None with the sandbox remedy at One.b's teardown; the module end is quiet.
  Z, the first-window flag's pin (a pair): One.a's lazy first build passes unnamed, and the follower's class Moved
    moves jd.STATE for its one test without building, so its window sees the object its module's start read found
    over a root that is not jd.STATE; the flag says this is not the worker's first window, and nothing is said.
  U, a setUpClass that completes a leak (builds over a sandbox, restores jd.STATE, removes the sandbox): two error
    lines for one leak, the inherited gone report on One.a and One's class boundary at One.b's teardown naming the
    change from None with the gone clause and the sandbox remedy; the module end is quiet on the named object.
  V, the same leak completed by setUpModule: a's inherited report, the class end quiet (its start read saw the
    object) and the module end named at b's teardown with the gone clause and the sandbox remedy.
  X, the same object with its state_dir repointed: One.a builds first; One.b repoints the singleton at a kept sandbox
    and leaves it (named at its own window, both roots from the recorded text, no gone clause, the repoint remedy);
    One.c repoints and puts the state_dir back (quiet); Two's tearDownClass repoints the object its test left (the
    class boundary, named before its quiet rules); Three's tearDownClass puts back the object it found with its
    state_dir repointed (the put-back branch); the module end is quiet on the named object.
  Y, the stated limit as behaviour: the scratch loads the kernel a second time under a private name; a builds that
    kernel's singleton over a sandbox and removes it, b asserts inside the child that the leak stands and the shared
    slot is None; the ratchet says nothing and the run exits 0 (the control is B.a, the same leak under the shared
    name, named).
  M, class teardowns that install a value: One.a builds first; Two's tearDownClass builds over a kept sandbox (the
    class boundary names the change from the run root's backend to the sandbox's, sandbox remedy); Three's
    tearDownClass resets the slot to None (object remedy, no sandbox sentence); Four does nothing under the None and
    is quiet; Five's tearDownClass builds from None over a sandbox (named); Six does nothing under it and the module
    end is quiet. No refusal is taken in the run, and none of its three boundary verdicts, each the start-to-end
    judgment, names a refused object: the boundary link clause's negative with no refusal in the worker (S10C has one).
  P, a class that puts back the object it found and removes that object's directory: One.a leaks over a kept sandbox
    (named); Two's setUpClass saves and replaces the singleton and moves jd.STATE, Two.a builds over the class root
    (allowed), and Two's tearDownClass restores both and removes both roots: the class boundary names the put-back
    with the gone clause; Three does nothing under the gone object and is quiet.
  G, values on the other roads: a. a class whose __module__ claims romp_sdk_backend under another qualname, installed
    as the worker's first value over jd.STATE, is refused and rendered romp_sdk_backend.Fake; b. a re-execution that
    leaves a types.SimpleNamespace is named with the re-execution wording as a value that is not the kernel's build.
  R1 and R2, a real backend over the reference root whose directory is gone: the first build then rmtree(jd.STATE)
    (the allowance asks for a directory: the change from None is named with the gone clause and the sandbox remedy),
    and a re-execution, the lazy build, then rmtree(jd.STATE) (the reload road says jd.STATE is no longer a
    directory); the judge fixture names the removed root in the same teardown, one exception group each.
  Q, the worker's lazy first build on the importable road (the stub head, nested_run's sdk_stub): a asserts the stub is
    what imported and _sdk_missing is False, builds over jd.STATE and passes; the run exits 0 and neither notice is in
    its output.

The outer tests read a nested run's output by structure, never by the count of a phrase: the verbose per-phase lines
(outcomes, a set per case), the verdicts by the test or scope each names (verdict, inherited, boundary: the first
match, the ERRORS section's; carriers: the set of tests whose report opens with a head; boundary_scopes: the set of
scopes named), the final summary line parsed (summary_mismatch, and the warned run's read of its warnings segment), and
the presence or absence of a text (the
judge fixture's, the exception group's header, the SDK notices), which the short summary cannot change since it only
repeats what the ERRORS section already printed; the readers are the helpers defined between nested_run and _NestedRun
whose first parameter is the child's output, and TheReadersRosterNamesEveryReader derives that population from the
source and reads each name here. CI's pytest is
unpinned (the workflow installs the latest, 9.1.1
today, the test venv's version here too), and pytest's short summary prints each error's message whole when CI is set
in the environment or at -vv and trimmed to the terminal width otherwise, so a reader that counted the boundary text's
occurrences read 1 on a box and 2 on CI for one verdict (the CI red at the round-3 preparation head: red here with
CI=true alone and under a CI-like install through uv, green at this head both ways). The PROTECTION is the structured
reads above: none of them counts occurrences,
so the summary's shape cannot change what they read. The child also runs -vv, which is NOT a protection: it only makes a box
run print what CI prints so a reader comparing the two by eye sees one shape; pytest may change what -vv prints and the
readers would still hold, while a structured read removed as redundant with -vv would put the count back. Two of the
readers parse plain text, outcomes over the per-phase lines and SUMMARY_LINE over the final line, so the child's colour
is switched off at the nested_run boundary (its colour-forcing variables popped and --color=no passed; the pin is C's run
from a parent that exports PY_COLORS=1 and FORCE_COLOR=1): under an inherited PY_COLORS=1 the child printed ANSI markup
into both and 74 of the 100 tests at the round-3 head went red. The independence is of the short summary's shape, never
of the summary line's own format: two readers parse that line (summary_mismatch over SUMMARY_LINE, and the warned run's
segment read) and fail loudly, the line quoted, when it changes.

Mutations of the fixture run against this module, each landed and reverted (2026-09-19; the runner compile-checks the
mutated conftest and counts a NameError in the outer output as a crash, never as a weakening), listed by what the
fixture READS and the branch each read feeds, each with a case that reds under it: a witness, never the set (a case
added later joins a set, and no sentence here says it did not). The refusal's cells and the boundary link's, the ones
the S cases keep touching, state instead the RULE every red case satisfies and carry a derive id: the mutation is data
(MUTATIONS, the exact text replaced in tests/conftest.py), TheMutationCellsApply pins that each replaced text occurs
exactly once at this tree and that the matrix and the table name the same cells, and
`python -B tests/test_sdk_singleton_ratchet.py --derive <id>` plants the cell in a detached worktree at HEAD, runs this
module there, prints the red cases by case id with the head it ran at, and removes the worktree: a cell's current list
is that run's, at the head it prints, and none is written here.
  the reads (_sdk_read): the marker ignored, every test on the same-marker road (A.c fails falsely on the stale
    pre-reload object); a None marker before treated as the same-marker road (H2.a fails falsely) or as an exemption
    (H.a passes); os.path.isdir replaced by os.path.exists (D.One's boundary verdict disappears, A.g); isdir forced
    True (A.f, A.g, B.a, D, L); the last read never recorded (D and L boundary text); the before read replaced by a
    null record (A.d, A.e, E.a and more); the after read skipped (every failing case).
  the same-marker judgment: the same-object gone transition deleted (A.f passes silently); the repoint comparison
    dropped (X.One.b passes silently); the gone check made
    absolute again (A.h, E.b and D.Two fail as false accusations and every error count rises); identity replaced by
    equality of state_dir (A.d passes); the rebuild road rendered as before (A.d's text); the gone clause's class gate
    dropped (F.h carries
    the clause); a None after treated as
    nothing left (A.i and F.d pass); any False after admitted (F.f passes); the None-to-False allowance removed (F.c
    errors).
  the allowance: its gate opened to any before value (A.d passes); the class check dropped (F.a's look-alike passes),
    reduced to the qualname (F.a) or to the module (G.a's module-claiming look-alike passes); the root comparison
    dropped (C.a passes); the reference moved to jd.STATE after the test (J.a passes this fixture); the isdir term
    dropped (R1: the ratchet's clause disappears and the run stays red on the judge's alone); root and isdir both
    dropped (B.a, C.a, J.a).
  the changed-marker road: turned back into an exemption with only the gone check surviving (B.c and H.a pass
    silently); compared to jd.STATE before the test (B.d fails falsely); the gone clause dropped from its wording
    (B.b); a value that is not the kernel's build admitted (G.b passes); the build over a gone jd.STATE admitted (R2:
    the ratchet's clause disappears); the real-elsewhere verdict deleted (B.c, H.a).
  the remedy pick: one remedy on every road (F.a, F.b, F.d, F.f, F.g and A.i assert it absent); the object road for
    a real backend over a gone reference (R1 and R2 assert the sandbox remedy).
  the inherited report: deleted (E.a passes: an import-time leak is never reported); without the named list (E.b
    errors too); fired only on a named object (E.a); raised at the setup again (E.a and S6.a run no body); the own
    verdict dropped beside it (S6.a); the inherited object not named (E.b, S6.b); the kept-root clause deleted (S6.a
    passes silently); its first-window flag ignored (Z's Moved gets a false report); the kept-root report taken without
    the identity term (T's One.a gets a false report blaming import-time code, and the run counts two errors, the
    boundary verdict staying beside it); its reference moved from the module start read's jd.STATE to the window's (K2's
    One.a gets a false report blaming import-time code for the moves setUpModule and setUpClass made for their tests).
  the first window's refusal (_sdk_swapped), each cell a rule and a derive id: deleted (red: every case whose first
    window refuses, reading the refusal line or the exit code it sets; derive: refusal-deleted); keyed on the window's
    before object in place of the start read's (red: every refusing case whose first window holds None, the swapping
    classes' reset, the refusal then silent, and every case whose start read found no object while its first window
    holds a real one, that object then refused as the start read's; a window holding a real build of the class's own
    beside a refused start read still renders the start read's fields; derive: refusal-window-object); the reference
    root rendered from the window's jd.STATE in place of the start read's (red: every refusing case whose scope moved
    jd.STATE before its first window and that reads the jd.STATE the refusal names by value, a run root ending in
    /romp; a case reading the object's root or the heads alone stays green; derive: refusal-window-root); the start
    read's object rendered from the live attribute in place of its recorded state_dir
    (red: every case whose refused object is repointed between the module start read and the first window and that
    reads the refusal's root; derive: refusal-live-root); the window value rendered as None whatever the slot holds
    (red: every refusing case whose first window holds a real object and reads it in the refusal; the window value's
    recorded-text argument is inert, nothing running between the before read and the render, annotated at the call and
    not a cell; derive: refusal-window-value-none); the named-object term dropped from its guard (red: every case where
    a verdict named the start read's object before the first window opened; derive: refusal-named-guard); its class
    guard dropped (red: every case whose module start read found no real object and whose first window does not hold
    that value, the refusal then naming None (not built); derive: refusal-class-guard); its run-root guard dropped (red:
    every case whose start read's object stands over jd.STATE as that read recorded it and whose first window does not
    hold it; derive: refusal-run-root-guard); its gone arm removed, the start read's gone object refused silently (red:
    every case whose first window refuses under the gone head; derive: refusal-gone-arm-removed); the gone arm rendered
    under the kept head (red: every case whose first window refuses under the gone head, each reading the carriers of
    both heads; derive: refusal-gone-under-kept-head); the kept arm rendered under the gone head (red: every case whose
    first window refuses under the kept head; derive: refusal-kept-under-gone-head); the gone arm's cause clause
    replaced by the kept arm's (red: every case that reads the gone refusal's cause clause, the needle naming a
    directory since removed; a case reading the gone head alone stays green; derive: refusal-gone-cause-swapped); the
    kept arm's cause clause replaced by the gone arm's (red: every case that reads the kept refusal's cause clause, the
    needle naming a root that is not the run's; derive: refusal-kept-cause-swapped); the refused list never written
    (red: every case that reads a link clause present; derive: refused-list-unwritten); the link clause dropped from
    the gone branch (red: every case that reads the gone report's link clause present; derive: report-link-dropped);
    the clause emitted for every gone report (red: every case that reads a gone report on an object no refusal named
    for the clause's absence, whether the run took no refusal or took one on another object; derive:
    report-link-unconditional); the link keyed on the rendered text in place of the object, the refusal recording its
    object's path as the module start read recorded it and the report testing the object's live rendering against that
    list (red: every case whose refused object is repointed between the module start read and the gone report on it, the
    two paths then differing; derive: report-link-by-path); the link keyed
    on any refusal in the worker in place of the refused object, membership by existence (red: every case with a
    refusal followed by a gone report on an object no refusal named; derive: report-link-by-existence); the refusal
    marking its object as reported (red: every case with a gone report on the refused object after the refusal, that
    report then silenced; derive: refusal-marks-reported); the flag dropped from its condition with the spent first
    term kept (red: every case whose worker has a later window where the refusal renders at all, whether or not the
    slot holds the start read's object there (the identity check lives in the spent first term), its guards standing:
    the object real, unnamed, unreported, and gone or off the recorded jd.STATE; a case whose object a verdict named or
    the first window's report marked stays green; derive: refusal-flag-dropped); the identity term alone in the
    condition's place (red: every refusing case whose worker has a later window where the identity term fails, the
    refusal's guards standing there; a case whose start read found no object is never a refusing one, whatever its later
    windows hold; derive: refusal-identity-alone); a scope
    appended to its text (red: every case that reads the refusal for naming no scope or test; derive:
    refusal-scope-appended); the flag kept when the identity term fails, the deferral not taken (red: every case whose
    first window refuses, the refusal then never taken and the flag spent only where the identity term holds, so a
    later window that holds the start read's object over its standing root carries the kept-root report with its
    premise sentence false; derive: refusal-flag-kept).
  the boundary verdict's link to the refusal (_sdk_found_refused), each cell a rule and a derive id: the clause dropped
    (red: every case that reads the boundary's clause present, a scope that found the refused object and ended on
    another value; derive: boundary-link-dropped); the link keyed on the rendered text in place of the object, the
    refusal recording its object's rendered path and the boundary testing the found object's live rendering against
    that list (red: every case whose refused object is repointed between the module start read and the scope's reads,
    the two paths then differing; derive: boundary-link-by-path); the clause emitted on every start-to-end verdict
    (red: every case that reads a start-to-end boundary verdict on a found object no refusal named for the clause's
    absence, or reads one to its last words; the last-object and put-back roads carry no gate and are untouched;
    derive: boundary-link-unconditional); the link keyed on any refusal in the worker in place of the found object,
    membership by existence (red: every case with a refusal followed by a start-to-end boundary verdict whose found
    object is not the refused one; derive: boundary-link-by-existence); the clause keyed on the found object on every
    road, the gate moved from the start-to-end call to the boundary fixture (red: every case whose scope found the
    refused object and whose verdict renders another object, the last-object roads; derive:
    boundary-link-on-start-object); the clause moved into _sdk_judge, the boundary's call bare and the changed-object
    return wrapped, so it rides the function fixture's road too (red: every case that reads a test's own verdict whose
    before value is the refused object for the clause's absence; derive: boundary-link-in-judge); the changed-marker
    term dropped from the gate, the clause then riding the reload judgment too (red: every case whose scope found the
    refused object and ends on a kernel re-execution the reload judgment names, a line that renders no before value;
    derive: boundary-link-marker-term-dropped).
  the boundary: the class end deleted (D.One.b and K.One.b show no boundary error, M, P); the module end deleted
    (L.b shows none); compared to its last read only (K.One passes silently); judged without the restore exemption
    (K.Two errors); the named skip dropped (a second report at the class or module end of A, B, C, D, E, K and L;
    where the scope's last case fails on its own the boundary failure folds into that item's one teardown report, so
    those runs pin it by reading the boundary text, not the count); the quiet rule reading the inherited report's
    list too, the one-list behaviour (U's class boundary and V's module boundary disappear); the same-object gone
    transition deleted (D and L); the repoint of the last test's object dropped (X.Two's boundary disappears); the
    put-back-repointed comparison dropped (X.Three's boundary disappears, the module end quiet on the named object); the
    put-back-of-a-gone-object branch deleted (P's boundary text disappears); the final start-to-end judgment deleted
    (M's three boundary verdicts disappear); the object it accused not named (D.Two.a gets an inherited
    report); the start read replaced by a null record (K.Two and others); the yield to the tests' windows removed
    (N: boundary text on every accused class, Two.b errors), without its first-window condition (Six's boundary
    disappears) or without its reference condition (K.One passes silently); the windows never recorded (as the
    yield removed).
  the function fixture not naming the object it accused (A.h gets an inherited report, E, D).
Eighty-nine cells red at the round-6 head.
Four are pinned by no run at the round-6 close head, each for a stated reason: the unreadable reference root granting
the allowance (not constructible: the kernel always binds jd); the yield's identity condition dropped (redundant by
construction: when the end value is the last read's and is not the last window's value, a class teardown inside the
scope installed it, and that class's own boundary judged it against its start, which only a restore of the value the
scope found passes, so the module end is looking at its own start value); the windows list not cleared at the module
end (the read-count filter never selects a stale entry; the clearing bounds memory); the refusal's _sdk_reported term (a
belt: the one site that fills _SDK_REPORTED, the function fixture's report line, runs after the refusal is computed in
the same first window, and no earlier window exists in the worker, so the list is empty whenever the refusal is
consulted; dropped, the module stays green; the _sdk_named term beside it is reachable and pinned, S13); and no others.
"""
import ast
import inspect
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest import mock
from romp_load import load_source  # noqa: F401  a direct run's floor lands with this import (tests/romp_load.py)

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
BIN = os.path.join(ROOT, "bin")
# Hermetic state BEFORE any load: romp modules resolve their state root at import time, and only pytest runs
# conftest's floor (a bare unittest or script run otherwise writes REAL state).
os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
os.environ.pop("ROMP_STATE_DIR", None)  # a live kernel's export outranks the XDG floor

RATCHET = "left the kernel's backend singleton (km._sdk_backend)"
REMEDY_A = "save km._sdk_backend before moving jd.STATE and put it back where jd.STATE is restored"
REMEDY_B = "Put back the object the test found, None or False included, not an equal one"
SANDBOX = "A test that reaches km._sdk() under a sandboxed jd.STATE"      # the sandbox road's sentence, absent on the object road
REBUILT = "after another SdkBackend over the same directory (the readers hold the object, not the path)"
GONE = "whose state_dir is no longer a directory"
REEXEC = ("re-executed the kernel (or loaded it for the first time) and left the kernel's backend singleton "
          "(km._sdk_backend)")
INHERITED = "starts under the kernel's backend singleton (km._sdk_backend) over a directory that no longer exists"
INHERITED_KEPT = ("starts under the kernel's backend singleton (km._sdk_backend) over a directory that is not jd.STATE, before any "
                  "test in this worker has run")
PUT_BACK_GONE = "put back the kernel's backend singleton (km._sdk_backend) it found, whose directory is gone: "
SWAPPED = ("opens the worker's first test window, and this module's start read had found the kernel's backend singleton "
           "(km._sdk_backend) over a directory that is not jd.STATE, before any test in this worker has run")
SWAPPED_GONE = ("opens the worker's first test window, and this module's start read had found the kernel's backend singleton "
                "(km._sdk_backend) over a directory that no longer exists, before any test in this worker has run")
REFUSED_OBJECT = "the object this worker's first test window refused to attribute"   # the gone report's link to the refusal's line
# The start-to-end boundary verdict's own link to the refusal's line (_sdk_found_refused). REFUSED_FOUND carries
# REFUSED_OBJECT, so that needle reads both clauses absent (S10C, M); REFUSED_FOUND_TAIL is the clause's last words, where
# the clause ends, one period before "Fix:" (S10, S10B).
REFUSED_FOUND = "The object this scope found is " + REFUSED_OBJECT
REFUSED_FOUND_TAIL = "the scope at whose end the slot no longer held it, and the value it held"
PUT_BACK_REPOINTED = "put back the kernel's backend singleton (km._sdk_backend) it found with its state_dir repointed: before "
REMEDY_C = ("Put back the singleton's state_dir where it was found: the kernel's readers hold the object and read its state_dir "
            "on every registry scan")
BOUNDARY = "'s class or module boundary (tearDownClass, tearDownModule or a class- or module-scoped fixture)"
SHARED_STATE = "left shared state changed"     # the judge fixture's text: quiet in every case here, so the ratchet's is the only red
SDK_NOT_FOUND = "sdk-backend: claude_agent_sdk not found"     # the boot log's line on the missing road (_sdk_import_notice)
SDK_NOT_IMPORTABLE = "claude_agent_sdk is NOT importable"     # the backend's construction notice on the missing road

# The mutation table: cell id -> (target file relative to tests/, the exact substitutions). Each old text occurs exactly
# once in its target at this tree (TheMutationCellsApply), so a fixture edit that moves an anchor reds that pin instead
# of retiring the cell silently. The rule each cell's red set satisfies is written in the module docstring's matrix
# alone, beside "derive: <id>"; no list of red cases is written anywhere: `python -B tests/test_sdk_singleton_ratchet.py
# --derive <id>` (derive, below) plants the cell in a detached worktree at HEAD, runs this module there and prints the
# red cases by case id with the head it ran at. The ids are the refusal block's (the module docstring's matrix).
# _sdk_swapped's guard: the start.isdir line tells it from _sdk_inherited's, which opens the same way
_REFUSAL_GUARD = ("    if not _sdk_is_real(be) or _sdk_named(be) or _sdk_reported(be):\n        return None\n"
                  "    if start.isdir is False:\n")
_REFUSAL_RENDER = "% (head, _sdk_singleton_text(be, start.sd), start.jd_state,"
_REFUSAL_CONDITION = "    if _SDK_FIRST_WINDOW and _SDK_MODULE_START is not None and not first:\n"
_REFUSE_CALL = "_sdk_refuse(_SDK_MODULE_START.be)"
_LINK_CONDITION = 'if _sdk_refused(be) else "")'
_GONE_HEAD_LINE = "        head, cause = _SDK_SWAPPED_GONE_HEAD, ("
_KEPT_HEAD_LINE = "        head, cause = _SDK_SWAPPED_HEAD, ("
_GONE_CAUSE = ('("building the singleton over a directory since removed, or removing the directory "\n'
               '                                               "it was built over")')
_KEPT_CAUSE = ('("building the singleton over a root that is not the run\'s, or moving jd.STATE after the "\n'
               '                                          "build and leaving it there")')
# the boundary link's gate (_sdk_found_refused), its one call site in _sdk_judge_scope, and the boundary fixture's call
_BOUNDARY_LINK_GATE = ("    if verdict is None or end.marker is not start.marker or not _sdk_refused(start.be):\n"
                       "        return verdict\n")
_BOUNDARY_LINK_CALL = "    return _sdk_found_refused(_sdk_judge(start, end, start.jd_state), start, end)\n"
_BOUNDARY_VERDICT = "    verdict = _sdk_judge_scope(start, last, end, windows)\n"
# _sdk_judge's changed-object return, the function fixture's road: the clause must never be attached here
_JUDGE_CHANGED_RETURN = ('    return ("left the kernel\'s backend singleton (km._sdk_backend) changed after its teardown: before %s, '
                         'after %s%s"\n'
                         '            % (_sdk_singleton_text(be0), after_text, unreadable), _sdk_remedy(after, ref))\n')
MUTATIONS = {
    "refusal-deleted": ("conftest.py", [
        ("        swapped = _sdk_swapped(_SDK_MODULE_START, before)\n", "        swapped = None\n")]),
    "refusal-window-object": ("conftest.py", [("    be = start.be\n", "    be = before.be\n")]),
    "refusal-window-root": ("conftest.py", [
        (_REFUSAL_RENDER, "% (head, _sdk_singleton_text(be, start.sd), before.jd_state,")]),
    "refusal-live-root": ("conftest.py", [(_REFUSAL_RENDER, "% (head, _sdk_singleton_text(be), start.jd_state,")]),
    "refusal-window-value-none": ("conftest.py", [
        ("_sdk_singleton_text(before.be, before.sd),", "_sdk_singleton_text(None),")]),
    "refusal-named-guard": ("conftest.py", [(_REFUSAL_GUARD, _REFUSAL_GUARD.replace(" _sdk_named(be) or", ""))]),
    "refusal-class-guard": ("conftest.py", [(_REFUSAL_GUARD, _REFUSAL_GUARD.replace("not _sdk_is_real(be) or ", ""))]),
    "refusal-run-root-guard": ("conftest.py", [
        ("    elif start.sd == start.jd_state:\n        return None\n", "    elif False:\n        return None\n")]),
    "refusal-gone-arm-removed": ("conftest.py", [
        ("    if start.isdir is False:\n" + _GONE_HEAD_LINE,
         "    if start.isdir is False:\n        return None\n    elif False:\n" + _GONE_HEAD_LINE)]),
    "refusal-gone-under-kept-head": ("conftest.py", [(_GONE_HEAD_LINE, _KEPT_HEAD_LINE)]),
    "refusal-kept-under-gone-head": ("conftest.py", [(_KEPT_HEAD_LINE, _GONE_HEAD_LINE)]),
    "refusal-gone-cause-swapped": ("conftest.py", [(_GONE_CAUSE, _KEPT_CAUSE)]),
    "refusal-kept-cause-swapped": ("conftest.py", [(_KEPT_CAUSE, _GONE_CAUSE)]),
    "refused-list-unwritten": ("conftest.py", [(_REFUSE_CALL, "None")]),
    "report-link-dropped": ("conftest.py", [(_LINK_CONDITION, 'if False else "")')]),
    "report-link-unconditional": ("conftest.py", [(_LINK_CONDITION, 'if True else "")')]),
    "report-link-by-path": ("conftest.py", [
        ("_SDK_REFUSED = []", "_SDK_REFUSED_TEXT = []; _SDK_REFUSED = []"),
        (_REFUSE_CALL, _REFUSE_CALL + "; _SDK_REFUSED_TEXT.append(_sdk_singleton_text(_SDK_MODULE_START.be, "
                       "_SDK_MODULE_START.sd))"),
        (_LINK_CONDITION, 'if _sdk_singleton_text(be) in _SDK_REFUSED_TEXT else "")')]),
    "report-link-by-existence": ("conftest.py", [(_LINK_CONDITION, 'if _SDK_REFUSED else "")')]),
    "refusal-marks-reported": ("conftest.py", [(_REFUSE_CALL, _REFUSE_CALL + "; _sdk_report(_SDK_MODULE_START.be)")]),
    "refusal-flag-dropped": ("conftest.py", [
        (_REFUSAL_CONDITION, "    if _SDK_MODULE_START is not None and not first:\n")]),
    "refusal-identity-alone": ("conftest.py", [
        (_REFUSAL_CONDITION, "    if _SDK_MODULE_START is not None and before.be is not _SDK_MODULE_START.be:\n")]),
    "refusal-scope-appended": ("conftest.py", [
        ('        lines.append("%s %s" % (request.node.nodeid, swapped))\n',
         '        lines.append("%s %s (%s)" % (request.node.nodeid, swapped, request.node.parent.nodeid))\n')]),
    "refusal-flag-kept": ("conftest.py", [
        (_REFUSAL_CONDITION, "    if False:\n"),
        ("    _SDK_FIRST_WINDOW = False\n", "    if first:\n        _SDK_FIRST_WINDOW = False\n")]),
    "boundary-link-dropped": ("conftest.py", [(_BOUNDARY_LINK_GATE, "    if True:\n        return verdict\n")]),
    "boundary-link-by-path": ("conftest.py", [
        ("_SDK_REFUSED = []", "_SDK_REFUSED_TEXT = []; _SDK_REFUSED = []"),
        (_REFUSE_CALL, _REFUSE_CALL + "; _SDK_REFUSED_TEXT.append(_sdk_singleton_text(_SDK_MODULE_START.be, "
                       "_SDK_MODULE_START.sd))"),
        (_BOUNDARY_LINK_GATE, "    if verdict is None or end.marker is not start.marker or _sdk_singleton_text(start.be) not in "
                              "_SDK_REFUSED_TEXT:\n        return verdict\n")]),
    "boundary-link-unconditional": ("conftest.py", [
        (_BOUNDARY_LINK_GATE, "    if verdict is None:\n        return verdict\n")]),
    "boundary-link-by-existence": ("conftest.py", [
        (_BOUNDARY_LINK_GATE, "    if verdict is None or end.marker is not start.marker or not _SDK_REFUSED:\n"
                              "        return verdict\n")]),
    "boundary-link-on-start-object": ("conftest.py", [
        (_BOUNDARY_LINK_CALL, "    return _sdk_judge(start, end, start.jd_state)\n"),
        (_BOUNDARY_VERDICT, "    verdict = _sdk_found_refused(_sdk_judge_scope(start, last, end, windows), start, end)\n")]),
    "boundary-link-marker-term-dropped": ("conftest.py", [
        (_BOUNDARY_LINK_GATE, "    if verdict is None or not _sdk_refused(start.be):\n        return verdict\n")]),
    "boundary-link-in-judge": ("conftest.py", [
        (_BOUNDARY_LINK_CALL, "    return _sdk_judge(start, end, start.jd_state)\n"),
        (_JUDGE_CHANGED_RETURN, _JUDGE_CHANGED_RETURN.replace("    return (", "    return _sdk_found_refused((", 1)
                                .replace("_sdk_remedy(after, ref))\n", "_sdk_remedy(after, ref)), before, after)\n"))]),
}
DERIVE_DESELECT = "tests/test_sdk_singleton_ratchet.py::TheMutationCellsApply"   # reds under any plant (its docstring)
DERIVE_ENV_DROPPED = ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_CURRENT_TEST",
                      "PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT", "ROMP_TESTS_SYSTEM_TMPDIR",
                      "PY_COLORS", "FORCE_COLOR", "CLICOLOR_FORCE",      # what nested_run pops from its child's
                      "CLAUDE_CODE_SESSION_ID")                          # environment; the session id the recipe unsets


def mutation_cell_text(doc, cell):
    """The docstring cell that carries "derive: <cell>", whitespace collapsed: from the cell's own opening words to the
    close of the parenthesis the derive id sits in (nested parentheses balanced), or None when no cell carries it. The
    pin reads it for the rule's presence; derive prints it beside the derived list, so the rule and the list sit
    together in one output."""
    doc = re.sub(r"\s+", " ", doc)
    tag = "; derive: %s)" % cell
    end = doc.find(tag)
    if end < 0:
        return None
    end += len(tag)
    depth, i = 0, end - 1
    while i >= 0:
        if doc[i] == ")":
            depth += 1
        elif doc[i] == "(":
            depth -= 1
            if depth == 0:
                break
        i -= 1
    start = max(doc.rfind("; ", 0, i), doc.rfind("): ", 0, i))       # the previous cell's end, or the block's head
    return doc[doc.index(" ", start) + 1:end]


def derive(cell):
    """Plant the cell's mutation in a detached worktree at HEAD, run this module there, print the red cases by case id
    with the head, and remove the worktree: the runnable derivation of the cell's current red set, which no sentence in
    this module lists (the module docstring's matrix states each cell's rule and points here). Exits 0 when the plant
    and the run completed, whatever the run's colour; an old text absent or found twice, a mutated file that does not
    parse, or a run that does not finish is a loud error. The applicability pin is deselected on the command line, never
    skipped in the test: under any plant it reds (a replacement that removes its old text fails the exact-once count,
    and one that appends beside the old text puts a new text the pin holds absent into the file), and it is no cell's
    set. The run's environment is the test recipe's (every ROMP_* variable and the pytest variables nested_run pops
    dropped, TMPDIR fresh)."""
    target, subs = MUTATIONS[cell]
    scratch = tempfile.mkdtemp(prefix="derive-")
    tree = os.path.join(scratch, "tree")
    added = False
    try:
        git = ["git", "-C", ROOT]
        head = subprocess.run(git + ["rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
        subprocess.run(git + ["worktree", "add", "--detach", "--quiet", tree, "HEAD"], check=True)
        added = True
        print("# cell: %s" % cell)
        print("# head: %s" % head)
        dirty = subprocess.run(git + ["status", "--porcelain", "--", "tests/conftest.py",
                                      "tests/test_sdk_singleton_ratchet.py"],
                               check=True, capture_output=True, text=True).stdout
        if dirty.strip():
            print("# warning: the working tree differs from HEAD (%s); the derivation ran at HEAD"
                  % ", ".join(sorted(line[3:] for line in dirty.splitlines())))
        path = os.path.join(tree, "tests", target)
        with open(path) as f:
            text = f.read()
        for old, new in subs:
            n = text.count(old)
            if n != 1:
                raise SystemExit("%s: the old text occurs %d times in %s, not once: %r" % (cell, n, target, old))
            text = text.replace(old, new)
        ast.parse(text, filename=path)
        with open(path, "w") as f:
            f.write(text)
        print("# planted: %s, %d substitution(s)" % (target, len(subs)))
        env = {k: v for k, v in os.environ.items() if not k.startswith("ROMP_") and k not in DERIVE_ENV_DROPPED}
        env.update(TMPDIR=scratch, PYTHONDONTWRITEBYTECODE="1")
        cmd = [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", "-q", "-rf",
               "--deselect", DERIVE_DESELECT, "tests/test_sdk_singleton_ratchet.py"]
        print("# run: %s (in the worktree)" % " ".join(cmd[1:]))
        r = subprocess.run(cmd, cwd=tree, env=env, capture_output=True, text=True, timeout=1200)
        if r.returncode not in (0, 1):
            raise SystemExit("%s: pytest exited %d, not 0 or 1:\n%s"
                             % (cell, r.returncode, r.stdout[-4000:] + r.stderr[-2000:]))
        failed = {}
        for cls, test in re.findall(r"^FAILED tests/test_sdk_singleton_ratchet\.py::(\w+)::(\w+)", r.stdout, re.M):
            failed.setdefault(cls, []).append(test)
        module = sys.modules[__name__]
        ids = {}
        for cls in failed:
            scratch_text = getattr(getattr(module, cls, None), "SCRATCH", None)
            names = [n[len("SCRATCH_"):] for n, v in vars(module).items()
                     if n.startswith("SCRATCH_") and v is scratch_text]
            ids[cls] = "/".join(sorted(names)) if isinstance(scratch_text, str) and names else "-"
        for cls in sorted(failed, key=lambda c: (ids[c], c)):
            print("red: %s (%s): %s" % (ids[cls], cls, ", ".join(sorted(failed[cls]))))
        lines = [line for line in r.stdout.splitlines() if line.strip()]
        print("summary: %s" % (lines[-1] if lines else "(no output)"))
        print("cell: %s" % (mutation_cell_text(__doc__, cell)
                            or "(no cell in the module docstring carries derive: %s)" % cell))
    finally:
        if added:
            subprocess.run(git + ["worktree", "remove", "--force", tree], check=False)
        shutil.rmtree(scratch, ignore_errors=True)


SCRATCH_HEAD = textwrap.dedent('''\
    import os, shutil, sys, tempfile, unittest
    from pathlib import Path
    from romp_load import load_source     # the suite's loader (tests/__init__.py registers it under tests.conftest)
    os.environ["ROMP_KERNEL_NO_OPEN"] = "1"
    os.environ.setdefault("ROMP_SERVE_TOKEN", "testtok")
    os.environ["XDG_STATE_HOME"] = tempfile.mkdtemp()
    os.environ.pop("ROMP_STATE_DIR", None)
    # This module's own state root, hosts off: per-session hosts are on by default, and a backend built over a root with
    # no session-hosts file starts a real bin/romp-session-host for any session it connects (CLAUDE.md, Testing). The
    # runner's conftest floors the run root it minted and only that one; the lazy first builds below (A.a and every case
    # that builds over this root) build over THIS one, so the switch is written here, before any build, as sandbox() does.
    os.makedirs(os.path.join(os.environ["XDG_STATE_HOME"], "romp"))
    Path(os.environ["XDG_STATE_HOME"], "romp", "session-hosts").write_text("off\\n")
    # The SDK road is forced, not inherited from the interpreter: CI's install and the test venv have no
    # claude_agent_sdk, a box that installed it has one, and SdkBackend constructs either way (the probe at construction,
    # importlib.util.find_spec, only sets _sdk_missing and prints the not-found notice on the missing road). None in
    # sys.modules for the name makes find_spec answer None and the import fail, so a run over this head with the line
    # below takes the missing road wherever it runs; Q's head (SCRATCH_HEAD_SDK_STUB) replaces the line with a comment
    # and takes the importable road with a stub package on the child's path (nested_run's sdk_stub).
    sys.modules["claude_agent_sdk"] = None
    KERNEL = os.path.join(os.environ["ROMP_RATCHET_BIN"], "romp-kernel")
    km = load_source("romp_kernel", KERNEL)
    jd = km.jd

    def sandbox():
        """A state root of the test's own, hosts off: the runner's belt covers the run root only (CLAUDE.md, Testing)."""
        root = Path(tempfile.mkdtemp())
        (root / "session-hosts").write_text("off\\n")
        return root

    def build_over(root):
        """ViewBuilder's road to the singleton: jd.STATE at a sandbox and the lazy build reached through km._sdk()."""
        jd.STATE = root
        km._sdk_backend = None
        return km._sdk()
''')

SCRATCH_A = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_lazy_first_build_under_the_run_root_passes(self):
            assert km._sdk_backend is None
            be = km._sdk()
            assert be is not None and be.state_dir == jd.STATE and jd.STATE.is_dir()
            assert not be.session_hosts_on()       # the module's root carries the off switch (CLAUDE.md, Testing)

        def test_b_a_saved_and_restored_singleton_passes(self):
            saved = (jd.STATE, km._sdk_backend)
            root = sandbox()
            assert build_over(root).state_dir == root
            jd.STATE, km._sdk_backend = saved
            shutil.rmtree(root)

        def test_c_a_kernel_reexecution_inside_the_test_is_not_judged(self):
            before = km._sdk_backend
            load_source("romp_kernel", KERNEL)
            assert km._sdk_backend is None            # the reload's module-level reset
            be = km._sdk()
            assert be is not before and be.state_dir == jd.STATE

        def test_d_a_rebuilt_singleton_over_the_same_root_fails(self):
            before = km._sdk_backend
            km._sdk_backend = None
            rebuilt = km._sdk()
            assert rebuilt is not before and rebuilt.state_dir == before.state_dir

        def test_e_the_leak_with_the_sandbox_kept_fails(self):
            saved = jd.STATE
            build_over(sandbox())
            jd.STATE = saved                          # the sandbox stands; the singleton stays over it

        def test_f_removing_the_directory_under_the_singleton_it_found_fails(self):
            be = km._sdk_backend                      # e's object, over its kept sandbox
            assert be.state_dir != jd.STATE and be.state_dir.is_dir()
            shutil.rmtree(be.state_dir)               # the same object before and after; its directory present, then gone

        def test_g_the_leak_with_the_sandbox_removed_fails(self):
            saved = jd.STATE
            root = sandbox()
            build_over(root)
            jd.STATE = saved
            shutil.rmtree(root)
            root.write_text("a regular file where the directory was\\n")   # exists, and is not a directory

        def test_h_doing_nothing_under_an_inherited_gone_singleton_passes(self):
            assert km._sdk_backend.state_dir.is_file()        # g's object; g was named for it, so this test is not

        def test_i_resetting_the_singleton_to_none_fails(self):
            km._sdk_backend = None                    # the next reader would rebuild over whatever jd.STATE is then
''')

SCRATCH_B = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_leak_as_the_first_build_fails(self):
            assert km._sdk_backend is None
            saved = jd.STATE
            root = sandbox()
            jd.STATE = root
            km._sdk()                                 # the worker's lazy first build, over the sandbox
            jd.STATE = saved
            shutil.rmtree(root)

        def test_b_a_reexecution_that_builds_over_a_removed_sandbox_fails(self):
            load_source("romp_kernel", KERNEL)
            saved = jd.STATE
            root = sandbox()
            build_over(root)
            jd.STATE = saved
            shutil.rmtree(root)

        def test_c_a_reexecution_that_builds_over_a_kept_sandbox_fails(self):
            load_source("romp_kernel", KERNEL)
            saved = jd.STATE
            build_over(sandbox())
            jd.STATE = saved                          # the sandbox stands; the singleton stays over it

        def test_d_a_reexecution_under_a_moved_environment_root_then_the_lazy_build_passes(self):
            new = Path(tempfile.mkdtemp())            # last in B: this moves the child's environment for good
            (new / "romp").mkdir()
            (new / "romp" / "session-hosts").write_text("off\\n")
            os.environ["XDG_STATE_HOME"] = str(new)
            load_source("romp_kernel", KERNEL)        # re-executes judge.py too: jd.STATE re-binds from the environment
            assert jd.STATE == new / "romp" and km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE
''')

SCRATCH_C = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_first_build_over_a_kept_sandbox_fails(self):
            assert km._sdk_backend is None
            saved = jd.STATE
            jd.STATE = sandbox()
            km._sdk()                                 # the worker's lazy first build, over a sandbox that stands
            jd.STATE = saved
''')

SCRATCH_D = SCRATCH_HEAD + textwrap.dedent('''\

    class One(unittest.TestCase):
        root = None

        @classmethod
        def tearDownClass(cls):
            shutil.rmtree(cls.root)
            cls.root.write_text("a regular file where the directory was\\n")   # exists, and is not a directory

        def test_a_builds_over_a_kept_sandbox_stored_on_the_class(self):
            saved = jd.STATE
            One.root = sandbox()
            build_over(One.root)
            jd.STATE = saved

        def test_b_does_nothing(self):
            assert km._sdk_backend.state_dir == One.root and One.root.is_dir()

    class Two(unittest.TestCase):
        def test_a_does_nothing(self):
            assert km._sdk_backend.state_dir == One.root and One.root.is_file()

        def test_b_does_nothing(self):
            pass
''')

SCRATCH_E = SCRATCH_HEAD + textwrap.dedent('''\

    _root = sandbox()                                 # import-time code, before any test: the leak no window sees made
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved
    shutil.rmtree(_root)

    class Cases(unittest.TestCase):
        def test_a_does_nothing_and_is_the_first_to_meet_the_state(self):
            pass

        def test_b_does_nothing(self):
            assert not km._sdk_backend.state_dir.exists()

        def test_c_makes_a_kept_sandbox_leak_of_its_own(self):
            saved = jd.STATE
            build_over(sandbox())
            jd.STATE = saved
''')

SCRATCH_K = SCRATCH_HEAD + textwrap.dedent('''\

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved_state = jd.STATE
            cls.root = sandbox()
            jd.STATE = cls.root                       # the class's root for every test in it

        @classmethod
        def tearDownClass(cls):
            jd.STATE = cls.saved_state                # the sandbox stands; the singleton built over it is not put back

        def test_a_the_lazy_build_over_the_class_root_passes_at_its_own_window(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == One.root

        def test_b_does_nothing(self):
            pass

    class Two(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            shutil.rmtree(cls.root)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == Two.root
''')

SCRATCH_K2 = SCRATCH_HEAD + textwrap.dedent('''\

    km._sdk()                                         # import-time: the kernel's own lazy build over the RUN root, nothing leaked
    assert km._sdk_backend.state_dir == jd.STATE
    _run_root = jd.STATE
    _module_root = None

    def setUpModule():
        global _module_root
        _module_root = sandbox()
        jd.STATE = _module_root                       # moved for the module's tests, no build; after the module's start read

    def tearDownModule():
        jd.STATE = _run_root
        shutil.rmtree(_module_root)

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.root = sandbox()
            jd.STATE = cls.root                       # moved again for the class's tests, no build (K.One's shape, put back)

        @classmethod
        def tearDownClass(cls):
            jd.STATE = _module_root
            shutil.rmtree(cls.root)

        def test_a_does_nothing_under_the_run_roots_singleton(self):
            assert km._sdk_backend.state_dir == _run_root and jd.STATE == One.root

    class Two(unittest.TestCase):
        def test_a_does_nothing_under_the_run_roots_singleton(self):
            assert km._sdk_backend.state_dir == _run_root and jd.STATE == _module_root
''')

SCRATCH_L = SCRATCH_HEAD + textwrap.dedent('''\

    _root = None

    def tearDownModule():
        shutil.rmtree(_root)

    class Cases(unittest.TestCase):
        def test_a_builds_over_a_kept_sandbox_stored_on_the_module(self):
            global _root
            saved = jd.STATE
            _root = sandbox()
            build_over(_root)
            jd.STATE = saved

        def test_b_does_nothing(self):
            assert km._sdk_backend.state_dir == _root and _root.is_dir()
''')


SCRATCH_HEAD_LAZY = SCRATCH_HEAD.replace(
    'km = load_source("romp_kernel", KERNEL)\njd = km.jd\n',
    'km = jd = None                        # no kernel at import: the worker\'s first load happens inside the test\n'
    '\n'
    'def load():\n'
    '    global km, jd\n'
    '    km = load_source("romp_kernel", KERNEL)\n'
    '    jd = km.jd\n')
assert "def load():" in SCRATCH_HEAD_LAZY and "km = jd = None" in SCRATCH_HEAD_LAZY, SCRATCH_HEAD_LAZY

SCRATCH_HEAD_SDK_STUB = SCRATCH_HEAD.replace(
    'sys.modules["claude_agent_sdk"] = None\n',
    '# the importable road: the forcing line is replaced by this comment, and the stub package is on the path\n')
assert 'sys.modules["claude_agent_sdk"]' not in SCRATCH_HEAD_SDK_STUB and SCRATCH_HEAD_SDK_STUB != SCRATCH_HEAD

SCRATCH_Q = SCRATCH_HEAD_SDK_STUB + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_lazy_first_build_on_the_importable_road(self):
            import claude_agent_sdk                                # the stub, importable in this child alone (nested_run)
            stub = os.environ["ROMP_RATCHET_SDK_STUB"]
            assert claude_agent_sdk.__file__.startswith(stub + os.sep), claude_agent_sdk.__file__
            assert km._sdk_backend is None, km._sdk_backend
            be = km._sdk()
            assert be is not None and be is not False and be.state_dir == jd.STATE, be
            assert be._sdk_missing is False, "the probe found the stub, so this build is on the importable road"
    ''')

SCRATCH_H = SCRATCH_HEAD_LAZY + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_first_load_then_a_build_over_a_kept_sandbox_fails(self):
            assert "romp_kernel" not in sys.modules
            load()
            saved = jd.STATE
            jd.STATE = sandbox()
            km._sdk()                                 # the first build of the worker, over a sandbox that stands
            jd.STATE = saved
''')

SCRATCH_H2 = SCRATCH_HEAD_LAZY + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_first_load_then_the_lazy_build_over_the_loaders_root_passes(self):
            assert "romp_kernel" not in sys.modules
            load()
            assert km._sdk().state_dir == jd.STATE
''')


SCRATCH_F = SCRATCH_HEAD + textwrap.dedent('''\
    import types

    class SdkBackend:
        """A look-alike: the kernel's class name, defined here, with a state_dir over the run root."""
        def __init__(self, root):
            self.state_dir = root

    class Cases(unittest.TestCase):
        def test_a_a_look_alike_over_jd_state_as_the_workers_first_value_fails(self):
            assert km._sdk_backend is None
            km._sdk_backend = SdkBackend(jd.STATE)

        def test_b_none_left_in_place_of_the_look_alike_fails(self):
            km._sdk_backend = None

        def test_c_the_kernels_unavailable_outcome_passes(self):
            assert km._sdk_backend is None
            saved = km._sdk_import_notice
            def unavailable():
                raise RuntimeError("the SDK will not import (scratch)")
            km._sdk_import_notice = unavailable
            try:
                assert km._sdk() is None               # _sdk_locked's except branch: the slot is False, the caller gets None
            finally:
                km._sdk_import_notice = saved
            assert km._sdk_backend is False

        def test_d_none_left_in_place_of_false_fails(self):
            assert km._sdk_backend is False
            km._sdk_backend = None

        def test_e_the_real_lazy_build_over_the_run_root_passes(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE

        def test_f_false_left_in_place_of_the_backend_fails(self):
            km._sdk_backend = False

        def test_g_a_simplenamespace_left_fails(self):
            km._sdk_backend = types.SimpleNamespace()

        def test_h_a_magicmock_left_fails(self):
            from unittest import mock
            km._sdk_backend = mock.MagicMock()        # an unstopped patch's shape: its state_dir renders to a non-directory string
''')

SCRATCH_J = SCRATCH_HEAD + textwrap.dedent('''\

    class Cases(unittest.TestCase):
        def test_a_the_first_build_over_a_sandbox_with_jd_state_left_there_fails(self):
            assert km._sdk_backend is None
            jd.STATE = sandbox()                      # LEFT here: the singleton agrees with jd.STATE as left
            assert km._sdk().state_dir == jd.STATE
''')


SCRATCH_N = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        def test_a_the_lazy_first_build(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE

    class Sandboxed(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved_state = jd.STATE
            cls.root = sandbox()
            jd.STATE = cls.root                       # moved for the tests, no build: One's singleton stays over the run root

        @classmethod
        def tearDownClass(cls):
            jd.STATE = cls.saved_state
            shutil.rmtree(cls.root)

        def test_a_does_nothing_under_a_singleton_over_the_run_root(self):
            assert km._sdk_backend is not None and km._sdk_backend.state_dir != jd.STATE

    class Two(unittest.TestCase):
        def test_a_leaves_none(self):
            km._sdk_backend = None                    # accused at its own window

        def test_b_the_lazy_rebuild_over_the_run_root_after_the_accused_reset(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE   # allowed at its own window; the class end has nothing to add

    class Three(unittest.TestCase):
        def test_a_leaves_none_as_the_last_test_of_a_class_that_started_on_a_real_backend(self):
            km._sdk_backend = None

    class Four(unittest.TestCase):
        def test_a_the_lazy_rebuild(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE

        def test_b_leaves_false_as_the_last_test(self):
            km._sdk_backend = False

    class Five(unittest.TestCase):
        def test_a_none_in_place_of_false(self):
            assert km._sdk_backend is False
            km._sdk_backend = None

        def test_b_the_lazy_rebuild(self):
            assert km._sdk().state_dir == jd.STATE

    class Six(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            km._sdk_backend = None                    # the class drops the object it found; a test then rebuilds over the same root

        def test_a_the_lazy_rebuild_the_next_module_inherits(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE
""")

SCRATCH_N2 = textwrap.dedent("""\
    import sys, unittest
    km = sys.modules["romp_kernel"]                   # the kernel the first module loaded: no re-execution here
    jd = km.jd

    class Follow(unittest.TestCase):
        def test_a_leaves_none_as_the_last_test_of_the_module(self):
            assert km._sdk_backend is not None
            km._sdk_backend = None
""")

SCRATCH_S6 = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # import-time code: a build over a sandbox that STANDS, jd.STATE restored
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved

    class Cases(unittest.TestCase):
        def test_a_is_the_first_to_meet_the_state_and_leaks_on_its_own(self):
            assert km._sdk_backend.state_dir == _root and _root.is_dir() and jd.STATE != _root
            saved = jd.STATE
            build_over(sandbox())                     # a kept-sandbox leak of its own, judged in the same teardown
            jd.STATE = saved

        def test_b_does_nothing(self):
            pass
""")

SCRATCH_S7 = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # import-time code: S6's build over a sandbox that STANDS, jd.STATE restored
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)   # K.Two's shape: save, reset, move; put both back after
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            shutil.rmtree(cls.root)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == One.root

    class Two(unittest.TestCase):
        def test_a_meets_the_import_time_object(self):
            assert km._sdk_backend.state_dir == _root and _root.is_dir() and jd.STATE != _root
""")

SCRATCH_S7B = SCRATCH_S7 + textwrap.dedent("""\

    class Three(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)   # One's shape again, after Two: a later window where the identity term fails
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            shutil.rmtree(cls.root)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == Three.root
""")

SCRATCH_S8 = SCRATCH_HEAD + textwrap.dedent("""\

    km._sdk()                                         # import-time: the kernel's own lazy build over the RUN root, nothing leaked
    assert km._sdk_backend.state_dir == jd.STATE
    _run_root = jd.STATE

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)   # S7's swapping class over a clean import-time build
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            shutil.rmtree(cls.root)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == One.root

    class Two(unittest.TestCase):
        def test_a_meets_the_run_roots_object(self):
            assert km._sdk_backend.state_dir == _run_root and jd.STATE == _run_root
""")

SCRATCH_S9 = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # E's import-time leak: built over a sandbox, jd.STATE restored, the sandbox removed
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved
    shutil.rmtree(_root)

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)   # S7's swapping class over a gone import-time object
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            shutil.rmtree(cls.root)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == One.root

    class Two(unittest.TestCase):
        def test_a_meets_the_gone_object(self):
            assert km._sdk_backend.state_dir == _root and not _root.exists()
""")

SCRATCH_S9B = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # E's import-time leak: built over a sandbox, jd.STATE restored, the sandbox removed
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved
    shutil.rmtree(_root)
    _obj = km._sdk_backend
    _moved = None

    def setUpModule():
        global _moved
        _moved = Path(tempfile.mkdtemp(prefix="moved-"))   # a second removed path: the gone object repointed there and the slot
        shutil.rmtree(_moved)                             # cleared, after the module start read, so the two lines render two paths
        _obj.state_dir = _moved
        km._sdk_backend = None

    def tearDownModule():
        _obj.state_dir = _root                        # both put back: the module's start and end reads agree, neither a directory
        km._sdk_backend = _obj

    class One(unittest.TestCase):
        def test_a_builds_over_the_run_root(self):
            assert km._sdk().state_dir == jd.STATE    # the lazy build over the run root, allowed

    class Two(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = km._sdk_backend
            km._sdk_backend = _obj                    # the gone object, repointed, put in the slot for this class's test

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend = cls.saved

        def test_a_meets_the_gone_object_repointed(self):
            assert km._sdk_backend is _obj and not _moved.exists() and not _root.exists()
""")

SCRATCH_S10 = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # E's import-time leak: built over a sandbox, jd.STATE restored, the sandbox removed
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved
    shutil.rmtree(_root)

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            km._sdk_backend = None                    # the gone object swapped out and never put back; jd.STATE untouched

        def test_a_builds_over_the_run_root(self):
            assert km._sdk().state_dir == jd.STATE

    class Two(unittest.TestCase):
        def test_a_meets_the_classes_build(self):
            assert km._sdk_backend.state_dir == jd.STATE and not _root.exists()
""")

SCRATCH_S10B = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # E's import-time leak: built over a sandbox, jd.STATE restored, the sandbox removed
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved
    shutil.rmtree(_root)
    _obj = km._sdk_backend                            # the object the worker's first window will refuse
    _moved = None

    def setUpModule():
        global _moved
        _moved = Path(tempfile.mkdtemp(prefix="moved-"))   # a second removed path: the gone object repointed there after the module
        shutil.rmtree(_moved)                             # start read and LEFT in the slot, so One's start read finds it over this path
        _obj.state_dir = _moved

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            km._sdk_backend = None                    # S10's swap: the gone object swapped out and never put back; jd.STATE untouched

        def test_a_builds_over_the_run_root(self):
            assert km._sdk().state_dir == jd.STATE

    class Two(unittest.TestCase):
        def test_a_meets_the_classes_build(self):
            be = km._sdk_backend
            assert be is not _obj and be.state_dir == jd.STATE and not _root.exists() and not _moved.exists()
""")

SCRATCH_S10C = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # E's import-time leak: built over a sandbox, jd.STATE restored, the sandbox removed
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved
    shutil.rmtree(_root)
    _obj = km._sdk_backend                            # the object the worker's first window will refuse

    def tearDownModule():
        km._sdk_backend = _obj                        # the module's start and end reads agree on the gone object: its end is quiet

    class One(unittest.TestCase):
        root = None

        @classmethod
        def setUpClass(cls):
            km._sdk_backend = None                    # S10's swap: the refused object swapped out and never put back; jd.STATE untouched

        @classmethod
        def tearDownClass(cls):
            One.root = sandbox()
            km._sdk_backend.state_dir = One.root      # the teardown repoints the build its test left (X.Two's shape): the
                                                      # verdict renders that build alone; the object the class FOUND is
                                                      # the refused one

        def test_a_builds_over_the_run_root(self):
            assert km._sdk().state_dir == jd.STATE

    class Two(unittest.TestCase):
        @classmethod
        def tearDownClass(cls):
            km._sdk_backend = None                    # M.Three's shape: the start-to-end judgment on One.a's build, an object no
                                                      # refusal named, while the refused list holds the first object

        def test_a_does_nothing_under_the_repointed_build(self):
            assert km._sdk_backend.state_dir == One.root and One.root.is_dir() and not _root.exists()
""")

SCRATCH_S11 = SCRATCH_HEAD + textwrap.dedent("""\

    _root = Path(tempfile.mkdtemp(prefix="kept-"))    # S6's import-time build over a sandbox that STANDS, jd.STATE restored; the
    (_root / "session-hosts").write_text("off\\n")    # prefix marks the root the start read records (hosts off, as sandbox() does)
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)   # S7's swapping class, the start read's object REPOINTED before the swap: the
            cls.moved = Path(tempfile.mkdtemp(prefix="repointed-"))     # live attribute shows a root the start read did not record
            km._sdk_backend.state_dir = cls.moved
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            km._sdk_backend.state_dir = _root         # the state_dir put back where the class found it, so One's boundary is quiet
            shutil.rmtree(cls.root)
            shutil.rmtree(cls.moved)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == One.root
            assert One.saved[0].state_dir == One.moved   # the live attribute shows the repointed root at this window

    class Two(unittest.TestCase):
        def test_a_meets_the_import_time_object(self):
            assert km._sdk_backend.state_dir == _root and _root.is_dir() and jd.STATE != _root
""")

SCRATCH_S12 = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # S6's import-time build over a sandbox that STANDS, jd.STATE restored
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)   # S7's swapping class, but the setup BUILDS over its root in place of resetting
            cls.root = Path(tempfile.mkdtemp(prefix="classroot-"))   # the slot: a real object of the class's own is in the slot at
            (cls.root / "session-hosts").write_text("off\\n")        # the first window (hosts off, as sandbox() does)
            build_over(cls.root)

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            shutil.rmtree(cls.root)

        def test_a_finds_the_classes_build_in_the_slot(self):
            assert km._sdk_backend.state_dir == One.root and km._sdk() is km._sdk_backend   # a cache hit: no transition

    class Two(unittest.TestCase):
        def test_a_meets_the_import_time_object(self):
            assert km._sdk_backend.state_dir == _root and _root.is_dir() and jd.STATE != _root
""")

SCRATCH_S13 = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            saved = jd.STATE
            cls.root = sandbox()
            build_over(cls.root)                      # a backend over a kept sandbox, left in the slot by the setup
            jd.STATE = saved
            raise unittest.SkipTest("this class's tests never run: no function window opens in this module")

        def test_a_never_runs(self):
            pass
""")

SCRATCH_S13_FOLLOWER = textwrap.dedent("""\
    import shutil, sys, tempfile, unittest
    from pathlib import Path
    km = sys.modules["romp_kernel"]                   # the kernel the first module loaded: no re-execution here
    jd = km.jd                                        # km._sdk_backend is not read at import: collection runs before One's setUpClass

    def sandbox():
        root = Path(tempfile.mkdtemp())
        (root / "session-hosts").write_text("off\\n")
        return root

    class Two(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)   # S7's swapping class, over the object module 1's class boundary named
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            shutil.rmtree(cls.root)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == Two.root

    class Three(unittest.TestCase):
        def test_a_meets_the_named_object(self):
            be = km._sdk_backend
            assert be is Two.saved[0] and be.state_dir.is_dir() and jd.STATE != be.state_dir
""")

SCRATCH_S14 = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # E's import-time leak: built over a sandbox, jd.STATE restored, the sandbox removed
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved
    shutil.rmtree(_root)
    _obj = km._sdk_backend                            # the object the worker's first window will refuse

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)   # S7's swapping class over the gone import-time object: refused at One.a
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            shutil.rmtree(cls.root)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == One.root

    class Two(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)   # the refused object, put back by One; a SECOND gone object of this class's own
            cls.root = sandbox()                      # making is left in the slot for its test: built over a sandbox, jd.STATE
            build_over(cls.root)                      # restored, the sandbox removed (U's completed leak, after a refusal)
            jd.STATE = cls.saved[1]
            shutil.rmtree(cls.root)

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved     # the refused object back in the slot: this class's start and end reads agree

        def test_a_meets_its_own_classes_gone_object(self):
            be = km._sdk_backend
            assert be is not _obj and be.state_dir == Two.root and not Two.root.exists() and not _root.exists()
""")

SCRATCH_S15 = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # E's import-time leak: built over a sandbox, jd.STATE restored, the sandbox removed
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved
    shutil.rmtree(_root)

    class One(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)   # S9's swapping class over the gone import-time object: refused at One.a, put back
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved
            shutil.rmtree(cls.root)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == One.root

    class Two(unittest.TestCase):
        def test_a_resets_the_slot_under_the_gone_object(self):
            assert km._sdk_backend.state_dir == _root and not _root.exists()
            km._sdk_backend = None                    # a TEST's change from the refused object: its own window renders the
                                                      # refused object as before; the module end finds the slot changed
""")

SCRATCH_S16 = SCRATCH_HEAD + textwrap.dedent("""\

    _root = sandbox()                                 # E's import-time leak: built over a sandbox, jd.STATE restored, the sandbox removed
    _saved = jd.STATE
    jd.STATE = _root
    km._sdk()
    jd.STATE = _saved
    shutil.rmtree(_root)

    class One(unittest.TestCase):
        root = None

        @classmethod
        def setUpClass(cls):
            km._sdk_backend = None                    # S10's swap: the refused object swapped out and never put back

        @classmethod
        def tearDownClass(cls):
            load_source("romp_kernel", KERNEL)        # the marker changes: the class end is judged on the reload road
            km2 = sys.modules["romp_kernel"]
            One.root = sandbox()
            saved = km2.jd.STATE
            km2.jd.STATE = One.root
            km2._sdk()                                # the re-executed kernel's build over a root that is not jd.STATE, left
            km2.jd.STATE = saved

        def test_a_builds_over_the_run_root(self):
            assert km._sdk().state_dir == jd.STATE
""")

CONFTEST_W = textwrap.dedent("""\
    import sys, tempfile
    from pathlib import Path
    import pytest

    # A session-scoped autouse fixture: it sets up before the module boundary's start read, builds the kernel's
    # singleton over a root of its own (hosts off) and restores jd.STATE, leaving the singleton over the kept root.
    @pytest.fixture(autouse=True, scope="session")
    def _installs_the_singleton_before_the_modules_reads():
        km = sys.modules["romp_kernel"]                 # the kernel the scratch module loaded at collection
        jd = km.jd
        root = Path(tempfile.mkdtemp())
        (root / "session-hosts").write_text("off\\n")
        saved = jd.STATE
        jd.STATE = root
        km._sdk_backend = None
        km._sdk()
        jd.STATE = saved
        yield
""")

SCRATCH_W = SCRATCH_HEAD + textwrap.dedent("""\

    class Cases(unittest.TestCase):
        def test_a_is_the_first_to_meet_the_fixtures_install(self):
            be = km._sdk_backend                      # the session fixture's build (conftest.py beside this module), kept
            assert be is not None and be.state_dir != jd.STATE and be.state_dir.is_dir(), be

        def test_b_does_nothing(self):
            pass
""")

SCRATCH_T = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        root = None

        @classmethod
        def setUpClass(cls):
            saved = jd.STATE
            One.root = sandbox()
            build_over(One.root)                      # the worker's first build, made by a class setup over a root that stands
            jd.STATE = saved

        def test_a_does_nothing_under_the_setups_object(self):
            be = km._sdk_backend
            assert be is not None and be.state_dir == One.root and One.root.is_dir() and jd.STATE != One.root

        def test_b_does_nothing(self):
            pass
""")

SCRATCH_Z = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        def test_a_the_lazy_first_build(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE
""")

SCRATCH_Z2 = textwrap.dedent("""\
    import shutil, sys, tempfile, unittest
    from pathlib import Path
    km = sys.modules["romp_kernel"]                   # the kernel the first module loaded: no re-execution here
    jd = km.jd

    class Moved(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved_state = jd.STATE
            cls.root = Path(tempfile.mkdtemp())
            (cls.root / "session-hosts").write_text("off\\n")
            jd.STATE = cls.root                       # moved for the tests, no build: One.a's singleton stays over the run root

        @classmethod
        def tearDownClass(cls):
            jd.STATE = cls.saved_state
            shutil.rmtree(cls.root)

        def test_a_does_nothing_under_a_singleton_over_the_run_root(self):
            assert km._sdk_backend is not None and km._sdk_backend.state_dir != jd.STATE
""")

SCRATCH_U = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        root = None

        @classmethod
        def setUpClass(cls):
            saved = jd.STATE
            One.root = sandbox()
            build_over(One.root)
            jd.STATE = saved
            shutil.rmtree(One.root)                   # the leak completed by the setup: built, jd.STATE restored, the root removed

        def test_a_meets_the_gone_object_first(self):
            assert km._sdk_backend is not None and not km._sdk_backend.state_dir.exists()

        def test_b_does_nothing(self):
            pass
""")

SCRATCH_V = SCRATCH_HEAD + textwrap.dedent("""\

    _root = None

    def setUpModule():
        global _root
        saved = jd.STATE
        _root = sandbox()
        build_over(_root)
        jd.STATE = saved
        shutil.rmtree(_root)                          # the same leak, completed by the module's setup after its start read

    class One(unittest.TestCase):
        def test_a_meets_the_gone_object_first(self):
            assert km._sdk_backend is not None and not km._sdk_backend.state_dir.exists()

        def test_b_does_nothing(self):
            pass
""")

SCRATCH_X = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        root = None

        def test_a_the_lazy_first_build(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE

        def test_b_repoints_the_singleton_it_found_at_a_kept_sandbox_and_leaves_it(self):
            One.root = sandbox()
            km._sdk_backend.state_dir = One.root      # the same object; every later registry scan reads this root

        def test_c_repoints_and_puts_the_state_dir_back(self):
            be = km._sdk_backend
            found = be.state_dir
            other = sandbox()
            be.state_dir = other
            be.state_dir = found
            shutil.rmtree(other)

    class Two(unittest.TestCase):
        root = None

        @classmethod
        def tearDownClass(cls):
            Two.root = sandbox()
            km._sdk_backend.state_dir = Two.root      # the teardown repoints the object its test left

        def test_a_does_nothing_under_the_repointed_object(self):
            assert km._sdk_backend.state_dir == One.root and One.root.is_dir()

    class Three(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved     # the object it found, put back
            cls.moved = sandbox()
            km._sdk_backend.state_dir = cls.moved     # with its state_dir repointed
            shutil.rmtree(cls.root)

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == Three.root
""")

SCRATCH_Y = SCRATCH_HEAD + textwrap.dedent("""\
    kp = load_source("romp_kernel_scratchp", KERNEL)  # the kernel under a PRIVATE name: its own _sdk_backend slot, the shared jd
    assert kp is not km and kp.jd is jd and kp._sdk_locked is not km._sdk_locked

    class Cases(unittest.TestCase):
        def test_a_leaks_the_private_kernels_singleton_over_a_removed_sandbox(self):
            saved = jd.STATE
            root = sandbox()
            jd.STATE = root
            kp._sdk_backend = None
            assert kp._sdk().state_dir == root        # the private kernel's build, over the sandbox
            jd.STATE = saved
            shutil.rmtree(root)                       # left dangling: the defect class, on a private name

        def test_b_the_leak_stands_and_the_shared_slot_is_untouched(self):
            assert kp._sdk_backend is not None and not kp._sdk_backend.state_dir.exists()
            assert km._sdk_backend is None
""")

SCRATCH_M = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        def test_a_the_lazy_first_build(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE

    class Two(unittest.TestCase):
        @classmethod
        def tearDownClass(cls):
            saved = jd.STATE
            cls.root = sandbox()
            build_over(cls.root)                      # the teardown itself builds a new singleton over a sandbox that stands
            jd.STATE = saved

        def test_a_does_nothing(self):
            pass

    class Three(unittest.TestCase):
        @classmethod
        def tearDownClass(cls):
            km._sdk_backend = None                    # a class "cleaning up": the next reader rebuilds over whatever jd.STATE is then

        def test_a_does_nothing_under_twos_object(self):
            assert km._sdk_backend.state_dir == Two.root and Two.root.is_dir()

    class Four(unittest.TestCase):
        def test_a_does_nothing_under_none(self):
            assert km._sdk_backend is None

    class Five(unittest.TestCase):
        @classmethod
        def tearDownClass(cls):
            saved = jd.STATE
            cls.root = sandbox()
            build_over(cls.root)                      # None at the start, a singleton over a sandbox at the end
            jd.STATE = saved

        def test_a_does_nothing_under_none(self):
            assert km._sdk_backend is None

    class Six(unittest.TestCase):
        def test_a_does_nothing_under_fives_object(self):
            assert km._sdk_backend.state_dir == Five.root
""")

SCRATCH_P = SCRATCH_HEAD + textwrap.dedent("""\

    class One(unittest.TestCase):
        root = None

        def test_a_leaks_over_a_kept_sandbox(self):
            saved = jd.STATE
            One.root = sandbox()
            build_over(One.root)                      # named at its own window
            jd.STATE = saved

    class Two(unittest.TestCase):
        @classmethod
        def setUpClass(cls):
            cls.saved = (km._sdk_backend, jd.STATE)
            cls.root = sandbox()
            km._sdk_backend = None
            jd.STATE = cls.root

        @classmethod
        def tearDownClass(cls):
            km._sdk_backend, jd.STATE = cls.saved     # the object it found, put back
            shutil.rmtree(cls.root)
            shutil.rmtree(One.root)                   # and the directory under it removed

        def test_a_builds_over_the_class_root(self):
            assert km._sdk().state_dir == Two.root

    class Three(unittest.TestCase):
        def test_a_does_nothing_under_the_gone_object(self):
            assert not km._sdk_backend.state_dir.exists()
""")

SCRATCH_G = SCRATCH_HEAD + textwrap.dedent("""\
    import types

    class Fake:
        __module__ = "romp_sdk_backend"               # the kernel's module name claimed by a class defined here
        def __init__(self, root):
            self.state_dir = root

    class Cases(unittest.TestCase):
        def test_a_a_look_alike_claiming_the_kernels_module_as_the_workers_first_value_fails(self):
            assert km._sdk_backend is None
            km._sdk_backend = Fake(jd.STATE)

        def test_b_a_reexecution_then_a_simplenamespace_left_fails(self):
            load_source("romp_kernel", KERNEL)
            assert km._sdk_backend is None            # the reload's module-level reset
            km._sdk_backend = types.SimpleNamespace(state_dir=jd.STATE)
""")

SCRATCH_R1 = SCRATCH_HEAD + textwrap.dedent("""\

    class Cases(unittest.TestCase):
        def test_a_the_first_build_then_the_run_root_removed_fails(self):
            assert km._sdk_backend is None
            assert km._sdk().state_dir == jd.STATE
            shutil.rmtree(jd.STATE)                   # the singleton is over the reference root, which is now gone
""")

SCRATCH_R2 = SCRATCH_HEAD + textwrap.dedent("""\

    class Cases(unittest.TestCase):
        def test_a_a_reexecution_the_lazy_build_then_the_run_root_removed_fails(self):
            load_source("romp_kernel", KERNEL)        # the judge re-binds and creates jd.STATE
            assert km._sdk().state_dir == jd.STATE
            shutil.rmtree(jd.STATE)
""")


def nested_run(text, follower=None, sdk_stub=False, conftest=None):
    """pytest in a child over one scratch module written to a fresh directory, under this checkout's conftest
    (loaded as a plugin: the module sits outside tests/, so tests/conftest.py is not discovered there; the case
    directory's own conftest.py is, when `conftest` gives its text, the road W's session-scoped fixture takes),
    verbose and with the all-outcomes summary, so the outer test reads each case's outcome and the ratchet's text.
    The child's environment is the precedent's (tests/test_tempdir_hygiene.py, RunLeavesNothing): a fresh TMPDIR,
    the parent's pytest variables dropped so the child records its own run, and the bin directory the scratch
    module loads the kernel from. `follower` is the text of a second module written beside the first. Returns
    (returncode, stdout and stderr).

    The child runs -vv, not -v, so its output has one shape on a box and on CI: pytest's short summary (-rA) repeats
    each error's message, whole when CI is set in the environment (pytest's running_on_ci) or at -vv, and trimmed to
    the terminal width otherwise (_get_line_with_reprcrash_message). running_on_ci is true when CI or BUILD_NUMBER is
    non-empty (compat.py) and is read at three sites in pytest 9.1.1: that short-summary message, whole or trimmed
    (terminal.py); assertion truncation (assertion/truncate.py); and the sequence-compare helper
    (assertion/_compare_sequence.py). Each is gated on verbosity so that at -vv none of the three varies with the
    environment (the message is whole at verbose >= 2, truncation happens only at verbose < 2, and the helper's CI
    branch runs only at verbose <= 0), which is why -vv stays and lowering the child's verbosity is unsafe: at -v two
    of the three vary. At -v a box saw every verdict once, in the ERRORS section, and CI saw each twice, so a count of occurrences over the
    output read 1 here and 2 there for the same one boundary verdict (CI red at the round-3 preparation head); the
    outer tests read the verdicts by the scope or test they name (boundary_scopes, boundary, verdict), never by
    occurrence, and that is the protection; -vv is not one. It only makes a box run print what CI prints so the two
    outputs compare by eye, and it is coupled to pytest's current behaviour; the structured reads hold whatever the
    summary prints, and none of them is redundant with -vv.

    The child's colour is switched off at this boundary, on both sides: PY_COLORS, FORCE_COLOR and CLICOLOR_FORCE are
    popped from its environment beside the pytest variables, and --color=no is on its argv. pytest 9.1.1's
    should_do_markup reads PY_COLORS and FORCE_COLOR (and NO_COLOR, left alone here: it only disables) before any
    isatty check, so a child under a parent that exported either printed ANSI markup into its rule and PASSED lines,
    and 74 of this module's 100 tests at the round-3 head went red with messages naming nothing about colour
    (2026-09-19); CLICOLOR_FORCE is popped as the third forcing convention although pytest 9.1.1 does not read it.
    --color=no outranks every one of them (create_terminal_writer sets hasmarkup False after should_do_markup), so the
    pop and the flag are belt for each other and the pin (AChildStartedUnderAColourForcingEnvironment) reds only when
    both go. Two readers parse plain text, outcomes over the per-phase lines and SUMMARY_LINE through summary_mismatch,
    and this is their protection; the body-text readers were never coloured, since pytest marks up no message text.

    `sdk_stub` puts a stub claude_agent_sdk package, one docstring-only __init__.py written under the fresh directory,
    on the child's PYTHONPATH and names its directory in ROMP_RATCHET_SDK_STUB, so the child alone imports it: the
    importable road for SdkBackend's construction probe (Q). Every other run's head forces the missing road."""
    fresh = tempfile.mkdtemp()
    case = os.path.join(fresh, "case")
    os.makedirs(case)
    path = os.path.join(case, "test_scratch.py")
    with open(path, "w") as f:
        f.write(text)
    if follower is not None:                # a second module, collected after the first (pytest keeps the directory order)
        with open(os.path.join(case, "test_scratch2.py"), "w") as f:
            f.write(follower)
    if conftest is not None:                # the case directory's own conftest.py, discovered for both modules
        with open(os.path.join(case, "conftest.py"), "w") as f:
            f.write(conftest)
    env = dict(os.environ, TMPDIR=fresh, PYTHONDONTWRITEBYTECODE="1", ROMP_RATCHET_BIN=BIN)
    if sdk_stub:
        stub = os.path.join(fresh, "sdkstub")
        os.makedirs(os.path.join(stub, "claude_agent_sdk"))
        with open(os.path.join(stub, "claude_agent_sdk", "__init__.py"), "w") as f:
            f.write('"""A stub for the kernel\'s import probe (find_spec at SdkBackend construction); no session runs here."""\n')
        env["PYTHONPATH"] = stub + ((os.pathsep + env["PYTHONPATH"]) if env.get("PYTHONPATH") else "")
        env["ROMP_RATCHET_SDK_STUB"] = stub
    for var in ("PYTEST_ADDOPTS", "PYTEST_PLUGINS", "PYTEST_DISABLE_PLUGIN_AUTOLOAD", "PYTEST_CURRENT_TEST",
                "PYTEST_XDIST_WORKER", "PYTEST_XDIST_WORKER_COUNT", "ROMP_TESTS_SYSTEM_TMPDIR",
                "PY_COLORS", "FORCE_COLOR", "CLICOLOR_FORCE"):     # the colour-forcing variables: two readers parse plain text
        env.pop(var, None)
    r = subprocess.run([sys.executable, "-m", "pytest", "-p", "tests.conftest", "-p", "no:cacheprovider",
                        "-vv", "-rA", "--tb=short", "--color=no", case],
                       cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr


def outcomes(out):
    """{"<Class>.<method>": set of the phase outcomes pytest printed for it} from the verbose lines: a case the
    ratchet fails at its teardown shows PASSED for its call and ERROR for its teardown; one it reports at setup
    shows ERROR alone."""
    seen = {}
    for cls, m, o in re.findall(r"test_scratch2?\.py::(\w+)::(test_\w+) (PASSED|FAILED|ERROR)\b", out):
        seen.setdefault("%s.%s" % (cls, m), set()).add(o)
    return seen


SUMMARY_LINE = re.compile(r"^=+ (.*? in [\d.]+s(?: \([\d:]+\))?) =+$", re.M)


def summary_mismatch(out, errors):
    """None when the nested run's summary line counts `errors` errors, else a sentence naming the count expected and
    the summary line found. The line is pytest's last ("6 passed, 3 errors in 0.19s"), read tolerant of any other
    comma-separated count between passed and errors (a warning, a skip, an xfail: "6 passed, 1 warning, 3 errors in")
    and strict about the count: every skipped segment ends in a comma, and the count follows a space, so "13 errors"
    does not stand for 3. With `errors` 0 the line carries no errors segment at all, other counts allowed. The count
    is read on the summary line alone because SUMMARY_LINE selects that line (re.M without re.S, so its capture holds
    no newline); the segment class's newline exclusion ([^,\n]) and the [ ,] tail after the count are defence in
    depth over a value already reduced to one line, and no test can red on the exclusion alone. At the round-3 head
    the test named for the property credited the class; it pins SUMMARY_LINE's line selection
    (NestedSummaryMatcher.test_the_count_is_read_on_the_summary_line_alone). The first form asked for "N passed, M
    errors in" and "N passed in" exactly, so one unrelated warning in the child (an unpinned pytest's deprecation, a
    conftest filterwarnings entry pytest drops with a config warning)
    turned "6 passed, 3 errors in" into "6 passed, 1 warning, 3 errors in" and redded every run with a message that
    named no warning (round 1, 2026-09-19).

    THE COUNT'S LIMIT: pytest counts one error per item whose setup or teardown failed, and a boundary verdict lands
    on the teardown of the scope's last test. So a boundary failure on an item whose own teardown also fails folds
    into that item's one teardown report, an exception group, so pytest's error count cannot see that case and the
    boundary text is the signal: a run whose count matches can still hide a boundary verdict on a scope whose last
    test failed on its own, and every run therefore reads boundary() for the ends it expects quiet or accused, and
    ERRORS below is the count of items, never of verdicts. B and C are the shape (the one or last case fails on its
    own, and the class and module ends are read as text); J, R1 and R2 read the exception group by name."""
    m = SUMMARY_LINE.search(out)
    if m is None:
        return "no pytest summary line (\"N passed, M errors in Ns\") in the nested run's output; %d errors expected" % errors
    line = m.group(1)
    if errors == 0:
        ok = re.search(r"\d+ passed(?:, \d+ (?!errors?\b)[a-z]+)* in ", line)
    else:
        ok = re.search(r"\d+ passed,(?:[^,\n]+,)* %d errors?[ ,]" % errors, line)
    if ok:
        return None
    found = re.search(r"(\d+) errors?\b", line)
    if found is not None and int(found.group(1)) == errors:
        return "the nested run's summary line counts %d error%s but does not read 'N passed, other counts, %d error%s in': %r" % (
            errors, "" if errors == 1 else "s", errors, "" if errors == 1 else "s", line)
    return "the nested run's summary line counts %s, not %d error%s: %r" % (
        found.group(0) if found else "no errors", errors, "" if errors == 1 else "s", line)


def _split(m):
    """(clause, remedy) from a matched "<who> <clause>. Fix: <remedy>" message, the clause with the ratchet's
    common head stripped so the tests read the part that names the transition."""
    clause, remedy = m.group(1), m.group(2)
    if clause.startswith(RATCHET + " "):
        clause = clause[len(RATCHET) + 1:]
    return clause, remedy


def verdict(out, cls, method):
    """The ratchet's own-leak verdict on `cls.method` as (clause, remedy), from the message that starts with the
    case's nodeid; None when the ratchet said nothing about it as a test."""
    m = re.search(r"::%s::%s ((?:left|re-executed)[^\n]*?)\. Fix: ([^\n]*)" % (re.escape(cls), re.escape(method)), out)
    return _split(m) if m else None


def inherited(out, cls, method, head=INHERITED):
    """The text of the inherited report on `cls.method` (the object named, and the sentence saying this test did not
    make it), or None; `head` picks the gone wording (the default) or the kept-root one (INHERITED_KEPT)."""
    m = re.search(r"::%s::%s %s: ([^\n]*)" % (re.escape(cls), re.escape(method), re.escape(head)), out)
    return m.group(1) if m else None


def boundary(out, scope, module="test_scratch.py"):
    """The boundary verdict for `scope` ("::One" for a class, "" for the module) as (clause, remedy), or None."""
    m = re.search(r"%s%s%s ([^\n]*?)\. Fix: ([^\n]*)" % (re.escape(module), re.escape(scope), re.escape(BOUNDARY)), out)
    return _split(m) if m else None


def carriers(out, head):
    """The tests whose report opens with `head`, as a set of "test_scratch.py::<Class>::<method>": the count of such
    reports is the size of this set, never the count of the text's occurrences, which the short summary repeats
    (nested_run). "Exactly one refusal" is a set of size one."""
    return set(re.findall(r"(test_scratch2?\.py::\w+::test_\w+) %s: " % re.escape(head), out))


def boundary_scopes(out):
    """The scopes the run's boundary verdicts name, as a set ("test_scratch.py::Six" for a class end, "test_scratch2.py"
    for a module end): the count of verdicts is the size of this set, never the count of the boundary text's
    occurrences, which the short summary repeats (nested_run)."""
    return set(re.findall(r"(test_scratch2?\.py(?:::\w+)?)%s " % re.escape(BOUNDARY), out))


class _NestedRun:
    """The shared half of a scratch run's tests; a mixin, so the runner collects only the runs below."""
    SCRATCH = ""
    FOLLOWER = None        # a second module's text, collected after the first, for the runs that need a module pair
    ERRORS = 0             # pytest's error count for the run: one per item whose teardown failed, whatever folded into that
                           # item's report; a boundary verdict on a last test that fails on its own is not a second count
                           # (summary_mismatch, THE COUNT'S LIMIT), so the runs read the boundary text beside the count
    JUDGE_RED = False      # whether the judge fixture (_shared_state_restored) is expected to fail in the run too
    SDK_STUB = False       # the importable road: a stub claude_agent_sdk the child alone can import (nested_run); Q only
    CONFTEST = None        # the text of a conftest.py written in the case directory (nested_run); W only

    @classmethod
    def setUpClass(cls):
        cls.rc, cls.out = nested_run(cls.SCRATCH, cls.FOLLOWER, sdk_stub=cls.SDK_STUB, conftest=cls.CONFTEST)

    def assertRatchetPassed(self, cls, method):
        self.assertEqual(outcomes(self.out).get("%s.%s" % (cls, method)), {"PASSED"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), self.out)
        self.assertIsNone(inherited(self.out, cls, method), self.out)

    def assertRatchetFailed(self, cls, method, remedy=REMEDY_A):
        got = outcomes(self.out).get("%s.%s" % (cls, method), set())
        self.assertIn("PASSED", got, "the case's own asserts held; the ratchet is the only red: %s" % self.out)
        self.assertIn("ERROR", got, "the ratchet fails the case at its teardown: %s" % self.out)
        self.assertNotIn("FAILED", got, self.out)
        found = verdict(self.out, cls, method)
        self.assertIsNotNone(found, "the ratchet's message names the case's nodeid: %s" % self.out)
        clause, fix = found
        self.assertIn(remedy, fix, self.out)
        if remedy == REMEDY_A:
            self.assertIn(SANDBOX, fix, fix)
        return clause

    def assertObjectRoad(self, cls, method):
        """The case fails with the object road's remedy and no sandbox sentence: no sandbox was involved."""
        clause = self.assertRatchetFailed(cls, method, remedy=REMEDY_B)
        _, fix = verdict(self.out, cls, method)
        self.assertNotIn(SANDBOX, fix, "the sandbox sentence is the other road's: %s" % fix)
        self.assertNotIn(REMEDY_A, fix, fix)
        return clause

    def assertInherited(self, cls, method, head=INHERITED, own=False):
        """The inherited report lands on `cls.method` after its teardown, the body having run (PASSED, then ERROR); with
        `own`, the test's own verdict is expected beside it, else none."""
        self.assertEqual(outcomes(self.out).get("%s.%s" % (cls, method)), {"PASSED", "ERROR"},
                         "the body runs, and the report is the teardown's: %s" % self.out)
        text = inherited(self.out, cls, method, head)
        self.assertIsNotNone(text, self.out)
        if own:
            self.assertIsNotNone(verdict(self.out, cls, method), "the test's own verdict is judged too: %s" % self.out)
        else:
            self.assertIsNone(verdict(self.out, cls, method), "no own-leak verdict on the inheriting test: %s" % self.out)
        self.assertNotIn("Fix:", text, "no remedy is addressed to the test that inherited: %s" % text)
        self.assertIn("This test did not make it", text)
        return text

    def assertBoundaryFailed(self, scope, last, remedy=REMEDY_A):
        """The scope's boundary verdict, the error landing on `last` ("<Class>.<method>", the scope's last test)."""
        self.assertEqual(outcomes(self.out).get(last), {"PASSED", "ERROR"}, self.out)
        cls, method = last.split(".")
        self.assertIsNone(verdict(self.out, cls, method), "the last test is not accused as a test: %s" % self.out)
        found = boundary(self.out, scope)
        self.assertIsNotNone(found, "the boundary verdict names the scope %r: %s" % (scope, self.out))
        clause, fix = found
        self.assertIn(remedy, fix, self.out)
        return clause

    def test_the_judge_fixture_is_quiet_and_the_run_reds_only_on_the_ratchet(self):
        if not self.JUDGE_RED:
            self.assertNotIn(SHARED_STATE, self.out, "every case puts jd.STATE back; the ratchet's text is the only red")
        if self.ERRORS == 0:
            self.assertEqual(self.rc, 0, self.out)
        else:
            self.assertNotEqual(self.rc, 0, self.out)
        problem = summary_mismatch(self.out, self.ERRORS)
        if problem is not None:
            self.fail("%s\n%s" % (problem, self.out))


class LeakAfterFirstBuild(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_A
    ERRORS = 5

    def test_the_run_takes_the_missing_road_wherever_it_runs(self):
        # SCRATCH_HEAD forces the road (None in sys.modules for the name), so both notices are in the output on a box
        # that installed the SDK too; Q is the importable road, with neither (LazyFirstBuildOnTheImportableRoad).
        self.assertIn(SDK_NOT_FOUND, self.out, "the boot log's not-found line is the missing road's: %s" % self.out)
        self.assertIn(SDK_NOT_IMPORTABLE, self.out, "the construction notice is the missing road's: %s" % self.out)

    def test_the_lazy_first_build_under_the_run_root_passes(self):
        self.assertRatchetPassed("Cases", "test_a_the_lazy_first_build_under_the_run_root_passes")

    def test_a_saved_and_restored_singleton_passes(self):
        self.assertRatchetPassed("Cases", "test_b_a_saved_and_restored_singleton_passes")

    def test_a_kernel_reexecution_inside_the_test_is_not_judged(self):
        self.assertRatchetPassed("Cases", "test_c_a_kernel_reexecution_inside_the_test_is_not_judged")

    def test_a_rebuilt_singleton_over_the_same_root_is_a_change(self):
        text = self.assertObjectRoad("Cases", "test_d_a_rebuilt_singleton_over_the_same_root_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + REBUILT), "identity, not the path, is the check, and the text says so: %s" % text)
        self.assertNotIn(GONE, text)

    def test_the_leak_with_the_sandbox_kept_names_the_change_and_no_gone_directory(self):
        text = self.assertRatchetFailed("Cases", "test_e_the_leak_with_the_sandbox_kept_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_removing_the_directory_under_the_singleton_it_found_is_this_tests_own_transition(self):
        text = self.assertRatchetFailed("Cases", "test_f_removing_the_directory_under_the_singleton_it_found_fails")
        self.assertTrue(text.startswith("over a directory it removed: SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)
        self.assertNotIn("changed", text)

    def test_the_leak_with_the_sandbox_removed_names_the_change_the_gone_directory_and_the_remedy(self):
        text = self.assertRatchetFailed("Cases", "test_g_the_leak_with_the_sandbox_removed_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), "a regular file at the path is not a directory: %s" % text)
        self.assertIsNone(inherited(self.out, "Cases", "test_g_the_leak_with_the_sandbox_removed_fails"),
                          "g starts under f's gone object, already named: no inherited report")

    def test_doing_nothing_under_an_inherited_gone_singleton_passes(self):
        self.assertRatchetPassed("Cases", "test_h_doing_nothing_under_an_inherited_gone_singleton_passes")

    def test_a_none_left_in_place_of_the_backend_is_the_object_road(self):
        text = self.assertObjectRoad("Cases", "test_i_resetting_the_singleton_to_none_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", after None (not built)"), text)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class LeakAsFirstBuild(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_B
    ERRORS = 3

    def test_the_leak_as_the_first_build_is_outside_the_allowance(self):
        text = self.assertRatchetFailed("Cases", "test_a_the_leak_as_the_first_build_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)

    def test_a_reexecution_that_builds_over_a_removed_sandbox_is_named_with_the_gone_clause(self):
        text = self.assertRatchetFailed("Cases", "test_b_a_reexecution_that_builds_over_a_removed_sandbox_fails")
        self.assertTrue(text.startswith(REEXEC + " over a root that is not jd.STATE: SdkBackend over "), text)
        self.assertIn(", jd.STATE ", text)
        self.assertTrue(text.endswith(", " + GONE), text)
        self.assertNotIn("changed", text)

    def test_a_reexecution_that_builds_over_a_kept_sandbox_is_named_by_what_it_left(self):
        text = self.assertRatchetFailed("Cases", "test_c_a_reexecution_that_builds_over_a_kept_sandbox_fails")
        self.assertTrue(text.startswith(REEXEC + " over a root that is not jd.STATE: SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_a_reexecution_under_a_moved_environment_root_then_the_lazy_build_passes(self):
        self.assertRatchetPassed("Cases", "test_d_a_reexecution_under_a_moved_environment_root_then_the_lazy_build_passes")

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        # The last case fails on its own at teardown, and a boundary failure on the same item would fold into that one
        # teardown report (one exception group, one counted error), so the count cannot see it: read the text.
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class FirstBuildOverAKeptSandbox(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_C
    ERRORS = 1

    def test_the_first_build_over_a_kept_sandbox_is_outside_the_allowance(self):
        text = self.assertRatchetFailed("Cases", "test_a_the_first_build_over_a_kept_sandbox_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)     # the one case is the last: the count cannot see a
        self.assertIsNone(boundary(self.out, ""), self.out)            # boundary verdict here (summary_mismatch's limit)


SCRATCH_C_WARNED = SCRATCH_C.replace(
    "import os, shutil, sys, tempfile, unittest\n",
    "import os, shutil, sys, tempfile, unittest, warnings\n"
    "warnings.warn(\"a module-level warning, counted on the child's summary line (scratch)\", DeprecationWarning)\n", 1)
assert SCRATCH_C_WARNED != SCRATCH_C, SCRATCH_C


class ASummaryWithAWarningSegment(FirstBuildOverAKeptSandbox):
    """C's run with a module-level DeprecationWarning planted in the scratch: the child's summary line gains a
    warnings segment between passed and errors, the outcomes and the ratchet's text are C's (every test of C runs
    again here over the warned output), and the summary matcher reads the error count past the warning. The first
    form's regex went red on this output with a message that named no warning. The run pins the segment's presence
    and position and a count of at least one, never the count itself: an exact "1 warning" here would put back, on
    this one run, the strict shape the widened matcher removed."""
    SCRATCH = SCRATCH_C_WARNED

    def test_the_summary_line_carries_the_warning_segment_between_passed_and_errors(self):
        m = SUMMARY_LINE.search(self.out)
        self.assertIsNotNone(m, self.out)
        seg = re.match(r"^\d+ passed, (\d+) warnings?, 1 error in ", m.group(1))
        self.assertIsNotNone(seg, "a warnings segment sits between passed and errors on the line: %s" % m.group(1))
        self.assertGreaterEqual(int(seg.group(1)), 1, "the warning is counted on the line: %s" % m.group(1))
        self.assertIsNone(summary_mismatch(self.out, 1), self.out)
        self.assertIn("DeprecationWarning", self.out, "the warnings summary names it: %s" % self.out)


class AChildStartedUnderAColourForcingEnvironment(FirstBuildOverAKeptSandbox):
    """C's run with the parent exporting PY_COLORS=1 and FORCE_COLOR=1 for the child's start (mock.patch.dict over
    os.environ around nested_run, restored after): every test of C runs again here over that child's output, each a
    positive structured read (outcomes, the verdict, the summary line through summary_mismatch) that misread ANSI
    markup before nested_run popped the colour variables and passed --color=no (74 of the module's 100 tests red at
    the round-3 head with PY_COLORS=1 exported), and the absence read below is the belt. The pin reds only when both
    the pop and --color=no go: each alone keeps the child plain (--color=no outranks the variables, and the pop
    starves --color=no's case)."""

    @classmethod
    def setUpClass(cls):
        with mock.patch.dict(os.environ, {"PY_COLORS": "1", "FORCE_COLOR": "1"}):
            cls.rc, cls.out = nested_run(cls.SCRATCH, cls.FOLLOWER, sdk_stub=cls.SDK_STUB, conftest=cls.CONFTEST)

    def test_the_childs_output_carries_no_escape_sequence(self):
        self.assertNotIn("\x1b[", self.out, "the child prints plain text under a colour-forcing parent: %s" % self.out)


class LazyFirstBuildOnTheImportableRoad(_NestedRun, unittest.TestCase):
    """Q: the worker's lazy first build with claude_agent_sdk importable, a stub package on the child's PYTHONPATH
    (nested_run's sdk_stub) over the head without the forcing line, the other road from every other run's forced
    missing one. SdkBackend constructs on both: the probe at construction (find_spec) sets _sdk_missing and, on the
    missing road, prints the not-found notices, so the transition the ratchet judges (None before, the kernel's class
    over jd.STATE after) is the same on both roads and passes here too. The case asserts the road inside the child (the
    stub is what imported, _sdk_missing is False) and the outer test reads the notices' absence beside the pass."""
    SCRATCH = SCRATCH_Q
    SDK_STUB = True
    ERRORS = 0

    def test_the_lazy_first_build_passes_on_the_importable_road(self):
        self.assertRatchetPassed("Cases", "test_a_the_lazy_first_build_on_the_importable_road")
        self.assertEqual(self.rc, 0, self.out)

    def test_the_child_took_the_importable_road(self):
        self.assertNotIn(SDK_NOT_FOUND, self.out, "the boot log's not-found line is the missing road's: %s" % self.out)
        self.assertNotIn(SDK_NOT_IMPORTABLE, self.out, "the construction notice is the missing road's: %s" % self.out)


class APrivateNameKernelsLeakIsOutsideTheFixture(_NestedRun, unittest.TestCase):
    """Y, the stated limit pinned as behaviour: the scratch loads the kernel a second time under a private name (its own
    _sdk_backend slot, the shared jd), a builds that kernel's singleton over a sandbox and removes the sandbox, and b
    asserts inside the child that the leak stands (the private slot's state_dir no longer exists) and the shared slot
    is untouched (None): this fixture's own defect class, on a private name. The ratchet reads the shared name alone,
    so it says nothing and the run exits 0. The limit is worded in the conftest comment and the module docstring
    (TheStatedLimitIsWorded, with the blocker and the order: the private-kernel harnesses' save-and-restore first, then
    the arm) and pinned here as what the fixture does: red the day the private-kernel arm lands. The control is the
    same leak under the shared name, B.a, which is named."""
    SCRATCH = SCRATCH_Y
    ERRORS = 0

    def test_the_run_exits_zero_and_the_ratchet_says_nothing(self):
        self.assertEqual(self.rc, 0, self.out)
        for method in ("test_a_leaks_the_private_kernels_singleton_over_a_removed_sandbox",
                       "test_b_the_leak_stands_and_the_shared_slot_is_untouched"):
            self.assertRatchetPassed("Cases", method)
            self.assertIsNone(inherited(self.out, "Cases", method, head=INHERITED_KEPT), self.out)
        self.assertNotIn(RATCHET, self.out, "the private kernel's slot is outside the fixture: %s" % self.out)
        self.assertNotIn(REEXEC, self.out, self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class NestedSummaryMatcher(unittest.TestCase):
    """summary_mismatch over fabricated summary lines: the shapes the nested runs print today, the ones a warning or a
    skip in the child adds a segment to, and the wrong counts it must still refuse, naming the count."""

    def test_the_error_count_is_read_past_other_counts(self):
        for line, errors in (("6 passed, 3 errors in 0.19s", 3),
                             ("6 passed, 1 warning, 3 errors in 0.19s", 3),
                             ("6 passed, 2 skipped, 9 warnings, 3 errors in 0.19s", 3),
                             ("2 passed, 1 error in 0.19s", 1),
                             ("1 failed, 2 passed, 1 warning, 1 error in 65.20s (0:01:05)", 1)):
            self.assertIsNone(summary_mismatch("=========== %s ===========\n" % line, errors), line)

    def test_zero_errors_tolerates_other_counts_and_refuses_an_errors_segment(self):
        for line in ("6 passed in 0.19s", "6 passed, 1 warning in 0.19s", "6 passed, 2 skipped, 1 warning in 0.19s"):
            self.assertIsNone(summary_mismatch("=== %s ===\n" % line, 0), line)
        for line in ("6 passed, 3 errors in 0.19s", "6 passed, 1 warning, 1 error in 0.19s"):
            problem = summary_mismatch("=== %s ===\n" % line, 0)
            self.assertIsNotNone(problem, line)
            self.assertIn("not 0 errors", problem)

    def test_a_wrong_count_is_refused_and_the_message_names_both_counts_and_the_line(self):
        problem = summary_mismatch("=== 6 passed, 1 warning, 3 errors in 0.19s ===\n", 2)
        self.assertIsNotNone(problem)
        self.assertIn("counts 3 errors, not 2 errors", problem)
        self.assertIn("'6 passed, 1 warning, 3 errors in 0.19s'", problem)
        self.assertIsNotNone(summary_mismatch("=== 6 passed, 13 errors in 0.19s ===\n", 3), "13 errors do not stand for 3")
        self.assertIsNotNone(summary_mismatch("=== 6 passed, 3 errors in 0.19s ===\n", 1))

    def test_a_count_that_agrees_on_a_line_of_another_shape_is_named_as_the_shape(self):
        problem = summary_mismatch("=== 3 errors in 0.19s ===\n", 3)      # no passed segment: pytest prints no "0 passed"
        self.assertIsNotNone(problem)
        self.assertIn("counts 3 errors but does not read 'N passed, other counts, 3 errors in'", problem)

    def test_the_count_is_read_on_the_summary_line_alone(self):
        """SUMMARY_LINE's line selection, not the segment class, keeps the count on the summary line: the class's
        newline exclusion is unreachable over the one-line capture (at the round-3 head this test's name credited the
        class). Three fabricated outputs: a count on a later line is not read (reds only when the segment search is
        repointed from the matched line to the whole output AND the class is widened to [^,]; neither alone); a later
        line carrying a passed-and-errors shape of its own is not read (reds under the repoint alone, with either
        class); a rule split across two lines is no summary line (reds when SUMMARY_LINE gains re.S: its capture then
        holds the newline)."""
        out = "=== 6 passed, 3 errors in 0.19s ===\nanother line, with a comma, 2 errors named here\n"
        self.assertIsNotNone(summary_mismatch(out, 2), "the count is read on the summary line alone")
        self.assertIsNone(summary_mismatch(out, 3))
        out = "=== 6 passed, 3 errors in 0.19s ===\n2 passed, 1 error in 0.01s\n"
        self.assertIsNotNone(summary_mismatch(out, 1), "a later line's own passed-and-errors shape is not the summary line")
        self.assertIsNone(summary_mismatch(out, 3))
        out = "=== 6 passed,\n3 errors in 0.19s ===\n"
        self.assertIsNone(SUMMARY_LINE.search(out), "a rule split across two lines is no summary line")
        self.assertIn("no pytest summary line", summary_mismatch(out, 3))

    def test_no_summary_line_is_refused_with_the_count_expected(self):
        for out in ("", "collected 0 items\n", "6 passed, 3 errors in 0.19s\n"):     # the last lacks pytest's rule of equals signs
            problem = summary_mismatch(out, 3)
            self.assertIsNotNone(problem, repr(out))
            self.assertIn("no pytest summary line", problem)
            self.assertIn("3 errors expected", problem)


LIMIT_UNPROTECTED = ("a private-name kernel's dangling backend over a removed directory that a sibling file reads and gets the "
                     "silent empty-registry answer this fixture exists to stop")
LIMIT_BLOCKER = "the loop cannot land here because the private-kernel harnesses carry 90 or more pre-existing teardown leaks"
LIMIT_ORDER = "so their save-and-restore product code lands first, then the ratchet's private-kernel arm"
LIMIT_READERS = ("two of the three", "tests/test_kernel_interrupt_machine_cut.py", "tests/test_kernel_msgcaption.py")


def conftest_comment_text():
    """tests/conftest.py's comment lines, the hash stripped, joined by one space with whitespace collapsed, so a needle
    reads across the wrapped lines of a paragraph."""
    lines = []
    with open(os.path.join(HERE, "conftest.py")) as f:
        for line in f:
            s = line.strip()
            if s.startswith("#"):
                lines.append(s[1:].strip())
    return re.sub(r"\s+", " ", " ".join(lines))


LIMIT_COUNT = ("a boundary failure on an item whose own teardown also fails folds into that item's one teardown report, an "
               "exception group, so pytest's error count cannot see that case and the boundary text is the signal")


class TheCountLimitIsStatedBesideTheCount(unittest.TestCase):
    """The limit of pytest's error count is stated where a reader of the count meets it: in summary_mismatch's docstring,
    the matcher every run's count goes through, and beside ERRORS in the runs' shared half, which points at it."""

    def test_the_matchers_docstring_states_the_limit(self):
        self.assertIn(LIMIT_COUNT, re.sub(r"\s+", " ", summary_mismatch.__doc__))

    def test_the_error_count_attribute_points_at_the_limit(self):
        src = inspect.getsource(_NestedRun)
        m = re.search(r"^    ERRORS = 0 +#(.*(?:\n {27}#.*)*)", src, re.M)
        self.assertIsNotNone(m, "ERRORS carries a comment: %s" % src)
        note = re.sub(r"\s+", " ", m.group(1))
        self.assertIn("summary_mismatch", note)
        self.assertIn("THE COUNT'S LIMIT", note)
        self.assertIn("boundary", note)


class TheStatedLimitIsWorded(unittest.TestCase):
    """The stated limit (a private kernel's own dangling singleton is outside the fixture) is worded, in the conftest
    comment and in this module's docstring, with what it leaves unprotected, the two files that read the dangling
    object today, and the blocker in its order (the harness fixes first, then the private-kernel arm); an edit that
    drops any of them reds here."""

    def _assert_worded(self, text, where):
        for needle in (LIMIT_UNPROTECTED, LIMIT_BLOCKER, LIMIT_ORDER) + LIMIT_READERS:
            self.assertIn(needle, text, "%s does not say: %s" % (where, needle))
        self.assertLess(text.index(LIMIT_UNPROTECTED), text.index(LIMIT_BLOCKER),
                        "%s: what is unprotected is said before the blocker" % where)
        self.assertLess(text.index(LIMIT_BLOCKER), text.index(LIMIT_ORDER), "%s: the blocker before the order" % where)

    def test_the_conftest_comment_says_what_is_unprotected_and_names_the_blocker_in_order(self):
        self._assert_worded(conftest_comment_text(), "tests/conftest.py")

    def test_this_modules_docstring_says_the_same(self):
        self._assert_worded(re.sub(r"\s+", " ", __doc__), "the module docstring")


RESIDUAL_GREEN = "proves no leak occurred in that run and not that no test would leak alone"
RESIDUAL_MASK = "a first builder that leaves its build masks a later sandboxed test's reach as a cache hit"
RESIDUAL_MEASURED = ("77 passed and 0 verdicts", "65 passed and 1 error")
RESIDUAL_INSTRUMENT = "the order-independent instrument is the module-alone sweep"
RESIDUAL_FOLLOWUP = "a follow-up item, its own PR after this one"
LEDGER_ENTRY = os.path.join(ROOT, "upstream", "2026-09-19-sdk-singleton-ratchet.md")


def ledger_entry_body():
    """The ratchet's ledger entry, the body past its header block, whitespace collapsed. A missing entry fails the test
    that reads it, never skips it: a skipping pin reports green."""
    with open(LEDGER_ENTRY) as f:
        lines = f.read().split("\n")
    assert lines[0] == "---", "the entry opens with a header block: %r" % lines[:1]
    close = lines.index("---", 1)
    return re.sub(r"\s+", " ", " ".join(lines[close + 1:]))


class TheResidualIsWorded(unittest.TestCase):
    """The residual the ratchet leaves is worded, in this module's docstring and in the ledger entry, as a stated
    limit: a green run under it proves no leak occurred in that run and not that no test would leak alone, because a
    first builder that leaves its build masks a later sandboxed test's reach as a cache hit; with the measurement that
    shows it, the order-independent instrument (the module-alone sweep) and the follow-up arm as its own PR, in that
    order. An edit that drops any of them reds here."""

    def _assert_worded(self, text, where):
        for needle in (RESIDUAL_GREEN, RESIDUAL_MASK, RESIDUAL_INSTRUMENT, RESIDUAL_FOLLOWUP) + RESIDUAL_MEASURED:
            self.assertTrue(needle in text, "%s does not say: %s" % (where, needle))
        self.assertLess(text.index(RESIDUAL_GREEN), text.index(RESIDUAL_MASK), "%s: the claim before its mechanism" % where)
        self.assertLess(text.index(RESIDUAL_MASK), text.index(RESIDUAL_MEASURED[0]), "%s: the mechanism before the measurement" % where)
        self.assertLess(text.index(RESIDUAL_MEASURED[1]), text.index(RESIDUAL_INSTRUMENT), "%s: the measurement before the instrument" % where)
        self.assertLess(text.index(RESIDUAL_INSTRUMENT), text.index(RESIDUAL_FOLLOWUP), "%s: the instrument before the follow-up" % where)

    def test_this_modules_docstring_names_the_residual(self):
        self._assert_worded(re.sub(r"\s+", " ", __doc__), "the module docstring")

    def test_the_ledger_entry_names_the_residual(self):
        self._assert_worded(ledger_entry_body(), "the ledger entry")


PROTECT_READS = "The PROTECTION is the structured reads above: none of them counts occurrences"
PROTECT_VV = "The child also runs -vv, which is NOT a protection"
RUN_PROTECT_READS = "never by occurrence, and that is the protection"
RUN_PROTECT_VV = "-vv is not one"


class TheProtectionIsWorded(unittest.TestCase):
    """The wording required at the round-3 preparation head, that the structured reads are the protection against the
    short summary's shape and -vv only makes a box run and a CI run compare by eye, is pinned in both docstrings that
    carry it, this module's and nested_run's, each in its own words: the reads named as the protection BEFORE -vv is
    named as not one, so a later author does not delete a structured read as redundant with -vv. The other three
    required wordings on this branch (the residual, the private-kernel limit, the error count's limit) each landed with
    a needle; this one landed without, and could be deleted or reflowed with the module green (round 3, 2026-09-19)."""

    def _assert_worded(self, text, where, reads, vv):
        for needle in (reads, vv):
            self.assertTrue(needle in text, "%s does not say: %s" % (where, needle))
        self.assertLess(text.index(reads), text.index(vv), "%s: the protection is named before what is not one" % where)

    def test_this_modules_docstring_names_the_reads_as_the_protection_and_vv_as_not_one(self):
        self._assert_worded(re.sub(r"\s+", " ", __doc__), "the module docstring", PROTECT_READS, PROTECT_VV)

    def test_nested_runs_docstring_says_the_same_in_its_own_words(self):
        self._assert_worded(re.sub(r"\s+", " ", nested_run.__doc__), "nested_run's docstring", RUN_PROTECT_READS, RUN_PROTECT_VV)


class TheReadersRosterNamesEveryReader(unittest.TestCase):
    """The module docstring's roster of structured output readers names every reader this module defines. The
    population is derived from the source, never listed here: the top-level functions between nested_run and _NestedRun
    whose first parameter is the nested run's output, so a reader added without its roster entry reds this test. At the
    round-4 head the roster omitted carriers, the reader that delta added, with the module green: the PROTECTION needle
    pins two claim sentences and their order, not the roster's names."""

    def test_every_reader_is_named_in_the_roster(self):
        src = inspect.getsource(sys.modules[__name__])
        region = src[src.index("\ndef nested_run("):src.index("\nclass _NestedRun")]
        readers = set(re.findall(r"^def (\w+)\(out\b", region, re.M))
        self.assertGreaterEqual(len(readers), 7, "a derived population that comes back short is a failure, not a pass: %r" % readers)
        doc = re.sub(r"\s+", " ", __doc__)
        roster = doc[doc.index("The outer tests read a nested run's output by structure"):doc.index(PROTECT_READS)]
        for name in sorted(readers):
            self.assertRegex(roster, r"\b%s\b" % re.escape(name), "the roster does not name the reader %s" % name)


class TheMutationCellsApply(unittest.TestCase):
    """The mutation table (MUTATIONS) applies at this tree, and the module docstring's matrix and the table name the
    same cells. Each cell's old text occurs exactly once in its target file and differs from its replacement, and the
    mutated file parses: a fixture edit that moves an anchor reds here instead of retiring the cell silently, and a
    recipe that would not compile is caught before a derivation runs it. Every key is carried by exactly one docstring
    cell as "derive: <id>", inside a parenthesis that opens with the cell's rule ("(red: "), and every derive id in the
    docstring is a key: the composition, pinned both ways. The table is not short: a population that comes back under
    the count at the head that set the floor is a failure, not a pass (the roster pin's convention). derive() deselects
    this class, and under any plant it reds: a replacement that removes its old text fails the exact-once count, and one
    that appends beside the old text (the new text containing the old, so the count holds after the plant) puts a new
    text into the file that this class holds absent. It is no cell's set."""

    def test_each_cells_old_text_occurs_exactly_once_and_the_mutation_parses(self):
        for cell, (target, subs) in MUTATIONS.items():
            with open(os.path.join(HERE, target)) as f:
                text = f.read()
            for old, new in subs:
                self.assertEqual(text.count(old), 1, "%s: the old text occurs %d times in %s, not once: %r"
                                 % (cell, text.count(old), target, old))
                self.assertNotEqual(old, new, cell)
                if old in new:                   # an append beside the old text: the plant leaves the count at one
                    self.assertFalse(new in text, "%s: the tree already carries the plant: %r" % (cell, new))
                    # assertFalse, not assertNotIn: the container is the whole fixture file, which the failure
                    # message would otherwise quote entire
                text = text.replace(old, new)
            ast.parse(text, filename=target)                 # a SyntaxError is the failure

    def test_the_docstring_and_the_table_name_the_same_cells(self):
        doc = re.sub(r"\s+", " ", __doc__)
        in_doc = re.findall(r"; derive: ([\w-]+)\)", doc)
        self.assertEqual(len(in_doc), len(set(in_doc)), "a derive id appears in two cells: %r" % in_doc)
        self.assertEqual(set(in_doc), set(MUTATIONS), "the docstring's derive ids and the table's keys differ")
        for cell in MUTATIONS:
            text = mutation_cell_text(__doc__, cell)
            self.assertIsNotNone(text, cell)
            self.assertIn("(red: ", text, "%s: the cell states no rule: %s" % (cell, text))

    def test_the_table_is_not_short(self):
        self.assertGreaterEqual(len(MUTATIONS), 30, "the refusal block's twenty-three cells and the boundary link's seven "
                                "at the round-6 close head; a shorter table is a failure, not a pass: %r" % sorted(MUTATIONS))


class ClassTeardownRemovesTheDirectory(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_D
    ERRORS = 2

    def test_the_first_build_over_the_class_sandbox_fails_as_its_own(self):
        text = self.assertRatchetFailed("One", "test_a_builds_over_a_kept_sandbox_stored_on_the_class")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_class_boundary_names_the_directory_its_teardown_removed(self):
        self.assertEqual(outcomes(self.out).get("One.test_b_does_nothing"), {"PASSED", "ERROR"}, self.out)
        text = self.assertBoundaryFailed("::One", "One.test_b_does_nothing")
        self.assertTrue(text.startswith("over a directory it removed: SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), "a regular file at the path is not a directory: %s" % text)

    def test_the_class_that_inherits_the_named_object_is_quiet(self):
        self.assertRatchetPassed("Two", "test_a_does_nothing")
        self.assertRatchetPassed("Two", "test_b_does_nothing")
        self.assertIsNone(boundary(self.out, "::Two"), self.out)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)


class ImportTimeLeakIsInheritedOnce(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_E
    ERRORS = 2

    def test_the_first_test_to_meet_the_state_reports_it_as_inherited_after_its_body_ran(self):
        text = self.assertInherited("Cases", "test_a_does_nothing_and_is_the_first_to_meet_the_state")
        self.assertTrue(text.startswith("SdkBackend over "), text)
        self.assertIn("import-time code", text)
        self.assertIn("after that test's own teardown", text)
        self.assertNotIn(REFUSED_OBJECT, text, "no refusal preceded this report, so it names no refused object: %s" % text)

    def test_the_next_test_under_the_same_object_is_quiet(self):
        self.assertRatchetPassed("Cases", "test_b_does_nothing")

    def test_a_leak_of_its_own_is_still_named(self):
        text = self.assertRatchetFailed("Cases", "test_c_makes_a_kept_sandbox_leak_of_its_own")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_class_and_module_ends_are_quiet(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class ClassScopedRoot(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_K
    ERRORS = 1

    def test_the_lazy_build_over_the_class_root_passes_at_its_own_window(self):
        self.assertRatchetPassed("One", "test_a_the_lazy_build_over_the_class_root_passes_at_its_own_window")
        self.assertIsNone(verdict(self.out, "One", "test_b_does_nothing"), self.out)      # b's ERROR is the boundary's, below

    def test_the_class_that_moved_jd_state_and_kept_the_singleton_is_the_author(self):
        text = self.assertBoundaryFailed("::One", "One.test_b_does_nothing")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)
        _, fix = boundary(self.out, "::One")
        self.assertIn("setUpClass and tearDownClass when the class moves it", fix)

    def test_the_class_level_save_and_restore_is_quiet(self):
        self.assertRatchetPassed("Two", "test_a_builds_over_the_class_root")
        self.assertIsNone(boundary(self.out, "::Two"), self.out)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)


class ModuleTeardownRemovesTheDirectory(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_L
    ERRORS = 2

    def test_the_first_build_over_the_module_sandbox_fails_as_its_own(self):
        text = self.assertRatchetFailed("Cases", "test_a_builds_over_a_kept_sandbox_stored_on_the_module")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)

    def test_the_module_boundary_names_the_directory_its_teardown_removed(self):
        text = self.assertBoundaryFailed("", "Cases.test_b_does_nothing")
        self.assertTrue(text.startswith("over a directory it removed: SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)
        self.assertIsNone(boundary(self.out, "::Cases"), "the class end is quiet on the named object: %s" % self.out)


class FirstLoadInsideTheTest(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_H
    ERRORS = 1

    def test_the_first_load_then_a_build_over_a_kept_sandbox_is_named_by_what_it_left(self):
        text = self.assertRatchetFailed("Cases", "test_a_the_first_load_then_a_build_over_a_kept_sandbox_fails")
        self.assertTrue(text.startswith(REEXEC + " over a root that is not jd.STATE: SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class FirstLoadThenTheLazyBuild(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_H2
    ERRORS = 0

    def test_the_first_load_then_the_lazy_build_over_the_loaders_root_passes(self):
        self.assertRatchetPassed("Cases", "test_a_the_first_load_then_the_lazy_build_over_the_loaders_root_passes")
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class ValuesThatAreNotTheKernelsBuild(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_F
    ERRORS = 6

    def test_a_look_alike_over_jd_state_is_refused_by_the_class_check(self):
        text = self.assertObjectRoad("Cases", "test_a_a_look_alike_over_jd_state_as_the_workers_first_value_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after test_scratch.SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_none_left_in_place_of_the_look_alike_fails(self):
        text = self.assertObjectRoad("Cases", "test_b_none_left_in_place_of_the_look_alike_fails")
        self.assertTrue(text.startswith("changed after its teardown: before test_scratch.SdkBackend over "), text)
        self.assertTrue(text.endswith(", after None (not built)"), text)

    def test_the_kernels_unavailable_outcome_passes(self):
        self.assertRatchetPassed("Cases", "test_c_the_kernels_unavailable_outcome_passes")

    def test_none_left_in_place_of_false_fails(self):
        text = self.assertObjectRoad("Cases", "test_d_none_left_in_place_of_false_fails")
        self.assertTrue(text.startswith("changed after its teardown: before False"), text)
        self.assertTrue(text.endswith(", after None (not built)"), text)

    def test_the_real_lazy_build_over_the_run_root_passes(self):
        self.assertRatchetPassed("Cases", "test_e_the_real_lazy_build_over_the_run_root_passes")

    def test_false_left_in_place_of_the_backend_fails(self):
        text = self.assertObjectRoad("Cases", "test_f_false_left_in_place_of_the_backend_fails")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertIn(", after False", text)

    def test_a_simplenamespace_left_fails_and_renders_module_qualified(self):
        text = self.assertObjectRoad("Cases", "test_g_a_simplenamespace_left_fails")
        self.assertTrue(text.endswith(", after types.SimpleNamespace over no state_dir"), text)

    def test_a_magicmock_left_fails_without_the_gone_clause(self):
        # The clause says a state_dir is NO LONGER a directory, true of the kernel's own class alone; a MagicMock's
        # attribute never was one, and at the round-3 head the clause was appended to it all the same.
        text = self.assertObjectRoad("Cases", "test_h_a_magicmock_left_fails")
        self.assertTrue(text.startswith("changed after its teardown: before types.SimpleNamespace over no state_dir, "
                                        "after unittest.mock.MagicMock over <MagicMock name='mock.state_dir'"), text)
        self.assertNotIn(GONE, text, "the gone clause is gated on the kernel's class as well as on isdir: %s" % text)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class FirstBuildWithJdStateLeftAtTheSandbox(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_J
    ERRORS = 1
    JUDGE_RED = True

    def test_the_ratchet_judges_against_the_root_the_test_inherited_and_the_judge_names_the_state_leak(self):
        text = self.assertRatchetFailed("Cases", "test_a_the_first_build_over_a_sandbox_with_jd_state_left_there_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)
        self.assertIn(SHARED_STATE, self.out, "the judge fixture names the moved jd.STATE in the same teardown")
        self.assertIn("romp_judge.STATE changed from", self.out)
        self.assertRegex(self.out, r"errors while tearing down <TestCaseFunction test_a_\w+> \(2 sub-exceptions\)",
                         "pytest 9 renders the two teardown failures on the one item as one exception group")

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class BoundaryYieldsToTheTestsOwnWindows(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_N
    FOLLOWER = SCRATCH_N2
    ERRORS = 6

    def test_each_accused_test_is_named_once_on_the_object_road(self):
        for cls, method, after in (("Two", "test_a_leaves_none", ", after None (not built)"),
                                   ("Three", "test_a_leaves_none_as_the_last_test_of_a_class_that_started_on_a_real_backend",
                                    ", after None (not built)"),
                                   ("Four", "test_b_leaves_false_as_the_last_test", ", after False (the build failed)"),
                                   ("Follow", "test_a_leaves_none_as_the_last_test_of_the_module", ", after None (not built)")):
            text = self.assertObjectRoad(cls, method)
            self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
            self.assertTrue(text.endswith(after), text)
        text = self.assertObjectRoad("Five", "test_a_none_in_place_of_false")
        self.assertTrue(text.startswith("changed after its teardown: before False (the build failed), after None"), text)

    def test_the_allowed_rebuild_after_an_accused_reset_passes_alone(self):
        self.assertRatchetPassed("Two", "test_b_the_lazy_rebuild_over_the_run_root_after_the_accused_reset")
        self.assertRatchetPassed("Four", "test_a_the_lazy_rebuild")
        self.assertRatchetPassed("Five", "test_b_the_lazy_rebuild")

    def test_a_class_that_moves_jd_state_and_never_builds_is_quiet(self):
        # Sandboxed's test runs under an unnamed singleton whose state_dir is not jd.STATE, the picture the first-window
        # report names at the worker's first window only, and only for the object the module's start read found; here
        # One.a's window made it, judged there, and nothing is said. Z pins the flag itself (this object is not the
        # module start read's, so the identity term alone keeps this case quiet).
        self.assertRatchetPassed("Sandboxed", "test_a_does_nothing_under_a_singleton_over_the_run_root")
        self.assertIsNone(inherited(self.out, "Sandboxed", "test_a_does_nothing_under_a_singleton_over_the_run_root", head=INHERITED_KEPT))
        self.assertIsNone(boundary(self.out, "::Sandboxed"), self.out)

    def test_no_class_or_module_boundary_is_accused_of_what_its_tests_did(self):
        for scope in ("::One", "::Sandboxed", "::Two", "::Three", "::Four", "::Five", ""):
            self.assertIsNone(boundary(self.out, scope), "a boundary that did nothing is accused: %s" % self.out)
        self.assertIsNone(boundary(self.out, "::Follow", module="test_scratch2.py"), self.out)
        self.assertIsNone(boundary(self.out, "", module="test_scratch2.py"), self.out)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py::Six"},
                         "the one boundary verdict in the run is Six's: %s" % self.out)
        # The "(N sub-exceptions)" suffix is CPython's BaseExceptionGroup str, and "errors while tearing down" around it
        # is pytest's. This absence read is the rendering-agnostic backstop that catches a second teardown exception
        # from outside the ratchet and the judge, which no structured read above sees; the presence twins in J, R1
        # and R2 make a rendering change loud, and the boundary_scopes equality two lines above is the structural pin
        # (deleting this line alone changes nothing: a planted fold reds there).
        self.assertNotIn("sub-exceptions", self.out, "no verdict folds into another's teardown report: %s" % self.out)

    def test_a_class_that_dropped_the_object_it_found_before_its_tests_rebuild_stays_the_author(self):
        # The first window inside Six started from None, not from the object Six found (Five.b's build), so the yield
        # does not apply and the class is named for the rebuild over the same root; the test itself passes alone.
        text = self.assertBoundaryFailed("::Six", "Six.test_a_the_lazy_rebuild_the_next_module_inherits", remedy=REMEDY_B)
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + REBUILT), text)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)


class ScopesMoveJdStateUnderAnImportTimeBuildOverTheRunRoot(_NestedRun, unittest.TestCase):
    """K2: the kernel's own lazy build at import time over the RUN root, then setUpModule and One's setUpClass move
    jd.STATE for their tests without building and put it back. Nothing leaked, and no window says anything: the
    kept-root report at the worker's first window compares the object's state_dir with jd.STATE as the MODULE START
    READ recorded it (the read whose object identity it checks), which the scope setups' moves come after. Compared
    with jd.STATE at the window itself, as the report did before the fixed head's consolidation, One.a got the
    kept-root report blaming import-time code for a build over another root or a move of jd.STATE that never
    happened (an ERROR on an innocent test, exit 1)."""
    SCRATCH = SCRATCH_K2
    ERRORS = 0

    def test_no_window_reports_the_run_roots_singleton_as_inherited(self):
        for cls in ("One", "Two"):
            self.assertRatchetPassed(cls, "test_a_does_nothing_under_the_run_roots_singleton")
            self.assertIsNone(inherited(self.out, cls, "test_a_does_nothing_under_the_run_roots_singleton", head=INHERITED_KEPT),
                              self.out)
        self.assertEqual(self.rc, 0, self.out)

    def test_every_boundary_is_quiet(self):
        for scope in ("::One", "::Two", ""):
            self.assertIsNone(boundary(self.out, scope), self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)


class ImportTimeLeakOverAKeptSandboxIsInheritedOnce(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_S6
    ERRORS = 1

    def test_the_first_window_reports_the_kept_root_as_inherited_beside_the_tests_own_verdict(self):
        text = self.assertInherited("Cases", "test_a_is_the_first_to_meet_the_state_and_leaks_on_its_own", head=INHERITED_KEPT, own=True)
        self.assertTrue(text.startswith("SdkBackend over "), text)
        self.assertIn(", jd.STATE ", text)
        self.assertIn("import-time code did", text)
        own = self.assertRatchetFailed("Cases", "test_a_is_the_first_to_meet_the_state_and_leaks_on_its_own")
        self.assertTrue(own.startswith("changed after its teardown: before SdkBackend over "), own)
        self.assertNotIn(GONE, own)

    def test_the_next_test_under_the_tests_own_object_is_quiet_and_the_ends_are_quiet(self):
        self.assertRatchetPassed("Cases", "test_b_does_nothing")
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class AnImportTimeKeptRootLeakMetFirstByAClassThatSwapsTheSingleton(_NestedRun, unittest.TestCase):
    """S7: S6's import-time build over a kept root, jd.STATE restored, met first by a class that saves, resets and puts
    back the singleton around its one test (K.Two's shape). One.a's before object is None, not the one the module start
    read found, so the kept-root report is not taken at the worker's first window; the window REFUSES instead, with the
    flag spent there: it names the leak from the start read's fields (the object, its root, and jd.STATE at that read),
    says a module or class setup swapped the slot between the two reads, accuses no test and names no scope. Two.a
    meets the object at a later window and is quiet, One's boundary sees the object it found put back unchanged, every
    boundary is quiet, and the run exits 1 on the refusal alone. Before the refusal this class pinned the silence (exit
    0, no report) as a stated limit, a pin that froze the defect: a reader of a green pin concludes the case is handled.
    The deferral not taken (the flag kept when the identity term fails) would put the kept-root report on Two.a, where
    a test body has run and its premise sentence, before any test in this worker has run, is false."""
    SCRATCH = SCRATCH_S7
    ERRORS = 1
    FIRST = "One.test_a_builds_over_the_class_root"

    def test_the_first_window_names_the_leak_and_refuses_to_attribute_it(self):
        cls, method = self.FIRST.split(".")
        text = inherited(self.out, cls, method, head=SWAPPED)
        self.assertIsNotNone(text, "the first window's refusal line, opening with SWAPPED, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"},
                         "the body runs; the refusal is the teardown's: %s" % self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the allowed build over the class root is not accused: %s" % self.out)
        self.assertTrue(text.startswith("SdkBackend over "), text)                # the start read's object and its root
        self.assertRegex(text, r", jd.STATE \S+/romp at that read")             # the run root as the start read recorded it, by
        self.assertIn("(it holds None (not built))", text)                       # value: the run root ends in /romp, the class
        self.assertIn("no test is accused and no scope is named", text)          # root does not; what the window found in the slot
        self.assertIn("Import-time code did, or a session- or package-scoped fixture did", text)
        self.assertIn("building the singleton over a root that is not the run's", text)   # the kept shape's cause clause
        self.assertNotIn("Fix:", text, "no remedy is addressed to the test at the window: %s" % text)
        self.assertNotIn(GONE, text)
        self.assertNotIn(BOUNDARY, text)
        self.assertIsNone(re.search(r"test_scratch2?\.py::\w+", text), "no scope or test is named in the refusal: %s" % text)
        for head in (INHERITED, INHERITED_KEPT):
            self.assertIsNone(inherited(self.out, cls, method, head=head), "not the starts-under report: %s" % self.out)

    def test_the_refusal_is_on_one_test_and_every_boundary_is_quiet(self):
        self.assertEqual(carriers(self.out, SWAPPED), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), set(), "the object's directory stands: the kept head, not the gone one: %s" % self.out)
        for scope in ("::One", "::Two", ""):
            self.assertIsNone(boundary(self.out, scope), self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)
        self.assertNotIn("sub-exceptions", self.out, "the refusal is One.a's only teardown failure, no fold: %s" % self.out)

    def test_the_later_test_that_meets_the_object_is_quiet(self):
        self.assertRatchetPassed("Two", "test_a_meets_the_import_time_object")
        for head in (INHERITED_KEPT, SWAPPED):
            self.assertIsNone(inherited(self.out, "Two", "test_a_meets_the_import_time_object", head=head), self.out)


class TheRefusalIsTheFirstWindowsAlone(AnImportTimeKeptRootLeakMetFirstByAClassThatSwapsTheSingleton):
    """S7B: S7 with a third class of One's shape after Two, so a LATER window where the identity term fails exists
    (Three.a's before object is None while the start read's is the import-time object). The refusal is the first
    window's: one carrier, Three.a quiet, Three's boundary quiet, still one error. The flag's two cells are in the
    module docstring's matrix with their rules and derive ids (refusal-flag-dropped, refusal-identity-alone); this case
    is a carrier of both by the rules, Three.a being a later window, and one where the identity term fails."""
    SCRATCH = SCRATCH_S7B

    def test_the_later_swapping_class_gets_no_refusal(self):
        self.assertRatchetPassed("Three", "test_a_builds_over_the_class_root")
        self.assertIsNone(inherited(self.out, "Three", "test_a_builds_over_the_class_root", head=SWAPPED), self.out)
        self.assertIsNone(boundary(self.out, "::Three"), self.out)


class ASwappingClassOverAnImportTimeBuildOverTheRunRoot(_NestedRun, unittest.TestCase):
    """S8, the refusal's refused input on the run-root shape: K2's import-time build over the RUN root, then S7's
    swapping class. The identity term fails at One.a, but the start read's object is over jd.STATE as that read
    recorded it, so nothing leaked and the refusal is not taken; Two.a meets the run root's object quietly and the run
    exits 0."""
    SCRATCH = SCRATCH_S8
    ERRORS = 0

    def test_no_refusal_and_no_report_on_a_clean_import_time_build(self):
        self.assertRatchetPassed("One", "test_a_builds_over_the_class_root")
        self.assertRatchetPassed("Two", "test_a_meets_the_run_roots_object")
        for head in (SWAPPED, SWAPPED_GONE):
            self.assertEqual(carriers(self.out, head), set(), self.out)
        for cls, method in (("One", "test_a_builds_over_the_class_root"), ("Two", "test_a_meets_the_run_roots_object")):
            self.assertIsNone(inherited(self.out, cls, method, head=INHERITED_KEPT), self.out)
        self.assertEqual(self.rc, 0, self.out)

    def test_every_boundary_is_quiet(self):
        for scope in ("::One", "::Two", ""):
            self.assertIsNone(boundary(self.out, scope), self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)


class ASwappingClassOverAnImportTimeGoneLeak(_NestedRun, unittest.TestCase):
    """S9, the gone shape where the swapping class puts the object back: E's import-time leak (built over a sandbox,
    jd.STATE restored, the sandbox removed), then S7's swapping class. One.a's first window refuses under the gone head
    (the start read's object over a directory that no longer exists, the slot holding None, the cause family narrowed to
    what could have run before the start read), and Two.a, which starts under the gone object put back, carries the
    inherited gone report with its own cause clause: two lines on two items, each saying what the other does not (the
    refusal, the object's origin before any test ran; the gone report, which test lives under it), the pattern the
    completes-a-leak cases set; two errors, every boundary quiet. Before the gone arm this class pinned One.a quiet and
    left the shape where the class never puts the object back (S10) with no line naming the leak's origin."""
    SCRATCH = SCRATCH_S9
    ERRORS = 2
    FIRST = "One.test_a_builds_over_the_class_root"

    def test_the_first_window_refuses_under_the_gone_head(self):
        cls, method = self.FIRST.split(".")
        text = inherited(self.out, cls, method, head=SWAPPED_GONE)
        self.assertIsNotNone(text, "the first window's refusal line, opening with SWAPPED_GONE, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"},
                         "the body runs; the refusal is the teardown's: %s" % self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the allowed build over the class root is not accused: %s" % self.out)
        self.assertTrue(text.startswith("SdkBackend over "), text)                # the start read's object and its removed root
        self.assertRegex(text, r", jd.STATE \S+/romp at that read")             # the run root as the start read recorded it, by value
        self.assertIn("(it holds None (not built))", text)
        self.assertIn("no test is accused and no scope is named", text)
        self.assertIn("building the singleton over a directory since removed", text)   # the gone shape's cause clause
        self.assertNotIn("Fix:", text, "no remedy is addressed to the test at the window: %s" % text)
        self.assertNotIn(BOUNDARY, text)
        self.assertIsNone(re.search(r"test_scratch2?\.py::\w+", text), "no scope or test is named in the refusal: %s" % text)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED), set(), "the kept head is the standing directory's: %s" % self.out)

    def test_the_later_test_that_starts_under_the_object_carries_the_gone_report(self):
        text = self.assertInherited("Two", "test_a_meets_the_gone_object")
        self.assertTrue(text.startswith("SdkBackend over "), text)
        self.assertIn("import-time code did", text)
        self.assertIn(REFUSED_OBJECT, text, "the report names the object as the one the refusal named: %s" % text)   # both lines
        self.assertLess(text.index(REFUSED_OBJECT), text.index("This test did not make it"), text)   # name one object: the refusal
        self.assertEqual(carriers(self.out, INHERITED), {"test_scratch.py::Two::test_a_meets_the_gone_object"}, self.out)   # read by
        # carriers with the SWAPPED_GONE head on One.a (the first test above), the report read here on Two.a, its link clause opening
        # the tail; the clause appears in no other line of the run
        self.assertNotIn("sub-exceptions", self.out, "the two lines land on two items, no fold: %s" % self.out)

    def test_every_boundary_is_quiet(self):
        for scope in ("::One", "::Two", ""):
            self.assertIsNone(boundary(self.out, scope), self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)


class TheGoneObjectRepointedBetweenTheTwoLines(_NestedRun, unittest.TestCase):
    """S9B: S9's pair of lines with the gone object REPOINTED between them, so the two lines render two different paths
    for one object and the rendered text cannot link them. E's import-time leak (built over a sandbox, jd.STATE restored,
    the sandbox removed); setUpModule, after the module start read, repoints the object's state_dir to a second removed
    path (prefix moved-) and clears the slot; One.a makes the lazy build over the run root (allowed) and its first window
    refuses under the gone head, naming the root the start read RECORDED; Two's setUpClass puts the repointed object in
    the slot for its one test, which carries the inherited gone report over the moved path, and its tearDownClass puts
    the build back; tearDownModule puts the state_dir and the slot back, so the module's start and end reads agree and
    every boundary is quiet; two errors. The link between the two lines is the object, not its path: the fixture records
    the object the refusal named on _SDK_REFUSED at the moment the refusal is taken, and the gone report on an object
    that list holds opens its tail by saying it is the object this worker's first test window refused to attribute. Here
    the paths differ and the clause is still there; with the link keyed on the rendered text the clause would be missing
    (the kill cell), while S9, where the paths agree, would stay green."""
    SCRATCH = SCRATCH_S9B
    ERRORS = 2
    FIRST = "One.test_a_builds_over_the_run_root"
    LATER = "Two.test_a_meets_the_gone_object_repointed"

    def test_the_two_lines_render_two_paths_and_the_report_names_the_object_as_the_one_refused(self):
        cls, method = self.FIRST.split(".")
        refusal = inherited(self.out, cls, method, head=SWAPPED_GONE)
        self.assertIsNotNone(refusal, "the first window's refusal line, opening with SWAPPED_GONE, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the lazy build over the run root is not accused: %s" % self.out)
        report = self.assertInherited(*self.LATER.split("."))
        refused_root = re.match(r"SdkBackend over (\S+),", refusal).group(1)      # the root the start read recorded
        reported_root = re.match(r"SdkBackend over (\S+)\.", report).group(1)     # the live attribute at the later window
        self.assertNotEqual(refused_root, reported_root, "the object was repointed between the two lines: %s" % self.out)
        self.assertIn("moved-", reported_root)
        self.assertNotIn("moved-", refused_root)
        self.assertIn(REFUSED_OBJECT, report, "the link, keyed on the object: %s" % report)
        self.assertLess(report.index(REFUSED_OBJECT), report.index("This test did not make it"), report)
        self.assertNotIn(REFUSED_OBJECT, refusal)
        self.assertIn("building the singleton over a directory since removed", refusal)
        self.assertIn("import-time code did", report)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, INHERITED), {"test_scratch.py::" + self.LATER.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED), set(), self.out)

    def test_every_boundary_is_quiet(self):
        for scope in ("::One", "::Two", ""):
            self.assertIsNone(boundary(self.out, scope), self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)
        self.assertNotIn("sub-exceptions", self.out, "the two lines land on two items, no fold: %s" % self.out)


class ASwappingClassNeverPutsTheGoneObjectBack(_NestedRun, unittest.TestCase):
    """S10, the gone shape where no window ever starts under the object: E's import-time leak, then a class whose
    setUpClass resets the slot and never puts the object back (jd.STATE untouched; a lazy-builds over the run root, Two.a
    meets that build). Without the gone arm the only line was One's boundary verdict on the swap (before the gone
    object, after the class's build, the object remedy), which names neither the gone directory nor import-time code:
    the leak's origin went unstated. Now One.a's teardown carries the refusal under the gone head beside that verdict,
    one exception group, one error; no test starts under the gone object, so no gone report; Two.a is quiet.
    The two lines name one object, and the verdict says so: the object it found is the one this worker's first test
    window refused to attribute, the link keyed on the object (_sdk_refused, membership by identity on _SDK_REFUSED) and
    not on its rendered path, which here the two lines agree on and in S10B do not. The clause is the boundary's own,
    with its own tail (the scope at whose end the slot no longer held the object, and the value it held: what the
    start-to-end road always knows; the gone report's tail, the test that lives under the object, is false here, where
    no test does, and a tail naming the scope as the one that swapped the object out is false at S15's module end, which
    found the slot changed by a test inside it), and ends one period before the remedy: a period inside the clause made
    ".. Fix:" on the line, and the boundary() reader's non-greedy read accepted it."""
    SCRATCH = SCRATCH_S10
    ERRORS = 1
    FIRST = "One.test_a_builds_over_the_run_root"

    def test_the_first_window_refuses_under_the_gone_head_beside_the_boundary_verdict(self):
        cls, method = self.FIRST.split(".")
        text = inherited(self.out, cls, method, head=SWAPPED_GONE)
        self.assertIsNotNone(text, "the first window's refusal line, opening with SWAPPED_GONE, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the allowed build over the run root is not accused: %s" % self.out)
        self.assertTrue(text.startswith("SdkBackend over "), text)
        self.assertIn(", jd.STATE ", text)
        self.assertIn("(it holds None (not built))", text)
        self.assertIn("no test is accused and no scope is named", text)
        self.assertIn("building the singleton over a directory since removed", text)
        self.assertNotIn("Fix:", text, text)
        self.assertNotIn(REFUSED_OBJECT, text, "the refusal is the line linked to; the clause is the verdict's: %s" % text)
        self.assertNotIn(BOUNDARY, text, "the boundary verdict is its own line, not folded into the refusal: %s" % text)
        self.assertIsNone(re.search(r"test_scratch2?\.py::\w+", text), "no scope or test is named in the refusal: %s" % text)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED), set(), self.out)
        for head in (INHERITED, INHERITED_KEPT):
            self.assertEqual(carriers(self.out, head), set(), "no test starts under the gone object: %s" % self.out)

    def test_the_boundary_verdict_on_the_swap_lands_beside_the_refusal_and_names_the_object_as_the_one_refused(self):
        clause = self.assertBoundaryFailed("::One", self.FIRST, remedy=REMEDY_B)
        self.assertTrue(clause.startswith("changed after its teardown: before SdkBackend over "), clause)
        self.assertIn(REFUSED_FOUND, clause, "the verdict says the object it found is the one the refusal named: %s" % clause)
        self.assertLess(clause.index(", after SdkBackend over "), clause.index(REFUSED_FOUND), clause)   # the clause follows
        # the transition it links, before the remedy (boundary() reads it up to "Fix:"); its last words are the tail
        self.assertTrue(clause.endswith(REFUSED_FOUND_TAIL), "the clause ends on its tail, no period inside it: %s" % clause)
        self.assertNotIn(".. Fix:", self.out, "one period between the clause and the remedy: %s" % self.out)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py::One"}, self.out)
        # Two nodes fail in One.a's teardown stack, the item (the function fixture's refusal) and the class (the boundary
        # verdict), so pytest 9 groups them as "errors during test teardown" with two sub-exceptions; J, R1 and R2 pin the
        # one-node shape ("errors while tearing down <TestCaseFunction ...>"), two function-fixture failures on one item.
        self.assertRegex(self.out, r"BaseExceptionGroup: errors during test teardown \(2 sub-exceptions\)",
                         "the refusal and the boundary verdict are One.a's one teardown report: %s" % self.out)
        for scope in ("::Two", ""):
            self.assertIsNone(boundary(self.out, scope), self.out)

    def test_the_test_that_meets_the_classes_build_is_quiet(self):
        self.assertRatchetPassed("Two", "test_a_meets_the_classes_build")


class TheSwapVerdictNamesTheGoneObjectRepointedBetweenTheTwoLines(_NestedRun, unittest.TestCase):
    """S10B: S10's pair of lines, the refusal and One's boundary verdict on the swap, with the gone object REPOINTED
    between the reads that render them, so the two lines render two different paths for one object and the rendered text
    cannot link them. E's import-time leak (built over a sandbox, jd.STATE restored, the sandbox removed); setUpModule,
    after the module start read, repoints the object's state_dir to a second removed path (prefix moved-) and leaves it
    in the slot; One's class start read finds the object over the moved path; One's setUpClass resets the slot and never
    puts the object back (jd.STATE untouched); One.a makes the lazy build over the run root (allowed) and its first
    window refuses under the gone head, naming the root the module start read RECORDED; One's boundary verdict on the
    swap renders the object it found from the live attribute, the moved path, and still says it found the object the
    first window refused to attribute: the link is the object, not its path (_sdk_refused, membership by identity on
    _SDK_REFUSED). One exception group on One.a's teardown, one error; Two.a meets the build and is quiet; the module
    end is quiet on the named build. With the boundary's link keyed on the rendered text the clause would be missing
    here (the kill cell, derive: boundary-link-by-path), while S10, where the two lines render one path, would stay
    green."""
    SCRATCH = SCRATCH_S10B
    ERRORS = 1
    FIRST = "One.test_a_builds_over_the_run_root"

    def test_the_two_lines_render_two_paths_and_the_verdict_names_the_object_as_the_one_refused(self):
        cls, method = self.FIRST.split(".")
        refusal = inherited(self.out, cls, method, head=SWAPPED_GONE)
        self.assertIsNotNone(refusal, "the first window's refusal line, opening with SWAPPED_GONE, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the lazy build over the run root is not accused: %s" % self.out)
        clause = self.assertBoundaryFailed("::One", self.FIRST, remedy=REMEDY_B)
        refused_root = re.match(r"SdkBackend over (\S+),", refusal).group(1)     # the root the module start read recorded
        m = re.match(r"changed after its teardown: before SdkBackend over (\S+), after SdkBackend over (\S+)\.", clause)
        self.assertIsNotNone(m, clause)
        found_root = m.group(1)                                                    # the live attribute at the class's reads
        self.assertNotEqual(refused_root, found_root, "the object was repointed between the two lines: %s" % self.out)
        self.assertIn("moved-", found_root)
        self.assertNotIn("moved-", refused_root)
        self.assertIn(REFUSED_FOUND, clause, "the link, keyed on the object: %s" % clause)
        self.assertLess(clause.index(", after SdkBackend over "), clause.index(REFUSED_FOUND), clause)   # the clause follows the transition
        self.assertTrue(clause.endswith(REFUSED_FOUND_TAIL), "the clause ends on its tail, no period inside it: %s" % clause)
        self.assertNotIn(".. Fix:", self.out, "one period between the clause and the remedy: %s" % self.out)
        self.assertNotIn(REFUSED_OBJECT, refusal)
        self.assertIn("building the singleton over a directory since removed", refusal)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED), set(), self.out)
        for head in (INHERITED, INHERITED_KEPT):
            self.assertEqual(carriers(self.out, head), set(), "no test starts under the gone object: %s" % self.out)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py::One"}, self.out)
        self.assertRegex(self.out, r"BaseExceptionGroup: errors during test teardown \(2 sub-exceptions\)",
                         "the refusal and the boundary verdict are One.a's one teardown report: %s" % self.out)

    def test_the_test_that_meets_the_classes_build_is_quiet_and_the_other_ends_are(self):
        self.assertRatchetPassed("Two", "test_a_meets_the_classes_build")
        for scope in ("::Two", ""):
            self.assertIsNone(boundary(self.out, scope), self.out)


class TheFoundObjectRefusedAndTheVerdictsOnOtherObjectsCarryNoClause(_NestedRun, unittest.TestCase):
    """S10C, the boundary link clause's two negatives with a refusal in the run: a verdict rendering an object other
    than the one the scope found, and a verdict on a found object no refusal named. E's import-time gone leak, the
    object kept as _obj and put back by tearDownModule (the module's start and end reads agree on it, so the module end
    is quiet, the reason S14's Two is). One's setUpClass resets the slot (S10's swap) and One.a lazy-builds over the run
    root (allowed; its first window refuses under the gone head, naming the gone object); One's tearDownClass repoints
    that build's state_dir to a kept sandbox (X.Two's shape), so One's verdict is the last-object repoint, rendering the
    build alone (before it over the run root, after it over the sandbox, the state_dir remedy) while the object One
    FOUND is the refused one: a clause keyed on the found object there would name an object the line does not show, and
    the fixture keys the clause on the object each road renders, so One's verdict carries none. Two does nothing under
    the build and its tearDownClass resets the slot to None (M.Three's shape), so Two's verdict is the start-to-end
    judgment on a found object no refusal named (before the build over the sandbox, after None, the object remedy), and
    carries none while the refused list holds the first object: membership by identity, not any refusal's having been
    taken. The refusal and One's verdict are One.a's one teardown report; Two.a passes and errors at its teardown; two
    errors. Kill cells: the clause on every start-to-end verdict (derive: boundary-link-unconditional, Two's carries
    it), the link by any refusal in the worker (derive: boundary-link-by-existence, Two's carries it), and the clause
    keyed on the found object on every road (derive: boundary-link-on-start-object, One's carries it)."""
    SCRATCH = SCRATCH_S10C
    ERRORS = 2
    FIRST = "One.test_a_builds_over_the_run_root"
    LAST = "Two.test_a_does_nothing_under_the_repointed_build"

    def test_the_refusal_names_the_gone_object_and_neither_verdict_says_it_found_it(self):
        cls, method = self.FIRST.split(".")
        refusal = inherited(self.out, cls, method, head=SWAPPED_GONE)
        self.assertIsNotNone(refusal, "the first window's refusal line, opening with SWAPPED_GONE, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the lazy build over the run root is not accused: %s" % self.out)
        self.assertIn("building the singleton over a directory since removed", refusal)
        self.assertNotIn(REFUSED_OBJECT, refusal)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED), set(), self.out)
        for head in (INHERITED, INHERITED_KEPT):
            self.assertEqual(carriers(self.out, head), set(), "no test starts under the gone object: %s" % self.out)
        refused_root = re.match(r"SdkBackend over (\S+),", refusal).group(1)     # the gone root the module start read recorded
        one = self.assertBoundaryFailed("::One", self.FIRST, remedy=REMEDY_C)
        self.assertTrue(one.startswith("changed after its teardown: before SdkBackend over "), one)
        self.assertIn(", after SdkBackend over ", one)
        self.assertNotIn(GONE, one)
        self.assertNotIn(REFUSED_OBJECT, one, "the verdict renders the build the teardown repointed, not the object the class "
                         "found; a clause here would name an object the line does not show: %s" % one)
        self.assertNotIn(refused_root, one, "the refused object is rendered on the refusal alone: %s" % one)
        two = self.assertBoundaryFailed("::Two", self.LAST, remedy=REMEDY_B)
        self.assertTrue(two.startswith("changed after its teardown: before SdkBackend over "), two)
        self.assertTrue(two.endswith(", after None (not built)"), two)
        self.assertNotIn(REFUSED_OBJECT, two, "a start-to-end verdict on a found object no refusal named, with a refusal standing "
                         "in the worker: %s" % two)
        self.assertNotIn(refused_root, two, two)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py::One", "test_scratch.py::Two"}, self.out)
        self.assertRegex(self.out, r"BaseExceptionGroup: errors during test teardown \(2 sub-exceptions\)",
                         "the refusal and One's boundary verdict are One.a's one teardown report: %s" % self.out)

    def test_the_test_under_the_repointed_build_passes_and_the_module_end_is_quiet(self):
        cls, method = self.LAST.split(".")
        self.assertEqual(outcomes(self.out).get(self.LAST), {"PASSED", "ERROR"}, "Two's verdict lands on its one test: %s" % self.out)
        self.assertIsNone(verdict(self.out, cls, method), self.out)
        self.assertIsNone(inherited(self.out, cls, method), "the build stands over a directory: no gone report: %s" % self.out)
        self.assertIsNone(boundary(self.out, ""), "tearDownModule put the refused object back, the module's start and end reads "
                          "agree on it, and the module end is quiet: %s" % self.out)


class TheRefusalNamesTheRootTheStartReadRecorded(_NestedRun, unittest.TestCase):
    """S11: S7 with the start read's object REPOINTED before the swap. One's setUpClass moves the import-time object's
    state_dir to a second sandbox (prefix repointed-), then saves, resets and moves jd.STATE as S7's class does, and its
    tearDownClass puts the object, jd.STATE and the state_dir back. At One.a's window the live attribute shows the
    repointed root while the start read recorded the kept one (prefix kept-), and the refusal names the root the start
    read RECORDED: rendered from the live attribute, it would name a root the start read never saw. Two.a meets the
    object put back over its kept root and is quiet; every boundary is quiet (One's start and end reads agree on the
    object and its state_dir text); one error. The kill cell is the start read's object rendered live
    (_sdk_singleton_text(be) in place of _sdk_singleton_text(be, start.sd)): the refusal then names the repointed root."""
    SCRATCH = SCRATCH_S11
    ERRORS = 1
    FIRST = "One.test_a_builds_over_the_class_root"

    def test_the_refusal_names_the_root_the_start_read_recorded_not_the_live_attribute(self):
        cls, method = self.FIRST.split(".")
        text = inherited(self.out, cls, method, head=SWAPPED)
        self.assertIsNotNone(text, "the first window's refusal line, opening with SWAPPED, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the allowed build over the class root is not accused: %s" % self.out)
        self.assertRegex(text, r"^SdkBackend over \S*/kept-\S+, jd.STATE \S+/romp at that read")   # the recorded root, and the run root
        self.assertNotIn("repointed-", text, "the live attribute's root is not the start read's: %s" % text)
        self.assertIn("(it holds None (not built))", text)
        self.assertNotIn("Fix:", text, text)
        self.assertNotIn(BOUNDARY, text)
        self.assertIsNone(re.search(r"test_scratch2?\.py::\w+", text), "no scope or test is named in the refusal: %s" % text)
        self.assertEqual(carriers(self.out, SWAPPED), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), set(), self.out)

    def test_every_boundary_is_quiet_and_the_later_test_is_quiet(self):
        for scope in ("::One", "::Two", ""):
            self.assertIsNone(boundary(self.out, scope), self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)
        self.assertRatchetPassed("Two", "test_a_meets_the_import_time_object")


class ASwappingClassThatLeavesItsOwnBuildInTheSlot(_NestedRun, unittest.TestCase):
    """S12: S6's import-time build over a kept root met first by a class whose setUpClass saves the singleton and jd.STATE
    and then BUILDS over a class root (prefix classroot-) in place of resetting the slot, so the slot holds a real object
    of the class's own at the worker's first window; tearDownClass puts both back. The identity term fails as in S7 and
    the refusal fires with the kept head, and its window value says what the slot holds: "(it holds SdkBackend over
    <class root>)", the branch of the render no other case executes (every other refusal meets a None in the slot).
    One.a's own window is quiet (the same object before and after, a cache hit), Two.a meets the import-time object
    and is quiet, every boundary is quiet, one error. The kill cell is the window value rendered as None whatever the
    slot holds. The render's second argument, the before read's recorded state_dir, is not a cell: the before read and
    the render are one fixture call with no test code between, so no run can tell it from the live attribute (annotated
    at the call in tests/conftest.py)."""
    SCRATCH = SCRATCH_S12
    ERRORS = 1
    FIRST = "One.test_a_finds_the_classes_build_in_the_slot"

    def test_the_refusal_says_the_slot_holds_the_classes_build(self):
        cls, method = self.FIRST.split(".")
        text = inherited(self.out, cls, method, head=SWAPPED)
        self.assertIsNotNone(text, "the first window's refusal line, opening with SWAPPED, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the cache hit is no transition: %s" % self.out)
        self.assertTrue(text.startswith("SdkBackend over "), text)                # the start read's object over the kept root
        self.assertRegex(text, r"\(it holds SdkBackend over \S*/classroot-\S+\)")  # the class's own build in the slot at the window
        self.assertNotIn("None (not built)", text, "the slot holds a real object here: %s" % text)
        self.assertNotIn("Fix:", text, text)
        self.assertNotIn(BOUNDARY, text)
        self.assertIsNone(re.search(r"test_scratch2?\.py::\w+", text), "no scope or test is named in the refusal: %s" % text)
        self.assertEqual(carriers(self.out, SWAPPED), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), set(), self.out)

    def test_every_boundary_is_quiet_and_the_later_test_is_quiet(self):
        for scope in ("::One", "::Two", ""):
            self.assertIsNone(boundary(self.out, scope), self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)
        self.assertRatchetPassed("Two", "test_a_meets_the_import_time_object")


class AScopeNamesTheObjectBeforeAnyWindowOpens(_NestedRun, unittest.TestCase):
    """S13, the refusal's named-object guard (_sdk_named in _sdk_swapped's condition), a module pair. Module 1's One
    has a setUpClass that builds over a kept sandbox, restores jd.STATE, leaves the build in the slot and raises SkipTest,
    so no function window opens in that module: pytest sets fixtures up by scope, the class boundary's start read runs at
    One's first item (the slot None), the setUpClass builds and skips, the function fixture never sets up, and the
    first-window flag stays armed. One's boundary end read finds the build and judges None to a real backend over a
    root that is not jd.STATE: the verdict lands as an ERROR on One.a's teardown (its call was SKIPPED) with the sandbox
    remedy, names the object, and module 1's end is quiet on the named object. Module 2 (the follower) opens the
    worker's FIRST function window at Two.a under S7's swapping class, the slot None while module 2's start read found
    the named object over its kept root: the identity term fails, the refusal is consulted with the flag armed, and it
    returns None only because a verdict has named the object. Three.a meets the object put back and is quiet. Two
    passed, one skipped, one error, no carrier of any head: one line per object. Measured with the named-object term
    dropped from the condition: a kept-head refusal on the follower's Two.a, a second line on the object module 1's
    class boundary already named, two errors. The _sdk_reported term beside it is a belt, not a cell: the one site that
    fills that list, the function fixture's report line, runs after the refusal is computed in the same first window,
    and no earlier window exists in the worker (the module docstring's unpinned list states it)."""
    SCRATCH = SCRATCH_S13
    FOLLOWER = SCRATCH_S13_FOLLOWER
    ERRORS = 1

    def test_the_skipping_classes_boundary_names_the_object_its_setup_built(self):
        # outcomes() reads PASSED, FAILED and ERROR and not SKIPPED, so the skip is read by a line anchored on the nodeid
        self.assertEqual(outcomes(self.out).get("One.test_a_never_runs"), {"ERROR"}, self.out)
        self.assertRegex(self.out, r"test_scratch\.py::One::test_a_never_runs SKIPPED")
        self.assertIsNone(verdict(self.out, "One", "test_a_never_runs"), "the skipped test is not accused as a test: %s" % self.out)
        found = boundary(self.out, "::One")     # assertBoundaryFailed asks for PASSED and ERROR; the scope's one test never ran
        self.assertIsNotNone(found, "One's class boundary names its setup's build: %s" % self.out)
        clause, fix = found
        self.assertTrue(clause.startswith("changed after its teardown: before None (not built), after SdkBackend over "), clause)
        self.assertNotIn(GONE, clause)
        self.assertIn(REMEDY_A, fix, fix)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py::One"}, self.out)
        self.assertIsNone(boundary(self.out, ""), "module 1's end is quiet on the object its class end named: %s" % self.out)

    def test_the_followers_first_window_takes_no_refusal_on_the_named_object(self):
        self.assertRatchetPassed("Two", "test_a_builds_over_the_class_root")
        self.assertRatchetPassed("Three", "test_a_meets_the_named_object")
        for head in (SWAPPED, SWAPPED_GONE, INHERITED, INHERITED_KEPT):
            self.assertEqual(carriers(self.out, head), set(), "the guard: one line per object: %s" % self.out)
        self.assertIsNone(inherited(self.out, "Two", "test_a_builds_over_the_class_root", head=SWAPPED), self.out)
        for scope in ("", "::Two", "::Three"):
            self.assertIsNone(boundary(self.out, scope, module="test_scratch2.py"), self.out)


class ASecondGoneObjectAfterTheRefusalCarriesNoLink(_NestedRun, unittest.TestCase):
    """S14, the link clause's negative control: a gone report on an object NO refusal named carries no clause, after a
    refusal in the same worker. S9's import-time gone leak and swapping class (One.a's first window refuses under the gone
    head, and One's tearDownClass puts the object back), then a class whose setUpClass builds over a sandbox of its own,
    restores jd.STATE and removes the sandbox (U's completed leak), leaving that SECOND gone object in the slot for its
    one test and putting the first back after it. Two.a carries the inherited gone report on the second object, whose
    root is not the refused one's, and the report says nothing about the refusal: _SDK_REFUSED holds the first object
    alone, and the clause is written on membership by identity (_sdk_refused). Two errors, every boundary quiet (Two's
    start and end reads agree on the refused object). The kill cell is membership by existence, the clause written
    whenever any refusal was taken in the worker (`if _SDK_REFUSED` in place of `if _sdk_refused(be)`): Two.a's report
    then says it is the object the first window refused to attribute, a false link, while the cases whose gone object
    is the refused one, or whose run took no refusal, stay green (derive: report-link-by-existence; a verifier's finding
    on the round-4 fixes: no case had a refusal on one object followed by a gone report on another)."""
    SCRATCH = SCRATCH_S14
    ERRORS = 2
    FIRST = "One.test_a_builds_over_the_class_root"
    LATER = "Two.test_a_meets_its_own_classes_gone_object"

    def test_the_report_on_the_second_object_carries_no_link_clause(self):
        cls, method = self.FIRST.split(".")
        refusal = inherited(self.out, cls, method, head=SWAPPED_GONE)
        self.assertIsNotNone(refusal, "the first window's refusal line, opening with SWAPPED_GONE, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the allowed build over the class root is not accused: %s" % self.out)
        report = self.assertInherited(*self.LATER.split("."))
        refused_root = re.match(r"SdkBackend over (\S+),", refusal).group(1)      # the refused object's root
        reported_root = re.match(r"SdkBackend over (\S+)\.", report).group(1)     # the second object's root
        self.assertNotEqual(refused_root, reported_root, "two objects over two removed roots: %s" % self.out)
        self.assertNotIn(REFUSED_OBJECT, report, "a link clause on an object no refusal named: %s" % report)
        self.assertIn("a class or module setup or teardown", report)                # the gone report's own cause family
        self.assertNotIn(REFUSED_OBJECT, refusal)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, INHERITED), {"test_scratch.py::" + self.LATER.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED), set(), self.out)

    def test_every_boundary_is_quiet(self):
        for scope in ("::One", "::Two", ""):
            self.assertIsNone(boundary(self.out, scope), self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)
        self.assertNotIn("sub-exceptions", self.out, "the two lines land on two items, no fold: %s" % self.out)


class ATestResetsTheSlotUnderTheRefusedObjectAndTheModuleEndFindsItChanged(_NestedRun, unittest.TestCase):
    """S15, the boundary link clause's placement pin: a test window whose before value is the refused object carries no
    clause, and the module end's start-to-end verdict on the same change does. S9's import-time gone leak and swapping
    class (One.a's first window refuses under the gone head; One's tearDownClass puts the object back), then Two.a,
    which starts under the gone object (the inherited gone report with its link to the refusal, as S9's Two.a) and
    resets the slot to None itself: its own verdict renders the refused object as before and None as after, with the
    object remedy, and says nothing about the refusal (the clause rides the boundary's start-to-end road alone, never
    _sdk_judge, which is this window's road too). The module end then finds the slot changed from the object it found
    to None: no window chain accounts for it (the first changing window, One.a's, starts from None, not from the found
    object), None is a value no verdict can name, so the start-to-end judgment renders the found object and None and
    carries the clause, and its tail is true here although the module swapped nothing: the slot no longer held the
    object at the module's end, and it held None. Both class ends are quiet (One's start and end reads agree on the
    object; Two's tests made its change, judged at Two.a's window). Two errors: One.a's refusal, and Two.a's teardown
    report, the gone report and its own verdict on the item and the module end's verdict beside them. Kill cell: the
    clause moved into _sdk_judge (derive: boundary-link-in-judge), under which Two.a's own verdict carries it."""
    SCRATCH = SCRATCH_S15
    ERRORS = 2
    FIRST = "One.test_a_builds_over_the_class_root"
    LATER = "Two.test_a_resets_the_slot_under_the_gone_object"

    def test_the_tests_own_verdict_on_the_refused_object_carries_no_clause_and_the_module_ends_does(self):
        cls, method = self.FIRST.split(".")
        refusal = inherited(self.out, cls, method, head=SWAPPED_GONE)
        self.assertIsNotNone(refusal, "the first window's refusal line, opening with SWAPPED_GONE, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the allowed build over the class root is not accused: %s" % self.out)
        refused_root = re.match(r"SdkBackend over (\S+),", refusal).group(1)      # the gone root the module start read recorded
        cls, method = self.LATER.split(".")
        report = self.assertInherited(cls, method, own=True)
        self.assertIn(REFUSED_OBJECT, report, "the gone report names the object as the one the refusal named: %s" % report)
        own, fix = verdict(self.out, cls, method)
        self.assertTrue(own.startswith("changed after its teardown: before SdkBackend over %s, after None (not built)" % refused_root),
                        own)
        self.assertTrue(own.endswith(", after None (not built)"), "the test's own verdict ends on the value it left: %s" % own)
        self.assertNotIn(REFUSED_OBJECT, own, "a test window whose before value is the refused object carries no clause: %s" % own)
        self.assertIn(REMEDY_B, fix, fix)
        found = boundary(self.out, "")               # read directly: assertBoundaryFailed holds the last test unaccused, and
        self.assertIsNotNone(found, "the module end's verdict lands beside Two.a's own: %s" % self.out)   # Two.a is accused here
        end, fix = found
        self.assertIn(REMEDY_B, fix, fix)
        self.assertTrue(end.startswith("changed after its teardown: before SdkBackend over %s, after None (not built). " % refused_root),
                        end)
        self.assertIn(REFUSED_FOUND, end, "the module end's start-to-end verdict says the object it found is the refused one: %s" % end)
        self.assertTrue(end.endswith(REFUSED_FOUND_TAIL), "the clause ends on its tail, no period inside it: %s" % end)
        self.assertNotIn(".. Fix:", self.out, "one period between the clause and the remedy: %s" % self.out)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, INHERITED), {"test_scratch.py::" + self.LATER.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED), set(), self.out)

    def test_both_class_ends_are_quiet_and_the_module_end_is_the_one_boundary_verdict(self):
        for scope in ("::One", "::Two"):
            self.assertIsNone(boundary(self.out, scope), self.out)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py"}, self.out)
        self.assertRegex(self.out, r"BaseExceptionGroup: errors during test teardown \(2 sub-exceptions\)",
                         "Two.a's report and the module end's verdict are Two.a's one teardown report: %s" % self.out)


class TheScopeThatFoundTheRefusedObjectEndsOnAReExecution(_NestedRun, unittest.TestCase):
    """S16, the boundary link's changed-marker term: the scope that found the refused object ends on the reload road,
    and its verdict carries no clause. E's import-time gone leak, then a class whose setUpClass resets the slot (S10's
    swap; One.a lazy-builds over the run root, allowed, and its first window refuses under the gone head) and whose
    tearDownClass re-executes the kernel and builds the new kernel's singleton over a sandbox, jd.STATE restored. The
    class end's marker differs from its start's, so the start-to-end judgment takes the reload road, which renders the
    after value alone against jd.STATE as the reload re-bound it (over a root that is not jd.STATE, the sandbox remedy)
    and no before value: a clause there would say the object the scope found is the refused one on a line that shows no
    found object, and the gate's changed-marker term keeps it off. The refusal and the verdict are One.a's one teardown
    report, one error; the module end is quiet on the object the class end named. Kill cell: the term dropped from the
    gate (derive: boundary-link-marker-term-dropped), under which the reload verdict carries the clause."""
    SCRATCH = SCRATCH_S16
    ERRORS = 1
    FIRST = "One.test_a_builds_over_the_run_root"

    def test_the_reload_verdict_beside_the_refusal_carries_no_clause(self):
        cls, method = self.FIRST.split(".")
        refusal = inherited(self.out, cls, method, head=SWAPPED_GONE)
        self.assertIsNotNone(refusal, "the first window's refusal line, opening with SWAPPED_GONE, is missing: %s" % self.out)
        self.assertEqual(outcomes(self.out).get(self.FIRST), {"PASSED", "ERROR"}, self.out)
        self.assertIsNone(verdict(self.out, cls, method), "the allowed build over the run root is not accused: %s" % self.out)
        self.assertIn("building the singleton over a directory since removed", refusal)
        clause = self.assertBoundaryFailed("::One", self.FIRST, remedy=REMEDY_A)
        self.assertTrue(clause.startswith("re-executed the kernel (or loaded it for the first time) and left the kernel's backend "
                                          "singleton (km._sdk_backend) over a root that is not jd.STATE: SdkBackend over "), clause)
        self.assertNotIn(REFUSED_OBJECT, clause, "the reload judgment renders the after value alone and no before; a clause here "
                         "would name an object the line does not show: %s" % clause)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py::One"}, self.out)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)
        self.assertRegex(self.out, r"BaseExceptionGroup: errors during test teardown \(2 sub-exceptions\)",
                         "the refusal and the reload verdict are One.a's one teardown report: %s" % self.out)
        self.assertEqual(carriers(self.out, SWAPPED_GONE), {"test_scratch.py::" + self.FIRST.replace(".", "::")}, self.out)
        self.assertEqual(carriers(self.out, SWAPPED), set(), self.out)


class SessionScopedFixtureInstallsBeforeTheModulesReads(_NestedRun, unittest.TestCase):
    """W: a session-scoped autouse fixture in the case directory's own conftest.py builds the singleton over a kept root
    and restores jd.STATE. It sets up before the module boundary's start read (the order a scratch run showed: the
    plugin's session fixtures, this conftest's session and package fixtures, the module start read, setUpModule, a
    module-scoped fixture of the module's own, the class start read, setUpClass, the function before-read), so the
    start read sees its object, the identity term holds, and the kept-root report on the first test names the cause
    family: import-time code, or a session- or package-scoped fixture. No read brackets a session fixture, so both
    boundaries are quiet: the first-window report's stated residual. At the round-3 head the report blamed import-time
    code alone."""
    SCRATCH = SCRATCH_W
    CONFTEST = CONFTEST_W
    ERRORS = 1

    def test_the_first_test_reports_the_fixtures_install_as_inherited_and_names_the_cause_family(self):
        text = self.assertInherited("Cases", "test_a_is_the_first_to_meet_the_fixtures_install", head=INHERITED_KEPT)
        self.assertTrue(text.startswith("SdkBackend over "), text)
        self.assertIn(", jd.STATE ", text)
        self.assertIn("a session- or package-scoped fixture", text)
        self.assertIn("import-time code did", text)

    def test_the_next_test_and_both_ends_are_quiet(self):
        self.assertRatchetPassed("Cases", "test_b_does_nothing")
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)


class ClassSetupBuildsOverAKeptSandboxAsTheWorkersFirstBuilder(_NestedRun, unittest.TestCase):
    """T: setUpClass makes the worker's first build over a kept sandbox and restores jd.STATE. The module boundary's
    start read saw None, so at One.a's window the object is not the one that read found, the kept-root inherited
    report is not taken (the identity term), and One's class boundary names the change from None with the sandbox
    remedy at One.b's teardown. At the round-3 head One.a carried the kept-root report blaming import-time code with
    no remedy, and its naming silenced the class boundary; with the identity term dropped the report returns and, the
    two naming lists being apart, the boundary verdict stays too, so the run counts two errors."""
    SCRATCH = SCRATCH_T
    ERRORS = 1

    def test_the_first_test_is_not_told_import_time_code_made_the_setups_object(self):
        self.assertRatchetPassed("One", "test_a_does_nothing_under_the_setups_object")
        self.assertIsNone(inherited(self.out, "One", "test_a_does_nothing_under_the_setups_object", head=INHERITED_KEPT), self.out)
        self.assertEqual(carriers(self.out, SWAPPED), set(), "no refusal on a first window whose start read saw None: %s" % self.out)

    def test_the_class_boundary_names_the_setups_build_with_the_sandbox_remedy(self):
        text = self.assertBoundaryFailed("::One", "One.test_b_does_nothing")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py::One"}, self.out)


class ALaterModulesClassMovesJdStateUnderAnUnnamedFirstBuild(_NestedRun, unittest.TestCase):
    """Z, the first-window flag's pin (a pair, one nested run): One.a's lazy first build passes unnamed; the follower's
    module start read sees that object, and its class Moved moves jd.STATE for its one test without building, so at
    Moved.a's window the singleton is the object the module's start read found and its state_dir is not jd.STATE, the
    picture the kept-root report names at the worker's FIRST window only. The flag says this is not that window, and
    nothing is said; with the flag ignored Moved.a gets a false report. Before the identity term N's Sandboxed pinned
    the flag; its object is not its module's start value, so that cell went dead and this run replaces it."""
    SCRATCH = SCRATCH_Z
    FOLLOWER = SCRATCH_Z2
    ERRORS = 0

    def test_the_first_build_passes_and_the_later_class_that_moved_jd_state_is_quiet(self):
        self.assertRatchetPassed("One", "test_a_the_lazy_first_build")
        self.assertRatchetPassed("Moved", "test_a_does_nothing_under_a_singleton_over_the_run_root")
        self.assertIsNone(inherited(self.out, "Moved", "test_a_does_nothing_under_a_singleton_over_the_run_root",
                                    head=INHERITED_KEPT), self.out)
        self.assertEqual(self.rc, 0, self.out)

    def test_every_boundary_is_quiet(self):
        for module, scope in (("test_scratch.py", "::One"), ("test_scratch.py", ""),
                              ("test_scratch2.py", "::Moved"), ("test_scratch2.py", "")):
            self.assertIsNone(boundary(self.out, scope, module=module), self.out)
        self.assertEqual(boundary_scopes(self.out), set(), self.out)


class ClassSetupCompletesALeak(_NestedRun, unittest.TestCase):
    """U: setUpClass builds over a sandbox, restores jd.STATE and removes the sandbox before any test. Two error lines
    for one leak: the inherited gone report on One.a (its cause clause already names a class or module setup) and One's
    class boundary at One.b's teardown, naming the change from None with the gone clause and the sandbox remedy. At
    the round-3 head the report's naming silenced the boundary (one list held both kinds of naming), so the leak was
    never attributed to the scope; the boundary's quiet rule now reads the verdict list alone."""
    SCRATCH = SCRATCH_U
    ERRORS = 2

    def test_the_first_test_reports_the_gone_object_as_inherited(self):
        text = self.assertInherited("One", "test_a_meets_the_gone_object_first")
        self.assertTrue(text.startswith("SdkBackend over "), text)
        self.assertIn("a class or module setup or teardown", text)
        self.assertNotIn(REFUSED_OBJECT, text, "no refusal preceded this report, so it names no refused object: %s" % text)
        for head in (SWAPPED, SWAPPED_GONE):
            self.assertEqual(carriers(self.out, head), set(), "no refusal beside the gone report: %s" % self.out)

    def test_the_class_boundary_names_the_setups_leak_with_the_gone_clause_and_the_sandbox_remedy(self):
        text = self.assertBoundaryFailed("::One", "One.test_b_does_nothing")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py::One"}, self.out)
        self.assertNotIn("sub-exceptions", self.out, "the two lines land on two items, no fold: %s" % self.out)


class ModuleSetupCompletesALeak(_NestedRun, unittest.TestCase):
    """V: the same leak completed by setUpModule, which runs after the module boundary's start read and before the
    class's: One.a carries the inherited gone report, One's class end is quiet (its start read saw the object) and the
    module end names the change from None at One.b's teardown with the gone clause and the sandbox remedy."""
    SCRATCH = SCRATCH_V
    ERRORS = 2

    def test_the_first_test_reports_the_gone_object_as_inherited(self):
        text = self.assertInherited("One", "test_a_meets_the_gone_object_first")
        self.assertIn("a class or module setup or teardown", text)
        self.assertNotIn(REFUSED_OBJECT, text, "no refusal preceded this report, so it names no refused object: %s" % text)
        for head in (SWAPPED, SWAPPED_GONE):
            self.assertEqual(carriers(self.out, head), set(), "no refusal beside the gone report: %s" % self.out)

    def test_the_module_boundary_names_the_setups_leak_and_the_class_end_is_quiet(self):
        text = self.assertBoundaryFailed("", "One.test_b_does_nothing")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)
        self.assertIsNone(boundary(self.out, "::One"), "the class end is quiet, its start read saw the object: %s" % self.out)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py"}, self.out)
        self.assertNotIn("sub-exceptions", self.out, self.out)


class ClassTeardownInstallsAValue(_NestedRun, unittest.TestCase):
    """M, class teardowns that install a value (the case list above), and the boundary link clause's negative with no
    refusal in the run (One.a opens the worker's first window holding the value its module start read found, None, so
    the identity term holds and the refusal is never consulted): none of the three boundary verdicts, each the
    start-to-end judgment, Two's on the object One.a built, Three's on the one Two's teardown built (both real) and
    Five's on None, names a refused object. The clause is written on membership by identity (_sdk_refused), and a clause
    emitted on every start-to-end verdict lands on all three here (the kill cell, derive: boundary-link-unconditional),
    while S10 and S10B, whose found object is the refused one, stay green."""
    SCRATCH = SCRATCH_M
    ERRORS = 3

    def test_no_verdict_names_a_refused_object_since_no_refusal_preceded(self):
        for head in (SWAPPED, SWAPPED_GONE):
            self.assertEqual(carriers(self.out, head), set(), "no refusal in this run: %s" % self.out)
        for scope in ("::Two", "::Three", "::Five"):
            found = boundary(self.out, scope)
            self.assertIsNotNone(found, "the boundary verdict names the scope %r: %s" % (scope, self.out))
            self.assertNotIn(REFUSED_OBJECT, found[0], "a link clause on a verdict whose found object no refusal named: %s" % found[0])

    def test_a_teardown_that_builds_over_a_sandbox_is_named_at_the_class_boundary(self):
        text = self.assertBoundaryFailed("::Two", "Two.test_a_does_nothing")
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertIn(", after SdkBackend over ", text)
        self.assertNotIn(GONE, text)
        self.assertNotIn(REBUILT, text, "another root, not a rebuild over the same one: %s" % text)

    def test_a_teardown_that_resets_the_slot_to_none_is_named_with_the_object_remedy(self):
        text = self.assertBoundaryFailed("::Three", "Three.test_a_does_nothing_under_twos_object", remedy=REMEDY_B)
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertTrue(text.endswith(", after None (not built)"), text)
        _, fix = boundary(self.out, "::Three")
        self.assertNotIn(SANDBOX, fix, fix)
        self.assertRatchetPassed("Four", "test_a_does_nothing_under_none")
        self.assertIsNone(boundary(self.out, "::Four"), "a class that inherits the None and does nothing is quiet: %s" % self.out)

    def test_a_teardown_that_builds_from_none_is_named_and_the_module_end_is_quiet_on_it(self):
        text = self.assertBoundaryFailed("::Five", "Five.test_a_does_nothing_under_none")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)
        self.assertRatchetPassed("Six", "test_a_does_nothing_under_fives_object")
        self.assertIsNone(boundary(self.out, "::Six"), self.out)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the object the class end named: %s" % self.out)


class ClassTeardownPutsBackAnObjectWhoseDirectoryItRemoved(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_P
    ERRORS = 2

    def test_the_leak_over_the_kept_sandbox_is_named_at_its_own_window(self):
        text = self.assertRatchetFailed("One", "test_a_leaks_over_a_kept_sandbox")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertNotIn(GONE, text)

    def test_the_put_back_of_the_found_object_over_a_removed_directory_is_named_at_the_class_boundary(self):
        # Two.a's lazy build over the root the class moved to passes at its own window; Two's one case is its last, so the
        # boundary verdict lands on it (PASSED for the call, ERROR at the teardown), and no test verdict names it.
        text = self.assertBoundaryFailed("::Two", "Two.test_a_builds_over_the_class_root")
        self.assertTrue(text.startswith(PUT_BACK_GONE + "SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)

    def test_the_class_that_inherits_the_gone_object_is_quiet(self):
        self.assertRatchetPassed("Three", "test_a_does_nothing_under_the_gone_object")
        self.assertIsNone(boundary(self.out, "::Three"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class ValuesOnTheOtherRoads(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_G
    ERRORS = 2

    def test_a_look_alike_claiming_the_kernels_module_is_refused_and_rendered_module_qualified(self):
        text = self.assertObjectRoad("Cases", "test_a_a_look_alike_claiming_the_kernels_module_as_the_workers_first_value_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after romp_sdk_backend.Fake over "), text)
        self.assertNotIn(GONE, text)

    def test_a_reexecution_that_leaves_a_value_that_is_not_the_kernels_build_is_named(self):
        text = self.assertObjectRoad("Cases", "test_b_a_reexecution_then_a_simplenamespace_left_fails")
        self.assertTrue(text.startswith(REEXEC + " as a value that is not the kernel's build: types.SimpleNamespace over "), text)
        self.assertNotIn("changed", text)

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class ARepointedStateDir(_NestedRun, unittest.TestCase):
    """X: the same object with its state_dir text changed, at the three places the reads compare it. One.b repoints the
    singleton One.a built at a kept sandbox and leaves it (named at its own window with the changed wording, both sides
    from the recorded text since the live attribute shows the after path on both, no gone clause, the repoint remedy);
    One.c repoints and puts the state_dir back (quiet); Two's tearDownClass repoints the object its test left (the
    class boundary, before its quiet rules, on an object a verdict already named); Three's setUpClass saves and
    replaces the singleton and moves jd.STATE, Three.a builds over the class root (allowed at its own window), and its
    tearDownClass puts the saved object back with its state_dir repointed (the put-back-repointed branch). At the
    round-3 head the run was 4 passed, exit 0, and no window said anything: the same-object road compared isdir alone,
    although the readers hold the object and read its state_dir on every registry scan."""
    SCRATCH = SCRATCH_X
    ERRORS = 3

    def test_a_repoint_left_in_place_is_named_at_its_own_window_with_the_repoint_remedy(self):
        method = "test_b_repoints_the_singleton_it_found_at_a_kept_sandbox_and_leaves_it"
        text = self.assertRatchetFailed("One", method, remedy=REMEDY_C)
        m = re.match(r"changed after its teardown: before SdkBackend over (\S+), after SdkBackend over (\S+)$", text)
        self.assertIsNotNone(m, text)
        self.assertNotEqual(m.group(1), m.group(2), "both sides come from the recorded text, not the live attribute: %s" % text)
        self.assertNotIn(GONE, text)
        self.assertNotIn(REBUILT, text)
        _, fix = verdict(self.out, "One", method)
        self.assertNotIn(SANDBOX, fix, fix)
        self.assertNotIn(REMEDY_A, fix, fix)
        self.assertNotIn(REMEDY_B, fix, fix)

    def test_a_repoint_put_back_is_quiet(self):
        self.assertRatchetPassed("One", "test_c_repoints_and_puts_the_state_dir_back")
        self.assertIsNone(boundary(self.out, "::One"), self.out)

    def test_a_teardown_that_repoints_the_object_its_test_left_is_named_at_the_class_boundary(self):
        text = self.assertBoundaryFailed("::Two", "Two.test_a_does_nothing_under_the_repointed_object", remedy=REMEDY_C)
        self.assertTrue(text.startswith("changed after its teardown: before SdkBackend over "), text)
        self.assertIn(", after SdkBackend over ", text)
        self.assertNotIn(GONE, text)

    def test_a_put_back_with_the_state_dir_repointed_is_named_at_the_class_boundary(self):
        text = self.assertBoundaryFailed("::Three", "Three.test_a_builds_over_the_class_root", remedy=REMEDY_C)
        self.assertTrue(text.startswith(PUT_BACK_REPOINTED + "SdkBackend over "), text)
        self.assertNotIn(GONE, text)
        self.assertIsNone(boundary(self.out, ""), "the module end is quiet on the named object: %s" % self.out)
        self.assertEqual(boundary_scopes(self.out), {"test_scratch.py::Two", "test_scratch.py::Three"}, self.out)


class FirstBuildThenTheRunRootRemoved(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_R1
    ERRORS = 1
    JUDGE_RED = True

    def test_the_ratchet_names_the_gone_root_with_the_sandbox_remedy_beside_the_judges_verdict(self):
        text = self.assertRatchetFailed("Cases", "test_a_the_first_build_then_the_run_root_removed_fails")
        self.assertTrue(text.startswith("changed after its teardown: before None (not built), after SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), "the allowance asks for a directory, and this one is gone: %s" % text)
        self.assertIn(SHARED_STATE, self.out, "the judge fixture names the removed root in the same teardown")
        self.assertIn("was a directory and is gone", self.out)
        self.assertRegex(self.out, r"errors while tearing down <TestCaseFunction test_a_\w+> \(2 sub-exceptions\)")

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


class ReexecutionThenTheRunRootRemoved(_NestedRun, unittest.TestCase):
    SCRATCH = SCRATCH_R2
    ERRORS = 1
    JUDGE_RED = True

    def test_the_reload_road_names_the_gone_root_with_the_sandbox_remedy_beside_the_judges_verdict(self):
        text = self.assertRatchetFailed("Cases", "test_a_a_reexecution_the_lazy_build_then_the_run_root_removed_fails")
        self.assertTrue(text.startswith(REEXEC + " over jd.STATE, which is no longer a directory: SdkBackend over "), text)
        self.assertTrue(text.endswith(", " + GONE), text)
        self.assertIn(SHARED_STATE, self.out)
        self.assertIn("is not a directory after the test reloaded the judge", self.out)
        self.assertRegex(self.out, r"errors while tearing down <TestCaseFunction test_a_\w+> \(2 sub-exceptions\)",
                         "the ratchet's verdict and the judge's fold into one exception group on the one item")

    def test_the_class_and_module_ends_are_quiet_on_the_named_object(self):
        self.assertIsNone(boundary(self.out, "::Cases"), self.out)
        self.assertIsNone(boundary(self.out, ""), self.out)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--derive":        # the derivation of a cell's red set (or every cell's)
        for name in (sorted(MUTATIONS) if sys.argv[2] == "all" else [sys.argv[2]]):
            derive(name)
            print()
    else:
        unittest.main()

#!/usr/bin/env python3
"""No test writes a fixed port in the ephemeral range (2026-10-03).

WHY. tests/test_postal_token.py's PeerTokenPlumbing pointed a peer at the fixed loopback port 45001 with up: true. The
bus then starts a real dialer (_peer_loop), whose exchange POSTs to that port with a timeout of EXCHANGE_WAIT + 10, 30 s by
default. 45001 is inside the range the system hands out as source ports and as the ports of bind(0), so any process on
the machine can hold a listener there: another xdist worker, another checkout's sweep, a served lab. When nothing
listens, the dial is refused at once. When a listener accepts and never answers, the dialer sits inside its request, the
wake that ends it cannot reach it, and the test's cleanup, which waits 10 s for the dialer to end, fails for a reason
outside the test (a sweep's red, reproduced with a planted silent listener). A fixed port below that range is no fix:
the machine's own services listen there (the postal bus on 25302, the kernel on 29855). tests/test_postal_peer_tier.py
already used the fix: a test that needs a dial that never lands names port 1. On Linux at the default nothing
unprivileged can listen below 1024, and by convention nothing listens on port 1, so in practice a dial there is refused
at once; where a test needs several distinct ports (a tunnel row's local, bus and reverse ports), each takes its own
number below 1024 (1, 2, 3 and so on). A test that needs a real listener takes its port from the system: a bind to port
0, or tests/lab_ports.py's reserve() for a kernel.

THE RANGE is 32768-65535 (LOW, HIGH): the union of Linux's default ephemeral range, 32768-60999 (a machine can change
it in /proc/sys/net/ipv4/ip_local_port_range; CI's ubuntu-latest runners are Linux at the default), and the range
macOS hands out, 49152-65535 (CI's macOS cells).

THE FILES are derived by walking the checkout (files()): every regular file under tests/, fixtures included, and every
file named *.test.* or under a directory named fixtures anywhere else, outside node_modules, dist, out, site, venv,
__pycache__ and every hidden directory (.git; .claude, where a clone may keep worktrees of other commits; .venv). A
symlink is skipped (its target is read where it lives, if that is in THE FILES). A file that is not UTF-8 text is
skipped, and the census fails if the walk finds no files, no Python file with a number in the range, no product function
to resolve a call against, or no module under tests/ that a read module imports, so it never passes on nothing. A file
is opened only when its text, as written, holds anywhere (a comment included) a five-digit number in the range standing
alone, with no dot, no underscore and no character str.isalnum() accepts against either end (digit separators allowed:
45_001), or, for Python, one of the computed forms below as text: a % followed, after any spaces or tabs, by four or
five digits (% 20000; not % 20_000 or % (20000)), or randint, randrange or randbelow with the parenthesis right after
the name (randint( opens a file, randint ( does not). Every rule reads an open file, so a port computed from smaller
constants alone (30000 + 5000) is read only in a file something else opens. A digit, here and in THE RULE, is any
Unicode decimal digit (what Python's regular expressions match as a digit), so Arabic-Indic and fullwidth digits count
as ASCII ones do.

THE RULE. A number in the range counts when it is WRITTEN AS A PORT: a value of one of the forms below, in one of the
positions below. This section states what the census reads. A name is BOUND, here and below, by the bindings the census
records: a constant, a number written with a sign (-7, +7, -7.0, which Python parses as a unary minus or plus over a
constant, recorded as the number Python computes), or a list, tuple or set display, given to the name anywhere in the
module by =, an annotated = or :=, by a tuple or list assignment element by element, or by a for loop or a
comprehension over a display. Any other binding of the name adds no value: every other place Python's grammar binds a
name, read from the ast (a call's result, B = A, 0 - 7, an augmented assignment, a starred target, a for target over
anything but a display, a with or except target, a parameter, an import, a function's or class's name, a del, a global
or nonlocal statement, a match capture), and any binding form the census does not classify, which it counts among
these (unrecorded_bindings()). Such a binding takes no value away from the hop, a host, a template or offset_base()
(HOST = "127.0.0.1", then HOST = os.environ["H"], leaves HOST a host), nor, anywhere but at a randrange's step, from
interval(), which reads every name by the ints the census records for it, whatever its other bindings (K bound to 7
and to 9 reads 7-9, and so does K bound to 7, to 9 and by K = f()). At a step, and anywhere inside one, interval()
bounds a name only when the census records every binding of it and each gives an int, so that K is unbounded there
once K = f() binds it too. A star import, which binds names the module's text does not write, counts as such
a binding of every name in its module. A position's value that reads a name with such a binding is read twice, by
the name's recorded ints and with the name unbounded, and counts by either reading, their union: with K bound to 7 and
by K = f(), 20000 + K % 20000 reads 20007 and, as an unknown operand of % by 20000, 20000-39999, and 40000 + K reads
40007 and is a sum built on 40000 (offset_base(), below); where the value gives no reading with the name unbounded (a
bare name at a randrange's start or stop), the reading by its recorded ints stands alone. A value that reads several
such names is read once for each mix of the two ways, each name by its ints or unbounded, 2**k readings for k names:
with BASE bound to 20000 and by BASE = g(), and OFFSET bound to 7 and by OFFSET = f(), BASE + OFFSET % 20000 reads
20000-39999, BASE by its int and OFFSET unbounded. A value that reads more than eight such names, more than 256 mixes
(MIXES), is refused: the census counts it, naming the names, an over-refusal wherever no mix reaches the range, since
reading it by spans or by fewer mixes could miss (a name read unbounded gives no interval at all, so a mix left out can
be the one reading that counts). So interval(), anywhere but at a step, reads each int a binding the census records
gives a name, and not a value a binding it does not record gives, unless the value bounds that name's every value as
these do, nor a float or a string a binding it records gives, which it reads only inside int(), as CPython's int() of
it, nor a None, which it reads only at a randrange's stop, as the stop left empty (both below; WHAT IT CANNOT SEE gives
examples); the hop counts every value recorded, a string wherever a string counts. Inside a class Python reads a name
written with two leading underscores and not two trailing ones as another (__K in class C is _C__K), so a binding of
either spelling binds the name a read of the other sees: once such a name is written anywhere in a class statement, the
census counts both spellings among the names with a binding it does not record, wherever the module reads them, unless
the class's name is underscores alone, which mangles nothing. The spelling with the two underscores (__K) then reads,
wherever the module reads it, in interval(), offset_base() and the hop (a host and a template read the spelling
written), by the values the census records under it and under the spelling each class it is written in mangles it to
(the class's name less its leading underscores): with _C__K bound to 45001, __K read in a method of C reads 45001, as
CPython does. That is an over-read where the module reads __K outside C, or in a class nested in C, which CPython
mangles by the innermost class alone; the spelled-out _C__K reads its own values only. A name a module sets with no
binding form (globals()["K"] = f(), exec("K = f()"), setattr(sys.modules[__name__], "K", f()), or mod.K = f() in another
module) has no binding here, and the census does not see the value such a setting gives it (WHAT IT CANNOT SEE).
  In Python, read by AST (scan_python), the positions:
    a value under a dict key that names a port ({"port": N}, {"local_port": N}, {"busPort": N}; a key names a port when
    one of its words, split at underscores, other punctuation and camelCase, is "port" or "ports": "report" does not;
    the key is a string, or a bare name judged by the name itself, so {BUS_PORT: N} counts whatever BUS_PORT holds);
    a keyword argument that names a port (bus_port=N, ROMP_POSTAL_PORT="N");
    the value assigned to a target that names a port, by =, an annotated =, := or an augmented assignment (PORT = N,
    km.BUS_PORT = N, os.environ["ROMP_POSTAL_PORT"] = "N", port += N); a tuple or list target is read element by
    element against a tuple or list value of its length (h, port = "x", N);
    the default of a parameter that names a port (def _notify(self, host, up, port=N));
    a positional argument whose parameter names a port, in the functions the callee resolves to. An attribute call on a
    tests/ module the module imports (import helpers, import tests.helpers as h, or from tests import helpers; then
    helpers.dial or h.dial) resolves to that module's function (HelperModules). Any other callee resolves by its name
    alone, whatever it is called on: to the module's own function of that name (code text included, below); else, for
    a bare name the module imports from a tests/ module (from helpers import dial, from tests.helpers import dial, or a
    star import), to that module's function; else to every function of that name in the .py files directly under
    kernel/, postal/ or cli/ (not their subdirectories), a name a tests/ module only re-exports included
    (km._notify_bus_peer("h", N, True); vendorlib.ring(N) resolves to every product function or method named ring).
    import tests.helpers without as, then tests.helpers.dial, and a relative import, give no tests/ module, so their
    callees resolve by name alone like any other. A first parameter named self or cls is skipped; a *ports parameter
    takes every extra argument;
    an element of a list, tuple or set display that a for loop or a comprehension walks, under a target that names a
    port (for host, port in (("h", N),): the element at the port's index);
    the second argument of a call whose first argument is a string that names a port (os.environ.setdefault(
    "ROMP_POSTAL_PORT", "N"), monkeypatch.setenv);
    the port of an address, a tuple or list whose first element is a HOST and whose second is the port, read in every
    tuple or list the module writes, an unpacking target included (HOST, X = pair() counts X's values): a
    loopback or wildcard literal ("127.0.0.1", "localhost", "0.0.0.0", "::1", "::" or ""), or a name the module binds
    only to such literals, the empty one aside (HOST = "127.0.0.1"): ("127.0.0.1", N), (HOST, N);
    the positional argument right after a host in a call, the empty string aside (http.client.HTTPConnection(
    "127.0.0.1", N, timeout=30), asyncio.open_connection(HOST, N));
    an operand formatted into an address (below), by %, by an f-string or by a .format() call on the template, whose
    template (a str literal; for % and format, also a name bound to exactly one str literal; never bytes, and never
    str.format(t, N)) puts an address, then a colon before the operand
    ("http://127.0.0.1:%d/" % N, "http://%s:%d/" % (h, N), f"http://127.0.0.1:{P}/", f"ws://{h}:{P}/",
    "http://127.0.0.1:{}/".format(N)); for %, the template holds an address whose colon is followed at once by a plain
    %d, %i or %s, and then the whole right operand is read, each element of a tuple, whatever placeholder it fills;
    for format, a field takes the operand str.format gives it (by its number, its name or the next automatic number),
    and takes its automatic number before the fields nested in its format spec take theirs, so
    "http://{:{}}:{}/".format(h, w, N) reads N, and "http://{:{}}:{}/".format(h, N, 1) reads nothing. A field is
    numbered when its name before any . or [ is decimal digits alone (str.isdecimal(), the test str.format makes), so
    an Arabic-Indic digit numbers a field and a superscript digit, which str.isdigit() accepts, names one, as
    str.format reads them. Such a name takes the keyword argument of that name, which a call can pass only in a **
    mapping (no identifier holds a superscript digit), one the format reading does not open, so its operand is not
    read; and as it is no numbered field, an automatic field beside it takes the operand str.format gives it. A format
    template is not read when string.Formatter().parse refuses its text or a field's format spec, when a field nested
    in a spec has an opening brace in its own spec ("http://{:{:{}}}:{}/", where str.format refuses a field nested two
    deep), or when automatic fields ({}) and numbered ones ({1}) mix ("http://{}:{1}/", where str.format refuses the
    switch). Nothing else that str.format refuses is checked, so a template it refuses for any other reason still has
    its port's operand read: a field with no operand ("http://{}:{}/{}".format(h, N) reads N), an unknown conversion, a
    spec an operand refuses;
    a port concatenated onto an address: the right operand of a + whose left side, read as text (string literals, names
    bound to one, f-strings' literal parts) with every other operand as a placeholder, ends in an address, then a colon
    ("http://127.0.0.1:" + str(N), "http://" + host + ":" + P);
    an element of a list or tuple display right after a string element that is a --*port option whole: -- and a name
    (word characters and dashes, in parts a dot may join) one of whose words is port or ports, so --port, --bus-port,
    --ports, --port-file and --server.port alike (an argv: ["romp", "serve", "--port", "N"], ("--bus-port", N)).
  The values that count, in any of those positions, and no others:
    an int in the range (45_001 is 45001);
    a str (not bytes) that is five digits once str.strip() has taken off any leading and trailing whitespace ("N",
    " N ", "45_001", in any decimal digits, THE FILES), except that such a str constant, written there or reached by
    the hop, is not read as a positional argument (by its parameter or after a host) or as the port of an address: a
    string handed to a function by position is that function's input text, not a setting (km._notify_bus_peer("h",
    "N", True) is not counted, where km._notify_bus_peer("h", N, True) is), and a socket address takes its port as an
    int. The exception is for the constant alone: str(N) there is an expression interval() bounds, and counts; and it
    belongs to those positions, so ("127.0.0.1", "N") assigned to a port-named target is a display in the assignment's
    position, and its digit string counts;
    a list, tuple or set display, each element read by these same terms ({"ports": [N, 1]});
    an expression interval() bounds that can reach the range, or a sum or difference offset_base() finds built on a
    constant expression in the range (both below);
    a bare name, by one hop, in every position but a loop's sequence: it counts each value it is bound to (BOUND,
    above), each read by these same terms (P = N ... {"port": P}). So a name bound twice counts both values, a digit
    string counts wherever a string does (P = "N", then ["romp", "--port", P]), and a name bound to a display counts its
    elements, a name among them through interval() (two hops: A = N, L = [A], then {"ports": L}). The hop is taken
    wherever the position's own value is the bare name, the positions that are themselves elements of a display
    included: a tuple assignment's element (h, port = "x", P), the port of an address ((HOST, P)) and the element after
    a --*port option. A name inside a display that is the position's value ({"ports": [P]}, the tuple a % formats), and
    a name in a loop's sequence, counts only through interval(), which reads a name by the ints the census records
    for it, written with or without a sign (BOUND).
  An address is a loopback or wildcard host (127.0.0.1, localhost or 0.0.0.0 with no underscore and no character
  str.isalnum() accepts against either end; [::1]; [::]) or // and a run of word characters, dots and dashes, standing
  right before the colon, with spaces or tabs allowed on either side of the colon except in a %-template; in that run a
  %-template may also put %s, and an f-string, a format template or a concatenation a placeholder (a field, or an
  operand not read as text).
  For the f-string, format and concatenation rules the text must end at the colon and any spaces or tabs after it, so a
  newline after the colon ends the address ("http://127.0.0.1:" and a newline, then + str(N), is not read), and a NUL
  character the source writes is read as an ordinary character, never as a placeholder ("http://", a NUL and a colon,
  then + str(N), is not read).
  An expression counts when it is bounded and can reach the range: interval() bounds int constants; anywhere but at a
  randrange's step, a name by the ints the census records for it, signed or not, whatever its other bindings, as the
  span from the lowest to the highest, which holds each one's reading (with P bound to 1 and to 45001, P is 1-45001 and
  P + 1 is 2-45002; an over-read where those ints lie on both sides of the range and none in it), and, where P = f()
  binds it too, also as unbounded, the two readings' union (BOUND); at a step, a name every binding of which the
  census records, each to an int, as the same span; int() of a name, as the span of CPython's int() of each value the
  census records for it, a float or a string included and a value int() refuses passed over (with P bound to "45001",
  or to 45001.0, or to "x" and to "45001", int(P) is 45001), except at a step, where a name with a value other than an
  int is unbounded, int() around it too; int() of a constant, as CPython's int() of it, a constant int() refuses not
  read (int("45001"), int(" 45_001 "), int(45001.0) and int(b"45001") are 45001, and int("45001.0") is not read); in
  offset_base(), below, a name by each value the census records for it in turn; and, over bounded operands, str() and
  int(), a unary minus or plus (-7, +7), + - and *, and // and % by a divisor read by its positive part, from the
  greater of its lowest value and 1 up to its highest, and its negative part, from its lowest value up to the lesser of
  its highest and -1, each a part only where it holds a value, as the span holding both parts' readings. 0, for which
  Python raises, is in neither part, so no reading divides by it, and a divisor that is 0 alone, or a reversed one
  (below) whose ends lie on either side of 0, is not read. By a part, // is the span from the least to the greatest
  quotient of an end of its left operand by an end of the part (90002 // K, with K bound to 2, to 3 and by K = f(), is
  30000-45001, and with K bound to -1 and to 2 it is -90002-90002), and % is the remainder where the left operand and
  the part are one value each, and otherwise 0 to the part's highest value less one for a positive part and the part's
  lowest value plus one to 0 for a negative one, as Python's remainder takes the divisor's sign (50000 % K, with K bound
  to 60000, to 70000 and by K = f(), is 0-69999, and 80000 + os.getpid() % -40000 is 40001-80000). Over operands never
  negative it reads ** and << and >> as the span from the least to the greatest value of the operator over their ends (2
  ** 15 + 1000 is 33768, and random.randint(2 ** 15, 2 ** 16 - 1) is 32768-65535), unless a ** or a << can pass 2**4096
  (BIG), and &, | and ^ as Python's own value where each operand is one value (40000 | 1 is 40001) and otherwise as 0 up
  to the lesser of the operands' highest values for &, and up to 2**n - 1 for | and ^, n the bit length of the greater;
  over any bounded operand, ~ as -x - 1 (~-45002 is 45001); not as 0 to 1, whatever its operand, and as its one value
  where the operand has one; a conditional expression as the span holding its two branches (45001 if x else 45002 is
  45001-45002); and a := as its value. True division, which gives a float, is not read, nor are **, <<, >>, &, | and ^
  over an operand that can be negative (WHAT IT CANNOT SEE), and Operators checks that each operator of Python's grammar
  is read here or named as not read (OPERATOR_LIMITS). It reads an unknown operand of % by a divisor so too, by each
  part as for a left operand of several values, and a call to randint(a, b), randrange(stop), randrange(start, stop[,
  step]) or randbelow(n) over bounded arguments (random's and secrets', by the callee's name; a randrange's step may be
  unbounded, below) as the values it can return, so 20000 + os.getpid() % 20000 is 20000-39999 and counts, and so does
  random.randint(40000, 50000). A call Python always refuses can give a span whose ends are reversed
  (random.randint(50000, 40000) is 50000-40000), and such a span counts when both its ends lie in the range; as a
  divisor it reads by its parts, so 90002 // random.randint(3, 2) is 30000-45001, an over-read, and 90002 //
  random.randint(1, 0) is not read. Each argument of one of these random calls is given by position or by its
  parameter's name (randint's a and b, randrange's start, stop and step, randbelow's exclusive_upper_bound; a keyword
  that names none is passed over), and the call is read by the arguments that fill its parameters from the first up to
  the first left empty: random.randint(a=40000, b=50000) counts as random.randint(40000, 50000) does, randrange(start=S)
  reads as randrange(S), and neither randint(b=N) nor randrange(stop=E) is read. A call spelled on a name or attribute
  called Random or SystemRandom takes its first positional argument as the instance (random.Random.randrange(rng, 40000,
  50000) is 40000-49999, and so is the call with start= and stop= after rng). The class is known by that name alone, as
  the random calls are by the callee's name, so a call spelled on Random imported by name or on mymod.SystemRandom drops
  its first argument too, whatever that name holds (WHAT IT CANNOT SEE). A ** mapping names no parameter, yet can fill
  any parameter left empty: beside a randrange's start and stop, with its step left empty, it is read as a step
  interval() does not bound (below), and beside any other parameter left empty the call is not read, since what the call
  returns then depends on what the mapping holds (random.randrange(30000, **kw) returns values up to 29999 when kw is
  empty, and up to 49999 when kw holds a stop of 50000). A call with an argument passed through a * sequence
  (random.randrange(*(40000, 50000))) is not read. Two shapes Python refuses for the way the arguments are passed are
  not read: a keyword that names a parameter a positional argument fills (random.randint(40000, 50000, a=1)), and a
  randrange whose stop is left empty and whose step is anything but the int 1 (random.randrange(start=50000, step=7);
  Python tests that the step is the int 1 itself, so it refuses True). A step of 1, randrange's default, is the one step
  Python takes without a stop, however it is computed: the int 1 written there reads as randrange(S)
  (random.randrange(start=50000, step=1) reads as randrange(50000)), and a step that is 1 only at run time (a name bound
  to 1, +1, int(1)) is not read (WHAT IT CANNOT SEE). A stop written as None, randrange's own default, is a stop left
  empty, once a keyword that repeats it is refused: random.randrange(50000, None) and random.randrange(50000, None, 1)
  read as randrange(50000), while random.randrange(50000, None, 7) and random.randrange(40000, None, stop=50000), which
  Python refuses, are not read. A stop that is a name a binding the census records gives None is read so too, with its
  step left out or the int 1 written there, and the call reads as the span holding that reading and the one by the
  name's ints: with E bound to None, random.randrange(45001, E) reads as randrange(45001), 0-45000, and so does
  random.randrange(45001, F) with F bound to 1000, to None and by F = f(), the span holding randrange(45001, 1000)'s
  reading and randrange(45001)'s. A randrange(start, stop[, step]) whose start and stop are bounded is read by one rule,
  whether or not interval() bounds its step (a step left out is 1, and one a ** mapping can give is unbounded): a
  positive step returns values from start up to stop less one, a negative step values from stop plus one up to start,
  and a step of 0 raises. So, with start from s_lo to s_hi and stop from e_lo to e_hi, a step that is never negative is
  read as s_lo to e_hi - 1, any other step that is never positive as e_lo + 1 to s_hi, and every remaining step, one
  that can take either sign or one interval() does not bound, as the span holding both, min(s_lo, e_lo + 1) to max(s_hi,
  e_hi - 1). random.randrange(40000, 50000, k) is 40000-49999, by keyword too (random.randrange(40000, stop=50000,
  step=k)); random.randrange(50000, 40000, k) and random.randrange(50000, 40000, -7) are 40001-50000;
  random.randrange(40000 + os.getpid() % 61, 40020 + os.getpid() % 21, k) is 40000-40060, and 40021-40060 with a step of
  -7; random.randrange(40000, 1000, K), with K bound to 7 and by K = f(), is 1001-40000, and random.randrange(S, 50000),
  with S bound to 40000 and by S = f(), is 40000-49999; and random.randrange(30000 + os.getpid() % 5000, 30000, **kw) is
  30000-34999 whatever kw holds, by keyword too (random.randrange(start=30000 + os.getpid() % 5000, stop=30000, **kw)).
  Each reading holds every value random's randrange can return for the call, except where a name it takes a value for is
  also set with no binding form, or a name called Random or SystemRandom holds an instance (both in WHAT IT CANNOT SEE),
  or a binding the census does not record gives a name in its start or stop a value it does not read (BOUND), or a
  binding the census records gives such a name a value interval() does not read and the call takes: a None at a stop
  beside a step that is 1 only at run time, or a float, which randrange takes on 3.10 and 3.11 (each in WHAT IT CANNOT
  SEE); and it can hold values it never returns (a step of 7 returns values 7 apart). At a step it takes a value for a
  name only when the census records every binding of it, each to an int. Where Python refuses a call for every value its
  start, stop and step can take, the reading still stands, an over-read: a step of 0 is read with the steps that are
  never negative (random.randrange(40000, 50000, 0) is 40000-49999); a positive step from a start never below its stop,
  or a negative one from a start never above it, is read as a span with its ends reversed (random.randrange(50000,
  40000, 7) is 50000-39999, and random.randrange(40000, 50000, -1) is 50001-40000); and a start and stop that are one
  and the same value, with a step that can take either sign or one interval() does not bound, read as that value
  (random.randrange(40000, 40000, k) is 40000-40000, and so is the call with a step of os.getpid() % 3 - 1).
  RandrangeAgainstCPython checks this reading against CPython's own randrange over generated calls. A sum or difference
  with an unbounded operand counts when one of its operands alone is a constant expression (one interval() bounds with
  no unknown in it) whose value is in the range, found through str(), int() and a unary plus and down a chain of sums
  and differences: 40000 + i is built on 40000, and so is 40000 * 1 + i (offset_base()); one with no such operand (base
  + i) is not read. A name in that operand is read by each value the census records for it in turn, whatever its other
  bindings, a value other than an int adding nothing but inside int(): BASE + i, with BASE bound to 40000, or to 40000
  and to 50000, or to 1000 and to 40000, or to 40000 and to "x", with or without BASE = f() beside them, is built on
  40000, and so are BASE * 1 + i and, with BASE bound to "40000" and to "50000", int(BASE) + i. Where the names of one
  operand can take their values more than 256 ways (EACH), the operand is read once instead, each name holding every
  value it is read by, a span that holds every way's reading: the sum counts as built on the lowest value of that span
  in the range when the span reaches the range, an over-read where no one way is in it, and on 32768 when that reading
  gives none and the operand holds a ** or a <<, whose cap at 2**4096 can leave the wide reading empty where one way has
  a value. A name with a binding the census does not record is also read unbounded (BOUND), so with K bound to 30000 and
  by K = f(), 40000 + K, which reads 70000 by K's int, is built on 40000, and so are 40000 - K and 40000 + 90002 // K.
  interval() reads a bool as the int it is, True as 1 and False as 0 (random.randrange(True, 50000) is 1-49999), and a
  float only through int() of it or of a name bound to it (above).
  In any file, read as text (text_hits): a non-Python file whole; in Python, each string literal that is not a
  docstring, each literal part of an f-string, each bytes literal, and the code of code text (below), each only when
  its value holds five digits standing alone (FIVE: any five, in the range or not); a string without them is read
  neither as text nor as code text, so "port = 4000 * 10" in a string is not read where the same code in the module
  is. A number there
  may carry digit separators (45_001), and in the key, decl, env, flag and pair rules it may follow a quote and may open
  a shell arithmetic expansion ($((40000 + RANDOM % 1000)) reads as 40000):
    key   a port-named key or name after a delimiter ({ , ( [ ;) or at a line's start, then : or = and the number
          ({ port: N }, "busPort": N, , port=N);
    decl  a port-named name declared and assigned (const port = N, local port=N, export ROMP_POSTAL_PORT=N);
    env   an upper-case port-named name, then : or = and the number, quoted or not (ROMP_POSTAL_PORT'] = 'N');
    flag  a --*port option (above: --port N, --port=N, --no-port-check=N), or one followed by a quote, a comma and the
          number, as in a list ('--port', 'N'), with whitespace on either side of the comma (any character
          str.isspace() accepts, newlines included, so a list split across lines reads the same), or one followed by a
          quote and then spaces or tabs before the number (a shell argv's "--port" N, '--port' "N"). Neither quoted
          form checks that the quote closes a string, or that a string it closes opened at the option, so a quote that
          opens one reads the same way (--port" N", --port", N"), and so does an option that ends a longer quoted word
          ("serve --port" N);
    authority  host:N after an address (above) with no placeholder in its run (http://127.0.0.1:N, //TESTHOST:N), the
               number right after the colon, or after a quote, a + and an optional quote ('http://127.0.0.1:' + N),
               with whitespace on either side of the + (newlines included: a concatenation split across lines, the +
               ending one line or starting the next) but only spaces or tabs between the colon and the quote, so a
               newline inside the string after the colon ends the address; the rule does not check that the quote
               closes a string, so a quote that opens one reads the same way, and an object literal's { localhost:
               '+N' } is read as a concatenation;
    address    a loopback or wildcard address tuple in text (("127.0.0.1", N));
    call  a number handed first to .listen(, .connect(, createConnection( or .bind(;
    pair  a port-named string and the number handed together ("ROMP_POSTAL_PORT", "N").
  Code text in a Python string, one that parses as Python into at least one statement (a probe a test runs with
  python -c, a planted module), is read both ways, whether or not anything runs it, since the census cannot tell a
  probe that runs from one that is only parsed: by the Python rules, and by the text rules over its code with its
  comments and string literals blanked out (code_text_tokens(); the whole text when the tokenizer refuses it). Each
  string literal inside it is read in its own right, as here, so a comment or a docstring inside code text stays out as
  it does in a module. A string that parses to no statement, comments alone, is no code text: the text rules read it
  whole, its comments included ("# PORT=N"). Code text is parsed three levels deep (code text inside code text inside
  code text); a string inside the third level is read by the text rules alone. A short string can parse as code without
  being any: "localhost:N" is an annotation to the parser, and the authority rule reads it. A hit inside a string
  literal is reported on the source line that writes the number when the number is written there in plain ASCII
  digits; otherwise on a line counted from the literal's newlines, which can be off by the newline escapes it holds.

THE EXCLUDED CLASS, a stated predicate rather than a list: a number in the range that no rule above reads is not read,
and stays. In Python that takes in prose in a comment or a docstring (in code text too). Elsewhere it takes in a number
only where no rule's position or shape holds it: a log, error or ps line a test hands to a parser (the ssh errors of
tests/test_tunnel_stale_and_logging.py, the ps lines of tests/test_kernel_tunnels.py, whose -L 50512:127.0.0.1:29855
puts the number before the host), a digit string handed by position, an assertion's expected value (it follows the
setting it checks, so the setting is what counts), an id, a size, a byte offset, a timeout and a duration. These are
not exempt as kinds: a file read as text is read whole, its comments included (a shell comment holding localhost:N is
read), and a line or a value that fits a rule is read where it is written (parse_line("... 127.0.0.1:N ..."),
assertEqual(got, {"port": N}), f(port_timeout=N)). Not every place left unread is inert: WHAT IT CANNOT SEE gives
known examples that can dial or bind.

WHAT IT CANNOT SEE: known examples, each with a green plant in test_the_stated_blind_spots_stay_unread. This is not a
closed list. THE RULE states what the census reads; a shape it leaves out is unread whether or not an example here
names it, and rules read from a test's text cannot follow every way a test comes by a port. A change that reads one of
these turns its plant red, and the example leaves this list.
  a value in a position whose form THE RULE's values leave out: a name with no binding the census records (BOUND: a
  parameter, a name another module binds, B after B = A), an attribute (cfg.p after cfg.p = N), a container's element
  (CFG["a"]), a call's result other than str() or int() around a bounded value and the random calls (pick(),
  random.choice((N, M))), a random call with a parameter left empty that a ** mapping beside it can fill
  (random.randrange(50000, **kw), random.randrange(start=50000, step=1, **kw), and random.randrange(50000, E, **kw)
  with E bound to None, a stop the name can leave empty), a name interval() does not bound inside a display that is
  the position's value or in a loop's sequence (P = "N", then {"ports": [P]}, the census recording no int for P), an
  f-string ("127.0.0.1:" + f"{N}"), an unbounded expression with no constant operand of a sum or difference in the range
  (base + i, N * k), and a run-time substitution into code text (a template's __VALUE__ replaced at run time); a rule of
  its own may still read such a value where it is written;
  an unbound random method spelled on anything but a name or attribute called Random or SystemRandom, whose instance
  then fills start (type(rng).randrange(rng, N, M), MyRandom.randrange(rng, N, M));
  a name or attribute called Random or SystemRandom that holds an instance (Random = random.Random(), then
  Random.randint(N, M); cfg.SystemRandom.randint(N, M)), whose first argument is taken for the instance, in THE BIND
  BANDS' draws too;
  a name a module sets with no binding form beside a binding the census records (K = 7, then globals()["K"] = -7,
  exec("K = -7"), setattr(sys.modules[__name__], "K", -7), or mod.K = -7 in another module), read by the values the
  census records alone: random.randrange(40000, 1000, K) reads K as 7 and is not counted, though CPython returns values
  from 1001 to 40000;
  a value a binding the census does not record gives a name the census records an int for, where the position's value
  gives no reading with the name unbounded and the name reads by its recorded ints alone (BOUND): with E bound to 1000
  and by E = f(), random.randrange(30000, E) reads E as 1000 and is not counted, though CPython returns values from
  30000 to 49999 when f() returns 50000;
  a float where the census reads an int outside int(), which a random call takes on 3.10 and 3.11
  (random.randrange(40000.0, 50000)), a float bound to a name beside an int and a binding the census does not record
  included, where the name reads by its ints alone: with E bound to 1000, to 45010.0 and by E = f(),
  random.randrange(45001, E) reads E as 1000 and is not counted, though on 3.10 and 3.11 CPython returns values from
  45001 to 45009 for E = 45010.0 (int(E) reads it, and int(45001.0) is 45001: THE RULE);
  an operator interval() does not read over the operands it is given (THE RULE): true division, which gives a float
  (int(90002 / 2)), **, <<, >>, &, | or ^ over an operand that can be negative (-(-45001 | 0)), and a ** or a <<
  whose value can pass 2**4096 ((2 ** 5000 + 45001) % 2 ** 5000);
  a random call with an argument passed through a * sequence (random.randrange(*(N, M)), random.randint(*[N, M]));
  a randrange with its stop left empty and a step that is 1 only at run time, which Python takes (ONE = 1, then
  random.randrange(start=50000, step=ONE); random.randrange(50000, step=+1); E = None, then random.randrange(50000,
  E, ONE));
  a host that THE RULE does not take for one (("TESTHOST", N), HTTPConnection(self.host, N)), a name bound to the
  empty string, even in a tuple (H = "", then (H, N)), and the empty string itself before a port in a call (serve("",
  N)); the port beside it is read only when another rule reads it;
  a positional port handed to a function whose name no index holds (a name no function of the module, of a tests/
  module it imports, or of kernel/, postal/ or cli/ carries: vendorlib.start_vendor_server(N), a tests/ helper the
  module does not import, a helper reached through import tests.helpers used whole), with no host right before it;
  in a file read as text, a positional port beyond the call rule (nc -l 127.0.0.1 N, python3 -m http.server N,
  startServer(N)), and a port reached through a name that does not name a port (const P = N, then :${P});
  a %-template whose port's placeholder is not a plain %d, %i or %s: one with a mapping key, a flag, a width, a
  precision, a length modifier or another conversion ("http://127.0.0.1:%(p)d/" % {"p": N}, "http://127.0.0.1:%-d/" %
  N, "http://127.0.0.1:%5d/" % N, "http://127.0.0.1:%.5d/" % N, "http://127.0.0.1:%ld/" % N, "http://127.0.0.1:%u/" %
  N), unless another rule reads the operand (a port-named key does) or another address in the same template has a
  plain one;
  a %-template or a format template that is neither a string literal nor a name the module binds to exactly one string
  literal (a parameter or a call's result: t % N, tmpl() % N, tmpl().format(N));
  a port with no address and colon right before it in the text its rule examines, which only a rule that needs no host
  can read ($BUS_PORT:N, by the env rule): a placeholder host before digits (f"http://{host}:N/x", f"{host}:N",
  "http://%s:N/x" % host, "http://{}:N/x".format(host), `http://${host}:N/x`, curl http://$HOST:N/x), a host or a
  colon in an operand of its own before digits ("http://" + host + ":N" and "http://127.0.0.1" + ":N", in Python and
  in JavaScript), a left side of a + with no address written in it (base_url() + str(N)), the colon and the port in
  operands of their own in JavaScript ("http://" + host + ":" + N; Python's concatenation rule reads it), userinfo
  before a host that is no loopback or wildcard literal ("http://u@TESTHOST:%d/x" % N), and an IPv6 literal other
  than [::1] or [::] ("http://[2001:db8::1]:%d/x" % N);
  an option the flag rules do not read, in Python and in text: an option spelled with one dash (-p N), an option whose
  name has no port word (["romp", "serve", "--listen", "N"]), and an option and its number that are not neighbours
  (["--port"] + [N], ['--port'].concat(['N'])), and a flag built at run time (["romp", "--" + "port", "N"]);
  in text, a line continuation or a comment where a rule takes only whitespace: a shell line continuation between an
  option and its number (--port, a backslash, a newline, then N), and a JavaScript comment, a block or a line one,
  between the + or the comma and the number ('http://127.0.0.1:' + /* the port */ N, ['--port', /* the port */ 'N']);
  a value under a key that names no port by THE RULE: a bare name with no port word, whatever it holds (K = "port",
  then {K: N});
  code text that does not parse on its own (an indented fragment, a %-template), which the text rules read instead, so
  its positional ports are not resolved;
  a file the census never opens, since its only number in the range does not stand alone in its text as written (THE
  FILES): a digit string right after an escape sequence, such as a port key's value written as a backslash, a t and
  then N (a tab, then the port);
  a file outside THE FILES (a support file such as ui/test-dom-shim.ts, a lab tool under tools/).
Each planted shape below is red, with the rule it names among the rules that read it, and each excluded shape is green.

THE SENTINELS (SentinelPorts; the ruling of round 1 on fork PR 966, (b)). tests/test_hermetic_kernel_postal.py's children
read back values a test wrote to a port name (ROMP_POSTAL_PORT, ROMP_KERNEL_PORT, BUS_PORT), and
tests/test_postal_fixed_port_belt.py names a hermetic bus's own port, which the belt lets the bus bind. Those values are
7, 8 and 9: below 1024, where on Linux at the default an unprivileged bind is refused, and in no band a test binds. The
pin reads, in those two modules, every number written as text a process could take for a port (sentinel_values(): a
quoted digit string, since the environment holds strings; a number after a loopback host and a colon; an int assigned
to a port-named name, BUS_PORT = N), and fails on any that falls in a bind band.
THE BIND BANDS are derived from THE FILES (bind_bands()):
  the ephemeral range, LOW-HIGH (a bind to port 0, tests/lab_ports.py's reserve());
  each per-test base of a shell file, a port-named name set to B plus ${BATS_TEST_NUMBER} in an arithmetic expansion
  (tests/romp-postal.bats): B to B plus the file's count of tests, moved by every constant the file adds to that name
  in an arithmetic expansion (the squat test's), and by every retry step a helper adds to a port-named name (port +
  try * S, inside a function: S times each try below the most its callers ask for);
  each draw from randint(a, b) with a at or above 1024: a call in Python whose two arguments are int literals, each
  given by position or by its parameter's name as THE RULE reads a random call (_random_args(): randint(a=A, b=B) is
  randint(A, B), and neither randint(b=B) nor randint(A, B, a=C), which Python refuses, is a draw; a call spelled on a
  name or attribute called Random or SystemRandom drops its first argument as the instance, so
  random.Random.randint(rng, A, B) is randint(A, B)), since every reader of a random call reads its arguments one way;
  or the text in a shell file, by position (the probe of tests/free-port.bash);
  each block keyed by a test file's name, 'name.test.js': [lo, hi] (tests/manager-ports.js).
The machine's own fixed ports (the postal bus's, the kernel's, the manager's) are not among them: no test binds them,
and the two modules write them on purpose, to show the belt and the licences refusing them. A band made any other way
is not read.

THE HEADER'S BANDS (HeaderBands; round 1 on fork PR 966). tests/manager-ports.js's header lists the bands other suites
draw from, which its blocks sit under. Each range in that list must lie below LOW, since under this census no test
draws a port from a band that reaches the range, and must hold a band bind_bands() derives from another file, so the
list names bands the tree has (it still named 20000-39999, the postal port two modules derived from their pid, after
both had moved to port 1). Its single ports, the machine's own, are not read, and neither is whether the list is
complete or each range tight.

Synthetic: reads the tree only; no socket, no kernel, no subprocess.
"""
import ast
import io
import itertools
import os
import random
import re
import shutil
import string
import sys
import tempfile
import tokenize
import unittest

HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import parse_cache                                  # noqa: E402  one parse per file per process, shared with the other AST censuses

LOW, HIGH = 32768, 65535
LOOPBACK = frozenset({"127.0.0.1", "localhost", "0.0.0.0", "::1", "::", ""})
SKIP_DIRS = frozenset({"node_modules", "dist", "out", "site", "venv", "__pycache__"})   # and every hidden directory
PRODUCT_DIRS = ("kernel", "postal", "cli")
_D5 = r"\d(?:_?\d){4}"                              # five digits, digit separators allowed (45_001)
FIVE = re.compile(r"(?<![\w.])(" + _D5 + r")(?![\w.])")   # a five-digit number standing alone (not inside an id, a decimal or a hash)
WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
COMPUTED = re.compile(r"%[ \t]*\d{4,5}\b|\brand(?:int|range|below)\(")   # the computed forms interval() bounds
RANDOM_CALLS = {"randint": ("a", "b"), "randrange": ("start", "stop", "step"),   # the calls interval() bounds, random's
                "randbelow": ("exclusive_upper_bound",)}                         # and secrets', with their parameters' names
MAX_CODE_DEPTH = 3                                  # code text inside code text inside code text, and no deeper


def in_range(v):
    return isinstance(v, int) and not isinstance(v, bool) and LOW <= v <= HIGH


def _num(s):
    return int(s.replace("_", ""))


def names_a_port(name):
    """True when one of the words of `name` (split at punctuation and camelCase) is port or ports."""
    if not isinstance(name, str):
        return False
    return any(w.lower() in ("port", "ports") for part in re.split(r"[^A-Za-z0-9]+", name) for w in WORDS.findall(part))


def _digits(v):
    """The number a str spells when, once str.strip() has taken off any leading and trailing whitespace, it is five
    digits (any Unicode decimal digits, digit separators allowed: " 45_001 "), else None."""
    if isinstance(v, str) and re.fullmatch(_D5, v.strip()):
        return _num(v.strip())
    return None


# The text rules.
_NUM = r"[\"'`]?(?:\$\(\([ \t]*)?(?P<n>" + _D5 + r")(?![\w.])"
_HOST = r"(?:\b(?:127\.0\.0\.1|localhost|0\.0\.0\.0)\b|\[::1?\])"
_OPT = r"[\w-]+(?:\.[\w-]+)*"                     # an option's name after --: word characters and dashes, in parts a dot joins
TEXT_RULES = (
    ("key", re.compile(r"(?:^|[{,(\[;])[ \t]*[\"'`]?(?P<name>[\w$.-]+)[\"'`]?[ \t]*[:=][ \t]*" + _NUM, re.M)),
    ("decl", re.compile(r"\b(?:const|let|var|local|export|readonly|declare(?:[ \t]+-\w+)?)[ \t]+(?P<name>[\w$]+)[ \t]*=[ \t]*" + _NUM)),
    ("env", re.compile(r"\b(?P<name>[A-Z][A-Z0-9_]*)[\"'`]?\]?[ \t]*[:=][ \t]*" + _NUM)),
    ("flag", re.compile(r"--(?P<name>" + _OPT + r")(?:=|[ \t]+|[\"'`]\s*,\s*|[\"'`][ \t]+)" + _NUM)),   # quoted: in a list, or then spaces
    ("authority", re.compile(r"(?:" + _HOST + r"|//[\w.-]+)[ \t]*:[ \t]*(?:[\"'`]\s*\+\s*[\"'`]?)?(?P<n>" + _D5
                             + r")(?![\w.])")),   # the number right after the colon, or concatenated onto it
    ("address", re.compile(r"\([ \t]*[\"'](?:127\.0\.0\.1|localhost|0\.0\.0\.0|::1?|)[\"'][ \t]*,[ \t]*(?P<n>" + _D5 + r")[ \t]*[,)]")),
    ("call", re.compile(r"(?:\.listen|\.connect|createConnection|\.bind)\([ \t]*(?P<n>" + _D5 + r")(?![\w.])")),
    ("pair", re.compile(r"\([ \t]*[\"'`](?P<name>[\w$.-]+)[\"'`][ \t]*,[ \t]*" + _NUM)),
)
_NAMED = frozenset({"key", "decl", "env", "flag", "pair"})   # the rules whose match carries a name that must name a port
# A template's address up to the port's colon (\x00: a formatted host). \Z and not $, which also matches before a final
# newline, so "http://127.0.0.1:\n" is no address before a port.
_ADDR_END = re.compile(r"(?:" + _HOST + r"|//[\w.\x00-]+)[ \t]*:[ \t]*\Z")
_ADDR_PCT = re.compile(r"(?:" + _HOST + r"|//(?:[\w.-]|%s)+):%[dis]")   # a host after // may be a %s placeholder
_BLANKED = frozenset([tokenize.COMMENT, tokenize.STRING] + [getattr(tokenize, t) for t in (
    "FSTRING_START", "FSTRING_MIDDLE", "FSTRING_END", "TSTRING_START", "TSTRING_MIDDLE", "TSTRING_END") if hasattr(tokenize, t)])


def _as_text(s):
    """A literal's text as the address rule reads it: a NUL the source itself writes becomes U+FFFD, which no part of
    the rule accepts, so the only \x00 in a rendered text is the placeholder for a piece the census cannot read."""
    return s.replace("\x00", "\ufffd")


def _line_in(first, last, after):
    """The physical line of a place inside a string literal that spans lines `first` to `last`, with `after` newlines of
    the literal's value after the place. It is counted back from the literal's end, so a triple-quoted literal whose
    opening line ends in a backslash reads right, and it is held between the two lines, so a literal written on one line
    with newline escapes reads as that line."""
    return max(first, min(last, last - after))


def text_hits(text, first_line=1, last_line=None):
    """[(line, number, why)] for every text rule's match in `text`: in a whole file, the line counted from `first_line`;
    in a string literal spanning `first_line` to `last_line`, the line _line_in reads."""
    out = []
    for rule, rx in TEXT_RULES:
        for m in rx.finditer(text):
            v = _num(m.group("n"))
            if not in_range(v):
                continue
            if rule in _NAMED and not names_a_port(m.group("name")):
                continue
            if rule == "env" and m.group("name") != m.group("name").upper():
                continue
            if last_line is None:
                line = first_line + text.count("\n", 0, m.start("n"))
            else:
                line = _line_in(first_line, last_line, text.count("\n", m.start("n")))
            out.append((line, v, "text rule %s" % rule))
    return out


def code_text_tokens(src):
    """`src`, a code text, with its comments and string literals blanked out (every character but a newline made a space,
    so each place keeps its line), for the text rules; `src` whole when the tokenizer refuses it."""
    starts, at = [], 0                              # the tokenizer's rows are readline()'s lines, split at newlines only
    for line in src.split("\n"):
        starts.append(at)
        at += len(line) + 1
    out = list(src)
    try:
        for tok in tokenize.generate_tokens(io.StringIO(src).readline):
            if tok.type in _BLANKED:
                a = starts[tok.start[0] - 1] + tok.start[1]
                b = starts[tok.end[0] - 1] + tok.end[1]
                for i in range(a, min(b, len(out))):
                    if out[i] != "\n":
                        out[i] = " "
    except (tokenize.TokenError, SyntaxError, IndexError, ValueError):
        return src
    return "".join(out)


# The Python rules.
def _params(fn):
    a = fn.args
    names = [x.arg for x in a.posonlyargs + a.args]
    if names and names[0] in ("self", "cls"):
        names = names[1:]
    return tuple(names), (a.vararg.arg if a.vararg else None)


def defs_of(tree, into=None):
    """{name: [(positional parameter names, *args name)]} for every function `tree` defines, at any depth."""
    into = {} if into is None else into
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            into.setdefault(n.name, []).append(_params(n))
    return into


class HelperModules:
    """The functions a module under `root`/tests/ defines, by the dotted name a test imports it under (helpers and
    tests.helpers are tests/helpers.py; served.helpers is tests/served/helpers.py); None for a name that is no module
    there. `resolved` holds every module found, for the census's not-empty pin."""

    def __init__(self, root):
        self.base = os.path.join(root, "tests")
        self.memo, self.resolved = {}, set()

    def __call__(self, dotted):
        if dotted not in self.memo:
            parts = dotted.split(".")
            if parts[0] == "tests":
                parts = parts[1:]
            p = (os.path.join(self.base, *parts) + ".py") if parts and all(parts) else None
            defs = None
            if p is not None and os.path.isfile(p):
                defs = defs_of(parse_cache.source_and_tree(p)[1])
                self.resolved.add(p)
            self.memo[dotted] = defs
        return self.memo[dotted]


def _no_helpers(_dotted):
    return None


def _docstrings(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
                out.add(id(first.value))
    return out


def _target_name(t):
    if isinstance(t, ast.Name):
        return t.id
    if isinstance(t, ast.Attribute):
        return t.attr
    if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and isinstance(t.slice.value, str):
        return t.slice.value
    return None


def _port_flag(node):
    """The --*port option a string literal spells whole (--port, --bus-port, --server.port), else None."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        m = re.fullmatch(r"--(" + _OPT + r")", node.value)
        if m and names_a_port(m.group(1)):
            return node.value
    return None


def _callee(f):
    return f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)


def _signed_number(v):
    """The number a unary minus or plus over an int or float constant computes (-7, +7, -7.0; True among the ints, so
    -True is -1), which BOUND records for a name; None for any other node."""
    if isinstance(v, ast.UnaryOp) and isinstance(v.op, (ast.USub, ast.UAdd)) and isinstance(v.operand, ast.Constant) \
            and isinstance(v.operand.value, (int, float)):
        return -v.operand.value if isinstance(v.op, ast.USub) else +v.operand.value
    return None


def interval(node, bound=None, steps=None):
    """(lo, hi, computed) for an int expression the census can bound, else None: constants, a unary minus or plus, + -
    and * over them, // and % by a divisor read by its positive and its negative part, 0 in neither (_divided(): so
    90002 // K, with K bound to 2, to 3 and by K = f(), is 30000-45001, and with K bound to -1 and to 2 it is
    -90002-90002), every other integer operator over the operands THE RULE gives it (BINARY and UNARY: ** << >> & | ^
    over operands never negative, ~ and not), a conditional expression as the span holding its two branches, a := as its
    value, a name (below), str() or int() around one (int() of a name as CPython's int() of each of its values in
    `bound`, a float or a string included and a value int() refuses passed over, and int() of a constant as CPython's
    int() of it), an unknown operand of % by such a divisor read by its parts too, and randint(a, b), randrange(stop),
    randrange(start, stop[, step]) and randbelow(n) over bounded arguments read as the values each can return, each
    argument given by position or by its parameter's name (_random_args()). randrange(start, stop[, step]) is read by
    its step's sign, the step bounded or not (a step left out is 1, and one a ** mapping can give is unbounded): start's
    lowest value to stop's highest less one for a step that is never negative, stop's lowest plus one to start's highest
    for any other step that is never positive, and the span holding both for the rest, a step that can take either sign
    or one interval() does not bound (THE RULE). A bool is the int it is (True 1, False 0). computed is True when an
    unknown took part, or a name's values differ. `bound` maps a name to the values it reads by, and `steps` does the
    same at a randrange's step and anywhere inside one (`bound` when not given): the span from the lowest int among them
    to the highest, a None, a float or a string among them adding nothing, and no reading when none is an int. A
    randrange's stop that is a name with None among its values in `bound` is also read as a stop left empty, randrange's
    default, when the step is left out or is the int 1 written there, and the call reads as the span holding both
    readings. literal() hands it as `bound` every value the census records for each name (BOUND), so a name bound to 7,
    to 9 and by K = f() reads 7-9, and as `steps` the values of each name every binding of which the census records,
    each to an int, so at a step that K is one it does not bound; and, for a value that reads names with a binding the
    census does not record, it calls again for each mix of leaving such names out of `bound` or not, so that each reads
    unbounded in some reading and by its ints in another. offset_base() hands it the values of its own `bound`, each
    name it reads holding one of its values at a time, an int or any other constant (a float, a string or bytes reads
    only inside int(), and None only at a randrange's stop)."""
    bound = bound or {}
    steps = bound if steps is None else steps
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return int(node.value), int(node.value), False
    if isinstance(node, ast.Name) and bound.get(node.id):
        ints = [int(x.value) for x in bound[node.id] if isinstance(x, ast.Constant) and isinstance(x.value, int)]
        if not ints:
            return None
        return min(ints), max(ints), min(ints) != max(ints)   # the union of its ints' readings, one span
    if isinstance(node, ast.Call) and _callee(node.func) in ("str", "int") and len(node.args) == 1 and not node.keywords:
        arg = node.args[0]
        if _callee(node.func) == "int" and isinstance(arg, ast.Name) and bound.get(arg.id):
            ints = [v for v in map(_int_of, bound[arg.id]) if v is not None]   # CPython's int() of each value it takes
            return (min(ints), max(ints), min(ints) != max(ints)) if ints else None
        if _callee(node.func) == "int" and isinstance(arg, ast.Constant):
            v = _int_of(arg)                        # CPython's int() of the constant, as of a name's each value
            return None if v is None else (v, v, False)
        return interval(arg, bound, steps)
    if isinstance(node, ast.Call) and _callee(node.func) in RANDOM_CALLS:
        name, args = _callee(node.func), _random_args(node) or []
        calls, stop = [args], (args[1] if name == "randrange" and len(args) > 1 else None)
        if isinstance(stop, ast.Name) and any(isinstance(x, ast.Constant) and x.value is None for x in bound.get(stop.id, ())) \
                and (len(args) == 2 or _the_int_one(args[2])):
            calls.append(args[:1])                  # a stop the name leaves empty, randrange's own default None
        got = [r for r in (_random_span(name, [interval(a, steps if name == "randrange" and i == 2 else bound, steps)
                                               for i, a in enumerate(c)]) for c in calls) if r]   # a step reads by `steps`
        return (min(r[0] for r in got), max(r[1] for r in got), True) if got else None
    if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY:
        return UNARY[type(node.op)](interval(node.operand, bound, steps))
    if isinstance(node, ast.BinOp) and type(node.op) in BINARY:
        right = interval(node.right, bound, steps)
        left = interval(node.left, bound, steps)
        if right is None or (left is None and not isinstance(node.op, ast.Mod)):
            return None                             # an unknown left operand is read only by %
        return BINARY[type(node.op)](node.op, left, right)
    if isinstance(node, ast.IfExp):                 # either branch: the span holding both
        body, orelse = interval(node.body, bound, steps), interval(node.orelse, bound, steps)
        if body is None or orelse is None:
            return None
        lo, hi = min(body[0], orelse[0]), max(body[1], orelse[1])
        return lo, hi, body[2] or orelse[2] or lo != hi
    if isinstance(node, ast.NamedExpr):             # a := is its value
        return interval(node.value, bound, steps)
    return None


def _divided(op, left, right):
    """(lo, hi, computed) for `left` // or % `right`, `left` an interval or None when interval() does not bound it, else
    None. The divisor is read by its positive part, from the greater of its lowest value and 1 up to its highest, and
    its negative part, from its lowest value up to the lesser of its highest and -1, each a part only where it holds a
    value, and the reading is the span holding both parts' readings. 0, for which Python raises, is in neither part, so
    no end of a part is 0, and a reversed divisor (a call Python always refuses) has a part only where its two ends
    share a sign. // by a part is the span from the least to the greatest quotient of an end of `left` by an end of the
    part (a // x is monotonic in a, and in x on either side of 0); % by a part is the remainder where `left` and the
    part are one value each, and otherwise, `left` unknown included, 0 to the part's highest value less one for a
    positive part and the part's lowest value plus one to 0 for a negative one (Python's remainder takes the divisor's
    sign). None when the divisor has no part (it is 0, or a reversed one across 0), or for // when `left` is unknown."""
    c, d, cb = right
    parts = ([(max(c, 1), d)] if d >= 1 else []) + ([(c, min(d, -1))] if c <= -1 else [])
    reads = []
    for p, q in parts:
        if isinstance(op, ast.FloorDiv):
            if left is None:
                return None
            ends = [x // y for x in left[:2] for y in (p, q)]
            reads.append((min(ends), max(ends)))
        elif left is not None and left[0] == left[1] and p == q:
            reads.append((left[0] % p,) * 2)
        else:
            reads.append((0, max(p, q) - 1) if p > 0 else (min(p, q) + 1, 0))
    if not reads:
        return None
    lo, hi = min(r[0] for r in reads), max(r[1] for r in reads)
    return lo, hi, (True if left is None else left[2]) or cb or lo != hi


BIG = 4096                                          # bits: a ** or << whose value can pass 2**BIG is not read
MIXES = 256                                         # the most ways literal() reads a value's names two ways each (BOUND)


def _cornered(f, left, right):
    """(lo, hi, computed) for an operator monotonic in each operand: the least and greatest of `f` over their ends."""
    ends = [f(x, y) for x in left[:2] for y in right[:2]]
    lo, hi = min(ends), max(ends)
    return lo, hi, left[2] or right[2] or lo != hi


def _never_negative(*ivs):
    return all(min(iv[:2]) >= 0 for iv in ivs)


def _power(_op, left, right):
    """** over operands never negative, by its ends (x ** y never falls as x grows, and as y grows falls only for x = 0,
    from 0 ** 0 = 1 to 0, so the ends hold it), unless its value can pass 2**BIG; None otherwise (a negative exponent
    gives a float, a negative base a possibly negative value)."""
    if not _never_negative(left, right):
        return None
    b, d = max(left[:2]), max(right[:2])
    if b >= 2 and (d * (b.bit_length() - 1) > BIG or b ** d > 2 ** BIG):   # the first test bounds the second's cost
        return None
    return _cornered(lambda x, y: x ** y, left, right)


def _shifted(op, left, right):
    """<< and >> over operands never negative, by their ends (x << y grows in both, x >> y grows in x and falls in y),
    unless a << can pass 2**BIG; None otherwise (a negative shift count raises)."""
    if not _never_negative(left, right):
        return None
    if isinstance(op, ast.LShift):
        b, d = max(left[:2]), max(right[:2])
        if b and (b.bit_length() + d > BIG + 1 or b << d > 2 ** BIG):   # the first test bounds the second's cost
            return None
        return _cornered(lambda x, y: x << y, left, right)
    return _cornered(lambda x, y: x >> min(y, x.bit_length()), left, right)


def _bitwise(op, left, right):
    """&, | and ^ over operands never negative: Python's own value where each operand is one value, else 0 up to the
    lesser of their highest values for & (x & y is at most each), and 0 up to 2**n - 1 for | and ^, n the bit length
    of the greater of their highest values (neither sets a bit above both); None over an operand that can be
    negative."""
    if not _never_negative(left, right):
        return None
    if left[0] == left[1] and right[0] == right[1]:
        v = {ast.BitAnd: int.__and__, ast.BitOr: int.__or__, ast.BitXor: int.__xor__}[type(op)](left[0], right[0])
        return v, v, left[2] or right[2]
    top = min(max(left[:2]), max(right[:2])) if isinstance(op, ast.BitAnd) else \
        2 ** max(max(left[:2]), max(right[:2])).bit_length() - 1
    return 0, top, True


# The operators interval() reads (THE RULE), each by its class: BINARY's over two bounded operands (an unknown left
# operand of % too), UNARY's over its operand's interval or None. OPERATOR_LIMITS names, with the reason, each operator
# of Python's grammar interval() does not read; Operators checks that every one is in exactly one of the three.
BINARY = {
    ast.Add: lambda _op, l, r: (l[0] + r[0], l[1] + r[1], l[2] or r[2]),
    ast.Sub: lambda _op, l, r: (l[0] - r[1], l[1] - r[0], l[2] or r[2]),
    ast.Mult: lambda _op, l, r: _cornered(lambda x, y: x * y, l, r),
    ast.FloorDiv: _divided, ast.Mod: _divided, ast.Pow: _power, ast.LShift: _shifted, ast.RShift: _shifted,
    ast.BitAnd: _bitwise, ast.BitOr: _bitwise, ast.BitXor: _bitwise}
UNARY = {
    ast.UAdd: lambda o: o,                                              # +7 is 7
    ast.USub: lambda o: o and (-o[1], -o[0], o[2]),
    ast.Invert: lambda o: o and (-o[1] - 1, -o[0] - 1, o[2]),           # ~x is -x - 1
    ast.Not: lambda o: (int(not o[0]),) * 2 + (o[2],) if o and o[0] == o[1] else (0, 1, True)}   # a bool, whatever o is
OPERATOR_LIMITS = {
    ast.Div: "true division gives a float, which no port is, and int() of one is not read (int(90002 / 2))",
    ast.MatMult: "Python raises for @ over ints"}


def _random_span(name, ivs):
    """(lo, hi, True) for the random call `name` over the intervals of its arguments `ivs` (_random_args()'s order),
    else None: THE RULE's reading of each call."""
    k = len(ivs)
    if name == "randrange" and k in (2, 3) and ivs[0] and ivs[1]:   # THE RULE's one reading, by the step's sign
        (a, b, _), (c, d, _) = ivs[:2]
        step = ivs[2] if k == 3 else (1, 1, False)
        if step and step[0] >= 0:                   # never negative: from start up to stop less one (a step of 0 raises)
            return a, d - 1, True
        if step and step[1] <= 0:                   # never positive: from stop plus one up to start
            return c + 1, b, True
        return min(a, c + 1), max(b, d - 1), True   # either sign, or unbounded: the span holding both
    if ivs and all(ivs):
        if name == "randint" and k == 2:
            return ivs[0][0], ivs[1][1], True
        if name in ("randrange", "randbelow") and k == 1:
            return 0, ivs[0][1] - 1, True
    return None


def _int_of(node):
    """CPython's int() of the constant `node` holds (45001 for "45001", " 45_001 " or 45001.9, 1 for True), or None
    when int() refuses it ("x", "45001.0", None) or `node` is a display."""
    if isinstance(node, ast.Constant):
        try:
            return int(node.value)
        except (TypeError, ValueError, OverflowError):
            pass
    return None


def _the_int_one(node):
    """True when `node` writes the int 1 itself, the one step Python takes with a stop left empty."""
    return isinstance(node, ast.Constant) and type(node.value) is int and node.value == 1


def _random_args(call):
    """The arguments of a random call (RANDOM_CALLS) in its parameters' order, up to the first parameter left empty: each
    positional argument in its place, then each keyword in the place of the parameter it names (randint(a=A, b=B) is
    randint(A, B)), a keyword that names no parameter passed over. A stop written as None, randrange's default, is a
    stop left empty, once a keyword that repeats it is refused. A ** mapping can fill any parameter left empty, at run
    time: beside a randrange's start and stop it fills the step, given as the keyword node that passes the mapping,
    which is no expression, so interval() never bounds it whatever the mapping holds; with any other parameter left
    empty beside it, None. None too when an argument is starred, the positional arguments outnumber the parameters, or
    Python refuses the call for the way its arguments are passed: a keyword names a parameter a positional argument
    fills, or a randrange's stop is left empty and its step is anything but the int 1 (randrange's default step, the
    one step Python takes without a stop). None as well for a stop left empty beside a step that is 1 only at run time
    (a name bound to 1, +1), which Python takes: only the int 1 written there is read. A call spelled on a name or
    attribute called Random or SystemRandom passes its instance first, and it is dropped (random.Random.randrange(rng,
    S, E)); the class is known by that name alone, so a name or attribute so called that holds an instance loses its
    first argument (WHAT IT CANNOT SEE)."""
    params, args = RANDOM_CALLS[_callee(call.func)], call.args
    if isinstance(call.func, ast.Attribute) and _callee(call.func.value) in ("Random", "SystemRandom") and args \
            and not isinstance(args[0], ast.Starred):
        args = args[1:]                             # an unbound method spelled on the class: the instance comes first
    if len(args) > len(params) or any(isinstance(a, ast.Starred) for a in args):
        return None
    got, mapping = dict(zip(params, args)), None
    for kw in call.keywords:
        if kw.arg is None:
            mapping = kw                            # a ** mapping: it names no parameter, yet can fill any
        elif kw.arg in got:
            return None                             # Python: got multiple values for argument
        elif kw.arg in params:
            got[kw.arg] = kw.value
    if isinstance(got.get("stop"), ast.Constant) and got["stop"].value is None:
        del got["stop"]                             # a stop of None written there is randrange's default: left empty
    if mapping is not None:
        if "start" in got and "stop" in got:
            got.setdefault("step", mapping)         # the step the mapping can give: unbounded, so the span holding both
        if len(got) < len(params):
            return None                             # a parameter only the mapping can fill: its value is unknown
    step = got.get("step")
    if step is not None and "stop" not in got and not _the_int_one(step):
        return None                                 # Python refuses it unless the step is 1 at run time; only a written 1 is read
    out = []
    for p in params:
        if p not in got:
            break
        out.append(got[p])
    return out


EACH = 256                                          # the most ways offset_base() reads one operand value by value


def _values(each, k):
    """The values offset_base() reads the name `k` by, one at a time: its ints from the lowest, then its other values (a
    float or a string, which int() reads) in the order the module binds them."""
    return sorted({v for v in each[k] if isinstance(v, int)}) + [v for v in dict.fromkeys(each[k]) if not isinstance(v, int)]


def _each_value(node, bound, each):
    """`bound` once for every way the names of `each` that `node` reads can each take one of their values there (just
    `bound` when it reads none), each such name holding that one value (_values())."""
    names = sorted({n.id for n in ast.walk(node) if isinstance(n, ast.Name) and each.get(n.id)})
    for vals in itertools.product(*(_values(each, k) for k in names)):
        yield {**bound, **{k: [ast.Constant(v)] for k, v in zip(names, vals)}}


def offset_base(node, bound=None, each=None):
    """The constant in the range that a sum or difference with an unbounded operand is built on (40000 + i: 40000), read
    through str(), int() and a unary plus and down a chain of sums and differences; None when no constant operand alone
    is in the range. literal() hands it as `bound` every value the census records for each name (BOUND), and as
    `each` the constants it records for each name, each of which the operand is read with in turn, whatever the name's
    other bindings, a value other than an int adding nothing but inside int(): BASE + i, with BASE bound to 40000, or to
    40000 and to 50000, or to 40000 and to "x", with or without BASE = f() beside them, is built on 40000, and so is
    int(BASE) + i with BASE bound to "40000" and to "50000". literal() calls it once, where interval() gives no
    reading in one of the mixes it reads a value's names by, since it reads each name by each value alike in every
    mix: 40000 + K, with K bound to 30000 and by K = f(), which interval() reads as 70000 by K's int and not at all
    with K unbounded, is built on 40000. An operand with more ways than EACH to take its names' values is read once,
    each name holding every value it is read by, and the sum counts as built on the lowest value of that span in the
    range when the span reaches it (it holds every way's reading, so this over-reads only), or on 32768 when it gives
    no reading and holds a ** or a <<, whose cap at 2**BIG can leave a wide reading empty where one way has a value."""
    bound, each = bound or {}, each or {}
    if isinstance(node, ast.Call) and _callee(node.func) in ("str", "int") and len(node.args) == 1 and not node.keywords:
        return offset_base(node.args[0], bound, each)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return offset_base(node.operand, bound, each)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        for side in (node.left, node.right):
            names = sorted({n.id for n in ast.walk(side) if isinstance(n, ast.Name) and each.get(n.id)})
            ways = 1
            for k in names:
                ways *= len(_values(each, k))
            if ways > EACH:                         # once, each name holding every value it is read by: their spans
                iv = interval(side, {**bound, **{k: [ast.Constant(v) for v in _values(each, k)] for k in names}})
                if iv and min(iv[:2]) <= HIGH and max(iv[:2]) >= LOW:
                    return max(min(iv[:2]), LOW)    # it holds every way's reading: an over-read where none is in range
                if iv is None and any(isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Pow, ast.LShift))
                                      for n in ast.walk(side)):
                    return LOW                      # a ** or << past 2**BIG can leave the spans unread, one way not
            else:
                for table in _each_value(side, bound, each):
                    iv = interval(side, table)
                    if iv and not iv[2] and in_range(iv[0]):
                        return iv[0]
            got = offset_base(side, bound, each)
            if got is not None:
                return got
    return None


# The places Python's grammar binds a name (BOUND, in THE RULE), read from the ast: a Name in any context but Load (a
# Store; a Del, which unbinds it), an import's alias, and each node field that can hold a name, classified here as one
# that binds the name it holds (True) or one that holds something else (False). A field that holds a string and is not
# classified here, as one a later Python adds would be, counts as a binding the census does not record, so a form the
# census does not know leaves a name unbounded rather than read by its other values.
BINDING_FIELDS = {
    ("FunctionDef", "name"): True, ("AsyncFunctionDef", "name"): True, ("ClassDef", "name"): True, ("arg", "arg"): True,
    ("ExceptHandler", "name"): True, ("Global", "names"): True, ("Nonlocal", "names"): True, ("MatchAs", "name"): True,
    ("MatchStar", "name"): True, ("MatchMapping", "rest"): True, ("TypeVar", "name"): True, ("ParamSpec", "name"): True,
    ("TypeVarTuple", "name"): True,
    ("Name", "id"): False, ("alias", "name"): False, ("alias", "asname"): False,   # read by the context and the import
    ("Attribute", "attr"): False, ("keyword", "arg"): False, ("ImportFrom", "module"): False,
    ("MatchClass", "kwd_attrs"): False, ("Constant", "value"): False, ("Constant", "kind"): False,
    ("MatchSingleton", "value"): False, ("Interpolation", "str"): False, ("TypeIgnore", "tag"): False,
    **{(t, "type_comment"): False for t in ("FunctionDef", "AsyncFunctionDef", "Assign", "For", "AsyncFor", "With",
                                            "AsyncWith", "arg")}}


def _target_names(t):
    """The Names an assignment target binds: the target itself, or each one inside a tuple, list or starred target."""
    if isinstance(t, ast.Name):
        return [t]
    if isinstance(t, ast.Starred):
        return _target_names(t.value)
    if isinstance(t, (ast.Tuple, ast.List)):
        return [x for e in t.elts for x in _target_names(e)]
    return []


def _names_held(n):
    """The names the node `n` writes where Python's grammar binds or reads one: a Name's id, the name an import's alias
    binds (import a.b binds a; none for a star), and each name in a field BINDING_FIELDS says binds it, or does not
    classify."""
    if isinstance(n, ast.Name):
        return [n.id]
    if isinstance(n, ast.alias):
        return [] if n.name == "*" else [n.asname or n.name.split(".")[0]]
    out = []
    for field, v in ast.iter_fields(n):
        held = [v] if isinstance(v, str) else [x for x in v if isinstance(x, str)] if isinstance(v, list) else []
        if held and BINDING_FIELDS.get((type(n).__name__, field), True):
            out += held
    return out


def mangled_names(tree):
    """{name: spellings}: each name Python mangles that `tree` writes anywhere in a class statement, a read included,
    with the spelling it mangles to for each class it is written in (an outer one too). Inside a class Python mangles a
    name written with two leading underscores and not two trailing ones: __K there is _C__K, C the class's name less
    its leading underscores, and a class whose name is underscores alone mangles nothing."""
    out = {}
    for n in ast.walk(tree):
        cls = n.name.lstrip("_") if isinstance(n, ast.ClassDef) else ""
        if cls:
            for x in ast.walk(n):
                for name in _names_held(x):
                    if name.startswith("__") and not name.endswith("__"):
                        out.setdefault(name, set()).add("_" + cls + name)
    return out


def unrecorded_bindings(tree, recorded, mangled=None):
    """(names, star): the names `tree` binds anywhere by a binding the census does not record (BOUND), and True when it
    holds a star import, which binds names its text does not write. A binding is a Name in a Store or Del context not
    in `recorded` (the ids of the Names _bind recorded a value for), an import's alias (import a.b binds a), and the
    name held in a field BINDING_FIELDS says binds it, or does not classify. A binding of a name Python mangles in a
    class, written one way, binds the name read the other, so each name of `mangled` (mangled_names() of the tree when
    not given) and each spelling it mangles to count here."""
    names, star = set(), False
    for n in ast.walk(tree):
        if isinstance(n, ast.alias) and n.name == "*":
            star = True
        elif not (isinstance(n, ast.Name) and (isinstance(n.ctx, ast.Load) or id(n) in recorded)):
            names.update(_names_held(n))
    for name, spellings in (mangled_names(tree) if mangled is None else mangled).items():
        names.update({name} | spellings)
    return names, star


class _Scan:
    """One module's (or one code text's) Python reading; hits are (line, number, why)."""

    def __init__(self, own, product, line_of, depth, src=None, helpers=None):
        self.own, self.product, self.line_of, self.depth, self.src = own, product, line_of, depth, src
        self.helpers = helpers or _no_helpers
        self.inherited = ({}, {})                   # the imports of the module a code text sits in
        self.hits = []

    def _place(self, est, v, first, last):
        """The line among `first`-`last` of the module's source that writes the number `v`, nearest the estimate `est`
        (several pieces of one literal can sit on separate lines); `est` when no line there writes it or the source is
        not at hand."""
        if not self.src:
            return est
        rx = re.compile(r"(?<!\d)%d(?!\d)" % v)
        cands = [i for i in range(first, last + 1) if i - 1 < len(self.src) and rx.search(self.src[i - 1])]
        return min(cands, key=lambda i: abs(i - est)) if cands else est

    def _imports(self, tree):
        """The functions of tests/ modules the module imports: {local name: defs} and {module alias: {name: defs}}."""
        imported, modules = dict(self.inherited[0]), dict(self.inherited[1])
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module and not n.level:
                for a in n.names:
                    if a.name == "*":
                        imported.update(self.helpers(n.module) or {})
                        continue
                    sub = self.helpers(n.module + "." + a.name)
                    if sub is not None:
                        modules[a.asname or a.name] = sub
                        continue
                    defs = self.helpers(n.module)
                    if defs is not None and a.name in defs:
                        imported[a.asname or a.name] = defs[a.name]
            elif isinstance(n, ast.Import):
                for a in n.names:
                    if a.asname or "." not in a.name:
                        defs = self.helpers(a.name)
                        if defs is not None:
                            modules[a.asname or a.name] = defs
        return imported, modules

    def _resolve(self, f):
        """The (parameters, *args) of every function the callee `f` resolves to: the module's own, a tests/ module's it
        imports, else (a name such a module only re-exports too) the product's by name."""
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name) and f.value.id in self.modules \
                and f.attr in self.modules[f.value.id]:
            return self.modules[f.value.id][f.attr]
        name = _callee(f)
        if name is None:
            return ()
        if name in self.own:
            return self.own[name]
        if isinstance(f, ast.Name) and name in self.imported:
            return self.imported[name]
        return self.product.get(name, ())

    def _host(self, node):
        """The loopback or wildcard host `node` writes: such a literal, or a name the module binds only to non-empty such
        literals; else None."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value in LOOPBACK:
            return node.value
        if isinstance(node, ast.Name):
            lits = self.bound.get(node.id, ())
            if lits and all(isinstance(x, ast.Constant) and isinstance(x.value, str) and x.value and x.value in LOOPBACK
                            for x in lits):
                return lits[0].value
        return None

    def _template(self, node):
        """The text of a format template: a string literal, or a name the module binds to exactly one."""
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.Name):
            lits = self.bound.get(node.id, ())
            if len(lits) == 1 and isinstance(lits[0], ast.Constant) and isinstance(lits[0].value, str):
                return lits[0].value
        return None

    def _rendered(self, node):
        """The text a string expression renders, each piece the census cannot read standing as \x00: a string literal, a
        name the module binds to exactly one, an f-string's literal parts, and a sum (+) of them, walked without
        recursion so a long chain of sums costs no stack. A NUL the source writes is read through _as_text, so it is
        never taken for the placeholder."""
        out, stack = [], [node]
        while stack:
            x = stack.pop()
            if isinstance(x, ast.BinOp) and isinstance(x.op, ast.Add):
                stack.extend((x.right, x.left))
            elif isinstance(x, ast.JoinedStr):
                out.extend(_as_text(p.value) if isinstance(p, ast.Constant) and isinstance(p.value, str) else "\x00"
                           for p in x.values)
            else:
                t = self._template(x)
                out.append("\x00" if t is None else _as_text(t))
        return "".join(out)

    def _formatted(self, tmpl, args, keywords):
        """Each operand str.format places right after an address's colon in the template `tmpl`. A field takes the next
        automatic number before the fields nested in its format spec take theirs ("{:{}}" takes two). A field is
        numbered when its name before any . or [ is decimal digits alone (str.isdecimal(), the test str.format makes),
        so a superscript digit, which str.isdigit() accepts and int() refuses, makes a name. The template is not read
        when string.Formatter().parse refuses it or a field's spec, when a field nested in a spec has an opening brace
        in its own spec, or when automatic and numbered fields mix: str.format refuses each of those for the text
        alone. Nothing else it refuses is checked (a field with no operand, an unknown conversion, a spec an operand
        refuses)."""
        try:
            fields = [(lit, field, [(f, s) for _l, f, s, _c in string.Formatter().parse(spec or "") if f is not None])
                      for lit, field, spec, _conv in string.Formatter().parse(tmpl)]
        except ValueError:
            return
        heads = [re.match(r"[^.\[]*", f).group(0) for _lit, field, nested in fields if field is not None
                 for f in [field] + [f for f, _s in nested]]          # each field's name before any . or [, in str.format's order
        numbering = {"automatic" if h == "" else "numbered" for h in heads if h == "" or h.isdecimal()}
        if len(numbering) > 1 or any("{" in s for _lit, _field, nested in fields for _f, s in nested):
            return                                  # str.format refuses a switch of numbering, and a field nested two deep
        rendered, auto = "", 0
        for lit, field, nested in fields:
            rendered += _as_text(lit)
            if field is None:
                continue
            head = re.match(r"[^.\[]*", field).group(0)
            if head == "":
                arg, auto = (args[auto] if auto < len(args) else None), auto + 1
            elif head.isdecimal():
                arg = args[int(head)] if int(head) < len(args) else None
            else:
                arg = keywords.get(head)
            auto += sum(1 for f, _s in nested if re.match(r"[^.\[]*", f).group(0) == "")   # the spec's automatic fields
            if arg is not None and head == field and not isinstance(arg, ast.Starred) and _ADDR_END.search(rendered):
                self._value(arg, "an operand formatted into an address")
            rendered += "\x00"

    def _record(self, node, v, why):
        self.hits.append((self.line_of(node), v, why))

    def literal(self, node, why, strings=True):
        """The numbers `node` writes as a port: an int constant, a five-digit string (when `strings`), each element of a
        tuple, list or set display of them, a bounded expression that can reach the range, or a sum or difference built
        on a constant in the range."""
        if isinstance(node, ast.Constant):
            v = node.value
            if in_range(v):
                self._record(node, v, why)
            elif strings and in_range(_digits(v)):
                self._record(node, _digits(v), why)
        elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            for e in node.elts:
                self.literal(e, why, strings)
        else:                                       # (BOUND) each name with a binding the census does not record, two ways
            loose = sorted({x.id for x in ast.walk(node) if isinstance(x, ast.Name) and x.id in self.reads
                            and x.id not in self.fixed})
            if 2 ** len(loose) > MIXES:
                self._record(node, LOW, "%s, refused: it reads %d names with a binding the census does not record (%s), "
                             "more ways to read them than %d" % (why, len(loose), ", ".join(loose), MIXES))
                return
            got, based = [], False
            for mix in itertools.product((False, True), repeat=len(loose)):   # True: that name read unbounded
                unbounded = {k for k, u in zip(loose, mix) if u}
                iv = interval(node, {k: v for k, v in self.reads.items() if k not in unbounded}, self.steps)
                if iv and iv[2] and iv[0] <= HIGH and iv[1] >= LOW:
                    got.append((max(iv[0], LOW), "%s, computed into %d-%d" % (why, iv[0], iv[1])))
                elif iv and not iv[2] and in_range(iv[0]):
                    got.append((iv[0], why + ", a constant expression"))
                elif iv is None and not based:      # offset_base() reads each name by each value in every way alike
                    based, base = True, offset_base(node, self.reads, self.each)
                    if base is not None:
                        got.append((base, "%s, an offset from %d" % (why, base)))
            for v, reading in dict.fromkeys(got):     # each reading once, the ways often agreeing
                self._record(node, v, reading)

    def _bind(self, t, v):
        """Records the value `v` gives each name the target `t` binds (BOUND), and the id of each Name it records one
        for; a name the target gives any other value (K = f(), B = A, 0 - 7; a starred target; a tuple target over
        anything but a display of its length) goes in self.loose, a binding the census does not record."""
        if isinstance(t, ast.Name) and isinstance(v, (ast.Constant, ast.Tuple, ast.List, ast.Set)):
            self.bound.setdefault(t.id, []).append(v)
            self.recorded.add(id(t))
        elif isinstance(t, ast.Name) and _signed_number(v) is not None:   # -7 is a unary minus over 7: the number it computes
            self.bound.setdefault(t.id, []).append(ast.copy_location(ast.Constant(_signed_number(v)), v))
            self.recorded.add(id(t))
        elif isinstance(t, (ast.Tuple, ast.List)) and isinstance(v, (ast.Tuple, ast.List)) and len(t.elts) == len(v.elts):
            for te, ve in zip(t.elts, v.elts):
                self._bind(te, ve)
        else:
            self.loose.update(x.id for x in _target_names(t))

    def _value(self, v, why, strings=True):
        if isinstance(v, ast.Name) and v.id in self.reads:
            self.uses.append((v.id, why, strings))
        else:
            self.literal(v, why, strings)

    def scan(self, tree):
        docs = _docstrings(tree)
        self.bound, self.uses, self.recorded, self.loose = {}, [], set(), set()
        self.imported, self.modules = self._imports(tree)
        for n in ast.walk(tree):
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and n.value is not None:
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    self._bind(t, n.value)
            elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)) and isinstance(n.iter, (ast.Tuple, ast.List, ast.Set)):
                for e in n.iter.elts:
                    self._bind(n.target, e)
        # What interval() reads a name by (BOUND). Anywhere but at a randrange's step: every name, by the ints the census
        # records for it, their union (self.reads, every value recorded, of which interval() reads the ints); and, for an
        # expression that reads names with a binding the census does not record (every name beside a star import; the
        # names not in self.fixed), once for each way of reading each such name by its ints or unbounded, the union of
        # all (literal(), which refuses a value with more ways than MIXES). At a step, and anywhere inside one: a name
        # every binding of which the census records, when each gives an int (self.steps), so a name with such a binding
        # is unbounded there in every way. The hop reads self.reads too, and a host and a template read self.bound, every
        # value recorded under the spelling written; offset_base, the same in every way, reads each name by each of its
        # values in turn (self.each), of which interval() reads the ints, and int() of the name any value int() takes. A
        # name Python mangles in a class reads, under the spelling written in the class, the values of both spellings,
        # the one each class it is written in mangles it to too (self.reads).
        mangled = mangled_names(tree)
        loose, star = unrecorded_bindings(tree, self.recorded, mangled)
        loose |= self.loose
        self.reads = dict(self.bound)
        for name, spellings in mangled.items():
            joined = self.bound.get(name, []) + [x for s in sorted(spellings) for x in self.bound.get(s, ())]
            if joined:
                self.reads[name] = joined
        self.fixed = {k: v for k, v in self.reads.items() if not star and k not in loose}
        self.steps = {k: v for k, v in self.fixed.items()
                      if all(isinstance(x, ast.Constant) and isinstance(x.value, int) for x in v)}
        self.each = {k: [x.value for x in v if isinstance(x, ast.Constant)] for k, v in self.reads.items()}
        for n in ast.walk(tree):
            if isinstance(n, ast.Dict):
                for k, v in zip(n.keys, n.values):
                    key = k.value if isinstance(k, ast.Constant) else (k.id if isinstance(k, ast.Name) else None)
                    if names_a_port(key):
                        self._value(v, "the value of the key %r" % key)
            elif isinstance(n, ast.Call):
                for kw in n.keywords:
                    if names_a_port(kw.arg):
                        self._value(kw.value, "the keyword %s=" % kw.arg)
                if len(n.args) >= 2 and isinstance(n.args[0], ast.Constant) and names_a_port(n.args[0].value):
                    self._value(n.args[1], "the value handed with the name %r" % n.args[0].value)
                name = _callee(n.func)
                for params, star in self._resolve(n.func):
                    for i, a in enumerate(n.args):
                        p = params[i] if i < len(params) else star
                        if names_a_port(p) and not isinstance(a, ast.Starred):
                            self._value(a, "the argument %s of %s()" % (p, name), strings=False)
                for i in range(len(n.args) - 1):
                    h = self._host(n.args[i])
                    if h and not isinstance(n.args[i + 1], ast.Starred):        # the empty string is a host in a tuple only
                        self._value(n.args[i + 1], "the argument after the host %r" % h, strings=False)
                if isinstance(n.func, ast.Attribute) and n.func.attr == "format":
                    tmpl = self._template(n.func.value)
                    if tmpl is not None:
                        self._formatted(tmpl, n.args, {k.arg: k.value for k in n.keywords if k.arg})
            elif isinstance(n, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.NamedExpr)) and n.value is not None:
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    if isinstance(t, (ast.Tuple, ast.List)):
                        if isinstance(n.value, (ast.Tuple, ast.List)) and len(t.elts) == len(n.value.elts):
                            for te, ve in zip(t.elts, n.value.elts):
                                if names_a_port(_target_name(te)):
                                    self._value(ve, "an assignment to %s" % _target_name(te))
                    elif names_a_port(_target_name(t)):
                        self._value(n.value, "an assignment to %s" % _target_name(t))
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                a = n.args
                pos = a.posonlyargs + a.args
                for arg, d in list(zip(pos[len(pos) - len(a.defaults):], a.defaults)) + list(zip(a.kwonlyargs, a.kw_defaults)):
                    if d is not None and names_a_port(arg.arg):
                        self._value(d, "the default of %s" % arg.arg)
            elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)) and isinstance(n.iter, (ast.Tuple, ast.List, ast.Set)):
                t = n.target
                if isinstance(t, (ast.Tuple, ast.List)):
                    for i, te in enumerate(t.elts):
                        if names_a_port(_target_name(te)):
                            for e in n.iter.elts:
                                if isinstance(e, (ast.Tuple, ast.List)) and i < len(e.elts):
                                    self.literal(e.elts[i], "the loop target %s" % _target_name(te))
                elif names_a_port(_target_name(t)):
                    for e in n.iter.elts:
                        self.literal(e, "the loop target %s" % _target_name(t))
            elif isinstance(n, (ast.Tuple, ast.List)) and len(n.elts) >= 2:
                h = self._host(n.elts[0])
                if h is not None:
                    self._value(n.elts[1], "the port of the address (%r, ...)" % h, strings=False)
                for i in range(len(n.elts) - 1):
                    flag = _port_flag(n.elts[i])
                    if flag and not isinstance(n.elts[i + 1], ast.Starred):
                        self._value(n.elts[i + 1], "the argument after the flag %s" % flag)
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod):
                tmpl = self._template(n.left)
                if tmpl is not None and _ADDR_PCT.search(tmpl):
                    self._value(n.right, "an operand formatted into an address")
            elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
                if _ADDR_END.search(self._rendered(n.left)):
                    self._value(n.right, "a port concatenated onto an address")
            elif isinstance(n, ast.JoinedStr):
                rendered = ""
                for piece in n.values:
                    if isinstance(piece, ast.FormattedValue):
                        if _ADDR_END.search(rendered):
                            self._value(piece.value, "an operand formatted into an address")
                        rendered += "\x00"
                    elif isinstance(piece, ast.Constant) and isinstance(piece.value, str):
                        rendered += _as_text(piece.value)
            if isinstance(n, ast.Constant) and isinstance(n.value, (str, bytes)) and id(n) not in docs:
                s = n.value if isinstance(n.value, str) else n.value.decode("latin-1")
                if FIVE.search(s):
                    self._string(n, s, code=isinstance(n.value, str))
        for name, why, strings in self.uses:
            for lit in self.reads.get(name, ()):
                self.literal(lit, "%s, through the name %s" % (why, name), strings)

    def _string(self, n, s, code=True):
        """A string literal's reading: code text both ways (the Python rules and the text rules over its code), any other
        string, and a bytes literal, by the text rules."""
        first, last = self.line_of(n), self.line_of(n, end=True)
        sub = None
        if code and self.depth < MAX_CODE_DEPTH:
            try:
                sub = ast.parse(s)
            except (SyntaxError, ValueError, RecursionError, MemoryError):
                sub = None
        if sub is not None and sub.body:
            total = s.count("\n")

            def line_of(x, end=False, first=first, last=last, total=total):
                return _line_in(first, last, total - (getattr(x, "end_lineno" if end else "lineno", 1) - 1))
            inner = _Scan(defs_of(sub, dict(self.own)), self.product, line_of, self.depth + 1, self.src, self.helpers)
            inner.inherited = (self.imported, self.modules)
            inner.scan(sub)
            found = inner.hits + text_hits(code_text_tokens(s), first, last)
            self.hits.extend((self._place(ln, v, first, last), v, "in code text, " + why) for ln, v, why in found)
        else:
            self.hits.extend((self._place(ln, v, first, last), v, why) for ln, v, why in text_hits(s, first, last))


def scan_python(tree, product, text=None, helpers=None):
    """[(line, number, why)], sorted and one per (line, number), for a parsed module; `text`, the module's source, places a
    hit inside a string literal on the physical line that writes it; `helpers`, a HelperModules, resolves what the module
    imports from tests/."""
    def line_of(x, end=False):
        return getattr(x, "end_lineno" if end else "lineno", 1) or 1
    sc = _Scan(defs_of(tree), product, line_of, 0, text.split("\n") if text is not None else None, helpers)
    sc.scan(tree)
    return _one_per_place(sc.hits)


def _one_per_place(hits):
    seen, out = set(), []
    for line, v, why in sorted(hits):
        if (line, v) not in seen:
            seen.add((line, v))
            out.append((line, v, why))
    return out


# The population.
def files(root):
    """Every file the census reads under `root`: the files under tests/, and every *.test.* file and fixtures file
    elsewhere, outside SKIP_DIRS and every hidden directory (.git; .claude, where a clone may keep worktrees of other
    commits; .venv); symlinks skipped."""
    out = []
    for d, dirs, names in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP_DIRS and not x.startswith("."))
        parts = os.path.relpath(d, root).split(os.sep)
        for f in sorted(names):
            p = os.path.join(d, f)
            if os.path.islink(p) or not os.path.isfile(p):
                continue
            if parts[0] == "tests" or ".test." in f or "fixtures" in parts:
                out.append(p)
    return out


def product_defs(root):
    into = {}
    for sub in PRODUCT_DIRS:
        base = os.path.join(root, sub)
        for f in sorted(os.listdir(base)):
            if f.endswith(".py"):
                defs_of(parse_cache.source_and_tree(os.path.join(base, f))[1], into)
    return into


def census(root):
    """{"hits": [(path relative to root, line, number, why)], "files": n, "python_read": n, "product_defs": n,
    "helper_modules": n}."""
    product = product_defs(root)
    helpers = HelperModules(root)
    hits, n_files, n_py = [], 0, 0
    for p in files(root):
        n_files += 1
        rel = os.path.relpath(p, root)
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        if not any(in_range(_num(m.group(1))) for m in FIVE.finditer(text)) and not (p.endswith(".py") and COMPUTED.search(text)):
            continue
        if p.endswith(".py"):
            n_py += 1
            found = scan_python(parse_cache.source_and_tree(p)[1], product, text, helpers)
        else:
            found = _one_per_place(text_hits(text))
        hits += [(rel, line, v, why) for line, v, why in found]
    return {"hits": hits, "files": n_files, "python_read": n_py, "product_defs": len(product),
            "helper_modules": len(helpers.resolved)}


def render(hits):
    return "\n".join("  %s:%d: %d, %s" % h for h in hits)


# The sentinels and the bind bands (THE SENTINELS, in the docstring).
SENTINEL_MODULES = (os.path.join("tests", "test_hermetic_kernel_postal.py"), os.path.join("tests", "test_postal_fixed_port_belt.py"))
PRIVILEGED = 1024                                   # below this, on Linux at the default, an unprivileged bind is refused
SHELL_FILES = (".bats", ".bash", ".sh")
_PER_TEST = re.compile(r"\b(?P<name>\w+)=\$\(\([ \t]*(?P<base>\d+)[ \t]*\+[ \t]*\$\{?BATS_TEST_NUMBER\b")
_SHELL_ADD = re.compile(r"\$\(\([ \t]*\$?(?P<v>\w+)[ \t]*\+[ \t]*(?:(?P<k>\w+)[ \t]*\*[ \t]*)?(?P<c>\d+)[ \t]*\)\)")
_SHELL_FN = re.compile(r"^[ \t]*(?:function[ \t]+)?(\w+)[ \t]*\(\)[ \t]*\{", re.M)
_DRAW_TEXT = re.compile(r"\brandint\([ \t]*(\d+)[ \t]*,[ \t]*(\d+)[ \t]*\)")
_BLOCK = re.compile(r"""["'][\w.-]+\.test\.[cm]?[jt]s["'][ \t]*:[ \t]*\[[ \t]*(\d+)[ \t]*,[ \t]*(\d+)[ \t]*\]""")
_QUOTED_DIGITS = re.compile(r"""(["'])(\d{1,5})\\?\1""")
_AFTER_HOST = re.compile(r"(?:" + _HOST + r"):(\d{1,5})(?![\d.])")
_PORT_INT = re.compile(r"\b(?P<name>\w+)[ \t]*=[ \t]*(?P<n>\d{1,5})(?![\w.])")


def _shell_bands(text):
    """[(lo, hi)]: the ports each per-test base of the shell file `text` makes, with its offsets and retry steps."""
    out = []
    tests = len(re.findall(r"^[ \t]*@test\b", text, re.M))
    for m in _PER_TEST.finditer(text):
        name, base = m.group("name"), int(m.group("base"))
        if not names_a_port(name):
            continue
        offsets, steps = {0}, {0}
        for a in _SHELL_ADD.finditer(text):
            if not names_a_port(a.group("v")):
                continue
            c = int(a.group("c"))
            if a.group("k") is None:
                if a.group("v") == name:
                    offsets.add(c)
                continue
            fns = list(_SHELL_FN.finditer(text, 0, a.start()))
            if fns:
                helper = re.escape(fns[-1].group(1))
                tries = [int(t) for t in re.findall(r"\b" + helper + r"[ \t]+(?:\"[^\"\n]*\"|\S+)[ \t]+(\d+)\b", text)]
                steps |= {c * i for i in range(max(tries, default=1))}
        out += [(base + o + st, base + tests + o + st) for o in sorted(offsets) for st in sorted(steps)]
    return out


def _python_draws(tree):
    """[(a, b)]: every call to randint(a, b) in `tree` whose two arguments are int literals, each given by position or
    by its parameter's name: the arguments THE RULE's port reading takes from a random call (_random_args()), since
    every reader of a random call is one population (randint(a=A, b=B) and randint(A, b=B) are randint(A, B);
    randint(b=B) is no draw, and neither is randint(A, B, a=C), which Python refuses)."""
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and _callee(n.func) == "randint":
            args = _random_args(n)
            if args and len(args) == 2 and all(isinstance(a, ast.Constant) and type(a.value) is int for a in args):
                out.append((args[0].value, args[1].value))
    return out


def bind_bands(root):
    """[(lo, hi, where)]: every band of ports a test binds, derived from THE FILES under `root` (THE BIND BANDS)."""
    out = [(LOW, HIGH, "the ephemeral range")]
    for p in files(root):
        rel = os.path.relpath(p, root)
        try:
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
        except (UnicodeDecodeError, OSError):
            continue
        draws = []
        if p.endswith(SHELL_FILES):
            out += [(lo, hi, "%s: a per-test base" % rel) for lo, hi in _shell_bands(text)]
            draws = [(int(a), int(b)) for a, b in _DRAW_TEXT.findall(text)]
        elif p.endswith(".py") and "randint(" in text:
            draws = _python_draws(parse_cache.source_and_tree(p)[1])
        out += [(a, b, "%s: a draw" % rel) for a, b in draws if a >= PRIVILEGED]
        if p.endswith((".js", ".mjs", ".cjs", ".ts")):
            out += [(int(a), int(b), "%s: a block" % rel) for a, b in _BLOCK.findall(text)]
    return out


def sentinel_values(text):
    """[(line, number, why)]: every number the module `text` writes as text a process could take for a port."""
    out = []
    for rx, group, why in ((_QUOTED_DIGITS, 2, "a quoted digit string"), (_AFTER_HOST, 1, "a number after a loopback host"),
                           (_PORT_INT, "n", "an int assigned to a port-named name")):
        for m in rx.finditer(text):
            if group == "n" and not names_a_port(m.group("name")):
                continue
            out.append((text.count("\n", 0, m.start()) + 1, int(m.group(group)), why))
    return out


def sentinel_faults(root, bands, modules=SENTINEL_MODULES):
    """[(module, line, number, why, band's where, lo, hi)]: each number the `modules` write as a port that a band holds."""
    out = []
    for rel in modules:
        with open(os.path.join(root, rel), encoding="utf-8") as fh:
            text = fh.read()
        for line, v, why in sentinel_values(text):
            out += [(rel, line, v, why, where, lo, hi) for lo, hi, where in bands if lo <= v <= hi]
    return out


# The bands tests/manager-ports.js's header lists (THE HEADER'S BANDS, in the docstring).
MANAGER_PORTS = os.path.join("tests", "manager-ports.js")
_HEADER_LIST = re.compile(r"sits under every band[^:]*:(?P<list>.*?)\.(?:\s|$)", re.S)
_RANGE = re.compile(r"(?<![\d.])(\d{4,5})-(\d{4,5})(?![\d.])")


def header_band_faults(root, bands):
    """[str]: each range tests/manager-ports.js's header lists among the bands other suites draw from that reaches the
    ephemeral range or holds no band `bands` derives from another file; one fault when the list cannot be read."""
    try:
        with open(os.path.join(root, MANAGER_PORTS), encoding="utf-8") as fh:
            text = fh.read()
    except (UnicodeDecodeError, OSError) as e:
        return ["%s cannot be read: %s" % (MANAGER_PORTS, e)]
    comments = " ".join(re.sub(r"^//[ \t]?", "", l.strip()) for l in text.splitlines() if l.strip().startswith("//"))
    m = _HEADER_LIST.search(comments)
    ranges = [(int(a), int(b)) for a, b in _RANGE.findall(m.group("list"))] if m else []
    if not ranges:
        return ["%s's header has no sentence 'It also sits under every band ...: <ranges>.' with a range in it" % MANAGER_PORTS]
    # The file's own blocks aside. The ephemeral range needs no exclusion: only a range that reaches it could hold it,
    # and such a range is refused first.
    others = [(lo, hi) for lo, hi, where in bands if not where.startswith(MANAGER_PORTS)]
    out = []
    for lo, hi in ranges:
        if hi >= LOW:
            out.append("%d-%d reaches the ephemeral range (%d-%d), where this census refuses a port, so no test draws "
                       "from it" % (lo, hi, LOW, HIGH))
        elif not any(lo <= blo and bhi <= hi for blo, bhi in others):
            out.append("%d-%d holds no band a test draws from (bind_bands())" % (lo, hi))
    return out


# The pins.
class NoFixedEphemeralPort(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = parse_cache.derived("ephemeral_port_census", lambda: census(ROOT))

    def test_no_test_writes_a_fixed_port_in_the_ephemeral_range(self):
        hits = self.result["hits"]
        if hits:
            self.fail("%d fixed port(s) in %d-%d written as a port. Any process can hold a listener on such a port, so a "
                      "dial to it can hang. Use port 1 for a dial that never lands (2, 3 and on for a row's other ports), "
                      "and a bind to port 0 or tests/lab_ports.reserve for a listener; this module's docstring states the "
                      "rule and what it excludes:\n%s" % (len(hits), LOW, HIGH, render(hits)))

    def test_the_population_is_not_empty(self):
        self.assertGreater(self.result["files"], 1000, "the walk read the tests and the node suites")
        self.assertGreater(self.result["python_read"], 50, "Python modules with a number in the range were read")
        self.assertGreater(self.result["product_defs"], 1000, "the product's functions are the resolver's index")
        self.assertGreater(self.result["helper_modules"], 5, "the tests/ modules the read modules import were indexed")
        self.assertIn(os.path.join(ROOT, "tests", "test_postal_token.py"), files(ROOT))
        self.assertIn(os.path.join(ROOT, "tests", "fixtures"), {os.path.dirname(p) for p in files(ROOT)})


def _n(k=0):
    """A number in the range, built at run time so this file holds none in a port position: LOW + 12233 + k."""
    return LOW + 12233 + k


def _sep(v):
    """`v` written with a digit separator (45_001)."""
    return "%d_%03d" % (v // 1000, v % 1000)


def _arabic(v):
    """`v` written in Arabic-Indic digits, decimal digits other than ASCII's."""
    return "".join(chr(0x660 + int(d)) for d in str(v))


# Each way to bind a name that the census does not record (BOUND), as the lines that write it for the name {k}: a Name
# stored by anything but =, an annotated = or := of a value the census records, or a for or a comprehension over a
# display of such values; a Name deleted; an import's alias; and each field BINDING_FIELDS says binds (the places
# unrecorded_bindings() reads). "{k} = {v}" goes first, {v} the int the census records, unless a line writes {v}
# itself. Each parses on 3.10 and later; UNRECORDED_FORMS_312 holds the forms 3.12 added. A star import is no entry:
# it unbounds every name of its module at a step
# (test_a_name_with_a_binding_the_census_does_not_record_is_unbounded_at_a_step).
UNRECORDED_FORMS = (
    ("a call's result", ("{k} = f()",)),
    ("another name", ("{k} = A",)),
    ("an expression the census records no value for", ("{k} = 0 - 7",)),
    ("an annotated assignment of a call's result", ("{k}: int = f()",)),
    ("an annotation with no value", ("{k}: int",)),
    ("an augmented assignment", ("{k} *= -1",)),
    ("a tuple target over a call's result", ("{k}, {k}b = f()",)),
    ("a tuple target over a display of another length", ("{k}, {k}b = 1, 2, 3",)),
    ("a starred target", ("{k}a, *{k} = 1, 2",)),
    ("a walrus over a call's result", ("if ({k} := f()):", "    pass")),
    ("a for target over a call's result", ("for {k} in range(3):", "    pass")),
    ("a for target over a display holding a call's result", ("for {k} in ({v}, f()):", "    pass")),
    ("a for target unpacking an element the census does not record", ("for {k}, {k}b in (({v}, 1), f()):", "    pass")),
    ("a comprehension target over a call's result", ("{k}c = [0 for {k} in range(3)]",)),
    ("a with target", ("with f() as {k}:", "    pass")),
    ("an except target", ("try:", "    pass", "except OSError as {k}:", "    pass")),
    ("a parameter", ("def {k}f({k}):", "    pass")),
    ("a lambda's starred parameter", ("{k}f = lambda *{k}: 0",)),
    ("a function's name", ("def {k}():", "    pass")),
    ("an async function's name", ("async def {k}():", "    pass")),
    ("a class's name", ("class {k}:", "    pass")),
    ("an import", ("import {k}",)),
    ("a dotted import", ("import {k}.sub",)),
    ("an import under another name", ("import m as {k}",)),
    ("a from-import", ("from m import {k}",)),
    ("a from-import under another name", ("from m import x as {k}",)),
    ("a del", ("del {k}",)),
    ("a global statement", ("def {k}f():", "    global {k}")),
    ("a nonlocal statement", ("def {k}f():", "    {k} = {v}", "    def g():", "        nonlocal {k}")),
    ("a match capture", ("match x:", "    case {k}:", "        pass")),
    ("a match's starred capture", ("match x:", "    case [*{k}]:", "        pass")),
    ("a match mapping's rest", ("match x:", "    case {**{k}}:", "        pass")))
UNRECORDED_FORMS_312 = (
    ("a type alias", ("type {k} = int",)),
    ("a type parameter", ("def {k}f[{k}]():", "    pass")),
    ("a type parameter tuple", ("class {k}c[*{k}]:", "    pass")),
    ("a parameter specification", ("def {k}f[**{k}]():", "    pass")))
# Each way a name Python mangles in a class gives the name a read sees a binding the census files under the other
# spelling (unrecorded_bindings()), as (label, the lines before the call, the call's indent, the name as the call
# writes it): {k} the name as the class writes it, two leading underscores first, {c} the class, and {v} the int the
# census records under the spelling the call writes, or, in the last, under the mangled spelling, which the name the
# call writes in a method reads (mangled_names()).
MANGLED_FORMS = (
    ("a name read in a class body, its mangled spelling bound by a call", ("{k} = {v}", "_{c}{k} = f()", "class {c}:"),
     4, "{k}"),
    ("a mangled spelling read outside its class, bound in it under a global statement by a call",
     ("_{c}{k} = {v}", "class {c}:", "    def g(self):", "        global {k}", "        {k} = f()"), 0, "_{c}{k}"),
    ("a name read in a method, its mangled spelling bound in the module", ("_{c}{k} = {v}", "class {c}:",
                                                                          "    def m(self):"), 8, "{k}"))


def _earlier_readings():
    """[(label, source, readings)]: shapes whose readings two earlier censuses gave, each with those readings, as
    [(number, why)], the union of both censuses' raw readings of the same source (numbers in the range built at run
    time, as _n() builds them; a comment that writes one opens a file no other number does). One read a name with a
    binding the census does not record as unbounded wherever offset_base() did not read it by its one recorded int; the
    other read a name by its value only where it recorded exactly one, and recorded no number written with a sign, so
    with K bound to -1 and to 2 it read K as 2."""
    lo, hi, n = LOW + 7232, LOW + 17232, _n()                                      # 40000, 50000 and 45001
    mod, ass = "%d + K %% %d" % (20000, 20000), "an assignment to port, "
    key, opens = "the value of the key 'port', ", "                # %d opens the file" % n
    return [
        ("% by a constant", "K = 7\nK = f()\nport = %s\n" % mod, [(LOW, ass + "computed into 20000-39999")]),
        ("% by a constant, under a port-named key", 'K = 7\nK = f()\nrow = {"port": %s}\n' % mod,
         [(LOW, key + "computed into 20000-39999")]),
        ("% by a constant, beside a star import", "from m import *\nK = 7\nport = %s\n" % mod,
         [(LOW, ass + "computed into 20000-39999")]),
        ("% by a constant, of a name Python mangles in a class",
         "class C:\n    __K = 7\n    port = %d + __K %% %d\n" % (20000, 20000), [(LOW, ass + "computed into 20000-39999")]),
        ("a sum", "K = %d\nK = f()\nport = %d + K\n" % (30000, lo), [(lo, ass + "an offset from %d" % lo)]),
        ("a sum, the name first", "K = %d\nK = f()\nport = K + %d\n" % (30000, lo), [(lo, ass + "an offset from %d" % lo)]),
        ("a difference", "K = 9000\nK = f()\nport = %d - K\n" % lo, [(lo, ass + "an offset from %d" % lo)]),
        ("a difference, as an address's port", 'K = 9000\nK = f()\ns.bind(("127.0.0.1", %d - K))\n' % lo,
         [(lo, "the port of the address ('127.0.0.1', ...), an offset from %d" % lo)]),
        ("a sum on a quotient by the name", "K = 3\nK = f()\nport = %d + %d // K\n" % (lo, 2 * n),
         [(lo, ass + "an offset from %d" % lo)]),
        ("a sum, the name's int small", "K = 7\nK = f()\nport = %d + K\n" % lo,
         [(lo, ass + "an offset from %d" % lo), (lo + 7, ass + "a constant expression")]),
        ("% by a constant, then a sum", "K = 7\nK = f()\nport = K %% %d + %d\n" % (20000, lo),
         [(lo, ass + "computed into %d-%d" % (lo, lo + 19999)), (lo + 7, ass + "a constant expression")]),
        ("a randrange whose start is under % by a constant", "K = 7\nK = f()\nport = random.randrange(%s, %d)\n" % (mod, hi),
         [(LOW, ass + "computed into 20000-%d" % (hi - 1)), (LOW, ass + "computed into 20007-%d" % (hi - 1))]),
        ("a difference by the name, from a name every binding of which the census records",
         "S = %d\nK = %d\nK = f()\nport = S - K\n" % (70000, lo), [(lo, ass + "an offset from %d" % lo)]),
        ("a sum of the name and a name every binding of which the census records",
         "S = 9000\nK = %d\nK = f()\nport = S + K\n" % n,
         [(n, ass + "an offset from %d" % n), (9000 + n, ass + "a constant expression")]),
        ("% by a constant, of a private name bound only under the spelling its class mangles it to",
         "_C__K = 7\n_C__K = f()\n\n\nclass C:\n    def m(self):\n        port = %s\n" % mod.replace("K", "__K"),
         [(LOW, ass + "computed into 20000-39999")]),
        ("a sum on a private name bound only under the spelling its class mangles it to",
         "_C__K = %d\n_C__K = f()\n\n\nclass C:\n    def m(self):\n        port = %d + __K\n" % (30000, lo),
         [(lo, ass + "an offset from %d" % lo)]),
        ("// by a divisor name bound to a negative and a positive int",
         'K = -1\nK = 2\nrow = {"port": %d // K}%s\n' % (2 * n, opens), [(n, key + "a constant expression")]),
        ("// by a divisor name bound to a negative and a positive int and by a call",
         'K = -1\nK = 2\nK = f()\nrow = {"port": %d // K}%s\n' % (2 * n, opens), [(n, key + "a constant expression")]),
        ("// by a divisor name a loop binds to a negative and a positive int",
         'for K in (-1, 2):\n    row = {"port": %d // K}%s\n' % (2 * n, opens), [(n, key + "a constant expression")]),
        ("// by a divisor name bound to a negative and a positive int, in a randrange's stop",
         "K = -1\nK = 2\nport = random.randrange(%d, %d // K)\n" % (lo, 2 * hi), [(lo, ass + "computed into %d-%d" % (lo, hi - 1))]),
        ("% of one value by a divisor name bound to a negative and a positive int and by a call",
         'K = -1\nK = %d\nK = f()\nrow = {"port": %d %% K}\n' % (hi + 10000, hi), [(hi, key + "a constant expression")]),
        ("an unknown operand of % by a divisor name bound to a negative and a positive int",
         "K = -5\nK = 30000\nport = 20000 + os.getpid() %% K%s\n" % opens, [(LOW, ass + "computed into 20000-49999")]),
        ("an unknown operand of % by a divisor name bound to a negative and a positive int and by a call",
         "K = -5\nK = 30000\nK = f()\nport = 20000 + os.getpid() %% K%s\n" % opens,
         [(LOW, ass + "computed into 20000-49999")]),
        ("% by a constant of a sum of two names, each with a binding the census does not record",
         "A = 7\nA = f()\nB = 9\nB = g()\nport = %d + (A + B) %% %d\n" % (20000, 20000), [(LOW, ass + "computed into 20000-39999")]),
        ("a sum and a difference of two names, each with a binding the census does not record",
         "A = %d\nA = f()\nB = 9000\nB = g()\nport = %d + A - B\n" % (30000, lo),
         [(lo, ass + "an offset from %d" % lo), (lo + 21000, ass + "a constant expression")])]


def _holds(got, old):
    """True when the readings `got`, [(number, why)], hold the reading `old` at its position: a span inside a span got
    reports, a sum built on a constant in the range by any such sum got reports (each claims a value no bound holds,
    whichever constant the census found first), or a constant got reports or a span holding it."""
    rx = re.compile(r"(.*), (?:computed into (-?\d+)-(-?\d+)|a constant expression|an offset from (-?\d+))$")
    o = rx.match(old[1])
    for v, why in got:
        g = rx.match(why)
        if not (g and o and g.group(1) == o.group(1)):
            continue                                # another position, or no reading THE RULE names
        span = (int(g.group(2)), int(g.group(3))) if g.group(2) is not None else None
        if o.group(4) is not None:                  # a sum built on a constant
            if g.group(4) is not None:
                return True
        elif o.group(2) is not None:                # a span
            if span and span[0] <= int(o.group(2)) and span[1] >= int(o.group(3)):
                return True
        elif (span and span[0] <= old[0] <= span[1]) or (g.group(4) is None and span is None and v == old[0]):
            return True                             # a constant
    return False


def _bound_by(name, lines, v):
    """The lines of one of UNRECORDED_FORMS for `name`, after "name = v" unless a line writes {v}, as module text."""
    body = [x.replace("{k}", name).replace("{v}", str(v)) for x in lines]
    return "".join(x + "\n" for x in ([] if any("{v}" in x for x in lines) else ["%s = %d" % (name, v)]) + body)


class Plants(unittest.TestCase):
    """Each planted shape is one hit, read by the rule it names (among any others that read the same place), and each
    excluded shape is green."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        os.makedirs(os.path.join(self.d, "tests"))
        for sub in PRODUCT_DIRS:
            os.makedirs(os.path.join(self.d, sub))
        with open(os.path.join(self.d, "kernel", "k.py"), "w", encoding="utf-8") as f:
            f.write("def _notify_bus_peer(host, port, up):\n    pass\n\n\nclass R:\n    def ring(self, port):\n        pass\n")

    def _write(self, rel, text):
        """`text` at `rel` under the scratch root, by a rename-over: the file takes a new inode, so tests/parse_cache.py,
        which serves the old tree for a same-size rewrite within one tick of a coarse clock, parses each plant afresh."""
        p = os.path.join(self.d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + ".new", "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(p + ".new", p)

    def _hits(self, name, text):
        """The census's hits in the planted file `name` (written fresh under the scratch root's tests/; the root and every
        plant in it go with the test's cleanup)."""
        self._write(os.path.join("tests", name), text)
        return [h for h in census(self.d)["hits"] if h[0] == os.path.join("tests", name)]

    def _whys(self, name, text):
        """Every reason the rules give for the plant, before the census keeps one per place (two rules can read one place,
        a shell export is both a declaration and an upper-case name)."""
        if not name.endswith(".py"):
            return [w for _l, _v, w in text_hits(text)]
        tree = ast.parse(text)
        sc = _Scan(defs_of(tree), product_defs(self.d), lambda x, end=False: getattr(x, "lineno", 1), 0,
                   helpers=HelperModules(self.d))
        sc.scan(tree)
        return [w for _l, _v, w in sc.hits]

    def assertRed(self, name, text, why_part, n=None):
        hits = self._hits(name, text)
        self.assertEqual([h[2] for h in hits], [n or _n()], "%s: one hit, the planted number: %r\n%s" % (name, hits, text))
        whys = self._whys(name, text)
        self.assertTrue(any(why_part in w for w in whys), "%s: read by the rule %r: %r" % (name, why_part, whys))

    def assertGreen(self, name, text):
        hits = self._hits(name, text)
        self.assertEqual(hits, [], "%s: excluded, yet counted:\n%s\n%s" % (name, render(hits), text))

    def test_the_python_positions(self):
        n = _n()
        for label, src, why in (
                ("dict key", 'ps.peer_update({"host": "TESTHOST", "port": %d, "up": True})\n' % n, "key 'port'"),
                ("camelCase key", 'row = {"busPort": %d}\n' % n, "key 'busPort'"),
                ("digit string under a key", 'env = {"ROMP_POSTAL_PORT": "%d"}\n' % n, "key 'ROMP_POSTAL_PORT'"),
                ("digit separators", 'ps.peer_update({"host": "TESTHOST", "port": %s, "up": True})\n' % _sep(n), "key 'port'"),
                ("keyword", 'row(bus_port=%d)\n' % n, "keyword bus_port="),
                ("env keyword", 'f(ROMP_POSTAL_PORT="%d")\n' % n, "keyword ROMP_POSTAL_PORT="),
                ("assignment", 'km.BUS_PORT = %d\n' % n, "assignment to BUS_PORT"),
                ("env subscript", 'os.environ["ROMP_KERNEL_PORT"] = "%d"\n' % n, "assignment to ROMP_KERNEL_PORT"),
                ("tuple assignment", 'h, port = "x", %d\n' % n, "assignment to port"),
                ("default", 'def notify(host, up, port=%d):\n    pass\n' % n, "default of port"),
                ("own function positional", 'def rec(port, pid=None):\n    pass\n\n\nrec(%d)\n' % n, "argument port of rec()"),
                ("product function positional", 'km._notify_bus_peer("TESTHOST", %d, True)\n' % n, "argument port of _notify_bus_peer()"),
                ("product method positional", 'r.ring(%d)\n' % n, "argument port of ring()"),
                ("loop target", 'for host, port in (("A", %d),):\n    pass\n' % n, "loop target port"),
                ("a call handed a port name and its value", 'os.environ.setdefault("ROMP_POSTAL_PORT", "%d")\n' % n,
                 "handed with the name 'ROMP_POSTAL_PORT'"),
                ("address", 's.connect(("127.0.0.1", %d))\n' % n, "address ('127.0.0.1'"),
                ("address with a host from a name", 'HOST = "127.0.0.1"\ns.connect((HOST, %d))\n' % n, "address ('127.0.0.1'"),
                ("a call's argument after a host", 'conn = http.client.HTTPConnection("127.0.0.1", %d, timeout=30)\n' % n,
                 "argument after the host '127.0.0.1'"),
                ("a call's argument after a host from a name",
                 'HOST = "localhost"\n\n\nasync def f():\n    r, w = await asyncio.open_connection(HOST, %d)\n' % n,
                 "argument after the host 'localhost'"),
                ("formatted address", 'u = "http://127.0.0.1:%%d/peer" %% %d\n' % n, "formatted into an address"),
                ("formatted address, the template from a name", 'URL = "http://127.0.0.1:%%d/peer"\nurlopen(URL %% %d)\n' % n,
                 "formatted into an address"),
                ("formatted address with a placeholder host", 'u = "http://%%s:%%d/x" %% (h, %d)\n' % n, "formatted into an address"),
                ("formatted address with a placeholder host from an attribute, %s for the port",
                 'u = "ws://%%s:%%s/ws" %% (self.host, %d)\n' % n, "formatted into an address"),
                ("formatted address, %i for the port", 'u = "http://localhost:%%i/x" %% %d\n' % n, "formatted into an address"),
                ("a port concatenated onto an address", 'u = "http://127.0.0.1:" + str(%d) + "/peer"\n' % n,
                 "concatenated onto an address"),
                ("a port concatenated onto an address whose host is a name", 'u = "http://" + host + ":" + "%d"\n' % n,
                 "concatenated onto an address"),
                ("a port concatenated onto an f-string's address", 'P = %d\nu = f"ws://{h}:" + str(P)\n' % n,
                 "concatenated onto an address, a constant expression"),
                ("an argv list", 'subprocess.run(["romp", "serve", "--port", "%d"])\n' % n, "argument after the flag --port"),
                ("an argv tuple, the number an int", 'ARGS = ("--bus-port", %d)\n' % n, "argument after the flag --bus-port"),
                ("f-string address", 'P = %d\nurllib.request.urlopen(f"http://127.0.0.1:{P}/peer")\n' % n,
                 "formatted into an address, through the name P"),
                ("f-string address with a formatted host", 'h = "x"\nu = f"ws://{h}:{%d}/ws"\n' % n, "formatted into an address"),
                ("str.format address", 'urllib.request.urlopen("http://127.0.0.1:{}/peer".format(%d))\n' % n,
                 "formatted into an address"),
                ("str.format address by field name", 'u = "http://localhost:{p}/x".format(p=%d)\n' % n,
                 "formatted into an address"),
                ("one hop", 'P = %d\nps.peer_update({"host": "h", "port": P})\n' % n, "through the name P"),
                ("one hop, a name bound twice", 'P = 1\nP = %d\nrow = {"port": P}\n' % n, "key 'port', through the name P"),
                ("one hop, a name bound to a display", 'L = [%d, 1]\nrow = {"ports": L}\n' % n, "key 'ports', through the name L"),
                ("two hops through a display", 'A = %d\nL = [A]\nrow = {"ports": L}\n' % n,
                 "key 'ports', through the name L, a constant expression"),
                ("a tuple assignment's element, a name bound to a digit string", 'P = "%d"\nh, port = "x", P\n' % n,
                 "assignment to port, through the name P"),
                ("a tuple assignment's element, a name bound twice", 'P = 1\nP = %d\nh, port = "x", P\n' % n,
                 "assignment to port, through the name P"),
                ("an argv's element, a name bound to a digit string", 'P = "%d"\nsubprocess.run(["romp", "--port", P])\n' % n,
                 "argument after the flag --port, through the name P"),
                ("an argv's element, a name bound twice", 'P = "1"\nP = "%d"\nsubprocess.run(["romp", "--port", P])\n' % n,
                 "argument after the flag --port, through the name P"),
                ("an address's port, a name bound twice", 'P = 1\nP = %d\ns.connect(("127.0.0.1", P))\n' % n,
                 "address ('127.0.0.1', ...), through the name P"),
                ("an address written as a list", 'ADDR = ["127.0.0.1", %d]\n' % n, "address ('127.0.0.1'"),
                ("an unpacking target read as an address", 'HOST = "127.0.0.1"\nX = %d\nHOST, X = pair()\n' % n,
                 "address ('127.0.0.1', ...), through the name X"),
                ("an augmented assignment", 'port += %d\n' % n, "assignment to port"),
                ("a digit string padded with whitespace", 'env = {"ROMP_POSTAL_PORT": " %d "}\n' % n,
                 "key 'ROMP_POSTAL_PORT'"),
                ("a digit string with a digit separator", 'env = {"ROMP_POSTAL_PORT": "%s"}\n' % _sep(n), "key 'ROMP_POSTAL_PORT'"),
                ("a digit string in other decimal digits", 'env = {"ROMP_POSTAL_PORT": "%s"}\n' % _arabic(n),
                 "key 'ROMP_POSTAL_PORT'"),
                ("str() of an int by position", 'km._notify_bus_peer("TESTHOST", str(%d), True)\n' % n,
                 "argument port of _notify_bus_peer()"),
                ("a digit string in an address assigned to a port-named target", 'LISTEN_PORT = ("127.0.0.1", "%d")\n' % n,
                 "assignment to LISTEN_PORT"),
                ("a host name rebound by a call is still a host", 'HOST = "127.0.0.1"\nHOST = os.environ["H"]\n'
                 's.connect((HOST, %d))\n' % n, "address ('127.0.0.1'"),
                ("a key that is a bare name with a port word", 'BUS_PORT = "x"\nrow = {BUS_PORT: %d}\n' % n, "key 'BUS_PORT'"),
                ("an option whose name holds a port word", 'subprocess.run(["romp", "--port-file", "%d"])\n' % n,
                 "after the flag --port-file"),
                ("a callee resolved by its name on another object", 'import vendorlib\nvendorlib.ring(%d)\n' % n,
                 "argument port of ring()"),
                ("a sum built on a constant expression", 'port = %d * 1 + i\n' % n, "an offset from"),
                ("code text of comments alone, read as text", 'CFG = "# PORT=%d"\n' % n, "text rule env"),
                ("code text", 'subprocess.run([sys.executable, "-c", %r])\n' % ('bus.peer_update({"host": "h", "port": %d, "up": True})' % n),
                 "in code text"),
                ("text rule in a string", 'JS = "await fetch(\\"http://127.0.0.1:%d/x\\")"\n' % n, "text rule authority"),
                ("a string that parses as code, read by a text rule", 'conn = http.client.HTTPConnection("localhost:%d", timeout=30)\n' % n,
                 "in code text, text rule authority"),
                ("a Host header", 'h = {"Host": "localhost:%d"}\n' % n, "in code text, text rule authority"),
                ("a key in a one-line string", 'CFG = "port: %d"\n' % n, "in code text, text rule key"),
                ("a bytes literal", 's.sendall(b"GET / HTTP/1.1\\r\\nHost: 127.0.0.1:%d\\r\\n\\r\\n")\n' % n, "text rule authority")):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why)

    def test_a_helper_another_tests_module_defines(self):
        n = _n()
        self._write(os.path.join("tests", "plant_helpers.py"),
                    "from kernel.k import _notify_bus_peer                # a re-export\n\n\ndef dial(host, port, wait=30):\n    pass\n")
        for label, src, *why in (
                ("from-import", 'from plant_helpers import dial\ndial("TESTHOST", %d)\n' % n),
                ("from-import under another name", 'from plant_helpers import dial as d\nd("TESTHOST", %d)\n' % n, "argument port of d()"),
                ("star import", 'from plant_helpers import *\ndial("TESTHOST", %d)\n' % n),
                ("module import", 'import plant_helpers\nplant_helpers.dial("TESTHOST", %d)\n' % n),
                ("module import under another name", 'import plant_helpers as ph\nph.dial("TESTHOST", %d)\n' % n),
                ("the module from the tests package", 'from tests import plant_helpers\nplant_helpers.dial("TESTHOST", %d)\n' % n),
                ("the module from the tests package, imported dotted under another name",
                 'import tests.plant_helpers as ph\nph.dial("TESTHOST", %d)\n' % n),
                ("the function from the tests package's module", 'from tests.plant_helpers import dial\ndial("TESTHOST", %d)\n' % n),
                ("the import's code text", 'import plant_helpers\nsubprocess.run([sys.executable, "-c", %r])\n'
                 % ('plant_helpers.dial("TESTHOST", %d)' % n)),
                ("a name the module only re-exports, by name in the product", 'import plant_helpers\n'
                 'plant_helpers._notify_bus_peer("TESTHOST", %d, True)\n' % n, "argument port of _notify_bus_peer()")):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why[0] if why else "argument port of dial()")
        self.assertGreen("test_x.py", 'dial("TESTHOST", %d)\n' % n)             # not imported: no index holds dial

    def test_a_computed_port_that_can_reach_the_range(self):
        shape = 'env = dict(ROMP_POSTAL_PORT=str(%d + os.getpid() %% %d))\n'      # written as a template, so this file holds no such code
        hits = self._hits("test_plant.py", shape % (20000, 20000))
        self.assertEqual(len(hits), 1, hits)
        self.assertIn("computed into 20000-39999", hits[0][3])
        self.assertGreen("test_plant.py", shape % (20000, 10000))
        self.assertGreen("test_plant.py", 'env = dict(ROMP_POSTAL_PORT=str(base + i))\n')
        lo, hi = LOW + 7232, LOW + 17232                                           # 40000 and 50000, built at run time
        for label, src, why, first in (
                ("randint", 'port = random.randint(%d, %d)\n' % (lo, hi), "computed into %d-%d" % (lo, hi), lo),
                ("randrange from a base", 'port = %d + random.randrange(1000)\n' % lo, "computed into %d-%d" % (lo, lo + 999), lo),
                ("randrange with a start and a step", 'env = dict(ROMP_POSTAL_PORT=str(random.randrange(%d, %d, 2)))\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("randbelow", 'port = %d + secrets.randbelow(100)\n' % lo, "computed into %d-%d" % (lo, lo + 99), lo),
                ("a randrange from a base below the range, no five-digit number in it", 'port = %d + random.randrange(%d)\n'
                 % (lo - 8000, 9000), "computed into %d-%d" % (lo - 8000, lo + 999), LOW),
                ("a sum built on a constant in the range", 'for i in range(3):\n    port = %d + i\n' % lo, "an offset from %d" % lo, lo),
                ("a sum built on a name bound to one", 'BASE = %d\nsrv.bind(("127.0.0.1", BASE + worker))\n' % lo,
                 "an offset from %d" % lo, lo),
                ("// by a divisor of several values",
                 'port = %d // (2 + os.getpid() %% 2)                # %d opens the file\n' % (2 * _n(), _n()),
                 "computed into %d-%d" % (2 * _n() // 3, _n()), LOW),
                ("% by a divisor of several values", 'port = %d %% (%d + os.getpid() %% 5)\n' % (hi, hi + 10000),
                 "computed into 0-%d" % (hi + 10003), LOW),
                ("an unknown % a divisor of several values",
                 'port = 20000 + os.getpid() %% (20000 + os.getpid() %% 2)                # %d opens the file\n' % _n(),
                 "computed into 20000-40000", LOW)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)
        self.assertGreen("test_plant.py", 'port = random.randint(1, 6)\n')

    def test_the_text_rules(self):
        n = _n()
        for label, name, src, why in (
                ("JS key", "a.test.mjs", "const srv = { host: '127.0.0.1', port: %d };\n" % n, "rule key"),
                ("JSON key", "x.json", '{\n  "busPort": %d\n}\n' % n, "rule key"),
                ("JS declaration", "a.test.ts", "const proxyPort = %d;\n" % n, "rule decl"),
                ("JS digit separators", "b.test.ts", "const proxyPort = %s;\n" % _sep(n), "rule decl"),
                ("shell env", "a.bats", "export ROMP_POSTAL_PORT=%d\n" % n, "rule env"),
                ("shell arithmetic", "h.bats", "export ROMP_POSTAL_PORT=$((%d + RANDOM %% 1000))\n" % n, "rule env"),
                ("shell local", "b.bats", "    local port=%d\n" % n, "rule decl"),
                ("flag", "c.bats", "run romp serve --port %d\n" % n, "rule flag"),
                ("URL", "d.test.mjs", "await fetch('http://localhost:%d/healthz');\n" % n, "rule authority"),
                ("a port concatenated onto a URL", "d2.test.mjs", "await fetch('http://127.0.0.1:' + %d + '/x');\n" % n,
                 "rule authority"),
                ("a flag and its number as list elements", "c2.test.mjs", "spawn(bin, ['serve', '--port', '%d']);\n" % n,
                 "rule flag"),
                ("address in shell python", "e.bats", "python3 -c \"s.bind(('127.0.0.1', %d))\"\n" % n, "rule address"),
                ("listen", "f.test.js", "server.listen(%d, '127.0.0.1');\n" % n, "rule call"),
                ("a name and its value handed together", "g.test.js", "setEnv('ROMP_POSTAL_PORT', '%d');\n" % n, "rule pair"),
                ("a quote that opens a string, then a +, after an address's colon", "o.test.mjs",
                 "const o = { localhost: '+%d' };\n" % n, "rule authority"),
                ("a quote that opens a string after a --*port option, then a space", "p1.bats", 'echo --port" %d"\n' % n,
                 "rule flag"),
                ("a quote that opens a string after a --*port option, then a comma", "p2.bats", 'echo --port", %d"\n' % n,
                 "rule flag"),
                ("a --*port option that ends a longer quoted word, then a space", "p3.bats", 'run romp "serve --port" %d\n' % n,
                 "rule flag"),
                ("a quote that opens a string after a --*port option, in a JavaScript string", "p4.test.mjs",
                 "execSync(\"romp --port' %d'\");\n" % n, "rule flag"),
                ("other decimal digits", "k.bats", "export ROMP_POSTAL_PORT=%s\n" % _arabic(n), "rule env"),
                ("a comment in a file read as text", "m.bats", "# the old default: localhost:%d\n" % n, "rule authority"),
                ("a shell arithmetic expansion after a flag", "n.bats", "run romp --port $((%d + RANDOM %% 100))\n" % n,
                 "rule flag")):
            with self.subTest(label):
                self.assertRed(name, src, why)

    def test_the_excluded_class_stays(self):
        n = _n()
        for label, name, src in (
                ("prose in a comment", "test_x.py", "# the old port %d sat inside the range\nx = 1\n" % n),
                ("docstring", "test_x.py", '"""It dialed port %d once."""\n' % n),
                ("ssh error line", "test_x.py", 'LINES = ("Error: remote port forwarding failed for listen port %d",\n'
                                                '         "channel_setup_fwd_listener_tcpip: cannot listen to port: %d")\n' % (n, n)),
                ("ps line", "test_x.py", 'PS = "  12345 /usr/bin/ssh -N -T -L %d:127.0.0.1:29855 TESTHOST"\n' % n),
                ("a string by position after a host", "test_x.py", 'self.assertEqual(split_line("127.0.0.1", "%d"), 1)\n' % n),
                ("an expected value", "test_x.py", 'self.assertEqual((snap["port"], snap["up"]), (%d, True))\n' % n),
                ("a timeout", "test_x.py", 'page.goto(url, timeout=%d)\n' % n),
                ("a word that only contains port", "test_x.py", 'row = {"report": %d, "transport": %d}\n' % (n, n)),
                ("an argv element after an option that does not name a port", "test_x.py",
                 'subprocess.run(["x", "--report", "%d"])\n' % n),
                ("an id", "test_x.py", 'MID = "1700000001.%d_44444.TESTHOST"\n' % n),
                ("an empty string before a number in a call", "test_x.py", 'row = make_row("id", "", %d)\n' % n),
                ("a digit string as an address's port", "test_x.py", 's.connect(("127.0.0.1", "%d"))\n' % n),
                ("a comment inside code text", "test_x.py", 'subprocess.run([sys.executable, "-c", "x = 1  # was {port: %d}"])\n' % n),
                ("a docstring inside code text", "test_x.py", 'PROBE = "def f():\\n    \\"\\"\\"{port: %d}\\"\\"\\"\\n"\n' % n),
                ("JS timeout", "g.test.ts", "await page.waitForSelector('#x', { timeout: %d });\n" % n),
                ("JS prose", "h.test.ts", "// the bus port: %d was the old default\n" % n),
                ("bats size", "i.bats", '[[ "$output" == *"dom %d"* ]]\n' % n)):
            with self.subTest(label):
                self.assertGreen(name, src)

    def test_a_digit_string_by_position_to_a_port_named_parameter_is_not_counted(self):
        """The excluded class's string by position, where the resolver does find a port-named parameter: each call below
        resolves in the scratch index (kernel/k.py, or the module's own function), as its int form, red, shows, and the
        same call with the number as a digit string is green."""
        n = _n()
        for label, call in (("a product function", 'km._notify_bus_peer("TESTHOST", %s, True)\n'),
                            ("a product method", 'r.ring(%s)\n'),
                            ("the module's own function", 'def rec(port, pid=None):\n    pass\n\n\nrec(%s)\n')):
            with self.subTest(label):
                self.assertRed("test_plant.py", call % n, "argument port of")
                self.assertGreen("test_x.py", call % ('"%d"' % n))

    def test_an_address_ends_where_its_text_ends_and_a_nul_in_the_source_is_no_placeholder(self):
        """THE RULE's address, for the f-string, format and concatenation rules. The text before the operand must end at the
        colon and any spaces or tabs, so a newline after the colon ends the address (the end was matched with $, which
        also matches before a final newline, and each newline form below was read). A NUL the source writes is an
        ordinary character, never the placeholder a field or an unread operand leaves (each NUL form below was read).
        Each green form has a red twin that differs only there, so the green is the rule's and not a file left unread."""
        n = _n()
        for label, green, red, why in (
                ("a newline after the colon, concatenated", 'u = "http://127.0.0.1:\\n" + str(%d)\n' % n,
                 'u = "http://127.0.0.1:" + str(%d)\n' % n, "concatenated onto an address"),
                ("a newline after the colon, in an f-string", 'P = %d\nu = f"http://127.0.0.1:\\n{P}/x"\n' % n,
                 'P = %d\nu = f"http://127.0.0.1:{P}/x"\n' % n, "formatted into an address"),
                ("a newline after the colon, by str.format", 'u = "http://127.0.0.1:\\n{}/x".format(%d)\n' % n,
                 'u = "http://127.0.0.1:{}/x".format(%d)\n' % n, "formatted into an address"),
                ("a NUL for the host, concatenated", 'u = "http://\\x00:" + str(%d)\n' % n,
                 'u = "http://" + h + ":" + str(%d)\n' % n, "concatenated onto an address"),
                ("a NUL for the host, in an f-string", 'P = %d\nu = f"http://\\x00:{P}/x"\n' % n,
                 'P = %d\nu = f"http://{h}:{P}/x"\n' % n, "formatted into an address"),
                ("a NUL for the host, by str.format", 'u = "http://\\x00:{}/x".format(%d)\n' % n,
                 'u = "http://{}:{}/x".format(h, %d)\n' % n, "formatted into an address")):
            with self.subTest(label):
                self.assertGreen("test_x.py", green)
                self.assertRed("test_plant.py", red, why)

    def test_an_option_then_a_quote_and_spaces_before_its_number(self):
        """THE RULE's flag rule, for an option followed by a quote and then spaces or tabs before its number: a shell argv
        that quotes the option, and a JavaScript string that holds such a command. Each green twin is a near miss in a
        file the census opens (its number stands alone in the range), so the green is the rule's: a quoted option with no
        port word, one with one dash, a word between the option and the quote, and a quoted option that ends its line
        with the number alone at the start of the next, in shell (where the number is then the next command) and in a
        JavaScript template literal: a newline is not a space or a tab. That the quote need not close a string, nor one
        opened at the option, is pinned in test_the_text_rules."""
        n = _n()
        for label, name, src in (
                ("a quoted option, then a space", "q1.bats", 'run romp serve "--port" %d\n' % n),
                ("a quoted option and a quoted number, then a tab", "q2.bats", "run romp serve '--bus-port'\t\"%d\"\n" % n),
                ("a JavaScript string holding the command", "q3.test.mjs", "execSync('romp serve \"--port\" %d');\n" % n)):
            with self.subTest(label):
                self.assertRed(name, src, "rule flag")
        for label, name, src in (
                ("a quoted option with no port word", "q4.bats", 'run romp serve "--report" %d\n' % n),
                ("a quoted option with one dash", "q5.bats", 'run romp serve "-p" %d\n' % n),
                ("a word between the option and the quote", "q6.bats", 'echo "--port is" %d\n' % n),
                ("a quoted option that ends its line, the number alone on the next", "q7.bats",
                 'run romp serve "--port"\n%d\n' % n),
                ("a quoted option that ends a JavaScript template literal's line, the number alone on the next",
                 "q8.test.mjs", "const cmd = `romp serve '--port'\n%d`;\n" % n)):
            with self.subTest(label):
                self.assertGreen(name, src)

    def test_a_dotted_option(self):
        """THE RULE's --*port option, for a name in parts a dot joins (--server.port, the spelling some servers give their
        settings), in Python's argv rule and in the text flag rule. Each green twin is a near miss in a file the census
        opens: a dotted name with no port word, and a dot that ends the option (prose), which is no part of its name."""
        n = _n()
        for label, name, src, why in (
                ("a dotted option, then a space", "d1.bats", "run java -jar srv.jar --server.port %d\n" % n, "rule flag"),
                ("a dotted option and =", "d2.bats", "run java -jar srv.jar --server.port=%d\n" % n, "rule flag"),
                ("a dotted option quoted, then a space", "d3.bats", 'run java -jar srv.jar "--server.port" %d\n' % n,
                 "rule flag"),
                ("a dotted option in a JavaScript argv", "d4.test.mjs",
                 "spawn('java', ['-jar', 'srv.jar', '--server.port', '%d']);\n" % n, "rule flag"),
                ("a dotted option in a Python argv", "test_plant.py",
                 'subprocess.run(["java", "-jar", "srv.jar", "--server.port", "%d"])\n' % n, "after the flag --server.port")):
            with self.subTest(label):
                self.assertRed(name, src, why)
        for label, name, src in (
                ("a dotted option with no port word, in shell", "d5.bats", "run java -jar srv.jar --server.report %d\n" % n),
                ("a dotted option with no port word, in Python", "test_x.py",
                 'subprocess.run(["java", "-jar", "srv.jar", "--server.report", "%d"])\n' % n),
                ("a dot that ends the option", "d6.bats", "# pass --port. %d was the old default\n" % n)):
            with self.subTest(label):
                self.assertGreen(name, src)

    def test_a_javascript_concatenation_or_list_split_across_lines(self):
        """THE RULE's authority and flag rules, for a concatenation onto an address and a list's --*port element split
        across lines, the + or the comma ending one line or starting the next. Each green twin is a near miss in a file
        the census opens: a template literal whose colon ends its line, so the address has ended before the +, and a
        comment holding the number on the line after the + or the comma, prose and not the operand."""
        n = _n()
        for label, name, src, why in (
                ("a + that ends the line", "s1.test.mjs", "await fetch('http://127.0.0.1:' +\n    %d + '/x');\n" % n,
                 "rule authority"),
                ("a + that starts the next line", "s2.test.mjs", "await fetch('http://127.0.0.1:'\n    + '%d' + '/x');\n" % n,
                 "rule authority"),
                ("a comma that ends the line", "s3.test.mjs", "spawn(bin, ['serve', '--port',\n    '%d']);\n" % n, "rule flag"),
                ("a comma that starts the next line", "s4.test.mjs",
                 "spawn(bin, [\n  'serve',\n  '--port'\n  , '%d',\n]);\n" % n, "rule flag")):
            with self.subTest(label):
                self.assertRed(name, src, why)
        for label, name, src in (
                ("a template literal whose colon ends its line", "s5.test.mjs", "await fetch(`http://127.0.0.1:\n` + %d);\n" % n),
                ("a comment after the +", "s6.test.mjs",
                 "await fetch('http://127.0.0.1:' +\n    // %d was the old port\n    port);\n" % n),
                ("a comment after the comma", "s7.test.mjs",
                 "spawn(bin, ['serve', '--port',\n    // %d was the old port\n    String(port)]);\n" % n)):
            with self.subTest(label):
                self.assertGreen(name, src)

    def test_a_format_field_nested_in_a_spec_takes_its_own_operand(self):
        """THE RULE's str.format reading, for a field nested in another field's format spec ("{:{}}", a width or a fill
        given as an operand): a field takes its automatic number before the fields nested in its spec take theirs, so the
        port's field after them takes the operand str.format gives it, and a nested field's operand is not read. A field
        nested by name takes no number. Each green twin is in a file the census opens: the number in the range is a
        nested field's operand (a width), and the port is 1."""
        n = _n()
        for label, src in (
                ("a host's field with a nested field", 'u = "http://{:{}}:{}/x".format(h, w, %d)\n' % n),
                ("a host's field with a fill and a nested width", 'u = "http://{:>{}}:{}/x".format(h, 9, %d)\n' % n),
                ("a host's field with two nested fields", 'u = "http://{:{}{}}:{}/x".format(h, ">", w, %d)\n' % n),
                ("a field nested by name takes no number", 'u = "http://{:{w}}:{}/x".format(h, %d, w=9)\n' % n)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, "formatted into an address")
        for label, src in (
                ("the nested width of the host's field", 'u = "http://{:{}}:{}/x".format(h, %d, 1)\n' % n),
                ("the nested width of the port's own field", 'u = "http://127.0.0.1:{:{}}/x".format(1, %d)\n' % n)):
            with self.subTest(label):
                self.assertGreen("test_x.py", src)

    def test_a_format_template_str_format_refuses_for_its_text_is_not_read(self):
        """THE RULE's str.format reading, for a template str.format refuses whatever its operands: a field nested two deep
        (an opening brace in the spec of a field nested in a spec), and automatic and numbered fields mixed, in either
        order or inside a spec. Each green form puts the number in the range at every operand the port's field could be
        numbered to, so it is green because the template is refused, and its red twin differs only there: nested one
        deep, or numbered one way throughout. The red plants pin what THE RULE says goes unchecked: a template str.format
        refuses for another reason (a field with no operand, an unknown conversion) still has its port's operand read."""
        n = _n()
        for label, green, red in (
                ("a field nested two deep", 'u = "http://{:{:{}}}:{}/x".format(h, %d, %d, %d)\n' % (n, n, n),
                 'u = "http://{:{:}}:{}/x".format(h, %d, %d, %d)\n' % (n, n, n)),
                ("an automatic field, then a numbered one", 'u = "http://{}:{1}/x".format(h, %d)\n' % n,
                 'u = "http://{}:{}/x".format(h, %d)\n' % n),
                ("a numbered field, then an automatic one", 'u = "http://{1}:{}/x".format(%d, h)\n' % n,
                 'u = "http://{1}:{0}/x".format(%d, h)\n' % n),
                ("a numbered field nested in an automatic field's spec", 'u = "http://{:{1}}:{}/x".format(h, %d, %d)\n' % (n, n),
                 'u = "http://{0:{1}}:{2}/x".format(h, %d, %d)\n' % (n, n))):
            with self.subTest(label):
                self.assertGreen("test_x.py", green)
                self.assertRed("test_plant.py", red, "formatted into an address")
        for label, src in (
                ("another field with no operand", 'u = "http://{}:{}/{}".format(h, %d)\n' % n),
                ("another field with an unknown conversion", 'u = "http://{}:{}/{!x}".format(h, %d, p)\n' % n)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, "formatted into an address")

    def test_a_format_field_is_numbered_by_decimal_digits_alone(self):
        """THE RULE's str.format reading, for a field name of digits other than ASCII's: a field is numbered when its
        name is decimal digits alone (str.isdecimal()), as str.format reads it. An Arabic-Indic digit numbers a field.
        A superscript two, a digit to str.isdigit() but not decimal, is a name: a numbered field beside it is read by
        its number and an automatic one by the next automatic number, and the field itself takes the keyword argument
        of its name, which no call writes as a keyword, so a port in it is not read (the green form, whose red twins
        above show the template read). The census tested str.isdigit() here and then called int() on the name, which
        raised ValueError for a superscript digit, and counted such a name as a numbered field, so beside an automatic
        field the template was refused."""
        n, sup2, ar1 = _n(), "\u00b2", "\u0661"                         # a superscript two; an Arabic-Indic one
        for label, src in (
                ("a numbered field after a superscript-digit name", 'u = "http://{%s}:{0}/x".format(%d)\n' % (sup2, n)),
                ("an automatic field after a superscript-digit name", 'u = "http://{%s}:{}/x".format(%d)\n' % (sup2, n)),
                ("a field numbered by an Arabic-Indic digit", 'u = "http://127.0.0.1:{%s}/x".format(1, %d)\n' % (ar1, n))):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, "formatted into an address")
        with self.subTest("the port's field named by a superscript digit"):
            self.assertGreen("test_x.py", 'u = "http://127.0.0.1:{%s}/x".format(%d)\n' % (sup2, n))

    def test_a_random_call_with_keyword_arguments(self):
        """THE RULE's random calls, with arguments given by their parameters' names (randint(a=..., b=...)), read as their
        positional forms are. Each green twin is in a file the census opens: a call whose first parameter is left empty
        (randint and randrange), one whose keyword names no parameter of the call, and keyword bounds below the range
        (that file opened by the randint( form alone)."""
        lo, hi = LOW + 7232, LOW + 17232                                           # 40000 and 50000, built at run time
        for label, src, why, first in (
                ("randint by keyword", 'port = random.randint(a=%d, b=%d)\n' % (lo, hi), "computed into %d-%d" % (lo, hi), lo),
                ("randint by keyword, in the other order", 'port = random.randint(b=%d, a=%d)\n' % (hi, lo),
                 "computed into %d-%d" % (lo, hi), lo),
                ("randint by position, then by keyword", 'port = random.randint(%d, b=%d)\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi), lo),
                ("randrange by keyword", 'env = dict(ROMP_POSTAL_PORT=str(random.randrange(start=%d, stop=%d)))\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("randrange's stop by keyword, after a start below the range", 'port = random.randrange(1024, stop=%d)\n' % hi,
                 "computed into 1024-%d" % (hi - 1), LOW),
                ("randbelow by keyword", 'port = secrets.randbelow(exclusive_upper_bound=%d)\n' % hi,
                 "computed into 0-%d" % (hi - 1), LOW)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)
        for label, src in (
                ("randint with its first parameter left empty", 'port = random.randint(b=%d)\n' % hi),
                ("randrange with its first parameter left empty", 'port = random.randrange(stop=%d)\n' % hi),
                ("randint with a keyword that names no parameter of it", 'port = random.randint(%d, high=%d)\n' % (lo, hi)),
                ("randint by keyword below the range", 'port = random.randint(a=1024, b=2048)\n')):
            with self.subTest(label):
                self.assertGreen("test_x.py", src)

    def test_a_random_call_python_refuses_for_its_arguments_is_not_read(self):
        """A random call Python refuses for the way its arguments are passed is not read. Each green plant is in a file
        the census opens and is a call the old reading counted: a randrange whose stop is left empty and whose step is
        given, by keyword or after a positional start (Python: Missing a non-None stop argument, unless the step is 1
        at run time, as step=k can be; WHAT IT CANNOT SEE lists that), and a keyword that repeats a positional argument
        (Python: got multiple values for argument), in each of the three calls. Python
        accepts a stop left empty beside a step of 1, its default (and refuses True there), so randrange(start=S,
        step=1) reads as randrange(S), red. A stop written as None, randrange's default, is a stop left empty: the red
        plants randrange(S, None), randrange(start=S, stop=None) and randrange(S, None, 1) read as randrange(S), from
        0 to S less one, which e50adc775 did not read; randrange(S, None, 7) stays a stop left empty beside a step, and
        randrange(40000, None, stop=50000) a keyword that repeats the stop, both refused and green."""
        lo, hi = LOW + 7232, LOW + 17232                                           # 40000 and 50000, built at run time
        for label, src in (
                ("randrange with its stop None and a step of 7", 'port = random.randrange(%d, None, 7)\n' % hi),
                ("randrange with its stop None and a keyword that repeats it",
                 'port = random.randrange(%d, None, stop=%d)\n' % (lo, hi)),
                ("randrange with its stop left empty and its step given", 'port = random.randrange(start=%d, step=7)\n' % hi),
                ("randrange with its start by position, its stop left empty and its step given",
                 'port = random.randrange(%d, step=k)\n' % hi),
                ("randrange with its stop left empty and a step of True, a bool Python refuses there",
                 'port = random.randrange(%d, step=True)\n' % hi),
                ("randrange with a keyword that repeats its stop", 'port = random.randrange(%d, %d, stop=3)\n' % (lo, hi)),
                ("randint with a keyword that repeats its a", 'port = random.randint(%d, %d, a=1)\n' % (lo, hi)),
                ("randbelow with a keyword that repeats its bound",
                 'port = secrets.randbelow(%d, exclusive_upper_bound=3)\n' % hi)):
            with self.subTest(label):
                self.assertGreen("test_x.py", src)
        for label, src in (
                ("randrange with its stop left empty and a step of 1", 'port = random.randrange(start=%d, step=1)\n' % hi),
                ("randrange with its stop None", 'port = random.randrange(%d, None)\n' % hi),
                ("randrange with its stop None, by keyword", 'port = random.randrange(start=%d, stop=None)\n' % hi),
                ("randrange with its stop None and a step of 1", 'port = random.randrange(%d, None, 1)\n' % hi)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, "computed into 0-%d" % (hi - 1), n=LOW)

    def test_a_randrange_whose_step_is_unbounded(self):
        """randrange(start, stop, step) with a step interval() does not bound (a name, k), given by position or by its
        name, the stop by either too: read as the span holding both the values a positive step returns (start to stop
        less one) and those a negative step returns (stop plus one up to start), from the lower of start's lowest value
        and stop's lowest plus one to the higher of start's highest and stop's highest less one. Each red plant asserts
        the span the census reports. Where start's interval lies wholly below stop's that span is start to stop less
        one: 40000-49999 for the first three, and 40000-41998 for a computed start and stop, start's interval ending
        one below stop's. The other four share a value with stop, and 1e04b89f8 read none of them: start 40000 to
        42999 with stop 41000 to 41999 (a negative step returns up to 42999), 40000-42999; with stop 40500 to 41499,
        40000-41498; with stop 40999 to 41998, where start's highest value is stop's lowest, 40000-41997; and start
        40010 to 40020 inside stop 40000 to 40040, 40001-40039."""
        lo, hi = LOW + 7232, LOW + 17232                                           # 40000 and 50000, built at run time
        shape = 'port = random.randrange(%d + os.getpid() %% %d, %d + os.getpid() %% %d, %s)\n'
        for label, src, span, first in (
                ("the step by position", 'port = random.randrange(%d, %d, k)\n' % (lo, hi), (lo, hi - 1), lo),
                ("the step by keyword", 'port = random.randrange(%d, %d, step=k)\n' % (lo, hi), (lo, hi - 1), lo),
                ("the stop and the step by keyword", 'port = random.randrange(%d, stop=%d, step=k)\n' % (lo, hi),
                 (lo, hi - 1), lo),
                ("start and stop computed, start's interval wholly below stop's",
                 shape % (lo, 1000, lo + 1000, 1000, "step=k"), (lo, lo + 1998), lo),
                ("start's interval running past stop's highest", shape % (lo, 3000, lo + 1000, 1000, "k"),
                 (lo, lo + 2999), lo),
                ("start's interval and stop's overlap, start's highest value below stop's highest",
                 shape % (lo, 1000, lo + 500, 1000, "k"), (lo, lo + 1498), lo),
                ("start's highest value is stop's lowest", shape % (lo, 1000, lo + 999, 1000, "k"), (lo, lo + 1997), lo),
                ("start's interval inside stop's", shape % (lo + 10, 11, lo, 41, "k"), (lo + 1, lo + 39), lo + 1)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, "computed into %d-%d" % span, n=first)

    def test_a_randrange_whose_start_lies_wholly_above_its_stop(self):
        """randrange(start, stop, step) whose start's interval lies wholly above stop's, or touches it from above
        (start's lowest value stop's highest): only a negative step can return a value, from stop plus one up to
        start. A negative step is read as stop plus one to start (stop's lowest value plus one to start's highest), and
        so is an unbounded one, since the span holding both comes to that span here (CPython's own randrange(50000,
        40000, -7) returns 40004 to 50000). Each red plant asserts the span the census reports: a bounded negative
        step, an unbounded step by position, by keyword and with the stop by keyword too, a computed start and stop,
        start's lowest value one above stop's highest, a bounded negative step from a start in the range to a stop
        below it, and start 40000 to 40999 with stop 39000 to 40000, where start's lowest value is stop's highest,
        39001-40999, which 1e04b89f8 did not read."""
        lo, hi = LOW + 7232, LOW + 17232                                           # 40000 and 50000, built at run time
        for label, src, span, first in (
                ("a bounded negative step", 'port = random.randrange(%d, %d, 0 - 7)\n' % (hi, lo), (lo + 1, hi), lo + 1),
                ("an unbounded step by position", 'port = random.randrange(%d, %d, k)\n' % (hi, lo), (lo + 1, hi), lo + 1),
                ("an unbounded step by keyword", 'port = random.randrange(%d, %d, step=k)\n' % (hi, lo), (lo + 1, hi),
                 lo + 1),
                ("the stop and an unbounded step by keyword", 'port = random.randrange(%d, stop=%d, step=k)\n' % (hi, lo),
                 (lo + 1, hi), lo + 1),
                ("start and stop computed, start's lowest value one above stop's highest",
                 'port = random.randrange(%d + os.getpid() %% 1000, %d + os.getpid() %% 1000, step=k)\n' % (lo + 1000, lo),
                 (lo + 1, lo + 1999), lo + 1),
                ("a bounded negative step from the range to below it", 'port = random.randrange(%d, 20000, 0 - 7)\n' % lo,
                 (20001, lo), LOW),
                ("start's lowest value is stop's highest",
                 'port = random.randrange(%d + os.getpid() %% 1000, %d + os.getpid() %% 1001, k)\n' % (lo, lo - 1000),
                 (lo - 999, lo + 999), lo - 999)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, "computed into %d-%d" % span, n=first)

    def test_a_randrange_python_refuses_for_every_value_is_over_read(self):
        """THE RULE's over-reads: a randrange(start, stop, step) that Python refuses for every value its start, stop and
        step can take is still read by the rule, and each plant asserts the span the census reports. A step of 0 is
        read with the steps that are never negative: randrange(40000, 50000, 0) is 40000-49999, and a step of 0 from a
        start of 40000 to 40999 to a stop of 40500 to 41499 is 40000-41498. A positive step from a start never below
        its stop, or a negative one from a start never above it, is read as a span with its ends reversed, which counts
        because both its ends lie in the range: randrange(40000, 50000, -1) is 50001-40000 (interval() bounds the
        unary minus), randrange(50000, 40000, 7) is 50000-39999, a step of 7 from a start of 40000 to 40099 to a stop
        of 40000 is 40000-39999, and with start and stop both 40000 a step of 7 is 40000-39999 and a step of -7
        40001-40000. With a step that can take either sign or an unbounded one, start and stop both 40000 read as
        40000-40000. Python raises for every plant."""
        lo, hi = LOW + 7232, LOW + 17232                                           # 40000 and 50000, built at run time
        for label, src, span, first in (
                ("start below stop and a step of 0", 'port = random.randrange(%d, %d, 0)\n' % (lo, hi), (lo, hi - 1), lo),
                ("start and stop sharing a value and a step of 0",
                 'port = random.randrange(%d + os.getpid() %% 1000, %d + os.getpid() %% 1000, 0)\n' % (lo, lo + 500),
                 (lo, lo + 1498), lo),
                ("start below stop and a step of -1", 'port = random.randrange(%d, %d, -1)\n' % (lo, hi), (hi + 1, lo),
                 hi + 1),
                ("start above stop and a step of 7", 'port = random.randrange(%d, %d, 7)\n' % (hi, lo), (hi, lo - 1), hi),
                ("start never below stop and a step of 7", 'port = random.randrange(%d + os.getpid() %% 100, %d, 7)\n'
                 % (lo, lo), (lo, lo - 1), lo),
                ("start equal to stop and a step of 7", 'port = random.randrange(%d, %d, 7)\n' % (lo, lo), (lo, lo - 1),
                 lo),
                ("start equal to stop and a step of -7", 'port = random.randrange(%d, %d, -7)\n' % (lo, lo),
                 (lo + 1, lo), lo + 1),
                ("start equal to stop and an unbounded step", 'port = random.randrange(%d, %d, k)\n' % (lo, lo), (lo, lo),
                 lo),
                ("start equal to stop and a step of either sign",
                 'port = random.randrange(%d, %d, os.getpid() %% 3 - 1)\n' % (lo, lo), (lo, lo), lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, "computed into %d-%d" % span, n=first)

    def test_a_randrange_whose_start_and_stop_share_a_value_is_read_by_its_steps_sign(self):
        """randrange(start, stop, step) whose start's interval and stop's share a value: a positive step returns values
        from start to stop less one and a negative step values from stop plus one up to start, so a step that is never
        negative is read as the first span, any other step that is never positive as the second, and any other step,
        one that can take either sign (os.getpid() % 3 - 1, from -1 to 1) or one interval() does not bound, as the span
        holding both. Each red plant asserts the span the census reports. 1e04b89f8 read every such call with a
        bounded step as start to stop less one, which with a negative step was wrong: it reported 40000-40039 for the
        first plant, from which CPython returns values from 40021 to 40060; it did not count the plants across 32768
        or the ones whose stop is 32760, from which CPython returns values up to 32800; and it reported the backward
        span 40000-39999 where start's lowest value is stop's highest. A step from -5 to 0 and one from 0 to 5 are
        read by the sign they can take, since a step of 0 raises. The green twins: a positive step across 32768, whose
        values stay from 32750 to 32759, and a negative step from a start of 32700 to 32760 to a stop of 32750 to
        32800, whose values stay from 32751 to 32760, where start to stop less one would reach 32799."""
        lo = LOW + 7232                                                            # 40000, built at run time
        s, e = LOW - 18, LOW - 68                                                  # 32750 and 32700, built at run time
        across = 'port = random.randrange(%d + os.getpid() %% 51, %s%d + os.getpid() %% 61, %s)\n'
        inside = 'port = random.randrange(%d + os.getpid() %% 61, %d + os.getpid() %% 21, %s)\n'
        for label, src, span, first in (
                ("a negative step, start running past stop on both sides", inside % (lo, lo + 20, "0 - 7"),
                 (lo + 21, lo + 60), lo + 21),
                ("a negative step by keyword, start running past stop on both sides",
                 inside % (lo, lo + 20, "step=0 - 7"), (lo + 21, lo + 60), lo + 21),
                ("a negative step, start and stop across 32768", across % (s, "", e, "0 - 7"), (e + 1, s + 50), LOW),
                ("a negative step, start and stop across 32768, the stop and the step by keyword",
                 across % (s, "stop=", e, "step=0 - 7"), (e + 1, s + 50), LOW),
                ("a negative step, start's lowest value a constant stop",
                 'port = random.randrange(%d + os.getpid() %% 41, %d, 0 - 7)\n' % (s + 10, s + 10), (s + 11, s + 50), LOW),
                ("a negative step, start's lowest value a constant stop, the stop and the step by keyword",
                 'port = random.randrange(%d + os.getpid() %% 41, stop=%d, step=0 - 7)\n' % (s + 10, s + 10),
                 (s + 11, s + 50), LOW),
                ("a negative step, start's lowest value stop's highest, in the range",
                 'port = random.randrange(%d + os.getpid() %% 31, %d + os.getpid() %% 31, 0 - 7)\n' % (lo, lo - 30),
                 (lo - 29, lo + 30), lo - 29),
                ("a step that can be negative or positive, start and stop across 32768",
                 across % (s, "", e, "os.getpid() % 3 - 1"), (e + 1, s + 50), LOW),
                ("a step that can be negative or positive, by keyword", inside % (lo, lo + 20, "step=os.getpid() % 3 - 1"),
                 (lo, lo + 60), lo),
                ("an unbounded step", inside % (lo, lo + 20, "k"), (lo, lo + 60), lo),
                ("a step from -5 to 0, never positive", inside % (lo, lo + 20, "os.getpid() % 6 - 5"), (lo + 21, lo + 60),
                 lo + 21),
                ("a step from 0 to 5, never negative", inside % (lo, lo + 20, "os.getpid() % 6"), (lo, lo + 39), lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, "computed into %d-%d" % span, n=first)
        with self.subTest("a positive step, start and stop across 32768"):
            self.assertGreen("test_x.py", across % (s, "", e, "7"))
        with self.subTest("a negative step, start's interval sharing a value with stop's from below"):
            self.assertGreen("test_x.py", 'port = random.randrange(%d + os.getpid() %% 61, %d + os.getpid() %% 51, 0 - 7)\n'
                             % (e, s))

    def test_a_unary_minus_over_a_bounded_operand_is_bounded(self):
        """interval() bounds a unary minus over a bounded operand as the operand's interval negated, its ends swapped,
        so -7 is a negative step and -(os.getpid() % 3 - 1) one that can take either sign. Each red plant asserts the
        span the census reports, start 40000 to 40060 and stop 40020 to 40040: a negative step reads 40021-40060, a
        positive one 40000-40039, and one of either sign 40000-40060, as does a unary minus over an unbounded step,
        which stays unbounded. Outside a step, 50000 - -7 is a constant expression, 50007. The green twin is a
        negative constant, -40000, which no port is."""
        lo, hi = LOW + 7232, LOW + 17232                                           # 40000 and 50000, built at run time
        inside = 'port = random.randrange(%d + os.getpid() %% 61, %d + os.getpid() %% 21, %s)\n'
        for label, src, why, first in (
                ("a step of -7", inside % (lo, lo + 20, "-7"), "computed into %d-%d" % (lo + 21, lo + 60), lo + 21),
                ("a step of -7 by keyword", inside % (lo, lo + 20, "step=-7"), "computed into %d-%d" % (lo + 21, lo + 60),
                 lo + 21),
                ("a unary minus over a step from 1 to 5", inside % (lo, lo + 20, "-(1 + os.getpid() % 5)"),
                 "computed into %d-%d" % (lo + 21, lo + 60), lo + 21),
                ("a unary minus over a step from -1 to 1", inside % (lo, lo + 20, "-(os.getpid() % 3 - 1)"),
                 "computed into %d-%d" % (lo, lo + 60), lo),
                ("a unary minus over a negative step", inside % (lo, lo + 20, "-(0 - 7)"),
                 "computed into %d-%d" % (lo, lo + 39), lo),
                ("a unary minus over an unbounded step", inside % (lo, lo + 20, "-k"), "computed into %d-%d" % (lo, lo + 60),
                 lo),
                ("a constant less a negative constant", 'port = %d - -7\n' % hi, "a constant expression", hi + 7)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)
        with self.subTest("a negative constant"):
            self.assertGreen("test_x.py", 'port = -%d\n' % lo)

    def test_a_unary_plus_reads_as_its_operand(self):
        """interval() and offset_base() read a unary plus as its operand, so +45001 is a constant expression, 45001, a
        random call's argument may carry one, and +(40000 + i) is an offset from 40000. Each red plant asserts what the
        census reports: randrange(+40000, 50000) and randrange(40000, +50000) are 40000-49999, randint(+40000, 50000) is
        40000-50000, randrange(+50000, 40000, +k) is 40001-50000, and a step of +(-7), with start 40000 to 40060 and stop
        40020 to 40040, is a negative step, 40021-40060. e50adc775 read none of these but the step, which it took for
        an unbounded one, 40000-40060."""
        lo, hi, n = LOW + 7232, LOW + 17232, _n()                                  # 40000, 50000 and 45001, built at run time
        inside = 'port = random.randrange(%d + os.getpid() %% 61, %d + os.getpid() %% 21, +(-7))\n' % (lo, lo + 20)
        for label, src, why, first in (
                ("a port written with a plus", 'port = +%d\n' % n, "a constant expression", n),
                ("a randrange whose start has a plus", 'port = random.randrange(+%d, %d)\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a randrange whose stop has a plus", 'port = random.randrange(%d, +%d)\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a randint whose first argument has a plus", 'port = random.randint(+%d, %d)\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi), lo),
                ("a plus over the start and over an unbounded step", 'port = random.randrange(+%d, %d, +k)\n' % (hi, lo),
                 "computed into %d-%d" % (lo + 1, hi), lo + 1),
                ("a step of +(-7)", inside, "computed into %d-%d" % (lo + 21, lo + 60), lo + 21),
                ("a sum under a plus", 'port = +(%d + i)\n' % lo, "an offset from %d" % lo, lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)

    def test_a_name_bound_to_a_signed_number_holds_that_number(self):
        """BOUND records a number written with a sign, a unary minus or plus over an int or float constant, as the
        number Python computes. So a name bound to 7 and to -7 holds two values and reads as a step interval() does not
        bound, by the span holding both, and a name bound to -40000 alone reads as -40000. Each red plant asserts what
        the census reports. e50adc775 recorded no such binding, so it read a name bound to 7 and to -7 as 7 alone, a
        positive step: it reported nothing for randrange(40000, 30000, step) in a loop over (1, -1), from which CPython
        returns values from 30001 to 40000, nor for randrange(40000, 1000, K) with K bound to 7 and to -7, or to -7.0,
        which 3.10 and 3.11 take as a step. It read a name bound to -7 alone as unbounded, 40000-40060 where the step
        is negative and CPython returns 40021 to 40060, and left unread the calls whose name holds a negative number
        alone: randint(1, -S) with S bound to -40000 returns values up to 40000, and randrange(41000 + OFFSET, 42000)
        with OFFSET bound to -1000 values from 40000. A name bound to -7 and to +7 holds both (recording the minus
        alone would read it as -7, a negative step, and miss randrange(1000, 40000, K)'s values), and a name bound to
        +45001 holds 45001, read through the hop. A name also bound by a binding the census does not record reads as
        unbounded at a step, and elsewhere by the ints the census records for it
        (test_a_name_with_a_binding_the_census_does_not_record_is_unbounded_at_a_step)."""
        lo, n = LOW + 7232, _n()                                                   # 40000 and 45001, built at run time
        s = LOW - 2768                                                             # 30000, built at run time
        inside = 'port = random.randrange(%d + os.getpid() %% 61, %d + os.getpid() %% 21, K)\n' % (lo, lo + 20)
        for label, src, why, first in (
                ("a loop over a positive and a negative step",
                 'for step in (1, -1):\n    port = random.randrange(%d, %d, step)\n' % (lo, s),
                 "computed into %d-%d" % (s + 1, lo), LOW),
                ("a name bound to 7 and to -7", 'K = 7\nK = -7\nport = random.randrange(%d, 1000, K)\n' % lo,
                 "computed into 1001-%d" % lo, LOW),
                ("a name bound to 7 and to -7.0", 'K = 7\nK = -7.0\nport = random.randrange(%d, 1000, K)\n' % lo,
                 "computed into 1001-%d" % lo, LOW),
                ("a name bound to -7 and to +7", 'K = -7\nK = +7\nport = random.randrange(1000, %d, K)\n' % lo,
                 "computed into 1000-%d" % (lo - 1), LOW),
                ("a name bound to -7 alone, a negative step", 'K = -7\n' + inside,
                 "computed into %d-%d" % (lo + 21, lo + 60), lo + 21),
                ("a name bound to a negative number, negated", 'S = -%d\nport = random.randint(1, -S)\n' % lo,
                 "computed into 1-%d" % lo, LOW),
                ("a name bound to a negative number, added",
                 'OFFSET = -1000\nport = random.randrange(%d + OFFSET, %d)\n' % (lo + 1000, lo + 2000),
                 "computed into %d-%d" % (lo, lo + 1999), lo),
                ("a name bound to a number written with a plus, through the hop", 'P = +%d\nrow = {"port": P}\n' % n,
                 "key 'port', through the name P", n)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)

    def test_a_bool_reads_as_its_int(self):
        """interval() reads a bool as the int it is, True as 1 and False as 0, as randrange and randint take it. Each red
        plant asserts what the census reports: randrange(True, 50000) is 1-49999, by keyword too and through a name
        bound to True; randint(False, 40000) is 0-40000; and 32767 + True is a constant expression, 32768. e50adc775
        read none of them. A float stays unread (WHAT IT CANNOT SEE)."""
        lo, hi, n = LOW + 7232, LOW + 17232, _n()                                  # 40000, 50000 and 45001, built at run time
        for label, src, why, first in (
                ("a randrange from True", 'port = random.randrange(True, %d)\n' % hi, "computed into 1-%d" % (hi - 1), LOW),
                ("a randrange from True by keyword", 'port = random.randrange(start=True, stop=%d)\n' % hi,
                 "computed into 1-%d" % (hi - 1), LOW),
                ("a randrange from a name bound to True", 'B = True\nport = random.randrange(B, %d)\n' % hi,
                 "computed into 1-%d" % (hi - 1), LOW),
                ("a randint from False", 'port = random.randint(False, %d)\n' % lo, "computed into 0-%d" % lo, LOW),
                ("a sum with True", 'port = %d + True                # %d opens the file\n' % (LOW - 1, n),
                 "a constant expression", LOW)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)

    def test_a_random_call_spelled_on_the_class_takes_its_instance_first(self):
        """A random call spelled on a name or attribute called Random or SystemRandom, an unbound method, passes its
        instance first, and the census drops it before reading the arguments: the class is known by that name alone, so
        mymod.Random counts as random.Random does. Each red plant asserts the span the census reports: randrange(rng,
        40000, 50000) is 40000-49999, on mymod.Random too, by keyword after the instance, and with a step of 7, four
        arguments in all; randrange(rng, 50000) is 0-49999; randint(rng, 40000, 50000) is 40000-50000, by keyword
        too. e50adc775 put the instance in start's place, so it read none of these (a keyword after the instance
        repeated the start, four arguments outnumbered randrange's three); with rng bound to 0 elsewhere in the module
        it read randrange(rng, 1000, 50000) as 0-999 and reported nothing, where CPython returns 1000-49999."""
        lo, hi = LOW + 7232, LOW + 17232                                           # 40000 and 50000, built at run time
        for label, src, span, first in (
                ("randrange on random.Random", 'port = random.Random.randrange(rng, %d, %d)\n' % (lo, hi), (lo, hi - 1), lo),
                ("randrange on an attribute of another module called Random",
                 'port = mymod.Random.randrange(rng, %d, %d)\n' % (lo, hi), (lo, hi - 1), lo),
                ("randrange on random.Random with its start alone", 'port = random.Random.randrange(rng, %d)\n' % hi,
                 (0, hi - 1), LOW),
                ("randint on random.Random", 'port = random.Random.randint(rng, %d, %d)\n' % (lo, hi), (lo, hi), lo),
                ("randint on random.Random by keyword", 'port = random.Random.randint(rng, a=%d, b=%d)\n' % (lo, hi),
                 (lo, hi), lo),
                ("randrange on random.SystemRandom by keyword",
                 'port = random.SystemRandom.randrange(rng, start=%d, stop=%d)\n' % (lo, hi), (lo, hi - 1), lo),
                ("randrange on Random imported by name, the stop by keyword",
                 'from random import Random\nport = Random.randrange(rng, %d, stop=%d)\n' % (lo, hi), (lo, hi - 1), lo),
                ("randrange on random.Random with a step, four arguments",
                 'port = random.Random.randrange(rng, %d, %d, 7)\n' % (lo, hi), (lo, hi - 1), lo),
                ("an instance whose name the module also binds to an int",
                 'def setup():\n    rng = 0\n\n\ndef go():\n    rng = random.Random()\n    port = random.Random.randrange(rng, 1000, %d)\n'
                 % hi, (1000, hi - 1), LOW)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, "computed into %d-%d" % span, n=first)

    def test_a_mapping_beside_a_randrange_s_start_and_stop_is_read_as_an_unbounded_step(self):
        """A ** mapping names no parameter, yet can fill any parameter left empty. Beside a randrange's start and stop,
        with its step left empty, it is read as a step interval() does not bound, by the span holding both, and each
        red plant asserts the span the census reports. A start of 30000 to 34999 and a stop of 30000 read 30000-34999:
        by position, with a display that gives a step of -7 (CPython returns values from 30001 to 34999 there), with
        start and stop by keyword, and with the stop by keyword after the mapping. So does a mapping whose name the
        module also binds to an int, since the census never reads what the mapping holds. 7d1bdcda6 passed the mapping
        over, read each of those as randrange(start, stop), from 30000 up to 29999, and reported none of them. A start
        of 50000 and a stop of 40000 read 40001-50000, where 7d1bdcda6 reported 50000-39999. A call whose parameters
        are all filled without the mapping is read as it is: randint(40000, 50000, **kw) is 40000-50000, and
        randrange(40000, 50000, 7, **kw) is 40000-49999. A call with any other parameter left empty beside a mapping is
        not read; WHAT IT CANNOT SEE lists it, with green plants."""
        lo, hi = LOW + 7232, LOW + 17232                                           # 40000 and 50000, built at run time
        s = LOW - 2768                                                             # 30000, built at run time
        for label, src, span, first in (
                ("a mapping beside start and stop", 'port = random.randrange(%d + os.getpid() %% 5000, %d, **kw)\n' % (s, s),
                 (s, s + 4999), LOW),
                ("a display that gives a step of -7",
                 'port = random.randrange(%d + os.getpid() %% 5000, %d, **{"step": -7})\n' % (s, s), (s, s + 4999), LOW),
                ("start and stop by keyword",
                 'port = random.randrange(start=%d + os.getpid() %% 5000, stop=%d, **kw)\n' % (s, s), (s, s + 4999), LOW),
                ("the stop by keyword after the mapping",
                 'port = random.randrange(%d + os.getpid() %% 5000, **kw, stop=%d)\n' % (s, s), (s, s + 4999), LOW),
                ("a mapping whose name the module also binds to an int",
                 'kw = 7\n\n\ndef go(kw):\n    port = random.randrange(%d + os.getpid() %% 5000, %d, **kw)\n' % (s, s),
                 (s, s + 4999), LOW),
                ("start above stop", 'port = random.randrange(%d, %d, **kw)\n' % (hi, lo), (lo + 1, hi), lo + 1),
                ("randint with both its parameters filled", 'port = random.randint(%d, %d, **kw)\n' % (lo, hi), (lo, hi), lo),
                ("randrange with its step filled", 'port = random.randrange(%d, %d, 7, **kw)\n' % (lo, hi), (lo, hi - 1),
                 lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, "computed into %d-%d" % span, n=first)

    def test_a_name_with_a_binding_the_census_does_not_record_is_unbounded_at_a_step(self):
        """At a randrange's step, and anywhere inside one, interval() bounds a name only when the census records every
        binding of it (BOUND), so a name bound to an int and also by a binding the census does not record reads there as
        the span holding both signs, for each such binding form (UNRECORDED_FORMS, and UNRECORDED_FORMS_312 on 3.12 and
        later, where they parse): each red plant binds K to 7 and by the form, and random.randrange(40000, 1000, K)
        reads 1001-40000, where 3d5b30b85 read K as 7, the call as 40000-999, and reported nothing (CPython returns
        values from 1001 to 40000 when K is negative). Anywhere else such a name reads by the ints the census records
        for it (and, where the position's value gives a reading with the name unbounded, by that one too: BOUND),
        where 6766e22fe left it unread and dropped a number the test writes: per form, random.randrange(S, 50000) with S
        bound to 40000 and by the form, and random.randrange(40000, E) with E bound to 50000 and by the form, read
        40000-49999, as their twins with no other binding do. So does a start beside a star import, which
        binds names its text does not write, and so does the name inside a display that is the position's value, in a
        loop's sequence, in a two-hop display, in str() and int(), in arithmetic outside a sum, and as randint's and
        randbelow's bounds, each red. A name bound to two ints reads the span from one to the other: a stop bound to
        1000, to 50000 and by E = f() reads 40000-49999, a start bound to 2000, to 40000 and by S = f() reads 1001-40000
        with a step of -7, and P bound to 1, to 45001 and by P = f() reads 1-45001 in a loop's sequence, where a reading
        of the first int alone counts none of the three. A value interval() does not read adds nothing to the span: P
        bound to 45001, to "x" and by P = f() reads 45001 inside a display. The two examples WHAT IT CANNOT SEE gave at
        3d5b30b85 (K = 7, then K = f() or K *= -1) are red, and so is a step beside a star import. Anywhere inside a
        step the name is unbounded too: random.randrange(1000, 40000, -K) reads 1000-39999, the span holding both signs,
        and a randrange whose step is K reads 1001-40000 inside arithmetic as either operand (+ 0, and 0 +), under a
        unary plus, in int() and in str(), 40000-78999 subtracted from 80000, 1000-39999 under a unary minus
        (-random.randrange(-1000, -40000, K)), and 0-39999 as randbelow's bound, where a reading that gave the nested
        call's step the ints the census records reports nothing. As the divisor of // or % such a name bound to two ints
        reads by the span between them, each value positive: 90002 // K, with K bound to 2, to 3 and by K = f(), reads
        30000-45001, random.randrange(40000, 100000 // K) reads 40000-49999, 50000 % K, with K bound to 60000, to 70000
        and by K = f(), reads 0-69999, and 20000 + os.getpid() % K, with K bound to 20000, to 30000 and by K = f(),
        reads 20000-49999, each red, where 3cdcef0ae read // and % only by a divisor of one value and reported nothing.
        offset_base() reads such a name by each int the census records for it, in turn: BASE + worker, with BASE bound
        to 40000 and by BASE = f(), or beside a star import, or to 40000, to 50000 and by BASE = f(), or to 1000, to
        40000 and by BASE = f(), or to 40000, to "x" and by BASE = f(), is an offset from 40000, and so is BASE * 1 +
        worker with BASE bound to 40000, to 50000 and by BASE = f(); 3cdcef0ae counted only the first two. The values a
        binding the census does not record gives are not read where the position's value gives no reading with the name
        unbounded, nor a float a binding it records gives such a name at a start or stop (WHAT IT CANNOT SEE, with green
        plants); a None at a stop and int() of a float or a string read as their own tests show."""
        lo, hi, n = LOW + 7232, LOW + 17232, _n()                                  # 40000, 50000 and 45001, built at run time
        forms = UNRECORDED_FORMS + (UNRECORDED_FORMS_312 if sys.version_info >= (3, 12) else ())
        for label, lines in forms:
            with self.subTest(label, role="step"):
                self.assertRed("test_plant.py", _bound_by("K", lines, 7) + "port = random.randrange(%d, 1000, K)\n" % lo,
                               "computed into 1001-%d" % lo, n=LOW)
            with self.subTest(label, role="start"):
                self.assertRed("test_plant.py", _bound_by("S", lines, lo) + "port = random.randrange(S, %d)\n" % hi,
                               "computed into %d-%d" % (lo, hi - 1), n=lo)
            with self.subTest(label, role="stop"):
                self.assertRed("test_plant.py", _bound_by("E", lines, hi) + "port = random.randrange(%d, E)\n" % lo,
                               "computed into %d-%d" % (lo, hi - 1), n=lo)
        for label, src, why, first in (
                ("a start with no other binding", 'S = %d\nport = random.randrange(S, %d)\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a stop with no other binding", 'E = %d\nport = random.randrange(%d, E)\n' % (hi, lo),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("K = 7, then K = f()", 'K = 7\nK = f()\nport = random.randrange(%d, 1000, K)\n' % n,
                 "computed into 1001-%d" % n, LOW),
                ("K = 7, then K *= -1", 'K = 7\nK *= -1\nport = random.randrange(%d, 1000, K)\n' % n,
                 "computed into 1001-%d" % n, LOW),
                ("a step name beside a star import", 'from m import *\nK = 7\nport = random.randrange(%d, 1000, K)\n' % lo,
                 "computed into 1001-%d" % lo, LOW),
                ("a start beside a star import", 'from m import *\nS = %d\nport = random.randrange(S, %d)\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("inside a display that is the position's value", 'P = %d\nP = f()\nrow = {"ports": [P]}\n' % n,
                 "the value of the key 'ports', a constant expression", n),
                ("in a loop's sequence", 'P = %d\nP = f()\nfor host, port in (("h", P),):\n    pass\n' % n,
                 "the loop target port, a constant expression", n),
                ("in a two-hop display", 'A = %d\nA = f()\nL = [A]\nrow = {"ports": L}\n' % n,
                 "through the name L, a constant expression", n),
                ("in str()", 'P = %d\nP = f()\nrow = {"port": str(P)}\n' % n, "the key 'port', a constant expression", n),
                ("in int()", 'P = %d\nP = f()\nrow = {"port": int(P)}\n' % n, "the key 'port', a constant expression", n),
                ("in arithmetic outside a sum", 'K = %d\nK = f()\nrow = {"port": K * 2}                # %d opens the file\n'
                 % (lo // 2, n), "the key 'port', a constant expression", lo),
                ("as randint's bound", 'K = %d\nK = f()\nport = random.randint(1, K)\n' % lo, "computed into 1-%d" % lo, LOW),
                ("as randbelow's bound", 'K = %d\nK = f()\nport = secrets.randbelow(K)\n' % lo,
                 "computed into 0-%d" % (lo - 1), LOW),
                ("a stop bound to two ints", 'E = 1000\nE = %d\nE = f()\nport = random.randrange(%d, E)\n' % (hi, lo),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a start bound to two ints, a step of -7",
                 'S = 2000\nS = %d\nS = f()\nport = random.randrange(S, 1000, -7)\n' % lo, "computed into 1001-%d" % lo, LOW),
                ("a name bound to two ints in a loop's sequence",
                 'P = 1\nP = %d\nP = f()\nfor host, port in (("h", P),):\n    pass\n' % n, "computed into 1-%d" % n, LOW),
                ("a name bound to an int and to a string, inside a display",
                 'P = %d\nP = "x"\nP = f()\nrow = {"ports": [P]}\n' % n, "the key 'ports', a constant expression", n),
                ("a step that negates the name", 'K = 7\nK = f()\nport = random.randrange(1000, %d, -K)\n' % lo,
                 "computed into 1000-%d" % (lo - 1), LOW),
                ("a randrange in arithmetic, its step the name",
                 'K = 7\nK = f()\nport = random.randrange(%d, 1000, K) + 0\n' % lo, "computed into 1001-%d" % lo, LOW),
                ("a randrange as arithmetic's right operand, its step the name",
                 'K = 7\nK = f()\nport = 0 + random.randrange(%d, 1000, K)\n' % lo, "computed into 1001-%d" % lo, LOW),
                ("a randrange subtracted, its step the name",
                 'K = 7\nK = f()\nport = %d - random.randrange(%d, 1000, K)\n' % (2 * lo, lo),
                 "computed into %d-%d" % (lo, 2 * lo - 1001), lo),
                ("a randrange under a unary minus, its step the name",
                 'K = 7\nK = f()\nport = -random.randrange(-1000, -%d, K)\n' % lo, "computed into 1000-%d" % (lo - 1),
                 LOW),
                ("a randrange under a unary plus, its step the name",
                 'K = 7\nK = f()\nport = +random.randrange(%d, 1000, K)\n' % lo, "computed into 1001-%d" % lo, LOW),
                ("a randrange in int(), its step the name",
                 'K = 7\nK = f()\nport = int(random.randrange(%d, 1000, K))\n' % lo, "computed into 1001-%d" % lo, LOW),
                ("a randrange in str(), its step the name",
                 'K = 7\nK = f()\nport = str(random.randrange(%d, 1000, K))\n' % lo, "computed into 1001-%d" % lo, LOW),
                ("a randrange as randbelow's bound, its step the name",
                 'K = 7\nK = f()\nport = secrets.randbelow(random.randrange(%d, 1000, K))\n' % lo,
                 "computed into 0-%d" % (lo - 1), LOW),
                ("the divisor of // bound to two ints",
                 'K = 2\nK = 3\nK = f()\nrow = {"port": %d // K}                # %d opens the file\n' % (2 * n, n),
                 "the key 'port', computed into %d-%d" % (2 * n // 3, n), LOW),
                ("the divisor of // bound to two ints, in a randrange's stop",
                 'K = 2\nK = 3\nK = f()\nport = random.randrange(%d, %d // K)\n' % (lo, 2 * hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("the divisor of % bound to two ints",
                 'K = %d\nK = %d\nK = f()\nrow = {"port": %d %% K}\n' % (hi + 10000, hi + 20000, hi),
                 "the key 'port', computed into 0-%d" % (hi + 20000 - 1), LOW),
                ("the divisor of % bound to two ints, its other operand unknown",
                 'K = 20000\nK = 30000\nK = f()\nport = 20000 + os.getpid() %% K          # %d opens the file\n' % n,
                 "computed into 20000-49999", LOW),
                ("a sum built on a name with another binding",
                 'BASE = %d\nBASE = f()\nsrv.bind(("127.0.0.1", BASE + worker))\n' % lo, "an offset from %d" % lo, lo),
                ("a sum built on a name beside a star import",
                 'from m import *\nBASE = %d\nsrv.bind(("127.0.0.1", BASE + worker))\n' % lo, "an offset from %d" % lo, lo),
                ("a sum built on a name bound to two ints",
                 'BASE = %d\nBASE = %d\nBASE = f()\nsrv.bind(("127.0.0.1", BASE + worker))\n' % (lo, hi),
                 "an offset from %d" % lo, lo),
                ("a sum built on a name bound to an int below the range and to one in it",
                 'BASE = 1000\nBASE = %d\nBASE = f()\nsrv.bind(("127.0.0.1", BASE + worker))\n' % lo,
                 "an offset from %d" % lo, lo),
                ("a sum built on a name bound to an int and to a string",
                 'BASE = %d\nBASE = "x"\nBASE = f()\nsrv.bind(("127.0.0.1", BASE + worker))\n' % lo,
                 "an offset from %d" % lo, lo),
                ("a sum built on a product of a name bound to two ints",
                 'BASE = %d\nBASE = %d\nBASE = f()\nsrv.bind(("127.0.0.1", BASE * 1 + worker))\n' % (lo, hi),
                 "an offset from %d" % lo, lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)

    def test_a_value_reads_each_name_with_a_binding_the_census_does_not_record_both_ways(self):
        """A value that reads several names with a binding the census does not record reads once for each way of taking
        each such name either by its recorded ints or as unbounded, every mix of the two, and counts by any of them
        (BOUND). Each red plant was not counted where the census read all such names one way or all the other: with
        BASE bound to 20000 and by BASE = g(), and OFFSET bound to 7 and by OFFSET = f(), BASE + OFFSET % 20000 reads
        20000-39999 (BASE by its int and OFFSET unbounded), and so do OFFSET % 20000 + BASE, the sum under a port-named
        key, and A + B + C % 20000 with A bound to 20000, B to 0 and C to 7, each by a call too, where reading every
        name by its ints gives 20007 and reading every one unbounded gives nothing. A value with more such names than
        eight, more than MIXES ways, is refused, counted with the names: B + Z1 + ... + Z7 + K % 20000, B bound to 20000,
        each Z to 0 and K to 7, each by a call too, whose value, with B and each Z at its int and K any value, is 20000
        to 39999; reading it by every name's ints, or by every name one way, gives nothing, a miss. Eight such names are read, not
        refused: A + ... + H, each bound to 1 and by a call, is green."""
        lo = LOW + 7232                                                            # 40000, built at run time
        c = 20000                                   # the base and the modulus, written apart from the plants' text
        two = "BASE = %d\nBASE = g()\nOFFSET = 7\nOFFSET = f()\n" % c
        nine = "B = %d\nB = g()\n" % c + "".join("Z%d = 0\nZ%d = f()\n" % (i, i) for i in range(1, 8)) + "K = 7\nK = f()\n"
        names = "B, K, " + ", ".join("Z%d" % i for i in range(1, 8))
        for label, src, why in (
                ("a sum, its base by its int and its other operand unbounded", two + "port = BASE + OFFSET %% %d\n" % c,
                 "an assignment to port, computed into 20000-39999"),
                ("the operands the other way round", two + "port = OFFSET %% %d + BASE\n" % c,
                 "an assignment to port, computed into 20000-39999"),
                ("under a port-named key", two + 'row = {"port": BASE + OFFSET %% %d}\n' % c,
                 "the key 'port', computed into 20000-39999"),
                ("three names", "A = %d\nA = g()\nB = 0\nB = h()\nC = 7\nC = f()\nport = A + B + C %% %d\n" % (c, c),
                 "an assignment to port, computed into 20000-39999"),
                ("nine names, refused", nine + "port = B + %s + K %% %d\n" % (" + ".join("Z%d" % i for i in range(1, 8)), c),
                 "an assignment to port, refused: it reads 9 names with a binding the census does not record (%s)" % names)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=LOW)
        with self.subTest("eight names, read"):
            self.assertGreen("test_x.py", "".join("%s = 1\n%s = f()\n" % (k, k) for k in "ABCDEFGH")
                             + "port = A + B + C + D + E + F + G + H                # %d opens the file\n" % lo)

    def test_offset_base_reads_an_operand_with_more_ways_than_each_by_its_spans(self):
        """offset_base() reads an operand value by value only while its names can take their values at most EACH ways;
        past that it reads the operand once, each name holding every value it is read by (THE RULE). Pinned by counting
        the interval() calls offset_base() makes itself, never by time: with A, B and C each bound by a loop over 40 ints
        and by a call, A + B + C + worker costs at most EACH calls for each operand it reads (six), where reading every
        way costs 40**3 + 40**2 + 3 * 40 + 1 = 65721; the sum is not counted either way (green). Past the cap the span
        holds every way's reading, so it only over-reads: with each name over 0 to 19 and 70000 to 70019, no way is in
        the range and the span 0-210057 reaches it, red, an over-read. A ** or a << past 2**BIG leaves the span unread
        where one way has a value, so such an operand counts too: 2 ** (A + B + C) + worker, A over 15 and 5000 to
        5038, B and C over 0 to 39, is red, as 2 ** 15 is 32768."""
        lo = LOW + 7232                                                            # 40000, built at run time
        opens = "                # %d opens the file\n" % lo

        def names(*values):
            return "".join("for %s in (%s):\n    pass\n%s = f()\n" % (k, ", ".join(map(str, v)), k)
                           for k, v in zip("ABC", values))
        small, gapped = list(range(40)), list(range(20)) + list(range(70000, 70020))
        src = names(small, small, small) + "port = A + B + C + worker" + opens
        tree = ast.parse(src)
        sc = _Scan(defs_of(tree), {}, lambda x, end=False: getattr(x, "lineno", 1), 0)
        sc.scan(tree)
        value = tree.body[-1].value
        operands = 2 * sum(isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)) for n in ast.walk(value))
        module, calls, depth = sys.modules[__name__], [0], [0]
        real = module.interval

        def counted(*args, **kwargs):
            calls[0] += depth[0] == 0               # offset_base()'s own calls, not interval()'s calls inside them
            depth[0] += 1
            try:
                return real(*args, **kwargs)
            finally:
                depth[0] -= 1
        module.interval = counted
        try:
            got = offset_base(value, sc.reads, sc.each)
        finally:
            module.interval = real
        self.assertIsNone(got)
        self.assertEqual(operands, 6)
        self.assertLessEqual(calls[0], operands * EACH, "offset_base() made %d interval() calls" % calls[0])
        self.assertGreater(calls[0], 0)
        self.assertGreen("test_x.py", src)
        for label, src in (
                ("past the cap, no way in the range, an over-read", names(gapped, gapped, gapped) + "port = A + B + C + worker"),
                ("past the cap, ** past 2**BIG", names([15] + list(range(5000, 5039)), small, small)
                 + "port = 2 ** (A + B + C) + worker")):
            with self.subTest(label):
                self.assertRed("test_plant.py", src + opens, "an assignment to port, an offset from %d" % LOW, n=LOW)

    def test_the_step_table_reaches_a_randrange_nested_anywhere(self):
        """interval() reads a name at a randrange's step, and anywhere inside one, by `steps`, which holds a name only
        when the census records every binding of it, each to an int, and every place interval() reads a nested
        expression hands `steps` on. Here K is bound to 7 and to -7.0, every binding recorded (CPython 3.10 and 3.11
        take -7.0 as a step, so random.randrange(40000, 1000, K) returns values from 1001 to 40000 there), so `steps`
        leaves K unbounded while the census's other table reads it as 7. Each red plant nests the call in one such place:
        as a sum's right operand (0 + the call) and its left one (the call + 0), in int() and in str(), as randbelow's
        bound, under a unary plus and a unary minus, in a conditional expression, and under a :=. Each is red under a
        mutant that hands the other table on at its place, which reads the call as 40000-999 and reports nothing. A
        step name with a binding the census does not record cannot pin these places, since the census also reads a
        value that reads such a name with the name left out of both tables (BOUND), which leaves it unbounded at the
        step whichever table reaches it."""
        lo = LOW + 7232                                                            # 40000, built at run time
        call, k = "random.randrange(%d, 1000, K)" % lo, "K = 7\nK = -7.0\n"
        for label, written, why in (
                ("a sum's right operand", "0 + " + call, "computed into 1001-%d" % lo),
                ("a sum's left operand", call + " + 0", "computed into 1001-%d" % lo),
                ("int()", "int(%s)" % call, "computed into 1001-%d" % lo),
                ("str()", "str(%s)" % call, "computed into 1001-%d" % lo),
                ("randbelow's bound", "secrets.randbelow(%s)" % call, "computed into 0-%d" % (lo - 1)),
                ("a unary plus", "+" + call, "computed into 1001-%d" % lo),
                ("a unary minus", "-random.randrange(-1000, -%d, K)" % lo, "computed into 1000-%d" % (lo - 1)),
                ("a conditional expression", call + " if x else 0", "computed into 0-%d" % lo),
                ("a :=", "(P := %s)" % call, "computed into 1001-%d" % lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", k + "port = %s\n" % written, why, n=LOW)

    def test_a_binding_form_the_census_does_not_classify_counts_as_one_it_does_not_record(self):
        """unrecorded_bindings() counts a field that holds a string, in a node type or field BINDING_FIELDS does not
        classify, as a binding the census does not record, as it would a form a later Python adds. The plant is a
        statement no Python has, with one such field naming K, beside K = 7: random.randrange(40000, 1000, K) reads
        1001-40000, the span holding both signs, where a census that took the field for no binding would read K as 7
        and report nothing."""
        class Bind(ast.stmt):                       # a binding statement Python does not have
            _fields = ("target_name",)
        lo = LOW + 7232                                                            # 40000, built at run time
        tree = ast.parse("K = 7\nport = random.randrange(%d, 1000, K)\n" % lo)
        tree.body.insert(0, Bind(target_name="K"))
        sc = _Scan({}, {}, lambda x, end=False: getattr(x, "lineno", 1), 0)
        sc.scan(tree)
        self.assertEqual([(v, w) for _l, v, w in sc.hits], [(LOW, "an assignment to port, computed into 1001-%d" % lo)])

    def test_a_name_python_mangles_in_a_class_is_unbounded_at_a_step(self):
        """Inside a class Python reads __K as _C__K, so a binding of either spelling binds the name a read of the other
        sees, and the census, which keys a name by its spelling, counts both as names with a binding it does not record
        (unrecorded_bindings()). As a step such a name reads as the span holding both signs, so random.randrange(40000,
        1000, K) reads 1001-40000 in each of these red plants, where 016098526 read the one int recorded under the
        spelling the call writes and reported nothing, though CPython returns values from 1001 to 40000 when the name
        the call reads is negative: each of MANGLED_FORMS; __K bound to 7 and _C__K to -7, every binding recorded; __K
        bound to 7 in the class body and read in a method, which reads the module's _C__K; and _C__K bound to 7, read
        outside the class, with a match in a method capturing __K under a global statement, a binding no Name node
        writes. As a start or a stop it reads by the ints the census records under the spelling the call writes, and,
        for the spelling with the two underscores, under the spelling it mangles to (THE RULE), as a name with a binding
        the census does not record does anywhere but at a step: each of MANGLED_FORMS so reads 40000-49999 (red), where
        6766e22fe reported nothing for the first two, and the census before the spellings were joined for the last. The
        census being module-wide, such a name is unbounded at a step wherever the module reads it: __K bound to 7 and
        read outside the class reads 1001-40000 too, an over-read, since CPython refuses that call for every value
        (red). A name with one leading underscore (_S) or two trailing ones (__S__) is not mangled, nor is any name in a
        class whose name is underscores alone (class __:), and each is read by its one recorded int: random.randrange(S,
        50000) with S bound to 40000 reads 40000-49999 (red)."""
        lo, hi = LOW + 7232, LOW + 17232                                            # 40000 and 50000, built at run time

        def module(lines, indent, spelled, k, v, call):
            text = "".join(x.format(k=k, c="C", v=v) + "\n" for x in lines)
            return text + " " * indent + call.format(n=spelled.format(k=k, c="C")) + "\n"
        for label, lines, indent, spelled in MANGLED_FORMS:
            with self.subTest(label, role="step"):
                self.assertRed("test_plant.py", module(lines, indent, spelled, "__K", 7,
                                                       "port = random.randrange(%d, 1000, {n})" % lo),
                               "computed into 1001-%d" % lo, n=LOW)
            with self.subTest(label, role="start"):
                self.assertRed("test_plant.py", module(lines, indent, spelled, "__S", lo,
                                                       "port = random.randrange({n}, %d)" % hi),
                               "computed into %d-%d" % (lo, hi - 1), n=lo)
            with self.subTest(label, role="stop"):
                self.assertRed("test_plant.py", module(lines, indent, spelled, "__E", hi,
                                                       "port = random.randrange(%d, {n})" % lo),
                               "computed into %d-%d" % (lo, hi - 1), n=lo)
        step = "    def m(self):\n        port = random.randrange(%d, 1000, __K)\n" % lo
        for label, src, why, first in (
                ("__K bound to 7 and _C__K to -7, every binding recorded",
                 "__K = 7\n_C__K = -7\n\n\nclass C:\n" + step, "computed into 1001-%d" % lo, LOW),
                ("__K bound to 7 in the class body, read in a method, which reads the module's _C__K",
                 "_C__K = f()\n\n\nclass C:\n    __K = 7\n\n" + step, "computed into 1001-%d" % lo, LOW),
                ("_C__K bound to 7, and by a match capture of __K under a global statement in a method of C",
                 "_C__K = 7\n\n\nclass C:\n    def g(self, x):\n        global __K\n        match x:\n"
                 "            case __K:\n                pass\n\n\nport = random.randrange(%d, 1000, _C__K)\n" % lo,
                 "computed into 1001-%d" % lo, LOW),
                ("__K read outside the class too, an over-read",
                 "__K = 7\nport = random.randrange(%d, 1000, __K)\n\n\nclass C:\n    def m(self):\n"
                 "        return __K\n" % lo,
                 "computed into 1001-%d" % lo, LOW),
                ("a name with one leading underscore, which Python does not mangle",
                 "_S = %d\n\n\nclass C:\n    port = random.randrange(_S, %d)\n" % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a name with two trailing underscores, which Python does not mangle",
                 "__S__ = %d\n\n\nclass C:\n    port = random.randrange(__S__, %d)\n" % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a class whose name is underscores alone, which mangles nothing",
                 "__S = %d\n\n\nclass __:\n    port = random.randrange(__S, %d)\n" % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)

    def test_a_name_every_binding_of_which_the_census_records_reads_the_span_of_its_ints(self):
        """A name every binding of which the census records reads, wherever it is read, by the span of the ints those
        bindings give, as it does beside a binding the census does not record: adding such a binding is never what makes
        a written number count (BOUND). Each red plant binds the name to two ints, or to an int and a string, a float or
        None, and in no other way, where a census that read such a name only when it held one value reported nothing: a
        start bound to 40000 and to 50000 reads random.randrange(S, 60000) as 40000-59999; a stop bound to 45000 and to
        50000 reads random.randrange(40000, E) as 40000-49999; P bound to 1 and to 45001 reads 1-45001 in a loop's
        sequence, in str() and in int(). The reading is keyed on the ints the census records, whatever other values the
        name holds: S bound to 40000 and to "x", or to 40000 and to 1.5, reads random.randrange(S, 50000) as
        40000-49999; E bound to 50000 and to None reads random.randrange(40000, E) as 0-49999, the span holding
        randrange(40000, 50000)'s reading and randrange(40000)'s, its stop left empty; P bound to 45001 and to "x" reads
        45001 inside a display. K bound to 40000 and to 45000 reads 1-45000 as randint's bound; and BASE + worker is a
        sum built on 40000 with BASE bound to 40000 and to 50000, or to 1000 and to 40000, and so is BASE * 1 + worker.
        At a step such a name, its every value an int, reads by their span: K bound to 3 and to 7 is a step never
        negative, so random.randrange(40000 + os.getpid() % 101, 39990 + os.getpid() % 211, K) reads 40000-40199 (red),
        where the span holding both signs, 39991-40199, also held values below the start, which CPython never returns
        there. The same reading drops two over-reads, each green: 40000 - K with K bound to 9000 and to 9001 (31000 or
        30999, never in the range), and 40000 + 90002 // K with K bound to 2 and to 3 (85001 or 70000), each read before
        as a sum built on 40000."""
        lo, hi, n = LOW + 7232, LOW + 17232, _n()                                  # 40000, 50000 and 45001, built at run time
        for label, src, why, first in (
                ("a start bound to two ints", 'S = %d\nS = %d\nport = random.randrange(S, %d)\n' % (lo, hi, hi + 10000),
                 "computed into %d-%d" % (lo, hi + 9999), lo),
                ("a stop bound to two ints", 'E = %d\nE = %d\nport = random.randrange(%d, E)\n' % (n - 1, hi, lo),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a name bound to two ints in a loop's sequence", 'P = 1\nP = %d\nfor host, port in (("h", P),):\n    pass\n'
                 % n, "the loop target port, computed into 1-%d" % n, LOW),
                ("a name bound to two ints in str()", 'P = 1\nP = %d\nrow = {"port": str(P)}\n' % n,
                 "the key 'port', computed into 1-%d" % n, LOW),
                ("a name bound to two ints in int()", 'P = 1\nP = %d\nrow = {"port": int(P)}\n' % n,
                 "the key 'port', computed into 1-%d" % n, LOW),
                ("a start bound to an int and to a string", 'S = %d\nS = "x"\nport = random.randrange(S, %d)\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a start bound to an int and to a float", 'S = %d\nS = 1.5\nport = random.randrange(S, %d)\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a stop bound to an int and to None", 'E = %d\nE = None\nport = random.randrange(%d, E)\n' % (hi, lo),
                 "computed into 0-%d" % (hi - 1), LOW),
                ("a name bound to an int and to a string, inside a display", 'P = %d\nP = "x"\nrow = {"ports": [P]}\n' % n,
                 "the key 'ports', a constant expression", n),
                ("a name bound to two ints as randint's bound", 'K = %d\nK = %d\nport = random.randint(1, K)\n' % (lo, n - 1),
                 "computed into 1-%d" % (n - 1), LOW),
                ("a sum built on a name bound to two ints",
                 'BASE = %d\nBASE = %d\nsrv.bind(("127.0.0.1", BASE + worker))\n' % (lo, hi), "an offset from %d" % lo, lo),
                ("a sum built on a name bound to an int below the range and to one in it",
                 'BASE = 1000\nBASE = %d\nsrv.bind(("127.0.0.1", BASE + worker))\n' % lo, "an offset from %d" % lo, lo),
                ("a sum built on a product of a name bound to two ints",
                 'BASE = %d\nBASE = %d\nsrv.bind(("127.0.0.1", BASE * 1 + worker))\n' % (lo, hi), "an offset from %d" % lo,
                 lo),
                ("a step bound to two positive ints",
                 'K = 3\nK = 7\nport = random.randrange(%d + os.getpid() %% 101, %d + os.getpid() %% 211, K)\n' % (lo, lo - 10),
                 "computed into %d-%d" % (lo, lo + 199), lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)
        for label, src in (
                ("a difference by a name bound to two ints, never in the range", 'K = 9000\nK = 9001\nport = %d - K\n' % lo),
                ("a sum on a quotient by a name bound to two ints, never in the range",
                 'K = 2\nK = 3\nport = %d + %d // K\n' % (lo, 2 * n))):
            with self.subTest(label):
                self.assertGreen("test_x.py", src)

    def test_no_reading_either_earlier_census_gave_is_dropped(self):
        """No reading two earlier censuses gave a shape is dropped (_earlier_readings(): the census that read a name with
        a binding it does not record as unbounded, and the one that read a name only where it recorded one value). A
        name with a binding the census does not record reads, at every position, the union of two readings (BOUND):
        with the name unbounded, wherever the expression gives a reading without it (an unknown operand of % by a
        divisor, a sum or difference built on a constant in the range, which offset_base() finds, and a step's span
        holding both signs), and with the name as the span of the ints the census records for it; where the first gives
        nothing (a bare name at a start or stop), the second stands alone. Each case fails when no reading the census
        gives the place holds an earlier one (_holds()), and each also has a hit where the census keeps one per place.
        The first fourteen failed where such a name read by its recorded ints alone: 20000 + K % 20000, with K bound to
        7 and by K = f(), read 20007 and was not counted (in an assignment, under a port-named key, beside a star import,
        and with K a name Python mangles in a class), where the census reads 20000-39999 again; 40000 + K and K + 40000
        with K bound to 30000, 40000 - K with K bound to 9000 (in an assignment and as an address's port) and 40000 +
        90002 // K with K bound to 3 read 70000, 70000, 31000 and 70000 and were not counted, each a sum built on 40000
        again; and 40000 + K and K % 20000 + 40000 with K bound to 7, and a randrange whose start is 20000 + K % 20000,
        kept a hit but read 40007, 40007 and 20007-49999 alone, where the census reads the sum built on 40000,
        40000-59999 and 20000-49999 again beside them. S - K and S + K pin that the reading with such a name unbounded
        in interval() reads it in offset_base() by its recorded ints, as that census did: S - K, with S bound to 70000
        and K to 40000 and by K = f(), read 30000 and was not counted, and S + K, with S bound to 9000 and K to 45001
        and by K = f(), read 54001 alone, where the census reads each as a sum built on K's int again. The next two read
        a private name whose values come only through the spelling its class mangles it to: 20000 + __K % 20000 and
        40000 + __K in a method of C, with _C__K bound to 7 or to 30000 and by _C__K = f(). The two earlier censuses, the
        one that read such a name by its recorded ints (none of the three read __K by _C__K's values) and this one all
        read them as 20000-39999 and as a sum built on 40000. They pin where the census looks for a name with a binding it does
        not record: among the names it reads by the values of both spellings (self.reads). Looked for among the names
        with a value recorded under the spelling written (self.bound), where __K has none, it read the two values by
        _C__K's ints alone, as 20007 and 70000, and counted neither. The next seven pin a divisor read by its positive
        and its negative part: with K bound to -1 and to 2 (with and without K = f(), and bound by a loop), 90002 // K
        and a randrange's stop of 100000 // K, with K bound to -1, to 60000 and by K = f(), 50000 % K, and with K bound
        to -5 and to 30000 (with and without K = f()), 20000 + os.getpid() % K read 45001, 40000-49999, 50000 and
        20000-49999 in the census that read K by its one recorded value, 2, 60000 or 30000, and each read nothing where
        the census read a divisor only when its every value was positive; the census reads them as -90002-90002,
        40000-99999, 0-59999 and 19996-49999. The last two read two names with a binding the census does not record in
        one value, A bound to 7 and by A = f() and B to 9 and by B = g() in 20000 + (A + B) % 20000, and A bound to
        30000 and B to 9000, each by a call too, in 40000 + A - B: the census that read such names as unbounded read
        20000-39999 and a sum built on 40000, and the other 61000, which the census reads beside the sum."""
        for label, src, old in _earlier_readings():
            with self.subTest(label):
                tree = ast.parse(src)
                sc = _Scan(defs_of(tree), {}, lambda x, end=False: getattr(x, "lineno", 1), 0)
                sc.scan(tree)
                got = [(v, why) for _l, v, why in sc.hits]
                self.assertEqual([r for r in old if not _holds(got, r)], [], "%s: a reading dropped; the census reads %r\n%s"
                                 % (label, got, src))
                self.assertTrue(self._hits("test_plant.py", src), "%s: no hit\n%s" % (label, src))

    def test_a_name_bound_to_none_at_a_randrange_s_stop_reads_as_a_stop_left_empty(self):
        """A stop that is a name a binding the census records gives None reads, beside the reading by the name's ints,
        as a stop left empty, randrange's own default, as a stop written as None does, when the step is left out or is
        the int 1 written there; the call reads as the span holding both (THE RULE). Each red plant was not counted
        where the census read such a name by its ints alone: E bound to None reads random.randrange(45001, E) as
        randrange(45001), 0-45000, and so with a step of 1 and with the stop by keyword; F bound to 1000, to None and by
        F = f() reads random.randrange(45001, F) as 0-45000, where randrange(45001, 1000) alone reads 45001-999, not
        counted; and E bound to None and to 50000 reads random.randrange(40000, E) as 0-49999. Python refuses a stop
        left empty beside any other step, and a None start, and each stays unread, green: E bound to None with a step of
        7 or of True, and random.randrange(S, 45001) with S bound to None."""
        lo, hi, n = LOW + 7232, LOW + 17232, _n()                                  # 40000, 50000 and 45001, built at run time
        for label, src, why in (
                ("a stop bound to None", 'E = None\nport = random.randrange(%d, E)\n' % n, "computed into 0-%d" % (n - 1)),
                ("a stop bound to None, a step of 1", 'E = None\nport = random.randrange(%d, E, 1)\n' % n,
                 "computed into 0-%d" % (n - 1)),
                ("a stop bound to None, by keyword", 'E = None\nport = random.randrange(%d, stop=E)\n' % n,
                 "computed into 0-%d" % (n - 1)),
                ("a stop bound to an int, to None and by a call", 'F = 1000\nF = None\nF = f()\nport = random.randrange(%d, F)\n'
                 % n, "computed into 0-%d" % (n - 1)),
                ("a stop bound to None and to an int", 'E = None\nE = %d\nport = random.randrange(%d, E)\n' % (hi, lo),
                 "computed into 0-%d" % (hi - 1))):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=LOW)
        for label, src in (
                ("a stop bound to None, a step of 7", 'E = None\nport = random.randrange(%d, E, 7)\n' % n),
                ("a stop bound to None, a step of True", 'E = None\nport = random.randrange(%d, E, True)\n' % n),
                ("a start bound to None", 'S = None\nport = random.randrange(S, %d)\n' % n)):
            with self.subTest(label):
                self.assertGreen("test_x.py", src)

    def test_the_hop_counts_a_string_a_binding_records_beside_one_it_does_not(self):
        """THE RULE's clause on a None, a float or a string a binding the census records is interval()'s alone: the hop
        counts every value recorded, a digit string wherever a string counts, whatever the name's other bindings. Each
        red plant is a name bound to "45001" and also by a binding the census does not record (P = f(), or a star
        import), read by the hop: under a port-named key, as the argument after --port, and beside an int it records
        (P bound to 7, to "45001" and by P = f()). A census that took the clause as the hop's too, dropping such a
        string, would read none of them."""
        n = _n()
        for label, src, why in (
                ("under a port-named key", 'P = "%d"\nP = f()\nrow = {"port": P}\n' % n, "the key 'port', through the name P"),
                ("after --port", 'P = "%d"\nP = f()\nsubprocess.run(["romp", "--port", P])\n' % n,
                 "the argument after the flag --port, through the name P"),
                ("beside an int", 'P = 7\nP = "%d"\nP = f()\nrow = {"port": P}\n' % n, "the key 'port', through the name P"),
                ("beside a star import", 'from m import *\nP = "%d"\nrow = {"port": P}\n' % n,
                 "the key 'port', through the name P")):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why)

    def test_int_of_a_name_reads_cpython_s_int_of_each_value_the_census_records(self):
        """int() of a name reads as the span of CPython's int() of each value the census records for it, a float or a
        string included and a value int() refuses passed over (THE RULE), so a test that writes a port as a string and
        hands it on through int() is counted. Each red plant was not counted where interval() read the name's ints
        alone: P bound to "45001" reads int(P) as 45001 under a port-named key and as an address's port, where the digit
        string itself would not be counted (an address takes its port as an int); so do P bound to 45001.0, to 45001.9
        (int() truncates), to
        b"45001", to "45001" in Arabic-Indic digits, and to "x" and to "45001" ("x" passed over); P bound to 7, to
        "45001" and by P = f() reads 7-45001; random.randrange(45001, int(E)), with E bound to 1000, to "45010" and by
        E = f(), or to 1000, to 45010.0 and by E = f(), reads 45001-45009; and int(BASE) + worker, with BASE bound to
        "40000" and to "50000", is a sum built on 40000. A name each value of which int() refuses stays unread, green:
        P bound to "x", and P bound to "45001.0"."""
        lo, hi, n = LOW + 7232, LOW + 17232, _n()                                  # 40000, 50000 and 45001, built at run time
        key, opens = "the key 'port', a constant expression", "                # %d opens the file" % (n + 1)
        for label, src, why, first in (
                ("a digit string", 'P = "%d"\nrow = {"port": int(P)}\n' % n, key, n),
                ("a digit string, as an address's port", 'P = "%d"\ns.bind(("127.0.0.1", int(P)))\n' % n,
                 "the port of the address ('127.0.0.1', ...), a constant expression", n),
                ("a float", 'P = %d.0\nrow = {"port": int(P)}%s\n' % (n, opens), key, n),
                ("a float int() truncates", 'P = %d.9\nrow = {"port": int(P)}%s\n' % (n, opens), key, n),
                ("bytes", 'P = b"%d"\nrow = {"port": int(P)}\n' % n, key, n),
                ("Arabic-Indic digits", 'P = "%s"\nrow = {"port": int(P)}\n' % _arabic(n), key, n),
                ("a string int() refuses and a digit string", 'P = "x"\nP = "%d"\nrow = {"port": int(P)}\n' % n, key, n),
                ("an int, a digit string and a call", 'P = 7\nP = "%d"\nP = f()\nrow = {"port": int(P)}\n' % n,
                 "the key 'port', computed into 7-%d" % n, LOW),
                ("a randrange's stop, a digit string beside an int and a call",
                 'E = 1000\nE = "%d"\nE = f()\nport = random.randrange(%d, int(E))\n' % (n + 9, n),
                 "computed into %d-%d" % (n, n + 8), n),
                ("a randrange's stop, a float beside an int and a call",
                 'E = 1000\nE = %d.0\nE = f()\nport = random.randrange(%d, int(E))\n' % (n + 9, n),
                 "computed into %d-%d" % (n, n + 8), n),
                ("a sum built on int() of a name bound to two digit strings",
                 'BASE = "%d"\nBASE = "%d"\nsrv.bind(("127.0.0.1", int(BASE) + worker))\n' % (lo, hi), "an offset from %d" % lo,
                 lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)
        for label, src in (
                ("a string int() refuses", 'P = "x"\nrow = {"port": int(P)}%s\n' % opens),
                ("a decimal string int() refuses", 'P = "%d.0"\nrow = {"port": int(P)}%s\n' % (n, opens))):
            with self.subTest(label):
                self.assertGreen("test_x.py", src)

    def test_int_of_a_constant_reads_cpython_s_int_of_it(self):
        """int() of a constant reads as CPython's int() of it, a constant int() refuses not read, as int() of a name
        reads each value the census records (THE RULE). Each red plant reported nothing where interval() passed int()'s
        argument through and bounded int constants alone: PORT = int("45001"), and int("45001") under a port-named key,
        int(" 45_001 "), int(45001.0), int(b"45001") and int() of 45001 in Arabic-Indic digits are 45001;
        random.randrange(int("40000"), 50000) is 40000-49999; and int("40000") + worker is a sum built on 40000. A
        constant each value of which int() refuses stays unread, green: int("x") and int("45001.0")."""
        lo, hi, n = LOW + 7232, LOW + 17232, _n()                                  # 40000, 50000 and 45001, built at run time
        key, opens = "the key 'port', a constant expression", "                # %d opens the file" % (n + 1)
        for label, src, why, first in (
                ("a digit string, assigned to a port-named target", 'PORT = int("%d")\n' % n,
                 "an assignment to PORT, a constant expression", n),
                ("a digit string", 'row = {"port": int("%d")}\n' % n, key, n),
                ("a digit string with spaces and a separator", 'row = {"port": int(" %s ")}\n' % _sep(n), key, n),
                ("a float", 'row = {"port": int(%d.0)}%s\n' % (n, opens), key, n),
                ("bytes", 'row = {"port": int(b"%d")}\n' % n, key, n),
                ("Arabic-Indic digits", 'row = {"port": int("%s")}\n' % _arabic(n), key, n),
                ("a random call's argument", 'port = random.randrange(int("%d"), %d)\n' % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a sum built on it", 'srv.bind(("127.0.0.1", int("%d") + worker))\n' % lo, "an offset from %d" % lo, lo)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)
        for label, src in (
                ("a string int() refuses", 'row = {"port": int("x")}%s\n' % opens),
                ("a decimal string int() refuses", 'row = {"port": int("%d.0")}%s\n' % (n, opens))):
            with self.subTest(label):
                self.assertGreen("test_x.py", src)

    def test_a_private_name_in_a_class_reads_the_values_of_the_spelling_it_mangles_to(self):
        """Inside class C, __K reads the values the census records under __K and under _C__K, the spelling CPython
        mangles it to there (THE RULE). Each red plant binds a mangled spelling at module level, which a census reading
        each spelling alone left __K in a method of C without: a display reads 45001, the hop reads 45001 (through the
        name __K, on the line that binds _C__K), and random.randrange(__S, 50000) with _C__S bound to 40000 reads
        40000-49999; the class's leading underscores are stripped (class _C mangles to _C__K, class __D to _D__K) and no
        other underscore is (class C_ mangles to _C___K, class C_x to _C_x__K); a class nested in C reads the spelling
        of each class around it, the innermost one's (_D__K, which CPython reads) among them; and with __K bound to 1
        and _C__K to 45001, __K in C reads 1-45001. The census joins the spellings wherever the module reads __K, so __K
        read outside C reads 45001 too, an over-read (red). A class named only with underscores mangles nothing, and a
        name ending in two underscores is not private: each stays unread, green (___K bound to 45001 and __K read in
        class __; _C__K__ bound to 45001 and __K__ read in C)."""
        lo, hi, n = LOW + 7232, LOW + 17232, _n()                                  # 40000, 50000 and 45001, built at run time
        method = "    def m(self):\n        return {\"ports\": [__K]}\n"
        for label, src, why, first in (
                ("a display in a method", "class C:\n" + method + "\n\n_C__K = %d\n" % n,
                 "the key 'ports', a constant expression", n),
                ("the hop in a method", 'class C:\n    def m(self):\n        return {"port": __K}\n\n\n_C__K = %d\n' % n,
                 "the key 'port', through the name __K", n),
                ("a randrange's start in a method",
                 "_C__S = %d\n\n\nclass C:\n    def m(self):\n        port = random.randrange(__S, %d)\n" % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("a class whose name has a leading underscore", "_C__K = %d\n\n\nclass _C:\n" % n + method,
                 "the key 'ports', a constant expression", n),
                ("a class whose name has two leading underscores", "_D__K = %d\n\n\nclass __D:\n" % n + method,
                 "the key 'ports', a constant expression", n),
                ("a class whose name ends in an underscore", "_C___K = %d\n\n\nclass C_:\n" % n + method,
                 "the key 'ports', a constant expression", n),
                ("a class whose name holds an underscore inside it", "_C_x__K = %d\n\n\nclass C_x:\n" % n + method,
                 "the key 'ports', a constant expression", n),
                ("a class nested in another", "_D__K = %d\n\n\nclass C:\n    class D:\n" % n
                 + "".join("    " + x + "\n" for x in method.splitlines()), "the key 'ports', a constant expression", n),
                ("both spellings bound", "__K = 1\n_C__K = %d\n\n\nclass C:\n" % n + method,
                 "the key 'ports', computed into 1-%d" % n, LOW),
                ("the name read outside the class too, an over-read",
                 "_C__K = %d\n\n\nclass C:\n    def m(self):\n        return __K\n\n\nrow = {\"ports\": [__K]}\n" % n,
                 "the key 'ports', a constant expression", n)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)
        for label, src in (
                ("a class whose name is underscores alone", "___K = %d\n\n\nclass __:\n" % n + method),
                ("a name ending in two underscores",
                 '_C__K__ = %d\n\n\nclass C:\n    def m(self):\n        return {"ports": [__K__]}\n' % n)):
            with self.subTest(label):
                self.assertGreen("test_x.py", src)

    def test_a_divisor_reads_by_its_positive_and_its_negative_part(self):
        """// and % read a divisor by its positive part and its negative part, each by its ends, as the span holding
        both, 0 in neither (THE RULE), where the census read a divisor only when its every value was positive and read
        each red plant as nothing. A divisor name bound to -1 and to 2, with and without K = f(), reads 90002 // K as
        -90002-90002; bound to -5 and to 30000 it reads 20000 + os.getpid() % K as 19996-49999. The edges: a divisor
        all negative (-90002 // K with K bound to -2 and to -3 is 30000-45001), one negative value (-90002 // -2 is
        45001, and 80000 + os.getpid() % -40000 is 40001-80000, the remainder taking the divisor's sign), one that
        touches 0 from above or from below (90002 // K with K bound to 0 and to 2, and -90002 // K with K bound to -2
        and to 0, are 45001-90002), one that straddles 0 (90002 // (os.getpid() % 3 - 1) is -90002-90002), and a reversed
        one of one sign from a call Python always refuses, read by its ends, an over-read (90002 // random.randint(3,
        2) is 30000-45001). A divisor that is 0, or a reversed one whose ends lie on either side of 0 (random.randint(1,
        0), which Python always refuses), has no part and is not read, green, and no divisor makes interval() divide by
        0: each divisor below, with a left operand of one value, of several or unknown, by // and by %, reads without
        raising, where 90002 // random.randint(1, 0) raised ZeroDivisionError in the census that read a divisor whose
        lowest value was positive by its two ends."""
        n, opens = _n(), "                # %d opens the file" % _n(1)
        key = "the key 'port', "
        for label, src, why, first in (
                ("// by a divisor name bound to a negative and a positive int",
                 'K = -1\nK = 2\nrow = {"port": %d // K}%s\n' % (2 * n, opens), key + "computed into -%d-%d" % (2 * n, 2 * n),
                 LOW),
                ("// by a divisor name bound to a negative and a positive int and by a call",
                 'K = -1\nK = 2\nK = f()\nrow = {"port": %d // K}%s\n' % (2 * n, opens),
                 key + "computed into -%d-%d" % (2 * n, 2 * n), LOW),
                ("an unknown operand of % by a divisor name bound to a negative and a positive int",
                 'K = -5\nK = 30000\nport = 20000 + os.getpid() %% K%s\n' % opens, "computed into 19996-49999", LOW),
                ("// by a divisor all negative", 'K = -2\nK = -3\nrow = {"port": -%d // K}%s\n' % (2 * n, opens),
                 key + "computed into 30000-%d" % n, LOW),
                ("// by one negative value", 'row = {"port": -%d // -2}%s\n' % (2 * n, opens), key + "a constant expression", n),
                ("an unknown operand of % by one negative value", 'port = 80000 + os.getpid() %% -%d\n' % (LOW + 7232),
                 "computed into 40001-80000", LOW + 7233),
                ("// by a divisor that touches 0 from above", 'K = 0\nK = 2\nrow = {"port": %d // K}%s\n' % (2 * n, opens),
                 key + "computed into %d-%d" % (n, 2 * n), n),
                ("// by a divisor that touches 0 from below", 'K = -2\nK = 0\nrow = {"port": -%d // K}%s\n' % (2 * n, opens),
                 key + "computed into %d-%d" % (n, 2 * n), n),
                ("// by a divisor that straddles 0", 'row = {"port": %d // (os.getpid() %% 3 - 1)}%s\n' % (2 * n, opens),
                 key + "computed into -%d-%d" % (2 * n, 2 * n), LOW),
                ("// by a reversed divisor of one sign, an over-read",
                 'row = {"port": %d // random.randint(3, 2)}\n' % (2 * n), key + "computed into 30000-%d" % n, LOW)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)
        for label, src in (
                ("// by 0", 'row = {"port": %d // 0}%s\n' % (2 * n, opens)),
                ("// by a reversed divisor across 0", 'row = {"port": %d // random.randint(1, 0)}\n' % (2 * n)),
                ("% by a reversed divisor across 0", 'row = {"port": %d %% random.randint(1, 0)}\n' % (2 * n)),
                ("an unknown operand of % by a reversed divisor across 0",
                 'row = {"port": os.getpid() % random.randint(1, 0)}\n')):
            with self.subTest(label):
                self.assertGreen("test_x.py", src)
        for divisor in ("0", "-0", "os.getpid() % 1", "random.randint(1, 0)", "random.randint(0, 0)",
                        "random.randint(0, -3)", "random.randint(3, 0)", "random.randint(2, -2)", "random.randint(-1, -3)",
                        "random.randint(3, 2)", "os.getpid() % 3 - 1", "os.getpid() % 4 - 3"):
            for left in ("%d" % (2 * n), "os.getpid() % 7 - 3", "os.getpid()"):
                for op in ("//", "%"):
                    text = "(%s) %s (%s)" % (left, op, divisor)
                    with self.subTest("no division by 0", expression=text):
                        interval(ast.parse(text, mode="eval").body)

    def test_each_integer_operator_reads_over_bounded_operands(self):
        """interval() reads every integer operator over bounded operands (THE RULE; Operators checks the class against
        the grammar and Python's arithmetic): ** and << and >> over operands never negative by their ends, &, | and ^
        over operands never negative by Python's own value where each is one value and by a span holding every value
        otherwise, ~ as -x - 1, not as 0 to 1, a conditional expression as the span holding its branches, and a := as
        its value. Each red plant reported nothing where interval() read + - * // % and the unary minus and plus
        alone: fixed ports (2 ** 15 + 1000 is 33768, 1 << 15 is 32768, 90002 >> 1, 45000 | 1, 45001 & 65535, 45000 ^ 1
        and ~-45002 are 45001, 45001 if x else 45002 is 45001-45002, (P := 45001) is 45001), spans ((1 + os.getpid() %
        2) ** 16 is 1-65536, (45000 + os.getpid() % 2) & 65535 is 0-45001, (45000 + os.getpid() % 2) | 1 is 0-65535),
        random calls (random.randint(2 ** 15, 2 ** 16 - 1) and random.randrange(1 << 15, 1 << 16) are 32768-65535,
        random.randint(40000 | 1, 50000) is 40001-50000, random.randrange(40000 if x else 41000, 50000) and
        random.randrange((S := 40000), 50000) are 40000-49999, and random.randrange(not x, 50000) is 0-49999), and a sum
        built on (40000 | 1), which reads as the one value 40001 and so as a sum's constant operand."""
        n, lo, hi = _n(), LOW + 7232, LOW + 17232                                  # 45001, 40000 and 50000
        opens, key, ass = "                # %d opens the file" % _n(1), "the key 'port', ", "an assignment to PORT, "
        for label, src, why, first in (
                ("** over constants", 'row = {"port": 2 ** 15 + 1000}%s\n' % opens, key + "a constant expression", LOW + 1000),
                ("<< over constants", "PORT = 1 << 15%s\n" % opens, ass + "a constant expression", LOW),
                (">> over constants", "PORT = %d >> 1%s\n" % (2 * n, opens), ass + "a constant expression", n),
                ("| over constants", "PORT = %d | 1\n" % (n - 1), ass + "a constant expression", n),
                ("& over constants", "PORT = %d & 65535\n" % n, ass + "a constant expression", n),
                ("^ over constants", "PORT = %d ^ 1\n" % (n - 1), ass + "a constant expression", n),
                ("~ over a constant", "PORT = ~-%d\n" % (n + 1), ass + "a constant expression", n),
                ("a conditional expression", "PORT = %d if x else %d\n" % (n, n + 1), ass + "computed into %d-%d" % (n, n + 1),
                 n),
                ("a :=", 'row = {"port": (P := %d)}\n' % n, key + "a constant expression", n),
                ("** over a span", 'row = {"port": (1 + os.getpid() %% 2) ** 16}%s\n' % opens, key + "computed into 1-65536",
                 LOW),
                ("& over a span", 'row = {"port": (%d + os.getpid() %% 2) & 65535}\n' % (n - 1), key + "computed into 0-%d" % n,
                 LOW),
                ("| over a span", 'row = {"port": (%d + os.getpid() %% 2) | 1}\n' % (n - 1), key + "computed into 0-65535",
                 LOW),
                ("** as a random call's arguments", "port = random.randint(2 ** 15, 2 ** 16 - 1)\n", "computed into 32768-65535",
                 LOW),
                ("<< as a random call's arguments", "port = random.randrange(1 << 15, 1 << 16)\n", "computed into 32768-65535",
                 LOW),
                ("| as a random call's argument", "port = random.randint(%d | 1, %d)\n" % (lo, hi),
                 "computed into %d-%d" % (lo + 1, hi), lo + 1),
                ("a conditional expression as a random call's argument",
                 "port = random.randrange(%d if x else %d, %d)\n" % (lo, lo + 1000, hi), "computed into %d-%d" % (lo, hi - 1), lo),
                ("a := as a random call's argument", "port = random.randrange((S := %d), %d)\n" % (lo, hi),
                 "computed into %d-%d" % (lo, hi - 1), lo),
                ("not as a random call's argument", "port = random.randrange(not x, %d)\n" % hi,
                 "computed into 0-%d" % (hi - 1), LOW),
                ("a sum built on | over constants", 'srv.bind(("127.0.0.1", (%d | 1) + worker))\n' % lo,
                 "an offset from %d" % (lo + 1), lo + 1)):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why, n=first)

    def test_the_stated_blind_spots_stay_unread(self):
        """Each example WHAT IT CANNOT SEE gives, planted green. The examples are known shapes, not a closed list: a change
        that reads one turns its subtest red, and the example leaves the docstring's list."""
        n = _n()
        self._write(os.path.join("tests", "plant_helpers.py"), "P = %d\n\n\ndef dial(host, port):\n    pass\n" % n)
        for label, name, src in (
                ("a parameter", "test_x.py", 'def go(p):\n    return {"port": p}\n\n\ngo(%d)\n' % n),
                ("a container", "test_x.py", 'CFG = {"a": %d}\nrow = {"port": CFG["a"]}\n' % n),
                ("a call's result", "test_x.py", 'def pick():\n    return %d\n\n\nrow = {"port": pick()}\n' % n),
                ("a name another module binds", "test_x.py",
                 'from plant_helpers import P\nrow = {"port": P}\nOTHER = %d                # opens the file\n' % (n + 1)),
                ("a name bound to a name (B = A)", "test_x.py", 'A = %d\nB = A\nrow = {"port": B}\n' % n),
                ("an unbound random method spelled on anything but a name or attribute called Random or SystemRandom",
                 "test_x.py",
                 'port = type(rng).randrange(rng, %d, %d)\nport = MyRandom.randrange(rng, %d, %d)\n' % (n, n + 9, n, n + 9)),
                ("a name or attribute called Random or SystemRandom that holds an instance", "test_x.py",
                 'Random = random.Random()\nport = Random.randint(%d, %d)\ncfg.SystemRandom = random.SystemRandom()\n'
                 'port = cfg.SystemRandom.randint(%d, %d)\n' % (n, n + 9, n, n + 9)),
                ("a name a module sets with no binding form beside a binding the census records", "test_x.py",
                 'K = 7\nglobals()["K"] = -7\nexec("K = -7")\nsetattr(sys.modules[__name__], "K", -7)\n'
                 'port = random.randrange(%d, 1000, K)\n' % n),
                ("a float where the census reads an int outside int()", "test_x.py",
                 'port = random.randrange(%d.0, %d)\n' % (n, n + 9)),
                ("a float bound to a name beside an int and a binding the census does not record", "test_x.py",
                 'E = 1000\nE = %d.0\nE = f()\nport = random.randrange(%d, E)\n' % (n + 9, n)),
                ("an operator interval() does not read over the operands it is given", "test_x.py",
                 'row = {"port": int(%d / 2)}\nrow = {"port": -(-%d | 0)}\nrow = {"port": (2 ** 5000 + %d) %% 2 ** 5000}\n'
                 % (2 * n, n, n)),
                ("a random call with an argument passed through a * sequence", "test_x.py",
                 'port = random.randrange(*(%d, %d))\nport = random.randrange(%d, *[%d])\nport = random.randint(*[%d, %d])\n'
                 % (n, n + 9, n, n + 9, n, n + 9)),
                ("a randrange with its stop left empty and a step that is 1 only at run time", "test_x.py",
                 'ONE = 1\nport = random.randrange(start=%d, step=ONE)\nport = random.randrange(%d, step=+1)\n'
                 'E = None\nport = random.randrange(%d, E, ONE)\n' % (n, n, n)),
                ("an attribute", "test_x.py", 'cfg.p = %d\nrow = {"port": cfg.p}\n' % n),
                ("a name bound to a digit string, inside a display that is the position's value", "test_x.py",
                 'P = "%d"\nrow = {"ports": [P]}\n' % n),
                ("a value a binding the census does not record gives, beside an int it records, at a start or stop",
                 "test_x.py", 'E = 1000\nE = f()\nport = random.randrange(%d, E)\n' % (LOW - 2768)),
                ("a run-time substitution into code text", "test_x.py",
                 'PROBE = "bus.peer_update({\'port\': __VALUE__})"\n'
                 'subprocess.run([sys.executable, "-c", PROBE.replace("__VALUE__", "%d")])\n' % n),
                ("a call other than the random calls", "test_x.py", 'port = random.choice((%d, %d))\n' % (n, n + 1)),
                ("a randrange with its stop left empty beside a ** mapping", "test_x.py",
                 'port = random.randrange(%d, **kw)\n' % n),
                ("a randrange with its stop left empty beside a ** mapping, its start by keyword and a step of 1", "test_x.py",
                 'port = random.randrange(start=%d, step=1, **kw)\n' % n),
                ("a randrange from a start below the range with its stop left empty beside a ** mapping", "test_x.py",
                 'port = random.randrange(%d, **kw)\n' % (LOW - 2768)),
                ("a randrange whose stop is a name bound to None, beside a ** mapping", "test_x.py",
                 'E = None\nport = random.randrange(%d, E, **kw)\n' % _n()),
                ("an unbounded computed port with no constant of a sum in the range", "test_x.py",
                 'port = base + i\nother_port = %d * k\n' % n),
                ("a host that is no loopback or wildcard literal", "test_x.py",
                 's.connect(("TESTHOST", %d))\nconn = HTTPConnection(self.host, %d)\n' % (n, n)),
                ("a name bound only to the empty string, in a tuple", "test_x.py", 'H = ""\ns.bind((H, %d))\n' % n),
                ("the empty string before a port in a call", "test_x.py", 'serve("", %d)\n' % n),
                ("a function no index holds, no host before it", "test_x.py",
                 'import vendorlib\nvendorlib.start_vendor_server(%d)\n' % n),
                ("a helper reached through import tests.helpers used whole", "test_x.py",
                 'import tests.plant_helpers\ntests.plant_helpers.dial("TESTHOST", %d)\n' % n),
                ("a tests/ helper the module does not import", "test_x.py", 'dial("TESTHOST", %d)\n' % n),
                ("a positional port in shell", "x.bats",
                 "    nc -l 127.0.0.1 %d &\n    python3 -m http.server %d --bind 127.0.0.1 &\n" % (n, n)),
                ("a positional port in JavaScript", "x.test.mjs", "const srv = startServer(%d);\n" % n),
                ("a JavaScript name that does not name a port", "y.test.ts",
                 "const P = %d;\nawait fetch(`http://127.0.0.1:${P}/x`);\n" % n),
                ("a %-template placeholder with a mapping key", "test_x.py", 'u = "http://127.0.0.1:%%(p)d/x" %% {"p": %d}\n' % n),
                ("a %-template placeholder with a flag, each of the five", "test_x.py",
                 "".join('w = "http://127.0.0.1:%%%sd/x" %% %d\n' % (flag, n) for flag in "-+ #0")),
                ("a %-template placeholder with a width", "test_x.py", 'v = "http://127.0.0.1:%%5d/x" %% %d\n' % n),
                ("a %-template placeholder with a precision", "test_x.py", 'v = "http://127.0.0.1:%%.5d/x" %% %d\n' % n),
                ("a %-template placeholder with a length modifier", "test_x.py", 'v = "http://127.0.0.1:%%ld/x" %% %d\n' % n),
                ("a %-template placeholder with another conversion", "test_x.py", 'v = "http://127.0.0.1:%%u/x" %% %d\n' % n),
                ("a template or an address that is no literal", "test_x.py",
                 'def go(t, base):\n    return t %% %d, base + str(%d)\n' % (n, n)),
                ("a template that is a call's result", "test_x.py", 'u = tmpl() %% %d\nv = tmpl().format(%d)\n' % (n, n)),
                ("a left side of a + that is a call's result", "test_x.py", 'u = base_url() + str(%d)\n' % n),
                ("digits after a placeholder host in an f-string", "test_x.py", 'u = f"http://{host}:%d/x"\n' % n),
                ("digits after a placeholder host in a %-template", "test_x.py", 'u = "http://%%s:%d/x" %% host\n' % n),
                ("digits after a placeholder host in a format template", "test_x.py",
                 'u = "http://{}:%d/x".format(host)\n' % n),
                ("digits after a placeholder host in a JavaScript template", "x.test.mjs",
                 "await fetch(`http://${host}:%d/x`);\n" % n),
                ("digits after a host name joined on with +, in JavaScript", "x.test.mjs",
                 'await fetch("http://" + host + ":%d");\n' % n),
                ("digits after a host name joined on with +, in Python", "test_x.py", 'u = "http://" + host + ":%d"\n' % n),
                ("digits after an f-string host with no // before it", "test_x.py", 'u = f"{host}:%d"\n' % n),
                ("an f-string as the right operand of a + after an address's colon", "test_x.py",
                 'u = "127.0.0.1:" + f"{%d}"\n' % n),
                ("digits after a bare shell $NAME", "x.bats", "    curl http://$HOST:%d/x\n" % n),
                ("a literal host whose colon starts the next operand, in Python", "test_x.py",
                 'u = "http://127.0.0.1" + ":%d"\n' % n),
                ("a literal host whose colon starts the next operand, in JavaScript", "x.test.mjs",
                 'await fetch("http://127.0.0.1" + ":%d");\n' % n),
                ("a colon and a port as operands of their own after a host name, in JavaScript", "x.test.mjs",
                 'await fetch("http://" + host + ":" + %d);\n' % n),
                ("userinfo before a host that is no loopback or wildcard literal", "test_x.py",
                 'u = "http://u@TESTHOST:%%d/x" %% %d\n' % n),
                ("an IPv6 literal other than [::1] or [::]", "test_x.py", 'u = "http://[2001:db8::1]:%%d/x" %% %d\n' % n),
                ("an option whose word names no port", "test_x.py",
                 'subprocess.run(["romp", "serve", "--listen", "%d"])\n' % n),
                ("an option and its number apart, or a short option", "test_x.py",
                 'subprocess.run(["romp", "--port"] + ["%d"])\nsubprocess.run(["romp", "-p", "%d"])\n' % (n, n)),
                ("a short option in shell", "z.bats", "    romp serve -p %d\n" % n),
                ("an option and its number apart in JavaScript", "w.test.mjs", "spawn(bin, ['--port'].concat(['%d']));\n" % n),
                ("a flag built at run time", "test_x.py", 'subprocess.run(["romp", "--" + "port", "%d"])\n' % n),
                ("a shell line continuation between an option and its number", "c1.bats",
                 "    run romp serve --port \\\n        %d\n" % n),
                ("a JavaScript comment, a block or a line one, between the + or the comma and the number", "c2.test.mjs",
                 "await fetch('http://127.0.0.1:' + /* the port */ %d + '/x');\n"
                 "await fetch('http://127.0.0.1:' + // the port\n    %d + '/x');\n"
                 "spawn(bin, ['serve', '--port', /* the port */ '%d']);\n"
                 "spawn(bin, ['serve', '--port', // the port\n    '%d']);\n" % (n, n, n, n)),
                ("a key that is a bare name with no port word", "test_x.py", 'K = "port"\nrow = {K: %d}\n' % n),
                ("code text that does not parse", "test_x.py", 'FRAG = "    km._notify_bus_peer(\'h\', %d, True)"\n' % n),
                ("code text that does not parse, a %-template", "test_x.py",
                 'TMPL = "km._notify_bus_peer(\'h\', %d, %%(up)s)"\n' % n)):
            with self.subTest(label):
                self.assertGreen(name, src)
        with self.subTest("a name another module sets with no binding form beside a binding the census records"):
            self._write(os.path.join("tests", "test_y.py"), "import plant_k\nplant_k.K = -7\n")
            self.assertGreen("plant_k.py", "K = 7\nport = random.randrange(%d, 1000, K)\n" % n)
        with self.subTest("a file whose only number in the range follows an escape sequence"):
            self.assertGreen("test_x.py", 'env = {"ROMP_POSTAL_PORT": "\\t%d"}\n' % n)
            self.assertRed("test_plant.py", 'env = {"ROMP_POSTAL_PORT": "\\t%d"}\nX = %d\n' % (n, n + 1),
                           "key 'ROMP_POSTAL_PORT'")            # opened for another number, the census reads it
        with self.subTest("a file outside the walk"):
            self._write(os.path.join("ui", "test-dom-shim.ts"), "export const PORT = %d;\n" % n)
            self._write(os.path.join("tools", "lab_x.py"), "PORT = %d\n" % n)
            self.assertEqual([h for h in census(self.d)["hits"] if not h[0].startswith("tests" + os.sep)], [])
            self.assertRed("y.test.ts", "export const PORT = %d;\n" % n, "rule decl")

    def test_a_hit_inside_a_string_that_spans_lines_names_its_own_line(self):
        n = _n()
        src = ('import textwrap\n'
               'PROBE = textwrap.dedent("""\\\n'
               '    import os\n'
               '    os.environ["ROMP_POSTAL_PORT"] = "%d"\n'
               '""")\n'
               'JS = """\n'
               'const srv = { port: %d };\n'
               '"""\n'
               'ONE = "x = 1\\nbus.peer_update({\\"port\\": %d})"\n') % (n, n, n)
        self.assertEqual([h[1] for h in self._hits("test_plant.py", src)], [4, 7, 9], src)

    def test_a_port_below_the_range_or_port_one_is_not_counted(self):
        self.assertGreen("test_x.py", 'ps.peer_update({"host": "TESTHOST", "port": 1, "up": True})\nrow = {"local_port": 2, "bus_port": %d}\n'
                         % (LOW - 1))

    def test_the_walk_skips_hidden_and_build_directories(self):
        n = _n()
        for d in (".claude/worktrees/old/tools", "vscode-extension/node_modules/pkg", "site/assets", "venv/lib"):
            os.makedirs(os.path.join(self.d, d), exist_ok=True)
            with open(os.path.join(self.d, d, "x.test.js"), "w", encoding="utf-8") as f:
                f.write("server.listen(%d);\n" % n)
        self.assertEqual([h for h in census(self.d)["hits"] if h[0].endswith("x.test.js")], [])
        self.assertRed("y.test.js", "server.listen(%d);\n" % n, "rule call")

    def test_the_range_ends_are_32768_and_65535(self):
        """The ends, with values built apart from LOW and HIGH so a change to either constant shows: 2**15 and 2**16 - 1
        are read, 2**15 - 1 is not, and neither is 2**16, which no port can be."""
        for v in (2 ** 15, 2 ** 16 - 1):
            with self.subTest(v):
                self.assertRed("test_plant.py", 'row = {"local_port": %d}\n' % v, "key 'local_port'", n=v)
        for v in (2 ** 15 - 1, 2 ** 16):
            with self.subTest(v):
                self.assertGreen("test_x.py", 'row = {"local_port": %d}\n' % v)

    def test_the_plural_ports_names_a_port(self):
        """ports is a port word as port is: a ports key, and a *ports parameter taking the extra arguments."""
        n = _n()
        for label, src, why in (
                ("a ports key", 'row = {"ports": [%d, 1]}\n' % n, "key 'ports'"),
                ("a *ports parameter", 'def listen_all(host, *ports):\n    pass\n\n\nlisten_all("TESTHOST", %d)\n' % n,
                 "argument ports of listen_all()")):
            with self.subTest(label):
                self.assertRed("test_plant.py", src, why)


class _RandrangeEnds(random.Random):
    """CPython's Random with only its draw replaced: _randbelow(n) returns n - 1 when top is set and 0 when it is not, so
    randrange, CPython's own code, returns the lowest value a call can return, or the highest."""
    top = False

    def _randbelow(self, n):
        return n - 1 if self.top else 0


class RandrangeAgainstCPython(unittest.TestCase):
    """THE RULE's randrange reading, checked against CPython's own randrange over generated calls (the ruling of
    2026-10-05 on fork PR 973: one rule, and a property test in place of one more plant per pass; the closing check
    that day grew the generator with the spellings it found misread or unread, and the owner's calls after it with a
    name bound to ints the census records and by a binding it does not record, with a name Python mangles in a class,
    and with the readings the owner's calls after them added: a name every binding of which the census records, bound
    to several ints, a name with a binding it does not record under % by a constant, a stop name bound to None, int() of
    a name bound to strings and floats, and a private name read in a method, bound under its mangled spelling; and the
    light check at the pushed head after them with a start or stop name bound to ints beside a string, a float or
    None, with a divisor bound to ints of both signs, with each operator the census reads, with int() of a constant,
    with a call that is a sum's right operand, its step a name with a binding the census does not record, and with two
    such names in a start or stop)."""

    SEED = 973                                      # fixed: the same calls, samples and draws on every run
    STEPS = (-1000, -7, -2, -1, 0, 1, 2, 7, 1000)   # the values a step interval() does not bound takes
    STEP_SHAPES = (                                 # (the step as written or None, left out; its values or None, unbounded)
        ("7", (7, 7)), ("1 + os.getpid() % 5", (1, 5)),                                       # known positive
        ("0 - 7", (-7, -7)), ("-7", (-7, -7)), ("-(1 + os.getpid() % 5)", (-5, -1)),          # known negative
        ("os.getpid() % 3 - 1", (-1, 1)), ("-(os.getpid() % 11 - 5)", (-5, 5)),               # either sign
        ("os.getpid() % 6 - 5", (-5, 0)), ("os.getpid() % 6", (0, 5)), ("0", (0, 0)),         # 0 at an end, or alone
        ("k", None), ("-k", None),                                                            # unbounded
        (None, (1, 1)))                                                                       # left out: 1
    FORMS = ((), ("step",), ("stop", "step"), ("step", "start", "stop"),   # the parameters given by keyword, in order,
             ("**step",), ("start", "**step", "stop"))                    # **step: the step in a ** mapping
    RELATIONS = ("start below stop", "start above stop", "start's highest value stop's lowest",
                 "start's lowest value stop's highest", "start and stop one value", "overlapping, start lower",
                 "overlapping, start higher", "start inside stop", "stop inside start")
    NAMED_STEPS = (("{k} = -7",), ("{k} = 7", "{k} = -7"), ("{k} = -2", "{k} = 1"),   # a step name's bindings, {k} the
                   ("{k} = -7", "{k} = +7"), ("for {k} in (1, -1):",),               # name: signed numbers alone and
                   ("for {k} in (-7, 2, 7):",))                                      # beside others, and a loop's
    BOOL_STEPS = (("True", [True]), ("-True", [-1]))                                  # a step written with a bool
    NONE_FORMS = (((), None), ((), "1"), (("stop",), None), (("start", "stop"), None),   # randrange(S, None, ...): the
                  (("stop", "step"), "1"), ((), "7"), (("step",), "-1"), ((), "True"))  # last three Python refuses
    CLASSES = (("random.Random", random.Random), ("random.SystemRandom", random.SystemRandom), ("Random", random.Random))
    STEP_BINDS = ((3, 7), (-7, -3), (-2, 7), (0, 5), (-5, 0), (1, 2, 1000))   # a step name's ints, every binding recorded:
                                                                             # one sign, both, or 0 at an end

    @staticmethod
    def _shape(relation, c, rng):
        """(start's interval, stop's interval) in `relation`, about the value `c`."""
        w1, w2, g = rng.randint(0, 40), rng.randint(0, 40), rng.randint(1, 30)
        return {"start below stop": ((c - g - w1, c - g), (c, c + w2)),
                "start above stop": ((c, c + w1), (c - g - w2, c - g)),
                "start's highest value stop's lowest": ((c - w1, c), (c, c + w2)),
                "start's lowest value stop's highest": ((c, c + w1), (c - w2, c)),
                "start and stop one value": ((c, c), (c, c)),
                "overlapping, start lower": ((c - w1 - 1, c + g), (c, c + g + w2 + 1)),
                "overlapping, start higher": ((c, c + g + w1 + 1), (c - w2 - 1, c + g)),
                "start inside stop": ((c, c + g), (c - w2 - 1, c + g + w2 + 1)),
                "stop inside start": ((c - w1 - 1, c + g + w1 + 1), (c, c + g))}[relation]

    @staticmethod
    def _call(form, args):
        """randrange's arguments as (positional, keyword), the parameters `form` names given by keyword in its order, a
        name **p giving p in a ** mapping, whose value is None when the call gives no p (an empty mapping); `args` maps
        each parameter the call gives to its value or its text."""
        return ([args[p] for p in ("start", "stop", "step") if p in args and p not in form and "**" + p not in form],
                [(p, args.get(p.lstrip("*"))) for p in form if p.lstrip("*") in args or p.startswith("**")])

    @staticmethod
    def _text(iv):
        """An interval as a call writes it: the value, or its lowest value plus os.getpid() % its width."""
        return "%d" % iv[0] if iv[0] == iv[1] else "%d + os.getpid() %% %d" % (iv[0], iv[1] - iv[0] + 1)

    def _grown(self):
        """The calls the closing check of 2026-10-05 found misread or unread, each as (label, start, stop, (step as
        written, its values), form, how), from a generator seeded apart from the grid's so the grid's calls, samples and
        draws stay as they were. A start, stop or step is an interval (lowest, highest), a list of the values it takes,
        or None for an unbounded step; `how` holds the lines written before the call ("pre"; "indent", 4 when the first
        is a for loop's header and the call its body), the start or stop as written where it is no interval's text, the
        callee as written and the class whose randrange runs it, and the exceptions a call Python refuses raises. Per
        relation and form: a step name for each of NAMED_STEPS; a start, and half the time a stop, offset by a name
        bound to a negative number or written as such a name negated; a unary plus over the start, half the time over
        the stop and half the time over the step; and the call spelled on random.Random, random.SystemRandom or Random,
        the instance first, the step each time drawn from STEP_SHAPES. Then a start or stop written as True or False,
        the step drawn from STEP_SHAPES and BOOL_STEPS, twice per form; and a stop written as None, three times for each
        of NONE_FORMS."""
        rng, out = random.Random(self.SEED + 1), []

        def near():
            return rng.choice((LOW + rng.randint(-60, 60), HIGH + rng.randint(-60, 60), rng.randint(LOW + 100, HIGH - 100),
                               rng.randint(1024, LOW - 200)))

        def bound(line):
            v = ast.literal_eval(line.split(" in ")[1].rstrip(":") if line.startswith("for ") else line.split(" = ")[1])
            return v if isinstance(v, tuple) else (v,)
        for relation in self.RELATIONS:
            for form in self.FORMS:
                for binds in self.NAMED_STEPS:
                    name = "K%d" % len(out)
                    out.append(("a step name: " + "; ".join(b.format(k="K").rstrip(":") for b in binds),)
                               + self._shape(relation, near(), rng)
                               + ((name, sorted({v for b in binds for v in bound(b)})), form,
                                  {"pre": [b.format(k=name) for b in binds],
                                   "indent": 4 if binds[0].startswith("for ") else 0}))
                s, e = self._shape(relation, near(), rng)
                how = {"pre": []}
                for p, iv in (("start", s), ("stop", e)):
                    if p == "start" or rng.random() < 0.5:
                        name, rest = "%s%d" % ("S" if p == "start" else "E", len(out)), self._text(iv)[len("%d" % iv[0]):]
                        if rng.random() < 0.5:
                            m = rng.randint(1, 5000)
                            how[p], line = "%d + %s%s" % (iv[0] + m, name, rest), "%s = -%d" % (name, m)
                        else:
                            how[p], line = "-%s%s" % (name, rest), "%s = -%d" % (name, iv[0])
                        how["pre"].append(line)
                out.append(("a start or stop offset by a name bound to a negative number", s, e,
                            rng.choice(self.STEP_SHAPES), form, how))
                s, e = self._shape(relation, near(), rng)
                how = {}
                for p, iv in (("start", s), ("stop", e)):
                    if p == "start" or rng.random() < 0.5:
                        how[p] = rng.choice(("+(%s)", "+%s")) % self._text(iv)
                k, kiv = rng.choice(self.STEP_SHAPES)
                if k is not None and rng.random() < 0.5:
                    k = "+(%s)" % k
                out.append(("a unary plus", s, e, (k, kiv), form, how))
                spelled, cls = rng.choice(self.CLASSES)
                out.append(("the unbound method",) + self._shape(relation, near(), rng)
                           + (rng.choice(self.STEP_SHAPES), form, {"callee": spelled + ".randrange(rng, ", "cls": cls}))
        for relation in ("start below stop", "start above stop"):
            for form in self.FORMS:
                for _ in range(2):
                    b, c = rng.choice((True, False)), near()
                    iv, step = (c, c + rng.randint(0, 40)), rng.choice(self.STEP_SHAPES + self.BOOL_STEPS)
                    out.append(("a bool start or stop", [b], iv, step, form, {"start": str(b)}) if relation == "start below stop"
                               else ("a bool start or stop", iv, [b], step, form, {"stop": str(b)}))
        for form, k in self.NONE_FORMS:
            for _ in range(3):
                c = near()
                out.append(("a stop written as None", (c, c + rng.randint(0, 40)), [None],
                            (k, None if k is None else [ast.literal_eval(k)]), form,
                            {"stop": "None", "raises": (ValueError, TypeError)}))
        return out

    def _mixed(self):
        """A name bound to ints the census records and also by each of UNRECORDED_FORMS, written as the step (twice per
        relation, its int positive and then negative), as the start and as the stop, each case as _grown() writes them,
        from a generator seeded apart from the grid's and _grown()'s so their calls, samples and draws stay as they
        were. A step name is bound to one int and takes STEPS, its int among them (1 or 7, -1 or -7): at a step THE RULE
        reads such a name as unbounded, so it takes any value. A start or stop name is bound to several ints: one drawn
        from an interval in the relation, that int less 1000 and plus 1000, and the interval's ends and a seeded value
        inside it. It takes those values alone, since THE RULE reads a start or stop by the ints its recorded bindings
        give, and not a value a binding the census does not record gives (WHAT IT CANNOT SEE). The step of a start or
        stop case is drawn from STEP_SHAPES, and each case's form from FORMS. After them, the same four cases per
        relation for a name Python mangles in a class, written each way MANGLED_FORMS writes it, drawn on after the
        others so theirs stay as they were; there a step's form is one with no ** mapping, since a step a mapping gives
        is unbounded whatever the name holds."""
        rng, out = random.Random(self.SEED + 2), []

        def near():
            return rng.choice((LOW + rng.randint(-60, 60), HIGH + rng.randint(-60, 60), rng.randint(LOW + 100, HIGH - 100),
                               rng.randint(1024, LOW - 200)))

        def pre(lines, mangled, k, c, v):
            """The lines that bind the name `k` (in the class `c` when `mangled`) before its call."""
            return [x.format(k=k, c=c, v=v) for x in lines] if mangled else _bound_by(k, lines, v).splitlines()
        shapes = [("a name bound to an int and by " + label, lines, None) for label, lines in UNRECORDED_FORMS] \
            + [(label, lines, (indent, spelled)) for label, lines, indent, spelled in MANGLED_FORMS]
        unmapped = tuple(f for f in self.FORMS if not any(p.startswith("**") for p in f))
        for label, lines, mangled in shapes:
            for relation in self.RELATIONS:
                for role, sign in (("step", 1), ("step", -1), ("start", 0), ("stop", 0)):
                    s, e = self._shape(relation, near(), rng)
                    forms = unmapped if mangled and role == "step" else self.FORMS
                    name, form = "M%s%d" % ({"step": "K", "start": "S", "stop": "E"}[role], len(out)), rng.choice(forms)
                    tag, k, c = "the %s, %s" % (role, label), ("__" if mangled else "") + name, "C%d" % len(out)
                    written, how = (mangled[1].format(k=k, c=c), {"indent": mangled[0]}) if mangled else (k, {})
                    if role == "step":
                        v = sign * rng.choice((1, 7))
                        out.append((tag, s, e, (written, sorted(set(self.STEPS) | {v})), form,
                                    dict(how, pre=pre(lines, mangled, k, c, v))))
                        continue
                    iv = s if role == "start" else e
                    v = rng.randint(*iv)
                    takes = sorted({v - 1000, v, v + 1000, iv[0], iv[1], rng.randint(*iv)})
                    out.append(("the %s, bound to several ints, %s" % (role, label), takes if role == "start" else s,
                                e if role == "start" else takes, rng.choice(self.STEP_SHAPES), form,
                                dict(how, pre=["%s = %d" % (written, x) for x in takes if x != v]
                                     + pre(lines, mangled, k, c, v), **{role: written})))
        return out

    def _recorded(self):
        """The calls the owner's calls of 2026-10-05 after _mixed()'s read, from a generator seeded apart from the grid's,
        _grown()'s and _mixed()'s so their calls, samples and draws stay as they were. Per relation: a step name every
        binding of which the census records, bound to the ints of one of STEP_BINDS and taking each, twice, each time in
        a form drawn from FORMS; and a start and a stop name bound to several ints as _mixed() binds them, with no other
        binding, the step drawn from STEP_SHAPES and the form from FORMS. Then, per relation, a start and a stop written
        as the interval's lowest value plus K % its width, or its highest less K % its width, K bound to an int and by
        K = f(): since K % the width lies in the interval whatever K holds, the start or stop takes the values K gives
        for its int, for 0 and for the width less one, and for two seeded ints no binding gives, and THE RULE reads it,
        with K unbounded, as the whole interval (BOUND). Then, for each of NONE_FORMS, a stop name bound to None alone,
        beside an int, and beside an int and by a call, taking None and the int, with the exceptions a stop left empty
        beside a step other than 1 raises. Then, per relation, a start and a stop written as int() of a name bound to a
        digit string, a float that int() truncates, a digit string with spaces, a bytes literal, an int, and two strings
        int() refuses, and half the time by a call too, taking CPython's int() of each value int() takes. Last, per
        relation, a start and a stop that a method of a class reads as a private name, bound at module level only under
        the spelling the class mangles it to (the class's name drawn with no, one or two leading underscores, and by
        turns with no other underscore, one at its end or one inside it), taking each value bound there."""
        rng, out = random.Random(self.SEED + 3), []

        def near():
            return rng.choice((LOW + rng.randint(-60, 60), HIGH + rng.randint(-60, 60), rng.randint(LOW + 100, HIGH - 100),
                               rng.randint(1024, LOW - 200)))
        for relation in self.RELATIONS:
            for _ in range(2):
                ints, name = rng.choice(self.STEP_BINDS), "RK%d" % len(out)
                out.append(("a step name, every binding recorded",) + self._shape(relation, near(), rng)
                           + ((name, list(ints)), rng.choice(self.FORMS), {"pre": ["%s = %d" % (name, v) for v in ints]}))
            for role in ("start", "stop"):
                s, e = self._shape(relation, near(), rng)
                iv = s if role == "start" else e
                v = rng.randint(*iv)
                takes = sorted({v - 1000, v, v + 1000, iv[0], iv[1], rng.randint(*iv)})
                name = "R%s%d" % ({"start": "S", "stop": "E"}[role], len(out))
                out.append(("the %s, bound to several ints, every binding recorded" % role, takes if role == "start" else s,
                            e if role == "start" else takes, rng.choice(self.STEP_SHAPES), rng.choice(self.FORMS),
                            {"pre": ["%s = %d" % (name, x) for x in takes], role: name}))
        for relation in self.RELATIONS:
            for role in ("start", "stop"):
                s, e = self._shape(relation, near(), rng)
                (lo, hi), name = (s if role == "start" else e), "RM%d" % len(out)
                w, v, up = hi - lo + 1, rng.randint(0, 5000), rng.random() < 0.5
                ks = (v, 0, w - 1, rng.randint(-10 ** 6, 10 ** 6), rng.randint(-10 ** 6, 10 ** 6))
                takes = sorted({lo + k % w if up else hi - k % w for k in ks})
                written = "%d + %s %% %d" % (lo, name, w) if up else "%d - %s %% %d" % (hi, name, w)
                out.append(("the %s, a name with a binding the census does not record under %% by a constant" % role,
                            takes if role == "start" else s, e if role == "start" else takes, rng.choice(self.STEP_SHAPES),
                            rng.choice(self.FORMS), {"pre": ["%s = %d" % (name, v), "%s = f()" % name], role: written}))
        for form, k in self.NONE_FORMS:
            for others in ((), ("an int",), ("an int", "a call")):
                c, name = near(), "RN%d" % len(out)
                ints = [near()] if others else []
                out.append(("a stop name bound to None", (c, c + rng.randint(0, 40)), [None] + ints,
                            (k, None if k is None else [ast.literal_eval(k)]), form,
                            {"pre": ["%s = None" % name] + ["%s = %d" % (name, x) for x in ints]
                             + (["%s = f()" % name] if "a call" in others else []), "stop": name,
                             "raises": (ValueError, TypeError)}))
        for relation in self.RELATIONS:
            for role in ("start", "stop"):
                s, e = self._shape(relation, near(), rng)
                (lo, hi), name = (s if role == "start" else e), "RI%d" % len(out)
                v, w = rng.randint(lo, hi), rng.randint(lo, hi)
                written = ['"%d"' % v, '%d.5' % w, '" %d "' % lo, 'b"%d"' % hi, '"x"', '"%d.0"' % v, "%d" % rng.randint(lo, hi)]
                takes = []
                for x in written:
                    try:
                        takes.append(int(ast.literal_eval(x)))
                    except ValueError:
                        pass
                pre = ["%s = %s" % (name, x) for x in written] + (["%s = f()" % name] if rng.random() < 0.5 else [])
                out.append(("the %s, int() of a name bound to strings and floats" % role, sorted(set(takes)) if role == "start"
                            else s, e if role == "start" else sorted(set(takes)), rng.choice(self.STEP_SHAPES),
                            rng.choice(self.FORMS), {"pre": pre, role: "int(%s)" % name}))
        for relation in self.RELATIONS:
            for role in ("start", "stop"):
                s, e = self._shape(relation, near(), rng)
                iv, n = (s if role == "start" else e), len(out)
                takes = sorted({iv[0], iv[1], rng.randint(*iv)})
                shape = ("CJ%d", "CJ%d_", "C_J%d")[n % 3]   # by turns: no other underscore, one at the end, one inside
                cls = rng.choice(("", "_", "__")) + shape % n
                out.append(("the %s, a private name read in a method, bound under its mangled spelling" % role,
                            takes if role == "start" else s, e if role == "start" else takes, rng.choice(self.STEP_SHAPES),
                            rng.choice(self.FORMS), {"pre": ["_%s__RJ%d = %d" % (cls.lstrip("_"), n, x) for x in takes]
                                                     + ["class %s:" % cls, "    def m(self):"], "indent": 8,
                                                     role: "__RJ%d" % n}))
        return out

    def _checked(self):
        """The calls the light check of 2026-10-05 at the pushed head and the owner's calls after it added, from a
        generator seeded apart from the grid's, _grown()'s, _mixed()'s and _recorded()'s so their calls, samples and
        draws stay as they were. Per relation, a start and a stop name every binding of which the census records, bound
        to several ints as _mixed() binds them and to a string or a float with a fraction, which no call takes and
        interval() passes over, taking each int, the step drawn from STEP_SHAPES and the form from FORMS; and a stop
        name so bound and to None, taking each int and None, in a form and with a step drawn from NONE_FORMS, with the
        exceptions a stop left empty beside a step other than 1 raises. Then, per relation, a start and a stop written
        as a number // a divisor name, and as the interval's lowest value plus an unknown % a divisor name, the name
        bound to two positive ints, two negative ones and half the time 0 (for %, the interval's width and its negative
        too), and half the time by a call, taking CPython's quotient by each int but 0, or its remainder of seeded
        values by each; each such case also writes a dict whose port is a number // random.randint(1, 0), a reversed
        divisor across 0, which the census must read without raising. Last, per relation, a start and a stop written
        with each operator the census reads beyond + - * // and % and the unary minus and plus (**, <<, >>, &, |, ^, ~,
        not, a conditional expression and a :=), over an operand written as an interval's text, taking the value
        Python's own operator gives at each end of that interval and at a seeded value between. Last, per relation, a
        start and a stop written as int() of a constant (by turns a digit string, one with spaces, a float with a
        fraction, bytes, and a digit string with a separator), taking CPython's int() of it; and, per relation, in a
        call written as the right operand of 0 + random.randrange(...), in a form with no ** mapping, twice a step name
        bound to an int (positive, then negative) and by a call, taking STEPS as _mixed()'s step names do, and once a
        step name bound to an int and to it negated as a float, every binding recorded, taking both (CPython 3.10 and
        3.11 take the float as a step; later ones raise TypeError). Last, per relation, a start and a stop written as B
        + O % the interval's width, B bound to the interval's lowest value and O to an int, each by a call too, taking
        B's int (THE RULE reads a start or stop by its recorded ints) plus O % the width for O's int, 0, the width less
        one and a seeded value no binding gives, which THE RULE reads with B by its int and O unbounded."""
        rng, out = random.Random(self.SEED + 4), []

        def near():
            return rng.choice((LOW + rng.randint(-60, 60), HIGH + rng.randint(-60, 60), rng.randint(LOW + 100, HIGH - 100),
                               rng.randint(1024, LOW - 200)))
        for relation in self.RELATIONS:
            for role, kind in (("start", "a string"), ("start", "a float"), ("stop", "a string"), ("stop", "a float"),
                               ("stop", "None")):
                s, e = self._shape(relation, near(), rng)
                iv, name = (s if role == "start" else e), "X%s%d" % ({"start": "S", "stop": "E"}[role], len(out))
                v = rng.randint(*iv)
                ints = sorted({v - 1000, v, v + 1000, iv[0], iv[1], rng.randint(*iv)})
                pre = ["%s = %d" % (name, x) for x in ints]
                pre.insert(rng.randint(0, len(pre)), "%s = %s" % (name, {"a string": '"x"', "a float": "%d.5" % v,
                                                                          "None": "None"}[kind]))
                takes = ints + ([None] if kind == "None" else [])
                if kind == "None":
                    form, k = rng.choice(self.NONE_FORMS)
                    step, how = (k, None if k is None else [ast.literal_eval(k)]), {"raises": (ValueError, TypeError)}
                else:
                    form, step, how = rng.choice(self.FORMS), rng.choice(self.STEP_SHAPES), {}
                out.append(("the %s, bound to several ints and to %s, every binding recorded" % (role, kind),
                            takes if role == "start" else s, e if role == "start" else takes, step, form,
                            dict(how, pre=pre, **{role: name})))
        for relation in self.RELATIONS:
            for role, kind in (("start", "//"), ("stop", "//"), ("start", "%"), ("stop", "%")):
                s, e = self._shape(relation, near(), rng)
                (lo, hi), name = (s if role == "start" else e), "XD%d" % len(out)
                k = rng.randint(1, 4)
                ks = sorted({k, k + 1, -rng.randint(1, 3), -rng.randint(4, 9)} | ({0} if rng.random() < 0.5 else set()))
                if kind == "//":
                    m = rng.randint(lo, hi) * k
                    written, takes = "%d // %s" % (m, name), sorted({m // x for x in ks if x})
                else:
                    w = hi - lo + 1
                    ks = sorted({w, -w} | set(ks))
                    ps = (0, 1, w - 1, rng.randint(0, 10 ** 6), rng.randint(-10 ** 6, 0))
                    written, takes = "%d + os.getpid() %% %s" % (lo, name), sorted({lo + p % x for x in ks if x for p in ps})
                pre = ["%s = %d" % (name, x) for x in ks] + (["%s = f()" % name] if rng.random() < 0.5 else [])
                pre.append("XZ%d = {\"port\": %d // random.randint(1, 0)}" % (len(out), rng.randint(LOW, HIGH)))
                out.append(("the %s, %s by a divisor name bound to ints of both signs" % (role, kind),
                            takes if role == "start" else s, e if role == "start" else takes, rng.choice(self.STEP_SHAPES),
                            rng.choice(self.FORMS), {"pre": pre, role: written}))

        def ends(iv):
            return sorted({iv[0], iv[1], rng.randint(*iv)})
        for relation in self.RELATIONS:
            for role in ("start", "stop"):
                for op in ("**", "<<", ">>", "&", "|", "^", "~", "not", "if", ":="):
                    s, e = self._shape(relation, near(), rng)
                    (lo, hi), n = (s if role == "start" else e), len(out)
                    if op == "**":
                        base = (int(lo ** 0.5), int(hi ** 0.5) + 1)
                        written = "(%s) ** (%s)" % (self._text(base), self._text((1, 2)))
                        takes = {x ** y for x in ends(base) for y in (1, 2)}
                    elif op in ("<<", ">>"):
                        k = rng.randint(1, 3)
                        operand = (lo >> k, (hi >> k) + 1) if op == "<<" else (lo << k, (hi << k) + rng.randint(0, 3))
                        written = "(%s) %s %d" % (self._text(operand), op, k)
                        takes = {x << k if op == "<<" else x >> k for x in ends(operand)}
                    elif op in ("&", "|", "^"):
                        m = rng.choice((rng.randint(0, 7), rng.randint(hi, 2 * hi), 2 ** 16 - 1))
                        written = "(%s) %s %d" % (self._text((lo, hi)), op, m)
                        takes = {{"&": x & m, "|": x | m, "^": x ^ m}[op] for x in ends((lo, hi))}
                    elif op == "~":
                        operand = (-hi - 1, -lo - 1)
                        written, takes = "~(%s)" % self._text(operand), {~x for x in ends(operand)}
                    elif op == "not":
                        written = "%s + (not XN%d)" % (self._text((lo, hi)), n)
                        takes = {x + b for x in ends((lo, hi)) for b in (0, 1)}
                    elif op == "if":
                        other = rng.randint(lo, hi)
                        written = "(%d if XC%d else %s)" % (other, n, self._text((lo, hi)))
                        takes = {other} | set(ends((lo, hi)))
                    else:
                        written, takes = "(XW%d := %s)" % (n, self._text((lo, hi))), set(ends((lo, hi)))
                    out.append(("the %s, written with %s" % (role, op), sorted(takes) if role == "start" else s,
                                e if role == "start" else sorted(takes), rng.choice(self.STEP_SHAPES),
                                rng.choice(self.FORMS), {role: written}))
        for relation in self.RELATIONS:
            for role in ("start", "stop"):
                s, e = self._shape(relation, near(), rng)
                v = rng.randint(*(s if role == "start" else e))
                text = ('"%d"' % v, '" %d "' % v, "%d.5" % v, 'b"%d"' % v, '"%s"' % _sep(v))[len(out) % 5]
                out.append(("the %s, int() of a constant" % role, [int(ast.literal_eval(text))] if role == "start" else s,
                            e if role == "start" else [int(ast.literal_eval(text))], rng.choice(self.STEP_SHAPES),
                            rng.choice(self.FORMS), {role: "int(%s)" % text}))
        unmapped = tuple(f for f in self.FORMS if not any(p.startswith("**") for p in f))
        for relation in self.RELATIONS:
            for sign in (1, -1):
                s, e = self._shape(relation, near(), rng)
                name, v = "XK%d" % len(out), sign * rng.choice((1, 7))
                out.append(("a step name with a binding the census does not record, the call the right operand of a sum",
                            s, e, (name, sorted(set(self.STEPS) | {v})), rng.choice(unmapped),
                            {"pre": ["%s = %d" % (name, v), "%s = f()" % name], "callee": "0 + random.randrange("}))
            s, e = self._shape(relation, near(), rng)
            name, v = "XF%d" % len(out), rng.choice((1, 7))
            out.append(("a step name bound to an int and to it negated as a float, the call the right operand of a sum",
                        s, e, (name, [v, -float(v)]), rng.choice(unmapped),
                        {"pre": ["%s = %d" % (name, v), "%s = -%d.0" % (name, v)], "callee": "0 + random.randrange(",
                         "raises": (ValueError, TypeError)}))
        for relation in self.RELATIONS:
            for role in ("start", "stop"):
                s, e = self._shape(relation, near(), rng)
                (lo, hi), n = (s if role == "start" else e), len(out)
                w, v = hi - lo + 1, rng.randint(0, 5000)
                takes = sorted({lo + k % w for k in (v, 0, w - 1, rng.randint(-10 ** 6, 10 ** 6))})
                out.append(("the %s, a sum on %% by a constant of two names, each with a binding the census does not record"
                            % role, takes if role == "start" else s, e if role == "start" else takes,
                            rng.choice(self.STEP_SHAPES), rng.choice(self.FORMS),
                            {"pre": ["XB%d = %d" % (n, lo), "XB%d = g()" % n, "XO%d = %d" % (n, v), "XO%d = f()" % n],
                             role: "XB%d + XO%d %% %d" % (n, n, w)}))
        return out

    def test_every_value_cpython_returns_lies_in_the_span_the_census_reports(self):
        """A seeded generator writes randrange calls: start's interval below stop's, above it, touching it from either
        side, one value with it, and overlapping it four ways, crossed with STEP_SHAPES (steps known positive, known
        negative, of either sign, from -5 to 0 and from 0 to 5, of 0, unbounded, a unary minus among them, and a step
        left out) and with FORMS (every argument by position, the step by keyword, the stop and the step, all three in
        another order, and the step in a ** mapping after start and stop by position or between them by keyword, a
        mapping that is empty when the step is left out; no call gives a mapping beside an empty stop, which THE RULE
        does not read), each twice about a value drawn near 32768, near 65535, inside the range or below it; and the
        two calls CPython showed 1e04b89f8 missed, and the one with a mapping that 7d1bdcda6 missed. After that grid
        come the spellings _grown() writes: step names bound to signed numbers, names bound to negative numbers in a
        start or stop, a unary plus, the call spelled on the class, a bool start or stop, and a stop written as None.
        Then come the bindings _mixed() writes: a name bound to ints the census records and also by each binding form it
        does not record, and a name Python mangles in a class, as the step, the start or the stop; then those
        _recorded() writes: a name every binding of which the census records, bound to several ints, as the step, the
        start or the stop, a start or stop under % by a constant of a name with a binding the census does not record, a
        stop name bound to None, a start or stop that is int() of a name bound to strings and floats, and a private name
        read in a method, bound under the spelling its class mangles it to; and last those _checked() writes: a start or
        stop name every binding of which the census records, bound to several ints and to a string, a float or None, a
        start or stop that is a number // a divisor name, or a sum on an unknown % one, the name bound to ints of both
        signs, a start or stop written with each operator the census reads beyond + - * // and % and the unary minus and
        plus, a start or stop that is int() of a constant, and a step name with a binding the census does not record, or
        bound to an int and to a float, in a call that is a sum's right operand, and a start or stop that sums two names
        with such a binding. The census reads them as one module, each call on a line of its own after the lines that
        bind its names (in the class's body or a method where the call reads the name there). For each call the test
        samples start and stop at each end of their intervals and at a seeded value between (or each value they take),
        and the step at each end, a seeded value between, and -1, 0 and 1 where the step can take them (an unbounded
        step takes STEPS, a step name each value it is bound to), and runs CPython's Random.randrange, the function
        random.randrange is bound to, three times: with its draw pinned to the lowest and to the highest
        (_RandrangeEnds), and with a seeded draw. Every value returned must lie in a span the census reports (every
        reading of the call, before the census keeps one per place: a call that reads names with a binding the census
        does not record has one for each mix of reading each by its recorded ints or unbounded), and where the census
        reports nothing no value may lie in the range. That holds for a start or stop name with a binding the census
        does not record too: it takes the ints its recorded bindings give, and THE RULE reads them, and under % by a
        constant it takes any value, which THE RULE reads with the name unbounded. The failure names the calls outside
        by shape, with the first of each."""
        rng = random.Random(self.SEED)
        cases = [("overlapping, start higher", (30000, 32999), (20000, 30999), ("0 - 7", (-7, -7)), (), {}),
                 ("start's lowest value stop's highest", (30000, 34999), (30000, 30000), ("0 - 7", (-7, -7)), (), {}),
                 ("start's lowest value stop's highest", (30000, 34999), (30000, 30000), ("0 - 7", (-7, -7)), ("**step",),
                  {})]
        for relation in self.RELATIONS:
            for step in self.STEP_SHAPES:
                for form in self.FORMS:
                    for _ in range(2):
                        c = rng.choice((LOW + rng.randint(-60, 60), HIGH + rng.randint(-60, 60),
                                        rng.randint(LOW + 100, HIGH - 100), rng.randint(1024, LOW - 200)))
                        cases.append((relation,) + self._shape(relation, c, rng) + (step, form, {}))
        cases += self._grown() + self._mixed() + self._recorded() + self._checked()

        def written(p, x):
            return "%s=%s" % (p, x) if p[0] != "*" else "**{%s}" % ("" if x is None else '"%s": %s' % (p[2:], x))
        lines, line_of = [], {}
        for n, (_label, s, e, (k, _kiv), form, how) in enumerate(cases, 1):
            args = dict(start=how["start"] if "start" in how else self._text(s),
                        stop=how["stop"] if "stop" in how else self._text(e), **({"step": k} if k is not None else {}))
            pos, kw = self._call(form, args)
            lines += [b + "\n" for b in how.get("pre", ())]
            lines.append("%sport = %s%s)\n" % (" " * how.get("indent", 0), how.get("callee", "random.randrange("),
                                               ", ".join(pos + [written(p, x) for p, x in kw])))
            line_of[n] = len(lines)
        case_at = {line: n for n, line in line_of.items()}
        reading = {}                                # every reading of a call, before the census keeps one per place
        sc = _Scan({}, {}, lambda x, end=False: getattr(x, "end_lineno" if end else "lineno", 1) or 1, 0)
        sc.scan(ast.parse("".join(lines)))
        for line, _v, why in sc.hits:
            self.assertIn(line, case_at, "a hit on a line that writes no call: %s" % why)
            m = re.search(r"computed into (-?\d+)-(-?\d+)$", why)
            reading.setdefault(case_at[line], []).append((int(m.group(1)), int(m.group(2))) if m else why)

        def between(iv):
            return sorted({iv[0], iv[1], rng.randint(*iv)})
        low, high, seeded = _RandrangeEnds(), _RandrangeEnds(), random.Random(self.SEED)
        high.top = True
        failures, bad, reached, returned = {}, set(), set(), 0
        for n, (label, s, e, (k, kiv), form, how) in enumerate(cases, 1):
            got = reading.get(n)
            said = "nothing" if got is None else " and ".join("%d-%d" % r if isinstance(r, tuple) else r for r in got)
            ks = self.STEPS if kiv is None else (kiv if isinstance(kiv, list) else
                                                 sorted(set(between(kiv)) | {x for x in (-1, 0, 1) if kiv[0] <= x <= kiv[1]}))
            randrange = how.get("cls", random.Random).randrange
            for a in (between(s) if isinstance(s, tuple) else s):
                for b in (between(e) if isinstance(e, tuple) else e):
                    for step in (ks if k is not None else (None,)):
                        pos, kw = self._call(form, dict(start=a, stop=b, **({"step": step} if k is not None else {})))
                        for draw in (low, high, seeded):
                            try:
                                v = randrange(draw, *pos, **{p.lstrip("*"): x for p, x in kw if x is not None})
                            except how.get("raises", ValueError):
                                continue
                            returned += 1
                            if LOW <= v <= HIGH:
                                reached |= {label} | (set() if how else {k})
                            if (got is None and LOW <= v <= HIGH) or (got is not None and not any(
                                    isinstance(r, tuple) and r[0] <= v <= r[1] for r in got)):
                                bad.add(n)
                                failures.setdefault(label, []).append(
                                    "line %d, %s: start %s, stop %s, step %s returned %d; the census reads %s"
                                    % (line_of[n], lines[line_of[n] - 1].strip(), a, b, step, v, said))
        if failures:
            self.fail("%d values from %d of %d calls lie outside the census's reading. By shape, the calls outside and "
                      "the first value:\n%s" % (sum(map(len, failures.values())), len(bad), len(cases), "\n".join(
                          "  %s: %d calls; %s" % (label, len({c for c in bad if cases[c - 1][0] == label}), got[0])
                          for label, got in failures.items())))
        self.assertGreater(returned, 0)
        self.assertEqual(sorted(set(self.RELATIONS) - {"start and stop one value"} - reached), [],
                         "a relation with no call that returned a value in the range: the test proves nothing there")
        self.assertEqual(sorted({k for k, _ in self.STEP_SHAPES} - {"0"} - reached, key=str), [],
                         "a step with no call that returned a value in the range: the test proves nothing there")
        self.assertEqual(sorted({c[0] for c in cases if c[5]} - reached), [],
                         "a spelling with no call that returned a value in the range: the test proves nothing there")


class BindingForms(unittest.TestCase):
    """BINDING_FIELDS against Python's own grammar, the node classes of the running interpreter's ast."""

    def test_every_field_that_can_hold_a_name_is_classified(self):
        """Every field of the running interpreter's ast node classes whose declared type can hold a string (an
        identifier, an optional one or a list of them, a string, or a constant) is in BINDING_FIELDS, so the table is
        the grammar's and not a remembered list. Field types are declared from 3.13 on (_field_types), and CI's 3.13
        cell runs this; Constant's deprecated aliases, which ast.parse never produces, are aside. On every
        interpreter each entry names a node class this one lacks (TypeVar before 3.12, Interpolation before 3.14) or a
        field among that class's _fields, so no entry is misspelled."""
        def subclasses(c):
            for s in c.__subclasses__():
                yield s
                yield from subclasses(s)
        nodes = {c for c in subclasses(ast.AST) if c.__module__ == "ast"}
        typed = [c for c in nodes if hasattr(c, "_field_types") and not (issubclass(c, ast.Constant) and c is not ast.Constant)]
        if sys.version_info >= (3, 13):
            self.assertGreater(len(typed), 100, "3.13 and later declare each node class's field types")
        held = sorted((c.__name__, f) for c in typed for f, t in c._field_types.items()
                      if t is str or t is object or str in getattr(t, "__args__", ()))
        self.assertEqual([x for x in held if x not in BINDING_FIELDS], [], "a field that can hold a name, not classified")
        by_name = {c.__name__: c for c in nodes}
        for cls, field in BINDING_FIELDS:
            if cls in by_name:
                self.assertIn(field, by_name[cls]._fields, "BINDING_FIELDS names %s.%s" % (cls, field))


def _subclasses(c):
    for s in c.__subclasses__():
        yield s
        yield from _subclasses(s)


class Operators(unittest.TestCase):
    """THE RULE's operators against the running interpreter's grammar and its own arithmetic (the owner's call of
    2026-10-05 on fork PR 973: interval() reads the operators as one closed class)."""

    def test_every_operator_is_read_or_named_as_one_not_read(self):
        """Each operator class of the running interpreter's ast, binary (ast.operator's subclasses) and unary
        (ast.unaryop's), is in exactly one of BINARY or UNARY, the operators interval() reads, and OPERATOR_LIMITS, the
        ones it names as not read, with the reason; so an operator a later Python adds fails here until the census
        reads it or names it. Each key of the three is such a class, so none is misspelled or stale."""
        for base, read in ((ast.operator, BINARY), (ast.unaryop, UNARY)):
            ops = set(_subclasses(base))
            self.assertGreater(len(ops), 3, "the grammar's %s classes were found" % base.__name__)
            for op in sorted(ops, key=lambda c: c.__name__):
                with self.subTest(op.__name__):
                    self.assertEqual((op in read) + (op in OPERATOR_LIMITS), 1,
                                     "%s: read by interval() and named as not read, or neither" % op.__name__)
            self.assertEqual(sorted(c.__name__ for c in set(read) - ops), [], "a key that is no %s" % base.__name__)
        self.assertEqual(sorted(c.__name__ for c in set(OPERATOR_LIMITS) - set(_subclasses(ast.operator))
                                - set(_subclasses(ast.unaryop))), [], "an OPERATOR_LIMITS key that is no operator")

    def test_each_operator_read_holds_every_value_python_computes(self):
        """For each operator of BINARY and UNARY, over operands drawn from a pool of intervals (one value or several;
        negative, with 0 at an end, across 0, positive, in the range), interval() reads names bound to each operand's
        ends, and every int Python's own operator computes over values at those ends, between them and at -1, 0 and 1
        where the operand holds them, lies in its reading. Where it gives no reading, the operands are one THE RULE
        leaves out: an operand that can be negative under **, <<, >>, &, | or ^, a divisor that is 0 alone, or a ** or
        << whose value can pass 2**BIG. not reads 0 to 1 over an operand interval() does not bound too."""
        rng = random.Random(973)
        pool = ((0, 0), (1, 1), (7, 7), (-7, -7), (0, 1), (0, 5), (-5, 0), (-3, 4), (2, 9), (-9, -2), (15, 17),
                (40000, 40100), (65530, 65540), (-65540, -65530))

        def values(iv):
            return sorted({iv[0], iv[1], rng.randint(*iv)} | {x for x in (-1, 0, 1) if iv[0] <= x <= iv[1]})

        def bound(**ivs):
            return {k: [ast.Constant(iv[0]), ast.Constant(iv[1])] for k, iv in ivs.items()}

        def too_big(op, b, d):
            if isinstance(op, ast.Pow):
                return b >= 2 and (d * (b.bit_length() - 1) > BIG or b ** d > 2 ** BIG)
            return isinstance(op, ast.LShift) and b > 0 and (b.bit_length() + d > BIG + 1 or b << d > 2 ** BIG)
        outside, unread = [], []
        for cls in sorted(BINARY, key=lambda c: c.__name__):
            for left in pool:
                for right in pool:
                    node = ast.BinOp(ast.Name("A", ast.Load()), cls(), ast.Name("B", ast.Load()))
                    got = interval(node, bound(A=left, B=right))
                    if got is None:
                        limit = right == (0, 0) if cls in (ast.FloorDiv, ast.Mod) else \
                            cls not in (ast.Add, ast.Sub, ast.Mult) and (min(left + right) < 0
                                                                        or too_big(cls(), left[1], right[1]))
                        if not limit:
                            unread.append("%s %s %s" % (left, cls.__name__, right))
                        continue
                    code = compile(ast.fix_missing_locations(ast.Expression(node)), "<operator>", "eval")
                    for x in values(left):
                        for y in values(right):
                            try:
                                v = eval(code, {"A": x, "B": y})
                            except (ZeroDivisionError, ValueError):
                                continue
                            if isinstance(v, int) and not got[0] <= v <= got[1]:
                                outside.append("%d %s %d is %d, outside %d-%d" % (x, cls.__name__, y, v, got[0], got[1]))
        for cls in sorted(UNARY, key=lambda c: c.__name__):
            for operand in pool:
                node = ast.UnaryOp(cls(), ast.Name("A", ast.Load()))
                got = interval(node, bound(A=operand))
                code = compile(ast.fix_missing_locations(ast.Expression(node)), "<operator>", "eval")
                for x in values(operand):
                    v = eval(code, {"A": x})
                    if got is None or not got[0] <= v <= got[1]:
                        outside.append("%s %d is %d, outside %r" % (cls.__name__, x, v, got))
        self.assertEqual(outside, [], "a value Python computes outside interval()'s reading")
        self.assertEqual(unread, [], "operands THE RULE reads, not read")
        self.assertEqual(interval(ast.parse("not f()", mode="eval").body), (0, 1, True))


class SentinelPorts(unittest.TestCase):
    """THE SENTINELS: no number tests/test_hermetic_kernel_postal.py or tests/test_postal_fixed_port_belt.py writes as text
    a process could take for a port falls in a bind band, and every kind of band is found in the tree."""

    @classmethod
    def setUpClass(cls):
        cls.bands = parse_cache.derived("ephemeral_port_bind_bands", lambda: bind_bands(ROOT))

    def test_no_sentinel_falls_in_a_bind_band(self):
        faults = sentinel_faults(ROOT, self.bands)
        if faults:
            self.fail("%d number(s) written as a port by the sentinel modules fall in a band a test binds, so a bus that "
                      "reads one could bind inside another suite's band. Use a port below 1024 that no band holds (7, 8 and 9 "
                      "are the sentinels); this module's docstring, THE SENTINELS, says how the bands are derived:\n%s"
                      % (len(faults), "\n".join("  %s:%d: %d, %s, inside %s (%d-%d)" % f for f in faults)))

    def test_every_kind_of_band_and_each_sentinel_module_is_found(self):
        kinds = {where for _lo, _hi, where in self.bands}
        for where in ("the ephemeral range", os.path.join("tests", "romp-postal.bats") + ": a per-test base",
                      os.path.join("tests", "free-port.bash") + ": a draw", os.path.join("tests", "manager-ports.js") + ": a block"):
            self.assertIn(where, kinds, "a band of this kind is derived from the tree")
        for rel in SENTINEL_MODULES:
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                values = {v for _l, v, _w in sentinel_values(fh.read())}
            self.assertTrue(values - {0, 1}, "%s writes numbers the pin reads, beyond the floors' 0 and 1" % rel)


class SentinelPlants(unittest.TestCase):
    """Each band shape THE BIND BANDS names is read from a planted file, and each way sentinel_values() reads a number is
    red inside a band and green below 1024."""
    B, STEP, OFFSET = 26000, 100, 300             # a planted per-test base, a helper's retry step, a test's offset

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        os.makedirs(os.path.join(self.d, "tests"))

    def _write(self, rel, text):
        """`text` at `rel` under the scratch root, by a rename-over (Plants._write says why)."""
        p = os.path.join(self.d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p + ".new", "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(p + ".new", p)

    def _shell(self):
        """A bats file whose two tests each take B plus their number, through a helper that retries STEP higher as many
        times as its callers ask (twice), and one of whose tests offsets the port by OFFSET and spawns there."""
        return ('setup() {\n'
                '    export ROMP_POSTAL_PORT=$((%d + ${BATS_TEST_NUMBER:-0}))\n'
                '    spawn "$ROMP_POSTAL_PORT" 2\n'
                '}\n\n'
                'spawn() {\n'
                '    local port=$1 tries=${2:-1} try=0\n'
                '    export ROMP_POSTAL_PORT=$((port + try * %d))\n'
                '}\n\n'
                '@test "a" {\n'
                '    local squat=$((ROMP_POSTAL_PORT + %d))\n'
                '    spawn "$squat" 2\n'
                '}\n\n'
                '@test "b" {\n'
                '    :\n'
                '}\n') % (self.B, self.STEP, self.OFFSET)

    def _bands(self):
        return sorted((lo, hi) for lo, hi, where in bind_bands(self.d) if where != "the ephemeral range")

    def test_each_band_shape_is_read(self):
        b, s, o = self.B, self.STEP, self.OFFSET
        draw = "random.randint(%d, %d)"                                   # a template, so this file holds no such call
        kw = ("random.randint(a=%d, b=%d)", "random.randint(b=%d, a=%d)", "random.randint(%d, b=%d)")   # by keyword
        cases = (
            ("a per-test base with its offset and its retry steps", "romp-x.bats", self._shell(),
             [(b + x + y, b + 2 + x + y) for x in (0, o) for y in (0, s)]),
            ("a draw in a shell file", "free-x.bash", "p = %s\nq = %s\n" % (draw % (b - 5000, b - 4001), draw % (0, 99)),
             [(b - 5000, b - 4001)]),
            ("a draw in Python, a call and not a string", "helper_x.py",
             "import random\nP = %s\nDOC = %r\n" % (draw % (b - 4000, b - 3901), draw % (b - 3000, b - 2901)), [(b - 4000, b - 3901)]),
            ("a draw in Python by keyword, read as THE RULE reads a random call", "helper_y.py",
             "import random\nP = %s\nQ = %s\nR = %s\nLOW = %s\nHALF = %s\nREP = %s\n"
             % (kw[0] % (b - 2000, b - 1901), kw[1] % (b - 901, b - 1000), kw[2] % (b - 6000, b - 5901),
                kw[0] % (10, 99), "random.randint(b=%d)" % (b - 7000), "random.randint(%d, %d, a=1)" % (b - 8000, b - 7901)),
             [(b - 2000, b - 1901), (b - 1000, b - 901), (b - 6000, b - 5901)]),
            ("a draw in Python on a name or attribute called Random or SystemRandom, its first argument the instance",
             "helper_z.py",
             "import random\nP = random.Random.randint(rng, %d, %d)\n"
             "Random = random.Random()\nQ = Random.randint(%d, %d)\nR = cfg.SystemRandom.randint(%d, %d)\n"
             % (b - 9000, b - 8901, b - 10000, b - 9901, b - 11000, b - 10901),
             [(b - 9000, b - 8901)]),
            ("a block keyed by a test file's name", "ports-x.js", "const RANGES = {\n  'a.test.js': [%d, %d],\n};\n" % (b - 13000, b - 12489),
             [(b - 13000, b - 12489)]))
        for label, name, text, want in cases:
            with self.subTest(label):
                self._write(os.path.join("tests", name), text)
                got = self._bands()
                os.unlink(os.path.join(self.d, "tests", name))              # before the assertion, so a red case leaves no plant
                self.assertEqual(got, sorted(want), text)

    def test_a_sentinel_inside_a_band_is_red_and_one_below_1024_green(self):
        self._write(os.path.join("tests", "romp-x.bats"), self._shell())
        inside, above = self.B + 1, self.B + 3                            # a test's port; one past the last test's
        for rel in SENTINEL_MODULES:
            for label, tmpl, why in (
                    ("a quoted digit string", 'os.environ["ROMP_POSTAL_PORT"] = "%d"\n', "a quoted digit string"),
                    ("an escaped one inside code text", 'SRC = "os.environ[\\"ROMP_POSTAL_PORT\\"] = \\"%d\\""\n',
                     "a quoted digit string"),
                    ("a number after a loopback host", 'URL = "http://127.0.0.1:%d/v1/models"\n', "a number after a loopback host"),
                    ("an int assigned to a port-named name", '_km.BUS_PORT = %d\n', "an int assigned to a port-named name")):
                with self.subTest(rel=rel, shape=label):
                    self._write(rel, tmpl % inside)
                    faults = sentinel_faults(self.d, bind_bands(self.d), (rel,))
                    self.assertEqual([(f[2], f[3]) for f in faults], [(inside, why)], tmpl)
                    for v in (7, above):
                        self._write(rel, tmpl % v)
                        self.assertEqual(sentinel_faults(self.d, bind_bands(self.d), (rel,)), [], tmpl % v)


class HeaderBands(unittest.TestCase):
    """THE HEADER'S BANDS: every range tests/manager-ports.js's header lists among the bands other suites draw from lies
    below the ephemeral range and holds a band a test draws from, in the tree and in planted headers."""
    B = 21000                                     # a planted draw's low end, below the range

    def test_the_manager_ports_header_lists_only_bands_the_tree_draws_from(self):
        bands = parse_cache.derived("ephemeral_port_bind_bands", lambda: bind_bands(ROOT))
        faults = header_band_faults(ROOT, bands)
        if faults:
            self.fail("%s's header lists, among the bands other suites draw from, a range the tree does not have. This "
                      "pin reads that sentence only; the bands themselves are derived by bind_bands() (THE BIND BANDS, "
                      "in this module's docstring). Correct the header:\n%s" % (MANAGER_PORTS, "\n".join("  " + f for f in faults)))

    def _plant(self, ranges, sentence="It also sits under every band another suite on the same machine draws from"):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        os.makedirs(os.path.join(d, "tests"))
        with open(os.path.join(d, "tests", "free-x.bash"), "w", encoding="utf-8") as f:
            f.write("p = random.randint(%d, %d)\n" % (self.B, self.B + 999))
        with open(os.path.join(d, MANAGER_PORTS), "w", encoding="utf-8") as f:
            f.write("'use strict';\n// A header.\n//\n// %s: the bus's %d, %s (all in\n// tests/free-x.bash's header).\n"
                    "//\n// The table.\nconst RANGES = {\n  'a.test.js': [%d, %d],\n};\n"
                    % (sentence, self.B + 1500, ", ".join("%d-%d" % r for r in ranges), self.B - 9000, self.B - 8489))
        return header_band_faults(d, bind_bands(d))

    def test_a_planted_header(self):
        b = self.B
        self.assertEqual(self._plant([(b, b + 999), (b - 500, b + 1200)]), [], "ranges that hold the draw")
        for label, ranges, sentence, want in (
                ("a range that reaches the range", [(b, b + 999), (b, LOW + 7231)], None, "reaches the ephemeral range"),
                ("a range no test draws from", [(b, b + 999), (b + 2000, b + 2999)], None, "holds no band"),
                ("a range that holds only the file's own block", [(b - 9000, b - 8000)], None, "holds no band"),
                ("the sentence reworded", [(b, b + 999)], "Every other band is higher", "has no sentence")):
            with self.subTest(label):
                faults = self._plant(ranges, *([sentence] if sentence else []))
                self.assertEqual(len(faults), 1, faults)
                self.assertIn(want, faults[0])
        with self.subTest("no header file"):
            d = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, d, True)
            os.makedirs(os.path.join(d, "tests"))
            faults = header_band_faults(d, bind_bands(d))
            self.assertEqual(len(faults), 1, faults)
            self.assertIn("cannot be read", faults[0])


if __name__ == "__main__":
    unittest.main()

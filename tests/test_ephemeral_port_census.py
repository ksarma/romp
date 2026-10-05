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
comprehension over a display. Any other binding of the name (a call's result, a parameter, an import, B = A, 0 - 7) is
not seen, adding no value and taking none away (HOST = "127.0.0.1", then HOST = os.environ["H"], leaves HOST a host).
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
    a name in a loop's sequence, counts only through interval(), which reads a name bound to exactly one value, an int,
    written with or without a sign.
  An address is a loopback or wildcard host (127.0.0.1, localhost or 0.0.0.0 with no underscore and no character
  str.isalnum() accepts against either end; [::1]; [::]) or // and a run of word characters, dots and dashes, standing
  right before the colon, with spaces or tabs allowed on either side of the colon except in a %-template; in that run a
  %-template may also put %s, and an f-string, a format template or a concatenation a placeholder (a field, or an
  operand not read as text).
  For the f-string, format and concatenation rules the text must end at the colon and any spaces or tabs after it, so a
  newline after the colon ends the address ("http://127.0.0.1:" and a newline, then + str(N), is not read), and a NUL
  character the source writes is read as an ordinary character, never as a placeholder ("http://", a NUL and a colon,
  then + str(N), is not read).
  An expression counts when it is bounded and can reach the range: interval() bounds int constants, a name bound to
  exactly one value, an int, signed or not, and, over bounded operands, str() and int(), a unary minus or plus (-7,
  +7), + - and *, and // and % by a positive constant; it reads an unknown operand of % by a positive constant as 0 to
  the constant less one, and a call to randint(a, b), randrange(stop), randrange(start, stop[, step]) or randbelow(n)
  over bounded arguments (random's and secrets', by the callee's name; a randrange's step may be unbounded, below) as
  the values it can return, so 20000 + os.getpid() % 20000 is 20000-39999 and counts, and so does random.randint(40000,
  50000). A call Python always refuses can give a span whose ends are reversed (random.randint(50000, 40000) is
  50000-40000), and such a span counts when both its ends lie in the range. Each argument of one of these random calls
  is given by position or by its parameter's name (randint's a and b, randrange's start, stop and step, randbelow's
  exclusive_upper_bound; a keyword that names none is passed over), and the call is read by the arguments that fill its
  parameters from the first up to the first left empty: random.randint(a=40000, b=50000) counts as random.randint(40000,
  50000) does, randrange(start=S) reads as randrange(S), and neither randint(b=N) nor randrange(stop=E) is read. A **
  mapping names no parameter, yet can fill any parameter left empty: beside a randrange's start and stop, with its step
  left empty, it is read as a step interval() does not bound (below), and beside any other parameter left empty the call
  is not read, since what the call returns then depends on what the mapping holds (random.randrange(30000, **kw) returns
  values up to 29999 when kw is empty, and up to 49999 when kw holds a stop of 50000). Two shapes Python refuses for
  the way the arguments are passed are not read: a keyword that names a parameter a positional argument fills
  (random.randint(40000, 50000, a=1)), and a randrange whose stop is left empty and whose step is given
  (random.randrange(start=50000, step=7)), unless that step is the int 1 written there, randrange's default and the one
  step Python takes without a stop: random.randrange(start=50000, step=1) reads as randrange(50000), and with a step
  that is 1 only at run time (a name bound to 1) the call is not read. A stop written as None, randrange's own default,
  is a stop left empty, once a keyword that repeats it is refused: random.randrange(50000, None) and
  random.randrange(50000, None, 1) read as randrange(50000), while random.randrange(50000, None, 7) and
  random.randrange(40000, None, stop=50000), which Python refuses, are not read. A randrange(start, stop[, step]) whose
  start and stop are bounded is read by one rule, whether or not interval() bounds its step (a step left out is 1, and
  one a ** mapping can give is unbounded): a positive step returns values from start up to stop less one, a negative
  step values from stop plus one up to start, and a step of 0 raises. So, with start from s_lo to s_hi and stop from
  e_lo to e_hi, a step that is never negative is read as s_lo to e_hi - 1, any other step that is never positive as
  e_lo + 1 to s_hi, and every remaining step, one that can take either sign or one interval() does not bound, as the
  span holding both, min(s_lo, e_lo + 1) to max(s_hi, e_hi - 1). random.randrange(40000, 50000, k) is 40000-49999, by
  keyword too (random.randrange(40000, stop=50000, step=k)); random.randrange(50000, 40000, k) and
  random.randrange(50000, 40000, -7) are 40001-50000; random.randrange(40000 + os.getpid() % 61,
  40020 + os.getpid() % 21, k) is 40000-40060, and 40021-40060 with a step of -7; and
  random.randrange(30000 + os.getpid() % 5000, 30000, **kw) is 30000-34999 whatever kw holds, by keyword too
  (random.randrange(start=30000 + os.getpid() % 5000, stop=30000, **kw)). Each reading holds every value the
  call can return wherever every binding of each name in the call is one the census records (BOUND; WHAT IT CANNOT
  SEE gives a name that also has another), and can hold values it never returns (a step of 7 returns values 7 apart).
  Where Python refuses a call for every value its start, stop and step can take, the reading still stands, an over-read:
  a step of 0 is read with the steps that are never negative (random.randrange(40000, 50000, 0) is 40000-49999); a
  positive step from a start never below its stop, or a negative one from a start never above it, is read as a span with
  its ends reversed (random.randrange(50000, 40000, 7) is 50000-39999, and random.randrange(40000, 50000, -1) is
  50001-40000); and a start and stop that are one and the same value, with an unbounded step, read as that value
  (random.randrange(40000, 40000, k) is 40000-40000). RandrangeAgainstCPython checks this reading against CPython's own
  randrange over generated calls. A sum or difference with an unbounded operand counts when one of its operands alone
  is a constant expression (one interval() bounds with no unknown in it) whose value is in the range, found through
  str(), int() and a unary plus and down a chain of sums and differences: 40000 + i is built on 40000, and so is
  40000 * 1 + i (offset_base()); one with no such operand (base + i) is not read.
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
  (random.randrange(50000, **kw), random.randrange(start=50000, step=1, **kw)), a name bound to anything but one int,
  signed or not, inside a display that is the position's value or in a loop's sequence (P = "N", then {"ports": [P]};
  P bound to 1 and to N, then for host, port in (("h", P),)), an f-string ("127.0.0.1:" + f"{N}"), an unbounded
  expression with no constant operand of a sum or difference in the range (base + i, N * k), and a run-time
  substitution into code text (a template's __VALUE__ replaced at run time); a rule of its own may still read such a
  value where it is written;
  a name bound to one int the census records and also by a binding it does not record (K = 7, then K = f() or
  K *= -1), which interval() reads as that one int, so random.randrange(40000, 1000, K) is read as 40000-999 whatever
  else K holds;
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
  randint(A, B), and neither randint(b=B) nor randint(A, B, a=C), which Python refuses, is a draw), since every reader
  of a random call reads its arguments one way; or the text in a shell file, by position (the probe of
  tests/free-port.bash);
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


def interval(node, bound=None):
    """(lo, hi, computed) for an int expression the census can bound, else None: constants, a unary minus or plus,
    + - * // and % over them, a name bound to one int (signed or not), str() or int() around one, an unknown
    operand of % by a positive constant read as 0 to the constant less one, and randint(a, b), randrange(stop),
    randrange(start, stop[, step]) and randbelow(n) over bounded arguments read as the values each can return, each
    argument given by position or by its parameter's name (_random_args()). randrange(start, stop[, step]) is read by
    its step's sign, the step bounded or not (a step left out is 1, and one a ** mapping can give is unbounded): start's
    lowest value to stop's highest less one for a step that is never negative, stop's lowest plus one to start's highest
    for any other step that is never positive, and the span holding both for the rest, a step that can take either sign
    or one interval() does not bound (THE RULE). computed is True when an unknown took part."""
    bound = bound or {}
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value, node.value, False
    if isinstance(node, ast.Name) and len(bound.get(node.id, ())) == 1:
        lit = bound[node.id][0]
        if isinstance(lit, ast.Constant) and isinstance(lit.value, int) and not isinstance(lit.value, bool):
            return lit.value, lit.value, False
        return None
    if isinstance(node, ast.Call) and _callee(node.func) in ("str", "int") and len(node.args) == 1 and not node.keywords:
        return interval(node.args[0], bound)
    if isinstance(node, ast.Call) and _callee(node.func) in RANDOM_CALLS:
        ivs = [interval(a, bound) for a in _random_args(node) or ()]
        name, k = _callee(node.func), len(ivs)
        if name == "randrange" and k in (2, 3) and ivs[0] and ivs[1]:   # THE RULE's one reading, by the step's sign
            (a, b, _), (c, d, _) = ivs[:2]
            step = ivs[2] if k == 3 else (1, 1, False)
            if step and step[0] >= 0:               # never negative: from start up to stop less one (a step of 0 raises)
                return a, d - 1, True
            if step and step[1] <= 0:               # never positive: from stop plus one up to start
                return c + 1, b, True
            return min(a, c + 1), max(b, d - 1), True   # either sign, or unbounded: the span holding both
        if ivs and all(ivs):
            if name == "randint" and k == 2:
                return ivs[0][0], ivs[1][1], True
            if name in ("randrange", "randbelow") and k == 1:
                return 0, ivs[0][1] - 1, True
        return None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return interval(node.operand, bound)       # +7 is 7
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        operand = interval(node.operand, bound)
        return (-operand[1], -operand[0], operand[2]) if operand else None
    if isinstance(node, ast.BinOp):
        right = interval(node.right, bound)
        left = interval(node.left, bound)
        if isinstance(node.op, ast.Mod) and right and right[0] == right[1] and right[0] > 0 and left is None:
            return 0, right[0] - 1, True
        if left is None or right is None:
            return None
        (a, b, ca), (c, d, cb) = left, right
        if isinstance(node.op, ast.Add):
            return a + c, b + d, ca or cb
        if isinstance(node.op, ast.Sub):
            return a - d, b - c, ca or cb
        if isinstance(node.op, ast.Mult):
            ends = (a * c, a * d, b * c, b * d)
            return min(ends), max(ends), ca or cb
        if isinstance(node.op, (ast.FloorDiv, ast.Mod)) and c == d and c > 0:
            if isinstance(node.op, ast.FloorDiv):
                return a // c, b // c, ca or cb
            return (a % c, b % c, ca or cb) if a == b else (0, c - 1, ca or cb)
    return None


def _random_args(call):
    """The arguments of a random call (RANDOM_CALLS) in its parameters' order, up to the first parameter left empty: each
    positional argument in its place, then each keyword in the place of the parameter it names (randint(a=A, b=B) is
    randint(A, B)), a keyword that names no parameter passed over. A stop written as None, randrange's default, is a
    stop left empty, once a keyword that repeats it is refused. A ** mapping can fill any parameter left empty, at run
    time: beside a randrange's start and stop it fills the step, given as the keyword node that passes the mapping,
    which is no expression, so interval() never bounds it whatever the mapping holds; with any other parameter left
    empty beside it, None. None too when an argument is starred, the positional arguments outnumber the parameters, or
    Python refuses the call for the way its arguments are passed: a keyword names a parameter a positional argument
    fills, or a randrange's stop is left empty and its step is given as anything but the int 1 written there
    (randrange's default step, the one step Python takes without a stop)."""
    params = RANDOM_CALLS[_callee(call.func)]
    if len(call.args) > len(params) or any(isinstance(a, ast.Starred) for a in call.args):
        return None
    got, mapping = dict(zip(params, call.args)), None
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
    if step is not None and "stop" not in got \
            and not (isinstance(step, ast.Constant) and type(step.value) is int and step.value == 1):
        return None                                 # Python: Missing a non-None stop argument
    out = []
    for p in params:
        if p not in got:
            break
        out.append(got[p])
    return out


def offset_base(node, bound=None):
    """The constant in the range that a sum or difference with an unbounded operand is built on (40000 + i: 40000), read
    through str(), int() and a unary plus and down a chain of sums and differences; None when no constant operand alone
    is in the range."""
    if isinstance(node, ast.Call) and _callee(node.func) in ("str", "int") and len(node.args) == 1 and not node.keywords:
        return offset_base(node.args[0], bound)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return offset_base(node.operand, bound)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub)):
        for side in (node.left, node.right):
            iv = interval(side, bound)
            if iv and not iv[2] and in_range(iv[0]):
                return iv[0]
            got = offset_base(side, bound)
            if got is not None:
                return got
    return None


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
        else:
            iv = interval(node, self.bound)
            if iv and iv[2] and iv[0] <= HIGH and iv[1] >= LOW:
                self._record(node, max(iv[0], LOW), "%s, computed into %d-%d" % (why, iv[0], iv[1]))
            elif iv and not iv[2] and in_range(iv[0]):
                self._record(node, iv[0], why + ", a constant expression")
            elif iv is None:
                base = offset_base(node, self.bound)
                if base is not None:
                    self._record(node, base, "%s, an offset from %d" % (why, base))

    def _bind(self, t, v):
        if isinstance(t, ast.Name):
            if isinstance(v, (ast.Constant, ast.Tuple, ast.List, ast.Set)):
                self.bound.setdefault(t.id, []).append(v)
            elif _signed_number(v) is not None:     # -7 is a unary minus over 7: recorded as the number it computes
                self.bound.setdefault(t.id, []).append(ast.copy_location(ast.Constant(_signed_number(v)), v))
        elif isinstance(t, (ast.Tuple, ast.List)) and isinstance(v, (ast.Tuple, ast.List)) and len(t.elts) == len(v.elts):
            for te, ve in zip(t.elts, v.elts):
                self._bind(te, ve)

    def _value(self, v, why, strings=True):
        if isinstance(v, ast.Name) and v.id in self.bound:
            self.uses.append((v.id, why, strings))
        else:
            self.literal(v, why, strings)

    def scan(self, tree):
        docs = _docstrings(tree)
        self.bound, self.uses = {}, []
        self.imported, self.modules = self._imports(tree)
        for n in ast.walk(tree):
            if isinstance(n, (ast.Assign, ast.AnnAssign, ast.NamedExpr)) and n.value is not None:
                for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                    self._bind(t, n.value)
            elif isinstance(n, (ast.For, ast.AsyncFor, ast.comprehension)) and isinstance(n.iter, (ast.Tuple, ast.List, ast.Set)):
                for e in n.iter.elts:
                    self._bind(n.target, e)
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
            for lit in self.bound.get(name, ()):
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
                 "an offset from %d" % lo, lo)):
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
        given, by keyword or after a positional start (Python: Missing a non-None stop argument), and a keyword that
        repeats a positional argument (Python: got multiple values for argument), in each of the three calls. Python
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
        40001-40000. With an unbounded step, start and stop both 40000 read as 40000-40000. Python raises for every
        plant."""
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
                 lo)):
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
        +45001 holds 45001, read through the hop. WHAT IT CANNOT SEE lists a name bound to an int and by a binding the
        census does not record, with a green plant."""
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
                ("a name bound to an int and by a binding the census does not record", "test_x.py",
                 'K = 7\nK = f()\nport = random.randrange(%d, 1000, K)\nJ = 7\nJ *= -1\nport = random.randrange(%d, 1000, J)\n'
                 % (n, n)),
                ("an attribute", "test_x.py", 'cfg.p = %d\nrow = {"port": cfg.p}\n' % n),
                ("a name bound to a digit string, inside a display that is the position's value", "test_x.py",
                 'P = "%d"\nrow = {"ports": [P]}\n' % n),
                ("a name bound twice, in a loop's sequence", "test_x.py",
                 'P = 1\nP = %d\nfor host, port in (("h", P),):\n    pass\n' % n),
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
    2026-10-05 on fork PR 973: one rule, and a property test in place of one more plant per pass)."""

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

    def test_every_value_cpython_returns_lies_in_the_span_the_census_reports(self):
        """A seeded generator writes randrange calls: start's interval below stop's, above it, touching it from either
        side, one value with it, and overlapping it four ways, crossed with STEP_SHAPES (steps known positive, known
        negative, of either sign, from -5 to 0 and from 0 to 5, of 0, unbounded, a unary minus among them, and a step
        left out) and with FORMS (every argument by position, the step by keyword, the stop and the step, all three in
        another order, and the step in a ** mapping after start and stop by position or between them by keyword, a
        mapping that is empty when the step is left out; no call gives a mapping beside an empty stop, which THE RULE
        does not read), each twice about a value drawn near 32768, near 65535, inside the range or below it; and the
        two calls CPython showed 1e04b89f8 missed, and the one with a mapping that 7d1bdcda6 missed. The census reads
        them as one module, a call to a line. For each call the test samples start and stop at each end of their
        intervals and at a seeded value between, and the step at each end, a seeded value between, and -1, 0 and 1
        where the step can take them (an unbounded step takes STEPS), and runs CPython's Random.randrange, the function
        random.randrange is bound to, three times: with its draw pinned to the lowest and to the highest
        (_RandrangeEnds), and with a seeded draw. Every value returned must lie in the span the census reports, and
        where the census reports nothing no value may lie in the range."""
        rng = random.Random(self.SEED)
        cases = [("overlapping, start higher", (30000, 32999), (20000, 30999), ("0 - 7", (-7, -7)), ()),
                 ("start's lowest value stop's highest", (30000, 34999), (30000, 30000), ("0 - 7", (-7, -7)), ()),
                 ("start's lowest value stop's highest", (30000, 34999), (30000, 30000), ("0 - 7", (-7, -7)), ("**step",))]
        for relation in self.RELATIONS:
            for step in self.STEP_SHAPES:
                for form in self.FORMS:
                    for _ in range(2):
                        c = rng.choice((LOW + rng.randint(-60, 60), HIGH + rng.randint(-60, 60),
                                        rng.randint(LOW + 100, HIGH - 100), rng.randint(1024, LOW - 200)))
                        cases.append((relation,) + self._shape(relation, c, rng) + (step, form))

        def text(iv):
            return "%d" % iv[0] if iv[0] == iv[1] else "%d + os.getpid() %% %d" % (iv[0], iv[1] - iv[0] + 1)

        def written(p, x):
            return "%s=%s" % (p, x) if p[0] != "*" else "**{%s}" % ("" if x is None else '"%s": %s' % (p[2:], x))
        lines = []
        for _relation, s, e, (k, _kiv), form in cases:
            args = dict(start=text(s), stop=text(e), **({"step": k} if k is not None else {}))
            pos, kw = self._call(form, args)
            lines.append("port = random.randrange(%s)\n" % ", ".join(pos + [written(p, x) for p, x in kw]))
        reading = {}
        for line, _v, why in scan_python(ast.parse("".join(lines)), {}):
            m = re.search(r"computed into (-?\d+)-(-?\d+)$", why)
            reading[line] = (int(m.group(1)), int(m.group(2))) if m else why

        def between(iv):
            return sorted({iv[0], iv[1], rng.randint(*iv)})
        low, high, seeded = _RandrangeEnds(), _RandrangeEnds(), random.Random(self.SEED)
        high.top = True
        failures, bad, reached, returned = [], set(), set(), 0
        for n, (relation, s, e, (k, kiv), form) in enumerate(cases, 1):
            got = reading.get(n)
            said = "nothing" if got is None else ("%d-%d" % got if isinstance(got, tuple) else got)
            ks = self.STEPS if kiv is None else sorted(set(between(kiv)) | {x for x in (-1, 0, 1) if kiv[0] <= x <= kiv[1]})
            for a in between(s):
                for b in between(e):
                    for step in (ks if k is not None else (None,)):
                        pos, kw = self._call(form, dict(start=a, stop=b, **({"step": step} if k is not None else {})))
                        for draw in (low, high, seeded):
                            try:
                                v = draw.randrange(*pos, **{p.lstrip("*"): x for p, x in kw if x is not None})
                            except ValueError:
                                continue
                            returned += 1
                            if LOW <= v <= HIGH:
                                reached |= {relation, k}
                            if (got is None and LOW <= v <= HIGH) or (got is not None and not (
                                    isinstance(got, tuple) and got[0] <= v <= got[1])):
                                bad.add(n)
                                failures.append("line %d, %s: start %d, stop %d, step %s returned %d; the census reads %s"
                                                % (n, lines[n - 1].strip(), a, b, step, v, said))
        if failures:
            self.fail("%d values from %d of %d calls lie outside the census's reading; the first 8:\n%s"
                      % (len(failures), len(bad), len(cases), "\n".join(failures[:8])))
        self.assertGreater(returned, 0)
        self.assertEqual(sorted(set(self.RELATIONS) - {"start and stop one value"} - reached), [],
                         "a relation with no call that returned a value in the range: the test proves nothing there")
        self.assertEqual(sorted({k for k, _ in self.STEP_SHAPES} - {"0"} - reached, key=str), [],
                         "a step with no call that returned a value in the range: the test proves nothing there")


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

#!/usr/bin/env bats
# The shell surfaces run on a stock mac too: /bin/sh, and a /bin/bash at 3.2. The bats macOS cell runs on manual dispatch
# alone, so nothing in CI reads them under that bash; this pins the bash-4-plus constructs out of every shell script the
# repo ships (bin/, scripts/*.sh, install.sh, bootstrap.sh, hooks/*.sh, .githooks/pre-push, tools/, and the extension's
# install.sh and scripts/) statically instead (round four of issue 1600: a ${1,,} in romp-service's escape-hatch reader
# made the install die with a bad substitution after writing the plist and before bootstrapping the agent). Non-comment lines
# only, so a construct NAMED in a comment is fine; one named in a string is a hit, and the line is reworded. The patterns
# are bash-shaped on purpose: a Python heredoc inside a script writes [-1] and a nested ${a:-${b:-c}} default is not a
# negative-length substring, and neither may read as a hit.
#
# The same list also pins the FILE SCOPE of every tracked tests/*.bats file and of every tests/*.bash helper the files
# load. bats runs a file's file scope while it gathers the tests, before any test runs, so one bash-4 construct there
# fails the gather: the whole bats run then reports that one failure and no test result (2026-09-30: a declare -gA at
# file scope in tests/pre-push-hook.bats did this to the macOS cell). Inside a function or a @test body that nothing at
# file scope calls, a construct fails only the cases that run it, and those skip under an older bash. The exception is a
# construct bash 3.2 cannot parse (an extglob pattern inside [[ ]], [[ -v, |&, ;& or ;;&, &>>, coproc { ... }): it stops
# the whole file loading wherever it stands, and this pin does not look for it inside bodies (the same day, an extglob
# pattern in a case of tests/pre-push-hook.bats stopped that file loading once its file scope was fixed). _scope_scan
# reads each file's file scope and hands it to _scan. It follows a function or @test body by its braces, treats a
# heredoc's body as data wherever it stands, and drops comments and the inside of single-quoted strings, except for a
# printf time directive %(...)T, the one family that lives inside a quoted format. The reader checks itself: it must end
# each file outside every quote, heredoc and body, and open one @test body for each @test line bats reads; otherwise the
# pin fails and names the file. Its limits: a body in parentheses, f() ( ... ), reads as file scope (a false hit); a <<
# in arithmetic reads as a heredoc that never ends (a loud failure); a brace standing alone as a word (echo {) moves the
# brace count (a loud failure, unless a second such brace cancels it); a heredoc's body at file scope that runs as code
# (source /dev/stdin <<EOF) is not read; a single-quoted string at file scope that runs as code (eval '...', bash -c
# '...') is not read; and a function called at file scope runs its body while bats gathers, which the pin does not
# follow.

setup() {
    REPO="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"
    TEST_DIR="$(mktemp -d)"
}
teardown() { rm -rf "$TEST_DIR"; }

# One construct family per line: a name, a tab, an extended regex.
CONSTRUCTS='case modification, ${x,,} ${x^^} ${x,} ${x^} (bash 4)	\$\{[A-Za-z0-9_@*#?!-]+(\[[^]]*\])?[,^]
associative array, declare -A (bash 4)	(declare|local|typeset)[[:space:]]+-[A-Za-z]*A[A-Za-z]*([[:space:]]|$)
nameref, declare -n (bash 4.3)	(declare|local|typeset)[[:space:]]+-[A-Za-z]*n[A-Za-z]*([[:space:]]|$)
[[ -v var ]] (bash 4.2)	\[\[[^]]*[[:space:]]-v[[:space:]]
mapfile / readarray (bash 4)	(^|[^A-Za-z0-9_])(mapfile|readarray)([^A-Za-z0-9_]|$)
wait -n (bash 4.3)	(^|[^A-Za-z0-9_])wait[[:space:]]+-n([^A-Za-z0-9_]|$)
coproc (bash 4)	(^|[^A-Za-z0-9_])coproc([^A-Za-z0-9_]|$)
&> and &>> redirection (&>> is bash 4; neither is sh)	&>
;& and ;;& case fall-through (bash 4)	;&
|& pipe (bash 4)	\|&
${var@Q} transformation (bash 4.4)	\$\{[A-Za-z0-9_]+@[A-Za-z]
EPOCHSECONDS / EPOCHREALTIME (bash 5)	\$\{?EPOCH(SECONDS|REALTIME)
[ -v var ] and test -v (bash 4.2)	(^|[^A-Za-z0-9_])(\[|test)[[:space:]]+-v[[:space:]]
shopt -s globstar or lastpipe (bash 4, 4.2)	shopt[[:space:]]+-s[[:space:]]+[a-z ]*(globstar|lastpipe)
BASHPID (bash 4)	\$\{?BASHPID
declare -g (bash 4.2)	(declare|typeset)[[:space:]]+-[A-Za-z]*g[A-Za-z]*([[:space:]]|$)
negative array index, ${a[-1]} or a[-1]= (bash 4.3)	\$\{[A-Za-z_][A-Za-z0-9_]*\[-[0-9]+\]|(^|[^A-Za-z0-9_])[A-Za-z_][A-Za-z0-9_]*\[-[0-9]+\]=
printf %(...)T (bash 4.2)	printf[^|;&]*%\([^)]*\)T
read -N (bash 4.1)	(^|[^A-Za-z0-9_])read[[:space:]]+(-[a-zA-Z]*)?N[[:space:]]
exec {fd}< or {fd}> (bash 4.1)	exec[[:space:]]+\{[A-Za-z_][A-Za-z0-9_]*\}[<>]
negative-length substring ${var:off:-n} (bash 4.2)	\$\{[A-Za-z_][A-Za-z0-9_]*:[0-9]+:-[0-9]+\}
dollar-quote unicode escape (bash 4.2)	\$'"'"'[^'"'"']*\\[uU][0-9A-Fa-f]'

_shell_files() {   # the surfaces: every TRACKED shell script the repo ships, found by an sh or bash shebang on its first line. git
                   # ls-files, not a glob over the working tree: a stray file another test left under bin/ or tools/ cannot enter the
                   # set (the tagged tip's confirming macOS run stalled here for the job's whole 180 s per-test bound where the proof
                   # run took 3.3 s, with no shell file changed between them, 2026-09-16)
    local f
    git -C "$REPO" ls-files -z -- bin 'scripts/*.sh' install.sh bootstrap.sh 'hooks/*.sh' .githooks tools vscode-extension/install.sh vscode-extension/scripts 2>/dev/null \
        | tr '\0' '\n' | while IFS= read -r f; do
            [ -n "$f" ] && [ -f "$REPO/$f" ] || continue
            head -1 "$REPO/$f" | grep -qE '^#!.*(/|env )(ba)?sh([[:space:]]|$)' && echo "$REPO/$f"
        done
    return 0
}

_bounded_fn() {   # $1 seconds, $2 a function of this file, $@ its args: the function in a child bash under a bound of its own, so a
                  # stall in the list or the scan is cut and named by the pin, never left to the job's per-test bound. coreutils
                  # timeout where it exists (124 at the bound), else perl's alarm (the child dies to SIGALRM: 142), else unbounded.
    local secs="$1" fn="$2"; shift 2
    local body; body="$(declare -f _shell_files _scan _scope_files _scope_scan); $fn \"\$@\""
    if command -v timeout >/dev/null 2>&1; then
        REPO="$REPO" CONSTRUCTS="$CONSTRUCTS" timeout "$secs" bash -c "$body" _ "$@"
    elif command -v perl >/dev/null 2>&1; then
        REPO="$REPO" CONSTRUCTS="$CONSTRUCTS" perl -e 'alarm shift; exec @ARGV' "$secs" bash -c "$body" _ "$@"
    else
        REPO="$REPO" CONSTRUCTS="$CONSTRUCTS" bash -c "$body" _ "$@"
    fi
}

_scan() {   # $@ files: every non-comment line holding a construct, as "family: file:line:text". ONE grep per file with every
            # family's pattern joined, then the family named in this shell (bash's =~ is the same POSIX ERE grep -E reads): 22
            # families x 21 files x 2 greps was 924 processes, minutes on a slow macOS runner; this is 42.
    local name re f line n text all="" hit
    while IFS=$'\t' read -r name re; do
        [ -n "$name" ] || continue
        all="${all:+$all|}($re)"
    done <<< "$CONSTRUCTS"
    for f in "$@"; do
        while IFS= read -r line; do
            n="${line%%:*}"; text="${line#*:}"; hit=""
            while IFS=$'\t' read -r name re; do
                [ -n "$name" ] || continue
                if [[ "$text" =~ $re ]]; then printf '%s: %s:%s:%s\n' "$name" "${f#$REPO/}" "$n" "$text"; hit=1; fi
            done <<< "$CONSTRUCTS"
            [ -n "$hit" ] || printf '%s: %s:%s:%s\n' "unclassified construct" "${f#$REPO/}" "$n" "$text"   # grep saw it; still a hit
        done < <(grep -nE -- "$all" "$f" 2>/dev/null | grep -vE '^[0-9]+:[[:space:]]*#')
    done
    return 0
}

_scope_files() {   # the second population: every TRACKED tests/*.bats file, which CI's bats run gathers, and every tests/*.bash helper,
                   # which a file's load runs while it gathers; git ls-files for _shell_files' reason
    local f
    git -C "$REPO" ls-files -z -- 'tests/*.bats' 'tests/*.bash' 2>/dev/null | tr '\0' '\n' | while IFS= read -r f; do
        [ -n "$f" ] && [ -f "$REPO/$f" ] && echo "$REPO/$f"
    done
    return 0
}

_scope_scan() {   # $1 a directory, $@ files under REPO: each file's file scope written under the directory at its REPO path, one line
                  # per line of the file (the header's reading), and _scan's hits in it, "family: file:line:text". A file the reader
                  # loses its place in is named on stdout, with status 2, and no hit is read from it.
    local dir="$1" f rel want got rc=0; shift
    mkdir -p "$dir"
    cat > "$dir/scope.awk" <<'AWK'
# One output line per input line: the bytes of it outside every function body and @test body, with a comment dropped
# and the inside of a single-quoted string dropped but for any printf time directive in it. Contexts stack on st[]: code
# (the file's, or a $( ... ) substitution's begun inside double quotes, par[] counting its open parentheses; one begun in
# code is read as parentheses of the code around it), bq (a backquoted one, read as code),
# sq, ansi ($'...'), dq, and pe and peq (a ${...} begun outside or inside double quotes: it ends at its first unquoted },
# and a single quote quotes in the first alone). Braces count only as the reserved words, in code, on bt[]: f for a body,
# g for a group, which is file scope when it stands there.
function emit(x, m) { if (!infn) out = out x; pm = pm (m ? "" : x) }
function push(t) { st[++d] = t; par[d] = 0 }
function head(p) { return p ~ /(^|[;&|( \t])(function[ \t]+)?[^ \t;&|()<>{}]+[ \t]*\([ \t]*\)[ \t]*$/ || p ~ /(^|[;&|( \t])function[ \t]+[^ \t;&|()<>{}]+[ \t]*$/ }
function fmts(seg,   r) { r = ""; while (match(seg, /%\([^)]*\)T/)) { r = r substr(seg, RSTART, RLENGTH) " "; seg = substr(seg, RSTART + RLENGTH) }; return r }
BEGIN { d = 0; st[0] = "code"; par[0] = 0; b = 0; infn = 0; nh = 0; hi = 0; tests = 0; pend = 0; bad = "" }
{
    line = $0; n = length(line); out = ""; pm = ""
    if (hi) {                                                           # a heredoc's body, ended by its word (tabs stripped under <<-)
        t = line; if (hs[hi]) sub(/^\t+/, "", t)
        if (t == hq[hi]) { hi++; if (hi > nh) { hi = 0; nh = 0 } }
        print ""; next
    }
    i = 1; prev = " "
    while (i <= n) {
        c = substr(line, i, 1); s = st[d]
        if (s == "sq") {
            k = index(substr(line, i), "'")
            if (!k) { emit(fmts(substr(line, i)), 1); i = n + 1; break }
            emit(fmts(substr(line, i, k - 1)), 1); i += k; d--; emit("'"); prev = "'"; continue
        }
        if (s == "ansi") {
            if (c == "\\") { emit(substr(line, i, 2), 1); i += 2; continue }
            if (c == "'") d--
            emit(c, 1); i++; prev = c; continue
        }
        if (s == "dq" || s == "pe" || s == "peq") {
            if (c == "\\") { emit(substr(line, i, 2), 1); i += 2; continue }
            if (c == "\"") { if (s == "dq") d--; else push("dq"); emit(c); i++; prev = c; continue }
            if (c == "}" && s != "dq") { d--; emit(c); i++; prev = c; continue }
            if (c == "'" && s == "pe") { push("sq"); emit(c); i++; prev = c; continue }
            if (substr(line, i, 2) == "$(") { push("code"); emit("$("); i += 2; prev = "("; continue }
            if (substr(line, i, 2) == "${") { push(s == "dq" ? "peq" : s); emit("${"); i += 2; prev = "{"; continue }
            if (c == "`") { push("bq"); emit(c); i++; prev = c; continue }
            emit(c, 1); i++; prev = c; continue
        }
        if (!index("\\#`$'\"(){}<", c)) {                               # code: a run of bytes no branch below reads, copied whole
            k = match(substr(line, i + 1), /[\\#`$'"(){}<]/); k = k ? i + k : n + 1
            emit(substr(line, i, k - i)); prev = substr(line, k - 1, 1); i = k; continue
        }
        if (c == "\\") { emit(substr(line, i, 2)); i += 2; prev = "x"; continue }
        if (c == "#" && (i == 1 || prev ~ /[ \t;&|()]/)) break          # a comment, to the end of the line
        if (c == "`") { if (s == "bq") d--; else push("bq"); emit(c); i++; prev = c; continue }
        if (substr(line, i, 2) == "$'") { push("ansi"); emit("$'"); i += 2; prev = "'"; continue }
        if (c == "'") { push("sq"); emit(c); i++; prev = c; continue }
        if (c == "\"") { push("dq"); emit(c); i++; prev = c; continue }
        if (substr(line, i, 2) == "${") { push("pe"); emit("${"); i += 2; prev = "{"; continue }
        if (c == "(") { par[d]++; emit(c); i++; prev = c; continue }
        if (c == ")") { if (par[d] > 0) par[d]--; else if (d > 0 && s == "code") d--; emit(c); i++; prev = c; continue }
        if (c == "{" && (i == 1 || prev ~ /[ \t;&|()]/) && (i == n || substr(line, i + 1, 1) ~ /[ \t]/)) {   # the reserved word, not a brace inside a word ([{], {a,b}, {fd}>)
            if (!infn && (pm ~ /^[ \t]*@test[ \t]/ || head(pm) || (pend && pm ~ /^[ \t]*$/))) {
                if (pm ~ /^[ \t]*@test[ \t]/) { tests++; out = "" }       # a test's name becomes a function's name: no code here
                bt[++b] = "f"; infn++; pm = pm c; i++; prev = c; continue
            }
            bt[++b] = "g"; emit(c); i++; prev = c; continue
        }
        if (c == "}" && (i == 1 || prev ~ /[ \t;&|]/) && (i == n || substr(line, i + 1, 1) ~ /[ \t;&|)<>]/)) {
            if (!b) { if (bad == "") bad = "a } with no { open at line " NR; emit(c); i++; prev = c; continue }
            if (bt[b--] == "f") { infn--; pm = pm c; i++; prev = c; continue }
            emit(c); i++; prev = c; continue
        }
        if (c == "<" && substr(line, i, 2) == "<<") {                   # a heredoc: its word, quotes removed, ends a body from the next line (a here-string's third < ends the word before it starts)
            j = i + 2; strip = 0
            if (substr(line, j, 1) == "-") { strip = 1; j++ }
            while (j <= n && substr(line, j, 1) ~ /[ \t]/) j++
            w = ""
            while (j <= n) {
                ch = substr(line, j, 1)
                if (ch ~ /[ \t;&|()<>]/) break
                if (ch == "'" || ch == "\"") { k = index(substr(line, j + 1), ch); if (!k) { w = w substr(line, j + 1); j = n + 1; break }; w = w substr(line, j + 1, k - 1); j += k + 1; continue }
                if (ch == "\\") { w = w substr(line, j + 1, 1); j += 2; continue }
                w = w ch; j++
            }
            if (w != "") { hq[++nh] = w; hs[nh] = strip }
            emit(substr(line, i, j - i)); i = j; prev = "x"; continue
        }
        emit(c); i++; prev = c
    }
    if (nh && !hi) hi = 1
    if (pm !~ /^[ \t]*$/) pend = !infn && d == 0 && head(pm)            # a header whose { comes on a later line
    print out
}
END {
    if (hi) bad = bad (bad == "" ? "" : "; ") "the heredoc ended by " hq[hi] " never ends"
    if (d > 0) bad = bad (bad == "" ? "" : "; ") "a " st[d] " context is still open at the end"
    if (b > 0) bad = bad (bad == "" ? "" : "; ") b " brace(s) still open at the end"
    print tests > cnt
    if (bad != "") { print bad > (cnt ".bad"); exit 2 }
}
AWK
    for f in "$@"; do
        rel="${f#$REPO/}"; mkdir -p "$dir/$(dirname "$rel")"
        if ! LC_ALL=C awk -v cnt="$dir/$rel.tests" -f "$dir/scope.awk" "$f" > "$dir/$rel"; then
            echo "the file-scope reader lost its place in $rel: $(cat "$dir/$rel.tests.bad" 2>/dev/null)"; rc=2; : > "$dir/$rel"; continue
        fi
        want=$(grep -cE '^[[:blank:]]*@test[[:blank:]]+.*[^[:blank:]][[:blank:]]+\{' "$f" || true); got=$(cat "$dir/$rel.tests")   # bats' own @test line
        if [ "$want" != "$got" ]; then
            echo "the file-scope reader lost its place in $rel: it opened $got @test bodies where bats reads $want @test lines"; rc=2; : > "$dir/$rel"
        fi
    done
    for f in "$@"; do rel="${f#$REPO/}"; (REPO="$dir"; _scan "$dir/$rel"); done
    return "$rc"
}

@test "portability pin: the file set is the shell surfaces, found by shebang" {
    run _shell_files
    [[ "$output" == *"/bin/romp-node-launch"* ]]     # #!/bin/sh
    [[ "$output" == *"/bin/romp-service"* ]]         # #!/usr/bin/env bash
    [[ "$output" == *"/install.sh"* ]]
    [[ "$output" == *"/scripts/release.sh"* ]]
    [[ "$output" == *"/bootstrap.sh"* ]]
    [[ "$output" == *"/hooks/romp-wake.sh"* ]]
    [[ "$output" == *"/.githooks/pre-push"* ]]
    [[ "$output" == *"/vscode-extension/install.sh"* ]]
    [[ "$output" == *"/vscode-extension/scripts/ci-browser-legs.sh"* ]]   # the extension's CI scripts
    [[ "$output" == *"/tools/romp-lab/lab.sh"* ]]      # the tools live one directory down: tools/*/*.sh
    [[ "$output" == *"/tools/ui-verify/shot.sh"* ]]
    [[ "$output" != *".py"* ]]                        # a python file under bin/ is not read
    [[ "$output" != *".mjs"* ]]                       # nor a node tool under tools/
}

_plants() {   # one line per construct family, each a hit wherever it stands as code: the planted cases write them
    cat <<'EOF'
v="${1,,}"
declare -A map
local -n ref=v
[[ -v v ]] && :
mapfile -t lines < file
wait -n
coproc { :; }
cmd &>/dev/null
case x in a) ;& b) ;; esac
cmd |& tee
q="${v@Q}"
t=$EPOCHSECONDS
[ -v v ] && :
shopt -s globstar
p=$BASHPID
declare -g G=1
last="${arr[-1]}"
printf '%(%Y)T\n' -1
read -N 4 chunk
exec {fd}<file
tail="${v:1:-1}"
u=$'\u00e9'
EOF
}

@test "portability pin: every construct family is caught in a planted file, and a comment naming one is not" {
    local planted="$TEST_DIR/planted.sh"
    { printf '%s\n' '#!/usr/bin/env bash' '# a comment may say ${x,,} or declare -A or mapfile; only code counts'; _plants; } > "$planted"
    run _scan "$planted"
    local families; families="$(printf '%s\n' "$CONSTRUCTS" | grep -c .)"
    [ "$families" -eq 22 ]
    local caught; caught="$(printf '%s\n' "$output" | cut -d: -f1 | sort -u | grep -c .)"
    [ "$caught" -eq "$families" ]
    [[ "$output" != *"a comment may say"* ]]
}

@test "portability pin: a Python heredoc's negative index and a nested default are not hits" {
    local benign="$TEST_DIR/benign.sh"
    cat > "$benign" <<'EOF'
#!/usr/bin/env bash
port="${ROMP_SERVE_PORT:-${ROMP_KERNEL_PORT:-29855}}"
python3 - <<'PYCODE'
last = mins[-1]["data"] if mins else {}
PYCODE
EOF
    run _scan "$benign"
    [ -z "$output" ]
}

@test "portability pin: the declare -A, -n and -g families match their letter anywhere in the option cluster, and a cluster without it is not a hit" {
    # until 2026-09-30 each pattern ended the cluster at its letter, so declare -Ax, local -nr and declare -gx passed the pin
    local f="$TEST_DIR/flags.sh" want
    printf '%s\n' '#!/usr/bin/env bash' 'declare -Ax a1' 'local -Ar a2' 'declare -gAx a3' 'local -nr r1=v' 'declare -gx g1=1' \
        'typeset -xgr g2=1' 'declare -rx c1=1' 'local -a c2' 'declare -i c3' 'local -r c4' 'typeset -x c5' > "$f"
    run _scan "$f"
    [ "$status" -eq 0 ]
    want="$(printf '%s\n' \
        "associative array, declare -A (bash 4): $f:2:declare -Ax a1" \
        "associative array, declare -A (bash 4): $f:3:local -Ar a2" \
        "associative array, declare -A (bash 4): $f:4:declare -gAx a3" \
        "declare -g (bash 4.2): $f:4:declare -gAx a3" \
        "nameref, declare -n (bash 4.3): $f:5:local -nr r1=v" \
        "declare -g (bash 4.2): $f:6:declare -gx g1=1" \
        "declare -g (bash 4.2): $f:7:typeset -xgr g2=1")"
    [ "$output" = "$want" ]
}

@test "portability pin: a head that blocks is cut at the list's own bound, not the job's" {
    # the tagged tip's confirming macOS run (2026-09-16): the pin sat 180 s until the job's per-test bound killed it, nameless as
    # to WHICH command stalled. The list and the scan run under bounds of their own now, and the pin says which one stalled.
    local tools="$TEST_DIR/blocking"; mkdir -p "$tools"
    printf '#!/usr/bin/env bash\nsleep 300\n' > "$tools/head"; chmod +x "$tools/head"
    local t0=$SECONDS rc=0
    PATH="$tools:$PATH" _bounded_fn 3 _shell_files >/dev/null 2>&1 || rc=$?
    [ "$rc" -eq 124 ] || [ "$rc" -eq 142 ]                    # timeout's 124, or perl's SIGALRM
    [ $((SECONDS - t0)) -lt 10 ]
}

@test "portability pin: a stray shell file in the tree is not a surface: the set is git's tracked list" {
    local stray="$REPO/bin/stray-portability-probe-$$.sh"
    printf '#!/usr/bin/env bash\nv="${1,,}"\n' > "$stray"
    local out; out="$(_shell_files)"; rm -f "$stray"
    [[ "$out" != *"stray-portability-probe"* ]]
    [[ "$out" == *"/bin/romp-service"* ]]                    # the tracked surfaces are still the set
}

@test "portability pin: the shell surfaces use no bash-4-only construct" {
    local files rc=0
    files="$(_bounded_fn 30 _shell_files)" || rc=$?
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 142 ]; then echo "the shell-surface list stalled: _shell_files did not return within 30 s (a blocking head or grep on PATH, a hung git)"; return 1; fi
    [ -n "$files" ]
    run _bounded_fn 120 _scan $files
    if [ "$status" -eq 124 ] || [ "$status" -eq 142 ]; then echo "the shell-surface scan stalled: _scan did not return within 120 s"; return 1; fi
    if [ -n "$output" ]; then
        echo "bash-4-only constructs in the shell surfaces (a stock mac's /bin/bash is 3.2; use a case pattern, tr, a plain array, 2>&1):"
        echo "$output"
        return 1
    fi
}

@test "file-scope pin: the file set is every tracked bats file and bash helper under tests/, and a stray one is not" {
    local stray="$REPO/tests/stray-scope-probe-$$.bash"
    printf 'declare -gA X=()\n' > "$stray"
    local out; out="$(_scope_files)"; rm -f "$stray"
    [[ "$out" != *"stray-scope-probe"* ]]
    [[ "$out" == *"/tests/pre-push-hook.bats"* ]]
    [[ "$out" == *"/tests/shell-portability.bats"* ]]
    [[ "$out" == *"/tests/git-hermetic.bash"* ]]                 # a helper the files load, which bats runs while it gathers
    [[ "$out" != *"/tests/pre-push-reads-header.sh"* ]]          # a script a test runs is no file bats gathers
}

@test "file-scope pin: every construct family planted at file scope is caught, and the same lines in a function body, a @test body, a heredoc, a comment or a single-quoted string are not" {
    local REPO="$TEST_DIR/plant" f="$TEST_DIR/plant/tests/planted.bats" mark n
    mkdir -p "$REPO/tests"
    {
        printf '%s\n' '#!/usr/bin/env bats' '# a comment at file scope may say declare -A or mapfile' "QUOTED='declare -A x" "mapfile -t y'"
        printf 'X=1   # a trailing comment may say declare -A\n'
        printf 'setup() {\n'; _plants; printf '    [[ $x =~ [{] ]] && echo "}"   # the brace test'"'"'s own { in a comment\n    y=${x:- }; z="${x%%%%"'"'"'"*}"; w="${x:-it'"'"'s}"; u="`printf %%s "it'"'"'s"`"; v="$(printf %%s "it'"'"'s")"\n}\n'
        printf '@test "a planted case whose name says mapfile, with } and { in it" {\n'; _plants
        printf "    cat <<'PLANT'\n"; _plants; printf '}\nPLANT\n'
        printf '    cat <<-END\n\t}\n\tEND\n}\n'
        printf 'helper()\n{\n'; _plants; printf '}\n'
        printf 'function other {\n'; _plants; printf '}\n'
        printf 'FILE_SCOPE_BELOW=1\n'
        printf 'one() { declare -A m; }; declare -gA LEAK=()\n'     # code after a one-line body is file scope again
        printf 'if true; then declare -A inif; fi\n'                 # so is a compound command's, and a brace group's
        printf '{ mapfile -t grp < /dev/null; }\n'
        _plants
    } > "$f"
    mark=$(grep -n '^FILE_SCOPE_BELOW=1$' "$f" | cut -d: -f1)
    run _scope_scan "$TEST_DIR/views" "$f"
    [ "$status" -eq 0 ]
    local families; families="$(printf '%s\n' "$CONSTRUCTS" | grep -c .)"
    local caught; caught="$(printf '%s\n' "$output" | cut -d: -f1 | sort -u | grep -c .)"
    [ "$caught" -eq "$families" ]
    [[ "$output" == *"tests/planted.bats:$((mark + 1)):one() ; declare -gA LEAK=()"* ]]
    [[ "$output" == *"tests/planted.bats:$((mark + 2)):if true; then declare -A inif; fi"* ]]
    [[ "$output" == *"tests/planted.bats:$((mark + 3)):{ mapfile -t grp < /dev/null; }"* ]]
    [[ "$output" != *"declare -A m;"* ]]
    for n in $(printf '%s\n' "$output" | sed -E 's/^.*: tests\/planted\.bats:([0-9]+):.*$/\1/'); do   # a family's name may hold a colon
        [ "$n" -gt "$mark" ]                                        # nothing above the mark: bodies, the heredoc, the comment, the quote
    done
    [ "$(printf '%s\n' "$output" | grep -c .)" -ge "$((families + 3))" ]
}

@test "file-scope pin: the incident's shape, a declare -gA between two functions, is named with its file and line" {
    local REPO="$TEST_DIR/plant" f="$TEST_DIR/plant/tests/incident.bats"
    mkdir -p "$REPO/tests"
    printf '%s\n' '#!/usr/bin/env bats' 'census_a() {' '    local -A seen' '}' 'declare -gA CENSUS_IS=()' 'census_b() { mapfile -t l < "$1"; }' > "$f"
    run _scope_scan "$TEST_DIR/views" "$f"
    [ "$status" -eq 0 ]
    [ "$output" = "$(printf '%s\n' "associative array, declare -A (bash 4): tests/incident.bats:5:declare -gA CENSUS_IS=()" \
        "declare -g (bash 4.2): tests/incident.bats:5:declare -gA CENSUS_IS=()")" ]
}

@test "file-scope pin: a file the reader loses its place in fails the pin by name and reason, and no hit is read from it" {
    local REPO="$TEST_DIR/plant" f
    mkdir -p "$REPO/tests"
    printf '%s\n' 'f() {' "    cat <<'NEVER'" '}' 'declare -A a' > "$REPO/tests/heredoc.bats"
    { printf '%s\n' 'f() {' '    echo {' '}'; printf '@test "t" {\n    :\n}\n'; printf '}\ndeclare -A b\n'; } > "$REPO/tests/brace.bats"   # ends clean, the @test read inside f
    printf '%s\n' 'f() {' '    :' 'declare -A c' > "$REPO/tests/open.bats"
    printf '%s\n' 'f() { :; }' '}' 'declare -A d' > "$REPO/tests/stray.bats"
    { printf '@test "t" {\n'; printf '%s\n' "    x='open" '}' 'declare -A e'; } > "$REPO/tests/quote.bats"
    for f in "heredoc:the heredoc ended by NEVER never ends" "brace:it opened 0 @test bodies where bats reads 1 @test lines" \
             "open:1 brace(s) still open at the end" "stray:a } with no { open at line 2" "quote:a sq context is still open at the end"; do
        run _scope_scan "$TEST_DIR/views" "$REPO/tests/${f%%:*}.bats"
        [ "$status" -eq 2 ]
        [[ "$output" == "the file-scope reader lost its place in tests/${f%%:*}.bats: "*"${f#*:}"* ]]
        [[ "$output" != *"declare -A"* ]]
    done
}

_scope_verdict() {   # $1 a directory, $@ files under REPO: the file-scope pin's verdict, _scope_scan run under a bound of its own; silent
                     # with status 0 when every file reads clean and holds no hit, else what failed on stdout and status 1. A file
                     # the reader cannot follow is reported as that, never as a construct, with any other file's hits after it
    local dir="$1" out rc=0; shift
    out="$(_bounded_fn 120 _scope_scan "$dir" "$@")" || rc=$?
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 142 ]; then echo "the file-scope scan stalled: _scope_scan did not return within 120 s"; return 1; fi
    if [ "$rc" -eq 2 ]; then
        echo "the file-scope reader could not follow a file (a limit the header names, or a new shape): reword the line it names or teach _scope_scan the shape; any construct hits are listed with it:"
        echo "$out"
        return 1
    fi
    if [ "$rc" -ne 0 ] || [ -n "$out" ]; then
        echo "bash-4-only constructs at the file scope of a bats file or a helper it loads, which bats runs while it gathers (a stock mac's /bin/bash is 3.2, and one such line leaves the cell with no test result: move it into the function or case that needs it, and skip that case under an older bash, as needs_bash4 in tests/pre-push-hook.bats does):"
        echo "$out"
        return 1
    fi
    return 0
}

@test "file-scope pin: the verdict names a file the reader cannot follow as that, not as a construct, with the other files' hits after it" {
    local REPO="$TEST_DIR/plant"
    mkdir -p "$REPO/tests"
    printf '%s\n' 'f() {' '    echo }' '}' > "$REPO/tests/zz-brace.bats"       # a legal echo } in a body closes it early for the reader
    printf '%s\n' 'declare -A LEAK=()' > "$REPO/tests/leak.bats"
    printf '%s\n' 'g() {' '    local -A fine' '}' > "$REPO/tests/clean.bats"
    run _scope_verdict "$TEST_DIR/views" "$REPO/tests/clean.bats"
    [ "$status" -eq 0 ]
    [ -z "$output" ]
    run _scope_verdict "$TEST_DIR/views" "$REPO/tests/leak.bats"
    [ "$status" -eq 1 ]
    [[ "${lines[0]}" == "bash-4-only constructs at the file scope "* ]]
    [ "${lines[1]}" = "associative array, declare -A (bash 4): tests/leak.bats:1:declare -A LEAK=()" ]
    run _scope_verdict "$TEST_DIR/views" "$REPO/tests/zz-brace.bats" "$REPO/tests/leak.bats"
    [ "$status" -eq 1 ]
    [[ "${lines[0]}" == "the file-scope reader could not follow a file "* ]]
    [ "${lines[1]}" = "the file-scope reader lost its place in tests/zz-brace.bats: a } with no { open at line 3" ]
    [ "${lines[2]}" = "associative array, declare -A (bash 4): tests/leak.bats:1:declare -A LEAK=()" ]
    [[ "$output" != *"bash-4-only constructs"* ]]
}

@test "file-scope pin: no bats file or helper under tests/ holds a bash-4-only construct at file scope" {
    local files rc=0
    files="$(_bounded_fn 30 _scope_files)" || rc=$?
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 142 ]; then echo "the file list stalled: _scope_files did not return within 30 s (a hung git)"; return 1; fi
    [[ "$files" == *"/tests/pre-push-hook.bats"* ]]
    _scope_verdict "$TEST_DIR/scope" $files
}

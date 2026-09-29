#!/usr/bin/env bash
# Emit the block of .githooks/pre-push's header that lies between its two
# marker lines, from tests/pre-push-reads.tsv, the one authority for it: the
# prose rows first, one paragraph per paragraph name in the order the names
# first appear (the rows of one paragraph joined with a space), then the two
# lists, each gate= and own= read on a line of its own with its fact or its
# safe-side reason folded under it. Every paragraph and fact is folded at 78
# columns by the awk below, word by word, so the output depends on the table
# alone. tests/pre-push-hook.bats' table case asserts the hook's block equals
# this output byte for byte: a change to a row's read, fact or reason changes
# the header, and a hand edit of the header is red there. One optional
# argument: the tsv path.
set -u
tsv="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/pre-push-reads.tsv}"
LC_ALL=C awk -F'\t' -v width=78 '
    function fold(first, cont, text,    n, w, i, line, started) {
        n = split(text, w, " ")
        line = ""; started = 0
        for (i = 1; i <= n; i++) {
            if (!started) { line = first w[i]; started = 1 }
            else if (length(line) + 1 + length(w[i]) > width) { print line; line = cont w[i] }
            else line = line " " w[i]
        }
        if (started) print line
    }
    /^#/ || /^$/ { next }
    $1 == "prose" { if (!($2 in text)) order[++np] = $2; text[$2] = ($2 in text) ? text[$2] " " $3 : $3; next }
    $1 == "gate"  { ng++; gread[ng] = $2; gfact[ng] = $3; next }
    $1 == "own"   { no++; oread[no] = $2; ofact[no] = $3; next }
    END {
        for (i = 1; i <= np; i++) fold("# ", "# ", text[order[i]])
        print "# Reads gated by a sibling fact (gate=):"
        for (i = 1; i <= ng; i++) { print "#   " gread[i]; fold("#       ", "#       ", gfact[i]) }
        print "# Reads whose empty answer is the object" sprintf("%c", 39) "s own (own=):"
        for (i = 1; i <= no; i++) { print "#   " oread[i]; fold("#       ", "#       ", ofact[i]) }
    }' "$tsv"

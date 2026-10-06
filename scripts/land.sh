#!/usr/bin/env bash
# scripts/land.sh <name> [--auto] [--flake RUN/ATTEMPT=TEXT]... [--no-notify] [--no-fetch]: land a batch.
#
# It runs `scripts/batch.py land` with the same arguments (it execs it) and has no merge logic of its
# own, so a batch has one gated merge path (pre-round ruling, item 2): batch.py land runs verify
# again (the sweep result at the batch head's full sha, the batch head containing main), reads the
# batch push's CI run from GitHub, reads main once more right before the merge, merges the batch PR
# with a merge commit pinned to the verified head, and runs finish, which reports loudly when the
# merge commit's first parent is not the main verify read. Every PR lands through a batch, a single
# PR as a one-member batch (`scripts/batch.py plan --only N`), so the rules this script once kept for
# a member PR, a stacked pair and a merge into an open PR's branch are gone with that path (item 3).
#
# `scripts/land.sh --help` prints this usage and then `scripts/batch.py land --help`, which names
# every flag and refusal. Env: whatever scripts/batch.py reads (ROMP_GH names the gh binary). The
# exit status is batch.py's.
set -euo pipefail

BATCH="$(cd "$(dirname "$0")" && pwd)/batch.py"

if [ "${1:-}" = --help ] || [ "${1:-}" = -h ]; then
    cat <<'EOF'
usage: scripts/land.sh <name> [--auto] [--flake RUN/ATTEMPT=TEXT]... [--no-notify] [--no-fetch]
       scripts/land.sh --help

Lands a batch: runs `scripts/batch.py land` with the same arguments and has no merge logic of its
own. <name> is the batch's name, as `scripts/batch.py plan` printed it, not a PR number. A single
PR lands as a one-member batch (scripts/batch.py plan --only N, then assemble, sweep, verify, push
and summarize). The flags and refusals are batch.py land's:

EOF
    exec "$BATCH" land --help
fi
exec "$BATCH" land "$@"

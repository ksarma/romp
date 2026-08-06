#!/usr/bin/env bats

# .gitleaks.toml — the repo's secret-scanning rules, exercised against the REAL
# scanner (tests/install-sh.bats stubs it, because what it tests there is the
# hook's wiring; what is under test here is the config itself, which a stub
# cannot check).
#
# Skipped when gitleaks is not installed, so a clone that never wanted the
# scanner still runs a green suite — CI installs it and is the arbiter.
#
# Nothing in this file may contain a credential-shaped literal: gitleaks scans
# this repo, and a fixture secret written out longhand would flag the very test
# that proves the scanner works. The probes below are assembled at run time and
# only ever exist in a temp file.

ROMP_DIR="$(cd "$(dirname "$BATS_TEST_FILENAME")/.." && pwd)"

setup() {
    command -v gitleaks >/dev/null || skip "gitleaks not installed"
    TEST_DIR="$(mktemp -d)"
    CFG="$ROMP_DIR/.gitleaks.toml"
}

teardown() { rm -rf "${TEST_DIR:-}"; }

scan() { gitleaks dir "$TEST_DIR" --no-banner --redact --exit-code 1 --config "$CFG"; }

@test "the config parses and the repo as it stands is clean" {
    run gitleaks dir "$ROMP_DIR" --no-banner --redact --exit-code 1 --config "$CFG"
    [ "$status" -eq 0 ]
}

@test "every commit in this clone is clean" {
    run gitleaks git "$ROMP_DIR" --no-banner --redact --exit-code 1 --config "$CFG" --log-opts=--all
    [ "$status" -eq 0 ]
}

@test "a planted credential is caught" {
    # ghp_ + 36 chars, assembled so the literal never lives in a tracked file.
    printf 'token = "gh%s_%s%s"\n' p "$(printf '0123456789%.0s' 1 2 3)" abcdef > "$TEST_DIR/probe.py"
    run scan
    [ "$status" -ne 0 ]
}

@test "RFC 6455's example WebSocket key is excused" {
    # The handshake nonce the kernel's tests hand a fake request. High entropy by
    # protocol design, published in the RFC, not a credential.
    printf 'headers = {"Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="}\n' > "$TEST_DIR/probe.py"
    run scan
    [ "$status" -eq 0 ]
}

@test "the excuse is the value, not the header — another WebSocket key still trips" {
    # The narrowness that makes the allowlist safe: it forgives one published
    # string, not every line that mentions Sec-WebSocket-Key. Halves, because a
    # whole one written here would trip the scan of this very repo — which is
    # how this test first failed.
    printf 'headers = {"Sec-WebSocket-Key": "%s%s"}\n' "9kLm2QpXvTz7" "RbNc4WdY1A==" > "$TEST_DIR/probe.py"
    run scan
    [ "$status" -ne 0 ]
}

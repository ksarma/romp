# Contributing

Thanks for looking at Romp.

This is a personal side project. Bug reports and pull requests are
welcome, and I'd rather hear about a problem than not. Responses may be slow, and
I may not get to everything. 

If you're interested in reporting bugs and making PRs, please try to reproduce them or ground your suggestions with the latest code at the tip of the main branch rather than a tagged release version.

## Running the tests

```bash
python3 -m pytest -q       # the Python pipeline (kernel/, cli/, postal/)
bats tests/*.bats          # the shell surfaces (hooks, postal, manager)
cd vscode-extension && npm ci && npm test
```

`tests/gitleaks-config.bats` checks the secret-scanning rules against the real
scanner and skips itself when `gitleaks` is not installed (`brew install
gitleaks`, or the pinned binary CI uses). Installing it also arms the credential
half of the `pre-push` hook, which is worth having before you push anything.

The Python and shell suites are also the CI gate, across Python 3.10 to 3.13 on
Linux; the macOS cells run on demand from the Actions tab (they are billed even
on a public repo, so they are not part of the per-push matrix).

## Measuring dashboard pane performance

`tools/ui-bench.mjs` measures, in a headless Chromium, what the browser does
with the frames the kernel pushes to a pane page, so the cost of a rendering
change can be measured before and after it lands. It needs the extension's
`node_modules` (`cd vscode-extension && npm ci`), a built `dist/`
(`npm run build` there), `python3`, and a Chromium: Playwright's own
(`npx playwright install chromium` in `vscode-extension/`) or a system Google
Chrome.

```bash
# a frame stream with invented content, for a bench that needs no live board
node tools/ui-bench.mjs --synthesize feed --cards 200 --out /tmp/romp-perf/synth-feed.jsonl
# replay it into the real feed page and print per-frame timings
node tools/ui-bench.mjs --replay feed --frames /tmp/romp-perf/synth-feed.jsonl --fast --json /tmp/romp-perf/before.json
# change the bundle, rebuild, replay again, then compare the two reports
node tools/ui-bench.mjs --compare /tmp/romp-perf/before.json /tmp/romp-perf/after.json
# record 90 seconds of what a running kernel sends the feed page, then replay that
node tools/ui-bench.mjs --record feed --seconds 90 --out /tmp/romp-perf/frames-feed.jsonl
node tools/ui-bench.mjs --replay feed --frames /tmp/romp-perf/frames-feed.jsonl --json /tmp/romp-perf/live.json
```

A replay reports, per frame type, the bytes, the synchronous handler time, and
the time until the main thread is free again (to the second
`requestAnimationFrame` after the message) as p50, p90, and max; then the
long-animation-frame entries with script attribution, the JavaScript heap, the
DOM size, and every console error. The numbers come from the real pages: the
kernel's own HTTP handler serves the HTML, the shim, and the bundles from a
`python3` subprocess under an isolated environment (the pattern of
`tests/test_color_route.py`), and a Node front server answers the page's
WebSocket and proxies everything else to it. The default is no CPU throttling,
a desktop; `--cpu-throttle 4` emulates a machine four times slower. `--iters 3`
pools three runs. `--fast` sends the frames back-to-back instead of at their
recorded pacing; settle times then overlap, handler times do not.

A recording holds real session data. `--record` connects to the running kernel
as one more pane (the same URL and capabilities, the token as the page's
cookie), sends the ready handshake and nothing else, and writes only under
`/tmp`, refusing a path inside a git checkout. Never copy one into the repo;
the tests use synthetic streams. Apps: `feed`, `fleet` (the Outline pane),
`waiting`, `chat`, `timeline`, `files`. The chat's frames cannot be
synthesized, only recorded.

`tests/ui-bench.test.mjs` (`node --test tests/ui-bench.test.mjs`) covers the
tool and replays synthetic feed and timeline streams in a real browser. It
skips, saying why, when no Chromium or `python3` is available.

## Test environment

Three things about the test environment are worth knowing, because all have
produced confusing failures:

- The bats suite takes about a minute on Linux and about fifteen on macOS. That
  is expected, not a hang.
- Some tests behave differently depending on whether a `tmux` binary exists on
  the machine, because romp treats "no tmux at all" as headless and falls back
  to file-derived sessions. Tests that care now pin this explicitly; if you add
  one that calls into session liveness, pin it too rather than inheriting the
  machine's state.
- On macOS, run the bats suite with a modern bash (`brew install bash`; bats
  picks it up via `env bash` when `/opt/homebrew/bin` precedes `/bin` on PATH).
  The stock `/bin/bash` 3.2 does not fail a test on a mid-test `[[ ]]`
  assertion — only the last command's status counts — so a stale assertion can
  pass silently for months. Linux CI runs bash 5 and is the arbiter; two
  assertions went stale exactly this way while CI was offline.

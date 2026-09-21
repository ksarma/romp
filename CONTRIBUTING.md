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

`npm test` caps `node --test` at 8 worker processes (`--test-concurrency=8`) and each
worker's V8 heap at 2 GB (`--max-old-space-size=2048`). Node's default concurrency is
one worker per core minus one, so a 32-core machine would start 31 test processes at
once, some driving a headless Chromium, and overlapping runs there ran the machine out
of memory. V8's default heap limit is set from memory: node hands V8 the smaller of the
machine's RAM and the process's cgroup memory limit (`process.constrainedMemory()`), and
on 64-bit V8 sets the old generation to half of that below 4 GB, with a floor of 256 MB
(so a machine or cgroup under 512 MB still gets 256 MB), 2 GB from 4 GB up to 15 GB, and
4 GB from 15 GB up, a step taken only while V8's `huge_max_old_generation_size` flag is
on, as it is by default (node 22; the `heap_size_limit` it reports adds the young
generation: 4144 MB measured under node 22 on the machine that ran the suite, 2096 MB
under a 4 to 14 GB cgroup, about 2 GB on an 8 GB laptop). So the cap halves the default
only on hosts or cgroups of 15 GB or more; below that V8 already defaults to 2 GB or
less, and eight workers are bounded to 16 GB either way. The cap is sized at about 8x the
largest DOM fixture measured, `ui/timeline-tags-scale.test.ts` at
210 to 246 MB RSS over ten runs (the suite-wide per-file peak was not measured). The cap
bounds the V8 heap only (objects, strings, arrays); ArrayBuffer and typed-array backing
stores live outside it, so it would not have stopped the runaway of 2026-09-09, in which
node's `assert` built a diff of tens of GB in typed arrays from a failing assertion on
a fake DOM node. That class is stopped by the fake DOM itself (`ui/test-dom-shim.ts`: a
node inspects as a short projection, never as its tree) and bounded only by a process
or cgroup limit (`systemd-run --scope -p MemoryMax=...`, `prlimit`). To use another
worker count, build the tests and start the runner yourself, from `vscode-extension/`:
`node esbuild.js --tests && node --max-old-space-size=2048 --test --test-concurrency=N
'out-tests/**/*.test.js'`.

CI's vscode-extension job runs `npm test` before it installs a browser, so every browser leg
(a test module that launches a Playwright browser) skips at launch there. The legs named in
`vscode-extension/ci-browser-legs.txt`, one compiled bundle path per line, run again after the
job's Chromium install with `ROMP_BROWSER_LEGS_REQUIRE=1`. The one shared launcher, `inBrowser`
in `ui/webview/real-viewer-leg.ts`, reads the switch (any non-empty value arms it): under it a
leg that cannot launch fails naming the switch and the reason instead of skipping. A rostered
leg launches through `inBrowser` with no launch or skip of its own, and in the gating job that
is Chromium; a leg's Firefox and WebKit runs live elsewhere (a served pytest step, a local run),
and a leg that launches on its own is refused from the roster until it takes the shared
launcher; after the run a skipped test, or a leg that registered no test, is red. Every other
browser leg is listed in `vscode-extension/ci-browser-legs-excluded.txt`
with a reason. What a browser leg is, `vscode-extension/scripts/browser-legs-census.mjs` reads
from each test module's tree with the TypeScript compiler (a call of the shared launcher through
its import under any name, a playwright package named by any specifier, or a driver string that
loads one; a form it cannot classify is refused with file and line). A PR that wants its legs
run moves them to the roster (a leg already in the exclusions loses its line there in the same
commit). `ui/webview/ci-browser-legs-census.test.ts`, in the extension's `npm test`, holds every
browser leg in the tree to one file or the other and fails on a line whose source is gone, and
the step's script checks the same before it runs a leg; `tools/ci-browser-legs.test.mjs`, which
CI's shell job runs without `npm ci`, holds the two files' shape and reasons and runs the script
over synthetic trees.

`tests/gitleaks-config.bats` checks the secret-scanning rules in `.gitleaks.toml`
against the real scanner and skips itself when `gitleaks` is not installed
(`brew install gitleaks`, or a release binary; `ROMP_GITLEAKS` names one that is
not on `PATH`). Installing it also arms the credential half of the `pre-push`
hook, which is worth having before you push anything.

The Python and shell suites are also the CI gate, across Python 3.10 to 3.13 on
Linux; the macOS cells run on demand from the Actions tab (they are billed even
on a public repo, so they are not part of the per-push matrix).

## Measuring dashboard pane performance

`tools/ui-bench.mjs` replays a pane's frame stream into the real pane page in
a headless Chromium and reports where the browser's time goes, so a rendering
change can be measured before and after it lands, on the same input. It needs
the extension's `node_modules` (`cd vscode-extension && npm ci`), a built
`dist/` (`npm run build` there), `python3`, and a Chromium: Playwright's own
(`npx playwright install chromium` in `vscode-extension/`) or a system Google
Chrome. The tool is POSIX-only (Linux and macOS).

```bash
# a frame stream with invented content, for a bench that needs no live kernel
node tools/ui-bench.mjs --synthesize feed --cards 200 --out /tmp/romp-perf/synth-feed.jsonl
# replay it into the real feed page, a frame every 100 ms, and print per-frame timings
node tools/ui-bench.mjs --replay feed --frames /tmp/romp-perf/synth-feed.jsonl --gap 100 --json /tmp/romp-perf/before.json
# change the bundle, rebuild, replay again, then compare the two reports
node tools/ui-bench.mjs --compare /tmp/romp-perf/before.json /tmp/romp-perf/after.json
# record 90 seconds of what a running kernel sends the feed page, then replay that
node tools/ui-bench.mjs --record feed --seconds 90 --out /tmp/romp-perf/frames-feed.jsonl
node tools/ui-bench.mjs --replay feed --frames /tmp/romp-perf/frames-feed.jsonl --json /tmp/romp-perf/live.json
```

The pane page's shim does not render a frame inside its WebSocket handler. The
handler parses the frame, applies a view delta to the state it holds, and
queues the result; a separate task (a `MessageChannel` message, so it runs
while the tab is hidden too) hands the queued frames to the bundle, where a
newer whole-state frame (a full feed, the timeline's bars or skeleton, a tab
order) replaces an older one still queued, and the task stops after 8 ms and
re-arms itself so input can land between slices. A wire frame and the
bundle's render of it are therefore two measurements, and a replay reports
both, per frame type: the bytes; the handler time (the shim's synchronous
work per wire frame); the bundle time for each frame the shim delivered on its
own; and the settle, the time from a frame's receipt until the main thread is
free again (the second `requestAnimationFrame` after the delivery that
carried it), each as p50, p90, and max. A `delivered` column beside `count`
says how many frames of a type reached the bundle as their own delivery; the
rest were coalesced into a newer frame's (the report counts them) or, for
keepalives and the resync asks the shim answers itself, never left the shim.
Frames sent back-to-back with `--fast` queue together, so most of a stream's
deltas coalesce into one delivery and the bundle column covers only that
one; for the bundle's cost per frame, replay at the recorded pacing or with
`--gap 100` (a fixed gap in milliseconds between frames). On a kernel whose
shim still renders inside the handler, the report says so and the handler
column includes the bundle's time.

After the table come the long-animation-frame entries with script
attribution, the JavaScript heap after a forced garbage collection (and before
it, so the line shows what the collection freed), the DOM size, and every
console error and uncaught exception. The attribution names each task's entry point
(the WebSocket message handler, the shim's flush task, a
`requestAnimationFrame` callback, a timer, a script's evaluation), not the
function inside the bundle that did the work. For that, add
`--cpu-profile /tmp/romp-perf/feed.cpuprofile`: it samples the page's
JavaScript with the V8 profiler across the replay, writes a file Chrome
DevTools loads (Performance panel), and prints the functions with the most
self and total time as `bundle.js:function:line` with the source position from
the dist's `.map` files (a `--production` dist is minified and has none; the
report says so), overall and inside the delivery that carried the first
content frame and the largest frame of each type. For the hottest functions
it also names the lines that hold the time; a forced synchronous layout, for
instance, shows up as one line of one function owning most of its self time.
The end-of-run layout, style, script and task counters are cumulative since
navigation, so they include page load and idle timers (the timeline redraws
every animation frame while it follows the present), and `--compare` shows
them without percentages when the two runs differ in pacing or length.
`--cpu-throttle 4` emulates a machine four times slower (the default is no
throttling). `--iters 3` pools three runs. With `--fast`, settle times overlap
(a frame's includes the frames queued behind it); handler and bundle times do
not. `--hidden` replays into a page that reports itself hidden (a dashboard tab in
the background: the panes hold their paint and the timeline stops its live
tick), shows it again after the last frame, and the report adds the return's
synchronous cost (the catch-up paint plus the pane shim's and federation's
return handlers); with `--cpu-profile` the profile runs through that return. A
timeline replay also reports how many wire bars and judging entries the view
expanded during the replay, and under `--hidden` how many the return expanded.
`--compare` names each report's regime and refuses a hidden report against a
visible one, since the two measure different work.

The numbers come from the real pages: the kernel's own HTTP handler serves the
HTML, the shim, and the bundles from a `python3` subprocess under an isolated
environment, the pattern of `tests/test_color_route.py` with the floors
`tests/conftest.py` applies (the manager variables are removed and the manager
port set to a dead one; every credential and key-source name conftest pops is
removed, the API keys, the key reference and command, the token credentials,
the auth declaration and 1Password's names; the manager's key file and the
boot model-catalog fetch are
pointed away, the Claude binary is `/bin/false`, the CLI scope is off, the
postal peer bus is off, the serve token is minted for the run, and the
subprocess exits when the bench does). Run state, the browser's profile
included, lives under one per-user directory in the temp root; a run killed
with its whole process group leaves its entry there until the next run sweeps
it. A Node front server answers the page's WebSocket and proxies everything
else to the subprocess.

A recording holds real session data. `--record` connects to the running kernel
as one more pane (the same URL and query, the token as the page's cookie),
sends the ready handshake and nothing else, and writes only under the system
temp directory (private to your user: directory 0700, file 0600), refusing a
path inside a git checkout or through a symlink. Never copy one into the repo;
the tests use synthetic streams. Apps: `feed`, `fleet` (the Outline pane),
`waiting`, `chat`, `timeline`, `files`. Two cannot be synthesized, only
recorded: the chat's session frame is built by `build_session` and is too rich
to fake, and the Files pane parses no frames at all (its socket carries
keepalives and op replies).

`tests/ui-bench.test.mjs` (`node --test tests/ui-bench.test.mjs`) covers the
tool, including the recording client against a local WebSocket server and the
Handler subprocess's isolation, and replays synthetic feed and timeline streams
in a real browser, the timeline once more with the page hidden, and that hidden
replay again with the page's clock standing still across each delivery (every
bundle reading 0.0 ms: on a hidden page the report's bundle column is asserted
as measured, not as having taken time, since a hidden page's delivery draws
nothing and can read 0.0 at the clock's 0.1 ms steps; a visible page's column
keeps the strict claim, its deliveries rendering inside the bracket). The browser tests
skip, saying why, when no Chromium (either
playwright's own, `cd vscode-extension && npx playwright install chromium`,
which CI installs so the required check never rides the runner image's
browser, or a system Google Chrome), no `python3` or no built `dist/` is
available; with `ROMP_UI_BENCH_REQUIRE=1` in the environment (CI sets it) that
skip is a failure instead. The replays assert
what holds under any scheduling (frame totals, ordering, the handoff's
accounting); the timing relations the bench measures (a settle margin, a render
outweighing a parse, the CPU throttle's slowdown) are assertions only with
`ROMP_UI_BENCH_TIMING=1`, which a loaded machine can fail and CI does not set;
without it a relation that did not hold is a diagnostic line in the output.

## Test environment

Three things about the test environment are worth knowing, because all have
produced confusing failures:

- The bats suite takes about a minute on Linux and about fifteen on macOS. That
  is expected, not a hang.
- On macOS, run the bats suite with a modern bash (`brew install bash`; bats
  picks it up via `env bash` when `/opt/homebrew/bin` precedes `/bin` on PATH).
  The stock `/bin/bash` 3.2 does not fail a test on a mid-test `[[ ]]`
  assertion — only the last command's status counts — so a stale assertion can
  pass silently for months. Linux CI runs bash 5 and is the arbiter; two
  assertions went stale exactly this way while CI was offline.

## A message listener from another world clones every frame it can see

The pane pages receive the kernel's frames as `message` events on `window`.
Blink hands a listener in the page's own JavaScript world the event's data
object itself, but a listener in another world, a browser extension's content
script, that reads `event.data` receives a structured clone of the whole
object, made synchronously inside the dispatch: 35-46 ms and about 7 MB of
garbage per dispatch of a 7 MB frame in a Chromium probe, against 0 ms for a
direct call. The live `romp perf client` rows show it as a `fed:<type>` share
far above federation's own compute (about 1 ms per frame).

`federation.js` therefore hands its merged frames (`feed`, `tabOrder`, `data`,
`bars`) to the pane's handler by direct call (`window.__rompFed.onFrame`,
through `ui/webview/frame-listener.ts`) and dispatches them on `window` only
when nothing registered. Every other frame still arrives as a `window` event,
so a foreign listener still sees those, and a new frame type that grows large
should go through the registry too.

To check a browser for such a listener before or after a deploy: open DevTools
on the dashboard, pick the feed iframe in the console's context selector, and
time a dispatch of a large frame:

```js
const big = Array.from({ length: 150000 }, (_, i) => ({ i, s: "x" }));
const t = performance.now();
window.dispatchEvent(new MessageEvent("message", { data: big }));
performance.now() - t
```

Under a millisecond means no foreign reader: only same-world listeners saw the
event. Tens of milliseconds means a listener in another world read
`event.data` and paid for the clone. This timing is the detection step.
`getEventListeners(window).message` cannot be, because it is per-world: it
lists only the listeners registered from the world whose context the console
is running in, so in the page's own context it shows romp's listeners and
nothing else, whether or not a content script is present. To see a content
script's listener, switch the console's context selector to that extension's
context (listed under the frame by extension name) and run the enumeration
there. Every romp listener on a kernel pane page comes from that page's pane
bundle (`feed.js` on the feed page, `render.js` on the chat, and so on; the
kernel-served timeline's is its inline boot; under a dev build with source
maps DevTools may show the source file names), and any other URL, in
particular a `chrome-extension://` one, is the foreign listener. With no
foreign listener present, a large `fed:<type>` share in the live rows is not
the clone and needs another explanation before anything is built on this one.

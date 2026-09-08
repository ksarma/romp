# romp-lab — a full, hermetic, headless romp you can drive in a loop

The standing capability T106 asked for (the user 2026-08-26): run a COMPLETE romp —
real kernel, real SDK sessions replying on the cheapest usable model, the real
dashboard in a headless browser — entirely in the background, reproduce a reported
behavior by scripting the user's exact flow, and iterate until it demonstrably
matches intent. ui-verify (next door) renders static fixtures; romp-lab runs the
whole stack.

## Hermeticity (non-negotiable)

`lab.sh` exports `XDG_STATE_HOME` into a fresh temp root BEFORE anything loads —
the never-load-romp-modules-against-live-state rule: a kernel booted against live
state reconciles it (resumes turns, spawns writers). Its own `ROMP_SERVE_TOKEN`,
its own free port, `ROMP_KERNEL_NO_OPEN=1` (nothing pops up), headless Chromium
(the playwright cache vscode-extension pins). Live state, live postal, and every
visible display stay untouched. Session content is SYNTHETIC ONLY: invented
prompts, never anything from live transcripts.

## Run

```sh
tools/romp-lab/lab.sh                      # full highlight loop, screenshots + verdicts
tools/romp-lab/lab.sh --keep               # keep the temp root + kernel log for forensics
LAB_MODEL="Haiku 4.5" tools/romp-lab/lab.sh   # pick the reply model (default: the cheapest Haiku the menu offers)
```

The driver (`highlight-loop.mjs`) scripts the user's exact flow through the real
dashboard — create a session from the + picker, drop the model to the lab default,
send a prompt, get a REAL reply, select rendered text, Comment, send, follow up —
and asserts the comment-mark state at EVERY event boundary of the T102 contract:

1. send gesture → the busy pulse latches immediately (before any thread exists)
2. thread-open → no state change (sampled continuously: zero flicker)
3. the reply record lands → the pulse clears to settled yellow
4. a follow-up send → re-latches until ITS reply
5. after → nothing sticks (sampled well past the last push)

Screenshots land in the temp root's `shots/` per phase; the script exits non-zero
on the first divergence with the phase named, so it loops cleanly in a
fix → re-run cycle.

## Phases

The default run drives TWO phases, banner first (it spends no model turns):

- **banner-loop.mjs** (T119) — the reload-banner contract on the real stack: a fresh
  page shows no banner; a dist rebuild (an mtime bump on the lab's own dist copy —
  `ROMP_DIST_DIR`, so live viewers never see it) raises the shell's `#rstale` within
  one heartbeat via the shim's keepalive dv-compare; the prompt latches across live
  pushes (`wsFresh` never retires a build prompt); Reload answers it; and after a
  real kernel kill + relaunch the reconnected page still banners on the next drift.
  `--banner-only` runs just this phase.
- **highlight-loop.mjs** (T102/T106) — the comment-mark contract described above; its
  permanent tail phases: 4c full-text (the rendered thread converges to the complete
  reply), 4d clear-timing (the mark may never read settled while the final answer is
  not visible — T112), and 4e thread-interrupt (T138: the popover's working state
  offers the stop square, it targets the THREAD's own session, the ack is instant,
  the pulse clears on the gesture — no reply record is coming — and the turn ends), and
  6 relay (T145: the Relay button acks instantly, the WHOLE exchange arrives in the main
  thread machine-dressed, the thread keeps its ↩ sent-back marker and stays talkable).
  `--highlight-only` skips the banner phase.

## Cost

A lab run spends a handful of short turns on the configured model (default Haiku)
against the machine's own key — the same key live sessions bill.

## todos-lab.sh and todos-loop.mjs: the user-todos capture

`todos-lab.sh` boots its own lab and runs `todos-loop.mjs`. It is a sibling of `lab.sh` rather than a
`--todos-only` mode because the phase needs more than a flag: the user-todos switch turned on in the
lab state before the kernel boots, a postal bus on its own port (both read the switch), a synthetic
`notes-api` project with a file the session can name, video and asset directories, and a stricter
environment scrub than the other phases run under (the calling session's `ROMP_SID`,
`ROMP_MANAGER_PID` and `CLAUDE_*` are unset; `ROMP_SERVE_PORT` and `ROMP_POSTAL_PORT` point at the
lab, so a lab session's hooks reach the lab kernel and never the live one; `ROMP_CLI_SCOPE=0` starts
no systemd scope). Folding that into `lab.sh` would change the preamble every other phase runs.

```sh
tools/romp-lab/todos-lab.sh --keep --out=DIR     # keep the temp root; copy the finished assets to DIR (outside the repo)
LAB_ROOT=$HOME/scratch tools/romp-lab/todos-lab.sh   # temp root somewhere other than $TMPDIR (else /tmp)
```

The loop records one browser context with three pages (the chat, the feed, and a second chat view
for the tab strip) and asserts the user-todos contract in order:

1. A real session on the lab model files an ask through the postal `add_user_todo` tool (`POST
   /usertodo` is the recorded fallback); the card's Waiting-on-you section appears while the turn is
   still open, then the tab glyph on `api` only and the feed marker.
2. The idle session escalates to Needs input on the feed, and the gear shows the switch on.
3. Reply from the card lands as the person's own message, the row leaves the card, and the session
   answers. Dismiss is a two-step control; the section, the glyph and the marker clear together.
4. A kernel kill and relaunch keep the open asks; the SessionStart hook
   (`hooks/romp-usertodo-context.sh`, run the way the CLI runs it) returns them as the context block,
   and `POST /usertodo/context` agrees with it.
5. Reply revives the dormant session, whose transcript carries the block and whose answer names or
   withdraws the open notes.

It then cuts four GIFs from the recordings at the marks it took (`user-todos-filed.gif`, `-reply.gif`,
`-escalates.gif`, `-resume.gif`) into `assets/`, beside the PNGs, `context-block.txt`, `marks.json` and
`record.json`. A run spends about five short model turns, takes five to seven minutes, and needs
`ffmpeg` and `ffprobe` on PATH (or named in `FFMPEG` and `FFPROBE`).

Lessons from the first captures (2026-09-07):

- Dismiss the tab hover card before any frame you keep. It shows the project's full path, and a tab
  rebuild under the pointer can leave it stuck; `settleTabTip` re-enters and leaves the active tab and
  hides a stuck card directly. One run's chat frames leaked the scratch path this way.
- ffmpeg's `palettegen` and `paletteuse` at 10 fps and 1100 px keep most GIFs under 1.5 MB. The long
  resume GIF needs 900 px at 6 fps; the loop steps down a width and frame-rate ladder until a GIF is
  under 3 MB.
- The model may file its own checklist through `add_user_todo`, and every count assertion then fails
  (one run's card read "Waiting on you · 5", with three `Implement ...` rows). The prompt now says
  which tool is for what; count failures with such rows on the card are the model, not the UI.

## rail-drift.mjs — the scroll-marks invariance assertion (T129)

Under pure scrolling, the transcript rail's notches must never move relative to each other (the
user filmed exactly that, 2026-08-27). `node rail-drift.mjs [--dist <dir>]` renders a synthetic
long mixed transcript over the built bundle (no kernel needed — file:// page, placeholder UUIDs),
scrolls two full round trips sampling every notch per frame, and asserts the second round trip —
the learned regime, after the height cache primes — shows zero pairwise drift (tolerance 1.5px for
style rounding; the pre-fix map drifted 5.7px, endlessly). The first round trip's remaps are
event-keyed cache learning and are reported but not gated. Run it after any change to
contentOffsetFrame, the virtualization window, or the scroll-marks/comment-rail painters.

# Review in the file viewer: tracked changes and anchored comments

**Status: PROPOSED, NOT COMMITTED** (awaiting the user's approval, 2026-09-05). Nothing is
scheduled and nothing should be built from it unbidden. Once approved, the implementing romp
session builds it in this fork slice by slice, the header changes to the build status, and the
`plans/README.md` entry moves out of the proposed list. File and line references describe this
fork at its 2026-09-05 merge base and the track-changents repo as of the same day; as with every
plans/ document, treat them as dated.

## Summary

The user runs sessions overnight and reviews their reports in the morning. That review leaves
romp today: the report is opened on GitHub, comments are typed into it as plain text, the user
tells the session the review is done, and the session pulls from GitHub and works through the
comments. Nothing records which passage a comment addressed, whether it was answered, or what
the agent changed in response, and seeing the agent's revisions means reading a GitHub diff.

track-changents, a clean-file track-changes core written by a collaborator (MIT), already solves
the persistence half. A JSON sidecar beside the file holds attributed insert/delete/replace
suggestions and anchored comment threads; four small CLIs, a Claude Code guard hook, and a skill
let an agent write it, and they already attribute by romp's session identity variables. Its
review UIs are an Obsidian plugin and a VS Code extension, neither part of the user's workflow.

This document proposes that romp's file viewer become a host for that sidecar: a Review mode in
the Files pane that shows the agent's pending changes, holds persistent comments on passages, on
images, and on PDFs, sends one review message, and accepts or rejects the agent's revisions in
place. It reaches the loop above with no GitHub visit and no Obsidian, in six independently
useful slices, and keeps the sidecar byte-compatible so the agent-side tooling works unchanged.
It asks the user to approve the slice plan and to answer the open questions at the end. After
approval the implementing session publishes a working note naming the files it owns and lands
each slice as one fork PR with an adversarial review pass, as the file browser did.

Terminology: track-changents' own README calls the JSON file the store; this document says
**sidecar** for the file, **`store-io`** for the module that reads and writes it, **host script**
for the node program the kernel runs, and **owning kernel** for the machine that holds the file.
"Host" alone means an editor host (the Obsidian plugin, the VS Code extension, or this viewer).

## The loop this serves, and the parity bar

Paraphrased from the user's description (the user 2026-09-05):

1. The user gives a session instructions and answers its questions.
2. The user tells it to work overnight and report in the morning.
3. Overnight the session writes or revises a report and files a user todo asking for a review,
   naming the report path in the todo's detail.
4. In the morning the user opens the report from the todo.
5. The user sees the session's pending suggestions: every change not yet accepted or rejected.
6. The user comments on passages, on figures, and on the report's PDFs. The comments persist
   with the files.
7. The user sends the review in one gesture, which also answers the todo.
8. The session addresses the review: it replies into threads and revises text.
9. The user sees the revisions in the same viewer as suggestions and accepts or rejects them,
   singly or all at once.

Two facts about the sidecar shape this loop. First, **tracking must be on for the report before
the session writes it** for step 5 to show anything: the guard passes untracked files straight
through, so an untracked report is written raw, no sidecar exists, and the first morning is
comments-only. The design therefore lets the user track a folder before its report exists, and
makes Send review turn tracking on when it is off. Second, **the sidecar keeps no history**:
accepting a suggestion drops it and rejecting one reverts it, so "what changed since the last
review" can only mean "what is still pending". A review is closed by resolving its suggestions;
what stays pending is what the next morning shows, mixed with the night's new edits.

**Parity bar.** Steps 4 through 9 complete inside romp's Files pane, on the disk the session
works on, with no GitHub tab and no Obsidian window, and every comment, reply, and suggestion
lands in the same `.trackchanges/` sidecar the track-changents CLIs, guard, and skill already read
and write, unchanged. GitHub remains a read-only pointer through the viewer's existing GitHub
link; the loop never depends on it.

## What the dashboard already does for this loop

Verified against this fork on 2026-09-05.

- **Steps 1 and 2** need nothing: the chat composer's `sendMessage` op (`kernel/kernel.py:11954`)
  and POST `/send` (`kernel.py:37689`) carry human-to-agent text on every backend, through
  `_send_or_park` (`kernel.py:22180`), which revives a dormant SDK session.
- **Step 3** works when the gear's User todos switch is on. The postal `add_user_todo` tool files
  the todo (`postal/postal_service.py:2984-2989`, POST `/usertodo`, `_add_user_todo` at
  `kernel.py:3584-3603`), and its description promises that a file path in `detail` becomes an
  openable link. The switch is per install and default OFF (`kernel.py:4855-4884`).
- **Step 4** half works. The chat's todo card and its Reply modal linkify the detail path through
  `linkifyFileUris` and `openPath` (`ui/webview/render.ts:3041-3046, 1411, 966`), and `openPath`
  lands in the Files pane when it is open. The cross-session Waiting-on-you pane, the surface a
  morning reviewer looks at, renders the detail as plain text in the row and in its Reply modal
  (`ui/webview/waiting.ts:209, 126-127`). The pane is its own iframe with none of the chat's
  routing state, and `render.ts` exports nothing, so the linkifier cannot simply be imported.
- **Step 5** has no surface. The viewer renders the current bytes of one file (`renderBody`,
  `ui/webview/file-view.ts:554-563`) over GET `/file`, which stamps `X-Romp-Mtime-Ns`
  (`kernel.py:36819-36883`). Nothing in romp reads a `.trackchanges/` sidecar.
- **Step 6** is ephemeral. Selecting a passage mints a `path:line` quote chip
  (`file-view.ts:565-626`, `ui/webview/docreview.ts:28-60`); Cmd-Enter stages several; Enter
  sends them as one message. The viewer's own per-file comment store was retired on 2026-08-23 in
  favor of chips (`file-view.ts:248-262`).
- **Step 7** half works. Reply on the todo posts `userTodoAnswer`, whose handler checks the
  switch, the todo's openness, and the session's liveness, sends through `_send_or_park`, and
  stamps the todo answered itself on an immediate send or lets a parked send stamp when it drains
  (`kernel.py:12198-12250, 22392`). Nothing ties staged notes to it.
- **Step 8** works once track-changents' `install.sh` has run on the session's machine (it is not
  installed on the user's machine as of 2026-09-05). romp's SDK backend leaves the SDK's
  `setting_sources` unset, and the installed SDK (0.2.95, `ClaudeAgentOptions.setting_sources`)
  documents that as loading all sources, matching the CLI's defaults, so the user-level guard hook
  and the tracked-changes skill apply; Slice 1 confirms this on a live session. `ROMP_SESSION_NAME`
  and `ROMP_SID` become the author label and stable id (`kernel/sdk_backend.py:7169-7176`; the
  tmux launch line in `bin/romp`), and both names are reserved against per-session env overrides.
  Because agent and dashboard share the owning kernel's disk, the pull from GitHub is already
  unnecessary.
- **Step 9** has no surface.
- Two substrates matter for the design. Editing: Edit mounts a lazily loaded CodeMirror 6 chunk
  (`ui/webview/editor-chunk.ts`) and Save rides `saveFile` to `_save_file`
  (`kernel.py:30673-30749`): a server-side consent gate (`_file_editing_on`,
  `kernel.py:4752-4764`), existing UTF-8 text files only, a 2 MB cap (`_TEXT_MAX_BYTES`,
  `kernel.py:30554`), a nanosecond mtime fence, and an atomic replace, followed by an edit trace
  telling the session whose cwd contains the file that a human edited it
  (`kernel.py:30815-30827`). Dispatch: POST `/fork-comment` and `/fork-promote`
  (`kernel.py:10981-11052, 37743-37755`) were built on 2026-08-31 for exactly this plugin's review
  comments and have no caller yet.

### Why this is not the retired comment layer

The viewer's 2026-08-23 consolidation removed a browser-local comment store because batching
notes for one hand-off is what quote chips already do. This proposal does not bring that store
back. The sidecar is a file on disk in the user's repo, attributed per author, read and written by
the agent's own tools and by two other editors, and it carries the agent's revisions as well as
the human's comments. The chips stay for one-off notes on untracked files; Review mode is for a
document under review.

## Shape of the feature

A **Review mode on the file viewer**, entered from the viewer's action row, with a **review
panel** beside the viewer body in the Files pane column, folding below it when the column is
narrower than the two-column minimum. Four structural choices, each with a precedent in this
repo:

1. **The sidecar is track-changents v3, byte for byte, plus one optional field for regions.**
   romp mints no second schema. That is what keeps the agent half (CLIs, guard, skill) and the
   other two hosts working unchanged, and it is what keeps the romp side small. The one addition,
   an optional `target` on a thread for image and PDF regions, follows the contract's own rule
   for additive fields (see The contract).
2. **The kernel does the disk work, on the owning kernel, by running a small node host script
   built on track-changents' own `store-io` and engine.** The browser renders JSON and never
   holds a sidecar it writes back. This is the `listDir`/`saveFile` shape: a sid-routed WebSocket
   op, so a remote session's file works with no new relay code (`ui/webview/federation.ts:53,
   278-288`).
3. **The UI enters through the viewer's action registry** (`registerFileViewAction`,
   `file-view.ts:181-192`, the GitHub link's seam): mounted hidden, revealed when the kernel
   answers. A file with no tooling behind it never shows Review, the GitHub link's
   absent-until-verified pattern, and the gear says why (see Getting into it).
4. **Change awareness by polling, not a watcher.** HEAD `/file` on the report and on the sidecar
   every 2.5 s while the panel is open, comparing `X-Romp-Mtime-Ns` as strings. `CLAUDE.md`
   prefers the event to the timer; the human's own writes need no poll, since every review verb
   answers with fresh state, and agent writes have no event source without a filesystem watcher,
   which the file-browser plan deferred. The poll stands in for that missing event and is close
   to the Obsidian host's 2 s sidecar poll.

## The contract: the track-changents sidecar

One JSON file per tracked file at `<root>/.trackchanges/<encodeURIComponent(relpath)>.json`
(track-changents `README.md`, "The sidecar store"): `v: 3`, `id`, `path`, `suggestions[]` as
insert/delete/replace ops in current-text coordinates, each with `author`, optional `authorId`,
`ts`, and an `anchor {prefix, quote, suffix}`; `comments[]` as threads with `id`, `author`,
`body`, `ts`, `replies[]`, `resolved`, an optional `anchor {quote, prefix, suffix}` for a passage
comment, and an optional `suggestionId` binding the thread to an op; a top-level `detached[]` of
ops the load-time rebase could not re-place, which a host preserves and shows rather than drops;
and a `fingerprint` over the current text. A thread is a change thread when `suggestionId` is
set (the README calls it the cross-editor key, and the Obsidian host classifies on it); a passage
thread keeps its anchor and gains a `suggestionId` when the agent answers it with `track-edit
--thread`, and is then shown on the change's card. The VS Code host classifies on the absent
anchor instead (`vscode/src/panel.ts:206`), so it shows such a thread as a passage comment; a
thread written by the CLIs has exactly one of the two fields until then. The file on disk is
always the current text with every suggestion applied. The root is the nearest `.obsidian/`,
`.git/`, or `.trackchanges/` ancestor. The single on/off control is `.trackchanges/config.json`
`{v: 2, tracked: [...]}`: a path tracks one file, a `folder/` entry tracks everything under it,
and an optional `untracked: [...]` veto with the same shapes wins over both the list and the
link-closure inheritance (`store-io.mjs:87-98, 190-192`). `.trackchanges/` is committed with the
repo.

Four properties of the contract shape the design:

- **A thread with neither anchor nor `suggestionId` is valid and means a comment on the file as
  a whole.** The schema marks `anchor` optional (README, thread shape), `store-io` passes such a
  thread through untouched, `track-reply` replies into it, the engine's comment pruning keeps it
  (`engine.js:827-833`), and both existing hosts render it as a plain discussion card (VS Code at
  the top of the panel, Obsidian at the bottom). The Obsidian host already writes this shape for a
  message with no selection. Only `track-comment` cannot create it, since it requires `--anchor`;
  the host script builds the thread itself. This is how comments on standalone images and PDFs
  are stored in Slice 1.
- **One optional field, `target`, carries a region.** `target: {kind: "image"|"pdf", region: {x,
  y, w, h}, page?, hash}` with the rectangle in fractions of the rendered page or image, `page`
  1-based for PDFs, and `hash` the sha256 of the file's bytes so a regenerated figure marks its
  region threads stale the way a moved text anchor does. The text anchor stays absent for a
  standalone image or PDF, so the other hosts show the thread as a discussion card and preserve
  the field (both write the whole object back). For a figure embedded in a report, the thread
  carries both the anchor on the embed's source line, which every host can place, and the
  region, which this viewer paints on the rendered image. The README's version rule says to bump
  `v` only for a breaking change; an optional field older readers ignore is not one. Documenting
  the field in the track-changents README is a dependency on its author.
- **A file created through `track-edit` is one insertion** spanning the whole file, and while any
  same-author insertion is pending, that author's further edits inside or beside it coalesce
  into it (`engine.js:204-218`) and do not appear as separate changes. A morning review of a
  report the session created under a tracked folder therefore begins with one card covering
  everything; accepting it is how the session's later revisions become separate suggestions.
- **A corrupt or newer-version sidecar must be refused, never replaced.** Two CLIs today replace
  it, `track-edit` and `track-comment` (item A2 of the 2026-09-03 track-changents survey, a
  session note outside both repos; every item relied on is restated here); `track-reply` fails
  instead, unless a `.superseded` park holds the thread, in which case it revives over the
  corrupt file. The host script loads through `loadStoreStatus` (`store-io.mjs:286`), never
  through `loadStore` or `ensureStore`: `loadStore` returns null for corrupt, unsupported, and
  absent alike (`store-io.mjs:302-304`), and `ensureStore` and `track-comment` then mint a fresh
  sidecar over that null (`store-io.mjs:413-418`, `cli/track-comment.mjs:76-79`). The host script
  also never calls `reviveThreadFromSuperseded` (survey A1: replying into a thread that survives
  only in a park overwrites the live sidecar with an empty suggestion list).

Binary files: the CLIs read every file as UTF-8 text. `track-comment` and `track-reply` operate
on an image or PDF and write a valid, deterministic sidecar without touching the file, but
`track-edit` rewrites the file from the lossy decode and destroys it. The guard would steer an
agent toward `track-edit` on a tracked image. A non-text refusal in the guard and in `track-edit`
is therefore a dependency on the author before folders that hold figures are tracked.

Human authorship uses the label `you` with no `authorId`, matching the VS Code host's default;
see open question 6.

## Kernel: two ops and a host script

Both ops echo a client-minted `reqId`, route to the owning kernel by `sid`, and answer on the
sending socket, the `listDir`/`saveFile` pattern (`kernel.py:39531-39558`). All mtimes travel as
strings.

**`trackReview`**, the disk op:

```
request  {type:"trackReview", reqId, sid, path, verb, args?,
          fence?: {storeMtimeNs: str|"", fileMtimeNs?: str, configMtimeNs?: str|""}}
reply    {type:"trackReviewResult", reqId, verb, root, storePath, trackedBy,
          fileMtimeNs, storeMtimeNs|null, configMtimeNs|null, store|null, hunks, baseline?}
refusal  {type:"trackReviewFailed", reqId, verb, code, error}
```

`store` is the sidecar as loaded and normalized (with `detached[]`), or null when absent.
`hunks` is `engine.toHunks(store.suggestions)`: one row per op with `id, author, ts, kind,
curFrom, curTo, baseFrom, baseTo, oldText, newText, anchor`, sorted by offset. `baseline`, the
clean text with every suggestion rejected (`engine.baselineOf`), is the whole file and is returned
only when the request asks for it. `trackedBy` is `{kind: "file"|"folder"|"inherited", entry}` or
null, so the panel can say which `config.json` entry covers the file. `configMtimeNs` is null
when `config.json` does not exist; the client sends `""` for null, the same convention as
`storeMtimeNs`. The browser builds its cards from `store` and `hunks`; no card model crosses the
wire.

Verbs by slice. Slice 1: `status`; `set-tracked {on, scope: "file"|"folder"}`, where `folder`
writes `<dir>/` (refusing the root) so a folder can be tracked before its report exists, and
`off` removes the covering entry when its kind is `file` or `folder` (a folder asks a pane-local
confirm naming it) and refuses `tracked-inherited` when the file is covered only through link
inheritance, naming the parent note; `comment {anchor?, note, hintOffset?, target?}` (anchor
present for a passage, absent for a file-level comment, `target` from Slices 3 and 4);
`reply {threadId, note}`; `resolve {threadId, on}`. Slice 2: `accept {ids}`, `reject {ids}`,
`accept-all`, `reject-all`. Slice 5: `save {content, ops}`. Every mutating verb (all but
`status`) carries a fence: `storeMtimeNs` must equal the sidecar's current mtime, with `""`
meaning the sidecar must not exist yet, so two browsers cannot both create it; `reject`,
`reject-all`, and `save` also fence on `fileMtimeNs`; `set-tracked` fences on `configMtimeNs`
the same way, since it writes `config.json`, not the sidecar, and the host script stats
`config.json` before and after inside the same process. A moved fence refuses, and the client
re-issues `status`, re-renders, and retries by stable op or thread id, surfacing a second refusal
verbatim. Nothing merges.

Refusal codes name the resolved path, tilde-collapsed: `no-host` (tooling absent on the owning
kernel; `status` returns it quietly and Review never appears), `no-node`, `no-root`,
`editing-off` (an `error` containing the phrase "file editing is off", the regex the viewer
already matches, phrased for review: cannot write the review for the file, dashboard file
editing is off on this machine), `store-moved`, `file-moved`, `config-moved`,
`unsupported-version`, `corrupt`, `unreadable` (with the OS error text), `anchor-not-found`,
`anchor-ambiguous`, `tracked-inherited`, `no-thread`, `too-large`.

Kernel work, about 150 lines including the send op below: resolve `path` with
`_resolve_open_path` (`kernel.py:30654`); refuse mutating verbs while `_file_editing_on()` is
false, before any content check; run `node <host script>` with the request on stdin, argv as a
list, a 10 s timeout, in a thread as `fileGitLink` does so the receive loop never blocks (the
`_git_out` discipline, `kernel.py:30830-30838`; the kernel already spawns node for its own bundle,
`kernel.py:5391`); parse one JSON object from stdout; a non-zero exit or bad stdout becomes
`trackReviewFailed` with the stderr tail. The kernel never exports `TRACKCHANGES_ROOT` (it would
override every file's root for the CLIs, survey item A8). The authenticated `/defaults` payload
the gear already reads reports the review verdict per kernel (`ok`, `no-host`, or `no-node`), not
`/version`, which is served before authorization.

**The host script** (`tools/track-review-host.mjs` in this repo, about 250 lines; see open
question 3 for the alternative home) finds the track-changents checkout as
`dirname(dirname(realpath(~/.claude/hooks/track-edit.mjs)))`, since `install.sh` symlinks
`~/.claude/hooks/track-edit.mjs` to `<checkout>/cli/track-edit.mjs`, or through a new romp-defined
override for installs that never ran `install.sh` (track-changents defines only
`TRACKCHANGES_ROOT` and `TRACKCHANGES_SESSION`). It imports `store-io.mjs`, `engine.js`, and the
`addReply` function of `cli/track-reply.mjs` by file URL from that root (the package's exports
map covers `./store-io` and `./engine` but not `./cli/*`). It performs each verb as one
load-mutate-write in a single process: root discovery, sidecar path, the load-time rebase that
re-places ops after external edits, anchor location, thread construction, accept and reject
through the engine, fingerprint, atomic write, prune-when-empty. For `comment` it builds the
thread object itself in `addComment`'s exact shape (`cli/track-comment.mjs:38-46`: id
`${now}-${idx}`, `author`, `ts`, `anchor`, `body`, `replies: []`, `resolved: false`, with
`author` passed as `you` and no `authorId`; `addComment` itself anchors at the first occurrence
and cannot take an offset, so it is not reused), and seeds a missing sidecar as `{v: 3, path,
suggestions: [], comments: []}` exactly as `track-comment` does. For a passage comment it re-reads
the file and runs `engine.locateAnchor` on the fresh text with the anchor the browser built from
the displayed text, hinted by the start offset; it saves only when the located text equals the
quote, rebuilding the anchor at the located position, and refuses `anchor-not-found` when the
passage is gone and `anchor-ambiguous` when two candidates tie. Reject writes the sidecar first,
then the file, and restores the prior sidecar bytes (or removes the sidecar it created, when none
existed) if the file write fails, the order `track-edit` uses (`cli/track-edit.mjs:108-128`); its
file write is atomic (temp file and rename in the same directory, through the realpath, mode
preserved) and applies the same 2 MB and UTF-8 checks as `_save_file`, refusing `too-large`
before any write. The host script's accept verbs never drop a thread bound by `suggestionId`;
they set `resolved: true` on it, a stated divergence from the Obsidian host's accept-all, kept so
the thread ids in a review message stay addressable by `track-reply`.

**`trackReviewSend`**, the ping op:

```
request  {type:"trackReviewSend", reqId, sid, path, tracked, threads:[{id, desc, body}],
          accepted, rejected, todoId?}
reply    {type:"trackReviewSent", reqId, queued}
refusal  {type:"trackReviewSendFailed", reqId, error}
```

`tracked` is the client's post-toggle `status` verdict and picks the second bullet of the message.
`desc` is the first 40 characters of the passage for an anchored thread, the change's old and new
text for a thread bound by `suggestionId`, "this file" for a file-level thread, and "the region
at x, y, w, h" (with the page for a PDF) for a region thread. `body` is the thread's unsent `you`
turns joined with a blank line, oldest first; a thread whose opening was already sent lists only
its new replies. The kernel builds the message below and marker-neutralizes the path and every
body (`_neutralize_romp_markers`, `kernel.py:30786-30798`). Delivery follows the `userTodoAnswer`
handler (`kernel.py:12198-12250`) in its order and its ended-session refusal, factored into one
helper both ops call with a flag, and deviates on purpose where a review is worth sending without
a stamp: with the user-todos switch off, the review is sent, nothing is stamped, and the reply
warns with the switch's own reason; with the todo already settled, the review is sent, nothing is
stamped, and the reply warns naming the todo (the handler sends nothing in both cases, and keeps
doing so for its own op); an ended session refuses with the existing revive-the-session text and
sends nothing. Otherwise the helper calls `_send_or_park(be, sid, body, echo="human" if be is
_TMUX else None, user_todo=todoId)`, the handler's own call: a "parked" result replies `queued:
true` and stamps when the batch drains (`_deliver_send_batch`, `kernel.py:22392`), a truthy
result stamps at once through `_stamp_user_todo_answered`, and a falsy result fails the op.
Without a `todoId` the same truthy-or-falsy split decides sent or failed. The review body is not
wrapped in the handler's "Re:" form; it is its own message. The review is already on disk before
any send, so a refusal loses nothing.

### The Send review message

The `[obsidian-diff]` shape the skill handles (`skill/SKILL.md:121-133` for the shape, `:85-91`
for the command lines), written in the person's voice like every injected body, batched:

```
[obsidian-diff] I left 3 comments on <absPath>.

Thread <id1> (on "<quoted passage>"):
<body>

Thread <id2> (on your change "<old>" to "<new>"):
<body>

Thread <id3> (on the region at 0.12, 0.40, 0.35, 0.20 of page 2):
<body>

I accepted 4 of your changes and rejected 1.

To respond:
  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file <absPath> --thread <id> --note "<your reply>"
  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file <absPath> --thread <id> --old "<exact text>" --new "<replacement>"

When you have addressed these, ask me for another look the same way you asked for this review,
naming the file.
```

The format is modeled on the VS Code host's `buildThreadPing` (`vscode/src/dispatch.ts:519-533`)
but is romp's own text. It keeps what the skill describes: the `[obsidian-diff]` prefix, the
absolute path, a thread id per thread, and the exact `track-reply` and `track-edit --thread`
command lines. The tracking-on second bullet restates the skill's own instruction, since no host
emits one today (the VS Code bullet says to edit normally, and the Obsidian host's ping is a stub
in its repo). With `tracked` false the second bullet becomes the VS Code host's wording: edit the
file normally and note it with `track-reply`. For an image or PDF the second bullet says to
regenerate the file with normal writes and never to run `track-edit` on it; the agent can read
images and PDF pages directly. The closing sentence is what brings the loop back: the session's
next todo is the return signal. The text names no romp machinery; `tests/test_injected_voice.py`
gains the ping body and the review trace body in its rendered set. The skill's ping paragraph
should gain one sentence saying a ping may list several threads (a change in the track-changents
repo, by its author).

### Consent, trace, routing

Every verb that writes disk, sidecar included, sits behind the file-editing consent
(`kernel.py:30695-30700`): one mental model, the dashboard may write files on this machine, and
the sidecar is a committed file in the user's repo. The first review triggers the existing popup
once. That popup's copy promises the session is told when the user edits under it
(`file-view.ts:460-463`); Slice 1 amends it for the review case, since comments reach the
session only when the review is sent (open question 5).

Verbs that change file bytes (`reject`, `reject-all`, `save`) send a review-specific trace to the
session whose cwd contains the file, first person like `_edit_trace_body`: I rejected N of your
tracked changes in the file while reviewing it; the file and its sidecar both changed, so re-read
before writing. Sidecar-only verbs send nothing; the Send review message carries the news, and
the CLIs read the sidecar on every call. Host-script writes never pass through `saveFile`, so the
generic `_edit_trace` is untouched; a sidecar hand-edited in the viewer traces like any other
file, as the never-lose-the-thread rule requires.

Both ops carry `sid`; `routeOutbound` routes any op with a scalar id field to the owning kernel
and strips the prefix (`federation.ts:53, 278-288`), so a `host:sid` file's review lands on the
kernel that owns the disk. The sidecar's bytes reach a remote browser over the same
`/remote/<host>/file` relay the report does, which mirrors the mtime header on HEAD
(`kernel.py:39930`).

## UX

### The surface, in its Slice 2 state

```
┌ Files ──────────────────────────────────────────────────────────────────────────────┐
│ ~/code/notes-api/docs/report.md   Rendered · Raw   Edit   GitHub ↗   Review · 5 changes · 2 comments   ✕ │
├───────────────────────────────────────────────────┬──────────────────────────────────┤
│ ## Findings                                       │ Track changes [on]  Send review (3) │
│ The api session ~~reduced~~ cut p95 latency       │ ──────────────────────────────── │
│ by 40% ▍web                                       │ ▍web  "reduced" to "cut"         │
│ ...                                               │       [Accept] [Reject] [Reply]  │
│ We recommend ▌shipping the cache in v1.2.         │ ▍you  on "shipping the cache…"   │
│                                                   │       Which cache? Say which.    │
│                                                   │       ↳ web: The response cache. │
│                                                   │       [Reply] [Resolve]          │
│                                                   │ Accept all · Reject all          │
└───────────────────────────────────────────────────┴──────────────────────────────────┘
```

- **Progressive disclosure**: the action-row label is the glance, the panel is one click, a
  thread expands on click, keyed by thread id in a set that survives the poll's re-render. For a
  file under a root with neither sidecar nor tracked flag the action reads plain "Review" and the
  panel holds only the Track changes toggle (file or folder); counts and highlights appear once a
  sidecar exists.
- **Raw view is exact, Rendered view is best effort.** Ops are offsets into the source. In Raw,
  insertions tint, deletions render struck at their point, substitutions show both, each with the
  author's session chip in the session's color. In Rendered, insertions and substitutions are
  re-found by their text and highlighted; a deletion cannot be placed in rendered prose and
  appears only as a card, whose **Reveal** switches to Raw and scrolls there. An unpainted hunk
  always has a card, so the compact view never dead-ends. Session colors come from one
  `GET /sessions` fetch per panel open, mapping `authorId` to name and color; an author with no
  live match gets a neutral chip with its label.
- **Comment on a selection**: selecting a passage still seeds the quote chip when a chat composer
  is reachable; in Review mode a floating **Comment** button also appears beside the selection's
  bounding box (the chip lives in another iframe, so "beside the chip" is not possible), and the
  selection hook runs before the composer gate so it works with no chat pane. The button opens a
  one-line composer in the panel with the quote shown; Enter saves to the sidecar and the
  highlight and card appear at once. The mapping from a selection to a source anchor, in both
  views and every format, is specified in the next subsection.
- **Send review** lists what goes (N comments, M replies, accepts, rejects), confirms once
  pane-locally, disables and relabels itself while sending, then shows "Sent to <session> at
  <time>", or "Queued for <session>" when the reply carries `queued: true`, and keeps polling
  while open. The confirm carries up to three checkboxes, all checked by default: **answer the
  todo** when the file was opened from one; **turn Track changes on** when it is off (file scope),
  so the session's revisions come back as suggestions; and, from Slice 2, **accept the N pending
  changes as reviewed** when suggestions remain, so the session's revisions arrive as fresh
  suggestions rather than coalescing into a pending insertion. The sequence is fixed: the message
  is built from the current sidecar, then `set-tracked`, then `accept-all`, then
  `trackReviewSend` with `tracked` set to the post-toggle verdict; a refusal at any step aborts
  the sequence before the send and shows the refusal. One review per file: when a todo names
  several files, the first send answers it and later sends for the other files show no todo
  checkbox.
- **What counts as unsent.** The sidecar carries no send state (choice 1), so the client keeps a
  per-sidecar ledger in `localStorage` keyed by the sidecar's `id`: `{lastSentTs, accepted,
  rejected}`. `lastSentTs` is set to the largest `ts` among the threads and replies included in
  the send, read from the sidecar, never from the browser clock, since the host script stamps
  `ts` on the owning kernel. A comment or reply counts when its author is `you` and its `ts` is
  after `lastSentTs`; accepts and rejects are tallied by the panel and reset on a successful send;
  a refusal leaves the ledger unchanged. A browser with no ledger offers every `you` thread that
  has no agent reply. The confirm always lists what goes, so a stale count is visible before it
  is sent.
- **Edit while changes are pending** (Slices 1 to 4): the Edit button refuses with a one-line
  reason naming the count of pending changes, because a raw save over pending ops rewrites their
  offsets. In Slice 1 the reason says that accept and reject arrive with the next slice and that
  the session's own `track-edit` still works; from Slice 2 it says to resolve the changes in
  Review first. Slice 5 lifts the refusal.
- **Errors** render inside the panel as an error row under the control that asked, in the
  viewer's `fileview-err` dress; `store-moved`, `file-moved`, and `config-moved` offer Reload. A
  federation `warn` arriving while a review request is outstanding is treated as that request's
  failure with the warn's text. An `editing-off` refusal runs the same confirm-then-consent-then-
  retry branch the viewer's Save uses, lifted into a shared helper (see the seam below).
- **Click-safety**: the panel re-renders on every poll, so its controls delegate to one stable
  root (`actions.ts` `delegate()`) with `flash()` acknowledgement; waits show the romp loader;
  sizes and menu tokens follow `ui/CLAUDE.md`.

### Commenting from either view, and in every format

Commenting works in whichever view the user is reading. The viewer has two views of text: Raw,
which every text format has (markdown, HTML, XML and SVG source, CSS, code, CSV, JSON, logs, and
the rest of the kernel's text allowlist), and Rendered, which only markdown has. HTML is never
rendered by the viewer (the kernel serves it as plain text and the file-browser plan records that
stance), so commenting on HTML means commenting on its source. Images and PDFs have no text view;
their commenting is covered below and in Slices 3 and 4.

A comment made from a selection in either view is stored with an anchor whose quote is an exact
substring of the file text the host script read, so the agent CLIs, the sidecar's re-anchoring
on load, and the two existing editor hosts treat it the same as a comment written by the comment
CLI. The browser builds the anchor from the displayed text with the engine's `makeAnchor` (the
quote plus 24 characters of prefix and suffix) and sends it with the note and the start offset;
the host script re-reads the file and locates the anchor with the engine's `locateAnchor`, hinted
by that offset, and refuses when the located text differs from the quote or two candidates tie.
The typed note is never discarded by a refusal.

In Raw view the mapping is exact. Each logical line is one row whose text equals the source line
(the viewer always soft-wraps, and the row number is CSS content that never enters a selection),
so a selection endpoint becomes a line index and a column from the row's text nodes, the pair
becomes a source offset range, leading and trailing whitespace is trimmed, and the quote is the
source slice with its interior line endings. A selection that reaches outside the rows snaps to
the first or last row when its container is an ancestor of the code element, and refuses
otherwise. The self-check compares the text-node concatenation of the untrimmed range with the
source slice minus its line endings, exactly.

In Rendered view the browser rebuilds the rendered text from the source with the same markdown
lexer the viewer renders with, recording the source index of every character it emits and
verifying every token's source text at the position the walk assigns it; a block whose tokens
cannot be placed refuses rather than yielding a wrong quote. The walk drops the marks the
renderer consumes: heading hashes, list bullets and indentation, blockquote markers, emphasis and
strong delimiters, inline code backticks, link brackets and destinations, backslash escapes,
reference definitions, hard-break spaces and backslashes, and task-list checkboxes. A top-level
block counts as aligned only when its text with all whitespace removed equals the corresponding
rendered element's; the comparison ignores whitespace entirely because the renderer's line breaks
carry no text. A selection whose endpoints fall in aligned blocks maps back to a source range,
and that source slice is the quote; endpoints in the whitespace between blocks snap to the
nearest block edge. Fenced and indented code, tables, HTML blocks, prose blocks containing HTML
entities, link labels with escaped brackets, list or blockquote lines that begin with a tab after
the marker, and any block that fails alignment refuse in Rendered view. A selection spanning two
aligned blocks is accepted, and its quote includes the blank line and block markers between them,
which the composer shows before saving. A selection whose edge falls inside a mark the renderer
consumed paints narrower in Rendered than in Raw, never wider.

When the mapping refuses, the composer keeps the typed note, states the reason in one line, and
offers a switch to Raw that preselects the same passage when its text occurs in the source (code
fences) and otherwise opens scrolled to the block's first line with the note intact (tables and
HTML blocks).

Painting distinguishes three states after the engine locates a thread's anchor in the current
text: located at the quote, painted normally; quote gone but its context found
(`engine.js:793-800`), painted over the between-context region in a text-changed style with a
card; neither found, shown as a card only, marked detached in the panel. Detached is a rendering
state here, not a stored flag; the host script never calls the engine's comment pruning, and the
thread stays in the sidecar. In Raw view a located thread is painted by offset over the line
rows, with no text matching. In Rendered view the located source range is converted through the
same index map to a highlight over the rendered text; a thread inside a refused block falls back
to a whitespace-tolerant match of its quote stripped of inline markup, and a thread that cannot
be painted has a card whose Reveal switches to Raw and scrolls to the passage.

Images and PDFs. A figure embedded in a markdown report is commented on through its embed line:
in Rendered view a click on the rendered image offers Comment, the anchor is the embed's source
text, and the highlight is a frame around the image; in Raw view the embed line is text like any
other. A standalone image or PDF opened in the viewer offers a **Comment on this file** button in
Slice 1, which writes a file-level thread (no anchor, no `suggestionId`) to the file's own
sidecar; it renders as a card in every host and the agent replies to it with `track-reply`.
Region comments, drawn as a rectangle on the image or on a PDF page, arrive in Slices 3 and 4
with the `target` field.

Acceptance criteria:

- Raw: for every pair of source offsets in a fixture with CRLF line endings, leading tabs,
  highlighted syntax, and a trailing newline, whose end characters are non-whitespace, a DOM
  selection constructed at those offsets (each end tried as a text-node boundary and as an
  element boundary) stores a quote equal to the source slice, and the highlight after reload
  wraps exactly the text nodes of that slice. A CR-only line and a selection ending past the last
  row are included.
- Raw: a quote that occurs twice anchors to the selected occurrence, including when two lines
  are inserted above the passage between the selection and Enter.
- Rendered: for a fixture covering both heading styles, tight and loose lists, nested and task
  lists, blockquotes, emphasis, strong, strikethrough, inline code, every link form, images,
  escapes, hard breaks, and a reference definition, every selection inside aligned blocks yields
  a quote whose walk-mapped characters equal the selected rendered characters one to one, and
  painting the stored anchor in Rendered wraps exactly the originally selected text; the reply
  CLI reads the resulting thread unchanged.
- Rendered: a selection touching code, a table, an HTML block, an entity-bearing paragraph, or
  an escaped link label is refused, the note survives, and the Raw offer opens with the passage
  selected when its text occurs in the source, else scrolled to the block.
- Every text format: a comment from the Raw view of an HTML, SVG, CSS, CSV, and code fixture
  stores the exact source slice.
- Both: with the author label held equal, the thread object written from either view
  deep-equals the one `addComment` writes for the same quote and note, apart from id and `ts`;
  the sidecar's suggestions, fingerprint, and version are unchanged.
- Both: after an agent edit moves the passage, the highlight follows the engine's relocation in
  both views; when only the context survives, the text-changed style appears in both views; when
  neither survives, the card shows detached in both views and the thread remains in the sidecar.
- Images and PDFs: a file-level thread written from the viewer is replied to by `track-reply`,
  renders as a card in the VS Code host's loader and the Obsidian host's reader, and the file's
  bytes are unchanged.

### The viewer seam

The panel needs more of the viewer than the registry's `{path, sid}` context gives. Slice 1
extends `FileViewActionCtx` with `todoId?`, `body()`, `mode()`, `text()`, `mtimeNs()`,
`onRendered(cb)`, `onSelection(cb)`, `post(msg)`, `ensureEditingAllowed()` (the first-consent
popup and the re-consent-on-refusal branch, today closures inside `openFileView` and `doSave`,
lifted into one exported helper that Save and the review verbs both call), `setEditBlocked(reason
| null)`, `aside(el | null)` (mounts or removes the panel beside the body; the viewer owns the
two-column CSS and the narrow-column fold), `setMode("raw" | "rendered")`, `scrollToOffset(n)`,
and `reload()` (re-fetch bytes and mtime, re-run `renderBody` and `onRendered`, keep the action
row and panel). The action row itself stays registry-only. `track-review.ts` registers its own
`message` listener for its four reply types.

### Getting into it

- From the Waiting-on-you pane: the todo's detail path is a link (Slice 0). The pane is its own
  iframe, so the link posts `{romp:"viewFile", pane:"pane", path, sid, identity:{name,color},
  todoId}` to the shell, the Files-pane branch that turns the pane on and forwards the message
  (`kernel.py:34486-34493`); the shell forwards `todoId`, `files.ts` passes it to
  `openFileView(path, sid, {todoId})`, and relative paths resolve on the kernel through
  `_resolve_open_path`. When the pane is not framed by the shell, the detail stays plain text.
- From the viewer: the Review action, for any file under a track-changents root on a machine
  whose kernel reports the tooling. If Review is missing, the gear's row beside "File links open
  in" names the machine and the reason (`no-host` or `no-node`), and the guide says to look
  there.
- From the chat: a file link on a tracked file opens the viewer as today; Review is one click
  further.
- An ended session's todo is hidden from Waiting on you until the session is revived, since the
  board lists living sessions only and gates ended ones (`kernel.py:25738, 26082-26087`; the
  chat's own card gate is at `24047-24062`), so the morning entry point can vanish; the report is
  still on disk and Review works on it without a todo. The guide says: if a review you expected
  is missing, check the session list for an ended session.

## Build slices

Each slice is independently useful and lands as its own fork PR with an adversarial review pass.
Sizes are approximate new lines, webview TypeScript / kernel Python / node.

### Slice 0: from the morning todo to the report in one click

User-visible: in the Waiting-on-you pane, a report path in a todo's detail is a link that opens
the file in the Files pane; the Reply modal shows the same link. The review itself is today's
quote-chip flow, and Reply on the todo is the done gesture. This alone removes the GitHub detour
for a comments-only review, without persistence.

Acceptance: both `waiting.ts` render sites (`:209`, `:126-127`) turn the detail's path into a
link that posts the `viewFile` message above; the shell forwards `todoId`; relative paths resolve
against the todo's session on the kernel; `ui/webview/user-todo-links.test.ts` pins the posted
payload and both callers of the shared matcher.

Files: `render.ts` exports nothing and is the chat entry, so the path-token matcher
(`CLICKABLE_PATH_RE`, `looksLikeFilePath`, `looksLikeBareFileName`, `fileUriToPath`, the
trailing-punctuation trim; `render.ts:1338-1520`) moves into a new `ui/webview/path-links.ts`
that emits `.file-uri-link` spans carrying `data-act="openpath"`, `data-path`, and `data-sid` and
binds nothing; `render.ts` re-imports it and keeps its previews, its own listener, and
`openPath`; `waiting.ts` adds `openpath` to its existing delegate handler map and one direct
listener in the static Reply modal, since its rows are rebuilt on every feed frame; the shell
relay's forwarded object gains `todoId`; `file-view.ts` gains `openFileView(path, sid, opts?:
{todoId?})` and `FileViewActionCtx.todoId?`; `files.ts` passes `m.todoId` through; `docs/guide.md`.
Size: ~100 to 200 / ~10 / 0.

### Slice 1: persisted comments, the tracking toggle, one Send review

User-visible: the Review action; the panel with a Track changes toggle (file or folder) and
thread cards; Comment on a selection in either view of any text format; Comment on this file for
a standalone image or PDF; highlights in both views; replies from `track-reply` appearing within
the poll interval; Send review as one message with two of the confirm checkboxes (answer the
todo, turn Track changes on); the Edit refusal while suggestions are pending; the gear row
reporting the review verdict.

Acceptance: the criteria under Commenting from either view; a first comment on a clean file
creates `.trackchanges/` and the sidecar exactly where `storePathFor` puts it; the toggle writes
`config.json` through `setTracked`, fenced on `configMtimeNs`, and `off` on an inherited file
refuses `tracked-inherited`; a mutating verb on a moved sidecar refuses and the panel reloads and
retries; the Send review text carries the `[obsidian-diff]` prefix, the absolute path, and each
thread id in the form the skill describes, and the kernel and webview builders produce identical
text for one and for several threads; a send with `todoId` follows the helper's branches (switch
off, settled, ended, and the send arm's parked, sent, and refused outcomes); the first mutating
click triggers the consent popup once; on a live SDK session the guard denies a raw Write on a
tracked fixture and `track-config` answers.

Files: new `ui/webview/track-review.ts` (registration, panel, highlight pass and the two mapping
walks, Comment button, poll, ledger, send composer), `tools/track-review-host.mjs` and its node
tests, `tests/test_track_review.py`, `ui/webview/track-review.test.ts`; touched:
`kernel/kernel.py` (the two ops, the shared todo-answer helper, the `/defaults` verdict),
`file-view.ts` (the seam above), `files.ts` (the `/sessions` color map), `gear.js` (the verdict
row), `styles.css` and `files-pane.css` (about 80 lines adapted from the Obsidian host's
stylesheet, mapped to `--accent`, `--bg`, `--fg`), `docs/guide.md`. track-changents code reused
unchanged: `store-io.mjs`, `engine.js` (`makeAnchor`, `locateAnchor`, `toHunks`, `baselineOf`),
`addReply`. Size: ~600 to 750 for `track-review.ts` (the Rendered walk is the largest part) plus
~110 to 140 for the seam and ~30 for `files.ts` and the relay / ~150 / ~250, plus about 150 lines
of tests on each side.

### Slice 2: the agent's changes as accept/reject cards and inline marks

User-visible: change cards grouped by paragraph with Accept, Reject, Accept all, Reject all, and
a Reply bound to the change so the agent's `track-edit --thread` revisions fold into it; inline
marks in Raw, highlights in Rendered, Reveal for deletions; Send review states accepts and
rejects and offers the accept-as-reviewed checkbox.

Acceptance: accept changes the sidecar only (the engine's `acceptSuggestions`) and marks bound
threads resolved without dropping them; reject applies the engine's reverse edits to the file
and writes sidecar then file with rollback; both fence on the sidecar mtime and reject also on
the file mtime; after a reject the owning session receives the review trace; a `track-edit`
landing mid-review makes the next Accept refuse and reload; accept-all on a file with no comments
prunes the sidecar as `pruneIfClean` decides; a sidecar holding one whole-file insertion renders
one card whose Accept clears it.

Files: `track-review.ts` (the card model ported from the VS Code host's `buildCards`,
`vscode/src/panel.ts:194-300`, and its `weave` and `awaitState` helpers at `:301-351`; the port
replaces its two host inputs, the `vscode.TextDocument` and the configured label, with the
current text and `you`, and adds the buttons that panel deliberately lacks; the Raw painter over
the viewer's line nodes), CSS (about 120 lines), `kernel.py` (trace after reject), host script
verbs. Reused unchanged: `engine.js` accept/reject (`engine.js:388-419`), `display.js`
`planDiffDisplay`; adapted: `applyEditsToText` (12 lines from `obsidian/src/track-rollup.js`).
Size: ~400 / ~40 / ~120.

### Slice 3: region comments on images

User-visible: on a standalone image, or on a figure embedded in a rendered report, the user
drags a rectangle and comments on it; the rectangle paints over the image with the author's
chip, and the card shows a thumbnail crop. When the image's bytes change, its region threads
show as stale until resolved or re-placed. The review message names the region.

Acceptance: a region thread carries `target {kind: "image", region, hash}` in fractions of the
image's natural size, plus the embed-line anchor when the figure is embedded, and no anchor when
standalone; `track-reply` replies into it; the Obsidian and VS Code hosts show it as a discussion
card (embedded: on the embed line) and preserve `target` on their next write; a regenerated image
flips the thread to stale by `hash`; the rectangle re-paints correctly at any viewer width.

Files: `track-review.ts` (the overlay, the drag, the crop), `file-view.ts` (a hook exposing the
rendered image elements), the host script (`comment` accepts `target`; `hash` computed from the
bytes), `kernel.py` (none beyond passing the field), CSS. Dependency: the `target` field
documented in the track-changents README by its author; the non-text refusal in the guard and
`track-edit`. Size: ~250 / ~10 / ~40.

### Slice 4: PDFs rendered in the viewer, with page and region comments

User-visible: a PDF opens as rendered pages inside the viewer instead of the browser's own frame,
with the same Comment on this file button and the same rectangle gesture per page; a region
thread names its page; the card shows the page crop.

Why a slice of its own: the browser's PDF frame gives the page no coordinates or selection, so
region comments need romp to render pages itself. Recommended: a lazily loaded PDF chunk built
on pdf.js (Apache-2.0, matching romp's license), in the same on-demand pattern as the editor
chunk, loaded only when a PDF opens; the fallback for a failed chunk load is today's frame with
file-level comments only. Alternative: rasterize pages on the owning kernel with a command-line
tool and serve page images, which avoids a browser dependency at the cost of a kernel-side tool
and a new route (open question 12).

Acceptance: pages render within the viewer's text cap policy for PDFs (a stated size cap, loudly
refused above it); a region thread carries `target {kind: "pdf", page, region, hash}`; a
regenerated PDF flips its region threads stale; `track-reply` replies into them; the main
bundles stay byte-stable with the chunk lazy.

Files: new `ui/webview/pdf-chunk.ts` esbuild entry, `file-view.ts` (the PDF branch mounts the
chunk when Review is on, else the frame), `track-review.ts` (per-page overlays), the host script
(no change beyond Slice 3), `kernel.py` (a size cap for the chunk's fetch). Size: ~350 / ~20 / 0,
plus the dependency decision.

### Slice 5: live CodeMirror editing over pending changes

User-visible: Edit works on a tracked file with pending changes; CodeMirror shows insertions
tinted and deletions struck inline; typing remaps the ops rather than desyncing them; click
accepts, modifier-click rejects; undo restores an accepted suggestion; Save writes file and
remapped sidecar together, and the Edit refusal disappears.

Acceptance: the cases of track-changents' `obsidian/tests/track-cm.test.mjs` and
`track-cm.undo.test.mjs`, copied into romp with their `createRequire` loads of
`../src/track-cm.js`, `track-changents/engine`, `@codemirror/state`, and `@codemirror/commands`
rewritten to romp's review chunk and its CodeMirror (the tests use Node's own `require`, which a
vitest alias cannot redirect), pass as the behavioral oracle; a save refuses when either mtime
moved and keeps the buffer; `editor-lazy.test.ts` pins that the main bundles stay byte-stable.

Files: `editor-chunk.ts` (a typed `track` mount option curated inside `extensionsFor`,
`editor-chunk.ts:113-135`, consumed only by `file-view.ts`; the header doctrine comment names
it), a new lazy `review-chunk` esbuild entry bundling the engine, the 78-line CodeMirror state
field (`obsidian/src/track-cm.js`, unchanged), the decorations block
(`obsidian/src/track-snapshot.js:433-839`) together with `obsidian/src/track-logic.js` (215
lines of display-planning and click and layout helpers the block calls), with the one Obsidian
read at `:595-596` replaced by a constant and the `mouseover` handler at `:774-781` fixed to take
the editor view (survey A6), `file-view.ts` `doSave` sending the `save` verb instead of
`saveFile` when Review is active. Size: ~500 / ~60 / ~40, plus the vendoring decision. Lowest
confidence of the six; it is the one slice that touches the editor chunk's contract.

### Optional: per-thread fork dispatch

A card's **Discuss in a side session** forks the owning session at its tip with the thread's ping
as the opener, through the door built for it (`_fork_comment_request`, `kernel.py:10981-11023`),
and the existing comment popover shows the fork's conversation. SDK sessions only; each fork is a
CLI holding the parent's context, so per thread and never by default. `_fork_promote_request`
returns `name` only today (`kernel.py:11043, 11047, 11052`) while the track-changents consumer
reads `promotedName` (`obsidian/src/track-snapshot.js:1445`), so this slice adds `promotedName`
beside `name` in all three success arms, with a test. A WS op wraps the POST so the webview needs
no serve token. Size: ~60 / ~20 / 0.

## Security posture

Unchanged in kind, and stated rather than silently widened, as the file-browser plan did for
saves. `trackReview` is issuable from any authenticated socket, like `saveFile`; every verb that
writes disk sits behind the same server-side consent gate, checked before any content check; the
server-side gate is the enforcement and the UI's checks are convenience. The host script runs
only on the owning kernel, on paths resolved by the kernel, and writes only the sidecar,
`config.json`, and (on reject or save) the reviewed file. The mtime fences refuse and never
merge. Both ops route by `sid` to the owning kernel over the existing federation splice; nothing
new is exempt from `_authorize`, and the review verdict rides the authenticated `/defaults`
payload rather than `/version`.

## Doctrines this respects

- **Philosophy** (`CLAUDE.md`): the count is the glance and the panel one click deeper; Send
  review batches N comments into one interruption; never-lose-the-thread holds on disk, since
  comments live in the sidecar before any send, detached threads and ops are kept rather than
  dropped, the todo stamps only at delivery, and every file-changing verb traces to the session.
- **Event over time** (`CLAUDE.md`, Design): the poll stands in for an event source the Files
  pane does not have; the human's own writes never wait on it, since every verb reply carries
  fresh mtimes that rebase the poll.
- **No plugin API** (`ui/webview/editor-chunk.ts:1-15`): Slices 0 to 4 never touch the chunk.
  Slice 5 adds a typed, internal `track` option, not a generic extension hook.
- **UI rules** (`ui/CLAUDE.md`): click-safe delegation, keyed expand state, one font-size
  vocabulary, `var(--accent)`, the romp loader on waits, no dead ends.
- **Coordination**: the implementing session works on its own worktree and publishes a working
  note naming `kernel/kernel.py` (the two ops), `file-view.ts`, `waiting.ts`, `files.ts`,
  `editor-chunk.ts` before editing; several live sessions edit `kernel.py`.

## Risks

- **Two writers on one sidecar** (agent CLIs and the host script). Mitigation: one
  load-mutate-write per verb, mtime fences, refuse-and-reload, retry by stable id. The Obsidian
  host spends several hundred lines on this race; the fence-plus-retry shape is the smaller
  alternative.
- **Rendered markdown versus offsets.** Mitigation: Raw is exact; Rendered maps through the
  lexer walk with per-token verification and refuses rather than mis-anchoring; the fallback
  painter reuses the whitespace-tolerant matcher in `ui/webview/comments.ts:86-162`; deletions
  are panel-only there; every hunk and thread has a card; a comment whose selection cannot be
  mapped offers Raw.
- **Raw human saves desync ops before Slice 5.** Mitigation: the Edit refusal from Slice 1 on.
- **Tracking off on the first night.** Mitigation: folder tracking before the report exists, the
  Send review checkbox that turns tracking on, and a guide paragraph saying to track the reports
  folder before an overnight run.
- **Tracked folders that hold figures.** The guard would send an agent to `track-edit` on an
  image, which corrupts it. Mitigation: the non-text refusal in the guard and `track-edit` is a
  dependency before such folders are tracked; until then the guide says to track reports by
  file, or to keep figures in a sibling folder.
- **Ended overnight session.** Its todo is hidden from Waiting on you and `_send_or_park` revives
  dormant sessions, not ended ones (`kernel.py:24047-24062, 12227-12234`). Mitigation: the guide
  note above; Send review surfaces the refusal; the review is already on disk.
- **Prerequisites on the owning kernel** (node on the kernel's PATH, track-changents installed,
  the file under a root). Mitigation: `no-host` and `no-node` are explicit no-verdicts surfaced
  in the gear; Review never appears broken. Node on the kernel's PATH under every service unit
  is unverified and is the first thing Slice 1 checks.
- **Tracking inheritance.** The CLIs treat notes reachable through whole-line links and embeds as
  tracked (`store-io.mjs:100-197`). Mitigation: the host script uses `isTrackedFile`, the same
  function as the guard, so verdicts agree by construction, and reports `inherited` so the panel
  can say so.
- **track-changents defects the loop can reach** (the 2026-09-03 survey). A1: `track-reply` or
  `track-edit --thread` into a thread the live sidecar lacks revives it from the `.superseded`
  park and overwrites the sidecar with an empty suggestion list, erasing pending ops including
  the one `track-edit` just recorded. A2: `track-edit` and `track-comment` replace a corrupt or
  newer sidecar with a fresh one. A7: `--thread` can bind a thread to an op id that coalescing
  dropped. A10: `track-edit --thread` failures are silent. The host script avoids A1 and A2 in its
  own path; A1 in both CLIs is a prerequisite fix before Slice 1 ships, since the agent's replies
  are the loop's step 8. Skill drift C3 (the skill says `track-edit` refuses stale text; it
  usually detaches the displaced ops instead) should be corrected so reviewers are not surprised
  by detached ops.
- **A PDF rendering dependency** (Slice 4). Mitigation: lazy chunk, size cap, frame fallback, and
  a slice of its own so the rest of the feature never waits on it.
- **Polling cost.** Two HEAD requests every 2.5 s per open panel. Mitigation: only while the
  panel is open and the tab visible. The poll's state per file is one of absent, present with an
  mtime, or unknown with a status; it starts after the first `status` supplies the sidecar path,
  takes its baseline from every `trackReviewResult` so the human's own writes never fire it, and
  treats a 404 as the value "absent" so absent-to-present is a transition like any other; a 413
  or 415 stops the poll on that file and shows the kernel's reason row.

## Tests

Synthetic fixtures only (the `notes-api` world, `TESTHOST`, placeholder ids).

- `tests/test_track_review.py` (the `tests/test_savefile.py` hermetic pattern): path resolution,
  consent refusal before content checks, host discovery and `no-host`, timeout and bad-stdout
  handling, `sid` routing, trace after reject and not after comment, the todo helper's branches
  (switch off, settled, ended, and the send arm's parked, sent, and refused outcomes, plus the
  handler's own unchanged behavior), ping text for one and several threads and for `tracked` on
  and off, the `/defaults` verdict; `tests/test_injected_voice.py` gains the two new bodies.
- Host script conformance (node tests beside the script): a sidecar written by `track-comment`,
  replied to by the host script, read by `track-reply` keeps every field; the host script's
  sidecar path equals `storePathFor`; `v` stays 3 and the fingerprint matches; accept then
  `track-edit` succeeds; reject yields the engine's baseline for the subset and remaps survivors;
  rollback when the file write fails, including removal of a sidecar the verb created; fence
  refusals with `""` and with a stale value; nothing written on `v: 4` or unparseable JSON;
  `comment` with an ambiguous anchor refuses; a file-level thread and a `target` thread round-trip
  through `store-io` unchanged; `set-tracked off` on an inherited file refuses.
- `ui/webview/track-review.test.ts`: source pins (registry entry, both ops carry `sid`, one
  `delegate()` root, string mtime comparison, no client-computed sidecar path, keyed expand
  state), pure tests for the card model, the unsent-ledger derivation, the Raw and Rendered
  mapping walks over the fixtures named in the acceptance criteria, and the ping builder against
  the kernel's text.
- `ui/webview/user-todo-links.test.ts` rewritten to pin `path-links.ts` and both callers
  (Slice 0); `editor-lazy.test.ts` extended for the typed `track` option (Slice 5) and for the
  PDF chunk staying lazy (Slice 4).

## Docs

`docs/guide.md`: "Reviewing a document" (`:29-45`) gains Review mode, states that quote chips
remain for untracked files, and tells the user to track the reports folder before an overnight
run and to keep figures out of tracked folders until the non-text refusal lands; "Waiting on you"
notes the linked path and the ended-session case; "Files" (`:126-138`) gains the panel, the poll,
the consent gate the guide omits today, commenting in either view and on images and PDFs, and
where to look when Review is missing. `docs/reference.md`, under install-time switches, notes the
User todos switch as a prerequisite for the morning loop and the node plus track-changents
requirement on the owning kernel. In track-changents (its author): README "Hosts" gains romp and
the thread shape gains `target`; the skill's ping paragraph gains the batched form.

## Deliberately not in v1

Git operations on a session's repo (romp's git calls on session repos are read-only queries);
ingesting comments typed on GitHub; a filesystem watcher or kernel push for the Files pane; a
viewer or editor extension API; rendering HTML files (the viewer serves them as source by
design); text-quote anchors inside PDFs (the CLIs cannot read a PDF's text, so PDF comments are
file-level or region); the Obsidian host's embed trees, explorer badges, status bar, multi-pane
sync, and vault rename re-keying; a scheduler for overnight work; changes to the Obsidian and VS
Code hosts beyond the documented `target` field; inline deletions in the Rendered view; undo of
accept and reject before Slice 5; multi-file review batching (one review per file).

## Dependencies

On the owning kernel: node on the kernel's PATH; track-changents installed through its
`install.sh` (the `~/.claude/hooks/` symlinks are how the kernel finds the checkout and how the
skill invokes the CLIs); the file inside a root with `.git/`, `.obsidian/`, or `.trackchanges/`;
the report's path or folder listed in `config.json` before the session writes it; the User todos
switch on for the morning todo to exist; the file-editing consent given once. On track-changents'
author: the A1 fix in both CLIs before Slice 1 ships; the skill sentence and the README row; the
`target` field documented before Slice 3; the non-text refusal in the guard and `track-edit`
before folders holding figures are tracked; for Slice 5, the vendoring decision. For Slice 4, the
PDF rendering dependency. The feature is fork-only until track-changents is public, since it
depends on that repo's CLIs.

## Open questions for the user

1. **Slice order.** 0, 1, 2, then 3 (image regions), 4 (PDFs), and 5 (live editing), each as its
   own PR, or live editing before the region slices? Recommended: the order as written, since
   the morning report is text plus figures and live editing serves it least; the fork dispatch
   stays parked until asked for.
2. **Write path.** A node host script on the owning kernel using track-changents' `store-io` and
   engine unchanged, or a Python reimplementation of the sidecar I/O in the kernel? Recommended:
   the host script; a second implementation of a cross-tool contract is where shared files get
   corrupted.
3. **Where the host script lives.** In this fork (`tools/track-review-host.mjs`, importing the
   installed checkout by file path), or in the track-changents repo as a fifth CLI? Recommended:
   this fork, so the implementing session ships it without a cross-repo dependency; offer it to
   track-changents later.
4. **Vendoring.** None in Slices 0 to 4; if Slice 5 is approved, vendor the engine, display
   planner, protocol constants, the CodeMirror field, and the logic helpers (MIT, about 1,500
   lines) pinned to a commit, or require the package to be public first? Recommended: vendor,
   unless it is public by then.
5. **Consent scope.** Every mutating verb, sidecar-only included, behind the one existing
   file-editing consent, or sidecar-only verbs ungated since they change no file bytes?
   Recommended: the former, one mental model, with the popup's copy amended so it stays true for
   comments (the session learns of them when the review is sent).
6. **Human author label.** `you`, matching the VS Code host's default so one person is one author
   across hosts, or `reviewer`, which reads better in the agent's message? Recommended: `you`; no
   `authorId`.
7. **Trace policy.** A review-specific trace after `reject`, `reject-all`, `save` and nothing
   after sidecar-only verbs, or a trace after every write? Recommended: the former; the review
   message is the notification for comments.
8. **Send review defaults.** The confirm checkboxes (answer the todo, turn tracking on, accept
   pending changes as reviewed) all checked by default, or off by default? Recommended: checked;
   each is visible in the confirm before the send.
9. **Per-reply pings** (the VS Code host's behavior; the Obsidian host's ping is a no-op stub in
   its repo) in addition to the batch? Recommended: batch only.
10. **The unsent ledger.** Browser-local per sidecar id (a second browser offers every `you`
    thread without an agent reply), or mirrored in the kernel's state directory so two browsers
    agree? Recommended: browser-local; the confirm always lists what goes.
11. **Turning tracking off on an inherited file.** Refuse with the parent named, or write the
    file into the `untracked` veto list? Recommended: refuse in v1; the veto list is a
    track-changents behavior the guide does not explain yet.
12. **PDF rendering.** A lazily loaded pdf.js chunk in the browser, or page rasterization on the
    owning kernel served as images? Recommended: the chunk, since it keeps the kernel free of a
    new tool and follows the editor chunk's pattern; the frame stays as the fallback.
13. **The region field.** Propose `target {kind, region, page?, hash}` to the track-changents
    author now, before Slice 3, or build it romp-only and document it later? Recommended:
    propose now, so the other hosts can choose to render it.
14. **The Slice 5 doctrine question**: a curated `track` option in the editor chunk. Yes, typed
    and internal with the header updated, or no live editing over pending changes at all?
    Recommended: yes.

## Upstream

Slice 0 is a pure romp change and a candidate upstream row. Slices 1 to 5 depend on a private
repo's tooling and stay fork-only until that changes; the offer decisions belong to the offer
flow, not this plan.

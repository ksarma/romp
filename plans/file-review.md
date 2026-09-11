# Comments and tracked changes in the file viewer

**Status: BUILT — all six slices (2026-09-07), awaiting the user's end-to-end walk** (decision 29: done
means the per-slice criteria pass and the user completes the motivating loop with no GitHub and no
Obsidian). Approved by the user on 2026-09-06 after reviews on 2026-09-05 and 2026-09-06 and a structured
design interview. Built by a dedicated romp session as six stacked fork PRs, each through an adversarial
review (seven lenses, two refuters per finding with executed probes, three rounds, a consolidation pass,
and a full test sweep); the "The Slice N build" notes in the sections below record where the code as
built departs from this text and why. The ADR was accepted with Slice 1. Running `install.sh` on a
machine links the vendored tooling and registers the guard; the walk needs that first. File and line
references describe this fork at its 2026-09-05 merge base and the track-changents repo as of the same
day; as with every plans/ document, treat them as dated.

## Summary

romp's file viewer can show any file and, since the file browser landed, edit it. It cannot hold
a comment on one. The person who directs the sessions reads their output as files, and today a
comment on a file leaves romp: it goes into GitHub, into a chat message that quotes the passage
and then scrolls away, or into the file itself as plain text the agent has to find. Nothing
records which passage was meant, whether it was answered, or what the session changed in
response, and seeing a session's edits to a file means reading a diff somewhere else.

This plan gives the viewer **file comments** and **tracked changes**: a comment on a passage, on a
region of an image or a PDF page, or on a file as a whole, kept beside the file with its replies;
a session's edits to a tracked file shown in place as changes the person accepts or rejects; and
one **Send to session** that hands everything unsent to the session that owns the file. It is
built on track-changents, a clean-file track-changes core written by a collaborator (MIT), whose
sidecar format, agent CLIs, guard hook, and skill are vendored into this repo unchanged, so the
agent side works on the first day and the two other editors that read the format keep working.
Six slices, each useful alone, built together.

The motivating story is the morning review of an overnight report, told in the next section, but
nothing here is specific to reports or to reviews: a session can file a user todo naming any file
it wants the person to look at, and the person can comment on any file for any reason.

The user ruled on every question this document and its reviews raised; the rulings are recorded
under Decisions. The plan keeps its original file name, `file-review.md`,
since the todo and README already point at it; every name inside follows the new vocabulary. A committed **comments log** beside each file's comments, added at the user's
request, gives git a durable record of what was said, sent, and decided.

Terminology, as pinned in `CONTEXT.md`: a **file comment** is the object (never "thread", which in
romp is a forked side session anchored to the chat); a **change** is a session's edit awaiting
accept or reject (never "suggestion", the storage format's word); a **tracked file** is one whose
session edits are recorded as changes; a **direct edit** is the person's own edit from the
dashboard. This document says **sidecar** for the JSON file that holds a file's comments and
changes, **comments log** for the append-only record beside it, **`store-io`** for the module that
reads and writes them, **host script** for the node program the kernel runs, and **owning kernel**
for the machine that holds the file. "Host" alone means an editor host (the Obsidian plugin, the
VS Code extension, or this viewer).

## The motivating loop, and the bar

Paraphrased from the user's description (the user 2026-09-05):

1. The user gives a session instructions and answers its questions.
2. The user tells it to work overnight and report in the morning.
3. Overnight the session writes or revises a report and files a user todo asking for a look,
   naming the file's path in the todo's detail.
4. In the morning the user opens the file from the todo.
5. The user sees the session's pending changes: every edit not yet accepted or rejected.
6. The user comments on passages, on figures, and on PDFs, or edits the text directly. The
   comments persist with the files.
7. The user sends everything to the session in one gesture, which also answers the todo.
8. The session addresses the comments: it replies into them and revises the text.
9. The user sees the revisions in the same viewer as changes and accepts or rejects them, singly
   or all at once.

Two facts about the storage format shape this loop. First, **tracking must be on for a file
before a session writes it** for step 5 to show anything: the guard passes untracked files
through, so an untracked file is written raw and no changes exist to show. The design therefore
lets the user track a folder before its files exist and makes Send to session turn tracking on
when it is off. Second, **the sidecar keeps no history**: accepting a change drops it and
rejecting one reverts it, so "what changed since I last looked" can only mean "what is still
pending". A round is closed by resolving its changes; what stays pending is what the next look
shows, mixed with newer edits. The comments log is what remembers the rest.

**The bar.** Steps 4 through 9 complete inside romp's Files pane, on the disk the session works
on, with no GitHub tab and no Obsidian window, and every comment, reply, and change lands in the
same `.trackchanges/` files the track-changents CLIs, guard, and skill already read and write,
unchanged. GitHub remains a read-only pointer through the viewer's existing GitHub link.

**A durable record.** The user asked that the comments leave a record in git (the user
2026-09-05). Comments already persist in the sidecar, but the sidecar forgets accepted and
rejected changes and deletes itself when a file has nothing pending. The comments log beside it
records every send, every accept or reject, every tracking toggle, and every direct edit; see The
comments log under Kernel. Whether either file is committed is the session's or the user's call
per repository (the user 2026-09-06); romp writes the files and does no git operation.

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
  morning reader looks at, renders the detail as plain text in the row and in its Reply modal
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
- **Step 8** works once the agent-side tooling is linked on the session's machine, which romp's
  installer will do from the vendored copy. romp's SDK backend leaves the SDK's
  `setting_sources` unset, and the SDK in romp's own environment (0.2.132, `ClaudeAgentOptions.setting_sources`,
  `types.py:1990`) documents that as loading all sources, matching the CLI's defaults, so the user-level guard hook
  and the skill apply; Slice 1 confirms this on a live session. `ROMP_SESSION_NAME` and `ROMP_SID`
  become the author label and stable id (`kernel/sdk_backend.py:7169-7176`; the tmux launch line
  in `bin/romp`), and both names are reserved against per-session env overrides. Because agent
  and dashboard share the owning kernel's disk, a pull from GitHub is already unnecessary.
- **Step 9** has no surface.
- Two substrates matter for the design. Editing: Edit mounts a lazily loaded CodeMirror 6 chunk
  (`ui/webview/editor-chunk.ts`) and Save rides `saveFile` to `_save_file`
  (`kernel.py:30673-30749`): a server-side consent gate (`_file_editing_on`,
  `kernel.py:4752-4764`), existing UTF-8 text files only, a 2 MB cap (`_TEXT_MAX_BYTES`,
  `kernel.py:30554`), a nanosecond mtime fence, and an atomic replace, followed by an edit trace
  telling the session whose cwd contains the file that a human edited it
  (`kernel.py:30815-30827`). Dispatch: POST `/fork-comment` and `/fork-promote`
  (`kernel.py:10981-11052, 37743-37755`) were built on 2026-08-31 for exactly this tooling's
  comments and have no caller yet.

### Why this is not the retired comment layer

The viewer's 2026-08-23 consolidation removed a browser-local comment store because batching
notes for one hand-off is what quote chips already do. This proposal does not bring that store
back. The sidecar is a file on disk beside the commented file, attributed per author, read and
written by the agent's own tools and by two other editors, and it carries the session's changes
as well as the person's comments. The chips stay for one-off notes; file comments are for
anything worth keeping with the file.

## Shape of the feature

A **comments panel on the file viewer**, opened from the viewer's action row, beside the viewer
body in the Files pane column and folding below it when the column is narrower than the
two-column minimum. Five structural choices, each with a precedent in this repo:

1. **The sidecar is track-changents v3, byte for byte, plus one optional field for regions.**
   romp mints no second schema. That is what lets the agent half (CLIs, guard, skill) and the
   other two hosts work unchanged, and it is what keeps the romp side small. The one addition, an
   optional `target` on a file comment for image and PDF regions, follows the format's own rule
   for additive fields (see The contract). A second romp-only file, the comments log, sits beside
   the sidecar in the same directory and is outside the contract; the other hosts' directory scans
   match only `.json` names and ignore it.
2. **The kernel does the disk work, on the owning kernel, by running a small node host script
   built on track-changents' own `store-io` and engine.** The browser renders JSON and never
   holds a sidecar it writes back. This is the `listDir`/`saveFile` shape: a sid-routed WebSocket
   op, so a remote session's file works with no new relay code (`ui/webview/federation.ts:53,
   278-288`).
3. **The UI enters through the viewer's action registry** (`registerFileViewAction`,
   `file-view.ts:181-192`, the GitHub link's seam): mounted hidden, revealed when the kernel
   answers.
4. **Change awareness by polling, not a watcher.** HEAD `/file` on the file, on the sidecar, and
   on `config.json` (an agent's `track-config` can flip the toggle) every 2.5 s while the panel
   is open, comparing `X-Romp-Mtime-Ns` as strings. `CLAUDE.md`
   prefers the event to the timer; the person's own writes need no poll, since every verb answers
   with fresh state, and agent writes have no event source without a filesystem watcher, which
   the file-browser plan deferred. The poll stands in for that missing event and is close to the
   Obsidian host's 2 s sidecar poll.
5. **Any file, anywhere the viewer can show it.** Comments are not tied to a project type or a
   review: every text format gets passage comments, every file gets a whole-file comment, images
   and PDFs get regions, and a file with no repository or vault above it gets a `.trackchanges/` folder created beside it
   on the first comment, which then serves as its project's root (decision 37).

## The contract: the track-changents sidecar

One JSON file per commented or tracked file at
`<root>/.trackchanges/<encodeURIComponent(relpath)>.json` (track-changents `README.md`, "The
sidecar store"): `v: 3`, `id`, `path`, `suggestions[]` as insert/delete/replace records (the README's ops) in current-text
coordinates, each with `author`, optional `authorId`, `ts`, and an `anchor {prefix, quote,
suffix}` (these are the changes); `comments[]` as file comments with `id`, `author`, `body`,
`ts`, `replies[]`, `resolved`, an optional `anchor {quote, prefix, suffix}` for a passage comment,
the format's optional `suggestionId` binding the comment to a change, and romp's own optional
`changeIds[]`, the changes the comment is ABOUT by id, the person's pick (the about follow-on,
2026-09-10, decision 45; the third romp-only additive field after `target` and `anchorAt`, ADR
0002); a top-level `detached[]` of ops
the load-time rebase could not re-place, which a host preserves and shows rather than drops; and
a `fingerprint` over the current text. The README calls `suggestionId` the cross-editor key and the
Obsidian host classifies on it: a passage comment keeps its anchor and gains a `suggestionId` when
an agent answers it with `track-edit --thread`, a shape the format allows and romp's message no
longer asks for (decision 42: the session makes edits with plain `track-edit` and answers a comment
with `track-reply`). romp never writes `suggestionId` (decision 45) and reads one it finds as the
change that ANSWERED the comment, a legacy reference on the comment's own card; a comment names the
changes it is about in `changeIds`, with or without an anchor, and its card and the sent message
name them ("about your change …"), so the reference is the person's own and survives the passage's
rewrite and the change's acceptance. The VS Code host classifies on the absent
anchor instead (`vscode/src/panel.ts:206`), so it shows a comment with `suggestionId` and no anchor
as a passage comment; a comment written by the CLIs has at most one of `anchor` and `suggestionId`.
The file on disk is
always the current text with every change applied. The root is the nearest `.obsidian/`, `.git/`, or `.trackchanges/` ancestor; nothing reads git,
the folder is only a landmark for where the one `.trackchanges/` directory of a project lives.
One `.trackchanges/` per project, at its root, never one per directory (decision 38): the tracked
list, the comments of every file in the project, and the commit-or-ignore choice have one home,
and a file moved within the project keeps its comments. The single on/off control is
`.trackchanges/config.json` `{v: 2, tracked: [...]}`: a path tracks one file, a `folder/` entry
tracks everything under it, and an optional `untracked: [...]` veto with the same shapes wins over
both the list and the link-closure inheritance (`store-io.mjs:87-98, 190-192`).

Four properties of the contract shape the design:

- **A file comment with neither anchor nor `suggestionId` is valid and means a comment on the
  file as a whole.** The schema marks `anchor` optional (README, thread shape), `store-io` passes
  such a comment through untouched, `track-reply` replies into it, the engine's comment pruning
  keeps it (`engine.js:827-833`), and both existing hosts render it as a plain discussion card
  (VS Code at the top of the panel, Obsidian at the bottom). The Obsidian host already writes
  this shape for a message with no selection. Only `track-comment` cannot create it, since it
  requires `--anchor`; the host script builds the comment itself. Every file gets this comment in
  Slice 1 (the user 2026-09-06); for images and PDFs it is the only comment until regions land.
- **One optional field, `target`, carries a region; a second, `anchorAt`, a position.** `target: {kind: "image"|"pdf", region: {x,
  y, w, h}, page?, hash, src?}` with the rectangle in fractions of the rendered page or image,
  `page` 1-based for PDFs, `hash` the sha256 of the figure's bytes so a regenerated figure marks
  its region comments stale the way a moved text anchor does, and `src` only on a figure embedded
  in a markdown file: the embed's destination as written (the Slice 3 build, 2026-09-06; this plan
  first stated the shape without it). The comment names its figure because the anchor's quote does
  not always carry the destination (a reference-style embed's sits in a `[ref]: dest` definition
  elsewhere in the file) and a passage can embed two figures; the reply's per-figure hashes and
  the panel's re-place are keyed by that spelling. The host script, never the client, computes
  `hash` from the bytes of the file the target is about: the commented file itself for a
  standalone image or PDF, the file `src` names for an embedded figure, resolved and bounded as
  Security posture states. A target on an anchored comment that names no `src` stays valid and is
  read; it is the shape this plan first described, and one a writer with the contract alone can
  leave. The host tells its figure from the anchored passage when that passage embeds exactly one
  distinct figure (one figure embedded twice still tells), says per comment where it could not,
  and never writes the sidecar on a read. The text anchor
  stays absent for a standalone image or PDF, so the other hosts show the comment as a discussion
  card and preserve the field (both write the whole object back). For a figure embedded in a
  markdown file, the comment carries both the anchor on the embed's source line, which every host
  can place, and the region, which this viewer paints on the rendered image. The README's version
  rule says to bump `v` only for a breaking change; an optional field older readers ignore is not
  one. The field is built romp-only for now (the user 2026-09-05); documenting it in the
  track-changents README, in the five-key shape above, is a later offer to its author, not a
  dependency. The second optional field, `anchorAt: <number>`, sits beside `anchor` on a passage
  comment and holds the offset the anchor located at (the anchors follow-on, 2026-09-07). It is
  romp-only and additive under the same version rule: older readers ignore it, the other hosts and
  the CLIs write the whole object back so it survives them, and the host script refreshes it on
  every sidecar write it makes, against the text the sidecar is saved for, by where the whole
  anchor sits in that text: at one place, the position becomes that place when the comment had
  none or the quote occurs nowhere else, and otherwise, since the one whole copy may be the other
  copy of a passage whose own surroundings were edited, moves only where the sidecar's recorded
  changes can have carried it, to that copy or to the one other occurrence of the quote, and
  stands otherwise; at several (the copies tie), the position stands where it still names a copy
  and otherwise moves only to the one copy, or the one occurrence of the quote, the recorded
  changes can have carried it to, never to the nearest, and only while the file is as the
  sidecar's last writer left it; nowhere, the engine's scoring places it, under a scan budget per
  write past which the remaining such comments keep the position they have (the anchors follow-on
  review, 2026-09-07, and its third round, 2026-09-08). A comment without an anchor never carries it. The panel passes it to the
  engine as the tie-break when it paints, so a passage that recurs with identical surroundings
  wider than the anchor's context stays on the copy that was chosen while the position names one of
  the copies; a copy the position does not name is painted as a guess, never as the chosen one (the
  painting paragraph under Commenting from either view).
- **A file created through `track-edit` is one insertion** spanning the whole file, and while any
  same-author insertion is pending, that author's further edits inside or beside it coalesce
  into it (`engine.js:204-218`) and do not appear as separate changes. A first look at a file the
  session created under a tracked folder therefore begins with one card covering everything;
  accepting it is how the session's later revisions become separate changes.
- **A corrupt or newer-version sidecar must be refused, never replaced.** Two CLIs today replace
  it, `track-edit` and `track-comment` (item A2 of the 2026-09-03 track-changents survey, a
  session note outside both repos; every item relied on is restated here); `track-reply` fails
  instead, unless a `.superseded` park holds the comment, in which case it revives over the
  corrupt file. The host script loads through `loadStoreStatus` (`store-io.mjs:286`), never
  through `loadStore` or `ensureStore`: `loadStore` returns null for corrupt, unsupported, and
  absent alike (`store-io.mjs:302-304`), and `ensureStore` and `track-comment` then mint a fresh
  sidecar over that null (`store-io.mjs:413-418`, `cli/track-comment.mjs:76-79`). The host script
  also never calls `reviveThreadFromSuperseded` (survey A1: replying into a comment that survives
  only in a park overwrites the live sidecar with an empty change list); a `reply` or `resolve`
  whose `commentId` is not in the live sidecar refuses `no-comment`.

Binary files: the CLIs read every file as UTF-8 text. `track-comment` and `track-reply` operate
on an image or PDF and write a valid, deterministic sidecar without touching the file, but
`track-edit` rewrites the file from the lossy decode and destroys it. The guard would steer an
agent toward `track-edit` on a tracked image. A non-text refusal in the vendored guard and
`track-edit` lands in Slice 1, before folder tracking ships.

Human authorship uses the label `you` with no `authorId`, matching the VS Code host's default
(decision 6).

## Kernel: two ops and a host script

Both ops echo a client-minted `reqId`, route to the owning kernel by `sid`, and answer on the
sending socket, the `listDir`/`saveFile` pattern (`kernel.py:39531-39558`). All mtimes travel as
strings.

**`fileComments`**, the disk op:

```
request  {type:"fileComments", reqId, sid, path, verb, args?,
          fence?: {storeMtimeNs: str|"", fileMtimeNs?: str, configMtimeNs?: str|"",
                   figureHash?: str}}
reply    {type:"fileCommentsResult", reqId, verb, root, storePath, trackedBy, agentTooling,
          fileMtimeNs, storeMtimeNs|null, configMtimeNs|null, store|null, hunks, unsent,
          log, logTruncated, decided, bom, fileHash?, fileHashReason?, embeddedHashes?, embeddedHashReasons?,
          derivedSrcs?, derivedSrcReasons?, baseline?}
refusal  {type:"fileCommentsFailed", reqId, verb, code, error}
```

`store` is the sidecar as loaded and normalized (with `detached[]`), or null when absent. `bom`
says whether the text the host read keeps a leading UTF-8 BOM, which the fetch strips from the
text the viewer shows: a stored `anchorAt` is an offset into the host's text, and the panel maps
it into the view's by this bit (the painting paragraph under Commenting from either view).
`hunks` is `engine.toHunks(store.suggestions)`: one row per change with `id, author, ts, kind,
curFrom, curTo, baseFrom, baseTo, oldText, newText, anchor`, sorted by offset. `unsent` is the
derivation from the comments log described below: `{comments: [id], replies: [{commentId, ts}],
accepted, rejected, watermark}`, where replies are identified by their comment and `ts` since the
v3 shape gives them no id, and `watermark` is the last send's (null when none). `baseline`, the clean text with every
change rejected (`engine.baselineOf`), is the whole file and is returned only when the request
asks for it. `trackedBy` is `{kind: "file"|"folder"|"inherited", entry}` or null, so the panel
can say which `config.json` entry covers the file. `agentTooling` is `"present"` or `"absent"`
for the agent-side CLIs on the owning kernel; when absent the panel works but warns that the
session cannot reply until romp's `install.sh` has run on that machine. `configMtimeNs` is null
when `config.json` does not exist; the client sends `""` for null, the same convention as
`storeMtimeNs`. The browser builds its cards from `store` and `hunks`; no card model crosses the
wire. The hash fields are Slice 3's: what a region comment's `target.hash` is compared with on
every reply. On an image or PDF that is `fileHash`, the file's bytes now; on a text file it is
`embeddedHashes`, one per distinct `src` its region comments name, and `store` carries the `src`
each src-less anchored target names by its passage (`derivedSrcs` lists which, per comment id).
Null is unknown, never stale, and each null has its reason beside it (`fileHashReason`,
`embeddedHashReasons`, `derivedSrcReasons`), since the kernel keeps the host's stderr only when a
call fails.

Verbs by slice. Slice 1: `status`; `set-tracked {on, scope: "file"|"folder"}`, where `folder`
writes `<dir>/` (refusing the root) so a folder can be tracked before its files exist, and `off`
removes the covering entry when its kind is `file` or `folder` (a folder asks a pane-local confirm
naming it) and refuses `tracked-inherited` when the file is covered only through link
inheritance, naming the parent note; `comment {anchor?, note, hintOffset?, target?}` (anchor
present for a passage, absent for a whole-file comment, `target` from Slices 3 and 4);
`reply {commentId, note}`; `resolve {commentId, on}`; `log-edit {summary}` (called by the kernel
after a direct edit, see The comments log). Slice 2: `accept {ids}`, `reject {ids}`,
`accept-all`, `reject-all`. Slice 3: `retarget {commentId, target}`, the re-place of a region
comment (a new rectangle over the same figure, the hash recomputed from the bytes as they are
now; not appended to the comments log, since a re-placed rectangle is not a decision). Slice 5:
`save {content, suggestions, accepted, rejected}` (as built: the
records as the editor's field holds them after the person's typing remapped them, which is what
this plan called `ops`, and the decisions taken in the editor, each `{id, oldText, newText}`;
the records are checked against `content` and refuse `desync` naming the first that does not
fit). Every mutating verb (all but
`status`) carries a fence: `storeMtimeNs` must equal the sidecar's current mtime, with `""`
meaning the sidecar must not exist yet, so two browsers cannot both create it; `reject`,
`reject-all`, and `save` also fence on `fileMtimeNs`; `set-tracked` fences on `configMtimeNs`
the same way, since it writes `config.json`, not the sidecar, and the host script stats
`config.json` before and after inside the same process. From Slice 3 the two verbs that stamp a
figure's hash, `comment` with a `target` and `retarget`, also fence on the figure's bytes through
`figureHash`: the hash the last reply carried for that figure (`fileHash` on an image or PDF,
`embeddedHashes[src]` on a text file), checked against the bytes the host hashes for the target,
and a mismatch refuses `figure-changed`. This key is optional where the mtime keys are not: a
caller has no hash for a figure no reply has hashed yet, so a request naming none is checked on the
mtime fences alone, and a value that is not a sha256 hex is a caller bug, refused before any disk
read. A moved fence refuses, as does `busy` (another writer held the host's lock past its wait, decision
49), and the client re-issues `status`, re-renders, and retries by stable
change or comment id, surfacing a second refusal verbatim. `figure-changed` is not retried, because
a retry would stamp the new bytes: the person is told to reload and draw the region on the picture
as it is now. Nothing merges. Two limits on the retry, from the Slice 2 build (2026-09-06):
`accept-all` and `reject-all` carry no id, so after a moved fence they re-issue `status` and stop,
saying nothing was decided — the choice is made again over the fresh set, never over changes that
landed after the click; and `accept` and `reject` retry by id only while the change under that id
still reads as its card showed it (a same-author `track-edit` coalesces into a pending change and
grows its texts under the same id), else they stand down the same way and the card shows the new
reading. The fresh status also carries the file's mtime, and when that is not the view's the panel
re-fetches the bytes — a `store-moved` from a `track-edit` moved the file too, and the code names
only the sidecar.

Refusal codes name the resolved path, tilde-collapsed: `no-node` (node absent on the owning
kernel; `status` returns it quietly and the action never appears), `editing-off` (an `error`
containing the phrase "file editing is off", the regex the viewer already matches, phrased for
comments: cannot write the comments for the file, dashboard file editing is off on this machine),
`store-moved`, `file-moved`, `config-moved`, `unsupported-version`, `corrupt`, `unreadable` (with
the OS error text), `anchor-not-found`, `anchor-ambiguous`, `tracked-inherited`, `no-comment`,
`too-large`, `busy` (the lock on the sidecar, or on `config.json` for `set-tracked`, still held by another
writer after the host's two-second wait; the client handles it as a moved fence, decision 49), and from
Slice 3 `figure-mismatch` (the anchored passage does not embed the `src` the
target names), `no-figure` (a re-place of a src-less anchored target whose passage embeds no
figure, or several distinct ones) and `figure-changed` (the figure's bytes are not the ones the
request's `figureHash` says were shown). There is no `no-root` code: a file with no landmark above
it gets `.trackchanges/` created beside it on the first mutating verb other than `log-edit`
(decision 37).

Kernel work, about 160 lines including the send op below: resolve `path` with
`_resolve_open_path` (`kernel.py:30654`); refuse mutating verbs while `_file_editing_on()` is
false, before any content check; run `node <host script>` with the request on stdin, argv as a
list, a 10 s timeout, in a `threading.Thread` as
`fileGitLink` does so the receive loop never blocks (the
`_git_out` discipline, `kernel.py:30830-30838`; the kernel already spawns node for its own bundle,
`kernel.py:5391`); parse one JSON object from stdout; a non-zero exit or bad stdout becomes
`fileCommentsFailed` with the stderr tail. The kernel never exports `TRACKCHANGES_ROOT` (it would
override every file's root for the CLIs, survey item A8). After a successful `saveFile` on a file that already has a sidecar, a comments log, or a
`config.json` entry covering it, the kernel calls the host script's `log-edit` verb (decision 33)
before replying `fileSaved`, so the reply can carry `logged: true|false` and the panel's Log is
current when the viewer hears the save; a save on any other file is traced as today and not
logged, a save on a path inside `.trackchanges/` is never logged, and `log-edit` never creates a
sidecar, a log, or a landmark. The summary is `{mtimeBeforeNs, mtimeAfterNs, bytesBefore,
bytesAfter, diff, truncated}`: `_save_file` returns the prior text beside the new mtime, the
`saveFile` handler (`kernel.py:39542-39556`, where the edit trace fires) builds a zero-context
unified diff capped at 200 lines or 16 KB (`truncated: true` when cut), and a failed append is
reported in the reply and never fails the save.
The authenticated `/defaults` payload the gear already reads reports the panel's verdict per
kernel (`ok`, `no-node`, or `agent-tooling-absent`), not `/version`, which is served before
authorization.

**The host script** (`tools/file-comments-host.mjs` in this repo, about 260 lines; decision 3)
imports `store-io.mjs`, `engine.js`, and the `addReply` function of `cli/track-reply.mjs` from the
copy of track-changents vendored into this repo (see Vendoring), so the kernel side needs no
track-changents install on the owning kernel. It reports whether the agent-side tooling is linked
there, by the presence of `~/.claude/hooks/track-reply.mjs` (placed by romp's `install.sh` from
the vendored copy, or by track-changents' own installer), since the session cannot answer a
comment without it. For every verb it reads the file as UTF-8 text and passes that string as the current text,
binary files included, so its fingerprint equals the CLIs'; `too-large` applies only to verbs
that write the file. It performs each verb as one load-mutate-write in a single process: root
discovery, sidecar path, the load-time rebase that re-places changes after external edits, anchor
location, comment construction, accept and reject through the engine, fingerprint, atomic write,
prune-when-empty, and the comments log append. For `comment` it builds the object itself in
`addComment`'s exact shape (`cli/track-comment.mjs:38-46`: id `${now}-${idx}`, `author`, `ts`,
`anchor`, `body`, `replies: []`, `resolved: false`, with `author` passed as `you` and no
`authorId`; `addComment` itself anchors at the first occurrence and cannot take an offset, so it
is not reused), and seeds a missing sidecar as `{v: 3, path, suggestions: [], comments: []}`
exactly as `track-comment` does; a whole-file comment has no anchor, no `target`, and the id
`${now}-0`. For a passage comment it re-reads the file and runs
`engine.locateAnchor` on the fresh text with the anchor the browser built from the displayed
text, hinted by the start offset; it saves only when the located text equals the quote,
rebuilding the anchor at the located position with the smallest context, from 24 characters in
steps of 24 up to a cap of 480 or the file's bounds, at which the anchor has one best hit in the
whole text (past the cap it is saved at the cap), storing the located offset beside it as
`anchorAt`, and refuses `anchor-not-found` when the passage is gone and `anchor-ambiguous` when
two candidates tie and the request's offset cannot settle it: no offset was sent, or the offset
sent sits on none of the tied copies in the text the host read, because the text moved after the
selection; that offset is refused, with a message that says the text moved, rather than placed on
the nearest copy (the anchors follow-on, 2026-09-07, and its review; before the follow-on every
tie was refused). Every sidecar write the host makes refreshes `anchorAt`, in `stageSidecar`, the
one function every sidecar write goes through, and once more before the reply is measured, so the
bytes the refresh adds count against `too-large`; the refresh reads where each comment's whole
anchor sits in the text the sidecar is saved for: at one place, the position becomes that place
when the comment had none or the quote occurs nowhere else, and otherwise moves only where the
recorded changes (the pending ops, the ops the write settles, among them the changes a save's
editor accepted, the edits the write applies) can have carried it, to that copy or to the one
other occurrence of the quote, since the one whole copy may be the other copy of a passage whose
own surroundings were edited; at several, the position stands where it still names a copy and
otherwise moves only to the one copy, or the one occurrence of the quote, those changes can have
carried it to, and only while the sidecar's fingerprint matches the file, since after an
unrecorded edit the record no longer bounds the shift; nowhere, the engine's scoring places it.
Every scan the refresh makes (the whole-anchor classification, the quote count, the engine's
scoring) is charged at its own cost to one budget per write (`REFRESH_SCAN_BUDGET`), a passage
still at its position costs no scan, and past the budget the remaining comments keep their
position and stderr says how many, once per write; and a stored comment's anchor is located
with its `anchorAt` as the hint. Reject writes the sidecar first, then the
file, and restores the prior sidecar bytes (or removes the sidecar it created, when none existed)
if the file write fails, the order `track-edit` uses (`cli/track-edit.mjs:108-128`); its file
write is atomic (temp file and rename in the same directory, through the realpath, mode
preserved, with a temporary name that does not end in `.json` so the other hosts' scans skip it) and applies the same 2 MB and UTF-8 checks as `_save_file`, refusing `too-large`
before any write. Every verb that rewrites the sidecar or `config.json` (`comment`, `reply`,
`resolve`, `retarget`, `accept`, `reject` and `save` the sidecar; `set-tracked` the config) holds
store-io's lock on the file it rewrites, from its fence stat through its last rename or prune, the
lock the vendored CLIs hold around their own load-to-rename, and refuses `busy` when the lock is
still held after two seconds; `log-edit` and `log-send`, which only append to the comments log,
hold none, since the log is appended an entry at a time by the host script alone and never
rewritten, so it has no load-to-rename for a second writer to erase; every clock a reply carries
(`storeMtimeNs`, `configMtimeNs`) is taken before the bytes it describes are read, never at reply
time (decisions 49 and 50). When `findVaultRoot` finds no landmark above the file (`store-io.mjs:43-54` walks up to forty
parents and returns null), `status` answers `root: null, storePath: null, trackedBy: null, store:
null` and the panel still offers Comment on this file and Track changes; `comment` and `set-tracked` then create `.trackchanges/` beside the file
and call `findVaultRoot` again, which now returns the file's directory, and the CLIs resolve the
same root from then on with no `TRACKCHANGES_ROOT`; `log-edit` never creates it. The host script's
decisions never drop a comment about a change (`changeIds`) or bound to one by a legacy `suggestionId`, a
stated divergence from the Obsidian host's
accept-all, kept so the comment ids in a sent message stay addressable by `track-reply`; and since
decision 42 (2026-09-09) they never resolve one either — before it, accept and a save's decisions set
`resolved: true` on the bound comments. The comments a decision stages equal the loaded ones apart
from `anchorAt`, and the host checks that on the staged sidecar, before every decision's rename lands it
(`requireCommentsUntouched`).

**`fileCommentsSend`**, the send op:

```
request  {type:"fileCommentsSend", reqId, sid, path, tracked, comments:[{id, desc, body}],
          accepted, rejected, watermark, todoId?, note?}
reply    {type:"fileCommentsSent", reqId, queued}
refusal  {type:"fileCommentsSendFailed", reqId, error}
```

`tracked` is the client's post-toggle `status` verdict and picks the second bullet of the message.
`desc` is the first 40 characters of the passage for an anchored comment, and when the host
widened the anchor's context past 24 characters because the passage recurs, also the copy by its
whole surroundings (`, the one after "…" and before "…"`: the stored prefix and suffix,
JSON-quoted so the message's `Comment <id> (…):` line stays one line; a side the file's bound left
empty is not named), the text a session can pass to `track-edit --old`, which refuses text that
is not unique, to reach that copy; a side wider than 120 characters (five widening steps) is not
printed, and the desc says instead that the passage appears more than once with the same text
around each copy, since at the host's cap the anchor may still tie, so the sides would name every
copy, and would run to a kilobyte of escaped text (the anchors follow-on review, 2026-09-07); after the passage, or
alone when the comment has none, the changes it is about (`changeIds`, the about follow-on, 2026-09-10) in the change
card's words, `about your change "<old>" to "<new>"`, `about the text you added "<new>"`, `about the text you removed
"<old>"`, several joined as a list; the change's old and
new text alone, in the older `on your change …` form, for a legacy comment bound by `suggestionId` with no passage;
"this file" for a whole-file comment, and "the
region at x, y, w, h" (with the page for a PDF) for a region comment. `body` is the comment's
unsent `you` turns joined with a blank line, oldest first; a comment whose opening was already
sent lists only its new replies. `watermark` is the largest `ts` among the `you` comments and
replies the client included, taken from the `status` reply it built the message from. `note` (the arrivals
follow-on, 2026-09-09) is the Send confirm's box, trimmed and left out when empty; the kernel refuses a `note` that is
not text, trims one that is, and refuses a trimmed note longer than 4000 characters (`_SEND_NOTE_MAX`), both refusals
before the nothing-to-send gate (a note alone is something to send) and before the watermark is read; the panel refuses
the same bound (`SEND_NOTE_MAX`, `file-comments-model.ts`) before any request goes; the message places it as decision
40 says. The kernel builds the message below and marker-neutralizes the
path, every body and the note (`_neutralize_romp_markers`, `kernel.py:30786-30798`). Delivery follows the
`userTodoAnswer` handler (`kernel.py:12198-12250`) in its order and its ended-session refusal,
factored into one helper both ops call with a flag, and deviates on purpose where the message is
worth sending without a stamp: with the user-todos switch off, the message is sent, nothing is
stamped, and the reply warns with the switch's own reason; with the todo already settled, the
message is sent, nothing is stamped, and the reply warns naming the todo (the handler sends
nothing in both cases, and keeps doing so for its own op); an ended session refuses with the
existing revive-the-session text and sends nothing. Otherwise the helper calls
`_send_or_park(be, sid, body, echo="human" if be is _TMUX else None, user_todo=todoId)`, the
handler's own call: a "parked" result replies `queued: true` and stamps when the batch drains
(`_deliver_send_batch`, `kernel.py:22392`), a truthy result stamps at once through
`_stamp_user_todo_answered`, and a falsy result fails the op. Without a `todoId` the same
truthy-or-falsy split decides sent or failed. The body is not wrapped in the handler's "Re:"
form; it is its own message. The comments are already on disk before any send, so a refusal
loses nothing. After a sent or queued reply the kernel appends the `send` entry to the comments
log through the host script.

### The message to the session

The `[obsidian-diff]` shape the skill handles (`skill/SKILL.md:121-133` for the shape, `:85-91`
for the command lines), written in the person's voice like every injected body, batched:

```
[obsidian-diff] I left 3 comments on <absPath>.

Comment <id1> (on "<quoted passage>"):
<body>

Comment <id2> (on your change "<old>" to "<new>"):
<body>

Comment <id3> (on the region at 0.12, 0.40, 0.35, 0.20 of page 2):
<body>

I accepted 4 of your changes and rejected 1.

To respond:
  • reply in words:     node ~/.claude/hooks/track-reply.mjs --file <absPath> --thread <id> --note "<your reply>"
  • to revise the text: node ~/.claude/hooks/track-edit.mjs --file <absPath> --old "<exact text>" --new "<replacement>"

When you have addressed these, ask me for another look the same way you asked for this one,
naming the file.
```

With a note from the Send confirm's box (decision 40, 2026-09-09) the note is the first paragraph after the header line
in both shapes, in the person's own words with no label, before the comments; a note with nothing else unsent is the
header, the note and the closing ask, without the line saying nothing needs a reply.
The parenthetical for a comment bound to a change follows the change's kind: a substitution reads
`on your change "<old>" to "<new>"` as above, an insertion `on the text you added "<new>"`, a
deletion `on the text you removed "<old>"` — never an empty quoted string in the person's voice. A
send that carries decisions and no comment takes a second shape (the Slice 2 build): `[obsidian-diff]
I went over <absPath>.`, the accepted-and-rejected line, `No comments this time, so nothing needs a
reply.`, and the closing sentence with the lead-in `When you have made more changes, ` — no comment
ids and no command lines, since there is nothing to reply into; the vendored skill says such a message
exists (patch 0005).

The format is modeled on the VS Code host's `buildThreadPing` (`vscode/src/dispatch.ts:519-533`)
but is romp's own text. It keeps what the skill describes: the `[obsidian-diff]` prefix, the
absolute path, a comment id per comment (the CLI flag is still `--thread`, the format's word),
and the exact `track-reply` and `track-edit` command lines — plain `track-edit`, with no `--thread`,
since decision 42 (2026-09-09): the link that folded a revision into the comment's card confused the
user, so the message no longer asks for it and the vendored skill's copy says the same (patch 0006).
The tracking-on second bullet restates the skill's own instruction, since no host emits one today (the VS Code bullet
says to edit normally, and the Obsidian host's message builder is a stub in its repo). With `tracked` false
the second bullet becomes the VS Code host's wording: edit the file normally and note it with
`track-reply`. For an image or PDF the second bullet says to regenerate the file with normal
writes and never to run `track-edit` on it; the agent can read images and PDF pages directly. The
closing sentence is what brings the loop back: the session's next todo is the return signal. The
text names no romp machinery; `tests/test_injected_voice.py` gains this body and the trace body
in its rendered set. The vendored skill gains one sentence saying a message may list several
comments, and one saying how to ask for another look.

### Vendoring

The user ruled to vendor now rather than wait for track-changents to be public (the user
2026-09-05), and to vendor the agent-side tooling too (the user 2026-09-06). `vendor/
track-changents/` holds a pinned copy of the MIT core with its LICENSE and source commit:
`package.json` (it pins the CommonJS reading of `engine.js` and the exports map), `engine.js`,
`display.js`, `protocol.js`, `store-io.mjs`, `cli/track-config.mjs`, `cli/track-edit.mjs`,
`cli/track-comment.mjs`, `cli/track-reply.mjs`, `cli/cli-args.mjs`, `hooks/track-guard.mjs`,
`skill/SKILL.md`, `obsidian/src/track-cm.js`, `obsidian/src/track-logic.js`, the
`applyEditsToText` function of `obsidian/src/track-rollup.js`, and the decorations block of
`obsidian/src/track-snapshot.js` adapted as described in Slice 5. The host script imports the node modules from it, and the
comments and editor chunks bundle the browser modules from it, so nothing depends on anything
outside this repo. romp's `install.sh` links the CLIs and the guard into `~/.claude/hooks/` and
the skill into `~/.claude/skills/tracked-changes`, and registers the guard as a PreToolUse hook
on `Write|Edit|MultiEdit` by extending the embedded registrar that already registers romp's hooks
in `~/.claude/settings.json` (`install.sh:109-167`): today its entries carry no matcher and it
appends only to the matcher-less group (`:149-152`), and its already-registered test compares the
exact `~/.claude/hooks/<name>` string (`:154-155`), so it gains a matcher-aware entry that finds or
creates the group with that exact matcher (the guard's is `async` false, since a deny must block,
and timeout 10, matching the upstream installer), and its presence check matches by basename, so
an entry the track-changents installer wrote with an expanded home path counts as registered and
is not doubled. Existing `~/.claude/hooks/track-*.mjs` and skill links that point at a
track-changents checkout are replaced with links into the vendored copy and the replacement is
reported, because the vendored copy carries fixes the checkout lacks. A machine that runs romp
then runs the whole loop with nothing else installed.

The vendored tree is the pinned upstream commit unchanged plus a patch series under
`vendor/track-changents/patches/`, one file per edit, applied at vendoring time and listed in
`vendor/track-changents/README.md`. The drift test checks two things: the vendored files equal
the pinned commit with the patches applied, and a track-changents checkout present on the
machine, if any, is at or past the pin. It never compares against whatever the checkout contains,
which by construction differs from a patched copy.

Three patches are offered back to the author: the A1 fix in `track-reply` and `track-edit`; a
non-text refusal in the guard and `track-edit`; and the skill edits (the two sentences above and
the C3 correction named under Risks). A fourth patch is romp's own and stays here: the guard
exits at once when `ROMP_SID` is absent from its environment (decision 24), as the first statement
of its `if (invokedDirectly)` block, before stdin is read, so the exported `evaluate()` and its
unit test are unchanged. Verified on the installed CLI: hook commands
inherit the session's environment, both romp backends set `ROMP_SID` there, and one of romp's
own hooks already gates on it (`hooks/romp-usertodo-context.sh:29`, rationale at `:11-13`); so the guard is registered
machine-wide yet inert in every session romp did not launch, at the cost of a node process that
exits immediately. Anything a romp session itself spawns also carries the variable and counts as
romp, which is the wanted behavior for the agent's own subprocesses. A second PreToolUse hook,
romp's own (`hooks/romp-track-bash-guard.mjs`, on the `Bash` matcher, registered by the same merge
and gated the same way), covers the write path the vendored guard never sees: it reads the command
a session runs through Bash, extracts the paths it would write (cp, mv, install and tee targets,
`>` and `>>` redirections, `sed -i` and `perl -i` files, a path a python or node inline script
opens for writing), resolves them against the session's working directory, and refuses when one is
a tracked text file, naming the file and track-edit; a read never trips it and a command it cannot
read through passes (decision 47). An eighth patch (2026-09-11) adds the per-sidecar lock to `store-io.mjs` and its take to
`track-edit`, `track-comment` and `track-reply` (decision 49); written as offerable, it is held back
from the offer under the standing word of that day to open nothing new upstream.

### The comments log

Comments persist in the sidecar, but the sidecar forgets accepted and rejected changes and
deletes itself when a file has nothing pending, so a round of comments would leave no record in
git. The user asked for one (the user 2026-09-05). The host script therefore keeps an append-only
log beside the sidecar, `<root>/.trackchanges/<encodeURIComponent(relpath)>.comments-log.jsonl`,
in the same directory and outside the v3 contract: the other hosts' directory scans match only
`.json` names (`store-io.mjs:365`, and the Obsidian host's orphan-heal and badge scans,
`obsidian/src/track-snapshot.js:414, 2052, 2104, 3433`), so they never read it, and
the VS Code host reads only the sidecar path. One JSON object per line, each with `ts` (stamped
by the host script on the owning kernel), `kind`, and `author`:

- `send`: the message as sent, with `sid`, the session's display name as `sessionName` when the
  kernel knows one (so the panel's Log row can name the session after it is renamed or ended and
  the sid maps to nothing; the same name already reaches the sidecar as the author label of every
  reply the session writes), the comment ids, the `desc` and `body` of each, the counts accepted
  and rejected since the previous send, `queued`, and `watermark`, the largest `ts` among the
  `you` comments and replies it carried.
- `accept` and `reject`: the change ids and their `oldText` and `newText` at the time, so a
  decision survives the change leaving the sidecar.
- `set-tracked`: the entry written or removed.
- `edit`: a direct edit from the viewer (decision 33) on a file that already has a sidecar, a
  comments log, or a tracked flag, with the file's mtimes and sizes before and after and a
  zero-context diff capped at 200 lines or 16 KB; the kernel's `saveFile` path calls the host
  script's `log-edit` verb after a successful save and before the `fileSaved` reply, so the log has
  one writer and the panel sees the entry when the save lands.

`fileCommentsSend` appends its entry after a sent or queued reply, never after a refusal; the
accept, reject, and toggle verbs append theirs in the same process as the sidecar write. The host
script never rewrites or prunes the log. It serves two readers. The panel shows it as a Log
section, one row per entry, so the person can see what was said, sent, decided, and edited on
earlier occasions. And it holds the only state for what is unsent: the watermark is the `watermark`
of the last `send` entry, a `you` comment or reply is unsent when its `ts` is later, and accepts and rejects since the last send are counted from the log. The
`status` reply carries the derivation. A browser crash, a second browser, or a fresh machine all
see the same answer, which resolves the user's concern about a browser-local send state (decision
10). The reply's `log` is the newest 200 entries (`logTruncated` says when that is a tail), and the
panel reads a decided change's texts from the log to describe a comment bound to it; so the reply
also carries `decided`, read off the whole log: for every comment bound to a change the sidecar no
longer holds, the newest accept or reject entry naming that change, with its texts. A decision older
than the tail describes its comment the same as a fresh one (the Slice 2 consolidation, 2026-09-06). The log is JSON lines by the user's ruling (decision 16); a rendered export for reading on
GitHub can follow if wanted.

### Consent, trace, routing

Every verb that writes disk, sidecar included, sits behind the file-editing consent
(`kernel.py:30695-30700`): one mental model, the dashboard may write files on this machine, and
the sidecar is a file in the user's project. The first comment triggers the existing popup once.
That popup's copy promises the session is told when the user edits under it
(`file-view.ts:460-463`); Slice 1 amends it for comments, since they reach the session only when
sent (decision 5).

Verbs that change file bytes (`reject`, `reject-all`, `save`) send a trace to the session whose
cwd contains the file, first person like `_edit_trace_body`: I rejected N of your tracked changes
in the file while reading it; the file and its sidecar both changed, so re-read before writing.
Sidecar-only verbs send nothing; the sent message carries the news, and the CLIs read the sidecar
on every call. Host-script writes never pass through `saveFile`, so the generic `_edit_trace` is
untouched; a sidecar hand-edited in the viewer traces like any other file, as the
never-lose-the-thread rule requires.

Both ops carry `sid`; `routeOutbound` routes any op with a scalar id field to the owning kernel
and strips the prefix (`federation.ts:53, 278-288`), so a `host:sid` file's comments land on the
kernel that owns the disk. The sidecar's bytes reach a remote browser over the same
`/remote/<host>/file` relay the file does, which mirrors the mtime header on HEAD
(`kernel.py:39930`).

## UX

### The surface, in its Slice 2 state

```
┌ Files ──────────────────────────────────────────────────────────────────────────────┐
│ ~/code/notes-api/docs/report.md   Rendered · Raw   Edit   GitHub ↗   Comments · 2 · 5 changes   ✕ │
├───────────────────────────────────────────────────┬──────────────────────────────────┤
│ ## Findings                                       │ Track changes [on] · Comment on this file · Send to session (3) │
│ The api session ~~reduced~~ cut p95 latency       │ ──────────────────────────────── │
│ by 40% ▍web                                       │ ▍web  "reduced" to "cut"         │
│ ...                                               │       [Accept] [Reject] [Reply]  │
│ We recommend ▌shipping the cache in v1.2.         │ ▍you  on "shipping the cache…"   │
│                                                   │       Which cache? Say which.    │
│                                                   │       ↳ web: The response cache. │
│                                                   │       [Reply] [Resolve]          │
│                                                   │ … 4 more changes                 │
│                                                   │ Accept all · Reject all          │
│                                                   │ Log ▸                            │
└───────────────────────────────────────────────────┴──────────────────────────────────┘
```

- **Progressive disclosure**: the action-row label is the glance, the panel is one click, a
  comment expands on click, keyed by comment id in a set that survives the poll's re-render, and
  beside the body each card sits level with the passage it is about and scrolls with the text, so
  the margin itself is the glance (the margin-layout follow-on, under Slice 2). For
  a file with neither sidecar nor tracked flag the action reads plain "Comments" and the panel
  holds the Track changes toggle (file or folder), the Comment on this file button, and an empty
  Log; counts and highlights appear once a sidecar exists.
- **Raw view is exact, Rendered view is best effort.** Changes are offsets into the source. In
  Raw, insertions tint, deletions render struck at their point, substitutions show both, each with
  the author's session chip in the session's color. In Rendered, insertions and substitutions are
  re-found by their text and highlighted, and deletions are struck at their point in both views:
  the Rendered point is placed through the same index map the comment highlights use, so a
  deletion inside a block the map refuses (a table, a code fence) appears only as a card, whose
  **Reveal** switches to Raw and scrolls there (the inline-display follow-on, 2026-09-07; before
  it every Rendered deletion was card-only). **Show changes inline** in the panel header turns
  every change mark off in both views and back on, at once and without a status round trip, and
  the choice is kept in the shared webview settings across opens and pages. **All · Comments ·
  Changes** on the row under those toggles (the filter follow-on, 2026-09-07) narrows the list and
  the marks to one kind, Comments and Changes carrying their counts and All none, and is kept the
  same way; Send to session is not narrowed. An unpainted change
  always has a card, so the compact view never dead-ends. A comment can be made inside a change
  without replying to it (2026-09-09): a click or a tap on a change mark or a comment highlight opens
  its card, whatever selection stands elsewhere in the body, and a selection made by dragging inside
  one leaves a comment on those words, since the click that ends a drag is not a tap (the panel's
  `dragClick`, which reads the selection against the clicked mark alone; decision 44). Session colors come from one
  `GET /sessions` fetch per panel open, mapping `authorId` to name and color; an author with no
  live match gets a neutral chip with its label.
- **Comment on a selection**: selecting a passage still seeds the quote chip when a chat composer
  is reachable; with the panel open a floating **Comment** button also appears beside the
  selection's bounding box (the chip lives in another iframe, so "beside the chip" is not
  possible), and the selection hook runs before the composer gate so it works with no chat pane.
  The button opens a multi-line composer in the panel with the quote shown; Enter adds a line;
  Cmd+Enter (Ctrl+Enter off a Mac) or Save saves to the sidecar, and the highlight and card
  appear at once. **Comment on this file** in the panel
  header writes a whole-file comment on any file. The mapping from a selection to a source anchor,
  in both views and every format, is specified in the next subsection.
- **Send to session** sends everything unsent in the file: comments, replies, and the accept and
  reject decisions made since the last send; the number on the button is that count. It lists what goes, confirms once pane-locally,
  disables and relabels itself while sending, then shows "Sent to <session> at <time>", or
  "Queued for <session>" when the reply carries `queued: true`, and keeps polling while open. The
  confirm carries up to three checkboxes, all checked by default: **answer the todo** when the
  file was opened from one; **turn on tracking so the session's edits come back as changes** when
  it is off (file scope); and, from Slice 2, **accept the N pending changes you have seen** when any
  pending change exists, so the session's later edits arrive as fresh changes rather than coalescing
  into an old one — the SEEN ones only (decision 41, 2026-09-09): a change whose card was on screen at
  one of the person's gestures (the card alone, as the arrivals follow-on's `entryShown` reads it: a mark
  in the text on screen with its card out of the box marks nothing seen), or that the panel's first status
  held; the option names
  how many unseen ones stay pending, and with every pending change unseen the box is unchecked and
  disabled and says nothing is accepted until they look. The sequence is fixed: the message is built
  from the current sidecar, then `set-tracked`, then `accept` with the seen changes' ids (the card's
  own accept, never an accept-all), then `fileCommentsSend` with `tracked` set to the post-toggle
  verdict and the accepted count read from the accept's reply; a refusal
  at any step aborts the sequence before the send and shows the refusal; the log entry is appended
  after the send succeeds or queues. One send per file: when a todo names several files, the
  first send answers it and later sends for the other files show no todo checkbox.
- **What counts as unsent** is derived from the comments log on the owning kernel (see The
  comments log), never from browser state; the `status` reply carries it, and the confirm always
  lists what goes.
- **Direct edits.** Edit and Save work as today for an untracked file or a tracked file with no
  pending changes; the save traces to the session and, when the file has a sidecar, a log, or a
  tracked flag, is logged (decision 33). While changes are
  pending (Slices 1 to 4) the Edit button refuses with a one-line reason naming the count, because
  a raw save over pending changes rewrites their offsets. In Slice 1 the reason says that accept
  and reject arrive with the next slice and that the session's own `track-edit` still works; from
  Slice 2 it says to resolve the changes first. Slice 5 lifts the refusal.
- **Errors** render inside the panel as an error row under the control that asked, in the
  viewer's `fileview-err` dress; `store-moved`, `file-moved`, `config-moved` and, since the sidecar lock
  (2026-09-11, decision 49), `busy` offer Reload, in the panel's row and in the viewer's Save error alike, and so
  does `figure-changed` in the panel's row (Slice 3; never retried). A
  federation `warn` arriving while a request is outstanding is treated as that request's failure
  with the warn's text. An `editing-off` refusal runs the same confirm-then-consent-then-retry
  branch the viewer's Save uses, lifted into a shared helper (see the seam below).
- **Click-safety**: the panel re-renders on every poll, so its controls delegate to one stable
  root (`actions.ts` `delegate()`) with `flash()` acknowledgement; waits show the romp loader;
  sizes and menu tokens follow `ui/CLAUDE.md`.
- **Phone**: the panel, reading, and commenting work on the phone as the same webview; region
  drawing by touch is not attempted in v1 (the user 2026-09-06).

### Commenting from either view, and in every format

Commenting works in whichever view the person is reading. The viewer has two views of text: Raw,
which every text format has (markdown, HTML, XML and SVG source, CSS, code, CSV, JSON, logs, and
the rest of the kernel's text allowlist), and Rendered, which only markdown has. HTML is never
rendered by the viewer (the kernel serves it as plain text and the file-browser plan records that
stance), so commenting on HTML means commenting on its source. Images and PDFs have no text view;
their commenting is covered below and in Slices 3 and 4. Every file, text or not, takes a
whole-file comment.

A comment made from a selection in either view is stored with an anchor whose quote is an exact
substring of the file text the host script read, so the agent CLIs, the sidecar's re-anchoring
on load, and the two existing editor hosts treat it the same as a comment written by the comment
CLI. The browser builds the anchor from the displayed text with the engine's `makeAnchor` (the
quote plus 24 characters of prefix and suffix) and sends it with the note and the start offset;
the host script re-reads the file and locates the anchor with the engine's `locateAnchor`, hinted
by that offset, widens the stored anchor's context until it is unique in the file, stores the
offset beside it as `anchorAt`, and refuses when the located text differs from the quote, or when
two candidates tie and the offset cannot settle it: none was sent, or the one sent sits on no tied
copy because the text moved after the selection, and the note is then refused rather than placed
on the nearest copy. The typed comment is never discarded by a refusal.

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

When the mapping refuses, the composer keeps the typed comment, states the reason in one line, and
offers a switch to Raw that preselects the same passage when its text occurs in the source (code
fences) and otherwise opens scrolled to the block's first line with the comment intact (tables and
HTML blocks).

Painting distinguishes four states after the engine locates a comment's anchor in the current
text, with the comment's stored `anchorAt` as the tie-break so a passage that recurs with
identical surroundings past the anchor's context is painted on the copy that was chosen: located
at the quote on a copy the comment vouches for, the anchor's one best hit or a tied copy the
stored position names, painted normally; located at the quote on a guessed copy, painted in the
dashed ring the text-changed state wears, with a "passage recurs" tag on the card and, on the open
card, a line saying the copy is the nearest to the stored position, or the first, and not a
confirmed one; quote gone but its context found (`engine.js:793-800`), painted over the
between-context region in a text-changed style with a card; neither found, shown as a card only,
marked detached in the panel. A copy is guessed when the anchor ties and the stored position
names none of the tied copies, or the comment has no position (`copyUnsure`): the refresh keeps a
position the recorded changes carried to no copy or to several, and every position after an edit
nobody recorded, and an edit inside the chosen copy's context leaves the other copies whole to
outscore it, so the engine's nearest-wins pick from such a position, or its earliest tie with
none, is a guess and is shown as one, never as the copy that was chosen (the anchors follow-on's
review, 2026-09-07; before it the guess was painted as located). The stored position is an offset
into the text the host read, which keeps a leading UTF-8 BOM the fetch strips from the viewer's
text, so the reply says whether it does (`bom`) and the panel maps the position into the view's
coordinates by it (`viewAt`) before the engine takes it as the hint and before the copy is
judged; compared unmapped, a position naming the chosen copy missed it by one on every such file,
and the copy was painted as a guess (the consolidation, 2026-09-08). Detached is a rendering state
here, not a stored flag; the host script never calls the engine's comment pruning, and the
comment stays in the sidecar. In Raw view a located comment is painted by offset over the line
rows, with no text matching. In Rendered view the located source range is converted through the
same index map to a highlight over the rendered text; a comment inside a refused block falls back
to a whitespace-tolerant match of its quote stripped of inline markup, and a comment that cannot
be painted has a card whose Reveal switches to Raw and scrolls to the passage.

Images and PDFs. A figure embedded in a markdown file is commented on through its embed line: in
Rendered view a click on the rendered image offers Comment, the anchor is the embed's source
text, and the highlight is a frame around the image; in Raw view the embed line is text like any
other. A standalone image or PDF opened in the viewer takes the whole-file comment in Slice 1,
which lands in the file's own sidecar; it renders as a card in every host and the agent replies to
it with `track-reply`. Region comments, drawn as a rectangle on the image or on a PDF page, carry
the `target` field: on images from Slice 3 (its build note under Build slices says what the host
stores and reads for them), on PDF pages from Slice 4.

Acceptance criteria:

- Raw: for every pair of source offsets in a fixture with CRLF line endings, leading tabs,
  highlighted syntax, and a trailing newline, whose end characters are non-whitespace, a DOM
  selection constructed at those offsets (each end tried as a text-node boundary and as an
  element boundary) stores a quote equal to the source slice, and the highlight after reload
  wraps exactly the text nodes of that slice. A CR-only line and a selection ending past the last
  row are included.
- Raw: a quote that occurs twice, with the same 24 characters around each copy so only the offset
  can tell them apart, anchors to the selected occurrence, including when two lines are inserted
  above the passage between the selection and the save, provided the panel painted the edited text
  before the save (the poll's reload, Reload, a refresh: `followPassage` moves the pending pair with
  its copy, exactly, and Save sends the moved offset, which the host finds on the selected copy).
  When the save comes before the panel has shown the edit, the offset sent indexes the old text and
  sits on no copy, and the host refuses `anchor-ambiguous` with a message that says the text moved,
  writes nothing, and the note stays in the composer to be placed by selecting the passage again,
  never on the nearest copy, which a stale offset picks by the insertion's length and not by the
  selection (the anchors follow-on's review, 2026-09-07; the second review, 2026-09-08, amended
  this criterion, which had stated the first outcome alone).
- Rendered: for a fixture covering both heading styles, tight and loose lists, nested and task
  lists, blockquotes, emphasis, strong, strikethrough, inline code, every link form, images,
  escapes, hard breaks, and a reference definition, every selection inside aligned blocks yields
  a quote whose walk-mapped characters equal the selected rendered characters one to one, and
  painting the stored anchor in Rendered wraps exactly the originally selected text; the reply
  CLI reads the resulting comment unchanged.
- Rendered: a selection touching code, a table, an HTML block, an entity-bearing paragraph, or
  an escaped link label is refused, the comment survives, and the Raw offer opens with the passage
  selected when its text occurs in the source, else scrolled to the block.
- Every text format: a comment from the Raw view of an HTML, SVG, CSS, CSV, and code fixture
  stores the exact source slice.
- Both: with the author label held equal, the comment object written from either view
  deep-equals the one `addComment` writes for the same quote and note, apart from id, `ts`, and
  the romp-only `anchorAt` stored beside the anchor; the anchor is the one `addComment` writes
  when its 24 characters of context locate the passage uniquely, and wider only when they tie
  with another copy's (the anchors follow-on, 2026-09-07); the sidecar's changes, fingerprint,
  and version are unchanged.
- Both: after an agent edit moves the passage, the highlight follows the engine's relocation in
  both views; when only the context survives, the text-changed style appears in both views; when
  neither survives, the card shows detached in both views and the comment remains in the sidecar.
- Whole-file: a whole-file comment written from the viewer on a text file, an image, and a PDF is
  replied to by `track-reply`, renders as a card in the VS Code host's loader and the Obsidian
  host's reader, and the file's bytes are unchanged.

### The viewer seam

The panel needs more of the viewer than the registry's `{path, sid}` context gives. Slice 1
extends `FileViewActionCtx` with `todoId?`, `body()`, `mode()`, `text()`, `mtimeNs()`,
`onRendered(cb)`, `onSelection(cb)`, `post(msg)`, `ensureEditingAllowed()` (the first-consent
popup and the re-consent-on-refusal branch, today closures inside `openFileView` and `doSave`,
lifted into one exported helper that Save and the comment verbs both call), `setEditBlocked(reason
| null)`, `aside(el | null)` (mounts or removes the panel beside the body; the viewer owns the
two-column CSS and the narrow-column fold), `setMode("raw" | "rendered")`, `scrollToOffset(n)`,
`onSaved(cb)` (fired on the `fileSaved` reply, which by then carries `logged`, so the panel can
refresh its Log), and `reload()` (re-fetch
bytes and mtime, re-run `renderBody` and `onRendered`, keep the action row and panel). The action
row itself stays registry-only. `file-comments.ts` registers its own `message` listener for its
four reply types.

### Getting into it

- From the Waiting-on-you pane: the todo's detail path is a link (Slice 0). The pane is its own
  iframe, so the link posts `{romp:"viewFile", pane:"pane", path, sid, identity:{name,color},
  todoId}` to the shell, the Files-pane branch that turns the pane on and forwards the message
  (`kernel.py:34486-34493`); the shell forwards `todoId`, `files.ts` passes it to
  `openFileView(path, sid, {todoId})`, and relative paths resolve on the kernel through
  `_resolve_open_path`. When the pane is not framed by the shell, the detail stays plain text.
- From a todo that names its file (the todo-file follow-on, 2026-09-07): a user todo record
  carries an optional `file`, the absolute path the kernel resolved when the todo was filed
  (`add_user_todo`'s `file` argument; a relative path resolves against the session's cwd; a path
  that does not resolve is stored as given and the reply warns). The Waiting-on-you pane shows
  it as a chip on the row and in the Reply modal (the basename, the full path on hover), which
  posts the same `viewFile` message as a linkified path: path, sid, identity, todoId. The
  `fileComments` status reply lists the open todos of the session whose `file` is the status'd
  file (`todos: [{id, text}]`), so the panel's Send confirm offers to answer a todo however the
  file was opened: one candidate is the checkbox, several are one radio group, and the chosen
  id goes out as `fileCommentsSend`'s `todoId`. A todo that names its file only in the detail
  still works through the opened-from link alone.
- From the viewer: the Comments action, on any file, on a machine whose kernel has node. If the
  action is missing, the gear's row beside "File links open in" names the machine and the reason
  (`no-node`), and the same row warns when the agent-side tooling is not linked and offers to run
  the link step; the guide says to look there. (Slice 1 ships the row naming the reason and the
  command to run, without the one-click link step; see decision 39.)
- From the chat: a file link opens the viewer as today; Comments is one click further.
- From the session's side: romp's default session prompt (`claude/romp-session-prompt.md`,
  symlinked by `install.sh:173` and appended to the system prompt by both backends) gains one
  sentence in its Working style section, after the paragraph on locating paths (the user
  2026-09-06), in the person's voice and conditional on the tool: when you want me to look at a
  file, flag it with `add_user_todo` if you have that tool, and give the file's absolute path as
  its `file` argument (not only as an absolute path in the detail, which can still describe it);
  I open it from there, and my comments come back to you as a message with instructions; if you
  don't have the tool, ask for the look in your reply and name the file. (As approved, the
  sentence put the path in the detail; the todo-file follow-on, 2026-09-07, moved it to the `file`
  argument, the structured link the chip and the Send confirm read, and left the detail its
  descriptive role. Decision 35 says the same, and `tests/test_file_review_plan_prompt_sentence.py`
  holds this bullet, that decision and the prompt to one another.) It does not go in the
  Housekeeping section, which `CLAUDE.md` reserves for explaining romp's artifacts. The vendored
  skill gains the sentence on asking for another look, naming the file. Both speak as the person
  and name only what the agent already sees, so the veil holds.
- An ended session's todo is hidden from Waiting on you until the session is revived, since the
  board lists living sessions only and gates ended ones (`kernel.py:25731, 26082-26087`; the
  chat's own card gate is at `24047-24062`), so a todo can vanish; the file is still on disk and
  Comments works on it without a todo. The guide says: if a todo you expected is missing, check
  for an ended session (revive it) or for a session hidden from the feed (Show in feed on its tab
  menu); the Slice 0 review found the hidden case was missing from the first wording.

## Build slices

The user ruled that all six slices are built in one push (the user 2026-09-05), leaving how to
staff and sequence it to the implementing session, with a dedicated new session suggested. Each
slice stays independently useful and lands as its own fork PR with an adversarial review pass, in
the order below unless the implementing session finds a reason to reorder. The push is done when
every slice's acceptance passes and the user completes the motivating loop with no GitHub and no
Obsidian (decision 29); the implementing session files one user todo at the end asking for that
walk, not one per slice (decision 21). Sizes are approximate new lines, webview TypeScript /
kernel Python / node.

### Slice 0: from the todo to the file in one click

User-visible: in the Waiting-on-you pane, a file path in a todo's detail is a link that opens
the file in the Files pane; the Reply modal shows the same link. Commenting is today's quote-chip
flow, and Reply on the todo is the done gesture. This alone removes the GitHub detour for
comments that need no persistence.

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

### Slice 1: file comments, the tracking toggle, one Send to session

User-visible: the Comments action; the panel with a Track changes toggle (file or folder),
comment cards, and the Log; Comment on a selection in either view of any text format; Comment on
this file on any file, images and PDFs included; highlights in both views; replies from
`track-reply` appearing within the poll interval; Send to session as one message with two of the
confirm checkboxes (answer the todo, turn on tracking); direct edits logged; the Edit refusal
while changes are pending; the gear row reporting the verdict; the installer linking the vendored
tooling; the default-prompt sentence.

Acceptance: the criteria under Commenting from either view; a first comment on a clean file
creates `.trackchanges/` and the sidecar exactly where `storePathFor` puts it; the toggle writes
`config.json` through `setTracked`, fenced on `configMtimeNs`, and `off` on an inherited file
refuses `tracked-inherited`; a mutating verb on a moved sidecar refuses and the panel reloads and
retries; the sent text carries the `[obsidian-diff]` prefix, the absolute path, and each comment
id in the form the skill describes, and the kernel and webview builders produce identical text
for one and for several comments; a send with `todoId` follows the helper's branches (switch off,
settled, ended, and the send arm's parked, sent, and refused outcomes); the first mutating click
triggers the consent popup once; the comments log gains a `send` entry after each send, an `edit`
entry after each direct edit, and the unsent count is derived from it; on a live SDK session the
guard denies a raw Write on a tracked fixture and passes a non-text file through, and
`track-config` answers; spawned without `ROMP_SID` the guard exits 0 before reading stdin (node
test); romp's installer links the tooling idempotently,
leaves an existing track-changents install in place, and registers the guard once.

Files: new `ui/webview/file-comments.ts` (registration, panel, highlight pass and the two mapping
walks, Comment buttons, poll, Log, send composer), `vendor/track-changents/` with its pin and
drift test, `install.sh` and `tests/install-sh.bats` (the vendored CLIs, guard, and skill linked
into `~/.claude/`, the registrar's matcher support, and the guard registered on its own
`Write|Edit|MultiEdit` group),
`tools/file-comments-host.mjs` and its node tests, `tests/test_file_comments.py`,
`ui/webview/file-comments.test.ts`, `docs/adr/0002-file-comments-in-the-track-changents-sidecar.md`
(accepted with this slice); touched: `kernel/kernel.py` (the two ops, the shared todo-answer
helper, the `log-edit` call after `saveFile`, the `/defaults` verdict), `file-view.ts` (the seam
above), `files.ts` (the `/sessions` color map), `gear.js` (the verdict row), `styles.css` and
`files-pane.css` (about 80 lines adapted from the Obsidian host's stylesheet, mapped to
`--accent`, `--bg`, `--fg`), `claude/romp-session-prompt.md` (one sentence), `docs/guide.md`.
track-changents code reused unchanged from the vendored copy: `store-io.mjs`, `engine.js`
(`makeAnchor`, `locateAnchor`, `toHunks`, `baselineOf`), `addReply`. Size: ~600 to 750 for
`file-comments.ts` (the Rendered walk is the largest part) plus ~110 to 140 for the seam and ~30
for `files.ts` and the relay / ~160 / ~260, plus about 150 lines of tests on each side.

### Slice 2: the session's changes as accept/reject cards and inline marks

User-visible: change cards grouped by paragraph with Accept, Reject, Accept all, Reject all, and
Comment on this change (a comment about the change, its own card in the list, the comment and the
change each carrying a tag for the other; the about follow-on, 2026-09-10. Before it a Reply that wrote a comment bound
to the change by the format's own field and drawn inside the change card; the `track-edit --thread`
link that folded the session's revisions into that card left the
loop with decision 42); inline
marks in Raw, highlights and deletion points in Rendered (the points since the inline-display
follow-on, 2026-09-07), Reveal for a change the Rendered view cannot paint; Send to session states
accepts and rejects and offers the accept-pending-changes checkbox.

Acceptance: accept changes the sidecar only (the engine's `acceptSuggestions`) and leaves bound
comments as they are, neither dropped nor resolved (decision 42; before it, marked resolved); reject applies the engine's reverse edits to the file
and writes sidecar then file with rollback; both fence on the sidecar mtime and reject also on
the file mtime; after a reject the owning session receives the trace; a `track-edit` landing
mid-round makes the next Accept refuse and reload; accept-all on a file with no comments prunes
the sidecar as `pruneIfClean` decides; a sidecar holding one whole-file insertion renders one card
whose Accept clears it; each accept and reject appends to the comments log.

Files: `file-comments.ts` (the card model ported from the VS Code host's `buildCards`,
`vscode/src/panel.ts:194-300`, and its `weave` and `awaitState` helpers at `:301-351`; the port
replaces its two host inputs, the `vscode.TextDocument` and the configured label, with the
current text and `you`, and adds the buttons that panel deliberately lacks; the Raw painter over
the viewer's line nodes), CSS (about 120 lines), `kernel.py` (trace after reject), host script
verbs. Reused unchanged: `engine.js` accept/reject (`engine.js:388-419`), `display.js`
`planDiffDisplay`; adapted: `applyEditsToText` (12 lines from `obsidian/src/track-rollup.js`).
Size: ~400 / ~40 / ~120.

The Slice 2 build (2026-09-06), panel side: the card model lives in `file-comments-model.ts`, the
panel's pure half, beside the Slice 1 comment cards; the paragraph grouping is romp's own pass over
paragraph ranges (the source split on blank lines), since `planDiffDisplay` merges only a dense
paragraph and names no paragraph for the changes it passes through. A comment bound to a pending
change is shown on the change's card and leaves the comment list; once the change is decided, the
comment's card stands on its own again with the change's texts read from the log's accept or reject
entry, which is also what `describeComment` falls back to, so a manual Accept before the send keeps
the change's words in the message. Since the about follow-on (2026-09-10) every comment is its own card
whatever it names, and Comment on this change writes `comment {anchor, hintOffset, changeIds: [id], note}`
over the change's span (a deletion: `{changeIds: [id], note}`; for a spanned change the card offers it only while the
view carries the change's text, `spanCarried` in the about follow-on's paragraph below), the verb's `changeIds` argument
the list above does not name; before it, Reply on a change card wrote `comment {suggestionId, note}`. The panel re-fetches the view's bytes itself whenever
a status lands whose file mtime is not the view's — a reject's reply, the fresh status a moved fence
asked for, an accept's reply after a write the poll had not seen — one fetch per mtime, with the loader
over the cards until the paint shows that text: every reply re-baselines the poll, so the poll never
sees a move a status already reported (the consolidation, 2026-09-06; before it, only a reject's reply
and a `file-moved` code re-fetched, and a `store-moved` from a `track-edit` left stale bytes up). The new
elements (`.fc-change`, `.fc-group`, `.fc-foot`, `.fc-diff`) wear the Slice 1 classes
beside their own and need no rule of their own to be usable (`.fc-hosted`, the comment drawn inside a change
card, had a flex-column rule at the turns' gap from the reply-place follow-on's review, 2026-09-07, and went
with its element in the about follow-on, 2026-09-10); the sheets are the
painter's.

The inline-display follow-on (2026-09-07): after walking the loop, the user asked for two things the
Slice 2 build left out: tracked changes must read inline in the Rendered view too, not only in Raw,
and the person must be able to turn the inline marks off. In the Rendered view, `paintChangesRendered`
now paints a deletion as the same zero-width `span.fc-del` point Raw paints (one element constructor
for both views, `makePoint`), placed in the rendered text at its `curFrom` through the index map
(`paintRenderedPoint`). The point goes before the first emitted character at or past the offset, or
right after the last character before it when the offset follows that character directly, so a
deletion at a word's end sits against the word. A refused block, a hole, or a blank line between
blocks leaves the change unpainted, with its card's "not shown" tag and Reveal. A substitution's point
sits immediately before its tint, wherever the tint was found: inside a code fence or a table cell
too, where the tint came through the text-match fallback, so a substitution there is shown while a
deletion at the same offset is card-only. A point at the edge of a painter's own mark (a change's
`fc-ins`, a comment's `fc-hl`, the composer's `fc-presel`) sits outside the mark, in both views and
whichever change was painted first: a deletion right after an insertion follows the insertion's mark
as its sibling, one right before it precedes the mark, and a substitution whose tint begins a comment
highlight has its point before the highlight, while one whose tint is inside the highlight keeps its
point inside, immediately before the tint. Points at one offset keep their paint order
(`insertBeforeNode` and `insertAfterText` in `anchor-map.ts`). The renderer's own inline elements are
not boundaries: a point after the last word of a `<strong>` stays in it. Before the rule, placement
followed the paint order: with the insertion painted first, Rendered made the point the mark's last
child, and the struck old text wore the insertion's tint and author underline (the review,
2026-09-07). The point adds no text node, so
`mapRenderedSelection` and `unpaintChanges` are unaffected. The **Show changes inline** toggle sits
beside Track changes in the panel header, a two-state `fc-toggle` button offered while the file has
changes and the read view is up. It is ON by default and kept as `changesInline` in the shared webview
settings (`settings.ts`, the store the gear writes; toggled from the panel as `subgoals` is from the
feed footer). Off, no change mark is painted in either view, comment highlights are untouched, and
every change card is plain (no "not shown" tag, since nothing is shown by choice) and offers Reveal. A
flip repaints from the status already held, with no request; a flip in another pane or tab reaches an
open panel through the settings signal. The sheets gained no rule: the point is the same inline span,
and the label takes the block's font. Its white-space is the block's when the label has a visible
character, which folds a multi-line label onto its line. A label of spaces or tabs alone (a removed
space beside one that stayed, a substitution of whitespace) carries the Raw rows' `white-space:
pre-wrap` as an inline style (`renderedPointStyles` in `anchor-map.ts`): under the block's normal
white-space such a label collapsed to a 0px point with no struck mark and nothing to hover, while the
painter reported the change shown (the review, 2026-09-07).

The composer follow-on (2026-09-07): after walking the loop, the user found the one-line box too
small for the comments the loop needs. Every composer the panel offers (a passage, the whole file, a
region, a reply on a card, a comment bound to a change) is now one textarea: three rows to start,
grown to its content up to twelve rows and scrolling past that, draggable taller or shorter
(`resize: vertical`; a drag may pass the twelve rows, the cap being the panel's and not a sheet
max-height, and a dragged height stands until the composer closes). Enter adds a line; Cmd+Enter on
macOS or Ctrl+Enter elsewhere (either modifier works on every platform, the chat composer's rule) or
the Save button saves; Escape cancels as before, the re-place Escape included; an Escape pressed
while an IME is composing is the IME's and stops at the box, never the viewer's close over the typed
comment. The box's measurement puts every scrolled ancestor back where it was, so a keystroke at the
cap does not scroll the panel. A hint under the box says what saves, and its wording follows the
device. With a keyboard it names the platform's chord: "Cmd+Enter saves; Enter adds a line" on
macOS, Ctrl+Enter elsewhere, the modifier detected once by the editor's modifier rule. On a device
whose primary pointer is coarse (a phone; a tablet with no trackpad) it names the button instead:
"Enter adds a line; tap Save when done". A soft keyboard has no modifier to hold, so a chord would
name a key the device lacks, and a person who pressed Return to save in the old one-line box got a
newline with no explanation of what saves now (the composer review, 2026-09-07). The chord still
saves from any hardware keyboard, whatever the hint says: a tablet with a keyboard and no trackpad
shows the button hint and accepts the chord. Whether the pointer is coarse is read at each render,
as the editor's decide words read it, because the primary pointer changes when a tablet docks to a
trackpad; the chat composer's placeholder, which drops its key chart on a coarse pointer, follows
the same rule. The draft (text, caret, chosen height) survives the poll's re-render and a refusal,
since the box is one persistent node and the typed comment is never discarded; saving trims the
blank ends and keeps the line breaks inside; a blank comment saves nothing. A card renders a
multi-line body with its breaks (`white-space: pre-wrap`, both sheets), and the send message carries
the body verbatim: the kernel's builder and the webview's are pinned to the same two-line text on
both sides (`tests/test_file_comments.py` TheMessage, `ui/webview/file-comments.test.ts`). Tests:
`ui/webview/file-comments-composer.test.ts` (driven) and `file-comments-composer-browser.test.ts`
(the real cap and the real keys, Chromium and Firefox);
`tools/file-review-plan-save-gesture.test.mjs` holds this plan to the one gesture: the plain key
adds a line wherever the plan names it, and the four sentences that once anchored a moment to that
key say the save. The same walk asked for the reply's box to open where the comment is read (2026-09-07): a
reply's box now stands inside the card it answers, below the comment's turns and above its buttons, and
stays in that card across the poll's re-render with its words, caret and height; when the list stops
showing the card (the comment resolved into the closed fold, hidden by the Changes filter, or gone from the sidecar;
until the about follow-on, 2026-09-10, its change card behind the "… N more
changes" row too) the box returns to the panel's slot with the words and a line
saying why, and Escape or Cancel hands the keyboard back to the card's Reply
(`file-comments-reply-place.test.ts`). A comment on a change card (`.fc-hosted`) had no
rule of its own until then, so as a plain block it stood the box against the turn above and the buttons
below at 0px, and after a turn of yours the two washes ran together; the review gave it a flex column at the
turns' own gap, in both sheets. The about follow-on (2026-09-10) draws no comment inside a change card, so the
element, its rule and its test (`feed-fc-hosted-gap.test.ts`) are gone.

The margin-layout follow-on (2026-09-07), panel side. The user, after walking the loop, asked whether comments could
move with the window when possible, each trying to stay centered near the place in the text it was left as the reader
scrolls, at least for markdown. The layout is the build's reading of that ask: comment cards that follow the text,
laid out as margin-aligned cards the way document editors lay out comments, each card's top level with its passage
rather than centered on it, overlapping cards pushed down in order and never up (as first built; the focus follow-on,
2026-09-08, below, holds the card the person last acted on at its mark and moves the cards above it up), and the
passage centered only on a click. The build described the design to the user as the work began, so the user could
redirect it early if it was not what the ask meant; the user has not yet said whether it is. Built: beside the body the
aside wears the margin layout
(`fc-margin`). The head and the composer sit at the top; Accept all · Reject all (moved out of the list), Send and the
Log at the bottom, fixed in place while the track scrolls though not in size (the yield rule, below); the cards
section between them is a track whose scroll is locked to the body's (each scroller's scroll event writes its position
onto the other, the echo let through without a write back; every write copies an absolute position, so an event taken
for the wrong scroller costs one write, and the next genuine one puts both scrollers at the same position again), and
the two share one range. The track's box ends a footer's height above the body's, so a card level with the text's last
lines would sit under the footer with the body at its end, where no scroll reached it: the pass pads the body's
content at its end by the footer's height plus how far the last card hangs past the content's end (`padBody`, an
inline `padding-bottom` written only when it changes and cleared by `layoutOff` when the layout ends: the fold, edit
mode, the panel's close), and makes the list as tall as puts the track's farthest position at the body's, or as the
last card's end, whichever is more, so the body itself reaches every card's end. Padding cannot lengthen a body that
does not scroll (a short file, a picture sized to its box); there the track goes on alone as far as the last card's
end, and a pass or a status reply leaves it there instead of pulling it back to the body (`followBody`). Such padding is
taken back in the pass that wrote it: a box's padding comes out of its content box, and content sized to the box by a
`min-height: 100%` (the standalone picture's box, which centers the picture in itself; the Raw view's) shrank by it
instead of scrolling, so the body gained no range and a centered picture rose by half the footer at every open of the
panel and fell back at the close, on no new information about it; the pass writes the padding, measures, and clears it
where the body's scroll height is still its box's, and keeps it where the body did lengthen (a picture nearly the box's
height, whose own box outgrows the padded content box: the body scrolls then, to a card at the picture's foot) — the
third review. The track
holds cards alone: every row the list held stands in the footer above Send (`moveRows`), the foot with Accept all ·
Reject all first, then a wait's loader, a refusal row, the "… N more changes" and Resolved folds and the empty note,
in the list's order. The footer begins under a rule whichever row comes first: the rule stands on the Send section's
top edge in both sheets, and the Send box drops its own when nothing stands before it (the first review's rule stood on
the foot alone, so a footer of rows with no pending change — a comments-only file with a resolved comment — began flush
under the track's clipped cards and drew its one rule under the fold, above Send; the review's consolidation,
2026-09-07). A row at the top of a track locked to the body's scroll was out of view for a reader anywhere but
the top of the text, and the reload's loader and the fold that says why a painted change has no card were among them.
Every card is absolutely positioned at its mark's top in the body's content, less the header's height the track begins
under: a comment highlight, a framed figure, a region rectangle on a picture or a PDF page, a change mark. Cards are
laid by that top (a tie in the list's order by the cards' own fields since 2026-09-10: a change card before a comment
card, two changes by position then time, two comments by time, the key last, and never by the order the pass was given
the cards in, so a comment about a change lays after the change at every pass, but for a tied pair above a focus with
room for the comment but not for both, where the change, first of the pair, is the one laid below the focus and the
comment holds the start (`card-layout.ts`; the focus follow-on, below); as first built, by that order, which is the
model's after a render and the last placement's after any other pass, so under a focus each pass reversed a comment
card and a change card whose marks shared a line, and every card below moved by their height difference: the Slice 4
review of `plans/markdown-viewer.md`, round 16) and each takes the larger of it and the previous card's bottom plus the
gap, so cards never overlap and, without a focus, only ever move down from their marks (with one — the card the person
last acted on, which holds its mark — the cards above it move up, past their own marks where they must: the focus
follow-on, 2026-09-08, below); a pushed card draws a dashed leader up the gutter to its mark's height, and a card the
focus moved up one down. Cards with no mark — a whole-file comment, a detached anchor, a change the view does not
paint, a region whose figure has not loaded — are the loose group at the top of the track, in the list's order, and
the placed cards begin below it (a focus can move the group up from there; the focus follow-on says how). The pure
rule is `card-layout.ts` (`layoutCards`); the panel measures and applies
(`placeCards`) after every render, on the body's, the row's, the track's and the cards' resizes, on the body's
content's resize (`watchContent`: the body is a flex-sized scroller whose box does not change when its content
reflows, as when a `<details>` block opens, so its element children join the size observer each pass), on a figure's
load and on the window's resize, one pass per frame, and never on scroll. The pass also makes the cards' DOM order the
placement's, so the Tab order runs down the margin; `cardsInOrder` gives the keyboard's place that order before a
rebuild and after it, and the foot's place is the last change card's. The rows' move into the footer and the reorder
both detach a focused control, and `moving` gives the keyboard back to it, since the browser's focus-fixup rule
otherwise drops it to the body; the selectors the pass builds from a comment id are CSS-escaped (`cssId`), so an id
holding a quote places its card instead of throwing. A mark's click, a card's opening and a card's reference link
scroll the body so the mark sits at the vertical center with the card level beside it, the pass having run first so
the expanded card's height is known; a fold moves nothing. Where centering the mark would leave the card's end past
the track's box (an open card, a pushed one), the body scrolls the least that shows the card's end, as far as keeps
the mark's top in view; that scroll is track content, where the lock keeps the track's position the body's, so it
carries no header term (`centerOn`): the first cut added one, and an opened card that fit the track landed with its
head (the fold control, the reference link) under the panel's header. A comment saved while the text is scrolled
scrolls to the card the save landed in, before the composer closes (`scrollToSaved`: the reply's render placed the
cards under the composer's box and `centerOn` measures the header live, so the two agree; the host names no id in its
reply, so the new comment is read off the reply's store as the one the status before the write did not hold,
`savedCommentId`). That was this review's build; decision 43 (2026-09-09, the arrivals follow-on below) retired the scroll
and `scrollToSaved` with it: `landSaved`, before the composer closes as well, makes the saved card the focus and moves
nothing, and a line at the panel's foot says where the card is. A passage comment's or a reply's card is centered as an
opened card is, and a loose card (a
whole-file comment's, at the top of the track, where the lock keeps it out of view for a reader anywhere but the top
of the text) is brought into the track's box by the least scroll that shows it, written onto the body and the track at
once (`showLoose`, `scrollBoth`), since a track-only `scrollIntoView` moved the track alone and the frame's
`followBody` pass pulled it back to the body; before that the composer closed and no card appeared, and the save read
as having done nothing. The reply box the composer follow-on stands inside the card it answers (`placeComposer`) is placed
with that card: a descendant of it, not a child of the list, so the sheet's absolute positioning and `moveRows` leave it
where it stands, `swapCards` keeps the card around it across a render, and the card's observer covers the box's growth;
Reply, and a render that moved the box while it held the keyboard, bring the box into the track's box the way a loose card
is shown, through both scrollers and after the pass (`showComposer`: a card the fresh list built has no top until the
pass places it, so a scroll before the pass went where the card would not stand). The narrow fold and edit mode are the list layout as before, and the two switch as the layout
changes: the fold is read off the row's computed flex-direction, since the sheet's container query owns it — and that
query, it turned out, had never fired: `.fileview-main` is the container it declares, a container query styles a
container's descendants and never the container itself, and no ancestor declared one, so a narrow column got the
fold's aside rules alone beside an unstacked body. The viewer's card (`.fileview`) now declares the container the fold
resolves against. PDFs and standalone images take the same pass, their region rectangles the marks. The footer stays
inside the panel, in both sheets: the panel is `overflow: hidden` (a panel that scrolled would carry the track off the
body and every card off its mark), the track has a basis of 0 with a floor of 30% of the panel, and, as the first
review built it, a footer section that outgrows its share (the Send section with its confirm up, the Log with its
rows) shrinks and scrolls inside itself instead of pushing Send, Cancel or the Log toggle past the panel's edge, with
the Log toggle sticky at the top of its scroller. The second review widened that yield to every section but the track,
in two tiers, in both sheets (their file-comments blocks are held byte-equal): keyed on the confirm and the Log's
rows, the first rule left every other growth (the composer, the Track file/folder choice, the Reject all confirm, a
refusal row under the foot, a fold row, the tooling warning) pushing Send and the Log toggle past the panel's bottom,
and a Tab onto one scrolled the clipped panel anyway, the head under the top edge and every card above its mark by
that amount until the next pass. Now the head, the composer, the Send section and the Log all shrink (`flex: 0 1 auto;
min-height: 0`) and scroll inside themselves when they do; the sections holding what grew give first (the composer
while it shows; the head, the Send section and the Log while they hold anything beyond their controls), their
flex-shrink a million times the others', so the collapsed sections keep their size to within a layout unit, down to a
floor of one control row, or 15% of a panel too short for one (`min(15%, 2.4em)`: four grown sections at the floor and
the track's 30% still fit); only then do the collapsed sections give, in proportion, scrolling too. The sections add
up to the panel, always. The one range, the footer rows, the content observer, the placement order, the focus fixup,
the escaping and the footer's yield rule are the follow-on's first review (2026-09-07); before it the list was sized
to the body's scroll height less the header's offset, so the last lines' cards sat under the footer, the rows scrolled
out of the locked track, a reflow inside the body left the cards off their marks, and a tall confirm or Log ran past
the panel's bottom. The two tiers, the offset-free centering and the save's scroll are the follow-on's second review
(2026-09-07), which also found the sheets' margin comment still attributing the level-with placement to the user and
held it to this note's record; the pass without a render that un-pushes a card (the leader's attribute and its length
leave the reused node) stood already and gained its pin in that round. The third review (2026-09-07) found the two tiers
had reached styles.css alone, the feed page's sheet still carrying the first cut while the byte-equal pins stood red,
and mirrored the block into feed.css; found the padding's shift of a centered picture and of a short Raw file, and made
the pass take the padding back where it bought no range; and found the panel's own section comment still attributing
the level-with placement to the user, and held it to this note's record as the sheets' had been. The loose group's
place — cards with no mark at the top of the track, out of view for a reader anywhere else — is the third review's one
finding left to the user's word, under Open questions. Tests: `card-layout.test.ts` (the rule),
`file-comments-margin.test.ts` (the panel driven over a measuring stand-in), `file-comments-margin-browser.test.ts`
(Chromium and Firefox: placed tops against marks, the collision, the lock to the far end, the fold); from the review,
`file-comments-margin-review.test.ts` (the panel over a stand-in with the focus-fixup rule, clamped scroll positions,
a footer under the track, a reflowing body, escaped selectors and media bodies: the one range and the overhang, the
non-scrolling body, the footer rows, the placement order, the content observer, the escaping, the padding gone on
close, a region card on an image and on a PDF page), `file-comments-margin-review-browser.test.ts` (the focus fixup,
the `<details>` reflow, the Tab order and the footer rows in Chromium and Firefox), `feed-css-margin-footers.test.ts`
and `styles-fc-margin-footer.test.ts` (each sheet's footer: the floor, the yield rule and the sticky toggle as
declared, and the confirm and the Log scrolling within their sections in both engines),
`feed-css-margin-leader.test.ts` (the pushed card's leader: the `::before` rule's declarations in feed.css, keyed on
the attribute and the variable the pass writes, styles.css held to the same rule, and in both engines a dashed leader
as tall as the push on a pushed card and none on an unpushed one), `tests/test_guide_files_margin_layout.py` (the
guide's Files sentence held to the panel and the sheets) and `tools/file-review-plan-margin-review.test.mjs` (this
account held to the panel, the sheets and the modules it names); from the second review,
`styles-fc-margin-fit.test.ts` (styles.css's two tiers as declared, and in Chromium and Firefox at the review's panel
heights nothing past the aside's edge, Send and the Log toggle in reach, the collapsed sections uncut, and a focus or
a real Tab onto Send or the Log leaving the aside unscrolled and every card on its mark),
`file-comments-margin-fixes.test.ts` (over the first review's stand-in with room for an open card: the opened card
shown whole from its head and from its reference link, a card taller than the track clipped at its head by the excess
alone, the un-push without a render, a whole-file comment saved while scrolled moving nothing, the line at the foot
saying above and its click bringing the card into the track's box by one write onto both scrollers, the composer
closing after (decision 43; before it, the save's own scroll), a reply's save scrolling nothing with the card the focus
and its line's click centering the card, the saved comment read off the reply's store, and at source the offset-free
term and the save's focus and line raised before the composer's close, with no scroll),
`file-comments-margin-fixes-browser.test.ts` (the opening and the save in Chromium and Firefox over a rendered body),
`styles-fc-margin-attribution.test.ts` (each sheet's margin comment held to the record
`tools/file-review-plan-attribution.test.mjs` holds this note to) and
`tools/file-review-plan-margin-review-2.test.mjs` (the second review's statements here held to the panel, the sheets
and the modules they name); from the third review, `feed-css-margin-fit.test.ts` (feed.css's two tiers as declared and
held to styles.css's rules, and in Chromium and Firefox under feed.css alone the fit at the review's panel heights),
`file-comments-margin-image-pad.test.ts` (over the first review's stand-in with a picture world: the padding taken back
where it bought no range, kept over a picture nearly the box's height, a short Raw file's taken back and a scrolling
file's kept, and at source the write-then-measure), `file-comments-margin-image-browser.test.ts` (in Chromium and
Firefox over the viewer's image body: the picture where the box centered it before and after the panel's open, its card
level with the rectangle, and the near-full picture's padding kept), `file-comments-margin-attribution.test.ts` (the
panel's section comment held to the record the plan's and the sheets' pins hold) and
`tools/file-review-plan-margin-review-3.test.mjs` (the third review's statements here held to the panel, the sheets and
the modules they name); from the review's consolidation, `feed-css-margin-footer-rule.test.ts` (the footer's rule on the
Send section's edge in both sheets, after the shared rule it overrides, and in Chromium and Firefox one hairline between
the track and the first row — the Send box alone, the Resolved fold, the foot — with the Send box's own only behind a
row).

The focus follow-on (2026-09-08): reviewing a document with a few dozen comments and changes, the user clicked a
comment's highlight and saw the highlight rise to the top edge of the body with no card beside it. A change card for a
whole replaced paragraph — its old text struck and its new text marked, several hundred pixels tall — stood above the
comment's card in the track; the placement pass only ever pushed cards down, so the comment's card sat a full viewport
below its highlight, and the click's scroll went as far as kept the highlight's top in view and no further. Built: the
pass anchors the layout on a FOCUS (`focusCard`; `focusKey` was already the name of the keyboard-focus reader), the card the person last acted on — a highlight or a change mark
clicked, a card opened by its head, a reference link followed, a Show more, the card a save landed in, a Reveal — and
`layoutCards` takes it as its third argument. The focused card sits exactly at its mark (clamped to the top inset when
the mark is under the header, as any first card is); the cards above it, by desired top, are laid by the push-down rule
first and then moved UP from the focus, each by the least that puts its end a gap above the card under it, so a card the
chain never reaches stays where the push-down rule laid it; the loose group joins that chain when the moved cards reach
it, moving up as one by the same minimum, as far as the track's start. No card is moved past the start (the review,
2026-09-08). As first built the chain ran past it when the cards above the focus did not fit between the start and
the focus, on the reading
that the focused card wins and the centering keeps it in view — but a card at a negative top could be neither read nor
reached: the track cannot scroll there, a card's head is its only control, a loose card has no mark to click, and the
placement held until another gesture changed the focus, so a whole-file comment's card vanished on a click on the first
paragraph's highlight while the header still counted it. A card the chain would move past the start is laid below the
focused card instead, by the push-down rule from its end and ahead of the cards whose marks are below the focus — the
marked ones first, each wearing the leader up to its mark as any pushed card does, then the loose ones in the list's
order; the room above the focus stays for the cards further up the chain, so a small card above a tall one that did not
fit keeps its place, and of the loose group the cards at its end go below until the rest fit, so the group's head keeps
its place at the start. A card laid below the focus stands above nothing, so the cards above are laid again without it —
the push-down rule, then the chain — until a pass moves no card past the start (the set of cards sent below only grows,
so the passes end): a card the spilled card alone had pushed under its mark sits at its mark again, and a card under a
spilled whole-file card takes the start the group gave up (the verification review, 2026-09-09: laid once, the card
between a spilled tall card and the focus kept the push the tall card had given it in the push-down layout and stood
under its mark wearing a leader up a gutter no card stood in — in the panel's own stand-in, the passage's card under its
mark with empty track above it, its leader claiming a push the change card, by then below the essay, no longer made). The
cards below the focus follow the push-down rule from the end of the last card so displaced, as ever from a card's end.
Without a focus the rule is unchanged.
A focus written on a LOOSE card — a whole-file comment's card opened by its head or its Show more, the card a
whole-file comment's save landed in — leaves the pass's focus as it was: the pass keeps the card it laid the cards on
last (`laidOn`), since a loose card has no mark to be laid level with and the rule takes a focus with no mark as none,
so writing it laid the whole margin by the push-down rule again, the clicked card at the track's start out of the box
with nothing scrolling after it and the card the person was reviewing under the tall card again, off its mark (the
verification review's second round, 2026-09-09: the reach rule lays a loose card the chain cannot fit above the focus
below it, where a head click reaches it); a gesture on such a card moves nothing, as a head click on a loose card
never did, and `layoutOff` clears the memory with the focus.
A focus written on a card that is loose in the CURRENT view alone is spent by that pass the same way: a comment on a
passage the Rendered view cannot paint (an HTML comment block) has its Raw highlight one view switch away, but the pass
replaces the focus with the card it laid on (`focusCard` takes `laidOn`; the pass keeps no second memory), so the focus
does not survive to the view that paints the card, and the bar's Raw button, a gesture on the view and not on a card,
lays the card by the push-down rule, under a tall card above it, where Reveal on the card arms the focus and lays it
level (the merge audit, 2026-09-09; a focus kept latent through a loose pass, with the card-gone clear falling back to
`laidOn`, was the alternative).
A card the focus moved up past its own mark draws its leader down the gutter
(`data-pulled`, `--fc-pull`), as a pushed card draws one up. The focus is set before the render whose pass lays the
card (`showCard`; the head-click
listener in `installLayout`; `focusOn`, which `goTo` and `scrollCard` call and which runs a pass when the focus
changed; the save's is the one on `scrollCard`'s path — `scrollToSaved` reaches it with no gesture before it, so a reply
saved on an open card that is not the focus, pushed under a tall change card whose mark was clicked after the card
opened, lands level with its mark and not where the push-down rule left it, a viewport below: the verification review,
2026-09-09; since decision 43 the same day the save's setter is `landSaved`'s own call to `focusOn`, with no click on the
card before it to set the focus and no scroll after it, and `scrollToSaved` is gone), and the mark is then centered
(`centerOn`) so the mark and its card sit together mid-view; the least-scroll
fallback stays for a focused card taller than the track has room for below the centered mark — the margin note's rule
above: where the card's end would fall past the track's box with the mark at the body's center, the body scrolls the
least that shows the card's end, and the mark lands above the center with the card whole and level beside it. That
room is half the body's height less the footer's and the gap (in the focus fixtures' geometry 82px, against a 160px
track), so the fallback fires for an open card that fits the track with room to spare, not only for a card taller than
the track (the verification review, 2026-09-09: this record had narrowed it to the latter, while
`file-comments-focus.test.ts` and `file-comments-margin-fixes.test.ts` both drive a fitting card through it).
Reveal arms the focus as well (`revealInRaw`; the merge audit, 2026-09-09): the card is made the focus before the
switch to Raw, so the pass the viewer's `setMode` runs synchronously lays it level with its Raw mark before
`scrollToOffset` centers the row, and a pass runs after the switch where the switch ran none, and only there (a file
with no Rendered view is Raw already, so the switch paints nothing; every pass ends by writing a new placement,
`placed`, so the placement of before still standing after the switch says no pass ran — the review of the merge audit's
fixes, round 2, 2026-09-09: the pass ran wherever the last pass had not laid the cards on the card, which with Show
changes inline off, where Raw paints no mark and the switch's pass keeps the focus it had, was every change card's
Reveal, the margin measured and written twice for one click). The row's centering is then settled (`settleRevealed`;
the review of the merge audit's fixes, 2026-09-09): where the switch's pass laid the card on its Raw mark, `centerOn`
follows the row's centering with the landing a click on the mark gives — the mark centered, or the least scroll that
shows the card's end, the fallback above — since the row's centering alone left a card taller than the room under the
body's center level with its head in the track's box and its end, its run of turns and its Reply and Resolve row, past
the track's bottom, so the body ends where `centerOn` puts it, not where the row's centering did; where the pass laid
the card on no mark (Show changes inline off: Raw paints none, and `landOn` cues the row) the row's centering stands,
since `centerOn` has no mark to scroll to. Before, Reveal set no focus, and the switch's pass laid the margin on the
tall change card the person had unfolded: the revealed card was pushed under it, wholly outside the track's box, while
its passage sat mid-body; `focusOn` before the switch would not serve, since the card is loose in the view where Reveal
is offered and the pass spends a loose focus.
A focused card taller than the track has its head cut by the excess (its end and the gap over the track's box) with
its end in the box and the mark's top in the body's; one taller than the track by more than the header less the gap
meets the cap — the scroll stops where the mark's top would leave the body's box, a gap under its top, so the head is
cut by the header less the gap and the end stays past the box, since no scroll shows both ends of such a card (the
verification review, 2026-09-09: this record had the excess alone cut the head in both cases, while `centerOn` and
`file-comments-margin-fixes.test.ts` cap the scroll; Show more on a long text is the usual way there, its Show less at
the foot keeping the keyboard as below).
The focus clears when the list no longer holds the card (a status, the filter, a fold), when the layout
ends (`layoutOff`: the fold to the list, edit mode, the panel's close) and with the panel (`dispose`); and a pass in the
list layout clears one too (the review, 2026-09-08: a mark or a head clicked in the list wrote a focus the list had no
pass to spend, and the flip to the margin layout — a resize, not a click — anchored on it with nothing centered, the
cards above it moved from their marks). `layoutOff` clears the pass's writes on the list and the cards too — the list's
inline height, each card's top and leader — since the render that follows keeps the live list and a card while a reply's
box stands in it (the graft around the box), and the list kept the margin's height in the list layout, the aside
scrolling through a screen and more of empty space under the cards until the box left the card or the columns came back
(the merge audit, 2026-09-09). Tall cards fold:
in the margin layout a change card's old and new text, a comment's body and a run of turns wear `fc-clip`, and the
sheets cap each at eight of its lines (`8lh`), the last lines fading (a mask) where the pass found the cap cut the
content (`clipCards`: `data-clipped`, read before the cards' heights, since the fold changes them) — a run of turns cut
at its START instead, scrolled to its last row with the sheets' fade at its first lines (`keepEnd`; the review,
2026-09-08: the turns stand oldest first, so the cap hid the newest, the session's latest answer and the turn a reply
box under the run answers, behind Show more); the parts are every `fc-clip` under the card (until the about follow-on,
2026-09-10, a change card's hosted comments' body and run of turns among them, so the card's one Show more lifted them with
the change's text: the verification review, 2026-09-09, found that a pass reading the card's own children alone left a
hosted run capped with no fade and, where the change's own text was short, no Show more at all, a compact view with no
way in; no comment is drawn inside a change card now); the card's foot then offers Show more (`fcclip`, a `fileview-btn` through the delegate root, hidden as rendered
until the pass finds a part cut), Show less once open, keyed like the expand state (`openBodies`; the card wears
`fc-more`) so the choice
survives a re-render; Show more makes the card the focus and centers its mark, as opening a card does.
The row stands at the card's foot above the action row — on a comment's card under the run of turns, on a change card
after its old and new text, above Accept and Reject — and a reply's box opened on the card stands between the row and
the buttons (`placeComposer` puts it before `.fc-actions`): the box below the turns and above the card's Reply and
Resolve, as asked on 2026-09-07, with the toggle kept by the text it lifts (until the about follow-on, 2026-09-10, a
hosted comment's Reply and Resolve so stood above the change card's one Show more, which lifted the hosted parts too:
the verification review, 2026-09-09, raised both orders and the choice was recorded; with every comment on its own card
there is one order, the comment card's, which the reply-place stand-ins assert).
The list layout caps nothing. The keyboard stays on Show more and Show less (the review, 2026-09-08): the row is rendered hidden and the
pass shows it, so `render`'s refocus before the pass could not land on the fresh toggle — focus() on an element not
rendered is a no-op — and the keyboard fell to the body when the toggle was pressed, and on any re-render while it was
on the toggle; `render` refocuses once more after the pass (`refocus`, `settled`), and where the row stays hidden (the
list layout) the keyboard goes to the card's head, the toggle remembered and taken back by the next render that shows
it.
The memory holds for as long as the control is in the list and the keyboard stays where the panel put it, however many
renders pass — a repaint, a status — and a busy Accept or Reject is remembered the same way, so the refusal that keeps
a card returns the keyboard to the button; the composer's controls keep the one render, since a save closes the box in
the render after its Save comes back (the verification review's second round, 2026-09-09: `render` dropped the memory
at its start and `refocus` re-armed it only on the way to the nearest place, so it lasted one render — the toggle was
forgotten on the first status while the columns stayed narrow, and the render after they came back left the keyboard
on the card's head, where a press folds the card).
Tests: `card-layout.test.ts` (the focus rule: the tall card moved up by the least that clears the focused card, the
cards above shifting only as needed, the cards below unchanged, the loose group joining the chain as far as the start,
and no focus, a loose focus and an unknown focus giving the old result), `file-comments-focus.test.ts` (the panel over
the review stand-in: the focus set by a highlight click, a
change mark, a head click that opens, a reference link and Show more, passed to the pass and laying the card level with
a tall card above moved up; not set by a fold, of the focus or of another card; cleared when the card is gone from the
status and on the fold; the leader down; a tall part clipped in the margin and not in the list, of a change card and of
a comment card — a long body, a run of turns; Show more and Show less, surviving a re-render, Show more centering the
mark), `file-comments-focus-browser.test.ts`
(Chromium and Firefox over a rendered body with a replaced paragraph's tall change card open above a comment: the
comment's card level with its highlight within a pixel and both in view after the click — which the panel before the
fix failed, the card a viewport below — the change card moved up and folded to eight lines with Show more, Show more
opening it whole as the focus, Show less, and the narrow fold clipping nothing), `tests/test_guide_files_focus.py` (the
guide's sentence held to the panel and the sheets) and `tools/file-review-plan-focus.test.mjs` (this paragraph held to
the panel, the layout, the sheets and the modules it names); from the review (2026-09-08), `card-layout-reach.test.ts`
(no card past the start: the review's scene, a tall card the chain cannot fit laid below the focus with its leader up,
the room above kept for the cards further up, the loose group's end going below in the list's order, and a grid of
fixtures with every card at or below the start), `file-comments-focus-review.test.ts` (the panel over the stand-in with
a focus() that lands only on a rendered element: a mark or a head clicked in the list layout anchoring nothing when the
columns come back, the keyboard held on Show more and Show less across a press and a re-render and sent to the card's
head where the row stays hidden, a folded run of turns scrolled to its end), `tests/test_guide_files_focus_scope.py`
(the guide's sentence scoped to the panel beside the file, with the list under a narrow column showing a long card
whole) and `tools/file-review-plan-focus-review.test.mjs` (the margin note's rule qualified by the focus and pointing
here, the Docs section's record of the guide's sentence and the Open question's loose group, each held to the layout,
the panel, the sheets and the guide); from the verification review (2026-09-09), `card-layout-spill.test.ts` (the
re-lay: the card between a spilled tall card and the focus at its own mark; two such cards, the first at its mark and the
second pushed by the first alone; a card above the spilled one still pushing the card between; the loose group's spill
giving the first paragraph's card the start, and the card under a kept head laid from that head's end; and a grid of
fixtures where every card under its mark sits exactly a gap under the card placed above it),
`file-comments-focus-verify.test.ts` (the panel over the stand-in: a reply saved on an open card that is not the focus
making it the focus, level with its mark and centered, the tall change card above moved up; a comment a change
answered folding on its own card, its run of turns cut and scrolled to its end and lifted by that card's own Show more,
while the change card folds its own text alone and hosts nothing, on a change whose own text is long and on a short
one, whose card offers no toggle while the comment's does (the about follow-on's rewrite, 2026-09-10, of the hosted
comment's fold with the change card the module pinned until then); the fold's choice surviving a re-render a status
drives, an ask answered with the store; and the module's own vocabulary),
`tools/file-review-plan-focus-centering.test.mjs` (the fallback's trigger as recorded here held to `centerOn`'s
condition — the card's end against the centered scroll, not its height against the track's — and to the panel fixtures'
geometry, whose open card fits the track and takes the fallback) and `tools/file-review-plan-focus-verify.test.mjs` (the
re-lay, the save's focus and the fold's parts as recorded here, the hosted fold among them as history, held to the
layout, the panel and the modules this round names, and every focus module in the tree — the layout's, the panel's,
the guide's and the plan's — named here and in the Tests section's bullet, so a round's module fails by name, not in a
later consolidation — a scan of the names, `card-layout` and `file-comments-focus`, which a focus module named
otherwise passed unnamed: the module of the review of the merge audit's fixes, named for Reveal, until
`tools/file-review-plan-focus-audit.test.mjs` below read the headers);
and from its second round, `file-comments-focus-verify-2.test.ts` (the panel over the review stand-in: a head click, a
Show more and a whole-file comment's save on a loose card the reach rule laid below the focused card leave the layout
and the scroll as they were, the focus kept on the card the person was reviewing; the keyboard's memory of a control a
render could not land on — Show less hidden by the fold to the list layout, a busy Reject — held across a repaint and
a status until the control is back; and the focus cleared by the panel's close, driven through a close and a reopen);
and from the merge audit (2026-09-09), `file-comments-focus-audit.test.ts` (the panel over the review stand-in: Reveal on
a card pushed under the unfolded change card writing the focus before the switch to Raw, the pass the switch runs laying
the card level with its point; the fold to the list layout with a reply's box standing in a card leaving no inline height
on the list and no top or leader on the kept card, the columns sizing and placing the cards again),
`file-view-focus-seat-browser.test.ts` (the real viewer in Chromium, the Files pane at 1000x600: a card made the focus by
its highlight level with its mark and the track locked to the body across Raw and Rendered, one A+, a session's write
landing through the poll and a reload run under a held press, whole in the track's box after the click and the view
round trip; then the Reveal step, a deletion's card and a loose comment's under the unfolded change card laid level with
their Raw marks, whole in the track's box, not pushed) and, in `file-comments-focus-browser.test.ts`, the fold with a
reply's box standing in a card (the list's box its children's span, the aside's scroll range its content, the box and
the words kept in the card, in Chromium and Firefox); and from the review of the merge audit's fixes (2026-09-09),
`file-comments-reveal-arms-focus.test.ts` (the panel over the review stand-in with a seam that does what the viewer's
does — `setMode` returning without a paint on a file with no Rendered view and re-rendering the body synchronously on a
markdown file, `scrollToOffset` centering the Raw row holding the offset — where the audit's stand-in stubs the switch
and drives the change branch alone: the pass `revealInRaw` runs itself where the switch painted nothing laying the
deletion's card level with its point, not pushed, then the scroll bringing it whole into the track's box; the comment's
branch writing the focus before the switch and scrolling after it, over the Raw rows, the card level with its Raw
highlight; a revealed card taller than the room under the body's center settled by the least scroll that shows its end,
past the row's centering; and with Show changes inline off the pass keeping the focus it had, the row's centering
standing with no settling after it and the row wearing the landing cue) and
`tools/file-review-plan-focus-audit.test.mjs` (the Reveal statements here — the focus before the switch, the pass after
it where the switch ran none, the settling where the switch's pass laid the card on its mark — held to the panel and to
the module, which is named here and in the Tests section's bullet and holds what this record credits it with; and every
module whose header cites this paragraph named in both places, read from the headers and not the names, since the name
scan above reaches `card-layout` and `file-comments-focus` and this round's module, named for Reveal, passed it
unnamed); and from its second round, `file-comments-reveal-one-pass.test.ts` (the same stand-in with the passes counted
through the global `getComputedStyle`, the pass's first read: with Show changes inline off, Reveal on the change card
from Raw and from Rendered, and on the deletion's card, runs one pass, the switch's own, which finds the card loose and
keeps the focus it had, with none after it — before, the whole margin was measured and written a second time, to the
same values — the row centered and wearing the landing cue; on a file with no Rendered view the pass `revealInRaw` runs
itself is the click's only pass, laying the card level with its point; and on the comment's branch in Rendered the
switch's own pass, laying the card level with its Raw highlight, is the only one). From the about follow-on's review
(2026-09-10), `tools/file-review-plan-about-records.test.mjs` holds the sentences here the follow-on superseded, the
Show more row's order and the focus module's fold, to the panel and the module as history.

The anchors follow-on (2026-09-07): the user asked that a passage comment anchor reliably to text that
recurs. Before it, a comment on a passage whose 24 characters of context matched another copy's was
refused `anchor-ambiguous`, whichever copy was selected, and a stored comment carried nothing but its
three anchor fields to be placed by. Two changes, both in the host and both romp-only: the stored
anchor's context widens until it is unique (`uniqueAnchor`: 24 characters, then 24 more at a time, to
a cap of 480 or the file's bounds; a passage unique at 24 keeps the anchor `track-comment` writes, and
one still tied at the cap is saved at the cap), and the comment gains `anchorAt`, the located offset,
refreshed on every sidecar write the host makes (`refreshAnchorAts`, first thing in `stageSidecar`, the
one function every sidecar write goes through, and again in `checkReplyFits` before the reply is
measured, so the bytes it adds are counted). The refresh is exact and bounded (the review, 2026-09-07; its third round, 2026-09-08):
an anchor that sits in whole at one place takes that place when the comment had no position or its quote
occurs nowhere else, and otherwise, since the one whole copy may be the other copy of a passage whose own
surroundings were edited, moves only where the recorded changes can have carried it, to that copy or to
the one other occurrence of the quote, and stands otherwise; one that sits at several keeps its position
where it still names a copy and otherwise moves only to the one copy the recorded changes (the pending
ops, the ops the write settles, the edits the write applies, summed as bounds on the shift) can have
carried it to, or to the one occurrence of the quote they can have (`movedCopy`), never to the nearest
copy, and only while the sidecar's fingerprint says no unrecorded edit touched the file; one that sits
nowhere in whole is placed by the engine's scoring under `REFRESH_SCAN_BUDGET`, past which the rest keep
their position and stderr says how many, so no count of comments holds a write past the kernel's deadline;
every scan (the whole-anchor classification, the quote count, the engine's) is charged to that one
budget per write, and a passage still at its position costs none. The panel passes a card's `anchorAt` to the
engine as the tie-break when it paints (the model carries the field), so the highlight stays on the
copy that was chosen even where the anchor alone cannot tell, while the position names a tied copy;
where it names none, or the comment has no position, the copy the engine returns is a guess, and
the panel paints it as one: the dashed ring the text-changed state wears, a "passage recurs" tag
and the card's words (`copyUnsure`, the review; the painting paragraph under Commenting from either
view states the four states); a pending composer's passage moves exactly through an edit that does
not reach it, and one the edit reaches is re-found through its anchor, with no offset sent when the
copies now tie, so the host refuses instead of guessing (`followPassage`). The refusal remains for a
tie the request cannot settle: no offset sent, or an
offset that sits on none of the tied copies in the text the host read because the text moved after
the selection (`locateExact` with `exact`, refused `anchor-ambiguous` with a message that says so,
never placed on the nearest copy). The Raw acceptance criterion on a quote that occurs twice states
both outcomes of lines inserted between the selection and the save: the note lands on the selected copy
when the panel painted the edit before the save, since the follow moves the offset only from a repaint
(`retargetComposer`, on `onRendered`), and is refused with the note kept when the save came first (the
second review, 2026-09-08; the criterion had stated the first outcome alone). The sent message
names a recurring passage by its widened surroundings (`passageDesc`, up to 120 characters a side;
past that it says only that the passage recurs with the same text around each copy), so the
session reading it can reach the chosen copy, or learns that `--old` with the nearby text will be
refused. Tests: the host
modules `tools/file-comments-host-anchors.test.mjs`, `-anchors-exact`, `-anchors-review-2` and
`-anchors-review-3`, two e2e cases (a 24-character
tie told apart at 48, and a tie past the cap whose positions follow a tracked insertion above),
`ui/webview/file-comments-anchors.test.ts`, `-follow` and `-model-recurring`, and this plan's pins in
`tools/file-review-plan.test.mjs`, `-acceptance` and `-anchors`; the painted states in
`ui/webview/file-comments-anchors-unsure.test.ts` (a guessed copy wears the dashed ring, the tag and the
words; a copy the position names and a unique passage paint plainly) and `-region-tied` (the region
composer's tied and elsewhere pairs); and `tools/file-review-plan-anchors-states.test.mjs`, which pins
the painting paragraph's four states, this note's guessed-copy clause and the Raw criterion's two
outcomes against the panel and the host.

The todo-file follow-on (2026-09-07): after the end-to-end walk the user asked that the link between a
user todo and its file be structured, not a path in the detail's free text, and that any Send on the
file answer the todo, not only a Send from a viewer opened through the todo's link. The record gains
`file` (kernel), `add_user_todo` gains the argument and the session prompt says to pass it (postal),
and on the panel side: `Status` gains `todos`, the open todos of the session that name the file,
which the kernel adds to the `status` reply; `todoChoices` (`file-comments-model.ts`) lists the
candidates: the todo the file was opened from first, with its text when the status lists it, then the
status's todos in the kernel's order, each once, minus the todos a send from this page has stamped.
The confirm renders one candidate as the checkbox (checked, the todo's text cut to one line, the
whole text on hover and in the row's fold) and several as one radio group, Answer: the first selected, the others, none, so
one send still answers one todo (decision 28); `chosenTodoId` is what `doSend` puts in `todoId`. After
a send the list follows the next status, which no longer carries the settled todo; the page's memory of
what it stamped covers the moment before that status, and a send the kernel could not stamp leaves the
todo offered, as before. A status asked after the send's reply that still lists the todo is the kernel's
word that it is open (a parked send stamps at its drain; a recalled or lost answer reopens the todo) and
releases the memory, so the todo is offered again — the review found a reopened todo hidden from every
confirm on the page until a reload; only the todo the file was opened from whose `file` is another file,
which no status of that viewer lists, stays answered for good. In Waiting on you the todo's `file` is a chip on the row and in the Reply modal
(`fileChip`: openPathLink's span restyled, so the list delegate's and the modal's `openpath` open it
with the same `viewFile` message: path, sid, identity, todoId); the detail's linkified paths stay. The
chat's todo card and its Reply modal show the same chip (render.ts `todoFileChip`; the `.ut-file` pill in styles.css,
which the review found missing: the class named no rule, so the card's chip was a plain link). The guide's Waiting on
you and Files sections say both.

The filter follow-on (2026-09-07): reviewing a document with dozens of routine changes, the user found
the few comments that mattered buried among the change cards, and could not tell a comment card from a
change card at a glance. The panel header gained a filter on the row under the two toggles, one group of
the toggles' buttons, **All · Comments N · Changes M**, offered once the file has a card to filter
(`filterOffered`) and kept as `commentsFilter` in the shared webview settings (`settings.ts`, "all" by
default) the way `changesInline` is: read when a panel opens, written on each pick, and reaching an open
panel elsewhere through the settings signal. Its counts are the action-row label's (`cardCounts` in
`file-comments-model.ts`: the open comments and the pending changes), so the label and the control
agree; All carries no count. A detached change is neither an open comment nor a pending change, so the
Changes option carries the label's detached count after its own, "Changes 0 · 1 detached", and its title
says the detached changes are listed in a group of their own: a file holding detached changes alone does
not read as one with nothing to show (the review, 2026-09-07). **Comments** lists every comment card on
its own, a comment naming a change included with its tag (until the about follow-on, 2026-09-10, a comment
bound to a pending change stood here with the change's words as its reference and an "on a change" tag, its
only card of its own under the filter), with no change card, group, fold or
Accept all · Reject all foot, and paints no change mark in the text; **Changes** lists the change cards
alone, each counting the comments about it (before the about follow-on, each with the comments made on it
drawn inside), and paints no comment highlight or region rectangle; **All**
is the list as before. Show changes inline applies on top ("Changes" with the marks off shows the cards
and no mark), the keyed expand state is untouched by a pick, and Send to session is not filtered: the
confirm lists everything unsent as before. The buttons are one group for the keyboard: an arrow chooses
the next or previous option, wrapping at the ends, and Home and End the first and last. Every card head
names its kind, Comment, Change, or Region, in a word before the author's chip, styled like `.fc-note`
(`--dim`, 0.86em; the `.fc-kind` rule), and the card's left edge is colored by kind, a 3px border in the
accent for a comment (a region is one) and in `--text-muted` for a change (`data-cue`; both sheets,
tokens only); a detached card keeps its dashed edge. A reply's box whose card the filter hides returns to
the panel's slot with a line saying so, and Escape or Cancel moves the focus to the All button, the one
that brings the card back. The review of 2026-09-07 settled five more behaviors. Under Comments a resolved
comment's line names the Resolved fold, where its card is, and Cancel focuses that fold (`replyAway`; until
the about follow-on, 2026-09-10, a comment bound to a change was read there as one on no change, since under
All and Changes it rode the change's card and the "… N more changes" row could hide it, and Comments never
named a row it did not render; no comment rides a change card now, so the fold case is gone). The tag a
comment wears for the changes it names says each change's state, pending or detached (`refStateWords`; before
the about follow-on the "on a change" tag's title said pending only when the change was among the status's
hunks and detached otherwise, naming the Detached changes
group), and a detached change card's kind cue offers no accept or reject. A comment saved while Changes is
chosen is hidden by the choice, its highlight or rectangle with it, and a save that shows nothing reads
as one that failed: the panel keeps the saved comment's id (`hiddenSaved`) and renders a dismissable line
at the top of the list saying the comment is saved and that All or Comments shows it (`hiddenSavedRow`);
the line ends once the card shows, the comment is gone from the file, the ✕ is clicked, or the panel
closes, a later return to Changes does not bring it back, and the kept choice is unchanged; since the about
follow-on every comment is its own card, so a comment made from the change card's Comment on this change is
hidden under Changes like any other and gets the line (before it, a comment made from the change card's Reply
rode that card under Changes and got no line). Under the margin layout
(the margin-layout follow-on, above) the line is one of the list's rows and stands in the footer above Send
with the foot and the folds (`moveRows`), in view wherever the text is scrolled, where a row at the top of the
locked track is not; the save's landing (`landSaved`) finds no card for a comment the filter hides and raises no
line for it, since this row says where the comment is; and the save moves nothing, hidden card or not (decision 43;
before it, the margin's scroll to a saved card, `scrollToSaved`, found no card for such a comment and moved nothing).
The filter hides a card by leaving it out of the list (`renderCards`), never by
styling it away, so the placement pass lays out the cards the chosen option shows and no other, and a pick
repaints through `paintAll`, whose render ends in the pass (`afterRender`). The filter's row is a control row
of the head, like the toggles' above it, not growth: the margin layout's two-tier rule leaves the head in the
collapsed tier while that row is all the head holds beyond its buttons (`:has(.fc-head > :nth-child(n+2):not(.fc-filter))`
in both sheets), so the head gives only in the collapsed tier's turn while it holds its two control rows alone;
a Track choice or a refusal row still counts as growth. While the Slice 5 editor
is up the filter row is offered all the same (Show changes inline is not: the editor draws every change
itself), and the option titles say the editor keeps every change marked in its text rather than that the
marks are hidden. The rows answering a click on the toggles' row, the Track scope choice, the folder Stop
confirm and the track slot's loader and refusal, are inserted above the filter's row, directly under the
toggles (`underToggles`), and the filter's row is under the toggles again once the question is answered;
the other head rows keep their place below it. The second review round (2026-09-07) settled two more.
With no filter row to stand above (a file with nothing to filter, or no status) the track slot's loader
and refusal are inserted above the head's other rows, the status refusal's, the poll's and the editor's,
rather than appended after them, so the answer to a Track click never stands below a row about the
file. Under Comments the read view paints no change mark whatever Show changes inline says, so the
toggle stays offered (its setting is shared with All, Changes and the other panels) and its title says the
filter hides the marks and that the setting governs All and Changes, never that the text carries marks it
does not. Tests: `ui/webview/file-comments-filter.test.ts` (driven),
`ui/webview/file-comments-filter-review.test.ts` (the first round's fixes, driven over the same stand-in,
with source pins) and `ui/webview/file-comments-filter-fixes.test.ts` (the second round's, driven the same
way: the track rows with and without a filter row, the Changes empty state's stray rows, the saved line's
rectangle wording and its end when the comment's card comes to show, and the inline toggle's title
under each filter); the third round (2026-09-07) added `ui/webview/file-comments-filter-saved-line.test.ts`
(driven the same way: the saved line's pick among several fresh comments in one status, and the row's
shape, `.fc-note` on the words alone so the ✕ keeps the panel buttons' size) and
`ui/webview/file-comments-saved-line-sizes.test.ts` (the saved row's ✕ and words resolved through both
sheets' real cascade); `ui/webview/feed-css-kind-cue.test.ts` holds the sheets' kind-cue comment to the
terms above and to the declarations it describes, and `ui/webview/file-comments-filter-wording.test.ts`
holds the four driven suites' and the two size probes' titles, assertion messages and comments to the same
terms (the rule by its selector, the token by name, the focus move by where the focus goes, no figure for
any); `tools/file-review-plan.test.mjs`,
`tools/file-review-plan-kind-cue.test.mjs`, `tools/file-review-plan-filter-review.test.mjs`,
`tools/file-review-plan-filter-fixes.test.mjs` and `tests/test_guide_files_filter.py` hold this note and
the guide's paragraph to the source.

The seen follow-on (2026-09-09): two rulings of the user's on what the arrivals follow-on surfaced. The first
(decision 41): a Send had accepted eleven changes they had not looked at; they keep the box and its default, but an
unseen change is never accepted by a send. Built: the panel splits the pending changes against the seen set
(`partitionPending` in `file-comments-model.ts`, over the same entry keys `statusEntries` writes; `pendingSplit` in the
panel, empty on both sides while the editor is up), and the confirm's accept option (`acceptOption`, `syncAcceptOption`)
reads "accept the N pending changes you have seen" with, when K unseen exist, "(K unseen stay pending)"; the option no
longer says "arrived since you last looked" itself (`acceptOptionLabel`), since every unseen pending change is among the
arrivals the line under the header counts (that line's changes count takes in a detached arrival too, which
`statusEntries` files as a change with pending off and the split, over the status's hunks, never sees, so the two numbers
agree only while no detached change has arrived); with nothing seen it reads "accept the pending changes you have seen
(all K pending changes are unseen; nothing is accepted until you look)" and the box is unchecked and disabled, the
person's own choice
(`sendOpts.accept`) kept for when a look brings a change to the seen side. `doSend` accepts the seen changes by id
through the card's own accept (`mutate("accept", { ids })`, never an accept-all), over the seen set as the confirm SHOWED
it (`confirmSeen`, written at the confirm's render and rewritten with the option's words after a gesture; `pendingSplit`
reads it while a confirm is up), so what the option and the count row said when the person pressed Send is what goes,
and states in the message the count the accept's reply lists (`accepted`), never the confirm's. The press is a gesture
and marks a card on screen seen as any gesture does, for the NEXT confirm and not this send (`sendPress`: the send's own
press, a pointer's or the key's, leaves the option and `confirmSeen` as the person read them; for a pointer press the
row's hold, `pressHold`, parks the change in place until after the click as well). The review of 2026-09-09 found the
send reading the live set after the press's own mark, and accepting a change while the box still read disabled and
unchecked with "nothing is accepted until you look", words the hold had kept through the press. Any other gesture while
the confirm is up moves a card it shows to the seen side in place (`reflectSeen`), rewriting the option's words and its
checked and disabled state, the count row and `confirmSeen` through the same `syncAcceptOption` the render uses. Seen is
keyed by the change's id and its texts (`seenTexts`, recorded with the seeds, at a gesture and for the person's own writes:
`recordSeen`, `recordPending`): a same-author `track-edit` landing inside or beside a pending change is coalesced into it
under the same id, so a status can bring a seen id with text the person has not read. A seen pending change that reads
differently from its record leaves the set and is filed as an arrival again (`noteArrivals`, `grownSince`, the same
comparison the decisions stand down on, `changedSince`): its dot, the line under the header and the unseen count name it,
the next gesture with its card on screen sees it anew, and the person's own change stays seen whatever it reads (the
review's third round, 2026-09-09: before it the send accepted a change grown under a seen id and the confirm counted it
among the seen; `file-comments-seen-review3.test.ts` drives the case). The
second ruling (decision 42): the message's `track-edit --thread <id>` line, which bound a revision to the comment so the
card showed the edit inside it, confused them and is gone: both builders (`buildSendMessage`, the kernel's
`_file_comments_message`) say plain `track-edit` for edits and `track-reply` for answering a comment in words, the
vendored skill says the same (patch 0006), and the host's decisions never resolve a comment (`requireCommentsUntouched`
holds the staged comments to the loaded ones apart from `anchorAt`). With nothing resolved by an accept, the confirm's
"resolves M comments" clause and the acknowledgment line's tail are retired. Tests: `file-comments-model-seen.test.ts`
(the split and the words), `file-comments-send-seen.test.ts` (the stand-in: two seen and one unseen accept the two by id
and leave the third pending; all unseen make no accept call and a disabled box; the words follow a gesture in place and
on the re-render; the message's count is the reply's), `file-comments-send-seen-browser.test.ts` (Chromium and Firefox,
the two-seen-one-unseen scene), `tests/test_guide_files_seen.py` (the guide's sentence held to the panel) and
`tools/file-review-plan-seen.test.mjs` (this note held to the code and the modules it names),
`tools/file-review-plan-seen-review.test.mjs` (the review's plan fixes: the arrivals paragraph's retired option words and
save scroll stated as history, the acknowledgment line named as CONTEXT.md names it, the contract paragraph's check held
to the host's call sites, the margin-fixes and model-seen accounts held to their modules) and
`tools/file-review-plan-seen-review-2.test.mjs` (the second round's: the send's split over the confirm's set and the
press's mark for the next confirm, the seen rule as the card alone, the unseen count against the arrivals line's, and the
save's retired scroll stated as history wherever this document names it, each held to the panel and the model),
`tools/file-review-plan-seen-review-3.test.mjs` (the third round's: the saved line's place stated by layout, the keys that
are no gesture against `NAV_KEYS`, the acknowledgment never a note across a wrap, the Tests bullet's modules against the
tree) and the rounds' own modules (`file-comments-seen-fixes.test.ts`, `file-comments-seen-review2.test.ts`,
`file-comments-seen-review2-browser.test.ts`, `file-comments-seen-review3.test.ts`,
`file-comments-seen-review3-browser.test.ts`, `feed-css-saved-line-head-dress.test.ts`,
`tests/test_guide_files_seen_definition.py`,
`tests/test_guide_files_saved_line_layout.py`, `tools/file-comments-host-untouched.test.mjs`,
`tools/file-comments-host-review-seen.test.mjs`; the Tests section says what each drives).

The arrivals follow-on (2026-09-09): two rules, both from the user's reports of the day. The first report: the user
sent comments, the session answered with eleven changes and seven replies while they kept commenting, and nothing in
the panel said so; the first they knew of them was the next Send accepting the changes by default. Built: the panel keeps
the set of ENTRIES the person has seen (a pending or detached change, a comment, a reply, each by a key:
`statusEntries` in `file-comments-model.ts`), seeded at its first render with a status from everything in it and again
from the first status to land with the panel open (`seenOpen`: the render's status is the mount's probe, asked with the
panel closed, and the open's own re-ask lands after it, so a file opened fresh has no arrivals, whatever the session
added between the probe and the open — the review, 2026-09-09), and every status after that files an entry by another
author that is not in the set as an ARRIVAL (`noteArrivals`); the person's own writes, `you` by decision 6, join the set
outright and are never arrivals. The rule reads the sidecar's author label as the cards' chips do: a record labelled
`you` is the person's whoever wrote it, and one under any other label is not, whatever its `authorId`. While any arrival
stands, one line under the header names them in the model's words (`arrivalWords`: "api
made 11 changes and 7 replies since you last looked", singulars handled, "and N comments" when the session added
comments of its own, the authors named as the chips name them and several joined with "and"), a button through the
delegate table (`fcarrivals`) whose click shows the first arrival in the list's order as the focus (`goToArrival`,
`showCard`; when the list shows none of them the filter goes to All first); the arrival cards and their marks in the
text wear `data-new`, a dot in the accent at the head's left and in a mark's corner, in both sheets' file-comments
block. Seen is event-based (`gesture`): a gesture of the person's marks every arrival whose card is then in the
track's box seen (`entryShown`: the placed top inside the box; the list layout reads the card's box against the
aside's and the window's), and the ones it scrolled into view are seen by the gesture that follows; a card not
rendered, behind a fold or the filter, is not on screen and stays an arrival. A gesture is a pointer press or a key
anywhere in the body row, a wheel or a touch move (the two events that begin a scroll of the person's: the scroll
event itself is not one, since the lock's writes and a centering fire it with no gesture behind them, as the save's
scroll did while it stood (decision 43 retired it), and a wheel fires before the scroll it starts), a save, a send;
never a timer. A Tab or a modifier pressed alone (Shift, Control, Alt, AltGraph, Meta: `NAV_KEYS`) is no gesture: it moves
the keyboard or begins a chord and scrolls, edits or presses nothing, and the key or the click that follows is the gesture;
counted as gestures they ended the saved line before the keyboard could reach it, a Tab from the Send button removing the
line the focus was moving to (the review's first round, 2026-09-09; `file-comments-seen-review2.test.ts` drives the Tab
and each modifier on both lines). The line's own press marks nothing, so the click that shows an arrival does not mark it
seen; the dots and the line change in place rather than by a render, the line through the row's press hold (`pressHold`),
since a line removed during a press moves the list under the pointer. The Send confirm's accept option read "accept the N pending
changes (M arrived since you last looked)" when arrivals included pending changes, until decision 41 (the seen follow-on
above, the same day) moved it to the seen split: it names the pending changes the person has seen and the unseen ones
that stay pending, and says nothing of arrivals, which the line under the header counts (`acceptOptionLabel`; the seen
follow-on's paragraph carries the words); the default stays decision 8's; the same confirm lost its message preview
to a box for the person's own words the same day (decision 40), which travel first in the message as `note`. From the
lost-update probe of the same day: the accept then resolved the comments bound to the changes it accepted (the host's
rule at the time), and in the incident seven comments the session's edits had answered folded under a collapsed Resolved
with nothing said; the option gained a
"resolves M comments" clause and the acknowledgment line a tail naming what moved to Resolved. Decision 42 (the same
day) ended the host's resolve-on-accept, so nothing leaves the visible list on a send any more and both went with it (the
seen follow-on above). The set lives with the
panel: a Raw/Rendered switch, a reload and a close and reopen of the aside keep it, and a new file is a new panel. The
second report: they saved a reply, scrolled on while the host answered, and the reply's landing pulled the text back to
the card (the save's scroll above, from the 2026-09-07 review, ran unconditionally). Built first: `saveComposer` counted
the save as a gesture and sampled the count when Save was pressed, and when the reply landed the save scrolled only if
the count stood (no gesture of theirs in between) and the saved card was not already whole in the track's box.
Decision 43 (the seen follow-on, the same day) retired the scroll: a save never moves the view, the count went with the
scroll it judged, and `landSaved` makes the saved card the focus for the layout (`focusOn`), so it lands level with its
mark wherever that is. When the card is not whole in view once the save's status has landed (`cardWhere`: the placed
top and height against the track's scroll and box in the margin layout, the card's box against the aside's in the
list), in the margin layout the acknowledgment line's position at the panel's foot reads "Saved · the card is above" or
"below" (`savedLine`; the words are the model's, `savedWhereWords`), a button whose click scrolls the card into view as the
focus (`fcsavedgo`: `scrollCard`); in the list layout the same button stands under the header (`savedLineHead`, appended by
`renderHead`), since the list's Send section is the scroller's foot, below the very card the line says is below, so a line
there was never on screen when it was wanted, and an earlier send's acknowledgment keeps its place at the foot there where
the margin layout's gives way to the line (the review's first round, 2026-09-09). The acknowledgment the margin layout's
line displaces comes back in its place when the line ends (`sentAck`, set with the acknowledgment by `doSend`;
`restoreSent`, from `reflectLines` at a gesture and at the settled re-read that finds the card in view, and from the
panel's close), so the foot never shows neither; the next confirm's opening clears the acknowledgment and the copy it
kept, and a line standing then comes down on nothing, the next send's acknowledgment taking the place (the review's third
round, 2026-09-09: a reply's landing read its card, taller with the composer's box inside it, as below the box, the close
re-laid the card whole in view, and the pass's re-read ended the line with the acknowledgment gone;
`file-comments-seen-review3.test.ts` and its browser leg drive the scene). The side is latched at the landing
(`savedOut`), since a render swaps in a card list the pass has not sized yet and the track's scroll reads 0 until it has,
and re-read where the geometry is settled, at the end of a pass and at a scroll (`reflectLines`, through the row's press
hold as the arrivals line is: a line leaving the Send section moves the Send button under a pointer); the line ends there
when the card is in view, and at the person's
next gesture (`gesture`; a press on the line itself excepted, its click being what it is for). No timer. The composer's
acknowledgment is unchanged. Tests: `file-comments-model-arrivals.test.ts` (the pure half),
`file-comments-arrivals.test.ts` (the stand-in: both rules driven), `file-comments-arrivals-browser.test.ts` (Chromium
and Firefox), `tests/test_guide_files_arrivals.py` (the guide's two sentences held to the panel),
`tests/test_guide_files_save_line.py` (the save sentences' gesture words derived from the listeners) and
`tools/file-review-plan-arrivals.test.mjs` (this note held to the code and the modules it names).

The about follow-on (2026-09-10): the user's answers to the decoupling assessment of 2026-09-09 (a report kept
outside the repo, at ~/romp-handoffs/romp-filereview-notes/decouple-assessment-report.txt), three rulings and one
requirement. The first: a comment should say which changes it is about, by the
user's own pick, not by the session's stamp; built as `changeIds` on the comment (decision 45), the third romp-only
additive field. The second: one list with the All / Comments / Changes filter, no tabs and no second section. The third:
nothing resolves a comment except the user, with a bulk action for the comments the session has answered (decision 46).
The requirement: a comment inside a tracked change is an ordinary comment, never turned into a reply on the change
(decision 44's rule, kept here with the about option). Built: the host's `comment` op takes `changeIds` (each id a
pending or detached change, else `no-change` naming the missing ids), the suggestionId request branch is gone and a
request naming one is a caller bug, `decidedFor` collects both fields, and romp writes `suggestionId` never again
(`tools/file-comments-host-about.test.mjs`). The model reads a comment's changes as `refs` (`refIds`, `commentRefs`:
source about for `changeIds`, answered for a legacy `suggestionId`, each with its state through `boundChange` and its
texts), `CardKind` loses "change" and `Card` loses `hunk` (a comment about a change with no passage is kind file with the
changes' words as its reference), `changeCards` drops the hosted comments for a count of the open comments naming the
change (`commentsAbout`), and `describeComment` names the passage or the region first and then the changes, in the
change card's words (`aboutClause`, `changeWords`: `on "<quote>", about your change "<old>" to "<new>"`; a truncated tail
names an unknown change by id), so the sent message says which changes a comment is about; the kernel's builder prints
the desc verbatim, unchanged in code, its docstring naming the forms and the parity suites rendering them
(`file-comments-model-about.test.ts`, `tests/test_file_comments.py`, `tests/test_injected_voice.py`). The panel draws
no comment inside a change card any more (`renderHosted` and `.fc-hosted` are gone from the panel and both sheets;
`cardKey` answers the comment's own id): every comment is its own card in the one list, the change cards first under
All. The change card's Reply is Comment on this change (`fcchangecomment`, `startChangeComment`): the composer opens in
the panel's slot anchored over the change's span in the current text, the presel over it, with an about option checked
(`aboutOption`, `input[data-opt="about"]`, "about this change"), and Save posts `changeIds: [id]` beside the anchor; a
deletion, whose text is not in the file, takes the comment by id alone, the reference row saying "About the change …"
and, in one line, that the comment is laid at the change's point (`markTop`'s fallback lays an anchorless comment's card
level with the first pending change it names, and after that change's card, since a tie on the top lays in the list's
order, but for a tied pair above a focus with room for the comment but not for both, where the change is the one laid
below the focus and the comment holds the start: the margin-layout record above) or, in the list layout, where no card
is laid at any point, that the comment names the change instead of a passage (the review's second round, 2026-09-10).
For a spanned change, an insertion or a substitution, the card offers
Comment on this change only while the view carries the change's text (`spanCarried`: the view's bytes are the status's,
whose offsets place the span (`textCurrent`); there is a text to cut it from (`indexedText`: the view's, or while the
editor is up the file as the editor loaded it, never the buffer); and the view shows text at all, not the picture of a
media file); in flux, a reject's reply landed and its reload not, or the poll's reload landed and its status not, the
card shows Accept and Reject alone, no Comment on this change, and a click that reaches `startChangeComment` anyway
writes nothing, since the composer over the span would quote other bytes and a comment by id alone would lose the
passage the change has; the button comes back with the bytes, as an unpainted change's Reveal and its "not shown" tag
do on the same ground (`inFlux`), while a deletion's, by id, stands whatever the view shows (the review of the slice,
2026-09-10; before it a spanned change in flux took the deletion's by-id composer and Save wrote a comment with no
passage though the change has one). A selection overlapping pending changes' marks (`overlapping`: an
insertion's or a substitution's span sharing a character with the range, a deletion's point strictly inside it; nothing
while the view shows other bytes) gets the same option, "about N changes" for several, checked; unchecked, Save writes a
plain passage comment (`About.on`). A selection over a deletion's struck label alone holds no text of the file (the
mapping refuses or maps an empty range), and the composer offers the comment about that change by id (`deletionUnder`:
the one deletion mark the selection's range intersects). Both cards wear tags: the comment "about a change" or "about N
changes", "answered by a change" for a legacy binding (`aboutTagWords`), the title the changes' words and states
(`refStateWords`), and the pointer over it rings the pending changes' marks in the text (`lightChanges`, `.fc-lit`, a
render unlighting first since the tag under the pointer is rebuilt); the change card "N comments" (`fc-about-count`), a
control whose click shows the first open comment about the change, All chosen first when Changes hides the comment
cards (`fcaboutfirst`, `showAbout`; the keyboard's activation through `KEY_ACTS`). The "on a change" tag, the change fold case of
`replyAway` and the held head of a change card go with the hosting. The Send confirm and the message are otherwise
unchanged. Tests: `file-comments-about.test.ts` (the stand-in: the list, the tags and the ring, the count tag's click and
key, Comment on this change on a substitution and on a deletion, the option unchecked, a selection inside an insertion,
across two marks, reaching a deletion's point and over its label alone, the sources), `file-comments-about-browser.test.ts`
(Chromium and Firefox, Rendered with the marks shown and hidden and Raw: the composer over the real span, a real drag
inside an insertion and a substitution's new text, the option unchecked, a drag across the insertion's end with its
highlight painting in the other view too, the deletion's label and the card laid level with its mark, the ring's computed
outline, the count tag's click), `file-comments-model-about.test.ts` (the pure half),
`tools/file-comments-host-about.test.mjs` (the host), `tests/test_guide_files_about.py` (the guide's sentences held to
the panel) and `tools/file-review-plan-about.test.mjs` (this note and decisions 45 and 46 held to the code and the
modules they name). From the about follow-on's review (2026-09-10): `file-comments-about-fixes.test.ts` (the stand-in
with the editor's seam: the span cut from the file as the editor loaded it, Comment on this change withheld in flux and
in media mode and standing on a deletion, a refused selection crossing a deletion's mark, a BOM file's offsets,
`deletionUnder`'s one mark, the open card's line naming the changes), `file-comments-resolve-answered-fixes.test.ts`
(the confirm's end when nothing answered remains and at the panel's close, the editing consent asked once, the Reopen
all row's dress and place, a wheel ending the offer under focus), `tools/file-comments-host-about-scale.test.mjs` (the
host's id walk in linear time: a hundred thousand ids refused `no-change` inside the kernel's deadline) and
`tools/file-review-plan-about-flux.test.mjs` (the withholding as recorded here and in the Slice 2 build paragraph held to
the panel and the stand-in). From its second round (2026-09-10): `file-comments-about-review2.test.ts` (the stand-in
with the layout switchable: the composer's about ids pruned as a status retires a change, a selection starting exactly at a deletion's point, the
deletion marks a drag crosses, the kind cue's title by source, the ids-only line by layout),
`file-comments-resolve-answered-review2.test.ts` (the Reopen all offer's place by layout and the keyboard after a run
the confirm's Resolve began from the keyboard) and `file-comments-arrivals-about.test.ts` (a session's reply on a comment
about a pending change shows on the comment's own card, never the change's).

### Slice 3: region comments on images

User-visible: on a standalone image, or on a figure embedded in a rendered markdown file, the
person drags a rectangle and comments on it; the rectangle paints over the image with the
author's chip, and the card shows a thumbnail crop. When the image's bytes change, its region
comments show as stale until resolved or re-placed. The sent message names the region. Desktop
only in v1; on the phone the whole-file comment stands in.

Acceptance: a region comment carries `target {kind: "image", region, hash, src?}` in fractions of
the image's natural size, plus the embed-line anchor and `src` when the figure is embedded, and no
anchor when standalone; `track-reply` replies into it; the Obsidian and VS Code hosts show it as a
discussion card (embedded: on the embed line) and preserve `target` on their next write; a
regenerated image flips the comment to stale by `hash`; the rectangle re-paints correctly at any
viewer width.

Files: `file-comments.ts` (the overlay, the drag, the crop), `file-view.ts` (a hook exposing the
rendered image elements), the host script (`comment` accepts `target`; `hash` computed from the
bytes), `kernel.py` (none beyond passing the field), CSS. Dependency: the non-text refusal in the
guard and `track-edit`, which lands in Slice 1; the `target` field is romp-only (decision 13).
Size: ~250 / ~10 / ~40.

The Slice 3 build (2026-09-06), host side: the stored target is `{kind, region, page?, hash, src?}`
in that key order, `src` on an embedded figure only (the contract's `target` bullet says why the
destination is stored rather than derived). `hash` is the host's sha256 of the figure's bytes,
streamed and never decoded, since the UTF-8 read every other verb makes is lossy for an image; the
client's value, if any, is ignored. `comment` runs its checks in a fixed order. The fence's shape
and the target's shape come first, before any disk read, and a bad shape is a caller bug: `kind`
image or pdf, the region inside the unit square at four decimals, `page` on a pdf only, `src`
exactly when the comment has an anchor, `figureHash` a sha256 hex and only with a target. Then the
anchor is placed, and the anchored passage must embed the `src` the target names
(`figure-mismatch`, a refusal rather than a caller bug: a reference definition can change on disk
between the drag and the save). Only then is the figure resolved and hashed: `unreadable` when the src
is a URL, resolves outside the project root, or is not a regular file; a caller bug when its
extension is not the kind the target claims, or one the viewer never shows as media; `too-large`
past the 50 MB the viewer shows, refused before a byte is read (before this cap a multi-GB src
pinned the host until the kernel's deadline); and last, when the request's fence carries
`figureHash`, `figure-changed` unless the bytes hashed are the ones it names (the Slice 3 review,
2026-09-06: before this fence a figure regenerated between the drag and the save was stamped with the
new bytes' hash, which every reply then equalled, so the panel read a rectangle drawn on the old
picture as current on the new one, the one write the hash exists to catch). The host checks that
fence whenever a request carries it, and the kernel passes the fence object through whole. The
panel sends `figureHash` on `comment` with a target and on `retarget`: the hash its status holds for
the figure (`fileHash` on a standalone image or PDF, `embeddedHashes[src]` on an embedded figure),
and none when the status holds none (the first comment on an embedded figure no comment yet names
has nothing to fence on, since the host hashes only the srcs the sidecar names; a fence the panel
cannot arm is left off, never guessed). A `figure-changed` refusal is never retried; the panel
re-reads the comments and the view, as it does when the poll sees a figure move, and shows the
refusal with Reload, the comment kept (the review consolidation, 2026-09-06; the build first sent the
three mtime keys only, so the host's fence stood unarmed). `retarget` is the
same path for the same figure: a stored `src` must be named again, unchanged, and the same fence
applies. The reply's hash fields are described under the op above. A text file's figures are
hashed under one 200 MB budget per call; past it, or when a src fails a check, the hash is null
with the reason beside it, not a refusal. A stored target with an anchor and no `src` (the
contract's first shape) is told its figure from its passage on every reply and on a re-place that
names none, and refuses `no-figure` when the passage embeds none or several distinct ones (one
figure embedded twice still tells). A `src` is decoded as the viewer decodes it before it resolves
(`p95%20latency.png` is the file with the space) and stored as written. Panel side: the poll HEADs
every figure a text file's open region comments name beside the file and the sidecar, so a
regenerated embedded figure re-asks `status` and flips by hash; the reply carries each named
figure's mtime from the read its hash came from (`embeddedMtimes`, by src, absent where the figure
could not be read), which seeds the poll's baseline for it as `fileMtimeNs` seeds the file's, so a
figure regenerated between the host's read and the poll's first HEAD is a move on that tick and not
a first observation (the review consolidation, 2026-09-06; before it that window left the card
reading current until the next status or move); a resolved comment's card shows the
resolved tag alone (no stale tag, no Re-place, no rectangle), so a figure only resolved comments
name is not watched, and reopening one is a write whose reply carries the hash to flip it by; the
sent message names the figure of a region comment on an embedded figure; a stale card offers
Re-place. `kernel.py` is unchanged, as the Files line says.

### Slice 4: PDFs rendered in the viewer, with page and region comments

User-visible: a PDF opens as rendered pages inside the viewer instead of the browser's own frame,
with the same Comment on this file button and the same rectangle gesture per page; a region
comment names its page; the card shows the page crop once its page has been drawn (pages draw as the
reader nears them), and until then a line naming the page that scrolls it in.

Why a slice of its own: the browser's PDF frame gives the page no coordinates or selection, so
region comments need romp to render pages itself. Ruled (decision 12): a lazily loaded PDF chunk
built on pdf.js (Apache-2.0, matching romp's license), in the same on-demand pattern as the editor
chunk, loaded only when a PDF opens; the fallback for a failed chunk load is today's frame with
whole-file comments only. The alternative, rasterizing pages on the owning kernel with a
command-line tool, was rejected as a new kernel-side tool and route.

Acceptance: pages render within a stated size cap for PDFs, loudly refused above it; a region
comment carries `target {kind: "pdf", page, region, hash}`; a regenerated PDF flips its region
comments stale; `track-reply` replies into them; the main bundles stay byte-stable with the chunk
lazy.

Files: new `ui/webview/pdf-chunk.ts` esbuild entry, `file-view.ts` (the PDF branch mounts the
chunk when the panel is open, else the frame), `file-comments.ts` (per-page overlays), the host
script (no change beyond Slice 3), `kernel.py` (a size cap for the chunk's fetch). Size: ~350 /
~20 / 0.

### Slice 5: live CodeMirror editing over pending changes

User-visible: Edit works on a tracked file with pending changes; CodeMirror shows insertions
tinted and deletions struck inline; typing remaps the changes rather than desyncing them; click
accepts, modifier-click rejects; undo restores an accepted change; Save writes file and remapped
sidecar together, and the Edit refusal disappears.

Acceptance (as built): the cases of track-changents' `obsidian/tests/track-cm.test.mjs` and
`track-cm.undo.test.mjs`, ported case for case from vitest to `node:test` as
`ui/webview/track-cm-oracle.test.ts` — their `createRequire` loads of `../src/track-cm.js`,
`track-changents/engine`, `@codemirror/state` and `@codemirror/commands` are imports the test
bundle resolves to the vendored field, the vendored engine and the one CodeMirror the editor
chunk bundles — pass as the behavioral oracle; a save refuses when either mtime moved and keeps
the buffer; `editor-lazy.test.ts` pins that the main bundles stay byte-stable.

Files (as built): `editor-chunk.ts` carries the track field, the decorations and the click
handling inside the editor chunk's own bundle, reached through the typed `track` mount option
curated inside `extensionsFor` and consumed only by `file-view.ts` (decision 14; the header
doctrine comment names it): the 78-line CodeMirror state field (`obsidian/src/track-cm.js`,
bundled unchanged) and the engine from the vendored copy, and the decorations block adapted as
`ui/webview/track-decorations.ts`, derived from the pristine vendored
`obsidian/src/track-snapshot.js` (the inline-overlay block at the pinned commit, cited in its
header) with the display-planning and click and layout helpers it calls, the one Obsidian read
replaced by a constant and the `mouseover` handler taking the editor view (survey A6);
`file-view.ts` `doSave` sends the `save` verb instead of `saveFile` when the panel routes the save
(`setTrackedEdit`, below). The one slice that touches the editor chunk's contract.

The Slice 5 build (2026-09-06): the track field, the marks and the click handling live inside
the editor chunk's own bundle, reached through the typed `track` mount option (decision 14),
because two bundles that each carry `@codemirror/state` cannot share a page; there is no
separate comments chunk, and the oracle tests run under `node:test` as
`ui/webview/track-cm-oracle.test.ts`. The viewer knows nothing of sidecars: the panel
registers its half through one seam member (`setTrackedEdit`: what rides into the editor at
Edit, whether Save goes through the host, and the save itself), and the viewer answers
`text()` from the buffer and says `editing()` while the editor is up, so the panel's paint
pass and the poll's file reload stand down. The save is fenced on the two things it writes: the
sidecar the records came from (the status at Edit, not the poll's latest) and the file the
editor loaded. It does not fence on `config.json`, which it only reads, as the disk stands at
the save, to decide whether the edit is logged; a `configMtimeNs` a client sends is not read
(`tools/file-comments-host-save-guards.test.mjs` pins this), and `set-tracked`, the verb that
writes the config, is the one that fences on it, as the wire section says. A moved sidecar is
retried once when the sidecar's records are still the ones the editor carries (a reply a session
wrote mid-edit), a moved file never; there is no `config-moved` refusal for a save to retry. An
older editor bundle that ignores the option is detected by the handle it returns, and Edit then
refuses with the Slice 2 wording; a bundle that fails to load over pending changes refuses the
same way rather than falling back to the plain editor. A CRLF file with pending changes refuses
Edit: the editor normalizes line endings, which moves every offset the records hold.

### Optional: per-comment fork dispatch

A card's **Discuss in a side session** forks the owning session at its tip with the comment's
message as the opener, through the door built for it (`_fork_comment_request`,
`kernel.py:10981-11023`), and the existing comment-thread popover shows the fork's conversation.
SDK sessions only; each fork is a CLI holding the parent's context, so per comment and never by
default. `_fork_promote_request` returns `name` only today (`kernel.py:11043, 11047, 11052`)
while the track-changents consumer reads `promotedName` (`obsidian/src/track-snapshot.js:1445`),
so this slice adds `promotedName` beside `name` in all three success arms, with a test. A WS op
wraps the POST so the webview needs no serve token. Parked until asked for (decision 1). Size:
~60 / ~20 / 0.

## Security posture

Stated rather than silently widened, as the file-browser plan did for saves. On the kernel side
the posture is unchanged in kind. `fileComments` is issuable from any authenticated socket, like
`saveFile`; every verb that writes disk sits behind the same server-side consent gate, checked
before any content check; the server-side gate is the enforcement and the UI's checks are
convenience. The host script runs only on the owning kernel, on paths resolved by the kernel (and, from
Slice 3, on the figure paths the next paragraph describes, the one class of path it resolves
itself), and writes only the sidecar, the comments log, `config.json`, (on reject or save) the
commented file, and, for the length of one write, the lock beside the sidecar or the config
(`<name>.lock`, decision 49), created with O_EXCL, which no link can redirect, and, for the few calls of a
stale lock's break, the claim its waiters serialize on beside that lock (`<name>.lock.break`, created the same
way; decision 49). Those two names, and the one `made-dir` line a writer that made the folder appends to
another writer's lock or claim when it leaves first, are everything the lock leaves under `.trackchanges/`; a
link or another non-file at the lock's name, or at the claim's while a stale lock stands, refuses the write as
`unreadable`, never followed and never removed. The mtime fences refuse and never merge. Both ops route by `sid` to the owning
kernel over the existing federation splice; nothing new is exempt from `_authorize`, and the
panel's verdict rides the authenticated `/defaults` payload rather than `/version`. Nothing under
`.trackchanges/` is read or written through a symbolic link: the sidecar, the comments log and
`config.json` are named from the file's path and never shown to the person, and a checked-out
repository can commit anything under those names, so a link there would carry a write outside the
four files above; every verb refuses `unreadable` when any of the three, or `.trackchanges/`
itself, is a link or otherwise not a regular file, the log is opened `O_NOFOLLOW`, and every temp
file the host creates takes a random name with `O_EXCL`. The commented file is the one path
written through its link, on purpose: the person chose it (the Slice 2 review, 2026-09-06). The
installer's new step registers a PreToolUse hook that runs on every Edit and Write in every Claude
Code session on the machine; it exits at once in any session romp did not launch (no `ROMP_SID`),
and in romp's sessions it is a path check that passes untracked files through.

From Slice 3 the host also reads one class of path the kernel did not resolve: the figure a region
comment's `target.src` names (the Slice 3 build, 2026-09-06). The client names that path on
`comment` and on `retarget`, and every reply reads it back out of the sidecar; the host resolves
it. It is only ever read, to hash it: the sha256 of its bytes is what the reply carries, and
nothing under it is written or served. The host bounds the read itself. The src is decoded as the
viewer decodes it, refused when it is a URL, resolved against the commented file's directory, and
confirmed by realpath to lie inside the project root (never above it, not out through a symlink,
and an absolute src held to the same check) and to be a regular file, opened non-blocking so a
FIFO or a directory fails at once instead of hanging. On a write verb the src must also be a figure
the anchored passage embeds (`figure-mismatch`), of the kind the target claims by its extension,
and under the 50 MB the viewer shows, refused before a byte is read. On a reply the host hashes
every in-root regular file the sidecar's srcs name, of any extension, under one 200 MB budget per
call; a src that fails a check gives a null hash with its reason rather than a refusal, so a
comment another writer left is shown as unknown and not hidden. The reply's read runs on `status`
too, outside the consent gate, as reading the commented file does. This widens by one step what
an authenticated client can learn, and the step is stated here rather than left implicit: a
writer that can already put a src into a sidecar (the agent CLIs, or the viewer, whose Save edits
a sidecar like any text file when the consent is on) can learn the sha256 of any regular file
inside the project root by naming it there, never its bytes, including a file the viewer would not
serve because it never renders that extension. A socket with no such write names only a figure its
anchored passage embeds. Refusing on a reply what a write verb refuses (a non-media extension, a
src the passage does not embed) is the follow-up if that hash is judged worth withholding; the
Risks bullet on figure paths names the trade.

Slice 4 widens the browser side, and in kind: PDF parsing moves into the dashboard's origin.
Before it, a PDF in the viewer was an iframe over the bytes, parsed by the browser's own PDF
viewer in a process of its own, apart from the dashboard's document. While the Comments panel is
open, the viewer hands the same bytes to pdf.js instead (the `/file` response it already holds,
fetched with the dashboard's cookie; no second request, no new route, no kernel-side tool, per
decision 12). pdf.js parses them in a module Worker on the dashboard's origin,
`/dist/pdf-worker.js`, served behind `_authorize` like every `/dist` asset, and paints each page
onto a canvas on the main thread, embedded fonts included (through `FontFace`). A PDF is
untrusted input: sessions download PDFs into the trees the viewer shows, and the person opens
them. A parser fault that reached script would run on the authenticated origin, where the
browser's viewer would have contained it. pdf.js is JavaScript, so a malformed file cannot
corrupt memory as it could in a native parser; a parser bug becomes script on the origin only
through a sink that executes code or inserts content, and the properties below remove every such
sink. The dashboard already interprets untrusted files on this origin under the same discipline
(marked and DOMPurify over markdown, the highlighter over source); a PDF joins that list.

What bounds the widening, each a property to keep across every pdfjs-dist upgrade and every later
slice, pinned against the code by `ui/webview/file-review-posture.test.ts`:

- **`getDocument` receives `data`, never a URL.** pdf.js issues no request of its own, and the
  chunk fetches nothing.
- **No eval path.** The installed pdfjs-dist (6.x) has no `eval`, no `new Function`, and none of
  the `isEvalSupported` switch of earlier majors, in the main build or the worker. This is a
  property of the installed version, not of the API: an upgrade re-verifies it before landing and
  restates it here if the answer changes.
- **Pixels are the only sink.** The chunk imports pdf.js's core alone, never `pdfjs-dist/web`: no
  text layer, no annotation layer, no forms, no XFA, no scripting manager, so no PDF content
  becomes DOM, a form field, a link, or a script. Page painting runs at pdf.js's default,
  `AnnotationMode.ENABLE`, which draws annotation appearance streams onto the canvas as pixels and
  nothing else. A later slice that wants selectable text or clickable links on a PDF page widens
  this list and says so here first.
- **Two caps, refused by name before any work.** 25 MB of bytes before pdf.js sees one; 5,000
  pages once the document has opened and before a page shell exists.
- **The fallback is the old boundary.** A chunk that fails to load, a document pdf.js refuses, or a
  PDF over either cap gets today's frame, the browser's own viewer, with whole-file comments and a
  line saying why; the widening never keeps a PDF from opening.

## Doctrines this respects

- **Philosophy** (`CLAUDE.md`): the count is the glance and the panel one click deeper; Send to
  session batches N comments into one interruption; never-lose-the-thread holds on disk, since
  comments live in the sidecar before any send, detached comments and changes are kept rather
  than dropped, the todo stamps only at delivery, every file-changing verb traces to the session,
  and the comments log keeps what the sidecar forgets.
- **Event over time** (`CLAUDE.md`, Design): the poll stands in for an event source the Files
  pane does not have; the person's own writes never wait on it, since every verb reply carries
  fresh mtimes that rebase the poll.
- **The veil** (`CONTEXT.md`): the sent message, the trace, the skill sentences, and the
  default-prompt sentence speak as the person and name no romp nouns.
- **No plugin API** (`ui/webview/editor-chunk.ts:1-15`): Slices 0 to 4 never touch the chunk.
  Slice 5 adds a typed, internal `track` option, not a generic extension hook.
- **UI rules** (`ui/CLAUDE.md`): click-safe delegation, keyed expand state, one font-size
  vocabulary, `var(--accent)`, the romp loader on waits, no dead ends.
- **Coordination**: the implementing session works on its own worktree and publishes a working
  note naming `kernel/kernel.py` (the two ops), `file-view.ts`, `waiting.ts`, `files.ts`,
  `editor-chunk.ts`, `install.sh`, and `claude/romp-session-prompt.md` before editing; several
  live sessions edit `kernel.py`.

## Risks

- **Two writers on one sidecar** (agent CLIs and the host script). Mitigation: one
  load-mutate-write per verb, mtime fences, refuse-and-reload, retry by stable id while the change
  still reads as shown (the id-less verbs stop and re-read), and since 2026-09-11 one lock per
  sidecar, shared with the CLIs, that serializes the writers (decision 49); the fences catch the
  stale copy, the lock the concurrent writer. The Obsidian
  host spends several hundred lines on this race; the fence-plus-retry shape is the smaller
  alternative. The comments log has one writer, the host script, appending.
- **Rendered markdown versus offsets.** Mitigation: Raw is exact; Rendered maps through the
  lexer walk with per-token verification and refuses rather than mis-anchoring; the fallback
  painter reuses the whitespace-tolerant matcher in `ui/webview/comments.ts:86-162`; a deletion
  there is a point placed through the same index map, card-only where the map refuses (the
  inline-display follow-on, 2026-09-07; before it every Rendered deletion was panel-only); every
  change and comment has a card, and an unpainted change's Reveal opens Raw; a comment whose
  selection cannot be mapped offers Raw.
- **Raw direct edits desync changes before Slice 5.** Mitigation: the Edit refusal from Slice 1
  on.
- **Tracking off before a session writes.** Mitigation: folder tracking before the files exist,
  the Send to session checkbox that turns tracking on, and a guide paragraph saying to track the
  folder a session will write into.
- **Tracked folders that hold figures.** The guard would send an agent to `track-edit` on an
  image, which corrupts it. Mitigation: the non-text refusal lands in the vendored guard and
  `track-edit` in Slice 1, before folder tracking ships.
- **A figure path the client names** (Slice 3). `target.src` is a path the host resolves itself,
  and a reply hashes every src a sidecar holds. Mitigation, the bound Security posture states in
  full: decoded as the viewer decodes it, no URLs, realpath containment in the project root, regular
  files only, on a write the anchored passage must embed it and its extension must match the
  target's kind, 50 MB per figure on a write and one 200 MB budget per reply, and on a reply a null
  hash with its reason where a check fails. What the read yields is a hash, never bytes. The trade
  left open: a reply hashes an in-root file of any extension so a comment another writer left is
  not shown as unknown, which tells a client that can already edit the sidecar (the consent on)
  the sha256 of an in-root file the viewer would not serve it; refusing such srcs on a reply is the
  follow-up if that is judged worth withholding.
- **A file moved or renamed by the session.** The sidecar is keyed by path. This plan first said
  the store layer re-finds a moved file by content hash on load. The Slice 1 build (2026-09-06)
  found otherwise: `store-io` heals only when `healOrphanStore` is called explicitly (the VS Code
  host calls it; `loadStoreStatus` and the CLIs never do), and the host script does not call it,
  on purpose. A heal is a disk write: on `status` it would run outside the consent gate, and on
  a mutating verb it would make a sidecar appear under a `""` fence, refusing the very verb that
  caused it. So today a renamed file starts a fresh sidecar and the old one stays behind as an
  orphan; the comments log keeps the record either way (decision 27), and there is no rename UI.
  The follow-up option: heal on a mutating verb only, behind the consent, and let the
  fence-and-retry shape absorb the appearance (the verb refuses `store-moved` once, the client
  re-issues `status` and retries by id while the change reads as it did).
- **Author chips on a file a remote kernel owns.** `GET /sessions` lists only the local kernel's
  sessions and no `/remote/<host>/sessions` relay exists, so on such a file the panel cannot map a
  sidecar `authorId` to a session's name and color: those chips fall back to the neutral chip with
  the sidecar's own author label. The Send label still names the session, since that comes from
  the viewer's identity rather than the map (the Slice 1 build, 2026-09-06). A relay route is the
  fix if the chips matter on a remote file.
- **Ended session.** Its todo is hidden from Waiting on you and `_send_or_park` revives dormant
  sessions, not ended ones (`kernel.py:24047-24062, 12227-12234`). Mitigation: the guide note
  above; Send to session surfaces the refusal; the comments are already on disk.
- **Prerequisites on the owning kernel** (node on the kernel's PATH for the host script, the
  agent-side tooling linked for the session to reply). Mitigation: `no-node` and the
  agent-tooling warning are explicit verdicts surfaced in the gear and the panel; the action never
  appears broken. Node on the kernel's PATH under every service unit is unverified and is the
  first thing Slice 1 checks.
- **Tracking inheritance.** The CLIs treat notes reachable through whole-line links and embeds as
  tracked (`store-io.mjs:100-197`). Mitigation: the host script uses `isTrackedFile`, the same
  function as the guard, so verdicts agree by construction, and reports `inherited` so the panel
  can say so (decision 11: turning it off refuses with the parent named).
- **track-changents defects the loop can reach** (the 2026-09-03 survey). A1: `track-reply` or
  `track-edit --thread` into a comment the live sidecar lacks revives it from the `.superseded`
  park and overwrites the sidecar with an empty change list, erasing pending changes including the
  one `track-edit` just recorded. A2: `track-edit` and `track-comment` replace a corrupt or newer
  sidecar with a fresh one. A7: `--thread` can bind a comment to a change id that coalescing
  dropped. A10: `track-edit --thread` failures are silent. The host script avoids A1 and A2 in its
  own path; A1 is fixed in both vendored CLIs in Slice 1, since the agent's replies are the loop's
  step 8, and the fix is offered back. Skill drift C3 (the skill says `track-edit` refuses stale
  text; it usually detaches the displaced changes instead) is corrected in the vendored skill and
  offered back.
- **A session rebases its own branch** (the user 2026-09-06: romp sessions are allowed to). A
  rebase can rewrite a commented file under the open panel and, when `.trackchanges/` is
  committed, rewrites the sidecar and the comments log like any other file. The design tolerates
  it without new mechanism: the poll sees the new mtimes, changes rebase or detach and comment
  anchors relocate or show detached, every fence refuses a write against the pre-rebase state,
  the log is append-only, and a sidecar left with conflict markers reads as corrupt and is
  refused, never replaced. The implementing session decides how the panel words a conflicted
  sidecar and whether the guide tells sessions to resolve `.trackchanges/` conflicts by taking the
  branch that holds the newer comments; nothing here changes the plan's shape.
- **A PDF rendering dependency** (Slice 4). Mitigation: lazy chunk, size cap, frame fallback, and
  a slice of its own so the rest of the feature never waits on it. Its trust boundary, PDF parsing
  on the dashboard's origin rather than in the browser's viewer, is stated under Security posture
  with the properties an upgrade or a later slice keeps.
- **Polling cost.** Two HEAD requests every 2.5 s per open panel, plus one per figure the file's
  open region comments name (Slice 3). Mitigation: only while the panel is open and the tab
  visible. The poll's state per file is one of absent, present with an
  mtime, or unknown with a status; it starts after the first `status` supplies the sidecar path,
  takes its baseline from every `fileCommentsResult` (the file's `fileMtimeNs`, the figures'
  `embeddedMtimes`) so the person's own writes never fire it, and
  treats a 404 as the value "absent" so absent-to-present is a transition like any other; a 413
  or 415 stops the poll on that file and shows the kernel's reason row.

## Tests

Synthetic fixtures only (the `notes-api` world, `TESTHOST`, placeholder ids).

- `tests/test_file_comments.py` (the `tests/test_savefile.py` hermetic pattern): path resolution,
  consent refusal before content checks, the vendored import path, `no-node` and the
  agent-tooling verdict, timeout and bad-stdout handling, `sid` routing, trace after reject and
  not after comment, the `log-edit` call after a save of a file with a sidecar, log, or tracked flag, not after a
  save of any other file, and not after a refused save, with `logged` in the `fileSaved` reply, the todo
  helper's branches (switch off, settled, ended, and the send arm's parked, sent, and refused
  outcomes, plus the handler's own unchanged behavior), message text for one and several comments
  and for `tracked` on and off, the `/defaults` verdict; `tests/test_injected_voice.py` gains the
  two new bodies.
- Host script conformance (node tests beside the script): a sidecar written by `track-comment`,
  replied to by the host script, read by `track-reply` keeps every field; the host script's
  sidecar path equals `storePathFor`; `v` stays 3 and the fingerprint matches; accept then
  `track-edit` succeeds; reject yields the engine's baseline for the subset and remaps survivors;
  rollback when the file write fails, including removal of a sidecar the verb created; fence
  refusals with `""` and with a stale value; nothing written on `v: 4` or unparseable JSON;
  `comment` with an ambiguous anchor refuses; a whole-file comment and a `target` comment
  round-trip through `store-io` unchanged; `set-tracked off` on an inherited file refuses; the
  comments log gains one entry per send, accept, reject, toggle, and edit, is never rewritten, and
  the unsent derivation from it matches the panel's; the vendored copy matches a present checkout
  (the drift test: pin plus patches, and a present checkout at or past the pin); the guard exits at
  once without `ROMP_SID` and passes a non-text file through. Slice 3, with figures generated as
  tiny PNGs at run time (`tools/file-comments-host-regions.test.mjs`, `-targets`, `-embeds`,
  `-plan-shape`, `-review-3`): the target's shape and unit-square check; the hash is the bytes', not
  the client's, and a `track-reply` into a region comment keeps it; containment of a relative and an
  absolute src in both directions; `figure-mismatch` before any hash; `too-large` on a write
  pinned with a sparse file, and a null hash with its reason on a reply; the decoded src; the
  src-less contract shape told from its passage, and its re-place; the figure fence:
  `figure-changed` on a standalone and on an embedded figure regenerated between the drag and
  the save, nothing written and no landmark created, a malformed `figureHash` refused before any disk
  read, `too-large` before `figure-changed`. The anchors follow-on
  (`tools/file-comments-host-anchors.test.mjs`, `-anchors-exact`, `-anchors-review-2` and
  `-anchors-review-3`): the anchor's context widens only as far as
  uniqueness needs and stops at the cap; a tie settled by the hint is placed, one without a hint
  refuses, and one whose hint sits on no tied copy (the text moved) refuses too, on a plain and on
  a tracked file; `anchorAt` is set at creation, kept by `track-reply` and `track-edit`, refreshed by the
  next host write after an edit above, never added to a comment without an anchor, and round-trips
  through `store-io`; a tied position follows its copy through a tracked insertion above, its
  reject, an accept and the person's own save, and keeps its position after an edit nobody recorded, after
  changes above that span a copy, and when the comment has no position; a comment whose one whole
  copy is the other copy of a passage whose surroundings were edited keeps its position after an
  edit nobody recorded and follows a tracked edit to the quote's other occurrence, and back through
  its reject; a save settles the changes its editor accepted; the refresh scans only for anchors
  that no longer sit at their position, charges every scan to one budget per write, past which the
  rest keep their position and stderr says so once, and 300 cap-width tied comments on a near-cap
  file, and 400 on a text of one repeated character, complete inside the kernel's
  deadline; the reply is measured with the refreshed positions, so a store within the slack of the
  cap refuses `too-large` instead of landing a reply the kernel discards. `tools/file-review-plan.test.mjs` pins what this plan
  states for the target's shape, the anchor rule, the verbs, the fence, the codes, the caps, the read bound and the
  poll against the host, kernel and panel sources, so a change to either side without the other
  fails a test. `tools/file-review-plan-acceptance.test.mjs` pins the Both acceptance criterion
  on the comment `addComment` writes: its wording, the host test whose title makes the same
  `anchorAt` exception, and on the fixture the anchor kept at 24 characters for a unique passage
  and widened for a tied one. `tools/file-review-plan-anchors.test.mjs` pins what the contract,
  the host paragraph, the commenting section and the follow-on note state after the follow-on's
  review: the refresh by where the whole anchor sits, its two sites and its budget, the refusal of
  an offset that sits on no tied copy once the text moved, and the `desc` sentence's widened form and
  its 120-character bound, against the host and model sources, the fixture, and the test modules and
  e2e cases the note names. `tools/file-review-plan-anchors-states.test.mjs` pins the painting
  paragraph's four states and the follow-on note's guessed-copy clause against the panel (`copyUnsure`,
  the dashed ring on a located mark, the tag and the card's words), the Raw criterion's two outcomes
  against the host's `locateExact` on the Raw fixture and the panel's follow and Save, and the webview
  modules that drive the painted states against the tree. `tools/file-review-plan-attribution.test.mjs` holds the margin-layout note to the
  record: the ask as the user made it, with its hedges, and the layout as the build's reading of
  it, awaiting the user's word (a review of the follow-on found the note had folded the build's
  design into the ask, 2026-09-07); `ui/webview/styles-fc-margin-attribution.test.ts` holds each sheet's
  margin comment to the same record (the second review found the sheets still said the user had asked
  for what was built, 2026-09-07).
- `tests/install-sh.bats` gains the tooling links, the guard registration with its matcher,
  idempotency, the basename presence check against an expanded-path entry, and the
  replace-an-existing-install case (Slice 1).
- `ui/webview/file-comments.test.ts`: source pins (registry entry, both ops carry `sid`, one
  `delegate()` root, string mtime comparison, no client-computed sidecar path, keyed expand
  state), pure tests for the card model, the Raw and Rendered mapping walks over the fixtures
  named in the acceptance criteria, and the message builder against the kernel's text.
- The inline-display follow-on (2026-09-07), in webview tests beside the Slice 2 suites:
  `anchor-map.test.ts` gains the Rendered change marks and the deletion points' placement (before
  the word the offset is on, against a word the deletion followed, a paragraph's end, the file's
  end, a list item, a blockquote, the capped label) and the blocks the map refuses (a code fence,
  a table, an HTML block, a blank line between blocks, a nested code block's inside);
  `anchor-map-rendered-points.test.ts` pins a table nested in a list item as a hole with the
  table's own extent, the block that begins at an offset holding the point where one block ends
  as the next begins, and the `white-space: pre-wrap` a label of spaces or tabs alone carries;
  `anchor-map-block-edges.test.ts` pins the blank line a token's raw swallows (under an ATX or a
  setext heading, an hr, a blockquote) as unpainted like the one under a paragraph, the end of a
  file whose last block is a heading, a deletion at the first character of a nested code fence or
  table sitting after the item text before the hole, and the change-marks section's statement
  that Rendered leaves only an unplaceable change to its card;
  `anchor-map-boundary-points.test.ts` pins the boundary rule over marked's output in Raw and
  Rendered under both paint orders: a deletion right after or right before an insertion sits
  outside the insertion's mark, at a row's end too, while a deletion inside the insertion still
  splits the mark; a deletion at a comment highlight's edge sits outside the highlight, a
  substitution whose tint begins the highlight has its point before it and one whose tint is inside
  keeps its point inside, before the tint; a deletion at the edge of a change mark and a highlight
  over the same word sits outside both; two points at one offset keep their paint order; and a
  substitution inside a code fence or a table cell gets its point before its fallback-placed tint
  and is reported painted while a deletion at the same offset is card-only;
  `anchor-map-whitespace-point-browser.test.ts` and `file-comments-rendered-point-browser.test.ts`
  measure the points under the real sheets in headless Chromium and Firefox (skipped where
  playwright or an engine is missing): a removed space or tab has width and takes the pointer, a
  short label adds no line, a long one wraps with the prose, the selection never carries the
  struck text, and unpaint restores the markup; `file-comments-changes-review.test.ts`'s Rendered
  half now expects the struck point and a plain card; `file-comments-inline-toggle.test.ts`
  drives Show changes inline as a panel: the ON default with nothing written until a flip, the
  deletion and substitution points and their cards, off with no status ask and the comment
  highlights kept, the store's `changesInline` read on the next open and a corrupt store as the
  default, the settings-signal and storage-event repaint, and the source pins (the delegate
  action, the header's order, the key and default, the listener's install);
  `file-comments-inline-review.test.ts`: a change mark inside the author's link opens its card
  and opens no tab, by click and by keyboard and under the chat pane's capture-phase link handler,
  the toggle withheld while the editor holds the body, and the generic "not shown" title on a
  deletion inside a code fence; `file-comments-reveal-title.test.ts`: Reveal's title with the
  marks off, in both views, with and without a line number; `file-comments-reveal-landing.test.ts`:
  the cue a Reveal paints on the Raw row it centred when the view shows no mark of ours there (the
  marks off; a batch the Raw painter refused), one row at a time and none beside a mark, its
  lifetime by event (a paint pass, the next Reveal, the panel closing), and a file the viewer
  shows only Raw.
  `tests/test_file_review_plan_rendered_deletions.py` holds this plan's Rendered-deletion
  passages (the surface paragraph, the Slice 2 line, the Risks bullet, the not-in-v1 list) to the
  painter's source; `tests/test_file_review_plan_inline_display.py` holds the follow-on note's
  white-space clause to `renderedPointStyles` and this bullet's file names to the tree; and
  `tests/test_file_review_plan_boundary_points.py` holds the note's boundary clause to
  `insertBeforeNode` and `insertAfterText` and this bullet's account of the boundary suite to the
  suite's tests.
- `ui/webview/user-todo-links.test.ts` rewritten to pin `path-links.ts` and both callers
  (Slice 0); `editor-lazy.test.ts` extended for the typed `track` option (Slice 5).
- `ui/webview/card-layout.test.ts`, `file-comments-margin.test.ts` and
  `file-comments-margin-browser.test.ts` (the margin-layout follow-on, 2026-09-07): the push-down rule,
  the ties, the gap, the loose group and an expanded card pushing the next; the track in two columns, the
  loose group, the list fallback in the fold and in edit mode, the scroll lock and the re-layout on
  expand, driven over a measuring stand-in; and in Chromium and Firefox the placed tops against the marks,
  the collision, the lock both ways to the far end (a comment on the last paragraph, both ranges within
  2px, the last card level with its mark from either scroller and from its reference link), the centering
  and the fold, under the sheets' own rules. From the follow-on's first review (2026-09-07):
  `file-comments-margin-review.test.ts` drives the panel over a stand-in that models what the first
  stand-in did not (the browser's focus-fixup rule, scroll positions clamped to each scroller's range, a
  footer under the track, a body whose content reflows without its box changing, escaped attribute
  selectors, and media bodies) and pins the keyboard surviving the rows' move and the reorder, the one
  range (the footer's height in the body's padding, the overhang growing it, the padding gone on close and
  back on reopen), the non-scrolling body's track going on alone and coming back level, the footer rows in
  the list's order, the placement order, a clamped write raising no echo, the content observer and the
  observer taking the list layout's cards when the margin comes on, the escaped id, and a region card on
  an image and on a PDF page; `file-comments-margin-review-browser.test.ts` runs the focus fixup, the
  `<details>` reflow, the Tab order and the footer rows in Chromium and Firefox;
  `feed-css-margin-footers.test.ts` and `styles-fc-margin-footer.test.ts` hold each sheet's footer block
  (the floor, the yield rule, the sticky Log toggle) and, in both engines, the Send confirm with its
  preview and the Log with its rows scrolling within their sections, Send, Cancel and every row in reach
  and the track keeping its floor; `feed-css-margin-leader.test.ts` holds the pushed card's leader rule in
  feed.css to the attribute and the variable the pass writes and styles.css to the same rule, and in both
  engines reads the leader's box off a pushed card (dashed, as tall as the push, its top at the mark's
  height) and finds none on an unpushed one; `tests/test_guide_files_margin_layout.py` holds the guide's
  Files sentence (level with the passage, scrolling with the text, the narrow column listing the cards) to
  the panel source and to both sheets; and `tools/file-review-plan-margin-review.test.mjs` holds the
  note's Built account to the panel and the sheets, and every module the note and this bullet name to the
  tree and to the pin credited to it (the round's commit message said the section named them, and it named
  none; found in review, 2026-09-07). From the follow-on's second review (2026-09-07):
  `styles-fc-margin-fit.test.ts` holds styles.css's margin sections to the two tiers (every section but
  the track shrinking and scrolling inside itself; the composer, and the head, Send and the Log while they
  hold more than their controls, giving first at a shrink factor a million times the others' down to a
  floor of `min(15%, 2.4em)`; the track's floor and the panel's clip kept) and, in Chromium and Firefox at
  the review's panel heights, measures nothing past the aside's edge, Send and the Log toggle in reach,
  the collapsed sections uncut, and a focus or a real Tab onto Send or the Log leaving the aside
  unscrolled and every card on its mark; `file-comments-margin-fixes.test.ts` drives the panel over the
  first review's stand-in with room for an open card and pins the opened card shown whole (the least
  scroll that shows its end, with no header term, so its head stays in the track's box, from the head
  click and from the reference link), a card taller than the track clipped at its head by the excess
  alone, a pass without a render un-pushing a card, a whole-file comment saved while scrolled moving
  nothing, the line at the foot saying above and its click bringing the card into the track's box by one
  write onto both scrollers, the composer closing after (decision 43; before it, the save's own scroll), a
  reply's save scrolling nothing with the card the focus and its line's click centering the card, the saved
  comment read off the reply's store (one new comment; among several, the one whose body is the note; none
  identifiable, no line), and at source the offset-free term and the save's focus and line raised before the
  composer's close, with no scroll; `file-comments-margin-fixes-browser.test.ts` runs the
  opening and the save in Chromium and Firefox over a rendered body;
  `styles-fc-margin-attribution.test.ts` holds each sheet's margin comment to the record
  `tools/file-review-plan-attribution.test.mjs` holds the note to (the layout as the build's reading, the
  ask with its hedges, nothing level-with attributed to the user); and
  `tools/file-review-plan-margin-review-2.test.mjs` holds the account's second-review statements to the
  panel, the sheets and these modules (the second round's commit, like the first's, added modules this
  section did not name; found in review, 2026-09-07). From the follow-on's third review (2026-09-07):
  `feed-css-margin-fit.test.ts` holds feed.css's margin sections to the two tiers and to styles.css's
  rules (the second review's change reached styles.css alone, and the byte-equal pins said so while
  nothing measured the feed page's fit), and in Chromium and Firefox under feed.css alone measures the
  fit at the review's panel heights; `file-comments-margin-image-pad.test.ts` drives the panel over the
  first review's stand-in with a picture world (the box's min-height and the centering modelled) and
  pins the footer's padding taken back in the pass that wrote it where the body gained no range, kept
  over a picture nearly the box's height, a short Raw file's taken back and a scrolling file's kept, and
  at source the write-then-measure; `file-comments-margin-image-browser.test.ts` measures the same over
  the viewer's image body in Chromium and Firefox (the picture where the box centered it before and
  after the panel's open, its card level with the rectangle, the near-full picture's padding kept);
  `file-comments-margin-attribution.test.ts` holds the panel's margin-layout section comment to the
  record the plan's and the sheets' pins hold (the first two rounds' corrections reached the plan and
  the sheets, not the panel source); and `tools/file-review-plan-margin-review-3.test.mjs` holds the
  account's third-review statements to the panel, the sheets and these modules (the third round's
  commit, like the two before it, added modules this section did not name; found in the review's
  consolidation, 2026-09-07). From the review's consolidation (2026-09-07):
  `feed-css-margin-footer-rule.test.ts` holds both sheets to the footer's rule on the Send section's top
  edge (after the shared section rule it overrides, the Send box's own dropped when it is first, the
  first review's rule on the foot gone), and in Chromium and Firefox mounts the panel under feed.css
  alone in three worlds — comments alone, a resolved comment with its fold first, a pending change with
  its foot first — and reads one hairline at the section's top level with the track's bottom, none on
  the first row, the Send box's own only behind a row, and nothing past the aside's edge.
- The focus follow-on (2026-09-08): `card-layout.test.ts` gains the focus rule (the focused card at its
  mark, the cards above moved up by the least that clears it, the cards below as before, the loose group
  joining the chain, and the old result with no focus, a loose focus or an unknown one);
  `file-comments-focus.test.ts` drives the panel over the review stand-in (the focus set by a highlight
  click, a change mark, a head click, a reference link and Show more, cleared when the card leaves the
  status and on the fold; the fold of a tall part in the margin and not in the list; Show more and Show
  less across a re-render); `file-comments-focus-browser.test.ts` measures the defect's scene in Chromium
  and Firefox (the comment's card level with its highlight after the click, the tall change card above
  moved up and folded with Show more, the narrow fold clipping nothing); `tests/test_guide_files_focus.py`
  holds the guide's sentence to the panel and the sheets; `tools/file-review-plan-focus.test.mjs` holds the
  follow-on's paragraph to the code and the modules it names. From the follow-on's review (2026-09-08):
  `card-layout-reach.test.ts` (no card past the track's start: the cards the chain cannot fit above the focus
  laid below it, the loose group's end going below in the list's order, a grid of fixtures with every card at
  or below the start); `file-comments-focus-review.test.ts` (the stand-in with a focus() that lands only on a
  rendered element: a focus written in the list layout anchoring nothing when the columns come back, the
  keyboard held on Show more and Show less across a press and a re-render, a folded run of turns at its end);
  `tests/test_guide_files_focus_scope.py` (the guide's sentence scoped to the panel beside the file);
  `tools/file-review-plan-focus-review.test.mjs` holds the margin note's rule, qualified by the focus, the Docs
  section's record of the guide's sentence and the Open question's loose group to the layout, the panel, the
  sheets and the guide. From the verification review (2026-09-09): `card-layout-spill.test.ts` (the re-lay of the
  cards above the focus without the cards laid below it: the card between a spilled tall card and the focus at its
  own mark, the loose group's spill giving the first paragraph's card the start, a grid where every card under its
  mark sits a gap under the card placed above it); `file-comments-focus-verify.test.ts` (the stand-in: a reply's save
  making an open card that was not the focus the focus, level and centered; a comment a change answered folding on
  its own card while the change card folds its own text alone and hosts nothing, on a long change and on a short one
  whose card offers no toggle (the about follow-on's rewrite, 2026-09-10, of the hosted fold the module pinned until
  then); the fold's choice surviving a status-driven re-render); `tools/file-review-plan-focus-centering.test.mjs`
  holds the paragraph's
  account of the centering fallback — its trigger the card's end past the track's box with the mark centered, an open
  card that fits the track included — to `centerOn`'s condition and the panel fixtures' geometry;
  `tools/file-review-plan-focus-verify.test.mjs` holds the paragraph's re-lay, save and fold statements (the hosted
  fold as history) to the
  layout, the panel and these modules, and every focus module in the tree to the paragraph and this bullet (the
  round's commit added modules this section did not name, as the margin follow-on's three review rounds' had; found
  in the round's review, 2026-09-09).
  From its second round: `file-comments-focus-verify-2.test.ts` (the stand-in: a gesture on a loose card below the
  focus moving nothing, the keyboard's memory held across the renders that cannot land it, the focus cleared with the
  panel's close, driven). From the merge audit (2026-09-09): `file-comments-focus-audit.test.ts` (the stand-in: Reveal
  writing the focus before the switch to Raw, the pass the switch runs laying the revealed card level; the fold to the
  list layout with a reply's box standing in a card leaving no inline height on the list and no top or leader on the
  kept card); `file-view-focus-seat-browser.test.ts` (the real viewer in Chromium, the Files pane at 1000x600: a focused
  card level with its mark and the track locked to the body across Raw and Rendered, one A+, the poll's reload and a
  reload under a held press, then the Reveal step, a deletion's card and a loose comment's laid level with their Raw
  marks in the track's box); `file-comments-focus-browser.test.ts` gains the fold with a reply's box standing in a card
  (the list's box its children's span, the aside's scroll range its content, in Chromium and Firefox). From the review
  of the merge audit's fixes (2026-09-09): `file-comments-reveal-arms-focus.test.ts` (the stand-in with a seam that does
  what the viewer's does: the pass `revealInRaw` runs itself where the switch painted nothing, the comment's branch of
  Reveal writing the focus before the switch and scrolling after it, a revealed card taller than the room under the
  body's center settled whole in the track's box past the row's centering, and Show changes inline off leaving the row's
  centering and cueing the row); `tools/file-review-plan-focus-audit.test.mjs` holds the paragraph's Reveal statements —
  the focus before the switch, the pass after it where the switch ran none, the settling — to the panel and the module,
  and every module whose header cites the paragraph to the paragraph and this bullet (the scan above reads the names,
  and the round's module, named for Reveal, passed it unnamed; found in the round's review, 2026-09-09). From its second
  round: `file-comments-reveal-one-pass.test.ts` (the stand-in with the passes counted: one pass per Reveal — the
  switch's own with Show changes inline off, from Raw and from Rendered, on a change card and on the deletion's; the
  pass `revealInRaw` runs itself on a file with no Rendered view; the switch's own on the comment's branch, level with
  its Raw highlight).
- The arrivals follow-on (2026-09-09): `file-comments-model-arrivals.test.ts` (a status's entries,
  the arrivals against a seen set, the line's words, the accept option's);
  `file-comments-arrivals.test.ts` drives the panel over the review stand-in (the line and the dots
  on a status landing, none for the person's own writes or the first status; seen by a wheel, a key,
  a press and a touch move, in the track's box only, never by time; the line's click and its own
  press; the accept option's words; the set across a repaint, a status and a close and reopen; the
  save moving nothing whatever came between Save and the reply, the saved card the focus, the line
  at the foot for a card below or above the box, its words following the card between renders, its
  click, its end at a gesture, under a held press at the release, and when the card comes into view,
  and no line for a card in view or for one the reply's store cannot name);
  `file-comments-arrivals-browser.test.ts` measures both in Chromium and Firefox (the line in the
  accent with its dot, the dots on the cards' heads and the marks, a real wheel marking the arrival
  in the box seen; a whole-file comment's save moving nothing, the line at the foot in the
  acknowledgment's green, a real wheel ending it, and its click bringing the text to the card);
  `tests/test_guide_files_arrivals.py` holds the guide's two sentences to the panel;
  `tests/test_guide_files_save_line.py` derives the save sentences' gesture words from the listeners;
  `tools/file-review-plan-arrivals.test.mjs` holds the follow-on's paragraph to the code and the
  modules it names; `tools/file-review-plan-send-note-close.test.mjs` holds decision 40's sentences on
  the viewer's close guard (the composer's comment and the Send box's note each asked about) to the panel's
  close asks and the viewer's close and replace-open paths. `tools/file-review-plan-arrivals-review.test.mjs`
  holds the review's three plan fixes (the request block's `note?` and the op prose to the kernel and
  the panel, the user ungendered, the Docs sentence's gestures to the guide).
- The seen follow-on (2026-09-09): `file-comments-model-seen.test.ts` (the pending changes split against
  the seen set; the accept option's words with seen and unseen counts and with nothing seen, and no resolve
  clause, the option taking two counts since decision 42);
  `file-comments-send-seen.test.ts` drives the panel over the review stand-in (two seen and one unseen:
  the option's words, the accept by id for the two, the message's count from the reply, the third still
  pending; all unseen: no accept call, the box unchecked and disabled; the person's own uncheck kept; a
  gesture while the confirm is up moving a change to the seen side in place and on the re-render);
  `file-comments-send-seen-browser.test.ts` measures the two-seen-one-unseen scene in Chromium and
  Firefox; `tests/test_guide_files_seen.py` holds the guide's sentence to the panel;
  `tools/file-review-plan-seen.test.mjs` holds the follow-on's paragraph and decisions 41 and 42 to the
  code, the message builders and the modules they name; `tools/file-review-plan-seen-review.test.mjs`
  holds the review's plan fixes (the arrivals paragraph's retired option words and save scroll as history,
  the acknowledgment line named as CONTEXT.md names it, the contract paragraph's self-check to the host's
  call sites, the margin-fixes and model-seen accounts to their modules) to the code;
  `tools/file-review-plan-seen-review-2.test.mjs` holds the second round's (the send's split over the confirm's
  set and the press's mark for the next confirm, the seen rule as the card alone, the unseen count against the
  arrivals line's, the save's retired scroll as history wherever the plan names it) to the panel and the model.
  The review rounds' own modules: `file-comments-seen-fixes.test.ts` drives the panel over the stand-in (the send
  accepting what the confirm showed and the press's mark for the next confirm; the count row following a gesture; a
  wheel over the saved line ending it, a press or a touch move on it not; the list layout re-reading the line's side at
  the aside's scroll, at a render and after the composer's close; the line under the header in the list layout and in
  the Send section in the margin layout; the panel's close ending the line; doSend's contract naming no accept-all);
  `file-comments-seen-review2.test.ts` drives the second round's (the confirm's Send activated from the keyboard as the
  send's own press; a key or a touch move ending the saved line; a Tab or a modifier alone no gesture, so the keyboard
  reaches the line, whose activation leaves the keyboard on the card it showed; the margin layout's line stuck to the
  Send section's bottom edge with the confirm up; the list layout's save leaving the acknowledgment in place; the
  track-and-accept send standing down on a change grown between the press and set-tracked's reply), and
  `file-comments-seen-review2-browser.test.ts` measures the stuck line and the keyboard's way to it in Chromium and
  Firefox; `file-comments-seen-review3.test.ts` drives the third round's over the same stand-in, a reply's box measured
  inside its card (the re-read at the end of the margin pass ending the line when the composer's close lays the card whole
  in view; the acknowledgment the line displaced back at the foot at that re-read, at a gesture and at the panel's close,
  and gone for good when Send to session is pressed with the line standing; a seen pending change grown under its id
  unseen again, an arrival with its dot, counted among the unseen, left pending by the send and seen anew at the next
  gesture that finds its card), `file-comments-seen-review3-browser.test.ts` measures the reply-box scene and the
  returning acknowledgment in Chromium and Firefox, and `feed-css-saved-line-head-dress.test.ts` holds the list layout's
  line under the header to the arrivals row's dress in both sheets and measures the two rows in both engines;
  `tests/test_guide_files_seen_definition.py` holds the guide's definition of a seen change (the first status's
  entries, a later change whose card was in view at a gesture, and a seen change the session edited again unseen until
  the next look) to the panel;
  `tests/test_guide_files_saved_line_layout.py` holds the guide's list-layout sentence to the panel's placement by
  layout, the sheets and the panel's tests of both placements; `tools/file-comments-host-untouched.test.mjs` drives the
  host's self-check end to end (a real stage, a comment changed in every way, the `anchorAt` carve-out, a check with
  nothing staged throwing, the verbs); `tools/file-comments-host-review-seen.test.mjs` holds the host's account of
  `suggestionId` to its code (every write of `resolved` the person's own `resolve` verb); and
  `tools/file-review-plan-seen-review-3.test.mjs` holds the third round's plan fixes (the saved line's place stated by
  layout in the arrivals paragraph, decision 43 and the Docs sentence; the keys that are no gesture named against
  `NAV_KEYS`; the acknowledgment never a note, across a wrap either; this list against the tree) to the panel, the guide
  and the tree. From the about follow-on's review (2026-09-10), `tools/file-review-plan-about-records.test.mjs` holds
  this paragraph's superseded sentences, the Show more row's order and the focus module's fold, to the panel and the
  module as history.
- The todo-file follow-on (2026-09-07): `waiting-file-chip.test.ts` boots `waiting.ts` under a
  DOM stand-in and drives the chip (rendered from the frame's `file`, its posted `viewFile`
  payload, the Reply modal's chip, no chip without the field, the detail link beside it);
  `file-comments-todo-choices.test.ts` drives the confirm (the checkbox from the status's `todos`
  with no opened-from todo, the radio group with several, the chosen id in the `fileCommentsSend`
  request, the todo gone after a send when the next status omits it, the stamp latch, the one-line
  label) and runs `todoChoices`; `tests/test_guide_todo_file_chip.py` holds the guide's Waiting on
  you and Files sections to the pane and the panel; `tools/file-review-plan.test.mjs` holds the
  follow-on's note and its Getting into it bullet to the model, the panel and the pane;
  `tests/test_file_review_plan_prompt_sentence.py` holds the From the session's side bullet,
  decision 35 and `claude/romp-session-prompt.md` to one another on the `file` argument (the
  review, 2026-09-07: the bullet still put the path in the detail after the prompt moved it).
- `ui/webview/pdf-lazy.test.ts` (Slice 4), on `editor-lazy.test.ts`'s model and in a file of its
  own, so a Node under pdf.js's floor fails the PDF tests by name and leaves the editor pins
  standing: the PDF chunk staying lazy (no main-bundle source imports pdfjs-dist or the chunk; the
  contract is the window global), the chunk and its worker as esbuild entries, `file-view.ts`
  loading the PDF chunk with the editor chunk's own find literal, the byte cap refused by name,
  the page shells and the observer-driven draws, and the license named beside romp's own;
  `pdf-lazy-render.test.ts` executes the draws over pdf.js's legacy build.
- `ui/webview/file-review-docs.test.ts`: this plan's own record of its tests and docs, held to
  the tree the way the posture test holds the Security posture section to the code: every test
  file the Tests section names exists; the file the section credits with the PDF chunk staying
  lazy holds that test; and each of the Docs section's two Slice 4 items (`SECURITY.md`'s bullet,
  the `pdf-chunk.ts` header) is in its file unless the section says it is not yet landed, and
  absent while it does, so whichever side moves first, the test names the other.
- `ui/webview/file-review-posture.test.ts` (Slice 4): the Security posture section's PDF
  statements held against the code, so the section cannot drift from what ships: the section
  names the boundary; `getDocument` takes `data` only and the chunk fetches nothing; the chunk
  imports pdf.js's core alone, never `pdfjs-dist/web`, and enables no layer, form, XFA, or
  scripting option; the installed build has no `eval`, `new Function`, or `isEvalSupported`, and
  its major is the one the section names; the caps are the section's 25 MB and 5,000 pages; the
  fallback is the frame; the worker asset is served behind `_authorize`.

- The filter follow-on (2026-09-07): `ui/webview/file-comments-filter.test.ts` drives the panel through
  the three states (the cards each shows, the marks each paints, the inline toggle on top), the default
  and the kept choice, a pick elsewhere, the arrow keys, Send unchanged, the kind cue, and the counts
  against the label's, and pins the delegate action, the header's order, the paint guards, the store's
  key and default and the sheets' rules at source; `ui/webview/file-comments-filter-review.test.ts`
  drives the review's six fixes over the same stand-in (the bound comment's reply under Comments in
  three paths, the tag and cue titles for a detached change, the editor-up titles, the line for a
  comment saved under Changes, the detached clause on the Changes option, and the head rows above the
  filter's) and pins their source; `ui/webview/file-comments-filter-fixes.test.ts` drives the second
  round's cases the same way (the track slot's loader and refusal with and without a filter row, the
  Changes empty state and the "Nothing decided" row under it, a region comment's saved line naming the
  rectangle, the line standing when a change comes to answer the comment and its end at the count's click (the
  about follow-on, 2026-09-10; until it the comment rode the change card and the line ended there), and the inline
  toggle's title under each filter) and pins the anchor and the title at source;
  `ui/webview/file-comments-filter-saved-line.test.ts` drives the third round's cases the same way (a
  status answering a save with several fresh comments, a session's among them, and the saved row's shape:
  `.fc-note` on the words' span, the ✕ a `.fileview-btn` under the unsized row) and pins the row at
  source; `ui/webview/file-comments-saved-line-sizes.test.ts` resolves the saved row's ✕ and words through
  both sheets' whole cascade, holding them to `.fileview-btn`'s and `.fc-note`'s sizes;
  `ui/webview/feed-css-kind-cue.test.ts`
  holds the sheets' kind-cue comment to the note's terms and to the declarations it describes, byte-equal

  across the two sheets, and `ui/webview/file-comments-filter-wording.test.ts` holds the four driven
  suites' and the two size probes' titles, assertion messages and comments to the same terms (the rule by
  its selector, the token by name, the focus move by where the focus goes, and none of the figures the
  plan's review replaced); `tools/file-review-plan.test.mjs` and

  `tests/test_guide_files_filter.py` hold the follow-on note above and the guide's Files paragraph to
  the source, `tools/file-review-plan-kind-cue.test.mjs` holds the note's kind-cue and focus
  sentences to the sheets and the panel, `tools/file-review-plan-filter-review.test.mjs` holds the
  note's review sentences and the UX paragraph's counts to the panel, the model and the guide, and
  `tools/file-review-plan-filter-fixes.test.mjs` holds the note's second-round sentences to the panel
  and this inventory to the tree: every suite named `file-comments-filter…` under `ui/webview` is named
  here and in the note.
- The marks' drag rule (2026-09-09, decision 44): `ui/webview/file-comments-markclick.test.ts` drives the
  `fcchange` and `fcopen` handlers over the behavior suite's stand-in with the live selection faked per case
  (inside the mark, elsewhere in the body with none of it in the mark, collapsed, none, in the aside, one end
  out; the pointer's click with `detail` 1 and the keyboard's activation through the row's keydown with 0, as
  browsers dispatch them);
  `ui/webview/file-comments-markclick-browser.test.ts` drags a real mouse inside an insertion's mark over the
  real viewer and panel in Chromium and Firefox, Rendered and Raw, the mark off the body's centre so the old
  behaviour scrolled: no card opens, the body does not scroll, the float stands, the composer opens on the
  selection, Save posts a passage comment the reply paints as its own card and highlight, a plain click on the
  mark still opens its card and scrolls, and the keyboard's activation of the focused mark opens it with the
  selection standing; its second test per engine selects words in another paragraph and clicks a deletion's
  struck label, and in Rendered an insertion's mark and a comment highlight inside an author's link, marks whose
  press collapses no selection: each opens its card and scrolls as with no selection (in Raw the link's label
  is plain text, whose press collapses the selection, the control). `ui/webview/file-comments-markclick-controls.test.ts`
  drives the guard as read against the clicked mark over the stand-in: a selection standing elsewhere in the body, or
  spanning the mark from outside, leaves the click a click for a change mark, a deletion's point and a comment
  highlight; the drag's own click still opens nothing and leaves no press pulse; a drag's end reported at the mark's
  edge is the mark's and one past it is not; and with the panel closed a drag inside a mark opens no panel and no
  card while a plain click opens both. `ui/webview/file-comments-markclick-controls-browser.test.ts` makes that state
  with a real mouse over the real viewer and panel in Chromium and Firefox: with words selected in another paragraph a
  click on a deletion's label, on a mark inside an author's link, on a region rectangle and on a framed figure opens
  its card; a drag inside an insertion's mark opens nothing and leaves no pulse; a drag ending at the mark's last
  character is the drag's; a tap on the deletion label with a selection standing opens the card (Chromium's touch);
  and with the panel closed the label and the frame open the panel and the card, the drag neither.
  `tools/file-review-plan-markclick.test.mjs` holds this bullet, the surface sentence and decision 44 to the panel,
  the sheets, the overlay and the four modules.
- The about follow-on (2026-09-10, decisions 45 and 46): `tools/file-comments-host-about.test.mjs` (the host: `changeIds`
  with and without an anchor, the id rule, the refusal naming the missing ids, the suggestionId caller bug, `decidedFor`
  over both fields, the field through track-reply and accept); `file-comments-model-about.test.ts` (refIds, commentRefs,
  the card's refs and reference, the count, describeComment's about clause and its edges, the sent text against the
  kernel's literal); `file-comments-about.test.ts` (the stand-in: every comment its own card, the tags and the ring, the
  count tag's click and key, Comment on this change on a substitution and on a deletion, the option unchecked, a selection
  inside an insertion, across two marks, reaching a deletion's point and over its label alone, the sources);
  `file-comments-about-browser.test.ts` (Chromium and Firefox, Rendered with the marks shown and hidden and Raw);
  `file-comments-resolve-answered.test.ts` (the stand-in: the header action's count and its absence, the confirm, the
  resolve requests, a refusal per comment, Reopen all and its end at a gesture) and `file-comments-resolve-answered-browser.test.ts`
  (Chromium and Firefox); `tests/test_guide_files_about.py` holds the guide's sentences to the panel;
  `tools/file-review-plan-about.test.mjs` holds the about follow-on's note and decisions 45 and 46 to the code and the
  modules they name; `tools/file-review-plan-about-records.test.mjs` holds the hosted-era sentences the follow-on
  superseded elsewhere in this document (the Show more row's order, the focus module's fold, the filter module's saved
  line) to the panel and the modules as history, decision 46 to the vocabulary, and the note's citation of the
  assessment to the tree (the report is outside it), and, since the review's consolidation (2026-09-10), the relation's
  names in the records, the panel, the ADR and the host to CONTEXT.md's About entry (each carries a tag for the other;
  never linked, cross-linked or thread), with the filter's option titles and the decision tag held to the guide's words.
  From the about follow-on's review (2026-09-10):
  `file-comments-about-fixes.test.ts` (the stand-in with the editor's seam: the span cut from the file as the editor
  loaded it, Comment on this change withheld in flux and in media mode and standing on a deletion, a refused selection
  crossing a deletion's mark, a BOM file's offsets, `deletionUnder`'s one mark, the open card's line naming the
  changes), `file-comments-resolve-answered-fixes.test.ts` (the confirm's end when nothing answered remains and at the
  panel's close, the editing consent asked once, the Reopen all row's dress and place, a wheel ending the offer under
  focus) and `tools/file-comments-host-about-scale.test.mjs` (the host's id walk in linear time: a hundred thousand ids
  refused `no-change` inside the kernel's deadline); `tools/file-review-plan-about-flux.test.mjs` holds the paragraph's
  account of Comment on this change withheld in flux and in media mode, and the Slice 2 build paragraph's clause, to the
  panel and the stand-in. From its second round (2026-09-10): `file-comments-about-review2.test.ts` (the stand-in with
  the layout switchable: the composer's about ids pruned as a status retires a change, a selection starting exactly at a deletion's point, the
  deletion marks a drag crosses, the kind cue's title by source, the ids-only line by layout),
  `file-comments-resolve-answered-review2.test.ts` (the Reopen all offer's place by layout and the keyboard after a run
  the confirm's Resolve began from the keyboard) and `file-comments-arrivals-about.test.ts` (a session's reply on a
  comment about a pending change shows on the comment's own card, never the change's).
- The Bash-side guard (2026-09-10, decision 47): `tools/romp-track-bash-guard.test.mjs` drives the hook's
  evaluate() over synthetic PreToolUse payloads against a scratch project (cp over a tracked file refused naming
  the file and track-edit, cat allowed, a heredoc redirection refused with its body never read as commands, sed -i
  in its spellings, an unrelated path and a tracked source copied out allowed, the dry run's compound command, the
  copy verbs with a directory destination and -t, every write redirection and none of the reads, tee, dd, sort -o,
  perl -i, python and node inline scripts and a script on stdin, cd and ~/ and an absolute path, the opaque forms
  allowed, a tracked image passing by name and a new file under a tracked folder refused, the refusal's voice) and
  the hook as a process (exit 0 at once without ROMP_SID with stdin held open; exit 2 with the reason on stderr
  with it, by its real path and through the `~/.claude/hooks/` symlink install.sh registers); from the review's
  first round (2026-09-10), `tools/romp-track-bash-guard-shapes.test.mjs` pins the
  shapes the round found misread, each in both directions where it has two, the write the hook missed and the
  ordinary command it refused for a file the command never touches: a cd inside `( ... )` ending at the `)`, and
  in an if, loop or case body leaving the cwd unknown once the body closes; a heredoc body kept by the command
  that opened it through a following `&&`, `|`, `;` or `&`, or piped into python or node; a shell fed its script
  by heredoc (`bash <<EOF`, `bash -s`, `sh -`) read like `sh -c`; `-c` in an option cluster (`bash -lc`,
  `sh -ec`); python and node options before a heredoc on stdin; a prefix with options (`sudo -u`, `env -u`,
  `timeout -s`, `exec -a`); pushd moving the cwd and popd leaving it unknown; `[[ a > b ]]` and `(( a > b ))`
  comparing while `[ a > b ]` redirects; a function body moving nothing after it; `Path(x).open('w')`, `open()`
  with keyword arguments and `fs.openSync` with a write flag; node `-p` and `--print`; the refusal's word (a
  change, never a suggestion); the NUL-byte rule; the full walk of a directory source, past 500 entries and into
  a subfolder behind them, skipped for a landing folder that does not exist under any project that tracks
  anything; `&&` inside `[[ ... ]]` and a quoted `[[`; a brace list; a wrapped `open(`; a here-string; a process
  substitution; a glob source and a glob that names no write; a symlink to a tracked file; one link closure per
  call over a directory copy and over five redirect targets, agreeing with store-io's `isTrackedFile` on every
  kind of path and pinning its three steps; and the hook process on a subshell cd, a chained heredoc and a
  heredoc-fed shell;
  `tests/install-sh.bats` the Bash-side guard's registration on its own `Bash` group, once, with the
  vendored guard's group beside it and a user's own Bash group kept; `tests/romp-uninstall.bats` its removal;
  `tools/file-review-plan-bash-guard.test.mjs` holds decision 47, the Vendoring paragraph and this bullet to the
  hook, the installer and the uninstaller; `tools/file-review-plan-dry-run-record.test.mjs` holds decision 47's
  record of the dry run to the form every other record of it takes, a dry run and its date, with no project
  named; `tools/file-review-plan-bash-guard-review.test.mjs` holds decision 47's cost sentence to the hook (the
  closure built after the veto and the explicit list, never with an empty list, once per call and shared by the
  command's targets) and the inventory to the tree: every `romp-track-bash-guard…` module under `tools/` is
  named in decision 47 and in this bullet, and every `file-review-plan-bash-guard…` module in this bullet, so a
  later round's module cannot land unrecorded, and the hook's row in `hooks/README.md` names every
  `romp-track-bash-guard…` module too. Sessions commit the folder (decision 48):
  `tests/test_session_prompt.py`
  pins the prompt's sentence; `tools/vendor-patches.test.mjs` (P7) pins patch 0007's two rules in the skill;
  `tests/test_guide_files_commit_folder.py` holds the prompt, the skill, the guide's Files sentence and decision 25
  to one another; `tests/test_guide_files_bash_guard.py` holds the guide's Track changes sentence on the refusal
  to the hook's grammar.

- The sidecar lock and the clocks (2026-09-11, decisions 49 and 50): `tools/file-comments-host-store-lock.test.mjs`
  (the host's `comment` and the real `track-reply` against a writer mid-write, the `busy` refusal and the CLIs' one
  line with nothing written, a dead writer's lock broken, and `withStoreLock` itself: the stamp, the release on
  return and on throw, the folder made for the lock and taken away, a non-lock at its name refused);
  `tools/file-comments-host-race.test.mjs` (a `track-edit` inside a reject's write through the
  `FILE_COMMENTS_TEST_PAUSE_MS` seam: both land; the seam is read in one place, inert when unset, never set by the
  kernel); `tools/file-comments-host-clocks.test.mjs` (a newer sidecar and a newer config landed right after the
  first read, the read-back after a comment, a prune answering null with a null clock, and the source: every
  reader clocks first and the reply stats nothing); `tools/vendor-patches.test.mjs` (P8: the three CLIs' refusal
  under a held lock, the release on a failure, no folder left by a refused first comment);
  `ui/webview/file-comments-changes-review2.test.ts` (Accept refused `busy`: one retry by id with the fresh fence,
  the row verbatim with Reload on a second; Accept all refused `busy`: re-read, nothing decided);
  `tools/file-review-plan-sidecar.test.mjs` (decisions 49 and 50, the host paragraph, the codes list, the
  Vendoring sentence, this bullet and the ADR held to the source and the tree);
  `tools/file-review-plan-lock-verbs.test.mjs` (the host paragraph's lock sentence held to the host's verb
  table: the eight verbs route through the lock, `status`, `log-edit` and `log-send` take none, the log is
  appended an entry at a time and never rewritten, and nothing vendored names it).
  From the slice's review (2026-09-11; the first round's commit added six modules and named one here, found in the
  second round): `tools/store-io-lock.test.mjs` (the break of a stale lock has one winner: real writers racing to
  one instant on a dead pid's lock, or on a stamp past the bound, never hold together and every one writes; a live
  breaker's claim, `<sidecar>.lock.break`, excludes every other breaker and a dead breaker's claim is removed; a
  holder broken while alive leaves the breaker's lock alone at release, so a third writer waits for the breaker; a
  stamp write that fails leaves no lock and no folder; two first writes on a fresh root leave no `.trackchanges/`
  behind, the folder handed over by the `made-dir` line and taken away by the last one out; a lock the process
  cannot read refused naming the lock and the OS error); `tools/file-comments-host-config-lock.test.mjs`
  (`set-tracked` against a held `config.json.lock`: the wait, then `config-moved` from the holder's write and the
  retry landing both entries, or the landing after a release with nothing written; `busy` past the wait naming the
  root's tracked list, nothing written and the lock left; a comment on the same file landing under the sidecar's
  own lock; two hosts toggling two files under one root in a loop, never both ok with an entry missing);
  `tools/file-comments-host-landmark-race.test.mjs` (two first writes on one loose file, in both orderings the
  race has and in a two-process loop: the second meets `store-moved` or `config-moved`, never `unreadable`, and
  the retry lands both; a directory at the landmark's name is built over, a link to nothing is not);
  `tools/file-comments-host-read-under-lock.test.mjs` (a comment sent while a `track-edit` has renamed its sidecar
  and not yet written the file waits and is placed in the text the edit left, a whole-file comment carrying the
  edited file's clock and fingerprint); `tools/track-comment-race.test.mjs` (six real `track-comment` processes on
  one file at one instant, the first round on a root with no `.trackchanges/` yet: every comment lands and the
  folder holds the sidecar alone; three comments and three replies to one earlier comment at once; the source:
  the save inside the lock); `tests/test_kernel_file_comments_host_env.py` (the kernel hands the host its environment
  minus `TRACKCHANGES_ROOT` and every `FILE_COMMENTS_*` variable, so a pause seam exported in the kernel's shell
  never reaches a reject or a save: against the function, a stub host and the real host);
  `ui/webview/file-comments-save-busy.test.ts` (the editor's Save through the panel refused `busy`: one status
  re-read and one retry with the fresh fence, the success applied as the status; no retry on a second `busy` or
  when the re-read shows other records, the refusal handed to the viewer with its code and the host's words);
  `ui/webview/file-comments-save-busy-viewer.test.ts` (the viewer's half at the real `openFileView`: a second `busy`
  holds the host's words in the bar with Reload file, Save re-armed and the buffer kept, and Reload asks before it
  re-opens the file); `ui/webview/file-comments.test.ts` gains the `MOVED` literal with `busy` and the save path's retry line;
  `ui/webview/file-view.test.ts` anchors the viewer's failed arm on its four-code closing line and asserts the
  anchor is found exactly once; `tools/file-comments-host-landed.test.mjs` reads the sidecar's lock as the first
  thing a save creates under `.trackchanges/`, so a folder that cannot be written to refuses `unreadable` on the
  lock; `tools/file-comments-host-store-lock.test.mjs` holds its header's 220 ms before-figure equal to decision
  49's; `tools/0002-file-comments-in-the-track-changents-sidecar-lock-names.test.mjs` (the second round's module
  for the ADR's lock bullet, `docs/adr/0002`, which the first round had left naming one file: the bullet's two
  names, `<name>.lock` and `<name>.lock.break`, and its one `made-dir` line held to the constants `store-io.mjs`
  defines, so a name or a line that one side has and the other lacks fails; and the lock run in a scratch root:
  a live claim beside a dead lock governs the waiter and a dead claim goes with the break, the write seeing the
  lock alone, and the maker of the folder writes the line into a real holder's lock, which that holder honors at
  its own release). `tools/file-review-plan-sidecar-records.test.mjs` holds this bullet's inventory to the tree both
  ways: every module it names is in the tree, and every test module under `tools/`, `ui/webview/` or `tests/` that
  cites decision 49 or 50 is named here, so a later round's module cannot land unrecorded; it also holds the panel
  section's Errors bullet (the codes that offer Reload) to the panel and the viewer, and the Security posture's two
  lock names and one line to `store-io.mjs`. That scan goes by citation, and the ADR's module cites the ADR and
  not the decision, so it landed in the commit that built the scan and was named nowhere in this plan (found in
  the review's third round, 2026-09-11): `tools/file-review-plan-sidecar-adr-modules.test.mjs` holds every module
  named for an ADR (under `tools/`, an ADR's number and slug and then what the module tests) to this bullet and
  to decision 49 by its name, whatever it cites, and holds this bullet and decision 49 to the plan's vocabulary:
  the `track-comment` race is run on a file and its replies land on a comment, and the two words `CONTEXT.md`
  sets aside under File comment (the forked side session's and the send's paragraph's) appear in neither record,
  where the second round had written both.

## Docs

`docs/guide.md`: "Reviewing a document" (`:29-45`) becomes a section on file comments and tracked
changes, states that quote chips remain for one-off notes, tells the user to track the folder a
session will write into, and to keep figures out of tracked folders until Slice 1's refusal is
in place; "Waiting on you" notes the linked path and the ended-session case (and, from the
todo-file follow-on, the file chip); "Files"
(`:126-138`) gains the panel, the poll, the consent gate the guide omits today, commenting in
either view and on images and PDFs, the comments log and the `.gitignore` opt-out, and where to
look when the action is missing (and, from the todo-file follow-on, that a Send answers the todo
that named the file however the file was opened); with the margin-layout follow-on (2026-09-07) it says that beside
the file each card sits level with the passage it is about and scrolls with the text, and that a
narrow column lists the cards (`tests/test_guide_files_margin_layout.py` holds the sentence to the
panel and both sheets); with the focus follow-on (2026-09-08), that the card you click sits level with its
passage whatever stands above it and that a long card folds to a few lines with Show more at its foot
(`tests/test_guide_files_focus.py` holds the sentence to the panel, the layout rule and the sheets).
With the arrivals follow-on (2026-09-09), that a line under the panel's header counts what the session added since you
last looked, with a dot on each until you scroll or click with it in view, and that a save leaves the text where it is,
a line at the panel's foot saying whether the new card is above or below until your next scroll, click, tap, or key,
its click bringing the card into view (`tests/test_guide_files_arrivals.py` holds both sentences to the panel), and that
in the list under a narrow column the line stands under the panel's header instead
(`tests/test_guide_files_saved_line_layout.py` holds that sentence to the panel's placement by layout, the sheets and the
panel's tests of both placements). With the seen follow-on (2026-09-09), that the Send's checkbox accepts only the pending
changes you have seen and says how many unseen ones stay pending, and that a change the session edits again after you
looked at it is unseen until you look again (`tests/test_guide_files_seen.py` and `tests/test_guide_files_seen_definition.py`
hold the sentence to the panel). With the about follow-on (2026-09-10), that Comment on this change opens the box over
the change's text with "about this change" checked so the message names the change, that a comment is never shown inside
a change's card and the comment and the change each carry a tag for the other, that a selection inside a change leaves
an ordinary comment with the same
box checked, that an older binding reads "answered by a change", and that nothing resolves a comment but you, singly or
with Resolve answered (`tests/test_guide_files_about.py` holds the sentences to the panel). With the Bash guard
follow-on (2026-09-10), that a session writing a tracked file any other
way, with its editing tools or a shell command, is refused and pointed at track-edit (`tests/test_guide_files_bash_guard.py`
holds the sentence to the hook), and that sessions are asked to include `.trackchanges/` when they commit their own work while
the person's commits stay theirs (`tests/test_guide_files_commit_folder.py` holds it to the prompt, the skill and decision
25); `docs/install.md` names the Bash-side guard beside the vendored one.
`docs/reference.md`, under install-time switches, notes the
User todos switch as a prerequisite for the todo path and the node requirement on the owning
kernel; `docs/install.md` names the tooling the installer links into `~/.claude/`. With Slice 4,
`SECURITY.md`'s output-sanitization bullet names the PDF renderer (pdf.js parsing on the
dashboard's origin, in a Worker, with pixels as its only sink, as Security posture states it),
and the `pdf-chunk.ts` header says the same in a sentence, so a session upgrading pdfjs-dist
reads the boundary where it edits. The slice's merge carried neither (its review, 2026-09-06);
both landed with the review's fixes.
`ui/webview/file-review-docs.test.ts` holds this paragraph to the two files: an item it calls not
yet landed must be absent from its file and every other present, so the paragraph and the files
move together.
`claude/romp-session-prompt.md` gains its one sentence. `CONTEXT.md` already carries the
vocabulary; `docs/adr/0002` records the storage decision. In track-changents (its author): the
offers back named under Vendoring, and a README "Hosts" row.

## Deliberately not in v1

Git operations on any project (romp's git calls on session repos are read-only queries; whether
`.trackchanges/` is committed is the project's call); ingesting comments typed on GitHub; a
filesystem watcher or kernel push for the Files pane; a viewer or editor extension API; rendering
HTML files (the viewer serves them as source by design); text-quote anchors inside PDFs (the CLIs
cannot read a PDF's text, so PDF comments are whole-file or region); region drawing by touch on
the phone; changes authored by the person (their edits are direct edits, decision 23); the
Obsidian host's embed trees, explorer badges, status bar, multi-pane sync, and vault rename
re-keying; a scheduler for overnight work; changes to the Obsidian and VS Code hosts; undo of
accept and reject before Slice 5; multi-file sends (one send per file, decision 28). Inline
deletions in the Rendered view were on this list until the inline-display follow-on (2026-09-07,
under Slice 2's build note) built them.

## Dependencies

On the owning kernel: node on the kernel's PATH; the agent-side tooling linked into `~/.claude/`
by romp's `install.sh` from the vendored copy (decision 15); for changes to appear, the file's
path or folder listed in `config.json` before the session writes it; the User todos switch on for
the todo path to exist; the file-editing consent given once. Nothing blocks on track-changents'
author: the A1 fix, the non-text refusal, and the skill edits land in the vendored copy as
patches in Slice 1 and are offered back; the `target` field and the comments log are romp-only. For Slice 4,
the PDF rendering dependency.

## Decisions (the user, 2026-09-05 and 2026-09-06)

The user reviewed the first full draft on GitHub, the revision through the viewer's own quote
flow, and then answered a structured design interview. Every ruling is recorded here so the
document stands on its own, each with the reasoning it was given.

1. **Slice order and cadence.** All six slices are built in one push; the order in Build slices
   is the default landing order, and the implementing session decides staffing, with a dedicated
   new session suggested. The fork dispatch stays parked until asked for.
2. **Write path.** The node host script on the owning kernel, over track-changents' `store-io`
   and engine unchanged. A second implementation of a cross-tool contract is where shared files
   get corrupted.
3. **Where the host script lives.** In this fork, importing the vendored copy. The user intends
   to offer the whole feature upstream to romp eventually, so everything it needs is built into
   this repo first and offered to track-changents later.
4. **Vendoring.** Now, without waiting for track-changents to be public: the MIT core pinned to a
   commit under `vendor/track-changents/` (see Vendoring).
5. **Consent scope.** Every mutating verb, sidecar-only included, behind the one file-editing
   consent, with the popup's copy amended so it stays true for comments.
6. **Human author label.** `you`, so one person is one author across hosts; no `authorId`.
7. **Trace policy.** A trace after `reject`, `reject-all`, and `save`; nothing after sidecar-only
   verbs, since the sent message is the notification for comments.
8. **Send defaults.** All confirm checkboxes checked by default, each visible before the send.
9. **Per-comment sends.** Batch only.
10. **The unsent state.** Not browser-local. The user asked whether a browser crash could lose the
    comments. It could not, since comments and changes live in the sidecar on disk, but the send
    watermark would have been lost. The comments log holds it on the owning kernel, so no state
    lives in the browser.
11. **Turning tracking off on an inherited file.** Refuse with the parent named.
12. **PDF rendering.** The lazily loaded pdf.js chunk, with the browser's frame as the fallback.
13. **The region field.** Built romp-only for now; documenting it for the other hosts is a later
    offer, not a dependency. (The Slice 3 build stores a fifth key, `src`, on a figure embedded in a
    markdown file, and has the host resolve and hash the file it names; the offer documents the
    shape as built; see the contract's `target` bullet and Security posture.)
14. **The Slice 5 doctrine question.** Yes: a typed, internal `track` option in the editor chunk,
    with the header updated.
15. **Ship the agent-side tooling with romp.** Yes (2026-09-06): the four CLIs, the guard hook,
    and the skill are vendored with the core and linked by romp's installer, so a machine that
    runs romp runs the whole loop with nothing else installed; fixes land in the vendored copy
    and are offered back.
16. **The log's format.** JSON lines in `.trackchanges/`, rendered by the panel's Log section; a
    markdown export may follow if reading it on GitHub matters.
17. **The object is a file comment** (2026-09-06), never a thread: a comment on a passage, a
    region, or a whole file, kept with the file. The name also covers comments that have nothing
    to do with a review.
18. **"Change" is the user-facing word** for a session's pending edit; "suggestion" is the storage
    format's word and stays out of the UI.
19. **The plan merges first.** The implementing session merges this plan to main with the header
    changed, then begins, likely in a new session it creates.
20. **Plain delegation** to the implementing session; no report-back tie to the authoring
    session.
21. **One user todo at the end**, for the end-to-end walk, rather than one per slice.
22. **No "report" object.** The feature is rich commenting and editing of files in romp with easy
    communication back to the session; the overnight report is one use. No folder convention is
    imposed; the user tracks what they want tracked.
23. **Direct edits stay direct.** The person's own edits land at once and trace to the session;
    the person chooses between editing the text and commenting instructions.
24. **The guard is scoped to romp sessions by environment**: registered machine-wide, it exits at
    once when `ROMP_SID` is absent.
25. **Committing is the project's call.** romp writes the sidecar and the comments log and does
    no git operation; a `.gitignore` line is the opt-out. (2026-09-10: sessions are asked by the
    skill and the session prompt to include the folder when they commit their work, the person's
    own commits staying theirs and romp still running no git command; decision 48.)
26. **Phone**: reading and commenting work there; region drawing waits.
27. **Renames** rely on the store layer's content-hash healing; no rename UI, and the log keeps
    the record. (The Slice 1 build found that healing runs only when a host calls it, and the host
    script does not; see the rename bullet under Risks for the actual behavior and the follow-up.)
28. **One send per file**, sending everything unsent in it; a todo naming several files is
    answered by the first send.
29. **Done** means the per-slice criteria pass and the user completes the motivating loop end to
    end with no GitHub and no Obsidian.
30. **Compatibility stays, and gets an ADR.** The storage format is track-changents' unchanged,
    plus the romp-only log; the reasoning is recorded in `docs/adr/0002`.
31. **Names**: "Comments" for the action and panel, "Track changes" for the toggle, "Send to
    session" for the button, no mode concept.
32. **The log is the comments log** (not "history", which reads as git history), file suffix
    `.comments-log.jsonl`, panel section "Log".
33. **Direct edits are logged** too, so the log holds everything that happened to the file
    through romp.
34. **Whole-file comments on every file**, not only images and PDFs.
35. **Sessions learn the pattern from romp's default session prompt** and from the skill: name
    the file's absolute path in the todo's detail; ask for another look the same way. (The todo-file
    follow-on, 2026-09-07: the path goes to `add_user_todo`'s `file` argument, and the detail may
    still describe it; the prompt's sentence says so. See Getting into it.)
36. **The three Send checkboxes** keep their generic wording: answer the todo; turn on tracking so
    the session's edits come back as changes; accept the N pending changes.

37. **A file with no repository or vault above it** (2026-09-06) gets `.trackchanges/` created
    beside it on the first comment or tracking toggle, and that folder is its project's root from
    then on; the loose-file case refuses nothing.
38. **One `.trackchanges/` per project, at its root** (2026-09-06), never one per directory: the
    nearest git repository, vault, or folder that already holds one is the project, and a loose
    file starts a project of its own. The tracked list, the comments of every file in the project,
    and the commit-or-ignore choice have one home; a file moved within the project keeps its
    comments; and the agent CLIs, the guard, and the other editors look in the same place.
39. **The gear row names the reason and the command; the one-click link step waits** (the Slice 1
    build, 2026-09-06). When the agent-side tooling is not linked on a machine, the File comments
    row says so, says that its sessions cannot reply until it is, and names the command to run
    (romp's `install.sh` on that machine); it does not offer to run it. Getting into it promised a
    button. Running the installer from the dashboard needs a kernel op that executes `install.sh`,
    and Security posture enumerates what the feature may write: the sidecar, the comments log,
    `config.json`, and the commented file. An installer run writes `~/.claude` and `settings.json`
    and is outside that list, so the button adds a server-side surface the posture does not name.
    It awaits the user's ruling; until then the row's sentence is the offer.
40. **The Send confirm's message preview gives way to a note box** (2026-09-09). The user's ruling: the grey preview
    text in the confirm is a system message tied to the send and not worth showing; a text box for anything they want
    to add takes its place. The box is optional and empty by default (three rows, growing to about eight, then
    scrolling; Enter adds a line, the composer's chord or the Send button sends); its text survives every re-render
    while the confirm is open and is cleared only by a successful send or by Cancel. The arrivals follow-on's review
    (2026-09-09) found one gap: the viewer's close guard (`ctx.guardClose`) asked about the composer's typed comment
    and not about the note, so a close of the viewer or a replace-open (a link followed inside the file, a Files-pane
    row) while the box held words dropped them with the panel, and neither a dialog nor the notice bar said so. The
    review's consolidation closed it with a second ask beside the composer's (`noteAsk`): words in the box, as the
    kernel reads them (`trimNote`), make a close ask naming what it would drop, put by the viewer the way it puts the
    editor's own, and a refused ask keeps the viewer, the panel and the words; Cancel and a send that went leave no
    ask, a send out or refused keeps it, and Escape typed in the box stops at the box and closes nothing.
    `tools/file-review-plan-send-note-close.test.mjs` holds these sentences to the panel's two close asks and the
    viewer's close paths; `file-comments-send-note.test.ts` drives the ask. The note travels as `note` in the
    fileCommentsSend request, trimmed, at most 4000 characters (refused before any request with a line naming the
    bound; the kernel refuses the same bound), and both builders place it as the first paragraph after the header
    line, unlabeled, before the comments, marker-neutralized like every other request-supplied string; a note with
    nothing else unsent still sends, as the header, the note and the closing ask, so Send opens the confirm with
    nothing unsent and the confirm's own Send waits for words. The comments log's send entry gains `note`, and the
    panel's Log shows it. The acknowledgment line after a send (Sent to <session> at <time>) is unchanged. A kernel change: the panel and the kernel land together,
    and the kernel restarts to go live.

41. **The Send's accept takes the changes you have seen, never an unseen one** (2026-09-09). The user's ruling on
    what the arrivals follow-on surfaced (a Send had accepted eleven changes they had not looked at): the box stays,
    and so does its default, but a send never accepts a change they have not seen. The option accepts the pending
    changes the person has seen — a change whose card was on screen at one of their gestures, or that the panel's
    first status held, the arrivals follow-on's rule (the card alone: a mark in the text on screen with its card
    out of the box marks nothing seen) — by id, through the same accept the card's button uses, and says how many
    unseen ones stay pending; with nothing seen the box is unchecked and disabled and says so. The send accepts the
    seen set as the confirm showed it: the Send press is a gesture and marks a card on screen seen, for the next
    confirm and not for this send. The message states the count the accept's reply lists. A seen change the session
    edits again under the same id is unseen again until the person looks at it (the review's third round, 2026-09-09).
    The seen follow-on under Slice 2 has the build.

42. **The edit-to-comment link leaves the loop, and a decision never resolves a comment** (2026-09-09). The message
    told the session to revise with `track-edit --thread <id>`, which binds the edit to the comment so its card shows
    the edit inside the comment; the user found the link too confusing and asked for it to go. Both message builders
    now say plain `track-edit` for edits and `track-reply <id>` for answering a comment in words, the vendored skill's
    copy says the same (patch 0006), and the host's accept and save leave a comment bound to a decided change as it
    was, open: resolving is the person's own act. Comments already bound stay as they are on disk and render as
    before. With nothing resolved by an accept, the confirm's "resolves M comments" clause and the acknowledgment
    line's "moved to Resolved" tail are retired.

43. **A save never moves the view; a line says where the card is** (2026-09-09). The user's ruling on the save's
    scroll, which the arrivals follow-on had stand down once they had moved on: no scroll after a save at all, even
    when the new card lands out of view, because a scroll is disruptive; they accept that the person may then have to
    look for the card. Built: the save makes the card the focus for the layout and scrolls nothing. When the card is
    not whole in view once the save's status has landed, in the margin layout the acknowledgment line's position at the
    panel's foot reads "Saved · the card is above" or "below", a button whose click scrolls the card into view, and in
    the list under a narrow column the same button stands under the panel's header (the list's Send section is the
    scroller's foot, below the very card the line says is below, so a line there was never on screen when it was
    wanted; the review's first round, 2026-09-09); the line ends at the person's next gesture (a Tab or a modifier
    pressed alone, the keyboard's way to the line, is none) or when the card comes into view, never on a timer. In the
    margin layout the acknowledgment of the send before, which the line displaced, is back in its place when the line
    ends (the review's third round, 2026-09-09). The arrivals follow-on under Slice 2 has the build.

44. **A comment can be made inside a tracked change without replying to the change** (2026-09-09). The user wants
    selecting words inside a change's new text and commenting on them to work as it does for any other passage;
    Reply on the change's card must not be the only way to comment on a change. The mapping, the composer and the
    save already accepted such a passage. The mark blocked it by mouse: a change mark and a comment highlight are
    controls (`fcchange`, `fcopen`), a drag begun and ended inside one fires a click on it, the common ancestor of
    the press and the release, and the card's open (`showCard`, `centerOn`) scrolled the mark to the body's centre
    and hid the Comment float the same mouseup had offered beside the selection (`hideFloatOnScroll`). The rule is
    event-based: the click that ends a drag is not a tap. In the `fcchange` and `fcopen` handlers a click arriving
    with a non-collapsed selection whose anchor and focus both lie inside the clicked mark does nothing
    (`dragClick`): no card, no scroll, no focus change; the float stands and the composer opens on the selection as
    for any passage. A plain click or a tap on a mark opens the card as before: its click arrives with the selection
    collapsed, or standing with no end inside the clicked mark, and the guard yields only to a selection whose ends
    both lie inside that mark, whatever the control's press did to a standing selection; a selection elsewhere
    (another paragraph, the aside, another pane) changes nothing; a click with no pointer behind it (`detail` 0: the
    keyboard's activation of the focused mark) opens the card whatever selection stands. The guard reads the clicked
    mark rather than the whole body since the slice's review (2026-09-09, with a real mouse in Chromium and Firefox,
    Rendered and Raw). As first built it read any selection with both ends in the body as a drag's, on the premise
    that a press collapses a standing selection, which holds only for a press on text the press can select: a press
    on a deletion's struck label (generated text under `user-select: none`), on a region rectangle (the figure
    overlay cancels its `pointerdown`, and with it the mousedown that would have collapsed one), on a mark inside an
    author's link (a draggable anchor) or on a framed picture collapses nothing, so with words selected in another
    paragraph a click on any of them opened nothing until the selection was dropped. Read against the mark, the guard
    yields only to the drag's own selection: a drag that ends on the mark it began in puts both ends inside it, a
    drag that leaves the mark fires its click on the common ancestor and never on the mark, a selection standing
    elsewhere or spanning the mark from outside has no end inside it, and no selection end can lie inside a
    deletion's point or a rectangle, so those clicks open the card whatever stands selected. An engine may report a
    drag's end at the mark's edge as a point in the mark's parent or in the neighbouring text rather than in the mark;
    `endInside` takes both as the mark's. The click stood down shows nothing: the press pulse the delegate put on the
    mark before the handler ran comes off in the same task (`actions.ts`). With the panel closed the marks are painted
    too, and a drag inside one behaves as a drag over any passage does then: no panel opens and no card, since the
    Comment float is the open panel's; a plain click on the mark opens both. The comment saved is an ordinary passage
    comment, its own card and highlight, no `suggestionId`. `file-comments-markclick.test.ts` and
    `file-comments-markclick-controls.test.ts` drive the guard over the stand-in;
    `file-comments-markclick-browser.test.ts` and `file-comments-markclick-controls-browser.test.ts` drag a real mouse
    in Chromium and Firefox, Rendered and Raw: inside an insertion's mark, and, with words selected in another
    paragraph, on a deletion's label, the marks inside a link, a region rectangle and a framed figure. Client-only; no
    kernel change.
45. **A comment names the changes it is about by stored ids the person picks; romp never writes `suggestionId`**
    (2026-09-10). The user's answers to the decoupling assessment: a comment should be able to say which changes it is
    about, by their own pick and not by the session's stamp; one list with the filter, no tabs; and a comment made inside
    a change is an ordinary comment. Built as `changeIds` on the comment, romp's third additive field: Comment on this
    change (the change card's Reply until now) and the composer's checked "about this change" option over a selection
    that overlaps pending changes' marks write the ids beside the anchor, or alone for a deletion, whose text is not in
    the file; the card wears "about a change" and the change card "N comments", each a tag for the other; the message says
    "about your change …" after the passage. Stored ids over a derived overlap because an explicit list is what saying
    which changes a comment is about means, and it survives the passage's rewrite and the change's acceptance (the
    texts come from the sidecar or the comments log). The format's own `suggestionId` is read as the change that
    answered the comment (an older sidecar, or one `track-edit --thread` wrote) and never written: the host refuses a
    request naming it as a caller bug, and no comment is drawn inside a change card any more. The about follow-on under
    Slice 2 has the build. Client and host; the kernel's builder prints the desc verbatim and changed only in its
    docstring, so no kernel restart is needed for the message to say it.
46. **Resolve answered: the person resolves, singly or all the answered ones at once** (2026-09-10). The user's ruling
    on what should resolve a comment: nothing but them, and a button that resolves every comment the session has
    replied to. Built: nothing in the host or the panel resolves a comment except the card's Resolve (as before) and a
    header action "Resolve answered (N)", shown while N > 0, N being the unresolved comments by the person that carry a
    reply by another author since the person's last message on the comment (a reply of kind edit counts as an answer;
    the person's own later reply does not). Its click asks in one plain line, "Resolve the N comments the session has
    answered?", resolves them through the host's `resolve` op one request each (a refusal is reported per comment,
    under the card), and puts "Reopen all" in the acknowledgment's position (the margin layout's Send section; in the list
    layout, whose Send section is the scroller's foot and left the offer off screen after the click, under the header: the
    review's second round, 2026-09-10) until the person's next gesture, which reopens the same comments the same way.
    Event-based: the set is read off the status when the button is pressed, never a timer. Client-only; no kernel change.
47. **A guard on the Bash tool too** (2026-09-10). The vendored guard denies a raw Write, Edit or MultiEdit on a
    tracked file and sees nothing else, and a session in auto mode is told to write files through Bash: cp and mv
    over the file, tee, a heredoc redirected into it, sed -i, a python or node one-liner. A dry run (2026-09-09)
    saw one do exactly that: it ran track-config and cp in a single compound command on a tracked file, the flag
    printed on, and the copy landed raw, with no change recorded for the user to accept or reject; the session
    recovered from its own base copy, whose hash matched the sidecar's fingerprint, and
    re-applied its edits through track-edit. The remedy is in two places. The skill (patch 0007) says a tracked
    file is never written through Bash either, and that track-config's exit code is checked as a step of its own,
    since its 0 means ON and a `&&` after it runs the write on exactly the tracked file. And romp's own PreToolUse
    hook on the Bash tool, `hooks/romp-track-bash-guard.mjs`, beside the vendored guard and registered by the same
    installer merge on the `Bash` matcher (synchronous, timeout 10; linked from `hooks/` with romp's own hooks and
    removed by the uninstaller with romp's hooks), reads the command and refuses one that would write a tracked
    file. What it reads: the command lexed as a shell would (quotes, escapes, comments, line continuations, heredoc
    bodies kept as data, pipes and lists cut into simple commands, `cd` moving the working directory for what
    follows, inside `( ... )` only up to the `)`), and from each simple command the paths it would write: the
    destination of cp, mv, install and ln (a directory destination or `-t` resolved to the files that land in it,
    a directory source walked to the files it carries, a link one entry whatever it points at), the operands of
    tee, sponge and truncate, dd's `of=`, sort's `-o`, every `>`, `>>`, `>|`, `&>` and descriptor-prefixed
    redirection target, the files of sed -i and perl -i in their spellings, and a literal path a python or node
    inline script opens with a write mode (`-c` or `-e`, or a heredoc on stdin), the same inside `$(...)`, a
    literal `sh -c`, a loop body or after sudo, env or nice. Each is resolved against the payload's cwd and judged
    by the project's `.trackchanges/config.json` through store-io's `findVaultRoot` and the three steps of its
    `isTrackedFile` (the veto list, the explicit list by name, then the link closure), which the hook runs itself
    as `trackedIn` so the closure is built once per call; a path is judged under the name given and under the real
    path the kernel opens, so a symlink to a tracked file carries no write past it. The refusal is exit 2 with one
    line naming the file and the track-edit command, in the person's voice. What it lets through: a read (cat,
    grep, diff, git, sed without -i) names no target; a path built from a variable, and a command behind eval,
    xargs or a shell -c it cannot read, is unresolvable and passes, since a silent block of ordinary work would
    cost more than a missed write; a glob is expanded against the filesystem as the shell expands it and passes
    only when it matches nothing or names more than the hook will list, a brace list is expanded before the
    operands are read, a here-string is scanned like a heredoc and a process substitution's command is read like
    a `$(...)`; a tracked image or PDF passes by name as in the vendored guard; a source copied out of a tracked
    file is a read. Not read: rm, a mv of the tracked file elsewhere (a rename the store heals by content hash),
    find -exec, rsync and patch. Without ROMP_SID it exits 0 before reading stdin (decision 24). Cost: about 60 ms
    per Bash call when no target needs the link closure (a read, a target outside any project, an explicit hit on
    the project's tracked list, an empty list); a write to a file inside a tracking project that the list does not
    name (the common write in a project that tracks anything) adds one walk of the project's markdown tree per
    call, store-io's `trackedClosure`, a listing of every .md under the root and a read of every tracked note, the
    same walk the vendored guard pays on every such Write, built once and shared by all the command's targets, so
    a directory copy pays it once: measured at 80 to 100 ms on a 3000-note tree and 130 to 170 ms on a 12000-note
    one, more under load, growing with the project's markdown count and well under the installer's 10 s timeout.
    `tools/romp-track-bash-guard.test.mjs` drives the grammar and the process;
    `tools/romp-track-bash-guard-shapes.test.mjs`, from the review's first round (2026-09-10), the shapes that
    round found misread, each in both directions where it has two (a cd inside a subshell or a body, a heredoc
    followed by `&&`, a heredoc-fed shell, `bash -lc`, a prefix with options, pushd and popd, `[[ a > b ]]`, a
    function body, keyword and `Path(x).open()`, node `-p`, the NUL-byte rule, the full walk of a directory source
    and the landing folder that skips it, a brace list, a glob, a here-string, a process substitution, a symlink
    to a tracked file, the one closure per call); `tests/install-sh.bats` the registration;
    `tools/file-review-plan-bash-guard.test.mjs` holds this decision to the hook and the installer, and
    `tools/file-review-plan-bash-guard-review.test.mjs` its cost sentence to the hook's closure and every
    `romp-track-bash-guard…` module under `tools/` to this decision and the Tests bullet.
48. **Sessions commit the comments folder** (2026-09-10). The user found that their sessions never added
    `.trackchanges/` to git, so the user's comments on the sessions' files and the record of the tracked changes
    were not archived with the work. Decision 25 is unchanged: romp does no git operation, and a `.gitignore` line is the
    opt-out. The norm is added on the session side: the vendored skill (`vendor/track-changents/patches/0007`, its
    Notes) and `claude/romp-session-prompt.md` (one sentence in Working style, in the person's voice, naming the
    folder and nothing else of the machinery) ask a session that commits work in a project which has the folder
    and does not ignore it to include the folder in the commit, since it holds the person's comments and the
    record of the tracked changes. The guide's Files section and decision 25 say so to the person: sessions are
    asked, the person's own commits stay theirs, and nothing on the host stages or commits (the user did not
    choose staging). `tests/test_guide_files_commit_folder.py` holds the four texts to one another;
    `tests/test_session_prompt.py` pins the sentence.

49. **One writer per sidecar at a time** (2026-09-11). The lost-update probe (2026-09-09) ran the real host and
    the real vendored CLIs against one file and lost one write in five at a stagger of 4 to 20 ms. Every writer
    loads the sidecar, changes the object and renames a temp over it; a second writer whose load fell before the
    first's rename saved a store without the first's change, and its rename erased it. A `track-edit` between a
    reject's sidecar rename and its file rename lost its text the same way, to the reject's rename. A stat before
    the rename narrows the window without closing it, and a lock in the host alone leaves the CLIs overwriting, so
    the user said yes to one lock per sidecar shared by both (2026-09-11). `withStoreLock(storePath, fn)` in the
    vendored `store-io.mjs` creates `<sidecar>.lock` with O_EXCL holding `pid ts`, sleeps 2 to 5 ms and retries
    for up to 2 s while it is held, breaks a lock whose writer is dead or whose stamp is older than 15 s (the
    kernel kills a host at 10 s), and unlinks it in `finally`; the `.trackchanges/` folder is made for the lock
    when it is missing and removed again when nothing else landed in it. The break has one winner (the slice's
    review, first round, 2026-09-11; as first built two waiters that read one dead lock together both removed it,
    the second taking away the first's fresh lock, and both wrote): the waiters that find a stale lock serialize
    on a claim beside it, `<sidecar>.lock.break`, created with O_EXCL like the lock and holding the same `pid ts`;
    the one holding the claim judges the lock again under it, unlinks it only while it is still stale, and removes
    the claim on its way out; a claim whose breaker is dead or whose stamp is past the bound is removed by the
    lock's own rule. The release unlinks the lock only while the entry at the name is the holder's own inode, so
    a writer broken as stale while alive leaves the breaker's lock alone; a stamp that cannot be written after the
    create leaves no lock and no folder behind; a writer that made the folder and leaves while another writer's
    lock or claim is in it passes the folder's removal to that writer by a `made-dir` line appended to its lock or
    claim, honored at that writer's release (or by the breaker of that lock when its holder dies); and a link or
    another non-file at the lock's name, or at the claim's while a stale lock stands, is a lock that cannot be
    taken: the host refuses `unreadable` naming it, the CLIs print its line and exit 1, and nothing is followed or
    removed. The two names and that line are everything the lock leaves under `.trackchanges/`
    (`tools/store-io-lock.test.mjs`; the ADR's lock bullet, `docs/adr/0002`, is held to the same names and line
    and to the lock run in a scratch root by
    `tools/0002-file-comments-in-the-track-changents-sidecar-lock-names.test.mjs`). `track-edit`, `track-comment`
    and `track-reply` take it around their load-to-rename (`track-edit` from the file read through the file write and
    the edit turn it adds to the comment it answers) and, when it is not obtained, print `another editor is writing this file; retry` and exit 1
    with nothing written; their `fail()` throws to the entry point so a held lock is released. That part is
    vendor patch 0008, written as offerable to the engine's author and held back from the offer by the
    standing word of 2026-09-11 to open nothing new upstream. The host takes the same lock from its fence stat through its
    last rename or prune (`underStoreLock`): the sidecar's for `comment`, `reply`, `resolve`, `retarget`,
    `accept`, `reject` and `save`; `config.json`'s own for `set-tracked`, since that verb writes the root's list,
    which every file under the root shares, and a held `config.json` lock refuses `busy` naming the root's tracked
    list rather than the file, since that is what the lock guards (`tools/file-comments-host-config-lock.test.mjs`).
    A loose file takes it after its landmark and checks its `""` fence
    again under it, and every reply is built after the release from a store read back under the lock. The mtime
    fences stay: the lock serializes the writers, the fences catch the panel's stale copy, so every writer loads
    after the previous writer's rename and a stale copy always refuses. A lock still held after the wait refuses
    `busy` with nothing changed; the panel handles `busy` as it handles a moved fence (`MOVED`): a fresh status,
    one retry by id (the id-less verbs re-read and say nothing was decided), and the refusal verbatim with Reload
    on a second. `tools/file-comments-host-store-lock.test.mjs` drives the host and `track-reply` against a
    writer mid-write (before the lock, each answered about 220 ms before the holder saved, and the holder's save
    erased its write), the refusal and the stale lock; `tools/file-comments-host-race.test.mjs` a `track-edit`
    inside a reject's write, through `FILE_COMMENTS_TEST_PAUSE_MS`, a test seam at the file's rename that is
    inert unless set and that the kernel never sets; `tools/file-comments-host-landmark-race.test.mjs` two first
    writes on one loose file, in both orderings the race has and in a two-process loop, the second meeting a moved
    fence and never `unreadable`; `tools/file-comments-host-read-under-lock.test.mjs` a comment sent between a
    `track-edit`'s two writes, placed in the text the edit left; `tools/file-comments-host-config-lock.test.mjs`
    `set-tracked` against a held `config.json.lock`; `tools/track-comment-race.test.mjs` six real `track-comment`
    processes on one file at one instant, every comment landing; `tools/vendor-patches.test.mjs` (P8) the CLIs' refusal and
    their release on a failure; `ui/webview/file-comments-changes-review2.test.ts` the panel's `busy`;
    `ui/webview/file-comments-save-busy.test.ts` the editor's Save through the panel refused `busy`, one retry and
    no more; `tools/file-review-plan-sidecar.test.mjs` holds this record and decision 50 to the source,
    `tools/file-review-plan-sidecar-records.test.mjs` the records' inventory to the tree, and
    `tools/file-review-plan-sidecar-adr-modules.test.mjs` the ADR-named modules to the Tests bullet and to this
    record by name, and both records to the glossary's words for a file and a comment.
50. **The clock a reply carries is taken before the read** (2026-09-11). The same probe found the panel's poll
    blind to a write 11 times in 147 rounds. The host read the sidecar and then stat'ed it for the reply's
    `storeMtimeNs`, so a write landing between the two gave the panel the writer's clock over the earlier bytes;
    the poll compared that clock with the disk's, saw no difference, and the panel kept a store one write
    behind until something else moved it. `configMtimeNs` had the same shape. The user said yes to the host
    clocking each file before it reads it (2026-09-11): `loadOrRefuse` and `loadFile` stat the sidecar first
    (`loadFile` decides from that clock whether there is a sidecar to read), `configStatus` stats `config.json`
    first, a prune sets the sidecar's clock to null as of the prune, and `set-tracked` stamps the config's with
    its own write, under its lock. The reply carries those clocks (`clockOf`) and stats nothing under
    `.trackchanges/`; a verb that reaches the reply without a clock is a program error, never a stat at reply
    time. The clock the panel baselines from is therefore never newer than the bytes it was given, so a write in
    the remaining gap makes the next poll refresh once, or the next write refuse `store-moved`.
    `tools/file-comments-host-clocks.test.mjs` interposes the read so a newer sidecar, and a newer config, land
    right after the first read (before: the reply carried the disk's newer clock over bytes without the write),
    and a newer sidecar in the instant after a prune (before: a later writer's clock beside a null store).

## Open questions for the user

Every question raised by this document, by its reviews, or in the design interview has been ruled
on; see Decisions. The margin layout (the follow-on note under Slice 2) awaits the user's word: it
is the build's reading of the ask, not a ruling, and the walk answers it. With it, the loose group's
place: a card with no mark (a whole-file comment, a change the Rendered view cannot paint, a detached
anchor, a region whose figure has not loaded) stands at the top of the track, which the lock keeps out
of view for a reader anywhere but the top of the text; the follow-on's third review confirmed that and
proposed a pinned band between the composer and the track for those cards, in the list's order, with
its own scroll and a fold beyond a few — a new surface, so it waits for the same word rather than
landing with the review's fixes (the saved line's click, through `showLoose`, brings a whole-file comment's card into
view on request; the save itself moves nothing since decision 43). The focus follow-on (2026-09-08) adds to the question: the group joins the chain of cards
a focus moves up, as far as the track's start, and the cards at its end that do not fit above the focused
card are laid below it — so a focus near the top of the text can put a whole-file comment's card under the
focused card rather than at the top (as first built the group was moved above the start, where no scroll
reaches it; the follow-on's review put every card at or below the start, and the verification review, 2026-09-09, lays
the cards a spilled card had pushed again without it, so the first passage's card takes the start a spilled whole-file
card gave up).

## Upstream

The user intends to offer the whole feature upstream to romp eventually (the user 2026-09-05).
Vendoring the core and the agent-side tooling (decisions 4 and 15) makes the loop
self-contained, so the whole feature can be offered as one; Slice 0 is also a candidate row on
its own. The offer decisions belong to the offer flow, not this plan.
